"""Low-overhead runtime diagnostics for runner and Predictor operations.

The module is deliberately best-effort: unavailable kernel/cgroup files or an
unwritable diagnostics directory must never break normal Rainmapper work.
"""

from __future__ import annotations

import io
import json
import os
import re
import resource
import sys
import threading
import time
import zipfile
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import fcntl
except ImportError:  # pragma: no cover - Rainmapper targets Unix platforms
    fcntl = None  # type: ignore[assignment]


SCHEMA_VERSION = "2.1"
MAX_RECORDS = 2_000
MAX_BYTES = 5 * 1024 * 1024
MAX_SUMMARY_RECORDS = 20_000
MAX_SUMMARY_BYTES = 20 * 1024 * 1024
MAX_ANOMALY_RECORDS = 5_000
MAX_ANOMALY_BYTES = 10 * 1024 * 1024
MAX_FAILURE_LOGS = 20
MAX_LOG_EXPORT_BYTES = 2 * 1024 * 1024
DEFAULT_DIAGNOSTICS_PATH = Path(
    "/share/rainmapper/diagnostics/runtime_metrics.jsonl"
)
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 10.0

_FILE_LOCK = threading.Lock()
_STATE_LOCK = threading.Lock()
_STATUS_CACHE_LOCK = threading.Lock()
_STATUS_CACHE_KEY: tuple[Any, ...] | None = None
_STATUS_CACHE_VALUE: dict[str, Any] | None = None
_CURRENT_OPERATION_ID: ContextVar[str | None] = ContextVar(
    "rainmapper_runtime_operation_id", default=None
)
_BOOT_ID: str | None = None
_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(api(?:_|-)?key|access(?:_|-)?token|token|password)=([^&\s]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)(authorization:\s*bearer\s+)(\S+)")


def diagnostics_path() -> Path:
    configured = os.environ.get("RAINMAPPER_RUNTIME_DIAGNOSTICS_PATH", "").strip()
    return Path(configured) if configured else DEFAULT_DIAGNOSTICS_PATH


def _artifact_path(metrics_path: Path, filename: str) -> Path:
    return metrics_path.with_name(filename)


def summary_path(path: Path | None = None) -> Path:
    return _artifact_path(path or diagnostics_path(), "runtime_summary.jsonl")


def anomalies_path(path: Path | None = None) -> Path:
    return _artifact_path(path or diagnostics_path(), "runtime_anomalies.jsonl")


def state_path(path: Path | None = None) -> Path:
    return _artifact_path(path or diagnostics_path(), "runtime_state.json")


def failure_logs_path(path: Path | None = None) -> Path:
    return _artifact_path(path or diagnostics_path(), "failed_operations")


def boot_id() -> str:
    global _BOOT_ID
    if _BOOT_ID is None:
        _BOOT_ID = new_operation_id("boot")
    return _BOOT_ID


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "boot_id": boot_id(),
        "pending_operations": {},
        "pending_snapshots": {},
    }


def _read_state(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return _empty_state()
    if not isinstance(payload, dict):
        return _empty_state()
    payload.setdefault("pending_operations", {})
    payload.setdefault("pending_snapshots", {})
    return payload


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _update_state(
    metrics_path: Path,
    update: Any,
) -> dict[str, Any] | None:
    path = state_path(metrics_path)
    lock_path = path.with_suffix(path.suffix + ".lock")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _STATE_LOCK, lock_path.open("a+", encoding="utf-8") as lock_handle:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                state = _read_state(path)
                update(state)
                state["schema_version"] = SCHEMA_VERSION
                state.setdefault("boot_id", boot_id())
                _write_json_atomic(path, state)
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        return state
    except OSError:
        return None


@contextmanager
def operation_context(operation_id: str):
    token = _CURRENT_OPERATION_ID.set(operation_id)
    try:
        yield
    finally:
        _CURRENT_OPERATION_ID.reset(token)


def new_operation_id(operation: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_operation = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in operation.strip().lower()
    ).strip("-") or "operation"
    return f"{timestamp}-{safe_operation}-{uuid4().hex[:8]}"


def _read_keyed_kib(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            key, separator, raw_value = line.partition(":")
            if not separator:
                continue
            first = raw_value.strip().split(" ", 1)[0]
            try:
                values[key] = float(first) / 1024.0
            except ValueError:
                continue
    except OSError:
        pass
    return values


def _read_bytes_mib(path: Path) -> float | None:
    try:
        raw_value = path.read_text(encoding="utf-8").strip()
        if not raw_value or raw_value == "max":
            return None
        return round(int(raw_value) / (1024 * 1024), 3)
    except (OSError, ValueError):
        return None


def _read_int_map(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            key, separator, raw_value = line.partition(" ")
            if separator:
                try:
                    values[key] = int(raw_value.strip())
                except ValueError:
                    continue
    except OSError:
        pass
    return values


def _cpu_temperature_c() -> float | None:
    for path in (
        Path("/sys/class/thermal/thermal_zone0/temp"),
        Path("/sys/class/hwmon/hwmon0/temp1_input"),
    ):
        try:
            value = float(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if value > 1_000:
            value /= 1_000.0
        if -20 <= value <= 150:
            return round(value, 2)
    return None


def _host_boot_id() -> str | None:
    try:
        value = Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return None
    return value or None


def _host_uptime_seconds() -> float | None:
    try:
        value = Path("/proc/uptime").read_text(encoding="utf-8").split()[0]
        return round(float(value), 3)
    except (OSError, ValueError, IndexError):
        return None


def snapshot() -> dict[str, Any]:
    """Return a portable process/container/host resource snapshot."""
    process_status = _read_keyed_kib(Path("/proc/self/status"))
    usage = resource.getrusage(resource.RUSAGE_SELF)
    fallback_peak_mib = (
        usage.ru_maxrss / (1024 * 1024)
        if sys.platform == "darwin"
        else usage.ru_maxrss / 1024.0
    )

    cgroup_root = Path("/sys/fs/cgroup")
    cgroup_current = _read_bytes_mib(cgroup_root / "memory.current")
    cgroup_peak = _read_bytes_mib(cgroup_root / "memory.peak")
    cgroup_limit = _read_bytes_mib(cgroup_root / "memory.max")
    cgroup_events = _read_int_map(cgroup_root / "memory.events")
    if cgroup_current is None:
        cgroup_current = _read_bytes_mib(
            cgroup_root / "memory" / "memory.usage_in_bytes"
        )
        cgroup_peak = _read_bytes_mib(
            cgroup_root / "memory" / "memory.max_usage_in_bytes"
        )
        cgroup_limit = _read_bytes_mib(
            cgroup_root / "memory" / "memory.limit_in_bytes"
        )

    host_meminfo = _read_keyed_kib(Path("/proc/meminfo"))
    return {
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        ),
        "pid": os.getpid(),
        "process_rss_mib": round(process_status.get("VmRSS", 0.0), 3)
        if process_status
        else None,
        "process_peak_rss_mib": round(
            process_status.get("VmHWM", fallback_peak_mib), 3
        ),
        "cgroup_memory_current_mib": cgroup_current,
        "cgroup_memory_peak_mib": cgroup_peak,
        "cgroup_memory_limit_mib": cgroup_limit,
        "host_mem_available_mib": round(
            host_meminfo.get("MemAvailable", 0.0), 3
        )
        if host_meminfo
        else None,
        "cpu_user_seconds": round(usage.ru_utime, 3),
        "cpu_system_seconds": round(usage.ru_stime, 3),
        "cpu_temperature_c": _cpu_temperature_c(),
        "cgroup_oom": cgroup_events.get("oom"),
        "cgroup_oom_kill": cgroup_events.get("oom_kill"),
        "host_boot_id": _host_boot_id(),
        "host_uptime_seconds": _host_uptime_seconds(),
    }


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return value.name
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return str(value)


def _redact_log(content: bytes) -> bytes:
    text = content.decode("utf-8", errors="replace")
    text = _SECRET_VALUE_PATTERN.sub(r"\1=[REDACTED]", text)
    text = _BEARER_PATTERN.sub(r"\1[REDACTED]", text)
    return text.encode("utf-8")


def _read_log_tail(path: Path) -> bytes:
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        if size <= MAX_LOG_EXPORT_BYTES:
            handle.seek(0)
            return handle.read()
        handle.seek(-MAX_LOG_EXPORT_BYTES, os.SEEK_END)
        tail = handle.read()
    first_newline = tail.find(b"\n")
    if first_newline >= 0:
        tail = tail[first_newline + 1 :]
    return b"[Earlier log output omitted from diagnostics export]\n" + tail


def _compact_locked(
    path: Path,
    count_path: Path,
    *,
    max_records: int,
    max_bytes: int,
) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    retained_reversed: list[str] = []
    retained_bytes = 0
    for line in reversed(lines[-max_records:]):
        line_bytes = len((line + "\n").encode("utf-8"))
        if retained_reversed and retained_bytes + line_bytes > max_bytes:
            break
        retained_reversed.append(line)
        retained_bytes += line_bytes
    retained = list(reversed(retained_reversed))
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary_path.write_text(
            "\n".join(retained) + ("\n" if retained else ""),
            encoding="utf-8",
        )
        temporary_path.replace(path)
        count_path.write_text(str(len(retained)), encoding="utf-8")
    finally:
        temporary_path.unlink(missing_ok=True)


def _append_bounded_record(
    record: dict[str, Any],
    path: Path,
    *,
    max_records: int,
    max_bytes: int,
) -> bool:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_suffix(path.suffix + ".lock")
        count_path = path.with_suffix(path.suffix + ".count")
        with _FILE_LOCK, lock_path.open("a+", encoding="utf-8") as lock_handle:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                if count_path.exists():
                    try:
                        count = int(count_path.read_text(encoding="utf-8").strip())
                    except (OSError, ValueError):
                        count = 0
                elif path.exists():
                    count = len(
                        path.read_text(encoding="utf-8", errors="replace").splitlines()
                    )
                else:
                    count = 0
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                count += 1
                count_path.write_text(str(count), encoding="utf-8")
                if count > max_records or path.stat().st_size > max_bytes:
                    _compact_locked(
                        path,
                        count_path,
                        max_records=max_records,
                        max_bytes=max_bytes,
                    )
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        return True
    except OSError:
        return False


def _append_record(record: dict[str, Any], path: Path) -> bool:
    return _append_bounded_record(
        record,
        path,
        max_records=MAX_RECORDS,
        max_bytes=MAX_BYTES,
    )


def record_event(
    operation: str,
    operation_id: str,
    phase: str,
    details: dict[str, Any] | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    record = {
        "schema_version": SCHEMA_VERSION,
        "boot_id": boot_id(),
        "operation": operation,
        "operation_id": operation_id,
        "phase": phase,
        **snapshot(),
        "details": _json_safe(details or {}),
    }
    return record if _append_record(record, path or diagnostics_path()) else None


def _summary_record(
    operation: str,
    operation_id: str,
    status: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "boot_id": boot_id(),
        "timestamp": _utc_now(),
        "operation": operation,
        "operation_id": operation_id,
        "status": status,
        "details": _json_safe(details),
    }


def _is_anomaly(status: str, details: dict[str, Any]) -> bool:
    if status not in {"ok", "snapshot", "started", "stopped", "unavailable"}:
        return True
    return bool(
        details.get("cgroup_oom_delta") or details.get("cgroup_oom_kill_delta")
    )


def record_summary(
    operation: str,
    operation_id: str,
    status: str,
    details: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any] | None:
    metrics_path = path or diagnostics_path()
    record = _summary_record(operation, operation_id, status, details)
    if not _append_bounded_record(
        record,
        summary_path(metrics_path),
        max_records=MAX_SUMMARY_RECORDS,
        max_bytes=MAX_SUMMARY_BYTES,
    ):
        return None
    if _is_anomaly(status, details):
        _append_bounded_record(
            record,
            anomalies_path(metrics_path),
            max_records=MAX_ANOMALY_RECORDS,
            max_bytes=MAX_ANOMALY_BYTES,
        )
    return record


def _register_pending_operation(
    operation: str,
    operation_id: str,
    details: dict[str, Any],
    metrics_path: Path,
) -> None:
    def update(state: dict[str, Any]) -> None:
        pending = state.setdefault("pending_operations", {})
        if isinstance(pending, dict):
            pending[operation_id] = {
                "operation": operation,
                "operation_id": operation_id,
                "boot_id": boot_id(),
                "started_at": _utc_now(),
                "details": _json_safe(details),
            }

    _update_state(metrics_path, update)


def _clear_pending_operation(operation_id: str, metrics_path: Path) -> None:
    def update(state: dict[str, Any]) -> None:
        pending = state.setdefault("pending_operations", {})
        if isinstance(pending, dict):
            pending.pop(operation_id, None)

    _update_state(metrics_path, update)


def initialize_runtime(
    app_version: str,
    path: Path | None = None,
    *,
    last_run_log_path: Path | None = None,
) -> str:
    """Start a boot session and reconcile work left pending by an earlier boot."""
    global _BOOT_ID
    _BOOT_ID = new_operation_id("boot")
    metrics_path = path or diagnostics_path()
    previous_state = _read_state(state_path(metrics_path))
    previous_operations = previous_state.get("pending_operations", {})
    previous_snapshots = previous_state.get("pending_snapshots", {})
    previous_boot_id = previous_state.get("boot_id")
    previous_started_at = previous_state.get("started_at")
    previous_stopped_at = previous_state.get("stopped_at")
    previous_host_boot_id = previous_state.get("host_boot_id")
    recent_summaries = _read_recent_jsonl(summary_path(metrics_path), limit=500)
    completed_operation_ids = {
        str(record.get("operation_id"))
        for record in recent_summaries
        if record.get("status")
        in {"ok", "error", "degraded", "unavailable", "interrupted"}
    }
    recent_metrics = _read_recent_jsonl(metrics_path, limit=500)
    captured_snapshots = {
        (str(record.get("operation_id")), str(record.get("phase")))
        for record in recent_metrics
    }

    current_host = snapshot()

    def reset(state: dict[str, Any]) -> None:
        state["boot_id"] = boot_id()
        state["pending_operations"] = {}
        state["pending_snapshots"] = {}
        state["started_at"] = _utc_now()
        state.pop("stopped_at", None)
        state["app_version"] = app_version
        state["host_boot_id"] = current_host.get("host_boot_id")
        state["host_uptime_seconds"] = current_host.get("host_uptime_seconds")

    _update_state(metrics_path, reset)
    record_event(
        "runtime_boot",
        boot_id(),
        "start",
        {
            "app_version": app_version,
            "reconciled_operations": len(previous_operations)
            if isinstance(previous_operations, dict)
            else 0,
            "reconciled_snapshots": len(previous_snapshots)
            if isinstance(previous_snapshots, dict)
            else 0,
        },
        metrics_path,
    )
    record_summary(
        "runtime_boot",
        boot_id(),
        "started",
        {"app_version": app_version},
        metrics_path,
    )
    if (
        previous_started_at
        and previous_boot_id
        and previous_boot_id != boot_id()
        and not previous_stopped_at
    ):
        interrupted_boot = {
            "started_at": previous_started_at,
            "reason": "process_restarted_without_stop",
            "oom_attribution": "unknown",
        }
        record_event(
            "runtime_boot",
            str(previous_boot_id),
            "interrupted",
            interrupted_boot,
            metrics_path,
        )
        record_summary(
            "runtime_boot",
            str(previous_boot_id),
            "interrupted",
            interrupted_boot,
            metrics_path,
        )
    archived_interrupted_log_id: str | None = None
    if isinstance(previous_operations, dict) and last_run_log_path is not None:
        runner_candidates = [
            str(operation_id)
            for operation_id, pending in previous_operations.items()
            if isinstance(pending, dict)
            and pending.get("operation") == "runner_action"
            and str(operation_id) not in completed_operation_ids
        ]
        if not runner_candidates:
            runner_candidates = [
                str(operation_id)
                for operation_id, pending in previous_operations.items()
                if isinstance(pending, dict)
                and pending.get("operation") == "runner_update"
                and str(operation_id) not in completed_operation_ids
            ]
        if runner_candidates and last_run_log_path.is_file():
            archived_interrupted_log_id = runner_candidates[0]
            _archive_failure_log(
                archived_interrupted_log_id,
                last_run_log_path,
                metrics_path,
            )

    if isinstance(previous_operations, dict):
        for operation_id, pending in previous_operations.items():
            if not isinstance(pending, dict):
                continue
            if str(operation_id) in completed_operation_ids:
                continue
            operation = str(pending.get("operation", "unknown"))
            details = {
                "status": "interrupted",
                "started_at": pending.get("started_at"),
                "previous_boot_id": pending.get("boot_id"),
                "reason": "process_restarted_before_finish",
                "oom_attribution": "unknown",
                "previous_host_boot_id": previous_host_boot_id,
                "current_host_boot_id": current_host.get("host_boot_id"),
                "interrupted_log_archived": (
                    str(operation_id) == archived_interrupted_log_id
                ),
            }
            record_event(
                operation,
                str(operation_id),
                "interrupted",
                details,
                metrics_path,
            )
            record_summary(
                operation,
                str(operation_id),
                "interrupted",
                details,
                metrics_path,
            )
    if isinstance(previous_snapshots, dict):
        for snapshot_key, pending in previous_snapshots.items():
            if not isinstance(pending, dict):
                continue
            if (
                str(pending.get("operation_id", snapshot_key)),
                str(pending.get("phase")),
            ) in captured_snapshots:
                continue
            record_event(
                str(pending.get("operation", "unknown")),
                str(pending.get("operation_id", snapshot_key)),
                "snapshot_interrupted",
                {
                    "target_phase": pending.get("phase"),
                    "due_at": pending.get("due_at"),
                    "previous_boot_id": pending.get("boot_id"),
                },
                metrics_path,
            )
            record_summary(
                "diagnostic_snapshot",
                str(snapshot_key),
                "interrupted",
                {
                    "parent_operation": pending.get("operation"),
                    "parent_operation_id": pending.get("operation_id"),
                    "target_phase": pending.get("phase"),
                    "due_at": pending.get("due_at"),
                    "previous_boot_id": pending.get("boot_id"),
                },
                metrics_path,
            )
    return boot_id()


def shutdown_runtime(path: Path | None = None) -> None:
    metrics_path = path or diagnostics_path()
    record_event("runtime_boot", boot_id(), "stop", {}, metrics_path)
    record_summary("runtime_boot", boot_id(), "stopped", {}, metrics_path)

    def update(state: dict[str, Any]) -> None:
        state["stopped_at"] = _utc_now()

    _update_state(metrics_path, update)


class OperationMonitor:
    """Sample one operation in memory and persist phase/summary records."""

    def __init__(
        self,
        operation: str,
        *,
        operation_id: str | None = None,
        details: dict[str, Any] | None = None,
        path: Path | None = None,
        failure_log_path: Path | None = None,
        sample_interval_seconds: float = 0.5,
        heartbeat_interval_seconds: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        self.operation = operation
        self.operation_id = operation_id or new_operation_id(operation)
        self.path = path or diagnostics_path()
        self.failure_log_path = failure_log_path
        parent_operation_id = _CURRENT_OPERATION_ID.get()
        operation_details = dict(details or {})
        if parent_operation_id and parent_operation_id != self.operation_id:
            operation_details.setdefault("parent_operation_id", parent_operation_id)
        self._operation_details = operation_details
        self._started_at = time.perf_counter()
        self._start_snapshot = snapshot()
        self._sample_interval = max(0.05, sample_interval_seconds)
        self._heartbeat_interval = max(0.05, heartbeat_interval_seconds)
        self._stop_event = threading.Event()
        self._finished = False
        self._aggregate: dict[str, float | None] = {
            "max_process_rss_mib": None,
            "max_process_peak_rss_mib": None,
            "max_cgroup_memory_current_mib": None,
            "max_cgroup_memory_peak_mib": None,
            "min_host_mem_available_mib": None,
            "max_cpu_temperature_c": None,
        }
        start_record = record_event(
            operation,
            self.operation_id,
            "start",
            operation_details,
            self.path,
        )
        self.enabled = start_record is not None
        if self.enabled:
            _register_pending_operation(
                operation,
                self.operation_id,
                operation_details,
                self.path,
            )
        self._sample(self._start_snapshot)
        self._thread: threading.Thread | None = None
        if self.enabled:
            self._thread = threading.Thread(
                target=self._sampling_loop,
                name=f"diagnostics-{operation}",
                daemon=True,
            )
            self._thread.start()

    def _sample(self, current: dict[str, Any]) -> None:
        maximum_fields = {
            "process_rss_mib": "max_process_rss_mib",
            "process_peak_rss_mib": "max_process_peak_rss_mib",
            "cgroup_memory_current_mib": "max_cgroup_memory_current_mib",
            "cgroup_memory_peak_mib": "max_cgroup_memory_peak_mib",
            "cpu_temperature_c": "max_cpu_temperature_c",
        }
        for source, target in maximum_fields.items():
            value = current.get(source)
            if isinstance(value, (int, float)):
                previous = self._aggregate[target]
                self._aggregate[target] = value if previous is None else max(previous, value)
        available = current.get("host_mem_available_mib")
        if isinstance(available, (int, float)):
            previous = self._aggregate["min_host_mem_available_mib"]
            self._aggregate["min_host_mem_available_mib"] = (
                available if previous is None else min(previous, available)
            )

    def _sampling_loop(self) -> None:
        next_heartbeat = time.monotonic() + self._heartbeat_interval
        while not self._stop_event.wait(self._sample_interval):
            self._sample(snapshot())
            now = time.monotonic()
            if now < next_heartbeat:
                continue
            record_event(
                self.operation,
                self.operation_id,
                "heartbeat",
                {
                    "status": "running",
                    "elapsed_seconds": round(
                        time.perf_counter() - self._started_at, 3
                    ),
                    **self._aggregate,
                },
                self.path,
            )
            next_heartbeat = now + self._heartbeat_interval

    def mark(self, phase: str, details: dict[str, Any] | None = None) -> None:
        current = snapshot()
        self._sample(current)
        if self.enabled:
            record_event(
                self.operation,
                self.operation_id,
                phase,
                details,
                self.path,
            )

    def finish(
        self,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        if self._finished:
            return
        self._finished = True
        self._stop_event.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
        current = snapshot()
        self._sample(current)
        summary = {
            **(details or {}),
            "status": status,
            "wall_seconds": round(time.perf_counter() - self._started_at, 3),
            "cpu_user_seconds": round(
                float(current.get("cpu_user_seconds") or 0)
                - float(self._start_snapshot.get("cpu_user_seconds") or 0),
                3,
            ),
            "cpu_system_seconds": round(
                float(current.get("cpu_system_seconds") or 0)
                - float(self._start_snapshot.get("cpu_system_seconds") or 0),
                3,
            ),
            **self._aggregate,
            "cgroup_oom": current.get("cgroup_oom"),
            "cgroup_oom_kill": current.get("cgroup_oom_kill"),
            "cgroup_oom_delta": max(
                0,
                int(current.get("cgroup_oom") or 0)
                - int(self._start_snapshot.get("cgroup_oom") or 0),
            ),
            "cgroup_oom_kill_delta": max(
                0,
                int(current.get("cgroup_oom_kill") or 0)
                - int(self._start_snapshot.get("cgroup_oom_kill") or 0),
            ),
        }
        cpu_seconds = summary["cpu_user_seconds"] + summary["cpu_system_seconds"]
        summary["cpu_percent_one_core"] = round(
            100 * cpu_seconds / max(summary["wall_seconds"], 0.001),
            1,
        )
        if self.enabled:
            record_event(
                self.operation,
                self.operation_id,
                "finish",
                summary,
                self.path,
            )
            record_summary(
                self.operation,
                self.operation_id,
                status,
                {**self._operation_details, **summary},
                self.path,
            )
            _clear_pending_operation(self.operation_id, self.path)
            if status not in {"ok", "unavailable"} and self.failure_log_path:
                _archive_failure_log(
                    self.operation_id,
                    self.failure_log_path,
                    self.path,
                )


def _archive_failure_log(
    operation_id: str,
    source_path: Path,
    metrics_path: Path,
) -> None:
    directory = failure_logs_path(metrics_path)
    try:
        content = _redact_log(_read_log_tail(source_path))
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{operation_id}.log"
        temporary_path = directory / f".{target.name}.{uuid4().hex}.tmp"
        try:
            temporary_path.write_bytes(content)
            temporary_path.replace(target)
        finally:
            temporary_path.unlink(missing_ok=True)
        retained = sorted(
            (item for item in directory.glob("*.log") if item.is_file()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for stale in retained[MAX_FAILURE_LOGS:]:
            stale.unlink(missing_ok=True)
    except OSError:
        pass


def schedule_snapshot(
    operation: str,
    operation_id: str,
    phase: str,
    delay_seconds: float,
    details: dict[str, Any] | None = None,
    path: Path | None = None,
) -> threading.Timer:
    metrics_path = path or diagnostics_path()
    snapshot_key = f"{operation_id}:{phase}"

    def register(state: dict[str, Any]) -> None:
        pending = state.setdefault("pending_snapshots", {})
        if isinstance(pending, dict):
            pending[snapshot_key] = {
                "operation": operation,
                "operation_id": operation_id,
                "phase": phase,
                "boot_id": boot_id(),
                "due_at": (
                    datetime.now(UTC) + timedelta(seconds=max(0.0, delay_seconds))
                ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "details": _json_safe(details or {}),
            }

    _update_state(metrics_path, register)

    def capture() -> None:
        record = record_event(
            operation, operation_id, phase, details, metrics_path
        )
        if record is not None:
            resource_fields = {
                key: record.get(key)
                for key in (
                    "process_rss_mib",
                    "process_peak_rss_mib",
                    "cgroup_memory_current_mib",
                    "cgroup_memory_peak_mib",
                    "host_mem_available_mib",
                    "cpu_temperature_c",
                    "cgroup_oom",
                    "cgroup_oom_kill",
                )
            }
            record_summary(
                operation,
                operation_id,
                "snapshot",
                {"phase": phase, **(details or {}), **resource_fields},
                metrics_path,
            )

        def clear(state: dict[str, Any]) -> None:
            pending = state.setdefault("pending_snapshots", {})
            if isinstance(pending, dict):
                pending.pop(snapshot_key, None)

        _update_state(metrics_path, clear)

    timer = threading.Timer(
        delay_seconds,
        capture,
    )
    timer.daemon = True
    timer.start()
    return timer


_CLIENT_TIMING_FIELDS = {
    "response_start_ms",
    "response_end_ms",
    "dom_interactive_ms",
    "dom_content_loaded_ms",
    "load_event_ms",
    "transfer_size_bytes",
    "encoded_body_size_bytes",
    "decoded_body_size_bytes",
}


def record_predictor_client_timing(
    operation_id: str,
    payload: dict[str, Any],
    path: Path | None = None,
) -> bool:
    """Persist allow-listed browser navigation timing for one Predictor request."""
    if not re.fullmatch(
        r"\d{8}T\d{6}Z-predictor_request-[0-9a-f]{8}", operation_id
    ):
        return False
    details: dict[str, Any] = {}
    for field in _CLIENT_TIMING_FIELDS:
        value = payload.get(field)
        if isinstance(value, (int, float)) and 0 <= float(value) <= 86_400_000:
            details[field] = round(float(value), 3)
    navigation_type = str(payload.get("navigation_type", ""))
    if navigation_type in {"navigate", "reload", "back_forward", "prerender"}:
        details["navigation_type"] = navigation_type
    if not details:
        return False
    metrics_path = path or diagnostics_path()
    known_request = any(
        record.get("operation") == "predictor_request"
        and record.get("operation_id") == operation_id
        and record.get("phase") == "start"
        for record in _read_recent_jsonl(metrics_path, limit=250)
    )
    if not known_request:
        return False
    record_event(
        "predictor_client_render",
        operation_id,
        "client_loaded",
        details,
        metrics_path,
    )
    record_summary(
        "predictor_client_render",
        operation_id,
        "ok",
        details,
        metrics_path,
    )
    return True


def _read_recent_jsonl(
    path: Path,
    limit: int = 250,
    max_bytes: int = 512 * 1024,
) -> list[dict[str, Any]]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            content = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    if size > max_bytes:
        content = content.split("\n", 1)[-1]
    records: list[dict[str, Any]] = []
    for line in content.splitlines()[-limit:]:
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def diagnostics_status(path: Path | None = None) -> dict[str, Any]:
    """Return a small dashboard summary without exposing operation payloads."""
    global _STATUS_CACHE_KEY, _STATUS_CACHE_VALUE
    metrics_path = path or diagnostics_path()
    source_paths = (
        summary_path(metrics_path),
        anomalies_path(metrics_path),
        state_path(metrics_path),
    )

    def signature(source_path: Path) -> tuple[int, int]:
        try:
            stat = source_path.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return 0, 0

    cache_key = (str(metrics_path), *(signature(item) for item in source_paths))
    with _STATUS_CACHE_LOCK:
        if cache_key == _STATUS_CACHE_KEY and _STATUS_CACHE_VALUE is not None:
            return dict(_STATUS_CACHE_VALUE)

    summaries = _read_recent_jsonl(source_paths[0])
    anomalies = _read_recent_jsonl(
        source_paths[1],
        limit=MAX_ANOMALY_RECORDS,
        max_bytes=MAX_ANOMALY_BYTES,
    )
    last_success = next(
        (record for record in reversed(summaries) if record.get("status") == "ok"),
        None,
    )
    last_failure = next(
        (
            record
            for record in reversed(anomalies)
            if record.get("status") in {"error", "degraded", "interrupted"}
        ),
        None,
    )
    last_oom = next(
        (
            record
            for record in reversed(anomalies)
            if isinstance(record.get("details"), dict)
            and (
                record["details"].get("cgroup_oom_delta")
                or record["details"].get("cgroup_oom_kill_delta")
            )
        ),
        None,
    )
    recent_cgroup_peaks = [
        record.get("details", {}).get("max_cgroup_memory_current_mib")
        for record in summaries
        if isinstance(record.get("details"), dict)
        and isinstance(
            record.get("details", {}).get("max_cgroup_memory_current_mib"),
            (int, float),
        )
    ]

    def compact(record: dict[str, Any] | None) -> dict[str, Any] | None:
        if not record:
            return None
        return {
            "timestamp": record.get("timestamp"),
            "operation": record.get("operation"),
            "status": record.get("status"),
        }

    current_state = _read_state(source_paths[2])
    pending_operations = current_state.get("pending_operations", {})
    result = {
        "boot_id": current_state.get("boot_id") or boot_id(),
        "last_success": compact(last_success),
        "last_failure": compact(last_failure),
        "last_oom": compact(last_oom),
        "recent_max_cgroup_mib": max(recent_cgroup_peaks)
        if recent_cgroup_peaks
        else None,
        "pending_operation_count": len(pending_operations)
        if isinstance(pending_operations, dict)
        else 0,
    }
    with _STATUS_CACHE_LOCK:
        _STATUS_CACHE_KEY = cache_key
        _STATUS_CACHE_VALUE = dict(result)
    return result


def export_bundle(
    *,
    last_run_log_path: Path,
    app_version: str,
    path: Path | None = None,
) -> bytes:
    metrics_path = path or diagnostics_path()
    persistent_files = {
        "runtime_metrics.jsonl": metrics_path,
        "runtime_summary.jsonl": summary_path(metrics_path),
        "runtime_anomalies.jsonl": anomalies_path(metrics_path),
        "runtime_state.json": state_path(metrics_path),
    }
    failed_logs = sorted(failure_logs_path(metrics_path).glob("*.log"))
    contents = [*persistent_files, "last_run.log"] + [
        f"failed_operations/{item.name}" for item in failed_logs
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "app_version": app_version,
        "contents": contents,
        "last_run_log_max_bytes": MAX_LOG_EXPORT_BYTES,
        "privacy": "No configuration, credentials, observations, media, models or weather datasets.",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        try:
            last_run_log = _redact_log(_read_log_tail(last_run_log_path))
        except OSError:
            last_run_log = b""
        for archive_name, source_path in persistent_files.items():
            try:
                content = source_path.read_bytes()
            except OSError:
                content = b"{}\n" if archive_name.endswith(".json") else b""
            archive.writestr(archive_name, content)
        archive.writestr("last_run.log", last_run_log)
        for failed_log in failed_logs:
            try:
                content = _redact_log(_read_log_tail(failed_log))
            except OSError:
                continue
            archive.writestr(f"failed_operations/{failed_log.name}", content)
    return buffer.getvalue()
