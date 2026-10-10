"""Paired retrospective analysis of the sealed A/B/C selector experiment.

This module does not train models, tune thresholds, or run inference. The
predeclared rule can nominate an exploratory candidate only.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from scripts.prediction_model_selection.common import (
    OLD_OUTPUT, OUTPUT, ROOT, TARGETS, digest, load, protect_originals,
    verify_inputs, write_new,
)

FOLDS = (2024, 2025, 2026)
METHODS = ("A", "B", "C")
DECISIONS = ("favorable", "unfavorable", "abstain")
CONTRASTS = (("B", "A"), ("C", "B"), ("C", "A"))
CELLS = tuple(f"{y}_{d}" for y in ("positive", "negative") for d in DECISIONS)
METRICS = ("false_favorable", "true_favorable", "false_unfavorable", "positive_abstain",
           "missed_positive", "recommendations", "precision", "false_discovery_rate",
           "false_positive_rate", "recall", "miss_rate", "coverage", "favorable_coverage")
REPLICATES, SEED = 2000, 20261004
PROTOCOL = ROOT / "docs/agents/prediction-model-selection/protocolo-ejecucion-2026-10-04.md"
INPUT_PROTOCOL = ROOT / "docs/agents/prediction-model-selection/protocolo-control-entradas-2026-10-04.md"
FALLBACK_PROTOCOL = ROOT / "docs/agents/prediction-model-selection/protocolo-correccion-daily-fallback-2026-10-04.md"
DAILY_INDEPENDENT = "independent_daily_family_v1"
DAILY_REUSE = "reuse_B_native_daily_fallback_v1"


def finite(value):
    value = float(value)
    return value if np.isfinite(value) else None


def rates(cells):
    tp, fn, pa, fp, tn, na = np.moveaxis(np.asarray(cells, dtype=float), -1, 0)
    positive, negative = tp + fn + pa, fp + tn + na
    total = positive + negative

    def divide(a, b):
        return np.divide(a, b, out=np.full_like(a, np.nan, dtype=float), where=b > 0)

    return dict(zip(METRICS, (fp, tp, fn, pa, fn + pa, tp + fp,
        divide(tp, tp + fp), divide(fp, tp + fp), divide(fp, negative), divide(tp, positive),
        divide(fn + pa, positive), divide(tp + fp + fn + tn, total), divide(tp + fp, total))))


def validate_rows(rows, cohort=None, *, require_design=False):
    """Reject changed identities/labels, missing horizons, and invalid decisions."""
    observations = {}
    expected = None
    if cohort is not None:
        expected = {(fold, row["observation_id"]): row for fold in FOLDS for row in cohort["rows"]
                    if row["species_id"] in TARGETS and
                    cohort["folds"][str(fold)][row["observation_id"]] == "external"}
    for row in rows:
        identity, fold, horizon = row["observation_id"], row["fold"], row["horizon"]
        if fold not in FOLDS or type(horizon) is not int or horizon not in range(1, 8):
            raise ValueError("Invalid fold/horizon")
        if row["phase"] != "external" or row["species_id"] not in TARGETS or row["y"] not in (0, 1):
            raise ValueError("Invalid external role/species/label")
        target, issue = date.fromisoformat(row["target_date"]), date.fromisoformat(row["issue_date"])
        if issue != target - timedelta(days=horizon - 1) or target.year != fold:
            raise ValueError("Target/issue dates do not match the external fold/horizon")
        previous = observations.setdefault(identity, {"identity": (fold, row["species_id"], row["episode_id"],
                                                        row["y"], row["target_date"]), "horizons": set()})
        if previous["identity"] != (fold, row["species_id"], row["episode_id"], row["y"], row["target_date"]):
            raise ValueError("Inconsistent observation identity/label")
        if horizon in previous["horizons"]:
            raise ValueError("Duplicate observation/horizon")
        previous["horizons"].add(horizon)
        if expected is not None:
            original = expected.get((fold, identity))
            if original is None or any(row[k] != original[k] for k in ("species_id", "episode_id", "y")) or row["target_date"] != original["date"]:
                raise ValueError("External observation differs from frozen cohort")
        for method in METHODS:
            result = row[method]
            if result["decision"] not in DECISIONS:
                raise ValueError("Unknown three-way recommendation")
            probability = result.get("probability")
            if probability is not None and (isinstance(probability, bool) or not np.isfinite(probability) or not 0 <= probability <= 1):
                raise ValueError("Invalid probability")
            if result["decision"] != "abstain" and (probability is None or not result.get("winner")):
                raise ValueError("Recommendation without available winner/probability")
            if result["decision"] == "favorable" and probability < .60:
                raise ValueError("Favorable recommendation below the fixed threshold")
    if not observations or any(v["horizons"] != set(range(1, 8)) for v in observations.values()):
        raise ValueError("Every observation must retain all seven horizons")
    if expected is not None and {(r["fold"], r["observation_id"]) for r in rows} != set(expected):
        raise ValueError("External cases lost or added")
    if require_design:
        counts = Counter(v["identity"][1] for v in observations.values())
        if len(rows) != 812 or len(observations) != 116 or counts != {"boletus_aereus": 55, "amanita_caesarea": 61}:
            raise ValueError("Frozen 116-observation/812-emission design changed")


def episode_tensor(rows, *, horizon=None):
    """One cluster per fold/episode; each observation weighs one across horizons."""
    groups = {}
    for row in rows:
        if horizon is not None and row["horizon"] != horizon:
            continue
        counts = groups.setdefault((row["fold"], row["episode_id"]), np.zeros((3, 6), dtype=float))
        for method_index, method in enumerate(METHODS):
            cell = ("positive" if row["y"] else "negative") + "_" + row[method]["decision"]
            counts[method_index, CELLS.index(cell)] += 1 / 7 if horizon is None else 1
    keys = sorted(groups)
    if not keys:
        raise ValueError("No cases in an external analysis stratum")
    return keys, np.asarray([groups[key] for key in keys])


def bootstrap(keys, tensor, *, replicates=REPLICATES, seed=SEED):
    rng = np.random.default_rng(seed)
    draws = np.zeros((replicates, 3, 6))
    for fold in sorted({key[0] for key in keys}):
        indices = [i for i, key in enumerate(keys) if key[0] == fold]
        selected = rng.choice(indices, size=(replicates, len(indices)), replace=True)
        # Identical cluster multiplicities for all methods and every horizon.
        draws += tensor[selected].sum(axis=1)
    values = {method: rates(draws[:, i]) for i, method in enumerate(METHODS)}
    for alternative, comparator in CONTRASTS:
        values[f"{alternative}_minus_{comparator}"] = {
            metric: values[alternative][metric] - values[comparator][metric] for metric in METRICS}
    output = {}
    for method, metrics in values.items():
        output[method] = {}
        for metric, raw in metrics.items():
            valid = np.asarray(raw)[np.isfinite(raw)]
            output[method][metric] = {
                "lower": finite(np.quantile(valid, .025)) if len(valid) else None,
                "upper": finite(np.quantile(valid, .975)) if len(valid) else None,
                "finite_replicates": int(len(valid)),
            }
    return output


def _method_summary(totals):
    return {"matrix": dict(zip(CELLS, map(float, totals))),
            "metrics": {key: finite(value) for key, value in rates(totals).items()}}


def describe(rows, *, horizon=None, replicates=REPLICATES):
    keys, tensor = episode_tensor(rows, horizon=horizon)
    totals = tensor.sum(axis=0)
    if not np.allclose(totals.sum(axis=1), totals[0].sum()):
        raise AssertionError("A/B/C denominators differ")
    result = {"horizon": horizon or "average_1_to_7", "observations": len({r["observation_id"] for r in rows}),
              "groups": len(keys), "positive_observations": len({r["observation_id"] for r in rows if r["y"]}),
              "negative_observations": len({r["observation_id"] for r in rows if not r["y"]})}
    for index, method in enumerate(METHODS):
        result[method] = _method_summary(totals[index])
        result[method]["recommended_groups"] = int(np.count_nonzero(tensor[:, index, 0] + tensor[:, index, 3]))
        result[method]["groups_with_false_favorable"] = int(np.count_nonzero(tensor[:, index, 3]))
    for alternative, comparator in CONTRASTS:
        result[f"{alternative}_minus_{comparator}"] = {
            metric: finite(result[alternative]["metrics"][metric] - result[comparator]["metrics"][metric])
            if result[alternative]["metrics"][metric] is not None and result[comparator]["metrics"][metric] is not None
            else None for metric in METRICS}
    result["bootstrap_95_percentile"] = bootstrap(keys, tensor, replicates=replicates)
    positive, negative = totals[0, :3].sum(), totals[0, 3:].sum()
    result["controls"] = {
        "always_unfavorable": _method_summary([0, positive, 0, 0, negative, 0]),
        "always_abstain": _method_summary([0, 0, positive, 0, 0, negative]),
    }
    return result


def exploratory_rule(strata, alternative, comparator="A"):
    """Apply the frozen utility rule; never imply independent confirmation."""
    pooled = strata["pooled"]["average"]
    alt, comp = pooled[alternative]["metrics"], pooled[comparator]["metrics"]
    eps = 1e-9
    criteria = {
        "external_positive_support_at_least_5": pooled["positive_observations"] >= 5,
        "external_negative_support_at_least_5": pooled["negative_observations"] >= 5,
        "weighted_favorable_recommendations_at_least_5": alt["recommendations"] + eps >= 5,
        "recommended_episodes_at_least_3": pooled[alternative]["recommended_groups"] >= 3,
        "recall_at_least_25_percent": alt["recall"] is not None and alt["recall"] + eps >= .25,
        "retain_at_least_80_percent_tp": alt["true_favorable"] + eps >= .8 * comp["true_favorable"],
        "retain_at_least_80_percent_coverage": alt["coverage"] is not None and comp["coverage"] is not None and alt["coverage"] + eps >= .8 * comp["coverage"],
        "improve_false_favorables_or_add_tp_without_more_fp": (
            comp["false_favorable"] - alt["false_favorable"] + eps >= .5 or
            (alt["false_favorable"] <= comp["false_favorable"] + eps and
             alt["true_favorable"] - comp["true_favorable"] + eps >= 1)),
    }
    fold_checks = {}
    for fold in FOLDS:
        row = strata[str(fold)]["average"]
        candidate, baseline = row[alternative]["metrics"], row[comparator]["metrics"]
        fold_checks[str(fold)] = {
            "fp_increase_at_most_1": candidate["false_favorable"] <= baseline["false_favorable"] + 1 + eps,
            "retain_half_tp_when_baseline_at_least_2": baseline["true_favorable"] < 2 - eps or
                candidate["true_favorable"] + eps >= .5 * baseline["true_favorable"],
            "fp_change": candidate["false_favorable"] - baseline["false_favorable"],
            "candidate_tp": candidate["true_favorable"], "comparator_tp": baseline["true_favorable"],
        }
    criteria["all_fold_fp_limits"] = all(row["fp_increase_at_most_1"] for row in fold_checks.values())
    criteria["all_fold_tp_limits"] = all(row["retain_half_tp_when_baseline_at_least_2"] for row in fold_checks.values())
    return {"alternative": alternative, "comparator": comparator, "passes": all(criteria.values()),
            "criteria": criteria, "by_fold": fold_checks,
            "interpretation": "exploratory candidate only; no independent confirmation or operational authorization"}


def nomination(strata):
    comparisons = {f"{a}_minus_{b}": exploratory_rule(strata, a, b) for a, b in CONTRASTS}
    candidates = [method for method in ("B", "C") if comparisons[f"{method}_minus_A"]["passes"]]
    def order(method):
        metrics = strata["pooled"]["average"][method]["metrics"]
        return (round(metrics["false_favorable"], 9), -round(metrics["true_favorable"], 9), method != "B")
    return {"comparisons": comparisons,
            "exploratory_nominee": min(candidates, key=order) if candidates else None,
            "action": "propose_independent_confirmation" if candidates else "retain_reference_pending_more_evidence",
            "operational_change_authorized": False}


def family(winner):
    if not winner:
        return None
    return "/".join(str(winner.get(key, "missing")) for key in
                    ("version_id", "profile_id", "temporal_contract_id", "estimator_id"))


def development_diagnostics(catalogs, species_id):
    """Expose only public-safe support and leave-one-episode-out summaries."""
    output = {}
    for fold in FOLDS:
        output[str(fold)] = {}
        for method in ("A", "B"):
            catalog = catalogs[fold][method]
            selections = [row for row in catalog["species_selections"] if row["species_id"] == species_id]
            days = {}
            for selection in selections:
                evidence = selection.get("evidence") or {}
                stability = selection.get("stability") or {}
                days[str(selection["prediction_day"])] = {
                    "selection_status": selection["selection_status"],
                    "winner_family": family(selection.get("candidate")),
                    "candidate_chain_length": len(selection.get("candidate_chain", [])),
                    "support": {key: evidence.get(key) for key in (
                        "observation_count", "validation_group_count", "positive_observation_count",
                        "negative_observation_count", "favorable_call_count", "true_favorable_count",
                        "false_favorable_count", "favorable_precision", "wilson_lower_95_observations")},
                    "stability": {key: stability.get(key) for key in (
                        "method", "omission_count", "same_winner_count", "same_winner_rate")},
                }
            entries = [row for row in catalog["entries"] if row["species_id"] == species_id]
            output[str(fold)][method] = {
                "days": days, "entry_count": len(entries),
                "quality_evidence_counts": dict(Counter(row["evidence"] for row in entries)),
                "support_distribution": dict(sorted(Counter(str(row["n_test"]) for row in entries).items())),
                "fewer_than_8_cases": sum(row["n_test"] < 8 for row in entries),
                "missing_both_classes": sum(not row["both_test_classes"] for row in entries),
                "insufficient_even_with_positive_brier_delta": sum(row["evidence"] == "insufficient" and
                    row.get("brier_delta_vs_prevalence") is not None and row["brier_delta_vs_prevalence"] > 0 for row in entries),
                "note": "entry counts are candidate/contract/horizon entries, never independent observations",
            }
        output[str(fold)]["C"] = {"same_development_catalog_as": "B"}
    return output


def diagnostics(rows, catalogs=None):
    output = {}
    for method in METHODS:
        reasons, reason_codes, winners, final, gates, geo = (Counter() for _ in range(6))
        pairs, brier_causes = Counter(), Counter()
        for row in rows:
            result = row[method]
            reasons[str(result.get("reason"))] += 1
            reason_codes.update(result.get("reason_codes", []))
            geo.update(result.get("geography_reasons", []))
            winner = family(result.get("winner"))
            if winner:
                winners[winner] += 1
                if result["decision"] != "abstain":
                    final[winner] += 1
            for member in result.get("trace", []):
                gates.update(member.get("gate_failures", []))
                if catalogs is not None and "brier_not_better_than_prevalence" in member.get("gate_failures", []):
                    q = catalogs[row["fold"]]["B" if method == "C" else method]
                    matches = [entry for entry in q["entries"] if entry["species_id"] == row["species_id"] and
                               entry["horizon_days"] == member.get("horizon") and family(entry) == family(member.get("family"))]
                    if len(matches) != 1:
                        raise ValueError("Trace quality identity is absent or ambiguous")
                    entry = matches[0]
                    brier_causes[entry["evidence"]] += 1
                    if entry["evidence"] == "insufficient":
                        brier_causes["insufficient_fewer_than_8"] += entry["n_test"] < 8
                        brier_causes["insufficient_missing_both_classes"] += not entry["both_test_classes"]
            days = result.get("weekly_days", [])
            pairs["resolved_week_instances"] += bool(days)
            for first, second in zip(days, days[1:]):
                pairs["adjacent_day_pairs"] += 1
                fa, fb = family(first.get("winner")), family(second.get("winner"))
                if fa and fb:
                    pairs["pairs_with_two_winners"] += 1
                    pairs["family_changes_with_two_winners"] += fa != fb
                pairs["winner_or_availability_changes"] += fa != fb
                pairs["verdict_changes"] += first.get("verdict") != second.get("verdict")
        by_fold = {}
        dominant = []
        for fold in FOLDS:
            subset = [row for row in rows if row["fold"] == fold]
            counts = Counter(family(row[method].get("winner")) for row in subset if row[method].get("winner"))
            most = sorted(counts, key=lambda key: (-counts[key], key))[0] if counts else None
            dominant.append(most)
            by_fold[str(fold)] = {"emissions": len(subset),
                "decisions": dict(Counter(row[method]["decision"] for row in subset)),
                "winner_counts": dict(counts), "dominant_family": most,
                "dominant_share_of_available_winners": counts[most] / sum(counts.values()) if most else None}
        available = [row for row in rows if row[method].get("probability") is not None]
        bins = []
        for left, right in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1)):
            subset = [row for row in available if left <= row[method]["probability"] and
                      (row[method]["probability"] < right or right == 1)]
            bins.append({"left_inclusive": left, "right": right, "emissions": len(subset),
                         "observations": len({row["observation_id"] for row in subset}),
                         "mean_probability": float(np.mean([row[method]["probability"] for row in subset])) if subset else None,
                         "observed_positive_fraction": float(np.mean([row["y"] for row in subset])) if subset else None})
        total = sum(winners.values())
        output[method] = {
            "units": "emissions; overlapping week instances and materialized traces are not independent",
            "reason_counts": dict(reasons), "reason_code_counts": dict(reason_codes),
            "geography_reason_counts": dict(geo), "winner_counts": dict(winners),
            "recommended_winner_counts": dict(final), "materialized_gate_counts": dict(gates),
            "generic_brier_gate_evidence_breakdown": dict(brier_causes),
            "winner_concentration_hhi": sum((count / total) ** 2 for count in winners.values()) if total else None,
            "dominant_winner_share": max(winners.values()) / total if total else None,
            "within_week_stability": dict(pairs), "by_fold": by_fold,
            "dominant_family_changes_between_folds_with_winners": sum(a != b for a, b in zip(dominant, dominant[1:]) if a and b),
            "descriptive_calibration": {"post_selection_available_winners_only": True, "emissions": len(available),
                "brier": float(np.mean([(row[method]["probability"] - row["y"]) ** 2 for row in available])) if available else None,
                "bins": bins},
        }
    return output


def _record(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}


def check_source_seal(records):
    """Sources can advance only when their exact execution bytes are preserved."""
    for record in records:
        current = ROOT / record["path"]
        if current.is_file() and digest(current) == record["sha256"]:
            continue
        archives = [base / "source-archive" / (record["sha256"] + current.suffix) for base in (OUTPUT, OLD_OUTPUT)]
        if current.suffix != ".py" or not any(path.is_file() and digest(path) == record["sha256"] for path in archives):
            raise ValueError("Sealed dependency changed without preserved execution source: " + record["path"])


def validate_control_logs(cases, controls, input_comparisons):
    """A successful summary cannot conceal missing, duplicate or failed checks."""
    expected = {(row["observation_id"], row["horizon"]) for row in cases}
    for records in (controls, input_comparisons):
        keys = [(row["observation_id"], row["horizon"]) for row in records]
        if len(keys) != len(set(keys)) or set(keys) != expected:
            raise ValueError("Technical comparisons do not cover exactly the external emissions")
        if any(row["status"] != "passed" for row in records):
            raise ValueError("A technical comparison failed")
    if any(row["different_fields"] or row["actual_sha256"] != row["expected_sha256"] for row in controls):
        raise ValueError("Technical control differs from its predecessor")
    if any(row["mismatched_materializations"] != 0 or row["mismatched_key_hashes"] for row in input_comparisons):
        raise ValueError("B/C meteorological input contracts differ")
    return {key: sum(row[key] for row in input_comparisons) for key in
            ("shared_materializations", "only_B_materializations", "only_C_materializations")}


def required_evaluation_protocols(fold):
    # The correction was frozen after 2024's unchanged normal weekly branch.
    # Requiring a retroactive seal would misstate its actual execution provenance.
    if fold not in FOLDS:
        raise ValueError("Unknown external fold")
    return (PROTOCOL, INPUT_PROTOCOL) + ((FALLBACK_PROTOCOL,) if fold >= 2025 else ())


def _json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def execution_diagnostics(cases, summary, seal):
    """Validate accounting of the paired harness; this is not runtime latency."""
    fold = summary["fold"]
    limitation = ("paired research harness with technical control and reuse; not a standalone latency comparison; "
                  "standalone C in native daily fallback would incur B's inference cost")
    if fold == 2024:
        return {"execution_modes_recorded": False, "C_execution_modes": None,
                "counts_as_originally_recorded": summary["actual_counts"], "cost_interpretation": limitation,
                "note": "unchanged 2024 weekly branch retained with its original execution source; new fields not backfilled"}
    plans = summary["C_execution_plans"]
    if plans != seal["cardinality"]["C_execution_plans"]:
        raise ValueError("C execution plans differ from their pre-inference seal")
    modes, counts = Counter(), Counter()
    species_counts = {sid: Counter() for sid in TARGETS}
    scientific_fields = summary["technical_control"]["scientific_fields"]
    for sid, plan in plans.items():
        if sid not in TARGETS or plan["species_id"] != sid or plan["quality_sha256"] != summary["quality_sha256"]["B"]:
            raise ValueError("C execution plan identity differs")
        if plan["sha256"] != _json_digest({key: value for key, value in plan.items() if key != "sha256"}):
            raise ValueError("C execution plan digest differs")
        if plan["depends_on_point_probabilities"] is not False or plan["depends_on_observed_outcome"] is not False:
            raise ValueError("C execution route depends on point outcome/probabilities")
        if plan["mode"] not in (DAILY_INDEPENDENT, DAILY_REUSE):
            raise ValueError("Unknown C execution mode")
        states = plan["catalog_states"]
        if plan["mode"] == DAILY_REUSE and (len(states) != 7 or {state["day"] for state in states} != set(range(1, 8)) or
                                           any(state["weekly_status"] != "daily_fallback" for state in states)):
            raise ValueError("Reuse requires a complete native daily-fallback plan")
    for row in cases:
        result, plan = row["C"], plans[row["species_id"]]
        if (result["execution_mode"], result["execution_plan_sha256"]) != (plan["mode"], plan["sha256"]):
            raise ValueError("Point execution differs from its ex-ante plan")
        reused = result["execution_mode"] == DAILY_REUSE
        if result["reused_from"] != ("B" if reused else None):
            raise ValueError("Incorrect reuse provenance")
        if reused:
            payloads = [{key: value.get("decision" if key == "decision_a" else key) for key in scientific_fields}
                        for value in (row["B"], result)]
            if payloads[0] != payloads[1] or result.get("input_contracts") != row["B"].get("input_contracts"):
                raise ValueError("Reused C differs from native daily B")
            if result["reused_scientific_payload_sha256"] != _json_digest(payloads[0]):
                raise ValueError("Reused scientific payload digest differs")
        elif result["reused_scientific_payload_sha256"] is not None:
            raise ValueError("Independent C carries a reused-payload digest")
        trace = result.get("trace", [])
        modes[result["execution_mode"]] += 1
        species_counts[row["species_id"]][result["execution_mode"]] += 1
        counts["scored_emissions"] += 1
        counts["evaluator_calls"] += not reused
        counts["reused_scored_emissions"] += reused
        counts["trace_members"] += len(trace)
        counts["materialized_members"] += 0 if reused else len(trace)
        counts["reused_materialized_members"] += len(trace) if reused else 0
        counts["materialized_available_members"] += 0 if reused else sum(member.get("available") is True for member in trace)
    if dict(modes) != summary["C_execution_modes"] or any(summary["actual_counts"]["C"][key] != value for key, value in counts.items()):
        raise ValueError("C reuse/inference accounting differs from the prediction records")
    return {"execution_modes_recorded": True, "C_execution_modes": dict(modes),
            "C_execution_modes_by_species": {sid: dict(value) for sid, value in species_counts.items()},
            "counts_as_originally_recorded": summary["actual_counts"], "cost_interpretation": limitation}


def read_evidence(cohort):
    rows, sources = [], [_record(OLD_OUTPUT / "cohort-v2.json"), _record(PROTOCOL), _record(INPUT_PROTOCOL), _record(FALLBACK_PROTOCOL)]
    catalogs, executions = {}, {}
    snapshot = "sha256:" + digest(OLD_OUTPUT / "cohort-v2.json")
    from rainmapper_core.mushroom_ml_quality_catalog import validate_catalog
    for fold in FOLDS:
        stage = OUTPUT / f"fold-{fold}/evaluation"
        summary_path, seal_path = stage / "evaluation-summary.json", stage / "evaluation-seal.json"
        summary, seal = load(summary_path), load(seal_path)
        if (summary["status"], summary["fold"], summary["phase"], summary["snapshot_id"]) != ("completed", fold, "external", snapshot):
            raise ValueError("Incomplete/mismatched evaluation phase")
        if (seal["fold"], seal["phase"], seal["snapshot_id"]) != (fold, "external", snapshot):
            raise ValueError("Mismatched pre-evaluation seal")
        external = stage / "predictions.jsonl"
        if summary["predictions_sha256"] != digest(external):
            raise ValueError("Predictions changed after evaluation closure")
        check_source_seal(seal["files"])
        check_source_seal(seal["model_hashes"])
        for protocol in required_evaluation_protocols(fold):
            if not any(record["path"] == str(protocol.relative_to(ROOT)) and record["sha256"] == digest(protocol)
                       for record in seal["files"]):
                raise ValueError("Evaluation did not seal the current frozen protocol")
        cases = [json.loads(line) for line in external.read_text().splitlines()]
        control = summary["technical_control"]
        if control["status"] != "passed" or control["emissions"] != len(cases) or not summary.get("inputs_verified_after"):
            raise ValueError("Technical control/input preservation did not pass for every emission")
        parity = summary["B_C_input_parity"]
        if parity["status"] != "passed" or parity["mismatched_materializations"] != 0:
            raise ValueError("B/C input-contract parity did not pass")
        comparison_logs = []
        for name, field in (("control-comparisons.jsonl", "control_comparisons_sha256"),
                            ("input-contract-comparisons.jsonl", "input_contract_comparisons_sha256")):
            path = stage / name
            if digest(path) != summary[field]:
                raise ValueError("Technical comparison evidence changed")
            sources.append(_record(path))
            comparison_logs.append([json.loads(line) for line in path.read_text().splitlines()])
        counts = validate_control_logs(cases, *comparison_logs)
        if any(parity[key] != value for key, value in counts.items()):
            raise ValueError("B/C input-parity aggregate differs from checked records")
        if summary["quality_sha256"]["C"] != summary["quality_sha256"]["B"]:
            raise ValueError("C did not use exactly B's development evidence")
        executions[str(fold)] = execution_diagnostics(cases, summary, seal)
        catalogs[fold] = {}
        for method in ("A", "B"):
            path = stage.parent / f"quality-{method}.json"
            if digest(path) != summary["quality_sha256"][method]:
                raise ValueError("Development catalog changed since evaluation")
            catalogs[fold][method] = validate_catalog(load(path), require_selections=True)
            if catalogs[fold][method]["snapshot_id"] != snapshot:
                raise ValueError("Development catalog uses another cohort")
            sources.append(_record(path))
        if summary["predictions"] != len(cases) or summary["observations"] * 7 != len(cases) or any(row["fold"] != fold for row in cases):
            raise ValueError("Evaluation summary does not match its cases")
        validate_rows(cases)
        rows.extend(cases)
        sources.extend(_record(path) for path in (external, summary_path, seal_path))
        sources.extend(seal["files"])
        sources.extend(seal["model_hashes"])
    validate_rows(rows, cohort, require_design=True)
    # Preserve each path/hash pair, including distinct execution versions of code.
    sources = list({(record["path"], record["sha256"]): record for record in sources}.values())
    return rows, sources, catalogs, executions


def _number(value, percent=False):
    return "NE" if value is None else f"{value * (100 if percent else 1):.2f}" + ("%" if percent else "")


def spatial_support(cohort, species_id):
    """Inventory cohort exposure, without claiming profile-specific fit inclusion."""
    by_fold = {}
    external = {}
    for fold in FOLDS:
        roles = cohort["folds"][str(fold)]
        training = [row for row in cohort["rows"] if roles[row["observation_id"]] in {"fit", "ranking", "threshold"}]
        cases = [row for row in cohort["rows"] if row["species_id"] == species_id and roles[row["observation_id"]] == "external"]
        external.update({row["observation_id"]: row for row in cases})
        any_species_areas = {row["area_id"] for row in training}
        same_species_areas = {row["area_id"] for row in training if row["species_id"] == species_id}
        by_fold[str(fold)] = {
            "external_observations": len(cases), "external_areas": len({row["area_id"] for row in cases}),
            "observations_in_areas_seen_in_training_any_species": sum(row["area_id"] in any_species_areas for row in cases),
            "observations_in_areas_seen_in_training_same_species": sum(row["area_id"] in same_species_areas for row in cases),
        }
    return {
        "areas": len({row["area_id"] for row in external.values()}),
        "nonempty_micro_areas": len({row["micro_area_id"] for row in external.values() if row.get("micro_area_id")}),
        "by_fold": by_fold,
        "scope": "frozen cohort before profile-specific exclusions; training roles fit/ranking/threshold",
        "new_location_transfer_test": False,
        "interpretation": "area overlap is not exact point overlap and does not prove transfer to unseen places",
    }


def render_tables(results):
    """Public-safe Markdown: no observation, episode, area IDs or coordinates."""
    lines = ["# Comparación retrospectiva de selección de modelos", "",
             "Exploratoria; las observaciones son externas al ajuste, pero ya se habían visto al diseñar las hipótesis.",
             "No constituye confirmación independiente ni autoriza cambios operativos.", "",
             "FP/TP y matrices del promedio ponderan cada horizonte por 1/7. NE = no estimable.",
             "IC: percentiles 95%, 2.000 réplicas por episodios completos, estratificadas por corte, modelos fijos.", ""]
    for sid, content in results["species"].items():
        lines.extend([f"## {sid}", "", "| Corte | Horizonte | Variante | TP | FP | Pos. desfav. | Pos. abst. | Neg. desfav. | Neg. abst. | Precisión | Recall | FPR | Cobertura | Cob. favorable |",
                      "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
        for stratum, data in content["strata"].items():
            for horizon, report in [("media 1–7", data["average"])] + list(data["horizons"].items()):
                for method in METHODS:
                    matrix, metrics = report[method]["matrix"], report[method]["metrics"]
                    cells = [matrix[key] for key in ("positive_favorable", "negative_favorable", "positive_unfavorable", "positive_abstain", "negative_unfavorable", "negative_abstain")]
                    rates_ = [metrics[key] for key in ("precision", "recall", "false_positive_rate", "coverage", "favorable_coverage")]
                    lines.append("| " + " | ".join([stratum, horizon, method] + [_number(v) for v in cells] + [_number(v, True) for v in rates_]) + " |")
        lines.extend(["", "### Diferencias pareadas en el promedio conjunto", "",
                      "| Contraste | Métrica | Diferencia | IC inferior | IC superior | Réplicas válidas |",
                      "|---|---|---:|---:|---:|---:|"])
        pooled = content["strata"]["pooled"]["average"]
        for alt, comp in CONTRASTS:
            label = f"{alt}_minus_{comp}"
            for metric in METRICS:
                ci = pooled["bootstrap_95_percentile"][label][metric]
                lines.append("| " + " | ".join([f"{alt}−{comp}", metric, _number(pooled[label][metric]),
                    _number(ci["lower"]), _number(ci["upper"]), str(ci["finite_replicates"])]) + " |")
        lines.extend(["", "### Regla exploratoria y controles", "",
                      "| Contraste | Supera la regla | Criterios no cumplidos |", "|---|---|---|"])
        for label, report in content["nomination"]["comparisons"].items():
            lines.append(f"| {label} | {'Sí' if report['passes'] else 'No'} | {', '.join(k for k, v in report['criteria'].items() if not v) or 'Ninguno'} |")
        lines.extend(["", "Candidata exploratoria: " + (content["nomination"]["exploratory_nominee"] or "ninguna; mantener referencia"), "",
                      "| Control | Recall | FP | Oportunidades perdidas | Cobertura | Precisión |",
                      "|---|---:|---:|---:|---:|---:|"])
        for label, report in pooled["controls"].items():
            metrics = report["metrics"]
            lines.append("| " + " | ".join([label, _number(metrics["recall"], True), _number(metrics["false_favorable"]),
                _number(metrics["missed_positive"]), _number(metrics["coverage"], True), _number(metrics["precision"], True)]) + " |")
        lines.extend(["", "### Diagnóstico descriptivo", "",
                      "Las frecuencias son emisiones repetidas; el Brier sólo describe el ganador disponible después de seleccionarlo.", "",
                      "| Variante | Ganador dominante | Fracción dominante | Concentración HHI | Cambios de familia entre días / pares con ganador | Brier disponible |",
                      "|---|---|---:|---:|---:|---:|"])
        for method, diagnostic in content["diagnostics"].items():
            counts = diagnostic["winner_counts"]
            dominant = sorted(counts, key=lambda k: (-counts[k], k))[0] if counts else "NE"
            stability = diagnostic["within_week_stability"]
            lines.append("| " + " | ".join([method, dominant, _number(diagnostic["dominant_winner_share"], True),
                _number(diagnostic["winner_concentration_hhi"]),
                f"{stability.get('family_changes_with_two_winners', 0)} / {stability.get('pairs_with_two_winners', 0)}",
                _number(diagnostic["descriptive_calibration"]["brier"])]) + " |")
        lines.append("")
        lines.extend(["### Inventario espacial de la cohorte", "",
                      "Ámbito previo a las exclusiones por perfil; ajuste final = fit + ranking + threshold.",
                      "Un área vista no implica el mismo punto exacto. Esta comparación no prueba transferencia a lugares nuevos.", "",
                      "| Corte | Observaciones externas | Áreas externas | Observaciones en área vista: cualquier especie | Observaciones en área vista: misma especie |",
                      "|---|---:|---:|---:|---:|"])
        for fold, counts in content["spatial_support"]["by_fold"].items():
            values = [counts[key] for key in ("external_observations", "external_areas",
                      "observations_in_areas_seen_in_training_any_species", "observations_in_areas_seen_in_training_same_species")]
            lines.append("| " + " | ".join([fold] + [str(value) for value in values]) + " |")
        lines.append("")
        lines.extend(["### Soporte y sensibilidad del ranking de desarrollo", "",
                      "C comparte exactamente B. Retirar episodios reordena el ranking; no vuelve a ajustar los modelos.", "",
                      "| Corte | Catálogo | Día | Casos | Episodios | Positivos | Negativos | Candidatos | Omisiones | Mismo ganador | Fracción estable |",
                      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
        for fold, methods in content["development_diagnostics"].items():
            for method in ("A", "B"):
                for day, diagnostic in methods[method]["days"].items():
                    support, stability = diagnostic["support"], diagnostic["stability"]
                    values = [support.get(key) for key in ("observation_count", "validation_group_count", "positive_observation_count", "negative_observation_count")]
                    values += [diagnostic["candidate_chain_length"], stability.get("omission_count"), stability.get("same_winner_count")]
                    lines.append("| " + " | ".join([fold, method, day] + [_number(value) for value in values] + [_number(stability.get("same_winner_rate"), True)]) + " |")
        lines.extend(["", "| Corte | Catálogo | Entradas | Evidencia insuficiente | Peor/igual Brier | Mejor Brier | Insuficiente pese a delta Brier positivo |",
                      "|---|---|---:|---:|---:|---:|---:|"])
        for fold, methods in content["development_diagnostics"].items():
            for method in ("A", "B"):
                diagnostic = methods[method]
                counts = diagnostic["quality_evidence_counts"]
                values = [diagnostic["entry_count"], counts.get("insufficient", 0), counts.get("worse_than_prevalence", 0),
                          counts.get("better_than_prevalence", 0), diagnostic["insufficient_even_with_positive_brier_delta"]]
                lines.append("| " + " | ".join([fold, method] + [str(value) for value in values]) + " |")
        lines.append("")
    lines.extend(["## Ejecución y reutilización del arnés", "",
                  "Los contadores miden esta comparación pareada, que incluye un control técnico. No comparan latencia operativa.",
                  "Cuando B ya elige diariamente, C reutiliza B en el arnés; C ejecutado por separado asumiría ese coste de inferencia.",
                  "2024 conserva sus contadores originales: no se añaden retrospectivamente modos que no registró.", "",
                  "| Corte | Emisiones C independientes registradas | Emisiones C reutilizadas registradas | Miembros nuevos C registrados | Miembros C reutilizados registrados |",
                  "|---|---:|---:|---:|---:|"])
    for fold, execution in results["execution_diagnostics"].items():
        modes = execution["C_execution_modes"]
        counts = execution["counts_as_originally_recorded"]["C"]
        values = [modes.get(DAILY_INDEPENDENT, 0) if modes is not None else None,
                  modes.get(DAILY_REUSE, 0) if modes is not None else None,
                  counts.get("materialized_members"), counts.get("reused_materialized_members")]
        lines.append("| " + " | ".join([fold] + [_number(value) for value in values]) + " |")
    lines.extend(["", "Los intervalos no incluyen reajuste de los modelos ni garantizan independencia entre visitas.",
                  "Con pocos episodios, cero errores observados puede producir un bootstrap degenerado: no demuestra riesgo cero.",
                  "El ranking acumulado mezcla antigüedad, soporte y tamaños de ajuste; no aísla sólo el efecto de tener más casos.", ""])
    return "\n".join(lines)


def main():
    if os.environ.get("RAINMAPPER_MODEL_SELECTION_GUARDED") != "1":
        raise SystemExit("Launch through the model-selection bounded.py")
    protect_originals()
    cohort = load(OLD_OUTPUT / "cohort-v2.json")
    verify_inputs(cohort)
    rows, sources, catalogs, executions = read_evidence(cohort)
    sources.extend(_record(path) for path in (Path(__file__), Path(__file__).with_name("common.py")))
    destination = OUTPUT / "analysis"
    destination.mkdir(exist_ok=False)
    for path in (Path(__file__), Path(__file__).with_name("common.py")):
        archive = OUTPUT / "source-archive" / (digest(path) + ".py")
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            with archive.open("xb") as stream:
                stream.write(path.read_bytes())
    write_new(destination / "analysis-seal.json", {"files": sources, "bootstrap_replicates": REPLICATES,
        "seed": SEED, "unit": "episode cluster stratified by external fold; each observation weights one across horizons",
        "independent_confirmation": False})
    results = {"schema": 1, "status": "completed", "independent_confirmation": False,
               "external_observations": len({row["observation_id"] for row in rows}), "external_emissions_per_method": len(rows),
               "external_episode_groups_across_species": len({(row["fold"], row["episode_id"]) for row in rows}),
               "bootstrap_replicates": REPLICATES, "bootstrap_seed": SEED, "species": {}, "execution_diagnostics": executions}
    for sid in TARGETS:
        subset = [row for row in rows if row["species_id"] == sid]
        strata = {}
        for label, cases in [("pooled", subset)] + [(str(fold), [row for row in subset if row["fold"] == fold]) for fold in FOLDS]:
            strata[label] = {"average": describe(cases),
                             "horizons": {str(h): describe(cases, horizon=h) for h in range(1, 8)}}
        results["species"][sid] = {"strata": strata, "diagnostics": diagnostics(subset, catalogs), "nomination": nomination(strata),
            "development_diagnostics": development_diagnostics(catalogs, sid),
            "spatial_support": spatial_support(cohort, sid)}
    verify_inputs(cohort)
    check_source_seal(sources)
    write_new(destination / "results.json", results)
    with (destination / "tablas.md").open("x") as stream:
        stream.write(render_tables(results))
    write_new(destination / "summary.json", {"status": "completed", "inputs_verified_after": True,
        "files": [_record(destination / name) for name in ("analysis-seal.json", "results.json", "tablas.md")],
        "observations": results["external_observations"], "emissions_per_method": len(rows), "operational_change_authorized": False})
    print(json.dumps({"status": "completed", "observations": results["external_observations"], "emissions_per_method": len(rows),
        "exploratory_nominees": {sid: value["nomination"]["exploratory_nominee"] for sid, value in results["species"].items()}}))


if __name__ == "__main__":
    main()
