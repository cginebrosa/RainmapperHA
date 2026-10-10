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
