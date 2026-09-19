import json
import threading
import time
import unittest
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rainmapper_core import mushroom_prediction_map as contract
from rainmapper_core.mushroom_map_queries import QueryBroker, QueryError, MAX_QUERIES
from rainmapper_core import mushroom_map_worker as worker


def request(**changes):
    return dict(contract=contract.CONTRACT_ID,request_id="query_test_0001",point=dict(lat=42.,lon=2.),
                start_date="2026-09-12",history_days=60,horizon_days=7,execution="worker",**changes)


class Executor:
    def ready(self): return True
    def close(self): pass
    def execute(self, req):
        result = contract.demo_result(req)
        result["execution"] = {"mode":req["execution"],"compute_ms":1.0}
        return result


class QueryTests(unittest.TestCase):
    def test_map_shares_online_slot_and_background_does_not_block_it(self):
        slot = threading.Lock()
        slot.acquire()  # Existing foreground job owns the online lane.
        stop = threading.Event()
        background = threading.Thread(target=lambda:stop.wait(5),daemon=True)
        background.start()
        self.addCleanup(lambda:(stop.set(),background.join(timeout=1)))
        actions = []
        test = self
        class CheckedExecutor(Executor):
            def execute(self, req):
                test.assertTrue(background.is_alive())
                test.assertFalse(slot.acquire(blocking=False))
                return super().execute(req)
        def transport(coordinator,payload):
            actions.append(payload['action'])
            if payload['action'] == 'busy':
                slot.release()  # Foreground finishes, background keeps running.
                return {'query':None}
            if payload['action'] == 'poll':
                return {'query':{'request':request(),'query_id':'test_query','claim':'test_claim'}}
            stop.set()
            return {'accepted':True}
        worker.run_loop([{'coordinator_id':'a'}],'worker-A',{'a':CheckedExecutor()},stop,
                        transport=transport,online_slot=slot)
        self.assertEqual(actions,['busy','poll','finish'])
        self.assertTrue(slot.acquire(blocking=False))
        slot.release()

    def test_online_slot_is_released_after_transport_failure(self):
        slot = threading.Lock()
        stop = threading.Event()
        def transport(coordinator,payload):
            stop.set()
            raise OSError('unavailable coordinator')
        worker.run_loop([{'coordinator_id':'a'}],'worker-A',{'a':Executor()},stop,
                        transport=transport,online_slot=slot)
        self.assertTrue(slot.acquire(blocking=False))
        slot.release()

    def test_busy_worker_stays_connected_without_claiming_and_recovers(self):
        now = [1.]
        broker = QueryBroker(clock=lambda:now[0])
        broker.worker_poll("worker-A")
        accepted = broker.submit("alice",request())
        self.assertIsNone(broker.worker_poll("worker-A",busy=True)["query"])
        self.assertEqual(broker.status("alice",accepted["query_id"])[1]["state"],"queued")
        with self.assertRaisesRegex(QueryError,"worker_busy"):
            broker.submit("bob",request())
        now[0] += 10
        broker.worker_poll("worker-A",busy=True)
        now[0] += 10
        with self.assertRaisesRegex(QueryError,"worker_busy"):
            broker.submit("bob",request())
        self.assertEqual(broker.worker_poll("worker-A")["query"]["query_id"],accepted["query_id"])
        self.assertTrue(broker.capabilities()["worker"])
        now[0] += 16
        with self.assertRaisesRegex(QueryError,"executor_unavailable"):
            broker.submit("bob",request())

    def test_busy_loop_announces_status_without_executing_or_polling(self):
        stop = threading.Event()
        messages = []
        class NoExecution(Executor):
            def execute(self, req): raise AssertionError("busy worker must not calculate")
        def transport(coordinator,payload):
            messages.append(payload)
            stop.set()
            return {"query":None}
        worker.run_loop([{"coordinator_id":"a"}],"worker-A",{"a":NoExecution()},stop,
                        busy=lambda:True,transport=transport)
        self.assertEqual(messages,[{"worker_id":"worker-A","action":"busy",
                                    "capabilities":["prediction_model_policy_v1"]}])

    def setUp(self):
        self.broker = QueryBroker()
        self.broker.worker_poll("worker-A")

    def test_claim_owner_cancel_and_late_result(self):
        accepted = self.broker.submit("alice",request())
        with self.assertRaises(QueryError) as error:
            self.broker.status("bob",accepted["query_id"])
        self.assertEqual(error.exception.status,404)
        job = self.broker.worker_poll("worker-A")["query"]
        self.assertIsNone(self.broker.worker_poll("worker-A")["query"])
        with self.assertRaises(QueryError):
            self.broker.finish("worker-B",{**job,"result":Executor().execute(job["request"])})
        self.broker.status("alice",accepted["query_id"],cancel=True)
        result = self.broker.finish("worker-A",{**job,"result":Executor().execute(job["request"])})
        self.assertFalse(result["accepted"])

    def test_idempotency_and_changed_request_rejected(self):
        req = request()
        accepted = self.broker.submit("alice",req)
        self.assertEqual(self.broker.submit("alice",deepcopy(req)),accepted)
        req["point"]["lat"] = 41
        with self.assertRaises(QueryError) as error:
            self.broker.submit("alice",req)
        self.assertEqual(error.exception.status,409)

    def test_bounded_queue_and_expiry(self):
        now = [1.]
        broker = QueryBroker(clock=lambda:now[0])
        broker.worker_poll("worker-A")
        for i in range(MAX_QUERIES):
            req = request(); req["request_id"] += str(i)
            broker.submit("alice",req)
        req["request_id"] += "extra"
        with self.assertRaises(QueryError) as error: broker.submit("alice",req)
        self.assertEqual(error.exception.status,429)
        now[0] = 200
        self.assertFalse(broker.capabilities()["worker"])
        self.assertEqual(len(broker.queries),0)

    def test_prepared_worker_busy_online_accepts_bounded_queue_without_claim(self):
        broker = QueryBroker()
        self.addCleanup(broker.close)
        self.assertIsNone(broker.worker_poll('worker-A', busy=True, ready=True)['query'])
        self.assertTrue(broker.capabilities()['worker'])
        accepted = broker.submit('alice', request())
        self.assertIsNone(broker.worker_poll('worker-A', busy=True, ready=True)['query'])
        claimed = broker.worker_poll('worker-A', busy=False, ready=True)['query']
        self.assertEqual(claimed['query_id'], accepted['query_id'])
        broker.worker_poll('worker-A', busy=True, ready=False)
        self.assertFalse(broker.capabilities()['worker'])

    def test_no_implicit_local_fallback(self):
        broker = QueryBroker()
        req = request()
        with self.assertRaises(QueryError) as error: broker.submit("alice",req)
        self.assertEqual(error.exception.status,503)
        self.assertEqual(len(broker.queries),0)

    def test_mismatched_point_and_unvalidated_science_rejected(self):
        self.broker.submit("alice",request())
        job = self.broker.worker_poll("worker-A")["query"]
        result = Executor().execute(job["request"])
        result["point"]["lon"] = 99
        with self.assertRaises(QueryError): self.broker.finish("worker-A",{**job,"result":result})
        result = Executor().execute(job["request"])
        result["provenance"]["scientifically_validated"] = True
        with self.assertRaises(QueryError): self.broker.finish("worker-A",{**job,"result":result})

    def test_http_worker_transport_and_local_parity(self):
        broker = self.broker
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                if self.headers.get("Authorization") != "Bearer isolated-test-token":
                    self.send_error(403); return
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path != worker.WORKER_PATH or payload["protocol"] != worker.PROTOCOL:
                    self.send_error(400); return
                result = broker.worker_poll(payload["worker_id"]) if payload["action"] == "poll" else broker.finish(payload["worker_id"],payload)
                raw = json.dumps(result).encode()
                self.send_response(200);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
        server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        coordinator = dict(coordinator_id="isolated",rainmapper_url=f"http://127.0.0.1:{server.server_port}",token="isolated-test-token")
        before = deepcopy(coordinator)
        stop = threading.Event()
        thread = threading.Thread(target=worker.run_loop,args=([coordinator],"worker-A",{"isolated":Executor()},stop),daemon=True)
        thread.start();self.addCleanup(lambda:(stop.set(),thread.join(timeout=2)))
        req = request()
        remote = broker.submit("alice",req)
        local = QueryBroker(Executor());self.addCleanup(local.close)
        deadline=time.monotonic()+4
        while not local.local_ready and time.monotonic()<deadline: time.sleep(.01)
        local_req = {**req,"execution":"local"}
        accepted = local.submit("alice",local_req)
        while time.monotonic()<deadline:
            remote_status, remote_result = broker.status("alice",remote["query_id"])
            local_status, local_result = local.status("alice",accepted["query_id"])
            if remote_status == local_status == 200: break
            time.sleep(.02)
        self.assertEqual((remote_status,local_status),(200,200))
        self.assertEqual(remote_result["execution"]["mode"],"worker")
        self.assertEqual(local_result["execution"]["mode"],"local")
        remote_result.pop("execution");local_result.pop("execution")
        self.assertEqual(remote_result,local_result)
        self.assertEqual(coordinator,before)
