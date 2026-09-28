import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from rainmapper_core import mushroom_territorial_reader as reader
from rainmapper_core import mushroom_gis_lab as lab
from rainmapper_core.mushroom_territorial_context import resolve_context


class TerritorialReaderTests(unittest.TestCase):
    def test_paths_are_local_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(reader.dataset_config(root))
            config = {'format': reader.FORMAT, 'geography': {'mvc50_index': '../outside'}}
            (root/reader.CONFIG_FILE).write_text(json.dumps(config))
            with self.assertRaises(ValueError): reader.dataset_config(root)
            config['geography']['mvc50_index'] = 'mvc.sqlite'
            (root/reader.CONFIG_FILE).write_text(json.dumps(config))
            self.assertEqual(reader.dataset_config(root)['mvc50_index'], str(root.resolve()/'mvc.sqlite'))

    def test_one_reader_and_frozen_catalog_for_multiple_points(self):
        catalogs = {'host_taxa': []}
        child = Mock()
        child.call.return_value = {'status': 'not_connected', 'land_context': {}}
        with patch.object(reader, 'ResidentReader', return_value=child) as factory:
            with reader.TerritorialSession({}, {}, catalogs) as session:
                args = factory.call_args.args[2]
                catalog_path = Path(args[args.index('--catalogs')+1])
                self.assertEqual(json.loads(catalog_path.read_text()), catalogs)
                session.lookup(41, 2)
                session.lookup(42, 3)
            factory.assert_called_once()
            self.assertEqual(child.call.call_count, 2)
            child.close.assert_called_once()
            self.assertFalse(catalog_path.exists())

    def test_reconstruction_uses_dataset_session_without_live_map_or_raw_vectors(self):
        result = {'resolution': resolve_context({'mvc50': {'soil_tendency_ids': ['soil_siliceous']}}),
                  'land_context': {}}
        session = Mock()
        session.lookup.return_value = result
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        rows = [{'observation_id': f'o{i}', 'location': {'lat': 41, 'lon': 2}} for i in range(2)]
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(reader, 'dataset_config', return_value={'mvc50_index': 'frozen'}) as config, \
             patch.object(reader, 'TerritorialSession', return_value=session) as factory, \
             patch.object(lab, 'sample_dem', return_value={'status': 'ok', 'elevation_m': 50}), \
             patch.object(lab, 'vector_layers', side_effect=AssertionError('raw GIS consulted')), \
             patch('rainmapper_core.mushroom_gis_recovery.territorial_session', side_effect=AssertionError('live map consulted')):
            root = Path(tmp)
            data = lab.reconstruct_observations(rows, ['o0', 'o1'], root/'out.json',
                    gis_root_path=root, qgis_points_path=root/'points.json')
            config.assert_called_once_with(root)
            factory.assert_called_once()
            session.__exit__.assert_called_once()
            self.assertEqual(session.lookup.call_count, 2)
            for row in data['results']:
                self.assertEqual(row['gis_context_v0']['soil_tendency_ids'], ['soil_siliceous'])

    def test_microarea_resolves_priority_before_aggregating(self):
        from contextlib import nullcontext
        session = Mock()
        resolution = resolve_context({'mfe25': {'host_ids': ['mfe_host']},
                                      'mvc50': {'host_ids': ['mvc_host'], 'forest_type_ids': ['oak']}})
        session.lookup.return_value = {'resolution': resolution, 'land_context': {}}
        with patch.object(lab, 'polygon_sample_grid', return_value=[(2,41,0,0),(2.1,41.1,1,1)]), \
             patch.object(lab, 'sample_dem', return_value={'status': 'missing'}), \
             patch('rainmapper_core.mushroom_gis_recovery.territorial_session', return_value=nullcontext(session)), \
             patch.object(lab, 'vector_layers', side_effect=AssertionError('raw GIS consulted')):
            report = lab.derive_site_gis_dem({'type':'Polygon','coordinates':[[[2,41],[3,41],[3,42],[2,41]]]}, {}, {})
        self.assertEqual(report['gis']['host_ids'], ['mfe_host'])
        self.assertEqual(report['gis']['forest_type_ids'], ['oak'])


if __name__ == '__main__': unittest.main()
