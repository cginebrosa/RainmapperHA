import copy
from datetime import date
import tempfile
from pathlib import Path
import unittest

from rainmapper_core import mushroom_competing_comparison as comparison
from rainmapper_core import mushroom_competing_panels as panels
from rainmapper_core import mushroom_map_competing as competing


class ComparisonTests(unittest.TestCase):
    def visits(self):
        return [{'id': str(i), 'species_id': 's', 'day': f'2026-09-{i + 10:02d}', 'y': y}
                for i, y in enumerate([1, 1, 0, 0])]

    def test_common_visits_weight_one_native_participates_ties_and_cost_reranks(self):
        calls = []
        def replay(visit, issue, k):
            self.assertNotIn('y', visit)
            self.assertLessEqual(issue, date.fromisoformat(visit['day']))
            calls.append((visit['id'], issue, k))
            return {'habitual': visit['id'] in ('0', '1'),
                    'A': visit['id'] in ('0', '1'), 'B': True,
                    'C': visit['id'] == '0', 'D': visit['id'] == '0' if k > 1 else True}
        result = comparison.evaluate(self.visits(), k=4, cutoff='2026-10-06', replay=replay)
        comparison.validate(result)
        row = result['species']['s']
        self.assertEqual(len(calls), 4 * 7)
        self.assertEqual(row['visits'], 4)
        self.assertEqual(row['positive'], 2)
        self.assertEqual(row['methods']['habitual']['ik'], 100)
        self.assertEqual(row['methods']['B']['ik'], -300)
        self.assertEqual(row['winners'], ['habitual', 'A'])
        low = comparison.evaluate(self.visits(), k=0, cutoff='2026-10-06', replay=replay)
        self.assertEqual(low['species']['s']['winners'], ['habitual', 'A', 'B', 'D'])

    def test_partial_horizon_missing_excludes_whole_visit_for_everyone(self):
        def replay(visit, issue, k):
            if visit['id'] == '1' and issue.day == 9:
                raise comparison.MissingReplay('weather_missing')
            return dict.fromkeys(comparison.METHODS, visit['id'] == '0')
        row = comparison.evaluate(self.visits(), k=4, cutoff='2026-10-06', replay=replay)['species']['s']
        self.assertEqual((row['visits'], row['positive'], row['total_visits']), (3, 1, 4))
        self.assertEqual(row['missing'], {'weather_missing': 1})
        self.assertTrue(all(s['ik'] == 100 for s in row['methods'].values()))

    def test_abstention_keeps_opportunities_and_no_green_without_comparable_support(self):
        value = comparison.evaluate(self.visits(), k=4, cutoff='2026-10-06',
                                    replay=lambda *args: dict.fromkeys(comparison.METHODS))
        row = value['species']['s']
        self.assertEqual((row['visits'], row['positive']), (4, 2))
        self.assertEqual(row['winners'], [])
        self.assertEqual(row['status'], 'insufficient')
        self.assertEqual(row['methods']['habitual']['abstentions'], 4)
        comparison.validate(value)

    def test_future_visits_duplicate_and_bad_scores_fail_closed(self):
        replay = lambda *args: dict.fromkeys(comparison.METHODS, False)
        visits = self.visits()
        result = comparison.evaluate(visits, k=4, cutoff='2026-09-12', replay=replay)
        self.assertEqual(result['species']['s']['total_visits'], 2)
        self.assertEqual(result['species']['s']['winners'], [])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            comparison.evaluate(visits + visits[:1], k=4, cutoff='2026-10-06', replay=replay)
        broken = copy.deepcopy(result)
        broken['species']['s']['methods']['habitual']['ik'] = 9
        with self.assertRaises(ValueError):
            comparison.validate(broken)
        legacy = {key:value for key,value in result.items() if key != 'history'}
        self.assertIsNone(competing.comparison_for({'comparisons': [legacy]}, 's', '2026-09-11', 4))
        self.assertIsNone(competing.comparison_for({'comparisons': [result]}, 's', '2026-09-12', 3))
        self.assertIsNotNone(competing.comparison_for({'comparisons': [result]}, 's', '2026-09-12', 4))

    def test_history_matches_separate_past_only_evaluation_without_replay_on_lookup(self):
        from unittest.mock import Mock
        from datetime import timedelta
        visits = self.visits() + [dict(id='same-day', species_id='s', day='2026-09-12', y=1),
            dict(id='missing', species_id='s', day='2026-09-14', y=1),
            dict(id='earlier-missing', species_id='s', day='2026-09-08', y=0)]
        def replay(v, issue, k):
            if 'missing' in v['id']:
                raise comparison.MissingReplay('weather_missing')
            return {method:None if i == issue.day % 5 else issue.day % (i+2) == 0
                    for i,method in enumerate(comparison.METHODS)}
        tracked = Mock(side_effect=replay)
        result = comparison.evaluate(visits, k=4, cutoff='2026-10-01', replay=tracked)
        calls = tracked.call_count
        comparison.validate(result)
        for offset in range(12):
            cutoff = (date(2026,9,7) + timedelta(days=offset)).isoformat()
            historical = competing.comparison_for({'comparisons':[result]}, 's', cutoff, 4)
            expected = comparison.evaluate(visits, k=4, cutoff=cutoff, replay=replay)
            row = historical['species']['s']
            if expected['species']:
                self.assertEqual(row, expected['species']['s'], cutoff)
            else:
                self.assertEqual((row['visits'], row['total_visits'], row['winners']), (0,0,[]))
            self.assertNotIn('history', historical)
            self.assertLess(len(__import__('json').dumps(historical)), 2000)
            comparison.validate(historical)
        self.assertEqual(tracked.call_count, calls)
        # One prefix per observation date; same-day observations coalesce.
        self.assertEqual(len(result['history']['species']['s']['rows']), 6)
        legacy = {key:value for key,value in result.items() if key != 'history'}
        self.assertEqual(competing.comparison_unavailable_reason({'comparisons':[legacy]}, 's', '2026-09-12', 4), 'historical_not_prepared')
        self.assertEqual(competing.comparison_unavailable_reason({'comparisons':[legacy]}, 's', '2026-09-12', 3), 'pending')

    def test_history_rejects_corruption_and_preserves_common_denominator(self):
        result = comparison.evaluate(self.visits(), k=4, cutoff='2026-10-01',
            replay=lambda *args: dict.fromkeys(comparison.METHODS, True))
        for mutation in ('future', 'negative_delta', 'different_final', 'wrong_counts', 'duplicate_day'):
            value = copy.deepcopy(result)
            rows = value['history']['species']['s']['rows']
            if mutation == 'future': rows[-1][0] = '2026-10-01'
            if mutation == 'negative_delta': rows[1][1] = 0
            if mutation == 'different_final': rows[-1][4] -= 1
            if mutation == 'wrong_counts': rows[0][4] = 8
            if mutation == 'duplicate_day': rows[1][0] = rows[0][0]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                comparison.validate(value)
        from unittest.mock import patch
        with patch.object(comparison, 'MAX_HISTORY_BYTES', 100), self.assertRaisesRegex(ValueError, 'history_size_limit'):
            comparison.evaluate(self.visits(), k=4, cutoff='2026-10-01',
                replay=lambda *args: dict.fromkeys(comparison.METHODS, True))

    def test_week_replay_rejects_observed_day_only(self):
        with self.assertRaisesRegex(ValueError, 'complete_week'):
            comparison.decision({'days': [{}]}, 1)

    def test_production_native_audit_and_full_week_replay_ignore_target_and_future_labels(self):
        from rainmapper_core import mushroom_competing_evidence as evidence
        from rainmapper_core.mushroom_competing_replay import Replay, pack_unit_index
        from rainmapper_core import mushroom_recommendation_policy as recommendations
        from tests.test_mushroom_map_prediction import PointWeekTests
        from datetime import timedelta
        refs = [e['candidate'] for e in PointWeekTests().resolutions()[1]['candidate_chain']]
        visits = [{'id':str(i), 'species_id':'s', 'day':f'2026-06-{i+1:02d}', 'y':i%2,
                   'group':f'group{i}', 'area':'synthetic-area'} for i in range(12)]
        visits += [{'id':oid, 'species_id':'s', 'day':day, 'y':1,
                    'group':group, 'area':'synthetic-area'} for oid,day,group in (
                        ('future','2026-11-01','future-group'),
                        ('recent','2026-10-01','recent-group'),
                        ('episode','2026-06-20','target-group'))]
        visit = {'id':'target','species_id':'s','day':'2026-10-06','y':1,'group':'target-group','area':'synthetic-area'}
        units = []
        index = []
        for ref in refs:
            rows = [[v['species_id'],v['id'],v['day'],h,v['y'],.8 if v['y'] else .2,.5,v['group']]
                    for v in visits for h in range(1,8)]
            units.append({'family':ref,'reused':False,'missing':[],'rows':rows})
            index.append(['s','target',[ref[k] for k in ('version_id','profile_id','temporal_contract_id','estimator_id')], 'unit'])
        value = evidence.summarize(units,manifest={'batch_id':'b','snapshot_id':'s','quality_catalog':{'sha256':'q'}},
                                   revision='a'*64,cutoff='2026-12-01')
        calls = []
        class PanelFixture:
            def read(self, key, sid, oid, target, horizon):
                calls.append((target, horizon))
                return {'available':True, 'prediction':{'probability':.8,
                    'applicability':{'status':'within_observed_range'}}, 'features_used':{}}
        peer = {**visit, 'id':'peer', 'y':0}
        changed_area = {**peer, 'id':'other-area', 'area':'elsewhere'}
        changed_model = {**peer, 'id':'other-model'}
        extra = [peer, changed_area, changed_model]
        extra_index = [[sid, v['id'], family, 'other-unit' if v is changed_model else key]
                       for sid, _, family, key in index for v in extra]
        replay = Replay(value, panels=PanelFixture(), unit_index=pack_unit_index(index+extra_index, visits+[visit]+extra), visits=visits+[visit]+extra,
                        profiles={'s':{'phenology':{'main_months':list(range(1,13))}}},
                        recommendation_policy=recommendations.settings({}))
        identity = {k:visit[k] for k in ('id','species_id','day')}
        issue = date(2026,10,6)
        prior, native = replay.prior(identity, issue)
        self.assertEqual(len(prior['cells']), 12 * 7 * len(refs))
        self.assertEqual(set(native), set(range(1,8)))
        self.assertTrue(all(v['selection_status'] == 'winner' for v in native.values()))
        # Seven nearby issue dates often consume exactly the same prior cases.
        # Reusing by date alone used to repeat the entire audit unnecessarily.
        from unittest.mock import patch
        with patch('rainmapper_core.mushroom_competing_replay.audit.audit_rows',
                   side_effect=AssertionError('same cases must reuse native ranking')):
            self.assertIs(replay.prior(identity, issue + timedelta(days=1))[1], native)
        result = replay(identity, issue, 4)
        self.assertEqual(result, dict.fromkeys(comparison.METHODS, True))
        self.assertEqual({d for d,h in calls}, {issue+timedelta(days=i) for i in range(7)})
        self.assertTrue(all(d-timedelta(days=h) < issue for d,h in calls))
        initial_calls = len(calls)
        # Same complete inputs share the week even when the target label differs.
        with patch('rainmapper_core.mushroom_competing_replay.iter_species_week',
                   side_effect=AssertionError('identical week must be reused')):
            self.assertEqual(replay({k:peer[k] for k in identity}, issue, 4), result)
        self.assertEqual(len(calls), initial_calls)
        self.assertEqual(replay.stats['weeks_reused'], 1)
        for other in (changed_area, changed_model):
            self.assertEqual(replay({k:other[k] for k in identity}, issue, 4), result)
            self.assertGreater(len(calls), initial_calls)
            initial_calls = len(calls)
        replay(identity, issue, 3)
        self.assertGreater(len(calls), initial_calls)
        # Later labels and the target answer cannot alter the decision.
        replay.visits['s','target']['y'] = 0
        excluded = set(range(len(value['cases']))) - {c[0] for c in prior['cells']}
        self.assertEqual(len(excluded), 3)
        for index in excluded:
            case = value['cases'][index]
            value['cases'][index] = [*case[:2], 0, case[3]]
        for index, cell in enumerate(value['cells']):
            if cell[0] in excluded:
                value['cells'][index] = [*cell[:2], 1 - cell[2], *cell[3:]]
        replay.cache.clear()
        self.assertEqual(replay(identity, issue, 4), result)

    def test_sealed_scalar_evidence_copies_share_storage_and_cannot_mutate(self):
        from rainmapper_core.mushroom_competing_replay import SealedScalars
        value = SealedScalars({'score': .5, 'n': 12})
        self.assertIs(copy.deepcopy(value), value)
        with self.assertRaises(TypeError):
            value['score'] = 99
        with self.assertRaises(TypeError):
            value.update(score=99)
        with self.assertRaises(ValueError):
            SealedScalars({'mutable': []})

    def test_private_panel_cache_round_trip_bounded_and_missing_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = panels.Panels(Path(tmp) / 'panels.sqlite')
            self.addCleanup(cache.close)
            member = {'available': True, 'prediction': {'probability': .8123456789,
                      'applicability': {'status': 'caution'}}, 'features_used': {'significant_rain_found_90d': True}}
            cache.write('key', 's', 'o', [['2026-09-01', 7, member]])
            actual = cache.read('key', 's', 'o', date(2026, 9, 1), 7)
            self.assertEqual(actual['prediction'], member['prediction'])
            self.assertEqual(actual['metadata']['cutoff_date'], '2026-08-25')
            with self.assertRaises(comparison.MissingReplay):
                cache.read('key', 's', 'o', date(2026, 9, 2), 7)
            with self.assertRaisesRegex(ValueError, 'plan_limit'):
                panels.preflight([{'species_id':'s', 'temporal_contract_id':'lag_event_x'}] * 100,
                                 [{'species_id':'s'}] * 1000)

    def test_interleaved_packets_and_misses_are_cached_until_write(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            cache = panels.Panels(Path(tmp) / 'panels.sqlite')
            self.addCleanup(cache.close)
            day = date(2026, 9, 1)
            member = {'prediction': {'probability': .8, 'applicability': {'status': 'caution'}}}
            for i in range(64):
                cache.write(str(i), 's', 'o', [[day.isoformat(), 7, member]])
            with patch.object(cache, '_packet', wraps=cache._packet) as read:
                for _ in range(7):
                    for i in range(64):
                        self.assertEqual(cache.read(str(i), 's', 'o', day, 7)['prediction'], member['prediction'])
                self.assertEqual(read.call_count, 64)
                for _ in range(7):
                    with self.assertRaises(comparison.MissingReplay):
                        cache.read('missing', 's', 'o', day, 7)
                self.assertEqual(read.call_count, 65)
            cache.write('missing', 's', 'o', [[day.isoformat(), 7, member]])
            self.assertEqual(cache.read('missing', 's', 'o', day, 7)['prediction'], member['prediction'])
            self.assertLessEqual(cache.memo.size, cache.memo.max_bytes)

    def test_batch_write_rollback_preserves_previous_committed_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = panels.Panels(Path(tmp)/'panels.sqlite')
            self.addCleanup(cache.close)
            day = date(2026,9,1)
            member = {'prediction': {'probability': .8}}
            cache.write('old','s','o',[[day.isoformat(),7,member]])
            before = cache.read('old','s','o',day,7)
            with self.assertRaisesRegex(ValueError,'fixture failure'):
                with cache.db:
                    cache.write('old','s','o',[[day.isoformat(),7,{'prediction': {'probability': .1}}]],commit=False)
                    cache.write('new','s','o',[[day.isoformat(),7,member]],commit=False)
                    raise ValueError('fixture failure')
            self.assertEqual(cache.read('old','s','o',day,7),before)
            with self.assertRaises(comparison.MissingReplay):
                cache.read('new','s','o',day,7)


if __name__ == '__main__':
    unittest.main()
