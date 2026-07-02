#!/usr/bin/env python3
"""Compare the normalized v0 source with current mushroom profiles.

The script is intentionally read-only for productive data. It compares the
normalized source extracted from the reviewed Marc Estevez summary against the
current rich profiles, using the v0 projection contract from
``rainmapper_core.mushroom_profile_v0``. Reports are written under ``tmp/`` by
default so they can include operational review notes without entering the Home
Assistant image or productive JSON stores.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core.mushroom_profile_v0 import project_profiles_payload_v0


DEFAULT_PROFILES_PATH = REPO_ROOT / "mushroom-data" / "mushroom_profiles.json"
DEFAULT_CATALOGS_PATH = REPO_ROOT / "mushroom-data" / "mushroom_reference_catalogs.json"
DEFAULT_SOURCE_PATH = (
    REPO_ROOT / "docs" / "mushrooms" / "literature" / "marc-estevez-v0-source-normalized.json"
)
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "tmp" / "mushroom-lab" / "output" / "reports" / "mushroom_profile_v0_source_audit.md"
)
DEFAULT_JSON_PATH = (
    REPO_ROOT / "tmp" / "mushroom-lab" / "working" / "features" / "mushroom_profile_v0_source_audit.json"
)

CATALOG_FIELDS = {
    "host_ids": "host_taxa",
    "forest_type_ids": "forest_types",
    "soil_tendency_ids": "soil_types",
    "habitat_feature_ids": "habitat_features",
    "season_pattern_ids": "season_patterns",
}

PROJECTED_FIELDS = {
    "host_ids": ("ecology", "host_affinities"),
    "forest_type_ids": ("ecology", "forest_type_affinities"),
    "soil_tendency_ids": ("ecology", "soil_tendency_affinities"),
    "habitat_feature_ids": ("ecology", "habitat_feature_affinities"),
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def catalog_ids(catalogs_payload: dict[str, Any]) -> dict[str, set[str]]:
    catalogs = catalogs_payload.get("catalogs")
    if not isinstance(catalogs, dict):
        return {}
    result: dict[str, set[str]] = {}
    for name, entries in catalogs.items():
        if isinstance(entries, list):
            result[name] = {
                str(entry.get("id", "") or "")
                for entry in entries
                if isinstance(entry, dict) and entry.get("id")
            }
    return result


def affinity_ids(projected_profile: dict[str, Any], field: str) -> list[str]:
    path = PROJECTED_FIELDS[field]
    current: Any = projected_profile
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    if not isinstance(current, list):
        return []
    ids: list[str] = []
    for item in current:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return sorted(dict.fromkeys(ids))


def normalized_ids(source_profile: dict[str, Any], field: str) -> list[str]:
    values = source_profile.get(field)
    if not isinstance(values, list):
        return []
    return sorted(dict.fromkeys(str(value) for value in values if str(value)))


def compare_lists(current: list[str], source: list[str]) -> dict[str, list[str]]:
    current_set = set(current)
    source_set = set(source)
    return {
        "current": sorted(current_set),
        "source": sorted(source_set),
        "shared": sorted(current_set & source_set),
        "source_adds": sorted(source_set - current_set),
        "current_only": sorted(current_set - source_set),
    }


def validate_source_catalog_ids(
    source_profiles: list[dict[str, Any]],
    ids_by_catalog: dict[str, set[str]],
) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for source_profile in source_profiles:
        species_id = str(source_profile.get("species_id", "") or "-")
        for field, catalog_name in CATALOG_FIELDS.items():
            valid_ids = ids_by_catalog.get(catalog_name, set())
            for value in normalized_ids(source_profile, field):
                if value not in valid_ids:
                    missing.append(
                        {
                            "species_id": species_id,
                            "field": field,
                            "catalog": catalog_name,
                            "id": value,
                        }
                    )
    return missing


def build_audit(
    profiles_payload: dict[str, Any],
    catalogs_payload: dict[str, Any],
    source_payload: dict[str, Any],
) -> dict[str, Any]:
    projected_payload = project_profiles_payload_v0(profiles_payload)
    projected_by_id = {
        str(profile.get("species_id", "") or ""): profile
        for profile in projected_payload.get("species_profiles", [])
        if isinstance(profile, dict)
    }
    source_profiles = [
        profile for profile in source_payload.get("species", []) if isinstance(profile, dict)
    ]
    source_by_id = {
        str(profile.get("species_id", "") or ""): profile
        for profile in source_profiles
        if profile.get("species_id")
    }

    current_ids = set(projected_by_id)
    source_ids = set(source_by_id)
    ids_by_catalog = catalog_ids(catalogs_payload)
    source_catalog_errors = validate_source_catalog_ids(source_profiles, ids_by_catalog)

    species_rows: list[dict[str, Any]] = []
    for species_id in sorted(current_ids | source_ids):
        source_profile = source_by_id.get(species_id)
        current_profile = projected_by_id.get(species_id)
        row: dict[str, Any] = {
            "species_id": species_id,
            "scientific_name": (
                str(source_profile.get("scientific_name", "") or "")
                if source_profile
                else str(current_profile.get("scientific_name", "") or "")
            ),
            "status": "existing" if current_profile else "new_candidate",
            "in_current_profiles": current_profile is not None,
            "in_v0_source": source_profile is not None,
            "catalog_gap_candidates": (
                source_profile.get("catalog_gap_candidates", [])
                if isinstance(source_profile, dict)
                else []
            ),
            "v0_notes": (
                str(source_profile.get("v0_notes", "") or "")
                if isinstance(source_profile, dict)
                else ""
            ),
        }
        if source_profile and current_profile:
            for field in PROJECTED_FIELDS:
                row[field] = compare_lists(
                    affinity_ids(current_profile, field),
                    normalized_ids(source_profile, field),
                )
            row["main_months"] = compare_lists(
                [str(value) for value in current_profile.get("phenology", {}).get("main_months", [])],
                [str(value) for value in source_profile.get("main_months", [])],
            )
            row["secondary_months"] = compare_lists(
                [
                    str(value)
                    for value in current_profile.get("phenology", {}).get("secondary_months", [])
                ],
                [str(value) for value in source_profile.get("secondary_months", [])],
            )
        elif source_profile:
            for field in PROJECTED_FIELDS:
                row[field] = {
                    "current": [],
                    "source": normalized_ids(source_profile, field),
                    "shared": [],
                    "source_adds": normalized_ids(source_profile, field),
                    "current_only": [],
                }
            row["main_months"] = {
                "current": [],
                "source": [str(value) for value in source_profile.get("main_months", [])],
                "shared": [],
                "source_adds": [str(value) for value in source_profile.get("main_months", [])],
                "current_only": [],
            }
            row["secondary_months"] = {
                "current": [],
                "source": [str(value) for value in source_profile.get("secondary_months", [])],
                "shared": [],
                "source_adds": [str(value) for value in source_profile.get("secondary_months", [])],
                "current_only": [],
            }
        species_rows.append(row)

    gap_counter: Counter[str] = Counter()
    for profile in source_profiles:
        gaps = profile.get("catalog_gap_candidates")
        if isinstance(gaps, list):
            gap_counter.update(str(gap) for gap in gaps if str(gap))

    return {
        "summary": {
            "current_profile_count": len(current_ids),
            "source_species_count": len(source_ids),
            "current_profiles_missing_from_source": sorted(current_ids - source_ids),
            "source_species_missing_from_current_profiles": sorted(source_ids - current_ids),
            "source_catalog_reference_errors": source_catalog_errors,
            "catalog_gap_candidates": [
                {"id": gap_id, "species_count": count}
                for gap_id, count in sorted(gap_counter.items())
            ],
        },
        "species": species_rows,
    }


def list_text(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def render_delta(label: str, delta: dict[str, list[str]]) -> str:
    return (
        f"- {label}: source `{list_text(delta['source'])}`; "
        f"current-only `{list_text(delta['current_only'])}`; "
        f"source-adds `{list_text(delta['source_adds'])}`"
    )


def render_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    lines = [
        "# Mushroom Profile v0 Source Audit",
        "",
        "This report is generated from the normalized v0 source and current rich profiles.",
        "It is a review aid only; it does not modify profiles, catalogs or GIS mappings.",
        "",
        "## Summary",
        "",
        f"- Current profiles: {summary['current_profile_count']}",
        f"- Source species: {summary['source_species_count']}",
        "- Current profiles missing from source: "
        + list_text(summary["current_profiles_missing_from_source"]),
        "- Source species missing from current profiles: "
        + list_text(summary["source_species_missing_from_current_profiles"]),
        f"- Source catalog reference errors: {len(summary['source_catalog_reference_errors'])}",
        "",
        "## Catalog Gap Candidates",
        "",
    ]
    if summary["catalog_gap_candidates"]:
        for item in summary["catalog_gap_candidates"]:
            lines.append(f"- `{item['id']}`: {item['species_count']} species")
    else:
        lines.append("- None")

    lines.extend(["", "## Species", ""])
    for row in audit["species"]:
        lines.extend(
            [
                f"### {row['species_id']}",
                "",
                f"- Scientific name: {row['scientific_name']}",
                f"- Status: {row['status']}",
                f"- In current profiles: {row['in_current_profiles']}",
                f"- In v0 source: {row['in_v0_source']}",
            ]
        )
        if row.get("v0_notes"):
            lines.append(f"- Notes: {row['v0_notes']}")
        gaps = row.get("catalog_gap_candidates")
        if isinstance(gaps, list) and gaps:
            lines.append("- Catalog gap candidates: " + list_text([str(gap) for gap in gaps]))
        for field, label in (
            ("host_ids", "Hosts"),
            ("forest_type_ids", "Forest/habitat types"),
            ("soil_tendency_ids", "Soil tendencies"),
            ("habitat_feature_ids", "Habitat features"),
            ("main_months", "Main months"),
            ("secondary_months", "Secondary months"),
        ):
            delta = row.get(field)
            if isinstance(delta, dict):
                lines.append(render_delta(label, delta))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--catalogs", type=Path, default=DEFAULT_CATALOGS_PATH)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_audit(
        load_json(args.profiles),
        load_json(args.catalogs),
        load_json(args.source),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_markdown(audit), encoding="utf-8")
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(audit, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    summary = audit["summary"]
    print(f"Wrote {args.report}")
    print(f"Wrote {args.json_output}")
    print(f"Current profiles: {summary['current_profile_count']}")
    print(f"Source species: {summary['source_species_count']}")
    print(
        "Current profiles missing from source: "
        + list_text(summary["current_profiles_missing_from_source"])
    )
    print(
        "Source species missing from current profiles: "
        + list_text(summary["source_species_missing_from_current_profiles"])
    )
    print(f"Source catalog reference errors: {len(summary['source_catalog_reference_errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
