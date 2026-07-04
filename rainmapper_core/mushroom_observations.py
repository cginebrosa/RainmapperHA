"""Shared helpers for mushroom observation payloads."""

from __future__ import annotations

import copy
from datetime import date
from typing import Any


SEASON_BY_MONTH = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
    12: "winter",
}
VALID_SEASONS = set(SEASON_BY_MONTH.values())


def derived_fields_from_observed_at(observed_at: object) -> dict[str, object]:
    """Return cheap denormalized fields derived from an observation date."""
    text = str(observed_at or "").strip()
    if not text:
        return {}
    try:
        observed_date = date.fromisoformat(text)
    except ValueError:
        return {}
    month = observed_date.month
    return {
        "month": month,
        "season": SEASON_BY_MONTH[month],
    }


def finalize_observation_payload(observation: dict[str, Any]) -> dict[str, Any]:
    """Return an observation copy with common persisted derived fields updated."""
    finalized = copy.deepcopy(observation)
    derived = finalized.get("derived")
    if not isinstance(derived, dict):
        derived = {}
    derived.update(derived_fields_from_observed_at(finalized.get("observed_at")))
    if derived:
        finalized["derived"] = derived
    else:
        finalized.pop("derived", None)
    return finalized
