"""Controlled, non-operational feature ablations for mushroom ML audits."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any
import json

import numpy as np

from rainmapper_core import mushroom_ml_experiment_trainer
from rainmapper_core import mushroom_ml_holdout


DEFAULT_VERSION_ID = "biology_v3"
DEFAULT_PROFILE_ID = "common_idw_plus_physical_state"
DEFAULT_TEMPORAL_CONTRACT_ID = "lag_event_biology_v3"
DEFAULT_ESTIMATOR_ID = "logistic_regression_reduced_v1"


def expected_calibration_error(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    bin_count: int = 5,
) -> float:
    """Return equal-width expected calibration error."""
    if bin_count < 1:
        raise ValueError("bin_count must be positive")
    if len(y_true) != len(probabilities):
        raise ValueError("labels and probabilities must have equal length")
    if len(y_true) == 0:
        return 0.0
    edges = np.linspace(0.0, 1.0, bin_count + 1)
    total = 0.0
    for index in range(bin_count):
        lower = edges[index]
        upper = edges[index + 1]
        selected = (
            (probabilities >= lower) & (probabilities <= upper)
            if index == bin_count - 1
            else (probabilities >= lower) & (probabilities < upper)
        )
        if not np.any(selected):
            continue
        total += float(np.mean(selected)) * abs(
            float(np.mean(probabilities[selected])) - float(np.mean(y_true[selected]))
        )
    return round(total, 6)


def feature_families(columns: list[str]) -> dict[str, list[str]]:
    """Classify the actual model columns; never infer absent features."""
    available = set(columns)

    def matching(*prefixes: str) -> list[str]:
        return [column for column in columns if column.startswith(prefixes)]

    families = {
        "horizon": [column for column in columns if column == "horizon_days"],
        "direct_rain_amounts": matching("rain_cutoff_"),
        "dry_spell": [
            column for column in columns if column == "dry_spell_observed_at_cutoff"
        ],
        "temperature": matching("temp_"),
        "humidity": matching("humidity_"),
        "climatic_balance": matching("climatic_water_balance_"),
        "soil_water": matching("soil_water_"),
        "altitude_direct": [
            column
            for column in columns
            if column in {"gis_altitude_m", "altitude_m"}
        ],
    }
    families["direct_rain"] = (
        families["direct_rain_amounts"] + families["dry_spell"]
    )
    families["hydric_state"] = (
        families["climatic_balance"] + families["soil_water"]
    )
    families["all_hydric"] = families["direct_rain"] + families["hydric_state"]
    for column in columns:
        if column not in available:
            raise AssertionError(column)
    return families


def ablation_specs(columns: list[str]) -> list[dict[str, Any]]:
    """Build named ablations over exactly the columns consumed by the model."""
    families = feature_families(columns)
    specs: OrderedDict[str, tuple[list[str], str]] = OrderedDict(
        (
            ("baseline_full", ([], "All consumed features.")),
            (
                "no_direct_rain",
                (
                    families["direct_rain"],
                    "Removes recent rain amounts and the observed dry-spell counter.",
                ),
            ),
            (
                "no_rain_amounts",
                (families["direct_rain_amounts"], "Removes only recent rain totals."),
            ),
            (
                "no_dry_spell",
                (families["dry_spell"], "Removes only the dry-spell counter."),
            ),
            (
                "no_climatic_balance",
                (families["climatic_balance"], "Removes the climatic water balance."),
            ),
            (
                "no_soil_water",
                (families["soil_water"], "Removes the learned soil-water state."),
            ),
            (
                "no_hydric_state",
                (
                    families["hydric_state"],
                    "Keeps direct rain but removes balance and soil-water state.",
                ),
            ),
            (
                "no_all_hydric",
                (families["all_hydric"], "Removes rain, balance and soil-water state."),
            ),
            (
                "no_temperature",
                (families["temperature"], "Removes altitude-corrected temperature."),
            ),
            ("no_humidity", (families["humidity"], "Removes relative humidity.")),
            (
                "no_altitude_direct",
                (
                    families["altitude_direct"],
                    "Null control: V3 physical has no direct altitude column.",
                ),
            ),
            ("no_horizon", (families["horizon"], "Removes forecast horizon.")),
        )
    )
    for suffix in ("0_3d", "4_7d", "8_14d", "15_21d"):
        column = f"rain_cutoff_{suffix}_mm"
        if column in columns:
            specs[f"no_rain_{suffix}"] = (
                [column],
                f"Removes only direct rain for lag {suffix.replace('_', '-')}.",
            )
    for suffix in ("0_7d", "8_14d", "15_21d", "22_30d"):
        column = f"climatic_water_balance_cutoff_{suffix}_mm"
        if column in columns:
            specs[f"no_balance_{suffix}"] = (
                [column],
                f"Removes only climatic balance for lag {suffix.replace('_', '-')}.",
            )
    soil_current = [
        column
        for column in (
            "soil_water_area_mean_at_cutoff",
            "soil_water_area_min_at_cutoff",
            "soil_water_deficit_at_cutoff",
        )
        if column in columns
    ]
    soil_dynamics = [
        column
        for column in (
            "soil_water_change_7d",
            "soil_water_change_14d",
            "soil_water_recharge_7d",
            "soil_water_drydown_7d",
        )
        if column in columns
    ]
    specs["no_soil_current_state"] = (
        soil_current,
        "Removes current storage/minimum/deficit, retaining soil dynamics.",
    )
    specs["no_soil_dynamics"] = (
        soil_dynamics,
        "Removes soil changes/recharge/drydown, retaining current state.",
    )
    return [
        {"id": key, "removed_features": value[0], "description": value[1]}
        for key, value in specs.items()
    ]


def load_holdout_rows(
    path: Path,
    *,
    species_id: str,
    group_days: int,
    version_id: str = DEFAULT_VERSION_ID,
    profile_id: str = DEFAULT_PROFILE_ID,
    temporal_contract_id: str = DEFAULT_TEMPORAL_CONTRACT_ID,
) -> list[dict[str, Any]]:
    """Load only the frozen rows defining one exact external hold-out."""
    split_id = f"fruiting_groups_{group_days}d"
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if (
                row.get("species_id") == species_id
                and row.get("version_id") == version_id
                and row.get("profile_id") == profile_id
                and row.get("temporal_contract_id") == temporal_contract_id
                and row.get("split_id") == split_id
            ):
                rows.append(row)
    if not rows:
        raise ValueError(f"No matching hold-out rows for {split_id}")
    return rows


def _scored_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    result = mushroom_ml_holdout.metrics(y_true, probabilities)
    result["expected_calibration_error_5bin"] = expected_calibration_error(
        y_true, probabilities, bin_count=5
    )
    result["mean_probability"] = round(float(np.mean(probabilities)), 6)
    return result


def _linear_runtime_explanation(
    model: Any,
    runtime_vector: np.ndarray,
    columns: list[str],
) -> dict[str, Any]:
    """Explain a scaled logistic prediction in log-odds, not causal effects."""
    imputed = model.named_steps["imputer"].transform(runtime_vector)
    standardized = model.named_steps["scaler"].transform(imputed)[0]
    classifier = model.named_steps["classifier"]
    contributions = standardized * classifier.coef_[0]
    rows = [
        {
            "feature": column,
            "value": round(float(runtime_vector[0, index]), 6),
            "standardized_value": round(float(standardized[index]), 6),
            "log_odds_contribution": round(float(contributions[index]), 6),
        }
        for index, column in enumerate(columns)
    ]
    contribution_by_feature = {
        row["feature"]: row["log_odds_contribution"] for row in rows
    }
    families = feature_families(columns)
    atomic_families = (
        "horizon",
        "direct_rain_amounts",
        "dry_spell",
        "temperature",
        "humidity",
        "climatic_balance",
        "soil_water",
        "altitude_direct",
    )
    return {
        "interpretation": (
            "Conditional logistic contributions relative to the training mean; "
            "they are not causal effects."
        ),
        "intercept": round(float(classifier.intercept_[0]), 6),
        "prediction_log_odds": round(float(model.decision_function(runtime_vector)[0]), 6),
        "family_log_odds_contributions": {
            family: round(
                sum(contribution_by_feature[column] for column in families[family]), 6
            )
            for family in atomic_families
        },
        "features": sorted(
            rows, key=lambda row: abs(row["log_odds_contribution"]), reverse=True
        ),
    }


def audit_split(
    benchmark: dict[str, Any],
    archived_rows: list[dict[str, Any]],
    *,
    species_id: str,
    estimator_id: str = DEFAULT_ESTIMATOR_ID,
    runtime_features: dict[str, Any] | None = None,
    runtime_reference_probability: float | None = None,
) -> dict[str, Any]:
    """Retrain controlled copies on one frozen split and compare ablations."""
    samples = [
        sample
        for sample in mushroom_ml_holdout.eligible_samples(benchmark)
        if str((sample.get("metadata") or {}).get("species_id")) == species_id
    ]
    all_keys = {mushroom_ml_holdout.comparison_key(sample) for sample in samples}
    test_keys = {
        (str(row["observation_id"]), int(row["horizon_days"]))
        for row in archived_rows
    }
    unknown = test_keys - all_keys
    if unknown:
        raise ValueError(f"Prepared benchmark is missing {len(unknown)} hold-out keys")
    train_keys = all_keys - test_keys
    train = [
        sample
        for sample in samples
        if mushroom_ml_holdout.comparison_key(sample) in train_keys
    ]
    test = [
        sample
        for sample in samples
        if mushroom_ml_holdout.comparison_key(sample) in test_keys
    ]
    columns = list((benchmark.get("feature_set") or {}).get("predictive_feature_cols") or [])
    _, all_labels = mushroom_ml_holdout.matrix(samples, columns)
    archived = {
        (str(row["observation_id"]), int(row["horizon_days"])): row
        for row in archived_rows
    }
    variants: list[dict[str, Any]] = []
    baseline_probabilities: np.ndarray | None = None
    for spec in ablation_specs(columns):
        removed = set(spec["removed_features"])
        kept = [column for column in columns if column not in removed]
        X_train, y_train = mushroom_ml_holdout.matrix(train, kept)
        X_test, y_test = mushroom_ml_holdout.matrix(test, kept)
        model = mushroom_ml_experiment_trainer._pipeline(estimator_id)
        model.fit(X_train, y_train)
        probabilities = model.predict_proba(X_test)[:, 1]
        variant: dict[str, Any] = {
            **spec,
            "kept_feature_count": len(kept),
            "metrics_all_horizons": _scored_metrics(y_test, probabilities),
            "metrics_by_horizon": {},
        }
        for horizon in range(1, 8):
            selected = np.asarray(
                [
                    int((sample.get("metadata") or {}).get("horizon_days") or 7)
                    == horizon
                    for sample in test
                ],
                dtype=bool,
            )
            variant["metrics_by_horizon"][str(horizon)] = _scored_metrics(
                y_test[selected], probabilities[selected]
            )
        if runtime_features is not None:
            runtime_vector = np.asarray(
                [[float(runtime_features[column]) for column in kept]], dtype=float
            )
            X_all, y_all = mushroom_ml_holdout.matrix(samples, kept)
            full_model = mushroom_ml_experiment_trainer._pipeline(estimator_id)
            full_model.fit(X_all, y_all)
            variant["runtime_probability"] = round(
                float(full_model.predict_proba(runtime_vector)[0, 1]), 10
            )
            variant["runtime_fit_sample_count"] = len(samples)
            if spec["id"] == "baseline_full":
                variant["runtime_linear_explanation"] = _linear_runtime_explanation(
                    full_model, runtime_vector, kept
                )
        if baseline_probabilities is None:
            baseline_probabilities = probabilities
            archived_differences = []
            for index, sample in enumerate(test):
                key = mushroom_ml_holdout.comparison_key(sample)
                archived_probability = float(
                    archived[key]["estimator_probabilities"][estimator_id]
                )
                archived_differences.append(abs(probabilities[index] - archived_probability))
            variant["archived_reproduction"] = {
                "row_count": len(archived_differences),
                "max_absolute_probability_difference": round(
                    max(archived_differences), 12
                ),
            }
            if runtime_reference_probability is not None and runtime_features is not None:
                variant["runtime_reproduction_absolute_difference"] = round(
                    abs(variant["runtime_probability"] - runtime_reference_probability), 12
                )
        else:
            changed = (probabilities >= 0.5) != (baseline_probabilities >= 0.5)
            variant["change_vs_baseline"] = {
                "mean_absolute_probability_change": round(
                    float(np.mean(np.abs(probabilities - baseline_probabilities))), 6
                ),
                "classification_flips": int(np.sum(changed)),
                "brier_score_change": round(
                    variant["metrics_all_horizons"]["brier_score"]
                    - variants[0]["metrics_all_horizons"]["brier_score"],
                    6,
                ),
                "roc_auc_change": round(
                    variant["metrics_all_horizons"]["roc_auc"]
                    - variants[0]["metrics_all_horizons"]["roc_auc"],
                    6,
                ),
            }
            if runtime_features is not None:
                variant["change_vs_baseline"]["runtime_probability_change"] = round(
                    variant["runtime_probability"]
                    - variants[0]["runtime_probability"],
                    10,
                )
        variants.append(variant)
    group_days = int(archived_rows[0]["group_days"])
    return {
        "split_id": f"fruiting_groups_{group_days}d",
        "group_days": group_days,
        "species_id": species_id,
        "estimator_id": estimator_id,
        "n_train": len(train),
        "n_test": len(test),
        "full_fit_class_counts": {
            "favorable": int(np.sum(all_labels)),
            "unfavorable": int(len(all_labels) - np.sum(all_labels)),
        },
        "feature_columns": columns,
        "feature_families": feature_families(columns),
        "variants": variants,
    }
