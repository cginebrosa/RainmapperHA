"""Explicit offline installation of public map files; never called per query.

Preserve paths and nanosecond timestamps required by the existing indices.
Private profiles, models, weather and coordinator credentials are not exported.
"""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3

FORMAT = 'prediction_map_volume_v1'
MAX_FILES = 20000
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
GEO_FILES = ('terrain_index', 'municipalities', 'land_cover', 'geology',
             'land_cover_parts', 'geology_parts', 'forest_index', 'openlandmap_ph')
GEO_ROOTS = ('soil_root', 'dem_root', 'regional_root')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def local(root, relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts or str(p) != relative:
        raise ValueError('invalid_volume_path')
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('volume_path_escape')
    return target


def plan(config, source_root):
    """Enumerate only dependencies of prepared readers, without hashing rasters."""
    root = Path(source_root).resolve()
    selected = {}
    paths = {}
    for key in (*GEO_FILES, *GEO_ROOTS):
        if config.get(key):
            p = (root / config[key]).resolve(strict=True)
            paths[key] = p.relative_to(root).as_posix()
    def add(path, known_sha=None, expected=None):
        p = Path(path).resolve(strict=True)
        relative = p.relative_to(root).as_posix()
        stat = p.stat()
        if not p.is_file() or (expected and (stat.st_size, stat.st_mtime_ns) != tuple(expected)):
            raise ValueError('volume_source_changed:' + relative)
        selected[relative] = dict(path=relative, bytes=stat.st_size, mtime_ns=stat.st_mtime_ns,
                                  sha256=known_sha or None)
        if len(selected) > MAX_FILES:
            raise ValueError('volume_file_limit')
    for key in GEO_FILES:
        if key in paths:
            add(root / paths[key])
    if 'terrain_index' in paths:
        with closing(sqlite3.connect((root/paths['terrain_index']).as_uri()+'?mode=ro', uri=True)) as db:
            if db.execute('SELECT count(*) FROM assets').fetchone()[0] > MAX_FILES:
                raise ValueError('volume_file_limit')
            for key, rel, size, mtime, sha in db.execute('SELECT root_key,path,bytes,mtime_ns,recorded_sha256 FROM assets'):
                add(local(root / paths[{'soil':'soil_root','dem':'dem_root','regional':'regional_root'}[key]],rel), sha, (size,mtime))
    if 'forest_index' in paths:
        index = root / paths['forest_index']
        with closing(sqlite3.connect(index.as_uri()+'?mode=ro',uri=True)) as db:
            meta = json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
        source = (index.parent / meta['source']).resolve(strict=True)
        for ext, expected in meta['stamps'].items():
            add(source.with_suffix(ext), expected=expected)
        for ext in ('.cpg', '.qix'):
            if source.with_suffix(ext).exists():
                add(source.with_suffix(ext))
    if 'openlandmap_ph' in paths:
        manifest = root / paths['openlandmap_ph']
        for asset in json.loads(manifest.read_text())['assets']:
            add(local(manifest.parent,asset['path']),asset.get('sha256'),(asset['bytes'],asset['mtime_ns']))
    # Nearby provenance/licence files, never originals or private runtime trees.
    for relative in list(selected):
        parent = (root / relative).parent
        for name in ('README.md', 'LICENSE', 'LICENSE.txt'):
            if (parent/name).is_file():
                add(parent/name)
    config_out = {**paths, 'ecology_ph_source':config.get('ecology_ph_source','soilgrids')}
    if config.get('municipalities_edition'):
        config_out['municipalities_edition'] = config['municipalities_edition']
    assets = sorted(selected.values(),key=lambda x:x['path'])
    return {'format':FORMAT,'scope':'prepared_readers; ecology coverage is not implied by DEM extent',
            'geography':config_out,'files':assets,'file_count':len(assets),
            'bytes':sum(a['bytes'] for a in assets)}


def validate_manifest(data, *, sealed=False):
    if data.get('format') != FORMAT or not isinstance(data.get('files'),list) or not 0 < len(data['files']) <= MAX_FILES:
        raise ValueError('invalid_volume_manifest')
    seen = set()
    for a in data['files']:
        # Validate syntax even before a destination exists.
        local(Path('/'),a['path'])
        if a['path'] in seen or type(a['bytes']) is not int or a['bytes'] < 0 or type(a['mtime_ns']) is not int:
            raise ValueError('invalid_volume_asset')
        seen.add(a['path'])
        sha = a.get('sha256')
        if (sealed or sha is not None) and (not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha)):
            raise ValueError('invalid_volume_hash')
    if data['bytes'] != sum(a['bytes'] for a in data['files']) or data['file_count'] != len(seen):
        raise ValueError('invalid_volume_totals')
    if len(json.dumps(data).encode()) > MAX_MANIFEST_BYTES:
        raise ValueError('volume_manifest_limit')


def install(data, source_root, destination, *, link=False):
    """New inactive destination, resumable. No overwrite/activation of another generation.

    With link=True reuse immutable public files on the same filesystem. Consumers
    must mount them read-only. Default copies support a physically separate host.
    Existing receipts avoid transfer and hashing on a repeated installation.
    """
    validate_manifest(data)
    source, target = Path(source_root).resolve(), Path(destination).resolve()
    if target == source:
        raise ValueError('volume_destination_is_source')
    target.mkdir(parents=True,exist_ok=True)
    receipt = target/'manifest.json'
    if receipt.exists():
        installed = json.loads(receipt.read_text())
        validate_manifest(installed,sealed=True)
        if data['geography'] != installed['geography'] or [(a['path'],a['bytes'],a['mtime_ns']) for a in data['files']] != [(a['path'],a['bytes'],a['mtime_ns']) for a in installed['files']]:
            raise ValueError('volume_generation_conflict')
        for expected, a in zip(data['files'], installed['files']):
            if expected.get('sha256') and expected['sha256'] != a['sha256']:
                raise ValueError('volume_generation_conflict')
            stat = local(target,a['path']).stat()
            if (stat.st_size,stat.st_mtime_ns) != (a['bytes'],a['mtime_ns']):
                raise ValueError('installed_volume_changed')
        return {'status':'reused','files':len(data['files']),'transferred_bytes':0,'hashed_bytes':0}
    output = json.loads(json.dumps(data))
    transferred = hashed = 0
    for a in output['files']:
        src, dst = local(source,a['path']), local(target,a['path'])
        before = src.stat()
        if (before.st_size,before.st_mtime_ns) != (a['bytes'],a['mtime_ns']):
            raise ValueError('volume_source_changed')
        dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists():
            temporary = dst.with_name(dst.name+'.installing')
            if link:
                if not temporary.exists():
                    os.link(src,temporary)
                elif not os.path.samefile(src,temporary):
                    raise ValueError('volume_staging_conflict')
            else:
                # A partial copy can be resumed by rerunning; replace only our staging file.
                if temporary.is_symlink():
                    raise ValueError('volume_staging_conflict')
                with src.open('rb') as reader, temporary.open('wb') as writer:
                    shutil.copyfileobj(reader,writer,1024*1024)
                os.utime(temporary,ns=(before.st_atime_ns,before.st_mtime_ns))
                transferred += a['bytes']
            check = digest(temporary); hashed += a['bytes']
            if a.get('sha256') and check != a['sha256']:
                raise ValueError('volume_checksum_mismatch')
            temporary.rename(dst)
        else:
            check = digest(dst); hashed += a['bytes']
            if check != (a.get('sha256') or digest(src)):
                raise ValueError('volume_destination_conflict')
        if (dst.stat().st_size,dst.stat().st_mtime_ns) != (a['bytes'],a['mtime_ns']):
            raise ValueError('volume_timestamp_mismatch')
        if (src.stat().st_size,src.stat().st_mtime_ns) != (before.st_size,before.st_mtime_ns):
            raise ValueError('volume_source_changed')
        a['sha256'] = check
    validate_manifest(output,sealed=True)
    temporary = target/'manifest.json.installing'
    temporary.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    temporary.rename(receipt)
    return {'status':'installed','files':len(output['files']),'transferred_bytes':transferred,'hashed_bytes':hashed}
