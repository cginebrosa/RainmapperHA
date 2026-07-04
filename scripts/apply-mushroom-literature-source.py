#!/usr/bin/env python3
"""Apply a normalized literature source to mushroom profile affinities.

The script is intentionally small and conservative. It only touches ecology
affinity rows supported by the normalized source JSON. It does not read
observations, GIS/DEM evidence, weather data or learned-model artefacts.

For the current Marc Estevez source, a listed affinity is treated as a strong
documentary signal and is written as ``relationship: "primary"``. The script
also adds a minimal ``source_ids`` provenance list so the maintenance UI can
show the source without adding a larger evidence model to profiles.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_paths


VERSIONED_PROFILES_PATH = REPO_ROOT / "mushroom-data" / "mushroom_profiles.json"
DEFAULT_PROFILES_PATH = mushroom_paths.mushroom_data_file("mushroom_profiles.json")
DEFAULT_SOURCE_PATH = (
    REPO_ROOT / "docs" / "mushrooms" / "literature" / "marc-estevez-v0-source-normalized.json"
)
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "tmp"
    / "mushroom-lab"
    / "output"
    / "reports"
    / "mushroom_literature_source_apply.md"
)

SOURCE_ID_ALIASES = {
    "marc_estevez_species_pdf_visual_review": "literature_marc_estevez",
}

SOURCE_FIELDS = {
    "host_ids": "host_affinities",
    "forest_type_ids": "forest_type_affinities",
    "soil_tendency_ids": "soil_affinities",
    "habitat_feature_ids": "habitat_feature_affinities",
}

GAP_PREFIX_FIELDS = {
    "host_": "host_affinities",
    "forest_": "forest_type_affinities",
    "soil_": "soil_affinities",
    "feature_": "habitat_feature_affinities",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def source_provenance_id(source_payload: dict[str, Any]) -> str:
    raw_source_id = str(source_payload.get("source_id", "") or "").strip()
    return SOURCE_ID_ALIASES.get(raw_source_id, raw_source_id or "literature_source")


def source_species_index(source_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    species = source_payload.get("species")
    if not isinstance(species, list):
        return {}
    return {
        str(item.get("species_id", "") or "").strip(): item
        for item in species
        if isinstance(item, dict) and str(item.get("species_id", "") or "").strip()
    }


def ensure_source_ids(item: dict[str, Any], source_id: str) -> bool:
    raw_values = item.get("source_ids")
    values = [str(value) for value in raw_values if str(value or "").strip()] if isinstance(raw_values, list) else []
    if source_id in values:
        return False
    values.append(source_id)
    item["source_ids"] = values
    return True


def affinity_ids_for_source(source_profile: dict[str, Any]) -> dict[str, set[str]]:
    ids_by_field: dict[str, set[str]] = {field: set() for field in SOURCE_FIELDS.values()}
    for source_key, profile_field in SOURCE_FIELDS.items():
        values = source_profile.get(source_key)
        if isinstance(values, list):
            ids_by_field[profile_field].update(str(value) for value in values if str(value or "").strip())
    gaps = source_profile.get("catalog_gap_candidates")
    if isinstance(gaps, list):
        for raw_gap_id in gaps:
            gap_id = str(raw_gap_id or "").strip()
            if not gap_id:
                continue
            for prefix, profile_field in GAP_PREFIX_FIELDS.items():
                if gap_id.startswith(prefix):
                    ids_by_field.setdefault(profile_field, set()).add(gap_id)
                    break
    return ids_by_field


def apply_source_to_affinity(
    affinities: list[Any],
    item_id: str,
    source_id: str,
) -> tuple[str, dict[str, Any]]:
    for item in affinities:
        if not isinstance(item, dict) or item.get("id") != item_id:
            continue
        before = deepcopy(item)
        if item.get("relationship") != "primary":
            item["relationship"] = "primary"
        item.setdefault("affinity", 0.0)
        if item.get("v0_active") is False:
            item.pop("v0_active", None)
        ensure_source_ids(item, source_id)
        return ("updated" if item != before else "unchanged", item)

    item = {
        "id": item_id,
        "relationship": "primary",
        "affinity": 0.0,
        "v0_placeholder": True,
        "source_ids": [source_id],
    }
    affinities.append(item)
    return "added", item


def apply_literature_source(
    profiles_payload: dict[str, Any],
    source_payload: dict[str, Any],
) -> dict[str, Any]:
    source_id = source_provenance_id(source_payload)
    source_by_species = source_species_index(source_payload)
    report: dict[str, Any] = {
        "source_id": source_id,
        "species_seen": 0,
        "added": [],
        "updated": [],
        "unchanged": [],
        "missing_species": [],
    }
    profiles = profiles_payload.get("species_profiles")
    if not isinstance(profiles, list):
        return report

    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        species_id = str(profile.get("species_id", "") or "").strip()
        source_profile = source_by_species.get(species_id)
        if not source_profile:
            continue
        report["species_seen"] += 1
        ecology = profile.setdefault("ecology", {})
        if not isinstance(ecology, dict):
            continue
        for field, ids in affinity_ids_for_source(source_profile).items():
            affinities = ecology.setdefault(field, [])
            if not isinstance(affinities, list):
                affinities = []
                ecology[field] = affinities
            for item_id in sorted(ids):
                action, item = apply_source_to_affinity(affinities, item_id, source_id)
                if action in {"added", "updated", "unchanged"}:
                    report[action].append(
                        {
                            "species_id": species_id,
                            "field": field,
                            "id": item_id,
                            "relationship": item.get("relationship"),
                        }
                    )

    profile_ids = {
        str(profile.get("species_id", "") or "").strip()
        for profile in profiles
        if isinstance(profile, dict)
    }
    report["missing_species"] = sorted(set(source_by_species) - profile_ids)
    return report


def render_report(report: dict[str, Any], *, applied: bool, profiles_path: Path, source_path: Path) -> str:
    timestamp = datetime.now(UTC).isoformat()
    lines = [
        "# Mushroom literature source apply report",
        "",
        f"- timestamp: `{timestamp}`",
        f"- mode: `{'apply' if applied else 'dry-run'}`",
        f"- profiles: `{profiles_path}`",
        f"- source: `{source_path}`",
        f"- source_id: `{report.get('source_id', '-')}`",
        f"- species matched: `{report.get('species_seen', 0)}`",
        f"- added affinities: `{len(report.get('added', []))}`",
        f"- updated affinities: `{len(report.get('updated', []))}`",
        f"- unchanged affinities: `{len(report.get('unchanged', []))}`",
        f"- missing source species in profiles: `{len(report.get('missing_species', []))}`",
        "",
        "## Updated",
        "",
    ]
    for item in report.get("updated", [])[:200]:
        lines.append(f"- {item['species_id']} {item['field']} {item['id']} -> {item['relationship']}")
    if len(report.get("updated", [])) > 200:
        lines.append("- ...")
    lines.extend(["", "## Added", ""])
    for item in report.get("added", [])[:200]:
        lines.append(f"- {item['species_id']} {item['field']} {item['id']} -> {item['relationship']}")
    if len(report.get("added", [])) > 200:
        lines.append("- ...")
    missing = report.get("missing_species", [])
    if missing:
        lines.extend(["", "## Missing Species", ""])
        lines.extend(f"- {species_id}" for species_id in missing)
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profiles",
        type=Path,
        default=None,
        help=(
            "Profiles file to update. Defaults to the live mushroom data path "
            "resolved by rainmapper_core.mushroom_paths."
        ),
    )
    parser.add_argument(
        "--versioned-defaults",
        action="store_true",
        help="Update the versioned seed file in mushroom-data/ instead of the live data path.",
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--apply", action="store_true", help="Write changes to the profiles file.")
    args = parser.parse_args(argv)

    profiles_path = args.profiles
    if profiles_path is None:
        profiles_path = VERSIONED_PROFILES_PATH if args.versioned_defaults else DEFAULT_PROFILES_PATH

    profiles_payload = load_json(profiles_path)
    source_payload = load_json(args.source)
    working_payload = deepcopy(profiles_payload)
    report = apply_literature_source(working_payload, source_payload)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render_report(report, applied=args.apply, profiles_path=profiles_path, source_path=args.source),
        encoding="utf-8",
    )
    if args.apply:
        write_json(profiles_path, working_payload)
    print(
        f"{'Applied' if args.apply else 'Dry-run'} literature source {report['source_id']}: "
        f"{len(report['updated'])} updated, {len(report['added'])} added, "
        f"{len(report['unchanged'])} unchanged. Report: {args.report}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
