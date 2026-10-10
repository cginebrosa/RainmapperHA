"""Bounded cooperative replay: gather demanded members, infer by model, resume.

No provisional probability is supplied to a selector. A replay pauses on a
missing member and resumes against the same immutable inputs after its batch
is materialized. Only sixteen visits (112 issued weeks) are held at a time.
"""
from collections import OrderedDict
from datetime import date, timedelta

from rainmapper_core.mushroom_competing_comparison import MissingReplay


class _PendingMember(Exception):
    pass


class BatchedReplay:
    def __init__(self, replay, requested, visits, *, batch_size=16):
        if not 1 <= batch_size <= 16:
            raise ValueError('comparison_visit_batch_limit')
        self.replay, self.requested = replay, requested
        self.visits = sorted(visits,key=lambda v:(v['day'],v['species_id'],v['id']))
        self.positions = {(v['species_id'],v['id']):i for i,v in enumerate(self.visits)}
        self.batch_size = batch_size
        self.results = {}

    def __call__(self, visit, issue, k):
        key = visit['species_id'],visit['id'],issue,k
        if key not in self.results:
            start = self.positions[visit['species_id'],visit['id']]
            self._fill(self.visits[start:start+self.batch_size],k)
        value = self.results[key]
        if isinstance(value,MissingReplay):
            raise value
        return dict(value)

    def _fill(self, visits, k):
        self.results.clear()
        waiting = []
        for visit in visits:
            identity = {name:visit[name] for name in ('id','species_id','day')}
            target = date.fromisoformat(visit['day'])
            waiting.extend((identity,target-timedelta(days=h)) for h in range(7))
        store = self.requested.store
        original = store.materialize_missing
        queue, missing = OrderedDict(), {}
        def defer(unit,sid,oid,target,horizon,*,week_issue=None):
            request = unit,sid,oid,target,horizon,week_issue
            if request in missing:
                raise missing[request]
            if request not in queue and len(queue)>=112:
                raise ValueError('comparison_request_batch_limit')
            queue[request] = None
            raise _PendingMember()
        store.materialize_missing = defer
        try:
            while waiting:
                pending = []
                for visit,issue in waiting:
                    key = visit['species_id'],visit['id'],issue,k
                    try:
                        self.results[key] = self.replay(visit,issue,k)
                    except _PendingMember:
                        pending.append((visit,issue))
                    except MissingReplay as exc:
                        self.results[key] = exc
                if not pending:
                    break
                if not queue:
                    raise ValueError('comparison_batch_no_progress')
                requests = list(queue); queue.clear()
                self.requested.fill_many(requests)
                # A missing area/gate can produce no packet. Preserve the
                # ordinary technical exclusion instead of retrying forever.
                for request in requests:
                    try:
                        store._read(*request[:5])
                    except MissingReplay as exc:
                        missing[request] = exc
                waiting = pending
        finally:
            store.materialize_missing = original
            close = getattr(self.replay, 'close_pending', None)
            if close is not None:
                close()
