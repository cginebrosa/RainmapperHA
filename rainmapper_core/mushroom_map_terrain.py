"""Indexed local terrain reads for the point-map prototype.

GDAL imports are deferred. This reader does not migrate SoilGrids contexts,
download data, hash files, interpolate pixels or calculate species predictions.
"""
from __future__ import annotations

from collections import OrderedDict
import json
import math
from pathlib import Path
import sqlite3
import threading

from rainmapper_core import mushroom_soilgrids as soilgrids
from rainmapper_core.mushroom_geography_store import SourceIdentities

PH_DEPTHS = ((0, 5), (5, 15), (15, 30))
PH_QUANTILES = ("Q0.05", "Q0.5", "Q0.95")
SOIL_CRS = "+proj=igh +datum=WGS84 +no_defs"
SOIL_ORIGIN = (-19949750, -6147500)


def local_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("invalid_local_asset")
    return path


class TerrainReader:
    """One owning thread, read-only SQLite, LRU GDAL handles, 1x1 windows."""

    def __init__(self, index: str, roots: dict[str, str], *, sources=None):
        from osgeo import gdal, osr

        self._gdal, self._osr = gdal, osr
        self._sources = sources or SourceIdentities()
        gdal.SetCacheMax(16 * 1024 * 1024)
        self._owner = threading.get_ident()
        self._roots = {key: Path(value).resolve() for key, value in roots.items()}
        self._datasets = OrderedDict()
        self._transforms = {}
        self._db = sqlite3.connect(Path(index).resolve(strict=True).as_uri() + "?mode=ro", uri=True)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA query_only=ON")
        self._db.execute("PRAGMA cache_size=-4096")
        if self._db.execute("PRAGMA user_version").fetchone()[0] != 1:
            self.close()
            raise ValueError("unsupported_terrain_index")
        self._dem_crs = [row[0] for row in self._db.execute("SELECT DISTINCT crs FROM assets WHERE kind='dem' LIMIT 17")]
        if len(self._dem_crs) > 16:
            self.close()
            raise ValueError("terrain_crs_limit")

    def close(self):
        self._datasets.clear()
        self._transforms.clear()
        self._db.close()

    def _project(self, lon, lat, crs):
        if crs not in self._transforms:
            source = self._osr.SpatialReference()
            source.ImportFromEPSG(4326)
            source.SetAxisMappingStrategy(self._osr.OAMS_TRADITIONAL_GIS_ORDER)
            target = self._osr.SpatialReference()
            if target.SetFromUserInput(crs) != 0:
                raise ValueError("invalid_terrain_crs")
            target.SetAxisMappingStrategy(self._osr.OAMS_TRADITIONAL_GIS_ORDER)
            self._transforms[crs] = self._osr.CoordinateTransformation(source, target)
        x, y, _ = self._transforms[crs].TransformPoint(lon, lat)
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("outside_projection")
        return x, y

    def _read(self, asset, col, row):
        if not (0 <= col < asset["width"] and 0 <= row < asset["height"]):
            raise ValueError("invalid_terrain_window")
        logical = self._roots[asset["root_key"]] / asset["path"]
        if self._sources.stamp(logical) != [asset["bytes"], asset["mtime_ns"]]:
            self._datasets.pop(asset["id"], None)
            raise ValueError("terrain_asset_changed")
        path = (self._sources.resolve(logical) if self._sources.portable else
                local_path(self._roots[asset["root_key"]], asset["path"]))
        if asset["id"] not in self._datasets:
            if len(self._datasets) >= 16:
                self._datasets.popitem(last=False)
            # GeoTIFF only: no VRT or remote dependencies from an indexed asset.
            ds = self._gdal.OpenEx(str(path), self._gdal.OF_RASTER | self._gdal.OF_READONLY, allowed_drivers=["GTiff"])
            if ds is None or (ds.RasterXSize, ds.RasterYSize) != (asset["width"], asset["height"]):
                raise ValueError("invalid_terrain_raster")
            if any(abs(a-b) > 1e-6 for a,b in zip(ds.GetGeoTransform(), json.loads(asset["transform"]))):
                raise ValueError("terrain_grid_changed")
            self._datasets[asset["id"]] = ds
        self._datasets.move_to_end(asset["id"])
        band = self._datasets[asset["id"]].GetRasterBand(1)
        values = band.ReadAsArray(col, row, 1, 1)
        if values is None:
            raise ValueError("terrain_read_failed")
        value = float(values[0, 0])
        if not math.isfinite(value) or value == band.GetNoDataValue():
            return None
        return value

    def _elevation(self, lat, lon):
        candidates = []
        for crs in self._dem_crs:
            x, y = self._project(lon, lat, crs)
            rows = self._db.execute(
                "SELECT a.* FROM bounds b JOIN assets a ON b.id=a.id "
                "WHERE a.kind='dem' AND a.crs=? AND b.minx<=? AND b.maxx>=? AND b.miny<=? AND b.maxy>=? LIMIT 17",
                (crs, x, x, y, y),
            ).fetchall()
            candidates.extend((asset, x, y) for asset in rows)
        if len(candidates) > 16:
            raise ValueError("terrain_candidate_limit")
        for asset, x, y in sorted(candidates, key=lambda item: (item[0]["priority"], item[0]["id"])):
            gt = json.loads(asset["transform"])
            col, row = math.floor((x-gt[0])/gt[1]), math.floor((y-gt[3])/gt[5])
            # R-tree envelopes are conservative; edges can fall outside a raster.
            if not (0 <= col < asset["width"] and 0 <= row < asset["height"]):
                continue
            value = self._read(asset, col, row)
            if value is not None:
                return {"status": "available", "value_m": round(value, 1),
                        "resolution_m": abs(gt[1]), "source_id": asset["source"]}
        return {"status": "no_data" if candidates else "not_covered"}

    def _soil_pixel(self, lat, lon):
        x, y = self._project(lon, lat, SOIL_CRS)
        col = math.floor((x-SOIL_ORIGIN[0])/250)
        # North-up rasters assign an exact horizontal edge to the pixel below.
        bottom_row = math.ceil((y-SOIL_ORIGIN[1])/250)-1
        tx, ty = col // 512, bottom_row // 512
        pixel_x, pixel_y = col % 512, 511-bottom_row % 512
        return tx, ty, pixel_x, pixel_y

    def _soil_asset(self, coverage, pixel):
        tx, ty, _, _ = pixel
        return self._db.execute(
            "SELECT a.*, t.xoff, t.yoff FROM tile_layers t JOIN assets a ON a.id=t.asset_id "
            "WHERE t.coverage=? AND t.tile_x=? AND t.tile_y=?", (coverage, tx, ty),
        ).fetchone()

    def _ph(self, lat, lon):
        pixel = self._soil_pixel(lat, lon)
        _, _, pixel_x, pixel_y = pixel
        depths = []
        for low, high in PH_DEPTHS:
            values, states = [], []
            for quantile in PH_QUANTILES:
                coverage = f"phh2o_{low}-{high}cm_{quantile}"
                asset = self._soil_asset(coverage, pixel)
                if asset is None:
                    values.append(None); states.append("not_covered"); continue
                raw = self._read(asset, asset["xoff"]+pixel_x, asset["yoff"]+pixel_y)
                if raw is None or raw == 0:
                    values.append(None); states.append("no_data")
                elif 0 < raw <= 140:
                    values.append(raw/10); states.append("available")
                else:
                    raise ValueError("invalid_ph_value")
            present = [value for value in values if value is not None]
            if present != sorted(present):
                raise ValueError("invalid_ph_quantiles")
            state = "available" if len(present) == 3 else "partial" if present else "not_covered" if all(s == "not_covered" for s in states) else "no_data"
            depths.append({"depth_cm": [low, high], "status": state,
                           "lower": values[0], "median": values[1], "upper": values[2]})
        states = [row["status"] for row in depths]
        status = "available" if all(s == "available" for s in states) else "partial" if any(s in ("available", "partial") for s in states) else "not_covered" if all(s == "not_covered" for s in states) else "no_data"
        return {"status": status, "resolution_m": 250, "source_id": "soilgrids_2_phh2o", "depths": depths}

    def _validate_point(self, lat, lon):
        if threading.get_ident() != self._owner:
            raise RuntimeError("terrain_reader_thread_mismatch")
        for value, limit in ((lat, 90), (lon, 180)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > limit:
                raise ValueError("invalid_point")

    def soil_water_context(self, lat: float, lon: float) -> dict:
        """One native cell adapted to the existing water-state input shape.

        This is not a persisted micro-area context. The existing aggregation
        validity rule applies to each property triplet; raster zero is not
        globally reclassified as NoData. No download, CLI or raster hash occurs.
        """
        self._validate_point(lat, lon)
        pixel = self._soil_pixel(lat, lon)
        tx, ty, px, py = pixel
        depths, identities = [], []
        available_groups = covered_layers = 0
        reasons = set()
        for top, bottom, label in soilgrids.DEPTHS:
            weighted, counts = {}, {}
            for stored_quantile, service_quantile in soilgrids.QUANTILES:
                values = {}
                for prop in soilgrids.PROPERTIES:
                    coverage = soilgrids.coverage_id(prop, label, service_quantile)
                    asset = self._soil_asset(coverage, pixel)
                    raw = None
                    if asset is None:
                        reasons.add("missing_cache_assets")
                    else:
                        covered_layers += 1
                        raw = self._read(asset, asset["xoff"]+px, asset["yoff"]+py)
                        identities.append((coverage, asset["path"], asset["recorded_sha256"],
                                           asset["bytes"], asset["mtime_ns"]))
                        if raw is None or not 0 < raw <= 1000:
                            reasons.add("water_retention_value_ineligible")
                    values[f"{prop}_mm_per_m"] = raw
                valid = all(value is not None and 0 < value <= 1000 for value in values.values())
                counts[stored_quantile] = int(valid)
                available_groups += int(valid)
                weighted[stored_quantile] = values if valid else {key: None for key in values}
            depths.append({"top_cm": top, "bottom_cm": bottom,
                           "valid_pixel_count": min(counts.values()),
                           "quantile_valid_pixel_counts": counts, "area_weighted": weighted})
        total_groups = len(soilgrids.DEPTHS)*len(soilgrids.QUANTILES)
        complete = available_groups == total_groups
        status = "complete" if complete else "partial" if available_groups else "no_coverage"
        context = {
            "contract_id": "point_soilgrids_water_context_v1", "status": status,
            "source": {"source_id": soilgrids.SOURCE_ID, "spatial_support": "native_cell",
                       "resolution_m": soilgrids.PIXEL_SIZE_M, "tile_id": soilgrids.tile_id(tx, ty),
                       "pixel_col": px, "pixel_row": py,
                       "asset_set_id": soilgrids.canonical_sha256(identities)},
            # As in aggregate_geometry this is minimum spatial coverage across
            # groups, not the fraction of layers that happened to be present.
            "coverage_fraction": 1.0 if complete else 0.0,
            "depths": depths,
            "quality": {"covered_layer_count": covered_layers,
                        "valid_group_count": available_groups,
                        "exclusion_reasons": sorted(reasons)},
        }
        context["context_hash"] = soilgrids.canonical_sha256(context)
        return context

    def lookup(self, lat: float, lon: float) -> dict:
        self._validate_point(lat, lon)
        result = {"status": "available", "data_mode": "geographic_sources"}
        for key, read in (("elevation", self._elevation), ("ph", self._ph)):
            try:
                result[key] = read(lat, lon)
            except (ValueError, RuntimeError, OSError, KeyError, sqlite3.Error):
                result[key] = {"status": "unavailable"}
        states = [result[key]["status"] for key in ("elevation", "ph")]
        if any(s != "available" for s in states):
            result["status"] = "partial" if any(s in ("available", "partial") for s in states) else "unavailable" if "unavailable" in states else "no_data"
        return result


SCHEMA = """
PRAGMA user_version=1;
CREATE TABLE assets(id INTEGER PRIMARY KEY, root_key TEXT, path TEXT, kind TEXT,
    source TEXT, crs TEXT, transform TEXT, width INTEGER, height INTEGER,
    bytes INTEGER, mtime_ns INTEGER, priority INTEGER, recorded_sha256 TEXT,
    UNIQUE(root_key,path));
CREATE INDEX assets_crs ON assets(kind,crs);
CREATE VIRTUAL TABLE bounds USING rtree(id,minx,maxx,miny,maxy);
CREATE TABLE tile_layers(coverage TEXT, tile_x INTEGER, tile_y INTEGER,
    asset_id INTEGER REFERENCES assets(id), xoff INTEGER, yoff INTEGER,
    PRIMARY KEY(coverage,tile_x,tile_y));
"""


def add_asset(db, root_key, root, relative, *, kind, source, crs, transform,
              width, height, priority=0, recorded_sha256=None, expected_bytes=None):
    """Preparation only: register local identity, not a full integrity audit."""
    path = local_path(Path(root), relative)
    stat = path.stat()
    if expected_bytes is not None and stat.st_size != expected_bytes:
        raise ValueError("terrain_asset_size_mismatch")
    if transform[2] != 0 or transform[4] != 0 or transform[1] <= 0 or transform[5] >= 0:
        raise ValueError("unsupported_terrain_grid")
    cursor = db.execute("INSERT INTO assets VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?)",
        (root_key, relative, kind, source, crs, json.dumps(transform), width, height,
         stat.st_size, stat.st_mtime_ns, priority, recorded_sha256))
    asset_id = cursor.lastrowid
    x, y = transform[0], transform[3]
    db.execute("INSERT INTO bounds VALUES(?,?,?,?,?)", (asset_id, x, x+width*transform[1], y+height*transform[5], y))
    return asset_id
