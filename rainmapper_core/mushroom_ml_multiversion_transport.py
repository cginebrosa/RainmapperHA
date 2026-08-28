"""Verified transport and coordinator installation for V2--V6 runtime batches."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

import joblib

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_runtime_trainer
from rainmapper_core import mushroom_ml_benchmark_reports
from rainmapper_core import mushroom_ml_multiversion_plan
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_performance_telemetry
from rainmapper_core import mushroom_worker_transport


RESULT_SCHEMA_VERSION = "1.0"
RESULT_KIND = "mushroom_ml_multiversion_result"
RESULT_MANIFEST_NAME = "multiversion_result.json"
MAX_RESULT_FILE_BYTES = 256 * 1024 * 1024
MAX_RESULT_BYTES = 2 * 1024 * 1024 * 1024
JOB_PURPOSES = frozenset({"operational", "benchmark"})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
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


def _record_tree_copy(source: Path) -> None:
    files = [path for path in source.rglob("*") if path.is_file()]
    size = sum(path.stat().st_size for path in files)
    mushroom_performance_telemetry.add(
        copies=len(files),
        copy_bytes=size,
        files_read=len(files),
        bytes_read=size,
        files_written=len(files),
        bytes_written=size,
    )


def validate_result_manifest(
    payload: object,
    *,
    job_id: str,
    expected_purpose: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("Multiversion result manifest must be an object")
    if payload.get("schema_version") != RESULT_SCHEMA_VERSION or payload.get("kind") != RESULT_KIND:
        raise ValueError("Multiversion result manifest contract is invalid")
    if payload.get("job_id") != job_id:
        raise ValueError("Multiversion result belongs to another job")
    batch_id = catalog._identifier(payload.get("batch_id"), "batch_id")
    snapshot_id = str(payload.get("snapshot_id") or "")
    if not snapshot_id.startswith("sha256:") or len(snapshot_id) != 71:
        raise ValueError("Multiversion snapshot identity is invalid")
    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("Multiversion result files are missing")
    files: list[dict[str, Any]] = []
    total_bytes = 0
    seen: set[str] = set()
    for raw in raw_files:
        if not isinstance(raw, Mapping):
            raise ValueError("Multiversion result file declaration is invalid")
        path = safe_input_path(raw.get("path"))
        if not path.startswith("batch/") or path in seen:
            raise ValueError("Multiversion result file path is invalid")
        size_bytes = int(raw.get("size_bytes", -1))
        digest = str(raw.get("sha256") or "")
        if size_bytes < 0 or size_bytes > MAX_RESULT_FILE_BYTES or len(digest) != 64:
            raise ValueError("Multiversion result file metadata is invalid")
        seen.add(path)
        total_bytes += size_bytes
        files.append({"path": path, "size_bytes": size_bytes, "sha256": digest})
    if total_bytes > MAX_RESULT_BYTES or "batch/manifest.json" not in seen:
        raise ValueError("Multiversion result bundle is invalid")
    manifest_digest = str(payload.get("batch_manifest_sha256") or "")
    if len(manifest_digest) != 64:
        raise ValueError("Multiversion batch manifest digest is invalid")
    counts: dict[str, int] = {}
    for key in ("planned_fit_count", "successful_fit_count", "failed_fit_count"):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Multiversion {key} is invalid")
        counts[key] = value
    if counts["successful_fit_count"] + counts["failed_fit_count"] != counts["planned_fit_count"]:
        raise ValueError("Multiversion fit counts are inconsistent")
    operational = payload.get("operational_candidate_trained") is True
    purpose = str(payload.get("job_purpose") or ("operational" if operational else "benchmark"))
    if purpose not in JOB_PURPOSES:
        raise ValueError("Multiversion job purpose is invalid")
    if operational != (purpose == "operational"):
        raise ValueError("Multiversion purpose and operational flag disagree")
    if expected_purpose is not None and purpose != expected_purpose:
        raise ValueError("Multiversion result has the wrong job purpose")
    report_id = str(payload.get("report_id") or "")
    if purpose == "benchmark" and not re.fullmatch(r"sha256:[0-9a-f]{64}", report_id):
        raise ValueError("Benchmark result report identity is invalid")
    if purpose == "operational" and report_id:
        raise ValueError("Operational result cannot declare a benchmark report")
    operational_scope_id = str(payload.get("operational_scope_id") or "")
    operational_plan_id = str(payload.get("operational_plan_id") or "")
    if purpose == "operational" and (
        not re.fullmatch(r"sha256:[0-9a-f]{64}", operational_scope_id)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", operational_plan_id)
    ):
        raise ValueError("Operational result does not declare sealed scope and plan identities")
    if purpose == "benchmark" and (operational_scope_id or operational_plan_id):
        raise ValueError("Benchmark result cannot declare an operational plan")
    return {
        **dict(payload),
        "batch_id": batch_id,
        "snapshot_id": snapshot_id,
        "files": files,
        "job_purpose": purpose,
        "operational_candidate_trained": operational,
        "report_id": report_id,
        "operational_scope_id": operational_scope_id,
        "operational_plan_id": operational_plan_id,
        **counts,
    }


def _verified_result(
    *,
    result_manifest_path: Path,
    result_root: Path,
    registry_path: Path,
    job_id: str,
    expected_purpose: str,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    result = validate_result_manifest(
        json.loads(result_manifest_path.read_text(encoding="utf-8")),
        job_id=job_id,
        expected_purpose=expected_purpose,
    )
    for record in result["files"]:
        candidate = Path(result_root) / record["path"]
        if (
            not candidate.is_file()
            or candidate.stat().st_size != record["size_bytes"]
            or sha256(candidate) != record["sha256"]
        ):
            raise ValueError(f"Multiversion result integrity failed: {record['path']}")
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    extracted = Path(result_root) / "batch"
    batch_manifest_path = extracted / "manifest.json"
    if (
        not batch_manifest_path.is_file()
        or sha256(batch_manifest_path) != result["batch_manifest_sha256"]
    ):
        raise ValueError("Multiversion batch manifest integrity check failed")
    batch_manifest = catalog.validate_batch_manifest(
        registry, json.loads(batch_manifest_path.read_text(encoding="utf-8"))
    )
    if (
        batch_manifest["batch_id"] != result["batch_id"]
        or batch_manifest["snapshot_id"] != result["snapshot_id"]
        or str(batch_manifest.get("job_purpose") or expected_purpose) != expected_purpose
        or bool(batch_manifest.get("operational_candidate_trained"))
        != (expected_purpose == "operational")
    ):
        raise ValueError("Multiversion batch identity does not match its result")
    if expected_purpose == "operational" and (
        batch_manifest.get("operational_scope_id") != result["operational_scope_id"]
        or batch_manifest.get("operational_plan_id") != result["operational_plan_id"]
    ):
        raise ValueError("Operational batch scope or plan does not match its result")
    for key in ("planned_fit_count", "successful_fit_count", "failed_fit_count"):
        if int(batch_manifest.get(key, -1)) != int(result[key]):
            raise ValueError("Multiversion result and batch fit counts disagree")
    if expected_purpose == "operational":
        mushroom_ml_version_registry.validate_revision_vector(
            batch_manifest.get("input_revisions")
        )
        species_ids = batch_manifest.get("species_ids")
        if not isinstance(species_ids, list) or not species_ids:
            raise ValueError("Operational batch does not declare its species scope")
        profile_keys = batch_manifest.get("profile_keys")
        if not isinstance(profile_keys, list) or not profile_keys:
            raise ValueError("Operational batch must declare its profile scope")
        selected_profiles = [
            mushroom_ml_version_registry.resolve_operational_profile(
                registry, str(profile_key)
            )
            for profile_key in profile_keys
        ]
        selected_version_ids = list(
            dict.fromkeys(row["version_id"] for row in selected_profiles)
        )
        for selected_version_id in selected_version_ids:
            required_profile_keys = {
                row["profile_key"]
                for row in mushroom_ml_version_registry.operational_profile_options(registry)
                if row["version_id"] == selected_version_id
            }
            if set(profile_keys) & required_profile_keys != required_profile_keys:
                raise ValueError(
                    f"Operational batch omits profiles from {selected_version_id}"
                )
        artifact_refs = [
            catalog.ModelArtifactRef.from_mapping(row["artifact_ref"])
            for row in batch_manifest["artifacts"]
        ]
        generation_ids = {
            ref.version_id: ref.generation_id for ref in artifact_refs
        }
        if (
            result["failed_fit_count"] != 0
            or set(generation_ids) != set(selected_version_ids)
        ):
            raise ValueError("Operational batch is incomplete or targets another version")
        expected_plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id=result["batch_id"],
            snapshot_id=result["snapshot_id"],
            generation_ids=generation_ids,
            species_ids=[str(value) for value in species_ids],
            version_ids=selected_version_ids,
            profile_keys=[str(value) for value in profile_keys],
        )
        expected_refs = {
            catalog.ModelArtifactRef.from_mapping(row["artifact_ref"]).key
            for row in expected_plan["fits"]
        }
        actual_refs = {ref.key for ref in artifact_refs}
        if expected_refs != actual_refs or len(actual_refs) != result["planned_fit_count"]:
            raise ValueError("Operational batch does not contain every required artifact")
    quality_ref = batch_manifest.get("quality_catalog")
    if isinstance(quality_ref, Mapping):
        quality_path = extracted / Path(str(quality_ref["path"])).relative_to(
            Path("batches") / result["batch_id"]
        )
        if not quality_path.is_file() or sha256(quality_path) != quality_ref["sha256"]:
            raise ValueError("Multiversion quality catalog integrity failed")
    elif expected_purpose in {"operational", "benchmark"}:
        raise ValueError(
            f"{expected_purpose.capitalize()} batch has no synchronized hold-out quality catalog"
        )
    training_input_ref = batch_manifest.get("training_input_manifest")
    if isinstance(training_input_ref, Mapping):
        training_input_path = extracted / Path(str(training_input_ref["path"])).relative_to(
            Path("batches") / result["batch_id"]
        )
        if (
            not training_input_path.is_file()
            or sha256(training_input_path) != training_input_ref["sha256"]
        ):
            raise ValueError("Multiversion training input manifest integrity failed")
    elif expected_purpose in {"operational", "benchmark"}:
        raise ValueError(
            f"{expected_purpose.capitalize()} batch has no training input identity"
        )
    report_ref = batch_manifest.get("benchmark_report")
    predictions_ref = batch_manifest.get("holdout_predictions")
    if expected_purpose == "benchmark" or (
        isinstance(report_ref, Mapping) and isinstance(predictions_ref, Mapping)
    ):
        if not isinstance(report_ref, Mapping) or not isinstance(predictions_ref, Mapping):
            raise ValueError("Training batch does not contain synchronized hold-out evidence")
        report_path = extracted / mushroom_ml_benchmark_reports.REPORT_NAME
        predictions_path = extracted / mushroom_ml_benchmark_reports.PREDICTIONS_NAME
        if (
            report_ref.get("path")
            != f"batches/{result['batch_id']}/{mushroom_ml_benchmark_reports.REPORT_NAME}"
            or (
                expected_purpose == "benchmark"
                and report_ref.get("report_id") != result["report_id"]
            )
            or not report_path.is_file()
            or sha256(report_path) != report_ref.get("sha256")
            or predictions_ref.get("path")
            != f"batches/{result['batch_id']}/{mushroom_ml_benchmark_reports.PREDICTIONS_NAME}"
            or not predictions_path.is_file()
            or sha256(predictions_path) != predictions_ref.get("sha256")
        ):
            raise ValueError("Benchmark report artifacts failed integrity checks")
        report = mushroom_ml_benchmark_reports.validate_report(
            json.loads(report_path.read_text(encoding="utf-8")),
            root=extracted,
        )
        if (
            report.get("batch_id") != result["batch_id"]
            or report.get("snapshot_id") != result["snapshot_id"]
        ):
            raise ValueError("Benchmark report identity does not match its batch")
    for artifact in batch_manifest["artifacts"]:
        staged_path = extracted / Path(str(artifact["path"])).relative_to(
            Path("batches") / result["batch_id"]
        )
        if (
            not staged_path.is_file()
            or sha256(staged_path) != artifact["sha256"]
        ):
            raise ValueError(f"Multiversion artifact integrity failed: {artifact['path']}")
    return result, batch_manifest, extracted


def install_verified_result(
    *,
    result_manifest_path: Path,
    result_root: Path,
    registry_path: Path,
    models_root: Path,
    job_id: str,
) -> dict[str, Any]:
    result, batch_manifest, extracted = _verified_result(
        result_manifest_path=result_manifest_path,
        result_root=result_root,
        registry_path=registry_path,
        job_id=job_id,
        expected_purpose="operational",
    )
    root = Path(models_root).resolve()
    batches = root / "batches"
    batches.mkdir(parents=True, exist_ok=True)
    destination = batches / result["batch_id"]
    if destination.exists():
        raise FileExistsError(f"Multiversion batch already exists: {destination}")
    staging = Path(tempfile.mkdtemp(prefix=f".{result['batch_id']}.", suffix=".install", dir=batches))
    try:
        shutil.copytree(extracted, staging / "batch")
        _record_tree_copy(extracted)
        os.replace(staging / "batch", destination)
        return {
            "status": "verified_batch_installed",
            "batch_id": result["batch_id"],
            "snapshot_id": result["snapshot_id"],
            "planned_fit_count": result["planned_fit_count"],
            "successful_fit_count": result["successful_fit_count"],
            "failed_fit_count": result["failed_fit_count"],
            "artifact_count": len(batch_manifest["artifacts"]),
            "job_purpose": "operational",
            "operational_candidate_trained": True,
            "version_ids": [str(value) for value in batch_manifest.get("version_ids", [])],
            "generation_ids": {
                str(row["artifact_ref"]["version_id"]): str(
                    row["artifact_ref"]["generation_id"]
                )
                for row in batch_manifest["artifacts"]
            },
            "profile_keys": [str(value) for value in batch_manifest.get("profile_keys", [])],
            "input_revisions": batch_manifest.get("input_revisions"),
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def verify_installed_batch(
    *,
    models_root: Path,
    registry_path: Path,
    batch_id: str,
) -> dict[str, Any]:
    """Revalidate hashes and minimally load every artifact from an installed batch."""
    resolved_id = catalog._identifier(batch_id, "batch_id")
    root = Path(models_root).resolve()
    batch_root = root / "batches" / resolved_id
    if batch_root.is_symlink() or not batch_root.is_dir():
        raise ValueError("Installed multiversion batch is not a safe directory")
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    manifest = catalog.validate_batch_manifest(
        registry,
        json.loads((batch_root / "manifest.json").read_text(encoding="utf-8")),
    )
    if manifest["batch_id"] != resolved_id:
        raise ValueError("Installed multiversion batch identity changed")
    loaded = 0
    for artifact in manifest["artifacts"]:
        artifact_ref = catalog.ModelArtifactRef.from_mapping(artifact["artifact_ref"])
        artifact_path = root / artifact["path"]
        if (
            artifact_path.is_symlink()
            or not artifact_path.is_file()
            or sha256(artifact_path) != artifact["sha256"]
        ):
            raise ValueError(f"Installed multiversion artifact failed integrity: {artifact['path']}")
        bundle = joblib.load(artifact_path)
        if not isinstance(bundle, dict) or bundle.get("artifact_ref") != artifact_ref.as_dict():
            raise ValueError(f"Installed multiversion artifact failed identity: {artifact['path']}")
        loaded += 1
    return {
        "status": "verified_installed_batch",
        "batch_id": resolved_id,
        "artifact_count": loaded,
        "version_ids": [str(value) for value in manifest.get("version_ids", [])],
    }


def safe_input_path(value: object) -> str:
    return mushroom_worker_transport.safe_relative_path(str(value or "")).as_posix()


def receive_result_file(
    result_root: Path,
    *,
    job_id: str,
    logical_path: str,
    content: bytes,
) -> dict[str, Any]:
    """Stage one declared result file without trusting worker paths."""
    mushroom_worker_transport.validate_job_id(job_id)
    path = safe_input_path(logical_path)
    job_root = Path(result_root) / job_id / "multiversion"
    job_root.mkdir(parents=True, exist_ok=True)
    if path == RESULT_MANIFEST_NAME:
        manifest = validate_result_manifest(json.loads(content.decode("utf-8")), job_id=job_id)
    else:
        manifest_path = job_root / RESULT_MANIFEST_NAME
        manifest = validate_result_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8")), job_id=job_id
        )
        declaration = next((row for row in manifest["files"] if row["path"] == path), None)
        if declaration is None:
            raise ValueError("Multiversion result file was not declared")
        mushroom_performance_telemetry.add(hashes=1, hash_bytes=len(content))
        if len(content) != declaration["size_bytes"] or hashlib.sha256(content).hexdigest() != declaration["sha256"]:
            raise ValueError("Multiversion uploaded file integrity failed")
    destination = job_root / path
    if destination.exists():
        raise FileExistsError(f"Multiversion result file already exists: {path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    mushroom_performance_telemetry.add(
        files_written=1,
        bytes_written=len(content),
        fsyncs=1,
    )
    return {"status": "staged", "path": path, "size_bytes": len(content)}


def finalize_result(
    result_root: Path,
    *,
    job_id: str,
    registry_path: Path,
    models_root: Path,
    job_purpose: str,
) -> dict[str, Any]:
    job_root = Path(result_root) / job_id / "multiversion"
    purpose = str(job_purpose or "")
    result, batch_manifest, extracted = _verified_result(
        result_manifest_path=job_root / RESULT_MANIFEST_NAME,
        result_root=job_root,
        registry_path=registry_path,
        job_id=job_id,
        expected_purpose=purpose,
    )
    verification = {
        "status": "verified",
        "batch_id": result["batch_id"],
        "snapshot_id": result["snapshot_id"],
        "planned_fit_count": result["planned_fit_count"],
        "successful_fit_count": result["successful_fit_count"],
        "failed_fit_count": result["failed_fit_count"],
        "artifact_count": len(batch_manifest["artifacts"]),
        "job_purpose": purpose,
        "operational_candidate_trained": purpose == "operational",
        "operational_scope_id": result["operational_scope_id"],
        "operational_plan_id": result["operational_plan_id"],
    }
    if purpose == "operational":
        return verification
    archived = archive_verified_result(
        result_manifest_path=job_root / RESULT_MANIFEST_NAME,
        result_root=job_root,
        registry_path=registry_path,
        models_root=models_root,
        job_id=job_id,
    )
    shutil.rmtree(job_root)
    return archived


def archive_verified_result(
    *,
    result_manifest_path: Path,
    result_root: Path,
    registry_path: Path,
    models_root: Path,
    job_id: str,
) -> dict[str, Any]:
    result, batch_manifest, extracted = _verified_result(
        result_manifest_path=result_manifest_path,
        result_root=result_root,
        registry_path=registry_path,
        job_id=job_id,
        expected_purpose="benchmark",
    )
    archive_root = Path(models_root).resolve() / "benchmarks"
    archive_root.mkdir(parents=True, exist_ok=True)
    destination = archive_root / result["batch_id"]
    if destination.exists():
        raise FileExistsError(f"Benchmark batch already exists: {destination}")
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{result['batch_id']}.", suffix=".archive", dir=archive_root
        )
    )
    try:
        shutil.copytree(extracted, staging / "batch")
        _record_tree_copy(extracted)
        os.replace(staging / "batch", destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    report = mushroom_ml_benchmark_reports.load_report(
        Path(models_root), result["batch_id"]
    )
    evidence_plan = mushroom_ml_benchmark_reports.benchmark_evidence_plan(
        Path(models_root), result["batch_id"]
    )
    evidence = mushroom_ml_benchmark_reports.compact_benchmark_to_evidence(
        Path(models_root), result["batch_id"], plan=evidence_plan
    )
    return {
        "status": "verified_and_archived",
        "batch_id": result["batch_id"],
        "snapshot_id": result["snapshot_id"],
        "planned_fit_count": result["planned_fit_count"],
        "successful_fit_count": result["successful_fit_count"],
        "failed_fit_count": result["failed_fit_count"],
        "artifact_count": len(batch_manifest["artifacts"]),
        "job_purpose": "benchmark",
        "operational_candidate_trained": False,
        "archive": str(destination),
        "report_id": result["report_id"],
        "benchmark_report_available": True,
        "storage_state": evidence["status"],
        "summary": dict(report.get("summary") or {}),
        "selection": dict(report.get("selection") or {}),
    }


def install_staged_operational_result(
    result_root: Path,
    *,
    job_id: str,
    registry_path: Path,
    models_root: Path,
) -> dict[str, Any]:
    job_root = Path(result_root) / job_id / "multiversion"
    return install_verified_result(
        result_manifest_path=job_root / RESULT_MANIFEST_NAME,
        result_root=job_root,
        registry_path=registry_path,
        models_root=models_root,
        job_id=job_id,
    )


def remove_installed_batch(*, models_root: Path, batch_id: str) -> None:
    """Remove one reconstructible batch after its version slots were restored."""
    root = Path(models_root)
    destination = root / "batches" / batch_id
    if destination.is_dir():
        shutil.rmtree(destination)


def discard_staged_result(result_root: Path, *, job_id: str) -> None:
    shutil.rmtree(Path(result_root) / job_id / "multiversion", ignore_errors=True)
