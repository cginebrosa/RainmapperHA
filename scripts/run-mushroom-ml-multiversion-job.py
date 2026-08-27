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
from rainmapper_core import mushroom_ml_model_catalog  # noqa: E402
from rainmapper_core import mushroom_ml_benchmark_reports  # noqa: E402
from rainmapper_core import mushroom_ml_quality_catalog  # noqa: E402
from rainmapper_core import mushroom_ml_runtime_trainer  # noqa: E402
from rainmapper_core import mushroom_ml_tuning_catalog  # noqa: E402
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
    parser.add_argument("--version", action="append")
    parser.add_argument("--profile-key", action="append")
    parser.add_argument(
        "--job-purpose",
        choices=("operational", "benchmark"),
        default="benchmark",
    )
    parser.add_argument("--v3-fixed", required=True, type=Path)
    parser.add_argument("--v3-lag", required=True, type=Path)
    parser.add_argument("--v4-fixed", type=Path)
    parser.add_argument("--v4-lag", type=Path)
    parser.add_argument("--v5-fixed", type=Path)
    parser.add_argument("--v5-lag", type=Path)
    parser.add_argument("--v2-v5-heldout", type=Path)
    parser.add_argument("--v6-heldout", type=Path)
    parser.add_argument("--models-root", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--job-id", default="")
    parser.add_argument("--result-manifest", type=Path)
    parser.add_argument("--progress-jsonl", type=Path)
    parser.add_argument("--training-input-manifest", type=Path)
    parser.add_argument("--tuning-catalog", type=Path)
    parser.add_argument(
        "--quality-catalog",
        type=Path,
        help="Verified scientific hold-out catalog to carry into an operational candidate.",
    )
    return parser.parse_args()


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Benchmark must be an object: {path}")
    return payload


def _load_optional(path: Path | None) -> dict | None:
    return _load(path) if path is not None else None


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


def _input_revisions(training_manifest: dict, registry_path: Path) -> dict[str, str]:
    files = {
        str(row.get("role") or ""): str(row.get("sha256") or "")
        for row in training_manifest.get("files", [])
        if isinstance(row, dict)
    }
    datasets = {
        str(row.get("dataset_id") or ""): str(row.get("fingerprint") or "")
        for row in training_manifest.get("datasets", [])
        if isinstance(row, dict)
    }
    weather = training_manifest.get("weather_history")
    weather = weather if isinstance(weather, dict) else {}

    def revision(role: str) -> str:
        digest = files.get(role, "")
        if not digest:
            raise ValueError(f"Training input revision is missing: {role}")
        return "sha256:" + digest.removeprefix("sha256:")

    gis_parts = [revision("gis_mappings")]
    gis_parts.extend(sorted(value for value in datasets.values() if value))
    gis_revision = "sha256:" + hashlib.sha256(
        "|".join(gis_parts).encode("utf-8")
    ).hexdigest()
    vector = {
        "observations_revision": revision("observations"),
        "weather_generation_id": str(weather.get("generation_id") or ""),
        "weather_manifest_sha256": "sha256:"
        + str(weather.get("manifest_sha256") or "").removeprefix("sha256:"),
        "sites_revision": revision("extra:known-sites.json"),
        "stations_revision": revision("extra:stations.txt"),
        "catalogs_revision": revision("reference_catalogs"),
        "gis_revision": gis_revision,
        "training_contract_version": mushroom_ml_version_registry.training_contract_revision(
            mushroom_ml_version_registry.load_registry(registry_path)
        ),
    }
    return mushroom_ml_version_registry.validate_revision_vector(vector)


def resolve_training_scope(
    registry: dict,
    *,
    job_purpose: str,
    profile_keys: list[str] | None,
    version_ids: list[str],
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    """Resolve complete operational versions or a benchmark profile selection."""
    if job_purpose == "operational":
        requested = list(profile_keys or [])
        if not requested:
            requested = mushroom_ml_version_registry.training_profile_keys(
                registry,
                job_purpose="operational",
                version_ids=version_ids,
            )
        selected_profiles = [
            mushroom_ml_version_registry.resolve_operational_profile(
                registry, profile_key
            )
            for profile_key in requested
        ]
        resolved_versions = list(
            dict.fromkeys(row["version_id"] for row in selected_profiles)
        )
        resolved_profiles = [row["profile_key"] for row in selected_profiles]
        for version_id in resolved_versions:
            required_profiles = {
                row["profile_key"]
                for row in mushroom_ml_version_registry.operational_profile_options(
                    registry
                )
                if row["version_id"] == version_id
            }
            if set(resolved_profiles) & required_profiles != required_profiles:
                raise ValueError(
                    f"Operational training must contain every profile in {version_id}"
                )
        return selected_profiles, resolved_profiles, resolved_versions
    selected_profiles = mushroom_ml_version_registry.resolve_benchmark_profiles(
        registry, profile_keys
    )
    resolved_profiles = [row["profile_key"] for row in selected_profiles]
    resolved_versions = list(
        dict.fromkeys(row["version_id"] for row in selected_profiles)
    )
    return selected_profiles, resolved_profiles, resolved_versions


def main() -> int:
    args = parse_args()
    registry = mushroom_ml_version_registry.load_registry(args.registry)
    generation_ids = dict(args.generation)
    operational = args.job_purpose == "operational"
    selected_profiles, profile_keys, version_ids = resolve_training_scope(
        registry,
        job_purpose=args.job_purpose,
        profile_keys=(
            list(args.profile_key) if args.profile_key is not None else None
        ),
        version_ids=list(args.version or generation_ids),
    )
    declared_version_ids = list(args.version or generation_ids)
    if declared_version_ids != version_ids or set(generation_ids) != set(version_ids):
        raise ValueError(
            "Training version and generation scope does not match the selected profiles"
        )
    selected_keys = set(profile_keys or [])
    selected_catalog = [
        row
        for row in mushroom_ml_model_catalog.catalog_entries(registry)
        if f"{row['version_id']}/{row['profile_id']}" in selected_keys
    ]
    required_input_ids = {
        str(input_id)
        for row in selected_catalog
        for input_id in row["input_requirements"]["prepared_input_ids"]
    }
    optional_paths = {
        "v4_fixed": args.v4_fixed,
        "v4_lag": args.v4_lag,
        "v5_fixed": args.v5_fixed,
        "v5_lag": args.v5_lag,
    }
    required_optional_paths = [
        optional_paths[input_id]
        for input_id in sorted(required_input_ids & set(optional_paths))
    ]
    required_optional_paths.extend([args.v2_v5_heldout, args.v6_heldout])
    if any(path is None for path in required_optional_paths):
        raise ValueError("Training is missing inputs required by the selected profiles")
    plan = mushroom_ml_multiversion_plan.build_plan(
        registry,
        batch_id=args.batch_id,
        snapshot_id=args.snapshot_id,
        generation_ids=generation_ids,
        species_ids=args.species,
        version_ids=version_ids,
        profile_keys=profile_keys,
    )
    tuning_catalog = (
        mushroom_ml_tuning_catalog.validate_catalog(
            registry,
            _load(args.tuning_catalog),
            training_plan=plan,
        )
        if args.tuning_catalog is not None
        else None
    )
    if operational and tuning_catalog is None:
        raise ValueError("Operational training requires a compatible tuning catalog")
    benchmarks = mushroom_ml_runtime_trainer.materialize_runtime_benchmarks(
        v3_fixed=_load(args.v3_fixed),
        v3_lag=_load(args.v3_lag),
        v4_fixed=_load_optional(args.v4_fixed),
        v4_lag=_load_optional(args.v4_lag),
        v5_fixed=_load_optional(args.v5_fixed),
        v5_lag=_load_optional(args.v5_lag),
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
            tuning_catalog=tuning_catalog,
        )
        if operational and int(manifest.get("failed_fit_count", 0) or 0):
            raise ValueError("Operational training must produce every planned artifact")
        manifest["job_purpose"] = args.job_purpose
        manifest["operational_candidate_trained"] = operational
        if tuning_catalog is not None:
            tuning_path = destination / "tuning-catalog.json"
            mushroom_ml_tuning_catalog.save(tuning_path, tuning_catalog)
            manifest["tuning_catalog"] = {
                **manifest["tuning_catalog"],
                "path": "batches/" + manifest["batch_id"] + "/tuning-catalog.json",
                "sha256": _sha256(tuning_path),
            }
        if operational and args.quality_catalog is not None:
            source_catalog = _load(args.quality_catalog)
            if (
                source_catalog.get("kind") != mushroom_ml_quality_catalog.KIND
                or source_catalog.get("schema_version")
                != mushroom_ml_quality_catalog.SCHEMA_VERSION
            ):
                raise ValueError("Operational quality catalog contract is invalid")
            catalog_profile_keys = {
                f"{row.get('version_id')}/{row.get('profile_id')}"
                for row in source_catalog.get("entries", [])
                if isinstance(row, dict)
            }
            if not set(profile_keys) <= catalog_profile_keys:
                raise ValueError(
                    "Operational quality catalog does not cover every selected profile"
                )
            quality_path = destination / "quality-catalog.json"
            shutil.copyfile(args.quality_catalog, quality_path)
            manifest["quality_catalog"] = {
                "path": "batches/" + manifest["batch_id"] + "/quality-catalog.json",
                "sha256": _sha256(quality_path),
            }
        if args.quality_catalog is None:
            expected_estimators: dict[str, list[str]] = {}
            for fit in plan["fits"]:
                ref = fit["artifact_ref"]
                key = f"{ref['version_id']}/{ref['profile_id']}"
                expected_estimators.setdefault(key, [])
                if ref["estimator_id"] not in expected_estimators[key]:
                    expected_estimators[key].append(ref["estimator_id"])
            quality_catalog = mushroom_ml_quality_catalog.build_catalog(
                args.v2_v5_heldout,
                args.v6_heldout,
                snapshot_id=args.snapshot_id,
                profile_keys=profile_keys,
                expected_estimators=expected_estimators,
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
            report_result = mushroom_ml_benchmark_reports.write_report(
                destination,
                job_id=args.job_id,
                training_plan=plan,
                selected_profiles=selected_profiles or [],
                quality_catalog=quality_catalog,
                fit_results=manifest.get("fit_results", []),
                failed_fits=manifest.get("failed_fits", []),
                v2_v5_predictions_path=args.v2_v5_heldout,
                v6_predictions_path=args.v6_heldout,
            )
            report_path = report_result["report_path"]
            predictions_path = report_result["predictions_path"]
            manifest["benchmark_report"] = {
                "path": "batches/" + manifest["batch_id"] + "/benchmark-report.json",
                "sha256": _sha256(report_path),
                "report_id": report_result["report"]["report_id"],
            }
            manifest["holdout_predictions"] = {
                "path": "batches/" + manifest["batch_id"] + "/holdout-predictions.jsonl",
                "sha256": _sha256(predictions_path),
                "row_count": report_result["report"]["holdout_predictions"]["row_count"],
            }
        if args.training_input_manifest:
            sanitized_training = _sanitized_training_manifest(
                args.training_input_manifest
            )
            training_input_path = destination / "training-input-manifest.json"
            training_input_path.write_text(
                json.dumps(
                    sanitized_training,
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
            manifest["input_revisions"] = _input_revisions(
                sanitized_training, args.registry
            )
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
        "job_purpose": args.job_purpose,
        "version_ids": version_ids,
        "profile_keys": list(plan.get("profile_keys") or []),
        "report_id": (
            str((manifest.get("benchmark_report") or {}).get("report_id") or "")
            if not operational
            else ""
        ),
        "operational_candidate_trained": operational,
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
        if isinstance(manifest.get("quality_catalog"), dict):
            result_files.append(
                {
                    "path": "batch/quality-catalog.json",
                    "size_bytes": (result_batch / "quality-catalog.json").stat().st_size,
                    "sha256": _sha256(result_batch / "quality-catalog.json"),
                }
            )
        for key, filename in (
            ("benchmark_report", "benchmark-report.json"),
            ("holdout_predictions", "holdout-predictions.jsonl"),
        ):
            if isinstance(manifest.get(key), dict):
                path = result_batch / filename
                result_files.append(
                    {
                        "path": "batch/" + filename,
                        "size_bytes": path.stat().st_size,
                        "sha256": _sha256(path),
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
            "job_purpose": args.job_purpose,
            "report_id": summary["report_id"],
            "operational_candidate_trained": operational,
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
