"""D only: frozen annual evidence, no operational writes or network access."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, OrderedDict
from datetime import date, timedelta
import gc
import json
import os
from pathlib import Path
import runpy
import sys
import time
import warnings

sys.dont_write_bytecode = True
ROOT_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_PATH))
sys.path.insert(0, str(ROOT_PATH / "scripts/prediction_research"))
from scripts.prediction_model_selection_d.common import ROOT, OUTPUT, OLD_OUTPUT, TARGETS, load, digest, write_new, protect_originals
from scripts.prediction_model_selection import ranking, evaluate
from scripts.prediction_research import train_fold
from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_runtime_inference as inference
from rainmapper_core import mushroom_ml_quality_catalog as quality
from rainmapper_core import mushroom_ml_tuning_catalog as tuning
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth

PREVIOUS = ROOT / "tmp/prediction-model-selection"
PROTOCOL = ROOT / "docs/agents/prediction-model-selection/protocolo-D-2026-10-05.md"
YEARS = tuple(range(2015, 2022))
COHORT = OLD_OUTPUT / "cohort-v2.json"
HISTORICAL = OUTPUT / "historical-v2"


def memberships(rows, year):
    boundaries = (date(year, 1, 1), date(year + 1, 1, 1))
    groups = defaultdict(list)
    for r in rows:
        groups[r["episode_id"]].append(date.fromisoformat(r["date"]))
    purged = {g for g, dates in groups.items() if any(
        min(dates) < boundary <= max(dates) or any(abs((d-boundary).days) <= 14 for d in dates)
        for boundary in boundaries)}
    return {r["observation_id"]: "purged" if r["episode_id"] in purged else
        "train" if r["date"] < boundaries[0].isoformat() else
        "test" if r["date"] < boundaries[1].isoformat() else "future" for r in rows}


def partition(benchmark, cohort, year):
    roles = memberships(cohort["rows"], year)
    train, test = [], []
    for sample in holdout.eligible_samples(benchmark):
        m = sample["metadata"]
        role = roles[m["observation_id"]]
        if role == "train":
            train.append(sample)
        elif role == "test" and m["species_id"] in TARGETS:
            test.append(sample)
    a = {r["metadata"]["research_episode_id"] for r in train}
    b = {r["metadata"]["research_episode_id"] for r in test}
    if a & b:
        raise ValueError("Cross-species episode overlap")
    if train and test and max(r["metadata"]["target_date"] for r in train) >= min(r["metadata"]["target_date"] for r in test):
        raise ValueError("Training is not strictly before evaluation")
    return train, test


def checked_inputs():
    inv = load(OUTPUT / "inventory.json")
    for p, sha in inv["inputs"].items():
        if digest(ROOT / p) != sha:
            raise ValueError("Study input changed: " + p)
    return inv


def inventory():
    previous = load(PREVIOUS / "inventory-d-2026-10-05.json")
    for p, sha in previous["inputs_sha256"].items():
        if digest(ROOT / p) != sha:
            raise ValueError("Read-only inventory input changed: " + p)
    cohort = load(COHORT)
    manifest = load(OLD_OUTPUT / "benchmarks/manifest.json")
    paths = {COHORT, PROTOCOL, OLD_OUTPUT / "benchmarks/manifest.json", PREVIOUS / "inventory-d-2026-10-05.json"}
    paths.update(ROOT / p for p in previous["inputs_sha256"])
    paths.update(ROOT / e["path"] for e in manifest["benchmarks"])
    # Freeze all original cohort inputs at their current bytes, checking data
    # separately from historical source snapshots. No source fallback is executed.
    original_changes = []
    non_consumed_input_changes = []
    raw_weather_changes = []
    for entry in cohort["inputs"]:
        p = ROOT / entry["path"]
        same = p.exists() and digest(p) == entry["sha256"]
        if not same and (p.name in {"mushroom_observations.json", "mushroom_known_sites.json"}):
            non_consumed_input_changes.append({"path": entry["path"], "reason": "sealed_cohort_benchmarks_and_private_observation_snapshot_replace_operational_input"})
            continue
        if not same and "weather-history/" in entry["path"]:
            raw_weather_changes.append({"path": entry["path"], "status": "changed" if p.exists() else "missing", "original_sha256": entry["sha256"]})
            continue
        paths.add(p)
        if not same:
            if p.suffix != ".py":
                raise ValueError("Original data/configuration changed: " + str(p))
            original_changes.append(entry["path"])
    for year in (2024, 2025, 2026):
        paths.update((PREVIOUS / f"fold-{year}").glob("*.json"))
        paths.update((PREVIOUS / f"fold-{year}").glob("*.jsonl"))
        paths.update((PREVIOUS / f"fold-{year}/evaluation").glob("*.json*"))
        paths.update((OLD_OUTPUT / f"fold-{year}/external").glob("*.json"))
        models = load(OLD_OUTPUT / f"fold-{year}/external/manifest.json")
        for artifact in models["artifacts"]:
            p = OLD_OUTPUT / f"fold-{year}/external/models" / artifact["path"]
            if digest(p) != artifact["sha256"]:
                raise ValueError("Final model differs from its receipt")
            paths.add(p)
    paths.add(OLD_OUTPUT / "geography.jsonl")
    annual = {}
    for year in YEARS:
        roles = memberships(cohort["rows"], year)
        annual[str(year)] = {}
        for sid in TARGETS:
            annual[str(year)][sid] = {role: {
                "n": len(rows := [r for r in cohort["rows"] if r["species_id"] == sid and roles[r["observation_id"]] == role]),
                "positive": sum(r["y"] for r in rows), "negative": sum(1-r["y"] for r in rows),
                "episodes": len({r["episode_id"] for r in rows})} for role in ("train", "test", "purged")}
    references = load(OLD_OUTPUT / "fold-2024/external/manifest.json")["artifacts"]
    support = []
    for entry in manifest["benchmarks"]:
        p = ROOT / entry["path"]
        if digest(p) != entry["sha256"]:
            raise ValueError("Benchmark changed")
        bench = load(p)
        ranking.validate_samples(bench, entry["key"], cohort)
        refs = [r["artifact_ref"] for r in references if trainer.benchmark_key(r["artifact_ref"]["version_id"], r["artifact_ref"]["temporal_contract_id"], r["artifact_ref"]["profile_id"]) == entry["key"]]
        for year in YEARS:
            train, test = partition(bench, cohort, year)
            prior_species = {s["metadata"]["species_id"] for s in train}
            for ref in refs:
                tr = [r for r in train if ref["species_id"] == "all_species" or r["metadata"]["species_id"] == ref["species_id"]]
                te = [r for r in test if (ref["species_id"] == "all_species" or r["metadata"]["species_id"] == ref["species_id"]) and r["metadata"]["species_id"] in prior_species]
                support.append({"year": year, "key": tuning.decision_key(ref),
                    "train_samples": len(tr), "train_observations": len({r["metadata"]["observation_id"] for r in tr}),
                    "train_classes": sorted({r["prediction_target"] for r in tr}),
                    "test_samples": len(te), "test_observations": len({r["metadata"]["observation_id"] for r in te}),
                    "attempt": bool(te) and len({r["prediction_target"] for r in tr}) == 2})
        del bench
        gc.collect()
    result = {"status": "sealed", "protocol_sha256": digest(PROTOCOL), "cohort_sha256": digest(COHORT),
        "inputs": {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}, "annual": annual,
        "candidate_support": support, "planned_attempts_upper": sum(r["attempt"] for r in support),
        "old_source_changes": original_changes, "created_at_epoch": time.time(),
        "non_consumed_input_changes": non_consumed_input_changes,
        "raw_weather_changes": raw_weather_changes,
        "point_evaluation_ready": not raw_weather_changes,
        "resource_limit": {"seconds": 3600, "output_bytes": 512*1024**2, "rss_bytes": 8*1024**3},
        "new_annual_evidence_rows_upper": 42*88, "external_emissions": 812}
    write_new(OUTPUT / "inventory.json", result)
    print(json.dumps({k: result[k] for k in ("status", "planned_attempts_upper", "old_source_changes", "annual")}))


def historical():
    inv = checked_inputs()
    if inv["old_source_changes"]:
        # Changes must be audited and acknowledged explicitly, never silently.
        review = load(OUTPUT / "source-change-review.json")
        if set(review["non_consumed_changes"]) != set(inv["old_source_changes"]):
            raise ValueError("Historical source changes have not been accounted for")
    cohort, manifest = load(COHORT), load(OLD_OUTPUT / "benchmarks/manifest.json")
    references = load(OLD_OUTPUT / "fold-2024/external/manifest.json")["artifacts"]
    selector = runpy.run_path(str(ROOT / "scripts/evaluate-biology-v6-smooth-hierarchical.py"))["select_joint_config"]
    destination = HISTORICAL
    destination.mkdir(exist_ok=False)
    evidence, missing, events = [], [], []
    for entry in manifest["benchmarks"]:
        bench = load(ROOT / entry["path"])
        refs = [r["artifact_ref"] for r in references if trainer.benchmark_key(r["artifact_ref"]["version_id"], r["artifact_ref"]["temporal_contract_id"], r["artifact_ref"]["profile_id"]) == entry["key"]]
        eligible_ids = {r["sample_id"] for r in holdout.eligible_samples(bench)}
        for year in YEARS:
            train, test = partition(bench, cohort, year)
            roles = memberships(cohort["rows"], year)
            prior = {r["metadata"]["species_id"] for r in train}
            valid_test = [r for r in test if r["metadata"]["species_id"] in prior]
            for s in bench["samples"]:
                m = s["metadata"]
                if m["species_id"] not in TARGETS or int(m["target_date"][:4]) != year:
                    continue
                cause = "purged_episode" if roles[m["observation_id"]] == "purged" else "profile_ineligible" if s["sample_id"] not in eligible_ids else "no_previous_species_prevalence" if m["species_id"] not in prior else None
                if cause:
                    missing.append({"year": year, "benchmark": entry["key"], "observation_id": m["observation_id"], "species_id": m["species_id"], "horizon": m["horizon_days"], "reason": cause, "detail": s.get("quality", {}).get("training_exclusion_reasons", [])})
            rows = {r["sample_id"]: r for r in ranking.evidence_rows(entry["key"], train, valid_test)}
            filtered = {**bench, "samples": train}
            prepared_cache = {}
            for ref in refs:
                ref = {**ref, "batch_id": f"D_historical_{year}", "generation_id": f"{ref['version_id']}_D_{year}"}
                reference = catalog.ModelArtifactRef.from_mapping(ref)
                key = tuning.decision_key(ref)
                selected = [r for r in valid_test if reference.species_id == "all_species" or r["metadata"]["species_id"] == reference.species_id]
                event = {"year": year, "key": key, "available": False, "test_samples": len(selected)}
                start = time.monotonic()
                try:
                    if not selected:
                        event["reason"] = "no_evaluable_target_samples"
                    else:
                        if reference.species_id not in prepared_cache:
                            prepared_cache[reference.species_id] = trainer._prepare_fit_inputs(reference, filtered)
                        prepared = prepared_cache[reference.species_id]
                        decision = None
                        if reference.version_id == smooth.WINDOWED_VERSION_ID:
                            config, provenance = train_fold.initial_v6_decision(reference, prepared, selector)
                            decision = {"key": key, "fit_config": config}
                            event["tuning_provenance"] = provenance
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter("always")
                            bundle = trainer.fit_artifact(reference, filtered, snapshot_id="sha256:"+inv["cohort_sha256"], tuning_decision=decision, prepared_inputs=prepared)
                        train_fold.single_thread(bundle)
                        predictions = ranking.predict_rows(bundle, selected, trainer._columns(reference, bench))
                        for sample, prediction in zip(selected, predictions, strict=True):
                            rows[sample["sample_id"]]["estimator_probabilities"][reference.estimator_id] = prediction["probability"]
                        event.update(available=True, train_samples=len(prepared["samples"]),
                            train_observations=len({s["metadata"]["observation_id"] for s in prepared["samples"]}),
                            train_ids=sorted({s["metadata"]["observation_id"] for s in prepared["samples"]}),
                            test_ids=sorted({s["metadata"]["observation_id"] for s in selected}),
                            fit_config=bundle["fit_config"], warnings=dict(Counter(type(w.message).__name__ for w in caught)))
                        del bundle, predictions
                except (ValueError, FloatingPointError) as exc:
                    expected = ("No eligible rows", "requires both classes", "requires at least seven", "calibration requires", "sparse-group estimator did not converge", "sparse-group logistic did not converge within 2000 iterations")
                    if not any(s in str(exc) for s in expected):
                        raise
                    event["reason"] = str(exc)
                event["seconds"] = time.monotonic()-start
                events.append(event)
                with (destination / "fit-events.jsonl").open("a") as stream:
                    stream.write(json.dumps(event)+"\n")
            evidence.extend(rows.values())
        print(json.dumps({"benchmark_completed": entry["key"], "candidate_events": len(events), "successful_fits": sum(e["available"] for e in events)}), flush=True)
        del bench, train, test, filtered, prepared_cache
        gc.collect()
    paths = ranking.write_evidence(destination, "ranking", evidence)
    write_new(destination / "missing.json", missing)
    checked_inputs()
    write_new(destination / "summary.json", {"status": "completed", "candidate_events": len(events),
        "successful_fits": sum(e["available"] for e in events), "ranking_rows": len(evidence),
        "years_with_probabilities": dict(Counter(r["target_date"][:4] for r in evidence if r["estimator_probabilities"])),
        "files": {str(p.relative_to(ROOT)): digest(p) for p in paths}})


def rank_all():
    inv = checked_inputs()
    cohort = load(COHORT)
    historical_rows = [r for family in ("v2-v5", "v6") for r in ranking.read_rows(HISTORICAL / f"ranking-{family}.jsonl")]
    estimators = {p["version_id"]+"/"+p["profile_id"]: p["estimator_ids"] for p in cohort["profiles"]}
    options = {"snapshot_id": "sha256:"+inv["cohort_sha256"], "profile_keys": list(estimators), "expected_estimators": estimators}
    for year in (2024, 2025, 2026):
        destination = OUTPUT / f"fold-{year}"
        destination.mkdir(exist_ok=False)
        sources = [PREVIOUS / f"fold-{year}/combined-{f}.jsonl" for f in ("v2-v5", "v6")]
        for older in range(2022, year-2):
            sources += [OLD_OUTPUT / f"fold-{older+2}/ranking/ranking-{f}.jsonl" for f in ("v2-v5", "v6")]
        rows = [*historical_rows, *(r for p in sources for r in ranking.read_rows(p))]
        if len({r["row_key"] for r in rows}) != len(rows) or any(int(r["target_date"][:4]) >= year for r in rows):
            raise ValueError("Duplicate years/rows or future ranking evidence")
        external_episodes = {r["episode_id"] for r in cohort["rows"] if cohort["folds"][str(year)][r["observation_id"]] == "external"}
        if external_episodes & {r["validation_group_id"] for r in rows}:
            raise ValueError("Ranking/external episode overlap")
        paths = ranking.write_evidence(destination, "combined-D", rows)
        q = quality.build_catalog(*paths, **options)
        quality.validate_catalog(q, require_selections=True)
        write_new(destination / "quality-D.json", q)
        write_new(destination / "ranking-provenance.json", {"fold": year, "source_files": {str(p.relative_to(ROOT)): digest(p) for p in sources},
            "historical_files": load(HISTORICAL / "summary.json")["files"], "rows": len(rows),
            "species_observations_with_probability": {sid: len({r["observation_id"] for r in rows if r["species_id"] == sid and r["estimator_probabilities"]}) for sid in TARGETS},
            "years": sorted({r["target_date"][:4] for r in rows if r["estimator_probabilities"]}), "quality_sha256": digest(destination / "quality-D.json")})
        print(json.dumps({"fold": year, "rows": len(rows), "quality_sha256": digest(destination / "quality-D.json")}), flush=True)


def point_evaluate(year):
    inv = checked_inputs()
    if not inv["point_evaluation_ready"]:
        raise ValueError("Original point-weather snapshot is unavailable; cannot compare D to saved A/B/C using changed weather")
    cohort = load(COHORT)
    legacy = evaluate.legacy
    old_stage = OLD_OUTPUT / f"fold-{year}/external"
    stage = OUTPUT / f"fold-{year}/evaluation"
    stage.mkdir(exist_ok=False)
    registry_path = ROOT / "docker-data/mushroom-data/mushroom_ml_version_registry.json"
    registry = legacy.policy_store.resolve(registry_path, load(registry_path))
    if legacy.recommendations.settings(registry)["mode"] != "shadow":
        raise ValueError("Frozen policy must remain shadow")
    manifest = legacy.catalog.validate_batch_manifest(registry, load(old_stage / "manifest.json"))
    q = quality.validate_catalog(load(OUTPUT / f"fold-{year}/quality-D.json"), require_selections=True)
    indexed = evaluate.index_resolutions(q)
    cases = [r for r in cohort["rows"] if r["species_id"] in TARGETS and cohort["folds"][str(year)][r["observation_id"]] == "external"]
    planned = evaluate.cardinality(cases, {"D": indexed})
    write_new(stage / "seal.json", {"fold": year, "quality_sha256": digest(OUTPUT / f"fold-{year}/quality-D.json"), "cardinality": planned,
        "models_manifest_sha256": digest(old_stage / "manifest.json"), "protocol_sha256": inv["protocol_sha256"]})
    base = ROOT / "docker-data/mushroom-data"
    profiles = {p["species_id"]: p for p in load(base / "mushroom_profiles.json")["species_profiles"]}
    ecology = legacy.EcologyReader(str(base / "mushroom_profiles.json"), str(base / "mushroom_reference_catalogs.json"), str(base / "mushroom_gis_mappings.json"), ph_source=cohort["geography_config"].get("ecology_ph_source", "soilgrids"))
    geography = {r["id"]: r for r in ranking.read_rows(OLD_OUTPUT / "geography.jsonl") if r["id"] != "capabilities"}
    observations = {r["observation_id"]: r for r in load(ROOT / cohort["observations_input"])["observations"]}
    previous = {(r["observation_id"], r["horizon"]): r for r in ranking.read_rows(PREVIOUS / f"fold-{year}/evaluation/predictions.jsonl")}
    versions = list(dict.fromkeys(p["version_id"] for p in cohort["profiles"]))
    weather = legacy.PointWeatherReader(str(ROOT / "docker-data/Data"), str(ROOT / "docker-data/stations.txt"))
    legacy.inference.clear_artifact_cache()
    counts = Counter()
    with legacy.frozen_weather():
        weather._refresh()
        identity = weather._identity
        with (stage / "predictions.jsonl").open("x") as stream:
            for index, observed in enumerate(cases):
                cache = OrderedDict()
                for horizon in range(1, 8):
                    issue = date.fromisoformat(observed["date"])-timedelta(days=horizon-1)
                    materializations = []
                    with evaluate.materialization_contracts(materializations):
                        result = legacy.evaluate_case(row={k: observed[k] for k in ("observation_id", "species_id", "date")}, location=observations[observed["observation_id"]]["location"], geography=geography[observed["observation_id"]], issue=issue, horizon=horizon, registry=registry, manifest=manifest, quality_catalog=q, models_root=old_stage / "models", resolutions=indexed.get(observed["species_id"]), profiles=profiles, ecology_reader=ecology, weather=weather, weather_cache=cache, installed_versions=versions)
                    result["decision"] = result.pop("decision_a")
                    result["input_contracts"] = materializations
                    # Shared D/B requests must retain exact meteorological requirements.
                    check = evaluate.compare_input_contracts(previous[(observed["observation_id"], horizon)]["B"]["input_contracts"], materializations)
                    if check["status"] != "passed":
                        raise ValueError("D/B input preparation mismatch")
                    if weather._identity != identity:
                        raise ValueError("Weather changed")
                    if result["decision"] == "favorable" and (result["probability"] is None or result["probability"] < .6):
                        raise ValueError("Favorable threshold changed")
                    payload = {"observation_id": observed["observation_id"], "species_id": observed["species_id"], "episode_id": observed["episode_id"], "target_date": observed["date"], "issue_date": issue.isoformat(), "horizon": horizon, "fold": year, "phase": "external", "y": observed["y"], "D": result, "D_B_input_parity": check}
                    evaluate._write_line(stream, payload)
                    counts[result["decision"]] += 1
                    counts["input_shared_materializations"] += check["shared_materializations"]
                print(json.dumps({"fold": year, "completed_observations": index+1, "planned_observations": len(cases)}), flush=True)
    legacy.inference.clear_artifact_cache()
    checked_inputs()
    write_new(stage / "summary.json", {"status": "completed", "fold": year, "observations": len(cases), "emissions": len(cases)*7, "counts": dict(counts), "predictions_sha256": digest(stage / "predictions.jsonl"), "cardinality": planned})


def guard_probe():
    import subprocess
    import socket
    from threadpoolctl import threadpool_info
    checks = []
    for label, action in (
        ("subprocess_blocked", lambda: subprocess.run([sys.executable, "-c", "pass"])),
        ("network_blocked", lambda: socket.socket().connect(("127.0.0.1", 9))),
        ("outside_write_blocked", lambda: (ROOT / "tmp/forbidden-D-guard").open("w")),
    ):
        try:
            action()
        except PermissionError:
            checks.append(label)
        else:
            raise AssertionError("Isolation guard did not block " + label)
    pools = threadpool_info()
    if any(p["num_threads"] != 1 for p in pools):
        raise ValueError("A native compute threadpool has more than one thread")
    print(json.dumps({"checks": checks, "native_threadpools": [{"api": p["internal_api"], "threads": p["num_threads"]} for p in pools]}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("probe", "inventory", "historical", "ranking", "evaluate"))
    parser.add_argument("--year", type=int, choices=(2024, 2025, 2026))
    args = parser.parse_args()
    if os.environ.get("RAINMAPPER_D_GUARDED") != "1":
        raise SystemExit("Launch through D bounded.py")
    protect_originals()
    {"probe": guard_probe, "inventory": inventory, "historical": historical, "ranking": rank_all, "evaluate": lambda: point_evaluate(args.year)}[args.stage]()


if __name__ == "__main__":
    main()
