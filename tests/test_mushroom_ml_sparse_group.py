from __future__ import annotations

import unittest

import numpy as np

from rainmapper_core.mushroom_ml_sparse_group import SparseGroupLogisticClassifier


class SparseGroupLogisticTests(unittest.TestCase):
    def test_finite_deterministic_probabilities_and_objective_descent(self):
        rng = np.random.default_rng(42)
        X = rng.normal(size=(120, 6))
        y = (X[:, 0] + 0.8 * X[:, 1] > 0).astype(int)
        kwargs = dict(regularization=0.01, l1_ratio=0.5, groups=[0, 0, 1, 1, 2, 2])
        first = SparseGroupLogisticClassifier(**kwargs).fit(X, y)
        second = SparseGroupLogisticClassifier(**kwargs).fit(X, y)
        probabilities = first.predict_proba(X)
        self.assertTrue(np.all(np.isfinite(probabilities)))
        self.assertTrue(np.all((probabilities >= 0) & (probabilities <= 1)))
        self.assertTrue(all(right <= left + 1e-10 for left, right in zip(first.objective_history_, first.objective_history_[1:])))
        np.testing.assert_allclose(first.coef_, second.coef_)

    def test_large_penalty_removes_irrelevant_group(self):
        rng = np.random.default_rng(7)
        informative = rng.normal(size=(200, 2))
        irrelevant = rng.normal(size=(200, 2))
        X = np.column_stack((informative, irrelevant))
        y = (informative[:, 0] > 0).astype(int)
        model = SparseGroupLogisticClassifier(
            regularization=0.08,
            l1_ratio=0.25,
            groups=[0, 0, 1, 1],
        ).fit(X, y)
        self.assertGreater(np.linalg.norm(model.coef_[0, :2]), 0)
        self.assertEqual(np.linalg.norm(model.coef_[0, 2:]), 0)

    def test_non_convergence_has_a_readable_error(self):
        X = np.asarray([[-2.0], [-1.0], [1.0], [2.0]])
        y = np.asarray([0, 0, 1, 1])
        with self.assertRaisesRegex(ValueError, "did not converge within 1 iterations"):
            SparseGroupLogisticClassifier(
                regularization=0.001, groups=[0], max_iter=1, tolerance=0.0
            ).fit(X, y)


if __name__ == "__main__":
    unittest.main()
