"""Compare recent, accumulated, and daily selectors on frozen point forecasts."""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from contextlib import contextmanager
import copy
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_PATH))
# The previous scripts have absolute helper imports. The new helpers always use
# their package name, so the two different output directories cannot collide.
sys.path.insert(0, str(ROOT_PATH / "scripts/prediction_research"))
from scripts.prediction_model_selection import common
from scripts.prediction_model_selection.daily import resolve_species_days
from scripts.prediction_research import evaluate_fold as legacy
from scripts.prediction_research.recommendation_metrics import validate_rows
from rainmapper_core.mushroom_predictor_precompute import weekly_aggregate_resolution_index

ROOT, OUTPUT, OLD_OUTPUT, TARGETS = common.ROOT, common.OUTPUT, common.OLD_OUTPUT, common.TARGETS
METHODS = ("A", "B", "C")
DAILY_INDEPENDENT = "independent_daily_family_v1"
DAILY_REUSE = "reuse_B_native_daily_fallback_v1"
SCIENTIFIC_FIELDS = (
    "decision_a", "probability", "winner", "verdict", "reason", "reason_codes",
    "geography_status", "geography_reasons", "trace", "weekly_days",
)


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def scientific_payload(value):
    """Compare all scientific outputs; observation identity is checked separately."""
    return {key: value.get(key) for key in SCIENTIFIC_FIELDS}


def compare_control(actual, expected):
    current, previous = scientific_payload(actual), scientific_payload(expected)
    differences = [key for key in SCIENTIFIC_FIELDS if current[key] != previous[key]]
    return {"status": "passed" if not differences else "failed",
            "different_fields": differences,
            "actual_sha256": json_hash(current), "expected_sha256": json_hash(previous)}


@contextmanager
def daily_resolver():
    """Inject only the resolver into the unchanged, sequential point evaluator."""
    previous = legacy.resolve_species_week
    legacy.resolve_species_week = resolve_species_days
    try:
        yield
    finally:
        legacy.resolve_species_week = previous


@contextmanager
def materialization_contracts(records):
    """Observe exact requests without changing their meteorology or inference."""
    previous_requirements = legacy.comparison._weather_requirements
    previous_compare = legacy.comparison.compare_prepared
    pending = None
    def requirements(refs, **keywords):
        nonlocal pending
        value = previous_requirements(refs, **keywords)
        pending = ({ref.key for ref in refs}, value)
        return value
    def compare(registry, manifest, refs, **keywords):
        if pending is None or pending[0] != {ref.key for ref in refs}:
            raise ValueError("Materialization has no observed weather contract")
        days, physical = pending[1]
        target = keywords["target_date"]
        for ref in refs:
            records.append({"model_ref": ref.as_dict(), "target_date": target.isoformat(),
                "cutoff_date": (target - timedelta(days=ref.horizon_days)).isoformat(),
                "weather_lookback_days": days, "include_physical_state": physical})
        return previous_compare(registry, manifest, refs, **keywords)
    legacy.comparison._weather_requirements = requirements
    legacy.comparison.compare_prepared = compare
    try:
        yield
    finally:
        legacy.comparison._weather_requirements = previous_requirements
        legacy.comparison.compare_prepared = previous_compare


def compare_input_contracts(left, right):
    """Reject C/B differences for the same materialized model/target/cutoff."""
    def indexed(rows):
        result = {}
        for row in rows:
            key = json_hash({key: row[key] for key in ("model_ref", "target_date", "cutoff_date")})
            value = (row["weather_lookback_days"], row["include_physical_state"])
            if key in result and result[key] != value:
                raise ValueError("One method prepared the same model with unlike weather inputs")
            result[key] = value
        return result
    a, b = indexed(left), indexed(right)
    common_keys = set(a) & set(b)
    mismatches = sorted(key for key in common_keys if a[key] != b[key])
    return {"status": "passed" if not mismatches else "failed",
            "shared_materializations": len(common_keys),
            "only_B_materializations": len(set(a) - set(b)),
            "only_C_materializations": len(set(b) - set(a)),
            "mismatched_materializations": len(mismatches), "mismatched_key_hashes": mismatches}


def index_resolutions(catalog):
    result = {}
    for resolution in catalog["species_selections"]:
        key = (resolution["species_id"], resolution["prediction_day"])
        if key[1] in result.get(key[0], {}):
            raise ValueError("Duplicate catalog species/day")
        result.setdefault(key[0], {})[key[1]] = resolution
    for sid in TARGETS:
        if sid in result and set(result[sid]) != set(range(1, 8)):
            raise ValueError("Incomplete catalog species/week")
    return result


def daily_execution_plan(resolutions, *, species_id, installed_version_ids, quality_sha256):
    """Choose C's execution route from sealed metadata, before point inference.

    B's native daily_fallback already uses the same daily evidence order, gates,
    models and interpretation as C. Reusing that complete native result retains
    its mixed-batch input preparation exactly. Other weeks keep C's daily path.
    """
    raw = resolutions or {}
    if raw and (set(raw) != set(range(1, 8)) or any(type(day) is not int for day in raw)):
        raise ValueError("Incomplete C execution-plan week")
    for row in raw.values():
        if row.get("runtime_selection_status") or row.get("weekly_model_selection"):
            raise ValueError("C execution plan requires original catalog chains")
    aggregate = weekly_aggregate_resolution_index(
        {(species_id, "catalog_plan", day): row for day, row in raw.items()},
        installed_version_ids=installed_version_ids) if raw else {}
    states = [{"day": day, "selection_status": row["selection_status"],
               "weekly_status": (row.get("weekly_model_selection") or {}).get("status", "weekly"
                   if row.get("weekly_model_selection") else "absent")}
              for (_sid, _point, day), row in sorted(aggregate.items())]
    reuse = len(states) == 7 and all(row["weekly_status"] == "daily_fallback" for row in states)
    plan = {"mode": DAILY_REUSE if reuse else DAILY_INDEPENDENT,
            "reason": "B_already_resolves_original_daily_chains" if reuse else "C_resolves_original_daily_chains_independently",
            "species_id": species_id, "quality_sha256": quality_sha256,
            "raw_resolutions_sha256": json_hash(raw),
            "aggregate_plan_sha256": json_hash({str(day): row for (_sid, _point, day), row in aggregate.items()}),
            "catalog_states": states, "depends_on_point_probabilities": False,
            "depends_on_observed_outcome": False}
    return {**plan, "sha256": json_hash(plan)}


def reuse_native_daily_result(result_b, contracts_b, plan):
    if plan.get("mode") != DAILY_REUSE or not plan.get("catalog_states") or any(
            state["weekly_status"] != "daily_fallback" for state in plan["catalog_states"]):
        raise ValueError("Native B result reuse requires the predeclared daily-fallback plan")
    return copy.deepcopy(result_b), copy.deepcopy(contracts_b)


def cardinality(cases, indexed):
    """Bound requests before weather/features/inference; do not load private rows."""
    observations = Counter(row["species_id"] for row in cases)
    per_method = {}
    for method, by_species in indexed.items():
        counts = {}
        for sid in TARGETS:
            per_week = sum(len(legacy.comparison.reliability_candidate_selections(resolution))
                           for resolution in by_species.get(sid, {}).values())
            counts[sid] = {
                "observations": observations[sid], "emissions": observations[sid] * 7,
                "week_targets": observations[sid] * 49,
                "candidate_requests_upper_bound": observations[sid] * 7 * per_week,
                "candidate_entries_per_week_before_runtime_veto": per_week,
            }
        per_method[method] = counts
    return {"observations": len(cases), "scored_emissions": len(cases) * 7,
            "week_targets_per_method": len(cases) * 49,
            "methods_including_technical_control": len(indexed), "per_method": per_method,
            "weather_cache_max_entries": 8,
            "cache_scope": "one observation; exact coordinates/altitude/cutoff/lookback/physical/soil",
            "prediction_cache_between_methods": False,
            "candidate_limit_is_upper_bound_not_independent_observations": True}


def _write_line(stream, row):
    stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    stream.flush()


def _checked_old(path, inventory):
    relative = str(path.relative_to(ROOT))
    record = next((r for r in inventory["old_files"] if r["path"] == relative), None)
    if record is None or common.digest(path) != record["sha256"]:
        raise ValueError("Frozen predecessor file changed: " + relative)
    return common.load(path)


def _read_controls(path, cohort, fold, cases, inventory):
    relative = str(path.relative_to(ROOT))
    expected_hash = next((r["sha256"] for r in inventory["old_files"] if r["path"] == relative), None)
    if expected_hash != common.digest(path):
        raise ValueError("Technical-control predictions differ from frozen inventory")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    validate_rows(rows)
    observations = {r["observation_id"]: r for r in cases}
    if {r["observation_id"] for r in rows} != set(observations):
        raise ValueError("Technical control has different external observations")
    controls = {}
    for row in rows:
        observation = observations[row["observation_id"]]
        if row["fold"] != fold or row["phase"] != "external" or any(
                row[key] != observation[key] for key in ("species_id", "episode_id", "y")):
            raise ValueError("Technical-control identity differs")
        issue = date.fromisoformat(observation["date"]) - timedelta(days=row["horizon"] - 1)
        if row["target_date"] != observation["date"] or row["issue_date"] != issue.isoformat():
            raise ValueError("Technical-control target/issue differs")
        controls[(row["observation_id"], row["horizon"])] = row
    return controls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, choices=(2024, 2025, 2026), required=True)
    args = parser.parse_args()
    if os.environ.get("RAINMAPPER_MODEL_SELECTION_GUARDED") != "1":
        raise SystemExit("Launch through prediction_model_selection/bounded.py")
    common.protect_originals()
    inventory_path = OUTPUT / "inventory.json"
    inventory = common.load(inventory_path)
    if inventory.get("status") != "verified":
        raise ValueError("The predecessor inventory is not verified")
    protocol = inventory["protocol"]
    if common.digest(ROOT / protocol["path"]) != protocol["sha256"]:
        raise ValueError("Protocol changed since inventory")
    cohort_path = OLD_OUTPUT / "cohort-v2.json"
    cohort = _checked_old(cohort_path, inventory)
    if common.digest(cohort_path) != inventory["cohort_sha256"]:
        raise ValueError("Inventory/cohort identity mismatch")
    common.verify_inputs(cohort)
    snapshot = "sha256:" + common.digest(cohort_path)
    old_fold = OLD_OUTPUT / f"fold-{args.fold}"
    old_stage = old_fold / "external"
    stage = OUTPUT / f"fold-{args.fold}/evaluation"
    if stage.exists():
        raise ValueError("Refusing to overwrite a point evaluation")
    fit_summary = _checked_old(old_stage / "summary.json", inventory)
    if (fit_summary["status"], fit_summary["fold"], fit_summary["phase"], fit_summary["snapshot_id"]) != (
            "completed", args.fold, "external", snapshot):
        raise ValueError("External model phase identity differs")
    registry_path = ROOT / "docker-data/mushroom-data/mushroom_ml_version_registry.json"
    registry = legacy.policy_store.resolve(registry_path, common.load(registry_path))
    if legacy.recommendations.settings(registry)["mode"] != "shadow":
        raise ValueError("The frozen research design requires shadow policy")
    manifest_path = old_stage / "manifest.json"
    manifest = legacy.catalog.validate_batch_manifest(registry, _checked_old(manifest_path, inventory))
    if manifest["snapshot_id"] != snapshot:
        raise ValueError("External model snapshot differs")
    models_root = old_stage / "models"
    for artifact in manifest["artifacts"]:
        if common.digest(models_root / artifact["path"]) != artifact["sha256"]:
            raise ValueError("External artifact changed before evaluation")
    quality_paths = {"control": old_fold / "ranking/quality.json",
                     "A": OUTPUT / f"fold-{args.fold}/quality-A.json",
                     "B": OUTPUT / f"fold-{args.fold}/quality-B.json"}
    catalogs = {name: legacy.quality.validate_catalog(
        _checked_old(path, inventory) if name == "control" else common.load(path), require_selections=True)
        for name, path in quality_paths.items()}
    if any(q["snapshot_id"] != snapshot for q in catalogs.values()):
        raise ValueError("Quality/model snapshot mismatch")
    catalogs["C"] = catalogs["B"]
    indexed = {name: index_resolutions(q) for name, q in catalogs.items()}
    cases = [row for row in cohort["rows"] if row["species_id"] in TARGETS
             and cohort["folds"][str(args.fold)][row["observation_id"]] == "external"]
    control_path = old_stage / "predictions.jsonl"
    controls = _read_controls(control_path, cohort, args.fold, cases, inventory)
    planned = cardinality(cases, indexed)
    versions = list(dict.fromkeys(p["version_id"] for p in cohort["profiles"]))
    if not {a["artifact_ref"]["version_id"] for a in manifest["artifacts"]} <= set(versions):
        raise ValueError("External models contain an unfrozen version")
    c_plans = {sid: daily_execution_plan(indexed["B"].get(sid), species_id=sid,
        installed_version_ids=versions, quality_sha256=common.digest(quality_paths["B"])) for sid in TARGETS}
    planned["C_execution_plans"] = c_plans
    base = ROOT / "docker-data/mushroom-data"
    profiles = {p["species_id"]: p for p in common.load(base / "mushroom_profiles.json")["species_profiles"]}
    ecology = legacy.EcologyReader(str(base / "mushroom_profiles.json"),
        str(base / "mushroom_reference_catalogs.json"), str(base / "mushroom_gis_mappings.json"),
        ph_source=cohort["geography_config"].get("ecology_ph_source", "soilgrids"))
    geography_path = OLD_OUTPUT / "geography.jsonl"
    geography_hash = next(r["sha256"] for r in inventory["old_files"]
                          if r["path"] == str(geography_path.relative_to(ROOT)))
    if common.digest(geography_path) != geography_hash:
        raise ValueError("Prepared geography changed")
    geography = {r["id"]: r for r in map(json.loads, geography_path.read_text().splitlines())
                 if r["id"] != "capabilities"}
    observations = {o["observation_id"]: o for o in common.load(ROOT / cohort["observations_input"])["observations"]}
    files = [Path(__file__), Path(__file__).with_name("daily.py"), Path(common.__file__),
             ROOT / "scripts/prediction_research/evaluate_fold.py",
             ROOT / "scripts/prediction_research/common.py",
             ROOT / "scripts/prediction_research/readonly_weather.py",
             ROOT / "scripts/prediction_research/recommendation_metrics.py",
             inventory_path, cohort_path, manifest_path, control_path, geography_path,
             ROOT / protocol["path"],
             ROOT / "docs/agents/prediction-model-selection/protocolo-control-entradas-2026-10-04.md",
             ROOT / "docs/agents/prediction-model-selection/protocolo-correccion-daily-fallback-2026-10-04.md",
             *quality_paths.values()]
    sealed = [{"path": str(p.relative_to(ROOT)), "sha256": common.digest(p)} for p in files]
    common.write_new(stage / "evaluation-seal.json", {
        "schema": 1, "fold": args.fold, "phase": "external", "snapshot_id": snapshot,
        "files": sealed, "cardinality": planned,
        "model_hashes": [{"path": str((models_root / a["path"]).relative_to(ROOT)), "sha256": a["sha256"]}
                         for a in manifest["artifacts"]],
        "source_probability_precision_decimals": 6,
        "technical_control_fields": list(SCIENTIFIC_FIELDS),
        "confirmatory_independence": False})
    print(json.dumps({"stage": "preflight", "fold": args.fold, "cardinality": planned}), flush=True)
    legacy.inference.clear_artifact_cache()
    weather = legacy.PointWeatherReader(str(ROOT / "docker-data/Data"), str(ROOT / "docker-data/stations.txt"))
    counters = {name: Counter() for name in ("control", *METHODS)}
    decision_counts = {name: Counter() for name in METHODS}
    weather_preparations = 0
    prepare = weather.prepare_model_inputs
    def counted_prepare(*positional, **keywords):
        nonlocal weather_preparations
        weather_preparations += 1
        return prepare(*positional, **keywords)
    weather.prepare_model_inputs = counted_prepare
    checked_rows = {name: [] for name in METHODS}
    control_count = 0
    input_comparisons = Counter()
    requirement_counts = {name: Counter() for name in ("control", *METHODS)}
    reused_requirement_counts = {name: Counter() for name in ("control", *METHODS)}
    execution_modes = Counter()
    try:
        with legacy.frozen_weather():
            weather._refresh()
            weather_identity = weather._identity
            with (stage / "predictions.jsonl").open("x") as predictions, (stage / "control-comparisons.jsonl").open("x") as control_log, (stage / "input-contract-comparisons.jsonl").open("x") as input_log:
                for index, observed in enumerate(cases):
                    # The legacy evaluator enforces its original eight-entry LRU
                    # and exact preparation key; no feature/prediction cache is shared.
                    weather_cache = OrderedDict()
                    no_label = {k: observed[k] for k in ("observation_id", "species_id", "date")}
                    for horizon in range(1, 8):
                        issue = date.fromisoformat(observed["date"]) - timedelta(days=horizon - 1)
                        identity = {"observation_id": observed["observation_id"], "species_id": observed["species_id"],
                            "episode_id": observed["episode_id"], "target_date": observed["date"], "issue_date": issue.isoformat(),
                            "horizon": horizon, "fold": args.fold, "phase": "external", "y": observed["y"]}
                        results = {}
                        raw_results = {}
                        method_contracts = {}
                        for method in ("control", *METHODS):
                            parameters = dict(row=no_label, location=observations[observed["observation_id"]]["location"],
                                geography=geography[observed["observation_id"]], issue=issue, horizon=horizon,
                                registry=registry, manifest=manifest, quality_catalog=catalogs[method], models_root=models_root,
                                resolutions=indexed[method].get(observed["species_id"]), profiles=profiles,
                                ecology_reader=ecology, weather=weather, weather_cache=weather_cache, installed_versions=versions)
                            materializations = []
                            plan = c_plans[observed["species_id"]]
                            reuse_b = method == "C" and plan["mode"] == DAILY_REUSE
                            if reuse_b:
                                result, materializations = reuse_native_daily_result(
                                    raw_results["B"], method_contracts["B"], plan)
                            else:
                                with materialization_contracts(materializations):
                                    if method == "C":
                                        with daily_resolver():
                                            result = legacy.evaluate_case(**parameters)
                                    else:
                                        result = legacy.evaluate_case(**parameters)
                            raw_results[method] = result
                            method_contracts[method] = materializations
                            for materialization in materializations:
                                ref = materialization["model_ref"]
                                family = {key: ref.get(key) for key in legacy.recommendations.FAMILY}
                                key = json.dumps({"family": family,
                                    "weather_lookback_days": materialization["weather_lookback_days"],
                                    "include_physical_state": materialization["include_physical_state"]}, sort_keys=True)
                                requirement_counts[method][key] += 1
                                reused_requirement_counts[method][key] += reuse_b
                            if weather._identity != weather_identity:
                                raise ValueError("Weather changed during point evaluation")
                            counters[method]["scored_emissions"] += 1
                            counters[method]["evaluator_calls"] += not reuse_b
                            counters[method]["reused_scored_emissions"] += reuse_b
                            counters[method]["trace_members"] += len(result.get("trace", []))
                            counters[method]["materialized_members"] += 0 if reuse_b else len(result.get("trace", []))
                            counters[method]["reused_materialized_members"] += len(result.get("trace", [])) if reuse_b else 0
                            counters[method]["materialized_available_members"] += 0 if reuse_b else sum(
                                m.get("available") is True for m in result.get("trace", []))
                            if method == "control":
                                check = compare_control(result, controls[(observed["observation_id"], horizon)])
                                _write_line(control_log, {"observation_id": observed["observation_id"], "horizon": horizon, **check})
                                if check["status"] != "passed":
                                    raise ValueError("Technical control differs in: " + ",".join(check["different_fields"]))
                                control_count += 1
                            else:
                                compact = {**result, "decision": result["decision_a"]}
                                compact.pop("decision_a")
                                compact["input_contracts"] = materializations
                                if method == "C":
                                    execution_modes[plan["mode"]] += 1
                                    compact.update(execution_mode=plan["mode"], execution_plan_sha256=plan["sha256"],
                                        reused_from="B" if reuse_b else None,
                                        reused_scientific_payload_sha256=json_hash(scientific_payload(raw_results["B"])) if reuse_b else None)
                                results[method] = compact
                                decision_counts[method][compact["decision"]] += 1
                                checked_rows[method].append({**identity, "decision_a": compact["decision"], "probability": compact["probability"]})
                        input_check = compare_input_contracts(method_contracts["B"], method_contracts["C"])
                        _write_line(input_log, {"observation_id": observed["observation_id"], "horizon": horizon, **input_check})
                        if input_check["status"] != "passed":
                            raise ValueError("B/C input contracts differ; selector-only attribution is invalid")
                        for key in ("shared_materializations", "only_B_materializations", "only_C_materializations"):
                            input_comparisons[key] += input_check[key]
                        _write_line(predictions, {**identity, **results})
                    print(json.dumps({"fold": args.fold, "observations_completed": index + 1,
                        "observations_planned": len(cases), "controls_passed": control_count,
                        "weather_preparations": weather_preparations}), flush=True)
        if control_count != len(cases) * 7:
            raise ValueError("Incomplete technical control")
        for method in METHODS:
            validate_rows(checked_rows[method])
        common.verify_inputs(cohort)
        if any(common.digest(ROOT / record["path"]) != record["sha256"] for record in sealed):
            raise ValueError("Source/protocol/evidence changed during evaluation")
        for artifact in manifest["artifacts"]:
            if common.digest(models_root / artifact["path"]) != artifact["sha256"]:
                raise ValueError("External artifact changed during evaluation")
        common.write_new(stage / "evaluation-summary.json", {
            "schema": 1, "status": "completed", "fold": args.fold, "phase": "external", "snapshot_id": snapshot,
            "observations": len(cases), "predictions": len(cases) * 7,
            "predictions_sha256": common.digest(stage / "predictions.jsonl"),
            "control_comparisons_sha256": common.digest(stage / "control-comparisons.jsonl"),
            "input_contract_comparisons_sha256": common.digest(stage / "input-contract-comparisons.jsonl"),
            "B_C_input_parity": {"status": "passed", "mismatched_materializations": 0, **dict(input_comparisons)},
            "technical_control": {"status": "passed", "emissions": control_count,
                                  "scientific_fields": list(SCIENTIFIC_FIELDS)},
            "cardinality": planned, "actual_counts": {key: dict(value) for key, value in counters.items()},
            "decision_counts": {key: dict(value) for key, value in decision_counts.items()},
            "weather_preparations": weather_preparations, "inputs_verified_after": True,
            "C_execution_modes": dict(execution_modes), "C_execution_plans": c_plans,
            "requirement_counts": {method: [{**json.loads(key),
                                            "materializations": count - reused_requirement_counts[method][key],
                                            "reused_materializations": reused_requirement_counts[method][key]}
                                           for key, count in sorted(values.items())]
                                   for method, values in requirement_counts.items()},
            "quality_sha256": {**{key: common.digest(path) for key, path in quality_paths.items()},
                               "C": common.digest(quality_paths["B"])},
            "model_manifest_sha256": common.digest(manifest_path)})
    finally:
        legacy.inference.clear_artifact_cache()


if __name__ == "__main__":
    main()
