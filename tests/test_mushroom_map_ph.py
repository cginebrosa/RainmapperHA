import copy
import json
from pathlib import Path
import tempfile
import unittest

try:
    from osgeo import gdal, osr
    import numpy as np
except ImportError:
    gdal = None

from rainmapper_core.mushroom_map_ph import OpenLandMapPHReader, distance_m


@unittest.skipIf(gdal is None, 'GDAL Python bindings required')
class OpenLandMapPHTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root/'manifest.json'
        self.meta = {'schema':'openlandmap_ph_local_v1','source_id':'openlandmap_soildb_ph',
                     'edition':'test','period':'2020-2022','depth_cm':[0,30], 'scale':0.1,
                     'interval_probability':0.68,'nearest_max_distance_m':1000,'assets':[]}
        self.gt = (2,0.001,0,42.01,0,-0.001)
        self.lat,self.lon = 42.0065,2.0035
        for statistic,value in [('mean',67),('p0.16',55),('p0.84',79)]:
            self.raster(statistic, np.full((8,8),value,dtype=np.uint8))
        self.save()

    def raster(self, statistic, values):
        path = self.root/(statistic+'.tif')
        ds = gdal.GetDriverByName('GTiff').Create(str(path),8,8,1,gdal.GDT_Byte)
        ds.SetGeoTransform(self.gt)
        srs = osr.SpatialReference(); srs.ImportFromEPSG(4326); ds.SetProjection(srs.ExportToWkt())
        band = ds.GetRasterBand(1); band.SetNoDataValue(255); band.WriteArray(values)
        band=ds=None
        stat=path.stat()
        self.meta['assets']=[a for a in self.meta['assets'] if a['statistic']!=statistic]
        self.meta['assets'].append({'path':path.name,'region':'test','statistic':statistic,
            'resolution_m':30 if statistic=='mean' else 120, 'width':8,'height':8,'transform':list(self.gt),
            'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns})

    def save(self):
        self.path.write_text(json.dumps(self.meta))

    def reader(self):
        reader=OpenLandMapPHReader(self.path); self.addCleanup(reader.close); return reader

    def test_local_mean_and_uncertainty_remain_distinct(self):
        row=self.reader().lookup(self.lat,self.lon)
        self.assertEqual((row['estimate'],row['lower'],row['upper']),(6.7,5.5,7.9))
        self.assertEqual(row['lookup']['method'],'point')
        self.assertEqual(row['lookup']['distance_m'],0)
        self.assertEqual(row['depth_cm'],[0,30])
        self.assertEqual(row['interval_probability'],0.68)

    def test_nearest_valid_mean_reports_real_distance_and_its_interval(self):
        values=np.full((8,8),255,dtype=np.uint8);values[3,4]=65;values[7,7]=73
        self.raster('mean',values);self.save()
        row=self.reader().lookup(self.lat,self.lon)
        self.assertEqual(row['estimate'],6.5)
        self.assertEqual(row['lookup']['method'],'nearest')
        self.assertAlmostEqual(row['lookup']['distance_m'],distance_m(self.lat,self.lon,42.0065,2.0045),delta=0.1)
        self.assertEqual((row['lower'],row['upper']),(5.5,7.9))

    def test_radius_is_configurable_and_search_does_not_expand(self):
        values=np.full((8,8),255,dtype=np.uint8);values[3,4]=65
        self.raster('mean',values);self.meta['nearest_max_distance_m']=20;self.save()
        self.assertEqual(self.reader().lookup(self.lat,self.lon)['status'],'no_data')

    def test_no_data_does_not_use_zero_or_invalid_raw_values(self):
        for raw in (0,141,255):
            with self.subTest(raw=raw):
                self.raster('mean',np.full((8,8),raw,dtype=np.uint8));self.save()
                row=self.reader().lookup(self.lat,self.lon)
                self.assertIsNone(row['estimate'])
                self.assertEqual(row['status'],'no_data')

    def test_missing_interval_keeps_usable_mean(self):
        self.raster('p0.16',np.full((8,8),255,dtype=np.uint8));self.save()
        row=self.reader().lookup(self.lat,self.lon)
        self.assertEqual(row['status'],'partial');self.assertEqual(row['estimate'],6.7)
        self.assertIsNone(row['lower'])

    def test_no_invented_containment_across_two_resolutions(self):
        self.raster('mean',np.full((8,8),80,dtype=np.uint8));self.save()
        row=self.reader().lookup(self.lat,self.lon)
        self.assertEqual((row['estimate'],row['upper']),(8.0,7.9))

    def test_outside_crop_has_no_remote_fallback(self):
        self.assertEqual(self.reader().lookup(0,0)['status'],'no_data')

    def test_modified_raster_is_not_used_from_cache(self):
        reader=self.reader();reader.lookup(self.lat,self.lon)
        path=self.root/'mean.tif';path.write_bytes(path.read_bytes()+b'x')
        with self.assertRaisesRegex(ValueError,'ph_asset_changed'):
            reader.lookup(self.lat,self.lon)

    def test_manifest_escape_cardinality_and_radius_guards(self):
        original=copy.deepcopy(self.meta)
        for field,value in [('nearest_max_distance_m',5001),('assets',original['assets']*9)]:
            self.meta=copy.deepcopy(original);self.meta[field]=value;self.save()
            with self.assertRaises(ValueError):self.reader()
        outside=self.root/'outside.json';outside.write_text('{}')
        self.meta=copy.deepcopy(original);self.meta['assets'][0]['path']='outside.json';self.save()
        with self.assertRaisesRegex(ValueError,'invalid_ph_asset_path'):self.reader()

    def test_invalid_coordinates_rejected(self):
        reader=self.reader()
        for lat,lon in [(True,2),(float('nan'),2),(91,2),(42,181)]:
            with self.assertRaises(ValueError):reader.lookup(lat,lon)


if __name__ == '__main__':
    unittest.main()
