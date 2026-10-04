"""Private overlay projection, with resource bounds and no persistence side effects."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_map_known_sites as overlay


class KnownSitesOverlayTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'sites.json'
        for patch in (mock.patch.object(overlay.mushroom_known_sites, 'persistent_path', return_value=self.path),
                      mock.patch.object(overlay, '_cache', None)):
            patch.start(); self.addCleanup(patch.stop)
        self.polygon = {'type': 'Polygon', 'coordinates': [[[1, 41], [2, 41], [2, 42], [1, 41]]]}
        self.area = {'area_id': 'area', 'name': '<b>Area</b>', 'geometry': self.polygon, 'notes': 'PRIVATE'}
        self.micro = {'micro_area_id': 'micro', 'area_id': 'area', 'name': 'Micro',
                      'geometry': {'type': 'MultiPolygon', 'coordinates': [self.polygon['coordinates']]},
                      'representative_location': {'lon': 1.75, 'lat': 41.5}, 'ecology': {'notes': 'PRIVATE'}}

    def write(self, areas=None, micros=None):
        self.path.write_text(json.dumps({'areas': [self.area] if areas is None else areas,
                                        'micro_areas': [self.micro] if micros is None else micros}))

    def test_projection_preserves_polygons_and_only_exports_map_fields(self):
        self.write(); before = self.path.read_bytes()
        raw = overlay.response(); rows = json.loads(raw)['features']
        self.assertNotIn(b'PRIVATE', raw)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(rows[0]['geometry'], self.polygon)
        self.assertEqual(rows[1]['geometry']['type'], 'MultiPolygon')
        self.assertEqual(rows[1]['properties']['label_point'], [1.75, 41.5])
        self.assertEqual(rows[0]['properties']['name'], '<b>Area</b>')
        self.assertEqual(set(rows[0]['properties']), {'kind', 'name', 'label_point'})
        self.assertEqual(len(list(self.path.parent.iterdir())), 1)

    def test_missing_file_does_not_seed_and_points_do_not_invent_boundaries(self):
        self.assertEqual(json.loads(overlay.response())['features'], [])
        self.assertFalse(self.path.exists())
        self.area.update(geometry=None, representative_location={'lat': 41, 'lon': 2})
        self.micro['geometry'] = None; self.micro['representative_location'] = None
        self.write(); rows = json.loads(overlay.response())['features']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['geometry'], {'type': 'Point', 'coordinates': [2, 41]})

    def test_archived_areas_and_their_microareas_are_hidden(self):
        self.area['archived'] = True; self.write()
        self.assertEqual(json.loads(overlay.response())['features'], [])
        self.area['archived'] = False; self.micro['archived'] = True; self.write()
        self.assertEqual(len(json.loads(overlay.response())['features']), 1)

    def test_bounds_reject_before_encoding_and_cache_updates_with_source(self):
        self.write()
        for name, limit in [('MAX_FILE_BYTES', 1), ('MAX_FEATURES', 1), ('MAX_VERTICES', 7)]:
            with self.subTest(name=name), mock.patch.object(overlay, name, limit), \
                    mock.patch.object(overlay, '_encode') as encode:
                with self.assertRaisesRegex(overlay.SitesError, 'source_limit'):
                    overlay.response()
                encode.assert_not_called()
        with mock.patch.object(overlay, 'MAX_RESPONSE_BYTES', 10):
            with self.assertRaisesRegex(overlay.SitesError, 'response_limit'):
                overlay.response()
        initial = overlay.response()
        with mock.patch.object(overlay, '_shape', side_effect=AssertionError('cache')):
            self.assertIs(overlay.response(), initial)
        self.area['name'] = 'Changed area'; self.write()
        self.assertNotEqual(overlay.response(), initial)

    def test_invalid_coordinates_fail_without_invalid_geojson(self):
        for point in ([True, 41], [181, 41], [1, float('nan')], [1, 41, 9]):
            self.polygon['coordinates'][0][1] = point; self.write()
            with self.assertRaisesRegex(overlay.SitesError, 'invalid_geometry'):
                overlay.response()


if __name__ == '__main__':
    unittest.main()
