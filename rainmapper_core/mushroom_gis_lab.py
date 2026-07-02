"""GIS reconstruction helpers for mushroom observation lab work.

This module is intentionally experimental and read-only. It samples local GIS
layers for selected observation coordinates or batch mapping audits and writes a
review payload in the first persistent lab location available. The UI can show
traceable raw layer values without changing species profiles, predictor
parameters, or observation records.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VectorLayer:
    source_id: str
    label: str
    path: Path
    layer_name: str
    fields: tuple[str, ...]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_mushroom_lab_root() -> Path:
    """Return the best writable lab root for reusable mushroom reconstruction outputs."""
    configured = os.environ.get("RAINMAPPER_MUSHROOM_LAB_DIR", "").strip()
    if configured:
        return Path(configured)

    ha_share_root = Path("/share/rainmapper")
    if ha_share_root.exists():
        return ha_share_root / "mushroom-lab"

    local_share_copy = repo_root() / "docker-data"
    if local_share_copy.exists():
        return local_share_copy / "mushroom-lab"

    return repo_root() / "tmp" / "mushroom-lab"


def default_output_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_GIS_RECONSTRUCTION_PATH", "").strip()
    if configured:
        return Path(configured)
    return default_mushroom_lab_root() / "working" / "features" / "gis_observation_reconstruction.json"


def default_qgis_points_path() -> Path:
    return repo_root() / "tmp" / "mushroom-lab" / "working" / "qgis" / "selected_observations.geojson"


def host_visible_path(path: Path) -> str:
    """Return the host path for local Docker mounts when the launcher provides it."""
    configured_root = os.environ.get("RAINMAPPER_LOCAL_REPO_ROOT", "").strip()
    if not configured_root:
        return str(path)
    try:
        relative = path.relative_to(repo_root())
    except ValueError:
        return str(path)
    return str(Path(configured_root) / relative)


def gis_root() -> Path:
    return repo_root() / "mushroom-GIS"


def dem_path() -> Path:
    return (
        gis_root()
        / "model-elevacions-terreny-topografic-catalunya-5m-2009-2018"
        / "extracted"
        / "model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif"
    )


def vector_layers() -> tuple[VectorLayer, ...]:
    root = gis_root()
    return (
        VectorLayer(
            source_id="mvc50",
            label="MVC50 vegetacion",
            path=root / "MVC50mil" / "extracted" / "MVC50mil_novembre2019.shp",
            layer_name="MVC50mil_novembre2019",
            fields=(
                "LLVA",
                "LLVA_txt",
                "LLVA_niv2",
                "LLVA_niv2t",
                "LLVA_niv3t",
                "LLFISCAT",
                "LLFISCAT_t",
                "LLVA_Subst",
                "LLVP_txt",
                "LLVP_Fisio",
            ),
        ),
        VectorLayer(
            source_id="geology_50000",
            label="ICGC geologia 1:50.000",
            path=root
            / "geologia-territorial-50000-geologic-v3r0-202412"
            / "extracted"
            / "geologia-territorial-50000-geologic-v3r0-202412.gpkg",
            layer_name="_04_unitats_geologiques_50000",
            fields=(
                "Codi",
                "Descripcio",
                "Eo",
                "Era",
                "Periode",
                "Epoca",
                "Codi_metamorfisme",
                "Descripcio_metamorfisme",
                "Codi_protolit",
                "Descripcio_protolit",
            ),
        ),
    )


MAPPABLE_LAYER_FIELDS = {
    "mvc50": ("LLFISCAT_t", "LLVA_niv2t", "LLVA_Subst"),
    "geology_50000": ("Codi",),
}

MAPPING_ID_CATALOGS = {
    "mapped_host_ids": "host_taxa",
    "mapped_forest_type_ids": "forest_types",
    "mapped_habitat_feature_ids": "habitat_features",
    "mapped_lithology_ids": "lithology_types",
    "mapped_soil_tendency_ids": "soil_types",
}

GIS_V0_OUTPUT_FIELDS = {
    "mapped_host_ids": "host_ids",
    "mapped_forest_type_ids": "forest_type_ids",
    "mapped_habitat_feature_ids": "habitat_feature_ids",
    "mapped_soil_tendency_ids": "soil_tendency_ids",
}


def run_command(args: list[str], input_text: str | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def sql_identifier(name: str) -> str:
    """Return a SQLite identifier quoted only when the layer name needs it."""
    safe = name.replace('"', '""')
    if safe.replace("_", "").isalnum():
        return safe
    return f'"{safe}"'


def transform_wgs84_to_utm31(lon: float, lat: float) -> tuple[float, float]:
    result = run_command(
        ["gdaltransform", "-s_srs", "EPSG:4326", "-t_srs", "EPSG:25831"],
        input_text=f"{lon} {lat}\n",
        timeout=20,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gdaltransform failed")
    parts = result.stdout.strip().split()
    if len(parts) < 2:
        raise RuntimeError("gdaltransform did not return projected coordinates")
    return float(parts[0]), float(parts[1])


def first_vector_feature(layer: VectorLayer, x: float, y: float) -> dict[str, Any]:
    if not layer.path.exists():
        return {"status": "missing_layer", "source": str(layer.path), "properties": {}}
    result = run_command(
        [
            "ogrinfo",
            "-json",
            "-features",
            "-geom=NO",
            "-spat",
            str(x),
            str(y),
            str(x),
            str(y),
            str(layer.path),
            layer.layer_name,
        ],
        timeout=60,
    )
    if result.returncode != 0:
        return {
            "status": "query_error",
            "source": str(layer.path),
            "error": (result.stderr or result.stdout).strip(),
            "properties": {},
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "status": "invalid_json",
            "source": str(layer.path),
            "error": str(exc),
            "properties": {},
        }
    layers = payload.get("layers") if isinstance(payload, dict) else None
    first_layer = layers[0] if isinstance(layers, list) and layers else {}
    features = first_layer.get("features") if isinstance(first_layer, dict) else None
    if not isinstance(features, list) or not features:
        return {
            "status": "no_coverage_at_point",
            "source": str(layer.path),
            "message": "The layer returned no feature for this exact point.",
            "properties": {},
        }
    properties = features[0].get("properties") if isinstance(features[0], dict) else {}
    properties = properties if isinstance(properties, dict) else {}
    selected = {field: properties.get(field) for field in layer.fields if properties.get(field) not in ("", None)}
    return {
        "status": "ok",
        "source": str(layer.path),
        "fid": features[0].get("fid") if isinstance(features[0], dict) else None,
        "properties": selected,
    }


def catalog_ids_by_group(catalogs_payload: dict[str, Any] | None) -> dict[str, set[str]]:
    catalogs = catalogs_payload.get("catalogs") if isinstance(catalogs_payload, dict) else None
    if not isinstance(catalogs, dict):
        return {}
    ids_by_group: dict[str, set[str]] = {}
    for group, entries in catalogs.items():
        if not isinstance(entries, list):
            continue
        ids_by_group[str(group)] = {
            str(entry.get("id"))
            for entry in entries
            if isinstance(entry, dict) and entry.get("id") not in (None, "")
        }
    return ids_by_group


def normalized_mapping_key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def exact_mapping_lookup(gis_payload: dict[str, Any] | None) -> dict[tuple[str, str, str], dict[str, Any]]:
    mappings = gis_payload.get("exact_value_mappings") if isinstance(gis_payload, dict) else None
    if not isinstance(mappings, list):
        return {}
    lookup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        source_id = str(mapping.get("source_id", "") or "")
        field = str(mapping.get("field", "") or "")
        raw_value = mapping.get("raw_value")
        if not source_id or not field or raw_value in (None, ""):
            continue
        lookup[(source_id, field, normalized_mapping_key(raw_value))] = mapping
    return lookup


def exact_mapping_key_set(gis_payload: dict[str, Any] | None) -> set[tuple[str, str, str]]:
    """Return normalized keys for existing exact mappings."""
    return set(exact_mapping_lookup(gis_payload))


def valid_catalog_ids(mapping: dict[str, Any], ids_by_catalog: dict[str, set[str]]) -> tuple[dict[str, list[str]], list[str]]:
    valid: dict[str, list[str]] = {}
    invalid: list[str] = []
    for output_field, catalog_group in MAPPING_ID_CATALOGS.items():
        raw_ids = mapping.get(output_field)
        if raw_ids is None:
            continue
        if not isinstance(raw_ids, list):
            invalid.append(f"{output_field}: expected list")
            continue
        accepted: list[str] = []
        catalog_ids = ids_by_catalog.get(catalog_group, set())
        for item in raw_ids:
            item_id = str(item)
            if item_id in catalog_ids:
                accepted.append(item_id)
            else:
                invalid.append(f"{output_field}: {item_id} not found in {catalog_group}")
        if accepted:
            valid[output_field] = accepted
    return valid, invalid


def _text_matches_pattern(text: str, pattern: object) -> bool:
    normalized_pattern = str(pattern or "").strip().casefold()
    return bool(normalized_pattern and normalized_pattern in text)


def _rule_match_text(rule: dict[str, Any], properties: dict[str, Any], raw_field: str) -> str:
    fields = rule.get("match_fields")
    if not isinstance(fields, list) or not fields:
        fields = ["raw_value"]
    values = []
    for field in fields:
        key = str(field or "")
        if key == "raw_value":
            values.append(properties.get(raw_field))
        else:
            values.append(properties.get(key))
    return " | ".join(str(value or "").casefold() for value in values)


def _rule_matches(rule: dict[str, Any], properties: dict[str, Any], raw_field: str) -> bool:
    raw_values = rule.get("raw_values")
    if isinstance(raw_values, list):
        raw_value = normalized_mapping_key(properties.get(raw_field))
        normalized_values = {normalized_mapping_key(item) for item in raw_values if item not in (None, "")}
        if raw_value in normalized_values:
            return True
    patterns = rule.get("source_patterns")
    if isinstance(patterns, list):
        match_text = _rule_match_text(rule, properties, raw_field)
        return any(_text_matches_pattern(match_text, pattern) for pattern in patterns)
    return False


def _candidate_rules_from_batch_rule(
    rule: dict[str, Any],
    gis_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    source_section = str(rule.get("source_section", "") or "")
    if not source_section:
        return [rule]
    section_rules = gis_payload.get(source_section) if isinstance(gis_payload, dict) else None
    if not isinstance(section_rules, list):
        return []
    derived_rules: list[dict[str, Any]] = []
    for section_rule in section_rules:
        if not isinstance(section_rule, dict):
            continue
        derived = dict(section_rule)
        derived.setdefault("match_fields", rule.get("match_fields", ["raw_value"]))
        derived.setdefault("suggestion_source", source_section)
        derived.setdefault("suggestion_notes", rule.get("notes", "Review-only suggestion from declarative GIS mapping rules."))
        derived.setdefault("auto_accept_confidences", rule.get("auto_accept_confidences", []))
        derived_rules.append(derived)
    return derived_rules


def _suggested_review_status(rule: dict[str, Any], confidence: str) -> str:
    """Return the review status declared for a suggested mapping."""
    explicit_status = str(rule.get("suggested_review_status", "") or "")
    if explicit_status in {"accepted", "pending_review", "ignored"}:
        return explicit_status
    auto_accept_confidences = rule.get("auto_accept_confidences")
    if isinstance(auto_accept_confidences, list) and confidence in {str(item) for item in auto_accept_confidences}:
        return "accepted"
    return "pending_review"


def suggested_batch_mapping(
    source_id: str,
    field: str,
    properties: dict[str, Any],
    gis_payload: dict[str, Any] | None,
    catalogs_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return review-only suggestions from declarative batch rules."""
    batch_rules = gis_payload.get("batch_suggestion_rules") if isinstance(gis_payload, dict) else None
    if not isinstance(batch_rules, list):
        return {}

    ids_by_catalog = catalog_ids_by_group(catalogs_payload)
    selected_mapping: dict[str, list[str]] = {field_name: [] for field_name in MAPPING_ID_CATALOGS}
    confidences: list[str] = []
    review_statuses: list[str] = []
    auto_accept_confidences: list[str] = []
    suggestion_sources: list[str] = []
    suggestion_notes: list[str] = []
    invalid_references: list[str] = []
    matched_count = 0

    for batch_rule in batch_rules:
        if not isinstance(batch_rule, dict):
            continue
        if str(batch_rule.get("source_id", "") or "") != source_id or str(batch_rule.get("field", "") or "") != field:
            continue
        for rule in _candidate_rules_from_batch_rule(batch_rule, gis_payload):
            if not _rule_matches(rule, properties, field):
                continue
            matched_count += 1
            confidence = str(rule.get("confidence", "") or batch_rule.get("confidence", "") or "medium")
            confidences.append(confidence)
            review_statuses.append(_suggested_review_status(rule, confidence))
            raw_auto_accept_confidences = rule.get("auto_accept_confidences")
            if isinstance(raw_auto_accept_confidences, list):
                for item in raw_auto_accept_confidences:
                    item_value = str(item)
                    if item_value and item_value not in auto_accept_confidences:
                        auto_accept_confidences.append(item_value)
            source = str(rule.get("suggestion_source", "") or batch_rule.get("rule_id", "") or batch_rule.get("source_section", "") or "batch_suggestion_rules")
            if source and source not in suggestion_sources:
                suggestion_sources.append(source)
            notes = str(rule.get("suggestion_notes", "") or rule.get("notes", "") or batch_rule.get("notes", "") or "")
            if notes and notes not in suggestion_notes:
                suggestion_notes.append(notes)
            valid_ids, invalid_ids = valid_catalog_ids(rule, ids_by_catalog)
            invalid_references.extend(invalid_ids)
            for output_field, item_ids in valid_ids.items():
                for item_id in item_ids:
                    if item_id not in selected_mapping[output_field]:
                        selected_mapping[output_field].append(item_id)

    selected_mapping = {field_name: item_ids for field_name, item_ids in selected_mapping.items() if item_ids}
    if not selected_mapping:
        return {}
    confidence_rank = {"low": 0, "medium": 1, "high": 2}
    confidence = min(confidences, key=lambda item: confidence_rank.get(item, 1)) if confidences else "medium"
    suggestion: dict[str, Any] = {
        "suggested_confidence": confidence,
        "suggested_review_status": "pending_review" if "pending_review" in review_statuses else "accepted",
        "suggestion_source": ", ".join(suggestion_sources) or "batch_suggestion_rules",
        "suggested_rule_count": str(matched_count),
        **{f"suggested_{field_name}": item_ids for field_name, item_ids in selected_mapping.items()},
    }
    auto_accept_label = ", ".join(auto_accept_confidences) if auto_accept_confidences else "none"
    if suggestion["suggested_review_status"] == "accepted":
        status_note = f"Auto-accepted because the matched rule confidence is {confidence} and this rule allows auto-accept for: {auto_accept_label}."
    else:
        status_note = f"Pending review because the matched rule confidence is {confidence}; this rule only auto-accepts: {auto_accept_label}."
    suggestion["suggestion_notes"] = status_note
    if invalid_references:
        suggestion["suggestion_invalid_references"] = "; ".join(invalid_references)
    return suggestion


def unique_vector_values_for_field(layer: VectorLayer, field: str) -> list[dict[str, Any]]:
    """Return unique non-empty raw values for a vector field with review context.

    The query is attribute-only and does not load geometries. It is used by the
    batch GIS mapping audit to populate the same candidate queue that point-based
    observation reconstruction uses, without writing mappings.
    """
    if not layer.path.exists():
        raise FileNotFoundError(layer.path)
    table = sql_identifier(layer.layer_name)
    if layer.source_id == "geology_50000" and field == "Codi":
        sql = (
            "SELECT Codi AS raw_value, MIN(Descripcio) AS Descripcio, "
            "MIN(Descripcio_metamorfisme) AS Descripcio_metamorfisme, "
            "MIN(Codi_protolit) AS Codi_protolit, "
            "MIN(Descripcio_protolit) AS Descripcio_protolit, "
            f"COUNT(*) AS feature_count FROM {table} "
            "WHERE Codi IS NOT NULL AND LENGTH(TRIM(Codi)) > 0 GROUP BY Codi"
        )
    else:
        sql = (
            f"SELECT {field} AS raw_value, COUNT(*) AS feature_count FROM {table} "
            f"WHERE {field} IS NOT NULL AND LENGTH(TRIM({field})) > 0 GROUP BY {field}"
        )
    result = run_command(
        ["ogrinfo", "-json", "-features", "-dialect", "SQLite", "-sql", sql, str(layer.path)],
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ogrinfo returned invalid JSON for {layer.source_id}.{field}: {exc}") from exc
    layers = payload.get("layers") if isinstance(payload, dict) else None
    features = layers[0].get("features") if isinstance(layers, list) and layers else None
    if not isinstance(features, list):
        return []
    rows: list[dict[str, Any]] = []
    for feature in features:
        properties = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(properties, dict):
            continue
        raw_value = properties.get("raw_value")
        if raw_value in (None, ""):
            continue
        rows.append(properties)
    return rows


def exact_mapping_candidate_context(source_id: str, field: str, row: dict[str, Any]) -> dict[str, Any]:
    """Return review context for a unique batch row using point-sampling policy."""
    properties = dict(row)
    raw_value = properties.pop("raw_value", "")
    properties[field] = raw_value
    return mapping_context(source_id, field, properties)


def build_batch_unmapped_candidates(
    gis_payload: dict[str, Any] | None,
    catalogs_payload: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build candidate mappings from every unique value in configured GIS layers.

    Existing exact mappings are skipped. Returned candidates are review inputs
    only; they do not alter `mushroom_gis_mappings.json` and do not emit
    computable IDs until a reviewer stores them as accepted exact mappings.
    """
    existing_keys = exact_mapping_key_set(gis_payload)
    candidates: list[dict[str, Any]] = []
    field_summaries: list[dict[str, Any]] = []
    for layer in vector_layers():
        for field in MAPPABLE_LAYER_FIELDS.get(layer.source_id, ()):
            field_started = time.monotonic()
            unique_rows = unique_vector_values_for_field(layer, field)
            field_total = 0
            field_existing = 0
            field_candidates = 0
            field_suggested = 0
            for row in unique_rows:
                raw_value = str(row.get("raw_value", "") or "")
                if not raw_value:
                    continue
                field_total += 1
                key = (layer.source_id, field, normalized_mapping_key(raw_value))
                if key in existing_keys:
                    field_existing += 1
                    continue
                item: dict[str, Any] = {
                    "source_id": layer.source_id,
                    "field": field,
                    "raw_value": raw_value,
                }
                feature_count = row.get("feature_count")
                if feature_count not in (None, ""):
                    item["feature_count"] = str(feature_count)
                item.update(exact_mapping_candidate_context(layer.source_id, field, row))
                suggestion_properties = dict(row)
                suggestion_properties[field] = raw_value
                suggestion = suggested_batch_mapping(layer.source_id, field, suggestion_properties, gis_payload, catalogs_payload)
                if suggestion:
                    field_suggested += 1
                    item.update(suggestion)
                candidates.append(item)
                field_candidates += 1
            field_summaries.append(
                {
                    "source_id": layer.source_id,
                    "field": field,
                    "unique_values": field_total,
                    "existing_exact_mappings": field_existing,
                    "candidate_values": field_candidates,
                    "suggested_values": field_suggested,
                    "duration_seconds": round(time.monotonic() - field_started, 3),
                }
            )
    candidates.sort(key=lambda item: (str(item.get("source_id", "")), str(item.get("field", "")), str(item.get("raw_value", ""))))
    return candidates, field_summaries


def mapping_context(source_id: str, field: str, properties: dict[str, Any]) -> dict[str, str]:
    """Return human review context for a raw GIS value without changing its key."""
    if source_id == "geology_50000" and field == "Codi":
        description = str(properties.get("Descripcio", "") or "").strip()
        if description:
            return {"description": description}
    return {}


def apply_exact_layer_mappings(
    source_id: str,
    layer_result: dict[str, Any],
    gis_payload: dict[str, Any] | None,
    catalogs_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    properties = layer_result.get("properties")
    if layer_result.get("status") != "ok" or not isinstance(properties, dict):
        return {"status": "not_applicable", "mapped_values": [], "ignored_values": [], "unmapped_values": []}

    mappable_fields = MAPPABLE_LAYER_FIELDS.get(source_id, ())
    if not mappable_fields:
        return {"status": "not_applicable", "mapped_values": [], "ignored_values": [], "unmapped_values": []}

    lookup = exact_mapping_lookup(gis_payload)
    ids_by_catalog = catalog_ids_by_group(catalogs_payload)
    mapped_values: list[dict[str, Any]] = []
    pending_values: list[dict[str, Any]] = []
    ignored_values: list[dict[str, Any]] = []
    unmapped_values: list[dict[str, str]] = []
    invalid_references: list[str] = []
    aggregate: dict[str, list[str]] = {field: [] for field in MAPPING_ID_CATALOGS}

    for field in mappable_fields:
        value = properties.get(field)
        if value in (None, ""):
            continue
        mapping = lookup.get((source_id, field, normalized_mapping_key(value)))
        context = mapping_context(source_id, field, properties)
        if not mapping:
            unmapped_item = {
                "source_id": source_id,
                "field": field,
                "raw_value": str(value),
            }
            unmapped_item.update(context)
            unmapped_item.update(suggested_batch_mapping(source_id, field, properties, gis_payload, catalogs_payload))
            unmapped_values.append(unmapped_item)
            continue
        review_status = str(mapping.get("review_status", "") or "accepted")
        if review_status == "ignored":
            ignored_item = {
                "source_id": source_id,
                "field": field,
                "raw_value": str(value),
                "confidence": mapping.get("confidence", ""),
                "review_status": review_status,
            }
            ignored_item.update(context)
            ignored_values.append(ignored_item)
            continue
        mapped_ids, invalid_ids = valid_catalog_ids(mapping, ids_by_catalog)
        invalid_references.extend(invalid_ids)
        if review_status == "pending_review":
            pending_item = {
                "source_id": source_id,
                "field": field,
                "raw_value": str(value),
                "confidence": mapping.get("confidence", ""),
                "review_status": review_status,
                **mapped_ids,
            }
            pending_item.update(context)
            pending_values.append(pending_item)
            continue
        for output_field, item_ids in mapped_ids.items():
            for item_id in item_ids:
                if item_id not in aggregate[output_field]:
                    aggregate[output_field].append(item_id)
        mapped_item = {
            "source_id": source_id,
            "field": field,
            "raw_value": str(value),
            "confidence": mapping.get("confidence", ""),
            "review_status": review_status,
            **mapped_ids,
        }
        mapped_item.update(context)
        mapped_values.append(mapped_item)

    mapped_count = len(mapped_values)
    pending_count = len(pending_values)
    ignored_count = len(ignored_values)
    unmapped_count = len(unmapped_values)
    if invalid_references:
        status = "invalid_mapping"
    elif mapped_count and unmapped_count:
        status = "partial"
    elif mapped_count and pending_count:
        status = "partial"
    elif mapped_count:
        status = "mapped"
    elif pending_count and unmapped_count:
        status = "partial"
    elif pending_count:
        status = "pending_review"
    elif ignored_count and unmapped_count:
        status = "partial"
    elif ignored_count:
        status = "ignored"
    elif unmapped_count:
        status = "unmapped"
    else:
        status = "not_applicable"

    return {
        "status": status,
        "mapped_values": mapped_values,
        "pending_values": pending_values,
        "ignored_values": ignored_values,
        "unmapped_values": unmapped_values,
        "invalid_references": invalid_references,
        **{field: ids for field, ids in aggregate.items() if ids},
    }


def append_unique(target: list[str], values: object) -> None:
    """Append string IDs while preserving first-seen order."""
    if not isinstance(values, list):
        return
    for value in values:
        item = str(value or "").strip()
        if item and item not in target:
            target.append(item)


def build_gis_context_v0(reconstruction: dict[str, Any]) -> dict[str, Any]:
    """Project a rich GIS reconstruction into the minimal predictor-v0 context.

    This adapter does not query GIS layers. It only reads the traceable
    reconstruction payload and emits broad ecological signals that the v0
    predictor can consume without depending on enriched/debug fields.
    """
    context: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "mushroom_gis_context_v0",
        "host_ids": [],
        "forest_type_ids": [],
        "soil_tendency_ids": [],
        "habitat_feature_ids": [],
        "evidence": {
            "source_layers": [],
            "mapped_source_layers": [],
            "pending_source_layers": [],
            "unmapped_source_layers": [],
            "invalid_source_layers": [],
            "gaps": list(reconstruction.get("gaps", [])) if isinstance(reconstruction.get("gaps"), list) else [],
            "has_pending_values": False,
            "has_unmapped_values": False,
            "has_invalid_references": False,
        },
    }
    layers = reconstruction.get("layers")
    if not isinstance(layers, dict):
        return context

    evidence = context["evidence"]
    for source_id, layer_result in layers.items():
        if source_id == "dem_5m" or not isinstance(layer_result, dict):
            continue
        str_source_id = str(source_id)
        evidence["source_layers"].append(str_source_id)
        mapped = layer_result.get("mapped")
        if not isinstance(mapped, dict):
            continue
        status = str(mapped.get("status", "") or "")
        if status in {"mapped", "partial"}:
            evidence["mapped_source_layers"].append(str_source_id)
        if status in {"pending_review", "partial"} and mapped.get("pending_values"):
            evidence["pending_source_layers"].append(str_source_id)
            evidence["has_pending_values"] = True
        if status in {"unmapped", "partial"} and mapped.get("unmapped_values"):
            evidence["unmapped_source_layers"].append(str_source_id)
            evidence["has_unmapped_values"] = True
        if status == "invalid_mapping" or mapped.get("invalid_references"):
            evidence["invalid_source_layers"].append(str_source_id)
            evidence["has_invalid_references"] = True
        for source_field, target_field in GIS_V0_OUTPUT_FIELDS.items():
            append_unique(context[target_field], mapped.get(source_field))

    dem = layers.get("dem_5m")
    if isinstance(dem, dict) and dem.get("status") == "ok":
        try:
            context["altitude_m"] = float(dem["elevation_m"])
            context["altitude_source"] = "dem_5m"
        except (KeyError, TypeError, ValueError):
            pass
    return context


def sample_dem(lon: float, lat: float, observed_altitude: object) -> dict[str, Any]:
    path = dem_path()
    if not path.exists():
        return {"status": "missing_layer", "source": str(path)}
    result = run_command(["gdallocationinfo", "-wgs84", "-valonly", str(path), str(lon), str(lat)], timeout=30)
    if result.returncode != 0:
        return {"status": "query_error", "source": str(path), "error": result.stderr.strip()}
    raw = result.stdout.strip()
    try:
        elevation = float(raw)
    except ValueError:
        return {"status": "no_value", "source": str(path), "raw": raw}
    if math.isclose(elevation, -9999.0):
        return {"status": "no_data", "source": str(path), "elevation_m": elevation}
    observed_value = None
    if isinstance(observed_altitude, dict):
        try:
            observed_value = float(observed_altitude.get("meters"))
        except (TypeError, ValueError):
            observed_value = None
    payload: dict[str, Any] = {
        "status": "ok",
        "source": str(path),
        "elevation_m": round(elevation, 2),
    }
    if observed_value is not None:
        payload["observed_altitude_m"] = observed_value
        payload["delta_observed_vs_dem_m"] = round(observed_value - elevation, 2)
    return payload


def observation_location(row: dict[str, object]) -> tuple[float, float] | None:
    location = row.get("location")
    if not isinstance(location, dict):
        return None
    try:
        lat = float(location.get("lat"))
        lon = float(location.get("lon"))
    except (TypeError, ValueError):
        return None
    return lat, lon


def reconstruct_observation(
    row: dict[str, object],
    gis_payload: dict[str, Any] | None = None,
    catalogs_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observation_id = str(row.get("observation_id", "") or "")
    location = observation_location(row)
    base: dict[str, Any] = {
        "observation_id": observation_id,
        "species_id": row.get("species_id", ""),
        "observed_at": row.get("observed_at", ""),
        "flush_abundance": row.get("flush_abundance", ""),
        "location_redacted": True,
        "layers": {},
        "status": "pending",
        "gaps": [],
    }
    if location is None:
        base["status"] = "skipped"
        base["gaps"].append("missing_coordinates")
        return base
    lat, lon = location
    base["location"] = {
        "lat": round(lat, 7),
        "lon": round(lon, 7),
        "source": "mushroom_observations",
    }
    base["location_redacted"] = False
    try:
        x, y = transform_wgs84_to_utm31(lon, lat)
    except Exception as exc:
        base["status"] = "error"
        base["gaps"].append("coordinate_transform_error")
        base["error"] = str(exc)
        return base
    for layer in vector_layers():
        layer_result = first_vector_feature(layer, x, y)
        layer_result["mapped"] = apply_exact_layer_mappings(
            layer.source_id,
            layer_result,
            gis_payload,
            catalogs_payload,
        )
        base["layers"][layer.source_id] = layer_result
    base["layers"]["dem_5m"] = sample_dem(lon, lat, row.get("altitude"))
    gaps = [
        source_id
        for source_id, layer_result in base["layers"].items()
        if isinstance(layer_result, dict) and layer_result.get("status") != "ok"
    ]
    base["gaps"] = gaps
    base["status"] = "complete_with_gaps" if gaps else "complete"
    base["gis_context_v0"] = build_gis_context_v0(base)
    return base


def reconstruct_observations(
    observations: list[dict[str, object]],
    observation_ids: list[str],
    output_path: Path | None = None,
    gis_payload: dict[str, Any] | None = None,
    catalogs_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_ids = [item for item in observation_ids if item]
    selected_set = set(selected_ids)
    rows = [row for row in observations if str(row.get("observation_id", "")) in selected_set]
    results = [reconstruct_observation(row, gis_payload=gis_payload, catalogs_payload=catalogs_payload) for row in rows]
    unmapped_candidates = collect_unmapped_candidates(results)
    qgis_points_path = write_qgis_points(rows)
    payload: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "mushroom_observation_gis_reconstruction",
        "generated_at": datetime.now(UTC).isoformat(),
        "selected_observation_ids": selected_ids,
        "result_count": len(results),
        "coordinate_policy": "Coordinates are read locally but not written to this review payload.",
        "qgis_points_path": str(qgis_points_path),
        "qgis_points_host_path": host_visible_path(qgis_points_path),
        "qgis_points_note": "Local-only GeoJSON with selected observation coordinates for visual GIS review.",
        "mapping_policy": "Raw GIS values are preserved. Exact mappings are applied from mushroom_gis_mappings.json and only emit IDs present in mushroom_reference_catalogs.json.",
        "unmapped_candidates": unmapped_candidates,
        "results": results,
    }
    target = output_path or default_output_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def reconstruct_all_gis_mapping_candidates(
    output_path: Path | None = None,
    gis_payload: dict[str, Any] | None = None,
    catalogs_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a batch GIS mapping reconstruction for all configured layer values."""
    started = time.monotonic()
    candidates, field_summaries = build_batch_unmapped_candidates(gis_payload, catalogs_payload)
    duration_seconds = round(time.monotonic() - started, 3)
    payload: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "mushroom_gis_mapping_batch_reconstruction",
        "generated_at": datetime.now(UTC).isoformat(),
        "duration_seconds": duration_seconds,
        "result_count": 0,
        "coordinate_policy": "Batch reconstruction reads layer attributes only; no observation coordinates are used.",
        "mapping_policy": "Existing exact mappings are skipped. New values are emitted as review candidates; suggestions from text patterns are not computable until saved as accepted exact mappings.",
        "field_summaries": field_summaries,
        "unmapped_candidates": candidates,
        "results": [],
    }
    target = output_path or default_output_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def collect_unmapped_candidates(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Collect unique source/field/raw GIS values that need human mapping review."""
    seen: set[tuple[str, str, str]] = set()
    candidates: list[dict[str, str]] = []
    for result in results:
        layers = result.get("layers")
        if not isinstance(layers, dict):
            continue
        for layer_result in layers.values():
            if not isinstance(layer_result, dict):
                continue
            mapped = layer_result.get("mapped")
            if not isinstance(mapped, dict):
                continue
            unmapped_values = mapped.get("unmapped_values")
            if not isinstance(unmapped_values, list):
                continue
            for item in unmapped_values:
                if not isinstance(item, dict):
                    continue
                source_id = str(item.get("source_id", "") or "")
                field = str(item.get("field", "") or "")
                raw_value = str(item.get("raw_value", "") or "")
                key = (source_id, field, raw_value)
                if not source_id or not field or not raw_value or key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "source_id": source_id,
                        "field": field,
                        "raw_value": raw_value,
                        **{
                            key: value
                            for key, value in item.items()
                            if key not in {"source_id", "field", "raw_value"} and value not in (None, "")
                        },
                    }
                )
    return candidates


def write_qgis_points(observations: list[dict[str, object]], path: Path | None = None) -> Path:
    """Write selected observation points for local visual inspection in QGIS."""
    target = path or default_qgis_points_path()
    features = []
    for row in observations:
        location = observation_location(row)
        if location is None:
            continue
        lat, lon = location
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "observation_id": row.get("observation_id", ""),
                    "species_id": row.get("species_id", ""),
                    "observed_at": row.get("observed_at", ""),
                    "flush_abundance": row.get("flush_abundance", ""),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
            }
        )
    payload = {
        "type": "FeatureCollection",
        "name": "selected_mushroom_observations",
        "crs": {
            "type": "name",
            "properties": {"name": "EPSG:4326"},
        },
        "features": features,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def load_latest_reconstruction(path: Path | None = None) -> dict[str, Any] | None:
    target = path or default_output_path()
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
