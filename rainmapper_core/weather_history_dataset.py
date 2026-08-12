"""Versioned, partitioned readers for the canonical daily weather history."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Iterator, Sequence
from uuid import uuid4

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from rainmapper_core.weather_history_contract import (
    CATALOG_COLUMNS,
    CURRENT_SCHEMA_VERSION,
    DATA_SCHEMA_VERSION,
    KNOWN_SOURCES,
    MANIFEST_SCHEMA_VERSION,
    WEATHER_HISTORY_COLUMNS,
    WEATHER_HISTORY_SCHEMA,
)


HISTORY_DIRECTORY = "weather-history"
class WeatherHistoryDatasetError(RuntimeError):
    """Base error for an invalid or unreadable weather-history generation."""


class WeatherHistoryManifestError(WeatherHistoryDatasetError):
    """Raised when CURRENT or its immutable manifest violates the contract."""


class WeatherHistoryIntegrityError(WeatherHistoryDatasetError):
    """Raised when a referenced immutable object does not match its metadata."""


@dataclass(frozen=True)
class WeatherPartition:
    source: str
    year: int
    path: str
    sha256: str
    size_bytes: int
    rows: int
    min_local_date: str
    max_local_date: str


@dataclass(frozen=True)
class WeatherCatalog:
    path: str
    sha256: str
    size_bytes: int
    rows: int


@dataclass(frozen=True)
class WeatherGeneration:
    root: Path
    generation_id: str
    manifest_path: Path
    manifest_sha256: str
    previous_generation_id: str | None
    created_at: str
    partitions: tuple[WeatherPartition, ...]
    catalog: WeatherCatalog

    @property
    def cache_identity(self) -> tuple[str, str]:
        return self.generation_id, self.manifest_sha256

    def object_path(self, relative_path: str) -> Path:
        return _contained_path(self.root, relative_path)


def weather_history_root(data_dir: Path) -> Path:
    """Return the dataset root whether called with Data/ or weather-history/."""
    path = Path(data_dir)
    return path if path.name == HISTORY_DIRECTORY else path / HISTORY_DIRECTORY


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_json_atomic(path: Path, payload: object) -> None:
    """Write canonical JSON beside the destination and atomically replace it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _load_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WeatherHistoryManifestError(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WeatherHistoryManifestError(f"{label} must be a JSON object: {path}")
    return payload


def _required_text(payload: dict[str, object], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WeatherHistoryManifestError(f"{label}.{key} must be non-empty text")
    return value.strip()


def _required_int(payload: dict[str, object], key: str, label: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WeatherHistoryManifestError(f"{label}.{key} must be a non-negative integer")
    return value


def _validate_sha256(value: str, label: str) -> str:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise WeatherHistoryManifestError(f"{label} must be a lowercase SHA-256")
    return value


def _contained_path(root: Path, relative_path: str) -> Path:
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise WeatherHistoryManifestError(f"Unsafe weather-history path: {relative_path!r}")
    root_resolved = root.resolve()
    candidate = root.joinpath(*pure.parts).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise WeatherHistoryManifestError(
            f"Weather-history path escapes dataset root: {relative_path!r}"
        ) from exc
    return candidate


def _parse_partition(payload: object, index: int) -> WeatherPartition:
    label = f"manifest.partitions[{index}]"
    if not isinstance(payload, dict):
        raise WeatherHistoryManifestError(f"{label} must be an object")
    source = _required_text(payload, "source", label)
    if source not in KNOWN_SOURCES:
        raise WeatherHistoryManifestError(f"Unknown weather source {source!r}")
    year = _required_int(payload, "year", label)
    if year < 1900 or year > 2200:
        raise WeatherHistoryManifestError(f"Invalid partition year {year}")
    minimum = _required_text(payload, "min_local_date", label)
    maximum = _required_text(payload, "max_local_date", label)
    for name, value in (("min_local_date", minimum), ("max_local_date", maximum)):
        if len(value) != 8 or not value.isdigit() or int(value[:4]) != year:
            raise WeatherHistoryManifestError(f"{label}.{name} is outside declared year")
    if minimum > maximum:
        raise WeatherHistoryManifestError(f"{label} has an inverted date range")
    return WeatherPartition(
        source=source,
        year=year,
        path=_required_text(payload, "path", label),
        sha256=_validate_sha256(_required_text(payload, "sha256", label), f"{label}.sha256"),
        size_bytes=_required_int(payload, "size_bytes", label),
        rows=_required_int(payload, "rows", label),
        min_local_date=minimum,
        max_local_date=maximum,
    )


def _parse_catalog(payload: object) -> WeatherCatalog:
    label = "manifest.catalog"
    if not isinstance(payload, dict):
        raise WeatherHistoryManifestError(f"{label} must be an object")
    return WeatherCatalog(
        path=_required_text(payload, "path", label),
        sha256=_validate_sha256(_required_text(payload, "sha256", label), f"{label}.sha256"),
        size_bytes=_required_int(payload, "size_bytes", label),
        rows=_required_int(payload, "rows", label),
    )


def resolve_weather_generation(
    data_dir: Path,
    *,
    verify_hashes: bool = False,
) -> WeatherGeneration:
    """Resolve and validate one immutable generation without changing CURRENT."""
    root = weather_history_root(Path(data_dir))
    current_path = root / "CURRENT.json"
    current = _load_json_object(current_path, "CURRENT")
    if current.get("schema_version") != CURRENT_SCHEMA_VERSION:
        raise WeatherHistoryManifestError("Unsupported CURRENT schema_version")
    generation_id = _required_text(current, "generation_id", "CURRENT")
    manifest_relative = _required_text(current, "manifest_path", "CURRENT")
    manifest_sha = _validate_sha256(
        _required_text(current, "manifest_sha256", "CURRENT"),
        "CURRENT.manifest_sha256",
    )
    manifest_path = _contained_path(root, manifest_relative)
    if not manifest_path.is_file():
        raise WeatherHistoryIntegrityError(f"Missing weather manifest: {manifest_path}")
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != manifest_sha:
        raise WeatherHistoryIntegrityError(
            f"Manifest SHA mismatch: expected {manifest_sha}, got {actual_manifest_sha}"
        )
    return resolve_weather_manifest(
        root,
        manifest_path,
        expected_generation_id=generation_id,
        expected_sha256=manifest_sha,
        verify_hashes=verify_hashes,
    )


def resolve_weather_manifest(
    data_dir: Path,
    manifest_path: Path,
    *,
    expected_generation_id: str | None = None,
    expected_sha256: str | None = None,
    verify_hashes: bool = False,
) -> WeatherGeneration:
    """Validate one explicit manifest without consulting or changing CURRENT."""
    root = weather_history_root(Path(data_dir))
    manifest_path = Path(manifest_path)
    try:
        manifest_path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise WeatherHistoryManifestError(
            f"Weather manifest escapes dataset root: {manifest_path}"
        ) from exc
    if not manifest_path.is_file():
        raise WeatherHistoryIntegrityError(f"Missing weather manifest: {manifest_path}")
    manifest_sha = sha256_file(manifest_path)
    if expected_sha256 is not None and manifest_sha != expected_sha256:
        raise WeatherHistoryIntegrityError(
            f"Manifest SHA mismatch: expected {expected_sha256}, got {manifest_sha}"
        )
    manifest = _load_json_object(manifest_path, "manifest")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise WeatherHistoryManifestError("Unsupported manifest schema_version")
    if manifest.get("data_schema_version") != DATA_SCHEMA_VERSION:
        raise WeatherHistoryManifestError("Unsupported weather data schema_version")
    generation_id = _required_text(manifest, "generation_id", "manifest")
    if expected_generation_id is not None and generation_id != expected_generation_id:
        raise WeatherHistoryManifestError("CURRENT and manifest generation_id differ")
    if manifest.get("key") != ["source", "station_code", "local_date"]:
        raise WeatherHistoryManifestError("Unsupported canonical weather key")
    created_at = _required_text(manifest, "created_at", "manifest")
    previous = manifest.get("previous_generation_id")
    if previous is not None and (not isinstance(previous, str) or not previous.strip()):
        raise WeatherHistoryManifestError("manifest.previous_generation_id is invalid")
    raw_partitions = manifest.get("partitions")
    if not isinstance(raw_partitions, list) or not raw_partitions:
        raise WeatherHistoryManifestError("manifest.partitions must be a non-empty list")
    partitions = tuple(_parse_partition(value, index) for index, value in enumerate(raw_partitions))
    identities = [(partition.source, partition.year) for partition in partitions]
    if identities != sorted(identities) or len(identities) != len(set(identities)):
        raise WeatherHistoryManifestError("Partitions must be unique and sorted by source/year")
    catalog = _parse_catalog(manifest.get("catalog"))
    totals = manifest.get("totals")
    if not isinstance(totals, dict):
        raise WeatherHistoryManifestError("manifest.totals must be an object")
    if _required_int(totals, "rows", "manifest.totals") != sum(p.rows for p in partitions):
        raise WeatherHistoryManifestError("manifest total row count does not match partitions")
    expected_bytes = sum(p.size_bytes for p in partitions) + catalog.size_bytes
    if _required_int(totals, "size_bytes", "manifest.totals") != expected_bytes:
        raise WeatherHistoryManifestError("manifest total size does not match its objects")

    generation = WeatherGeneration(
        root=root,
        generation_id=generation_id,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha,
        previous_generation_id=previous.strip() if isinstance(previous, str) else None,
        created_at=created_at,
        partitions=partitions,
        catalog=catalog,
    )
    validate_weather_generation(generation, verify_hashes=verify_hashes)
    return generation


def validate_weather_generation(
    generation: WeatherGeneration,
    *,
    verify_hashes: bool = True,
) -> None:
    """Validate files, sizes, Parquet metadata and optionally every object hash."""
    for partition in generation.partitions:
        path = generation.object_path(partition.path)
        _validate_object(path, partition.size_bytes, partition.sha256, verify_hashes)
        parquet = pq.ParquetFile(path)
        if parquet.schema_arrow != WEATHER_HISTORY_SCHEMA:
            raise WeatherHistoryIntegrityError(f"Unexpected weather schema: {path}")
        if parquet.metadata.num_rows != partition.rows:
            raise WeatherHistoryIntegrityError(f"Weather row count mismatch: {path}")
        date_index = parquet.schema_arrow.get_field_index("local_date")
        minimums: list[str] = []
        maximums: list[str] = []
        for row_group in range(parquet.metadata.num_row_groups):
            statistics = parquet.metadata.row_group(row_group).column(date_index).statistics
            if statistics is None or not statistics.has_min_max:
                raise WeatherHistoryIntegrityError(
                    f"Missing local_date statistics in weather partition: {path}"
                )
            minimums.append(str(statistics.min))
            maximums.append(str(statistics.max))
        if minimums and (min(minimums), max(maximums)) != (
            partition.min_local_date,
            partition.max_local_date,
        ):
            raise WeatherHistoryIntegrityError(f"Weather date range mismatch: {path}")
    catalog_path = generation.object_path(generation.catalog.path)
    _validate_object(
        catalog_path,
        generation.catalog.size_bytes,
        generation.catalog.sha256,
        verify_hashes,
    )
    catalog_file = pq.ParquetFile(catalog_path)
    if catalog_file.schema_arrow.names != list(CATALOG_COLUMNS):
        raise WeatherHistoryIntegrityError(f"Unexpected station catalog schema: {catalog_path}")
    if catalog_file.metadata.num_rows != generation.catalog.rows:
        raise WeatherHistoryIntegrityError(f"Station catalog row count mismatch: {catalog_path}")


def _validate_object(path: Path, size_bytes: int, expected_sha: str, verify_hash: bool) -> None:
    if not path.is_file():
        raise WeatherHistoryIntegrityError(f"Missing weather-history object: {path}")
    if path.stat().st_size != size_bytes:
        raise WeatherHistoryIntegrityError(f"Weather-history size mismatch: {path}")
    if verify_hash and sha256_file(path) != expected_sha:
        raise WeatherHistoryIntegrityError(f"Weather-history SHA mismatch: {path}")


@contextmanager
def pin_weather_generation(
    data_dir: Path,
    generation_id: str | None = None,
    *,
    lease_seconds: int = 3600,
) -> Iterator[WeatherGeneration]:
    """Pin a generation for a bounded reader and expose a cleanup-safe lease."""
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    root = weather_history_root(Path(data_dir))
    lock_path = root / "locks" / "writer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lease_path: Path | None = None
    with lock_path.open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_SH)
        try:
            generation = resolve_weather_generation(root)
            if generation_id is not None and generation.generation_id != generation_id:
                raise WeatherHistoryManifestError(
                    f"Requested generation {generation_id!r} is not CURRENT"
                )
            lease_id = uuid4().hex
            lease_path = root / "leases" / generation.generation_id / f"{lease_id}.json"
            now = datetime.now(UTC)
            write_json_atomic(
                lease_path,
                {
                    "schema_version": "weather_history_lease_v1",
                    "generation_id": generation.generation_id,
                    "lease_id": lease_id,
                    "pid": os.getpid(),
                    "created_at": now.isoformat(),
                    "expires_at": datetime.fromtimestamp(
                        now.timestamp() + lease_seconds,
                        tz=UTC,
                    ).isoformat(),
                },
            )
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    try:
        yield generation
    finally:
        if lease_path is not None:
            lease_path.unlink(missing_ok=True)


def _selected_partitions(
    generation: WeatherGeneration,
    sources: set[str] | None,
    start_date: str | None,
    end_date: str | None,
) -> list[WeatherPartition]:
    years: set[int] | None = None
    if start_date is not None or end_date is not None:
        first = int((start_date or "19000101")[:4])
        last = int((end_date or "22001231")[:4])
        years = set(range(first, last + 1))
    return [
        partition
        for partition in generation.partitions
        if (sources is None or partition.source in sources)
        and (years is None or partition.year in years)
        and (start_date is None or partition.max_local_date >= start_date)
        and (end_date is None or partition.min_local_date <= end_date)
    ]


def _validate_read_request(
    columns: Sequence[str] | None,
    sources: set[str] | None,
    station_filter: set[tuple[str, str]] | None,
    start_date: str | None,
    end_date: str | None,
    *,
    allow_unbounded: bool = False,
) -> list[str]:
    selected_columns = list(columns or WEATHER_HISTORY_COLUMNS)
    unknown = set(selected_columns).difference(WEATHER_HISTORY_COLUMNS)
    if unknown:
        raise ValueError(f"Unknown weather columns: {sorted(unknown)}")
    if len(selected_columns) != len(set(selected_columns)):
        raise ValueError("Weather columns must be unique")
    if sources is not None:
        unknown_sources = sources.difference(KNOWN_SOURCES)
        if unknown_sources:
            raise ValueError(f"Unknown weather sources: {sorted(unknown_sources)}")
    if station_filter is not None:
        invalid = {source for source, station in station_filter if source not in KNOWN_SOURCES or not station}
        if invalid:
            raise ValueError("Invalid station_filter")
    for label, value in (("start_date", start_date), ("end_date", end_date)):
        if value is not None and (len(value) != 8 or not value.isdigit()):
            raise ValueError(f"{label} must be YYYYMMDD")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must not be after end_date")
    if (
        not allow_unbounded
        and sources is None
        and station_filter is None
        and start_date is None
        and end_date is None
    ):
        raise ValueError("Unbounded reads must use iter_weather_history explicitly")
    return selected_columns


def iter_weather_history(
    data_dir: Path,
    *,
    columns: Sequence[str] | None = None,
    sources: set[str] | None = None,
    station_filter: set[tuple[str, str]] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    batch_size: int = 16_384,
    allow_unbounded: bool = True,
) -> Iterator[pa.RecordBatch]:
    """Yield filtered canonical rows while holding one immutable generation."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    selected_columns = _validate_read_request(
        columns,
        sources,
        station_filter,
        start_date,
        end_date,
        allow_unbounded=allow_unbounded,
    )
    required_columns = list(selected_columns)
    for column in ("source", "station_code", "local_date"):
        if column not in required_columns:
            required_columns.append(column)
    with pin_weather_generation(data_dir) as generation:
        partitions = _selected_partitions(generation, sources, start_date, end_date)
        station_codes_by_source: dict[str, set[str]] = {}
        if station_filter is not None:
            for source, station_code in station_filter:
                station_codes_by_source.setdefault(source, set()).add(station_code)
        for partition in partitions:
            if station_filter is not None and partition.source not in station_codes_by_source:
                continue
            parquet = pq.ParquetFile(generation.object_path(partition.path))
            for batch in parquet.iter_batches(batch_size=batch_size, columns=required_columns):
                mask: pa.Array | None = None
                if start_date is not None:
                    mask = pc.greater_equal(batch.column("local_date"), start_date)
                if end_date is not None:
                    condition = pc.less_equal(batch.column("local_date"), end_date)
                    mask = condition if mask is None else pc.and_(mask, condition)
                if station_filter is not None:
                    allowed = pa.array(sorted(station_codes_by_source[partition.source]))
                    condition = pc.is_in(batch.column("station_code"), value_set=allowed)
                    mask = condition if mask is None else pc.and_(mask, condition)
                filtered = batch if mask is None else batch.filter(mask)
                if filtered.num_rows:
                    yield filtered.select(selected_columns)


def read_weather_history(
    data_dir: Path,
    *,
    columns: Sequence[str] | None = None,
    sources: set[str] | None = None,
    station_filter: set[tuple[str, str]] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> "pd.DataFrame":
    """Read a bounded subset of one coherent weather-history generation."""
    import pandas as pd
    selected_columns = _validate_read_request(
        columns, sources, station_filter, start_date, end_date
    )
    batches = list(
        iter_weather_history(
            data_dir,
            columns=selected_columns,
            sources=sources,
            station_filter=station_filter,
            start_date=start_date,
            end_date=end_date,
            allow_unbounded=False,
        )
    )
    if not batches:
        return pd.DataFrame(columns=selected_columns)
    return pa.Table.from_batches(batches).to_pandas()
