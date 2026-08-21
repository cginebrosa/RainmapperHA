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

    def test_windowed_profile_id_round_trips(self):
        for window_days in raw.WINDOW_DAYS_OPTIONS:
            profile_id = smooth.windowed_profile_id(window_days)
            self.assertEqual(smooth.window_days_from_profile_id(profile_id), window_days)
        self.assertIsNone(
            smooth.window_days_from_profile_id("smooth_weather_physical_state")
        )

    def test_windowed_basis_and_columns_use_raw_channels_only(self):
        for window_days in raw.WINDOW_DAYS_OPTIONS:
            basis = smooth.smooth_lag_basis(window_days=window_days)
            self.assertEqual(basis.shape, (window_days, smooth.N_BASIS))
            np.testing.assert_allclose(
                basis.sum(axis=0), np.ones(smooth.N_BASIS), atol=1e-10
            )
            columns = smooth.raw_columns(
                include_horizon=True,
                channels=raw.RAW_CHANNELS,
                window_days=window_days,
            )
            for channel in raw.RAW_CHANNELS:
                self.assertIn(f"{channel}__lag_{window_days - 1:03d}", columns)
                self.assertNotIn(f"{channel}__lag_{window_days:03d}", columns)
            for channel in raw.PHYSICAL_CHANNELS + raw.STATE_CHANNELS:
                self.assertNotIn(f"{channel}__lag_000", columns)

    def test_windowed_preprocessor_matches_windowed_columns_shape(self):
        window_days = 30
        columns = smooth.raw_columns(
            include_horizon=True, channels=raw.RAW_CHANNELS, window_days=window_days
        )
        X = np.ones((4, len(columns)))
        preprocessor = smooth.SmoothLagPreprocessor(
            channels=raw.RAW_CHANNELS, window_days=window_days
        ).fit(X)
        projected_width = (
            len(raw.RAW_CHANNELS) * smooth.N_BASIS + len(raw.PHYSICAL_STATE_SCALARS) + 3
        )
        self.assertEqual(preprocessor.transform(X).shape, (4, projected_width))
        self.assertEqual(len(preprocessor.feature_names()), projected_width)

    def test_default_preprocessor_behaviour_is_unchanged(self):
        """The retired (status=reference) 365-day profile must keep fitting
        identically to before these windowed variants were added."""
        width = len(smooth.raw_columns(include_horizon=True))
        X = np.ones((3, width))
        preprocessor = smooth.SmoothLagPreprocessor().fit(X)
        self.assertEqual(preprocessor.channels, raw.DAILY_CHANNELS)
        self.assertEqual(preprocessor.window_days, raw.LOOKBACK_DAYS)


if __name__ == "__main__":
    unittest.main()
