"""I4 analysis of saved methods, and D only when the point stage is valid."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.prediction_model_selection_d import study
from scripts.prediction_model_selection_d.common import OUTPUT, TARGETS, load, write_new, protect_originals, digest
import numpy as np

DECISIONS = ("favorable", "unfavorable", "abstain")


def values(cells):
    tp, fn, pa, fp, tn, na = np.moveaxis(np.asarray(cells, dtype=float), -1, 0)
    p, n = tp+fn+pa, tp+fn+pa+fp+tn+na
    def divide(a, b):
        return np.divide(a, b, out=np.full_like(a, np.nan), where=b>0)
    return {"TP": tp, "FP": fp, "recommendations": tp+fp, "precision": divide(tp,tp+fp),
            "detection": divide(tp,p), "favorable_frequency": divide(tp+fp,n), "I4": 100*divide(tp-4*fp,p)}


def finite(x):
    return float(x) if np.isfinite(x) else None


def summarize(rows, methods, horizon=None):
    groups = {}
    for r in rows:
        if horizon is not None and r["horizon"] != horizon:
            continue
        tensor = groups.setdefault((r["fold"],r["episode_id"]), np.zeros((len(methods),6)))
        for i,m in enumerate(methods):
            tensor[i,(0 if r["y"] else 3)+DECISIONS.index(r[m]["decision"])] += 1 if horizon else 1/7
    keys=sorted(groups); tensor=np.array([groups[k] for k in keys]); total=tensor.sum(axis=0)
    result={"n":len({r["observation_id"] for r in rows}),"positive":len({r["observation_id"] for r in rows if r["y"]}),"negative":len({r["observation_id"] for r in rows if not r["y"]}),"episodes":len(keys),"methods":{}}
    rng=np.random.default_rng(20261005); draws=np.zeros((2000,len(methods),6))
    for fold in sorted({k[0] for k in keys}):
        indices=[i for i,k in enumerate(keys) if k[0]==fold]
        draws+=tensor[rng.choice(indices,size=(2000,len(indices)),replace=True)].sum(axis=1)
    bootstrap={m:values(draws[:,i]) for i,m in enumerate(methods)}
    for i,m in enumerate(methods):
        val={k:finite(v) for k,v in values(total[i]).items()}
        episodes=int(np.count_nonzero(tensor[:,i,0]+tensor[:,i,3]))
        ci={}
        for k,v in bootstrap[m].items():
            valid=v[np.isfinite(v)]
            ci[k]={"lower":finite(np.quantile(valid,.025)) if len(valid) else None,"upper":finite(np.quantile(valid,.975)) if len(valid) else None,"valid_replicates":len(valid)}
        val.update(recommended_episodes=episodes,bootstrap_95=ci)
        val["practically_useful"]=(val["I4"] is not None and val["I4"]>=5-1e-9 and val["recommendations"]>=10-1e-9 and val["detection"]>=.25-1e-9 and episodes>=5)
        val["minimum_evidence"]=(result["positive"]>=10 and result["negative"]>=10 and result["episodes"]>=10 and episodes>=5)
        result["methods"][m]=val
    if "D" in methods:
        result["D_contrasts"]={}
        for comp in ("B","A","C"):
            vals=bootstrap["D"]["I4"]-bootstrap[comp]["I4"];valid=vals[np.isfinite(vals)]
            result["D_contrasts"][comp]={"delta_I4":result["methods"]["D"]["I4"]-result["methods"][comp]["I4"],"lower":finite(np.quantile(valid,.025)),"upper":finite(np.quantile(valid,.975)),"valid_replicates":len(valid)}
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--common",action="store_true");args=parser.parse_args()
    if os.environ.get("RAINMAPPER_D_GUARDED")!="1":
        raise SystemExit("Launch through D bounded.py")
    protect_originals(); inv=study.checked_inputs()
    rows=[]; methods=["A","B","C"]
    complete=all((OUTPUT/f"fold-{y}/evaluation/summary.json").is_file() for y in (2024,2025,2026))
    if args.common:
        from scripts.prediction_model_selection_d import common_weather
        common_weather.check()
        def common_stage(year):
            return common_weather.DESTINATION/(f"fold-{year}"+("-retry" if year==2025 else ""))
        complete=all((common_stage(y)/"summary.json").is_file() for y in (2024,2025,2026))
        if not complete:raise ValueError("Common weather contrast is incomplete")
    if complete: methods.append("D")
    for y in (2024,2025,2026):
        previous=study.ranking.read_rows((common_stage(y)/"predictions.jsonl") if args.common else (study.PREVIOUS/f"fold-{y}/evaluation/predictions.jsonl"))
        d={(r["observation_id"],r["horizon"]):r for r in (previous if args.common else study.ranking.read_rows(OUTPUT/f"fold-{y}/evaluation/predictions.jsonl"))} if complete else {}
        for r in previous:
            if complete:
                fresh=d[(r["observation_id"],r["horizon"])]
                for k in ("fold","episode_id","y","target_date","species_id"):
                    if r[k]!=fresh[k]:raise ValueError("D external identity mismatch")
                r["D"]=fresh["D"]
            rows.append(r)
    if len(rows)!=812: raise ValueError("Incomplete external cohort")
    from scripts.prediction_model_selection import analyze as original_analysis
    original_analysis.validate_rows(rows,load(study.COHORT),require_design=True)
    result={"status":"completed" if complete else "D_point_comparison_unavailable","methods":methods,"species":{},"D_not_estimated_reason":None if complete else inv["raw_weather_changes"]}
    cohort=load(study.COHORT)
    historical=[r for f in ("v2-v5","v6") for r in study.ranking.read_rows(study.HISTORICAL/f"ranking-{f}.jsonl")]
    missing=load(study.HISTORICAL/"missing.json")
    events=study.ranking.read_rows(study.HISTORICAL/"fit-events.jsonl")
    support={}
    for sid in TARGETS:
        support[sid]={}
        for y in study.YEARS:
            original={r["observation_id"] for r in cohort["rows"] if r["species_id"]==sid and int(r["date"][:4])==y}
            scored={r["observation_id"] for r in historical if r["species_id"]==sid and int(r["target_date"][:4])==y and r["estimator_probabilities"]}
            unscored=original-scored
            reasons=Counter(m["reason"] for m in missing if m["observation_id"] in unscored)
            support[sid][str(y)]={"original_observations":len(original),"observations_with_any_prediction":len(scored),"observations_without_any_prediction":len(unscored),"no_prediction_reasons_by_profile_horizon":dict(reasons),"observations_with_every_profile_estimator":sum(sum(r["observation_id"]==obs for r in historical)==88 and all(len(r["estimator_probabilities"])==len(next(p["estimator_ids"] for p in cohort["profiles"] if p["version_id"]==r["version_id"] and p["profile_id"]==r["profile_id"])) for r in historical if r["observation_id"]==obs) for obs in scored)}
    result["historical_support"]=support
    result["historical_fit_events"]={"total":len(events),"successful":sum(e["available"] for e in events),"unavailable_reasons":dict(Counter(e["reason"] for e in events if not e["available"]))}
    result["D_ranking_diagnostics"]={}
    for y in (2024,2025,2026):
        q=load(OUTPUT/f"fold-{y}/quality-D.json")
        result["D_ranking_diagnostics"][str(y)]={"provenance":load(OUTPUT/f"fold-{y}/ranking-provenance.json"),"species":{}}
        for sid in TARGETS:
            resolutions=[r for r in q["species_selections"] if r["species_id"]==sid]
            result["D_ranking_diagnostics"][str(y)]["species"][sid]={"days":[{"day":r["prediction_day"],"status":r["selection_status"],"family":r.get("candidate"),"stability":{k:(r.get("stability") or {}).get(k) for k in ("method","omission_count","same_winner_count","same_winner_rate")},"support":{k:(r.get("evidence") or {}).get(k) for k in ("observation_count","validation_group_count","positive_observation_count","negative_observation_count")}} for r in resolutions],"candidate_support_distribution":dict(Counter(str(e["n_test"]) for e in q["entries"] if e["species_id"]==sid))}
    for sid in TARGETS:
        subset=[r for r in rows if r["species_id"]==sid]
        strata={"pooled":summarize(subset,methods)}
        for y in (2024,2025,2026):strata[str(y)]=summarize([r for r in subset if r["fold"]==y],methods)
        strata["horizons"]={str(h):summarize(subset,methods,h) for h in range(1,8)}
        for m in methods:
            campaigns=[strata[str(y)] for y in (2024,2025,2026)]
            strata["pooled"]["methods"][m]["stable_between_campaigns"]=(sum(c["methods"][m]["I4"] is not None and c["methods"][m]["I4"]>0 for c in campaigns)>=2 and all(c["positive"]<5 or (c["methods"][m]["recommendations"]>=1-1e-9 and c["methods"][m]["detection"]>=.1-1e-9) for c in campaigns))
        result["species"][sid]=strata
    if args.common:
        result["weather_snapshot"]=load(common_weather.DESTINATION/"seal.json")
        result["drift_from_saved"]={str(y):load(common_stage(y)/"summary.json")["drift_from_saved"] for y in (2024,2025,2026)}
        result["D_native_route_effect"]={str(y):load(common_stage(y)/"summary.json").get("D_native_route_effect",{}) for y in (2024,2025,2026)}
        result["comparison_scope"]="new_common_weather_A_B_C_D_not_mixed_with_saved_outcomes"
    write_new(OUTPUT/("analysis-common/results.json" if args.common else "analysis/results.json"),result)
    print(json.dumps({"status":result["status"],"species":{sid:{m:{k:v for k,v in data["pooled"]["methods"][m].items() if k!="bootstrap_95"} for m in methods} for sid,data in result["species"].items()}}),flush=True)


if __name__=="__main__":main()
