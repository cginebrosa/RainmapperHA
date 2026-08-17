#!/usr/bin/env python3
"""Audit vegetation and geology proxy values for known-site micro-areas.

The script is read-only and writes JSON to stdout. Intersections use complete
micro-area polygons, not their centroids, and preserve the source values plus
their area fractions. It requires the GDAL/OGR Python bindings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from osgeo import ogr, osr


ogr.UseExceptions()


VEGETATION_FIELDS = (
    "LLVA_Subst",
    "LLVA_niv2t",
    "LLVA_niv3t",
    "LLFISCAT_t",
    "LLVP_Fisio",
)
GEOLOGY_FIELDS = (
    "Codi",
    "Descripcio",
    "Codi_metamorfisme",
    "Descripcio_metamorfisme",
    "Codi_protolit",
    "Descripcio_protolit",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--known-sites", required=True, type=Path)
    parser.add_argument("--vegetation", required=True, type=Path)
    parser.add_argument("--geology", required=True, type=Path)
    parser.add_argument("--geology-layer", default="_04_unitats_geologiques_50000")
    return parser.parse_args()


def dataset_hash(path: Path) -> str:
    digest = hashlib.sha256()
    candidates = (
        sorted(path.parent.glob(f"{path.stem}.*"))
        if path.suffix.lower() == ".shp"
        else [path]
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        digest.update(candidate.name.encode("utf-8"))
        with candidate.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def geometry_hash(geometry: dict[str, Any]) -> str:
    canonical = json.dumps(
        geometry, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def union_geometry(current: ogr.Geometry | None, addition: ogr.Geometry) -> ogr.Geometry:
    if current is None:
        return addition.Clone()
    return current.Union(addition)


def coverage_status(fraction: float) -> str:
    if fraction >= 0.999:
        return "full"
    if fraction > 0.001:
        return "partial"
    return "none"


def open_layer(path: Path, layer_name: str | None = None) -> tuple[Any, Any]:
    dataset = ogr.Open(str(path), 0)
    if dataset is None:
        raise RuntimeError(f"Cannot open dataset: {path}")
    layer = dataset.GetLayerByName(layer_name) if layer_name else dataset.GetLayer(0)
    if layer is None:
        raise RuntimeError(f"Cannot open layer {layer_name!r} from {path}")
    return dataset, layer


def transformed_geometry(
    geometry_payload: dict[str, Any], target_srs: osr.SpatialReference
) -> ogr.Geometry:
    geometry = ogr.CreateGeometryFromJson(json.dumps(geometry_payload))
    if geometry is None:
        raise ValueError("Invalid GeoJSON geometry")
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geometry.Transform(osr.CoordinateTransformation(wgs84, target_srs))
    if not geometry.IsValid():
        geometry = geometry.MakeValid()
    return geometry


def intersect_layer(
    layer: Any,
    geometry: ogr.Geometry,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    micro_area_m2 = geometry.GetArea()
    layer.SetSpatialFilter(geometry)
    layer.ResetReading()
    covered: ogr.Geometry | None = None
    components: dict[tuple[str, ...], float] = {}
    feature_count = 0
    for feature in layer:
        source_geometry = feature.GetGeometryRef()
        if source_geometry is None or not source_geometry.Intersects(geometry):
            continue
        intersection = source_geometry.Intersection(geometry)
        if intersection is None or intersection.IsEmpty():
            continue
        area_m2 = intersection.GetArea()
        if area_m2 <= 0:
            continue
        values = tuple(str(feature.GetField(field) or "").strip() for field in fields)
        components[values] = components.get(values, 0.0) + area_m2
        covered = union_geometry(covered, intersection)
        feature_count += 1
    layer.SetSpatialFilter(None)
    covered_m2 = covered.GetArea() if covered is not None else 0.0
    fraction = min(1.0, max(0.0, covered_m2 / micro_area_m2))
    component_rows = []
    for values, area_m2 in sorted(components.items(), key=lambda item: -item[1]):
        component_rows.append(
            {
                **dict(zip(fields, values)),
                "micro_area_fraction": round(area_m2 / micro_area_m2, 6),
                "covered_layer_fraction": round(area_m2 / covered_m2, 6)
                if covered_m2
                else 0.0,
            }
        )
    return {
        "coverage_fraction": round(fraction, 6),
        "coverage_status": coverage_status(fraction),
        "intersecting_features": feature_count,
        "components": component_rows,
    }


def status_counts(rows: list[dict[str, Any]], section: str) -> dict[str, int]:
    return {
        status: sum(row[section]["coverage_status"] == status for row in rows)
        for status in ("full", "partial", "none")
    }


def main() -> int:
    args = parse_args()
    payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    micro_areas = [
        row
        for row in payload.get("micro_areas", [])
        if isinstance(row, dict) and isinstance(row.get("geometry"), dict)
    ]
    vegetation_dataset, vegetation_layer = open_layer(args.vegetation)
    geology_dataset, geology_layer = open_layer(args.geology, args.geology_layer)
    vegetation_srs = vegetation_layer.GetSpatialRef()
    geology_srs = geology_layer.GetSpatialRef()
    if vegetation_srs is None or geology_srs is None:
        raise RuntimeError("Proxy layer has no spatial reference")

    rows: list[dict[str, Any]] = []
    for micro_area in micro_areas:
        payload_geometry = micro_area["geometry"]
        vegetation_geometry = transformed_geometry(payload_geometry, vegetation_srs)
        geology_geometry = transformed_geometry(payload_geometry, geology_srs)
        micro_area_m2 = vegetation_geometry.GetArea()
        rows.append(
            {
                "micro_area_id": micro_area.get("micro_area_id"),
                "area_id": micro_area.get("area_id"),
                "name": micro_area.get("name"),
                "geometry_hash": geometry_hash(payload_geometry),
                "micro_area_ha": round(micro_area_m2 / 10_000, 4),
                "vegetation": intersect_layer(
                    vegetation_layer, vegetation_geometry, VEGETATION_FIELDS
                ),
                "geology": intersect_layer(geology_layer, geology_geometry, GEOLOGY_FIELDS),
            }
        )

    total_area = sum(row["micro_area_ha"] for row in rows)

    def weighted_coverage(section: str) -> float:
        if not total_area:
            return 0.0
        covered = sum(
            row["micro_area_ha"] * row[section]["coverage_fraction"] for row in rows
        )
        return round(covered / total_area, 6)

    report = {
        "contract_candidate": "microarea_gis_proxy_context_v1",
        "known_sites_path": str(args.known_sites),
        "known_sites_sha256": file_hash(args.known_sites),
        "known_sites_schema_version": payload.get("schema_version"),
        "vegetation": {
            "path": str(args.vegetation),
            "dataset_sha256": dataset_hash(args.vegetation),
            "layer_name": vegetation_layer.GetName(),
            "fields": list(VEGETATION_FIELDS),
        },
        "geology": {
            "path": str(args.geology),
            "dataset_sha256": dataset_hash(args.geology),
            "layer_name": geology_layer.GetName(),
            "fields": list(GEOLOGY_FIELDS),
        },
        "micro_areas_declared": len(payload.get("micro_areas", [])),
        "micro_areas_with_geometry": len(micro_areas),
        "micro_areas_audited": len(rows),
        "summary": {
            "vegetation_status_counts": status_counts(rows, "vegetation"),
            "geology_status_counts": status_counts(rows, "geology"),
            "micro_area_total_ha": round(total_area, 4),
            "vegetation_area_weighted_coverage_fraction": weighted_coverage(
                "vegetation"
            ),
            "geology_area_weighted_coverage_fraction": weighted_coverage("geology"),
        },
        "micro_areas": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    del geology_dataset
    del vegetation_dataset
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
