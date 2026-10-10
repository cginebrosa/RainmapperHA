"""Full coordinator queue/receipt flow with isolated inputs and no real worker."""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tests.test_web_server_auth import load_web_server_module
from rainmapper_core import mushroom_competing_control as control
from rainmapper_core import mushroom_competing_evidence as evidence


class BackendTests(unittest.TestCase):
    def test_point_queries_never_request_historical_work_even_when_comparison_is_missing(self):
        import json
        ui = self.web.mushroom_prediction_map_ui
        broker = Mock()
        broker.submit.return_value = {'query_id':'synthetic-query'}
        handler = self.web.RainmapperHandler.__new__(self.web.RainmapperHandler)
        handler.path = ui.contract.API_PATH + '/queries'
        handler.allow_listener_path = lambda *_: True
        handler.require_authentication = lambda: {'username':'alice',ui.contract.PERMISSION:True}
        handler.send_bytes = Mock()
        with patch.object(ui, 'broker', return_value=broker), \
             patch.object(self.web, 'schedule_mushroom_competing_history') as schedule:
            for index in range(12):
                request = {'contract':ui.contract.CONTRACT_ID, 'request_id':f'point_query_{index}',
                    'point':{'lat':42+index/1000,'lon':2}, 'start_date':'2026-10-06',
                    'horizon_days':7, 'history_days':30, 'competing_selection':index%3 != 0,
                    'k_value': 2 if index%2 else 4}
                handler.read_request_body = lambda *_: json.dumps(request).encode()
                handler.do_POST()
                self.assertEqual(handler.send_bytes.call_args.args[0], 202)
            schedule.assert_not_called()
        self.assertEqual(broker.submit.call_count, 12)
        self.bundle.assert_not_called()
        self.assertFalse(self.state.exists())
        self.assertFalse(self.queue.exists())

    def test_cost_summaries_merge_and_reuse_without_overwriting_other_users(self):
        import json
        from rainmapper_core import mushroom_competing_comparison as comparison
        manifest = self.plan()[0]['manifest']
        def plan(k=None):
            k = 4 if k is None else k
            dependencies = {**self.dependencies, 'comparison_k':hashlib.sha256(str(float(k)).encode()).hexdigest()}
            return {'revision':control.revision(dependencies), 'history_revision':'f'*64,
                    'comparison_k':k, 'manifest':manifest}, dependencies
        with patch.object(self.web, 'mushroom_competing_plan', side_effect=plan):
            for k in (4, 2):
                code, result = self.web.request_mushroom_competing_history(self.worker, comparison_k=k)
                self.assertEqual(code, 202, result)
                jobs = self.web.mushroom_worker_jobs
                job = jobs.claim_next(self.queue, worker_id=self.worker, lane='background')
                auth = dict(job_id=job['job_id'], worker_id=self.worker, claim_token=job['claim_token'])
                jobs.start_job(self.queue, **auth)
                spec, _ = plan(k)
                value = evidence.summarize([], manifest=manifest, revision=spec['revision'], cutoff='2026-10-06')
                visits = [{'species_id':'s','id':str(i),'day':f'2026-09-{i+1:02d}','y':i%2} for i in range(4)]
                value.update(history_revision='f'*64, comparisons=[comparison.evaluate(visits, k=k,
                    cutoff='2026-10-06', replay=lambda v,issue,k:dict.fromkeys(comparison.METHODS, int(v['id'])%2 == 1))])
                code, response = self.web.finish_mushroom_worker_job({**auth, 'status':'complete',
                    'result': {'evidence': value, 'seconds':1}})
                self.assertEqual(code, 200, response)
            saved = json.loads(self.state.with_name('prediction-competing.json').read_text())
            self.assertEqual([r['k'] for r in saved['comparisons']], [4, 2])
            self.assertEqual(self.web.request_mushroom_competing_history(self.worker, comparison_k=4)[0], 200)
            self.assertEqual(self.bundle.call_count, 2)

    def test_explicit_workers_update_uses_personal_k_or_addon_inheritance(self):
        handler = self.web.RainmapperHandler.__new__(self.web.RainmapperHandler)
        handler.auth_credentials = lambda: ('token', 'device-test')
        with patch.object(self.web, 'schedule_mushroom_competing_history', return_value=True) as schedule:
            for settings, expected in (({'prediction_k_value':2.5},2.5), ({},None)):
                with patch.object(self.web, 'settings_for_device', return_value=settings):
                    result = handler.handle_mushroom_workers_post({
                        'worker_action':['run_competing_history'], 'worker_id':[self.worker]})
                self.assertEqual(result, './workers')
                schedule.assert_called_with(self.worker, origin='manual', comparison_k=expected)

    def test_runner_precompute_initializes_history_with_map_disabled_and_deduplicates(self):
        # Execute the asynchronous callbacks immediately, with all real data
        # paths and transport isolated by setUp. No operational job is launched.
        class ImmediateThread:
            def __init__(self, *, target, **kwargs):
                self.target = target
            def start(self):
                self.target()
        with patch.dict(os.environ, {'RAINMAPPER_PREDICTION_COMPETING_SELECTION':'false'}), \
             patch.object(self.web.threading,'Thread',ImmediateThread), \
             patch.object(self.web,'preferred_mushroom_precompute_worker',return_value=(self.worker,{},False)), \
             patch.object(self.web,'_unpack_predictor_precompute_plan',side_effect=ValueError('synthetic precompute unavailable')):
            self.assertFalse(self.state.exists())
            self.web.schedule_mushroom_predictor_precompute_request()
            state = control.load(self.state)
            self.assertEqual(state['status'],'queued')
            self.assertTrue(state['job_id'])
            self.web.schedule_mushroom_predictor_precompute_request()
            self.assertEqual(control.load(self.state)['job_id'],state['job_id'])
            self.assertEqual(self.bundle.call_count,1)

    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.web = load_web_server_module()
        self.state = self.root / 'state.json'; self.queue = self.root / 'jobs.json'
        self.dependencies = {'observations':'a'*64, 'models':'b'*64}
        self.worker = 'worker_aaaaaaaa'
        self.statuses = [{'reachable':True, 'payload':{'worker_id':self.worker,
                          'capabilities':[control.CAPABILITY], 'display_name':'Test'}}]
        for name, result in [('mushroom_competing_state_path',self.state),
                             ('mushroom_worker_jobs_path',self.queue),
                             ('mushroom_worker_input_bundles_path',self.root/'bundles'),
                             ('mushroom_worker_api_enabled',True),
                             ('authenticate_mushroom_worker',True),
                             ('discard_mushroom_worker_input_bundle',None),
                             ('reconcile_mushroom_worker_storage_for_launch',{})]:
            self.stack.enter_context(patch.object(self.web,name,return_value=result))
        self.stack.enter_context(patch.object(self.web,'registered_mushroom_worker_statuses',
                                              side_effect=lambda:self.statuses))
        self.stack.enter_context(patch.object(self.web,'mushroom_competing_plan',side_effect=self.plan))
        self.bundle = self.stack.enter_context(patch.object(self.web.mushroom_worker_transport,
            'prepare_coordinator_bundle', side_effect=lambda *a,**kw:{'job_id':kw['job_id'],
                 'snapshot_id':'sha256:'+'c'*64,'job_spec_id':'sha256:'+'d'*64}))

    def plan(self, comparison_k=None):
        return {'revision':control.revision(self.dependencies), 'manifest':{
            'batch_id':'batch', 'snapshot_id':'snapshot', 'quality_catalog':{'sha256':'quality'}}}, self.dependencies

    def running(self):
        code, result = self.web.request_mushroom_competing_history(self.worker)
        self.assertEqual(code,202,result)
        jobs = self.web.mushroom_worker_jobs
        claimed = jobs.claim_next(self.queue,worker_id=self.worker,lane='background')
        auth = dict(job_id=claimed['job_id'],worker_id=self.worker,claim_token=claimed['claim_token'])
        job = jobs.start_job(self.queue,**auth)
        spec,_ = self.plan()
        value = evidence.summarize([],manifest=spec['manifest'],revision=spec['revision'],cutoff='2026-10-05')
        return job,{**auth,'status':'complete','result':{'evidence':value,'seconds':3.5}}

    def test_queue_dedup_publication_retry_and_unchanged_inputs(self):
        job,payload = self.running()
        code,result = self.web.request_mushroom_competing_history(self.worker)
        self.assertEqual(code,200); self.assertTrue(result['reused'])
        self.assertEqual(self.bundle.call_count,1)
        # Simulate a crash after artifact/control commit, before the job queue commit.
        first = self.web.accept_mushroom_competing_result(job,payload)
        artifact = self.state.with_name('prediction-competing.json')
        before = artifact.stat().st_mtime_ns
        code,response = self.web.finish_mushroom_worker_job(payload)
        self.assertEqual(code,200,response)
        self.assertEqual(artifact.stat().st_mtime_ns,before)
        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(),first['artifact_sha256'])
        self.assertEqual(response['job']['result'],first)
        self.assertNotIn('evidence',response['job']['result'])
        code,retry = self.web.finish_mushroom_worker_job(payload)
        self.assertEqual(code,200); self.assertTrue(retry['idempotent'])
        self.assertEqual(self.web.request_mushroom_competing_history(self.worker)[0],200)
        self.assertEqual(self.bundle.call_count,1)

    def test_corrected_inputs_reject_stale_publication_and_offline_worker_stays_pending(self):
        _,payload = self.running()
        self.dependencies = {**self.dependencies,'observations':'e'*64}
        code,response = self.web.finish_mushroom_worker_job(payload)
        self.assertEqual(code,200,response)
        self.assertFalse(self.state.with_name('prediction-competing.json').exists())
        self.assertTrue(control.needs_job(control.load(self.state)))
        self.statuses = []
        self.assertEqual(self.web.request_mushroom_competing_history(self.worker)[0],409)
        self.assertEqual(control.load(self.state)['status'],'pending')

    def test_foreign_claim_invalid_payload_and_cancellation_never_activate(self):
        _,payload = self.running()
        for wrong in [{**payload,'claim_token':'wrong'}, {**payload,'status':'invented'},
                      {**payload,'result':{'evidence':{'kind':evidence.KIND,'revision':'a'*64}}}]:
            code,response = self.web.finish_mushroom_worker_job(wrong)
            self.assertEqual(code,409,response)
            self.assertFalse(self.state.with_name('prediction-competing.json').exists())
        auth = {k:payload[k] for k in ('job_id','worker_id','claim_token')}
        self.web.mushroom_worker_jobs.request_cancel(self.queue,job_id=auth['job_id'])
        self.assertEqual(self.web.finish_mushroom_worker_job(payload)[0],409)
        code,response = self.web.finish_mushroom_worker_job({**auth,'status':'cancelled'})
        self.assertEqual(code,200,response)
        self.assertEqual(control.load(self.state)['status'],'failed')
        self.assertFalse(self.state.with_name('prediction-competing.json').exists())

    def test_comparison_cannot_claim_a_different_input_generation(self):
        _, payload = self.running()
        spec, dependencies = self.plan()
        spec['history_revision'] = 'f' * 64
        payload['result']['evidence']['history_revision'] = 'e' * 64
        with patch.object(self.web, 'mushroom_competing_plan', return_value=(spec, dependencies)):
            code, response = self.web.finish_mushroom_worker_job(payload)
        self.assertEqual(code, 409, response)
        self.assertFalse(self.state.with_name('prediction-competing.json').exists())


if __name__ == '__main__':
    unittest.main()
