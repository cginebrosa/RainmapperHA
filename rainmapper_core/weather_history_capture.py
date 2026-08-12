"""Feature-gated capture of fresh source data into immutable pending batches."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

import pyarrow as pa

from rainmapper_core.weather_history_pending import PendingBatch, build_pending_batch


PARTITIONED_HISTORY_ENV = "RAINMAPPER_PARTITIONED_WEATHER_HISTORY"
WEATHER_RUN_ID_ENV = "RAINMAPPER_WEATHER_RUN_ID"


def partitioned_history_enabled() -> bool:
    return os.environ.get(PARTITIONED_HISTORY_ENV, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def weather_run_id() -> str:
    configured = os.environ.get(WEATHER_RUN_ID_ENV, "").strip()
    if configured:
        return configured
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + f"-pid{os.getpid()}"


def _frame_batches(frame, chunk_rows: int) -> Iterator[pa.Table]:
    for offset in range(0, len(frame), chunk_rows):
        yield pa.Table.from_pandas(
            frame.iloc[offset : offset + chunk_rows],
            preserve_index=False,
        )


def capture_fresh_weather_rows(
    data_dir: Path,
    source: str,
    frame,
    *,
    chunk_rows: int = 8_192,
) -> PendingBatch | None:
    """Capture only the fresh/rebuilt rows, before the live daily CSV write."""
    if not partitioned_history_enabled() or frame is None or frame.empty:
        return None
    return build_pending_batch(
        Path(data_dir),
        source,
        _frame_batches(frame, chunk_rows),
        run_id=weather_run_id(),
        chunk_rows=chunk_rows,
        row_group_size=chunk_rows,
    )
