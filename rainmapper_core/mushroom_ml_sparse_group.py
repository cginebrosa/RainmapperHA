"""Small deterministic sparse-group logistic classifier for V5 benchmarks."""

from __future__ import annotations

from typing import Iterable

import numpy as np


class SparseGroupLogisticClassifier:
    """Binary logistic regression with non-overlapping L1/group penalties."""

    def __init__(
        self,
        *,
        regularization: float = 0.1,
        l1_ratio: float = 0.5,
        groups: Iterable[int] | None = None,
        max_iter: int = 2000,
        tolerance: float = 1e-6,
    ) -> None:
        self.regularization = float(regularization)
        self.l1_ratio = float(l1_ratio)
        self.groups = None if groups is None else np.asarray(list(groups), dtype=int)
        self.max_iter = int(max_iter)
        self.tolerance = float(tolerance)

    @staticmethod
    def _sigmoid(values: np.ndarray) -> np.ndarray:
        values = np.clip(values, -35.0, 35.0)
        return 1.0 / (1.0 + np.exp(-values))

    def _prox(self, values: np.ndarray, step: float) -> np.ndarray:
        l1 = step * self.regularization * self.l1_ratio
        shrunk = np.sign(values) * np.maximum(np.abs(values) - l1, 0.0)
        group_strength = step * self.regularization * (1.0 - self.l1_ratio)
        if group_strength <= 0:
            return shrunk
        result = shrunk.copy()
        groups = self.groups_
        for group in np.unique(groups):
            indices = np.flatnonzero(groups == group)
            norm = float(np.linalg.norm(result[indices]))
            threshold = group_strength * np.sqrt(len(indices))
            if norm <= threshold:
                result[indices] = 0.0
            else:
                result[indices] *= 1.0 - threshold / norm
        return result

    def _objective(self, X: np.ndarray, y: np.ndarray, coef: np.ndarray, intercept: float) -> float:
        scores = X @ coef + intercept
        loss = float(np.mean(np.logaddexp(0.0, scores) - y * scores))
        l1 = float(np.sum(np.abs(coef)))
        group = 0.0
        for value in np.unique(self.groups_):
            indices = self.groups_ == value
            group += np.sqrt(int(np.sum(indices))) * float(np.linalg.norm(coef[indices]))
        return loss + self.regularization * (self.l1_ratio * l1 + (1.0 - self.l1_ratio) * group)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SparseGroupLogisticClassifier":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim != 2 or y.ndim != 1 or len(X) != len(y):
            raise ValueError("X and y have incompatible shapes")
        if set(np.unique(y)) != {0.0, 1.0}:
            raise ValueError("sparse-group logistic requires both binary classes")
        if self.regularization < 0 or not 0 <= self.l1_ratio <= 1:
            raise ValueError("invalid sparse-group regularization")
        self.groups_ = self.groups if self.groups is not None else np.arange(X.shape[1])
        if len(self.groups_) != X.shape[1]:
            raise ValueError("groups must contain one id per feature")
        coef = np.zeros(X.shape[1], dtype=float)
        intercept = float(np.log(np.mean(y) / (1.0 - np.mean(y))))
        # Frobenius norm is a cheap conservative upper bound for the spectral
        # norm; the V5 matrices are wide (up to 2,557 columns).
        spectral_upper = float(np.linalg.norm(X, ord="fro"))
        step = 1.0 / max(0.25 * spectral_upper * spectral_upper / len(X), 1e-6)
        objective = self._objective(X, y, coef, intercept)
        history = [objective]
        converged = False
        for iteration in range(1, self.max_iter + 1):
            previous_objective = objective
            probabilities = self._sigmoid(X @ coef + intercept)
            residual = probabilities - y
            gradient = X.T @ residual / len(X)
            intercept_gradient = float(np.mean(residual))
            local_step = step
            while True:
                candidate = self._prox(coef - local_step * gradient, local_step)
                candidate_intercept = intercept - local_step * intercept_gradient
                candidate_objective = self._objective(X, y, candidate, candidate_intercept)
                if candidate_objective <= objective + 1e-12 or local_step < 1e-12:
                    break
                local_step *= 0.5
            delta = max(float(np.max(np.abs(candidate - coef))), abs(candidate_intercept - intercept))
            coef, intercept, objective = candidate, candidate_intercept, candidate_objective
            history.append(objective)
            step = min(local_step * 1.05, step)
            if delta <= self.tolerance or abs(previous_objective - objective) <= self.tolerance:
                converged = True
                break
        self.coef_ = coef.reshape(1, -1)
        self.intercept_ = np.asarray([intercept])
        self.n_iter_ = np.asarray([iteration])
        self.converged_ = converged
        self.objective_history_ = history
        self.classes_ = np.asarray([0, 1])
        if not converged:
            raise ValueError(
                f"sparse-group logistic did not converge within {self.max_iter} iterations"
            )
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        probabilities = self._sigmoid(np.asarray(X, dtype=float) @ self.coef_[0] + self.intercept_[0])
        return np.column_stack((1.0 - probabilities, probabilities))
