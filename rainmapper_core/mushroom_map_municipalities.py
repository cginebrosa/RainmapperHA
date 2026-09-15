"""Read-only point lookup in a prepared municipal GeoPackage.

Requires GDAL Python bindings with GEOS in the executing environment. Nothing
downloads, converts or hashes data here. One reader is reused across queries.
"""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import math
from pathlib import Path
import sqlite3
import threading


class MunicipalityReader:
    """R-tree candidates followed by exact geometry; never nearest settlement."""

    def __init__(self, path: str, *, edition: str):
        from osgeo import ogr

        if ogr.GetGEOSVersionMajor() < 3:
            raise RuntimeError("municipalities_geos_required")
        self._ogr = ogr
        self._lock = threading.Lock()
        self._cache = OrderedDict()
        self._edition = edition
        source = Path(path).resolve(strict=True)
        self._db = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, check_same_thread=False)
        self._db.execute("PRAGMA query_only=ON")
        self._db.execute("PRAGMA cache_size=-2048")
        self._dataset = ogr.Open(str(source), 0)
        self._layer = self._dataset.GetLayerByName("municipalities") if self._dataset else None
        row = self._db.execute(
            "SELECT srs_id FROM gpkg_geometry_columns WHERE table_name='municipalities' AND column_name='geom'"
        ).fetchone()
        if self._layer is None or row != (4326,):
            self.close()
            raise ValueError("invalid_municipalities_dataset")
        # Verify the index and required schema without scanning the country.
        self._db.execute("SELECT id FROM rtree_municipalities_geom LIMIT 0")
        self._db.execute("SELECT fid, name, national_code, geom FROM municipalities LIMIT 0")

    def close(self):
        with self._lock:
            self._cache.clear()
            self._layer = None
            self._dataset = None
            self._db.close()

    def lookup(self, lat: float, lon: float) -> dict:
        for value, limit in ((lat, 90), (lon, 180)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > limit:
                raise ValueError("invalid_point")
        key = (lat, lon)  # No rounding: even adjacent points can cross a boundary.
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return deepcopy(self._cache[key])
            result = self._lookup(lat, lon)
            self._cache[key] = result
            if len(self._cache) > 128:
                self._cache.popitem(last=False)
            return deepcopy(result)

    def _lookup(self, lat, lon):
        result = {"status": "not_covered", "source": "IGN", "edition": self._edition}
        candidates = self._db.execute(
            "SELECT m.fid, m.name, m.national_code, length(m.geom) "
            "FROM rtree_municipalities_geom r JOIN municipalities m ON m.fid=r.id "
            "WHERE r.minx<=? AND r.maxx>=? AND r.miny<=? AND r.maxy>=? LIMIT 65",
            (lon, lon, lat, lat),
        ).fetchall()
        if len(candidates) > 64 or any(row[3] is None or row[3] > 2 * 1024 * 1024 for row in candidates):
            return {**result, "status": "resource_limit"}
        point = self._ogr.Geometry(self._ogr.wkbPoint)
        point.AddPoint_2D(lon, lat)
        matches = []
        boundary = False
        for fid, name, code, _ in candidates:
            feature = self._layer.GetFeature(fid)
            geometry = feature.GetGeometryRef() if feature else None
            if geometry is None or geometry.IsEmpty() or not geometry.IsValid():
                return {**result, "status": "unavailable"}
            if geometry.Contains(point):
                matches.append((name, code))
            elif geometry.Intersects(point):
                boundary = True
        if boundary or len(matches) > 1:
            return {**result, "status": "ambiguous"}
        if len(matches) == 1:
            name, code = matches[0]
            if not name or not code:
                return {**result, "status": "unavailable"}
            return {**result, "status": "available", "name": name, "national_code": code}
        return result


def main():
    """Persistent JSON-lines adapter for the isolated local viewer preview."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--edition", required=True)
    args = parser.parse_args()
    reader = MunicipalityReader(args.dataset, edition=args.edition)
    try:
        for line in sys.stdin:
            if len(line) > 1024:
                raise ValueError("request_too_large")
            request = json.loads(line)
            try:
                location = reader.lookup(request["lat"], request["lon"])
            except (ValueError, RuntimeError, sqlite3.Error):
                location = {"status": "unavailable"}
            print(json.dumps({"id": request["id"], "location": location}, ensure_ascii=False), flush=True)
    finally:
        reader.close()


if __name__ == "__main__":
    main()
