"""Immutable input bundle transport between Rainmapper and an external worker."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from rainmapper_core import mushroom_rebuild_contracts
from rainmapper_core import mushroom_rebuild_snapshot
from rainmapper_core import mushroom_performance_telemetry
from rainmapper_core import mushroom_worker_dataset_cache


SCHEMA_VERSION = "0.1"
JOB_SPEC_LOGICAL_PATH = "job_spec.json"
SNAPSHOT_PREFIX = "snapshot"
INPUT_MANIFEST_LOGICAL_PATH = f"{SNAPSHOT_PREFIX}/{mushroom_rebuild_snapshot.MANIFEST_NAME}"
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_INPUT_FILE_BYTES = 2 * 1024 * 1024 * 1024
MAX_BUNDLE_BYTES = 4 * 1024 * 1024 * 1024
MAX_DATASET_FILE_BYTES = 8 * 1024 * 1024 * 1024
MAX_DATASET_BYTES = 16 * 1024 * 1024 * 1024
DATASET_PROGRESS_BYTES = 64 * 1024 * 1024
_JOB_ID_RE = re.compile(r"^worker_job_[a-zA-Z0-9_-]{8,80}$")
_STAGING_DIR_RE = re.compile(
    r"^\.worker_job_[a-zA-Z0-9_-]{8,80}\.staging-[0-9a-f]{32}$"
)
DEFAULT_STAGING_GRACE_SECONDS = 60 * 60
DEFAULT_ORPHAN_GRACE_SECONDS = 24 * 60 * 60
WEATHER_INPUT_CACHE_DIR = "weather-input-cache/objects"
IMMUTABLE_INPUT_CACHE_DIR = "immutable-input-cache/objects"
IMMUTABLE_RECEIPT_VERSION = "1.0"
MAX_IMMUTABLE_INPUT_CACHE_BYTES = 1024 * 1024 * 1024
MAX_WEATHER_INPUT_CACHE_BYTES = 512 * 1024 * 1024


def safe_relative_path(value: object) -> Path:
    text = str(value or "")
    logical = PurePosixPath(text)
    if not text or logical.is_absolute() or "." in logical.parts or ".." in logical.parts:
        raise ValueError(f"unsafe worker input path: {text!r}")
    if logical.as_posix() != text:
        raise ValueError(f"worker input path must be normalized POSIX: {text!r}")
    return Path(*logical.parts)


def validate_job_id(job_id: str) -> str:
    resolved = str(job_id or "").strip()
    if not _JOB_ID_RE.fullmatch(resolved):
        raise ValueError("Worker transport job ID is invalid.")
    return resolved


def _bundle_metadata(job_spec: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    existing_files = [
        row
        for row in manifest.get("files", [])
        if isinstance(row, dict) and row.get("exists", True) is not False
    ]
    input_size = sum(
        int(row.get("size_bytes", 0) or 0)
        for row in existing_files
        if isinstance(row.get("size_bytes"), int)
    )
    dataset = mushroom_worker_dataset_cache.dataset_contract(manifest)
    if manifest.get("weather_history") or any(
        str(row.get("role", "")).startswith("weather-history:")
        for row in existing_files
    ):
        weather_transport = "partitioned_v1"
    elif any(row.get("role") == "weather:daily_parquet" for row in existing_files):
        weather_transport = "parquet"
    else:
        weather_transport = "csv"
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "rainmapper_worker_input_bundle",
        "job_id": job_spec.get("job_id"),
        "job_spec_id": job_spec.get("job_spec_id"),
        "snapshot_id": manifest.get("snapshot_id"),
        "input_file_count": len(existing_files),
        "input_size_bytes": input_size,
        "weather_transport": weather_transport,
        "dataset_id": dataset["dataset_id"],
        "dataset_fingerprint": dataset["fingerprint"],
        "dataset_file_count": len(dataset["files"]),
        "dataset_size_bytes": sum(int(row["size_bytes"]) for row in dataset["files"]),
    }


def prepare_coordinator_bundle(
    bundle_root: Path,
    *,
    job_id: str,
    observations_path: Path,
    reference_catalogs_path: Path,
    gis_mappings_path: Path,
    weather_data_dir: Path,
    gis_root: Path,
    reconstruction_scope: str = "all",
    selected_observation_ids: list[str] | tuple[str, ...] | None = None,
    pending_species_ids: list[str] | tuple[str, ...] | None = None,
    prefer_weather_parquet: bool = True,
    allow_partitioned_weather_history: bool = True,
    extra_inputs: dict[str, Path] | None = None,
    source_snapshot_dir: Path | None = None,
) -> dict[str, Any]:
    """Create one immutable coordinator-side bundle without changing live inputs."""
    resolved_job_id = validate_job_id(job_id)
    root = bundle_root.resolve()
    destination = root / resolved_job_id
    if destination.exists():
        raise FileExistsError(f"worker input bundle already exists: {destination}")
    root.mkdir(parents=True, exist_ok=True)
    staging = root / f".{resolved_job_id}.staging-{uuid.uuid4().hex}"
    staging.mkdir()
    try:
        snapshot_dir = staging / SNAPSHOT_PREFIX
        if source_snapshot_dir is None:
            manifest = mushroom_rebuild_snapshot.create_snapshot(
                snapshot_dir,
                observations_path=observations_path,
                reference_catalogs_path=reference_catalogs_path,
                gis_mappings_path=gis_mappings_path,
                weather_data_dir=weather_data_dir,
                gis_root=gis_root,
                gis_hash_cache_path=root / ".gis-hash-cache.json",
                prefer_weather_parquet=prefer_weather_parquet,
                allow_partitioned_weather_history=allow_partitioned_weather_history,
                extra_inputs=extra_inputs,
            )
        else:
            manifest = mushroom_rebuild_snapshot.derive_snapshot(
                snapshot_dir,
                source_snapshot_dir=source_snapshot_dir,
                extra_inputs=extra_inputs,
            )
        job_spec = mushroom_rebuild_contracts.create_job_spec(
            snapshot_dir,
            reconstruction_scope=reconstruction_scope,
            selected_observation_ids=selected_observation_ids,
            pending_species_ids=pending_species_ids,
            job_id=resolved_job_id,
        )
        mushroom_rebuild_contracts.write_manifest(staging / JOB_SPEC_LOGICAL_PATH, job_spec)
        staging.replace(destination)
        return _bundle_metadata(job_spec, manifest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def load_coordinator_bundle(bundle_root: Path, job_id: str) -> dict[str, Any]:
    root = bundle_root.resolve()
    bundle = root / validate_job_id(job_id)
    job_spec = mushroom_rebuild_contracts.load_job_spec(bundle / JOB_SPEC_LOGICAL_PATH)
    manifest = mushroom_rebuild_snapshot.load_manifest(bundle / SNAPSHOT_PREFIX)
    if str(job_spec.get("job_id", "")) != job_id:
        raise ValueError("worker input bundle job ID mismatch")
    return _bundle_metadata(job_spec, manifest)


def discard_coordinator_bundle(bundle_root: Path, job_id: str) -> bool:
    """Remove one identity-checked immutable coordinator bundle."""
    root = bundle_root.resolve()
    bundle = root / validate_job_id(job_id)
    if not bundle.is_dir():
        return False
    if bundle.is_symlink():
        raise ValueError("Refusing to discard a symlinked worker bundle.")
    try:
        spec = json.loads((bundle / JOB_SPEC_LOGICAL_PATH).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError("Refusing to discard a worker bundle without a valid job spec.") from exc
    if not isinstance(spec, dict) or spec.get("job_id") != job_id:
        raise ValueError("Refusing to discard a worker bundle with a different job identity.")
    shutil.rmtree(bundle)
    return True


def discard_unqueued_bundle(bundle_root: Path, job_id: str) -> None:
    """Roll back only a bundle created for a job that was not queued."""
    discard_coordinator_bundle(bundle_root, job_id)


def coordinator_bundle_is_discardable(job: dict[str, Any]) -> bool:
    """Return whether a job no longer needs its immutable input bundle."""
    status = str(job.get("status", ""))
    if status in {"failed", "cancelled"}:
        return True
    if status != "complete":
        return False
    if str(job.get("job_type", "")) in {
        "worker_snapshot_transport_probe",
        "worker_ml_multiversion_v1",
    }:
        return True
    return str(job.get("promotion_status", "")) == "promoted"


def cleanup_coordinator_bundles(
    bundle_root: Path,
    jobs: list[dict[str, Any]],
    *,
    now: float | None = None,
    staging_grace_seconds: int = DEFAULT_STAGING_GRACE_SECONDS,
    orphan_grace_seconds: int = DEFAULT_ORPHAN_GRACE_SECONDS,
    apply: bool = True,
) -> dict[str, object]:
    """Reconcile private input copies without touching active or undecided jobs."""
    root = bundle_root.resolve()
    report: dict[str, object] = {
        "mode": "apply" if apply else "dry-run",
        "planned_terminal": [],
        "planned_orphan": [],
        "planned_staging": [],
        "discarded_terminal": [],
        "discarded_orphan": [],
        "discarded_staging": [],
        "retained": [],
        "errors": [],
    }
    if not root.exists():
        return report
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Worker input bundle root must be a real directory.")
    timestamp = time.time() if now is None else float(now)
    jobs_by_id = {
        str(job.get("job_id", "")): job
        for job in jobs
        if isinstance(job, dict) and _JOB_ID_RE.fullmatch(str(job.get("job_id", "")))
    }
    for child in root.iterdir():
        name = child.name
        if child.is_symlink():
            cast_errors = report["errors"]
            assert isinstance(cast_errors, list)
            cast_errors.append(f"refused symlink: {name}")
            continue
        age_seconds = max(0.0, timestamp - child.stat().st_mtime)
        try:
            if _STAGING_DIR_RE.fullmatch(name):
                if child.is_dir() and age_seconds >= max(0, staging_grace_seconds):
                    planned_staging = report["planned_staging"]
                    assert isinstance(planned_staging, list)
                    planned_staging.append(name)
                    if apply:
                        shutil.rmtree(child)
                        cast_staging = report["discarded_staging"]
                        assert isinstance(cast_staging, list)
                        cast_staging.append(name)
                continue
            if not child.is_dir() or not _JOB_ID_RE.fullmatch(name):
                continue
            job = jobs_by_id.get(name)
            if job is not None and coordinator_bundle_is_discardable(job):
                planned_terminal = report["planned_terminal"]
                assert isinstance(planned_terminal, list)
                planned_terminal.append(name)
                if apply:
                    discard_coordinator_bundle(root, name)
                    cast_terminal = report["discarded_terminal"]
                    assert isinstance(cast_terminal, list)
                    cast_terminal.append(name)
            elif job is None and age_seconds >= max(0, orphan_grace_seconds):
                planned_orphan = report["planned_orphan"]
                assert isinstance(planned_orphan, list)
                planned_orphan.append(name)
                if apply:
                    discard_coordinator_bundle(root, name)
                    cast_orphan = report["discarded_orphan"]
                    assert isinstance(cast_orphan, list)
                    cast_orphan.append(name)
            else:
                cast_retained = report["retained"]
                assert isinstance(cast_retained, list)
                cast_retained.append(name)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            cast_errors = report["errors"]
            assert isinstance(cast_errors, list)
            cast_errors.append(f"{name}: {exc}")
    return report


def discard_worker_job(worker_data_dir: Path, job_id: str) -> bool:
    """Remove one completed worker job without touching the shared dataset cache."""
    resolved_job_id = validate_job_id(job_id)
    jobs_root = worker_data_dir.resolve() / "jobs"
    job_dir = jobs_root / resolved_job_id
    if not job_dir.exists():
        return False
    if not job_dir.is_dir():
        raise ValueError("Worker job path is not a directory.")
    if job_dir.is_symlink():
        raise ValueError("Refusing to discard a symlinked worker job.")
    try:
        spec = json.loads((job_dir / JOB_SPEC_LOGICAL_PATH).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError("Refusing to discard a worker job without a valid job spec.") from exc
    if not isinstance(spec, dict) or spec.get("job_id") != resolved_job_id:
        raise ValueError("Refusing to discard a worker job with a different identity.")
    shutil.rmtree(job_dir)
    return True


def allowed_bundle_paths(bundle_root: Path, job_id: str) -> dict[str, Path]:
    root = bundle_root.resolve()
    bundle = root / validate_job_id(job_id)
    manifest = mushroom_rebuild_snapshot.load_manifest(bundle / SNAPSHOT_PREFIX)
    allowed = {
        JOB_SPEC_LOGICAL_PATH: bundle / JOB_SPEC_LOGICAL_PATH,
        INPUT_MANIFEST_LOGICAL_PATH: bundle / INPUT_MANIFEST_LOGICAL_PATH,
    }
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("worker input manifest files must be a list")
    for raw_record in files:
        if not isinstance(raw_record, dict):
            raise ValueError("worker input manifest contains an invalid file record")
        relative = safe_relative_path(raw_record.get("path"))
        if raw_record.get("exists", True) is False:
            continue
        logical = f"{SNAPSHOT_PREFIX}/{relative.as_posix()}"
        allowed[logical] = bundle / SNAPSHOT_PREFIX / relative
    for logical, path in allowed.items():
        resolved = path.resolve()
        try:
            resolved.relative_to(bundle.resolve())
        except ValueError as exc:
            raise ValueError(f"worker input path escapes its bundle: {logical}") from exc
        if not resolved.is_file():
            raise FileNotFoundError(f"worker input file is missing: {logical}")
        allowed[logical] = resolved
    return allowed


def resolve_coordinator_file(bundle_root: Path, job_id: str, logical_path: str) -> Path:
    normalized = safe_relative_path(logical_path).as_posix()
    allowed = allowed_bundle_paths(bundle_root, job_id)
    if normalized not in allowed:
        raise ValueError("worker input file is not part of the immutable bundle")
    return allowed[normalized]


def resolve_coordinator_dataset_file(
    bundle_root: Path,
    gis_root: Path,
    *,
    job_id: str,
    dataset_id: str,
    fingerprint: str,
    logical_path: str,
) -> Path:
    """Resolve one GIS file declared by an immutable job manifest."""
    bundle = bundle_root.resolve() / validate_job_id(job_id)
    manifest = mushroom_rebuild_snapshot.load_manifest(bundle / SNAPSHOT_PREFIX)
    dataset = mushroom_worker_dataset_cache.dataset_contract(
        manifest,
        dataset_id=str(dataset_id or ""),
    )
    if dataset["fingerprint"] != str(fingerprint or ""):
        raise ValueError("Worker dataset fingerprint does not match the immutable job manifest.")
    normalized = safe_relative_path(logical_path).as_posix()
    matches = [record for record in dataset["files"] if record["path"] == normalized]
    if len(matches) != 1:
        raise ValueError("Worker dataset file is not declared by the immutable job manifest.")
    root = gis_root.resolve()
    path = (root / Path(*PurePosixPath(normalized).parts)).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Worker dataset file escapes the authoritative GIS root.") from exc
    if not path.is_file():
        raise FileNotFoundError("Worker dataset source file is missing.")
    if path.stat().st_size != matches[0]["size_bytes"]:
        raise RuntimeError("Worker dataset source size changed after the job was frozen.")
    return path


def request_headers(worker_id: str, claim_token: str, token: str) -> dict[str, str]:
    headers = {
        "Accept": "application/octet-stream",
        "X-Rainmapper-Worker": worker_id,
        "X-Rainmapper-Claim": claim_token,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _download_file(
    url: str,
    destination: Path,
    *,
    headers: dict[str, str],
    expected_size: int | None,
    expected_sha256: str | None,
    max_bytes: int,
    timeout: float,
    progress_callback: Callable[[int], None] | None = None,
) -> tuple[int, str]:
    request = Request(url, headers=headers, method="GET")
    mushroom_performance_telemetry.add(requests=1)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    total = 0
    with urlopen(request, timeout=timeout) as response, destination.open("xb") as output:
        advertised = response.headers.get("Content-Length")
        if advertised:
            try:
                advertised_size = int(advertised)
            except ValueError as exc:
                raise ValueError("Rainmapper returned an invalid input Content-Length.") from exc
            if advertised_size > max_bytes:
                raise ValueError("Rainmapper input file exceeds the worker safety limit.")
            if expected_size is not None and advertised_size != expected_size:
                raise ValueError("Rainmapper input Content-Length does not match its manifest.")
        source: BinaryIO = response
        while chunk := source.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("Rainmapper input file exceeds the worker safety limit.")
            output.write(chunk)
            digest.update(chunk)
            if progress_callback is not None:
                progress_callback(total)
        output.flush()
        os.fsync(output.fileno())
    resolved_digest = digest.hexdigest()
    if expected_size is not None and total != expected_size:
        raise ValueError("Downloaded worker input size does not match its manifest.")
    if expected_sha256 is not None and resolved_digest != expected_sha256:
        raise ValueError("Downloaded worker input hash does not match its manifest.")
    mushroom_performance_telemetry.add(
        files_written=1,
        bytes_read=total,
        bytes_written=total,
        hashes=1,
        hash_bytes=total,
        fsyncs=1,
    )
    return total, resolved_digest


def _materialize_cached_weather_input(
    url: str,
    destination: Path,
    *,
    worker_data_dir: Path,
    digest: str,
    size: int,
    headers: dict[str, str],
    timeout: float,
) -> bool:
    """Materialize one immutable weather object; return True on cache reuse."""
    cache_root = worker_data_dir.resolve() / WEATHER_INPUT_CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    cached = cache_root / digest
    valid = _sealed_immutable_object(cached, digest, size)
    if not valid:
        cached.unlink(missing_ok=True)
        temporary = cache_root / f".{digest}.{uuid.uuid4().hex}.tmp"
        try:
            _download_file(
                url,
                temporary,
                headers=headers,
                expected_size=size,
                expected_sha256=digest,
                max_bytes=MAX_INPUT_FILE_BYTES,
                timeout=timeout,
            )
            os.replace(temporary, cached)
            _write_immutable_receipt(cached, digest, size)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        os.utime(cached, None)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(cached, destination)
    except OSError:
        shutil.copy2(cached, destination)
        mushroom_performance_telemetry.add(
            copies=1,
            copy_bytes=size,
            files_read=1,
            bytes_read=size,
            files_written=1,
            bytes_written=size,
        )
    return valid


def _immutable_receipt_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.verified.json")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_immutable_receipt(path: Path, digest: str, size: int) -> None:
    receipt = _immutable_receipt_path(path)
    temporary = receipt.with_name(f".{receipt.name}.{uuid.uuid4().hex}.tmp")
    payload = {
        "schema_version": IMMUTABLE_RECEIPT_VERSION,
        "sha256": digest,
        "size_bytes": size,
    }
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, receipt)
        _fsync_directory(receipt.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _sealed_immutable_object(path: Path, digest: str, size: int) -> bool:
    if not path.is_file() or path.stat().st_size != size:
        return False
    expected = {
        "schema_version": IMMUTABLE_RECEIPT_VERSION,
        "sha256": digest,
        "size_bytes": size,
    }
    try:
        receipt = json.loads(
            _immutable_receipt_path(path).read_text(encoding="utf-8")
        )
    except (OSError, ValueError, json.JSONDecodeError):
        receipt = None
    if receipt == expected:
        return True
    if mushroom_rebuild_snapshot.sha256_file(path) != digest:
        return False
    _write_immutable_receipt(path, digest, size)
    return True


def _materialize_cached_immutable_input(
    url: str,
    destination: Path,
    *,
    worker_data_dir: Path,
    digest: str,
    size: int,
    headers: dict[str, str],
    timeout: float,
) -> bool:
    """Link one sealed object into a job, downloading it only when absent."""
    cache_root = worker_data_dir.resolve() / IMMUTABLE_INPUT_CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    cached = cache_root / digest
    valid = _sealed_immutable_object(cached, digest, size)
    if not valid:
        temporary = cache_root / f".{digest}.{uuid.uuid4().hex}.tmp"
        try:
            _download_file(
                url,
                temporary,
                headers=headers,
                expected_size=size,
                expected_sha256=digest,
                max_bytes=MAX_INPUT_FILE_BYTES,
                timeout=timeout,
            )
            os.replace(temporary, cached)
            _fsync_directory(cache_root)
            _write_immutable_receipt(cached, digest, size)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        os.utime(cached, None)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(cached, destination)
    except OSError:
        shutil.copy2(cached, destination)
        mushroom_performance_telemetry.add(
            copies=1,
            copy_bytes=size,
            files_read=1,
            bytes_read=size,
            files_written=1,
            bytes_written=size,
        )
    return valid


def _prune_immutable_input_cache(
    worker_data_dir: Path, protected: set[str]
) -> int:
    cache_root = worker_data_dir.resolve() / IMMUTABLE_INPUT_CACHE_DIR
    if not cache_root.is_dir():
        return 0
    entries = [
        path
        for path in cache_root.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and not path.name.endswith(".verified.json")
    ]
    total = sum(path.stat().st_size for path in entries)
    removed = 0
    for path in sorted(entries, key=lambda candidate: candidate.stat().st_mtime_ns):
        if total <= MAX_IMMUTABLE_INPUT_CACHE_BYTES:
            break
        if path.name in protected:
            continue
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        _immutable_receipt_path(path).unlink(missing_ok=True)
        total -= size
        removed += size
    return removed


def _prune_weather_input_cache(worker_data_dir: Path, protected: set[str]) -> int:
    cache_root = worker_data_dir.resolve() / WEATHER_INPUT_CACHE_DIR
    if not cache_root.is_dir():
        return 0
    entries = [
        path
        for path in cache_root.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and not path.name.endswith(".verified.json")
    ]
    total = sum(path.stat().st_size for path in entries)
    removed = 0
    for path in sorted(entries, key=lambda candidate: candidate.stat().st_mtime_ns):
        if total <= MAX_WEATHER_INPUT_CACHE_BYTES:
            break
        if path.name in protected:
            continue
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        _immutable_receipt_path(path).unlink(missing_ok=True)
        total -= size
        removed += size
    return removed


def _sync_required_dataset(
    ha_url: str,
    job: dict[str, Any],
    input_manifest: dict[str, Any],
    worker_data_dir: Path,
    *,
    worker_id: str,
    claim_token: str,
    token: str,
    timeout: float,
    progress_callback: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any]:
    input_bundle = job.get("input_bundle")
    if not isinstance(input_bundle, dict):
        raise ValueError("Worker job does not contain an input bundle contract.")
    dataset = mushroom_worker_dataset_cache.dataset_contract(input_manifest)
    total_bytes = sum(int(record["size_bytes"]) for record in dataset["files"])
    if total_bytes > MAX_DATASET_BYTES:
        raise ValueError("Worker GIS dataset exceeds the safety limit.")
    expected_fingerprint = str(input_bundle.get("dataset_fingerprint", "") or "")
    if expected_fingerprint and expected_fingerprint != dataset["fingerprint"]:
        raise ValueError("Worker GIS dataset fingerprint does not match the assigned job.")
    endpoint = str(input_bundle.get("dataset_endpoint", "") or "")
    headers = request_headers(worker_id, claim_token, token)
    transferred_before = 0

    def fetch_file(record: dict[str, Any], destination: Path) -> tuple[int, str]:
        nonlocal transferred_before
        if endpoint != "/api/mushrooms/workers/jobs/dataset":
            raise ValueError("Worker GIS dataset endpoint is invalid.")
        size = int(record["size_bytes"])
        if size > MAX_DATASET_FILE_BYTES:
            raise ValueError(f"Worker GIS dataset file exceeds the safety limit: {record['path']}")
        query = urlencode(
            {
                "job_id": validate_job_id(str(job.get("job_id", ""))),
                "dataset_id": dataset["dataset_id"],
                "fingerprint": dataset["fingerprint"],
                "file": record["path"],
            }
        )
        last_reported = 0

        def report_file_progress(file_bytes: int) -> None:
            nonlocal last_reported
            if progress_callback is None:
                return
            if file_bytes != size and file_bytes - last_reported < DATASET_PROGRESS_BYTES:
                return
            last_reported = file_bytes
            completed = transferred_before + file_bytes
            progress_callback(
                {
                    "phase": "Synchronizing GIS dataset",
                    "message": (
                        f"Downloaded {completed}/{total_bytes} GIS byte(s); "
                        f"file {record['path']}."
                    ),
                    "overall_percent": 10 + int((completed / total_bytes) * 35) if total_bytes else 45,
                }
            )

        result = _download_file(
            ha_url.rstrip("/") + endpoint + "?" + query,
            destination,
            headers=headers,
            expected_size=size,
            expected_sha256=str(record["sha256"]),
            max_bytes=MAX_DATASET_FILE_BYTES,
            timeout=timeout,
            progress_callback=report_file_progress,
        )
        transferred_before += result[0]
        return result

    result = mushroom_worker_dataset_cache.sync_from_fetcher(
        input_manifest,
        worker_data_dir,
        fetch_file=fetch_file,
        dataset_id=dataset["dataset_id"],
    )
    if progress_callback is not None:
        progress_callback(
            {
                "phase": "GIS dataset ready",
                "message": (
                    "Required GIS dataset reused from persistent cache."
                    if result["status"] == "reused"
                    else "Required GIS dataset downloaded, verified and activated."
                ),
                "overall_percent": 45,
            }
        )
    return result


def _load_downloaded_json(path: Path, label: str) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    mushroom_performance_telemetry.add(
        files_read=1,
        bytes_read=len(content.encode("utf-8")),
    )
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError(f"downloaded {label} must contain a JSON object")
    return payload


def download_input_bundle(
    ha_url: str,
    job: dict[str, Any],
    worker_data_dir: Path,
    *,
    worker_id: str,
    claim_token: str,
    token: str = "",
    timeout: float = 30.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Download, verify and persist the immutable inputs for a claimed job."""
    job_id = validate_job_id(str(job.get("job_id", "")))
    input_bundle = job.get("input_bundle")
    if not isinstance(input_bundle, dict):
        raise ValueError("Worker job does not contain an input bundle contract.")
    endpoint = str(input_bundle.get("endpoint", "") or "")
    if not endpoint.startswith("/api/mushrooms/workers/jobs/input"):
        raise ValueError("Worker job input endpoint is invalid.")
    jobs_root = worker_data_dir.resolve() / "jobs"
    destination = jobs_root / job_id
    if destination.exists():
        snapshot_dir = destination / SNAPSHOT_PREFIX
        job_spec = mushroom_rebuild_contracts.load_job_spec(destination / JOB_SPEC_LOGICAL_PATH)
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot_dir)
        dataset_sync = _sync_required_dataset(
            ha_url,
            job,
            manifest,
            worker_data_dir,
            worker_id=worker_id,
            claim_token=claim_token,
            token=token,
            timeout=timeout,
            progress_callback=progress_callback,
        )
        dataset = mushroom_worker_dataset_cache.resolve_current(worker_data_dir)
        verification = mushroom_rebuild_contracts.verify_job_spec(
            job_spec,
            snapshot_dir,
            gis_root_override=Path(str(dataset["path"])),
            verify_gis_file_hashes=False,
        )
        if verification["status"] != "valid":
            raise RuntimeError("Existing worker input bundle is invalid.")
        return {
            **verification,
            "status": "reused",
            "input_dir": str(destination),
            "input_file_count": input_bundle.get("input_file_count"),
            "input_size_bytes": input_bundle.get("input_size_bytes"),
            "dataset_fingerprint": dataset.get("fingerprint"),
            "dataset_cache_status": dataset_sync.get("status"),
            "dataset_transferred_size_bytes": dataset_sync.get("transferred_size_bytes", 0),
            "weather_cache_reused_size_bytes": 0,
        }

    jobs_root.mkdir(parents=True, exist_ok=True)
    staging = jobs_root / f".{job_id}.staging-{uuid.uuid4().hex}"
    staging.mkdir()
    headers = request_headers(worker_id, claim_token, token)

    def file_url(logical_path: str) -> str:
        query = urlencode({"job_id": job_id, "file": logical_path})
        separator = "?" if "?" not in endpoint else "&"
        return ha_url.rstrip("/") + endpoint + separator + query

    try:
        _download_file(
            file_url(JOB_SPEC_LOGICAL_PATH),
            staging / JOB_SPEC_LOGICAL_PATH,
            headers=headers,
            expected_size=None,
            expected_sha256=None,
            max_bytes=MAX_JSON_BYTES,
            timeout=timeout,
        )
        _download_file(
            file_url(INPUT_MANIFEST_LOGICAL_PATH),
            staging / INPUT_MANIFEST_LOGICAL_PATH,
            headers=headers,
            expected_size=None,
            expected_sha256=None,
            max_bytes=MAX_JSON_BYTES,
            timeout=timeout,
        )
        job_spec = _load_downloaded_json(staging / JOB_SPEC_LOGICAL_PATH, "job spec")
        manifest = _load_downloaded_json(staging / INPUT_MANIFEST_LOGICAL_PATH, "input manifest")
        if job_spec.get("job_id") != job_id:
            raise ValueError("Downloaded job spec belongs to a different job.")
        if job_spec.get("job_spec_id") != input_bundle.get("job_spec_id"):
            raise ValueError("Downloaded job spec identity does not match the claim.")
        if manifest.get("snapshot_id") != input_bundle.get("snapshot_id"):
            raise ValueError("Downloaded snapshot identity does not match the claim.")
        files = manifest.get("files")
        if not isinstance(files, list):
            raise ValueError("Downloaded input manifest files must be a list.")
        records = [row for row in files if isinstance(row, dict) and row.get("exists", True) is not False]
        if len(records) != int(input_bundle.get("input_file_count", -1)):
            raise ValueError("Downloaded input manifest file count does not match the claim.")
        total_bytes = sum(int(row.get("size_bytes", 0) or 0) for row in records)
        if total_bytes != int(input_bundle.get("input_size_bytes", -1)) or total_bytes > MAX_BUNDLE_BYTES:
            raise ValueError("Downloaded input manifest size does not match the claim or safety limit.")

        dataset_requirements = job_spec.get("dataset_requirements")
        if not isinstance(dataset_requirements, list) or len(dataset_requirements) != 1:
            raise ValueError("Job spec must require exactly one cached GIS dataset.")
        requirement = dataset_requirements[0]
        if not isinstance(requirement, dict):
            raise ValueError("Job spec GIS dataset requirement is invalid.")
        manifest_dataset = mushroom_worker_dataset_cache.dataset_contract(
            manifest,
            dataset_id=str(requirement.get("dataset_id", "")),
        )
        if manifest_dataset["fingerprint"] != str(requirement.get("fingerprint", "")):
            raise ValueError("Job spec GIS requirement does not match its input manifest.")
        dataset_sync = _sync_required_dataset(
            ha_url,
            job,
            manifest,
            worker_data_dir,
            worker_id=worker_id,
            claim_token=claim_token,
            token=token,
            timeout=timeout,
            progress_callback=progress_callback,
        )
        cache = mushroom_worker_dataset_cache.verify_version(
            worker_data_dir,
            dataset_id=manifest_dataset["dataset_id"],
            fingerprint=manifest_dataset["fingerprint"],
            deep=False,
        )
        if cache["status"] != "valid":
            raise RuntimeError("Required GIS dataset did not pass cache validation.")

        transferred = 0
        reused_weather_bytes = 0
        reused_immutable_bytes = 0
        processed = 0
        protected_weather_digests: set[str] = set()
        protected_immutable_digests: set[str] = set()
        for index, raw_record in enumerate(records, start=1):
            relative = safe_relative_path(raw_record.get("path"))
            size = raw_record.get("size_bytes")
            digest = raw_record.get("sha256")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > MAX_INPUT_FILE_BYTES:
                raise ValueError(f"Invalid worker input size: {relative.as_posix()}")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"Invalid worker input hash: {relative.as_posix()}")
            role = str(raw_record.get("role", "") or "")
            if role.startswith("weather-history:"):
                protected_weather_digests.add(digest)
                reused = _materialize_cached_weather_input(
                    file_url(f"{SNAPSHOT_PREFIX}/{relative.as_posix()}"),
                    staging / SNAPSHOT_PREFIX / relative,
                    worker_data_dir=worker_data_dir,
                    digest=digest,
                    size=size,
                    headers=headers,
                    timeout=timeout,
                )
                if reused:
                    reused_weather_bytes += size
                else:
                    transferred += size
            else:
                protected_immutable_digests.add(digest)
                reused = _materialize_cached_immutable_input(
                    file_url(f"{SNAPSHOT_PREFIX}/{relative.as_posix()}"),
                    staging / SNAPSHOT_PREFIX / relative,
                    worker_data_dir=worker_data_dir,
                    digest=digest,
                    size=size,
                    headers=headers,
                    timeout=timeout,
                )
                if reused:
                    reused_immutable_bytes += size
                else:
                    transferred += size
            processed += size
            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": (
                            "Reusing sealed local inputs"
                            if reused
                            else "Downloading missing inputs"
                        ),
                        "message": (
                            f"Materialized input file {index}/{len(records)} "
                            f"from {'local cache' if reused else 'HA'}."
                        ),
                        "overall_percent": 50 + int((processed / total_bytes) * 40) if total_bytes else 90,
                    }
                )

        dataset = mushroom_worker_dataset_cache.resolve_current(worker_data_dir)
        verification = mushroom_rebuild_contracts.verify_job_spec(
            job_spec,
            staging / SNAPSHOT_PREFIX,
            gis_root_override=Path(str(dataset["path"])),
            verify_snapshot_files=False,
            verify_gis_file_hashes=False,
        )
        if verification["status"] != "valid":
            raise RuntimeError(f"Downloaded worker input bundle is invalid: {verification['errors']}")
        staging.replace(destination)
        pruned_weather_bytes = _prune_weather_input_cache(
            worker_data_dir, protected_weather_digests
        )
        pruned_immutable_bytes = _prune_immutable_input_cache(
            worker_data_dir, protected_immutable_digests
        )
        return {
            **verification,
            "status": "verified",
            "input_dir": str(destination),
            "input_file_count": len(records),
            "input_size_bytes": total_bytes,
            "dataset_fingerprint": cache.get("fingerprint"),
            "dataset_cache_status": dataset_sync.get("status"),
            "dataset_transferred_size_bytes": dataset_sync.get("transferred_size_bytes", 0),
            "input_transferred_size_bytes": transferred,
            "weather_cache_reused_size_bytes": reused_weather_bytes,
            "weather_cache_pruned_size_bytes": pruned_weather_bytes,
            "immutable_cache_reused_size_bytes": reused_immutable_bytes,
            "immutable_cache_pruned_size_bytes": pruned_immutable_bytes,
        }
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def download_ml_train_inputs(
    ha_url: str,
    job: dict[str, Any],
    worker_data_dir: Path,
    *,
    worker_id: str,
    claim_token: str,
    token: str,
    timeout: float = 60.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Download the three input files for a ml_train_v0 job (job_spec, features, known_sites)."""
    job_id = validate_job_id(str(job.get("job_id", "")))
    input_bundle = job.get("input_bundle") or {}
    endpoint = str(input_bundle.get("endpoint", "") or "")
    if endpoint != "/api/mushrooms/workers/jobs/input":
        raise ValueError("Worker ML training input endpoint is invalid.")
    destination = worker_data_dir / job_id
    if destination.is_dir():
        return {"status": "reused", "input_dir": str(destination)}
    staging = worker_data_dir / f".ml.{job_id}.staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        headers = request_headers(worker_id, claim_token, token)
        logical_paths = ["job_spec.json", "features.json", "known_sites.json"]
        contracts = {
            "job_spec.json": (
                str(input_bundle.get("job_spec_id", "")).removeprefix("sha256:"),
                input_bundle.get("job_spec_size_bytes"),
            ),
            "features.json": (
                str(input_bundle.get("features_digest", "")).removeprefix("sha256:"),
                input_bundle.get("features_size_bytes"),
            ),
            "known_sites.json": (
                str(input_bundle.get("known_sites_digest", "")).removeprefix("sha256:"),
                input_bundle.get("known_sites_size_bytes"),
            ),
        }
        total_bytes = 0
        transferred_bytes = 0
        reused_bytes = 0
        protected_digests: set[str] = set()
        for idx, logical_path in enumerate(logical_paths):
            query = urlencode({"job_id": job_id, "file": logical_path})
            url = ha_url.rstrip("/") + endpoint + "?" + query
            dest_path = staging / logical_path
            digest, raw_size = contracts[logical_path]
            if not re.fullmatch(r"[0-9a-f]{64}", digest) or not isinstance(
                raw_size, int
            ):
                raise ValueError("Worker ML training input contract is incomplete.")
            size = int(raw_size)
            protected_digests.add(digest)
            reused = _materialize_cached_immutable_input(
                url,
                dest_path,
                worker_data_dir=worker_data_dir,
                digest=digest,
                size=size,
                headers=headers,
                timeout=timeout,
            )
            total_bytes += size
            if reused:
                reused_bytes += size
            else:
                transferred_bytes += size
            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": (
                            "Reusing sealed local inputs"
                            if reused
                            else "Downloading missing inputs"
                        ),
                        "message": (
                            f"Materialized {logical_path} ({idx + 1}/{len(logical_paths)}) "
                            f"from {'local cache' if reused else 'HA'}."
                        ),
                        "overall_percent": 5 + int((idx + 1) / len(logical_paths) * 10),
                    }
                )
        staging.replace(destination)
        pruned_bytes = _prune_immutable_input_cache(
            worker_data_dir, protected_digests
        )
        return {
            "status": "verified",
            "input_dir": str(destination),
            "input_size_bytes": total_bytes,
            "input_transferred_size_bytes": transferred_bytes,
            "immutable_cache_reused_size_bytes": reused_bytes,
            "immutable_cache_pruned_size_bytes": pruned_bytes,
        }
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def download_ml_multiversion_inputs(
    ha_url: str,
    job: dict[str, Any],
    worker_data_dir: Path,
    *,
    worker_id: str,
    claim_token: str,
    token: str,
    timeout: float = 120.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Download and verify the exact files declared by a multiversion job."""
    job_id = validate_job_id(str(job.get("job_id", "")))
    bundle = job.get("input_bundle")
    if not isinstance(bundle, dict):
        raise ValueError("Worker multiversion input bundle is missing.")
    endpoint = str(bundle.get("endpoint", "") or "")
    files = bundle.get("files")
    if endpoint != "/api/mushrooms/workers/jobs/input" or not isinstance(files, list) or not files:
        raise ValueError("Worker multiversion input contract is invalid.")
    records: list[dict[str, Any]] = []
    total_expected = 0
    for raw in files:
        if not isinstance(raw, dict):
            raise ValueError("Worker multiversion input file declaration is invalid.")
        logical_path = safe_relative_path(str(raw.get("path", ""))).as_posix()
        size = int(raw.get("size_bytes", -1))
        digest = str(raw.get("sha256", ""))
        if size < 0 or size > MAX_INPUT_FILE_BYTES or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Worker multiversion input metadata is invalid: {logical_path}")
        records.append({"path": logical_path, "size_bytes": size, "sha256": digest})
        total_expected += size
    destination = worker_data_dir / job_id
    if destination.is_dir():
        return {"status": "reused", "input_dir": str(destination)}
    staging = worker_data_dir / f".multiversion.{job_id}.staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    transferred = 0
    try:
        headers = request_headers(worker_id, claim_token, token)
        for index, record in enumerate(records, start=1):
            query = urlencode({"job_id": job_id, "file": record["path"]})
            size, _ = _download_file(
                ha_url.rstrip("/") + endpoint + "?" + query,
                staging / record["path"],
                headers=headers,
                expected_size=record["size_bytes"],
                expected_sha256=record["sha256"],
                max_bytes=MAX_INPUT_FILE_BYTES,
                timeout=timeout,
            )
            transferred += size
            if progress_callback is not None:
                progress_callback(
                    {
                        "phase": "Downloading V2--V6 inputs",
                        "message": f"Downloaded {record['path']} ({index}/{len(records)}).",
                        "overall_percent": 5 + int(index / len(records) * 10),
                    }
                )
        if transferred != total_expected:
            raise ValueError("Worker multiversion input bundle size is inconsistent.")
        staging.replace(destination)
        return {
            "status": "verified",
            "input_dir": str(destination),
            "input_file_count": len(records),
            "input_size_bytes": transferred,
        }
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
