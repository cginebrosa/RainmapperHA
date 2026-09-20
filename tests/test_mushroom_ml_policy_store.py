import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from rainmapper_core import mushroom_ml_policy_store as store
from rainmapper_core import mushroom_ml_prediction_policy as policy
from rainmapper_core import mushroom_ml_version_registry as versions
from rainmapper_core import mushroom_predictor_runtime as runtime
from rainmapper_core import mushroom_rebuild_snapshot as snapshots

ROOT = Path(__file__).resolve().parents[1]
SPECIES = 'lactarius_deliciosus'
KEY = 'altitude_v2/common_idw/hist_gradient_boosting_restricted_v1'


class PolicyStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'registry.json'
        self.base = versions.load_registry(ROOT/'mushroom-data/mushroom_ml_version_registry.json')
        self.rules = policy.update(self.base, model_key=KEY, species_id=SPECIES,
            enabled=False, reason='Rainfall audit', actor='test', expected_revision=policy.revision(self.base))
        versions.save_registry(self.path, self.rules)
        self.policy_path = self.path.parent/store.FILENAME

    def test_migration_preserves_effective_registry_and_contract(self):
        store.migrate(self.path)
        self.assertEqual(versions.load_registry(self.path), self.rules)
        disk = json.loads(self.path.read_text())
        self.assertNotIn(policy.FIELD, disk)
        self.assertEqual(disk[store.REFERENCE], store.FILENAME)
        self.assertEqual(versions.training_contract_revision(disk), versions.training_contract_revision(self.rules))
        self.assertEqual(store.decode(self.policy_path.read_bytes()), self.rules[policy.FIELD])
        before = self.path.read_bytes(), self.policy_path.read_bytes()
        store.migrate(self.path)
        self.assertEqual(before, (self.path.read_bytes(), self.policy_path.read_bytes()))

    def test_migration_recovers_after_pointer_write_failure(self):
        with mock.patch.object(versions, 'save_registry', side_effect=OSError('disk')):
            with self.assertRaises(OSError): store.migrate(self.path)
        self.assertEqual(versions.load_registry(self.path), self.rules)
        store.migrate(self.path)
        self.assertEqual(versions.load_registry(self.path), self.rules)

    def test_conflicting_unlinked_file_is_not_overwritten(self):
        self.policy_path.write_bytes(store.encode(store.document(self.base)))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'differ'): store.migrate(self.path)
        self.assertEqual(before, self.path.read_bytes())

    def test_promotion_cannot_restore_old_rules_and_empty_is_authoritative(self):
        store.migrate(self.path)
        registry_bytes = self.path.read_bytes()
        store.save(self.path, self.base, expected_revision=policy.revision(self.rules))
        self.assertEqual(self.path.read_bytes(), registry_bytes)
        self.assertEqual(versions.load_registry(self.path), self.base)
        versions.save_registry(self.path, self.rules)  # job carries its older policy
        self.assertEqual(versions.load_registry(self.path), self.base)
        versions.ensure_seeded(default_path=ROOT/'mushroom-data/mushroom_ml_version_registry.json', persistent_path=self.path)
        self.assertEqual(versions.load_registry(self.path), self.base)

    def test_portable_copy_does_not_modify_destination_generations(self):
        store.migrate(self.path)
        with tempfile.TemporaryDirectory() as other:
            destination = Path(other)/'registry.json'
            local = copy.deepcopy(self.base)
            local['versions'][0]['description'] = 'different installation metadata'
            versions.save_registry(destination, local)
            store.migrate(destination)
            before = destination.read_bytes()
            (destination.parent/store.FILENAME).write_bytes(self.policy_path.read_bytes())
            effective = versions.load_registry(destination)
            self.assertEqual(effective[policy.FIELD], self.rules[policy.FIELD])
            effective.pop(policy.FIELD)
            self.assertEqual(effective, local)
            self.assertEqual(destination.read_bytes(), before)

    def test_malformed_missing_oversized_and_path_escape_fail_closed(self):
        store.migrate(self.path)
        for raw in (b'{}', b'bad', b' '*(store.MAX_BYTES+1)):
            self.policy_path.write_bytes(raw)
            with self.assertRaises(ValueError): versions.load_registry(self.path)
        self.policy_path.unlink()
        with self.assertRaises(OSError): versions.load_registry(self.path)
        raw = json.loads(self.path.read_text()); raw[store.REFERENCE] = '../other.json'
        self.path.write_text(json.dumps(raw))
        with self.assertRaises(ValueError): versions.load_registry(self.path)

    def test_import_rejects_stale_unknown_and_registry_documents_atomically(self):
        raw = store.encode(store.document(self.rules))
        expected = policy.revision(self.base)
        result = store.import_rules(raw, self.base, {SPECIES}, expected_revision=expected)
        self.assertEqual(result, self.rules)
        for data, species, revision in (
            (raw, set(), expected), (raw, {SPECIES}, 'stale'),
            (json.dumps(self.base).encode(), {SPECIES}, expected),
            (raw.replace(b'hist_gradient_boosting_restricted_v1', b'unknown'), {SPECIES}, expected),
        ):
            with self.assertRaises(ValueError):
                store.import_rules(data, self.base, species, expected_revision=revision)
        with self.assertRaisesRegex(ValueError, 'Refresh'):
            store.save(self.path, self.base, expected_revision=expected)
        self.assertEqual(versions.load_registry(self.path), self.rules)

    def test_worker_training_and_runtime_snapshots_freeze_effective_rules(self):
        store.migrate(self.path)
        snapshot = self.path.parent/'snapshot/inputs/extra/registry.json'
        snapshots._copy_snapshot_file(self.path, snapshot, role='extra:registry.json',
                                      logical_path='inputs/extra/registry.json', required=True)
        runtime_path = runtime._runtime_registry_snapshot(versions.load_registry(self.path),
                                    source_path=self.path, explicit_source=True)
        store.save(self.path, self.base, expected_revision=policy.revision(self.rules))
        for path in (snapshot, runtime_path):
            self.assertEqual(versions.load_registry(path)[policy.FIELD], self.rules[policy.FIELD])
            self.assertNotIn(store.REFERENCE, json.loads(path.read_text()))
        self.assertEqual(versions.load_registry(self.path), self.base)

    def test_published_precompute_identity_rejects_changed_live_policy(self):
        store.migrate(self.path)
        publication = {'policy_source': {'registry_path': str(self.path), 'revision': policy.revision(self.rules)}}
        runtime._check_published_policy(publication)
        self.policy_path.write_bytes(store.encode(store.document(self.base)))
        with self.assertRaisesRegex(ValueError, 'settings changed'):
            runtime._check_published_policy(publication)

    def test_ui_import_requires_confirmation_and_rejects_stale_forms(self):
        from test_web_server_auth import load_web_server_module
        web = load_web_server_module()
        handler = object.__new__(web.RainmapperHandler)
        profiles = mock.Mock()
        profiles.load.return_value = {'species_profiles':[{'species_id':SPECIES}]}
        form = {'policy_revision':[policy.revision(self.rules)],
                'policy_json':[store.encode(store.document(self.base)).decode()]}
        with mock.patch.object(web.mushroom_paths, 'mushroom_ml_version_registry_path', return_value=self.path), \
             mock.patch.object(web, 'default_store', return_value=profiles), \
             mock.patch.object(web, 'set_mushroom_workers_flash') as flash:
            handler.handle_mushroom_model_policy_import(form)
            self.assertTrue(flash.call_args.kwargs['error'])
            self.assertEqual(versions.load_registry(self.path), self.rules)
            form['confirm_replace'] = ['true']
            handler.handle_mushroom_model_policy_import(form)
            self.assertFalse(flash.call_args.kwargs.get('error'))
            self.assertEqual(versions.load_registry(self.path), self.base)
            handler.handle_mushroom_model_policy_import(form)
            self.assertTrue(flash.call_args.kwargs['error'])
