import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from rainmapper_core import mushroom_map_competing as c
from rainmapper_core import mushroom_prediction_map as contract
from rainmapper_core.mushroom_map_prediction import resolve_species_week
from tests import test_mushroom_map_prediction as fixtures


class CompetingTests(unittest.TestCase):
    def test_point_cache_drops_large_diagnostics_and_evicts_within_byte_budget(self):
        cache = c.PointCache(max_bytes=2000)
        cache.put('large', {'diagnostic':'x'*5000})
        self.assertIsNone(cache.get('large'))
        for index in range(10):
            cache.put(str(index), {'members':[{'probability':.7,'label':'x'*200}]})
        self.assertIsNone(cache.get('0'))
        self.assertIsNotNone(cache.get('9'))
        self.assertLessEqual(cache.size,2000)

    def test_point_cache_lru_shares_owned_immutable_inputs_but_limits_new_values(self):
        shared = {'cases':['x'*5000]}
        cache = c.PointCache(max_bytes=2000,max_entries=2,shared_values=(shared,))
        cache.put('a',{'input':shared,'score':1})
        cache.put('b',{'input':shared,'score':2})
        self.assertIs(cache.get('a')['input'],shared)
        cache.put('c',{'input':shared,'score':3})
        self.assertIsNone(cache.get('b'))
        self.assertIsNotNone(cache.get('a'))
        self.assertLessEqual(cache.size,2000)
        cache.clear()
        self.assertEqual(cache.size,0)
        self.assertIsNone(cache.get('a'))

    def rank(self, original, evidence, sid, issue, method, k):
        from unittest.mock import patch
        rows = [(species, ref, f'{when}-10-01' if isinstance(when,int) else when, stats)
                for species,ref,when,stats in (evidence or {}).get('rows',[])]
        issued = f'{issue}-01-01' if isinstance(issue,int) else issue
        with patch.object(c.evidence_contract, 'expanded_rows', return_value=iter(rows)):
            return c.rank(original, evidence, sid, issued, method, k)

    def fixture(self):
        resolutions = fixtures.PointWeekTests().resolutions()
        rows = []
        for day, row in resolutions.items():
            for index, entry in enumerate(row['candidate_chain']):
                # Lower K likes more detections; higher K likes fewer errors.
                tp, fp = (9, 3) if index == 0 else (6, 1)
                rows.append(['s', list(c.identity(entry['candidate'])), 2025,
                             [20, 10, tp, fp, 1, 5, .1, .9, 'same-cases']])
        return resolutions, {'rows':rows}

    def test_cost_orders_highest_not_nearest_zero_without_mutating_native(self):
        original, evidence = self.fixture(); before = copy.deepcopy(original)
        for k, expected in [(0, 'quality_first'), (1, 'quality_first'), (4, 'coverage_first'), (100, 'coverage_first')]:
            ranked, years, _ = self.rank(original, evidence, 's', 2026, 'A', k)
            self.assertEqual(years, [2025])
            self.assertEqual(ranked[1]['candidate']['estimator_id'], expected)
        self.assertEqual(original, before)

    def test_windows_include_old_history_but_never_query_or_future_year(self):
        original, evidence = self.fixture()
        for year in [2010, 2024, 2026, 2027]:
            evidence['rows'] += [[sid, ref, year, stats] for sid, ref, _, stats in evidence['rows'][:14]]
        for method, wanted in [('A',[2025]), ('B',[2024,2025]), ('C',[2024,2025]), ('D',[2010,2024,2025])]:
            _, years, _ = self.rank(original, evidence, 's', 2026, method, 4)
            self.assertEqual(years, wanted)

    def test_missing_and_single_class_abstain_not_zero_or_unfavorable(self):
        original, evidence = self.fixture()
        for source in [None, {'rows':[]}]:
            rows, years, _ = self.rank(original, source, 's', 2026, 'D', 4)
            self.assertTrue(all(r['selection_status'] == 'abstain' for r in rows.values()))
        for row in evidence['rows']:
            row[3][1] = 0
        rows, _, _ = self.rank(original, evidence, 's', 2026, 'D', 4)
        self.assertEqual(rows[1]['candidate_chain'], [])

    def test_different_populations_are_never_compared_by_utility(self):
        original, evidence = self.fixture()
        # Candidate two's spectacular score on one positive must not displace
        # the candidate with the larger comparable population.
        for row in evidence['rows']:
            if row[1][-1] == 'coverage_first':
                row[3] = [2,1,1,0,.1,.5,.1,.9,'different']
        ranked, _, _ = self.rank(original, evidence, 's', 2026, 'A', 4)
        self.assertEqual(len(ranked[1]['candidate_chain']), 1)
        self.assertEqual(ranked[1]['candidate']['estimator_id'], 'quality_first')

    def test_week_ranking_uses_k_and_keeps_applicability_veto(self):
        fixture = fixtures.PointWeekTests(); original, evidence = self.fixture()
        ranked, _, _ = self.rank(original, evidence, 's', 2026, 'A', 4)
        def run(veto):
            return resolve_species_week(species_id='s', point_id='p', issue_date=fixture.issue,
                resolutions_by_day=ranked, installed_version_ids=['biology_v6'],
                materialize=fixture.materializer(veto), season_phase=lambda _: 'main', phenology={},
                lazy_families=True, order_week=c.order_week)
        result = run({})
        self.assertEqual(result['days'][0]['reliability_selection']['candidate']['estimator_id'], 'coverage_first')
        result = run({'coverage_first':{7}})
        self.assertEqual(result['days'][0]['reliability_selection']['candidate']['estimator_id'], 'quality_first')

    def test_c_chooses_each_day_independently(self):
        fixture = fixtures.PointWeekTests(); original, evidence = self.fixture()
        for row in evidence['rows']:
            if row[1][3] == 7 and row[1][-1] == 'quality_first':
                row[3][2:4] = [9,0]
        ranked, _, _ = self.rank(original, evidence, 's', 2026, 'C', 4)
        result = resolve_species_week(species_id='s', point_id='p', issue_date=fixture.issue,
            resolutions_by_day=ranked, installed_version_ids=['biology_v6'], materialize=fixture.materializer(),
            season_phase=lambda _: 'main', phenology={}, lazy_families=True, independent_days=True)
        self.assertEqual([d['reliability_selection']['candidate']['estimator_id'] for d in result['days']],
                         ['coverage_first']*6+['quality_first'])

    def test_request_rejects_invalid_cost_and_identity_mismatch(self):
        from tests.test_mushroom_map_queries import request
        req = {**request(), 'species_ids':[], 'competing_selection':True, 'k_value':4}
        self.assertEqual(contract.parse_request(json.dumps(req).encode())['k_value'], 4)
        for invalid in [-1, True, '4', float('nan'), float('inf'), 1001]:
            with self.assertRaises(ValueError):
                contract.parse_request(json.dumps({**req, 'k_value':invalid}).encode())
        result = contract.demo_result(req); result['execution'] = {'mode':req['execution']}
        contract.validate_result(result, req)
        result['k_value'] = 3
        with self.assertRaises(ValueError): contract.validate_result(result, req)

    def test_moving_windows_include_current_year_and_d_keeps_older_cases(self):
        original, evidence = self.fixture()
        rows = evidence['rows']
        dates = ['2016-10-01', '2024-10-04', '2024-10-05', '2025-10-04',
                 '2025-10-05', '2026-09-01', '2026-10-05', '2026-10-06']
        evidence['rows'] = [[sid, ref, day, stats] for day in dates for sid, ref, _, stats in rows]
        expected = {'A': [2025,2026], 'B': [2024,2025,2026], 'C': [2024,2025,2026], 'D': [2016,2024,2025,2026]}
        for method, years in expected.items():
            ranked, actual, _ = self.rank(original, evidence, 's', '2026-10-05', method, 4)
            self.assertEqual(actual, years)
            days = {'A': 2, 'B': 4, 'C': 4, 'D': 6}[method]
            self.assertEqual(ranked[1]['candidate_chain'][0]['competing_n'], 20 * days)
        from datetime import date
        self.assertEqual(c.window_start(date(2024,2,29),'A'), date(2023,2,28))

    def test_temporal_result_is_bound_to_batch_and_malformed_stats_fail_closed(self):
        from rainmapper_core import mushroom_competing_evidence as e
        original, _ = self.fixture(); ref = original[1]['candidate']
        manifest = {'batch_id':'b', 'snapshot_id':'s', 'quality_catalog':{'sha256':'q'}}
        unit = {'family':ref, 'reused':False, 'missing':[], 'rows':[
            ['s','obs1','2026-09-01',ref['horizon_days'],1,.8,.5,'g1']]}
        value = e.summarize([unit],manifest=manifest,revision='a'*64,cutoff='2026-10-05')
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/c.FILENAME; target.write_bytes(c.encode(value))
            self.assertEqual(c.read(target,manifest),json.loads(c.encode(value)))
            self.assertIsNone(c.read(target,{**manifest,'batch_id':'other'}))
            value['cells'][0][2] = 99
            target.write_bytes(c.encode(value))
            self.assertIsNone(c.read(target,manifest))

    def test_old_workers_are_not_assigned_competing_queries(self):
        from tests.test_mushroom_map_queries import request
        from rainmapper_core.mushroom_map_queries import QueryBroker, QueryError
        broker = QueryBroker(); self.addCleanup(broker.close)
        req = {**request(), 'competing_selection':True, 'k_value':4}
        broker.worker_poll('old')
        with self.assertRaises(QueryError): broker.submit('u',req)
        broker.worker_poll('new',capabilities=[c.CAPABILITY])
        broker.submit('u',req)
        self.assertIsNone(broker.worker_poll('old')['query'])
        self.assertIsNotNone(broker.worker_poll('new',capabilities=[c.CAPABILITY])['query'])
