"""Coverage and lossless editing through the same contract as the map."""
import copy
from collections import Counter
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'rainmapper-app/app'))
import mushroom_gis_mappings_ui as ui
from rainmapper_core.mushroom_gis_inventory import source_inventory, upsert_mapping
from rainmapper_core.mushroom_map_ecology import compile_exact_mappings, MAPPING_CATALOGS


class InventoryTests(unittest.TestCase):
    def test_full_published_inventory_without_reconstruction(self):
        rows = ui.mapping_rows({}, None)
        counts = Counter((r['source_id'], r['field']) for r in rows)
        self.assertEqual(counts, {('geology_50000', 'Codi'): 1055,
                                 ('mvc50', 'LLFISCAT_t'): 202,
                                 ('mvc50', 'LLVA_niv2t'): 62,
                                 ('mvc50', 'LLVA_Subst'): 13})
        self.assertTrue(all(r['status'] == 'pending_review' and r['mapping'] is None for r in rows))
        self.assertEqual(len({r['key'] for r in rows}), len(rows))
        self.assertFalse(any('mapped_soil_tendency_ids' in v for s in source_inventory() for v in s['values']))

    def group(self):
        return {'source_id': 'geology_50000', 'edition': '2024-12', 'field': 'Codi',
                'raw_values': ['EÇOrgl', 'Cagl'], 'mapped_soil_tendency_ids': ['soil_sandy'],
                'review_status': 'accepted', 'confidence': 'medium', 'review_ref': 'old-review',
                'metadata': {'provenance': 'preserve'}}

    def test_group_visible_once_and_correct_edition_survives_edit(self):
        group = self.group()
        another_edition = dict(group, edition='2025-12')
        payload = {'exact_value_mapping_groups': [group, another_edition]}
        old = {'unmapped_candidates': [{'source_id': 'geology_50000', 'field': 'Codi', 'raw_value': 'EÇOrgl',
                                       'suggested_mapped_soil_tendency_ids': ['soil_calcareous']}]}
        rows = ui.mapping_rows(payload, old)
        matching = [r for r in rows if r['raw_value'] == 'EÇOrgl']
        self.assertEqual(len(matching), 2)
        row = next(r for r in matching if r['edition'] == '2024-12')
        self.assertEqual(row['mapping']['mapped_soil_tendency_ids'], ['soil_sandy'])
        self.assertIn('Jújols', ui.raw_value_label(row))
        form = ui.render_mapping_detail(row, {})
        self.assertIn('name="edition" value="2024-12"', form)
        self.assertIn('name="review_ref" value="old-review"', form)
        replacement = {'source_id': group['source_id'], 'edition': group['edition'], 'field': 'Codi',
                       'raw_value': 'EÇOrgl', 'mapped_soil_tendency_ids': ['soil_siliceous'],
                       'review_status': 'accepted', 'review_ref': 'new-evidence'}
        upsert_mapping(payload, replacement)
        self.assertEqual(payload['exact_value_mapping_groups'][0]['raw_values'], ['Cagl'])
        self.assertEqual(payload['exact_value_mapping_groups'][1], another_edition)
        self.assertEqual(payload['exact_value_mappings'][0]['metadata'], group['metadata'])
        ids = {catalog: {'soil_siliceous', 'soil_sandy'} if catalog == 'soil_types' else set() for catalog in MAPPING_CATALOGS.values()}
        lookup = compile_exact_mappings(payload, ids)
        self.assertEqual(lookup[(group['source_id'], '2024-12', 'Codi', 'EÇOrgl')]['mapped_soil_tendency_ids'], ['soil_siliceous'])
        self.assertEqual(lookup[(group['source_id'], '2024-12', 'Codi', 'Cagl')]['mapped_soil_tendency_ids'], ['soil_sandy'])

    def test_deselect_removes_targets_and_pending_does_not_apply(self):
        payload = {'exact_value_mapping_groups': [self.group()]}
        upsert_mapping(payload, {'source_id': 'geology_50000', 'edition': '2024-12',
                                'field': 'Codi', 'raw_value': 'EÇOrgl', 'review_status': 'pending_review'})
        self.assertNotIn('mapped_soil_tendency_ids', payload['exact_value_mappings'][0])
        self.assertNotIn('review_ref', payload['exact_value_mappings'][0])
        self.assertEqual(payload['exact_value_mapping_groups'][0]['raw_values'], ['Cagl'])

    def test_manual_mvc_decision_is_preserved(self):
        mapping = {'source_id': 'mvc50', 'field': 'LLVA_Subst', 'raw_value': 'Silici',
                   'review_status': 'accepted', 'mapped_soil_tendency_ids': ['soil_siliceous']}
        payload = {'exact_value_mappings': [mapping]}
        before = copy.deepcopy(payload)
        rows = ui.mapping_rows(payload, None)
        self.assertEqual(payload, before)
        row = next(r for r in rows if r['source_id'] == 'mvc50' and r['raw_value'] == 'Silici')
        self.assertEqual(row['mapping'], mapping)
        self.assertEqual(row['status'], 'accepted')

    def test_no_description_from_another_code(self):
        candidates = {'unmapped_candidates': [
            {'source_id': 'geology_50000', 'field': 'Descripcio', 'raw_value': 'unrelated'},
            {'source_id': 'geology_50000', 'field': 'Codi', 'raw_value': 'unknown-code'},
        ]}
        self.assertNotIn('description', ui.candidate_rows(candidates)[0]['context'])

    def test_duplicate_refused_without_mutation(self):
        payload = {'exact_value_mapping_groups': [self.group(), self.group()]}
        before = copy.deepcopy(payload)
        with self.assertRaises(ValueError):
            upsert_mapping(payload, {'source_id': 'geology_50000', 'edition': '2024-12',
                                     'field': 'Codi', 'raw_value': 'EÇOrgl'})
        self.assertEqual(payload, before)

    def test_reconstructor_consumes_current_groups_not_old_suggestions(self):
        from rainmapper_core.mushroom_gis_lab import exact_mapping_lookup
        group = self.group()
        old = {'source_id': 'geology_50000', 'field': 'Codi', 'raw_value': 'EÇOrgl',
               'review_status': 'accepted', 'mapped_soil_tendency_ids': ['soil_calcareous']}
        payload = {'exact_value_mappings': [old], 'exact_value_mapping_groups': [group]}
        lookup = exact_mapping_lookup(payload)
        self.assertEqual(lookup[('geology_50000', 'Codi', 'EÇOrgl')]['mapped_soil_tendency_ids'], ['soil_sandy'])
        upsert_mapping(payload, {'source_id': 'geology_50000', 'edition': '2024-12', 'field': 'Codi',
                                 'raw_value': 'EÇOrgl', 'review_status': 'pending_review'})
        self.assertEqual(exact_mapping_lookup(payload)[('geology_50000', 'Codi', 'EÇOrgl')]['review_status'], 'pending_review')
        self.assertEqual(payload['exact_value_mappings'][0], old)
        # An unrelated future edition cannot silently change the legacy reader.
        future = {'exact_value_mappings': [old], 'exact_value_mapping_groups': [dict(group, edition='2099')]}
        self.assertEqual(exact_mapping_lookup(future)[('geology_50000', 'Codi', 'EÇOrgl')], old)

    def test_legacy_bookmark_selects_same_code(self):
        rows = ui.mapping_rows({}, None)
        row = ui.selected_mapping_row(rows, ui.mapping_key('geology_50000', 'Codi', 'EÇOrgl'))
        self.assertEqual((row['raw_value'], row['edition']), ('EÇOrgl', '2024-12'))

    def test_geology_case_distinguishes_units_in_map_and_reconstruction(self):
        from rainmapper_core.mushroom_gis_lab import exact_mapping_lookup, apply_exact_layer_mappings
        rules = [dict(source_id='geology_50000', edition='2024-12', field='Codi',
                      raw_value=code, review_status='accepted', review_ref='ICGC',
                      mapped_lithology_ids=targets)
                 for code, targets in [('KSCm', ['lith_calcareous_marl']),
                                       ('KScm', ['lith_calcareous_marl', 'lith_limestone'])]]
        payload = {'exact_value_mappings': rules}
        catalog = {'catalogs': {group: [{'id': v} for v in
                     (['lith_calcareous_marl', 'lith_limestone'] if group=='lithology_types' else [])]
                     for group in MAPPING_CATALOGS.values()}}
        ids = {group: {v['id'] for v in rows} for group, rows in catalog['catalogs'].items()}
        map_index = compile_exact_mappings(payload, ids)
        self.assertEqual(len(exact_mapping_lookup(payload)), 2)
        for rule in rules:
            result = apply_exact_layer_mappings('geology_50000',
                {'status': 'ok', 'properties': {'Codi': rule['raw_value']}}, payload, catalog)
            expected = map_index[('geology_50000', '2024-12', 'Codi', rule['raw_value'])]['mapped_lithology_ids']
            self.assertEqual(result['mapped_lithology_ids'], expected)

    def test_map_adapts_old_publication_name_without_renaming_shared_data(self):
        from rainmapper_core.mushroom_map_ecology import mapping_key
        payload = {'exact_value_mapping_groups': [self.group()]}
        before = copy.deepcopy(payload)
        ids = {group: {'soil_sandy'} if group=='soil_types' else set() for group in MAPPING_CATALOGS.values()}
        index = compile_exact_mappings(payload, ids)
        old_point = {'source_id':'icgc_geologia_50000','edition':'2024-12','field':'Codi'}
        self.assertIn(mapping_key(old_point,'EÇOrgl'), index)
        old_payload = copy.deepcopy(payload)
        old_payload['exact_value_mapping_groups'][0]['source_id'] = 'icgc_geologia_50000'
        self.assertEqual(set(compile_exact_mappings(old_payload, ids)), set(index))
        self.assertEqual(payload, before)

    def test_table_paginates_and_can_reach_last_value(self):
        rows = ui.mapping_rows({}, None)
        first = ui.render_mapping_table(rows, rows[0])
        last = ui.render_mapping_table(rows, rows[-1])
        self.assertEqual(first.count('data-href='), 100)
        self.assertIn('Siguiente', first)
        self.assertIn('Anterior', last)
        self.assertIn('1301–1332 / 1332', last)

    def test_form_save_validates_and_preserves_effective_identity(self):
        from tests.test_web_server_auth import load_web_server_module
        web = load_web_server_module()
        group = self.group()
        form = {k: [v] for k, v in {'source_id': group['source_id'], 'edition': group['edition'],
            'field': 'Codi', 'raw_value': 'EÇOrgl', 'confidence': 'medium', 'review_status': 'accepted',
            'review_ref': 'test-evidence'}.items()}
        form['mapped_soil_tendency_ids'] = ['soil_siliceous']
        mapping, message = web.gis_mapping_from_form(form)
        self.assertIsNotNone(mapping, message)
        payload = {'exact_value_mapping_groups': [group]}
        ok, message = web.upsert_exact_gis_mapping(payload, mapping)
        self.assertTrue(ok, message)
        self.assertEqual(payload['exact_value_mappings'][0]['edition'], '2024-12')
        del form['review_ref']
        self.assertIsNone(web.gis_mapping_from_form(form)[0])


if __name__ == '__main__':
    unittest.main()
