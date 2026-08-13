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
                temp_max_c=None,
                temp_min_c=None,
                humidity_max_pct=None,
                humidity_min_pct=None,
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
        )

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

    def test_repeated_positive_and_implausible_values_are_suppressed(self) -> None:
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
        self.assertIsNone(result.rain_mm)
        self.assertEqual(result.excluded_suppressed, 2)

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
                "contract_id": "daily_rain_idw_radius15km_power2_v1",
                "method": "inverse_distance_weighted_daily_rainfall",
                "radius_km": 15.0,
                "power": 2.0,
                "distance_floor_km": 0.1,
                "target_geometry": "micro_area_representative_point",
                "observed_zero_is_zero": True,
                "missing_is_zero": False,
                "suppressed_is_zero": False,
                "minimum_contributing_stations": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
