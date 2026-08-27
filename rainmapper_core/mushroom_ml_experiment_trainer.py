"""Train comparable observed-weather models from frozen ML benchmarks.

The filenames retain the historical ``experiment`` prefix for compatibility.
The Predictor keeps both feature sets operational and uses their embedded
out-of-sample evaluation to decide whether an estimator may contribute.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_ml_input_identity
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_paths
from rainmapper_core.mushroom_ml_experiments import (
    FEATURE_SETS,
    FIXED_GAP_7D_ALTITUDE_V2,
    LAG_EVENT_ALTITUDE_V2,
    build_benchmark,
)
from rainmapper_core.mushroom_ml_trainer import load_features, load_micro_area_to_area
from rainmapper_core.mushroom_ml_trainer import load_area_representative_altitudes


EXPERIMENT_MODEL_PREFIX = "mushroom_ml_experiment"
DEFAULT_FEATURE_SET_IDS = (
    FIXED_GAP_7D_ALTITUDE_V2.feature_set_id,
    LAG_EVENT_ALTITUDE_V2.feature_set_id,
)
EXPERIMENT_ESTIMATOR_IDS = (
    "logistic_regression_reduced_v1",
    "random_forest_restricted_v1",
    "extra_trees_restricted_v1",
    "hist_gradient_boosting_restricted_v1",
    "knn_distance_v1",
    "rbf_svm_calibrated_v1",
)


def model_filename(feature_set_id: str, species_id: str) -> str:
    return f"{EXPERIMENT_MODEL_PREFIX}_{feature_set_id}_{species_id}.joblib"


def _matrix(samples: list[dict[str, Any]], feature_cols: list[str]) -> tuple[Any, Any]:
    import numpy as np  # noqa: PLC0415

    X = np.array(
        [
            [
                float(sample.get("features", {}).get(column))
                if sample.get("features", {}).get(column) is not None
                else float("nan")
                for column in feature_cols
            ]
            for sample in samples
        ],
        dtype=float,
    )
    y = np.array(
        [1 if sample.get("prediction_target") == "favorable" else 0 for sample in samples],
        dtype=int,
    )
    return X, y


def _feature_support(
    samples: list[dict[str, Any]], feature_cols: list[str]
) -> dict[str, dict[str, Any]]:
    """Describe the finite training support used for runtime OOD checks."""
    import numpy as np  # noqa: PLC0415

    X, _y = _matrix(samples, feature_cols)
    support: dict[str, dict[str, Any]] = {}
    for index, column in enumerate(feature_cols):
        values = X[:, index]
        finite = values[np.isfinite(values)]
        if len(finite) == 0:
            support[column] = {"observed_count": 0}
            continue
        support[column] = {
            "observed_count": int(len(finite)),
            "min": round(float(np.min(finite)), 6),
            "max": round(float(np.max(finite)), 6),
            "mean": round(float(np.mean(finite)), 6),
            "std": round(float(np.std(finite)), 6),
        }
    return support


def _pipeline(estimator_id: str) -> Any:
    from sklearn.calibration import CalibratedClassifierCV  # noqa: PLC0415
    from sklearn.ensemble import (  # noqa: PLC0415
        ExtraTreesClassifier,
        HistGradientBoostingClassifier,
        RandomForestClassifier,
    )
    from sklearn.impute import SimpleImputer  # noqa: PLC0415
    from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    from sklearn.neighbors import KNeighborsClassifier  # noqa: PLC0415
    from sklearn.pipeline import Pipeline  # noqa: PLC0415
    from sklearn.preprocessing import StandardScaler  # noqa: PLC0415
    from sklearn.svm import SVC  # noqa: PLC0415

    if estimator_id == "logistic_regression_reduced_v1":
        estimator = LogisticRegression(
            C=1.0,
            max_iter=2000,
            random_state=42,
            class_weight="balanced",
        )
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("classifier", estimator),
            ]
        )
    if estimator_id == "random_forest_restricted_v1":
        estimator = RandomForestClassifier(
            n_estimators=200,
            max_depth=3,
            min_samples_leaf=3,
            random_state=42,
            class_weight="balanced",
            # These operational partitions contain only tens or hundreds of
            # rows. Recreating a process-wide joblib pool for every species,
            # profile and hold-out split costs more than fitting the trees.
            n_jobs=1,
        )
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("classifier", estimator),
            ]
        )
    if estimator_id == "extra_trees_restricted_v1":
        estimator = ExtraTreesClassifier(
            n_estimators=300,
            max_depth=4,
            min_samples_leaf=2,
            random_state=42,
            class_weight="balanced",
            n_jobs=1,
        )
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("classifier", estimator),
            ]
        )
    if estimator_id == "hist_gradient_boosting_restricted_v1":
        estimator = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=150,
            max_leaf_nodes=7,
            min_samples_leaf=5,
            l2_regularization=1.0,
            random_state=42,
            class_weight="balanced",
        )
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("classifier", estimator),
            ]
        )
    if estimator_id == "knn_distance_v1":
        estimator = KNeighborsClassifier(
            n_neighbors=7,
            weights="distance",
            metric="minkowski",
            p=2,
        )
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("classifier", estimator),
            ]
        )
    if estimator_id == "rbf_svm_calibrated_v1":
        estimator = CalibratedClassifierCV(
            SVC(
                C=1.0,
                kernel="rbf",
                gamma="scale",
                class_weight="balanced",
            ),
            method="sigmoid",
            cv=2,
            ensemble=False,
        )
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("classifier", estimator),
            ]
        )
    raise ValueError(f"Unknown estimator_id: {estimator_id}")


def _estimator_unavailable_reason(estimator_id: str, y_train: Any) -> str | None:
    """Return a stable reason when an estimator cannot be evaluated honestly."""
    if estimator_id != "rbf_svm_calibrated_v1":
        return None
    import numpy as np  # noqa: PLC0415

    class_counts = np.bincount(y_train, minlength=2)
    if int(np.min(class_counts)) < 2:
        return "calibration requires at least two training examples of each class"
    return None


def _metrics(y_true: Any, probabilities: Any) -> dict[str, Any]:
    import numpy as np  # noqa: PLC0415
    from sklearn.metrics import (  # noqa: PLC0415
        average_precision_score,
        balanced_accuracy_score,
        brier_score_loss,
        confusion_matrix,
        log_loss,
        roc_auc_score,
    )

    if len(y_true) == 0:
        return {"n": 0, "note": "empty test partition"}
    predicted = (probabilities >= 0.5).astype(int)
    result: dict[str, Any] = {
        "n": int(len(y_true)),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, predicted)), 4),
        "brier_score": round(float(brier_score_loss(y_true, probabilities)), 4),
        "log_loss": round(float(log_loss(y_true, probabilities, labels=[0, 1])), 4),
        "confusion_matrix": confusion_matrix(y_true, predicted, labels=[0, 1]).tolist(),
        "favorable_ratio": round(float(np.mean(y_true)), 4),
    }
    if len(np.unique(y_true)) >= 2:
        result["roc_auc"] = round(float(roc_auc_score(y_true, probabilities)), 4)
        result["pr_auc"] = round(float(average_precision_score(y_true, probabilities)), 4)
    else:
        result["roc_auc"] = None
        result["pr_auc"] = None
        result["note"] = "test partition has a single class"
    return result


def _evaluate_by_horizon(
    samples: list[dict[str, Any]],
    y: Any,
    probabilities: Any,
) -> dict[str, Any]:
    import numpy as np  # noqa: PLC0415

    horizons = sorted(
        {int(sample.get("metadata", {}).get("horizon_days", 0)) for sample in samples}
    )
    result: dict[str, Any] = {}
    for horizon in horizons:
        indices = [
            index
            for index, sample in enumerate(samples)
            if int(sample.get("metadata", {}).get("horizon_days", 0)) == horizon
        ]
        result[str(horizon)] = _metrics(y[indices], np.asarray(probabilities)[indices])
    return result


def train_benchmark(
    benchmark: dict[str, Any],
    models_dir: Path,
    *,
    min_episodes: int = 20,
    features_sha256: str | None = None,
    known_sites_sha256: str | None = None,
    known_sites_identity: dict[str, Any] | None = None,
    version_id: str | None = None,
) -> dict[str, Any]:
    """Fit identical estimator families for every eligible species."""
    import joblib  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    feature_set = dict(benchmark["feature_set"])
    feature_set_id = str(feature_set["id"])
    feature_cols = [str(value) for value in feature_set["feature_cols"]]
    audit_samples = [dict(value) for value in benchmark.get("samples", [])]
    samples = [
        sample
        for sample in audit_samples
        if bool(sample.get("metadata", {}).get("training_eligible", True))
    ]
    species_ids = sorted({str(sample.get("species_id")) for sample in audit_samples})
    species_results: list[dict[str, Any]] = []
    models_dir.mkdir(parents=True, exist_ok=True)

    for species_id in species_ids:
        species_samples = [sample for sample in samples if sample.get("species_id") == species_id]
        episode_count = len({sample.get("episode_id") for sample in species_samples})
        train_samples = [sample for sample in species_samples if sample.get("partition") == "train"]
        test_samples = [sample for sample in species_samples if sample.get("partition") == "test"]
        chronological_train_samples = [
            sample
            for sample in species_samples
            if sample.get("chronological_partition") == "train"
        ]
        chronological_test_samples = [
            sample
            for sample in species_samples
            if sample.get("chronological_partition") == "test"
        ]
        if episode_count < min_episodes:
            species_results.append(
                {
                    "species_id": species_id,
                    "skipped": True,
                    "reason": f"only {episode_count} episodes (min={min_episodes})",
                }
            )
            continue
        X_train, y_train = _matrix(train_samples, feature_cols)
        X_test, y_test = _matrix(test_samples, feature_cols)
        X_all, y_all = _matrix(species_samples, feature_cols)
        _X_chronological_train, y_chronological_train = _matrix(
            chronological_train_samples, feature_cols
        )
        _X_chronological_test, y_chronological_test = _matrix(
            chronological_test_samples, feature_cols
        )
        if len(np.unique(y_all)) < 2:
            species_results.append(
                {
                    "species_id": species_id,
                    "skipped": True,
                    "reason": "full dataset has a single class",
                }
            )
            continue

        train_has_two_classes = len(np.unique(y_train)) >= 2
        test_has_two_classes = len(np.unique(y_test)) >= 2
        chronological_train_has_two_classes = (
            len(np.unique(y_chronological_train)) >= 2
        )
        chronological_test_has_two_classes = (
            len(np.unique(y_chronological_test)) >= 2
        )
        temporal_validation_available = (
            chronological_train_has_two_classes
            and chronological_test_has_two_classes
        )
        if not chronological_train_has_two_classes:
            temporal_validation_reason = "chronological training partition has a single class"
        elif not chronological_test_has_two_classes:
            temporal_validation_reason = "chronological test partition has a single class"
        else:
            temporal_validation_reason = None
        temporal_validation = {
            "available": temporal_validation_available,
            "reason": temporal_validation_reason,
            "train_favorable": int(np.sum(y_chronological_train)),
            "train_unfavorable": int(
                len(y_chronological_train) - np.sum(y_chronological_train)
            ),
            "test_favorable": int(np.sum(y_chronological_test)),
            "test_unfavorable": int(
                len(y_chronological_test) - np.sum(y_chronological_test)
            ),
        }

        evaluation_available = train_has_two_classes and test_has_two_classes
        evaluation_reason = (
            None
            if evaluation_available
            else "stratified grouped partition could not preserve both classes"
        )

        prevalence = float(np.mean(y_train)) if len(y_train) else float(np.mean(y_all))
        baseline_probs = np.full(len(y_test), prevalence, dtype=float)
        estimator_reports: dict[str, Any] = {
            "train_prevalence_v1": {
                "test": (
                    _metrics(y_test, baseline_probs)
                    if evaluation_available
                    else {
                        "n": int(len(y_test)),
                        "note": evaluation_reason,
                    }
                ),
                "probability": round(prevalence, 4),
            }
        }
        held_out_predictions: dict[str, dict[str, Any]] = {
            str(sample.get("sample_id")): {
                "sample_id": sample.get("sample_id"),
                "episode_id": sample.get("episode_id"),
                "area_id": sample.get("area_id"),
                "target_date": sample.get("metadata", {}).get("target_date"),
                "horizon_days": sample.get("metadata", {}).get("horizon_days"),
                "prediction_target": sample.get("prediction_target"),
                "estimator_probabilities": {},
            }
            for sample in test_samples
        }
        production_models: dict[str, Any] = {}
        estimator_availability: dict[str, dict[str, Any]] = {}
        for estimator_id in EXPERIMENT_ESTIMATOR_IDS:
            unavailable_reason = _estimator_unavailable_reason(estimator_id, y_train)
            estimator_available = evaluation_available and unavailable_reason is None
            estimator_availability[estimator_id] = {
                "available": estimator_available,
                "reason": unavailable_reason or evaluation_reason,
            }
            if estimator_available:
                evaluation_model = _pipeline(estimator_id)
                evaluation_model.fit(X_train, y_train)
                test_probabilities = evaluation_model.predict_proba(X_test)[:, 1]
                estimator_reports[estimator_id] = {
                    "test": _metrics(y_test, test_probabilities),
                    "test_by_horizon": _evaluate_by_horizon(
                        test_samples, y_test, test_probabilities
                    ),
                }
                for sample, probability in zip(
                    test_samples, test_probabilities, strict=True
                ):
                    held_out_predictions[str(sample.get("sample_id"))][
                        "estimator_probabilities"
                    ][estimator_id] = round(float(probability), 6)
            else:
                estimator_reports[estimator_id] = {
                    "test": {
                        "n": int(len(y_test)),
                        "note": unavailable_reason or evaluation_reason,
                    },
                    "test_by_horizon": {},
                }
            if unavailable_reason is not None:
                continue
            production_model = _pipeline(estimator_id)
            production_model.fit(X_all, y_all)
            production_models[estimator_id] = production_model

        episode_partitions: dict[str, dict[str, Any]] = {}
        for sample in species_samples:
            episode_id = str(sample.get("episode_id"))
            episode_partitions.setdefault(
                episode_id,
                {
                    "episode_id": episode_id,
                    "area_id": sample.get("area_id"),
                    "target_date": sample.get("metadata", {}).get("target_date"),
                    "prediction_target": sample.get("prediction_target"),
                    "partition": sample.get("partition"),
                    "chronological_partition": sample.get(
                        "chronological_partition"
                    ),
                },
            )

        path = models_dir / model_filename(feature_set_id, species_id)
        joblib.dump(
            {
                "schema_version": "1.2",
                "kind": "mushroom_ml_experiment_bundle",
                "feature_set_id": feature_set_id,
                "feature_cols": feature_cols,
                "species_id": species_id,
                "models": production_models,
                "estimator_availability": estimator_availability,
                "fit_scope": "all_benchmark_samples_after_grouped_temporal_evaluation",
                "n_samples": len(species_samples),
                "n_episodes": episode_count,
                "feature_support": _feature_support(species_samples, feature_cols),
                "evaluation_training_feature_support": _feature_support(
                    train_samples, feature_cols
                ),
                "episode_partitions": sorted(
                    episode_partitions.values(),
                    key=lambda row: str(row.get("episode_id")),
                ),
                "held_out_predictions": sorted(
                    held_out_predictions.values(),
                    key=lambda row: str(row.get("sample_id")),
                ),
                "temporal_validation": temporal_validation,
                "evaluation": {
                    "available": evaluation_available,
                    "reason": evaluation_reason,
                    "baseline": dict(
                        estimator_reports["train_prevalence_v1"].get("test", {})
                    ),
                    "estimators": {
                        estimator_id: dict(
                            estimator_reports[estimator_id].get("test", {})
                        )
                        for estimator_id in EXPERIMENT_ESTIMATOR_IDS
                    },
                    "partition": {
                        "train_favorable": int(np.sum(y_train)),
                        "train_unfavorable": int(len(y_train) - np.sum(y_train)),
                        "test_favorable": int(np.sum(y_test)),
                        "test_unfavorable": int(len(y_test) - np.sum(y_test)),
                    },
                },
                "generated_at": datetime.now(UTC).isoformat(),
                "features_sha256": features_sha256,
                "training_features_identity_policy": (
                    "artifact_sha256_provenance_only"
                ),
                "known_sites_sha256": known_sites_sha256,
                "known_sites_identity_contract": (
                    dict(known_sites_identity.get("contract") or {})
                    if known_sites_identity is not None
                    else None
                ),
                "known_sites_semantic_sha256": (
                    known_sites_identity.get("sha256")
                    if known_sites_identity is not None
                    else None
                ),
                "known_sites_area_sha256": (
                    dict(known_sites_identity.get("area_sha256") or {})
                    if known_sites_identity is not None
                    else None
                ),
                "version_id": version_id,
            },
            path,
        )
        species_results.append(
            {
                "species_id": species_id,
                "n_episodes": episode_count,
                "n_samples": len(species_samples),
                "n_train": len(train_samples),
                "n_test": len(test_samples),
                "stratified_evaluation": {
                    "available": evaluation_available,
                    "reason": evaluation_reason,
                    "train_favorable": int(np.sum(y_train)),
                    "train_unfavorable": int(len(y_train) - np.sum(y_train)),
                    "test_favorable": int(np.sum(y_test)),
                    "test_unfavorable": int(len(y_test) - np.sum(y_test)),
                },
                "temporal_validation": temporal_validation,
                "coverage": {
                    "enough_history_samples": sum(
                        bool(sample.get("metadata", {}).get("enough_history"))
                        for sample in species_samples
                    ),
                    "total_samples": len(species_samples),
                },
                "estimators": estimator_reports,
                "model_path": str(path),
            }
        )

    return {
        "feature_set_id": feature_set_id,
        "version_id": version_id,
        "feature_cols": feature_cols,
        "episode_count": benchmark.get("episode_count", 0),
        "sample_count": benchmark.get("sample_count", 0),
        "training_eligible_sample_count": len(samples),
        "training_ineligible_sample_count": len(audit_samples) - len(samples),
        "training_ineligibility_reasons": dict(
            sorted(
                Counter(
                    reason
                    for sample in audit_samples
                    if not bool(
                        sample.get("metadata", {}).get("training_eligible", True)
                    )
                    for reason in sample.get("metadata", {}).get(
                        "training_ineligibility_reasons", []
                    )
                ).items()
            )
        ),
        "species_results": species_results,
    }


def run(
    *,
    features_path: Path,
    known_sites_path: Path,
    models_dir: Path,
    report_path: Path,
    min_episodes: int = 20,
    feature_set_ids: tuple[str, ...] = DEFAULT_FEATURE_SET_IDS,
    species_ids: list[str] | None = None,
    version_registry_path: Path | None = None,
) -> dict[str, Any]:
    rows = load_features(features_path)
    if species_ids is not None:
        selected = {str(value) for value in species_ids}
        rows = [row for row in rows if str(row.get("species_id")) in selected]
    mapping = load_micro_area_to_area(known_sites_path)
    area_altitudes = load_area_representative_altitudes(known_sites_path)
    features_sha256 = hashlib.sha256(features_path.read_bytes()).hexdigest()
    known_sites_sha256 = hashlib.sha256(known_sites_path.read_bytes()).hexdigest()
    registry = mushroom_ml_version_registry.load_registry(
        version_registry_path or mushroom_paths.mushroom_ml_version_registry_path()
    )
    results: list[dict[str, Any]] = []
    for feature_set_id in feature_set_ids:
        version = mushroom_ml_version_registry.version_for_temporal_contract(
            registry, feature_set_id
        )
        identity_contract = version.get("known_sites_identity_contract")
        if not isinstance(identity_contract, dict):
            raise ValueError(
                f"ML version {version['version_id']} has no known_sites identity contract."
            )
        semantic_identity = mushroom_ml_input_identity.known_sites_semantic_identity_from_path(
            known_sites_path, identity_contract
        )
        semantic_identity["contract"] = identity_contract
        benchmark = build_benchmark(
            rows,
            mapping,
            area_representative_altitudes=area_altitudes,
            feature_set_id=feature_set_id,
        )
        results.append(
            train_benchmark(
                benchmark,
                models_dir,
                min_episodes=min_episodes,
                features_sha256=features_sha256,
                known_sites_sha256=known_sites_sha256,
                known_sites_identity=semantic_identity,
                version_id=str(version["version_id"]),
            )
        )
    report = {
        "schema_version": "1.0",
        "kind": "mushroom_ml_experiment_report",
        "generated_at": datetime.now(UTC).isoformat(),
        "features_sha256": features_sha256,
        "known_sites_sha256": known_sites_sha256,
        "version_registry": mushroom_ml_version_registry.benchmark_version_metadata(
            registry,
            list(
                dict.fromkeys(
                    str(result["version_id"])
                    for result in results
                    if result.get("version_id")
                )
            ),
        ),
        "partition_contract": (
            "deterministic_stratified_70_30_grouped_by_species_and_target_date_seed_42"
        ),
        "chronological_diagnostic_contract": (
            "chronological_target_dates_70_30_grouped_by_species_and_target_date"
        ),
        "feature_sets": results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Train shadow mushroom ML comparison models.")
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--known-sites", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--min-episodes", type=int, default=20)
    parser.add_argument("--feature-sets", nargs="+", choices=sorted(FEATURE_SETS), default=list(DEFAULT_FEATURE_SET_IDS))
    parser.add_argument("--species", nargs="+")
    args = parser.parse_args()
    run(
        features_path=args.features,
        known_sites_path=args.known_sites,
        models_dir=args.models_dir,
        report_path=args.report,
        min_episodes=args.min_episodes,
        feature_set_ids=tuple(args.feature_sets),
        species_ids=args.species,
    )


if __name__ == "__main__":
    main()
