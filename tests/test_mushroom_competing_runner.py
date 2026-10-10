import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_ml_benchmark_io as io
from rainmapper_core import mushroom_competing_evidence as evidence
from tests import test_mushroom_competing_history as fixture
from tests.test_mushroom_competing_history import REF as HISTORY_REF


class RunnerTests(unittest.TestCase):
    def test_absence_audit_is_lossless_and_bounded_before_writing(self):
        import gzip
        import os
        runner = self.load_runner()
        raw = b'{"missing":["example",7,"temporal_episode_boundary"]}\n' * 200000
        self.assertGreater(len(raw), 8 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'audit.jsonl.gz'
            with runner.AbsenceAudit(path) as audit:
                for offset in range(0,len(raw),10000):
                    audit.write(raw[offset:offset+10000])
            self.assertEqual(gzip.decompress(path.read_bytes()),raw)
            self.assertLess(path.stat().st_size,8*1024*1024)
            with patch.object(runner.AbsenceAudit,'MAX_RAW',5):
                with self.assertRaisesRegex(ValueError,'history_audit_limit'):
                    with runner.AbsenceAudit(path) as audit:
                        audit.write(b'123456')
            with patch.object(runner.AbsenceAudit,'MAX_PACKED',128):
                with self.assertRaisesRegex(ValueError,'history_audit_limit'):
                    with runner.AbsenceAudit(path) as audit:
                        audit.write(os.urandom(10000))
                self.assertLessEqual(path.stat().st_size,128)

    def test_feature_budget_uses_actual_columns_and_keeps_limit_for_wide_models(self):
        runner = self.load_runner()
        # 5,000 visits with seven lag rows and the installed 90-day column
        # envelope fit the existing numeric matrix budget; full-year models do not.
        self.assertEqual(runner.check_feature_plan(5000, {'lag': range(460)}),
                         {'planned_matrix_columns':460, 'planned_matrix_bytes':144900000})
        with self.assertRaisesRegex(ValueError, 'feature_plan_limit'):
            runner.check_feature_plan(5000, {'lag': range(2930)})

    def load_runner(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/run-mushroom-competing-history.py'
        loader = importlib.util.spec_from_file_location('competing_runner_test', script)
        runner = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(runner)
        return runner

    def test_builder_progress_forwards_counters_and_identifies_failure(self):
        runner = self.load_runner()
        events = []
        def builder():
            print(json.dumps({'cached_microareas': 5, 'total_microareas': 10}))
            print(json.dumps({'completed_area_cutoffs': 25, 'total_area_cutoffs': 100}))
            print(json.dumps({'report': 'x' * 10000}))
            print(json.dumps({'completed_area_cutoffs': 100, 'total_area_cutoffs': 100}))
            raise ValueError('benchmark_metadata_limit')
        argv = runner.sys.argv
        with patch.object(runner.runpy, 'run_path', return_value={'main': builder}):
            with self.assertRaisesRegex(RuntimeError, 'V4 fixed: benchmark_metadata_limit'):
                runner.run_builder('fixture.py', [], progress=events.append,
                                   label='V4 fixed', start=13, end=20)
        self.assertIs(runner.sys.argv, argv)
        self.assertEqual(len(events), 4)
        self.assertEqual(events[1]['message'], 'weather microareas: 5/10')
        self.assertEqual(events[-1]['message'], 'soil states: 100/100')
        self.assertIn('100/100', events[-1]['phase'])
        self.assertGreater(events[-1]['overall_percent'], 19)

    def test_job_progress_keeps_global_percent_through_nested_steps(self):
        runner = self.load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'progress.jsonl'
            progress = runner.JobProgress(path)
            for event in ({'overall_percent':35}, {'overall_percent':42},
                          {'phase':'Preparing historical complete weeks','completed_visits_in_unit':1},
                          {'overall_percent':36}, {'overall_percent':90}):
                progress(event)
            events = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual([e['overall_percent'] for e in events],[35,42,42,42,90])
        self.assertEqual(events[2]['completed_visits_in_unit'],1)

    def test_full_feature_chain_runs_real_builders_and_records_v5_provenance(self):
        from rainmapper_core import mushroom_ml_weather_workspace as workspace
        from rainmapper_core import mushroom_ml_biology_v3 as v3
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
        from tests import test_mushroom_water_unification as water
        from tests import test_mushroom_ml_biology_v3 as observations
        fixture = water.WaterUnificationTests()
        fixture.setUp()
        self.addCleanup(workspace.clear_active_workspace)
        runner = self.load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'observations.json').write_text(json.dumps({'observations': [
                observations.MushroomMLBiologyV3Tests().observation('synthetic',
                    micro_area_id='micro', observed_at=fixture.end.isoformat())]}))
            (root/'sites.json').write_text(json.dumps({
                'areas': [{'area_id': 'area', 'representative_location': {'lat': 42., 'lon': 2.}}],
                'micro_areas': [{'micro_area_id': 'micro', 'area_id': 'area', 'derived_context': {
                    'soilgrids_water': fixture.context.soilgrids_water}}]}))
            (root/'features.json').write_text(json.dumps({'rows': [
                {'micro_area_id': 'micro', 'gis_altitude_m': 1000.}]}))
            (root/'stations.txt').write_text('')
            spec = {'observations_path': 'observations.json', 'known_sites_path': 'sites.json',
                    'stations_path': 'stations.txt', 'observation_features_path': 'features.json',
                    'weather_data_dir': 'weather', 'references': [
                        {**fixture_ref, 'temporal_contract_id': prefix + suffix}
                        for prefix in ('fixed_gap_7d', 'lag_event')
                        for fixture_ref, suffix in [
                            ({**HISTORY_REF,
                              'profile_id': 'common_idw_plus_physical_state'}, '_biology_v3'),
                            ({**HISTORY_REF,
                              'version_id': 'biology_v6_smooth_hierarchical',
                              'profile_id': 'smooth_weather_physical_state',
                              'estimator_id': 'smooth_species_logistic_v1'}, '_biology_v6_smooth_hierarchical_v2'),
                        ]],
                    'revision': 'a'*64, 'procedure_revision': runner.implementation_id(),
                    'manifest': {'snapshot_id': 'synthetic-snapshot'}}
            events = []
            with (patch.object(workspace.weather_context, 'load_stations_catalog', return_value=__import__('pandas').DataFrame([
                      {'source':'meteocat','station_code':'W','lat':42.,'lon':2.}])),
                  patch.object(workspace.weather_context, 'load_daily_weather_parquet', return_value=fixture.stations),
                  patch.object(v3, 'load_micro_area_contexts', return_value={'micro': fixture.context})):
                prepared = runner.build_features(root, root/'history-inputs', spec, events.append)
            self.assertEqual(set(prepared), {'v3_fixed','v3_lag','v4_fixed','v4_lag','v5_fixed','v5_lag'})
            inputs = {name: io.read(path) for name,path in prepared.items()}
            self.assertTrue(all(value['samples'] for value in inputs.values()))
            original_profiles = trainer.materialize_runtime_benchmarks(**inputs)
            projected_inputs = {name:io.read(path, compact_features=True,
                sample_projection=io.fit_sample if name.startswith('v5_') else io.historical_source_sample)
                for name,path in prepared.items()}
            projected_profiles = trainer.materialize_runtime_benchmarks(**projected_inputs)
            self.assertEqual(set(projected_profiles),set(original_profiles))
            from rainmapper_core.mushroom_competing_history import SOURCE_FIELDS
            for name, original in original_profiles.items():
                projected = projected_profiles[name]
                requested = trainer.materialize_runtime_benchmarks(**projected_inputs, requested_keys={name})
                self.assertEqual(set(requested),{name})
                self.assertEqual(requested[name],projected)
                self.assertEqual(original['feature_set'],projected['feature_set'])
                for before,after in zip(original['samples'],projected['samples'],strict=True):
                    self.assertEqual(dict(before['predictive_features']),dict(after['predictive_features']))
                    self.assertEqual(before['prediction_target'],after['prediction_target'])
                    for field in SOURCE_FIELDS:
                        self.assertEqual(before['metadata'].get(field),after['metadata'].get(field))
                    self.assertEqual(before['quality'].get('training_eligible'),after['quality'].get('training_eligible'))
                    self.assertEqual(before['quality'].get('training_exclusion_reasons'),after['quality'].get('training_exclusion_reasons'))
            manifest_path = root/'history-inputs/MANIFEST.json'
            manifest = json.loads(manifest_path.read_bytes())
            self.assertEqual(manifest['source_snapshot_id'], 'synthetic-snapshot')
            self.assertEqual(len(manifest['files']), 4)
            for name, entry in manifest['files'].items():
                self.assertEqual(entry['sha256'], hashlib.sha256((manifest_path.parent/name).read_bytes()).hexdigest())
            build = json.loads((root/'history-inputs/raw/MANIFEST.build.json').read_bytes())
            self.assertEqual(build['source_snapshot_manifest_sha256'], hashlib.sha256(manifest_path.read_bytes()).hexdigest())
            self.assertEqual(build['source_snapshot'], str(manifest_path.parent))
            self.assertEqual(events[-1]['overall_percent'], 35)
            self.check_v6_historical_profiles(root, prepared)
            # Real runtime adapters for neighbouring dates must use only weather
            # before each issued week. No additional model training is needed.
            from rainmapper_core import mushroom_competing_panels as panels
            from rainmapper_core import mushroom_ml_model_catalog as catalog
            from tests.test_mushroom_competing_history import REF as history_reference
            from datetime import date, timedelta
            store = panels.Panels(root/'panels.sqlite')
            self.addCleanup(store.close)
            with patch.object(v3, 'load_micro_area_contexts', return_value={'micro': fixture.context}):
                builder = panels.Builder(store=store, known_sites=root/'sites.json', data_dir=root/'weather',
                    stations_file=root/'stations.txt', profiles=[{'version_id':'biology_v3','profile_id':'core',
                        'input_requirements':{'weather_lookback_days':90,'include_physical_state':False}}], progress=events.append)
            for temporal, expected_count in [('fixed',13), ('lag',49)]:
                ref = catalog.ModelArtifactRef.from_mapping({**history_reference,
                    'temporal_contract_id':('fixed_gap_7d' if temporal=='fixed' else 'lag_event')+'_biology_v3'})
                sample = io.read(prepared['v3_'+temporal])['samples'][0]
                generated = list(builder.samples(ref, [sample]))
                self.assertEqual(len(generated), expected_count)
                target = date.fromisoformat(sample['metadata']['target_date'])
                self.assertTrue(all(day-timedelta(days=h) < target for _,_,day,h,_ in generated))
                self.assertEqual(len(builder.fingerprint(ref, [sample])),64)

    def check_v6_historical_profiles(self, root, prepared):
        """Consume actual V5 files in every V6 profile/temporal/estimator branch."""
        from rainmapper_core import mushroom_competing_history as history
        from rainmapper_core import mushroom_ml_model_catalog as catalog
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
        from rainmapper_core import mushroom_ml_raw_weather as raw
        from rainmapper_core import mushroom_ml_holdout as holdout
        profiles = [('biology_v6_smooth_hierarchical', 'smooth_weather_physical_state')]
        profiles += [(smooth.WINDOWED_VERSION_ID, smooth.windowed_profile_id(days)) for days in raw.WINDOW_DAYS_OPTIONS]
        combinations = 0
        with history.UnitCache(root/'v6-synthetic.sqlite') as cache:
            for temporal, prefix in [('fixed', 'fixed_gap_7d'), ('lag', 'lag_event')]:
                for version, profile in profiles:
                    for estimator in ('smooth_species_logistic_v1', 'smooth_shared_logistic_v1',
                                      'smooth_partial_pooling_logistic_v1'):
                        ref = catalog.ModelArtifactRef.from_mapping({
                            'batch_id':'synthetic', 'generation_id':'synthetic_v6', 'version_id':version,
                            'temporal_contract_id':prefix+'_biology_v6_smooth_hierarchical_v2',
                            'profile_id':profile, 'estimator_id':estimator,
                            'species_id':'boletus_aereus' if estimator=='smooth_species_logistic_v1' else 'all_species'})
                        columns = trainer._columns(ref, io.metadata(prepared['v5_'+temporal]))
                        source = io.read(prepared['v5_'+temporal], feature_columns=columns)
                        self.assertTrue(set(columns).issubset(source['samples'][0]['predictive_features']))
                        rows = []
                        for index in range(11):
                            day = f'2024-{3+index//2:02d}-01' if index<8 else '2025-06-01'
                            row = fixture.sample('v6-'+str(index), day,
                                target='favorable' if index//2%2 else 'unfavorable',
                                sid=('boletus_edulis' if index in (6,7,10) else
                                     'boletus_aereus' if index%2==0 else 'amanita_caesarea'))
                            row['predictive_features'] = {c:float(index+1)/20 for c in columns}
                            row['predictive_features'].update({'horizon_days':7.} if temporal=='lag' else {})
                            rows.append(row)
                        self.assertTrue(holdout._inner_splits(rows[:8], 14))
                        benchmark = {**source, 'samples':rows}
                        arguments = dict(cutoff='2026-10-05', implementation_id='synthetic-v6',
                                         cache=cache, targets={'boletus_aereus','amanita_caesarea','boletus_edulis'})
                        units = list(history.evaluate_benchmark(benchmark, [ref.as_dict()], **arguments))
                        predictions = [r for unit in units for r in unit['rows']]
                        self.assertEqual(len(predictions), 1 if ref.species_id!='all_species' else 3)
                        self.assertTrue(all(0<=row[5]<=1 for row in predictions))
                        self.assertIsNotNone(units[-1]['fit_config'])
                        if ref.species_id == 'all_species':
                            audit = units[-1]['tuning_diagnostics']
                            self.assertEqual(audit['inner_splits'], 2)
                            self.assertEqual(audit['used_inner_splits'], 1)
                            self.assertEqual(audit['unsupported_validation_occurrences_by_species'],
                                             {'boletus_edulis': 4})
                            self.assertFalse(audit['default_used'])
                            self.assertIn('boletus_edulis', {row[0] for row in predictions})
                        with patch.object(history, 'fit_temporal_unit', side_effect=AssertionError('must reuse SQLite')):
                            cached = list(history.evaluate_benchmark(benchmark, [ref.as_dict()], **arguments))
                        self.assertTrue(all(unit['reused'] for unit in cached))
                        self.assertEqual(cached[-1]['tuning_diagnostics'], units[-1]['tuning_diagnostics'])
                        combinations += 1
        self.assertEqual(combinations, 24)

    def test_parquet_inputs_temporal_fits_sqlite_reuse_and_bounded_delivery(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/run-mushroom-competing-history.py'
        loader = importlib.util.spec_from_file_location('competing_runner_test', script)
        runner = importlib.util.module_from_spec(loader); loader.loader.exec_module(runner)
        current_producer = runner.implementation_id()
        previous_producer = runner.history.COMPATIBLE_ROW_PROCEDURES[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / 'snapshot/inputs/extra'; inputs.mkdir(parents=True)
            matrix = root / 'synthetic.parquet'
            benchmark = fixture.HistoryTests().benchmark()
            for sample in benchmark['samples']:
                sample['metadata']['area_id'] = 'synthetic-area'
            io.write(matrix, benchmark)
            REF = fixture.REF
            spec = {'kind':'competing_history_job_v1','cutoff':'2026-10-05',
                    'references':[REF], 'species_ids':['boletus_aereus'],
                    'revision':'a'*64,'procedure_revision':previous_producer,
                    'manifest':{'batch_id':'b','snapshot_id':'s','quality_catalog':{'sha256':'q'}},
                    'eligible_candidates':[['boletus_aereus',[REF['version_id'],REF['profile_id'],
                        REF['temporal_contract_id'],7,REF['estimator_id']]]]}
            spec.update(history_revision='b'*64, comparison_k=4, profiles={}, recommendation_policy={},
                        prediction_model_suspensions=[], catalog_profiles=[],
                        observations_path='observations.json', known_sites_path='sites.json',
                        weather_data_dir='weather', stations_path='stations.txt')
            (root/'observations.json').write_text(json.dumps({'observations': []}))
            (inputs/'competing-spec.json').write_text(json.dumps(spec))
            output = root / 'result.json'
            arguments = ['runner','--input-dir',str(root),'--cache-dir',str(root/'cache'),
                         '--output',str(output),'--progress-jsonl',str(root/'progress.jsonl')]
            with patch.object(runner.sys,'argv',arguments), \
                 patch.object(runner, 'implementation_id', return_value=previous_producer) as producer, \
                 patch.object(runner,'build_features',return_value={'v3_fixed':matrix}) as prepare, \
                 patch('rainmapper_core.mushroom_competing_panels.Builder') as builder:
                builder.return_value.fingerprint.return_value = 'synthetic-panels'
                builder.return_value.input_fingerprint.return_value = 'synthetic-panel-inputs'
                self.assertEqual(runner.main(),0)
                result = evidence.validate(json.loads(output.read_bytes()))
                self.assertEqual(result['summary']['computed_units'],3)
                self.assertEqual(result['summary']['missing_rows'],2)
                self.assertEqual(len(evidence.cell_rows(result)),2)
                self.assertIn('history', result['comparisons'][0])
                self.assertEqual(runner.main(),0)
                reused = json.loads(output.read_bytes())
                self.assertEqual(reused['summary']['computed_units'],0)
                self.assertEqual(reused['summary']['reused_units'],3)
                self.assertEqual(list(evidence.cell_rows(reused)),list(evidence.cell_rows(result)))
                self.assertEqual(prepare.call_count, 1)
                self.assertEqual(set(reused['comparisons'][0]['species']['boletus_aereus']['methods']),
                                 {'habitual','A','B','C','D'})
                spec['comparison_k'] = 2
                spec['revision'] = 'c'*64
                (inputs/'competing-spec.json').write_text(json.dumps(spec))
                self.assertEqual(runner.main(),0)
                self.assertEqual(prepare.call_count, 1, 'Changing K must not prepare weather or fit models')
                self.assertEqual(json.loads(output.read_bytes())['comparisons'][0]['k'], 2)
                # An aggregation-only upgrade must reuse the binary-key units
                # produced by the deployed runner, without refitting any model.
                producer.return_value = current_producer
                spec.update(procedure_revision=current_producer, history_revision='d'*64, revision='e'*64)
                (inputs/'competing-spec.json').write_text(json.dumps(spec))
                with patch.object(runner.history, 'fit_temporal_unit', side_effect=AssertionError('duplicate fit')):
                    self.assertEqual(runner.main(), 0)
                upgraded = json.loads(output.read_bytes())
                self.assertEqual(upgraded['summary']['computed_units'], 0)
                self.assertEqual(upgraded['summary']['reused_units'], 3)
                self.assertEqual(list(evidence.cell_rows(upgraded)), list(evidence.cell_rows(result)))
                builder.return_value.fingerprint.assert_not_called()
                spec['procedure_revision'] = 'f'*64
                (inputs/'competing-spec.json').write_text(json.dumps(spec))
                with self.assertRaisesRegex(ValueError,'code_mismatch'):
                    runner.main()


if __name__ == '__main__':
    unittest.main()
