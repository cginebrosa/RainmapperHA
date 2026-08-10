import unittest
from collections import Counter

from rainmapper_core.mushroom_ml_experiments import (
    FIXED_GAP_7D_V1,
    LAG_EVENT_V1,
    build_benchmark,
    build_fixed_gap_7d_features,
    build_lag_event_features,
)


def _episode(day: str = "2026-08-14") -> dict:
    rain = [0.0] * 120
    rain[-9] = 10.0
    return {
        "species_id": "boletus_aereus",
        "area_id": "coll_batalla",
        "observed_at": day,
        "prediction_target": "favorable",
        "gis_altitude_m": 700.0,
        "daily_rain_mm": rain,
        "daily_rain_observed": [1.0] * 120,
        "daily_rain_suppressed": [0.0] * 120,
        "daily_temp_max_c": [25.0] * 120,
        "daily_temp_mean_c": [18.0] * 120,
        "daily_humidity_mean_pct": [70.0] * 120,
    }


class LagEventFeaturesTests(unittest.TestCase):
    def test_future_horizon_moves_cutoff_and_never_reads_later_values(self) -> None:
        episode = _episode()
        episode["daily_rain_mm"][-1] = 99.0

        features, metadata = build_lag_event_features(episode, horizon_days=4)

        self.assertEqual(metadata["cutoff_date"], "2026-08-10")
        self.assertEqual(features["rain_cutoff_0_3d_mm"], 0.0)
        self.assertNotIn(99.0, features.values())

    def test_known_rain_age_is_expressed_at_target_date(self) -> None:
        features, _ = build_lag_event_features(_episode(), horizon_days=4)
        self.assertEqual(features["days_since_significant_rain_at_target"], 8.0)

    def test_missing_rain_day_is_zero_with_separate_coverage(self) -> None:
        episode = _episode()
        episode["daily_rain_mm"][-6] = None
        episode["daily_rain_observed"][-6] = 0.0

        features, _ = build_lag_event_features(episode, horizon_days=4)
        self.assertEqual(features["rain_cutoff_0_3d_mm"], 0.0)
        self.assertEqual(features["rain_missing_days_21"], 1.0)

    def test_incomplete_immediate_heat_run_is_censored(self) -> None:
        episode = _episode()
        episode["daily_temp_max_c"][-5] = None

        features, _ = build_lag_event_features(episode, horizon_days=4)
        self.assertEqual(features["heat_stress_observed_at_cutoff"], 0.0)
        self.assertEqual(features["heat_stress_is_censored"], 1.0)

    def test_no_rain_event_saturates_at_ninety_days(self) -> None:
        episode = _episode()
        episode["daily_rain_mm"] = [0.0] * 120

        features, _ = build_lag_event_features(episode, horizon_days=4)

        self.assertEqual(features["days_since_rain_gt_2_at_target"], 90.0)
        self.assertEqual(features["days_since_significant_rain_at_target"], 90.0)
        self.assertEqual(features["significant_rain_found_90d"], 0.0)

    def test_fixed_gap_always_uses_target_minus_seven(self) -> None:
        features, metadata = build_fixed_gap_7d_features(_episode())
        self.assertEqual(metadata["cutoff_date"], "2026-08-07")
        self.assertNotIn("horizon_days", features)
        self.assertEqual(metadata["feature_set_id"], FIXED_GAP_7D_V1.feature_set_id)


class BenchmarkContractTests(unittest.TestCase):
    def test_episode_horizons_stay_in_same_partition(self) -> None:
        rows = []
        for index in range(10):
            row = _episode(f"2026-08-{index + 1:02d}")
            row.update(
                {
                    "micro_area_id": "micro_a",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "prediction_target": "favorable" if index % 2 else "unfavorable",
                }
            )
            rows.append(row)

        payload = build_benchmark(rows, {"micro_a": "area_a"}, horizons=(1, 3, 6))

        self.assertEqual(payload["feature_set"]["id"], LAG_EVENT_V1.feature_set_id)
        self.assertEqual(payload["weather_contract"]["version"], "observed_weather_v2")
        self.assertEqual(payload["weather_contract"]["station_max_distance_km"], 15.0)
        self.assertEqual(payload["episode_count"], 10)
        self.assertEqual(payload["sample_count"], 30)
        by_episode: dict[str, set[str]] = {}
        for sample in payload["samples"]:
            by_episode.setdefault(sample["episode_id"], set()).add(sample["partition"])
        self.assertTrue(all(len(partitions) == 1 for partitions in by_episode.values()))

    def test_fixed_gap_has_one_sample_per_episode(self) -> None:
        rows = []
        for index in range(4):
            row = _episode(f"2026-08-{index + 1:02d}")
            row.update(
                {
                    "micro_area_id": "micro_a",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "prediction_target": "favorable" if index % 2 else "unfavorable",
                }
            )
            rows.append(row)
        payload = build_benchmark(
            rows,
            {"micro_a": "area_a"},
            feature_set_id=FIXED_GAP_7D_V1.feature_set_id,
        )
        self.assertEqual(payload["episode_count"], 4)
        self.assertEqual(payload["sample_count"], 4)
        self.assertEqual(payload["horizons"], [7])

    def test_partition_is_stratified_and_keeps_chronology_as_diagnostic(self) -> None:
        rows = []
        for index in range(26):
            row = _episode(f"2026-01-{index + 1:02d}")
            row.update(
                {
                    "micro_area_id": "micro_a",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "prediction_target": (
                        "favorable" if index < 21 else "unfavorable"
                    ),
                }
            )
            rows.append(row)

        payload = build_benchmark(
            rows,
            {"micro_a": "area_a"},
            feature_set_id=FIXED_GAP_7D_V1.feature_set_id,
        )
        train = Counter(
            sample["prediction_target"]
            for sample in payload["samples"]
            if sample["partition"] == "train"
        )
        test = Counter(
            sample["prediction_target"]
            for sample in payload["samples"]
            if sample["partition"] == "test"
        )
        chronological_train = Counter(
            sample["prediction_target"]
            for sample in payload["samples"]
            if sample["chronological_partition"] == "train"
        )

        self.assertEqual(train, Counter({"favorable": 15, "unfavorable": 3}))
        self.assertEqual(test, Counter({"favorable": 6, "unfavorable": 2}))
        self.assertEqual(chronological_train["unfavorable"], 0)


if __name__ == "__main__":
    unittest.main()
