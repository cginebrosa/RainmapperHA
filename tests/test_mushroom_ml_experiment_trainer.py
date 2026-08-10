import tempfile
import unittest
from pathlib import Path

import joblib

from rainmapper_core.mushroom_ml_experiment_trainer import (
    _estimator_unavailable_reason,
    train_benchmark,
)
from rainmapper_core.mushroom_ml_experiments import FIXED_GAP_7D_V1


class ExperimentTrainerTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("scikit-learn not installed")

    def test_calibrated_svm_requires_two_examples_of_each_class(self) -> None:
        import numpy as np

        self.assertIsNotNone(
            _estimator_unavailable_reason(
                "rbf_svm_calibrated_v1", np.asarray([1, 1, 1, 0])
            )
        )
        self.assertIsNone(
            _estimator_unavailable_reason(
                "rbf_svm_calibrated_v1", np.asarray([1, 1, 0, 0])
            )
        )

    def test_trains_both_estimators_without_overwriting_v0(self) -> None:
        samples = []
        for index in range(30):
            target = "favorable" if index % 2 else "unfavorable"
            samples.append(
                {
                    "sample_id": f"sp|area|2026-01-{index + 1:02d}|fixed",
                    "episode_id": f"sp|area|2026-01-{index + 1:02d}",
                    "species_id": "sp",
                    "area_id": "area",
                    "prediction_target": target,
                    "partition": "train" if index < 20 else "test",
                    "chronological_partition": "train" if index < 20 else "test",
                    "features": {
                        column: float(index % 2)
                        for column in FIXED_GAP_7D_V1.feature_cols
                    },
                    "metadata": {
                        "target_date": f"2026-01-{index + 1:02d}",
                        "horizon_days": 7,
                        "enough_history": True,
                    },
                }
            )
        benchmark = {
            "feature_set": {
                "id": FIXED_GAP_7D_V1.feature_set_id,
                "feature_cols": list(FIXED_GAP_7D_V1.feature_cols),
            },
            "episode_count": 30,
            "sample_count": 30,
            "samples": samples,
        }
        with tempfile.TemporaryDirectory() as directory:
            result = train_benchmark(benchmark, Path(directory), min_episodes=20)
            model_files = list(Path(directory).glob("*.joblib"))
            bundle = joblib.load(model_files[0])
        self.assertEqual(len(model_files), 1)
        species = result["species_results"][0]
        self.assertIn("logistic_regression_reduced_v1", species["estimators"])
        self.assertIn("random_forest_restricted_v1", species["estimators"])
        self.assertIn("extra_trees_restricted_v1", species["estimators"])
        self.assertIn("hist_gradient_boosting_restricted_v1", species["estimators"])
        self.assertIn("knn_distance_v1", species["estimators"])
        self.assertIn("rbf_svm_calibrated_v1", species["estimators"])
        self.assertFalse(model_files[0].name.startswith("mushroom_ml_v0_"))
        self.assertEqual(bundle["schema_version"], "1.2")
        self.assertIn("target_month_sin", bundle["feature_support"])
        self.assertEqual(len(bundle["episode_partitions"]), 30)
        self.assertEqual(len(bundle["held_out_predictions"]), 10)
        self.assertEqual(
            set(bundle["held_out_predictions"][0]["estimator_probabilities"]),
            {
                "logistic_regression_reduced_v1",
                "random_forest_restricted_v1",
                "extra_trees_restricted_v1",
                "hist_gradient_boosting_restricted_v1",
                "knn_distance_v1",
                "rbf_svm_calibrated_v1",
            },
        )

    def test_full_fit_is_kept_when_chronological_train_has_one_class(self) -> None:
        samples = []
        for index in range(26):
            samples.append(
                {
                    "sample_id": f"edulis|area|{index}|fixed",
                    "episode_id": f"edulis|area|{index}",
                    "species_id": "edulis",
                    "prediction_target": "favorable" if index < 21 else "unfavorable",
                    "partition": "train" if index < 16 else "test",
                    "features": {
                        column: float(index % 3)
                        for column in FIXED_GAP_7D_V1.feature_cols
                    },
                    "metadata": {"horizon_days": 7, "enough_history": True},
                }
            )
        benchmark = {
            "feature_set": {
                "id": FIXED_GAP_7D_V1.feature_set_id,
                "feature_cols": list(FIXED_GAP_7D_V1.feature_cols),
            },
            "episode_count": 26,
            "sample_count": 26,
            "samples": samples,
        }
        with tempfile.TemporaryDirectory() as directory:
            result = train_benchmark(benchmark, Path(directory), min_episodes=20)
            model_files = list(Path(directory).glob("*.joblib"))

        self.assertEqual(len(model_files), 1)
        species = result["species_results"][0]
        self.assertFalse(species.get("skipped", False))
        self.assertFalse(species["temporal_validation"]["available"])
        self.assertEqual(
            species["temporal_validation"]["reason"],
            "chronological training partition has a single class",
        )


if __name__ == "__main__":
    unittest.main()
