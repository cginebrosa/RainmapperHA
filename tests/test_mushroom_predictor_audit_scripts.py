from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rain = _load("rain_applicability_audit", "audit-mushroom-rain-applicability.py")
extremes = _load("probability_extremes_audit", "audit-mushroom-probability-extremes.py")


class RainApplicabilityAuditTests(unittest.TestCase):
    def test_rain_excursion_can_be_caution_without_relaxing_other_features(self) -> None:
        columns = ["rain_mm__lag_028", "temp_max_c__lag_000"]
        support = {
            "rain_mm__lag_028": {
                "min": 0.0,
                "max": 25.75,
                "mean": 2.0,
                "std": 4.7,
                "log_mean": 0.8,
                "log_std": 1.0,
            },
            "temp_max_c__lag_000": {
                "min": 0.0,
                "max": 35.0,
                "mean": 20.0,
                "std": 5.0,
                "log_mean": None,
                "log_std": None,
            },
        }
        features = {"rain_mm__lag_028": 32.14, "temp_max_c__lag_000": 20.0}

        current = rain._applicability(features, columns, support, "current_raw")
        log_tail = rain._applicability(features, columns, support, "rain_log_tail")
        no_veto = rain._applicability(features, columns, support, "rain_never_vetoes")

        self.assertEqual(current[0], "outside_domain")
        self.assertEqual(log_tail[0], "caution")
        self.assertEqual(no_veto[0], "caution")

        features["temp_max_c__lag_000"] = 40.0
        self.assertEqual(
            rain._applicability(
                features, columns, support, "rain_never_vetoes"
            )[0],
            "outside_domain",
        )


class ProbabilityExtremeAuditTests(unittest.TestCase):
    def test_exact_endpoints_are_not_treated_as_rounded_bands(self) -> None:
        rows = [
            {
                "probability": 1.0,
                "y_true": 0,
                "baseline_probability": 0.5,
                "observation_id": "one",
                "validation_group_id": "g1",
            },
            {
                "probability": 0.999,
                "y_true": 1,
                "baseline_probability": 0.5,
                "observation_id": "near-one",
                "validation_group_id": "g2",
            },
            {
                "probability": 0.0,
                "y_true": 0,
                "baseline_probability": 0.5,
                "observation_id": "zero",
                "validation_group_id": "g3",
            },
        ]

        result = extremes._summary(rows)

        self.assertEqual(result["exact_one"]["count"], 1)
        self.assertEqual(result["exact_one"]["error_count"], 1)
        self.assertEqual(result["at_least_0_99"]["count"], 2)
        self.assertEqual(result["exact_zero"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
