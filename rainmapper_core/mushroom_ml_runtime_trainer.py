"""Fit immutable non-active runtime artifacts for the V2--V6 catalog.

This module never promotes a batch.  It only writes a new content-verified
batch directory; activation is an explicit separate coordinator operation.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import warnings
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from sklearn.exceptions import ConvergenceWarning

from rainmapper_core import mushroom_ml_biology_v3_evaluation
from rainmapper_core import mushroom_ml_biology_v3_physical
from rainmapper_core import mushroom_ml_biology_v4
from rainmapper_core import mushroom_ml_holdout
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core.mushroom_ml_sparse_group import SparseGroupLogisticClassifier


ARTIFACT_SCHEMA_VERSION = "1.0"
ARTIFACT_KIND = "mushroom_ml_runtime_model"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def benchmark_key(version_id: str, temporal_contract_id: str, profile_id: str) -> str:
    return "|".join((version_id, temporal_contract_id, profile_id))


def supported_runtime_benchmark_keys() -> frozenset[str]:
    """Return the registry members this runtime can materialize from shared inputs."""
    keys: set[str] = set()
    for _temporal, v2_contract, v3_contract, v4_contract, v5_contract, v6_contract in (
        (
            "fixed",
            "fixed_gap_7d_altitude_v2",
            "fixed_gap_7d_biology_v3",
            "fixed_gap_7d_biology_v4",
            "fixed_gap_7d_biology_v5_raw365_v2",
            "fixed_gap_7d_biology_v6_smooth_hierarchical_v2",
        ),
        (
            "lag",
            "lag_event_altitude_v2",
            "lag_event_biology_v3",
            "lag_event_biology_v4",
            "lag_event_biology_v5_raw365_v2",
            "lag_event_biology_v6_smooth_hierarchical_v2",
        ),
    ):
        keys.add(benchmark_key("altitude_v2", v2_contract, "common_idw"))
        keys.add(benchmark_key("biology_v3", v3_contract, "core"))
        keys.add(
            benchmark_key(
                "biology_v3",
                v3_contract,
                mushroom_ml_biology_v3_physical.PROFILE_ID,
            )
        )
        for profile_id in ("extended_weather", "climatic_balance"):
            keys.add(benchmark_key("biology_v4", v4_contract, profile_id))
        keys.add(
            benchmark_key(
                "biology_v5_raw_weather_discovery",
                v5_contract,
                "raw_primary_plus_physical_state",
            )
        )
        keys.add(
            benchmark_key(
                "biology_v6_smooth_hierarchical",
                v6_contract,
                "smooth_weather_physical_state",
            )
        )
        for window_days in raw.WINDOW_DAYS_OPTIONS:
            keys.add(
                benchmark_key(
                    raw.WINDOWED_VERSION_ID, v5_contract, raw.windowed_profile_id(window_days)
                )
            )
            keys.add(
                benchmark_key(
                    smooth.WINDOWED_VERSION_ID,
                    v6_contract,
                    smooth.windowed_profile_id(window_days),
                )
            )
    return frozenset(keys)


def validate_benchmark_coverage(
    training_plan: Mapping[str, Any],
    available_keys: Sequence[str] | set[str] | frozenset[str],
) -> None:
    """Reject a registry/runtime mismatch before performing any model fits."""
    fits = training_plan.get("fits")
    if not isinstance(fits, Sequence) or not fits:
        raise ValueError("Multiversion training plan contains no fits")
    available = set(available_keys)
    missing: set[str] = set()
    for fit in fits:
        if not isinstance(fit, Mapping):
            raise ValueError("Invalid multiversion fit row")
        artifact_ref = fit.get("artifact_ref")
        if not isinstance(artifact_ref, Mapping):
            raise ValueError("Invalid multiversion artifact reference")
        key = benchmark_key(
            str(artifact_ref.get("version_id") or ""),
            str(artifact_ref.get("temporal_contract_id") or ""),
            str(artifact_ref.get("profile_id") or ""),
        )
        if key not in available:
            missing.add(key)
    if missing:
        raise ValueError(
            "Runtime registry is incompatible with the available benchmark contracts: "
            + ", ".join(sorted(missing))
        )


def materialize_runtime_benchmarks(
    *,
    v3_fixed: Mapping[str, Any],
    v3_lag: Mapping[str, Any],
    v4_fixed: Mapping[str, Any] | None = None,
    v4_lag: Mapping[str, Any] | None = None,
    v5_fixed: Mapping[str, Any] | None = None,
    v5_lag: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Derive runtime profiles available from the supplied base datasets."""
    result: dict[str, dict[str, Any]] = {}
    rows = (
        (
            "fixed",
            dict(v3_fixed),
            dict(v4_fixed) if v4_fixed is not None else None,
            dict(v5_fixed) if v5_fixed is not None else None,
            "fixed_gap_7d_altitude_v2",
            "fixed_gap_7d_biology_v3",
            "fixed_gap_7d_biology_v4",
            "fixed_gap_7d_biology_v5_raw365_v2",
            "fixed_gap_7d_biology_v6_smooth_hierarchical_v2",
        ),
        (
            "lag",
            dict(v3_lag),
            dict(v4_lag) if v4_lag is not None else None,
            dict(v5_lag) if v5_lag is not None else None,
            "lag_event_altitude_v2",
            "lag_event_biology_v3",
            "lag_event_biology_v4",
            "lag_event_biology_v5_raw365_v2",
            "lag_event_biology_v6_smooth_hierarchical_v2",
        ),
    )
    for (
        _temporal,
        v3,
        v4,
        v5,
        v2_contract,
        v3_contract,
        v4_contract,
        v5_contract,
        v6_contract,
    ) in rows:
        result[benchmark_key("altitude_v2", v2_contract, "common_idw")] = (
            mushroom_ml_biology_v3_evaluation.build_observation_altitude_v2_common_idw_benchmark(v3)
        )
        result[benchmark_key("biology_v3", v3_contract, "core")] = v3
        if v4 is not None:
            result[
                benchmark_key(
                    "biology_v3",
                    v3_contract,
                    mushroom_ml_biology_v3_physical.PROFILE_ID,
                )
            ] = dict(mushroom_ml_biology_v3_physical.materialize_benchmark(v4))
            for profile_id in ("extended_weather", "climatic_balance"):
                result[benchmark_key("biology_v4", v4_contract, profile_id)] = dict(
                    mushroom_ml_biology_v4.materialize_comparison_benchmark(
                        v4, profile_id=profile_id
                    )
                )
        if v5 is not None:
            result[
                benchmark_key(
                    "biology_v5_raw_weather_discovery",
                    v5_contract,
                    "raw_primary_plus_physical_state",
                )
            ] = v5
            result[
                benchmark_key(
                    "biology_v6_smooth_hierarchical",
                    v6_contract,
                    "smooth_weather_physical_state",
                )
            ] = v5
            for window_days in raw.WINDOW_DAYS_OPTIONS:
                result[
                    benchmark_key(
                        raw.WINDOWED_VERSION_ID,
                        v5_contract,
                        raw.windowed_profile_id(window_days),
                    )
                ] = v5
                result[
                    benchmark_key(
                        smooth.WINDOWED_VERSION_ID,
                        v6_contract,
                        smooth.windowed_profile_id(window_days),
                    )
                ] = v5
    return result


def _columns(artifact_ref: catalog.ModelArtifactRef, benchmark: Mapping[str, Any]) -> list[str]:
    feature_set = benchmark.get("feature_set") or {}
    if artifact_ref.version_id in {"biology_v5_raw_weather_discovery", raw.WINDOWED_VERSION_ID}:
        return list((feature_set.get("profiles") or {})[artifact_ref.profile_id])
    if artifact_ref.version_id == "biology_v6_smooth_hierarchical":
        return smooth.raw_columns(
            include_phenology=True,
            include_horizon=artifact_ref.temporal_contract_id.startswith("lag_event_"),
        )
    if artifact_ref.version_id == smooth.WINDOWED_VERSION_ID:
        window_days = smooth.window_days_from_profile_id(artifact_ref.profile_id)
        return smooth.raw_columns(
            include_phenology=True,
            include_horizon=artifact_ref.temporal_contract_id.startswith("lag_event_"),
            channels=raw.RAW_CHANNELS,
            window_days=window_days,
        )
    return list(
        feature_set.get("predictive_feature_cols")
        or feature_set.get("feature_cols")
        or []
    )


def _species(sample: Mapping[str, Any]) -> str:
    metadata = sample.get("metadata") or {}
    return str(metadata.get("species_id") or sample.get("species_id") or "")


def _fit_current(estimator_id: str, X: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    from rainmapper_core import mushroom_ml_experiment_trainer

    unavailable = mushroom_ml_experiment_trainer._estimator_unavailable_reason(
        estimator_id, y
    )
    if estimator_id == "knn_distance_v1" and len(y) < 7:
        unavailable = "KNN requires at least seven training samples"
    if unavailable:
        raise ValueError(unavailable)
    model = mushroom_ml_experiment_trainer._pipeline(estimator_id)
    model.fit(X, y)
    return {"model": model, "preprocessor": None, "fit_config": {}}


def _fit_v5(
    estimator_id: str,
    samples: list[dict[str, Any]],
    X: np.ndarray,
    y: np.ndarray,
    columns: list[str],
) -> dict[str, Any]:
    selected, selected_inside = mushroom_ml_holdout._select_v5(
        estimator_id, samples, X, y, columns, 14
    )
    scaled, _unused, imputer, scaler = mushroom_ml_holdout._preprocess(X, X)
    if estimator_id == mushroom_ml_holdout.V5_ESTIMATORS[0]:
        from sklearn.linear_model import LogisticRegression

        model = LogisticRegression(
            solver="saga", max_iter=1500, random_state=42, tol=1e-3, **selected
        )
    else:
        model = SparseGroupLogisticClassifier(
            groups=mushroom_ml_holdout._groups(columns),
            max_iter=2000,
            tolerance=1e-5,
            **selected,
        )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", (FutureWarning, ConvergenceWarning))
        model.fit(scaled, y)
    if estimator_id == mushroom_ml_holdout.V5_ESTIMATORS[1] and not model.converged_:
        raise ValueError("sparse-group estimator did not converge")
    return {
        "model": model,
        "preprocessor": {"imputer": imputer, "scaler": scaler},
        "fit_config": {**selected, "inner_selection_available": selected_inside},
    }


def _fit_v6(
    artifact_ref: catalog.ModelArtifactRef,
    samples: list[dict[str, Any]],
    X: np.ndarray,
    y: np.ndarray,
) -> dict[str, Any]:
    window_days = smooth.window_days_from_profile_id(artifact_ref.profile_id)
    if window_days is not None:
        preprocessor = smooth.SmoothLagPreprocessor(
            channels=raw.RAW_CHANNELS, window_days=window_days
        ).fit(X)
    else:
        preprocessor = smooth.SmoothLagPreprocessor().fit(X)
    transformed = preprocessor.transform(X)
    species = [_species(sample) for sample in samples]
    species_order = sorted(set(species))
    if artifact_ref.estimator_id == "smooth_species_logistic_v1":
        design = transformed
        config = {"C": 0.1, "deviation_scale": None}
    elif artifact_ref.estimator_id == "smooth_shared_logistic_v1":
        config = {"C": 0.1, "deviation_scale": None}
        design = smooth.pooled_design(
            transformed,
            species,
            species_order=species_order,
            deviation_scale=None,
        )
    elif artifact_ref.estimator_id == "smooth_partial_pooling_logistic_v1":
        config = {"C": 0.1, "deviation_scale": 4.0}
        design = smooth.pooled_design(
            transformed,
            species,
            species_order=species_order,
            deviation_scale=4.0,
        )
    else:
        raise ValueError(f"Unsupported V6 estimator: {artifact_ref.estimator_id}")
    model = smooth.fit_logistic(design, y, C=config["C"])
    return {
        "model": model,
        "preprocessor": preprocessor,
        "species_order": species_order,
        "fit_config": config,
    }


def fit_artifact(
    artifact_ref: catalog.ModelArtifactRef,
    benchmark: Mapping[str, Any],
    *,
    snapshot_id: str,
) -> dict[str, Any]:
    """Fit exactly one plan unit against all eligible rows, without promotion."""
    columns = _columns(artifact_ref, benchmark)
    if not columns:
        raise ValueError(f"Benchmark has no runtime columns: {artifact_ref.key}")
    samples = [dict(row) for row in mushroom_ml_holdout.eligible_samples(dict(benchmark))]
    if artifact_ref.species_id != "all_species":
        samples = [row for row in samples if _species(row) == artifact_ref.species_id]
    if not samples:
        raise ValueError(f"No eligible rows for runtime artifact: {artifact_ref.key}")
    X, y = mushroom_ml_holdout.matrix(samples, columns)
    if len(np.unique(y)) < 2:
        raise ValueError(f"Runtime artifact requires both classes: {artifact_ref.key}")
    if artifact_ref.version_id in {"altitude_v2", "biology_v3", "biology_v4"}:
        fitted = _fit_current(artifact_ref.estimator_id, X, y)
    elif artifact_ref.version_id in {"biology_v5_raw_weather_discovery", raw.WINDOWED_VERSION_ID}:
        fitted = _fit_v5(artifact_ref.estimator_id, samples, X, y, columns)
    elif artifact_ref.version_id in {"biology_v6_smooth_hierarchical", smooth.WINDOWED_VERSION_ID}:
        fitted = _fit_v6(artifact_ref, samples, X, y)
    else:
        raise ValueError(f"No runtime trainer for {artifact_ref.version_id}")
    feature_support = {}
    for index, column in enumerate(columns):
        values = X[:, index]
        finite = values[np.isfinite(values)]
        if len(finite):
            feature_support[column] = {
                "min": float(np.min(finite)),
                "max": float(np.max(finite)),
                "mean": float(np.mean(finite)),
                "std": float(np.std(finite)),
            }
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "kind": ARTIFACT_KIND,
        "artifact_ref": artifact_ref.as_dict(),
        "snapshot_id": snapshot_id,
        "feature_cols": columns,
        "training_row_count": len(samples),
        "training_species_ids": sorted({_species(row) for row in samples}),
        "feature_support": feature_support,
        **fitted,
    }


def write_batch(
    registry: Mapping[str, Any],
    training_plan: Mapping[str, Any],
    benchmarks: Mapping[str, Mapping[str, Any]],
    *,
    models_root: Path,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Write a new immutable batch in staging; never activate or overwrite."""
    import joblib

    checked_registry = mushroom_ml_version_registry.validate_registry(registry)
    batch_id = catalog._identifier(training_plan.get("batch_id"), "batch_id")
    snapshot_id = str(training_plan.get("snapshot_id") or "")
    fits = training_plan.get("fits")
    if not isinstance(fits, Sequence) or not fits:
        raise ValueError("Multiversion training plan contains no fits")
    validate_benchmark_coverage(training_plan, set(benchmarks))
    root = Path(models_root)
    batches = root / "batches"
    destination = batches / batch_id
    if destination.exists():
        raise FileExistsError(f"Runtime batch already exists: {destination}")
    batches.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{batch_id}.", suffix=".tmp", dir=batches))
    artifacts: list[dict[str, Any]] = []
    failed_fits: list[dict[str, Any]] = []
    fit_results: list[dict[str, Any]] = []
    try:
        for fit_index, fit in enumerate(fits, start=1):
            if not isinstance(fit, Mapping):
                raise ValueError("Invalid multiversion fit row")
            artifact_ref = catalog.validate_artifact_ref(
                checked_registry, fit.get("artifact_ref") or {}
            )
            key = benchmark_key(
                artifact_ref.version_id,
                artifact_ref.temporal_contract_id,
                artifact_ref.profile_id,
            )
            benchmark = benchmarks.get(key)
            if benchmark is None:
                raise ValueError(f"Runtime benchmark is missing: {key}")
            fit_started = time.perf_counter()
            try:
                bundle = fit_artifact(artifact_ref, benchmark, snapshot_id=snapshot_id)
            except ValueError as exc:
                duration_seconds = round(time.perf_counter() - fit_started, 6)
                failed_fits.append(
                    {
                        "artifact_ref": artifact_ref.as_dict(),
                        "reason": str(exc),
                    }
                )
                fit_results.append(
                    {
                        "artifact_ref": artifact_ref.as_dict(),
                        "status": "failed",
                        "duration_seconds": duration_seconds,
                        "reason": str(exc),
                    }
                )
                if progress_callback is not None:
                    progress_callback(
                        {
                            "completed_fit_count": fit_index,
                            "planned_fit_count": len(fits),
                            "successful_fit_count": len(artifacts),
                            "failed_fit_count": len(failed_fits),
                            "version_id": artifact_ref.version_id,
                            "species_id": artifact_ref.species_id,
                            "profile_id": artifact_ref.profile_id,
                            "estimator_id": artifact_ref.estimator_id,
                            "duration_seconds": duration_seconds,
                        }
                    )
                continue
            final_relative = catalog.model_relative_path(artifact_ref)
            within_batch = Path(*final_relative.parts[2:])
            target = staging / within_batch
            target.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(bundle, target)
            duration_seconds = round(time.perf_counter() - fit_started, 6)
            artifacts.append(
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": list(fit["supported_horizons"]),
                    "path": final_relative.as_posix(),
                    "sha256": sha256(target),
                }
            )
            fit_results.append(
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "status": "complete",
                    "duration_seconds": duration_seconds,
                    "training_row_count": int(bundle["training_row_count"]),
                }
            )
            if progress_callback is not None:
                progress_callback(
                    {
                        "completed_fit_count": fit_index,
                        "planned_fit_count": len(fits),
                        "successful_fit_count": len(artifacts),
                        "failed_fit_count": len(failed_fits),
                        "version_id": artifact_ref.version_id,
                        "species_id": artifact_ref.species_id,
                        "profile_id": artifact_ref.profile_id,
                        "estimator_id": artifact_ref.estimator_id,
                        "duration_seconds": duration_seconds,
                    }
                )
        manifest = catalog.validate_batch_manifest(
            checked_registry,
            {
                "schema_version": catalog.SCHEMA_VERSION,
                "kind": catalog.BATCH_MANIFEST_KIND,
                "batch_id": batch_id,
                "snapshot_id": snapshot_id,
                "version_ids": list(training_plan.get("version_ids") or []),
                "species_ids": list(training_plan.get("species_ids") or []),
                "profile_keys": list(training_plan.get("profile_keys") or []),
                "artifacts": artifacts,
                    "active": False,
                    "operational_candidate_trained": False,
                    "planned_fit_count": len(fits),
                    "successful_fit_count": len(artifacts),
                    "failed_fit_count": len(failed_fits),
                    "failed_fits": failed_fits,
                    "fit_results": fit_results,
                },
            )
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, destination)
        return destination, manifest
    finally:
        if staging.exists():
            import shutil

            shutil.rmtree(staging, ignore_errors=True)
