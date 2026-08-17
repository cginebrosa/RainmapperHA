#!/usr/bin/env python3
"""Train one isolated V2--V6 runtime batch from prebuilt shared benchmarks."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_ml_multiversion_plan  # noqa: E402
from rainmapper_core import mushroom_ml_quality_catalog  # noqa: E402
from rainmapper_core import mushroom_ml_runtime_trainer  # noqa: E402
from rainmapper_core import mushroom_ml_version_registry  # noqa: E402


def _generation(value: str) -> tuple[str, str]:
    version_id, separator, generation_id = value.partition("=")
    if not separator or not version_id.strip() or not generation_id.strip():
        raise argparse.ArgumentTypeError("generation must be VERSION_ID=GENERATION_ID")
    return version_id.strip(), generation_id.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--generation", action="append", type=_generation, required=True)
    parser.add_argument("--species", action="append", required=True)
    parser.add_argument("--v3-fixed", required=True, type=Path)
    parser.add_argument("--v3-lag", required=True, type=Path)
    parser.add_argument("--v4-fixed", required=True, type=Path)
    parser.add_argument("--v4-lag", required=True, type=Path)
    parser.add_argument("--v5-fixed", required=True, type=Path)
    parser.add_argument("--v5-lag", required=True, type=Path)
    parser.add_argument("--v2-v5-heldout", required=True, type=Path)
    parser.add_argument("--v6-heldout", required=True, type=Path)
    parser.add_argument("--models-root", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--job-id", default="")
    parser.add_argument("--result-manifest", type=Path)
    parser.add_argument("--progress-jsonl", type=Path)
    parser.add_argument("--training-input-manifest", type=Path)
    return parser.parse_args()


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Benchmark must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sanitized_training_manifest(path: Path) -> dict:
    payload = _load(path)
    if payload.get("kind") != "mushroom_rebuild_input_manifest":
        raise ValueError("Training input manifest kind is invalid")
    sanitized = json.loads(json.dumps(payload))
    for dataset in sanitized.get("datasets", []):
        if isinstance(dataset, dict):
            dataset.pop("root_path", None)
    return sanitized


def main() -> int:
    args = parse_args()
    registry = mushroom_ml_version_registry.load_registry(args.registry)
    generation_ids = dict(args.generation)
    plan = mushroom_ml_multiversion_plan.build_plan(
        registry,
        batch_id=args.batch_id,
        snapshot_id=args.snapshot_id,
        generation_ids=generation_ids,
        species_ids=args.species,
    )
    benchmarks = mushroom_ml_runtime_trainer.materialize_runtime_benchmarks(
        v3_fixed=_load(args.v3_fixed),
        v3_lag=_load(args.v3_lag),
        v4_fixed=_load(args.v4_fixed),
        v4_lag=_load(args.v4_lag),
        v5_fixed=_load(args.v5_fixed),
        v5_lag=_load(args.v5_lag),
    )
    progress_handle = None
    if args.progress_jsonl:
        args.progress_jsonl.parent.mkdir(parents=True, exist_ok=True)
        progress_handle = args.progress_jsonl.open("x", encoding="utf-8")

    def report_progress(event: dict) -> None:
        if progress_handle is None:
            return
        progress_handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        progress_handle.flush()

    try:
        destination, manifest = mushroom_ml_runtime_trainer.write_batch(
            registry,
            plan,
            benchmarks,
            models_root=args.models_root,
            progress_callback=report_progress,
        )
        quality_catalog = mushroom_ml_quality_catalog.build_catalog(
            args.v2_v5_heldout,
            args.v6_heldout,
            snapshot_id=args.snapshot_id,
        )
        quality_path = destination / "quality-catalog.json"
        quality_path.write_text(
            json.dumps(quality_catalog, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        manifest["quality_catalog"] = {
            "path": "batches/" + manifest["batch_id"] + "/quality-catalog.json",
            "sha256": _sha256(quality_path),
        }
        if args.training_input_manifest:
            training_input_path = destination / "training-input-manifest.json"
            training_input_path.write_text(
                json.dumps(
                    _sanitized_training_manifest(args.training_input_manifest),
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            manifest["training_input_manifest"] = {
                "path": "batches/"
                + manifest["batch_id"]
                + "/training-input-manifest.json",
                "sha256": _sha256(training_input_path),
            }
        (destination / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    finally:
        if progress_handle is not None:
            progress_handle.close()
    summary = {
        "status": "complete",
        "batch_id": manifest["batch_id"],
        "snapshot_id": manifest["snapshot_id"],
        "fit_count": plan["fit_count"],
        "artifact_count": len(manifest["artifacts"]),
        "batch_dir": str(destination),
        "manifest_path": str(destination / "manifest.json"),
        "active": False,
        "operational_candidate_trained": False,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if args.result_manifest:
        result_batch = args.result_manifest.parent / "batch"
        if result_batch.exists():
            raise FileExistsError(f"Result batch already exists: {result_batch}")
        shutil.copytree(destination, result_batch)
        result_files = [
            {
                "path": "batch/manifest.json",
                "size_bytes": (result_batch / "manifest.json").stat().st_size,
                "sha256": _sha256(result_batch / "manifest.json"),
            }
        ]
        result_files.append(
            {
                "path": "batch/quality-catalog.json",
                "size_bytes": (result_batch / "quality-catalog.json").stat().st_size,
                "sha256": _sha256(result_batch / "quality-catalog.json"),
            }
        )
        training_input_ref = manifest.get("training_input_manifest")
        if isinstance(training_input_ref, dict):
            training_input_path = result_batch / "training-input-manifest.json"
            result_files.append(
                {
                    "path": "batch/training-input-manifest.json",
                    "size_bytes": training_input_path.stat().st_size,
                    "sha256": _sha256(training_input_path),
                }
            )
        for artifact in manifest["artifacts"]:
            relative = Path(str(artifact["path"])).relative_to(
                Path("batches") / manifest["batch_id"]
            )
            artifact_path = result_batch / relative
            result_files.append(
                {
                    "path": (Path("batch") / relative).as_posix(),
                    "size_bytes": artifact_path.stat().st_size,
                    "sha256": _sha256(artifact_path),
                }
            )
        result_payload = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_multiversion_result",
            "job_id": args.job_id,
            "batch_id": manifest["batch_id"],
            "snapshot_id": manifest["snapshot_id"],
            "files": result_files,
            "batch_manifest_sha256": _sha256(destination / "manifest.json"),
            "planned_fit_count": int(manifest.get("planned_fit_count", 0)),
            "successful_fit_count": int(manifest.get("successful_fit_count", 0)),
            "failed_fit_count": int(manifest.get("failed_fit_count", 0)),
            "operational_candidate_trained": False,
        }
        args.result_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.result_manifest.write_text(
            json.dumps(result_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
