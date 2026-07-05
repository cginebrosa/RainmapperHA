import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from rainmapper_core import create_aemet


def observation(station, fint, rain, name="Test Station", lat=41.5, lon=2.1, temp=None, humidity=None, **extra):
    row = {
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
    row.update(extra)
    return row


class CreateAemetTests(unittest.TestCase):
    def test_rate_limit_metrics_keep_last_24h_and_consecutive_runs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir)
            now = datetime(2026, 6, 24, 12, 0, 0)
            old_event = (now - timedelta(hours=25)).isoformat(timespec="seconds")
            recent_event = (now - timedelta(hours=2)).isoformat(timespec="seconds")
            create_aemet.write_rate_limit_metrics(
                data_dir,
                {
                    "updated_at": old_event,
                    "events": [old_event, recent_event],
                    "rate_limit_24h": 2,
                    "consecutive_429_runs": 3,
                },
            )

            status = create_aemet.rate_limit_status(data_dir, now=now)

            self.assertEqual(status["rate_limit_24h"], 1)
            self.assertEqual(status["consecutive_429_runs"], 3)

            status = create_aemet.record_rate_limit_result(data_dir, rate_limited=True, now=now)

            self.assertEqual(status["rate_limit_24h"], 2)
            self.assertEqual(status["consecutive_429_runs"], 4)

            status = create_aemet.record_rate_limit_result(
                data_dir,
                rate_limited=False,
                now=now + timedelta(minutes=10),
            )

            self.assertEqual(status["rate_limit_24h"], 2)
            self.assertEqual(status["consecutive_429_runs"], 0)

    def test_fetch_observations_labels_index_and_data_url_with_delay(self):
        calls = []
        sleeps = []
        original_fetch_json = create_aemet.fetch_json
        original_sleep = create_aemet.time.sleep

        def fake_fetch_json(url, api_key=None, timeout=30, request_label="AEMET request"):
            calls.append((url, api_key, timeout, request_label))
            if request_label == "observations index endpoint":
                return {"estado": 200, "datos": "https://example.test/aemet-data"}
            return [{"idema": "0002I", "fint": "2026-06-24T08:00:00+0000", "prec": 0.0}]

        try:
            create_aemet.fetch_json = fake_fetch_json
            create_aemet.time.sleep = lambda seconds: sleeps.append(seconds)

            rows = create_aemet.fetch_observations(
                api_key="test-key",
                timeout=12,
                data_url_delay_seconds=1.5,
            )
        finally:
            create_aemet.fetch_json = original_fetch_json
            create_aemet.time.sleep = original_sleep

        self.assertEqual(rows[0]["idema"], "0002I")
        self.assertEqual(sleeps, [1.5])
        self.assertEqual(calls[0][3], "observations index endpoint")
        self.assertEqual(calls[0][1], "test-key")
        self.assertEqual(calls[0][2], 12)
        self.assertEqual(calls[1][0], "https://example.test/aemet-data")
        self.assertEqual(calls[1][1], None)
        self.assertEqual(calls[1][3], "observations data URL")

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

    def test_normalize_observations_keeps_hourly_wind_fields(self):
        rows = [
            observation(
                "0002I",
                "2026-06-23T15:00:00+0000",
                0.0,
                vv=1.9,
                vmax=4.2,
                dv=84.0,
                dmax=96.0,
            ),
        ]

        result = create_aemet.normalize_observations(rows, local_timezone="Europe/Madrid")

        row = result.iloc[0]
        self.assertEqual(row["wind_avg_kmh"], 6.8)
        self.assertEqual(row["wind_min_kmh"], 6.8)
        self.assertEqual(row["wind_max_kmh"], 6.8)
        self.assertEqual(row["wind_gust_kmh"], 15.1)
        self.assertEqual(row["wind_direction_deg"], 84.0)
        self.assertEqual(row["wind_gust_direction_deg"], 96.0)
        self.assertEqual(row["wind_observation_count"], 1)

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

    def test_build_daily_incremental_handles_csv_and_current_local_date_types(self):
        existing = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T07:00:00+0000", 1.0),
            observation("9632X", "2026-06-22T08:00:00+0000", 2.0),
        ])
        existing["local_date"] = existing["local_date"].astype(int)
        current = create_aemet.normalize_observations([
            observation("9632X", "2026-06-22T18:00:00+0000", 4.0),
        ])

        hourly = create_aemet.update_hourly_incremental(current, existing)
        result = create_aemet.build_daily_incremental(hourly)

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["Codi Estació"], "AEMET:9632X")
        self.assertEqual(row["Data Local"], "20260622")
        self.assertEqual(row["Total"], 7.0)
        self.assertEqual(row["Hora Local"], "20:00:00")

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

    def test_build_daily_incremental_aggregates_hourly_wind(self):
        hourly = create_aemet.normalize_observations([
            observation("0002I", "2026-06-23T15:00:00+0000", 0.0, vv=1.0, vmax=4.0, dv=350.0, dmax=10.0),
            observation("0002I", "2026-06-23T16:00:00+0000", 0.0, vv=2.0, vmax=5.0, dv=10.0, dmax=20.0),
            observation("0002I", "2026-06-23T17:00:00+0000", 0.0, vv=None, vmax=None, dv=None, dmax=None),
        ])

        result = create_aemet.build_daily_incremental(hourly)

        row = result.iloc[0]
        self.assertEqual(row["wind_avg_kmh"], 5.4)
        self.assertEqual(row["wind_min_kmh"], 3.6)
        self.assertEqual(row["wind_max_kmh"], 7.2)
        self.assertEqual(row["wind_gust_kmh"], 18.0)
        self.assertEqual(row["wind_direction_deg"], 0.0)
        self.assertEqual(row["wind_gust_direction_deg"], 15.0)
        self.assertEqual(row["wind_observation_count"], 2)

    def test_merge_daily_incremental_preserves_manual_backfill_days(self):
        backfill_row = {
            "Codi Estació": "AEMET:0002I",
            "Data Lectura": "2026-05-25 23:59:00",
            "Estació": "VANDELLOS",
            "Comarca": "",
            "Municipi": "Vandellos",
            "Provincia": "Tarragona",
            "Altitud": 32.0,
            "Latitud": 40.95806,
            "Longitud": 0.871385,
            "Ultima Lectura": "2026/05/25 23:59:00",
            "Variable": "Precipitacion",
            "Total": 12.3,
            "Unitat": "mm",
            "Data Local": "20260525",
            "Hora Local": "23:59:00",
        }
        existing_daily = pd.DataFrame([backfill_row])
        current_daily = create_aemet.build_daily_incremental(create_aemet.normalize_observations([
            observation("0002I", "2026-06-23T15:00:00+0000", 1.0),
        ]))

        result = create_aemet.merge_daily_incremental(current_daily, existing_daily)

        dates = set(result["Data Local"])
        self.assertIn("20260525", dates)
        self.assertIn("20260623", dates)
        self.assertEqual(result[result["Data Local"] == "20260525"].iloc[0]["Total"], 12.3)

    def test_merge_daily_incremental_replaces_existing_same_station_day(self):
        existing_daily = pd.DataFrame([
            {
                "Codi Estació": "AEMET:0002I",
                "Data Lectura": "2026-06-23 12:00:00",
                "Total": 1.0,
                "Data Local": 20260623,
            }
        ])
        current_daily = create_aemet.build_daily_incremental(create_aemet.normalize_observations([
            observation("0002I", "2026-06-23T15:00:00+0000", 4.0),
        ]))

        result = create_aemet.merge_daily_incremental(current_daily, existing_daily)

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["Data Local"], "20260623")
        self.assertEqual(row["Total"], 4.0)

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
            self.assertIn("wind_avg_kmh", result.columns)
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
            for key in (
                "fetch_seconds",
                "normalize_seconds",
                "read_hourly_seconds",
                "merge_hourly_seconds",
                "read_stations_seconds",
                "station_catalog_seconds",
                "station_enrichment_seconds",
                "build_daily_seconds",
                "read_daily_seconds",
                "merge_daily_seconds",
                "write_outputs_seconds",
                "total_seconds",
            ):
                self.assertIn(key, summary["timings"])
                self.assertIsInstance(summary["timings"][key], float)
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
