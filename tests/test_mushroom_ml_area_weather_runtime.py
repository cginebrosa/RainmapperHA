from __future__ import annotations

from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import patch

from rainmapper_core import mushroom_ml_area_weather_runtime as runtime
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3


class MushroomMLAreaWeatherRuntimeTests(TestCase):
    def context(self, identifier: str) -> biology_v3.MicroAreaContext:
        return biology_v3.MicroAreaContext(
            micro_area_id=identifier,
            area_id="area-a",
            lat=42.0,
            lon=1.0,
            location_source="test",
            altitude_m=1000.0,
            altitude_source="test",
            soilgrids_water={"context_hash": identifier},
        )

    def weather(
        self,
        *,
        days: list[str],
        rain: list[float | None],
        temp_min: list[float],
    ) -> dict[str, object]:
        return {
            "daily_dates": days,
            "daily_rain_idw_mm": rain,
            "daily_temp_min_idw_c": temp_min,
            "daily_temp_max_idw_c": [value + 10.0 for value in temp_min],
            "daily_humidity_min_idw_pct": [40.0] * len(days),
            "daily_humidity_max_idw_pct": [80.0] * len(days),
            "daily_rain_suppressed_station_count": [0] * len(days),
            "daily_rain_imputed_duplicate_zero_station_count": [0] * len(days),
        }

    def test_predictor_derives_balance_and_soil_state_from_microarea_idw(self):
        end = date(2026, 8, 17)
        axis = [(end - timedelta(days=1)).isoformat(), end.isoformat()]
        weather_rows = [
            self.weather(days=axis, rain=[0.0, 10.0], temp_min=[1.0, 1.0]),
            self.weather(days=axis, rain=[None, 20.0], temp_min=[2.0, 2.0]),
        ]
        soil_inputs: list[tuple[list[float | None], list[float | None], str]] = []

        def build_soil_state(**kwargs):
            soil_inputs.append(
                (
                    list(kwargs["rain_idw_mm"]),
                    list(kwargs["reference_evapotranspiration_mm"]),
                    str(kwargs["soilgrids_context"]["context_hash"]),
                )
            )
            fractions = [0.25, 0.5]
            return {
                "predictive_features": {},
                "quality": {
                    "training_eligible": True,
                    "training_exclusion_reasons": [],
                },
                "metadata": {
                    "cutoff_date": end.isoformat(),
                    "daily_storage_fraction": [0.1] * 13 + fractions,
                    "longest_converged_daily_dates": axis,
                    "longest_converged_daily_storage_fraction": fractions,
                },
            }

        with (
            patch.object(
                runtime.mushroom_weather_idw,
                "build_daily_weather_idw_series",
                side_effect=weather_rows,
            ),
            patch.object(
                runtime.climate,
                "hargreaves_reference_evapotranspiration_mm",
                side_effect=lambda _day, _lat, low, _high: float(low),
            ),
            patch.object(
                runtime.mushroom_soil_water_state,
                "build_soil_water_state",
                side_effect=build_soil_state,
            ),
        ):
            result = runtime.materialize_area_series(
                area_id="area-a",
                end_day=end,
                days=2,
                microareas_by_area={
                    "area-a": [self.context("micro-1"), self.context("micro-2")]
                },
                stations={},
            )

        self.assertEqual(
            soil_inputs,
            [
                ([0.0, 10.0], [1.0, 1.0], "micro-1"),
                ([None, 20.0], [2.0, 2.0], "micro-2"),
            ],
        )
        self.assertEqual(result["daily_rain_idw_mean_mm"], [0.0, 15.0])
        self.assertEqual(result["daily_eto0_mean_mm"], [1.5, 1.5])
        self.assertEqual(result["daily_climatic_balance_mean_mm"], [-1.0, 13.5])
        self.assertEqual(result["daily_soil_water_fraction_mean"], [0.25, 0.5])

    def test_idw_only_profile_skips_physical_state_without_removing_idw(self):
        end = date(2026, 8, 17)
        axis = [(end - timedelta(days=1)).isoformat(), end.isoformat()]
        weather = self.weather(days=axis, rain=[0.0, 10.0], temp_min=[1.0, 1.0])
        with (
            patch.object(
                runtime.mushroom_weather_idw,
                "build_daily_weather_idw_series",
                return_value=weather,
            ) as build_idw,
            patch.object(
                runtime.climate,
                "hargreaves_reference_evapotranspiration_mm",
            ) as build_eto,
            patch.object(
                runtime.mushroom_soil_water_state,
                "build_soil_water_state",
            ) as build_soil,
        ):
            result = runtime.materialize_area_series(
                area_id="area-a",
                end_day=end,
                days=2,
                microareas_by_area={"area-a": [self.context("micro-1")]},
                stations={},
                include_physical_state=False,
            )

        build_idw.assert_called_once()
        build_eto.assert_not_called()
        build_soil.assert_not_called()
        self.assertEqual(result["daily_rain_idw_mean_mm"], [0.0, 10.0])
        self.assertNotIn("daily_climatic_balance_mean_mm", result)


if __name__ == "__main__":
    import unittest

    unittest.main()
