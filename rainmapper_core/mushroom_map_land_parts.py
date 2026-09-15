"""Prepared subdivisions of oversized source polygons; never prepared per click."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

FORMAT = "prediction_map_land_parts_v1"
PART_BYTES = 128 * 1024


def stamp(path):
    s = Path(path).stat()
    return s.st_size, s.st_mtime_ns


class LandParts:
    def __init__(self, path, source, kind, *, sources=None):
        from osgeo import ogr
        self.path = Path(path).resolve(strict=True)
        self.identity = stamp(self.path)
        self.db = self.dataset = self.layer = None
        self.ogr = ogr
        try:
            self.db = sqlite3.connect(self.path.as_uri()+"?mode=ro", uri=True, check_same_thread=False)
            self.db.execute("PRAGMA query_only=ON")
            self.db.execute("PRAGMA cache_size=-2048")
            row = self.db.execute("SELECT value FROM preparation WHERE length(value)<=65536").fetchone()
            meta = json.loads(row[0]) if row else {}
            if (meta.get("format") != FORMAT or meta.get("kind") != kind or
                    meta.get("source_stamp") != (sources.stamp(source) if sources else list(stamp(source)))
                    or meta.get("complete") is not True):
                raise ValueError("land_parts_source_mismatch")
            originals = meta.get("source_ids")
            if not isinstance(originals, list) or not 0 < len(originals) <= 64 or any(type(x) is not int for x in originals):
                raise ValueError("invalid_land_parts_sources")
            self.source_ids = frozenset(originals)
            self.db.execute("SELECT id FROM rtree_land_parts_geom LIMIT 0")
            self.db.execute("SELECT id, source_fid, geom FROM land_parts LIMIT 0")
            if self.db.execute("SELECT srs_id FROM gpkg_geometry_columns WHERE table_name='land_parts' AND column_name='geom'").fetchone() != (25831,):
                raise ValueError("invalid_land_parts_crs")
            counts = dict(self.db.execute("SELECT source_fid,count(*) FROM land_parts GROUP BY source_fid"))
            if counts != {int(k): v for k,v in meta.get("part_counts",{}).items()} or set(counts) != self.source_ids:
                raise ValueError("incomplete_land_parts")
            self.dataset = ogr.Open(str(self.path), 0)
            self.layer = self.dataset.GetLayerByName("land_parts") if self.dataset else None
            if self.layer is None:
                raise ValueError("invalid_land_parts_layer")
        except Exception:
            self.close()
            raise

    def close(self):
        self.layer = self.dataset = None
        if self.db is not None:
            self.db.close()
            self.db = None

    def candidates(self, x, y, limit):
        if stamp(self.path) != self.identity:
            raise ValueError("land_parts_changed")
        return self.db.execute(
            "SELECT p.id, length(p.geom), p.source_fid FROM rtree_land_parts_geom r "
            "JOIN land_parts p ON p.id=r.id "
            "WHERE r.minx<=? AND r.maxx>=? AND r.miny<=? AND r.maxy>=? LIMIT ?",
            (x,x,y,y,limit+1)).fetchall()

    def geometries(self, rows):
        """Union only nearby parts of each original: artificial cuts aren't borders."""
        groups = {}
        for fid, _, source_fid in rows:
            feature = self.layer.GetFeature(fid)
            geom = feature.GetGeometryRef() if feature else None
            if geom is None or geom.IsEmpty() or not geom.IsValid():
                raise ValueError("invalid_land_part")
            groups.setdefault(source_fid, []).append(geom.Clone())
        for source_fid, geometries in groups.items():
            merged = self.ogr.Geometry(self.ogr.wkbMultiPolygon)
            for geom in geometries:
                if self.ogr.GT_Flatten(geom.GetGeometryType()) == self.ogr.wkbPolygon:
                    merged.AddGeometry(geom)
                else:
                    for part in geom:
                        merged.AddGeometry(part)
            union = merged.UnionCascaded()
            if union is None or union.IsEmpty() or not union.IsValid():
                raise ValueError("invalid_land_parts_union")
            yield source_fid, union


def subdivide(geometry, *, max_bytes=PART_BYTES, depth=0):
    """Lossless axis-aligned clipping; no simplification or buffers."""
    from osgeo import ogr
    if geometry.IsEmpty():
        return
    if geometry.WkbSize() <= max_bytes:
        yield geometry
        return
    if depth >= 24:
        raise ValueError("subdivision_depth_limit")
    xmin,xmax,ymin,ymax = geometry.GetEnvelope()
    if xmax-xmin >= ymax-ymin:
        mid = (xmin+xmax)/2
        boxes = [(xmin,mid,ymin,ymax),(mid,xmax,ymin,ymax)]
    else:
        mid = (ymin+ymax)/2
        boxes = [(xmin,xmax,ymin,mid),(xmin,xmax,mid,ymax)]
    for left,right,bottom,top in boxes:
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for x,y in [(left,bottom),(right,bottom),(right,top),(left,top),(left,bottom)]:
            ring.AddPoint_2D(x,y)
        box = ogr.Geometry(ogr.wkbPolygon)
        box.AddGeometry(ring)
        clipped = geometry.Intersection(box)
        if clipped is None:
            raise ValueError("subdivision_failed")
        # Clipping may include boundary-only line remnants. Keep polygon parts.
        polygons = ogr.Geometry(ogr.wkbMultiPolygon)
        def collect(g):
            kind = ogr.GT_Flatten(g.GetGeometryType())
            if kind == ogr.wkbPolygon:
                polygons.AddGeometry(g)
            elif kind in (ogr.wkbMultiPolygon, ogr.wkbGeometryCollection):
                for child in g:
                    collect(child)
        collect(clipped)
        yield from subdivide(polygons, max_bytes=max_bytes, depth=depth+1)


def prepare(source, output, kind, *, threshold=2*1024*1024, part_bytes=PART_BYTES):
    """Explicit offline preparation on development machine/worker, source read-only."""
    from osgeo import ogr, osr
    from rainmapper_core.mushroom_map_land import SOURCES
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("land_parts_output_exists")
    source_stamp = stamp(source)
    table = SOURCES[kind][0]
    with closing(sqlite3.connect(source.as_uri()+"?mode=ro", uri=True)) as db:
        rows = db.execute(f'SELECT id,length(geom) FROM "{table}" WHERE length(geom)>? LIMIT 65', (threshold,)).fetchall()
    if not rows or len(rows)>64 or any(size>64*1024*1024 for _,size in rows):
        raise ValueError("land_preparation_scope_limit")
    output.parent.mkdir(parents=True,exist_ok=True)
    original = ogr.Open(str(source),0)
    layer = original.GetLayerByName(table)
    target = ogr.GetDriverByName("GPKG").CreateDataSource(str(output))
    srs = osr.SpatialReference();srs.ImportFromEPSG(25831)
    if not layer.GetSpatialRef().IsSame(srs):
        raise ValueError("land_preparation_crs")
    dest = target.CreateLayer("land_parts",srs,ogr.wkbMultiPolygon,options=["FID=id","GEOMETRY_NAME=geom","SPATIAL_INDEX=YES"])
    dest.CreateField(ogr.FieldDefn("source_fid",ogr.OFTInteger64))
    counts = {}
    target.StartTransaction()
    for fid,_ in rows:
        feature = layer.GetFeature(fid)
        geometry = feature.GetGeometryRef()
        if not geometry.IsValid():
            raise ValueError("invalid_original_geometry")
        area = 0.0;count = 0
        for part in subdivide(geometry,max_bytes=part_bytes):
            if not part.IsValid():
                raise ValueError("invalid_subdivision")
            area += part.GetArea();count += 1
            if count > 16384:
                raise ValueError("land_part_count_limit")
            out = ogr.Feature(dest.GetLayerDefn());out.SetField("source_fid",fid)
            out.SetGeometry(ogr.ForceToMultiPolygon(part.Clone()))
            if dest.CreateFeature(out) != 0:
                raise ValueError("land_part_write_failed")
        if count == 0 or abs(area-geometry.GetArea()) > max(.01,geometry.GetArea()*1e-8):
            raise ValueError("land_subdivision_area_mismatch")
        counts[fid]=count
        print(f"Prepared source {fid}: {count} parts",flush=True)
    target.CommitTransaction()
    out = dest = target = feature = layer = original = None
    if stamp(source) != source_stamp:
        raise ValueError("land_source_changed_during_preparation")
    meta = {"format":FORMAT,"kind":kind,"source_stamp":list(source_stamp),"source_ids":[r[0] for r in rows],"part_counts":counts,"complete":True}
    with closing(sqlite3.connect(output)) as db, db:
        db.execute("CREATE INDEX land_parts_source ON land_parts(source_fid)")
        db.execute("CREATE TABLE preparation(value TEXT NOT NULL)")
        db.execute("INSERT INTO preparation VALUES (?)",(json.dumps(meta),))
    return meta
