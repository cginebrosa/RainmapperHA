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
from typing import Any

from rainmapper_core import mushroom_gis_lab, mushroom_observation_context


SCHEMA_VERSION = "0.1"
MANIFEST_NAME = "input_manifest.json"
GIS_HASH_CACHE_SCHEMA_VERSION = "0.1"
GIS_HASH_CACHE_KIND = "rainmapper_gis_hash_cache"
REQUIRED_INPUT_KEYS = {
    "observations",
    "reference_catalogs",
    "gis_mappings",
    "weather_data_dir",
}


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
        for source_id, filename in mushroom_observation_context.DAILY_INCREMENTAL_FILES:
            relative = f"inputs/weather/{filename}"
            snapshot_files.append(
                _copy_snapshot_file(
                    weather_data_dir.resolve() / filename,
                    staging / relative,
                    logical_path=relative,
                    role=f"weather:{source_id}",
                    required=False,
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
    if payload.get("schema_version") != SCHEMA_VERSION:
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
) -> dict[str, Any]:
    """Verify that current authoritative inputs still match a frozen manifest."""
    errors: list[str] = []
    current_records: list[dict[str, object]] = []
    fixed_sources = {
        "observations": observations_path.resolve(),
        "reference_catalogs": reference_catalogs_path.resolve(),
        "gis_mappings": gis_mappings_path.resolve(),
    }
    files = input_manifest.get("files")
    if not isinstance(files, list):
        return {"status": "invalid", "errors": ["input manifest files must be a list"]}
    for raw_record in files:
        if not isinstance(raw_record, dict):
            errors.append("invalid live input file record")
            continue
        role = str(raw_record.get("role", ""))
        logical_path = str(raw_record.get("path", ""))
        source = fixed_sources.get(role)
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
    for raw_record in dataset.get("files", []):
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
        current = _stable_file_record(source, logical_path=relative, role="gis")
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
    return {
        "status": "valid" if not errors else "stale",
        "snapshot_id": input_manifest.get("snapshot_id"),
        "current_snapshot_id": current_snapshot_fingerprint,
        "dataset_fingerprint": dataset.get("fingerprint"),
        "current_dataset_fingerprint": current_gis_fingerprint,
        "verified_input_files": len(current_records),
        "verified_gis_files": len(current_gis_records),
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
