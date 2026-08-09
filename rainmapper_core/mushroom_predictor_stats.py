"""Persistent, bounded execution statistics used by Predictor Auto mode."""

from __future__ import annotations

import json
import os
import statistics
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
MAX_SAMPLES_PER_EXECUTOR = 40


def _empty() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "executors": {}}


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty()
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        return _empty()
    executors = payload.get("executors")
    return payload if isinstance(executors, dict) else _empty()


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def record(
    path: Path,
    *,
    executor_id: str,
    cold: bool,
    backend_seconds: float,
    total_seconds: float | None = None,
    runtime_fingerprint: str = "",
    app_version: str = "",
    worker_version: str = "",
    recorded_at: str | None = None,
) -> dict[str, Any]:
    if not executor_id or backend_seconds < 0:
        raise ValueError("Predictor execution sample is invalid.")
    payload = load(path)
    samples = payload["executors"].setdefault(executor_id, [])
    sample = {
        "recorded_at": recorded_at or datetime.now(UTC).isoformat(timespec="seconds"),
        "cold": bool(cold),
        "backend_seconds": round(float(backend_seconds), 4),
        "total_seconds": round(float(total_seconds), 4) if total_seconds is not None else None,
        "runtime_fingerprint": str(runtime_fingerprint),
        "app_version": str(app_version),
        "worker_version": str(worker_version),
    }
    samples.append(sample)
    payload["executors"][executor_id] = samples[-MAX_SAMPLES_PER_EXECUTOR:]
    _write_atomic(path, payload)
    return sample


def summary(path: Path, executor_id: str) -> dict[str, Any]:
    samples = list(load(path).get("executors", {}).get(executor_id, []))
    valid = [row for row in samples if isinstance(row, dict) and isinstance(row.get("backend_seconds"), (int, float))]
    cold = [float(row["backend_seconds"]) for row in valid if row.get("cold") is True]
    warm = [float(row["backend_seconds"]) for row in valid if row.get("cold") is False]
    return {
        "executor_id": executor_id,
        "sample_count": len(valid),
        "last_seconds": float(valid[-1]["backend_seconds"]) if valid else None,
        "median_seconds": statistics.median(float(row["backend_seconds"]) for row in valid) if valid else None,
        "cold_median_seconds": statistics.median(cold) if cold else None,
        "warm_median_seconds": statistics.median(warm) if warm else None,
        "last_cold": bool(valid[-1].get("cold")) if valid else None,
        "last_recorded_at": valid[-1].get("recorded_at") if valid else None,
    }


def rank_available(path: Path, executor_ids: list[str], *, preferred: str = "") -> list[dict[str, Any]]:
    rows = [summary(path, executor_id) for executor_id in dict.fromkeys(executor_ids)]

    def key(row: dict[str, Any]) -> tuple[int, float, int, str]:
        measured = row["median_seconds"] is not None
        return (
            0 if measured else 1,
            float(row["median_seconds"] or 0.0),
            0 if row["executor_id"] == preferred else 1,
            str(row["executor_id"]),
        )

    return sorted(rows, key=key)
