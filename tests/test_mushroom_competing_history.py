import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_competing_history as h


def sample(oid, day, target='favorable', sid='boletus_aereus', site='one'):
    return {'sample_id': oid + '|7', 'prediction_target': target,
            'quality': {'training_eligible': True}, 'predictive_features': {'rain': 10.},
            'metadata': {'observation_id': oid, 'species_id': sid, 'target_date': day,
                         'horizon_days': 7, 'micro_area_id': site,
                         'validation_group_14d': oid}}


REF = {'batch_id': 'installed', 'generation_id': 'v3_installed', 'version_id': 'biology_v3',
       'temporal_contract_id': 'fixed_gap_7d_biology_v3', 'profile_id': 'core',
       'estimator_id': 'logistic_regression_reduced_v1', 'species_id': 'boletus_aereus'}


class HistoryTests(unittest.TestCase):
    def test_binary_producer_upgrade_reuses_units_without_legacy_week_expansion(self):
        benchmark = self.benchmark()
        def evaluate(ref, source, train, test, key):
            return {'rows': [[s['metadata']['species_id'], s['metadata']['observation_id'],
                s['metadata']['target_date'], s['metadata']['horizon_days'],
                int(s['prediction_target'] == 'favorable'), .5, .5,
                s['metadata']['validation_group_14d']] for s in test], 'missing': []}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'units.sqlite'
            def run(cache, code, **kwargs):
                return list(h.evaluate_benchmark(benchmark, [REF], cutoff='2026-10-05',
                    implementation_id=code, cache=cache, targets={'boletus_aereus'},
                    evaluate=evaluate, unit_context=lambda *args: 'unchanged-source-windows', **kwargs))
            with h.UnitCache(path) as cache:
                run(cache, 'legacy-json')
                old = run(cache, 'binary-before', fingerprint_rows=True)
            with h.UnitCache(path) as cache:
                with (patch.object(h, '_tensor_row', side_effect=AssertionError('legacy tensor expansion')),
                      patch.object(h, 'fit_temporal_unit', side_effect=AssertionError('duplicate fit'))):
                    migrated = run(cache, 'binary-after', fingerprint_rows=True,
                        compatible_row_implementation_ids=('binary-before',),
                        compatible_implementation_ids=('legacy-json',),
                        compatible_unit_context=lambda *args: self.fail('legacy full-week expansion'))
                self.assertEqual(len(migrated), 3)
                self.assertTrue(all(u['reused'] for u in migrated))
                self.assertEqual([u['unit_key'] for u in old], [u['unit_key'] for u in migrated])
                # Aliases survive reopening; no compatibility probes are needed again.
            with h.UnitCache(path) as cache:
                again = run(cache, 'binary-after', fingerprint_rows=True)
                self.assertTrue(all(u['reused'] for u in again))
                self.assertEqual([u['unit_key'] for u in old], [u['unit_key'] for u in again])
                unreviewed = run(cache, 'unreviewed', fingerprint_rows=True)
                self.assertTrue(all(not u['reused'] for u in unreviewed))
                benchmark['samples'][0]['predictive_features']['rain'] += 1
                changed = run(cache, 'binary-after', fingerprint_rows=True,
                              compatible_row_implementation_ids=('binary-before',))
                self.assertTrue(all(not u['reused'] for u in changed))

    def test_binary_migration_checks_current_source_context_and_labels(self):
        for changed in ('context', 'label'):
            with self.subTest(changed=changed), h.UnitCache(':memory:') as cache:
                benchmark = self.benchmark()
                def run(code, context, **kwargs):
                    return list(h.evaluate_benchmark(benchmark, [REF], cutoff='2026-10-05',
                        implementation_id=code, cache=cache, targets={'boletus_aereus'},
                        fingerprint_rows=True, unit_context=lambda *args: context,
                        evaluate=lambda *args: {'rows': [], 'missing': []}, **kwargs))
                run('before', 'original')
                if changed == 'label': benchmark['samples'][0]['prediction_target'] = 'unfavorable'
                current = run('after', 'changed' if changed == 'context' else 'original',
                              compatible_row_implementation_ids=('before',))
                self.assertTrue(all(not u['reused'] for u in current if u['year'] >= 2021))

    def test_interrupted_fresh_cache_never_probes_absent_legacy_producers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'units.sqlite'
            with h.UnitCache(path) as cache:
                self.assertEqual(cache.compatible_producers('current', ('legacy',)), ())
                cache.put('partial', {'rows': []})
            with h.UnitCache(path) as cache:
                self.assertFalse(cache.prepared('current'))
                self.assertEqual(cache.compatible_producers('current', ('legacy',)), ())
                self.assertEqual(cache.compatible_producers('next', ('current',)), ('current',))
            with h.UnitCache(Path(tmp)/'legacy.sqlite') as cache:
                cache.put('untracked', {'rows': []})
                self.assertEqual(cache.compatible_producers('new', ('legacy',)), ('legacy',))

    def test_binary_rows_preserve_every_float_bit_null_and_identity(self):
        import math
        import numpy as np
        from rainmapper_core.mushroom_ml_benchmark_io import ColumnarFeatures
        row = sample('one', '2025-09-01')
        row['predictive_features'] = {'rain': None, 'other': -0.0, 'precise': 1.123456789123}
        columns = ['precise', 'rain', 'other']
        expected = h._binary_tensor_row(columns, row)
        values = np.asarray([[float('nan'), -0., 1.123456789123]])
        valid = np.asarray([[False, True, True]])
        columnar = ColumnarFeatures({'rain':0,'other':1,'precise':2},values,valid,0,frozenset(),{})
        self.assertEqual(h._binary_tensor_row(columns,{**row,'predictive_features':columnar}), expected)
        for name, value in [('rain', 0.), ('other', 0.),
                            ('precise', math.nextafter(1.123456789123, math.inf))]:
            changed = copy.deepcopy(row); changed['predictive_features'][name] = value
            self.assertNotEqual(h._binary_tensor_row(columns,changed),expected)
        for value in (float('nan'), float('inf')):
            changed = copy.deepcopy(row); changed['predictive_features']['rain'] = value
            with self.assertRaisesRegex(ValueError, 'nonfinite'):
                h._binary_tensor_row(columns,changed)
        with self.assertRaisesRegex(ValueError, 'missing_history_feature'):
            h._binary_tensor_row([*columns,'absent'],row)
        changed = copy.deepcopy(row); changed['metadata']['observer'] = 'irrelevant'
        self.assertEqual(h._binary_tensor_row(columns,changed),expected)
        changed['prediction_target'] = 'unfavorable'
        self.assertNotEqual(h._binary_tensor_row(columns,changed),expected)

    def test_row_digests_reuse_serialization_without_losing_changed_inputs(self):
        from rainmapper_core.mushroom_ml_model_catalog import ModelArtifactRef
        benchmark = self.benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        memo = h.RowFingerprints(['rain'])
        values = []
        with patch.object(h,'_binary_tensor_row',wraps=h._binary_tensor_row) as encode:
            for year in (2021,2022):
                train,test,_ = h.partition(benchmark['samples'],year)
                result = h.unit_keys([ref],benchmark,train,test,implementation_ids=('new',),row_fingerprints=memo)
                value = result[tuple(ref.as_dict()[k] for k in h.FAMILY_FIELDS)]['new']
                self.assertEqual(value,h.unit_key(ref,benchmark,train,test,
                    implementation_id='new',row_fingerprints=memo))
                values.append(value)
            self.assertEqual(encode.call_count,4)
        train,test,_ = h.partition(benchmark['samples'],2022)
        benchmark['samples'][0]['predictive_features']['rain'] += 1
        # A new invocation starts a fresh identity cache for its immutable rows.
        self.assertNotEqual(values[-1],h.unit_key(ref,benchmark,train,test,
            implementation_id='new',row_fingerprints=h.RowFingerprints(['rain'])))
        self.assertNotEqual(values[0],values[1])

    def test_new_row_keys_can_read_reviewed_legacy_units_only_with_exact_tensors(self):
        benchmark = self.benchmark()
        with tempfile.TemporaryDirectory() as tmp, h.UnitCache(Path(tmp)/'units.sqlite') as cache:
            def run(code,**kwargs):
                return list(h.evaluate_benchmark(benchmark,[REF],cutoff='2026-10-05',
                    implementation_id=code,cache=cache,targets={'boletus_aereus'},
                    evaluate=lambda *args:{'rows':[],'missing':[]},**kwargs))
            old = run('reviewed')
            migrated = run('current',compatible_implementation_ids=('reviewed',),fingerprint_rows=True)
            self.assertTrue(all(unit['reused'] for unit in migrated))
            self.assertEqual([u['unit_key'] for u in old],[u['unit_key'] for u in migrated])
            self.assertFalse(cache.prepared('current'))
            cache.mark_prepared('current')
            self.assertTrue(cache.prepared('current'))
            self.assertFalse(cache.prepared('different-code'))
            # Original unit keys are retained for persisted weekly panels;
            # the exact new key resolves without any legacy probe or tensor.
            with patch.object(cache,'has_test_scope',side_effect=AssertionError('legacy rescan')):
                again = run('current',fingerprint_rows=True)
            self.assertTrue(all(unit['reused'] for unit in again))
            self.assertEqual([u['unit_key'] for u in old],[u['unit_key'] for u in again])
            benchmark['samples'][0]['predictive_features']['rain'] += 1
            changed = run('current',compatible_implementation_ids=('reviewed',),fingerprint_rows=True)
            self.assertTrue(all(not unit['reused'] for unit in changed))

    def test_new_population_hashes_only_current_producer_and_shares_scoped_work(self):
        refs = [REF, {**REF, 'estimator_id': 'random_forest_default'}]
        benchmark = self.benchmark()
        with (tempfile.TemporaryDirectory() as tmp,
              h.UnitCache(Path(tmp)/'cache.sqlite') as cache,
              patch.object(cache, 'has_test_scope', return_value=False) as probe,
              patch.object(h, 'unit_keys', wraps=h.unit_keys) as keys):
            def old_context(*args):
                self.fail('New evaluation populations cannot match legacy units')
            units = list(h.evaluate_benchmark(benchmark, refs, cutoff='2026-10-05',
                implementation_id='current', targets={'boletus_aereus'}, cache=cache,
                compatible_implementation_ids=('old-one', 'old-two'),
                unit_context=lambda *args: 'current-inputs', compatible_unit_context=old_context,
                evaluate=lambda *args: {'rows': [], 'missing': []}))
        self.assertEqual(len(units), 6)
        self.assertEqual(probe.call_count, 0)
        self.assertEqual(keys.call_count, 3)
        self.assertTrue(all(call.kwargs['implementation_ids'] == ('current',)
                            for call in keys.call_args_list))

    def test_key_batch_serializes_each_row_once_and_preserves_every_legacy_key(self):
        from dataclasses import replace
        from rainmapper_core.mushroom_ml_model_catalog import ModelArtifactRef
        benchmark = self.benchmark()
        reference = ModelArtifactRef.from_mapping(REF)
        references = [reference, replace(reference, estimator_id='random_forest_default')]
        train, test, _ = h.partition(benchmark['samples'], 2021)
        versions = ('current', 'reviewed-one', 'reviewed-two')
        expected = {tuple(ref.as_dict()[k] for k in h.FAMILY_FIELDS): {
            version: h.unit_key(ref, benchmark, train, test, implementation_id=version)
            for version in versions} for ref in references}
        with patch.object(h, '_tensor_chunks', wraps=h._tensor_chunks) as tensors:
            actual = h.unit_keys(references, benchmark, train, test, implementation_ids=versions)
        self.assertEqual(actual, expected)
        self.assertEqual(tensors.call_count, 1)
        with self.assertRaisesRegex(ValueError, 'batch_scope'):
            h.unit_keys([reference, replace(reference, species_id='amanita_caesarea')],
                        benchmark, train, test, implementation_ids=versions)

    def test_tensor_reuse_preserves_legacy_keys_for_each_estimator_and_revision(self):
        from dataclasses import replace
        from rainmapper_core.mushroom_ml_model_catalog import ModelArtifactRef
        benchmark = self.benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        train, test, _ = h.partition(benchmark['samples'], 2021)
        cache = {}
        for estimator in (ref.estimator_id, 'random_forest_default'):
            for revision in ('new', 'reviewed-old'):
                candidate = replace(ref, estimator_id=estimator)
                expected = h.unit_key(candidate, benchmark, train, test, implementation_id=revision)
                actual = h.unit_key(candidate, benchmark, train, test, implementation_id=revision,
                                    tensor_cache=cache)
                self.assertEqual(actual, expected)
        # A new tensor must be validated and hashed, never served by identity
        # from another invocation (the memo lives within an immutable benchmark).
        edited = copy.deepcopy(train)
        edited[0]['predictive_features']['rain'] += 1
        changed = h.unit_key(ref, benchmark, edited, test, implementation_id='new', tensor_cache=cache)
        self.assertNotEqual(changed, h.unit_key(ref, benchmark, train, test, implementation_id='new'))

    def test_fit_preparation_is_shared_by_estimators_but_not_changed_rows(self):
        from rainmapper_core.mushroom_ml_model_catalog import ModelArtifactRef
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        benchmark = self.benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        train, test, _ = h.partition(benchmark['samples'], 2021)
        cache = {}
        with patch.object(trainer, '_prepare_fit_inputs', wraps=trainer._prepare_fit_inputs) as prepare:
            a = h.fit_temporal_unit(ref, benchmark, train, test, 'a'*64, prepared_cache=cache)
            b = h.fit_temporal_unit(ref, benchmark, list(train), test, 'b'*64, prepared_cache=cache)
            self.assertEqual(a['rows'], b['rows'])
            self.assertEqual(prepare.call_count, 1)
            edited = copy.deepcopy(train)
            edited[0]['predictive_features']['rain'] += 1
            h.fit_temporal_unit(ref, benchmark, edited, test, 'c'*64, prepared_cache=cache)
            self.assertEqual(prepare.call_count, 2)

    def test_unusable_and_boundary_cases_have_explicit_reasons_even_without_a_fit(self):
        benchmark = self.benchmark()
        excluded = sample('not_eligible','2023-06-01')
        excluded['quality']['training_eligible'] = False
        benchmark['samples'] += [excluded, sample('boundary','2024-01-05')]
        with tempfile.TemporaryDirectory() as tmp, h.UnitCache(Path(tmp)/'cache.sqlite') as cache:
            units = self.run_history(benchmark,cache,lambda *a:{'rows':[],'missing':[]})
        reasons = {row[1]:row[3] for unit in units for row in unit['missing']}
        self.assertEqual(reasons['not_eligible'],'not_eligible_for_profile')
        self.assertEqual(reasons['boundary'],'temporal_episode_boundary')

    def test_actual_validation_fit_uses_past_rows_and_keeps_initial_case_visible(self):
        from rainmapper_core.mushroom_ml_model_catalog import ModelArtifactRef
        benchmark = self.benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        train, test, _ = h.partition(benchmark['samples'], 2021)
        value = h.fit_temporal_unit(ref, benchmark, train, test, 'a'*64)
        self.assertEqual(len(value['rows']), 1)
        self.assertEqual(value['rows'][0][1], 'a')
        self.assertEqual(value['rows'][0][6], .5)
        first = h.fit_temporal_unit(ref, benchmark, [], train, 'b'*64)
        self.assertEqual(first['rows'], [])
        self.assertEqual(len(first['missing']), 2)

    def benchmark(self):
        return {'feature_set': {'predictive_feature_cols': ['rain']}, 'samples': [
            sample('old1', '2020-05-01'), sample('old2', '2020-10-01', 'unfavorable'),
            sample('a', '2021-06-01'), sample('b', '2022-06-01', 'unfavorable')]}

    def run_history(self, benchmark, cache, evaluate, progress=lambda event: None):
        return list(h.evaluate_benchmark(benchmark, [REF], cutoff='2026-10-05',
                    implementation_id='checked-code-hash', targets={'boletus_aereus'},
                    cache=cache, evaluate=evaluate, progress=progress))

    def test_purge_shared_site_episodes_and_all_horizons(self):
        rows = [sample('past', '2024-10-01'), sample('near', '2024-12-24'),
                sample('other_species', '2025-01-05', sid='amanita_caesarea'),
                sample('chained', '2025-01-18'), sample('ok', '2025-06-01')]
        train, test, purged = h.partition(rows, 2025)
        self.assertEqual([r['metadata']['observation_id'] for r in train], ['past'])
        self.assertEqual([r['metadata']['observation_id'] for r in test], ['ok'])
        self.assertEqual(len(purged), 2)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            h.partition(rows + [rows[0]], 2025)

    def test_reused_partition_plan_keeps_purge_across_sites_species_and_years(self):
        rows = [sample('far-past','2022-06-01',site='other'),
                sample('before','2024-12-18'), sample('boundary','2025-01-02'),
                sample('chained','2025-01-16',sid='amanita_caesarea'),
                sample('separate','2025-06-01'), sample('next','2026-06-01')]
        # A validation group can span distant dates and distinct sites.
        rows[0]['metadata']['validation_group_14d'] = 'shared'
        rows[-1]['metadata']['validation_group_14d'] = 'shared'
        plan = h.PartitionPlan(list(reversed(rows)))
        train,test,excluded = plan.for_year(2025)
        self.assertEqual(train,[])
        self.assertEqual([r['metadata']['observation_id'] for r in test],['separate'])
        self.assertEqual({r['metadata']['observation_id'] for r in excluded},{'boundary','chained'})
        train,test,excluded = plan.for_year(2026)
        self.assertEqual({r['metadata']['observation_id'] for r in train},
                         {'before','boundary','chained','separate'})
        self.assertEqual(test,[])
        self.assertEqual([r['metadata']['observation_id'] for r in excluded],['next'])

    def test_new_case_reuses_past_years_and_correction_invalidates_later_training(self):
        calls = []
        def evaluate(ref, bench, train, test, key):
            calls.append(key)
            self.assertLess(max((s['metadata']['target_date'] for s in train), default=''),
                            min(s['metadata']['target_date'] for s in test))
            return {'rows': [], 'missing': [], 'fit_config': {}}
        with tempfile.TemporaryDirectory() as tmp, h.UnitCache(Path(tmp) / 'cache.sqlite') as cache:
            benchmark = self.benchmark()
            original = self.run_history(benchmark, cache, evaluate)
            self.assertEqual(len(calls), 3)
            unchanged = self.run_history(benchmark, cache, evaluate)
            self.assertTrue(all(r['reused'] for r in unchanged))
            benchmark['samples'].append(sample('new', '2026-09-01'))
            newer = self.run_history(benchmark, cache, evaluate)
            self.assertEqual(len(calls), 4)
            self.assertEqual([r['unit_key'] for r in newer[:3]], [r['unit_key'] for r in original])
            benchmark['samples'][0]['prediction_target'] = 'unfavorable'
            corrected = self.run_history(benchmark, cache, evaluate)
            self.assertTrue(all(not r['reused'] for r in corrected))
            self.assertEqual(len(calls), 8)

    def test_only_consumed_features_invalidate_and_order_is_stable(self):
        evaluate = lambda *args: {'rows': [], 'missing': [], 'fit_config': {}}
        with tempfile.TemporaryDirectory() as tmp, h.UnitCache(Path(tmp) / 'cache.sqlite') as cache:
            benchmark = self.benchmark()
            a = self.run_history(benchmark, cache, evaluate)
            for row in benchmark['samples']:
                row['metadata']['observer'] = 'changed private metadata'
                row['predictive_features']['unused_new_rain'] = 200
            benchmark['samples'].reverse()
            b = self.run_history(benchmark, cache, evaluate)
            self.assertEqual([r['unit_key'] for r in a], [r['unit_key'] for r in b])
            self.assertTrue(all(r['reused'] for r in b))
            benchmark['samples'][-1]['predictive_features']['rain'] = 99.
            c = self.run_history(benchmark, cache, evaluate)
            self.assertTrue(all(not r['reused'] for r in c))

    def test_species_changes_reuse_independent_families_and_invalidate_shared_dependencies(self):
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        sid = 'lactarius_deliciosus'
        refs = [REF, {**REF, 'species_id': sid},
                {**REF, 'species_id': 'all_species', 'version_id': 'biology_v6_smooth_hierarchical',
                 'temporal_contract_id': 'fixed_gap_7d_biology_v6_smooth_hierarchical_v2',
                 'profile_id': 'smooth_weather_physical_state', 'estimator_id': 'smooth_shared_logistic_v1'}]
        benchmark = self.benchmark()
        benchmark['samples'] += [sample('d-'+row['metadata']['observation_id'],
                                      row['metadata']['target_date'], row['prediction_target'], sid=sid,
                                      site='deliciosus-site') for row in list(benchmark['samples'])]
        def evaluate(*args):
            return {'rows': [], 'missing': [], 'fit_config': {}}
        with (tempfile.TemporaryDirectory() as tmp, h.UnitCache(Path(tmp)/'cache.sqlite') as cache,
              patch.object(trainer, '_columns', return_value=['rain'])):
            def run():
                return list(h.evaluate_benchmark(benchmark, refs, cutoff='2026-10-05',
                            implementation_id='synthetic', targets={'boletus_aereus', sid},
                            cache=cache, evaluate=evaluate))
            self.assertEqual(len(run()), 9)
            benchmark['samples'].append(sample('new-deliciosus', '2022-09-01', sid=sid,
                                               site='deliciosus-site'))
            changed = run()
            self.assertEqual({(unit['family']['species_id'], unit['year']) for unit in changed
                              if not unit['reused']}, {(sid, 2022), ('all_species', 2022)})
            # A correction in past training also affects later shared fits,
            # while independent aereus fits remain reusable.
            benchmark['samples'][4]['predictive_features']['rain'] = 99.
            corrected = run()
            self.assertEqual({(unit['family']['species_id'], unit['year']) for unit in corrected
                              if not unit['reused']},
                             {(species, year) for species in (sid, 'all_species') for year in (2020,2021,2022)})

    def test_cancelled_unit_is_not_committed_and_previous_units_survive(self):
        with tempfile.TemporaryDirectory() as tmp, h.UnitCache(Path(tmp) / 'cache.sqlite') as cache:
            cache.put('previous', {'rows': []})
            def progress(event):
                if event['phase'] == 'Saving historical validation':
                    raise RuntimeError('cancelled')
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                self.run_history(self.benchmark(), cache, lambda *a: {'rows': []}, progress)
            self.assertEqual(cache.read('previous'), {'rows': []})
            self.assertEqual(cache.db.execute('SELECT count(*) FROM units').fetchone()[0], 1)

    def test_cache_integrity_and_resource_limit_fail_before_fit(self):
        with tempfile.TemporaryDirectory() as tmp, h.UnitCache(Path(tmp) / 'cache.sqlite') as cache:
            cache.put('bad', {'rows': []})
            cache.db.execute('UPDATE units SET payload=? WHERE key=?', (b'{}', 'bad'))
            with self.assertRaisesRegex(ValueError, 'integrity'):
                cache.read('bad')
            with patch.object(h, 'MAX_MATRIX_BYTES', 1), patch.object(h, 'fit_temporal_unit') as fit:
                with self.assertRaisesRegex(ValueError, 'matrix_limit'):
                    self.run_history(self.benchmark(), cache, fit)
                fit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
