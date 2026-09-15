"""Bounded, read-only lookup of local ICGC cover and geology polygons.

Descriptive source values only: no ecological inference or automatic mappings.
Datasets are immutable during a reader's lifetime; replacements require reopen.
"""
from collections import OrderedDict
from copy import deepcopy
import math
from pathlib import Path
import sqlite3
import threading


SOURCES = {
    "vegetation": ("cobertes_sol", "nivell_2", "icgc_cobertes_2024", "2024"),
    "geology": ("_04_unitats_geologiques_50000", "Codi", "icgc_geologia_50000", "2024-12"),
}
MAX_CANDIDATES = 64
MAX_GEOMETRY_BYTES = 2 * 1024 * 1024
MAX_TOTAL_GEOMETRY_BYTES = 8 * 1024 * 1024


class LandReader:
    """One resident reader per configured product, with exact point cache."""

    def __init__(self, path, kind, *, parts=None, sources=None):
        from osgeo import ogr, osr

        self._lock = threading.Lock()
        self._cache = OrderedDict()
        self._db = self._dataset = self._layer = None
        self._parts = None
        self._ogr = ogr
        self.kind = kind
        self.table, self.field, self.source_id, self.edition = SOURCES[kind]
        self._path = Path(path).resolve(strict=True)
        self._identity = self._stat()
        self._categories = {}
        try:
            if ogr.GetGEOSVersionMajor() < 3:
                raise ValueError("land_geos_required")
            self._db = sqlite3.connect(self._path.as_uri()+"?mode=ro", uri=True, check_same_thread=False)
            self._db.execute("PRAGMA query_only=ON")
            self._db.execute("PRAGMA cache_size=-2048")
            row = self._db.execute("SELECT srs_id FROM gpkg_geometry_columns WHERE table_name=? AND column_name='geom'", (self.table,)).fetchone()
            if row != (25831,):
                raise ValueError("invalid_land_crs")
            self._db.execute(f'SELECT id FROM "rtree_{self.table}_geom" LIMIT 0')
            self._db.execute(f'SELECT id, geom, "{self.field}" FROM "{self.table}" LIMIT 0')
            if kind == "vegetation":
                categories = self._db.execute("SELECT nivell_2, categoria FROM cobertes_sol_categories LIMIT 129").fetchall()
                if len(categories) > 128 or any(not isinstance(label, str) or len(label) > 512 for _, label in categories):
                    raise ValueError("invalid_land_categories")
                self._categories = {str(code): label for code, label in categories}
                if len(self._categories) != len(categories):
                    raise ValueError("duplicate_land_categories")
            else:
                self._db.execute(f'SELECT Descripcio FROM "{self.table}" LIMIT 0')
            self._label_length = 'length(p.Descripcio)' if kind == 'geology' else '0'
            self._dataset = ogr.Open(str(self._path), 0)
            self._layer = self._dataset.GetLayerByName(self.table) if self._dataset else None
            if self._layer is None or self._layer.GetFIDColumn() != "id":
                raise ValueError("invalid_land_layer")
            geographic = osr.SpatialReference()
            geographic.ImportFromEPSG(4326)
            projected = osr.SpatialReference()
            projected.ImportFromEPSG(25831)
            for srs in (geographic, projected):
                srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            self._transform = osr.CoordinateTransformation(geographic, projected)
            if parts:
                from rainmapper_core.mushroom_map_land_parts import LandParts
                self._parts = LandParts(parts, self._path, kind, sources=sources)
        except Exception:
            self.close()
            raise

    def _stat(self):
        value = self._path.stat()
        return value.st_ino, value.st_size, value.st_mtime_ns

    def close(self):
        with self._lock:
            self._cache.clear()
            self._layer = self._dataset = None
            if self._parts is not None:
                self._parts.close()
                self._parts = None
            if self._db is not None:
                self._db.close()
                self._db = None

    def lookup(self, lat, lon):
        for value, limit in ((lat, 90), (lon, 180)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > limit:
                raise ValueError("invalid_point")
        with self._lock:
            base = {"source_id": self.source_id, "edition": self.edition, "field": self.field}
            if self._parts:
                from rainmapper_core.mushroom_map_land_parts import stamp
                if stamp(self._parts.path) != self._parts.identity:
                    self._cache.clear()
                    return {**base, "status": "unavailable", "reason": "parts_changed"}
            if self._stat() != self._identity:
                self._cache.clear()
                return {**base, "status": "unavailable", "reason": "dataset_changed"}
            key = (lat, lon)
            if key not in self._cache:
                self._cache[key] = {**base, **self._lookup(lat, lon)}
                if len(self._cache) > 64:
                    self._cache.popitem(last=False)
            self._cache.move_to_end(key)
            return deepcopy(self._cache[key])

    def _lookup(self, lat, lon):
        x, y, _ = self._transform.TransformPoint(lon, lat)
        if not math.isfinite(x) or not math.isfinite(y):
            return {"status": "not_covered"}
        # Read lengths before GDAL materializes any candidate geometry.
        rows = self._db.execute(
            f'SELECT p.id, length(p.geom), length(p."{self.field}"), {self._label_length} FROM "rtree_{self.table}_geom" r '
            f'JOIN "{self.table}" p ON p.id=r.id '
            'WHERE r.minx<=? AND r.maxx>=? AND r.miny<=? AND r.maxy>=? LIMIT ?',
            (x, x, y, y, MAX_CANDIDATES+1),
        ).fetchall()
        part_rows = self._parts.candidates(x,y,MAX_CANDIDATES) if self._parts else []
        ordinary = [row for row in rows if not self._parts or row[0] not in self._parts.source_ids]
        if (len(rows) > MAX_CANDIDATES or
                len(ordinary)+len(part_rows) > MAX_CANDIDATES or
                any(size is None or size > MAX_GEOMETRY_BYTES for _, size, _, _ in ordinary) or
                any(size is None or size > MAX_GEOMETRY_BYTES for _,size,_ in part_rows) or
                sum(size for _, size, _, _ in ordinary)+sum(size for _,size,_ in part_rows) > MAX_TOTAL_GEOMETRY_BYTES):
            return {"status": "resource_limit"}
        if any(code_size is None or code_size > 128 or (label_size or 0) > 1024 for _, _, code_size, label_size in rows):
            return {"status": "unavailable", "reason": "invalid_attributes"}
        point = self._ogr.Geometry(self._ogr.wkbPoint)
        point.AddPoint_2D(x, y)
        matches = []
        def geometries():
            for fid, _, _, _ in ordinary:
                feature = self._layer.GetFeature(fid)
                geom = feature.GetGeometryRef() if feature else None
                yield fid, geom
            if self._parts:
                yield from self._parts.geometries(part_rows)
        for fid, geom in geometries():
            if geom is None or geom.IsEmpty() or not geom.IsValid():
                return {"status": "unavailable", "reason": "invalid_geometry"}
            if geom.Contains(point):
                # Attributes only: never materialize an oversized original here.
                fields = f'"{self.field}", Descripcio' if self.kind == 'geology' else f'"{self.field}"'
                attributes = self._db.execute(f'SELECT {fields} FROM "{self.table}" WHERE id=?',(fid,)).fetchone()
                if not attributes:
                    return {"status":"unavailable", "reason":"missing_source_feature"}
                code = attributes[0]
                label = self._categories.get(str(code)) if self.kind == "vegetation" else attributes[1]
                if code is None or len(str(code)) > 128 or (label is not None and len(str(label)) > 1024):
                    return {"status": "unavailable", "reason": "invalid_attributes"}
                matches.append({"feature_id": fid, "code": str(code), "label": label,
                                "mapping_status": "not_evaluated"})
            elif geom.Intersects(point):
                return {"status": "ambiguous", "reason": "boundary"}
        if len(matches) > 1:
            return {"status": "ambiguous", "reason": "overlap"}
        return {"status": "available", **matches[0]} if matches else {"status": "not_covered"}
