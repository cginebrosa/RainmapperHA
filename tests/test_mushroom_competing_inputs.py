import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from rainmapper_core import mushroom_competing_inputs as inputs
from rainmapper_core import weather_history_dataset as dataset


class InputRevisionTests(unittest.TestCase):
    def test_only_exact_reviewed_source_hash_preserves_runtime_identity(self):
        (name, reviewed), previous = next(iter(inputs._REVIEWED_RUNTIME_FILE_HASHES.items()))
        files = [Path(name), Path('mushroom_ml_runtime_features.py')]
        hashes = {name:previous, files[1].name:'a'*64}
        with patch.object(inputs, '_procedure_files', return_value=files), \
             patch.object(inputs, 'file_hash', side_effect=lambda p:hashes[p.name]):
            before = inputs.runtime_feature_revision()
            procedure_before = inputs.procedure_revision()
            hashes[name] = reviewed
            self.assertEqual(inputs.runtime_feature_revision(), before)
            self.assertNotEqual(inputs.procedure_revision(), procedure_before)
            hashes[name] = 'b'*64
            self.assertNotEqual(inputs.runtime_feature_revision(), before)
            hashes[name] = reviewed
            hashes[files[1].name] = 'c'*64
            self.assertNotEqual(inputs.runtime_feature_revision(), before)

    def test_multi_k_changes_comparison_revision_but_not_history_or_models(self):
        from rainmapper_core import mushroom_ml_version_registry as versions
        from rainmapper_core import mushroom_ml_model_catalog as catalog
        from rainmapper_core import mushroom_ml_policy_store as policy_store
        from rainmapper_core import mushroom_recommendation_policy as recommendations
        from rainmapper_core import mushroom_map_model_runtime as runtime
        from tests.test_mushroom_competing_history import REF
        manifest_path = Path('synthetic-manifest.json')
        documents = {
            'registry.json':{}, 'profiles.json':{'species_profiles':[]},
            manifest_path.name:{'batch_id':'b','snapshot_id':'s', 'quality_catalog':{'path':'q','sha256':'q'},
                                'artifacts':[{'artifact_ref':REF}]},
            'observations.json':{'observations':[]},
        }
        quality = {'species_selections':[{'species_id':REF['species_id'], 'candidate_chain':[
            {'candidate':{**REF,'horizon_days':7}}]}]}
        kwargs = dict(registry_path=Path('registry.json'), profiles_path=Path('profiles.json'),
            models_root=Path('models'), observations_path=Path('observations.json'),
            known_sites_path=Path('sites.json'), stations_path=Path('stations.txt'),
            features_path=Path('features.json'), weather_data_dir=Path('weather'),
            weather_cache_path=Path('cache.json'), cutoff='2026-10-06')
        with patch.object(inputs, 'read_json', side_effect=lambda p,limit:documents[Path(p).name]), \
             patch.object(inputs, 'file_hash', return_value='a'*64), \
             patch.object(inputs, 'historical_weather_revision', return_value='b'*64), \
             patch.object(inputs, 'procedure_revision', return_value='c'*64), \
             patch.object(policy_store, 'resolve', return_value={}), \
             patch.object(versions, 'operational_manifest_path', return_value=manifest_path), \
             patch.object(runtime, 'projected_quality', return_value=quality), \
             patch.object(catalog, 'catalog_entries', return_value=[]), \
             patch.object(recommendations, 'settings', return_value={}):
            original, deps = inputs.plan(**kwargs, comparison_k=4)
            expanded, new_deps = inputs.plan(**kwargs, comparison_ks=[4.0, 2.5, 4])
            reordered, _ = inputs.plan(**kwargs, comparison_ks=[2.5, 4.0])
        self.assertEqual(expanded, reordered)
        self.assertEqual(expanded['required_ks'], [2.5, 4.0])
        self.assertEqual(expanded['comparison_ks'], [2.5, 4.0])
        self.assertEqual(expanded['kind'], 'competing_history_job_v2')
        self.assertNotEqual(original['revision'], expanded['revision'])
        self.assertEqual(original['history_revision'], expanded['history_revision'])
        self.assertEqual(original['references'], expanded['references'])
        self.assertEqual({k:v for k,v in deps.items() if k != 'comparison_ks'},
                         {k:v for k,v in new_deps.items() if k != 'comparison_ks'})

    def test_only_feature_producer_changes_invalidate_runtime_input_identity(self):
        files = [Path(name) for name in (
            'mushroom_competing_replay.py', 'mushroom_competing_fits.py',
            'mushroom_ml_runtime_features.py', 'mushroom_competing_panels.py',
            'build-biology-v4-benchmark.py', 'mushroom_competing_new_unknown.py')]
        hashes = {p.name: 'a' for p in files}
        with patch.object(inputs, '_procedure_files', return_value=files), \
                patch.object(inputs, 'file_hash', side_effect=lambda p: hashes[p.name]):
            initial = inputs.runtime_feature_revision()
            procedure = inputs.procedure_revision()
            for p in files[:2]:
                hashes[p.name] = 'b'
                self.assertEqual(inputs.runtime_feature_revision(), initial)
                self.assertNotEqual(inputs.procedure_revision(), procedure)
            for p in files[2:]:
                before = inputs.runtime_feature_revision()
                hashes[p.name] = 'b'
                self.assertNotEqual(inputs.runtime_feature_revision(), before)

    def test_weather_after_last_observation_does_not_invalidate_but_historical_correction_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observations = [{'observed_at':'2026-09-01'}]
            rows = [{'local_date':'20260801','rain_mm':2.,'station_code':'test'}]
            def revision(rows):
                p = root / 'weather.parquet'
                pq.write_table(pa.Table.from_pylist(rows),p)
                sha = hashlib.sha256(p.read_bytes()).hexdigest()
                part = SimpleNamespace(source='meteocat',year=2026,path=p.name,sha256=sha,
                        min_local_date=min(r['local_date'] for r in rows),
                        max_local_date=max(r['local_date'] for r in rows))
                generation = SimpleNamespace(partitions=[part],object_path=lambda name:root/name)
                with patch.object(dataset,'resolve_weather_generation',return_value=generation):
                    return inputs.historical_weather_revision(root,observations,root/'memo.json')
            before = revision(rows)
            after = revision(rows + [{'local_date':'20261001','rain_mm':99.,'station_code':'test'}])
            self.assertEqual(before,after)
            corrected = revision([{**rows[0],'rain_mm':5.}])
            self.assertNotEqual(before,corrected)

    def test_complete_immutable_year_needs_no_data_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            part = SimpleNamespace(source='meteocat',year=2025,path='unused',sha256='a'*64,
                                   min_local_date='20250101',max_local_date='20251231')
            generation = SimpleNamespace(partitions=[part],object_path=lambda name:Path(tmp)/name)
            with patch.object(dataset,'resolve_weather_generation',return_value=generation), \
                 patch.object(pq,'ParquetFile',side_effect=AssertionError('must not scan')):
                result = inputs.historical_weather_revision(Path(tmp),[
                    {'observed_at':'2025-10-01'},{'observed_at':'2026-10-01'}],Path(tmp)/'memo.json')
            self.assertEqual(len(result),64)


if __name__ == '__main__':
    unittest.main()
