from datetime import date, timedelta
from unittest import TestCase
from unittest import mock

from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_biology_v3_physical as biology_v3_physical
from rainmapper_core import mushroom_ml_biology_v4 as biology_v4
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_runtime_features as runtime_features


class MushroomMLRuntimeFeaturesTests(TestCase):
    def area_series(self):
        start = date(2024, 1, 1)
        result = {
            "daily_dates": [
                (start + timedelta(days=index)).isoformat()
                for index in range(raw.LOOKBACK_DAYS)
            ]
        }
        for key in raw.AREA_SERIES_KEYS.values():
            result[key] = [float(index % 17) for index in range(raw.LOOKBACK_DAYS)]
        return result

    def ref(self, *, version_id, contract, profile, estimator, horizon):
        return catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-a",
            version_id=version_id,
            temporal_contract_id=contract,
            profile_id=profile,
            estimator_id=estimator,
            species_id="boletus_edulis",
            horizon_days=horizon,
        )

    def test_raw_rain_quality_uses_only_the_previous_ninety_days(self) -> None:
        area_series = self.area_series()
        rain = [0.0] * raw.LOOKBACK_DAYS
        rain[0] = 20.0
        area_series[raw.AREA_SERIES_KEYS["rain_mm"]] = rain

        result = runtime_features._raw_rain_quality(area_series, horizon_days=7)

        self.assertFalse(result["significant_rain_found_90d"])
        self.assertEqual(result["days_since_significant_rain_at_target"], 90.0)
        self.assertIsNone(result["significant_rain_event_date"])
        self.assertIsNone(result["significant_rain_event_amount_mm"])

    def test_raw_rain_quality_identifies_exact_daily_idw_event(self) -> None:
        area_series = self.area_series()
        rain = [0.0] * raw.LOOKBACK_DAYS
        rain[-5] = 12.4
        area_series[raw.AREA_SERIES_KEYS["rain_mm"]] = rain

        result = runtime_features._raw_rain_quality(area_series, horizon_days=7)

        self.assertEqual(result["significant_rain_event_date"], "2024-12-26")
        self.assertEqual(result["significant_rain_event_amount_mm"], 12.4)
        self.assertEqual(result["significant_rain_threshold_mm"], 5.0)
        self.assertEqual(result["days_since_significant_rain_at_target"], 11.0)

    def test_v5_lag_uses_complete_idw_physical_state_profile(self) -> None:
        result = runtime_features.build_runtime_features(
            self.ref(
                version_id="biology_v5_raw_weather_discovery",
                contract=raw.LAG_CONTRACT_ID,
                profile="raw_primary_plus_physical_state",
                estimator="elastic_net_logistic_raw365_v1",
                horizon=3,
            ),
            target_date=date(2024, 12, 31),
            area_id="area-a",
            area_context=None,
            area_series=self.area_series(),
            stations={},
        )
        features = result["predictive_features"]
        self.assertEqual(features["horizon_days"], 3.0)
        self.assertIn("target_day_sin", features)
        self.assertEqual(features["rain_mm__lag_000"], float(364 % 17))
        self.assertEqual(features["eto0_mm__lag_000"], float(364 % 17))
        self.assertEqual(
            features["soil_water_fraction__lag_000"], float(364 % 17)
        )
        self.assertIn("soil_water_area_mean_at_cutoff", features)
        self.assertTrue(result["quality"]["significant_rain_found_90d"])
        self.assertEqual(
            result["quality"]["days_since_significant_rain_at_target"], 3.0
        )

    def test_v6_uses_same_raw_series_without_four_horizon_fits(self) -> None:
        result = runtime_features.build_runtime_features(
            self.ref(
                version_id="biology_v6_smooth_hierarchical",
                contract="lag_event_biology_v6_smooth_hierarchical_v2",
                profile="smooth_weather_physical_state",
                estimator="smooth_partial_pooling_logistic_v1",
                horizon=7,
            ),
            target_date=date(2024, 12, 31),
            area_id="area-a",
            area_context=None,
            area_series=self.area_series(),
            stations={},
        )
        features = result["predictive_features"]
        self.assertEqual(
            len(features),
            len(raw.DAILY_CHANNELS) * 365
            + len(raw.PHYSICAL_STATE_SCALARS)
            + 3,
        )
        self.assertEqual(features["horizon_days"], 7.0)
        self.assertIn("target_day_sin", features)
        self.assertIn("soil_water_fraction__lag_000", features)
        self.assertEqual(result["metadata"]["horizon_days"], 7)
        self.assertTrue(result["quality"]["significant_rain_found_90d"])
        self.assertEqual(
            result["quality"]["days_since_significant_rain_at_target"], 7.0
        )

    def test_v3_physical_runtime_uses_the_declared_profile_projection(self) -> None:
        cutoff = date(2026, 8, 15)
        days = [cutoff - timedelta(days=age) for age in reversed(range(90))]
        source = {
            "sample_id": "runtime|biology_v3|h7",
            "prediction_target": "unknown",
            "predictive_features": {
                name: 1.0
                for name in biology_v3.FIXED_GAP_7D_BIOLOGY_V3.candidate_predictive_feature_cols
            },
            "quality": {
                "training_eligible": False,
                "inference_eligible": True,
                "inference_exclusion_reasons": [],
                "significant_rain_event_date": "2026-08-11",
                "significant_rain_event_amount_mm": 12.2,
                "significant_rain_threshold_mm": 5.0,
            },
            "metadata": {
                "area_id": "area-a",
                "target_date": "2026-08-22",
                "cutoff_date": cutoff.isoformat(),
                "area_representative_location": {"lat": 42.0, "lon": 2.0},
                "weather_series": {
                    "daily_dates": [day.isoformat() for day in days],
                    "daily_area_rain_idw_mean_mm": [5.0] * 90,
                    "daily_temp_min_corrected_c": [10.0] * 90,
                    "daily_temp_max_corrected_c": [20.0] * 90,
                    "daily_humidity_min_pct": [60.0] * 90,
                    "daily_humidity_max_pct": [90.0] * 90,
                },
            },
        }
        area_series = {
            **{field.name: 0.5 for field in biology_v4.SOIL_WATER_FIELDS},
            "soil_water_quality": {"training_eligible": True},
            "soil_water_metadata": {"selected_spinup_days": 365},
        }
        with mock.patch.object(
            runtime_features.biology_v3,
            "build_biology_v3_inference_sample",
            return_value=source,
        ):
            result = runtime_features.build_runtime_features(
                self.ref(
                    version_id="biology_v3",
                    contract=biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID,
                    profile=biology_v3_physical.PROFILE_ID,
                    estimator="logistic_regression_reduced_v1",
                    horizon=7,
                ),
                target_date=date(2026, 8, 22),
                area_id="area-a",
                area_context=None,
                area_series=area_series,
                stations={},
            )

        self.assertTrue(result["quality"]["inference_eligible"])
        self.assertEqual(
            list(result["predictive_features"]),
            list(
                biology_v3_physical.predictive_columns(
                    biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
                )
            ),
        )
        self.assertNotIn("rain_cutoff_22_30d_mm", result["predictive_features"])
        self.assertEqual(result["quality"]["significant_rain_event_date"], "2026-08-11")
        self.assertEqual(result["quality"]["significant_rain_event_amount_mm"], 12.2)
        self.assertEqual(result["quality"]["significant_rain_threshold_mm"], 5.0)
        self.assertEqual(
            result["quality"]["days_since_significant_rain_at_target"], 1.0
        )
