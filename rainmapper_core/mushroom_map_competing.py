"""K ranking of installed families using worker-prepared temporal validation."""
from __future__ import annotations

import copy
from datetime import date
import json
import math
import os
from pathlib import Path
import calendar
from collections import OrderedDict
import sys

from rainmapper_core import mushroom_competing_evidence as evidence_contract

FILENAME = 'prediction-competing.json'
KIND = evidence_contract.KIND
CAPABILITY = 'map_competing_selection_v2'
MAX_BYTES = evidence_contract.MAX_BYTES
FIELDS = ('version_id', 'profile_id', 'temporal_contract_id', 'horizon_days', 'estimator_id')


class PointCache:
    """Bound repeated A/B/C/D inference within one point by bytes and entries."""
    def __init__(self, max_bytes=2 * 1024 * 1024, max_entries=28, shared_values=()):
        self.values = OrderedDict()
        self.shared_values = tuple(shared_values)
        self.max_bytes, self.max_entries, self.size = max_bytes, max_entries, 0

    def get(self, key):
        row = self.values.get(key)
        if row is not None:
            self.values.move_to_end(key)
        return row[0] if row else None

    def discard(self, key):
        row = self.values.pop(key, None)
        if row is not None:
            self.size -= row[1]

    def clear(self):
        self.values.clear()
        self.size = 0

    def put(self, key, value):
        pending, seen, size = [key, value], {id(v) for v in self.shared_values}, 0
        while pending:
            item = pending.pop()
            if id(item) in seen:
                continue
            seen.add(id(item)); size += sys.getsizeof(item)
            if size > self.max_bytes:
                return
            if isinstance(item, dict):
                pending.extend(item.keys()); pending.extend(item.values())
            elif isinstance(item, (tuple, list)):
                pending.extend(item)
        if key in self.values:
            self.size -= self.values.pop(key)[1]
        while self.values and (self.size + size > self.max_bytes or len(self.values) >= self.max_entries):
            self.size -= self.values.popitem(last=False)[1][1]
        self.values[key] = (value, size); self.size += size


def valid_k(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1000


def defaults():
    try:
        k = float(os.environ.get('RAINMAPPER_PREDICTION_K_VALUE', '4'))
    except ValueError:
        k = 4
    return {'competing_selection': os.environ.get('RAINMAPPER_PREDICTION_COMPETING_SELECTION', 'false').lower() == 'true',
            'k_value': k if valid_k(k) else 4}


def identity(candidate):
    return tuple(candidate.get(key) for key in FIELDS)


def validate_comparison(value, horizon):
    if not isinstance(value, dict) or value.get('evidence') not in ('temporal_history', 'unavailable'):
        return False
    labels = value.get('labels'); criteria = value.get('criteria')
    if (not isinstance(labels, list) or len(labels) > 28 or
            any(not isinstance(label, str) or not 0 < len(label) <= 96 for label in labels) or
            not isinstance(criteria, list) or len(criteria) != 4):
        return False
    for method, row in zip('ABCD', criteria):
        if not isinstance(row, dict) or row.get('method') != method:
            return False
        years = row.get('years'); days = row.get('days')
        if (not isinstance(years, list) or len(years) > 101 or
                any(type(y) is not int or not 2000 <= y <= 2100 for y in years) or
                years != sorted(set(years)) or not isinstance(days, list) or len(days) != horizon):
            return False
        for day in days:
            if day == [None, None, None]:
                continue
            if (not isinstance(day, list) or len(day) != 4 or type(day[0]) not in (float, int) or
                    not math.isfinite(day[0]) or not 0 <= day[0] <= 1 or type(day[1]) is not int or
                    not 0 <= day[1] < len(labels) or type(day[3]) is not bool):
                return False
            if type(day[2]) not in (float, int) or not math.isfinite(day[2]):
                return False
    if value.get('comparison') is not None:
        from rainmapper_core import mushroom_competing_comparison as comparison
        try:
            comparison.validate(value['comparison'])
        except (ValueError, KeyError, TypeError, IndexError):
            return False
    return True


def comparison_for(evidence, species_id, issue_date, k):
    if not evidence:
        return None
    issue = issue_date.isoformat() if isinstance(issue_date, date) else issue_date
    from rainmapper_core.mushroom_competing_comparison import at_date
    for value in evidence.get('comparisons', []):
        if value['k'] == k:
            return at_date(value, species_id, issue)
    return None


def comparison_unavailable_reason(evidence, species_id, issue_date, k):
    issue = issue_date.isoformat() if isinstance(issue_date, date) else issue_date
    for value in (evidence or {}).get('comparisons', []):
        if value['k'] == k and species_id in value['species'] and issue < value['cutoff'] and 'history' not in value:
            return 'historical_not_prepared'
    return 'pending'


def encode(value):
    return evidence_contract.encode(value)


def read(path, manifest):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return None
        value = json.loads(raw)
        if (value.get('kind') != KIND or value.get('batch_id') != manifest['batch_id'] or
                value.get('snapshot_id') != manifest['snapshot_id'] or
                value.get('quality_sha256') != manifest['quality_catalog']['sha256']):
            return None
        return evidence_contract.validate(value)
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return None


def window_start(issued, method):
    if method not in 'ABCD' or len(method) != 1:
        raise ValueError('invalid_competing_method')
    if method == 'D':
        return date.min
    year = issued.year - (1 if method == 'A' else 2)
    return date(year, issued.month, min(issued.day, calendar.monthrange(year, issued.month)[1]))


def rank(resolutions, evidence, species_id, issue_date, method, k, *, statistics=None):
    """Rank candidates over 12/24 months or all prior history by maximum I_k."""
    issued = date.fromisoformat(issue_date) if isinstance(issue_date, str) else issue_date
    start = window_start(issued, method)
    result = copy.deepcopy(resolutions)
    selected = {}
    years = set()
    rows = (statistics if statistics is not None else
            evidence_contract.expanded_rows(evidence, species_id=species_id) if evidence else ())
    candidates = {identity(entry['candidate']) for row in result.values()
                  for entry in row.get('candidate_chain', [])}
    if hasattr(rows, 'aggregates_for'):
        aggregates, years = rows.aggregates_for(candidates, start, issued)
    else:
        if hasattr(rows, 'rows_for'):
            rows = rows.rows_for(candidates, start, issued)
        for sid, candidate, day, stats in rows:
            observed = date.fromisoformat(day)
            if sid != species_id or not start <= observed < issued:
                continue
            selected.setdefault(tuple(candidate), []).append((day, stats)); years.add(observed.year)
        aggregates = {key: (*[sum(s[i] for _,s in parts) for i in range(6)],
                           min(s[6] for _,s in parts), max(s[7] for _,s in parts),
                           tuple(sorted((day,s[8]) for day,s in parts)))
                      for key,parts in selected.items()}
    scores = {}
    for day, row in result.items():
        eligible = []
        for entry in row.get('candidate_chain', []):
            key = identity(entry['candidate']); stats = aggregates.get(key)
            if stats is None:
                continue
            n, p, tp, fp, error, baseline, minimum, maximum, population = stats
            if not (p > 0 and n > p and tp + fp > 0 and error < baseline and
                    maximum - minimum > 1e-6):
                continue
            score = 100 * (tp - k * fp) / p
            entry['competing_score'] = score
            entry['competing_n'] = n
            entry['competing_positive'] = p
            entry['competing_net'] = tp - k * fp
            eligible.append((entry, population, n))
            scores[key] = score
        if eligible:
            # As in the native audit: never compare different observation sets.
            populations = {population: n for _, population, n in eligible}
            population = min(populations, key=lambda p: (-populations[p], p))
            chain = [e for e, pop, _ in eligible if pop == population]
            chain.sort(key=lambda e: -e['competing_score'])  # native order breaks ties
            row.update(candidate_chain=chain, candidate=copy.deepcopy(chain[0]['candidate']), selection_status='winner')
        else:
            row.update(candidate_chain=[], candidate=None, selection_status='abstain')
    return result, sorted(years), scores


def order_week(resolutions):
    """Reorder already native-aggregated common families by mean daily I_k."""
    from rainmapper_core.mushroom_ml_multiversion_comparison import _weekly_candidate_family
    weekly = all(r.get('weekly_model_selection', {}).get('status') != 'daily_fallback' and
                 r.get('selection_status') == 'winner' for r in resolutions.values())
    if not weekly:
        return resolutions
    totals = {}
    for row in resolutions.values():
        for entry in row['candidate_chain']:
            family = _weekly_candidate_family(entry['candidate'])
            net, positive = totals.get(family, (0, 0))
            totals[family] = (net + entry['competing_net'], positive + entry['competing_positive'])
    scores = {family:100 * net / positive for family,(net,positive) in totals.items()}
    for row in resolutions.values():
        row['candidate_chain'].sort(key=lambda e: -scores[_weekly_candidate_family(e['candidate'])])
        for entry in row['candidate_chain']:
            entry['competing_score'] = scores[_weekly_candidate_family(entry['candidate'])]
        row['candidate'] = copy.deepcopy(row['candidate_chain'][0]['candidate'])
    return resolutions
