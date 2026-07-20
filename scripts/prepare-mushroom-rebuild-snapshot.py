#!/usr/bin/env python3
"""Create or verify a private, reproducible mushroom rebuild input snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import (  # noqa: E402
    mushroom_gis_lab,
    mushroom_paths,
    mushroom_rebuild_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="Create a new immutable input snapshot.")
    create.add_argument("--snapshot-dir", type=Path, required=True)
    create.add_argument("--observations", type=Path, default=mushroom_paths.mushroom_observations_path())
    create.add_argument(
        "--reference-catalogs",
        type=Path,
        default=mushroom_paths.mushroom_reference_catalogs_path(),
    )
    create.add_argument(
        "--gis-mappings",
        type=Path,
        default=mushroom_paths.mushroom_data_file("mushroom_gis_mappings.json"),
    )
    create.add_argument("--weather-data-dir", type=Path, default=mushroom_paths.weather_data_dir())
    create.add_argument("--gis-root", type=Path, default=mushroom_gis_lab.gis_root())

    verify = subparsers.add_parser("verify", help="Verify snapshot and GIS dataset hashes.")
    verify.add_argument("--snapshot-dir", type=Path, required=True)
    verify.add_argument("--gis-root", type=Path)

    materialize = subparsers.add_parser(
        "materialize-ha-test",
        help="Create an isolated HA-like runtime from a verified snapshot.",
    )
    materialize.add_argument("--snapshot-dir", type=Path, required=True)
    materialize.add_argument("--runtime-dir", type=Path, required=True)
    materialize.add_argument("--gis-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "create":
        try:
            manifest = mushroom_rebuild_snapshot.create_snapshot(
                args.snapshot_dir,
                observations_path=args.observations,
                reference_catalogs_path=args.reference_catalogs,
                gis_mappings_path=args.gis_mappings,
                weather_data_dir=args.weather_data_dir,
                gis_root=args.gis_root,
            )
        except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
            print(f"Snapshot creation failed: {exc}", file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "status": "created",
                    "snapshot_dir": str(args.snapshot_dir.resolve()),
                    "snapshot_id": manifest["snapshot_id"],
                    "snapshot_files": len(manifest["files"]),
                    "gis_files": len(manifest["datasets"][0]["files"]),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "materialize-ha-test":
        try:
            result = mushroom_rebuild_snapshot.materialize_ha_test_runtime(
                args.snapshot_dir,
                args.runtime_dir,
                gis_root_override=args.gis_root,
            )
        except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
            print(f"HA test runtime materialization failed: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    try:
        result = mushroom_rebuild_snapshot.verify_snapshot(
            args.snapshot_dir,
            gis_root_override=args.gis_root,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"Snapshot verification failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
