from __future__ import annotations

import unittest

import numpy as np

from rainmapper_core.mushroom_ml_hydric_ablation import (
    ablation_specs,
    expected_calibration_error,
    feature_families,
)


class MushroomMLHydricAblationTests(unittest.TestCase):
    def test_expected_calibration_error_is_zero_for_perfect_predictions(self) -> None:
        labels = np.asarray([0, 0, 1, 1], dtype=int)
        probabilities = np.asarray([0.0, 0.0, 1.0, 1.0], dtype=float)

        self.assertEqual(expected_calibration_error(labels, probabilities), 0.0)

    def test_feature_families_use_only_consumed_columns(self) -> None:
        columns = [
            "horizon_days",
            "rain_cutoff_0_3d_mm",
            "dry_spell_observed_at_cutoff",
            "temp_max_cutoff_7d_c",
            "humidity_min_cutoff_0_3d_pct",
            "climatic_water_balance_cutoff_0_7d_mm",
            "soil_water_area_mean_at_cutoff",
        ]

        families = feature_families(columns)

        self.assertEqual(families["altitude_direct"], [])
        self.assertEqual(
            families["all_hydric"],
            [
                "rain_cutoff_0_3d_mm",
                "dry_spell_observed_at_cutoff",
                "climatic_water_balance_cutoff_0_7d_mm",
                "soil_water_area_mean_at_cutoff",
            ],
        )

    def test_altitude_ablation_is_explicit_null_control_when_feature_is_absent(self) -> None:
        specs = {row["id"]: row for row in ablation_specs(["horizon_days"])}

        self.assertEqual(specs["no_altitude_direct"]["removed_features"], [])
        self.assertIn("Null control", specs["no_altitude_direct"]["description"])


if __name__ == "__main__":
    unittest.main()
