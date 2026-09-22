"""Optional prediction-map route using the unmodified meteorological viewer."""

from __future__ import annotations

import json
import os
import threading
from zoneinfo import available_timezones
from pathlib import Path

import mushroom_profiles_ui
from rainmapper_core import mushroom_prediction_map as contract
from rainmapper_core import mushroom_map_history as history
from rainmapper_core.mushroom_map_queries import QueryBroker, QueryError

_broker = None
_broker_lock = threading.Lock()


def broker():
    global _broker
    with _broker_lock:
        if _broker is None:
            executor = None
            publication = None
            geography = None
            path = os.environ.get("RAINMAPPER_PREDICTION_MAP_CONFIG")
            if not path:
                for installed in (Path('/share/rainmapper/prediction-map/config.json'),
                                  Path('/media/rainmapper/geography/map-config.json')):
                    if installed.is_file():
                        path = str(installed)
                        break
            if path:
                from rainmapper_core.mushroom_map_execution import load_config, PointExecutor
                config, root = load_config(path)
                if config.get("geography_publication_root"):
                    from rainmapper_core.mushroom_map_geography_runtime import GeographyPublication, PublishedPointExecutor
                    geography = GeographyPublication(root / config["geography_publication_root"])
                    executor = PublishedPointExecutor(config, root, geography)
                else:
                    executor = PointExecutor(config,root)
                if config.get("private_runtime"):
                    from rainmapper_core.mushroom_map_runtime import MapPublication
                    publication = MapPublication(config, root)
            _broker = QueryBroker(executor, publication=publication, geography=geography)
        return _broker


def serve_worker_api(handler, authenticate):
    from rainmapper_core.mushroom_map_worker import PROTOCOL
    from rainmapper_core.mushroom_worker_registry import WORKER_ID_PATTERN
    try:
        raw = handler.read_request_body(contract.MAX_RESULT_BYTES+4096)
        if len(raw) > contract.MAX_RESULT_BYTES+4096:
            raise QueryError("worker_payload_limit",413)
        payload = json.loads(raw)
        token, _ = handler.auth_credentials()
        worker_id = payload.get("worker_id", "")
        if not isinstance(worker_id,str) or not WORKER_ID_PATTERN.fullmatch(worker_id) or not authenticate(worker_id,token):
            raise QueryError("forbidden",403)
        if payload.get("protocol") != PROTOCOL:
            raise QueryError("unsupported_protocol")
        if payload.get("action") in {"runtime_manifest", "runtime_object", "geography_manifest", "geography_object"}:
            public_geo = payload["action"].startswith("geography_")
            publication = broker().geography if public_geo else broker().publication
            if publication is None: raise QueryError("map_runtime_unavailable", 503)
            fingerprint = payload.get("fingerprint")
            if not isinstance(fingerprint, str): raise QueryError("invalid_map_reference")
            if payload["action"].endswith("_manifest"):
                from rainmapper_core.mushroom_map_runtime import encode
                raw_manifest = encode(publication.lookup(fingerprint)["manifest"])
                handler.send_bytes(200, raw_manifest, "application/json", {"Cache-Control":"no-store"})
            else:
                offset = payload.get("offset", 0) if public_geo else 0
                source, size = (publication.object(fingerprint, payload.get("file"), offset) if public_geo
                                else publication.object(fingerprint, payload.get("file")))
                with source.open("rb") as stream:
                    if not public_geo and source.stat().st_size != size: raise QueryError("map_object_changed", 409)
                    stream.seek(offset)
                    handler.send_response(200)
                    handler.send_header("Content-Type", "application/octet-stream")
                    handler.send_header("Content-Length", str(size))
                    handler.send_header("Cache-Control", "no-store")
                    handler.end_headers()
                    remaining = size
                    while remaining:
                        chunk = stream.read(min(1024*1024, remaining))
                        if not chunk: raise OSError("map_object_truncated")
                        handler.wfile.write(chunk); remaining -= len(chunk)
            return
        if payload.get("action") in {"poll", "busy"}:
            current = broker()
            reference, geo_ref = None, None
            eligible = True
            if current.publication:
                try: reference = current.publication.reference()
                except QueryError: reference = None
                eligible = eligible and reference is not None and payload.get("ready_fingerprint") == reference['fingerprint']
                if reference:
                    eligible = eligible and set(reference.get('required_capabilities', [])) <= set(payload.get('capabilities') or [])
            if current.geography:
                try: geo_ref = current.geography.reference()
                except QueryError: geo_ref = None
                eligible = eligible and geo_ref is not None and payload.get('ready_geography') == geo_ref['fingerprint']
                if reference and geo_ref:
                    reference = {**reference, 'geography': geo_ref}
            # Cache eligibility survives a busy online slot; the bounded map
            # queue can wait without accepting unprepared/stale generations.
            if not current.publication and not current.geography and payload['action'] == 'busy':
                eligible = False
            result = current.worker_poll(worker_id, busy=payload['action'] == 'busy' or not eligible, ready=eligible, capabilities=payload.get("capabilities"))
            if current.publication: result['runtime'] = reference
            if current.geography:
                result['geography'] = geo_ref
        elif payload.get("action") == "finish":
            result = broker().finish(worker_id,payload)
        else:
            raise QueryError("invalid_action")
        send_json(handler,200,result)
    except (ValueError, TypeError, AttributeError) as error:
        send_json(handler,getattr(error,"status",400),{"error":str(error)})


def send_json(handler, status: int, payload: dict) -> None:
    handler.send_bytes(status, contract.encode_result(payload), "application/json; charset=utf-8",
                       {"Cache-Control": "no-store, max-age=0"})


def serve_api(handler, path: str, *, post: bool = False) -> None:
    user = handler.require_authentication()
    if not user:
        return
    if not contract.can_access(user) and user.get(history.PERMISSION) is not True:
        send_json(handler, 403, {"ok": False, "error": "forbidden"})
        return
    action = path.removeprefix(contract.API_PATH)
    if not post and action == "/capabilities":
        current = broker()
        available = current.capabilities()
        data_mode = "prediction" if getattr(current.executor, "model", None) is not None else "simulation"
        send_json(handler, 200, {
            "contract": contract.CONTRACT_ID, contract.PERMISSION: contract.can_access(user),
            history.PERMISSION: user.get(history.PERMISSION) is True,
            "history_contract": history.CONTRACT,
            "admin_only": False, "data_mode": data_mode, "worker_ready": available["worker"],
            "executors": available,
            "calendar_timezone": getattr(current.executor,'calendar_timezone','Europe/Madrid'),
            "max_horizon_days": 7, "max_species": contract.MAX_SPECIES,
        })
        return
    if post and action in {"/demo", "/queries"}:
        try:
            request = contract.parse_request(handler.read_request_body(contract.MAX_REQUEST_BYTES))
            historical = history.is_request(request)
            if not (user.get(history.PERMISSION) is True if historical else contract.can_access(user)):
                raise QueryError('forbidden', 403)
            if historical:
                if action != '/queries':
                    raise QueryError('invalid_action')
                from rainmapper_core.geojson import load_ignore_station_codes
                request['settings'] = {'include_aemet': True, 'minimum_rain': 0,
                    'history_records': min(90, max(1, int(os.environ.get('RAINMAPPER_LAST_RAINS_HISTORY', '30')))),
                    'ignored': sorted(load_ignore_station_codes(os.environ.get('RAINMAPPER_IGNORE_STATIONS_TOMAP_FILE', '/app/ignore_stations_tomap.txt')))}
            if action == "/queries":
                accepted = broker().submit(str(user.get("username","admin")),request)
                send_json(handler,202,accepted)
                return
            send_json(handler, 200, contract.demo_result(request))
        except ValueError as exc:
            send_json(handler, getattr(exc,"status",400), {"ok": False, "error": str(exc)})
        return
    if action.startswith("/queries/"):
        parts = action.split("/")
        cancelling = post and len(parts) == 4 and parts[3] == "cancel"
        if cancelling or (not post and len(parts) == 3):
            try:
                historical = broker().is_history(str(user.get('username', 'admin')), parts[2])
                if not (user.get(history.PERMISSION) is True if historical else contract.can_access(user)):
                    raise QueryError('forbidden', 403)
                status, result = broker().status(str(user.get("username","admin")),parts[2],cancel=cancelling)
                send_json(handler,status,result)
            except QueryError as error:
                send_json(handler,error.status,{"error":str(error)})
            return
    send_json(handler, 404, {"ok": False, "error": "not_found"})


def serve_viewer(handler, requested_path: str, *, assets: Path, config_js: str, cache_bust) -> None:
    if not requested_path:
        handler.redirect_to("/protected/maplibre/index.html")
        return
    relative = requested_path.lstrip("/") or "index.html"
    extension_assets = assets.parent / "prediction-map"
    if relative == "index.html":
        # Both viewer URLs compose the shared weather template and resources.
        try:
            page = cache_bust((assets / "index.html").read_text(encoding="utf-8"))
        except OSError:
            handler.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
            return
        page = page.replace("</body>", '<script src="prediction-bootstrap.js"></script>\n</body>')
        handler.send_bytes(200, page.encode("utf-8"), "text/html; charset=utf-8",
                           {"Cache-Control": "no-store, max-age=0"})
        return
    if relative == "config.js":
        labels = {key.removeprefix("ui.prediction_map_"): values
                  for key, values in mushroom_profiles_ui.PARAMETER_LABELS.items()
                  if key.startswith("ui.prediction_map_")}
        config = {"apiBase": contract.API_PATH, "contract": contract.CONTRACT_ID, "labels": labels,
                  "historyContract": history.CONTRACT,
                  "calendarTimezones": sorted(available_timezones()),
                  "defaultCalendarTimezone": "Europe/Madrid"}
        source = config_js + "\nwindow.RAINMAPPER_CONFIG.predictionMap = " + json.dumps(config) + ";\n"
        handler.send_bytes(200, source.encode("utf-8"), "application/javascript",
                           {"Cache-Control": "no-store, max-age=0"})
        return
    if relative in {"prediction-bootstrap.js", "prediction-mode.js", "prediction-mode.css", "prediction-weather.js", "historical-mode.js", "historical-mode.css"}:
        content_type = "text/css" if relative.endswith(".css") else "application/javascript"
        try:
            source = (extension_assets / relative).read_bytes()
        except OSError:
            handler.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
            return
        handler.send_bytes(200, source, content_type,
                           {"Cache-Control": "no-store, max-age=0"})
        return
    handler.serve_protected_maplibre("/" + relative)
