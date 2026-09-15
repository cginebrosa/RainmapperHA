"""Geometric tests use small synthetic polygons, never production data."""
import tempfile
import unittest
from pathlib import Path

try:
    from osgeo import ogr, osr
except ImportError:
    ogr = osr = None

from rainmapper_core.mushroom_map_municipalities import MunicipalityReader


@unittest.skipIf(ogr is None, "GDAL Python bindings required")
class MunicipalityReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "municipalities.gpkg")
        dataset = ogr.GetDriverByName("GPKG").CreateDataSource(self.path)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        layer = dataset.CreateLayer("municipalities", srs, ogr.wkbMultiPolygon,
                                    options=["GEOMETRY_NAME=geom", "SPATIAL_INDEX=YES"])
        for name in ("name", "national_code"):
            layer.CreateField(ogr.FieldDefn(name, ogr.OFTString))
        shapes = [
            ("Outer", "001", "MULTIPOLYGON (((0 0,4 0,4 4,0 4,0 0),(1 1,1 2,2 2,2 1,1 1)))"),
            ("Enclave", "002", "MULTIPOLYGON (((1 1,2 1,2 2,1 2,1 1)))"),
            ("Neighbour", "003", "MULTIPOLYGON (((4 0,5 0,5 4,4 4,4 0)))"),
            ("Overlap", "004", "MULTIPOLYGON (((3 3,5 3,5 5,3 5,3 3)))"),
        ]
        for name, code, wkt in shapes:
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField("name", name)
            feature.SetField("national_code", code)
            feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
            layer.CreateFeature(feature)
        feature = layer = dataset = None
        self.reader = MunicipalityReader(self.path, edition="test")

    def tearDown(self):
        self.reader.close()
        self.temp.cleanup()

    def test_interior_and_enclave(self):
        self.assertEqual(self.reader.lookup(.5, .5)["name"], "Outer")
        self.assertEqual(self.reader.lookup(1.5, 1.5)["name"], "Enclave")

    def test_boundary_overlap_and_no_coverage(self):
        for point in ((1, 4), (1, 1), (3.5, 3.5)):
            result = self.reader.lookup(*point)
            self.assertEqual(result["status"], "ambiguous")
            self.assertNotIn("name", result)
        self.assertEqual(self.reader.lookup(40, 40)["status"], "not_covered")

    def test_near_boundary_is_not_rounded(self):
        self.assertEqual(self.reader.lookup(1, 4 - 1e-8)["name"], "Outer")
        self.assertEqual(self.reader.lookup(1, 4 + 1e-8)["name"], "Neighbour")

    def test_cache_is_bounded_and_results_are_independent(self):
        self.reader.lookup(.5, .5)["name"] = "mutated"
        self.assertEqual(self.reader.lookup(.5, .5)["name"], "Outer")
        for i in range(150):
            self.reader.lookup(40, i / 100)
        self.assertEqual(len(self.reader._cache), 128)

    def test_invalid_points(self):
        for point in ((True, 0), (float("nan"), 0), (91, 0), (0, 181), ("1", 2)):
            with self.assertRaises(ValueError):
                self.reader.lookup(*point)


if __name__ == "__main__":
    unittest.main()
