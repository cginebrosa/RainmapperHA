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
from rainmapper_core import mushroom_worker_transport


RESULT_SCHEMA_VERSION = "1.0"
RESULT_KIND = "mushroom_ml_multiversion_result"
RESULT_MANIFEST_NAME = "multiversion_result.json"
MAX_RESULT_FILE_BYTES = 256 * 1024 * 1024
MAX_RESULT_BYTES = 2 * 1024 * 1024 * 1024
JOB_PURPOSES = frozenset({"operational", "benchmark"})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    return {
        **dict(payload),
        "batch_id": batch_id,
        "snapshot_id": snapshot_id,
        "files": files,
        "job_purpose": purpose,
        "operational_candidate_trained": operational,
        "report_id": report_id,
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
    for key in ("planned_fit_count", "successful_fit_count", "failed_fit_count"):
        if int(batch_manifest.get(key, -1)) != int(result[key]):
            raise ValueError("Multiversion result and batch fit counts disagree")
    if expected_purpose == "operational":
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
        selected_version_ids = {
            row["version_id"] for row in selected_profiles
        }
        if len(selected_version_ids) != 1:
            raise ValueError("Operational batch must contain one complete version")
        selected_version_id = next(iter(selected_version_ids))
        required_profile_keys = {
            row["profile_key"]
            for row in mushroom_ml_version_registry.operational_profile_options(registry)
            if row["version_id"] == selected_version_id
        }
        if set(profile_keys) != required_profile_keys:
            raise ValueError("Operational batch omits profiles from its version")
        artifact_refs = [
            catalog.ModelArtifactRef.from_mapping(row["artifact_ref"])
            for row in batch_manifest["artifacts"]
        ]
        generation_ids = {
            ref.version_id: ref.generation_id for ref in artifact_refs
        }
        if (
            result["failed_fit_count"] != 0
            or set(generation_ids) != {selected_version_id}
        ):
            raise ValueError("Operational batch is incomplete or targets another version")
        expected_plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id=result["batch_id"],
            snapshot_id=result["snapshot_id"],
            generation_ids=generation_ids,
            species_ids=[str(value) for value in species_ids],
            version_ids=[selected_version_id],
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
    if expected_purpose == "benchmark":
        report_ref = batch_manifest.get("benchmark_report")
        predictions_ref = batch_manifest.get("holdout_predictions")
        if not isinstance(report_ref, Mapping) or not isinstance(predictions_ref, Mapping):
            raise ValueError("Benchmark batch does not contain its persistent report")
        report_path = extracted / mushroom_ml_benchmark_reports.REPORT_NAME
        predictions_path = extracted / mushroom_ml_benchmark_reports.PREDICTIONS_NAME
        if (
            report_ref.get("path")
            != f"batches/{result['batch_id']}/{mushroom_ml_benchmark_reports.REPORT_NAME}"
            or report_ref.get("report_id") != result["report_id"]
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
            report.get("report_id") != result["report_id"]
            or report.get("batch_id") != result["batch_id"]
            or report.get("snapshot_id") != result["snapshot_id"]
        ):
            raise ValueError("Benchmark report identity does not match its batch")
    for artifact in batch_manifest["artifacts"]:
        staged_path = extracted / Path(str(artifact["path"])).relative_to(
            Path("batches") / result["batch_id"]
        )
        if (
            not staged_path.is_file()
            or mushroom_ml_runtime_trainer.sha256(staged_path) != artifact["sha256"]
        ):
            raise ValueError(f"Multiversion artifact integrity failed: {artifact['path']}")
    return result, batch_manifest, extracted


def archive_verified_candidate(
    *,
    result_manifest_path: Path,
    result_root: Path,
    registry_path: Path,
    models_root: Path,
    job_id: str,
) -> dict[str, Any]:
    """Persist one verified operational candidate without changing runtime state."""
    result, batch_manifest, _ = _verified_result(
        result_manifest_path=result_manifest_path,
        result_root=result_root,
        registry_path=registry_path,
        job_id=job_id,
        expected_purpose="operational",
    )
    archive_root = Path(models_root).resolve() / "candidates"
    archive_root.mkdir(parents=True, exist_ok=True)
    destination = archive_root / result["batch_id"]
    if destination.exists():
        raise FileExistsError(f"Operational candidate already exists: {destination}")
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{result['batch_id']}.", suffix=".archive", dir=archive_root
        )
    )
    try:
        shutil.copytree(Path(result_root), staging / "candidate")
        os.replace(staging / "candidate", destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {
        "status": "verified_candidate_archived",
        "candidate_id": result["batch_id"],
        "batch_id": result["batch_id"],
        "snapshot_id": result["snapshot_id"],
        "version_id": str(batch_manifest["version_ids"][0]),
        "profile_keys": [str(value) for value in batch_manifest["profile_keys"]],
        "planned_fit_count": result["planned_fit_count"],
        "successful_fit_count": result["successful_fit_count"],
        "failed_fit_count": result["failed_fit_count"],
        "artifact_count": len(batch_manifest["artifacts"]),
        "archive": str(destination),
        "job_id": job_id,
        "runtime_changed": False,
    }


def archive_benchmark_as_candidate(
    *,
    models_root: Path,
    registry_path: Path,
    benchmark_batch_id: str,
    version_id: str,
    candidate_batch_id: str,
    job_id: str,
    progress: Callable[[int, str, str], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Repackage one complete benchmark version without fitting models again."""
    source_id = catalog._identifier(benchmark_batch_id, "benchmark_batch_id")
    target_batch_id = catalog._identifier(candidate_batch_id, "candidate_batch_id")
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    required_profiles = [
        row
        for row in mushroom_ml_version_registry.operational_profile_options(registry)
        if row["version_id"] == version_id
    ]
    if not required_profiles:
        raise ValueError("The selected version is not technically promotable")
    required_profile_keys = {row["profile_key"] for row in required_profiles}
    source_root = Path(models_root).resolve() / "benchmarks" / source_id
    source_manifest_path = source_root / "manifest.json"
    source_manifest = catalog.validate_batch_manifest(
        registry, json.loads(source_manifest_path.read_text(encoding="utf-8"))
    )
    if (
        source_manifest["batch_id"] != source_id
        or source_manifest.get("job_purpose") != "benchmark"
        or source_manifest.get("operational_candidate_trained") is not False
    ):
        raise ValueError("The source batch is not an archived scientific benchmark")
    report = mushroom_ml_benchmark_reports.load_report(models_root, source_id)
    report_profile_keys = {
        str(row.get("profile_key") or "")
        for row in (report.get("selection") or {}).get("profiles", [])
        if isinstance(row, Mapping)
    }
    if not required_profile_keys <= report_profile_keys:
        raise ValueError("The benchmark does not contain the complete operational version")
    if report.get("snapshot_id") != source_manifest["snapshot_id"]:
        raise ValueError("The benchmark report and model batch use different snapshots")

    quality_ref = source_manifest.get("quality_catalog")
    training_ref = source_manifest.get("training_input_manifest")
    if not isinstance(quality_ref, Mapping) or not isinstance(training_ref, Mapping):
        raise ValueError("The benchmark lacks quality or training-input evidence")
    quality_source = source_root / Path(str(quality_ref["path"])).relative_to(
        Path("batches") / source_id
    )
    training_source = source_root / Path(str(training_ref["path"])).relative_to(
        Path("batches") / source_id
    )
    if sha256(quality_source) != quality_ref["sha256"]:
        raise ValueError("The benchmark quality catalog failed integrity checks")
    if sha256(training_source) != training_ref["sha256"]:
        raise ValueError("The benchmark training inputs failed integrity checks")
    quality_payload = json.loads(quality_source.read_text(encoding="utf-8"))
    quality_profile_keys = {
        f"{row.get('version_id')}/{row.get('profile_id')}"
        for row in quality_payload.get("entries", [])
        if isinstance(row, Mapping)
    }
    if not required_profile_keys <= quality_profile_keys:
        raise ValueError("The benchmark quality catalog does not cover the complete version")

    source_artifacts = [
        row
        for row in source_manifest["artifacts"]
        if str((row.get("artifact_ref") or {}).get("version_id") or "") == version_id
        and f"{version_id}/{(row.get('artifact_ref') or {}).get('profile_id')}"
        in required_profile_keys
    ]
    if not source_artifacts:
        raise ValueError("The benchmark contains no reusable artifacts for this version")
    generation_id = f"{version_id}_{target_batch_id}"

    def logical_key(raw_ref: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
        return (
            str(raw_ref.get("version_id") or ""),
            str(raw_ref.get("temporal_contract_id") or ""),
            str(raw_ref.get("profile_id") or ""),
            str(raw_ref.get("estimator_id") or ""),
            str(raw_ref.get("species_id") or ""),
        )

    durations = {
        logical_key(row.get("artifact_ref") or {}): float(row.get("duration_seconds", 0) or 0)
        for row in source_manifest.get("fit_results", [])
        if isinstance(row, Mapping)
        and isinstance(row.get("artifact_ref"), Mapping)
        and row.get("status") == "complete"
    }
    if progress is not None:
        progress(10, "Verifying benchmark artifacts", f"Checking {len(source_artifacts)} archived fits.")
    with tempfile.TemporaryDirectory(prefix=f".{target_batch_id}.") as temporary:
        result_root = Path(temporary)
        batch_root = result_root / "batch"
        batch_root.mkdir()
        candidate_artifacts: list[dict[str, Any]] = []
        fit_results: list[dict[str, Any]] = []
        for index, source_artifact in enumerate(source_artifacts, start=1):
            if cancel_requested is not None and cancel_requested():
                raise InterruptedError("Candidate preparation was cancelled")
            source_ref = catalog.ModelArtifactRef.from_mapping(
                source_artifact["artifact_ref"]
            )
            source_path = source_root / Path(str(source_artifact["path"])).relative_to(
                Path("batches") / source_id
            )
            if not source_path.is_file() or sha256(source_path) != source_artifact["sha256"]:
                raise ValueError(f"Benchmark artifact integrity failed: {source_artifact['path']}")
            bundle = joblib.load(source_path)
            if not isinstance(bundle, dict) or bundle.get("artifact_ref") != source_ref.as_dict():
                raise ValueError(f"Benchmark artifact identity failed: {source_artifact['path']}")
            candidate_ref = catalog.ModelArtifactRef(
                batch_id=target_batch_id,
                generation_id=generation_id,
                version_id=source_ref.version_id,
                temporal_contract_id=source_ref.temporal_contract_id,
                profile_id=source_ref.profile_id,
                estimator_id=source_ref.estimator_id,
                species_id=source_ref.species_id,
            )
            bundle["artifact_ref"] = candidate_ref.as_dict()
            relative = catalog.model_relative_path(candidate_ref).relative_to(
                Path("batches") / target_batch_id
            )
            destination = batch_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(bundle, destination)
            candidate_artifacts.append(
                {
                    "artifact_ref": candidate_ref.as_dict(),
                    "supported_horizons": list(source_artifact["supported_horizons"]),
                    "path": catalog.model_relative_path(candidate_ref).as_posix(),
                    "sha256": sha256(destination),
                }
            )
            fit_results.append(
                {
                    "artifact_ref": candidate_ref.as_dict(),
                    "status": "complete",
                    "duration_seconds": durations.get(logical_key(source_ref.as_dict()), 0.0),
                    "reused_from_benchmark": source_id,
                }
            )
            if progress is not None and (index == len(source_artifacts) or index % 10 == 0):
                progress(
                    10 + int(75 * index / len(source_artifacts)),
                    "Reusing benchmark artifacts",
                    f"Verified and repackaged {index}/{len(source_artifacts)} fits.",
                )

        quality_destination = batch_root / "quality-catalog.json"
        training_destination = batch_root / "training-input-manifest.json"
        shutil.copyfile(quality_source, quality_destination)
        shutil.copyfile(training_source, training_destination)
        candidate_manifest = {
            key: value
            for key, value in source_manifest.items()
            if key
            not in {
                "artifacts",
                "benchmark_report",
                "holdout_predictions",
                "quality_catalog",
                "training_input_manifest",
                "fit_results",
                "failed_fits",
            }
        }
        candidate_manifest.update(
            {
                "batch_id": target_batch_id,
                "snapshot_id": source_manifest["snapshot_id"],
                "version_ids": [version_id],
                "profile_keys": sorted(required_profile_keys),
                "artifacts": candidate_artifacts,
                "planned_fit_count": len(candidate_artifacts),
                "successful_fit_count": len(candidate_artifacts),
                "failed_fit_count": 0,
                "fit_results": fit_results,
                "failed_fits": [],
                "active": False,
                "job_purpose": "operational",
                "operational_candidate_trained": True,
                "quality_catalog": {
                    "path": f"batches/{target_batch_id}/quality-catalog.json",
                    "sha256": sha256(quality_destination),
                },
                "training_input_manifest": {
                    "path": f"batches/{target_batch_id}/training-input-manifest.json",
                    "sha256": sha256(training_destination),
                },
                "source_benchmark_batch_id": source_id,
                "artifact_preparation": "verified_benchmark_reuse",
            }
        )
        manifest_path = batch_root / "manifest.json"
        manifest_path.write_text(
            json.dumps(candidate_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result_files = [
            {
                "path": path.relative_to(result_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(batch_root.rglob("*"))
            if path.is_file()
        ]
        result_payload = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "kind": RESULT_KIND,
            "job_id": job_id,
            "batch_id": target_batch_id,
            "snapshot_id": source_manifest["snapshot_id"],
            "files": result_files,
            "batch_manifest_sha256": sha256(manifest_path),
            "planned_fit_count": len(candidate_artifacts),
            "successful_fit_count": len(candidate_artifacts),
            "failed_fit_count": 0,
            "job_purpose": "operational",
            "report_id": "",
            "operational_candidate_trained": True,
        }
        result_manifest_path = result_root / RESULT_MANIFEST_NAME
        result_manifest_path.write_text(
            json.dumps(result_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        archived = archive_verified_candidate(
            result_manifest_path=result_manifest_path,
            result_root=result_root,
            registry_path=registry_path,
            models_root=models_root,
            job_id=job_id,
        )
    if progress is not None:
        progress(100, "Operational candidate ready", "Benchmark artifacts were reused without retraining.")
    return {
        **archived,
        "source_benchmark_batch_id": source_id,
        "artifact_preparation": "verified_benchmark_reuse",
        "reused_artifact_count": len(source_artifacts),
    }


def verify_archived_candidate(
    *,
    models_root: Path,
    registry_path: Path,
    candidate_id: str,
) -> tuple[dict[str, Any], dict[str, Any], Path, str]:
    """Revalidate an archived candidate before an explicit human promotion."""
    resolved_id = catalog._identifier(candidate_id, "candidate_id")
    root = Path(models_root).resolve() / "candidates" / resolved_id
    raw = json.loads((root / RESULT_MANIFEST_NAME).read_text(encoding="utf-8"))
    job_id = str(raw.get("job_id") or "")
    result, manifest, extracted = _verified_result(
        result_manifest_path=root / RESULT_MANIFEST_NAME,
        result_root=root,
        registry_path=registry_path,
        job_id=job_id,
        expected_purpose="operational",
    )
    return result, manifest, extracted, job_id


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
            "job_purpose": "operational",
            "operational_candidate_trained": True,
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
        os.replace(staging / "batch", destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    report = mushroom_ml_benchmark_reports.load_report(
        Path(models_root), result["batch_id"]
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


def restore_runtime_batch(
    *,
    models_root: Path,
    installed_batch_id: str,
    previous_descriptor: bytes | None,
) -> None:
    root = Path(models_root)
    destination = root / "batches" / installed_batch_id
    if destination.is_dir():
        shutil.rmtree(destination)
    descriptor = root / "runtime-batch.json"
    if previous_descriptor is None:
        descriptor.unlink(missing_ok=True)
        return
    handle, temporary_name = tempfile.mkstemp(
        prefix=".runtime-batch.rollback.", suffix=".tmp", dir=root
    )
    try:
        with os.fdopen(handle, "wb") as temporary:
            temporary.write(previous_descriptor)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, descriptor)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def discard_staged_result(result_root: Path, *, job_id: str) -> None:
    shutil.rmtree(Path(result_root) / job_id / "multiversion", ignore_errors=True)
