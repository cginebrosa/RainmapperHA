"""User-owned, reversible model suspensions carried by the runtime registry.

These controls affect serving, never training definitions or archived evidence.
An absent rule permits a model; any matching suspension wins (including global).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Mapping

FIELD = "prediction_model_suspensions"
CAPABILITY = "prediction_model_policy_v1"
_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,159}$")
IDENTITY = ("version_id", "profile_id", "estimator_id", "species_id")
MAX_RULES = 512


def worker_compatible(registry: Mapping, capabilities) -> bool:
    return not registry.get(FIELD) or CAPABILITY in set(capabilities or [])


def validate_rules(value: object) -> list[dict]:
    if not isinstance(value, list) or len(value) > MAX_RULES:
        raise ValueError("Invalid model suspensions (maximum 512).")
    result, seen = [], set()
    for row in value:
        if not isinstance(row, dict):
            raise ValueError("Invalid model suspension.")
        key = tuple(row.get(field) for field in IDENTITY)
        for field, item in zip(IDENTITY, key):
            if not isinstance(item, str) or not (
                _ID.fullmatch(item) or (field == "species_id" and item == "*")
            ):
                raise ValueError(f"Invalid suspension {field}.")
        if key in seen:
            raise ValueError("Duplicate model suspension.")
        reason = row.get("reason")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            raise ValueError("A suspension needs a reason (maximum 500 characters).")
        for field in ("updated_at", "updated_by"):
            if not isinstance(row.get(field), str) or not 0 < len(row[field]) <= 160:
                raise ValueError(f"Invalid suspension {field}.")
        seen.add(key)
        result.append({**dict(zip(IDENTITY, key)), "reason": reason.strip(),
                       "updated_at": row["updated_at"], "updated_by": row["updated_by"]})
    return sorted(result, key=lambda row: tuple(row[field] for field in IDENTITY))


def revision(registry: Mapping) -> str:
    rules = validate_rules(registry.get(FIELD, []))
    return hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()


def suspension(registry: Mapping, model: Mapping) -> dict | None:
    # Registry validation bounds and checks these small rules once when loaded.
    for row in registry.get(FIELD, []):
        if (all(row[field] == model.get(field) for field in IDENTITY[:3])
                and row["species_id"] in {"*", model.get("species_id")}):
            return dict(row)
    return None


def update(registry: dict, *, model_key: str, species_id: str,
           enabled: bool, reason: str, actor: str, expected_revision: str) -> dict:
    from rainmapper_core import mushroom_ml_model_catalog as catalog

    if revision(registry) != expected_revision:
        raise ValueError("Model settings changed. Refresh before saving again.")
    models = {"/".join((row["version_id"], row["profile_id"], estimator))
              for row in catalog.catalog_entries(registry)
              for estimator in row["estimator_ids"]}
    if model_key not in models:
        raise ValueError("Unknown prediction model.")
    version, profile, estimator = model_key.split("/")
    key = (version, profile, estimator, species_id)
    result = copy.deepcopy(registry)
    rows = [row for row in registry.get(FIELD, [])
            if tuple(row[field] for field in IDENTITY) != key]
    if not enabled:
        rows.append({**dict(zip(IDENTITY, key)), "reason": reason,
                     "updated_at": datetime.now(timezone.utc).isoformat(),
                     "updated_by": actor})
    rows = validate_rules(rows)
    if rows:
        result[FIELD] = rows
    else:
        result.pop(FIELD, None)
    # The map reads this registry as bounded metadata; reject before persistence.
    if len(json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')) + 1 > 256 * 1024:
        raise ValueError("Model settings exceed the runtime registry size limit.")
    return result
