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
            if family["feature_cols"]:
                self.assertEqual(
                    set(family["estimator_status"]),
                    {
                        "logistic_regression_reduced_v1",
                        "random_forest_restricted_v1",
                        "extra_trees_restricted_v1",
                        "hist_gradient_boosting_restricted_v1",
                        "knn_distance_v1",
                        "rbf_svm_calibrated_v1",
                    },
                )
                self.assertEqual(
                    family["pooled_metrics_policy"],
                    "diagnostic_only_never_select_across_species",
                )
                self.assertEqual(
                    family["pairwise_consensus_contract"]["aggregate_policy"],
                    "report rates; do not invent one species-wide label",
                )
                active_pair = family["pairwise_consensus_by_species"]["species"][
                    "logistic_regression_reduced_v1__random_forest_restricted_v1"
                ]
                self.assertEqual(active_pair["n"], 2)
                self.assertEqual(active_pair["held_out_observation_count"], 2)
                self.assertEqual(
                    sum(
                        active_pair["prediction_consensus"][f"{level}_count"]
                        for level in ("high", "moderate", "low")
                    ),
                    active_pair["n"],
                )
        self.assertEqual(report["split"]["group_overlap_count"], 0)
        self.assertEqual(
            report["evaluation_axes"]["fitted_model_definition"],
            "one species x one temporal contract x one estimator",
        )
        self.assertFalse(report["model_artifact_written"])

    def test_matched_comparison_uses_identical_rows_and_split(self) -> None:
        v3_rows = [
            sample(1, "favorable", "a", "a"),
            sample(2, "unfavorable", "b", "b"),
            sample(3, "favorable", "c", "c"),
            sample(4, "unfavorable", "d", "d"),
            sample(5, "favorable", "e", "e"),
            sample(6, "unfavorable", "f", "f"),
        ]
        for row in v3_rows:
            row["metadata"]["observation_id"] = f"obs_{row['sample_id']}"
            row["metadata"]["horizon_days"] = 7
        v2_rows = []
        for row in v3_rows:
            clone = {
                **row,
                "predictive_features": {
                    "rain_cutoff_0_3d_mm": row["predictive_features"]["rain_cutoff_0_3d_mm"]
                },
            }
            v2_rows.append(clone)
        v2_rows.append(
            {
                **sample(7, "favorable", "g", "g"),
                "metadata": {
                    **sample(7, "favorable", "g", "g")["metadata"],
                    "observation_id": "v2_only",
                    "horizon_days": 7,
                },
            }
        )
        v2 = {
            "feature_set": {"id": "v2", "predictive_feature_cols": ["rain_cutoff_0_3d_mm"]},
            "samples": v2_rows,
        }
        v3 = {
            "feature_set": {
                "id": "v3",
                "predictive_feature_cols": ["rain_cutoff_0_3d_mm", "temp_mean_cutoff_7d_c"],
            },
            "samples": v3_rows,
        }
        report = evaluation.evaluate_matched_benchmarks(v2, v3, group_days=7)
        self.assertEqual(report["coverage"]["jointly_eligible"], 6)
        self.assertEqual(report["coverage"]["v2_only"], 1)
        self.assertEqual(report["altitude_v2"]["split"], report["biology_v3"]["split"])
        self.assertFalse(report["model_artifact_written"])


if __name__ == "__main__":
    unittest.main()
