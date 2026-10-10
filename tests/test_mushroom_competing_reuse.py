"""Check reuse against native runtime inputs, with synthetic weather only."""
import copy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_competing_features as features
from rainmapper_core import mushroom_competing_history as history
from rainmapper_core import mushroom_competing_panels as panels
from rainmapper_core import mushroom_ml_area_weather_runtime as weather
from rainmapper_core import mushroom_ml_biology_v3 as v3
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_runtime_features as runtime
from rainmapper_core import mushroom_ml_runtime_inference as inference
from rainmapper_core import mushroom_ml_weather_workspace as workspace
from tests.test_mushroom_competing_history import REF, sample
from tests import test_mushroom_competing_history as history_fixture
from tests import test_mushroom_water_unification as water_fixture
from tests import test_mushroom_ml_weather_workspace as workspace_fixture


class InputCacheTests(unittest.TestCase):
    def test_decoded_reuse_is_immutable_and_shares_existing_memory_budget(self):
        from copy import deepcopy
        with tempfile.TemporaryDirectory() as tmp, history.UnitCache(Path(tmp)/'units.sqlite') as units:
            cache = features.Inputs(units.db)
            value = {'weather': [1., None, {'quality': True}], 'metadata': {'source': 'fixture'}}
            cache.write('a', value)
            one = cache.read_shared('a')
            self.assertEqual(one, value)
            with patch.object(cache, 'read', side_effect=AssertionError('duplicate decode')):
                self.assertIs(cache.read_shared('a'), one)
            self.assertEqual(history.canonical(one), history.canonical(value))
            self.assertIs(deepcopy(one), one)
            for change in (lambda: one.update(x=1), lambda: one['weather'].append(3),
                           lambda: one['weather'][2].clear()):
                with self.assertRaisesRegex(TypeError, 'immutable_history_input'):
                    change()
            mutable = cache.read('a'); mutable['weather'].append(3)
            self.assertEqual(one, value)
            with patch.object(features, 'MAX_MEMORY_BYTES', 2048):
                for i in range(30):
                    cache.write(str(i), value)
                    self.assertEqual(cache.read_shared(str(i)), value)
                    self.assertLessEqual(cache.memory_bytes + cache.shared_bytes, 2048)

    def test_bounded_cache_survives_reopen_without_evicting_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'units.sqlite'
            with history.UnitCache(path) as units:
                units.put('result', {'rows': []})
                cache = features.Inputs(units.db, limit=300)
                for index in range(30):
                    cache.write(str(index), {'value': hashlib.sha256(str(index).encode()).hexdigest()})
                cache.flush()
                self.assertLessEqual(cache.used, 300)
                self.assertLess(units.db.execute('SELECT count(*) FROM runtime_inputs').fetchone()[0],30)
                self.assertEqual(units.read('result'), {'rows': []})
            with history.UnitCache(path) as units:
                cache = features.Inputs(units.db, limit=300)
                self.assertIsNone(cache.read('0'))
                self.assertIsNotNone(cache.read('29'))
                units.db.execute("UPDATE runtime_inputs SET payload=? WHERE key='29'", (b'bad',))
                with self.assertRaisesRegex(ValueError,'integrity'):
                    features.Inputs(units.db).read('29')
                with patch.object(features,'MAX_RAW_BYTES',4):
                    with self.assertRaisesRegex(ValueError,'size_limit'):
                        cache.write('oversized',{'large': 10})

    def test_reviewed_revision_reuse_requires_current_tensors_and_week_inputs(self):
        benchmark = history_fixture.HistoryTests().benchmark()
        with tempfile.TemporaryDirectory() as tmp, history.UnitCache(Path(tmp)/'units.sqlite') as cache:
            def run(revision, context, compatible=()):
                return list(history.evaluate_benchmark(benchmark,[REF],cutoff='2026-10-05',
                    implementation_id=revision,targets={'boletus_aereus'},cache=cache,
                    evaluate=lambda *a:{'rows':[],'missing':[]},unit_context=lambda *a:context,
                    compatible_implementation_ids=compatible))
            old = run('reviewed-old','week')
            reused = run('new','week',('reviewed-old',))
            self.assertEqual([u['unit_key'] for u in old],[u['unit_key'] for u in reused])
            self.assertTrue(all(u['reused'] for u in reused))
            self.assertFalse(any(u['reused'] for u in run('unreviewed','week')))
            different = run('new','changed-week',('reviewed-old',))
            self.assertFalse(different[-1]['reused'])
            benchmark['samples'][0]['predictive_features']['rain'] = 99.
            self.assertFalse(any(u['reused'] for u in run('new','week',('reviewed-old',))))


class RuntimeReuseTests(unittest.TestCase):
    def setUp(self):
        water = water_fixture.WaterUnificationTests(); water.setUp()
        station = next(iter(water.stations.values()))
        first = min(station.records_by_day)
        records = dict(station.records_by_day)
        for offset in range(1,31):
            day = first-timedelta(days=offset)
            records[day] = replace(records[first],day=day)
        self.stations = {('meteocat','W'):replace(station, records_by_day=records)}
        # Duplicate rainfall crossing window boundaries, one absent station,
        # and an irrelevant far station exercise slicing equivalence.
        wu = replace(station,source='wunderground',station_code='WU',records_by_day={
            d:replace(r,source='wunderground',station_code='WU',rain_mm=5.) for d,r in records.items()})
        self.stations['wunderground','WU'] = wu
        self.stations['test','old'] = replace(station,records_by_day={first:records[first]})
        self.stations['test','far'] = replace(station,lat=50.,lon=10.)
        self.workspace = workspace_fixture.OperationalWeatherWorkspaceTests().workspace(self.stations)
        self.context, self.end = water.context, water.end
        self.rows = [sample('visit',self.end.isoformat())]
        self.rows[0]['metadata']['area_id']='area'
        self.profiles = catalog.catalog_entries(json.loads((Path(__file__).resolve().parents[1]/
            'mushroom-data/mushroom_ml_version_registry.json').read_bytes()))
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = panels.Panels(self.root/'panels.sqlite'); self.addCleanup(self.store.close)
        self.units = self.enterContext(history.UnitCache(self.root/'units.sqlite'))

    def builder(self, revision='fast'):
        with (patch.object(v3,'load_micro_area_contexts',return_value={'micro':self.context}),
              patch.object(workspace,'active_workspace',return_value=self.workspace)):
            return panels.Builder(store=self.store, known_sites=self.root/'sites.json',data_dir=self.root,
                stations_file=self.root/'stations.txt',profiles=self.profiles,progress=lambda e:None,
                inputs=features.Inputs(self.units.db),input_revision=revision)

    def direct_series(self,builder,area,cutoff,days,physical,key):
        return weather.materialize_area_series(area_id=area,end_day=cutoff,days=days,
            microareas_by_area=builder.microareas,
            stations=builder._stations(area,cutoff-timedelta(days=days-1),cutoff),
            excluded_station_keys=builder.workspace.disabled,include_physical_state=physical)

    def test_input_identity_never_builds_unused_features_and_rejects_weather_changes(self):
        ref = catalog.ModelArtifactRef.from_mapping(REF)
        builder = self.builder()
        with patch.object(builder, 'samples', side_effect=AssertionError('unused features')):
            original = builder.input_fingerprint(ref, self.rows)
            self.assertEqual(builder.input_fingerprint(replace(ref, estimator_id='other'), self.rows), original)
        self.assertEqual(builder.stats['features_built'], 0)
        source = self.workspace.stations['meteocat','W']
        records = dict(source.records_by_day)
        day = self.end-timedelta(days=15)
        records[day] = replace(records[day], rain_mm=99.)
        self.workspace.stations = {**self.workspace.stations,
            ('meteocat','W'): replace(source, records_by_day=records)}
        self.assertNotEqual(self.builder().input_fingerprint(ref, self.rows), original)
        self.assertNotEqual(self.builder('new-producer').input_fingerprint(ref, self.rows), original)

    def test_week_source_fingerprint_covers_every_consumed_window_without_expanding_members(self):
        for temporal in ('fixed_gap_7d_biology_v3','lag_event_biology_v3'):
            ref = catalog.ModelArtifactRef.from_mapping({**REF,'temporal_contract_id':temporal})
            builder = self.builder()
            requests = list(builder._requests(ref,self.rows))
            earliest = min(row[6] for row in requests)
            latest = max(row[7] for row in requests)
            with (patch.object(builder,'_signature',wraps=builder._signature) as signature,
                  patch.object(builder,'_requests',side_effect=AssertionError('unnecessary weekly expansion'))):
                builder.input_fingerprint(ref,self.rows)
                signature.assert_called_once_with('area',earliest,latest)

    def test_deferred_predictions_equal_eager_weeks_and_never_refit(self):
        from rainmapper_core import mushroom_competing_fits as fits
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        for temporal in ('fixed_gap_7d_biology_v3', 'lag_event_biology_v3'):
            ref = catalog.ModelArtifactRef.from_mapping({**REF, 'temporal_contract_id': temporal})
            builder = self.builder()
            runtime_rows = list(builder.samples(ref, self.rows))
            columns = sorted(runtime_rows[0][-1]['predictive_features'])
            training = [sample('train-'+str(i), '2020-09-01', 'favorable' if i%2 else 'unfavorable') for i in range(8)]
            for i, row in enumerate(training):
                row['predictive_features'] = {c:float(i+1) for c in columns}
            benchmark = {'feature_set': {'predictive_feature_cols': columns}, 'samples': training}
            bundle = trainer.fit_artifact(ref, benchmark, snapshot_id='synthetic')
            eager_key, deferred_key = temporal+'eager', temporal+'requested'
            builder(bundle, ref, self.rows, eager_key)
            cache = fits.Fits(self.units.db, 'synthetic')
            cache.write(deferred_key, bundle, {})
            self.assertTrue(builder.defer(ref, deferred_key, cache, deferred_key))
            self.assertEqual(self.store.db.execute('SELECT count(*) FROM panels WHERE unit=?', (deferred_key,)).fetchone()[0], 0)
            visits = [{'species_id':REF['species_id'], 'id':oid, 'day':self.end.isoformat(), 'area':'area'}
                      for oid in ('visit','same-inputs-different-observation')]
            requested = panels.RequestedPanels(self.store, cache, visits, lambda:builder)
            self.store.materialize_missing = requested
            sid = REF['species_id']
            with patch.object(trainer, 'fit_artifact', side_effect=AssertionError('must not refit')):
                # Read two separated cells, then read the first again from the
                # merged persisted packet. Unrequested cells remain absent.
                selected = [runtime_rows[0], runtime_rows[-1], runtime_rows[0]]
                for _, _, day, h, _ in selected:
                    self.assertEqual(self.store.read(deferred_key, sid, 'visit', day, h),
                                     self.store.read(eager_key, sid, 'visit', day, h))
                self.assertEqual(requested.stats['models_loaded'], 1)
                self.assertEqual(requested.stats['members_built'], 2)
                self.assertEqual(len(self.store._packet(deferred_key, sid, 'visit')), 2)
                with self.assertRaisesRegex(ValueError, 'outside_week'):
                    self.store.read(deferred_key, sid, 'visit', self.end+timedelta(days=20), 7)
                issue = self.end-timedelta(days=3)
                before = requested.stats['members_built']
                with patch.object(inference,'predict_bundle_many',wraps=inference.predict_bundle_many) as predict:
                    for offset in range(7):
                        day, h = issue+timedelta(days=offset), offset+1 if temporal.startswith('lag_') else 7
                        expected = self.store.read(eager_key,sid,'visit',day,h)
                        self.assertEqual(self.store.read_week_member(deferred_key,sid,'visit',day,h,issue=issue),expected)
                    self.assertEqual(predict.call_count,1)
                self.assertLessEqual(requested.stats['members_built']-before,7)
                with patch.object(inference,'predict_bundle_many',side_effect=AssertionError('duplicate forecast')):
                    for offset in range(7):
                        day, h = issue+timedelta(days=offset), offset+1 if temporal.startswith('lag_') else 7
                        self.assertEqual(self.store.read_week_member(deferred_key,sid,
                            'same-inputs-different-observation',day,h,issue=issue),
                            self.store.read(eager_key,sid,'visit',day,h))
                self.assertEqual(requested.stats['members_reused'],7)
            self.store.materialize_missing = None

    def test_station_windows_share_records_but_preserve_date_boundaries(self):
        builder = self.builder()
        start, end = self.end-timedelta(days=15), self.end-timedelta(days=1)
        actual = builder._stations('area', start, end)
        self.assertIs(actual, builder._stations('area', start, end))
        for key, station in actual.items():
            source = builder._area('area')[key]
            self.assertIs(station.records_by_day.records, source.records_by_day)
            self.assertEqual(dict(station.records_by_day),
                             {d:r for d,r in source.records_by_day.items() if start <= d <= end})
            self.assertNotIn(end+timedelta(days=1), station.records_by_day)
        for offset in range(30):
            builder._stations('area', start-timedelta(days=offset), end-timedelta(days=offset))
        self.assertLessEqual(len(builder.station_windows), 16)

    def test_exact_prepared_soil_window_is_reused_without_repeating_physics(self):
        builder = self.builder()
        cutoff = self.end - timedelta(days=1)
        builder._area('area')
        expected = self.direct_series(builder, 'area', cutoff, 365, True, 'unused')
        state = {'predictive_features': {k:v for k,v in expected.items()
                    if k.startswith('soil_water_') and k not in ('soil_water_quality', 'soil_water_metadata')},
                 'quality': expected['soil_water_quality'],
                 'metadata': {**expected['soil_water_metadata'], 'microarea_weather_idw_quality': {'audit':True}}}
        start = cutoff - timedelta(days=364)
        view = builder._workspace('area')
        micro = view.weather_for_contexts(builder.microareas['area'], start_day=start, end_day=cutoff)
        rain = {k:v['daily_rain_idw_mm'] for k,v in micro.items()}
        eto = {c.micro_area_id:view.eto_for_context(c.micro_area_id, start_day=start, end_day=cutoff)
               for c in builder.microareas['area']}
        self.workspace.store_soil_bundle(workspace.DEFAULT_SOIL_VARIANT_ID, 'area', cutoff,
            workspace.AreaSoilBundle(aggregated=state, daily_fraction_mean=expected['daily_soil_water_fraction_mean'],
                                    input_signature=workspace.soil_inputs_signature(rain, eto)))
        with patch.object(weather.mushroom_soil_water_state, 'build_soil_water_state',
                          side_effect=AssertionError('duplicate physics')):
            actual = builder._series('area', cutoff, 365, True, 'cached-soil')
            self.assertEqual(actual, expected)
            with self.assertRaisesRegex(AssertionError, 'duplicate physics'):
                builder._series('area', cutoff, 364, True, 'different-window')
            # Same area/date/length is insufficient: V4 and inference can have
            # different duplicate-rain policies at the window's first day.
            changed_rain = copy.deepcopy(rain)
            next(iter(changed_rain.values()))[0] = 987.
            self.workspace.store_soil_bundle(workspace.DEFAULT_SOIL_VARIANT_ID, 'area', cutoff,
                workspace.AreaSoilBundle(aggregated=state, daily_fraction_mean=expected['daily_soil_water_fraction_mean'],
                                        input_signature=workspace.soil_inputs_signature(changed_rain, eto)))
            with self.assertRaisesRegex(AssertionError, 'duplicate physics'):
                builder._series('area', cutoff, 365, True, 'different-inputs')
        self.assertEqual(builder.stats['soil_states_reused'], 1)

    def test_native_week_features_match_for_v3_to_v6_and_both_temporal_contracts(self):
        fast, native = self.builder(), self.builder('native')
        native._series = lambda *args:self.direct_series(native,*args)
        for configuration in self.profiles:
            version,profile = configuration['version_id'],configuration['profile_id']
            if version == 'altitude_v2':
                continue
            for temporal in configuration['temporal_contract_ids']:
                count = 49 if temporal.startswith('lag_') else 13
                with self.subTest(version=version,profile=profile,temporal=temporal):
                    ref = catalog.ModelArtifactRef.from_mapping({**REF,'version_id':version,
                        'profile_id':profile,'temporal_contract_id':temporal})
                    expected = list(native.samples(ref,self.rows))
                    actual = list(fast.samples(ref,self.rows))
                    self.assertEqual(len(actual),count)
                    self.assertEqual(actual,expected)
                    self.assertEqual(fast.fingerprint(ref,self.rows),native.fingerprint(ref,self.rows))
        self.assertIs(fast.view._weather_base,self.workspace._weather_base)
        self.assertLessEqual(len(fast.view._weather_views),1)

    def test_reopen_estimator_change_and_new_visit_reuse_inputs_but_weather_edit_invalidates(self):
        ref = catalog.ModelArtifactRef.from_mapping(REF)
        first = self.builder()
        original = first.fingerprint(ref,self.rows)
        self.assertEqual(first.stats['features_built'],13)
        self.assertEqual(first.stats['weather_built'],13)
        self.units.db.close(); self.units = self.enterContext(history.UnitCache(self.root/'units.sqlite'))
        other = self.builder()
        changed_ref = replace(ref,estimator_id='another-estimator',generation_id='new-weights')
        with (patch.object(weather,'materialize_area_series',side_effect=AssertionError('must reuse')),
              patch.object(runtime,'build_runtime_features',side_effect=AssertionError('must reuse'))):
            self.assertEqual(other.fingerprint(changed_ref,self.rows),original)
            rows = copy.deepcopy(self.rows); rows[0]['metadata']['observation_id']='another-visit'
            list(other.samples(changed_ref,rows))
        self.assertEqual(other.stats['features_reused'],13)
        self.assertEqual(other.stats['fingerprints_restored'],1)
        self.workspace.stations = dict(self.workspace.stations)
        source = self.workspace.stations['meteocat','W']
        records = dict(source.records_by_day)
        # A day later than every historical cutoff is not consumed.
        records[self.end]=replace(records[self.end],rain_mm=1000.)
        self.workspace.stations['meteocat','W']=replace(source,records_by_day=records)
        self.assertEqual(self.builder().fingerprint(ref,self.rows),original)
        day = self.end-timedelta(days=15)
        records[day]=replace(records[day],rain_mm=1000.)
        self.workspace.stations['meteocat','W']=replace(source,records_by_day=records)
        self.workspace._weather_base.clear();self.workspace._eto_base.clear()
        changed = self.builder()
        self.assertNotEqual(changed.fingerprint(ref,self.rows),original)
        self.assertEqual(changed.stats['features_built'],13)

    def test_fingerprint_shared_by_estimators_without_rereading_feature_vectors(self):
        ref = catalog.ModelArtifactRef.from_mapping(REF)
        builder = self.builder()
        original = builder.fingerprint(ref, self.rows)
        with patch.object(builder, 'samples', side_effect=AssertionError('must reuse fingerprint')):
            self.assertEqual(builder.fingerprint(replace(ref, estimator_id='another'), self.rows), original)
        self.assertEqual(builder.stats['fingerprints_reused'], 1)
        rows = copy.deepcopy(self.rows)
        rows[0]['metadata']['observation_id'] = 'new-visit'
        self.assertNotEqual(builder.fingerprint(ref, rows), original)

    def test_persisted_fingerprint_survives_feature_eviction_and_checks_code(self):
        ref = catalog.ModelArtifactRef.from_mapping(REF)
        original = self.builder().fingerprint(ref, self.rows)
        # Deletion applies only to disposable fixture inputs, never real data.
        with self.units.db:
            self.units.db.execute('DELETE FROM runtime_inputs')
        reopened = self.builder()
        with patch.object(reopened, 'samples', side_effect=AssertionError('do not rebuild weather/features')):
            self.assertEqual(reopened.fingerprint(ref, self.rows), original)
        self.assertEqual(reopened.stats['features_built'], 0)
        changed = self.builder(revision='different-feature-producer')
        with patch.object(changed, 'samples', side_effect=AssertionError('new producer must validate')):
            with self.assertRaisesRegex(AssertionError, 'new producer'):
                changed.fingerprint(ref, self.rows)
        with self.units.db:
            self.units.db.execute("UPDATE runtime_fingerprints SET value=?", ('0'*64,))
        with self.assertRaisesRegex(ValueError, 'fingerprint_integrity'):
            self.builder().fingerprint(ref, self.rows)

    def test_inference_is_one_batch_per_visit_and_keeps_unavailable_days(self):
        builder = self.builder()
        ref = catalog.ModelArtifactRef.from_mapping(REF)
        samples = list(builder.samples(ref,self.rows))
        samples[0][-1]['quality']['inference_eligible']=False
        def predict(bundle, values, species_ids, applicability_only=False):
            self.assertEqual(len(values),12)
            return [{'probability':.7,'applicability':{'status':'inside'}} for _ in values]
        with patch.object(builder,'samples',return_value=iter(samples)), patch.object(inference,'predict_bundle_many',side_effect=predict) as batch:
            builder({},ref,self.rows,'unit')
        self.assertEqual(batch.call_count,1)
        for i,(sid,oid,day,horizon,_) in enumerate(samples):
            result=self.store.read('unit',sid,oid,day,horizon)
            self.assertEqual(result['available'],i!=0)
            if i: self.assertEqual(result['prediction']['probability'],.7)


if __name__ == '__main__':
    unittest.main()


class TransientInputTests(unittest.TestCase):
    def test_row_budget_and_immutable_reuse(self):
        cache = features.TransientInputs(limit=2048)
        for i in range(50):
            cache.put(str(i), {'predictive_features':{'rain':[i, None]},'quality':{'eligible':True}})
            self.assertLessEqual(cache.used, 2048)
        row = cache.get('49')
        self.assertIsNotNone(row)
        self.assertIs(cache.get('49'), row)
        with self.assertRaises(TypeError):
            row['predictive_features']['rain'].append(4)
        cache.put('huge', {'value':'x'*4096})
        self.assertIsNone(cache.get('huge'))
        self.assertEqual(row['predictive_features']['rain'], [49,None])
