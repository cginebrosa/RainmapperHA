import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


class MushroomWeatherIDWTests(unittest.TestCase):
    day = date(2026, 8, 11)

    def station(
        self,
        code: str,
        *,
        lat: float,
        lon: float,
        rain_by_day: dict[date, float | None],
        source: str = "test",
        altitude_m: float | None = None,
        temp_min_c: float | None = None,
        temp_max_c: float | None = None,
        humidity_min_pct: float | None = None,
        humidity_max_pct: float | None = None,
    ) -> weather_context.WeatherStation:
        records = {
            day: weather_context.DailyWeatherRecord(
                source=source,
                station_code=code,
                station_name=code,
                day=day,
                lat=lat,
                lon=lon,
                rain_mm=value,
                temp_max_c=temp_max_c,
                temp_min_c=temp_min_c,
                humidity_max_pct=humidity_max_pct,
                humidity_min_pct=humidity_min_pct,
                wind_avg_kmh=None,
                wind_gust_kmh=None,
                wind_direction_deg=None,
            )
            for day, value in rain_by_day.items()
        }
        return weather_context.WeatherStation(
            source=source,
            station_code=code,
            station_name=code,
            lat=lat,
            lon=lon,
            records_by_day=records,
            altitude_m=altitude_m,
        )

    def test_temperature_idw_corrects_each_source_before_weighting(self) -> None:
        one_km_lat = 1.0 / 111.195
        stations = {
            ("aemet", "A"): self.station(
                "A", source="aemet", lat=one_km_lat, lon=0,
                rain_by_day={self.day: 0.0}, altitude_m=500.0, temp_max_c=20.0,
            ),
            ("meteocat", "B"): self.station(
                "B", source="meteocat", lat=2 * one_km_lat, lon=0,
                rain_by_day={self.day: 0.0}, altitude_m=1000.0, temp_max_c=18.0,
            ),
            ("meteoclimatic", "C"): self.station(
                "C", source="meteoclimatic", lat=3 * one_km_lat, lon=0,
                rain_by_day={self.day: 0.0}, altitude_m=None, temp_max_c=99.0,
            ),
        }
        result = mushroom_weather_idw.estimate_daily_weather_idw(
            stations,
            metric="temp_max_c",
            target_lat=0,
            target_lon=0,
            target_altitude_m=1000.0,
            day=self.day,
        )
        # A is adjusted by -3.25 C; B needs no correction; C is excluded.
        distances = [row.distance_km for row in result.contributions]
        expected = (16.75 / distances[0] ** 2 + 18.0 / distances[1] ** 2) / (
            1.0 / distances[0] ** 2 + 1.0 / distances[1] ** 2
        )
        self.assertAlmostEqual(result.value, expected, places=10)
        self.assertEqual({row.source for row in result.contributions}, {"aemet", "meteocat"})
        self.assertEqual(result.excluded_altitude_missing, 1)

    def test_humidity_idw_uses_all_sources_without_altitude_correction(self) -> None:
        stations = {
            (source, str(index)): self.station(
                str(index), source=source, lat=index * 0.001, lon=0,
                rain_by_day={self.day: 0.0}, altitude_m=None,
                humidity_min_pct=40.0 + index,
            )
            for index, source in enumerate(
                ("aemet", "meteocat", "meteoclimatic", "wunderground"), start=1
            )
        }
        result = mushroom_weather_idw.estimate_daily_weather_idw(
            stations,
            metric="humidity_min_pct",
            target_lat=0,
            target_lon=0,
            target_altitude_m=None,
            day=self.day,
        )
        self.assertIsNotNone(result.value)
        self.assertEqual(result.station_count, 4)
        self.assertEqual(
            {row.source for row in result.contributions},
            {"aemet", "meteocat", "meteoclimatic", "wunderground"},
        )

    def test_combined_series_keeps_values_and_quality_separate(self) -> None:
        station = self.station(
            "A", source="aemet", lat=0, lon=0,
            rain_by_day={self.day: 3.0}, altitude_m=500.0,
            temp_min_c=10.0, temp_max_c=20.0,
            humidity_min_pct=50.0, humidity_max_pct=80.0,
        )
        series = mushroom_weather_idw.build_daily_weather_idw_series(
            {("aemet", "A"): station},
            target_lat=0,
            target_lon=0,
            target_altitude_m=1000.0,
            end_day=self.day,
            days=1,
        )
        self.assertEqual(series["daily_rain_idw_mm"], [3.0])
        self.assertEqual(series["daily_temp_min_idw_c"], [6.75])
        self.assertEqual(series["daily_temp_max_idw_c"], [16.75])
        self.assertEqual(series["daily_humidity_min_idw_pct"], [50.0])
        self.assertEqual(series["daily_humidity_max_idw_pct"], [80.0])
        self.assertEqual(series["daily_temp_min_idw_station_count"], [1])
        self.assertNotIn("daily_temp_min_idw_station_count", mushroom_weather_idw.WEATHER_IDW_METRICS)

    def test_cached_series_slice_exactly_matches_direct_window(self) -> None:
        first_day = self.day - timedelta(days=3)
        rain = {
            first_day + timedelta(days=offset): float(offset)
            for offset in range(6)
        }
        station = self.station(
            "A",
            source="aemet",
            lat=0,
            lon=0,
            rain_by_day=rain,
            altitude_m=500.0,
            temp_min_c=10.0,
            temp_max_c=20.0,
            humidity_min_pct=50.0,
            humidity_max_pct=80.0,
        )
        stations = {("aemet", "A"): station}
        cached = mushroom_weather_idw.build_daily_weather_idw_series(
            stations,
            target_lat=0,
            target_lon=0,
            target_altitude_m=1000.0,
            end_day=first_day + timedelta(days=5),
            days=6,
        )
        sliced = mushroom_weather_idw.slice_daily_weather_idw_series(
            cached,
            end_day=first_day + timedelta(days=4),
            days=3,
        )
        direct = mushroom_weather_idw.build_daily_weather_idw_series(
            stations,
            target_lat=0,
            target_lon=0,
            target_altitude_m=1000.0,
            end_day=first_day + timedelta(days=4),
            days=3,
        )
        self.assertEqual(sliced, direct)

    def test_cached_series_slice_rejects_out_of_range_window(self) -> None:
        station = self.station("A", lat=0, lon=0, rain_by_day={self.day: 0.0})
        cached = mushroom_weather_idw.build_daily_weather_idw_series(
            {("test", "A"): station},
            target_lat=0,
            target_lon=0,
            target_altitude_m=None,
            end_day=self.day,
            days=1,
        )
        with self.assertRaisesRegex(ValueError, "outside the cached range"):
            mushroom_weather_idw.slice_daily_weather_idw_series(
                cached,
                end_day=self.day + timedelta(days=1),
                days=1,
            )

    def test_combined_series_prefilter_preserves_near_station_quality(self) -> None:
        near = self.station(
            "NEAR",
            lat=0,
            lon=0,
            rain_by_day={self.day: 2.0},
            altitude_m=500.0,
            temp_min_c=10.0,
            temp_max_c=20.0,
            humidity_min_pct=50.0,
            humidity_max_pct=80.0,
        )
        far = self.station(
            "FAR",
            lat=1,
            lon=0,
            rain_by_day={self.day: 200.0},
            altitude_m=500.0,
            temp_min_c=-30.0,
            temp_max_c=50.0,
            humidity_min_pct=1.0,
            humidity_max_pct=100.0,
        )
        combined = mushroom_weather_idw.build_daily_weather_idw_series(
            {("test", "NEAR"): near, ("test", "FAR"): far},
            target_lat=0,
            target_lon=0,
            target_altitude_m=500.0,
            end_day=self.day,
            days=1,
        )
        direct = mushroom_weather_idw.build_daily_weather_idw_series(
            {("test", "NEAR"): near},
            target_lat=0,
            target_lon=0,
            target_altitude_m=500.0,
            end_day=self.day,
            days=1,
        )
        self.assertEqual(combined, direct)

    def test_matches_maplibre_inverse_distance_formula(self) -> None:
        one_km_lat = 1.0 / 111.195
        stations = {
            ("test", "A"): self.station(
                "A", lat=one_km_lat, lon=0, rain_by_day={self.day: 10.0}
            ),
            ("test", "B"): self.station(
                "B", lat=2 * one_km_lat, lon=0, rain_by_day={self.day: 30.0}
            ),
        }
        result = mushroom_weather_idw.estimate_daily_rain_idw(
            stations, target_lat=0, target_lon=0, day=self.day
        )

        distance_a, distance_b = [item.distance_km for item in result.contributions]
        expected = (
            10.0 / distance_a**2 + 30.0 / distance_b**2
        ) / (1.0 / distance_a**2 + 1.0 / distance_b**2)
        self.assertAlmostEqual(result.rain_mm, expected, places=10)
        self.assertAlmostEqual(result.rain_mm, 14.0, places=2)

    def test_observed_zero_participates_but_missing_never_becomes_zero(self) -> None:
        zero = self.station("ZERO", lat=0, lon=0, rain_by_day={self.day: 0.0})
        wet = self.station("WET", lat=0.01, lon=0, rain_by_day={self.day: 20.0})
        result = mushroom_weather_idw.estimate_daily_rain_idw(
            {("test", "ZERO"): zero, ("test", "WET"): wet},
            target_lat=0,
            target_lon=0,
            day=self.day,
        )
        self.assertTrue(result.observed)
        self.assertEqual(result.station_count, 2)
        self.assertLess(result.rain_mm, 1.0)

        missing = mushroom_weather_idw.estimate_daily_rain_idw(
            {("test", "ZERO"): zero},
            target_lat=0,
            target_lon=0,
            day=self.day + timedelta(days=1),
        )
        self.assertIsNone(missing.rain_mm)
        self.assertFalse(missing.observed)

    def test_repeated_positive_is_zero_but_implausible_value_is_suppressed(self) -> None:
        repeated = self.station(
            "REPEAT",
            lat=0,
            lon=0,
            rain_by_day={self.day: 12.0, self.day + timedelta(days=1): 12.0},
        )
        suspect = self.station(
            "SUSPECT", lat=0.01, lon=0, rain_by_day={self.day + timedelta(days=1): 301.0}
        )
        result = mushroom_weather_idw.estimate_daily_rain_idw(
            {("test", "REPEAT"): repeated, ("test", "SUSPECT"): suspect},
            target_lat=0,
            target_lon=0,
            day=self.day + timedelta(days=1),
        )
        self.assertEqual(result.rain_mm, 0.0)
        self.assertEqual(result.station_count, 1)
        self.assertEqual(result.imputed_repeated_positive_zero, 1)
        self.assertEqual(result.excluded_suppressed, 1)
        self.assertTrue(result.contributions[0].imputed_repeated_positive_as_zero)

    def test_out_of_radius_and_retired_stations_do_not_contribute(self) -> None:
        retired = self.station(
            "IRETIRED", lat=0, lon=0, rain_by_day={self.day: 50.0}, source="wunderground"
        )
        far = self.station("FAR", lat=1, lon=0, rain_by_day={self.day: 40.0})
        result = mushroom_weather_idw.estimate_daily_rain_idw(
            {("wunderground", "IRETIRED"): retired, ("test", "FAR"): far},
            target_lat=0,
            target_lon=0,
            day=self.day,
            excluded_station_keys={("wunderground", "IRETIRED")},
        )
        self.assertIsNone(result.rain_mm)
        self.assertEqual(result.excluded_retired, 1)

    def test_disabled_station_file_accepts_all_disable_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "stations.txt"
            path.write_text(
                "# rainmapper-disabled:404 https://www.wunderground.com/dashboard/pws/IONE1\n"
                "# rainmapper-disabled:bad_data https://www.wunderground.com/dashboard/pws/ITWO2\n"
                "https://www.wunderground.com/dashboard/pws/IACTIVE3\n",
                encoding="utf-8",
            )
            self.assertEqual(
                mushroom_weather_idw.disabled_wunderground_station_keys(path),
                frozenset({("wunderground", "IONE1"), ("wunderground", "ITWO2")}),
            )

    def test_series_keeps_missing_quality_separate_from_values(self) -> None:
        station = self.station("A", lat=0, lon=0, rain_by_day={self.day: 0.0})
        series = mushroom_weather_idw.build_daily_rain_idw_series(
            {("test", "A"): station},
            target_lat=0,
            target_lon=0,
            end_day=self.day + timedelta(days=1),
            days=2,
        )
        self.assertEqual(series["daily_rain_idw_mm"], [0.0, None])
        self.assertEqual(series["daily_rain_observed"], [True, False])
        self.assertEqual(series["rain_observed_days"], 1)
        self.assertEqual(series["rain_missing_days"], 1)

    def test_contract_is_versioned_and_fixed(self) -> None:
        self.assertEqual(
            mushroom_weather_idw.rainfall_idw_contract_metadata(),
            {
                "contract_id": "daily_rain_idw_radius15km_power2_duplicate_zero_v2",
                "method": "inverse_distance_weighted_daily_rainfall",
                "radius_km": 15.0,
                "power": 2.0,
                "distance_floor_km": 0.1,
                "target_geometry": "micro_area_representative_point",
                "observed_zero_is_zero": True,
                "missing_is_zero": False,
                "repeated_positive_suppressed_is_zero": True,
                "other_suppressed_is_zero": False,
                "minimum_contributing_stations": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
