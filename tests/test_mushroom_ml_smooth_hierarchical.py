from __future__ import annotations

import unittest

import numpy as np

from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth


class SmoothHierarchicalTests(unittest.TestCase):
    def test_basis_is_causal_normalized_and_smooth(self):
        basis = smooth.smooth_lag_basis()
        self.assertEqual(basis.shape, (365, 10))
        np.testing.assert_allclose(basis.sum(axis=0), np.ones(10), atol=1e-10)
        self.assertTrue(np.all(np.isfinite(basis)))
        self.assertLess(float(np.max(np.abs(np.diff(basis, axis=0)))), 0.4)

    def test_train_only_imputation_and_projection_shape(self):
        width = len(smooth.raw_columns(include_horizon=True))
        X_train = np.ones((3, width))
        X_train[:, 10] = [1.0, np.nan, 3.0]
        X_test = np.ones((1, width))
        X_test[:, 10] = 1000.0
        transformer = smooth.SmoothLagPreprocessor().fit(X_train)
        projected_width = (
            len(raw.DAILY_CHANNELS) * smooth.N_BASIS
            + len(raw.PHYSICAL_STATE_SCALARS)
            + 3
        )
        self.assertEqual(transformer.transform(X_train).shape, (3, projected_width))
        self.assertEqual(transformer.transform(X_test).shape, (1, projected_width))
        self.assertEqual(len(transformer.feature_names()), projected_width)
        self.assertEqual(float(transformer.imputer_.statistics_[10]), 2.0)

    def test_partial_pooling_design_contains_shared_and_species_deviations(self):
        Z = np.asarray([[1.0, 2.0], [3.0, 4.0]])
        design = smooth.pooled_design(
            Z, ["a", "b"], species_order=["a", "b"], deviation_scale=4.0
        )
        # two shared + one species intercept + two deviations per species
        self.assertEqual(design.shape, (2, 7))
        np.testing.assert_allclose(design[0, 3:5], Z[0] / 4.0)
        np.testing.assert_allclose(design[0, 5:7], 0.0)
        np.testing.assert_allclose(design[1, 3:5], 0.0)
        np.testing.assert_allclose(design[1, 5:7], Z[1] / 4.0)

    def test_unknown_holdout_species_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown hold-out species"):
            smooth.pooled_design(
                np.zeros((1, 2)), ["c"], species_order=["a", "b"], deviation_scale=None
            )


if __name__ == "__main__":
    unittest.main()
