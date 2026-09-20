"""Contract/parity tests for the accepted SMI, independent of Docker or HA."""
from dataclasses import replace
from datetime import date, timedelta
import copy
import unittest

from rainmapper_core import mushroom_water_physics as physics
from rainmapper_core import mushroom_map_hydrology as map_water
from rainmapper_core import mushroom_soil_water_state as soil
from rainmapper_core import mushroom_ml_area_weather_runtime as area_runtime
from rainmapper_core import mushroom_ml_biology_v3 as v3
from rainmapper_core import mushroom_ml_biology_v4 as v4
from rainmapper_core import mushroom_ml_runtime_features as runtime_features
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_runtime_inference as inference
from rainmapper_core import mushroom_ml_model_catalog as catalog
from tests import test_mushroom_ml_weather_workspace as workspace_fixture
from tests import test_mushroom_soil_water_state as soil_fixture
from tests import test_mushroom_ml_biology_v4 as biology_fixture


class WaterUnificationTests(unittest.TestCase):
    def setUp(self):
        fixture = workspace_fixture.OperationalWeatherWorkspaceTests()
        self.end = date(2026, 8, 15)
        days = [self.end-timedelta(days=i) for i in reversed(range(365))]
        # A real recharge outside the shortest chart, then a prolonged drydown.
        station = fixture.station('W', {d: 65.0 if i%43 == 0 else 0.0 for i,d in enumerate(days)})
        station = replace(station, source='meteocat', lat=42.,lon=2., altitude_m=1000., records_by_day={
            d:replace(record,source='meteocat',lat=42.,lon=2.,wind_avg_kmh=7.2,wind_source_height_m=10.)
            for d,record in station.records_by_day.items()})
        self.stations = {('meteocat','W'):station}
        self.workspace = fixture.workspace(self.stations)
        self.context = v3.MicroAreaContext(micro_area_id='micro',area_id='area',lat=42.,lon=2.,
            altitude_m=1000.,location_source='test',soilgrids_water=soil_fixture.MushroomSoilWaterStateTests().context())
        self.weather = self.workspace.weather_for_contexts([self.context],start_day=days[0],end_day=self.end)['micro']
        self.eto = self.workspace.eto_for_context('micro',start_day=days[0],end_day=self.end)
        self.area = area_runtime.materialize_area_series(area_id='area',end_day=self.end,days=365,
            microareas_by_area={'area':[self.context]},stations=self.stations)

    def test_training_workspace_point_and_area_have_same_et_and_water(self):
        wind,_ = physics.reference_wind(self.stations,42.,2.,self.weather['daily_dates'],1000.)
        result = map_water.build_history(self.weather,42.,60,60.,altitude_m=1000.,wind_u2_m_s=wind)
        self.assertEqual(result['et0_method_counts']['pm_station_wind'],365)
        for map_et,area_et,train_et in zip(result['et0_mm'],self.area['daily_eto0_mean_mm'][-60:],self.eto[-60:]):
            self.assertAlmostEqual(map_et,train_et,places=6)
            self.assertAlmostEqual(area_et,train_et,places=10)
        for pct,fraction in zip(result['smi_pct'],self.area['daily_soil_water_fraction_mean'][-60:]):
            self.assertLessEqual(abs(pct/100-fraction),5.6e-6) # display 0.001%, tensor 1e-6
        self.assertEqual(result['method_id'],physics.WATER_STATE_CONTRACT_ID)
        self.assertIsNotNone(result['smi_legacy_pct'][-1])
        self.assertNotEqual(result['smi_pct'][-1],result['smi_legacy_pct'][-1])

    def test_display_windows_do_not_restart_and_gaps_do_not_become_dry(self):
        values = [map_water.build_history(self.weather,42.,n,60.,altitude_m=1000.)['smi_pct'][-1]
                  for n in (7,15,30,60)]
        self.assertEqual(len(set(values)),1)
        weather = copy.deepcopy(self.weather)
        weather['daily_rain_idw_mm'][-10] = None
        result = map_water.build_history(weather,42.,7,60.,altitude_m=1000.)
        self.assertTrue(all(v is None for v in result['smi_pct']))
        state = soil.build_soil_water_state(dates=[date.fromisoformat(d) for d in weather['daily_dates']],
            rain_idw_mm=weather['daily_rain_idw_mm'],reference_evapotranspiration_mm=self.eto,
            soilgrids_context=self.context.soilgrids_water)
        self.assertIsNone(state['predictive_features']['soil_water_at_cutoff_fraction'])

    def test_fallback_is_explicit_and_is_not_a_zero_et(self):
        weather = copy.deepcopy(self.weather)
        weather['daily_humidity_min_idw_pct'][-1] = None
        result = physics.reference_et_series(weather,42.,altitude_m=1000.)
        self.assertEqual(result['et0_methods'][-1],'hargreaves')
        self.assertGreater(result['et0_mm'][-1],0)
        self.assertEqual(result['et0_methods'][-2],'pm_estimated_wind')

    def test_excluded_station_cannot_supply_reference_wind(self):
        # Keep identical meteorology available from a non-XEMA station, while
        # excluding the only station with an admissible measured wind height.
        source = next(iter(self.stations.values()))
        other = replace(source, source='other')
        stations = {**self.stations, ('other','W'):other}
        excluded = area_runtime.materialize_area_series(area_id='area',end_day=self.end,days=365,
            microareas_by_area={'area':[self.context]},stations=stations,
            excluded_station_keys={('meteocat','W')})
        expected = physics.reference_et_series(self.weather,42.,altitude_m=1000.)['et0_mm']
        for actual, value in zip(excluded['daily_eto0_mean_mm'],expected):
            self.assertAlmostEqual(actual,value,places=10)

    def test_v4_consumes_shared_daily_et_instead_of_recomputing_area_hargreaves(self):
        source = biology_fixture.MushroomMLBiologyV4Tests().source_v3_sample()
        weather = source['metadata']['weather_series']
        weather['daily_eto0_mean_mm'] = self.eto[-90:]
        result = v4.build_biology_v4_sample(source,temporal_contract_id=v4.FIXED_GAP_7D_BIOLOGY_V4_ID)
        expected = sum(5.-v for v in self.eto[-7:])
        self.assertAlmostEqual(result['predictive_features']['climatic_water_balance_cutoff_0_7d_mm'],expected,places=5)

    def test_v5_training_and_runtime_keep_smi_scale_and_physical_channels(self):
        source = biology_fixture.MushroomMLBiologyV4Tests().source_v3_sample()
        source['metadata'].update(target_date=(self.end+timedelta(days=7)).isoformat(),horizon_days=7,species_id='boletus_edulis')
        trained = raw.build_v5_sample(source,self.area,temporal_contract_id=raw.FIXED_CONTRACT_ID)
        ref = catalog.ModelRef(batch_id='b',generation_id='g',version_id=raw.VERSION_ID,
            temporal_contract_id=raw.FIXED_CONTRACT_ID,profile_id='raw_primary_plus_physical_state',
            estimator_id='elastic_net_logistic_raw365_v1',species_id='boletus_edulis',horizon_days=7)
        predicted = runtime_features.build_runtime_features(ref,target_date=self.end+timedelta(days=7),
            area_id='area',area_context=None,area_series=self.area,stations=self.stations)
        self.assertEqual(trained['predictive_features'],predicted['predictive_features'])
        self.assertTrue(0 <= predicted['predictive_features']['soil_water_fraction__lag_000'] <= 1)

    def test_physical_artifact_requires_current_inputs_and_retraining(self):
        ref = catalog.ModelArtifactRef(batch_id='b',generation_id='g',version_id='biology_v4',
            temporal_contract_id=v4.FIXED_GAP_7D_BIOLOGY_V4_ID,profile_id='climatic_balance',
            estimator_id='logistic_regression_reduced_v1',species_id='boletus_edulis')
        field = 'climatic_water_balance_cutoff_0_7d_mm'
        benchmark = {'feature_set':{'predictive_feature_cols':[field]},'samples':[
            {'prediction_target':'favorable' if i%2 else 'unfavorable','predictive_features':{field:float(i)},
             'quality':{'training_eligible':True},'metadata':{'species_id':'boletus_edulis'}} for i in range(12)]}
        with self.assertRaisesRegex(ValueError,'water_state_contract_mismatch'):
            trainer.fit_artifact(ref,benchmark,snapshot_id='test')
        benchmark['water_state_contract_id'] = physics.WATER_STATE_CONTRACT_ID
        bundle = trainer.fit_artifact(ref,benchmark,snapshot_id='test')
        result = inference.predict_bundle(bundle,{field:3.},species_id='boletus_edulis')
        self.assertIsInstance(result,dict)
        del bundle['water_state_contract_id']
        with self.assertRaisesRegex(ValueError,'water_state_contract_mismatch'):
            inference.predict_bundle(bundle,{field:3.},species_id='boletus_edulis')
        # Non-hydric weights remain usable: no mandatory retrain by estimator name.
        physics.validate_water_contract({},['rain_cutoff_0_7d_mm','target_day_sin'])

    def test_real_v4_v5_builders_match_inference_with_shared_and_direct_weather(self):
        import contextlib
        import importlib.util
        import io
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from types import SimpleNamespace
        from unittest.mock import patch
        from rainmapper_core import mushroom_ml_weather_workspace as workspace

        def load(name):
            spec = importlib.util.spec_from_file_location(name,Path(__file__).resolve().parents[1]/'scripts'/name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        builders = [load(name) for name in ('build-biology-v4-benchmark.py','build-biology-v5-raw-benchmark.py')]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            sites,stations = root/'sites.json', root/'stations.txt'
            sites.write_text(json.dumps({'areas':[{'area_id':'area','representative_location':{'lat':42.,'lon':2.}}],
                'micro_areas':[{'micro_area_id':'micro','area_id':'area','derived_context':{'soilgrids_water':self.context.soilgrids_water}}]}))
            stations.write_text('')
            fixed,lag = root/'fixed.json',root/'lag.json'
            for path,is_lag in ((fixed,False),(lag,True)):
                row = biology_fixture.MushroomMLBiologyV4Tests().source_v3_sample(lag=is_lag)
                row['metadata'].update(target_date=(self.end+timedelta(days=3 if is_lag else 7)).isoformat(),
                                       horizon_days=3 if is_lag else 7,species_id='boletus_edulis')
                # Use the actual IDW weather, not the constant fixture rain.
                view = row['metadata']['weather_series']
                for dst,src in [('daily_area_rain_idw_mean_mm','daily_rain_idw_mm'),
                                ('daily_temp_min_corrected_c','daily_temp_min_idw_c'),
                                ('daily_temp_max_corrected_c','daily_temp_max_idw_c'),
                                ('daily_humidity_min_pct','daily_humidity_min_idw_pct'),
                                ('daily_humidity_max_pct','daily_humidity_max_idw_pct')]:
                    view[dst]=self.weather[src][-90:]
                path.write_text(json.dumps({'feature_set':{'id':v3.LAG_EVENT_BIOLOGY_V3_ID if is_lag else v3.FIXED_GAP_7D_BIOLOGY_V3_ID},'samples':[row]}))
            (root/'MANIFEST.json').write_text('{}')
            for use_workspace in (True,False):
                v4_path=root/f'v4-{use_workspace}.json'
                out=root/f'v5-{use_workspace}';out.mkdir()
                args4=SimpleNamespace(v3_benchmark=fixed,known_sites=sites,stations_file=stations,data_dir=root,output=v4_path)
                args5=SimpleNamespace(v3_fixed=fixed,v3_lag=lag,known_sites=sites,stations_file=stations,data_dir=root,output_dir=out)
                with (patch.object(v3,'load_micro_area_contexts',return_value={'micro':self.context}),
                      patch.object(workspace,'active_workspace',return_value=self.workspace if use_workspace else None),
                      patch.object(builders[0].weather_context,'load_stations_catalog',return_value=__import__('pandas').DataFrame([
                          {'source':'meteocat','station_code':'W','lat':42.,'lon':2.}])),
                      patch.object(builders[0].weather_context,'load_daily_weather_parquet',return_value=self.stations),
                      contextlib.redirect_stdout(io.StringIO())):
                    with patch.object(builders[0],'parse_args',return_value=args4): builders[0].main()
                    with patch.object(builders[1],'parse_args',return_value=args5): builders[1].main()
                built4=json.loads(v4_path.read_text());built5=json.loads((out/'biology-v5-fixed.json').read_text())
                self.assertEqual(built4['water_state_contract_id'],physics.WATER_STATE_CONTRACT_ID)
                self.assertEqual(built5['water_state_contract_id'],physics.WATER_STATE_CONTRACT_ID)
                state=built4['soil_variants']['wv0033_0_30cm']['area_state_catalog']['area|2026-08-15']
                for key,value in state['predictive_features'].items():
                    self.assertEqual(value,self.area[key])
                field='climatic_water_balance_cutoff_0_7d_mm'
                expected=sum(p-e for p,e in zip(self.weather['daily_rain_idw_mm'][-7:],self.eto[-7:]))
                self.assertAlmostEqual(built4['samples'][0]['predictive_features'][field],expected,places=5)
                features=built5['samples'][0]['predictive_features']
                self.assertAlmostEqual(features['eto0_mm__lag_000'],self.eto[-1],places=5)
                self.assertEqual(features['soil_water_area_mean_at_cutoff'],self.area['soil_water_area_mean_at_cutoff'])
                self.assertEqual(features['soil_water_fraction__lag_000'],self.area['daily_soil_water_fraction_mean'][-1])
