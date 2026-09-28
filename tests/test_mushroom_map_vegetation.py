import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch
try:
    from osgeo import ogr, osr
except ImportError:
    ogr = osr = None
from rainmapper_core.mushroom_map_vegetation import VegetationReader, prepare, FIELDS


@unittest.skipIf(ogr is None, 'GDAL bindings required')
class VegetationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source, self.index = root/'mvc.shp', root/'mvc.sqlite'
        ds = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(self.source))
        srs = osr.SpatialReference(); srs.ImportFromEPSG(25831)
        layer = ds.CreateLayer('mvc', srs, ogr.wkbPolygon)
        for name in FIELDS:
            layer.CreateField(ogr.FieldDefn(name, ogr.OFTString))
        for code, wkt in [('one','POLYGON ((0 0,4 0,4 4,0 4,0 0),(1 1,1 2,2 2,2 1,1 1))'),
                          ('hole','POLYGON ((1 1,2 1,2 2,1 2,1 1))'),
                          ('overlap','POLYGON ((3 3,5 3,5 5,3 5,3 3))')]:
            f = ogr.Feature(layer.GetLayerDefn())
            for name in FIELDS: f.SetField(name, code)
            f.SetGeometry(ogr.CreateGeometryFromWkt(wkt)); layer.CreateFeature(f)
        f = layer = ds = None
        self.report = prepare(self.source, self.index)
        self.reader = VegetationReader(self.index)
        self.addCleanup(self.reader.close)
        self.reader.transform = Mock(TransformPoint=lambda lon, lat: (lon, lat, 0))

    def test_exact_holes_borders_overlap_and_outside(self):
        self.assertEqual(self.report['feature_count'], 3)
        self.assertEqual(self.reader.lookup(.5,.5)['properties']['LLVA_Subst'], 'one')
        self.assertEqual(self.reader.lookup(1.5,1.5)['properties']['LLVA_Subst'], 'hole')
        self.assertEqual(self.reader.lookup(1,1)['reason'], 'boundary')
        self.assertEqual(self.reader.lookup(3.5,3.5)['reason'], 'overlap')
        self.assertEqual(self.reader.lookup(42,2)['status'], 'not_covered')
        with self.assertRaises(ValueError): prepare(self.source, self.index)

    def test_limits_before_decoding_geometry_and_cache_is_bounded(self):
        for key in ('MAX_CANDIDATES', 'MAX_GEOMETRY_BYTES', 'MAX_TOTAL_BYTES'):
            with patch('rainmapper_core.mushroom_map_vegetation.'+key, 0):
                self.reader.cache.clear()
                with patch.object(self.reader, 'ogr') as decoder:
                    self.assertEqual(self.reader.lookup(.5,.5)['status'], 'resource_limit')
                    decoder.CreateGeometryFromWkb.assert_not_called()
        self.reader.cache.clear()
        self.reader.lookup(.5,.5)['properties']['LLVA_Subst'] = 'corrupt'
        self.assertEqual(self.reader.lookup(.5,.5)['properties']['LLVA_Subst'], 'one')
        for i in range(70): self.reader.lookup(40,i/100)
        self.assertEqual(len(self.reader.cache), 64)
        before = self.index.stat()
        os.utime(self.index, ns=(before.st_atime_ns, before.st_mtime_ns+1000000000))
        self.assertEqual(self.reader.lookup(.5,.5)['reason'], 'dataset_changed')

    def test_invalid_points(self):
        for lat, lon in ((True,0),(float('nan'),2),(91,0),(0,181)):
            with self.assertRaises(ValueError): self.reader.lookup(lat,lon)
