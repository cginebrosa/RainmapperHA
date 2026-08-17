"""Verified transport and coordinator installation for V2--V6 runtime batches."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_runtime_trainer
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_worker_transport


RESULT_SCHEMA_VERSION = "1.0"
RESULT_KIND = "mushroom_ml_multiversion_result"
RESULT_MANIFEST_NAME = "multiversion_result.json"
MAX_RESULT_FILE_BYTES = 256 * 1024 * 1024
MAX_RESULT_BYTES = 2 * 1024 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_result_manifest(payload: object, *, job_id: str) -> dict[str, Any]:
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
    if payload.get("operational_candidate_trained") is not False:
        raise ValueError("Multiversion result must remain non-operational")
    return {
        **dict(payload),
        "batch_id": batch_id,
        "snapshot_id": snapshot_id,
        "files": files,
        **counts,
    }


def install_verified_result(
    *,
    result_manifest_path: Path,
    result_root: Path,
    registry_path: Path,
    models_root: Path,
    job_id: str,
) -> dict[str, Any]:
    result = validate_result_manifest(
        json.loads(result_manifest_path.read_text(encoding="utf-8")), job_id=job_id
    )
    for record in result["files"]:
        candidate = Path(result_root) / record["path"]
        if not candidate.is_file() or candidate.stat().st_size != record["size_bytes"] or sha256(candidate) != record["sha256"]:
            raise ValueError(f"Multiversion result integrity failed: {record['path']}")
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    root = Path(models_root).resolve()
    batches = root / "batches"
    batches.mkdir(parents=True, exist_ok=True)
    destination = batches / result["batch_id"]
    if destination.exists():
        raise FileExistsError(f"Multiversion batch already exists: {destination}")
    staging = Path(tempfile.mkdtemp(prefix=f".{result['batch_id']}.", suffix=".install", dir=batches))
    try:
        extracted = Path(result_root) / "batch"
        batch_manifest_path = extracted / "manifest.json"
        if not batch_manifest_path.is_file() or sha256(batch_manifest_path) != result["batch_manifest_sha256"]:
            raise ValueError("Multiversion batch manifest integrity check failed")
        batch_manifest = catalog.validate_batch_manifest(
            registry, json.loads(batch_manifest_path.read_text(encoding="utf-8"))
        )
        if batch_manifest["batch_id"] != result["batch_id"] or batch_manifest["snapshot_id"] != result["snapshot_id"]:
            raise ValueError("Multiversion batch identity does not match its result")
        quality_ref = batch_manifest.get("quality_catalog")
        if isinstance(quality_ref, Mapping):
            quality_path = extracted / Path(str(quality_ref["path"])).relative_to(
                Path("batches") / result["batch_id"]
            )
            if not quality_path.is_file() or sha256(quality_path) != quality_ref["sha256"]:
                raise ValueError("Multiversion quality catalog integrity failed")
        training_input_ref = batch_manifest.get("training_input_manifest")
        if isinstance(training_input_ref, Mapping):
            training_input_path = extracted / Path(
                str(training_input_ref["path"])
            ).relative_to(Path("batches") / result["batch_id"])
            if (
                not training_input_path.is_file()
                or sha256(training_input_path) != training_input_ref["sha256"]
            ):
                raise ValueError("Multiversion training input manifest integrity failed")
        for artifact in batch_manifest["artifacts"]:
            staged_path = extracted / Path(str(artifact["path"])).relative_to(
                Path("batches") / result["batch_id"]
            )
            if not staged_path.is_file() or mushroom_ml_runtime_trainer.sha256(staged_path) != artifact["sha256"]:
                raise ValueError(f"Multiversion artifact integrity failed: {artifact['path']}")
        shutil.copytree(extracted, staging / "batch")
        os.replace(staging / "batch", destination)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".runtime-batch.", suffix=".tmp", dir=root)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(batch_manifest, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, root / "runtime-batch.json")
        finally:
            Path(temporary_name).unlink(missing_ok=True)
        return {
            "status": "verified_and_installed",
            "batch_id": result["batch_id"],
            "snapshot_id": result["snapshot_id"],
            "planned_fit_count": result["planned_fit_count"],
            "successful_fit_count": result["successful_fit_count"],
            "failed_fit_count": result["failed_fit_count"],
            "artifact_count": len(batch_manifest["artifacts"]),
            "operational_candidate_trained": False,
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)


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
    return {"status": "staged", "path": path, "size_bytes": len(content)}


def finalize_result(
    result_root: Path,
    *,
    job_id: str,
    registry_path: Path,
    models_root: Path,
) -> dict[str, Any]:
    job_root = Path(result_root) / job_id / "multiversion"
    installed = install_verified_result(
        result_manifest_path=job_root / RESULT_MANIFEST_NAME,
        result_root=job_root,
        registry_path=registry_path,
        models_root=models_root,
        job_id=job_id,
    )
    shutil.rmtree(job_root)
    return installed
