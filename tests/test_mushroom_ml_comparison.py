from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

import numpy as np

from rainmapper_core.mushroom_ml_comparison import MushroomModelComparator
from rainmapper_core import mushroom_observation_context as ctx
from rainmapper_core.mushroom_ml_experiments import (
    FIXED_GAP_7D_V1,
    LAG_EVENT_V1,
    build_fixed_gap_7d_features,
    build_lag_event_features,
)
from rainmapper_core.mushroom_ml_predictor import PredictionResult
from rainmapper_core.mushroom_observation_context import DailyWeatherRecord, WeatherStation


class ConstantEstimator:
    def __init__(self, probability: float) -> None:
        self.probability = probability

    def predict_proba(self, values):
        return np.asarray([[1.0 - self.probability, self.probability] for _ in values])


class MushroomModelComparisonTests(TestCase):
    def test_severe_feature_extrapolation_excludes_logistic_regression(self) -> None:
        bundle = {
            "feature_cols": ["heat_stress_observed_at_cutoff"],
            "feature_support": {
                "heat_stress_observed_at_cutoff": {
                    "observed_count": 30,
                    "min": 0.0,
                    "max": 8.0,
                    "mean": 0.5,
                    "std": 1.25,
                }
            },
            "models": {
                "logistic_regression_reduced_v1": ConstantEstimator(1.0),
                "random_forest_restricted_v1": ConstantEstimator(0.2),
            },
            "evaluation": {},
        }

        result = MushroomModelComparator._apply(
            bundle, {"heat_stress_observed_at_cutoff": 59.0}
        )

        self.assertEqual(
            result["estimator_exclusions"]["logistic_regression_reduced_v1"][
                "reason"
            ],
            "severe_feature_extrapolation",
        )
        self.assertEqual(
            result["severe_out_of_domain_features"][0]["feature"],
            "heat_stress_observed_at_cutoff",
        )

    def test_historical_evaluation_returns_held_out_probabilities(self) -> None:
        bundle = {
            "episode_partitions": [
                {
                    "episode_id": "sp|area|2025-08-06",
                    "area_id": "area",
                    "target_date": "2025-08-06",
                    "prediction_target": "favorable",
                    "partition": "test",
                    "chronological_partition": "test",
                }
            ],
            "held_out_predictions": [
                {
                    "sample_id": "sp|area|2025-08-06|h1",
                    "area_id": "area",
                    "target_date": "2025-08-06",
                    "horizon_days": 1,
                    "estimator_probabilities": {
                        "logistic_regression_reduced_v1": 0.84,
                        "random_forest_restricted_v1": 0.52,
                    },
                }
            ],
        }

        result = MushroomModelComparator._historical_evaluation(
            bundle,
            area_id="area",
            target_date=date(2025, 8, 6),
            horizon_days=1,
        )

        self.assertTrue(result["out_of_sample"])
        self.assertEqual(result["prediction_target"], "favorable")
        self.assertEqual(
            result["estimator_probabilities"][
                "logistic_regression_reduced_v1"
            ],
            0.84,
        )

    def test_bundle_must_match_current_inputs(self) -> None:
        import joblib

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            features = root / "features.json"
            sites = root / "sites.json"
            features.write_text("{}", encoding="utf-8")
            sites.write_text("{}", encoding="utf-8")
            bundle_path = root / (
                "mushroom_ml_experiment_fixed_gap_7d_v1_boletus.joblib"
            )
            joblib.dump(
                {
                    "kind": "mushroom_ml_experiment_bundle",
                    "feature_set_id": "fixed_gap_7d_v1",
                    "features_sha256": "0" * 64,
                    "known_sites_sha256": "0" * 64,
                },
                bundle_path,
            )
            predictor = SimpleNamespace(
                species_id="boletus",
                _features_artifact_path=features,
                _known_sites_path=sites,
            )
            comparator = MushroomModelComparator(predictor, root)

            with self.assertRaisesRegex(ValueError, "does not match current"):
                comparator._bundle("fixed_gap_7d_v1")

    def test_future_comparison_uses_only_declared_cutoffs(self) -> None:
        issue = date(2026, 8, 10)
        target = issue + timedelta(days=4)
        records = {}
        for offset in range(120):
            day = target - timedelta(days=119 - offset)
            records[day] = DailyWeatherRecord(
                source="test",
                station_code="station",
                station_name="Station",
                day=day,
                lat=42.0,
                lon=1.0,
                rain_mm=1.0,
                temp_max_c=20.0,
                temp_min_c=10.0,
                humidity_max_pct=80.0,
                humidity_min_pct=40.0,
                wind_avg_kmh=None,
                wind_gust_kmh=None,
                wind_direction_deg=None,
            )
        station = WeatherStation("test", "station", "Station", 42.0, 1.0, records)
        operational = PredictionResult(
            species_id="boletus",
            area_id="area",
            target_date=target,
            lr_probability=0.8,
            rf_probability=0.6,
            ensemble_probability=0.7,
            label="favorable",
            weather_station_code="station",
            weather_station_distance_km=0.0,
            weather_coverage_days=30,
            season_phase="main",
        )
        predictor = Mock()
        predictor.species_id = "boletus"
        predictor.predict.return_value = operational
        predictor._area_profiles = {
            "area": SimpleNamespace(lat=42.0, lon=1.0, gis_altitude_m=1000.0)
        }
        predictor._weather_stations = {("test", "station"): station}
        comparator = MushroomModelComparator(predictor, Path("/unused"))
        for spec in (FIXED_GAP_7D_V1, LAG_EVENT_V1):
            comparator._bundles[spec.feature_set_id] = {
                "kind": "mushroom_ml_experiment_bundle",
                "feature_set_id": spec.feature_set_id,
                "feature_cols": list(spec.feature_cols),
                "models": {
                    "logistic_regression_reduced_v1": ConstantEstimator(0.3),
                    "random_forest_restricted_v1": ConstantEstimator(0.5),
                },
                "evaluation": {
                    "available": True,
                    "baseline": {"brier_score": 0.25},
                    "estimators": {
                        "logistic_regression_reduced_v1": {
                            "n": 10,
                            "brier_score": 0.20,
                            "roc_auc": 0.70,
                        },
                        "random_forest_restricted_v1": {
                            "n": 10,
                            "brier_score": 0.15,
                            "roc_auc": 0.80,
                        },
                    },
                },
            }

        result = comparator.compare("area", target, issue_date=issue)

        self.assertEqual(result["weather_contract"]["version"], "observed_weather_v2")
        self.assertNotIn("operational_v0", result)
        self.assertEqual(result["fixed_gap_7d_v1"]["cutoff_date"], "2026-08-07")
        self.assertEqual(result["lag_event_v1"]["cutoff_date"], "2026-08-09")
        self.assertEqual(result["lag_event_v1"]["horizon_days"], 5)
        self.assertEqual(result["lag_event_v1"]["ensemble_probability"], 0.4)
        self.assertEqual(result["interpretation"]["reference_range"]["min"], 0.5)
        self.assertEqual(
            result["fixed_gap_7d_v1"]["feature_count"],
            len(FIXED_GAP_7D_V1.feature_cols),
        )
        self.assertGreater(
            result["fixed_gap_7d_v1"]["features_used"]["rain_suppressed_days_90"],
            0,
        )
        self.assertEqual(
            result["fixed_gap_7d_v1"]["station_selection"][
                "skipped_nearer_station_count"
            ],
            0,
        )
        self.assertEqual(
            result["fixed_gap_7d_v1"]["station_selection"][
                "selected_station_quality"
            ]["rain_days_90"],
            90,
        )

        duplicate_dates = ctx._consecutive_duplicate_rain_dates(
            ctx.records_for_window(station, target, ctx.DAILY_SERIES_DAYS)
        )
        episode = {
            "observed_at": target.isoformat(),
            "gis_altitude_m": 1000.0,
            **ctx.build_daily_series(station, target, duplicate_dates),
        }
        expected_fixed, _ = build_fixed_gap_7d_features(episode)
        expected_lag, _ = build_lag_event_features(episode, 5)
        self.assertEqual(
            result["fixed_gap_7d_v1"]["features_used"], expected_fixed
        )
        self.assertEqual(result["lag_event_v1"]["features_used"], expected_lag)
