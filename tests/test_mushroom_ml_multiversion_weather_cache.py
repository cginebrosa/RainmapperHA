from contextlib import ExitStack
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from unittest import TestCase, mock

import pandas as pd

from rainmapper_core import mushroom_ml_area_weather_runtime as area_weather
from rainmapper_core import mushroom_ml_biology_v3 as biology
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_version_registry as registry_module
from rainmapper_core import mushroom_observation_context as weather


class EffectiveWeatherCutoffCacheTests(TestCase):
    def arguments(self, **changes):
        return {
            'known_sites_path': Path('/unused/sites.json'),
            'weather_data_dir': Path('/unused/weather'),
            'area_id': 'area-a',
            'target_date': date(2026, 10, 10),
            'horizons': (1,),
            'lookback_days': 90,
            'include_physical_state': True,
            'excluded_station_keys': frozenset(),
            **changes,
        }

    def fixture(self):
        cutoff = date(2026, 10, 9)
        axis = [cutoff - timedelta(days=374 - i) for i in range(375)]
        stations = {}
        for code, lon in (('A', 0.0), ('B', 0.01)):
            records = {
                day: weather.DailyWeatherRecord(
                    source='test', station_code=code, station_name=code,
                    day=day, lat=0.0, lon=lon, rain_mm=float(i % 11),
                    temp_max_c=20.0, temp_min_c=10.0,
                    humidity_max_pct=80.0, humidity_min_pct=50.0,
                    wind_avg_kmh=None, wind_gust_kmh=None, wind_direction_deg=None,
                ) for i, day in enumerate(axis) if i % 13 != 0
            }
            stations['test', code] = weather.WeatherStation(
                source='test', station_code=code, station_name=code,
                lat=0.0, lon=lon, altitude_m=500.0, records_by_day=records,
            )
        micros = [biology.MicroAreaContext(
            micro_area_id=f'micro-{i}', area_id='area-a', lat=0.0, lon=i * 0.01,
            altitude_m=500.0, location_source='test',
        ) for i in range(2)]
        context = biology.AreaPredictionContext(
            area_id='area-a', lat=0.0, lon=0.005,
            altitude_m=500.0, location_source='test',
        )
        catalog_rows = pd.DataFrame([
            {'source': 'test', 'station_code': code, 'lat': 0.0, 'lon': station.lon}
            for (_source, code), station in stations.items()
        ])

        def load(_path, *, station_filter, start_date, end_date):
            return {key: replace(station, records_by_day={
                day: value for day, value in station.records_by_day.items()
                if start_date <= day <= end_date
            }) for key, station in stations.items() if key in station_filter}

        stack = ExitStack()
        stack.enter_context(mock.patch.object(area_weather, 'area_contexts',
            return_value=({'area-a': context}, {'area-a': micros})))
        stack.enter_context(mock.patch.object(weather, 'load_stations_catalog', return_value=catalog_rows))
        stack.enter_context(mock.patch.object(weather, 'load_daily_weather_parquet', side_effect=load))
        return stack

    def test_seven_lag_days_equal_direct_weather_and_features_without_copying_series(self):
        cache = {}
        issue = date(2026, 10, 10)
        ref = catalog.ModelRef(
            batch_id='batch', generation_id='generation', version_id=raw.WINDOWED_VERSION_ID,
            temporal_contract_id=raw.LAG_CONTRACT_ID,
            profile_id='raw_window_30d_plus_physical_state',
            estimator_id='elastic_net_logistic_raw365_v1',
            species_id='boletus_edulis', horizon_days=1,
        )
        with self.fixture():
            baseline = [comparison.prepare_area_weather(**self.arguments(
                target_date=issue + timedelta(days=i), horizons=(i + 1,), lookback_days=365,
                excluded_station_keys=frozenset({('TEST', 'b')}),
            )) for i in range(7)]
            with mock.patch.object(comparison, 'prepare_area_weather',
                                   wraps=comparison.prepare_area_weather) as prepare:
                actual = [comparison._cached_area_weather(**self.arguments(
                    target_date=issue + timedelta(days=i), horizons=(i + 1,), lookback_days=365,
                    excluded_station_keys=frozenset({('test', 'B')}),
                ), prepared_weather_cache=cache) for i in range(7)]
            self.assertEqual(prepare.call_count, 1)
            self.assertEqual([hit for _value, hit in actual], [False] + [True] * 6)
            self.assertEqual(len(cache), 2)  # One series entry and one runtime preparation context.
            for i, ((value, _hit), expected) in enumerate(zip(actual, baseline, strict=True)):
                with self.subTest(day=i + 1):
                    self.assertEqual(value, expected)
                    self.assertIs(value[1][i + 1], actual[0][0][1][1])
                    self.assertIs(value[2], actual[0][0][2])
                    args = dict(model_ref=replace(ref, horizon_days=i + 1),
                                target_date=issue + timedelta(days=i), area_id='area-a')
                    build = comparison.mushroom_ml_runtime_features.build_runtime_features
                    self.assertEqual(
                        build(**args, area_context=value[0], area_series=value[1][i + 1], stations=value[2]),
                        build(**args, area_context=expected[0], area_series=expected[1][i + 1], stations=expected[2]),
                    )

    def test_shifted_multiple_cutoffs_keep_the_right_horizon_series(self):
        cache = {}
        with self.fixture():
            for index, (target, horizons) in enumerate((
                (date(2026, 10, 10), (1, 7)),
                (date(2026, 10, 12), (9, 3)),
            )):
                args = self.arguments(target_date=target, horizons=horizons)
                expected = comparison.prepare_area_weather(**args)
                actual, hit = comparison._cached_area_weather(**args, prepared_weather_cache=cache)
                self.assertEqual(actual, expected)
                self.assertEqual(hit, bool(index))
        self.assertEqual(len(cache), 2)

    def test_cache_separates_inputs_windows_cutoff_sets_and_physical_contract(self):
        variants = (
            {'area_id': 'area-b'},
            {'known_sites_path': Path('/different/sites.json')},
            {'weather_data_dir': Path('/different/weather')},
            {'target_date': date(2026, 10, 11)},
            {'horizons': (1, 2)},
            {'lookback_days': 365},
            {'include_physical_state': False},
            {'excluded_station_keys': frozenset({('aemet', 'X')})},
        )
        def prepare(**args):
            return object(), {int(h): {'inputs': args} for h in args['horizons']}, {}
        for changes in variants:
            with self.subTest(changes=changes), mock.patch.object(
                    comparison, 'prepare_area_weather', side_effect=prepare) as loader:
                cache = {}
                comparison._cached_area_weather(**self.arguments(), prepared_weather_cache=cache)
                _value, hit = comparison._cached_area_weather(**self.arguments(**changes), prepared_weather_cache=cache)
                self.assertFalse(hit)
                self.assertEqual(loader.call_count, 2)
        with mock.patch.object(comparison, 'prepare_area_weather', side_effect=prepare) as loader:
            cache = {}
            comparison._cached_area_weather(**self.arguments(), prepared_weather_cache=cache)
            with mock.patch.object(area_weather, 'WATER_STATE_CONTRACT_ID', 'other-contract'):
                _value, hit = comparison._cached_area_weather(**self.arguments(), prepared_weather_cache=cache)
            self.assertFalse(hit)
            self.assertEqual(loader.call_count, 2)

    def test_explicit_v2_window_is_preserved_and_not_promoted(self):
        args = self.arguments()
        window = object(), {1: {'daily_dates': ['extended-window']}}, {}
        cache = {comparison._prepared_weather_key(**args): window}
        with mock.patch.object(comparison, 'prepare_area_weather', return_value=('direct', {2: {}}, {})) as prepare:
            value, hit = comparison._cached_area_weather(**args, prepared_weather_cache=cache)
            self.assertIs(value, window)
            self.assertTrue(hit)
            shifted = self.arguments(target_date=date(2026, 10, 11), horizons=(2,))
            value, hit = comparison._cached_area_weather(**shifted, prepared_weather_cache=cache)
            self.assertEqual(value[0], 'direct')
            self.assertFalse(hit)
            prepare.assert_called_once()

    def test_no_cache_keeps_direct_execution(self):
        with mock.patch.object(comparison, 'prepare_area_weather', return_value=(None, {1: {}}, {})) as prepare:
            for _ in range(2):
                _value, hit = comparison._cached_area_weather(**self.arguments(), prepared_weather_cache=None)
                self.assertFalse(hit)
            self.assertEqual(prepare.call_count, 2)

    def test_prewarm_then_dated_comparisons_share_weather_and_predictions(self):
        registry = registry_module.load_registry(
            Path(__file__).resolve().parents[1] / 'mushroom-data/mushroom_ml_version_registry.json')
        ref = catalog.ModelRef(
            batch_id='batch-a', generation_id='generation-v5',
            version_id='biology_v5_raw_weather_discovery', temporal_contract_id=raw.LAG_CONTRACT_ID,
            profile_id='raw_primary_plus_physical_state', estimator_id='elastic_net_logistic_raw365_v1',
            species_id='boletus_edulis', horizon_days=1,
        )
        refs = [ref, replace(ref, estimator_id='sparse_group_logistic_raw365_v1')]
        manifest = {'schema_version': '1.0', 'kind': 'mushroom_ml_runtime_batch',
            'batch_id': 'batch-a', 'snapshot_id': 'sha256:' + 'a' * 64, 'artifacts': [{
                'artifact_ref': member.artifact_ref.as_dict(), 'supported_horizons': list(range(1, 8)),
                'path': catalog.model_relative_path(member.artifact_ref).as_posix(), 'sha256': 'b' * 64}
                for member in refs + [replace(member, species_id='amanita_caesarea') for member in refs]]}
        dated = [(date(2026, 10, 10) + timedelta(days=i), [{
            'version_id': member.version_id, 'temporal_contract_id': member.temporal_contract_id,
            'profile_id': member.profile_id, 'estimator_id': member.estimator_id, 'horizon_days': i + 1,
        } for member in refs]) for i in range(7)]
        prepared_cache, comparison_cache = {}, {}
        paths = dict(species_id='boletus_edulis', area_id='area-a', models_root=Path('/unused/models'),
                     known_sites_path=Path('/unused/sites.json'), weather_data_dir=Path('/unused/weather'),
                     prepared_weather_cache=prepared_cache, comparison_cache=comparison_cache)
        def sample(model_ref, **_args):
            return {'predictive_features': {'h': model_ref.horizon_days}, 'quality': {}, 'metadata': {}}
        with (
            mock.patch.object(comparison, 'prepare_area_weather', return_value=(None, {1: {}}, {})) as prepare,
            mock.patch.object(comparison.mushroom_ml_runtime_features, 'build_runtime_features', side_effect=sample) as features,
            mock.patch.object(comparison.mushroom_ml_runtime_inference, 'load_exact_artifact',
                              side_effect=lambda _registry, _manifest, model_ref, **_kwargs:
                                  {'offset': 0.01 if model_ref.estimator_id == refs[1].estimator_id else 0.0}),
            mock.patch.object(comparison.mushroom_ml_runtime_inference, 'predict_bundle_many',
                              side_effect=lambda bundle, rows, **_kwargs:
                                  [{'probability': row['h'] / 10 + bundle['offset']} for row in rows]) as predict,
        ):
            count = comparison.prewarm_selection_predictions(registry, manifest, dated,
                excluded_station_keys=frozenset(), **paths)
            results = [comparison.compare_selection(registry, manifest, selections,
                        target_date=target, **paths) for target, selections in dated]
            other_count = comparison.prewarm_selection_predictions(registry, manifest, dated,
                excluded_station_keys=frozenset(), **{**paths, 'species_id': 'amanita_caesarea'})
        self.assertEqual(count, 14)
        self.assertEqual(other_count, 14)
        prepare.assert_called_once()
        self.assertEqual(features.call_count, 14)  # Seven samples for each species.
        self.assertEqual(predict.call_count, 4)  # Both artifacts remain separate for each species.
        self.assertEqual([result['members'][0]['prediction']['probability'] for result in results],
                         [i / 10 for i in range(1, 8)])
        self.assertEqual([result['members'][1]['prediction']['probability'] for result in results],
                         [i / 10 + 0.01 for i in range(1, 8)])
        self.assertEqual([result['runtime_metrics']['weather_cache_status'] for result in results], ['hit'] * 7)

    def test_profile_feature_cache_isolates_every_model_field_and_exact_inputs(self):
        ref = catalog.ModelRef(
            batch_id='batch', generation_id='generation', version_id='biology_v3',
            temporal_contract_id='lag_event_biology_v3', profile_id='core',
            estimator_id='random_forest_restricted_v1', species_id='boletus_edulis', horizon_days=1,
        )
        inputs = dict(target_date=date(2026, 10, 10), area_id='area-a',
                      area_context=object(), area_series={}, stations={})
        cases = [(replace(ref, **{field: value}), inputs) for field, value in (
            ('batch_id', 'another'), ('generation_id', 'another'), ('version_id', 'another'),
            ('temporal_contract_id', 'another'), ('profile_id', 'another'),
            ('species_id', 'another'), ('horizon_days', 2),
        )]
        cases.extend((ref, {**inputs, field: value}) for field, value in (
            ('target_date', date(2026, 10, 11)), ('area_id', 'area-b'),
            ('area_context', object()), ('area_series', {}), ('stations', {}),
        ))
        for changed_ref, changed_inputs in cases:
            with self.subTest(ref=changed_ref, inputs=changed_inputs), mock.patch.object(
                    comparison.mushroom_ml_runtime_features, 'build_runtime_features', return_value={}) as build:
                cache = {}
                comparison._runtime_feature_sample(ref, **inputs, cache=cache)
                comparison._runtime_feature_sample(changed_ref, **changed_inputs, cache=cache)
                self.assertEqual(build.call_count, 2)

    def test_profile_feature_cache_matches_both_native_estimators_and_keeps_gates(self):
        refs = [catalog.ModelRef(
            batch_id='batch', generation_id='generation', version_id='biology_v3',
            temporal_contract_id='lag_event_biology_v3', profile_id='core',
            estimator_id=estimator, species_id='boletus_edulis', horizon_days=1,
        ) for estimator in ('random_forest_restricted_v1', 'logistic_regression_reduced_v1')]
        with self.fixture():
            context, series, stations = comparison.prepare_area_weather(**self.arguments(include_physical_state=False))
            inputs = dict(target_date=date(2026, 10, 10), area_id='area-a',
                          area_context=context, area_series=series[1], stations=stations)
            builder = comparison.mushroom_ml_runtime_features.build_runtime_features
            expected = [builder(ref, **inputs) for ref in refs]
            with mock.patch.object(comparison.mushroom_ml_runtime_features, 'build_runtime_features', wraps=builder) as build:
                cache = {}
                actual = [comparison._runtime_feature_sample(ref, **inputs, cache=cache) for ref in refs]
                self.assertEqual(actual, expected)
                self.assertIs(actual[0], actual[1])
                build.assert_called_once()

    def test_preparation_shares_sources_and_exact_station_windows_across_physical_modes(self):
        requests = [self.arguments(lookback_days=days, include_physical_state=physical)
                    for days, physical in ((90, False), (90, True), (365, True))]
        with self.fixture():
            expected = [comparison.prepare_area_weather(**args) for args in requests]
            with (
                mock.patch.object(area_weather, 'area_contexts', wraps=area_weather.area_contexts) as contexts,
                mock.patch.object(weather, 'load_stations_catalog', wraps=weather.load_stations_catalog) as stations_catalog,
                mock.patch.object(weather, 'load_daily_weather_parquet', wraps=weather.load_daily_weather_parquet) as daily,
                mock.patch.object(comparison, '_area_station_filter', wraps=comparison._area_station_filter) as filters,
                mock.patch.object(area_weather, 'materialize_area_series', wraps=area_weather.materialize_area_series) as series,
            ):
                cache = {}
                actual = [comparison._cached_area_weather(**args, prepared_weather_cache=cache)[0]
                          for args in requests]
            self.assertEqual(actual, expected)
            contexts.assert_called_once()
            stations_catalog.assert_called_once()
            filters.assert_called_once()
            self.assertEqual(daily.call_count, 2)
            self.assertEqual(series.call_count, 3)
            self.assertIs(actual[0][2], actual[1][2])
            self.assertIsNot(actual[1][2], actual[2][2])
            self.assertIsNot(actual[0][1][1], actual[1][1][1])
            self.assertNotIn('water_state_contract_id', actual[0][1][1])
            self.assertIn('water_state_contract_id', actual[1][1][1])
            context = cache[comparison._WEATHER_PREPARATION_CONTEXT_KEY]
            self.assertEqual(len(context.station_windows), 2)

    def test_preparation_bounds_station_retention_and_separates_area_exclusions_and_dates(self):
        with self.fixture():
            context = comparison._WeatherPreparationContext(('/unused/sites.json', '/unused/weather'))
            contexts = context.contexts(Path('/unused/sites.json'))[1]['area-a']
            args = dict(area_id='area-a', contexts=contexts,
                        earliest=date(2026, 10, 1), latest=date(2026, 10, 9), excluded=set())
            with mock.patch.object(weather, 'load_daily_weather_parquet', wraps=weather.load_daily_weather_parquet) as daily:
                first = context.stations(Path('/unused/weather'), **args)
                self.assertIs(first, context.stations(Path('/unused/weather'), **args))
                self.assertEqual(daily.call_count, 1)
                excluded = context.stations(Path('/unused/weather'), **{**args, 'excluded': {('test', 'B')}})
                self.assertNotIn(('test', 'B'), excluded)
                self.assertEqual(len(context.station_windows), 2)
                context.stations(Path('/unused/weather'), **{**args, 'earliest': date(2026, 9, 30)})
                self.assertEqual(len(context.station_windows), 2)
                context.stations(Path('/unused/weather'), **args)  # First range was evicted.
                self.assertEqual(daily.call_count, 4)
                context.stations(Path('/unused/weather'), **{**args, 'area_id': 'area-b'})
                self.assertEqual(len(context.station_windows), 1)
                self.assertEqual(daily.call_count, 5)
                context.stations(Path('/unused/weather'), **args)
                self.assertEqual(len(context.station_windows), 1)
                self.assertEqual(daily.call_count, 6)

    def test_shared_cache_replaces_preparation_context_for_another_runtime(self):
        with self.fixture(), mock.patch.object(area_weather, 'materialize_area_series', return_value={}):
            cache = {}
            comparison._cached_area_weather(**self.arguments(), prepared_weather_cache=cache)
            first = cache[comparison._WEATHER_PREPARATION_CONTEXT_KEY]
            args = self.arguments(weather_data_dir=Path('/other/weather'))
            comparison._cached_area_weather(**args, prepared_weather_cache=cache)
            second = cache[comparison._WEATHER_PREPARATION_CONTEXT_KEY]
            self.assertIsNot(first, second)
            self.assertEqual(second.source_identity[1], '/other/weather')
            with self.assertRaisesRegex(ValueError, 'another runtime'):
                comparison.prepare_area_weather(**args, preparation_context=first)
