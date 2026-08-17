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


if __name__ == "__main__":
    unittest.main()
