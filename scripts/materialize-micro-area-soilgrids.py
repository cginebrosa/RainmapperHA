#!/usr/bin/env python3
"""Materialize SoilGrids context into a distinct known-sites candidate file."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_known_sites, mushroom_soilgrids
from rainmapper_core.mushroom_store import write_json_atomic


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--known-sites", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--micro-area", action="append", dest="micro_area_ids")
    parser.add_argument(
        "--ensure-cache",
        action="store_true",
        help="Download and validate missing WCS tiles before aggregation.",
    )
    return parser.parse_args()


def _error_context(geometry: object, exc: Exception) -> dict[str, Any]:
    try:
        polygons = mushroom_soilgrids.transform_geometry(geometry)
        tile_ids = mushroom_soilgrids.tile_ids_for_geometry(polygons)
    except Exception:
        tile_ids = []
    context = mushroom_soilgrids.pending_context(
        geometry,
        tile_ids=tile_ids,
        reasons=["soilgrids_resolution_error"],
    )
    context["quality"]["error_type"] = type(exc).__name__
    context["quality"]["error"] = str(exc)
    return context


def main() -> int:
    args = parse_args()
    source = args.known_sites.resolve()
    destination = args.output.resolve()
    if source == destination:
        raise ValueError("SoilGrids materialization requires a distinct output file.")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("known_sites must contain an object.")
    validation_errors = mushroom_known_sites.validate_payload(payload)
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    candidate = copy.deepcopy(payload)
    selected = set(args.micro_area_ids or [])
    cache_root = args.cache_root or mushroom_soilgrids.default_cache_root()
    rows: list[dict[str, Any]] = []
    candidate_micro_areas = candidate.get("micro_areas", [])
    eligible_total = sum(
        1
        for value in candidate_micro_areas
        if isinstance(value, dict)
        and (not selected or str(value.get("micro_area_id") or "") in selected)
    )
    for micro_area in candidate_micro_areas:
        if not isinstance(micro_area, dict):
            continue
        micro_area_id = str(micro_area.get("micro_area_id") or "")
        if selected and micro_area_id not in selected:
            continue
        geometry = micro_area.get("geometry")
        if not isinstance(geometry, dict):
            rows.append(
                {
                    "micro_area_id": micro_area_id,
                    "status": "skipped",
                    "reason": "missing_geometry",
                }
            )
            continue
        cache_result = None
        try:
            if args.ensure_cache:
                cache_result = mushroom_soilgrids.ensure_geometry_cache(
                    cache_root, geometry
                )
            context = mushroom_soilgrids.aggregate_geometry(cache_root, geometry)
        except Exception as exc:
            context = _error_context(geometry, exc)
        mushroom_soilgrids.apply_micro_area_context(micro_area, context)
        rows.append(
            {
                "micro_area_id": micro_area_id,
                "status": context["status"],
                "coverage_fraction": context.get("coverage_fraction"),
                "cache": cache_result,
                "exclusion_reasons": list(
                    (context.get("quality") or {}).get("exclusion_reasons") or []
                ),
                "soilgrids_water_context": copy.deepcopy(context),
            }
        )
        print(
            json.dumps(
                {
                    "completed": len(rows),
                    "total": eligible_total,
                    "micro_area_id": micro_area_id,
                    "status": context["status"],
                    "coverage_fraction": context.get("coverage_fraction"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    missing_requested = sorted(
        selected - {str(row.get("micro_area_id") or "") for row in rows}
    )
    if missing_requested:
        raise ValueError(f"Unknown micro-area: {missing_requested[0]}")
    candidate_errors = mushroom_known_sites.validate_payload(candidate)
    if candidate_errors:
        raise ValueError("; ".join(candidate_errors))
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(destination, candidate)
    statuses = Counter(str(row["status"]) for row in rows)
    report = {
        "schema_version": "1.0",
        "kind": "microarea_soilgrids_materialization_report",
        "input": str(source),
        "input_sha256": mushroom_soilgrids.file_sha256(source),
        "output": str(destination),
        "output_sha256": mushroom_soilgrids.file_sha256(destination),
        "cache_root": str(cache_root),
        "ensure_cache": bool(args.ensure_cache),
        "summary": {
            "processed": len(rows),
            "statuses": dict(sorted(statuses.items())),
        },
        "micro_areas": rows,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(args.report, report)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "micro_areas"},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
