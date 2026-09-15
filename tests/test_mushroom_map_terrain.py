import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

try:
    from osgeo import gdal, osr
    import numpy as np
except ImportError:
    gdal = osr = np = None

from rainmapper_core.mushroom_map_terrain import (
    TerrainReader, SCHEMA, SOIL_CRS, SOIL_ORIGIN, PH_DEPTHS, PH_QUANTILES, add_asset,
)
from rainmapper_core import mushroom_soilgrids as soilgrids
from rainmapper_core.mushroom_soil_water_state import available_water_capacity_mm


@unittest.skipIf(gdal is None, "GDAL Python bindings required")
class TerrainReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.index = self.root/"terrain.sqlite"
        self.db = sqlite3.connect(self.index)
        self.db.executescript(SCHEMA)
        self.readers = []
        self.lat, self.lon = 42.0, 2.0
        x, y = self.project(SOIL_CRS)
        col, row = int((x-SOIL_ORIGIN[0])//250), int((y-SOIL_ORIGIN[1])//250)
        self.tx, self.ty = col//512, row//512
        self.px, self.py = 512+col%512, 511-row%512
        gt = (SOIL_ORIGIN[0]+(self.tx-1)*128000, 250, 0, SOIL_ORIGIN[1]+(self.ty+1)*128000, 0, -250)
        for low, high in PH_DEPTHS:
            for q, raw in zip(PH_QUANTILES, (43, 63, 80)):
                coverage = f"phh2o_{low}-{high}cm_{q}"
                asset = self.raster(coverage, "ph", SOIL_CRS, gt, 1024, 512, raw, 0, self.px, self.py)
                self.db.execute("INSERT INTO tile_layers VALUES(?,?,?,?,?,?)", (coverage, self.tx, self.ty, asset, 512, 0))
        dx, dy = self.project("EPSG:3857")
        dem_gt = (dx-25, 25, 0, dy+25, 0, -25)
        self.raster("regional", "dem", "EPSG:3857", dem_gt, 3, 3, -9999, 0, 1, 1)
        self.raster("national", "dem", "EPSG:3857", dem_gt, 3, 3, 600, 10, 1, 1)
        self.db.commit()

    def project(self, crs):
        source = osr.SpatialReference(); source.ImportFromEPSG(4326)
        target = osr.SpatialReference(); target.SetFromUserInput(crs)
        for srs in (source, target): srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        return osr.CoordinateTransformation(source, target).TransformPoint(self.lon, self.lat)[:2]

    def raster(self, name, kind, crs, gt, width, height, value, priority, col, row):
        path = self.root/(name+".tif")
        ds = gdal.GetDriverByName("GTiff").Create(str(path), width, height, 1, gdal.GDT_Int16, options=["COMPRESS=DEFLATE"])
        ds.SetGeoTransform(gt)
        srs = osr.SpatialReference(); srs.SetFromUserInput(crs); ds.SetProjection(srs.ExportToWkt())
        band = ds.GetRasterBand(1); band.SetNoDataValue(-9999); band.Fill(-9999)
        band.WriteArray(np.array([[value]], dtype=np.int16), col, row)
        band = ds = None
        return add_asset(self.db, "fixture", self.root, path.name, kind=kind, source=name,
            crs=crs, transform=gt, width=width, height=height, priority=priority)

    def reader(self):
        reader = TerrainReader(str(self.index), {"fixture": str(self.root)})
        self.readers.append(reader)
        return reader

    def tearDown(self):
        for reader in self.readers: reader.close()
        self.db.close()
        self.temp.cleanup()

    def test_native_window_scaling_and_dem_nodata_fallback(self):
        result = self.reader().lookup(self.lat, self.lon)
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["elevation"]["source_id"], "national")
        self.assertEqual(result["elevation"]["value_m"], 600)
        self.assertEqual([r["median"] for r in result["ph"]["depths"]], [6.3]*3)
        self.assertEqual(result["ph"]["depths"][0]["lower"], 4.3)

    def test_missing_quantile_stays_partial(self):
        self.db.execute("DELETE FROM tile_layers WHERE coverage='phh2o_0-5cm_Q0.5'")
        self.db.commit()
        result = self.reader().lookup(self.lat, self.lon)
        self.assertEqual(result["ph"]["status"], "partial")
        self.assertIsNone(result["ph"]["depths"][0]["median"])
        self.assertEqual(result["elevation"]["status"], "available")

    def test_exact_northern_pixel_edge_uses_pixel_below(self):
        reader = self.reader()
        x, _ = self.project(SOIL_CRS)
        y = SOIL_ORIGIN[1]+(self.ty+1)*128000-self.py*250
        with patch.object(reader, "_project", return_value=(x, y)):
            self.assertEqual(reader._ph(self.lat, self.lon)["depths"][0]["median"], 6.3)

    def test_changed_asset_is_error_even_with_cached_dataset(self):
        reader = self.reader()
        self.assertEqual(reader.lookup(self.lat, self.lon)["ph"]["status"], "available")
        with (self.root/"phh2o_0-5cm_Q0.5.tif").open("ab") as handle: handle.write(b"changed")
        result = reader.lookup(self.lat, self.lon)
        self.assertEqual(result["ph"]["status"], "unavailable")
        self.assertEqual(result["elevation"]["status"], "available")

    def test_zero_ph_is_no_data(self):
        path = self.root/"phh2o_0-5cm_Q0.5.tif"
        ds = gdal.Open(str(path), gdal.GA_Update)
        ds.GetRasterBand(1).WriteArray(np.array([[0]], dtype=np.int16), self.px, self.py)
        ds = None
        stat = path.stat()
        self.db.execute("UPDATE assets SET bytes=?,mtime_ns=? WHERE path=?", (stat.st_size,stat.st_mtime_ns,path.name))
        self.db.commit()
        result = self.reader().lookup(self.lat, self.lon)
        self.assertIsNone(result["ph"]["depths"][0]["median"])
        self.assertEqual(result["ph"]["depths"][0]["status"], "partial")

    def test_no_coverage_and_invalid_input(self):
        reader = self.reader()
        self.assertEqual(reader.lookup(0, 0)["status"], "no_data")
        for lat,lon in ((True,0), (91,0), (0,181), (float("nan"),0)):
            with self.assertRaises(ValueError): reader.lookup(lat,lon)

    def test_dataset_handles_are_bounded(self):
        for i in range(20):
            self.raster(f"extra{i}", "dem", "EPSG:3857", (i*25,25,0,100,0,-25), 1,1,10,10,0,0)
        self.db.commit()
        reader = self.reader()
        for asset in reader._db.execute("SELECT * FROM assets WHERE path LIKE 'extra%'"):
            reader._read(asset,0,0)
        self.assertEqual(len(reader._datasets),16)

    def water_layers(self, *, zero_coverage=None):
        gt = (SOIL_ORIGIN[0]+(self.tx-1)*128000,250,0,SOIL_ORIGIN[1]+(self.ty+1)*128000,0,-250)
        raw_values = {}
        for top, bottom, label in soilgrids.DEPTHS:
            for index, (_stored, quantile) in enumerate(soilgrids.QUANTILES):
                for prop, base in zip(soilgrids.PROPERTIES, (400,300,100)):
                    coverage = soilgrids.coverage_id(prop,label,quantile)
                    raw = 0 if coverage == zero_coverage else base+index*10
                    asset = self.raster(coverage,"water",SOIL_CRS,gt,1024,512,raw,0,self.px,self.py)
                    self.db.execute("INSERT INTO tile_layers VALUES(?,?,?,?,?,?)", (coverage,self.tx,self.ty,asset,512,0))
                    raw_values[coverage] = raw
        self.db.commit()
        return raw_values

    def test_water_context_matches_existing_single_cell_aggregation_and_capacity(self):
        raw_values = self.water_layers()
        reader = self.reader()
        with patch.object(soilgrids, "_command", side_effect=AssertionError("CLI during point read")), \
             patch.object(soilgrids, "file_sha256", side_effect=AssertionError("full hash during point read")):
            actual = reader.soil_water_context(self.lat,self.lon)
        self.assertEqual(actual["contract_id"],"point_soilgrids_water_context_v1")
        self.assertEqual(actual["source"]["spatial_support"],"native_cell")
        self.assertEqual(actual["quality"]["covered_layer_count"],54)
        self.assertLess(len(json.dumps(actual).encode()), 8192)
        self.assertLessEqual(len(reader._datasets),16)
        self.assertEqual(actual, reader.soil_water_context(self.lat,self.lon))
        col, row = self.tx*512+self.px-512, self.ty*512+511-self.py
        x,y = SOIL_ORIGIN[0]+col*250, SOIL_ORIGIN[1]+row*250
        polygons = [[[(x+50,y+50),(x+150,y+50),(x+150,y+150),(x+50,y+150),(x+50,y+50)]]]
        tile = soilgrids.tile_id(self.tx,self.ty)
        manifest = {"coverages": {cov:{"tiles": {tile:{"normalized_path":cov+".tif","normalized_sha256":"fixture"}}} for cov in raw_values}}
        # The oracle is the unchanged polygon aggregator. Raster decoding is
        # supplied independently from fixture values; real 1x1 I/O is above.
        with patch.object(soilgrids,"load_manifest",return_value=manifest), \
             patch.object(soilgrids,"transform_geometry",return_value=polygons), \
             patch.object(soilgrids,"manifest_sha256",return_value="fixture-manifest"), \
             patch.object(soilgrids,"_registered_tile_is_valid",return_value=True), \
             patch.object(soilgrids,"_read_xyz_window",side_effect=lambda path,**kw: {(col,row):raw_values[path.stem]}):
            expected = soilgrids.aggregate_geometry(self.root,{"type":"fixture"})
        self.assertEqual(actual["depths"],expected["depths"])
        self.assertEqual(actual["status"],expected["status"])
        for depth in (30,60,100):
            self.assertEqual(available_water_capacity_mm(actual,profile_depth_cm=depth),
                             available_water_capacity_mm(expected,profile_depth_cm=depth))
            self.assertEqual(available_water_capacity_mm(actual,profile_depth_cm=depth)["capacity_mm"],2*depth)

    def test_water_missing_quantile_rejects_capacity_without_changing_ph(self):
        self.water_layers()
        self.db.execute("DELETE FROM tile_layers WHERE coverage='wv0033_0-5cm_Q0.5'")
        self.db.commit()
        reader = self.reader()
        result = reader.soil_water_context(self.lat,self.lon)
        self.assertEqual(result["status"],"partial")
        self.assertEqual(result["coverage_fraction"],0)
        self.assertEqual(result["quality"]["covered_layer_count"],53)
        self.assertIn("missing_cache_assets",result["quality"]["exclusion_reasons"])
        self.assertTrue(all(v is None for v in result["depths"][0]["area_weighted"]["Q0.50"].values()))
        with self.assertRaises(ValueError): available_water_capacity_mm(result,profile_depth_cm=30)
        self.assertEqual(reader.lookup(self.lat,self.lon)["ph"]["status"],"available")

    def test_zero_water_is_ineligible_but_raw_pixel_is_preserved(self):
        coverage = "wv0010_0-5cm_Q0.5"
        self.water_layers(zero_coverage=coverage)
        reader = self.reader()
        self.assertEqual(reader.soil_water_context(self.lat,self.lon)["status"],"partial")
        asset = reader._soil_asset(coverage,reader._soil_pixel(self.lat,self.lon))
        self.assertEqual(reader._read(asset,self.px,self.py),0)

    def test_water_empty_old_index_changed_asset_and_exact_edge(self):
        reader = self.reader()
        self.assertEqual(reader.soil_water_context(self.lat,self.lon)["status"],"no_coverage")
        self.water_layers()
        x,_ = self.project(SOIL_CRS)
        y = SOIL_ORIGIN[1]+(self.ty+1)*128000-self.py*250
        with patch.object(reader,"_project",return_value=(x,y)):
            self.assertEqual(reader.soil_water_context(self.lat,self.lon)["status"],"complete")
        with (self.root/"wv0033_0-5cm_Q0.5.tif").open("ab") as handle: handle.write(b"changed")
        with self.assertRaisesRegex(ValueError,"terrain_asset_changed"):
            reader.soil_water_context(self.lat,self.lon)


if __name__ == "__main__": unittest.main()
