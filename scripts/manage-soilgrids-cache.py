#!/usr/bin/env python3
"""Create, extend, and verify the local SoilGrids tile cache."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_soilgrids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("record-capabilities", "ensure-known-sites", "verify")
    )
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--known-sites", type=Path)
    parser.add_argument("--micro-area", action="append", dest="micro_area_ids")
    parser.add_argument("--margin-tiles", type=int, default=0)
    parser.add_argument(
        "--coverage",
        action="append",
        dest="coverage_ids",
        help="Limit cache creation to one or more declared coverage IDs.",
    )
    return parser.parse_args()


def known_sites_tiles(path: Path, selected: set[str]) -> tuple[list[str], int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tile_ids: set[str] = set()
    processed = 0
    found_ids: set[str] = set()
    for row in payload.get("micro_areas", []):
        if not isinstance(row, dict):
            continue
        micro_area_id = str(row.get("micro_area_id") or "")
        if selected and micro_area_id not in selected:
            continue
        found_ids.add(micro_area_id)
        geometry = row.get("geometry")
        if not isinstance(geometry, dict):
            continue
        polygons = mushroom_soilgrids.transform_geometry(geometry)
        tile_ids.update(mushroom_soilgrids.tile_ids_for_geometry(polygons))
        processed += 1
    missing = sorted(selected - found_ids)
    if missing:
        raise ValueError(f"Unknown micro-area: {missing[0]}")
    return sorted(tile_ids), processed


def verify(cache_root: Path) -> dict[str, int]:
    manifest = mushroom_soilgrids.load_manifest(cache_root)
    checked = 0
    invalid = 0
    observed_hashes: dict[Path, str] = {}
    for coverage, coverage_row in manifest["coverages"].items():
        for tile_id, tile in coverage_row["tiles"].items():
            checked += 1
            try:
                raw = cache_root / tile["raw_path"]
                normalized = cache_root / tile["normalized_path"]
                if raw not in observed_hashes:
                    observed_hashes[raw] = mushroom_soilgrids.file_sha256(raw)
                raw_hash = observed_hashes[raw]
                if raw_hash != tile["raw_sha256"]:
                    raise ValueError("raw hash mismatch")
                if normalized not in observed_hashes:
                    observed_hashes[normalized] = mushroom_soilgrids.file_sha256(
                        normalized
                    )
                normalized_hash = observed_hashes[normalized]
                if normalized_hash != tile["normalized_sha256"]:
                    raise ValueError("normalized hash mismatch")
                mushroom_soilgrids.validate_raster(
                    normalized,
                    mushroom_soilgrids.tile_bbox(tile_id),
                    require_crs=True,
                )
            except Exception as exc:
                invalid += 1
                print(
                    json.dumps(
                        {
                            "status": "invalid",
                            "coverage_id": coverage,
                            "tile_id": tile_id,
                            "error": str(exc),
                        }
                    ),
                    flush=True,
                )
    return {"checked": checked, "invalid": invalid}


def main() -> int:
    args = parse_args()
    if args.command == "record-capabilities":
        hashes = mushroom_soilgrids.record_capabilities(args.cache_root)
        print(json.dumps({"status": "complete", "hashes": hashes}, indent=2))
        return 0
    if args.command == "verify":
        summary = verify(args.cache_root)
        print(json.dumps({"status": "complete", **summary}, indent=2))
        return 1 if summary["invalid"] else 0
    if args.known_sites is None:
        raise ValueError("--known-sites is required for ensure-known-sites.")
    occupied_tile_ids, micro_area_count = known_sites_tiles(
        args.known_sites, set(args.micro_area_ids or [])
    )
    reserve_tile_ids = mushroom_soilgrids.expand_tile_rectangle(
        occupied_tile_ids, args.margin_tiles
    )
    required_coverages = mushroom_soilgrids.required_coverage_ids()
    coverage_ids = args.coverage_ids or required_coverages
    unsupported = sorted(set(coverage_ids) - set(required_coverages))
    if unsupported:
        raise ValueError(f"Unsupported SoilGrids coverage: {unsupported[0]}")
    # A single representative topsoil layer classifies completely empty sea
    # positions. Current occupied tiles are always retained, regardless of mask.
    if args.margin_tiles and mushroom_soilgrids.LAND_MASK_COVERAGE_ID not in coverage_ids:
        mushroom_soilgrids.ensure_tiles_bulk(
            args.cache_root,
            mushroom_soilgrids.LAND_MASK_COVERAGE_ID,
            reserve_tile_ids,
        )
    if args.margin_tiles:
        manifest = mushroom_soilgrids.load_manifest(args.cache_root)
        land_tile_ids, empty_tile_ids = mushroom_soilgrids.land_tile_ids_from_manifest(
            manifest, reserve_tile_ids
        )
        tile_ids = sorted(
            set(land_tile_ids) | set(occupied_tile_ids),
            key=mushroom_soilgrids.tile_indices,
        )
    else:
        tile_ids = reserve_tile_ids
        empty_tile_ids = []
    total = sum(
        len(reserve_tile_ids)
        if coverage == mushroom_soilgrids.LAND_MASK_COVERAGE_ID and args.margin_tiles
        else len(tile_ids)
        for coverage in coverage_ids
    )
    completed = 0
    counts = {"downloaded": 0, "reused": 0}
    for coverage in coverage_ids:
        coverage_tile_ids = (
            reserve_tile_ids
            if coverage == mushroom_soilgrids.LAND_MASK_COVERAGE_ID
            and args.margin_tiles
            else tile_ids
        )
        outcome = mushroom_soilgrids.ensure_tiles_bulk(
            args.cache_root, coverage, coverage_tile_ids
        )
        completed += len(coverage_tile_ids)
        counts["downloaded"] += outcome["downloaded"]
        counts["reused"] += outcome["reused"]
        print(
            json.dumps(
                {
                    "completed": completed,
                    "total": total,
                    "coverage_id": coverage,
                    "downloaded": outcome["downloaded"],
                    "reused": outcome["reused"],
                    "batch_id": outcome.get("batch_id"),
                }
            ),
            flush=True,
        )
    print(
        json.dumps(
            {
                "status": "complete",
                "micro_area_count": micro_area_count,
                "occupied_tile_ids": occupied_tile_ids,
                "reserve_tile_ids": reserve_tile_ids,
                "tile_ids": tile_ids,
                "empty_reference_tile_ids": empty_tile_ids,
                "coverage_count": len(coverage_ids),
                **counts,
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
