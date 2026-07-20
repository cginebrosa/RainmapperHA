#!/usr/bin/env python3
"""Create, run and verify a contract-driven local mushroom rebuild job."""

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
    mushroom_rebuild_contracts,
    mushroom_rebuild_pipeline,
    mushroom_rebuild_snapshot,
    mushroom_worker_dataset_cache,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-spec", help="Create JobSpec 0.1 from a snapshot.")
    create.add_argument("--snapshot-dir", type=Path, required=True)
    create.add_argument("--job-spec", type=Path, required=True)
    create.add_argument("--gis-root", type=Path)
    create.add_argument(
        "--scope",
        choices=sorted(mushroom_rebuild_contracts.SUPPORTED_SCOPES),
        default="all",
    )
    create.add_argument("--observation-id", action="append", default=[])
    create.add_argument("--pending-species-id", action="append", default=[])

    run = subparsers.add_parser("run", help="Verify JobSpec and run it into an isolated directory.")
    run.add_argument("--snapshot-dir", type=Path, required=True)
    run.add_argument("--job-spec", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--gis-root", type=Path)
    run.add_argument(
        "--worker-data-dir",
        type=Path,
        help="Use and shallowly validate the active persistent worker GIS cache.",
    )
    run.add_argument("--quiet", action="store_true")
    run.add_argument(
        "--progress-jsonl",
        type=Path,
        help="Append machine-readable progress events for a supervising worker.",
    )

    verify_job = subparsers.add_parser("verify-spec", help="Verify JobSpec and all input hashes.")
    verify_job.add_argument("--snapshot-dir", type=Path, required=True)
    verify_job.add_argument("--job-spec", type=Path, required=True)
    verify_job.add_argument("--gis-root", type=Path)

    verify_result = subparsers.add_parser(
        "verify-result",
        help="Verify ResultManifest and all output hashes.",
    )
    verify_result.add_argument("--job-spec", type=Path, required=True)
    verify_result.add_argument("--output-dir", type=Path, required=True)
    verify_result.add_argument("--result-manifest", type=Path)
    return parser.parse_args()


def paths_overlap(first: Path, second: Path) -> bool:
    left = first.resolve()
    right = second.resolve()
    return left == right or left in right.parents or right in left.parents


def validate_output_dir(output_dir: Path, snapshot_dir: Path, gis_root: Path) -> None:
    output = output_dir.resolve()
    for label, protected in (
        ("snapshot", snapshot_dir.resolve()),
        ("GIS dataset", gis_root.resolve()),
        ("live mushroom data", mushroom_paths.mushroom_data_dir().resolve()),
    ):
        if paths_overlap(output, protected):
            raise ValueError(f"output directory must not overlap {label}: {protected}")
    if output.exists() and not output.is_dir():
        raise ValueError(f"output path must be a directory: {output}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output directory must be absent or empty: {output}")


def print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> int:
    args = parse_args()
    try:
        if args.command == "create-spec":
            verification = mushroom_rebuild_snapshot.verify_snapshot(
                args.snapshot_dir,
                gis_root_override=args.gis_root,
            )
            if verification["status"] != "valid":
                print_json(verification)
                return 1
            job_spec = mushroom_rebuild_contracts.create_job_spec(
                args.snapshot_dir,
                reconstruction_scope=args.scope,
                selected_observation_ids=args.observation_id or None,
                pending_species_ids=args.pending_species_id or None,
            )
            contract_verification = mushroom_rebuild_contracts.verify_job_spec(
                job_spec,
                args.snapshot_dir,
                gis_root_override=args.gis_root,
                verify_snapshot_files=False,
            )
            if contract_verification["status"] != "valid":
                print_json(contract_verification)
                return 1
            mushroom_rebuild_contracts.write_manifest(args.job_spec, job_spec)
            print_json(
                {
                    "status": "created",
                    "job_spec": str(args.job_spec.resolve()),
                    "job_id": job_spec["job_id"],
                    "job_spec_id": job_spec["job_spec_id"],
                    "snapshot_id": job_spec["input"]["snapshot_id"],
                    "selected_observations": len(
                        job_spec["scope"]["selected_observation_ids"]
                    ),
                    "dataset_requirements": len(job_spec["dataset_requirements"]),
                    "expected_artifacts": len(job_spec["expected_artifacts"]),
                }
            )
            return 0

        job_spec = mushroom_rebuild_contracts.load_job_spec(args.job_spec)
        if args.command == "verify-spec":
            result = mushroom_rebuild_contracts.verify_job_spec(
                job_spec,
                args.snapshot_dir,
                gis_root_override=args.gis_root,
            )
            print_json(result)
            return 0 if result["status"] == "valid" else 1

        if args.command == "verify-result":
            manifest_path = args.result_manifest or (
                args.output_dir / mushroom_rebuild_contracts.RESULT_MANIFEST_NAME
            )
            result_manifest = mushroom_rebuild_contracts.load_result_manifest(manifest_path)
            result = mushroom_rebuild_contracts.verify_result_manifest(
                result_manifest,
                job_spec,
                args.output_dir,
            )
            print_json(result)
            return 0 if result["status"] == "valid" else 1

        input_manifest = mushroom_rebuild_snapshot.load_manifest(args.snapshot_dir)
        dataset = input_manifest["datasets"][0]
        verify_gis_file_hashes = True
        if args.worker_data_dir is not None:
            cache = mushroom_worker_dataset_cache.resolve_current(args.worker_data_dir)
            requirements = {
                row["dataset_id"]: row["fingerprint"]
                for row in job_spec["dataset_requirements"]
            }
            required_fingerprint = requirements.get(mushroom_worker_dataset_cache.DEFAULT_DATASET_ID)
            if cache["fingerprint"] != required_fingerprint:
                raise ValueError("active GIS cache fingerprint does not match JobSpec")
            cached_gis_root = Path(cache["path"])
            if args.gis_root is not None and args.gis_root.resolve() != cached_gis_root.resolve():
                raise ValueError("--gis-root does not point to the active worker GIS cache")
            gis_root = cached_gis_root
            verify_gis_file_hashes = False
        else:
            gis_root = args.gis_root or Path(str(dataset["root_path"]))
        verification = mushroom_rebuild_contracts.verify_job_spec(
            job_spec,
            args.snapshot_dir,
            gis_root_override=gis_root,
            verify_gis_file_hashes=verify_gis_file_hashes,
        )
        if verification["status"] != "valid":
            print_json(verification)
            return 1
        validate_output_dir(args.output_dir, args.snapshot_dir, gis_root)
        resolved = mushroom_rebuild_snapshot.resolved_input_paths(args.snapshot_dir, input_manifest)
        inputs = mushroom_rebuild_pipeline.RebuildInputPaths(
            observations=resolved["observations"],
            reference_catalogs=resolved["reference_catalogs"],
            gis_mappings=resolved["gis_mappings"],
            weather_data_dir=resolved["weather_data_dir"],
            gis_root=gis_root.resolve(),
        )
        outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(args.output_dir)
        scope = job_spec["scope"]

        def report_progress(event: dict[str, object]) -> None:
            if args.progress_jsonl is not None:
                args.progress_jsonl.parent.mkdir(parents=True, exist_ok=True)
                with args.progress_jsonl.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")
                    handle.flush()
            if not args.quiet:
                print(
                    "[{overall_percent:3}%] {phase} {phase_percent:3}% - {message}".format(
                        **event
                    ),
                    file=sys.stderr,
                    flush=True,
                )

        pipeline_result = mushroom_rebuild_pipeline.run_rebuild(
            inputs,
            outputs,
            selected_observation_ids=scope["selected_observation_ids"],
            pending_species_ids=scope["pending_species_ids"],
            progress_callback=report_progress,
        )
        rebuild_result_path = outputs.root / "rebuild_result.json"
        rebuild_result_path.write_text(
            json.dumps(pipeline_result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result_manifest = mushroom_rebuild_contracts.create_result_manifest(
            job_spec,
            outputs.root,
            pipeline_result,
        )
        mushroom_rebuild_contracts.write_manifest(
            outputs.root / mushroom_rebuild_contracts.RESULT_MANIFEST_NAME,
            result_manifest,
        )
        result_verification = mushroom_rebuild_contracts.verify_result_manifest(
            result_manifest,
            job_spec,
            outputs.root,
        )
        print_json(
            {
                "status": "complete",
                "job_id": job_spec["job_id"],
                "job_spec_id": job_spec["job_spec_id"],
                "result_manifest_id": result_manifest["result_manifest_id"],
                "result_verification": result_verification,
                "summary": pipeline_result["summary"],
                "phase_durations_seconds": pipeline_result["phase_durations_seconds"],
                "duration_seconds": pipeline_result["duration_seconds"],
            }
        )
        return 0 if result_verification["status"] == "valid" else 1
    except (FileExistsError, FileNotFoundError, KeyError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Contract job failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
