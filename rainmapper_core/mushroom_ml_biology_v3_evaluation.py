"""Non-operational, observation-preserving evaluation for Biology V3.

The evaluator never serializes fitted models.  Its only output is an auditable
metrics report built from chronological hold-outs whose fruiting groups never
cross the train/test boundary.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from rainmapper_core.mushroom_ml_biology_v3 import observation_validation_groups


FEATURE_FAMILIES = {
    "active_full": lambda name: True,
    "without_rain": lambda name: not (
        name.startswith("rain_") or name.startswith("days_since_rain")
    ),
    "without_temperature_humidity": lambda name: not (
        name.startswith("temp_") or name.startswith("humidity_")
    ),
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
    return {
        "n": int(len(y_true)),
        "favorable_ratio": round(float(np.mean(y_true)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, predicted)), 4),
        "brier_score": round(float(brier_score_loss(y_true, probabilities)), 4),
        "log_loss": round(float(log_loss(y_true, probabilities, labels=[0, 1])), 4),
        "expected_calibration_error": round(calibration_error, 4),
        "calibration_bins": bins,
    }


def evaluate_benchmark(
    benchmark: dict[str, Any],
    *,
    group_days: int,
) -> dict[str, Any]:
    """Evaluate retained feature families without emitting a reusable model."""
    import numpy as np  # noqa: PLC0415
    from sklearn.impute import SimpleImputer  # noqa: PLC0415
    from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    from sklearn.pipeline import Pipeline  # noqa: PLC0415
    from sklearn.preprocessing import StandardScaler  # noqa: PLC0415

    samples = _eligible_samples(benchmark)
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
    for family_id, selector in FEATURE_FAMILIES.items():
        feature_cols = [name for name in active_cols if selector(name)]
        species_reports: dict[str, Any] = {}
        held_y: list[int] = []
        held_probabilities: list[float] = []
        species_ids = sorted(
            {str((row.get("metadata") or {}).get("species_id") or "") for row in samples}
        )
        for species_id in species_ids:
            species_train = [
                row for row in train if (row.get("metadata") or {}).get("species_id") == species_id
            ]
            species_test = [
                row for row in test if (row.get("metadata") or {}).get("species_id") == species_id
            ]
            if not species_train or not species_test:
                species_reports[species_id] = {"available": False, "reason": "empty partition"}
                continue
            X_train, y_train = _matrix(species_train, feature_cols)
            X_test, y_test = _matrix(species_test, feature_cols)
            if len(np.unique(y_train)) < 2:
                species_reports[species_id] = {
                    "available": False,
                    "reason": "chronological training partition has a single class",
                    "n_train": len(species_train),
                    "n_test": len(species_test),
                }
                continue
            model = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scale", StandardScaler()),
                    ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced")),
                ]
            )
            model.fit(X_train, y_train)
            probabilities = model.predict_proba(X_test)[:, 1]
            species_reports[species_id] = {
                "available": True,
                "n_train": len(species_train),
                "n_test": len(species_test),
                "metrics": _metrics(y_test, probabilities),
            }
            held_y.extend(int(value) for value in y_test)
            held_probabilities.extend(float(value) for value in probabilities)
        reports[family_id] = {
            "feature_cols": feature_cols,
            "species": species_reports,
            "pooled_metrics": (
                _metrics(np.asarray(held_y), np.asarray(held_probabilities))
                if held_y
                else {"n": 0, "note": "no species had an evaluable chronological split"}
            ),
        }
    return {
        "schema_version": "1.0",
        "kind": "biology_v3_non_operational_evaluation",
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
