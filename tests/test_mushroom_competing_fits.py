import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_competing_fits as fits
from rainmapper_core import mushroom_competing_history as history
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core.mushroom_ml_model_catalog import ModelArtifactRef
from tests import test_mushroom_competing_history as fixture
from tests.test_mushroom_competing_history import REF, sample


class FitReuseTests(unittest.TestCase):
    def test_migrated_panel_recipe_reads_only_reviewed_same_environment_fit(self):
        from rainmapper_core.mushroom_competing_panels import Panels, RequestedPanels
        ref = ModelArtifactRef.from_mapping(REF)
        bundle = {'kind': 'mushroom_ml_runtime_model', 'values': [1., 2.]}
        with tempfile.TemporaryDirectory() as tmp, history.UnitCache(Path(tmp)/'units.sqlite') as units:
            old = fits.Fits(units.db, 'before')
            old.write('original-fit-key', bundle, {})
            store = Panels(Path(tmp)/'panels.sqlite')
            self.addCleanup(store.close)
            store.save_fit('original-unit-key', ref, 'original-fit-key')
            recipe = store.fit('original-unit-key')
            with self.assertRaisesRegex(ValueError, 'cache_contract'):
                fits.Fits(units.db, 'after').read(recipe['fit_key'])
            current = fits.Fits(units.db, 'after', compatible_producers=('before',))
            requested = RequestedPanels(store, current, [], lambda: self.fail('unnecessary builder'))
            self.assertEqual(requested._model(recipe['fit_key']), bundle)
            self.assertEqual(current.stats['fits_reused'], 1)
            self.assertEqual(current.stats['fits_built'], 0)
            self.assertEqual(units.db.execute('SELECT count(*) FROM historical_fits').fetchone()[0], 1)
            # Approval of code identity never approves a different numerical environment.
            with patch.object(fits, 'version', return_value='different-library-version'):
                other = fits.Fits(units.db, 'after', compatible_producers=('before',))
            with self.assertRaisesRegex(ValueError, 'cache_contract'):
                other.read(recipe['fit_key'])

    def test_zstd_is_bounded_and_old_zlib_entries_remain_readable(self):
        import hashlib
        import pickle
        import zlib
        import pyarrow as pa
        with tempfile.TemporaryDirectory() as tmp, history.UnitCache(Path(tmp)/'units.sqlite') as units:
            cache = fits.Fits(units.db,'test')
            bundle = {'kind':'mushroom_ml_runtime_model','values':list(range(1000))}
            cache.write('model',bundle,{})
            packed = units.db.execute('SELECT payload FROM historical_fits').fetchone()[0]
            self.assertTrue(packed.startswith(b'RMF2'))
            raw = pa.decompress(packed[8:],int.from_bytes(packed[4:8],'big'),codec='zstd').to_pybytes()
            old = zlib.compress(raw,1)
            def replace(value):
                units.db.execute('UPDATE historical_fits SET payload=?,sha=?',
                    (value,hashlib.sha256(value).hexdigest()))
            replace(old)
            self.assertEqual(cache.read('model')['bundle'],bundle)
            replace(b'RMF2'+(fits.MAX_MODEL_BYTES+1).to_bytes(4,'big')+packed[8:])
            with patch.object(pickle,'loads',side_effect=AssertionError('must reject before unpickling')):
                with self.assertRaisesRegex(ValueError,'cache_size'):
                    cache.read('model')
            replace(packed+b'trailing')
            with self.assertRaisesRegex(ValueError,'cache_integrity'):
                cache.read('model')

    def test_cache_pressure_cannot_trigger_a_cartesian_week_rebuild(self):
        from types import SimpleNamespace
        benchmark = fixture.HistoryTests().benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        train,test,_ = history.partition(benchmark['samples'],2021)
        builder = SimpleNamespace(defer=lambda *args:False)
        with self.assertRaisesRegex(ValueError,'history_fit_cache_budget'):
            history.fit_temporal_unit(ref,benchmark,train,test,'key',panel_builder=builder,
                                      defer_panels=True)

    def test_large_numpy_protocol_five_buffers_persist_with_byte_limit(self):
        import numpy as np
        for array in (np.arange(40000).reshape(200,200),
                      np.asfortranarray(np.arange(40000).reshape(200,200))):
            with self.subTest(order='F' if array.flags.f_contiguous else 'C'), \
                    tempfile.TemporaryDirectory() as tmp, \
                    history.UnitCache(Path(tmp)/'units.sqlite') as units:
                cache = fits.Fits(units.db,'synthetic')
                bundle = {'kind':'mushroom_ml_runtime_model','preprocessor':array}
                cache.write('fits',bundle,{})
                self.assertTrue(cache.contains('fits'))
                np.testing.assert_array_equal(cache.read('fits')['bundle']['preprocessor'],array)
                self.assertEqual(cache.stats['fits_not_cached'],0)
                with patch.object(fits,'MAX_MODEL_BYTES',array.nbytes-1):
                    cache.write('too-large',bundle,{})
                self.assertFalse(cache.contains('too-large'))
                self.assertEqual(cache.stats['fits_not_cached'],1)

    def test_validation_and_fit_keys_share_rows_and_match_independent_legacy_keys(self):
        from dataclasses import replace
        benchmark = fixture.HistoryTests().benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        refs = [ref,replace(ref,estimator_id='random_forest_default')]
        train,test,_ = history.partition(benchmark['samples'],2021)
        with tempfile.TemporaryDirectory() as tmp, history.UnitCache(Path(tmp)/'units.sqlite') as units:
            cache = fits.Fits(units.db,'test')
            expected = [cache.key(r,benchmark,train) for r in refs]
            with patch.object(history,'_tensor_chunks',wraps=history._tensor_chunks) as tensors:
                sealed = cache.seal_unit_keys(refs,benchmark,train,test,implementation_ids=('current','old'))
                self.assertEqual(tensors.call_count,1)
                for r,key in zip(refs,expected):
                    self.assertEqual(cache.key(r,benchmark,train),key)
                self.assertEqual(tensors.call_count,1)
            self.assertEqual(sealed,history.unit_keys(refs,benchmark,train,test,
                                                     implementation_ids=('current','old')))
            edited = copy.deepcopy(train); edited[0]['predictive_features']['rain'] += 1
            self.assertNotEqual(cache.key(ref,benchmark,edited),expected[0])
            # Changing only evaluated observations keeps the exact fit identity.
            cache.seal_unit_keys(refs,benchmark,train,[],implementation_ids=('new',))
            self.assertEqual(cache.key(ref,benchmark,train),expected[0])

    def test_new_evaluation_rows_reuse_exact_fit_after_reopen_but_changed_training_does_not(self):
        benchmark = fixture.HistoryTests().benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        train, test, _ = history.partition(benchmark['samples'], 2021)
        extra = sample('new', '2021-09-02', 'unfavorable')
        extra['predictive_features']['rain'] = 25.
        expected = history.fit_temporal_unit(ref, benchmark, train, test + [extra], 'b'*64)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'units.sqlite'
            with patch.object(trainer, 'fit_artifact', wraps=trainer.fit_artifact) as fit:
                with history.UnitCache(path) as units:
                    cache = fits.Fits(units.db, 'current')
                    history.fit_temporal_unit(ref, benchmark, train, test, 'a'*64, fit_cache=cache)
                    key = cache.key(ref, benchmark, train)
                    self.assertEqual(fit.call_count, 1)
                with history.UnitCache(path) as units:
                    cache = fits.Fits(units.db, 'current')
                    with patch.object(trainer, '_prepare_fit_inputs', side_effect=AssertionError('duplicate preparation')):
                        actual = history.fit_temporal_unit(ref, benchmark, train, test + [extra], 'b'*64, fit_cache=cache)
                    self.assertEqual(actual, expected)
                    self.assertEqual(fit.call_count, 1)
                    self.assertEqual(cache.stats['fits_reused'], 1)
                    edited = copy.deepcopy(train)
                    edited[0]['predictive_features']['rain'] += 3
                    self.assertNotEqual(cache.key(ref, benchmark, edited), key)
                    history.fit_temporal_unit(ref, benchmark, edited, test, 'c'*64, fit_cache=cache)
                    self.assertEqual(fit.call_count, 2)
                    newer = fits.Fits(units.db, 'different-code')
                    self.assertIsNone(newer.read(newer.key(ref, benchmark, train)))

    def test_fit_budget_does_not_remove_units_and_corruption_is_rejected(self):
        benchmark = fixture.HistoryTests().benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        train, test, _ = history.partition(benchmark['samples'], 2021)
        with tempfile.TemporaryDirectory() as tmp, history.UnitCache(Path(tmp)/'units.sqlite') as units:
            units.put('completed', {'rows': []})
            cache = fits.Fits(units.db, 'current')
            with patch.object(fits, 'MAX_MODEL_BYTES', 1):
                actual = history.fit_temporal_unit(ref, benchmark, train, test, 'a'*64, fit_cache=cache)
            self.assertTrue(actual['rows'])
            self.assertEqual(cache.stats['fits_not_cached'], 1)
            self.assertEqual(units.read('completed'), {'rows': []})
            self.assertEqual(cache.used, 0)
            history.fit_temporal_unit(ref, benchmark, train, test, 'a'*64, fit_cache=cache)
            key = cache.key(ref, benchmark, train)
            with patch.object(fits, 'MAX_MODEL_BYTES', 1):
                with self.assertRaisesRegex(ValueError, 'cache_size'):
                    cache.read(key)
            units.db.execute('UPDATE historical_fits SET payload=?', (b'corrupt',))
            with self.assertRaisesRegex(ValueError, 'cache_integrity'):
                cache.read(key)

    def test_training_labels_and_shared_species_are_part_of_fit_identity(self):
        benchmark = fixture.HistoryTests().benchmark()
        ref = ModelArtifactRef.from_mapping(REF)
        train, _, _ = history.partition(benchmark['samples'], 2021)
        with tempfile.TemporaryDirectory() as tmp, history.UnitCache(Path(tmp)/'units.sqlite') as units:
            cache = fits.Fits(units.db, 'current')
            key = cache.key(ref, benchmark, train)
            edited = copy.deepcopy(train); edited[0]['prediction_target'] = 'unfavorable'
            self.assertNotEqual(cache.key(ref, benchmark, edited), key)
            edited = copy.deepcopy(train); edited[0]['metadata']['species_id'] = 'amanita_caesarea'
            self.assertNotEqual(cache.key(ref, benchmark, edited), key)
            edited = copy.deepcopy(train); edited[0]['metadata']['validation_group_14d'] = 'changed'
            self.assertNotEqual(cache.key(ref, benchmark, edited), key)

    def test_v6_shared_and_partial_reuse_fitted_preprocessing_and_tuning(self):
        from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
        from rainmapper_core import mushroom_ml_raw_weather as raw
        from rainmapper_core import mushroom_competing_tuning as tuning
        from rainmapper_core.mushroom_water_physics import WATER_STATE_CONTRACT_ID
        for estimator in ('smooth_shared_logistic_v1', 'smooth_partial_pooling_logistic_v1'):
            ref = ModelArtifactRef.from_mapping({**REF, 'species_id': 'all_species',
                'version_id': smooth.WINDOWED_VERSION_ID,
                'temporal_contract_id': 'fixed_gap_7d_biology_v6_smooth_hierarchical_v2',
                'profile_id': smooth.windowed_profile_id(raw.WINDOW_DAYS_OPTIONS[0]),
                'estimator_id': estimator})
            benchmark = {'feature_set': raw.feature_set_contract(raw.FIXED_CONTRACT_ID),
                         'water_state_contract_id': WATER_STATE_CONTRACT_ID}
            columns = trainer._columns(ref, benchmark)
            rows = [sample(str(i), f'2020-{i+1:02d}-20',
                           target='favorable' if i//2 % 2 else 'unfavorable',
                           sid='boletus_aereus' if i % 2 else 'amanita_caesarea') for i in range(10)]
            for i, row in enumerate(rows):
                row['predictive_features'] = {c: (i+1.)/20 for c in columns}
            train, test = rows[:8], rows[8:]
            benchmark['samples'] = rows
            expected = history.fit_temporal_unit(ref, benchmark, train, test, 'b'*64)
            with self.subTest(estimator=estimator), tempfile.TemporaryDirectory() as tmp, \
                    history.UnitCache(Path(tmp)/'units.sqlite') as units, \
                    patch.object(tuning, 'historical_v6_config', wraps=tuning.historical_v6_config) as tune, \
                    patch.object(trainer, 'fit_artifact', wraps=trainer.fit_artifact) as fit:
                cache = fits.Fits(units.db, 'current')
                history.fit_temporal_unit(ref, benchmark, train, test[:1], 'a'*64, fit_cache=cache)
                actual = history.fit_temporal_unit(ref, benchmark, train, test, 'b'*64, fit_cache=cache)
                self.assertEqual(actual, expected)
                self.assertEqual(fit.call_count, 1)
                self.assertEqual(tune.call_count, 1)


if __name__ == '__main__':
    unittest.main()
