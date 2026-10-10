"""New paired point contrast on one current weather snapshot; old runs immutable."""
from __future__ import annotations
import argparse
from collections import Counter, OrderedDict
from datetime import date, timedelta
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.prediction_model_selection_d import study
from scripts.prediction_model_selection_d.common import ROOT, OUTPUT, OLD_OUTPUT, TARGETS, load, digest, write_new, protect_originals
from scripts.prediction_model_selection import evaluate

DESTINATION=OUTPUT/"common-weather"
ANNEX=ROOT/"docs/agents/prediction-model-selection/protocolo-D-meteorologia-comun-2026-10-05.md"
METHODS=("A","B","C","D")
ROUTE_ANNEX=ROOT/"docs/agents/prediction-model-selection/protocolo-D-ruta-nativa-2026-10-05.md"


def freeze():
    inv=study.checked_inputs()
    pointer_path=ROOT/"docker-data/Data/weather-history/CURRENT.json"
    pointer=load(pointer_path)
    manifest_path=pointer_path.parent/pointer["manifest_path"]
    if digest(manifest_path)!=pointer["manifest_sha256"]:
        raise ValueError("Current weather manifest checksum mismatch")
    weather=load(manifest_path)
    catalog_path=pointer_path.parent/weather["catalog"]["path"]
    if digest(catalog_path)!=weather["catalog"]["sha256"]:
        raise ValueError("Current weather station catalog checksum mismatch")
    files=[pointer_path,manifest_path,catalog_path,ANNEX]
    for year in (2024,2025,2026):
        files.extend([study.PREVIOUS/f"fold-{year}/quality-{m}.json" for m in ("A","B")])
        files.append(OUTPUT/f"fold-{year}/quality-D.json")
    # The existing read-only resolver verifies every immutable weather partition.
    with evaluate.legacy.frozen_weather(): pass
    write_new(DESTINATION/"seal.json",{"status":"sealed","inputs":{str(p.relative_to(ROOT)):digest(p) for p in files},
        "weather_generation":pointer["generation_id"],"original_weather_unavailable":inv["raw_weather_changes"],
        "methods":METHODS,"observations":116,"emissions_per_method":812,"estimated_max_additional_seconds":1500})
    print(json.dumps({"stage":"common_weather_sealed","generation":pointer["generation_id"],"emissions_per_method":812}),flush=True)


def check():
    study.checked_inputs()
    seal=load(DESTINATION/"seal.json")
    for path,sha in seal["inputs"].items():
        if digest(ROOT/path)!=sha:raise ValueError("Common weather input changed: "+path)
    return seal


def route_check(check, b_plan, d_plan):
    if check["status"] == "passed":
        return check
    if b_plan["mode"] == evaluate.DAILY_REUSE and d_plan["mode"] == evaluate.DAILY_INDEPENDENT and len(d_plan["catalog_states"]) == 7 and all(x["weekly_status"] == "weekly" for x in d_plan["catalog_states"]):
        return {**check, "status": "native_route_effect", "interpretation": "total_procedure_effect_not_fixed_candidate_inputs", "B_plan_sha256": b_plan["sha256"], "D_plan_sha256": d_plan["sha256"]}
    return check


def run(year, attempt=None):
    seal=check();cohort=load(study.COHORT);legacy=evaluate.legacy
    stage=DESTINATION/(f"fold-{year}"+(f"-{attempt}" if attempt else ""));stage.mkdir(exist_ok=False)
    old_stage=OLD_OUTPUT/f"fold-{year}/external"
    registry_path=ROOT/"docker-data/mushroom-data/mushroom_ml_version_registry.json"
    registry=legacy.policy_store.resolve(registry_path,load(registry_path))
    if legacy.recommendations.settings(registry)["mode"]!="shadow":raise ValueError("Policy changed")
    manifest=legacy.catalog.validate_batch_manifest(registry,load(old_stage/"manifest.json"))
    paths={m:study.PREVIOUS/f"fold-{year}/quality-{m}.json" for m in ("A","B")}
    paths["D"]=OUTPUT/f"fold-{year}/quality-D.json"
    catalogs={m:legacy.quality.validate_catalog(load(p),require_selections=True) for m,p in paths.items()};catalogs["C"]=catalogs["B"]
    indexed={m:evaluate.index_resolutions(q) for m,q in catalogs.items()}
    versions=list(dict.fromkeys(p["version_id"] for p in cohort["profiles"]))
    cases=[r for r in cohort["rows"] if r["species_id"] in TARGETS and cohort["folds"][str(year)][r["observation_id"]]=="external"]
    planned=evaluate.cardinality(cases,indexed)
    plans={sid:evaluate.daily_execution_plan(indexed["B"].get(sid),species_id=sid,installed_version_ids=versions,quality_sha256=digest(paths["B"])) for sid in TARGETS}
    d_plans={sid:evaluate.daily_execution_plan(indexed["D"].get(sid),species_id=sid,installed_version_ids=versions,quality_sha256=digest(paths["D"])) for sid in TARGETS}
    route_annex_sha=digest(ROUTE_ANNEX)
    write_new(stage/"seal.json",{"fold":year,"cardinality":planned,"C_plans":plans,"D_plans":d_plans,"route_annex_sha256":route_annex_sha,"common_weather_seal_sha256":digest(DESTINATION/"seal.json")})
    base=ROOT/"docker-data/mushroom-data"
    profiles={p["species_id"]:p for p in load(base/"mushroom_profiles.json")["species_profiles"]}
    ecology=legacy.EcologyReader(str(base/"mushroom_profiles.json"),str(base/"mushroom_reference_catalogs.json"),str(base/"mushroom_gis_mappings.json"),ph_source=cohort["geography_config"].get("ecology_ph_source","soilgrids"))
    geography={r["id"]:r for r in study.ranking.read_rows(OLD_OUTPUT/"geography.jsonl") if r["id"]!="capabilities"}
    observations={r["observation_id"]:r for r in load(ROOT/cohort["observations_input"])["observations"]}
    previous={(r["observation_id"],r["horizon"]):r for r in study.ranking.read_rows(study.PREVIOUS/f"fold-{year}/evaluation/predictions.jsonl")}
    weather=legacy.PointWeatherReader(str(ROOT/"docker-data/Data"),str(ROOT/"docker-data/stations.txt"))
    legacy.inference.clear_artifact_cache();counts={m:Counter() for m in METHODS};drift={m:Counter() for m in ("A","B","C")};route_effect=Counter()
    with legacy.frozen_weather():
        weather._refresh();weather_identity=weather._identity
        with (stage/"predictions.jsonl").open("x") as stream:
            for index,observed in enumerate(cases):
                cache=OrderedDict()
                for horizon in range(1,8):
                    issue=date.fromisoformat(observed["date"])-timedelta(days=horizon-1)
                    results={};raw={};contracts={}
                    for method in METHODS:
                        parameters=dict(row={k:observed[k] for k in ("observation_id","species_id","date")},location=observations[observed["observation_id"]]["location"],geography=geography[observed["observation_id"]],issue=issue,horizon=horizon,registry=registry,manifest=manifest,quality_catalog=catalogs[method],models_root=old_stage/"models",resolutions=indexed[method].get(observed["species_id"]),profiles=profiles,ecology_reader=ecology,weather=weather,weather_cache=cache,installed_versions=versions)
                        materializations=[];plan=plans[observed["species_id"]]
                        if method=="C" and plan["mode"]==evaluate.DAILY_REUSE:
                            result,materializations=evaluate.reuse_native_daily_result(raw["B"],contracts["B"],plan)
                        else:
                            with evaluate.materialization_contracts(materializations):
                                if method=="C":
                                    with evaluate.daily_resolver():result=legacy.evaluate_case(**parameters)
                                else:result=legacy.evaluate_case(**parameters)
                        raw[method]=result;contracts[method]=materializations
                        compact={**result,"decision":result["decision_a"],"input_contracts":materializations};compact.pop("decision_a")
                        results[method]=compact;counts[method][compact["decision"]]+=1
                        if method in drift:
                            old=previous[(observed["observation_id"],horizon)][method]
                            drift[method]["different_decision"]+=old["decision"]!=compact["decision"]
                            drift[method]["different_probability"]+=old["probability"]!=compact["probability"]
                        if compact["decision"]=="favorable" and (compact["probability"] is None or compact["probability"]<.6):raise ValueError("Threshold changed")
                    checks={m:evaluate.compare_input_contracts(contracts["B"],contracts[m]) for m in ("C","D")}
                    checks["D"]=route_check(checks["D"],plans[observed["species_id"]],d_plans[observed["species_id"]])
                    if checks["D"]["status"]=="native_route_effect":
                        route_effect["emissions"]+=1;route_effect["shared_requests_affected"]+=checks["D"]["mismatched_materializations"]
                    if checks["C"]["status"]!="passed" or checks["D"]["status"] not in {"passed","native_route_effect"}:
                        write_new(stage/"contract-failure.json",{"fold":year,"horizon":horizon,"observation_id":observed["observation_id"],"checks":checks,"contracts":contracts})
                        raise ValueError("Common weather B/C or B/D input contract mismatch")
                    if weather._identity!=weather_identity:raise ValueError("Weather changed during contrast")
                    identity={"observation_id":observed["observation_id"],"species_id":observed["species_id"],"episode_id":observed["episode_id"],"target_date":observed["date"],"issue_date":issue.isoformat(),"horizon":horizon,"fold":year,"phase":"external","y":observed["y"]}
                    evaluate._write_line(stream,{**identity,**results,"input_parity":checks})
                print(json.dumps({"fold":year,"completed_observations":index+1,"planned_observations":len(cases)}),flush=True)
    legacy.inference.clear_artifact_cache();check()
    if digest(ROUTE_ANNEX)!=route_annex_sha:raise ValueError("Route-effect protocol changed")
    write_new(stage/"summary.json",{"status":"completed","fold":year,"observations":len(cases),"emissions_per_method":len(cases)*7,"counts":{m:dict(v) for m,v in counts.items()},"drift_from_saved":{m:dict(v) for m,v in drift.items()},"D_native_route_effect":dict(route_effect),"predictions_sha256":digest(stage/"predictions.jsonl"),"cardinality":planned})


def main():
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("freeze","evaluate"));p.add_argument("--year",type=int,choices=(2024,2025,2026));p.add_argument("--attempt",choices=("retry",));args=p.parse_args()
    if os.environ.get("RAINMAPPER_D_GUARDED")!="1":raise SystemExit("Launch through D bounded.py")
    protect_originals()
    freeze() if args.stage=="freeze" else run(args.year,args.attempt)


if __name__=="__main__":main()
