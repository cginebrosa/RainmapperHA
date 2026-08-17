#!/usr/bin/env python3
"""Audit aligned SoilGrids water-retention clips over known-site polygons.

The input rasters must be WCS clips of the same extent/resolution for one depth
and quantile. SoilGrids WCS currently omits the CRS tag from returned GeoTIFFs;
the service-native Interrupted Goode Homolosine CRS is therefore explicit in
this audit contract. Results are written to stdout and inputs are never edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from osgeo import gdal, ogr, osr


gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()


SOILGRIDS_IGH_PROJ4 = "+proj=igh +datum=WGS84 +no_defs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--known-sites", required=True, type=Path)
    parser.add_argument("--wv0010", required=True, type=Path)
    parser.add_argument("--wv0033", required=True, type=Path)
    parser.add_argument("--wv1500", required=True, type=Path)
    parser.add_argument("--depth-label", required=True)
    parser.add_argument("--depth-thickness-m", required=True, type=float)
    parser.add_argument("--quantile", required=True)
    return parser.parse_args()


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


def same_grid(reference: Any, candidate: Any) -> bool:
    return (
        reference.RasterXSize == candidate.RasterXSize
        and reference.RasterYSize == candidate.RasterYSize
        and all(
            math.isclose(left, right, rel_tol=0.0, abs_tol=1e-9)
            for left, right in zip(
                reference.GetGeoTransform(), candidate.GetGeoTransform()
            )
        )
    )


def cell_polygon(geotransform: tuple[float, ...], row: int, col: int) -> ogr.Geometry:
    x0 = geotransform[0] + col * geotransform[1]
    y1 = geotransform[3] + row * geotransform[5]
    x1 = x0 + geotransform[1]
    y0 = y1 + geotransform[5]
    return ogr.CreateGeometryFromWkt(
        f"POLYGON (({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"
    )


def main() -> int:
    args = parse_args()
    if args.depth_thickness_m <= 0:
        raise ValueError("depth thickness must be positive")

    paths = {
        "wv0010": args.wv0010,
        "wv0033": args.wv0033,
        "wv1500": args.wv1500,
    }
    datasets = {name: gdal.Open(str(path)) for name, path in paths.items()}
    if any(dataset is None for dataset in datasets.values()):
        raise RuntimeError("Cannot open one or more SoilGrids rasters")
    reference = datasets["wv0033"]
    for name, dataset in datasets.items():
        if not same_grid(reference, dataset):
            raise ValueError(f"Raster {name} is not aligned with wv0033")
    arrays = {
        name: dataset.GetRasterBand(1).ReadAsArray()
        for name, dataset in datasets.items()
    }
    nodata = {
        name: dataset.GetRasterBand(1).GetNoDataValue()
        for name, dataset in datasets.items()
    }
    geotransform = reference.GetGeoTransform()

    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    soilgrids_srs = osr.SpatialReference()
    soilgrids_srs.ImportFromProj4(SOILGRIDS_IGH_PROJ4)
    soilgrids_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(wgs84, soilgrids_srs)

    payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    micro_areas = [
        row
        for row in payload.get("micro_areas", [])
        if isinstance(row, dict) and isinstance(row.get("geometry"), dict)
    ]
    rows: list[dict[str, Any]] = []
    for micro_area in micro_areas:
        geometry_payload = micro_area["geometry"]
        geometry = ogr.CreateGeometryFromJson(json.dumps(geometry_payload))
        if geometry is None:
            continue
        geometry.Transform(transform)
        if not geometry.IsValid():
            geometry = geometry.MakeValid()
        total_area = geometry.GetArea()
        if total_area <= 0:
            continue

        min_x, max_x, min_y, max_y = geometry.GetEnvelope()
        col_start = max(0, int(math.floor((min_x - geotransform[0]) / geotransform[1])))
        col_end = min(
            reference.RasterXSize - 1,
            int(math.floor((max_x - geotransform[0]) / geotransform[1])),
        )
        row_start = max(
            0, int(math.floor((geotransform[3] - max_y) / -geotransform[5]))
        )
        row_end = min(
            reference.RasterYSize - 1,
            int(math.floor((geotransform[3] - min_y) / -geotransform[5])),
        )

        weighted_sums = {name: 0.0 for name in arrays}
        valid_area = 0.0
        intersecting_pixels = 0
        for row in range(row_start, row_end + 1):
            for col in range(col_start, col_end + 1):
                intersection = geometry.Intersection(
                    cell_polygon(geotransform, row, col)
                )
                if intersection is None or intersection.IsEmpty():
                    continue
                area = intersection.GetArea()
                if area <= 0:
                    continue
                values = {
                    name: float(array[row, col]) for name, array in arrays.items()
                }
                is_valid = all(
                    value > 0
                    and (nodata[name] is None or not math.isclose(value, nodata[name]))
                    for name, value in values.items()
                )
                if not is_valid:
                    continue
                intersecting_pixels += 1
                valid_area += area
                for name, value in values.items():
                    weighted_sums[name] += value * area

        means = {
            name: weighted_sum / valid_area if valid_area else None
            for name, weighted_sum in weighted_sums.items()
        }
        coverage = min(1.0, max(0.0, valid_area / total_area))
        awc_33_mm = (
            (means["wv0033"] - means["wv1500"]) * args.depth_thickness_m
            if means["wv0033"] is not None and means["wv1500"] is not None
            else None
        )
        awc_10_mm = (
            (means["wv0010"] - means["wv1500"]) * args.depth_thickness_m
            if means["wv0010"] is not None and means["wv1500"] is not None
            else None
        )
        rows.append(
            {
                "micro_area_id": micro_area.get("micro_area_id"),
                "area_id": micro_area.get("area_id"),
                "name": micro_area.get("name"),
                "geometry_hash": geometry_hash(geometry_payload),
                "coverage_fraction": round(coverage, 6),
                "intersecting_valid_pixels": intersecting_pixels,
                "wv0010_mm_per_m": round(means["wv0010"], 6)
                if means["wv0010"] is not None
                else None,
                "wv0033_mm_per_m": round(means["wv0033"], 6)
                if means["wv0033"] is not None
                else None,
                "wv1500_mm_per_m": round(means["wv1500"], 6)
                if means["wv1500"] is not None
                else None,
                "available_water_33_minus_1500_mm": round(awc_33_mm, 6)
                if awc_33_mm is not None
                else None,
                "available_water_10_minus_1500_mm": round(awc_10_mm, 6)
                if awc_10_mm is not None
                else None,
            }
        )

    available_33 = [
        row["available_water_33_minus_1500_mm"]
        for row in rows
        if row["available_water_33_minus_1500_mm"] is not None
    ]
    available_10 = [
        row["available_water_10_minus_1500_mm"]
        for row in rows
        if row["available_water_10_minus_1500_mm"] is not None
    ]
    report = {
        "contract_candidate": "microarea_soilgrids_water_context_v1",
        "status": "partial_depth_quantile_audit",
        "known_sites_path": str(args.known_sites),
        "known_sites_sha256": file_hash(args.known_sites),
        "source": {
            "id": "soilgrids_2_water_retention",
            "native_crs_proj4": SOILGRIDS_IGH_PROJ4,
            "pixel_size_m": abs(geotransform[1]),
            "depth_label": args.depth_label,
            "depth_thickness_m": args.depth_thickness_m,
            "quantile": args.quantile,
            "mapped_unit": "1 mm/m (10^-3 cm3/cm3)",
            "rasters": {
                name: {"path": str(path), "sha256": file_hash(path)}
                for name, path in paths.items()
            },
        },
        "summary": {
            "micro_areas_audited": len(rows),
            "full_coverage": sum(row["coverage_fraction"] >= 0.999 for row in rows),
            "partial_coverage": sum(
                0.001 < row["coverage_fraction"] < 0.999 for row in rows
            ),
            "no_coverage": sum(row["coverage_fraction"] <= 0.001 for row in rows),
            "available_water_33_minus_1500_mm_min": round(min(available_33), 6),
            "available_water_33_minus_1500_mm_max": round(max(available_33), 6),
            "available_water_10_minus_1500_mm_min": round(min(available_10), 6),
            "available_water_10_minus_1500_mm_max": round(max(available_10), 6),
        },
        "micro_areas": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
