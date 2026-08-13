"""Authenticated staging and verification for external worker candidate results."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from rainmapper_core import mushroom_rebuild_comparison
from rainmapper_core import mushroom_rebuild_contracts
from rainmapper_core import mushroom_rebuild_pipeline
from rainmapper_core import mushroom_rebuild_snapshot
from rainmapper_core import mushroom_worker_transport
from rainmapper_core import mushroom_gis_lab
from rainmapper_core import mushroom_learned_model
from rainmapper_core import mushroom_observation_context
from rainmapper_core import mushroom_observation_features


SCHEMA_VERSION = "0.1"
MAX_RESULT_FILE_BYTES = 64 * 1024 * 1024
MAX_RESULT_BUNDLE_BYTES = 256 * 1024 * 1024
VERIFICATION_NAME = "candidate_verification.json"
PROMOTION_RECEIPT_NAME = "promotion_receipt.json"
MAX_RETAINED_PROMOTION_BACKUPS = 2


def _json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object.")
    return payload


def _row_id(row: dict[str, Any], key: str) -> str:
    return str(row.get(key, "") or "").strip()


def _merge_selected_rows(
    live_payload: dict[str, Any],
    candidate_payload: dict[str, Any],
    *,
    rows_key: str,
    identity_key: str,
    selected_ids: set[str],
    label: str,
) -> list[dict[str, Any]]:
    live_rows = live_payload.get(rows_key)
    candidate_rows = candidate_payload.get(rows_key)
    if not isinstance(live_rows, list) or not isinstance(candidate_rows, list):
        raise ValueError(f"Partial promotion requires row lists in {label}.")
    live = [dict(row) for row in live_rows if isinstance(row, dict)]
    candidate = [dict(row) for row in candidate_rows if isinstance(row, dict)]
    candidate_selected = {
        _row_id(row, identity_key): row
        for row in candidate
        if _row_id(row, identity_key) in selected_ids
    }
    missing = sorted(selected_ids - set(candidate_selected))
    if missing:
        raise ValueError(f"Partial candidate {label} is missing selected row {missing[0]}.")
    merged: list[dict[str, Any]] = []
    inserted: set[str] = set()
    for row in live:
        row_id = _row_id(row, identity_key)
        if row_id in selected_ids:
            merged.append(candidate_selected[row_id])
            inserted.add(row_id)
        else:
            merged.append(row)
    for row in candidate:
        row_id = _row_id(row, identity_key)
        if row_id in selected_ids and row_id not in inserted:
            merged.append(row)
            inserted.add(row_id)
    return merged


def _merge_partial_candidate_outputs(
    candidate_root: Path,
    live_outputs: mushroom_rebuild_pipeline.RebuildOutputPaths,
    staged_outputs: mushroom_rebuild_pipeline.RebuildOutputPaths,
    job_spec: dict[str, Any],
) -> dict[str, int]:
    """Build a full, promotable artifact set from one verified partial candidate."""
    scope = job_spec.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("Partial candidate job scope is invalid.")
    selected_ids = {
        str(value).strip()
        for value in scope.get("selected_observation_ids", [])
        if str(value or "").strip()
    }
    species_ids = {
        str(value).strip()
        for value in scope.get("pending_species_ids", [])
        if str(value or "").strip()
    }
    if not selected_ids or not species_ids:
        raise ValueError("Partial candidate scope is empty.")
    for field in mushroom_rebuild_pipeline.ACCEPTED_OUTPUT_FIELDS:
        if not Path(getattr(live_outputs, field)).is_file():
            raise FileNotFoundError(
                f"Partial promotion requires an existing full model artifact: {getattr(live_outputs, field)}"
            )

    live_gis = _json_object(live_outputs.gis_reconstruction, "live GIS artifact")
    candidate_gis = _json_object(candidate_root / "mushroom_gis_observation_reconstruction.json", "candidate GIS artifact")
    gis_rows = _merge_selected_rows(
        live_gis,
        candidate_gis,
        rows_key="results",
        identity_key="observation_id",
        selected_ids=selected_ids,
        label="GIS artifact",
    )
    merged_gis = dict(live_gis)
    merged_gis["generated_at"] = candidate_gis.get("generated_at", live_gis.get("generated_at"))
    merged_gis["selected_observation_ids"] = [
        _row_id(row, "observation_id") for row in gis_rows if _row_id(row, "observation_id")
    ]
    merged_gis["result_count"] = len(gis_rows)
    merged_gis["results"] = gis_rows
    merged_gis["unmapped_candidates"] = mushroom_gis_lab.collect_unmapped_candidates(gis_rows)
    staged_outputs.gis_reconstruction.parent.mkdir(parents=True, exist_ok=True)
    staged_outputs.gis_reconstruction.write_text(
        json.dumps(merged_gis, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    live_weather = _json_object(live_outputs.weather_json, "live weather artifact")
    candidate_weather = _json_object(candidate_root / "mushroom_observations_weather_features.json", "candidate weather artifact")
    weather_rows = _merge_selected_rows(
        live_weather,
        candidate_weather,
        rows_key="rows",
        identity_key="observation_id",
        selected_ids=selected_ids,
        label="weather artifact",
    )
    merged_weather = dict(live_weather)
    for key in (
        "generated_at",
        "prediction_target_policy",
        "weather_method",
        "weather_summary_window_days",
        "rain_windows_days",
        "source_files",
    ):
        if key in candidate_weather:
            merged_weather[key] = candidate_weather[key]
    weather_summary = dict(
        candidate_weather.get("summary")
        if isinstance(candidate_weather.get("summary"), dict)
        else {}
    )
    weather_summary.update(
        {
            "observations": len(weather_rows),
            "with_weather_station": sum(bool(row.get("weather_station_code")) for row in weather_rows),
            "with_gaps": sum(bool(row.get("data_gaps")) for row in weather_rows),
        }
    )
    merged_weather["summary"] = weather_summary
    merged_weather["rows"] = weather_rows
    merged_weather["output_paths"] = {
        "json": str(live_outputs.weather_json),
        "csv": str(live_outputs.weather_csv),
        "report": str(live_outputs.weather_report),
    }
    mushroom_observation_context.write_json(staged_outputs.weather_json, merged_weather)
    mushroom_observation_context.write_csv(staged_outputs.weather_csv, weather_rows)
    mushroom_observation_context.write_report(staged_outputs.weather_report, merged_weather)

    live_features = _json_object(live_outputs.features_json, "live features artifact")
    candidate_features = _json_object(candidate_root / "mushroom_observation_features_v0.json", "candidate features artifact")
    feature_rows = _merge_selected_rows(
        live_features,
        candidate_features,
        rows_key="rows",
        identity_key="observation_id",
        selected_ids=selected_ids,
        label="features artifact",
    )
    merged_features = dict(live_features)
    for key in ("generated_at", "prediction_target_policy"):
        if key in candidate_features:
            merged_features[key] = candidate_features[key]
    merged_features["summary"] = {
        "observations": len(feature_rows),
        "with_weather": len(feature_rows),
        "with_gis": sum("missing_gis_reconstruction" not in (row.get("feature_gaps") or []) for row in feature_rows),
        "with_weather_gaps": sum(bool(row.get("weather_gaps")) for row in feature_rows),
        "with_gis_or_feature_gaps": sum(bool(row.get("gis_gaps") or row.get("feature_gaps")) for row in feature_rows),
    }
    merged_features["rows"] = feature_rows
    merged_features["output_paths"] = {
        "json": str(live_outputs.features_json),
        "csv": str(live_outputs.features_csv),
        "report": str(live_outputs.features_report),
    }
    mushroom_observation_features.write_json(staged_outputs.features_json, merged_features)
    mushroom_observation_features.write_csv(staged_outputs.features_csv, feature_rows)
    mushroom_observation_features.write_report(staged_outputs.features_report, merged_features)

    live_model = _json_object(live_outputs.model_json, "live model artifact")
    candidate_model = _json_object(candidate_root / "mushroom_model_v0.json", "candidate model artifact")
    live_models = live_model.get("species_models")
    candidate_models = candidate_model.get("species_models")
    if not isinstance(live_models, list) or not isinstance(candidate_models, list):
        raise ValueError("Partial promotion requires species model lists.")
    model_by_species = {
        _row_id(model, "species_id"): dict(model)
        for model in live_models
        if isinstance(model, dict) and _row_id(model, "species_id")
    }
    replacements = {
        _row_id(model, "species_id"): dict(model)
        for model in candidate_models
        if isinstance(model, dict) and _row_id(model, "species_id") in species_ids
    }
    for species_id in species_ids:
        if species_id in replacements:
            model_by_species[species_id] = replacements[species_id]
        else:
            model_by_species.pop(species_id, None)
    merged_models = [model_by_species[key] for key in sorted(model_by_species)]
    training_count = sum(int(model.get("observation_count", 0) or 0) for model in merged_models)
    favorable_count = sum(
        int(model.get("favorable_count", model.get("positive_count", 0)) or 0)
        for model in merged_models
    )
    unfavorable_count = sum(
        int(model.get("unfavorable_count", model.get("negative_count", 0)) or 0)
        for model in merged_models
    )
    merged_model = dict(live_model)
    for key in (
        "schema_version",
        "generated_at",
        "model_status",
        "prediction_target_policy",
        "model_notes",
        "feature_contract",
    ):
        if key in candidate_model:
            merged_model[key] = candidate_model[key]
    merged_model["scope"] = {"species_id": None}
    merged_model["summary"] = {
        "observations": training_count,
        "source_observations": len(feature_rows),
        "excluded_observations": max(0, len(feature_rows) - training_count),
        "species": len(merged_models),
        "favorable_observations": favorable_count,
        "unfavorable_observations": unfavorable_count,
        "positive_observations": favorable_count,
        "negative_observations": unfavorable_count,
    }
    merged_model["species_models"] = merged_models
    merged_model["last_partial_rebuild"] = {
        "species_ids": sorted(species_ids),
        "generated_at": merged_model.get("generated_at"),
    }
    merged_model["output_paths"] = {
        "json": str(live_outputs.model_json),
        "report": str(live_outputs.model_report),
    }
    mushroom_learned_model.write_json(staged_outputs.model_json, merged_model)
    mushroom_learned_model.write_report(staged_outputs.model_report, merged_model)
    return {
        "selected_observations": len(selected_ids),
        "updated_species": len(species_ids),
        "model_species": len(merged_models),
    }


def _rebase_promoted_metadata(
    staged_outputs: mushroom_rebuild_pipeline.RebuildOutputPaths,
    live_outputs: mushroom_rebuild_pipeline.RebuildOutputPaths,
    *,
    observations_path: Path,
    reference_catalogs_path: Path,
    weather_data_dir: Path,
    gis_root: Path,
) -> list[str]:
    """Replace worker-private filesystem metadata with coordinator live paths."""
    changed: list[str] = []

    def persist_if_changed(path: Path, before: dict[str, Any], after: dict[str, Any]) -> None:
        if after == before:
            return
        path.write_text(json.dumps(after, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed.append(path.relative_to(staged_outputs.root).as_posix())

    def rebase_catalog_policy(payload: dict[str, Any]) -> None:
        policy = payload.get("prediction_target_policy")
        if isinstance(policy, dict) and "catalog_path" in policy:
            policy["catalog_path"] = str(reference_catalogs_path.resolve())

    gis_path = staged_outputs.gis_reconstruction
    gis_before = _json_object(gis_path, "staged GIS artifact")
    gis = json.loads(json.dumps(gis_before))
    gis.pop("qgis_points_path", None)
    gis.pop("qgis_points_host_path", None)
    authoritative_sources = {
        layer.source_id: str(layer.path.resolve())
        for layer in mushroom_gis_lab.vector_layers(gis_root.resolve())
    }
    authoritative_sources["dem_5m"] = str(mushroom_gis_lab.dem_path(gis_root.resolve()).resolve())
    results = gis.get("results")
    if isinstance(results, list):
        for result in results:
            if not isinstance(result, dict) or not isinstance(result.get("layers"), dict):
                continue
            for source_id, layer in result["layers"].items():
                if isinstance(layer, dict) and "source" in layer and source_id in authoritative_sources:
                    layer["source"] = authoritative_sources[source_id]
    persist_if_changed(gis_path, gis_before, gis)

    weather_path = staged_outputs.weather_json
    weather_before = _json_object(weather_path, "staged weather artifact")
    weather = json.loads(json.dumps(weather_before))
    if isinstance(weather.get("input_paths"), dict):
        weather["input_paths"] = {
            "observations": str(observations_path.resolve()),
            "weather_data_dir": str(weather_data_dir.resolve()),
            "reference_catalogs": str(reference_catalogs_path.resolve()),
        }
    weather_files = {
        source_id: filename
        for source_id, filename in mushroom_observation_context.DAILY_INCREMENTAL_FILES
    }
    source_files = weather.get("source_files")
    if isinstance(source_files, list):
        for row in source_files:
            if not isinstance(row, dict) or "path" not in row:
                continue
            filename = weather_files.get(str(row.get("source", "")))
            if filename:
                row["path"] = str((weather_data_dir.resolve() / filename))
    rebase_catalog_policy(weather)
    if isinstance(weather.get("output_paths"), dict):
        weather["output_paths"] = {
            "json": str(live_outputs.weather_json),
            "csv": str(live_outputs.weather_csv),
            "report": str(live_outputs.weather_report),
        }
    persist_if_changed(weather_path, weather_before, weather)

    features_path = staged_outputs.features_json
    features_before = _json_object(features_path, "staged features artifact")
    features = json.loads(json.dumps(features_before))
    if isinstance(features.get("input_paths"), dict):
        features["input_paths"] = {
            "weather_features": str(live_outputs.weather_json),
            "gis_reconstruction": str(live_outputs.gis_reconstruction),
        }
    rebase_catalog_policy(features)
    if isinstance(features.get("output_paths"), dict):
        features["output_paths"] = {
            "json": str(live_outputs.features_json),
            "csv": str(live_outputs.features_csv),
            "report": str(live_outputs.features_report),
        }
    persist_if_changed(features_path, features_before, features)

    model_path = staged_outputs.model_json
    model_before = _json_object(model_path, "staged model artifact")
    model = json.loads(json.dumps(model_before))
    if isinstance(model.get("input_paths"), dict):
        model["input_paths"] = {"observation_features_v0": str(live_outputs.features_json)}
    rebase_catalog_policy(model)
    if isinstance(model.get("output_paths"), dict):
        model["output_paths"] = {
            "json": str(live_outputs.model_json),
            "report": str(live_outputs.model_report),
        }
    persist_if_changed(model_path, model_before, model)
    return changed


def _job_dir(root: Path, job_id: str) -> Path:
    return root.resolve() / mushroom_worker_transport.validate_job_id(job_id)


def _staging_dir(root: Path, job_id: str) -> Path:
    return root.resolve() / f".{mushroom_worker_transport.validate_job_id(job_id)}.staging"


def _load_job_spec(input_bundle_root: Path, job_id: str) -> dict[str, Any]:
    return mushroom_rebuild_contracts.load_job_spec(
        input_bundle_root.resolve() / job_id / mushroom_worker_transport.JOB_SPEC_LOGICAL_PATH
    )


def _load_result_manifest(path: Path) -> dict[str, Any]:
    return mushroom_rebuild_contracts.load_result_manifest(path)


def _artifact_record(manifest: dict[str, Any], logical_path: str) -> dict[str, Any]:
    records = manifest.get("artifacts")
    if not isinstance(records, list):
        raise ValueError("Candidate result manifest artifacts must be a list.")
    matches = [row for row in records if isinstance(row, dict) and row.get("path") == logical_path]
    if len(matches) != 1:
        raise ValueError("Candidate result file is not declared exactly once.")
    return dict(matches[0])


def _write_exact(path: Path, content: bytes, *, expected_size: int, expected_sha256: str) -> None:
    if len(content) != expected_size:
        raise ValueError("Candidate result file size does not match its manifest.")
    if len(content) > MAX_RESULT_FILE_BYTES:
        raise ValueError("Candidate result file exceeds the coordinator safety limit.")
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("Candidate result file hash does not match its manifest.")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("Candidate result upload conflicts with an existing file.")
        return
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def receive_result_file(
    result_root: Path,
    input_bundle_root: Path,
    *,
    job_id: str,
    logical_path: str,
    content: bytes,
) -> dict[str, Any]:
    """Persist one idempotent result file in coordinator-side staging."""
    safe_path = mushroom_worker_transport.safe_relative_path(logical_path).as_posix()
    if safe_path not in {
        mushroom_rebuild_contracts.RESULT_MANIFEST_NAME,
        *mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS,
    }:
        raise ValueError("Candidate result path is not allowed.")
    final = _job_dir(result_root, job_id)
    if final.exists():
        raise ValueError("Candidate result has already been finalized.")
    staging = _staging_dir(result_root, job_id)
    staging.mkdir(parents=True, exist_ok=True)
    job_spec = _load_job_spec(input_bundle_root, job_id)
    manifest_path = staging / mushroom_rebuild_contracts.RESULT_MANIFEST_NAME

    if safe_path == mushroom_rebuild_contracts.RESULT_MANIFEST_NAME:
        if len(content) > mushroom_worker_transport.MAX_JSON_BYTES:
            raise ValueError("Candidate result manifest exceeds the safety limit.")
        try:
            manifest = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Candidate result manifest is not valid JSON.") from exc
        if not isinstance(manifest, dict):
            raise ValueError("Candidate result manifest must contain a JSON object.")
        errors = mushroom_rebuild_contracts.result_manifest_contract_errors(manifest, job_spec)
        if errors:
            raise ValueError(f"Candidate result manifest contract is invalid: {errors[0]}")
        total_size = sum(int(row.get("size_bytes", 0)) for row in manifest["artifacts"])
        if total_size > MAX_RESULT_BUNDLE_BYTES:
            raise ValueError("Candidate result bundle exceeds the coordinator safety limit.")
        digest = hashlib.sha256(content).hexdigest()
        _write_exact(manifest_path, content, expected_size=len(content), expected_sha256=digest)
        return {
            "status": "manifest_received",
            "result_manifest_id": manifest.get("result_manifest_id"),
            "expected_artifacts": len(manifest["artifacts"]),
            "expected_size_bytes": total_size,
        }

    if not manifest_path.is_file():
        raise ValueError("Candidate result manifest must be uploaded first.")
    manifest = _load_result_manifest(manifest_path)
    record = _artifact_record(manifest, safe_path)
    _write_exact(
        staging / safe_path,
        content,
        expected_size=int(record["size_bytes"]),
        expected_sha256=str(record["sha256"]),
    )
    return {
        "status": "artifact_received",
        "path": safe_path,
        "size_bytes": len(content),
    }


def finalize_candidate_result(
    result_root: Path,
    input_bundle_root: Path,
    live_artifact_root: Path,
    *,
    job_id: str,
) -> dict[str, Any]:
    final = _job_dir(result_root, job_id)
    if final.is_dir():
        verification_path = final / VERIFICATION_NAME
        payload = json.loads(verification_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Stored candidate verification is invalid.")
        return {**payload, "status": "reused"}
    staging = _staging_dir(result_root, job_id)
    job_spec = _load_job_spec(input_bundle_root, job_id)
    manifest = _load_result_manifest(staging / mushroom_rebuild_contracts.RESULT_MANIFEST_NAME)
    verification = mushroom_rebuild_contracts.verify_result_manifest(manifest, job_spec, staging)
    if verification["status"] != "valid":
        raise ValueError(f"Candidate result verification failed: {verification['errors']}")
    comparison = mushroom_rebuild_comparison.compare_artifact_dirs(
        live_artifact_root.resolve(),
        staging,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "rainmapper_worker_candidate_verification",
        "status": "verified",
        "job_id": job_id,
        "result_manifest_id": manifest.get("result_manifest_id"),
        "verified_artifacts": verification.get("verified_artifacts"),
        "comparison_status": comparison.get("status"),
        "summary": manifest.get("summary"),
        "duration_seconds": manifest.get("duration_seconds"),
    }
    (staging / VERIFICATION_NAME).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    staging.replace(final)
    return report


def load_final_candidate(result_root: Path, job_id: str) -> dict[str, Any]:
    payload = json.loads((_job_dir(result_root, job_id) / VERIFICATION_NAME).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != "rainmapper_worker_candidate_verification":
        raise ValueError("Stored candidate verification is invalid.")
    if payload.get("status") != "verified":
        raise ValueError("Stored candidate result is not verified.")
    return payload


def discard_candidate_staging(result_root: Path, job_id: str) -> bool:
    """Remove only an unfinished coordinator staging area for one known job."""
    staging = _staging_dir(result_root, job_id)
    if not staging.exists():
        return False
    if not staging.is_dir():
        raise ValueError("Candidate result staging path is not a directory.")
    if staging.is_symlink():
        raise ValueError("Refusing to discard symlinked candidate staging.")
    shutil.rmtree(staging)
    return True


def discard_candidate(
    result_root: Path,
    live_artifact_root: Path,
    *,
    job_id: str,
) -> dict[str, bool]:
    """Remove an unpromoted candidate while preserving live and rollback artifacts."""
    resolved_job_id = mushroom_worker_transport.validate_job_id(job_id)
    live_root = live_artifact_root.resolve()
    promotion_staging = live_root / ".worker-promotion-staging" / resolved_job_id
    promotion_backup = live_root / ".worker-promotion-backups" / resolved_job_id
    if promotion_staging.exists() or promotion_backup.exists():
        raise ValueError(
            "Candidate promotion recovery artifacts still exist; refusing to discard it automatically."
        )
    candidate = _job_dir(result_root, resolved_job_id)
    removed_candidate = False
    if candidate.exists():
        if not candidate.is_dir():
            raise ValueError("Candidate result path is not a directory.")
        if candidate.is_symlink():
            raise ValueError("Refusing to discard a symlinked candidate result.")
        if (candidate / PROMOTION_RECEIPT_NAME).exists():
            raise ValueError("A promoted candidate receipt exists; the candidate cannot be discarded.")
        verification = load_final_candidate(result_root, resolved_job_id)
        if verification.get("job_id") != resolved_job_id:
            raise ValueError("Refusing to discard a candidate with a different job identity.")
        shutil.rmtree(candidate)
        removed_candidate = True
    removed_staging = discard_candidate_staging(result_root, resolved_job_id)
    return {
        "candidate": removed_candidate,
        "staging": removed_staging,
    }


def discard_promoted_result(
    result_root: Path,
    *,
    job_id: str,
    job_type: str,
) -> bool:
    """Remove a promoted private result after validating its durable receipt."""
    resolved_job_id = mushroom_worker_transport.validate_job_id(job_id)
    if job_type == "worker_candidate_rebuild":
        candidate = _job_dir(result_root, resolved_job_id)
        expected_kind = "rainmapper_worker_candidate_promotion"
    elif job_type == "worker_ml_train_v0":
        candidate = _ml_train_job_dir(result_root, resolved_job_id)
        expected_kind = "rainmapper_worker_ml_train_promotion"
    else:
        raise ValueError("Only promoted rebuild or ML results can be discarded.")
    if not candidate.exists():
        return False
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("Refusing to discard an unsafe promoted result path.")
    receipt = _json_object(candidate / PROMOTION_RECEIPT_NAME, "promotion receipt")
    if (
        receipt.get("kind") != expected_kind
        or receipt.get("status") != "promoted"
        or receipt.get("job_id") != resolved_job_id
    ):
        raise ValueError("Refusing to discard a result without its matching promotion receipt.")
    shutil.rmtree(candidate)
    return True


def cleanup_promoted_results(
    result_root: Path,
    jobs: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Reconcile legacy promoted results while preserving pending candidates."""
    report: dict[str, list[str]] = {"discarded": [], "errors": []}
    for job in jobs:
        if not isinstance(job, dict) or job.get("promotion_status") != "promoted":
            continue
        job_id = str(job.get("job_id", ""))
        job_type = str(job.get("job_type", ""))
        if job_type not in {"worker_candidate_rebuild", "worker_ml_train_v0"}:
            continue
        try:
            if discard_promoted_result(
                result_root,
                job_id=job_id,
                job_type=job_type,
            ):
                report["discarded"].append(job_id)
        except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
            report["errors"].append(f"{job_id}: {exc}")
    return report


def prune_promotion_backups(
    live_artifact_root: Path,
    *,
    current_job_id: str,
    keep: int = MAX_RETAINED_PROMOTION_BACKUPS,
) -> list[str]:
    """Keep only the newest known promotion backups, always including current."""
    if keep < 1:
        raise ValueError("At least one promotion backup must be retained.")
    resolved_current = mushroom_worker_transport.validate_job_id(current_job_id)
    backup_root = live_artifact_root.resolve() / ".worker-promotion-backups"
    if not backup_root.is_dir():
        return []
    known: list[Path] = []
    for path in backup_root.iterdir():
        if not path.is_dir():
            continue
        try:
            mushroom_worker_transport.validate_job_id(path.name)
        except ValueError:
            continue
        known.append(path)
    known.sort(
        key=lambda path: (
            path.name == resolved_current,
            path.stat().st_mtime_ns,
            path.name,
        ),
        reverse=True,
    )
    removed: list[str] = []
    for path in known[keep:]:
        shutil.rmtree(path)
        removed.append(path.name)
    return removed


def promote_verified_candidate(
    result_root: Path,
    input_bundle_root: Path,
    live_artifact_root: Path,
    *,
    job_id: str,
    observations_path: Path,
    reference_catalogs_path: Path,
    gis_mappings_path: Path,
    weather_data_dir: Path,
    gis_root: Path,
    progress_callback: Callable[[int, str, str], None] | None = None,
) -> dict[str, Any]:
    """Freshness-check and atomically promote a verified external candidate."""
    def report(percent: int, phase: str, message: str = "") -> None:
        if progress_callback is not None:
            progress_callback(percent, phase, message)

    report(2, "Loading verified candidate", "Loading the private verified result.")
    candidate = _job_dir(result_root, job_id)
    receipt_path = candidate / PROMOTION_RECEIPT_NAME
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or receipt.get("status") != "promoted":
            raise ValueError("Stored candidate promotion receipt is invalid.")
        report(99, "Promotion receipt already exists", "Reusing the completed promotion receipt.")
        return {**receipt, "status": "reused"}
    load_final_candidate(result_root, job_id)
    job_dir = input_bundle_root.resolve() / mushroom_worker_transport.validate_job_id(job_id)
    job_spec = _load_job_spec(input_bundle_root, job_id)
    manifest = _load_result_manifest(candidate / mushroom_rebuild_contracts.RESULT_MANIFEST_NAME)
    report(8, "Revalidating candidate artifacts", "Checking the result manifest and candidate hashes.")
    verification = mushroom_rebuild_contracts.verify_result_manifest(manifest, job_spec, candidate)
    if verification.get("status") != "valid":
        raise ValueError(f"Candidate changed after verification: {verification.get('errors', [])}")
    input_manifest = mushroom_rebuild_snapshot.load_manifest(
        job_dir / mushroom_worker_transport.SNAPSHOT_PREFIX
    )

    def report_freshness(completed: int, total: int, logical_path: str) -> None:
        ratio = completed / max(1, total)
        percent = 12 + round(ratio * 60)
        detail = f"Checking {logical_path}." if logical_path else "Checking authoritative inputs."
        report(percent, f"Validating live inputs ({completed}/{total})", detail)

    report(12, "Validating live inputs", "Checking that authoritative inputs have not changed.")
    freshness = mushroom_rebuild_snapshot.verify_live_inputs(
        input_manifest,
        observations_path=observations_path,
        reference_catalogs_path=reference_catalogs_path,
        gis_mappings_path=gis_mappings_path,
        weather_data_dir=weather_data_dir,
        gis_root=gis_root,
        gis_hash_cache_path=input_bundle_root.resolve() / ".gis-hash-cache.json",
        progress_callback=report_freshness,
    )
    if freshness.get("status") != "valid":
        raise ValueError(f"Candidate inputs are stale: {freshness.get('errors', [])}")

    live_root = live_artifact_root.resolve()
    staging = live_root / ".worker-promotion-staging" / mushroom_worker_transport.validate_job_id(job_id)
    backup = live_root / ".worker-promotion-backups" / mushroom_worker_transport.validate_job_id(job_id)
    if staging.exists() or backup.exists():
        raise FileExistsError("Candidate promotion staging or backup already exists.")
    staged_outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(staging)
    final_outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(live_root)
    promoted = False
    partial_merge: dict[str, int] | None = None
    try:
        report(76, "Preparing atomic promotion", "Preparing the complete artifact set in staging.")
        scope = job_spec.get("scope") if isinstance(job_spec.get("scope"), dict) else {}
        reconstruction_scope = str(scope.get("reconstruction_scope", "all"))
        if reconstruction_scope in {"species", "pending"}:
            partial_merge = _merge_partial_candidate_outputs(
                candidate,
                final_outputs,
                staged_outputs,
                job_spec,
            )
        else:
            for relative in mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS:
                source = candidate / relative
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        rebased_metadata = _rebase_promoted_metadata(
            staged_outputs,
            final_outputs,
            observations_path=observations_path,
            reference_catalogs_path=reference_catalogs_path,
            weather_data_dir=weather_data_dir,
            gis_root=gis_root,
        )
        report(90, "Installing verified artifacts", "Replacing the live artifact set atomically.")
        promotion = mushroom_rebuild_pipeline.promote_rebuild_outputs(staged_outputs, final_outputs)
        promoted = True
        rollback = staging / ".rollback"
        backup.parent.mkdir(parents=True, exist_ok=True)
        if rollback.is_dir():
            rollback.replace(backup)
        else:
            backup.mkdir()
        report(96, "Preserving rollback copy", "Retaining the previous live artifact set.")
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "kind": "rainmapper_worker_candidate_promotion",
            "status": "promoted",
            "job_id": job_id,
            "snapshot_id": freshness.get("snapshot_id"),
            "dataset_fingerprint": freshness.get("dataset_fingerprint"),
            "result_manifest_id": manifest.get("result_manifest_id"),
            "artifact_count": promotion.get("artifact_count"),
            "reconstruction_scope": reconstruction_scope,
            "partial_merge": partial_merge or {},
            "rebased_metadata": rebased_metadata,
            "backup_path": str(backup.relative_to(live_root)),
            "backup_retention_limit": MAX_RETAINED_PROMOTION_BACKUPS,
        }
        removed_backups = prune_promotion_backups(
            live_root,
            current_job_id=job_id,
        )
        receipt["pruned_backup_count"] = len(removed_backups)
        report(99, "Writing promotion receipt", "Recording the completed promotion.")
        temporary = candidate / f".{PROMOTION_RECEIPT_NAME}.{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("x", encoding="utf-8") as handle:
                json.dump(receipt, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(receipt_path)
        finally:
            temporary.unlink(missing_ok=True)
        return receipt
    except BaseException:
        if promoted:
            rollback_root = backup if backup.is_dir() else staging / ".rollback"
            rollback_errors: list[str] = []
            for field in reversed(mushroom_rebuild_pipeline.ACCEPTED_OUTPUT_FIELDS):
                destination = Path(getattr(final_outputs, field))
                relative = destination.relative_to(live_root)
                previous = rollback_root / relative
                try:
                    if previous.is_file():
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(previous, destination)
                    else:
                        destination.unlink(missing_ok=True)
                except OSError as exc:
                    rollback_errors.append(f"{relative}: {exc}")
            if rollback_errors:
                raise RuntimeError(
                    "external candidate promotion failed and rollback was incomplete: "
                    + "; ".join(rollback_errors)
                )
            shutil.rmtree(backup, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _post_bytes(
    url: str,
    content: bytes,
    *,
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    request = Request(url, data=content, headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("Rainmapper result upload response is too large.")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise ValueError("Rainmapper rejected the candidate result upload.")
    return payload


def upload_candidate_result(
    ha_url: str,
    job: dict[str, Any],
    worker_job_dir: Path,
    *,
    worker_id: str,
    claim_token: str,
    token: str,
    timeout: float = 30.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    job_id = mushroom_worker_transport.validate_job_id(str(job.get("job_id", "")))
    endpoint = str(job.get("result_endpoint", "") or "")
    complete_endpoint = str(job.get("result_complete_endpoint", "") or "")
    if endpoint != "/api/mushrooms/workers/jobs/result-file":
        raise ValueError("Worker candidate result endpoint is invalid.")
    if complete_endpoint != "/api/mushrooms/workers/jobs/result-complete":
        raise ValueError("Worker candidate completion endpoint is invalid.")
    output_dir = worker_job_dir.resolve() / "candidate"
    job_spec = mushroom_rebuild_contracts.load_job_spec(
        worker_job_dir.resolve() / mushroom_worker_transport.JOB_SPEC_LOGICAL_PATH
    )
    manifest_path = output_dir / mushroom_rebuild_contracts.RESULT_MANIFEST_NAME
    manifest = mushroom_rebuild_contracts.load_result_manifest(manifest_path)
    local_verification = mushroom_rebuild_contracts.verify_result_manifest(
        manifest,
        job_spec,
        output_dir,
    )
    if local_verification["status"] != "valid":
        raise RuntimeError("Worker candidate result failed local verification.")
    headers = mushroom_worker_transport.request_headers(worker_id, claim_token, token)
    headers["Content-Type"] = "application/octet-stream"

    files = [mushroom_rebuild_contracts.RESULT_MANIFEST_NAME, *mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS]
    for index, logical_path in enumerate(files, start=1):
        content = (output_dir / logical_path).read_bytes()
        query = urlencode({"job_id": job_id, "file": logical_path})
        _post_bytes(
            ha_url.rstrip("/") + endpoint + "?" + query,
            content,
            headers=headers,
            timeout=timeout,
        )
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "Uploading candidate result",
                    "message": f"Uploaded result file {index}/{len(files)}.",
                    "overall_percent": 90 + int((index / len(files)) * 8),
                }
            )

    complete_headers = dict(headers)
    complete_headers["Content-Type"] = "application/json"
    payload = json.dumps(
        {"job_id": job_id, "worker_id": worker_id, "claim_token": claim_token},
        ensure_ascii=False,
    ).encode("utf-8")
    completed = _post_bytes(
        ha_url.rstrip("/") + complete_endpoint,
        payload,
        headers=complete_headers,
        timeout=timeout,
    )
    verification = completed.get("verification")
    if not isinstance(verification, dict) or verification.get("status") not in {"verified", "reused"}:
        raise ValueError("Rainmapper did not verify the uploaded candidate result.")
    return dict(verification)


# ── ML training result handling ────────────────────────────────────────────

ML_TRAIN_RESULT_NAME = "ml_train_result.json"
ML_TRAIN_RESULT_SCHEMA_VERSION = "0.2"
ML_TRAIN_REPORT_NAME = "ml_train_report.json"
MAX_ML_TRAIN_MODEL_BYTES = 256 * 1024 * 1024
MAX_ML_TRAIN_BUNDLE_BYTES = 1024 * 1024 * 1024


def _ml_train_staging_dir(result_root: Path, job_id: str) -> Path:
    return result_root.resolve() / f".ml.{mushroom_worker_transport.validate_job_id(job_id)}.staging"


def _ml_train_job_dir(result_root: Path, job_id: str) -> Path:
    return result_root.resolve() / f"ml.{mushroom_worker_transport.validate_job_id(job_id)}"


def _validate_ml_train_report(content: bytes) -> dict[str, Any]:
    if len(content) > mushroom_worker_transport.MAX_JSON_BYTES:
        raise ValueError("ML training report exceeds the safety limit.")
    try:
        report = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("ML training report is not valid JSON.") from exc
    if not isinstance(report, dict):
        raise ValueError("ML training report must contain a JSON object.")
    if report.get("schema_version") != "0.1" or report.get("kind") != "mushroom_ml_v0_report":
        raise ValueError("ML training report contract is invalid.")
    if not isinstance(report.get("species_results"), list):
        raise ValueError("ML training report species_results are missing.")
    return report


def _validate_ml_train_manifest(
    manifest: object,
    *,
    job_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict):
        raise ValueError("ML training result manifest must contain a JSON object.")
    if manifest.get("schema_version") != ML_TRAIN_RESULT_SCHEMA_VERSION:
        raise ValueError("ML training result manifest schema_version is invalid.")
    if manifest.get("kind") != "mushroom_ml_v0_result":
        raise ValueError("ML training result manifest kind is invalid.")
    if manifest.get("job_id") != job_id:
        raise ValueError("ML training result manifest job_id does not match the upload.")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("ML training result manifest artifacts must be a list.")
    normalized: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    report_count = 0
    for row in artifacts:
        if not isinstance(row, dict):
            raise ValueError("ML training result manifest artifact entry is invalid.")
        safe_path = mushroom_worker_transport.safe_relative_path(
            str(row.get("path", ""))
        ).as_posix()
        if safe_path in seen_paths:
            raise ValueError(f"ML training result artifact is declared more than once: {safe_path}")
        seen_paths.add(safe_path)
        try:
            size_bytes = int(row.get("size_bytes", -1))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"ML training artifact size is invalid: {safe_path}") from exc
        sha256 = str(row.get("sha256", ""))
        if size_bytes < 0 or len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
            raise ValueError(f"ML training artifact metadata is invalid: {safe_path}")
        if safe_path == ML_TRAIN_REPORT_NAME:
            report_count += 1
            if size_bytes > mushroom_worker_transport.MAX_JSON_BYTES:
                raise ValueError("ML training report exceeds the safety limit.")
        elif (
            Path(safe_path).parent == Path("ml_models")
            and (
                Path(safe_path).name.startswith("mushroom_ml_v0_")
                or Path(safe_path).name.startswith("mushroom_ml_experiment_fixed_gap_7d_v1_")
                or Path(safe_path).name.startswith("mushroom_ml_experiment_lag_event_v1_")
                or Path(safe_path).name.startswith("mushroom_ml_experiment_fixed_gap_7d_altitude_v2_")
                or Path(safe_path).name.startswith("mushroom_ml_experiment_lag_event_altitude_v2_")
            )
            and safe_path.endswith(".joblib")
        ):
            if size_bytes > MAX_ML_TRAIN_MODEL_BYTES:
                raise ValueError(f"ML training model exceeds the safety limit: {safe_path}")
        else:
            raise ValueError("ML training result artifact path is not allowed.")
        normalized.append({**row, "path": safe_path, "size_bytes": size_bytes, "sha256": sha256})
    if report_count != 1:
        raise ValueError("ML training result must contain exactly one training report.")
    trained_species = manifest.get("trained_species")
    if not isinstance(trained_species, list):
        raise ValueError("ML training result trained_species is invalid.")
    normalized_species = [str(value).strip() for value in trained_species]
    if (
        any(
            not value or any(not (character.isalnum() or character in "_-") for character in value)
            for value in normalized_species
        )
        or len(set(normalized_species)) != len(normalized_species)
    ):
        raise ValueError("ML training result trained_species contains invalid values.")
    expected_models = {
        f"ml_models/mushroom_ml_v0_{species_id}.joblib"
        for species_id in normalized_species
    }
    actual_operational_models = {
        str(row["path"])
        for row in normalized
        if Path(str(row["path"])).name.startswith("mushroom_ml_v0_")
    }
    if actual_operational_models != expected_models:
        raise ValueError("ML training result models do not match trained_species.")
    shadow_models = manifest.get("shadow_models", [])
    if not isinstance(shadow_models, list):
        raise ValueError("ML training result shadow_models is invalid.")
    normalized_shadow_models = [
        mushroom_worker_transport.safe_relative_path(str(value)).as_posix()
        for value in shadow_models
    ]
    if len(set(normalized_shadow_models)) != len(normalized_shadow_models):
        raise ValueError("ML training result shadow_models contains duplicates.")
    actual_shadow_models = {
        str(row["path"])
        for row in normalized
        if Path(str(row["path"])).name.startswith("mushroom_ml_experiment_")
    }
    if actual_shadow_models != set(normalized_shadow_models):
        raise ValueError("ML training result shadow models do not match the manifest.")
    for shadow_path in normalized_shadow_models:
        if not any(shadow_path.endswith(f"_{species_id}.joblib") for species_id in normalized_species):
            raise ValueError("ML training shadow model does not match trained_species.")
    total_size = sum(int(row["size_bytes"]) for row in normalized)
    if total_size > MAX_ML_TRAIN_BUNDLE_BYTES:
        raise ValueError("ML training result bundle exceeds the coordinator safety limit.")
    return normalized


def receive_ml_train_result_file(
    result_root: Path,
    *,
    job_id: str,
    logical_path: str,
    content: bytes,
) -> dict[str, Any]:
    """Persist one idempotent ML training result file in coordinator-side staging."""
    safe_path = mushroom_worker_transport.safe_relative_path(logical_path).as_posix()
    final = _ml_train_job_dir(result_root, job_id)
    if final.exists():
        raise ValueError("ML training result has already been finalized.")
    staging = _ml_train_staging_dir(result_root, job_id)
    staging.mkdir(parents=True, exist_ok=True)
    manifest_path = staging / ML_TRAIN_RESULT_NAME

    if safe_path == ML_TRAIN_RESULT_NAME:
        if len(content) > mushroom_worker_transport.MAX_JSON_BYTES:
            raise ValueError("ML training result manifest exceeds the safety limit.")
        try:
            manifest = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("ML training result manifest is not valid JSON.") from exc
        artifacts = _validate_ml_train_manifest(manifest, job_id=job_id)
        total_size = sum(int(row["size_bytes"]) for row in artifacts)
        digest = hashlib.sha256(content).hexdigest()
        _write_exact(manifest_path, content, expected_size=len(content), expected_sha256=digest)
        return {
            "status": "manifest_received",
            "result_manifest_id": f"sha256:{digest}",
            "expected_artifacts": len(artifacts),
            "expected_size_bytes": total_size,
        }

    if not manifest_path.is_file():
        raise ValueError("ML training result manifest must be uploaded first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = _validate_ml_train_manifest(manifest, job_id=job_id)
    matches = [
        row for row in artifacts
        if isinstance(row, dict) and row.get("path") == safe_path
    ]
    if len(matches) != 1:
        raise ValueError("ML training result artifact is not declared exactly once in manifest.")
    record = matches[0]
    if safe_path == ML_TRAIN_REPORT_NAME:
        _validate_ml_train_report(content)
    _write_exact(
        staging / safe_path,
        content,
        expected_size=int(record["size_bytes"]),
        expected_sha256=str(record["sha256"]),
    )
    return {"status": "artifact_received", "path": safe_path, "size_bytes": len(content)}


def finalize_ml_train_result(result_root: Path, *, job_id: str) -> dict[str, Any]:
    """Verify staging completeness and move to final dir."""
    final = _ml_train_job_dir(result_root, job_id)
    verification_path = final / VERIFICATION_NAME
    if final.is_dir():
        payload = json.loads(verification_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Stored ML training verification is invalid.")
        return {**payload, "status": "reused"}
    staging = _ml_train_staging_dir(result_root, job_id)
    manifest_path = staging / ML_TRAIN_RESULT_NAME
    if not manifest_path.is_file():
        raise ValueError("ML training result manifest is missing.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("ML training result manifest is invalid.")
    artifacts = _validate_ml_train_manifest(manifest, job_id=job_id)
    trained_species = manifest.get("trained_species")
    if not isinstance(trained_species, list):
        raise ValueError("ML training result trained_species is invalid.")
    for row in artifacts:
        artifact_path = staging / str(row.get("path", ""))
        if not artifact_path.is_file():
            raise ValueError(f"ML training result artifact is missing: {row.get('path', '')}")
        actual_size = artifact_path.stat().st_size
        actual_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if actual_size != int(row.get("size_bytes", -1)):
            raise ValueError(f"ML training artifact size mismatch: {row.get('path', '')}")
        if actual_sha256 != str(row.get("sha256", "")):
            raise ValueError(f"ML training artifact hash mismatch: {row.get('path', '')}")
    report_payload = _validate_ml_train_report((staging / ML_TRAIN_REPORT_NAME).read_bytes())
    reported_species = {
        str(row.get("species_id", ""))
        for row in report_payload["species_results"]
        if isinstance(row, dict) and not row.get("skipped") and row.get("species_id")
    }
    if reported_species != {str(value) for value in trained_species}:
        raise ValueError("ML training report and result manifest disagree on trained species.")
    manifest_content = manifest_path.read_bytes()
    manifest_id = f"sha256:{hashlib.sha256(manifest_content).hexdigest()}"
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "rainmapper_worker_ml_train_verification",
        "status": "verified",
        "job_id": job_id,
        "result_manifest_id": manifest_id,
        "verified_artifacts": len(artifacts),
        "trained_species": trained_species,
        "trained_species_count": len(trained_species),
    }
    (staging / VERIFICATION_NAME).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    staging.replace(final)
    return report


def promote_ml_train_candidate(
    result_root: Path,
    ml_models_dir: Path,
    *,
    job_id: str,
    report_path: Path,
) -> dict[str, Any]:
    """Copy verified models and their matching report to the live data directory."""
    final = _ml_train_job_dir(result_root, job_id)
    receipt_path = final / PROMOTION_RECEIPT_NAME
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or receipt.get("status") != "promoted":
            raise ValueError("Stored ML training promotion receipt is invalid.")
        return {**receipt, "status": "reused"}
    verification_path = final / VERIFICATION_NAME
    if not verification_path.is_file():
        raise ValueError("ML training candidate has not been finalized.")
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    if not isinstance(verification, dict) or verification.get("status") != "verified":
        raise ValueError("ML training candidate is not verified.")
    manifest_path = final / ML_TRAIN_RESULT_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = _validate_ml_train_manifest(manifest, job_id=job_id)
    ml_models_dir = ml_models_dir.resolve()
    ml_models_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    promoted_files: list[str] = []
    ordered_artifacts = sorted(
        artifacts,
        key=lambda row: str(row["path"]) == ML_TRAIN_REPORT_NAME,
    )
    promotion_sources: list[tuple[Path, Path]] = []
    for row in ordered_artifacts:
        rel_path = str(row.get("path", ""))
        source = final / rel_path
        if not source.is_file():
            raise FileNotFoundError(f"ML training artifact missing during promotion: {rel_path}")
        if source.stat().st_size != int(row["size_bytes"]):
            raise ValueError(f"ML training artifact size mismatch during promotion: {rel_path}")
        source_content = source.read_bytes()
        if hashlib.sha256(source_content).hexdigest() != str(row["sha256"]):
            raise ValueError(f"ML training artifact hash mismatch during promotion: {rel_path}")
        if rel_path == ML_TRAIN_REPORT_NAME:
            _validate_ml_train_report(source_content)
            destination = report_path
        else:
            destination = ml_models_dir / source.name
        promotion_sources.append((source, destination))
    rollback_root = final / ".promotion-rollback"
    backups: dict[Path, Path | None] = {}
    promoted_destinations: list[Path] = []
    if rollback_root.exists():
        raise FileExistsError("ML promotion rollback staging already exists.")
    try:
        for _source, destination in promotion_sources:
            if destination.is_file():
                backup = rollback_root / destination.name
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
                backups[destination] = backup
            else:
                backups[destination] = None
        for source, destination in promotion_sources:
            temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}.tmp"
            try:
                shutil.copy2(source, temporary)
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            promoted_destinations.append(destination)
            promoted_files.append(destination.name)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "kind": "rainmapper_worker_ml_train_promotion",
            "status": "promoted",
            "job_id": job_id,
            "result_manifest_id": verification.get("result_manifest_id"),
            "promoted_files": promoted_files,
            "trained_species": verification.get("trained_species", []),
            "trained_species_count": len(verification.get("trained_species", [])),
        }
        temporary_receipt = final / f".{PROMOTION_RECEIPT_NAME}.{uuid.uuid4().hex}.tmp"
        try:
            with temporary_receipt.open("x", encoding="utf-8") as handle:
                json.dump(receipt, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary_receipt.replace(receipt_path)
        finally:
            temporary_receipt.unlink(missing_ok=True)
    except BaseException:
        rollback_errors: list[str] = []
        for destination in reversed(promoted_destinations):
            backup = backups[destination]
            try:
                if backup is None:
                    destination.unlink(missing_ok=True)
                else:
                    os.replace(backup, destination)
            except OSError as exc:
                rollback_errors.append(f"{destination.name}: {exc}")
        if rollback_errors:
            raise RuntimeError(
                "ML promotion failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            )
        raise
    finally:
        shutil.rmtree(rollback_root, ignore_errors=True)
    return receipt


def rollback_promoted_candidate(
    result_root: Path,
    live_artifact_root: Path,
    *,
    job_id: str,
) -> dict[str, Any]:
    """Restore the retained pre-promotion artifact set for a linked failure."""
    resolved_job_id = mushroom_worker_transport.validate_job_id(job_id)
    candidate = _job_dir(result_root, resolved_job_id)
    receipt_path = candidate / PROMOTION_RECEIPT_NAME
    receipt = _json_object(receipt_path, "candidate promotion receipt")
    if receipt.get("status") != "promoted" or receipt.get("job_id") != resolved_job_id:
        raise ValueError("Candidate promotion receipt cannot be rolled back.")
    live_root = live_artifact_root.resolve()
    backup = (live_root / str(receipt.get("backup_path", ""))).resolve()
    backup.relative_to(live_root)
    if not backup.is_dir():
        raise FileNotFoundError("Candidate promotion backup is missing.")
    final_outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(live_root)
    restored: list[str] = []
    for field in reversed(mushroom_rebuild_pipeline.ACCEPTED_OUTPUT_FIELDS):
        destination = Path(getattr(final_outputs, field))
        relative = destination.relative_to(live_root)
        previous = backup / relative
        if previous.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(previous, destination)
        else:
            destination.unlink(missing_ok=True)
        restored.append(relative.as_posix())
    shutil.rmtree(backup, ignore_errors=True)
    receipt_path.unlink(missing_ok=True)
    return {"status": "rolled_back", "job_id": resolved_job_id, "restored": restored}


def upload_ml_train_result(
    ha_url: str,
    job: dict[str, Any],
    worker_job_dir: Path,
    *,
    worker_id: str,
    claim_token: str,
    token: str,
    timeout: float = 30.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    job_id = mushroom_worker_transport.validate_job_id(str(job.get("job_id", "")))
    endpoint = str(job.get("result_endpoint", "") or "")
    complete_endpoint = str(job.get("result_complete_endpoint", "") or "")
    if endpoint != "/api/mushrooms/workers/jobs/ml-result-file":
        raise ValueError("Worker ML training result endpoint is invalid.")
    if complete_endpoint != "/api/mushrooms/workers/jobs/ml-result-complete":
        raise ValueError("Worker ML training completion endpoint is invalid.")
    output_dir = worker_job_dir.resolve() / "ml_candidate"
    manifest_path = output_dir / ML_TRAIN_RESULT_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"ML training result manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("ML training result manifest is not a JSON object.")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("ML training result manifest artifacts are missing.")
    headers = mushroom_worker_transport.request_headers(worker_id, claim_token, token)
    headers["Content-Type"] = "application/octet-stream"
    files = [ML_TRAIN_RESULT_NAME] + [str(row["path"]) for row in artifacts if isinstance(row, dict)]
    for index, logical_path in enumerate(files, start=1):
        content = (output_dir / logical_path).read_bytes()
        query = urlencode({"job_id": job_id, "file": logical_path})
        _post_bytes(
            ha_url.rstrip("/") + endpoint + "?" + query,
            content,
            headers=headers,
            timeout=timeout,
        )
        if progress_callback is not None:
            progress_callback(
                {
                    "phase": "Uploading ML training result",
                    "message": f"Uploaded result file {index}/{len(files)}.",
                    "overall_percent": 90 + int((index / len(files)) * 8),
                }
            )
    complete_headers = dict(headers)
    complete_headers["Content-Type"] = "application/json"
    payload = json.dumps(
        {"job_id": job_id, "worker_id": worker_id, "claim_token": claim_token},
        ensure_ascii=False,
    ).encode("utf-8")
    completed = _post_bytes(
        ha_url.rstrip("/") + complete_endpoint,
        payload,
        headers=complete_headers,
        timeout=timeout,
    )
    verification = completed.get("verification")
    if not isinstance(verification, dict) or verification.get("status") not in {"verified", "reused"}:
        raise ValueError("Rainmapper did not verify the uploaded ML training result.")
    return dict(verification)
