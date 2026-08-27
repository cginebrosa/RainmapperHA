"""Immutable tuning decisions reused by operational mushroom rebuilds."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib

from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_performance_telemetry
from rainmapper_core import mushroom_ml_version_registry


SCHEMA_VERSION = "1.0"
KIND = "mushroom_ml_tuning_catalog"
IMPLEMENTATION_REVISION = "operational-tuning-2026-08-26.1"
SCOPE_KEYS = (
    "version_id",
    "temporal_contract_id",
    "profile_id",
    "estimator_id",
    "species_id",
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    mushroom_performance_telemetry.add(
        files_read=1,
        bytes_read=size,
        hashes=1,
        hash_bytes=size,
    )
    return digest.hexdigest()


def compatibility_fingerprint(registry: Mapping[str, object]) -> str:
    payload = {
        "implementation_revision": IMPLEMENTATION_REVISION,
        "training_contract_revision": (
            mushroom_ml_version_registry.training_contract_revision(registry)
        ),
    }
    return "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()


def decision_scope(artifact_ref: Mapping[str, object]) -> dict[str, str]:
    scope = {key: str(artifact_ref.get(key) or "").strip() for key in SCOPE_KEYS}
    if any(not value for value in scope.values()):
        raise ValueError("Tuning decision scope is incomplete")
    return scope


def decision_key(scope: Mapping[str, object]) -> str:
    checked = decision_scope(scope)
    return "|".join(checked[key] for key in SCOPE_KEYS)


def _json_config(value: object, *, depth: int = 0) -> object:
    if depth > 8:
        raise ValueError("Tuning configuration is too deeply nested")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Tuning configuration contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _json_config(item, depth=depth + 1)
            for key, item in sorted(value.items(), key=lambda row: str(row[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_config(item, depth=depth + 1) for item in value]
    raise ValueError(f"Unsupported tuning configuration value: {type(value).__name__}")


def _validated_fit_config(scope: Mapping[str, str], value: object) -> dict[str, object]:
    config = _json_config(value or {})
    if not isinstance(config, dict):
        raise ValueError("Tuning fit_config must be an object")
    version_id = scope["version_id"]
    estimator_id = scope["estimator_id"]
    if version_id in {"altitude_v2", "biology_v3", "biology_v4"}:
        expected = set()
    elif version_id in {
        "biology_v5_raw_weather_discovery",
        "biology_v5_windowed_raw_weather",
    }:
        if estimator_id not in {
            "elastic_net_logistic_raw365_v1",
            "sparse_group_logistic_raw365_v1",
        }:
            raise ValueError(f"Unsupported V5 tuning estimator: {estimator_id}")
        expected = (
            {"C", "l1_ratio", "class_weight", "inner_selection_available"}
            if estimator_id == "elastic_net_logistic_raw365_v1"
            else {"regularization", "l1_ratio", "inner_selection_available"}
        )
    elif version_id in {
        "biology_v6_smooth_hierarchical",
        "biology_v6_windowed_smooth_hierarchical",
    }:
        if estimator_id not in {
            "smooth_species_logistic_v1",
            "smooth_shared_logistic_v1",
            "smooth_partial_pooling_logistic_v1",
        }:
            raise ValueError(f"Unsupported V6 tuning estimator: {estimator_id}")
        expected = {"C", "deviation_scale"}
    else:
        raise ValueError(f"Unsupported tuning catalog version: {version_id}")
    if set(config) != expected:
        raise ValueError(
            f"Tuning fit_config keys are invalid for {version_id}/{estimator_id}"
        )
    return config


def _expected_keys(training_plan: Mapping[str, object]) -> set[str]:
    fits = training_plan.get("fits")
    if not isinstance(fits, Sequence) or isinstance(fits, (str, bytes)):
        raise ValueError("Training plan fits are invalid")
    return {
        decision_key(row.get("artifact_ref") or {})
        for row in fits
        if isinstance(row, Mapping)
    }


def validate_catalog(
    registry: Mapping[str, object],
    payload: object,
    *,
    training_plan: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("Tuning catalog must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("kind") != KIND:
        raise ValueError("Tuning catalog contract is invalid")
    fingerprint = str(payload.get("compatibility_fingerprint") or "")
    if fingerprint != compatibility_fingerprint(registry):
        raise ValueError("Tuning catalog is incompatible with the training contract")
    source_batch_id = str(payload.get("source_batch_id") or "").strip()
    source_snapshot_id = str(payload.get("source_snapshot_id") or "").strip()
    if not source_batch_id or not re.fullmatch(r"sha256:[0-9a-f]{64}", source_snapshot_id):
        raise ValueError("Tuning catalog source identity is invalid")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("Tuning catalog must contain decisions")
    checked_decisions = []
    seen = set()
    for row in decisions:
        if not isinstance(row, Mapping):
            raise ValueError("Tuning catalog decision must be an object")
        scope = decision_scope(row.get("scope") or {})
        key = decision_key(scope)
        if row.get("key") != key or key in seen:
            raise ValueError("Tuning catalog contains an invalid or duplicate key")
        seen.add(key)
        artifact_sha256 = str(row.get("source_artifact_sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
            raise ValueError("Tuning decision artifact digest is invalid")
        checked_decisions.append(
            {
                "key": key,
                "scope": scope,
                "fit_config": _validated_fit_config(
                    scope, row.get("fit_config") or {}
                ),
                "source_artifact_sha256": artifact_sha256,
            }
        )
    checked_decisions.sort(key=lambda row: row["key"])
    if training_plan is not None:
        expected = _expected_keys(training_plan)
        if seen != expected:
            missing = len(expected - seen)
            unexpected = len(seen - expected)
            raise ValueError(
                f"Tuning catalog does not cover the plan: {missing} missing, "
                f"{unexpected} unexpected"
            )
    identity_payload = {
        "compatibility_fingerprint": fingerprint,
        "source_batch_id": source_batch_id,
        "source_snapshot_id": source_snapshot_id,
        "decisions": checked_decisions,
    }
    catalog_id = "sha256:" + hashlib.sha256(_canonical(identity_payload)).hexdigest()
    if payload.get("catalog_id") != catalog_id:
        raise ValueError("Tuning catalog identity is invalid")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "catalog_id": catalog_id,
        **identity_payload,
    }


def build_from_batch(
    registry: Mapping[str, object],
    manifest: object,
    *,
    batch_root: Path,
    training_plan: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    checked_manifest = mushroom_ml_model_catalog.validate_batch_manifest(
        registry, manifest
    )
    batch_id = checked_manifest["batch_id"]
    batch_root = Path(batch_root)
    decisions = []
    for artifact in checked_manifest["artifacts"]:
        relative = Path(artifact["path"])
        expected_prefix = Path("batches", batch_id)
        try:
            within_batch = relative.relative_to(expected_prefix)
        except ValueError as exc:
            raise ValueError("Runtime artifact is outside its batch") from exc
        path = batch_root / within_batch
        if not path.is_file() or _sha256(path) != artifact["sha256"]:
            raise ValueError("Runtime artifact does not match its manifest")
        artifact_size = path.stat().st_size
        bundle = joblib.load(path)
        mushroom_performance_telemetry.add(
            files_read=1,
            bytes_read=artifact_size,
        )
        if not isinstance(bundle, Mapping):
            raise ValueError("Runtime artifact bundle is invalid")
        artifact_ref = artifact["artifact_ref"]
        if bundle.get("artifact_ref") != artifact_ref:
            raise ValueError("Runtime artifact identity does not match its manifest")
        if bundle.get("snapshot_id") != checked_manifest["snapshot_id"]:
            raise ValueError("Runtime artifact snapshot does not match its batch")
        decisions.append(
            {
                "key": decision_key(artifact_ref),
                "scope": decision_scope(artifact_ref),
                "fit_config": _validated_fit_config(
                    decision_scope(artifact_ref), bundle.get("fit_config") or {}
                ),
                "source_artifact_sha256": artifact["sha256"],
            }
        )
    decisions.sort(key=lambda row: row["key"])
    identity_payload = {
        "compatibility_fingerprint": compatibility_fingerprint(registry),
        "source_batch_id": batch_id,
        "source_snapshot_id": checked_manifest["snapshot_id"],
        "decisions": decisions,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "catalog_id": "sha256:" + hashlib.sha256(_canonical(identity_payload)).hexdigest(),
        **identity_payload,
    }
    return validate_catalog(registry, payload, training_plan=training_plan)


def lookup(payload: Mapping[str, object], artifact_ref: Mapping[str, object]) -> dict[str, Any]:
    key = decision_key(artifact_ref)
    for row in payload.get("decisions") or []:
        if isinstance(row, Mapping) and row.get("key") == key:
            return dict(row)
    raise KeyError(key)


def resolve_temporal_contract(
    payload: Mapping[str, object],
    *,
    version_id: str,
    profile_id: str,
    source_temporal_contract_id: str,
) -> str:
    """Resolve a version's declared contract from a fixed/lag source family."""
    family = str(source_temporal_contract_id or "").split("_", 1)[0]
    if family not in {"fixed", "lag"}:
        raise ValueError("Tuning source temporal contract family is invalid")
    candidates = {
        str((row.get("scope") or {}).get("temporal_contract_id") or "")
        for row in payload.get("decisions") or []
        if isinstance(row, Mapping)
        and (row.get("scope") or {}).get("version_id") == version_id
        and (row.get("scope") or {}).get("profile_id") == profile_id
        and str((row.get("scope") or {}).get("temporal_contract_id") or "").startswith(
            family + "_"
        )
    }
    if len(candidates) != 1:
        raise ValueError(
            "Tuning catalog does not declare exactly one compatible temporal contract"
        )
    return next(iter(candidates))


def installed_source_batch_id(
    registry: Mapping[str, object], version_ids: Sequence[str]
) -> str:
    checked = mushroom_ml_version_registry.validate_registry(registry)
    selected = {str(value) for value in version_ids}
    batch_ids = set()
    covered = set()
    for version in checked["versions"]:
        version_id = str(version["version_id"])
        if version_id not in selected:
            continue
        generation_id = version.get("installed_generation_id")
        generation = next(
            (
                row
                for row in version.get("generations", [])
                if row.get("generation_id") == generation_id
            ),
            None,
        )
        if generation is None or not generation.get("batch_id"):
            raise ValueError(f"Installed tuning source is missing for {version_id}")
        covered.add(version_id)
        batch_ids.add(str(generation["batch_id"]))
    if covered != selected or len(batch_ids) != 1:
        raise ValueError("Selected versions do not share one installed tuning source batch")
    return next(iter(batch_ids))


def save(path: Path, payload: Mapping[str, object]) -> None:
    content = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        mushroom_performance_telemetry.add(
            files_written=1,
            bytes_written=len(content),
            fsyncs=2,
        )
    finally:
        temporary.unlink(missing_ok=True)
