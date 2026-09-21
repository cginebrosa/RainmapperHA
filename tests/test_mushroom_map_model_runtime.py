import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from datetime import date, datetime, timezone
import importlib.util
import io

from rainmapper_core.mushroom_map_model_runtime import projected_quality, PointModelRuntime
from rainmapper_core import mushroom_prediction_map as contract


class ProjectionTests(unittest.TestCase):
    def test_midnight_week_calculates_without_runner_and_rejects_future_cutoffs(self):
        from tests.test_mushroom_map_prediction import PointWeekTests
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profiles.json'
            path.write_text(json.dumps({'species_profiles':[{'species_id':'test',
                'phenology':{'main_months':[9],'secondary_months':[]}}]}))
            r=PointModelRuntime(registry_path='unused',models_root=folder,profiles_path=path,
                                data_root=folder,stations_file='unused')
            r.resolutions={'test':PointWeekTests().resolutions()}
            r.revision='test';r.manifest={'batch_id':'test'};r.registry={};r.catalog_profiles={}
            r.installed=['biology_v6'];r.quality={};r.weather.generation=SimpleNamespace(generation_id='test')
            geography={'ecology':{'status':'available','species':[{'species_id':'test','status':'compatible',
                'daily_statuses':['compatible']*7,'daily_season_phases':['main']*7}]}}
            def selection(*args,**kwargs):
                return SimpleNamespace(horizon_days=args[2]['horizon_days'],reference=args[2])
            applicability={'status':'within_observed_range'}
            def compare(*args,**kwargs):
                return {'members':[{'model_ref':ref.reference,'available':True,
                    'prediction':{'probability':.6,'applicability':applicability},
                    'evaluation':{'evidence':'better_than_prevalence','brier_score':.1,
                     'prevalence_brier_score':.25,'brier_delta_vs_prevalence':.15,'roc_auc':.8}}
                    for ref in args[2]]}
            module='rainmapper_core.mushroom_map_model_runtime.'
            with patch('rainmapper_core.mushroom_map_weather.datetime') as clock, \
                 patch.object(r,'_refresh'),patch.object(r.weather,'_refresh'), \
                 patch.object(r.weather,'prepare_model_inputs',return_value=(SimpleNamespace(area_id='point'),[],[])) as prepare, \
                 patch(module+'comparison.resolve_selection',side_effect=selection), \
                 patch(module+'comparison._weather_requirements',return_value=(60,False)), \
                 patch(module+'comparison.compare_prepared',side_effect=compare) as infer:
                instant=datetime(2026,9,14,22,10,tzinfo=timezone.utc)
                clock.now.side_effect=lambda tz: instant.astimezone(tz)
                for day in (14,15):
                    prepare.reset_mock();infer.reset_mock()
                    result=r.predict({'start_date':f'2026-09-{day}','horizon_days':7,'point':{'lat':42,'lon':2}},geography)
                    self.assertEqual(result['species'][0]['probabilities'],[.6]*7)
                    self.assertEqual(result['species'][0]['reasons'],['calculated']*7)
                    self.assertEqual(infer.call_count,7)
                    self.assertEqual(prepare.call_count,1)
                    self.assertEqual(prepare.call_args.kwargs['end_day'],date(2026,9,day-1))
                for status in ('caution','outside_domain'):
                    applicability.update(status=status,outside_feature_count=8,checked_feature_count=160,
                        most_extreme=[{'feature':f'temp_min_c__lag_{i:03}', 'value':23.,
                            'training_min':-7.,'training_max':22.} for i in range(5)])
                    output=r.predict({'start_date':'2026-09-15','horizon_days':7,'point':{'lat':42,'lon':2}},geography)
                    row=output['species'][0]
                    self.assertEqual(row['applicability'],[0]*7)
                    self.assertEqual(len(row['applicability_details']),1)
                    self.assertEqual(len(row['applicability_details'][0]['examples']),3)
                    self.assertEqual(row['reasons'],['calculated' if status=='caution' else 'outside_domain']*7)
                    self.assertEqual(row['probabilities'],[.6 if status=='caution' else None]*7)
                for day,zone in (('2026-09-16','Europe/Madrid'),('2026-09-15','UTC')):
                    prepare.reset_mock();infer.reset_mock()
                    future=r.predict({'start_date':day,'calendar_timezone':zone,'horizon_days':7,'point':{'lat':42,'lon':2}},geography)
                    self.assertEqual(future['species'][0]['probabilities'],[None]*7)
                    prepare.assert_not_called();infer.assert_not_called()

    def test_geography_filters_before_preparing_hydric_model_inputs(self):
        path=Path(__file__).resolve().parents[1]/'scripts/prediction-map-local-geography.py'
        spec=importlib.util.spec_from_file_location('point_geography_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        terrain=Mock();terrain.lookup.return_value={'status':'available'}
        terrain.soil_water_context.return_value={'context_hash':'test'}
        ecology=Mock()
        events=[]
        def evaluate(*args):
            events.append('ecology')
            return {'status':'available','species':[{'species_id':'one','status':state,'daily_season_phases':['main']*7}]}
        ecology.evaluate.side_effect=evaluate
        terrain.soil_water_context.side_effect=lambda *args: events.append('model_inputs') or {'context_hash':'test'}
        argv=[str(path),'--terrain-index','unused','--soil-root','unused','--dem-root','unused',
              '--regional-root','unused','--profiles','unused','--ecology-catalogs','unused','--gis-mappings','unused']
        for state,requested,expected in [('incompatible',[],False),('unknown',[],False),
                                          ('compatible',['other'],False),('compatible',[],True)]:
            events.clear();terrain.soil_water_context.reset_mock()
            request={'id':1,'lat':42,'lon':2,'start_date':'2026-09-14','model_inputs':True,'species_ids':requested}
            output=io.StringIO()
            with patch.object(module,'TerrainReader',return_value=terrain), \
                 patch.object(module,'EcologyReader',return_value=ecology), \
                 patch('sys.argv',argv),patch('sys.stdin',io.StringIO(json.dumps(request)+'\n')), \
                 patch('sys.stdout',output):
                module.main()
            self.assertEqual('model_soil_water' in json.loads(output.getvalue()),expected)
            self.assertEqual(events,['ecology','model_inputs'] if expected else ['ecology'])

    def test_streaming_projection_keeps_species_and_discards_large_area_rows(self):
        from rainmapper_core import mushroom_ml_quality_catalog as q
        data={'kind':q.KIND,'schema_version':q.SCHEMA_VERSION,
              'selection_prediction_days':list(range(1,8)),
              'selection_split_id':q.mushroom_ml_reliability_audit.OFFICIAL_SELECTION_SPLIT_ID,
              'entries':[{'literal':'text } ] , \\" ä'*8000}],
              'species_selections':[], 'species_area_selections':[{'padding':'x'*12000}]*50}
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'q.json.gz';p.write_bytes(gzip.compress(json.dumps(data).encode()))
            result=projected_quality(p,hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(result['entries'],data['entries'])
            self.assertEqual(result['species_area_selections'],[])
            with self.assertRaisesRegex(ValueError,'digest'): projected_quality(p,'0'*64)

    def test_single_oversized_element_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'q.json.gz';p.write_bytes(gzip.compress(json.dumps({'discarded':[{'s':'x'*600000}]}).encode()))
            with self.assertRaisesRegex(ValueError,'quality_read_limit'):
                projected_quality(p,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_verified_point_prefix_does_not_decompress_large_area_tail(self):
        from rainmapper_core import mushroom_ml_quality_catalog as q
        data={'kind':q.KIND,'schema_version':q.SCHEMA_VERSION,
              'snapshot_id':'test-snapshot','split_id':'fruiting_groups_7d',
              'selection_schema_version':'1.2','selection_status':'complete',
              'selection_id':'test-selection','selection_prediction_days':list(range(1,8)),
              'selection_split_id':q.mushroom_ml_reliability_audit.OFFICIAL_SELECTION_SPLIT_ID,
              'entries':[{'literal':'point evidence'}],'species_selections':[]}
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'q.json.gz'
            # More than the reader's 64 MiB scan budget, but no large allocation.
            with gzip.open(p,'wt') as stream:
                stream.write(json.dumps(data)[:-1]+',"species_area_selections":[')
                row=json.dumps({'unused_area_evidence':'x'*16384})
                for index in range(4200):
                    stream.write((',' if index else '')+row)
                stream.write(']}')
            opener=gzip.open
            read_sizes=[]
            def bounded_open(*args,**kwargs):
                stream=opener(*args,**kwargs)
                original=stream.read
                def read(size=-1):
                    value=original(size)
                    read_sizes.append(len(value))
                    self.assertLessEqual(sum(read_sizes),65536)
                    return value
                stream.read=read
                return stream
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            with patch('rainmapper_core.mushroom_map_model_runtime.gzip.open',side_effect=bounded_open):
                result=projected_quality(p,digest)
            self.assertEqual(result['entries'],data['entries'])
            self.assertEqual(result['species_selections'],data['species_selections'])
            self.assertEqual(result['species_area_selections'],[])
            # Integrity still covers bytes that the projection never decompresses.
            p.write_bytes(p.read_bytes()+b'changed-tail')
            with self.assertRaisesRegex(ValueError,'quality_digest_mismatch'):
                projected_quality(p,digest)

    def test_missing_species_does_not_borrow_a_model(self):
        with tempfile.TemporaryDirectory() as folder:
            profiles=Path(folder)/'p.json';profiles.write_text('{"species_profiles":[]}')
            r=PointModelRuntime(registry_path='unused',models_root=folder,profiles_path=profiles,data_root=folder,stations_file='unused')
            r.resolutions={};r.revision='test';r.manifest={'batch_id':'test'}
            r.weather._refresh=lambda: None;r.weather.generation=type('G',(),{'generation_id':'test'})()
            geography={'ecology':{'status':'available','species':[{'species_id':'new_species','status':'compatible','daily_statuses':['compatible']*7,'daily_season_phases':['main']*7}]}}
            with patch.object(r,'_refresh'):
                with patch.object(r.weather,'_refresh',side_effect=AssertionError('no model needs no weather')):
                    out=r.predict({'start_date':'2026-09-13','horizon_days':7,'point':{'lat':42,'lon':2}},geography)
            self.assertEqual(out['species'][0]['probabilities'],[None]*7)
            self.assertEqual(out['species'][0]['status'],'no_model')

    def test_empty_rejected_unknown_or_unrequested_never_prepare_models(self):
        runtime=PointModelRuntime(registry_path='unused',models_root='/tmp',profiles_path='unused',
                                  data_root='/tmp',stations_file='unused')
        for state, requested in [('incompatible',[]),('unknown',[]),('compatible',['other'])]:
            # Even an obsolete daily projection cannot override territorial status.
            ecology={'status':'available','species':[{'species_id':'test','status':state,
                                                      'daily_statuses':['compatible']*7,'daily_season_phases':['main']*7}]}
            with patch.object(runtime,'_refresh') as refresh, patch.object(runtime.weather,'_refresh') as weather:
                out=runtime.predict({'start_date':'2026-09-14','horizon_days':7,'species_ids':requested},
                                    {'ecology':ecology})
            refresh.assert_not_called(); weather.assert_not_called()
            self.assertEqual(out['species'],[])

    def test_out_of_season_and_unknown_season_skip_models_and_weather(self):
        runtime=PointModelRuntime(registry_path='unused',models_root='/tmp',profiles_path='unused',
                                  data_root='/tmp',stations_file='unused')
        for phase in ('out_of_season','unknown'):
            ecology={'status':'available','species':[{'species_id':'test','status':'compatible',
                'daily_statuses':['compatible']*7,'daily_season_phases':[phase]*7}]}
            with patch.object(runtime,'_refresh') as models,patch.object(runtime.weather,'_refresh') as weather:
                out=runtime.predict({'start_date':'2026-09-14','horizon_days':7},{'ecology':ecology})
            models.assert_not_called();weather.assert_not_called()
            self.assertEqual(out['species'],[])

    def test_week_crossing_season_boundary_never_infers_outside_days(self):
        from tests.test_mushroom_map_prediction import PointWeekTests
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profiles.json'
            path.write_text(json.dumps({'species_profiles':[{'species_id':'test',
                'phenology':{'main_months':[9],'secondary_months':[]}}]}))
            r=PointModelRuntime(registry_path='unused',models_root=folder,profiles_path=path,
                                data_root=folder,stations_file='unused')
            r.resolutions={'test':PointWeekTests().resolutions()}
            r.revision='test';r.manifest={'batch_id':'test'};r.registry={};r.catalog_profiles={}
            r.installed=['biology_v6'];r.quality={};r.weather.generation=SimpleNamespace(generation_id='test')
            phases=['out_of_season']*3+['main']*4
            geography={'ecology':{'status':'available','species':[{'species_id':'test','status':'compatible',
                'daily_statuses':['compatible']*7,'daily_season_phases':phases}]}}
            def selection(*args,**kwargs):
                return SimpleNamespace(horizon_days=args[2]['horizon_days'],reference=args[2])
            def compare(*args,**kwargs):
                self.assertEqual(kwargs['target_date'].month,9)
                return {'members':[{'model_ref':ref.reference,'available':True,
                    'prediction':{'probability':.6,'applicability':{'status':'within_observed_range'}},
                    'evaluation':{'evidence':'better_than_prevalence','brier_score':.1,
                     'prevalence_brier_score':.25,'brier_delta_vs_prevalence':.15,'roc_auc':.8}}
                    for ref in args[2]]}
            module='rainmapper_core.mushroom_map_model_runtime.'
            with patch.object(r,'_refresh'),patch.object(r.weather,'_refresh'), \
                 patch.object(r.weather,'prepare_model_inputs',return_value=(SimpleNamespace(area_id='point'),[],[])), \
                 patch(module+'comparison.resolve_selection',side_effect=selection), \
                 patch(module+'comparison._weather_requirements',return_value=(60,False)), \
                 patch(module+'comparison.compare_prepared',side_effect=compare) as infer:
                result=r.predict({'start_date':'2025-08-29','horizon_days':7,'point':{'lat':42,'lon':2}},geography)
            self.assertGreater(infer.call_count,0)
            row=result['species'][0]
            self.assertEqual(row['probabilities'][:3],[None]*3)
            self.assertEqual(row['reasons'][:3],['out_of_season']*3)
            self.assertTrue(all(p is not None for p in row['probabilities'][3:]))

    def test_only_territorial_candidates_invoke_models_and_pass_original_phenology(self):
        with tempfile.TemporaryDirectory() as folder:
            phenology={'main_months':[9], 'secondary_months':[10], 'season_pattern_ids':['original']}
            p=Path(folder)/'profiles.json'
            p.write_text(json.dumps({'species_profiles':[{'species_id':'allowed','phenology':phenology}]}))
            r=PointModelRuntime(registry_path='unused',models_root=folder,profiles_path=p,
                                data_root=folder,stations_file='unused')
            r.resolutions={sid:{i:{} for i in range(1,8)} for sid in ('allowed','rejected','unknown')}
            r.revision='test';r.manifest={'batch_id':'test'};r.registry={};r.catalog_profiles={}
            r.installed=['test'];r.quality={}
            r.weather.generation=SimpleNamespace(generation_id='test')
            geography={'ecology':{'status':'available','species':[
                {'species_id':sid,'status':state,'daily_statuses':[state]*7,'daily_season_phases':['main']*7}
                for sid,state in [('rejected','incompatible'),('unknown','unknown'),
                                  ('no_model','compatible'),('allowed','compatible')]]}}
            def week(**kwargs):
                self.assertEqual(kwargs['species_id'],'allowed')
                self.assertEqual(kwargs['phenology'],phenology)
                from rainmapper_core.mushroom_ml_predictor import season_phase_for_months
                day=kwargs['issue_date']
                self.assertEqual(kwargs['season_phase'](day),season_phase_for_months(day,[9],[10]))
                kwargs['materialize'](target_date=day,selections=[{}])
                return {'days':[{'operational_comparison':{'selected_winners':[{'probability':v}]},
                                  'reliability_selection':{'runtime_selection_status':'winner' if n != 3 else 'abstain',
                                      'candidate':{'version_id':'altitude_v2' if n==0 else 'biology_v6_windowed_smooth_hierarchical',
                                                   'estimator_id':'extra_trees_restricted_v1' if n==0 else 'smooth_partial_pooling_logistic_v1'}}}
                                for n,v in enumerate((0,.7,None,None,None,None,None))]}
            module='rainmapper_core.mushroom_map_model_runtime.'
            with patch.object(r,'_refresh'), patch.object(r.weather,'_refresh'), \
                 patch.object(r.weather,'prepare_model_inputs',return_value=(SimpleNamespace(area_id='point'),[],[])) as prepare, \
                 patch(module+'resolve_species_week',side_effect=week) as resolve, \
                 patch(module+'comparison.resolve_selection',return_value=SimpleNamespace(horizon_days=1)) as selection, \
                 patch(module+'comparison._weather_requirements',return_value=(60,False)), \
                 patch(module+'comparison.compare_prepared',return_value={}) as inference:
                for day in ('2025-09-13','2025-10-29'):
                    out=r.predict({'start_date':day,'horizon_days':7,'point':{'lat':42,'lon':2}},geography)
                    self.assertEqual([x['species_id'] for x in out['species']],['no_model','allowed'])
                    self.assertEqual(out['species'][0]['probabilities'],[None]*7)
                    self.assertEqual(out['species'][1]['probabilities'][:3],[0,.7,None])
                    self.assertEqual(out['species'][1]['model_labels'],['ET–V2','Smooth Partial–V6w'])
                    self.assertEqual(out['species'][1]['models'][:4],[0,1,1,None])
                    self.assertNotIn('models',out['species'][0])
                self.assertEqual(inference.call_count,2)
                self.assertEqual(prepare.call_count,2)
                self.assertEqual(resolve.call_count,2)
                self.assertEqual([c.kwargs['species_id'] for c in selection.call_args_list],['allowed']*2)


class ResultTests(unittest.TestCase):
    def setUp(self):
        self.request=dict(contract=contract.CONTRACT_ID,request_id='model_test_0001',point={'lat':42,'lon':2},
            start_date='2026-09-13',horizon_days=7,history_days=60,species_ids=[],execution='local')
        self.result=contract.demo_result(self.request)
        self.result.update(data_mode='prediction',execution={'mode':'local'},
            provenance={'engine':'existing_python_predictor','scientifically_validated':False},
            ecology={'status':'available','species':[{'species_id':'one','status':'compatible','daily_statuses':['compatible']*7,'daily_season_phases':['main']*7}]},
            species=[{'species_id':'one','status':'available','probabilities':[0,.9,None,None,None,None,None],
                'reasons':['calculated','calculated','model_abstained','model_abstained','model_abstained','model_abstained','model_abstained']}])

    def test_model_labels_are_bounded_and_never_claim_a_missing_model(self):
        row=self.result['species'][0]
        row.update(models=[0,1,1,None,None,None,None],model_labels=['ET–V2','Smooth Partial–V6w'])
        contract.validate_result(self.result,self.request)
        for defect in ('reference','length','label','no_model','unavailable'):
            result=copy.deepcopy(self.result); r=result['species'][0]
            if defect=='reference': r['models'][0]=2
            if defect=='length': r['models'].pop()
            if defect=='label': r['model_labels'][0]='X'*97
            if defect=='no_model': r['status']='no_model'
            if defect=='unavailable': r['reasons'][0]='model_unavailable'
            with self.subTest(defect=defect), self.assertRaisesRegex(ValueError,'invalid_result_models'):
                contract.validate_result(result,self.request)

    def test_model_details_are_optional_bounded_and_aligned(self):
        row=self.result['species'][0]
        row.update(models=[0]*7, model_labels=['ET–V2'], model_details=[{
            'estimator':'extra_trees_restricted_v1', 'inputs':['rain'], 'window_days':60}])
        contract.validate_result(self.result,self.request)
        for invalid in ([], [None, None], [{'inputs':['rain']}],
                        [{'estimator':{}, 'inputs':[], 'window_days':60}]):
            result=copy.deepcopy(self.result); result['species'][0]['model_details']=invalid
            with self.assertRaisesRegex(ValueError,'invalid_result_model_details'):
                contract.validate_result(result,self.request)

    def test_real_result_preserves_zero_and_abstention(self):
        contract.validate_result(self.result,self.request)

    def test_executor_accepts_real_species_filter_without_demo_ids(self):
        from unittest.mock import Mock
        from rainmapper_core.mushroom_map_execution import PointExecutor
        geography=Mock(); geography.call.return_value={'ecology':self.result['ecology']}
        weather=Mock(); weather.call.return_value={}
        model=Mock(); model.call.return_value={k:self.result[k] for k in ('species','provenance','data_mode')}
        config={key:'unused' for key in ('terrain_index','soil_root','dem_root','regional_root',
            'models_root','model_registry','profiles','weather_data','weather_stations')}
        with patch('rainmapper_core.mushroom_map_execution.ResidentReader',side_effect=[model,geography,weather]):
            executor=PointExecutor(config,Path('/tmp'))
            req={**self.request,'species_ids':['one']}
            result=executor.execute(req)
        self.assertEqual(result['species'],self.result['species'])
        self.assertTrue(geography.call.call_args.args[0]['model_inputs'])

    def test_executor_propagates_one_calendar_to_both_readers_at_midnight(self):
        from rainmapper_core.mushroom_map_execution import PointExecutor
        instant=datetime(2026,9,14,22,10,tzinfo=timezone.utc)
        for calendar,selected,expected_end in (('Europe/Madrid',None,'2026-09-14'),
                                              ('UTC',None,'2026-09-13'),('UTC','Europe/Madrid','2026-09-14')):
            model=Mock();model.call.return_value={}
            geography=Mock();geography.call.return_value={'ecology':{'status':'available','species':[]}}
            weather=Mock();weather.call.return_value={}
            config={key:'unused' for key in ('terrain_index','soil_root','dem_root','regional_root',
                'models_root','model_registry','profiles','weather_data','weather_stations')}
            config['calendar_timezone']=calendar
            with self.subTest(calendar=calendar), \
                 patch('rainmapper_core.mushroom_map_weather.datetime') as clock, \
                 patch('rainmapper_core.mushroom_map_execution.ResidentReader',side_effect=[model,geography,weather]) as readers:
                clock.now.side_effect=lambda tz: instant.astimezone(tz)
                executor=PointExecutor(config,Path('/tmp'))
                req={**self.request,'start_date':'2026-09-15'}
                if selected: req['calendar_timezone']=selected
                result=executor.execute(req)
                for i in (0,2):
                    args=readers.call_args_list[i].args[2]
                    self.assertEqual(args[args.index('--calendar-timezone')+1],calendar)
                self.assertEqual(weather.call.call_args.args[0]['end_day'],expected_end)
                self.assertEqual(weather.call.call_args.args[0]['calendar_timezone'],selected or calendar)
                self.assertEqual(result['calendar_timezone'],selected or calendar)

    def test_broker_accepts_prediction_mode_and_preserves_nulls(self):
        from rainmapper_core.mushroom_map_queries import QueryBroker
        broker=QueryBroker(); broker.local_ready=True
        receipt=broker.submit('owner',self.request)
        with broker.lock: job=broker._claim('local','_local')
        self.assertTrue(broker.finish('_local',{**job,'result':self.result})['accepted'])
        status,result=broker.status('owner',receipt['query_id'])
        self.assertEqual(status,200)
        self.assertEqual(result['species'],self.result['species'])

    def test_executor_empty_territory_skips_model_process_but_keeps_weather_display(self):
        from rainmapper_core.mushroom_map_execution import PointExecutor
        geography=Mock(); geography.call.return_value={'ecology':{'status':'available','species':[]}}
        weather=Mock();weather.call.return_value={'weather':{'status':'available'}}
        model=Mock()
        config={key:'unused' for key in ('terrain_index','soil_root','dem_root','regional_root',
            'models_root','model_registry','profiles','weather_data','weather_stations')}
        with patch('rainmapper_core.mushroom_map_execution.ResidentReader',side_effect=[model,geography,weather]):
            result=PointExecutor(config,Path('/tmp')).execute(self.request)
        model.call.assert_not_called();weather.call.assert_called_once()
        self.assertEqual(result['species'],[])
        self.assertEqual(result['weather']['status'],'available')

    def test_compact_applicability_contract_rejects_unbounded_or_invalid_details(self):
        valid=copy.deepcopy(self.result)
        valid['species'][0].update(applicability=[0]*7,applicability_details=[
            {'status':'caution','outside':8,'total':160,'examples':[
                {'feature':'temp_min_c__lag_009','value':22.83,'training_min':-7.63,'training_max':22.73}]}])
        contract.validate_result(valid,self.request)
        for defect in ('reference','length','status','count','examples','nan','name'):
            r=copy.deepcopy(valid);row=r['species'][0];detail=row['applicability_details'][0]
            if defect=='reference':row['applicability'][0]=1
            if defect=='length':row['applicability'].pop()
            if defect=='status':detail['status']='unknown'
            if defect=='count':detail['outside']=161
            if defect=='examples':detail['examples']*=4
            if defect=='nan':detail['examples'][0]['value']=float('nan')
            if defect=='name':detail['examples'][0]['feature']='x'*129
            with self.subTest(defect=defect), self.assertRaisesRegex(ValueError,'invalid_result_applicability'):
                contract.validate_result(r,self.request)

    def test_rejects_cross_species_incompatible_and_invalid_probability(self):
        for mutation in ('species','ecology','nan','bool','no_model','duplicate','point','season','missing_season'):
            r=copy.deepcopy(self.result)
            if mutation=='species': r['species'][0]['species_id']='another'
            if mutation=='ecology': r['ecology']['species'][0]['daily_statuses'][0]='unknown'
            if mutation=='season': r['ecology']['species'][0]['daily_season_phases'][0]='out_of_season'
            if mutation=='missing_season': r['ecology']['species'][0].pop('daily_season_phases')
            if mutation=='nan': r['species'][0]['probabilities'][0]=float('nan')
            if mutation=='bool': r['species'][0]['probabilities'][0]=True
            if mutation=='no_model': r['species'][0]['status']='no_model'
            if mutation=='duplicate': r['species'].append(copy.deepcopy(r['species'][0]))
            if mutation=='point': r['point']['lat']=43
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                contract.validate_result(r,self.request)
