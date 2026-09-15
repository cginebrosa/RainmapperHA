"""Ephemeral, bounded report queries. Never writes training jobs or user data."""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import json
import secrets
import threading
import time

from rainmapper_core import mushroom_prediction_map as contract

WORKER_PATH = "/api/mushrooms/workers/map-queries"
MAX_QUERIES = 8
TTL = 120


class QueryError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class QueryBroker:
    def __init__(self, executor=None, clock=time.monotonic, publication=None, geography=None):
        self.executor, self.clock = executor, clock
        self.publication = publication
        self.geography = geography
        self.lock = threading.RLock()
        self.queries = OrderedDict()
        self.workers = {}
        self.local_ready = False
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.thread = None
        if executor is not None:
            self.thread = threading.Thread(target=self._local_loop, daemon=True, name="map-local-reports")
            self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()
        if self.publication: self.publication.close()
        if self.geography: self.geography.close()
        if self.thread:
            self.thread.join(timeout=2)

    def _prune(self):
        now = self.clock()
        for key in list(self.queries):
            if now-self.queries[key]["created"] >= TTL:
                del self.queries[key]
        self.workers = {key:value for key,value in self.workers.items() if now-value[0] < 15}

    def capabilities(self):
        with self.lock:
            self._prune()
            return {"local":self.local_ready,"worker":any(value[2] for value in self.workers.values())}

    def submit(self, owner, payload):
        request = contract.parse_request(json.dumps(payload).encode())
        mode = request.get("execution","local")
        with self.lock:
            self._prune()
            for key,row in self.queries.items():
                if row["owner"] == owner and row["request"]["request_id"] == request["request_id"]:
                    if row["request"] != request:
                        raise QueryError("request_id_conflict",409)
                    return {"query_id":key,"state":row["state"]}
            if not self.capabilities()[mode]:
                if mode == "worker" and self.workers:
                    raise QueryError("worker_busy",503)
                raise QueryError("executor_unavailable",503)
            if len(self.queries) >= MAX_QUERIES:
                disposable = next((key for key,row in self.queries.items() if row.get("delivered") or row["state"] in ("cancelled","failed")),None)
                if disposable:
                    del self.queries[disposable]
                else:
                    raise QueryError("query_queue_full",429)
            reference = self.publication.reference() if mode == "worker" and self.publication else None
            if self.geography:
                reference = {**(reference or {}), "geography": self.geography.reference()}
            key = secrets.token_urlsafe(18)
            self.queries[key] = {"owner":owner,"request":deepcopy(request),"mode":mode,
                "created":self.clock(),"state":"queued","worker_id":None,"claim":None,"runtime":reference}
            if mode == "local":
                self.wake.set()
            return {"query_id":key,"state":"queued"}

    def status(self, owner, key, cancel=False):
        with self.lock:
            self._prune()
            row = self.queries.get(key)
            if not row or row["owner"] != owner:
                raise QueryError("query_not_found",404)
            if cancel and row["state"] in ("queued","running"):
                row["state"] = "cancelled"
            if cancel:
                return 200, {"query_id":key,"state":row["state"]}
            if row["state"] == "complete":
                row["delivered"] = True
                return 200, deepcopy(row["result"])
            if row["state"] in ("cancelled","failed"):
                raise QueryError("query_"+row["state"],409)
            return 202, {"query_id":key,"state":row["state"]}

    def _claim(self, mode, worker_id):
        # Caller holds lock. One active query per executor.
        if any(row["state"] == "running" and row["worker_id"] == worker_id for row in self.queries.values()):
            return None
        for key,row in self.queries.items():
            if row["mode"] == mode and row["state"] == "queued":
                row.update(state="running",worker_id=worker_id,claim=secrets.token_urlsafe(24))
                return {"query_id":key,"claim":row["claim"],"request":deepcopy(row["request"]),
                        **({"runtime":row["runtime"]} if row.get("runtime") else {})}
        return None

    def worker_poll(self, worker_id, busy=False, ready=None):
        with self.lock:
            self._prune()
            if worker_id not in self.workers and len(self.workers) >= 8:
                raise QueryError("worker_limit",429)
            self.workers[worker_id] = (self.clock(), busy, not busy if ready is None else bool(ready))
            return {"query":None if busy else self._claim("worker",worker_id)}

    def finish(self, worker_id, payload):
        with self.lock:
            self._prune()
            row = self.queries.get(payload.get("query_id"))
            if not row or row["worker_id"] != worker_id or not secrets.compare_digest(row.get("claim") or "", str(payload.get("claim",""))):
                raise QueryError("invalid_claim",403)
            if row["state"] != "running":
                return {"accepted":False,"state":row["state"]}
            result = payload.get("result")
            if payload.get("failed") is True:
                row["state"] = "failed"
                return {"accepted":True}
            contract.encode_result(result)
            req = row["request"]
            try:
                contract.validate_result(result, req)
            except (ValueError,TypeError,KeyError,AttributeError) as error:
                raise QueryError("invalid_result") from error
            row.update(state="complete",result=deepcopy(result))
            return {"accepted":True}

    def _local_loop(self):
        try:
            self.local_ready = self.executor.ready()
            while not self.stop.is_set():
                self.wake.wait(1)
                self.wake.clear()
                if self.stop.is_set():
                    break
                with self.lock:
                    self._prune()
                    job = self._claim("local","_local") if self.local_ready else None
                if job:
                    try:
                        result = (self.executor.execute_snapshot(job["request"], job.get("runtime"))
                                  if hasattr(self.executor, "execute_snapshot") else self.executor.execute(job["request"]))
                        self.finish("_local",{**job,"result":result})
                    except Exception:
                        try:
                            self.finish("_local",{**job,"failed":True})
                        except QueryError:
                            pass
                    self.wake.set()
        except Exception:
            self.local_ready = False
        finally:
            self.executor.close()
