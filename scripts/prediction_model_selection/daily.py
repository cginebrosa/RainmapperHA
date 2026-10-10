"""Experimental daily selection using the existing gates and interpretation."""
from __future__ import annotations

import copy
from datetime import date, timedelta
from typing import Callable, Mapping, Sequence

from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_recommendation_policy as recommendations


def resolve_species_days(
    *, species_id: str, point_id: str, issue_date: date,
    resolutions_by_day: Mapping[int, Mapping[str, object]],
    installed_version_ids: Sequence[str], materialize: Callable,
    season_phase: Callable[[date], str], phenology: Mapping[str, object],
    lazy_families: bool = False,
    recommendation_policy: Mapping[str, object] | None = None,
) -> dict:
    """Resolve each original daily chain without the weekly-family aggregate.

    The version/lazy arguments match resolve_species_week, allowing the
    experiment to reuse its existing point evaluator unchanged. Lazy daily
    selection stops at the first gate-eligible family in the sealed order,
    regardless of whether its probability leads to a favorable recommendation.
    This experiment requires shadow policy: daily consensus is unavailable, as
    in the existing daily-fallback path, and cannot change the recommendation.
    """
    if not species_id or not point_id or type(issue_date) is not date:
        raise ValueError("invalid_point_week_identity")
    if set(resolutions_by_day) != set(range(1, 8)) or any(
            type(day) is not int for day in resolutions_by_day):
        raise ValueError("point_week_requires_seven_days")
    config = recommendations.validate(dict(recommendation_policy) if recommendation_policy else None)
    if config["mode"] != "shadow":
        raise ValueError("Daily research requires the frozen shadow policy")
    resolutions = {}
    members_by_day = {}
    for day, original in resolutions_by_day.items():
        if original.get("selection_status") not in {"winner", "abstain"}:
            raise ValueError("point_week_requires_sealed_resolution")
        if any(original.get(field) for field in (
                "runtime_selection_status", "weekly_model_selection", "recommendation_plan",
                "recommendation_decision")):
            raise ValueError("daily_research_requires_original_candidate_chains")
        resolution = copy.deepcopy(dict(original))
        resolutions[day] = resolution
        target = issue_date + timedelta(days=day - 1)
        if resolution["selection_status"] == "abstain":
            members_by_day[day] = []
            continue
        selections = comparison.retarget_operational_selections(
            comparison.reliability_candidate_selections(resolution),
            target_date=target, issue_date=issue_date)
        # Catalog horizons must already be right; retargeting cannot repair a
        # broken seal by silently changing candidate identities.
        if selections != comparison.reliability_candidate_selections(resolution):
            raise ValueError("daily_candidate_horizon_mismatch")
        # Weekly lazy execution prepares a family with its own weather contract.
        # Combining unlike profiles here would silently change that preparation.
        families = {}
        for selection in selections:
            families.setdefault(comparison._weekly_candidate_family(selection), []).append(selection)
        members = []
        for family_selections in families.values():
            result = materialize(target_date=target, selections=family_selections)
            materialized = result.get("members") if isinstance(result, Mapping) else None
            if not isinstance(materialized, list) or any(not isinstance(row, Mapping) for row in materialized):
                raise ValueError("invalid_point_week_materialization")
            members.extend(materialized)
            if lazy_families and any(not comparison._operational_gate_failures(row) for row in materialized):
                break
        members_by_day[day] = members

    # With no weekly_model_selection this helper preserves every daily chain.
    # It only attaches the existing empty shadow-consensus plan where relevant.
    resolutions = comparison.prioritize_weekly_resolutions_by_applicability(
        resolutions, members_by_day, recommendation_policy=config, species_id=species_id)
    days = []
    for day in range(1, 8):
        resolution = resolutions[day]
        target = issue_date + timedelta(days=day - 1)
        if resolution["selection_status"] == "abstain":
            operational = {"available": False, "reason": "reliability_selection_abstained"}
            active = resolution
        else:
            operational, active = comparison.build_reliability_selected_operational_comparison(
                members_by_day[day], resolution,
                season_phase=season_phase(target), phenology=phenology)
        output = {"target_date": target.isoformat(), "prediction_day": day,
                  "operational_comparison": operational, "reliability_selection": active}
        candidate = active.get("candidate") or {}
        member = next((m for m in members_by_day[day]
                       if comparison._candidate_identity(m.get("model_ref") or {}) ==
                       comparison._candidate_identity(candidate)), {})
        applicability = (member.get("prediction") or {}).get("applicability") or {}
        if applicability:
            output["applicability"] = {
                "status": applicability.get("status"),
                "outside": applicability.get("outside_feature_count", 0),
                "total": applicability.get("checked_feature_count", 0),
                "examples": [{key: extreme[key] for key in
                              ("feature", "value", "training_min", "training_max")}
                             for extreme in applicability.get("most_extreme", [])[:3]],
            }
        days.append(output)
    return {"species_id": species_id, "point_id": point_id,
            "issue_date": issue_date.isoformat(), "days": days}
