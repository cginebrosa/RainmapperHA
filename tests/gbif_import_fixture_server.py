"""Temporary-store HTTP fixture for the GBIF browser test; never starts app jobs."""
import json
import os
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["RAINMAPPER_MUSHROOM_UI_LANGUAGE"] = "es"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "rainmapper-app/app"))
import web_server as web
import mushroom_gbif_ui
import mushroom_profiles_ui as ui
from rainmapper_core.mushroom_store import MushroomDataStore

data = Path(sys.argv[1])
data.mkdir(parents=True, exist_ok=True)
store = MushroomDataStore(defaults_dir=ROOT / "mushroom-data", data_dir=data)
for kind in ("profiles", "catalogs", "gis"):
    store.persistent_path(kind).write_bytes(store.default_path(kind).read_bytes())
store.persistent_path("observations").write_bytes((ROOT / "rainmapper-app/defaults/mushroom_observations.json").read_bytes())
# Deterministic GIS fixture; real configured layers are checked separately in HA local.
from rainmapper_core import mushroom_gis_recovery, mushroom_gis_lab, mushroom_soilgrids
mushroom_gis_lab.derive_site_gis_dem = lambda *_: {"dem_status": "ok", "altitude_min_m": 400, "altitude_max_m": 450, "altitude_mean_m": 425, "gis": {}}
mushroom_gis_recovery.observation_preview = lambda lat, lon, *_: {
    "version": 1, "location": mushroom_gis_recovery.point(lat, lon),
    "values": {}, "sources": {}, "forest": {"status": "not_connected"}, "gaps": ["fixture"],
}
mushroom_soilgrids.resolve_geometry_context = lambda _root, geometry, **_: mushroom_soilgrids.pending_context(geometry, tile_ids=[], reasons=['fixture_no_coverage'])
web.default_store = lambda: store
ui.UI_LANGUAGE = "es"


class Handler(web.RainmapperHandler):
    def trusted_worker_control_request(self):
        return True

    def do_GET(self):
        self.send_bytes(200, ("<!doctype html><meta charset=utf-8>" + mushroom_gbif_ui.render(ui.ui_label)).encode(), "text/html; charset=utf-8")


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
print(json.dumps({"port": server.server_port}), flush=True)
server.serve_forever()
