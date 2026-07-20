"""Versioned job and result contracts for portable mushroom rebuilds."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import (
    mushroom_rebuild_pipeline,
    mushroom_rebuild_snapshot,
)


SCHEMA_VERSION = "0.1"
JOB_SPEC_KIND = "mushroom_rebuild_job_spec"
RESULT_MANIFEST_KIND = "mushroom_rebuild_result_manifest"
JOB_SPEC_NAME = "job_spec.json"
RESULT_MANIFEST_NAME = "result_manifest.json"
SUPPORTED_SCOPES = {"all", "visible", "species", "pending"}
EXPECTED_ARTIFACT_PATHS = (
    "mushroom_gis_observation_reconstruction.json",
    "mushroom_observations_weather_features.json",
    "mushroom_observations_weather_features.csv",
    "reports/mushroom_observations_weather_features.md",
    "mushroom_observation_features_v0.json",
    "mushroom_observation_features_v0.csv",
    "reports/mushroom_observation_features_v0.md",
    "mushroom_model_v0.json",
    "reports/mushroom_model_v0.md",
)


def _canonical_hash(payload: dict[str, Any], identity_field: str) -> str:
    normalized = copy.deepcopy(payload)
    normalized.pop(identity_field, None)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return payload


def load_job_spec(path: Path) -> dict[str, Any]:
    payload = _load_json_object(path.resolve(), "job spec")
    if payload.get("kind") != JOB_SPEC_KIND:
        raise ValueError(f"unexpected job spec kind: {payload.get('kind')}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported job spec schema: {payload.get('schema_version')}")
    return payload


def load_result_manifest(path: Path) -> dict[str, Any]:
    payload = _load_json_object(path.resolve(), "result manifest")
    if payload.get("kind") != RESULT_MANIFEST_KIND:
        raise ValueError(f"unexpected result manifest kind: {payload.get('kind')}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported result manifest schema: {payload.get('schema_version')}")
    return payload


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    target = path.resolve()
    if target.exists():
        raise FileExistsError(f"refusing to overwrite manifest: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _dataset_requirements(input_manifest: dict[str, Any]) -> list[dict[str, str]]:
    datasets = input_manifest.get("datasets")
    if not isinstance(datasets, list):
        raise ValueError("input manifest datasets must be a list")
    requirements = []
    for raw_dataset in datasets:
        if not isinstance(raw_dataset, dict):
            raise ValueError("input manifest contains an invalid dataset")
        dataset_id = str(raw_dataset.get("dataset_id", "")).strip()
        fingerprint = str(raw_dataset.get("fingerprint", "")).strip()
        if not dataset_id or not fingerprint.startswith("sha256:"):
            raise ValueError("input manifest contains an invalid dataset requirement")
        requirements.append({"dataset_id": dataset_id, "fingerprint": fingerprint})
    return requirements


def create_job_spec(
    snapshot_dir: Path,
    *,
    reconstruction_scope: str = "all",
    selected_observation_ids: list[str] | tuple[str, ...] | None = None,
    pending_species_ids: list[str] | tuple[str, ...] | None = None,
    job_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    snapshot_root = snapshot_dir.resolve()
    input_manifest = mushroom_rebuild_snapshot.load_manifest(snapshot_root)
    inputs = mushroom_rebuild_snapshot.resolved_input_paths(snapshot_root, input_manifest)
    observations_payload = mushroom_rebuild_pipeline.load_json_object(
        inputs["observations"],
        "observations",
    )
    observations = mushroom_rebuild_pipeline.observation_rows(observations_payload)
    eligible_ids = mushroom_rebuild_pipeline.eligible_observation_ids(observations)
    scope = str(reconstruction_scope).strip().lower()
    if scope not in SUPPORTED_SCOPES:
        raise ValueError(f"unsupported reconstruction scope: {reconstruction_scope}")
    selected_ids = [str(value).strip() for value in (selected_observation_ids or eligible_ids)]
    selected_ids = [value for value in selected_ids if value]
    pending_ids = sorted(
        {
            str(value).strip()
            for value in (pending_species_ids or [])
            if str(value).strip()
        }
    )
    if not selected_ids:
        raise ValueError("job spec requires at least one eligible observation")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": JOB_SPEC_KIND,
        "job_id": str(job_id or uuid.uuid4()),
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "job_type": "rebuild_v0",
        "pipeline": {"id": "mushroom_rebuild_v0", "contract_version": SCHEMA_VERSION},
        "input": {
            "manifest_kind": input_manifest.get("kind"),
            "manifest_schema_version": input_manifest.get("schema_version"),
            "snapshot_id": input_manifest.get("snapshot_id"),
        },
        "dataset_requirements": _dataset_requirements(input_manifest),
        "scope": {
            "reconstruction_scope": scope,
            "selected_observation_ids": selected_ids,
            "pending_species_ids": pending_ids,
        },
        "expected_artifacts": list(EXPECTED_ARTIFACT_PATHS),
    }
    payload["job_spec_id"] = _canonical_hash(payload, "job_spec_id")
    return payload


def verify_job_spec(
    job_spec: dict[str, Any],
    snapshot_dir: Path,
    *,
    gis_root_override: Path | None = None,
    verify_snapshot_files: bool = True,
    verify_gis_file_hashes: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    if job_spec.get("kind") != JOB_SPEC_KIND:
        errors.append("unexpected job spec kind")
    if job_spec.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported job spec schema")
    expected_id = _canonical_hash(job_spec, "job_spec_id")
    if job_spec.get("job_spec_id") != expected_id:
        errors.append("job spec hash mismatch")
    if job_spec.get("job_type") != "rebuild_v0":
        errors.append("unsupported job type")
    pipeline = job_spec.get("pipeline")
    if not isinstance(pipeline, dict) or pipeline != {
        "id": "mushroom_rebuild_v0",
        "contract_version": SCHEMA_VERSION,
    }:
        errors.append("unsupported pipeline contract")
    if job_spec.get("expected_artifacts") != list(EXPECTED_ARTIFACT_PATHS):
        errors.append("unexpected artifact contract")

    try:
        input_manifest = mushroom_rebuild_snapshot.load_manifest(snapshot_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load input manifest: {exc}")
        input_manifest = {}
    input_contract = job_spec.get("input")
    expected_input = {
        "manifest_kind": input_manifest.get("kind"),
        "manifest_schema_version": input_manifest.get("schema_version"),
        "snapshot_id": input_manifest.get("snapshot_id"),
    }
    if input_contract != expected_input:
        errors.append("job spec input manifest does not match snapshot")
    try:
        if job_spec.get("dataset_requirements") != _dataset_requirements(input_manifest):
            errors.append("job spec dataset requirements do not match snapshot")
    except ValueError as exc:
        errors.append(str(exc))

    if verify_snapshot_files and input_manifest:
        verification = mushroom_rebuild_snapshot.verify_snapshot(
            snapshot_dir,
            gis_root_override=gis_root_override,
            verify_gis_file_hashes=verify_gis_file_hashes,
        )
        if verification.get("status") != "valid":
            errors.extend(f"input verification: {error}" for error in verification.get("errors", []))

    scope = job_spec.get("scope")
    if not isinstance(scope, dict):
        errors.append("job spec scope must be an object")
    else:
        reconstruction_scope = str(scope.get("reconstruction_scope", ""))
        if reconstruction_scope not in SUPPORTED_SCOPES:
            errors.append("unsupported reconstruction scope")
        selected_ids = scope.get("selected_observation_ids")
        pending_ids = scope.get("pending_species_ids")
        if not isinstance(selected_ids, list) or not selected_ids:
            errors.append("job spec requires selected observation IDs")
            selected_ids = []
        if len(selected_ids) != len(set(map(str, selected_ids))):
            errors.append("job spec contains duplicate observation IDs")
        if not isinstance(pending_ids, list):
            errors.append("pending species IDs must be a list")
            pending_ids = []
        if list(pending_ids) != sorted(set(map(str, pending_ids))):
            errors.append("pending species IDs must be unique and sorted")
        if reconstruction_scope in {"species", "pending"} and not pending_ids:
            errors.append("species and pending scopes require pending species IDs")
        try:
            inputs = mushroom_rebuild_snapshot.resolved_input_paths(snapshot_dir, input_manifest)
            observations_payload = mushroom_rebuild_pipeline.load_json_object(
                inputs["observations"],
                "observations",
            )
            eligible_ids = mushroom_rebuild_pipeline.eligible_observation_ids(
                mushroom_rebuild_pipeline.observation_rows(observations_payload)
            )
            unknown_ids = [value for value in selected_ids if value not in eligible_ids]
            if unknown_ids:
                errors.append(f"job spec contains an ineligible observation: {unknown_ids[0]}")
            if reconstruction_scope == "all" and selected_ids != eligible_ids:
                errors.append("all scope does not contain the exact eligible observation set")
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"cannot validate job scope: {exc}")

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "mushroom_rebuild_job_spec_verification",
        "status": "valid" if not errors else "invalid",
        "job_id": job_spec.get("job_id"),
        "job_spec_id": job_spec.get("job_spec_id"),
        "snapshot_id": input_manifest.get("snapshot_id"),
        "errors": errors,
    }


def _artifact_kind(relative_path: str) -> str:
    suffix = Path(relative_path).suffix.lower()
    return {".json": "json", ".csv": "csv", ".md": "report"}.get(suffix, "file")


def _summary_count(payload: dict[str, Any], *path: str) -> int:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            raise ValueError(f"artifact summary is missing {'/'.join(path)}")
        value = value.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"artifact summary has invalid {'/'.join(path)}")
    return value


def derive_artifact_summary(output_dir: Path) -> dict[str, int]:
    root = output_dir.resolve()
    gis = _load_json_object(
        root / "mushroom_gis_observation_reconstruction.json",
        "GIS artifact",
    )
    weather = _load_json_object(
        root / "mushroom_observations_weather_features.json",
        "weather artifact",
    )
    features = _load_json_object(
        root / "mushroom_observation_features_v0.json",
        "features artifact",
    )
    model = _load_json_object(root / "mushroom_model_v0.json", "model artifact")
    return {
        "gis_observations": _summary_count(gis, "result_count"),
        "weather_observations": _summary_count(weather, "summary", "observations"),
        "feature_observations": _summary_count(features, "summary", "observations"),
        "model_species": _summary_count(model, "summary", "species"),
    }


def _job_snapshot_id(job_spec: dict[str, Any]) -> object:
    input_contract = job_spec.get("input")
    return input_contract.get("snapshot_id") if isinstance(input_contract, dict) else None


def create_result_manifest(
    job_spec: dict[str, Any],
    output_dir: Path,
    pipeline_result: dict[str, Any],
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    if pipeline_result.get("status") != "complete":
        raise ValueError("result manifest requires a complete pipeline result")
    root = output_dir.resolve()
    artifacts = []
    for relative in EXPECTED_ARTIFACT_PATHS:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"expected rebuild artifact not found: {relative}")
        if path.suffix.lower() == ".json":
            _load_json_object(path, "JSON artifact")
        artifacts.append(
            {
                "path": relative,
                "kind": _artifact_kind(relative),
                "size_bytes": path.stat().st_size,
                "sha256": mushroom_rebuild_snapshot.sha256_file(path),
            }
        )
    derived_summary = derive_artifact_summary(root)
    if pipeline_result.get("summary") != derived_summary:
        raise ValueError("pipeline summary does not match generated artifacts")
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": RESULT_MANIFEST_KIND,
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "job_id": job_spec.get("job_id"),
        "job_spec_id": job_spec.get("job_spec_id"),
        "snapshot_id": _job_snapshot_id(job_spec),
        "status": "complete",
        "summary": pipeline_result.get("summary", {}),
        "phase_durations_seconds": pipeline_result.get("phase_durations_seconds", {}),
        "duration_seconds": pipeline_result.get("duration_seconds"),
        "artifacts": artifacts,
    }
    payload["result_manifest_id"] = _canonical_hash(payload, "result_manifest_id")
    return payload


def verify_result_manifest(
    result_manifest: dict[str, Any],
    job_spec: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    errors = result_manifest_contract_errors(result_manifest, job_spec)

    raw_artifacts = result_manifest.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raw_artifacts = []
    root = output_dir.resolve()
    verified_artifacts = 0
    for raw_artifact in raw_artifacts:
        if not isinstance(raw_artifact, dict):
            continue
        relative = str(raw_artifact.get("path", ""))
        if relative not in EXPECTED_ARTIFACT_PATHS:
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"missing result artifact: {relative}")
            continue
        if path.stat().st_size != raw_artifact.get("size_bytes"):
            errors.append(f"result artifact size mismatch: {relative}")
            continue
        if mushroom_rebuild_snapshot.sha256_file(path) != raw_artifact.get("sha256"):
            errors.append(f"result artifact hash mismatch: {relative}")
            continue
        if raw_artifact.get("kind") != _artifact_kind(relative):
            errors.append(f"result artifact kind mismatch: {relative}")
            continue
        if path.suffix.lower() == ".json":
            try:
                _load_json_object(path, "JSON artifact")
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON result artifact {relative}: {exc}")
                continue
        verified_artifacts += 1
    try:
        derived_summary = derive_artifact_summary(root)
        if result_manifest.get("summary") != derived_summary:
            errors.append("result summary does not match generated artifacts")
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"cannot derive result summary: {exc}")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "mushroom_rebuild_result_manifest_verification",
        "status": "valid" if not errors else "invalid",
        "job_id": result_manifest.get("job_id"),
        "job_spec_id": result_manifest.get("job_spec_id"),
        "result_manifest_id": result_manifest.get("result_manifest_id"),
        "verified_artifacts": verified_artifacts,
        "errors": errors,
    }


def result_manifest_contract_errors(
    result_manifest: dict[str, Any],
    job_spec: dict[str, Any],
) -> list[str]:
    """Validate result identity and declared artifacts without reading their bytes."""
    errors: list[str] = []
    if result_manifest.get("kind") != RESULT_MANIFEST_KIND:
        errors.append("unexpected result manifest kind")
    if result_manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported result manifest schema")
    if result_manifest.get("result_manifest_id") != _canonical_hash(
        result_manifest,
        "result_manifest_id",
    ):
        errors.append("result manifest hash mismatch")
    if result_manifest.get("status") != "complete":
        errors.append("result manifest is not complete")
    for field, expected in (
        ("job_id", job_spec.get("job_id")),
        ("job_spec_id", job_spec.get("job_spec_id")),
        ("snapshot_id", _job_snapshot_id(job_spec)),
    ):
        if result_manifest.get(field) != expected:
            errors.append(f"result manifest {field} mismatch")

    raw_artifacts = result_manifest.get("artifacts")
    if not isinstance(raw_artifacts, list):
        errors.append("result artifacts must be a list")
        raw_artifacts = []
    artifact_paths = [item.get("path") for item in raw_artifacts if isinstance(item, dict)]
    if artifact_paths != list(EXPECTED_ARTIFACT_PATHS):
        errors.append("result artifact list does not match job contract")
    for raw_artifact in raw_artifacts:
        if not isinstance(raw_artifact, dict):
            errors.append("invalid result artifact record")
            continue
        relative = str(raw_artifact.get("path", ""))
        if relative not in EXPECTED_ARTIFACT_PATHS:
            continue
        size = raw_artifact.get("size_bytes")
        digest = raw_artifact.get("sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            errors.append(f"invalid result artifact size: {relative}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"invalid result artifact hash: {relative}")
        if raw_artifact.get("kind") != _artifact_kind(relative):
            errors.append(f"result artifact kind mismatch: {relative}")
    return errors
