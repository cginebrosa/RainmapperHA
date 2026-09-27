import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_training_observations as trace


class TrainingObservationTests(unittest.TestCase):
    def test_deduplicated_sets_exact_membership_and_missing_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            batch = root / 'batches/batch-test'
            batch.mkdir(parents=True)
            writer = trace.Writer(batch / trace.FILENAME)
            rows = [{'metadata': {'observation_id': value}} for value in ['obs-a', 'obs-b', 'obs-a']]
            writer.add('model-a', ('shared',), rows)
            writer.add('model-b', ('shared',), rows)
            writer.add('model-c', ('other',), rows[:1])
            writer.add('incomplete', ('legacy-input',), rows[:1] + [{'sample_id': 'obs-b'}])
            manifest = {'batch_id': 'batch-test', 'training_observations': writer.finish('batch-test')}
            writer.close()
            self.assertEqual(trace.lookup(root, manifest, 'model-a', 'obs-a'), 'used')
            self.assertEqual(trace.lookup(root, manifest, 'model-b', 'obs-b'), 'used')
            self.assertEqual(trace.lookup(root, manifest, 'model-c', 'obs-b'), 'not_used')
            self.assertEqual(trace.lookup(root, manifest, 'model-a', "x' OR 1=1 --"), 'not_used')
            self.assertEqual(trace.lookup(root, manifest, 'incomplete', 'obs-a'), 'used')
            self.assertEqual(trace.lookup(root, manifest, 'incomplete', 'obs-b'), 'unavailable')
            self.assertEqual(trace.lookup(root, manifest, 'missing-model', 'obs-a'), 'unavailable')
            self.assertEqual(trace.lookup(root, {'batch_id': 'old'}, 'model-a', 'obs-a'), 'legacy')
            with sqlite3.connect(batch / trace.FILENAME) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM members').fetchone()[0], 4)
                plan = db.execute('EXPLAIN QUERY PLAN SELECT 1 FROM members WHERE set_id=? AND observation_id=?', (1, 'obs-a')).fetchall()
                self.assertIn('SEARCH members USING PRIMARY KEY', str(plan))
                self.assertNotIn('SCAN members', str(plan))
            (batch / trace.FILENAME).unlink()
            self.assertEqual(trace.lookup(root, manifest, 'model-a', 'obs-a'), 'unavailable')
            self.assertFalse((batch / trace.FILENAME).exists())  # read-only lookup must not create a database

    def test_budget_checked_before_iterating_and_reference_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = trace.Writer(Path(folder) / trace.FILENAME)
            try:
                with patch.object(trace, 'MAX_MEMBERS', 0), self.assertRaisesRegex(ValueError, 'budget'):
                    writer.add('model', ('scope',), [{}])
                self.assertEqual(writer.db.execute('SELECT count(*) FROM members').fetchone()[0], 0)
            finally:
                writer.close()
        for value in ({}, {'path': '../escape', 'sha256': 'a'*64, 'size_bytes': 4096},
                      {'path': 'batches/test/'+trace.FILENAME, 'sha256': 'a'*64, 'size_bytes': trace.MAX_BYTES+1}):
            with self.assertRaises(ValueError):
                trace.validate_reference(value, 'test')

    def test_shared_model_resolves_to_actual_artifact(self):
        from rainmapper_core import mushroom_ml_model_catalog as catalog
        from rainmapper_core import mushroom_ml_version_registry as versions
        registry = versions.load_registry(Path(__file__).resolve().parents[1] / 'mushroom-data/mushroom_ml_version_registry.json')
        profile = next(p for p in catalog.catalog_entries(registry) if 'shared' in p['estimator_scopes'].values())
        estimator = next(e for e, scope in profile['estimator_scopes'].items() if scope == 'shared')
        reference = {'batch_id': 'batch-test', 'generation_id': 'gen-test',
                     'version_id': profile['version_id'], 'profile_id': profile['profile_id'],
                     'temporal_contract_id': profile['temporal_contract_ids'][0],
                     'estimator_id': estimator, 'species_id': 'boletus_edulis', 'horizon_days': 7}
        self.assertEqual(catalog.artifact_ref_for_model_ref(registry, reference).species_id, 'all_species')
