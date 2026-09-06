from __future__ import annotations

import unittest
from io import BytesIO

import joblib
import numpy as np
from sklearn.base import clone

from rainmapper_core import mushroom_ml_experiment_trainer as trainer
from rainmapper_core.mushroom_ml_probability_calibration import (
    BetaSmoothedKNeighborsClassifier,
)


class BetaSmoothedKNeighborsClassifierTests(unittest.TestCase):
    def test_binary_endpoints_are_smoothed_with_a_symmetric_pseudocount(self) -> None:
        classifier = BetaSmoothedKNeighborsClassifier(
            n_neighbors=1,
            effective_sample_size=7.0,
            beta_alpha=1.0,
        )
        classifier.fit(np.asarray([[0.0], [10.0]]), np.asarray([0, 1]))

        probabilities = classifier.predict_proba(np.asarray([[0.0], [10.0]]))

        np.testing.assert_allclose(
            probabilities,
            np.asarray([[8.0 / 9.0, 1.0 / 9.0], [1.0 / 9.0, 8.0 / 9.0]]),
        )
        np.testing.assert_allclose(probabilities.sum(axis=1), np.ones(2))

    def test_active_roster_uses_only_smoothed_knn(self) -> None:
        self.assertIn(
            trainer.KNN_DISTANCE_SMOOTHED_ESTIMATOR_ID,
            trainer.EXPERIMENT_ESTIMATOR_IDS,
        )
        self.assertNotIn(
            trainer.KNN_DISTANCE_LEGACY_ESTIMATOR_ID,
            trainer.EXPERIMENT_ESTIMATOR_IDS,
        )

    def test_pipeline_is_cloneable_and_serializable(self) -> None:
        model = trainer._pipeline(trainer.KNN_DISTANCE_SMOOTHED_ESTIMATOR_ID)
        cloned = clone(model)
        self.assertIsInstance(
            cloned.named_steps["classifier"], BetaSmoothedKNeighborsClassifier
        )
        X = np.asarray([[float(index)] for index in range(7)])
        y = np.asarray([0, 0, 0, 1, 1, 1, 1])
        model.fit(X, y)

        buffer = BytesIO()
        joblib.dump(model, buffer)
        buffer.seek(0)
        restored = joblib.load(buffer)

        np.testing.assert_allclose(model.predict_proba(X), restored.predict_proba(X))


if __name__ == "__main__":
    unittest.main()
