"""Canonical operational mushroom training scope and transport-neutral plan."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from rainmapper_core import mushroom_ml_multiversion_plan
from rainmapper_core import mushroom_ml_trainer
from rainmapper_core import mushroom_ml_tuning_catalog


SCOPE_SCHEMA_VERSION = "1.0"
SCOPE_KIND = "mushroom_operational_training_scope"
ELIGIBILITY_REVISION = "area-episode-eligibility-2026-08-28.1"
PLAN_SCHEMA_VERSION = "1.0"
PLAN_KIND = "mushroom_operational_training_plan"
MIN_EPISODES_DEFAULT = 10


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _identity(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _payload_rows(payload: object) -> list[dict[str, Any]]:
    raw_rows = payload.get("rows", payload) if isinstance(payload, Mapping) else payload
    if not isinstance(raw_rows, list):
        raise ValueError("Operational training features must contain a row list")
    return [dict(row) for row in raw_rows if isinstance(row, Mapping)]


def build_scope(
    features_payload: object,
    known_sites_payload: object,
    *,
    min_episodes: int = MIN_EPISODES_DEFAULT,
) -> dict[str, Any]:
    """Calculate eligibility once, after canonical area/date aggregation."""
    if not isinstance(min_episodes, int) or min_episodes < 1:
        raise ValueError("Operational training min_episodes must be positive")
    rows = _payload_rows(features_payload)
    if not isinstance(known_sites_payload, Mapping):
        raise ValueError("Operational training known-sites payload must be an object")
    micro_area_to_area = {
        str(row.get("micro_area_id")): str(row.get("area_id"))
        for row in known_sites_payload.get("micro_areas", [])
        if isinstance(row, Mapping)
        and str(row.get("micro_area_id") or "")
        and str(row.get("area_id") or "")
    }
    candidate_counts = Counter(
        str(row.get("species_id"))
        for row in rows
        if str(row.get("species_id") or "")
    )
    species_rows: list[dict[str, Any]] = []
    admitted: list[str] = []
    omitted: list[dict[str, Any]] = []
    for species_id in sorted(candidate_counts):
        eligible_rows = mushroom_ml_trainer.filter_eligible(rows, species_id)
        episodes = mushroom_ml_trainer.aggregate_to_area_episodes(
            eligible_rows,
            micro_area_to_area,
        )
        classes = sorted(
            {
                str(row.get("prediction_target"))
                for row in episodes
                if str(row.get("prediction_target") or "")
            }
        )
        decision = "admitted"
        reason_code = "eligible"
        if len(episodes) < min_episodes:
            decision = "omitted"
            reason_code = "insufficient_area_episodes"
        elif not {"favorable", "unfavorable"}.issubset(classes):
            decision = "omitted"
            reason_code = "missing_required_classes"
        row = {
            "species_id": species_id,
            "row_count": candidate_counts[species_id],
            "eligible_row_count": len(eligible_rows),
            "area_episode_count": len(episodes),
            "classes": classes,
            "decision": decision,
            "reason_code": reason_code,
        }
        species_rows.append(row)
        if decision == "admitted":
            admitted.append(species_id)
        else:
            omitted.append(
                {
                    "species_id": species_id,
                    "reason_code": reason_code,
                    "eligible_row_count": len(eligible_rows),
                    "area_episode_count": len(episodes),
                    "classes": classes,
                }
            )
    source_identity = {
        "features_sha256": _identity(features_payload),
        "known_sites_sha256": _identity(known_sites_payload),
    }
    identity_payload = {
        "eligibility_revision": ELIGIBILITY_REVISION,
        "min_episodes": min_episodes,
        "source_identity": source_identity,
        "species": species_rows,
        "admitted_species_ids": admitted,
        "omitted_species": omitted,
    }
    return {
        "schema_version": SCOPE_SCHEMA_VERSION,
        "kind": SCOPE_KIND,
        "scope_id": _identity(identity_payload),
        **identity_payload,
    }


def validate_scope(payload: object) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("Operational training scope must be an object")
    if (
        payload.get("schema_version") != SCOPE_SCHEMA_VERSION
        or payload.get("kind") != SCOPE_KIND
    ):
        raise ValueError("Operational training scope contract is invalid")
    identity_payload = {
        key: payload.get(key)
        for key in (
            "eligibility_revision",
            "min_episodes",
            "source_identity",
            "species",
            "admitted_species_ids",
            "omitted_species",
        )
    }
    if payload.get("scope_id") != _identity(identity_payload):
        raise ValueError("Operational training scope identity is invalid")
    admitted = identity_payload["admitted_species_ids"]
    if not isinstance(admitted, list) or not admitted:
        raise ValueError("Operational training scope contains no admitted species")
    if admitted != sorted(set(str(value) for value in admitted)):
        raise ValueError("Operational training admitted species are not canonical")
    return json.loads(json.dumps(dict(payload)))


def build_plan(
    registry: Mapping[str, object],
    scope: Mapping[str, object],
    tuning_catalog: Mapping[str, object],
    *,
    version_ids: Sequence[str],
    profile_keys: Sequence[str],
) -> dict[str, Any]:
    """Seal the scientific work independently from executor and job identifiers."""
    checked_scope = validate_scope(scope)
    versions = sorted({str(value) for value in version_ids})
    profiles = sorted({str(value) for value in profile_keys})
    generation_ids = {version_id: f"plan_{version_id}" for version_id in versions}
    fit_plan = mushroom_ml_multiversion_plan.build_plan(
        registry,
        batch_id="operational_plan",
        snapshot_id=checked_scope["scope_id"],
        generation_ids=generation_ids,
        species_ids=checked_scope["admitted_species_ids"],
        version_ids=versions,
        profile_keys=profiles,
    )
    checked_catalog = mushroom_ml_tuning_catalog.validate_catalog(
        registry,
        tuning_catalog,
    )
    expected_tuning_keys = {
        mushroom_ml_tuning_catalog.decision_key(fit["artifact_ref"])
        for fit in fit_plan["fits"]
    }
    available_tuning_keys = {
        str(row["key"]) for row in checked_catalog["decisions"]
    }
    missing_tuning_keys = sorted(expected_tuning_keys - available_tuning_keys)
    if missing_tuning_keys:
        raise ValueError(
            "Tuning catalog does not cover the plan: "
            + ", ".join(missing_tuning_keys)
        )
    fit_scopes = [
        {
            "artifact_scope": {
                key: value
                for key, value in fit["artifact_ref"].items()
                if key not in {"batch_id", "generation_id"}
            },
            "estimator_scope": fit["estimator_scope"],
            "training_species_ids": fit["training_species_ids"],
            "supported_horizons": fit["supported_horizons"],
        }
        for fit in fit_plan["fits"]
    ]
    identity_payload = {
        "scope": checked_scope,
        "scope_id": checked_scope["scope_id"],
        "tuning_catalog_id": checked_catalog["catalog_id"],
        "version_ids": versions,
        "profile_keys": profiles,
        "fit_count": len(fit_scopes),
        "fits": fit_scopes,
    }
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "kind": PLAN_KIND,
        "plan_id": _identity(identity_payload),
        **identity_payload,
    }


def validate_plan(payload: object) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("Operational training plan must be an object")
    if payload.get("schema_version") != PLAN_SCHEMA_VERSION or payload.get("kind") != PLAN_KIND:
        raise ValueError("Operational training plan contract is invalid")
    checked_scope = validate_scope(payload.get("scope"))
    identity_payload = {
        key: payload.get(key)
        for key in (
            "scope",
            "scope_id",
            "tuning_catalog_id",
            "version_ids",
            "profile_keys",
            "fit_count",
            "fits",
        )
    }
    if identity_payload["scope_id"] != checked_scope["scope_id"]:
        raise ValueError("Operational training plan scope identity is inconsistent")
    if payload.get("plan_id") != _identity(identity_payload):
        raise ValueError("Operational training plan identity is invalid")
    if identity_payload["fit_count"] != len(identity_payload["fits"] or []):
        raise ValueError("Operational training plan fit count is invalid")
    return json.loads(json.dumps(dict(payload)))


def assert_trained_species(plan: Mapping[str, object], trained_species: Sequence[str]) -> None:
    checked = validate_plan(plan)
    assert_scope_trained_species(checked["scope"], trained_species)


def assert_scope_trained_species(
    scope: Mapping[str, object], trained_species: Sequence[str]
) -> None:
    checked = validate_scope(scope)
    expected = checked["admitted_species_ids"]
    actual = sorted({str(value) for value in trained_species})
    if actual != expected:
        raise ValueError(
            "ML v0 trained species do not match the sealed operational scope: "
            f"expected {expected}, got {actual}"
        )
