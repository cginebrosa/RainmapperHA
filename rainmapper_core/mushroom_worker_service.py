"""Local status service for the portable Rainmapper worker."""

from __future__ import annotations

import json
import http.client
import os
import platform
import secrets
import shutil
import signal
import subprocess
import sys
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
from rainmapper_core import mushroom_worker_registry
from rainmapper_core import mushroom_predictor_runtime
from rainmapper_core.mushroom_predictor_service import PredictorService


SCHEMA_VERSION = "0.1"
IDENTITY_SCHEMA_VERSION = "0.1"
IDENTITY_RELATIVE_PATH = Path("identity/worker.json")
JOB_TELEMETRY_INTERVAL_SECONDS = 2.0
_T = TypeVar("_T")


class _CoalescedJobTelemetry:
    """Bound remote job telemetry while preserving cancellation and final state."""

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

    def poll_control(self, *, force: bool = False) -> dict[str, Any]:
        now = self._monotonic()
        if not force and now < self._next_control_at:
            return {}
        control = self._update("control", dict(self._base_payload))
        self._next_control_at = now + self._interval_seconds
        if control.get("cancel_requested"):
            error = InterruptedError(self._cancel_message)
            setattr(error, "force_cancel_requested", bool(control.get("force_cancel_requested")))
            raise error
        return control

    def publish(self, progress: dict[str, Any], *, force: bool = False) -> None:
        self._pending_progress = {**self._base_payload, **progress}
        self.poll_control()
        now = self._monotonic()
        if not force and now < self._next_progress_at:
            return
        self._update("progress", self._pending_progress)
        self._pending_progress = None
        self._next_progress_at = now + self._interval_seconds

    def flush(self) -> None:
        self.poll_control(force=True)
        if self._pending_progress is not None:
            self._update("progress", self._pending_progress)
            self._pending_progress = None
            self._next_progress_at = self._monotonic() + self._interval_seconds


def retry_transient(
    operation: Callable[[], _T],
    *,
    retry_seconds: float,
    retry_interval: float = 1.0,
    stop_event: threading.Event | None = None,
) -> _T:
    """Retry short transport outages without retrying HTTP contract failures."""
    deadline = time.monotonic() + max(0.0, retry_seconds)
    while True:
        try:
            return operation()
        except HTTPError:
            raise
        except (URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            if time.monotonic() >= deadline or (stop_event is not None and stop_event.is_set()):
                raise
            wait_seconds = min(max(0.01, retry_interval), max(0.01, deadline - time.monotonic()))
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
            mushroom_worker_registry.TERMINAL_JOB_CLEANUP_CAPABILITY,
            mushroom_worker_registry.PREDICTOR_CAPABILITY,
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
    manifest = mushroom_predictor_runtime.validate_manifest(job.get("runtime_manifest"))
    headers = mushroom_worker_transport.request_headers(worker_id, claim_token, token)

    def fetch(logical_path: str, target: Path) -> None:
        query = urlencode({"job_id": job.get("job_id", ""), "file": logical_path})
        request = Request(ha_url.rstrip("/") + endpoint + "?" + query, headers=headers, method="GET")
        with urlopen(request, timeout=120) as response, target.open("xb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)

    return mushroom_predictor_runtime.synchronize_runtime(
        worker_data_dir.resolve() / "predictor-runtime",
        manifest,
        fetch,
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
) -> dict[str, Any] | None:
    endpoint = ha_url.rstrip("/") + "/api/mushrooms/workers/jobs/claim"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        endpoint,
        data=json.dumps({"worker_id": worker_id}, ensure_ascii=False).encode("utf-8"),
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
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(65537)
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
    runtime_state: dict[str, str],
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
                runtime_status = str(runtime_state.get("status", "idle"))
            payload = worker_status(
                worker_data_dir,
                worker_version=worker_version,
                identity=identity,
                runtime_status=runtime_status,
            )
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
    runtime_state = {"status": "idle", "active_job_id": ""}
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
    active_job_thread: threading.Thread | None = None
    probe_duration = max(2.0, float(os.environ.get("RAINMAPPER_WORKER_CLAIM_PROBE_SECONDS", "12")))
    job_retry_seconds = max(
        0.0,
        float(os.environ.get("RAINMAPPER_WORKER_JOB_RETRY_SECONDS", "120")),
    )

    if ha_url:
        def set_runtime(status: str, job_id: str = "") -> None:
            with runtime_lock:
                runtime_state["status"] = status
                runtime_state["active_job_id"] = job_id

        def run_claimed_job(job: dict[str, Any]) -> None:
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
                    lambda: update_job(ha_url, action, payload, token=token),
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
            try:
                job_type = str(job.get("job_type", ""))
                if job_type not in {
                    "worker_claim_probe",
                    "worker_snapshot_transport_probe",
                    "worker_candidate_rebuild",
                    "worker_ml_train_v0",
                    "worker_predictor_v1",
                }:
                    raise ValueError("Worker received an unsupported job type.")
                job_update(
                    "start",
                    {"job_id": job_id, "worker_id": identity["worker_id"], "claim_token": claim_token},
                )
                started = True
                set_runtime("busy", job_id)
                if job_type == "worker_predictor_v1":
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
                            predictor_services.clear()
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
                        job_update,
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

                    verification = with_transport_retry(
                        lambda: mushroom_worker_results.upload_candidate_result(
                            ha_url,
                            job,
                            worker_job_dir,
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                            progress_callback=upload_progress,
                        )
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
                        job_update,
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

                    verification = with_transport_retry(
                        lambda: mushroom_worker_results.upload_ml_train_result(
                            ha_url,
                            job,
                            worker_job_dir,
                            worker_id=identity["worker_id"],
                            claim_token=claim_token,
                            token=token,
                            progress_callback=ml_upload_progress,
                        )
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
                set_runtime("idle")

        def heartbeat_loop() -> None:
            nonlocal active_job_thread
            last_error = ""
            while not stop_event.is_set():
                try:
                    with runtime_lock:
                        runtime_status = str(runtime_state.get("status", "idle"))
                    status = worker_status(
                        worker_data_dir.resolve(),
                        worker_version=resolved_version,
                        identity=identity,
                        runtime_status=runtime_status,
                    )
                    with runtime_lock:
                        worker_has_job = bool(runtime_state.get("active_job_id"))
                        active_job_id = str(runtime_state.get("active_job_id", "") or "")
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
                        if worker_has_job and resolved_discard_job_id == active_job_id:
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
                        if worker_has_job and resolved_cleanup_job_id == active_job_id:
                            continue
                        mushroom_worker_transport.discard_worker_job(
                            worker_data_dir.resolve(),
                            resolved_cleanup_job_id,
                        )
                        with runtime_lock:
                            cleaned_job_ids_pending.add(resolved_cleanup_job_id)
                    if not worker_has_job and (active_job_thread is None or not active_job_thread.is_alive()):
                        claimed_job = claim_job(ha_url, identity["worker_id"], token=token)
                    else:
                        claimed_job = None
                    if claimed_job is not None and not stop_event.is_set():
                        set_runtime("busy", str(claimed_job.get("job_id", "")))
                        print(
                            json.dumps(
                                {
                                    "status": "job_claimed",
                                    "service": "rainmapper-worker",
                                    "job_id": claimed_job.get("job_id", ""),
                                    "job_type": claimed_job.get("job_type", ""),
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                        active_job_thread = threading.Thread(
                            target=run_claimed_job,
                            args=(claimed_job,),
                            daemon=True,
                            name="rainmapper-worker-job",
                        )
                        active_job_thread.start()
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
        if active_job_thread is not None:
            active_job_thread.join(timeout=2)
