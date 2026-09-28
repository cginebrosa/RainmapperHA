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


def add_map_asset(root, asset, role, generation):
    """Register an already verified ordinary file; publish new metadata atomically.

    Explicit import boundary, never a query/startup action. Existing scientific
    dataset manifests and assets are untouched. The receipt must accompany a
    copy verified by the caller; no large rehash on HA.
    """
    import re
    from .mushroom_geography_store import SourceIdentities, read_metadata
    from .mushroom_map_geography_runtime import GeographyPublication
    from .mushroom_map_volume import GEO_FILES
    if role not in GEO_FILES or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', generation):
        raise ValueError('invalid_geography_extension')
    root = Path(root).resolve()
    publication = GeographyPublication(root, start=False)
    try:
        reference = publication.reference()
        current = publication.lookup(reference['fingerprint'])
        if not current['identities'].portable:
            raise ValueError('portable_geography_required')
        old = current['manifest']
        if asset['path'] in {r['path'] for r in old['files']}:
            raise ValueError('geography_asset_already_registered')
        manifest = dict(old, geography={**old['geography'], role: asset['path']},
                        files=[*old['files'], asset], file_count=old['file_count'] + 1,
                        bytes=old['bytes'] + asset['bytes'])
        checked_manifest(manifest)
        aliases = {r['path']: current['identities'].records[r['path']]['physical_path'] for r in old['files']}
        aliases[asset['path']] = asset['path']
        # Check unchanged files against their sealed physical identities before
        # issuing a fresh metadata publication, not merely their byte lengths.
        for row in old['files']:
            if current['identities'].stamp(current['root']/row['path']) != [row['bytes'], row['mtime_ns']]:
                raise ValueError('geography_base_changed')
        records = identities(root, manifest['files'], aliases)
        dest = root/'generations'/generation
        if dest.exists():
            raise ValueError('geography_generation_already_exists')
        sources_file = 'map-sources-' + generation + '.json'
        if (root/sources_file).exists():
            raise ValueError('geography_sources_already_exists')
        dest.mkdir(parents=True)
        write_metadata(dest/'manifest.json', manifest)
        write_metadata(root/sources_file, records)
        if publication.reference() != reference:
            raise ValueError('geography_changed_during_extension')
        ref = {'format': 'map_geography_publication_v1', 'generation': generation,
               'fingerprint': fingerprint(manifest), 'sources_file': sources_file}
        write_metadata(root/'CURRENT.json', ref)
        return {**ref, 'added_bytes': asset['bytes'], 'hashed_asset_bytes': 0}
    finally:
        publication.close()


def territorial_dataset_plan(root):
    """Small manifest over already published assets; never copy/hash GIS data."""
    import json
    import hashlib
    import sqlite3
    from contextlib import closing
    from .mushroom_geography_store import read_metadata, SourceIdentities
    from .mushroom_map_geography_runtime import GeographyPublication
    from .mushroom_territorial_reader import CONFIG_FILE, FORMAT, PATH_FLAGS
    from .mushroom_worker_dataset_cache import _canonical_fingerprint, DEFAULT_DATASET_ID
    root = Path(root).resolve()
    publication = GeographyPublication(root, start=False)
    try:
        ref = publication.reference()
        snapshot = publication.lookup(ref['fingerprint'])
        sources = snapshot['identities']
        if not sources.portable:
            raise ValueError('portable_geography_required')
        selected = {}
        def add(name):
            row = sources.records.get(name)
            if not row:
                raise ValueError('territorial_dependency_not_published')
            if sources.stamp(root/name) != row['logical']:
                raise ValueError('territorial_source_changed')
            physical = row['physical_path']
            selected[physical] = row
            return physical
        geography = {role: add(name) for role, name in snapshot['manifest']['geography'].items()
                     if role in PATH_FLAGS}
        if 'mvc50_index' not in geography:
            raise ValueError('territorial_mvc50_required')
        if 'forest_index' in geography:
            index = root / geography['forest_index']
            with closing(sqlite3.connect(index.as_uri()+'?mode=ro', uri=True)) as db:
                raw = db.execute('SELECT value FROM metadata LIMIT 1').fetchone()[0]
            if len(raw) > 4096:
                raise ValueError('forest_metadata_limit')
            meta = json.loads(raw)
            source = (index.parent / meta['source']).resolve()
            for suffix in ('.shp', '.shx', '.dbf', '.prj'):
                name = source.with_suffix(suffix).relative_to(root).as_posix()
                logical = name if name in sources.records else sources.physical_names.get(name)
                if not logical or add(logical) != name:
                    raise ValueError('territorial_forest_layout_mismatch')
        # Keep the current DEM coverage, omit original MVC50/geology duplicates.
        old_root = root / 'mushroom-GIS'
        old = dataset_contract({'datasets': [read_metadata(old_root/'geography-dataset.json')]})
        old_sources = SourceIdentities(old_root/IDENTITIES_FILE)
        for row in old['files']:
            if Path(row['path']).suffix.lower() not in ('.tif', '.tiff'):
                continue
            identity = old_sources.records[row['path']]
            if (old_sources.stamp(old_root/row['path']) != identity['logical']
                    or identity['sha256'] != row['sha256']):
                raise ValueError('territorial_dem_changed')
            selected['mushroom-GIS/'+row['path']] = identity
        config = {'format': FORMAT, 'geography': geography,
                  'source_stamps': {name: row['logical'] for name, row in sorted(selected.items())}}
        raw = json.dumps(config, sort_keys=True, separators=(',', ':')).encode()
        if len(raw) > 8192:
            raise ValueError('territorial_config_limit')
        files = [{'role': 'gis', 'path': name, 'sha256': row['sha256'], 'size_bytes': row['logical'][0]}
                 for name, row in sorted(selected.items())]
        files.append({'role': 'gis', 'path': CONFIG_FILE, 'size_bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest()})
        dataset = {'dataset_id': DEFAULT_DATASET_ID,
                   'files': files, 'fingerprint': _canonical_fingerprint(files)}
        dataset_contract({'datasets': [dataset]})
        return {'config': config, 'dataset': dataset, 'map_reference': ref,
                'configuration_bytes': len(raw), 'hashed_asset_bytes': 0,
                'copied_asset_bytes': 0}
    finally:
        publication.close()


def activate_territorial_dataset(root, plan):
    """Explicit idle-time activation: metadata only, existing transport/cache unchanged."""
    from .mushroom_territorial_reader import CONFIG_FILE
    root = Path(root).resolve()
    # Revalidate references/stats, never hash the large inputs on HA.
    current = territorial_dataset_plan(root)
    if current != plan:
        raise ValueError('territorial_plan_changed')
    write_metadata(root/CONFIG_FILE, plan['config'])
    rows = [{'path': r['path'], 'sha256': r['sha256'], 'bytes': r['size_bytes'],
             'mtime_ns': (root/CONFIG_FILE).stat().st_mtime_ns if r['path'] == CONFIG_FILE
                         else plan['config']['source_stamps'][r['path']][1]}
            for r in plan['dataset']['files']]
    data = identities(root, rows, {r['path']: r['path'] for r in rows})
    write_metadata(root/IDENTITIES_FILE, data)
    write_metadata(root/'geography-dataset.json', plan['dataset'])
