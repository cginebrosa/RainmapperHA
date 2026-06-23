import tempfile
import unittest
from pathlib import Path

import pandas as pd

from rainmapper_core import create_aemet


def observation(station, fint, rain, name="Test Station", lat=41.5, lon=2.1, temp=None, humidity=None):
    return {
        "idema": station,
        "fint": fint,
        "prec": rain,
        "ubi": name,
        "lat": lat,
        "lon": lon,
        "alt": 120.0,
        "ta": temp,
        "hr": humidity,
    }


class CreateAemetTests(unittest.TestCase):
    def test_normalize_observations_keeps_hourly_utc_and_local_fields(self):
        rows = [
            observation("9632X", "2026-06-22T13:00:00+0000", 14.0, name="TUIXENT"),
            observation("BAD", "2026-06-22T13:00:00+0000", None),
        ]

        result = create_aemet.normalize_observations(rows, local_timezone="Europe/Madrid")

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["station_code"], "AEMET:9632X")
        self.assertEqual(row["fint_utc"], "2026-06-22T13:00:00+0000")
        self.assertEqual(row["reading_utc"], "2026-06-22 13:00:00")
        self.assertEqual(row["local_date"], "20260622")
        self.assertEqual(row["local_time"], "15:00:00")
        self.assertEqual(row["rain_mm"], 14.0)
        self.assertTrue(pd.isna(row["temp_celsius"]))
        self.assertTrue(pd.isna(row["humidity_percent"]))

    def test_normalize_observations_keeps_hourly_temperature_and_humidity(self):
        rows = [
            observation(
                "9632X",
                "2026-06-22T13:00:00+0000",
                1.0,
                temp="24,7",
                humidity=68,
            ),
        ]

        result = create_aemet.normalize_observations(rows, local_timezone="Europe/Madrid")

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["temp_celsius"], 24.7)
        self.assertEqual(row["humidity_percent"], 68.0)

    def test_update_hourly_incremental_deduplicates_by_station_and_fint(self):
        existing = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T10:00:00+0000", 1.0),
            observation("9632X", "2026-06-22T11:00:00+0000", 2.0),
        ])
        current = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T11:00:00+0000", 2.5),
            observation("9632X", "2026-06-22T12:00:00+0000", 3.0),
        ])

        result = create_aemet.update_hourly_incremental(current, existing)

        self.assertEqual(len(result), 3)
        rows = {
            row["fint_utc"]: row["rain_mm"]
            for row in result.to_dict(orient="records")
        }
        self.assertEqual(rows["2026-06-22T10:00:00+0000"], 1.0)
        self.assertEqual(rows["2026-06-22T11:00:00+0000"], 2.5)
        self.assertEqual(rows["2026-06-22T12:00:00+0000"], 3.0)

    def test_build_daily_incremental_aggregates_from_full_hourly_history(self):
        morning = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T07:00:00+0000", 1.0),
            observation("9632X", "2026-06-22T08:00:00+0000", 2.0),
        ])
        evening = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T18:00:00+0000", 4.0),
        ])
        hourly = create_aemet.update_hourly_incremental(evening, morning)

        result = create_aemet.build_daily_incremental(hourly)

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["Codi Estació"], "AEMET:9632X")
        self.assertEqual(row["Data Local"], "20260622")
        self.assertEqual(row["Total"], 7.0)
        self.assertEqual(row["Hora Local"], "20:00:00")
        self.assertTrue(pd.isna(row["max_temp_celsius"]))

    def test_build_daily_incremental_aggregates_temperature_and_humidity(self):
        hourly = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T07:00:00+0000", 1.0, temp=18.2, humidity=82),
            observation("9632X", "2026-06-22T08:00:00+0000", 2.0, temp=21.5, humidity=65),
            observation("9632X", "2026-06-22T09:00:00+0000", 0.0, temp=None, humidity=None),
        ])

        result = create_aemet.build_daily_incremental(hourly)

        row = result.iloc[0]
        self.assertEqual(row["max_temp_celsius"], 21.5)
        self.assertEqual(row["min_temp_celsius"], 18.2)
        self.assertEqual(row["max_humidity_percent"], 82.0)
        self.assertEqual(row["min_humidity_percent"], 65.0)

    def test_read_csv_if_exists_adds_new_hourly_weather_columns_to_existing_history(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "Aemet_hourly_incremental.csv"
            pd.DataFrame([
                {
                    "aemet_id": "9632X",
                    "station_code": "AEMET:9632X",
                    "station_name": "TUIXENT",
                    "fint_utc": "2026-06-22T07:00:00+0000",
                    "reading_utc": "2026-06-22 07:00:00",
                    "reading_local": "2026-06-22 09:00:00",
                    "local_date": "20260622",
                    "local_time": "09:00:00",
                    "rain_mm": 1.0,
                    "lat": 41.5,
                    "lon": 2.1,
                    "alt_m": 120.0,
                }
            ]).to_csv(csv_path, index=False)

            result = create_aemet.read_csv_if_exists(csv_path, create_aemet.HOURLY_COLUMNS)

            self.assertIn("temp_celsius", result.columns)
            self.assertIn("humidity_percent", result.columns)
            self.assertTrue(pd.isna(result.iloc[0]["temp_celsius"]))

    def test_station_catalog_preserves_manual_location_fields(self):
        hourly = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T07:00:00+0000", 1.0, name="TUIXENT NEW"),
        ])
        existing = pd.DataFrame([
            {
                "Codi Estació": "AEMET:9632X",
                "aemet_id": "9632X",
                "Estació": "TUIXENT OLD",
                "Comarca": "Alt Urgell",
                "Municipi": "Tuixent",
                "Provincia": "Lleida",
                "Altitud": "",
                "Latitud": 41.5,
                "Longitud": 2.1,
            }
        ])

        result = create_aemet.build_station_catalog(hourly, existing)

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["Estació"], "TUIXENT NEW")
        self.assertEqual(row["Comarca"], "Alt Urgell")
        self.assertEqual(row["Municipi"], "Tuixent")
        self.assertEqual(row["Provincia"], "Lleida")
        self.assertEqual(row["Latitud"], 41.5)

    def test_build_daily_incremental_uses_station_catalog_location(self):
        hourly = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T07:00:00+0000", 1.0),
        ])
        stations = pd.DataFrame([
            {
                "Codi Estació": "AEMET:9632X",
                "aemet_id": "9632X",
                "Estació": "TUIXENT",
                "Comarca": "Alt Urgell",
                "Municipi": "Tuixent",
                "Provincia": "Lleida",
                "Altitud": 120.0,
                "Latitud": 41.5,
                "Longitud": 2.1,
            }
        ])

        result = create_aemet.build_daily_incremental(hourly, stations)

        row = result.iloc[0]
        self.assertEqual(row["Estació"], "TUIXENT")
        self.assertEqual(row["Comarca"], "Alt Urgell")
        self.assertEqual(row["Municipi"], "Tuixent")
        self.assertEqual(row["Provincia"], "Lleida")

    def test_enrich_station_catalog_fills_missing_reverse_geocoding_fields(self):
        stations = pd.DataFrame([
            {
                "Codi Estació": "AEMET:9632X",
                "aemet_id": "9632X",
                "Estació": "TUIXENT",
                "Comarca": "",
                "Municipi": "",
                "Provincia": "",
                "Altitud": 120.0,
                "Latitud": 41.5,
                "Longitud": 2.1,
            }
        ])

        def fake_reverse_geocoder(lat, lon, api_key):
            self.assertEqual(api_key, "gmap-test")
            return {
                "Comarca": "Alt Urgell",
                "Municipi": "Tuixent",
                "Provincia": "Lleida",
            }

        result, enriched_count = create_aemet.enrich_station_catalog(
            stations,
            "gmap-test",
            reverse_geocoder=fake_reverse_geocoder,
        )

        self.assertEqual(enriched_count, 1)
        row = result.iloc[0]
        self.assertEqual(row["Comarca"], "Alt Urgell")
        self.assertEqual(row["Municipi"], "Tuixent")
        self.assertEqual(row["Provincia"], "Lleida")

    def test_enrich_station_catalog_preserves_existing_manual_fields(self):
        stations = pd.DataFrame([
            {
                "Codi Estació": "AEMET:9632X",
                "aemet_id": "9632X",
                "Estació": "TUIXENT",
                "Comarca": "Manual comarca",
                "Municipi": "Manual town",
                "Provincia": "Manual province",
                "Altitud": 120.0,
                "Latitud": 41.5,
                "Longitud": 2.1,
            }
        ])

        def failing_reverse_geocoder(lat, lon, api_key):
            raise AssertionError("Reverse geocoder should not be called for complete stations")

        result, enriched_count = create_aemet.enrich_station_catalog(
            stations,
            "gmap-test",
            reverse_geocoder=failing_reverse_geocoder,
        )

        self.assertEqual(enriched_count, 0)
        row = result.iloc[0]
        self.assertEqual(row["Comarca"], "Manual comarca")
        self.assertEqual(row["Municipi"], "Manual town")
        self.assertEqual(row["Provincia"], "Manual province")

    def test_enrich_station_catalog_does_not_retry_only_for_empty_comarca(self):
        stations = pd.DataFrame([
            {
                "Codi Estació": "AEMET:9632X",
                "aemet_id": "9632X",
                "Estació": "TUIXENT",
                "Comarca": "",
                "Municipi": "Tuixent",
                "Provincia": "Lleida",
                "Altitud": 120.0,
                "Latitud": 41.5,
                "Longitud": 2.1,
            }
        ])

        def failing_reverse_geocoder(lat, lon, api_key):
            raise AssertionError("Reverse geocoder should not be called when town and province are complete")

        result, enriched_count = create_aemet.enrich_station_catalog(
            stations,
            "gmap-test",
            reverse_geocoder=failing_reverse_geocoder,
        )

        self.assertEqual(enriched_count, 0)
        row = result.iloc[0]
        self.assertEqual(row["Municipi"], "Tuixent")
        self.assertEqual(row["Provincia"], "Lleida")
        self.assertEqual(row["Comarca"], "")

    def test_extract_google_metadata_prefers_administrative_municipality_over_plus_code(self):
        result = [
            {
                "types": ["plus_code"],
                "address_components": [
                    {"long_name": "Poligono Industrial de Constantí", "types": ["locality", "political"]},
                    {"long_name": "Tarragona", "types": ["administrative_area_level_2", "political"]},
                ],
            },
            {
                "types": ["airport", "establishment"],
                "address_components": [
                    {"long_name": "Reus", "types": ["locality", "political"]},
                    {"long_name": "Tarragona", "types": ["administrative_area_level_2", "political"]},
                ],
            },
            {
                "types": ["administrative_area_level_4", "political"],
                "address_components": [
                    {"long_name": "Reus", "types": ["administrative_area_level_4", "political"]},
                    {"long_name": "Tarragona", "types": ["administrative_area_level_2", "political"]},
                ],
            },
        ]

        metadata = create_aemet.extract_google_metadata(result)

        self.assertEqual(metadata["municipality"], "Reus")
        self.assertEqual(metadata["province"], "Tarragona")

    def test_station_catalog_discards_location_metadata_when_coordinates_change(self):
        hourly = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T07:00:00+0000", 1.0, lat=42.0, lon=2.5),
        ])
        existing = pd.DataFrame([
            {
                "Codi Estació": "AEMET:9632X",
                "aemet_id": "9632X",
                "Estació": "TUIXENT OLD",
                "Comarca": "Old comarca",
                "Municipi": "Old town",
                "Provincia": "Old province",
                "Altitud": "",
                "Latitud": 41.5,
                "Longitud": 2.1,
            }
        ])

        result = create_aemet.build_station_catalog(hourly, existing)

        row = result.iloc[0]
        self.assertEqual(row["Municipi"], "")
        self.assertEqual(row["Provincia"], "")
        self.assertEqual(row["Comarca"], "")
        self.assertEqual(row["Latitud"], 42.0)

    def test_run_update_writes_expected_csv_files_with_mocked_fetch(self):
        rows = [
            observation("9632X", "2026-06-22T07:00:00+0000", 1.0),
            observation("9632X", "2026-06-22T08:00:00+0000", 2.0),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_fetch = create_aemet.fetch_observations
            create_aemet.fetch_observations = lambda api_key, timeout=30: rows
            try:
                summary = create_aemet.run_update(
                    data_dir=Path(tmp_dir),
                    api_key="test",
                    local_timezone="Europe/Madrid",
                    enrich_stations=False,
                )
            finally:
                create_aemet.fetch_observations = original_fetch

            self.assertEqual(summary["current_hourly_rows"], 2)
            self.assertEqual(summary["daily_incremental_rows"], 1)
            self.assertTrue((Path(tmp_dir) / "Aemet.csv").exists())
            self.assertTrue((Path(tmp_dir) / "Aemet_hourly_incremental.csv").exists())
            self.assertTrue((Path(tmp_dir) / "estacions_aemet.csv").exists())
            self.assertTrue((Path(tmp_dir) / "Aemet_incremental.csv").exists())
            daily = pd.read_csv(Path(tmp_dir) / "Aemet_incremental.csv", decimal=",")
            self.assertEqual(daily.iloc[0]["Total"], 3.0)
            stations = pd.read_csv(Path(tmp_dir) / "estacions_aemet.csv", decimal=",")
            self.assertEqual(stations.iloc[0]["Codi Estació"], "AEMET:9632X")


    def test_run_update_enriches_existing_station_catalog_when_requested(self):
        rows = [
            observation("9632X", "2026-06-22T07:00:00+0000", 1.0),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            existing = pd.DataFrame([
                {
                    "Codi Estació": "AEMET:9632X",
                    "aemet_id": "9632X",
                    "Estació": "TUIXENT OLD",
                    "Comarca": "",
                    "Municipi": "",
                    "Provincia": "",
                    "Altitud": "",
                    "Latitud": "",
                    "Longitud": "",
                }
            ])
            existing.to_csv(data_dir / "estacions_aemet.csv", index=False, decimal=",")

            original_fetch = create_aemet.fetch_observations
            create_aemet.fetch_observations = lambda api_key, timeout=30: rows
            try:
                summary = create_aemet.run_update(
                    data_dir=data_dir,
                    api_key="test",
                    local_timezone="Europe/Madrid",
                    enrich_stations=True,
                    gmap_api_key="gmap-test",
                    reverse_geocoder=lambda lat, lon, api_key: {
                        "Comarca": "Alt Urgell",
                        "Municipi": "Tuixent",
                        "Provincia": "Lleida",
                    },
                )
            finally:
                create_aemet.fetch_observations = original_fetch

            self.assertEqual(summary["enriched_station_rows"], 1)
            stations = pd.read_csv(data_dir / "estacions_aemet.csv", decimal=",")
            self.assertEqual(stations.iloc[0]["Municipi"], "Tuixent")
            daily = pd.read_csv(data_dir / "Aemet_incremental.csv", decimal=",")
            self.assertEqual(daily.iloc[0]["Provincia"], "Lleida")


if __name__ == "__main__":
    unittest.main()
