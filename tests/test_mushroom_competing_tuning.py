import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from rainmapper_core import mushroom_competing_tuning as tuning
from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth


class TuningTests(unittest.TestCase):
    def test_compact_design_preserves_every_column_without_dense_species_blocks(self):
        rng = np.random.default_rng(58)
        for n,p in ((1,3),(20,12),(300,40)):
            values = rng.normal(size=(n,p)); values[values<.3] = 0.
            species = ['abc'[i%3] for i in range(n)]
            for scale in (None,2.,4.,8.):
                expected = smooth.pooled_design(values,species,species_order=list('abc'),deviation_scale=scale)
                actual = tuning.compact_pooled_design(values,species,species_order=list('abc'),deviation_scale=scale)
                np.testing.assert_array_equal(actual.toarray(),expected)
        with self.assertRaisesRegex(ValueError,'unknown hold-out species'):
            tuning.compact_pooled_design(np.ones((1,2)),['new'],species_order=['a'],deviation_scale=4.)

    def test_compact_tuning_preserves_decision_and_diagnostics(self):
        from concurrent.futures import ThreadPoolExecutor
        class IdentityPreprocessor:
            def fit(self, values): return self
            def transform(self, values): return values
        for partial in (False,True):
            results = []
            for compact in (False,True):
                audit = {}
                with (patch.object(holdout,'_inner_splits',return_value=[(list(range(4)),[4,5])]),
                      patch.object(smooth,'SmoothLagPreprocessor',IdentityPreprocessor)):
                    choice = tuning.historical_v6_config(self.reference(partial),self.prepared(),
                                                         compact=compact,diagnostics=audit)
                results.append((choice,audit))
            self.assertEqual(results[0],results[1])
            audit = {}
            with (ThreadPoolExecutor(max_workers=4) as executor,
                  patch.object(holdout,'_inner_splits',return_value=[(list(range(4)),[4,5])]),
                  patch.object(smooth,'SmoothLagPreprocessor',IdentityPreprocessor)):
                parallel = tuning.historical_v6_config(self.reference(partial),self.prepared(),
                    compact=True,diagnostics=audit,executor=executor)
            self.assertEqual((parallel,audit),results[1])

    def test_parallel_v5_preserves_choices_for_both_estimators(self):
        from concurrent.futures import ThreadPoolExecutor
        rng = np.random.default_rng(87)
        X = rng.normal(size=(160,12)); X[1:4,1] = np.nan
        y = (np.nan_to_num(X[:,0]) + .3*X[:,4] > 0).astype(int)
        samples = [{'prediction_target':'favorable' if value else 'unfavorable','metadata':{
            'validation_group_14d':str(i//4), 'target_date':f'2024-{1+i//16:02d}-01'}}
            for i,value in enumerate(y)]
        columns = [f'rain__lag_{i}' for i in range(12)]
        for estimator in holdout.V5_ESTIMATORS:
            serial = holdout._select_v5(estimator,samples,X,y,columns,14)
            with ThreadPoolExecutor(max_workers=4) as executor:
                parallel = holdout._select_v5(estimator,samples,X,y,columns,14,executor=executor)
            self.assertEqual(serial,parallel)

    def test_regularization_values_share_design_without_skipping_any_candidate(self):
        class IdentityPreprocessor:
            def fit(self, values):
                return self
            def transform(self, values):
                return values
        for partial in (False, True):
            with (self.subTest(partial=partial),
                patch.object(holdout, '_inner_splits', return_value=[(list(range(4)), [4, 5])]),
                patch.object(smooth, 'SmoothLagPreprocessor', IdentityPreprocessor),
                patch.object(smooth, 'pooled_design', wraps=smooth.pooled_design) as design,
                patch.object(smooth, 'fit_logistic', wraps=smooth.fit_logistic) as fit
            ):
                tuning.historical_v6_config(self.reference(partial), self.prepared())
                self.assertEqual(design.call_count, 6 if partial else 2)
                self.assertEqual(fit.call_count, 9 if partial else 3)
                calls = fit.call_args_list
                for offset in range(0, len(calls), 3):
                    self.assertEqual([c.kwargs['C'] for c in calls[offset:offset+3]], [.01, .1, 1.])
                    self.assertTrue(all(c.args[0] is calls[offset].args[0] for c in calls[offset:offset+3]))

    def prepared(self):
        return {'X': np.arange(16, dtype=float).reshape(8, 2) / 10,
                'y': np.array([0, 1, 0, 1, 1, 0, 1, 0]),
                'samples': [{'metadata': {'species_id': sid}} for sid in
                            ['early_a', 'early_b', 'early_a', 'early_b',
                             'early_a', 'early_b', 'late_c', 'late_c']]}

    def reference(self, partial):
        return SimpleNamespace(profile_id='smooth_weather_physical_state',
                               estimator_id=('smooth_partial_pooling_logistic_v1' if partial
                                             else 'smooth_shared_logistic_v1'))

    def test_all_inner_validation_species_unseen_uses_default_without_fitting(self):
        for partial in (False, True):
            with self.subTest(partial=partial):
                audit = {}
                with (patch.object(holdout, '_inner_splits', return_value=[(list(range(4)), [6, 7])]),
                      patch.object(smooth, 'SmoothLagPreprocessor') as preprocess,
                      patch.object(smooth, 'fit_logistic') as fit):
                    config = tuning.historical_v6_config(self.reference(partial), self.prepared(),
                                                         diagnostics=audit)
                self.assertEqual(config, {'C': .1, 'deviation_scale': 4. if partial else None})
                self.assertEqual(audit, {'inner_splits': 1, 'used_inner_splits': 0,
                    'unsupported_validation_occurrences_by_species': {'late_c': 2}, 'default_used': True})
                preprocess.assert_not_called()
                fit.assert_not_called()

    def test_unseen_species_cannot_change_tuning_or_enter_inner_preprocessing(self):
        fitted = []

        class IdentityPreprocessor:
            def fit(self, values):
                fitted.append(values.copy())
            def transform(self, values):
                return values

        prepared = self.prepared()
        changed = copy.deepcopy(prepared)
        changed['X'][6:] = 1e9
        changed['y'][6:] = 1 - changed['y'][6:]
        for partial in (False, True):
            with self.subTest(partial=partial):
                results = []
                for values, validation in ((prepared, [4, 5, 6, 7]),
                                           (changed, [4, 5, 6, 7]), (prepared, [4, 5])):
                    audit = {}
                    with (patch.object(holdout, '_inner_splits', return_value=[(list(range(4)), validation)]),
                          patch.object(smooth, 'SmoothLagPreprocessor', IdentityPreprocessor)):
                        results.append(tuning.historical_v6_config(self.reference(partial), values,
                                                                   diagnostics=audit))
                    self.assertEqual(audit['used_inner_splits'], 1)
                    self.assertFalse(audit['default_used'])
                    self.assertEqual(audit['unsupported_validation_occurrences_by_species'],
                                     {'late_c': 2} if len(validation) == 4 else {})
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])
        self.assertEqual(len(fitted), 6)
        for values in fitted:
            np.testing.assert_array_equal(values, prepared['X'][:4])


if __name__ == '__main__':
    unittest.main()
