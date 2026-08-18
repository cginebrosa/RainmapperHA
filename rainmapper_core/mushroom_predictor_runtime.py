"""Immutable, content-addressed runtime contract for remote prediction."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

from rainmapper_core import mushroom_paths


SCHEMA_VERSION = "1.0"
MANIFEST_KIND = "rainmapper_mushroom_predictor_runtime"
FEATURE_CONTRACT = "mushroom_features_v0"
MODEL_CONTRACT = "mushroom_ml_v0_plus_shadow_v1_joblib"
MULTIVERSION_MODEL_CONTRACT = "mushroom_ml_v0_plus_multiversion_v1_joblib"
WEATHER_CONTRACT = "weather_parquet_v1"
PARTITIONED_WEATHER_CONTRACT = "partitioned_weather_history_v1"
_DIGEST_CACHE: dict[tuple[str, int, int], str] = {}
_ARCHIVE_LOCK = threading.Lock()


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
    version_registry_path: Path | None = None,
    runtime_batch_manifest_path: Path | None = None,
    stations_file_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    weather = Path(weather_data_dir or mushroom_paths.weather_data_dir())
    models = Path(models_dir or mushroom_paths.mushroom_ml_models_dir())
    features = Path(features_artifact_path or mushroom_paths.mushroom_observation_features_json_path())
    known_sites = Path(known_sites_path or mushroom_paths.mushroom_known_sites_path())
    profiles = Path(profiles_path or mushroom_paths.mushroom_profiles_path())
    version_registry = Path(
        version_registry_path or mushroom_paths.mushroom_ml_version_registry_path()
    )
    if runtime_batch_manifest_path is not None:
        runtime_batch_manifest = Path(runtime_batch_manifest_path)
    elif models_dir is not None:
        runtime_batch_manifest = models / "runtime-batch.json"
    else:
        runtime_batch_manifest = mushroom_paths.mushroom_ml_runtime_batch_manifest_path()
    sources: dict[str, Path] = {
        "data/mushroom_observation_features_v0.json": features,
        "data/mushroom_known_sites.json": known_sites,
        "data/mushroom_profiles.json": profiles,
    }
    stations_file = Path(stations_file_path or "/app/stations.txt")
    if stations_file.is_file():
        sources["data/stations.txt"] = stations_file
    partitioned_current = weather / "weather-history" / "CURRENT.json"
    weather_contract = WEATHER_CONTRACT
    if partitioned_current.is_file():
        from rainmapper_core.weather_history_dataset import resolve_weather_generation

        generation = resolve_weather_generation(weather)
        history_root = generation.root.resolve()
        history_files = [
            partitioned_current,
            generation.manifest_path,
            generation.object_path(generation.catalog.path),
            *(generation.object_path(partition.path) for partition in generation.partitions),
        ]
        for source in history_files:
            source = source.resolve()
            relative = source.relative_to(history_root).as_posix()
            sources[f"weather/weather-history/{relative}"] = source
        weather_contract = PARTITIONED_WEATHER_CONTRACT
    else:
        sources.update(
            {
                "weather/weather_daily.parquet": weather / "weather_daily.parquet",
                "weather/weather_stations_catalog.parquet": weather
                / "weather_stations_catalog.parquet",
            }
        )
    for model in sorted(models.glob("mushroom_ml_v0_*.joblib")):
        sources[f"models/{model.name}"] = model
    for model in sorted(models.glob("mushroom_ml_experiment_*.joblib")):
        sources[f"models/{model.name}"] = model
    model_contract = MODEL_CONTRACT
    if runtime_batch_manifest.is_file():
        from rainmapper_core import mushroom_ml_model_catalog
        from rainmapper_core import mushroom_ml_version_registry

        registry = mushroom_ml_version_registry.load_registry(version_registry)
        batch = mushroom_ml_model_catalog.validate_batch_manifest(
            registry,
            json.loads(runtime_batch_manifest.read_text(encoding="utf-8")),
        )
        sources["data/mushroom_ml_version_registry.json"] = version_registry
        sources["models/runtime-batch.json"] = runtime_batch_manifest
        quality_ref = batch.get("quality_catalog")
        if isinstance(quality_ref, dict):
            relative = Path(str(quality_ref["path"]))
            source = models / relative
            if not source.is_file() or _sha256(source) != f"sha256:{quality_ref['sha256']}":
                raise ValueError("Multiversion quality catalog is missing or has the wrong digest")
            sources[f"models/{relative.as_posix()}"] = source
        for artifact in batch["artifacts"]:
            relative = Path(str(artifact["path"]))
            source = models / relative
            if not source.is_file():
                raise FileNotFoundError(
                    f"Multiversion model declared by runtime batch is missing: {source}"
                )
            if _sha256(source) != f"sha256:{artifact['sha256']}":
                raise ValueError(
                    f"Multiversion model digest does not match runtime batch: {source}"
                )
            sources[f"models/{relative.as_posix()}"] = source
        model_contract = MULTIVERSION_MODEL_CONTRACT
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
            "models": model_contract,
            "weather": weather_contract,
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


def build_runtime_archive(
    cache_dir: Path,
    manifest: object,
    sources: dict[str, Path],
) -> Path:
    """Build one cached, content-addressed tar for low-latency worker transfer."""
    checked = validate_manifest(manifest)
    fingerprint = checked["fingerprint"].removeprefix("sha256:")
    root = Path(cache_dir)
    destination = root / f"{fingerprint}.tar"
    with _ARCHIVE_LOCK:
        if destination.is_file():
            return destination
        root.mkdir(parents=True, exist_ok=True)
        temporary = root / f".{fingerprint}.{os.getpid()}.tmp"
        temporary.unlink(missing_ok=True)
        try:
            with tarfile.open(temporary, mode="w") as archive:
                for row in checked["files"]:
                    logical_path = str(row["path"])
                    source = resolve_source(checked, sources, logical_path)
                    archive.add(source, arcname=logical_path, recursive=False)
            os.replace(temporary, destination)
            for candidate in root.glob("*.tar"):
                if candidate != destination:
                    candidate.unlink(missing_ok=True)
        finally:
            temporary.unlink(missing_ok=True)
    return destination


def synchronize_runtime_archive(
    cache_root: Path,
    manifest: object,
    archive_path: Path,
) -> tuple[Path, dict[str, Any]]:
    """Synchronize a runtime from one verified tar transport."""
    checked = validate_manifest(manifest)
    expected = {str(row["path"]) for row in checked["files"]}
    with tarfile.open(archive_path, mode="r:") as archive:
        members = {member.name: member for member in archive.getmembers()}
        if set(members) != expected or any(not member.isfile() for member in members.values()):
            raise ValueError("Predictor runtime archive contents do not match its manifest.")

        def fetch(logical_path: str, target: Path) -> None:
            source = archive.extractfile(members[logical_path])
            if source is None:
                raise ValueError(f"Predictor runtime archive file is missing: {logical_path}")
            with source, target.open("xb") as handle:
                shutil.copyfileobj(source, handle, length=1024 * 1024)

        return synchronize_runtime(cache_root, checked, fetch)


def cache_runtime_objects(
    cache_root: Path,
    records: list[tuple[Path, str, int]],
) -> dict[str, int]:
    """Retain worker-produced files by digest until a runtime can link them."""
    objects = Path(cache_root) / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    cached = 0
    cached_size = 0
    for source_value, digest_value, size_value in records:
        source = Path(source_value)
        digest = str(digest_value)
        if not digest.startswith("sha256:"):
            digest = f"sha256:{digest}"
        size = int(size_value)
        if not source.is_file() or source.stat().st_size != size or _sha256(source) != digest:
            raise ValueError(f"Worker-produced predictor object is invalid: {source}")
        destination = objects / digest.removeprefix("sha256:")
        if destination.is_file() and destination.stat().st_size == size and _sha256(destination) == digest:
            continue
        temporary = objects / f".{destination.name}.{os.getpid()}.tmp"
        temporary.unlink(missing_ok=True)
        try:
            try:
                os.link(source, temporary)
            except OSError:
                shutil.copy2(source, temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        cached += 1
        cached_size += size
    return {"cached_objects": cached, "cached_size_bytes": cached_size}


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
    objects = root / "objects"
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
                cached_object = objects / str(row["sha256"]).removeprefix("sha256:")
                if (
                    cached_object.is_file()
                    and cached_object.stat().st_size == row["size_bytes"]
                    and _sha256(cached_object) == row["sha256"]
                ):
                    try:
                        os.link(cached_object, target)
                    except OSError:
                        shutil.copy2(cached_object, target)
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
        pruned = _prune_runtime_versions(versions, keep={destination, current})
        shutil.rmtree(objects, ignore_errors=True)
        return destination, {
            "status": "synchronized",
            "transferred_size_bytes": transferred,
            "pruned_versions": pruned,
        }
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _set_current(root: Path, destination: Path) -> None:
    current = root / "current"
    temporary = root / ".current.tmp"
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(destination.relative_to(root), target_is_directory=True)
    os.replace(temporary, current)


def _prune_runtime_versions(versions: Path, *, keep: set[Path | None]) -> int:
    """Keep current and immediate predecessor; all files are reconstructible."""
    retained = {path.resolve() for path in keep if path is not None}
    removed = 0
    for candidate in versions.iterdir():
        if not candidate.is_dir() or candidate.resolve() in retained:
            continue
        shutil.rmtree(candidate)
        removed += 1
    return removed


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
        "version_registry_path": root / "data/mushroom_ml_version_registry.json",
        "runtime_batch_manifest_path": root / "models/runtime-batch.json",
        "stations_file_path": root / "data/stations.txt",
    }
