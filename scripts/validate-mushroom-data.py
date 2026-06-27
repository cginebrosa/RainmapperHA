#!/usr/bin/env python3
"""Validate mushroom prediction JSON data files.

The mushroom predictor data is maintained as JSON, but it should behave like a
small typed dataset: profiles and GIS mappings may only reference IDs declared
in the reference catalogs, numeric ranges must be coherent, and controlled
values must stay stable. This script reports all detected issues and never
modifies input files.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core.mushroom_validation import validate_profile_semantics

DEFAULT_DATA_DIR = REPO_ROOT / "mushroom-data"

PROFILE_FILE = "mushroom_profiles.json"
CATALOG_FILE = "mushroom_reference_catalogs.json"
GIS_FILE = "mushroom_gis_mappings.json"

REQUIRED_PROFILE_ROOT_KEYS = {
    "schema_version",
    "model_purpose",
    "important_note",
    "requires_catalog_file",
    "species_profiles",
    "metadata",
}
REQUIRED_CATALOG_ROOT_KEYS = {
    "schema_version",
    "model_purpose",
    "important_note",
    "catalogs",
    "metadata",
}
REQUIRED_GIS_ROOT_KEYS = {
    "schema_version",
    "model_purpose",
    "important_note",
    "mapping_sources",
    "vegetation_mappings",
    "corine_land_cover_mappings",
    "lithology_mappings",
    "derived_rules",
    "metadata",
}
REQUIRED_CATALOGS = {
    "trophic_modes",
    "host_taxa",
    "forest_types",
    "soil_types",
    "lithology_types",
    "aspects",
    "season_patterns",
    "habitat_features",
}
REQUIRED_PROFILE_KEYS = {
    "species_id",
    "scientific_name",
    "common_names",
    "taxonomy_status",
    "edibility",
    "ecology",
    "phenology",
    "topography",
    "weather_model",
    "scoring_weights",
    "prediction_confidence",
    "metadata",
}
REQUIRED_ECOLOGY_KEYS = {
    "trophic_mode_id",
    "host_affinities",
    "forest_type_affinities",
    "soil_affinities",
    "lithology_affinities",
    "habitat_feature_affinities",
}
REQUIRED_PHENOLOGY_KEYS = {
    "main_months",
    "secondary_months",
    "season_pattern_ids",
    "fruiting_delay_after_rain_days",
}
REQUIRED_TOPOGRAPHY_KEYS = {
    "altitude_min_m",
    "altitude_optimal_min_m",
    "altitude_optimal_max_m",
    "altitude_max_m",
    "preferred_aspect_ids",
    "aspect_notes",
}
REQUIRED_WEATHER_KEYS = {"rainfall", "temperature", "humidity", "wind"}
REQUIRED_CONFIDENCE_KEYS = {
    "overall_confidence",
    "habitat_confidence",
    "topography_confidence",
    "phenology_confidence",
    "weather_threshold_confidence",
    "taxonomy_confidence",
    "local_calibration_status",
    "calibration_priority",
    "minimum_observations_for_calibration",
    "minimum_positive_observations",
    "minimum_negative_observations",
    "notes",
}
REQUIRED_PROFILE_METADATA_KEYS = {
    "profile_version",
    "created_at",
    "updated_at",
    "created_by",
    "review_status",
    "reviewed_by",
    "source_quality",
    "requires_human_validation",
}
EXPECTED_WEIGHT_KEYS = {
    "habitat",
    "season",
    "altitude",
    "rainfall",
    "temperature",
    "humidity",
    "wind_penalty",
}
SPECIAL_WEIGHT_KEYS = {"snowmelt_or_soil_moisture"}

TAXONOMY_STATUSES = {
    "accepted",
    "uncertain_operational_taxon",
    "species_complex_operational",
}
CONFIDENCE_VALUES = {"low", "medium", "high"}
LOCAL_CALIBRATION_STATUSES = {
    "not_calibrated",
    "partially_calibrated",
    "locally_calibrated",
    "needs_review",
}
CALIBRATION_PRIORITIES = {"low", "medium", "high", "very_high"}
GIS_CONFIDENCE_VALUES = {"low", "medium", "high"}
REVIEW_STATUSES = {"draft", "needs_review", "reviewed", "validated", "deprecated"}


@dataclass(frozen=True)
class ValidationMessage:
    severity: str
    location: str
    message: str
    fix: str | None = None

    def format(self) -> str:
        output = f"{self.severity} [{self.location}] {self.message}"
        if self.fix:
            output += f"\n  Fix: {self.fix}"
        return output


def error(location: str, message: str, fix: str | None = None) -> ValidationMessage:
    return ValidationMessage("ERROR", location, message, fix)


def warning(location: str, message: str, fix: str | None = None) -> ValidationMessage:
    return ValidationMessage("WARN", location, message, fix)


def load_json(path: Path) -> tuple[Any | None, list[ValidationMessage]]:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle), []
    except FileNotFoundError:
        return None, [error(str(path), "file does not exist")]
    except JSONDecodeError as exc:
        return None, [
            error(
                str(path),
                f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            )
        ]


def require_mapping(
    value: Any,
    keys: set[str],
    location: str,
    messages: list[ValidationMessage],
) -> bool:
    if not isinstance(value, dict):
        messages.append(error(location, "expected an object"))
        return False
    for key in sorted(keys - set(value)):
        messages.append(error(f"{location}.{key}", "missing required field"))
    return True


def require_list(
    value: Any,
    location: str,
    messages: list[ValidationMessage],
) -> bool:
    if not isinstance(value, list):
        messages.append(error(location, "expected a list"))
        return False
    return True


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_number(
    value: Any,
    location: str,
    messages: list[ValidationMessage],
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    integer: bool = False,
) -> bool:
    if integer:
        valid_type = isinstance(value, int) and not isinstance(value, bool)
    else:
        valid_type = is_number(value)
    if not valid_type:
        expected = "integer" if integer else "number"
        messages.append(error(location, f"expected {expected}, got {type(value).__name__}"))
        return False
    if minimum is not None and value < minimum:
        messages.append(error(location, f"expected value >= {minimum}, got {value}"))
    if maximum is not None and value > maximum:
        messages.append(error(location, f"expected value <= {maximum}, got {value}"))
    return True


def validate_controlled(
    value: Any,
    allowed: set[str],
    location: str,
    messages: list[ValidationMessage],
) -> None:
    if value not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        messages.append(error(location, f"invalid value {value!r}; expected one of: {allowed_text}"))


def validate_required_keys(
    obj: dict[str, Any],
    required: set[str],
    location: str,
    messages: list[ValidationMessage],
) -> None:
    for key in sorted(required - set(obj)):
        messages.append(error(f"{location}.{key}", "missing required field"))


def collect_catalog_ids(
    catalogs_payload: Any,
    messages: list[ValidationMessage],
) -> dict[str, set[str]]:
    ids_by_catalog: dict[str, set[str]] = {catalog: set() for catalog in REQUIRED_CATALOGS}
    if not require_mapping(catalogs_payload, REQUIRED_CATALOG_ROOT_KEYS, "catalogs", messages):
        return ids_by_catalog

    catalogs = catalogs_payload.get("catalogs")
    if not require_mapping(catalogs, REQUIRED_CATALOGS, "catalogs.catalogs", messages):
        return ids_by_catalog

    for catalog_name in sorted(REQUIRED_CATALOGS):
        entries = catalogs.get(catalog_name)
        if not require_list(entries, f"catalogs.catalogs.{catalog_name}", messages):
            continue
        seen: set[str] = set()
        for index, entry in enumerate(entries):
            location = f"catalogs.{catalog_name}[{index}]"
            if not isinstance(entry, dict):
                messages.append(error(location, "expected an object"))
                continue
            item_id = entry.get("id")
            if not isinstance(item_id, str) or not item_id:
                messages.append(error(f"{location}.id", "missing or invalid catalog ID"))
                continue
            if item_id in seen:
                messages.append(error(f"{location}.id", f"duplicate catalog ID {item_id!r}"))
            seen.add(item_id)
            ids_by_catalog[catalog_name].add(item_id)

    return ids_by_catalog


def validate_id(
    item_id: Any,
    catalog_name: str,
    ids_by_catalog: dict[str, set[str]],
    location: str,
    messages: list[ValidationMessage],
    used_ids: dict[str, set[str]],
) -> None:
    if not isinstance(item_id, str) or not item_id:
        messages.append(error(location, "expected a non-empty catalog ID string"))
        return
    if item_id not in ids_by_catalog.get(catalog_name, set()):
        messages.append(
            error(
                location,
                f"unknown {catalog_name} ID {item_id!r}",
                f"add it to mushroom_reference_catalogs.json/catalogs.{catalog_name} or replace it.",
            )
        )
        return
    used_ids.setdefault(catalog_name, set()).add(item_id)


def validate_affinities(
    profile_id: str,
    affinities: Any,
    catalog_name: str,
    ids_by_catalog: dict[str, set[str]],
    location: str,
    messages: list[ValidationMessage],
    used_ids: dict[str, set[str]],
) -> None:
    if not require_list(affinities, location, messages):
        return
    for index, affinity in enumerate(affinities):
        item_location = f"{location}[{index}]"
        if not isinstance(affinity, dict):
            messages.append(error(item_location, "expected an object"))
            continue
        validate_id(
            affinity.get("id"),
            catalog_name,
            ids_by_catalog,
            f"{item_location}.id",
            messages,
            used_ids,
        )
        if "affinity" not in affinity:
            messages.append(error(f"{item_location}.affinity", "missing required field"))
        elif validate_number(affinity["affinity"], f"{item_location}.affinity", messages):
            if not -1.0 <= affinity["affinity"] <= 1.0:
                messages.append(
                    error(f"{item_location}.affinity", "expected affinity between -1.0 and 1.0")
                )


def validate_ordered_numbers(
    obj: dict[str, Any],
    keys: list[str],
    location: str,
    messages: list[ValidationMessage],
) -> None:
    values = []
    for key in keys:
        if key not in obj:
            messages.append(error(f"{location}.{key}", "missing required field"))
            return
        if not validate_number(obj[key], f"{location}.{key}", messages):
            return
        values.append(obj[key])
    for left_key, left, right_key, right in zip(keys, values, keys[1:], values[1:]):
        if left > right:
            messages.append(
                error(f"{location}.{right_key}", f"expected {left_key} <= {right_key}")
            )


def validate_profile_numeric_ranges(
    profile_id: str,
    profile: dict[str, Any],
    messages: list[ValidationMessage],
) -> None:
    phenology = profile.get("phenology", {})
    for field in ("main_months", "secondary_months"):
        months = phenology.get(field, [])
        if require_list(months, f"profiles.{profile_id}.phenology.{field}", messages):
            for index, month in enumerate(months):
                validate_number(
                    month,
                    f"profiles.{profile_id}.phenology.{field}[{index}]",
                    messages,
                    minimum=1,
                    maximum=12,
                    integer=True,
                )

    delay = phenology.get("fruiting_delay_after_rain_days", {})
    if isinstance(delay, dict):
        validate_ordered_numbers(
            delay,
            ["min", "optimal_min", "optimal_max", "max"],
            f"profiles.{profile_id}.phenology.fruiting_delay_after_rain_days",
            messages,
        )
    else:
        messages.append(
            error(f"profiles.{profile_id}.phenology.fruiting_delay_after_rain_days", "expected an object")
        )

    topography = profile.get("topography", {})
    if isinstance(topography, dict):
        validate_ordered_numbers(
            topography,
            ["altitude_min_m", "altitude_optimal_min_m", "altitude_optimal_max_m", "altitude_max_m"],
            f"profiles.{profile_id}.topography",
            messages,
        )

    weather = profile.get("weather_model", {})
    if isinstance(weather, dict):
        rainfall = weather.get("rainfall", {})
        if isinstance(rainfall, dict):
            validate_ordered_numbers(
                rainfall,
                ["rain_15d_min_mm", "rain_15d_optimal_min_mm", "rain_15d_optimal_max_mm"],
                f"profiles.{profile_id}.weather_model.rainfall",
                messages,
            )
            if "rain_7d_min_mm" in rainfall:
                validate_number(
                    rainfall["rain_7d_min_mm"],
                    f"profiles.{profile_id}.weather_model.rainfall.rain_7d_min_mm",
                    messages,
                    minimum=0,
                )
            if "rain_30d_saturation_penalty_mm" in rainfall:
                validate_number(
                    rainfall["rain_30d_saturation_penalty_mm"],
                    f"profiles.{profile_id}.weather_model.rainfall.rain_30d_saturation_penalty_mm",
                    messages,
                    minimum=0,
                )

        temperature = weather.get("temperature", {})
        if isinstance(temperature, dict):
            validate_ordered_numbers(
                temperature,
                ["temp_min_7d_optimal_min_c", "temp_min_7d_optimal_max_c"],
                f"profiles.{profile_id}.weather_model.temperature",
                messages,
            )
            validate_ordered_numbers(
                temperature,
                ["temp_max_7d_optimal_min_c", "temp_max_7d_optimal_max_c"],
                f"profiles.{profile_id}.weather_model.temperature",
                messages,
            )

        humidity = weather.get("humidity", {})
        if isinstance(humidity, dict):
            for key, value in humidity.items():
                validate_number(
                    value,
                    f"profiles.{profile_id}.weather_model.humidity.{key}",
                    messages,
                    minimum=0,
                    maximum=100,
                )

        wind = weather.get("wind", {})
        if isinstance(wind, dict):
            for key in ("wind_avg_3d_penalty_kmh", "wind_gust_3d_penalty_kmh"):
                if key in wind:
                    validate_number(
                        wind[key],
                        f"profiles.{profile_id}.weather_model.wind.{key}",
                        messages,
                        minimum=0,
                    )
            if "dry_wind_sensitive" in wind and not isinstance(wind["dry_wind_sensitive"], bool):
                messages.append(
                    error(
                        f"profiles.{profile_id}.weather_model.wind.dry_wind_sensitive",
                        "expected boolean",
                    )
                )


def validate_scoring_weights(
    profile_id: str,
    weights: Any,
    messages: list[ValidationMessage],
) -> None:
    location = f"profiles.{profile_id}.scoring_weights"
    if not isinstance(weights, dict):
        messages.append(error(location, "expected an object"))
        return
    missing = EXPECTED_WEIGHT_KEYS - set(weights)
    extra = set(weights) - EXPECTED_WEIGHT_KEYS - SPECIAL_WEIGHT_KEYS
    for key in sorted(missing):
        messages.append(error(f"{location}.{key}", "missing expected scoring weight"))
    for key in sorted(extra):
        messages.append(error(f"{location}.{key}", "unexpected scoring weight key"))
    total = 0.0
    for key, value in weights.items():
        key_location = f"{location}.{key}"
        if validate_number(value, key_location, messages, minimum=0):
            total += float(value)
    if abs(total - 1.0) > 0.001:
        messages.append(error(location, f"weights sum to {total:.6g}, expected approximately 1.0"))


def validate_profiles(
    profiles_payload: Any,
    ids_by_catalog: dict[str, set[str]],
    messages: list[ValidationMessage],
    used_ids: dict[str, set[str]],
) -> None:
    if not require_mapping(profiles_payload, REQUIRED_PROFILE_ROOT_KEYS, "profiles", messages):
        return
    species_profiles = profiles_payload.get("species_profiles")
    if not require_list(species_profiles, "profiles.species_profiles", messages):
        return

    seen_species: set[str] = set()
    for index, profile in enumerate(species_profiles):
        location = f"profiles.species_profiles[{index}]"
        if not isinstance(profile, dict):
            messages.append(error(location, "expected an object"))
            continue
        validate_required_keys(profile, REQUIRED_PROFILE_KEYS, location, messages)
        profile_id = profile.get("species_id", f"index_{index}")
        profile_location = f"profiles.{profile_id}"
        if not isinstance(profile.get("species_id"), str) or not profile.get("species_id"):
            messages.append(error(f"{location}.species_id", "missing or invalid species ID"))
        elif profile_id in seen_species:
            messages.append(error(f"{location}.species_id", f"duplicate species ID {profile_id!r}"))
        seen_species.add(profile_id)

        validate_controlled(
            profile.get("taxonomy_status"),
            TAXONOMY_STATUSES,
            f"{profile_location}.taxonomy_status",
            messages,
        )

        ecology = profile.get("ecology")
        if require_mapping(ecology, REQUIRED_ECOLOGY_KEYS, f"{profile_location}.ecology", messages):
            validate_id(
                ecology.get("trophic_mode_id"),
                "trophic_modes",
                ids_by_catalog,
                f"{profile_location}.ecology.trophic_mode_id",
                messages,
                used_ids,
            )
            validate_affinities(
                profile_id,
                ecology.get("host_affinities"),
                "host_taxa",
                ids_by_catalog,
                f"{profile_location}.ecology.host_affinities",
                messages,
                used_ids,
            )
            validate_affinities(
                profile_id,
                ecology.get("forest_type_affinities"),
                "forest_types",
                ids_by_catalog,
                f"{profile_location}.ecology.forest_type_affinities",
                messages,
                used_ids,
            )
            validate_affinities(
                profile_id,
                ecology.get("soil_affinities"),
                "soil_types",
                ids_by_catalog,
                f"{profile_location}.ecology.soil_affinities",
                messages,
                used_ids,
            )
            validate_affinities(
                profile_id,
                ecology.get("lithology_affinities"),
                "lithology_types",
                ids_by_catalog,
                f"{profile_location}.ecology.lithology_affinities",
                messages,
                used_ids,
            )
            validate_affinities(
                profile_id,
                ecology.get("habitat_feature_affinities"),
                "habitat_features",
                ids_by_catalog,
                f"{profile_location}.ecology.habitat_feature_affinities",
                messages,
                used_ids,
            )

        phenology = profile.get("phenology")
        if require_mapping(
            phenology, REQUIRED_PHENOLOGY_KEYS, f"{profile_location}.phenology", messages
        ):
            for idx, season_id in enumerate(phenology.get("season_pattern_ids", [])):
                validate_id(
                    season_id,
                    "season_patterns",
                    ids_by_catalog,
                    f"{profile_location}.phenology.season_pattern_ids[{idx}]",
                    messages,
                    used_ids,
                )

        topography = profile.get("topography")
        if require_mapping(
            topography, REQUIRED_TOPOGRAPHY_KEYS, f"{profile_location}.topography", messages
        ):
            for idx, aspect_id in enumerate(topography.get("preferred_aspect_ids", [])):
                validate_id(
                    aspect_id,
                    "aspects",
                    ids_by_catalog,
                    f"{profile_location}.topography.preferred_aspect_ids[{idx}]",
                    messages,
                    used_ids,
                )

        weather = profile.get("weather_model")
        require_mapping(weather, REQUIRED_WEATHER_KEYS, f"{profile_location}.weather_model", messages)
        validate_profile_numeric_ranges(str(profile_id), profile, messages)
        validate_scoring_weights(str(profile_id), profile.get("scoring_weights"), messages)
        for issue in validate_profile_semantics(profile):
            messages.append(error(issue.location, issue.message, issue.fix))

        confidence = profile.get("prediction_confidence")
        if require_mapping(
            confidence, REQUIRED_CONFIDENCE_KEYS, f"{profile_location}.prediction_confidence", messages
        ):
            for key in (
                "overall_confidence",
                "habitat_confidence",
                "topography_confidence",
                "phenology_confidence",
                "weather_threshold_confidence",
                "taxonomy_confidence",
            ):
                validate_controlled(
                    confidence.get(key),
                    CONFIDENCE_VALUES,
                    f"{profile_location}.prediction_confidence.{key}",
                    messages,
                )
            validate_controlled(
                confidence.get("local_calibration_status"),
                LOCAL_CALIBRATION_STATUSES,
                f"{profile_location}.prediction_confidence.local_calibration_status",
                messages,
            )
            validate_controlled(
                confidence.get("calibration_priority"),
                CALIBRATION_PRIORITIES,
                f"{profile_location}.prediction_confidence.calibration_priority",
                messages,
            )
            for key in (
                "minimum_observations_for_calibration",
                "minimum_positive_observations",
                "minimum_negative_observations",
            ):
                validate_number(
                    confidence.get(key),
                    f"{profile_location}.prediction_confidence.{key}",
                    messages,
                    minimum=0,
                    integer=True,
                )

        metadata = profile.get("metadata")
        if require_mapping(
            metadata, REQUIRED_PROFILE_METADATA_KEYS, f"{profile_location}.metadata", messages
        ):
            validate_controlled(
                metadata.get("review_status"),
                REVIEW_STATUSES,
                f"{profile_location}.metadata.review_status",
                messages,
            )
            if "requires_human_validation" in metadata and not isinstance(
                metadata["requires_human_validation"], bool
            ):
                messages.append(
                    error(
                        f"{profile_location}.metadata.requires_human_validation",
                        "expected boolean",
                    )
                )


def validate_id_list(
    values: Any,
    catalog_name: str,
    ids_by_catalog: dict[str, set[str]],
    location: str,
    messages: list[ValidationMessage],
    used_ids: dict[str, set[str]],
) -> None:
    if values is None:
        return
    if not require_list(values, location, messages):
        return
    for index, item_id in enumerate(values):
        validate_id(
            item_id,
            catalog_name,
            ids_by_catalog,
            f"{location}[{index}]",
            messages,
            used_ids,
        )


def validate_gis(
    gis_payload: Any,
    ids_by_catalog: dict[str, set[str]],
    messages: list[ValidationMessage],
    used_ids: dict[str, set[str]],
) -> None:
    if not require_mapping(gis_payload, REQUIRED_GIS_ROOT_KEYS, "gis", messages):
        return

    for section in ("vegetation_mappings", "corine_land_cover_mappings"):
        mappings = gis_payload.get(section)
        if not require_list(mappings, f"gis.{section}", messages):
            continue
        for index, mapping in enumerate(mappings):
            location = f"gis.{section}[{index}]"
            if not isinstance(mapping, dict):
                messages.append(error(location, "expected an object"))
                continue
            validate_id_list(
                mapping.get("mapped_host_ids"),
                "host_taxa",
                ids_by_catalog,
                f"{location}.mapped_host_ids",
                messages,
                used_ids,
            )
            validate_id_list(
                mapping.get("mapped_forest_type_ids"),
                "forest_types",
                ids_by_catalog,
                f"{location}.mapped_forest_type_ids",
                messages,
                used_ids,
            )
            validate_id_list(
                mapping.get("mapped_habitat_feature_ids"),
                "habitat_features",
                ids_by_catalog,
                f"{location}.mapped_habitat_feature_ids",
                messages,
                used_ids,
            )
            validate_controlled(
                mapping.get("confidence"),
                GIS_CONFIDENCE_VALUES,
                f"{location}.confidence",
                messages,
            )

    lithology_mappings = gis_payload.get("lithology_mappings")
    if require_list(lithology_mappings, "gis.lithology_mappings", messages):
        for index, mapping in enumerate(lithology_mappings):
            location = f"gis.lithology_mappings[{index}]"
            if not isinstance(mapping, dict):
                messages.append(error(location, "expected an object"))
                continue
            validate_id_list(
                mapping.get("mapped_lithology_ids"),
                "lithology_types",
                ids_by_catalog,
                f"{location}.mapped_lithology_ids",
                messages,
                used_ids,
            )
            validate_id_list(
                mapping.get("mapped_soil_tendency_ids"),
                "soil_types",
                ids_by_catalog,
                f"{location}.mapped_soil_tendency_ids",
                messages,
                used_ids,
            )
            validate_controlled(
                mapping.get("confidence"),
                GIS_CONFIDENCE_VALUES,
                f"{location}.confidence",
                messages,
            )

    all_catalog_lookup = {
        item_id: catalog_name
        for catalog_name, values in ids_by_catalog.items()
        for item_id in values
    }
    derived_rules = gis_payload.get("derived_rules")
    if require_list(derived_rules, "gis.derived_rules", messages):
        for index, rule in enumerate(derived_rules):
            location = f"gis.derived_rules[{index}]"
            if not isinstance(rule, dict):
                messages.append(error(location, "expected an object"))
                continue
            validate_controlled(
                rule.get("confidence"),
                GIS_CONFIDENCE_VALUES,
                f"{location}.confidence",
                messages,
            )
            outputs = rule.get("outputs")
            if not require_list(outputs, f"{location}.outputs", messages):
                continue
            for output_index, output_id in enumerate(outputs):
                output_location = f"{location}.outputs[{output_index}]"
                if not isinstance(output_id, str) or output_id not in all_catalog_lookup:
                    messages.append(
                        error(
                            output_location,
                            f"unknown internal catalog ID {output_id!r}",
                            "emit only IDs declared in mushroom_reference_catalogs.json.",
                        )
                    )
                    continue
                used_ids.setdefault(all_catalog_lookup[output_id], set()).add(output_id)


def add_unused_catalog_warnings(
    ids_by_catalog: dict[str, set[str]],
    used_ids: dict[str, set[str]],
    messages: list[ValidationMessage],
) -> None:
    for catalog_name, ids in sorted(ids_by_catalog.items()):
        unused = sorted(ids - used_ids.get(catalog_name, set()))
        for item_id in unused:
            messages.append(
                warning(
                    f"catalogs.{catalog_name}.{item_id}",
                    "catalog ID is not referenced by profiles or GIS mappings",
                )
            )


def validate_mushroom_data(data_dir: Path = DEFAULT_DATA_DIR) -> list[ValidationMessage]:
    profile_payload, profile_messages = load_json(data_dir / PROFILE_FILE)
    catalog_payload, catalog_messages = load_json(data_dir / CATALOG_FILE)
    gis_payload, gis_messages = load_json(data_dir / GIS_FILE)
    messages = [*profile_messages, *catalog_messages, *gis_messages]
    if profile_payload is None or catalog_payload is None or gis_payload is None:
        return messages

    ids_by_catalog = collect_catalog_ids(catalog_payload, messages)
    used_ids: dict[str, set[str]] = {catalog_name: set() for catalog_name in REQUIRED_CATALOGS}

    validate_profiles(profile_payload, ids_by_catalog, messages, used_ids)
    validate_gis(gis_payload, ids_by_catalog, messages, used_ids)
    add_unused_catalog_warnings(ids_by_catalog, used_ids, messages)
    return messages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Rainmapper mushroom predictor JSON data.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing the three mushroom JSON files.",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Return exit code 1 when warnings are present.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    messages = validate_mushroom_data(args.data_dir)
    errors = [message for message in messages if message.severity == "ERROR"]
    warnings = [message for message in messages if message.severity == "WARN"]

    if messages:
        for message in messages:
            print(message.format(), file=sys.stderr if message.severity == "ERROR" else sys.stdout)

    print(
        f"Mushroom data validation finished: {len(errors)} error(s), {len(warnings)} warning(s)."
    )
    if errors or (warnings and args.fail_on_warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
