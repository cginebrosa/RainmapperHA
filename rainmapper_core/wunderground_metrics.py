"""Bounded diagnostic history for Wunderground station requests."""

from __future__ import annotations

import csv
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Mapping


FIELDNAMES = [
    "id_ejecucion",
    "timestamp_lectura",
    "fecha_lectura",
    "hora_lectura",
    "codi_estacio",
    "estacion",
    "url",
    "tiempo_lectura_s",
    "ok",
    "filas",
    "ultimo_error",
]
DEFAULT_RETENTION_DAYS = 30


def _row_date(row: Mapping[str, object]) -> date | None:
    raw_day = str(row.get("fecha_lectura") or "").strip()
    if raw_day:
        try:
            return datetime.strptime(raw_day, "%Y%m%d").date()
        except ValueError:
            pass

    raw_timestamp = str(row.get("timestamp_lectura") or "").strip()
    if raw_timestamp:
        try:
            return datetime.fromisoformat(raw_timestamp).date()
        except ValueError:
            pass
    return None


def _write_atomic(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def save_metrics(
    path: str | Path,
    new_rows: Iterable[Mapping[str, object]],
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    today: date | None = None,
) -> dict[str, object]:
    """Append diagnostic rows while retaining a bounded calendar window."""
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")

    path = Path(path)
    today = today or date.today()
    cutoff = today - timedelta(days=retention_days - 1)
    retained: list[dict[str, object]] = []
    input_rows = 0
    malformed_rows = 0

    if path.exists() and path.stat().st_size:
        with path.open("r", newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                input_rows += 1
                row_day = _row_date(row)
                if row_day is None:
                    malformed_rows += 1
                    continue
                if row_day >= cutoff:
                    retained.append(row)

    appended = list(new_rows)
    retained.extend(appended)
    _write_atomic(path, retained)
    return {
        "path": str(path),
        "retention_days": retention_days,
        "cutoff_date": cutoff.isoformat(),
        "input_rows": input_rows,
        "appended_rows": len(appended),
        "retained_rows": len(retained),
        "dropped_rows": input_rows - (len(retained) - len(appended)),
        "malformed_rows_dropped": malformed_rows,
        "output_bytes": path.stat().st_size,
    }
