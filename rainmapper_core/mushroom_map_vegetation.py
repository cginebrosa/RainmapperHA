"""Bounded resident MVC50 point lookup over an explicitly prepared SQLite index."""
from collections import OrderedDict
from copy import deepcopy
import json
import math
from pathlib import Path
import sqlite3
import threading

SOURCE = 'mvc50'
EDITION = '2019-11'
FIELDS = ('LLFISCAT_t', 'LLVA_niv2t', 'LLVA_Subst')
FORMAT = 'mvc50_point_index_v1'
MAX_CANDIDATES = 64
MAX_GEOMETRY_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024


class VegetationReader:
    def __init__(self, path):
        from osgeo import ogr, osr
        self.path = Path(path).resolve(strict=True)
        self.identity = self._stamp()
        self.lock = threading.Lock()
        self.cache = OrderedDict()
        self.ogr = ogr
        self.db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, check_same_thread=False)
        try:
            self.db.execute('PRAGMA query_only=ON')
            self.db.execute('PRAGMA cache_size=-2048')
            meta = json.loads(self.db.execute('SELECT value FROM metadata').fetchone()[0])
            if (meta.get('format'), meta.get('source_id'), meta.get('edition'), meta.get('epsg')) != (FORMAT, SOURCE, EDITION, 25831):
                raise ValueError('invalid_mvc50_index')
            self.db.execute('SELECT id,minx,maxx,miny,maxy FROM bounds LIMIT 0')
            geographic, projected = osr.SpatialReference(), osr.SpatialReference()
            geographic.ImportFromEPSG(4326)
            projected.ImportFromEPSG(25831)
            for srs in (geographic, projected):
                srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            self.transform = osr.CoordinateTransformation(geographic, projected)
        except Exception:
            self.db.close()
            raise

    def _stamp(self):
        s = self.path.stat()
        return s.st_ino, s.st_size, s.st_mtime_ns

    def close(self):
        with self.lock:
            self.cache.clear()
            self.db.close()

    def lookup(self, lat, lon):
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > lim
               for v, lim in ((lat, 90), (lon, 180))):
            raise ValueError('invalid_point')
        with self.lock:
            base = {'source_id': SOURCE, 'edition': EDITION}
            if self._stamp() != self.identity:
                self.cache.clear()
                return {**base, 'status': 'unavailable', 'reason': 'dataset_changed'}
            key = (lat, lon)
            if key not in self.cache:
                self.cache[key] = {**base, **self._lookup(lat, lon)}
                if len(self.cache) > 64:
                    self.cache.popitem(last=False)
            self.cache.move_to_end(key)
            return deepcopy(self.cache[key])

    def _lookup(self, lat, lon):
        x, y, _ = self.transform.TransformPoint(lon, lat)
        if not math.isfinite(x) or not math.isfinite(y):
            return {'status': 'not_covered'}
        rows = self.db.execute('SELECT p.id,length(p.geom),length(p.attributes) FROM bounds r '
                              'JOIN features p ON p.id=r.id WHERE minx<=? AND maxx>=? '
                              'AND miny<=? AND maxy>=? ORDER BY p.id LIMIT ?',
                              (x, x, y, y, MAX_CANDIDATES + 1)).fetchall()
        if (len(rows) > MAX_CANDIDATES or any(not size or size > MAX_GEOMETRY_BYTES or attrs > 2048
                                             for _, size, attrs in rows)
                or sum(size for _, size, _ in rows) > MAX_TOTAL_BYTES):
            return {'status': 'resource_limit'}
        point = self.ogr.Geometry(self.ogr.wkbPoint)
        point.AddPoint_2D(x, y)
        matches = []
        for fid, _, _ in rows:
            wkb, attributes = self.db.execute('SELECT geom,attributes FROM features WHERE id=?', (fid,)).fetchone()
            geom = self.ogr.CreateGeometryFromWkb(wkb)
            if geom is None or geom.IsEmpty() or not geom.IsValid():
                return {'status': 'unavailable', 'reason': 'invalid_geometry'}
            if geom.Contains(point):
                matches.append({'feature_id': fid, 'properties': json.loads(attributes)})
            elif geom.Intersects(point):
                return {'status': 'ambiguous', 'reason': 'boundary'}
        if len(matches) > 1:
            return {'status': 'ambiguous', 'reason': 'overlap'}
        return {'status': 'available', **matches[0]} if matches else {'status': 'not_covered'}


def prepare(source, destination):
    """Explicit offline operation: stream features once, keep original geometries."""
    from osgeo import ogr
    source, destination = Path(source).resolve(strict=True), Path(destination)
    if destination.exists():
        raise ValueError('mvc50_destination_exists')
    dataset = ogr.Open(str(source), 0)
    layer = dataset.GetLayer(0) if dataset else None
    if layer is None or layer.GetSpatialRef().GetAuthorityCode(None) != '25831':
        raise ValueError('invalid_mvc50_source_crs')
    if any(layer.GetLayerDefn().GetFieldIndex(field) < 0 for field in FIELDS):
        raise ValueError('invalid_mvc50_source_fields')
    if layer.GetFeatureCount() > 200000:
        raise ValueError('mvc50_feature_limit')
    stamps = {ext: (source.with_suffix(ext).stat().st_size, source.with_suffix(ext).stat().st_mtime_ns)
              for ext in ('.shp', '.shx', '.dbf', '.prj')}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.preparing')
    if temporary.exists():
        raise ValueError('mvc50_staging_exists')
    count = geometry_bytes = max_geometry_bytes = 0
    with sqlite3.connect(temporary) as db:
        db.executescript('CREATE TABLE metadata(value TEXT NOT NULL); '
                         'CREATE TABLE features(id INTEGER PRIMARY KEY,geom BLOB NOT NULL,attributes TEXT NOT NULL); '
                         'CREATE VIRTUAL TABLE bounds USING rtree(id,minx,maxx,miny,maxy);')
        for feature in layer:
            geom = feature.GetGeometryRef()
            if geom is None or geom.IsEmpty():
                raise ValueError('mvc50_empty_geometry')
            attrs = {field: feature.GetField(field) for field in FIELDS}
            encoded = json.dumps(attrs, ensure_ascii=False)
            size = geom.WkbSize()
            if len(encoded.encode()) > 2048 or size > 16 * 1024 * 1024:
                raise ValueError('mvc50_feature_size_limit')
            fid = feature.GetFID()
            db.execute('INSERT INTO features VALUES(?,?,?)', (fid, bytes(geom.ExportToWkb()), encoded))
            db.execute('INSERT INTO bounds VALUES(?,?,?,?,?)', (fid, *geom.GetEnvelope()))
            count += 1
            geometry_bytes += size
            max_geometry_bytes = max(max_geometry_bytes, size)
        for ext, expected in stamps.items():
            s = source.with_suffix(ext).stat()
            if (s.st_size, s.st_mtime_ns) != expected:
                raise ValueError('mvc50_source_changed')
        meta = {'format': FORMAT, 'source_id': SOURCE, 'edition': EDITION, 'epsg': 25831,
                'source': source.name, 'source_stamps': stamps, 'feature_count': count,
                'geometry_bytes': geometry_bytes, 'max_geometry_bytes': max_geometry_bytes}
        db.execute('INSERT INTO metadata VALUES(?)', (json.dumps(meta),))
    temporary.rename(destination)
    return {**meta, 'bytes': destination.stat().st_size}
