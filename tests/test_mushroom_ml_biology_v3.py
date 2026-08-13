import json
import copy
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_observation_context as weather_context


class MushroomMLBiologyV3Tests(unittest.TestCase):
    def observation(self, observation_id: str, **updates: object) -> dict[str, object]:
        row: dict[str, object] = {
            "observation_id": observation_id,
            "species_id": "boletus_edulis",
            "micro_area_id": "site_a",
            "observed_at": "2026-08-13",
            "validation_status": "valid",
            "calibration_use": "include",
            "flush_abundance": "normal",
        }
        row.update(updates)
        return row

    def weather_station(self, rain_mm: float | None) -> weather_context.WeatherStation:
        day = date(2026, 8, 13)
        record = weather_context.DailyWeatherRecord(
            source="test",
            station_code="ONE",
            station_name="One",
            day=day,
            lat=42.0,
            lon=2.0,
            rain_mm=rain_mm,
            temp_max_c=None,
            temp_min_c=None,
            humidity_max_pct=None,
            humidity_min_pct=None,
            wind_avg_kmh=None,
            wind_gust_kmh=None,
            wind_direction_deg=None,
        )
        return weather_context.WeatherStation(
            source="test",
            station_code="ONE",
            station_name="One",
            lat=42.0,
            lon=2.0,
            records_by_day={day: record},
        )

    def complete_station(
        self,
        station_code: str,
        *,
        distance_offset: float = 0.0,
        included_ages: set[int] | None = None,
    ) -> weather_context.WeatherStation:
        target_day = date(2026, 8, 13)
        ages = included_ages if included_ages is not None else set(range(120))
        records = {}
        for age in ages:
            day = target_day - timedelta(days=age)
            records[day] = weather_context.DailyWeatherRecord(
                source="test",
                station_code=station_code,
                station_name=station_code,
                day=day,
                lat=42.0 + distance_offset,
                lon=2.0,
                rain_mm=0.0,
                temp_max_c=20.0,
                temp_min_c=10.0,
                humidity_max_pct=80.0,
                humidity_min_pct=60.0,
                wind_avg_kmh=None,
                wind_gust_kmh=None,
                wind_direction_deg=None,
            )
        return weather_context.WeatherStation(
            source="test",
            station_code=station_code,
            station_name=station_code,
            lat=42.0 + distance_offset,
            lon=2.0,
            altitude_m=500.0,
            records_by_day=records,
        )

    def area_rainfall(self, *, missing_ages: set[int] | None = None) -> dict[str, object]:
        target_day = date(2026, 8, 13)
        missing = missing_ages or set()
        days = [target_day - timedelta(days=age) for age in reversed(range(120))]
        return {
            "area_rainfall_contract_id": biology_v3.AREA_RAINFALL_CONTRACT_ID,
            "source_rainfall_contract_id": "daily_rain_idw_radius15km_power2_v1",
            "daily_dates": [day.isoformat() for day in days],
            "daily_rain_idw_mean_mm": [
                None if (target_day - day).days in missing else 0.0 for day in days
            ],
            "daily_rain_suppressed_station_count": [0] * len(days),
        }

    def area_context(self) -> biology_v3.AreaPredictionContext:
        return biology_v3.AreaPredictionContext(
            area_id="area",
            lat=42.0,
            lon=2.0,
            altitude_m=1000.0,
            location_source="test",
        )

    def test_target_policy_does_not_treat_pending_as_negative(self) -> None:
        for abundance in (None, "", "pending", "unexpected"):
            with self.subTest(abundance=abundance):
                self.assertEqual(
                    biology_v3.resolve_modeling_target(
                        valid=True,
                        calibration_use="include",
                        flush_abundance=abundance,
                    ),
                    "unknown",
                )
        self.assertEqual(
            biology_v3.resolve_modeling_target(
                valid=True, calibration_use="include", flush_abundance="very_scarce"
            ),
            "unfavorable",
        )
        self.assertEqual(
            biology_v3.resolve_modeling_target(
                valid=True, calibration_use="include", flush_abundance="scarce"
            ),
            "favorable",
        )
        self.assertEqual(
            biology_v3.resolve_modeling_target(
                valid=False, calibration_use="include", flush_abundance="normal"
            ),
            "unknown",
        )
        self.assertEqual(
            biology_v3.resolve_modeling_target(
                valid=True, calibration_use="review", flush_abundance="normal"
            ),
            "unknown",
        )

    def test_microarea_duplicates_are_canonicalized_and_conflicts_preserved(self) -> None:
        rows = [
            self.observation("one", flush_abundance="very_scarce"),
            self.observation("two", flush_abundance="abundant"),
        ]
        canonical = biology_v3.canonicalize_microarea_observations(rows)
        self.assertEqual(len(canonical), 1)
        self.assertEqual(canonical[0]["n_source_rows"], 2)
        self.assertEqual(canonical[0]["modeling_target"], "favorable")
        self.assertEqual(canonical[0]["canonical_flush_abundance"], "abundant")
        self.assertTrue(canonical[0]["target_conflict"])

    def test_area_episode_preserves_mixed_microarea_evidence(self) -> None:
        rows = biology_v3.canonicalize_microarea_observations(
            [
                self.observation("one", micro_area_id="site_a", flush_abundance="normal"),
                self.observation(
                    "two", micro_area_id="site_b", flush_abundance="very_scarce"
                ),
                self.observation("three", micro_area_id="site_c", flush_abundance="pending"),
            ]
        )
        episodes = biology_v3.aggregate_area_episodes(
            rows, {"site_a": "area", "site_b": "area", "site_c": "area"}
        )
        self.assertEqual(len(episodes), 1)
        episode = episodes[0]
        self.assertEqual(episode["modeling_target"], "favorable")
        self.assertEqual(episode["n_microareas_observed"], 3)
        self.assertEqual(episode["n_microareas_target_known"], 2)
        self.assertEqual(episode["n_microareas_unknown"], 1)
        self.assertTrue(episode["mixed_target"])

    def test_microarea_point_prefers_explicit_representative_location(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "known.json"
            path.write_text(
                json.dumps(
                    {
                        "micro_areas": [
                            {
                                "micro_area_id": "site_a",
                                "area_id": "area",
                                "representative_location": {"lat": 42.0, "lon": 2.0},
                                "geometry": None,
                                "archived": False,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            context = biology_v3.load_micro_area_contexts(path)["site_a"]
            self.assertEqual((context.lat, context.lon), (42.0, 2.0))
            self.assertEqual(context.location_source, "representative_location")

    def test_idw_is_materialized_once_per_microarea_date_with_quality(self) -> None:
        canonical = biology_v3.canonicalize_microarea_observations(
            [self.observation("one"), self.observation("two")]
        )
        contexts = {
            "site_a": biology_v3.MicroAreaContext(
                micro_area_id="site_a",
                area_id="area",
                lat=42.0,
                lon=2.0,
                location_source="test",
            )
        }
        rows = biology_v3.materialize_microarea_rainfall(
            canonical,
            micro_area_contexts=contexts,
            stations={("test", "ONE"): self.weather_station(18.0)},
            excluded_station_keys=frozenset(),
            series_days=1,
        )
        self.assertEqual(len(rows), 1)
        rainfall = rows[0]["rainfall"]
        self.assertEqual(rainfall["daily_rain_idw_mm"], [18.0])
        self.assertEqual(rainfall["daily_rain_observed"], [True])
        self.assertEqual(rainfall["daily_rain_station_count"], [1])
        self.assertIsNone(rows[0]["rainfall_unavailable_reason"])

    def test_missing_microarea_location_is_explicit_not_zero(self) -> None:
        canonical = biology_v3.canonicalize_microarea_observations([self.observation("one")])
        rows = biology_v3.materialize_microarea_rainfall(
            canonical,
            micro_area_contexts={},
            stations={},
            excluded_station_keys=frozenset(),
            series_days=1,
        )
        self.assertIsNone(rows[0]["rainfall"])
        self.assertEqual(rows[0]["rainfall_unavailable_reason"], "micro_area_location_missing")

    def test_area_rainfall_is_mean_of_available_microareas_not_centroid(self) -> None:
        area = biology_v3.aggregate_area_rainfall_series(
            {
                "wet": {
                    "daily_dates": ["2026-08-12", "2026-08-13"],
                    "daily_rain_idw_mm": [50.0, None],
                },
                "dry": {
                    "daily_dates": ["2026-08-12", "2026-08-13"],
                    "daily_rain_idw_mm": [10.0, 0.0],
                },
            }
        )
        self.assertEqual(area["daily_rain_idw_mean_mm"], [30.0, 0.0])
        self.assertEqual(area["daily_microareas_available"], [2, 1])
        self.assertEqual(area["daily_microarea_spread_mm"], [40.0, 0.0])
        self.assertEqual(area["full_microarea_coverage_days"], 1)
        self.assertEqual(area["partial_microarea_coverage_days"], 1)

    def test_area_rainfall_is_missing_only_when_every_microarea_is_missing(self) -> None:
        area = biology_v3.aggregate_area_rainfall_series(
            {
                "one": {
                    "daily_dates": ["2026-08-13"],
                    "daily_rain_idw_mm": [None],
                },
                "two": {
                    "daily_dates": ["2026-08-13"],
                    "daily_rain_idw_mm": [None],
                },
            }
        )
        self.assertEqual(area["daily_rain_idw_mean_mm"], [None])
        self.assertEqual(area["rain_missing_days"], 1)
        self.assertEqual(area["daily_microareas_available"], [0])

    def test_v3_sample_separates_predictors_quality_and_metadata(self) -> None:
        station = self.complete_station("COMPLETE")
        sample = biology_v3.build_fixed_gap_7d_biology_v3(
            self.observation("one"),
            area_context=self.area_context(),
            area_rainfall=self.area_rainfall(),
            stations={("test", "COMPLETE"): station},
        )

        self.assertEqual(
            set(sample),
            {"sample_id", "prediction_target", "predictive_features", "quality", "metadata"},
        )
        self.assertNotIn("area_id", sample["predictive_features"])
        self.assertNotIn("rain_observed_days_21", sample["predictive_features"])
        self.assertEqual(sample["metadata"]["area_id"], "area")
        self.assertTrue(sample["quality"]["training_eligible"])

    def test_quality_fields_can_never_enter_X(self) -> None:
        station = self.complete_station("COMPLETE")
        sample = biology_v3.build_fixed_gap_7d_biology_v3(
            self.observation("one"),
            area_context=self.area_context(),
            area_rainfall=self.area_rainfall(),
            stations={("test", "COMPLETE"): station},
        )
        matrix_before, columns = biology_v3.build_biology_v3_X(
            [sample], biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
        )
        changed_quality = copy.deepcopy(sample)
        changed_quality["quality"]["rain_observed_days_21"] = 20
        matrix_after, _ = biology_v3.build_biology_v3_X(
            [changed_quality], biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
        )
        self.assertEqual(matrix_before, matrix_after)
        self.assertNotIn("rain_observed_days_21", columns)
        with self.assertRaisesRegex(ValueError, "Quality fields cannot enter X"):
            biology_v3.build_biology_v3_X(
                [sample],
                biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID,
                requested_cols=["rain_observed_days_21"],
            )

    def test_cutoff_sensitive_selector_falls_back_to_eligible_station(self) -> None:
        nearest_ages = set(range(22, 90)) | set(range(0, 19))
        nearest = self.complete_station(
            "NEAREST", distance_offset=0.001, included_ages=nearest_ages
        )
        fallback = self.complete_station("FALLBACK", distance_offset=0.01)
        sample = biology_v3.build_fixed_gap_7d_biology_v3(
            self.observation("one"),
            area_context=self.area_context(),
            area_rainfall=self.area_rainfall(),
            stations={
                ("test", "NEAREST"): nearest,
                ("test", "FALLBACK"): fallback,
            },
        )

        selected = sample["metadata"]["selected_station"]
        self.assertEqual(selected["station_code"], "FALLBACK")
        self.assertEqual(
            selected["selection_audit"]["skipped_nearer_station_count"], 1
        )
        self.assertTrue(sample["quality"]["station_quality_eligible"])

    def test_low_idw_coverage_excludes_with_readable_reason(self) -> None:
        station = self.complete_station("COMPLETE")
        sample = biology_v3.build_fixed_gap_7d_biology_v3(
            self.observation("one"),
            area_context=self.area_context(),
            area_rainfall=self.area_rainfall(missing_ages={8, 9, 10}),
            stations={("test", "COMPLETE"): station},
        )
        reasons = sample["quality"]["training_exclusion_reasons"]
        reason_by_code = {reason["code"]: reason["message"] for reason in reasons}
        self.assertFalse(sample["quality"]["training_eligible"])
        self.assertIn("rain_coverage_below_19_of_21", reason_by_code)
        self.assertIn("18/21", reason_by_code["rain_coverage_below_19_of_21"])

    def test_inactive_post_rain_fields_are_retained_but_not_in_default_X(self) -> None:
        station = self.complete_station("COMPLETE")
        sample = biology_v3.build_fixed_gap_7d_biology_v3(
            self.observation("one"),
            area_context=self.area_context(),
            area_rainfall=self.area_rainfall(),
            stations={("test", "COMPLETE"): station},
        )
        registry = biology_v3.biology_v3_feature_registry(
            biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
        )
        _matrix, columns = biology_v3.build_biology_v3_X(
            [sample], biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
        )
        self.assertIn(
            "temp_mean_after_significant_rain_c",
            sample["predictive_features"],
        )
        self.assertIn(
            "temp_mean_after_significant_rain_c",
            registry["inactive_predictive_feature_cols"],
        )
        self.assertNotIn("temp_mean_after_significant_rain_c", columns)
        self.assertNotIn("days_since_rain_gt_2_at_target", columns)
        self.assertIn(
            "rain_cutoff_31_60d_mm",
            registry["experimental_predictive_feature_cols"],
        )

    def test_benchmark_keeps_every_observation_instead_of_area_date_reduction(self) -> None:
        station = self.complete_station("COMPLETE")
        observations = [self.observation("one"), self.observation("two")]
        payload = biology_v3.build_biology_v3_benchmark(
            observations,
            feature_set_id=biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID,
            micro_area_to_area={"site_a": "area"},
            area_contexts={"area": self.area_context()},
            area_rainfall_by_date={
                ("area", "2026-08-13"): self.area_rainfall()
            },
            stations={("test", "COMPLETE"): station},
        )
        self.assertEqual(payload["observation_count"], 2)
        self.assertEqual(payload["sample_count"], 2)
        self.assertEqual(
            {sample["metadata"]["observation_id"] for sample in payload["samples"]},
            {"one", "two"},
        )

    def test_short_and_long_fruiting_groups_relate_but_do_not_merge_rows(self) -> None:
        observations = [
            self.observation("one", observed_at="2026-08-01"),
            self.observation("two", observed_at="2026-08-08"),
            self.observation("three", observed_at="2026-08-14"),
            self.observation("other-area", observed_at="2026-08-08", micro_area_id="site_b"),
        ]
        groups_7d = biology_v3.observation_validation_groups(
            observations,
            micro_area_to_area={"site_a": "area", "site_b": "other"},
            max_duration_days=7,
        )
        groups_14d = biology_v3.observation_validation_groups(
            observations,
            micro_area_to_area={"site_a": "area", "site_b": "other"},
            max_duration_days=14,
        )
        self.assertEqual(len(groups_7d), len(observations))
        self.assertEqual(groups_7d[0], groups_7d[1])
        self.assertNotEqual(groups_7d[0], groups_7d[2])
        self.assertEqual(groups_14d[0], groups_14d[2])
        self.assertNotEqual(groups_14d[1], groups_14d[3])

    def test_fixed_gap_never_reads_rain_from_hidden_week(self) -> None:
        station = self.complete_station("COMPLETE")
        rainfall = self.area_rainfall()
        rainfall["daily_rain_idw_mean_mm"][-1] = 99.0
        rainfall["daily_rain_idw_mean_mm"][-6] = 50.0
        sample = biology_v3.build_fixed_gap_7d_biology_v3(
            self.observation("one"),
            area_context=self.area_context(),
            area_rainfall=rainfall,
            stations={("test", "COMPLETE"): station},
        )
        self.assertEqual(sample["metadata"]["cutoff_date"], "2026-08-06")
        self.assertEqual(sample["predictive_features"]["rain_cutoff_0_3d_mm"], 0.0)
        self.assertNotIn(99.0, sample["predictive_features"].values())
        self.assertNotIn(50.0, sample["predictive_features"].values())

    def test_lag_event_keeps_horizon_as_predictor(self) -> None:
        station = self.complete_station("COMPLETE")
        sample = biology_v3.build_lag_event_biology_v3(
            self.observation("one"),
            horizon_days=3,
            area_context=self.area_context(),
            area_rainfall=self.area_rainfall(),
            stations={("test", "COMPLETE"): station},
        )
        self.assertEqual(sample["metadata"]["cutoff_date"], "2026-08-10")
        self.assertEqual(sample["predictive_features"]["horizon_days"], 3.0)
        _matrix, columns = biology_v3.build_biology_v3_X(
            [sample], biology_v3.LAG_EVENT_BIOLOGY_V3_ID
        )
        self.assertIn("horizon_days", columns)


if __name__ == "__main__":
    unittest.main()
