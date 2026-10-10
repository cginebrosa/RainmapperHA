"""Lossless, bounded numerical evidence; no Python object per stored cell.

Case/candidate/baseline indices are uint16, probabilities remain float64.
Columns are compressed separately from their JSON identity tables. Reading a
species or candidate never expands the entire evidence into dictionaries.
"""
from array import array
import base64
import hashlib
import math
import sys
import zlib

FORMAT = 'competing_columns_le_v1'
MAX_CELLS = 2_000_000
MAX_ENCODED_BYTES = 14 * 1024 * 1024
_cached = None


def pack(rows):
    if isinstance(rows, Cells) and rows.allowed is None:
        return rows.packet
    count = len(rows)
    if not 0 <= count <= MAX_CELLS:
        raise ValueError('competing_columns_cardinality')
    columns = [array('H'), array('H'), array('d'), array('H')]
    previous = (-1, -1)
    for oid, cid, p, bid in rows:
        if (any(type(i) is not int or not 0 <= i < 65536 for i in (oid, cid, bid)) or
                type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 or
                (oid, cid) <= previous):
            raise ValueError('competing_columns_value')
        for column, value in zip(columns, (oid, cid, p, bid)):
            column.append(value)
        previous = oid, cid
    if len(columns[0]) != count:
        raise ValueError('competing_columns_count')
    encoder, sha, chunks, size = zlib.compressobj(1), hashlib.sha256(), [], 0
    for column in columns:
        if sys.byteorder != 'little':
            column.byteswap()
        raw = memoryview(column).cast('B')
        sha.update(raw)
        part = encoder.compress(raw)
        chunks.append(part); size += len(part)
        if 4 * ((size + 2) // 3) > MAX_ENCODED_BYTES:
            raise ValueError('competing_columns_size')
    part = encoder.flush(); chunks.append(part); size += len(part)
    if 4 * ((size + 2) // 3) > MAX_ENCODED_BYTES:
        raise ValueError('competing_columns_size')
    return {'format': FORMAT, 'count': count, 'sha256': sha.hexdigest(),
            'data': base64.b64encode(b''.join(chunks)).decode('ascii')}


def unpack(packet):
    global _cached
    if not isinstance(packet, dict) or packet.get('format') != FORMAT:
        raise ValueError('competing_columns_format')
    count, data, sha = packet.get('count'), packet.get('data'), packet.get('sha256')
    if (type(count) is not int or not 0 <= count <= MAX_CELLS or
            not isinstance(data, str) or len(data) > MAX_ENCODED_BYTES or
            not isinstance(sha, str) or len(sha) != 64):
        raise ValueError('competing_columns_cardinality')
    try:
        encoded = data.encode('ascii')
        identity = count, sha, hashlib.sha256(encoded).digest()
        if _cached is not None and _cached[0] == identity:
            return _cached[1]
        packed = base64.b64decode(encoded, validate=True)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(packed, count * 14 + 1)
        if (len(raw) != count * 14 or not decoder.eof or decoder.unused_data or
                hashlib.sha256(raw).hexdigest() != sha):
            raise ValueError('competing_columns_integrity')
    except (UnicodeError, zlib.error) as exc:
        raise ValueError('competing_columns_encoding') from exc
    value = Cells(packet, raw)
    # One typed evidence object, at most 28 MB of data + 8 MB of index. No
    # decoded JSON cell list and no unbounded cache across model generations.
    _cached = identity, value
    return value


class Cells:
    def __init__(self, packet, raw):
        import numpy as np
        self.packet, self.raw, self.allowed = packet, raw, None
        n = packet['count']
        self.oid = np.frombuffer(raw, dtype='<u2', count=n)
        self.cid = np.frombuffer(raw, dtype='<u2', count=n, offset=n*2)
        self.p = np.frombuffer(raw, dtype='<f8', count=n, offset=n*4)
        self.bid = np.frombuffer(raw, dtype='<u2', count=n, offset=n*12)
        if (not np.all(np.isfinite(self.p)) or np.any(self.p < 0) or np.any(self.p > 1) or
                np.any((self.oid[1:] < self.oid[:-1]) |
                       ((self.oid[1:] == self.oid[:-1]) & (self.cid[1:] <= self.cid[:-1])))):
            raise ValueError('competing_columns_value')
        self._order = self._offsets = None

    def validate(self, cases, candidates, baselines):
        if len(self) and (self.oid.max() >= cases or self.cid.max() >= candidates or self.bid.max() >= baselines):
            raise ValueError('invalid_competing_cell')

    def __len__(self):
        return len(self.oid) if self.allowed is None else self._count

    def __iter__(self):
        for i in range(len(self.oid)):
            oid = int(self.oid[i])
            if self.allowed is None or self.allowed[oid]:
                yield oid, int(self.cid[i]), float(self.p[i]), int(self.bid[i])

    def has_case(self, oid):
        import numpy as np
        index = int(np.searchsorted(self.oid, oid))
        return index < len(self.oid) and self.oid[index] == oid

    def subset(self, cases):
        import numpy as np
        self._index()
        result = object.__new__(Cells)
        result.__dict__.update(self.__dict__)
        allowed = np.zeros(int(self.oid[-1]) + 1 if len(self.oid) else 0, dtype=np.bool_)
        if any(type(i) is not int or not 0 <= i < len(allowed) for i in cases):
            raise ValueError('competing_columns_case_subset')
        allowed[list(cases)] = True
        if self.allowed is not None:
            allowed &= self.allowed
        result.allowed = allowed
        result._count = int(np.count_nonzero(allowed[self.oid]))
        return result

    def candidate_rows(self, cid):
        self._index()
        for i in self._order[self._offsets[cid]:self._offsets[cid+1]]:
            oid = int(self.oid[i])
            if self.allowed is None or self.allowed[oid]:
                yield oid, cid, float(self.p[i]), int(self.bid[i])

    def _index(self):
        import numpy as np
        if self._offsets is None:
            order = np.argsort(self.cid, kind='stable').astype(np.uint32)
            offsets = np.r_[0, np.cumsum(np.bincount(self.cid, minlength=4096))]
            self._order = order
            self._offsets = offsets
