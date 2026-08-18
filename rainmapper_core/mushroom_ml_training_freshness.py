"""Compare the active V2--V6 batch identity with current training inputs."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_rebuild_snapshot


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_beneath(root: Path, relative: str) -> Path:
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    resolved.relative_to(resolved_root)
    return resolved


def _file_marker(path: Path) -> str:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return f"{path}:missing"
    return f"{path}:{stat.st_size}:{stat.st_mtime_ns}"


def assess(
    *,
    runtime_manifest_path: Path,
    registry_path: Path,
    models_root: Path,
    observations_path: Path,
    reference_catalogs_path: Path,
    gis_mappings_path: Path,
    weather_data_dir: Path,
    gis_root: Path,
    gis_hash_cache_path: Path | None = None,
    extra_inputs: dict[str, Path] | None = None,
    cache_seconds: float = 60.0,
) -> dict[str, Any]:
    """Return current/stale/unknown without exposing source paths to the UI."""
    runtime_path = Path(runtime_manifest_path)
    if not runtime_path.is_file():
        return {
            "status": "unknown",
            "reason": "runtime_batch_missing",
            "errors": [],
        }
    marker_paths = [
        Path(observations_path),
        Path(reference_catalogs_path),
        Path(gis_mappings_path),
        Path(weather_data_dir) / "weather-history" / "CURRENT.json",
        Path(weather_data_dir) / mushroom_rebuild_snapshot.WEATHER_DAILY_PARQUET_NAME,
        *(Path(path) for path in (extra_inputs or {}).values()),
    ]
    cache_key = (
        f"{runtime_path.resolve()}:{runtime_path.stat().st_mtime_ns}:"
        f"{runtime_path.stat().st_size}:"
        + "|".join(_file_marker(path) for path in marker_paths)
    )
    now = time.monotonic()
    with _CACHE_LOCK:
        if (
            cache_seconds > 0
            and _CACHE.get("key") == cache_key
            and now - float(_CACHE.get("checked_at", 0.0)) < cache_seconds
        ):
            return dict(_CACHE["result"])
    try:
        registry = mushroom_ml_version_registry.load_registry(registry_path)
        batch = mushroom_ml_model_catalog.validate_batch_manifest(
            registry,
            json.loads(runtime_path.read_text(encoding="utf-8")),
        )
        training_ref = batch.get("training_input_manifest")
        if not isinstance(training_ref, dict):
            result = {
                "status": "unknown",
                "reason": "training_identity_unavailable",
                "batch_id": batch["batch_id"],
                "snapshot_id": batch["snapshot_id"],
                "errors": [],
            }
        else:
            training_path = _resolve_beneath(
                Path(models_root), str(training_ref["path"])
            )
            if (
                not training_path.is_file()
                or _sha256(training_path) != training_ref["sha256"]
            ):
                raise ValueError("training input identity integrity failed")
            training_manifest = json.loads(training_path.read_text(encoding="utf-8"))
            verification = mushroom_rebuild_snapshot.verify_live_inputs(
                training_manifest,
                observations_path=observations_path,
                reference_catalogs_path=reference_catalogs_path,
                gis_mappings_path=gis_mappings_path,
                weather_data_dir=weather_data_dir,
                gis_root=gis_root,
                gis_hash_cache_path=gis_hash_cache_path,
                extra_inputs=extra_inputs,
                # This artifact is a derived reconstruction output. Promotion
                # rebases its private paths to live paths, changing its bytes
                # without changing the authoritative training observations.
                ignored_extra_inputs={"observation-features.json"},
                # Partitioned history is immutable and content-addressed. Its
                # generation id plus manifest digest is sufficient for this UI
                # freshness hint; candidate promotion still performs deep hashes.
                verify_weather_file_hashes=False,
            )
            result = {
                "status": "current"
                if verification["status"] == "valid"
                else "stale",
                "reason": "inputs_match"
                if verification["status"] == "valid"
                else "inputs_changed",
                "batch_id": batch["batch_id"],
                "snapshot_id": batch["snapshot_id"],
                "current_snapshot_id": verification.get("current_snapshot_id"),
                "errors": list(verification.get("errors", [])),
            }
    except (FileNotFoundError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "status": "invalid",
            "reason": "freshness_check_failed",
            "errors": [str(exc)],
        }
    with _CACHE_LOCK:
        _CACHE.clear()
        _CACHE.update({"key": cache_key, "checked_at": now, "result": dict(result)})
    return result


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
