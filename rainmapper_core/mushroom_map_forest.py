"""Indexed MFE polygon trees, descriptive only; same reader on HA and worker.

The auxiliary index stores bounding boxes, record sizes and small subdivisions
of the few oversized polygons. Original source files remain unchanged.
Prepare explicitly once; queries do not build indexes or scan shapefiles.
"""
from collections import OrderedDict
from copy import deepcopy
from contextlib import closing
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sqlite3
import struct
import threading

MAX_GEOMETRY = 2 * 1024 * 1024
MAX_CANDIDATES = 64


def stamp(path):
    stat = Path(path).stat()
    return [stat.st_size, stat.st_mtime_ns]


def source_stamps(path, sources=None):
    reader = sources.stamp if sources else stamp
    return {ext: reader(path.with_suffix(ext)) for ext in ('.shp', '.shx', '.dbf', '.prj')}


def prepare_index(source, output):
    """Read SHX entries and polygon headers only, in bounded batches on setup."""
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if source.suffix.lower() != '.shp' or output.exists():
        raise ValueError('forest_source_or_existing_output')
    identities = source_stamps(source)
    count = (identities['.shx'][0] - 100) // 8
    if count < 1 or count > 2_000_000 or (identities['.shx'][0]-100) % 8:
        raise ValueError('forest_index_size')
    output.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(output)) as db, db, source.open('rb') as shp, source.with_suffix('.shx').open('rb') as shx:
        db.execute('CREATE TABLE metadata (value TEXT NOT NULL)')
        db.execute('CREATE TABLE records (fid INTEGER PRIMARY KEY, size INTEGER NOT NULL)')
        db.execute('CREATE VIRTUAL TABLE bounds USING rtree(fid,minx,maxx,miny,maxy)')
        shx.seek(100)
        for start in range(0, count, 1000):
            records, boxes = [], []
            raw = shx.read(min(1000, count-start)*8)
            for i, (offset, words) in enumerate(struct.iter_unpack('>II', raw)):
                fid, size = start+i, words*2
                if offset*2+8+size > identities['.shp'][0] or size < 4:
                    raise ValueError('invalid_forest_record')
                shp.seek(offset*2)
                header = shp.read(min(44, size+8))
                record_id, actual_words = struct.unpack('>II', header[:8])
                shape = struct.unpack('<I', header[8:12])[0]
                if record_id != fid+1 or actual_words != words:
                    raise ValueError('invalid_forest_offsets')
                if shape == 0:
                    continue
                if shape not in (5, 15, 25) or size < 44:
                    raise ValueError('forest_polygon_required')
                minx,miny,maxx,maxy = struct.unpack('<4d', header[12:44])
                if not all(math.isfinite(v) for v in (minx,miny,maxx,maxy)) or minx>maxx or miny>maxy:
                    raise ValueError('invalid_forest_bounds')
                records.append((fid,size)); boxes.append((fid,minx,maxx,miny,maxy))
            db.executemany('INSERT INTO records VALUES (?,?)',records)
            db.executemany('INSERT INTO bounds VALUES (?,?,?,?,?)',boxes)
        # A few large multipart polygons have country-scale bounding boxes.
        # Reuse the lossless subdivision routine, explicitly during preparation.
        from osgeo import ogr
        from rainmapper_core.mushroom_map_land_parts import subdivide
        db.execute('CREATE TABLE parts (pid INTEGER PRIMARY KEY, fid INTEGER, geom BLOB)')
        db.execute('CREATE VIRTUAL TABLE part_bounds USING rtree(pid,minx,maxx,miny,maxy)')
        db.execute('CREATE TABLE large_attributes (fid INTEGER PRIMARY KEY, value TEXT)')
        large = db.execute('SELECT fid,size FROM records WHERE size>? LIMIT 65',(MAX_GEOMETRY,)).fetchall()
        if len(large)>64 or any(size>64*1024*1024 for _,size in large):
            raise ValueError('forest_preparation_limit')
        dataset = ogr.Open(str(source),0)
        layer = dataset.GetLayer(0)
        pid = 0
        repaired = []
        for fid,_ in large:
            feature = layer.GetFeature(fid)
            geom = feature.GetGeometryRef()
            if geom is None:
                raise ValueError('invalid_forest_geometry')
            if not geom.IsValid():
                original_area = geom.GetArea()
                geom = geom.MakeValid()
                if (geom is None or not geom.IsValid() or
                        abs(geom.GetArea()-original_area)>max(.01,abs(original_area)*1e-8)):
                    raise ValueError('forest_repair_area_mismatch')
                repaired.append(fid)
            attrs = {key:feature.GetField(key) for key in ('Poligon','FormArbol',
                *[f'Especie{i}' for i in range(1,4)],*[f'n_sp{i}' for i in range(1,4)])}
            db.execute('INSERT INTO large_attributes VALUES (?,?)',(fid,json.dumps(attrs)))
            area = 0
            for part in subdivide(geom):
                pid += 1
                if pid>16384 or not part.IsValid():
                    raise ValueError('forest_parts_limit')
                area += part.GetArea()
                a,b,c,d = part.GetEnvelope()
                db.execute('INSERT INTO parts VALUES (?,?,?)',(pid,fid,bytes(part.ExportToWkb())))
                db.execute('INSERT INTO part_bounds VALUES (?,?,?,?,?)',(pid,a,b,c,d))
            if abs(area-geom.GetArea())>max(.01,geom.GetArea()*1e-8):
                raise ValueError('forest_parts_area_mismatch')
        if source_stamps(source) != identities:
            raise ValueError('forest_changed_during_preparation')
        meta = {'format':'prediction_map_forest_v2', 'source':os.path.relpath(source,output.parent),
                'stamps':identities, 'record_count':count, 'part_count':pid, 'repaired_fids':repaired}
        db.execute('INSERT INTO metadata VALUES (?)',(json.dumps(meta),))
    return {'records':count,'index_bytes':output.stat().st_size}


class ForestReader:
    def __init__(self, index, *, catalogs=None, sources=None):
        from osgeo import ogr, osr
        self._lock = threading.Lock()
        self._sources = sources
        self._cache = OrderedDict()
        self._geometry_repairs = OrderedDict()
        self._db = self._dataset = self._layer = None
        self._index = Path(index).resolve(strict=True)
        self._index_stamp = stamp(self._index)
        self._catalog = Path(catalogs).resolve(strict=True) if catalogs else None
        self._names = {}
        self._host_ids = {}
        self._ogr = ogr
        try:
            self._db = sqlite3.connect(self._index.as_uri()+'?mode=ro',uri=True,check_same_thread=False)
            self._db.execute('PRAGMA query_only=ON')
            self._db.execute('PRAGMA cache_size=-2048')
            rows = self._db.execute('SELECT value FROM metadata LIMIT 2').fetchall()
            if len(rows)!=1 or len(rows[0][0])>4096:
                raise ValueError('invalid_forest_index')
            meta = json.loads(rows[0][0])
            if meta.get('format')!='prediction_map_forest_v2':
                raise ValueError('invalid_forest_index')
            self._path = (self._index.parent/meta['source']).resolve(strict=True)
            self._identity = meta['stamps']
            if source_stamps(self._path, self._sources)!=self._identity:
                raise ValueError('forest_source_changed')
            self._db.execute('SELECT r.fid,r.size FROM bounds b JOIN records r ON r.fid=b.fid LIMIT 0')
            if self._db.execute('SELECT count(*) FROM parts').fetchone()[0]!=meta.get('part_count'):
                raise ValueError('incomplete_forest_parts')
            self._repaired = set(meta.get('repaired_fids',[]))
            self._dataset = ogr.Open(str(self._path),0)
            self._layer = self._dataset.GetLayer(0) if self._dataset else None
            if not self._layer or ogr.GetGEOSVersionMajor()<3:
                raise ValueError('forest_layer_unavailable')
            fields = {f.GetName() for f in self._layer.schema}
            required = {'Poligon','FormArbol',*[f'Especie{i}' for i in range(1,4)],*[f'n_sp{i}' for i in range(1,4)]}
            if not required.issubset(fields):
                raise ValueError('forest_schema_not_supported')
            projected = self._layer.GetSpatialRef()
            if projected is None:
                raise ValueError('forest_crs_required')
            projected = projected.Clone()
            geographic = osr.SpatialReference(); geographic.ImportFromEPSG(4326)
            for crs in (projected,geographic):
                crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            self._transform = osr.CoordinateTransformation(geographic,projected)
            self._catalog_stamp = None
            self._catalog_revision = None
            self._refresh_catalog()
        except Exception:
            self.close()
            raise

    def _refresh_catalog(self):
        """Reload only the small editable vocabulary; keep cached geography."""
        if not self._catalog:
            return
        stat = self._catalog.stat()
        identity = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
        if identity == self._catalog_stamp:
            return
        with self._catalog.open('rb') as stream:
            raw = stream.read(1024*1024+1)
        stat = self._catalog.stat()
        if len(raw)>1024*1024 or (stat.st_ino,stat.st_size,stat.st_mtime_ns)!=identity:
            raise ValueError('forest_catalog_limit_or_changed')
        data = json.loads(raw)
        rows = data.get('catalogs',{}).get('host_taxa') if isinstance(data,dict) else None
        if not isinstance(rows,list):
            raise ValueError('invalid_forest_catalog')
        scientific, aliases = {}, {}
        labels = {}
        for index, row in enumerate(rows):
            if not isinstance(row,dict):
                raise ValueError('invalid_forest_catalog_row')
            name = row.get('scientific_name')
            common_names = row.get('common_names')
            labels[index] = {}
            for language in ('es', 'ca', 'en'):
                common = common_names.get(language,[]) if isinstance(common_names,dict) else []
                if isinstance(common,list) and common and isinstance(common[0],str) and common[0].strip():
                    labels[index][language] = common[0].strip()[:128]
            if isinstance(name,str) and name.strip():
                scientific.setdefault(name.strip().casefold(),set()).add(index)
            values = row.get('gis_aliases',[])
            if isinstance(values,list):
                for alias in values:
                    if isinstance(alias,str) and alias.strip():
                        aliases.setdefault(alias.strip().casefold(),set()).add(index)
        # Exact scientific names take precedence. A shared alias must never
        # choose an arbitrary taxon, even when both rows have the same label.
        names, host_ids = {}, {}
        for key in scientific.keys() | aliases.keys():
            owners = scientific.get(key,aliases.get(key))
            if len(owners)==1:
                owner = next(iter(owners))
                label = labels[owner]
                host_ids[key] = rows[owner].get('id')
                if label:
                    names[key] = label
        self._names, self._host_ids, self._catalog_stamp = names, host_ids, identity
        self._catalog_revision = sha256(raw).hexdigest()[:20]

    def close(self):
        with self._lock:
            self._cache.clear()
            self._geometry_repairs.clear()
            self._layer = self._dataset = None
            if self._db:
                self._db.close(); self._db = None

    def lookup(self, lat, lon):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>limit
               for v,limit in ((lat,90),(lon,180))):
            raise ValueError('invalid_point')
        with self._lock:
            base = {'source_id':'mfe25', 'exhaustive':False}
            if stamp(self._index)!=self._index_stamp or source_stamps(self._path, self._sources)!=self._identity:
                self._cache.clear()
                return {**base,'status':'unavailable','reason':'dataset_changed'}
            catalog_available = True
            try:
                self._refresh_catalog()
            except (OSError, ValueError):
                # A failed/partial save must not reuse stale display labels or
                # hide otherwise valid geographic evidence. Retry next query.
                self._names, self._host_ids, self._catalog_stamp = {}, {}, None
                self._catalog_revision = None
                catalog_available = False
            key = (lat,lon)
            if key not in self._cache:
                self._cache[key] = {**base,**self._lookup(lat,lon)}
                if len(self._cache)>64:
                    self._cache.popitem(last=False)
            self._cache.move_to_end(key)
            result = deepcopy(self._cache[key])
            result['catalog_revision'] = self._catalog_revision
            for item in result.get('items',[]):
                item['labels'] = dict(self._names.get(item['scientific_name'].strip().casefold(),{}))
                item['label'] = item['labels'].get('es',item['scientific_name'])
                item['host_id'] = self._host_ids.get(item['scientific_name'].strip().casefold())
            if not catalog_available:
                result['catalog_status'] = 'unavailable'
            return result

    def _lookup(self, lat, lon):
        x,y,_ = self._transform.TransformPoint(lon,lat)
        if not math.isfinite(x) or not math.isfinite(y):
            return {'status':'not_covered'}
        rows = self._db.execute('SELECT r.fid,r.size FROM bounds b JOIN records r ON r.fid=b.fid '
            'WHERE minx<=? AND maxx>=? AND miny<=? AND maxy>=? AND r.fid NOT IN (SELECT fid FROM large_attributes) LIMIT ?',
            (x,x,y,y,MAX_CANDIDATES+1)).fetchall()
        parts = self._db.execute('SELECT p.pid,p.fid,length(p.geom) FROM part_bounds b JOIN parts p ON p.pid=b.pid '
            'WHERE minx<=? AND maxx>=? AND miny<=? AND maxy>=? LIMIT ?',
            (x,x,y,y,MAX_CANDIDATES+1)).fetchall()
        if (len(rows)+len(parts)>MAX_CANDIDATES or any(size>MAX_GEOMETRY for _,size in rows)
                or any(size>MAX_GEOMETRY for _,_,size in parts)
                or sum(s for _,s in rows)+sum(s for _,_,s in parts)>8*1024*1024):
            return {'status':'resource_limit'}
        point = self._ogr.Geometry(self._ogr.wkbPoint); point.AddPoint_2D(x,y)
        matches = []
        def candidates():
            for fid,_ in rows:
                feature = self._layer.GetFeature(fid)
                if feature is None:
                    raise ValueError('missing_forest_feature')
                yield feature.GetGeometryRef(), feature.GetField, ('source',fid)
            grouped = {}
            for pid,fid,_ in parts:
                raw = self._db.execute('SELECT geom FROM parts WHERE pid=?',(pid,)).fetchone()[0]
                geom = self._ogr.CreateGeometryFromWkb(raw)
                if geom is None or not geom.IsValid():
                    raise ValueError('invalid_forest_part')
                grouped.setdefault(fid,[]).append(geom)
            for fid, geometries in grouped.items():
                merged = self._ogr.Geometry(self._ogr.wkbMultiPolygon)
                for geom in geometries:
                    if self._ogr.GT_Flatten(geom.GetGeometryType())==self._ogr.wkbPolygon:
                        merged.AddGeometry(geom)
                    else:
                        for part in geom:
                            merged.AddGeometry(part)
                attrs = json.loads(self._db.execute('SELECT value FROM large_attributes WHERE fid=?',(fid,)).fetchone()[0])
                yield merged.UnionCascaded(), attrs.get, ('parts',fid,tuple(pid for pid,owner,_ in parts if owner==fid))
        for geom,field,key in candidates():
            geom = self._valid_geometry(geom,key)
            if geom is None:
                return {'status':'unavailable','reason':'invalid_geometry'}
            if geom.Contains(point):
                items = []
                for slot in range(1,4):
                    scientific = str(field(f'Especie{slot}') or '').strip()
                    code = field(f'n_sp{slot}')
                    if scientific and len(scientific)<=128 and code:
                        items.append({'label':scientific,
                                      'scientific_name':scientific,'code':str(code)[:32]})
                matches.append({'status':'available' if items else 'no_trees_recorded', 'items':items,
                                'polygon_id':str(field('Poligon'))[:64],
                                'formation':str(field('FormArbol') or '')[:256]})
            elif geom.Intersects(point):
                return {'status':'ambiguous'}
        if len(matches)>1:
            return {'status':'ambiguous'}
        return matches[0] if matches else {'status':'not_covered'}

    def _valid_geometry(self, geom, key):
        """Repair a bounded candidate once, never changing the source shapefile.

        An invalid distant ring in a candidate's envelope must not erase local
        tree data. Apply the same area-preserving rule used by index preparation.
        """
        if key in self._geometry_repairs:
            self._geometry_repairs.move_to_end(key)
            return self._geometry_repairs[key]
        if geom is None or geom.IsEmpty():
            return None
        if geom.IsValid():
            return geom
        if geom.WkbSize()>MAX_GEOMETRY:
            return None
        area=geom.GetArea()
        repaired=geom.MakeValid()
        if (repaired is None or repaired.IsEmpty() or not repaired.IsValid() or
            self._ogr.GT_Flatten(repaired.GetGeometryType()) not in (self._ogr.wkbPolygon,self._ogr.wkbMultiPolygon) or
            repaired.WkbSize()>MAX_GEOMETRY or
            abs(repaired.GetArea()-area)>max(.01,abs(area)*1e-8)):
            return None
        if len(self._geometry_repairs)>=8:
            self._geometry_repairs.popitem(last=False)
        self._geometry_repairs[key]=repaired
        return repaired
