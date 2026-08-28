"""Compare the active V2--V6 batch identity with current training inputs."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import tempfile
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_rebuild_snapshot


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {}


def compare_revision_vectors(
    installed: object,
    current: object,
) -> dict[str, Any]:
    """Compare published metadata only; never open or hash source datasets."""
    try:
        installed_vector = mushroom_ml_version_registry.validate_revision_vector(
            installed
        )
        current_vector = mushroom_ml_version_registry.validate_revision_vector(
            current
        )
    except ValueError as exc:
        return {
            "status": "unknown",
            "reason": "revision_vector_unavailable",
            "changed_categories": [],
            "errors": [str(exc)],
        }
    changed = [
        key
        for key in mushroom_ml_version_registry.REVISION_VECTOR_KEYS
        if installed_vector[key] != current_vector[key]
    ]
    return {
        "status": "current" if not changed else "stale",
        "reason": "revisions_match" if not changed else "revisions_changed",
        "changed_categories": changed,
        "errors": [],
    }


def publish_current_revisions(path: Path, vector: object) -> None:
    """Atomically publish the small live-input revision vector."""
    checked = mushroom_ml_version_registry.validate_revision_vector(vector)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(checked, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def restore_current_revisions(path: Path, previous: bytes | None) -> None:
    """Restore revision metadata as part of an installation rollback."""
    destination = Path(path)
    if previous is None:
        destination.unlink(missing_ok=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(previous)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


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
    runtime_manifest_path: Path | None = None,
    registry_path: Path,
    models_root: Path,
    observations_path: Path,
    reference_catalogs_path: Path,
    gis_mappings_path: Path,
    weather_data_dir: Path,
    gis_root: Path,
    gis_hash_cache_path: Path | None = None,
    extra_inputs: dict[str, Path] | None = None,
    current_revisions_path: Path | None = None,
    cache_seconds: float = 60.0,
    deep: bool = False,
) -> dict[str, Any]:
    """Return current/stale/unknown without exposing source paths to the UI."""
    registry: dict[str, Any] | None = None
    if runtime_manifest_path is None:
        try:
            registry = mushroom_ml_version_registry.load_registry(registry_path)
            runtime_manifest_path = mushroom_ml_version_registry.preferred_manifest_path(
                registry, models_root=models_root
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {
                "status": "invalid",
                "reason": "freshness_check_failed",
                "errors": [str(exc)],
            }
    if runtime_manifest_path is None:
        return {
            "status": "unknown",
            "reason": "preferred_version_missing",
            "errors": [],
        }
    runtime_path = Path(runtime_manifest_path)
    if not runtime_path.is_file():
        return {
            "status": "unknown",
            "reason": "runtime_batch_missing",
            "errors": [],
        }
    if not deep:
        try:
            if registry is None:
                registry = mushroom_ml_version_registry.load_registry(registry_path)
            batch = mushroom_ml_model_catalog.validate_batch_manifest(
                registry,
                json.loads(runtime_path.read_text(encoding="utf-8")),
            )
            installed_vector = batch.get("input_revisions")
            revisions_path = Path(
                current_revisions_path
                or Path(models_root) / "current-input-revisions.json"
            )
            if installed_vector is None or not revisions_path.is_file():
                return {
                    "status": "unknown",
                    "reason": "revision_vector_unavailable",
                    "batch_id": batch["batch_id"],
                    "snapshot_id": batch["snapshot_id"],
                    "changed_categories": [],
                    "errors": [],
                }
            current_vector = json.loads(revisions_path.read_text(encoding="utf-8"))
            result = compare_revision_vectors(installed_vector, current_vector)
            result.update(
                {"batch_id": batch["batch_id"], "snapshot_id": batch["snapshot_id"]}
            )
            return result
        except (FileNotFoundError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
            return {
                "status": "invalid",
                "reason": "freshness_check_failed",
                "changed_categories": [],
                "errors": [str(exc)],
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
        if registry is None:
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
                ignored_extra_inputs={"observation-features.json", "registry.json"},
                # Partitioned history is immutable and content-addressed. Its
                # generation id plus manifest digest is sufficient for this UI
                # freshness hint; candidate promotion uses the same authoritative
                # immutable identity while explicit deep audits hash every object.
                verify_weather_file_hashes=deep,
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


def audit_deep(**kwargs: Any) -> dict[str, Any]:
    """Run the explicit full-input audit, including weather object hashes."""
    return assess(**kwargs, cache_seconds=0.0, deep=True)
