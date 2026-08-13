#!/usr/bin/env python3
"""Materialize cached DEM altitudes for known-site micro-areas.

The command deliberately requires a distinct output path so audits cannot
overwrite the authoritative known-sites file by accident.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_gis_lab


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--known-sites", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gis-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.known_sites.resolve() == args.output.resolve():
        raise SystemExit("--output must differ from --known-sites")
    payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    rows = payload.get("micro_areas")
    if not isinstance(rows, list):
        raise SystemExit("known-sites payload has no micro_areas list")

    statuses: Counter[str] = Counter()
    source_samples: Counter[str] = Counter()
    materialized = 0
    for row in rows:
        if not isinstance(row, dict) or not row.get("geometry"):
            statuses["missing_geometry"] += 1
            continue
        report = mushroom_gis_lab.materialize_micro_area_dem_altitude(
            row, args.gis_root
        )
        status = str(report.get("dem_status") or "unknown")
        statuses[status] += 1
        if status == "ok":
            materialized += 1
        for source_id, count in (report.get("dem_source_counts") or {}).items():
            source_samples[str(source_id)] += int(count)

    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata["micro_area_dem_altitudes_materialized"] = materialized
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "input": str(args.known_sites),
                "output": str(args.output),
                "micro_area_count": len(rows),
                "materialized": materialized,
                "statuses": dict(sorted(statuses.items())),
                "dem_source_samples": dict(sorted(source_samples.items())),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
