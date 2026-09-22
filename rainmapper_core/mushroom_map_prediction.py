"""Point-map weekly orchestration through the existing Predictor selectors.

The caller supplies sealed evidence and point-specific model materialization.
This module does not infer geographical eligibility, rank evidence itself,
load datasets, create areas, or publish scientific results to the browser.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable, Mapping, Sequence

from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core.mushroom_predictor_precompute import weekly_aggregate_resolution_index


def resolve_species_week(
    *,
    species_id: str,
    point_id: str,
    issue_date: date,
    resolutions_by_day: Mapping[int, Mapping[str, object]],
    installed_version_ids: Sequence[str],
    materialize: Callable,
    season_phase: Callable[[date], str],
    phenology: Mapping[str, object],
    lazy_families: bool = False,
    recommendation_policy: Mapping[str, object] | None = None,
) -> dict:
    """Use the Predictor's complete-week policy, including daily fallback.

    ``materialize(target_date=..., selections=...)`` returns the shared
    inference result with a ``members`` list. All seven days are required even
    when the UI requests a shorter horizon. Evidence remains caller-owned;
    the point ID is a calculation key, never proof of territorial validation.
    """
    if not species_id or not point_id or type(issue_date) is not date:
        raise ValueError("invalid_point_week_identity")
    if set(resolutions_by_day) != set(range(1,8)) or any(type(day) is not int for day in resolutions_by_day):
        raise ValueError("point_week_requires_seven_days")
    for resolution in resolutions_by_day.values():
        if resolution.get("selection_status") not in ("winner","abstain"):
            raise ValueError("point_week_requires_sealed_resolution")
        if resolution.get("runtime_selection_status") or resolution.get("weekly_model_selection"):
            # Already resolved area results have lost the original alternatives.
            raise ValueError("point_week_requires_original_candidate_chains")
    indexed = weekly_aggregate_resolution_index(
        {(species_id,point_id,day):row for day,row in resolutions_by_day.items()},
        issue_date=issue_date, installed_version_ids=installed_version_ids,
    )
    resolutions = {day:indexed[(species_id,point_id,day)] for day in range(1,8)}
    members_by_day = {day: [] for day in range(1,8)}
    def calculate(day, selections):
        target = issue_date+timedelta(days=day-1)
        selections = comparison.retarget_operational_selections(
            selections, target_date=target, issue_date=issue_date)
        result = materialize(target_date=target,selections=selections)
        members = result.get("members") if isinstance(result,Mapping) else None
        if not isinstance(members,list) or any(not isinstance(row,Mapping) for row in members):
            raise ValueError("invalid_point_week_materialization")
        members_by_day[day].extend(members)
        return members
    weekly = lazy_families and all(
        r.get('selection_status') == 'winner' and
        isinstance(r.get('weekly_model_selection'), Mapping) and
        r['weekly_model_selection'].get('status') != 'daily_fallback'
        for r in resolutions.values())
    if weekly:
        # The aggregate already sorted common families by sealed evidence. Once
        # the first family covers all 7 days, no later family can beat it.
        families = [comparison._weekly_candidate_family(e['candidate'])
                    for e in resolutions[1]['candidate_chain']]
        for family in families:
            coverage = 0
            for day,resolution in resolutions.items():
                comparison.validate_weekly_lag_resolution(resolution,day)
                candidates = [e['candidate'] for e in resolution['candidate_chain']
                    if comparison._weekly_candidate_family(e['candidate']) == family]
                members = calculate(day,candidates)
                coverage += any(not comparison._operational_gate_failures(m) for m in members)
            if coverage == 7:
                break
    else:
        for day,resolution in resolutions.items():
            if resolution['selection_status'] == 'abstain': continue
            comparison.validate_weekly_lag_resolution(resolution,day)
            calculate(day,comparison.reliability_candidate_selections(resolution))

    resolutions = comparison.prioritize_weekly_resolutions_by_applicability(
        resolutions,members_by_day, recommendation_policy=recommendation_policy, species_id=species_id,
    )
    # Reuse already evaluated members; at most two extra fixed families.
    for day, resolution in resolutions.items():
        plan = resolution.get("recommendation_plan") or {}
        selected = resolution.get("candidate") or {}
        winner = next((m for m in members_by_day[day] if comparison._candidate_identity(m.get("model_ref") or {})
                       == comparison._candidate_identity(selected)), None)
        if season_phase(issue_date + timedelta(days=day-1)) == "out_of_season":
            continue
        if winner is None or comparison._operational_gate_failures(winner):
            continue
        if (winner.get("prediction") or {}).get("probability", 0) < .60:
            continue
        existing = {comparison._candidate_identity(m.get("model_ref") or {}) for m in members_by_day[day]}
        needed = [ref for ref in plan.get("alternatives", [])
                  if comparison._candidate_identity(ref) not in existing]
        if needed:
            calculate(day, needed)
    days = []
    for day,resolution in resolutions.items():
        target = issue_date+timedelta(days=day-1)
        if resolution["selection_status"] == "abstain":
            operational = {"available":False,"reason":"reliability_selection_abstained"}
            active = resolution
        else:
            operational,active = comparison.build_reliability_selected_operational_comparison(
                members_by_day[day],resolution,
                season_phase=season_phase(target),phenology=phenology,
            )
        days.append({"target_date":target.isoformat(),"prediction_day":day,
                     "operational_comparison":operational,"reliability_selection":active})
        # Only carry the selected member's compact explanation to the map.
        # Full per-feature diagnostics remain outside the point response.
        candidate = active.get("candidate") or {}
        member = next((m for m in members_by_day[day]
            if comparison._candidate_identity(m.get("model_ref") or {}) ==
               comparison._candidate_identity(candidate)), {})
        applicability = (member.get("prediction") or {}).get("applicability") or {}
        if applicability:
            days[-1]["applicability"] = {
                "status": applicability.get("status"),
                "outside": applicability.get("outside_feature_count", 0),
                "total": applicability.get("checked_feature_count", 0),
                "examples": [{key: extreme[key] for key in
                    ("feature", "value", "training_min", "training_max")}
                    for extreme in applicability.get("most_extreme", [])[:3]],
            }
    return {"species_id":species_id,"point_id":point_id,"issue_date":issue_date.isoformat(),
            "days":days}
