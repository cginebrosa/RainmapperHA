"""Opt-in outbound point reports using the worker's existing coordinator URLs."""
import json
import logging
import threading
import time
from urllib.request import Request, urlopen

from rainmapper_core.mushroom_map_execution import PointExecutor, load_config
from rainmapper_core.mushroom_map_queries import WORKER_PATH
from rainmapper_core import mushroom_prediction_map as contract
from rainmapper_core import mushroom_ml_prediction_policy as model_policy

PROTOCOL = "map_report_v1"


def exchange(coordinator, payload):
    raw = json.dumps({"protocol":PROTOCOL,**payload},allow_nan=False).encode()
    if len(raw) > contract.MAX_RESULT_BYTES+4096:
        raise ValueError("map_worker_payload_limit")
    request = Request(coordinator["rainmapper_url"].rstrip("/")+WORKER_PATH, data=raw,
                      headers={"Authorization":"Bearer "+coordinator["token"],"Content-Type":"application/json"})
    with urlopen(request,timeout=5) as response:
        data = response.read(contract.MAX_REQUEST_BYTES+4097)
    if len(data) > contract.MAX_REQUEST_BYTES+4096:
        raise ValueError("map_worker_response_limit")
    return json.loads(data)


def run_loop(coordinators, worker_id, executors, stop, busy=lambda:False, transport=exchange, online_slot=None):
    """One online slot; private snapshots are synchronized within their association."""
    def announce(executor, response):
        geography = getattr(executor, 'geography', None)
        if geography and response.get('geography'):
            geography.request(response['geography'])

    def readiness(executor):
        return {'capabilities': [model_policy.CAPABILITY],
                **({'ready_fingerprint': executor.fingerprint} if hasattr(executor, 'prepare') else {}),
                **({'ready_geography': executor.executor_geography} if getattr(executor, 'geography', None) else {})}

    ready = {}
    retry_after, failures = {}, {}
    try:
        for key,executor in executors.items():
            try:
                ready[key] = executor.ready()
            except Exception:
                ready[key] = False
        while not stop.is_set():
            for coordinator in coordinators:
                key = coordinator["coordinator_id"]
                if stop.is_set() or not ready.get(key):
                    continue
                reserved = False
                try:
                    if time.monotonic() < retry_after.get(key, 0):
                        announce(executors[key], transport(coordinator,{"worker_id":worker_id,"action":"busy", **readiness(executors[key])}))
                        continue
                    if not busy():
                        reserved = online_slot is None or online_slot.acquire(blocking=False)
                    if not reserved:
                        # Keep liveness separate from willingness to claim work.
                        # Older coordinators reject this action without claiming a query.
                        announce(executors[key], transport(coordinator,{"worker_id":worker_id,"action":"busy", **readiness(executors[key])}))
                        continue
                    response = transport(coordinator,{"worker_id":worker_id,"action":"poll",
                        "capabilities": [model_policy.CAPABILITY],
                        **({"ready_fingerprint":executors[key].fingerprint} if hasattr(executors[key], "prepare") else {}),
                        **({"ready_geography":executors[key].executor_geography} if getattr(executors[key], 'geography', None) else {})})
                    announce(executors[key], response)
                    job = response.get("query")
                    if not job:
                        if response.get("runtime") and hasattr(executors[key], "prepare"):
                            geo = getattr(executors[key], 'geography', None)
                            if geo and (not response.get('geography') or geo.reference() != response['geography']['fingerprint']):
                                continue
                            executors[key].prepare(response["runtime"])
                            failures[key] = 0
                        continue
                    request = contract.parse_request(json.dumps(job["request"]).encode())
                    if request.get("execution") != "worker":
                        raise ValueError("invalid_map_executor")
                    completion = {"worker_id":worker_id,"action":"finish","query_id":job["query_id"],"claim":job["claim"]}
                    try:
                        completion["result"] = (executors[key].execute_snapshot(request, job.get("runtime"))
                            if hasattr(executors[key], "execute_snapshot") else executors[key].execute(request))
                    except Exception:
                        completion["failed"] = True
                    # One identical retry is safe; completion is claim-protected and idempotent.
                    try:
                        transport(coordinator,completion)
                    except Exception:
                        if not stop.wait(1):
                            transport(coordinator,completion)
                except Exception as error:
                    # No local fallback, coordinator rewrite or scientific-job side effect.
                    failures[key] = min(failures.get(key, 0)+1, 6)
                    retry_after[key] = time.monotonic()+min(60, 2**failures[key])
                    logging.getLogger(__name__).warning('Map association %s paused after %s', key, type(error).__name__)
                finally:
                    if reserved and online_slot is not None:
                        online_slot.release()
            stop.wait(1)
    finally:
        for executor in executors.values():
            executor.close()


def start(config_path, coordinators, worker_id, stop, busy=lambda:False, online_slot=None, worker_data_dir=None, background_slot=None):
    config, root = load_config(config_path)
    contexts = config.get("coordinators",{})
    executors = {}
    for coordinator in coordinators:
        key = coordinator["coordinator_id"]
        selected = contexts.get(key)
        if selected is None and (len(coordinators) == 1 or config.get("all_coordinators") is True) and "coordinators" not in config:
            selected = config
        if selected is not None:
            if selected.get("private_runtime"):
                if worker_data_dir is None: raise ValueError("missing_worker_cache_root")
                from rainmapper_core.mushroom_map_runtime import CachedPointExecutor
                executors[key] = CachedPointExecutor(selected, root, coordinator, worker_id, worker_data_dir, background_slot=background_slot)
            else:
                executors[key] = PointExecutor(selected,root)
    thread = threading.Thread(target=run_loop,args=(coordinators,worker_id,executors,stop,busy),
                              kwargs={"online_slot":online_slot},daemon=True,name="map-worker-reports")
    thread.start()
    return thread
