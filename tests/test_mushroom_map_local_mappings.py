"""Opt-in checks against the user's local JSONs, never repository seeds.

RAINMAPPER_TEST_LOCAL_MUSHROOM_DATA=docker-data/mushroom-data python -m unittest ...
No writes, GIS scans, jobs or training. Coordinates are unnecessary for these
tests of already-read, source-qualified category values.
"""
import json
import os
from pathlib import Path
import unittest

from rainmapper_core.mushroom_map_ecology import EcologyReader


class LocalMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = os.environ.get('RAINMAPPER_TEST_LOCAL_MUSHROOM_DATA')
        if not folder:
            raise unittest.SkipTest('Explicit local dataset required')
        root = Path(folder)
        cls.reader = EcologyReader(root/'mushroom_profiles.json',
                                   root/'mushroom_reference_catalogs.json',
                                   root/'mushroom_gis_mappings.json', ph_source='openlandmap')
        cls.payload = json.loads((root/'mushroom_gis_mappings.json').read_text())

    def geography(self, cover='228', geology='CAAc'):
        return {'land_context':{
            'trees':{'status':'not_covered'},
            'vegetation':{'status':'available','source_id':'icgc_cobertes_2024',
                          'edition':'2024','field':'nivell_2','code':cover},
            'geology':{'status':'available','source_id':'icgc_geologia_50000',
                       'edition':'2024-12','field':'Codi','code':geology}},
            'terrain':{'elevation':{'status':'available','value_m':800},
                       'ph_openlandmap':{'status':'available','estimate':6.8,'lower':6,'upper':7.8}}}

    def test_actual_profiles_accept_meadow_or_riparian_without_inventing_trees(self):
        for cover, day, species in [('228','2026-04-20','calocybe_gambosa'),
                                    ('228','2026-04-20','marasmius_oreades'),
                                    ('228','2026-09-13','macrolepiota_procera'),
                                    ('222','2026-09-13','lepista_nuda'),
                                    ('229','2026-04-20','morchella_elata_complex')]:
            with self.subTest(species=species):
                result = self.reader.evaluate(self.geography(cover), day)
                rows = {r['species_id']:r for r in result['species']}
                self.assertIsNone(result['abstention_reason'])
                self.assertEqual(rows[species]['status'],'compatible')
                self.assertEqual(rows[species]['matched_host_ids'],[])
                for profile in self.reader.profiles:
                    if profile['ecology']['trophic_mode_id']=='trophic_ectomycorrhizal':
                        self.assertNotEqual(rows[profile['species_id']]['status'],'compatible')

    def test_actual_mixed_units_keep_components_and_deduplicate_soil_tendencies(self):
        result = self.reader.evaluate(self.geography(), '2026-09-13')
        context = result['mapped_context']
        self.assertEqual({r['id'] for r in context['lithologies']},
                         {'lith_limestone','lith_calcareous_marl','lith_sandstone'})
        self.assertEqual({r['id'] for r in context['soil_tendencies']},
                         {'soil_calcareous','soil_sandy'})
        self.assertTrue(all('ph_unknown' not in r['reasons'] for r in result['species']))
        result = self.reader.evaluate(self.geography(geology='Orp'),'2026-09-13')
        self.assertEqual({r['id'] for r in result['mapped_context']['soil_tendencies']},
                         {'soil_calcareous','soil_sandy','soil_siliceous'})

    def test_generic_cover_unknown_codes_and_other_editions_do_not_supply_habitat(self):
        for cover in ('221','223','225','227','224','231','unknown'):
            result = self.reader.evaluate(self.geography(cover),'2026-09-13')
            self.assertEqual(result['abstention_reason'],'terrain_context_missing')
            self.assertFalse(any(r['status']=='compatible' for r in result['species']))
        for field in ('source_id','edition','field'):
            geo = self.geography();geo['land_context']['vegetation'][field]='other'
            self.assertEqual(self.reader.evaluate(geo,'2026-09-13')['mapping_states']['vegetation'],'unresolved')

    def test_unresolved_geology_and_alluvial_origin_never_fabricate_soil_or_habitat(self):
        for code in ('CK','bf','ff','unknown','Qt1'):
            result = self.reader.evaluate(self.geography('unknown',code),'2026-09-13')
            self.assertEqual(result['mapped_context']['soil_tendencies'],[])
            self.assertEqual(result['mapped_context']['habitats'],[])
            self.assertEqual(result['abstention_reason'],'terrain_context_missing')

    def test_reviewed_geology_separates_composition_from_ph_and_preserves_mixtures(self):
        for code, expected in [
                ('Ggd',{'soil_siliceous'}), ('Gdb',{'soil_siliceous'}),
                ('mc_Dcm',{'soil_calcareous'}), ('TJb',{'soil_calcareous'}),
                ('Cacnl',{'soil_siliceous','soil_calcareous'}),
                ('mc_Capl',{'soil_siliceous','soil_calcareous'}),
                ('Bo',set()), ('Ggdq',set()), ('Orst',set()), ('Qdc',set())]:
            with self.subTest(code=code):
                r=self.reader.evaluate(self.geography(geology=code),'2026-09-14')
                ids={x['id'] for x in r['mapped_context']['soil_tendencies']}
                self.assertEqual(ids,expected)
                self.assertFalse(ids & {'soil_acidic','soil_neutral','soil_basic'})
        g=self.geography(geology='Ggd')
        for key in ('source_id','edition','field'):
            old=g['land_context']['geology'][key]
            g['land_context']['geology'][key]='different'
            r=self.reader.evaluate(g,'2026-09-14')
            self.assertEqual(r['mapped_context']['soil_tendencies'],[])
            g['land_context']['geology'][key]=old

    def test_aereus_local_exception_requires_siliceous_without_carbonate_conflict(self):
        g=self.geography(geology='Ggd')
        g['land_context']['trees']={'status':'available','items':[{'host_id':'host_quercus_ilex'}]}
        g['terrain']['ph_openlandmap'].update(estimate=7.5,lower=6.6,upper=8.1)
        for code,expected in [('Ggd','compatible'),('mc_Capg','compatible'),
                              ('mc_Capl','incompatible'),('mc_Dcm','incompatible'),('Qt1','incompatible')]:
            g['land_context']['geology']['code']=code
            r=self.reader.evaluate(g,'2026-09-14')
            row=next(x for x in r['species'] if x['species_id']=='boletus_aereus')
            self.assertEqual(row['status'],expected,(code,row))
        g['land_context']['geology']['code']='mc_Capl'
        g['terrain']['ph_openlandmap']['estimate']=6.7
        row=next(x for x in self.reader.evaluate(g,'2026-09-14')['species'] if x['species_id']=='boletus_aereus')
        self.assertEqual(row['status'],'compatible')

    def test_shared_rules_are_local_data_with_provenance_and_no_host_expansion(self):
        groups = self.payload['exact_value_mapping_groups']
        self.assertTrue(groups)
        for group in groups:
            self.assertTrue(group['review_ref'])
            self.assertFalse(group.get('mapped_host_ids'))
            first = self.reader.mappings[(group['source_id'],group['edition'],group['field'],group['raw_values'][0])]
            for code in group['raw_values']:
                self.assertIs(first,self.reader.mappings[(group['source_id'],group['edition'],group['field'],code)])

    def test_documented_sites_keep_territorial_species_across_all_months(self):
        # Replay documented inputs, not new GIS measurements or inferred setal pH.
        cases=[('mc_Capg','host_quercus_ilex',415.4,7.2,6.7,7.8,'boletus_aereus'),
               ('mc_Capg','host_quercus_faginea',357.9,7.5,6.6,8.1,'boletus_aereus'),
               ('Ggd','host_quercus_ilex',415.4,6.9,6.0,7.7,'boletus_aereus'),
               ('PPcm','host_pinus_sylvestris',1663.7,6.3,5.2,7.3,'boletus_edulis'),
               ('PPcm','host_pinus_sylvestris',1663.7,6.3,5.2,7.3,'boletus_pinophilus'),
               ('PPcm','host_pinus_sylvestris',1663.7,6.3,5.2,7.3,'cantharellus_cibarius_sl'),
               ('PPcm','host_pinus_sylvestris',1050,6.9,6,8,'hygrophorus_latitabundus')]
        for code,host,alt,ph,low,high,sid in cases:
            g=self.geography(cover='unknown',geology=code)
            g['land_context']['trees']={'status':'available','items':[{'host_id':host}]}
            g['terrain']['elevation']['value_m']=alt
            g['terrain']['ph_openlandmap'].update(estimate=ph,lower=low,upper=high)
            expected=self.reader.evaluate(g,'2026-09-13')['species']
            def territory(rows):
                return [{k:v for k,v in row.items() if k!='daily_season_phases'} for row in rows]
            for month in range(1,13):
                with self.subTest(species=sid,month=month):
                    self.assertEqual(territory(self.reader.evaluate(g,f'2026-{month:02d}-27')['species']),territory(expected))
            row=next(r for r in expected if r['species_id']==sid)
            self.assertEqual(row['status'],'compatible',row)
            if sid!='hygrophorus_latitabundus':
                self.assertEqual(row['admission'],'conditional',row)
                self.assertTrue(row['soil_filter_review_ref'])
            if code=='PPcm' and sid!='hygrophorus_latitabundus':
                self.assertIn('soil_ph_conditional',row['reasons'])

    def test_local_joint_rules_preserve_limits_and_abstain_on_missing_inputs(self):
        profiles={p['species_id']:p for p in self.reader.profiles}
        self.assertEqual(profiles['boletus_aereus']['ecology']['ph_max'],6.8)
        self.assertEqual(profiles['boletus_edulis']['topography']['altitude_min_m'],900)
        self.assertEqual(profiles['boletus_pinophilus']['topography']['altitude_min_m'],1100)
        g=self.geography(cover='unknown',geology='PPcm')
        g['land_context']['trees']={'status':'available','items':[{'host_id':'host_pinus_sylvestris'}]}
        g['terrain']['elevation']['value_m']=1663.7
        for ph,state in [(6.3,'compatible'),(8.5,'incompatible'),(None,'unknown')]:
            g['terrain']['ph_openlandmap']['estimate']=ph
            rows={r['species_id']:r for r in self.reader.evaluate(g,'2026-01-01')['species']}
            for sid in ('boletus_edulis','boletus_pinophilus','cantharellus_cibarius_sl'):
                self.assertEqual(rows[sid]['status'],state,(sid,rows[sid]))
                self.assertEqual(profiles[sid]['ecology']['soil_filter']['excluded_soil_ids'],[])
        g['terrain']['ph_openlandmap']['estimate']=6.3
        g['land_context']['geology']['code']='unknown'
        rows={r['species_id']:r for r in self.reader.evaluate(g,'2026-01-01')['species']}
        self.assertEqual(rows['boletus_edulis']['status'],'unknown')
        self.assertIn('soil_unresolved',rows['boletus_edulis']['reasons'])
        g['land_context']['geology']['code']='Ggd'
        g['land_context']['trees']={'status':'no_trees_recorded','items':[]}
        result=self.reader.evaluate(g,'2026-09-14')
        self.assertEqual(result['abstention_reason'],'terrain_context_missing')
        self.assertFalse(any(r['status']=='compatible' for r in result['species']))


if __name__=='__main__':
    unittest.main()
