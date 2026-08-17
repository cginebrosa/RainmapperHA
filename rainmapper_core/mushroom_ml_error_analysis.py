"""Row-level flowering phase and shared-error diagnostics."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def assign_observed_phases(rows: list[dict[str, Any]]) -> dict[str, str]:
    by_group: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_group[(str(row.get("species_id")), str(row.get("area_id")), str(row.get("validation_group_id")))].append(row)
    phases: dict[str, str] = {}
    for grouped in by_group.values():
        by_observation: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in grouped:
            by_observation[str(item.get("observation_id") or item.get("sample_id"))].append(item)
        ordered = sorted(
            [items[0] for items in by_observation.values()],
            key=lambda item: (str(item.get("target_date")), str(item.get("observation_id") or item.get("sample_id"))),
        )
        favorable = [index for index, item in enumerate(ordered) if int(item.get("y_true", 0)) == 1]
        observation_phases: dict[str, str] = {}
        for index, item in enumerate(ordered):
            observation_id = str(item.get("observation_id") or item.get("sample_id"))
            if not favorable:
                phase = "unknown_phase"
            elif int(item.get("y_true", 0)) == 1 and len(favorable) == 1:
                phase = "singleton"
            elif index == favorable[0]:
                phase = "onset_observed"
            elif index == favorable[-1]:
                phase = "decline_observed"
            elif int(item.get("y_true", 0)) == 1:
                phase = "active_observed"
            elif favorable[0] < index < favorable[-1]:
                phase = "between_positive_visits"
            elif index < favorable[0]:
                phase = "pre_fruiting_observed"
            else:
                phase = "post_fruiting_observed"
            observation_phases[observation_id] = phase
        for observation_id, items in by_observation.items():
            for item in items:
                phases[str(item["row_key"])] = observation_phases[observation_id]
    return phases


def shared_error_record(row: dict[str, Any], estimator_ids: list[str]) -> dict[str, Any]:
    probabilities = row.get("estimator_probabilities") or {}
    available = [name for name in estimator_ids if probabilities.get(name) is not None]
    y_true = int(row["y_true"])
    wrong = [
        name
        for name in available
        if (y_true == 0 and float(probabilities[name]) >= 0.5)
        or (y_true == 1 and float(probabilities[name]) < 0.5)
    ]
    return {
        **row,
        "available_count": len(available),
        "wrong_count": len(wrong),
        "wrong_estimators": wrong,
        "error_type": "false_positive" if wrong and y_true == 0 else "false_negative" if wrong else None,
        "shared_all": len(available) >= 2 and len(wrong) == len(available),
        "shared_supermajority": len(available) >= 3 and len(wrong) >= math.ceil(2 * len(available) / 3),
        "shared_current_six": len(estimator_ids) == 6 and len(available) == 6 and len(wrong) == 6,
    }
