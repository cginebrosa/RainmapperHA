"""Replay the production selectors on past evidence and private weekly panels."""
from __future__ import annotations

from collections import OrderedDict, defaultdict
from bisect import bisect_left
from datetime import date, timedelta
import copy
import hashlib
import json

from rainmapper_core import mushroom_map_competing as competing
from rainmapper_core import mushroom_ml_reliability_audit as audit
from rainmapper_core.mushroom_competing_comparison import METHODS, MissingReplay, decision
from rainmapper_core.mushroom_map_prediction import prepare_species_week_resolutions
from rainmapper_core.mushroom_map_prediction import iter_species_week
from rainmapper_core.mushroom_phenology import season_phase_for_months


class SealedScalars(dict):
    """Read-only scalar evidence shared safely across copied resolver plans."""
    def __init__(self, values):
        if any(not (v is None or type(v) in (str, int, float, bool)) for v in values.values()):
            raise ValueError('replay_evidence_must_be_scalar')
        super().__init__(values)

    def __deepcopy__(self, memo):
        return self

    def _immutable(self, *args, **kwargs):
        raise TypeError('sealed_replay_evidence')

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable


def cohort(oid, y, group):
    return hashlib.sha256(json.dumps([oid, y, group]).encode()).hexdigest()[:24]


def pack_unit_index(index, visits):
    """Intern private family/unit/case identities instead of repeating strings."""
    cases = {(v['species_id'], v['id']): i for i, v in enumerate(visits)}
    families = []; units = []; cells = []; family_ids = {}; unit_ids = {}; seen = set()
    for sid, oid, family, key in sorted(index):
        family = tuple(family)
        if family not in family_ids:
            family_ids[family] = len(families); families.append(family)
        if key not in unit_ids:
            unit_ids[key] = len(units); units.append(key)
        identity = cases[sid, oid], family_ids[family]
        if identity in seen:
            raise ValueError('duplicate_comparison_unit')
        seen.add(identity)
        cells.append([*identity, unit_ids[key]])
    return {'families': families, 'units': units, 'cells': cells}


def evaluation(evidence):
    brier, baseline = evidence.get('brier_score'), evidence.get('prevalence_brier_score')
    return {'evidence': 'better_than_prevalence' if brier is not None and baseline is not None and brier < baseline else 'unavailable',
            'brier_score': brier, 'prevalence_brier_score': baseline,
            'brier_delta_vs_prevalence': evidence.get('brier_delta_vs_prevalence'),
            'roc_auc': evidence.get('roc_auc'), 'n_test': evidence.get('observation_count'),
            'test_positive_count': evidence.get('positive_observation_count'),
            'test_negative_count': evidence.get('negative_observation_count')}


class Replay:
    def __init__(self, evidence, *, panels, unit_index, visits, profiles, recommendation_policy, suspensions=()):
        self.evidence, self.panels = evidence, panels
        families = [tuple(f) for f in unit_index['families']]
        self.units = {(visits[vid]['species_id'], visits[vid]['id'], families[fid]): unit_index['units'][uid]
                      for vid, fid, uid in unit_index['cells']}
        self.visits = {(v['species_id'], v['id']): v for v in visits}
        self.context = {cohort(v['id'], v['y'], v['group']): v for v in visits}
        self.profiles, self.policy = profiles, recommendation_policy
        self.suspensions = suspensions
        self.cache = competing.PointCache(max_bytes=16*1024*1024, max_entries=32, shared_values=evidence.values())
        self.pending_replays = {}
        self.pending_week_keys = {}
        self.partial_outcomes = competing.PointCache(max_bytes=2*1024*1024, max_entries=1024)
        self.case_audit = None
        self.daily_statistics = None
        self.rank_cache = competing.PointCache(max_bytes=16*1024*1024, max_entries=96)
        self.week_cache = competing.PointCache(max_bytes=16*1024*1024, max_entries=96)
        self.outcome_cache = competing.PointCache(max_bytes=1024*1024, max_entries=1024)
        bindings = defaultdict(list)
        for vid, fid, uid in unit_index['cells']:
            bindings[vid].append((fid, uid))
        self.bindings = {(v['species_id'], v['id']): hashlib.sha256(
            json.dumps(sorted(bindings[i]), separators=(',', ':')).encode()).digest()
            for i, v in enumerate(visits)}
        self.stats = dict(native_computed=0, native_reused=0, ranks_computed=0, ranks_reused=0, weeks_computed=0, weeks_reused=0)
        from rainmapper_core.mushroom_competing_evidence import cell_rows
        from rainmapper_core.mushroom_competing_columns import Cells
        self.cells = cell_rows(evidence)
        self.cells_by_case = {}
        if not isinstance(self.cells, Cells):
            for cell in self.cells:
                self.cells_by_case.setdefault(cell[0], []).append(cell)

        self.case_dates, self.group_dates = defaultdict(list), defaultdict(list)
        has_case = self.cells.has_case if isinstance(self.cells, Cells) else self.cells_by_case.__contains__
        for i, (species, day, _, identity) in enumerate(evidence['cases']):
            if has_case(i):
                sid = evidence['species'][species]
                self.case_dates[sid].append((day, i))
                self.group_dates[sid, self.context[identity]['group']].append((day, i))
        for entries in (*self.case_dates.values(), *self.group_dates.values()):
            entries.sort()

    def prior(self, visit, issue):
        sid = visit['species_id']; current = self.visits[sid, visit['id']]
        # An episode and a 14-day boundary are excluded together, across species.
        bound = (issue - timedelta(days=14)).isoformat()
        from rainmapper_core.mushroom_competing_columns import Cells
        cases = self.case_dates[sid]
        related = self.group_dates.get((sid, current['group']), ())
        count = bisect_left(cases, (bound, -1))
        excluded_count = bisect_left(related, (bound, -1))
        # Prefixes identify exactly the prior set; no full case scan on a hit.
        key = sid, count, current['group'] if excluded_count else None, excluded_count
        cached = self.cache.get(key)
        if cached is not None:
            self.stats['native_reused'] += 1
            return cached
        excluded = {i for _, i in related[:excluded_count]}
        valid = tuple(sorted(i for _, i in cases[:count] if i not in excluded))
        if self.case_audit is None:
            from rainmapper_core.mushroom_competing_audit import CaseAudit
            self.case_audit = CaseAudit(self.evidence, self.context)
        evidence = {**{k:v for k,v in self.evidence.items() if k != 'packed_cells'},
                    'cells': self.case_audit.cells.subset(valid)}
        report = self.case_audit.report(sid, valid)
        selected = audit.build_selection_catalog(report)['species_selections']
        resolutions = {r['prediction_day']: r for r in selected if r['species_id'] == sid}
        for h in range(1, 8):
            resolutions.setdefault(h, {'selection_status': 'abstain', 'candidate': None, 'candidate_chain': []})
        # Territorial diagnostics are never consumed by this species-level
        # replay. Avoid copying their duplicate evidence through every week.
        for row in resolutions.values():
            for name in ('evidence_by_scope', 'population', 'stability'):
                row.pop(name, None)
            for entry in row.get('candidate_chain', []):
                entry.pop('evidence_by_scope', None)
                entry['evidence'] = SealedScalars(entry['evidence'])
                entry['candidate'] = SealedScalars(entry['candidate'])
            if isinstance(row.get('evidence'), dict):
                row['evidence'] = SealedScalars(row['evidence'])
        if self.daily_statistics is None:
            from rainmapper_core.mushroom_competing_statistics import DailyStatistics
            self.daily_statistics = DailyStatistics(self.evidence, self.case_audit.cells, compact_populations=True)
        # Daily buckets are immutable and shared; a prior only masks dates/groups.
        evidence = {**evidence, '_statistics': self.daily_statistics.view(sid, date.fromisoformat(bound), excluded),
                    '_dates': tuple(sorted({self.evidence['cases'][i][1] for i in valid})),
                    '_prior_key': key}
        self.cache.put(key,(evidence,resolutions))
        self.stats['native_computed'] += 1
        return evidence, resolutions

    def ranked(self, native, evidence, sid, issue, method, k):
        start = competing.window_start(issue, method).isoformat()
        # B and C use the same ranking; daily/weekly resolution happens later.
        dates = evidence['_dates'][bisect_left(evidence['_dates'],start):bisect_left(evidence['_dates'],issue.isoformat())]
        key = evidence['_prior_key'], dates, k
        cached = self.rank_cache.get(key)
        if cached is not None:
            self.stats['ranks_reused'] += 1
            return cached
        result = competing.rank(native, evidence, sid, issue, method, k,
                                statistics=evidence['_statistics'])[0]
        self.stats['ranks_computed'] += 1
        self.rank_cache.put(key,result)
        return result

    def __call__(self, visit, issue, k):
        from rainmapper_core.mushroom_competing_batch import _PendingMember
        key=visit['species_id'],visit['id'],issue,k
        state=self.pending_replays.get(key)
        if state is not None and key in self.pending_week_keys:
            completed=self.outcome_cache.get(self.pending_week_keys[key])
            if completed is not None:
                state[0].close()
                self.pending_replays.pop(key,None);self.pending_week_keys.pop(key,None)
                self.stats['weeks_reused']+=1
                horizon=(date.fromisoformat(visit['day'])-issue).days
                return {method:days[horizon] for method,days in completed.items()}
        if state is None:
            if len(self.pending_replays)>=112:raise ValueError('replay_continuation_limit')
            steps=self._steps(visit,issue,k)
            try:callback,request=next(steps)
            except StopIteration as done:
                self.pending_week_keys.pop(key,None)
                return done.value
            state=steps,callback,request
            self.pending_replays[key]=state
        steps,callback,request=state
        try:
            while True:
                materialized = callback(**request)
                try:
                    callback, request = steps.send(materialized)
                except StopIteration as done:
                    self.pending_replays.pop(key, None)
                    self.pending_week_keys.pop(key, None)
                    return done.value
                self.pending_replays[key] = steps, callback, request
        except _PendingMember:
            raise
        except BaseException:
            self.pending_replays.pop(key,None);self.pending_week_keys.pop(key,None)
            steps.close()
            raise

    def close_pending(self):
        for steps,_,_ in self.pending_replays.values():steps.close()
        self.pending_replays.clear();self.pending_week_keys.clear()

    def _steps(self, visit, issue, k):
        sid, oid = visit['species_id'], visit['id']
        target = date.fromisoformat(visit['day'])
        horizon = (target - issue).days + 1
        phenology = self.profiles.get(sid, {}).get('phenology', {})
        season = lambda d: season_phase_for_months(d, phenology.get('main_months', []), phenology.get('secondary_months', []))
        if season(target) not in ('main', 'secondary'):
            return dict.fromkeys(METHODS)
        evidence, native = self.prior(visit, issue)
        # Sharing is safe only for identical area, issue, prior evidence and
        # the complete family-to-temporal-model binding. Labels are still scored
        # separately by the caller. The cache stores all seven day decisions.
        week_key = (sid, self.visits[sid, oid]['area'], issue, k,
                    evidence['_prior_key'], self.bindings[sid, oid])
        self.pending_week_keys[sid,oid,issue,k]=week_key
        saved_outcomes = self.outcome_cache.get(week_key)
        if saved_outcomes is not None:
            self.stats['weeks_reused'] += 1
            return {method: days[horizon - 1] for method, days in saved_outcomes.items()}
        # Native quality checks remain independent of K for all five rules.
        quality = {competing.identity(e['candidate']): evaluation(e['evidence'])
                   for row in native.values() for e in row.get('candidate_chain', [])}
        versions = sorted({c[0] for c in evidence['candidates']})
        def materialize(*, target_date, selections):
            members = []
            for candidate in selections:
                from rainmapper_core import mushroom_ml_prediction_policy as policy
                reference = {**candidate, 'species_id': sid}
                if policy.suspension({policy.FIELD: self.suspensions}, reference):
                    members.append({'available': False, 'reason': 'model_suspended', 'model_ref': reference})
                    continue
                identity = competing.identity(candidate)
                family = identity[:3] + identity[4:]
                key = self.units.get((sid, oid, family))
                if key is None:
                    raise MissingReplay('temporal_model_unavailable')
                if hasattr(self.panels, 'read_week_member'):
                    member = self.panels.read_week_member(key,sid,oid,target_date,candidate['horizon_days'],issue=issue)
                else:
                    member = self.panels.read(key, sid, oid, target_date, candidate['horizon_days'])
                members.append({**copy.deepcopy(member), 'model_ref': {**candidate, 'species_id': sid},
                                'evaluation': quality.get(identity, {})})
            return {'members': members}
        outcomes = {}; resolved = {}
        for method in METHODS:
            partial_key = week_key, method
            previous = self.partial_outcomes.get(partial_key)
            if previous is not None:
                outcomes[method] = previous
                continue
            ranked = native if method == 'habitual' else self.ranked(native, evidence, sid, issue, method, k)
            plan_key = id(ranked), method == 'C', method == 'habitual'
            if plan_key in resolved and resolved[plan_key][0] is ranked:
                outcomes[method] = resolved[plan_key][1]
                continue
            saved = self.week_cache.get(plan_key)
            if saved is None or saved[0] is not ranked:
                plan = prepare_species_week_resolutions(
                    species_id=sid, point_id='historical-visit', resolutions_by_day=ranked,
                    issue_date=None, installed_version_ids=versions, independent_days=method == 'C',
                    order_week=None if method == 'habitual' else competing.order_week)
                self.week_cache.put(plan_key,(ranked,plan))
            else:
                plan = saved[1]
            resolver = iter_species_week(species_id=sid, point_id='historical-visit', issue_date=issue,
                resolutions_by_day=ranked, installed_version_ids=versions, materialize=materialize,
                season_phase=season, phenology=phenology, lazy_families=True,
                recommendation_policy=self.policy, independent_days=method == 'C',
                order_week=None if method == 'habitual' else competing.order_week,
                prepared_resolutions=plan)
            try:
                request=next(resolver)
                while True:
                    materialized=yield materialize,request
                    request=resolver.send(materialized)
            except StopIteration as done:
                week=done.value
            finally:
                resolver.close()
            outcomes[method] = tuple(decision(week, h) for h in range(1, 8))
            # A later method may pause on a missing member. Keep only this
            # completed decision, so resuming never resolves it a second time.
            self.partial_outcomes.put(partial_key, outcomes[method])
            resolved[plan_key] = ranked, outcomes[method]
        self.outcome_cache.put(week_key,outcomes)
        self.stats['weeks_computed'] += 1
        return {method: days[horizon - 1] for method, days in outcomes.items()}
