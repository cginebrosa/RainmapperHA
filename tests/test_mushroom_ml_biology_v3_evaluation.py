from __future__ import annotations

import unittest

from rainmapper_core import mushroom_ml_biology_v3_evaluation as evaluation


def sample(index: int, target: str, group_7: str, group_14: str) -> dict:
    return {
        "sample_id": str(index),
        "prediction_target": target,
        "predictive_features": {
            "rain_cutoff_0_3d_mm": float(index),
            "temp_mean_cutoff_7d_c": 10.0 + index,
        },
        "quality": {"training_eligible": True},
        "metadata": {
            "species_id": "species",
            "target_date": f"2026-01-{index:02d}",
            "validation_group_7d": group_7,
            "validation_group_14d": group_14,
        },
    }


class BiologyV3EvaluationTests(unittest.TestCase):
    def test_chronological_split_never_breaks_fruiting_group(self) -> None:
        rows = [
            sample(1, "favorable", "g7a", "g14a"),
            sample(2, "unfavorable", "g7a", "g14a"),
            sample(3, "favorable", "g7b", "g14a"),
            sample(4, "unfavorable", "g7c", "g14b"),
            sample(5, "favorable", "g7d", "g14c"),
        ]
        train, test = evaluation.chronological_group_split(rows, group_days=14)
        train_groups = {row["metadata"]["validation_group_14d"] for row in train}
        test_groups = {row["metadata"]["validation_group_14d"] for row in test}
        self.assertFalse(train_groups & test_groups)
        self.assertEqual(len(train) + len(test), len(rows))

    def test_quality_fields_are_not_available_to_feature_families(self) -> None:
        benchmark = {
            "feature_set": {
                "id": "fixture",
                "predictive_feature_cols": [
                    "rain_cutoff_0_3d_mm",
                    "temp_mean_cutoff_7d_c",
                ],
            },
            "samples": [
                sample(1, "favorable", "a", "a"),
                sample(2, "unfavorable", "b", "b"),
                sample(3, "favorable", "c", "c"),
                sample(4, "unfavorable", "d", "d"),
                sample(5, "favorable", "e", "e"),
                sample(6, "unfavorable", "f", "f"),
            ],
        }
        report = evaluation.evaluate_benchmark(benchmark, group_days=7)
        for family in report["families"].values():
            self.assertNotIn("training_eligible", family["feature_cols"])
        self.assertEqual(report["split"]["group_overlap_count"], 0)
        self.assertFalse(report["model_artifact_written"])


if __name__ == "__main__":
    unittest.main()
