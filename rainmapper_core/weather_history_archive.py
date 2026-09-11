"""Short-lived CLI that archives pending weather batches and closes their CSVs."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from rainmapper_core.weather_history_dataset import resolve_weather_generation, write_json_atomic
from rainmapper_core.weather_history_pending import list_pending_batches
from rainmapper_core.weather_live_csv import apply_pending_to_live_csv
from rainmapper_core.weather_history_writer import (
    acknowledge_archived_pending,
    archive_pending_batches,
    prune_weather_generations,
)


SOURCE_STATUS_NAMES = {
    "aemet": "AEMET",
    "meteocat": "Meteocat",
    "meteoclimatic": "Meteoclimatic",
    "wunderground": "Wunderground",
}


def update_source_status_counts(
    data_dir: Path,
    csv_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Publish archive row counts without rescanning the live weather CSVs."""
    status_path = Path(data_dir) / "source_status.json"
    if not status_path.exists():
        return {"updated": False, "sources": [], "reason": "source_status_missing"}

    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"updated": False, "sources": [], "reason": f"source_status_unreadable: {exc}"}
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), dict):
        return {"updated": False, "sources": [], "reason": "source_status_invalid"}

    updated_sources: list[str] = []
    sources = payload["sources"]
    for report in csv_reports:
        source = SOURCE_STATUS_NAMES.get(str(report.get("source") or "").lower())
        source_payload = sources.get(source) if source else None
        if not isinstance(source_payload, dict):
            continue
        try:
            total_rows = int(report["retained_rows"])
            updated_rows = int(report["pending_rows"])
        except (KeyError, TypeError, ValueError):
            continue
        source_payload["rows"] = total_rows
        source_payload["total_rows"] = total_rows
        source_payload["updated_rows"] = updated_rows
        updated_sources.append(source)

    if updated_sources:
        write_json_atomic(status_path, payload)
    return {"updated": bool(updated_sources), "sources": updated_sources}


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
    source_status_report = update_source_status_counts(Path(data_dir), csv_reports)
    cleanup_report = prune_weather_generations(Path(data_dir))
    return {
        **report.to_dict(),
        "acknowledged_batch_ids": acknowledged,
        "live_csv_reports": csv_reports,
        "source_status": source_status_report,
        "generation_cleanup": {
            "kept_generation_ids": list(cleanup_report.kept_generation_ids),
            "removed_generation_ids": list(cleanup_report.removed_generation_ids),
            "active_lease_generation_ids": list(cleanup_report.active_lease_generation_ids),
            "expired_leases_removed": cleanup_report.expired_leases_removed,
            "manifests_removed": cleanup_report.manifests_removed,
            "objects_removed": cleanup_report.objects_removed,
            "bytes_removed": cleanup_report.bytes_removed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(archive_and_close_pending(args.data_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
