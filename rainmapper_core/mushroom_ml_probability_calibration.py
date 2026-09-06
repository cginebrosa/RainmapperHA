"""Probability post-processing shared by mushroom ML training and inference."""

from __future__ import annotations

from typing import Any

from sklearn.neighbors import KNeighborsClassifier


class BetaSmoothedKNeighborsClassifier(KNeighborsClassifier):
    """KNN whose class probabilities receive symmetric pseudo-count smoothing.

    The operational configuration uses seven effective observations and one
    pseudo-observation per class. For a binary raw probability ``p`` this is
    exactly ``(7 * p + 1) / 9``. The transformation removes unjustified exact
    zeroes and ones without changing the class ordering.
    """

    def __init__(
        self,
        n_neighbors: int = 5,
        *,
        weights: str = "uniform",
        algorithm: str = "auto",
        leaf_size: int = 30,
        p: int = 2,
        metric: str = "minkowski",
        metric_params: dict[str, Any] | None = None,
        n_jobs: int | None = None,
        effective_sample_size: float = 7.0,
        beta_alpha: float = 1.0,
    ) -> None:
        super().__init__(
            n_neighbors=n_neighbors,
            weights=weights,
            algorithm=algorithm,
            leaf_size=leaf_size,
            p=p,
            metric=metric,
            metric_params=metric_params,
            n_jobs=n_jobs,
        )
        self.effective_sample_size = effective_sample_size
        self.beta_alpha = beta_alpha

    def predict_proba(self, X: Any) -> Any:  # noqa: N803 - sklearn API
        if self.effective_sample_size <= 0:
            raise ValueError("effective_sample_size must be positive")
        if self.beta_alpha <= 0:
            raise ValueError("beta_alpha must be positive")
        probabilities = super().predict_proba(X)
        class_count = probabilities.shape[1]
        denominator = self.effective_sample_size + self.beta_alpha * class_count
        return (
            self.effective_sample_size * probabilities + self.beta_alpha
        ) / denominator
