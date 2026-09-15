"""Shared immutable public geography objects and logical source identities.

Objects are identified by content, never by their filename or timestamp. A
prepared reader still sees its original source identity through a sealed view.
This module never discovers or deletes files outside its own store.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import threading
import uuid

MAX_METADATA = 8 * 1024 * 1024
IDENTITIES_FILE = 'geography-sources.json'
PORTABLE_FORMAT = 'geography_source_identities_portable_v1'
_LOCK = threading.RLock()


def digest_key(value):
    value = str(value).removeprefix('sha256:')
    if not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('invalid_geography_content_id')
    return value


def relative_path(value):
    value = str(value)
    path = PurePosixPath(value)
    if not value or not path.parts or path.is_absolute() or '..' in path.parts or path.as_posix() != value:
        raise ValueError('invalid_geography_logical_path')
    return Path(*path.parts)


def physical_stamp(path):
    stat = Path(path).stat()
    return [stat.st_size, stat.st_mtime_ns, stat.st_ino, stat.st_dev]


def receipt_stamp(path):
    stat = Path(path).stat()
    return [stat.st_size, stat.st_mtime_ns, stat.st_ino, stat.st_dev, stat.st_ctime_ns]


def read_metadata(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_METADATA + 1)
    if len(raw) > MAX_METADATA:
        raise ValueError('geography_metadata_limit')
    return json.loads(raw)


def write_metadata(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_METADATA:
        raise ValueError('geography_metadata_limit')
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class SourceIdentities:
    """A bounded immutable view; one local stat per source access, no hashes.

ctime is deliberately not a reader identity: adding another hardlink must not
invalidate a running query. The store's verification receipts do include ctime
and are refreshed while holding the shared store lock after link mutations.
"""
    def __init__(self, manifest=None):
        self.root = None
        self.records = {}
        self.manifest = None
        self.portable = False
        self.physical_names = {}
        if manifest is None:
            return
        path = Path(manifest).resolve(strict=True)
        data = read_metadata(path)
        self.portable = data.get('format') == PORTABLE_FORMAT
        if not self.portable and data.get('format') != 'geography_source_identities_v1':
            raise ValueError('invalid_geography_source_identities')
        self.root = path.parent
        self.manifest = path
        records = data.get('files')
        if not isinstance(records, dict) or len(records) > 20000:
            raise ValueError('geography_identity_limit')
        for name, row in records.items():
            relative_path(name)
            digest_key(row['sha256'])
            logical = row['logical']
            if self.portable:
                relative_path(row['physical_path'])
                stored = row['stored']
                if (len(logical) != 2 or len(stored) != 2 or logical[0] != stored[0]
                        or any(type(v) is not int or v < 0 for v in logical + stored)):
                    raise ValueError('invalid_geography_identity')
                self.physical_names.setdefault(row['physical_path'], name)
                continue
            physical = row['physical']
            if (len(logical) != 2 or len(physical) != 4 or logical[0] != physical[0]
                    or any(type(v) is not int for v in logical + physical)):
                raise ValueError('invalid_geography_identity')
        self.records = records

    def _record(self, path):
        # Resolve containment even when a logical alias has no physical file.
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError('geography_source_outside_view')
        name = resolved.relative_to(self.root).as_posix()
        row = self.records.get(name) or self.records.get(self.physical_names.get(name))
        if row is None:
            raise ValueError('geography_source_changed')
        return row

    def resolve(self, path):
        """Resolve a declared logical file, without materializing filesystem links."""
        if not self.portable:
            return Path(path).resolve(strict=True)
        row = self._record(path)
        actual = (self.root / row['physical_path']).resolve(strict=True)
        if not actual.is_relative_to(self.root) or not actual.is_file():
            raise ValueError('geography_source_outside_view')
        return actual

    def stamp(self, path):
        path = Path(path)
        if self.root is None:
            stat = path.stat()
            return [stat.st_size, stat.st_mtime_ns]
        if self.portable:
            row = self._record(path)
            stat = self.resolve(path).stat()
            # Prepared after verified copy. Millisecond timestamps survive SMB;
            # inode/device/ctime are deliberately not part of a portable package.
            if [stat.st_size, stat.st_mtime_ns // 1_000_000] != row['stored']:
                raise ValueError('geography_source_changed')
            return row['logical']
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(self.root):
            raise ValueError('geography_source_outside_view')
        row = self.records.get(resolved.relative_to(self.root).as_posix())
        if row is None or physical_stamp(resolved) != row['physical']:
            raise ValueError('geography_source_changed')
        return row['logical']


class ObjectStore:
    """Receipt-backed store, shared by all public GIS consumers.

adopt_checked is an internal publication/download boundary: callers must have
verified the digest or a sealed receipt, and pass that source's checked stat.
No trust is inferred from filenames or equal sizes.
"""
    def __init__(self, root):
        self.root = Path(root)
        self.objects = self.root / 'objects'
        self.db = None

    @contextmanager
    def locked(self):
        # Short transactions only: downloads/hashes must run outside this lock.
        # Indexed receipts avoid rewriting a growing JSON document per object.
        with _LOCK:
            self.objects.mkdir(parents=True, exist_ok=True)
            if self.db is None:
                self.db = sqlite3.connect(self.root / 'receipts.sqlite', timeout=30,
                                          isolation_level=None, check_same_thread=False)
                self.db.execute('PRAGMA journal_mode=WAL')
                self.db.execute('PRAGMA synchronous=NORMAL')
                self.db.execute('CREATE TABLE IF NOT EXISTS objects (sha TEXT PRIMARY KEY, state TEXT NOT NULL)')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                yield self
            except BaseException:
                self.db.execute('ROLLBACK')
                raise
            else:
                self.db.execute('COMMIT')

    def close(self):
        with _LOCK:
            if self.db is not None:
                self.db.close()
                self.db = None

    def find(self, sha256, size):
        key = digest_key(sha256)
        path = self.objects / key
        if not path.exists():
            return None
        row = self.db.execute('SELECT state FROM objects WHERE sha=?', (key,)).fetchone()
        state = json.loads(row[0]) if row else None
        if path.is_symlink() or state != receipt_stamp(path) or path.stat().st_size != size:
            raise ValueError('geography_object_unverified')
        return path

    def remember(self, path):
        key = digest_key(Path(path).name)
        state = receipt_stamp(path)
        encoded = json.dumps(state, separators=(',', ':'))
        row = self.db.execute('SELECT state FROM objects WHERE sha=?', (key,)).fetchone()
        if row is None or row[0] != encoded:
            self.db.execute('INSERT OR REPLACE INTO objects VALUES (?,?)', (key, encoded))

    def adopt_checked(self, source, sha256, size, checked_stamp):
        source = Path(source)
        existing = self.find(sha256, size)
        if existing is not None:
            return existing
        if source.is_symlink() or receipt_stamp(source) != checked_stamp or checked_stamp[0] != size:
            raise ValueError('geography_import_source_changed')
        destination = self.objects / digest_key(sha256)
        # No cross-filesystem copy fallback: adoption must not duplicate GiB.
        os.link(source, destination)
        self.remember(destination)
        return destination

    def link(self, obj, destination, *, replace_owned_view=False):
        obj, destination = Path(obj), Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if os.path.samefile(obj, destination):
                return
            if not replace_owned_view or destination.is_symlink():
                raise ValueError('geography_view_already_exists')
            temporary = destination.with_name('.' + destination.name + '.' + uuid.uuid4().hex)
            os.link(obj, temporary)
            os.replace(temporary, destination)
        else:
            os.link(obj, destination)
        self.remember(obj)

    def seal_view(self, root, records):
        root = Path(root).resolve()
        identities = {}
        for row in records:
            name = row['path']
            path = root / relative_path(name)
            obj = self.find(row['sha256'], row['bytes'])
            if obj is None or not os.path.samefile(path, obj):
                raise ValueError('geography_view_not_verified')
            identities[name] = {'sha256': digest_key(row['sha256']),
                                'logical': [row['bytes'], row['mtime_ns']],
                                'physical': physical_stamp(path)}
        write_metadata(root / IDENTITIES_FILE,
                       {'format': 'geography_source_identities_v1', 'files': identities})
