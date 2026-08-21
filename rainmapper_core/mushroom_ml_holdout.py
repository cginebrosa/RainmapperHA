"""Generic row-level, non-operational hold-out evaluation for mushroom ML."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable
import warnings

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning

from rainmapper_core import mushroom_ml_biology_v3_evaluation as v3_evaluation
from rainmapper_core import mushroom_ml_experiment_trainer
from rainmapper_core.mushroom_ml_sparse_group import SparseGroupLogisticClassifier


CURRENT_ESTIMATORS = mushroom_ml_experiment_trainer.EXPERIMENT_ESTIMATOR_IDS
V5_ESTIMATORS = ("elastic_net_logistic_raw365_v1", "sparse_group_logistic_raw365_v1")


def comparison_key(sample: dict[str, Any]) -> tuple[str, int]:
    metadata = sample.get("metadata") or {}
    return (
        str(metadata.get("observation_id") or sample.get("sample_id") or ""),
        int(metadata.get("horizon_days") or 7),
    )


def eligible_samples(benchmark: dict[str, Any]) -> list[dict[str, Any]]:
    return v3_evaluation._eligible_samples(benchmark)


def matrix(samples: list[dict[str, Any]], columns: list[str]) -> tuple[np.ndarray, np.ndarray]:
    X = np.asarray(
        [
            [
                float((sample.get("predictive_features") or {}).get(column))
                if (sample.get("predictive_features") or {}).get(column) is not None
                else np.nan
                for column in columns
            ]
            for sample in samples
        ],
        dtype=float,
    )
    y = np.asarray([1 if sample.get("prediction_target") == "favorable" else 0 for sample in samples], dtype=int)
    return X, y


def metrics(y: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    predicted = (probabilities >= 0.5).astype(int)
    result = {
        "n": int(len(y)),
        "brier_score": round(float(brier_score_loss(y, probabilities)), 6),
        "log_loss": round(float(log_loss(y, probabilities, labels=[0, 1])), 6),
        "balanced_accuracy": round(float(balanced_accuracy_score(y, predicted)), 6) if len(np.unique(y)) == 2 else None,
        "confusion_matrix": confusion_matrix(y, predicted, labels=[0, 1]).tolist(),
        "favorable_ratio": round(float(np.mean(y)), 6),
    }
    if len(np.unique(y)) == 2:
        result["roc_auc"] = round(float(roc_auc_score(y, probabilities)), 6)
        result["pr_auc"] = round(float(average_precision_score(y, probabilities)), 6)
        clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
        logits = np.log(clipped / (1.0 - clipped)).reshape(-1, 1)
        try:
            calibrator = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
            calibrator.fit(logits, y)
            result["calibration_intercept"] = round(float(calibrator.intercept_[0]), 6)
            result["calibration_slope"] = round(float(calibrator.coef_[0, 0]), 6)
        except ValueError:
            result["calibration_intercept"] = None
            result["calibration_slope"] = None
    else:
        result.update({
            "roc_auc": None,
            "pr_auc": None,
            "calibration_intercept": None,
            "calibration_slope": None,
        })
    return result


def _phenology_probabilities(
    train_samples: list[dict[str, Any]], test_samples: list[dict[str, Any]], y_train: np.ndarray
) -> np.ndarray:
    def values(samples: list[dict[str, Any]]) -> np.ndarray:
        result = []
        for sample in samples:
            features = sample.get("predictive_features") or {}
            if features.get("target_day_sin") is not None and features.get("target_day_cos") is not None:
                result.append([float(features["target_day_sin"]), float(features["target_day_cos"])])
                continue
            target_date = str((sample.get("metadata") or {}).get("target_date") or "")
            day = __import__("datetime").date.fromisoformat(target_date).timetuple().tm_yday
            angle = 2.0 * np.pi * (day - 1) / 365.2425
            result.append([float(np.sin(angle)), float(np.cos(angle))])
        return np.asarray(result, dtype=float)

    model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000, random_state=42)
    model.fit(values(train_samples), y_train)
    return model.predict_proba(values(test_samples))[:, 1]


def _preprocess(X_train: np.ndarray, X_test: np.ndarray) -> tuple[np.ndarray, np.ndarray, SimpleImputer, StandardScaler]:
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    train = imputer.fit_transform(X_train)
    test = imputer.transform(X_test)
    scaler = StandardScaler()
    return scaler.fit_transform(train), scaler.transform(test), imputer, scaler


def _inner_splits(samples: list[dict[str, Any]], group_days: int) -> list[tuple[np.ndarray, np.ndarray]]:
    group_key = f"validation_group_{group_days}d"
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, sample in enumerate(samples):
        grouped[str((sample.get("metadata") or {}).get(group_key) or index)].append(index)
    ordered = sorted(
        grouped.values(),
        key=lambda indices: max(str((samples[index].get("metadata") or {}).get("target_date") or "") for index in indices),
    )
    splits = []
    for fraction in (0.6, 0.8):
        boundary = int(len(ordered) * fraction)
        if boundary < 1 or boundary >= len(ordered):
            continue
        train = np.asarray([index for group in ordered[:boundary] for index in group], dtype=int)
        valid = np.asarray([index for group in ordered[boundary:] for index in group], dtype=int)
        if len(np.unique([samples[index]["prediction_target"] for index in train])) == 2 and len(valid):
            splits.append((train, valid))
    return splits


def _groups(columns: list[str]) -> np.ndarray:
    ids: dict[str, int] = {}
    values = []
    for column in columns:
        channel = column.split("__lag_", 1)[0] if "__lag_" in column else column
        ids.setdefault(channel, len(ids))
        values.append(ids[channel])
    return np.asarray(values, dtype=int)


def _select_v5(
    estimator_id: str,
    samples: list[dict[str, Any]],
    X: np.ndarray,
    y: np.ndarray,
    columns: list[str],
    group_days: int,
) -> tuple[dict[str, Any], bool]:
    splits = _inner_splits(samples, group_days)
    if estimator_id == V5_ESTIMATORS[0]:
        configs = [
            {"C": C, "l1_ratio": ratio, "class_weight": None}
            for C in (0.01, 0.1, 1.0)
            for ratio in (0.1, 0.9)
        ]
        fallback = {"C": 0.1, "l1_ratio": 0.5, "class_weight": None}
    else:
        configs = [
            {"regularization": strength, "l1_ratio": ratio}
            for strength in (0.01, 0.1, 1.0)
            for ratio in (0.25, 0.5, 0.75)
        ]
        fallback = {"regularization": 0.1, "l1_ratio": 0.5}
    if not splits:
        return fallback, False
    scored: list[tuple[float, dict[str, Any]]] = []
    for config in configs:
        fold_scores = []
        for train_indices, valid_indices in splits:
            train_X, valid_X, _imputer, _scaler = _preprocess(X[train_indices], X[valid_indices])
            train_y = y[train_indices]
            try:
                if estimator_id == V5_ESTIMATORS[0]:
                    model = LogisticRegression(
                        solver="saga", max_iter=500,
                        random_state=42, tol=1e-3, **config,
                    )
                else:
                    model = SparseGroupLogisticClassifier(
                        groups=_groups(columns), max_iter=350, tolerance=1e-4, **config
                    )
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", (FutureWarning, ConvergenceWarning))
                    model.fit(train_X, train_y)
                if estimator_id == V5_ESTIMATORS[1] and not model.converged_:
                    raise ValueError("sparse-group configuration did not converge")
                fold_scores.append(float(brier_score_loss(y[valid_indices], model.predict_proba(valid_X)[:, 1])))
            except (ValueError, FloatingPointError):
                fold_scores = []
                break
        if fold_scores:
            scored.append((float(np.mean(fold_scores)), config))
    if not scored:
        return fallback, False
    scored.sort(key=lambda item: (round(item[0], 6), item[1].get("C", -item[1].get("regularization", 0)), -item[1]["l1_ratio"]))
    return scored[0][1], True


def evaluate_dataset(
    benchmark: dict[str, Any],
    *,
    version_id: str,
    profile_id: str,
    group_days: int,
    train_keys: set[tuple[str, int]],
    test_keys: set[tuple[str, int]],
    mode: str,
    split_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    samples = eligible_samples(benchmark)
    train = [sample for sample in samples if comparison_key(sample) in train_keys]
    test = [sample for sample in samples if comparison_key(sample) in test_keys]
    feature_set = benchmark.get("feature_set") or {}
    if mode == "v5":
        columns = list((feature_set.get("profiles") or {})[profile_id])
        estimator_ids = V5_ESTIMATORS
    else:
        columns = list(feature_set.get("predictive_feature_cols") or feature_set.get("feature_cols") or [])
        estimator_ids = CURRENT_ESTIMATORS
    report: dict[str, Any] = {"version_id": version_id, "profile_id": profile_id, "species": {}}
    rows: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    species_ids = sorted({str((sample.get("metadata") or {}).get("species_id")) for sample in train + test})
    for species_id in species_ids:
        species_train = [sample for sample in train if str((sample.get("metadata") or {}).get("species_id")) == species_id]
        species_test = [sample for sample in test if str((sample.get("metadata") or {}).get("species_id")) == species_id]
        species_report: dict[str, Any] = {"n_train": len(species_train), "n_test": len(species_test), "estimators": {}}
        report["species"][species_id] = species_report
        if not species_train or not species_test:
            species_report["reason"] = "empty partition"
            continue
        X_train, y_train = matrix(species_train, columns)
        X_test, y_test = matrix(species_test, columns)
        if len(np.unique(y_train)) < 2:
            species_report["reason"] = "training partition has a single class"
            continue
        prevalence = float(np.mean(y_train))
        representative_metadata = species_train[0].get("metadata") or {}
        temporal_contract_id = str(representative_metadata.get("temporal_contract_id") or "")
        effective_split_id = split_id or f"fruiting_groups_{group_days}d"
        prevalence_probabilities = np.full(len(y_test), prevalence)
        phenology_probabilities = _phenology_probabilities(species_train, species_test, y_train)
        prevalence_metrics = metrics(y_test, prevalence_probabilities)
        phenology_metrics = metrics(y_test, phenology_probabilities)
        species_report["baselines"] = {
            "training_prevalence": prevalence_metrics,
            "phenology_sin_cos": phenology_metrics,
        }
        probabilities_by_estimator: dict[str, np.ndarray] = {}
        for estimator_id in estimator_ids:
            try:
                if mode == "current":
                    unavailable = mushroom_ml_experiment_trainer._estimator_unavailable_reason(estimator_id, y_train)
                    if estimator_id == "knn_distance_v1" and len(y_train) < 7:
                        unavailable = "KNN requires at least seven training samples"
                    if unavailable:
                        raise ValueError(unavailable)
                    model = mushroom_ml_experiment_trainer._pipeline(estimator_id)
                    model.fit(X_train, y_train)
                    probabilities = model.predict_proba(X_test)[:, 1]
                    selected_config = None
                    selected_inside = None
                else:
                    selected_config, selected_inside = _select_v5(
                        estimator_id, species_train, X_train, y_train, columns, group_days
                    )
                    scaled_train, scaled_test, imputer, scaler = _preprocess(X_train, X_test)
                    if estimator_id == V5_ESTIMATORS[0]:
                        model = LogisticRegression(
                            solver="saga", max_iter=1500,
                            random_state=42, tol=1e-3, **selected_config,
                        )
                    else:
                        model = SparseGroupLogisticClassifier(
                            groups=_groups(columns), max_iter=2000, tolerance=1e-5,
                            **selected_config,
                        )
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", (FutureWarning, ConvergenceWarning))
                        model.fit(scaled_train, y_train)
                    if estimator_id == V5_ESTIMATORS[1] and not model.converged_:
                        raise ValueError("sparse-group estimator did not converge")
                    probabilities = model.predict_proba(scaled_test)[:, 1]
                    coefficients = np.asarray(model.coef_[0], dtype=float)
                    scale = np.asarray(scaler.scale_, dtype=float)
                    for column, coefficient, column_scale in zip(columns, coefficients, scale, strict=True):
                        if abs(coefficient) > 1e-10:
                            selections.append({
                                "version_id": version_id, "profile_id": profile_id,
                                "temporal_contract_id": temporal_contract_id,
                                "split_id": effective_split_id,
                                "group_days": group_days, "species_id": species_id,
                                "estimator_id": estimator_id, "feature": column,
                                "coefficient_standardized": round(float(coefficient), 10),
                                "coefficient_unstandardized": round(float(coefficient / column_scale), 10)
                                if column_scale else 0.0,
                                "selected": True,
                            })
                probabilities_by_estimator[estimator_id] = probabilities
                result_metrics = metrics(y_test, probabilities)
                baseline_brier = float(brier_score_loss(y_test, np.full(len(y_test), prevalence)))
                result_metrics["brier_delta_vs_prevalence"] = round(baseline_brier - result_metrics["brier_score"], 6)
                result_metrics["brier_delta_vs_phenology"] = round(
                    phenology_metrics["brier_score"] - result_metrics["brier_score"], 6
                )
                species_report["estimators"][estimator_id] = {
                    "available": True, "metrics": result_metrics,
                    "selected_config": selected_config,
                    "inner_selection_available": selected_inside,
                }
                if mode == "v5":
                    species_report["estimators"][estimator_id]["convergence"] = {
                        "n_iter": int(np.asarray(model.n_iter_).ravel()[0]),
                        "converged": bool(getattr(model, "converged_", True)),
                    }
            except (ValueError, FloatingPointError) as exc:
                species_report["estimators"][estimator_id] = {"available": False, "reason": str(exc)}
        for index, sample in enumerate(species_test):
            metadata = sample.get("metadata") or {}
            sample_id = str(sample.get("sample_id") or "")
            row_temporal_contract_id = metadata.get("temporal_contract_id")
            if not row_temporal_contract_id:
                sample_parts = sample_id.split("|")
                row_temporal_contract_id = sample_parts[1] if len(sample_parts) >= 3 else None
            row_key = "|".join(
                (
                    version_id,
                    profile_id,
                    effective_split_id,
                    str(group_days),
                    species_id,
                    sample_id,
                )
            )
            rows.append({
                "row_key": row_key,
                "sample_id": sample_id,
                "observation_id": metadata.get("observation_id"),
                "species_id": species_id,
                "area_id": metadata.get("area_id"),
                "micro_area_id": metadata.get("micro_area_id"),
                "target_date": metadata.get("target_date"),
                "cutoff_date": metadata.get("cutoff_date"),
                "temporal_contract_id": row_temporal_contract_id,
                "horizon_days": int(metadata.get("horizon_days") or 7),
                "validation_group_id": metadata.get(f"validation_group_{group_days}d"),
                "version_id": version_id,
                "profile_id": profile_id,
                "group_days": group_days,
                "split_id": effective_split_id,
                "campaign_block_id": f"{metadata.get('area_id')}|{str(metadata.get('target_date') or '')[:4]}"
                if effective_split_id == "campaign_area_year_70_30" else None,
                "prediction_target": sample.get("prediction_target"),
                "y_true": int(y_test[index]),
                "train_prevalence_probability": round(prevalence, 10),
                "estimator_probabilities": {
                    estimator_id: round(float(probabilities[index]), 10)
                    for estimator_id, probabilities in probabilities_by_estimator.items()
                },
                "diagnostic_weather_summary": metadata.get("diagnostic_weather_summary", {}),
                "coverage": (sample.get("quality") or {}).get("raw365_coverage_by_channel", {}),
            })
    return report, rows, selections
