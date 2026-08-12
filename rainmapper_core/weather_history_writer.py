"""Bounded transactional writer for immutable partitioned weather history."""

from __future__ import annotations

import fcntl
import json
import math
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from rainmapper_core.weather_history_contract import (
    CATALOG_COLUMNS,
    CATALOG_SCHEMA,
    CURRENT_SCHEMA_VERSION,
    DATA_SCHEMA_VERSION,
    DEFAULT_ROW_GROUP_SIZE,
    MANIFEST_SCHEMA_VERSION,
    WEATHER_HISTORY_COLUMNS,
    WEATHER_HISTORY_FLOAT_COLUMNS,
    WEATHER_HISTORY_SCHEMA,
    weather_key,
)
from rainmapper_core.weather_history_dataset import (
    WeatherGeneration,
    WeatherPartition,
    canonical_json_bytes,
    resolve_weather_generation,
    resolve_weather_manifest,
    sha256_file,
    weather_history_root,
    write_json_atomic,
)
from rainmapper_core.weather_history_pending import (
    PendingBatch,
    acknowledge_pending_batch,
    list_pending_batches,
)


@dataclass(frozen=True)
class PartitionMergeReport:
    source: str
    year: int
    old_rows: int
    update_rows: int
    matched_rows: int
    inserted_rows: int
    changed_rows: int
    output_rows: int
    reused: bool
    output_bytes: int
    row_groups: int


@dataclass(frozen=True)
class ArchiveReport:
    generation_id: str
    previous_generation_id: str
    batch_ids: tuple[str, ...]
    already_applied_batch_ids: tuple[str, ...]
    partitions: tuple[PartitionMergeReport, ...]
    catalog_changed: bool
    committed: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["partitions"] = [asdict(value) for value in self.partitions]
        return payload


@dataclass(frozen=True)
class RestoreRepairReport:
    selected_generation_id: str
    selected_manifest_path: str
    valid_generation_ids: tuple[str, ...]
    rejected_manifests: tuple[tuple[str, str], ...]
    applied: bool


@dataclass(frozen=True)
class GenerationPruneReport:
    kept_generation_ids: tuple[str, ...]
    removed_generation_ids: tuple[str, ...]
    active_lease_generation_ids: tuple[str, ...]
    expired_leases_removed: int
    manifests_removed: int
    objects_removed: int
    bytes_removed: int


class WeatherHistoryWriterError(RuntimeError):
    """Base error for a rejected or failed transactional archive."""


class WeatherHistoryWriterBusy(WeatherHistoryWriterError):
    """Raised when another writer owns the dataset lock past the timeout."""


class WeatherHistoryCoordinateConflict(WeatherHistoryWriterError):
    """Raised when fresh station metadata jumps beyond the audited threshold."""


class InjectedWeatherHistoryFailure(WeatherHistoryWriterError):
    """Used by tests to stop a transaction at a precise durability boundary."""


class _FilteredPendingCursor:
    def __init__(self, batches: Sequence[PendingBatch], year: int, batch_size: int) -> None:
        self._files = iter(batches)
        self._year = year
        self._batch_size = batch_size
        self._iterator: Iterator[pa.RecordBatch] | None = None
        self._rows: list[dict[str, Any]] = []
        self._index = 0

    def next(self) -> dict[str, Any] | None:
        while True:
            while self._index < len(self._rows):
                row = self._rows[self._index]
                self._index += 1
                if int(str(row["local_date"])[:4]) == self._year:
                    return row
            if self._iterator is not None:
                try:
                    self._rows = next(self._iterator).to_pylist()
                    self._index = 0
                    continue
                except StopIteration:
                    self._iterator = None
            try:
                pending = next(self._files)
            except StopIteration:
                return None
            self._iterator = iter(
                pq.ParquetFile(pending.data_path).iter_batches(
                    batch_size=self._batch_size,
                    columns=WEATHER_HISTORY_COLUMNS,
                )
            )


class _BoundedTableWriter:
    def __init__(self, path: Path, row_group_size: int, fragment_limit: int = 128) -> None:
        self._writer = pq.ParquetWriter(
            path,
            WEATHER_HISTORY_SCHEMA,
            compression="snappy",
            use_dictionary=True,
        )
        self._row_group_size = row_group_size
        self._fragment_limit = fragment_limit
        self._fragments: list[pa.Table] = []
        self._rows = 0

    def append_table(self, value: pa.Table | pa.RecordBatch) -> None:
        if value.num_rows == 0:
            return
        table = value if isinstance(value, pa.Table) else pa.Table.from_batches([value])
        self._fragments.append(table)
        self._rows += table.num_rows
        if self._rows >= self._row_group_size or len(self._fragments) >= self._fragment_limit:
            self.flush()

    def append_row(self, row: Mapping[str, Any]) -> None:
        self.append_table(
            pa.Table.from_pylist(
                [{column: row.get(column) for column in WEATHER_HISTORY_COLUMNS}],
                schema=WEATHER_HISTORY_SCHEMA,
            )
        )

    def flush(self) -> None:
        if not self._fragments:
            return
        table = pa.concat_tables(self._fragments)
        self._writer.write_table(table, row_group_size=self._row_group_size)
        self._fragments.clear()
        self._rows = 0

    def close(self) -> None:
        self.flush()
        self._writer.close()


def _merge_non_null(older: Mapping[str, Any], newer: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(older)
    for column in WEATHER_HISTORY_COLUMNS:
        value = newer.get(column)
        if value is not None:
            merged[column] = value
    return merged


def _rows_differ(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    return any(first.get(column) != second.get(column) for column in WEATHER_HISTORY_COLUMNS)


def _fail_if_requested(fail_after: str | None, stage: str) -> None:
    if fail_after == stage:
        raise InjectedWeatherHistoryFailure(f"Injected failure after {stage}")


@contextmanager
def _writer_lock(root: Path, timeout_seconds: float) -> Iterator[None]:
    lock_path = root / "locks" / "writer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    with lock_path.open("a+b") as handle:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise WeatherHistoryWriterBusy(
                        f"Timed out waiting for weather writer lock after {timeout_seconds}s"
                    )
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_partition_stream(path: Path, source: str, year: int, batch_size: int) -> tuple[int, str, str]:
    parquet = pq.ParquetFile(path)
    if parquet.schema_arrow != WEATHER_HISTORY_SCHEMA:
        raise WeatherHistoryWriterError(f"Unexpected output schema: {path}")
    previous: tuple[str, str, str] | None = None
    rows = 0
    minimum: str | None = None
    maximum: str | None = None
    for batch in parquet.iter_batches(batch_size=batch_size, columns=WEATHER_HISTORY_COLUMNS):
        for row in batch.to_pylist():
            key = weather_key(row)
            if key[0] != source or int(key[2][:4]) != year:
                raise WeatherHistoryWriterError(f"Row outside output partition: {key!r}")
            if previous is not None and key <= previous:
                raise WeatherHistoryWriterError(f"Duplicate or unordered output key: {key!r}")
            previous = key
            for column in WEATHER_HISTORY_FLOAT_COLUMNS:
                value = row.get(column)
                if value is not None and not math.isfinite(float(value)):
                    raise WeatherHistoryWriterError(f"Non-finite output {column}: {key!r}")
            day = key[2]
            minimum = day if minimum is None else min(minimum, day)
            maximum = day if maximum is None else max(maximum, day)
            rows += 1
    if rows == 0 or minimum is None or maximum is None:
        raise WeatherHistoryWriterError(f"Empty output partition: {path}")
    return rows, minimum, maximum


def _merge_partition(
    root: Path,
    source: str,
    year: int,
    old_partition: WeatherPartition | None,
    pending: Sequence[PendingBatch],
    *,
    row_group_size: int,
    batch_size: int,
) -> tuple[dict[str, Any], PartitionMergeReport]:
    parts_dir = root / "parts" / f"source={source}" / f"year={year}"
    parts_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".merge-", suffix=".parquet", dir=parts_dir
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    output = _BoundedTableWriter(temporary, row_group_size)
    pending_cursor = _FilteredPendingCursor(pending, year, batch_size)
    update = pending_cursor.next()
    update_rows = matched = inserted = changed = old_rows = 0
    try:
        if old_partition is not None:
            old_path = root / old_partition.path
            parquet = pq.ParquetFile(old_path)
            if parquet.schema_arrow != WEATHER_HISTORY_SCHEMA:
                raise WeatherHistoryWriterError(f"Unexpected old partition schema: {old_path}")
            previous_old_key: tuple[str, str, str] | None = None
            for batch in parquet.iter_batches(batch_size=batch_size, columns=WEATHER_HISTORY_COLUMNS):
                stations = batch.column("station_code").to_pylist()
                dates = batch.column("local_date").to_pylist()
                slice_start = 0
                position = 0
                while position < batch.num_rows:
                    old_key = (source, str(stations[position]), str(dates[position]))
                    if previous_old_key is not None and old_key <= previous_old_key:
                        raise WeatherHistoryWriterError(
                            f"Duplicate or unordered historical key: {old_key!r}"
                        )
                    previous_old_key = old_key
                    while update is not None and weather_key(update) < old_key:
                        if position > slice_start:
                            output.append_table(batch.slice(slice_start, position - slice_start))
                        output.append_row(update)
                        update_rows += 1
                        inserted += 1
                        changed += 1
                        update = pending_cursor.next()
                        slice_start = position
                    if update is not None and weather_key(update) == old_key:
                        if position > slice_start:
                            output.append_table(batch.slice(slice_start, position - slice_start))
                        old_row = batch.slice(position, 1).to_pylist()[0]
                        merged = _merge_non_null(old_row, update)
                        output.append_row(merged)
                        update_rows += 1
                        matched += 1
                        if _rows_differ(old_row, merged):
                            changed += 1
                        update = pending_cursor.next()
                        position += 1
                        old_rows += 1
                        slice_start = position
                        continue
                    position += 1
                    old_rows += 1
                if slice_start < batch.num_rows:
                    output.append_table(batch.slice(slice_start))
        while update is not None:
            output.append_row(update)
            update_rows += 1
            inserted += 1
            changed += 1
            update = pending_cursor.next()
        output.close()
        output = None  # type: ignore[assignment]
        if update_rows == 0:
            raise WeatherHistoryWriterError(f"No pending rows found for {source}/{year}")
        if changed == 0 and old_partition is not None:
            temporary.unlink(missing_ok=True)
            report = PartitionMergeReport(
                source, year, old_rows, update_rows, matched, inserted, changed,
                old_partition.rows, True, old_partition.size_bytes,
                pq.ParquetFile(root / old_partition.path).metadata.num_row_groups,
            )
            return asdict(old_partition), report
        rows, minimum, maximum = _validate_partition_stream(
            temporary, source, year, batch_size
        )
        expected = old_rows + inserted
        if rows != expected:
            raise WeatherHistoryWriterError(
                f"Output row mismatch for {source}/{year}: expected {expected}, got {rows}"
            )
        digest = sha256_file(temporary)
        immutable = parts_dir / f"data-{digest}.parquet"
        if immutable.exists():
            if sha256_file(immutable) != digest:
                raise WeatherHistoryWriterError(f"Immutable partition collision: {immutable}")
            temporary.unlink()
        else:
            os.replace(temporary, immutable)
            _fsync_file(immutable)
            _fsync_directory(parts_dir)
        metadata = pq.ParquetFile(immutable).metadata
        descriptor = {
            "source": source,
            "year": year,
            "path": immutable.relative_to(root).as_posix(),
            "sha256": digest,
            "size_bytes": immutable.stat().st_size,
            "rows": rows,
            "min_local_date": minimum,
            "max_local_date": maximum,
        }
        report = PartitionMergeReport(
            source, year, old_rows, update_rows, matched, inserted, changed,
            rows, False, immutable.stat().st_size, metadata.num_row_groups,
        )
        return descriptor, report
    finally:
        if output is not None:
            output.close()
        temporary.unlink(missing_ok=True)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    value = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _valid_coordinates(row: Mapping[str, Any]) -> bool:
    lat, lon = row.get("lat"), row.get("lon")
    return lat is not None and lon is not None and -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180


def _update_catalog(
    root: Path,
    generation: WeatherGeneration,
    pending: Sequence[PendingBatch],
    *,
    batch_size: int,
    coordinate_limit_km: float,
) -> tuple[dict[str, Any], bool]:
    old_path = root / generation.catalog.path
    table = pq.read_table(old_path, schema=CATALOG_SCHEMA)
    original = table.to_pylist()
    entries = {(row["source"], row["station_code"]): dict(row) for row in original}
    for item in pending:
        for batch in pq.ParquetFile(item.data_path).iter_batches(
            batch_size=batch_size,
            columns=WEATHER_HISTORY_COLUMNS,
        ):
            for row in batch.to_pylist():
                key = (row["source"], row["station_code"])
                day = row["local_date"]
                current = entries.get(key)
                coordinates_valid = _valid_coordinates(row)
                if current is None:
                    if not coordinates_valid:
                        continue
                    entries[key] = {
                        "source": row["source"],
                        "station_code": row["station_code"],
                        "station_name": row.get("station_name"),
                        "lat": row.get("lat"),
                        "lon": row.get("lon"),
                        "altitude": row.get("altitude"),
                        "first_date": day,
                        "last_date": day,
                        "metadata_date": day,
                    }
                    continue
                current["first_date"] = min(str(current["first_date"]), str(day))
                current["last_date"] = max(str(current["last_date"]), str(day))
                if coordinates_valid:
                    distance = _haversine_km(
                        float(current["lat"]), float(current["lon"]),
                        float(row["lat"]), float(row["lon"]),
                    )
                    if distance > coordinate_limit_km:
                        raise WeatherHistoryCoordinateConflict(
                            f"Coordinate jump {distance:.3f} km for {key!r}"
                        )
                    if str(day) >= str(current["metadata_date"]):
                        for column in ("station_name", "lat", "lon", "altitude"):
                            if row.get(column) is not None:
                                current[column] = row[column]
                        current["metadata_date"] = day
    rows = [entries[key] for key in sorted(entries)]
    changed = rows != original
    if not changed:
        return {
            "path": generation.catalog.path,
            "sha256": generation.catalog.sha256,
            "size_bytes": generation.catalog.size_bytes,
            "rows": generation.catalog.rows,
        }, False
    catalogs = root / "catalogs"
    catalogs.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".catalog-", suffix=".parquet", dir=catalogs)
    os.close(descriptor)
    temporary = Path(name)
    try:
        pq.write_table(
            pa.Table.from_pylist(rows, schema=CATALOG_SCHEMA),
            temporary,
            compression="snappy",
            row_group_size=DEFAULT_ROW_GROUP_SIZE,
        )
        digest = sha256_file(temporary)
        immutable = catalogs / f"stations-{digest}.parquet"
        if immutable.exists():
            temporary.unlink()
        else:
            os.replace(temporary, immutable)
            _fsync_file(immutable)
            _fsync_directory(catalogs)
        return {
            "path": immutable.relative_to(root).as_posix(),
            "sha256": digest,
            "size_bytes": immutable.stat().st_size,
            "rows": len(rows),
        }, True
    finally:
        temporary.unlink(missing_ok=True)


def _manifest_payload(generation: WeatherGeneration) -> dict[str, Any]:
    return json.loads(generation.manifest_path.read_text(encoding="utf-8"))


def _receipt_ids(payload: Mapping[str, Any]) -> set[str]:
    report = payload.get("update_report")
    if not isinstance(report, Mapping):
        return set()
    values = report.get("batch_ids", [])
    return {str(value) for value in values} if isinstance(values, list) else set()


def _ensure_free_space(
    root: Path,
    generation: WeatherGeneration,
    pending: Sequence[PendingBatch],
    reserve_bytes: int,
) -> None:
    touched = {(item.source, year) for item in pending for year in item.years}
    old_bytes = sum(
        partition.size_bytes
        for partition in generation.partitions
        if (partition.source, partition.year) in touched
    )
    pending_bytes = sum(item.data_path.stat().st_size for item in pending)
    required = max(16 * 1024**2, old_bytes * 2 + pending_bytes * 2 + generation.catalog.size_bytes * 2)
    free = shutil.disk_usage(root).free
    if free - required < reserve_bytes:
        raise WeatherHistoryWriterError(
            f"Insufficient disk for archive: free={free}, required={required}, reserve={reserve_bytes}"
        )


def archive_pending_batches(
    data_dir: Path,
    *,
    row_group_size: int = DEFAULT_ROW_GROUP_SIZE,
    batch_size: int = DEFAULT_ROW_GROUP_SIZE,
    lock_timeout_seconds: float = 30.0,
    reserve_bytes: int = 512 * 1024**2,
    coordinate_limit_km: float = 1.0,
    fail_after: str | None = None,
) -> ArchiveReport:
    """Archive all valid pending batches as one immutable generation.

    Pending files deliberately remain in place.  The runner integration will
    acknowledge them only after the corresponding live CSV is also durable.
    """
    if row_group_size <= 0 or batch_size <= 0 or lock_timeout_seconds < 0:
        raise ValueError("Invalid archive limits")
    root = weather_history_root(Path(data_dir))
    with _writer_lock(root, lock_timeout_seconds):
        generation = resolve_weather_generation(root)
        pending = list_pending_batches(root)
        if not pending:
            return ArchiveReport(
                generation.generation_id,
                generation.generation_id,
                (), (), (), False, False,
            )
        current_payload = _manifest_payload(generation)
        receipts = _receipt_ids(current_payload)
        already = tuple(sorted(item.batch_id for item in pending if item.batch_id in receipts))
        fresh = [item for item in pending if item.batch_id not in receipts]
        if not fresh:
            return ArchiveReport(
                generation.generation_id,
                generation.generation_id,
                (), already, (), False, False,
            )
        _ensure_free_space(root, generation, fresh, reserve_bytes)
        old_by_key = {(item.source, item.year): item for item in generation.partitions}
        pending_by_source: dict[str, list[PendingBatch]] = {}
        touched: set[tuple[str, int]] = set()
        for item in fresh:
            pending_by_source.setdefault(item.source, []).append(item)
            touched.update((item.source, year) for year in item.years)
        descriptors = {
            (item.source, item.year): asdict(item) for item in generation.partitions
        }
        reports: list[PartitionMergeReport] = []
        for source, year in sorted(touched):
            descriptor, report = _merge_partition(
                root,
                source,
                year,
                old_by_key.get((source, year)),
                pending_by_source[source],
                row_group_size=row_group_size,
                batch_size=batch_size,
            )
            descriptors[(source, year)] = descriptor
            reports.append(report)
        _fail_if_requested(fail_after, "partitions")
        catalog, catalog_changed = _update_catalog(
            root,
            generation,
            fresh,
            batch_size=batch_size,
            coordinate_limit_km=coordinate_limit_km,
        )
        _fail_if_requested(fail_after, "catalog")

        active_pending_ids = {item.batch_id for item in pending}
        carried_receipts = receipts.intersection(active_pending_ids)
        batch_ids = tuple(sorted(item.batch_id for item in fresh))
        all_receipts = sorted(carried_receipts.union(batch_ids))
        created_at = datetime.now(UTC).isoformat()
        logical_seed = {
            "previous_generation_id": generation.generation_id,
            "batch_ids": batch_ids,
            "partitions": [descriptors[key] for key in sorted(descriptors)],
            "catalog": catalog,
        }
        import hashlib

        suffix = hashlib.sha256(canonical_json_bytes(logical_seed)).hexdigest()[:12]
        generation_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + f"-{suffix}"
        partition_values = [descriptors[key] for key in sorted(descriptors)]
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "generation_id": generation_id,
            "previous_generation_id": generation.generation_id,
            "created_at": created_at,
            "data_schema_version": DATA_SCHEMA_VERSION,
            "key": ["source", "station_code", "local_date"],
            "partitions": partition_values,
            "catalog": catalog,
            "totals": {
                "rows": sum(int(item["rows"]) for item in partition_values),
                "size_bytes": sum(int(item["size_bytes"]) for item in partition_values)
                + int(catalog["size_bytes"]),
            },
            "update_report": {
                "batch_ids": all_receipts,
                "fresh_batch_ids": list(batch_ids),
                "partitions": [asdict(value) for value in reports],
            },
        }
        manifests = root / "manifests"
        manifest_path = manifests / f"{generation_id}.json"
        write_json_atomic(manifest_path, manifest)
        manifest_sha = sha256_file(manifest_path)
        _fail_if_requested(fail_after, "manifest")
        write_json_atomic(
            root / "CURRENT.json",
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "generation_id": generation_id,
                "manifest_path": manifest_path.relative_to(root).as_posix(),
                "manifest_sha256": manifest_sha,
            },
        )
        _fail_if_requested(fail_after, "current")
        resolved = resolve_weather_generation(root)
        if resolved.generation_id != generation_id:
            raise WeatherHistoryWriterError("Committed generation did not become CURRENT")
        return ArchiveReport(
            generation_id,
            generation.generation_id,
            batch_ids,
            already,
            tuple(reports),
            catalog_changed,
            True,
        )


def acknowledge_archived_pending(data_dir: Path, batch_id: str) -> None:
    """Delete one pending only when CURRENT contains its durable receipt."""
    root = weather_history_root(Path(data_dir))
    with _writer_lock(root, 30.0):
        generation = resolve_weather_generation(root)
        receipts = _receipt_ids(_manifest_payload(generation))
        if batch_id not in receipts:
            raise WeatherHistoryWriterError(
                f"CURRENT generation has no receipt for pending {batch_id}"
            )
        matches = [item for item in list_pending_batches(root) if item.batch_id == batch_id]
        if len(matches) != 1:
            raise WeatherHistoryWriterError(
                f"Expected exactly one pending batch {batch_id}, found {len(matches)}"
            )
        acknowledge_pending_batch(matches[0])


def _active_lease_generation_ids(root: Path) -> tuple[set[str], int]:
    """Return unexpired lease generations and discard only valid expired leases."""
    active: set[str] = set()
    expired_removed = 0
    leases_root = root / "leases"
    now = datetime.now(UTC)
    if not leases_root.exists():
        return active, expired_removed
    for generation_dir in sorted(path for path in leases_root.iterdir() if path.is_dir()):
        generation_id = generation_dir.name
        for lease_path in sorted(generation_dir.glob("*.json")):
            try:
                payload = json.loads(lease_path.read_text(encoding="utf-8"))
                if payload.get("schema_version") != "weather_history_lease_v1":
                    raise ValueError("unsupported lease schema")
                if payload.get("generation_id") != generation_id:
                    raise ValueError("lease generation mismatch")
                expires_at = datetime.fromisoformat(str(payload["expires_at"]))
                if expires_at.tzinfo is None:
                    raise ValueError("lease expiry is not timezone-aware")
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                # A malformed lease is retained conservatively.  Deleting a
                # generation possibly held by a reader is worse than leaking it.
                active.add(generation_id)
                continue
            if expires_at <= now:
                lease_path.unlink(missing_ok=True)
                expired_removed += 1
            else:
                active.add(generation_id)
        try:
            generation_dir.rmdir()
        except OSError:
            pass
    return active, expired_removed


def prune_weather_generations(
    data_dir: Path,
    *,
    lock_timeout_seconds: float = 30.0,
) -> GenerationPruneReport:
    """Keep CURRENT, its immediate predecessor and every leased generation.

    Immutable objects are deleted only after resolving every retained manifest
    and computing their complete reference set under the exclusive writer lock.
    """
    root = weather_history_root(Path(data_dir))
    with _writer_lock(root, lock_timeout_seconds):
        current = resolve_weather_generation(root)
        keep_ids = {current.generation_id}
        if current.previous_generation_id:
            keep_ids.add(current.previous_generation_id)
        lease_ids, expired_removed = _active_lease_generation_ids(root)
        keep_ids.update(lease_ids)

        manifests_root = root / "manifests"
        manifests = {path.stem: path for path in manifests_root.glob("*.json")}
        missing = sorted(keep_ids - set(manifests))
        if missing:
            raise WeatherHistoryWriterError(
                f"Cannot prune: retained generation manifest(s) missing: {missing}"
            )

        # Compare canonical paths: macOS exposes /var through /private/var, and
        # lexical Path equality would otherwise misclassify every live object.
        referenced: set[Path] = set()
        for generation_id in sorted(keep_ids):
            generation = resolve_weather_manifest(
                root,
                manifests[generation_id],
                expected_generation_id=generation_id,
                verify_hashes=False,
            )
            referenced.update(
                generation.object_path(item.path).resolve()
                for item in generation.partitions
            )
            referenced.add(generation.object_path(generation.catalog.path).resolve())

        removed_ids: list[str] = []
        bytes_removed = 0
        manifests_removed = 0
        for generation_id, path in sorted(manifests.items()):
            if generation_id in keep_ids:
                continue
            size = path.stat().st_size
            path.unlink()
            bytes_removed += size
            manifests_removed += 1
            removed_ids.append(generation_id)

        objects_removed = 0
        candidates = [
            *root.glob("parts/source=*/year=*/*.parquet"),
            *root.glob("catalogs/*.parquet"),
        ]
        for path in sorted(set(candidates)):
            if path.resolve() in referenced:
                continue
            size = path.stat().st_size
            path.unlink()
            bytes_removed += size
            objects_removed += 1
        for directory in sorted(
            (path for path in (root / "parts").glob("source=*/year=*") if path.is_dir()),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
        return GenerationPruneReport(
            kept_generation_ids=tuple(sorted(keep_ids)),
            removed_generation_ids=tuple(removed_ids),
            active_lease_generation_ids=tuple(sorted(lease_ids)),
            expired_leases_removed=expired_removed,
            manifests_removed=manifests_removed,
            objects_removed=objects_removed,
            bytes_removed=bytes_removed,
        )


def repair_current_after_restore(
    data_dir: Path,
    *,
    apply: bool = False,
    lock_timeout_seconds: float = 30.0,
) -> RestoreRepairReport:
    """Select the newest exhaustively valid manifest after an interrupted restore.

    Dry-run is the default.  This never reconstructs data or falls back
    silently during normal reads; an operator must explicitly request apply.
    """
    root = weather_history_root(Path(data_dir))
    with _writer_lock(root, lock_timeout_seconds):
        valid: list[WeatherGeneration] = []
        rejected: list[tuple[str, str]] = []
        for path in sorted((root / "manifests").glob("*.json")):
            try:
                valid.append(
                    resolve_weather_manifest(
                        root,
                        path,
                        verify_hashes=True,
                    )
                )
            except Exception as exc:
                rejected.append((path.relative_to(root).as_posix(), str(exc)))
        if not valid:
            raise WeatherHistoryWriterError(
                "No complete weather-history generation survives the restore"
            )
        selected = max(valid, key=lambda value: (value.created_at, value.generation_id))
        if apply:
            write_json_atomic(
                root / "CURRENT.json",
                {
                    "schema_version": CURRENT_SCHEMA_VERSION,
                    "generation_id": selected.generation_id,
                    "manifest_path": selected.manifest_path.relative_to(root).as_posix(),
                    "manifest_sha256": selected.manifest_sha256,
                },
            )
            resolved = resolve_weather_generation(root, verify_hashes=True)
            if resolved.generation_id != selected.generation_id:
                raise WeatherHistoryWriterError("Restore repair did not publish selected generation")
        return RestoreRepairReport(
            selected_generation_id=selected.generation_id,
            selected_manifest_path=selected.manifest_path.relative_to(root).as_posix(),
            valid_generation_ids=tuple(
                value.generation_id
                for value in sorted(valid, key=lambda value: (value.created_at, value.generation_id))
            ),
            rejected_manifests=tuple(rejected),
            applied=apply,
        )
