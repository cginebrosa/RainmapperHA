"""Durable, bounded final notifications for the background precompute lane.

The artifact is delivered separately. This file holds only the existing finish
request, never the SQLite or prediction rows. One slot per coordinator prevents
an unavailable receiver from accumulating results indefinitely.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

from rainmapper_core.mushroom_worker_transport import validate_job_id


MAX_NOTICE_BYTES = 64 * 1024


class JobUpdateRejected(ValueError):
    def __init__(self, action: str, code: int, detail: str) -> None:
        self.code = code
        self.detail = detail
        suffix = f": {detail[:1000]}" if detail else ""
        super().__init__(f"HA rejected the worker job {action} request with HTTP {code}{suffix}")


class PrecomputeCompletion:
    def __init__(self, precompute_root: Path) -> None:
        self.path = precompute_root / "pending-finish.json"
        self.lock = threading.RLock()

    def pending(self) -> dict[str, Any] | None:
        with self.lock:
            try:
                with self.path.open("rb") as stream:
                    raw = stream.read(MAX_NOTICE_BYTES + 1)
            except FileNotFoundError:
                return None
            if len(raw) > MAX_NOTICE_BYTES:
                raise ValueError("Precompute completion notice is too large.")
            payload = json.loads(raw)
            validate_job_id(payload["job_id"])
            if payload.get("status") not in {"complete", "failed", "cancelled"}:
                raise ValueError("Precompute completion status is invalid.")
            return payload

    def _write(self, payload: dict[str, Any]) -> None:
        # Bound serialization before opening a file; no partial durable notice.
        raw = bytearray()
        for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False).iterencode(payload):
            encoded = chunk.encode("utf-8")
            if len(raw) + len(encoded) > MAX_NOTICE_BYTES:
                raise ValueError("Precompute completion notice is too large.")
            raw.extend(encoded)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".pending-finish-", dir=self.path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)  # mkstemp preserves private mode 0600.
            self._sync_directory()
        finally:
            temporary.unlink(missing_ok=True)

    def _sync_directory(self) -> None:
        fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def remember(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            validate_job_id(payload["job_id"])
            if payload.get("status") not in {"complete", "failed", "cancelled"}:
                raise ValueError("Precompute completion status is invalid.")
            current = self.pending()
            if current is not None:
                if any(current.get(key) != payload.get(key) for key in ("job_id", "worker_id", "claim_token")):
                    raise ValueError("Another precompute completion is awaiting acknowledgement.")
                # A lost successful response must never turn complete into failed.
                return current
            self._write(payload)
            return payload

    def deliver(self, send: Callable[[str, dict[str, Any]], dict[str, Any]]) -> dict[str, Any] | None:
        """One bounded attempt. Network failures leave the notice intact."""
        with self.lock:
            payload = self.pending()
            if payload is None:
                return None
            try:
                result = send("finish", payload)
            except JobUpdateRejected as exc:
                if exc.code == 409 and exc.detail in {
                    "Worker job was already finished with a different status.",
                    "Worker job claim is no longer valid.",
                    "Worker job belongs to a different worker.",
                    "Worker job was not found.",
                }:
                    # HA is authoritative: never resurrect abandonment or an old claim.
                    result = {"finish_superseded": True, "job": {"job_id": payload["job_id"]}}
                elif exc.code == 409 and exc.detail == "A cancelled worker job cannot publish a successful result.":
                    control = send("control", {key: payload[key] for key in ("job_id", "worker_id", "claim_token")})
                    if not control.get("cancel_requested"):
                        raise
                    payload = {
                        **{key: payload[key] for key in ("job_id", "worker_id", "claim_token")},
                        "status": "cancelled",
                        "error": "Cancelled by operator while final notification was pending.",
                    }
                    self._write(payload)
                    result = send("finish", payload)
                else:
                    raise
            self.path.unlink()
            self._sync_directory()
            return result
