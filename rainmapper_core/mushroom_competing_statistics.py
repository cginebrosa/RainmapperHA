"""Reusable per-day statistics over immutable historical numerical evidence."""
from datetime import date
import hashlib
import json
import numpy as np
from rainmapper_core.mushroom_map_competing import PointCache

STRIDE = 4_000_000


class DailyStatistics:
    def __init__(self, evidence, cells, *, compact_populations=False):
        self.evidence, self.cells = evidence, cells
        self.candidates = {tuple(c):i for i,c in enumerate(evidence['candidates'])}
        self.species = {s:i for i,s in enumerate(evidence['species'])}
        self.codes = np.asarray([sid*STRIDE + date.fromisoformat(day).toordinal()
                                 for sid,day,_,_ in evidence['cases']], dtype=np.int32)
        self.compact_populations = compact_populations
        self.years_by_code = {int(code):date.fromordinal(int(code)%STRIDE).year for code in set(self.codes)}
        self.blocks = {}
        self.corrections = PointCache(max_bytes=1024*1024,max_entries=128)
        cells._index()

    def _stats(self, positions):
        stats = [0, 0, 0, 0, 0, 0, 1., 0., []]
        for at in positions:
            oid, p, bid = int(self.cells.oid[at]), float(self.cells.p[at]), int(self.cells.bid[at])
            _, _, y, population = self.evidence['cases'][oid]
            stats[0] += 1; stats[1] += y
            stats[2] += int(y == 1 and p >= .6); stats[3] += int(y == 0 and p >= .6)
            stats[4] += (y-p)**2; stats[5] += (y-self.evidence['baselines'][bid])**2
            stats[6] = min(stats[6], p); stats[7] = max(stats[7], p)
            stats[8].append(population)
        stats[8] = hashlib.sha256(json.dumps(sorted(stats[8])).encode()).hexdigest()[:24]
        return tuple(stats)

    def _block(self, cid):
        if cid not in self.blocks:
            at = self.cells._order[self.cells._offsets[cid]:self.cells._offsets[cid+1]]
            codes = self.codes[self.cells.oid[at]]
            order = np.argsort(codes, kind='stable')
            at, codes = at[order], codes[order]
            starts = np.r_[0, np.flatnonzero(codes[1:] != codes[:-1])+1] if len(codes) else np.array([],dtype=int)
            ends = np.r_[starts[1:], len(codes)] if len(codes) else starts
            numbers = np.empty((len(starts),8),dtype=np.float64)
            populations = np.empty(len(starts),dtype='S24')
            for i,(a,b) in enumerate(zip(starts,ends)):
                stats = self._stats(at[a:b]); numbers[i] = stats[:8]; populations[i] = stats[8].encode()
            first = self.cells.oid[at[starts]]
            self.blocks[cid] = (codes[starts], at, starts.astype(np.uint32), ends.astype(np.uint32),
                                numbers, populations, first)
        return self.blocks[cid]

    def view(self, sid, bound, excluded):
        return StatisticsView(self, sid, bound, excluded)


class StatisticsView:
    def __init__(self, owner, sid, bound, excluded):
        self.owner, self.sid, self.bound = owner, sid, bound
        self.excluded = frozenset(excluded)
        self.excluded_codes = frozenset(int(owner.codes[i]) for i in excluded)

    def _windows(self, candidates, start, end):
        owner = self.owner
        sid = owner.species[self.sid]
        lower = sid*STRIDE + start.toordinal()
        upper = sid*STRIDE + min(end, self.bound).toordinal()
        for candidate in sorted(candidates, key=lambda key: owner.candidates.get(key,-1)):
            cid = owner.candidates.get(candidate)
            if cid is None: continue
            codes, at, starts, ends, numbers, populations, first = owner._block(cid)
            lo, hi = int(np.searchsorted(codes, lower)), int(np.searchsorted(codes, upper))
            if lo == hi: continue
            indices = np.arange(lo,hi)
            corrections = {}
            changed_first = first[lo:hi].copy()
            if self.excluded:
                for offset,i in enumerate(indices):
                    if int(codes[i]) not in self.excluded_codes: continue
                    key = cid, int(codes[i]), tuple(sorted(oid for oid in self.excluded if owner.codes[oid] == codes[i]))
                    saved = owner.corrections.get(key)
                    if saved is None:
                        positions = at[starts[i]:ends[i]]
                        positions = positions[[int(owner.cells.oid[p]) not in self.excluded for p in positions]]
                        saved = ((owner._stats(positions),int(owner.cells.oid[positions[0]]))
                                 if len(positions) else (None,65535))
                        owner.corrections.put(key,saved)
                    corrections[int(i)] = saved[0]; changed_first[offset] = saved[1]
            yield candidate, cid, indices, corrections, changed_first

    def rows_for(self, candidates, start, end):
        owner = self.owner
        sid = owner.species[self.sid]
        for candidate, cid, indices, corrections, changed_first in self._windows(candidates,start,end):
            codes, _, _, _, numbers, populations, _ = owner._block(cid)
            # Preserve the first-case order used by expanded_rows; never change
            # floating summation or native tie behavior by sorting dates.
            for i in indices[np.argsort(changed_first,kind='stable')]:
                if int(i) in corrections:
                    stats = corrections[int(i)]
                    if stats is None:continue
                else:
                    row = numbers[i]
                    stats = (*map(int,row[:4]),*map(float,row[4:]),populations[i].decode())
                day = date.fromordinal(int(codes[i])-sid*STRIDE).isoformat()
                yield self.sid, owner.evidence['candidates'][cid], day, stats

    def aggregates_for(self, candidates, start, end):
        """Identical ordered additions on typed arrays, without per-day objects.

        accumulate is deliberate: sum/reduce may regroup floating additions.
        Native ordering and exact population identities remain unchanged.
        """
        owner = self.owner
        sid = owner.species[self.sid]
        result, years = {}, set()
        for candidate, cid, indices, corrections, first in self._windows(candidates,start,end):
            codes, _, _, _, numbers, populations, _ = owner._block(cid)
            values = numbers[indices]
            hashes = populations[indices]
            keep = np.ones(len(indices),dtype=bool)
            for offset,i in enumerate(indices):
                if int(i) not in corrections: continue
                stats = corrections[int(i)]
                if stats is None:
                    keep[offset] = False
                else:
                    values[offset] = stats[:8]; hashes[offset] = stats[8].encode()
            if not np.any(keep): continue
            indices, values, hashes, first = indices[keep], values[keep], hashes[keep], first[keep]
            ordered = values[np.argsort(first,kind='stable')]
            totals = np.add.accumulate(ordered[:,:6],axis=0)[-1]
            years.update(owner.years_by_code[int(code)] for code in codes[indices])
            if owner.compact_populations:
                # Big-endian ordinals retain the lexicographic order of ISO
                # dates, followed by the same fixed-width population hash.
                records = np.empty(len(indices), dtype=[('day','>u4'),('identity','S24')])
                records['day'] = codes[indices]-sid*STRIDE
                records['identity'] = hashes
                population = records.tobytes()
            else:
                days = [date.fromordinal(int(codes[i])-sid*STRIDE) for i in indices]
                population = tuple((d.isoformat(),h.decode()) for d,h in zip(days,hashes))
            result[candidate] = (*map(float,totals),float(values[:,6].min()),
                                 float(values[:,7].max()),population)
        return result, years

    def __iter__(self):
        return self.rows_for(self.owner.candidates, date.min, self.bound)
