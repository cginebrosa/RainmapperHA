"""Bounded disjoint visit replay; only the parent publishes durable packets.

Each process uses an isolated disposable SQLite database, with a share of the
existing 96 MiB panel budget. Installed models and source data are read-only.
No forecast click invokes this worker-only module.
"""
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from collections import Counter
import json
import math
import multiprocessing
from pathlib import Path
import sqlite3
import tempfile
import time

from rainmapper_core import mushroom_competing_comparison as comparison
from rainmapper_core import mushroom_competing_panels as panel_cache


def merge_results(results):
    """Add integer horizon counts, then divide once; retain scalar rounding."""
    if not results:
        raise ValueError('comparison_empty_parts')
    result = {k:results[0][k] for k in ('protocol','k','cutoff')}
    if any(any(part[k] != result[k] for k in result) for part in results):
        raise ValueError('comparison_incompatible_parts')
    result['species'] = {}
    for sid in sorted({sid for part in results for sid in part['species']}):
        parts = [part['species'][sid] for part in results if sid in part['species']]
        n = sum(p['visits'] for p in parts)
        positive = sum(p['positive'] for p in parts)
        missing = Counter()
        for part in parts:
            missing.update(part['missing'])
        scores = {}
        for method in comparison.METHODS:
            def count(name):
                return sum(round(p['methods'][method][name]*7) for p in parts)/7
            tp, fp, abstain = count('tp'), count('fp'), count('abstentions')
            scores[method] = dict(ik=100*(tp-result['k']*fp)/positive if positive else None,
                tp=tp,fp=fp,calls=tp+fp,abstentions=abstain,
                precision=tp/(tp+fp) if tp+fp else None,recall=tp/positive if positive else None)
        ready = bool(positive and n>positive and all(s['abstentions']<n for s in scores.values()))
        best = max(s['ik'] for s in scores.values()) if ready else None
        result['species'][sid] = dict(status='ready' if ready else 'insufficient',visits=n,positive=positive,
            total_visits=sum(p['total_visits'] for p in parts),
            start=min((p['start'] for p in parts if p['start']),default=None),
            end=max((p['end'] for p in parts if p['end']),default=None),missing=dict(missing),methods=scores,
            winners=[m for m,s in scores.items() if best is not None and math.isclose(s['ik'],best,rel_tol=0,abs_tol=1e-9)])
    if all('history' in part for part in results):
        result['history'] = comparison.merge_histories(results)
    elif any('history' in part for part in results):
        raise ValueError('comparison_incompatible_history_parts')
    return comparison.validate(result)


class _PartPanels(panel_cache.Panels):
    def __init__(self, path, base, limit):
        super().__init__(path, max_bytes=limit)
        self.base = base

    def _packet(self, unit, sid, oid):
        packet = super()._packet(unit,sid,oid)
        return self.base._packet(unit,sid,oid) if packet is None else packet

    def fit(self, unit):
        return self.base.fit(unit)


def partition_ranges(count, workers, *, block_size=128):
    """Spread costly date ranges while retaining locality inside each block."""
    if not 2 <= workers <= 4 or not 0 < count <= comparison.MAX_VISITS or block_size != 128:
        raise ValueError('comparison_parallel_plan_limit')
    result = [[] for _ in range(workers)]
    for block, start in enumerate(range(0, count, block_size)):
        result[block % workers].append((start, min(count, start + block_size)))
    return result


def _evaluate_part(index, params):
    from rainmapper_core.mushroom_competing_history import UnitCache, COMPATIBLE_ROW_PROCEDURES
    from rainmapper_core.mushroom_competing_fits import Fits
    from rainmapper_core.mushroom_competing_features import Inputs
    from rainmapper_core.mushroom_competing_inputs import runtime_feature_revision
    from rainmapper_core.mushroom_competing_replay import Replay
    from rainmapper_core.mushroom_competing_batch import BatchedReplay
    from rainmapper_core import mushroom_ml_weather_workspace as weather
    directory = Path(params['directory'])
    progress_file = directory/f'part-{index}.json'
    spec = params['spec']
    base = panel_cache.Panels.readonly(params['panel_path'])
    models_db = sqlite3.connect(Path(params['unit_path']).resolve().as_uri()+'?mode=ro',uri=True)
    store = _PartPanels(directory/f'panels-{index}.sqlite',base,params['panel_limit'])
    count, last = 0, -1.
    ranges = params['ranges'][index]
    total = sum(end-start for start, end in ranges)
    def progress(event):
        nonlocal count,last
        count = event.get('completed_visits', count)
        now = time.monotonic()
        if now-last < .5 and count != total:
            return
        last = now
        raw = json.dumps({'completed':count,'message':str(event.get('message') or event.get('phase') or '')[:200]})
        temporary = progress_file.with_suffix('.tmp')
        temporary.write_text(raw);temporary.replace(progress_file)
    try:
        saved = base.generation(params['revision'])
        if saved is None:
            raise ValueError('comparison_generation_missing')
        ordered = sorted(saved['visits'], key=lambda v: (v['day'], v['species_id'], v['id']))
        visits = [visit for start, end in ranges for visit in ordered[start:end]]
        paths = {name:Path(value) for name,value in params['paths'].items()}
        weather.activate_operational_workspace(data_dir=paths['weather_data_dir'],
            observations=paths['observations_path'],known_sites=paths['known_sites_path'],
            stations_file=paths['stations_path'],max_horizon_days=13,compact_series=True)
        # Disposable feature cache shares this part's bounded panel database;
        # no second 256 MiB unit database is allocated for a read-only replay.
        def build():
            return panel_cache.Builder(store=store,known_sites=paths['known_sites_path'],
                data_dir=paths['weather_data_dir'],stations_file=paths['stations_path'],
                profiles=spec['catalog_profiles'],progress=progress,inputs=Inputs(store.db,limit=4*1024*1024),
                input_revision=runtime_feature_revision(),persist_features=False)
        requested = panel_cache.RequestedPanels(store,
            Fits(models_db,params['producer'],compatible_producers=COMPATIBLE_ROW_PROCEDURES),saved['visits'],build)
        store.materialize_missing = requested
        replay = Replay(saved['evidence'],panels=store,unit_index=saved['unit_index'],visits=saved['visits'],
            profiles=spec['profiles'],recommendation_policy=spec['recommendation_policy'],
            suspensions=spec['prediction_model_suspensions'])
        replay = BatchedReplay(replay,requested,visits)
        return comparison.evaluate(visits,k=spec['comparison_k'],cutoff=spec['cutoff'],replay=replay,progress=progress)
    finally:
        store.close();models_db.close();base.close()
        weather.clear_active_workspace()


def evaluate_parallel(*, panels, cache_dir, spec, paths, producer, visits, workers, progress):
    """Four processes maximum, no concurrent writers to the durable cache."""
    if not 2 <= workers <= 4 or not 0 < len(visits) <= comparison.MAX_VISITS:
        raise ValueError('comparison_parallel_plan_limit')
    ids = [(v['species_id'],v['id']) for v in visits]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate_comparison_visit')
    panel_path = panels.db.execute('PRAGMA database_list').fetchone()[2]
    if not panel_path:
        raise ValueError('comparison_parallel_requires_file_cache')
    panels.db.commit()
    with tempfile.TemporaryDirectory(prefix='comparison-parts-',dir=cache_dir) as scratch:
        ranges = partition_ranges(len(visits), workers)
        counts = [sum(end-start for start, end in part) for part in ranges]
        params = dict(directory=scratch,ranges=ranges,spec=spec,paths={k:str(v) for k,v in paths.items()},
            producer=producer,revision=spec['history_revision'],panel_path=panel_path,
            unit_path=str(Path(cache_dir)/'units.sqlite'),panel_limit=panel_cache.MAX_BYTES//workers)
        context = multiprocessing.get_context('forkserver')
        results = {};last = -1.
        with ProcessPoolExecutor(max_workers=workers,mp_context=context) as pool:
            futures = {pool.submit(_evaluate_part,i,params):i
                       for i in range(workers)}
            while futures:
                done, _ = wait(futures,timeout=.25,return_when=FIRST_COMPLETED)
                for future in done:
                    index = futures.pop(future)
                    results[index] = future.result()
                now = time.monotonic()
                if now-last >= .5:
                    count = 0;messages = []
                    for i in range(workers):
                        if i in results:
                            count += counts[i]
                        else:
                            path = Path(scratch)/f'part-{i}.json'
                            if path.exists():
                                item = json.loads(path.read_text());count += item['completed']
                                messages.append(f"{i+1}: {item['message']}")
                    progress(dict(phase='Comparing Habitual/A/B/C/D',completed_visits=count,
                                  total_visits=len(visits),message=' · '.join(messages)))
                    last = now
        # Keep the shared input database immutable until every reader exits.
        # Merging an early partition while another reads can require journal
        # recovery on a read-only connection (notably on mounted filesystems).
        for index in range(workers):
            panels.merge_from(Path(scratch)/f'panels-{index}.sqlite')
        return merge_results([results[i] for i in range(workers)])
