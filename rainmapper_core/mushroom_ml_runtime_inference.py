"""Exact per-estimator inference for immutable multiversion artifacts."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from rainmapper_core.mushroom_ml_predictor import _label


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _artifact_row(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    model_ref: catalog.ModelRef,
) -> dict[str, Any]:
    checked = catalog.validate_batch_manifest(registry, manifest)
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
) -> dict[str, Any]:
    """Load one hash-verified artifact and reject identity substitution."""
    import joblib

    wanted = catalog.validate_model_ref(registry, model_ref)
    row = _artifact_row(registry, manifest, wanted)
    path = Path(root) / str(row["path"])
    if not path.is_file():
        raise FileNotFoundError(f"Runtime model file is missing: {path}")
    if _sha256(path) != row["sha256"]:
        raise ValueError(f"Runtime model digest mismatch: {path}")
    bundle = joblib.load(path)
    if not isinstance(bundle, dict):
        raise ValueError("Runtime model bundle must be an object")
    actual = catalog.ModelArtifactRef.from_mapping(bundle.get("artifact_ref") or {})
    expected = catalog.artifact_ref_for_model_ref(registry, wanted)
    if actual != expected:
        raise ValueError("Runtime model bundle identity mismatch")
    return bundle


def predict_bundle(
    bundle: Mapping[str, Any],
    features: Mapping[str, object],
    *,
    species_id: str,
) -> dict[str, Any]:
    """Predict with one member only; never average estimators or versions."""
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
        ],
        dtype=float,
    )
    artifact_ref = catalog.ModelArtifactRef.from_mapping(
        bundle.get("artifact_ref") or {}
    )
    preprocessor = bundle.get("preprocessor")
    design = row
    if artifact_ref.version_id == "biology_v6_smooth_hierarchical":
        if not isinstance(preprocessor, smooth.SmoothLagPreprocessor):
            raise ValueError("V6 runtime artifact has no smooth preprocessor")
        design = preprocessor.transform(row)
        if artifact_ref.estimator_id != "smooth_species_logistic_v1":
            species_order = [str(value) for value in bundle.get("species_order", [])]
            config = bundle.get("fit_config") or {}
            design = smooth.pooled_design(
                design,
                [species_id],
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
    probability = float(model.predict_proba(design)[0][1])
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
    outside_ratio = len(outside) / len(columns)
    applicability = (
        "outside_domain"
        if outside_ratio >= 0.05 or any(float(row.get("standard_deviations") or 0) >= 3 for row in outside)
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
            "most_extreme": outside[:5],
        },
        "ensemble_used": False,
    }
