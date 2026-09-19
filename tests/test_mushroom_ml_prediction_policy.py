from datetime import date
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from rainmapper_core import mushroom_ml_prediction_policy as policy
from rainmapper_core import mushroom_ml_version_registry as versions
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_predictor_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
KEY = 'altitude_v2/common_idw/hist_gradient_boosting_restricted_v1'
SPECIES = 'lactarius_deliciosus'


class PredictionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.registry = versions.load_registry(ROOT/'mushroom-data/mushroom_ml_version_registry.json')

    def change(self, registry, species=SPECIES, enabled=False, **kwargs):
        return policy.update(registry, model_key=KEY, species_id=species,
                             enabled=enabled, reason='Audit of rainfall sensitivity',
                             actor='test', expected_revision=kwargs.get('revision', policy.revision(registry)))

    def test_species_global_and_reactivation(self):
        ref = dict(zip(policy.IDENTITY, (*KEY.split('/'), SPECIES)))
        registry = self.change(self.registry)
        self.assertIsNotNone(policy.suspension(registry, ref))
        self.assertIsNone(policy.suspension(registry, {**ref, 'species_id':'boletus_edulis'}))
        registry = self.change(registry, species='*')
        registry = self.change(registry, enabled=True)
        self.assertIsNotNone(policy.suspension(registry, ref))
        registry = self.change(registry, species='*', enabled=True)
        self.assertIsNone(policy.suspension(registry, ref))
        self.assertEqual(registry, self.registry)

    def test_persists_seed_roundtrip_without_invalidating_training_contract(self):
        registry = self.change(self.registry)
        self.assertEqual(versions.training_contract_revision(registry), versions.training_contract_revision(self.registry))
        merged = versions.merge_packaged_definitions(self.registry, registry)
        self.assertEqual(merged[policy.FIELD], registry[policy.FIELD])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'registry.json'
            versions.save_registry(path, merged)
            self.assertEqual(versions.load_registry(path), registry)
            snapshot = runtime._runtime_registry_snapshot(registry, source_path=path, explicit_source=True)
            self.assertEqual(json.loads(snapshot.read_text())[policy.FIELD], registry[policy.FIELD])
            first = runtime._entry('data', 'registry.json', snapshot)
            runtime._runtime_registry_snapshot(self.registry, source_path=path, explicit_source=True)
            self.assertNotEqual(first['sha256'], runtime._entry('data', 'registry.json', snapshot)['sha256'])

    def test_stale_form_and_malformed_policy_fail_closed(self):
        changed = self.change(self.registry)
        with self.assertRaisesRegex(ValueError, 'Refresh'):
            self.change(changed, revision=policy.revision(self.registry))
        for alteration in ({'species_id': ''}, {'reason': ''}, {'estimator_id': ['bad']}):
            broken = copy.deepcopy(changed)
            broken[policy.FIELD][0].update(alteration)
            with self.assertRaises(ValueError): versions.validate_registry(broken)
        with self.assertRaises(ValueError):
            versions.validate_registry({**changed, policy.FIELD: changed[policy.FIELD]*513})

    def test_old_worker_cannot_execute_suspended_policy(self):
        self.assertTrue(policy.worker_compatible(self.registry, []))
        self.assertFalse(policy.worker_compatible(self.change(self.registry), []))
        self.assertTrue(policy.worker_compatible(self.change(self.registry), [policy.CAPABILITY]))

    def test_ui_post_roundtrip_and_stale_form_cannot_overwrite(self):
        from test_web_server_auth import load_web_server_module
        web = load_web_server_module()
        handler = object.__new__(web.RainmapperHandler)
        profiles = {'species_profiles':[{'species_id':SPECIES,'scientific_name':'Lactarius deliciosus'}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'registry.json'
            versions.save_registry(path, self.registry)
            store = mock.Mock()
            store.load.return_value = profiles
            form = {key:[value] for key,value in {
                'worker_action':'set_prediction_model_policy','model_key':KEY,
                'species_scope':SPECIES,'model_enabled':'false',
                'suspension_reason':'<audit>','policy_revision':policy.revision(self.registry)}.items()}
            with mock.patch.object(web.mushroom_paths,'mushroom_ml_version_registry_path',return_value=path), \
                 mock.patch.object(web,'default_store',return_value=store), \
                 mock.patch.object(web,'set_mushroom_workers_flash') as flash:
                handler.handle_mushroom_workers_post(form)
                suspended = versions.load_registry(path)
                self.assertEqual(len(suspended[policy.FIELD]),1)
                page = web.mushroom_model_settings_ui.render(suspended,profiles)
                self.assertIn('&lt;audit&gt;',page)
                self.assertNotIn('missing label:',page)
                self.assertIn('HGB',page)
                handler.handle_mushroom_workers_post(form)
                self.assertTrue(flash.call_args.kwargs['error'])
                self.assertEqual(versions.load_registry(path),suspended)
                form['policy_revision']=[policy.revision(suspended)]
                form['model_enabled']=['true']
                handler.handle_mushroom_workers_post(form)
                self.assertEqual(versions.load_registry(path),self.registry)

    def test_suspension_precedes_cached_inference_and_all_horizons(self):
        registry = self.change(self.registry)
        refs = [catalog.ModelRef(batch_id='batch',generation_id='generation',
            version_id='altitude_v2',temporal_contract_id='lag_event_v1',profile_id='common_idw',
            estimator_id=KEY.split('/')[-1],species_id=SPECIES,horizon_days=h) for h in range(1,8)]
        cache = {'prediction_result_cache':{('area', '2026-09-19', ref.key): {'probability':1.0} for ref in refs}}
        manifest={'batch_id':'batch','snapshot_id':'snapshot','artifacts':[]}
        with mock.patch.object(comparison.mushroom_ml_runtime_features, 'build_runtime_features') as build:
            result=comparison.compare_prepared(registry,manifest,refs,models_root=Path('/unused'),
                target_date=date(2026,9,19),area_id='area',area_context=None,
                area_series_by_horizon={},stations={},checked_manifest=manifest,comparison_cache=cache)
        build.assert_not_called()
        self.assertEqual(len(result['members']),7)
        for member in result['members']:
            self.assertFalse(member['available'])
            self.assertEqual(member['reason'],'model_suspended')
            self.assertNotIn('prediction',member)

    def test_sealed_chain_uses_next_admissible_model_or_abstains(self):
        def member(name):
            return {'model_ref':{'version_id':name,'profile_id':'profile','estimator_id':'estimator',
                    'temporal_contract_id':'lag_event_test','horizon_days':1},'available':True,
                    'prediction':{'probability':0.6,'applicability':{'status':'within_observed_range'}},
                    'evaluation':{'evidence':'better_than_prevalence','brier_score':0.1,
                                  'prevalence_brier_score':0.25,'brier_delta_vs_prevalence':0.15,'roc_auc':0.8}}
        primary, alternative=member('primary'),member('alternative')
        resolution={'selection_status':'winner','selection_scope':'species_fallback',
            'candidate':primary['model_ref'],'candidate_chain':[
                {'candidate':m['model_ref'],'evidence':{},'evidence_by_scope':{}}
                for m in (primary,alternative)]}
        primary.update(available=False, reason='model_suspended')
        for suspend_all in (False, True):
            if suspend_all: alternative.update(available=False, reason='model_suspended')
            result,active=comparison.build_reliability_selected_operational_comparison(
                [primary,alternative],resolution,season_phase='in_season')
            self.assertEqual(result['reliability_candidate_exclusions'][0]['reasons'],['model_suspended'])
            if suspend_all: self.assertEqual(active['runtime_selection_status'],'abstain')
            else: self.assertEqual(active['candidate']['version_id'],'alternative')
