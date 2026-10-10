"""Common, past-only evaluation of complete selection procedures.

Worker code supplies a replay of ALL seven days of each issued week. This
module deliberately cannot substitute a probability at the observed date for
that replay. A technical absence excludes the whole visit for all procedures;
an ordinary selector abstention remains an evaluated opportunity.
"""
from __future__ import annotations

from collections import Counter
from bisect import bisect_left
from datetime import date, timedelta
import json
import math

METHODS = ('habitual', 'A', 'B', 'C', 'D')
PROTOCOL = 'common_selection_walk_forward_v1'
MAX_VISITS = 10000
HISTORY_VERSION = 1
MAX_HISTORY_BYTES = 2 * 1024 * 1024


def _score_counts(counts, k, *, start, end, missing):
    """One shared scoring rule for current, historical and merged results.

    Counts: total visits, common visits, common positives, then integer
    TP/FP/abstention horizon counts for each method (denominator seven).
    """
    total, n, positive = counts[:3]
    scores = {}
    for i, method in enumerate(METHODS):
        tp, fp, abstain = (v / 7 for v in counts[3 + 3*i:6 + 3*i])
        scores[method] = dict(ik=100*(tp-k*fp)/positive if positive else None,
            tp=tp, fp=fp, calls=tp+fp, abstentions=abstain,
            precision=tp/(tp+fp) if tp+fp else None, recall=tp/positive if positive else None)
    ready = bool(positive and n > positive and all(s['abstentions'] < n for s in scores.values()))
    best = max(s['ik'] for s in scores.values()) if ready else None
    return dict(status='ready' if ready else 'insufficient', visits=n, positive=positive,
        total_visits=total, start=start, end=end, missing=dict(missing), methods=scores,
        winners=[m for m, s in scores.items() if best is not None and math.isclose(s['ik'], best, rel_tol=0, abs_tol=1e-9)])


class _DailyCounts:
    """Bounded counters, no observation identities, models or forecast panels."""
    def __init__(self):
        self.days = {}
        self.absences = {}
        self.reasons = {}
        self.estimated_bytes = 0
        self.total = 0

    def _reserve(self, size):
        if self.estimated_bytes + size > MAX_HISTORY_BYTES:
            raise ValueError('comparison_history_size_limit')
        self.estimated_bytes += size

    def add(self, sid, day, counts, missing):
        self.total += counts[0]
        if self.total > MAX_VISITS:
            raise ValueError('comparison_visit_limit')
        if sid not in self.days:
            self._reserve(len(json.dumps(sid).encode()) + 128)
            self.days[sid] = {}
        days = self.days[sid]
        if day not in days:
            # 18 integers <= 70000, ISO date, punctuation; conservative bound.
            self._reserve(192)
            days[day] = [0] * 18
        days[day] = [a+b for a, b in zip(days[day], counts)]
        absences = self.absences.setdefault(sid, Counter())
        reasons = self.reasons.setdefault(sid, set())
        for reason, n in missing.items():
            if reason not in reasons:
                if len(reasons) >= 64:
                    raise ValueError('comparison_history_reason_limit')
                self._reserve(len(json.dumps(reason).encode()) + 1)
                reasons.add(reason)
            if (day, reason) not in absences:
                self._reserve(40)
            absences[day, reason] += n

    def finish(self):
        histories = {}
        for sid, days in sorted(self.days.items()):
            cumulative = [0] * 18
            rows = []
            for day, counts in sorted(days.items()):
                cumulative = [a+b for a, b in zip(cumulative, counts)]
                rows.append([day, *cumulative])
            reasons = sorted(self.reasons[sid])
            index = {reason:i for i, reason in enumerate(reasons)}
            histories[sid] = dict(rows=rows, reasons=reasons,
                missing=[[day, index[reason], n] for (day, reason), n in sorted(self.absences[sid].items())])
        return dict(version=HISTORY_VERSION, species=histories)


def _historical_species(history, cutoff, k):
    rows = history['rows']
    stop = bisect_left(rows, cutoff, key=lambda row: row[0])
    counts = rows[stop-1][1:] if stop else [0] * 18
    n = counts[1]
    # First and last included common-visit dates, even with technical misses.
    start = rows[bisect_left(rows, 1, key=lambda row: row[2])][0] if n else None
    end = rows[bisect_left(rows, n, key=lambda row: row[2])][0] if n else None
    missing = Counter()
    for day, reason, count in history['missing']:
        if day >= cutoff:
            break
        missing[history['reasons'][reason]] += count
    return _score_counts(counts, k, start=start, end=end, missing=missing)


def at_date(value, species_id, cutoff):
    """Return just five scores; never transport the timeline to a map point."""
    if species_id not in value['species']:
        return None
    if cutoff >= value['cutoff']:
        row = value['species'][species_id]
        cutoff = value['cutoff']
    elif 'history' in value:
        row = _historical_species(value['history']['species'][species_id], cutoff, value['k'])
    else:
        return None
    return dict(protocol=value['protocol'], k=value['k'], cutoff=cutoff, species={species_id:row})


def merge_histories(results):
    """Merge disjoint replay partitions by daily deltas; never replay a visit."""
    daily = _DailyCounts()
    for result in results:
        for sid, history in result['history']['species'].items():
            missing = {}
            for day, reason, n in history['missing']:
                missing.setdefault(day, Counter())[history['reasons'][reason]] += n
            previous = [0] * 18
            for day, *counts in history['rows']:
                daily.add(sid, day, [a-b for a, b in zip(counts, previous)], missing.get(day, {}))
                previous = counts
    return daily.finish()


class MissingReplay(ValueError):
    """A missing historical input, never an unfavorable prediction."""


def decision(week, horizon):
    """Read the observed day only AFTER the native full-week resolver ran."""
    from rainmapper_core import mushroom_recommendation_policy as policy
    days = week.get('days')
    if not isinstance(days, list) or len(days) != 7:
        raise ValueError('comparison_requires_complete_week')
    day = days[horizon - 1]
    active = day['reliability_selection']
    operational = day['operational_comparison']
    winners = operational.get('selected_winners', [])
    if active.get('selection_status') == 'abstain' or active.get('runtime_selection_status') == 'abstain':
        return None
    if len(winners) != 1:
        return None
    p = winners[0].get('probability')
    if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError('invalid_comparison_probability')
    notice = policy.map_notice(operational).get('recommendation_decision') or {}
    withheld = notice.get('mode') == 'prudent' and not notice.get('prudent_recommend')
    return bool(p >= .6 and not withheld)


def evaluate(visits, *, k, cutoff, replay, progress=lambda event: None):
    """Each common visit weighs one; its seven issue dates each weigh 1/7.

    ``replay(visit, issue, k)`` must choose using only evidence available before
    issue and return five decisions from complete weeks, or raise MissingReplay.
    Neither the target label nor future visits are passed to the callback.
    """
    from rainmapper_core.mushroom_map_competing import valid_k
    if not valid_k(k):
        raise ValueError('invalid_comparison_k')
    end = date.fromisoformat(cutoff)
    if len(visits) > MAX_VISITS:
        raise ValueError('comparison_visit_limit')
    seen = set(); total = Counter(); daily = _DailyCounts()
    for visit in sorted(visits, key=lambda v: (v['day'], v['species_id'], v['id'])):
        sid, oid = visit['species_id'], visit['id']
        if (sid, oid) in seen:
            raise ValueError('duplicate_comparison_visit')
        seen.add((sid, oid))
        target = date.fromisoformat(visit['day'])
        if target >= end:
            continue
        if type(visit['y']) is not int or visit['y'] not in (0, 1):
            raise ValueError('invalid_comparison_target')
        total[sid] += 1
        outcomes = {method: [] for method in METHODS}
        try:
            for horizon in range(1, 8):
                issue = target - timedelta(days=horizon - 1)
                # Do not give the evaluator the answer it is about to predict.
                identity = {key: visit[key] for key in ('id', 'species_id', 'day')}
                result = replay(identity, issue, k)
                if set(result) != set(METHODS) or any(type(v) is not bool and v is not None for v in result.values()):
                    raise ValueError('invalid_comparison_decisions')
                for method in METHODS:
                    outcomes[method].append(result[method])
        except MissingReplay as exc:
            daily.add(sid, visit['day'], [1] + [0]*17, {str(exc)[:160] or 'missing_replay':1})
        else:
            counts = [1, 1, visit['y']]
            for method in METHODS:
                favorable = sum(v is True for v in outcomes[method])
                counts.extend([favorable if visit['y'] else 0, favorable if not visit['y'] else 0,
                               sum(v is None for v in outcomes[method])])
            daily.add(sid, visit['day'], counts, {})
        progress({'phase': 'Comparing Habitual/A/B/C/D', 'completed_visits': sum(total.values()),
                  'total_visits': len(visits)})
    history = daily.finish()
    result = dict(protocol=PROTOCOL, k=k, cutoff=cutoff, history=history,
        species={sid:_historical_species(row, cutoff, k) for sid,row in history['species'].items()})
    return result


def validate(value):
    """Small public result only; no observation identities or weekly panels."""
    from rainmapper_core.mushroom_map_competing import valid_k
    if not isinstance(value, dict) or value.get('protocol') != PROTOCOL or not valid_k(value.get('k')):
        raise ValueError('invalid_rule_comparison')
    date.fromisoformat(value['cutoff'])
    if not isinstance(value.get('species'), dict) or len(value['species']) > 128:
        raise ValueError('invalid_rule_comparison_species')
    for sid, row in value['species'].items():
        if not isinstance(sid, str) or not 0 < len(sid) <= 160 or row.get('status') not in ('ready', 'insufficient'):
            raise ValueError('invalid_rule_comparison_status')
        for name in ('visits', 'positive', 'total_visits'):
            if type(row.get(name)) is not int or not 0 <= row[name] <= MAX_VISITS:
                raise ValueError('invalid_rule_comparison_count')
        if not row['positive'] <= row['visits'] <= row['total_visits']:
            raise ValueError('invalid_rule_comparison_denominator')
        missing = row.get('missing')
        if (not isinstance(missing, dict) or len(missing) > 64 or
                any(not isinstance(reason, str) or not 0 < len(reason) <= 160 or type(n) is not int or n <= 0
                    for reason, n in missing.items()) or sum(missing.values()) != row['total_visits'] - row['visits']):
            raise ValueError('invalid_rule_comparison_absences')
        if set(row.get('methods', {})) != set(METHODS):
            raise ValueError('invalid_rule_comparison_methods')
        for name in ('start', 'end'):
            if row.get(name) is not None:
                date.fromisoformat(row[name])
                if row[name] >= value['cutoff']:
                    raise ValueError('future_rule_comparison')
        for score in row['methods'].values():
            for name in ('tp', 'fp', 'calls', 'abstentions'):
                number = score.get(name)
                if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= row['visits']:
                    raise ValueError('invalid_rule_comparison_score')
            if (score['tp'] > row['positive'] or score['fp'] > row['visits'] - row['positive'] or
                    not math.isclose(score['tp'] + score['fp'], score['calls'], abs_tol=1e-9) or
                    score['calls'] + score['abstentions'] > row['visits'] + 1e-9):
                raise ValueError('invalid_rule_comparison_confusion')
            for metric, denominator in (('precision', score['calls']), ('recall', row['positive'])):
                rate = score.get(metric)
                if (rate is not None if not denominator else
                        type(rate) not in (int, float) or not math.isfinite(rate) or
                        not math.isclose(rate, score['tp'] / denominator, abs_tol=1e-9)):
                    raise ValueError('invalid_rule_comparison_rate')
            expected = 100 * (score['tp'] - value['k'] * score['fp']) / row['positive'] if row['positive'] else None
            if (score.get('ik') is None) != (expected is None) or (expected is not None and
                    (type(score['ik']) not in (int, float) or not math.isclose(score['ik'], expected, abs_tol=1e-8))):
                raise ValueError('invalid_rule_comparison_ik')
        winners = row.get('winners')
        if not isinstance(winners, list) or len(set(winners)) != len(winners) or any(m not in METHODS for m in winners):
            raise ValueError('invalid_rule_comparison_winners')
        eligible = row['status'] == 'ready'
        if eligible and not (0 < row['positive'] < row['visits'] and all(s['abstentions'] < row['visits'] for s in row['methods'].values())):
            raise ValueError('invalid_rule_comparison_support')
        best = max(s['ik'] for s in row['methods'].values()) if eligible else None
        expected_winners = [m for m in METHODS if best is not None and math.isclose(row['methods'][m]['ik'], best, rel_tol=0, abs_tol=1e-9)]
        if winners != expected_winners:
            raise ValueError('invalid_rule_comparison_winners')
    if 'history' in value:
        _validate_history(value)
    return value


def _validate_history(value):
    history = value['history']
    if (not isinstance(history, dict) or type(history.get('version')) is not int or history['version'] != HISTORY_VERSION or
            not isinstance(history.get('species'), dict) or set(history['species']) != set(value['species'])):
        raise ValueError('invalid_comparison_history')
    daily = _DailyCounts()
    for sid, entry in history['species'].items():
        rows, reasons, missing = (entry.get(k) for k in ('rows', 'reasons', 'missing'))
        if (not isinstance(rows, list) or not 0 < len(rows) <= MAX_VISITS or
                not isinstance(reasons, list) or len(reasons) > 64 or
                any(not isinstance(r, str) or not 0 < len(r) <= 160 for r in reasons) or
                reasons != sorted(set(reasons)) or not isinstance(missing, list) or len(missing) > MAX_VISITS):
            raise ValueError('invalid_comparison_history_rows')
        missing_by_day = {}
        last = None
        for event in missing:
            if (not isinstance(event, list) or len(event) != 3 or not isinstance(event[0], str) or
                    type(event[1]) is not int or not 0 <= event[1] < len(reasons) or
                    type(event[2]) is not int or not 0 < event[2] <= MAX_VISITS):
                raise ValueError('invalid_comparison_history_missing')
            day, reason, n = event
            key = (day, reason)
            if last is not None and key <= last:
                raise ValueError('invalid_comparison_history_missing_order')
            last = key
            missing_by_day.setdefault(day, {})[reasons[reason]] = n
        previous_day = ''
        previous = [0] * 18
        for row in rows:
            if (not isinstance(row, list) or len(row) != 19 or not isinstance(row[0], str) or
                    any(type(n) is not int or not 0 <= n <= MAX_VISITS*7 for n in row[1:])):
                raise ValueError('invalid_comparison_history_counts')
            day, *counts = row
            if date.fromisoformat(day).isoformat() != day or not previous_day < day < value['cutoff']:
                raise ValueError('invalid_comparison_history_date')
            delta = [a-b for a,b in zip(counts, previous)]
            total, n, positive = delta[:3]
            absent = missing_by_day.pop(day, {})
            if (any(c < 0 for c in delta) or not 0 <= positive <= n <= total or total < 1 or
                    sum(absent.values()) != total-n):
                raise ValueError('invalid_comparison_history_delta')
            for i in range(5):
                tp, fp, abstain = delta[3+3*i:6+3*i]
                if tp > positive*7 or fp > (n-positive)*7 or tp+fp+abstain > n*7:
                    raise ValueError('invalid_comparison_history_confusion')
            daily.add(sid, day, delta, absent)
            previous, previous_day = counts, day
        if missing_by_day or _historical_species(entry, value['cutoff'], value['k']) != value['species'][sid]:
            raise ValueError('invalid_comparison_history_summary')
