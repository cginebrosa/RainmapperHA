"""Complete mushroom-model regeneration executed inside a local HA container.

This module deliberately reuses the external-worker contracts.  It is an
execution adapter for the local development stack, not a second production
pipeline: reconstruction and both training stages are built from immutable
snapshots, verified, and only then promoted.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from rainmapper_core import mushroom_ml_multiversion_transport
from rainmapper_core import mushroom_ml_multiversion_plan
from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_performance_telemetry
from rainmapper_core import mushroom_ml_runtime_trainer
from rainmapper_core import mushroom_ml_training_freshness
from rainmapper_core import mushroom_ml_tuning_catalog
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_operational_training_scope
from rainmapper_core import mushroom_rebuild_contracts
from rainmapper_core import mushroom_rebuild_pipeline
from rainmapper_core import mushroom_rebuild_snapshot
from rainmapper_core import mushroom_worker_results
from rainmapper_core import mushroom_worker_transport


ProgressCallback = Callable[[int, str, str], None]
ProgressEventMapper = Callable[[dict[str, object]], tuple[int, str, str]]
TelemetryEventMapper = Callable[[dict[str, object]], str | None]
CancelCallback = Callable[[], bool]
PreSnapshotCallback = Callable[[], dict[str, object]]


class LocalBenchmarkCancelled(RuntimeError):
    """Raised after a local benchmark subprocess reaches a cancellable point."""


@dataclass(frozen=True)
class LocalFullUpdatePaths:
    observations: Path
    reference_catalogs: Path
    gis_mappings: Path
    weather_data_dir: Path
    gis_root: Path
    known_sites: Path
    stations: Path
    registry: Path
    mushroom_data_dir: Path
    ml_models_dir: Path
    ml_report: Path
    bundle_root: Path
    candidate_results_root: Path
    work_root: Path
    scripts_dir: Path = Path("/app/scripts")


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


def _read_bytes(path: Path) -> bytes:
    content = path.read_bytes()
    mushroom_performance_telemetry.add(files_read=1, bytes_read=len(content))
    return content


def _read_progress_lines(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    mushroom_performance_telemetry.add(
        files_read=1,
        bytes_read=len(content.encode("utf-8")),
    )
    return content.splitlines()


def _paths_overlap(first: Path, second: Path) -> bool:
    left = first.resolve()
    right = second.resolve()
    return left == right or left in right.parents or right in left.parents


def _validate_isolated_work_root(paths: LocalFullUpdatePaths) -> None:
    protected_paths = {
        "live mushroom data": paths.mushroom_data_dir,
        "observations": paths.observations,
        "reference catalogs": paths.reference_catalogs,
        "GIS mappings": paths.gis_mappings,
        "weather data": paths.weather_data_dir,
        "GIS dataset": paths.gis_root,
        "known sites": paths.known_sites,
        "stations": paths.stations,
        "version registry": paths.registry,
    }
    for label, protected in protected_paths.items():
        if _paths_overlap(paths.work_root, protected):
            raise ValueError(
                f"Local full-update work root must not overlap {label}: {protected.resolve()}"
            )


def _run_command(command: list[str], *, description: str) -> None:
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout)[-4000:].strip()
        raise RuntimeError(
            f"{description} exited with status {completed.returncode}"
            + (f": {detail}" if detail else "")
        )


def _training_progress_update(event: dict[str, object]) -> tuple[int, str, str]:
    planned = max(1, int(event.get("planned_fit_count") or 0))
    completed = min(planned, max(0, int(event.get("completed_fit_count") or 0)))
    successful = max(0, int(event.get("successful_fit_count") or 0))
    failed = max(0, int(event.get("failed_fit_count") or 0))
    percent = 58 + round(32 * completed / planned)
    version_id = str(event.get("version_id") or "—")
    species_id = str(event.get("species_id") or "—")
    detail = (
        f"{completed}/{planned} · {version_id} · {species_id} · "
        f"✓ {successful} · ✗ {failed}"
    )
    return percent, "Training active operational generation", detail


def _benchmark_training_progress_update(
    event: dict[str, object],
) -> tuple[int, str, str]:
    percent, _, detail = _training_progress_update(event)
    return percent, "Training scientific benchmark", detail


def _preparation_progress_update(event: dict[str, object]) -> tuple[int, str, str]:
    planned = max(1, int(event.get("planned_step_count") or 0))
    completed = min(planned, max(0, int(event.get("completed_step_count") or 0)))
    percent = 50 + round(8 * completed / planned)
    source_phase = str(event.get("phase") or "Preparing V2--V6 inputs")
    phase = f"Preparing shared inputs — {source_phase} (not training)"
    detail = str(event.get("detail") or f"Preparation step {completed}/{planned}.")
    return percent, phase, detail


def _run_command_with_jsonl_progress(
    command: list[str],
    *,
    description: str,
    progress_path: Path,
    progress: ProgressCallback,
    event_mapper: ProgressEventMapper,
    telemetry_event_mapper: TelemetryEventMapper | None = None,
    cancel_requested: CancelCallback | None = None,
) -> None:
    """Run one command while forwarding its flushed JSONL progress events."""
    if progress_path.exists():
        raise FileExistsError(f"Progress file already exists: {progress_path}")
    seen_events = 0

    def forward(raw_event: str) -> None:
        event = json.loads(raw_event)
        if not isinstance(event, dict):
            raise ValueError("Local V2--V6 progress event must be an object")
        if telemetry_event_mapper is not None:
            telemetry_phase = telemetry_event_mapper(event)
            if telemetry_phase:
                mushroom_performance_telemetry.phase(telemetry_phase)
        progress(*event_mapper(event))

    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stdout_handle, tempfile.TemporaryFile(
        mode="w+", encoding="utf-8"
    ) as stderr_handle:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )
        try:
            while True:
                if cancel_requested is not None and cancel_requested():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise LocalBenchmarkCancelled(f"{description} was cancelled")
                if progress_path.is_file():
                    lines = _read_progress_lines(progress_path)
                    for raw_event in lines[seen_events:]:
                        forward(raw_event)
                    seen_events = len(lines)
                if process.poll() is not None:
                    break
                time.sleep(0.25)
        except BaseException:
            process.terminate()
            process.wait()
            raise
        if progress_path.is_file():
            lines = _read_progress_lines(progress_path)
            for raw_event in lines[seen_events:]:
                forward(raw_event)
        if process.returncode:
            stdout_handle.seek(0)
            stderr_handle.seek(0)
            detail = (stderr_handle.read() or stdout_handle.read())[-4000:].strip()
            raise RuntimeError(
                f"{description} exited with status {process.returncode}"
                + (f": {detail}" if detail else "")
            )


def _stage_rebuild_result(
    *,
    job_id: str,
    output_dir: Path,
    bundle_root: Path,
    candidate_results_root: Path,
    live_data_dir: Path,
) -> dict[str, object]:
    logical_paths = [
        mushroom_rebuild_contracts.RESULT_MANIFEST_NAME,
        *mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS,
    ]
    for logical_path in logical_paths:
        mushroom_worker_results.receive_result_file(
            candidate_results_root,
            bundle_root,
            job_id=job_id,
            logical_path=logical_path,
            content=_read_bytes(output_dir / logical_path),
        )
    return mushroom_worker_results.finalize_candidate_result(
        candidate_results_root,
        bundle_root,
        live_data_dir,
        job_id=job_id,
    )


def _stage_ml_result(
    *,
    job_id: str,
    output_dir: Path,
    candidate_results_root: Path,
) -> dict[str, object]:
    manifest_path = output_dir / mushroom_worker_results.ML_TRAIN_RESULT_NAME
    manifest = json.loads(_read_bytes(manifest_path).decode("utf-8"))
    artifacts = manifest.get("artifacts") if isinstance(manifest, dict) else None
    if not isinstance(artifacts, list):
        raise ValueError("Local ML result manifest has no artifacts")
    logical_paths = [mushroom_worker_results.ML_TRAIN_RESULT_NAME] + [
        str(row["path"]) for row in artifacts if isinstance(row, dict)
    ]
    for logical_path in logical_paths:
        mushroom_worker_results.receive_ml_train_result_file(
            candidate_results_root,
            job_id=job_id,
            logical_path=logical_path,
            content=_read_bytes(output_dir / logical_path),
        )
    return mushroom_worker_results.finalize_ml_train_result(
        candidate_results_root,
        job_id=job_id,
    )


def eligible_training_species(features_path: Path) -> list[str]:
    payload = json.loads(features_path.read_text(encoding="utf-8"))
    rows = payload.get("rows") if isinstance(payload, dict) else []
    counts: Counter[str] = Counter()
    classes: dict[str, set[str]] = {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or row.get("validation_status") != "valid"
            or row.get("calibration_use") != "include"
            or row.get("prediction_target") not in {"favorable", "unfavorable"}
            or row.get("micro_area_id") is None
            or not row.get("species_id")
        ):
            continue
        species_id = str(row["species_id"])
        counts[species_id] += 1
        classes.setdefault(species_id, set()).add(str(row["prediction_target"]))
    return [
        species_id
        for species_id, count in counts.most_common()
        if count >= 10 and classes.get(species_id) == {"favorable", "unfavorable"}
    ]


def _validate_runtime_registry_before_work(
    registry_path: Path,
    species_ids: list[str],
    requested_version_ids: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    try:
        version_ids = mushroom_ml_version_registry.training_version_ids(
            registry,
            job_purpose="operational",
            requested_version_ids=requested_version_ids,
        )
    except ValueError:
        if requested_version_ids is not None:
            raise
        version_ids = list(
            dict.fromkeys(
                row["version_id"]
                for row in mushroom_ml_version_registry.operational_profile_options(
                    registry
                )
            )
        )
    generation_ids = {
        str(row["version_id"]): f"preflight_{row['version_id']}"
        for row in registry.get("versions", [])
        if isinstance(row, dict) and row.get("version_id") in version_ids
    }
    plan = mushroom_ml_multiversion_plan.build_plan(
        registry,
        batch_id="local_preflight",
        snapshot_id="sha256:" + "0" * 64,
        generation_ids=generation_ids,
        species_ids=species_ids or ["preflight_species"],
        version_ids=version_ids,
        profile_keys=mushroom_ml_version_registry.training_profile_keys(
            registry, job_purpose="operational", version_ids=version_ids
        ),
    )
    mushroom_ml_runtime_trainer.validate_benchmark_coverage(
        plan,
        mushroom_ml_runtime_trainer.supported_runtime_benchmark_keys(),
    )
    return version_ids


def _write_rebased_features(source: Path, destination: Path, paths: LocalFullUpdatePaths) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Candidate observation features must be an object")
    rebased = mushroom_worker_results.rebase_features_payload_for_live(
        payload,
        live_outputs=mushroom_rebuild_pipeline.RebuildOutputPaths.under(
            paths.mushroom_data_dir
        ),
        reference_catalogs_path=paths.reference_catalogs,
    )
    destination.write_text(
        json.dumps(rebased, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def materialize_operational_tuning_catalog(
    *,
    registry: dict[str, object],
    version_ids: list[str] | tuple[str, ...],
    models_root: Path,
    destination: Path,
) -> dict[str, object]:
    source_batch_id = mushroom_ml_tuning_catalog.installed_source_batch_id(
        registry, version_ids
    )
    source_root = Path(models_root) / "batches" / source_batch_id
    source_manifest = json.loads(
        _read_bytes(source_root / "manifest.json").decode("utf-8")
    )
    checked_manifest = mushroom_ml_model_catalog.validate_batch_manifest(
        registry, source_manifest
    )
    catalog_reference = checked_manifest.get("tuning_catalog")
    reference_source_batch_id = (
        str(catalog_reference.get("source_batch_id") or "").strip()
        if isinstance(catalog_reference, dict)
        else ""
    )
    if isinstance(catalog_reference, dict) and catalog_reference.get("path"):
        relative = Path(str(catalog_reference["path"]))
        expected_prefix = Path("batches", source_batch_id)
        try:
            within_batch = relative.relative_to(expected_prefix)
        except ValueError as exc:
            raise ValueError("Runtime tuning catalog is outside its batch") from exc
        source_catalog_path = source_root / within_batch
        if reference_source_batch_id != source_batch_id:
            source_catalog_path.unlink(missing_ok=True)
        elif source_catalog_path.is_file():
            content = _read_bytes(source_catalog_path)
            actual_digest = hashlib.sha256(content).hexdigest()
            if actual_digest != str(catalog_reference.get("sha256") or ""):
                source_catalog_path.unlink(missing_ok=True)
            else:
                loaded = json.loads(content.decode("utf-8"))
                loaded_decisions = loaded.get("decisions") if isinstance(loaded, dict) else None
                identity_matches = (
                    isinstance(loaded, dict)
                    and loaded.get("source_batch_id") == source_batch_id
                    and loaded.get("catalog_id") == catalog_reference.get("catalog_id")
                    and isinstance(loaded_decisions, list)
                    and len(loaded_decisions) == catalog_reference.get("decision_count")
                )
                if not identity_matches:
                    source_catalog_path.unlink(missing_ok=True)
                else:
                    catalog = mushroom_ml_tuning_catalog.validate_catalog(
                        registry, loaded
                    )
                    mushroom_ml_tuning_catalog.save(destination, catalog)
                    return catalog
    catalog = mushroom_ml_tuning_catalog.build_from_batch(
        registry,
        source_manifest,
        batch_root=source_root,
    )
    mushroom_ml_tuning_catalog.save(destination, catalog)
    return catalog


# Compatibility alias for callers/tests predating the public chained-worker API.
_materialize_operational_tuning_catalog = materialize_operational_tuning_catalog


def run_local_benchmark(
    *,
    operation_id: str,
    paths: LocalFullUpdatePaths,
    progress: ProgressCallback,
    profile_keys: list[str] | None = None,
    cancel_requested: CancelCallback | None = None,
) -> dict[str, object]:
    """Run and archive a manual V2--V6 benchmark without changing Predictor runtime."""
    _validate_isolated_work_root(paths)
    feature_path = paths.mushroom_data_dir / "mushroom_observation_features_v0.json"
    species_ids = eligible_training_species(feature_path)
    if not species_ids:
        raise ValueError("No species meet the minimum row count for local benchmark training")
    registry = mushroom_ml_version_registry.load_registry(paths.registry)
    selected_profiles = mushroom_ml_version_registry.resolve_benchmark_profiles(
        registry, profile_keys
    )
    resolved_profile_keys = [row["profile_key"] for row in selected_profiles]
    version_ids = list(dict.fromkeys(row["version_id"] for row in selected_profiles))
    job_id = mushroom_worker_transport.validate_job_id(
        f"worker_job_local_benchmark_{operation_id}"
    )
    operation_root = paths.work_root / operation_id
    operation_root.mkdir(parents=True, exist_ok=False)
    try:
        progress(2, "Preparing scientific benchmark", "Creating a fresh immutable benchmark snapshot.")
        bundle = mushroom_worker_transport.prepare_coordinator_bundle(
            paths.bundle_root,
            job_id=job_id,
            observations_path=paths.observations,
            reference_catalogs_path=paths.reference_catalogs,
            gis_mappings_path=paths.gis_mappings,
            weather_data_dir=paths.weather_data_dir,
            gis_root=paths.gis_root,
            prefer_weather_parquet=True,
            allow_partitioned_weather_history=True,
            extra_inputs={
                "registry.json": paths.registry,
                "known-sites.json": paths.known_sites,
                "stations.txt": paths.stations,
                "observation-features.json": feature_path,
            },
        )
        bundle_dir = paths.bundle_root / job_id
        snapshot_dir = bundle_dir / mushroom_worker_transport.SNAPSHOT_PREFIX
        input_manifest = mushroom_rebuild_snapshot.load_manifest(snapshot_dir)
        resolved_inputs = mushroom_rebuild_snapshot.resolved_input_paths(
            snapshot_dir, input_manifest
        )
        extra_root = snapshot_dir / "inputs" / "extra"
        prepared_root = operation_root / "multiversion-inputs"
        preparation_progress = operation_root / "multiversion-preparation-progress.jsonl"
        preparation_command = [
                sys.executable,
                str(paths.scripts_dir / "prepare-mushroom-ml-multiversion-inputs.py"),
                "--scripts-dir",
                str(paths.scripts_dir),
                "--data-dir",
                str(resolved_inputs["weather_data_dir"]),
                "--observations",
                str(resolved_inputs["observations"]),
                "--known-sites",
                str(extra_root / "known-sites.json"),
                "--observation-features",
                str(extra_root / "observation-features.json"),
                "--stations-file",
                str(extra_root / "stations.txt"),
                "--output-dir",
                str(prepared_root),
                "--source-snapshot-id",
                str(bundle["snapshot_id"]),
                "--progress-jsonl",
                str(preparation_progress),
            ]
        for profile_key in resolved_profile_keys:
            preparation_command.extend(["--profile-key", profile_key])
        _run_command_with_jsonl_progress(
            preparation_command,
            description="Local scientific benchmark input preparation",
            progress_path=preparation_progress,
            progress=progress,
            event_mapper=_preparation_progress_update,
            cancel_requested=cancel_requested,
        )
        if cancel_requested is not None and cancel_requested():
            raise LocalBenchmarkCancelled("Local scientific benchmark was cancelled")
        prepared = json.loads(
            (prepared_root / "prepared-inputs.json").read_text(encoding="utf-8")
        )
        model_inputs = prepared.get("inputs") if isinstance(prepared, dict) else None
        if not isinstance(model_inputs, dict):
            raise ValueError("Prepared local benchmark inputs are invalid")
        batch_id = "benchmark_v2_v6_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        generation_ids = {
            version_id: f"{version_id}_{batch_id}" for version_id in version_ids
        }
        result_root = operation_root / "multiversion-result"
        result_root.mkdir()
        result_manifest = result_root / "multiversion_result.json"
        command = [
            sys.executable,
            str(paths.scripts_dir / "run-mushroom-ml-multiversion-job.py"),
            "--registry",
            str(extra_root / "registry.json"),
            "--snapshot-id",
            str(bundle["snapshot_id"]),
            "--batch-id",
            batch_id,
            "--v3-fixed",
            str(model_inputs["v3_fixed"]),
            "--v3-lag",
            str(model_inputs["v3_lag"]),
            "--v2-v5-heldout",
            str(model_inputs["v2_v5_heldout"]),
            "--v6-heldout",
            str(model_inputs["v6_heldout"]),
            "--models-root",
            str(operation_root / "multiversion-models"),
            "--summary",
            str(operation_root / "multiversion-summary.json"),
            "--job-id",
            job_id,
            "--result-manifest",
            str(result_manifest),
            "--training-input-manifest",
            str(snapshot_dir / mushroom_rebuild_snapshot.MANIFEST_NAME),
            "--job-purpose",
            "benchmark",
        ]
        for option, key in (
            ("--v4-fixed", "v4_fixed"),
            ("--v4-lag", "v4_lag"),
            ("--v5-fixed", "v5_fixed"),
            ("--v5-lag", "v5_lag"),
        ):
            if key in model_inputs:
                command.extend([option, str(model_inputs[key])])
        for version_id, generation_id in generation_ids.items():
            command.extend(["--generation", f"{version_id}={generation_id}"])
            command.extend(["--version", version_id])
        for profile_key in resolved_profile_keys:
            command.extend(["--profile-key", profile_key])
        for species_id in species_ids:
            command.extend(["--species", species_id])
        benchmark_progress = operation_root / "multiversion-progress.jsonl"
        command.extend(["--progress-jsonl", str(benchmark_progress)])
        progress(58, "Training scientific benchmark", "Training isolated V2--V6 benchmark models.")
        _run_command_with_jsonl_progress(
            command,
            description="Local scientific benchmark training",
            progress_path=benchmark_progress,
            progress=progress,
            event_mapper=_benchmark_training_progress_update,
            cancel_requested=cancel_requested,
        )
        if cancel_requested is not None and cancel_requested():
            raise LocalBenchmarkCancelled("Local scientific benchmark was cancelled")
        archived = mushroom_ml_multiversion_transport.archive_verified_result(
            result_manifest_path=result_manifest,
            result_root=result_root,
            registry_path=paths.registry,
            models_root=paths.ml_models_dir,
            job_id=job_id,
        )
        progress(100, "Scientific benchmark archived", "Predictor runtime was not changed.")
        return {
            "executor": "home_assistant_local",
            "operation_id": operation_id,
            "job_purpose": "benchmark",
            "job_id": job_id,
            "snapshot_id": bundle["snapshot_id"],
            "version_ids": version_ids,
            "profile_keys": resolved_profile_keys,
            "archive": archived,
            "batch_id": archived["batch_id"],
            "report_id": archived["report_id"],
            "planned_fit_count": archived["planned_fit_count"],
            "successful_fit_count": archived["successful_fit_count"],
            "failed_fit_count": archived["failed_fit_count"],
            "artifact_count": archived["artifact_count"],
            "summary": archived["summary"],
            "selection": archived["selection"],
            "benchmark_report_available": True,
            "operational_candidate_trained": False,
        }
    finally:
        bundle_dir = paths.bundle_root / job_id
        if bundle_dir.is_dir():
            shutil.rmtree(bundle_dir)
        shutil.rmtree(operation_root, ignore_errors=True)


def run_local_full_update(
    *,
    operation_id: str,
    selected_observation_ids: list[str],
    species_ids: list[str],
    paths: LocalFullUpdatePaths,
    progress: ProgressCallback,
    version_ids: list[str] | tuple[str, ...] | None = None,
    telemetry_path: Path | None = None,
    pre_snapshot: PreSnapshotCallback | None = None,
) -> dict[str, object]:
    """Run reconstruction, ML v0 and selected installed ML versions locally."""
    if not selected_observation_ids:
        raise ValueError("The complete local update has no eligible observations")
    _validate_isolated_work_root(paths)
    version_ids = _validate_runtime_registry_before_work(
        paths.registry,
        species_ids,
        version_ids,
    )
    registry_before = mushroom_ml_version_registry.load_registry(paths.registry)
    profile_keys = mushroom_ml_version_registry.training_profile_keys(
        registry_before, job_purpose="operational", version_ids=version_ids
    )
    rebuild_job_id = mushroom_worker_transport.validate_job_id(
        f"worker_job_local_rebuild_{operation_id}"
    )
    training_job_id = mushroom_worker_transport.validate_job_id(
        f"worker_job_local_train_{operation_id}"
    )
    comparison_job_id = mushroom_worker_transport.validate_job_id(
        f"worker_job_local_v2v6_{operation_id}"
    )
    operation_root = paths.work_root / operation_id
    operation_root.mkdir(parents=True, exist_ok=False)
    resolved_telemetry_path = telemetry_path or (
        paths.mushroom_data_dir
        / "diagnostics"
        / "operational-performance"
        / f"{operation_id}.json"
    )
    telemetry = mushroom_performance_telemetry.PersistentTelemetry(
        resolved_telemetry_path,
        operation_id=operation_id,
        workload="local_operational_full_update",
    )
    telemetry_context = mushroom_performance_telemetry.activate(telemetry)
    telemetry_context.__enter__()
    result_payload: dict[str, object] | None = None
    telemetry_status = "failed"
    telemetry_error = ""
    installed_batch_id = ""
    previous_registry = _read_bytes(paths.registry)
    revisions_path = paths.ml_models_dir / "current-input-revisions.json"
    previous_revisions = _read_bytes(revisions_path) if revisions_path.is_file() else None
    rebuild_promoted = False
    pre_snapshot_report: dict[str, object] = {}
    try:
        if pre_snapshot is not None:
            mushroom_performance_telemetry.phase("soilgrids_reconciliation")
            progress(
                1,
                "Reconciling GIS and SoilGrids",
                "Repairing missing terrain context before freezing model inputs.",
            )
            pre_snapshot_report = pre_snapshot()
            mushroom_performance_telemetry.add(
                bytes_written=int(pre_snapshot_report.get("downloaded_bytes", 0) or 0),
                files_read=int(pre_snapshot_report.get("files_read", 0) or 0),
                files_written=int(pre_snapshot_report.get("files_promoted", 0) or 0),
                requests=int(pre_snapshot_report.get("requests", 0) or 0),
                hashes=int(pre_snapshot_report.get("asset_hashes_checked", 0) or 0),
                hash_bytes=int(pre_snapshot_report.get("hash_bytes", 0) or 0),
                fsyncs=int(pre_snapshot_report.get("fsyncs", 0) or 0),
            )
        mushroom_performance_telemetry.phase("reconstruction_snapshot")
        progress(2, "Preparing immutable inputs", "Creating the local reconstruction snapshot.")
        rebuild_bundle = mushroom_worker_transport.prepare_coordinator_bundle(
            paths.bundle_root,
            job_id=rebuild_job_id,
            observations_path=paths.observations,
            reference_catalogs_path=paths.reference_catalogs,
            gis_mappings_path=paths.gis_mappings,
            weather_data_dir=paths.weather_data_dir,
            gis_root=paths.gis_root,
            reconstruction_scope="all",
            selected_observation_ids=selected_observation_ids,
            prefer_weather_parquet=True,
            allow_partitioned_weather_history=True,
        )
        rebuild_bundle_dir = paths.bundle_root / rebuild_job_id
        rebuild_output = operation_root / "rebuild-candidate"
        mushroom_performance_telemetry.phase("reconstruction_compute")
        progress(5, "Reconstructing artifacts", "Running the shared reconstruction pipeline locally.")
        _run_command(
            [
                sys.executable,
                str(paths.scripts_dir / "run-mushroom-rebuild-job.py"),
                "run",
                "--snapshot-dir",
                str(rebuild_bundle_dir / mushroom_worker_transport.SNAPSHOT_PREFIX),
                "--job-spec",
                str(rebuild_bundle_dir / mushroom_worker_transport.JOB_SPEC_LOGICAL_PATH),
                "--output-dir",
                str(rebuild_output),
                "--gis-root",
                str(paths.gis_root),
                "--quiet",
            ],
            description="Local reconstruction",
        )
        mushroom_performance_telemetry.phase("reconstruction_verification")
        rebuild_verification = _stage_rebuild_result(
            job_id=rebuild_job_id,
            output_dir=rebuild_output,
            bundle_root=paths.bundle_root,
            candidate_results_root=paths.candidate_results_root,
            live_data_dir=paths.mushroom_data_dir,
        )

        candidate_features = (
            paths.candidate_results_root
            / rebuild_job_id
            / "mushroom_observation_features_v0.json"
        )
        training_input = operation_root / "training-features.json"
        _write_rebased_features(candidate_features, training_input, paths)
        operational_scope = mushroom_operational_training_scope.build_scope(
            json.loads(training_input.read_text(encoding="utf-8")),
            json.loads(paths.known_sites.read_text(encoding="utf-8")),
        )
        trained_species = list(operational_scope["admitted_species_ids"])
        if not trained_species:
            raise ValueError("No species meet the minimum row count for local ML training")
        training_spec = operation_root / "ml-job-spec.json"
        training_spec.write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "kind": "mushroom_ml_train_v0_spec",
                    "job_id": training_job_id,
                    "species_ids": trained_species,
                    "min_rows": operational_scope["min_episodes"],
                    "cv_folds": 3,
                    "operational_scope": operational_scope,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        training_output = operation_root / "ml-candidate"
        mushroom_performance_telemetry.phase("ml_v0_training")
        progress(38, "Training ML v0", "Training operational and shadow v0 models locally.")
        _run_command(
            [
                sys.executable,
                str(paths.scripts_dir / "run-mushroom-ml-train-job.py"),
                "--job-spec",
                str(training_spec),
                "--features",
                str(training_input),
                "--known-sites",
                str(paths.known_sites),
                "--output-dir",
                str(training_output),
                "--quiet",
            ],
            description="Local ML v0 training",
        )
        mushroom_performance_telemetry.phase("ml_v0_verification")
        training_verification = _stage_ml_result(
            job_id=training_job_id,
            output_dir=training_output,
            candidate_results_root=paths.candidate_results_root,
        )
        if training_verification.get("operational_scope_id") != operational_scope["scope_id"]:
            raise ValueError("Verified local ML v0 result does not match its requested scope")
        mushroom_operational_training_scope.assert_scope_trained_species(
            operational_scope,
            training_verification.get("trained_species") or [],
        )
        mushroom_performance_telemetry.phase("operational_snapshot")
        progress(48, "Preparing operational ML", "Creating a fresh immutable training snapshot.")
        comparison_bundle = mushroom_worker_transport.prepare_coordinator_bundle(
            paths.bundle_root,
            job_id=comparison_job_id,
            observations_path=paths.observations,
            reference_catalogs_path=paths.reference_catalogs,
            gis_mappings_path=paths.gis_mappings,
            weather_data_dir=paths.weather_data_dir,
            gis_root=paths.gis_root,
            prefer_weather_parquet=True,
            allow_partitioned_weather_history=True,
            extra_inputs={
                "registry.json": paths.registry,
                "known-sites.json": paths.known_sites,
                "stations.txt": paths.stations,
                "observation-features.json": training_input,
            },
        )
        comparison_bundle_dir = paths.bundle_root / comparison_job_id
        snapshot_dir = comparison_bundle_dir / mushroom_worker_transport.SNAPSHOT_PREFIX
        input_manifest = mushroom_rebuild_snapshot.load_manifest(snapshot_dir)
        resolved_inputs = mushroom_rebuild_snapshot.resolved_input_paths(
            snapshot_dir, input_manifest
        )
        extra_root = snapshot_dir / "inputs" / "extra"
        registry = mushroom_ml_version_registry.load_registry(extra_root / "registry.json")
        tuning_catalog_path = operation_root / "tuning-catalog.json"
        tuning_catalog = materialize_operational_tuning_catalog(
            registry=registry,
            version_ids=version_ids,
            models_root=paths.ml_models_dir,
            destination=tuning_catalog_path,
        )
        operational_plan = mushroom_operational_training_scope.build_plan(
            registry,
            operational_scope,
            tuning_catalog,
            version_ids=version_ids,
            profile_keys=profile_keys,
        )
        operational_plan_path = operation_root / "operational-training-plan.json"
        operational_plan_path.write_text(
            json.dumps(operational_plan, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        prepared_root = operation_root / "multiversion-inputs"
        preparation_progress = operation_root / "multiversion-preparation-progress.jsonl"
        mushroom_performance_telemetry.phase("operational_preparation")
        progress(50, "Preparing operational ML", "Building shared V2--V6 inputs and hold-out evidence.")
        preparation_command = [
                sys.executable,
                str(paths.scripts_dir / "prepare-mushroom-ml-multiversion-inputs.py"),
                "--scripts-dir",
                str(paths.scripts_dir),
                "--data-dir",
                str(resolved_inputs["weather_data_dir"]),
                "--observations",
                str(resolved_inputs["observations"]),
                "--known-sites",
                str(extra_root / "known-sites.json"),
                "--observation-features",
                str(extra_root / "observation-features.json"),
                "--stations-file",
                str(extra_root / "stations.txt"),
                "--output-dir",
                str(prepared_root),
                "--source-snapshot-id",
                str(comparison_bundle["snapshot_id"]),
                "--progress-jsonl",
                str(preparation_progress),
                "--job-purpose",
                "operational",
                "--tuning-catalog",
                str(tuning_catalog_path),
                "--operational-plan",
                str(operational_plan_path),
            ]
        for profile_key in profile_keys:
            preparation_command.extend(["--profile-key", profile_key])
        _run_command_with_jsonl_progress(
            preparation_command,
            description="Local operational multiversion input preparation",
            progress_path=preparation_progress,
            progress=progress,
            event_mapper=_preparation_progress_update,
            telemetry_event_mapper=lambda event: (
                "operational_preparation:"
                + str(event.get("phase") or "inputs").strip().lower().replace(" ", "_")
            ),
        )
        prepared = json.loads(
            (prepared_root / "prepared-inputs.json").read_text(encoding="utf-8")
        )
        model_inputs = prepared.get("inputs") if isinstance(prepared, dict) else None
        if not isinstance(model_inputs, dict) or prepared.get("operational_candidate_trained") is not False:
            raise ValueError("Prepared local operational multiversion inputs are invalid")
        batch_id = "local_operational_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        generation_ids = {
            str(row["version_id"]): f"{row['version_id']}_{batch_id}"
            for row in registry.get("versions", [])
            if isinstance(row, dict) and row.get("version_id") in version_ids
        }
        comparison_result = operation_root / "multiversion-result"
        comparison_result.mkdir()
        comparison_models = operation_root / "multiversion-models"
        comparison_summary = operation_root / "multiversion-summary.json"
        comparison_manifest = comparison_result / "multiversion_result.json"
        command = [
            sys.executable,
            str(paths.scripts_dir / "run-mushroom-ml-multiversion-job.py"),
            "--registry",
            str(extra_root / "registry.json"),
            "--snapshot-id",
            str(comparison_bundle["snapshot_id"]),
            "--batch-id",
            batch_id,
            "--v3-fixed",
            str(model_inputs["v3_fixed"]),
            "--v3-lag",
            str(model_inputs["v3_lag"]),
            "--models-root",
            str(comparison_models),
            "--summary",
            str(comparison_summary),
            "--job-id",
            comparison_job_id,
            "--result-manifest",
            str(comparison_manifest),
            "--training-input-manifest",
            str(snapshot_dir / mushroom_rebuild_snapshot.MANIFEST_NAME),
            "--tuning-catalog",
            str(tuning_catalog_path),
            "--job-purpose",
            "operational",
            "--operational-plan",
            str(operational_plan_path),
        ]
        for option, key in (
            ("--v4-fixed", "v4_fixed"),
            ("--v4-lag", "v4_lag"),
            ("--v5-fixed", "v5_fixed"),
            ("--v5-lag", "v5_lag"),
            ("--v2-v5-heldout", "v2_v5_heldout"),
            ("--v6-heldout", "v6_heldout"),
        ):
            if key in model_inputs:
                command.extend([option, str(model_inputs[key])])
        for version_id in version_ids:
            command.extend(["--version", version_id])
        for profile_key in profile_keys:
            command.extend(["--profile-key", profile_key])
        for version_id, generation_id in generation_ids.items():
            command.extend(["--generation", f"{version_id}={generation_id}"])
        for species_id in sorted(trained_species):
            command.extend(["--species", species_id])
        comparison_progress = operation_root / "multiversion-progress.jsonl"
        command.extend(["--progress-jsonl", str(comparison_progress)])
        mushroom_performance_telemetry.phase("operational_training")
        progress(
            58,
            "Refreshing operational ML versions",
            f"Training every Predictor artifact required by {len(version_ids)} versions.",
        )
        _run_command_with_jsonl_progress(
            command,
            description="Local operational multiversion training",
            progress_path=comparison_progress,
            progress=progress,
            event_mapper=_training_progress_update,
            telemetry_event_mapper=lambda event: (
                "operational_training:"
                + str(event.get("version_id") or "fits").strip().lower().replace(" ", "_")
            ),
        )
        comparison_result_payload = mushroom_ml_multiversion_transport.validate_result_manifest(
            json.loads(comparison_manifest.read_text(encoding="utf-8")),
            job_id=comparison_job_id,
            expected_purpose="operational",
        )
        mushroom_performance_telemetry.phase("operational_install_and_promotion")
        progress(
            92,
            "Promoting full generation",
            "Installing the active generation and publishing reconstructed artifacts and ML v0 atomically.",
        )
        installed_batch_id = str(comparison_result_payload["batch_id"])
        comparison_install = mushroom_ml_multiversion_transport.install_verified_result(
            result_manifest_path=comparison_manifest,
            result_root=comparison_result,
            registry_path=paths.registry,
            models_root=paths.ml_models_dir,
            job_id=comparison_job_id,
        )
        if str(comparison_install["batch_id"]) != installed_batch_id:
            raise ValueError("Installed operational batch identity changed during promotion")
        installed_manifest = json.loads(
            (
                paths.ml_models_dir
                / "batches"
                / installed_batch_id
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        installed_registry = mushroom_ml_version_registry.install_batch_generations(
            mushroom_ml_version_registry.load_registry(paths.registry),
            installed_manifest,
            approved_by="local_full_update",
        )
        mushroom_ml_version_registry.save_registry(paths.registry, installed_registry)
        mushroom_ml_training_freshness.publish_current_revisions(
            revisions_path,
            installed_manifest["input_revisions"],
        )
        rebuild_promotion = mushroom_worker_results.promote_verified_candidate(
            paths.candidate_results_root,
            paths.bundle_root,
            paths.mushroom_data_dir,
            job_id=rebuild_job_id,
            observations_path=paths.observations,
            reference_catalogs_path=paths.reference_catalogs,
            gis_mappings_path=paths.gis_mappings,
            weather_data_dir=paths.weather_data_dir,
            gis_root=paths.gis_root,
        )
        rebuild_promoted = True
        try:
            training_promotion = mushroom_worker_results.promote_ml_train_candidate(
                paths.candidate_results_root,
                paths.ml_models_dir,
                job_id=training_job_id,
                report_path=paths.ml_report,
            )
        except BaseException:
            mushroom_worker_results.rollback_promoted_candidate(
                paths.candidate_results_root,
                paths.mushroom_data_dir,
                job_id=rebuild_job_id,
            )
            rebuild_promoted = False
            raise
        progress(100, "Complete generation active", "Local reconstruction and all training stages completed.")
        result_payload = {
            "executor": "home_assistant_local",
            "operation_id": operation_id,
            "subjobs": {
                "reconstruction": rebuild_job_id,
                "ml_v0": training_job_id,
                "operational_ml": comparison_job_id,
            },
            "snapshot_id": rebuild_bundle["snapshot_id"],
            "operational_snapshot_id": comparison_bundle["snapshot_id"],
            "operational_scope_id": operational_scope["scope_id"],
            "operational_plan_id": operational_plan["plan_id"],
            "tuning_catalog_id": operational_plan["tuning_catalog_id"],
            "species_ids": list(operational_scope["admitted_species_ids"]),
            "rebuild_verification": rebuild_verification,
            "training_verification": training_verification,
            "comparison_install": comparison_install,
            "rebuild_promotion": rebuild_promotion,
            "training_promotion": training_promotion,
            "training_input_manifest_sha256": _sha256(
                paths.ml_models_dir / "batches" / installed_batch_id / "training-input-manifest.json"
            ),
            "version_ids": version_ids,
            "preferred_version_id": installed_registry.get("preferred_version_id"),
            "operational_candidate_trained": True,
            "soilgrids_reconciliation": pre_snapshot_report,
        }
        result_payload["performance_telemetry"] = telemetry.finish("complete")
        result_payload["performance_telemetry_path"] = str(resolved_telemetry_path)
        telemetry_status = "complete"
        return result_payload
    except BaseException as exc:
        telemetry_error = str(exc)
        if isinstance(exc, LocalBenchmarkCancelled):
            telemetry_status = "cancelled"
        if installed_batch_id:
            mushroom_ml_multiversion_transport.remove_installed_batch(
                models_root=paths.ml_models_dir,
                batch_id=installed_batch_id,
            )
            mushroom_ml_version_registry.save_registry(
                paths.registry, json.loads(previous_registry)
            )
            mushroom_ml_training_freshness.restore_current_revisions(
                revisions_path, previous_revisions
            )
        if rebuild_promoted:
            mushroom_worker_results.rollback_promoted_candidate(
                paths.candidate_results_root,
                paths.mushroom_data_dir,
                job_id=rebuild_job_id,
            )
        raise
    finally:
        for job_id in (rebuild_job_id, training_job_id, comparison_job_id):
            bundle_dir = paths.bundle_root / job_id
            if bundle_dir.is_dir():
                shutil.rmtree(bundle_dir)
            candidate_dir = paths.candidate_results_root / job_id
            if candidate_dir.is_dir():
                shutil.rmtree(candidate_dir)
        shutil.rmtree(operation_root, ignore_errors=True)
        try:
            if telemetry.snapshot().get("status") == "running":
                telemetry.finish(telemetry_status, error=telemetry_error)
        finally:
            telemetry_context.__exit__(None, None, None)
