"""A broken territorial layer must not remove other usable sources."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('recovery_adapter', Path(__file__).resolve().parents[1]/'scripts/recover-mushroom-forest.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class RecoveryAdapterTests(unittest.TestCase):
    def run_adapter(self, forest, mvc):
        cover = Mock()
        cover.lookup.return_value = {'status': 'available', 'properties': {'nivell_2': '222'}}
        request = json.dumps({'id': 'point1', 'lat': 41.7, 'lon': 2.7})+'\n'
        output = io.StringIO()
        with patch.object(adapter.sys, 'argv', ['recover', '--index', 'forest', '--mvc50-index', 'mvc', '--land-cover', 'cover', '--catalogs', 'catalog']), \
             patch.object(adapter.sys, 'stdin', Mock(buffer=io.BytesIO(request.encode()))), \
             patch.object(adapter.sys, 'stdout', output), \
             patch.object(adapter, 'SourceIdentities'), \
             patch.object(adapter, 'ForestReader', forest), \
             patch.object(adapter, 'VegetationReader', mvc), \
             patch.object(adapter, 'LandReader', return_value=cover), self.assertLogs(level='ERROR'):
            adapter.main()
        cover.close.assert_called_once()
        result = json.loads(output.getvalue())
        self.assertEqual(result['id'], 'point1')
        self.assertEqual(result['land_context']['vegetation'], cover.lookup.return_value)
        self.assertEqual(result['land_context']['geology']['status'], 'not_connected')
        self.assertEqual(result['land_context']['mvc50']['status'], 'unavailable')
        return result

    def test_initialization_failure_keeps_other_sources(self):
        result = self.run_adapter(Mock(side_effect=OSError('missing')), Mock(side_effect=ValueError('invalid index')))
        self.assertEqual(result['status'], 'unavailable')

    def test_query_failure_keeps_other_sources(self):
        forest, mvc = Mock(), Mock()
        forest.lookup.side_effect = OSError('changed')
        mvc.lookup.side_effect = RuntimeError('query failed')
        result = self.run_adapter(Mock(return_value=forest), Mock(return_value=mvc))
        self.assertEqual(result['status'], 'unavailable')
        forest.close.assert_called_once()
        mvc.close.assert_called_once()
