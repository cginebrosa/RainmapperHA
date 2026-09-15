"""Read-only point queries against tiny, real partitioned Parquet generations."""
import os
import unittest
from datetime import date, datetime, timezone
from unittest import mock

from tests import test_weather_history_dataset as fixtures
from rainmapper_core import mushroom_map_weather as weather
from rainmapper_core import mushroom_ml_area_weather_runtime as runtime


class PointWeatherTests(unittest.TestCase):
    def test_midnight_calendar_ignores_executor_timezone_and_keeps_future_guard(self):
        # UTC is still yesterday: Madrid has already closed that weather day.
        for instant in (datetime(2026,9,14,22,10,tzinfo=timezone.utc),
                        datetime(2026,12,14,23,10,tzinfo=timezone.utc)):
            with self.subTest(instant=instant), mock.patch.object(weather, 'datetime') as clock:
                clock.now.side_effect = lambda tz: instant.astimezone(tz)
                today = date(2026,instant.month,15)
                self.assertEqual(weather.map_today(),today)
                self.assertEqual(weather.map_today('UTC'),date(2026,instant.month,14))
                yesterday = date(2026,instant.month,14)
                _,series,_ = self.model_inputs(end_day=yesterday)
                self.assertEqual(series['daily_dates'][-1],yesterday.isoformat())
                with mock.patch.object(self.reader,'_load',side_effect=AssertionError('future read')):
                    for cutoff in (today,date(2026,instant.month,16)):
                        with self.assertRaisesRegex(ValueError,'invalid_model_weather_cutoff'):
                            self.model_inputs(end_day=cutoff)

    def setUp(self):
        class WeatherFixture(fixtures.WeatherHistoryDatasetTests):
            def _row(self, source, station, day, rain):
                frame = super()._row(source, station, day, 1.0 if station == "A" else rain)
                frame["min_temp_celsius"] = 10.0
                frame["max_temp_celsius"] = 20.0
                frame["min_humidity_percent"] = 40.0
                frame["max_humidity_percent"] = 90.0
                frame["wind_avg_kmh"] = 0.0
                frame["wind_gust_kmh"] = 12.0
                return frame
        self.fixture = WeatherFixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.stations = self.fixture.data_dir / "stations.txt"
        self.stations.write_text("", encoding="utf-8")
        self.reader = weather.PointWeatherReader(str(self.fixture.data_dir), str(self.stations))

    def query(self, **kw):
        return self.reader.lookup(42.0, 2.0, kw.pop("altitude", 800), end_day=date(2026, 1, 7), days=7, **kw)

    def signatures(self):
        return {str(p): weather.fingerprint(p) for p in self.fixture.data_dir.rglob("*") if p.is_file()}

    def test_padding_duplicate_zero_missing_and_temperature_contract(self):
        result = self.query()
        self.assertEqual(result["dates"][0], "2026-01-01")
        self.assertEqual(result["series"]["rain_mm"], [2.0] + [None]*6)
        self.assertEqual(result["rain_imputed_zero_counts"], [1]+[0]*6)
        self.assertEqual(result["station_counts"]["rain_mm"], [2]+[0]*6)
        self.assertAlmostEqual(result["series"]["temp_min_c"][0], 9.35)
        self.assertEqual(result["station_counts"]["temp_min_c"], [2]+[0]*6)
        self.assertEqual(result["wind"]["avg_kmh"], [0.0]+[None]*6)
        self.assertEqual(result["wind"]["station_code"], "A")
        self.assertEqual(self.reader.last_metrics["rows_loaded"], 4)

    def test_no_altitude_preserves_rain_and_humidity(self):
        result = self.query(altitude=None)
        self.assertEqual(result["series"]["temp_min_c"], [None]*7)
        self.assertEqual(result["series"]["rain_mm"][0], 2.0)
        self.assertEqual(result["series"]["humidity_max_pct"][0], 90.0)

    def test_read_only_cache_and_return_value_isolation(self):
        before = self.signatures()
        result = self.query()
        result["series"]["rain_mm"][0] = 999
        with mock.patch.object(self.reader, "_load", side_effect=AssertionError("cache miss")):
            self.assertEqual(self.query()["series"]["rain_mm"][0], 2.0)
        self.assertTrue(self.reader.last_metrics["cache_hit"])
        self.assertEqual(before, self.signatures())
        self.assertFalse((self.fixture.root / "leases").exists())

    def test_disabled_station_changes_invalidate_cache(self):
        self.query()
        self.stations.write_text("# rainmapper-disabled:bad_data https://www.wunderground.com/dashboard/pws/W\n")
        result = self.query()
        self.assertFalse(self.reader.last_metrics["cache_hit"])
        self.assertEqual(result["series"]["rain_mm"][0], 0.0)
        self.assertEqual(result["station_counts"]["rain_mm"][0], 1)

    def test_changed_partition_rejects_cached_response(self):
        self.query()
        partition = self.reader.generation.object_path(self.reader.generation.partitions[0].path)
        stat = partition.stat()
        os.utime(partition, ns=(stat.st_atime_ns, stat.st_mtime_ns+1000000))
        with self.assertRaisesRegex(ValueError, "weather_input_changed"):
            self.query()

    def test_outside_coverage_omits_wind_and_cache_is_bounded(self):
        for lon in range(5):
            result = self.reader.lookup(0.0, float(lon), None, end_day=date(2026,1,7), days=7)
            self.assertEqual(result["status"], "no_data")
            self.assertNotIn("wind", result)
        self.assertEqual(len(self.reader._cache), 4)

    def test_candidate_limit_fails_instead_of_truncating(self):
        self.reader._refresh()
        self.reader.catalog = [dict(self.reader.catalog[0], station_code=str(i)) for i in range(257)]
        with self.assertRaisesRegex(ValueError, "weather_station_limit"):
            self.reader._nearby(42, 2)

    def test_current_change_reloads_generation_once(self):
        self.query()
        current = self.fixture.root / "CURRENT.json"
        current.write_text(current.read_text()+"\n")
        with mock.patch.object(weather, "resolve_weather_generation", wraps=weather.resolve_weather_generation) as resolve:
            self.query()
            self.assertFalse(self.reader.last_metrics["cache_hit"])
            self.query()
            self.assertEqual(resolve.call_count, 1)
            self.assertFalse(resolve.call_args.kwargs["verify_hashes"])

    def model_inputs(self, **kwargs):
        options = {"end_day":date(2026,1,7),"lookback_days":90,"include_physical_state":False}
        options.update(kwargs)
        return self.reader.prepare_model_inputs(42.0,2.0,800,**options)

    def test_model_uses_shared_materialization_and_keeps_cutoff_gaps_and_duplicates(self):
        before = self.signatures()
        with mock.patch.object(runtime,"materialize_area_series",wraps=runtime.materialize_area_series) as build:
            area,series,stations = self.model_inputs()
        self.assertEqual(build.call_count,1)
        self.assertTrue(area.area_id.startswith("map-point:"))
        self.assertEqual(area.location_source,"map_query_point")
        self.assertEqual(series["daily_dates"][-1],"2026-01-07")
        self.assertEqual(len(series["daily_dates"]),90)
        self.assertEqual(series["daily_rain_idw_mean_mm"][-7:],[2.0]+[None]*6)
        self.assertEqual(self.reader.last_metrics["lookback_days"],90)
        self.assertEqual(before,self.signatures())
        self.assertEqual(len(self.reader._cache),0)
        self.assertEqual(self.query()["history_days"],7)
        with self.assertRaisesRegex(ValueError,"invalid_weather_days"):
            self.reader.lookup(42.0,2.0,800,end_day=date(2026,1,7),days=365)

    def test_model_full_year_missing_soil_is_not_fabricated(self):
        area,series,stations = self.model_inputs(lookback_days=365,include_physical_state=True)
        self.assertEqual(len(series["daily_dates"]),365)
        self.assertIsNone(series["soil_water_area_mean_at_cutoff"])
        self.assertFalse(series["soil_water_quality"]["training_eligible"])
        self.assertTrue(all(day <= date(2026,1,7) for station in stations.values() for day in station.records_by_day))
        other,_,_ = self.reader.prepare_model_inputs(42.0,2.001,800,end_day=date(2026,1,7),
            lookback_days=90,include_physical_state=False)
        self.assertNotEqual(area.area_id,other.area_id)

    def test_model_limits_reject_before_loading(self):
        with mock.patch.object(self.reader,"_load",side_effect=AssertionError("must reject before I/O")):
            for days in (0,366,True,90.0):
                with self.assertRaisesRegex(ValueError,"invalid_model_weather_days"):
                    self.model_inputs(lookback_days=days)
            with self.assertRaisesRegex(ValueError,"invalid_model_weather_cutoff"):
                self.model_inputs(end_day=weather.map_today())
            with self.assertRaisesRegex(ValueError,"invalid_point_soil_context"):
                self.model_inputs(soilgrids_context={"status":"complete"})


if __name__ == "__main__":
    unittest.main()
