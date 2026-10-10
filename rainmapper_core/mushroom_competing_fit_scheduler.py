"""Bounded numerical parallelism; SQLite and runtime panels stay on the caller."""
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, wait, FIRST_COMPLETED
import os

from rainmapper_core import mushroom_competing_history as history


def worker_count():
    """Explicit opt-in, capped independently of the container's CPU limit."""
    try:
        value = int(os.environ.get('RAINMAPPER_HISTORY_FIT_WORKERS', '1'))
    except ValueError as exc:
        raise ValueError('invalid_history_fit_workers') from exc
    if not 1 <= value <= 4:
        raise ValueError('invalid_history_fit_workers')
    return value


class FitScheduler:
    def __init__(self, fit_cache, workers, *, queue_limit=None):
        if not 2 <= workers <= 4:
            raise ValueError('invalid_history_fit_workers')
        self.workers, self.fit_cache = workers, fit_cache
        self.queue_limit = workers if queue_limit is None else queue_limit
        if not workers <= self.queue_limit <= 16:
            raise ValueError('history_fit_queue_limit')
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='history-fit')
        # A single shared pool for inner choices avoids an idle CPU when the
        # outer queue waits for its last expensive fit. No pool per model.
        self.tuning_pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='history-tuning')
        self.pending = {}
        self.prepared = None

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.tuning_pool.shutdown(wait=True, cancel_futures=True)
        self.pending.clear()
        self.prepared = None

    def prefetch(self, reference, benchmark, train, test, key):
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        if len(self.pending) >= self.queue_limit:
            raise ValueError('history_fit_queue_limit')
        if (not train or len({s['prediction_target'] for s in train}) < 2 or
                not {s['metadata']['species_id'] for s in train}.intersection(
                    s['metadata']['species_id'] for s in test)):
            return
        fit_key = self.fit_cache.key(reference, benchmark, train)
        if self.fit_cache.contains(fit_key):
            self.pending[key] = fit_key, None
            return
        scope = (reference.version_id,reference.temporal_contract_id,reference.profile_id,
                 reference.species_id,tuple(id(s) for s in train))
        if self.prepared is None or self.prepared[0] != scope:
            prepared = trainer._prepare_fit_inputs(reference, {**benchmark,'samples':train})
            self.prepared = scope, train, prepared
        prepared = self.prepared[2]
        # Matrices are shared read-only by estimators of the same scope. Each
        # future owns only its model; no weather builder or DB enters a thread.
        def compute():
            captured = []
            value = history.fit_temporal_unit(reference,benchmark,train,test,key,
                prepared_cache={scope:(train,prepared)},
                inner_executor=self.tuning_pool,
                capture=lambda bundle,diagnostics: captured.append((bundle,diagnostics)))
            return value, captured[0] if captured else None
        self.pending[key] = fit_key, self.pool.submit(compute)

    def finish(self, reference, benchmark, train, test, key, *, panel_builder,
               prepared_cache, defer_panels):
        pending = self.pending.pop(key, None)
        if pending is None:
            return history.fit_temporal_unit(reference,benchmark,train,test,key,
                panel_builder=panel_builder,prepared_cache=prepared_cache,
                fit_cache=self.fit_cache,defer_panels=defer_panels)
        fit_key, future = pending
        if future is None:
            return history.fit_temporal_unit(reference,benchmark,train,test,key,
                panel_builder=panel_builder,prepared_cache=prepared_cache,
                fit_cache=self.fit_cache,defer_panels=defer_panels,fit_key=fit_key)
        value, captured = future.result()
        if captured is not None:
            bundle, diagnostics = captured
            self.fit_cache.write(fit_key,bundle,diagnostics)
            if panel_builder is not None:
                deferred = defer_panels and panel_builder.defer(reference,key,self.fit_cache,fit_key)
                if defer_panels and not deferred:
                    raise ValueError('history_fit_cache_budget: cannot defer historical models within the cache limit')
                if not deferred:
                    supported = {s['metadata']['species_id'] for s in train}
                    panel_builder(bundle,reference,[s for s in test
                        if s['metadata']['species_id'] in supported],key)
        return value


def _fit_in_process(reference, benchmark, train, test, key, prepared):
    scope = (reference.version_id,reference.temporal_contract_id,reference.profile_id,
             reference.species_id,tuple(id(s) for s in train))
    captured = []
    value = history.fit_temporal_unit(reference,benchmark,train,test,key,
        prepared_cache={scope:(train,prepared)},
        capture=lambda bundle,diagnostics:captured.append((bundle,diagnostics)))
    return value, captured[0] if captured else None


class ProcessFitScheduler(FitScheduler):
    """Bounded lookahead; all durable writes still happen in finish()."""
    def __init__(self, fit_cache, workers, *, queue_limit=16):
        import multiprocessing
        if not 2 <= workers <= 4 or not workers <= queue_limit <= 16:
            raise ValueError('invalid_history_fit_workers')
        self.workers, self.fit_cache, self.queue_limit = workers, fit_cache, queue_limit
        self.pool = ProcessPoolExecutor(max_workers=workers,
            mp_context=multiprocessing.get_context('forkserver'))
        self.pending = {}
        self.prepared = None
        self.matrices = {}
        self.peak_matrix_bytes = 0

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.pending.clear(); self.matrices.clear(); self.prepared = None

    def prefetch(self, reference, benchmark, train, test, key):
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        if len(self.pending) >= self.queue_limit:
            raise ValueError('history_fit_queue_limit')
        if (not train or len({s['prediction_target'] for s in train}) < 2 or
                not {s['metadata']['species_id'] for s in train}.intersection(
                    s['metadata']['species_id'] for s in test)):
            return
        fit_key = self.fit_cache.key(reference,benchmark,train)
        if self.fit_cache.contains(fit_key):
            self.pending[key] = fit_key, None
            return
        scope = (reference.version_id,reference.temporal_contract_id,reference.profile_id,
                 reference.species_id,tuple(id(s) for s in train))
        if self.prepared is None or self.prepared[0] != scope:
            prepared = trainer._prepare_fit_inputs(reference,{**benchmark,'samples':train})
            def light(sample):
                return {'metadata':sample['metadata'],'prediction_target':sample['prediction_target']}
            prepared = {**prepared,'samples':tuple(light(s) for s in prepared['samples'])}
            self.prepared = scope, train, prepared, [light(s) for s in train]
        prepared, light_train = self.prepared[2:]
        matrices = {id(value[0]):value[1] for value in self.matrices.values()}
        size = prepared['X'].nbytes + prepared['y'].nbytes
        matrices[id(prepared)] = size
        total = sum(matrices.values())
        if total > 1024*1024*1024:
            raise ValueError('history_fit_queue_matrix_limit')
        self.peak_matrix_bytes = max(self.peak_matrix_bytes,total)
        envelope = {k:benchmark[k] for k in ('feature_set','water_state_contract_id') if k in benchmark}
        future = self.pool.submit(_fit_in_process,reference,envelope,light_train,test,key,prepared)
        self.pending[key] = fit_key, future
        self.matrices[key] = prepared, size

    def finish(self, reference, benchmark, train, test, key, **kwargs):
        try:
            return super().finish(reference,benchmark,train,test,key,**kwargs)
        finally:
            self.matrices.pop(key,None)

    def ready(self, key):
        value = self.pending.get(key)
        return value is None or value[1] is None or value[1].done()

    def wait_ready(self):
        values = [future for _,future in self.pending.values() if future is not None]
        if values:
            wait(values,return_when=FIRST_COMPLETED)
