import ast
import contextlib
import csv
import io
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd
import pyarrow.parquet as pq

from rainmapper_core.meteoclimatic_fixed_coordinates import (
    FILENAME, MAX_FILE_BYTES, FixedCoordinates, load_fixed_coordinates, location_metadata,
)
from rainmapper_core.atomic_io import write_csv_atomic
from rainmapper_core.weather_coordinates import protect_frame
from rainmapper_core.weather_history_capture import capture_fresh_weather_rows
from rainmapper_core import meteoclimatic_history
from rainmapper_core.incremental_upsert import upsert_incremental
from rainmapper_core.weather_history_archive import archive_and_close_pending
from rainmapper_core.weather_history_dataset import resolve_weather_generation, sha256_file
from rainmapper_core.weather_history_writer import (
    archive_pending_batches, acknowledge_archived_pending, InjectedWeatherHistoryFailure,
    WeatherHistoryCoordinateConflict,
)
from rainmapper_core.weather_live_csv import apply_pending_to_live_csv
from tests import test_weather_history_writer as fixtures

CODE = 'ESCAT0800000008510E'


class FixedCoordinateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / 'Data'
        self.data.mkdir()
        self.path = self.data.parent / FILENAME

    def test_missing_empty_comments_bom_and_inline_comment(self):
        self.assertEqual(load_fixed_coordinates(self.data), {})
        self.path.write_text('\ufeff# heading\n \t# disabled 49.99 2.32\n\n' + CODE + ' 41.99 2.32 # active\n')
        self.assertEqual(load_fixed_coordinates(self.data), {CODE: {'lat': 41.99, 'lon': 2.32}})
        self.path.write_text('# ' + CODE + ' 41.99 2.32\n')
        self.assertEqual(load_fixed_coordinates(self.data), {})
        self.path.write_text('')
        self.assertEqual(load_fixed_coordinates(self.data), {})

    def test_bad_entries_report_line_number_and_never_silently_skip(self):
        for entry in (CODE + ' nan 2', CODE + ' inf 2', CODE + ' 91 2', CODE + ' 41 -181',
                      CODE + ' 41', CODE + ' 41 2 unexpected', 'a/b 41 2',
                      CODE + ' 41 2\n' + CODE + ' 42 2'):
            with self.subTest(entry=entry):
                self.path.write_text('# header\n' + entry)
                with self.assertRaisesRegex(ValueError, FILENAME + r':[23]:'):
                    load_fixed_coordinates(self.data)
        self.path.write_text('#' * (MAX_FILE_BYTES + 1))
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            load_fixed_coordinates(self.data)

    def test_resolves_data_symlink_to_share_root(self):
        link = self.data.parent / 'app' / 'Data'
        link.parent.mkdir()
        link.symlink_to(self.data, target_is_directory=True)
        self.path.write_text(CODE + ' 41.99 2.32')
        self.assertIn(CODE, load_fixed_coordinates(link))

    def test_scoped_to_source_log_once_and_weather_untouched(self):
        target = {CODE: {'lat': 41.99, 'lon': 2.32, 'altitude': 465}}
        policy = FixedCoordinates(target)
        row = {'source': 'meteoclimatic', 'station_code': CODE, 'lat': 49.99, 'lon': 2.32,
               'rain_mm': 12.3, 'min_temp_celsius': 8.6, 'altitude': 121, 'municipality': 'Amiens'}
        before = dict(row)
        log = io.StringIO()
        with contextlib.redirect_stderr(log):
            for _ in range(10):
                result = policy.apply(row)
        self.assertEqual(row, before)
        self.assertEqual(result['lat'], 41.99)
        self.assertEqual(result['altitude'], 465)
        self.assertIsNone(result['municipality'])
        self.assertEqual((result['rain_mm'], result['min_temp_celsius']), (12.3, 8.6))
        self.assertEqual(log.getvalue().count('coordinates received'), 1)
        other = {**row, 'source': 'meteocat'}
        self.assertIs(policy.apply(other), other)
        absent = {**row, 'station_code': 'OTHER'}
        self.assertIs(policy.apply(absent), absent)

    def test_metadata_from_matching_registry_only(self):
        path = self.data / 'estacions_meteoclimatic.csv'
        header = 'Codi Estació,Latitud,Longitud,Altitud,Municipi,Provincia,Comarca\n'
        path.write_text(header + CODE + ',49.99,2.32,121,Amiens,Somme,\n')
        coords = {CODE: {'lat': 41.99, 'lon': 2.32}}
        catalog = [{'source': 'meteoclimatic', 'station_code': CODE, 'lat': 41.99, 'lon': 2.32, 'altitude': 465}]
        self.assertEqual(location_metadata(self.data, coords, catalog)[CODE],
                         {**coords[CODE], 'altitude': 465, 'municipality': None, 'province': None, 'county': None})
        path.write_text(header + CODE + ',41.99,2.32,465,Roda de Ter,Barcelona,Osona\n')
        result = location_metadata(self.data, coords, catalog)[CODE]
        self.assertEqual(result['municipality'], 'Roda de Ter')
        self.assertEqual(result['province'], 'Barcelona')

    def test_fresh_frame_and_disabled_line_restore_provider(self):
        self.path.write_text(CODE + ' 41.99 2.32')
        frame = pd.DataFrame([{'Codi Estació': CODE, 'Latitud': '49.99', 'Longitud': '2.32', 'Total': 7.5}])
        fixed = FixedCoordinates(load_fixed_coordinates(self.data), log=False).apply_frame(frame)
        self.assertEqual((fixed.iloc[0]['Latitud'], fixed.iloc[0]['Total']), (41.99, 7.5))
        self.assertEqual(frame.iloc[0]['Latitud'], '49.99')
        self.path.write_text('#' + CODE + ' 41.99 2.32')
        self.assertIs(FixedCoordinates(load_fixed_coordinates(self.data)).apply_frame(frame), frame)

    def test_source_enrichment_receives_fixed_location_and_refreshes_wrong_registry(self):
        # Import only the source function: importing rainmapper starts the CLI.
        tree = ast.parse(Path('rainmapper_core/rainmapper.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'refresh_estacions_meteoclimatic')
        namespace = {'pd': pd, 'math': __import__('math'), 're': __import__('re'), '_DATA_PATH': str(self.data) + '/',
                     'get_googlemaps': mock.Mock(return_value=(465, 'Roda de Ter', 'Barcelona')),
                     'write_csv_atomic': mock.Mock()}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<source function>', 'exec'), namespace)
        frame = pd.DataFrame([{'Codi Estació': CODE, 'Estació': 'Roda de Ter (Barcelona)', 'Latitud': 49.99,
                               'Longitud': 2.32, 'Altitud': 121, 'Municipi': 'Amiens', 'Provincia': 'Somme', 'Comarca': ''}])
        frame.to_csv(self.data / 'estacions_meteoclimatic.csv', index=False)
        fixed = FixedCoordinates({CODE: {'lat': 41.99, 'lon': 2.32}}, log=False).apply_frame(frame)
        enriched = namespace['refresh_estacions_meteoclimatic'](fixed)
        namespace['get_googlemaps'].assert_called_once_with(41.99, 2.32)
        self.assertEqual(enriched.iloc[0]['Municipi'], 'Roda de Ter')
        self.assertEqual(enriched.iloc[0]['Altitud'], 465)


class MeteoclimaticStationCacheTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WeatherHistoryWriterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.data = self.fixture.data_dir
        self.path = self.data / 'estacions_meteoclimatic.csv'
        tree = ast.parse(Path('rainmapper_core/rainmapper.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == 'refresh_estacions_meteoclimatic')
        self.geocode = mock.Mock(return_value=(900, 'Updated town', 'Updated province'))
        namespace = {'pd': pd, 'math': __import__('math'), 're': __import__('re'),
                     '_DATA_PATH': str(self.data) + '/', 'get_googlemaps': self.geocode,
                     'write_csv_atomic': write_csv_atomic}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<source function>', 'exec'), namespace)
        self.refresh = namespace['refresh_estacions_meteoclimatic']
        self.namespace = namespace

    def station(self, code=CODE, **changes):
        return {'Codi Estació': code, 'Estació': 'Station (Province)', 'Latitud': 41.99,
                'Longitud': 2.32, 'Altitud': 465., 'Municipi': 'Cached town',
                'Provincia': 'Cached province', 'Comarca': 'County', **changes}

    def test_numeric_provider_reuses_text_cache_with_dot_and_comma_decimals(self):
        cached = pd.DataFrame([
            self.station(Altitud='465.0', Latitud='41.99', Longitud='2.3200'),
            self.station('SECOND', Altitud='16,5', Latitud='41,12', Longitud='1,27'),
        ])
        cached.to_csv(self.path, index=False)
        incoming = pd.DataFrame([
            self.station(Altitud=0., Municipi='Provider town'),
            self.station('SECOND', Altitud=0., Latitud=41.12, Longitud=1.27),
        ])
        incoming['Total'] = [9.5, 3.2]
        incoming['Data Local'] = '20261107'
        before = incoming.copy(deep=True)
        for _ in range(2):  # Also reuse the cache written by the preceding run.
            guarded = protect_frame(self.data, 'meteoclimatic', incoming, fresh=True)
            actual = self.refresh(guarded).set_index('Codi Estació')
            self.geocode.assert_not_called()
            self.assertEqual(actual.loc[CODE, 'Altitud'], 465.)
            self.assertEqual(actual.loc['SECOND', 'Altitud'], 16.5)
            self.assertEqual(actual.loc[CODE, 'Municipi'], 'Cached town')
            stored = pd.read_csv(self.path, decimal=',').set_index('Codi Estació')
            self.assertEqual(stored.loc['SECOND', 'Latitud'], 41.12)
            self.assertEqual(stored.loc['SECOND', 'Altitud'], 16.5)
        pd.testing.assert_frame_equal(incoming, before)
        # Follow the source's metadata merge through capture and history archive.
        merged = guarded.set_index('Codi Estació', drop=False)
        merged.update(actual)
        with mock.patch.dict(os.environ, {'RAINMAPPER_PARTITIONED_WEATHER_HISTORY': 'true'}):
            pending = capture_fresh_weather_rows(self.data, 'meteoclimatic', merged.reset_index(drop=True))
        rows = {r['station_code']: r for r in pq.ParquetFile(pending.data_path).read().to_pylist()}
        self.assertEqual((rows[CODE]['altitude'], rows[CODE]['rain_mm']), (465., 9.5))
        self.assertEqual((rows['SECOND']['altitude'], rows['SECOND']['rain_mm']), (16.5, 3.2))
        archive_pending_batches(self.data, reserve_bytes=0)
        generation = resolve_weather_generation(self.data, verify_hashes=True)
        catalog = {r['station_code']: r for r in pq.read_table(generation.object_path(generation.catalog.path)).to_pylist()}
        self.assertEqual((catalog[CODE]['lat'], catalog[CODE]['altitude']), (41.99, 465.))
        self.assertEqual((catalog['SECOND']['lat'], catalog['SECOND']['altitude']), (41.12, 16.5))
        partition = next(p for p in generation.partitions if p.source == 'meteoclimatic')
        archived = {r['station_code']: r for r in pq.ParquetFile(generation.object_path(partition.path)).read().to_pylist()}
        for code in (CODE, 'SECOND'):
            self.assertEqual({k: archived[code][k] for k in ('lat', 'lon', 'altitude', 'rain_mm')},
                             {k: rows[code][k] for k in ('lat', 'lon', 'altitude', 'rain_mm')})
        self.geocode.assert_not_called()

    def test_real_change_missing_altitude_and_new_station_still_fetch_metadata(self):
        cached = pd.DataFrame([self.station('UNCHANGED'), self.station('MOVED'),
                               self.station('MISSING', Altitud=float('nan'))])
        cached.to_csv(self.path, index=False)
        incoming = pd.DataFrame([self.station('UNCHANGED'), self.station('MOVED', Latitud=41.995),
                                 self.station('MISSING'), self.station('NEW', Latitud=41.5)])
        with contextlib.redirect_stdout(io.StringIO()):
            actual = self.refresh(incoming).set_index('Codi Estació')
        self.assertEqual(self.geocode.call_count, 3)
        self.assertEqual(self.geocode.call_args_list,
                         [mock.call(41.995, 2.32), mock.call(41.99, 2.32), mock.call(41.5, 2.32)])
        self.assertEqual(actual.loc['UNCHANGED', 'Altitud'], 465.)
        self.assertEqual(list(actual.loc[['MOVED', 'MISSING', 'NEW'], 'Altitud']), [900.] * 3)

    def test_source_pipeline_preserves_location_precision_before_cache_and_archive(self):
        # Execute the actual source functions, including the aggregation that
        # used to round every numeric column. Only the feed and Google are mocks.
        tree = ast.parse(Path('rainmapper_core/rainmapper.py').read_text())
        names = {'parse_meteoclimatic_patterns', 'create_total_meteoclimatic', 'create_meteoclimatic',
                 'save_incremental_meteoclimatic', 'read_incremental', 'create_empty_incremental',
                 'start_timing', 'record_timing', 'SourceTimings', 'utc_to_local', 'get_data_inici', 'get_data_fi'}
        nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
        columns = next(n for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == '_INCREMENTAL_COLUMNS' for t in n.targets))
        ns = self.namespace
        ns.update({'Path': Path, 'os': os, 'time_module': __import__('time'), 'pytz': __import__('pytz'),
                   'datetime': __import__('datetime').datetime, '_meteoclimatic_pattern': 'ESCAT',
                   '_start_date': '2026-11-01T00:00:00', '_end_date': '2026-11-07T23:59:00',
                   'protect_frame': protect_frame, 'upsert_incremental': upsert_incremental,
                   'METEOCLIMATIC_OBSERVATION_COLUMNS': meteoclimatic_history.OBSERVATION_COLUMNS})
        for name in ('read_meteoclimatic_observations', 'update_meteoclimatic_observations',
                     'retain_meteoclimatic_observations', 'build_meteoclimatic_daily_incremental'):
            ns[name] = getattr(meteoclimatic_history, name)
        exec(compile(ast.Module(body=[columns, *nodes], type_ignores=[]), '<source pipeline>', 'exec'), ns)
        cached = pd.DataFrame([self.station(Latitud='41.43', Longitud='2.10', Altitud='385.0')])
        cached.to_csv(self.path, index=False)
        raw = pd.DataFrame([{
            **self.station(Latitud='41.43', Longitud='2.10', Altitud='To be set later',
                           Municipi='To be set later', Provincia='To be set later'),
            'Data Lectura': pd.Timestamp('2026-11-07T16:00:00Z'),
            'Ultima Lectura': pd.Timestamp('2026-11-07T16:00:00Z'),
            'Data Local': 'To be set later', 'Hora Local': 'To be set later',
            'Variable': 'Precipitació', 'Unitat': 'mm', 'Total': 9.54,
            'max_temp_celsius': 20.23, 'min_temp_celsius': 10.12,
            'max_humidity_percent': 80., 'min_humidity_percent': 30.,
        }])
        feed = mock.Mock()
        feed.weather_sel_stations.side_effect = lambda pattern: raw.copy(deep=True)
        ns['MeteoclimaticClient'] = mock.Mock(return_value=feed)
        self.geocode.side_effect = AssertionError('Unexpected paid Google Maps call')
        with mock.patch.dict(os.environ, {'RAINMAPPER_PARTITIONED_WEATHER_HISTORY': 'true'}), \
                contextlib.redirect_stdout(io.StringIO()):
            for _ in range(2):
                current = ns['create_meteoclimatic'](False)
                self.assertEqual((current.iloc[0].Latitud, current.iloc[0].Longitud, current.iloc[0].Altitud),
                                 (41.43, 2.10, 385.))
                self.assertEqual(current.iloc[0].Total, 9.5)
                ns['save_incremental_meteoclimatic'](current, False, retention_reference_day=date(2026, 11, 7))
                report = archive_and_close_pending(self.data)
                self.assertEqual(report['committed'], _ == 0)  # Identical replay is a no-op.
        self.geocode.assert_not_called()
        generation = resolve_weather_generation(self.data, verify_hashes=True)
        part = next(p for p in generation.partitions if p.source == 'meteoclimatic')
        row = pq.ParquetFile(generation.object_path(part.path)).read().to_pylist()[0]
        self.assertEqual((row['lat'], row['lon'], row['altitude'], row['rain_mm']), (41.43, 2.10, 385., 9.5))


class FixedCoordinateArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WeatherHistoryWriterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.data = self.fixture.data_dir
        self.path = self.data.parent / FILENAME
        seed = self.fixture._pending([self.fixture.row('meteoclimatic', CODE, '20260101', 1, lat=41.99, lon=2.32, altitude=465)], source='meteoclimatic')
        archive_pending_batches(self.data, reserve_bytes=0)
        acknowledge_archived_pending(self.data, seed.batch_id)
        self.initial = resolve_weather_generation(self.data)

    def pending(self):
        bad = self.fixture.row('meteoclimatic', CODE, '20260102', 9.3, lat=49.99, lon=2.32, altitude=121)
        bad.update(municipality='Amiens', province='Somme', min_temp_celsius=8.1)
        return self.fixture._pending([bad], source='meteoclimatic')

    def read_station(self, generation):
        part = next(p for p in generation.partitions if p.source == 'meteoclimatic')
        return pq.read_table(generation.object_path(part.path)).to_pylist()

    def test_real_error_repaired_without_mutating_pending_or_old_observations(self):
        pending = self.pending()
        digest = sha256_file(pending.data_path)
        report = archive_pending_batches(self.data, reserve_bytes=0)
        generation = resolve_weather_generation(self.data, verify_hashes=True)
        rows = self.read_station(generation)
        self.assertTrue(report.committed)
        self.assertEqual(sha256_file(pending.data_path), digest)
        self.assertEqual(rows[0], self.read_station(self.initial)[0])
        new = rows[1]
        self.assertEqual((new['lat'], new['lon'], new['altitude']), (41.99, 2.32, 465))
        self.assertEqual((new['rain_mm'], new['min_temp_celsius']), (9.3, 8.1))
        self.assertIsNone(new['municipality'])
        cat = pq.read_table(generation.object_path(generation.catalog.path)).to_pylist()
        self.assertEqual(next(r for r in cat if r['station_code'] == CODE)['lat'], 41.99)

    def test_crash_replay_uses_committed_policy_after_file_removed(self):
        self.pending()
        self.path.write_text(CODE + ' 41.99 2.32')
        with self.assertRaises(InjectedWeatherHistoryFailure):
            archive_pending_batches(self.data, reserve_bytes=0, fail_after='current')
        generation = resolve_weather_generation(self.data)
        self.path.write_text('# exception removed after commit\n')
        with mock.patch.dict(os.environ, {'RAINMAPPER_WEATHER_REFERENCE_DAY': '2026-01-03'}):
            report = archive_and_close_pending(self.data)
        self.assertEqual(report['generation_id'], generation.generation_id)
        self.assertEqual(len(report['acknowledged_batch_ids']), 1)
        with (self.data / 'Meteoclimatic_incremental.csv').open() as handle:
            row = next(csv.DictReader(handle))
        self.assertEqual(row['Latitud'], '41,99')
        self.assertEqual(row['Altitud'], '465')
        self.assertEqual(row['Municipi'], '')
        self.assertEqual(row['Total'], '9,3')

    def test_commented_legacy_pin_does_not_disable_shared_source_guard(self):
        from rainmapper_core.weather_coordinates import read_state
        self.pending()
        self.path.write_text('# ' + CODE + ' 41.99 2.32\nA 41 1')
        self.fixture._pending([self.fixture.row('meteocat', 'A', '20260102', 2, lat=49.99, lon=2.32)])
        self.assertTrue(archive_pending_batches(self.data, reserve_bytes=0).committed)
        state = read_state(self.data)
        self.assertEqual(state['exceptions']['meteocat:A']['accepted']['lat'], 42)
        self.assertEqual(state['exceptions']['meteoclimatic:' + CODE]['accepted']['lat'], 41.99)

    def test_invalid_file_does_not_publish_or_consume_pending(self):
        pending = self.pending()
        self.path.write_text(CODE + ' nan 2.32')
        with self.assertRaisesRegex(ValueError, FILENAME):
            archive_pending_batches(self.data, reserve_bytes=0)
        self.assertTrue(pending.data_path.exists())
        self.assertEqual(resolve_weather_generation(self.data).generation_id, self.initial.generation_id)

    def test_explicit_pin_can_correct_old_catalog_outside_regional_exception(self):
        # User pins are authoritative even where the automatic region policy refuses.
        self.path.write_text(CODE + ' 49.99 2.32')
        self.fixture._pending([self.fixture.row('meteoclimatic', CODE, '20260102', 2, lat=49.99, lon=2.32)], source='meteoclimatic')
        self.assertTrue(archive_pending_batches(self.data, reserve_bytes=0).committed)
