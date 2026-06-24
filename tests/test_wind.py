import unittest

import pandas as pd

from rainmapper_core.wind import (
    aemet_direction_to_degrees,
    circular_mean_degrees,
    compass_to_degrees,
    first_valid,
    meters_per_second_to_kmh,
    normalize_direction_degrees,
    optional_round,
    xema_daily_wind_fields,
)


class WindHelpersTest(unittest.TestCase):
    def test_optional_round_preserves_missing_values(self):
        self.assertEqual(optional_round("12,34"), 12.3)
        self.assertTrue(pd.isna(optional_round("")))
        self.assertTrue(pd.isna(optional_round("--")))

    def test_first_valid(self):
        self.assertEqual(first_valid(pd.NA, "", "3,5"), 3.5)
        self.assertTrue(pd.isna(first_valid(pd.NA, "")))

    def test_meters_per_second_to_kmh(self):
        self.assertEqual(meters_per_second_to_kmh(2), 7.2)
        self.assertTrue(pd.isna(meters_per_second_to_kmh("")))

    def test_xema_daily_wind_fields_prefers_10m(self):
        fields = xema_daily_wind_fields({
            "max_valor_variable_1503": 2.0,
            "max_valor_variable_1504": 4.0,
            "max_valor_variable_1509": 361,
            "max_valor_variable_1512": 8.0,
            "max_valor_variable_1515": 270,
        })
        self.assertEqual(fields["wind_avg_kmh"], 7.2)
        self.assertEqual(fields["wind_gust_kmh"], 28.8)
        self.assertEqual(fields["wind_direction_deg"], 1.0)
        self.assertEqual(fields["wind_gust_direction_deg"], 270.0)
        self.assertEqual(fields["wind_observation_count"], 1)
        self.assertEqual(fields["wind_source_height_m"], 10)

    def test_xema_daily_wind_fields_falls_back_to_6m(self):
        fields = xema_daily_wind_fields({
            "max_valor_variable_1504": 3.0,
            "max_valor_variable_1510": 90,
            "max_valor_variable_1513": 5.0,
            "max_valor_variable_1516": 100,
        })
        self.assertEqual(fields["wind_avg_kmh"], 10.8)
        self.assertEqual(fields["wind_gust_kmh"], 18.0)
        self.assertEqual(fields["wind_direction_deg"], 90.0)
        self.assertEqual(fields["wind_gust_direction_deg"], 100.0)
        self.assertEqual(fields["wind_source_height_m"], 6)

    def test_compass_to_degrees(self):
        self.assertEqual(compass_to_degrees("N"), 0.0)
        self.assertEqual(compass_to_degrees("SW"), 225.0)
        self.assertEqual(compass_to_degrees("wnw"), 292.5)
        self.assertTrue(pd.isna(compass_to_degrees("CALM")))

    def test_normalize_direction_degrees(self):
        self.assertEqual(normalize_direction_degrees(360), 0.0)
        self.assertEqual(normalize_direction_degrees(361), 1.0)
        self.assertEqual(normalize_direction_degrees(-10), 350.0)

    def test_aemet_daily_direction_decodes_tens_of_degrees(self):
        self.assertEqual(aemet_direction_to_degrees(23), 230.0)
        self.assertEqual(aemet_direction_to_degrees(344), 344.0)

    def test_circular_mean_wraps_around_north(self):
        self.assertEqual(circular_mean_degrees([350, 10]), 0.0)
        self.assertEqual(circular_mean_degrees([80, 100]), 90.0)
        self.assertTrue(pd.isna(circular_mean_degrees([])))


if __name__ == "__main__":
    unittest.main()
