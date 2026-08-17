#!/usr/bin/env python3
"""Audit known-site micro-area coverage against the ICGC soil polygons.

The script is read-only. It writes its JSON report to stdout so callers can
decide whether to persist it. It requires GDAL/OGR Python bindings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from osgeo import ogr, osr


ogr.UseExceptions()


SOIL_FIELDS = (
    "CRAD_CODI",
    "CRAD_TXT",
    "PROF_CODI",
    "PROF_TXT",
    "DREN_CODI",
    "DREN_TXT",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--known-sites", required=True, type=Path)
    parser.add_argument("--soil", required=True, type=Path)
    return parser.parse_args()


def file_set_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for candidate in sorted(path.parent.glob(f"{path.stem}.*")):
        if not candidate.is_file():
            continue
        digest.update(candidate.name.encode("utf-8"))
        with candidate.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def geometry_hash(geometry: dict[str, Any]) -> str:
    canonical = json.dumps(
        geometry, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def valid_hydraulic_context(values: dict[str, str]) -> bool:
    return all(
        values.get(field) not in {"", "misc"}
        for field in ("CRAD_CODI", "PROF_CODI", "DREN_CODI")
    )


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


def main() -> int:
    args = parse_args()
    payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    micro_areas = [
        row
        for row in payload.get("micro_areas", [])
        if isinstance(row, dict) and isinstance(row.get("geometry"), dict)
    ]

    dataset = ogr.Open(str(args.soil), 0)
    if dataset is None:
        raise RuntimeError(f"Cannot open soil dataset: {args.soil}")
    layer = dataset.GetLayer(0)
    soil_srs = layer.GetSpatialRef()
    if soil_srs is None:
        raise RuntimeError("Soil layer has no spatial reference")
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    soil_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(wgs84, soil_srs)

    rows: list[dict[str, Any]] = []
    for micro_area in micro_areas:
        geometry_payload = micro_area["geometry"]
        geometry = ogr.CreateGeometryFromJson(json.dumps(geometry_payload))
        if geometry is None:
            continue
        geometry.Transform(transform)
        if not geometry.IsValid():
            geometry = geometry.MakeValid()
        micro_area_m2 = geometry.GetArea()
        if micro_area_m2 <= 0:
            continue

        layer.SetSpatialFilter(geometry)
        layer.ResetReading()
        any_coverage: ogr.Geometry | None = None
        usable_coverage: ogr.Geometry | None = None
        components: dict[tuple[str, ...], float] = {}
        feature_count = 0
        usable_feature_count = 0

        for feature in layer:
            soil_geometry = feature.GetGeometryRef()
            if soil_geometry is None or not soil_geometry.Intersects(geometry):
                continue
            intersection = soil_geometry.Intersection(geometry)
            if intersection is None or intersection.IsEmpty():
                continue
            intersection_area = intersection.GetArea()
            if intersection_area <= 0:
                continue
            values = {
                field: str(feature.GetField(field) or "") for field in SOIL_FIELDS
            }
            feature_count += 1
            any_coverage = union_geometry(any_coverage, intersection)
            hydraulic_usable = valid_hydraulic_context(values)
            key = tuple(values[field] for field in SOIL_FIELDS) + (
                "usable" if hydraulic_usable else "not_usable",
            )
            components[key] = components.get(key, 0.0) + intersection_area
            if hydraulic_usable:
                usable_feature_count += 1
                usable_coverage = union_geometry(usable_coverage, intersection)

        layer.SetSpatialFilter(None)
        any_area = any_coverage.GetArea() if any_coverage is not None else 0.0
        usable_area = usable_coverage.GetArea() if usable_coverage is not None else 0.0
        any_fraction = min(1.0, max(0.0, any_area / micro_area_m2))
        usable_fraction = min(1.0, max(0.0, usable_area / micro_area_m2))
        component_rows = []
        for key, area_m2 in sorted(components.items(), key=lambda item: -item[1]):
            values = dict(zip(SOIL_FIELDS, key[:-1]))
            hydraulic_usable = key[-1] == "usable"
            component_rows.append(
                {
                    **values,
                    "hydraulic_usable": hydraulic_usable,
                    "micro_area_fraction": round(area_m2 / micro_area_m2, 6),
                    "covered_soil_map_fraction": round(area_m2 / any_area, 6)
                    if any_area
                    else 0.0,
                }
            )

        rows.append(
            {
                "micro_area_id": micro_area.get("micro_area_id"),
                "area_id": micro_area.get("area_id"),
                "name": micro_area.get("name"),
                "geometry_hash": geometry_hash(geometry_payload),
                "micro_area_ha": round(micro_area_m2 / 10_000, 4),
                "soil_map_coverage_fraction": round(any_fraction, 6),
                "hydraulic_coverage_fraction": round(usable_fraction, 6),
                "soil_map_coverage_status": coverage_status(any_fraction),
                "hydraulic_coverage_status": coverage_status(usable_fraction),
                "intersecting_soil_features": feature_count,
                "usable_soil_features": usable_feature_count,
                "components": component_rows,
            }
        )

    total_area = sum(float(row["micro_area_ha"]) for row in rows)
    covered_area = sum(
        float(row["micro_area_ha"]) * float(row["soil_map_coverage_fraction"])
        for row in rows
    )
    usable_area = sum(
        float(row["micro_area_ha"]) * float(row["hydraulic_coverage_fraction"])
        for row in rows
    )

    def counts(field: str) -> dict[str, int]:
        return {
            status: sum(row[field] == status for row in rows)
            for status in ("full", "partial", "none")
        }

    report = {
        "contract_candidate": "microarea_soil_hydraulic_context_v1",
        "known_sites_path": str(args.known_sites),
        "known_sites_schema_version": payload.get("schema_version"),
        "soil_path": str(args.soil),
        "soil_dataset_sha256": file_set_hash(args.soil),
        "soil_layer_name": layer.GetName(),
        "soil_layer_feature_count": layer.GetFeatureCount(),
        "micro_areas_declared": len(payload.get("micro_areas", [])),
        "micro_areas_with_geometry": len(micro_areas),
        "micro_areas_audited": len(rows),
        "summary": {
            "soil_map_status_counts": counts("soil_map_coverage_status"),
            "hydraulic_status_counts": counts("hydraulic_coverage_status"),
            "micro_area_total_ha": round(total_area, 4),
            "soil_map_area_weighted_coverage_fraction": round(
                covered_area / total_area, 6
            )
            if total_area
            else 0.0,
            "hydraulic_area_weighted_coverage_fraction": round(
                usable_area / total_area, 6
            )
            if total_area
            else 0.0,
        },
        "micro_areas": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
