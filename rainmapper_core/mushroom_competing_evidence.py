"""Bounded daily sufficient statistics transported from worker to map runtime."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
import math
import re

KIND = 'map_competing_temporal_counts_v1'
LEGACY_MAX_BYTES = 1024 * 1024
# Compact columns are capped separately at 28 MB decoded (no object per cell).
# The measured 5,152-visit fixture needs 4.34 MB encoded numerical columns.
MAX_BYTES = 16 * 1024 * 1024
MAX_CASES = 50000
FIELDS = ('version_id', 'profile_id', 'temporal_contract_id', 'horizon_days', 'estimator_id')


def encode(value):
    # Incremental encoding enforces the byte budget before allocating a full
    # serialized copy; row/cardinality limits apply before building the object.
    result = bytearray()
    limit = MAX_BYTES if 'packed_cells' in value else LEGACY_MAX_BYTES
    for part in json.JSONEncoder(separators=(',', ':'), sort_keys=True, allow_nan=False).iterencode(value):
        raw = part.encode()
        if len(result) + len(raw) > limit:
            raise ValueError('competing_evidence_limit')
        result.extend(raw)
    return bytes(result)


def summarize(units, *, manifest, revision, cutoff, wanted=None, private=False):
    # Case identity, family identity and training prevalence are shared tables.
    # A cell stores only their indices and the original (unrounded) probability.
    species = []; candidates = []; cases = []; baselines = []; cells = []
    si = {}; ci = {}; oi = {}; bi = {}; seen = set()
    reused = computed = missing = 0; estimated = 0
    reasons = Counter()
    cohorts = {}
    cutoff_day = date.fromisoformat(cutoff)
    from rainmapper_core.mushroom_competing_columns import MAX_CELLS
    def intern(table, index, key):
        if key not in index:
            index[key] = len(table); table.append(key)
        return index[key]
    for unit in units:
        reused += int(unit['reused']); computed += int(not unit['reused'] and unit.get('evaluated', True))
        missing += len(unit['missing'])
        reasons.update(str(row[-1])[:300] for row in unit['missing'])
        family = unit['family']
        candidates_by_horizon = {}
        for sid, oid, day, horizon, y, p, baseline, group in unit['rows']:
            if type(horizon) is not int or not 1 <= horizon <= 7:
                raise ValueError('invalid_competing_candidate')
            if horizon not in candidates_by_horizon:
                candidates_by_horizon[horizon] = tuple(horizon if k == 'horizon_days' else family[k] for k in FIELDS)
            candidate = candidates_by_horizon[horizon]
            if wanted is not None and (sid, candidate) not in wanted:
                continue
            if date.fromisoformat(day) >= cutoff_day:
                raise ValueError('future_history_evidence')
            if (type(y) is not int or y not in (0, 1) or
                    any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1
                        for v in (p, baseline))):
                raise ValueError('invalid_history_probability')
            if len(cells) >= (MAX_CELLS if private else MAX_CASES):
                raise ValueError('competing_evidence_cells_limit')
            # The same visit appears under many candidates and horizons.
            identity = (oid, y, group) if type(oid) is str and type(group) is str else None
            cohort = cohorts.get(identity) if identity is not None else None
            if cohort is None:
                cohort = hashlib.sha256(json.dumps([oid, y, group]).encode()).hexdigest()[:24]
                if identity is not None and len(cohorts) < 10000:
                    cohorts[identity] = cohort
            case = (intern(species, si, sid), day, y, cohort)
            case_id = intern(cases, oi, case)
            candidate_id = intern(candidates, ci, candidate)
            if (case_id, candidate_id) in seen:
                raise ValueError('duplicate_history_evidence')
            seen.add((case_id, candidate_id))
            cell = [case_id, candidate_id, p, intern(baselines, bi, baseline)]
            if len(cases) > 10000 or len(candidates) > 4096 or len(baselines) > 4096:
                raise ValueError('competing_evidence_cardinality')
            # With the checked indices and p in [0,1], 64 bytes bounds a JSON
            # cell, including its comma. Even MAX_CELLS fits the private cap.
            estimated += 64 if private else len(json.dumps(cell, separators=(',', ':')).encode()) + 1
            if estimated > (128 * 1024 * 1024 if private else LEGACY_MAX_BYTES):
                raise ValueError('competing_evidence_limit')
            cells.append(cell)
    result = {'kind': KIND, 'batch_id': manifest['batch_id'], 'snapshot_id': manifest['snapshot_id'],
              'quality_sha256': manifest['quality_catalog']['sha256'], 'revision': revision,
              'cutoff': cutoff, 'updated_at': datetime.now(timezone.utc).isoformat(),
              'species': species, 'candidates': candidates, 'cases': cases, 'baselines': baselines,
              'cells': sorted(cells),
              'summary': {'reused_units': reused, 'computed_units': computed, 'missing_rows': missing,
                          'missing_reasons': dict(reasons)}}
    validate(result, private=private)
    if not private:
        encode(result)
    return result


def validate(value, *, private=False):
    try:
        return _validate(value, private=private)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError('invalid_competing_evidence') from exc


def _validate(value, *, private=False):
    if (not isinstance(value, dict) or value.get('kind') != KIND or
            not re.fullmatch('[0-9a-f]{64}', str(value.get('revision', '')))):
        raise ValueError('invalid_competing_evidence')
    if any(not isinstance(value.get(k), str) or not 0 < len(value[k]) <= 160
           for k in ('batch_id', 'snapshot_id', 'quality_sha256')):
        raise ValueError('invalid_competing_model_binding')
    date.fromisoformat(value['cutoff'])
    if 'comparisons' in value:
        from rainmapper_core import mushroom_competing_comparison as comparison
        if (not re.fullmatch('[0-9a-f]{64}', str(value.get('history_revision', ''))) or
                not isinstance(value['comparisons'], list) or len(value['comparisons']) > 8):
            raise ValueError('invalid_competing_comparisons')
        keys = set()
        for result in value['comparisons']:
            comparison.validate(result)
            if result['k'] in keys:
                raise ValueError('duplicate_competing_comparison')
            keys.add(result['k'])
    from rainmapper_core.mushroom_competing_columns import Cells, MAX_CELLS
    species, candidates, cases, baselines = (value[k] for k in ('species', 'candidates', 'cases', 'baselines'))
    cells = cell_rows(value)
    if (not all(isinstance(x, (list, tuple)) for x in (species, candidates, cases, baselines)) or
            not isinstance(cells, (list, tuple, Cells)) or
            len(species) > 128 or len(candidates) > 4096 or len(cases) > 10000 or
            len(baselines) > 4096 or len(cells) > (MAX_CELLS if private or isinstance(cells, Cells) else MAX_CASES)):
        raise ValueError('competing_evidence_cardinality')
    if any(not isinstance(s, str) or not 0 < len(s) <= 160 for s in species):
        raise ValueError('invalid_competing_species')
    for c in candidates:
        if (not isinstance(c, (list, tuple)) or len(c) != 5 or type(c[3]) is not int or not 1 <= c[3] <= 7 or
                any(not isinstance(c[i], str) or not 0 < len(c[i]) <= 160 for i in (0, 1, 2, 4))):
            raise ValueError('invalid_competing_candidate')
    for case in cases:
        if not isinstance(case, (list, tuple)) or len(case) != 4:
            raise ValueError('invalid_competing_case')
        sid, day, y, population = case
        if (type(sid) is not int or not 0 <= sid < len(species) or type(y) is not int or y not in (0,1) or
                not isinstance(population, str) or not re.fullmatch('[0-9a-f]{24}', population)):
            raise ValueError('invalid_competing_case')
        date.fromisoformat(day)
        if day >= value['cutoff']:
            raise ValueError('future_competing_case')
    if len(set(map(tuple, cases))) != len(cases) or len(set(map(tuple, candidates))) != len(candidates):
        raise ValueError('duplicate_competing_identity')
    probability = lambda v: type(v) in (float,int) and math.isfinite(v) and 0 <= v <= 1
    if any(not probability(p) for p in baselines):
        raise ValueError('invalid_competing_baseline')
    if isinstance(cells, Cells):
        cells.validate(len(cases), len(candidates), len(baselines))
        return value
    seen = set()
    for cell in cells:
        if not isinstance(cell, (list, tuple)) or len(cell) != 4:
            raise ValueError('invalid_competing_cell')
        oid, cid, p, base = cell
        if (type(oid) is not int or not 0 <= oid < len(cases) or
                type(cid) is not int or not 0 <= cid < len(candidates) or not probability(p) or
                type(base) is not int or not 0 <= base < len(baselines) or (oid,cid) in seen):
            raise ValueError('invalid_competing_cell')
        seen.add((oid,cid))
    return value


def cell_rows(value):
    from rainmapper_core import mushroom_competing_columns as columns
    if 'packed_cells' in value:
        if 'cells' in value:
            raise ValueError('ambiguous_competing_cells')
        return columns.unpack(value['packed_cells'])
    return value['cells']


def to_wire(value):
    from rainmapper_core import mushroom_competing_columns as columns
    if 'packed_cells' in value:
        return value
    rows = value['cells']
    # Timelines across up to eight K values share one packed candidate table;
    # retain the existing total 16 MiB wire budget, never duplicate its cells.
    dated = any('history' in result for result in value.get('comparisons', []))
    if isinstance(rows, columns.Cells) or len(rows) > MAX_CASES or dated:
        return {**{k:v for k,v in value.items() if k != 'cells'}, 'packed_cells': columns.pack(rows)}
    return value


def expanded_rows(value, *, species_id=None):
    # Sufficient statistics depend on the observation date, never on K. No
    # historical inference takes place here; probabilities came from the worker.
    from rainmapper_core.mushroom_competing_columns import Cells
    cells = cell_rows(value)
    if isinstance(cells, Cells):
        # One candidate's daily buckets at a time. Stable column indexing keeps
        # each day's original float-addition order; nothing is rounded.
        groups = (cells.candidate_rows(cid) for cid in range(len(value['candidates'])))
    else:
        groups = (cells,)
    for group in groups:
        buckets = {}
        for oid, cid, p, base in group:
            sid, day, y, population = value['cases'][oid]
            if species_id is not None and value['species'][sid] != species_id:
                continue
            key = sid, cid, day
            if key not in buckets:
                buckets[key] = [0, 0, 0, 0, 0, 0, p, p, []]
            stats = buckets[key]
            stats[0] += 1; stats[1] += y
            stats[2] += int(y == 1 and p >= .6)
            stats[3] += int(y == 0 and p >= .6)
            stats[4] += (y-p)**2; stats[5] += (y-value['baselines'][base])**2
            stats[6] = min(stats[6], p); stats[7] = max(stats[7], p)
            stats[8].append(population)
        for (sid, cid, day), stats in buckets.items():
            stats[8] = hashlib.sha256(json.dumps(sorted(stats[8])).encode()).hexdigest()[:24]
            yield value['species'][sid], value['candidates'][cid], day, stats
