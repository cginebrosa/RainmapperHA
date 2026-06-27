"""Semantic validation helpers for mushroom predictor profile data.

The JSON schema validator checks structure and catalog references. These
helpers cover profile-level consistency rules that matter to maintainers, such
as duplicated choices or ambiguous month assignments.
"""

from __future__ import annotations

from dataclasses import dataclass
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
