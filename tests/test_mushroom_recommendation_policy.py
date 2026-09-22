"""Reversible serving policy; no fitting or operational jobs."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from rainmapper_core import mushroom_recommendation_policy as policy
from rainmapper_core import mushroom_ml_prediction_policy as serving
from rainmapper_core import mushroom_ml_policy_store as store
from rainmapper_core import mushroom_ml_version_registry as versions
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_predictor_runtime as runtime
import test_mushroom_map_prediction as point_tests

ROOT = Path(__file__).resolve().parents[1]

def member(name, p=.7):
    return {'model_ref': {'version_id':'biology_v6','profile_id':name,'estimator_id':'test',
        'temporal_contract_id':'lag_event_biology_v6','horizon_days':1}, 'available':True,
        'prediction':{'probability':p,'applicability':{'status':'within_observed_range'}},
        'evaluation':{'evidence':'better_than_prevalence','brier_score':.1,
                      'prevalence_brier_score':.25,'brier_delta_vs_prevalence':.15,'roc_auc':.8}}

class RecommendationTests(unittest.TestCase):
    def test_modes_missing_suspension_and_unchanged_iff(self):
        members=[member('winner',.99),member('second'),member('third')]
        original={'selected_winners':[{'probability':.99}],
                  'interpretation':{'verdict':'favorable','reference_range':[.99,.99]}}
        for mode in policy.MODES:
            for case in ('agree','disagree','missing','suspended'):
                rows=copy.deepcopy(members)
                if case=='disagree': rows[2]['prediction']['probability']=.59
                if case=='missing': rows.pop()
                if case=='suspended': rows[1].update(available=False,reason='model_suspended')
                resolution={}
                plan=policy.plan([{'candidate':m['model_ref']} for m in members],members[0]['model_ref'],
                    {'mode':mode,'rule_version':'consensus_v1'},species_id='amanita_caesarea')
                if plan: resolution['recommendation_plan']=plan
                result=policy.apply(copy.deepcopy(original),resolution,rows,comparison._operational_gate_failures)
                self.assertEqual(result['selected_winners'],original['selected_winners'])
                self.assertEqual(result['interpretation']['reference_range'],[.99,.99])
                self.assertEqual(result['interpretation']['verdict'],
                    'abstain' if mode=='prudent' and case!='agree' else 'favorable')
                if mode=='legacy': self.assertEqual(result,original)
                else:
                    d=result['recommendation_decision']
                    self.assertEqual(d['status'],{'agree':'agreed','disagree':'disagreed','missing':'unavailable','suspended':'unavailable'}[case])
                    # Cached result has only the winner, yet retains the sealed comparison.
                    resolution['recommendation_decision']=d
                    cached=policy.apply(copy.deepcopy(original),resolution,[rows[0]],comparison._operational_gate_failures)
                    self.assertEqual(cached,result)
                    self.assertLess(len(json.dumps(d)),1600)

    def test_fixed_next_families_and_species_scope(self):
        refs=[member(str(i))['model_ref'] for i in range(5)]
        entries=[{'candidate':r} for r in refs]
        config={'mode':'shadow','rule_version':'consensus_v1'}
        p=policy.plan(entries,refs[2],config,species_id='boletus_edulis')
        self.assertEqual(p['alternatives'],refs[3:])
        for sid in ('lactarius_deliciosus','boletus_aereus'):
            self.assertIsNone(policy.plan(entries,refs[0],config,species_id=sid))
        self.assertIsNone(policy.plan(entries,refs[0],policy.validate(),species_id='boletus_edulis'))

    def test_data_counts_do_not_count_unexecuted_suspended_or_domain_rejections(self):
        rows=[member(str(i)) for i in range(5)]
        entries=[{'candidate':m['model_ref']} for m in rows]
        rows[0].update(available=False,reason='runtime_feature_gates_failed',quality={'inference_exclusion_reasons':[
            {'code':'rain_coverage_below_threshold'},{'code':'v3_physical_soil_state_unavailable'}]})
        rows[1].update(available=False,reason='model_suspended')
        rows[2]['prediction']['applicability']['status']='outside_domain'
        a=policy.availability(entries+entries,rows[:4],policy.family(rows[3]['model_ref']))
        self.assertEqual((a['candidate_family_count'],a['evaluated_family_count'],a['data_rejected_count'],a['better_ranked_data_rejected_count']),(5,4,1,1))
        self.assertEqual(a['reason_counts']['rain_history'],1)
        self.assertEqual(a['reason_counts']['soil_water'],1)

    def test_policy_persistence_invalidates_serving_not_training_and_requires_worker_support(self):
        base=versions.load_registry(ROOT/'mushroom-data/mushroom_ml_version_registry.json')
        changed={**base,policy.FIELD:{'mode':'shadow','rule_version':'consensus_v1'}}
        self.assertEqual(versions.training_contract_revision(base),versions.training_contract_revision(changed))
        self.assertNotEqual(serving.revision(base),serving.revision(changed))
        self.assertFalse(serving.worker_compatible(changed,[]))
        self.assertTrue(serving.worker_compatible(changed,[policy.CAPABILITY,serving.CAPABILITY]))
        self.assertEqual(versions.merge_packaged_definitions(base,changed)[policy.FIELD],changed[policy.FIELD])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'registry.json';versions.save_registry(path,base)
            store.save(path,changed,expected_revision=serving.revision(base))
            self.assertEqual(versions.load_registry(path),changed)
            exported=store.encode(store.document(changed))
            self.assertEqual(store.import_rules(exported,base,set(),expected_revision=serving.revision(base)),changed)
            versions.save_registry(path,base) # promotion must retain user's setting
            self.assertEqual(versions.load_registry(path)[policy.FIELD],changed[policy.FIELD])
            snapshot=runtime._runtime_registry_snapshot(changed,source_path=path,explicit_source=True)
            a=snapshot.read_bytes()
            runtime._runtime_registry_snapshot(base,source_path=path,explicit_source=True)
            self.assertNotEqual(a,snapshot.read_bytes())
            with self.assertRaisesRegex(ValueError,'Refresh'):
                store.save(path,base,expected_revision=serving.revision(base))

    def test_settings_form_roundtrip_and_translated_warning(self):
        from test_web_server_auth import load_web_server_module
        web=load_web_server_module();handler=object.__new__(web.RainmapperHandler)
        base=versions.load_registry(ROOT/'mushroom-data/mushroom_ml_version_registry.json')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'registry.json';versions.save_registry(path,base)
            form={k:[v] for k,v in {'worker_action':'set_recommendation_policy','recommendation_mode':'shadow',
                'policy_revision':serving.revision(base)}.items()}
            with mock.patch.object(web.mushroom_paths,'mushroom_ml_version_registry_path',return_value=path),mock.patch.object(web,'set_mushroom_workers_flash') as flash:
                handler.handle_mushroom_workers_post(form)
                changed=versions.load_registry(path)
                self.assertEqual(changed[policy.FIELD]['mode'],'shadow')
                page=web.mushroom_model_settings_ui.render(changed,{'species_profiles':[]})
                self.assertIn('value="shadow" selected',page)
                self.assertNotIn('missing label',page)
                handler.handle_mushroom_workers_post(form)
                self.assertTrue(flash.call_args.kwargs['error'])
                from mushroom_predictor_ui import _selection_reservations_html
                rendered=_selection_reservations_html({'data_availability':{'data_rejected_count':9,'evaluated_family_count':33,'better_ranked_data_rejected_count':9}})
                self.assertIn('9',rendered);self.assertIn('33',rendered);self.assertNotIn('missing label',rendered)

    def test_lazy_week_two_extra_fixed_families_and_scope(self):
        fixture=point_tests.PointWeekTests();rows=fixture.resolutions()
        for day,r in rows.items():
            extra=copy.deepcopy(r['candidate_chain'][1]);extra['candidate']['estimator_id']='third'
            r['candidate_chain'].append(extra)
        from rainmapper_core.mushroom_map_prediction import resolve_species_week
        calc=fixture.materializer()
        result=resolve_species_week(species_id='amanita_caesarea',point_id='p',issue_date=fixture.issue,
            resolutions_by_day=rows,installed_version_ids=['biology_v6'],materialize=calc,
            season_phase=lambda _: 'in_season',phenology={},lazy_families=True,
            recommendation_policy={'mode':'shadow','rule_version':'consensus_v1'})
        self.assertEqual(calc.call_count,14) # 7 winner calls and 7 batched pairs
        self.assertEqual(sum(len(c.kwargs['selections']) for c in calc.call_args_list),21)
        for row in result['days']:
            decision=row['operational_comparison']['recommendation_decision']
            self.assertEqual(decision['status'],'agreed')
            self.assertEqual([r['model_ref']['estimator_id'] for r in decision['comparators']],['coverage_first','third'])

    def test_direct_service_views_use_same_weekly_decision(self):
        from datetime import timedelta
        import test_mushroom_predictor_service as service_tests
        from rainmapper_core.mushroom_predictor_service import PredictorService
        from rainmapper_core.mushroom_predictor_precompute import weekly_aggregate_resolution_index
        fixture=point_tests.PointWeekTests();rows=fixture.resolutions();sid='boletus_edulis'
        for row in rows.values():
            extra=copy.deepcopy(row['candidate_chain'][1]);extra['candidate']['estimator_id']='third'
            row['candidate_chain'].append(extra)
        indexed=weekly_aggregate_resolution_index({(sid,'area_one',d):r for d,r in rows.items()},
            issue_date=fixture.issue,installed_version_ids=['biology_v6'])
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            svc=PredictorService(models_dir=root,weather_data_dir=root,features_artifact_path=root/'features',
                known_sites_path=root/'sites',runtime_fingerprint='sha256:test')
            predictor=mock.Mock();predictor.season_phase.return_value='in_season'
            predictor.areas_with_species_observations.return_value=['area_one']
            predictor.week_window.return_value=[service_tests.prediction(sid,'area_one',fixture.issue+timedelta(days=i)) for i in range(7)]
            svc.predictor=mock.Mock(return_value=predictor);svc.species_phenology=mock.Mock(return_value={})
            svc.prewarm_multiversion_week=mock.Mock();svc.model_catalog=mock.Mock(return_value={})
            def infer(**kw):
                members=[]
                for ref in kw['selections']:
                    m=member('dummy', .5 if ref['estimator_id']=='third' else .8)
                    m['model_ref']=dict(ref);members.append(m)
                return {'available':True,'members':members}
            svc.multiversion_compare=mock.Mock(side_effect=infer)
            config={'mode':'prudent','rule_version':'consensus_v1'}
            context={'operational_resolution_index':indexed,
                'comparison_cache':{'service_registry':{policy.FIELD:config}},'disable_response_cache':True}
            request=service_tests.PredictorServiceTests().request(species_id=sid,trained_species_ids=[sid],
                target_date=fixture.issue.isoformat(),issue_date=fixture.issue.isoformat(),multiversion_selection=[])
            # First request is the all-area view, not a precomputed detailed query.
            recommended=svc.execute({**request,'view':'recommender','area_id':''},shared_context=context)
            day=fixture.issue.isoformat()
            first=recommended['data']['species'][sid]['model_comparisons']['area_one'][day]['operational_comparison']
            self.assertEqual(first['interpretation']['verdict'],'abstain')
            detailed=svc.execute(request,shared_context=context)
            second=detailed['data']['species'][sid]['model_comparisons']['area_one'][day]
            self.assertEqual(first['recommendation_decision'],second['recommendation_decision'])
            self.assertEqual(first['selected_winners'],second['selected_winners'])
            self.assertEqual(first['data_availability'], second['data_availability'])
            self.assertEqual(second['data_availability']['evaluated_family_count'], 3)

    def test_compact_map_summary_validates_and_omits_comparator_payloads(self):
        decision={'mode':'prudent','rule_version':'consensus_v1','status':'disagreed',
            'legacy_recommend':True,'prudent_recommend':False,'comparators':[{'model_ref':{'anything':'private'}}]}
        summary=policy.map_notice({'recommendation_decision':decision})
        self.assertTrue(policy.valid_map_notice(summary))
        self.assertNotIn('private',json.dumps(summary))
        self.assertLess(len(json.dumps(summary)),300)
        ref={'version_id':'biology_v3','profile_id':'core','estimator_id':'logistic_regression_reduced_v1',
             'private_features':[1]*10000}
        decision['comparators']=[{'model_ref':ref,'probability':.72,'status':'favorable'},
                                {'model_ref':ref,'probability':.55,'status':'not_favorable'}]
        summary=policy.map_notice({'recommendation_decision':decision})
        self.assertTrue(policy.valid_map_notice(summary))
        self.assertEqual(summary['recommendation_decision']['comparators'][0]['label'],'LR–V3 · core')
        self.assertEqual(summary['recommendation_decision']['comparators'][1]['probability'],.55)
        self.assertNotIn('private_features',json.dumps(summary))
        self.assertLess(len(json.dumps(summary)),600)
        from test_web_server_auth import load_web_server_module
        web=load_web_server_module()
        rendered=web.mushroom_predictor_ui._selection_reservations_html({'recommendation_decision':decision})
        self.assertIn('LR–V3 · core: IFF:72/100', rendered)
        self.assertIn('IFF:55/100', rendered)
        self.assertIn('<details><summary>', rendered)
        invalid=copy.deepcopy(summary)
        invalid['recommendation_decision']['comparators']*=2
        self.assertFalse(policy.valid_map_notice(invalid))
        summary['recommendation_decision']['prudent_recommend']=True
        self.assertFalse(policy.valid_map_notice(summary))

    def test_decision_survives_sqlite_composition_without_alternative_features(self):
        import test_mushroom_predictor_precompute as precompute_tests
        from rainmapper_core.mushroom_predictor_precompute import build_weekly_artifact, lookup_active_artifact
        owner=precompute_tests.WeeklyPrecomputeBatchTests()
        owner.setUp()
        config={'mode':'prudent','rule_version':'consensus_v1'}
        class Service(owner.FakeService):
            def execute(self, request, **kw):
                response=super().execute(request,**kw)
                species=response['data']['species']['boletus_edulis']
                for comparisons in (species.get('multiversion_comparisons',{}),
                                    species.get('model_comparisons',{}).get('montseny',{})):
                    for day,payload in comparisons.items():
                        dayno=(__import__('datetime').date.fromisoformat(day)-owner.issue_date).days+1
                        resolution=copy.deepcopy(kw['shared_context']['operational_resolution_index'][('boletus_edulis','montseny',dayno)])
                        resolution['recommendation_plan']={**config,'alternatives':[]}
                        resolution['recommendation_decision']={**config,'status':'unavailable',
                            'legacy_recommend':True,'prudent_recommend':False,'comparators':[]}
                        payload['reliability_selection']=resolution
                        if 'operational_comparison' in payload:
                            payload['operational_comparison']['reliability_selection']=resolution
                        policy.apply(payload.get('operational_comparison',payload),resolution,[],comparison._operational_gate_failures)
                return response
        service=Service(owner)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.sqlite3'
            build_weekly_artifact(path,identity=owner.identity(),predictor_service=service,
                operational_selections=owner.sealed_selections())
            for view in ('query','week','recommender'):
                req=next(r for r in service.calls if r['view']==view and (view!='query' or r['area_id']))
                hit=lookup_active_artifact(path,runtime_fingerprint=owner.runtime,request=req)
                self.assertTrue(hit.hit,hit.reason)
                sp=hit.response['data']['species']['boletus_edulis']
                payloads=sp['multiversion_comparisons'] if view=='query' else sp['model_comparisons']['montseny']
                for payload in payloads.values():
                    op=payload.get('operational_comparison',payload)
                    self.assertEqual(op['recommendation_decision']['status'],'unavailable')
                    self.assertEqual(op['interpretation']['verdict'],'abstain')

if __name__=='__main__':unittest.main()
