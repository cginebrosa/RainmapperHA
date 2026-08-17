import unittest

from rainmapper_core import mushroom_ml_biology_v4_continuity as continuity


class BiologyV4ContinuityTests(unittest.TestCase):
    def test_counts_daily_flicker_and_preserves_inputs(self) -> None:
        rows = [
            {"date": "2026-08-01", "probability": 0.2, "observed_label": "unfavorable"},
            {"date": "2026-08-02", "probability": 0.8, "observed_label": "favorable"},
            {"date": "2026-08-03", "probability": 0.3, "observed_label": "unfavorable"},
            {"date": "2026-08-04", "probability": 0.7},
            {"date": "2026-08-05", "probability": 0.8},
        ]
        result = continuity.summarize_daily_sequence(rows)
        self.assertEqual(result["metadata"]["isolated_positive_days"], 1)
        self.assertEqual(result["metadata"]["isolated_negative_days"], 1)
        self.assertEqual(result["metadata"]["probability_total_variation"], 1.6)
        self.assertEqual(result["metadata"]["observed_label_reversals"], 2)
        self.assertFalse(result["metadata"]["probabilities_modified"])
        self.assertEqual(result["predictive_features"], {})

    def test_gaps_break_runs_and_are_not_daily_transitions(self) -> None:
        result = continuity.summarize_daily_sequence([
            {"date": "2026-08-01", "probability": 0.8},
            {"date": "2026-08-03", "probability": 0.2},
        ])
        self.assertEqual(result["quality"]["date_gap_count"], 1)
        self.assertEqual(result["quality"]["consecutive_transition_count"], 0)
        self.assertEqual(result["metadata"]["probability_total_variation"], 0.0)
        self.assertEqual(len(result["metadata"]["prediction_run_lengths"]), 2)

    def test_rejects_duplicate_dates_and_invalid_probabilities(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate dates"):
            continuity.summarize_daily_sequence([
                {"date": "2026-08-01", "probability": 0.2},
                {"date": "2026-08-01", "probability": 0.3},
            ])
        with self.assertRaisesRegex(ValueError, "between zero and one"):
            continuity.summarize_daily_sequence([
                {"date": "2026-08-01", "probability": 1.2},
            ])

    def test_transient_evaluation_fits_only_training_and_writes_no_model(self) -> None:
        samples = []
        labels = ["unfavorable", "favorable"] * 5
        for index, label in enumerate(labels, start=1):
            day = f"2026-01-{index:02d}"
            samples.append({
                "sample_id": f"s{index}",
                "prediction_target": label,
                "predictive_features": {"rain": float(index)},
                "quality": {"training_eligible": True},
                "metadata": {
                    "species_id": "species_a",
                    "area_id": "area_a",
                    "target_date": day,
                    "validation_group_7d": f"g{index}",
                    "validation_group_14d": f"g{index}",
                },
            })
        benchmark = {
            "feature_set": {"id": "test_v4", "predictive_feature_cols": ["rain"]},
            "samples": samples,
        }
        daily = [
            {
                "predictive_features": {"rain": float(index)},
                "quality": {"training_eligible": True},
                "metadata": {"area_id": "area_a", "target_date": f"2026-01-{index:02d}"},
            }
            for index in range(7, 11)
        ]
        result = continuity.evaluate_daily_continuity(
            benchmark,
            daily,
            group_days=7,
            estimator_ids=["logistic_regression_reduced_v1"],
        )
        report = result["species"]["species_a"]
        area = report["estimators"]["logistic_regression_reduced_v1"]["areas"]["area_a"]
        self.assertEqual(len(area["daily_probabilities"]), 3)
        self.assertEqual(area["daily_probabilities"][0]["date"], "2026-01-08")
        self.assertFalse(result["probabilities_modified"])
        self.assertFalse(result["model_artifact_written"])
        self.assertEqual(result["causality"]["observed_labels"], "attached after prediction for diagnostics only")

    def test_transient_evaluation_rejects_unregistered_estimator(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown continuity estimators"):
            continuity.evaluate_daily_continuity(
                {"feature_set": {"predictive_feature_cols": ["rain"]}, "samples": []},
                [],
                group_days=7,
                estimator_ids=["invented"],
            )


if __name__ == "__main__":
    unittest.main()
