"""Immutable, content-addressed runtime contract for remote prediction."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

from rainmapper_core import mushroom_paths


SCHEMA_VERSION = "1.0"
MANIFEST_KIND = "rainmapper_mushroom_predictor_runtime"
FEATURE_CONTRACT = "mushroom_features_v0"
MODEL_CONTRACT = "mushroom_ml_v0_plus_shadow_v1_joblib"
WEATHER_CONTRACT = "weather_parquet_v1"
_DIGEST_CACHE: dict[tuple[str, int, int], str] = {}


def _sha256(path: Path) -> str:
    stat = path.stat()
    key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    cached = _DIGEST_CACHE.get(key)
    if cached:
        return cached
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    value = f"sha256:{digest.hexdigest()}"
    _DIGEST_CACHE[key] = value
    return value


def _entry(role: str, logical_path: str, source: Path) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(f"Predictor runtime file is missing: {source}")
    return {
        "role": role,
        "path": logical_path,
        "size_bytes": source.stat().st_size,
        "sha256": _sha256(source),
    }


def build_manifest(
    *,
    weather_data_dir: Path | None = None,
    models_dir: Path | None = None,
    features_artifact_path: Path | None = None,
    known_sites_path: Path | None = None,
    profiles_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    weather = Path(weather_data_dir or mushroom_paths.weather_data_dir())
    models = Path(models_dir or mushroom_paths.mushroom_ml_models_dir())
    features = Path(features_artifact_path or mushroom_paths.mushroom_observation_features_json_path())
    known_sites = Path(known_sites_path or mushroom_paths.mushroom_known_sites_path())
    profiles = Path(profiles_path or mushroom_paths.mushroom_profiles_path())
    sources: dict[str, Path] = {
        "weather/weather_daily.parquet": weather / "weather_daily.parquet",
        "weather/weather_stations_catalog.parquet": weather / "weather_stations_catalog.parquet",
        "data/mushroom_observation_features_v0.json": features,
        "data/mushroom_known_sites.json": known_sites,
        "data/mushroom_profiles.json": profiles,
    }
    for model in sorted(models.glob("mushroom_ml_v0_*.joblib")):
        sources[f"models/{model.name}"] = model
    for model in sorted(models.glob("mushroom_ml_experiment_*.joblib")):
        sources[f"models/{model.name}"] = model
    if not any(path.startswith("models/") for path in sources):
        raise FileNotFoundError(f"Predictor runtime has no trained models in {models}.")

    files = []
    for logical_path, source in sorted(sources.items()):
        role = logical_path.split("/", 1)[0]
        files.append(_entry(role, logical_path, source))
    identity = {
        "schema_version": SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "contracts": {
            "features": FEATURE_CONTRACT,
            "models": MODEL_CONTRACT,
            "weather": WEATHER_CONTRACT,
        },
        "files": files,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    identity["fingerprint"] = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    identity["size_bytes"] = sum(row["size_bytes"] for row in files)
    return identity, sources


def validate_manifest(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Predictor runtime manifest must be an object.")
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("kind") != MANIFEST_KIND:
        raise ValueError("Unsupported predictor runtime manifest.")
    fingerprint = str(payload.get("fingerprint", ""))
    if not fingerprint.startswith("sha256:") or len(fingerprint) != 71:
        raise ValueError("Predictor runtime fingerprint is invalid.")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Predictor runtime file list is empty.")
    seen: set[str] = set()
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("Predictor runtime file entry is invalid.")
        logical_path = str(row.get("path", ""))
        candidate = Path(logical_path)
        if candidate.is_absolute() or ".." in candidate.parts or logical_path in seen:
            raise ValueError("Predictor runtime logical path is unsafe or duplicated.")
        seen.add(logical_path)
        digest = str(row.get("sha256", ""))
        size = row.get("size_bytes")
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError("Predictor runtime file digest is invalid.")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("Predictor runtime file size is invalid.")
    return dict(payload)


def resolve_source(manifest: dict[str, Any], sources: dict[str, Path], logical_path: str) -> Path:
    validate_manifest(manifest)
    entry = next((row for row in manifest["files"] if row["path"] == logical_path), None)
    source = sources.get(logical_path)
    if entry is None or source is None or not source.is_file():
        raise ValueError("Predictor runtime file is not authorized.")
    if source.stat().st_size != entry["size_bytes"] or _sha256(source) != entry["sha256"]:
        raise ValueError("Predictor runtime source changed after manifest creation.")
    return source


def synchronize_runtime(
    cache_root: Path,
    manifest: object,
    fetch: Callable[[str, Path], None],
) -> tuple[Path, dict[str, Any]]:
    """Materialize one runtime, reusing identical files from the current one."""
    checked = validate_manifest(manifest)
    fingerprint = checked["fingerprint"].removeprefix("sha256:")
    root = Path(cache_root)
    versions = root / "versions"
    destination = versions / fingerprint
    manifest_path = destination / "manifest.json"
    if manifest_path.is_file():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if existing.get("fingerprint") == checked["fingerprint"]:
                verify_runtime(destination, checked)
                _set_current(root, destination)
                return destination, {"status": "reused", "transferred_size_bytes": 0}
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    versions.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{fingerprint}.", suffix=".tmp", dir=versions))
    transferred = 0
    current = current_runtime(root)
    try:
        for row in checked["files"]:
            relative = Path(row["path"])
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            reused = False
            if current is not None:
                old = current / relative
                if old.is_file() and old.stat().st_size == row["size_bytes"] and _sha256(old) == row["sha256"]:
                    try:
                        os.link(old, target)
                    except OSError:
                        shutil.copy2(old, target)
                    reused = True
            if not reused:
                fetch(row["path"], target)
                transferred += row["size_bytes"]
            if target.stat().st_size != row["size_bytes"] or _sha256(target) != row["sha256"]:
                raise ValueError(f"Predictor runtime file verification failed: {row['path']}")
        manifest_path_staging = staging / "manifest.json"
        manifest_path_staging.write_text(
            json.dumps(checked, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(staging, destination)
        _set_current(root, destination)
        return destination, {"status": "synchronized", "transferred_size_bytes": transferred}
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _set_current(root: Path, destination: Path) -> None:
    current = root / "current"
    temporary = root / ".current.tmp"
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(destination.relative_to(root), target_is_directory=True)
    os.replace(temporary, current)


def current_runtime(root: Path) -> Path | None:
    current = Path(root) / "current"
    try:
        resolved = current.resolve(strict=True)
    except OSError:
        return None
    return resolved if resolved.is_dir() else None


def verify_runtime(root: Path, manifest: object) -> None:
    checked = validate_manifest(manifest)
    for row in checked["files"]:
        path = Path(root) / row["path"]
        if not path.is_file() or path.stat().st_size != row["size_bytes"] or _sha256(path) != row["sha256"]:
            raise ValueError(f"Predictor runtime is incomplete: {row['path']}")


def service_paths(runtime_root: Path) -> dict[str, Path]:
    root = Path(runtime_root)
    return {
        "models_dir": root / "models",
        "weather_data_dir": root / "weather",
        "features_artifact_path": root / "data/mushroom_observation_features_v0.json",
        "known_sites_path": root / "data/mushroom_known_sites.json",
        "profiles_path": root / "data/mushroom_profiles.json",
    }
