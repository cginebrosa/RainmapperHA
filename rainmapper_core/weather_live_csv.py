"""Bounded reapply and retention for the four live daily weather CSV queues."""

from __future__ import annotations

import csv
import os
import stat
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterator, Mapping

import pyarrow.parquet as pq

from rainmapper_core.weather_history_contract import (
    LEGACY_TO_CANONICAL,
    WEATHER_HISTORY_COLUMNS,
    WEATHER_HISTORY_FLOAT_COLUMNS,
    normalize_mapping,
    weather_key,
)
from rainmapper_core.weather_history_pending import PendingBatch


LIVE_CSV_FILES = {
    "aemet": "Aemet_incremental.csv",
    "meteocat": "Meteocat_incremental.csv",
    "meteoclimatic": "Meteoclimatic_incremental.csv",
    "wunderground": "Wunderground_incremental.csv",
}
DEFAULT_LIVE_COLUMNS = tuple(LEGACY_TO_CANONICAL)
CANONICAL_TO_LEGACY = {canonical: legacy for legacy, canonical in LEGACY_TO_CANONICAL.items()}


@dataclass(frozen=True)
class LiveCsvReport:
    source: str
    input_rows: int
    pending_rows: int
    matched_rows: int
    inserted_rows: int
    retained_rows: int
    dropped_rows: int
    cutoff_date: str
    output_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _merge_non_null(older: Mapping[str, Any], newer: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(older)
    for column in WEATHER_HISTORY_COLUMNS:
        if newer.get(column) is not None:
            merged[column] = newer[column]
    return merged


def _descending_key(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["station_code"]), -int(str(row["local_date"]))


def _iter_existing(path: Path, source: str) -> tuple[list[str], Iterator[dict[str, Any]]]:
    handle = path.open("r", encoding="utf-8-sig", newline="")
    reader = csv.DictReader(handle)
    if not reader.fieldnames:
        handle.close()
        raise RuntimeError(f"Live CSV has no header: {path}")
    fieldnames = list(reader.fieldnames)

    def rows() -> Iterator[dict[str, Any]]:
        previous_key: tuple[str, int] | None = None
        buffered: dict[str, Any] | None = None
        try:
            for raw in reader:
                row = normalize_mapping(raw, source)
                key = _descending_key(row)
                if previous_key is not None and key < previous_key:
                    raise RuntimeError(f"Live CSV is not sorted at {weather_key(row)!r}: {path}")
                if buffered is not None and weather_key(buffered) == weather_key(row):
                    buffered = _merge_non_null(buffered, row)
                else:
                    if buffered is not None:
                        yield buffered
                    buffered = row
                previous_key = key
            if buffered is not None:
                yield buffered
        finally:
            handle.close()

    return fieldnames, rows()


def _pending_rows(pending: PendingBatch) -> list[dict[str, Any]]:
    rows = pq.read_table(pending.data_path, columns=WEATHER_HISTORY_COLUMNS).to_pylist()
    rows.sort(key=_descending_key)
    return rows


def _format_value(column: str, value: Any) -> str:
    if value is None:
        return ""
    if column in WEATHER_HISTORY_FLOAT_COLUMNS:
        return format(float(value), ".15g").replace(".", ",")
    return str(value)


def _legacy_row(row: Mapping[str, Any], fieldnames: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in fieldnames:
        canonical = LEGACY_TO_CANONICAL.get(field, field)
        result[field] = _format_value(canonical, row.get(canonical))
    return result


def apply_pending_to_live_csv(
    data_dir: Path,
    pending: PendingBatch,
    *,
    retention_days: int = 180,
    reference_day: date | None = None,
) -> LiveCsvReport:
    """Reapply one durable pending and atomically retain T-179..T."""
    if retention_days <= 0:
        raise ValueError("retention_days must be positive")
    reference_day = reference_day or date.today()
    cutoff = (reference_day - timedelta(days=retention_days - 1)).strftime("%Y%m%d")
    path = Path(data_dir) / LIVE_CSV_FILES[pending.source]
    path.parent.mkdir(parents=True, exist_ok=True)
    output_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    if path.exists():
        fieldnames, existing = _iter_existing(path, pending.source)
    else:
        fieldnames, existing = list(DEFAULT_LIVE_COLUMNS), iter(())
    incoming = iter(_pending_rows(pending))
    old = next(existing, None)
    fresh = next(incoming, None)
    input_rows = pending_rows = matched = inserted = retained = dropped = 0
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            os.fchmod(handle.fileno(), output_mode)
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            def emit(row: Mapping[str, Any]) -> None:
                nonlocal retained, dropped
                if str(row["local_date"]) < cutoff:
                    dropped += 1
                    return
                writer.writerow(_legacy_row(row, fieldnames))
                retained += 1

            while old is not None or fresh is not None:
                if old is None:
                    pending_rows += 1
                    inserted += 1
                    emit(fresh)
                    fresh = next(incoming, None)
                    continue
                if fresh is None:
                    input_rows += 1
                    emit(old)
                    old = next(existing, None)
                    continue
                old_key = _descending_key(old)
                fresh_key = _descending_key(fresh)
                if old_key < fresh_key:
                    input_rows += 1
                    emit(old)
                    old = next(existing, None)
                elif fresh_key < old_key:
                    pending_rows += 1
                    inserted += 1
                    emit(fresh)
                    fresh = next(incoming, None)
                else:
                    input_rows += 1
                    pending_rows += 1
                    matched += 1
                    emit(_merge_non_null(old, fresh))
                    old = next(existing, None)
                    fresh = next(incoming, None)
            handle.flush()
            os.fsync(handle.fileno())
        temporary = Path(temporary_name)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return LiveCsvReport(
            source=pending.source,
            input_rows=input_rows,
            pending_rows=pending_rows,
            matched_rows=matched,
            inserted_rows=inserted,
            retained_rows=retained,
            dropped_rows=dropped,
            cutoff_date=cutoff,
            output_bytes=path.stat().st_size,
        )
    finally:
        Path(temporary_name).unlink(missing_ok=True)
