"""Resolve complete seven-day point forecasts with experiment-owned models."""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from datetime import date, timedelta
import json
import os
from pathlib import Path
import sys

from common import ROOT, OUTPUT, TARGETS, load, write_new, verify_inputs, digest, protect_originals

sys.path.insert(0, str(ROOT))
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_ml_quality_catalog as quality
from rainmapper_core import mushroom_ml_policy_store as policy_store
from rainmapper_core import mushroom_recommendation_policy as recommendations
from rainmapper_core import mushroom_ml_runtime_inference as inference
from rainmapper_core.mushroom_map_prediction import resolve_species_week
from rainmapper_core.mushroom_map_weather import PointWeatherReader
from rainmapper_core.mushroom_map_ecology import EcologyReader, prediction_candidates
from readonly_weather import frozen_weather
from recommendation_metrics import select_threshold, validate_rows


def evaluate_case(*, row, location, geography, issue, horizon, registry, manifest,
                  quality_catalog, models_root, resolutions, profiles, ecology_reader, weather, weather_cache,
                  installed_versions):
    """This function receives identity/context, but no observed outcome."""
    sid = row["species_id"]
    ecology = ecology_reader.evaluate(geography, issue.isoformat(), 7)
    candidates = prediction_candidates(ecology, [sid])
    if not candidates:
        species = next((r for r in ecology.get("species", []) if r["species_id"] == sid), {})
        return {"decision_a": "abstain", "probability": None, "winner": None,
                "reason": "territory_or_season_gate", "geography_status": species.get("status"),
                "geography_reasons": species.get("reasons", []), "trace": []}
    if not resolutions:
        return {"decision_a": "abstain", "probability": None, "winner": None,
                "reason": "no_model", "trace": []}
    if set(resolutions) != set(range(1, 8)):
        raise ValueError("Incomplete internally sealed weekly evidence")
    phenology = profiles[sid].get("phenology", {})
    from rainmapper_core.mushroom_phenology import season_phase_for_months
    def season(target):
        return season_phase_for_months(target, phenology.get("main_months", []), phenology.get("secondary_months", []))
    trace = []
    catalog_profiles = catalog.catalog_entries(registry)
    altitude = geography.get("terrain", {}).get("elevation", {}).get("value_m")
    soil = geography.get("model_soil_water")

    def materialize(*, target_date, selections):
        if season(target_date) not in ("main", "secondary"):
            return {"members": []}
        refs = []
        for selection in selections:
            try:
                refs.append(comparison.resolve_selection(registry, manifest, selection, species_id=sid,
                    checked_manifest=manifest, catalog_profiles=catalog_profiles))
            except FileNotFoundError:
                continue
        if not refs:
            return {"members": []}
        days, physical = comparison._weather_requirements(refs, catalog_profiles=catalog_profiles)
        series_by_horizon = {}
        for h in sorted({r.horizon_days for r in refs}):
            cutoff = target_date - timedelta(days=h)
            if cutoff >= issue:
                raise AssertionError("Forecast read reaches its issue day/future")
            key = (location["lat"], location["lon"], altitude, cutoff.isoformat(), days, physical,
                   (soil or {}).get("context_hash"))
            if key not in weather_cache:
                weather_cache[key] = weather.prepare_model_inputs(location["lat"], location["lon"], altitude,
                    end_day=cutoff, lookback_days=days, include_physical_state=physical,
                    soilgrids_context=soil, calendar_timezone="Europe/Madrid")
                if len(weather_cache) > 8:
                    weather_cache.popitem(last=False)
            weather_cache.move_to_end(key)
            context, series, stations = weather_cache[key]
            series_by_horizon[h] = series
        result = comparison.compare_prepared(registry, manifest, refs, models_root=models_root,
            target_date=target_date, area_id=context.area_id, area_context=context,
            area_series_by_horizon=series_by_horizon, stations=stations, checked_manifest=manifest,
            comparison_cache={"quality_catalog": quality_catalog})
        for member in result["members"]:
            if member.get("reason") == "runtime_model_incompatible":
                raise ValueError("Unexpected runtime incompatibility: " + str(member.get("message")))
            ref = member.get("model_ref") or {}
            trace.append({"target": target_date.isoformat(), "family": {k: ref.get(k) for k in recommendations.FAMILY},
                "horizon": ref.get("horizon_days"), "available": member.get("available"),
                "gate_failures": comparison._operational_gate_failures(member),
                "probability": (member.get("prediction") or {}).get("probability"), "reason": member.get("reason")})
        return result

    week = resolve_species_week(species_id=sid, point_id=row["observation_id"], issue_date=issue,
        resolutions_by_day=resolutions,
        installed_version_ids=installed_versions,
        materialize=materialize, season_phase=season, phenology=phenology, lazy_families=True,
        recommendation_policy=recommendations.settings(registry))
    selected = week["days"][horizon-1]
    if selected["target_date"] != row["date"]:
        raise AssertionError("Scored target is not the observed day")
    operation = selected["operational_comparison"]
    active = selected["reliability_selection"]
    winners = operation.get("selected_winners", [])
    winner = winners[0] if len(winners) == 1 else None
    interpretation = operation.get("interpretation") or {}
    verdict = interpretation.get("verdict")
    probability = winner.get("probability") if winner else None
    if season(date.fromisoformat(row["date"])) not in ("main", "secondary") or active.get("runtime_selection_status") == "abstain":
        probability = None
    decision = verdict if probability is not None and verdict in {"favorable", "unfavorable"} else "abstain"
    return {"decision_a": decision, "probability": probability,
            "winner": winner.get("model_ref") if winner and probability is not None else None,
            "verdict": verdict, "reason": operation.get("reason") or ("calculated" if decision != "abstain" else "uncertain_or_abstained"),
            "reason_codes": interpretation.get("reason_codes", []), "trace": trace,
            "weekly_days": [{"target_date": d["target_date"],
                "selection_status": d["reliability_selection"].get("runtime_selection_status"),
                "winner": (d["operational_comparison"].get("selected_winners") or [{}])[0].get("model_ref"),
                "verdict": (d["operational_comparison"].get("interpretation") or {}).get("verdict")} for d in week["days"]]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, choices=(2024, 2025, 2026), required=True)
    parser.add_argument("--phase", choices=("threshold", "external"), required=True)
    args = parser.parse_args()
    if os.environ.get("RAINMAPPER_PREDICTION_RESEARCH_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py")
    protect_originals()
    cohort = load(OUTPUT / "cohort-v2.json")
    verify_inputs(cohort)
    root = OUTPUT / f"fold-{args.fold}"
    stage = root / args.phase
    summary = load(stage / "summary.json")
    snapshot_id = "sha256:" + digest(OUTPUT / "cohort-v2.json")
    if (summary["status"], summary["fold"], summary["phase"], summary["snapshot_id"]) != ("completed", args.fold, args.phase, snapshot_id):
        raise ValueError("Model phase identity differs")
    registry_path = ROOT / "docker-data/mushroom-data/mushroom_ml_version_registry.json"
    registry = policy_store.resolve(registry_path, load(registry_path))
    manifest = catalog.validate_batch_manifest(registry, load(stage / "manifest.json"))
    installed_versions = list(dict.fromkeys(p["version_id"] for p in cohort["profiles"]))
    actual_versions = {a["artifact_ref"]["version_id"] for a in manifest["artifacts"]}
    if not actual_versions <= set(installed_versions):
        raise ValueError("Model version outside the frozen design")
    q = quality.validate_catalog(load(root / "ranking/quality.json"), require_selections=True)
    if q["snapshot_id"] != snapshot_id or manifest["snapshot_id"] != snapshot_id:
        raise ValueError("Mismatched quality/model snapshots")
    resolutions = {}
    for resolution in q["species_selections"]:
        resolutions.setdefault(resolution["species_id"], {})[resolution["prediction_day"]] = resolution
    base = ROOT / "docker-data/mushroom-data"
    profiles = {p["species_id"]: p for p in load(base / "mushroom_profiles.json")["species_profiles"]}
    ecology_reader = EcologyReader(str(base / "mushroom_profiles.json"), str(base / "mushroom_reference_catalogs.json"),
        str(base / "mushroom_gis_mappings.json"), ph_source=cohort["geography_config"].get("ecology_ph_source", "soilgrids"))
    geography = {r["id"]: r for r in map(json.loads, (OUTPUT / "geography.jsonl").read_text().splitlines()) if r["id"] != "capabilities"}
    observations = {o["observation_id"]: o for o in load(ROOT / cohort["observations_input"])["observations"]}
    cases = [r for r in cohort["rows"] if r["species_id"] in TARGETS and cohort["folds"][str(args.fold)][r["observation_id"]] == args.phase]
    if args.phase == "external":
        choice = load(root / "threshold-choice.json")
        if choice["fold"] != args.fold or choice["snapshot_id"] != snapshot_id or choice["source_role"] != "threshold":
            raise ValueError("Threshold choice identity mismatch")
        dependencies = load(stage / "execution-code.json")["files"]
        threshold_path = str((root / "threshold-choice.json").relative_to(ROOT))
        expected = next(r["sha256"] for r in dependencies if r["path"] == threshold_path)
        if digest(root / "threshold-choice.json") != expected:
            raise ValueError("Threshold changed since external refit")
    files = [Path(__file__), Path(__file__).with_name("common.py"), Path(__file__).with_name("readonly_weather.py"),
             Path(__file__).with_name("recommendation_metrics.py"), stage / "manifest.json", root / "ranking/quality.json",
             OUTPUT / "geography.jsonl"]
    if args.phase == "external":
        files.append(root / "threshold-choice.json")
    sealed = [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in files]
    write_new(stage / "evaluation-seal.json", {"files": sealed, "observations": len(cases), "scored_rows": len(cases)*7,
        "week_target_count_before_reuse": len(cases)*49, "weather_cache_entries": 8, "snapshot_id": snapshot_id})
    inference.clear_artifact_cache()
    rows = []
    weather = PointWeatherReader(str(ROOT / "docker-data/Data"), str(ROOT / "docker-data/stations.txt"))
    with frozen_weather():
        weather._refresh()
        weather_identity = weather._identity
        with (stage / "predictions.jsonl").open("x") as stream:
            for index, observed in enumerate(cases):
                weather_cache = OrderedDict()
                no_label = {k: observed[k] for k in ("observation_id", "species_id", "date")}
                for horizon in range(1, 8):
                    issue = date.fromisoformat(observed["date"]) - timedelta(days=horizon-1)
                    result = evaluate_case(row=no_label, location=observations[observed["observation_id"]]["location"],
                        geography=geography[observed["observation_id"]], issue=issue, horizon=horizon, registry=registry,
                        manifest=manifest, quality_catalog=q, models_root=stage / "models",
                        resolutions=resolutions.get(observed["species_id"]), profiles=profiles,
                        ecology_reader=ecology_reader, weather=weather, weather_cache=weather_cache,
                        installed_versions=installed_versions)
                    if weather._identity != weather_identity:
                        raise ValueError("Weather changed during experimental inference")
                    result.update(observation_id=observed["observation_id"], species_id=observed["species_id"],
                        episode_id=observed["episode_id"], target_date=observed["date"], issue_date=issue.isoformat(),
                        horizon=horizon, fold=args.fold, phase=args.phase, y=observed["y"])
                    stream.write(json.dumps(result) + "\n"); stream.flush()
                    rows.append({k: value for k, value in result.items() if k not in ("trace", "weekly_days")})
                print(json.dumps({"observations_completed": index+1, "observations_planned": len(cases), "phase": args.phase}), flush=True)
    validate_rows(rows)
    verify_inputs(cohort)
    if any(digest(ROOT / r["path"]) != r["sha256"] for r in sealed):
        raise ValueError("Code/evidence changed during inference")
    if args.phase == "threshold":
        write_new(root / "threshold-choice.json", {"schema": 1, "fold": args.fold, "snapshot_id": snapshot_id,
            "source_role": "threshold", "predictions_sha256": digest(stage / "predictions.jsonl"),
            "selection_rule": "predeclared_grid_utility_then_false_favorable_v1",
            "species": {s: select_threshold([r for r in rows if r["species_id"] == s]) for s in TARGETS}})
    write_new(stage / "evaluation-summary.json", {"status": "completed", "fold": args.fold, "phase": args.phase,
        "snapshot_id": snapshot_id, "observations": len(cases), "predictions": len(rows),
        "decision_counts": dict(Counter(r["decision_a"] for r in rows)), "inputs_verified_after": True,
        "predictions_sha256": digest(stage / "predictions.jsonl")})
    inference.clear_artifact_cache()


if __name__ == "__main__":
    main()
