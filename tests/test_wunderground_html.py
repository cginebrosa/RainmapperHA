"""WU page variants and ingestion failures, using captured header fragments only."""
import ast
import csv
import io
import math
import os
import tempfile
import threading
import time
import unittest
import warnings
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import lxml.html as lh
import requests
import pandas as pd
from bs4 import BeautifulSoup

from rainmapper_core.sources.wunderground.Parser import Parser
from rainmapper_core.sources.wunderground.UnitConverter import ConvertToSystem
from rainmapper_core.sources.wunderground.Utils import Utils
from rainmapper_core.sources.wunderground.daily_api import WundergroundDailyApiError
from rainmapper_core.sources.wunderground.parseStationData import (
    WundergroundPageError, parseStationData, validate_history_dates,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/wunderground'
URL = 'https://www.wunderground.com/dashboard/pws/ILAIGL7'
MODULE = 'rainmapper_core.sources.wunderground.parseStationData'


def response(content, status=200):
    return SimpleNamespace(content=content.encode(), status_code=status)


def header(name='web-components-header'):
    return (FIXTURES / (name + '.html')).read_text()


class WundergroundHtmlTests(unittest.TestCase):
    def parser(self, content):
        p = parseStationData(URL)
        p.soup = BeautifulSoup(content, 'html.parser')
        return p

    def test_real_legacy_header_feet(self):
        self.assertEqual(self.parser(header('legacy-header')).get_station_header(),
                         ('ILAIGL7', 'Iglesuela', 'La Iglesuela del Cid', '376', 40.48, -0.32))

    def test_real_new_header_meters(self):
        self.assertEqual(self.parser(header()).get_station_header(),
                         ('ILAIGL7', 'Iglesuela', 'La Iglesuela del Cid', '375', 40.481, -0.32))

    def test_units_hemispheres_and_class_order(self):
        content = header('legacy-header').replace('columns small-12 station-header', 'station-header small-12 columns')
        content = content.replace('°N', '° S').replace('°W', '° E')
        self.assertEqual(self.parser(content).get_station_header()[4:], (-40.48, 0.32))
        with self.assertRaises(WundergroundPageError):
            self.parser(content.replace(' ft', ' furlongs')).get_station_header()

    def test_wrong_station_and_impossible_coordinates_rejected(self):
        for content in (header().replace('ILAIGL7', 'OTHER'), header().replace('40.481', '140.481')):
            with self.subTest(content=content[:40]), self.assertRaises(WundergroundPageError):
                self.parser(content).get_station_header()

    @mock.patch(MODULE + '.time.sleep')
    @mock.patch(MODULE + '.requests.get')
    def test_incomplete_200_retried_and_valid_header_reused(self, get, sleep):
        get.side_effect = [response('<html>Loading</html>'), response(header())]
        p = parseStationData(URL, max_attempts=3)
        p.fetch_data(require_metadata=True)
        self.assertEqual(p.get_station_header()[0], 'ILAIGL7')
        p.fetch_data(require_metadata=True)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(sleep.call_count, 1)
        self.assertNotEqual(get.call_args_list[0].kwargs['headers']['Accept-Encoding'],
                            get.call_args_list[1].kwargs['headers']['Accept-Encoding'])
        self.assertEqual(get.call_args.kwargs['timeout'], (5, 10))

    @mock.patch(MODULE + '.time.sleep')
    @mock.patch(MODULE + '.requests.get', return_value=response('<html>Loading</html>'))
    def test_exhaustion_is_bounded_and_does_not_retain_bad_page(self, get, sleep):
        p = parseStationData(URL, max_attempts=3)
        with self.assertRaisesRegex(WundergroundPageError, '3 intentos.*cabecera'):
            p.fetch_data(require_metadata=True)
        self.assertEqual(get.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertIsNone(p.response)
        self.assertIsNone(p.soup)

    @mock.patch(MODULE + '.time.sleep')
    @mock.patch(MODULE + '.requests.get')
    def test_timeout_and_http_failure_recover(self, get, sleep):
        get.side_effect = [requests.Timeout('timeout'), response('', 503), response(header())]
        p = parseStationData(URL)
        p.fetch_data(require_metadata=True)
        self.assertEqual(p.get_station_header()[3], '375')

    @mock.patch(MODULE + '.requests.get')
    def test_legacy_history_cookie_is_used_only_for_history_request(self, get):
        get.side_effect = [response(header()), response(header('legacy-history'))]
        p = parseStationData(URL)
        p.fetch_data(require_metadata=True)

        def validate(r):
            tables = lh.fromstring(r.content).xpath('//lib-history-table//table/tbody')
            if not tables:
                raise WundergroundPageError('missing history')
            return Parser.parse_html_table('2026-09-24', tables, 'ILAIGL7', 'Iglesuela', 'Town', '375', 40.481, -0.32)

        p.fetch_data(validator=validate, legacy_history=True)
        self.assertEqual(len(p.validated_data), 1)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[0].kwargs['cookies'], {})
        self.assertEqual(get.call_args_list[1].kwargs['cookies'], {'wu_prefer_legacy': 'true'})

    def test_dates_filter_partial_month_and_reject_unrelated_payload(self):
        rows = [{'Date': '2026-09-01'}, {'Date': '2026-09-24'}]
        self.assertEqual(validate_history_dates(rows, date(2026, 9, 20), date(2026, 9, 24)), rows[1:])
        with self.assertRaisesRegex(WundergroundPageError, 'intervalo 2028'):
            validate_history_dates(rows, date(2028, 9, 1), date(2028, 9, 30))
        for rows in ([], [{'Date': 'invalid'}], [{}]):
            with self.assertRaises(WundergroundPageError):
                validate_history_dates(rows, date(2026, 9, 1), date(2026, 9, 30))

    def run_station(self, folder, *, cached=None, api_rows=None, html_response=None, start=date(2026, 9, 1), api_key_error=None):
        # The runner executes on import. Compile only its real station function to
        # exercise file writes without launching providers, archives or training.
        module = ast.parse((ROOT / 'rainmapper_core/rainmapper.py').read_text())
        fn = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'scrap_wunderground_station')
        api = mock.Mock(return_value=api_rows)
        if api_rows is None:
            api.side_effect = WundergroundDailyApiError('HTTP 204')
        namespace = dict(threading=threading, datetime=datetime, time_module=time, requests=requests,
                         START_DATE=start, END_DATE=start.replace(day=24), UNIT_SYSTEM='metric',
                         FIND_FIRST_DATE=False, MONTHLY=True, MERGE_DATA=True,
                         _wunderground_monthly_api=True, _wunderground_weekly_api=False,
                         _wunderground_full_log=False, _max_attempts=3, _script_path=folder,
                         wunderground_header=True, os=os, csv=csv, Utils=Utils, lh=lh, Parser=Parser,
                         ConvertToSystem=ConvertToSystem, parseStationData=parseStationData,
                         WundergroundPageError=WundergroundPageError, WundergroundDailyApiError=WundergroundDailyApiError,
                         validate_history_dates=validate_history_dates, wunderground_log=lambda *a: None,
                         wunderground_api_range=lambda: (start, start.replace(day=24)),
                         cached_wunderground_station_metadata=lambda url: cached,
                         wunderground_weekly_window_enabled=lambda: False, fetch_wunderground_api_rows=api)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<station-under-test>', 'exec'), namespace)
        with mock.patch(MODULE + '.requests.get', return_value=response(html_response or header())) as get, \
             mock.patch(MODULE + '.time.sleep'), redirect_stdout(io.StringIO()):
            result = namespace['scrap_wunderground_station'](URL, 'test-run', api_key='test-key', api_key_error=api_key_error)
        with open(namespace['wunderground_file_name']) as f:
            written = list(csv.DictReader(f))
        return result, written, get.call_count, api.call_count

    def test_key_discovery_failure_uses_html_without_repeating_api_attempts(self):
        content = header('legacy-header') + header('legacy-history')
        with tempfile.TemporaryDirectory() as folder:
            result, written, _, api_calls = self.run_station(folder, html_response=content, api_key_error='discovery failed')
        self.assertTrue(result['ok'])
        self.assertEqual(len(written), 1)
        self.assertEqual(api_calls, 0)
        self.assertEqual(result['api_errors'], 1)

    def test_station_uses_new_header_then_api_without_more_html_requests(self):
        with tempfile.TemporaryDirectory() as folder:
            result, written, calls, api_calls = self.run_station(folder, api_rows=[{'Date': '2026-09-24'}])
        self.assertTrue(result['ok'])
        self.assertEqual(len(written), 1)
        self.assertEqual((calls, api_calls), (1, 1))

    def test_cached_metadata_bypasses_header_download(self):
        cached = dict(station_ID='ILAIGL7', station_name='Iglesuela', location_name='Town',
                      elevation='375', latitude='40.481', longitude='-0.32')
        with tempfile.TemporaryDirectory() as folder:
            result, written, calls, _ = self.run_station(folder, cached=cached, api_rows=[{'Date': '2026-09-24'}])
        self.assertTrue(result['ok'])
        self.assertEqual(calls, 0)

    def test_api_wrong_year_never_written(self):
        with tempfile.TemporaryDirectory() as folder:
            result, written, _, _ = self.run_station(folder, api_rows=[{'Date': '2026-09-24'}], start=date(2028, 9, 1))
        self.assertFalse(result['ok'])
        self.assertEqual(written, [])
        self.assertIn('2028', result['errors'][0])

    def test_missing_history_table_retried_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            result, written, calls, _ = self.run_station(folder)
        self.assertFalse(result['ok'])
        self.assertEqual(written, [])
        self.assertEqual(calls, 4)  # One metadata request, then at most three history attempts.
        self.assertIn('tabla histórica', result['errors'][0])

    def test_html_fallback_writes_matching_dates_only(self):
        content = header('legacy-header') + header('legacy-history')
        with tempfile.TemporaryDirectory() as folder:
            result, written, calls, _ = self.run_station(folder, html_response=content)
        self.assertTrue(result['ok'])
        self.assertEqual(len(written), 1)
        self.assertTrue(written[0]['Data'].startswith('2026-09-'))
        self.assertEqual(calls, 1)

    def test_html_fallback_wrong_year_is_retried_then_rejected(self):
        content = header('legacy-header') + header('legacy-history')
        with tempfile.TemporaryDirectory() as folder:
            result, written, calls, _ = self.run_station(
                folder, html_response=content, start=date(2028, 9, 1),
            )
        self.assertFalse(result['ok'])
        self.assertEqual(written, [])
        self.assertEqual(calls, 4)
        self.assertIn('2028', result['errors'][0])

    def test_all_stations_failed_raises_before_normalizing_or_publishing(self):
        module = ast.parse((ROOT / 'rainmapper_core/rainmapper.py').read_text())
        fn = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'create_wunderground')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'scrape.csv'
            path.write_text('Codi Estació,Data\n')
            normalize = mock.Mock()
            namespace = dict(datetime=datetime, _max_threads=1, URLS=[URL],
                             Path=Path, _DATA_PATH=folder,
                             read_coordinate_state=lambda _: {"exceptions": {}},
                             station_id_from_url=lambda url: url.rsplit('/', 1)[-1],
                             _wunderground_monthly_api=True, _wunderground_weekly_api=False,
                             MONTHLY=True, UNIT_SYSTEM='metric', _max_attempts=3,
                             daily_api_key=mock.Mock(return_value='test-key'),
                             WundergroundDailyApiError=WundergroundDailyApiError,
                             backfill_station_ids_for=lambda _: set(), math=math,
                             wunderground_log=lambda *a: None, start_timing=lambda *a: 0,
                             record_timing=lambda *a: None, ThreadPoolExecutor=ThreadPoolExecutor,
                             as_completed=as_completed, scrap_wunderground_station=mock.Mock(return_value={'ok': False}),
                             print_wunderground_summary=mock.Mock(), pd=pd, os=os,
                             print_wunderground_progress=mock.Mock(),
                             wunderground_file_name=str(path), WundergroundPageError=WundergroundPageError,
                             build_wunderground_dataframe=normalize)
            exec(compile(ast.Module(body=[fn], type_ignores=[]), '<create-under-test>', 'exec'), namespace)
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(WundergroundPageError, 'ninguna estación'):
                namespace['create_wunderground']()
            normalize.assert_not_called()
            namespace['daily_api_key'].assert_called_once_with([URL], max_attempts=3)

            # One key is shared by all worker threads, and resolved anew on the
            # next invocation even if the Python process itself is reused.
            namespace['URLS'] = [URL, URL.replace('ILAIGL7', 'ITEST2'), URL.replace('ILAIGL7', 'ITEST3')]
            namespace['_max_threads'] = 3
            namespace['read_coordinate_state'] = lambda _: {'exceptions': {'wunderground:ITEST2': {'source': 'wunderground', 'station_code': 'ITEST2'}}}
            namespace['daily_api_key'].side_effect = ['next-run-key', WundergroundDailyApiError('missing config')]
            for expected_key, expected_error in [('next-run-key', None), (None, 'missing config')]:
                path.write_text('Codi Estació,Data\n')
                namespace['scrap_wunderground_station'].reset_mock()
                with redirect_stdout(io.StringIO()), self.assertRaises(WundergroundPageError):
                    namespace['create_wunderground']()
                calls = namespace['scrap_wunderground_station'].call_args_list
                self.assertEqual(len(calls), 3)
                for call in calls:
                    self.assertEqual(call.kwargs, {'api_key': expected_key, 'api_key_error': expected_error,
                        'refresh_coordinates': call.args[0].endswith('ITEST2')})
            self.assertEqual(namespace['daily_api_key'].call_count, 3)

    def test_coordinate_protection_with_fresh_cached_and_mixed_metadata_has_no_future_warning(self):
        from rainmapper_core import weather_coordinates as coords
        from rainmapper_core.atomic_io import write_csv_atomic
        from rainmapper_core.wind import WIND_COLUMNS, compass_to_degrees, optional_round
        from rainmapper_core.weather_history_capture import capture_fresh_weather_rows
        import pyarrow.parquet as pq

        tree = ast.parse((ROOT / 'rainmapper_core/rainmapper.py').read_text())
        names = {'create_wunderground', 'build_wunderground_dataframe'}
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        for fresh_codes in ({'ITEST1', 'ITEST2'}, set(), {'ITEST1'}):
            with self.subTest(fresh_codes=fresh_codes), tempfile.TemporaryDirectory() as folder:
                data = Path(folder)
                raw = pd.DataFrame([{
                    'Codi Estació': code, 'Estació': code, 'Data': '2026-11-07', 'Hora': '10:00:00',
                    'Latitud': lat, 'Longitud': '2.0', 'Altitud': '100.0',
                    'Municipi': 'Town', 'Provincia': 'Province', 'Comarca': '',
                    'Rain_mm': rain, 'TempHigh_C': 17., 'TempLow_C': 3.,
                    'HumHigh_%': 90., 'HumLow_%': 40.,
                } for code, lat, rain in [('ITEST1', '49.0', 1.25), ('ITEST2', '42.0', 0.)]])
                with coords.transaction(data) as state:
                    state['accepted_moves'] = {f'wunderground:{c}': {'lat': 42., 'lon': 2.}
                                               for c in ('ITEST1', 'ITEST2')}
                # The second station is already in exception; cached coordinates
                # must not heal it, whereas fresh provider coordinates must.
                coords.protect_frame(data, 'wunderground', pd.DataFrame([{
                    'Codi Estació': 'ITEST2', 'Latitud': 49., 'Longitud': 2.,
                }]), fresh=True)
                path = data / 'scrape.csv'
                raw.to_csv(path, index=False)
                urls = ['https://www.wunderground.com/dashboard/pws/' + c for c in ('ITEST1', 'ITEST2')]
                ns = dict(datetime=datetime, _max_threads=1, URLS=urls, Path=Path, _DATA_PATH=folder+'/',
                          read_coordinate_state=coords.read_state, protect_frame=coords.protect_frame,
                          station_id_from_url=lambda u: u.rsplit('/', 1)[-1],
                          _wunderground_monthly_api=False, _wunderground_weekly_api=False,
                          backfill_station_ids_for=lambda _: set(), math=math,
                          wunderground_log=lambda *a: None, start_timing=lambda *a: 0,
                          record_timing=lambda *a: None, ThreadPoolExecutor=ThreadPoolExecutor,
                          as_completed=as_completed, print_wunderground_summary=lambda *a: None,
                          print_wunderground_progress=lambda *a: None, pd=pd, os=os,
                          wunderground_file_name=str(path), WundergroundPageError=WundergroundPageError,
                          WIND_COLUMNS=WIND_COLUMNS, optional_round=optional_round,
                          compass_to_degrees=compass_to_degrees, write_csv_atomic=write_csv_atomic,
                          refresh_estacions_wunderground=lambda df: df[['Codi Estació']].drop_duplicates(),
                          scrap_wunderground_station=lambda url, *a, **kw: {
                              'station_id': url.rsplit('/', 1)[-1],
                              'metadata_fresh': url.rsplit('/', 1)[-1] in fresh_codes})
                exec(compile(ast.Module(body=nodes, type_ignores=[]), '<wu-pipeline>', 'exec'), ns)
                with warnings.catch_warnings(), redirect_stdout(io.StringIO()):
                    warnings.simplefilter('error', FutureWarning)
                    actual = ns['create_wunderground']()
                self.assertEqual(list(actual['Codi Estació']), ['ITEST1', 'ITEST2'])
                self.assertEqual(list(actual['Total']), [1.25, 0.])
                self.assertEqual(list(actual['Latitud'].astype(float)), [42., 42.])
                self.assertEqual(list(actual['max_temp_celsius']), ['17.0', '17.0'])
                exceptions = coords.read_state(data)['exceptions']
                self.assertEqual('wunderground:ITEST1' in exceptions, 'ITEST1' in fresh_codes)
                self.assertEqual('wunderground:ITEST2' in exceptions, 'ITEST2' not in fresh_codes)
                with mock.patch.dict(os.environ, {'RAINMAPPER_PARTITIONED_WEATHER_HISTORY': 'true'}):
                    pending = capture_fresh_weather_rows(data, 'wunderground', actual)
                saved = pq.ParquetFile(pending.data_path).read().to_pylist()
                self.assertEqual([r['rain_mm'] for r in saved], [1.25, 0.])
                self.assertEqual([r['lat'] for r in saved], [42., 42.])
                self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
