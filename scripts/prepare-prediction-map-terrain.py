#!/usr/bin/env python3
"""Prepare a new local terrain index; never overwrite an existing generation."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_terrain import SCHEMA, SOIL_CRS, SOIL_ORIGIN, add_asset
from rainmapper_core import mushroom_soilgrids


def main():
    from osgeo import gdal
    gdal.UseExceptions()
    gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soil-root", required=True)
    parser.add_argument("--dem-root", required=True)
    parser.add_argument("--regional-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--include-water", action="store_true", help="Index the existing 54 water-retention layers too")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError("Index already exists; choose a new generation")
    roots = {"soil": Path(args.soil_root).resolve(), "dem": Path(args.dem_root).resolve(), "regional": Path(args.regional_root).resolve()}
    plan = json.loads((roots["soil"]/"acquisition-plan.json").read_text())
    validation = json.loads((roots["soil"]/"validation.json").read_text())
    dem_headers = json.loads((roots["dem"]/"gdal-validation.json").read_text())
    dem_files = {row["name"]: row for row in json.loads((roots["dem"]/"manifest.json").read_text())["files"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="terrain-index-", dir=output.parent) as temporary:
        candidate = Path(temporary)/"index.sqlite"
        db = sqlite3.connect(candidate)
        try:
            db.executescript(SCHEMA)
            assets = {}
            water_coverages = set(mushroom_soilgrids.required_coverage_ids()) if args.include_water else set()
            for key, row in plan["tiles"].items():
                coverage, tile = key.split("/")
                if not coverage.startswith("phh2o_") and coverage not in water_coverages:
                    continue
                kind = "ph" if coverage.startswith("phh2o_") else "water"
                tx, ty = (int(part[1:]) for part in tile.split("_"))
                relative = row["path"]
                if relative not in assets:
                    path = roots["soil"]/relative
                    ds = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY, allowed_drivers=["GTiff"])
                    gt, width, height = ds.GetGeoTransform(), ds.RasterXSize, ds.RasterYSize
                    if ds.RasterCount != 1 or ds.GetRasterBand(1).DataType != gdal.GDT_Int16 or gt[1] != 250 or gt[5] != -250:
                        raise ValueError("Invalid SoilGrids header")
                    recorded = validation["files"][relative]
                    asset_id = add_asset(db, "soil", roots["soil"], relative, kind=kind,
                        source="soilgrids_2_phh2o" if kind == "ph" else mushroom_soilgrids.SOURCE_ID,
                        crs=SOIL_CRS, transform=gt, width=width, height=height,
                        recorded_sha256=recorded["sha256"], expected_bytes=recorded["bytes"])
                    assets[relative] = (asset_id, gt, width, height)
                    ds = None
                asset_id, gt, width, height = assets[relative]
                xoff, yoff, w, h = row.get("pixel_window", [0, 0, 512, 512])
                if w != 512 or h != 512 or xoff < 0 or yoff < 0 or xoff+512 > width or yoff+512 > height:
                    raise ValueError("Invalid SoilGrids tile window")
                expected = (SOIL_ORIGIN[0]+tx*128000, SOIL_ORIGIN[1]+(ty+1)*128000)
                actual = (gt[0]+xoff*250, gt[3]-yoff*250)
                if any(abs(a-b) > 1e-6 for a,b in zip(expected, actual)):
                    raise ValueError("SoilGrids window does not match its native grid")
                db.execute("INSERT INTO tile_layers VALUES(?,?,?,?,?,?)", (coverage, tx, ty, asset_id, xoff, yoff))
            for row in dem_headers["files"]:
                recorded = dem_files[row["name"]]
                add_asset(db, "dem", roots["dem"], "source/"+row["name"], kind="dem", source="ign_mdt25",
                    crs=f"EPSG:{row['epsg']}", transform=row["transform"], width=row["size"][0], height=row["size"][1],
                    priority=10, recorded_sha256=recorded["sha256"], expected_bytes=recorded["bytes"])
            regionals = [
                ("model-elevacions-terreny-topografic-catalunya-5m-2009-2018/extracted/model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif", "dem_5m", 0),
                ("dem-andorra/extracted/rainmapper-dem-andorra-5m-elevation-m-epsg27563.tif", "dem_andorra_5m", 1),
                ("dem-france-rge-alti-5m/extracted/rainmapper-dem-france-rge-alti-5m.tif", "dem_france_rge_alti_5m", 2),
            ]
            for relative, source, priority in regionals:
                ds = gdal.OpenEx(str(roots["regional"]/relative), gdal.OF_RASTER | gdal.OF_READONLY, allowed_drivers=["GTiff"])
                srs = ds.GetSpatialRef()
                if srs is None:
                    raise ValueError("Regional DEM has no CRS")
                add_asset(db, "regional", roots["regional"], relative, kind="dem", source=source,
                    crs=srs.ExportToWkt(), transform=ds.GetGeoTransform(), width=ds.RasterXSize, height=ds.RasterYSize,
                    priority=priority)
                ds = None
            db.commit()
            counts = dict(db.execute("SELECT kind,count(*) FROM assets GROUP BY kind").fetchall())
            tile_count = db.execute("SELECT count(*) FROM tile_layers").fetchone()[0]
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Invalid terrain index")
        finally:
            db.close()
        # Publish only to a new name, atomically, never replacing another index.
        os.link(candidate, output)
    print(json.dumps({"index": str(output), "bytes": output.stat().st_size,
                      "assets": counts, "soil_tile_layers": tile_count,
                      "verification": "existing evidence, stat and SoilGrids/regional headers; no raster checksums or full hashes"}))


if __name__ == "__main__":
    main()
