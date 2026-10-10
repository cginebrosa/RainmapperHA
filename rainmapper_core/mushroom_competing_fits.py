"""Private reuse of completed historical fits, independent of evaluation rows.

Only models fitted by this worker are serialized here. Installed weights and
incoming artefacts are never loaded through this cache. It shares the existing
unit database budget; a full cache simply declines new memo entries.
"""
from __future__ import annotations

import hashlib
import io
from importlib.metadata import version
import pickle
import sys
import zlib

from rainmapper_core import mushroom_competing_history as history

MAX_BYTES = 64 * 1024 * 1024
MAX_MODEL_BYTES = 32 * 1024 * 1024
MAX_PACKET_BYTES = 8 * 1024 * 1024


class _BoundedBuffer(io.BytesIO):
    def write(self, data):
        # Protocol 5 passes large NumPy buffers directly, without __len__.
        # Count raw bytes (also for Fortran arrays), not logical elements.
        view = data.raw() if isinstance(data,pickle.PickleBuffer) else memoryview(data)
        if self.tell() + view.nbytes > MAX_MODEL_BYTES:
            raise OverflowError('history_fit_model_budget')
        return super().write(view)


class Fits:
    def __init__(self, db, producer, *, compatible_producers=()):
        self.db = db
        environment = [sys.version_info[:2],
            [(name, version(name)) for name in ('numpy', 'scipy', 'scikit-learn')]]
        self.producer = history.digest([producer, *environment])
        # Migrated units keep their original fit recipes/keys. Read only
        # explicitly reviewed producers in the same Python/library environment.
        self.accepted_producers = {self.producer, *(history.digest([old, *environment])
                                                  for old in compatible_producers)}
        self.db.execute('CREATE TABLE IF NOT EXISTS historical_fits '
                        '(key TEXT PRIMARY KEY, payload BLOB NOT NULL, sha TEXT NOT NULL)')
        self.used = self.db.execute('SELECT coalesce(sum(length(payload)),0) FROM historical_fits').fetchone()[0]
        self.stats = dict(fits_built=0, fits_reused=0, fits_not_cached=0)
        self.sealed = None
        self.row_fingerprints = None
        self.benchmark = None

    def seal_unit_keys(self, references, benchmark, train, test, *, implementation_ids, row_fingerprints=None):
        """Share serialization of consumed values with validation fingerprints."""
        keys = {}
        result = history.unit_keys(references,benchmark,train,test,
            implementation_ids=implementation_ids,
            training_implementation_id='historical_fit_v1:' + self.producer, training_keys=keys,
            row_fingerprints=row_fingerprints)
        # Keep only this immutable matrix alive; never match recycled object ids.
        self.sealed = benchmark, train, keys
        self.benchmark, self.row_fingerprints = benchmark, row_fingerprints
        return result

    def key(self, reference, benchmark, train):
        # Labels/features and temporal episode identities on the training side
        # enter the key. A new test observation cannot cause the same fit again.
        if self.sealed is not None and self.sealed[0] is benchmark and self.sealed[1] is train:
            key = self.sealed[2].get(tuple(reference.as_dict()[k] for k in history.FAMILY_FIELDS))
            if key is not None: return key
        return history.unit_key(reference, benchmark, train, [],
                                implementation_id='historical_fit_v1:' + self.producer,
                                row_fingerprints=self.row_fingerprints if self.benchmark is benchmark else None)

    def read(self, key):
        row = self.db.execute('SELECT payload,sha FROM historical_fits WHERE key=?', (key,)).fetchone()
        if row is None:
            return None
        packed, sha = row
        if len(packed) > MAX_PACKET_BYTES or hashlib.sha256(packed).hexdigest() != sha:
            raise ValueError('history_fit_cache_integrity')
        if packed.startswith(b'RMF2'):
            size = int.from_bytes(packed[4:8],'big')
            if len(packed) <= 8 or not 0 < size <= MAX_MODEL_BYTES:
                raise ValueError('history_fit_cache_size')
            import pyarrow as pa
            try:
                raw = pa.decompress(packed[8:],decompressed_size=size,codec='zstd').to_pybytes()
            except (OSError, ValueError) as exc:
                raise ValueError('history_fit_cache_integrity') from exc
            if len(raw) != size:
                raise ValueError('history_fit_cache_size')
        else:
            # Existing locally produced protocol-5 entries remain readable.
            decoder = zlib.decompressobj()
            raw = decoder.decompress(packed, MAX_MODEL_BYTES + 1)
            if len(raw) > MAX_MODEL_BYTES or not decoder.eof or decoder.unused_data:
                raise ValueError('history_fit_cache_size')
        # This table is created locally from fit_artifact, never from a
        # coordinator payload. Integrity/size are checked before deserialization.
        value = pickle.loads(raw)
        self.last_model_bytes = len(raw)
        if (not isinstance(value, dict) or value.get('key') != key or
                value.get('producer') not in self.accepted_producers or
                not isinstance(value.get('bundle'), dict) or
                value['bundle'].get('kind') != 'mushroom_ml_runtime_model'):
            raise ValueError('history_fit_cache_contract')
        self.stats['fits_reused'] += 1
        return value

    def contains(self, key):
        return self.db.execute('SELECT 1 FROM historical_fits WHERE key=?', (key,)).fetchone() is not None

    def write(self, key, bundle, diagnostics):
        self.stats['fits_built'] += 1
        if self.db.execute('SELECT 1 FROM historical_fits WHERE key=?', (key,)).fetchone():
            return
        packet = None
        if self.used < MAX_BYTES:
            try:
                with _BoundedBuffer() as stream:
                    pickle.dump({'key': key, 'producer': self.producer,
                                 'bundle': bundle, 'diagnostics': diagnostics}, stream, protocol=5)
                    import pyarrow as pa
                    raw = stream.getbuffer()
                    try:
                        packet = b'RMF2' + len(raw).to_bytes(4,'big') + pa.compress(raw,codec='zstd').to_pybytes()
                    finally:
                        raw.release()
            except (OverflowError, pickle.PicklingError, TypeError, AttributeError):
                pass
        page_size = self.db.execute('PRAGMA page_size').fetchone()[0]
        pages = self.db.execute('PRAGMA page_count').fetchone()[0]
        free = self.db.execute('PRAGMA freelist_count').fetchone()[0]
        if (packet is None or len(packet) > MAX_PACKET_BYTES or
                self.used + len(packet) > MAX_BYTES or
                (pages - free) * page_size + len(packet) > history.MAX_CACHE_BYTES - 32 * 1024 * 1024):
            self.stats['fits_not_cached'] += 1
            return
        with self.db:
            self.db.execute('INSERT INTO historical_fits VALUES (?,?,?)',
                            (key, packet, hashlib.sha256(packet).hexdigest()))
        self.used += len(packet)
