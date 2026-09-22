"""Contract and real handler dispatch tests, without user data, GIS or jobs."""

from __future__ import annotations

import importlib.util
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from rainmapper_core import mushroom_prediction_map as contract

ROOT = Path(__file__).resolve().parents[1]


def request(**changes):
    return {"contract": contract.CONTRACT_ID, "request_id": "test_request_0001",
            "point": {"lat": 42.0, "lon": 1.9}, "start_date": "2026-09-12",
            "horizon_days": 7, "history_days": 30, "species_ids": [], **changes}


class PredictionMapContractTests(unittest.TestCase):
    def test_model_error_is_bounded_and_cannot_accompany_predictions(self):
        req = request()
        result = contract.prediction_result(req)
        result.update(execution={'mode': 'local'}, model_status='unavailable', model_error='quality_read_limit')
        contract.validate_result(result, req)
        for value in ('/private/exception', 'x'*5000, {}, None):
            with self.subTest(value=str(value)[:40]), self.assertRaisesRegex(ValueError, 'invalid_result_model_error'):
                contract.validate_result({**result, 'model_error': value}, req)
        with self.assertRaisesRegex(ValueError, 'invalid_result_model_error'):
            contract.validate_result({**result, 'species': [{'probabilities': [.9]}]}, req)

    def test_calendar_timezone_is_validated_and_bound_to_response(self):
        for zone in ('Europe/Madrid','Atlantic/Canary','UTC'):
            req=contract.parse_request(json.dumps(request(calendar_timezone=zone)).encode())
            result=contract.demo_result(req)
            result['execution']={'mode':'local'}
            contract.validate_result(result,req)
            result['calendar_timezone']='Pacific/Honolulu'
            with self.assertRaisesRegex(ValueError,'invalid_result_calendar_timezone'):
                contract.validate_result(result,req)
        for zone in (None,True,{},'', 'x'*65, '../UTC','/etc/passwd','Not/AZone'):
            with self.subTest(zone=zone),self.assertRaisesRegex(ValueError,'invalid_calendar_timezone'):
                contract.parse_request(json.dumps(request(calendar_timezone=zone)).encode())

    def test_valid_request_does_not_create_an_area(self):
        parsed = contract.parse_request(json.dumps(request()).encode())
        self.assertEqual(parsed, request())
        self.assertNotIn("area_id", parsed)

    def test_reject_invalid_or_unbounded_inputs(self):
        cases = [
            {"horizon_days": 15}, {"horizon_days": True}, {"history_days": 365},
            {"start_date": "2026-02-30"}, {"start_date": "20260912"},
            {"point": {"lat": float("nan"), "lon": 0}},
            {"point": {"lat": 10 ** 500, "lon": 0}},
            {"point": {"lat": True, "lon": 0}},
            {"point": {"lat": 91, "lon": 0}},
            {"point": {"lat": 40, "lon": 181}},
            {"point": {"lat": 40, "lon": 1, "url": "file:///private"}},
            {"species_ids": ["a"] * 33}, {"species_ids": ["a", "a"]},
            {"species_ids": ["../../file"]}, {"request_id": "<script>"},
            {"contract": "area_predictor_v1"}, {"area_id": "existing_site"},
            {"execution":"automatic"}, {"execution":True},
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                contract.parse_request(json.dumps(request(**changes)).encode())
        for raw in (b"{", b"null", b"[]", b"\xff", b" " * (contract.MAX_REQUEST_BYTES + 1)):
            with self.subTest(raw=raw[:10]), self.assertRaises(ValueError):
                contract.parse_request(raw)

    def test_demo_is_small_explicit_and_preserves_missing_values(self):
        result = contract.demo_result(request())
        self.assertEqual(result["data_mode"], "simulation")
        self.assertFalse(result["provenance"]["scientifically_validated"])
        self.assertEqual(len(result["dates"]), 7)
        self.assertIsNone(result["species"][1]["probabilities"][2])
        self.assertEqual(result["species"][2]["status"], "no_model")
        self.assertLess(len(contract.encode_result(result)), 2048)
        self.assertNotIn("forecast", result)

    def test_individual_permission_is_explicit_for_every_role(self):
        self.assertFalse(contract.can_access(None))
        for role in ("free", "basic", "pro", "admin"):
            for value in (None, False, "true", 1):
                self.assertFalse(contract.can_access({"role": role, contract.PERMISSION: value}))
            self.assertTrue(contract.can_access({"role": role, contract.PERMISSION: True}))


class PredictionMapRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("prediction_map_web_test", ROOT / "rainmapper-app/app/web_server.py")
        cls.web = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.web)
        cls.web.MAPLIBRE_VIEWER_ASSETS_PATH = ROOT / "rainmapper_core/viewers/maplibre-viewer"

    def handler(self, path, *, user=None, body=None):
        handler = self.web.RainmapperHandler.__new__(self.web.RainmapperHandler)
        handler.path = path
        handler.server = SimpleNamespace(rainmapper_listener_role="web")
        handler.authenticated_user = mock.Mock(return_value=user)
        handler.send_bytes = mock.Mock()
        raw = json.dumps(body).encode() if body is not None else b""
        handler.headers = {"Content-Length": str(len(raw))}
        handler.rfile = io.BytesIO(raw)
        handler.command = "POST" if body is not None else "GET"
        return handler

    def response(self, handler):
        args = handler.send_bytes.call_args.args
        return args[0], json.loads(args[1])

    def test_history_permission_defaults_off_and_independent_routes(self):
        from rainmapper_core import mushroom_map_history as history
        from tests.test_mushroom_map_history import request as history_request
        from rainmapper_core.mushroom_map_queries import QueryBroker
        for role in ('free','basic','pro','admin'):
            self.assertFalse(self.web.user_auth_payload({'role':role,'username':'test'})[history.PERMISSION])
            self.assertEqual(self.web.default_user_permission(role,history.PERMISSION),'false')
        isolated=QueryBroker()
        isolated.local_ready=True
        ui=self.web.mushroom_prediction_map_ui
        with mock.patch.object(ui,'_broker',isolated):
            user={'username':'test',contract.PERMISSION:True}
            denied=self.handler(contract.API_PATH+'/queries',user=user,body=history_request())
            denied.do_POST();self.assertEqual(self.response(denied)[0],403)
            user={**user,history.PERMISSION:True}
            allowed=self.handler(contract.API_PATH+'/queries',user=user,body=history_request())
            allowed.do_POST();code,body=self.response(allowed);self.assertEqual(code,202)
            status=self.handler(contract.API_PATH+'/queries/'+body['query_id'],user={**user,history.PERMISSION:False})
            status.do_GET();self.assertEqual(self.response(status)[0],403)
            only_history=self.handler(contract.API_PATH+'/capabilities',user={'username':'test',history.PERMISSION:True})
            only_history.do_GET();code,body=self.response(only_history)
            self.assertEqual(code,200);self.assertTrue(body[history.PERMISSION]);self.assertFalse(body[contract.PERMISSION])

    def test_capabilities_authorization_and_revocation(self):
        for user, status in ((None, 401), ({"role": "free", contract.PERMISSION: True}, 200),
                             ({"role": "admin"}, 403),
                             ({"role": "admin", contract.PERMISSION: True}, 200)):
            with self.subTest(user=user):
                handler = self.handler(contract.API_PATH + "/capabilities", user=user)
                handler.do_GET()
                self.assertEqual(self.response(handler)[0], status)
        handler.authenticated_user.return_value = {"role": "free"}
        handler.do_GET()
        self.assertEqual(self.response(handler)[0], 403)

    def test_demo_and_real_endpoint_never_launch_jobs(self):
        with mock.patch.object(self.web.mushroom_worker_jobs, "create_predictor_job") as launch:
            demo = self.handler(contract.API_PATH + "/demo", user={"username": "test", "role": "admin", contract.PERMISSION: True}, body=request())
            demo.do_POST()
            self.assertEqual(self.response(demo)[1]["data_mode"], "simulation")
            self.assertIn("no-store", demo.send_bytes.call_args.args[3]["Cache-Control"])
            real = self.handler(contract.API_PATH + "/queries", user={"username": "test", "role": "admin", contract.PERMISSION: True}, body=request())
            real.do_POST()
            self.assertEqual(self.response(real)[0], 503)
            launch.assert_not_called()

    def test_demo_checks_auth_and_rejects_oversize_before_reading(self):
        handler = self.handler(contract.API_PATH + "/demo", body=request())
        handler.do_POST()
        self.assertEqual(self.response(handler)[0], 401)
        handler = self.handler(contract.API_PATH + "/demo", user={"username": "test", "role": "admin", contract.PERMISSION: True}, body=request())
        handler.headers["Content-Length"] = str(contract.MAX_REQUEST_BYTES + 1)
        handler.do_POST()
        self.assertEqual(self.response(handler)[0], 413)
        self.assertEqual(handler.rfile.tell(), 0)

    def test_both_routes_compose_the_same_unified_map(self):
        bare = self.handler(contract.VIEWER_PATH)
        bare.redirect_to = mock.Mock()
        bare.do_GET()
        bare.redirect_to.assert_called_once_with("/protected/maplibre/index.html")
        old = self.handler("/protected/maplibre/index.html")
        old.do_GET()
        new = self.handler(contract.VIEWER_PATH + "/index.html")
        new.do_GET()
        old_html = old.send_bytes.call_args.args[1].decode()
        new_html = new.send_bytes.call_args.args[1].decode()
        extension = '<script src="prediction-bootstrap.js"></script>\n'
        self.assertIn(extension, old_html)
        self.assertEqual(new_html, old_html)

    def test_weather_data_remains_available_without_prediction_permission(self):
        handler = self.handler(contract.VIEWER_PATH + "/data/07d.geojson", user={"role": "free"})
        handler.serve_static_file = mock.Mock()
        handler.do_GET()
        handler.serve_static_file.assert_called_once()
        for suffix in ("/../config.yaml", "/prediction-mode.js/../secret"):
            handler = self.handler(contract.VIEWER_PATH + suffix)
            handler.do_GET()
            self.assertEqual(handler.send_bytes.call_args.args[0], 400)

    def test_no_new_endpoints_on_worker_listener(self):
        handler = self.handler(contract.API_PATH + "/demo", user={"username": "test", "role": "admin", contract.PERMISSION: True}, body=request())
        handler.server.rainmapper_listener_role = "worker"
        handler.do_POST()
        self.assertEqual(self.response(handler)[0], 404)

    def test_report_worker_route_requires_auth_and_small_payload(self):
        from rainmapper_core.mushroom_map_queries import QueryBroker, WORKER_PATH
        body = {"protocol":"map_report_v1","worker_id":"worker-test","action":"poll"}
        handler = self.handler(WORKER_PATH,body=body)
        handler.server.rainmapper_listener_role = "worker"
        handler.auth_credentials = mock.Mock(return_value=("isolated-token",""))
        with mock.patch.object(self.web,"mushroom_worker_api_enabled",return_value=True), \
             mock.patch.object(self.web,"authenticate_mushroom_worker",return_value=False):
            handler.do_POST()
        self.assertEqual(self.response(handler)[0],403)
        isolated = QueryBroker()
        with mock.patch.object(self.web.mushroom_prediction_map_ui,"_broker",isolated), \
             mock.patch.object(self.web,"mushroom_worker_api_enabled",return_value=True), \
             mock.patch.object(self.web,"authenticate_mushroom_worker",return_value=True):
            handler.do_POST()
        self.assertEqual(self.response(handler),(200,{"query":None}))
        handler = self.handler(WORKER_PATH,body={**body,"action":"busy"})
        handler.server.rainmapper_listener_role = "worker"
        handler.auth_credentials = mock.Mock(return_value=("isolated-token",""))
        with mock.patch.object(self.web.mushroom_prediction_map_ui,"_broker",isolated), \
             mock.patch.object(self.web,"mushroom_worker_api_enabled",return_value=True), \
             mock.patch.object(self.web,"authenticate_mushroom_worker",return_value=True):
            handler.do_POST()
        self.assertEqual(self.response(handler),(200,{"query":None}))
        self.assertFalse(isolated.capabilities()["worker"])
        self.assertTrue(isolated.workers)
        oversized = self.handler(WORKER_PATH,body=body)
        oversized.server.rainmapper_listener_role = "worker"
        oversized.headers["Content-Length"] = str(contract.MAX_RESULT_BYTES+4097)
        oversized.do_POST()
        self.assertEqual(self.response(oversized)[0],413)
        self.assertEqual(oversized.rfile.tell(),0)

    def test_all_ui_labels_are_available_in_three_languages(self):
        labels = json.loads((ROOT / "mushroom-data/mushroom_labels.json").read_text())
        selected = {k: v for k, v in labels.items() if k.startswith("ui.prediction_map_")}
        self.assertTrue(selected)
        for key, translations in selected.items():
            self.assertEqual(set(translations), {"en", "es", "ca"}, key)
            self.assertTrue(all(translations.values()), key)

    def test_geography_requires_matching_ready_version_and_busy_still_receives_reference(self):
        from rainmapper_core.mushroom_map_queries import QueryBroker, WORKER_PATH
        publication, geography = mock.Mock(), mock.Mock()
        publication.reference.return_value = {'fingerprint': 'sha256:'+'a'*64}
        geography.reference.return_value = {'fingerprint': 'sha256:'+'b'*64}
        geography.lookup.return_value = {'manifest': {'files': []}}
        isolated = QueryBroker(publication=publication, geography=geography)
        self.addCleanup(isolated.close)
        ui = self.web.mushroom_prediction_map_ui
        def call(action, authorized=True, **fields):
            handler = self.handler(WORKER_PATH, body={'protocol': 'map_report_v1',
                'worker_id': 'worker-test', 'action': action, **fields})
            handler.auth_credentials = mock.Mock(return_value=('test-token', ''))
            with mock.patch.object(ui, '_broker', isolated):
                ui.serve_worker_api(handler, lambda worker_id, token: authorized)
            return self.response(handler)
        private, public = publication.reference.return_value, geography.reference.return_value
        self.assertEqual(call('geography_manifest', False, **public)[0], 403)
        geography.lookup.assert_not_called()
        self.assertEqual(call('geography_manifest', **public)[0], 200)
        self.assertEqual(call('busy')[1]['geography'], public)
        self.assertFalse(isolated.capabilities()['worker'])
        call('poll', ready_fingerprint=private['fingerprint'])
        self.assertFalse(isolated.capabilities()['worker'])
        call('poll', ready_fingerprint=private['fingerprint'], ready_geography=public['fingerprint'])
        self.assertTrue(isolated.capabilities()['worker'])
        call('busy', ready_fingerprint=private['fingerprint'], ready_geography=public['fingerprint'])
        self.assertTrue(isolated.capabilities()['worker'])
        geography.reference.return_value = {'fingerprint': 'sha256:'+'c'*64}
        call('poll', ready_fingerprint=private['fingerprint'], ready_geography=public['fingerprint'])
        self.assertFalse(isolated.capabilities()['worker'])

    def test_private_runtime_requires_auth_and_matching_ready_reference(self):
        from rainmapper_core.mushroom_map_queries import QueryBroker, WORKER_PATH, QueryError
        publication = mock.Mock()
        publication.reference.return_value = {'fingerprint':'sha256:'+'a'*64}
        publication.lookup.return_value = {'manifest':{'files':[]}}
        isolated = QueryBroker(publication=publication)
        ui = self.web.mushroom_prediction_map_ui
        def call(action, authorized=True, **fields):
            body={'protocol':'map_report_v1','worker_id':'worker-test','action':action,**fields}
            handler=self.handler(WORKER_PATH,body=body)
            handler.auth_credentials=mock.Mock(return_value=('test-token',''))
            with mock.patch.object(ui,'_broker',isolated):
                ui.serve_worker_api(handler,lambda worker_id,token:authorized)
            return handler
        ref=publication.reference.return_value
        self.assertEqual(self.response(call('runtime_manifest',False,**ref))[0],403)
        publication.lookup.assert_not_called()
        self.assertEqual(self.response(call('runtime_manifest',**ref))[0],200)
        self.response(call('poll',ready_fingerprint=None))
        self.assertFalse(isolated.capabilities()['worker'])
        self.response(call('poll',ready_fingerprint=ref['fingerprint']))
        self.assertTrue(isolated.capabilities()['worker'])
        publication.reference.side_effect=QueryError('map_data_not_ready',503)
        self.response(call('poll',ready_fingerprint=ref['fingerprint']))
        self.assertFalse(isolated.capabilities()['worker'])
        publication.object.side_effect=QueryError('map_object_not_authorized',403)
        self.assertEqual(self.response(call('runtime_object',file='../../private',**ref))[0],403)


if __name__ == "__main__":
    unittest.main()
