import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_observation_context


class MushroomObservationContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.data_dir = self.root / "Data"
        self.data_dir.mkdir()
        self.observations_path = self.root / "mushroom_observations.json"

    def write_daily_file(self, filename: str, rows: list[dict[str, object]]) -> None:
        fields = [
            "Codi Estació",
            "Data Lectura",
            "Estació",
            "Comarca",
            "Municipi",
            "Provincia",
            "Altitud",
            "Latitud",
            "Longitud",
            "Ultima Lectura",
            "Variable",
            "Total",
            "Unitat",
            "Data Local",
            "Hora Local",
            "max_temp_celsius",
            "min_temp_celsius",
            "max_humidity_percent",
            "min_humidity_percent",
            "wind_avg_kmh",
            "wind_gust_kmh",
            "wind_direction_deg",
        ]
        path = self.data_dir / filename
        path.write_text(
            ",".join(fields)
            + "\n"
            + "\n".join(
                ",".join(str(row.get(field, "")) for field in fields)
                for row in rows
            )
            + "\n",
            encoding="utf-8",
        )

    def write_observations(self) -> None:
        self.observations_path.write_text(
            json.dumps(
                {
                    "observations": [
                        {
                            "observation_id": "obs_1",
                            "species_id": "boletus_test",
                            "observed_at": "2026-07-10",
                            "location": {"lat": 42.0, "lon": 2.0},
                            "altitude": {"meters": 700},
                            "flush_abundance": "normal",
                            "validation_status": "valid",
                            "calibration_use": "include",
                            "source_quality": 1,
                            "site_context": {
                                "observed_host_ids": ["host_pinus_sylvestris"],
                                "observed_forest_type_ids": ["forest_montane_pine"],
                                "observed_soil_tendency_ids": ["soil_siliceous"],
                                "observed_habitat_feature_ids": ["feature_mature_forest"],
                                "observed_aspect_ids": ["aspect_N"],
                            },
                        },
                        {
                            "observation_id": "obs_2",
                            "species_id": "boletus_test",
                            "observed_at": "2020-07-10",
                            "location": {"lat": 39.0, "lon": 0.0},
                            "flush_abundance": "absent",
                            "validation_status": "valid",
                            "calibration_use": "include",
                            "source_quality": 1,
                            "site_context": {},
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_default_observations_path_prefers_persistent_share_file(self) -> None:
        share_path = Path("/share/rainmapper/mushroom-data/mushroom_observations.json")

        def fake_exists(path: Path) -> bool:
            return str(path) == str(share_path)

        with mock.patch.dict(
            "os.environ",
            {"RAINMAPPER_MUSHROOM_OBSERVATIONS_PATH": "", "RAINMAPPER_SHARE_ROOT": "/share/rainmapper"},
            clear=False,
        ), \
            mock.patch.object(Path, "exists", fake_exists):
            self.assertEqual(mushroom_observation_context.default_observations_path(), share_path)

    def test_prediction_target_uses_operational_flush_threshold(self) -> None:
        policy = mushroom_observation_context.load_prediction_target_policy()
        for abundance in ("normal", "abundant", "very_abundant", "exceptional"):
            self.assertEqual(mushroom_observation_context.prediction_target(abundance, policy), "favorable")
        for abundance in ("scarce", "very_scarce", "absent"):
            self.assertEqual(mushroom_observation_context.prediction_target(abundance, policy), "unfavorable")
        self.assertEqual(mushroom_observation_context.prediction_target("", policy), "unknown")
        self.assertEqual(policy["mapping"]["scarce"], 0)

    def test_prediction_target_policy_rejects_catalog_without_binary_flag(self) -> None:
        catalogs_path = self.root / "catalogs.json"
        catalogs_path.write_text(
            json.dumps({"catalogs": {"observation_flush_abundance": [{"id": "normal"}]}}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "prediction_favorable must be integer 0 or 1"):
            mushroom_observation_context.load_prediction_target_policy(catalogs_path)

    def test_build_weather_features_uses_nearest_available_station_and_reports_gaps(self) -> None:
        self.write_observations()
        self.write_daily_file(
            "Meteocat_incremental.csv",
            [
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260710",
                    "Total": "2.5",
                    "max_temp_celsius": "24",
                    "min_temp_celsius": "12",
                    "max_humidity_percent": "90",
                    "min_humidity_percent": "45",
                    "wind_avg_kmh": "10",
                    "wind_gust_kmh": "30",
                    "wind_direction_deg": "90",
                },
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260709",
                    "Total": "1.5",
                    "max_temp_celsius": "20",
                    "min_temp_celsius": "10",
                    "max_humidity_percent": "80",
                    "min_humidity_percent": "40",
                    "wind_avg_kmh": "20",
                    "wind_gust_kmh": "35",
                    "wind_direction_deg": "90",
                },
                {
                    "Codi Estació": "ST_FAR",
                    "Estació": "Far station",
                    "Latitud": "43.0",
                    "Longitud": "3.0",
                    "Data Local": "20260710",
                    "Total": "99",
                },
            ],
        )

        payload = mushroom_observation_context.build_observation_weather_features(
            observations_path=self.observations_path,
            weather_data_dir=self.data_dir,
        )
        rows = payload["rows"]
        first = rows[0]
        second = rows[1]

        self.assertEqual(payload["summary"]["observations"], 2)
        self.assertEqual(first["weather_source"], "meteocat")
        self.assertEqual(first["month"], 7)
        self.assertEqual(first["season"], "summer")
        self.assertEqual(first["weather_station_code"], "ST_NEAR")
        self.assertEqual(first["rain_1d_mm"], 2.5)
        self.assertEqual(first["rain_7d_mm"], 4.0)
        self.assertEqual(first["temp_min_7d_c"], 10.0)
        self.assertEqual(first["temp_max_7d_c"], 24.0)
        self.assertEqual(first["temp_min_14d_c"], 10.0)
        self.assertEqual(first["temp_max_14d_c"], 24.0)
        self.assertEqual(first["temp_min_c"], 10.0)
        self.assertEqual(first["temp_max_c"], 24.0)
        self.assertEqual(first["humidity_min_7d_pct"], 40.0)
        self.assertEqual(first["humidity_max_7d_pct"], 90.0)
        self.assertEqual(first["humidity_min_14d_pct"], 40.0)
        self.assertEqual(first["humidity_max_14d_pct"], 90.0)
        self.assertEqual(first["wind_avg_kmh"], 15.0)
        self.assertEqual(first["wind_gust_kmh"], 35.0)
        self.assertEqual(first["wind_direction_deg"], 90.0)
        self.assertIn("rain_7d_coverage_2/7", first["data_gaps"])
        self.assertEqual(first["observed_host_ids"], ["host_pinus_sylvestris"])
        self.assertEqual(first["observed_forest_type_ids"], ["forest_montane_pine"])
        self.assertEqual(first["observed_soil_tendency_ids"], ["soil_siliceous"])
        self.assertEqual(first["observed_habitat_feature_ids"], ["feature_mature_forest"])
        self.assertEqual(first["observed_aspect_ids"], ["aspect_N"])
        self.assertEqual(first["prediction_target"], "favorable")
        self.assertEqual(second["analysis_result"], "absent")
        self.assertEqual(second["prediction_target"], "unfavorable")
        self.assertEqual(payload["prediction_target_policy"]["version"], "catalog_prediction_favorable_v1")
        self.assertEqual(payload["prediction_target_policy"]["mapping"]["scarce"], 0)
        self.assertIn("no_weather_station_with_90d_coverage", second["data_gaps"])

    def test_build_weather_features_excludes_suspect_daily_rain(self) -> None:
        self.write_observations()
        self.write_daily_file(
            "Wunderground_incremental.csv",
            [
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260710",
                    "Total": "2.5",
                },
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260709",
                    "Total": "955.29",
                },
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260708",
                    "Total": "1.5",
                },
            ],
        )

        payload = mushroom_observation_context.build_observation_weather_features(
            observations_path=self.observations_path,
            weather_data_dir=self.data_dir,
        )
        first = payload["rows"][0]

        self.assertEqual(first["rain_7d_mm"], 4.0)
        self.assertIn("rain_7d_coverage_2/7", first["data_gaps"])
        self.assertIn("rain_suspect_daily_20260709_955.29mm", first["data_gaps"])

    def test_build_and_write_weather_features_outputs_json_csv_and_report(self) -> None:
        self.write_observations()
        self.write_daily_file(
            "Meteocat_incremental.csv",
            [
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260710",
                    "Total": "2.5",
                }
            ],
        )
        output_json = self.root / "out" / "features.json"
        output_csv = self.root / "out" / "features.csv"
        report = self.root / "out" / "features.md"
        progress: list[tuple[int, str]] = []

        payload = mushroom_observation_context.build_and_write_observation_weather_features(
            observations_path=self.observations_path,
            weather_data_dir=self.data_dir,
            output_json_path=output_json,
            output_csv_path=output_csv,
            report_path=report,
            progress_callback=lambda percent, message: progress.append((percent, message)),
        )

        self.assertTrue(output_json.exists())
        self.assertTrue(output_csv.exists())
        self.assertTrue(report.exists())
        self.assertEqual(json.loads(output_json.read_text(encoding="utf-8"))["output_paths"]["csv"], str(output_csv))
        self.assertIn("obs_1", output_csv.read_text(encoding="utf-8"))
        self.assertIn("Mushroom Observation Weather Features", report.read_text(encoding="utf-8"))
        self.assertEqual(payload["output_paths"]["report"], str(report))
        self.assertEqual(100, progress[-1][0])
        self.assertEqual([item[0] for item in progress], sorted(item[0] for item in progress))
        self.assertTrue(any("observaciones" in message for _percent, message in progress))
        self.assertTrue(any("CSV" in message for _percent, message in progress))


    def test_build_weather_features_nullifies_consecutive_duplicate_rain(self) -> None:
        self.write_observations()
        # Day 10 (obs day): real data
        # Day 9: real rain 8.0mm
        # Day 8: exact duplicate of day 9 → artifact, should be nullified
        # Day 7: different value → real
        self.write_daily_file(
            "Wunderground_incremental.csv",
            [
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260710",
                    "Total": "3.0",
                },
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260709",
                    "Total": "8.0",
                },
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260708",
                    "Total": "8.0",
                },
                {
                    "Codi Estació": "ST_NEAR",
                    "Estació": "Near station",
                    "Latitud": "42.01",
                    "Longitud": "2.01",
                    "Data Local": "20260707",
                    "Total": "2.0",
                },
            ],
        )

        payload = mushroom_observation_context.build_observation_weather_features(
            observations_path=self.observations_path,
            weather_data_dir=self.data_dir,
        )
        first = payload["rows"][0]

        # rain_7d should be 3.0 + 8.0 + 2.0 = 13.0 (day 8 nullified, day 7 kept)
        self.assertEqual(first["rain_7d_mm"], 13.0)
        # gap reported for the duplicate day (day 9 repeats day 8 → day 9 is the artifact)
        self.assertTrue(
            any("rain_suspect_consecutive_20260709" in g for g in first["data_gaps"]),
            f"Expected consecutive gap in {first['data_gaps']}",
        )
        # coverage reduced: 3 valid rain days out of 7
        self.assertTrue(
            any("rain_7d_coverage_3/7" in g for g in first["data_gaps"]),
            f"Expected coverage gap in {first['data_gaps']}",
        )


if __name__ == "__main__":
    unittest.main()
