"""Offline preparation of ordinary shared geography files; never run at startup.

The caller supplies manifests from an already verified copy. Preparation only
records portable file stats and content references. Readers never create paths.
"""
from pathlib import Path

from rainmapper_core.mushroom_geography_store import (
    PORTABLE_FORMAT, IDENTITIES_FILE, relative_path, write_metadata,
)
from rainmapper_core.mushroom_map_geography_runtime import checked_manifest, fingerprint
from rainmapper_core.mushroom_worker_dataset_cache import dataset_contract


def layout(map_manifest, auxiliary):
    checked_manifest(map_manifest)
    # Auxiliary inventory has the same bounded file contract, without map roles.
    checked_manifest(auxiliary)
    shared = {}
    files = {}
    for row in auxiliary['files']:
        name = 'mushroom-GIS/' + relative_path(row['path']).as_posix()
        shared.setdefault((row['sha256'], row['bytes']), name)
        files[name] = row
    aliases = {}
    for row in map_manifest['files']:
        physical = shared.get((row['sha256'], row['bytes']), row['path'])
        previous = files.get(physical)
        if previous and (previous['sha256'], previous['bytes']) != (row['sha256'], row['bytes']):
            raise ValueError('geography_physical_path_collision')
        files.setdefault(physical, row)
        aliases[row['path']] = physical
    return files, aliases


def identities(root, rows, aliases):
    root = Path(root).resolve()
    records = {}
    for row in rows:
        physical = aliases[row['path']]
        path = root / relative_path(physical)
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root) or not path.is_file():
            raise ValueError('geography_requires_ordinary_file')
        stat = path.stat()
        if stat.st_size != row['bytes']:
            raise ValueError('geography_copy_size_mismatch')
        records[row['path']] = {'sha256': row['sha256'],
            'logical': [row['bytes'], row['mtime_ns']], 'physical_path': physical,
            'stored': [stat.st_size, stat.st_mtime_ns // 1_000_000]}
    return {'format': PORTABLE_FORMAT, 'files': records}


def prepare(root, map_manifest, auxiliary, dataset, generation, config):
    """Write small prepared metadata after copying/verifying the ordinary files.

No links, inode receipts, raster hashing, download or startup integration.
The pointer is committed last. Existing private configuration is not edited.
"""
    import re
    if not isinstance(generation, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', generation):
        raise ValueError('invalid_geography_generation')
    dataset = dataset_contract({'datasets': [dataset]})
    root = Path(root).resolve()
    files, aliases = layout(map_manifest, auxiliary)
    auxiliary_by_name = {r['path']: r for r in auxiliary['files']}
    for row in dataset['files']:
        aux = auxiliary_by_name.get(row['path'], {})
        if aux.get('sha256') != row['sha256'] or aux.get('bytes') != row['size_bytes']:
            raise ValueError('geography_dataset_inventory_mismatch')
    map_identities = identities(root, map_manifest['files'], aliases)
    gis_root = root/'mushroom-GIS'
    gis_identities = identities(gis_root, auxiliary['files'], {r['path']: r['path'] for r in auxiliary['files']})
    generation_root = root/'generations'/generation
    generation_root.mkdir(parents=True, exist_ok=True)
    sources_file = 'map-sources-' + generation + '.json'
    write_metadata(generation_root/'manifest.json', map_manifest)
    write_metadata(root/sources_file, map_identities)
    write_metadata(gis_root/IDENTITIES_FILE, gis_identities)
    write_metadata(gis_root/'geography-dataset.json', dataset)
    write_metadata(gis_root/'geography-auxiliary.json', auxiliary)
    write_metadata(root/'map-config.json', {**config, 'geography_publication_root': '.'})
    ref = {'format': 'map_geography_publication_v1', 'generation': generation,
           'fingerprint': fingerprint(map_manifest), 'sources_file': sources_file}
    write_metadata(root/'CURRENT.json', ref)
    return {**ref, 'ordinary_files': len(files), 'ordinary_bytes': sum(r['bytes'] for r in files.values()),
            'map_logical_files': len(map_manifest['files']), 'gis_files': len(auxiliary['files']),
            'hashed_asset_bytes': 0, 'startup_commands': 0}
