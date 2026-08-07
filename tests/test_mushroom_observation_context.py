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


class StationCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name)

    def _write_parquet(self) -> None:
        import pandas as pd
        rows = [
            {"source": "meteocat", "station_code": "ST_A", "station_name": "Alpha",
             "local_date": "20260101", "lat": 42.0, "lon": 2.0, "altitude": 800.0,
             "rain_mm": 1.0, "max_temp_celsius": None, "min_temp_celsius": None,
             "max_humidity_percent": None, "min_humidity_percent": None,
             "wind_avg_kmh": None, "wind_gust_kmh": None},
            {"source": "meteocat", "station_code": "ST_A", "station_name": "Alpha",
             "local_date": "20260102", "lat": 42.0, "lon": 2.0, "altitude": 800.0,
             "rain_mm": 2.0, "max_temp_celsius": None, "min_temp_celsius": None,
             "max_humidity_percent": None, "min_humidity_percent": None,
             "wind_avg_kmh": None, "wind_gust_kmh": None},
            {"source": "wunderground", "station_code": "ST_B", "station_name": "Beta",
             "local_date": "20260101", "lat": 43.0, "lon": 3.0, "altitude": 500.0,
             "rain_mm": 0.5, "max_temp_celsius": None, "min_temp_celsius": None,
             "max_humidity_percent": None, "min_humidity_percent": None,
             "wind_avg_kmh": None, "wind_gust_kmh": None},
        ]
        pd.DataFrame(rows).to_parquet(self.data_dir / "weather_daily.parquet", index=False)

    def test_generate_catalog_produces_one_row_per_station(self) -> None:
        self._write_parquet()
        catalog_path = mushroom_observation_context.generate_stations_catalog_parquet(self.data_dir)
        self.assertIsNotNone(catalog_path)
        import pandas as pd
        df = pd.read_parquet(catalog_path)
        self.assertEqual(len(df), 2)
        codes = set(df["station_code"])
        self.assertIn("ST_A", codes)
        self.assertIn("ST_B", codes)

    def test_generate_weather_parquet_uses_filterable_row_groups(self) -> None:
        import pandas as pd
        import pyarrow.parquet as pq

        rows = [
            {
                "Codi Estació": "ST_A" if index < 300 else "ST_B",
                "Estació": "Alpha" if index < 300 else "Beta",
                "Data Local": f"2026{(index % 12) + 1:02d}{(index % 28) + 1:02d}",
                "Latitud": "42.0",
                "Longitud": "2.0",
                "Total": "1.0",
            }
            for index in range(513)
        ]
        pd.DataFrame(rows).to_csv(
            self.data_dir / "Meteocat_incremental.csv",
            index=False,
        )

        output_path = mushroom_observation_context.generate_weather_daily_parquet(
            self.data_dir
        )

        self.assertEqual(output_path, self.data_dir / "weather_daily.parquet")
        metadata = pq.ParquetFile(output_path).metadata
        self.assertEqual(metadata.num_rows, 513)
        self.assertEqual(metadata.num_row_groups, 2)
        self.assertFalse(list(self.data_dir.glob(".weather_daily.parquet.*.tmp")))

    def test_generate_catalog_returns_none_when_no_parquet(self) -> None:
        result = mushroom_observation_context.generate_stations_catalog_parquet(self.data_dir)
        self.assertIsNone(result)

    def test_load_catalog_returns_dataframe(self) -> None:
        self._write_parquet()
        mushroom_observation_context.generate_stations_catalog_parquet(self.data_dir)
        df = mushroom_observation_context.load_stations_catalog(self.data_dir)
        self.assertFalse(df.empty)
        self.assertIn("station_code", df.columns)
        self.assertIn("lat", df.columns)
        self.assertIn("lon", df.columns)

    def test_load_catalog_bootstraps_from_existing_daily_parquet(self) -> None:
        self._write_parquet()
        catalog_path = self.data_dir / "weather_stations_catalog.parquet"
        self.assertFalse(catalog_path.exists())

        df = mushroom_observation_context.load_stations_catalog(self.data_dir)

        self.assertTrue(catalog_path.exists())
        self.assertEqual(set(df["station_code"]), {"ST_A", "ST_B"})

    def test_load_catalog_returns_empty_when_no_file(self) -> None:
        df = mushroom_observation_context.load_stations_catalog(self.data_dir)
        self.assertTrue(df.empty)

    def test_nearest_station_codes_returns_closest_within_radius(self) -> None:
        self._write_parquet()
        mushroom_observation_context.generate_stations_catalog_parquet(self.data_dir)
        catalog = mushroom_observation_context.load_stations_catalog(self.data_dir)
        # ST_A is at (42.0, 2.0) — very close; ST_B is at (43.0, 3.0) — ~140 km away
        results = mushroom_observation_context.nearest_station_codes(
            catalog, lat=42.01, lon=2.01, max_km=15.0, top_n=5
        )
        self.assertEqual(len(results), 1)
        self.assertIn(("meteocat", "ST_A"), results)

    def test_nearest_station_codes_respects_top_n(self) -> None:
        self._write_parquet()
        mushroom_observation_context.generate_stations_catalog_parquet(self.data_dir)
        catalog = mushroom_observation_context.load_stations_catalog(self.data_dir)
        # Both stations within 1000 km — top_n=1 should return only the nearest
        results = mushroom_observation_context.nearest_station_codes(
            catalog, lat=42.01, lon=2.01, max_km=1000.0, top_n=1
        )
        self.assertEqual(len(results), 1)
        self.assertIn(("meteocat", "ST_A"), results)

    def test_nearest_station_codes_empty_catalog(self) -> None:
        import pandas as pd
        empty = pd.DataFrame(columns=["source", "station_code", "lat", "lon"])
        results = mushroom_observation_context.nearest_station_codes(empty, 42.0, 2.0)
        self.assertEqual(results, [])

    def test_station_filter_excludes_other_stations(self) -> None:
        self._write_parquet()
        original_read_parquet = mushroom_observation_context.pd.read_parquet
        with mock.patch.object(
            mushroom_observation_context.pd,
            "read_parquet",
            side_effect=original_read_parquet,
        ) as read_parquet:
            stations = mushroom_observation_context.load_daily_weather_parquet(
                self.data_dir,
                station_filter={("meteocat", "ST_A")},
            )
        self.assertIn(("meteocat", "ST_A"), stations)
        self.assertNotIn(("wunderground", "ST_B"), stations)
        self.assertEqual(
            read_parquet.call_args.kwargs["filters"],
            [[("source", "==", "meteocat"), ("station_code", "==", "ST_A")]],
        )

    def test_empty_station_filter_does_not_read_parquet(self) -> None:
        self._write_parquet()
        with mock.patch.object(
            mushroom_observation_context.pd, "read_parquet"
        ) as read_parquet:
            stations = mushroom_observation_context.load_daily_weather_parquet(
                self.data_dir,
                station_filter=set(),
            )
        self.assertEqual(stations, {})
        read_parquet.assert_not_called()

    def test_filtered_load_rejects_legacy_monolithic_parquet(self) -> None:
        import pandas as pd

        rows = [
            {
                "source": "meteocat",
                "station_code": "ST_A",
                "station_name": "Alpha",
                "local_date": "20260101",
                "lat": 42.0,
                "lon": 2.0,
            }
            for _index in range(513)
        ]
        pd.DataFrame(rows).to_parquet(
            self.data_dir / "weather_daily.parquet",
            index=False,
        )

        with mock.patch.object(
            mushroom_observation_context.pd, "read_parquet"
        ) as read_parquet, self.assertRaises(
            mushroom_observation_context.WeatherParquetLayoutError
        ):
            mushroom_observation_context.load_daily_weather_parquet(
                self.data_dir,
                station_filter={("meteocat", "ST_A")},
            )
        read_parquet.assert_not_called()

    def test_filtered_predictor_does_not_fall_back_to_all_csvs(self) -> None:
        with mock.patch.object(
            mushroom_observation_context,
            "_load_daily_weather_from_csv",
        ) as csv_loader:
            stations = mushroom_observation_context.load_daily_weather_parquet(
                self.data_dir,
                station_filter={("meteocat", "ST_A")},
            )
        self.assertEqual(stations, {})
        csv_loader.assert_not_called()

    def test_station_filter_none_loads_all_stations(self) -> None:
        self._write_parquet()
        stations = mushroom_observation_context.load_daily_weather_parquet(
            self.data_dir,
            station_filter=None,
        )
        self.assertIn(("meteocat", "ST_A"), stations)
        self.assertIn(("wunderground", "ST_B"), stations)


if __name__ == "__main__":
    unittest.main()
