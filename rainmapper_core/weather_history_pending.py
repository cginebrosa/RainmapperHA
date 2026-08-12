"""Bounded, deterministic pending batches for partitioned weather history."""

from __future__ import annotations

import hashlib
import heapq
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

from rainmapper_core.weather_history_contract import (
    DEFAULT_ROW_GROUP_SIZE,
    PENDING_SCHEMA_VERSION,
    WEATHER_HISTORY_COLUMNS,
    WEATHER_HISTORY_SCHEMA,
    normalize_mapping,
    weather_key,
)
from rainmapper_core.weather_history_dataset import (
    canonical_json_bytes,
    sha256_file,
    weather_history_root,
    write_json_atomic,
)


@dataclass(frozen=True)
class PendingBatch:
    source: str
    batch_id: str
    data_path: Path
    sidecar_path: Path
    rows: int
    input_rows: int
    collapsed_rows: int
    years: tuple[int, ...]
    min_local_date: str
    max_local_date: str
    data_sha256: str


class PendingBatchError(RuntimeError):
    """Raised when a pending batch is invalid or conflicts with queued work."""


class _ParquetRowCursor:
    def __init__(self, path: Path, batch_size: int) -> None:
        self._batches = iter(
            pq.ParquetFile(path).iter_batches(
                batch_size=batch_size,
                columns=WEATHER_HISTORY_COLUMNS,
            )
        )
        self._rows: list[dict[str, Any]] = []
        self._index = 0

    def next(self) -> dict[str, Any] | None:
        while self._index >= len(self._rows):
            try:
                self._rows = next(self._batches).to_pylist()
            except StopIteration:
                return None
            self._index = 0
        row = self._rows[self._index]
        self._index += 1
        return row


class _RowWriter:
    def __init__(self, path: Path, row_group_size: int) -> None:
        self.path = path
        self.row_group_size = row_group_size
        self._rows: list[dict[str, Any]] = []
        self._writer = pq.ParquetWriter(
            path,
            WEATHER_HISTORY_SCHEMA,
            compression="snappy",
            use_dictionary=False,
        )
        self.row_count = 0

    def append(self, row: Mapping[str, Any]) -> None:
        self._rows.append({column: row.get(column) for column in WEATHER_HISTORY_COLUMNS})
        if len(self._rows) >= self.row_group_size:
            self.flush()

    def flush(self) -> None:
        if not self._rows:
            return
        table = pa.Table.from_pylist(self._rows, schema=WEATHER_HISTORY_SCHEMA)
        self._writer.write_table(table, row_group_size=self.row_group_size)
        self.row_count += len(self._rows)
        self._rows.clear()

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


def _iter_input_rows(
    batches: Iterable[pa.RecordBatch | pa.Table | Sequence[Mapping[str, Any]]],
    source: str,
    chunk_rows: int,
) -> Iterator[dict[str, Any]]:
    for batch in batches:
        if isinstance(batch, (pa.RecordBatch, pa.Table)):
            for offset in range(0, batch.num_rows, chunk_rows):
                for row in batch.slice(offset, chunk_rows).to_pylist():
                    yield normalize_mapping(row, source)
        else:
            for row in batch:
                yield normalize_mapping(row, source)


def _write_run(path: Path, rows: Mapping[tuple[str, str, str], Mapping[str, Any]], row_group_size: int) -> None:
    writer = _RowWriter(path, row_group_size)
    try:
        for key in sorted(rows):
            writer.append(rows[key])
    finally:
        writer.close()


def _merge_run_group(paths: Sequence[Path], destination: Path, row_group_size: int) -> None:
    cursors = [_ParquetRowCursor(path, row_group_size) for path in paths]
    heap: list[tuple[tuple[str, str, str], int, dict[str, Any]]] = []
    for index, cursor in enumerate(cursors):
        row = cursor.next()
        if row is not None:
            heapq.heappush(heap, (weather_key(row), index, row))
    writer = _RowWriter(destination, row_group_size)
    try:
        while heap:
            key = heap[0][0]
            same_key: list[tuple[int, dict[str, Any]]] = []
            while heap and heap[0][0] == key:
                _, index, row = heapq.heappop(heap)
                same_key.append((index, row))
                following = cursors[index].next()
                if following is not None:
                    heapq.heappush(heap, (weather_key(following), index, following))
            same_key.sort(key=lambda item: item[0])
            collapsed = same_key[0][1]
            for _, newer in same_key[1:]:
                collapsed = _merge_non_null(collapsed, newer)
            writer.append(collapsed)
    finally:
        writer.close()


def _merge_runs(
    runs: list[Path],
    stage: Path,
    *,
    fan_in: int,
    row_group_size: int,
) -> Path:
    pass_index = 0
    while len(runs) > 1:
        merged: list[Path] = []
        for group_index, offset in enumerate(range(0, len(runs), fan_in)):
            group = runs[offset : offset + fan_in]
            destination = stage / f"merge-{pass_index:03d}-{group_index:06d}.parquet"
            _merge_run_group(group, destination, row_group_size)
            merged.append(destination)
        for path in runs:
            path.unlink(missing_ok=True)
        runs = merged
        pass_index += 1
    return runs[0]


def _logical_digest(path: Path, source: str, batch_size: int) -> tuple[str, int, tuple[int, ...], str, str]:
    digest = hashlib.sha256()
    digest.update(PENDING_SCHEMA_VERSION.encode("utf-8") + b"\0")
    digest.update(source.encode("utf-8") + b"\0")
    rows = 0
    years: set[int] = set()
    minimum: str | None = None
    maximum: str | None = None
    previous_key: tuple[str, str, str] | None = None
    for batch in pq.ParquetFile(path).iter_batches(
        batch_size=batch_size,
        columns=WEATHER_HISTORY_COLUMNS,
    ):
        for row in batch.to_pylist():
            key = weather_key(row)
            if previous_key is not None and key <= previous_key:
                raise PendingBatchError(f"Pending rows are not strictly ordered at {key!r}")
            previous_key = key
            day = str(row["local_date"])
            years.add(int(day[:4]))
            minimum = day if minimum is None else min(minimum, day)
            maximum = day if maximum is None else max(maximum, day)
            logical = [row.get(column) for column in WEATHER_HISTORY_COLUMNS]
            digest.update(
                json.dumps(
                    logical,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
                + b"\n"
            )
            rows += 1
    if rows == 0 or minimum is None or maximum is None:
        raise PendingBatchError("Cannot publish an empty pending batch")
    return digest.hexdigest(), rows, tuple(sorted(years)), minimum, maximum


def list_pending_batches(data_dir: Path, source: str | None = None) -> list[PendingBatch]:
    root = weather_history_root(Path(data_dir))
    directories = [root / "pending" / f"source={source}"] if source else sorted((root / "pending").glob("source=*"))
    result: list[PendingBatch] = []
    for directory in directories:
        if not directory.is_dir():
            continue
        for sidecar_path in sorted(directory.glob("*.json")):
            payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            if payload.get("schema_version") != PENDING_SCHEMA_VERSION:
                raise PendingBatchError(f"Unsupported pending sidecar: {sidecar_path}")
            data_path = directory / str(payload["data_file"])
            if not data_path.is_file() or sha256_file(data_path) != payload["data_sha256"]:
                raise PendingBatchError(f"Pending data integrity failure: {data_path}")
            result.append(
                PendingBatch(
                    source=str(payload["source"]),
                    batch_id=str(payload["batch_id"]),
                    data_path=data_path,
                    sidecar_path=sidecar_path,
                    rows=int(payload["rows"]),
                    input_rows=int(payload["input_rows"]),
                    collapsed_rows=int(payload["collapsed_rows"]),
                    years=tuple(int(value) for value in payload["years"]),
                    min_local_date=str(payload["min_local_date"]),
                    max_local_date=str(payload["max_local_date"]),
                    data_sha256=str(payload["data_sha256"]),
                )
            )
    return result


def build_pending_batch(
    data_dir: Path,
    source: str,
    batches: Iterable[pa.RecordBatch | pa.Table | Sequence[Mapping[str, Any]]],
    *,
    run_id: str,
    chunk_rows: int = DEFAULT_ROW_GROUP_SIZE,
    row_group_size: int = DEFAULT_ROW_GROUP_SIZE,
    fan_in: int = 8,
) -> PendingBatch | None:
    """Normalize, collapse and publish one bounded external-sort pending batch."""
    if chunk_rows <= 0 or row_group_size <= 0:
        raise ValueError("chunk_rows and row_group_size must be positive")
    if fan_in < 2:
        raise ValueError("fan_in must be at least 2")
    if list_pending_batches(data_dir, source):
        raise PendingBatchError(f"Source {source!r} already has a pending batch")

    root = weather_history_root(Path(data_dir))
    staging_parent = root / "pending" / ".staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f"{source}-", dir=staging_parent))
    runs: list[Path] = []
    chunk: dict[tuple[str, str, str], dict[str, Any]] = {}
    input_rows = 0
    try:
        for row in _iter_input_rows(batches, source, chunk_rows):
            input_rows += 1
            key = weather_key(row)
            chunk[key] = row if key not in chunk else _merge_non_null(chunk[key], row)
            if len(chunk) >= chunk_rows:
                path = stage / f"run-{len(runs):06d}.parquet"
                _write_run(path, chunk, row_group_size)
                runs.append(path)
                chunk.clear()
        if chunk:
            path = stage / f"run-{len(runs):06d}.parquet"
            _write_run(path, chunk, row_group_size)
            runs.append(path)
            chunk.clear()
        if not runs:
            return None
        final_run = _merge_runs(
            runs,
            stage,
            fan_in=fan_in,
            row_group_size=row_group_size,
        )
        batch_id, rows, years, minimum, maximum = _logical_digest(
            final_run,
            source,
            row_group_size,
        )
        data_sha = sha256_file(final_run)
        destination_dir = root / "pending" / f"source={source}"
        destination_dir.mkdir(parents=True, exist_ok=True)
        data_path = destination_dir / f"{batch_id}.parquet"
        sidecar_path = destination_dir / f"{batch_id}.json"
        if data_path.exists() or sidecar_path.exists():
            raise PendingBatchError(f"Pending batch collision: {batch_id}")
        os.replace(final_run, data_path)
        with data_path.open("rb") as handle:
            os.fsync(handle.fileno())
        descriptor = os.open(destination_dir, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        write_json_atomic(
            sidecar_path,
            {
                "schema_version": PENDING_SCHEMA_VERSION,
                "batch_id": batch_id,
                "source": source,
                "run_id": run_id,
                "created_at": datetime.now(UTC).isoformat(),
                "data_file": data_path.name,
                "data_sha256": data_sha,
                "data_size_bytes": data_path.stat().st_size,
                "rows": rows,
                "input_rows": input_rows,
                "collapsed_rows": input_rows - rows,
                "final_ordinal": input_rows - 1,
                "years": list(years),
                "min_local_date": minimum,
                "max_local_date": maximum,
            },
        )
        return PendingBatch(
            source=source,
            batch_id=batch_id,
            data_path=data_path,
            sidecar_path=sidecar_path,
            rows=rows,
            input_rows=input_rows,
            collapsed_rows=input_rows - rows,
            years=years,
            min_local_date=minimum,
            max_local_date=maximum,
            data_sha256=data_sha,
        )
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def acknowledge_pending_batch(batch: PendingBatch) -> None:
    """Remove a batch only after history and its future live CSV are confirmed."""
    batch.data_path.unlink(missing_ok=True)
    batch.sidecar_path.unlink(missing_ok=True)
    descriptor = os.open(batch.sidecar_path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
