"""Short-lived CLI that archives pending weather batches and closes their CSVs."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from rainmapper_core.weather_history_dataset import resolve_weather_generation
from rainmapper_core.weather_history_pending import list_pending_batches
from rainmapper_core.weather_live_csv import apply_pending_to_live_csv
from rainmapper_core.weather_history_writer import (
    acknowledge_archived_pending,
    archive_pending_batches,
)


def archive_and_close_pending(data_dir: Path) -> dict[str, Any]:
    """Archive pending, reapply it to the bounded live CSV, then acknowledge."""
    report = archive_pending_batches(Path(data_dir))
    generation = resolve_weather_generation(Path(data_dir))
    manifest = json.loads(generation.manifest_path.read_text(encoding="utf-8"))
    receipts = set(manifest.get("update_report", {}).get("batch_ids", []))
    acknowledged: list[str] = []
    csv_reports: list[dict[str, Any]] = []
    reference_text = os.environ.get("RAINMAPPER_WEATHER_REFERENCE_DAY", "").strip()
    reference_day = date.fromisoformat(reference_text) if reference_text else None
    for pending in list_pending_batches(Path(data_dir)):
        if pending.batch_id not in receipts:
            continue
        csv_report = apply_pending_to_live_csv(
            Path(data_dir),
            pending,
            reference_day=reference_day,
        )
        csv_reports.append(csv_report.to_dict())
        acknowledge_archived_pending(Path(data_dir), pending.batch_id)
        acknowledged.append(pending.batch_id)
    return {
        **report.to_dict(),
        "acknowledged_batch_ids": acknowledged,
        "live_csv_reports": csv_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(archive_and_close_pending(args.data_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
