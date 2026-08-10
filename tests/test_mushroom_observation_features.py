import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_observation_features


class MushroomObservationFeaturesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.weather_path = self.root / "weather.json"
        self.gis_path = self.root / "gis.json"

    def write_inputs(self) -> None:
        self.weather_path.write_text(
            json.dumps(
                {
                    "kind": "mushroom_observation_weather_features",
                    "prediction_target_policy": {
                        "field": "prediction_target",
                        "version": "catalog_prediction_favorable_v1",
                        "mapping": {"normal": 1, "absent": 0},
                    },
                    "rows": [
                        {
                            "observation_id": "obs_1",
                            "species_id": "boletus_test",
                            "observed_at": "2026-07-10",
                            "analysis_result": "present",
                            "prediction_target": "favorable",
                            "flush_abundance": "normal",
                            "month": 7,
                            "season": "summer",
                            "validation_status": "valid",
                            "calibration_use": "include",
                            "source_quality": 1,
                            "latitude": 42.0,
                            "longitude": 2.0,
                            "altitude_m": 700,
                            "weather_source": "meteocat",
                            "weather_station_code": "ST_NEAR",
                            "weather_station_distance_km": 1.2,
                            "weather_station_coverage_days_90d": 90,
                            "rain_1d_mm": 2.5,
                            "rain_7d_mm": 11.0,
                            "rain_14d_mm": 20.0,
                            "rain_21d_mm": 25.0,
                            "rain_30d_mm": 30.0,
                            "rain_60d_mm": 60.0,
                            "rain_90d_mm": 90.0,
                            "temp_min_7d_c": 10.0,
                            "temp_max_7d_c": 24.0,
                            "temp_mean_7d_c": 17.0,
                            "temp_min_14d_c": 9.0,
                            "temp_max_14d_c": 25.0,
                            "temp_mean_14d_c": 17.0,
                            "temp_min_c": 10.0,
                            "temp_max_c": 24.0,
                            "temp_mean_c": 17.0,
                            "humidity_min_7d_pct": 40.0,
                            "humidity_max_7d_pct": 90.0,
                            "humidity_mean_7d_pct": 65.0,
                            "humidity_min_14d_pct": 35.0,
                            "humidity_max_14d_pct": 92.0,
                            "humidity_mean_14d_pct": 64.0,
                            "daily_rain_mm": [0.0, 2.5],
                            "daily_temp_min_c": [9.0, 10.0],
                            "daily_temp_max_c": [22.0, 24.0],
                            "daily_temp_mean_c": [15.5, 17.0],
                            "daily_humidity_min_pct": [42.0, 40.0],
                            "daily_humidity_max_pct": [88.0, 90.0],
                            "daily_humidity_mean_pct": [65.0, 65.0],
                            "humidity_min_pct": 40.0,
                            "humidity_max_pct": 90.0,
                            "humidity_mean_pct": 65.0,
                            "wind_avg_kmh": None,
                            "wind_gust_kmh": None,
                            "wind_direction_deg": None,
                            "data_gaps": ["wind_no_data_7d"],
                            "observed_host_ids": ["host_pinus_sylvestris"],
                            "observed_forest_type_ids": ["forest_montane_pine"],
                            "observed_soil_tendency_ids": ["soil_siliceous"],
                            "observed_habitat_feature_ids": ["feature_mature_forest"],
                            "observed_aspect_ids": ["aspect_N"],
                        },
                        {
                            "observation_id": "obs_2",
                            "species_id": "boletus_test",
                            "observed_at": "2026-07-11",
                            "analysis_result": "absent",
                            "prediction_target": "unfavorable",
                            "flush_abundance": "absent",
                            "data_gaps": [],
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.gis_path.write_text(
            json.dumps(
                {
                    "kind": "mushroom_observation_gis_reconstruction",
                    "results": [
                        {
                            "observation_id": "obs_1",
                            "species_id": "boletus_test",
                            "gaps": [],
                            "gis_context_v0": {
                                "host_ids": ["host_quercus_ilex"],
                                "forest_type_ids": ["forest_holm_oak"],
                                "soil_tendency_ids": ["soil_calcareous"],
                                "habitat_feature_ids": ["feature_open_warm_woodland"],
                                "altitude_m": 705.0,
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_build_observation_features_joins_weather_and_gis_context(self) -> None:
        self.write_inputs()

        payload = mushroom_observation_features.build_observation_features_v0(
            weather_features_path=self.weather_path,
            gis_reconstruction_path=self.gis_path,
        )
        rows = payload["rows"]
        first = next(row for row in rows if row["observation_id"] == "obs_1")
        second = next(row for row in rows if row["observation_id"] == "obs_2")

        self.assertEqual(payload["summary"]["observations"], 2)
        self.assertEqual(payload["summary"]["with_gis"], 1)
        self.assertEqual(first["month"], 7)
        self.assertEqual(first["season"], "summer")
        self.assertEqual(first["rain_7d_mm"], 11.0)
        self.assertEqual(first["temp_min_14d_c"], 9.0)
        self.assertEqual(first["humidity_max_14d_pct"], 92.0)
        self.assertEqual(first["daily_rain_mm"], [0.0, 2.5])
        self.assertEqual(first["daily_temp_mean_c"], [15.5, 17.0])
        self.assertEqual(second["daily_rain_mm"], [])
        self.assertEqual(first["host_ids"], ["host_pinus_sylvestris", "host_quercus_ilex"])
        self.assertEqual(
            first["host_sources"],
            {"host_pinus_sylvestris": ["field"], "host_quercus_ilex": ["gis"]},
        )
        self.assertEqual(first["forest_type_ids"], ["forest_montane_pine", "forest_holm_oak"])
        self.assertEqual(first["forest_type_sources"], {"forest_montane_pine": ["field"], "forest_holm_oak": ["gis"]})
        self.assertEqual(first["soil_tendency_ids"], ["soil_siliceous", "soil_calcareous"])
        self.assertEqual(first["soil_tendency_sources"], {"soil_siliceous": ["field"], "soil_calcareous": ["gis"]})
        self.assertEqual(first["habitat_feature_ids"], ["feature_mature_forest", "feature_open_warm_woodland"])
        self.assertEqual(first["habitat_feature_sources"], {"feature_mature_forest": ["field"], "feature_open_warm_woodland": ["gis"]})
        self.assertEqual(first["aspect_ids"], ["aspect_N"])
        self.assertEqual(first["aspect_sources"], {"aspect_N": ["field"]})
        self.assertEqual(first["gis_altitude_m"], 705.0)
        self.assertEqual(first["weather_gaps"], ["wind_no_data_7d"])
        self.assertEqual(first["feature_gaps"], [])
        self.assertEqual(first["prediction_target"], "favorable")
        self.assertEqual(second["analysis_result"], "absent")
        self.assertEqual(second["prediction_target"], "unfavorable")
        self.assertEqual(payload["prediction_target_policy"]["field"], "prediction_target")
        self.assertIn("missing_gis_reconstruction", second["feature_gaps"])

    def test_build_and_write_observation_features_outputs_files(self) -> None:
        self.write_inputs()
        output_json = self.root / "out" / "features.json"
        output_csv = self.root / "out" / "features.csv"
        report = self.root / "out" / "features.md"
        progress: list[tuple[int, str]] = []

        payload = mushroom_observation_features.build_and_write_observation_features_v0(
            weather_features_path=self.weather_path,
            gis_reconstruction_path=self.gis_path,
            output_json_path=output_json,
            output_csv_path=output_csv,
            report_path=report,
            progress_callback=lambda percent, message: progress.append((percent, message)),
        )

        self.assertTrue(output_json.exists())
        self.assertTrue(output_csv.exists())
        self.assertTrue(report.exists())
        self.assertEqual(json.loads(output_json.read_text(encoding="utf-8"))["output_paths"]["report"], str(report))
        self.assertIn("host_quercus_ilex", output_csv.read_text(encoding="utf-8"))
        self.assertIn("Mushroom Observation Features v0", report.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["with_weather_gaps"], 1)
        self.assertEqual(100, progress[-1][0])
        self.assertEqual([item[0] for item in progress], sorted(item[0] for item in progress))
        self.assertTrue(any("Uniendo features" in message for _percent, message in progress))
        self.assertTrue(any("CSV" in message for _percent, message in progress))


if __name__ == "__main__":
    unittest.main()
