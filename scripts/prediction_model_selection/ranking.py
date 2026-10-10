"""Independent area evidence from frozen same-fold models; never fit or promote."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, timedelta
import gc
import json
import math
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.prediction_model_selection.common import (
    ROOT, OUTPUT, OLD_OUTPUT, TARGETS, digest, load, write_new, verify_inputs, protect_originals,
)
# train_fold imports its historical helpers as `common`; do not bind that name to
# this study's common module. New helpers always use their qualified namespace.
sys.path.insert(0, str(ROOT / "scripts/prediction_research"))
from scripts.prediction_research import train_fold as old_train
from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_quality_catalog as quality
from rainmapper_core import mushroom_ml_runtime_inference as inference
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from rainmapper_core import mushroom_ml_tuning_catalog as tuning

COHORT_SHA256 = "559fa0f1369ec44761860e013b29a9bd0d3fb68a3d43e944b4f2f0468bc9616d"
EXPECTED_RECENT_ROWS = {2024: 1056, 2025: 3232, 2026: 4312}
EXPECTED_OLD_ROWS = {2024: 1232, 2025: 1056, 2026: 3232}
PHYSICAL_PROFILE = "common_idw_plus_physical_state"
PHYSICAL_REASONS = {"v3_physical_soil_state_unavailable", "v3_physical_features_missing"}


def read_rows(path):
    with path.open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def validate_samples(benchmark, key, cohort):
    """Check identity/labels/groups, including ineligible samples, before inference."""
    frozen = {row["observation_id"]: row for row in cohort["rows"]}
    horizons = catalog.supported_horizons(key.split("|")[1])
    expected = {(identity, h) for identity in frozen for h in horizons}
    actual, sample_ids = set(), set()
    for sample in benchmark["samples"]:
        m = sample["metadata"]
        identity, horizon = m["observation_id"], m["horizon_days"]
        if identity not in frozen or sample["sample_id"] in sample_ids or (identity, horizon) in actual:
            raise ValueError("Unfrozen or duplicate benchmark sample")
        actual.add((identity, horizon)); sample_ids.add(sample["sample_id"])
        row = frozen[identity]
        if any(m.get(field) != row[field] for field in ("species_id", "area_id", "micro_area_id")):
            raise ValueError("Benchmark species/area identity changed")
        if m["target_date"] != row["date"] or m["research_episode_id"] != row["episode_id"]:
            raise ValueError("Benchmark date or cross-species episode changed")
        if sample["prediction_target"] != ("favorable" if row["y"] else "unfavorable"):
            raise ValueError("Benchmark label changed")
        if m["cutoff_date"] != (date.fromisoformat(row["date"]) - timedelta(days=horizon)).isoformat():
            raise ValueError("Benchmark cutoff is not target minus horizon")
    if actual != expected:
        raise ValueError("Incomplete observation/horizon benchmark coverage")


def evidence_rows(key, train, test):
    version, temporal, profile = key.split("|")
    prevalence = defaultdict(list)
    for sample in train:
        prevalence[sample["metadata"]["species_id"]].append(sample["prediction_target"] == "favorable")
    result = []
    for sample in test:
        m = sample["metadata"]
        values = prevalence[m["species_id"]]
        if not values:
            raise ValueError("No species-specific training prevalence")
        result.append({
            "row_key": key + "|" + sample["sample_id"], "sample_id": sample["sample_id"],
            "observation_id": m["observation_id"], "species_id": m["species_id"], "area_id": m["area_id"],
            "target_date": m["target_date"], "cutoff_date": m["cutoff_date"],
            "version_id": version, "profile_id": profile, "temporal_contract_id": temporal,
            "horizon_days": m["horizon_days"], "split_id": "fruiting_groups_14d", "group_days": 14,
            "validation_group_id": m["research_episode_id"],
            "y_true": int(sample["prediction_target"] == "favorable"),
            "train_prevalence_probability": sum(values) / len(values), "estimator_probabilities": {},
        })
    return result


def validate_evidence(rows, expected, estimators):
    actual = {row["row_key"]: row for row in rows}
    wanted = {row["row_key"]: row for row in expected}
    if len(actual) != len(rows) or len(wanted) != len(expected) or actual.keys() != wanted.keys():
        raise ValueError("Ranking evidence has duplicate, missing or unexpected rows")
    for key, row in actual.items():
        if {k: v for k, v in row.items() if k != "estimator_probabilities"} != {
                k: v for k, v in wanted[key].items() if k != "estimator_probabilities"}:
            raise ValueError("Ranking metadata or training prevalence mismatch")
        probabilities = row["estimator_probabilities"]
        if set(probabilities) != set(estimators[row["version_id"] + "/" + row["profile_id"]]):
            raise ValueError("Incomplete ranking estimator coverage")
        for value in probabilities.values():
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Invalid ranking probability")


def predict_rows(bundle, samples, expected_columns):
    columns = bundle["feature_cols"]
    if not columns or columns != expected_columns or len(set(columns)) != len(columns):
        raise ValueError("Model/benchmark feature columns differ")
    if any(not set(columns).issubset(s["predictive_features"]) for s in samples):
        raise ValueError("A required feature key is absent (explicit nulls remain allowed)")
    # Neither labels, groups, area metadata nor dates enter the predictor.
    predictions = inference.predict_bundle_many(bundle, [s["predictive_features"] for s in samples],
        species_ids=[s["metadata"]["species_id"] for s in samples])
    if len(predictions) != len(samples):
        raise ValueError("Prediction count mismatch")
    return predictions


def excluded_recent(benchmark, cohort, fold):
    eligible = {s["sample_id"] for s in holdout.eligible_samples(benchmark)}
    return [s for s in benchmark["samples"] if s["sample_id"] not in eligible
        and s["metadata"]["species_id"] in TARGETS
        and cohort["folds"][str(fold)][s["metadata"]["observation_id"]] == "threshold"]


def validate_exclusions(exclusions, fold):
    expected = {f"biology_v3|{contract}_biology_v3|{PHYSICAL_PROFILE}": count
                for contract, count in (("fixed_gap_7d", 3), ("lag_event", 21))} if fold == 2025 else {}
    if {key: len(rows) for key, rows in exclusions.items() if rows} != expected:
        raise ValueError("Recent exclusions differ from the frozen inventory")
    identity_sets = []
    for samples in exclusions.values():
        if not samples:
            continue
        identities = {s["metadata"]["observation_id"] for s in samples}
        identity_sets.append(identities)
        if len(identities) != 3 or any(s["metadata"]["species_id"] != "amanita_caesarea" or
                {reason["code"] if isinstance(reason, dict) else reason
                 for reason in s["quality"]["training_exclusion_reasons"]} != PHYSICAL_REASONS for s in samples):
            raise ValueError("Unexpected physical-state exclusion identity or reason")
    if identity_sets and any(ids != identity_sets[0] for ids in identity_sets):
        raise ValueError("Physical exclusions must concern the same three observations")


def expected_decisions(profiles):
    return {"|".join((p["version_id"], temporal, p["profile_id"], estimator, species))
        for p in profiles for temporal in p["temporal_contract_ids"] for estimator in p["estimator_ids"]
        for species in (["all_species"] if p["estimator_scopes"][estimator] == "shared" else TARGETS)}


def validate_bundle(bundle, reference, benchmark, train, event, initial, summary, snapshot_id):
    selected = [s for s in train if reference.species_id == "all_species" or
                s["metadata"]["species_id"] == reference.species_id]
    if (bundle.get("schema_version"), bundle.get("kind"), bundle.get("snapshot_id")) != (
            "1.0", "mushroom_ml_runtime_model", snapshot_id):
        raise ValueError("Unexpected threshold bundle schema/snapshot")
    training = (len(selected), sorted({s["metadata"]["species_id"] for s in selected}))
    if (bundle["training_row_count"], sorted(bundle["training_species_ids"])) != training or (
            event["training_rows"], sorted(event["training_species_ids"])) != training:
        raise ValueError("Bundle training scope differs from same-fold fit+ranking")
    if event["training_observations"] != len({s["metadata"]["observation_id"] for s in selected}):
        raise ValueError("Bundle training observation count differs")
    key = tuning.decision_key(reference.as_dict())
    if bundle["fit_config"] != summary["decisions"][key]["fit_config"] or bundle["fit_config"] != initial["decisions"][key]["fit_config"]:
        raise ValueError("Initial tuning was not kept fixed")
    if bundle["feature_cols"] != trainer._columns(reference, benchmark):
        raise ValueError("Bundle feature contract changed")


def write_evidence(destination, prefix, rows):
    paths = [destination / f"{prefix}-v2-v5.jsonl", destination / f"{prefix}-v6.jsonl"]
    for is_v6, path in enumerate(paths):
        with path.open("x") as stream:
            for row in rows:
                if (row["version_id"] == smooth.WINDOWED_VERSION_ID) == bool(is_v6):
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    return paths


def run(fold):
    if os.environ.get("RAINMAPPER_MODEL_SELECTION_GUARDED") != "1":
        raise SystemExit("Launch through prediction_model_selection/bounded.py")
    protect_originals()
    inventory_path = OUTPUT / "inventory.json"
    inventory = load(inventory_path)
    if inventory["status"] != "verified" or inventory["cohort_sha256"] != COHORT_SHA256:
        raise ValueError("Study inventory is not sealed for this cohort")
    frozen_files = {r["path"]: r for r in inventory["old_files"]}
    seals = {str(inventory_path.relative_to(ROOT)): digest(inventory_path)}
    protocol = inventory["protocol"]
    if digest(ROOT / protocol["path"]) != protocol["sha256"]:
        raise ValueError("The sealed study protocol changed")
    seals[protocol["path"]] = protocol["sha256"]

    def checked(path):
        relative = str(path.relative_to(ROOT))
        entry = frozen_files[relative]
        actual = digest(path)
        if actual != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise ValueError("Frozen study input changed: " + relative)
        seals[relative] = actual
        return path

    cohort_path = checked(OLD_OUTPUT / "cohort-v2.json")
    if digest(cohort_path) != COHORT_SHA256:
        raise ValueError("Unexpected cohort")
    cohort = load(cohort_path)
    verify_inputs(cohort)
    registry_path = ROOT / "docker-data/mushroom-data/mushroom_ml_version_registry.json"
    registry = load(registry_path)
    seals[str(registry_path.relative_to(ROOT))] = digest(registry_path)
    snapshot_id = "sha256:" + COHORT_SHA256
    benchmark_manifest = load(checked(OLD_OUTPUT / "benchmarks/manifest.json"))
    if benchmark_manifest["cohort_sha256"] != COHORT_SHA256:
        raise ValueError("Benchmark cohort mismatch")
    profiles = cohort["profiles"]
    estimators = {p["version_id"] + "/" + p["profile_id"]: p["estimator_ids"] for p in profiles}
    options = dict(snapshot_id=snapshot_id, profile_keys=list(estimators), expected_estimators=estimators)
    expected_keys = expected_decisions(profiles)
    phase_root = OLD_OUTPUT / f"fold-{fold}"
    summaries = {phase: load(checked(phase_root / phase / "summary.json")) for phase in ("ranking", "threshold", "external")}
    for phase, summary in summaries.items():
        if (summary["status"], summary["phase"], summary["fold"], summary["snapshot_id"], summary["planned"], summary["successful"], summary["failed"]) != (
                "completed", phase, fold, snapshot_id, 168, 168, []):
            raise ValueError("Incomplete frozen phase")
        if set(summary["decisions"]) != expected_keys:
            raise ValueError("Frozen candidate universe differs")
    manifest = catalog.validate_batch_manifest(registry, load(checked(phase_root / "threshold/manifest.json")))
    external_manifest_path = checked(phase_root / "external/manifest.json")
    if (manifest["batch_id"], manifest["snapshot_id"]) != (f"research_{fold}_threshold", snapshot_id):
        raise ValueError("Threshold bundles must belong to this fold")
    if {tuning.decision_key(r["artifact_ref"]) for r in manifest["artifacts"]} != expected_keys:
        raise ValueError("Threshold manifest candidate coverage differs")
    events = read_rows(checked(phase_root / "threshold/fit-events.jsonl"))
    events_by_key = {event["key"]: event for event in events}
    if len(events) != 168 or set(events_by_key) != expected_keys or not all(e["available"] for e in events):
        raise ValueError("Threshold fit evidence is incomplete")
    by_benchmark = defaultdict(list)
    for artifact in manifest["artifacts"]:
        ref = artifact["artifact_ref"]
        path = checked(phase_root / "threshold/models" / artifact["path"])
        if digest(path) != artifact["sha256"]:
            raise ValueError("Model manifest hash mismatch")
        by_benchmark[trainer.benchmark_key(ref["version_id"], ref["temporal_contract_id"], ref["profile_id"])].append(artifact)
    entries = benchmark_manifest["benchmarks"]
    if len(entries) != 22 or len({e["key"] for e in entries}) != 22 or set(by_benchmark) != {e["key"] for e in entries}:
        raise ValueError("Benchmark coverage differs")
    expected_old, expected_recent, exclusions = [], [], {}
    for entry in entries:
        benchmark = load(checked(ROOT / entry["path"]))
        if digest(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError("Benchmark manifest hash mismatch")
        validate_samples(benchmark, entry["key"], cohort)
        for phase, target in (("ranking", expected_old), ("threshold", expected_recent)):
            train, test = old_train.partition_samples(benchmark, cohort, fold, phase)
            target.extend(evidence_rows(entry["key"], train, test))
        exclusions[entry["key"]] = excluded_recent(benchmark, cohort, fold)
        del benchmark, train, test
    validate_exclusions(exclusions, fold)
    if (len(expected_old), len(expected_recent)) != (EXPECTED_OLD_ROWS[fold], EXPECTED_RECENT_ROWS[fold]):
        raise ValueError("Ranking row count differs from the agreed inventory")
    old_paths = [checked(phase_root / "ranking" / f"ranking-{family}.jsonl") for family in ("v2-v5", "v6")]
    old_rows = [row for path in old_paths for row in read_rows(path)]
    validate_evidence(old_rows, expected_old, estimators)
    old_quality = load(checked(phase_root / "ranking/quality.json"))
    if quality.build_catalog(*old_paths, **options) != old_quality:
        raise ValueError("Technical control failed to reproduce the old quality catalog")
    destination = OUTPUT / f"fold-{fold}"
    destination.mkdir(parents=True, exist_ok=True)
    # Archive all imported repository source before inference, then verify after.
    source_paths = {Path(__file__).resolve()}
    source_paths.update(Path(m.__file__).resolve() for m in tuple(sys.modules.values())
        if getattr(m, "__file__", None) and str(m.__file__).endswith(".py")
        and Path(m.__file__).resolve().is_relative_to(ROOT) and ".venv" not in Path(m.__file__).parts)
    for path in sorted(source_paths):
        sha = digest(path)
        seals[str(path.relative_to(ROOT))] = sha
        archive = OUTPUT / "source-archive" / (sha + ".py")
        if archive.exists():
            if digest(archive) != sha:
                raise ValueError("Source archive changed")
        else:
            archive.parent.mkdir(parents=True, exist_ok=True)
            with archive.open("xb") as stream:
                stream.write(path.read_bytes())
    write_new(destination / "ranking-execution-code.json", {"fold": fold, "files": seals, "snapshot_id": snapshot_id})
    recent = {row["row_key"]: row for row in expected_recent}
    completed = 0
    for entry in entries:
        benchmark = load(ROOT / entry["path"])
        train, test = old_train.partition_samples(benchmark, cohort, fold, "threshold")
        for artifact in by_benchmark[entry["key"]]:
            reference = catalog.ModelArtifactRef.from_mapping(artifact["artifact_ref"])
            model_ref = catalog.ModelRef.from_mapping({**reference.as_dict(), "horizon_days": 7})
            bundle = inference.load_exact_artifact(registry, manifest, model_ref,
                root=phase_root / "threshold/models", checked_manifest=manifest, artifact_row=artifact, cache=False)
            validate_bundle(bundle, reference, benchmark, train, events_by_key[tuning.decision_key(reference.as_dict())],
                summaries["ranking"], summaries["threshold"], snapshot_id)
            selected = [s for s in test if reference.species_id == "all_species" or s["metadata"]["species_id"] == reference.species_id]
            old_train.single_thread(bundle)
            predictions = predict_rows(bundle, selected, trainer._columns(reference, benchmark))
            for sample, prediction in zip(selected, predictions, strict=True):
                row = recent[entry["key"] + "|" + sample["sample_id"]]
                if reference.estimator_id in row["estimator_probabilities"]:
                    raise ValueError("Duplicate estimator prediction")
                row["estimator_probabilities"][reference.estimator_id] = prediction["probability"]
            completed += 1
            print(json.dumps({"fold": fold, "completed": completed, "planned": 168}), flush=True)
            del bundle, predictions
        del benchmark, train, test, selected
        gc.collect()
    recent_rows = list(recent.values())
    validate_evidence(recent_rows, expected_recent, estimators)
    combined = old_rows + recent_rows
    validate_evidence(combined, expected_old + expected_recent, estimators)
    paths_a = write_evidence(destination, "recent", recent_rows)
    paths_b = write_evidence(destination, "combined", combined)
    outputs = paths_a + paths_b
    for label, paths in (("A", paths_a), ("B", paths_b)):
        quality_path = destination / f"quality-{label}.json"
        write_new(quality_path, quality.build_catalog(*paths, **options))
        outputs.append(quality_path)
    verify_inputs(cohort)
    if any(digest(ROOT / path) != sha for path, sha in seals.items()):
        raise ValueError("A source or input changed during area evidence generation")
    write_new(destination / "ranking-provenance.json", {
        "fold": fold, "snapshot_id": snapshot_id, "inputs": seals,
        "recent_evaluation_role": "threshold", "recent_train_roles": ["fit", "ranking"],
        "recent_bundle_manifest": str((phase_root / "threshold/manifest.json").relative_to(ROOT)),
        "shared_final_manifest": str(external_manifest_path.relative_to(ROOT)),
        "A": {"years": [fold - 1], "rows": len(recent_rows)},
        "B": {"years": [fold - 2, fold - 1], "rows": len(combined)},
        "prevalence": "same species, same benchmark, eligible training rows of the generating bundle",
        "probability_precision_decimals": 6, "applicability_filter_applied": False,
        "technical_control_old_catalog_exact": True,
        "outputs": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in outputs],
    })
    summary = {"status": "completed", "fold": fold, "snapshot_id": snapshot_id, "models": completed,
        "old_rows": len(old_rows), "recent_rows": len(recent_rows), "combined_rows": len(combined),
        "recent_observations": {sid: len({r["observation_id"] for r in recent_rows if r["species_id"] == sid}) for sid in TARGETS},
        "physical_excluded_observations": 3 if fold == 2025 else 0,
        "physical_excluded_rows": sum(len(v) for v in exclusions.values()),
        "technical_control_old_catalog_exact": True, "inputs_verified_after": True}
    write_new(destination / "ranking-summary.json", summary)
    print(json.dumps(summary), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, choices=tuple(EXPECTED_RECENT_ROWS), required=True)
    run(parser.parse_args().fold)


if __name__ == "__main__":
    main()
