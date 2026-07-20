"""Persistent coordinator configuration for a portable Rainmapper worker."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


SCHEMA_VERSION = "0.1"
CONFIG_RELATIVE_PATH = Path("config/coordinator.json")
TOKEN_RELATIVE_PATH = Path("secrets/coordinator-token")


def normalize_rainmapper_url(value: str) -> str:
    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("Rainmapper URL has an invalid port.") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Rainmapper URL must start with http:// or https:// and include a host.")
    if parsed.username or parsed.password:
        raise ValueError("Rainmapper URL must not contain credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("Rainmapper URL must not contain a query string or fragment.")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _write_atomic(path: Path, content: str, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_coordinator_config(worker_data_dir: Path, *, include_token: bool = False) -> dict[str, Any]:
    config_path = worker_data_dir / CONFIG_RELATIVE_PATH
    token_path = worker_data_dir / TOKEN_RELATIVE_PATH
    if not config_path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "rainmapper_url": "",
            "has_token": token_path.exists() and bool(token_path.read_text(encoding="utf-8").strip()),
            **({"token": token_path.read_text(encoding="utf-8").strip()} if include_token and token_path.exists() else {}),
        }
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load Rainmapper coordinator configuration: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Rainmapper coordinator configuration schema is invalid.")
    rainmapper_url = normalize_rainmapper_url(str(payload.get("rainmapper_url", "")))
    token = token_path.read_text(encoding="utf-8").strip() if token_path.exists() else ""
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "rainmapper_url": rainmapper_url,
        "has_token": bool(token),
    }
    if include_token:
        result["token"] = token
    return result


def save_coordinator_config(
    worker_data_dir: Path,
    *,
    rainmapper_url: str,
    token: str | None = None,
) -> dict[str, Any]:
    normalized_url = normalize_rainmapper_url(rainmapper_url)
    config_path = worker_data_dir / CONFIG_RELATIVE_PATH
    token_path = worker_data_dir / TOKEN_RELATIVE_PATH
    payload = {"schema_version": SCHEMA_VERSION, "rainmapper_url": normalized_url}
    _write_atomic(config_path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    if token is not None:
        clean_token = str(token).strip()
        if clean_token:
            _write_atomic(token_path, clean_token + "\n")
        else:
            token_path.unlink(missing_ok=True)
    return load_coordinator_config(worker_data_dir)


def clear_coordinator_token(worker_data_dir: Path) -> bool:
    """Remove the persisted coordinator credential without requiring network access."""
    token_path = worker_data_dir / TOKEN_RELATIVE_PATH
    existed = token_path.exists()
    token_path.unlink(missing_ok=True)
    return existed


def probe_coordinator(
    rainmapper_url: str,
    *,
    token: str = "",
    worker_id: str = "",
    timeout: float = 5.0,
) -> dict[str, Any]:
    normalized_url = normalize_rainmapper_url(rainmapper_url)
    endpoint = normalized_url + "/api/mushrooms/workers/ping"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if worker_id:
        headers["X-Rainmapper-Worker"] = worker_id
    request = Request(endpoint, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(65537)
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise ValueError("Rainmapper rejected the worker credentials.") from exc
        raise ValueError(f"Rainmapper connectivity check returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ValueError(f"Cannot reach Rainmapper at {normalized_url}: {reason}") from exc
    if len(raw) > 65536:
        raise ValueError("Rainmapper connectivity response is too large.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Rainmapper connectivity response is not valid JSON.") from exc
    if (
        not isinstance(payload, dict)
        or not payload.get("ok")
        or payload.get("kind") != "rainmapper_worker_coordinator"
    ):
        raise ValueError("The configured URL is reachable but is not a compatible Rainmapper worker coordinator.")
    if payload.get("auth_required") and not token:
        raise ValueError(
            "Rainmapper requires pairing. Generate a temporary code in Workers and jobs, "
            "then enter it when starting the worker."
        )
    if payload.get("auth_required") and not payload.get("authenticated"):
        raise ValueError("Rainmapper rejected the worker credentials.")
    return dict(payload)


def pair_coordinator(
    rainmapper_url: str,
    *,
    pairing_code: str,
    identity: dict[str, str],
    timeout: float = 5.0,
) -> dict[str, Any]:
    normalized_url = normalize_rainmapper_url(rainmapper_url)
    clean_code = str(pairing_code or "").strip().upper()
    if not clean_code or len(clean_code) > 40:
        raise ValueError("A valid temporary pairing code is required.")
    request = Request(
        normalized_url + "/api/mushrooms/workers/pair",
        data=json.dumps(
            {
                "pairing_code": clean_code,
                "worker_id": str(identity.get("worker_id", "")),
                "display_name": str(identity.get("display_name", "")),
                "host_name": str(identity.get("host_name", "")),
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(65537)
    except HTTPError as exc:
        if exc.code in {401, 403, 409}:
            raise ValueError("Rainmapper rejected the temporary pairing code.") from exc
        raise ValueError(f"Rainmapper pairing returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ValueError(f"Cannot reach Rainmapper at {normalized_url}: {reason}") from exc
    if len(raw) > 65536:
        raise ValueError("Rainmapper pairing response is too large.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Rainmapper pairing response is not valid JSON.") from exc
    token = str(payload.get("token", "")) if isinstance(payload, dict) else ""
    if not isinstance(payload, dict) or not payload.get("ok") or len(token) < 32:
        raise ValueError("Rainmapper returned an invalid worker credential.")
    return dict(payload)
