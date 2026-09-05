import unittest
from datetime import date, timedelta

from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_biology_v3_physical as biology_v3_physical
from rainmapper_core import mushroom_ml_biology_v4 as biology_v4
from rainmapper_core import mushroom_observation_context as weather_context


class MushroomMLBiologyV4Tests(unittest.TestCase):
    def station(self, code: str, *, distance: float, missing_age: int | None = None):
        cutoff = date(2026, 8, 15)
        records = {}
        for age in range(90):
            if age == missing_age:
                continue
            day = cutoff - timedelta(days=age)
            records[day] = weather_context.DailyWeatherRecord(
                source="test", station_code=code, station_name=code, day=day,
                lat=42.0 + distance, lon=2.0, rain_mm=0.0,
                temp_max_c=20.0, temp_min_c=10.0,
                humidity_max_pct=90.0, humidity_min_pct=60.0,
                wind_avg_kmh=None, wind_gust_kmh=None, wind_direction_deg=None,
            )
        return weather_context.WeatherStation(
            source="test", station_code=code, station_name=code,
            lat=42.0 + distance, lon=2.0, altitude_m=500.0,
            records_by_day=records,
        )

    def source_v3_sample(self, *, lag: bool = False) -> dict[str, object]:
        feature_set = biology_v3.LAG_EVENT_BIOLOGY_V3 if lag else biology_v3.FIXED_GAP_7D_BIOLOGY_V3
        cutoff = date(2026, 8, 15)
        dates = [cutoff - timedelta(days=age) for age in reversed(range(90))]
        predictive = {
            name: 1.0 for name in feature_set.candidate_predictive_feature_cols
        }
        if lag:
            predictive["horizon_days"] = 3.0
        return {
            "sample_id": f"obs|{feature_set.feature_set_id}|h{'3' if lag else '7'}",
            "prediction_target": "favorable",
            "predictive_features": predictive,
            "quality": {"training_eligible": True},
            "metadata": {
                "area_id": "area",
                "cutoff_date": cutoff.isoformat(),
                "area_representative_location": {"lat": 42.0, "lon": 2.0},
                "weather_series": {
                    "daily_dates": [day.isoformat() for day in dates],
                    "daily_area_rain_idw_mean_mm": [5.0] * 90,
                    "daily_temp_min_corrected_c": [10.0] * 90,
                    "daily_temp_max_corrected_c": [20.0] * 90,
                    "daily_humidity_min_pct": [60.0] * 90,
                    "daily_humidity_max_pct": [90.0] * 90,
                },
            },
        }

    def soil_state(self) -> dict[str, object]:
        return {
            "predictive_features": {
                field.name: 0.5 for field in biology_v4.SOIL_WATER_FIELDS
            },
            "quality": {"training_eligible": True},
            "metadata": {"variant_id": "test"},
        }

    def test_blocks_are_cumulative_and_keep_weather_extremes_not_means(self) -> None:
        core = biology_v4.predictive_columns(
            biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "core"
        )
        extended = biology_v4.predictive_columns(
            biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "extended_weather"
        )
        soil = biology_v4.predictive_columns(
            biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "soil_water"
        )
        self.assertTrue(set(core) < set(extended) < set(soil))
        self.assertFalse(any("mean_cutoff" in name for name in core))
        self.assertIn("humidity_min_cutoff_22_30d_pct", extended)
        self.assertIn("temp_max_cutoff_22_30d_c", extended)

    def test_v3_physical_is_core_plus_balance_and_smi_only(self) -> None:
        columns = set(
            biology_v3_physical.predictive_columns(
                biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
            )
        )
        core = set(
            biology_v4.predictive_columns(
                biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "core"
            )
        )
        self.assertEqual(
            columns - core,
            {
                *(field.name for field in biology_v4.CLIMATIC_BALANCE_FIELDS),
                *(field.name for field in biology_v4.SOIL_WATER_FIELDS),
            },
        )
        self.assertNotIn("rain_cutoff_22_30d_mm", columns)

    def test_v3_physical_training_and_inference_projections_match(self) -> None:
        source = self.source_v3_sample()
        source["quality"]["inference_eligible"] = True
        state = self.soil_state()
        stored = biology_v4.build_biology_v4_sample(
            source,
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
        )
        stored["metadata"]["soil_state_key"] = "area|2026-08-15"
        payload = {
            "temporal_contract_id": biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            "samples": [stored],
            "soil_variants": {
                biology_v3_physical.SOIL_VARIANT_ID: {
                    "area_state_catalog": {"area|2026-08-15": state}
                }
            },
        }
        benchmark = biology_v3_physical.materialize_benchmark(payload)
        area_series = {
            **state["predictive_features"],
            "soil_water_quality": state["quality"],
            "soil_water_metadata": state["metadata"],
        }
        inference = biology_v3_physical.materialize_inference_row(
            source,
            temporal_contract_id=biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID,
            area_series=area_series,
        )

        self.assertEqual(benchmark["training_eligible_sample_count"], 1)
        self.assertTrue(inference["quality"]["inference_eligible"])
        self.assertEqual(
            benchmark["samples"][0]["predictive_features"],
            inference["predictive_features"],
        )

    def test_extended_weather_contributions_are_declarative_and_isolated(self) -> None:
        core = set(biology_v4.predictive_columns(
            biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "core"
        ))
        rain = biology_v4.extended_weather_contribution_columns(
            biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "rain_22_30"
        )
        rainy_days = biology_v4.extended_weather_contribution_columns(
            biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "rainy_days"
        )
        self.assertEqual(set(rain) - core, {"rain_cutoff_22_30d_mm"})
        self.assertEqual(
            set(rainy_days) - core,
            set(biology_v4.EXTENDED_WEATHER_CONTRIBUTION_GROUPS["rainy_days"]),
        )
        self.assertNotIn("rain_cutoff_22_30d_mm", rainy_days)
        with self.assertRaisesRegex(ValueError, "Unknown extended-weather"):
            biology_v4.extended_weather_contribution_columns(
                biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "unknown"
            )

    def test_complete_sample_materializes_every_block_without_losing_identity(self) -> None:
        result = biology_v4.build_biology_v4_sample(
            self.source_v3_sample(),
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            area_soil_water_state=self.soil_state(),
        )
        self.assertEqual(result["prediction_target"], "favorable")
        self.assertTrue(all(result["quality"]["eligibility_by_block"].values()))
        self.assertEqual(
            result["predictive_features"]["rainy_days_cutoff_22_30d"], 9.0
        )
        self.assertEqual(
            result["predictive_features"]["humidity_min_cutoff_22_30d_pct"], 60.0
        )

    def test_comparison_profile_uses_generic_schema_and_block_gate(self) -> None:
        complete = biology_v4.build_biology_v4_sample(
            self.source_v3_sample(),
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            area_soil_water_state=self.soil_state(),
        )
        complete["metadata"]["source_v3_metadata"]["observation_id"] = "obs"
        payload = {
            "temporal_contract_id": biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            "feature_blocks": {
                block: list(biology_v4.predictive_columns(
                    biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, block
                ))
                for block in biology_v4.BLOCK_ORDER
            },
            "samples": [complete],
            "soil_variants": {},
        }
        benchmark = biology_v4.materialize_comparison_benchmark(
            payload, profile_id="climatic_balance"
        )
        self.assertEqual(benchmark["training_eligible_sample_count"], 1)
        self.assertEqual(
            benchmark["feature_set"]["predictive_feature_cols"],
            payload["feature_blocks"]["climatic_balance"],
        )
        self.assertEqual(benchmark["samples"][0]["metadata"]["observation_id"], "obs")
        with self.assertRaisesRegex(ValueError, "Unknown Biology V4"):
            biology_v4.materialize_comparison_benchmark(payload, profile_id="unknown")

    def test_daily_inference_ignores_only_the_missing_target_gate(self) -> None:
        source = self.source_v3_sample()
        source["prediction_target"] = "unknown"
        source["quality"] = {
            "training_eligible": False,
            "rain_event_search_complete": True,
            "significant_rain_search_complete": True,
            "significant_rain_found_90d": True,
            "significant_rain_event_date": "2026-08-11",
            "significant_rain_event_amount_mm": 12.2,
            "significant_rain_threshold_mm": 5.0,
            "training_exclusion_reasons": [
                {"code": "modeling_target_unknown", "message": "target absent"}
            ],
        }
        source["metadata"]["target_date"] = "2026-08-22"
        row = biology_v4.materialize_daily_inference_row(
            source,
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            profile_id="climatic_balance",
        )
        self.assertTrue(row["quality"]["inference_eligible"])
        self.assertTrue(row["quality"]["rain_event_search_complete"])
        self.assertTrue(row["quality"]["significant_rain_search_complete"])
        self.assertTrue(row["quality"]["significant_rain_found_90d"])
        self.assertEqual(row["quality"]["significant_rain_event_date"], "2026-08-11")
        self.assertEqual(row["quality"]["significant_rain_event_amount_mm"], 12.2)
        self.assertEqual(row["quality"]["significant_rain_threshold_mm"], 5.0)
        self.assertEqual(
            row["quality"]["days_since_significant_rain_at_target"],
            source["predictive_features"]["days_since_significant_rain_at_target"],
        )
        self.assertEqual(row["metadata"]["target_date"], "2026-08-22")
        self.assertEqual(
            list(row["predictive_features"]),
            list(biology_v4.predictive_columns(
                biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "climatic_balance"
            )),
        )
        expected = biology_v4.build_biology_v4_sample(
            source,
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
        )
        self.assertEqual(
            row["predictive_features"],
            {
                name: expected["predictive_features"][name]
                for name in biology_v4.predictive_columns(
                    biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "climatic_balance"
                )
            },
        )

        source["quality"]["training_exclusion_reasons"].append(
            {"code": "temperature_coverage_below_19_of_21", "message": "weather gap"}
        )
        blocked = biology_v4.materialize_daily_inference_row(
            source,
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            profile_id="core",
        )
        self.assertFalse(blocked["quality"]["inference_eligible"])
        self.assertEqual(
            blocked["quality"]["inference_exclusion_reasons"][0]["code"],
            "temperature_coverage_below_19_of_21",
        )

    def test_train_inference_parity_audit_detects_field_drift(self) -> None:
        source = self.source_v3_sample()
        stored = biology_v4.build_biology_v4_sample(
            source,
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
        )
        payload = {
            "temporal_contract_id": biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            "feature_blocks": {
                block: list(biology_v4.predictive_columns(
                    biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, block
                ))
                for block in biology_v4.BLOCK_ORDER
            },
            "samples": [stored],
            "soil_variants": {},
        }
        clean = biology_v4.audit_train_inference_parity(
            {"samples": [source]}, payload, profile_id="climatic_balance"
        )
        self.assertTrue(clean["parity_passed"])
        stored["predictive_features"]["rain_cutoff_0_3d_mm"] = 999.0
        drift = biology_v4.audit_train_inference_parity(
            {"samples": [source]}, payload, profile_id="climatic_balance"
        )
        self.assertFalse(drift["parity_passed"])
        self.assertEqual(
            drift["predictive_field_mismatch_counts"]["rain_cutoff_0_3d_mm"], 1
        )

    def test_lag_event_keeps_horizon_while_fixed_gap_does_not(self) -> None:
        lag_columns = biology_v4.predictive_columns(
            biology_v4.LAG_EVENT_BIOLOGY_V4_ID, "core"
        )
        fixed_columns = biology_v4.predictive_columns(
            biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID, "core"
        )
        self.assertEqual(lag_columns[0], "horizon_days")
        self.assertNotIn("horizon_days", fixed_columns)

    def test_missing_weather_keeps_sample_and_marks_later_blocks_ineligible(self) -> None:
        source = self.source_v3_sample()
        source["metadata"]["weather_series"]["daily_temp_min_corrected_c"][-2] = None
        result = biology_v4.build_biology_v4_sample(
            source,
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            area_soil_water_state=self.soil_state(),
        )
        self.assertTrue(result["quality"]["eligibility_by_block"]["core"])
        self.assertFalse(result["quality"]["eligibility_by_block"]["climatic_balance"])
        self.assertIn("climatic_balance_features_missing", {
            reason["code"]
            for reason in result["quality"]["exclusion_reasons_by_block"]["climatic_balance"]
        })

    def test_quality_and_metadata_are_rejected_from_X(self) -> None:
        result = biology_v4.build_biology_v4_sample(
            self.source_v3_sample(),
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
            area_soil_water_state=self.soil_state(),
        )
        for forbidden in ("eligibility_by_block", "source_v3_metadata"):
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(ValueError, "cannot enter X"):
                    biology_v4.build_biology_v4_X(
                        [result],
                        temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
                        block="core",
                        requested_cols=[forbidden],
                    )

    def test_unregistered_field_cannot_enter_predictive_features_or_X(self) -> None:
        result = biology_v4.build_biology_v4_sample(
            self.source_v3_sample(),
            temporal_contract_id=biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID,
        )
        result["predictive_features"]["area_id"] = 1.0
        with self.assertRaisesRegex(ValueError, "Unregistered"):
            biology_v4.validate_biology_v4_sample(
                result, biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID
            )

    def test_temperature_gap_uses_real_cutoff_eligible_fallback_without_interpolation(self) -> None:
        cutoff = date(2026, 8, 15)
        primary = self.station("PRIMARY", distance=0.001, missing_age=2)
        fallback = self.station("FALLBACK", distance=0.002)
        dates = [cutoff - timedelta(days=age) for age in reversed(range(90))]
        result = biology_v4.build_cutoff_temperature_extremes_with_station_fallback(
            {("test", "PRIMARY"): primary, ("test", "FALLBACK"): fallback},
            primary_station=primary,
            dates=dates,
            cutoff_day=cutoff,
            area_lat=42.0,
            area_lon=2.0,
            area_altitude_m=500.0,
        )
        self.assertEqual(result["quality"]["fallback_station_days"], 1)
        self.assertEqual(result["quality"]["missing_days"], 0)
        self.assertEqual(result["quality"]["interpolated_days"], 0)
        self.assertEqual(result["metadata"]["daily_source_codes"][-3], "test:FALLBACK")


if __name__ == "__main__":
    unittest.main()
