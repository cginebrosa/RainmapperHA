"""Local status service for the portable Rainmapper worker."""

from __future__ import annotations

import json
import hashlib
import http.client
import os
import platform
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit

from rainmapper_core import mushroom_worker_dataset_cache
from rainmapper_core import mushroom_worker_config
from rainmapper_core import mushroom_worker_transport
from rainmapper_core import mushroom_worker_results
from rainmapper_core import mushroom_worker_jobs
from rainmapper_core import mushroom_worker_registry
from rainmapper_core import mushroom_predictor_runtime
from rainmapper_core import mushroom_predictor_precompute
from rainmapper_core import mushroom_predictor_precompute_control
from rainmapper_core import mushroom_ml_multiversion_transport
from rainmapper_core.mushroom_predictor_service import PredictorService


SCHEMA_VERSION = "0.1"
IDENTITY_SCHEMA_VERSION = "0.1"
IDENTITY_RELATIVE_PATH = Path("identity/worker.json")
JOB_TELEMETRY_INTERVAL_SECONDS = 10.0
PREDICTOR_RUNTIME_MANIFEST_MAX_BYTES = 8 * 1024 * 1024
PREDICTOR_PRECOMPUTE_SELECTIONS_MAX_BYTES = 16 * 1024 * 1024
PREDICTOR_FINISH_TIMEOUT_SECONDS = 60.0
_T = TypeVar("_T")


def _job_update_timeout(action: str, job_type: str) -> float:
    return (
        PREDICTOR_FINISH_TIMEOUT_SECONDS
        if action == "finish" and job_type == "worker_predictor_v1"
        else 3.0
    )


class _CoalescedJobTelemetry:
    """Publish only the latest job telemetry without blocking local computation."""

    def __init__(
        self,
        update: Callable[[str, dict[str, Any]], dict[str, Any]],
        *,
        base_payload: dict[str, Any],
        cancel_message: str,
        interval_seconds: float = JOB_TELEMETRY_INTERVAL_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._update = update
        self._base_payload = dict(base_payload)
        self._cancel_message = cancel_message
        self._interval_seconds = max(0.0, interval_seconds)
        self._monotonic = monotonic
        self._next_control_at = 0.0
        self._next_progress_at = 0.0
        self._pending_progress: dict[str, Any] | None = None
        self._pending_revision = 0
        self._lock = threading.Lock()
        self._inflight: threading.Thread | None = None
        self._terminal_error: BaseException | None = None

    def _raise_terminal_error(self) -> None:
        with self._lock:
            error = self._terminal_error
        if error is not None:
            raise error

    def _run_exchange(
        self,
        *,
        send_control: bool,
        progress: dict[str, Any] | None,
        progress_revision: int,
    ) -> None:
        progress_sent = False
        try:
            if send_control:
                control = self._update("control", dict(self._base_payload))
                if control.get("cancel_requested"):
                    error = InterruptedError(self._cancel_message)
                    setattr(
                        error,
                        "force_cancel_requested",
                        bool(control.get("force_cancel_requested")),
                    )
                    raise error
            if progress is not None:
                self._update("progress", progress)
                progress_sent = True
        except (URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            pass
        except BaseException as exc:
            with self._lock:
                self._terminal_error = exc
        finally:
            with self._lock:
                if progress_sent and self._pending_revision == progress_revision:
                    self._pending_progress = None
                self._inflight = None

    def _schedule(
        self,
        *,
        force_control: bool = False,
        force_progress: bool = False,
    ) -> None:
        with self._lock:
            if self._inflight is not None:
                return
            now = self._monotonic()
            send_control = force_control or now >= self._next_control_at
            send_progress = self._pending_progress is not None and (
                force_progress or now >= self._next_progress_at
            )
            if not send_control and not send_progress:
                return
            if send_control:
                self._next_control_at = now + self._interval_seconds
            if send_progress:
                self._next_progress_at = now + self._interval_seconds
            progress = dict(self._pending_progress) if send_progress else None
            progress_revision = self._pending_revision
            thread = threading.Thread(
                target=self._run_exchange,
                kwargs={
                    "send_control": send_control,
                    "progress": progress,
                    "progress_revision": progress_revision,
                },
                daemon=True,
                name="rainmapper-worker-job-telemetry",
            )
            self._inflight = thread
            thread.start()

    def _wait_for_idle(self) -> None:
        while True:
            with self._lock:
                thread = self._inflight
            if thread is None:
                return
            thread.join()

    def poll_control(self, *, force: bool = False) -> dict[str, Any]:
        self._raise_terminal_error()
        self._schedule(force_control=force)
        self._raise_terminal_error()
        return {}

    def publish(self, progress: dict[str, Any], *, force: bool = False) -> None:
        self._raise_terminal_error()
        with self._lock:
            self._pending_progress = {**self._base_payload, **progress}
            self._pending_revision += 1
        self._schedule(force_control=force, force_progress=force)
        self._raise_terminal_error()

    def flush(self) -> None:
        self._wait_for_idle()
        self._raise_terminal_error()
        self._schedule(force_control=True, force_progress=True)
        self._wait_for_idle()
        self._raise_terminal_error()


def retry_transient(
    operation: Callable[[], _T],
    *,
    retry_seconds: float | None,
    retry_interval: float = 1.0,
    stop_event: threading.Event | None = None,
    on_retry: Callable[[], None] | None = None,
) -> _T:
    """Retry transport outages, optionally without a deadline, but not HTTP contract failures."""
    deadline = None if retry_seconds is None else time.monotonic() + max(0.0, retry_seconds)
    while True:
        try:
            return operation()
        except HTTPError:
            raise
        except (URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            if (
                (deadline is not None and time.monotonic() >= deadline)
                or (stop_event is not None and stop_event.is_set())
            ):
                raise
            if on_retry is not None:
                on_retry()
            wait_seconds = max(0.01, retry_interval)
            if deadline is not None:
                wait_seconds = min(wait_seconds, max(0.01, deadline - time.monotonic()))
            if stop_event is None:
                time.sleep(wait_seconds)
            else:
                stop_event.wait(wait_seconds)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def ensure_worker_identity(
    worker_data_dir: Path,
    *,
    display_name: str = "",
    host_name: str = "",
) -> dict[str, str]:
    identity_path = worker_data_dir / IDENTITY_RELATIVE_PATH
    identity: dict[str, Any] = {}
    if identity_path.exists():
        try:
            loaded = json.loads(identity_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot load worker identity: {exc}") from exc
        if not isinstance(loaded, dict) or loaded.get("schema_version") != IDENTITY_SCHEMA_VERSION:
            raise ValueError("Worker identity schema is invalid.")
        identity = loaded
    worker_id = str(identity.get("worker_id", "") or "").strip()
    if not worker_id:
        worker_id = f"worker_{secrets.token_hex(8)}"
    current_host_name = str(host_name or identity.get("host_name") or platform.node() or "unknown-host").strip()[:255]
    current_display_name = str(display_name or identity.get("display_name") or current_host_name).strip()[:80]
    if not current_display_name or not current_host_name:
        raise ValueError("Worker identity requires a display name and host name.")
    updated = {
        "schema_version": IDENTITY_SCHEMA_VERSION,
        "worker_id": worker_id,
        "display_name": current_display_name,
        "host_name": current_host_name,
    }
    if identity != updated:
        _write_json_atomic(identity_path, updated)
    return {key: str(value) for key, value in updated.items()}


def worker_status(
    worker_data_dir: Path,
    *,
    worker_version: str | None = None,
    identity: dict[str, str] | None = None,
    runtime_status: str = "",
) -> dict[str, Any]:
    cache = mushroom_worker_dataset_cache.verify_version(
        worker_data_dir,
        dataset_id=mushroom_worker_dataset_cache.DEFAULT_DATASET_ID,
        deep=False,
    )
    cache_ready = cache["status"] == "valid"
    predictor_runtime = mushroom_predictor_runtime.current_runtime(
        worker_data_dir / "predictor-runtime"
    )
    predictor_manifest: dict[str, Any] = {}
    if predictor_runtime is not None:
        try:
            predictor_manifest = json.loads(
                (predictor_runtime / "manifest.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            predictor_manifest = {}
    identity = identity or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "rainmapper_worker_status",
        "service": "rainmapper-worker",
        "worker_id": identity.get("worker_id", ""),
        "display_name": identity.get("display_name", ""),
        "host_name": identity.get("host_name", ""),
        "architecture": platform.machine(),
        "platform": platform.system(),
        "worker_version": worker_version or os.environ.get("RAINMAPPER_WORKER_VERSION", "local"),
        "status": (runtime_status or "idle") if cache_ready else "needs_dataset",
        "job_api": "candidate_rebuild_v0",
        "capabilities": [
            "rebuild_v0",
            mushroom_worker_registry.WEATHER_PARQUET_CAPABILITY,
            mushroom_worker_registry.PARTITIONED_WEATHER_HISTORY_CAPABILITY,
            mushroom_worker_registry.TERMINAL_JOB_CLEANUP_CAPABILITY,
            mushroom_worker_registry.PREDICTOR_CAPABILITY,
            mushroom_worker_registry.PREDICTOR_PRECOMPUTE_CAPABILITY,
            mushroom_worker_registry.PREDICTOR_MULTIVERSION_CAPABILITY,
            mushroom_worker_registry.ML_MULTIVERSION_TRAINING_CAPABILITY,
            mushroom_worker_registry.ML_JOB_PURPOSE_CAPABILITY,
            mushroom_worker_registry.ML_BENCHMARK_REPORT_CAPABILITY,
        ],
        "dataset_cache": {
            "status": cache["status"],
            "dataset_id": cache["dataset_id"],
            "fingerprint": cache["fingerprint"],
            "validation": cache["validation"],
            "file_count": cache["file_count"],
            "size_bytes": cache["size_bytes"],
        },
        "predictor_cache": {
            "status": "valid" if predictor_manifest.get("fingerprint") else "empty",
            "fingerprint": str(predictor_manifest.get("fingerprint", "")),
            "size_bytes": int(predictor_manifest.get("size_bytes", 0) or 0),
        },
    }


def download_predictor_runtime(
    ha_url: str,
    job: dict[str, Any],
    worker_data_dir: Path,
    *,
    worker_id: str,
    claim_token: str,
    token: str,
) -> tuple[Path, dict[str, Any]]:
    endpoint = str(job.get("runtime_endpoint", ""))
    if endpoint != "/api/mushrooms/workers/jobs/predictor-runtime":
        raise ValueError("Worker predictor runtime endpoint is invalid.")
    headers = mushroom_worker_transport.request_headers(worker_id, claim_token, token)
    manifest_payload = job.get("runtime_manifest")
    if not isinstance(manifest_payload, dict):
        manifest_query = urlencode({"job_id": job.get("job_id", ""), "manifest": "1"})
        manifest_request = Request(
            ha_url.rstrip("/") + endpoint + "?" + manifest_query,
            headers=headers,
            method="GET",
        )
        with urlopen(manifest_request, timeout=120) as response:
            raw_manifest = response.read(PREDICTOR_RUNTIME_MANIFEST_MAX_BYTES + 1)
        if len(raw_manifest) > PREDICTOR_RUNTIME_MANIFEST_MAX_BYTES:
            raise ValueError("Worker predictor runtime manifest is too large.")
        manifest_response = json.loads(raw_manifest.decode("utf-8"))
        if not isinstance(manifest_response, dict) or not manifest_response.get("ok"):
            raise ValueError("HA returned an invalid predictor runtime manifest.")
        manifest_payload = manifest_response.get("manifest")
    manifest = mushroom_predictor_runtime.validate_manifest(manifest_payload)
    job["runtime_manifest"] = manifest

    runtime_cache_root = worker_data_dir.resolve() / "predictor-runtime"
    objects_root = runtime_cache_root / "objects"
    has_local_objects = objects_root.is_dir() and any(objects_root.iterdir())
    has_current_runtime = (
        mushroom_predictor_runtime.current_runtime(runtime_cache_root) is not None
    )
    if not has_local_objects and not has_current_runtime:
        archive_query = urlencode({"job_id": job.get("job_id", ""), "archive": "1"})
        archive_request = Request(
            ha_url.rstrip("/") + endpoint + "?" + archive_query,
            headers=headers,
            method="GET",
        )
        archive_limit = int(manifest.get("size_bytes", 0) or 0) + max(
            64 * 1024 * 1024,
            len(manifest["files"]) * 4096,
        )
        try:
            with (
                urlopen(archive_request, timeout=120) as response,
                tempfile.NamedTemporaryFile(
                    prefix="predictor-runtime-",
                    suffix=".tar",
                    dir=worker_data_dir.resolve(),
                ) as archive_handle,
            ):
                copied = 0
                while chunk := response.read(1024 * 1024):
                    copied += len(chunk)
                    if copied > archive_limit:
                        raise ValueError("Worker predictor runtime archive is too large.")
                    archive_handle.write(chunk)
                archive_handle.flush()
                return mushroom_predictor_runtime.synchronize_runtime_archive(
                    runtime_cache_root,
                    manifest,
                    Path(archive_handle.name),
                )
        except HTTPError as exc:
            if exc.code not in {404, 409}:
                raise
        except (ValueError, tarfile.TarError):
            # A corrupt or incompatible archive must not make prediction
            # unavailable: the per-file path verifies the same manifest.
            pass

    def fetch(logical_path: str, target: Path) -> None:
        query = urlencode({"job_id": job.get("job_id", ""), "file": logical_path})
        request = Request(ha_url.rstrip("/") + endpoint + "?" + query, headers=headers, method="GET")
        with urlopen(request, timeout=120) as response, target.open("xb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)

    return mushroom_predictor_runtime.synchronize_runtime(
        runtime_cache_root,
        manifest,
        fetch,
    )


def download_predictor_precompute_operational_selections(
    ha_url: str,
    job: dict[str, Any],
    *,
    worker_id: str,
    claim_token: str,
    token: str,
) -> list[dict[str, Any]] | dict[str, list[dict[str, Any]]]:
    """Load large precompute selections through their claim-bound endpoint."""
    inline = job.get("operational_selections")
    if isinstance(inline, (list, dict)):
        return mushroom_worker_jobs.normalize_predictor_precompute_operational_selections(
            inline
        )
    reference = job.get("operational_selections_ref")
    if not isinstance(reference, dict):
        raise ValueError("Worker precompute selections reference is missing.")
    endpoint = str(reference.get("endpoint", ""))
    if endpoint != mushroom_worker_jobs.PREDICTOR_PRECOMPUTE_SELECTIONS_ENDPOINT:
        raise ValueError("Worker precompute selections endpoint is invalid.")
    try:
        expected_size = int(reference.get("size_bytes", -1))
    except (TypeError, ValueError) as exc:
        raise ValueError("Worker precompute selections size is invalid.") from exc
    if expected_size < 0 or expected_size > PREDICTOR_PRECOMPUTE_SELECTIONS_MAX_BYTES:
        raise ValueError("Worker precompute selections are too large.")
    expected_sha256 = str(reference.get("sha256", ""))
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected_sha256):
        raise ValueError("Worker precompute selections digest is invalid.")
    query = urlencode({"job_id": job.get("job_id", "")})
    request = Request(
        ha_url.rstrip("/") + endpoint + "?" + query,
        headers=mushroom_worker_transport.request_headers(
            worker_id, claim_token, token
        ),
        method="GET",
    )
    response_limit = expected_size + 64 * 1024
    with urlopen(request, timeout=120) as response:
        raw = response.read(response_limit + 1)
    if len(raw) > response_limit:
        raise ValueError("HA precompute selections response is too large.")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or not payload.get("ok"):
        raise ValueError("HA returned invalid precompute selections.")
    selections = (
        mushroom_worker_jobs.normalize_predictor_precompute_operational_selections(
            payload.get("operational_selections")
        )
    )
    actual = mushroom_worker_jobs.predictor_precompute_operational_selections_ref(
        selections
    )
    if (
        actual.get("sha256") != expected_sha256
        or actual.get("size_bytes") != expected_size
    ):
        raise ValueError("HA precompute selections do not match their claim reference.")
    job["operational_selections"] = selections
    return selections


def cache_ml_train_predictor_objects(worker_data_dir: Path, candidate_dir: Path) -> dict[str, int]:
    """Preserve locally trained v0/shadow models before terminal job cleanup."""
    root = Path(candidate_dir)
    manifest = json.loads((root / "ml_train_result.json").read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts") if isinstance(manifest, dict) else None
    if not isinstance(artifacts, list):
        raise ValueError("Worker ML result artifact list is invalid.")
    records: list[tuple[Path, str, int]] = []
    for row in artifacts:
        if not isinstance(row, dict) or not str(row.get("path", "")).endswith(".joblib"):
            continue
        relative = mushroom_worker_transport.safe_relative_path(row.get("path"))
        records.append((root / relative, str(row.get("sha256", "")), int(row.get("size_bytes", -1))))
    return mushroom_predictor_runtime.cache_runtime_objects(
        worker_data_dir.resolve() / "predictor-runtime",
        records,
    )


def cache_multiversion_predictor_objects(
    worker_data_dir: Path,
    result_root: Path,
) -> dict[str, int]:
    """Preserve the locally trained V2--V6 batch by content digest."""
    batch_root = Path(result_root) / "batch"
    manifest_path = batch_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    batch_id = str(manifest.get("batch_id", "")) if isinstance(manifest, dict) else ""
    artifacts = manifest.get("artifacts") if isinstance(manifest, dict) else None
    if not batch_id or not isinstance(artifacts, list):
        raise ValueError("Worker multiversion batch manifest is invalid.")
    prefix = Path("batches") / batch_id
    records: list[tuple[Path, str, int]] = [
        (
            manifest_path,
            hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            manifest_path.stat().st_size,
        )
    ]
    referenced = list(artifacts)
    quality = manifest.get("quality_catalog")
    if isinstance(quality, dict):
        referenced.append(
            {
                "path": quality.get("path"),
                "sha256": quality.get("sha256"),
                "size_bytes": None,
            }
        )
    for row in referenced:
        if not isinstance(row, dict):
            raise ValueError("Worker multiversion artifact record is invalid.")
        declared = mushroom_worker_transport.safe_relative_path(row.get("path"))
        try:
            relative = declared.relative_to(prefix)
        except ValueError as exc:
            raise ValueError("Worker multiversion artifact path is outside its batch.") from exc
        source = batch_root / relative
        size = source.stat().st_size if row.get("size_bytes") is None else int(row["size_bytes"])
        records.append((source, str(row.get("sha256", "")), size))
    return mushroom_predictor_runtime.cache_runtime_objects(
        worker_data_dir.resolve() / "predictor-runtime",
        records,
    )


def heartbeat_payload(
    status: dict[str, Any],
    *,
    discarded_job_ids: list[str] | tuple[str, ...] = (),
    cleaned_job_ids: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        **status,
        "kind": "rainmapper_worker_heartbeat",
        "discarded_job_ids": list(discarded_job_ids),
        "cleaned_job_ids": list(cleaned_job_ids),
    }


def send_heartbeat(
    ha_url: str,
    payload: dict[str, Any],
    *,
    token: str = "",
    timeout: float = 3.0,
) -> dict[str, Any]:
    endpoint = ha_url.rstrip("/") + "/api/mushrooms/workers/heartbeat"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError("Heartbeat response is too large.")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict) or not result.get("ok"):
        raise ValueError("HA rejected the worker heartbeat.")
    return result


def claim_job(
    ha_url: str,
    worker_id: str,
    *,
    token: str = "",
    timeout: float = 3.0,
    lane: str | None = None,
) -> dict[str, Any] | None:
    endpoint = ha_url.rstrip("/") + "/api/mushrooms/workers/jobs/claim"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    claim_payload = {"worker_id": worker_id}
    if lane is not None:
        claim_payload["lane"] = lane
    request = Request(
        endpoint,
        data=json.dumps(claim_payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError("Worker claim response is too large.")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict) or not result.get("ok"):
        raise ValueError("HA rejected the worker job claim.")
    job = result.get("job")
    if job is None:
        return None
    if not isinstance(job, dict):
        raise ValueError("HA returned an invalid worker job.")
    return dict(job)


def upload_predictor_precompute_artifact(
    ha_url: str,
    path: Path,
    *,
    job_id: str,
    worker_id: str,
    claim_token: str,
    token: str,
    file_sha256: str,
    timeout: float = 300.0,
) -> tuple[
    mushroom_predictor_precompute_control.PublicationReceipt,
    dict[str, Any],
]:
    endpoint = "/api/mushrooms/workers/jobs/precompute-artifact?" + urlencode({"job_id": job_id})
    parsed = urlsplit(ha_url)
    connection_class = (
        http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_class(parsed.hostname, parsed.port, timeout=timeout)
    headers = mushroom_worker_transport.request_headers(worker_id, claim_token, token)
    headers.update(
        {
            "Content-Type": "application/vnd.sqlite3",
            "Content-Length": str(path.stat().st_size),
            "X-Rainmapper-SHA256": file_sha256,
        }
    )
    try:
        connection.putrequest("POST", (parsed.path.rstrip("/") + endpoint) or endpoint)
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                connection.send(chunk)
        response = connection.getresponse()
        raw = response.read(65537)
        if response.status != 200:
            raise ValueError(f"HA rejected Predictor precompute artifact with HTTP {response.status}.")
        if len(raw) > 65536:
            raise ValueError("HA precompute publication receipt is too large.")
        payload = json.loads(raw.decode("utf-8"))
        receipt = payload.get("publication_receipt") if isinstance(payload, dict) else None
        if not isinstance(receipt, dict):
            raise ValueError("HA returned an invalid precompute publication receipt.")
        publication_telemetry = (
            payload.get("publication_telemetry") if isinstance(payload, dict) else None
        )
        return (
            mushroom_predictor_precompute_control.PublicationReceipt.from_dict(receipt),
            mushroom_worker_jobs.normalize_precompute_telemetry(publication_telemetry),
        )
    finally:
        connection.close()


def update_job(
    ha_url: str,
    action: str,
    payload: dict[str, Any],
    *,
    token: str = "",
    timeout: float = 3.0,
) -> dict[str, Any]:
    if action not in {"start", "progress", "control", "finish"}:
        raise ValueError("Worker job action is invalid.")
    endpoint = ha_url.rstrip("/") + f"/api/mushrooms/workers/jobs/{action}"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(65537)
    except HTTPError as exc:
        raw_error = exc.read(65537)
        detail = ""
        if len(raw_error) <= 65536:
            try:
                error_payload = json.loads(raw_error.decode("utf-8"))
                if isinstance(error_payload, dict):
                    detail = str(error_payload.get("error", "") or "")
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail = raw_error.decode("utf-8", errors="replace").strip()
        suffix = f": {detail[:1000]}" if detail else ""
        raise ValueError(
            f"HA rejected the worker job {action} request with HTTP {exc.code}{suffix}"
        ) from exc
    if len(raw) > 65536:
        raise ValueError("Worker job response is too large.")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict) or not result.get("ok") or not isinstance(result.get("job"), dict):
        raise ValueError(f"HA rejected the worker job {action} request.")
    return dict(result)


def _handler_class(
    worker_data_dir: Path,
    worker_version: str,
    identity: dict[str, str],
    runtime_state: dict[str, Any],
    runtime_lock: threading.Lock,
) -> type[BaseHTTPRequestHandler]:
    class WorkerStatusHandler(BaseHTTPRequestHandler):
        server_version = "RainmapperWorker/0.1"

        def do_GET(self) -> None:  # noqa: N802
            request_path = urlsplit(self.path).path
            if request_path not in {"/", "/health", "/ready"}:
                self._write_json(404, {"status": "not_found"})
                return
            with runtime_lock:
                lanes = {
                    lane: dict(runtime_state.get(lane, {}))
                    for lane in ("foreground", "background")
                }
                runtime_status = str(lanes["foreground"].get("status", "idle"))
            payload = worker_status(
                worker_data_dir,
                worker_version=worker_version,
                identity=identity,
                runtime_status=runtime_status,
            )
            payload["lanes"] = lanes
            if request_path == "/ready" and payload["dataset_cache"].get("status") != "valid":
                self._write_json(503, payload)
                return
            self._write_json(200, payload)

        def _write_json(self, status: int, payload: dict[str, Any]) -> None:
            body = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return WorkerStatusHandler


def execute_interactive_prediction(
    predictor_service: PredictorService,
    request: object,
) -> dict[str, Any]:
    """Compute without turning local progress into coordinator round trips.

    The web client owns the non-authoritative waiting animation. The worker only
    publishes durable start and finish transitions for interactive jobs.
    Diagnostic metrics remain embedded in the returned predictor response.
    """
    return predictor_service.execute(request)


def multiversion_preparation_command(
    worker_job_dir: Path,
    spec: dict[str, Any],
    input_bundle: dict[str, Any],
    *,
    preparation_root: Path,
    progress_path: Path,
    job_purpose: str,
) -> list[str]:
    """Build the dynamic V2--V6 command from its sealed input contract."""
    command = [
        sys.executable,
        "/app/scripts/prepare-mushroom-ml-multiversion-inputs.py",
        "--data-dir",
        str(worker_job_dir / str(spec["weather_data_dir"])),
        "--observations",
        str(worker_job_dir / str(spec["observations_path"])),
        "--known-sites",
        str(worker_job_dir / str(spec["known_sites_path"])),
        "--observation-features",
        str(worker_job_dir / str(spec["observation_features_path"])),
        "--stations-file",
        str(worker_job_dir / str(spec["stations_path"])),
        "--output-dir",
        str(preparation_root),
        "--source-snapshot-id",
        str(input_bundle["snapshot_id"]),
        "--progress-jsonl",
        str(progress_path),
        "--job-purpose",
        job_purpose,
    ]
    tuning_catalog_path = spec.get("tuning_catalog_path")
    if tuning_catalog_path:
        command.extend(
            [
                "--tuning-catalog",
                str(worker_job_dir / str(tuning_catalog_path)),
            ]
        )
    operational_plan_path = spec.get("operational_plan_path")
    if job_purpose == "operational":
        if not operational_plan_path:
            raise ValueError("Operational worker job has no sealed training plan")
        command.extend(
            [
                "--operational-plan",
                str(worker_job_dir / str(operational_plan_path)),
            ]
        )
    for profile_key in list(spec.get("profile_keys") or []):
        command.extend(["--profile-key", str(profile_key)])
    return command


def validate_multiversion_retry_identity(
    payload: object,
    *,
    job_id: str,
    job_purpose: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Allow reuse only for the exact sealed scientific work."""
    manifest = mushroom_ml_multiversion_transport.validate_result_manifest(
        payload,
        job_id=job_id,
        expected_purpose=job_purpose,
    )
    if job_purpose == "operational" and (
        manifest.get("operational_scope_id") != spec.get("operational_scope_id")
        or manifest.get("operational_plan_id") != spec.get("operational_plan_id")
    ):
        raise ValueError(
            "Retry result does not match the sealed operational scope and plan"
        )
    return manifest


def serve(
    worker_data_dir: Path,
    *,
    host: str = "0.0.0.0",
    port: int = 8098,
    worker_version: str | None = None,
    ha_url: str = "",
    token: str = "",
    display_name: str = "",
    host_name: str = "",
    heartbeat_interval: float = 10.0,
) -> None:
    resolved_version = worker_version or os.environ.get("RAINMAPPER_WORKER_VERSION", "local")
    persisted_config = mushroom_worker_config.load_coordinator_config(
        worker_data_dir.resolve(),
        include_token=True,
    )
    ha_url = str(ha_url or persisted_config.get("rainmapper_url", "")).strip()
    token = str(token or persisted_config.get("token", "")).strip()
    if not ha_url:
        raise ValueError(
            "Rainmapper coordinator is not configured. Run mushroom_worker_start.sh "
            "with --rainmapper-url or complete its interactive setup."
        )
    identity = ensure_worker_identity(
        worker_data_dir.resolve(),
        display_name=display_name,
        host_name=host_name,
    )
    runtime_lock = threading.Lock()
    runtime_state: dict[str, Any] = {
        "foreground": {"status": "idle", "active_job_id": ""},
        "background": {"status": "idle", "active_job_id": ""},
    }
    discarded_job_ids_pending: set[str] = set()
    cleaned_job_ids_pending: set[str] = set()
    predictor_services: dict[str, PredictorService] = {}
    predictor_services_lock = threading.RLock()
    server = ThreadingHTTPServer(
        (host, port),
        _handler_class(worker_data_dir.resolve(), resolved_version, identity, runtime_state, runtime_lock),
    )
    print(
        json.dumps(
            {
                "status": "listening",
                "service": "rainmapper-worker",
                "host": host,
                "port": port,
                "worker_version": resolved_version,
                "worker_id": identity["worker_id"],
                "display_name": identity["display_name"],
                "host_name": identity["host_name"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    stop_event = threading.Event()
    heartbeat_thread: threading.Thread | None = None
    active_job_threads: dict[str, threading.Thread | None] = {
        "foreground": None,
        "background": None,
    }
    probe_duration = max(2.0, float(os.environ.get("RAINMAPPER_WORKER_CLAIM_PROBE_SECONDS", "12")))
    job_retry_seconds = max(
        0.0,
        float(os.environ.get("RAINMAPPER_WORKER_JOB_RETRY_SECONDS", "120")),
    )

    if ha_url:
        def set_runtime(lane: str, status: str, job_id: str = "") -> None:
            with runtime_lock:
                runtime_state[lane] = {"status": status, "active_job_id": job_id}

        def run_claimed_job(job: dict[str, Any], lane: str) -> None:
            job_id = str(job.get("job_id", ""))
            claim_token = str(job.get("claim_token", ""))
            started = False
            finish_acknowledged = False
            compute_process: subprocess.Popen[bytes] | None = None
            candidate_dir: Path | None = None
            candidate_runtime_files: list[Path] = []

            def job_update(action: str, payload: dict[str, Any]) -> dict[str, Any]:
                nonlocal finish_acknowledged
                result = retry_transient(
                    lambda: update_job(
                        ha_url,
                        action,
                        payload,
                        token=token,
                        timeout=_job_update_timeout(action, str(job.get("job_type", ""))),
                    ),
                    retry_seconds=job_retry_seconds,
                    stop_event=stop_event,
                )
                if action == "finish":
                    finish_acknowledged = True
                return result

            def with_transport_retry(operation: Callable[[], _T]) -> _T:
                return retry_transient(
                    operation,
                    retry_seconds=job_retry_seconds,
                    stop_event=stop_event,
                )

            def telemetry_update(action: str, payload: dict[str, Any]) -> dict[str, Any]:
                return update_job(
                    ha_url,
                    action,
                    payload,
                    token=token,
                    timeout=_job_update_timeout(action, str(job.get("job_type", ""))),
                )

            def deliver_result(
                operation: Callable[[], _T],
                telemetry: _CoalescedJobTelemetry,
            ) -> _T:
                return retry_transient(
                    operation,
                    retry_seconds=None,
                    stop_event=stop_event,
                    on_retry=lambda: telemetry.poll_control(force=True),
                )

            try:
                job_type = str(job.get("job_type", ""))
                if job_type not in {
                    "worker_claim_probe",
                    "worker_snapshot_transport_probe",
                    "worker_candidate_rebuild",
                    "worker_ml_train_v0",
                    "worker_ml_multiversion_v1",
                    "worker_predictor_v1",
                    "worker_predictor_precompute_v1",
                }:
                    raise ValueError("Worker received an unsupported job type.")
                job_update(
                    "start",
                    {"job_id": job_id, "worker_id": identity["worker_id"], "claim_token": claim_token},
                )
                started = True
                set_runtime(lane, "busy", job_id)
                if job_type == "worker_predictor_v1":
                    runtime_reference = job.get("runtime_manifest_ref")
                    lookup_fingerprint = str(
                        runtime_reference.get("fingerprint", "")
                        if isinstance(runtime_reference, dict)
                        else job.get("runtime_manifest", {}).get("fingerprint", "")
                        if isinstance(job.get("runtime_manifest"), dict)
                        else ""
                    )
                    precomputed = mushroom_predictor_precompute.lookup_active_artifact(
                        worker_data_dir.resolve() / "predictor_precompute" / "active.sqlite3",
                        runtime_fingerprint=lookup_fingerprint,
                        request=job.get("predictor_request"),
                    )
                    if precomputed.hit and precomputed.response is not None:
                        job_update(
                            "finish",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                                "status": "complete",
                                "result": {
                                    "response": precomputed.response,
                                    "cold": False,
                                    "runtime_cache_status": "precompute_hit",
                                    "runtime_transferred_size_bytes": 0,
                                },
                            },
                        )
                        return
                    runtime_root, runtime_sync = with_transport_retry(
                        lambda: download_predictor_runtime(
                            ha_url,
                            job,
                            worker_data_dir.resolve(),
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                        )
                    )
                    manifest = mushroom_predictor_runtime.validate_manifest(
                        job.get("runtime_manifest")
                    )
                    fingerprint = str(manifest["fingerprint"])
                    with predictor_services_lock:
                        cold = fingerprint not in predictor_services
                        if cold:
                            paths = mushroom_predictor_runtime.service_paths(runtime_root)
                            predictor_services[fingerprint] = PredictorService(
                                **paths,
                                runtime_fingerprint=fingerprint,
                            )
                        predictor_service = predictor_services[fingerprint]

                    # Interactive predictions are intentionally silent while computing.
                    # PredictorService can emit very fine-grained progress (for example,
                    # one event per area/day). Relaying every event synchronously through
                    # the coordinator made a fast local calculation spend most of its time
                    # waiting for HTTP control/progress round trips. The coordinator already
                    # knows that the job started and the final response is the only state
                    # transition the UI needs; its waiting indicator is client-side.
                    response = execute_interactive_prediction(
                        predictor_service, job.get("predictor_request")
                    )
                    mushroom_worker_jobs.validate_predictor_result_size(response)
                    control = job_update(
                        "control",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                        },
                    )
                    if control.get("cancel_requested"):
                        job_update(
                            "finish",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                                "status": "cancelled",
                            },
                        )
                        print(
                            json.dumps(
                                {
                                    "status": "job_cancelled",
                                    "service": "rainmapper-worker",
                                    "job_id": job_id,
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                        return
                    job_update(
                        "finish",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "status": "complete",
                            "result": {
                                "response": response,
                                "cold": cold,
                                "runtime_cache_status": runtime_sync["status"],
                                "runtime_transferred_size_bytes": runtime_sync[
                                    "transferred_size_bytes"
                                ],
                                "runtime_verification_status": runtime_sync.get(
                                    "verification_status", ""
                                ),
                                "runtime_hashed_file_count": runtime_sync.get(
                                    "hashed_file_count", 0
                                ),
                                "runtime_reused_file_count": runtime_sync.get(
                                    "reused_file_count", 0
                                ),
                                "runtime_fetched_file_count": runtime_sync.get(
                                    "fetched_file_count", 0
                                ),
                                "runtime_sync_seconds": runtime_sync.get(
                                    "elapsed_seconds", 0.0
                                ),
                                "precompute_fallback_reason": precomputed.reason or "",
                            },
                        },
                    )
                    print(
                        json.dumps(
                            {
                                "status": "prediction_complete",
                                "service": "rainmapper-worker",
                                "job_id": job_id,
                                "cold": cold,
                                "runtime_cache_status": runtime_sync["status"],
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    return
                if job_type == "worker_predictor_precompute_v1":
                    operational_selections = with_transport_retry(
                        lambda: download_predictor_precompute_operational_selections(
                            ha_url,
                            job,
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                        )
                    )
                    runtime_sync_started = time.perf_counter()
                    runtime_root, _runtime_sync = with_transport_retry(
                        lambda: download_predictor_runtime(
                            ha_url,
                            job,
                            worker_data_dir.resolve(),
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                        )
                    )
                    artifact_identity = mushroom_predictor_precompute.ArtifactIdentity.from_dict(
                        job.get("artifact_identity")
                    )
                    manifest = mushroom_predictor_runtime.validate_manifest(job.get("runtime_manifest"))
                    fingerprint = str(manifest["fingerprint"])
                    if fingerprint != artifact_identity.runtime_fingerprint:
                        raise ValueError("Precompute runtime does not match artifact identity.")
                    with predictor_services_lock:
                        if fingerprint not in predictor_services:
                            predictor_services[fingerprint] = PredictorService(
                                **mushroom_predictor_runtime.service_paths(runtime_root),
                                runtime_fingerprint=fingerprint,
                            )
                        predictor_service = predictor_services[fingerprint]
                    staging_dir = worker_data_dir.resolve() / "predictor_precompute" / "staging"
                    staging_dir.mkdir(parents=True, exist_ok=True)
                    staged_artifact = staging_dir / f"{job_id}.sqlite3"
                    precompute_telemetry: dict[str, Any] = {
                        "runtime_sync_seconds": round(
                            time.perf_counter() - runtime_sync_started, 6
                        )
                    }

                    def precompute_control() -> None:
                        control = job_update(
                            "control",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                            },
                        )
                        if control.get("cancel_requested"):
                            raise InterruptedError("Predictor precompute was cancelled or superseded.")

                    def precompute_progress(done: int, total: int, label: str) -> None:
                        precompute_control()
                        job_update(
                            "progress",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                                "phase": "Calculating weekly Predictor artifact",
                                "message": f"{done}/{total}: {label}",
                                "overall_percent": 10 + int(65 * done / max(1, total)),
                            },
                        )

                    job_update(
                        "progress",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "phase": "Calculating weekly Predictor artifact",
                            "message": "Starting the weekly Predictor calculation.",
                            "overall_percent": 10,
                            "precompute_milestone": "calculation_started",
                        },
                    )
                    calculation_started = time.perf_counter()
                    build = mushroom_predictor_precompute.build_weekly_artifact(
                        staged_artifact,
                        identity=artifact_identity,
                        predictor_service=predictor_service,
                        operational_selections=operational_selections,
                        progress=precompute_progress,
                        cancel_check=precompute_control,
                    )
                    precompute_telemetry["calculation_seconds"] = round(
                        time.perf_counter() - calculation_started, 6
                    )
                    job_update(
                        "progress",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "phase": "Uploading verified SQLite",
                            "message": "Transferring the artifact once to HA.",
                            "overall_percent": 85,
                            "precompute_milestone": "calculation_finished",
                        },
                    )
                    upload_started = time.perf_counter()
                    receipt, publication_telemetry = upload_predictor_precompute_artifact(
                        ha_url,
                        staged_artifact,
                        job_id=job_id,
                        worker_id=identity["worker_id"],
                        claim_token=claim_token,
                        token=token,
                        file_sha256=build.manifest.file_sha256,
                    )
                    upload_round_trip_seconds = round(
                        time.perf_counter() - upload_started, 6
                    )
                    ha_publish_seconds = float(
                        publication_telemetry.get("ha_publish_seconds", 0.0) or 0.0
                    )
                    precompute_telemetry.update(publication_telemetry)
                    precompute_telemetry.update(
                        {
                            "upload_round_trip_seconds": upload_round_trip_seconds,
                            "estimated_transfer_seconds": round(
                                max(0.0, upload_round_trip_seconds - ha_publish_seconds),
                                6,
                            ),
                            "artifact_size_bytes": build.manifest.size_bytes,
                        }
                    )
                    if receipt.desired_revision != int(job.get("desired_revision", 0) or 0):
                        raise ValueError("HA publication receipt has another desired revision.")
                    job_update(
                        "progress",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "phase": "Activating verified worker copy",
                            "message": "HA is active; activating the worker's local copy.",
                            "overall_percent": 98,
                        },
                    )
                    worker_activation_started = time.perf_counter()
                    mushroom_predictor_precompute_control.activate_worker_copy(
                        staged_artifact,
                        destination_path=(
                            worker_data_dir.resolve() / "predictor_precompute" / "active.sqlite3"
                        ),
                        receipt=receipt,
                        identity=artifact_identity,
                    )
                    precompute_telemetry.update(
                        {
                            "worker_activation_seconds": round(
                                time.perf_counter() - worker_activation_started, 6
                            ),
                            "worker_activation_finished_at": mushroom_worker_jobs.utc_now(),
                        }
                    )
                    staged_artifact.unlink(missing_ok=True)
                    job_update(
                        "finish",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "status": "complete",
                            "result": {
                                "publication_receipt": receipt.as_dict(),
                                "worker_activation": "active",
                                "precompute_telemetry": precompute_telemetry,
                            },
                        },
                    )
                    return
                if job_type == "worker_snapshot_transport_probe":
                    def report_progress(event: dict[str, Any]) -> None:
                        control = job_update(
                            "control",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                            },
                        )
                        if control.get("cancel_requested"):
                            raise InterruptedError("Worker input transport was cancelled.")
                        job_update(
                            "progress",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                                "phase": event.get("phase", "Downloading immutable inputs"),
                                "message": event.get("message", ""),
                                "overall_percent": event.get("overall_percent", 10),
                            },
                        )

                    result = with_transport_retry(
                        lambda: mushroom_worker_transport.download_input_bundle(
                            ha_url,
                            job,
                            worker_data_dir.resolve(),
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                            progress_callback=report_progress,
                        )
                    )
                    job_update(
                        "finish",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "status": "complete",
                            "result": {
                                "verification_status": result.get("status"),
                                "snapshot_id": result.get("snapshot_id"),
                                "job_spec_id": result.get("job_spec_id"),
                                "input_file_count": result.get("input_file_count"),
                                "input_size_bytes": result.get("input_size_bytes"),
                                "dataset_fingerprint": result.get("dataset_fingerprint"),
                                "dataset_cache_status": result.get("dataset_cache_status"),
                                "dataset_transferred_size_bytes": result.get(
                                    "dataset_transferred_size_bytes"
                                ),
                            },
                        },
                    )
                    print(
                        json.dumps(
                            {
                                "status": "input_bundle_verified",
                                "service": "rainmapper-worker",
                                "job_id": job_id,
                                "snapshot_id": result.get("snapshot_id", ""),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    return
                if job_type == "worker_candidate_rebuild":
                    telemetry = _CoalescedJobTelemetry(
                        telemetry_update,
                        base_payload={
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                        },
                        cancel_message="Worker candidate rebuild was cancelled.",
                    )

                    def publish_progress(event: dict[str, Any], *, pipeline: bool = False) -> None:
                        raw_percent = int(event.get("overall_percent", 10) or 10)
                        percent = 20 + int(raw_percent * 0.68) if pipeline else max(10, min(99, raw_percent))
                        telemetry.publish(
                            {
                                "phase": event.get("phase", "Candidate rebuild"),
                                "message": event.get("message", ""),
                                "overall_percent": percent,
                            }
                        )

                    def input_progress(event: dict[str, Any]) -> None:
                        mapped = dict(event)
                        mapped["overall_percent"] = 10 + int(
                            max(0, int(event.get("overall_percent", 10) or 10) - 10) * 0.1
                        )
                        publish_progress(mapped)

                    input_result = with_transport_retry(
                        lambda: mushroom_worker_transport.download_input_bundle(
                            ha_url,
                            job,
                            worker_data_dir.resolve(),
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                            progress_callback=input_progress,
                        )
                    )
                    worker_job_dir = Path(str(input_result["input_dir"])).resolve()
                    candidate_dir = worker_job_dir / "candidate"
                    progress_path = worker_job_dir / "pipeline-progress.jsonl"
                    stdout_path = worker_job_dir / "pipeline.stdout.log"
                    stderr_path = worker_job_dir / "pipeline.stderr.log"
                    candidate_runtime_files = [progress_path, stdout_path, stderr_path]
                    command = [
                        sys.executable,
                        "/app/scripts/run-mushroom-rebuild-job.py",
                        "run",
                        "--snapshot-dir",
                        str(worker_job_dir / "snapshot"),
                        "--job-spec",
                        str(worker_job_dir / "job_spec.json"),
                        "--output-dir",
                        str(candidate_dir),
                        "--worker-data-dir",
                        str(worker_data_dir.resolve()),
                        "--progress-jsonl",
                        str(progress_path),
                        "--quiet",
                    ]
                    with stdout_path.open("xb") as stdout_handle, stderr_path.open("xb") as stderr_handle:
                        compute_process = subprocess.Popen(
                            command,
                            stdin=subprocess.DEVNULL,
                            stdout=stdout_handle,
                            stderr=stderr_handle,
                        )
                    published_lines = 0
                    while not stop_event.is_set():
                        try:
                            telemetry.poll_control()
                        except InterruptedError as exc:
                            if compute_process.poll() is None:
                                if bool(getattr(exc, "force_cancel_requested", False)):
                                    compute_process.kill()
                                else:
                                    compute_process.terminate()
                                    try:
                                        compute_process.wait(timeout=2.0)
                                    except subprocess.TimeoutExpired:
                                        compute_process.kill()
                                compute_process.wait(timeout=2.0)
                            raise
                        if progress_path.is_file():
                            lines = progress_path.read_text(encoding="utf-8").splitlines()
                            pending_events = [
                                event
                                for line in lines[published_lines:]
                                if isinstance((event := json.loads(line)), dict)
                            ]
                            if pending_events:
                                publish_progress(pending_events[-1], pipeline=True)
                            published_lines = len(lines)
                        return_code = compute_process.poll()
                        if return_code is not None:
                            if return_code != 0:
                                detail = stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]
                                raise RuntimeError(
                                    f"Candidate rebuild process exited with status {return_code}: {detail}"
                                )
                            break
                        stop_event.wait(0.5)

                    def upload_progress(event: dict[str, Any]) -> None:
                        publish_progress(event)

                    verification = deliver_result(
                        lambda: mushroom_worker_results.upload_candidate_result(
                            ha_url,
                            job,
                            worker_job_dir,
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                            progress_callback=upload_progress,
                        ),
                        telemetry,
                    )
                    telemetry.flush()
                    job_update(
                        "finish",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "status": "complete",
                            "result": {
                                "verification_status": "verified",
                                "snapshot_id": input_result.get("snapshot_id"),
                                "job_spec_id": input_result.get("job_spec_id"),
                                "input_file_count": input_result.get("input_file_count"),
                                "input_size_bytes": input_result.get("input_size_bytes"),
                                "dataset_fingerprint": input_result.get("dataset_fingerprint"),
                                "result_manifest_id": verification.get("result_manifest_id"),
                                "verified_artifacts": verification.get("verified_artifacts"),
                                "comparison_status": verification.get("comparison_status"),
                            },
                        },
                    )
                    print(
                        json.dumps(
                            {
                                "status": "candidate_result_verified",
                                "service": "rainmapper-worker",
                                "job_id": job_id,
                                "comparison_status": verification.get("comparison_status", ""),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    return
                if job_type == "worker_ml_train_v0":
                    ml_telemetry = _CoalescedJobTelemetry(
                        telemetry_update,
                        base_payload={
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                        },
                        cancel_message="Worker ML training job was cancelled.",
                    )

                    def ml_publish_progress(event: dict[str, Any], *, pipeline: bool = False) -> None:
                        raw_percent = int(event.get("overall_percent", 10) or 10)
                        percent = 20 + int(raw_percent * 0.7) if pipeline else max(10, min(99, raw_percent))
                        ml_telemetry.publish(
                            {
                                "phase": event.get("phase", "ML training"),
                                "message": event.get("message", ""),
                                "overall_percent": percent,
                            }
                        )

                    def ml_input_progress(event: dict[str, Any]) -> None:
                        mapped = dict(event)
                        mapped["overall_percent"] = 5 + int(
                            max(0, int(event.get("overall_percent", 5) or 5) - 5) * 0.1
                        )
                        ml_publish_progress(mapped)

                    input_result = with_transport_retry(
                        lambda: mushroom_worker_transport.download_ml_train_inputs(
                            ha_url,
                            job,
                            worker_data_dir.resolve(),
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                            progress_callback=ml_input_progress,
                        )
                    )
                    worker_job_dir = Path(str(input_result["input_dir"])).resolve()
                    ml_candidate_dir = worker_job_dir / "ml_candidate"
                    ml_candidate_dir.mkdir(parents=True, exist_ok=True)
                    progress_path = worker_job_dir / "ml-progress.jsonl"
                    stdout_path = worker_job_dir / "ml.stdout.log"
                    stderr_path = worker_job_dir / "ml.stderr.log"
                    candidate_runtime_files = [progress_path, stdout_path, stderr_path]
                    command = [
                        sys.executable,
                        "/app/scripts/run-mushroom-ml-train-job.py",
                        "--job-spec", str(worker_job_dir / "job_spec.json"),
                        "--features", str(worker_job_dir / "features.json"),
                        "--known-sites", str(worker_job_dir / "known_sites.json"),
                        "--output-dir", str(ml_candidate_dir),
                        "--progress-jsonl", str(progress_path),
                        "--quiet",
                    ]
                    with stdout_path.open("xb") as stdout_handle, stderr_path.open("xb") as stderr_handle:
                        compute_process = subprocess.Popen(
                            command,
                            stdin=subprocess.DEVNULL,
                            stdout=stdout_handle,
                            stderr=stderr_handle,
                        )
                    published_lines = 0
                    while not stop_event.is_set():
                        try:
                            ml_telemetry.poll_control()
                        except InterruptedError as exc:
                            if compute_process.poll() is None:
                                if bool(getattr(exc, "force_cancel_requested", False)):
                                    compute_process.kill()
                                else:
                                    compute_process.terminate()
                                    try:
                                        compute_process.wait(timeout=2.0)
                                    except subprocess.TimeoutExpired:
                                        compute_process.kill()
                                compute_process.wait(timeout=2.0)
                            raise
                        if progress_path.is_file():
                            lines = progress_path.read_text(encoding="utf-8").splitlines()
                            pending_events = [
                                event
                                for line in lines[published_lines:]
                                if isinstance((event := json.loads(line)), dict)
                            ]
                            if pending_events:
                                ml_publish_progress(pending_events[-1], pipeline=True)
                            published_lines = len(lines)
                        return_code = compute_process.poll()
                        if return_code is not None:
                            if return_code != 0:
                                detail = stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]
                                raise RuntimeError(
                                    f"ML training process exited with status {return_code}: {detail}"
                                )
                            break
                        stop_event.wait(0.5)

                    def ml_upload_progress(event: dict[str, Any]) -> None:
                        ml_publish_progress(event)

                    verification = deliver_result(
                        lambda: mushroom_worker_results.upload_ml_train_result(
                            ha_url,
                            job,
                            worker_job_dir,
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                            progress_callback=ml_upload_progress,
                        ),
                        ml_telemetry,
                    )
                    try:
                        model_cache = cache_ml_train_predictor_objects(
                            worker_data_dir,
                            ml_candidate_dir,
                        )
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        model_cache = {"error": str(exc)}
                    print(
                        json.dumps(
                            {"status": "predictor_model_cache_seeded", **model_cache},
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    ml_telemetry.flush()
                    job_update(
                        "finish",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "status": "complete",
                            "result": {
                                "verification_status": "verified",
                                "result_manifest_id": verification.get("result_manifest_id"),
                                "trained_species_count": verification.get("trained_species_count"),
                                "trained_species": verification.get("trained_species", []),
                                "operational_scope_id": verification.get(
                                    "operational_scope_id", ""
                                ),
                            },
                        },
                    )
                    print(
                        json.dumps(
                            {
                                "status": "ml_train_result_verified",
                                "service": "rainmapper-worker",
                                "job_id": job_id,
                                "trained_species_count": verification.get("trained_species_count", 0),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    return
                if job_type == "worker_ml_multiversion_v1":
                    multiversion_telemetry = _CoalescedJobTelemetry(
                        telemetry_update,
                        base_payload={
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                        },
                        cancel_message="Worker V2--V6 training job was cancelled.",
                    )

                    def multiversion_progress(event: dict[str, Any]) -> None:
                        multiversion_telemetry.publish(event)

                    input_bundle = job.get("input_bundle")
                    input_bundle = input_bundle if isinstance(input_bundle, dict) else {}
                    dynamic_inputs = bool(input_bundle.get("snapshot_id"))
                    input_result = with_transport_retry(
                        lambda: (
                            mushroom_worker_transport.download_input_bundle(
                                ha_url,
                                job,
                                worker_data_dir.resolve(),
                                worker_id=identity["worker_id"],
                                claim_token=claim_token,
                                token=token,
                                progress_callback=multiversion_progress,
                            )
                            if dynamic_inputs
                            else mushroom_worker_transport.download_ml_multiversion_inputs(
                                ha_url,
                                job,
                                worker_data_dir.resolve(),
                                worker_id=identity["worker_id"],
                                claim_token=claim_token,
                                token=token,
                                progress_callback=multiversion_progress,
                            )
                        )
                    )
                    worker_job_dir = Path(str(input_result["input_dir"])).resolve()
                    spec = (
                        input_bundle.get("multiversion_spec")
                        if dynamic_inputs
                        else json.loads((worker_job_dir / "job_spec.json").read_text(encoding="utf-8"))
                    )
                    if not isinstance(spec, dict) or spec.get("kind") != "mushroom_ml_multiversion_job":
                        raise ValueError("Worker multiversion job specification is invalid.")
                    job_purpose = str(spec.get("job_purpose") or "benchmark")
                    if job_purpose not in {"operational", "benchmark"}:
                        raise ValueError("Worker multiversion job purpose is invalid.")
                    result_root = worker_job_dir / "multiversion_result"
                    existing_result = result_root / "multiversion_result.json"
                    if existing_result.is_file():
                        retry_manifest = validate_multiversion_retry_identity(
                            json.loads(existing_result.read_text(encoding="utf-8")),
                            job_id=job_id,
                            job_purpose=job_purpose,
                            spec=spec,
                        )
                        multiversion_progress(
                            {
                                "phase": "Retrying V2--V6 result delivery",
                                "message": "Reusing the completed local batch without retraining.",
                                "overall_percent": 90,
                            }
                        )
                        verification = deliver_result(
                            lambda: mushroom_worker_results.upload_ml_multiversion_result(
                                ha_url,
                                job,
                                worker_job_dir,
                                worker_id=identity["worker_id"],
                                claim_token=claim_token,
                                token=token,
                                progress_callback=multiversion_progress,
                            ),
                            multiversion_telemetry,
                        )
                        try:
                            model_cache = cache_multiversion_predictor_objects(
                                worker_data_dir,
                                result_root,
                            )
                        except (OSError, ValueError, json.JSONDecodeError) as exc:
                            model_cache = {"error": str(exc)}
                        print(
                            json.dumps(
                                {"status": "predictor_model_cache_seeded", **model_cache},
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                        multiversion_telemetry.flush()
                        job_update(
                            "finish",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                                "status": "complete",
                                "result": {"verification_status": "verified", **verification},
                            },
                        )
                        print(
                            json.dumps(
                                {
                                    "status": "ml_multiversion_result_retried",
                                    "service": "rainmapper-worker",
                                    "job_id": job_id,
                                    "batch_id": verification.get("batch_id", ""),
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                        return
                    result_root.mkdir(parents=True, exist_ok=False)
                    prepared_inputs: dict[str, str] | None = None
                    if dynamic_inputs:
                        preparation_root = worker_job_dir / "multiversion_inputs"
                        preparation_progress_path = worker_job_dir / "multiversion-preparation-progress.jsonl"
                        preparation_command = multiversion_preparation_command(
                            worker_job_dir,
                            spec,
                            input_bundle,
                            preparation_root=preparation_root,
                            progress_path=preparation_progress_path,
                            job_purpose=job_purpose,
                        )
                        multiversion_telemetry.publish(
                            {
                                "phase": (
                                    "Preparing selected operational inputs"
                                    if job_purpose == "operational"
                                    else "Preparing fresh V2--V6 evaluation inputs"
                                ),
                                "message": (
                                    "Building shared V2--V6 inputs and hold-out evidence."
                                    if job_purpose == "operational"
                                    else "Building disposable benchmarks from the current snapshot."
                                ),
                                "overall_percent": 20,
                            },
                            force=True,
                        )
                        compute_process = subprocess.Popen(
                            preparation_command,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                        )
                        published_preparation_lines = 0
                        while compute_process.poll() is None:
                            multiversion_telemetry.poll_control()
                            if preparation_progress_path.is_file():
                                lines = preparation_progress_path.read_text(encoding="utf-8").splitlines()
                                if len(lines) > published_preparation_lines:
                                    event = json.loads(lines[-1])
                                    completed = int(event.get("completed_step_count", 0) or 0)
                                    planned = max(1, int(event.get("planned_step_count", 1) or 1))
                                    multiversion_telemetry.publish(
                                        {
                                            "phase": str(event.get("phase", "Preparing V2--V6 inputs")),
                                            "message": str(
                                                event.get("detail")
                                                or f"Preparation step {completed}/{planned}."
                                            ),
                                            "overall_percent": 20 + int(completed / planned * 35),
                                        }
                                    )
                                    published_preparation_lines = len(lines)
                            stop_event.wait(0.5)
                        if compute_process.returncode != 0:
                            detail = (
                                compute_process.stderr.read() if compute_process.stderr else b""
                            ).decode("utf-8", errors="replace")[-2000:]
                            raise RuntimeError(
                                "V2--V6 input preparation exited with status "
                                f"{compute_process.returncode}: {detail}"
                            )
                        prepared = json.loads(
                            (preparation_root / "prepared-inputs.json").read_text(encoding="utf-8")
                        )
                        if (
                            not isinstance(prepared, dict)
                            or prepared.get("kind") != "mushroom_ml_prepared_multiversion_inputs"
                            or not isinstance(prepared.get("inputs"), dict)
                        ):
                            raise ValueError("Prepared multiversion inputs are invalid.")
                        prepared_inputs = {
                            str(key): str(value) for key, value in prepared["inputs"].items()
                        }
                    multiversion_progress_path = worker_job_dir / "multiversion-progress.jsonl"
                    model_inputs = prepared_inputs or {
                        key: str(worker_job_dir / str(value))
                        for key, value in dict(spec["inputs"]).items()
                    }
                    command = [
                        sys.executable,
                        "/app/scripts/run-mushroom-ml-multiversion-job.py",
                        "--registry", str(worker_job_dir / str(spec["registry_path"])),
                        "--snapshot-id", str(input_bundle.get("snapshot_id") or spec["snapshot_id"]),
                        "--batch-id", str(spec["batch_id"]),
                        "--v3-fixed", model_inputs["v3_fixed"],
                        "--v3-lag", model_inputs["v3_lag"],
                        "--models-root", str(worker_job_dir / "multiversion_models"),
                        "--summary", str(worker_job_dir / "multiversion-summary.json"),
                        "--job-id", job_id,
                        "--result-manifest", str(result_root / "multiversion_result.json"),
                        "--progress-jsonl", str(multiversion_progress_path),
                        "--training-input-manifest",
                        str(worker_job_dir / "snapshot" / "input_manifest.json"),
                        "--job-purpose", job_purpose,
                    ]
                    if job_purpose == "operational":
                        command.extend(
                            [
                                "--tuning-catalog",
                                str(worker_job_dir / str(spec["tuning_catalog_path"])),
                                "--operational-plan",
                                str(worker_job_dir / str(spec["operational_plan_path"])),
                            ]
                        )
                    for option, key in (
                        ("--v4-fixed", "v4_fixed"),
                        ("--v4-lag", "v4_lag"),
                        ("--v5-fixed", "v5_fixed"),
                        ("--v5-lag", "v5_lag"),
                        ("--v2-v5-heldout", "v2_v5_heldout"),
                        ("--v6-heldout", "v6_heldout"),
                    ):
                        if key in model_inputs:
                            command.extend([option, model_inputs[key]])
                    for version_id, generation_id in dict(spec["generation_ids"]).items():
                        command.extend(["--generation", f"{version_id}={generation_id}"])
                    for species_id in list(spec["species_ids"]):
                        command.extend(["--species", str(species_id)])
                    for version_id in list(spec.get("version_ids") or spec["generation_ids"]):
                        command.extend(["--version", str(version_id)])
                    for profile_key in list(spec.get("profile_keys") or []):
                        command.extend(["--profile-key", str(profile_key)])
                    multiversion_telemetry.publish(
                        {
                            "phase": (
                                "Refreshing selected operational versions"
                                if job_purpose == "operational"
                                else "Training V2--V6 scientific benchmark"
                            ),
                            "message": (
                                "Training every profile of the selected installed versions."
                                if job_purpose == "operational"
                                else "Training the isolated non-operational benchmark batch."
                            ),
                            "overall_percent": 55 if dynamic_inputs else 20,
                        },
                        force=True,
                    )
                    compute_process = subprocess.Popen(
                        command,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )
                    published_multiversion_lines = 0
                    while compute_process.poll() is None:
                        multiversion_telemetry.poll_control()
                        if multiversion_progress_path.is_file():
                            lines = multiversion_progress_path.read_text(encoding="utf-8").splitlines()
                            if len(lines) > published_multiversion_lines:
                                event = json.loads(lines[-1])
                                completed = int(event.get("completed_fit_count", 0) or 0)
                                planned = max(1, int(event.get("planned_fit_count", 1) or 1))
                                multiversion_telemetry.publish(
                                    {
                                        "phase": (
                                            "Training active operational generation"
                                            if job_purpose == "operational"
                                            else "Training V2--V6 scientific benchmark"
                                        ),
                                        "message": (
                                            f"{completed}/{planned} fits; "
                                            f"{event.get('version_id', '')} / {event.get('species_id', '')}."
                                        ),
                                        "overall_percent": (
                                            55 + int(completed / planned * 33)
                                            if dynamic_inputs
                                            else 20 + int(completed / planned * 68)
                                        ),
                                    }
                                )
                                published_multiversion_lines = len(lines)
                        stop_event.wait(0.5)
                    if compute_process.returncode != 0:
                        detail = (compute_process.stderr.read() if compute_process.stderr else b"").decode(
                            "utf-8", errors="replace"
                        )[-2000:]
                        raise RuntimeError(
                            f"V2--V6 training process exited with status {compute_process.returncode}: {detail}"
                        )
                    if dynamic_inputs:
                        shutil.rmtree(worker_job_dir / "multiversion_inputs", ignore_errors=True)
                    verification = deliver_result(
                        lambda: mushroom_worker_results.upload_ml_multiversion_result(
                            ha_url,
                            job,
                            worker_job_dir,
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                            progress_callback=multiversion_progress,
                        ),
                        multiversion_telemetry,
                    )
                    try:
                        model_cache = cache_multiversion_predictor_objects(
                            worker_data_dir,
                            result_root,
                        )
                    except (OSError, ValueError, json.JSONDecodeError) as exc:
                        model_cache = {"error": str(exc)}
                    print(
                        json.dumps(
                            {"status": "predictor_model_cache_seeded", **model_cache},
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    multiversion_telemetry.flush()
                    job_update(
                        "finish",
                        {
                            "job_id": job_id,
                            "worker_id": identity["worker_id"],
                            "claim_token": claim_token,
                            "status": "complete",
                            "result": {"verification_status": "verified", **verification},
                        },
                    )
                    print(
                        json.dumps(
                            {
                                "status": "ml_multiversion_result_verified",
                                "service": "rainmapper-worker",
                                "job_id": job_id,
                                "batch_id": verification.get("batch_id", ""),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    return
                compute_process = subprocess.Popen(
                    [sys.executable, "-c", "import sys,time; time.sleep(float(sys.argv[1]))", str(probe_duration)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(
                    json.dumps(
                        {"status": "job_started", "service": "rainmapper-worker", "job_id": job_id},
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                while not stop_event.is_set():
                    control = job_update(
                        "control",
                        {"job_id": job_id, "worker_id": identity["worker_id"], "claim_token": claim_token},
                    )
                    if control.get("cancel_requested"):
                        if compute_process.poll() is None:
                            if control.get("force_cancel_requested"):
                                compute_process.kill()
                            else:
                                compute_process.terminate()
                                try:
                                    compute_process.wait(timeout=2.0)
                                except subprocess.TimeoutExpired:
                                    compute_process.kill()
                            compute_process.wait(timeout=2.0)
                        job_update(
                            "finish",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                                "status": "cancelled",
                            },
                        )
                        print(
                            json.dumps(
                                {"status": "job_cancelled", "service": "rainmapper-worker", "job_id": job_id},
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                        return
                    return_code = compute_process.poll()
                    if return_code == 0:
                        job_update(
                            "finish",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                                "status": "complete",
                            },
                        )
                        print(
                            json.dumps(
                                {"status": "job_complete", "service": "rainmapper-worker", "job_id": job_id},
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                        return
                    if return_code is not None:
                        raise RuntimeError(f"Worker probe compute process exited with status {return_code}.")
                    stop_event.wait(0.5)
            except Exception as exc:
                if candidate_dir is not None:
                    shutil.rmtree(candidate_dir, ignore_errors=True)
                for runtime_file in candidate_runtime_files:
                    runtime_file.unlink(missing_ok=True)
                if started and not stop_event.is_set():
                    try:
                        job_update(
                            "finish",
                            {
                                "job_id": job_id,
                                "worker_id": identity["worker_id"],
                                "claim_token": claim_token,
                                "status": "cancelled" if isinstance(exc, InterruptedError) else "failed",
                                "error": str(exc),
                            },
                        )
                    except Exception:
                        pass
                print(
                    json.dumps(
                        {
                            "status": "job_cancelled" if isinstance(exc, InterruptedError) else "job_failed",
                            "service": "rainmapper-worker",
                            "job_id": job_id,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            finally:
                if compute_process is not None and compute_process.poll() is None:
                    compute_process.terminate()
                    try:
                        compute_process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        compute_process.kill()
                        compute_process.wait(timeout=1.0)
                if finish_acknowledged:
                    try:
                        mushroom_worker_transport.discard_worker_job(
                            worker_data_dir.resolve(),
                            job_id,
                        )
                        with runtime_lock:
                            cleaned_job_ids_pending.add(job_id)
                    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
                        print(
                            json.dumps(
                                {
                                    "status": "worker_job_cleanup_failed",
                                    "service": "rainmapper-worker",
                                    "job_id": job_id,
                                    "error": str(exc),
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                set_runtime(lane, "idle")

        def heartbeat_loop() -> None:
            last_error = ""
            while not stop_event.is_set():
                try:
                    with runtime_lock:
                        lanes = {
                            lane: dict(runtime_state.get(lane, {}))
                            for lane in ("foreground", "background")
                        }
                        runtime_status = str(lanes["foreground"].get("status", "idle"))
                    status = worker_status(
                        worker_data_dir.resolve(),
                        worker_version=resolved_version,
                        identity=identity,
                        runtime_status=runtime_status,
                    )
                    status["lanes"] = lanes
                    active_job_ids = {
                        str(value.get("active_job_id", "") or "")
                        for value in lanes.values()
                        if value.get("active_job_id")
                    }
                    with runtime_lock:
                        sent_discarded_ids = sorted(discarded_job_ids_pending)
                        sent_cleaned_ids = sorted(cleaned_job_ids_pending)
                    heartbeat_response = send_heartbeat(
                        ha_url,
                        heartbeat_payload(
                            status,
                            discarded_job_ids=sent_discarded_ids,
                            cleaned_job_ids=sent_cleaned_ids,
                        ),
                        token=token,
                    )
                    with runtime_lock:
                        discarded_job_ids_pending.difference_update(sent_discarded_ids)
                        cleaned_job_ids_pending.difference_update(sent_cleaned_ids)
                    discard_job_ids = heartbeat_response.get("discard_job_ids", [])
                    if not isinstance(discard_job_ids, list) or len(discard_job_ids) > 50:
                        raise ValueError("HA worker cleanup request is invalid.")
                    for discard_job_id in discard_job_ids:
                        resolved_discard_job_id = mushroom_worker_transport.validate_job_id(
                            discard_job_id
                        )
                        if resolved_discard_job_id in active_job_ids:
                            continue
                        mushroom_worker_transport.discard_worker_job(
                            worker_data_dir.resolve(),
                            resolved_discard_job_id,
                        )
                        with runtime_lock:
                            discarded_job_ids_pending.add(resolved_discard_job_id)
                            cleaned_job_ids_pending.add(resolved_discard_job_id)
                    cleanup_job_ids = heartbeat_response.get("cleanup_job_ids", [])
                    if not isinstance(cleanup_job_ids, list) or len(cleanup_job_ids) > 50:
                        raise ValueError("HA worker terminal cleanup request is invalid.")
                    for cleanup_job_id in cleanup_job_ids:
                        resolved_cleanup_job_id = mushroom_worker_transport.validate_job_id(
                            cleanup_job_id
                        )
                        if resolved_cleanup_job_id in active_job_ids:
                            continue
                        mushroom_worker_transport.discard_worker_job(
                            worker_data_dir.resolve(),
                            resolved_cleanup_job_id,
                        )
                        with runtime_lock:
                            cleaned_job_ids_pending.add(resolved_cleanup_job_id)
                    for lane in ("foreground", "background"):
                        active_thread = active_job_threads[lane]
                        if active_thread is not None and active_thread.is_alive():
                            continue
                        claimed_job = claim_job(
                            ha_url, identity["worker_id"], token=token, lane=lane
                        )
                        if claimed_job is None or stop_event.is_set():
                            continue
                        set_runtime(lane, "busy", str(claimed_job.get("job_id", "")))
                        print(
                            json.dumps(
                                {
                                    "status": "job_claimed",
                                    "service": "rainmapper-worker",
                                    "job_id": claimed_job.get("job_id", ""),
                                    "job_type": claimed_job.get("job_type", ""),
                                    "lane": lane,
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                        active_job_threads[lane] = threading.Thread(
                            target=run_claimed_job,
                            args=(claimed_job, lane),
                            daemon=True,
                            name=f"rainmapper-worker-{lane}-job",
                        )
                        active_job_threads[lane].start()
                    if last_error:
                        print(json.dumps({"status": "heartbeat_restored", "service": "rainmapper-worker"}), flush=True)
                    last_error = ""
                except Exception as exc:
                    error = str(exc)
                    if error != last_error:
                        print(
                            json.dumps(
                                {"status": "heartbeat_failed", "service": "rainmapper-worker", "error": error},
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                    last_error = error
                stop_event.wait(max(1.0, heartbeat_interval))

        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True, name="rainmapper-worker-heartbeat")
        heartbeat_thread.start()

    def request_shutdown(signum: int, frame: object) -> None:
        del frame
        stop_event.set()
        print(
            json.dumps(
                {
                    "status": "stopping",
                    "service": "rainmapper-worker",
                    "signal": signum,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    try:
        server.serve_forever()
    finally:
        stop_event.set()
        server.server_close()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=2)
        for active_job_thread in active_job_threads.values():
            if active_job_thread is not None:
                active_job_thread.join(timeout=2)
