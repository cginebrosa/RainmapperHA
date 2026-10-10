"""Bounded, content-addressed reuse of historical runtime inputs on the worker.

Shares the existing 256 MiB unit database. Only this disposable input table is
evicted; fitted-unit results, panels and source observations are never removed.
"""
from collections import OrderedDict
import hashlib
import json
import zlib
import sys

from rainmapper_core.mushroom_competing_history import canonical

MAX_BYTES = 32 * 1024 * 1024
MAX_RAW_BYTES = 2 * 1024 * 1024
MAX_MEMORY_BYTES = 2 * 1024 * 1024
MAX_FINGERPRINTS = 2048
FINGERPRINT_RESERVE = 1024 * 1024


def _immutable(*args, **kwargs):
    raise TypeError('immutable_history_input')


class _FrozenDict(dict):
    __slots__ = ()
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable

    def __deepcopy__(self, memo):
        return self


class _FrozenList(list):
    __slots__ = ()
    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = reverse = sort = __iadd__ = __imul__ = _immutable

    def __deepcopy__(self, memo):
        return self


def _freeze(value, limit):
    """Bound the decoded object, including containers, strings and scalars."""
    size = 0
    def visit(item):
        nonlocal size
        size += sys.getsizeof(item)
        if size > limit:
            raise OverflowError('shared_history_input_budget')
        if isinstance(item, dict):
            result = _FrozenDict((visit(k), visit(v)) for k,v in item.items())
        elif isinstance(item, list):
            result = _FrozenList(visit(v) for v in item)
        else:
            return item
        size += sys.getsizeof(result) - sys.getsizeof(item)
        if size > limit:
            raise OverflowError('shared_history_input_budget')
        return result
    frozen = visit(value)
    return frozen, size


class Inputs:
    def __init__(self, db, *, limit=MAX_BYTES):
        self.fingerprint_limit = min(FINGERPRINT_RESERVE, limit // 32)
        self.db, self.limit = db, max(0, limit - self.fingerprint_limit)
        self.db.execute('CREATE TABLE IF NOT EXISTS runtime_inputs '
                        '(key TEXT PRIMARY KEY, payload BLOB NOT NULL, sha TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS runtime_fingerprints '
                        '(key TEXT PRIMARY KEY, value TEXT NOT NULL, sha TEXT NOT NULL)')
        self.used = self.db.execute('SELECT coalesce(sum(length(payload)),0) FROM runtime_inputs').fetchone()[0]
        self.memo = OrderedDict(); self.memory_bytes = 0; self.pending = 0
        self.memory_limit = MAX_MEMORY_BYTES
        self.shared = OrderedDict(); self.shared_bytes = 0
        self.hits = 0; self.writes = 0

    def read_fingerprint(self, key):
        row = self.db.execute('SELECT value,sha FROM runtime_fingerprints WHERE key=?', (key,)).fetchone()
        if row is None:
            return None
        value, sha = row
        if (not isinstance(value, str) or len(value) != 64 or
                hashlib.sha256(value.encode()).hexdigest() != sha):
            raise ValueError('comparison_fingerprint_integrity')
        return value

    def write_fingerprint(self, key, value):
        if (len(key) != 64 or len(value) != 64 or
                any(c not in '0123456789abcdef' for c in key + value)):
            raise ValueError('comparison_fingerprint_invalid')
        count = self.db.execute('SELECT count(*) FROM runtime_fingerprints').fetchone()[0]
        if count >= MAX_FINGERPRINTS or (count + 1) * 512 > self.fingerprint_limit:
            return
        # Fixed small records share the existing database budget. Fingerprints
        # survive eviction of bulky reconstructible weather/feature rows.
        from rainmapper_core.mushroom_competing_history import MAX_CACHE_BYTES
        size = self.db.execute('PRAGMA page_size').fetchone()[0]
        pages = self.db.execute('PRAGMA page_count').fetchone()[0]
        free = self.db.execute('PRAGMA freelist_count').fetchone()[0]
        if (pages - free) * size + 256 > MAX_CACHE_BYTES - MAX_BYTES:
            return
        self.db.execute('INSERT OR REPLACE INTO runtime_fingerprints VALUES (?,?,?)',
                        (key, value, hashlib.sha256(value.encode()).hexdigest()))
        self.pending += 1

    def _remember(self, key, raw):
        old = self.memo.pop(key, None)
        self.memory_bytes -= len(old) if old is not None else 0
        self.memo[key] = raw; self.memory_bytes += len(raw)
        while self.memory_bytes > self.memory_limit and self.memo:
            self.memory_bytes -= len(self.memo.popitem(last=False)[1])

    def read(self, key):
        packed = self.memo.get(key)
        if packed is None:
            row = self.db.execute('SELECT payload,sha FROM runtime_inputs WHERE key=?', (key,)).fetchone()
            if row is None:
                return None
            packed, sha = row
            if len(packed) > MAX_RAW_BYTES or hashlib.sha256(packed).hexdigest() != sha:
                raise ValueError('comparison_inputs_integrity')
            self._remember(key, packed)
        self.hits += 1
        decoder = zlib.decompressobj()
        raw = decoder.decompress(packed, MAX_RAW_BYTES + 1)
        if len(raw) > MAX_RAW_BYTES or not decoder.eof:
            raise ValueError('comparison_inputs_size_limit')
        return json.loads(raw)

    def read_shared(self, key):
        """Read-only consumers share decoded inputs within the same 2 MiB cap."""
        self.memory_limit = MAX_MEMORY_BYTES // 2
        while self.memory_bytes > self.memory_limit and self.memo:
            self.memory_bytes -= len(self.memo.popitem(last=False)[1])
        if key in self.shared:
            self.shared.move_to_end(key)
            self.hits += 1
            return self.shared[key][0]
        value = self.read(key)
        if value is None:
            return None
        limit = MAX_MEMORY_BYTES - self.memory_limit
        try:
            frozen, size = _freeze(value, limit)
        except OverflowError:
            return value
        while self.shared and self.shared_bytes + size > limit:
            self.shared_bytes -= self.shared.popitem(last=False)[1][1]
        self.shared[key] = frozen, size
        self.shared_bytes += size
        return frozen

    def write(self, key, value):
        raw = canonical(value)
        if len(raw) > MAX_RAW_BYTES:
            raise ValueError('comparison_inputs_size_limit')
        packed = zlib.compress(raw, 1)
        if len(packed) > self.limit:
            return  # Oversized cache entry: compute normally, never evict results.
        if self.db.execute('SELECT 1 FROM runtime_inputs WHERE key=?', (key,)).fetchone():
            return
        # FIFO eviction is restricted to reconstructible runtime inputs.
        while self.used + len(packed) > self.limit:
            row = self.db.execute('SELECT rowid,length(payload) FROM runtime_inputs ORDER BY rowid LIMIT 1').fetchone()
            if row is None:
                break
            self.db.execute('DELETE FROM runtime_inputs WHERE rowid=?', (row[0],)); self.used -= row[1]
        # Reserve space for immutable results within the existing database cap.
        page_size = self.db.execute('PRAGMA page_size').fetchone()[0]
        allocated = self.db.execute('PRAGMA page_count').fetchone()[0]
        free = self.db.execute('PRAGMA freelist_count').fetchone()[0]
        from rainmapper_core.mushroom_competing_history import MAX_CACHE_BYTES
        if (allocated - free) * page_size + len(packed) > MAX_CACHE_BYTES - MAX_BYTES:
            return
        self.db.execute('INSERT INTO runtime_inputs VALUES (?,?,?)',
                        (key, packed, hashlib.sha256(packed).hexdigest()))
        self.used += len(packed); self.writes += 1; self.pending += 1
        self._remember(key, packed)
        if self.pending >= 128:
            self.flush()

    def flush(self):
        self.db.commit(); self.pending = 0


class LastView(dict):
    """Workspace views retain one window, not copies of all station histories."""
    def __setitem__(self, key, value):
        self.clear()
        super().__setitem__(key, value)


class TransientInputs:
 """Bounded immutable derived rows; durable models/panels remain on disk."""
 def __init__(self,limit=16*1024*1024):self.limit=limit;self.used=0;self.values=OrderedDict()
 def get(self,key):
  row=self.values.get(key)
  if row is not None:self.values.move_to_end(key);return row[0]
 def put(self,key,value):
  try:frozen,size=_freeze(value,self.limit)
  except OverflowError:return
  size+=len(key)*4+256
  if size>self.limit:return
  old=self.values.pop(key,None)
  if old:self.used-=old[1]
  while self.values and (self.used+size>self.limit or len(self.values)>=4096):self.used-=self.values.popitem(last=False)[1][1]
  self.values[key]=frozen,size;self.used+=size
