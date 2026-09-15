"""Sealed public geography: explicit media publication and persistent worker cache.

Only the small CURRENT.json is watched by HA. Raster checksums are prepared
before import and verified while downloading on the worker, never on a click.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import threading
import time

from rainmapper_core import mushroom_map_volume as volume
from rainmapper_core.mushroom_map_queries import QueryError
from rainmapper_core.mushroom_geography_store import (
    ObjectStore, SourceIdentities, IDENTITIES_FILE, receipt_stamp,
)

CHUNK_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024**3
_STORE_LOCK = threading.Lock()
RETENTION_SECONDS = 150  # Longer than the ephemeral map query TTL.


def encode(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def fingerprint(data):
    return 'sha256:' + hashlib.sha256(encode(data)).hexdigest()


def valid_reference(ref):
    fp = ref.get('fingerprint') if isinstance(ref, dict) else None
    if not isinstance(fp, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', fp):
        raise ValueError('invalid_geography_reference')
    return fp


def read_json(path, limit):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('geography_metadata_limit')
    return json.loads(raw)


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(encode(data))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def checked_manifest(data, fp=None):
    volume.validate_manifest(data, sealed=True)
    if data['bytes'] > MAX_TOTAL_BYTES:
        raise ValueError('geography_volume_limit')
    geo = data.get('geography')
    allowed = set(volume.GEO_FILES + volume.GEO_ROOTS + ('ecology_ph_source', 'municipalities_edition'))
    if not isinstance(geo, dict) or set(geo) - allowed:
        raise ValueError('invalid_geography_configuration')
    files = {row['path'] for row in data['files']}
    # Files cannot also be directories; reject before any cache materialization.
    for path in files:
        if any(p.as_posix() in files for p in Path(path).parents if p.as_posix() != '.'):
            raise ValueError('geography_path_collision')
        if path in {'manifest.json', 'verified.json', IDENTITIES_FILE}:
            raise ValueError('geography_reserved_path')
    for key in volume.GEO_FILES + volume.GEO_ROOTS:
        if key not in geo:
            continue
        value = geo[key]
        if not isinstance(value, str):
            raise ValueError('invalid_geography_path')
        volume.local(Path('/'), value)
        if key in volume.GEO_FILES and value not in files:
            raise ValueError('geography_dependency_missing')
        if key in volume.GEO_ROOTS and not any(p.startswith(value + '/') for p in files):
            raise ValueError('geography_root_empty')
    if geo.get('ecology_ph_source', 'soilgrids') not in {'soilgrids', 'openlandmap'}:
        raise ValueError('invalid_geography_ph_source')
    if not isinstance(geo.get('municipalities_edition', ''), str) or len(geo.get('municipalities_edition', '')) > 80:
        raise ValueError('invalid_geography_edition')
    if fp is not None and fingerprint(data) != fp:
        raise ValueError('geography_manifest_hash_mismatch')
    return data


def config_for_geography(config, root, manifest, identities=None):
    result = dict(config)
    identities = identities or SourceIdentities(Path(root)/IDENTITIES_FILE if (Path(root)/IDENTITIES_FILE).is_file() else None)
    for key, value in manifest['geography'].items():
        if key in volume.GEO_FILES:
            result[key] = str(identities.resolve(Path(root)/value))
        elif key in volume.GEO_ROOTS:
            result[key] = str(volume.local(Path(root), value))
        else:
            result[key] = value
    if identities.manifest:
        result['geography_sources'] = str(identities.manifest)
    return result


def publish(root, generation, *, restore_timestamps=False):
    """Offline/import boundary: reuse sealed hashes and check file stats once."""
    root = Path(root).resolve()
    if not isinstance(generation, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', generation):
        raise ValueError('invalid_geography_generation')
    destination = volume.local(root, 'generations/' + generation)
    manifest = checked_manifest(read_json(destination/'manifest.json', volume.MAX_MANIFEST_BYTES))
    identities = SourceIdentities(destination/IDENTITIES_FILE if (destination/IDENTITIES_FILE).exists() else None)
    for row in manifest['files']:
        source = volume.local(destination, row['path'])
        stat = source.stat()
        if identities.root is None and restore_timestamps and source.is_file() and stat.st_size == row['bytes'] and stat.st_mtime_ns != row['mtime_ns']:
            os.utime(source, ns=(stat.st_atime_ns, row['mtime_ns']))
            stat = source.stat()
        if not source.is_file() or identities.stamp(source) != [row['bytes'], row['mtime_ns']]:
            raise ValueError('geography_source_changed:' + row['path'])
    ref = {'format': 'map_geography_publication_v1', 'generation': generation, 'fingerprint': fingerprint(manifest)}
    atomic_json(root/'CURRENT.json', ref)
    return {**ref, 'files': manifest['file_count'], 'bytes': manifest['bytes'], 'hashed_asset_bytes': 0}


class GeographyPublication:
    """HA only reads the pointer and a bounded sealed manifest after publication."""
    def __init__(self, root, *, start=True):
        self.root = Path(root).resolve()
        self.lock = threading.RLock()
        self.signature = None
        self.current = None
        self.snapshots = {}
        self.stop = threading.Event()
        self.thread = None
        self.last_error = None
        try:
            self.refresh()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.last_error = type(error).__name__
        if start:
            self.thread = threading.Thread(target=self._loop, name='map-geography-publication', daemon=True)
            self.thread.start()

    def _signature(self):
        stat = (self.root/'CURRENT.json').stat()
        return stat.st_ino, stat.st_size, stat.st_mtime_ns

    def _loop(self):
        while not self.stop.wait(2):
            try:
                self.refresh()
            except (OSError, ValueError, KeyError, TypeError) as error:
                self.last_error = type(error).__name__

    def refresh(self):
        sig = self._signature()
        with self.lock:
            if sig == self.signature:
                return
        ref = read_json(self.root/'CURRENT.json', 1024)
        fp = valid_reference(ref)
        generation = ref.get('generation')
        if ref.get('format') != 'map_geography_publication_v1' or not isinstance(generation, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', generation):
            raise ValueError('invalid_geography_publication')
        destination = volume.local(self.root, 'generations/' + generation)
        manifest = checked_manifest(read_json(destination/'manifest.json', volume.MAX_MANIFEST_BYTES), fp)
        sources_file = ref.get('sources_file')
        if sources_file is not None and (not isinstance(sources_file, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.json', sources_file)):
            raise ValueError('invalid_geography_sources_file')
        sources_path = self.root/sources_file if sources_file else destination/IDENTITIES_FILE
        identities = SourceIdentities(sources_path if sources_file or sources_path.exists() else None)
        if sources_file and not identities.portable:
            raise ValueError('invalid_portable_geography_sources')
        if identities.portable:
            for row in manifest['files']:
                identity = identities.records.get(row['path'], {})
                if identity.get('sha256') != row['sha256'] or identity.get('logical') != [row['bytes'], row['mtime_ns']]:
                    raise ValueError('geography_identity_manifest_mismatch')
            destination = identities.root
        if sig != self._signature():
            raise ValueError('geography_publication_changed')
        with self.lock:
            now = time.monotonic()
            self.snapshots = {k: v for k, v in self.snapshots.items() if now-v['used'] < RETENTION_SECONDS}
            if fp not in self.snapshots and len(self.snapshots) >= 8:
                raise ValueError('geography_publication_busy')
            self.snapshots[fp] = {'root': destination, 'manifest': manifest,
                                  'identities': identities,
                                  'files': {r['path']: r for r in manifest['files']}, 'used': now}
            self.current, self.signature, self.last_error = fp, sig, None

    def reference(self):
        with self.lock:
            try:
                if self.signature != self._signature() or not self.current:
                    raise ValueError('changed')
            except (OSError, ValueError) as error:
                raise QueryError('geography_not_ready', 503) from error
            self.snapshots[self.current]['used'] = time.monotonic()
            return {'fingerprint': self.current}

    def lookup(self, fp):
        with self.lock:
            row = self.snapshots.get(fp)
            if row is None or (fp != self.current and time.monotonic()-row['used'] > RETENTION_SECONDS):
                raise QueryError('geography_not_authorized', 403)
            row['used'] = time.monotonic()
            return row

    def object(self, fp, path, offset=0):
        snapshot = self.lookup(fp)
        row = snapshot['files'].get(path) if isinstance(path, str) else None
        if row is None:
            raise QueryError('geography_object_not_authorized', 403)
        if type(offset) is not int or not 0 <= offset <= row['bytes']:
            raise QueryError('invalid_geography_offset')
        logical = snapshot['root']/path
        if snapshot['identities'].stamp(logical) != [row['bytes'], row['mtime_ns']]:
            raise QueryError('geography_object_changed', 409)
        source = snapshot['identities'].resolve(logical)
        return source, min(CHUNK_BYTES, row['bytes']-offset)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=3)


class GeographyCache:
    """Worker-owned public cache. Preparation cooperates with the background lane."""
    def __init__(self, worker_root, coordinator_id, post, *, background_slot=None):
        from rainmapper_core.mushroom_worker_config import validate_coordinator_id
        self.worker_root = Path(worker_root)
        self.legacy_shared = self.worker_root/'map-geography'
        self.shared = self.worker_root/'geography'
        self.root = self.shared/'coordinators'/validate_coordinator_id(coordinator_id)
        self.objects = self.shared/'objects'
        self.store = ObjectStore(self.shared)
        self.post = post
        self.background_slot = background_slot or threading.Lock()
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.lock = threading.RLock()
        self.requested = None
        self.current = None
        self.snapshots = {}
        self.last_sync = {}
        self.last_error = None
        self.cleanup_due = None
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._loop, name='map-geography-cache', daemon=True)
        self.thread.start()

    def request(self, reference):
        fp = valid_reference(reference)
        with self.lock:
            if self.requested != fp:
                self.requested = fp
                self.wake.set()

    def reference(self):
        with self.lock:
            return self.current

    def lookup(self, reference):
        fp = valid_reference(reference)
        with self.lock:
            if fp not in self.snapshots:
                raise ValueError('geography_cache_not_ready')
            row = self.snapshots[fp]
            row['used'] = time.monotonic()
            return row['root'], row['manifest']

    @contextmanager
    def _slot(self):
        while not self.stop.is_set():
            if self.background_slot.acquire(timeout=.1):
                break
        else:
            raise InterruptedError('geography_stopped')
        try:
            yield
        finally:
            self.background_slot.release()
        # Yield between bounded downloads to scientific background claims.
        self.stop.wait(.02)

    def _hash_existing(self, path):
        check, count = hashlib.sha256(), 0
        with path.open('rb') as stream:
            while True:
                with self._slot():
                    chunk = stream.read(CHUNK_BYTES)
                    if not chunk: break
                    check.update(chunk); count += len(chunk)
        return check, count

    def _loop(self):
        while not self.stop.is_set():
            self.wake.wait(2)
            self.wake.clear()
            with self.lock:
                fp = self.requested
            if fp and fp != self.reference():
                try:
                    self.prepare({'fingerprint': fp})
                    self.last_error = None
                except Exception as error:
                    self.last_error = type(error).__name__
                    if self.cleanup_due is None:
                        self.cleanup_due = time.monotonic()+RETENTION_SECONDS+1
                    self.stop.wait(5)
            if self.cleanup_due is not None and time.monotonic() >= self.cleanup_due:
                try:
                    with _STORE_LOCK, self._slot():
                        self.prune()
                    self.cleanup_due = (time.monotonic()+RETENTION_SECONDS+1
                                        if len(list((self.root/'versions').iterdir())) > 1 else None)
                except (OSError, ValueError, InterruptedError):
                    self.cleanup_due = time.monotonic()+RETENTION_SECONDS+1

    @staticmethod
    def _object_key(row):
        return row['sha256']

    def _legacy_sources(self):
        """Bounded migration hints; validate receipts/content before adoption."""
        sources = {}
        try:
            receipts = read_json(self.legacy_shared/'verified-objects.json', volume.MAX_MANIFEST_BYTES)
            for key, state in receipts.items():
                if re.fullmatch(r'[0-9a-f]{64}-[0-9]+', key):
                    sources.setdefault(key[:64], (self.legacy_shared/'objects'/key, state))
        except (OSError, ValueError, AttributeError):
            pass
        root = self.worker_root/'datasets'/'mushroom_gis_v0'/'current'
        try:
            data = read_json(root/'dataset_cache_manifest.json', volume.MAX_MANIFEST_BYTES)
            for row in data['files']:
                if re.fullmatch(r'[0-9a-f]{64}', row['sha256']):
                    sources.setdefault(row['sha256'], (volume.local(root, row['path']), None))
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return sources

    def _validate_object(self, row):
        """Warm receipts are cheap; repair changed content on the worker only."""
        obj = self.objects/self._object_key(row)
        with self.store.locked():
            try:
                self.store.find(row['sha256'], row['bytes'])
                return 0
            except ValueError:
                before = receipt_stamp(obj)
        count, valid = 0, before[0] == row['bytes']
        if valid:
            check, count = self._hash_existing(obj)
            valid = check.hexdigest() == row['sha256']
        with self.store.locked():
            if receipt_stamp(obj) != before:
                raise ValueError('geography_object_changed_during_check')
            if valid:
                self.store.remember(obj)
            else:
                obj.unlink()  # Only the cache object name; retained views keep their inode.
        return count

    def prepare(self, reference):
        # Only public preparations serialize; the scientific background slot is
        # released between chunks and online computation never takes this lock.
        with _STORE_LOCK:
            return self._prepare(reference)

    def _prepare(self, reference):
        fp = valid_reference(reference)
        with self.lock:
            if fp in self.snapshots:
                self.current = fp
                return
        target = self.root/'versions'/fp[7:]
        target.parent.mkdir(parents=True, exist_ok=True)
        self.objects.mkdir(parents=True, exist_ok=True)
        self.prune()
        if not target.exists() and len(list(target.parent.iterdir())) >= 8:
            raise ValueError('geography_generation_limit')
        target.mkdir(parents=True, exist_ok=True)
        transferred = metadata = fetched = hashed = 0
        try:
            manifest = checked_manifest(read_json(target/'manifest.json', volume.MAX_MANIFEST_BYTES), fp)
        except (OSError, ValueError):
            with self._slot(), self.post('geography_manifest', reference) as response:
                raw = response.read(volume.MAX_MANIFEST_BYTES+1)
            if len(raw) > volume.MAX_MANIFEST_BYTES:
                raise ValueError('geography_metadata_limit')
            manifest = checked_manifest(json.loads(raw), fp)
            metadata = len(raw)
            atomic_json(target/'manifest.json', manifest)
        self.objects.mkdir(parents=True, exist_ok=True)
        legacy = self._legacy_sources()
        unique = {r['sha256']: r for r in manifest['files']}
        missing = sum(r['bytes'] for r in unique.values()
                      if not (self.objects/self._object_key(r)).exists()
                      and not (r['sha256'] in legacy and legacy[r['sha256']][0].is_file()))
        if missing + 64*1024**2 > shutil.disk_usage(self.shared).free:
            raise ValueError('geography_disk_space')
        # One stat pass on restart/activation. No asset stat/hash during warm polls.
        for row in manifest['files']:
            if self.stop.is_set():
                raise InterruptedError('geography_stopped')
            with self.lock:
                if self.requested is not None and self.requested != fp:
                    raise InterruptedError('geography_superseded')
            obj = self.objects/self._object_key(row)
            dst = volume.local(target, row['path'])
            if obj.exists():
                hashed += self._validate_object(row)
            if not obj.exists() and row['sha256'] in legacy:
                source, trusted = legacy[row['sha256']]
                if source.is_file() and source.stat().st_size == row['bytes']:
                    before = receipt_stamp(source)
                    valid = trusted == self._stamp(source)
                    if not valid:
                        check, count = self._hash_existing(source); hashed += count
                        valid = check.hexdigest() == row['sha256']
                    if valid:
                        with self.store.locked():
                            self.store.adopt_checked(source, row['sha256'], row['bytes'], before)
            if not obj.exists():
                if row['bytes'] + 64*1024**2 > shutil.disk_usage(self.shared).free:
                    raise ValueError('geography_disk_space')
                partial = self.root/'partial'/self._object_key(row)
                partial.parent.mkdir(parents=True, exist_ok=True)
                size = partial.stat().st_size if partial.exists() else 0
                if size > row['bytes']:
                    partial.unlink(); size = 0
                check = hashlib.sha256()
                if size:
                    check, count = self._hash_existing(partial); hashed += count
                with partial.open('ab') as out:
                    while size < row['bytes']:
                        count = min(CHUNK_BYTES, row['bytes']-size)
                        with self._slot(), self.post('geography_object', reference, file=row['path'], offset=size) as response:
                            remaining = count
                            while remaining:
                                chunk = response.read(min(1024*1024, remaining))
                                if not chunk:
                                    raise ValueError('geography_download_truncated')
                                out.write(chunk); check.update(chunk)
                                size += len(chunk); transferred += len(chunk); hashed += len(chunk); remaining -= len(chunk)
                            if response.read(1):
                                raise ValueError('geography_download_oversized')
                        if self.stop.is_set():
                            raise InterruptedError('geography_stopped')
                    out.flush(); os.fsync(out.fileno())
                if check.hexdigest() != row['sha256']:
                    partial.unlink()
                    raise ValueError('geography_checksum_mismatch')
                os.utime(partial, ns=(row['mtime_ns'], row['mtime_ns']))
                # Atomic complete objects only. Other associations may have fetched the same hash.
                with self.store.locked():
                    if self.store.find(row['sha256'], row['bytes']) is None:
                        os.replace(partial, obj)
                        self.store.remember(obj)
                    else:
                        partial.unlink()
                fetched += 1
            with self.store.locked():
                if dst.exists() and not os.path.samefile(dst, obj):
                    dst.unlink()  # Only a worker-owned generation view.
                self.store.link(obj, dst)
        with self.store.locked():
            self.store.seal_view(target, manifest['files'])
        atomic_json(target/'verified.json', {'fingerprint': fp, 'files': manifest['file_count']})
        atomic_json(self.root/'CURRENT.json', {'fingerprint': fp})
        with self.lock:
            self.snapshots[fp] = {'root': target, 'manifest': manifest, 'used': time.monotonic()}
            self.current = fp
            self.last_sync = {'fingerprint': fp, 'transferred_bytes': transferred, 'metadata_bytes': metadata,
                              'fetched_files': fetched, 'hashed_bytes': hashed, 'files': manifest['file_count']}
            atomic_json(self.root/'last-sync.json', self.last_sync)
        self.prune()
        self.cleanup_due = time.monotonic()+RETENTION_SECONDS+1

    @staticmethod
    def _stamp(path):
        stat = path.stat()
        return [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino]

    def prune(self):
        """Worker cache only: preserve active/recent views, shared objects by hardlink refs."""
        with self.store.locked():
            self._prune_locked()

    def _prune_locked(self):
        now = time.time()
        rows = self.store.db.execute('SELECT sha,state FROM objects LIMIT 20001').fetchall()
        if len(rows) > 20000:
            raise ValueError('geography_receipt_limit')
        verified = {key: json.loads(state) for key, state in rows}
        trusted = {key for key, stamp in verified.items()
                   if (self.objects/key).is_file() and receipt_stamp(self.objects/key) == stamp}
        versions = self.root/'versions'
        with self.lock:
            protected = {fp[7:] for fp, row in self.snapshots.items()
                         if fp in (self.current, self.requested) or time.monotonic()-row['used'] < RETENTION_SECONDS}
            if self.requested:
                protected.add(self.requested[7:])
            for path in versions.iterdir():
                if path.name not in protected and now-path.stat().st_mtime > RETENTION_SECONDS:
                    shutil.rmtree(path)
                    self.snapshots.pop('sha256:'+path.name, None)
        partial = self.root/'partial'
        pending_keys = set()
        if self.requested:
            try:
                pending = read_json(versions/self.requested[7:]/'manifest.json', volume.MAX_MANIFEST_BYTES)
                pending_keys = {self._object_key(row) for row in pending['files']}
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if partial.exists():
            for path in partial.iterdir():
                if path.name not in pending_keys and now-path.stat().st_mtime > RETENTION_SECONDS:
                    path.unlink()
        for path in self.objects.iterdir():
            stat = path.stat()
            if stat.st_nlink == 1:
                path.unlink()  # Store lock excludes downloads; no retained view references it.
                self.store.db.execute('DELETE FROM objects WHERE sha=?', (path.name,))
        for key in trusted:
            path = self.objects/key
            if path.is_file() and receipt_stamp(path)[:4] == verified[key][:4]:
                self.store.remember(path)

    def close(self):
        self.stop.set(); self.wake.set()
        if self.thread:
            self.thread.join(timeout=3)
        if not self.thread or not self.thread.is_alive():
            self.store.close()


class PublishedPointExecutor:
    """Local parity: read the same immutable media publication as the worker."""
    def __init__(self, config, root, publication, *, executor_factory=None):
        from rainmapper_core.mushroom_map_execution import PointExecutor
        self.config, self.root, self.publication = config, root, publication
        self.factory = executor_factory or PointExecutor
        self.executor = None
        self.fingerprint = None
        self.calendar_timezone = config.get('calendar_timezone', 'Europe/Madrid')
        self.model = True if config.get('models_root') else None

    def _prepare(self, ref):
        fp = valid_reference(ref)
        if self.fingerprint != fp:
            row = self.publication.lookup(fp)
            new = self.factory(config_for_geography(self.config, row['root'], row['manifest'], row['identities']), self.root)
            if self.executor:
                self.executor.close()
            self.executor, self.fingerprint = new, fp
            self.model = new.model

    def ready(self):
        self._prepare(self.publication.reference())
        return self.executor.ready()

    def execute_snapshot(self, request, reference):
        self._prepare(reference['geography'])
        return self.executor.execute(request)

    def close(self):
        if self.executor:
            self.executor.close()
