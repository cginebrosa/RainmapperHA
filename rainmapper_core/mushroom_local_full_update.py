"""Complete mushroom-model regeneration executed inside a local HA container.

This module deliberately reuses the external-worker contracts.  It is an
execution adapter for the local development stack, not a second production
pipeline: reconstruction and both training stages are built from immutable
snapshots, verified, and only then promoted.
"""

from __future__ import annotations

import hashlib
import json
import os
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
from rainmapper_core import mushroom_ml_runtime_trainer
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_rebuild_contracts
from rainmapper_core import mushroom_rebuild_pipeline
from rainmapper_core import mushroom_rebuild_snapshot
from rainmapper_core import mushroom_worker_results
from rainmapper_core import mushroom_worker_transport


ProgressCallback = Callable[[int, str, str], None]
ProgressEventMapper = Callable[[dict[str, object]], tuple[int, str, str]]


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
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    return percent, "Training V2--V6", detail


def _preparation_progress_update(event: dict[str, object]) -> tuple[int, str, str]:
    planned = max(1, int(event.get("planned_step_count") or 0))
    completed = min(planned, max(0, int(event.get("completed_step_count") or 0)))
    percent = 50 + round(8 * completed / planned)
    phase = str(event.get("phase") or "Preparing V2--V6 inputs")
    detail = str(event.get("detail") or f"Preparation step {completed}/{planned}.")
    return percent, phase, detail


def _run_command_with_jsonl_progress(
    command: list[str],
    *,
    description: str,
    progress_path: Path,
    progress: ProgressCallback,
    event_mapper: ProgressEventMapper,
) -> None:
    """Run one command while forwarding its flushed JSONL progress events."""
    if progress_path.exists():
        raise FileExistsError(f"Progress file already exists: {progress_path}")
    seen_events = 0
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
                if progress_path.is_file():
                    lines = progress_path.read_text(encoding="utf-8").splitlines()
                    for raw_event in lines[seen_events:]:
                        event = json.loads(raw_event)
                        if not isinstance(event, dict):
                            raise ValueError("Local V2--V6 progress event must be an object")
                        progress(*event_mapper(event))
                    seen_events = len(lines)
                if process.poll() is not None:
                    break
                time.sleep(0.25)
        except BaseException:
            process.terminate()
            process.wait()
            raise
        if progress_path.is_file():
            lines = progress_path.read_text(encoding="utf-8").splitlines()
            for raw_event in lines[seen_events:]:
                event = json.loads(raw_event)
                if not isinstance(event, dict):
                    raise ValueError("Local V2--V6 progress event must be an object")
                progress(*event_mapper(event))
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
            content=(output_dir / logical_path).read_bytes(),
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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
            content=(output_dir / logical_path).read_bytes(),
        )
    return mushroom_worker_results.finalize_ml_train_result(
        candidate_results_root,
        job_id=job_id,
    )


def _eligible_training_species(features_path: Path) -> list[str]:
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
) -> None:
    registry = mushroom_ml_version_registry.load_registry(registry_path)
    generation_ids = {
        str(row["version_id"]): f"preflight_{row['version_id']}"
        for row in registry.get("versions", [])
        if isinstance(row, dict) and row.get("version_id")
    }
    plan = mushroom_ml_multiversion_plan.build_plan(
        registry,
        batch_id="local_preflight",
        snapshot_id="sha256:" + "0" * 64,
        generation_ids=generation_ids,
        species_ids=species_ids or ["preflight_species"],
    )
    mushroom_ml_runtime_trainer.validate_benchmark_coverage(
        plan,
        mushroom_ml_runtime_trainer.supported_runtime_benchmark_keys(),
    )


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


def _restore_runtime_batch(
    *,
    models_root: Path,
    installed_batch_id: str,
    previous_descriptor: bytes | None,
) -> None:
    destination = models_root / "batches" / installed_batch_id
    if destination.is_dir():
        shutil.rmtree(destination)
    descriptor = models_root / "runtime-batch.json"
    if previous_descriptor is None:
        descriptor.unlink(missing_ok=True)
        return
    handle, temporary_name = tempfile.mkstemp(
        prefix=".runtime-batch.rollback.", suffix=".tmp", dir=models_root
    )
    try:
        with os.fdopen(handle, "wb") as temporary:
            temporary.write(previous_descriptor)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, descriptor)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def run_local_full_update(
    *,
    operation_id: str,
    selected_observation_ids: list[str],
    species_ids: list[str],
    paths: LocalFullUpdatePaths,
    progress: ProgressCallback,
) -> dict[str, object]:
    """Run reconstruction, ML v0 and V2--V6 locally using worker contracts."""
    if not selected_observation_ids:
        raise ValueError("The complete local update has no eligible observations")
    _validate_isolated_work_root(paths)
    _validate_runtime_registry_before_work(paths.registry, species_ids)
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
    installed_batch_id = ""
    previous_descriptor_path = paths.ml_models_dir / "runtime-batch.json"
    previous_descriptor = (
        previous_descriptor_path.read_bytes()
        if previous_descriptor_path.is_file()
        else None
    )
    rebuild_promoted = False
    try:
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
        trained_species = _eligible_training_species(training_input)
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
                    "min_rows": 10,
                    "cv_folds": 3,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        training_output = operation_root / "ml-candidate"
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
        training_verification = _stage_ml_result(
            job_id=training_job_id,
            output_dir=training_output,
            candidate_results_root=paths.candidate_results_root,
        )

        progress(48, "Preparing V2--V6", "Creating a fresh immutable comparison snapshot.")
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
        prepared_root = operation_root / "multiversion-inputs"
        preparation_progress = operation_root / "multiversion-preparation-progress.jsonl"
        progress(50, "Preparing V2--V6", "Building disposable benchmarks from the fresh snapshot.")
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
            ]
        _run_command_with_jsonl_progress(
            preparation_command,
            description="Local V2--V6 input preparation",
            progress_path=preparation_progress,
            progress=progress,
            event_mapper=_preparation_progress_update,
        )
        prepared = json.loads(
            (prepared_root / "prepared-inputs.json").read_text(encoding="utf-8")
        )
        model_inputs = prepared.get("inputs") if isinstance(prepared, dict) else None
        if not isinstance(model_inputs, dict) or prepared.get("operational_candidate_trained") is not False:
            raise ValueError("Prepared local V2--V6 inputs are invalid")
        registry = mushroom_ml_version_registry.load_registry(extra_root / "registry.json")
        batch_id = "local_v2_v6_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        generation_ids = {
            str(row["version_id"]): f"{row['version_id']}_{batch_id}"
            for row in registry.get("versions", [])
            if isinstance(row, dict) and row.get("version_id")
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
            "--v4-fixed",
            str(model_inputs["v4_fixed"]),
            "--v4-lag",
            str(model_inputs["v4_lag"]),
            "--v5-fixed",
            str(model_inputs["v5_fixed"]),
            "--v5-lag",
            str(model_inputs["v5_lag"]),
            "--v2-v5-heldout",
            str(model_inputs["v2_v5_heldout"]),
            "--v6-heldout",
            str(model_inputs["v6_heldout"]),
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
        ]
        for version_id, generation_id in generation_ids.items():
            command.extend(["--generation", f"{version_id}={generation_id}"])
        for species_id in sorted(trained_species):
            command.extend(["--species", species_id])
        comparison_progress = operation_root / "multiversion-progress.jsonl"
        command.extend(["--progress-jsonl", str(comparison_progress)])
        progress(58, "Training V2--V6", "Training the non-operational comparison batch locally.")
        _run_command_with_jsonl_progress(
            command,
            description="Local V2--V6 training",
            progress_path=comparison_progress,
            progress=progress,
            event_mapper=_training_progress_update,
        )
        comparison_result_payload = mushroom_ml_multiversion_transport.validate_result_manifest(
            json.loads(comparison_manifest.read_text(encoding="utf-8")),
            job_id=comparison_job_id,
        )
        progress(
            92,
            "Promoting full generation",
            "Installing V2--V6 and publishing reconstructed artifacts and ML v0 as one generation.",
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
            raise ValueError("Installed V2--V6 batch identity changed during promotion")
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
        return {
            "executor": "home_assistant_local",
            "operation_id": operation_id,
            "subjobs": {
                "reconstruction": rebuild_job_id,
                "ml_v0": training_job_id,
                "v2_v6": comparison_job_id,
            },
            "snapshot_id": rebuild_bundle["snapshot_id"],
            "comparison_snapshot_id": comparison_bundle["snapshot_id"],
            "rebuild_verification": rebuild_verification,
            "training_verification": training_verification,
            "comparison_install": comparison_install,
            "rebuild_promotion": rebuild_promotion,
            "training_promotion": training_promotion,
            "training_input_manifest_sha256": _sha256(
                paths.ml_models_dir / "batches" / installed_batch_id / "training-input-manifest.json"
            ),
            "operational_candidate_trained": False,
        }
    except BaseException:
        if installed_batch_id:
            _restore_runtime_batch(
                models_root=paths.ml_models_dir,
                installed_batch_id=installed_batch_id,
                previous_descriptor=previous_descriptor,
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
