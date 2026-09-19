"""Small map snapshots over the already published Predictor objects.

HA never hashes model/weather objects here. It snapshots only mutable small
inputs; immutable objects are linked from the existing sealed publication.
Workers reuse the Predictor object store with an independent, bounded current
pointer for each coordinator's map. No training jobs or TAR transports.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import threading
import time
from urllib.request import Request, urlopen

from rainmapper_core import mushroom_predictor_runtime as runtime
from rainmapper_core.mushroom_map_execution import PointExecutor
from rainmapper_core.mushroom_map_queries import WORKER_PATH, QueryError, TTL, MAX_QUERIES
from rainmapper_core.mushroom_worker_config import validate_coordinator_id
from rainmapper_core.weather_history_dataset import pin_weather_generation

MAX_METADATA = 8 * 1024 * 1024
MAX_SMALL_FILE = 1024 * 1024
MAX_FILES = 4096
PRIVATE_FILES = {
    'profiles': 'data/mushroom_profiles.json',
    'forest_catalogs': 'data/forest_catalogs.json',
    'ecology_catalogs': 'data/mushroom_reference_catalogs.json',
    'gis_mappings': 'data/mushroom_gis_mappings.json',
    'model_registry': 'data/mushroom_ml_version_registry.json',
    'weather_stations': 'data/stations.txt',
}


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def model_registry_identity(registry):
    """Compare executable generations, excluding only installation audit notes.

    Promotion records its approver and previous generation in ``installation``;
    those notes do not select model files. Keep installed_generation_id and all
    generation contracts/artifact metadata in the comparison.
    """
    result = {k: v for k, v in registry.items() if k != 'preferred_version_id'}
    result['versions'] = [
        {k: v for k, v in row.items() if k != 'installation'}
        if isinstance(row, dict) else row for row in registry.get('versions', [])
    ]
    return result


def read_small(path, limit=MAX_SMALL_FILE):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('map_metadata_limit')
    return raw


def manifest_identity(manifest):
    return {k: manifest[k] for k in ('schema_version', 'kind', 'contracts', 'files')}


def checked_manifest(value, fingerprint=None):
    rows = value.get('files') if isinstance(value, dict) else None
    if not isinstance(rows, list) or not 0 < len(rows) <= MAX_FILES:
        raise ValueError('map_file_count_limit')
    checked = runtime.validate_manifest(value)
    for row in rows:
        p = PurePosixPath(row['path'])
        if (p.as_posix() != row['path'] or '\\' in row['path'] or
            p.parts[0] not in ('data', 'models', 'weather') or
            not re.fullmatch(r'sha256:[0-9a-f]{64}', row['sha256'])):
            raise ValueError('map_unsafe_object')
    if len(encode(checked)) > MAX_METADATA:
        raise ValueError('map_metadata_limit')
    if digest(encode(manifest_identity(checked))) != checked['fingerprint']:
        raise ValueError('map_manifest_identity')
    if fingerprint is not None and checked['fingerprint'] != fingerprint:
        raise ValueError('map_manifest_identity')
    if checked['size_bytes'] != sum(r['size_bytes'] for r in rows):
        raise ValueError('map_manifest_size')
    return checked


def config_for_runtime(config, root):
    root = Path(root)
    return {**config, **{k: str(root/v) for k, v in PRIVATE_FILES.items()},
            'weather_data': str(root/'weather'), 'models_root': str(root/'models')}


def file_state(root, manifest):
    """Worker-only, once on activation/restart; never on a resident query."""
    result = {}
    for row in manifest['files']:
        stat = (root/row['path']).stat()
        result[row['path']] = [stat.st_size, stat.st_mtime_ns, stat.st_ino]
    return result


def invalidate_changed_receipt(root, manifest):
    try:
        saved = json.loads(read_small(root/'map-files-state.json', MAX_METADATA))
        if saved == file_state(root, manifest):
            return
    except (OSError, ValueError):
        pass
    (root/'verified-runtime.json').unlink(missing_ok=True)


class MapPublication:
    """Background preparation; online path stats only the few mutable anchors."""
    def __init__(self, config, root, *, publication_path=None, cache_root=None, start=True):
        self.config = config
        self.root = Path(root)
        self.publication = Path(publication_path or runtime.default_publication_path())
        self.cache = Path(cache_root or self.publication.parent/'map-snapshots')
        self.inputs = {k: (self.root/config[k]).resolve() for k in PRIVATE_FILES}
        self.current_path = (self.root/config['weather_data']).resolve()/'weather-history/CURRENT.json'
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.signature = None
        self.current = None
        self.snapshots = {}
        self.last_error = None
        self.metrics = {'small_hashed_bytes': 0, 'heavy_hashed_bytes': 0, 'publications': 0}
        self.thread = None
        self.small_cache = {}
        if start:
            self.thread = threading.Thread(target=self._loop, daemon=True, name='map-data-publication')
            self.thread.start()

    def _signature(self):
        result = []
        for p in dict.fromkeys([self.publication, self.current_path, *self.inputs.values()]):
            stat = p.stat()
            result.append((str(p), stat.st_size, stat.st_mtime_ns, stat.st_ino))
        return tuple(result)

    def _small(self, path):
        stat = path.stat()
        stamp = (stat.st_size, stat.st_mtime_ns, stat.st_ino)
        cached = self.small_cache.get(path)
        if cached and cached[0] == stamp:
            return cached[1:]
        raw = read_small(path)
        sha = digest(raw)
        self.small_cache[path] = (stamp, raw, sha)
        self.metrics['small_hashed_bytes'] += len(raw)
        return raw, sha

    def close(self):
        self.stop.set(); self.wake.set()
        if self.thread: self.thread.join(timeout=2)
        with self.lock:
            for row in self.snapshots.values():
                row["lease"].__exit__(None, None, None)

    def _loop(self):
        while not self.stop.is_set():
            try: self.refresh()
            except Exception as error:
                self.last_error = type(error).__name__ + ': ' + str(error)
            self.wake.wait(2); self.wake.clear()

    def reference(self):
        with self.lock:
            try: unchanged = self.current is not None and self._signature() == self.signature
            except OSError: unchanged = False
            if not unchanged:
                self.wake.set()
                raise QueryError('map_data_not_ready', 503)
            self.snapshots[self.current]['used'] = time.monotonic()
            return {'fingerprint': self.current,
                    **({'required_capabilities': ['prediction_model_policy_v1']}
                       if self.snapshots[self.current].get('model_suspensions') else {})}

    def _prune(self):
        now = time.monotonic()
        for key, row in list(self.snapshots.items()):
            if key != self.current and now-row['used'] > TTL+30:
                row['lease'].__exit__(None, None, None)
                shutil.rmtree(row['root'])
                del self.snapshots[key]
        # Orphans left by a coordinator restart are disposable after the lease TTL.
        if self.cache.exists():
            live = {row['root'] for row in self.snapshots.values()}
            for p in self.cache.iterdir():
                if p.is_dir() and p not in live and time.time()-p.stat().st_mtime > TTL+30:
                    shutil.rmtree(p)

    def refresh(self):
        signature = self._signature()
        with self.lock:
            self._prune()
            if signature == self.signature and self.current:
                row = self.snapshots[self.current]
                if time.monotonic()-row['lease_started'] > 300:
                    lease = pin_weather_generation(self.current_path.parent.parent, lease_seconds=600)
                    generation = lease.__enter__()
                    if generation.generation_id != row['generation_id']:
                        lease.__exit__(None, None, None)
                        raise ValueError('map_weather_publication_pending')
                    row['lease'].__exit__(None, None, None)
                    row.update(lease=lease, lease_started=time.monotonic())
                return
            if len(self.snapshots) >= MAX_QUERIES+1:
                raise ValueError('map_snapshot_limit')
        publication = json.loads(read_small(self.publication, MAX_METADATA))
        base = checked_manifest(publication['manifest'])
        inputs = {k: self._small(p) for k, p in self.inputs.items()}
        raw_inputs = {k: v[0] for k, v in inputs.items()}
        sources = publication['sources']
        base_rows = {r['path']: r for r in base['files']}
        # A profile edit may dirty the Predictor publication. It is independent
        # of its sealed weather/models; verify the two live generation anchors.
        weather_current = 'weather/weather-history/CURRENT.json'
        current_raw, current_sha = self._small(self.current_path)
        if current_sha != base_rows[weather_current]['sha256']:
            raise ValueError('map_weather_publication_pending')
        registry = json.loads(raw_inputs['model_registry'])
        sealed_registry = json.loads(read_small(sources['data/mushroom_ml_version_registry.json']))
        if model_registry_identity(registry) != model_registry_identity(sealed_registry):
            raise ValueError('map_model_publication_pending')
        selected = [dict(r) for r in base['files']
                    if r['path'].startswith(('weather/', 'models/'))]
        if len(selected)+len(raw_inputs) > MAX_FILES:
            raise ValueError('map_file_count_limit')
        small = {PRIVATE_FILES[k]: raw for k, raw in raw_inputs.items()}
        small[weather_current] = current_raw
        hashes = {PRIVATE_FILES[k]: v[1] for k, v in inputs.items()}
        hashes[weather_current] = current_sha
        selected = [r for r in selected if r['path'] not in small]
        for path, raw in small.items():
            selected.append({'role': path.split('/')[0], 'path': path,
                             'sha256': hashes[path], 'size_bytes': len(raw)})
        manifest = {'schema_version': runtime.SCHEMA_VERSION, 'kind': runtime.MANIFEST_KIND,
                    'contracts': {**base['contracts'], 'map': 'private_map_inputs_v1'},
                    'files': sorted(selected, key=lambda r: r['path'])}
        manifest['fingerprint'] = digest(encode(manifest))
        manifest['size_bytes'] = sum(r['size_bytes'] for r in selected)
        checked_manifest(manifest)
        self.cache.mkdir(parents=True, exist_ok=True)
        destination = self.cache/manifest['fingerprint'][7:]
        lease = pin_weather_generation(self.current_path.parent.parent,
                                       generation_id=json.loads(current_raw)['generation_id'], lease_seconds=600)
        generation = lease.__enter__()
        staging = None
        retained = False
        try:
            staging = Path(tempfile.mkdtemp(prefix='.building-', dir=self.cache))
            for row in manifest['files']:
                path = row['path']; target = staging/path; target.parent.mkdir(parents=True, exist_ok=True)
                if path in small:
                    target.write_bytes(small[path])
                else:
                    source = Path(sources[path]); state = publication['source_state'][path]; stat = source.stat()
                    if stat.st_size != row['size_bytes'] or stat.st_mtime_ns != state['mtime_ns']:
                        raise ValueError('map_sealed_source_changed')
                    # Do not turn a cross-filesystem configuration into GB copies.
                    if path.startswith('weather/'):
                        target.symlink_to(source)  # Protected by the dataset's existing lease.
                    else:
                        os.link(source, target)
            (staging/'manifest.json').write_bytes(encode(manifest))
            if signature != self._signature():
                raise ValueError('map_inputs_changed_during_publication')
            with self.lock:
                if not destination.exists(): os.replace(staging, destination)
                previous = self.snapshots.get(manifest['fingerprint'])
                if previous: previous['lease'].__exit__(None, None, None)
                self.snapshots[manifest['fingerprint']] = {'root': destination, 'manifest': manifest,
                    'used': time.monotonic(), 'lease': lease, 'lease_started': time.monotonic(),
                    'generation_id': generation.generation_id,
                    'model_suspensions': bool(registry.get('prediction_model_suspensions'))}
                retained = True
                self.current = manifest['fingerprint']; self.signature = signature; self.last_error = None
                self.metrics['publications'] += 1
        finally:
            if not retained: lease.__exit__(None, None, None)
            if staging is not None and staging.exists(): shutil.rmtree(staging)

    def lookup(self, fingerprint):
        with self.lock:
            row = self.snapshots.get(fingerprint)
            if row is None or time.monotonic()-row['lease_started'] >= 600:
                raise QueryError('map_runtime_not_authorized', 403)
            row['used'] = time.monotonic()
            return row

    def object(self, fingerprint, logical_path):
        snapshot = self.lookup(fingerprint)
        row = next((r for r in snapshot['manifest']['files'] if r['path'] == logical_path), None)
        if row is None: raise QueryError('map_object_not_authorized', 403)
        return snapshot['root']/row['path'], row['size_bytes']


class CachedPointExecutor:
    """One resident runtime per association; sync never overlaps its calculation."""
    def __init__(self, config, root, coordinator, worker_id, worker_data_dir, *, executor_factory=PointExecutor, background_slot=None):
        self.config, self.root = config, root
        self.coordinator, self.worker_id = coordinator, worker_id
        key = validate_coordinator_id(coordinator['coordinator_id'])
        shared = Path(worker_data_dir).resolve()/'predictor-runtime'
        self.cache = shared/'coordinators'/key/'map'
        self.objects = shared/'objects'
        self.executor_factory = executor_factory
        self.executor = None
        self.fingerprint = None
        self.lock = threading.RLock()
        self.last_sync = {}
        self.geography = None
        self.executor_geography = None
        if config.get('geography_runtime'):
            from rainmapper_core.mushroom_map_geography_runtime import GeographyCache
            self.geography = GeographyCache(worker_data_dir, key, self._post, background_slot=background_slot)
            self.geography.start()

    def ready(self):
        # Private inputs arrive over the coordinator connection, never local mounts.
        return True

    def _post(self, action, reference, **extra):
        body = encode({'protocol': 'map_report_v1', 'worker_id': self.worker_id,
                       'action': action, 'fingerprint': reference['fingerprint'], **extra})
        req = Request(self.coordinator['rainmapper_url'].rstrip('/')+WORKER_PATH, data=body,
                      headers={'Authorization': 'Bearer '+self.coordinator['token'], 'Content-Type': 'application/json'})
        return urlopen(req, timeout=30 if action.startswith('geography_') else 120)

    def prepare(self, reference):
        with self.lock:
            fp = reference.get('fingerprint') if isinstance(reference, dict) else None
            if not isinstance(fp, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', fp):
                raise ValueError('invalid_map_reference')
            geo_ref = reference.get('geography')
            geography = self.geography.lookup(geo_ref) if self.geography else None
            geo_fp = geo_ref['fingerprint'] if geography else None
            if self.fingerprint == fp and self.executor_geography == geo_fp and self.executor is not None:
                self.last_sync = {'transferred_size_bytes': 0, 'fetched_file_count': 0, 'metadata_bytes': 0, 'resident': True}
                return
            manifest_path = self.cache/'versions'/fp[7:]/'manifest.json'
            metadata_bytes = 0
            try: manifest = checked_manifest(json.loads(read_small(manifest_path, MAX_METADATA)), fp)
            except (OSError, ValueError):
                with self._post('runtime_manifest', reference) as response: raw = response.read(MAX_METADATA+1)
                if len(raw) > MAX_METADATA: raise ValueError('map_metadata_limit')
                metadata_bytes = len(raw); manifest = checked_manifest(json.loads(raw), fp)
            rows = {r['path']: r for r in manifest['files']}
            if manifest_path.is_file():
                invalidate_changed_receipt(manifest_path.parent, manifest)
            current = runtime.current_runtime(self.cache)
            if current and current != manifest_path.parent:
                try:
                    old_manifest = checked_manifest(json.loads(read_small(current/'manifest.json', MAX_METADATA)))
                    invalidate_changed_receipt(current, old_manifest)
                except (OSError, ValueError):
                    (current/'verified-runtime.json').unlink(missing_ok=True)
            def fetch(path, target):
                with self._post('runtime_object', reference, file=path) as response, target.open('xb') as out:
                    size = 0
                    while chunk := response.read(min(1024*1024, rows[path]['size_bytes']-size+1)):
                        size += len(chunk)
                        if size > rows[path]['size_bytes']: raise ValueError('map_object_limit')
                        out.write(chunk)
            destination, diagnostics = runtime.synchronize_runtime(self.cache, manifest, fetch, objects_root=self.objects)
            runtime._atomic_write_json(destination/'map-files-state.json', file_state(destination, manifest))
            if self.executor: self.executor.close()
            config = config_for_runtime(self.config, destination)
            if geography:
                from rainmapper_core.mushroom_map_geography_runtime import config_for_geography
                config = config_for_geography(config, *geography)
            self.executor = self.executor_factory(config, self.root)
            self.executor_geography = geo_fp
            self.fingerprint = fp
            self.last_sync = {**diagnostics, 'metadata_bytes': metadata_bytes}
            runtime._atomic_write_json(self.cache/'last-sync.json', {'fingerprint': fp, **self.last_sync})

    def execute_snapshot(self, request, reference):
        with self.lock:
            self.prepare(reference)
            return self.executor.execute(request)

    def close(self):
        if self.geography: self.geography.close()
        with self.lock:
            if self.executor: self.executor.close()
            self.executor = None
