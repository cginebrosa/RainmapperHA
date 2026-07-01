"""Local GIS reconstruction helpers for mushroom observation lab work.

This module is intentionally experimental and read-only. It samples local GIS
layers for selected observation coordinates and writes a review payload under
`tmp/` so the UI can show traceable raw layer values without changing species
profiles, predictor parameters, or observation records.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
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


def default_output_path() -> Path:
    return repo_root() / "tmp" / "mushroom-lab" / "working" / "features" / "gis_observation_reconstruction.json"


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


def run_command(args: list[str], input_text: str | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


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
                            key: str(value)
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
