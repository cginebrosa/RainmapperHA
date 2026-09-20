"""Small MFE-shaped fixtures: exact lookup, no invented hosts, bounded I/O."""
import json
from hashlib import sha256
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
try:
    from osgeo import ogr, osr
except ImportError:
    ogr = osr = None
from rainmapper_core.mushroom_map_forest import ForestReader, prepare_index


@unittest.skipIf(ogr is None,'GDAL required')
class ForestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)/'forest.shp'
        ds = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(self.source))
        crs = osr.SpatialReference(); crs.ImportFromEPSG(25830)
        layer = ds.CreateLayer('forest',crs,ogr.wkbPolygon)
        for name in ['Poligon','FormArbol',*[f'Especie{i}' for i in range(1,4)],*[f'n_sp{i}' for i in range(1,4)]]:
            layer.CreateField(ogr.FieldDefn(name,ogr.OFTString))
        for idx,wkt in enumerate(['POLYGON ((0 0,4 0,4 4,0 4,0 0),(1 1,1 2,2 2,2 1,1 1))',
                                  'POLYGON ((1 1,2 1,2 2,1 2,1 1))',
                                  'POLYGON ((3 3,5 3,5 5,3 5,3 3))']):
            f=ogr.Feature(layer.GetLayerDefn());f.SetField('Poligon',str(idx));f.SetField('FormArbol','Forest')
            if idx!=1:
                f.SetField('Especie1','Quercus ilex');f.SetField('n_sp1','45')
                f.SetField('Especie2','Unknown taxon');f.SetField('n_sp2','999')
            f.SetGeometry(ogr.CreateGeometryFromWkt(wkt));layer.CreateFeature(f)
        f=layer=ds=None
        self.index=Path(self.tmp.name)/'index.sqlite'
        self.catalog=Path(self.tmp.name)/'catalog.json'
        self.catalog.write_text(json.dumps({'catalogs':{'host_taxa':[{'id':'host_quercus_ilex','scientific_name':'Quercus ilex','common_names':{'es':['Encina']}}]}}))
        prepare_index(self.source,self.index)
        self.reader=self.open(self.index)

    def open(self,index):
        r=ForestReader(index,catalogs=self.catalog);self.addCleanup(r.close)
        r._transform=Mock(TransformPoint=lambda lon,lat:(lon,lat,0))
        return r

    def test_area_preserving_ring_repair_is_cached_without_changing_source(self):
        before=self.source.read_bytes()
        repaired=Mock()
        repaired.IsEmpty.return_value=False;repaired.IsValid.return_value=True
        repaired.GetGeometryType.return_value=ogr.wkbPolygon
        repaired.WkbSize.return_value=100;repaired.GetArea.return_value=16
        invalid=Mock();invalid.IsEmpty.return_value=False;invalid.IsValid.return_value=False
        invalid.WkbSize.return_value=100;invalid.GetArea.return_value=16
        invalid.MakeValid.return_value=repaired
        self.assertIs(self.reader._valid_geometry(invalid,('source',99)),repaired)
        self.assertIs(self.reader._valid_geometry(invalid,('source',99)),repaired)
        invalid.MakeValid.assert_called_once()
        self.assertEqual(self.source.read_bytes(),before)
        repaired.GetArea.return_value=17
        self.assertIsNone(self.reader._valid_geometry(invalid,('source',100)))

    def test_names_codes_holes_and_no_inferred_absence(self):
        r=self.reader
        result=r.lookup(.5,.5)
        self.assertEqual(result['items'][0],{'label':'Encina','labels':{'es':'Encina'},'scientific_name':'Quercus ilex','code':'45','host_id':'host_quercus_ilex'})
        self.assertEqual(result['items'][1]['label'],'Unknown taxon')
        self.assertIsNone(result['items'][1]['host_id'])
        self.assertFalse(result['exhaustive'])
        self.assertEqual(r.lookup(1.5,1.5)['status'],'no_trees_recorded')
        self.assertEqual(r.lookup(1,1)['status'],'ambiguous')
        self.assertEqual(r.lookup(3.5,3.5)['status'],'ambiguous')
        self.assertEqual(r.lookup(8,8)['status'],'not_covered')

    def polygon(self, coordinates):
        # Fixture coordinates are small projected metres; use an identity
        # transform so exact intersection areas can be asserted.
        crs = osr.SpatialReference(); crs.ImportFromEPSG(25830)
        self.reader._transform = osr.CoordinateTransformation(crs, crs)
        return self.reader.lookup_polygon({'type':'Polygon','coordinates':coordinates})

    def test_polygon_unions_hosts_and_preserves_holes_and_positive_area(self):
        result = self.polygon([[[0,0],[3,0],[3,3],[0,3],[0,0]]])
        self.assertEqual(result['host_ids'], ['host_quercus_ilex'])
        self.assertEqual([p['polygon_id'] for p in result['polygons']], ['0', '1'])
        self.assertEqual([p['intersection_m2'] for p in result['polygons']], [8, 1])
        self.assertEqual(len(result['items']), 2)  # unknown taxa remain visible
        self.assertFalse(result['exhaustive'])
        hole = self.polygon([[[1.1,1.1],[1.9,1.1],[1.9,1.9],[1.1,1.9],[1.1,1.1]]])
        self.assertEqual(hole['status'], 'no_trees_recorded')
        self.assertEqual(hole['host_ids'], [])

    def test_polygon_resource_limit_returns_no_partial_host_list(self):
        with patch('rainmapper_core.mushroom_map_forest.MAX_CANDIDATES', 1):
            result = self.polygon([[[0,0],[5,0],[5,5],[0,5],[0,0]]])
        self.assertEqual(result['status'], 'resource_limit')
        self.assertNotIn('host_ids', result)

    def test_polygon_hole_excludes_forest_even_inside_bounding_box(self):
        result = self.polygon([[[-1,-1],[6,-1],[6,6],[-1,6],[-1,-1]],
                               [[-.5,-.5],[-.5,5.5],[5.5,5.5],[5.5,-.5],[-.5,-.5]]])
        self.assertEqual(result['status'], 'not_covered')

    def test_gdal_self_touching_ring_preserves_both_lobes(self):
        geom=ogr.CreateGeometryFromWkt('POLYGON ((0 0,2 0,2 2,0 2,0 0,-2 0,-2 -2,0 -2,0 0))')
        original=bytes(geom.ExportToWkb())
        self.assertFalse(geom.IsValid())
        repaired=self.reader._valid_geometry(geom,('source',99))
        self.assertIsNotNone(repaired)
        self.assertTrue(repaired.IsValid())
        self.assertAlmostEqual(repaired.GetArea(),geom.GetArea())
        for x,y in [(1,1),(-1,-1)]:
            point=ogr.Geometry(ogr.wkbPoint);point.AddPoint_2D(x,y)
            self.assertTrue(repaired.Contains(point))
        self.assertEqual(bytes(geom.ExportToWkb()),original)

    def test_catalog_edits_refresh_names_without_reloading_geometry(self):
        r=self.reader
        before=r.lookup(.5,.5)['catalog_revision']
        self.assertEqual(before,sha256(self.catalog.read_bytes()).hexdigest()[:20])
        with patch.object(r,'_lookup',side_effect=AssertionError('cached geometry must survive catalogue edits')):
            data=json.loads(self.catalog.read_text())
            data['catalogs']['host_taxa'].append({'scientific_name':' Unknown Taxon ', 'common_names':{'es':['Nuevo nombre']}})
            replacement=self.catalog.with_suffix('.new')
            replacement.write_text(json.dumps(data));replacement.replace(self.catalog)
            self.assertEqual(r.lookup(.5,.5)['items'][1]['label'],'Nuevo nombre')
            self.assertNotEqual(r.lookup(.5,.5)['catalog_revision'],before)
            self.assertEqual(r.lookup(.5,.5)['catalog_revision'],sha256(self.catalog.read_bytes()).hexdigest()[:20])
            data['catalogs']['host_taxa'][1]['common_names']['es']=['Nombre actualizado']
            self.catalog.write_text(json.dumps(data))
            self.assertEqual(r.lookup(.5,.5)['items'][1]['label'],'Nombre actualizado')
            data['catalogs']['host_taxa'].pop()
            self.catalog.write_text(json.dumps(data))
            self.assertEqual(r.lookup(.5,.5)['items'][1]['label'],'Unknown taxon')

    def test_localized_names_refresh_without_reloading_geometry(self):
        self.reader.lookup(.5,.5)
        data=json.loads(self.catalog.read_text())
        names={'es':['Encina'],'ca':['Alzina'],'en':['Holm oak']}
        data['catalogs']['host_taxa'][0]['common_names']=names
        self.catalog.write_text(json.dumps(data))
        with patch.object(self.reader,'_lookup',side_effect=AssertionError('keep cached geometry')):
            item=self.reader.lookup(.5,.5)['items'][0]
            self.assertEqual(item['labels'],{'es':'Encina','ca':'Alzina','en':'Holm oak'})
            self.assertEqual(item['label'],'Encina')
            self.assertEqual(item['host_id'],'host_quercus_ilex')
            item['labels']['en']='caller mutation'
            self.assertEqual(self.reader.lookup(.5,.5)['items'][0]['labels']['en'],'Holm oak')
            names['en']=['Edited English name']
            self.catalog.write_text(json.dumps(data))
            self.assertEqual(self.reader.lookup(.5,.5)['items'][0]['labels']['en'],'Edited English name')
            del names['ca']
            self.catalog.write_text(json.dumps(data))
            self.assertNotIn('ca',self.reader.lookup(.5,.5)['items'][0]['labels'])

    def test_incomplete_catalog_save_uses_scientific_names_and_recovers(self):
        r=self.reader
        original=self.catalog.read_text()
        r.lookup(.5,.5)
        self.catalog.write_text('{')
        result=r.lookup(.5,.5)
        self.assertEqual(result['status'],'available')
        self.assertEqual(result['items'][0]['label'],'Quercus ilex')
        self.assertEqual(result['catalog_status'],'unavailable')
        self.assertIsNone(result['items'][0]['host_id'])
        self.assertEqual(result['items'][0]['labels'],{})
        self.catalog.write_text(original)
        self.assertEqual(r.lookup(.5,.5)['items'][0]['label'],'Encina')

    def test_explicit_aliases_refresh_cached_points_and_exact_names_win(self):
        r=self.reader
        r.lookup(.5,.5)
        data=json.loads(self.catalog.read_text())
        data['catalogs']['host_taxa'].append({'id':'host_other','scientific_name':'Other taxon',
            'common_names':{'es':['Otro árbol']},'gis_aliases':[' UNKNOWN TAXON ','Quercus ilex']})
        self.catalog.write_text(json.dumps(data))
        with patch.object(r,'_lookup',side_effect=AssertionError('do not reload geography')):
            self.assertEqual([i['label'] for i in r.lookup(.5,.5)['items']],['Encina','Otro árbol'])
            self.assertEqual(r.lookup(.5,.5)['items'][1]['host_id'],'host_other')
            data['catalogs']['host_taxa'][1]['gis_aliases']=['Unknown']
            self.catalog.write_text(json.dumps(data))
            self.assertEqual(r.lookup(.5,.5)['items'][1]['label'],'Unknown taxon')
            self.assertIsNone(r.lookup(.5,.5)['items'][1]['host_id'])

    def test_colliding_aliases_do_not_choose_a_taxon_even_without_a_label(self):
        data=json.loads(self.catalog.read_text())
        data['catalogs']['host_taxa'] += [
            {'scientific_name':'Other taxon','common_names':{'es':['Otro árbol']},'gis_aliases':['Unknown taxon']},
            {'scientific_name':'Another taxon','gis_aliases':['unknown taxon']}]
        self.catalog.write_text(json.dumps(data))
        self.assertEqual(self.reader.lookup(.5,.5)['items'][1]['label'],'Unknown taxon')

    def test_functional_group_alias_and_ambiguous_scientific_names(self):
        data=json.loads(self.catalog.read_text())
        data['catalogs']['host_taxa'] += [
            {'scientific_name':None,'rank':'functional_group','common_names':{'es':['Grupo cartográfico']},
             'gis_aliases':['Unknown taxon']},
            {'scientific_name':'QUERCUS ILEX','common_names':{'es':['Etiqueta duplicada']}}]
        self.catalog.write_text(json.dumps(data))
        self.assertEqual([i['label'] for i in self.reader.lookup(.5,.5)['items']],
                         ['Quercus ilex','Grupo cartográfico'])

    def test_limits_checked_before_materializing(self):
        with patch('rainmapper_core.mushroom_map_forest.MAX_GEOMETRY',0),patch.object(self.reader,'_layer') as layer:
            self.assertEqual(self.reader.lookup(.5,.5)['status'],'resource_limit')
            layer.GetFeature.assert_not_called()

    def test_cache_and_source_changes(self):
        r=self.reader
        r.lookup(.5,.5)['items'].clear()
        self.assertEqual(len(r.lookup(.5,.5)['items']),2)
        for i in range(70): r.lookup(8,i/100)
        self.assertEqual(len(r._cache),64)
        stat=self.source.stat();os.utime(self.source,ns=(stat.st_atime_ns,stat.st_mtime_ns+1000000000))
        self.assertEqual(r.lookup(.5,.5)['reason'],'dataset_changed')
        with self.assertRaises(ValueError): self.open(self.index)

    def test_preparation_is_explicit_and_invalid_points_rejected(self):
        with self.assertRaises(ValueError): prepare_index(self.source,self.index)
        for p in [(True,0),(91,0),(0,float('nan'))]:
            with self.assertRaises(ValueError): self.reader.lookup(*p)

    def test_parts_preserve_lookup_and_do_not_read_large_original(self):
        index=Path(self.tmp.name)/'parts.sqlite'
        with patch('rainmapper_core.mushroom_map_forest.MAX_GEOMETRY',1):
            prepare_index(self.source,index)
        r=self.open(index)
        with patch.object(r,'_layer') as layer:
            for point in [(.5,.5),(1,1),(1.5,1.5),(3.5,3.5),(8,8)]:
                self.assertEqual(r.lookup(*point),self.reader.lookup(*point))
            layer.GetFeature.assert_not_called()

    def test_polygon_parts_equal_full_geometry_without_reading_large_original(self):
        index=Path(self.tmp.name)/'polygon-parts.sqlite'
        with patch('rainmapper_core.mushroom_map_forest.MAX_GEOMETRY',1):
            prepare_index(self.source,index)
        expected=self.polygon([[[0,0],[3,0],[3,3],[0,3],[0,0]]])
        reader=self.open(index)
        reader._transform=self.reader._transform
        with patch.object(reader,'_layer') as layer:
            actual=reader.lookup_polygon({'type':'Polygon','coordinates':[[[0,0],[3,0],[3,3],[0,3],[0,0]]]})
            layer.GetFeature.assert_not_called()
        self.assertEqual(actual,expected)

if __name__=='__main__': unittest.main()
