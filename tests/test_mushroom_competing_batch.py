from datetime import date, timedelta
import unittest

from rainmapper_core.mushroom_competing_batch import BatchedReplay
from rainmapper_core.mushroom_competing_comparison import METHODS, MissingReplay, evaluate


class Store:
    def __init__(self):
        self.values = {}
        self.materialize_missing = None

    def _read(self,unit,sid,oid,day,h):
        try:
            return self.values[unit,sid,oid,day,h]
        except KeyError:
            raise MissingReplay('weekly_day_unavailable') from None

    def read(self,unit,sid,oid,day,h,issue):
        try:
            return self._read(unit,sid,oid,day,h)
        except MissingReplay:
            self.materialize_missing(unit,sid,oid,day,h,week_issue=issue)
            return self._read(unit,sid,oid,day,h)


class Requested:
    def __init__(self,store):
        self.store,self.batches = store,[]

    def __call__(self,*args,week_issue=None):
        self.fill_many([(*args,week_issue)])

    def fill_many(self,requests):
        self.batches.append(len(requests))
        for unit,sid,oid,target,horizon,issue in requests:
            if oid=='missing':
                continue
            for h in range(1,8):
                value = ((issue.day+h+len(oid))%4)/4 if unit=='first' else .75
                self.store.values[unit,sid,oid,issue+timedelta(days=h-1),h] = value


class BatchTests(unittest.TestCase):
    def test_bounded_batches_preserve_dynamic_fallbacks_and_common_exclusions(self):
        visits = [dict(id='missing' if i==9 else str(i),species_id='boletus_aereus',
                       day=(date(2026,9,1)+timedelta(days=i//2)).isoformat(),y=i%2)
                  for i in range(37)]
        outputs = []; counts=[]
        for batched in (False,True):
            store=Store();requested=Requested(store);store.materialize_missing=requested
            def replay(visit,issue,k):
                self.assertEqual(set(visit),{'id','species_id','day'})
                values=[]
                for h in range(1,8):
                    day=issue+timedelta(days=h-1)
                    value=store.read('first',visit['species_id'],visit['id'],day,h,issue)
                    if value<.5:
                        value=store.read('fallback',visit['species_id'],visit['id'],day,h,issue)
                    values.append(value>=.6)
                horizon=(date.fromisoformat(visit['day'])-issue).days
                return dict.fromkeys(METHODS,values[horizon])
            call=BatchedReplay(replay,requested,visits) if batched else replay
            outputs.append(evaluate(visits,k=4,cutoff='2026-10-01',replay=call))
            self.assertIs(store.materialize_missing,requested)
            self.assertTrue(all(n<=112 for n in requested.batches))
            counts.append(len(requested.batches))
        self.assertEqual(outputs[0],outputs[1])
        self.assertEqual(outputs[1]['species']['boletus_aereus']['missing'],{'weekly_day_unavailable':1})
        self.assertLess(counts[1],counts[0]/4)

    def test_error_restores_callback_and_limits_are_explicit(self):
        store=Store();requested=Requested(store);store.materialize_missing=requested
        visit=dict(id='one',species_id='s',day='2026-09-01')
        def fail(*args):raise ValueError('real error')
        batch=BatchedReplay(fail,requested,[visit])
        with self.assertRaisesRegex(ValueError,'real error'):
            batch(visit,date(2026,9,1),4)
        self.assertIs(store.materialize_missing,requested)
        with self.assertRaisesRegex(ValueError,'batch_limit'):
            BatchedReplay(fail,requested,[visit],batch_size=17)
