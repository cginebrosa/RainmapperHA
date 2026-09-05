"""Exact per-estimator inference for immutable multiversion artifacts."""

from __future__ import annotations

import hashlib
import math
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Any, Mapping, Sequence

import numpy as np

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from rainmapper_core.mushroom_ml_predictor import _label


_ARTIFACT_CACHE_MAX_ENTRIES = 128
_artifact_cache: OrderedDict[tuple[str, str, int, int], dict[str, Any]] = (
    OrderedDict()
)
_artifact_cache_lock = RLock()


def is_rainfall_feature(feature_name: object) -> bool:
    """Identify the precipitation inputs covered by the warning-only policy."""
    normalized = str(feature_name).strip().lower()
    return (
        normalized.startswith(("rain_", "rainfall_"))
        or "rain_mm" in normalized
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clear_artifact_cache() -> int:
    """Release hash-verified immutable bundles after a runtime replacement."""
    with _artifact_cache_lock:
        released = len(_artifact_cache)
        _artifact_cache.clear()
    return released


def _artifact_row(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    model_ref: catalog.ModelRef,
    *,
    checked_manifest: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    checked = (
        checked_manifest
        if checked_manifest is not None
        else catalog.validate_batch_manifest(registry, manifest)
    )
    wanted = catalog.artifact_ref_for_model_ref(registry, model_ref)
    row = next(
        (
            dict(value)
            for value in checked["artifacts"]
            if catalog.ModelArtifactRef.from_mapping(value["artifact_ref"]).key
            == wanted.key
            and model_ref.horizon_days in value["supported_horizons"]
        ),
        None,
    )
    if row is None:
        raise FileNotFoundError(f"Model is not present in runtime batch: {model_ref.key}")
    return row


def load_exact_artifact(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    model_ref: catalog.ModelRef | Mapping[str, object],
    *,
    root: Path,
    checked_manifest: Mapping[str, object] | None = None,
    artifact_row: Mapping[str, object] | None = None,
    validated_model_ref: catalog.ModelRef | None = None,
) -> dict[str, Any]:
    """Load one hash-verified artifact and reject identity substitution."""
    import joblib

    wanted = validated_model_ref or catalog.validate_model_ref(registry, model_ref)
    row = (
        dict(artifact_row)
        if artifact_row is not None
        else _artifact_row(
            registry,
            manifest,
            wanted,
            checked_manifest=checked_manifest,
        )
    )
    path = Path(root) / str(row["path"])
    if not path.is_file():
        raise FileNotFoundError(f"Runtime model file is missing: {path}")
    stat = path.stat()
    resolved_path = str(path.resolve())
    declared_digest = str(row["sha256"])
    cache_key = (
        resolved_path,
        declared_digest,
        stat.st_mtime_ns,
        stat.st_size,
    )
    with _artifact_cache_lock:
        cached = _artifact_cache.get(cache_key)
        if cached is not None:
            _artifact_cache.move_to_end(cache_key)
            return cached

        if _sha256(path) != declared_digest:
            raise ValueError(f"Runtime model digest mismatch: {path}")
        bundle = joblib.load(path)
        if not isinstance(bundle, dict):
            raise ValueError("Runtime model bundle must be an object")
        actual = catalog.ModelArtifactRef.from_mapping(bundle.get("artifact_ref") or {})
        expected = catalog.ModelArtifactRef.from_mapping(row["artifact_ref"])
        if actual != expected:
            raise ValueError("Runtime model bundle identity mismatch")

        # A replaced immutable runtime must not retain an older object for the
        # same pathname. Digest and stat identity still guard every cache hit.
        for stale_key in [key for key in _artifact_cache if key[0] == resolved_path]:
            del _artifact_cache[stale_key]
        _artifact_cache[cache_key] = bundle
        while len(_artifact_cache) > _ARTIFACT_CACHE_MAX_ENTRIES:
            _artifact_cache.popitem(last=False)
        return bundle


def predict_bundle(
    bundle: Mapping[str, Any],
    features: Mapping[str, object],
    *,
    species_id: str,
) -> dict[str, Any]:
    """Predict with one member only; never average estimators or versions."""
    return predict_bundle_many(
        bundle,
        [features],
        species_ids=[species_id],
    )[0]


def predict_bundle_many(
    bundle: Mapping[str, Any],
    feature_rows: Sequence[Mapping[str, object]],
    *,
    species_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Predict multiple independent members in one estimator invocation."""
    if not feature_rows:
        return []
    if len(feature_rows) != len(species_ids):
        raise ValueError("Runtime feature rows and species ids must have equal length")
    columns = [str(value) for value in bundle.get("feature_cols", [])]
    if not columns:
        raise ValueError("Runtime model bundle has no feature columns")
    row = np.asarray(
        [
            [
                float(features[column])
                if features.get(column) is not None
                else np.nan
                for column in columns
            ]
            for features in feature_rows
        ],
        dtype=float,
    )
    artifact_ref = catalog.ModelArtifactRef.from_mapping(
        bundle.get("artifact_ref") or {}
    )
    preprocessor = bundle.get("preprocessor")
    design = row
    if artifact_ref.version_id in {"biology_v6_smooth_hierarchical", smooth.WINDOWED_VERSION_ID}:
        if not isinstance(preprocessor, smooth.SmoothLagPreprocessor):
            raise ValueError("V6 runtime artifact has no smooth preprocessor")
        design = preprocessor.transform(row)
        if artifact_ref.estimator_id != "smooth_species_logistic_v1":
            species_order = [str(value) for value in bundle.get("species_order", [])]
            config = bundle.get("fit_config") or {}
            design = smooth.pooled_design(
                design,
                [str(value) for value in species_ids],
                species_order=species_order,
                deviation_scale=config.get("deviation_scale"),
            )
    elif isinstance(preprocessor, Mapping):
        imputer = preprocessor.get("imputer")
        scaler = preprocessor.get("scaler")
        if imputer is None or scaler is None:
            raise ValueError("Runtime preprocessing bundle is incomplete")
        design = scaler.transform(imputer.transform(row))
    model = bundle.get("model")
    if model is None or not hasattr(model, "predict_proba"):
        raise ValueError("Runtime model bundle has no probabilistic estimator")
    probabilities = np.asarray(model.predict_proba(design))
    if probabilities.ndim != 2 or probabilities.shape != (len(feature_rows), 2):
        raise ValueError("Runtime model returned an invalid probability matrix")
    return [
        _prediction_payload(
            bundle,
            artifact_ref=artifact_ref,
            columns=columns,
            features=features,
            species_id=str(species_id),
            probability=float(probabilities[index][1]),
        )
        for index, (features, species_id) in enumerate(
            zip(feature_rows, species_ids, strict=True)
        )
    ]


def _prediction_payload(
    bundle: Mapping[str, Any],
    *,
    artifact_ref: catalog.ModelArtifactRef,
    columns: Sequence[str],
    features: Mapping[str, object],
    species_id: str,
    probability: float,
) -> dict[str, Any]:
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError("Runtime model returned an invalid probability")
    missing = [column for column in columns if features.get(column) is None]
    support = bundle.get("feature_support") or {}
    outside: list[dict[str, Any]] = []
    for column in columns:
        bounds = support.get(column) if isinstance(support, Mapping) else None
        value = features.get(column)
        if not isinstance(bounds, Mapping) or value is None:
            continue
        try:
            numeric = float(value)
            minimum = float(bounds["min"])
            maximum = float(bounds["max"])
            mean = float(bounds["mean"])
            std = float(bounds["std"])
        except (KeyError, TypeError, ValueError):
            continue
        if numeric < minimum or numeric > maximum:
            outside.append(
                {
                    "feature": column,
                    "value": round(numeric, 6),
                    "training_min": round(minimum, 6),
                    "training_max": round(maximum, 6),
                    "standard_deviations": round(abs(numeric - mean) / std, 3) if std > 0 else None,
                }
            )
    outside.sort(
        key=lambda row: float(row.get("standard_deviations") or 0.0), reverse=True
    )
    for row in outside:
        rainfall_warning = is_rainfall_feature(row.get("feature"))
        row["applicability_effect"] = (
            "warning_only" if rainfall_warning else "may_block"
        )
    blocking_outside = [
        row for row in outside if row["applicability_effect"] != "warning_only"
    ]
    outside_ratio = len(outside) / len(columns)
    blocking_outside_ratio = len(blocking_outside) / len(columns)
    applicability = (
        "outside_domain"
        if blocking_outside_ratio >= 0.05
        or any(
            float(row.get("standard_deviations") or 0) >= 3
            for row in blocking_outside
        )
        else "caution"
        if outside
        else "within_observed_range"
    )
    return {
        "artifact_ref": artifact_ref.as_dict(),
        "species_id": species_id,
        "estimator_id": artifact_ref.estimator_id,
        "probability": round(probability, 6),
        "label": _label(probability),
        "feature_count": len(columns),
        "missing_feature_count": len(missing),
        "missing_features": missing,
        "applicability": {
            "status": applicability,
            "outside_feature_count": len(outside),
            "checked_feature_count": len(columns),
            "outside_feature_ratio": round(outside_ratio, 6),
            "blocking_outside_feature_count": len(blocking_outside),
            "blocking_outside_feature_ratio": round(blocking_outside_ratio, 6),
            "rainfall_warning_feature_count": len(outside) - len(blocking_outside),
            "most_extreme": outside[:5],
        },
        "ensemble_used": False,
    }
