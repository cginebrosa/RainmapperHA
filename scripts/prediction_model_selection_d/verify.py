"""Close the D study by checking persisted evidence, not rerunning predictions."""
from __future__ import annotations
from collections import Counter
from datetime import date, timedelta
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.prediction_model_selection_d import study, common_weather
from scripts.prediction_model_selection_d.common import ROOT, OUTPUT, load, digest, write_new, protect_originals
from scripts.prediction_model_selection import analyze as old_analysis


def main():
    if os.environ.get("RAINMAPPER_D_GUARDED")!="1":raise SystemExit("Launch through D bounded.py")
    protect_originals(); inv=study.checked_inputs();common_weather.check()
    cohort=load(study.COHORT);by_id={r["observation_id"]:r for r in cohort["rows"]}
    events=study.ranking.read_rows(study.HISTORICAL/"fit-events.jsonl")
    valid=[e for e in events if e["available"]]
    for e in valid:
        train=[by_id[i] for i in e["train_ids"]];test=[by_id[i] for i in e["test_ids"]]
        if {r["episode_id"] for r in train}&{r["episode_id"] for r in test}:raise ValueError("Persisted episode leakage")
        if max(r["date"] for r in train)>=f"{e['year']}-01-01":raise ValueError("Persisted future training")
        if any(int(r["date"][:4])!=e["year"] for r in test):raise ValueError("Persisted test window differs")
        if len({r["y"] for r in train})!=2:raise ValueError("A fitted scope lacked both classes")
        if len(train)!=e["train_observations"]:raise ValueError("Persisted training support mismatch")
    historical=[r for f in ("v2-v5","v6") for r in study.ranking.read_rows(study.HISTORICAL/f"ranking-{f}.jsonl")]
    if len({r["row_key"] for r in historical})!=len(historical):raise ValueError("Historical duplicate row")
    for r in historical:
        original=by_id[r["observation_id"]]
        if (r["y_true"],r["validation_group_id"],r["species_id"],r["target_date"])!=(original["y"],original["episode_id"],original["species_id"],original["date"]):raise ValueError("Historical identity/label changed")
        if r["cutoff_date"]!=(date.fromisoformat(r["target_date"])-timedelta(days=r["horizon_days"])).isoformat():raise ValueError("Historical cutoff changed")
        if any(not 0<=p<=1 for p in r["estimator_probabilities"].values()):raise ValueError("Invalid historical probability")
    rows=[];route_effects=Counter();prediction_files={}
    for y in (2024,2025,2026):
        stage=common_weather.DESTINATION/(f"fold-{y}"+("-retry" if y==2025 else ""))
        summary=load(stage/"summary.json");path=stage/"predictions.jsonl"
        if summary["status"]!="completed" or digest(path)!=summary["predictions_sha256"]:raise ValueError("Point stage incomplete or changed")
        block=study.ranking.read_rows(path);rows.extend(block);prediction_files[str(path.relative_to(ROOT))]=digest(path)
        for r in block:
            result=r["D"]
            if result["decision"] not in old_analysis.DECISIONS:raise ValueError("Invalid D verdict")
            if result["decision"]!="abstain" and (result["probability"] is None or not result["winner"]):raise ValueError("D recommendation has no predictor")
            if result["decision"]=="favorable" and result["probability"]<.6:raise ValueError("D threshold changed")
            if r["input_parity"]["C"]["status"]!="passed":raise ValueError("B/C parity failed")
            state=r["input_parity"]["D"]["status"]
            if state=="native_route_effect":
                if r["species_id"]!="boletus_aereus" or y not in (2025,2026):raise ValueError("Unexpected route effect")
                route_effects[str(y)]+=1
            elif state!="passed":raise ValueError("Unexplained B/D parity failure")
    old_analysis.validate_rows(rows,cohort,require_design=True)
    analysis=load(OUTPUT/"analysis-common/results.json")
    for sid in study.TARGETS:
        selected=[r for r in rows if r["species_id"]==sid];p=len({r["observation_id"] for r in selected if r["y"]})
        for m in ("A","B","C","D"):
            tp=sum(r["y"]==1 and r[m]["decision"]=="favorable" for r in selected)/7
            fp=sum(r["y"]==0 and r[m]["decision"]=="favorable" for r in selected)/7
            saved=analysis["species"][sid]["pooled"]["methods"][m]
            if abs(saved["TP"]-tp)>1e-9 or abs(saved["FP"]-fp)>1e-9 or abs(saved["I4"]-100*(tp-4*fp)/p)>1e-9:raise ValueError("Persisted metric arithmetic differs")
    archived=0
    for p in (OUTPUT/"runs").glob("*.sources.json"):
        for source in load(p)["files"]:
            archived_path=OUTPUT/"source-archive"/(source["sha256"]+Path(source["path"]).suffix)
            if digest(archived_path)!=source["sha256"]:raise ValueError("Executed source bytes missing")
            archived+=1
    historical_receipt=load(OUTPUT/"historical-phase-receipt.json")
    if digest(OUTPUT/"historical-phase-report.md")!=historical_receipt["files"]["docs/agents/prediction-model-selection/resultados-D-2026-10-05.md"]:raise ValueError("Historical phase report snapshot changed")
    study.checked_inputs();common_weather.check()
    write_new(OUTPUT/"verification.json",{"status":"passed","sealed_inputs_checked":len(inv["inputs"]),"historical_successful_fits_checked":len(valid),"historical_rows_checked":len(historical),"external_observations":116,"external_rows_per_method":len(rows),"methods":4,"native_route_emissions":dict(route_effects),"archived_source_references_checked":archived,"prediction_files":prediction_files,"analysis_sha256":digest(OUTPUT/"analysis-common/results.json"),"historical_report_snapshot_verified":True})
    print(json.dumps({"status":"passed","sealed_inputs":len(inv["inputs"]),"historical_fits":len(valid),"external_emissions_per_method":len(rows),"source_references":archived}),flush=True)


if __name__=="__main__":main()
