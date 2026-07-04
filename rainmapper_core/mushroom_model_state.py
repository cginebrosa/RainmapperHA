"""Persistent operational state for the mushroom v0 model."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_paths
from rainmapper_core.mushroom_store import write_json_atomic


SCHEMA_VERSION = 1


def state_path() -> Path:
    return mushroom_paths.mushroom_model_state_path()


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def empty_state() -> dict[str, Any]:
    now = utc_timestamp()
    return {
        "schema_version": SCHEMA_VERSION,
        "pending_rebuild_species_ids": [],
        "pending_rebuild_reason": "",
        "updated_at": now,
        "last_full_rebuild_at": "",
        "last_partial_rebuild_at": "",
    }


def load_state(path: Path | None = None) -> dict[str, Any]:
    target = path or state_path()
    if not target.exists():
        return empty_state()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_state()
    if not isinstance(payload, dict):
        return empty_state()
    state = empty_state()
    state.update(payload)
    pending = payload.get("pending_rebuild_species_ids")
    if isinstance(pending, list):
        state["pending_rebuild_species_ids"] = sorted({str(item) for item in pending if str(item or "").strip()})
    else:
        state["pending_rebuild_species_ids"] = []
    return state


def write_state(payload: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    state = empty_state()
    state.update(payload)
    state["schema_version"] = SCHEMA_VERSION
    state["updated_at"] = utc_timestamp()
    pending = state.get("pending_rebuild_species_ids")
    state["pending_rebuild_species_ids"] = (
        sorted({str(item) for item in pending if str(item or "").strip()})
        if isinstance(pending, list) else []
    )
    write_json_atomic(path or state_path(), state)
    return state


def mark_species_pending(species_ids: list[str] | set[str], reason: str = "observations_changed") -> dict[str, Any]:
    state = load_state()
    current = set(state.get("pending_rebuild_species_ids") or [])
    current.update(str(species_id).strip() for species_id in species_ids if str(species_id or "").strip())
    state["pending_rebuild_species_ids"] = sorted(current)
    state["pending_rebuild_reason"] = reason if current else ""
    return write_state(state)


def clear_species_pending(species_ids: list[str] | set[str]) -> dict[str, Any]:
    state = load_state()
    remove = {str(species_id).strip() for species_id in species_ids if str(species_id or "").strip()}
    current = [species_id for species_id in state.get("pending_rebuild_species_ids", []) if species_id not in remove]
    state["pending_rebuild_species_ids"] = current
    state["pending_rebuild_reason"] = state.get("pending_rebuild_reason") if current else ""
    state["last_partial_rebuild_at"] = utc_timestamp()
    return write_state(state)


def clear_all_pending(full_rebuild: bool = False) -> dict[str, Any]:
    state = load_state()
    state["pending_rebuild_species_ids"] = []
    state["pending_rebuild_reason"] = ""
    if full_rebuild:
        state["last_full_rebuild_at"] = utc_timestamp()
    else:
        state["last_partial_rebuild_at"] = utc_timestamp()
    return write_state(state)
