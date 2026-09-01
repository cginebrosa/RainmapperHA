"""Immutable, content-addressed runtime contract for remote prediction."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import threading
import time
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
VERIFIED_RECEIPT_SCHEMA_VERSION = "1.0"
VERIFIED_RECEIPT_KIND = "rainmapper_mushroom_predictor_runtime_verified"
PUBLICATION_SCHEMA_VERSION = "1.2"
PUBLICATION_KIND = "rainmapper_mushroom_predictor_runtime_publication"
RUNTIME_REGISTRY_SNAPSHOT_NAME = "mushroom_ml_version_registry.runtime.json"
_DIGEST_CACHE: dict[tuple[str, int, int], str] = {}
_ARCHIVE_LOCK = threading.Lock()
_PUBLICATION_LOCK = threading.Lock()


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


def _runtime_archive_matches(path: Path, manifest: dict[str, Any]) -> bool:
    expected = {str(row["path"]): row for row in manifest["files"]}
    try:
        with tarfile.open(path, mode="r:") as archive:
            members = archive.getmembers()
            if (
                len(members) != len(expected)
                or any(not member.isfile() or member.name not in expected for member in members)
            ):
                return False
            for member in members:
                row = expected[member.name]
                if member.size != int(row["size_bytes"]):
                    return False
                source = archive.extractfile(member)
                if source is None:
                    return False
                digest = hashlib.sha256()
                with source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                if f"sha256:{digest.hexdigest()}" != row["sha256"]:
                    return False
    except (OSError, tarfile.TarError, ValueError):
        return False
    return True


def _entry(role: str, logical_path: str, source: Path) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(f"Predictor runtime file is missing: {source}")
    return {
        "role": role,
        "path": logical_path,
        "size_bytes": source.stat().st_size,
        "sha256": _sha256(source),
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    temporary.unlink(missing_ok=True)
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _runtime_registry_snapshot(
    registry: dict[str, Any],
    *,
    source_path: Path,
    explicit_source: bool,
) -> Path:
    """Materialize a scientific registry whose runtime default is stable."""
    root = (
        Path(source_path).parent
        if explicit_source
        else mushroom_paths.prepare_predictor_runtime_archive_dir().path
    )
    destination = root / RUNTIME_REGISTRY_SNAPSHOT_NAME
    try:
        current = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        current = None
    installed = {
        str(row.get("version_id"))
        for row in registry.get("versions", [])
        if isinstance(row, dict) and row.get("installed_generation_id") is not None
    }
    current_default = (
        str(current.get("preferred_version_id") or "")
        if isinstance(current, dict)
        else ""
    )
    live_default = str(registry.get("preferred_version_id") or "")
    runtime_default = (
        current_default
        if current_default in installed
        else live_default if live_default in installed else None
    )
    payload = {**registry, "preferred_version_id": runtime_default}
    if current != payload:
        _atomic_write_json(destination, payload)
    return destination


def _verified_receipt_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": VERIFIED_RECEIPT_SCHEMA_VERSION,
        "kind": VERIFIED_RECEIPT_KIND,
        "fingerprint": manifest["fingerprint"],
        "file_count": len(manifest["files"]),
        "size_bytes": manifest["size_bytes"],
    }


def _write_verified_receipt(root: Path, manifest: dict[str, Any]) -> None:
    _atomic_write_json(Path(root) / "verified-runtime.json", _verified_receipt_payload(manifest))


def _verified_receipt_matches(root: Path, manifest: dict[str, Any]) -> bool:
    runtime_root = Path(root)
    receipt_path = runtime_root / "verified-runtime.json"
    manifest_path = runtime_root / "manifest.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        installed = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return (
        receipt == _verified_receipt_payload(manifest)
        and installed == manifest
        and runtime_root.name == str(manifest["fingerprint"]).removeprefix("sha256:")
    )


def build_manifest(
    *,
    weather_data_dir: Path | None = None,
    models_dir: Path | None = None,
    features_artifact_path: Path | None = None,
    known_sites_path: Path | None = None,
    profiles_path: Path | None = None,
    version_registry_path: Path | None = None,
    stations_file_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    weather = Path(weather_data_dir or mushroom_paths.weather_data_dir())
    models = Path(models_dir or mushroom_paths.mushroom_ml_models_dir())
    features = Path(features_artifact_path or mushroom_paths.mushroom_observation_features_json_path())
    known_sites = Path(known_sites_path or mushroom_paths.mushroom_known_sites_path())
    profiles = Path(profiles_path or mushroom_paths.mushroom_profiles_path())
    explicit_version_registry = version_registry_path is not None
    version_registry = Path(
        version_registry_path or mushroom_paths.mushroom_ml_version_registry_path()
    )
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
    if version_registry.is_file() and any(
        models.glob("batches/*/manifest.json")
    ):
        from rainmapper_core import mushroom_ml_model_catalog
        from rainmapper_core import mushroom_ml_version_registry

        registry = mushroom_ml_version_registry.load_registry(version_registry)
        sources["data/mushroom_ml_version_registry.json"] = (
            _runtime_registry_snapshot(
                registry,
                source_path=version_registry,
                explicit_source=explicit_version_registry,
            )
        )
        for version in registry["versions"]:
            version_id = str(version["version_id"])
            if version.get("installed_generation_id") is None:
                continue
            manifest_path = mushroom_ml_version_registry.installed_manifest_path(
                registry, version_id, models_root=models
            )
            if manifest_path is None or not manifest_path.is_file():
                raise FileNotFoundError(
                    f"Installed manifest is missing for {version_id}"
                )
            batch = mushroom_ml_model_catalog.validate_batch_manifest(
                registry, json.loads(manifest_path.read_text(encoding="utf-8"))
            )
            manifest_relative = manifest_path.relative_to(models)
            sources[f"models/{manifest_relative.as_posix()}"] = manifest_path
            for reference_name in (
                "quality_catalog",
                "training_input_manifest",
                "benchmark_report",
                "holdout_predictions",
            ):
                reference = batch.get(reference_name)
                if not isinstance(reference, dict):
                    continue
                relative = Path(str(reference["path"]))
                source = models / relative
                if not source.is_file() or _sha256(source) != f"sha256:{reference['sha256']}":
                    raise ValueError(
                        f"Installed {reference_name} is missing or has the wrong digest"
                    )
                sources[f"models/{relative.as_posix()}"] = source
            for artifact in batch["artifacts"]:
                relative = Path(str(artifact["path"]))
                source = models / relative
                if not source.is_file():
                    raise FileNotFoundError(
                        f"Installed model is missing for {version_id}: {source}"
                    )
                if _sha256(source) != f"sha256:{artifact['sha256']}":
                    raise ValueError(
                        f"Installed model digest does not match manifest: {source}"
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


def default_publication_path() -> Path:
    """Return the regenerable HA-side publication outside backup storage."""
    return mushroom_paths.prepare_predictor_runtime_archive_dir().path / "published-runtime.json"


def _dirty_publication_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.dirty")


def _publication_source_state(
    manifest: dict[str, Any], sources: dict[str, Path]
) -> dict[str, dict[str, object]]:
    rows = {str(row["path"]): row for row in manifest["files"]}
    state: dict[str, dict[str, object]] = {}
    for logical_path, source in sources.items():
        stat = source.stat()
        state[logical_path] = {
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": rows[logical_path]["sha256"],
        }
    return state


def _seed_digest_cache_from_publication(publication_path: Path) -> None:
    """Reuse persisted digests whose size and mtime still match the source."""
    try:
        payload = json.loads(Path(publication_path).read_text(encoding="utf-8"))
        if (
            payload.get("schema_version") != PUBLICATION_SCHEMA_VERSION
            or payload.get("kind") != PUBLICATION_KIND
        ):
            return
        manifest = validate_manifest(payload["manifest"])
        rows = {str(row["path"]): row for row in manifest["files"]}
        raw_sources = payload["sources"]
        raw_state = payload["source_state"]
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return
    if not isinstance(raw_sources, dict) or not isinstance(raw_state, dict):
        return
    for logical_path, raw_path in raw_sources.items():
        metadata = raw_state.get(logical_path)
        row = rows.get(str(logical_path))
        if not isinstance(metadata, dict) or row is None:
            continue
        source = Path(str(raw_path))
        try:
            stat = source.stat()
            size = int(metadata["size_bytes"])
            mtime_ns = int(metadata["mtime_ns"])
            digest = str(metadata["sha256"])
        except (KeyError, OSError, TypeError, ValueError):
            continue
        if (
            stat.st_size == size
            and stat.st_mtime_ns == mtime_ns
            and digest == row["sha256"]
            and size == row["size_bytes"]
        ):
            _DIGEST_CACHE[(str(source.resolve()), mtime_ns, size)] = digest


def publish_manifest(
    publication_path: Path,
    **build_options: Path | None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Hash changed live inputs and atomically publish one reusable identity."""
    destination = Path(publication_path)
    _seed_digest_cache_from_publication(destination)
    manifest, sources = build_manifest(**build_options)
    publication = {
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "kind": PUBLICATION_KIND,
        "manifest": manifest,
        "sources": {
            logical_path: str(source.resolve())
            for logical_path, source in sorted(sources.items())
        },
        "source_state": _publication_source_state(manifest, sources),
    }
    with _PUBLICATION_LOCK:
        _atomic_write_json(destination, publication)
        dirty = _dirty_publication_path(destination)
        if dirty.exists():
            dirty.unlink()
            _fsync_directory(destination.parent)
    return manifest, sources


def load_published_manifest(
    publication_path: Path,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Load a published identity without opening or hashing runtime objects."""
    source = Path(publication_path)
    if _dirty_publication_path(source).exists():
        raise ValueError("Predictor runtime publication is dirty.")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != PUBLICATION_SCHEMA_VERSION
        or payload.get("kind") != PUBLICATION_KIND
    ):
        raise ValueError("Predictor runtime publication is invalid.")
    manifest = validate_manifest(payload.get("manifest"))
    raw_sources = payload.get("sources")
    raw_state = payload.get("source_state")
    if not isinstance(raw_sources, dict) or set(raw_sources) != {
        str(row["path"]) for row in manifest["files"]
    }:
        raise ValueError("Predictor runtime publication source map is invalid.")
    if not isinstance(raw_state, dict) or set(raw_state) != set(raw_sources):
        raise ValueError("Predictor runtime publication source state is invalid.")
    sources: dict[str, Path] = {}
    manifest_rows = {str(row["path"]): row for row in manifest["files"]}
    for logical_path, raw_path in raw_sources.items():
        source_path = Path(str(raw_path))
        if not source_path.is_absolute():
            raise ValueError("Predictor runtime publication source path is invalid.")
        metadata = raw_state.get(logical_path)
        if not isinstance(metadata, dict):
            raise ValueError("Predictor runtime publication source state is invalid.")
        stat = source_path.stat()
        if (
            stat.st_size != int(metadata.get("size_bytes", -1))
            or stat.st_mtime_ns != int(metadata.get("mtime_ns", -1))
            or str(metadata.get("sha256", ""))
            != manifest_rows[logical_path]["sha256"]
        ):
            raise ValueError("Predictor runtime publication source changed.")
        sources[str(logical_path)] = source_path
        _DIGEST_CACHE[
            (str(source_path.resolve()), stat.st_mtime_ns, stat.st_size)
        ] = str(metadata["sha256"])
    return manifest, sources


def load_published_manifest_metadata(publication_path: Path) -> dict[str, Any]:
    """Load only the persisted manifest, without statting or hashing runtime files."""
    source = Path(publication_path)
    if _dirty_publication_path(source).exists():
        raise ValueError("Predictor runtime publication is dirty.")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != PUBLICATION_SCHEMA_VERSION
        or payload.get("kind") != PUBLICATION_KIND
    ):
        raise ValueError("Predictor runtime publication is invalid.")
    return validate_manifest(payload.get("manifest"))


def load_or_publish_manifest(
    publication_path: Path | None = None,
    **build_options: Path | None,
) -> tuple[dict[str, Any], dict[str, Path], str]:
    """Read the persistent publication, rebuilding it once when unavailable."""
    destination = Path(publication_path or default_publication_path())
    try:
        manifest, sources = load_published_manifest(destination)
        return manifest, sources, "reused"
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        manifest, sources = publish_manifest(destination, **build_options)
        return manifest, sources, "published"


def invalidate_published_manifest(publication_path: Path | None = None) -> None:
    """Mark a publication unusable before a writer changes runtime inputs."""
    destination = Path(publication_path or default_publication_path())
    with _PUBLICATION_LOCK:
        _atomic_write_json(
            _dirty_publication_path(destination),
            {
                "schema_version": PUBLICATION_SCHEMA_VERSION,
                "kind": PUBLICATION_KIND,
                "status": "dirty",
            },
        )


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
        if root.is_symlink():
            raise ValueError("Predictor runtime archive cache cannot be a symlink.")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)
        if destination.is_symlink():
            raise ValueError("Predictor runtime archive cannot be a symlink.")
        if destination.is_file() and _runtime_archive_matches(destination, checked):
            destination.chmod(0o600)
            for candidate in root.glob("*.tar"):
                if candidate != destination:
                    candidate.unlink(missing_ok=True)
            return destination
        destination.unlink(missing_ok=True)
        temporary = root / f".{fingerprint}.{os.getpid()}.tmp"
        temporary.unlink(missing_ok=True)
        try:
            with tarfile.open(temporary, mode="w") as archive:
                for row in checked["files"]:
                    logical_path = str(row["path"])
                    source = resolve_source(checked, sources, logical_path)
                    archive.add(source, arcname=logical_path, recursive=False)
            os.replace(temporary, destination)
            destination.chmod(0o600)
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
    synchronization_started = time.perf_counter()
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
                receipt_matched = _verified_receipt_matches(destination, checked)
                if not receipt_matched:
                    verify_runtime(destination, checked)
                    _write_verified_receipt(destination, checked)
                _set_current(root, destination)
                return destination, {
                    "status": "reused",
                    "transferred_size_bytes": 0,
                    "verification_status": "receipt",
                    "hashed_file_count": 0 if receipt_matched else len(checked["files"]),
                    "reused_file_count": len(checked["files"]),
                    "fetched_file_count": 0,
                    "elapsed_seconds": round(
                        time.perf_counter() - synchronization_started, 6
                    ),
                }
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    versions.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{fingerprint}.", suffix=".tmp", dir=versions))
    transferred = 0
    current = current_runtime(root)
    current_manifest: dict[str, Any] | None = None
    current_rows: dict[str, dict[str, Any]] = {}
    current_is_verified = False
    if current is not None:
        try:
            current_manifest = validate_manifest(
                json.loads((current / "manifest.json").read_text(encoding="utf-8"))
            )
            current_is_verified = _verified_receipt_matches(current, current_manifest)
            if current_is_verified:
                current_rows = {
                    str(row["path"]): row for row in current_manifest["files"]
                }
        except (OSError, ValueError, json.JSONDecodeError):
            current_manifest = None
    objects = root / "objects"
    hashed_files = 0
    reused_files = 0
    fetched_files = 0
    try:
        for row in checked["files"]:
            relative = Path(row["path"])
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            reused = False
            reused_verified = False
            if current is not None:
                old = current / relative
                old_row = current_rows.get(str(row["path"]))
                if (
                    current_is_verified
                    and old_row is not None
                    and old_row["size_bytes"] == row["size_bytes"]
                    and old_row["sha256"] == row["sha256"]
                ):
                    try:
                        os.link(old, target)
                    except OSError:
                        shutil.copy2(old, target)
                    reused = True
                    reused_verified = True
                elif (
                    not current_is_verified
                    and old.is_file()
                    and old.stat().st_size == row["size_bytes"]
                    and _sha256(old) == row["sha256"]
                ):
                    hashed_files += 1
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
                    hashed_files += 1
                    try:
                        os.link(cached_object, target)
                    except OSError:
                        shutil.copy2(cached_object, target)
                    reused = True
                    reused_verified = True
            if not reused:
                fetch(row["path"], target)
                transferred += row["size_bytes"]
                fetched_files += 1
            else:
                reused_files += 1
            if not reused_verified:
                hashed_files += 1
            if (
                target.stat().st_size != row["size_bytes"]
                or (not reused_verified and _sha256(target) != row["sha256"])
            ):
                raise ValueError(f"Predictor runtime file verification failed: {row['path']}")
        manifest_path_staging = staging / "manifest.json"
        _atomic_write_json(manifest_path_staging, checked)
        _write_verified_receipt(staging, checked)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(staging, destination)
        _fsync_directory(versions)
        _set_current(root, destination)
        pruned = _prune_runtime_versions(versions, keep={destination, current})
        shutil.rmtree(objects, ignore_errors=True)
        return destination, {
            "status": "synchronized",
            "transferred_size_bytes": transferred,
            "pruned_versions": pruned,
            "verification_status": "full",
            "hashed_file_count": hashed_files,
            "reused_file_count": reused_files,
            "fetched_file_count": fetched_files,
            "elapsed_seconds": round(
                time.perf_counter() - synchronization_started, 6
            ),
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
        "stations_file_path": root / "data/stations.txt",
    }
