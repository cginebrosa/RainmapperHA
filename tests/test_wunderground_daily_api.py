import unittest

from rainmapper_core.sources.wunderground.daily_api import (
    build_monthly_rows,
    inch_to_mm,
    station_id_from_url,
)


class WundergroundDailyApiTest(unittest.TestCase):
    def test_station_id_from_url_normalizes_case(self):
        self.assertEqual(
            station_id_from_url("https://www.wunderground.com/dashboard/pws/IORDiN1"),
            "IORDIN1",
        )

    def test_inch_to_mm_matches_wunderground_metric_display(self):
        self.assertEqual(inch_to_mm(1.82), 46.23)

    def test_build_monthly_rows_maps_precipitation_and_weather_fields(self):
        rows = build_monthly_rows(
            [
                {
                    "obsTimeLocal": "2026-07-10 19:39:52",
                    "humidityHigh": 88,
                    "humidityAvg": 54.9,
                    "humidityLow": 19,
                    "imperial": {
                        "tempHigh": 91.4,
                        "tempAvg": 66,
                        "tempLow": 53.2,
                        "dewptHigh": 61.2,
                        "dewptAvg": 47,
                        "dewptLow": 41.7,
                        "windspeedHigh": 9.6,
                        "windspeedAvg": 1,
                        "windspeedLow": 0,
                        "pressureMax": 30.08,
                        "pressureMin": 29.97,
                        "precipTotal": 1.82,
                    },
                }
            ],
            "IORDIN1",
            "La Cortinada",
            "Ordino",
            "1344",
            42.571926,
            1.519332,
        )

        self.assertEqual(rows[0]["Date"], "2026-07-10")
        self.assertEqual(rows[0]["StationID"], "IORDIN1")
        self.assertEqual(rows[0]["Sum"], 46.23)
        self.assertEqual(rows[0]["High"], 33.0)
        self.assertEqual(rows[0]["High_3"], 15.45)


if __name__ == "__main__":
    unittest.main()
