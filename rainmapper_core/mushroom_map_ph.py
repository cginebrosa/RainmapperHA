"""Bounded, offline OpenLandMap point reads, with optional nearby-cell fallback."""
from collections import OrderedDict
from hashlib import sha256
import json
import math
from pathlib import Path
import threading

MAX_MANIFEST_BYTES = 65536
MAX_ASSETS = 24
MAX_SEARCH_PIXELS = 262144


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def distance_m(lat, lon, other_lat, other_lon):
    a,b = math.radians(lat),math.radians(other_lat)
    h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(other_lon-lon)/2)**2
    return 12742017.6 * math.asin(min(1,math.sqrt(h)))


class OpenLandMapPHReader:
    def __init__(self, manifest, *, sources=None):
        from rainmapper_core.mushroom_geography_store import SourceIdentities
        self._sources = sources or SourceIdentities()
        self.path = Path(manifest).resolve(strict=True)
        with self.path.open('rb') as stream:
            raw = stream.read(MAX_MANIFEST_BYTES+1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ValueError('ph_manifest_limit')
        self.meta = json.loads(raw)
        if self.meta.get('schema') != 'openlandmap_ph_local_v1':
            raise ValueError('invalid_ph_manifest')
        self.assets = self.meta['assets']
        if not isinstance(self.assets,list) or not 1 <= len(self.assets) <= MAX_ASSETS:
            raise ValueError('ph_asset_limit')
        self.radius = self.meta.get('nearest_max_distance_m',0)
        if not finite(self.radius) or not 0 <= self.radius <= 5000:
            raise ValueError('invalid_ph_search_radius')
        if not finite(self.meta.get('scale')) or self.meta['scale'] <= 0:
            raise ValueError('invalid_ph_scale')
        if not 0 < self.meta['interval_probability'] < 1 or self.meta['depth_cm'] != [0,30]:
            raise ValueError('invalid_ph_context')
        identities = set()
        for a in self.assets:
            p = (self.path.parent/a['path']).resolve(strict=True)
            if not p.is_relative_to(self.path.parent) or p.suffix != '.tif' or not p.is_file():
                raise ValueError('invalid_ph_asset_path')
            key = (a['region'],a['statistic'])
            if key in identities or a['statistic'] not in ('mean','p0.16','p0.84'):
                raise ValueError('invalid_ph_asset_identity')
            identities.add(key)
            gt = a['transform']
            if (len(gt) != 6 or not all(finite(v) for v in gt) or gt[2] or gt[4] or gt[1]<=0 or gt[5]>=0
                    or type(a['width']) is not int or type(a['height']) is not int or min(a['width'],a['height'])<1):
                raise ValueError('invalid_ph_grid')
            a['_local_path'] = p
        from osgeo import gdal
        self.gdal = gdal
        self.datasets = OrderedDict()
        self.owner = threading.get_ident()
        self.revision = sha256(raw).hexdigest()[:20]

    def close(self):
        self.datasets.clear()

    def _dataset(self, asset):
        path = asset['_local_path']
        if self._sources.stamp(path) != [asset['bytes'],asset['mtime_ns']]:
            raise ValueError('ph_asset_changed')
        if path not in self.datasets:
            ds = self.gdal.OpenEx(str(path), self.gdal.OF_RASTER | self.gdal.OF_READONLY, allowed_drivers=['GTiff'])
            if (ds is None or ds.RasterCount != 1 or (ds.RasterXSize,ds.RasterYSize)!=(asset['width'],asset['height'])
                    or any(abs(x-y)>1e-9 for x,y in zip(ds.GetGeoTransform(),asset['transform']))
                    or ds.GetSpatialRef() is None or ds.GetSpatialRef().GetAuthorityCode(None) != '4326'):
                raise ValueError('ph_asset_grid_changed')
            if len(self.datasets) >= 4:
                self.datasets.popitem(last=False)
            self.datasets[path] = ds
        self.datasets.move_to_end(path)
        return self.datasets[path]

    def _value(self, asset, col, row):
        band = self._dataset(asset).GetRasterBand(1)
        raw = float(band.ReadAsArray(col,row,1,1)[0,0])
        value = raw*self.meta['scale']
        return round(value,3) if raw != band.GetNoDataValue() and finite(value) and 0<value<=14 else None

    def _point(self, statistic, lat, lon):
        for a in self.assets:
            if a['statistic'] != statistic:
                continue
            gt = a['transform']
            col,row = math.floor((lon-gt[0])/gt[1]),math.floor((lat-gt[3])/gt[5])
            if 0<=col<a['width'] and 0<=row<a['height']:
                value = self._value(a,col,row)
                if value is not None:
                    return value,a
        return None,None

    def _nearest(self, lat, lon):
        import numpy as np
        if not self.radius:
            return None
        dy = self.radius/110000
        dx = dy/max(0.01,math.cos(math.radians(lat)))
        best = None
        for a in self.assets:
            if a['statistic'] != 'mean':
                continue
            gt = a['transform']
            x0 = max(0,math.floor((lon-dx-gt[0])/gt[1]))
            x1 = min(a['width'],math.ceil((lon+dx-gt[0])/gt[1]))
            y0 = max(0,math.floor((lat+dy-gt[3])/gt[5]))
            y1 = min(a['height'],math.ceil((lat-dy-gt[3])/gt[5]))
            if x1<=x0 or y1<=y0:
                continue
            if (x1-x0)*(y1-y0)>MAX_SEARCH_PIXELS:
                raise ValueError('ph_search_pixel_limit')
            band = self._dataset(a).GetRasterBand(1)
            raw = band.ReadAsArray(x0,y0,x1-x0,y1-y0)
            valid = np.isfinite(raw) & (raw>0) & (raw*self.meta['scale']<=14)
            if band.GetNoDataValue() is not None:
                valid &= raw != band.GetNoDataValue()
            for iy,ix in zip(*np.nonzero(valid)):
                other_lon = gt[0]+(x0+int(ix)+0.5)*gt[1]
                other_lat = gt[3]+(y0+int(iy)+0.5)*gt[5]
                distance = distance_m(lat,lon,other_lat,other_lon)
                if distance<=self.radius and (best is None or distance<best[0]):
                    best = (distance,other_lat,other_lon,round(float(raw[iy,ix])*self.meta['scale'],3),a)
        return best

    def lookup(self, lat, lon):
        if threading.get_ident() != self.owner:
            raise RuntimeError('ph_reader_thread_mismatch')
        if not all(finite(v) for v in (lat,lon)) or not -90<=lat<=90 or not -180<=lon<=180:
            raise ValueError('invalid_ph_point')
        result = {'status':'no_data','source_id':self.meta['source_id'],'edition':self.meta['edition'],
                  'period':self.meta['period'],'depth_cm':self.meta['depth_cm'],
                  'interval_probability':self.meta['interval_probability'],'revision':self.revision,
                  'estimate':None,'lower':None,'upper':None}
        estimate,asset = self._point('mean',lat,lon)
        used_lat,used_lon,distance,method = lat,lon,0,'point'
        if estimate is None:
            nearest = self._nearest(lat,lon)
            if nearest is None:
                return result
            distance,used_lat,used_lon,estimate,asset = nearest
            method = 'nearest'
        lower,lower_asset = self._point('p0.16',used_lat,used_lon)
        upper,upper_asset = self._point('p0.84',used_lat,used_lon)
        # Intervals are coarser than the mean; never force mean containment.
        if lower is not None and upper is not None and lower>upper:
            lower=upper=None
        result.update(status='available' if lower is not None and upper is not None else 'partial',
                      estimate=estimate,lower=lower,upper=upper,
                      estimate_resolution_m=asset['resolution_m'],
                      interval_resolution_m=(lower_asset or upper_asset or {}).get('resolution_m'),
                      lookup={'method':method,'distance_m':round(distance,1),'lat':used_lat,'lon':used_lon})
        return result
