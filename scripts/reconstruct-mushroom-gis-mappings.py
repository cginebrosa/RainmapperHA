#!/usr/bin/env python3
"""Build a batch GIS mapping candidate payload for the mushroom lab.

The script scans every unique value from the configured local GIS layer fields
and writes the same reconstruction payload consumed by `/mushrooms/gis-mappings`.
It is deliberately read-only for GIS layers, catalogs and mappings: existing
exact mappings are skipped, and text-pattern matches are emitted only as review
suggestions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_gis_lab  # noqa: E402


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def default_mushroom_data_root() -> Path:
    """Prefer the mutable local lab copy, then fall back to versioned defaults."""
    local_root = REPO_ROOT / "docker-data" / "mushroom-data"
    if (local_root / "mushroom_gis_mappings.json").exists() and (local_root / "mushroom_reference_catalogs.json").exists():
        return local_root
    return REPO_ROOT / "mushroom-data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mushroom_gis_mappings_rebuild.sh",
        description="Rebuild batch GIS mapping candidates for the mushroom lab UI.",
        epilog=(
            "Default output uses RAINMAPPER_MUSHROOM_GIS_RECONSTRUCTION_PATH when set, "
            "then RAINMAPPER_MUSHROOM_LAB_DIR, then /share/rainmapper/mushroom-lab "
            "inside Home Assistant, then docker-data/mushroom-lab in local labs."
        ),
    )
    parser.add_argument(
        "--mushroom-data-root",
        type=Path,
        default=default_mushroom_data_root(),
        help="Directory containing mushroom_gis_mappings.json and mushroom_reference_catalogs.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=mushroom_gis_lab.default_output_path(),
        help="Output reconstruction JSON path consumed by /mushrooms/gis-mappings.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_root = args.mushroom_data_root
    gis_path = data_root / "mushroom_gis_mappings.json"
    catalogs_path = data_root / "mushroom_reference_catalogs.json"
    if not gis_path.exists():
        print(f"Missing GIS mappings file: {gis_path}", file=sys.stderr)
        return 2
    if not catalogs_path.exists():
        print(f"Missing reference catalogs file: {catalogs_path}", file=sys.stderr)
        return 2

    payload = mushroom_gis_lab.reconstruct_all_gis_mapping_candidates(
        output_path=args.output,
        gis_payload=read_json(gis_path),
        catalogs_payload=read_json(catalogs_path),
    )

    print(f"Wrote: {args.output}")
    print(f"Mushroom data root: {data_root}")
    for row in payload.get("field_summaries", []):
        if not isinstance(row, dict):
            continue
        print(
            "{source_id}.{field}: unique={unique_values} existing={existing_exact_mappings} "
            "candidates={candidate_values} suggested={suggested_values} duration={duration_seconds}s".format(**row)
        )
    print(f"Candidate rows: {len(payload.get('unmapped_candidates', []))}")
    print(f"Total duration: {payload.get('duration_seconds')}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
