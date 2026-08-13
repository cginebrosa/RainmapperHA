"""Atomic incremental maintenance for the canonical daily weather Parquet."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from rainmapper_core.incremental_upsert import upsert_incremental
from rainmapper_core.mushroom_observation_context import (
    DAILY_INCREMENTAL_FILES,
    _PARQUET_COL_MAP,
    _PARQUET_FLOAT_COLS,
)
from rainmapper_core.weather_history_contract import (
    WEATHER_HISTORY_COLUMNS,
    WEATHER_HISTORY_KEY,
    WEATHER_HISTORY_SCHEMA,
    WEATHER_HISTORY_STRING_COLUMNS,
)


@dataclass(frozen=True)
class WeatherHistoryUpsertReport:
    old_rows: int
    update_rows: int
    matched_rows: int
    inserted_rows: int
    output_rows: int
    output_bytes: int
    row_groups: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def _clean_string(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().replace("", pd.NA)


def normalize_weather_history_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize either legacy incremental or canonical Parquet columns."""
    normalized = frame.rename(
        columns={
            legacy: canonical
            for legacy, canonical in _PARQUET_COL_MAP.items()
            if legacy in frame.columns and canonical not in frame.columns
        }
    ).copy()
    for column in WEATHER_HISTORY_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    normalized = normalized[WEATHER_HISTORY_COLUMNS]
    for column in WEATHER_HISTORY_STRING_COLUMNS:
        normalized[column] = _clean_string(normalized[column])
    normalized["local_date"] = normalized["local_date"].str.replace(
        r"\.0$", "", regex=True
    )
    for column in _PARQUET_FLOAT_COLS:
        normalized[column] = pd.to_numeric(
            normalized[column].astype("string").str.replace(",", ".", regex=False),
            errors="coerce",
        ).astype("Float64")
    return normalized


def collapse_weather_history_updates(frame: pd.DataFrame) -> pd.DataFrame:
    """Collapse repeated update keys with later non-null values winning."""
    normalized = normalize_weather_history_frame(frame)
    valid = normalized[WEATHER_HISTORY_KEY].notna().all(axis=1)
    normalized = normalized.loc[valid].copy()
    if normalized.empty:
        return normalized
    empty = normalized.head(0)
    collapsed = upsert_incremental(
        normalized,
        empty,
        key_columns=WEATHER_HISTORY_KEY,
    )
    return collapsed.sort_values(WEATHER_HISTORY_KEY, kind="stable").reset_index(drop=True)


def incremental_csv_to_weather_updates(
    path: Path,
    source: str,
    *,
    cutoff_date: str | None = None,
    chunk_rows: int = 100_000,
) -> pd.DataFrame:
    """Load one live CSV queue in chunks and normalize the requested tail."""
    frames = []
    for chunk in pd.read_csv(
        path,
        dtype=str,
        low_memory=False,
        chunksize=chunk_rows,
    ):
        if cutoff_date is not None:
            if "Data Local" not in chunk.columns:
                raise ValueError(f"Missing Data Local in weather queue {path}")
            local_dates = _clean_string(chunk["Data Local"]).str.replace(
                r"\.0$", "", regex=True
            )
            chunk = chunk.loc[local_dates >= cutoff_date].copy()
        if chunk.empty:
            continue
        chunk["source"] = source
        frames.append(normalize_weather_history_frame(chunk))
    if not frames:
        return pd.DataFrame(columns=WEATHER_HISTORY_COLUMNS)
    return collapse_weather_history_updates(pd.concat(frames, ignore_index=True))


def load_weather_queue_updates(
    data_dir: Path,
    *,
    retention_days: int = 180,
    reference_day: date | None = None,
) -> pd.DataFrame:
    """Load the four bounded live queues, never historical raw responses."""
    if retention_days <= 0:
        raise ValueError("retention_days must be positive")
    reference_day = reference_day or date.today()
    cutoff_date = (reference_day - timedelta(days=retention_days - 1)).strftime(
        "%Y%m%d"
    )
    frames = [
        incremental_csv_to_weather_updates(
            data_dir / filename,
            source,
            cutoff_date=cutoff_date,
        )
        for source, filename in DAILY_INCREMENTAL_FILES
        if (data_dir / filename).is_file()
    ]
    if not frames:
        return pd.DataFrame(columns=WEATHER_HISTORY_COLUMNS)
    return collapse_weather_history_updates(pd.concat(frames, ignore_index=True))


def update_weather_history_from_live_queues(
    data_dir: Path,
    *,
    retention_days: int = 180,
    reference_day: date | None = None,
) -> WeatherHistoryUpsertReport:
    """Apply bounded live CSV queues to the canonical Parquet in place."""
    history_path = Path(data_dir) / "weather_daily.parquet"
    updates = load_weather_queue_updates(
        Path(data_dir),
        retention_days=retention_days,
        reference_day=reference_day,
    )
    if updates.empty:
        raise RuntimeError("No usable rows found in the live weather queues")
    if not history_path.exists():
        history_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = history_path.with_name(
            f".{history_path.name}.{uuid4().hex}.tmp"
        )
        writer: pq.ParquetWriter | None = None
        try:
            writer = pq.ParquetWriter(
                temporary_path,
                WEATHER_HISTORY_SCHEMA,
                compression="snappy",
                use_dictionary=True,
            )
            _write_frame(writer, updates, row_group_size=512)
            writer.close()
            writer = None
            metadata = pq.ParquetFile(temporary_path).metadata
            with temporary_path.open("rb") as handle:
                os.fsync(handle.fileno())
            temporary_path.replace(history_path)
            return WeatherHistoryUpsertReport(
                old_rows=0,
                update_rows=len(updates),
                matched_rows=0,
                inserted_rows=len(updates),
                output_rows=metadata.num_rows,
                output_bytes=history_path.stat().st_size,
                row_groups=metadata.num_row_groups,
            )
        except Exception:
            if writer is not None:
                writer.close()
            temporary_path.unlink(missing_ok=True)
            raise
    return upsert_weather_history_parquet(history_path, updates)


def _key_tuples(frame: pd.DataFrame) -> list[tuple[str, str, str]]:
    return list(
        zip(
            frame["source"].astype(str),
            frame["station_code"].astype(str),
            frame["local_date"].astype(str),
            strict=True,
        )
    )


def _write_frame(
    writer: pq.ParquetWriter,
    frame: pd.DataFrame,
    *,
    row_group_size: int,
) -> None:
    if frame.empty:
        return
    table = pa.Table.from_pandas(
        frame[WEATHER_HISTORY_COLUMNS],
        schema=WEATHER_HISTORY_SCHEMA,
        preserve_index=False,
        safe=True,
    )
    writer.write_table(table, row_group_size=row_group_size)


def upsert_weather_history_parquet(
    history_path: Path,
    updates: pd.DataFrame,
    *,
    output_path: Path | None = None,
    batch_size: int = 65_536,
    row_group_size: int = 512,
) -> WeatherHistoryUpsertReport:
    """Stream an atomic non-null upsert into a canonical weather Parquet.

    The existing Parquet is read in bounded batches. It is never reconstructed
    from historical CSVs. The destination may be the history itself or a
    separate lab candidate.
    """
    history_path = Path(history_path)
    destination = Path(output_path) if output_path is not None else history_path
    if not history_path.is_file():
        raise FileNotFoundError(history_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    incoming = collapse_weather_history_updates(updates)
    incoming_indexed = incoming.set_index(WEATHER_HISTORY_KEY, drop=False)
    matched_keys: set[tuple[str, str, str]] = set()
    matched_rows = 0
    inserted_rows = 0
    old_rows = 0
    temporary_path = destination.with_name(
        f".{destination.name}.{uuid4().hex}.tmp"
    )
    writer: pq.ParquetWriter | None = None

    try:
        writer = pq.ParquetWriter(
            temporary_path,
            WEATHER_HISTORY_SCHEMA,
            compression="snappy",
            use_dictionary=True,
        )
        parquet_file = pq.ParquetFile(history_path)
        for batch in parquet_file.iter_batches(batch_size=batch_size):
            old_batch = normalize_weather_history_frame(batch.to_pandas())
            old_batch = old_batch.dropna(subset=WEATHER_HISTORY_KEY)
            old_keys = _key_tuples(old_batch)
            if not old_keys:
                continue
            old_rows += len(old_batch)

            old_key_index = pd.MultiIndex.from_tuples(
                old_keys,
                names=WEATHER_HISTORY_KEY,
            )
            matching_index = old_key_index.intersection(incoming_indexed.index)
            duplicate_matches = set(matching_index).intersection(matched_keys)
            if duplicate_matches:
                duplicate = sorted(duplicate_matches)[0]
                raise ValueError(
                    f"Canonical weather history contains duplicate key {duplicate!r}"
                )
            if matching_index.empty:
                merged = old_batch
            else:
                matched_keys.update(matching_index.tolist())
                matched_rows += len(matching_index)
                incoming_batch = incoming_indexed.loc[matching_index].reset_index(drop=True)
                merged = upsert_incremental(
                    incoming_batch,
                    old_batch,
                    key_columns=WEATHER_HISTORY_KEY,
                )
                merged = normalize_weather_history_frame(merged)
            _write_frame(writer, merged, row_group_size=row_group_size)

        remaining_index = incoming_indexed.index.difference(
            pd.MultiIndex.from_tuples(
                sorted(matched_keys),
                names=WEATHER_HISTORY_KEY,
            )
        )
        remaining = incoming_indexed.loc[remaining_index].reset_index(drop=True)
        if not remaining.empty:
            inserted_rows += len(remaining)
            _write_frame(writer, remaining, row_group_size=row_group_size)
        writer.close()
        writer = None

        expected_rows = old_rows + inserted_rows
        metadata = pq.ParquetFile(temporary_path).metadata
        if metadata.num_rows != expected_rows:
            raise AssertionError(
                f"Weather history row mismatch: expected {expected_rows}, got {metadata.num_rows}"
            )
        with temporary_path.open("rb") as handle:
            os.fsync(handle.fileno())
        temporary_path.replace(destination)
        return WeatherHistoryUpsertReport(
            old_rows=old_rows,
            update_rows=len(incoming),
            matched_rows=matched_rows,
            inserted_rows=inserted_rows,
            output_rows=metadata.num_rows,
            output_bytes=destination.stat().st_size,
            row_groups=metadata.num_row_groups,
        )
    except Exception:
        if writer is not None:
            writer.close()
        temporary_path.unlink(missing_ok=True)
        raise
