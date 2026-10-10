"""Compare the compact materializer with the unchanged scalar IDW oracle."""
from dataclasses import replace
from datetime import date, timedelta
import random
import unittest

from rainmapper_core import mushroom_weather_idw as idw
from rainmapper_core.mushroom_weather_series import WeatherSeries
from rainmapper_core.mushroom_ml_biology_v3 import MicroAreaContext
from test_mushroom_weather_idw import MushroomWeatherIDWTests


class CompactWeatherTests(unittest.TestCase):
    def test_exact_values_and_quality_for_all_channels(self):
        rng = random.Random(9243)
        start = date(2026, 1, 1)
        days = [start + timedelta(days=i) for i in range(30)]
        helper = MushroomWeatherIDWTests()
        stations = {}
        for i in range(17):
            station = helper.station(str(i), source='test', lat=i * .012, lon=.001,
                altitude_m=None if i % 3 == 0 else i * 100.,
                rain_by_day={d: rng.choice([None, 0., 12., 12., -2., 10000., 1.234]) for d in days})
            for day, row in list(station.records_by_day.items()):
                if rng.random() < .1:
                    del station.records_by_day[day]
                    continue
                station.records_by_day[day] = replace(row,
                    temp_min_c=rng.choice([None, -4.2, 'bad', float('nan'), 7., float('inf')]),
                    temp_max_c=rng.choice([None, 0., 14.328, 27.8]),
                    humidity_min_pct=rng.choice([None, -1., 10., 100.01, 77.]),
                    humidity_max_pct=rng.choice([None, 0., 90., 100.]))
            stations[('test', str(i))] = station
        duplicates = {k: idw.suppressed_rain_dates(v) for k, v in stations.items()}
        exclusions = {(' TEST ', ' 2 '), ('test', '9')}
        for limit in (1, 50000):
            index = WeatherSeries(stations, start, days[-1], duplicates, max_bytes=limit)
            for lat, altitude in ((.012, None), (.012, 493.2), (2., 0.), (0., float('nan'))):
                context = MicroAreaContext(micro_area_id='x', area_id='a', lat=lat,
                    lon=.01, altitude_m=altitude, location_source='test')
                expected = idw.build_daily_weather_idw_series(stations,
                    target_lat=lat, target_lon=.01, target_altitude_m=altitude,
                    end_day=days[-1], days=len(days), excluded_station_keys=exclusions,
                    duplicate_dates_by_station=duplicates)
                actual = index.build(context, exclusions)
                self.assertEqual(expected, actual)
                self.assertLessEqual(index.bytes, limit)

    def test_window_boundary_duplicate_and_station_absence(self):
        from test_mushroom_ml_weather_workspace import OperationalWeatherWorkspaceTests
        helper = OperationalWeatherWorkspaceTests()
        first = date(2026, 8, 1)
        days = [first + timedelta(days=i) for i in range(4)]
        stations = {('test', 'A'): helper.station('A', dict(zip(days, (5., 5., 5., 1.)))),
            ('test', 'B'): helper.station('B', {first: 20.})}
        scalar, compact = helper.workspace(stations), helper.workspace(stations)
        compact._series_index = WeatherSeries(stations, first, days[-1], compact.duplicate_dates)
        context = MicroAreaContext(micro_area_id='x', area_id='a', lat=0., lon=0.,
            altitude_m=500., location_source='test')
        for start in days[:3]:
            args = dict(start_day=start, end_day=days[-1])
            self.assertEqual(scalar.weather_for_contexts([context], **args),
                             compact.weather_for_contexts([context], **args))
            self.assertEqual(scalar.eto_for_context('x', **args), compact.eto_for_context('x', **args))

    def test_area_bounds_keep_weather_and_eto_aligned_to_the_requested_days(self):
        from test_mushroom_ml_weather_workspace import OperationalWeatherWorkspaceTests
        helper = OperationalWeatherWorkspaceTests()
        first = date(2026, 1, 1)
        days = [first + timedelta(days=i) for i in range(40)]
        stations = {('test','A'): helper.station('A', {d:float(i % 4) for i,d in enumerate(days)})}
        scalar, compact = helper.workspace(stations), helper.workspace(stations)
        compact._series_index = WeatherSeries(stations, first, days[-1], compact.duplicate_dates)
        compact.area_ranges = {'a': (days[10], days[30])}
        context = MicroAreaContext(micro_area_id='x', area_id='a', lat=0., lon=0.,
            altitude_m=500., location_source='test')
        for start, end in ((10,30), (14,27), (20,30)):
            args = dict(start_day=days[start], end_day=days[end])
            self.assertEqual(scalar.weather_for_contexts([context], **args),
                             compact.weather_for_contexts([context], **args))
            self.assertEqual(scalar.eto_for_context('x', **args), compact.eto_for_context('x', **args))
        self.assertEqual(len(compact._weather_base['x']['daily_dates']), 21)
