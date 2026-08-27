"""Bounded persistent performance telemetry for mushroom maintenance jobs.

Durations are measured exclusively with a monotonic clock.  Wall-clock values
are informational labels only; they are never subtracted to obtain elapsed
times.  The recorder batches counters in memory and persists at phase
boundaries or explicit checkpoints so measurement does not create a new
high-frequency I/O path.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterator


SCHEMA_VERSION = "0.1"
KIND = "mushroom_operational_performance_telemetry"
COUNTER_NAMES = (
    "bytes_read",
    "bytes_written",
    "files_read",
    "files_written",
    "requests",
    "hashes",
    "hash_bytes",
    "copies",
    "copy_bytes",
    "fsyncs",
    "queue_persists",
    "queue_bytes_written",
)
MAX_PHASES = 128


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def empty_counters() -> dict[str, int]:
    return {name: 0 for name in COUNTER_NAMES}


def _counter_values(values: dict[str, int]) -> dict[str, int]:
    unknown = set(values) - set(COUNTER_NAMES)
    if unknown:
        raise ValueError(f"Unknown performance counters: {', '.join(sorted(unknown))}")
    normalized: dict[str, int] = {}
    for name, value in values.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Performance counter {name} must be a non-negative integer")
        normalized[name] = value
    return normalized


class PersistentTelemetry:
    """Persist bounded phase timings and I/O counters for one operation."""

    def __init__(
        self,
        path: Path,
        *,
        operation_id: str,
        workload: str,
        monotonic: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], str] = _utc_now,
    ) -> None:
        self.path = Path(path)
        self._monotonic = monotonic
        self._wall_clock = wall_clock
        self._started = monotonic()
        self._phase_started = self._started
        self._active_phase = "initializing"
        self._status = "running"
        self._error = ""
        self._counters = empty_counters()
        self._phase_counters = empty_counters()
        self._phases: list[dict[str, object]] = []
        self._operation_id = str(operation_id)[:160]
        self._workload = str(workload)[:160]
        self._started_at = wall_clock()
        self._finished_at = ""
        self.persist()

    def add(self, **values: int) -> None:
        for name, value in _counter_values(values).items():
            self._counters[name] += value
            self._phase_counters[name] += value

    def phase(self, name: str) -> None:
        resolved = str(name or "unnamed")[:160]
        if resolved == self._active_phase:
            return
        now = self._monotonic()
        self._close_phase(now, "complete")
        self._active_phase = resolved
        self._phase_started = now
        self._phase_counters = empty_counters()
        self.persist(now=now)

    def checkpoint(self) -> None:
        self.persist()

    def finish(self, status: str, *, error: str = "") -> dict[str, object]:
        if status not in {"complete", "failed", "cancelled"}:
            raise ValueError("Performance telemetry terminal status is invalid")
        if self._status == "running":
            now = self._monotonic()
            self._close_phase(now, status)
            self._active_phase = ""
            self._status = status
            self._error = str(error or "")[:1000]
            self._finished_at = self._wall_clock()
            self.persist(now=now)
        return self.snapshot()

    def snapshot(self, *, now: float | None = None) -> dict[str, object]:
        resolved_now = self._monotonic() if now is None else now
        phases = [dict(row) for row in self._phases]
        if self._status == "running" and self._active_phase:
            phases.append(
                self._phase_payload(
                    self._active_phase,
                    resolved_now - self._phase_started,
                    "running",
                    self._phase_counters,
                )
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": KIND,
            "operation_id": self._operation_id,
            "workload": self._workload,
            "clock": "monotonic",
            "counter_scope": "instrumented_application_io",
            "status": self._status,
            "started_at": self._started_at,
            "finished_at": self._finished_at,
            "elapsed_seconds": round(max(0.0, resolved_now - self._started), 6),
            "active_phase": self._active_phase,
            "phases": phases[-MAX_PHASES:],
            "counters": dict(self._counters),
            "error": self._error,
        }

    def persist(self, *, now: float | None = None) -> None:
        # Telemetry's own durable write is real I/O and is counted.  The byte
        # value converges after at most a few passes when its decimal width
        # changes.
        self._counters["files_written"] += 1
        self._phase_counters["files_written"] += 1
        self._counters["fsyncs"] += 2
        self._phase_counters["fsyncs"] += 2
        base_total = self._counters["bytes_written"]
        base_phase = self._phase_counters["bytes_written"]
        content = b""
        candidate_size = 0
        for _attempt in range(8):
            self._counters["bytes_written"] = base_total + candidate_size
            self._phase_counters["bytes_written"] = base_phase + candidate_size
            payload = self.snapshot(now=now)
            content = (
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
            ).encode("utf-8")
            resolved_size = len(content)
            if resolved_size == candidate_size:
                break
            candidate_size = resolved_size
        else:
            raise RuntimeError("Performance telemetry size did not converge")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            directory_descriptor = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _close_phase(self, now: float, status: str) -> None:
        if not self._active_phase:
            return
        self._phases.append(
            self._phase_payload(
                self._active_phase,
                now - self._phase_started,
                status,
                self._phase_counters,
            )
        )
        self._phases = self._phases[-MAX_PHASES:]

    @staticmethod
    def _phase_payload(
        name: str,
        duration: float,
        status: str,
        counters: dict[str, int],
    ) -> dict[str, object]:
        return {
            "name": name,
            "duration_seconds": round(max(0.0, duration), 6),
            "status": status,
            "counters": dict(counters),
        }


_CURRENT: ContextVar[PersistentTelemetry | None] = ContextVar(
    "mushroom_performance_telemetry", default=None
)


@contextmanager
def activate(recorder: PersistentTelemetry) -> Iterator[PersistentTelemetry]:
    token = _CURRENT.set(recorder)
    try:
        yield recorder
    finally:
        _CURRENT.reset(token)


def add(**values: int) -> None:
    recorder = _CURRENT.get()
    if recorder is not None:
        recorder.add(**values)


def phase(name: str) -> None:
    recorder = _CURRENT.get()
    if recorder is not None:
        recorder.phase(name)


def validate_summary(value: object) -> dict[str, object]:
    """Validate an untrusted worker telemetry summary before queue persistence."""
    if not isinstance(value, dict):
        raise ValueError("Worker performance telemetry must be an object")
    if value.get("schema_version") != SCHEMA_VERSION or value.get("kind") != KIND:
        raise ValueError("Worker performance telemetry contract is invalid")
    if value.get("clock") != "monotonic" or value.get("status") not in {
        "complete",
        "failed",
        "cancelled",
    }:
        raise ValueError("Worker performance telemetry state is invalid")
    elapsed = value.get("elapsed_seconds")
    if (
        not isinstance(elapsed, (int, float))
        or isinstance(elapsed, bool)
        or not math.isfinite(float(elapsed))
        or elapsed < 0
    ):
        raise ValueError("Worker performance elapsed time is invalid")
    counters = value.get("counters")
    if not isinstance(counters, dict) or set(counters) != set(COUNTER_NAMES):
        raise ValueError("Worker performance counters are invalid")
    _counter_values(counters)
    phases = value.get("phases")
    if not isinstance(phases, list) or len(phases) > MAX_PHASES:
        raise ValueError("Worker performance phases are invalid")
    normalized_phases: list[dict[str, object]] = []
    for row in phases:
        if not isinstance(row, dict):
            raise ValueError("Worker performance phase must be an object")
        duration = row.get("duration_seconds")
        name = str(row.get("name") or "")
        phase_counters = row.get("counters")
        if (
            not name
            or len(name) > 160
            or not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(float(duration))
            or duration < 0
            or row.get("status") not in {"complete", "failed", "cancelled"}
            or not isinstance(phase_counters, dict)
            or set(phase_counters) != set(COUNTER_NAMES)
        ):
            raise ValueError("Worker performance phase is invalid")
        _counter_values(phase_counters)
        normalized_phases.append(
            {
                "name": name,
                "duration_seconds": round(float(duration), 6),
                "status": row["status"],
                "counters": dict(phase_counters),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "operation_id": str(value.get("operation_id") or "")[:160],
        "workload": str(value.get("workload") or "")[:160],
        "clock": "monotonic",
        "counter_scope": "instrumented_application_io",
        "status": value["status"],
        "started_at": str(value.get("started_at") or "")[:80],
        "finished_at": str(value.get("finished_at") or "")[:80],
        "elapsed_seconds": round(float(elapsed), 6),
        "active_phase": "",
        "phases": normalized_phases,
        "counters": dict(counters),
        "error": str(value.get("error") or "")[:1000],
    }
