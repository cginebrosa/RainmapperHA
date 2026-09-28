import copy
import unittest
from unittest.mock import patch
from rainmapper_core.mushroom_territorial_context import resolve_context
from rainmapper_core.mushroom_map_ecology import compile_exact_mappings, resolve_land_context
from rainmapper_core import mushroom_gis_lab as gis
from rainmapper_core.mushroom_gis_recovery import observation_preview


class TerritorialTests(unittest.TestCase):
    def test_field_priority_and_fallback_are_independent(self):
        sources = {'mfe25': {'host_ids': ['pine']},
                   'mvc50': {'host_ids': ['oak'], 'forest_type_ids': ['cork_oak'],
                             'soil_tendency_ids': ['soil_siliceous']},
                   'icgc_cobertes_2024': {'forest_type_ids': ['broadleaf']},
                   'geology_50000': {'lithology_ids': ['gravel']}}
        before = copy.deepcopy(sources)
        r = resolve_context(sources)
        self.assertEqual(r['values']['host_ids'], ['pine'])
        self.assertEqual(r['values']['forest_type_ids'], ['cork_oak'])
        self.assertEqual(r['values']['soil_tendency_ids'], ['soil_siliceous'])
        self.assertEqual(r['values']['lithology_ids'], ['gravel'])
        self.assertEqual(sources, before)
        sources['mfe25']['host_ids'] = []
        sources['mvc50']['forest_type_ids'] = []
        r = resolve_context(sources)
        self.assertEqual(r['values']['host_ids'], ['oak'])
        self.assertEqual(r['sources']['forest_type_ids'], ['icgc_cobertes_2024'])

    def test_missing_substrate_falls_back_but_conflicting_explicit_substrate_is_retained(self):
        sources = {'mvc50': {}, 'geology_50000': {'soil_tendency_ids': ['soil_calcareous']}}
        self.assertEqual(resolve_context(sources)['sources']['soil_tendency_ids'], ['geology_50000'])
        sources['mvc50']['soil_tendency_ids'] = ['soil_siliceous']
        r = resolve_context(sources)
        self.assertEqual(r['values']['soil_tendency_ids'], ['soil_calcareous', 'soil_siliceous'])
        self.assertEqual(r['conflicts'][0]['reason'], 'contradictory_substrate')
        sources['geology_50000']['soil_tendency_ids'].append('soil_siliceous')
        self.assertEqual(resolve_context(sources)['values']['soil_tendency_ids'], ['soil_siliceous'])
        self.assertFalse(resolve_context(sources)['conflicts'])

    def test_no_coverage_does_not_invent_a_classification(self):
        self.assertTrue(all(not ids for ids in resolve_context({})['values'].values()))

    def test_recent_artificial_cover_is_recorded_not_silently_merged_or_used_to_erase_history(self):
        sources = {'mvc50': {'forest_type_ids': ['cork_oak']}}
        cover = {'source_id': 'icgc_cobertes_2024', 'edition': '2024', 'field': 'nivell_2',
                 'status': 'available', 'code': '341'}
        r = resolve_context(sources, cover=cover)
        self.assertEqual(r['conflicts'][0]['reason'], 'non_forest_cover_conflict')
        self.assertEqual(r['values']['forest_type_ids'], ['cork_oak'])
        for code in ('223', '224', '111', '346'):
            self.assertFalse(resolve_context(sources, cover=dict(cover, code=code))['conflicts'])

    def test_map_and_observation_use_same_pinned_fields_and_rules(self):
        cats = {'catalogs': {'host_taxa': [{'id': 'pine'}, {'id': 'oak'}],
                'forest_types': [{'id': 'cork_oak'}, {'id': 'broadleaf'}],
                'soil_types': [{'id': 'soil_siliceous'}], 'habitat_features': [], 'lithology_types': []}}
        rules = {'exact_value_mappings': [
            {'source_id': 'mvc50', 'field': 'LLVA_Subst', 'raw_value': 'Silici',
             'review_status': 'accepted', 'mapped_soil_tendency_ids': ['soil_siliceous']},
            {'source_id': 'mvc50', 'field': 'LLVA_niv2t', 'raw_value': 'Alzinars i suredes',
             'review_status': 'accepted', 'mapped_forest_type_ids': ['cork_oak']},
            {'source_id': 'mvc50', 'field': 'LLFISCAT_t', 'raw_value': 'Quercus suber',
             'review_status': 'accepted', 'mapped_host_ids': ['oak']}]}
        ids = gis.catalog_ids_by_group(cats)
        index = compile_exact_mappings(rules, ids)
        props = {'LLVA_Subst': ' silici ', 'LLVA_niv2t': 'Alzinars i suredes', 'LLFISCAT_t': 'Quercus suber'}
        land = {'mvc50': {'source_id': 'mvc50', 'edition': '2019-11', 'status': 'available', 'properties': props},
                'trees': {'status': 'available', 'items': [{'host_id': 'pine'}]}}
        expected, _ = resolve_land_context(land, index, ids['host_taxa'])
        with (patch.object(gis, 'reconstruct_observation', return_value={'gis_context_v0': {}, 'layers': {}}),
              patch('rainmapper_core.mushroom_gis_recovery.forest_lookup',
                    return_value={**land['trees'], 'land_context': {'mvc50': land['mvc50']}})):
            report = observation_preview(41.7291191, 2.747922, rules, cats)
        for field, values in report['values'].items():
            self.assertEqual(values, expected['values'][field])
            self.assertEqual(report['sources'][field], expected['sources'][field])
        self.assertEqual(expected['values']['soil_tendency_ids'], ['soil_siliceous'])
        # Reject other editions, pending rules, and outside coverage.
        for state, edition in [('available', '2027'), ('not_covered', '2019-11')]:
            land['mvc50'].update(status=state, edition=edition)
            self.assertFalse(resolve_land_context(land, index, ids['host_taxa'])[0]['values']['soil_tendency_ids'])
        land['mvc50'].update(status='available', edition='2019-11')
        rules['exact_value_mappings'][0]['review_status'] = 'pending_review'
        self.assertFalse(resolve_land_context(land, compile_exact_mappings(rules, ids), ids['host_taxa'])[0]['values']['soil_tendency_ids'])
