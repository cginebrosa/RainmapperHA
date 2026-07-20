"""Persistent hashed credentials for authenticated Rainmapper workers."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core.mushroom_worker_registry import WORKER_ID_PATTERN


SCHEMA_VERSION = "0.1"
MIN_TOKEN_LENGTH = 32


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def empty_credentials() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "workers": []}


def load_credentials(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_credentials()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load worker credentials: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Worker credential schema is invalid.")
    workers = payload.get("workers")
    if not isinstance(workers, list):
        raise ValueError("Worker credential list is invalid.")
    return {
        "schema_version": SCHEMA_VERSION,
        "workers": [dict(row) for row in workers if isinstance(row, dict)],
    }


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
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def issue_credential(
    path: Path,
    *,
    worker_id: str,
    token: str | None = None,
    paired_at: str | None = None,
) -> str:
    resolved_worker_id = str(worker_id or "").strip()
    if not WORKER_ID_PATTERN.fullmatch(resolved_worker_id):
        raise ValueError("Worker ID is invalid.")
    resolved_token = str(token or secrets.token_urlsafe(32)).strip()
    if len(resolved_token) < MIN_TOKEN_LENGTH:
        raise ValueError("Worker credential token is too short.")
    timestamp = paired_at or utc_now()
    credentials = load_credentials(path)
    workers = credentials["workers"]
    existing = next(
        (row for row in workers if str(row.get("worker_id", "")) == resolved_worker_id),
        None,
    )
    row = {
        "worker_id": resolved_worker_id,
        "token_hash": token_hash(resolved_token),
        "paired_at": timestamp,
    }
    if existing is None:
        workers.append(row)
    else:
        existing.clear()
        existing.update(row)
    workers.sort(key=lambda item: str(item.get("worker_id", "")))
    _write_atomic(path, credentials)
    return resolved_token


def authenticate(path: Path, *, worker_id: str, token: str) -> bool:
    resolved_worker_id = str(worker_id or "").strip()
    resolved_token = str(token or "").strip()
    if not WORKER_ID_PATTERN.fullmatch(resolved_worker_id) or not resolved_token:
        return False
    credentials = load_credentials(path)
    row = next(
        (item for item in credentials["workers"] if str(item.get("worker_id", "")) == resolved_worker_id),
        None,
    )
    expected = str(row.get("token_hash", "")) if row is not None else ""
    supplied = token_hash(resolved_token)
    return bool(expected) and secrets.compare_digest(expected, supplied)


def is_paired(path: Path, *, worker_id: str) -> bool:
    return any(
        str(row.get("worker_id", "")) == str(worker_id or "").strip()
        for row in load_credentials(path)["workers"]
    )


def revoke_credential(path: Path, *, worker_id: str) -> bool:
    credentials = load_credentials(path)
    before = len(credentials["workers"])
    credentials["workers"] = [
        row for row in credentials["workers"] if str(row.get("worker_id", "")) != str(worker_id or "").strip()
    ]
    if len(credentials["workers"]) == before:
        return False
    _write_atomic(path, credentials)
    return True
