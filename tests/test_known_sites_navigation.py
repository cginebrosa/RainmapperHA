import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rainmapper-app/app'))
import mushroom_known_sites_ui as ui


class ObservationMapContextTests(unittest.TestCase):
    def setUp(self):
        self.payload = {'observations': [
            {'observation_id': 'one', 'species_id': 'amanita_caesarea', 'location': {'lat': 42, 'lon': 2, 'precision_m': 71}},
            {'observation_id': 'other', 'location': {'lat': 40, 'lon': 1}, 'notes': 'private unrelated data'},
        ]}

    def test_only_requested_observation_and_saved_coordinates(self):
        result = ui.observation_map_context(self.payload, {'observation_id': ['one']})
        self.assertEqual([2, 42], result['coordinates'])
        self.assertFalse(result['draft_position'])
        self.assertNotIn('private unrelated data', str(result))
        self.assertIn('obs_id=one', result['href'])

    def test_invalid_overrides_cannot_poison_map(self):
        for lat, lon in [('nan', '2'), ('42', 'inf'), ('91', '2'), ('42', '-181'), ('', '')]:
            with self.subTest(lat=lat, lon=lon):
                query = {'observation_id': ['one'], 'observation_lat': [lat], 'observation_lon': [lon]}
                self.assertEqual([2, 42], ui.observation_map_context(self.payload, query)['coordinates'])
                query.pop('observation_id')
                self.assertIsNone(ui.observation_map_context(self.payload, query))

    def test_form_position_is_explicitly_distinguished(self):
        result = ui.observation_map_context(self.payload, {'observation_id': ['one'], 'observation_lat': ['0'], 'observation_lon': ['0']})
        self.assertEqual([0, 0], result['coordinates'])
        self.assertTrue(result['draft_position'])
        self.assertEqual(42, self.payload['observations'][0]['location']['lat'])

    def test_new_observation_and_missing_reference(self):
        self.assertIsNone(ui.observation_map_context(self.payload, {'observation_id': ['missing']}))
        result = ui.observation_map_context(self.payload, {'observation_lat': ['42'], 'observation_lon': ['2']})
        self.assertEqual('', result['id'])
        self.assertEqual('', result['href'])
        self.assertEqual([], result['details'])
