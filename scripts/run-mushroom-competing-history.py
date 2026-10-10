#!/usr/bin/env python3
"""Prepare/update temporal selection evidence in an isolated worker directory."""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import redirect_stdout
from datetime import date
import gc
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# This process shares a worker with interactive inference.
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

from rainmapper_core import mushroom_competing_history as history
from rainmapper_core import mushroom_competing_evidence as evidence

# Reviewed numerical equivalence: exact CURRENT tensor/week fingerprints are
# still required before reading either historical producer's units. The second
# revision was checked on all 990 units and all 184 visits, not a snapshot alias.
COMPATIBLE_VALIDATION_PROCEDURES = (
    'ce683820f90f3e87cb2e8cdee471ba4ff466acbd6f4bab468d79555965b8cdd5',
    'a36878ced3018d2d38432befcd06105f9947e684de8770c75725bb64fd93a4e1',
)


class JobProgress:
    def __init__(self, path):
        self.path, self.percent = path, 0

    def __call__(self, event):
        self.percent = max(self.percent, min(95, float(event.get('overall_percent', self.percent))))
        with self.path.open('a') as stream:
            stream.write(json.dumps({**event, 'overall_percent': self.percent}, separators=(',', ':')) + '\n')


class AbsenceAudit:
    """Lossless streaming gzip; private diagnostics keep their 8 MiB disk cap."""
    MAX_PACKED = 8 * 1024 * 1024
    MAX_RAW = 128 * 1024 * 1024

    def __init__(self, path):
        self.stream = path.open('wb')
        self.codec = zlib.compressobj(1, zlib.DEFLATED, 31)
        self.raw_size = 0

    def __enter__(self):
        return self

    def _write(self, chunk):
        if self.stream.tell() + len(chunk) > self.MAX_PACKED:
            raise ValueError('history_audit_limit')
        self.stream.write(chunk)

    def write(self, raw):
        self.raw_size += len(raw)
        if self.raw_size > self.MAX_RAW:
            raise ValueError('history_audit_limit')
        self._write(self.codec.compress(raw))

    def __exit__(self, *args):
        try:
            self._write(self.codec.flush())
        finally:
            self.stream.close()


def read_json(path, max_bytes):
    with path.open('rb') as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError('history_input_size_limit')
    return json.loads(raw)


def contained(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('history_input_path_escape')
    return path


class BuilderProgress:
    """Forward small builder counters without retaining their final reports."""
    def __init__(self, progress, label, start, end):
        self.progress, self.label, self.start, self.end = progress, label, start, end
        self.pending = ''
        self.discard = False
        self.percent = start

    def write(self, text):
        for index, part in enumerate(text.split('\n')):
            if index:
                if not self.discard:
                    self.report(self.pending)
                self.pending, self.discard = '', False
            if len(self.pending) + len(part) > 8192:
                self.pending, self.discard = '', True
            if not self.discard:
                self.pending += part
        return len(text)

    def flush(self):
        pass

    def report(self, line):
        try:
            event = json.loads(line)
        except ValueError:
            return
        if not isinstance(event, dict):
            return
        for done, total, label, base, span in (
                ('cached_microareas', 'total_microareas', 'weather microareas', 0, .25),
                ('completed_area_cutoffs', 'total_area_cutoffs', 'soil states', .25, .7),
                ('materialized_area_cutoffs', 'total_area_cutoffs', 'weather windows', .25, .7)):
            if done in event and total in event:
                fraction = base + span * min(1, event[done] / max(1, event[total]))
                self.percent = max(self.percent, round(self.start + (self.end - self.start) * fraction, 1))
                message = f'{label}: {event[done]}/{event[total]}'
                self.progress({'phase': f'{self.label} · {message}',
                    'message': message,
                    'overall_percent': self.percent})
                break


def run_builder(name, arguments, *, progress, label, start, end):
    original = sys.argv
    progress({'phase': label, 'overall_percent': start})
    try:
        sys.argv = [name, *map(str, arguments)]
        with redirect_stdout(BuilderProgress(progress, label, start, end)):
            result = runpy.run_path(str(ROOT / 'scripts' / name))['main']()
        if result not in (None, 0):
            raise RuntimeError('history_feature_preparation_failed')
        progress({'phase': label, 'message': 'Completed', 'overall_percent': end})
    except Exception as exc:
        raise RuntimeError(f'{label}: {exc}') from exc
    finally:
        sys.argv = original


def raw_feature_plan(references):
    """Plan only columns consumed by installed raw-weather model profiles."""
    from rainmapper_core import mushroom_ml_runtime_trainer as trainer
    from rainmapper_core import mushroom_ml_model_catalog as catalog
    from rainmapper_core import mushroom_ml_raw_weather as raw_weather
    selected = {}
    for contract in (raw_weather.FIXED_CONTRACT_ID, raw_weather.LAG_CONTRACT_ID):
        header = {'feature_set': raw_weather.feature_set_contract(contract)}
        columns = set()
        for ref in references:
            if (('v5' in ref['version_id'] or 'v6' in ref['version_id']) and
                    ref['temporal_contract_id'].startswith('lag_') == contract.startswith('lag_')):
                columns.update(trainer._columns(catalog.ModelArtifactRef.from_mapping(ref), header))
        selected[contract] = sorted(columns)
    return selected


def check_feature_plan(observation_count, raw_columns):
    # Fixed and lag matrices are consumed separately. Raw rows retain typed
    # float64 numbers + null masks, not one Python dict/float per matrix cell.
    # Bound the widest live matrix before any weather/features are built.
    columns = max([44, *(len(c) for c in raw_columns.values())])
    estimated = observation_count * 7 * columns * 9
    if estimated > history.MAX_MATRIX_BYTES:
        raise ValueError('history_feature_plan_limit')
    return {'planned_matrix_columns': columns, 'planned_matrix_bytes': estimated}


def build_features(root, output, spec, progress):
    """Reuse production feature builders, without hold-out or operational fits."""
    from rainmapper_core import mushroom_ml_weather_workspace as weather
    paths = {k: contained(root, spec[k]) for k in ('observations_path', 'known_sites_path',
            'stations_path', 'observation_features_path', 'weather_data_dir')}
    observations = read_json(paths['observations_path'], 16 * 1024 * 1024)['observations']
    if not isinstance(observations, list) or len(observations) > 10000:
        raise ValueError('history_observation_limit')
    selected = raw_feature_plan(spec['references'])
    plan = check_feature_plan(len(observations), selected)
    del observations  # Builders read bounded projections; do not retain the source again.
    progress({'phase': 'Planning historical features', **plan})
    weather.clear_active_workspace()
    weather.activate_operational_workspace(data_dir=paths['weather_data_dir'],
        observations=paths['observations_path'], known_sites=paths['known_sites_path'],
        stations_file=paths['stations_path'], max_horizon_days=13, compact_series=True)
    common = ['--data-dir', paths['weather_data_dir'], '--known-sites', paths['known_sites_path'],
              '--stations-file', paths['stations_path']]
    result = {}
    versions = {r['version_id'] for r in spec['references']}
    needs_raw = any('v5' in v or 'v6' in v for v in versions)
    needs_v4 = 'biology_v4' in versions or any(r['profile_id'] == 'common_idw_plus_physical_state'
                                             for r in spec['references'])
    output.mkdir(parents=True, exist_ok=True)
    for temporal, contract in [('fixed', 'fixed_gap_7d_biology_v3'), ('lag', 'lag_event_biology_v3')]:
        start = 10 if temporal == 'fixed' else 20
        path = output / ('v3-' + temporal + '.parquet')
        run_builder('build-biology-v3-benchmark.py', [*common, '--observations', paths['observations_path'],
                    '--observation-features', paths['observation_features_path'],
                    '--feature-set', contract, '--output', path, '--historical-inputs'], progress=progress,
                    label=f'Preparing historical V3 ({temporal})', start=start, end=start + 3)
        result['v3_' + temporal] = path
        if needs_v4:
            v4 = output / ('v4-' + temporal + '.parquet')
            run_builder('build-biology-v4-benchmark.py', [*common, '--v3-benchmark', path, '--output', v4, '--training-only'],
                        progress=progress, label=f'Preparing historical V4 ({temporal})',
                        start=start + 3, end=start + 10)
            result['v4_' + temporal] = v4
    if needs_raw:
        column_plan = output / 'raw-feature-columns.json'
        column_plan.write_bytes(history.canonical(selected))
        # V5 consumes the provenance of the V3/V4 snapshot. Build it from the
        # actual files, just as the operational input preparer does.
        files = {}
        for path in result.values():
            with path.open('rb') as stream:
                files[path.name] = {'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(),
                                    'size_bytes': path.stat().st_size}
        (output / 'MANIFEST.json').write_text(json.dumps({
            'kind': 'competing_history_feature_snapshot_v1',
            'revision': spec['revision'], 'procedure_revision': spec['procedure_revision'],
            'source_snapshot_id': spec['manifest']['snapshot_id'], 'files': files,
        }, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
        run_builder('build-biology-v5-raw-benchmark.py', [*common, '--v3-fixed', result['v3_fixed'],
                    '--v3-lag', result['v3_lag'], '--output-dir', output / 'raw', '--output-format', 'parquet',
                    '--training-only', '--feature-columns-json', column_plan],
                    progress=progress, label='Preparing historical V5 weather windows', start=30, end=35)
        result.update(v5_fixed=output / 'raw/biology-v5-fixed.parquet', v5_lag=output / 'raw/biology-v5-lag.parquet')
    return result


def implementation_id():
    # Include local production builders/trainers; a code change cannot silently
    # reuse an old method's statistics. This is independent of installed weights.
    from rainmapper_core.mushroom_competing_inputs import procedure_revision
    return procedure_revision()


def prepare_generation(root, spec, cache_dir, progress, panels, code_id, *, deferred=False):
    prepared = build_features(root, root / 'history-inputs', spec, progress)
    from rainmapper_core import mushroom_ml_runtime_trainer as trainer
    from rainmapper_core import mushroom_ml_benchmark_io as benchmark_io
    from rainmapper_core import mushroom_ml_model_catalog as catalog
    from rainmapper_core import mushroom_competing_panels as panel_cache
    builder = None
    fit_cache = None
    fit_scheduler = None
    prepared_cache = {}
    visits = {}; unit_index = set()
    def fit(ref, benchmark, train, test, key):
        if fit_scheduler is not None:
            return fit_scheduler.finish(ref,benchmark,train,test,key,panel_builder=builder,
                                        prepared_cache=prepared_cache,defer_panels=deferred)
        return history.fit_temporal_unit(ref, benchmark, train, test, key,
                                         panel_builder=builder, prepared_cache=prepared_cache, fit_cache=fit_cache,
                                         defer_panels=deferred)
    grouped = defaultdict(list)
    for ref in spec['references']:
        grouped[trainer.benchmark_key(ref['version_id'], ref['temporal_contract_id'], ref['profile_id'])].append(ref)
    def units(cache):
        from collections import deque
        pending_results = deque()
        finished_families = 0
        fractions = {}
        def publish(unit):
            if callable(unit): unit=unit()
            if unit['missing']:
                raw=history.canonical({k:unit[k] for k in ('family','year','unit_key','missing')})+b'\n'
                audit.write(raw)
            family=tuple(unit['family'][k] for k in ('version_id','profile_id','temporal_contract_id','estimator_id'))
            for sid,oid,*_ in unit['rows']:
                unit_index.add((sid,oid,family,unit['unit_key']))
            return unit
        def next_completed():
            from concurrent.futures import wait, FIRST_COMPLETED
            while True:
                for index, unit in enumerate(pending_results):
                    key = getattr(unit, 'unit_key', None)
                    record = fit_scheduler.pending.get(key) if fit_scheduler else None
                    if record is None or record[1] is None or record[1].done():
                        del pending_results[index]
                        return publish(unit)
                fit_scheduler.wait_ready()
        # Release each temporal source before reading the other one. Derived
        # profiles share samples where production contracts permit it.
        for temporal in ('lag', 'fixed'):
            if not any(refs[0]['temporal_contract_id'].startswith('lag_event_') == (temporal == 'lag')
                       for refs in grouped.values()):
                continue
            source_cache = {}
            def load_source(name):
                if name in source_cache:
                    return source_cache[name]
                path = prepared[name + '_' + temporal]
                columns = None
                if name == 'v5':
                    header = benchmark_io.metadata(path)
                    columns = set()
                    for refs in grouped.values():
                        ref = refs[0]
                        if (('v5' in ref['version_id'] or 'v6' in ref['version_id']) and
                                ref['temporal_contract_id'].startswith('lag_event_') == (temporal == 'lag')):
                            columns.update(trainer._columns(catalog.ModelArtifactRef.from_mapping(ref), header))
                value = benchmark_io.read(path, feature_columns=columns, compact_features=True,
                    sample_projection=benchmark_io.fit_sample if name == 'v5' else benchmark_io.historical_source_sample)
                # At most the three projected, columnar sources for ONE temporal
                # contract. Keep the original family/output order while avoiding
                # re-reading the same immutable Parquet and parsing its records.
                source_cache[name] = value
                return value
            current_source = 'v3'
            inputs = {'v3_' + temporal: load_source('v3')}
            for sample in inputs['v3_' + temporal]['samples']:
                m = sample['metadata']; sid = m['species_id']
                if sid in spec['species_ids'] and m['target_date'] < spec['cutoff'] and sample.get('prediction_target') in ('favorable', 'unfavorable'):
                    visits[sid, m['observation_id']] = {'id': m['observation_id'], 'species_id': sid,
                        'day': m['target_date'], 'y': int(sample['prediction_target'] == 'favorable'),
                        'group': m['validation_group_14d'], 'area': m['area_id']}
            for key, refs in sorted(grouped.items(), key=lambda item: (-int(item[1][0]['version_id'][9]) if item[1][0]['version_id'].startswith('biology_v') else 0, item[0])):
                is_lag = refs[0]['temporal_contract_id'].startswith('lag_event_')
                if is_lag != (temporal == 'lag'):
                    continue
                prepared_cache.clear()
                first = refs[0]
                source = ('v5' if 'v5' in first['version_id'] or 'v6' in first['version_id'] else
                          'v4' if first['version_id'] == 'biology_v4' or
                                  first['profile_id'] == 'common_idw_plus_physical_state' else 'v3')
                if current_source != source:
                    inputs.clear()
                    gc.collect()
                    inputs[source + '_' + temporal] = load_source(source)
                    current_source = source
                inputs.setdefault('v3_fixed', {'samples': [], 'feature_set': {}})
                inputs.setdefault('v3_lag', {'samples': [], 'feature_set': {}})
                benchmarks = trainer.materialize_runtime_benchmarks(**inputs, requested_keys={key})
                if key not in benchmarks:
                    raise ValueError('history_benchmark_missing')
                def unit_progress(event, group=key):
                    if 'completed' in event:
                        fractions[group] = max(fractions.get(group,0),event['completed']/max(1,event['total']))
                    completed = sum(len(grouped[g])*fraction for g,fraction in fractions.items())
                    progress({**event,'overall_percent':35+55*completed/len(spec['references']),
                              'completed_families':int(completed),'total_families':len(spec['references'])})
                builder.progress = unit_progress
                for unit in history.evaluate_benchmark(benchmarks[key], refs, cutoff=spec['cutoff'],
                        implementation_id=code_id, cache=cache, targets=set(spec['species_ids']), progress=unit_progress,
                        evaluate=fit, unit_context=builder.input_fingerprint if deferred else builder.fingerprint,
                        compatible_unit_context=builder.fingerprint if deferred else None,
                        fit_cache=fit_cache,
                        fit_scheduler=fit_scheduler,
                        fingerprint_rows=True, defer_results=fit_scheduler is not None,
                        compatible_row_implementation_ids=() if cache.prepared(code_id) else history.COMPATIBLE_ROW_PROCEDURES,
                        compatible_implementation_ids=() if cache.prepared(code_id) else COMPATIBLE_VALIDATION_PROCEDURES):
                    pending_results.append(unit)
                    if len(pending_results) >= (fit_scheduler.queue_limit if fit_scheduler else 1):
                        yield next_completed()
                del benchmarks
                fit_cache.sealed = None
                fit_cache.benchmark = fit_cache.row_fingerprints = None
                prepared_cache.clear()
                finished_families += len(refs)
                progress({'phase':'Historical family queued',
                          'queued_families':finished_families, 'total_families':len(spec['references']),
                          'input_cache':dict(builder.stats), 'fit_cache':dict(fit_cache.stats)})
            prepared_cache.clear()
            del inputs
            source_cache.clear()
            gc.collect()
        while pending_results:
            yield next_completed()
        progress({'phase':'Historical selection completed','overall_percent':90,
                  'completed_families':len(spec['references']),'total_families':len(spec['references'])})
    with AbsenceAudit(root / 'history-absences.jsonl.gz') as audit, history.UnitCache(cache_dir / 'units.sqlite') as cache:
        from rainmapper_core.mushroom_competing_features import Inputs
        from rainmapper_core.mushroom_competing_fits import Fits
        from rainmapper_core.mushroom_competing_inputs import runtime_feature_revision
        fit_cache = Fits(cache.db, code_id, compatible_producers=history.COMPATIBLE_ROW_PROCEDURES)
        from rainmapper_core.mushroom_competing_fit_scheduler import ProcessFitScheduler, worker_count
        if worker_count() > 1:
            fit_scheduler = ProcessFitScheduler(fit_cache, worker_count())
        builder = panel_cache.Builder(store=panels, known_sites=contained(root, spec['known_sites_path']),
            data_dir=contained(root, spec['weather_data_dir']), stations_file=contained(root, spec['stations_path']),
            profiles=spec['catalog_profiles'], progress=progress, inputs=Inputs(cache.db),
            input_revision=runtime_feature_revision())
        wanted = {(sid, tuple(candidate)) for sid, candidate in spec['eligible_candidates']}
        try:
            ordered = history.OrderedUnits(cache,grouped)
            for unit in units(cache):
                ordered.add(unit)
            result = evidence.summarize(ordered, manifest=spec['manifest'],
                                       revision=spec['revision'], cutoff=spec['cutoff'], wanted=wanted, private=deferred)
            # Every compatible old result has an exact current-key alias now.
            # Future observation edits cannot benefit from scanning those old
            # generations again; unchanged units resolve through the aliases.
            cache.mark_prepared(code_id)
        finally:
            if fit_scheduler is not None:
                fit_scheduler.close()
    from rainmapper_core.mushroom_competing_replay import pack_unit_index
    visit_rows = list(visits.values())
    return {'evidence': result, 'unit_index': pack_unit_index(unit_index, visit_rows), 'visits': visit_rows,
            **({'deferred_panels': True} if deferred else {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--cache-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--progress-jsonl', type=Path, required=True)
    args = parser.parse_args()
    root = args.input_dir.resolve()
    spec = read_json(root / 'snapshot/inputs/extra/competing-spec.json', 512 * 1024)
    if spec.get('kind') != 'competing_history_job_v1':
        raise ValueError('invalid_history_job_spec')
    date.fromisoformat(spec['cutoff'])
    if not 0 < len(spec['references']) <= 4096 or not 0 < len(spec['species_ids']) <= 128:
        raise ValueError('history_job_cardinality')
    code_id = implementation_id()
    if code_id != spec.get('procedure_revision'):
        raise ValueError('history_worker_code_mismatch: update the worker before running this job')
    started = time.monotonic()
    progress = JobProgress(args.progress_jsonl)
    from rainmapper_core import mushroom_competing_panels as panel_cache
    from rainmapper_core import mushroom_competing_comparison as comparison
    from rainmapper_core.mushroom_competing_replay import Replay
    panels = panel_cache.Panels(args.cache_dir / 'comparison.sqlite')
    try:
        saved = panels.generation(spec['history_revision'])
        reused_generation = saved is not None
        if saved is None:
            observations = read_json(contained(root, spec['observations_path']), 16 * 1024 * 1024)['observations']
            planned = panel_cache.preflight(spec['references'], [v for v in observations
                if v['species_id'] in spec['species_ids'] and str(v.get('observed_at', ''))[:10] < spec['cutoff']], deferred=True)
            del observations
            progress({'phase': 'Planning historical complete weeks', 'overall_percent': 5, **planned})
            saved = prepare_generation(root, spec, args.cache_dir, progress, panels, code_id, deferred=True)
            # Pack once: persistence and comparison share the same columns.
            saved['evidence'] = evidence.to_wire(saved['evidence'])
            panels.save_generation(spec['history_revision'], saved)
        result = {**saved['evidence'], 'revision': spec['revision'], 'history_revision': spec['history_revision']}
        if reused_generation:
            summary = result['summary']
            result['summary'] = {**summary, 'computed_units': 0,
                                 'reused_units': summary['computed_units'] + summary['reused_units']}
        def replay_progress(event):
            event['overall_percent'] = 90 + 4 * event['completed_visits'] / max(1, event['total_visits'])
            progress(event)
        from rainmapper_core.mushroom_competing_fit_scheduler import worker_count
        if saved.get('deferred_panels') and worker_count()>1 and len(saved['visits'])>=256:
            from rainmapper_core.mushroom_competing_parallel import evaluate_parallel
            from rainmapper_core import mushroom_ml_weather_workspace as weather
            result = evidence.to_wire(result)
            saved['evidence'] = result
            weather.clear_active_workspace()
            gc.collect()
            paths = {name:contained(root,spec[name]) for name in (
                'observations_path','known_sites_path','weather_data_dir','stations_path')}
            evaluated = evaluate_parallel(panels=panels,cache_dir=args.cache_dir,spec=spec,
                paths=paths,producer=code_id,visits=saved['visits'],workers=worker_count(),progress=replay_progress)
        else:
            replay = Replay(result,panels=panels,unit_index=saved['unit_index'],visits=saved['visits'],
                profiles=spec['profiles'],recommendation_policy=spec['recommendation_policy'],
                suspensions=spec['prediction_model_suspensions'])
            with history.UnitCache(args.cache_dir / 'units.sqlite') as units:
                from rainmapper_core.mushroom_competing_fits import Fits
                from rainmapper_core.mushroom_competing_features import Inputs
                from rainmapper_core.mushroom_competing_inputs import runtime_feature_revision
                def build_requested():
                    from rainmapper_core import mushroom_ml_weather_workspace as weather
                    paths = {name: contained(root, spec[name]) for name in (
                        'observations_path', 'known_sites_path', 'weather_data_dir', 'stations_path')}
                    if weather.active_workspace(data_dir=paths['weather_data_dir'], known_sites=paths['known_sites_path'],
                                                stations_file=paths['stations_path']) is None:
                        weather.activate_operational_workspace(data_dir=paths['weather_data_dir'],
                            observations=paths['observations_path'], known_sites=paths['known_sites_path'],
                            stations_file=paths['stations_path'], max_horizon_days=13, compact_series=True)
                    return panel_cache.Builder(store=panels, known_sites=paths['known_sites_path'],
                        data_dir=paths['weather_data_dir'], stations_file=paths['stations_path'],
                        profiles=spec['catalog_profiles'], progress=progress, inputs=Inputs(units.db),
                        input_revision=runtime_feature_revision(), persist_features=False)
                if saved.get('deferred_panels'):
                    requested = panel_cache.RequestedPanels(panels,
                        Fits(units.db, code_id, compatible_producers=history.COMPATIBLE_ROW_PROCEDURES),
                        saved['visits'], build_requested)
                    panels.materialize_missing = requested
                    from rainmapper_core.mushroom_competing_batch import BatchedReplay
                    replay = BatchedReplay(replay,requested,saved['visits'])
                evaluated = comparison.evaluate(saved['visits'], k=spec['comparison_k'], cutoff=spec['cutoff'],
                                                 replay=replay, progress=replay_progress)
                panels.materialize_missing = None
        result['comparisons'] = [comparison.validate(evaluated)]
    finally:
        panels.close()
    result = evidence.to_wire(result)
    evidence.validate(result)
    raw = evidence.encode(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_bytes(raw); temporary.replace(args.output)
    progress({'phase': 'Historical evaluation completed', 'overall_percent': 95,
              'seconds': round(time.monotonic() - started, 3), 'size_bytes': len(raw), **result['summary']})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
