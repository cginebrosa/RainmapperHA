"""Persistent coordinator configuration for a portable Rainmapper worker."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


SCHEMA_VERSION = "0.1"
CONFIG_RELATIVE_PATH = Path("config/coordinator.json")
TOKEN_RELATIVE_PATH = Path("secrets/coordinator-token")
MULTICOORDINATOR_SCHEMA_VERSION = "0.1"
SECONDARY_CONFIG_RELATIVE_PATH = Path("config/additional-coordinators.json")
SECONDARY_TOKEN_DIR = Path("secrets/coordinators")
PRIMARY_COORDINATOR_ID = "primary"
DEFAULT_MAX_COORDINATORS = 4
MAX_COORDINATORS_LIMIT = 16
_COORDINATOR_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")


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


def validate_coordinator_id(value: object) -> str:
    coordinator_id = str(value or "").strip()
    if not _COORDINATOR_ID_RE.fullmatch(coordinator_id):
        raise ValueError("Rainmapper coordinator ID is invalid.")
    return coordinator_id


def _empty_secondary_config() -> dict[str, Any]:
    return {
        "schema_version": MULTICOORDINATOR_SCHEMA_VERSION,
        "max_coordinators": DEFAULT_MAX_COORDINATORS,
        "coordinators": [],
    }


def _secondary_token_path(worker_data_dir: Path, coordinator_id: str) -> Path:
    checked_id = validate_coordinator_id(coordinator_id)
    if checked_id == PRIMARY_COORDINATOR_ID:
        raise ValueError("The primary coordinator uses its existing credential path.")
    return worker_data_dir.resolve() / SECONDARY_TOKEN_DIR / f"{checked_id}.token"


def _load_secondary_config(worker_data_dir: Path) -> dict[str, Any]:
    path = worker_data_dir.resolve() / SECONDARY_CONFIG_RELATIVE_PATH
    if not path.exists():
        return _empty_secondary_config()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load additional Rainmapper coordinators: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != MULTICOORDINATOR_SCHEMA_VERSION:
        raise ValueError("Additional Rainmapper coordinator configuration schema is invalid.")
    max_coordinators = payload.get("max_coordinators")
    if (
        not isinstance(max_coordinators, int)
        or isinstance(max_coordinators, bool)
        or not 1 <= max_coordinators <= MAX_COORDINATORS_LIMIT
    ):
        raise ValueError("Rainmapper coordinator limit is invalid.")
    rows = payload.get("coordinators")
    if not isinstance(rows, list):
        raise ValueError("Additional Rainmapper coordinators must be a list.")
    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Additional Rainmapper coordinator entry is invalid.")
        coordinator_id = validate_coordinator_id(row.get("coordinator_id"))
        if coordinator_id == PRIMARY_COORDINATOR_ID or coordinator_id in seen_ids:
            raise ValueError("Additional Rainmapper coordinator ID is duplicated or reserved.")
        rainmapper_url = normalize_rainmapper_url(str(row.get("rainmapper_url", "")))
        if rainmapper_url in seen_urls:
            raise ValueError("Additional Rainmapper coordinator URL is duplicated.")
        label = str(row.get("label", "") or rainmapper_url).strip()[:80]
        if not label:
            raise ValueError("Additional Rainmapper coordinator label is invalid.")
        normalized.append(
            {
                "coordinator_id": coordinator_id,
                "label": label,
                "rainmapper_url": rainmapper_url,
            }
        )
        seen_ids.add(coordinator_id)
        seen_urls.add(rainmapper_url)
    return {
        "schema_version": MULTICOORDINATOR_SCHEMA_VERSION,
        "max_coordinators": max_coordinators,
        "coordinators": normalized,
    }


def load_coordinators(
    worker_data_dir: Path, *, include_tokens: bool = False
) -> dict[str, Any]:
    """Load the untouched primary association plus additive secondary associations."""
    root = worker_data_dir.resolve()
    primary = load_coordinator_config(root, include_token=include_tokens)
    additional = _load_secondary_config(root)
    coordinators: list[dict[str, Any]] = []
    primary_url = str(primary.get("rainmapper_url", ""))
    if primary_url:
        primary_row: dict[str, Any] = {
            "coordinator_id": PRIMARY_COORDINATOR_ID,
            "label": "Primary",
            "rainmapper_url": primary_url,
            "has_token": bool(primary.get("has_token")),
            "primary": True,
        }
        if include_tokens:
            primary_row["token"] = str(primary.get("token", ""))
        coordinators.append(primary_row)
    seen_urls = {primary_url} if primary_url else set()
    for row in additional["coordinators"]:
        rainmapper_url = str(row["rainmapper_url"])
        if rainmapper_url in seen_urls:
            raise ValueError("A Rainmapper coordinator URL is configured more than once.")
        token_path = _secondary_token_path(root, str(row["coordinator_id"]))
        token = token_path.read_text(encoding="utf-8").strip() if token_path.exists() else ""
        loaded: dict[str, Any] = {
            **row,
            "has_token": bool(token),
            "primary": False,
        }
        if include_tokens:
            loaded["token"] = token
        coordinators.append(loaded)
        seen_urls.add(rainmapper_url)
    if len(coordinators) > int(additional["max_coordinators"]):
        raise ValueError("Configured Rainmapper coordinators exceed the persisted limit.")
    return {
        "schema_version": MULTICOORDINATOR_SCHEMA_VERSION,
        "max_coordinators": int(additional["max_coordinators"]),
        "coordinators": coordinators,
    }


def add_coordinator(
    worker_data_dir: Path,
    *,
    rainmapper_url: str,
    token: str,
    label: str = "",
) -> dict[str, Any]:
    """Add or refresh a secondary coordinator without rewriting the primary files."""
    root = worker_data_dir.resolve()
    normalized_url = normalize_rainmapper_url(rainmapper_url)
    clean_token = str(token or "").strip()
    if len(clean_token) < 32:
        raise ValueError("A valid Rainmapper coordinator credential is required.")
    primary = load_coordinator_config(root)
    if normalized_url == str(primary.get("rainmapper_url", "")):
        raise ValueError("The Rainmapper coordinator is already configured as primary.")
    payload = _load_secondary_config(root)
    rows = [dict(row) for row in payload["coordinators"]]
    existing = next((row for row in rows if row["rainmapper_url"] == normalized_url), None)
    if existing is None:
        configured_count = len(rows) + (1 if primary.get("rainmapper_url") else 0)
        if configured_count >= int(payload["max_coordinators"]):
            raise ValueError("Rainmapper coordinator limit reached.")
        digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:16]
        coordinator_id = validate_coordinator_id(f"coordinator_{digest}")
        existing = {
            "coordinator_id": coordinator_id,
            "label": str(label or normalized_url).strip()[:80],
            "rainmapper_url": normalized_url,
        }
        rows.append(existing)
    elif label:
        existing["label"] = str(label).strip()[:80]
    if not existing["label"]:
        raise ValueError("Rainmapper coordinator label is invalid.")
    token_path = _secondary_token_path(root, str(existing["coordinator_id"]))
    _write_atomic(token_path, clean_token + "\n")
    updated = {
        "schema_version": MULTICOORDINATOR_SCHEMA_VERSION,
        "max_coordinators": int(payload["max_coordinators"]),
        "coordinators": rows,
    }
    _write_atomic(
        root / SECONDARY_CONFIG_RELATIVE_PATH,
        json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
    )
    return next(
        row
        for row in load_coordinators(root)["coordinators"]
        if row["coordinator_id"] == existing["coordinator_id"]
    )


def forget_coordinator(worker_data_dir: Path, coordinator_id: str) -> bool:
    checked_id = validate_coordinator_id(coordinator_id)
    if checked_id == PRIMARY_COORDINATOR_ID:
        raise ValueError("The primary coordinator cannot be forgotten by this command.")
    root = worker_data_dir.resolve()
    payload = _load_secondary_config(root)
    rows = [row for row in payload["coordinators"] if row["coordinator_id"] != checked_id]
    if len(rows) == len(payload["coordinators"]):
        return False
    updated = {**payload, "coordinators": rows}
    _write_atomic(
        root / SECONDARY_CONFIG_RELATIVE_PATH,
        json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
    )
    _secondary_token_path(root, checked_id).unlink(missing_ok=True)
    return True


def set_max_coordinators(worker_data_dir: Path, value: int) -> int:
    if isinstance(value, bool) or not 1 <= int(value) <= MAX_COORDINATORS_LIMIT:
        raise ValueError(f"Rainmapper coordinator limit must be between 1 and {MAX_COORDINATORS_LIMIT}.")
    root = worker_data_dir.resolve()
    configured = load_coordinators(root)["coordinators"]
    if int(value) < len(configured):
        raise ValueError("Rainmapper coordinator limit is below the configured association count.")
    payload = _load_secondary_config(root)
    payload["max_coordinators"] = int(value)
    _write_atomic(
        root / SECONDARY_CONFIG_RELATIVE_PATH,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )
    return int(value)


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
