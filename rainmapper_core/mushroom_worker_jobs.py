"""Persistent queue for jobs assigned to external Rainmapper workers.

The first supported job is deliberately non-destructive: it only proves that
HA can queue a job for one exact worker and that this worker can claim it.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import secrets
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from rainmapper_core.mushroom_worker_registry import WORKER_ID_PATTERN


SCHEMA_VERSION = "0.1"
JOB_ID_PATTERN = re.compile(r"^worker_job_[a-zA-Z0-9_-]{8,80}$")
JOB_TYPE_CLAIM_PROBE = "worker_claim_probe"
JOB_TYPE_SNAPSHOT_TRANSPORT = "worker_snapshot_transport_probe"
JOB_TYPE_CANDIDATE_REBUILD = "worker_candidate_rebuild"
JOB_TYPE_ML_TRAIN = "worker_ml_train_v0"
JOB_TYPE_ML_MULTIVERSION = "worker_ml_multiversion_v1"
JOB_TYPE_PREDICTOR = "worker_predictor_v1"
ML_JOB_PURPOSES = frozenset({"operational", "benchmark"})
MAX_JOBS = 50
DEFAULT_LEASE_SECONDS = 10
TERMINAL_STATUSES = {"complete", "cancelled", "failed"}
ACTIVE_STATUSES = {"preparing", "queued", "claimed", "running", "cancel_requested"}
WORK_KEY_CLAIM_PROBE = "worker_claim_probe:v0"
PREDICTOR_RESULT_MAX_BYTES = 64 * 1024 * 1024
PREDICTOR_RESULTS_DIRNAME = ".worker-predictor-results"
PREDICTOR_RESULT_KEEP_RECENT = 10
PREDICTOR_RESULT_MAX_AGE_HOURS = 24


def validate_predictor_result_size(response: object) -> int:
    """Return the encoded response size or reject it before transport/storage."""
    encoded_size = len(json.dumps(response, ensure_ascii=False).encode("utf-8"))
    if encoded_size > PREDICTOR_RESULT_MAX_BYTES:
        limit_mib = PREDICTOR_RESULT_MAX_BYTES // (1024 * 1024)
        raise ValueError(f"Worker predictor result exceeds {limit_mib} MiB.")
    return encoded_size


class DuplicateActiveWorkError(ValueError):
    """Raised when equivalent work is already active in the coordinator."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError("Worker job timestamp is invalid.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _lease_expires(timestamp: str, lease_seconds: int) -> str:
    return (_parse_timestamp(timestamp) + timedelta(seconds=max(1, lease_seconds))).isoformat(timespec="seconds")


def empty_queue() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "jobs": []}


def load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_queue()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load worker job queue: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Worker job queue schema is invalid.")
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("Worker job queue list is invalid.")
    return {"schema_version": SCHEMA_VERSION, "jobs": [dict(row) for row in jobs if isinstance(row, dict)]}


def _predictor_result_path(queue_path: Path, job_id: str) -> Path:
    if not JOB_ID_PATTERN.fullmatch(str(job_id)):
        raise ValueError("Worker job ID is invalid.")
    return queue_path.parent / PREDICTOR_RESULTS_DIRNAME / f"{job_id}.json"


def _externalize_predictor_results(
    queue_path: Path, payload: dict[str, Any]
) -> None:
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        return
    for job in jobs:
        if not isinstance(job, dict) or job.get("job_type") != JOB_TYPE_PREDICTOR:
            continue
        result = job.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("response"), dict):
            continue
        response = result.pop("response")
        encoded = json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > PREDICTOR_RESULT_MAX_BYTES:
            limit_mib = PREDICTOR_RESULT_MAX_BYTES // (1024 * 1024)
            raise ValueError(f"Worker predictor result exceeds {limit_mib} MiB.")
        result_path = _predictor_result_path(queue_path, str(job.get("job_id", "")))
        _write_atomic(
            result_path,
            {
                "schema_version": "1.0",
                "kind": "rainmapper_worker_predictor_result",
                "response": response,
            },
        )
        job["predictor_result_ref"] = {
            "size_bytes": len(encoded),
            "sha256": "sha256:" + hashlib.sha256(encoded).hexdigest(),
        }


def _cleanup_predictor_result_files(queue_path: Path, payload: dict[str, Any]) -> None:
    result_dir = queue_path.parent / PREDICTOR_RESULTS_DIRNAME
    if not result_dir.is_dir():
        return
    retained = {
        f"{job.get('job_id')}.json"
        for job in payload.get("jobs", [])
        if isinstance(job, dict) and isinstance(job.get("predictor_result_ref"), dict)
    }
    for candidate in result_dir.glob("worker_job_*.json"):
        if candidate.name not in retained:
            candidate.unlink(missing_ok=True)


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    is_queue = payload.get("schema_version") == SCHEMA_VERSION and isinstance(
        payload.get("jobs"), list
    )
    if is_queue:
        _externalize_predictor_results(path, payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    if is_queue:
        _cleanup_predictor_result_files(path, payload)


def _hydrate_predictor_result(path: Path, job: dict[str, Any]) -> dict[str, Any]:
    hydrated = dict(job)
    result = hydrated.get("result")
    reference = hydrated.get("predictor_result_ref")
    if not isinstance(result, dict) or not isinstance(reference, dict):
        return hydrated
    result_path = _predictor_result_path(path, str(hydrated.get("job_id", "")))
    try:
        stored = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load worker Predictor result: {exc}") from exc
    response = stored.get("response") if isinstance(stored, dict) else None
    if not isinstance(response, dict):
        raise ValueError("Worker Predictor result file is invalid.")
    encoded = json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    expected_size = int(reference.get("size_bytes", -1))
    expected_sha = str(reference.get("sha256", ""))
    if len(encoded) != expected_size or "sha256:" + hashlib.sha256(encoded).hexdigest() != expected_sha:
        raise ValueError("Worker Predictor result file integrity check failed.")
    hydrated["result"] = {**result, "response": response}
    return hydrated


def _predictor_result_timestamp(job: dict[str, Any]) -> datetime:
    value = str(job.get("finished_at") or job.get("created_at") or "")
    return _parse_timestamp(value)


def plan_predictor_result_expiration(
    path: Path,
    *,
    now: datetime | None = None,
    keep_recent: int = PREDICTOR_RESULT_KEEP_RECENT,
    max_age_hours: int = PREDICTOR_RESULT_MAX_AGE_HOURS,
) -> dict[str, Any]:
    """Plan expiry of heavy Predictor responses without changing the queue."""
    queue_path = Path(path)
    queue = load_queue(queue_path)
    current = (now or datetime.now(UTC)).astimezone(UTC)
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    retained: list[dict[str, str]] = []
    errors: list[str] = []
    for job in queue["jobs"]:
        if job.get("job_type") != JOB_TYPE_PREDICTOR:
            continue
        reference = job.get("predictor_result_ref")
        if not isinstance(reference, dict):
            continue
        job_id = str(job.get("job_id", ""))
        try:
            timestamp = _predictor_result_timestamp(job)
        except ValueError as exc:
            errors.append(f"{job_id}: {exc}")
            retained.append({"job_id": job_id, "reason": "invalid timestamp"})
            continue
        candidates.append((timestamp, job))

    newest_ids = {
        str(job.get("job_id", ""))
        for _timestamp, job in sorted(candidates, key=lambda row: row[0], reverse=True)[
            : max(0, int(keep_recent))
        ]
    }
    cutoff = current - timedelta(hours=max(0, int(max_age_hours)))
    planned: list[dict[str, Any]] = []
    for timestamp, job in candidates:
        job_id = str(job.get("job_id", ""))
        if job.get("status") in ACTIVE_STATUSES:
            retained.append({"job_id": job_id, "reason": "active"})
            continue
        if job_id in newest_ids:
            retained.append({"job_id": job_id, "reason": "newest retained set"})
            continue
        if timestamp >= cutoff:
            retained.append({"job_id": job_id, "reason": "within retention age"})
            continue
        try:
            result_path = _predictor_result_path(queue_path, job_id)
            if result_path.is_symlink() or not result_path.is_file():
                raise ValueError("Predictor result is missing or is not a regular file.")
            _hydrate_predictor_result(queue_path, job)
            planned.append(
                {
                    "job_id": job_id,
                    "path": result_path.name,
                    "size_bytes": result_path.stat().st_size,
                    "finished_at": timestamp.isoformat(timespec="seconds"),
                    "reason": (
                        f"older than {max(0, int(max_age_hours))} h and outside "
                        f"the newest {max(0, int(keep_recent))} Predictor results"
                    ),
                    "reference": dict(job["predictor_result_ref"]),
                }
            )
        except (OSError, ValueError) as exc:
            errors.append(f"{job_id}: {exc}")
            retained.append({"job_id": job_id, "reason": "validation error"})
    return {"planned": planned, "retained": retained, "errors": errors}


def expire_predictor_results(
    path: Path,
    plan: dict[str, Any],
    *,
    expired_at: datetime | None = None,
) -> dict[str, Any]:
    """Apply a previously validated expiry plan with the queue update first."""
    queue_path = Path(path)
    queue = load_queue(queue_path)
    jobs_by_id = {
        str(job.get("job_id", "")): job
        for job in queue["jobs"]
        if isinstance(job, dict)
    }
    timestamp = (expired_at or datetime.now(UTC)).astimezone(UTC).isoformat(timespec="seconds")
    expired: list[str] = []
    errors: list[str] = []
    for entry in plan.get("planned", []):
        if not isinstance(entry, dict):
            continue
        job_id = str(entry.get("job_id", ""))
        job = jobs_by_id.get(job_id)
        try:
            if job is None or job.get("job_type") != JOB_TYPE_PREDICTOR:
                raise ValueError("Predictor job is no longer present.")
            reference = job.get("predictor_result_ref")
            if not isinstance(reference, dict) or reference != entry.get("reference"):
                raise ValueError("Predictor result reference changed after planning.")
            _hydrate_predictor_result(queue_path, job)
            job.pop("predictor_result_ref", None)
            job["predictor_result_detail"] = {
                "status": "expired",
                "expired_at": timestamp,
                "previous_size_bytes": int(reference.get("size_bytes", 0)),
                "previous_sha256": str(reference.get("sha256", "")),
            }
            expired.append(job_id)
        except (OSError, ValueError) as exc:
            errors.append(f"{job_id}: {exc}")
    if expired:
        _write_atomic(queue_path, queue)
    return {"expired": expired, "errors": errors}


def _validate_worker_id(worker_id: str) -> str:
    value = str(worker_id or "").strip()
    if not WORKER_ID_PATTERN.fullmatch(value):
        raise ValueError("Worker ID is invalid.")
    return value


def create_claim_probe(
    path: Path,
    *,
    worker_id: str,
    worker_display_name: str,
    job_id: str | None = None,
    created_at: str | None = None,
    work_key: str = WORK_KEY_CLAIM_PROBE,
) -> dict[str, Any]:
    target_worker_id = _validate_worker_id(worker_id)
    display_name = str(worker_display_name or "").strip()[:80]
    if not display_name:
        raise ValueError("Worker display name is required.")
    resolved_job_id = job_id or f"worker_job_{secrets.token_urlsafe(9)}"
    if not JOB_ID_PATTERN.fullmatch(resolved_job_id):
        raise ValueError("Worker job ID is invalid.")
    timestamp = created_at or utc_now()
    resolved_work_key = str(work_key or "").strip()[:200]
    if not resolved_work_key:
        raise ValueError("Worker job work key is required.")
    queue = load_queue(path)
    duplicate = next(
        (
            row
            for row in queue["jobs"]
            if row.get("work_key") == resolved_work_key and row.get("status") in ACTIVE_STATUSES
        ),
        None,
    )
    if duplicate is not None:
        raise DuplicateActiveWorkError(
            f"Equivalent worker job is already active: {duplicate.get('job_id', '')}."
        )
    job = {
        "job_id": resolved_job_id,
        "job_type": JOB_TYPE_CLAIM_PROBE,
        "work_key": resolved_work_key,
        "target_worker_id": target_worker_id,
        "target_display_name": display_name,
        "status": "queued",
        "phase": "Waiting for worker",
        "message": "Non-destructive worker assignment test queued.",
        "scope": "transport test",
        "overall_percent": 0,
        "created_at": timestamp,
        "claimed_at": "",
        "started_at": "",
        "finished_at": "",
        "cancel_requested_at": "",
        "cancel_mode": "",
        "reassigned_at": "",
        "lease_expires_at": "",
        "claim_token": "",
        "assignment_revision": 1,
    }
    queue["jobs"].append(job)
    queue["jobs"] = queue["jobs"][-MAX_JOBS:]
    _write_atomic(path, queue)
    return dict(job)


def create_snapshot_transport_probe(
    path: Path,
    *,
    worker_id: str,
    worker_display_name: str,
    input_bundle: dict[str, Any],
    job_id: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    target_worker_id = _validate_worker_id(worker_id)
    display_name = str(worker_display_name or "").strip()[:80]
    if not display_name:
        raise ValueError("Worker display name is required.")
    if not JOB_ID_PATTERN.fullmatch(str(job_id or "")):
        raise ValueError("Worker job ID is invalid.")
    if not isinstance(input_bundle, dict) or input_bundle.get("job_id") != job_id:
        raise ValueError("Worker input bundle contract is invalid.")
    snapshot_id = str(input_bundle.get("snapshot_id", "") or "")
    job_spec_id = str(input_bundle.get("job_spec_id", "") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", snapshot_id):
        raise ValueError("Worker input snapshot ID is invalid.")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", job_spec_id):
        raise ValueError("Worker job spec ID is invalid.")
    file_count = input_bundle.get("input_file_count")
    size_bytes = input_bundle.get("input_size_bytes")
    if not isinstance(file_count, int) or isinstance(file_count, bool) or file_count < 1:
        raise ValueError("Worker input bundle file count is invalid.")
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 1:
        raise ValueError("Worker input bundle size is invalid.")
    work_key = f"snapshot_transport:v0:{snapshot_id}:all"
    queue = load_queue(path)
    duplicate = next(
        (
            row
            for row in queue["jobs"]
            if row.get("work_key") == work_key and row.get("status") in ACTIVE_STATUSES
        ),
        None,
    )
    if duplicate is not None:
        raise DuplicateActiveWorkError(
            f"Equivalent worker job is already active: {duplicate.get('job_id', '')}."
        )
    timestamp = created_at or utc_now()
    job = {
        "job_id": job_id,
        "job_type": JOB_TYPE_SNAPSHOT_TRANSPORT,
        "work_key": work_key,
        "target_worker_id": target_worker_id,
        "target_display_name": display_name,
        "status": "queued",
        "phase": "Waiting for worker",
        "message": "Immutable input transport test queued.",
        "scope": "input transport test",
        "overall_percent": 0,
        "created_at": timestamp,
        "claimed_at": "",
        "started_at": "",
        "finished_at": "",
        "cancel_requested_at": "",
        "cancel_mode": "",
        "reassigned_at": "",
        "lease_expires_at": "",
        "claim_token": "",
        "assignment_revision": 1,
        "input_bundle": {
            **input_bundle,
            "endpoint": "/api/mushrooms/workers/jobs/input",
            "dataset_endpoint": "/api/mushrooms/workers/jobs/dataset",
        },
    }
    queue["jobs"].append(job)
    queue["jobs"] = queue["jobs"][-MAX_JOBS:]
    _write_atomic(path, queue)
    return dict(job)


def create_candidate_rebuild(
    path: Path,
    *,
    worker_id: str,
    worker_display_name: str,
    input_bundle: dict[str, Any],
    job_id: str,
    profile_keys: list[str] | tuple[str, ...] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    target_worker_id = _validate_worker_id(worker_id)
    display_name = str(worker_display_name or "").strip()[:80]
    if not display_name:
        raise ValueError("Worker display name is required.")
    if not JOB_ID_PATTERN.fullmatch(str(job_id or "")):
        raise ValueError("Worker job ID is invalid.")
    if not isinstance(input_bundle, dict) or input_bundle.get("job_id") != job_id:
        raise ValueError("Worker input bundle contract is invalid.")
    snapshot_id = str(input_bundle.get("snapshot_id", "") or "")
    job_spec_id = str(input_bundle.get("job_spec_id", "") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", snapshot_id):
        raise ValueError("Worker input snapshot ID is invalid.")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", job_spec_id):
        raise ValueError("Worker job spec ID is invalid.")
    selected_profiles = [
        str(value or "").strip() for value in (profile_keys or [])
    ]
    if any(not value for value in selected_profiles) or len(selected_profiles) != len(
        set(selected_profiles)
    ):
        raise ValueError("Operational profile selection is invalid.")
    work_key = f"rebuild:v0:{snapshot_id}:all"
    queue = load_queue(path)
    duplicate = next(
        (
            row
            for row in queue["jobs"]
            if row.get("status") in ACTIVE_STATUSES
            and row.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
            and str(row.get("input_bundle", {}).get("snapshot_id", "")) == snapshot_id
            and row.get("work_key") == work_key
        ),
        None,
    )
    if duplicate is not None:
        raise DuplicateActiveWorkError(
            f"Equivalent worker job is already active: {duplicate.get('job_id', '')}."
        )
    timestamp = created_at or utc_now()
    job = {
        "job_id": job_id,
        "job_type": JOB_TYPE_CANDIDATE_REBUILD,
        "work_key": work_key,
        "target_worker_id": target_worker_id,
        "target_display_name": display_name,
        "status": "queued",
        "phase": "Waiting for worker",
        "message": "Complete operational rebuild queued for automatic promotion.",
        "scope": "all eligible",
        "reconstruction_scope": "all",
        "scope_species_ids": [],
        "profile_keys": selected_profiles,
        "overall_percent": 0,
        "created_at": timestamp,
        "claimed_at": "",
        "started_at": "",
        "finished_at": "",
        "cancel_requested_at": "",
        "cancel_mode": "",
        "reassigned_at": "",
        "lease_expires_at": "",
        "claim_token": "",
        "assignment_revision": 1,
        "promotion_eligible": True,
        "full_update": True,
        "promotion_status": "",
        "promotion_percent": 0,
        "promotion_error": "",
        "promotion_result": {},
        "discard_status": "",
        "discard_requested_at": "",
        "input_bundle": {
            **input_bundle,
            "endpoint": "/api/mushrooms/workers/jobs/input",
            "dataset_endpoint": "/api/mushrooms/workers/jobs/dataset",
        },
        "result_endpoint": "/api/mushrooms/workers/jobs/result-file",
        "result_complete_endpoint": "/api/mushrooms/workers/jobs/result-complete",
    }
    queue["jobs"].append(job)
    queue["jobs"] = queue["jobs"][-MAX_JOBS:]
    _write_atomic(path, queue)
    return dict(job)


def create_candidate_preparation(
    path: Path,
    *,
    worker_id: str,
    worker_display_name: str,
    job_id: str,
    profile_keys: list[str] | tuple[str, ...] | None = None,
    created_at: str | None = None,
    phase: str = "Reconciling GIS and SoilGrids",
    message: str = "Checking static GIS context before freezing the input snapshot.",
) -> dict[str, Any]:
    """Persist coordinator preparation before an immutable bundle exists."""
    target_worker_id = _validate_worker_id(worker_id)
    display_name = str(worker_display_name or "").strip()[:80]
    if not display_name:
        raise ValueError("Worker display name is required.")
    if not JOB_ID_PATTERN.fullmatch(str(job_id or "")):
        raise ValueError("Worker job ID is invalid.")
    selected_profiles = [str(value or "").strip() for value in (profile_keys or [])]
    if any(not value for value in selected_profiles) or len(selected_profiles) != len(
        set(selected_profiles)
    ):
        raise ValueError("Operational profile selection is invalid.")
    queue = load_queue(path)
    duplicate = next(
        (
            row
            for row in queue["jobs"]
            if row.get("status") in ACTIVE_STATUSES
            and row.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
            and row.get("reconstruction_scope") == "all"
        ),
        None,
    )
    if duplicate is not None:
        raise DuplicateActiveWorkError(
            f"An operational rebuild is already active: {duplicate.get('job_id', '')}."
        )
    timestamp = created_at or utc_now()
    job = {
        "job_id": job_id,
        "job_type": JOB_TYPE_CANDIDATE_REBUILD,
        "work_key": "rebuild:v0:preparing:all",
        "target_worker_id": target_worker_id,
        "target_display_name": display_name,
        "status": "preparing",
        "phase": str(phase or "")[:160],
        "message": str(message or "")[:500],
        "scope": "all eligible",
        "reconstruction_scope": "all",
        "scope_species_ids": [],
        "profile_keys": selected_profiles,
        "overall_percent": 1,
        "created_at": timestamp,
        "claimed_at": "",
        "started_at": timestamp,
        "finished_at": "",
        "cancel_requested_at": "",
        "cancel_mode": "",
        "reassigned_at": "",
        "lease_expires_at": "",
        "claim_token": "",
        "assignment_revision": 1,
        "promotion_eligible": True,
        "full_update": True,
        "promotion_status": "",
        "promotion_percent": 0,
        "promotion_error": "",
        "promotion_result": {},
        "discard_status": "",
        "discard_requested_at": "",
        "preparation_telemetry": {},
        "input_bundle": {},
    }
    queue["jobs"].append(job)
    queue["jobs"] = queue["jobs"][-MAX_JOBS:]
    _write_atomic(path, queue)
    return dict(job)


def update_candidate_preparation(
    path: Path,
    *,
    job_id: str,
    phase: str,
    message: str,
    overall_percent: int,
    telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("status") != "preparing":
        return dict(job)
    job.update(
        {
            "phase": str(phase or "")[:160],
            "message": str(message or "")[:500],
            "overall_percent": max(1, min(9, int(overall_percent))),
            "preparation_telemetry": dict(telemetry or {}),
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def candidate_preparation_cancelled(path: Path, *, job_id: str) -> bool:
    job = get_job(path, job_id=job_id)
    return bool(job and job.get("status") == "cancelled")


def finalize_candidate_preparation(
    path: Path,
    *,
    job_id: str,
    input_bundle: dict[str, Any],
    telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(input_bundle, dict) or input_bundle.get("job_id") != job_id:
        raise ValueError("Worker input bundle contract is invalid.")
    snapshot_id = str(input_bundle.get("snapshot_id", "") or "")
    job_spec_id = str(input_bundle.get("job_spec_id", "") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", snapshot_id):
        raise ValueError("Worker input snapshot ID is invalid.")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", job_spec_id):
        raise ValueError("Worker job spec ID is invalid.")
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("status") == "cancelled":
        raise ValueError("Worker job was cancelled during coordinator preparation.")
    if job.get("status") != "preparing":
        raise ValueError("Worker job is not awaiting coordinator preparation.")
    work_key = f"rebuild:v0:{snapshot_id}:all"
    duplicate = next(
        (
            row
            for row in queue["jobs"]
            if row is not job
            and row.get("status") in ACTIVE_STATUSES
            and row.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
            and str(row.get("input_bundle", {}).get("snapshot_id", "")) == snapshot_id
            and row.get("work_key") == work_key
        ),
        None,
    )
    if duplicate is not None:
        raise DuplicateActiveWorkError(
            f"Equivalent worker job is already active: {duplicate.get('job_id', '')}."
        )
    job.update(
        {
            "work_key": work_key,
            "status": "queued",
            "phase": "Waiting for worker",
            "message": "Complete operational rebuild queued for automatic promotion.",
            "overall_percent": 0,
            "started_at": "",
            "preparation_telemetry": dict(telemetry or {}),
            "input_bundle": {
                **input_bundle,
                "endpoint": "/api/mushrooms/workers/jobs/input",
                "dataset_endpoint": "/api/mushrooms/workers/jobs/dataset",
            },
            "result_endpoint": "/api/mushrooms/workers/jobs/result-file",
            "result_complete_endpoint": "/api/mushrooms/workers/jobs/result-complete",
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def fail_candidate_preparation(
    path: Path,
    *,
    job_id: str,
    error: str,
    finished_at: str | None = None,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("status") == "cancelled":
        return dict(job)
    if job.get("status") != "preparing":
        raise ValueError("Worker job is not awaiting coordinator preparation.")
    job.update(
        {
            "status": "failed",
            "phase": "Coordinator preparation failed",
            "message": str(error or "Coordinator preparation failed.")[:500],
            "error": str(error or "")[:2000],
            "finished_at": finished_at or utc_now(),
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def create_ml_train_job(
    path: Path,
    *,
    worker_id: str,
    worker_display_name: str,
    input_bundle: dict[str, Any],
    job_id: str,
    species_ids: list[str] | tuple[str, ...] | None = None,
    profile_keys: list[str] | tuple[str, ...] | None = None,
    triggered_by_job_id: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    target_worker_id = _validate_worker_id(worker_id)
    display_name = str(worker_display_name or "").strip()[:80]
    if not display_name:
        raise ValueError("Worker display name is required.")
    if not JOB_ID_PATTERN.fullmatch(str(job_id or "")):
        raise ValueError("Worker job ID is invalid.")
    if not isinstance(input_bundle, dict) or input_bundle.get("job_id") != job_id:
        raise ValueError("Worker input bundle contract is invalid.")
    features_digest = str(input_bundle.get("features_digest", "") or "")
    job_spec_id = str(input_bundle.get("job_spec_id", "") or "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", features_digest):
        raise ValueError("Worker input features digest is invalid.")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", job_spec_id):
        raise ValueError("Worker job spec ID is invalid.")
    resolved_species_ids = sorted(
        {str(sp).strip() for sp in (species_ids or []) if str(sp or "").strip()}
    )
    selected_profiles = [
        str(value or "").strip() for value in (profile_keys or [])
    ]
    if any(not value for value in selected_profiles) or len(selected_profiles) != len(
        set(selected_profiles)
    ):
        raise ValueError("Operational profile selection is invalid.")
    work_key = f"ml_train:v0:{features_digest}"
    triggered_by = str(triggered_by_job_id or "").strip()
    if triggered_by and not JOB_ID_PATTERN.fullmatch(triggered_by):
        raise ValueError("Triggered-by job ID is invalid.")
    queue = load_queue(path)
    duplicate = next(
        (
            row
            for row in queue["jobs"]
            if row.get("status") in {"queued", "claimed", "running"}
            and row.get("job_type") == JOB_TYPE_ML_TRAIN
            and row.get("work_key") == work_key
        ),
        None,
    )
    if duplicate is not None:
        raise DuplicateActiveWorkError(
            f"Equivalent ML training job is already active: {duplicate.get('job_id', '')}."
        )
    timestamp = created_at or utc_now()
    scope_label = (
        f"species: {len(resolved_species_ids)}" if resolved_species_ids else "all eligible"
    )
    job = {
        "job_id": job_id,
        "job_type": JOB_TYPE_ML_TRAIN,
        "work_key": work_key,
        "target_worker_id": target_worker_id,
        "target_display_name": display_name,
        "status": "queued",
        "phase": "Waiting for worker",
        "message": "ML training job queued.",
        "scope": scope_label,
        "scope_species_ids": resolved_species_ids,
        "profile_keys": selected_profiles,
        "triggered_by_job_id": triggered_by,
        "overall_percent": 0,
        "created_at": timestamp,
        "claimed_at": "",
        "started_at": "",
        "finished_at": "",
        "cancel_requested_at": "",
        "cancel_mode": "",
        "reassigned_at": "",
        "lease_expires_at": "",
        "claim_token": "",
        "assignment_revision": 1,
        "promotion_eligible": True,
        "promotion_status": "",
        "promotion_percent": 0,
        "promotion_error": "",
        "promotion_result": {},
        "discard_status": "",
        "discard_requested_at": "",
        "input_bundle": {
            **input_bundle,
            "endpoint": "/api/mushrooms/workers/jobs/input",
        },
        "result_endpoint": "/api/mushrooms/workers/jobs/ml-result-file",
        "result_complete_endpoint": "/api/mushrooms/workers/jobs/ml-result-complete",
    }
    queue["jobs"].append(job)
    queue["jobs"] = queue["jobs"][-MAX_JOBS:]
    _write_atomic(path, queue)
    return dict(job)


def create_ml_multiversion_job(
    path: Path,
    *,
    worker_id: str,
    worker_display_name: str,
    input_bundle: dict[str, Any],
    job_id: str,
    job_purpose: str = "benchmark",
    profile_keys: list[str] | None = None,
    triggered_by_job_id: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    target_worker_id = _validate_worker_id(worker_id)
    purpose = str(job_purpose or "").strip()
    if purpose not in ML_JOB_PURPOSES:
        raise ValueError("Multiversion job purpose is invalid.")
    selected_profiles = [str(value or "").strip() for value in (profile_keys or [])]
    if not selected_profiles or any(not value for value in selected_profiles):
        raise ValueError("Multiversion training must declare selected profiles.")
    display_name = str(worker_display_name or "").strip()[:80]
    if not display_name or not JOB_ID_PATTERN.fullmatch(str(job_id or "")):
        raise ValueError("Multiversion worker assignment is invalid.")
    if not isinstance(input_bundle, dict) or input_bundle.get("job_id") != job_id:
        raise ValueError("Multiversion input bundle contract is invalid.")
    bundle_digest = str(input_bundle.get("bundle_digest", ""))
    files = input_bundle.get("files")
    snapshot_bundle = (
        re.fullmatch(r"sha256:[0-9a-f]{64}", str(input_bundle.get("snapshot_id", "")))
        and re.fullmatch(r"sha256:[0-9a-f]{64}", str(input_bundle.get("job_spec_id", "")))
        and isinstance(input_bundle.get("input_file_count"), int)
        and int(input_bundle.get("input_file_count", 0)) > 0
        and isinstance(input_bundle.get("multiversion_spec"), dict)
    )
    legacy_bundle = isinstance(files, list) and bool(files)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", bundle_digest) or not (
        snapshot_bundle or legacy_bundle
    ):
        raise ValueError("Multiversion input bundle identity is invalid.")
    queue = load_queue(path)
    duplicate = next(
        (
            row
            for row in queue["jobs"]
            if row.get("status") in {"queued", "claimed", "running"}
            and row.get("job_type") == JOB_TYPE_ML_MULTIVERSION
            and row.get("work_key") == f"ml_multiversion:v1:{purpose}:{bundle_digest}"
        ),
        None,
    )
    if duplicate is not None:
        raise DuplicateActiveWorkError(
            f"Equivalent multiversion training is already active: {duplicate.get('job_id', '')}."
        )
    timestamp = created_at or utc_now()
    job = {
        "job_id": job_id,
        "job_type": JOB_TYPE_ML_MULTIVERSION,
        "work_key": f"ml_multiversion:v1:{purpose}:{bundle_digest}",
        "target_worker_id": target_worker_id,
        "target_display_name": display_name,
        "status": "queued",
        "phase": "Waiting for worker",
        "message": (
            "Selected operational ML versions queued for refresh."
            if purpose == "operational"
            else "V2--V6 scientific benchmark queued."
        ),
        "scope": (
            "selected operational ML versions"
            if purpose == "operational"
            else "V2--V6 scientific benchmark"
        ),
        "job_purpose": purpose,
        "profile_keys": selected_profiles,
        "overall_percent": 0,
        "created_at": timestamp,
        "claimed_at": "",
        "started_at": "",
        "finished_at": "",
        "cancel_requested_at": "",
        "cancel_mode": "",
        "reassigned_at": "",
        "lease_expires_at": "",
        "claim_token": "",
        "assignment_revision": 1,
        "promotion_eligible": purpose == "operational",
        "triggered_by_job_id": str(triggered_by_job_id or "")[:100],
        "input_bundle": {**input_bundle, "endpoint": "/api/mushrooms/workers/jobs/input"},
        "result_endpoint": "/api/mushrooms/workers/jobs/multiversion-result-file",
        "result_complete_endpoint": "/api/mushrooms/workers/jobs/multiversion-result-complete",
    }
    queue["jobs"].append(job)
    queue["jobs"] = queue["jobs"][-MAX_JOBS:]
    _write_atomic(path, queue)
    return dict(job)


def create_predictor_job(
    path: Path,
    *,
    worker_id: str,
    worker_display_name: str,
    request: dict[str, Any],
    runtime_manifest: dict[str, Any],
    job_id: str | None = None,
    operation_id: str = "",
    worker_version: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    """Queue one interactive prediction without embedding runtime file bytes."""
    from rainmapper_core.mushroom_predictor_runtime import validate_manifest  # noqa: PLC0415
    from rainmapper_core.mushroom_predictor_service import normalize_request  # noqa: PLC0415

    target_worker_id = _validate_worker_id(worker_id)
    display_name = str(worker_display_name or "").strip()[:80]
    if not display_name:
        raise ValueError("Worker display name is required.")
    resolved_job_id = job_id or f"worker_job_{secrets.token_urlsafe(9)}"
    if not JOB_ID_PATTERN.fullmatch(resolved_job_id):
        raise ValueError("Worker job ID is invalid.")
    checked_request = normalize_request(request)
    checked_manifest = validate_manifest(runtime_manifest)
    timestamp = created_at or utc_now()
    job = {
        "job_id": resolved_job_id,
        "job_type": JOB_TYPE_PREDICTOR,
        "work_key": f"predictor:v1:{resolved_job_id}",
        "target_worker_id": target_worker_id,
        "target_display_name": display_name,
        "status": "queued",
        "phase": "Waiting for worker",
        "message": "Interactive prediction queued.",
        "scope": f"predictor {checked_request['view']}",
        "overall_percent": 0,
        "created_at": timestamp,
        "claimed_at": "",
        "started_at": "",
        "finished_at": "",
        "cancel_requested_at": "",
        "cancel_mode": "",
        "reassigned_at": "",
        "lease_expires_at": "",
        "claim_token": "",
        "assignment_revision": 1,
        "operation_id": str(operation_id or "")[:120],
        "worker_version": str(worker_version or "")[:80],
        "predictor_request": checked_request,
        "runtime_manifest": checked_manifest,
        "runtime_endpoint": "/api/mushrooms/workers/jobs/predictor-runtime",
    }
    queue = load_queue(path)
    queue["jobs"].append(job)
    queue["jobs"] = queue["jobs"][-MAX_JOBS:]
    _write_atomic(path, queue)
    return dict(job)


def begin_candidate_promotion(path: Path, *, job_id: str) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("job_type") not in {JOB_TYPE_CANDIDATE_REBUILD, JOB_TYPE_ML_TRAIN}:
        raise ValueError("Only candidate rebuilds and ML training jobs can be promoted.")
    if (
        job.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
        and str(job.get("reconstruction_scope", "all")) != "all"
    ):
        raise ValueError(
            "Partial reconstruction candidates cannot be promoted; run a full rebuild."
        )
    result_payload = job.get("result")
    if (
        job.get("status") != "complete"
        or not isinstance(result_payload, dict)
        or result_payload.get("verification_status") != "verified"
    ):
        raise ValueError("Candidate is not complete and verified.")
    if not job.get("promotion_eligible"):
        raise ValueError("Candidate was not created for operational promotion.")
    promotion_status = str(job.get("promotion_status", "") or "")
    if promotion_status == "promoted":
        return dict(job)
    if promotion_status == "promoting":
        raise ValueError("Candidate promotion is already running.")
    job.update(
        {
            "promotion_status": "promoting",
            "promotion_percent": 1,
            "promotion_error": "",
            "phase": "Validating candidate freshness",
            "message": "Validating current inputs before manual promotion.",
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def begin_full_update_promotion(
    path: Path,
    *,
    rebuild_job_id: str,
    training_job_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Atomically reserve promotion of one full rebuild and its linked training."""
    queue = load_queue(path)
    rebuild = _find_job(queue, rebuild_job_id)
    training = _find_job(queue, training_job_id)
    if (
        rebuild.get("job_type") != JOB_TYPE_CANDIDATE_REBUILD
        or str(rebuild.get("reconstruction_scope", "")) != "all"
        or not rebuild.get("full_update")
    ):
        raise ValueError("Reconstruction job is not a complete update.")
    if (
        training.get("job_type") != JOB_TYPE_ML_TRAIN
        or training.get("triggered_by_job_id") != rebuild_job_id
    ):
        raise ValueError("Training job is not linked to the complete reconstruction.")
    for job in (rebuild, training):
        result = job.get("result")
        if (
            job.get("status") != "complete"
            or not isinstance(result, dict)
            or result.get("verification_status") != "verified"
        ):
            raise ValueError("The complete generation is not fully verified.")
        if not job.get("promotion_eligible"):
            raise ValueError("The complete generation is not eligible for promotion.")
        if str(job.get("promotion_status", "") or "") in {"promoting", "promoted"}:
            raise ValueError("The complete generation is already being promoted or is active.")
    for job in (rebuild, training):
        job.update(
            {
                "promotion_status": "promoting",
                "promotion_percent": 1,
                "promotion_error": "",
                "phase": "Validating complete generation",
                "message": "Validating linked reconstruction and training before promotion.",
            }
        )
    _write_atomic(path, queue)
    return dict(rebuild), dict(training)


def get_job(path: Path, *, job_id: str) -> dict[str, Any]:
    queue = load_queue(path)
    return _hydrate_predictor_result(path, _find_job(queue, job_id))


def validate_candidate_discard(
    job: dict[str, Any],
    *,
    allow_interrupted_promotion: bool = False,
) -> None:
    if job.get("job_type") != JOB_TYPE_CANDIDATE_REBUILD:
        raise ValueError("Only candidate rebuilds can be discarded.")
    if str(job.get("status", "")) not in TERMINAL_STATUSES:
        raise ValueError("A candidate can only be discarded after the job has finished.")
    promotion_status = str(job.get("promotion_status", "") or "")
    if promotion_status == "promoted":
        raise ValueError("A candidate already promoted to the live model cannot be discarded.")
    if promotion_status == "promoting" and not allow_interrupted_promotion:
        raise ValueError("A candidate cannot be discarded while promotion is running.")


def request_candidate_discard(
    path: Path,
    *,
    job_id: str,
    requested_at: str | None = None,
    allow_interrupted_promotion: bool = False,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    validate_candidate_discard(
        job,
        allow_interrupted_promotion=allow_interrupted_promotion,
    )
    if job.get("discard_status") == "requested":
        return dict(job)
    job.update(
        {
            "discard_status": "requested",
            "discard_requested_at": requested_at or utc_now(),
            "promotion_eligible": False,
            "promotion_status": "discarding",
            "promotion_percent": 0,
            "phase": "Discarding candidate",
            "message": "Coordinator artifacts removed; waiting for worker cleanup acknowledgement.",
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def pending_candidate_discards(path: Path, *, worker_id: str) -> list[str]:
    target_worker_id = _validate_worker_id(worker_id)
    return [
        str(job.get("job_id", ""))
        for job in load_queue(path)["jobs"]
        if job.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
        and job.get("target_worker_id") == target_worker_id
        and job.get("discard_status") == "requested"
        and JOB_ID_PATTERN.fullmatch(str(job.get("job_id", "")))
    ]


def acknowledge_candidate_discards(
    path: Path,
    *,
    worker_id: str,
    job_ids: list[str] | tuple[str, ...],
) -> list[str]:
    target_worker_id = _validate_worker_id(worker_id)
    acknowledged = {
        str(job_id or "").strip()
        for job_id in job_ids
        if JOB_ID_PATTERN.fullmatch(str(job_id or "").strip())
    }
    if not acknowledged:
        return []
    queue = load_queue(path)
    completed: list[str] = []
    timestamp = utc_now()
    for job in queue["jobs"]:
        job_id = str(job.get("job_id", ""))
        if (
            job.get("target_worker_id") == target_worker_id
            and job.get("discard_status") == "requested"
            and job_id in acknowledged
        ):
            job.update(
                {
                    "discard_status": "acknowledged",
                    "discarded_at": timestamp,
                    "phase": "Candidate discarded",
                    "message": "Coordinator and worker private artifacts were removed.",
                }
            )
            completed.append(job_id)
    if not completed:
        return []
    _write_atomic(path, queue)
    return completed


def pending_worker_job_cleanups(path: Path, *, worker_id: str) -> list[str]:
    """Return terminal job directories that a worker may safely remove."""
    target_worker_id = _validate_worker_id(worker_id)
    cleanup_job_types = {
        JOB_TYPE_SNAPSHOT_TRANSPORT,
        JOB_TYPE_CANDIDATE_REBUILD,
        JOB_TYPE_ML_TRAIN,
        JOB_TYPE_ML_MULTIVERSION,
        JOB_TYPE_PREDICTOR,
    }
    return [
        str(job.get("job_id", ""))
        for job in load_queue(path)["jobs"]
        if job.get("target_worker_id") == target_worker_id
        and job.get("job_type") in cleanup_job_types
        and job.get("status") in TERMINAL_STATUSES
        and job.get("worker_cleanup_status") != "complete"
        and JOB_ID_PATTERN.fullmatch(str(job.get("job_id", "")))
    ][:MAX_JOBS]


def acknowledge_worker_job_cleanups(
    path: Path,
    *,
    worker_id: str,
    job_ids: list[str] | tuple[str, ...],
) -> list[str]:
    """Persist worker-side cleanup without deleting the bounded job history."""
    target_worker_id = _validate_worker_id(worker_id)
    acknowledged = {
        str(job_id or "").strip()
        for job_id in job_ids
        if JOB_ID_PATTERN.fullmatch(str(job_id or "").strip())
    }
    if not acknowledged:
        return []
    queue = load_queue(path)
    completed: list[str] = []
    timestamp = utc_now()
    for job in queue["jobs"]:
        job_id = str(job.get("job_id", ""))
        if job.get("target_worker_id") == target_worker_id and job_id in acknowledged:
            job["worker_cleanup_status"] = "complete"
            job["worker_cleaned_at"] = timestamp
            completed.append(job_id)
    if completed:
        _write_atomic(path, queue)
    return completed


def update_candidate_promotion_progress(
    path: Path,
    *,
    job_id: str,
    percent: int,
    phase: str,
    message: str = "",
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("promotion_status") != "promoting":
        raise ValueError("Candidate promotion is not running.")
    checked_percent = max(1, min(99, int(percent)))
    job.update(
        {
            "promotion_percent": checked_percent,
            "phase": str(phase or "Promoting candidate")[:160],
            "message": str(message or "")[:500],
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def finish_candidate_promotion(
    path: Path,
    *,
    job_id: str,
    promoted: bool,
    result: dict[str, Any] | None = None,
    error: str = "",
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("promotion_status") not in {"promoting", "promoted"}:
        raise ValueError("Candidate promotion was not started.")
    if job.get("promotion_status") == "promoted":
        return dict(job)
    if promoted:
        job.update(
            {
                "promotion_status": "promoted",
                "promotion_percent": 100,
                "promotion_error": "",
                "promotion_result": dict(result or {}),
                "phase": "Promoted to live model",
                "message": "Verified external candidate promoted atomically.",
            }
        )
    else:
        job.update(
            {
                "promotion_status": "failed",
                "promotion_percent": 0,
                "promotion_error": str(error or "Candidate promotion failed.")[:1000],
                "phase": "Promotion rejected",
                "message": "The live model was preserved.",
            }
        )
    _write_atomic(path, queue)
    return dict(job)


def _find_job(queue: dict[str, Any], job_id: str) -> dict[str, Any]:
    job = next((row for row in queue["jobs"] if str(row.get("job_id", "")) == job_id), None)
    if job is None:
        raise ValueError("Worker job was not found.")
    return job


def _validate_claim(job: dict[str, Any], *, worker_id: str, claim_token: str) -> None:
    target_worker_id = _validate_worker_id(worker_id)
    if str(job.get("target_worker_id", "")) != target_worker_id:
        raise ValueError("Worker job belongs to a different worker.")
    expected_claim = str(job.get("claim_token", ""))
    if not claim_token or not expected_claim or not secrets.compare_digest(expected_claim, claim_token):
        raise ValueError("Worker job claim is no longer valid.")


def _normalized_result(job: dict[str, Any], result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    job_type = job.get("job_type")
    if job_type not in {
        JOB_TYPE_SNAPSHOT_TRANSPORT,
        JOB_TYPE_CANDIDATE_REBUILD,
        JOB_TYPE_ML_TRAIN,
        JOB_TYPE_ML_MULTIVERSION,
        JOB_TYPE_PREDICTOR,
    }:
        return {}
    if job_type == JOB_TYPE_PREDICTOR:
        from rainmapper_core.mushroom_predictor_service import validate_response  # noqa: PLC0415

        response = validate_response(result.get("response"))
        validate_predictor_result_size(response)
        cold = result.get("cold")
        if not isinstance(cold, bool):
            raise ValueError("Worker predictor cold flag is invalid.")
        normalized = {
            "response": response,
            "cold": cold,
            "runtime_cache_status": str(result.get("runtime_cache_status", ""))[:40],
            "runtime_transferred_size_bytes": max(
                0, int(result.get("runtime_transferred_size_bytes", 0) or 0)
            ),
        }
        verification_status = str(
            result.get("runtime_verification_status", "") or ""
        )[:40]
        if verification_status:
            normalized["runtime_verification_status"] = verification_status
        for key in (
            "runtime_hashed_file_count",
            "runtime_reused_file_count",
            "runtime_fetched_file_count",
        ):
            value = result.get(key)
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"Worker predictor {key} is invalid.")
            normalized[key] = value
        elapsed = result.get("runtime_sync_seconds")
        if elapsed is not None:
            if not isinstance(elapsed, (int, float)) or isinstance(elapsed, bool) or elapsed < 0:
                raise ValueError("Worker predictor runtime_sync_seconds is invalid.")
            normalized["runtime_sync_seconds"] = round(float(elapsed), 6)
        return normalized
    if job_type == JOB_TYPE_ML_TRAIN:
        normalized: dict[str, Any] = {}
        status = str(result.get("verification_status", "") or "")[:40]
        if status:
            normalized["verification_status"] = status
        trained_species = result.get("trained_species")
        if trained_species is not None:
            if not isinstance(trained_species, list) or len(trained_species) > 256:
                raise ValueError("Worker ML result trained_species is invalid.")
            normalized_species = [str(value).strip() for value in trained_species]
            if (
                any(
                    not value
                    or len(value) > 120
                    or any(not (character.isalnum() or character in "_-") for character in value)
                    for value in normalized_species
                )
                or len(set(normalized_species)) != len(normalized_species)
            ):
                raise ValueError("Worker ML result trained_species is invalid.")
            normalized["trained_species"] = normalized_species
        trained_species_count = result.get("trained_species_count")
        if trained_species_count is not None:
            if not isinstance(trained_species_count, int) or isinstance(trained_species_count, bool) or trained_species_count < 0:
                raise ValueError("Worker ML result trained_species_count is invalid.")
            if trained_species is not None and trained_species_count != len(normalized_species):
                raise ValueError("Worker ML result trained_species_count does not match trained_species.")
            normalized["trained_species_count"] = trained_species_count
        result_manifest_id = str(result.get("result_manifest_id", "") or "")
        if result_manifest_id:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", result_manifest_id):
                raise ValueError("Worker ML result result_manifest_id is invalid.")
            normalized["result_manifest_id"] = result_manifest_id
        return normalized
    if job_type == JOB_TYPE_ML_MULTIVERSION:
        normalized = {}
        status = str(result.get("verification_status", "") or "")[:40]
        if status:
            normalized["verification_status"] = status
        batch_id = str(result.get("batch_id", "") or "")
        if batch_id:
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", batch_id):
                raise ValueError("Worker multiversion batch_id is invalid.")
            normalized["batch_id"] = batch_id
        snapshot_id = str(result.get("snapshot_id", "") or "")
        if snapshot_id:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", snapshot_id):
                raise ValueError("Worker multiversion snapshot_id is invalid.")
            normalized["snapshot_id"] = snapshot_id
        for key in ("planned_fit_count", "successful_fit_count", "failed_fit_count"):
            value = result.get(key)
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"Worker multiversion {key} is invalid.")
            normalized[key] = value
        purpose = str(job.get("job_purpose") or "benchmark")
        if purpose not in ML_JOB_PURPOSES:
            raise ValueError("Worker multiversion job purpose is invalid.")
        report_id = str(result.get("report_id", "") or "")
        if purpose == "benchmark":
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", report_id):
                raise ValueError("Worker benchmark report_id is invalid.")
            if result.get("benchmark_report_available") is not True:
                raise ValueError("Worker benchmark report is not available.")
            normalized["report_id"] = report_id
            normalized["benchmark_report_available"] = True
        elif report_id or result.get("benchmark_report_available"):
            raise ValueError("Operational worker result cannot declare a benchmark report.")
        if result.get("operational_candidate_trained") is not (purpose == "operational"):
            raise ValueError("Worker multiversion result purpose does not match its job.")
        normalized["job_purpose"] = purpose
        normalized["operational_candidate_trained"] = purpose == "operational"
        return normalized
    normalized = {}
    status = str(result.get("verification_status", "") or "")[:40]
    if status:
        normalized["verification_status"] = status
    for key in ("snapshot_id", "job_spec_id", "dataset_fingerprint"):
        value = str(result.get(key, "") or "")
        if value and not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
            raise ValueError(f"Worker result {key} is invalid.")
        if value:
            normalized[key] = value
    for key in ("input_file_count", "input_size_bytes"):
        value = result.get(key)
        if value is None:
            continue
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Worker result {key} is invalid.")
        normalized[key] = value
    dataset_cache_status = str(result.get("dataset_cache_status", "") or "")
    if dataset_cache_status:
        if dataset_cache_status not in {"reused", "synchronized"}:
            raise ValueError("Worker result dataset cache status is invalid.")
        normalized["dataset_cache_status"] = dataset_cache_status
    dataset_transferred_size = result.get("dataset_transferred_size_bytes")
    if dataset_transferred_size is not None:
        if (
            not isinstance(dataset_transferred_size, int)
            or isinstance(dataset_transferred_size, bool)
            or dataset_transferred_size < 0
        ):
            raise ValueError("Worker result dataset transferred size is invalid.")
        normalized["dataset_transferred_size_bytes"] = dataset_transferred_size
    if job_type == JOB_TYPE_CANDIDATE_REBUILD:
        for key in ("result_manifest_id",):
            value = str(result.get(key, "") or "")
            if value and not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
                raise ValueError(f"Worker result {key} is invalid.")
            if value:
                normalized[key] = value
        comparison_status = str(result.get("comparison_status", "") or "")
        if comparison_status not in {"equivalent", "different"}:
            raise ValueError("Worker result comparison status is invalid.")
        normalized["comparison_status"] = comparison_status
        verified_artifacts = result.get("verified_artifacts")
        if not isinstance(verified_artifacts, int) or isinstance(verified_artifacts, bool):
            raise ValueError("Worker result verified artifact count is invalid.")
        normalized["verified_artifacts"] = verified_artifacts
    input_bundle = job.get("input_bundle")
    if isinstance(input_bundle, dict):
        for key in ("snapshot_id", "job_spec_id", "input_file_count", "input_size_bytes"):
            if key in normalized and normalized[key] != input_bundle.get(key):
                raise ValueError(f"Worker result {key} does not match the assigned input bundle.")
    return normalized


def claim_next(
    path: Path,
    *,
    worker_id: str,
    claimed_at: str | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    claim_token: str | None = None,
) -> dict[str, Any] | None:
    target_worker_id = _validate_worker_id(worker_id)
    queue = load_queue(path)
    timestamp = claimed_at or utc_now()
    now = _parse_timestamp(timestamp)
    changed = False
    for row in queue["jobs"]:
        if (
            row.get("status") == "claimed"
            and row.get("target_worker_id") == target_worker_id
            and not row.get("started_at")
            and row.get("lease_expires_at")
        ):
            if _parse_timestamp(str(row["lease_expires_at"])) < now:
                row.update(
                    {
                        "status": "queued",
                        "phase": "Waiting for worker",
                        "message": "Expired claim returned to the assigned worker queue.",
                        "claimed_at": "",
                        "lease_expires_at": "",
                        "claim_token": "",
                        "assignment_revision": int(row.get("assignment_revision", 1) or 1) + 1,
                    }
                )
                changed = True
    job = next(
        (
            row
            for row in queue["jobs"]
            if row.get("status") == "queued" and row.get("target_worker_id") == target_worker_id
        ),
        None,
    )
    if job is None:
        if changed:
            _write_atomic(path, queue)
        return None
    resolved_claim_token = claim_token or secrets.token_urlsafe(24)
    job.update(
        {
            "status": "claimed",
            "phase": "Claimed by worker",
            "message": (
                "The assigned worker claimed the candidate rebuild."
                if job.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
                else (
                    "The assigned worker claimed the immutable input transport test."
                    if job.get("job_type") == JOB_TYPE_SNAPSHOT_TRANSPORT
                    else (
                        "The assigned worker claimed the interactive prediction."
                        if job.get("job_type") == JOB_TYPE_PREDICTOR
                        else "The assigned worker claimed this non-destructive test job."
                    )
                )
            ),
            "overall_percent": 5,
            "claimed_at": timestamp,
            "lease_expires_at": _lease_expires(timestamp, lease_seconds),
            "claim_token": resolved_claim_token,
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def start_job(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
    started_at: str | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    _validate_claim(job, worker_id=worker_id, claim_token=claim_token)
    if job.get("status") != "claimed" or job.get("started_at"):
        raise ValueError("Worker job cannot be started from its current state.")
    timestamp = started_at or utc_now()
    lease_expires_at = str(job.get("lease_expires_at", "") or "")
    if lease_expires_at and _parse_timestamp(lease_expires_at) < _parse_timestamp(timestamp):
        raise ValueError("Worker job claim lease has expired.")
    job.update(
        {
            "status": "running",
            "phase": (
                "Preparing candidate rebuild"
                if job.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
                else (
                    "Preparing input transport"
                    if job.get("job_type") == JOB_TYPE_SNAPSHOT_TRANSPORT
                    else (
                        "Predictor working"
                        if job.get("job_type") == JOB_TYPE_PREDICTOR
                        else "Running assignment test"
                    )
                )
            ),
            "message": (
                "The worker started the isolated candidate rebuild."
                if job.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
                else (
                    "The worker started downloading the immutable input bundle."
                    if job.get("job_type") == JOB_TYPE_SNAPSHOT_TRANSPORT
                    else (
                        "The prediction was launched. Please wait for the result."
                        if job.get("job_type") == JOB_TYPE_PREDICTOR
                        else "The worker started the non-destructive assignment test."
                    )
                )
            ),
            "overall_percent": 10,
            "started_at": timestamp,
            "lease_expires_at": _lease_expires(timestamp, lease_seconds),
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def update_progress(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
    phase: str,
    message: str,
    overall_percent: int,
    checked_at: str | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    _validate_claim(job, worker_id=worker_id, claim_token=claim_token)
    if job.get("status") != "running":
        raise ValueError("Worker job is not running.")
    percent = max(10, min(99, int(overall_percent)))
    job.update(
        {
            "phase": str(phase or "Running")[:160],
            "message": str(message or "")[:500],
            "overall_percent": percent,
            "lease_expires_at": _lease_expires(checked_at or utc_now(), lease_seconds),
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def poll_job(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
    checked_at: str | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    _validate_claim(job, worker_id=worker_id, claim_token=claim_token)
    if job.get("status") not in {"running", "cancel_requested"}:
        raise ValueError("Worker job is not running.")
    if job.get("status") == "running":
        timestamp = checked_at or utc_now()
        job["lease_expires_at"] = _lease_expires(timestamp, lease_seconds)
        _write_atomic(path, queue)
    return dict(job)


def abandon_stuck_job(
    path: Path,
    *,
    job_id: str,
    abandoned_at: str | None = None,
) -> dict[str, Any]:
    """Forcefully mark a cancel_requested job as cancelled when the worker is unreachable."""
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("status") != "cancel_requested":
        raise ValueError("Only cancel_requested jobs can be abandoned.")
    timestamp = abandoned_at or utc_now()
    job.update(
        {
            "status": "cancelled",
            "phase": "Abandoned",
            "message": "Job abandoned by operator (worker unreachable).",
            "overall_percent": int(job.get("overall_percent", 0) or 0),
            "finished_at": timestamp,
            "lease_expires_at": "",
            "error": "Abandoned by operator: worker did not acknowledge cancellation.",
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def finish_job(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
    status: str,
    finished_at: str | None = None,
    error: str = "",
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in TERMINAL_STATUSES:
        raise ValueError("Worker job final status is invalid.")
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    _validate_claim(job, worker_id=worker_id, claim_token=claim_token)
    if job.get("status") not in {"running", "cancel_requested"}:
        raise ValueError("Worker job cannot finish from its current state.")
    if job.get("status") == "cancel_requested" and status != "cancelled":
        raise ValueError("A cancelled worker job cannot publish a successful result.")
    timestamp = finished_at or utc_now()
    complete_phase = (
        "Candidate result verified"
        if job.get("job_type") == JOB_TYPE_CANDIDATE_REBUILD
        else (
            "Prediction completed"
            if job.get("job_type") == JOB_TYPE_PREDICTOR
            else (
            "Input bundle verified"
            if job.get("job_type") == JOB_TYPE_SNAPSHOT_TRANSPORT
            else (
                "ML training completed"
                if job.get("job_type") == JOB_TYPE_ML_TRAIN
                else (
                    (
                        "Operational generation training completed"
                        if job.get("job_purpose") == "operational"
                        else "Scientific benchmark completed"
                    )
                    if job.get("job_type") == JOB_TYPE_ML_MULTIVERSION
                    else "Assignment test completed"
                )
            )
            )
        )
    )
    phase = {"complete": complete_phase, "cancelled": "Cancelled", "failed": "Failed"}[status]
    job.update(
        {
            "status": status,
            "phase": phase,
            "message": phase + ".",
            "overall_percent": 100 if status == "complete" else int(job.get("overall_percent", 10) or 10),
            "finished_at": timestamp,
            "lease_expires_at": "",
            "error": str(error or "")[:1000],
            "result": _normalized_result(job, result),
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def authorize_input_download(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    _validate_claim(job, worker_id=worker_id, claim_token=claim_token)
    if job.get("job_type") not in {
        JOB_TYPE_SNAPSHOT_TRANSPORT,
        JOB_TYPE_CANDIDATE_REBUILD,
        JOB_TYPE_ML_TRAIN,
        JOB_TYPE_ML_MULTIVERSION,
        JOB_TYPE_PREDICTOR,
    }:
        raise ValueError("Worker job does not have an input bundle.")
    if job.get("status") not in {"claimed", "running", "cancel_requested"}:
        raise ValueError("Worker input bundle is not available in the current job state.")
    return dict(job)


def authorize_result_upload(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    _validate_claim(job, worker_id=worker_id, claim_token=claim_token)
    if job.get("job_type") != JOB_TYPE_CANDIDATE_REBUILD:
        raise ValueError("Worker job cannot upload candidate results.")
    if job.get("status") != "running":
        raise ValueError("Worker candidate result is not accepted in the current job state.")
    return dict(job)


def authorize_ml_train_result_upload(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    _validate_claim(job, worker_id=worker_id, claim_token=claim_token)
    if job.get("job_type") != JOB_TYPE_ML_TRAIN:
        raise ValueError("Worker job cannot upload ML training results.")
    if job.get("status") != "running":
        raise ValueError("Worker ML result is not accepted in the current job state.")
    return dict(job)


def authorize_ml_multiversion_result_upload(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    _validate_claim(job, worker_id=worker_id, claim_token=claim_token)
    if job.get("job_type") != JOB_TYPE_ML_MULTIVERSION:
        raise ValueError("Worker job cannot upload multiversion results.")
    if job.get("status") != "running":
        raise ValueError("Worker multiversion result is not accepted in the current job state.")
    return dict(job)


def retry_ml_multiversion_result(
    path: Path,
    *,
    job_id: str,
    requested_at: str | None = None,
) -> dict[str, Any]:
    """Requeue only a failed multiversion result delivery under the same identity."""
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("job_type") != JOB_TYPE_ML_MULTIVERSION or job.get("status") != "failed":
        raise ValueError("Only a failed multiversion job can retry result delivery.")
    timestamp = requested_at or utc_now()
    job.update(
        {
            "status": "queued",
            "phase": "Waiting to retry V2--V6 result delivery",
            "message": "The completed local result will be reused; training will not run again.",
            "overall_percent": 90,
            "claimed_at": "",
            "started_at": "",
            "finished_at": "",
            "lease_expires_at": "",
            "claim_token": "",
            "cancel_requested_at": "",
            "cancel_mode": "",
            "error": "",
            "result": {},
            "result_retry": True,
            "result_retry_requested_at": timestamp,
            "worker_cleanup_status": "",
            "worker_cleaned_at": "",
            "assignment_revision": int(job.get("assignment_revision", 1) or 1) + 1,
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def request_cancel(
    path: Path,
    *,
    job_id: str,
    requested_at: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    status = str(job.get("status", ""))
    if status in TERMINAL_STATUSES:
        raise ValueError("Worker job has already finished.")
    timestamp = requested_at or utc_now()
    if status == "preparing" or (
        status in {"queued", "claimed"} and not job.get("started_at")
    ):
        job.update(
            {
                "status": "cancelled",
                "phase": (
                    "Cancelled during coordinator preparation"
                    if status == "preparing"
                    else "Cancelled before start"
                ),
                "message": (
                    "Coordinator preparation stopped before freezing the input snapshot."
                    if status == "preparing"
                    else "The job was cancelled before worker processing started."
                ),
                "finished_at": timestamp,
                "cancel_requested_at": timestamp,
                "cancel_mode": "force" if force else "cooperative",
                "lease_expires_at": "",
                "claim_token": "",
                "assignment_revision": int(job.get("assignment_revision", 1) or 1) + 1,
            }
        )
    elif status == "running":
        job.update(
            {
                "status": "cancel_requested",
                "phase": "Force cancellation requested" if force else "Cancellation requested",
                "message": (
                    "Waiting for the worker supervisor to terminate the compute process."
                    if force
                    else "Waiting for the worker to stop at a safe point."
                ),
                "cancel_requested_at": timestamp,
                "cancel_mode": "force" if force else "cooperative",
            }
        )
    elif status == "cancel_requested" and force:
        job.update(
            {
                "phase": "Force cancellation requested",
                "message": "Waiting for the worker supervisor to terminate the compute process.",
                "cancel_mode": "force",
            }
        )
    elif status != "cancel_requested":
        raise ValueError("Worker job cannot be cancelled from its current state.")
    _write_atomic(path, queue)
    return dict(job)


def reassign_job(
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    worker_display_name: str,
    reassigned_at: str | None = None,
) -> dict[str, Any]:
    target_worker_id = _validate_worker_id(worker_id)
    display_name = str(worker_display_name or "").strip()[:80]
    if not display_name:
        raise ValueError("Worker display name is required.")
    queue = load_queue(path)
    job = _find_job(queue, job_id)
    if job.get("status") not in {"queued", "claimed"} or job.get("started_at"):
        raise ValueError("Only a job that has not started can be reassigned.")
    if job.get("target_worker_id") == target_worker_id:
        raise ValueError("Worker job is already assigned to that worker.")
    timestamp = reassigned_at or utc_now()
    job.update(
        {
            "target_worker_id": target_worker_id,
            "target_display_name": display_name,
            "status": "queued",
            "phase": "Waiting for worker",
            "message": f"Job reassigned to {display_name} before processing started.",
            "claimed_at": "",
            "lease_expires_at": "",
            "claim_token": "",
            "reassigned_at": timestamp,
            "assignment_revision": int(job.get("assignment_revision", 1) or 1) + 1,
        }
    )
    _write_atomic(path, queue)
    return dict(job)


def recent_jobs(path: Path, *, limit: int = 10) -> list[dict[str, Any]]:
    jobs = load_queue(path)["jobs"]
    return sorted(jobs, key=lambda row: str(row.get("created_at", "")), reverse=True)[: max(0, limit)]
