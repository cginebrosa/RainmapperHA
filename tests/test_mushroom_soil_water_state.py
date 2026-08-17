import unittest
from datetime import date, timedelta

from rainmapper_core import mushroom_soil_water_state as soil_water


class MushroomSoilWaterStateTests(unittest.TestCase):
    def context(self) -> dict[str, object]:
        depths = []
        for top, bottom in ((0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200)):
            depths.append(
                {
                    "top_cm": top,
                    "bottom_cm": bottom,
                    "area_weighted": {
                        "Q0.50": {
                            "wv0010_mm_per_m": 400.0,
                            "wv0033_mm_per_m": 300.0,
                            "wv1500_mm_per_m": 100.0,
                        }
                    },
                }
            )
        return {"status": "complete", "context_hash": "abc", "depths": depths}

    def test_capacity_integrates_exact_profile_thickness(self) -> None:
        capacity = soil_water.available_water_capacity_mm(
            self.context(), profile_depth_cm=30
        )
        self.assertEqual(capacity["capacity_mm"], 60.0)
        self.assertEqual(capacity["coarse_fragment_correction"], "not_applied_context_unavailable")
        self.assertEqual(len(capacity["layers"]), 3)

    def test_incomplete_or_physically_inverted_capacity_is_rejected(self) -> None:
        context = self.context()
        context["depths"][0]["area_weighted"]["Q0.50"]["wv1500_mm_per_m"] = 350.0
        with self.assertRaisesRegex(ValueError, "below wilting"):
            soil_water.available_water_capacity_mm(context, profile_depth_cm=30)
        with self.assertRaisesRegex(ValueError, "one of"):
            soil_water.available_water_capacity_mm(self.context(), profile_depth_cm=45)

    def test_bucket_closes_mass_and_respects_bounds(self) -> None:
        result = soil_water.simulate_bounded_bucket(
            rain_mm=[100.0, 0.0, 0.0],
            reference_evapotranspiration_mm=[5.0, 5.0, 100.0],
            capacity_mm=60.0,
            initial_storage_mm=0.0,
        )
        self.assertEqual(result["storage_mm"], [60.0, 55.0, 0.0])
        self.assertEqual(result["drainage_mm"][0], 35.0)
        self.assertEqual(result["unmet_evaporative_demand_mm"][-1], 45.0)
        self.assertEqual(result["mass_error_max_mm"], 0.0)

    def test_spinup_selects_shortest_converged_candidate(self) -> None:
        cutoff = date(2026, 8, 15)
        dates = [cutoff - timedelta(days=age) for age in reversed(range(365))]
        # Saturating rain inside the latest 90 days erases both initial states.
        rain = [0.0] * 365
        rain[-45] = 100.0
        result = soil_water.build_soil_water_state(
            dates=dates,
            rain_idw_mm=rain,
            reference_evapotranspiration_mm=[1.0] * 365,
            soilgrids_context=self.context(),
        )
        self.assertEqual(result["metadata"]["selected_spinup_days"], 90)
        self.assertTrue(result["quality"]["training_eligible"])
        self.assertTrue(all(value is not None for value in result["predictive_features"].values()))

    def test_missing_day_is_not_dry_and_blocks_spinup(self) -> None:
        cutoff = date(2026, 8, 15)
        dates = [cutoff - timedelta(days=age) for age in reversed(range(365))]
        rain: list[float | None] = [1.0] * 365
        rain[-10] = None
        result = soil_water.build_soil_water_state(
            dates=dates,
            rain_idw_mm=rain,
            reference_evapotranspiration_mm=[1.0] * 365,
            soilgrids_context=self.context(),
        )
        self.assertFalse(result["quality"]["training_eligible"])
        self.assertEqual(result["quality"]["missing_input_reason_counts"]["missing_area_idw_rain"], 1)
        self.assertTrue(all(value is None for value in result["predictive_features"].values()))

    def test_quality_and_metadata_do_not_enter_predictive_features(self) -> None:
        cutoff = date(2026, 8, 15)
        dates = [cutoff - timedelta(days=age) for age in reversed(range(365))]
        result = soil_water.build_soil_water_state(
            dates=dates,
            rain_idw_mm=[10.0] * 365,
            reference_evapotranspiration_mm=[2.0] * 365,
            soilgrids_context=self.context(),
        )
        predictors = set(result["predictive_features"])
        self.assertTrue(predictors.isdisjoint(result["quality"]))
        self.assertTrue(predictors.isdisjoint(result["metadata"]))
        self.assertNotIn("selected_spinup_days", predictors)

    def test_area_aggregation_keeps_rows_and_uses_available_microareas(self) -> None:
        cutoff = date(2026, 8, 15)
        dates = [cutoff - timedelta(days=age) for age in reversed(range(365))]
        available = soil_water.build_soil_water_state(
            dates=dates,
            rain_idw_mm=[10.0] * 365,
            reference_evapotranspiration_mm=[2.0] * 365,
            soilgrids_context=self.context(),
        )
        unavailable_rain: list[float | None] = [10.0] * 365
        unavailable_rain[-1] = None
        unavailable = soil_water.build_soil_water_state(
            dates=dates,
            rain_idw_mm=unavailable_rain,
            reference_evapotranspiration_mm=[2.0] * 365,
            soilgrids_context=self.context(),
        )
        result = soil_water.aggregate_area_soil_water_states(
            {"micro_a": available, "micro_b": unavailable}
        )
        self.assertTrue(result["quality"]["training_eligible"])
        self.assertEqual(result["quality"]["configured_microarea_count"], 2)
        self.assertEqual(result["quality"]["available_microarea_count"], 1)
        self.assertEqual(result["metadata"]["available_microarea_ids"], ["micro_a"])
        self.assertTrue(all(value is not None for value in result["predictive_features"].values()))

    def test_area_aggregation_is_missing_only_when_every_microarea_is_missing(self) -> None:
        result = soil_water.aggregate_area_soil_water_states({})
        self.assertFalse(result["quality"]["training_eligible"])
        self.assertTrue(all(value is None for value in result["predictive_features"].values()))


if __name__ == "__main__":
    unittest.main()
