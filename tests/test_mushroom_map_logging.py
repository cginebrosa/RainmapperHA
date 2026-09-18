"""Operational failures must be visible without corrupting the reader protocol."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from rainmapper_core.mushroom_map_execution import PointExecutor
from rainmapper_core.mushroom_map_queries import QueryBroker

ROOT = Path(__file__).resolve().parents[1]


class MapLoggingTests(unittest.TestCase):
    def test_broker_initialization_preserves_original_exception_in_log(self):
        executor = Mock()
        executor.ready.side_effect = OSError("missing_catalog_fixture")
        with self.assertLogs('rainmapper_core.mushroom_map_queries', level='ERROR') as logs:
            broker = QueryBroker(executor)
            broker.thread.join(timeout=2)
            broker.close()
        self.assertFalse(broker.local_ready)
        self.assertIn('missing_catalog_fixture', '\n'.join(logs.output))
        self.assertIsNotNone(logs.records[0].exc_info)

    def test_readiness_false_identifies_component_without_changing_gate(self):
        executor = object.__new__(PointExecutor)
        executor.lock = threading.Lock()
        executor.geography = Mock()
        executor.weather = Mock()
        executor.model = Mock()
        executor.geography.call.return_value = {'geography_ready': True}
        executor.weather.call.return_value = {'weather_ready': False}
        executor.model.call.return_value = {'model_ready': True}
        with self.assertLogs('rainmapper_core.mushroom_map_execution', level='ERROR') as logs:
            self.assertFalse(executor.ready())
        self.assertIn('weather reader reported unavailable', '\n'.join(logs.output))
        executor.weather.call.return_value = {'weather_ready': True}
        with self.assertNoLogs('rainmapper_core.mushroom_map_execution', level='WARNING'):
            self.assertTrue(executor.ready())

    def test_weather_and_model_failed_capability_has_traceback_and_valid_json(self):
        cases = [('weather', 'rainmapper_core.mushroom_map_weather.PointWeatherReader._refresh',
                  ['--data-root', '/missing', '--stations-file', '/missing']),
                 ('model', 'rainmapper_core.mushroom_map_model_runtime.PointModelRuntime._refresh',
                  [arg for key in ('registry-path', 'models-root', 'profiles-path', 'data-root', 'stations-file')
                   for arg in ('--' + key, '/missing')])]
        for name, target, arguments in cases:
            with self.subTest(reader=name):
                script = ROOT/'scripts'/f'prediction-map-local-{name}.py'
                output = io.StringIO()
                with patch.object(sys, 'argv', [str(script), *arguments]), \
                        patch.object(sys, 'stdin', io.StringIO('{"id":7,"op":"capabilities"}\n')), \
                        patch(target, side_effect=ValueError('broken_' + name + '_fixture')), \
                        contextlib.redirect_stdout(output), self.assertLogs('__main__', level='ERROR') as logs:
                    runpy.run_path(str(script), run_name='__main__')
                self.assertEqual(json.loads(output.getvalue()), {'id': 7, name + '_ready': False})
                self.assertIn('broken_' + name + '_fixture', '\n'.join(logs.output))
                self.assertIsNotNone(logs.records[0].exc_info)

    def test_geography_initialization_logs_component_and_exception(self):
        script = ROOT/'scripts'/'prediction-map-local-geography.py'
        output = io.StringIO()
        args = [str(script), '--profiles', '/missing', '--ecology-catalogs', '/missing', '--gis-mappings', '/missing']
        with patch.object(sys, 'argv', args), \
                patch.object(sys, 'stdin', io.StringIO('{"id":3,"op":"capabilities"}\n')), \
                patch('rainmapper_core.mushroom_map_ecology.EcologyReader', side_effect=ValueError('bad_profile_fixture')), \
                contextlib.redirect_stdout(output), self.assertLogs('__main__', level='ERROR') as logs:
            runpy.run_path(str(script), run_name='__main__')
        self.assertFalse(json.loads(output.getvalue())['geography_ready'])
        self.assertIn('ecology reader initialization failed', '\n'.join(logs.output))
        self.assertIn('bad_profile_fixture', '\n'.join(logs.output))

    def test_real_subprocess_stderr_reaches_parent_without_polluting_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory)/'reader.py'
            script.write_text('import sys,json\nfor line in sys.stdin:\n r=json.loads(line); print("reader failure fixture",file=sys.stderr,flush=True); print(json.dumps({"id":r["id"],"ready":False}),flush=True)\n')
            program = '''import sys,json
from rainmapper_core.mushroom_map_execution import ResidentReader
reader=ResidentReader(sys.executable, 'unused', [])
reader.command=[sys.executable, sys.argv[1]]
try: print(json.dumps(reader.call({'op':'capabilities'})))
finally: reader.close()
'''
            result = subprocess.run([sys.executable, '-B', '-c', program, str(script)], cwd=ROOT,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {'ready': False})
            self.assertIn('reader failure fixture', result.stderr)


if __name__ == '__main__':
    unittest.main()
