import io
import json
from pathlib import Path
import threading
import unittest
from unittest import mock

import test_weather_history_dataset as weather_fixture
from rainmapper_core import mushroom_map_runtime as maps
from rainmapper_core import mushroom_predictor_runtime as runtime
from rainmapper_core import mushroom_map_worker as worker
from rainmapper_core.mushroom_map_queries import QueryError


class MapRuntimeTests(unittest.TestCase):
    def setUp(self):
        fixture = weather_fixture.WeatherHistoryDatasetTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = Path(fixture.temp_dir.name)
        self.config = {'weather_data': str(fixture.data_dir)}
        for key in maps.PRIVATE_FILES:
            path = self.root/(key+'.json')
            path.write_text(json.dumps({'key': key}))
            self.config[key] = str(path)
        self.config['forest_catalogs'] = self.config['ecology_catalogs']
        registry = Path(self.config['model_registry'])
        registry.write_text('{"versions": [], "preferred_version_id": "test"}')
        sealed = self.root/'sealed-registry.json'
        sealed.write_text('{"versions": []}')
        model = self.root/'model.joblib'; model.write_bytes(b'model-fixture')
        self.sources = {'models/model.joblib': model,
                        'data/mushroom_ml_version_registry.json': sealed,
                        'data/mushroom_observation_features_v0.json': registry,
                        'data/mushroom_known_sites.json': registry}
        for path in fixture.root.rglob('*'):
            if path.is_file():
                self.sources['weather/weather-history/'+path.relative_to(fixture.root).as_posix()] = path
        self.publication_path = self.root/'publication.json'
        self.publish_base()
        self.publisher = maps.MapPublication(self.config, self.root, publication_path=self.publication_path,
                                             cache_root=self.root/'ha-snapshots', start=False)
        self.addCleanup(self.publisher.close)
        self.publisher.refresh()
        self.calls = []
        self.executor = self.new_executor()

    def publish_base(self):
        rows = [runtime._entry(path.split('/')[0], path, source) for path, source in sorted(self.sources.items())]
        manifest = {'schema_version':runtime.SCHEMA_VERSION, 'kind':runtime.MANIFEST_KIND,
                    'contracts':{}, 'files':rows}
        manifest.update(fingerprint=maps.digest(maps.encode(manifest)), size_bytes=sum(r['size_bytes'] for r in rows))
        self.base_manifest = manifest
        self.publication_path.write_bytes(maps.encode({'manifest':manifest,
            'sources':{k:str(v) for k,v in self.sources.items()},
            'source_state':{k:{'mtime_ns':v.stat().st_mtime_ns} for k,v in self.sources.items()}}))

    def new_executor(self):
        class Executor:
            def __init__(self, config, root): self.config = config
            def execute(self, request): return json.loads(Path(self.config['profiles']).read_text())
            def close(self): pass
        executor = maps.CachedPointExecutor({}, self.root,
            {'coordinator_id':'coordinator_1234567890abcdef','rainmapper_url':'http://fixture.invalid','token':'fixture'},
            'worker_fixture', self.root/'worker', executor_factory=Executor)
        self.addCleanup(executor.close)
        def post(action, reference, **extra):
            self.calls.append((action, extra.get('file')))
            if action == 'runtime_manifest':
                return io.BytesIO(maps.encode(self.publisher.lookup(reference['fingerprint'])['manifest']))
            return self.publisher.object(reference['fingerprint'], extra['file'])[0].open('rb')
        executor._post = post
        return executor

    def test_existing_predictor_objects_reused_and_resident_query_does_no_io(self):
        runtime.synchronize_runtime(self.root/'worker/predictor-runtime/primary', self.base_manifest,
            lambda key,target: target.write_bytes(self.sources[key].read_bytes()), objects_root=self.executor.objects)
        reference = self.publisher.reference()
        self.executor.prepare(reference)
        fetched = [path for action,path in self.calls if action == 'runtime_object']
        self.assertTrue(fetched)
        self.assertFalse(any(p.startswith(('weather/','models/')) for p in fetched))
        self.assertEqual(len(set(fetched) & {'data/forest_catalogs.json', 'data/mushroom_reference_catalogs.json'}),1)
        manifest = self.publisher.lookup(reference['fingerprint'])['manifest']
        self.assertFalse(any('observation' in r['path'] or 'known_sites' in r['path'] for r in manifest['files']))
        self.calls.clear()
        with mock.patch.object(runtime, 'synchronize_runtime', side_effect=AssertionError('resident sync')):
            self.assertEqual(self.executor.execute_snapshot({}, reference), {'key':'profiles'})
        self.assertEqual(self.calls, [])
        self.assertEqual(self.executor.last_sync['transferred_size_bytes'], 0)

    def test_ha_hashes_only_changed_small_file_and_retains_inflight_snapshot(self):
        old = self.publisher.reference()
        self.executor.prepare(old)
        before = dict(self.publisher.metrics)
        with mock.patch.object(maps, 'read_small', side_effect=AssertionError('warm HA reads')):
            self.publisher.refresh()
            self.assertEqual(self.publisher.reference(), old)
        self.assertEqual(before, self.publisher.metrics)
        changed = b'{"edited_by_user":true}'
        Path(self.config['profiles']).write_bytes(changed)
        with self.assertRaisesRegex(QueryError,'map_data_not_ready'): self.publisher.reference()
        with mock.patch.object(runtime, '_sha256', side_effect=AssertionError('HA heavy hashing')):
            self.publisher.refresh()
        new = self.publisher.reference()
        self.assertNotEqual(old, new)
        self.assertEqual(self.publisher.metrics['small_hashed_bytes']-before['small_hashed_bytes'],len(changed))
        self.assertEqual(self.publisher.metrics['heavy_hashed_bytes'],0)
        self.calls.clear()
        self.executor.prepare(new)
        self.assertEqual([p for a,p in self.calls if a=='runtime_object'],['data/mushroom_profiles.json'])
        self.assertEqual(self.executor.last_sync['transferred_size_bytes'],len(changed))
        self.assertEqual(json.loads(self.publisher.object(old['fingerprint'],'data/mushroom_profiles.json')[0].read_bytes()),{'key':'profiles'})

    def test_worker_restart_reuses_receipt_without_hashes_or_transfer(self):
        reference = self.publisher.reference(); self.executor.prepare(reference)
        self.calls.clear()
        restarted = self.new_executor()
        with mock.patch.object(runtime, '_sha256', side_effect=AssertionError('unnecessary restart hash')):
            restarted.prepare(reference)
        self.assertEqual(self.calls, [])
        self.assertEqual(restarted.last_sync['hashed_file_count'],0)

    def test_weather_update_fetches_only_changed_partition_and_generation_metadata(self):
        old = self.publisher.reference(); self.executor.prepare(old)
        current = json.loads(self.publisher.current_path.read_bytes())
        weather_root = self.publisher.current_path.parent
        old_manifest_path = weather_root/current['manifest_path']
        generation = json.loads(old_manifest_path.read_bytes())
        partition = generation['partitions'][0]
        old_partition = weather_root/partition['path']
        import pyarrow.parquet as pq
        table = pq.read_table(old_partition)
        new_partition = old_partition.with_name('updated.parquet')
        pq.write_table(table, new_partition, compression='gzip')
        sha = maps.digest(new_partition.read_bytes())[7:]
        final_partition = new_partition.with_name('data-'+sha+'.parquet')
        new_partition.replace(final_partition)
        size_delta = final_partition.stat().st_size-partition['size_bytes']
        del self.sources['weather/weather-history/'+partition['path']]
        partition.update(path=final_partition.relative_to(weather_root).as_posix(),sha256=sha,size_bytes=final_partition.stat().st_size)
        generation['totals']['size_bytes'] += size_delta
        generation['previous_generation_id'] = generation['generation_id']
        generation['generation_id'] = '20260915T010000Z-next'
        new_manifest = weather_root/'manifests'/('20260915T010000Z-next.json')
        new_manifest.write_bytes(maps.encode(generation))
        del self.sources['weather/weather-history/'+current['manifest_path']]
        current.update(generation_id=generation['generation_id'],manifest_path=new_manifest.relative_to(weather_root).as_posix(),manifest_sha256=maps.digest(new_manifest.read_bytes())[7:])
        self.publisher.current_path.write_bytes(maps.encode(current))
        additions = {'weather/weather-history/'+p.relative_to(weather_root).as_posix():p for p in (new_manifest,final_partition)}
        self.sources.update(additions); self.publish_base()
        self.publisher.refresh(); self.calls.clear()
        self.executor.prepare(self.publisher.reference())
        fetched = {p for a,p in self.calls if a=='runtime_object'}
        self.assertEqual(fetched,set(additions)|{'weather/weather-history/CURRENT.json'})
        self.assertTrue(self.publisher.lookup(old['fingerprint'])['root'].exists())

    def test_corrupt_same_size_object_is_repaired_after_restart(self):
        reference = self.publisher.reference(); self.executor.prepare(reference)
        path = Path(self.executor.executor.config['profiles'])
        path.write_bytes(b'x'*path.stat().st_size)
        self.calls.clear()
        restarted = self.new_executor(); restarted.prepare(reference)
        self.assertEqual(restarted.execute_snapshot({},reference),{'key':'profiles'})
        self.assertEqual([p for a,p in self.calls if a=='runtime_object'],['data/mushroom_profiles.json'])

    def test_failed_transfer_keeps_current_and_resumes_from_shared_objects(self):
        old = self.publisher.reference(); self.executor.prepare(old)
        Path(self.config['profiles']).write_text('{"revision":2}')
        self.publisher.refresh(); new = self.publisher.reference()
        post = self.executor._post
        def interrupted(action, reference, **extra):
            if action=='runtime_object': return io.BytesIO(b'wrong')
            return post(action, reference, **extra)
        self.executor._post = interrupted
        with self.assertRaises(ValueError): self.executor.prepare(new)
        self.assertEqual(self.executor.fingerprint, old['fingerprint'])
        self.assertFalse(list((self.executor.cache/'versions').glob('.*.tmp')))
        self.executor._post = post; self.executor.prepare(new)
        self.assertEqual(self.executor.execute_snapshot({},new),{'revision':2})

    def test_versions_are_bounded_without_deleting_other_runtime_objects(self):
        for revision in range(4):
            Path(self.config['profiles']).write_text(json.dumps({'revision':revision}))
            self.publisher.refresh(); self.executor.prepare(self.publisher.reference())
        self.assertEqual(len(list((self.executor.cache/'versions').iterdir())),2)
        self.assertTrue(all(p.stat().st_nlink>1 for p in self.executor.objects.iterdir()))
        for row in self.publisher.snapshots.values(): row['used'] -= 200
        self.publisher.refresh()
        self.assertEqual(len(self.publisher.snapshots),1)
        self.assertEqual(len(list(self.publisher.cache.iterdir())),1)

    def test_missing_publication_stale_weather_or_models_fail_closed(self):
        original = self.publisher.current_path.read_bytes()
        self.publisher.current_path.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError,'weather_publication_pending'): self.publisher.refresh()
        self.publisher.current_path.write_bytes(original)
        Path(self.config['model_registry']).write_text('{"versions":["new"]}')
        with self.assertRaisesRegex(ValueError,'model_publication_pending'): self.publisher.refresh()
        with self.assertRaisesRegex(QueryError,'map_data_not_ready'): self.publisher.reference()

    def test_suspension_changes_snapshot_and_is_transported_to_worker(self):
        from rainmapper_core import mushroom_ml_prediction_policy as policy
        previous = self.publisher.reference()['fingerprint']
        registry = json.loads(Path(self.config['model_registry']).read_text())
        registry[policy.FIELD] = [{'version_id':'altitude_v2','profile_id':'common_idw',
            'estimator_id':'hist_gradient_boosting_restricted_v1','species_id':'lactarius_deliciosus',
            'reason':'audit','updated_at':'2026-09-19','updated_by':'test'}]
        Path(self.config['model_registry']).write_bytes(maps.encode(registry))
        with self.assertRaisesRegex(QueryError, 'map_data_not_ready'):
            self.publisher.reference()
        self.sources['data/mushroom_ml_version_registry.json'].write_bytes(maps.encode(registry))
        self.publish_base()
        self.publisher.refresh()
        reference = self.publisher.reference()
        self.assertNotEqual(reference['fingerprint'], previous)
        self.assertEqual(reference['required_capabilities'], [policy.CAPABILITY])
        self.executor.prepare(reference)
        received = json.loads(Path(self.executor.executor.config['model_registry']).read_text())
        self.assertEqual(received[policy.FIELD], registry[policy.FIELD])

    def test_recommendation_mode_changes_identity_and_requires_new_worker(self):
        from rainmapper_core import mushroom_recommendation_policy as rec
        previous = self.publisher.reference()['fingerprint']
        path = Path(self.config['model_registry'])
        registry = json.loads(path.read_text())
        registry[rec.FIELD] = {'mode': 'shadow', 'rule_version': 'consensus_v1'}
        path.write_bytes(maps.encode(registry))
        with self.assertRaises(QueryError):
            self.publisher.reference()
        self.publisher.refresh()
        reference = self.publisher.reference()
        self.assertNotEqual(reference['fingerprint'], previous)
        self.assertIn(rec.CAPABILITY, reference['required_capabilities'])
        self.executor.prepare(reference)
        received = json.loads(Path(self.executor.executor.config['model_registry']).read_text())
        self.assertEqual(received[rec.FIELD], registry[rec.FIELD])

    def test_external_policy_is_live_but_worker_snapshot_is_frozen(self):
        from rainmapper_core import mushroom_ml_policy_store as store
        from rainmapper_core import mushroom_ml_prediction_policy as policy
        registry_path = Path(self.config['model_registry'])
        raw = json.loads(registry_path.read_text())
        raw[store.REFERENCE] = store.FILENAME
        registry_path.write_bytes(maps.encode(raw))
        row = {'version_id':'altitude_v2','profile_id':'common_idw',
               'estimator_id':'hist_gradient_boosting_restricted_v1','species_id':'lactarius_deliciosus',
               'reason':'audit','updated_at':'2026-09-19','updated_by':'test'}
        path = registry_path.parent/store.FILENAME
        path.write_bytes(store.encode(store.document({policy.FIELD:[row]})))
        self.publisher.refresh()  # sealed model publication still has no rules
        reference = self.publisher.reference()
        self.executor.prepare(reference)
        sealed = Path(self.executor.executor.config['model_registry'])
        self.assertEqual(json.loads(sealed.read_bytes())[policy.FIELD], [row])
        self.assertNotIn(store.REFERENCE, json.loads(sealed.read_bytes()))
        path.write_bytes(store.encode(store.document({})))
        with self.assertRaisesRegex(QueryError, 'map_data_not_ready'):
            self.publisher.reference()
        self.publisher.refresh()
        self.assertNotEqual(reference, self.publisher.reference())
        self.assertEqual(json.loads(sealed.read_bytes())[policy.FIELD], [row])
        self.assertNotIn('required_capabilities', self.publisher.reference())
        path.unlink()
        with self.assertRaises(OSError): self.publisher.refresh()
        with self.assertRaises(QueryError): self.publisher.reference()

    def test_limits_and_authorization_before_materialization(self):
        with self.assertRaises(QueryError): self.publisher.object('sha256:'+'f'*64,'data/mushroom_profiles.json')
        with self.assertRaises(QueryError): self.publisher.object(self.publisher.current,'../../etc/passwd')
        with self.assertRaises(ValueError): self.executor.prepare({'fingerprint':'../../escape'})
        before = list(self.publisher.cache.iterdir())
        Path(self.config['profiles']).write_bytes(b' '*(maps.MAX_SMALL_FILE+1))
        with self.assertRaisesRegex(ValueError,'metadata_limit'): self.publisher.refresh()
        self.assertEqual(before,list(self.publisher.cache.iterdir()))
        bad = json.loads(maps.encode(self.base_manifest)); bad['files'][0]['sha256']='sha256:'+'f'*64
        with self.assertRaisesRegex(ValueError,'manifest_identity'): maps.checked_manifest(bad)

    def test_promotion_audit_does_not_hide_ready_models_but_generation_changes_do(self):
        version = {'version_id': 'fixture', 'installed_generation_id': 'current',
                   'generations': [{'generation_id': 'current', 'artifacts': ['model.joblib']}]}
        live = {'versions': [version], 'preferred_version_id': 'fixture'}
        sealed = {'versions': [{**version, 'installation': {
            'approved_by': 'linked_full_update', 'previous_generation_id': 'previous'}}]}
        Path(self.config['model_registry']).write_bytes(maps.encode(live))
        self.sources['data/mushroom_ml_version_registry.json'].write_bytes(maps.encode(sealed))
        self.publish_base()
        self.publisher.refresh()
        self.executor.prepare(self.publisher.reference())
        # Preserve the user's registry verbatim in the transported snapshot.
        self.assertEqual(json.loads(Path(self.executor.executor.config['model_registry']).read_bytes()), live)
        version['installed_generation_id'] = 'different'
        Path(self.config['model_registry']).write_bytes(maps.encode(live))
        with self.assertRaisesRegex(ValueError, 'model_publication_pending'):
            self.publisher.refresh()
        version['installed_generation_id'] = 'current'
        version['generations'][0]['artifacts'] = ['different.joblib']
        Path(self.config['model_registry']).write_bytes(maps.encode(live))
        with self.assertRaisesRegex(ValueError, 'model_publication_pending'):
            self.publisher.refresh()

    def test_idle_online_lane_prepares_before_advertising_ready(self):
        stop = threading.Event(); slot = threading.Lock(); messages = []
        reference = self.publisher.reference()
        def transport(coordinator, payload):
            messages.append(payload)
            self.assertFalse(slot.acquire(blocking=False))
            if len(messages)==2: stop.set()
            return {'query':None,'runtime':reference}
        worker.run_loop([{'coordinator_id':'a'}],'worker_fixture',{'a':self.executor},stop,
                        transport=transport,online_slot=slot)
        self.assertIsNone(messages[0]['ready_fingerprint'])
        self.assertEqual(messages[1]['ready_fingerprint'],reference['fingerprint'])
        self.assertTrue(slot.acquire(blocking=False)); slot.release()
