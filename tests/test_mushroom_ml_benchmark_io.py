from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_ml_benchmark_io as io
from rainmapper_core import mushroom_ml_biology_v4 as v4
from rainmapper_core import mushroom_ml_biology_v3_physical as physical


class BenchmarkIOTests(unittest.TestCase):
    def test_typed_weather_roundtrip_projection_and_bounds_preserve_source(self):
        from copy import deepcopy
        with tempfile.TemporaryDirectory() as tmp:
            value = self.fixture()
            value['kind'] = 'mushroom_ml_biology_v3_benchmark'
            value['samples'] = deepcopy(value['samples'] * 70)
            for index, sample in enumerate(value['samples']):
                sample['metadata'].update(area_id='area', area_representative_location={'lat':42.},
                    weather_idw={'unused_diagnostics': [index]},
                    weather_series={'daily_dates':['2026-01-01','2026-01-02'],
                        'daily_area_rain_idw_mean_mm':[None, index + .123456789123],
                        'daily_eto0_mean_mm':[], 'water_state_contract_id':'fixture'})
            original = deepcopy(value)
            path = Path(tmp)/'weather.parquet'
            def write(rows):
                io.write_rows(path, value, rows, columns=['rain','temperature'],
                              count=len(value['samples']), weather_column=True)
            write(value['samples'])
            self.assertEqual(io.read(path), value)
            self.assertEqual(list(io.SampleRows(path)), value['samples'])
            for projection in (io.fit_sample, io.historical_source_sample):
                self.assertEqual(io.read(path, sample_projection=projection)['samples'],
                                 [projection(s) for s in value['samples']])
            without = list(io.SampleRows(path, include_weather=False))
            self.assertTrue(all('weather_series' not in s['metadata'] for s in without))
            compact = [io.historical_intermediate_sample(s) for s in value['samples']]
            write(compact)
            self.assertEqual(io.read(path)['samples'], compact)
            self.assertEqual(value, original)
            self.assertTrue(all('weather_idw' not in s['metadata'] for s in compact))
            self.assertTrue(all('area_representative_location' in s['metadata'] for s in compact))
            for bad in (float('nan'), float('inf')):
                invalid = deepcopy(compact)
                invalid[0]['metadata']['weather_series']['daily_eto0_mean_mm'] = [bad]
                with self.assertRaisesRegex(ValueError, 'weather_nonfinite'):
                    write(invalid)
                self.assertEqual(io.read(path)['samples'], compact)
            invalid = deepcopy(compact)
            invalid[0]['metadata']['weather_series']['daily_eto0_mean_mm'] = [1.] * 366
            with self.assertRaisesRegex(ValueError, 'weather_size'):
                write(invalid)
            self.assertEqual(io.read(path)['samples'], compact)

    def test_streamed_header_is_finalized_after_row_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            value = self.fixture()
            value['count_from_stream'] = 0
            def rows():
                for sample in value['samples']:
                    value['count_from_stream'] += 1
                    yield sample
            path = Path(tmp)/'stream.parquet'
            io.write_rows(path, value, rows(), columns=['rain','temperature'], count=2, refresh_header=True)
            self.assertEqual(io.metadata(path)['count_from_stream'], 2)
            self.assertEqual(io.read(path), value)

    def test_compact_features_preserve_numbers_nulls_absences_and_share_immutable_batches(self):
        from copy import deepcopy
        from rainmapper_core.mushroom_ml_biology_v3_evaluation import _eligible_samples
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'compact.parquet'
            original = self.fixture()
            # More than one read batch, so row offsets must not leak across it.
            original['samples'] = deepcopy(original['samples'] * 130)
            for index, row in enumerate(original['samples']):
                row['predictive_features']['rain'] = index + .123456789123
                row['metadata'].update(species_id='synthetic', area_id='area',
                                       validation_group_7d='g7', validation_group_14d='g14')
            io.write(path, original)
            compact = io.read(path, compact_features=True)
            self.assertEqual(compact, original)
            features = compact['samples'][0]['predictive_features']
            self.assertIsInstance(features, io.ColumnarFeatures)
            self.assertIs(deepcopy(features), features)
            self.assertIs(features._values, compact['samples'][1]['predictive_features']._values)
            self.assertIsNot(features._values, compact['samples'][128]['predictive_features']._values)
            with self.assertRaises(TypeError):
                features['rain'] = 5
            with self.assertRaises(ValueError):
                features._values[0, 0] = 5
            eligible = _eligible_samples(compact)
            self.assertIs(eligible[0]['predictive_features'], features)
            self.assertEqual(eligible, _eligible_samples(original))
            import numpy as np
            from rainmapper_core.mushroom_ml_holdout import matrix
            for columns in (['temperature','rain'], ['rain'], ['missing','rain']):
                a = matrix(eligible, columns); b = matrix(_eligible_samples(original), columns)
                np.testing.assert_equal(a[0], b[0]); np.testing.assert_equal(a[1], b[1])
                self.assertEqual(features.values_for(columns),
                                 [original['samples'][0]['predictive_features'].get(c) for c in columns])
            self.assertEqual(features.values_for(['temperature']), [None])
            for columns in ([], list(features), ['temperature'], ['unknown'], ['rain', 'unknown']):
                self.assertEqual(features.contains_all(columns), set(columns).issubset(features))
            lean = io.read(path, compact_features=True, sample_projection=io.fit_sample)
            self.assertEqual(lean['samples'], [io.fit_sample(s) for s in compact['samples']])
            self.assertEqual(_eligible_samples(lean), [io.fit_sample(s) for s in eligible])
            projected = io.read(path, feature_columns=['temperature'], compact_features=True)
            self.assertIsNone(projected['samples'][0]['predictive_features']['temperature'])
            self.assertNotIn('temperature', projected['samples'][1]['predictive_features'])
            destination = Path(tmp)/'roundtrip.parquet'
            io.write(destination, compact)
            self.assertEqual(io.read(destination), original)

    def test_streamed_rows_match_materialized_and_reject_schema_or_count_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            value = self.fixture()
            path = Path(tmp)/'stream.parquet'
            header = {k:v for k,v in value.items() if k != 'samples'}
            io.write_rows(path, header, iter(value['samples']), columns=['rain','temperature'], count=2)
            self.assertEqual(io.read(path), value)
            rows = io.SampleRows(path)
            self.assertEqual(len(rows), len(value['samples']))
            self.assertEqual(list(rows), value['samples'])
            self.assertEqual(list(rows), value['samples'])
            for columns, count, reason in ((['rain'], 2, 'undeclared'),
                                           (['rain','temperature'], 1, 'count_mismatch'),
                                           (['rain','temperature'], 3, 'count_mismatch')):
                with self.assertRaisesRegex(ValueError, reason):
                    io.write_rows(path, header, iter(value['samples']), columns=columns, count=count)
                self.assertEqual(io.read(path), value)

    def fixture(self):
        return {'feature_set': {'profiles': {'short': ['rain'], 'long': ['rain','temperature']}},
                'water_state_contract_id': 'test-contract', 'samples': [
                    {'sample_id': 'one', 'prediction_target': 'favorable',
                     'metadata': {'target_date':'2026-09-01','nested':{'horizon':7}},
                     'quality': {'training_eligible':True},
                     'predictive_features': {'rain':12.123456789123, 'temperature':None}},
                    {'sample_id': 'two', 'prediction_target': 'unfavorable',
                     'metadata': {'target_date':'2025-09-01'}, 'quality':{},
                     'predictive_features': {'rain':0.0}}]}

    def test_full_roundtrip_preserves_nulls_missing_keys_and_unrounded_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'features.parquet'
            value = self.fixture()
            io.write(path,value)
            self.assertEqual(io.read(path),value)
            self.assertEqual(io.metadata(path),{k:v for k,v in value.items() if k != 'samples'})

    def test_projection_reads_only_requested_features_and_rejects_unknown_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'features.parquet'; value = self.fixture()
            io.write(path,value)
            projected = io.read(path,feature_columns=['rain'])
            for expected,actual in zip(value['samples'],projected['samples']):
                self.assertEqual(actual,{**expected,'predictive_features':{'rain':expected['predictive_features']['rain']}})
            with self.assertRaisesRegex(ValueError,'column_missing'):
                io.read(path,feature_columns=['invented'])

    def test_default_json_compatibility_and_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'features.json'; value=self.fixture()
            io.write(path,value)
            self.assertEqual(io.read(path),value)
            with patch.object(io,'MAX_FILE_BYTES',1):
                with self.assertRaisesRegex(ValueError,'file_limit'):
                    io.read(path)
            with patch.object(io,'MAX_ROWS',1):
                with self.assertRaisesRegex(ValueError,'row_limit'):
                    io.write(Path(tmp)/'too-many.parquet',value)

    def test_large_soil_catalog_is_data_and_preserves_both_model_consumers(self):
        import pyarrow.parquet as pq
        contract = v4.FIXED_GAP_7D_BIOLOGY_V4_ID
        columns = v4.predictive_columns(contract, 'soil_water')
        variant = physical.SOIL_VARIANT_ID
        value = self.fixture()
        value.update(temporal_contract_id=contract,
                     feature_blocks={'soil_water': list(columns)})
        state = {'predictive_features': {f.name: 41.123456789 for f in v4.SOIL_WATER_FIELDS},
                 'quality': {'training_eligible': True},
                 'metadata': {'diagnostics': 'test' * 1024}}
        catalog = {f'area|{i}': state for i in range(600)}
        value['soil_variants'] = {variant: {'profile_depth_cm': 30, 'area_state_catalog': catalog},
                                 'empty': {'area_state_catalog': {}}}
        for index, sample in enumerate(value['samples']):
            sample['predictive_features'] = {name: .125 for name in columns}
            sample['quality'].update(eligibility_by_block={'climatic_balance': True},
                                     source_v3_quality={'training_eligible': True})
            sample['metadata']['soil_state_key'] = f'area|{index}'
        self.assertGreater(len(json.dumps(catalog).encode()), io.MAX_METADATA_BYTES)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'v4.parquet'
            io.write(path, value)
            stored = pq.ParquetFile(path)
            self.assertLess(len(stored.schema_arrow.metadata[io.METADATA_KEY]), 10000)
            self.assertEqual(stored.metadata.num_rows, 602)
            self.assertEqual(io.metadata(path)['soil_variants'][variant]['area_state_catalog'], {})
            restored = io.read(path)
            self.assertEqual(restored, value)
            expected = v4.materialize_comparison_benchmark(value, profile_id=variant)
            self.assertEqual(expected['training_eligible_sample_count'], 2)
            self.assertEqual(v4.materialize_comparison_benchmark(restored, profile_id=variant), expected)
            self.assertEqual(physical.materialize_benchmark(restored), physical.materialize_benchmark(value))
            self.assertEqual(len(catalog), 600)  # source was not mutated

    def test_catalog_and_metadata_limits_preserve_previous_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'features.parquet'
            original = self.fixture()
            io.write(path, original)
            value = self.fixture()
            value['soil_variants'] = {'soil': {'area_state_catalog': {'a': {'state': 1}, 'b': {'state': 2}}}}
            with patch.object(io, 'MAX_CATALOG_ROWS', 1):
                with self.assertRaisesRegex(ValueError, 'catalog_row_limit'):
                    io.write(path, value)
            value['oversized_header'] = 'x' * (io.MAX_METADATA_BYTES + 1)
            with self.assertRaisesRegex(ValueError, 'metadata_limit'):
                io.write(path, value)
            self.assertEqual(io.read(path), original)


if __name__ == '__main__':
    unittest.main()
