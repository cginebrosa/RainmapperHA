import unittest

import pandas as pd

from rainmapper_core.meteocat_daily import combine_meteocat_daily_rows


class MeteocatDailyTests(unittest.TestCase):
    def test_condition_only_day_is_preserved_without_fabricating_zero_rain(self):
        rain = pd.DataFrame(
            [
                {
                    "Codi Estació": "CR",
                    "Data Lectura": pd.Timestamp("2020-08-12 02:00:01"),
                    "Data Local": "20200812",
                    "Total": 14.9,
                    "Variable": "Precipitació",
                    "Unitat": "mm",
                }
            ]
        )
        conditions = pd.DataFrame(
            [
                {
                    "Codi Estació": "CR",
                    "Data Lectura": pd.Timestamp("2020-08-11 02:00:01"),
                    "max_temp_celsius": 33.8,
                    "min_temp_celsius": 18.4,
                    "max_humidity_percent": 70.0,
                    "min_humidity_percent": 29.0,
                },
                {
                    "Codi Estació": "CR",
                    "Data Lectura": pd.Timestamp("2020-08-12 02:00:01"),
                    "max_temp_celsius": 29.0,
                    "min_temp_celsius": 15.0,
                    "max_humidity_percent": 100.0,
                    "min_humidity_percent": 41.0,
                },
            ]
        )

        result = combine_meteocat_daily_rows(rain, conditions)

        self.assertEqual(result["Data Local"].tolist(), ["20200812", "20200811"])
        dry_unknown = result[result["Data Local"] == "20200811"].iloc[0]
        self.assertTrue(pd.isna(dry_unknown["Total"]))
        self.assertEqual(dry_unknown["max_humidity_percent"], 70.0)
        rainy = result[result["Data Local"] == "20200812"].iloc[0]
        self.assertEqual(rainy["Total"], 14.9)
        self.assertEqual(rainy["min_humidity_percent"], 41.0)

    def test_observed_zero_rain_is_preserved(self):
        rain = pd.DataFrame(
            [{"Codi Estació": "CR", "Data Lectura": "2020-08-13", "Total": 0.0}]
        )
        conditions = pd.DataFrame(
            [{"Codi Estació": "CR", "Data Lectura": "2020-08-13", "max_humidity_percent": 100.0}]
        )

        result = combine_meteocat_daily_rows(rain, conditions)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Total"], 0.0)


if __name__ == "__main__":
    unittest.main()
