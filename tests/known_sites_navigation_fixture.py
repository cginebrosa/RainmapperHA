"""Isolated HTTP fixture: real UI/save handler, temporary sites and observations."""
import json
import os
import sys
from http.server import ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
data = Path(sys.argv[1]).resolve()
data.mkdir(parents=True, exist_ok=True)
os.environ.update(RAINMAPPER_MUSHROOM_UI_LANGUAGE="es", RAINMAPPER_MUSHROOM_DATA_DIR=str(data), RAINMAPPER_MUSHROOM_DEFAULTS_DIR=str(ROOT / "mushroom-data"))
sys.path[:0] = [str(ROOT), str(ROOT / "rainmapper-app/app")]
import web_server as web
import mushroom_profiles_ui as ui
from rainmapper_core import mushroom_known_sites as sites, mushroom_soilgrids
from rainmapper_core.mushroom_store import MushroomDataStore

store = MushroomDataStore(defaults_dir=ROOT / "mushroom-data", data_dir=data)
for kind in ("profiles", "catalogs", "gis"):
    store.persistent_path(kind).write_bytes(store.default_path(kind).read_bytes())
row = {"observation_id":"fixture_obs", "species_id":"amanita_caesarea", "observed_at":"2025-09-28", "flush_abundance":"normal", "source_quality":0.75,
       "location":{"lat":42.15,"lon":1.44,"precision_m":71}, "observer":{"name":"GBIF"}, "source":{"type":"gbif","name":"GBIF"},
       "validation_status":"draft", "calibration_use":"review", "micro_area_id":"fixture_micro"}
store.persistent_path("observations").write_text(json.dumps({"schema_version":"0.3", "observations":[row]}))
payload=sites.default_payload()
area=sites.empty_area('fixture_area');area['name']='Área de prueba'
area['geometry']={"type":"Polygon","coordinates":[[[1.42,42.13],[1.46,42.13],[1.46,42.17],[1.42,42.17],[1.42,42.13]]]}
micro=sites.empty_micro_area('fixture_micro','fixture_area');micro['name']='Microárea de prueba'
micro['geometry']={"type":"Polygon","coordinates":[[[1.435000000000001,42.145],[1.445,42.145],[1.445,42.155],[1.435,42.155],[1.435000000000001,42.145]]]}
# Generated with GDAL: WGS84 AEQD at 42.15,1.44, Buffer(500/cos(pi/256),64),
# then transformed to EPSG:4326, exactly as GBIF's area creation does.
gbif_area=sites.empty_area('fixture_gbif_circle');gbif_area['name']='Círculo GBIF sintético'
gbif_area['geometry']=json.loads((ROOT / 'tests/fixtures/known_sites_gbif_circle.json').read_text())
payload['areas']=[area,gbif_area];payload['micro_areas']=[micro]
sites.persistent_path().write_text(json.dumps(payload))
web.default_store=lambda:store
# A geometry save must not download new geography in this test.
mushroom_soilgrids.resolve_geometry_context=lambda _root, geometry, **_:mushroom_soilgrids.pending_context(geometry,tile_ids=[],reasons=['fixture'])

class Handler(web.RainmapperHandler):
    def trusted_worker_control_request(self): return True
    def allow_listener_path(self, method, path): return True
    def do_GET(self):
        if urlparse(self.path).path == '/auth/device-settings':
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            language = cookie.get('fixture_language')
            self.send_json(200, {'ok': True, 'settings': {'language': language.value} if language else {}})
        elif urlparse(self.path).path == '/mushrooms/fixture-observation':
            form=ui.render_observation_form_modal(store.load('profiles')['species_profiles'],store.load('catalogs')['catalogs'],row,
                modal_id='edit-fixture',action='update_observation',title='Fixture',selected_species_id='amanita_caesarea')
            self.send_bytes(200,web.html_page('Fixture',form,auto_refresh=False),'text/html; charset=utf-8')
        elif urlparse(self.path).path == '/mushrooms/fixture-filters':
            q=parse_qs(urlparse(self.path).query)
            form='<form class="observations-filters">'+''.join(ui.render_observation_date_filter(name,name,(q.get(name) or [''])[0]) for name in ('date_from','date_to'))+'<button type="button" id="outside">Outside</button></form>'
            self.send_bytes(200,web.html_page('Date filters',form,auto_refresh=False),'text/html; charset=utf-8')
        elif urlparse(self.path).path in {'/mushrooms/known-sites','/api/mushrooms/known-site-detail','/api/mushrooms/known-sites-workspace'}:
            super().do_GET()
        else:self.send_error(404)
    def do_POST(self):
        if urlparse(self.path).path=='/mushrooms/known-sites':super().do_POST()
        else:self.send_error(404)

server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
print(json.dumps({'port':server.server_port}),flush=True)
server.serve_forever()
