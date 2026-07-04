#!/usr/bin/env python3
"""Build a non-destructive v0 candidate profile payload.

The current maintained ``mushroom_profiles.json`` keeps the rich schema used by
the existing maintenance UI. The v0 predictor needs a smaller operational set
of fields, but the rich structure must remain available for later work. This
script creates a candidate rich-schema payload under ``tmp/`` by applying the
normalized v0 source only to the fields that v0 can justify today.

The generated payload is not written back to productive data. Numeric affinity
values added for new source-only relationships are schema-compatibility
placeholders; the v0 projection ignores them.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core.mushroom_validation import empty_species_profile


DEFAULT_PROFILES_PATH = REPO_ROOT / "mushroom-data" / "mushroom_profiles.json"
DEFAULT_CATALOGS_PATH = REPO_ROOT / "mushroom-data" / "mushroom_reference_catalogs.json"
DEFAULT_SOURCE_PATH = (
    REPO_ROOT / "docs" / "mushrooms" / "literature" / "marc-estevez-v0-source-normalized.json"
)
DEFAULT_OUTPUT_PROFILES_PATH = (
    REPO_ROOT / "tmp" / "mushroom-lab" / "working" / "profiles" / "mushroom_profiles_v0_candidate.json"
)
DEFAULT_OUTPUT_CATALOG_OVERLAY_PATH = (
    REPO_ROOT
    / "tmp"
    / "mushroom-lab"
    / "working"
    / "profiles"
    / "mushroom_reference_catalogs_v0_overlay_proposal.json"
)
DEFAULT_OUTPUT_CATALOGS_PATH = (
    REPO_ROOT
    / "tmp"
    / "mushroom-lab"
    / "working"
    / "profiles"
    / "mushroom_reference_catalogs_v0_promoted_candidate.json"
)
DEFAULT_OUTPUT_REPORT_PATH = (
    REPO_ROOT
    / "tmp"
    / "mushroom-lab"
    / "output"
    / "reports"
    / "mushroom_profile_v0_candidate_build.md"
)

SOURCE_TO_PROFILE_FIELDS = {
    "host_ids": ("ecology", "host_affinities", "primary"),
    "forest_type_ids": ("ecology", "forest_type_affinities", "primary"),
    "soil_tendency_ids": ("ecology", "soil_affinities", "primary"),
    "habitat_feature_ids": ("ecology", "habitat_feature_affinities", "primary"),
}
LITERATURE_SOURCE_ID = "literature_marc_estevez"

NEW_SPECIES_TROPHIC_MODE_IDS = {
    "cantharellus_lutescens": "trophic_ectomycorrhizal",
    "craterellus_cornucopioides": "trophic_ectomycorrhizal",
    "lactarius_deliciosus": "trophic_ectomycorrhizal",
    "lactarius_salmonicolor_quieticolor_group": "trophic_ectomycorrhizal",
    "lepista_nuda": "trophic_saprotrophic",
    "macrolepiota_procera": "trophic_saprotrophic",
    "marasmius_oreades": "trophic_saprotrophic_or_plant_associated_grassland",
    "russula_virescens": "trophic_ectomycorrhizal",
    "tricholoma_terreum": "trophic_ectomycorrhizal",
    "tuber_melanosporum": "trophic_ectomycorrhizal",
}

CATALOG_GAP_PROPOSALS = {
    "soil_variable": {
        "catalog": "soil_types",
        "entry": {
            "id": "soil_variable",
            "label": {"es": "Variable", "ca": "Variable", "en": "Variable"},
            "ph_min": None,
            "ph_max": None,
            "gis_aliases": ["variable", "indifferent", "sin filtro edafico"],
        },
    },
    "feature_mature_forest": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_mature_forest",
            "label": {"es": "Bosque maduro", "ca": "Bosc madur", "en": "Mature forest"},
        },
    },
    "feature_moist_forest": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_moist_forest",
            "label": {"es": "Bosque humedo", "ca": "Bosc humit", "en": "Moist forest"},
        },
    },
    "feature_shaded_slope": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_shaded_slope",
            "label": {"es": "Umbria", "ca": "Obaga", "en": "Shaded slope"},
        },
    },
    "feature_warm_lowland": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_warm_lowland",
            "label": {
                "es": "Tierra baja calida",
                "ca": "Terra baixa calida",
                "en": "Warm lowland",
            },
        },
    },
    "feature_mediterranean_shrubland": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_mediterranean_shrubland",
            "label": {
                "es": "Matorral mediterraneo",
                "ca": "Matollar mediterrani",
                "en": "Mediterranean shrubland",
            },
        },
    },
    "feature_calcicolous_shrubland": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_calcicolous_shrubland",
            "label": {
                "es": "Matorral calcicola",
                "ca": "Matollar calcicola",
                "en": "Calcicolous shrubland",
            },
        },
    },
    "feature_heath_rockrose_understory": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_heath_rockrose_understory",
            "label": {
                "es": "Sotobosque de brezos o jaras",
                "ca": "Sotabosc de brucs o estepes",
                "en": "Heath or rockrose understory",
            },
        },
    },
    "feature_blueberry_understory": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_blueberry_understory",
            "label": {
                "es": "Sotobosque de arandano",
                "ca": "Sotabosc de nabiu",
                "en": "Blueberry understory",
            },
        },
    },
    "feature_organic_debris": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_organic_debris",
            "label": {
                "es": "Restos organicos visibles",
                "ca": "Restes organiques visibles",
                "en": "Organic debris",
            },
        },
    },
    "feature_disturbed_soil": {
        "catalog": "habitat_features",
        "entry": {
            "id": "feature_disturbed_soil",
            "label": {
                "es": "Suelo removido",
                "ca": "Sol remogut",
                "en": "Disturbed soil",
            },
        },
    },
    "host_corylus_avellana": {
        "catalog": "host_taxa",
        "entry": {
            "id": "host_corylus_avellana",
            "rank": "species",
            "scientific_name": "Corylus avellana",
            "genus": "Corylus",
            "family": "Betulaceae",
            "common_names": {"es": ["avellano"], "ca": ["avellaner"], "en": ["hazel"]},
            "parent_id": None,
            "gis_aliases": ["Corylus avellana", "hazel", "avellano", "avellaner"],
        },
    },
    "host_quercus_faginea": {
        "catalog": "host_taxa",
        "entry": {
            "id": "host_quercus_faginea",
            "rank": "species",
            "scientific_name": "Quercus faginea",
            "genus": "Quercus",
            "family": "Fagaceae",
            "common_names": {"es": ["quejigo"], "ca": ["roure valencia"], "en": ["Portuguese oak"]},
            "parent_id": "host_quercus_spp",
            "gis_aliases": ["Quercus faginea", "quejigo", "roure valencia"],
        },
    },
    "host_quercus_coccifera": {
        "catalog": "host_taxa",
        "entry": {
            "id": "host_quercus_coccifera",
            "rank": "species",
            "scientific_name": "Quercus coccifera",
            "genus": "Quercus",
            "family": "Fagaceae",
            "common_names": {"es": ["coscoja"], "ca": ["garric"], "en": ["kermes oak"]},
            "parent_id": "host_quercus_spp",
            "gis_aliases": ["Quercus coccifera", "coscoja", "garric", "kermes oak"],
        },
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def today_local_iso() -> str:
    return datetime.now().astimezone().date().isoformat()


def list_catalog_ids(catalogs_payload: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    catalogs = catalogs_payload.get("catalogs")
    if not isinstance(catalogs, dict):
        return ids
    for entries in catalogs.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("id"):
                ids.add(str(entry["id"]))
    return ids


def normalize_source_profiles(source_payload: dict[str, Any]) -> list[dict[str, Any]]:
    profiles = source_payload.get("species")
    if not isinstance(profiles, list):
        return []
    return [profile for profile in profiles if isinstance(profile, dict) and profile.get("species_id")]


def source_values(source_profile: dict[str, Any], field: str) -> list[str]:
    values = source_profile.get(field)
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def merge_unique_values(primary: list[str], secondary: Any) -> list[str]:
    result = list(primary)
    if isinstance(secondary, list):
        for value in secondary:
            text = str(value)
            if text and text not in result:
                result.append(text)
    return result


def existing_affinity_by_id(items: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        result[str(item["id"])] = deepcopy(item)
    return result


def build_source_affinities(
    existing_items: Any,
    source_ids: list[str],
    relationship: str,
    preserve_legacy: bool,
) -> list[dict[str, Any]]:
    existing_by_id = existing_affinity_by_id(existing_items)
    affinities: list[dict[str, Any]] = []
    for item_id in source_ids:
        if item_id in existing_by_id:
            item = existing_by_id[item_id]
            item.pop("v0_active", None)
            item["relationship"] = relationship
            source_ids_list = item.get("source_ids")
            if not isinstance(source_ids_list, list):
                source_ids_list = []
            if LITERATURE_SOURCE_ID not in source_ids_list:
                source_ids_list.append(LITERATURE_SOURCE_ID)
            item["source_ids"] = source_ids_list
            affinities.append(item)
            continue
        affinities.append(
            {
                "id": item_id,
                "relationship": relationship,
                "affinity": 0.0,
                "v0_placeholder": True,
                "source_ids": [LITERATURE_SOURCE_ID],
            }
        )
    if preserve_legacy:
        for item_id, item in sorted(existing_by_id.items()):
            if item_id in source_ids:
                continue
            parked_item = deepcopy(item)
            parked_item["v0_active"] = False
            parked_item.setdefault("v0_parking_reason", "legacy_enriched_affinity_not_in_v0_source")
            affinities.append(parked_item)
    return affinities


def append_source_affinity_if_missing(
    ecology: dict[str, Any],
    field: str,
    item_id: str,
) -> None:
    items = ecology.setdefault(field, [])
    if not isinstance(items, list):
        items = []
        ecology[field] = items
    if any(isinstance(item, dict) and item.get("id") == item_id for item in items):
        return
    items.append(
        {
            "id": item_id,
            "relationship": "primary",
            "affinity": 0.0,
            "v0_placeholder": True,
            "source_ids": [LITERATURE_SOURCE_ID],
        }
    )


def apply_catalog_gap_candidates_to_profile(
    candidate: dict[str, Any],
    source_profile: dict[str, Any],
) -> None:
    """Reference promoted catalog gaps from the profiles that requested them."""

    ecology = candidate.setdefault("ecology", {})
    for gap_id in source_values(source_profile, "catalog_gap_candidates"):
        if gap_id.startswith("feature_"):
            append_source_affinity_if_missing(ecology, "habitat_feature_affinities", gap_id)
        elif gap_id.startswith("host_"):
            append_source_affinity_if_missing(ecology, "host_affinities", gap_id)


def normalize_parked_topography_bounds(topography: dict[str, Any]) -> None:
    """Keep rich-schema altitude bounds ordered after broad v0 altitude updates."""

    altitude_min = topography.get("altitude_min_m")
    altitude_max = topography.get("altitude_max_m")
    if not isinstance(altitude_min, (int, float)) or not isinstance(altitude_max, (int, float)):
        return
    if altitude_max < altitude_min:
        altitude_max = altitude_min
        topography["altitude_max_m"] = altitude_max

    optimal_min = topography.get("altitude_optimal_min_m")
    optimal_max = topography.get("altitude_optimal_max_m")
    if not isinstance(optimal_min, (int, float)):
        optimal_min = altitude_min
    if not isinstance(optimal_max, (int, float)):
        optimal_max = optimal_min

    optimal_min = max(altitude_min, min(optimal_min, altitude_max))
    optimal_max = max(optimal_min, min(optimal_max, altitude_max))
    topography["altitude_optimal_min_m"] = optimal_min
    topography["altitude_optimal_max_m"] = optimal_max


def apply_source_to_profile(
    profile: dict[str, Any],
    source_profile: dict[str, Any],
    species_existed: bool,
    include_catalog_gaps: bool,
) -> dict[str, Any]:
    candidate = deepcopy(profile)
    ecology = candidate.setdefault("ecology", {})
    phenology = candidate.setdefault("phenology", {})
    topography = candidate.setdefault("topography", {})
    confidence = candidate.setdefault("prediction_confidence", {})
    metadata = candidate.setdefault("metadata", {})

    for source_field, (_, profile_field, relationship) in SOURCE_TO_PROFILE_FIELDS.items():
        ecology[profile_field] = build_source_affinities(
            ecology.get(profile_field),
            source_values(source_profile, source_field),
            relationship,
            species_existed,
        )

    species_id = str(source_profile.get("species_id", "") or "")
    if not species_existed:
        ecology["trophic_mode_id"] = NEW_SPECIES_TROPHIC_MODE_IDS.get(
            species_id,
            ecology.get("trophic_mode_id", "trophic_ectomycorrhizal"),
        )

    phenology["main_months"] = source_values(source_profile, "main_months")
    phenology["secondary_months"] = source_values(source_profile, "secondary_months")
    phenology["main_months"] = [int(value) for value in phenology["main_months"]]
    phenology["secondary_months"] = [int(value) for value in phenology["secondary_months"]]
    season_pattern_ids = source_values(source_profile, "season_pattern_ids")
    if species_existed:
        season_pattern_ids = merge_unique_values(season_pattern_ids, phenology.get("season_pattern_ids"))
    phenology["season_pattern_ids"] = season_pattern_ids

    if source_profile.get("altitude_min_m") is not None:
        topography["altitude_min_m"] = source_profile["altitude_min_m"]
    if source_profile.get("altitude_max_m") is not None:
        topography["altitude_max_m"] = source_profile["altitude_max_m"]
    normalize_parked_topography_bounds(topography)
    topography.setdefault("preferred_aspect_ids", [])
    topography.setdefault("aspect_notes", "")

    today = today_local_iso()
    if not species_existed:
        metadata["created_at"] = today
    metadata["updated_at"] = today
    metadata["review_status"] = "needs_review"
    metadata["requires_human_validation"] = True
    metadata["v0_candidate_source"] = "docs/mushrooms/literature/marc-estevez-v0-source-normalized.json"
    metadata["v0_candidate_kind"] = "updated_existing" if species_existed else "new_candidate"

    note = str(source_profile.get("v0_notes", "") or "").strip()
    confidence["local_calibration_status"] = "not_calibrated"
    confidence["weather_threshold_confidence"] = "low"
    confidence["notes"] = (
        "v0 candidate generated from normalized source. Numeric affinities marked "
        "v0_placeholder are schema-compatibility placeholders and are not active "
        f"v0 parameters. Source note: {note}"
    )
    if include_catalog_gaps:
        apply_catalog_gap_candidates_to_profile(candidate, source_profile)
    return candidate


def build_candidate_profiles(
    profiles_payload: dict[str, Any],
    source_payload: dict[str, Any],
    include_catalog_gaps: bool = False,
) -> dict[str, Any]:
    current_profiles = [
        profile
        for profile in profiles_payload.get("species_profiles", [])
        if isinstance(profile, dict) and profile.get("species_id")
    ]
    current_by_id = {str(profile["species_id"]): profile for profile in current_profiles}
    source_profiles = normalize_source_profiles(source_payload)
    source_by_id = {str(profile["species_id"]): profile for profile in source_profiles}

    candidates: list[dict[str, Any]] = []
    for source_profile in source_profiles:
        species_id = str(source_profile["species_id"])
        current = current_by_id.get(species_id)
        if current is None:
            current = empty_species_profile(
                species_id,
                str(source_profile.get("scientific_name", "") or species_id),
            )
            species_existed = False
        else:
            species_existed = True
        candidates.append(
            apply_source_to_profile(
                current,
                source_profile,
                species_existed,
                include_catalog_gaps,
            )
        )

    for species_id in sorted(set(current_by_id) - set(source_by_id)):
        candidates.append(deepcopy(current_by_id[species_id]))

    return {
        "schema_version": str(profiles_payload.get("schema_version", "") or ""),
        "model_purpose": "mushroom_fruiting_probability_scoring_v0_candidate",
        "important_note": (
            "Non-productive v0 candidate generated under tmp/. Existing rich schema "
            "is preserved; v0 must ignore numeric placeholder affinities and all "
            "parked weather/scoring fields."
        ),
        "requires_catalog_file": str(profiles_payload.get("requires_catalog_file", "")),
        "species_profiles": sorted(candidates, key=lambda profile: str(profile.get("species_id", ""))),
        "metadata": deepcopy(profiles_payload.get("metadata", {})),
    }


def build_catalog_overlay(
    source_payload: dict[str, Any],
    catalogs_payload: dict[str, Any],
) -> dict[str, Any]:
    known_catalog_ids = list_catalog_ids(catalogs_payload)
    requested_gap_ids: set[str] = set()
    for profile in normalize_source_profiles(source_payload):
        requested_gap_ids.update(source_values(profile, "catalog_gap_candidates"))

    proposals_by_catalog: dict[str, list[dict[str, Any]]] = {}
    unresolved: list[str] = []
    for gap_id in sorted(requested_gap_ids):
        if gap_id in known_catalog_ids:
            continue
        proposal = CATALOG_GAP_PROPOSALS.get(gap_id)
        if not proposal:
            unresolved.append(gap_id)
            continue
        catalog_name = str(proposal["catalog"])
        proposals_by_catalog.setdefault(catalog_name, []).append(deepcopy(proposal["entry"]))

    return {
        "schema_version": "0.1",
        "model_purpose": "mushroom_v0_catalog_overlay_proposal",
        "important_note": (
            "Review-only overlay. Do not merge blindly into productive catalogs; "
            "promote only IDs that are also referenced by productive profiles or GIS mappings."
        ),
        "catalogs": proposals_by_catalog,
        "unresolved_gap_candidates": unresolved,
    }


def build_promoted_catalogs(
    catalogs_payload: dict[str, Any],
    overlay_payload: dict[str, Any],
) -> dict[str, Any]:
    promoted = deepcopy(catalogs_payload)
    catalogs = promoted.setdefault("catalogs", {})
    if not isinstance(catalogs, dict):
        catalogs = {}
        promoted["catalogs"] = catalogs
    overlay_catalogs = overlay_payload.get("catalogs", {})
    if not isinstance(overlay_catalogs, dict):
        return promoted

    for catalog_name, entries in overlay_catalogs.items():
        if not isinstance(entries, list):
            continue
        target_entries = catalogs.setdefault(catalog_name, [])
        if not isinstance(target_entries, list):
            continue
        existing_ids = {
            str(entry.get("id", "") or "")
            for entry in target_entries
            if isinstance(entry, dict)
        }
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            if str(entry["id"]) in existing_ids:
                continue
            target_entries.append(deepcopy(entry))
            existing_ids.add(str(entry["id"]))
    return promoted


def render_report(
    profiles_payload: dict[str, Any],
    source_payload: dict[str, Any],
    candidate_payload: dict[str, Any],
    overlay_payload: dict[str, Any],
) -> str:
    current_ids = {
        str(profile.get("species_id", "") or "")
        for profile in profiles_payload.get("species_profiles", [])
        if isinstance(profile, dict)
    }
    source_profiles = normalize_source_profiles(source_payload)
    source_ids = {str(profile["species_id"]) for profile in source_profiles}
    new_ids = sorted(source_ids - current_ids)
    updated_ids = sorted(source_ids & current_ids)
    placeholder_count = 0
    for profile in candidate_payload["species_profiles"]:
        ecology = profile.get("ecology", {})
        if not isinstance(ecology, dict):
            continue
        for field in (
            "host_affinities",
            "forest_type_affinities",
            "soil_affinities",
            "habitat_feature_affinities",
        ):
            for item in ecology.get(field, []):
                if isinstance(item, dict) and item.get("v0_placeholder"):
                    placeholder_count += 1

    lines = [
        "# Candidate build de perfiles v0",
        "",
        f"Fecha: {today_local_iso()}.",
        "",
        "Salida no productiva generada en `tmp/`. No modifica `mushroom-data/`.",
        "",
        "## Resumen",
        "",
        f"- Perfiles actuales de entrada: {len(current_ids)}",
        f"- Especies normalizadas en fuente v0: {len(source_ids)}",
        f"- Perfiles candidatos generados: {len(candidate_payload['species_profiles'])}",
        f"- Especies actuales actualizadas en candidato: {len(updated_ids)}",
        f"- Especies nuevas en candidato: {len(new_ids)}",
        f"- Afinidades placeholder de compatibilidad schema: {placeholder_count}",
        "",
        "## Especies nuevas",
        "",
    ]
    lines.extend(f"- `{species_id}`" for species_id in new_ids)
    if not new_ids:
        lines.append("- Ninguna")
    lines.extend(
        [
            "",
            "## Overlay de catalogos propuesto",
            "",
            "Este overlay es una propuesta revisable, no un catalogo productivo.",
        ]
    )
    for catalog_name, entries in sorted(overlay_payload["catalogs"].items()):
        lines.append("")
        lines.append(f"### `{catalog_name}`")
        lines.append("")
        lines.extend(f"- `{entry['id']}`" for entry in entries)
    if overlay_payload["unresolved_gap_candidates"]:
        lines.extend(["", "## Gaps sin propuesta", ""])
        lines.extend(f"- `{gap_id}`" for gap_id in overlay_payload["unresolved_gap_candidates"])
    lines.extend(
        [
            "",
            "## Reglas aplicadas",
            "",
            "- Se conservan los bloques ricos existentes cuando una especie ya existia.",
            "- Solo se actualizan campos activos v0: ecologia amplia, temporada y altitud amplia.",
            "- Las afinidades enriquecidas antiguas que no estan en la fuente se conservan como `v0_active: false`.",
            "- Las especies nuevas se crean con el template estructural validable.",
            "- Si `--include-catalog-gaps` esta activo, los gaps promovidos se referencian desde los perfiles que los solicitaron.",
            "- Los valores numericos de afinidad nuevos son placeholders `0.0` y no son parametros v0.",
            "- Los rangos `altitude_optimal_*` se normalizan solo para mantener el schema rico ordenado.",
            "- Los umbrales meteorologicos, pesos de scoring y litologia fina siguen aparcados.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a non-productive v0 mushroom profile candidate.")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--catalogs", type=Path, default=DEFAULT_CATALOGS_PATH)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--output-profiles", type=Path, default=DEFAULT_OUTPUT_PROFILES_PATH)
    parser.add_argument("--output-catalog-overlay", type=Path, default=DEFAULT_OUTPUT_CATALOG_OVERLAY_PATH)
    parser.add_argument("--output-catalogs", type=Path, default=DEFAULT_OUTPUT_CATALOGS_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_OUTPUT_REPORT_PATH)
    parser.add_argument(
        "--include-catalog-gaps",
        action="store_true",
        help="Promote catalog gap candidates into profile affinities and generated catalogs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profiles_payload = load_json(args.profiles)
    catalogs_payload = load_json(args.catalogs)
    source_payload = load_json(args.source)

    candidate_payload = build_candidate_profiles(
        profiles_payload,
        source_payload,
        include_catalog_gaps=args.include_catalog_gaps,
    )
    overlay_payload = build_catalog_overlay(source_payload, catalogs_payload)
    promoted_catalogs_payload = build_promoted_catalogs(catalogs_payload, overlay_payload)
    report = render_report(profiles_payload, source_payload, candidate_payload, overlay_payload)

    write_json(args.output_profiles, candidate_payload)
    write_json(args.output_catalog_overlay, overlay_payload)
    write_json(args.output_catalogs, promoted_catalogs_payload)
    write_text(args.report, report)

    print(f"Wrote candidate profiles: {args.output_profiles}")
    print(f"Wrote catalog overlay proposal: {args.output_catalog_overlay}")
    print(f"Wrote promoted catalog candidate: {args.output_catalogs}")
    print(f"Wrote report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
