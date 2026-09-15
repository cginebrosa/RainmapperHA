"""Small synthetic GeoPackages: geometry, bounds, provenance and CRS."""
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import Mock, patch

try:
    from osgeo import ogr, osr
except ImportError:
    ogr = osr = None

from rainmapper_core.mushroom_map_land import LandReader, SOURCES
from rainmapper_core.mushroom_map_land_parts import prepare, LandParts


@unittest.skipIf(ogr is None, "GDAL bindings required")
class LandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = {}
        self.readers = {}
        for kind, (table, field, _, _) in SOURCES.items():
            path = Path(self.tmp.name)/(kind+".gpkg")
            self.paths[kind] = path
            ds = ogr.GetDriverByName("GPKG").CreateDataSource(str(path))
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(25831)
            layer = ds.CreateLayer(table, srs, ogr.wkbPolygon, options=["FID=id", "GEOMETRY_NAME=geom", "SPATIAL_INDEX=YES"])
            layer.CreateField(ogr.FieldDefn(field, ogr.OFTString))
            if kind == "geology":
                layer.CreateField(ogr.FieldDefn("Descripcio", ogr.OFTString))
            for code, wkt in [("1", "POLYGON ((0 0,4 0,4 4,0 4,0 0),(1 1,1 2,2 2,2 1,1 1))"),
                              ("2", "POLYGON ((1 1,2 1,2 2,1 2,1 1))"),
                              ("3", "POLYGON ((3 3,5 3,5 5,3 5,3 3))")]:
                f = ogr.Feature(layer.GetLayerDefn())
                f.SetField(field, code)
                if kind == "geology":
                    f.SetField("Descripcio", "Geologia "+code)
                f.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
                layer.CreateFeature(f)
            f = layer = ds = None
            if kind == "vegetation":
                with closing(sqlite3.connect(path)) as db, db:
                    db.execute("CREATE TABLE cobertes_sol_categories (nivell_2 INTEGER, categoria TEXT)")
                    db.executemany("INSERT INTO cobertes_sol_categories VALUES (?,?)", [(1,"Bosc <literal>"),(2,"Prat"),(3,"Solapament")])
            r = LandReader(path, kind)
            self.addCleanup(r.close)
            self.readers[kind] = r
            r._transform = Mock(TransformPoint=lambda lon,lat: (lon,lat,0))

    def test_polygons_holes_labels_and_sources(self):
        for kind, reader in self.readers.items():
            self.assertEqual(reader.lookup(.5,.5)["code"], "1")
            self.assertEqual(reader.lookup(1.5,1.5)["code"], "2")
            self.assertEqual(reader.lookup(.5,.5)["source_id"], SOURCES[kind][2])
            self.assertEqual(reader.lookup(.5,.5)["mapping_status"], "not_evaluated")
        self.assertEqual(self.readers['vegetation'].lookup(.5,.5)['label'], 'Bosc <literal>')

    def test_boundary_overlap_and_outside(self):
        r = self.readers['vegetation']
        self.assertEqual(r.lookup(1,1)['status'], 'ambiguous')
        self.assertEqual(r.lookup(3.5,3.5)['reason'], 'overlap')
        self.assertEqual(r.lookup(42.5,2)['status'], 'not_covered')
        self.assertEqual(r.lookup(1.5,1-1e-8)['code'], '1')
        self.assertEqual(r.lookup(1.5,1+1e-8)['code'], '2')

    def test_bounds_before_geometry_materialization(self):
        for limit in ('MAX_CANDIDATES','MAX_GEOMETRY_BYTES','MAX_TOTAL_GEOMETRY_BYTES'):
            with patch('rainmapper_core.mushroom_map_land.'+limit, 0):
                r = self.readers['vegetation']
                r._cache.clear()
                with patch.object(r, '_layer') as layer:
                    self.assertEqual(r.lookup(.5,.5)['status'], 'resource_limit')
                    layer.GetFeature.assert_not_called()

    def test_cache_bounded_independent_and_no_stale_dataset(self):
        r = self.readers['vegetation']
        r.lookup(.5,.5)['label'] = 'mutated'
        self.assertEqual(r.lookup(.5,.5)['label'],'Bosc <literal>')
        for i in range(70):
            r.lookup(40,i/100)
        self.assertEqual(len(r._cache),64)
        p = self.paths['vegetation']
        stat = p.stat()
        os.utime(p, ns=(stat.st_atime_ns, stat.st_mtime_ns+1000000000))
        self.assertEqual(r.lookup(.5,.5)['reason'],'dataset_changed')

    def test_real_coordinate_transform_and_schema_validation(self):
        r = LandReader(self.paths['geology'], 'geology')
        self.addCleanup(r.close)
        x,y,_ = r._transform.TransformPoint(3,42)
        self.assertAlmostEqual(x,500000,places=2)
        self.assertTrue(4600000 < y < 4700000)
        p = self.paths['vegetation']
        self.readers['vegetation'].close()
        with closing(sqlite3.connect(p)) as db, db:
            db.execute('DROP TABLE rtree_cobertes_sol_geom')
        with self.assertRaises(sqlite3.OperationalError):
            LandReader(p,'vegetation')

    def test_invalid_point(self):
        for lat,lon in [(True,0),(float('nan'),0),(91,0),(0,181)]:
            with self.assertRaises(ValueError):
                self.readers['vegetation'].lookup(lat,lon)

    def _prepared(self):
        output=Path(self.tmp.name)/'parts.gpkg'
        prepare(self.paths['vegetation'],output,'vegetation',threshold=1,part_bytes=140)
        reader=LandReader(self.paths['vegetation'],'vegetation',parts=output)
        reader._transform=Mock(TransformPoint=lambda lon,lat:(lon,lat,0))
        self.addCleanup(reader.close)
        return output,reader

    def test_subdivision_preserves_holes_overlaps_and_artificial_seams(self):
        _,r=self._prepared()
        original=self.readers['vegetation']
        for point in [(.5,2),(2,.5),(1.5,1.5),(1,1),(3.5,3.5),(1,4),(40,40)]:
            self.assertEqual(r.lookup(*point),original.lookup(*point))
        # The large original is never loaded when reading its parts.
        r._cache.clear()
        with patch.object(r,'_layer') as layer:
            self.assertEqual(r.lookup(.5,2)['status'],'available')
            layer.GetFeature.assert_not_called()

    def test_parts_bounds_identity_and_incomplete_preparation(self):
        output,r=self._prepared()
        with patch('rainmapper_core.mushroom_map_land.MAX_TOTAL_GEOMETRY_BYTES',0):
            with patch.object(r._parts,'geometries') as geometries:
                self.assertEqual(r.lookup(.5,2)['status'],'resource_limit')
                geometries.assert_not_called()
        info=output.stat();os.utime(output,ns=(info.st_atime_ns,info.st_mtime_ns+1000000000))
        self.assertEqual(r.lookup(.5,2)['reason'],'parts_changed')
        with self.assertRaises(ValueError):
            LandParts(output,self.paths['geology'],'geology')
        r.close()
        with closing(sqlite3.connect(output)) as db,db:
            db.execute('UPDATE preparation SET value=replace(value,\'"complete": true\',\'"complete": false\')')
        with self.assertRaises(ValueError):
            LandParts(output,self.paths['vegetation'],'vegetation')


if __name__ == '__main__':
    unittest.main()
