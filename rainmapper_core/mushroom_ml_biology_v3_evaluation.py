"""Non-operational, observation-preserving evaluation for Biology V3.

The evaluator never serializes fitted models.  Its only output is an auditable
metrics report built from chronological hold-outs whose fruiting groups never
cross the train/test boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from itertools import combinations
from typing import Any

from rainmapper_core import mushroom_ml_experiments
from rainmapper_core import mushroom_ml_experiment_trainer
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_prediction_interpretation
from rainmapper_core.mushroom_ml_biology_v3 import observation_validation_groups


FEATURE_FAMILIES = {
    "active_full": lambda name: True,
    "without_rain": lambda name: not (
        name.startswith("rain_") or name.startswith("days_since_rain")
    ),
    "without_temperature_humidity": lambda name: not (
        name.startswith("temp_") or name.startswith("humidity_")
    ),
    "without_temperature": lambda name: not name.startswith("temp_"),
    "without_humidity": lambda name: not name.startswith("humidity_"),
    "weather_only": lambda name: name.startswith(
        ("rain_", "days_since_rain", "dry_spell_", "temp_", "humidity_")
    ),
}


def _eligible_samples(benchmark: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for source in benchmark.get("samples", []):
        if not isinstance(source, dict):
            continue
        metadata = dict(source.get("metadata") or {})
        metadata.setdefault("species_id", source.get("species_id"))
        metadata.setdefault("area_id", source.get("area_id"))
        metadata.setdefault("target_date", metadata.get("target_date"))
        eligible = (source.get("quality") or {}).get(
            "training_eligible", metadata.get("training_eligible", True)
        )
        if source.get("prediction_target") not in {"favorable", "unfavorable"} or not eligible:
            continue
        normalized.append(
            {
                **source,
                "predictive_features": dict(
                    source.get("predictive_features") or source.get("features") or {}
                ),
                "quality": dict(source.get("quality") or {}),
                "metadata": metadata,
            }
        )
    for days in (7, 14):
        key = f"validation_group_{days}d"
        missing = [row for row in normalized if not (row.get("metadata") or {}).get(key)]
        if not missing:
            continue
        group_inputs = [
            {
                "species_id": (row.get("metadata") or {}).get("species_id"),
                "area_id": (row.get("metadata") or {}).get("area_id"),
                "observed_at": (row.get("metadata") or {}).get("target_date"),
            }
            for row in normalized
        ]
        groups = observation_validation_groups(
            group_inputs, micro_area_to_area={}, max_duration_days=days
        )
        for row, group_id in zip(normalized, groups, strict=True):
            row["metadata"].setdefault(key, group_id)
    return normalized


def chronological_group_split(
    samples: list[dict[str, Any]],
    *,
    group_days: int,
    train_fraction: float = 0.7,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split chronologically per species while keeping complete fruiting groups."""
    if group_days not in {7, 14}:
        raise ValueError("group_days must be 7 or 14")
    key = f"validation_group_{group_days}d"
    train: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    by_species: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for sample in samples:
        metadata = sample.get("metadata") or {}
        species_id = str(metadata.get("species_id") or "")
        group_id = str(metadata.get(key) or "")
        if species_id and group_id:
            by_species[species_id][group_id].append(sample)
    for groups in by_species.values():
        ordered = sorted(
            groups.values(),
            key=lambda rows: max(
                str((row.get("metadata") or {}).get("target_date") or "")
                for row in rows
            ),
        )
        if len(ordered) < 2:
            train.extend(row for rows in ordered for row in rows)
            continue
        boundary = max(1, min(len(ordered) - 1, int(len(ordered) * train_fraction)))
        train.extend(row for rows in ordered[:boundary] for row in rows)
        test.extend(row for rows in ordered[boundary:] for row in rows)
    return train, test


def _matrix(samples: list[dict[str, Any]], feature_cols: list[str]) -> tuple[Any, Any]:
    import numpy as np  # noqa: PLC0415

    return (
        np.asarray(
            [
                [float((sample.get("predictive_features") or {})[name]) for name in feature_cols]
                for sample in samples
            ],
            dtype=float,
        ),
        np.asarray(
            [1 if sample.get("prediction_target") == "favorable" else 0 for sample in samples],
            dtype=int,
        ),
    )


def _metrics(y_true: Any, probabilities: Any) -> dict[str, Any]:
    import numpy as np  # noqa: PLC0415
    from sklearn.metrics import balanced_accuracy_score, brier_score_loss, log_loss  # noqa: PLC0415

    predicted = (probabilities >= 0.5).astype(int)
    bins: list[dict[str, Any]] = []
    calibration_error = 0.0
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = lower + 0.2
        mask = (probabilities >= lower) & (
            probabilities <= upper if upper >= 1.0 else probabilities < upper
        )
        if not np.any(mask):
            continue
        predicted_mean = float(np.mean(probabilities[mask]))
        observed_mean = float(np.mean(y_true[mask]))
        weight = float(np.mean(mask))
        calibration_error += weight * abs(predicted_mean - observed_mean)
        bins.append(
            {
                "lower": lower,
                "upper": round(upper, 1),
                "n": int(np.sum(mask)),
                "predicted_mean": round(predicted_mean, 4),
                "observed_mean": round(observed_mean, 4),
            }
        )
    balanced_accuracy = (
        round(float(balanced_accuracy_score(y_true, predicted)), 4)
        if len(np.unique(y_true)) == 2
        else None
    )
    return {
        "n": int(len(y_true)),
        "favorable_ratio": round(float(np.mean(y_true)), 4),
        "balanced_accuracy": balanced_accuracy,
        "brier_score": round(float(brier_score_loss(y_true, probabilities)), 4),
        "log_loss": round(float(log_loss(y_true, probabilities, labels=[0, 1])), 4),
        "expected_calibration_error": round(calibration_error, 4),
        "calibration_bins": bins,
    }


def _pairwise_consensus(
    probabilities_by_estimator: dict[str, Any],
    *,
    held_out_observation_count: int,
) -> dict[str, dict[str, Any]]:
    """Compare estimators row by row using the Predictor's existing gaps."""
    import numpy as np  # noqa: PLC0415

    reports: dict[str, dict[str, Any]] = {}
    for left_id, right_id in combinations(
        mushroom_ml_experiment_trainer.EXPERIMENT_ESTIMATOR_IDS, 2
    ):
        left = probabilities_by_estimator.get(left_id)
        right = probabilities_by_estimator.get(right_id)
        if left is None or right is None:
            continue
        left_values = np.asarray(left, dtype=float)
        right_values = np.asarray(right, dtype=float)
        if len(left_values) != len(right_values):
            raise AssertionError("pairwise estimator predictions are not row-aligned")
        gaps = np.abs(left_values - right_values)
        high = gaps <= mushroom_prediction_interpretation.HIGH_AGREEMENT_GAP
        low = gaps >= mushroom_prediction_interpretation.LOW_AGREEMENT_GAP
        moderate = ~(high | low)
        same_side = (left_values >= 0.5) == (right_values >= 0.5)
        pair_id = f"{left_id}__{right_id}"
        reports[pair_id] = {
            "left_estimator_id": left_id,
            "right_estimator_id": right_id,
            "n": int(len(gaps)),
            "held_out_observation_count": held_out_observation_count,
            "mean_absolute_probability_gap": round(float(np.mean(gaps)), 4),
            "maximum_absolute_probability_gap": round(float(np.max(gaps)), 4),
            "same_side_of_0_5_rate": round(float(np.mean(same_side)), 4),
            "prediction_consensus": {
                "high_count": int(np.sum(high)),
                "high_rate": round(float(np.mean(high)), 4),
                "moderate_count": int(np.sum(moderate)),
                "moderate_rate": round(float(np.mean(moderate)), 4),
                "low_count": int(np.sum(low)),
                "low_rate": round(float(np.mean(low)), 4),
            },
        }
    return reports


def _metrics_by_horizon(
    y_true: Any,
    probabilities: Any,
    horizons: Any,
) -> dict[str, dict[str, Any]]:
    """Score one fitted temporal model on each held-out horizon without refit."""
    import numpy as np  # noqa: PLC0415

    y_values = np.asarray(y_true)
    probability_values = np.asarray(probabilities, dtype=float)
    horizon_values = np.asarray(horizons, dtype=int)
    return {
        str(int(horizon_days)): _metrics(
            y_values[horizon_values == horizon_days],
            probability_values[horizon_values == horizon_days],
        )
        for horizon_days in sorted(set(int(value) for value in horizon_values))
    }


def evaluate_benchmark(
    benchmark: dict[str, Any],
    *,
    group_days: int,
    species_ids: set[str] | None = None,
    feature_families: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate retained feature families without emitting a reusable model."""
    import numpy as np  # noqa: PLC0415

    samples = _eligible_samples(benchmark)
    if species_ids is not None:
        samples = [
            row
            for row in samples
            if str((row.get("metadata") or {}).get("species_id") or "") in species_ids
        ]
    train, test = chronological_group_split(samples, group_days=group_days)
    train_groups = {
        (row.get("metadata") or {}).get(f"validation_group_{group_days}d") for row in train
    }
    test_groups = {
        (row.get("metadata") or {}).get(f"validation_group_{group_days}d") for row in test
    }
    if train_groups & test_groups:
        raise AssertionError("a fruiting group crossed the chronological split")
    feature_set = benchmark.get("feature_set") or {}
    active_cols = [
        str(name)
        for name in (
            feature_set.get("predictive_feature_cols")
            or feature_set.get("feature_cols")
            or []
        )
    ]
    reports: dict[str, Any] = {}
    selected_families = feature_families or FEATURE_FAMILIES
    for family_id, selector in selected_families.items():
        feature_cols = [name for name in active_cols if selector(name)]
        if not feature_cols:
            reports[family_id] = {
                "feature_cols": [],
                "species": {},
                "pooled_metrics": {"n": 0, "note": "feature family is empty"},
            }
            continue
        estimator_ids = mushroom_ml_experiment_trainer.EXPERIMENT_ESTIMATOR_IDS
        estimator_species: dict[str, dict[str, Any]] = {
            "train_prevalence_v1": {},
            **{estimator_id: {} for estimator_id in estimator_ids},
        }
        held: dict[str, tuple[list[int], list[float]]] = {
            estimator_id: ([], []) for estimator_id in estimator_species
        }
        evaluated_species_ids = sorted(
            {str((row.get("metadata") or {}).get("species_id") or "") for row in samples}
        )
        species_probabilities: dict[str, dict[str, Any]] = {}
        species_horizons: dict[str, Any] = {}
        for species_id in evaluated_species_ids:
            species_train = [
                row for row in train if (row.get("metadata") or {}).get("species_id") == species_id
            ]
            species_test = [
                row for row in test if (row.get("metadata") or {}).get("species_id") == species_id
            ]
            if not species_train or not species_test:
                for reports_by_species in estimator_species.values():
                    reports_by_species[species_id] = {"available": False, "reason": "empty partition"}
                continue
            X_train, y_train = _matrix(species_train, feature_cols)
            X_test, y_test = _matrix(species_test, feature_cols)
            train_observation_count = len(
                {
                    str((row.get("metadata") or {}).get("observation_id") or row.get("sample_id"))
                    for row in species_train
                }
            )
            test_observation_count = len(
                {
                    str((row.get("metadata") or {}).get("observation_id") or row.get("sample_id"))
                    for row in species_test
                }
            )
            if len(np.unique(y_train)) < 2:
                unavailable = {
                    "available": False,
                    "reason": "chronological training partition has a single class",
                    "n_train": len(species_train),
                    "n_test": len(species_test),
                    "n_train_observations": train_observation_count,
                    "n_test_observations": test_observation_count,
                }
                for reports_by_species in estimator_species.values():
                    reports_by_species[species_id] = dict(unavailable)
                continue
            baseline_probability = float(np.mean(y_train))
            baseline_probabilities = np.full(len(y_test), baseline_probability, dtype=float)
            species_probabilities[species_id] = {}
            horizons = np.asarray(
                [
                    int((row.get("metadata") or {}).get("horizon_days") or 7)
                    for row in species_test
                ],
                dtype=int,
            )
            species_horizons[species_id] = horizons
            baseline_metrics = _metrics(y_test, baseline_probabilities)
            baseline_metrics_by_horizon = _metrics_by_horizon(
                y_test, baseline_probabilities, horizons
            )
            estimator_species["train_prevalence_v1"][species_id] = {
                "available": True,
                "n_train": len(species_train),
                "n_test": len(species_test),
                "n_train_observations": train_observation_count,
                "n_test_observations": test_observation_count,
                "metrics": baseline_metrics,
                "metrics_by_horizon": baseline_metrics_by_horizon,
            }
            held["train_prevalence_v1"][0].extend(int(value) for value in y_test)
            held["train_prevalence_v1"][1].extend(
                float(value) for value in baseline_probabilities
            )
            for estimator_id in estimator_ids:
                unavailable_reason = (
                    mushroom_ml_experiment_trainer._estimator_unavailable_reason(
                        estimator_id, y_train
                    )
                )
                if estimator_id == "knn_distance_v1" and len(y_train) < 7:
                    unavailable_reason = "KNN requires at least seven training samples"
                if unavailable_reason is not None:
                    estimator_species[estimator_id][species_id] = {
                        "available": False,
                        "reason": unavailable_reason,
                        "n_train": len(species_train),
                        "n_test": len(species_test),
                        "n_train_observations": train_observation_count,
                        "n_test_observations": test_observation_count,
                    }
                    continue
                model = mushroom_ml_experiment_trainer._pipeline(estimator_id)
                model.fit(X_train, y_train)
                probabilities = model.predict_proba(X_test)[:, 1]
                species_probabilities[species_id][estimator_id] = probabilities
                metrics = _metrics(y_test, probabilities)
                baseline_brier = float(baseline_metrics["brier_score"])
                model_brier = float(metrics["brier_score"])
                metrics["brier_delta_vs_prevalence"] = round(
                    baseline_brier - model_brier, 4
                )
                metrics["brier_skill_vs_prevalence"] = round(
                    1.0 - (model_brier / baseline_brier), 4
                ) if baseline_brier > 0 else None
                metrics_by_horizon = _metrics_by_horizon(
                    y_test, probabilities, horizons
                )
                for horizon_key, horizon_metrics in metrics_by_horizon.items():
                    baseline_horizon_brier = float(
                        baseline_metrics_by_horizon[horizon_key]["brier_score"]
                    )
                    horizon_brier = float(horizon_metrics["brier_score"])
                    horizon_metrics["brier_delta_vs_prevalence"] = round(
                        baseline_horizon_brier - horizon_brier, 4
                    )
                    horizon_metrics["brier_skill_vs_prevalence"] = (
                        round(1.0 - (horizon_brier / baseline_horizon_brier), 4)
                        if baseline_horizon_brier > 0
                        else None
                    )
                estimator_species[estimator_id][species_id] = {
                    "available": True,
                    "n_train": len(species_train),
                    "n_test": len(species_test),
                    "n_train_observations": train_observation_count,
                    "n_test_observations": test_observation_count,
                    "metrics": metrics,
                    "metrics_by_horizon": metrics_by_horizon,
                }
                held[estimator_id][0].extend(int(value) for value in y_test)
                held[estimator_id][1].extend(float(value) for value in probabilities)
        estimator_reports: dict[str, Any] = {}
        for estimator_id, species_report in estimator_species.items():
            held_y, held_probabilities = held[estimator_id]
            estimator_reports[estimator_id] = {
                "species": species_report,
                "pooled_metrics_diagnostic_only": (
                    _metrics(np.asarray(held_y), np.asarray(held_probabilities))
                    if held_y
                    else {"n": 0, "note": "no species had an evaluable chronological split"}
                ),
            }
        primary_estimator_id = "logistic_regression_reduced_v1"
        species_reports = estimator_species[primary_estimator_id]
        pooled_lr = estimator_reports[primary_estimator_id]["pooled_metrics_diagnostic_only"]
        reports[family_id] = {
            "feature_cols": feature_cols,
            "species": species_reports,
            "pooled_metrics": pooled_lr,
            "estimators": estimator_reports,
            "estimator_status": {
                estimator_id: (
                    "active"
                    if estimator_id in {"logistic_regression_reduced_v1", "random_forest_restricted_v1"}
                    else "experimental"
                )
                for estimator_id in estimator_ids
            },
            "pairwise_consensus_by_species": {
                species_id: _pairwise_consensus(
                    probabilities_by_estimator,
                    held_out_observation_count=len(
                        {
                            str(
                                (row.get("metadata") or {}).get("observation_id")
                                or row.get("sample_id")
                            )
                            for row in test
                            if (row.get("metadata") or {}).get("species_id") == species_id
                        }
                    ),
                )
                for species_id, probabilities_by_estimator in species_probabilities.items()
            },
            "pairwise_consensus_by_species_and_horizon": {
                species_id: {
                    str(horizon_days): _pairwise_consensus(
                        {
                            estimator_id: np.asarray(probabilities)[
                                species_horizons[species_id] == horizon_days
                            ]
                            for estimator_id, probabilities in probabilities_by_estimator.items()
                        },
                        held_out_observation_count=int(
                            np.sum(species_horizons[species_id] == horizon_days)
                        ),
                    )
                    for horizon_days in sorted(
                        set(int(value) for value in species_horizons[species_id])
                    )
                }
                for species_id, probabilities_by_estimator in species_probabilities.items()
            },
            "pairwise_consensus_contract": {
                "comparison_unit": "same held-out row within species and temporal contract",
                "high": (
                    f"absolute probability gap <= "
                    f"{mushroom_prediction_interpretation.HIGH_AGREEMENT_GAP}"
                ),
                "moderate": (
                    f"absolute probability gap > "
                    f"{mushroom_prediction_interpretation.HIGH_AGREEMENT_GAP} and < "
                    f"{mushroom_prediction_interpretation.LOW_AGREEMENT_GAP}"
                ),
                "low": (
                    f"absolute probability gap >= "
                    f"{mushroom_prediction_interpretation.LOW_AGREEMENT_GAP}"
                ),
                "aggregate_policy": "report rates; do not invent one species-wide label",
            },
            "pooled_metrics_policy": "diagnostic_only_never_select_across_species",
        }
    return {
        "schema_version": "1.0",
        "kind": "biology_v3_non_operational_evaluation",
        "evaluation_axes": {
            "temporal_contract": (benchmark.get("feature_set") or {}).get("id"),
            "estimators": list(mushroom_ml_experiment_trainer.EXPERIMENT_ESTIMATOR_IDS),
            "species": sorted(
                {
                    str((row.get("metadata") or {}).get("species_id") or "")
                    for row in samples
                }
            ),
            "fitted_model_definition": "one species x one temporal contract x one estimator",
        },
        "feature_set_id": (benchmark.get("feature_set") or {}).get("id"),
        "split": {
            "method": "chronological_by_species_whole_fruiting_groups_70_30",
            "group_days": group_days,
            "eligible_samples": len(samples),
            "train_samples": len(train),
            "test_samples": len(test),
            "train_group_count": len(train_groups),
            "test_group_count": len(test_groups),
            "group_overlap_count": len(train_groups & test_groups),
        },
        "families": reports,
        "model_artifact_written": False,
    }


def _evaluation_report_for_horizon(
    report: dict[str, Any],
    *,
    horizon_days: int,
    parent_membership_sha256: str,
) -> dict[str, Any]:
    """Project metrics from one fitted temporal model onto one horizon."""
    horizon_key = str(horizon_days)
    families: dict[str, Any] = {}
    for family_id, family in (report.get("families") or {}).items():
        estimator_reports: dict[str, Any] = {}
        for estimator_id, estimator in (family.get("estimators") or {}).items():
            species_reports: dict[str, Any] = {}
            for species_id, species in (estimator.get("species") or {}).items():
                metrics = (species.get("metrics_by_horizon") or {}).get(horizon_key)
                if metrics is None:
                    species_reports[species_id] = {
                        "available": False,
                        "reason": "no held-out rows for this horizon",
                    }
                    continue
                projected = {
                    key: deepcopy(value)
                    for key, value in species.items()
                    if key not in {"metrics", "metrics_by_horizon"}
                }
                projected["metrics"] = deepcopy(metrics)
                projected["n_test"] = int(metrics.get("n") or 0)
                projected["n_test_observations"] = int(metrics.get("n") or 0)
                species_reports[species_id] = projected
            estimator_reports[estimator_id] = {
                "species": species_reports,
                "pooled_metrics_diagnostic_only": {
                    "note": "not pooled; metrics are filtered from the full temporal model"
                },
            }
        primary_id = "logistic_regression_reduced_v1"
        families[family_id] = {
            "feature_cols": deepcopy(family.get("feature_cols") or []),
            "species": deepcopy(
                (estimator_reports.get(primary_id) or {}).get("species") or {}
            ),
            "pooled_metrics": {
                "note": "not pooled; metrics are filtered from the full temporal model"
            },
            "estimators": estimator_reports,
            "estimator_status": deepcopy(family.get("estimator_status") or {}),
            "pairwise_consensus_by_species": {
                species_id: deepcopy(by_horizon.get(horizon_key) or {})
                for species_id, by_horizon in (
                    family.get("pairwise_consensus_by_species_and_horizon") or {}
                ).items()
            },
            "pairwise_consensus_contract": deepcopy(
                family.get("pairwise_consensus_contract") or {}
            ),
            "pooled_metrics_policy": "diagnostic_only_never_select_across_species",
        }
    return {
        "schema_version": "1.1-heldout-horizon-projection",
        "kind": "biology_v3_horizon_projection_no_refit",
        "evaluation_axes": deepcopy(report.get("evaluation_axes") or {}),
        "feature_set_id": report.get("feature_set_id"),
        "split": {
            "method": "filter_full_temporal_contract_holdout_predictions_no_refit",
            "horizon_days": horizon_days,
            "parent_membership_sha256": parent_membership_sha256,
        },
        "families": families,
        "model_artifact_written": False,
    }


def build_observation_altitude_v2_benchmark(
    feature_rows: list[dict[str, Any]],
    v3_benchmark: dict[str, Any],
    *,
    micro_area_to_area: dict[str, str],
    area_representative_altitudes: dict[str, float],
) -> dict[str, Any]:
    """Rebuild altitude V2 features on the exact observation rows used by V3."""
    rows_by_id = {
        str(row.get("observation_id") or ""): row
        for row in feature_rows
        if row.get("observation_id")
    }
    v3_feature_set_id = str((v3_benchmark.get("feature_set") or {}).get("id") or "")
    fixed = v3_feature_set_id == "fixed_gap_7d_biology_v3"
    v2_spec = (
        mushroom_ml_experiments.FIXED_GAP_7D_ALTITUDE_V2
        if fixed
        else mushroom_ml_experiments.LAG_EVENT_ALTITUDE_V2
    )
    samples: list[dict[str, Any]] = []
    missing_observation_ids: list[str] = []
    for v3_sample in v3_benchmark.get("samples", []):
        v3_metadata = dict(v3_sample.get("metadata") or {})
        observation_id = str(v3_metadata.get("observation_id") or "")
        source = rows_by_id.get(observation_id)
        if source is None:
            missing_observation_ids.append(observation_id)
            continue
        area_id = str(
            v3_metadata.get("area_id")
            or micro_area_to_area.get(str(source.get("micro_area_id") or ""))
            or ""
        )
        observation = dict(source)
        observation["area_id"] = area_id
        observation["gis_altitude_m"] = area_representative_altitudes.get(area_id)
        horizon_days = int(v3_metadata.get("horizon_days") or 7)
        if fixed:
            features, quality_metadata = (
                mushroom_ml_experiments.build_fixed_gap_7d_altitude_features(observation)
            )
        else:
            features, quality_metadata = (
                mushroom_ml_experiments.build_lag_event_altitude_features(
                    observation, horizon_days
                )
            )
        base_eligible = (
            source.get("validation_status") == "valid"
            and source.get("calibration_use") == "include"
            and source.get("prediction_target") in {"favorable", "unfavorable"}
            and bool(source.get("micro_area_id"))
        )
        reasons = list(quality_metadata.get("training_ineligibility_reasons") or [])
        if not base_eligible:
            reasons.append("observation_not_eligible_for_calibration")
        metadata = {
            **quality_metadata,
            "observation_id": observation_id,
            "species_id": str(v3_metadata.get("species_id") or source.get("species_id") or ""),
            "area_id": area_id,
            "micro_area_id": str(source.get("micro_area_id") or ""),
            "target_date": str(v3_metadata.get("target_date") or source.get("observed_at") or ""),
            "horizon_days": horizon_days,
            "validation_group_7d": v3_metadata.get("validation_group_7d"),
            "validation_group_14d": v3_metadata.get("validation_group_14d"),
        }
        samples.append(
            {
                "sample_id": f"{observation_id}|{v2_spec.feature_set_id}|h{horizon_days}",
                "prediction_target": source.get("prediction_target"),
                "predictive_features": features,
                "quality": {
                    "training_eligible": base_eligible and not reasons,
                    "training_exclusion_reasons": reasons,
                },
                "metadata": metadata,
            }
        )
    return {
        "schema_version": "2.0-observation-comparison",
        "kind": "mushroom_ml_altitude_v2_observation_benchmark",
        "feature_set": {
            "id": v2_spec.feature_set_id,
            "predictive_feature_cols": list(v2_spec.feature_cols),
        },
        "sample_count": len(samples),
        "training_eligible_sample_count": sum(
            bool((sample.get("quality") or {}).get("training_eligible"))
            for sample in samples
        ),
        "missing_observation_ids": sorted(set(missing_observation_ids)),
        "samples": samples,
    }


def build_observation_altitude_v2_common_idw_benchmark(
    v3_benchmark: dict[str, Any],
) -> dict[str, Any]:
    """Apply the retained V2 feature contract to V3's common IDW weather rows.

    This is an evaluation-only V2 variant. It preserves the V2 feature list but
    removes station choice as a confounder in V2/V3/V4 comparisons. The actual
    production V2 replay remains available through
    :func:`build_observation_altitude_v2_benchmark`.
    """
    v3_feature_set_id = str((v3_benchmark.get("feature_set") or {}).get("id") or "")
    fixed = v3_feature_set_id == "fixed_gap_7d_biology_v3"
    v2_spec = (
        mushroom_ml_experiments.FIXED_GAP_7D_ALTITUDE_V2
        if fixed
        else mushroom_ml_experiments.LAG_EVENT_ALTITUDE_V2
    )
    predictive_from_quality = {
        "significant_rain_found_90d",
        "rain_observed_days_21",
        "rain_missing_days_21",
        "rain_suppressed_days_21",
        "rain_observed_days_90",
        "rain_missing_days_90",
        "rain_suppressed_days_90",
        "dry_spell_is_censored",
        "temp_observed_days_after_significant_rain",
        "humidity_observed_days_after_significant_rain",
    }
    samples: list[dict[str, Any]] = []
    for source in v3_benchmark.get("samples", []):
        source_predictive = dict(source.get("predictive_features") or {})
        source_quality = dict(source.get("quality") or {})
        source_metadata = dict(source.get("metadata") or {})
        features: dict[str, float | None] = {}
        missing: list[str] = []
        for name in v2_spec.feature_cols:
            value = (
                source_quality.get(name)
                if name in predictive_from_quality
                else source_predictive.get(name)
            )
            if isinstance(value, bool):
                value = float(value)
            if value is None:
                features[name] = None
                missing.append(name)
            else:
                try:
                    features[name] = float(value)
                except (TypeError, ValueError):
                    features[name] = None
                    missing.append(name)
        reasons = list(source_quality.get("training_exclusion_reasons") or [])
        if missing:
            reasons.append(
                {
                    "code": "v2_common_idw_features_missing",
                    "message": "Missing V2 fields on common IDW weather: " + ", ".join(missing),
                }
            )
        horizon_days = int(source_metadata.get("horizon_days") or 7)
        observation_id = str(source_metadata.get("observation_id") or "")
        samples.append(
            {
                "sample_id": f"{observation_id}|{v2_spec.feature_set_id}_common_idw|h{horizon_days}",
                "prediction_target": source.get("prediction_target"),
                "predictive_features": features,
                "quality": {
                    "training_eligible": bool(source_quality.get("training_eligible")) and not missing,
                    "training_exclusion_reasons": reasons,
                },
                "metadata": {
                    **source_metadata,
                    "source_temporal_contract_id": v2_spec.feature_set_id,
                    "weather_basis": "common_multisource_area_idw",
                    "weather_idw_contract_id": v3_benchmark.get("weather_idw_contract_id"),
                    "comparison_only": True,
                },
            }
        )
    return {
        "schema_version": "2.1-observation-common-idw-comparison",
        "kind": "mushroom_ml_altitude_v2_common_idw_observation_benchmark",
        "feature_set": {
            "id": f"{v2_spec.feature_set_id}_common_idw",
            "predictive_feature_cols": list(v2_spec.feature_cols),
        },
        "weather_basis": "common_multisource_area_idw",
        "weather_idw_contract_id": v3_benchmark.get("weather_idw_contract_id"),
        "sample_count": len(samples),
        "training_eligible_sample_count": sum(
            bool((sample.get("quality") or {}).get("training_eligible"))
            for sample in samples
        ),
        "samples": samples,
    }


def materialize_altitude_v2_common_idw_inference_sample(
    source_v3_sample: dict[str, Any],
    *,
    fixed: bool,
) -> dict[str, Any]:
    """Apply the exact comparison V2 projection to one target-free V3 row."""
    payload = build_observation_altitude_v2_common_idw_benchmark(
        {
            "feature_set": {
                "id": (
                    "fixed_gap_7d_biology_v3"
                    if fixed
                    else "lag_event_biology_v3"
                )
            },
            "weather_idw_contract_id": source_v3_sample.get("metadata", {}).get(
                "weather_idw_contract_id"
            ),
            "samples": [source_v3_sample],
        }
    )
    sample = dict(payload["samples"][0])
    quality = dict(sample.get("quality") or {})
    reasons = [
        dict(reason)
        for reason in quality.get("training_exclusion_reasons", [])
        if isinstance(reason, dict) and reason.get("code") != "modeling_target_unknown"
    ]
    quality.update(
        {
            "inference_eligible": not reasons,
            "inference_exclusion_reasons": reasons,
            "target_gate_ignored_for_inference": True,
        }
    )
    sample["quality"] = quality
    return sample


def _comparison_key(sample: dict[str, Any]) -> tuple[str, int]:
    metadata = sample.get("metadata") or {}
    return (
        str(metadata.get("observation_id") or ""),
        int(metadata.get("horizon_days") or 7),
    )


def evaluate_matched_version_benchmarks(
    benchmarks_by_version: dict[str, dict[str, Any]],
    *,
    group_days: int,
    species_ids: set[str] | None = None,
    version_registry: object | None = None,
    evaluation_cache: dict[tuple[object, ...], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate any number of versions on their common observation rows."""
    if len(benchmarks_by_version) < 2:
        raise ValueError("At least two ML versions are required for comparison")
    version_ids = [str(version_id).strip() for version_id in benchmarks_by_version]
    if any(not version_id for version_id in version_ids):
        raise ValueError("ML comparison version IDs must be non-empty")
    eligible_by_version: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
    for version_id, benchmark in benchmarks_by_version.items():
        eligible = {
            _comparison_key(row): row for row in _eligible_samples(benchmark)
        }
        if species_ids is not None:
            eligible = {
                key: row
                for key, row in eligible.items()
                if str((row.get("metadata") or {}).get("species_id") or "")
                in species_ids
            }
        eligible_by_version[version_id] = eligible
    common_keys = sorted(
        set.intersection(*(set(rows) for rows in eligible_by_version.values()))
    )
    if not common_keys:
        raise ValueError("ML versions have no jointly eligible observation rows")
    mismatched_targets = [
        key
        for key in common_keys
        if len(
            {
                eligible_by_version[version_id][key].get("prediction_target")
                for version_id in version_ids
            }
        )
        != 1
    ]
    if mismatched_targets:
        raise ValueError("ML version targets differ for matched observations")
    mismatched_metadata = [
        key
        for key in common_keys
        if len(
            {
                tuple(
                    (eligible_by_version[version_id][key].get("metadata") or {}).get(
                        field
                    )
                    for field in ("species_id", "area_id", "target_date", "horizon_days")
                )
                for version_id in version_ids
            }
        )
        != 1
    ]
    if mismatched_metadata:
        raise ValueError("ML version metadata differ for matched observations")

    def evaluate_keys(
        keys: list[tuple[str, int]],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        reports: dict[str, dict[str, Any]] = {}
        split: dict[str, Any] | None = None
        split_membership: dict[str, list[tuple[str, int]]] | None = None
        keys_sha256 = hashlib.sha256(
            json.dumps(keys, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        for version_id in version_ids:
            matched = deepcopy(benchmarks_by_version[version_id])
            matched["samples"] = [eligible_by_version[version_id][key] for key in keys]
            matched_eligible = _eligible_samples(matched)
            matched_train, matched_test = chronological_group_split(
                matched_eligible, group_days=group_days
            )
            membership = {
                "train": sorted(_comparison_key(row) for row in matched_train),
                "test": sorted(_comparison_key(row) for row in matched_test),
            }
            if split_membership is None:
                split_membership = membership
            elif membership != split_membership:
                raise AssertionError(
                    "matched ML version rows did not produce identical partitions"
                )
            feature_set_id = str(
                (matched.get("feature_set") or {}).get("id") or ""
            )
            cache_key = (
                version_id,
                feature_set_id,
                group_days,
                keys_sha256,
                tuple(sorted(species_ids)) if species_ids is not None else None,
            )
            report = (
                deepcopy(evaluation_cache[cache_key])
                if evaluation_cache is not None and cache_key in evaluation_cache
                else evaluate_benchmark(
                    matched, group_days=group_days, species_ids=species_ids
                )
            )
            if evaluation_cache is not None and cache_key not in evaluation_cache:
                evaluation_cache[cache_key] = deepcopy(report)
            if split is None:
                split = report["split"]
            elif split != report["split"]:
                raise AssertionError(
                    "matched ML version rows did not produce the same split"
                )
            reports[version_id] = report
        split_report = dict(split or {})
        split_report["membership_sha256"] = hashlib.sha256(
            json.dumps(
                split_membership or {},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return reports, split_report

    reports, split = evaluate_keys(common_keys)
    all_keys = set().union(*(set(rows) for rows in eligible_by_version.values()))
    coverage_by_version = {
        version_id: {
            "eligible": len(eligible_by_version[version_id]),
            "not_jointly_eligible": len(
                set(eligible_by_version[version_id]) - set(common_keys)
            ),
            "missing_from_version": len(all_keys - set(eligible_by_version[version_id])),
        }
        for version_id in version_ids
    }
    horizons = sorted({key[1] for key in common_keys})
    by_horizon: dict[str, Any] = {}
    if len(horizons) > 1:
        for horizon_days in horizons:
            horizon_keys = [key for key in common_keys if key[1] == horizon_days]
            by_horizon[str(horizon_days)] = {
                "jointly_eligible": len(horizon_keys),
                "evaluation_method": (
                    "filter_predictions_from_full_temporal_contract_model_no_refit"
                ),
                "split": {
                    "horizon_days": horizon_days,
                    "parent_membership_sha256": split["membership_sha256"],
                },
                "versions": {
                    version_id: _evaluation_report_for_horizon(
                        reports[version_id],
                        horizon_days=horizon_days,
                        parent_membership_sha256=split["membership_sha256"],
                    )
                    for version_id in version_ids
                },
            }
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "kind": "mushroom_ml_matched_version_comparison",
        "version_ids": version_ids,
        "comparison_axes": [
            "version",
            "species",
            "temporal_contract",
            "estimator",
        ],
        "selection_policy": (
            "select per species, temporal contract and estimator; pooled scores "
            "are diagnostic only"
        ),
        "coverage": {
            "jointly_eligible": len(common_keys),
            "by_version": coverage_by_version,
            "target_mismatch_count": 0,
        },
        "split": split,
        "versions": reports,
        "by_horizon": by_horizon,
        "sources": {
            version_id: deepcopy(
                benchmarks_by_version[version_id].get("source") or {}
            )
            for version_id in version_ids
        },
        "model_artifact_written": False,
    }
    if version_registry is not None:
        report["version_registry"] = (
            mushroom_ml_version_registry.benchmark_version_metadata(
                version_registry, version_ids
            )
        )
    return report


def evaluate_matched_benchmarks(
    altitude_v2_benchmark: dict[str, Any],
    biology_v3_benchmark: dict[str, Any],
    *,
    group_days: int,
    species_ids: set[str] | None = None,
    version_registry: object | None = None,
) -> dict[str, Any]:
    """Evaluate V2 and V3 on the exact same eligible observation/horizon rows."""
    generic = evaluate_matched_version_benchmarks(
        {
            "altitude_v2": altitude_v2_benchmark,
            "biology_v3": biology_v3_benchmark,
        },
        group_days=group_days,
        species_ids=species_ids,
        version_registry=version_registry,
    )
    v2_eligible = generic["coverage"]["by_version"]["altitude_v2"]["eligible"]
    v3_eligible = generic["coverage"]["by_version"]["biology_v3"]["eligible"]
    jointly_eligible = generic["coverage"]["jointly_eligible"]
    by_horizon = {
        horizon: {
            "jointly_eligible": row["jointly_eligible"],
            "split": row["split"],
            "altitude_v2": row["versions"]["altitude_v2"],
            "biology_v3": row["versions"]["biology_v3"],
        }
        for horizon, row in generic["by_horizon"].items()
    }
    return {
        "schema_version": "1.0",
        "kind": "biology_v3_matched_altitude_v2_comparison",
        "coverage": {
            "v2_eligible": v2_eligible,
            "v3_eligible": v3_eligible,
            "jointly_eligible": jointly_eligible,
            "v2_only": generic["coverage"]["by_version"]["altitude_v2"]["not_jointly_eligible"],
            "v3_only": generic["coverage"]["by_version"]["biology_v3"]["not_jointly_eligible"],
            "target_mismatch_count": 0,
        },
        "split": generic["split"],
        "altitude_v2": generic["versions"]["altitude_v2"],
        "biology_v3": generic["versions"]["biology_v3"],
        "by_horizon": by_horizon,
        "sources": {
            "altitude_v2": deepcopy(altitude_v2_benchmark.get("source") or {}),
            "biology_v3": deepcopy(biology_v3_benchmark.get("source") or {}),
        },
        "version_comparison": generic,
        "model_artifact_written": False,
    }
