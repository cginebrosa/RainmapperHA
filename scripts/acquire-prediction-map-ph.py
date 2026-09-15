#!/usr/bin/env python3
"""Acquire bounded native-grid OpenLandMap COG windows; never run at point lookup.

An explicit reviewed JSON plan supplies URLs, metadata and regional extents.
Finished crops are resumable, partial files retained, manifest published last.
"""
import argparse
import fcntl
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import shutil
import time
from urllib.request import Request, urlopen


def digest(path):
    h = sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    tmp = path.with_suffix('.tmp.json')
    with tmp.open('w') as stream:
        json.dump(data, stream, indent=2); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.plan.read_bytes()
    if len(raw) > 65536:
        raise ValueError('plan_too_large')
    plan = json.loads(raw)
    if plan['schema'] != 'openlandmap_ph_acquisition_v1' or len(plan['regions']) > 8 or len(plan['layers']) != 3:
        raise ValueError('invalid_acquisition_plan')
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / '.acquire.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(args, plan, sha256(raw).hexdigest())


def run(args, plan, plan_hash):
    from osgeo import gdal
    gdal.UseExceptions()
    gdal.SetCacheMax(32 * 1024 * 1024)
    for key, value in {'GDAL_DISABLE_READDIR_ON_OPEN':'EMPTY_DIR',
                       'CPL_VSIL_CURL_ALLOWED_EXTENSIONS':'.tif',
                       'GDAL_HTTP_CONNECTTIMEOUT':'10', 'GDAL_HTTP_TIMEOUT':'60',
                       'GDAL_HTTP_MAX_RETRY':'2', 'GDAL_HTTP_RETRY_DELAY':'2',
                       'CPL_VSIL_CURL_CACHE_SIZE':'4194304'}.items():
        gdal.SetConfigOption(key, value)
    state_path = args.output / 'acquisition.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {
        'plan_sha256':plan_hash, 'status':'downloading', 'assets':[], 'sources':{}}
    if state['plan_sha256'] != plan_hash:
        raise ValueError('different_plan_in_existing_output')
    for layer in plan['layers']:
        url = layer['url']
        if not url.startswith('https://s3.opengeohub.org/') or not url.endswith('.tif'):
            raise ValueError('unexpected_source')
        with urlopen(Request(url, method='HEAD'), timeout=20) as response:
            identity = {k:response.headers.get(k) for k in ('ETag','Content-Length','Last-Modified')}
        if url in state['sources'] and state['sources'][url] != identity:
            raise ValueError('remote_source_changed')
        state['sources'][url] = identity
        write_json(state_path, state)
        source = gdal.OpenEx('/vsicurl/' + url, gdal.OF_RASTER | gdal.OF_READONLY, allowed_drivers=['GTiff'])
        gt = source.GetGeoTransform()
        if source.RasterCount != 1 or source.GetRasterBand(1).DataType != gdal.GDT_Byte or gt[2] or gt[4] or gt[1] <= 0 or gt[5] >= 0:
            raise ValueError('unexpected_source_grid')
        for region in plan['regions']:
            name = region['region'] + '_' + layer['statistic'].replace('.', '') + '.tif'
            if '/' in name or '..' in name:
                raise ValueError('invalid_asset_name')
            target = args.output / name
            previous = next((a for a in state['assets'] if a['path'] == name), None)
            if previous:
                if not target.is_file() or digest(target) != previous['sha256']:
                    raise ValueError('completed_asset_changed')
                print(json.dumps({'reused':name,'bytes':target.stat().st_size}), flush=True)
                continue
            if target.exists():
                raise ValueError('unregistered_existing_asset')
            west,south,east,north = region['bbox']
            x0,x1 = math.floor((west-gt[0])/gt[1]), math.ceil((east-gt[0])/gt[1])
            y0,y1 = math.floor((north-gt[3])/gt[5]), math.ceil((south-gt[3])/gt[5])
            width,height = x1-x0,y1-y0
            if not (0 <= x0 < x1 <= source.RasterXSize and 0 <= y0 < y1 <= source.RasterYSize) or width*height > 2_000_000_000:
                raise ValueError('crop_limit')
            if shutil.disk_usage(args.output).free < width*height + 512*1024*1024:
                raise ValueError('insufficient_disk_space')
            partial = args.output / (name + f'.{time.time_ns()}.partial.tif')
            progress_time = [0.0]
            def progress(fraction, message, data):
                if time.monotonic()-progress_time[0] >= 10 or fraction == 1:
                    print(json.dumps({'asset':name,'percent':round(fraction*100,1)}),flush=True)
                    progress_time[0] = time.monotonic()
                return 1
            output = gdal.Translate(str(partial), source, format='GTiff', srcWin=[x0,y0,width,height],
                creationOptions=['TILED=YES','BLOCKXSIZE=512','BLOCKYSIZE=512','COMPRESS=DEFLATE',
                                 'PREDICTOR=2','ZLEVEL=6','NUM_THREADS=1','BIGTIFF=IF_SAFER'], callback=progress)
            output.FlushCache(); output = None
            check = gdal.OpenEx(str(partial), gdal.OF_RASTER | gdal.OF_READONLY, allowed_drivers=['GTiff'])
            if (check.RasterXSize,check.RasterYSize) != (width,height):
                raise ValueError('crop_dimensions_mismatch')
            transform = list(check.GetGeoTransform())
            # Probe corners and centre against the actual source grid; no resampling.
            for cx,cy in ((0,0),(width-1,height-1),(width//2,height//2)):
                a = check.GetRasterBand(1).ReadRaster(cx,cy,1,1)
                b = source.GetRasterBand(1).ReadRaster(x0+cx,y0+cy,1,1)
                if a != b:
                    raise ValueError('crop_readback_mismatch')
            nodata = check.GetRasterBand(1).GetNoDataValue(); check = None
            os.replace(partial, target)
            stat = target.stat()
            asset = {'path':name,'region':region['region'],'statistic':layer['statistic'],
                     'resolution_m':layer['resolution_m'],'transform':transform,'width':width,'height':height,
                     'nodata':nodata,'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'sha256':digest(target)}
            state['assets'].append(asset); write_json(state_path, state)
            print(json.dumps({'complete':name,'bytes':stat.st_size}), flush=True)
        source = None
    state['status'] = 'complete'; write_json(state_path,state)
    manifest = {k:plan[k] for k in ('source_id','edition','period','depth_cm','scale','interval_probability','license','attribution','source_url')}
    manifest.update(schema='openlandmap_ph_local_v1', assets=state['assets'], plan_sha256=plan_hash,
                    nearest_max_distance_m=plan.get('nearest_max_distance_m',0))
    write_json(args.output/'manifest.json',manifest)
    print(json.dumps({'status':'complete','files':len(state['assets']),
                      'bytes':sum(a['bytes'] for a in state['assets'])}),flush=True)


if __name__ == '__main__':
    main()
