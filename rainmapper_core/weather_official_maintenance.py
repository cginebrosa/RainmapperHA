"""Detect and repair source-wide gaps in official partitioned weather history."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

import pandas as pd
import pyarrow as pa

from rainmapper_core.weather_history_dataset import write_json_atomic
from rainmapper_core.weather_history_pending import (
    build_pending_batch,
    list_pending_batches,
)
from rainmapper_core.weather_history_writer import (
    acknowledge_archived_pending,
    archive_pending_batches,
)
from rainmapper_core.weather_live_csv import apply_pending_to_live_csv
from rainmapper_core.weather_official_backfill import (
    fetch_aemet_climatology,
    fetch_meteocat_block,
    normalize_aemet_climatology,
    normalize_meteocat_block,
)
from rainmapper_core.weather_official_repair_state import (
    detect_and_enqueue_network_gaps,
    load_state,
    next_due,
    observed_network_days,
    record_attempt,
    write_state,
)


CATALOG_FILES = {
    "aemet": "estacions_aemet.csv",
    "meteocat": "estacions_xema.csv",
}
REPORT_FILENAME = "official-weather-gap-repair-report.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _frame_batches(frame: pd.DataFrame, chunk_rows: int = 8_192) -> Iterator[pa.Table]:
    for offset in range(0, len(frame), chunk_rows):
        yield pa.Table.from_pandas(
            frame.iloc[offset : offset + chunk_rows],
            preserve_index=False,
        )


def read_catalog(data_dir: Path, source: str) -> pd.DataFrame:
    path = Path(data_dir) / CATALOG_FILES[source]
    if not path.is_file():
        raise RuntimeError(f"Missing {source} station catalog: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def fetch_repair_frame(
    data_dir: Path,
    source: str,
    start: date,
    end: date,
    *,
    aemet_api_key: str | None,
    timeout: int,
) -> pd.DataFrame:
    catalog = read_catalog(data_dir, source)
    if source == "aemet":
        raw = fetch_aemet_climatology(
            start,
            end,
            api_key=aemet_api_key or "",
            timeout=timeout,
        )
        return normalize_aemet_climatology(raw, catalog)
    rain, conditions = fetch_meteocat_block(start, end, timeout=timeout)
    return normalize_meteocat_block(rain, conditions, catalog)


def repair_due_item(
    data_dir: Path,
    state: dict[str, Any],
    item: dict[str, Any],
    *,
    reference_day: date,
    aemet_api_key: str | None,
    timeout: int = 90,
    fetcher: Callable[..., pd.DataFrame] = fetch_repair_frame,
    attempted_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    attempted_at = attempted_at or utc_now()
    source = str(item["source"])
    start = date.fromisoformat(item["start_date"])
    end = date.fromisoformat(item["end_date"])
    expected = {start.fromordinal(start.toordinal() + offset) for offset in range((end - start).days + 1)}
    resumed_batches = []
    durable_pending = list_pending_batches(data_dir, source)
    if durable_pending:
        try:
            archive = archive_pending_batches(data_dir)
            applied = set(archive.batch_ids) | set(archive.already_applied_batch_ids)
            for pending in durable_pending:
                if pending.batch_id not in applied:
                    raise RuntimeError(
                        f"pending batch {pending.batch_id} has no durable archive receipt"
                    )
                live = apply_pending_to_live_csv(
                    data_dir,
                    pending,
                    reference_day=reference_day,
                )
                acknowledge_archived_pending(data_dir, pending.batch_id)
                resumed_batches.append(
                    {
                        "batch_id": pending.batch_id,
                        "generation_id": archive.generation_id,
                        "live_csv": live.to_dict(),
                    }
                )
        except Exception as exc:
            updated = record_attempt(
                state,
                item["id"],
                recovered_days=(),
                error=str(exc),
                attempted_at=attempted_at,
            )
            return updated, {
                "source": source,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "status": "retry_wait",
                "error": str(exc),
                "resumed_batches": resumed_batches,
            }
    already = observed_network_days(data_dir, source, start, end)
    if expected.issubset(already):
        updated = record_attempt(
            state,
            item["id"],
            recovered_days=expected,
            attempted_at=attempted_at,
        )
        return updated, {
            "source": source,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "status": "already_recovered",
            "recovered_days": len(expected),
            "resumed_batches": resumed_batches,
        }
    try:
        frame = fetcher(
            data_dir,
            source,
            start,
            end,
            aemet_api_key=aemet_api_key,
            timeout=timeout,
        )
        if frame.empty:
            raise RuntimeError("provider returned no modeled rows")
        pending = build_pending_batch(
            data_dir,
            source,
            _frame_batches(frame),
            run_id=f"automatic-gap-repair-{source}-{start.isoformat()}-{end.isoformat()}",
        )
        if pending is None:
            raise RuntimeError("normalized automatic repair batch is empty")
        archive = archive_pending_batches(data_dir)
        if not archive.committed and pending.batch_id not in archive.already_applied_batch_ids:
            raise RuntimeError("automatic repair batch was not archived")
        live = apply_pending_to_live_csv(data_dir, pending, reference_day=reference_day)
        acknowledge_archived_pending(data_dir, pending.batch_id)
        recovered = observed_network_days(data_dir, source, start, end)
        missing = sorted(expected - recovered)
        updated = record_attempt(
            state,
            item["id"],
            recovered_days=recovered,
            error=None if not missing else "provider_returned_no_rows_for_expected_day",
            attempted_at=attempted_at,
        )
        return updated, {
            "source": source,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "status": "resolved" if not missing else "partial",
            "input_rows": len(frame),
            "recovered_days": len(expected) - len(missing),
            "missing_days": [value.isoformat() for value in missing],
            "generation_id": archive.generation_id,
            "live_csv": live.to_dict(),
        }
    except Exception as exc:
        updated = record_attempt(
            state,
            item["id"],
            recovered_days=already,
            error=str(exc),
            attempted_at=attempted_at,
        )
        return updated, {
            "source": source,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "status": "retry_wait",
            "error": str(exc),
            "recovered_days": len(expected.intersection(already)),
        }


def run_maintenance(
    data_dir: Path,
    sources: Iterable[str],
    *,
    reference_day: date,
    aemet_api_key: str | None,
    timeout: int = 90,
) -> dict[str, Any]:
    data_dir = Path(data_dir)
    selected = sorted(set(sources))
    state = load_state(data_dir)
    due_before_detection = {
        source: next_due(state, source=source)
        for source in selected
    }
    attempts = []
    for source in selected:
        item = due_before_detection[source]
        if item is None:
            continue
        state, attempt = repair_due_item(
            data_dir,
            state,
            item,
            reference_day=reference_day,
            aemet_api_key=aemet_api_key,
            timeout=timeout,
        )
        write_state(data_dir, state)
        attempts.append(attempt)
    detected: dict[str, list[str]] = {}
    for source in selected:
        state, missing = detect_and_enqueue_network_gaps(
            state,
            data_dir,
            source,
            reference_day,
        )
        detected[source] = [value.isoformat() for value in missing]
    write_state(data_dir, state)
    selected_pending = [
        item for item in state.get("pending", []) if item.get("source") in selected
    ]
    report = {
        "schema_version": "official_weather_gap_repair_report_v1",
        "generated_at": utc_now().isoformat(),
        "reference_day": reference_day.isoformat(),
        "sources": selected,
        "attempts": attempts,
        "detected_missing_days": detected,
        "active": bool(selected_pending),
        "pending": selected_pending,
    }
    write_json_atomic(data_dir / "weather-history" / REPORT_FILENAME, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--source", action="append", choices=("aemet", "meteocat"), required=True)
    parser.add_argument("--reference-day", type=date.fromisoformat, default=date.today())
    parser.add_argument("--timeout", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_maintenance(
        args.data_dir,
        args.source,
        reference_day=args.reference_day,
        aemet_api_key=os.environ.get("RAINMAPPER_AEMET_API_KEY") or os.environ.get("AEMET_API_KEY"),
        timeout=args.timeout,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 2 if report["active"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
