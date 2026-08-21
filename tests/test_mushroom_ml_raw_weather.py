from __future__ import annotations

import unittest
from datetime import date, timedelta

from rainmapper_core import mushroom_ml_raw_weather as raw


class RawWeatherContractTests(unittest.TestCase):
    def series(self):
        start = date(2025, 1, 1)
        result = {"daily_dates": [(start + timedelta(days=index)).isoformat() for index in range(365)]}
        for channel, key in raw.AREA_SERIES_KEYS.items():
            result[key] = [float(index) for index in range(365)]
        for index, name in enumerate(raw.PHYSICAL_STATE_SCALARS):
            result[name] = index / 10.0
        return result

    def test_lag_zero_is_cutoff_and_lag_364_is_oldest(self):
        features = raw.build_raw_features(
            self.series(),
            target_date=date(2026, 1, 1),
            horizon_days=7,
            temporal_contract_id=raw.FIXED_CONTRACT_ID,
        )
        self.assertEqual(features["rain_mm__lag_000"], 364.0)
        self.assertEqual(features["rain_mm__lag_364"], 0.0)

    def test_lag_contract_keeps_horizon(self):
        features = raw.build_raw_features(
            self.series(),
            target_date=date(2026, 1, 1),
            horizon_days=3,
            temporal_contract_id=raw.LAG_CONTRACT_ID,
        )
        self.assertEqual(features["horizon_days"], 3.0)

    def test_non_consecutive_dates_are_rejected(self):
        series = self.series()
        series["daily_dates"][100] = "2030-01-01"
        with self.assertRaisesRegex(ValueError, "consecutive"):
            raw.build_raw_features(
                series,
                target_date=date(2026, 1, 1),
                horizon_days=7,
                temporal_contract_id=raw.FIXED_CONTRACT_ID,
            )

    def test_quality_columns_are_not_predictive(self):
        contract = raw.feature_set_contract(raw.FIXED_CONTRACT_ID)
        for columns in contract["profiles"].values():
            self.assertFalse(any("coverage" in value or "area_id" in value for value in columns))

    def test_no_calendar_profiles_remove_only_phenology_controls(self):
        profiles = raw.feature_set_contract(raw.LAG_CONTRACT_ID)["profiles"]
        self.assertNotIn("target_day_sin", profiles["raw_primary_no_calendar"])
        self.assertNotIn("target_day_cos", profiles["raw_primary_no_calendar"])
        self.assertIn("horizon_days", profiles["raw_primary_no_calendar"])
        self.assertEqual(
            set(profiles["raw_primary"]) - set(profiles["raw_primary_no_calendar"]),
            {"target_day_sin", "target_day_cos"},
        )

    def test_canonical_profile_contains_idw_physical_and_soil_state(self):
        profiles = raw.feature_set_contract(raw.FIXED_CONTRACT_ID)["profiles"]
        columns = profiles["raw_primary_plus_physical_state"]
        for channel in raw.DAILY_CHANNELS:
            self.assertIn(raw.lag_feature_name(channel, 0), columns)
        for name in raw.PHYSICAL_STATE_SCALARS:
            self.assertIn(name, columns)
        self.assertIn("target_day_sin", columns)

    def test_missing_idw_and_state_values_never_become_zero(self):
        series = self.series()
        series[raw.AREA_SERIES_KEYS["rain_mm"]][-1] = None
        series[raw.AREA_SERIES_KEYS["soil_water_fraction"]][-1] = None
        series["soil_water_area_mean_at_cutoff"] = None
        features = raw.build_raw_features(
            series,
            target_date=date(2026, 1, 1),
            horizon_days=7,
            temporal_contract_id=raw.FIXED_CONTRACT_ID,
        )
        self.assertIsNone(features["rain_mm__lag_000"])
        self.assertIsNone(features["soil_water_fraction__lag_000"])
        self.assertIsNone(features["soil_water_area_mean_at_cutoff"])

    def test_diagnostic_bands_do_not_change_model_features(self):
        summary = raw.diagnostic_weather_summary(self.series())
        self.assertEqual(summary["lag_000_006"]["rain_mm_sum"], sum(range(358, 365)))

    def test_windowed_profile_id_round_trips(self):
        for window_days in raw.WINDOW_DAYS_OPTIONS:
            profile_id = raw.windowed_profile_id(window_days)
            self.assertEqual(raw.window_days_from_profile_id(profile_id), window_days)
        self.assertIsNone(raw.window_days_from_profile_id("raw_primary_plus_physical_state"))
        with self.assertRaises(ValueError):
            raw.windowed_profile_id(45)

    def test_windowed_columns_truncate_raw_channels_only(self):
        for window_days in raw.WINDOW_DAYS_OPTIONS:
            columns = raw.windowed_feature_columns(window_days, include_horizon=False)
            for channel in raw.RAW_CHANNELS:
                self.assertIn(raw.lag_feature_name(channel, 0), columns)
                self.assertIn(raw.lag_feature_name(channel, window_days - 1), columns)
                self.assertNotIn(raw.lag_feature_name(channel, window_days), columns)
            for channel in raw.PHYSICAL_CHANNELS + raw.STATE_CHANNELS:
                self.assertNotIn(raw.lag_feature_name(channel, 0), columns)
            for name in raw.PHYSICAL_STATE_SCALARS:
                self.assertIn(name, columns)
            self.assertIn("target_day_sin", columns)
            self.assertNotIn("horizon_days", columns)
        with_horizon = raw.windowed_feature_columns(30, include_horizon=True)
        self.assertIn("horizon_days", with_horizon)

    def test_feature_set_contract_includes_windowed_profiles(self):
        for temporal_contract_id in (raw.FIXED_CONTRACT_ID, raw.LAG_CONTRACT_ID):
            profiles = raw.feature_set_contract(temporal_contract_id)["profiles"]
            for window_days in raw.WINDOW_DAYS_OPTIONS:
                profile_id = raw.windowed_profile_id(window_days)
                self.assertIn(profile_id, profiles)
                self.assertEqual(
                    profiles[profile_id],
                    raw.windowed_feature_columns(
                        window_days,
                        include_horizon=temporal_contract_id == raw.LAG_CONTRACT_ID,
                    ),
                )

    def test_windowed_features_reuse_full_365_day_build(self):
        """Balance/SMI scalars stay shared: built from the same 365-day
        series regardless of which window profile will later select columns."""
        features = raw.build_raw_features(
            self.series(),
            target_date=date(2026, 1, 1),
            horizon_days=7,
            temporal_contract_id=raw.FIXED_CONTRACT_ID,
        )
        windowed_columns = raw.windowed_feature_columns(30, include_horizon=False)
        for column in windowed_columns:
            self.assertIn(column, features)


if __name__ == "__main__":
    unittest.main()
