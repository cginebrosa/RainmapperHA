"""Explicit, auditable promotion and rollback for complete ML versions."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_ml_multiversion_transport
from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_ml_runtime_inference
from rainmapper_core import mushroom_ml_training_freshness
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_rebuild_snapshot


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _write_json(path: Path, payload: object) -> None:
    _atomic_bytes(
        path,
        (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def _promotion_record_path(models_root: Path, promotion_id: str) -> Path:
    return Path(models_root) / "promotion-history" / promotion_id / "promotion.json"


def promote_candidate(
    *,
    models_root: Path,
    registry_path: Path,
    candidate_id: str,
    observations_path: Path,
    reference_catalogs_path: Path,
    gis_mappings_path: Path,
    weather_data_dir: Path,
    gis_root: Path,
    known_sites_path: Path,
    stations_path: Path,
    observation_features_path: Path,
    source_benchmark_batch_id: str = "",
) -> dict[str, Any]:
    """Promote a complete, fresh candidate after an explicit human action."""
    result, manifest, extracted, job_id = (
        mushroom_ml_multiversion_transport.verify_archived_candidate(
            models_root=models_root,
            registry_path=registry_path,
            candidate_id=candidate_id,
        )
    )
    training_ref = manifest.get("training_input_manifest")
    if not isinstance(training_ref, dict):
        raise ValueError("Candidate has no immutable training input identity")
    training_manifest = json.loads(
        (extracted / "training-input-manifest.json").read_text(encoding="utf-8")
    )
    freshness = mushroom_rebuild_snapshot.verify_live_inputs(
        training_manifest,
        observations_path=observations_path,
        reference_catalogs_path=reference_catalogs_path,
        gis_mappings_path=gis_mappings_path,
        weather_data_dir=weather_data_dir,
        gis_root=gis_root,
        extra_inputs={
            "registry.json": registry_path,
            "known-sites.json": known_sites_path,
            "stations.txt": stations_path,
            "observation-features.json": observation_features_path,
        },
        ignored_extra_inputs={"registry.json"},
        verify_weather_file_hashes=True,
    )
    if freshness.get("status") != "valid":
        raise ValueError("Candidate inputs changed; prepare a fresh candidate before promotion")

    version_ids = [str(value) for value in manifest.get("version_ids", [])]
    profile_keys = [str(value) for value in manifest.get("profile_keys", [])]
    if len(version_ids) != 1 or not profile_keys:
        raise ValueError("Candidate does not contain one complete operational version")
    version_id = version_ids[0]
    generation_ids = {
        str(row["artifact_ref"]["generation_id"])
        for row in manifest.get("artifacts", [])
        if isinstance(row, dict) and isinstance(row.get("artifact_ref"), dict)
    }
    if len(generation_ids) != 1:
        raise ValueError("Candidate artifacts do not share one generation identity")
    generation_id = next(iter(generation_ids))
    profile_ids = [key.split("/", 1)[1] for key in profile_keys]
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    for artifact in manifest.get("artifacts", []):
        artifact_ref = mushroom_ml_model_catalog.ModelArtifactRef.from_mapping(
            artifact["artifact_ref"]
        )
        horizons = artifact.get("supported_horizons") or []
        if not horizons:
            raise ValueError("Candidate artifact has no supported horizon")
        model_ref = mushroom_ml_model_catalog.ModelRef(
            **artifact_ref.as_dict(), horizon_days=int(horizons[0])
        )
        smoke_row = dict(artifact)
        smoke_row["path"] = str(
            Path(str(artifact["path"])).relative_to(
                Path("batches") / str(manifest["batch_id"])
            )
        )
        mushroom_ml_runtime_inference.load_exact_artifact(
            registry,
            manifest,
            model_ref,
            root=extracted,
            checked_manifest=manifest,
            artifact_row=smoke_row,
            validated_model_ref=model_ref,
        )
    if not any(
        generation.get("generation_id") == generation_id
        for version in registry["versions"]
        if version["version_id"] == version_id
        for generation in version.get("generations", [])
    ):
        registry = mushroom_ml_version_registry.append_generation(
            registry,
            version_id=version_id,
            generation={
                "generation_id": generation_id,
                "kind": "trained_model",
                "retention": "permanent",
                "profile_ids": profile_ids,
                "batch_id": result["batch_id"],
                "snapshot_id": result["snapshot_id"],
                "source_benchmark_batch_id": str(source_benchmark_batch_id or ""),
                "promotion_gate_status": "passed",
                "promotion_gate_kind": "technical_execution_only",
            },
        )
    promoted_registry = mushroom_ml_version_registry.transition_active_generation(
        registry,
        version_id,
        generation_id=generation_id,
    )

    models = Path(models_root)
    runtime_descriptor = models / "runtime-batch.json"
    previous_descriptor = runtime_descriptor.read_bytes() if runtime_descriptor.is_file() else None
    previous_registry = Path(registry_path).read_bytes()
    promotion_id = "promotion_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    record_path = _promotion_record_path(models, promotion_id)
    record_root = record_path.parent
    record_root.mkdir(parents=True, exist_ok=False)
    _atomic_bytes(record_root / "previous-registry.json", previous_registry)
    if previous_descriptor is not None:
        _atomic_bytes(record_root / "previous-runtime-batch.json", previous_descriptor)
    record = {
        "schema_version": "1.0",
        "kind": "mushroom_ml_version_promotion",
        "promotion_id": promotion_id,
        "status": "prepared",
        "candidate_id": candidate_id,
        "candidate_job_id": job_id,
        "batch_id": result["batch_id"],
        "version_id": version_id,
        "profile_ids": profile_ids,
        "generation_id": generation_id,
        "source_benchmark_batch_id": str(source_benchmark_batch_id or ""),
        "previous_target": registry["active_operational_target"],
        "created_at": datetime.now(UTC).isoformat(),
    }
    _write_json(record_path, record)
    installed = False
    try:
        archive_root = models / "candidates" / candidate_id
        installation = mushroom_ml_multiversion_transport.install_verified_result(
            result_manifest_path=archive_root / mushroom_ml_multiversion_transport.RESULT_MANIFEST_NAME,
            result_root=archive_root,
            registry_path=registry_path,
            models_root=models,
            job_id=job_id,
        )
        installed = True
        mushroom_ml_version_registry.save_registry(registry_path, promoted_registry)
    except BaseException:
        if installed:
            mushroom_ml_multiversion_transport.restore_runtime_batch(
                models_root=models,
                installed_batch_id=str(result["batch_id"]),
                previous_descriptor=previous_descriptor,
            )
        _atomic_bytes(Path(registry_path), previous_registry)
        record["status"] = "rolled_back_after_failure"
        _write_json(record_path, record)
        raise
    record.update(
        {
            "status": "active",
            "activated_at": datetime.now(UTC).isoformat(),
            "installation": installation,
        }
    )
    _write_json(record_path, record)
    mushroom_ml_training_freshness.clear_cache()
    return {**record, "runtime_changed": True, "rollback_available": True}


def rollback_promotion(
    *, models_root: Path,
    registry_path: Path,
    promotion_id: str,
) -> dict[str, Any]:
    """Restore the exact descriptor and registry saved by one active promotion."""
    record_path = _promotion_record_path(models_root, promotion_id)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("status") != "active":
        raise ValueError("Only the currently active promotion can be rolled back")
    current_registry = mushroom_ml_version_registry.load_registry(registry_path)
    if (
        current_registry["active_operational_target"].get("generation_id")
        != record.get("generation_id")
    ):
        raise ValueError("A later operational generation is active; rollback refused")
    runtime = json.loads(
        (Path(models_root) / "runtime-batch.json").read_text(encoding="utf-8")
    )
    if runtime.get("batch_id") != record.get("batch_id"):
        raise ValueError("Runtime batch changed after this promotion; rollback refused")
    record_root = record_path.parent
    previous_descriptor_path = record_root / "previous-runtime-batch.json"
    previous_descriptor = (
        previous_descriptor_path.read_bytes()
        if previous_descriptor_path.is_file()
        else None
    )
    mushroom_ml_multiversion_transport.restore_runtime_batch(
        models_root=models_root,
        installed_batch_id=str(record["batch_id"]),
        previous_descriptor=previous_descriptor,
    )
    _atomic_bytes(
        Path(registry_path), (record_root / "previous-registry.json").read_bytes()
    )
    record.update(
        {"status": "rolled_back", "rolled_back_at": datetime.now(UTC).isoformat()}
    )
    _write_json(record_path, record)
    mushroom_ml_training_freshness.clear_cache()
    return {**record, "runtime_changed": True}
