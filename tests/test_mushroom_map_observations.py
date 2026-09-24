"""Observation map read contract: bounded, independent of historical dates."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from rainmapper_core import mushroom_map_observations as overlay
from rainmapper_core.lunar_phase import lunar_phase


class ObservationOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for target in (mock.patch.object(overlay.mushroom_paths,'mushroom_data_dir',return_value=self.root),
                       mock.patch.object(overlay.mushroom_known_sites,'persistent_path',return_value=self.root/'sites.json'),
                       mock.patch.object(overlay,'_cache',None)):
            target.start();self.addCleanup(target.stop)
        self.rows=[dict(observation_id=f'o{i}',species_id='sp',observed_at=day,location={'lat':42,'lon':1.9},
                        micro_area_id='m',observer={'name':'<b>Observer</b>'},flush_abundance='abundant',
                        site_context={'observed_host_ids':['pine'],'observed_forest_type_ids':['forest']},
                        source={'notes':'PRIVATE NOTE'},media=['PRIVATE MEDIA']) for i,day in enumerate(('2020-01-01','2030-01-01','2030-01-01'))]
        self.write('mushroom_observations.json',{'observations':self.rows})
        self.write('mushroom_profiles.json',{'species_profiles':[{'species_id':'sp','scientific_name':'Species name'}]})
        self.write('mushroom_reference_catalogs.json',{'catalogs':{'host_taxa':[{'id':'pine','scientific_name':'Pinus','common_names':{'es':['Pino'],'ca':['Pi'],'en':[]}}],
          'forest_types':[{'id':'forest','label':{'es':'Bosque','en':'Forest','ca':'Bosc'}}],
          'observation_flush_abundance':[{'id':'abundant','label':{'es':'Abundante'},'prediction_favorable':1}]}})
        self.write('sites.json',{'areas':[{'area_id':'a','name':'Area'}],'micro_areas':[{'micro_area_id':'m','area_id':'a','name':'Micro'}]})

    def write(self,name,data):
        (self.root/name).write_text(json.dumps(data))

    def test_counts_points_and_details_preserve_duplicates_and_dates(self):
        index=overlay.response('species',{})
        self.assertEqual(index['species'],[{'id':'sp','name':'Species name','count':3,'mapped_count':3,'favorable_count':3}])
        points=overlay.response('points',{'species_id':'sp','reference_date':'2025-01-01'})
        self.assertEqual(len(points['points']),3)
        self.assertEqual([r[3] for r in points['points']],['2020-01-01','2030-01-01','2030-01-01'])
        self.assertEqual([r[4] for r in points['points']],['abundant']*3)
        detail=overlay.response('detail',{'id':'o0','lang':'ca'})['observation']
        self.assertEqual((detail['area'],detail['microarea'],detail['forest']),('Area','Micro',['Bosc']))
        self.assertEqual(detail['hosts'],['Pi'])
        for lang,host,forest in (('es','Pino','Bosque'),('ca','Pi','Bosc'),('en','Pinus','Forest')):
            localized=overlay.response('detail',{'id':'o0','lang':lang})['observation']
            self.assertEqual(localized['hosts'],[host])
            self.assertEqual(localized['forest'],[forest])
        self.assertNotIn('PRIVATE',overlay.encode(detail).decode())
        self.assertNotIn('coordinates',detail)

    def test_invalid_coordinates_and_missing_fields(self):
        self.rows[0]['location']={'lat':True,'lon':1.9}
        self.rows[1]['location']={'lat':42,'lon':181}
        self.rows[2].pop('micro_area_id');self.rows[2]['site_context']={}
        self.write('mushroom_observations.json',{'observations':self.rows})
        self.assertEqual(overlay.response('species',{})['species'][0]['mapped_count'],1)
        row=overlay.response('detail',{'id':'o2'})['observation']
        self.assertEqual(row['microarea'],'');self.assertEqual(row['hosts'],[])

    def test_moon_uses_observation_date_only_and_is_detail_only(self):
        for action, params in (('species', {}), ('points', {'species_id':'sp'})):
            with mock.patch.object(overlay, 'lunar_phase', side_effect=AssertionError('detail only')):
                overlay.response(action, params)
        detail = overlay.response('detail', {'id':'o0', 'reference_date':'2025-09-21'})['observation']
        self.assertEqual(detail['moon'], lunar_phase('2020-01-01'))
        self.assertLess(len(overlay.encode(detail['moon'])), 300)
        self.rows[0]['observed_at'] = 'invalid'
        self.write('mushroom_observations.json', {'observations':self.rows})
        detail = overlay.response('detail', {'id':'o0'})['observation']
        self.assertIsNone(detail['moon'])
        self.assertEqual(detail['species'], 'Species name')

    def test_pagination_and_revision_reject_mixed_snapshots(self):
        with mock.patch.object(overlay,'PAGE_SIZE',2):
            first=overlay.response('points',{'species_id':'sp'})
            self.assertEqual(first['next_offset'],2)
            last=overlay.response('points',{'species_id':'sp','offset':'2','revision':first['revision']})
            self.assertEqual(len(last['points']),1);self.assertIsNone(last['next_offset'])
            self.rows.append({**self.rows[0],'observation_id':'new'})
            self.write('mushroom_observations.json',{'observations':self.rows})
            with self.assertRaisesRegex(overlay.ObservationError,'observations_changed'):
                overlay.response('points',{'species_id':'sp','revision':first['revision']})
        for offset in ('-1','999','x'):
            with self.assertRaisesRegex(overlay.ObservationError,'invalid_offset'):
                overlay.response('points',{'species_id':'sp','offset':offset})

    def test_source_and_response_limits(self):
        with mock.patch.object(overlay,'MAX_FILE_BYTES',5),self.assertRaisesRegex(overlay.ObservationError,'source_limit'):
            overlay.snapshot()
        with mock.patch.object(overlay,'MAX_RECORDS',2),self.assertRaisesRegex(overlay.ObservationError,'source_limit'):
            overlay.snapshot()
        with mock.patch.object(overlay,'MAX_RESPONSE_BYTES',10),self.assertRaisesRegex(overlay.ObservationError,'response_limit'):
            overlay.encode({'value':'long enough'})

    def test_favorable_table_uses_only_numeric_one_and_caches_catalog(self):
        catalog={'catalogs':{'observation_flush_abundance':[
            {'id':key,'prediction_favorable':value} for key,value in
            [('one',1),('float',1.0),('zero',0),('two',2),('string','1'),('boolean',True),('null',None)]]}}
        catalog['catalogs']['observation_flush_abundance'].append({'id':'missing'})
        self.write('mushroom_reference_catalogs.json',catalog)
        keys=['one','float','zero','two','string','boolean','null','missing','unknown','']
        rows=[{**self.rows[0],'observation_id':f'f{i}','flush_abundance':key} for i,key in enumerate(keys)]
        rows[0]['location']={}  # Counts include the favorable observation without a marker.
        self.write('mushroom_observations.json',{'observations':rows})
        initial=overlay.response('species',{})
        self.assertEqual(initial['abundance_favorable'],{k:int(k in ('one','float')) for k in keys[:-2]})
        self.assertEqual(initial['species'][0]['favorable_count'],2)
        self.assertEqual(initial['species'][0]['count'],10)
        self.assertEqual(initial['species'][0]['mapped_count'],9)
        with mock.patch.object(overlay,'_read',side_effect=AssertionError('Catalog must remain cached')):
            self.assertEqual(overlay.response('species',{}),initial)
            points=overlay.response('points',{'species_id':'sp'})
            overlay.response('detail',{'id':'f1'})
        self.assertNotIn('abundance_favorable',points)
        self.assertEqual([r[4] for r in points['points']],keys[1:])
        catalog['catalogs']['observation_flush_abundance'][0]['prediction_favorable']=0
        self.write('mushroom_reference_catalogs.json',catalog)
        with self.assertRaisesRegex(overlay.ObservationError,'observations_changed'):
            overlay.response('points',{'species_id':'sp','revision':initial['revision']})
        self.assertEqual(overlay.response('species',{})['species'][0]['favorable_count'],1)

    def test_abundance_table_is_bounded_before_building(self):
        with mock.patch.object(overlay,'MAX_ABUNDANCES',0),self.assertRaisesRegex(overlay.ObservationError,'source_limit'):
            overlay.response('species',{})

    def test_accepted_gis_is_displayed_with_manual_values_and_provenance(self):
        self.rows[0]['site_context']={'observed_host_ids':['manual','pine'], 'gis_recovery': {
            'version':1,'location':self.rows[0]['location'],
            'values':{'host_ids':['pine','gis_only'],'forest_type_ids':['forest']},
            'sources':{'host_ids':['mfe25'],'forest_type_ids':['mvc50']}}}
        self.write('mushroom_observations.json',{'observations':self.rows})
        row=overlay.response('detail',{'id':'o0','lang':'ca'})['observation']
        self.assertEqual(row['hosts'],['manual','Pi','gis_only'])
        self.assertEqual(row['forest'],['Bosc'])
        self.assertEqual(row['gis'],{'hosts':[2],'forest':[0]})
        # Moving coordinates invalidates the stored GIS evidence, not field notes.
        self.rows[0]['location']={'lat':43,'lon':1.9}
        self.write('mushroom_observations.json',{'observations':self.rows})
        row=overlay.response('detail',{'id':'o0'})['observation']
        self.assertEqual(row['hosts'],['manual','Pino'])
        self.assertEqual(row['forest'],[])
        self.assertEqual(row['gis'],{'hosts':[],'forest':[]})

    def test_unaccepted_or_invalid_gis_is_not_inferred(self):
        self.rows[0]['site_context']={'gis_recovery': {'version':1,'location':self.rows[0]['location'],
            'values':{'host_ids':'invalid'},'forest':{'items':[{'host_id':'not_accepted'}]}}}
        self.write('mushroom_observations.json',{'observations':self.rows})
        row=overlay.response('detail',{'id':'o0'})['observation']
        self.assertEqual(row['hosts'],[]);self.assertEqual(row['forest'],[])

    def test_duplicate_identifiers_rejected_without_silent_record_loss(self):
        self.rows.append(self.rows[0]);self.write('mushroom_observations.json',{'observations':self.rows})
        with self.assertRaisesRegex(overlay.ObservationError,'invalid_source'):
            overlay.snapshot()
