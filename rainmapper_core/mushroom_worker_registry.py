"""Persistent metadata and validation for Rainmapper compute workers."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1"
WORKER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{8,80}$")
JOB_ID_PATTERN = re.compile(r"^worker_job_[a-zA-Z0-9_-]{8,80}$")
HOME_ASSISTANT_EXECUTOR = "home_assistant"
WEATHER_PARQUET_CAPABILITY = "weather_parquet_v1"
PARTITIONED_WEATHER_HISTORY_CAPABILITY = "partitioned_weather_history_v1"
TERMINAL_JOB_CLEANUP_CAPABILITY = "terminal_job_cleanup_v1"
PREDICTOR_CAPABILITY = "predictor_v1"
STATIC_FIELDS = (
    "worker_id",
    "display_name",
    "host_name",
    "architecture",
    "platform",
    "worker_version",
    "capabilities",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def normalize_heartbeat(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Worker heartbeat must be an object.")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported worker heartbeat schema version.")
    if payload.get("kind") != "rainmapper_worker_heartbeat":
        raise ValueError("Invalid worker heartbeat kind.")
    worker_id = str(payload.get("worker_id", "") or "").strip()
    if not WORKER_ID_PATTERN.fullmatch(worker_id):
        raise ValueError("Worker ID is invalid.")
    display_name = str(payload.get("display_name", "") or "").strip()
    host_name = str(payload.get("host_name", "") or "").strip()
    if not display_name or len(display_name) > 80:
        raise ValueError("Worker display name is invalid.")
    if not host_name or len(host_name) > 255:
        raise ValueError("Worker host name is invalid.")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list) or not all(
        isinstance(value, str) and value.strip() and len(value) <= 80 for value in capabilities
    ):
        raise ValueError("Worker capabilities are invalid.")
    dataset_cache = payload.get("dataset_cache")
    if not isinstance(dataset_cache, dict):
        raise ValueError("Worker dataset cache summary is invalid.")
    predictor_cache = payload.get("predictor_cache", {})
    if not isinstance(predictor_cache, dict):
        raise ValueError("Worker predictor cache summary is invalid.")
    discarded_job_ids = payload.get("discarded_job_ids", [])
    if (
        not isinstance(discarded_job_ids, list)
        or len(discarded_job_ids) > 50
        or not all(isinstance(value, str) and JOB_ID_PATTERN.fullmatch(value) for value in discarded_job_ids)
    ):
        raise ValueError("Worker discarded job acknowledgement is invalid.")
    cleaned_job_ids = payload.get("cleaned_job_ids", [])
    if (
        not isinstance(cleaned_job_ids, list)
        or len(cleaned_job_ids) > 50
        or not all(isinstance(value, str) and JOB_ID_PATTERN.fullmatch(value) for value in cleaned_job_ids)
    ):
        raise ValueError("Worker cleaned job acknowledgement is invalid.")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "rainmapper_worker_heartbeat",
        "worker_id": worker_id,
        "display_name": display_name,
        "host_name": host_name,
        "architecture": str(payload.get("architecture", "") or "").strip()[:80],
        "platform": str(payload.get("platform", "") or "").strip()[:80],
        "worker_version": str(payload.get("worker_version", "") or "").strip()[:80],
        "status": str(payload.get("status", "unknown") or "unknown").strip()[:80],
        "job_api": str(payload.get("job_api", "not_implemented") or "not_implemented").strip()[:80],
        "capabilities": [str(value).strip() for value in capabilities],
        "dataset_cache": dict(dataset_cache),
        "predictor_cache": dict(predictor_cache),
        "discarded_job_ids": list(dict.fromkeys(discarded_job_ids)),
        "cleaned_job_ids": list(dict.fromkeys(cleaned_job_ids)),
    }


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "default_executor": HOME_ASSISTANT_EXECUTOR,
            "workers": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load worker registry: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Worker registry schema is invalid.")
    workers = payload.get("workers")
    if not isinstance(workers, list):
        raise ValueError("Worker registry list is invalid.")
    default_executor = normalize_executor(payload.get("default_executor", HOME_ASSISTANT_EXECUTOR))
    return {
        "schema_version": SCHEMA_VERSION,
        "default_executor": default_executor,
        "workers": [row for row in workers if isinstance(row, dict)],
    }


def normalize_executor(value: object) -> str:
    executor = str(value or HOME_ASSISTANT_EXECUTOR).strip()
    if executor == HOME_ASSISTANT_EXECUTOR:
        return executor
    if not executor.startswith("worker:"):
        raise ValueError("Default rebuild executor is invalid.")
    worker_id = executor.removeprefix("worker:")
    if not WORKER_ID_PATTERN.fullmatch(worker_id):
        raise ValueError("Default rebuild worker ID is invalid.")
    return executor


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
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


def remember_worker(path: Path, heartbeat: dict[str, Any]) -> bool:
    """Persist static worker metadata only when a worker is new or changes."""
    registry = load_registry(path)
    workers = registry["workers"]
    worker_id = str(heartbeat["worker_id"])
    existing = next((row for row in workers if str(row.get("worker_id", "")) == worker_id), None)
    static = {field: heartbeat.get(field) for field in STATIC_FIELDS}
    if existing is not None and all(existing.get(field) == static.get(field) for field in STATIC_FIELDS):
        return False
    now = utc_now()
    if existing is None:
        static["registered_at"] = now
        workers.append(static)
    else:
        registered_at = existing.get("registered_at", now)
        existing.clear()
        existing.update(static)
        existing["registered_at"] = registered_at
        existing["updated_at"] = now
    workers.sort(key=lambda row: (str(row.get("display_name", "")).casefold(), str(row.get("worker_id", ""))))
    _write_atomic(path, registry)
    return True


def set_default_executor(path: Path, executor: object) -> bool:
    """Persist the coordinator-side default without changing worker identity."""
    normalized = normalize_executor(executor)
    registry = load_registry(path)
    if registry["default_executor"] == normalized:
        return False
    registry["default_executor"] = normalized
    _write_atomic(path, registry)
    return True


def forget_worker(path: Path, worker_id: object) -> bool:
    """Remove a revoked worker and reset its default assignment to HA."""
    resolved_worker_id = str(worker_id or "").strip()
    if not WORKER_ID_PATTERN.fullmatch(resolved_worker_id):
        raise ValueError("Worker ID is invalid.")
    registry = load_registry(path)
    workers = registry["workers"]
    retained = [
        row for row in workers if str(row.get("worker_id", "")) != resolved_worker_id
    ]
    changed = len(retained) != len(workers)
    if registry["default_executor"] == f"worker:{resolved_worker_id}":
        registry["default_executor"] = HOME_ASSISTANT_EXECUTOR
        changed = True
    if not changed:
        return False
    registry["workers"] = retained
    _write_atomic(path, registry)
    return True
