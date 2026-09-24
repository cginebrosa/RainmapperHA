import copy
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from unittest.mock import Mock

from rainmapper_core import mushroom_gis_lab as gis
from rainmapper_core import mushroom_gis_recovery as recovery
from rainmapper_core.mushroom_observation_features import build_joined_row


class RecoveryTests(unittest.TestCase):
    def report(self):
        return {'version': 1, 'location': {'lat': 42.0, 'lon': 2.0},
                'values': {'host_ids': ['host_pinus_sylvestris']},
                'sources': {'host_ids': ['mfe25']}, 'recovered_at': '2026-09-20'}

    def test_reviewed_values_remain_gis_in_frozen_observation_rebuild(self):
        row = {'location': {'lat':42., 'lon':2.}, 'site_context': {
            'observed_host_ids':['host_quercus_spp'], 'gis_recovery': self.report()}}
        before = copy.deepcopy(row)
        with (patch.object(gis, 'transform_wgs84_to_utm31', return_value=(1,2)),
              patch.object(gis, 'vector_layers', return_value=[]),
              patch.object(gis, 'sample_dem', return_value={'status':'missing_layer'}),
              patch.object(recovery, 'forest_lookup', side_effect=AssertionError('no live map lookup in rebuild'))):
            result = gis.reconstruct_observation(row)
        self.assertEqual(row, before)
        joined = build_joined_row({'observed_host_ids':['host_quercus_spp']}, result)
        self.assertEqual(set(joined['host_ids']), {'host_quercus_spp','host_pinus_sylvestris'})
        self.assertEqual(joined['host_sources']['host_pinus_sylvestris'], ['gis'])
        self.assertEqual(joined['host_sources']['host_quercus_spp'], ['field'])

    def test_coordinate_change_invalidates_old_recovery(self):
        self.assertEqual(recovery.valid_recovery(self.report(), {'lat':42.1,'lon':2}), {})
        self.assertEqual(recovery.valid_recovery(self.report(), {'lat':42.,'lon':2.}), self.report())
        for value in (float('nan'), float('inf'), 91):
            with self.assertRaises(ValueError): recovery.point(value, 2)

    def test_modes_preserve_merge_or_replace_without_mutating_input(self):
        old = ['host_oak']; proposed = ['host_oak','host_pine']
        self.assertEqual(recovery.merge_value(old, proposed, 'keep'), old)
        self.assertEqual(recovery.merge_value(old, proposed, 'merge'), proposed)
        self.assertEqual(recovery.merge_value(old, ['host_pine'], 'replace'), ['host_pine'])
        self.assertEqual(old, ['host_oak'])
        with self.assertRaises(ValueError): recovery.merge_value(900, 950, 'merge')

    def test_point_preview_combines_sources_without_inventing_hosts_or_soil(self):
        with (patch.object(gis, 'reconstruct_observation', return_value={
                'gis_context_v0': {'host_ids':['host_quercus_spp'], 'altitude_m':924.7},
                'layers': {'mvc50': {'mapped': {'mapped_host_ids':['host_quercus_spp']}}}, 'gaps': []}),
              patch.object(recovery, 'forest_lookup', return_value={'status':'available', 'items':[
                  {'scientific_name':'Pinus sylvestris','host_id':'host_pinus_sylvestris'},
                  {'scientific_name':'Unknown','host_id':None}]})):
            result = recovery.observation_preview(42,2,{}, {})
        self.assertEqual(result['values']['host_ids'], ['host_pinus_sylvestris','host_quercus_spp'])
        self.assertEqual(result['values']['soil_tendency_ids'], [])
        self.assertEqual(result['sources']['host_ids'], ['mvc50','mfe25'])
        self.assertLess(len(json.dumps(result).encode()), 2048)

    def test_microarea_unions_mfe_hosts_and_keeps_missing_source_status(self):
        geometry={'type':'Polygon','coordinates':[[[2,42],[2.01,42],[2.01,42.01],[2,42]]]}
        with (patch.object(gis, 'polygon_sample_grid', return_value=[]),
              patch.object(recovery, 'forest_lookup', return_value={
                  'status':'available','host_ids':['host_pinus_sylvestris']})):
            result=gis.derive_site_gis_dem(geometry, {}, {})
        self.assertEqual(result['gis']['host_ids'], ['host_pinus_sylvestris'])
        self.assertEqual(result['gis']['accepted_exact_ids']['host_ids'], ['host_pinus_sylvestris'])


class RecoveryFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_web_server_auth import load_web_server_module
        cls.web = load_web_server_module()

    def test_save_keeps_field_and_gis_separate_and_discards_moved_evidence(self):
        form={'observation_species_id':['boletus_edulis'], 'observed_at':['2026-09-20'],
              'location_lat':['42'], 'location_lon':['2'], 'observed_host_ids':['host_quercus_spp'],
              'gis_recovery_json':[json.dumps(RecoveryTests().report())]}
        row=self.web.observation_payload_from_form(form, [])
        self.assertEqual(row['site_context']['observed_host_ids'], ['host_quercus_spp'])
        self.assertEqual(row['site_context']['gis_recovery']['values']['host_ids'], ['host_pinus_sylvestris'])
        form['location_lat']=['42.1']
        moved=self.web.observation_payload_from_form(form, [], row)
        self.assertNotIn('gis_recovery', moved['site_context'])
        self.assertEqual(moved['site_context']['observed_host_ids'], ['host_quercus_spp'])

    def test_duplicate_with_new_exif_keeps_gis_only_for_its_original_point(self):
        report = RecoveryTests().report()
        report['values'].update(forest_type_ids=['forest_mixed'],
                                soil_tendency_ids=['soil_calcareous'])
        report['sources'].update(forest_type_ids=['mvc50'],
                                 soil_tendency_ids=['geology_50000'])
        source = {'observation_id': 'original', 'location': {'lat': 42., 'lon': 2.},
                  'site_context': {'gis_recovery': report}}
        draft = self.web.mushroom_profiles_ui.observation_duplicate_template_row(source)
        form = {'observation_species_id': ['boletus_edulis'], 'observed_at': ['2026-09-20'],
                'location_lat': ['42'], 'location_lon': ['2'],
                'observed_habitat_feature_ids': ['habitat_mossy'],
                'gis_recovery_json': [json.dumps(draft['site_context']['gis_recovery'])]}
        for lat, expected in [(42., report), (42.1, None)]:
            with self.subTest(lat=lat):
                imported = self.web.observation_form_with_exif_fields(form, {
                    'lat': lat, 'lon': 2., 'observed_at': '2026-09-21', 'filename': 'new.jpg'})
                row = self.web.observation_payload_from_form(imported, [])
                self.assertEqual(row['site_context'].get('gis_recovery'), expected)
                self.assertEqual(row['site_context']['observed_habitat_feature_ids'], ['habitat_mossy'])
        self.assertEqual(source['site_context']['gis_recovery'], report)

    def test_microarea_apply_merges_draft_and_never_saves(self):
        row={'micro_area_id':'test', 'altitude':{'min_m':900}, 'ecology':{
            'host_ids':['host_quercus_spp'], 'soil_tendency_ids':['soil_siliceous']}}
        report={'altitude_min_m':950,'gis':{'host_ids':['host_pinus_sylvestris'],
                                         'soil_tendency_ids':['soil_calcareous']}}
        handler=self.web.RainmapperHandler.__new__(self.web.RainmapperHandler)
        with (patch.object(self.web.mushroom_known_sites,'load_payload',return_value={'micro_areas':[row]}),
              patch.object(self.web.mushroom_known_sites,'save_payload') as save,
              patch.object(self.web,'set_mushroom_known_sites_gis_preview') as preview):
            url=handler.handle_mushroom_known_sites_post({
                'known_site_action':['apply_gis_dem'], 'known_site_kind':['micro_area'],
                'known_site_id':['test'], 'gis_report_json':[json.dumps(report)],
                'gis_mode_host_ids':['merge'],'gis_mode_soil_tendency_ids':['replace'],
                'gis_mode_altitude_min_m':['keep']})
        save.assert_not_called()
        draft=preview.call_args.args[0]['draft']
        self.assertEqual(draft['ecology']['host_ids'], ['host_quercus_spp','host_pinus_sylvestris'])
        self.assertEqual(draft['ecology']['soil_tendency_ids'], ['soil_calcareous'])
        self.assertEqual(draft['altitude']['min_m'], 900)
        self.assertEqual(row['ecology']['host_ids'], ['host_quercus_spp'])
        self.assertEqual(url, '?kind=micro_area&id=test')

    def test_preview_endpoint_only_reads_and_uses_form_coordinates(self):
        handler=self.web.RainmapperHandler.__new__(self.web.RainmapperHandler)
        handler.path='/api/mushrooms/observation-gis-preview?location_lat=42&location_lon=2'
        handler.send_json=Mock();store=Mock()
        with (patch.object(self.web,'default_store',return_value=store),
              patch.object(recovery,'observation_preview',return_value=RecoveryTests().report()) as preview):
            handler.do_GET()
        self.assertEqual(handler.send_json.call_args.args[0], 200)
        self.assertEqual(preview.call_args.args[:2], (42,2))
        store.replace.assert_not_called();store.ensure_seeded.assert_not_called()

    def test_validator_rejects_unknown_recovered_catalog_ids(self):
        from tests.test_mushroom_data_validator import VALIDATOR
        form={'observation_species_id':['boletus_edulis'],'observed_at':['2026-09-20'],
              'location_lat':['42'],'location_lon':['2'],
              'gis_recovery_json':[json.dumps(RecoveryTests().report())]}
        row=self.web.observation_payload_from_form(form, [])
        catalogs=json.loads((Path(__file__).resolve().parents[1]/'mushroom-data/mushroom_reference_catalogs.json').read_text())['catalogs']
        ids={key:{r['id'] for r in rows} for key,rows in catalogs.items() if isinstance(rows,list)}
        for host, expect_error in [('host_pinus_sylvestris',False),('host_does_not_exist',True)]:
            row['site_context']['gis_recovery']['values']['host_ids']=[host]
            messages=[]
            VALIDATOR.validate_observations({'schema_version':'0.1','observations':[row]}, {'boletus_edulis'},ids,messages,{})
            self.assertEqual(any(m.severity=='ERROR' and '.gis_recovery' in m.location for m in messages), expect_error)


if __name__ == '__main__':
    unittest.main()
