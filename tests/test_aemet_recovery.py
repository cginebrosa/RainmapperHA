import ast
import io
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pandas as pd

from rainmapper_core import aemet_recovery as recovery, create_aemet as aemet
from rainmapper_core import weather_official_backfill as official
from rainmapper_core.weather_history_archive import archive_and_close_pending
from rainmapper_core.weather_history_dataset import read_weather_history

UTC = timezone.utc
NOW = datetime(2026, 10, 29, 5, tzinfo=UTC)


def observation(instant, rain=0.0):
    return {'idema': '1583X', 'fint': instant.strftime('%Y-%m-%dT%H:%M:%S+0000'),
            'prec': rain, 'ubi': 'O Barco', 'lat': 42.42, 'lon': -6.98,
            'alt': 300, 'ta': 10, 'hr': 70}


def published(rain='4,2', day='2026-10-25', **extra):
    return {'indicativo': '1583X', 'fecha': day, 'prec': rain,
            'nombre': 'O Barco', 'provincia': 'Ourense', 'tmax': '22,1', **extra}


class AemetRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.hourly = aemet.normalize_observations([
            observation(t) for t in pd.date_range('2026-10-21T22:00Z', NOW, freq='h')])
        self.catalog = aemet.build_station_catalog(self.hourly)
        self.lookup = self.catalog.set_index('Codi Estació', drop=False).to_dict('index')
        self.daily = aemet.build_daily_incremental(self.hourly, self.catalog)

    def refresh(self, path, rows, **kwargs):
        query = mock.Mock(return_value=rows)
        hourly, state, report = recovery.recover(path, self.hourly, self.catalog,
                                                api_key='test', now=NOW, fetcher=query, **kwargs)
        pd.testing.assert_frame_equal(hourly, self.hourly)
        return state, report, query

    def test_refreshes_entire_30_day_window_even_with_complete_local_hours(self):
        with tempfile.TemporaryDirectory() as tmp:
            state, report, query = self.refresh(tmp, [published(hrmax='95')])
            self.assertEqual([x.args for x in query.call_args_list], [
                (date(2026, 9, 29), date(2026, 10, 13)),
                (date(2026, 10, 14), date(2026, 10, 28))])
            result = recovery.apply_verified(self.daily, state, self.lookup).set_index('Data Local')
            self.assertEqual(result.at['20261025', 'Total'], 4.2)
            self.assertEqual(result.at['20261025', 'max_temp_celsius'], 22.1)
            self.assertEqual(result.at['20261025', 'max_humidity_percent'], 95)
            self.assertEqual(result.at['20261028', 'Total'], 0)
            self.assertEqual(report['status'], 'complete')
            self.assertIn('2026-10-28', report['awaiting_publication_dates'])

    def test_rechecks_next_run_accepts_downward_correction_and_keeps_cache_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.refresh(tmp, [published('8,5')])
            state, _, query = self.refresh(tmp, [published('1,2')])
            self.assertEqual(query.call_count, 2)
            state, report, _ = self.refresh(tmp, [published(None, tmax='20')])
            self.assertEqual(state['days']['20261025']['AEMET:1583X']['Total'], 1.2)
            failed = mock.Mock(side_effect=RuntimeError('API unavailable'))
            _, kept, report = recovery.recover(tmp, self.hourly, self.catalog,
                                              api_key='test', now=NOW + timedelta(minutes=1), fetcher=failed)
            self.assertEqual(failed.call_count, 1)
            self.assertEqual(report['status'], 'pending')
            result = recovery.apply_verified(self.daily, kept, self.lookup).set_index('Data Local')
            self.assertEqual(result.at['20261025', 'Total'], 1.2)
            self.assertEqual(result.at['20261025', 'max_temp_celsius'], 20)

    def test_window_retention_does_not_remove_other_existing_daily_rows(self):
        older = self.daily.iloc[[0]].copy()
        older['Data Local'] = '20200101'
        older['Total'] = 99
        with tempfile.TemporaryDirectory() as tmp:
            state, _, _ = self.refresh(tmp, [published('4,2', '2026-09-29'), published('8,2', '2026-10-25')])
            _, state, _ = recovery.recover(tmp, self.hourly, self.catalog, api_key='test',
                                          now=NOW + timedelta(days=1), fetcher=mock.Mock(return_value=[]))
            self.assertNotIn('20260929', state['days'])
            result = recovery.apply_verified(pd.concat([older, self.daily]), state, self.lookup)
            self.assertEqual(result.loc[result['Data Local'] == '20200101', 'Total'].item(), 99)
            self.assertEqual(result.loc[result['Data Local'] == '20261025', 'Total'].item(), 8.2)

    def test_unpublished_response_is_not_a_failure_or_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            state, report, _ = self.refresh(tmp, [])
            self.assertEqual(report['status'], 'complete')
            self.assertEqual(report['official_rows'], 0)
            pd.testing.assert_frame_equal(recovery.apply_verified(self.daily, state, self.lookup), self.daily)
        rows = official.fetch_aemet_climatology(date(2026, 10, 28), date(2026, 10, 28),
                api_key='test', fetcher=mock.Mock(return_value={'estado':404}), allow_empty=True)
        self.assertEqual(rows, [])

    def test_missing_accumulated_or_negative_rain_does_not_replace_provisional(self):
        provisional = self.daily.copy()
        provisional.loc[provisional['Data Local'] == '20261025', 'Total'] = 3.0
        for rain in (None, '', 'Acum', '-1'):
            with self.subTest(rain=rain), tempfile.TemporaryDirectory() as tmp:
                state, _, _ = self.refresh(tmp, [published(rain)])
                result = recovery.apply_verified(provisional, state, self.lookup)
                self.assertEqual(result.loc[result['Data Local'] == '20261025', 'Total'].item(), 3.0)

    def test_unknown_station_keeps_official_daily_with_available_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            state, _, _ = self.refresh(tmp, [published(indicativo='NEW', nombre='New station', altitud='200')])
            result = recovery.apply_verified(self.daily, state, self.lookup)
            row = result.loc[result['Codi Estació'] == 'AEMET:NEW'].iloc[0]
            self.assertEqual(row['Total'], 4.2)
            self.assertEqual(row['Estació'], 'New station')
            self.assertEqual(float(row['Altitud']), 200)
            self.assertTrue(pd.isna(row['Latitud']))
            from rainmapper_core.weather_history_capture import capture_fresh_weather_rows
            with mock.patch.dict('os.environ', {'RAINMAPPER_PARTITIONED_WEATHER_HISTORY':'true'}):
                self.assertIsNotNone(capture_fresh_weather_rows(Path(tmp), 'aemet', result))

    def test_api_routes_only_and_two_http_requests_per_block(self):
        calls = []
        def fetch(url, **kwargs):
            calls.append((url, kwargs))
            aemet._aemet_phase(kwargs['phase_callback'], 'download_complete', {'bytes':10})
            if '/valores/climatologicos/' in url:
                return {'estado':200, 'datos':'https://opendata.aemet.es/opendata/sh/test'}
            return [published()]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(aemet, 'fetch_json', side_effect=fetch):
            _, _, report = recovery.recover(tmp, self.hourly, self.catalog, api_key='test', now=NOW)
        self.assertEqual(len(calls), 4)
        self.assertEqual(report['requests'], 4)
        self.assertEqual(report['download_bytes'], 40)
        self.assertTrue(all(url.startswith('https://opendata.aemet.es/') for url, _ in calls))
        self.assertEqual(calls[0][1]['api_key'], 'test')
        self.assertNotIn('api_key', calls[1][1])
        self.assertTrue(all(kwargs['max_response_bytes'] == recovery.MAX_RESPONSE_BYTES for _, kwargs in calls))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(aemet, 'fetch_json', return_value={
                'estado':200, 'datos':'https://www.aemet.es/es/api-eltiempo/anything'}):
            _, _, report = recovery.recover(tmp, self.hourly, self.catalog, api_key='test', now=NOW)
            self.assertEqual(report['status'], 'pending')
            self.assertEqual(report['requests'], 1)

    def test_payload_limit_rejects_before_json_parsing(self):
        with mock.patch.object(aemet.urllib.request, 'urlopen', return_value=io.BytesIO(b'0123456789')):
            with mock.patch.object(aemet.json, 'loads') as loads:
                with self.assertRaisesRegex(ValueError, 'byte limit'):
                    aemet.fetch_json('https://opendata.aemet.es/test', max_response_bytes=5)
                loads.assert_not_called()

    def test_invalid_cache_stops_before_replacing_existing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            aemet.write_csv_atomic(self.hourly, p/'Aemet_hourly_incremental.csv')
            before = (p/'Aemet_hourly_incremental.csv').read_bytes()
            (p/recovery.STATE_FILE).write_text('{invalid')
            with mock.patch.object(aemet, 'fetch_observations', return_value=[observation(NOW)]):
                with self.assertRaises(ValueError):
                    aemet.run_update(p, 'test', enrich_stations=False, recovery_now=NOW)
            self.assertEqual((p/'Aemet_hourly_incremental.csv').read_bytes(), before)

    def test_midnight_precipitation_belongs_to_preceding_day(self):
        rows = aemet.normalize_observations([
            observation(datetime(2026,10,28,22,tzinfo=UTC),1),
            observation(datetime(2026,10,28,23,tzinfo=UTC),4.2),
            observation(datetime(2026,10,29,0,tzinfo=UTC),2)])
        rows.loc[rows['reading_local']=='2026-10-29 00:00:00','temp_celsius'] = 99
        daily = aemet.build_daily_incremental(rows).set_index('Data Local')
        self.assertAlmostEqual(daily.at['20261028','Total'],5.2)
        self.assertEqual(daily.at['20261029','Total'],2)
        self.assertEqual(daily.at['20261028','max_temp_celsius'],10)
        self.assertEqual(daily.at['20261029','max_temp_celsius'],99)

    def test_partitioned_archive_and_csv_keep_official_values_after_api_outage(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict('os.environ', {
                'RAINMAPPER_PARTITIONED_WEATHER_HISTORY':'true',
                'RAINMAPPER_WEATHER_REFERENCE_DAY':'2026-10-29'}), mock.patch.object(
                aemet, 'fetch_observations', return_value=[observation(NOW)]):
            p = Path(tmp)
            from tests.test_weather_history_writer import WeatherHistoryWriterTests
            seed = WeatherHistoryWriterTests()
            seed.data_dir=p; seed.root=p/'weather-history'; seed.root.mkdir()
            seed._write_initial_generation()
            aemet.write_csv_atomic(self.hourly, p/'Aemet_hourly_incremental.csv')
            with mock.patch.object(official, 'fetch_aemet_climatology', return_value=[published()]):
                aemet.run_update(p,'test',enrich_stations=False,retention_reference_day=NOW.date(),recovery_now=NOW)
            archive_and_close_pending(p)
            stored = read_weather_history(p,sources={'aemet'},start_date='20261025',end_date='20261025')
            self.assertEqual(stored['rain_mm'].item(),4.2)
            with mock.patch.object(official, 'fetch_aemet_climatology', side_effect=RuntimeError('offline')):
                aemet.run_update(p,'test',enrich_stations=False,retention_reference_day=NOW.date(),recovery_now=NOW)
            archive_and_close_pending(p)
            after = read_weather_history(p,sources={'aemet'},start_date='20261025',end_date='20261025')
            pd.testing.assert_frame_equal(stored,after)
            live = pd.read_csv(p/'Aemet_incremental.csv',decimal=',',dtype={'Data Local':str})
            self.assertEqual(live.loc[live['Data Local']=='20261025','Total'].item(),4.2)

    def test_runner_reports_secondary_api_failure_as_usable_partial(self):
        source = Path(aemet.__file__).with_name('rainmapper.py').read_text()
        functions = [node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef)
                     and node.name in {'collect_source_result','source_exit_code'}]
        recorded=mock.Mock()
        namespace={'source_extra_status':lambda _: {'recovery_status':'pending','recovery_message':'API unavailable'},
                   'record_source_status':recorded,'count_incremental_stations':lambda _:1,
                   'source_runtime_metric':lambda _:{},'SOURCE_STATUSES':{'AEMET':{'status':'PARTIAL','enabled':True}}}
        exec(compile(ast.Module(body=functions,type_ignores=[]),'rainmapper.py','exec'),namespace)
        future=mock.Mock();future.result.return_value=(pd.DataFrame(),pd.DataFrame({'Total':[4.2]}))
        namespace['collect_source_result']('AEMET',future,'Aemet_incremental',True)
        self.assertEqual(recorded.call_args.args[1:3],('PARTIAL',2))
        self.assertEqual(namespace['source_exit_code'](),2)


if __name__ == '__main__':
    unittest.main()
