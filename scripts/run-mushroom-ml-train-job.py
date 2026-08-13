#!/usr/bin/env python3
"""External worker training script for ml_train_v0 jobs.

Reads job_spec.json, features.json, known_sites.json from an input directory,
trains ML models for the specified species, and writes:
  - ml_candidate/ml_models/<species_id>.joblib
  - ml_candidate/ml_train_result.json  (manifest for upload)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ML models for a ml_train_v0 worker job.")
    parser.add_argument("--job-spec", required=True, help="Path to job_spec.json")
    parser.add_argument("--features", required=True, help="Path to features JSON file")
    parser.add_argument("--known-sites", required=True, help="Path to known_sites JSON file")
    parser.add_argument("--output-dir", required=True, help="Output directory for models and manifest")
    parser.add_argument("--progress-jsonl", default="", help="Path to write progress events (JSONL)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    job_spec_path = Path(args.job_spec)
    features_path = Path(args.features)
    known_sites_path = Path(args.known_sites)
    output_dir = Path(args.output_dir)
    progress_path = Path(args.progress_jsonl) if args.progress_jsonl else None

    if not job_spec_path.is_file():
        print(f"ERROR: job_spec not found: {job_spec_path}", file=sys.stderr)
        sys.exit(1)
    if not features_path.is_file():
        print(f"ERROR: features not found: {features_path}", file=sys.stderr)
        sys.exit(1)
    if not known_sites_path.is_file():
        print(f"ERROR: known_sites not found: {known_sites_path}", file=sys.stderr)
        sys.exit(1)

    job_spec = json.loads(job_spec_path.read_text(encoding="utf-8"))
    species_ids = job_spec.get("species_ids") if isinstance(job_spec, dict) else None
    if isinstance(species_ids, list):
        species_ids = [str(s).strip() for s in species_ids if str(s or "").strip()]
    else:
        species_ids = None

    models_dir = output_dir / "ml_models"
    report_path = output_dir / "ml_train_report.json"
    models_dir.mkdir(parents=True, exist_ok=True)

    def emit_progress(overall_percent: int, message: str) -> None:
        event = {"overall_percent": overall_percent, "phase": "Training ML models", "message": message}
        if not args.quiet:
            print(json.dumps(event, ensure_ascii=False), file=sys.stderr, flush=True)
        if progress_path is not None:
            with progress_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    emit_progress(5, "Importing trainer...")
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from rainmapper_core import mushroom_ml_experiment_trainer, mushroom_ml_trainer
    except ImportError as exc:
        print(f"ERROR: Cannot import mushroom_ml_trainer: {exc}", file=sys.stderr)
        sys.exit(2)

    def positive_int_setting(name: str, default: int, minimum: int) -> int:
        try:
            value = int(job_spec.get(name, default))
        except (TypeError, ValueError):
            return default
        return value if value >= minimum else default

    min_rows = positive_int_setting("min_rows", mushroom_ml_trainer.MIN_ROWS_DEFAULT, 1)
    cv_folds = positive_int_setting("cv_folds", mushroom_ml_trainer.CV_FOLDS_DEFAULT, 2)

    emit_progress(10, "Starting training...")
    def emit_operational_progress(percent: int, message: str) -> None:
        emit_progress(10 + int(max(0, min(100, percent)) * 0.7), message)

    try:
        report = mushroom_ml_trainer.run(
            species_ids=species_ids or None,
            features_path=features_path,
            known_sites_path=known_sites_path,
            models_dir=models_dir,
            report_path=report_path,
            min_rows=min_rows,
            cv_folds=cv_folds,
            progress_callback=emit_operational_progress,
        )
    except Exception as exc:
        print(f"ERROR: Training failed: {exc}", file=sys.stderr)
        sys.exit(1)

    species_results = report.get("species_results") if isinstance(report, dict) else []
    trained_species = [
        str(r["species_id"])
        for r in (species_results or [])
        if isinstance(r, dict) and not r.get("skipped") and r.get("species_id")
    ]

    emit_progress(82, "Training shadow comparison models...")
    shadow_report_path = output_dir / "ml_experiment_report.json"
    try:
        shadow_report = mushroom_ml_experiment_trainer.run(
            species_ids=trained_species,
            features_path=features_path,
            known_sites_path=known_sites_path,
            models_dir=models_dir,
            report_path=shadow_report_path,
        )
    except Exception as exc:
        print(f"ERROR: Shadow model training failed: {exc}", file=sys.stderr)
        sys.exit(1)
    report["shadow_experiments"] = shadow_report
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shadow_report_path.unlink(missing_ok=True)

    shadow_feature_set_ids = [
        str(feature_set.get("feature_set_id", "")).strip()
        for feature_set in shadow_report.get("feature_sets", [])
        if isinstance(feature_set, dict)
        and str(feature_set.get("feature_set_id", "")).strip()
    ]
    expected_shadow_feature_set_ids = list(
        mushroom_ml_experiment_trainer.DEFAULT_FEATURE_SET_IDS
    )
    if shadow_feature_set_ids != expected_shadow_feature_set_ids:
        print(
            "ERROR: Shadow model contract mismatch: "
            f"expected {expected_shadow_feature_set_ids}, got {shadow_feature_set_ids}",
            file=sys.stderr,
        )
        sys.exit(1)

    shadow_model_paths = sorted(
        {
            str(row.get("model_path", ""))
            for feature_set in shadow_report.get("feature_sets", [])
            if isinstance(feature_set, dict)
            for row in feature_set.get("species_results", [])
            if isinstance(row, dict) and not row.get("skipped") and row.get("model_path")
        }
    )

    emit_progress(95, f"Building result manifest ({len(trained_species)} models trained)...")
    if not report_path.is_file():
        print(f"ERROR: Expected training report not found: {report_path}", file=sys.stderr)
        sys.exit(1)
    artifacts = [{
        "path": "ml_train_report.json",
        "size_bytes": report_path.stat().st_size,
        "sha256": _sha256_file(report_path),
    }]
    for species_id in trained_species:
        model_file = models_dir / f"mushroom_ml_v0_{species_id}.joblib"
        if not model_file.is_file():
            print(f"WARNING: Expected model file not found: {model_file}", file=sys.stderr)
            continue
        size_bytes = model_file.stat().st_size
        sha256 = _sha256_file(model_file)
        artifacts.append({
            "path": f"ml_models/mushroom_ml_v0_{species_id}.joblib",
            "size_bytes": size_bytes,
            "sha256": sha256,
        })
    declared_shadow_models: list[str] = []
    for raw_path in shadow_model_paths:
        model_file = Path(raw_path)
        if not model_file.is_file() or model_file.parent.resolve() != models_dir.resolve():
            print(f"ERROR: Invalid shadow model path: {model_file}", file=sys.stderr)
            sys.exit(1)
        logical_path = f"ml_models/{model_file.name}"
        declared_shadow_models.append(logical_path)
        artifacts.append({
            "path": logical_path,
            "size_bytes": model_file.stat().st_size,
            "sha256": _sha256_file(model_file),
        })

    manifest_content = json.dumps(
        {
            "schema_version": "0.2",
            "kind": "mushroom_ml_v0_result",
            "job_id": str(job_spec.get("job_id", "") if isinstance(job_spec, dict) else ""),
            "trained_species": trained_species,
            "shadow_feature_set_ids": shadow_feature_set_ids,
            "shadow_models": declared_shadow_models,
            "artifacts": artifacts,
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"
    manifest_path = output_dir / "ml_train_result.json"
    manifest_path.write_text(manifest_content, encoding="utf-8")

    emit_progress(100, f"Done. {len(trained_species)} models trained.")
    print(
        json.dumps(
            {
                "status": "ml_train_complete",
                "trained_species_count": len(trained_species),
                "trained_species": trained_species,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
