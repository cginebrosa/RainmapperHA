"""Fit isolated temporal models and independent ranking evidence, never promote."""
from __future__ import annotations

import argparse
from collections import defaultdict
import gc
import json
import os
from pathlib import Path
import runpy
import sys
import time
import warnings

from common import ROOT, OUTPUT, TARGETS, load, write_new, digest, verify_inputs, protect_originals

sys.path.insert(0, str(ROOT))
import joblib
import numpy as np
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_plan as plans
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_runtime_inference as inference
from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core import mushroom_ml_quality_catalog as quality
from rainmapper_core import mushroom_ml_tuning_catalog as tuning
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from rainmapper_core import mushroom_ml_raw_weather as raw

TRAIN_ROLES = {"ranking": {"fit"}, "threshold": {"fit", "ranking"},
               "external": {"fit", "ranking", "threshold"}}


def partition_samples(benchmark, cohort, fold, phase):
    members = cohort["folds"][str(fold)]
    rows = {row["observation_id"]: row for row in cohort["rows"]}
    train, test = [], []
    for sample in holdout.eligible_samples(benchmark):
        metadata = sample["metadata"]
        identity = metadata["observation_id"]
        if identity not in rows:
            raise ValueError("Unfrozen observation in a model input")
        if metadata["species_id"] != rows[identity]["species_id"]:
            raise ValueError("Training species identity changed")
        if members[identity] in TRAIN_ROLES[phase]:
            train.append(sample)
        elif members[identity] == phase and rows[identity]["species_id"] in TARGETS:
            test.append(sample)
    train_ids = {s["metadata"]["observation_id"] for s in train}
    test_ids = {s["metadata"]["observation_id"] for s in test}
    if train_ids & test_ids:
        raise AssertionError("Train/test overlap")
    train_groups = {rows[i]["episode_id"] for i in train_ids}
    test_groups = {rows[i]["episode_id"] for i in test_ids}
    if train_groups & test_groups:
        raise AssertionError("Cross-species episode overlap")
    if train and test and max(rows[i]["date"] for i in train_ids) >= min(rows[i]["date"] for i in test_ids):
        raise AssertionError("Training must precede every test date")
    return train, test


def single_thread(bundle):
    model = bundle["model"]
    if hasattr(model, "get_params"):
        parameters = {name: 1 for name in model.get_params(deep=True) if name.endswith("n_jobs")}
        if parameters:
            model.set_params(**parameters)


def initial_v6_decision(reference, prepared, selector):
    if reference.estimator_id == "smooth_species_logistic_v1":
        config = {"C": 0.1, "deviation_scale": None}
        return config, {"selection": "existing_declared_species_default"}
    window = smooth.window_days_from_profile_id(reference.profile_id)
    transform = smooth.SmoothLagPreprocessor(channels=raw.RAW_CHANNELS, window_days=window).fit(prepared["X"])
    samples = list(prepared["samples"])
    species = [s["metadata"]["species_id"] for s in samples]
    selected = selector(transform.transform(prepared["X"]), prepared["y"], species, samples,
                        partial=reference.estimator_id == "smooth_partial_pooling_logistic_v1", group_days=14)
    return {key: selected[key] for key in ("C", "deviation_scale")}, {
        "selection": "existing_joint_selector_initial_fit_only", "detail": selected,
        "limitation": "existing joint selector preprocesses initial fit before its inner subdivisions"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, choices=(2024, 2025, 2026), required=True)
    parser.add_argument("--phase", choices=tuple(TRAIN_ROLES), required=True)
    args = parser.parse_args()
    if os.environ.get("RAINMAPPER_PREDICTION_RESEARCH_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py")
    protect_originals()
    cohort_path = OUTPUT / "cohort-v2.json"
    cohort = load(cohort_path)
    verify_inputs(cohort)
    registry = load(ROOT / "docker-data/mushroom-data/mushroom_ml_version_registry.json")
    benchmark_manifest = load(OUTPUT / "benchmarks/manifest.json")
    if benchmark_manifest["cohort_sha256"] != digest(cohort_path):
        raise ValueError("Prepared cohort changed")
    initial_path = OUTPUT / f"fold-{args.fold}/ranking"
    initial = load(initial_path / "summary.json") if args.phase != "ranking" else None
    snapshot_id = "sha256:" + digest(cohort_path)
    dependencies = []
    if initial is not None and (initial["status"], initial["fold"], initial["phase"], initial["snapshot_id"]) != (
            "completed", args.fold, "ranking", snapshot_id):
        raise ValueError("Initial fit/ranking phase incomplete")
    if initial is not None:
        dependencies = [initial_path / "summary.json", initial_path / "quality.json"]
        if load(dependencies[1])["snapshot_id"] != snapshot_id:
            raise ValueError("Initial quality snapshot mismatch")
    if args.phase == "external":
        closed_threshold = OUTPUT / f"fold-{args.fold}/threshold-choice.json"
        if not closed_threshold.is_file():
            raise ValueError("B must be sealed before external refitting")
        choice = load(closed_threshold)
        from recommendation_metrics import GRID
        if (choice.get("schema"), choice.get("fold"), choice.get("snapshot_id"), choice.get("source_role")) != (
                1, args.fold, snapshot_id, "threshold"):
            raise ValueError("Invalid threshold choice identity")
        if set(choice.get("species", {})) != set(TARGETS) or any(choice["species"][s].get("threshold") not in GRID for s in TARGETS):
            raise ValueError("Threshold choice is outside the sealed grid/species")
        if choice["predictions_sha256"] != digest(OUTPUT / f"fold-{args.fold}/threshold/predictions.jsonl"):
            raise ValueError("Threshold predictions changed after selection")
        dependencies.append(closed_threshold)
    destination = OUTPUT / f"fold-{args.fold}" / args.phase
    destination.mkdir(parents=True, exist_ok=False)
    batch_id = f"research_{args.fold}_{args.phase}"
    versions = list(dict.fromkeys(p["version_id"] for p in cohort["profiles"]))
    full_plan = plans.build_plan(registry, batch_id=batch_id, snapshot_id=snapshot_id,
        generation_ids={version: f"{version}_{args.fold}_{args.phase}" for version in versions},
        species_ids=cohort["shared_species"], version_ids=versions,
        profile_keys=[p["version_id"] + "/" + p["profile_id"] for p in cohort["profiles"]])
    fits = [f for f in full_plan["fits"] if f["artifact_ref"]["species_id"] in {*TARGETS, "all_species"}]
    by_benchmark = defaultdict(list)
    for fit in fits:
        ref = fit["artifact_ref"]
        by_benchmark[trainer.benchmark_key(ref["version_id"], ref["temporal_contract_id"], ref["profile_id"])].append(fit)
    trainer.validate_benchmark_coverage({"fits": fits}, {entry["key"] for entry in benchmark_manifest["benchmarks"]})
    if len({entry["key"] for entry in benchmark_manifest["benchmarks"]}) != len(benchmark_manifest["benchmarks"]):
        raise ValueError("Duplicate prepared benchmark identity")
    script_paths = [Path(__file__), Path(__file__).with_name("common.py"), *dependencies]
    code_seal = [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in script_paths]
    write_new(destination / "execution-code.json", {"files": code_seal, "fold": args.fold,
        "phase": args.phase, "cohort_sha256": digest(cohort_path), "planned_fits": len(fits),
        "train_roles": sorted(TRAIN_ROLES[args.phase]), "evaluation_role": args.phase,
        "ranking_probability_precision_decimals": 6})
    selector = runpy.run_path(str(ROOT / "scripts/evaluate-biology-v6-smooth-hierarchical.py"))["select_joint_config"]
    manifests = {"schema_version": catalog.SCHEMA_VERSION, "kind": catalog.BATCH_MANIFEST_KIND,
                 "batch_id": batch_id, "snapshot_id": snapshot_id, "artifacts": []}
    decisions, results, holdouts = {}, [], []
    models_root = destination / "models"
    for entry in benchmark_manifest["benchmarks"]:
        key = entry["key"]
        if key not in by_benchmark:
            continue
        path = ROOT / entry["path"]
        if digest(path) != entry["sha256"]:
            raise ValueError("Prepared benchmark changed")
        benchmark = load(path)
        train, test = partition_samples(benchmark, cohort, args.fold, args.phase)
        filtered = {**benchmark, "samples": train}
        prepared_by_scope, rows_by_id = {}, {}
        if args.phase == "ranking":
            for sample in test:
                m = sample["metadata"]
                sid = m["species_id"]
                species_train = [s for s in train if s["metadata"]["species_id"] == sid]
                if not species_train:
                    continue
                rows_by_id[sample["sample_id"]] = {
                    "row_key": key + "|" + sample["sample_id"], "sample_id": sample["sample_id"],
                    "observation_id": m["observation_id"], "species_id": sid, "area_id": m["area_id"],
                    "target_date": m["target_date"], "cutoff_date": m["cutoff_date"],
                    "version_id": key.split("|")[0], "profile_id": key.split("|")[2],
                    "temporal_contract_id": key.split("|")[1], "horizon_days": m["horizon_days"],
                    "split_id": "fruiting_groups_14d", "group_days": 14,
                    "validation_group_id": m["research_episode_id"],
                    "y_true": int(sample["prediction_target"] == "favorable"),
                    "train_prevalence_probability": sum(s["prediction_target"] == "favorable" for s in species_train) / len(species_train),
                    "estimator_probabilities": {}}
        for fit in by_benchmark[key]:
            reference = catalog.ModelArtifactRef.from_mapping(fit["artifact_ref"])
            decision_key = tuning.decision_key(reference.as_dict())
            start = time.monotonic()
            result = {"key": decision_key, "available": False}
            unexpected_error = None
            try:
                if initial is not None and decision_key not in initial["decisions"]:
                    raise ValueError("No sealed initial fit for this candidate")
                if reference.species_id not in prepared_by_scope:
                    prepared_by_scope[reference.species_id] = trainer._prepare_fit_inputs(reference, filtered)
                prepared = prepared_by_scope[reference.species_id]
                decision, provenance = None, {}
                if initial is not None:
                    decision = {"key": decision_key, "fit_config": initial["decisions"][decision_key]["fit_config"]}
                    provenance = {"selection": "frozen_initial_fit"}
                elif reference.version_id == smooth.WINDOWED_VERSION_ID:
                    config, provenance = initial_v6_decision(reference, prepared, selector)
                    decision = {"key": decision_key, "fit_config": config}
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    bundle = trainer.fit_artifact(reference, filtered, snapshot_id=snapshot_id,
                                                 tuning_decision=decision, prepared_inputs=prepared)
                single_thread(bundle)
                result["warnings"] = dict(__import__("collections").Counter(type(w.message).__name__ for w in caught))
                decisions[decision_key] = {"fit_config": bundle["fit_config"], **provenance}
                result.update(available=True, training_rows=bundle["training_row_count"],
                              training_observations=len({s["metadata"]["observation_id"] for s in prepared["samples"]}),
                              training_species_ids=bundle["training_species_ids"])
                if args.phase == "ranking":
                    selected_test = [s for s in test if s["sample_id"] in rows_by_id and (
                        reference.species_id == "all_species" or s["metadata"]["species_id"] == reference.species_id)]
                    predictions = inference.predict_bundle_many(bundle, [s["predictive_features"] for s in selected_test],
                        species_ids=[s["metadata"]["species_id"] for s in selected_test])
                    for sample, prediction in zip(selected_test, predictions, strict=True):
                        rows_by_id[sample["sample_id"]]["estimator_probabilities"][reference.estimator_id] = prediction["probability"]
                else:
                    relative = catalog.model_relative_path(reference)
                    model_path = models_root / relative
                    model_path.parent.mkdir(parents=True, exist_ok=True)
                    if model_path.exists():
                        raise ValueError("Refusing to overwrite an experiment model")
                    joblib.dump(bundle, model_path, compress=3)
                    manifests["artifacts"].append({"artifact_ref": reference.as_dict(),
                        "supported_horizons": sorted(catalog.supported_horizons(reference.temporal_contract_id)),
                        "path": relative.as_posix(), "sha256": digest(model_path)})
                del bundle
            except (ValueError, FloatingPointError) as exc:
                result.update(available=False, reason=str(exc))
                decisions.pop(decision_key, None)
                expected = ("No eligible rows", "requires both classes", "requires at least seven",
                            "calibration requires", "sparse-group", "No sealed initial fit")
                if not any(part in str(exc) for part in expected):
                    unexpected_error = exc
            result["seconds"] = time.monotonic() - start
            results.append(result)
            with (destination / "fit-events.jsonl").open("a") as log:
                log.write(json.dumps(result) + "\n")
            print(json.dumps({"completed": len(results), "planned": len(fits), "available": result["available"],
                              "key": decision_key, "seconds": round(result["seconds"], 2)}), flush=True)
            if unexpected_error is not None:
                raise RuntimeError("Unexpected estimator failure; do not interpret as scientific unavailability") from unexpected_error
        holdouts.extend(rows_by_id.values())
        del benchmark, filtered, train, test, prepared_by_scope
        gc.collect()
    if len(results) != len(fits) or {r["key"] for r in results} != {
            tuning.decision_key(f["artifact_ref"]) for f in fits}:
        raise ValueError("Fitted scope does not match the complete planned candidate universe")
    if args.phase == "ranking":
        paths = [destination / "ranking-v2-v5.jsonl", destination / "ranking-v6.jsonl"]
        for index, path in enumerate(paths):
            with path.open("x") as stream:
                for row in holdouts:
                    if (row["version_id"] == smooth.WINDOWED_VERSION_ID) == bool(index):
                        stream.write(json.dumps(row) + "\n")
        quality_catalog = quality.build_catalog(*paths, snapshot_id=snapshot_id,
            profile_keys=[p["version_id"] + "/" + p["profile_id"] for p in cohort["profiles"]],
            expected_estimators={p["version_id"] + "/" + p["profile_id"]: p["estimator_ids"] for p in cohort["profiles"]})
        write_new(destination / "quality.json", quality_catalog)
    else:
        catalog.validate_batch_manifest(registry, manifests)
        write_new(destination / "manifest.json", manifests)
    verify_inputs(cohort)
    if any(digest(ROOT / row["path"]) != row["sha256"] for row in code_seal):
        raise ValueError("Experiment code changed during fitting")
    summary = {"status": "completed", "phase": args.phase, "fold": args.fold,
               "planned": len(fits), "successful": sum(r["available"] for r in results),
               "failed": [r for r in results if not r["available"]], "decisions": decisions,
               "snapshot_id": snapshot_id, "inputs_verified_after": True}
    write_new(destination / "summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("status", "phase", "fold", "planned", "successful")}), flush=True)


if __name__ == "__main__":
    main()
