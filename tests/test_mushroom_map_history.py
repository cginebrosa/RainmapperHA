"""Historical dates never see later weather; pages are spatially/size bounded."""
import json
import unittest
from copy import deepcopy
from unittest import mock

from rainmapper_core import mushroom_map_history as history
from rainmapper_core import mushroom_prediction_map as contract
from rainmapper_core.mushroom_map_queries import QueryBroker, QueryError
from tests import test_weather_history_dataset as fixtures


def request(**changes):
    return dict(contract=history.CONTRACT, request_id='history_test_001', start_date='2026-01-01',
                calendar_timezone='Europe/Madrid', execution='local', period='07d.geojson', offset=0,
                bounds=[1.8,41.8,2.2,42.2], **changes)


class HistoricalWeatherTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WeatherHistoryDatasetTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        stations = self.fixture.data_dir / 'stations.txt'; stations.write_text('')
        self.reader = history.HistoryReader(self.fixture.data_dir, stations)

    def execute(self, **changes):
        req=request(); req.update(changes)
        result=self.reader.execute(req)
        contract.validate_result(result, req)
        return result

    def rows(self, result):
        return [dict(zip(result['columns'], row)) for row in result['rows']]

    def test_cutoff_inclusive_previous_day_and_read_only(self):
        before={p:p.read_bytes() for p in self.fixture.data_dir.rglob('*') if p.is_file()}
        result=self.execute()
        rows={r['history_code']:r for r in self.rows(result)}
        self.assertEqual(result['cutoff_date'],'2025-12-31')
        self.assertEqual(set(rows),{'A','B'})  # W only appears on January 1.
        self.assertEqual(rows['A']['Total'],1.0)  # Jan 1's 3 mm must not leak.
        self.assertEqual(rows['B']['Total'],2.0)
        self.assertEqual(before,{p:p.read_bytes() for p in self.fixture.data_dir.rglob('*') if p.is_file()})
        later={r['history_code']:r for r in self.rows(self.execute(start_date='2026-01-02'))}
        self.assertEqual(later['A']['Total'],4.0)
        self.assertEqual(later['W']['Total'],4.0)

    def test_spatial_filter_happens_before_reading_partitions(self):
        with mock.patch.object(self.reader,'_load',wraps=self.reader._load) as read:
            result=self.execute(bounds=[10,45,11,46])
        self.assertEqual(result['total_stations'],0)
        self.assertEqual(result['execution']['rows_read'],0)
        self.assertEqual(read.call_args.args[0],[])

    def test_cached_region_is_excluded_before_materialization(self):
        result=self.execute(bounds=[1,41,3,43],exclude_bounds=[[1.8,41.8,2.2,42.2]])
        self.assertEqual(result['total_stations'],0)
        self.assertEqual(result['execution']['rows_read'],0)

    def test_daily_records_without_coordinates_use_station_catalog(self):
        original = self.reader._load
        def missing_coordinates(*args):
            frame, count, checks = original(*args)
            frame.loc[frame['history_code'] == 'A', ['Latitud', 'Longitud']] = float('nan')
            return frame, count, checks
        with mock.patch.object(self.reader, '_load', side_effect=missing_coordinates):
            result = self.execute()
        rows = {r['history_code']: r for r in self.rows(result)}
        position = next(r for r in self.reader.weather.catalog if r['station_code'] == 'A')
        self.assertEqual((rows['A']['Latitud'], rows['A']['Longitud']), (position['lat'], position['lon']))
        self.assertEqual(rows['A']['history_coordinate_source'], 'station_catalog')
        self.assertEqual(rows['B']['history_coordinate_source'], 'daily_record')
        self.assertEqual(rows['A']['Total'], 1.0)

    def test_station_details_and_periods_obey_same_date(self):
        result=self.execute(start_date='2026-01-02', station={'source':'meteocat','code':'A'}, period='01d.geojson')
        row=self.rows(result)[0]
        self.assertEqual(row['Total'],3.0)
        self.assertEqual(row['history_loaded'],1)
        self.assertEqual(row['Data_Pluja_01'],'01/01/2026')
        self.assertEqual(row['Data_Pluja_02'],'31/12/2025')
        with self.assertRaisesRegex(ValueError,'history_generation_changed'):
            self.execute(generation='old-generation')

    def test_limits_reject_before_read(self):
        for changes in ({'offset':1},{'bounds':[2,42,1,41]}, {'bounds':[float('nan'),41,2,42]},
                        {'period':'../../secret'}, {'start_date':'2100-01-01'}):
            with self.subTest(changes=changes),mock.patch.object(self.reader.weather,'_refresh',side_effect=AssertionError('read')):
                with self.assertRaises(ValueError):self.execute(**changes)

    def test_reply_identity_extent_and_size(self):
        result=self.execute(); bad=deepcopy(result);bad['bounds']=[-180,-90,180,90]
        with self.assertRaisesRegex(ValueError,'history_result_mismatch'):history.validate_result(bad,request())
        bad=deepcopy(result);bad['rows'][0][0]='x'*513
        with self.assertRaisesRegex(ValueError,'invalid_history_cell'):history.validate_result(bad,request())
        self.assertLess(len(json.dumps(result).encode()),history.MAX_BYTES)

    def test_worker_must_advertise_history_without_affecting_prediction(self):
        broker=QueryBroker();broker.worker_poll('old-worker')
        req=request();req['execution']='worker'
        with self.assertRaisesRegex(QueryError,'worker_history_unsupported'):broker.submit('alice',req)
        broker.worker_poll('new-worker',capabilities=[history.CAPABILITY])
        accepted=broker.submit('alice',req)
        self.assertIsNone(broker.worker_poll('old-worker')['query'])
        claim=broker.worker_poll('new-worker',capabilities=[history.CAPABILITY])['query']
        self.assertEqual(claim['query_id'],accepted['query_id'])
        self.assertTrue(broker.is_history('alice',accepted['query_id']))
        with self.assertRaises(QueryError):broker.is_history('bob',accepted['query_id'])

    def test_history_preserves_readiness_reason_and_recovers_without_changing_prediction(self):
        now = [1.]
        broker = QueryBroker(clock=lambda: now[0])
        req = {**request(), 'execution': 'worker'}
        with self.assertRaisesRegex(QueryError, 'executor_unavailable'):
            broker.submit('alice', req)
        broker.worker_poll('legacy-worker')  # A ready older worker must not hide this reason.
        for reason in ('map_data_updating', 'map_data_syncing', 'worker_incompatible'):
            broker.worker_poll('history-worker', busy=True, ready=False,
                capabilities=[history.CAPABILITY], unavailable_reason=reason)
            with self.subTest(reason=reason), self.assertRaisesRegex(QueryError, reason):
                broker.submit('alice', req)
            self.assertEqual(len(broker.queries), 0)
        broker.worker_poll('history-worker', busy=True, capabilities=[history.CAPABILITY])
        with self.assertRaisesRegex(QueryError, 'worker_busy'):
            broker.submit('alice', req)
        broker.worker_poll('history-worker', busy=True, ready=True, capabilities=[history.CAPABILITY])
        self.assertNotIn('history-worker', broker.worker_unavailable_reasons)
        accepted = broker.submit('alice', req)
        self.assertIsNone(broker.worker_poll('history-worker', busy=True, ready=True,
            capabilities=[history.CAPABILITY])['query'])
        claim = broker.worker_poll('history-worker', capabilities=[history.CAPABILITY])['query']
        self.assertEqual(claim['query_id'], accepted['query_id'])
        now[0] += 16
        with self.assertRaisesRegex(QueryError, 'executor_unavailable'):
            broker.submit('bob', req)
        self.assertEqual(broker.worker_unavailable_reasons, {})


if __name__=='__main__':unittest.main()
