"""Transactional persistent dataset cache for the portable mushroom worker."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable


SCHEMA_VERSION = "0.1"
CACHE_MANIFEST_KIND = "rainmapper_worker_dataset_cache_manifest"
CACHE_MANIFEST_NAME = "dataset_cache_manifest.json"
DEFAULT_DATASET_ID = "mushroom_gis_v0"
MIN_DATASET_FREE_BYTES = 256 * 1024 * 1024
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_fingerprint(records: list[dict[str, Any]]) -> str:
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
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _safe_relative_path(value: object) -> Path:
    text = str(value)
    logical = PurePosixPath(text)
    if not text or logical.is_absolute() or ".." in logical.parts or "." in logical.parts:
        raise ValueError(f"unsafe dataset relative path: {text!r}")
    if logical.as_posix() != text:
        raise ValueError(f"dataset path must be normalized POSIX: {text!r}")
    return Path(*logical.parts)


def _validated_dataset(input_manifest: dict[str, Any], dataset_id: str) -> dict[str, Any]:
    datasets = input_manifest.get("datasets")
    if not isinstance(datasets, list):
        raise ValueError("input manifest datasets must be a list")
    matches = [row for row in datasets if isinstance(row, dict) and row.get("dataset_id") == dataset_id]
    if len(matches) != 1:
        raise ValueError(f"input manifest must contain exactly one {dataset_id} dataset")
    dataset = matches[0]
    fingerprint = dataset.get("fingerprint")
    if not isinstance(fingerprint, str) or not _FINGERPRINT_RE.fullmatch(fingerprint):
        raise ValueError("dataset fingerprint must be a lowercase sha256 value")
    raw_files = dataset.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("dataset files must be a non-empty list")
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_record in raw_files:
        if not isinstance(raw_record, dict):
            raise ValueError("dataset contains an invalid file record")
        relative = _safe_relative_path(raw_record.get("path"))
        logical_path = relative.as_posix()
        if logical_path in seen:
            raise ValueError(f"duplicate dataset path: {logical_path}")
        seen.add(logical_path)
        size = raw_record.get("size_bytes")
        digest = raw_record.get("sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"invalid size for dataset path: {logical_path}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"invalid sha256 for dataset path: {logical_path}")
        files.append(
            {
                "role": str(raw_record.get("role", "gis")),
                "path": logical_path,
                "size_bytes": size,
                "sha256": digest,
            }
        )
    if _canonical_fingerprint(files) != fingerprint:
        raise ValueError("dataset fingerprint does not match its file records")
    return {
        "dataset_id": dataset_id,
        "fingerprint": fingerprint,
        "files": files,
    }


def dataset_contract(
    input_manifest: dict[str, Any],
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
) -> dict[str, Any]:
    """Return the normalized, fingerprint-verified dataset contract."""
    return _validated_dataset(input_manifest, dataset_id)


def load_input_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input manifest must contain a JSON object")
    if payload.get("kind") != "mushroom_rebuild_input_manifest":
        raise ValueError("unexpected input manifest kind")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported input manifest schema")
    return payload


def _cache_root(worker_data_dir: Path, dataset_id: str) -> Path:
    if dataset_id != DEFAULT_DATASET_ID:
        raise ValueError(f"unsupported worker dataset: {dataset_id}")
    return worker_data_dir.resolve() / "datasets" / dataset_id


def _copy_and_hash(source: Path, destination: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as source_handle, destination.open("xb") as destination_handle:
        source_stream: BinaryIO = source_handle
        destination_stream: BinaryIO = destination_handle
        while chunk := source_stream.read(chunk_size):
            destination_stream.write(chunk)
            digest.update(chunk)
        destination_stream.flush()
        os.fsync(destination_stream.fileno())
    return digest.hexdigest()


def _write_cache_manifest(version_dir: Path, dataset: dict[str, Any]) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": CACHE_MANIFEST_KIND,
        "dataset_id": dataset["dataset_id"],
        "fingerprint": dataset["fingerprint"],
        "files": dataset["files"],
    }
    target = version_dir / CACHE_MANIFEST_NAME
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with target.open("rb") as handle:
        os.fsync(handle.fileno())


def _load_cache_manifest(version_dir: Path) -> dict[str, Any]:
    payload = json.loads((version_dir / CACHE_MANIFEST_NAME).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("cache manifest must contain a JSON object")
    return payload


def verify_version(
    worker_data_dir: Path,
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
    fingerprint: str | None = None,
    deep: bool = False,
) -> dict[str, Any]:
    root = _cache_root(worker_data_dir, dataset_id)
    errors: list[str] = []
    if fingerprint is None:
        current = root / "current"
        if not current.is_symlink():
            errors.append("current dataset version is not active")
            version_dir = root / "versions" / "missing"
            resolved_fingerprint = None
        else:
            link_target = os.readlink(current)
            expected_prefix = "versions/"
            resolved_fingerprint = link_target[len(expected_prefix) :] if link_target.startswith(expected_prefix) else None
            if resolved_fingerprint is None or not _FINGERPRINT_RE.fullmatch(resolved_fingerprint):
                errors.append("current dataset symlink target is invalid")
                version_dir = root / "versions" / "missing"
            else:
                version_dir = root / link_target
    else:
        if not _FINGERPRINT_RE.fullmatch(fingerprint):
            raise ValueError("dataset fingerprint must be a lowercase sha256 value")
        resolved_fingerprint = fingerprint
        version_dir = root / "versions" / fingerprint

    manifest: dict[str, Any] = {}
    if not version_dir.is_dir():
        errors.append("dataset version directory is missing")
    else:
        try:
            manifest = _load_cache_manifest(version_dir)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"cannot load cache manifest: {exc}")
    if manifest:
        if manifest.get("kind") != CACHE_MANIFEST_KIND:
            errors.append("unexpected cache manifest kind")
        if manifest.get("schema_version") != SCHEMA_VERSION:
            errors.append("unsupported cache manifest schema")
        if manifest.get("dataset_id") != dataset_id:
            errors.append("cache manifest dataset ID mismatch")
        if manifest.get("fingerprint") != resolved_fingerprint:
            errors.append("cache manifest fingerprint mismatch")
        try:
            dataset = _validated_dataset(
                {
                    "datasets": [manifest],
                },
                dataset_id,
            )
        except ValueError as exc:
            errors.append(str(exc))
            dataset = {"files": []}
        for record in dataset["files"]:
            relative = _safe_relative_path(record["path"])
            path = version_dir / relative
            if not path.is_file():
                errors.append(f"missing cached dataset file: {record['path']}")
                continue
            if path.stat().st_size != record["size_bytes"]:
                errors.append(f"cached dataset size mismatch: {record['path']}")
                continue
            if deep:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    while chunk := handle.read(4 * 1024 * 1024):
                        digest.update(chunk)
                if digest.hexdigest() != record["sha256"]:
                    errors.append(f"cached dataset hash mismatch: {record['path']}")

    files = manifest.get("files", []) if isinstance(manifest.get("files"), list) else []
    total_bytes = sum(
        row.get("size_bytes", 0)
        for row in files
        if isinstance(row, dict) and isinstance(row.get("size_bytes"), int)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "rainmapper_worker_dataset_cache_verification",
        "status": "valid" if not errors else "invalid",
        "dataset_id": dataset_id,
        "fingerprint": resolved_fingerprint,
        "validation": "deep" if deep else "shallow",
        "file_count": len(files),
        "size_bytes": total_bytes,
        "errors": errors,
    }


def _activate(root: Path, fingerprint: str) -> None:
    temporary = root / f".current-{uuid.uuid4().hex}.tmp"
    try:
        temporary.symlink_to(Path("versions") / fingerprint)
        temporary.replace(root / "current")
    finally:
        temporary.unlink(missing_ok=True)


def sync_local(
    input_manifest: dict[str, Any],
    source_root: Path,
    worker_data_dir: Path,
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
) -> dict[str, Any]:
    _validated_dataset(input_manifest, dataset_id)
    source_base = source_root.resolve()

    def fetch_file(record: dict[str, Any], destination: Path) -> tuple[int, str]:
        relative = _safe_relative_path(record["path"])
        source = (source_base / relative).resolve()
        try:
            source.relative_to(source_base)
        except ValueError as exc:
            raise ValueError(f"dataset source escapes its root: {record['path']}") from exc
        if not source.is_file():
            raise FileNotFoundError(f"required dataset source is missing: {record['path']}")
        before = source.stat()
        if before.st_size != record["size_bytes"]:
            raise RuntimeError(f"dataset source size mismatch: {record['path']}")
        digest = _copy_and_hash(source, destination)
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError(f"dataset source changed while copying: {record['path']}")
        return after.st_size, digest

    return sync_from_fetcher(
        input_manifest,
        worker_data_dir,
        fetch_file=fetch_file,
        dataset_id=dataset_id,
    )


def sync_from_fetcher(
    input_manifest: dict[str, Any],
    worker_data_dir: Path,
    *,
    fetch_file: Callable[[dict[str, Any], Path], tuple[int, str]],
    dataset_id: str = DEFAULT_DATASET_ID,
) -> dict[str, Any]:
    """Fetch a missing dataset version directly into transactional staging."""
    dataset = _validated_dataset(input_manifest, dataset_id)
    root = _cache_root(worker_data_dir, dataset_id)
    versions = root / "versions"
    staging_root = root / "staging"
    versions.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    fingerprint = dataset["fingerprint"]
    version_dir = versions / fingerprint

    if version_dir.exists():
        verification = verify_version(
            worker_data_dir,
            dataset_id=dataset_id,
            fingerprint=fingerprint,
            deep=False,
        )
        if verification["status"] != "valid":
            raise RuntimeError("existing dataset version failed shallow validation")
        _activate(root, fingerprint)
        return {
            **verification,
            "status": "reused",
            "transferred_file_count": 0,
            "transferred_size_bytes": 0,
        }

    required_bytes = sum(int(record["size_bytes"]) for record in dataset["files"])
    free_bytes = shutil.disk_usage(root).free
    if free_bytes < required_bytes + MIN_DATASET_FREE_BYTES:
        raise RuntimeError(
            "insufficient free space for dataset staging: "
            f"required={required_bytes + MIN_DATASET_FREE_BYTES}, available={free_bytes}"
        )

    staging = staging_root / f"{fingerprint}.{uuid.uuid4().hex}"
    staging.mkdir()
    transferred_files = 0
    transferred_bytes = 0
    try:
        for record in dataset["files"]:
            relative = _safe_relative_path(record["path"])
            size, digest = fetch_file(record, staging / relative)
            if size != record["size_bytes"]:
                raise RuntimeError(f"dataset source size mismatch: {record['path']}")
            if digest != record["sha256"]:
                raise RuntimeError(f"dataset source hash mismatch: {record['path']}")
            transferred_files += 1
            transferred_bytes += size
        _write_cache_manifest(staging, dataset)
        staging.replace(version_dir)
        verification = verify_version(
            worker_data_dir,
            dataset_id=dataset_id,
            fingerprint=fingerprint,
            deep=False,
        )
        if verification["status"] != "valid":
            raise RuntimeError("new dataset version failed shallow validation")
        _activate(root, fingerprint)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        **verification,
        "status": "synchronized",
        "transferred_file_count": transferred_files,
        "transferred_size_bytes": transferred_bytes,
    }


def resolve_current(
    worker_data_dir: Path,
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
) -> dict[str, Any]:
    verification = verify_version(worker_data_dir, dataset_id=dataset_id, deep=False)
    if verification["status"] != "valid":
        raise RuntimeError("current dataset cache is not valid")
    root = _cache_root(worker_data_dir, dataset_id)
    return {
        **verification,
        "path": str((root / "current").resolve()),
    }
