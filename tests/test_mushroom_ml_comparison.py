from __future__ import annotations

import json
from copy import deepcopy
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
    FIXED_GAP_7D_ALTITUDE_V2,
    LAG_EVENT_ALTITUDE_V2,
    build_fixed_gap_7d_altitude_features,
    build_lag_event_altitude_features,
)
from rainmapper_core.mushroom_ml_experiment_trainer import model_filename
from rainmapper_core.mushroom_ml_predictor import PredictionResult
from rainmapper_core.mushroom_ml_input_identity import known_sites_semantic_identity
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

    def test_stale_comparison_bundle_is_excluded_without_raising(self) -> None:
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

            self.assertIsNone(comparator._bundle("fixed_gap_7d_v1"))
            exclusion = comparator._bundle_unavailability["fixed_gap_7d_v1"]
            self.assertEqual(exclusion["reason"], "model_input_identity_mismatch")
            self.assertEqual(exclusion["input_name"], "features.json")
            self.assertEqual(exclusion["expected_sha256"], "0" * 64)
            self.assertEqual(len(exclusion["actual_sha256"]), 64)

    def test_missing_comparison_bundle_has_readable_reason(self) -> None:
        predictor = SimpleNamespace(species_id="boletus")
        with TemporaryDirectory() as temporary:
            comparator = MushroomModelComparator(predictor, Path(temporary))

            self.assertIsNone(comparator._bundle("fixed_gap_7d_v1"))

            self.assertEqual(
                comparator._bundle_unavailability["fixed_gap_7d_v1"],
                {
                    "available": False,
                    "reason": "model_not_trained",
                    "message": (
                        "No trained comparison model is available for this contract."
                    ),
                },
            )

    def test_stale_fixed_bundle_does_not_block_valid_lag_comparison(self) -> None:
        import hashlib
        import joblib

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            features = root / "features.json"
            sites = root / "sites.json"
            profiles = root / "profiles.json"
            features.write_text("{}", encoding="utf-8")
            sites.write_text("{}", encoding="utf-8")
            profiles.write_text('{"species_profiles": []}', encoding="utf-8")
            target = date(2026, 8, 10)
            records = {
                target - timedelta(days=119 - offset): DailyWeatherRecord(
                    source="test",
                    station_code="station",
                    station_name="Station",
                    day=target - timedelta(days=119 - offset),
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
                for offset in range(120)
            }
            station = WeatherStation(
                "test", "station", "Station", 42.0, 1.0, records, altitude_m=500.0
            )
            predictor = Mock()
            predictor.species_id = "boletus"
            predictor.season_phase.return_value = "main"
            predictor._features_artifact_path = features
            predictor._known_sites_path = sites
            predictor._profiles_path = profiles
            predictor._area_profiles = {
                "area": SimpleNamespace(lat=42.0, lon=1.0, gis_altitude_m=1000.0)
            }
            predictor._weather_stations = {("test", "station"): station}
            stale_path = root / model_filename(
                FIXED_GAP_7D_ALTITUDE_V2.feature_set_id, "boletus"
            )
            joblib.dump(
                {
                    "kind": "mushroom_ml_experiment_bundle",
                    "feature_set_id": FIXED_GAP_7D_ALTITUDE_V2.feature_set_id,
                    "features_sha256": hashlib.sha256(features.read_bytes()).hexdigest(),
                    "known_sites_sha256": "0" * 64,
                },
                stale_path,
            )
            comparator = MushroomModelComparator(predictor, root)
            comparator._bundles[LAG_EVENT_ALTITUDE_V2.feature_set_id] = {
                "kind": "mushroom_ml_experiment_bundle",
                "feature_set_id": LAG_EVENT_ALTITUDE_V2.feature_set_id,
                "feature_cols": list(LAG_EVENT_ALTITUDE_V2.feature_cols),
                "models": {"random_forest_restricted_v1": ConstantEstimator(0.4)},
            }

            result = comparator.compare("area", target, issue_date=target)

            fixed = result[FIXED_GAP_7D_ALTITUDE_V2.feature_set_id]
            lag = result[LAG_EVENT_ALTITUDE_V2.feature_set_id]
            self.assertFalse(fixed["available"])
            self.assertEqual(fixed["reason"], "model_input_identity_mismatch")
            self.assertEqual(fixed["input_name"], "sites.json")
            self.assertTrue(lag["available"])
            self.assertEqual(lag["ensemble_probability"], 0.4)

    def test_semantic_area_identity_ignores_name_but_detects_altitude(self) -> None:
        import hashlib
        import joblib

        contract = {
            "id": "fixture_area_altitude_v1",
            "collections": [
                {
                    "path": "micro_areas",
                    "id_field": "micro_area_id",
                    "group_field": "area_id",
                    "fields": [
                        "micro_area_id",
                        "area_id",
                        "derived_context.gis_dem.altitude_mean_m",
                    ],
                }
            ],
        }
        known_sites = {
            "micro_areas": [
                {
                    "micro_area_id": "area_1",
                    "area_id": "area",
                    "name": "Old name",
                    "derived_context": {"gis_dem": {"altitude_mean_m": 700.0}},
                }
            ]
        }
        identity = known_sites_semantic_identity(known_sites, contract)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            features = root / "features.json"
            sites = root / "sites.json"
            features.write_text("{}", encoding="utf-8")
            sites.write_text(json.dumps(known_sites), encoding="utf-8")
            feature_set_id = "fixed_gap_7d_v1"
            joblib.dump(
                {
                    "kind": "mushroom_ml_experiment_bundle",
                    "feature_set_id": feature_set_id,
                    "features_sha256": hashlib.sha256(features.read_bytes()).hexdigest(),
                    "training_features_identity_policy": (
                        "artifact_sha256_provenance_only"
                    ),
                    "known_sites_sha256": "0" * 64,
                    "known_sites_identity_contract": contract,
                    "known_sites_semantic_sha256": identity["sha256"],
                    "known_sites_area_sha256": identity["area_sha256"],
                },
                root / model_filename(feature_set_id, "boletus"),
            )
            predictor = SimpleNamespace(
                species_id="boletus",
                _features_artifact_path=features,
                _known_sites_path=sites,
            )
            comparator = MushroomModelComparator(predictor, root)

            bundle = comparator._bundle(feature_set_id)
            self.assertIsNotNone(bundle)
            self.assertEqual(
                comparator._area_input_identity(bundle, "area")["status"],
                "matched",
            )

            features.write_text('{"new_area":"training provenance changed"}', encoding="utf-8")
            comparator = MushroomModelComparator(predictor, root)
            bundle = comparator._bundle(feature_set_id)
            self.assertIsNotNone(bundle)
            self.assertEqual(
                comparator._area_input_identity(bundle, "area")["status"],
                "matched",
            )

            renamed = deepcopy(known_sites)
            renamed["micro_areas"][0]["name"] = "New name"
            sites.write_text(json.dumps(renamed), encoding="utf-8")
            comparator = MushroomModelComparator(predictor, root)
            bundle = comparator._bundle(feature_set_id)
            self.assertIsNotNone(bundle)
            self.assertEqual(
                comparator._area_input_identity(bundle, "area")["status"],
                "matched",
            )

            changed = deepcopy(renamed)
            changed["micro_areas"][0]["derived_context"]["gis_dem"][
                "altitude_mean_m"
            ] = 710.0
            sites.write_text(json.dumps(changed), encoding="utf-8")
            comparator = MushroomModelComparator(predictor, root)
            bundle = comparator._bundle(feature_set_id)
            mismatch = comparator._area_input_identity(bundle, "area")
            self.assertFalse(mismatch["available"])
            self.assertEqual(
                mismatch["reason"], "model_area_input_identity_mismatch"
            )

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
        station = WeatherStation(
            "test", "station", "Station", 42.0, 1.0, records, altitude_m=500.0
        )
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
        for spec in (FIXED_GAP_7D_ALTITUDE_V2, LAG_EVENT_ALTITUDE_V2):
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
        fixed_id = FIXED_GAP_7D_ALTITUDE_V2.feature_set_id
        lag_id = LAG_EVENT_ALTITUDE_V2.feature_set_id
        self.assertEqual(result[fixed_id]["cutoff_date"], "2026-08-07")
        self.assertEqual(result[lag_id]["cutoff_date"], "2026-08-09")
        self.assertEqual(result[lag_id]["horizon_days"], 5)
        self.assertEqual(result[lag_id]["ensemble_probability"], 0.4)
        self.assertEqual(result["interpretation"]["reference_range"]["min"], 0.5)
        self.assertEqual(
            result[fixed_id]["feature_count"],
            len(FIXED_GAP_7D_ALTITUDE_V2.feature_cols),
        )
        self.assertGreater(
            result[fixed_id]["features_used"]["rain_suppressed_days_90"],
            0,
        )
        self.assertEqual(
            result[fixed_id]["station_selection"][
                "skipped_nearer_station_count"
            ],
            0,
        )
        self.assertEqual(
            result[fixed_id]["station_selection"][
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
            "weather_station_altitude_m": 500.0,
            **ctx.build_daily_series(station, target, duplicate_dates),
        }
        expected_fixed, _ = build_fixed_gap_7d_altitude_features(episode)
        expected_lag, _ = build_lag_event_altitude_features(episode, 5)
        self.assertEqual(result[fixed_id]["features_used"], expected_fixed)
        self.assertEqual(result[lag_id]["features_used"], expected_lag)
