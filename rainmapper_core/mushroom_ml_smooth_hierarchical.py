"""Smooth-lag features and deterministic cross-species partial pooling for V6."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import SplineTransformer, StandardScaler

from rainmapper_core.mushroom_ml_raw_weather import LOOKBACK_DAYS, RAW_CHANNELS


N_BASIS = 10


def smooth_lag_basis(*, n_basis: int = N_BASIS, log_lag: bool = True) -> np.ndarray:
    """Return normalized causal B-spline weights, lag rows × basis columns."""
    lag = np.arange(LOOKBACK_DAYS, dtype=float)
    # A seven-day offset prevents the boundary spline from collapsing onto
    # lag_000 while retaining substantially finer resolution near the cutoff.
    coordinate = (np.log1p(lag + 7.0) - np.log(8.0)) if log_lag else lag
    coordinate = (coordinate / coordinate[-1]).reshape(-1, 1)
    n_knots = n_basis - 1  # cubic, include_bias=False => n_knots + 1 outputs
    transformer = SplineTransformer(
        n_knots=n_knots, degree=3, include_bias=False, knots="uniform"
    )
    basis = transformer.fit_transform(coordinate)
    totals = basis.sum(axis=0)
    basis[:, totals > 0] /= totals[totals > 0]
    return basis


def raw_columns() -> list[str]:
    return [f"{channel}__lag_{lag:03d}" for channel in RAW_CHANNELS for lag in range(LOOKBACK_DAYS)]


@dataclass
class SmoothLagPreprocessor:
    """Train-only daily imputation followed by deterministic lag projection."""

    n_basis: int = N_BASIS
    log_lag: bool = True

    def fit(self, X: np.ndarray) -> "SmoothLagPreprocessor":
        self.imputer_ = SimpleImputer(strategy="median", keep_empty_features=True)
        daily = self.imputer_.fit_transform(np.asarray(X, dtype=float))
        self.basis_ = smooth_lag_basis(n_basis=self.n_basis, log_lag=self.log_lag)
        projected = self._project(daily)
        self.scaler_ = StandardScaler().fit(projected)
        return self

    def _project(self, daily: np.ndarray) -> np.ndarray:
        blocks = []
        for channel_index in range(len(RAW_CHANNELS)):
            start = channel_index * LOOKBACK_DAYS
            blocks.append(daily[:, start : start + LOOKBACK_DAYS] @ self.basis_)
        return np.column_stack(blocks)

    def transform(self, X: np.ndarray) -> np.ndarray:
        daily = self.imputer_.transform(np.asarray(X, dtype=float))
        return self.scaler_.transform(self._project(daily))

    def feature_names(self) -> list[str]:
        return [f"{channel}__smooth_basis_{index:02d}" for channel in RAW_CHANNELS for index in range(self.n_basis)]


def pooled_design(
    smooth: np.ndarray,
    species: Iterable[str],
    *,
    species_order: list[str],
    deviation_scale: float | None,
) -> np.ndarray:
    """Build shared weather + species intercepts + optional shrunken deviations."""
    species_values = list(species)
    lookup = {value: index for index, value in enumerate(species_order)}
    one_hot = np.zeros((len(species_values), max(0, len(species_order) - 1)), dtype=float)
    for row, value in enumerate(species_values):
        if value not in lookup:
            raise ValueError(f"unknown hold-out species: {value}")
        index = lookup[value]
        if index:
            one_hot[row, index - 1] = 1.0
    blocks = [np.asarray(smooth, dtype=float), one_hot]
    if deviation_scale is not None:
        if deviation_scale <= 0:
            raise ValueError("deviation_scale must be positive")
        for value in species_order:
            mask = np.asarray([item == value for item in species_values], dtype=float).reshape(-1, 1)
            blocks.append(smooth * mask / deviation_scale)
    return np.column_stack(blocks)


def fit_logistic(X: np.ndarray, y: np.ndarray, *, C: float) -> LogisticRegression:
    model = LogisticRegression(C=C, solver="lbfgs", max_iter=3000, random_state=42)
    model.fit(X, y)
    return model
