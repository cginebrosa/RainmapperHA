from __future__ import annotations

import unittest

from rainmapper_core import mushroom_ml_error_analysis as errors


class ErrorAnalysisTests(unittest.TestCase):
    def test_shared_error_flags(self):
        row = {"y_true": 0, "estimator_probabilities": {"a": 0.7, "b": 0.8, "c": 0.1}}
        result = errors.shared_error_record(row, ["a", "b", "c"])
        self.assertEqual(result["wrong_count"], 2)
        self.assertTrue(result["shared_supermajority"])
        self.assertFalse(result["shared_all"])

    def test_observed_phase_preserves_between_negative(self):
        rows = [
            {"row_key": "a", "sample_id": "a", "species_id": "s", "area_id": "x", "validation_group_id": "g", "target_date": "2025-01-01", "y_true": 1},
            {"row_key": "b", "sample_id": "b", "species_id": "s", "area_id": "x", "validation_group_id": "g", "target_date": "2025-01-02", "y_true": 0},
            {"row_key": "c", "sample_id": "c", "species_id": "s", "area_id": "x", "validation_group_id": "g", "target_date": "2025-01-03", "y_true": 1},
        ]
        phases = errors.assign_observed_phases(rows)
        self.assertEqual(phases["a"], "onset_observed")
        self.assertEqual(phases["b"], "between_positive_visits")
        self.assertEqual(phases["c"], "decline_observed")


if __name__ == "__main__":
    unittest.main()
