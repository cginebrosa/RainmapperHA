"""Ecological eligibility never invents hosts or probabilities."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from rainmapper_core.mushroom_map_ecology import EcologyReader, compile_exact_mappings


class EcologyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.paths = [Path(self.tmp.name)/f'{s}.json' for s in ('profiles','catalog','mapping')]
        self.catalog = {'catalogs': {'host_taxa': [
            {'id':'family','rank':'family'},
            {'id':'pine','rank':'genus','parent_id':'family'},
            {'id':'black_pine','rank':'species','parent_id':'pine'},
            {'id':'scots_pine','rank':'species','parent_id':'pine'},
            {'id':'fir','rank':'genus','parent_id':'family'},
            {'id':'silver_fir','rank':'species','parent_id':'fir'},
            {'id':'oak','rank':'genus'}, {'id':'holm_oak','rank':'species','parent_id':'oak'}],
            'forest_types':[{'id':'meadow'}], 'soil_types':[], 'lithology_types':[], 'habitat_features':[]}}
        self.profile = {'species_id':'test','scientific_name':'Test species','common_names':['Prueba'],
            'ecology':{'trophic_mode_id':'trophic_ectomycorrhizal',
                'host_affinities':[{'id':'black_pine','relationship':'primary','affinity':0},
                                   {'id':'silver_fir','relationship':'preferred'}],
                'ph_min':None,'ph_max':None},
            'phenology':{'main_months':[9],'secondary_months':[10]},
            'topography':{'altitude_min_m':500,'altitude_max_m':2200,'preferred_aspect_ids':['north']}}
        self.mapping = {'exact_value_mappings':[]}
        self.save()
        self.reader = EcologyReader(*self.paths)
        self.geo = {'land_context':{'trees':{'status':'available','items':[{'host_id':'black_pine'}]}},
                    'terrain':{'elevation':{'status':'available','value_m':1800}}}

    def save(self):
        for path, data in zip(self.paths, ({'species_profiles':[self.profile]}, self.catalog, self.mapping)):
            path.write_text(json.dumps(data))

    def result(self, start='2026-09-13'):
        return self.reader.evaluate(self.geo,start)

    def row(self, start='2026-09-13'):
        return self.result(start)['species'][0]

    def test_map_name_is_local_metadata_without_species_or_host_aliasing(self):
        self.profile['metadata']={'map_display_name':'Rovelló · tipo de prueba'}
        self.save()
        row=self.row()
        self.assertEqual(row['name'],'Rovelló · tipo de prueba')
        self.assertEqual(row['species_id'],'test')
        self.assertEqual(row['scientific_name'],'Test species')
        self.assertEqual(row['matched_host_ids'],['black_pine'])

    def test_one_of_required_hosts_is_enough_and_zero_affinity_is_not_a_veto(self):
        for host in ('black_pine','silver_fir'):
            self.geo['land_context']['trees']['items']=[{'host_id':host}]
            self.assertEqual(self.row()['status'],'compatible')
            self.assertEqual(self.row()['matched_host_ids'],[host])
            self.assertNotIn('probabilities',self.row())

    def test_oaks_do_not_allow_species_requiring_black_pine_or_fir(self):
        self.geo['land_context']['trees']['items']=[{'host_id':'holm_oak'}]
        row=self.row()
        self.assertEqual(row['daily_statuses'],['unknown']*7)
        self.assertIn('hosts_unknown',row['reasons'])
        self.assertEqual(row['matched_host_ids'],[])

    def test_generic_pine_allowed_but_specific_sibling_and_family_not_substitutes(self):
        for host,allowed in [('pine',True),('scots_pine',False),('family',False),('fir',True)]:
            with self.subTest(host=host):
                self.geo['land_context']['trees']['items']=[{'host_id':host}]
                self.assertEqual(self.row()['status']=='compatible',allowed)
        self.profile['ecology']['host_affinities']=[{'id':'pine','relationship':'primary'}]
        self.save()
        self.geo['land_context']['trees']['items']=[{'host_id':'scots_pine'}]
        self.assertEqual(self.row()['status'],'compatible')
        self.geo['land_context']['trees']['items']=[{'host_id':'silver_fir'}]
        self.assertNotEqual(self.row()['status'],'compatible')

    def test_verified_meadow_admits_habitat_species_without_trees(self):
        self.profile['ecology'].update(trophic_mode_id='trophic_saprotrophic',
                                      forest_type_affinities=[{'id':'meadow','relationship':'primary'}])
        self.set_meadow_mapping()
        for state in ('no_trees_recorded','not_covered','unavailable','ambiguous','available'):
            with self.subTest(state=state):
                self.geo['land_context']['trees']={'status':state,'items':[]}
                self.assertIsNone(self.result()['abstention_reason'])
                self.assertEqual(self.row()['daily_statuses'],['compatible']*7)
        self.profile['ecology']['trophic_mode_id']='trophic_ectomycorrhizal'; self.save()
        self.assertEqual(self.row()['daily_statuses'],['unknown']*7)
        self.assertIn('hosts_unknown',self.row()['reasons'])

    def test_no_habitat_or_hosts_abstains_without_zero_probabilities(self):
        self.geo['land_context']['trees']={'status':'not_covered'}
        self.assertEqual(self.result()['abstention_reason'],'terrain_context_missing')
        self.assertEqual(self.row()['daily_statuses'],['unknown']*7)
        self.assertNotIn('probabilities',self.row())

    def test_unknown_id_label_and_failed_catalog_cannot_establish_host(self):
        for trees in ({'status':'available','items':[{'label':'Pino negro','host_id':'invented'}]},
                      {'status':'available','catalog_status':'unavailable','items':[{'host_id':'black_pine'}]}):
            self.geo['land_context']['trees']=trees
            self.assertEqual(self.result()['abstention_reason'],'terrain_context_missing')

    def test_altitude_windows_inclusive_no_aspect_requirement(self):
        for height,expected in [(0,'incompatible'),(499,'incompatible'),(500,'compatible'),
                                (2200,'compatible'),(2201,'incompatible')]:
            with self.subTest(height=height):
                self.geo['terrain']['elevation']['value_m']=height
                self.assertEqual(self.row()['status'],expected)
        self.geo['terrain']['elevation']['status']='no_data'
        self.assertEqual(self.row()['status'],'unknown')

    def test_territorial_result_ignores_months_and_year_boundary(self):
        original = copy.deepcopy(self.profile['phenology'])
        expected = self.row()
        self.assertEqual(expected.pop('daily_season_phases'),['main']*7)
        for day in ('2026-10-01','2026-11-01','2026-08-29','2026-12-29'):
            row=self.row(day);row.pop('daily_season_phases')
            self.assertEqual(row, expected)
        self.assertEqual(self.row('2026-10-01')['daily_season_phases'],['secondary']*7)
        self.assertEqual(self.row('2026-11-01')['daily_season_phases'],['out_of_season']*7)
        self.assertEqual(self.row('2026-08-29')['daily_season_phases'],['out_of_season']*3+['main']*4)
        self.assertEqual(self.profile['phenology'], original)
        self.profile['phenology'].update(main_months=[], secondary_months=[])
        self.save()
        row=self.row();self.assertEqual(row.pop('daily_season_phases'),['unknown']*7)
        self.assertEqual(row, expected)

    def test_optional_ph_and_uncertainty_are_not_zero_or_median_only(self):
        self.assertEqual(self.row()['status'],'compatible')
        self.profile['ecology'].update(ph_min=5,ph_max=7); self.save()
        self.assertEqual(self.row()['status'],'unknown')
        for lower,upper,expected in [(5,7,'compatible'),(4,6,'unknown'),(7.1,8,'incompatible'),
                                     (0,0,'unknown'),(6,None,'unknown')]:
            with self.subTest(interval=(lower,upper)):
                self.geo['terrain']['ph']={'depths':[{'depth_cm':[0,5],'status':'available',
                                                    'median':6,'lower':lower,'upper':upper}]}
                self.assertEqual(self.row()['status'],expected)

    def set_meadow_mapping(self):
        self.mapping['exact_value_mappings']=[{'source_id':'cover','edition':'2024','field':'code',
            'raw_value':'228','review_status':'accepted','mapped_forest_type_ids':['meadow']}]
        self.geo['land_context']['vegetation']={'source_id':'cover','edition':'2024','field':'code',
                                              'code':'228','status':'available'}
        self.save()

    def test_openlandmap_mean_selects_species_without_using_uncertainty_or_soilgrids(self):
        self.profile['ecology'].update(ph_min=5,ph_max=7);self.save()
        self.reader=EcologyReader(*self.paths,ph_source='openlandmap')
        self.geo['terrain']['ph']={'depths':[{'depth_cm':[0,5],'status':'available',
                                            'median':9,'lower':8,'upper':10}]}
        for value,expected in [(5,'compatible'),(6.7,'compatible'),(7,'compatible'),(7.1,'incompatible'),
                               (4.9,'incompatible'),(None,'unknown'),(0,'unknown')]:
            with self.subTest(value=value):
                self.geo['terrain']['ph_openlandmap']={'status':'partial','estimate':value,'lower':3,'upper':9}
                self.assertEqual(self.row()['status'],expected)
        self.assertEqual(self.result()['ph_selection'],{'source':'openlandmap','statistic':'mean'})
        self.geo['terrain']['ph_openlandmap']={'status':'unavailable','estimate':6}
        self.assertEqual(self.row()['status'],'unknown')

    def test_openlandmap_cannot_replace_missing_required_hosts(self):
        self.profile['ecology'].update(ph_min=5,ph_max=7);self.save()
        self.reader=EcologyReader(*self.paths,ph_source='openlandmap')
        self.geo['terrain']['ph_openlandmap']={'status':'available','estimate':6.6,'lower':5,'upper':8}
        self.geo['land_context']['trees']['items']=[{'host_id':'holm_oak'}]
        self.assertEqual(self.row()['status'],'unknown')
        self.assertIn('hosts_unknown',self.row()['reasons'])

    def set_soil_filter(self):
        self.catalog['catalogs']['soil_types'] = [{'id':s} for s in ('siliceous','calcareous','sandy')]
        self.profile['ecology'].update(ph_min=3.5, ph_max=6.8, soil_filter={
            'accepted_soil_ids':['siliceous'], 'excluded_soil_ids':['calcareous'],
            'ph_conflict':'estimated_interval_overlap', 'review_ref':'test-review'})
        self.mapping['exact_value_mappings'] = [{'source_id':'geology','edition':'2024',
            'field':'code','raw_value':'rock','review_status':'accepted',
            'mapped_soil_tendency_ids':['siliceous']}]
        self.geo['land_context']['geology'] = {'source_id':'geology','edition':'2024',
            'field':'code','code':'rock','status':'available'}
        self.geo['terrain']['ph_openlandmap'] = {
            'status':'available','estimate':7.5,'lower':6.6,'upper':8.1}
        self.save()
        self.reader = EcologyReader(*self.paths, ph_source='openlandmap')

    def test_reviewed_soil_qualifies_estimate_but_preserves_other_gates(self):
        self.set_soil_filter()
        original = copy.deepcopy(self.geo)
        self.assertEqual(self.row()['status'], 'compatible')
        self.assertIn('ph_conflict_soil_supported',self.row()['reasons'])
        self.assertEqual(self.geo,original)
        self.assertEqual(self.row('2026-11-01')['status'],'compatible')
        self.geo['terrain']['elevation']['value_m']=400
        self.assertEqual(self.row()['status'],'incompatible')
        self.geo=copy.deepcopy(original)
        self.geo['land_context']['trees']['items']=[{'host_id':'holm_oak'}]
        self.assertEqual(self.row()['status'],'unknown')

    def test_soil_cannot_rescue_missing_invalid_or_disjoint_ph(self):
        self.set_soil_filter()
        context=self.geo['terrain']['ph_openlandmap']
        for delta, expected in [({'lower':7},'incompatible'),({'lower':None},'incompatible'),
                                ({'upper':7.4},'incompatible'),({'lower':False},'incompatible'),
                                ({'estimate':None},'unknown'),({'status':'unavailable'},'unknown')]:
            with self.subTest(delta=delta):
                context.clear();context.update(status='available',estimate=7.5,lower=6.6,upper=8.1)
                context.update(delta)
                self.assertEqual(self.row()['status'],expected)

    def test_soil_exclusion_mixture_and_unknown_are_distinct(self):
        self.set_soil_filter()
        self.geo['terrain']['ph_openlandmap']['estimate']=6.7
        for soils,expected,reason in [(['calcareous'],'incompatible','soil_excluded'),
                (['siliceous','calcareous'],'unknown','soil_mixed_conflict'),
                (['sandy'],'compatible','soil_not_listed'),([], 'compatible','soil_unresolved')]:
            with self.subTest(soils=soils):
                self.mapping['exact_value_mappings'][0]['mapped_soil_tendency_ids']=soils
                self.save()
                self.assertEqual(self.row()['status'],expected)
                self.assertIn(reason,self.row()['reasons'])
        self.geo['terrain']['ph_openlandmap']['estimate']=7.5
        self.assertEqual(self.row()['status'],'incompatible')
        self.mapping['exact_value_mappings'][0]['mapped_soil_tendency_ids']=['siliceous']
        self.mapping['exact_value_mappings'][0]['review_status']='pending_review';self.save()
        self.assertEqual(self.row()['status'],'incompatible')

    def test_soil_policy_validation_and_live_reload_fail_closed(self):
        self.set_soil_filter()
        original=copy.deepcopy(self.profile['ecology']['soil_filter'])
        for delta in ({'accepted_soil_ids':['invented']}, {'excluded_soil_ids':['siliceous']},
                      {'ph_override_blocked_soil_ids':['invented']},
                      {'ph_override_blocked_soil_ids':'calcareous'},
                      {'conditional_soil_ids':['invented']}, {'conditional_soil_ids':['calcareous']},
                      {'require_soil_context':'yes'},
                      {'review_ref':''}, {'ph_conflict':'always'}, {'typo':True}):
            with self.subTest(delta=delta):
                self.profile['ecology']['soil_filter']={**original,**delta};self.save()
                self.assertEqual(self.result()['status'],'unavailable')
        self.profile['ecology']['soil_filter']=original;self.save()
        self.assertEqual(self.row()['status'],'compatible')
        self.profile['ecology']['soil_filter']['ph_conflict']='strict';self.save()
        self.assertEqual(self.row()['status'],'incompatible')

    def test_joint_policy_conditions_carbonate_without_inventing_decalcification(self):
        self.set_soil_filter()
        self.profile['ecology']['soil_filter'].update(excluded_soil_ids=[],
            conditional_soil_ids=['calcareous'], require_soil_context=True, ph_conflict='strict')
        self.geo['terrain']['ph_openlandmap']['estimate']=6.7
        original=copy.deepcopy(self.geo)
        for soils, state, admission in [(['calcareous'],'compatible','conditional'),
                (['siliceous','calcareous'],'compatible','standard'),
                (['sandy'],'compatible','conditional'),(['siliceous'],'compatible','standard'),
                ([], 'unknown',None)]:
            self.mapping['exact_value_mappings'][0]['mapped_soil_tendency_ids']=soils; self.save()
            row=self.row()
            self.assertEqual((row['status'],row['admission']),(state,admission))
            self.assertEqual(row['soil_filter_review_ref'],'test-review')
            if 'siliceous' in soils:
                self.assertNotIn('soil_ph_conditional',row['reasons'])
            elif soils == ['calcareous']:
                self.assertIn('soil_ph_conditional',row['reasons'])
        self.assertEqual(self.geo,original)
        self.mapping['exact_value_mappings'][0]['mapped_soil_tendency_ids']=['calcareous'];self.save()
        self.geo['terrain']['ph_openlandmap']['estimate']=7.5
        row=self.row()
        self.assertEqual(row['status'],'incompatible')
        self.assertIn('ph_outside',row['reasons'])
        self.assertNotIn('soil_ph_conditional',row['reasons'])

    def test_accepted_mixed_component_does_not_bypass_exclusion_or_ph_limits(self):
        self.set_soil_filter()
        rule=self.profile['ecology']['soil_filter']
        rule.update(excluded_soil_ids=[],conditional_soil_ids=['calcareous'],ph_conflict='strict')
        self.mapping['exact_value_mappings'][0]['mapped_soil_tendency_ids']=['siliceous','calcareous']
        for ph, expected, reason in [
                ({'status':'available','estimate':6,'lower':5.8,'upper':6.2},'compatible','ph_match'),
                ({'status':'available','estimate':7.5,'lower':7.2,'upper':7.8},'incompatible','ph_outside'),
                ({'status':'unavailable'},'unknown','ph_unknown')]:
            with self.subTest(ph=ph):
                self.geo['terrain']['ph_openlandmap']=ph; self.save()
                row=self.row()
                self.assertEqual(row['status'],expected)
                self.assertIn(reason,row['reasons'])
                self.assertNotIn('soil_ph_conditional',row['reasons'])
        self.geo['terrain']['ph_openlandmap']={'status':'available','estimate':6,'lower':5.8,'upper':6.2}
        rule.update(excluded_soil_ids=['calcareous'],conditional_soil_ids=[])
        self.save()
        row=self.row()
        self.assertNotEqual(row['status'],'compatible')
        self.assertIn('soil_mixed_conflict',row['reasons'])

    def test_mixed_substrate_can_block_ph_exception_without_becoming_a_soil_veto(self):
        self.set_soil_filter()
        rule = self.profile['ecology']['soil_filter']
        rule.update(excluded_soil_ids=[], ph_override_blocked_soil_ids=['calcareous'])
        mapping = self.mapping['exact_value_mappings'][0]
        for soils, estimate, expected in [
                (['siliceous'],7.5,'compatible'),
                (['siliceous','calcareous'],7.5,'incompatible'),
                (['siliceous','calcareous'],6.7,'compatible'),
                (['calcareous'],6.7,'compatible'),
                ([],7.5,'incompatible')]:
            with self.subTest(soils=soils,estimate=estimate):
                mapping['mapped_soil_tendency_ids']=soils
                self.geo['terrain']['ph_openlandmap']['estimate']=estimate
                self.save()
                row=self.row()
                self.assertEqual(row['status'],expected)
                self.assertNotIn('soil_excluded',row['reasons'])
                self.assertNotIn('soil_mixed_conflict',row['reasons'])
                if expected=='incompatible':
                    self.assertIn('ph_outside',row['reasons'])

    def test_habitat_mapping_requires_same_product_edition_field_and_review(self):
        self.profile['ecology'].update(trophic_mode_id='trophic_saprotrophic',
                                      forest_type_affinities=[{'id':'meadow','relationship':'primary'}])
        self.set_meadow_mapping()
        self.assertEqual(self.row()['status'],'compatible')
        for key in ('source_id','edition','field','code'):
            original=self.geo['land_context']['vegetation'][key]
            self.geo['land_context']['vegetation'][key]='other'
            self.assertEqual(self.row()['status'],'unknown')
            self.geo['land_context']['vegetation'][key]=original
        self.mapping['exact_value_mappings'][0]['review_status']='pending_review'; self.save()
        self.assertEqual(self.row()['status'],'unknown')

    def test_mixed_materials_union_preferences_without_veto_or_numeric_ph(self):
        self.catalog['catalogs']['soil_types']=[{'id':s,'ph_min':1,'ph_max':2} for s in ('calcareous','sandy','gypsum')]
        self.catalog['catalogs']['lithology_types']=[{'id':s} for s in ('limestone','sandstone','gypsum')]
        self.profile['ecology']['soil_affinities']=[{'id':'sandy','relationship':'preferred','affinity':0}]
        self.profile['ecology']['lithology_affinities']=[{'id':'limestone','relationship':'possible','affinity':0}]
        self.mapping['exact_value_mapping_groups']=[{'source_id':'geology','edition':'2024',
            'field':'Codi','raw_values':['mix1','mix2'],'review_status':'accepted','review_ref':'local-review.json',
            'mapped_lithology_ids':['limestone','sandstone','gypsum'],
            'mapped_soil_tendency_ids':['calcareous','sandy','gypsum','calcareous']}]
        self.geo['land_context']['geology']={'source_id':'geology','edition':'2024','field':'Codi','code':'mix2','status':'available'}
        self.save()
        result=self.result()
        self.assertEqual(len(result['mapped_context']['soil_tendencies']),3)
        self.assertEqual(len(result['mapped_context']['lithologies']),3)
        self.assertEqual(self.row()['status'],'compatible')
        self.assertIn('ph_unbounded',self.row()['reasons'])
        self.assertIn('soil_preference_match',self.row()['reasons'])
        self.assertIn('lithology_preference_match',self.row()['reasons'])
        first=self.reader.mappings[('geology','2024','Codi','mix1')]
        self.assertIs(first,self.reader.mappings[('geology','2024','Codi','mix2')])
        self.geo['land_context']['geology']['code']='unknown'
        self.assertEqual(self.row()['status'],'compatible')
        self.assertNotIn('soil_preference_match',self.row()['reasons'])

    def test_shared_rules_require_review_full_identity_unique_codes_and_valid_ids(self):
        self.set_meadow_mapping()
        original=self.mapping['exact_value_mappings'].pop()
        group={k:v for k,v in original.items() if k!='raw_value'}
        group.update(raw_values=['228','229'],review_ref='review.json')
        self.mapping['exact_value_mapping_groups']=[group]
        self.save()
        self.assertEqual(self.result()['mapping_states']['vegetation'],'accepted')
        for field in ('source_id','edition','field','review_status'):
            value=group[field]; group[field]='different'; self.save()
            self.assertEqual(self.result()['mapping_states']['vegetation'],'unresolved')
            group[field]=value
        for key,value in [('raw_values',['228','228']),('mapped_host_ids',['invented']),
                          ('raw_values',[None]),('review_ref',None),('edition',None),
                          ('raw_values',['228']*2049)]:
            with self.subTest(key=key,value_type=type(value).__name__):
                invalid=copy.deepcopy(group); invalid[key]=value
                self.mapping['exact_value_mapping_groups']=[invalid]; self.save()
                self.assertEqual(self.result()['status'],'unavailable')
        self.mapping['exact_value_mapping_groups']=[group]
        self.mapping['exact_value_mappings']=[original]; self.save()
        self.assertEqual(self.result()['status'],'unavailable')

    def test_unversioned_legacy_mapping_cannot_match_missing_identity(self):
        self.set_meadow_mapping()
        self.mapping['exact_value_mappings'][0].pop('edition')
        self.geo['land_context']['vegetation'].pop('edition');self.save()
        self.assertEqual(self.result()['mapping_states']['vegetation'],'unresolved')

    def test_catalog_edit_between_forest_and_ecology_abstains_then_recovers(self):
        trees=self.geo['land_context']['trees']
        trees.update(source_id='mfe25',catalog_revision=sha256(self.paths[1].read_bytes()).hexdigest()[:20])
        self.assertEqual(self.row()['status'],'compatible')
        # The same ID now denotes another taxon: ID existence is insufficient.
        self.catalog['catalogs']['host_taxa'][2]['scientific_name']='Changed taxon';self.save()
        self.assertEqual(self.result()['reason'],'host_catalog_mismatch')
        self.assertEqual(self.result()['species'],[])
        trees['catalog_revision']=sha256(self.paths[1].read_bytes()).hexdigest()[:20]
        self.assertEqual(self.row()['status'],'compatible')

    def test_invalid_edit_never_reuses_stale_rules_and_recovers(self):
        self.paths[0].write_text('{')
        self.assertEqual(self.result()['status'],'unavailable')
        self.save()
        self.assertEqual(self.row()['status'],'compatible')
        self.catalog['catalogs']['host_taxa'][0]['parent_id']='black_pine'; self.save()
        self.assertEqual(self.result()['status'],'unavailable')

    def test_valid_edits_change_revision_and_all_week_uses_new_snapshot(self):
        before=self.result()['revision']
        self.profile['topography']['altitude_max_m']=1000; self.save()
        result=self.result()
        self.assertNotEqual(result['revision'],before)
        self.assertEqual(result['species'][0]['daily_statuses'],['incompatible']*7)

    def test_unchanged_small_rules_not_read_or_hashed_each_click(self):
        with patch.object(Path,'open',side_effect=AssertionError('unchanged files must not be opened')):
            self.assertEqual(self.row()['status'],'compatible')

    def test_inactive_relation_does_not_supply_a_host(self):
        for relation in self.profile['ecology']['host_affinities']: relation['v0_active']=False
        self.save()
        self.assertEqual(self.row()['status'],'unknown')

    def test_unknown_catalog_reference_and_invalid_bounds_refused(self):
        self.profile['ecology']['host_affinities'][0]['id']='missing'; self.save()
        self.assertEqual(self.result()['status'],'unavailable')
        self.profile['ecology']['host_affinities'][0]['id']='black_pine'
        self.profile['ecology'].update(ph_min=8,ph_max=7); self.save()
        self.assertEqual(self.result()['status'],'unavailable')


if __name__ == '__main__':
    unittest.main()
