import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from rainmapper_core import create_aemet as aemet, aemet_station_inventory as inventory
from rainmapper_core import weather_official_backfill as official
from rainmapper_core import weather_coordinates as coordinates
from rainmapper_core.weather_history_archive import archive_and_close_pending
from rainmapper_core.weather_history_capture import capture_fresh_weather_rows
from rainmapper_core.weather_history_dataset import read_weather_history
from tests.test_create_aemet import observation


NOW = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)


def inventory_row(code="0158O", lat="413540N", lon="015021E"):
    return {"indicativo": code, "nombre": "MONTSERRAT", "provincia": "BARCELONA",
            "altitud": "738", "latitud": lat, "longitud": lon}


class AemetStationInventoryTests(unittest.TestCase):
    def test_absent_null_text_rain_keeps_coordinates_and_other_measurements(self):
        for rain in (None, "", "Ip", "Acum", True, -1, float("nan"), float("inf")):
            with self.subTest(rain=rain):
                row = observation("9677", "2026-10-28T23:00:00+0000", rain, temp=7, humidity=80)
                frame = aemet.normalize_observations([row])
                self.assertEqual(len(frame), 1)
                self.assertTrue(pd.isna(frame.iloc[0]["rain_mm"]))
                daily = aemet.build_daily_incremental(frame)
                self.assertEqual(daily["Data Local"].tolist(), ["20261029"])
                self.assertTrue(pd.isna(daily.iloc[0]["Total"]))
                self.assertEqual(daily.iloc[0]["max_temp_celsius"], 7)
                self.assertEqual(daily.iloc[0]["Latitud"], 41.5)
        row.pop("prec")
        self.assertTrue(pd.isna(aemet.normalize_observations([row]).iloc[0]["rain_mm"]))
        metadata_only = observation("9677", "2026-10-28T23:00:00+0000", None)
        hourly = aemet.normalize_observations([metadata_only])
        self.assertEqual(len(aemet.build_station_catalog(hourly)), 1)
        self.assertTrue(aemet.build_daily_incremental(hourly).empty)

    def test_missing_new_rain_preserves_previous_hour_but_explicit_zero_wins(self):
        old = aemet.normalize_observations([observation("9677", "2026-10-29T10:00:00+0000", 2.3, temp=10)])
        new = aemet.normalize_observations([observation("9677", "2026-10-29T10:00:00+0000", None, temp=11)])
        merged = aemet.update_hourly_incremental(new, old)
        self.assertEqual(merged.iloc[0]["rain_mm"], 2.3)
        self.assertEqual(merged.iloc[0]["temp_celsius"], 11)
        new["rain_mm"] = 0
        self.assertEqual(aemet.update_hourly_incremental(new, old).iloc[0]["rain_mm"], 0)

    def test_inventory_bounds_and_dms_validation(self):
        self.assertAlmostEqual(inventory.parse_coordinate("413540N", latitude=True), 41.594444)
        self.assertAlmostEqual(inventory.parse_coordinate("015356W", latitude=False), -1.898889)
        for raw in (None, "", "416000N", "415960N", "910000N", "413540E", "NaN"):
            self.assertIsNone(inventory.parse_coordinate(raw, latitude=True))
        rows = [inventory_row()]
        with mock.patch.object(aemet, "fetch_json", side_effect=[
                {"estado": 200, "datos": "https://opendata.aemet.es/opendata/sh/test"}, rows]) as fetch:
            self.assertEqual(inventory.fetch_inventory("secret"), rows)
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(fetch.call_args_list[1].kwargs["max_response_bytes"], inventory.MAX_BYTES)
            self.assertEqual(fetch.call_args_list[0].kwargs["deadline"], fetch.call_args_list[1].kwargs["deadline"])
            self.assertNotIn("api_key", fetch.call_args_list[1].kwargs)
        for response in ({"estado": 404}, {"estado": 200, "datos": "https://example.test/data"}):
            with mock.patch.object(aemet, "fetch_json", return_value=response) as fetch:
                with self.assertRaises(ValueError):
                    inventory.fetch_inventory("secret")
                self.assertEqual(fetch.call_count, 1)
        with mock.patch.object(aemet, "fetch_json", side_effect=[
                {"estado": 200, "datos": "https://opendata.aemet.es/opendata/sh/test"}, rows * (inventory.MAX_STATIONS + 1)]):
            with self.assertRaises(ValueError):
                inventory.fetch_inventory("secret")

    def test_inventory_failure_preserves_catalog_and_foreign_location_is_not_accepted(self):
        catalog = aemet.build_station_catalog(aemet.normalize_observations([
            observation("9632X", "2026-10-29T10:00:00+0000", 1)]))
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(inventory, "fetch_inventory", side_effect=TimeoutError):
                result, report = inventory.complete_station_catalog(tmp, catalog, {"AEMET:0158O": {}}, api_key="test")
                pd.testing.assert_frame_equal(result, catalog)
                self.assertEqual(report["error"], "TimeoutError")
                self.assertEqual(report["unresolved_stations"], 1)
            with mock.patch.object(inventory, "fetch_inventory", return_value=[inventory_row(lat="493540N")]):
                result, report = inventory.complete_station_catalog(tmp, catalog, {"AEMET:0158O": {}}, api_key="test")
                self.assertEqual(result["Codi Estació"].tolist(), ["AEMET:9632X"])
                self.assertEqual(report["unresolved_stations"], 1)
                self.assertIn(coordinates.station_key("aemet", "AEMET:0158O"), coordinates.read_state(tmp)["exceptions"])

    def test_inventory_outage_keeps_daily_values_and_reports_partial_without_erasing_catalog(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(aemet, "fetch_observations", return_value=[]), \
                mock.patch.object(official, "fetch_aemet_climatology", return_value=[
                    {"indicativo": "0158O", "fecha": "2026-10-25", "prec": "3,2", "nombre": "Montserrat"}]), \
                mock.patch.object(inventory, "fetch_inventory", side_effect=TimeoutError) as fetch:
            p = Path(tmp)
            catalog = aemet.build_station_catalog(aemet.normalize_observations([
                observation("9632X", "2026-10-01T10:00:00+0000", 1)]))
            aemet.write_csv_atomic(catalog, p / "estacions_aemet.csv", decimal=",")
            result = aemet.run_update(p, "test", enrich_stations=False, recovery_now=NOW, retention_reference_day=NOW.date())
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(result["recovery"]["status"], "pending")
            self.assertEqual(result["station_rows"], 1)
            from rainmapper_core.aemet_recovery import status
            self.assertEqual(status(p)["recovery_status"], "pending")
            daily = pd.read_csv(p / "Aemet_incremental.csv", decimal=",")
            self.assertEqual(float(daily["Total"].item()), 3.2)
            self.assertTrue(pd.isna(daily["Latitud"].item()))

    def test_two_runs_archive_missing_rain_and_inventory_locations_without_repeated_enrichment(self):
        rows = [observation("1583X", "2026-10-29T10:00:00+0000", None, lat=42.42, lon=-6.98, temp=11),
                observation("9677", "2026-10-29T10:00:00+0000", None, lat=42.410009, lon=1.214647, temp=7, humidity=80)]
        rows[1].pop("prec")
        daily_rows = [{"indicativo": "0158O", "fecha": "2026-10-25", "nombre": "MONTSERRAT", "prec": "3,2", "tmax": "20"},
                      {"indicativo": "9677", "fecha": "2026-10-25", "nombre": "PORT AINE", "tmax": "15", "hrmax": "90"}]
        geocoder = mock.Mock(return_value={"Municipi": "Town", "Provincia": "Province", "Comarca": "", "Altitud": 999})
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {
                "RAINMAPPER_PARTITIONED_WEATHER_HISTORY": "true", "RAINMAPPER_WEATHER_REFERENCE_DAY": "2026-10-29"}):
            p = Path(tmp)
            from tests.test_weather_history_writer import WeatherHistoryWriterTests
            seed = WeatherHistoryWriterTests()
            seed.data_dir = p; seed.root = p / "weather-history"; seed.root.mkdir()
            seed._write_initial_generation()
            def history():
                return read_weather_history(p, start_date="20250101", end_date="20261029")
            before = history()
            old = aemet.normalize_observations([observation("1583X", "2026-10-29T10:00:00+0000", 2.3, lat=42.42, lon=-6.98)])
            aemet.write_csv_atomic(old, p / "Aemet_hourly_incremental.csv")
            stations = aemet.build_station_catalog(old)
            stations["Municipi"] = "O Barco"; stations["Provincia"] = "Ourense"
            aemet.write_csv_atomic(stations, p / "estacions_aemet.csv", decimal=",")
            # These daily records already exist in history without locations,
            # just like the affected production stations.
            initial_daily = official.normalize_aemet_climatology(daily_rows, stations)
            capture_fresh_weather_rows(p, "aemet", initial_daily)
            archive_and_close_pending(p)
            self.assertEqual(len(coordinates.read_state(p)["exceptions"]), 2)
            moved = [{**rows[0], "lat": 49.42}, rows[1]]
            with mock.patch.object(aemet, "fetch_observations", side_effect=[moved, rows]), \
                    mock.patch.object(official, "fetch_aemet_climatology", return_value=daily_rows), \
                    mock.patch.object(inventory, "fetch_inventory", return_value=[inventory_row(), inventory_row("9677", lat="493540N")]) as fetch:
                first = aemet.run_update(p, "test", reverse_geocoder=geocoder, gmap_api_key="test",
                                         retention_reference_day=NOW.date(), recovery_now=NOW)
                archive_and_close_pending(p)
                stored = history()
                self.assertEqual(set(coordinates.read_state(p)["exceptions"]), {coordinates.station_key("aemet", "AEMET:1583X")})
                self.assertTrue((stored.loc[stored["station_code"] == "AEMET:1583X", "lat"] == 42.42).all())
                catalog_first = aemet.read_csv_if_exists(p / "estacions_aemet.csv", aemet.STATION_COLUMNS, decimal=",")
                second = aemet.run_update(p, "test", reverse_geocoder=geocoder, gmap_api_key="test",
                                          retention_reference_day=NOW.date(), recovery_now=NOW)
                archive_and_close_pending(p)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(first["station_inventory"]["resolved_stations"], 1)
            self.assertEqual(second["station_inventory"]["requested_stations"], 0)
            self.assertEqual(first["enriched_station_rows"], 2)
            self.assertEqual(second["enriched_station_rows"], 0)
            self.assertEqual(geocoder.call_count, 2)
            self.assertFalse(coordinates.read_state(p)["exceptions"])
            pd.testing.assert_frame_equal(stored, history())
            pd.testing.assert_frame_equal(before, stored.loc[stored["source"] != "aemet"].reset_index(drop=True))
            pd.testing.assert_frame_equal(catalog_first, aemet.read_csv_if_exists(p / "estacions_aemet.csv", aemet.STATION_COLUMNS, decimal=","))
            rainless = stored.loc[stored["station_code"] == "AEMET:9677"]
            self.assertTrue(rainless["rain_mm"].isna().all())
            self.assertTrue((rainless["lat"] == 42.410009).all())
            rain = stored.loc[(stored["station_code"] == "AEMET:1583X") & (stored["local_date"] == "20261029")]
            self.assertEqual(rain["rain_mm"].item(), 2.3)
            live = pd.read_csv(p / "Aemet_incremental.csv", decimal=",")
            self.assertEqual(live.loc[live["Codi Estació"] == "AEMET:0158O", "Total"].item(), 3.2)
            self.assertTrue(live.loc[live["Codi Estació"] == "AEMET:9677", "Total"].isna().all())
            self.assertEqual(catalog_first.set_index("Codi Estació").loc["AEMET:0158O", "Altitud"], 738)
            from rainmapper_core.geojson import dataframe_to_geojson
            geo = dataframe_to_geojson(live, coordinate_exceptions=coordinates.read_state(p)["exceptions"])
            self.assertEqual(len(geo["features"]), len(live))
            for feature in geo["features"]:
                self.assertNotIn("coordinate_exception", feature["properties"])
                if feature["properties"]["Codi Estació"] == "AEMET:9677":
                    self.assertEqual(feature["geometry"]["coordinates"], [1.214647, 42.410009])
                    self.assertIsNone(feature["properties"]["Total"])


if __name__ == "__main__":
    unittest.main()
