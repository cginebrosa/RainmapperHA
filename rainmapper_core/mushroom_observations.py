"""Shared helpers for mushroom observation payloads."""

from __future__ import annotations

import copy
import math
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


def preserve_observation_provenance(observation, existing, *, precision_supplied=False, duplicate=False):
    """Preserve optional provenance through UI edits; imported identity is not cloned."""
    previous = existing.get("location") or {}
    location = observation["location"]
    old_value = previous.get("precision_m")
    effective_old = old_value if old_value is not None else 0
    if not precision_supplied or location.get("precision_m") is None:
        location["precision_m"] = effective_old
    value = location["precision_m"]
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid positional uncertainty")
    same_point = all(
        isinstance(location.get(k), (float, int)) and isinstance(previous.get(k), (float, int))
        and abs(location[k] - previous[k]) <= 1e-7 for k in ("lat", "lon")
    )
    if same_point and value == effective_old:
        location["precision_origin"] = previous.get("precision_origin") or ("legacy_default_zero" if old_value is None else "manual")
    else:
        location["precision_origin"] = "manual"
        # A radius from GBIF no longer describes a different point.
        if not same_point and location.get("source") == "gbif":
            location["source"] = "manual_decimal"
        if not same_point and value == effective_old:
            location["precision_m"] = 0
            location["precision_origin"] = "legacy_default_zero"
    external = existing.get("external_source")
    if isinstance(external, dict):
        observation["external_source"] = copy.deepcopy(external)
        if duplicate:
            observation["external_source"]["is_copy"] = True
            observation["external_source"]["copied_from_observation_id"] = existing.get("observation_id")
    return observation


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
