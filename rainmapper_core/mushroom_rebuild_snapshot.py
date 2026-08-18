"""Versioned input snapshots for reproducible mushroom rebuilds."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from rainmapper_core import mushroom_gis_lab, mushroom_observation_context


SCHEMA_VERSION = "0.2"
SUPPORTED_SCHEMA_VERSIONS = {"0.1", SCHEMA_VERSION}
MANIFEST_NAME = "input_manifest.json"
GIS_HASH_CACHE_SCHEMA_VERSION = "0.1"
GIS_HASH_CACHE_KIND = "rainmapper_gis_hash_cache"
REQUIRED_INPUT_KEYS = {
    "observations",
    "reference_catalogs",
    "gis_mappings",
    "weather_data_dir",
}
WEATHER_DAILY_PARQUET_NAME = "weather_daily.parquet"


def _safe_relative_path(value: object, *, label: str) -> Path:
    text = str(value or "")
    logical = PurePosixPath(text)
    if not text or logical.is_absolute() or "." in logical.parts or ".." in logical.parts:
        raise ValueError(f"unsafe {label} path: {text!r}")
    if logical.as_posix() != text:
        raise ValueError(f"{label} path must be normalized POSIX: {text!r}")
    return Path(*logical.parts)


def _resolve_beneath(root: Path, value: object, *, label: str) -> Path:
    relative = _safe_relative_path(value, label=label)
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} path escapes its root: {value!r}") from exc
    return resolved


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_file_record(path: Path, *, logical_path: str, role: str) -> dict[str, object]:
    before = path.stat()
    digest = sha256_file(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"input changed while hashing: {path}")
    return {
        "role": role,
        "path": logical_path,
        "size_bytes": after.st_size,
        "sha256": digest,
    }


def _gis_cache_identity(path: Path, *, logical_path: str) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": logical_path,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "ctime_ns": stat.st_ctime_ns,
        "device": stat.st_dev,
        "inode": stat.st_ino,
    }


def _load_gis_hash_cache(path: Path | None) -> dict[str, dict[str, object]]:
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != GIS_HASH_CACHE_SCHEMA_VERSION
        or payload.get("kind") != GIS_HASH_CACHE_KIND
        or not isinstance(payload.get("files"), list)
    ):
        return {}
    return {
        str(row.get("path", "")): dict(row)
        for row in payload["files"]
        if isinstance(row, dict) and str(row.get("path", ""))
    }


def _write_gis_hash_cache(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": GIS_HASH_CACHE_SCHEMA_VERSION,
        "kind": GIS_HASH_CACHE_KIND,
        "files": records,
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def gis_file_records(
    gis_root: Path,
    *,
    hash_cache_path: Path | None = None,
) -> list[dict[str, object]]:
    """Hash GIS files once and reuse digests while their filesystem identity is unchanged."""
    root = gis_root.resolve()
    cached = _load_gis_hash_cache(hash_cache_path)
    records: list[dict[str, object]] = []
    cache_records: list[dict[str, object]] = []
    for path in gis_dataset_files(root):
        logical_path = path.relative_to(root).as_posix()
        identity = _gis_cache_identity(path, logical_path=logical_path)
        cached_record = cached.get(logical_path, {})
        cached_digest = str(cached_record.get("sha256", ""))
        if (
            all(cached_record.get(key) == value for key, value in identity.items())
            and re.fullmatch(r"[0-9a-f]{64}", cached_digest)
        ):
            record = {
                "role": "gis",
                "path": logical_path,
                "size_bytes": identity["size_bytes"],
                "sha256": cached_digest,
            }
        else:
            record = _stable_file_record(
                path,
                logical_path=logical_path,
                role="gis",
            )
            stable_identity = _gis_cache_identity(path, logical_path=logical_path)
            if stable_identity != identity:
                raise RuntimeError(f"input changed while hashing: {path}")
            identity = stable_identity
        records.append(record)
        cache_records.append({**identity, "sha256": record["sha256"]})
    if hash_cache_path is not None:
        _write_gis_hash_cache(hash_cache_path, cache_records)
    return records


def _fingerprint(records: list[dict[str, object]]) -> str:
    normalized = [
        {
            "role": record.get("role"),
            "path": record.get("path"),
            "size_bytes": record.get("size_bytes"),
            "sha256": record.get("sha256"),
            "exists": record.get("exists", True),
        }
        for record in records
    ]
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def gis_dataset_files(gis_root: Path) -> list[Path]:
    root = gis_root.resolve()
    layers = mushroom_gis_lab.vector_layers(root)
    mvc_path = layers[0].path
    mvc_files = sorted(
        path for path in mvc_path.parent.glob(f"{mvc_path.stem}.*") if path.is_file()
    )
    paths = [*mvc_files, layers[1].path, mushroom_gis_lab.dem_path(root)]
    andorra_dem = mushroom_gis_lab.andorra_dem_path(root)
    if andorra_dem.is_file():
        paths.append(andorra_dem)
    ign_mtn50_592_dem = mushroom_gis_lab.ign_mtn50_592_dem_path(root)
    if ign_mtn50_592_dem.is_file():
        paths.append(ign_mtn50_592_dem)
    unique: dict[str, Path] = {}
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"required GIS dataset file not found: {resolved}")
        unique[str(resolved)] = resolved
    return [unique[key] for key in sorted(unique)]


def _copy_snapshot_file(
    source: Path,
    destination: Path,
    *,
    logical_path: str,
    role: str,
    required: bool,
) -> dict[str, object]:
    if not source.is_file():
        if required:
            raise FileNotFoundError(f"required snapshot input not found: {source}")
        return {"role": role, "path": logical_path, "exists": False}
    source_record = _stable_file_record(source, logical_path=logical_path, role=role)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    destination_record = _stable_file_record(destination, logical_path=logical_path, role=role)
    if source_record["sha256"] != destination_record["sha256"]:
        raise RuntimeError(f"snapshot copy hash mismatch: {source}")
    return destination_record


def create_snapshot(
    snapshot_dir: Path,
    *,
    observations_path: Path,
    reference_catalogs_path: Path,
    gis_mappings_path: Path,
    weather_data_dir: Path,
    gis_root: Path,
    gis_hash_cache_path: Path | None = None,
    prefer_weather_parquet: bool = True,
    allow_partitioned_weather_history: bool = True,
    extra_inputs: dict[str, Path] | None = None,
) -> dict[str, Any]:
    target = snapshot_dir.resolve()
    if target.exists():
        raise FileExistsError(f"snapshot target already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.staging-{uuid.uuid4().hex}"
    staging.mkdir()
    try:
        snapshot_files: list[dict[str, object]] = []
        fixed_inputs = (
            (
                "observations",
                observations_path.resolve(),
                "inputs/mushroom-data/mushroom_observations.json",
            ),
            (
                "reference_catalogs",
                reference_catalogs_path.resolve(),
                "inputs/mushroom-data/mushroom_reference_catalogs.json",
            ),
            (
                "gis_mappings",
                gis_mappings_path.resolve(),
                "inputs/mushroom-data/mushroom_gis_mappings.json",
            ),
        )
        for role, source, relative in fixed_inputs:
            snapshot_files.append(
                _copy_snapshot_file(
                    source,
                    staging / relative,
                    logical_path=relative,
                    role=role,
                    required=True,
                )
            )
        for role, source in sorted((extra_inputs or {}).items()):
            role_name = str(role or "").strip()
            if not role_name:
                raise ValueError("extra snapshot input role must not be empty")
            relative = f"inputs/extra/{role_name}"
            _safe_relative_path(relative, label="extra snapshot input")
            snapshot_files.append(
                _copy_snapshot_file(
                    Path(source).resolve(),
                    staging / relative,
                    logical_path=relative,
                    role=f"extra:{role_name}",
                    required=True,
                )
            )
        weather_root = weather_data_dir.resolve()
        weather_history_record: dict[str, object] | None = None
        partitioned_current = weather_root / "weather-history" / "CURRENT.json"
        weather_parquet = weather_root / WEATHER_DAILY_PARQUET_NAME
        if partitioned_current.is_file() and not allow_partitioned_weather_history:
            raise ValueError(
                "Partitioned weather history is active but the target worker does not "
                "advertise partitioned_weather_history_v1."
            )
        if prefer_weather_parquet and partitioned_current.is_file():
            from rainmapper_core.weather_history_dataset import (
                pin_weather_generation,
                write_json_atomic,
            )

            with pin_weather_generation(weather_root) as generation:
                history_files = [
                    ("manifest", generation.manifest_path),
                    ("catalog", generation.object_path(generation.catalog.path)),
                    *[
                        ("partition", generation.object_path(partition.path))
                        for partition in generation.partitions
                    ],
                ]
                for role_suffix, source in history_files:
                    relative_under_history = source.relative_to(generation.root).as_posix()
                    relative = f"inputs/weather/weather-history/{relative_under_history}"
                    snapshot_files.append(
                        _copy_snapshot_file(
                            source,
                            staging / relative,
                            logical_path=relative,
                            role=f"weather-history:{role_suffix}",
                            required=True,
                        )
                    )
                current_relative = "inputs/weather/weather-history/CURRENT.json"
                current_destination = staging / current_relative
                write_json_atomic(
                    current_destination,
                    {
                        "schema_version": "weather_history_current_v1",
                        "generation_id": generation.generation_id,
                        "manifest_path": generation.manifest_path.relative_to(
                            generation.root
                        ).as_posix(),
                        "manifest_sha256": generation.manifest_sha256,
                    },
                )
                snapshot_files.append(
                    _stable_file_record(
                        current_destination,
                        logical_path=current_relative,
                        role="weather-history:current",
                    )
                )
                weather_history_record = {
                    "root": "inputs/weather/weather-history",
                    "generation_id": generation.generation_id,
                    "manifest_sha256": generation.manifest_sha256,
                    "partition_count": len(generation.partitions),
                }
            weather_inputs = ()
        elif prefer_weather_parquet and weather_parquet.is_file():
            weather_inputs = (("daily_parquet", WEATHER_DAILY_PARQUET_NAME, True),)
        else:
            weather_inputs = (
                (source_id, filename, False)
                for source_id, filename in mushroom_observation_context.DAILY_INCREMENTAL_FILES
            )
        for source_id, filename, required in weather_inputs:
            relative = f"inputs/weather/{filename}"
            snapshot_files.append(
                _copy_snapshot_file(
                    weather_root / filename,
                    staging / relative,
                    logical_path=relative,
                    role=f"weather:{source_id}",
                    required=required,
                )
            )

        resolved_gis_root = gis_root.resolve()
        gis_records = gis_file_records(
            resolved_gis_root,
            hash_cache_path=gis_hash_cache_path,
        )
        gis_fingerprint = _fingerprint(gis_records)
        snapshot_fingerprint = _fingerprint(
            [*snapshot_files, {"role": "dataset:mushroom_gis_v0", "path": gis_fingerprint}]
        )
        manifest: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "kind": "mushroom_rebuild_input_manifest",
            "created_at": datetime.now(UTC).isoformat(),
            "snapshot_id": f"sha256:{snapshot_fingerprint}",
            "inputs": {
                "observations": "inputs/mushroom-data/mushroom_observations.json",
                "reference_catalogs": "inputs/mushroom-data/mushroom_reference_catalogs.json",
                "gis_mappings": "inputs/mushroom-data/mushroom_gis_mappings.json",
                "weather_data_dir": "inputs/weather",
            },
            "files": snapshot_files,
            "datasets": [
                {
                    "dataset_id": "mushroom_gis_v0",
                    "storage": "external",
                    "root_path": str(resolved_gis_root),
                    "fingerprint": f"sha256:{gis_fingerprint}",
                    "files": gis_records,
                }
            ],
        }
        if weather_history_record is not None:
            manifest["weather_history"] = weather_history_record
        (staging / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        staging.replace(target)
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def load_manifest(snapshot_dir: Path) -> dict[str, Any]:
    manifest_path = snapshot_dir.resolve() / MANIFEST_NAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"snapshot manifest must contain an object: {manifest_path}")
    if payload.get("kind") != "mushroom_rebuild_input_manifest":
        raise ValueError(f"unexpected snapshot manifest kind: {manifest_path}")
    if payload.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"unsupported snapshot manifest schema: {payload.get('schema_version')}")
    return payload


def resolved_input_paths(snapshot_dir: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    root = snapshot_dir.resolve()
    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("snapshot manifest is missing inputs")
    if set(inputs) != REQUIRED_INPUT_KEYS:
        raise ValueError("snapshot manifest inputs do not match the required contract")
    return {
        key: _resolve_beneath(root, value, label=f"snapshot input {key}")
        for key, value in inputs.items()
    }


def verify_snapshot(
    snapshot_dir: Path,
    *,
    gis_root_override: Path | None = None,
    verify_gis_file_hashes: bool = True,
) -> dict[str, Any]:
    root = snapshot_dir.resolve()
    manifest = load_manifest(root)
    errors: list[str] = []
    verified_files = 0
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        raw_files = []
        errors.append("snapshot manifest files must be a list")
    for raw_record in raw_files:
        if not isinstance(raw_record, dict):
            errors.append("invalid snapshot file record")
            continue
        try:
            path = _resolve_beneath(root, raw_record.get("path"), label="snapshot file")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if raw_record.get("exists", True) is False:
            if path.exists():
                errors.append(f"unexpected snapshot file: {raw_record.get('path')}")
            continue
        if not path.is_file():
            errors.append(f"missing snapshot file: {raw_record.get('path')}")
            continue
        if path.stat().st_size != raw_record.get("size_bytes"):
            errors.append(f"snapshot size mismatch: {raw_record.get('path')}")
            continue
        if sha256_file(path) != raw_record.get("sha256"):
            errors.append(f"snapshot hash mismatch: {raw_record.get('path')}")
            continue
        verified_files += 1

    weather_history = manifest.get("weather_history")
    if weather_history is not None:
        if not isinstance(weather_history, dict):
            errors.append("weather_history must be an object")
        else:
            try:
                history_root = _resolve_beneath(
                    root,
                    weather_history.get("root"),
                    label="snapshot weather history",
                )
                from rainmapper_core.weather_history_dataset import resolve_weather_generation

                generation = resolve_weather_generation(history_root, verify_hashes=True)
                if generation.generation_id != weather_history.get("generation_id"):
                    errors.append("weather history generation identity mismatch")
                if generation.manifest_sha256 != weather_history.get("manifest_sha256"):
                    errors.append("weather history manifest identity mismatch")
                if len(generation.partitions) != weather_history.get("partition_count"):
                    errors.append("weather history partition count mismatch")
            except (OSError, RuntimeError, ValueError) as exc:
                errors.append(f"invalid weather history dataset: {exc}")

    datasets = manifest.get("datasets", [])
    if not isinstance(datasets, list) or len(datasets) != 1 or not isinstance(datasets[0], dict):
        errors.append("manifest must contain one GIS dataset")
        dataset: dict[str, Any] = {}
    else:
        dataset = datasets[0]
    dataset_root = (
        gis_root_override.resolve()
        if gis_root_override is not None
        else Path(str(dataset.get("root_path", ""))).resolve()
    )
    verified_gis_files = 0
    current_gis_records: list[dict[str, object]] = []
    raw_gis_files = dataset.get("files")
    if not isinstance(raw_gis_files, list):
        raw_gis_files = []
        errors.append("GIS dataset files must be a list")
    for raw_record in raw_gis_files:
        if not isinstance(raw_record, dict):
            errors.append("invalid GIS file record")
            continue
        relative = str(raw_record.get("path", ""))
        try:
            path = _resolve_beneath(dataset_root, relative, label="GIS file")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append(f"missing GIS file: {relative}")
            continue
        if verify_gis_file_hashes:
            current = _stable_file_record(path, logical_path=relative, role="gis")
        else:
            current = {
                "role": raw_record.get("role", "gis"),
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": raw_record.get("sha256"),
            }
        current_gis_records.append(current)
        if current.get("size_bytes") != raw_record.get("size_bytes"):
            errors.append(f"GIS size mismatch: {relative}")
            continue
        if current.get("sha256") != raw_record.get("sha256"):
            errors.append(f"GIS hash mismatch: {relative}")
            continue
        verified_gis_files += 1
    current_fingerprint = f"sha256:{_fingerprint(current_gis_records)}"
    if current_fingerprint != dataset.get("fingerprint"):
        errors.append("GIS dataset fingerprint mismatch")
    declared_dataset_fingerprint = str(dataset.get("fingerprint", ""))
    valid_file_records = [record for record in raw_files if isinstance(record, dict)]
    declared_snapshot_fingerprint = f"sha256:{_fingerprint([*valid_file_records, {'role': 'dataset:mushroom_gis_v0', 'path': declared_dataset_fingerprint.removeprefix('sha256:')}])}"
    if declared_snapshot_fingerprint != manifest.get("snapshot_id"):
        errors.append("snapshot manifest fingerprint mismatch")
    return {
        "status": "valid" if not errors else "invalid",
        "snapshot_id": manifest.get("snapshot_id"),
        "verified_snapshot_files": verified_files,
        "verified_gis_files": verified_gis_files,
        "gis_validation": "deep" if verify_gis_file_hashes else "shallow",
        "gis_root": str(dataset_root),
        "errors": errors,
    }


def verify_live_inputs(
    input_manifest: dict[str, Any],
    *,
    observations_path: Path,
    reference_catalogs_path: Path,
    gis_mappings_path: Path,
    weather_data_dir: Path,
    gis_root: Path,
    gis_hash_cache_path: Path | None = None,
    extra_inputs: dict[str, Path] | None = None,
    ignored_extra_inputs: set[str] | frozenset[str] | None = None,
    verify_weather_file_hashes: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Verify that current authoritative inputs still match a frozen manifest."""
    errors: list[str] = []
    current_records: list[dict[str, object]] = []
    fixed_sources = {
        "observations": observations_path.resolve(),
        "reference_catalogs": reference_catalogs_path.resolve(),
        "gis_mappings": gis_mappings_path.resolve(),
    }
    extra_sources = {
        str(role): Path(path).resolve()
        for role, path in (extra_inputs or {}).items()
    }
    ignored_extras = {str(value) for value in (ignored_extra_inputs or set())}
    matching_weather_identity = False
    weather_history = input_manifest.get("weather_history")
    if not verify_weather_file_hashes and isinstance(weather_history, dict):
        try:
            from rainmapper_core.weather_history_dataset import resolve_weather_generation

            generation = resolve_weather_generation(weather_data_dir, verify_hashes=False)
            matching_weather_identity = (
                generation.generation_id == weather_history.get("generation_id")
                and generation.manifest_sha256 == weather_history.get("manifest_sha256")
                and len(generation.partitions) == weather_history.get("partition_count")
            )
        except (OSError, RuntimeError, ValueError):
            matching_weather_identity = False
    files = input_manifest.get("files")
    if not isinstance(files, list):
        return {"status": "invalid", "errors": ["input manifest files must be a list"]}
    progress_datasets = input_manifest.get("datasets")
    progress_gis_files = (
        progress_datasets[0].get("files", [])
        if isinstance(progress_datasets, list)
        and len(progress_datasets) == 1
        and isinstance(progress_datasets[0], dict)
        and isinstance(progress_datasets[0].get("files"), list)
        else []
    )
    progress_total = max(1, len(files) + len(progress_gis_files))
    for index, raw_record in enumerate(files):
        if progress_callback is not None:
            logical_name = str(raw_record.get("path", "")) if isinstance(raw_record, dict) else ""
            progress_callback(index, progress_total, logical_name)
        if not isinstance(raw_record, dict):
            errors.append("invalid live input file record")
            continue
        role = str(raw_record.get("role", ""))
        logical_path = str(raw_record.get("path", ""))
        if role.startswith("extra:") and role.removeprefix("extra:") in ignored_extras:
            current_records.append(dict(raw_record))
            continue
        if role.startswith("weather-history:") and matching_weather_identity:
            current_records.append(dict(raw_record))
            continue
        source = fixed_sources.get(role)
        if source is None and role.startswith("extra:"):
            source = extra_sources.get(role.removeprefix("extra:"))
        if source is None and role.startswith("weather-history:"):
            weather_prefix = PurePosixPath("inputs/weather")
            logical = PurePosixPath(logical_path)
            try:
                relative_weather = logical.relative_to(weather_prefix)
                source = weather_data_dir.resolve().joinpath(*relative_weather.parts)
            except ValueError:
                source = None
        if source is None and role.startswith("weather:"):
            source = weather_data_dir.resolve() / Path(logical_path).name
        if source is None:
            errors.append(f"unknown live input role: {role}")
            continue
        if raw_record.get("exists", True) is False:
            current = {"role": role, "path": logical_path, "exists": False}
            current_records.append(current)
            if source.exists():
                errors.append(f"live input appeared after snapshot: {logical_path}")
            continue
        if not source.is_file():
            errors.append(f"live input is missing: {logical_path}")
            continue
        current = _stable_file_record(source, logical_path=logical_path, role=role)
        current_records.append(current)
        if current.get("size_bytes") != raw_record.get("size_bytes"):
            errors.append(f"live input size mismatch: {logical_path}")
        elif current.get("sha256") != raw_record.get("sha256"):
            errors.append(f"live input hash mismatch: {logical_path}")

    datasets = input_manifest.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 1 or not isinstance(datasets[0], dict):
        errors.append("manifest must contain one GIS dataset")
        dataset: dict[str, Any] = {}
    else:
        dataset = datasets[0]
    current_gis_records: list[dict[str, object]] = []
    fixed_file_count = len(files)
    raw_gis_records = dataset.get("files", [])
    if not isinstance(raw_gis_records, list):
        raw_gis_records = []
        errors.append("GIS dataset files must be a list")
    try:
        live_gis_by_path = {
            str(record.get("path", "")): record
            for record in gis_file_records(
                gis_root,
                hash_cache_path=gis_hash_cache_path,
            )
        }
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        live_gis_by_path = {}
        errors.append(str(exc))
    for index, raw_record in enumerate(raw_gis_records):
        if progress_callback is not None:
            logical_name = str(raw_record.get("path", "")) if isinstance(raw_record, dict) else ""
            progress_callback(fixed_file_count + index, progress_total, logical_name)
        if not isinstance(raw_record, dict):
            errors.append("invalid live GIS file record")
            continue
        relative = str(raw_record.get("path", ""))
        try:
            source = _resolve_beneath(gis_root, relative, label="live GIS file")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not source.is_file():
            errors.append(f"live GIS file is missing: {relative}")
            continue
        current = live_gis_by_path.get(relative)
        if current is None:
            errors.append(f"live GIS file is outside the canonical dataset: {relative}")
            continue
        current_gis_records.append(current)
        if current.get("size_bytes") != raw_record.get("size_bytes"):
            errors.append(f"live GIS size mismatch: {relative}")
        elif current.get("sha256") != raw_record.get("sha256"):
            errors.append(f"live GIS hash mismatch: {relative}")
    current_gis_fingerprint = f"sha256:{_fingerprint(current_gis_records)}"
    if current_gis_fingerprint != dataset.get("fingerprint"):
        errors.append("live GIS dataset fingerprint mismatch")
    current_snapshot_fingerprint = f"sha256:{_fingerprint([*current_records, {'role': 'dataset:mushroom_gis_v0', 'path': current_gis_fingerprint.removeprefix('sha256:')}])}"
    if current_snapshot_fingerprint != input_manifest.get("snapshot_id"):
        errors.append("live input snapshot fingerprint mismatch")
    if progress_callback is not None:
        progress_callback(progress_total, progress_total, "")
    return {
        "status": "valid" if not errors else "stale",
        "snapshot_id": input_manifest.get("snapshot_id"),
        "current_snapshot_id": current_snapshot_fingerprint,
        "dataset_fingerprint": dataset.get("fingerprint"),
        "current_dataset_fingerprint": current_gis_fingerprint,
        "verified_input_files": len(current_records),
        "verified_gis_files": len(current_gis_records),
        "gis_validation": "identity-cache" if gis_hash_cache_path is not None else "deep",
        "errors": errors,
    }


def materialize_ha_test_runtime(
    snapshot_dir: Path,
    runtime_dir: Path,
    *,
    gis_root_override: Path | None = None,
) -> dict[str, object]:
    snapshot_root = snapshot_dir.resolve()
    target = runtime_dir.resolve()
    if target.exists():
        raise FileExistsError(f"HA test runtime target already exists: {target}")
    verification = verify_snapshot(snapshot_root, gis_root_override=gis_root_override)
    if verification["status"] != "valid":
        raise ValueError(f"snapshot verification failed: {verification['errors']}")
    manifest = load_manifest(snapshot_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.staging-{uuid.uuid4().hex}"
    staging.mkdir()
    try:
        share = staging / "share"
        mushroom_data = share / "mushroom-data"
        weather_data = share / "Data"
        mushroom_data.mkdir(parents=True)
        weather_data.mkdir(parents=True)
        paths = resolved_input_paths(snapshot_root, manifest)
        shutil.copy2(paths["observations"], mushroom_data / "mushroom_observations.json")
        shutil.copy2(
            paths["reference_catalogs"],
            mushroom_data / "mushroom_reference_catalogs.json",
        )
        shutil.copy2(paths["gis_mappings"], mushroom_data / "mushroom_gis_mappings.json")
        for _source_id, filename in mushroom_observation_context.DAILY_INCREMENTAL_FILES:
            source = paths["weather_data_dir"] / filename
            if source.is_file():
                shutil.copy2(source, weather_data / filename)
        for raw_record in manifest.get("files", []):
            if not isinstance(raw_record, dict):
                continue
            if not str(raw_record.get("role", "")).startswith("weather-history:"):
                continue
            logical = PurePosixPath(str(raw_record.get("path", "")))
            try:
                relative_weather = logical.relative_to(PurePosixPath("inputs/weather"))
            except ValueError as exc:
                raise ValueError(f"invalid weather history snapshot path: {logical}") from exc
            source = _resolve_beneath(snapshot_root, logical.as_posix(), label="weather history file")
            destination = weather_data.joinpath(*relative_weather.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        shutil.copy2(snapshot_root / MANIFEST_NAME, share / "rebuild_test_input_manifest.json")
        (staging / "tmp").mkdir()
        (staging / "config-www").mkdir()
        marker = {
            "kind": "rainmapper_ha_rebuild_test_runtime",
            "snapshot_id": manifest["snapshot_id"],
            "source_snapshot": str(snapshot_root),
        }
        (staging / ".rainmapper-rebuild-test-runtime.json").write_text(
            json.dumps(marker, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        staging.replace(target)
        return {
            "status": "materialized",
            "runtime_dir": str(target),
            "share_dir": str(target / "share"),
            "snapshot_id": manifest["snapshot_id"],
        }
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
