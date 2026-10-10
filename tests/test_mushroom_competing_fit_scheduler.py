from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from rainmapper_core import mushroom_competing_history as history
from rainmapper_core.mushroom_competing_fit_scheduler import FitScheduler, worker_count
from rainmapper_core.mushroom_competing_fits import Fits
from tests.test_mushroom_competing_history import HistoryTests, REF


class FitSchedulerTests(unittest.TestCase):
    def test_single_family_can_use_independent_annual_folds_concurrently(self):
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        barrier = threading.Barrier(2)
        original = trainer.fit_artifact
        def together(*args,**kwargs):
            barrier.wait(timeout=5)
            return original(*args,**kwargs)
        with (tempfile.TemporaryDirectory() as tmp,
              history.UnitCache(Path(tmp)/'units.sqlite') as cache,
              patch.object(trainer,'fit_artifact',together)):
            fits = Fits(cache.db,'annual-test')
            scheduler = FitScheduler(fits,3)
            try:
                result = list(history.evaluate_benchmark(HistoryTests().benchmark(),[REF],
                    cutoff='2026-10-05',implementation_id='annual-test',cache=cache,
                    targets={'boletus_aereus'},fit_cache=fits,fit_scheduler=scheduler,
                    evaluate=lambda *args:scheduler.finish(*args,panel_builder=None,
                                                          prepared_cache={},defer_panels=True)))
            finally:
                scheduler.close()
        self.assertEqual([v['year'] for v in result],[2020,2021,2022])
        self.assertEqual(len(result[-1]['rows']),1)

    def test_parallel_predictions_equal_serial_and_only_caller_writes(self):
        from rainmapper_core import mushroom_ml_runtime_trainer as trainer
        benchmark = HistoryTests().benchmark()
        refs = [{**REF,'estimator_id':estimator} for estimator in (
            'logistic_regression_reduced_v1','random_forest_restricted_v1','extra_trees_restricted_v1')]
        outputs = []
        main = threading.get_ident()
        numeric_threads = set()
        original = trainer.fit_artifact
        def measured(*args,**kwargs):
            numeric_threads.add(threading.get_ident())
            time.sleep(.01)
            return original(*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp, patch.object(trainer,'fit_artifact',measured):
            for workers in (1,3):
                with history.UnitCache(Path(tmp)/f'{workers}.sqlite') as cache:
                    fits = Fits(cache.db,'same-test-producer')
                    scheduler = FitScheduler(fits,workers) if workers > 1 else None
                    saved = fits.write
                    def write(*args):
                        self.assertEqual(threading.get_ident(),main)
                        return saved(*args)
                    def fit(ref,bench,train,test,key):
                        if scheduler:
                            return scheduler.finish(ref,bench,train,test,key,panel_builder=None,
                                                    prepared_cache={},defer_panels=True)
                        return history.fit_temporal_unit(ref,bench,train,test,key,fit_cache=fits)
                    with patch.object(fits,'write',write):
                        try:
                            values = list(history.evaluate_benchmark(benchmark,refs,cutoff='2026-10-05',
                                implementation_id='same-test-producer',cache=cache,targets={'boletus_aereus'},
                                evaluate=fit,fit_cache=fits,fit_scheduler=scheduler))
                            self.assertTrue(all(v['reused'] for v in history.evaluate_benchmark(
                                benchmark,refs,cutoff='2026-10-05',implementation_id='same-test-producer',
                                cache=cache,targets={'boletus_aereus'},
                                evaluate=lambda *a:self.fail('Unchanged units must not fit again'),
                                fit_cache=fits,fit_scheduler=scheduler)))
                        finally:
                            if scheduler:scheduler.close()
                    outputs.append([{k:v for k,v in unit.items() if k != 'seconds'} for unit in values])
        self.assertEqual(outputs[0],outputs[1])
        self.assertGreater(len(numeric_threads-{main}),1)

    def test_explicit_opt_in_and_hard_cap(self):
        with patch.dict('os.environ',{},clear=True):
            self.assertEqual(worker_count(),1)
        for value in ('0','5','bad'):
            with patch.dict('os.environ',{'RAINMAPPER_HISTORY_FIT_WORKERS':value}):
                with self.assertRaisesRegex(ValueError,'invalid_history_fit_workers'):
                    worker_count()
        with patch.dict('os.environ',{'RAINMAPPER_HISTORY_FIT_WORKERS':'4'}):
            self.assertEqual(worker_count(),4)

    def test_queue_rejects_unbounded_submission(self):
        with tempfile.TemporaryDirectory() as tmp, history.UnitCache(Path(tmp)/'units.sqlite') as cache:
            scheduler = FitScheduler(Fits(cache.db,'test'),2)
            scheduler.pending = {'first':None,'second':None}
            try:
                with self.assertRaisesRegex(ValueError,'history_fit_queue_limit'):
                    scheduler.prefetch(None,None,[],[],'third')
            finally:
                scheduler.close()


    def test_process_pool_and_ordered_headers_preserve_serial_units(self):
        from rainmapper_core.mushroom_competing_fit_scheduler import ProcessFitScheduler
        from collections import OrderedDict
        benchmark = HistoryTests().benchmark()
        refs = [{**REF,'estimator_id':name} for name in ('logistic_regression_reduced_v1','extra_trees_restricted_v1')]
        outputs=[]
        with tempfile.TemporaryDirectory() as tmp:
            for parallel in (False,True):
                with history.UnitCache(Path(tmp)/f'process-{parallel}.sqlite') as cache:
                    fits=Fits(cache.db,'process-parity')
                    scheduler=ProcessFitScheduler(fits,2) if parallel else None
                    ordered=history.OrderedUnits(cache,OrderedDict(one=refs))
                    def fit(*args):
                        if scheduler:
                            return scheduler.finish(*args,panel_builder=None,prepared_cache={},defer_panels=True)
                        return history.fit_temporal_unit(*args,fit_cache=fits)
                    waiting=[]
                    try:
                        for unit in history.evaluate_benchmark(benchmark,refs,cutoff='2026-10-05',
                                implementation_id='process-parity',cache=cache,targets={'boletus_aereus'},
                                evaluate=fit,fit_cache=fits,fit_scheduler=scheduler,defer_results=parallel):
                            waiting.append(unit)
                        # Deliberately publish the numerical results out of order.
                        for unit in reversed(waiting):
                            ordered.add(unit() if callable(unit) else unit)
                        outputs.append([{k:v for k,v in unit.items() if k!='seconds'} for unit in ordered])
                    finally:
                        if scheduler:scheduler.close()
        self.assertEqual(outputs[0],outputs[1])
