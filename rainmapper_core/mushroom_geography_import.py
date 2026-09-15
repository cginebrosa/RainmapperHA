"""Explicit offline adoption of verified GIS copies into the shared store.

Nothing is downloaded, deleted or activated here. Sealed-source mode requires
the operator to have verified the imported copy; otherwise assets are hashed
once at this offline boundary. Use verification on the Mac, not on each HA job.
"""
import hashlib
import os
from pathlib import Path
import re

from rainmapper_core import mushroom_map_geography_runtime as geography
from rainmapper_core import mushroom_worker_dataset_cache as datasets
from rainmapper_core.mushroom_geography_store import (
    IDENTITIES_FILE, ObjectStore, read_metadata, receipt_stamp, relative_path,
    write_metadata,
)


def _adopt(store, source_root, destination, records, *, sealed_source):
    source_root, destination = Path(source_root).resolve(), Path(destination).resolve()
    if source_root == destination:
        raise ValueError('geography_import_destination_is_source')
    destination.mkdir(parents=True, exist_ok=True)
    hashed = reused = 0
    for row in records:
        relative = relative_path(row['path'])
        target = destination / relative
        with store.locked():
            obj = store.find(row['sha256'], row['bytes'])
            if obj is not None:
                store.link(obj, target)
                reused += row['bytes']
                continue
        source = (source_root / relative).resolve(strict=True)
        if not source.is_relative_to(source_root) or not source.is_file():
            raise ValueError('invalid_geography_import_source')
        before = receipt_stamp(source)
        if before[0] != row['bytes']:
            raise ValueError('geography_import_size_mismatch')
        if not sealed_source:
            check = hashlib.sha256()
            with source.open('rb') as stream:
                for block in iter(lambda: stream.read(4*1024*1024), b''):
                    check.update(block)
                    hashed += len(block)
            if check.hexdigest() != row['sha256']:
                raise ValueError('geography_import_checksum_mismatch')
        with store.locked():
            obj = store.adopt_checked(source, row['sha256'], row['bytes'], before)
            store.link(obj, target)
    with store.locked():
        store.seal_view(destination, records)
    return {'files': len(records), 'bytes': sum(r['bytes'] for r in records),
            'hashed_asset_bytes': hashed, 'reused_object_bytes': reused,
            'copied_asset_bytes': 0, 'source_preserved': True, 'activated': False}


def adopt_map(source_root, root, generation, *, sealed_source=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', generation):
        raise ValueError('invalid_geography_generation')
    source_root, root = Path(source_root).resolve(), Path(root).resolve()
    manifest = geography.checked_manifest(read_metadata(source_root/'manifest.json'))
    destination = root/'generations'/generation
    if (destination/'manifest.json').exists():
        existing = geography.checked_manifest(read_metadata(destination/'manifest.json'))
        if geography.fingerprint(existing) != geography.fingerprint(manifest):
            raise ValueError('geography_generation_already_exists')
    store = ObjectStore(root)
    try:
        report = _adopt(store, source_root, destination, manifest['files'], sealed_source=sealed_source)
        write_metadata(destination/'manifest.json', manifest)
        return {**report, 'generation': generation, 'fingerprint': geography.fingerprint(manifest),
                'destination': str(destination)}
    finally:
        store.close()


def adopt_dataset(source_root, root, manifest, *, sealed_source=False, auxiliary_manifest=None):
    dataset = datasets.dataset_contract({'datasets': [manifest]})
    source_root, root = Path(source_root).resolve(), Path(root).resolve()
    destination = root/'datasets'/dataset['dataset_id']/'versions'/dataset['fingerprint']
    if (destination/'geography-dataset.json').exists():
        if read_metadata(destination/'geography-dataset.json') != dataset:
            raise ValueError('geography_dataset_already_exists')
        previous_auxiliary = (read_metadata(destination/'geography-auxiliary.json')
                              if (destination/'geography-auxiliary.json').exists() else None)
        if previous_auxiliary != auxiliary_manifest:
            raise ValueError('geography_auxiliary_already_exists')
    records = []
    auxiliary = geography.checked_manifest(auxiliary_manifest) if auxiliary_manifest is not None else None
    auxiliary_rows = {r['path']: r for r in auxiliary['files']} if auxiliary else {}
    for row in dataset['files']:
        if row['path'] in {IDENTITIES_FILE, 'geography-dataset.json'}:
            raise ValueError('geography_reserved_path')
        aux = auxiliary_rows.get(row['path'])
        if aux and (aux['sha256'], aux['bytes']) != (row['sha256'], row['size_bytes']):
            raise ValueError('geography_auxiliary_conflict')
        # A delta import omits payloads already verified in the common store.
        # Their original timestamps come from its sealed source inventory.
        mtime = aux['mtime_ns'] if aux else (source_root/relative_path(row['path'])).stat().st_mtime_ns
        records.append({'path': row['path'], 'sha256': row['sha256'],
                        'bytes': row['size_bytes'], 'mtime_ns': mtime})
    # Preserve local acquisition/provenance files without adding them to the
    # scientific job's transport contract. SoilGrids writers replace atomically.
    if auxiliary_manifest is not None:
        by_path = {row['path']: row for row in records}
        for row in auxiliary['files']:
            if row['path'] in {'geography-dataset.json', 'geography-auxiliary.json'}:
                raise ValueError('geography_reserved_path')
            previous = by_path.get(row['path'])
            if previous and (previous['sha256'], previous['bytes']) != (row['sha256'], row['bytes']):
                raise ValueError('geography_auxiliary_conflict')
            if not previous:
                by_path[row['path']] = row
        records = list(by_path.values())
        # Validate combined limits and file/directory collisions before linking.
        geography.checked_manifest({'format': geography.volume.FORMAT, 'geography': {},
            'files': records, 'file_count': len(records), 'bytes': sum(r['bytes'] for r in records)})
    store = ObjectStore(root)
    try:
        report = _adopt(store, source_root, destination, records, sealed_source=sealed_source)
        write_metadata(destination/'geography-dataset.json', dataset)
        if auxiliary_manifest is not None:
            write_metadata(destination/'geography-auxiliary.json', auxiliary_manifest)
        return {**report, 'fingerprint': dataset['fingerprint'], 'destination': str(destination)}
    finally:
        store.close()


def publish_dataset(root, fingerprint):
    """Explicit pointer activation after complete, shallow sealed validation."""
    from rainmapper_core.mushroom_rebuild_snapshot import gis_file_records
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', fingerprint):
        raise ValueError('invalid_geography_dataset_fingerprint')
    root = Path(root).resolve()/'datasets'/datasets.DEFAULT_DATASET_ID
    target = root/'versions'/fingerprint
    records = gis_file_records(target)
    if datasets._canonical_fingerprint(records) != fingerprint:
        raise ValueError('geography_dataset_fingerprint_mismatch')
    temporary = root/'.current.next'
    if temporary.exists() or temporary.is_symlink():
        raise ValueError('geography_activation_already_in_progress')
    temporary.symlink_to('versions/'+fingerprint)
    os.replace(temporary, root/'current')
    return {'fingerprint': fingerprint, 'files': len(records), 'activated': True}
