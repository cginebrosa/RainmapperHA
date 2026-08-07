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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import fcntl
except ImportError:  # pragma: no cover - Rainmapper targets Unix platforms
    fcntl = None  # type: ignore[assignment]


SCHEMA_VERSION = "1.0"
MAX_RECORDS = 2_000
MAX_BYTES = 5 * 1024 * 1024
MAX_LOG_EXPORT_BYTES = 2 * 1024 * 1024
DEFAULT_DIAGNOSTICS_PATH = Path(
    "/share/rainmapper/diagnostics/runtime_metrics.jsonl"
)

_FILE_LOCK = threading.Lock()
_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(api(?:_|-)?key|access(?:_|-)?token|token|password)=([^&\s]+)"
)
_BEARER_PATTERN = re.compile(r"(?i)(authorization:\s*bearer\s+)(\S+)")


def diagnostics_path() -> Path:
    configured = os.environ.get("RAINMAPPER_RUNTIME_DIAGNOSTICS_PATH", "").strip()
    return Path(configured) if configured else DEFAULT_DIAGNOSTICS_PATH


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


def _compact_locked(path: Path, count_path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    retained_reversed: list[str] = []
    retained_bytes = 0
    for line in reversed(lines[-MAX_RECORDS:]):
        line_bytes = len((line + "\n").encode("utf-8"))
        if retained_reversed and retained_bytes + line_bytes > MAX_BYTES:
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


def _append_record(record: dict[str, Any], path: Path) -> bool:
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
                count += 1
                count_path.write_text(str(count), encoding="utf-8")
                if count > MAX_RECORDS or path.stat().st_size > MAX_BYTES:
                    _compact_locked(path, count_path)
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        return True
    except OSError:
        return False


def record_event(
    operation: str,
    operation_id: str,
    phase: str,
    details: dict[str, Any] | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    record = {
        "schema_version": SCHEMA_VERSION,
        "operation": operation,
        "operation_id": operation_id,
        "phase": phase,
        **snapshot(),
        "details": _json_safe(details or {}),
    }
    return record if _append_record(record, path or diagnostics_path()) else None


class OperationMonitor:
    """Sample one operation in memory and persist phase/summary records."""

    def __init__(
        self,
        operation: str,
        *,
        operation_id: str | None = None,
        details: dict[str, Any] | None = None,
        path: Path | None = None,
        sample_interval_seconds: float = 0.5,
    ) -> None:
        self.operation = operation
        self.operation_id = operation_id or new_operation_id(operation)
        self.path = path or diagnostics_path()
        self._started_at = time.perf_counter()
        self._start_snapshot = snapshot()
        self._sample_interval = max(0.05, sample_interval_seconds)
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
            details,
            self.path,
        )
        self.enabled = start_record is not None
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
        while not self._stop_event.wait(self._sample_interval):
            self._sample(snapshot())

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


def schedule_snapshot(
    operation: str,
    operation_id: str,
    phase: str,
    delay_seconds: float,
    details: dict[str, Any] | None = None,
    path: Path | None = None,
) -> threading.Timer:
    timer = threading.Timer(
        delay_seconds,
        record_event,
        args=(operation, operation_id, phase, details, path or diagnostics_path()),
    )
    timer.daemon = True
    timer.start()
    return timer


def export_bundle(
    *,
    last_run_log_path: Path,
    app_version: str,
    path: Path | None = None,
) -> bytes:
    metrics_path = path or diagnostics_path()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "app_version": app_version,
        "contents": ["runtime_metrics.jsonl", "last_run.log"],
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
            metrics = metrics_path.read_bytes()
        except OSError:
            metrics = b""
        try:
            last_run_log = _redact_log(_read_log_tail(last_run_log_path))
        except OSError:
            last_run_log = b""
        archive.writestr("runtime_metrics.jsonl", metrics)
        archive.writestr("last_run.log", last_run_log)
    return buffer.getvalue()
