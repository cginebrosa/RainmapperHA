"""Bounded, reversible recommendation agreement; never changes model scores."""
from __future__ import annotations

import copy
import math
from collections import Counter
from collections.abc import Mapping

FIELD = "recommendation_policy"
CAPABILITY = "recommendation_consensus_v1"
SPECIES = ("amanita_caesarea", "boletus_edulis", "boletus_pinophilus")
MODES = ("legacy", "shadow", "prudent")
FAMILY = ("version_id", "temporal_contract_id", "profile_id", "estimator_id")


def validate(value=None):
    if value is None:
        value = {"mode": "legacy", "rule_version": "consensus_v1"}
    if (not isinstance(value, dict) or set(value) != {"mode", "rule_version"}
            or value.get("mode") not in MODES or value.get("rule_version") != "consensus_v1"):
        raise ValueError("Invalid recommendation policy.")
    return dict(value)


def settings(registry):
    return validate(registry.get(FIELD))


def family(ref):
    return tuple(ref.get(k) for k in FAMILY)


def data_reasons(member):
    """Count data rejections only; suspension/domain/quality are different causes."""
    if not isinstance(member, Mapping) or member.get("reason") != "runtime_feature_gates_failed":
        return set()
    codes = {r.get("code", "") for r in (member.get("quality") or {}).get("inference_exclusion_reasons", [])
             if isinstance(r, Mapping)}
    result = set()
    if any(c.startswith("rain_coverage_") or c in {"rain_event_search_incomplete", "insufficient_history"} for c in codes):
        result.add("rain_history")
    if "v3_physical_soil_state_unavailable" in codes:
        result.add("soil_water")
    if any("missing" in c or "coverage" in c or "unavailable" in c or "history" in c for c in codes):
        result.add("required_inputs")
    return result


def availability(entries, members, selected_family):
    indexed = {family(m.get("model_ref") or {}): m for m in members}
    ordered = list(dict.fromkeys(family(e.get("candidate") or {}) for e in entries))
    selected_rank = ordered.index(selected_family) if selected_family in ordered else len(ordered)
    reasons = Counter(); rejected = 0; better = 0; evaluated = 0
    for rank, f in enumerate(ordered):
        if f not in indexed:
            continue  # lazy families not executed are not rejected
        evaluated += 1
        causes = data_reasons(indexed[f])
        if causes:
            rejected += 1; better += int(rank < selected_rank)
            reasons.update(causes)
    return {"candidate_family_count": len(ordered), "evaluated_family_count": evaluated,
            "data_rejected_count": rejected, "better_ranked_data_rejected_count": better,
            "reason_counts": dict(sorted(reasons.items()))}


def plan(entries, selected, config, *, species_id):
    config = validate(config)
    if config["mode"] == "legacy" or species_id not in SPECIES:
        return None
    seen = {family(selected)}; alternatives = []; after_selected = False
    # Fixed sealed quality order, independent of day scores and availability.
    for entry in entries:
        candidate = entry.get("candidate") or {}
        key = family(candidate)
        if key == family(selected):
            after_selected = True
        if not after_selected or key in seen:
            continue
        seen.add(key); alternatives.append(dict(candidate))
        if len(alternatives) == 2:
            break
    return {**config, "alternatives": alternatives}


def apply(comparison, resolution, members, gate_failures):
    """Persist a small decision; never transport alternative features/evidence."""
    availability_summary = resolution.get("data_availability")
    if isinstance(availability_summary, Mapping):
        comparison["data_availability"] = copy.deepcopy(availability_summary)
    plan_row = resolution.get("recommendation_plan")
    if not isinstance(plan_row, Mapping):
        return comparison
    config = validate({k: plan_row[k] for k in ("mode", "rule_version")})
    # Precomputed decisions are sealed under the policy/runtime fingerprint.
    cached = resolution.get("recommendation_decision")
    if isinstance(cached, Mapping):
        if any(cached.get(key) != config[key] for key in config):
            raise ValueError("Cached recommendation policy does not match this runtime.")
        decision = copy.deepcopy(dict(cached))
    else:
        winners = comparison.get("selected_winners") or []
        probability = winners[0].get("probability") if len(winners) == 1 else None
        interpretation = comparison.get("interpretation") or {}
        legacy = (interpretation.get("verdict") == "favorable"
                  and isinstance(probability, (int, float)) and probability >= .60)
        votes = []
        if legacy:
            for ref in plan_row.get("alternatives", [])[:2]:
                member = next((m for m in members if m.get("model_ref") == ref), None)
                # Model references may carry additional generation metadata.
                if member is None:
                    member = next((m for m in members if family(m.get("model_ref") or {}) == family(ref)
                                   and (m.get("model_ref") or {}).get("horizon_days") == ref.get("horizon_days")), None)
                failures = gate_failures(member) if member is not None else ["not_materialized"]
                p = (member.get("prediction") or {}).get("probability") if member and not failures else None
                votes.append({"model_ref": dict(member["model_ref"] if member else ref), "probability": p,
                              "status": "unavailable" if failures else "favorable" if p >= .60 else "not_favorable"})
        status = ("not_needed" if not legacy else "unavailable"
                  if len(votes) != 2 or any(v["status"] == "unavailable" for v in votes)
                  else "agreed" if all(v["status"] == "favorable" for v in votes) else "disagreed")
        decision = {**config, "status": status, "legacy_recommend": legacy,
                    "prudent_recommend": legacy and status == "agreed", "comparators": votes}
    comparison["recommendation_decision"] = decision
    if config["mode"] == "prudent" and decision["legacy_recommend"] and not decision["prudent_recommend"]:
        interpretation = copy.deepcopy(comparison.get("interpretation") or {})
        interpretation["verdict"] = "abstain"
        interpretation["reason_codes"] = list(interpretation.get("reason_codes") or []) + ["recommendation_consensus_" + decision["status"]]
        # Keep reference_range and selected_winners as the unchanged diagnostic IFF.
        comparison["interpretation"] = interpretation
    return comparison


def comparator_summaries(decision):
    """At most two small display rows; never include model artifacts or features."""
    from rainmapper_core.mushroom_model_labels import model_source_label
    rows = decision.get("comparators", [])
    if len(rows) > 2:
        raise ValueError("Expected at most two recommendation comparators.")
    result = []
    for row in rows:
        ref = row.get("model_ref") or {}
        label = model_source_label(ref)
        if not label:
            continue
        profile = str(ref.get("profile_id") or "")
        label += " · " + profile if profile else ""
        if len(label) > 256:
            raise ValueError("Recommendation comparator label is too long.")
        result.append({"label": label, "probability": row.get("probability"),
                       "status": row.get("status", "unavailable")})
    return result


def map_notice(comparison):
    """Bounded browser summary; full references stay in the sealed decision."""
    decision = comparison.get("recommendation_decision")
    return {"data_availability": comparison.get("data_availability"),
            "recommendation_decision": ({**{key: decision[key] for key in
                ("mode", "rule_version", "status", "legacy_recommend", "prudent_recommend")},
                "comparators": comparator_summaries(decision)}
                if isinstance(decision, Mapping) else None)}


def valid_map_notice(value):
    if not isinstance(value, dict) or set(value) != {"data_availability", "recommendation_decision"}:
        return False
    a = value["data_availability"]
    if a is not None:
        keys = {"candidate_family_count", "evaluated_family_count", "data_rejected_count",
                "better_ranked_data_rejected_count", "reason_counts"}
        if (not isinstance(a, dict) or set(a) != keys
                or any(type(a[k]) is not int or not 0 <= a[k] <= 10000 for k in keys - {"reason_counts"})
                or not isinstance(a["reason_counts"], dict)
                or set(a["reason_counts"]) - {"rain_history", "soil_water", "required_inputs"}
                or any(type(v) is not int or not 0 <= v <= a["data_rejected_count"] for v in a["reason_counts"].values())
                or not a["better_ranked_data_rejected_count"] <= a["data_rejected_count"] <= a["evaluated_family_count"] <= a["candidate_family_count"]):
            return False
    d = value["recommendation_decision"]
    if d is not None:
        keys = {"mode", "rule_version", "status", "legacy_recommend", "prudent_recommend"}
        if (not isinstance(d, dict) or not keys <= set(d) or set(d) - keys - {"comparators"}
                or d["mode"] not in {"shadow", "prudent"} or d["rule_version"] != "consensus_v1"
                or d["status"] not in {"not_needed", "agreed", "disagreed", "unavailable"}
                or type(d["legacy_recommend"]) is not bool or type(d["prudent_recommend"]) is not bool
                or d["prudent_recommend"] != (d["legacy_recommend"] and d["status"] == "agreed")
                or (d["status"] == "not_needed") != (not d["legacy_recommend"])):
            return False
        rows = d.get("comparators", [])
        if not isinstance(rows, list) or len(rows) > 2:
            return False
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {"label", "probability", "status"}
                    or not isinstance(row["label"], str) or not 1 <= len(row["label"]) <= 256
                    or row["status"] not in {"favorable", "not_favorable", "unavailable"}):
                return False
            p = row["probability"]
            if row["status"] == "unavailable":
                if p is not None:
                    return False
            elif (type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
                  or (row["status"] == "favorable") != (p >= .60)):
                return False
    return True
