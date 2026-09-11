"""Presentation regression checks; no weather lookup, training or precompute."""

import importlib.util
import json
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "weather_ui", ROOT / "rainmapper-app/app/mushroom_predictor_weather_ui.py"
)
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)
LABELS = json.loads((ROOT / "mushroom-data/mushroom_labels.json").read_text())


class WeatherPresentationTests(unittest.TestCase):
    def comparison(self, features, *, horizon=2, profile="smooth_window_30d_plus_physical_state"):
        return {
            "selected_winners": [{"result_key": "chosen", "model_ref": {
                "horizon_days": horizon, "profile_id": profile}}],
            "chosen": {"features_used": features},
            "competitor": {"features_used": {"rain_mm__lag_000": 999}},
        }

    def render(self, comparison, target=date(2026, 9, 11)):
        return ui.render_weather(comparison, target, lambda key: LABELS[key]["es"])

    def test_actual_lags_light_rain_and_missing_days(self):
        comparison = self.comparison({"rain_mm__lag_000": 3.3, "rain_mm__lag_001": .76,
                                      "rain_mm__lag_002": 0, "rain_mm__lag_003": None})
        data = ui.weather_inputs(comparison["chosen"], comparison["selected_winners"][0]["model_ref"], date(2026, 9, 11))
        self.assertEqual(data["start"], date(2026, 8, 11))
        self.assertEqual(data["end"], date(2026, 9, 9))
        rendered = self.render(comparison)
        self.assertIn("09/09/2026 · 3.30 mm", rendered)
        self.assertIn("08/09/2026 · 0.76 mm", rendered)
        self.assertIn("Suma de lluvia disponible: 4.1 mm", rendered)
        self.assertIn('pred-weather-bar dry', rendered)
        self.assertIn('pred-weather-bar missing', rendered)
        self.assertNotIn("999", rendered)
        self.assertNotIn("10/09/2026", rendered)
        self.assertIn("Meteorología observada", rendered)
        self.assertNotIn("Señala o toca", rendered)
        self.assertNotIn("Verde: lluvia", rendered)
        self.assertIn('aria-live="polite" hidden', rendered)

    def test_windows_and_horizons_across_year_and_leap_boundaries(self):
        for count in (30, 60, 90, 180, 365):
            for target in (date(2026, 1, 2), date(2024, 3, 1)):
                for horizon in (1, 7):
                    with self.subTest(count=count, target=target, horizon=horizon):
                        comparison = self.comparison(
                            {f"rain_mm__lag_{lag:03d}": 0 for lag in range(count)},
                            horizon=horizon, profile=f"raw_window_{count}d_plus_physical_state")
                        data = ui.weather_inputs(comparison["chosen"], comparison["selected_winners"][0]["model_ref"], target)
                        self.assertEqual(data["end"], target - timedelta(days=horizon))
                        self.assertEqual(data["start"], target - timedelta(days=horizon + count - 1))
                        self.assertEqual(len(data["rows"]), count)

    def test_last_rain_skips_traces_and_true_zeros_without_changing_inputs(self):
        for trace in (0, 0.0013102441455423875, 0.009999):
            features = {"rain_mm__lag_000": trace,
                        "rain_mm__lag_001": 42.73318528702588}
            comparison = self.comparison(features, horizon=1, profile="")
            rendered = self.render(comparison)
            self.assertIn("Última lluvia registrada: 09/09/2026 · 42.73 mm", rendered)
            data = ui.weather_inputs(comparison["chosen"],
                                     comparison["selected_winners"][0]["model_ref"], date(2026, 9, 11))
            self.assertEqual(data["rows"][-1]["rain_mm"], trace)
        rendered = self.render(self.comparison({"rain_mm__lag_000": 0.01}, horizon=1, profile=""))
        self.assertIn("Última lluvia registrada: 10/09/2026 · 0.01 mm", rendered)
        rendered = self.render(self.comparison({"rain_mm__lag_000": 0.001}, profile=""))
        self.assertNotIn("Última lluvia registrada:", rendered)

    def test_unknown_or_conflicting_cutoff_does_not_invent_dates(self):
        comparison = self.comparison({"rain_mm__lag_000": 1})
        comparison["chosen"]["metadata"] = {"cutoff_date": "2026-09-10"}
        self.assertEqual(self.render(comparison), "")
        for horizon in (None, True, "2", 0, 8):
            self.assertEqual(self.render(self.comparison({"rain_mm__lag_000": 1}, horizon=horizon)), "")

    def test_legacy_aggregates_not_fabricated_daily_curves(self):
        rendered = self.render(self.comparison({
            "rain_cutoff_0_3d_mm": 5, "rain_cutoff_4_7d_mm": 7,
            "temp_max_mean_cutoff_7d_c": 23, "temp_mean_cutoff_7d_c": 18,
            "humidity_mean_after_significant_rain_pct": 65,
        }, profile="common_idw"))
        self.assertIn("07/09/2026 – 09/09/2026", rendered)
        self.assertIn("03/09/2026 – 06/09/2026", rendered)
        self.assertIn("Media de máximas", rendered)
        self.assertIn("Humedad", rendered)
        self.assertNotIn("Última lluvia registrada", rendered)
        self.assertNotIn("pred-weather-lines", rendered)

    def test_daily_temperature_humidity_keep_missing_values_and_negative_temperatures(self):
        features = {f"{channel}__lag_{lag:03d}": value for channel, value in (
            ("rain_mm", 0), ("temp_min_c", -3), ("temp_max_c", 5),
            ("humidity_min_pct", 40), ("humidity_max_pct", 90)) for lag in range(3)}
        features["temp_min_c__lag_001"] = None
        rendered = self.render(self.comparison(features, profile=""))
        self.assertIn("mín -3.0 °C", rendered)
        self.assertIn("mín — °C", rendered)
        self.assertIn("máx 90.0 %", rendered)
        self.assertIn("Sin lluvia en este periodo", rendered)
        # Missing middle day splits the minimum-temperature line into two pieces.
        self.assertEqual(rendered.count('<polyline class="minimum"'), 3)

    def test_abstention_and_unsafe_values(self):
        self.assertEqual(self.render({"selected_winners": []}), "")
        rendered = self.render(self.comparison({"rain_mm__lag_000": float("nan"),
            "rain_mm__lag_001": -1, "rain_mm__lag_002": '<script>alert(1)</script>'}, profile=""))
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("nan", rendered)
        self.assertNotIn("Lluvia acumulada: 0", rendered)
        self.assertEqual(rendered.count('pred-weather-bar missing'), 3)

    def test_new_labels_exist_in_all_languages(self):
        comparison = self.comparison({"rain_mm__lag_000": 2}, profile="")
        for language in ("es", "ca", "en"):
            rendered = ui.render_weather(comparison, date(2026, 9, 11), lambda key: LABELS[key][language])
            self.assertNotIn("ui.predictor_weather_", rendered)


if __name__ == "__main__":
    unittest.main()
