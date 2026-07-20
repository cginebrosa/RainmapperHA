#!/usr/bin/env python3
"""Run the shared mushroom V0 rebuild into an isolated output directory."""

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
    mushroom_rebuild_pipeline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the existing four-phase mushroom V0 rebuild with explicit inputs "
            "and isolated outputs. This CLI never writes to the live mushroom-data directory."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--observations", type=Path, default=mushroom_paths.mushroom_observations_path())
    parser.add_argument(
        "--reference-catalogs",
        type=Path,
        default=mushroom_paths.mushroom_reference_catalogs_path(),
    )
    parser.add_argument(
        "--gis-mappings",
        type=Path,
        default=mushroom_paths.mushroom_data_file("mushroom_gis_mappings.json"),
    )
    parser.add_argument("--weather-data-dir", type=Path, default=mushroom_paths.weather_data_dir())
    parser.add_argument("--gis-root", type=Path, default=mushroom_gis_lab.gis_root())
    parser.add_argument(
        "--observation-id",
        action="append",
        default=[],
        help="Reconstruct only this observation ID; repeat for more than one. Defaults to all eligible.",
    )
    parser.add_argument(
        "--pending-species-id",
        action="append",
        default=[],
        help="Rebuild and merge only this species model; repeat for more than one.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print resolved paths without running phases.")
    parser.add_argument("--quiet", action="store_true", help="Suppress incremental progress output.")
    return parser.parse_args()


def paths_overlap(first: Path, second: Path) -> bool:
    first = first.resolve()
    second = second.resolve()
    return first == second or first in second.parents or second in first.parents


def validate_isolated_outputs(
    inputs: mushroom_rebuild_pipeline.RebuildInputPaths,
    outputs: mushroom_rebuild_pipeline.RebuildOutputPaths,
) -> None:
    live_data_dir = mushroom_paths.mushroom_data_dir().resolve()
    if paths_overlap(outputs.root, live_data_dir):
        raise ValueError(f"output directory must not overlap live mushroom data: {live_data_dir}")
    for label, raw_path in inputs.as_dict().items():
        if paths_overlap(outputs.root, Path(raw_path)):
            raise ValueError(f"output directory must not overlap {label}: {raw_path}")
    existing_outputs = [Path(path) for key, path in outputs.as_dict().items() if key != "root" and Path(path).exists()]
    result_path = outputs.root / "rebuild_result.json"
    if result_path.exists():
        existing_outputs.append(result_path)
    if existing_outputs:
        raise FileExistsError(f"refusing to overwrite existing rebuild outputs: {existing_outputs[0]}")


def main() -> int:
    args = parse_args()
    inputs = mushroom_rebuild_pipeline.RebuildInputPaths(
        observations=args.observations.resolve(),
        reference_catalogs=args.reference_catalogs.resolve(),
        gis_mappings=args.gis_mappings.resolve(),
        weather_data_dir=args.weather_data_dir.resolve(),
        gis_root=args.gis_root.resolve(),
    )
    outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(args.output_dir)
    try:
        validate_isolated_outputs(inputs, outputs)
    except (FileExistsError, ValueError) as exc:
        print(f"Safety check failed: {exc}", file=sys.stderr)
        return 2

    plan = {
        "inputs": inputs.as_dict(),
        "outputs": outputs.as_dict(),
        "selected_observation_ids": args.observation_id,
        "pending_species_ids": args.pending_species_id,
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    def report_progress(event: dict[str, object]) -> None:
        if args.quiet:
            return
        print(
            "[{overall_percent:3}%] {phase} {phase_percent:3}% - {message}".format(**event),
            file=sys.stderr,
            flush=True,
        )

    result = mushroom_rebuild_pipeline.run_rebuild(
        inputs,
        outputs,
        selected_observation_ids=args.observation_id or None,
        pending_species_ids=args.pending_species_id or None,
        progress_callback=report_progress,
    )
    result_path = outputs.root / "rebuild_result.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
