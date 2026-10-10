import unittest
from datetime import date, timedelta
from pathlib import Path

from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_weather_workspace as workspace_module
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


class OperationalWeatherWorkspaceTests(unittest.TestCase):
    def test_raw_area_windows_preserve_means_with_missing_days_and_long_windows(self):
        from statistics import fmean
        from types import SimpleNamespace
        contexts = [SimpleNamespace(micro_area_id='a'), SimpleNamespace(micro_area_id='b')]
        days = [(date(2024,1,1)+timedelta(days=i)).isoformat() for i in range(400)]
        rain = [[None if i%7==0 else i*.123456789 for i in range(400)],
                [None if i%11==0 else i*.234567891 for i in range(400)]]
        eto = [[None if i%13==0 else i*.0123456789 for i in range(400)],
               [None if i%17==0 else i*.0234567891 for i in range(400)]]
        weather = {c.micro_area_id:{'daily_dates':days,'daily_rain_idw_mm':rain[j]}
                   for j,c in enumerate(contexts)}
        cache = workspace_module.AreaPhysicalWindows({'area':contexts}, weather,
                                                     dict(zip(('a','b'),eto)))
        def means(rows):
            return [fmean(values) if (values := [r[i] for r in rows if r[i] is not None]) else None
                    for i in range(len(rows[0]))]
        for offset in (364,365,399):
            actual = cache.get('area', date.fromisoformat(days[offset]))
            left = offset-364
            expected_eto = means([row[left:offset+1] for row in eto])
            expected_balance = means([[p-e if p is not None and e is not None else None
                                      for p,e in zip(r[left:offset+1],t[left:offset+1])]
                                     for r,t in zip(rain,eto)])
            self.assertEqual(actual, (expected_eto,expected_balance))
        self.assertIsNone(cache.get('area', date.fromisoformat(days[0])))
        weather['b'] = {**weather['b'], 'daily_dates':days[1:]}
        misaligned = workspace_module.AreaPhysicalWindows({'area':contexts},weather,dict(zip(('a','b'),eto)))
        self.assertIsNone(misaligned.get('area',date.fromisoformat(days[-1])))

    def test_station_range_views_match_filtered_records_without_copying(self):
        first = date(2026, 1, 1)
        days = [first + timedelta(days=i) for i in range(6)]
        station = self.station('A', {days[i]: float(i) for i in (5, 0, 3, 2)})
        workspace = self.workspace({('test','A'): station})
        workspace._station_axes = {('test','A'): tuple(sorted(station.records_by_day))}
        workspace._station_views = workspace_module._LastWindow()
        for left, right in ((0, 5), (1, 4), (1, 1), (3, 3)):
            view = workspace.stations_for_view(days[left], days[right])
            expected = {d: record for d,record in station.records_by_day.items()
                        if days[left] <= d <= days[right]}
            if not expected:
                self.assertEqual(view, {})
                continue
            actual = view['test','A'].records_by_day
            self.assertEqual(dict(actual), expected)
            self.assertIs(actual.records, station.records_by_day)
            for d,record in expected.items():
                self.assertIs(actual[d], record)
            self.assertEqual(actual.get(days[left] - timedelta(days=1)), None)
        self.assertEqual(len(workspace._station_views), 1)

    def test_lazy_area_windows_match_native_aggregation_with_bounded_retention(self):
        from unittest.mock import patch
        start = date(2026, 1, 1)
        dates = [start + timedelta(days=i) for i in range(weather_context.DAILY_SERIES_DAYS + 3)]
        station = self.station('A', {d: float(i % 11) for i,d in enumerate(dates)})
        context = biology_v3.MicroAreaContext(micro_area_id='micro', area_id='area',
                    lat=0., lon=0., altitude_m=500., location_source='test')
        series = mushroom_weather_idw.build_daily_weather_idw_series(
            {('test','A'):station}, target_lat=0.,target_lon=0.,target_altitude_m=500.,
            end_day=dates[-1], days=len(dates))
        targets = dates[-3:]
        windows = workspace_module.AreaWeatherWindows(
            [('area',d) for d in targets] + [('missing',targets[0])],
            {'area':[context]}, {'micro':series}, max_entries=2)
        expected = {d.isoformat():biology_v3.aggregate_area_rainfall_series({'micro':
            mushroom_weather_idw.slice_daily_weather_idw_series(series,end_day=d,
                days=weather_context.DAILY_SERIES_DAYS)}) for d in targets}
        self.assertEqual(len(windows),3)
        self.assertIsNone(windows.get(('missing',targets[0].isoformat())))
        with patch.object(biology_v3,'aggregate_area_rainfall_series',
                          wraps=biology_v3.aggregate_area_rainfall_series) as aggregate:
            for day in targets:
                self.assertEqual(windows['area',day.isoformat()],expected[day.isoformat()])
            self.assertEqual(len(windows.memo),2)
            self.assertEqual(windows['area',targets[-1].isoformat()],expected[targets[-1].isoformat()])
            self.assertEqual(aggregate.call_count,1)
            self.assertEqual(windows['area',targets[0].isoformat()],expected[targets[0].isoformat()])
            self.assertEqual(aggregate.call_count,1)

    def station(
        self,
        code: str,
        records: dict[date, float],
    ) -> weather_context.WeatherStation:
        return weather_context.WeatherStation(
            source="test",
            station_code=code,
            station_name=code,
            lat=0.0,
            lon=0.0,
            altitude_m=500.0,
            records_by_day={
                day: weather_context.DailyWeatherRecord(
                    source="test",
                    station_code=code,
                    station_name=code,
                    day=day,
                    lat=0.0,
                    lon=0.0,
                    rain_mm=rain,
                    temp_max_c=20.0,
                    temp_min_c=10.0,
                    humidity_max_pct=80.0,
                    humidity_min_pct=50.0,
                    wind_avg_kmh=None,
                    wind_gust_kmh=None,
                    wind_direction_deg=None,
                )
                for day, rain in records.items()
            },
        )

    def workspace(
        self, stations: dict[tuple[str, str], weather_context.WeatherStation]
    ) -> workspace_module.OperationalWeatherWorkspace:
        first = min(day for station in stations.values() for day in station.records_by_day)
        last = max(day for station in stations.values() for day in station.records_by_day)
        workspace = object.__new__(workspace_module.OperationalWeatherWorkspace)
        workspace.data_dir = Path("/test/weather")
        workspace.known_sites = Path("/test/sites.json")
        workspace.stations_file = Path("/test/stations.txt")
        workspace.start_day = first
        workspace.end_day = last
        workspace.days = (last - first).days + 1
        workspace.disabled = frozenset()
        workspace.stations = stations
        workspace.duplicate_dates = {
            key: mushroom_weather_idw.suppressed_rain_dates(station)
            for key, station in stations.items()
        }
        workspace._station_views = {}
        workspace._weather_base = {}
        workspace._eto_base = {}
        workspace._weather_views = {}
        workspace._soil = {}
        workspace.series_built = 0
        workspace.series_reused = 0
        workspace.view_reused = 0
        return workspace

    def test_maximum_series_view_exactly_matches_direct_range(self) -> None:
        first = date(2026, 8, 1)
        days = [first + timedelta(days=offset) for offset in range(4)]
        stations = {
            ("test", "A"): self.station(
                "A", {days[0]: 5.0, days[1]: 5.0, days[2]: 5.0, days[3]: 1.0}
            ),
            ("test", "ONLY_BEFORE"): self.station("ONLY_BEFORE", {days[0]: 2.0}),
        }
        workspace = self.workspace(stations)
        context = biology_v3.MicroAreaContext(
            micro_area_id="micro-1",
            area_id="area-1",
            lat=0.0,
            lon=0.0,
            location_source="test",
            altitude_m=500.0,
        )

        shared = workspace.weather_for_contexts(
            [context], start_day=days[1], end_day=days[3]
        )[context.micro_area_id]
        view_stations = workspace.stations_for_view(days[1], days[3])
        direct = mushroom_weather_idw.build_daily_weather_idw_series(
            view_stations,
            target_lat=context.lat,
            target_lon=context.lon,
            target_altitude_m=context.altitude_m,
            end_day=days[3],
            days=3,
            duplicate_dates_by_station={
                key: mushroom_weather_idw.suppressed_rain_dates(station)
                for key, station in view_stations.items()
            },
        )

        self.assertEqual(shared, direct)
        self.assertEqual(workspace.series_built, 1)

    def test_one_base_is_reused_across_contract_views(self) -> None:
        first = date(2026, 8, 1)
        days = [first + timedelta(days=offset) for offset in range(5)]
        stations = {
            ("test", "A"): self.station(
                "A", {day: float(index) for index, day in enumerate(days)}
            )
        }
        workspace = self.workspace(stations)
        context = biology_v3.MicroAreaContext(
            micro_area_id="micro-1",
            area_id="area-1",
            lat=0.0,
            lon=0.0,
            location_source="test",
            altitude_m=500.0,
        )

        workspace.weather_for_contexts(
            [context], start_day=days[0], end_day=days[3]
        )
        workspace.weather_for_contexts(
            [context], start_day=days[1], end_day=days[4]
        )

        self.assertEqual(workspace.series_built, 1)
        self.assertEqual(workspace.series_reused, 1)

    def test_soil_bundle_is_shared_by_area_cutoff_identity(self) -> None:
        day = date(2026, 8, 1)
        workspace = self.workspace({("test", "A"): self.station("A", {day: 0.0})})
        bundle = workspace_module.AreaSoilBundle(
            aggregated={"predictive_features": {"soil": 0.5}},
            daily_fraction_mean=[0.5],
        )
        workspace.store_soil_bundle(
            workspace_module.DEFAULT_SOIL_VARIANT_ID, "area-1", day, bundle
        )

        self.assertIs(
            workspace.soil_bundle(
                workspace_module.DEFAULT_SOIL_VARIANT_ID, "area-1", day
            ),
            bundle,
        )


if __name__ == "__main__":
    unittest.main()
