"""Semantic validation helpers for mushroom predictor profile data.

The JSON schema validator checks structure and catalog references. These
helpers cover profile-level consistency rules that matter to maintainers, such
as duplicated choices or ambiguous month assignments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


AFFINITY_FIELDS = (
    "host_affinities",
    "forest_type_affinities",
    "soil_affinities",
    "lithology_affinities",
    "habitat_feature_affinities",
)

SIMPLE_ARRAY_FIELDS = (
    ("common_names",),
    ("phenology", "main_months"),
    ("phenology", "secondary_months"),
    ("phenology", "season_pattern_ids"),
    ("topography", "preferred_aspect_ids"),
)
SPECIES_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class ProfileValidationIssue:
    """A developer-facing semantic validation issue for one profile field."""

    location: str
    message: str
    fix: str | None = None


def _profile_id(profile: dict[str, Any]) -> str:
    return str(profile.get("species_id", "") or "-")


def _nested_value(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _duplicate_values(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if not normalized:
            continue
        if normalized in seen:
            duplicates.add(normalized)
        seen.add(normalized)
    return sorted(duplicates)


def validate_profile_semantics(profile: dict[str, Any]) -> list[ProfileValidationIssue]:
    """Return all semantic consistency issues detected for one species profile."""

    profile_id = _profile_id(profile)
    issues: list[ProfileValidationIssue] = []

    for path in SIMPLE_ARRAY_FIELDS:
        values = _nested_value(profile, path)
        if not isinstance(values, list):
            continue
        duplicates = _duplicate_values(values)
        if duplicates:
            location = ".".join(("profiles", profile_id, *path))
            issues.append(
                ProfileValidationIssue(
                    location=location,
                    message=f"contains duplicate values: {', '.join(duplicates)}",
                    fix="Remove repeated values before saving the profile.",
                )
            )

    phenology = profile.get("phenology")
    if isinstance(phenology, dict):
        main_months = phenology.get("main_months")
        secondary_months = phenology.get("secondary_months")
        if isinstance(main_months, list) and isinstance(secondary_months, list):
            overlap = sorted(
                {
                    str(month).strip()
                    for month in main_months
                    if str(month).strip()
                    and str(month).strip()
                    in {str(item).strip() for item in secondary_months}
                },
                key=lambda item: (0, int(item)) if item.isdigit() else (1, item),
            )
            if overlap:
                issues.append(
                    ProfileValidationIssue(
                        location=f"profiles.{profile_id}.phenology",
                        message=(
                            "main_months and secondary_months overlap: "
                            + ", ".join(overlap)
                        ),
                        fix="Keep each month either as main or secondary, not both.",
                    )
                )

    ecology = profile.get("ecology")
    if isinstance(ecology, dict):
        for field in AFFINITY_FIELDS:
            values = ecology.get(field)
            if not isinstance(values, list):
                continue
            ids = [
                str(item.get("id", "") or "").strip()
                for item in values
                if isinstance(item, dict)
            ]
            duplicates = _duplicate_values(ids)
            if duplicates:
                issues.append(
                    ProfileValidationIssue(
                        location=f"profiles.{profile_id}.ecology.{field}",
                        message=f"contains duplicate IDs: {', '.join(duplicates)}",
                        fix="Keep one affinity row per catalog ID.",
                    )
                )

    return issues


def validate_profiles_semantics(payload: dict[str, Any]) -> list[ProfileValidationIssue]:
    """Return semantic consistency issues for every profile in a profiles file."""

    profiles = payload.get("species_profiles")
    if not isinstance(profiles, list):
        return []
    issues: list[ProfileValidationIssue] = []
    for profile in profiles:
        if isinstance(profile, dict):
            issues.extend(validate_profile_semantics(profile))
    return issues


def validate_new_species_id(species_id: str, profiles: list[dict[str, Any]]) -> tuple[bool, str]:
    """Validate a new stable species ID before adding it to a profiles file."""

    if not species_id:
        return False, "Species ID is required."
    if not SPECIES_ID_PATTERN.fullmatch(species_id):
        return False, "Species ID must start with a lowercase letter and use only lowercase letters, numbers and underscores."
    if any(str(profile.get("species_id", "")) == species_id for profile in profiles):
        return False, f"Species profile {species_id} already exists."
    return True, ""


def empty_species_profile(species_id: str, scientific_name: str, common_name: str = "") -> dict[str, Any]:
    """Build a complete draft profile that passes structural validation.

    The generated profile is intentionally conservative: it is marked as draft,
    not calibrated and requiring human validation. Maintainers must review all
    ecological, phenological and weather parameters before using it for
    prediction.
    """

    today = datetime.now(UTC).date().isoformat()
    common_names = [common_name.strip()] if common_name.strip() else []
    return {
        "species_id": species_id,
        "scientific_name": scientific_name.strip(),
        "common_names": common_names,
        "taxonomy_status": "accepted",
        "edibility": "good",
        "ecology": {
            "trophic_mode_id": "trophic_ectomycorrhizal",
            "host_affinities": [],
            "forest_type_affinities": [],
            "soil_affinities": [],
            "lithology_affinities": [],
            "habitat_feature_affinities": [],
        },
        "phenology": {
            "main_months": [],
            "secondary_months": [],
            "season_pattern_ids": [],
            "fruiting_delay_after_rain_days": {
                "min": 0,
                "optimal_min": 0,
                "optimal_max": 0,
                "max": 0,
            },
        },
        "topography": {
            "altitude_min_m": 0,
            "altitude_optimal_min_m": 0,
            "altitude_optimal_max_m": 0,
            "altitude_max_m": 0,
            "preferred_aspect_ids": [],
            "aspect_notes": "",
        },
        "weather_model": {
            "rainfall": {
                "rain_7d_min_mm": 0,
                "rain_15d_min_mm": 0,
                "rain_15d_optimal_min_mm": 0,
                "rain_15d_optimal_max_mm": 0,
                "rain_30d_saturation_penalty_mm": 0,
            },
            "temperature": {
                "temp_min_7d_optimal_min_c": 0,
                "temp_min_7d_optimal_max_c": 0,
                "temp_max_7d_optimal_min_c": 0,
                "temp_max_7d_optimal_max_c": 0,
                "heat_penalty_temp_max_c": 0,
                "frost_penalty_temp_min_c": 0,
            },
            "humidity": {
                "humidity_min_7d_preferred_min_pct": 0,
                "humidity_max_7d_preferred_min_pct": 0,
            },
            "wind": {
                "wind_avg_3d_penalty_kmh": 0,
                "wind_gust_3d_penalty_kmh": 0,
                "dry_wind_sensitive": False,
            },
        },
        "scoring_weights": {
            "habitat": 0.25,
            "season": 0.15,
            "altitude": 0.10,
            "rainfall": 0.20,
            "temperature": 0.15,
            "humidity": 0.10,
            "wind_penalty": 0.05,
        },
        "prediction_confidence": {
            "overall_confidence": "low",
            "habitat_confidence": "low",
            "topography_confidence": "low",
            "phenology_confidence": "low",
            "weather_threshold_confidence": "low",
            "taxonomy_confidence": "medium",
            "local_calibration_status": "not_calibrated",
            "calibration_priority": "medium",
            "minimum_observations_for_calibration": 20,
            "minimum_positive_observations": 8,
            "minimum_negative_observations": 12,
            "notes": "Starter profile created from Rainmapper maintenance UI. Review all ecological, phenological and weather parameters before using it for prediction.",
        },
        "metadata": {
            "profile_version": "0.1",
            "created_at": today,
            "updated_at": today,
            "created_by": "rainmapper_ha_ui",
            "review_status": "draft",
            "reviewed_by": None,
            "source_quality": "mixed",
            "requires_human_validation": True,
        },
    }
