"""Aggregate sealed external predictions; never select a threshold here."""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path

import numpy as np
from scipy.stats import beta

from common import ROOT, OUTPUT, TARGETS, digest, load, write_new, verify_inputs, protect_originals
from recommendation_metrics import decision, validate_rows, GRID

FOLDS = (2024, 2025, 2026)
CELLS = tuple(f"{y}_{d}" for y in ("positive", "negative") for d in ("favorable", "unfavorable", "abstain"))
METRICS = ("false_favorable", "true_favorable", "false_unfavorable", "positive_abstain",
           "missed_positive", "recommendations", "precision", "false_discovery_rate",
           "false_positive_rate", "recall", "miss_rate", "coverage", "favorable_coverage")
REPLICATES, SEED = 2000, 20261003


def rates(cells):
    tp, fn, pa, fp, tn, na = np.moveaxis(np.asarray(cells, dtype=float), -1, 0)
    positive, negative = tp+fn+pa, fp+tn+na
    total = positive+negative
    def divide(a, b):
        return np.divide(a, b, out=np.full_like(a, np.nan, dtype=float), where=b > 0)
    return dict(zip(METRICS, (fp, tp, fn, pa, fn+pa, tp+fp,
        divide(tp, tp+fp), divide(fp, tp+fp), divide(fp, negative), divide(tp, positive),
        divide(fn+pa, positive), divide(tp+fp+fn+tn, total), divide(tp+fp, total))))


def finite(value):
    value = float(value)
    return value if np.isfinite(value) else None


def episode_tensor(rows, choices, *, horizon=None):
    """One cluster per episode and fold; seven emissions total one observation."""
    groups = {}
    for row in rows:
        if horizon is not None and row["horizon"] != horizon:
            continue
        key = (row["fold"], row["episode_id"])
        counts = groups.setdefault(key, np.zeros((2, 6), dtype=float))
        for method, threshold in enumerate((.60, choices[row["fold"]])):
            cell = ("positive" if row["y"] else "negative") + "_" + decision(row, threshold)
            counts[method, CELLS.index(cell)] += 1/7 if horizon is None else 1
    keys = sorted(groups)
    if not keys:
        raise ValueError("No cases in an external analysis stratum")
    return keys, np.asarray([groups[key] for key in keys])


def bootstrap(keys, tensor, *, replicates=REPLICATES, seed=SEED):
    rng = np.random.default_rng(seed)
    draws = np.zeros((replicates, 2, 6))
    for fold in sorted({k[0] for k in keys}):
        indices = [i for i, k in enumerate(keys) if k[0] == fold]
        # Sampling multiplicity is shared by A/B and by every horizon in a cluster.
        selected = rng.choice(indices, size=(replicates, len(indices)), replace=True)
        draws += tensor[selected].sum(axis=1)
    by_method = [rates(draws[:, method]) for method in (0, 1)]
    outputs = {}
    for label, values in (("A", by_method[0]), ("B", by_method[1]),
                          ("B_minus_A", {k: by_method[1][k]-by_method[0][k] for k in METRICS})):
        outputs[label] = {}
        for key, values_ in values.items():
            valid = np.asarray(values_)[np.isfinite(values_)]
            outputs[label][key] = {"lower": finite(np.quantile(valid, .025)) if len(valid) else None,
                                  "upper": finite(np.quantile(valid, .975)) if len(valid) else None,
                                  "finite_replicates": len(valid)}
    return outputs


def grouped_error_bound(keys, tensor):
    """Exploratory per-recommended-episode event rate, NOT forecast-level precision."""
    result = {}
    for index, method in enumerate(("A", "B")):
        recommended = tensor[:, index, 0] + tensor[:, index, 3] > 0
        n = int(recommended.sum())
        errors = int((tensor[:, index, 3] > 0).sum())
        upper = None if n == 0 else 1.0 if errors == n else float(beta.ppf(.95, errors+1, n-errors))
        result[method] = {"recommended_groups": n, "groups_with_any_false_favorable": errors,
                          "one_sided_95_upper_event_rate": upper,
                          "unit": "any false favorable in a recommended episode",
                          "independent_groups_not_established": True}
    return result


def describe(rows, choices, *, horizon=None):
    keys, tensor = episode_tensor(rows, choices, horizon=horizon)
    sums = tensor.sum(axis=0)
    if not np.isclose(sums[0].sum(), sums[1].sum()):
        raise AssertionError("A/B denominators differ")
    if sums[1, 0] > sums[0, 0]+1e-9 or sums[1, 3] > sums[0, 3]+1e-9:
        raise AssertionError("A conservative threshold created a favorable")
    result = {"horizon": horizon or "average_1_to_7", "observations": len({r["observation_id"] for r in rows}),
              "groups": len(keys), "positive_observations": len({r["observation_id"] for r in rows if r["y"]}),
              "negative_observations": len({r["observation_id"] for r in rows if not r["y"]})}
    for method, totals in zip(("A", "B"), sums):
        result[method] = {"matrix": dict(zip(CELLS, map(float, totals))),
                          "metrics": {key: finite(value) for key, value in rates(totals).items()}}
    result["B_minus_A"] = {key: finite(result["B"]["metrics"][key]-result["A"]["metrics"][key])
        if result["B"]["metrics"][key] is not None and result["A"]["metrics"][key] is not None else None for key in METRICS}
    result["bootstrap_95_percentile"] = bootstrap(keys, tensor)
    result["exploratory_group_bound"] = grouped_error_bound(keys, tensor)
    return result


def family(winner):
    return "/".join(str(winner[k]) for k in ("version_id", "profile_id", "temporal_contract_id", "estimator_id"))


def diagnostics(rows, choices):
    reasons, winners, final, gates, geo_reasons = (Counter() for _ in range(5))
    by_fold = {}
    for row in rows:
        reasons[row["reason"]] += 1
        if row["reason"] == "territory_or_season_gate":
            geo_reasons.update(row.get("geography_reasons", []))
        if row.get("winner"):
            winners[family(row["winner"])] += 1
            if row["decision_a"] != "abstain":
                final[family(row["winner"])] += 1
        for member in row["trace"]:
            for gate in member["gate_failures"]:
                gates[gate] += 1
    for fold in FOLDS:
        subset = [r for r in rows if r["fold"] == fold]
        by_fold[str(fold)] = {
            "emissions": len(subset), "decisions_A": dict(Counter(r["decision_a"] for r in subset)),
            "winners_with_probability": dict(Counter(family(r["winner"]) for r in subset if r.get("winner"))),
            "decisions_B": dict(Counter(decision(r, choices[fold]) for r in subset))}
    known_probabilities = [r for r in rows if r.get("probability") is not None]
    probability_bins = []
    for left, right in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.0)):
        subset = [r for r in known_probabilities if left <= r["probability"] and (r["probability"] < right or right == 1.0)]
        probability_bins.append({"left_inclusive": left, "right": right,
            "emissions": len(subset), "observations": len({r["observation_id"] for r in subset}),
            "mean_probability": float(np.mean([r["probability"] for r in subset])) if subset else None,
            "observed_positive_fraction": float(np.mean([r["y"] for r in subset])) if subset else None})
    return {"units": "emissions, not independent observations; traces may repeat week targets",
            "reason_counts": dict(reasons), "winners_with_probability": dict(winners),
            "ecology_reason_codes_on_gated_emissions": dict(geo_reasons),
            "winners_with_final_recommendation": dict(final), "materialized_trace_gate_counts": dict(gates),
            "by_fold": by_fold,
            "descriptive_calibration_available_winner_probabilities_only": {
                "post_selection_not_all_candidates": True, "emissions": len(known_probabilities),
                "brier": float(np.mean([(r["probability"]-r["y"])**2 for r in known_probabilities])) if known_probabilities else None,
                "bins": probability_bins}}


def check_source_seal(records):
    for record in records:
        current = ROOT / record["path"]
        if digest(current) == record["sha256"]:
            continue
        archive = OUTPUT / "source-archive" / (record["sha256"] + ".py")
        if current.suffix != ".py" or not archive.exists() or digest(archive) != record["sha256"]:
            raise ValueError("Sealed dependency changed without a preserved source: " + record["path"])


def read_evidence(cohort):
    rows, choices, sources = [], {}, []
    snapshot = "sha256:" + digest(OUTPUT / "cohort-v2.json")
    for fold in FOLDS:
        root = OUTPUT / f"fold-{fold}"
        choice_path = root / "threshold-choice.json"
        choice = load(choice_path)
        if (choice["schema"], choice["fold"], choice["source_role"], choice["snapshot_id"]) != (1, fold, "threshold", snapshot):
            raise ValueError("Threshold identity invalid")
        if set(choice["species"]) != set(TARGETS) or any(c["threshold"] not in GRID for c in choice["species"].values()):
            raise ValueError("Invalid threshold grid/species")
        if digest(root / "threshold/predictions.jsonl") != choice["predictions_sha256"]:
            raise ValueError("Development evidence changed")
        choices[fold] = choice["species"]
        execution = load(root / "external/execution-code.json")
        choice_ref = str(choice_path.relative_to(ROOT))
        if not any(r["path"] == choice_ref and r["sha256"] == digest(choice_path) for r in execution["files"]):
            raise ValueError("B differs from the choice sealed before external refit")
        for phase in ("ranking", "threshold", "external"):
            stage = root / phase
            summary = load(stage / "summary.json")
            if (summary["status"], summary["fold"], summary["phase"], summary["snapshot_id"]) != ("completed", fold, phase, snapshot):
                raise ValueError("Incomplete fitting phase")
            check_source_seal(load(stage / "execution-code.json")["files"])
            if phase != "ranking":
                check_source_seal(load(stage / "evaluation-seal.json")["files"])
                summary = load(stage / "evaluation-summary.json")
                if (summary["status"], summary["fold"], summary["phase"], summary["snapshot_id"]) != ("completed", fold, phase, snapshot):
                    raise ValueError("Incomplete evaluation phase")
                if summary.get("predictions_sha256") is not None and digest(stage / "predictions.jsonl") != summary["predictions_sha256"]:
                    raise ValueError("Predictions changed since evaluation closure")
        external = root / "external/predictions.jsonl"
        cases = [json.loads(line) for line in external.read_text().splitlines()]
        validate_rows(cases)
        expected = {r["observation_id"]: r for r in cohort["rows"] if r["species_id"] in TARGETS and cohort["folds"][str(fold)][r["observation_id"]] == "external"}
        if {r["observation_id"] for r in cases} != set(expected):
            raise ValueError("External cases lost or added")
        for row in cases:
            original = expected[row["observation_id"]]
            if row["fold"] != fold or row["phase"] != "external" or any(row[k] != original[k] for k in ("species_id", "episode_id", "y")) or row["target_date"] != original["date"]:
                raise ValueError("External case identity/label changed")
        rows.extend(cases)
        for path in (external, choice_path, root / "external/evaluation-summary.json", root / "ranking/quality.json"):
            sources.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path)})
    validate_rows(rows)
    return rows, choices, sources


def main():
    if os.environ.get("RAINMAPPER_PREDICTION_RESEARCH_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py")
    protect_originals()
    cohort = load(OUTPUT / "cohort-v2.json")
    verify_inputs(cohort)
    rows, choices, sources = read_evidence(cohort)
    destination = OUTPUT / "analysis"
    destination.mkdir(exist_ok=False)
    sealed_paths = [Path(__file__), Path(__file__).with_name("common.py"), Path(__file__).with_name("recommendation_metrics.py")]
    sources.extend({"path": str(path.relative_to(ROOT)), "sha256": digest(path)} for path in sealed_paths)
    write_new(destination / "analysis-seal.json", {"files": sources, "bootstrap_replicates": REPLICATES, "seed": SEED,
        "unit": "episode cluster, stratified by external fold; observations weight 1 across horizons",
        "geography_2024_limitation": "Not hashed in the original evaluation seal; current digest recorded at audit, not a retroactive pre-run seal"})
    results = {"choices": choices, "species": {}, "external_observations": len({r["observation_id"] for r in rows}),
               "external_emissions": len(rows), "external_episode_groups_across_species": len({(r["fold"], r["episode_id"]) for r in rows})}
    for sid in TARGETS:
        species_rows = [r for r in rows if r["species_id"] == sid]
        thresholds = {fold: choices[fold][sid]["threshold"] for fold in FOLDS}
        strata = {}
        for label, subset in [("pooled", species_rows)] + [(str(fold), [r for r in species_rows if r["fold"] == fold]) for fold in FOLDS]:
            strata[label] = {"average": describe(subset, thresholds),
                            "horizons": {str(h): describe(subset, thresholds, horizon=h) for h in range(1, 8)}}
        results["species"][sid] = {"strata": strata, "diagnostics": diagnostics(species_rows, thresholds)}
        external_ids = {r["observation_id"] for r in species_rows}
        cohort_rows = [r for r in cohort["rows"] if r["observation_id"] in external_ids]
        results["species"][sid]["spatial_support"] = {
            "areas": len({r["area_id"] for r in cohort_rows}),
            "nonempty_micro_areas": len({r["micro_area_id"] for r in cohort_rows if r.get("micro_area_id")}),
            "area_counts_by_fold": {str(fold): len({r["area_id"] for r in cohort_rows if cohort["folds"][str(fold)][r["observation_id"]] == "external"}) for fold in FOLDS}}
    with (destination / "paired-decisions.jsonl").open("x") as stream:
        for row in rows:
            threshold = choices[row["fold"]][row["species_id"]]["threshold"]
            evidence = {k: row[k] for k in ("observation_id", "episode_id", "species_id", "fold", "horizon", "y", "decision_a", "probability")}
            evidence.update(threshold=threshold, decision_b=decision(row, threshold))
            stream.write(json.dumps(evidence) + "\n")
    verify_inputs(cohort)
    if any(digest(ROOT / r["path"]) != r["sha256"] for r in sources):
        raise ValueError("Evidence changed during analysis")
    write_new(destination / "results.json", results)
    print(json.dumps({"status": "completed", "observations": results["external_observations"], "emissions": len(rows)}))


if __name__ == "__main__":
    main()
