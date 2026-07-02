"""Build the operational v0 view of mushroom species profiles.

The maintained profile file intentionally keeps a richer schema than the first
predictor should use. This module defines the small, explicit projection used by
v0 so the engine and future v0 maintenance UI can share the same contract while
the richer profile editor remains parked for later calibration work.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PROFILE_V0_SCHEMA_VERSION = "0.1"
PROFILE_V0_MODEL_PURPOSE = "mushroom_profiles_v0_operational_projection"

ACTIVE_V0_PROFILE_FIELDS = (
    "identity",
    "ecology.trophic_mode_id",
    "ecology.host_affinities",
    "ecology.forest_type_affinities",
    "ecology.soil_affinities",
    "ecology.habitat_feature_affinities",
    "phenology.main_months",
    "phenology.secondary_months",
    "phenology.season_pattern_ids",
    "topography.altitude_min_m",
    "topography.altitude_max_m",
    "topography.preferred_aspect_ids",
    "metadata.review_status",
    "prediction_confidence.local_calibration_status",
)

PARKED_V0_PROFILE_FIELDS = (
    "ecology.lithology_affinities",
    "phenology.fruiting_delay_after_rain_days",
    "topography.altitude_optimal_min_m",
    "topography.altitude_optimal_max_m",
    "weather_model",
    "scoring_weights",
    "prediction_confidence.weather_threshold_confidence",
    "prediction_confidence.minimum_observations_for_calibration",
    "prediction_confidence.minimum_positive_observations",
    "prediction_confidence.minimum_negative_observations",
)


def _copy_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    return []


def _copy_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    return {}


def _profile_id(profile: dict[str, Any]) -> str:
    return str(profile.get("species_id", "") or "")


def _simplify_affinities(values: Any) -> list[dict[str, str]]:
    """Return v0 affinity records without numeric weights.

    Existing profiles store numeric affinity values that are not trusted as v0
    engine parameters. The v0 contract keeps only catalog IDs and their broad
    relationship label so the first engine can compare habitat signals without
    treating old weights as calibrated.
    """

    if not isinstance(values, list):
        return []
    simplified: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        if item.get("v0_active") is False:
            continue
        affinity_id = str(item.get("id", "") or "").strip()
        if not affinity_id:
            continue
        relationship = str(item.get("relationship", "") or "present").strip() or "present"
        simplified.append({"id": affinity_id, "relationship": relationship})
    return simplified


def project_profile_v0(profile: dict[str, Any]) -> dict[str, Any]:
    """Project one rich profile into the operational v0 contract."""

    ecology = _copy_mapping(profile.get("ecology"))
    phenology = _copy_mapping(profile.get("phenology"))
    topography = _copy_mapping(profile.get("topography"))
    confidence = _copy_mapping(profile.get("prediction_confidence"))
    metadata = _copy_mapping(profile.get("metadata"))

    return {
        "species_id": _profile_id(profile),
        "scientific_name": str(profile.get("scientific_name", "") or ""),
        "common_names": _copy_list(profile.get("common_names")),
        "taxonomy_status": str(profile.get("taxonomy_status", "") or ""),
        "edibility": str(profile.get("edibility", "") or ""),
        "v0_model_status": {
            "review_status": str(metadata.get("review_status", "") or ""),
            "requires_human_validation": bool(metadata.get("requires_human_validation", True)),
            "local_calibration_status": str(
                confidence.get("local_calibration_status", "not_calibrated") or "not_calibrated"
            ),
            "numeric_weather_model_active": False,
            "scoring_weights_active": False,
        },
        "ecology": {
            "trophic_mode_id": str(ecology.get("trophic_mode_id", "") or ""),
            "host_affinities": _simplify_affinities(ecology.get("host_affinities")),
            "forest_type_affinities": _simplify_affinities(ecology.get("forest_type_affinities")),
            "soil_tendency_affinities": _simplify_affinities(ecology.get("soil_affinities")),
            "habitat_feature_affinities": _simplify_affinities(
                ecology.get("habitat_feature_affinities")
            ),
        },
        "phenology": {
            "main_months": _copy_list(phenology.get("main_months")),
            "secondary_months": _copy_list(phenology.get("secondary_months")),
            "season_pattern_ids": _copy_list(phenology.get("season_pattern_ids")),
        },
        "topography": {
            "altitude_min_m": topography.get("altitude_min_m"),
            "altitude_max_m": topography.get("altitude_max_m"),
            "preferred_aspect_ids": _copy_list(topography.get("preferred_aspect_ids")),
            "aspect_notes": str(topography.get("aspect_notes", "") or ""),
        },
        "weather_hypotheses": [],
        "parked_profile_fields": list(PARKED_V0_PROFILE_FIELDS),
    }


def project_profiles_payload_v0(payload: dict[str, Any]) -> dict[str, Any]:
    """Project a full rich profiles payload into a minimal v0 payload."""

    profiles = payload.get("species_profiles")
    if not isinstance(profiles, list):
        profiles = []
    return {
        "schema_version": PROFILE_V0_SCHEMA_VERSION,
        "model_purpose": PROFILE_V0_MODEL_PURPOSE,
        "source_profile_schema_version": str(payload.get("schema_version", "") or ""),
        "active_profile_fields": list(ACTIVE_V0_PROFILE_FIELDS),
        "parked_profile_fields": list(PARKED_V0_PROFILE_FIELDS),
        "species_profiles": [
            project_profile_v0(profile) for profile in profiles if isinstance(profile, dict)
        ],
    }
