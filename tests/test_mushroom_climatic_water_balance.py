import unittest
from datetime import date, timedelta

from rainmapper_core import mushroom_climatic_water_balance as water_balance


class MushroomClimaticWaterBalanceTests(unittest.TestCase):
    def complete_inputs(self, days: int = 30) -> dict[str, object]:
        cutoff = date(2026, 8, 15)
        dates = [cutoff - timedelta(days=age) for age in reversed(range(days))]
        return {
            "dates": dates,
            "rain_idw_mm": [5.0] * days,
            "temp_min_corrected_c": [10.0] * days,
            "temp_max_corrected_c": [20.0] * days,
            "latitude_deg": 42.0,
        }

    def test_hargreaves_matches_fao_example_scale_and_units(self) -> None:
        # FAO-56 Example 3 gives Ra=40.6 MJ m-2 day-1 for 45°43'N on
        # 15 July. With Tmin=14.8 and Tmax=26.6, Hargreaves is about 5 mm/day.
        eto = water_balance.hargreaves_reference_evapotranspiration_mm(
            date(1999, 7, 15), 45.72, 14.8, 26.6
        )
        self.assertGreater(eto, 4.8)
        self.assertLess(eto, 5.2)

    def test_zero_thermal_range_has_zero_hargreaves_demand(self) -> None:
        self.assertEqual(
            water_balance.hargreaves_reference_evapotranspiration_mm(
                date(2026, 8, 15), 42.0, 15.0, 15.0
            ),
            0.0,
        )

    def test_invalid_latitude_and_inverted_temperature_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "between -90 and 90"):
            water_balance.extraterrestrial_radiation_mj_m2_day(
                date(2026, 8, 15), 91.0
            )
        with self.assertRaisesRegex(ValueError, "greater than or equal"):
            water_balance.hargreaves_reference_evapotranspiration_mm(
                date(2026, 8, 15), 42.0, 20.0, 10.0
            )

    def test_daily_balance_closes_and_all_windows_use_exact_v3_ages(self) -> None:
        result = water_balance.build_climatic_water_balance(**self.complete_inputs())
        features = result["predictive_features"]
        metadata = result["metadata"]
        quality = result["quality"]

        self.assertEqual(set(features), {
            "climatic_water_balance_cutoff_0_7d_mm",
            "climatic_water_balance_cutoff_8_14d_mm",
            "climatic_water_balance_cutoff_15_21d_mm",
            "climatic_water_balance_cutoff_22_30d_mm",
        })
        self.assertEqual(metadata["window_age_bounds_inclusive"]["0_7d"], [0, 6])
        self.assertEqual(metadata["window_age_bounds_inclusive"]["22_30d"], [21, 29])
        self.assertLessEqual(quality["water_balance_mass_error_max_mm"], 0.000001)
        self.assertTrue(all(value is not None for value in features.values()))

    def test_missing_weather_is_not_zero_and_invalidates_only_affected_window(self) -> None:
        inputs = self.complete_inputs()
        inputs["rain_idw_mm"][-2] = None
        result = water_balance.build_climatic_water_balance(**inputs)

        self.assertIsNone(
            result["predictive_features"]["climatic_water_balance_cutoff_0_7d_mm"]
        )
        self.assertIsNotNone(
            result["predictive_features"]["climatic_water_balance_cutoff_8_14d_mm"]
        )
        self.assertEqual(
            result["quality"]["missing_input_reason_counts"],
            {"missing_area_idw_rain": 1},
        )
        self.assertEqual(result["metadata"]["daily_climatic_water_balance_mm"][-2], None)

    def test_quality_and_metadata_can_never_become_predictors_by_flattening(self) -> None:
        result = water_balance.build_climatic_water_balance(**self.complete_inputs())
        predictive = set(result["predictive_features"])
        quality = set(result["quality"])
        metadata = set(result["metadata"])
        self.assertTrue(predictive.isdisjoint(quality))
        self.assertTrue(predictive.isdisjoint(metadata))
        self.assertNotIn("evapotranspiration_input_coverage", predictive)
        self.assertNotIn("evapotranspiration_method", predictive)

    def test_non_consecutive_dates_are_rejected_to_prevent_hidden_gaps(self) -> None:
        inputs = self.complete_inputs()
        inputs["dates"][4] += timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "strictly increasing|consecutive"):
            water_balance.build_climatic_water_balance(**inputs)


if __name__ == "__main__":
    unittest.main()
