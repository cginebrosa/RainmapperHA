"""Functional tests for the lightweight MapLibre authentication backend.

These tests keep all state in a temporary directory so they do not touch the
real Home Assistant `/share/rainmapper` files or any developer-local devices.
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_SERVER_PATH = ROOT_DIR / "rainmapper-app" / "app" / "web_server.py"
MUSHROOM_PROFILES_UI_PATH = ROOT_DIR / "rainmapper-app" / "app" / "mushroom_profiles_ui.py"


def load_web_server_module():
    """Load `web_server.py` from its file path because `rainmapper-app` has a dash."""
    spec = importlib.util.spec_from_file_location("rainmapper_web_server_for_tests", WEB_SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load web_server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AuthDeviceLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.web_server = load_web_server_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        data_dir = Path(self.temp_dir.name)
        self.web_server.USERS_JSON_PATH = data_dir / "users.json"
        self.web_server.DEVICES_PATH = data_dir / "devices.json"

    def write_users_json(self, users: list[dict]) -> None:
        """Write the primary JSON user store used by new installations."""
        self.web_server.USERS_JSON_PATH.write_text(json.dumps({"users": users}), encoding="utf-8")

    def login(self, username: str, password: str, device_id: str) -> tuple[int, dict]:
        return self.web_server.login_user(username, password, device_id, "unit-test")

    def test_aemet_source_card_highlights_rate_limit_counters(self) -> None:
        html = self.web_server.source_status_card(
            "AEMET",
            {
                "status": "STALE",
                "exit_code": 2,
                "rows": 22774,
                "stations": 850,
                "duration_seconds": 0.2,
                "updated_at": "2026-06-24T12:00:00",
                "message": "Source failed; reused existing data.",
                "rate_limit_24h": 2,
                "consecutive_429_runs": 1,
            },
        )

        self.assertIn("AEMET 429 in last 24h: 2", html)
        self.assertIn("Consecutive AEMET 429 runs: 1", html)
        self.assertIn('class="source-alert"', html)
        self.assertIn('name="source_update" value="AEMET"', html)
        self.assertIn("Update only", html)

        ok_html = self.web_server.source_status_card(
            "AEMET",
            {
                "status": "OK",
                "exit_code": 0,
                "rate_limit_24h": 0,
                "consecutive_429_runs": 0,
            },
        )

        self.assertNotIn("AEMET 429 in last 24h", ok_html)
        self.assertNotIn("Consecutive AEMET 429 runs", ok_html)

    def test_control_panel_tabs_preserve_existing_actions_and_links(self) -> None:
        data_dir = Path(self.temp_dir.name)
        self.web_server.PLOTS_PATH = data_dir / "Plots"
        self.web_server.LOG_PATH = data_dir / "last_run.log"
        self.web_server.SOURCE_STATUS_PATH = data_dir / "source_status.json"
        self.web_server.STATIONS_PATH = data_dir / "stations.txt"
        self.web_server.WUNDERGROUND_STATIONS_DB_PATH = data_dir / "estacions_wunderground.csv"
        self.web_server.PUBLIC_MAPLIBRE_HEATMAP_PATH = data_dir / "rainmapper-maplibre-heatmap"
        self.web_server.PUBLIC_MAPLIBRE_AEMET_PATH = data_dir / "rainmapper-maplibre-aemet"
        self.web_server.PLOTS_PATH.mkdir()
        self.web_server.PUBLIC_MAPLIBRE_HEATMAP_PATH.mkdir()
        (self.web_server.PLOTS_PATH / "01_Tomap_Last_day.html").write_text("<html></html>", encoding="utf-8")
        (self.web_server.PLOTS_PATH / "04_Tomap_Last_three_weeks.html").write_text("<html></html>", encoding="utf-8")
        self.web_server.LOG_PATH.write_text(
            "- STATION404 status code=404\n- STATIONPARSE list index out of range\n",
            encoding="utf-8",
        )
        self.web_server.STATIONS_PATH.write_text(
            "https://www.wunderground.com/dashboard/pws/STATION404\n"
            "https://www.wunderground.com/dashboard/pws/STATIONPARSE\n"
            "# rainmapper-disabled:404 https://www.wunderground.com/dashboard/pws/STATIONOLD\n",
            encoding="utf-8",
        )
        self.web_server.SOURCE_STATUS_PATH.write_text(
            json.dumps(
                {
                    "sources": {
                        source: {
                            "status": "OK",
                            "exit_code": 0,
                            "rows": 10,
                            "stations": 2,
                            "duration_seconds": 1,
                            "updated_at": "2026-06-27T10:00:00",
                        }
                        for source in ("Meteoclimatic", "Meteocat", "Wunderground", "AEMET")
                    }
                }
            ),
            encoding="utf-8",
        )

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured = {}

        def capture_response(status: int, content: bytes, content_type: str) -> None:
            captured["status"] = status
            captured["content"] = content.decode("utf-8")
            captured["content_type"] = content_type

        handler.send_bytes = capture_response
        handler.render_index()

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        for label in ("Summary", "Data sources", "Viewers", "Maps", "Logs", "Errors"):
            self.assertIn(label, page)
        for action in ("Run update", "Generate maps", "Run all", "App settings", "Users", "Mushroom catalogs", "Mushroom species"):
            self.assertIn(action, page)
        for source in ("Meteoclimatic", "Meteocat", "Wunderground", "AEMET"):
            self.assertIn(f'name="source_update" value="{source}"', page)
        self.assertIn("Open Leaflet viewer", page)
        self.assertIn("Open MapLibre viewer", page)
        self.assertIn("Open heatmap experiment", page)
        self.assertIn("Open Bokeh 21 days", page)
        self.assertIn("01 Tomap Last day", page)
        self.assertIn("Open full log", page)
        self.assertIn("Disable all", page)
        self.assertIn("Enable all", page)

    def test_mushroom_catalogs_page_renders_reference_catalog_hub(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured = {}

        def capture_response(status: int, content: bytes, content_type: str) -> None:
            captured["status"] = status
            captured["content"] = content.decode("utf-8")
            captured["content_type"] = content_type

        handler.send_bytes = capture_response
        handler.render_mushroom_catalogs({"group": ["host_taxa"], "q": ["pinus"]})

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        self.assertIn("Catálogo maestro de referencia", page)
        self.assertIn("host_taxa", page)
        self.assertIn("host_pinus_spp", page)
        self.assertIn("Full catalog JSON import/export", page)
        self.assertIn('href="./profiles"', page)
        self.assertTrue((data_dir / "mushroom-data" / "mushroom_reference_catalogs.json").exists())

    def test_mushroom_profiles_page_renders_species_editor(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured = {}

        def capture_response(status: int, content: bytes, content_type: str) -> None:
            captured["status"] = status
            captured["content"] = content.decode("utf-8")
            captured["content_type"] = content_type

        handler.send_bytes = capture_response
        handler.render_mushroom_profiles({"id": ["boletus_pinophilus"]})

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        self.assertIn("Mantenimiento de especies", page)
        self.assertIn("Boletus pinophilus", page)
        self.assertIn("Host Affinities", page)
        self.assertIn("profile-metrics", page)
        self.assertIn("profile-tab-labels", page)
        self.assertIn("profile-list-rows", page)
        self.assertIn("profile-list-chip-legend", page)
        self.assertIn('title="Overall confidence:', page)
        self.assertIn('title="Calibration priority:', page)
        self.assertIn('title="Review status:', page)
        self.assertIn('name="profile_return_tab" value="profile-tab-general"', page)
        self.assertIn("Calibration", page)
        self.assertIn("Local calibration status", page)
        self.assertIn("Full profiles JSON import/export", page)
        self.assertIn('href="./catalogs"', page)
        self.assertIn("New species", page)
        self.assertIn('name="new_species_id"', page)
        self.assertIn('name="score_habitat"', page)
        self.assertIn('step="0.01"', page)
        self.assertIn("Current total", page)
        self.assertIn("Summary", page)
        self.assertIn("Species", page)
        self.assertIn("Observations", page)
        self.assertTrue((data_dir / "mushroom-data" / "mushroom_profiles.json").exists())

    def test_mushroom_profiles_v0_view_hides_parked_and_enriched_fields(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured = {}

        def capture_response(status: int, content: bytes, content_type: str) -> None:
            captured["status"] = status
            captured["content"] = content.decode("utf-8")
            captured["content_type"] = content_type

        handler.send_bytes = capture_response
        handler.render_mushroom_profiles({"id": ["boletus_pinophilus"], "view": ["v0"]})

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        self.assertIn("Boletus pinophilus", page)
        self.assertIn('name="view" value="v0"', page)
        self.assertIn("Aparcado para v0", page)
        self.assertIn("host_abies_alba", page)
        self.assertNotIn("host_picea_spp", page)
        self.assertNotIn('id="profile-tab-weather"', page)
        self.assertNotIn('id="profile-tab-scoring"', page)
        self.assertNotIn('id="profile-tab-json"', page)
        self.assertNotIn('name="score_habitat"', page)
        self.assertNotIn('id="profile-json"', page)

    def test_mushroom_profiles_page_renders_top_level_sections(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)

        for section, expected in (
            ("parameters", "Climate model"),
            ("calibration", "Confidence profile"),
            ("observations", "Observation records"),
        ):
            captured = {}

            def capture_response(status: int, content: bytes, content_type: str) -> None:
                captured["status"] = status
                captured["content"] = content.decode("utf-8")
                captured["content_type"] = content_type

            handler.send_bytes = capture_response
            handler.render_mushroom_profiles({"id": ["boletus_pinophilus"], "section": [section]})

            self.assertEqual(200, captured["status"])
            page = captured["content"]
            self.assertIn(expected, page)
            self.assertIn(f'section={section}', page)
            self.assertIn("Boletus pinophilus", page)
            if section == "species":
                self.assertIn('name="profile_return_tab" value="profile-tab-general"', page)

    def test_mushroom_profile_save_return_preserves_internal_tab(self) -> None:
        ok_redirect = self.web_server.profile_save_return_url(
            "boletus_pinophilus",
            {"profile_return_tab": ["profile-tab-phenology"]},
        )
        error_redirect = self.web_server.profile_save_return_url(
            "boletus_pinophilus",
            {"profile_return_tab": ["profile-tab-phenology"]},
            message=True,
        )

        self.assertEqual("?id=boletus_pinophilus&section=species#profile-tab-phenology", ok_redirect)
        self.assertEqual(
            "?id=boletus_pinophilus&section=species&profile_tab=profile-tab-phenology#mushroom-profile-message",
            error_redirect,
        )

    def test_mushroom_observations_create_persists_valid_record(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_pinophilus"],
                "observed_at": ["2026-06-29"],
                "location_input": ["https://www.google.com/maps/@41.3874,2.1686,15z"],
                "flush_abundance": ["abundant"],
                "source_quality": ["0.85"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "observer_name": ["Unit observer"],
                "observer_expertise": ["experienced"],
                "source_type": ["personal_observation"],
                "source_label": ["field report"],
                "altitude_m": ["120"],
                "altitude_source": ["manual"],
                "habitat_notes": ["oak woodland"],
            }
        )

        self.assertEqual("?section=observations&id=boletus_pinophilus&obs_id=obs_20260629_0001#observations-workspace", redirect)
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        payload = json.loads(observations_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload["observations"]))
        observation = payload["observations"][0]
        self.assertEqual("boletus_pinophilus", observation["species_id"])
        self.assertEqual("abundant", observation["flush_abundance"])
        self.assertEqual("google_maps_url", observation["location"]["source"])
        self.assertAlmostEqual(41.3874, observation["location"]["lat"])
        self.assertAlmostEqual(2.1686, observation["location"]["lon"])
        self.assertEqual(120, observation["altitude"]["meters"])
        self.assertNotIn("evidence", observation)

    def test_mushroom_observations_update_replaces_existing_record(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_pinophilus"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.3874"],
                "location_lon": ["2.1686"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["draft"],
                "calibration_use": ["review"],
            }
        )
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        observation_id = json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0]["observation_id"]

        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["update_observation"],
                "observation_id": [observation_id],
                "observation_species_id": ["boletus_pinophilus"],
                "observed_at": ["2026-06-30"],
                "location_lat": ["41.4000"],
                "location_lon": ["2.1700"],
                "flush_abundance": ["abundant"],
                "source_quality": ["0.9"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "observer_name": ["Updated observer"],
                "observer_expertise": ["expert"],
                "source_type": ["trusted_observer"],
                "habitat_notes": ["updated habitat"],
            }
        )

        self.assertEqual("?section=observations&id=boletus_pinophilus&obs_id=obs_20260629_0001#observations-workspace", redirect)
        payload = json.loads(observations_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload["observations"]))
        observation = payload["observations"][0]
        self.assertEqual(observation_id, observation["observation_id"])
        self.assertEqual("2026-06-30", observation["observed_at"])
        self.assertEqual("abundant", observation["flush_abundance"])
        self.assertEqual("Updated observer", observation["observer"]["name"])
        self.assertEqual("updated habitat", observation["site_context"]["habitat_notes"])

    def test_mushroom_observations_create_accepts_lat_lon_without_main_coordinates(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_pinophilus"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.3874"],
                "location_lon": ["2.1686"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["draft"],
                "calibration_use": ["review"],
                "observer_expertise": ["unknown"],
                "source_type": ["personal_observation"],
            }
        )

        self.assertEqual("?section=observations&id=boletus_pinophilus&obs_id=obs_20260629_0001#observations-workspace", redirect)
        payload = json.loads((data_dir / "mushroom-data" / "mushroom_observations.json").read_text(encoding="utf-8"))
        observation = payload["observations"][0]
        self.assertEqual("41.3874, 2.1686", observation["location"]["input"])
        self.assertEqual("manual_decimal", observation["location"]["source"])

    def test_mushroom_observations_duplicate_opens_unsaved_template(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_pinophilus"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.3874"],
                "location_lon": ["2.1686"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["draft"],
                "calibration_use": ["review"],
            }
        )
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        source = json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0]

        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["duplicate_observation"],
                "species_id": ["boletus_pinophilus"],
                "observation_id": [source["observation_id"]],
            }
        )

        payload = json.loads(observations_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload["observations"]))
        self.assertEqual(
            f"?section=observations&id=boletus_pinophilus&duplicate_from={source['observation_id']}#duplicate-observation",
            redirect,
        )

    def test_mushroom_observations_import_exif_images_uses_common_template(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")
        original_extractor = self.web_server.extract_photo_exif_observation_fields

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data
            self.web_server.extract_photo_exif_observation_fields = original_extractor

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        def fake_extractor(filename: str, content: bytes) -> dict[str, object]:
            return {
                "filename": filename,
                "observed_at": "2025-08-06",
                "lat": 42.0123638888889,
                "lon": 1.97034722222222,
                "altitude_m": 619.9,
            }

        self.web_server.extract_photo_exif_observation_fields = fake_extractor
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["import_observation_exif_images"],
                "observation_species_id": ["boletus_aereus"],
                "flush_abundance": ["abundant"],
                "source_quality": ["0.8"],
                "validation_status": ["draft"],
                "calibration_use": ["review"],
                "observer_name": ["Carlos"],
                "observer_expertise": ["experienced"],
            },
            files={"exif_images": [{"filename": "IMG_4144.jpeg", "content": b"fake-jpeg"}]},
        )

        self.assertEqual("?section=observations&id=boletus_aereus&obs_id=obs_20250806_0001#observations-workspace", redirect)
        payload = json.loads((data_dir / "mushroom-data" / "mushroom_observations.json").read_text(encoding="utf-8"))
        observation = payload["observations"][0]
        self.assertEqual("boletus_aereus", observation["species_id"])
        self.assertEqual("2025-08-06", observation["observed_at"])
        self.assertEqual("photo_exif", observation["location"]["source"])
        self.assertEqual(42.0123638888889, observation["location"]["lat"])
        self.assertEqual(1.97034722222222, observation["location"]["lon"])
        self.assertEqual(619.9, observation["altitude"]["meters"])
        self.assertEqual("photo_exif", observation["source"]["type"])
        self.assertEqual("IMG_4144.jpeg", observation["source"]["label"])
        self.assertEqual("Carlos", observation["observer"]["name"])
        self.assertEqual("experienced", observation["observer"]["expertise"])

    def test_mushroom_observations_update_from_exif_images_updates_and_creates_extra_rows(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")
        original_extractor = self.web_server.extract_photo_exif_observation_fields

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data
            self.web_server.extract_photo_exif_observation_fields = original_extractor

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_aereus"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.0"],
                "location_lon": ["2.0"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["draft"],
                "calibration_use": ["review"],
                "observer_name": ["Carlos"],
                "observer_expertise": ["experienced"],
            }
        )
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        observation_id = json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0]["observation_id"]

        def fake_extractor(filename: str, content: bytes) -> dict[str, object]:
            if filename == "IMG_4144.jpeg":
                return {
                    "filename": filename,
                    "observed_at": "2025-08-06",
                    "lat": 42.0123638888889,
                    "lon": 1.97034722222222,
                    "altitude_m": 619.9,
                }
            return {
                "filename": filename,
                "observed_at": "2025-08-07",
                "lat": 42.06723,
                "lon": 1.94652,
                "altitude_m": 761.9,
            }

        self.web_server.extract_photo_exif_observation_fields = fake_extractor
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["update_observation"],
                "observation_id": [observation_id],
                "observation_species_id": ["amanita_caesarea"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.0"],
                "location_lon": ["2.0"],
                "flush_abundance": ["scarce"],
                "source_quality": ["1"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "observer_name": ["Carlos"],
                "observer_expertise": ["experienced"],
                "source_type": ["personal_observation"],
            },
            files={
                "observation_exif_images": [
                    {"filename": "IMG_4144.jpeg", "content": b"fake-jpeg-1"},
                    {"filename": "IMG_4083.jpeg", "content": b"fake-jpeg-2"},
                ]
            },
        )

        self.assertEqual("?section=observations&id=amanita_caesarea&obs_id=obs_20260629_0001#observations-workspace", redirect)
        payload = json.loads(observations_path.read_text(encoding="utf-8"))
        self.assertEqual(2, len(payload["observations"]))
        updated, extra = payload["observations"]
        self.assertEqual(observation_id, updated["observation_id"])
        self.assertEqual("amanita_caesarea", updated["species_id"])
        self.assertEqual("2025-08-06", updated["observed_at"])
        self.assertEqual("photo_exif", updated["location"]["source"])
        self.assertEqual(619.9, updated["altitude"]["meters"])
        self.assertEqual("IMG_4144.jpeg", updated["source"]["label"])
        self.assertNotEqual(observation_id, extra["observation_id"])
        self.assertEqual("amanita_caesarea", extra["species_id"])
        self.assertEqual("2025-08-07", extra["observed_at"])
        self.assertEqual(761.9, extra["altitude"]["meters"])
        self.assertEqual("IMG_4083.jpeg", extra["source"]["label"])

    def test_mushroom_observations_create_reports_missing_coordinates(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_pinophilus"],
                "observed_at": ["2026-06-29"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["draft"],
                "calibration_use": ["review"],
            }
        )

        self.assertEqual("?section=observations&id=boletus_pinophilus#new-observation", redirect)
        self.assertIn("Coordinates are required", self.web_server.RUN_STATE["mushroom_profiles_flash"])

    def test_mushroom_observations_archive_restore_and_delete(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_pinophilus"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.3874"],
                "location_lon": ["2.1686"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
            }
        )
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        observation_id = json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0]["observation_id"]

        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["archive_observation"],
                "species_id": ["boletus_pinophilus"],
                "observation_id": [observation_id],
            }
        )
        self.assertEqual([], json.loads(observations_path.read_text(encoding="utf-8"))["observations"])
        archived_path = data_dir / "mushroom-data" / "archived" / "mushroom_observations_archived.json"
        self.assertEqual(observation_id, json.loads(archived_path.read_text(encoding="utf-8"))["observations"][0]["observation_id"])

        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["restore_observation"],
                "species_id": ["boletus_pinophilus"],
                "observation_id": [observation_id],
            }
        )
        self.assertEqual(observation_id, json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0]["observation_id"])
        self.assertEqual([], json.loads(archived_path.read_text(encoding="utf-8"))["observations"])

        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["archive_observation"],
                "species_id": ["boletus_pinophilus"],
                "observation_id": [observation_id],
            }
        )
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["delete_archived_observation"],
                "species_id": ["boletus_pinophilus"],
                "observation_id": [observation_id],
                "delete_confirm_id": ["wrong_id"],
            }
        )
        self.assertEqual(1, len(json.loads(archived_path.read_text(encoding="utf-8"))["observations"]))
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["delete_archived_observation"],
                "species_id": ["boletus_pinophilus"],
                "observation_id": [observation_id],
                "delete_confirm_id": [observation_id],
            }
        )
        self.assertEqual([], json.loads(archived_path.read_text(encoding="utf-8"))["observations"])

    def test_mushroom_parameters_render_human_labels_and_host_groups(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        store = self.web_server.default_store()
        store.ensure_seeded()
        profiles = store.load("profiles")
        catalogs = store.load("catalogs")
        profile = next(
            item
            for item in profiles["species_profiles"]
            if item["species_id"] == "boletus_pinophilus"
        )

        html = self.web_server.mushroom_profiles_ui.render_parameters_section(profile, catalogs)

        self.assertIn("7d min rain", html)
        self.assertIn("Hosts", html)
        self.assertIn("Secondary hosts", html)
        self.assertIn("parameter-section-tabs", html)
        self.assertIn("parameter-tab-panel active", html)
        self.assertIn("parameter-tab-panel inactive", html)
        self.assertIn('name="rainfall_rain_7d_min_mm"', html)
        self.assertIn('parameter_view=climate', html)
        self.assertLess(html.index("Habitat model"), html.index("Climate model"))
        self.assertLess(html.index("Climate model"), html.index("Scoring weights"))
        self.assertNotIn(">rain_7d_min_mm<", html)

    def test_mushroom_parameters_v0_does_not_reserve_empty_left_column(self) -> None:
        profiles = json.loads((ROOT_DIR / "mushroom-data" / "mushroom_profiles.json").read_text(encoding="utf-8"))[
            "species_profiles"
        ]
        catalogs = json.loads(
            (ROOT_DIR / "mushroom-data" / "mushroom_reference_catalogs.json").read_text(encoding="utf-8")
        )["catalogs"]
        profile = next(item for item in profiles if item["species_id"] == "amanita_caesarea")

        html = self.web_server.mushroom_profiles_ui.render_parameters_section(profile, catalogs, profile_view="v0")

        self.assertIn("profile-parameters-grid parameter-tabbed-grid v0", html)
        self.assertIn("parameter-section-tabs", html)
        self.assertNotIn("parameter-left-stack", html)
        self.assertNotIn("Climate model", html)
        self.assertIn("Habitat model", html)
        self.assertIn("month-toggle-field", html)
        self.assertIn('name="main_months" value="9" checked', html)
        self.assertIn('name="secondary_months" value="6" checked', html)
        self.assertNotIn('textarea id="profile-main_months"', html)
        self.assertNotIn('textarea id="profile-secondary_months"', html)
        self.assertIn('textarea id="profile-aspect_notes" name="aspect_notes" rows="3"', html)
        self.assertIn("parameter-section-forests parameter-profile-section", html)
        self.assertIn("<h4>Forest types</h4>", html)
        self.assertIn('title="forest_cork_oak"', html)
        self.assertIn('class="parameter-affinity-label">Cork oak woodland</span>', html)
        self.assertIn('class="parameter-affinity-badge preferred">Preferente</span>', html)
        self.assertIn('class="parameter-affinity-badge source">Fuente v0</span>', html)
        self.assertIn('class="parameter-affinity-badge catalog">Catalogo</span>', html)

    def test_mushroom_observation_filters_are_editable_and_filter_rows(self) -> None:
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")

        profiles = json.loads((ROOT_DIR / "mushroom-data" / "mushroom_profiles.json").read_text(encoding="utf-8"))[
            "species_profiles"
        ]
        catalogs = json.loads(
            (ROOT_DIR / "mushroom-data" / "mushroom_reference_catalogs.json").read_text(encoding="utf-8")
        )["catalogs"]
        profile = next(item for item in profiles if item["species_id"] == "boletus_pinophilus")
        observations = {
            "observations": [
                {
                    "observation_id": "obs_20260620_0001",
                    "species_id": "boletus_pinophilus",
                    "observed_at": "2026-06-20",
                    "flush_abundance": "scarce",
                    "validation_status": "draft",
                    "calibration_use": "review",
                    "source_quality": 0.5,
                    "location": {"lat": 41.1, "lon": 2.1, "source": "manual_decimal"},
                },
                {
                    "observation_id": "obs_20260629_0001",
                    "species_id": "boletus_pinophilus",
                    "observed_at": "2026-06-29",
                    "flush_abundance": "abundant",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "source_quality": 0.9,
                    "location": {"lat": 41.2, "lon": 2.2, "source": "manual_decimal"},
                    "site_context": {
                        "observed_host_ids": ["host_pinus_sylvestris"],
                        "habitat_notes": "",
                        "host_notes": "",
                    },
                },
                {
                    "observation_id": "obs_20260628_0001",
                    "species_id": "boletus_aereus",
                    "observed_at": "2026-06-28",
                    "flush_abundance": "normal",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "source_quality": 0.9,
                    "location": {"lat": 41.3, "lon": 2.3, "source": "manual_decimal"},
                },
            ]
        }
        archived_observations = {
            "observations": [
                {
                    "observation_id": "obs_20260627_0001",
                    "species_id": "boletus_aereus",
                    "observed_at": "2026-06-27",
                    "flush_abundance": "normal",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "source_quality": 0.8,
                    "location": {"lat": 41.4, "lon": 2.4, "source": "manual_decimal"},
                }
            ]
        }

        html = self.web_server.mushroom_profiles_ui.render_observations_section(
            profile,
            profiles,
            catalogs,
            observations,
            archived_observations,
            filters={"date_from": "2026-06-29", "result": "abundant"},
        )

        filters_html = html[html.index('<form class="observations-filters"') : html.index('<div class="observations-layout">')]
        self.assertIn('name="date_from" type="date" value="2026-06-29"', filters_html)
        self.assertIn('name="date_to" type="date"', filters_html)
        self.assertNotIn("readonly", filters_html)
        self.assertNotIn("disabled", filters_html)
        self.assertIn("sort=observed_at", html)
        self.assertIn("sort=abundance", html)
        self.assertIn("import-observation-exif", html)
        self.assertIn('name="exif_images"', html)
        self.assertIn('name="observed_host_ids"', html)
        self.assertIn('class="profile-action-bar observations-main-actions"', html)
        self.assertIn('<details id="gis-reconstruction-lab"', html)
        self.assertLess(html.index('href="#new-observation"'), html.index('id="archived-observations"'))
        self.assertLess(html.index('href="#new-observation"'), html.index('id="gis-reconstruction-lab"'))
        self.assertIn('data-observation-select data-observation-href=', html)
        self.assertIn('onclick="selectObservationRow(this)"', html)
        self.assertIn('class="observation-map-link" href="#observation-map-obs-20260629-0001"', html)
        self.assertIn('id="observation-map-obs-20260629-0001"', html)
        self.assertIn("maps.google.com/maps?", html)
        self.assertIn('href="#observation-map-obs-20260629-0001">Map</a>', html)
        self.assertIn("Scots pine", html)
        self.assertNotIn("missing label:", html)
        self.assertIn("obs_20260629_0001", html)
        self.assertNotIn("obs_20260620_0001", html)
        self.assertNotIn("obs_20260628_0001", html)

        sorted_html = self.web_server.mushroom_profiles_ui.render_observations_section(
            profile,
            profiles,
            catalogs,
            observations,
            archived_observations,
            filters={"sort": "abundance", "dir": "asc"},
        )
        self.assertLess(sorted_html.index("obs_20260629_0001"), sorted_html.index("obs_20260620_0001"))

        all_species_html = self.web_server.mushroom_profiles_ui.render_observations_section(
            profile,
            profiles,
            catalogs,
            observations,
            archived_observations,
            filters={"obs_species": "__all__", "sort": "observed_at", "dir": "desc", "obs_id": "obs_20260628_0001"},
        )
        self.assertIn("obs_20260629_0001", all_species_html)
        self.assertIn("obs_20260628_0001", all_species_html)
        self.assertIn("obs_20260627_0001", all_species_html)
        self.assertIn("obs_species=__all__", all_species_html)
        self.assertIn("obs_id=obs_20260628_0001", all_species_html)
        self.assertIn('class="observation-row selected"', all_species_html)
        self.assertIn("<h2>All species</h2>", all_species_html)
        self.assertIn("duplicate_from=obs_20260628_0001", all_species_html)

    def test_mushroom_observation_gis_summary_renders_v0_context(self) -> None:
        result = {
            "generated_at": "2026-07-02T12:00:00",
            "results": [
                {
                    "observation_id": "obs_20260702_0001",
                    "species_id": "boletus_edulis",
                    "status": "complete",
                    "layers": {
                        "mvc50": {
                            "status": "ok",
                            "properties": {"LLVA_niv2t": "pinedes", "LLVA_Subst": "silici"},
                            "mapped": {
                                "unmapped_values": [
                                    {"source_id": "mvc50", "field": "LLVA_niv2t", "raw_value": "pinedes"}
                                ]
                            },
                        },
                        "geology_50000": {
                            "status": "ok",
                            "properties": {"Codi": "Q", "Descripcio": "quaternari"},
                        },
                        "dem_5m": {
                            "status": "ok",
                            "elevation_m": 1200.0,
                            "delta_observed_vs_dem_m": 3.5,
                        },
                    },
                    "gis_context_v0": {
                        "schema_version": "0.1",
                        "kind": "mushroom_gis_context_v0",
                        "host_ids": ["host_pinus_sylvestris"],
                        "forest_type_ids": ["forest_pine"],
                        "soil_tendency_ids": ["soil_siliceous"],
                        "habitat_feature_ids": ["feature_montane_forest"],
                        "altitude_m": 1200.0,
                        "altitude_source": "dem_5m",
                    },
                    "gaps": [],
                },
                {
                    "observation_id": "obs_20260702_0002",
                    "species_id": "amanita_caesarea",
                    "status": "complete",
                    "layers": {
                        "mvc50": {
                            "status": "ok",
                            "properties": {"LLVA_niv2t": "alzinar"},
                            "mapped": {
                                "unmapped_values": [
                                    {"source_id": "mvc50", "field": "LLVA_niv2t", "raw_value": "alzinar"}
                                ]
                            },
                        },
                    },
                    "gis_context_v0": {},
                    "gaps": [],
                }
            ],
        }

        html = self.web_server.mushroom_profiles_ui.render_gis_result_summary(
            result,
            {"boletus_edulis": "Boletus edulis"},
            "boletus_edulis",
        )

        self.assertIn("Contexto v0", html)
        self.assertIn("host_pinus_sylvestris", html)
        self.assertIn("forest_pine", html)
        self.assertIn("soil_siliceous", html)
        self.assertIn("feature_montane_forest", html)
        self.assertIn("1200.0 m", html)
        self.assertIn("Observations used for the latest reconstruction", html)
        self.assertIn("pinedes", html)
        self.assertNotIn("obs_20260702_0002", html)
        self.assertNotIn("alzinar", html)

    def test_mushroom_local_evidence_section_renders_review_actions(self) -> None:
        profile = {
            "species_id": "boletus_aereus",
            "scientific_name": "Boletus aereus",
            "common_names": ["hongo negro"],
            "ecology": {
                "host_affinities": [{"id": "host_quercus_suber", "v0_active": True}],
                "forest_type_affinities": [{"id": "forest_cork_oak", "v0_active": True}],
                "soil_affinities": [{"id": "soil_calcareous", "v0_active": True}],
                "habitat_feature_affinities": [],
            },
            "prediction_confidence": {},
            "metadata": {},
        }
        catalogs = {
            "host_taxa": [
                {
                    "id": "host_quercus_ilex",
                    "scientific_name": "Quercus ilex",
                    "common_names": {"en": ["Holm oak"]},
                },
                {
                    "id": "host_quercus_suber",
                    "scientific_name": "Quercus suber",
                    "common_names": {"en": ["Cork oak"]},
                },
            ],
            "forest_types": [
                {"id": "forest_holm_oak", "label": {"en": "Holm oak forest"}},
                {"id": "forest_cork_oak", "label": {"en": "Cork oak forest"}},
            ],
            "soil_types": [{"id": "soil_calcareous", "label": {"en": "Calcareous"}}],
            "habitat_features": [{"id": "feature_open_warm_woodland", "label": {"en": "Open warm woodland"}}],
        }
        reconstruction = {
            "generated_at": "2026-07-02T12:00:00",
            "results": [
                {
                    "observation_id": "obs_1",
                    "species_id": "boletus_aereus",
                    "location": {"lat": 41.75, "lon": 2.15, "source": "mushroom_observations"},
                    "gis_context_v0": {
                        "host_ids": ["host_quercus_ilex"],
                        "forest_type_ids": ["forest_holm_oak"],
                        "soil_tendency_ids": ["soil_calcareous"],
                        "habitat_feature_ids": ["feature_open_warm_woodland"],
                    },
                }
            ],
        }
        decisions = {
            "decisions": [
                {
                    "species_id": "boletus_aereus",
                    "group": "host_affinities",
                    "item_id": "host_quercus_ilex",
                    "decision": "promote",
                }
            ]
        }

        html = self.web_server.mushroom_profiles_ui.render_local_evidence_section(
            profile,
            catalogs,
            reconstruction,
            None,
            decisions,
            profile_view="v0",
        )

        self.assertIn("Evidencia local v0", html)
        self.assertIn("Observed, not declared", html)
        self.assertIn("Declared, not observed", html)
        self.assertIn("Promote", html)
        self.assertIn("Doubtful", html)
        self.assertIn("GIS (hosts + forests)", html)
        self.assertIn("GIS (soils + habitat)", html)
        self.assertIn('name="profile_action" value="update_evidence_decision"', html)
        self.assertIn('name="view" value="v0"', html)
        self.assertIn('name="evidence_view" value="gis_hosts_forests"', html)
        self.assertIn("host_quercus_ilex", html)
        self.assertIn("host_quercus_suber", html)
        self.assertIn("Quercus ilex - Holm oak", html)
        self.assertIn("Quercus suber - Cork oak", html)
        self.assertIn("Whether this ID is already declared", html)
        self.assertIn("Evidence observations", html)
        self.assertIn("maps.google.com/maps?", html)
        self.assertIn("Open Google Maps", html)
        self.assertIn(">Open</a>", html)
        self.assertIn("?section=observations&amp;obs_id=obs_1&amp;id=boletus_aereus#observation-detail", html)
        self.assertNotIn("Ejemplos", html)

        soils_html = self.web_server.mushroom_profiles_ui.render_local_evidence_section(
            profile,
            catalogs,
            reconstruction,
            None,
            decisions,
            profile_view="v0",
            evidence_view="gis_soils_habitat",
        )
        self.assertIn("Soils", soils_html)
        self.assertIn("Habitat", soils_html)
        self.assertIn('name="view" value="v0"', soils_html)
        self.assertIn('name="evidence_view" value="gis_soils_habitat"', soils_html)
        self.assertNotIn("Quercus ilex - Holm oak", soils_html)

        self.assertEqual(
            "?id=boletus_aereus&section=evidence&view=v0&evidence_view=gis_soils_habitat#mushroom-profile-message",
            self.web_server.evidence_return_url(
                "boletus_aereus",
                profile_view="v0",
                evidence_view="gis_soils_habitat",
            ),
        )

    def test_mushroom_local_evidence_section_renders_weather_features(self) -> None:
        profile = {
            "species_id": "boletus_aereus",
            "scientific_name": "Boletus aereus",
            "common_names": {"en": ["Black bolete"]},
            "ecology": {},
            "prediction_confidence": {},
            "metadata": {},
        }
        features_payload = {
            "generated_at": "2026-07-02T14:00:00",
            "rows": [
                {
                    "observation_id": "obs_1",
                    "species_id": "boletus_aereus",
                    "observed_at": "2025-09-30",
                    "analysis_result": "present",
                    "flush_abundance": "abundant",
                    "rain_7d_mm": 11.0,
                    "rain_14d_mm": 22.0,
                    "rain_21d_mm": 27.0,
                    "rain_30d_mm": 33.0,
                    "rain_60d_mm": 60.0,
                    "rain_90d_mm": 90.0,
                    "gis_altitude_m": 705.0,
                    "temp_min_7d_c": 7.0,
                    "temp_max_7d_c": 21.0,
                    "temp_min_14d_c": 6.0,
                    "temp_max_14d_c": 22.0,
                    "temp_min_21d_c": 5.0,
                    "temp_max_21d_c": 23.0,
                    "temp_min_30d_c": 4.0,
                    "temp_max_30d_c": 24.0,
                    "temp_min_c": 7.0,
                    "temp_max_c": 21.0,
                    "humidity_min_7d_pct": 50.0,
                    "humidity_max_7d_pct": 88.0,
                    "humidity_min_14d_pct": 48.0,
                    "humidity_max_14d_pct": 89.0,
                    "humidity_min_21d_pct": 46.0,
                    "humidity_max_21d_pct": 90.0,
                    "humidity_min_30d_pct": 44.0,
                    "humidity_max_30d_pct": 91.0,
                    "humidity_min_pct": 50.0,
                    "humidity_max_pct": 88.0,
                    "weather_source": "meteocat",
                    "weather_station_code": "X1",
                    "weather_station_distance_km": 4.2,
                    "weather_gaps": ["wind_no_data_7d"],
                },
                {
                    "observation_id": "obs_2",
                    "species_id": "boletus_aereus",
                    "observed_at": "2025-10-01",
                    "analysis_result": "absent",
                    "flush_abundance": "absent",
                    "rain_7d_mm": 4.0,
                    "weather_source": "meteocat",
                    "weather_station_code": "X1",
                },
            ],
        }

        html = self.web_server.mushroom_profiles_ui.render_local_evidence_section(
            profile,
            {},
            {"generated_at": "2026-07-02T12:00:00", "results": []},
            features_payload,
            None,
            evidence_view="weather",
        )

        self.assertIn("Weather evidence", html)
        self.assertIn("Latest v0 features join: 2026-07-02T14:00:00", html)
        self.assertIn("Present", html)
        self.assertIn("Absent", html)
        self.assertIn("Rainfall 21d", html)
        self.assertIn("Rainfall 60d", html)
        self.assertIn("Temp 30d", html)
        self.assertIn("Hum 30d", html)
        self.assertIn("705 m", html)
        self.assertIn("11 mm", html)
        self.assertIn("meteocat", html)
        self.assertIn("wind_no_data_7d", html)

    def test_mushroom_local_evidence_section_renders_learned_model(self) -> None:
        profile = {
            "species_id": "boletus_aereus",
            "scientific_name": "Boletus aereus",
            "common_names": {"en": ["Black bolete"]},
            "ecology": {},
            "prediction_confidence": {},
            "metadata": {},
        }
        catalogs = {
            "host_taxa": [
                {
                    "id": "host_quercus_ilex",
                    "scientific_name": "Quercus ilex",
                    "common_names": {"en": ["Holm oak"]},
                }
            ],
            "forest_types": [],
            "soil_types": [],
            "habitat_features": [],
        }
        learned_model = {
            "generated_at": "2026-07-02T15:00:00",
            "species_models": [
                {
                    "species_id": "boletus_aereus",
                    "observation_count": 3,
                    "positive_count": 2,
                    "negative_count": 1,
                    "weather_gap_count": 1,
                    "gis_gap_count": 0,
                    "categorical_features": {
                        "hosts": [
                            {
                                "id": "host_quercus_ilex",
                                "positive_support": 2,
                                "positive_ratio": 1.0,
                                "negative_support": 1,
                                "negative_ratio": 1.0,
                                "ratio_delta": 0.0,
                            }
                        ]
                    },
                    "numeric_features": {
                        "rain_14d_mm": {
                            "positive": {"count": 2, "min": 20.0, "max": 30.0, "mean": 25.0},
                            "negative": {"count": 1, "min": 2.0, "max": 2.0, "mean": 2.0},
                        },
                        "altitude_m": {
                            "positive": {"count": 2, "min": 650.0, "max": 700.0, "mean": 675.0},
                            "negative": {"count": 1, "min": 680.0, "max": 680.0, "mean": 680.0},
                        },
                    },
                }
            ],
        }

        html = self.web_server.mushroom_profiles_ui.render_local_evidence_section(
            profile,
            catalogs,
            {"generated_at": "2026-07-02T12:00:00", "results": []},
            None,
            None,
            learned_model_payload=learned_model,
            evidence_view="learned_model",
        )

        self.assertIn("Learned model", html)
        self.assertIn("Learned v0 model", html)
        self.assertIn("Quercus ilex - Holm oak", html)
        self.assertIn("Rainfall 14d", html)
        self.assertIn("rain_14d_mm", html)
        self.assertIn("25 mm", html)
        self.assertIn("2026-07-02T15:00:00", html)
        self.assertIn('name="profile_action" value="rebuild_learned_model_v0_species"', html)
        self.assertIn('name="profile_action" value="rebuild_learned_model_v0_all"', html)
        self.assertIn("Rebuild this species", html)
        self.assertIn("Rebuild all species", html)

    def test_mushroom_learned_model_rebuild_post_runs_builders(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        with mock.patch.object(self.web_server.mushroom_observation_context, "build_and_write_observation_weather_features") as weather_builder, \
            mock.patch.object(self.web_server.mushroom_observation_features, "build_and_write_observation_features_v0") as features_builder, \
            mock.patch.object(self.web_server.mushroom_learned_model, "build_and_write_learned_model_v0") as model_builder:
            weather_builder.return_value = {"summary": {"observations": 3}}
            features_builder.return_value = {"summary": {"observations": 3}}
            model_builder.return_value = {
                "summary": {
                    "observations": 2,
                    "excluded_observations": 1,
                    "species": 1,
                }
            }

            redirect = handler.handle_mushroom_profiles_post(
                {
                    "profile_action": ["rebuild_learned_model_v0_all"],
                    "species_id": ["amanita_caesarea"],
                    "view": ["v0"],
                    "evidence_view": ["learned_model"],
                }
            )

        weather_builder.assert_called_once_with()
        features_builder.assert_called_once_with()
        model_builder.assert_called_once_with()
        self.assertEqual(
            "?id=amanita_caesarea&section=evidence&view=v0&evidence_view=learned_model#mushroom-profile-message",
            redirect,
        )
        self.assertIn("Learned v0 model rebuilt", self.web_server.RUN_STATE["mushroom_profiles_flash"])

    def test_mushroom_learned_model_rebuild_selected_species_does_not_rebuild_caches(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        with mock.patch.object(self.web_server.mushroom_observation_context, "build_and_write_observation_weather_features") as weather_builder, \
            mock.patch.object(self.web_server.mushroom_observation_features, "build_and_write_observation_features_v0") as features_builder, \
            mock.patch.object(self.web_server.mushroom_learned_model, "build_and_write_species_learned_model_v0") as species_builder:
            species_builder.return_value = {
                "species_models": [
                    {
                        "species_id": "amanita_caesarea",
                        "observation_count": 2,
                    }
                ]
            }

            redirect = handler.handle_mushroom_profiles_post(
                {
                    "profile_action": ["rebuild_learned_model_v0_species"],
                    "species_id": ["amanita_caesarea"],
                    "view": ["v0"],
                    "evidence_view": ["learned_model"],
                }
            )

        weather_builder.assert_not_called()
        features_builder.assert_not_called()
        species_builder.assert_called_once_with("amanita_caesarea")
        self.assertEqual(
            "?id=amanita_caesarea&section=evidence&view=v0&evidence_view=learned_model#mushroom-profile-message",
            redirect,
        )
        self.assertIn("selected species", self.web_server.RUN_STATE["mushroom_profiles_flash"])

    def test_mushroom_evidence_decisions_are_reversible(self) -> None:
        data_dir = Path(self.temp_dir.name)

        class EvidenceStore:
            pass

        store = EvidenceStore()
        store.data_dir = data_dir

        ok, message = self.web_server.save_evidence_decision(
            store,
            "boletus_aereus",
            "host_affinities",
            "host_quercus_ilex",
            "promote",
        )
        self.assertTrue(ok, message)
        payload = self.web_server.load_evidence_decisions(store)
        self.assertEqual(payload["decisions"][0]["decision"], "promote")

        ok, message = self.web_server.save_evidence_decision(
            store,
            "boletus_aereus",
            "host_affinities",
            "host_quercus_ilex",
            "unreviewed",
        )
        self.assertTrue(ok, message)
        payload = self.web_server.load_evidence_decisions(store)
        self.assertEqual(payload["decisions"], [])

    def test_mushroom_profiles_create_species_uses_validated_template(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_profile"],
                "new_species_id": ["boletus_test_new"],
                "new_scientific_name": ["Boletus test new"],
                "new_common_name": ["test cep"],
            }
        )

        self.assertEqual("?id=boletus_test_new", redirect)
        profiles_path = data_dir / "mushroom-data" / "mushroom_profiles.json"
        payload = json.loads(profiles_path.read_text(encoding="utf-8"))
        created = next(
            profile
            for profile in payload["species_profiles"]
            if profile["species_id"] == "boletus_test_new"
        )
        self.assertEqual("Boletus test new", created["scientific_name"])
        self.assertEqual(["test cep"], created["common_names"])
        self.assertEqual("draft", created["metadata"]["review_status"])
        self.assertEqual("not_calibrated", created["prediction_confidence"]["local_calibration_status"])

    def test_mushroom_profiles_create_species_blocks_duplicate_id(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_profile"],
                "new_species_id": ["boletus_edulis"],
                "new_scientific_name": ["Boletus duplicate"],
            }
        )

        self.assertEqual("?#mushroom-profile-message", redirect)
        self.assertIn(
            "already exists",
            self.web_server.RUN_STATE["mushroom_profiles_flash"],
        )

    def test_mushroom_profiles_duplicate_species_creates_editable_draft(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["duplicate_profile"],
                "species_id": ["boletus_edulis"],
                "duplicate_species_id": ["boletus_edulis_copy"],
                "duplicate_scientific_name": ["Boletus edulis copy"],
                "duplicate_common_name": ["copy cep"],
            }
        )

        self.assertEqual("?id=boletus_edulis_copy", redirect)
        payload = json.loads((data_dir / "mushroom-data" / "mushroom_profiles.json").read_text(encoding="utf-8"))
        duplicated = next(profile for profile in payload["species_profiles"] if profile["species_id"] == "boletus_edulis_copy")
        self.assertEqual("Boletus edulis copy", duplicated["scientific_name"])
        self.assertEqual(["copy cep"], duplicated["common_names"])
        self.assertEqual("draft", duplicated["metadata"]["review_status"])
        self.assertEqual("not_calibrated", duplicated["prediction_confidence"]["local_calibration_status"])

    def test_mushroom_profiles_archive_restore_and_delete_archived_species(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        archive_redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["archive_profile"],
                "species_id": ["boletus_edulis"],
            }
        )

        self.assertEqual("?", archive_redirect)
        profiles_path = data_dir / "mushroom-data" / "mushroom_profiles.json"
        archive_path = data_dir / "mushroom-data" / "archived" / "mushroom_profiles_archived.json"
        active_payload = json.loads(profiles_path.read_text(encoding="utf-8"))
        self.assertNotIn("boletus_edulis", [profile["species_id"] for profile in active_payload["species_profiles"]])
        archived_payload = json.loads(archive_path.read_text(encoding="utf-8"))
        self.assertIn("boletus_edulis", [profile["species_id"] for profile in archived_payload["archived_species_profiles"]])

        restore_redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["restore_profile"],
                "species_id": ["boletus_edulis"],
            }
        )

        self.assertEqual("?id=boletus_edulis", restore_redirect)
        active_payload = json.loads(profiles_path.read_text(encoding="utf-8"))
        self.assertIn("boletus_edulis", [profile["species_id"] for profile in active_payload["species_profiles"]])
        archived_payload = json.loads(archive_path.read_text(encoding="utf-8"))
        self.assertNotIn("boletus_edulis", [profile["species_id"] for profile in archived_payload["archived_species_profiles"]])

        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["archive_profile"],
                "species_id": ["boletus_edulis"],
            }
        )
        delete_redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["delete_archived_profile"],
                "species_id": ["boletus_edulis"],
                "delete_confirm_id": ["boletus_edulis"],
            }
        )

        self.assertEqual("?#mushroom-profile-message", delete_redirect)
        archived_payload = json.loads(archive_path.read_text(encoding="utf-8"))
        self.assertNotIn("boletus_edulis", [profile["species_id"] for profile in archived_payload["archived_species_profiles"]])

    def test_mushroom_catalogs_create_entry_uses_validated_template(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_catalogs_post(
            {
                "catalog_action": ["create_entry"],
                "group": ["host_taxa"],
                "id": ["host_test_new"],
            }
        )

        self.assertEqual("?group=host_taxa&id=host_test_new", redirect)
        catalog_path = data_dir / "mushroom-data" / "mushroom_reference_catalogs.json"
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertTrue(
            any(item.get("id") == "host_test_new" for item in payload["catalogs"]["host_taxa"])
        )

    def test_mushroom_catalog_links_are_ingress_relative(self) -> None:
        source = Path(WEB_SERVER_PATH).read_text(encoding="utf-8")

        self.assertIn('href="./mushrooms/catalogs"', source)
        self.assertIn('href="./mushrooms/profiles"', source)
        self.assertNotIn('href="/mushrooms/catalogs"', source)
        self.assertNotIn('href="/mushrooms/profiles"', source)
        self.assertNotIn('action="/mushrooms/catalogs"', source)
        self.assertNotIn('action="/mushrooms/profiles"', source)
        self.assertEqual("?group=host_taxa&id=host_foo", self.web_server.catalog_query_url("host_taxa", "host_foo"))

    def test_profile_form_preserves_species_id_and_updates_general_fields(self) -> None:
        profile = {
            "species_id": "boletus_test",
            "scientific_name": "Boletus test",
            "common_names": ["old"],
            "taxonomy_status": "accepted",
            "edibility": "good",
            "ecology": {
                "trophic_mode_id": "trophic_ectomycorrhizal",
                "host_affinities": [],
                "forest_type_affinities": [],
                "soil_affinities": [],
                "lithology_affinities": [],
                "habitat_feature_affinities": [],
            },
            "phenology": {
                "main_months": [9],
                "secondary_months": [],
                "season_pattern_ids": [],
                "fruiting_delay_after_rain_days": {"min": 1, "optimal_min": 2, "optimal_max": 3, "max": 4},
            },
            "topography": {
                "altitude_min_m": 0,
                "altitude_optimal_min_m": 100,
                "altitude_optimal_max_m": 500,
                "altitude_max_m": 1000,
                "preferred_aspect_ids": [],
                "aspect_notes": "",
            },
            "weather_model": {
                "rainfall": {"rain_7d_min_mm": 5},
                "temperature": {"temp_min_7d_optimal_min_c": 3},
                "humidity": {"humidity_min_7d_preferred_min_pct": 50},
                "wind": {"dry_wind_sensitive": True},
            },
            "scoring_weights": {"habitat": 0.2, "season": 0.2, "altitude": 0.1, "rainfall": 0.2, "temperature": 0.1, "humidity": 0.1, "wind_penalty": 0.1},
            "prediction_confidence": {
                "overall_confidence": "medium",
                "habitat_confidence": "medium",
                "topography_confidence": "medium",
                "phenology_confidence": "medium",
                "weather_threshold_confidence": "low",
                "taxonomy_confidence": "high",
                "local_calibration_status": "not_calibrated",
                "calibration_priority": "high",
                "minimum_observations_for_calibration": 30,
                "minimum_positive_observations": 10,
                "minimum_negative_observations": 10,
                "notes": "",
            },
            "metadata": {
                "profile_version": "0.1",
                "created_at": "2026-01-01",
                "updated_at": "2026-01-01",
                "created_by": "test",
                "review_status": "draft",
                "reviewed_by": "",
                "source_quality": "inferred_from_literature",
                "requires_human_validation": True,
            },
        }
        form = {
            "scientific_name": ["Boletus updated"],
            "common_names": ["updated\nsecond"],
            "taxonomy_status": ["accepted"],
            "edibility": ["excellent"],
            "trophic_mode_id": ["trophic_ectomycorrhizal"],
            "host_affinities_0_id": ["host_pinus_spp"],
            "host_affinities_0_relationship": ["primary"],
            "host_affinities_0_affinity": ["0,9"],
            "forest_type_affinities_0_id": [""],
            "soil_affinities_0_id": [""],
            "lithology_affinities_0_id": [""],
            "habitat_feature_affinities_0_id": [""],
            "main_months": ["8\n9"],
            "secondary_months": ["10"],
            "season_pattern_ids": ["season_autumn"],
            "preferred_aspect_ids": ["aspect_N"],
            "delay_min": ["5"],
            "delay_optimal_min": ["7"],
            "delay_optimal_max": ["12"],
            "delay_max": ["20"],
            "altitude_min_m": ["400"],
            "altitude_optimal_min_m": ["800"],
            "altitude_optimal_max_m": ["1600"],
            "altitude_max_m": ["2200"],
            "aspect_notes": ["fresh slopes"],
            "rainfall_rain_7d_min_mm": ["12"],
            "temperature_temp_min_7d_optimal_min_c": ["4"],
            "humidity_humidity_min_7d_preferred_min_pct": ["60"],
            "wind_dry_wind_sensitive": ["true"],
            "score_habitat": ["0,2"],
            "score_season": ["0,2"],
            "score_altitude": ["0,1"],
            "score_rainfall": ["0,2"],
            "score_temperature": ["0,1"],
            "score_humidity": ["0,1"],
            "score_wind_penalty": ["0,1"],
            "overall_confidence": ["high"],
            "habitat_confidence": ["medium"],
            "topography_confidence": ["medium"],
            "phenology_confidence": ["medium"],
            "weather_threshold_confidence": ["low"],
            "taxonomy_confidence": ["high"],
            "local_calibration_status": ["not_calibrated"],
            "calibration_priority": ["high"],
            "minimum_observations_for_calibration": ["40"],
            "minimum_positive_observations": ["12"],
            "minimum_negative_observations": ["11"],
            "confidence_notes": ["needs local data"],
            "profile_version": ["0.2"],
            "created_at": ["2026-01-01"],
            "updated_at": ["2026-06-27"],
            "created_by": ["test"],
            "review_status": ["draft"],
            "reviewed_by": [""],
            "source_quality": ["inferred_from_literature"],
            "requires_human_validation": ["true"],
        }

        updated = self.web_server.profile_from_form(profile, form)

        self.assertEqual("boletus_test", updated["species_id"])
        self.assertEqual("Boletus updated", updated["scientific_name"])
        self.assertEqual(["updated", "second"], updated["common_names"])
        self.assertEqual(
            [{"id": "host_pinus_spp", "relationship": "primary", "affinity": 0.9}],
            updated["ecology"]["host_affinities"],
        )
        self.assertEqual(40, updated["prediction_confidence"]["minimum_observations_for_calibration"])

    def test_profile_semantic_errors_report_duplicate_affinity_ids(self) -> None:
        profile = {
            "species_id": "boletus_test",
            "ecology": {
                "host_affinities": [
                    {"id": "host_pinus_spp", "relationship": "primary", "affinity": 1.0},
                    {"id": "host_pinus_spp", "relationship": "secondary", "affinity": 0.5},
                ],
                "forest_type_affinities": [],
                "soil_affinities": [],
                "lithology_affinities": [],
                "habitat_feature_affinities": [],
            },
        }

        errors = self.web_server.profile_semantic_error_messages(profile)

        self.assertEqual(
            ["profiles.boletus_test.ecology.host_affinities: contains duplicate IDs: host_pinus_spp."],
            errors,
        )

    def test_profile_semantic_errors_report_overlapping_months(self) -> None:
        profile = {
            "species_id": "boletus_test",
            "phenology": {
                "main_months": [8, 9, 10],
                "secondary_months": [6, 8],
            },
        }

        errors = self.web_server.profile_semantic_error_messages(profile)

        self.assertEqual(
            ["profiles.boletus_test.phenology: main_months and secondary_months overlap: 8."],
            errors,
        )

    def test_profile_affinity_rows_hide_already_used_ids_from_new_rows(self) -> None:
        catalogs = {
            "host_taxa": [
                {"id": "host_pinus_spp", "scientific_name": "Pinus spp."},
                {"id": "host_quercus_spp", "scientific_name": "Quercus spp."},
            ]
        }
        html = self.web_server.render_profile_affinity_rows(
            "host_affinities",
            [{"id": "host_pinus_spp", "relationship": "primary", "affinity": 1.0}],
            catalogs,
        )

        self.assertEqual(1, html.count('value="host_pinus_spp"'))
        self.assertGreaterEqual(html.count('value="host_quercus_spp"'), 2)

    def test_mushroom_profiles_post_blocks_duplicate_affinities(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        store = self.web_server.default_store()
        store.ensure_seeded()
        payload = store.load("profiles")
        profile = next(
            item
            for item in payload["species_profiles"]
            if item["species_id"] == "boletus_pinophilus"
        )
        profile["ecology"]["host_affinities"].append(dict(profile["ecology"]["host_affinities"][0]))

        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["save_profile_json"],
                "species_id": ["boletus_pinophilus"],
                "profile_return_tab": ["profile-tab-json"],
                "profile_json": [json.dumps(profile)],
            }
        )

        self.assertEqual("?id=boletus_pinophilus&section=species&profile_tab=profile-tab-json#mushroom-profile-message", redirect)
        self.assertIn(
            "host_affinities: contains duplicate IDs",
            self.web_server.RUN_STATE["mushroom_profiles_flash"],
        )

    def test_mushroom_profiles_post_blocks_overlapping_months(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        store = self.web_server.default_store()
        store.ensure_seeded()
        payload = store.load("profiles")
        profile = next(
            item
            for item in payload["species_profiles"]
            if item["species_id"] == "boletus_edulis"
        )
        profile["phenology"]["secondary_months"] = list(profile["phenology"]["main_months"][:1])

        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["save_profile_json"],
                "species_id": ["boletus_edulis"],
                "profile_return_tab": ["profile-tab-json"],
                "profile_json": [json.dumps(profile)],
            }
        )

        self.assertEqual("?id=boletus_edulis&section=species&profile_tab=profile-tab-json#mushroom-profile-message", redirect)
        self.assertIn(
            "main_months and secondary_months overlap",
            self.web_server.RUN_STATE["mushroom_profiles_flash"],
        )

    def test_mushroom_profiles_parameters_post_updates_only_parameter_blocks(self) -> None:
        data_dir = Path(self.temp_dir.name)
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")

        def restore_env() -> None:
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir / "mushroom-data")

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        store = self.web_server.default_store()
        store.ensure_seeded()
        payload = store.load("profiles")
        profile = next(
            item
            for item in payload["species_profiles"]
            if item["species_id"] == "boletus_pinophilus"
        )
        original_name = profile["scientific_name"]
        original_common_names = list(profile["common_names"])

        form = {
            "profile_action": ["save_profile_parameters"],
            "species_id": ["boletus_pinophilus"],
            "trophic_mode_id": [profile["ecology"]["trophic_mode_id"]],
            "main_months": ["\n".join(str(value) for value in profile["phenology"]["main_months"])],
            "secondary_months": ["\n".join(str(value) for value in profile["phenology"]["secondary_months"])],
            "season_pattern_ids": list(profile["phenology"]["season_pattern_ids"]),
            "preferred_aspect_ids": list(profile["topography"]["preferred_aspect_ids"]),
            "aspect_notes": [profile["topography"].get("aspect_notes", "")],
        }
        delay = profile["phenology"]["fruiting_delay_after_rain_days"]
        for key, value in {
            "delay_min": delay["min"],
            "delay_optimal_min": delay["optimal_min"],
            "delay_optimal_max": delay["optimal_max"],
            "delay_max": delay["max"],
            "altitude_min_m": profile["topography"]["altitude_min_m"],
            "altitude_optimal_min_m": profile["topography"]["altitude_optimal_min_m"],
            "altitude_optimal_max_m": profile["topography"]["altitude_optimal_max_m"],
            "altitude_max_m": profile["topography"]["altitude_max_m"],
        }.items():
            form[key] = [str(value)]
        for block_name in ("rainfall", "temperature", "humidity", "wind"):
            for key, value in profile["weather_model"][block_name].items():
                if isinstance(value, bool):
                    if value:
                        form[f"{block_name}_{key}"] = ["true"]
                else:
                    form[f"{block_name}_{key}"] = [str(value)]
        form["rainfall_rain_7d_min_mm"] = ["12"]
        for key, value in profile["scoring_weights"].items():
            form[f"score_{key}"] = [str(value)]

        redirect = handler.handle_mushroom_profiles_post(form)

        self.assertEqual("?id=boletus_pinophilus&section=parameters", redirect)
        updated_payload = store.load("profiles")
        updated = next(
            item
            for item in updated_payload["species_profiles"]
            if item["species_id"] == "boletus_pinophilus"
        )
        self.assertEqual(12, updated["weather_model"]["rainfall"]["rain_7d_min_mm"])
        self.assertEqual(original_name, updated["scientific_name"])
        self.assertEqual(original_common_names, updated["common_names"])

    def test_mushroom_profiles_flash_renders_validation_error_alert(self) -> None:
        html = self.web_server.render_mushroom_profiles_flash(
            "Species profile was not saved: profiles.boletus_test.phenology: main_months and secondary_months overlap: 8."
        )

        self.assertIn('id="mushroom-profile-message"', html)
        self.assertIn("catalog-alert error", html)
        self.assertIn("Validation error", html)
        self.assertIn("Nothing was saved", html)

    def test_mushroom_catalog_summary_uses_validator_status_not_loose_scan(self) -> None:
        catalogs = {
            "host_taxa": [{"id": "host_pinus", "scientific_name": "Pinus"}],
            "lithology_types": [{"id": "lith_limestone", "label": {"en": "Limestone"}}],
        }
        rows, metrics = self.web_server.catalog_rows(
            catalogs,
            {"species_profiles": []},
            {
                "mapping_sources": [{"mapping_type": "forest_species_or_forest_type"}],
                "derived_rules": [{"inputs": ["lith_limestone_or_dolomite_or_marl"], "outputs": ["lith_limestone"]}],
            },
        )

        html = self.web_server.render_catalog_metric_cards(metrics, errors=[], warnings=[])

        self.assertEqual(2, len(rows))
        self.assertNotIn("unknown", metrics)
        self.assertNotIn("Broken refs", html)
        self.assertIn("Reference errors", html)
        self.assertIn("Validation", html)
        self.assertIn("0 errors · 0 warnings", html)

    def test_mushroom_catalog_usage_counts_observation_references(self) -> None:
        catalogs = {
            "observer_expertise_levels": [
                {"id": "unknown", "label": {"en": "Unknown"}},
                {"id": "experienced", "label": {"en": "Experienced"}},
            ],
            "observation_calibration_uses": [
                {"id": "review", "label": {"en": "Review"}},
            ],
        }
        observations = {
            "observations": [
                {
                    "observer": {"expertise": "experienced"},
                    "calibration_use": "review",
                }
            ]
        }

        rows, metrics = self.web_server.catalog_rows(
            catalogs,
            {"species_profiles": []},
            {"mapping_sources": []},
            observations,
        )
        experienced = next(row for row in rows if row["id"] == "experienced")
        review = next(row for row in rows if row["id"] == "review")

        self.assertEqual(1, experienced["observation_count"])
        self.assertEqual(1, review["observation_count"])
        self.assertEqual("active", experienced["status"])
        self.assertEqual("active", review["status"])
        self.assertEqual(2, metrics["observation_used"])

        table_html = self.web_server.render_catalog_table(rows, experienced, "observer_expertise_levels", "")
        impact_html = self.web_server.render_catalog_domain_impact(rows, "observer_expertise_levels")

        self.assertIn("<th>Obs.</th>", table_html)
        self.assertIn("Observation references", impact_html)
        self.assertIn("<span class=\"value ok\">1</span>", impact_html)

    def test_mushroom_ui_language_is_loaded_from_addon_option_environment(self) -> None:
        old_language = os.environ.get("RAINMAPPER_MUSHROOM_UI_LANGUAGE")
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")

        def restore_env() -> None:
            if old_language is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_UI_LANGUAGE", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_UI_LANGUAGE"] = old_language
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_UI_LANGUAGE"] = "ca"
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")

        spec = importlib.util.spec_from_file_location("mushroom_profiles_ui_ca_test", MUSHROOM_PROFILES_UI_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual("Observacions", module.ui_label("ui.observations"))
        self.assertEqual("Gen", module.ui_label("month.1"))

    def test_mushroom_species_editor_translates_model_labels_and_values(self) -> None:
        old_language = os.environ.get("RAINMAPPER_MUSHROOM_UI_LANGUAGE")
        old_defaults = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR")

        def restore_env() -> None:
            if old_language is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_UI_LANGUAGE", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_UI_LANGUAGE"] = old_language
            if old_defaults is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = old_defaults

        self.addCleanup(restore_env)
        os.environ["RAINMAPPER_MUSHROOM_UI_LANGUAGE"] = "es"
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(ROOT_DIR / "mushroom-data")

        spec = importlib.util.spec_from_file_location("mushroom_profiles_ui_es_test", MUSHROOM_PROFILES_UI_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        profiles = json.loads((ROOT_DIR / "mushroom-data" / "mushroom_profiles.json").read_text(encoding="utf-8"))[
            "species_profiles"
        ]
        catalogs = json.loads(
            (ROOT_DIR / "mushroom-data" / "mushroom_reference_catalogs.json").read_text(encoding="utf-8")
        )["catalogs"]
        profile = next(item for item in profiles if item["species_id"] == "boletus_pinophilus")
        editor_html = module.render_profile_editor(profile, catalogs)
        html = "\n".join(
            [
                editor_html,
                module.render_parameters_section(profile, catalogs),
                module.render_calibration_section(profile),
            ]
        )

        self.assertIn("Lluvia min 7d", html)
        self.assertIn("Pesos de scoring", html)
        self.assertIn("Media", html)
        self.assertIn("Sin calibrar", html)
        self.assertIn("Posible a final de primavera", html)
        self.assertIn("Verano", html)
        self.assertIn("Norte", html)
        self.assertIn("Mixta", html)
        self.assertIn('name="main_months" value="6" checked', editor_html)
        self.assertIn('name="secondary_months" value="10" checked', editor_html)
        self.assertIn('name="season_pattern_ids" value="season_summer" checked', editor_html)
        self.assertIn('name="preferred_aspect_ids" value="aspect_N" checked', editor_html)
        self.assertNotIn('textarea id="profile-main_months"', editor_html)
        self.assertNotIn('textarea id="profile-season_pattern_ids"', editor_html)
        self.assertNotIn('textarea id="profile-preferred_aspect_ids"', editor_html)
        self.assertNotIn("missing label:", html)

    def test_run_script_exports_home_assistant_ui_language_option(self) -> None:
        run_script = (ROOT_DIR / "rainmapper-app" / "run.sh").read_text(encoding="utf-8")

        self.assertIn('UI_LANGUAGE_VALUE="$(option ui_language en)"', run_script)
        self.assertIn('export RAINMAPPER_MUSHROOM_UI_LANGUAGE="$UI_LANGUAGE_VALUE"', run_script)

    def test_mushroom_catalog_group_filter_selects_first_row_in_group(self) -> None:
        rows = [
            {"group": "trophic_modes", "id": "trophic_ectomycorrhizal"},
            {"group": "forest_types", "id": "forest_pinus_sylvestris"},
            {"group": "forest_types", "id": "forest_mixed_conifer"},
        ]

        selected = self.web_server.selected_catalog_row(rows, "forest_types", "")

        self.assertIsNotNone(selected)
        self.assertEqual("forest_types", selected["group"])
        self.assertEqual("forest_pinus_sylvestris", selected["id"])

    def test_mushroom_catalog_all_filter_does_not_force_first_group(self) -> None:
        rows = [
            {"group": "trophic_modes", "id": "trophic_ectomycorrhizal"},
            {"group": "forest_types", "id": "forest_pinus_sylvestris"},
        ]
        selected_group = ""
        selected_id = ""
        selected = self.web_server.selected_catalog_row(rows, selected_group, selected_id)
        if selected and selected_group and not selected_id:
            selected_id = str(selected["id"])

        self.assertIsNotNone(selected)
        self.assertEqual("", selected_group)
        self.assertEqual("", selected_id)
        self.assertEqual("trophic_modes", selected["group"])

    def test_catalog_entry_form_preserves_unknown_fields_and_updates_labels(self) -> None:
        existing = {
            "id": "soil_calcareous",
            "label": {"es": "Suelo calcareo", "ca": "Sol calcari", "en": "Calcareous soil"},
            "ph_min": 7.0,
            "ph_max": 8.5,
            "custom_future_field": "keep-me",
        }
        form = {
            "label_es": ["Suelo calcáreo"],
            "label_ca": ["Sòl calcari"],
            "label_en": ["Calcareous soil"],
            "ph_min": ["7.2"],
            "ph_max": ["8.5"],
            "texture": [""],
            "organic_matter": [""],
            "drainage": ["Moderate"],
            "gis_aliases": ["limestone\ncalcareous"],
        }

        entry = self.web_server.catalog_entry_from_form("soil_types", "soil_calcareous", existing, form)

        self.assertEqual("soil_calcareous", entry["id"])
        self.assertEqual("Suelo calcáreo", entry["label"]["es"])
        self.assertEqual(7.2, entry["ph_min"])
        self.assertEqual(8.5, entry["ph_max"])
        self.assertEqual(["limestone", "calcareous"], entry["gis_aliases"])
        self.assertEqual("keep-me", entry["custom_future_field"])

    def test_catalog_entry_form_updates_host_common_names_as_lists(self) -> None:
        existing = {
            "id": "host_pinus_sylvestris",
            "rank": "species",
            "scientific_name": "Pinus sylvestris",
            "genus": "Pinus",
            "family": "Pinaceae",
            "common_names": {"es": ["Pino silvestre"]},
            "parent_id": "host_pinus_spp",
        }
        form = {
            "rank": ["species"],
            "scientific_name": ["Pinus sylvestris"],
            "genus": ["Pinus"],
            "family": ["Pinaceae"],
            "parent_id": ["host_pinus_spp"],
            "common_names_es": ["Pino silvestre, Pino rojo"],
            "common_names_ca": ["Pi roig"],
            "common_names_en": ["Scots pine"],
            "gis_aliases": ["Pinus sylvestris"],
        }

        entry = self.web_server.catalog_entry_from_form("host_taxa", "host_pinus_sylvestris", existing, form)

        self.assertEqual(["Pino silvestre", "Pino rojo"], entry["common_names"]["es"])
        self.assertEqual(["Pi roig"], entry["common_names"]["ca"])
        self.assertEqual(["Scots pine"], entry["common_names"]["en"])
        self.assertEqual(["Pinus sylvestris"], entry["gis_aliases"])

    def test_catalog_cross_reference_checks_validate_host_parent_id(self) -> None:
        catalogs = {
            "host_taxa": [
                {"id": "host_pinaceae"},
                {"id": "host_pinus_spp", "parent_id": "host_pinaceae"},
            ]
        }

        valid_checks = self.web_server.catalog_cross_reference_checks(
            "host_taxa",
            {"id": "host_pinus_spp", "parent_id": "host_pinaceae"},
            catalogs,
        )
        invalid_checks = self.web_server.catalog_cross_reference_checks(
            "host_taxa",
            {"id": "host_pinus_spp", "parent_id": "host_missing"},
            catalogs,
        )

        self.assertEqual("ok", valid_checks[0][0])
        self.assertEqual("parent_id", valid_checks[0][1])
        self.assertEqual("error", invalid_checks[0][0])
        self.assertIn("host_missing", invalid_checks[0][2])

    def test_catalog_cross_reference_checks_validate_forest_and_lithology_refs(self) -> None:
        catalogs = {
            "host_taxa": [{"id": "host_pinus_spp"}],
            "forest_types": [{"id": "forest_montane_pine"}],
            "soil_types": [{"id": "soil_acidic"}],
        }

        forest_checks = self.web_server.catalog_cross_reference_checks(
            "forest_types",
            {
                "id": "forest_montane_pine",
                "dominant_host_ids": ["host_pinus_spp", "host_missing"],
                "soil_bias_ids": ["soil_missing"],
            },
            catalogs,
        )
        lithology_checks = self.web_server.catalog_cross_reference_checks(
            "lithology_types",
            {"id": "lith_granite", "parent_soil_tendency_ids": ["soil_missing"]},
            catalogs,
        )

        self.assertTrue(any(check[0] == "error" and "host_missing" in check[2] for check in forest_checks))
        self.assertTrue(any(check[0] == "error" and "soil_missing" in check[2] for check in forest_checks))
        self.assertTrue(any(check[0] == "error" and "soil_missing" in check[2] for check in lithology_checks))

    def test_basic_role_allows_two_devices_and_reusing_existing_device(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "basic",
                    "name": "Basic User",
                    "email": "basic@example.com",
                    "password": "secret",
                    "role": "basic",
                    "enabled": True,
                }
            ]
        )

        self.assertEqual(self.login("basic", "secret", "device-a")[0], 200)
        self.assertEqual(self.login("basic", "secret", "device-b")[0], 200)
        self.assertEqual(self.login("basic", "secret", "device-a")[0], 200)

        third_status, third_response = self.login("basic", "secret", "device-c")
        self.assertEqual(third_status, 403)
        self.assertIn("(2)", third_response["error"])

    def test_explicit_max_devices_overrides_role_default(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "pro",
                    "name": "Pro User",
                    "email": "pro@example.com",
                    "password": "secret",
                    "role": "pro",
                    "enabled": True,
                    "max_devices": 4,
                }
            ]
        )

        for index in range(4):
            status, response = self.login("pro", "secret", f"device-{index}")
            self.assertEqual(status, 200, response)
            self.assertEqual(response["name"], "Pro User")
            self.assertEqual(response["email"], "pro@example.com")

        blocked_status, blocked_response = self.login("pro", "secret", "device-4")
        self.assertEqual(blocked_status, 403)
        self.assertIn("(4)", blocked_response["error"])

    def test_admin_role_is_unlimited_by_default(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "admin",
                    "name": "Admin User",
                    "email": "admin@example.com",
                    "password": "secret",
                    "role": "admin",
                    "enabled": True,
                }
            ]
        )

        for index in range(5):
            status, response = self.login("admin", "secret", f"admin-device-{index}")
            self.assertEqual(status, 200, response)
            self.assertEqual(response["max_devices"], 0)
            self.assertTrue(response["can_use_heatmap"])
            self.assertTrue(response["can_use_layer_metrics"])
            self.assertTrue(response["can_use_estimated_field"])

    def test_missing_users_json_rejects_login(self) -> None:
        status, response = self.login("missing", "secret", "device-a")

        self.assertEqual(status, 401)
        self.assertFalse(response["ok"])

    def test_create_user_hashes_password_and_allows_login(self) -> None:
        message = self.web_server.create_user(
            "new-user",
            "New User",
            "new@example.com",
            "secret",
            "basic",
            "true",
            "2",
        )

        self.assertIn("Created user", message)
        users = self.web_server.read_users()
        self.assertTrue(users["new-user"]["password"].startswith("pbkdf2_sha256$"))
        self.assertTrue(users["new-user"]["created_at"].endswith("Z"))
        self.assertTrue(users["new-user"]["updated_at"].endswith("Z"))
        self.assertEqual(users["new-user"]["created_at"], users["new-user"]["updated_at"])
        self.assertEqual(users["new-user"]["last_change"], "created user")

        status, response = self.login("new-user", "secret", "device-a")
        self.assertEqual(status, 200, response)
        self.assertEqual(response["name"], "New User")
        self.assertEqual(response["max_devices"], 2)
        self.assertFalse(response["can_use_heatmap"])
        self.assertFalse(response["can_use_layer_metrics"])
        self.assertFalse(response["can_use_estimated_field"])

    def test_admin_user_creation_enables_maplibre_feature_permissions_by_default(self) -> None:
        message = self.web_server.create_user(
            "admin2",
            "Admin User",
            "admin2@example.com",
            "secret",
            "admin",
            "true",
            "",
        )

        self.assertIn("Created user", message)
        users = self.web_server.read_users()
        self.assertEqual(users["admin2"]["can_use_heatmap"], "true")
        self.assertEqual(users["admin2"]["can_use_layer_metrics"], "true")
        self.assertEqual(users["admin2"]["can_use_estimated_field"], "true")

        status, response = self.login("admin2", "secret", "device-a")
        self.assertEqual(status, 200, response)
        self.assertTrue(response["can_use_heatmap"])
        self.assertTrue(response["can_use_layer_metrics"])
        self.assertTrue(response["can_use_estimated_field"])

    def test_update_user_controls_maplibre_feature_permissions(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "basic",
                    "name": "Basic User",
                    "email": "basic@example.com",
                    "password": "secret",
                    "role": "basic",
                    "enabled": True,
                }
            ]
        )

        message = self.web_server.update_user(
            "basic",
            "Basic User",
            "basic@example.com",
            "basic",
            "true",
            "2",
            "true",
            "",
            "true",
        )

        self.assertIn("Updated user basic", message)
        users = self.web_server.read_users()
        self.assertEqual(users["basic"]["can_use_heatmap"], "true")
        self.assertEqual(users["basic"]["can_use_layer_metrics"], "false")
        self.assertEqual(users["basic"]["can_use_estimated_field"], "true")
        self.assertTrue(users["basic"]["updated_at"].endswith("Z"))
        self.assertEqual(users["basic"]["last_change"], "updated user settings")

        status, response = self.login("basic", "secret", "device-a")
        self.assertEqual(status, 200, response)
        self.assertTrue(response["can_use_heatmap"])
        self.assertFalse(response["can_use_layer_metrics"])
        self.assertTrue(response["can_use_estimated_field"])

    def test_set_password_replaces_existing_password_and_deletes_devices(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "basic",
                    "name": "Basic User",
                    "email": "basic@example.com",
                    "password": "old-secret",
                    "role": "basic",
                    "enabled": True,
                }
            ]
        )

        self.assertEqual(self.login("basic", "old-secret", "device-a")[0], 200)
        message = self.web_server.set_admin_user_password("basic", "new-secret")

        self.assertIn("Set password", message)
        self.assertIn("deleted 1 device", message)
        self.assertEqual(self.web_server.read_users()["basic"]["last_change"], "set password; deleted 1 device(s)")
        self.assertEqual(self.web_server.read_devices(), {})
        self.assertEqual(self.login("basic", "old-secret", "device-b")[0], 401)
        self.assertEqual(self.login("basic", "new-secret", "device-b")[0], 200)

    def test_reset_password_forces_user_to_choose_different_password(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "basic",
                    "name": "Basic User",
                    "email": "basic@example.com",
                    "password": "old-secret",
                    "role": "basic",
                    "enabled": True,
                }
            ]
        )

        self.assertEqual(self.login("basic", "old-secret", "device-a")[0], 200)
        message = self.web_server.require_user_password_change("basic")

        self.assertIn("Reset password", message)
        self.assertEqual(self.web_server.read_users()["basic"]["last_change"], "reset password; deleted 1 device(s)")
        self.assertEqual(self.web_server.read_devices(), {})
        login_status, login_response = self.login("basic", "old-secret", "device-a")
        self.assertEqual(login_status, 403)
        self.assertEqual(login_response["code"], "password_change_required")

        same_status, same_response = self.web_server.change_required_password(
            "basic",
            "old-secret",
            "old-secret",
            "device-a",
            "unit-test",
        )
        self.assertEqual(same_status, 400)
        self.assertIn("different", same_response["error"])

        changed_status, changed_response = self.web_server.change_required_password(
            "basic",
            "old-secret",
            "new-secret",
            "device-a",
            "unit-test",
        )
        self.assertEqual(changed_status, 200, changed_response)
        self.assertEqual(changed_response["username"], "basic")
        self.assertEqual(self.login("basic", "old-secret", "device-b")[0], 401)
        self.assertEqual(self.login("basic", "new-secret", "device-b")[0], 200)
        self.assertEqual(self.web_server.read_users()["basic"]["must_change_password"], "false")

    def test_delete_single_and_all_user_devices(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "pro",
                    "name": "Pro User",
                    "email": "pro@example.com",
                    "password": "secret",
                    "role": "pro",
                    "enabled": True,
                }
            ]
        )
        self.assertEqual(self.login("pro", "secret", "device-a")[0], 200)
        self.assertEqual(self.login("pro", "secret", "device-b")[0], 200)

        self.web_server.delete_device("device-a")
        devices = self.web_server.read_devices()
        self.assertNotIn("device-a", devices)
        self.assertIn("device-b", devices)
        self.assertEqual(self.web_server.read_users()["pro"]["last_change"], "deleted device device-a")

        self.web_server.delete_user_devices("pro")
        self.assertEqual(self.web_server.read_users()["pro"]["last_change"], "deleted all devices (1)")
        self.assertEqual(self.web_server.read_devices(), {})

    def test_delete_user_removes_user_and_devices(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "pro",
                    "name": "Pro User",
                    "email": "pro@example.com",
                    "password": "secret",
                    "role": "pro",
                    "enabled": True,
                }
            ]
        )
        self.assertEqual(self.login("pro", "secret", "device-a")[0], 200)
        self.assertEqual(self.login("pro", "secret", "device-b")[0], 200)

        message = self.web_server.delete_user("pro")

        self.assertIn("Deleted user pro", message)
        self.assertEqual(self.web_server.read_users(), {})
        self.assertEqual(self.web_server.read_devices(), {})
        self.assertEqual(self.login("pro", "secret", "device-c")[0], 401)

    def test_users_page_has_manual_refresh_and_searchable_device_content(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "diego",
                    "name": "Diego Mobile",
                    "email": "diego@example.com",
                    "password": "secret",
                    "role": "free",
                    "enabled": True,
                    "max_devices": 1,
                }
            ]
        )
        self.web_server.DEVICES_PATH.write_text(
            json.dumps(
                {
                    "devices": {
                        "device-mobile": {
                            "username": "diego",
                            "email": "diego@example.com",
                            "created_at": "2026-06-22T10:00:00Z",
                            "last_seen_at": "2026-06-22T11:00:00Z",
                            "user_agent": "Mobile Safari Test Agent",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        with self.web_server.RUN_LOCK:
            self.web_server.RUN_STATE["users_flash"] = "Created user: diego"
        captured = {}

        def capture_response(status: int, content: bytes, content_type: str) -> None:
            captured["status"] = status
            captured["content"] = content.decode("utf-8")
            captured["content_type"] = content_type

        handler.send_bytes = capture_response
        handler.render_users()

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        self.assertIn('id="users-refresh"', page)
        self.assertIn('id="users-filter"', page)
        self.assertIn('id="users-content"', page)
        self.assertIn('id="users-list"', page)
        self.assertIn('class="user-card"', page)
        self.assertIn('data-username="diego"', page)
        self.assertIn('data-user-search="diego Diego Mobile diego@example.com free enabled no heatmap no metrics no estimated field current 1 1', page)
        self.assertIn('data-device-search="device-mobile diego diego@example.com Mobile Safari Test Agent', page)
        self.assertIn("data-user-toggle", page)
        self.assertIn('aria-expanded="false"', page)
        self.assertIn(".user-panel[hidden]", page)
        self.assertIn("function collapseUserCards()", page)
        self.assertNotIn("rainmapperUsersExpanded", page)
        self.assertIn('id="create-user-modal"', page)
        self.assertIn("data-create-user-open", page)
        self.assertIn("confirmUserAdminAction(this)", page)
        self.assertIn('class="user-update-form"', page)
        self.assertIn('class="permissions-grid"', page)
        self.assertIn('class="permission-card permission-card-heatmap"', page)
        self.assertIn('name="can_use_heatmap" type="checkbox" value="true"', page)
        self.assertIn('name="can_use_layer_metrics" type="checkbox" value="true"', page)
        self.assertIn('name="can_use_estimated_field" type="checkbox" value="true"', page)
        self.assertIn("audit-strip", page)
        self.assertIn('class="security-password-form"', page)
        self.assertIn("Save changes for user diego?", page)
        self.assertIn("Set a new password for user diego and delete all registered devices?", page)
        self.assertIn("Reset password for user diego, force password change and delete all registered devices?", page)
        self.assertIn("Delete all registered devices for user diego?", page)
        self.assertIn("Delete user diego and all registered devices?", page)
        self.assertIn("Delete device device-mobile for user diego?", page)
        self.assertIn('window.alert("Created user: diego")', page)

    def test_device_settings_are_sanitized_and_stored_on_device(self) -> None:
        self.write_users_json(
            [
                {
                    "username": "basic",
                    "name": "Basic User",
                    "email": "basic@example.com",
                    "password": "secret",
                    "role": "basic",
                    "enabled": True,
                }
            ]
        )
        self.assertEqual(self.login("basic", "secret", "device-a")[0], 200)

        ok, settings = self.web_server.update_device_settings(
            "device-a",
            {
                "period": "21d.geojson",
                "min_rain_mm": 12500,
                "map_style": "esri-hybrid",
                "language": "ca",
                "last_rains_history": 12,
                "station_sources": ["Meteocat", "AEMET", "Unknown", "Invalid", "Meteocat"],
                "terrain_enabled": True,
                "terrain_exaggeration": 9,
                "layer_metric": "max_humidity",
                "heatmap_enabled": True,
                "heatmap_opacity": 1.5,
                "heatmap_radius_scale": 0.1,
                "heatmap_intensity_scale": 9,
                "heatmap_weight_curve": "strong",
                "estimated_field_enabled": True,
                "estimated_field_opacity": 1.5,
                "estimated_field_radius": "large",
                "estimated_field_quality": "high",
                "estimated_field_smoothing": "local",
                "estimated_field_altitude_correction": True,
                "map_view": {
                    "lng": 2.1234567,
                    "lat": 41.9876543,
                    "zoom": 8.12345,
                    "bearing": -12.345,
                    "pitch": 91,
                },
                "ignored": "value",
            },
        )

        self.assertTrue(ok)
        self.assertEqual(
            settings,
            {
                "period": "21d.geojson",
                "map_style": "esri-hybrid",
                "language": "ca",
                "min_rain_mm": 10000.0,
                "last_rains_history": 12,
                "station_sources": ["Meteocat", "AEMET", "Unknown"],
                "terrain_enabled": True,
                "terrain_exaggeration": 3.0,
                "layer_metric": "max_humidity",
                "heatmap_enabled": True,
                "heatmap_opacity": 1.0,
                "heatmap_radius_scale": 0.5,
                "heatmap_intensity_scale": 2.0,
                "heatmap_weight_curve": "strong",
                "estimated_field_enabled": True,
                "estimated_field_opacity": 1.0,
                "estimated_field_radius": "large",
                "estimated_field_quality": "high",
                "estimated_field_smoothing": "local",
                "estimated_field_altitude_correction": True,
                "map_view": {
                    "lng": 2.123457,
                    "lat": 41.987654,
                    "zoom": 8.123,
                    "bearing": -12.35,
                    "pitch": 85.0,
                },
            },
        )
        self.assertEqual(self.web_server.settings_for_device("device-a"), settings)

        ok, settings = self.web_server.update_device_settings("device-a", {"terrain_enabled": "false"})
        self.assertTrue(ok)
        self.assertFalse(settings["terrain_enabled"])
        self.assertNotIn("heatmap_opacity", settings)
        self.assertNotIn("heatmap_radius_scale", settings)
        self.assertNotIn("heatmap_intensity_scale", settings)
        self.assertNotIn("estimated_field_opacity", settings)
        self.assertNotIn("estimated_field_radius", settings)

    def test_device_settings_do_not_synthesize_heatmap_tuning_defaults(self) -> None:
        settings = self.web_server.sanitize_device_settings({"terrain_enabled": "false"})

        self.assertFalse(settings["terrain_enabled"])
        self.assertNotIn("heatmap_opacity", settings)
        self.assertNotIn("heatmap_radius_scale", settings)
        self.assertNotIn("heatmap_intensity_scale", settings)
        self.assertNotIn("estimated_field_opacity", settings)
        self.assertNotIn("estimated_field_radius", settings)

    def test_device_settings_reject_unknown_device(self) -> None:
        ok, settings = self.web_server.update_device_settings("missing-device", {"period": "21d.geojson"})

        self.assertFalse(ok)
        self.assertEqual(settings, {})

    def test_users_page_does_not_auto_refresh(self) -> None:
        page = self.web_server.html_page("Users", "<h1>Users</h1>", auto_refresh=False).decode("utf-8")

        self.assertNotIn('http-equiv="refresh"', page)

    def test_webui_update_command_passes_aemet_source_option(self) -> None:
        previous = os.environ.get("RAINMAPPER_CREATE_AEMET")
        os.environ["RAINMAPPER_CREATE_AEMET"] = "true"
        try:
            command = self.web_server.command_for("update")
        finally:
            if previous is None:
                os.environ.pop("RAINMAPPER_CREATE_AEMET", None)
            else:
                os.environ["RAINMAPPER_CREATE_AEMET"] = previous

        self.assertIn("--create_aemet", command)
        self.assertEqual(command[command.index("--create_aemet") + 1], "true")

    def test_webui_update_command_can_target_only_one_source(self) -> None:
        command = self.web_server.command_for("update", only_source="AEMET")

        self.assertEqual(command[command.index("--create_meteoclimatic") + 1], "false")
        self.assertEqual(command[command.index("--create_meteocat") + 1], "false")
        self.assertEqual(command[command.index("--create_wunderground") + 1], "false")
        self.assertEqual(command[command.index("--create_aemet") + 1], "true")

        command = self.web_server.command_for("update", only_source="Meteocat")

        self.assertEqual(command[command.index("--create_meteoclimatic") + 1], "false")
        self.assertEqual(command[command.index("--create_meteocat") + 1], "true")
        self.assertEqual(command[command.index("--create_wunderground") + 1], "false")
        self.assertEqual(command[command.index("--create_aemet") + 1], "false")

    def test_webui_maps_command_includes_aemet_in_production_tomap(self) -> None:
        command = self.web_server.command_for("maps")

        self.assertEqual(command[:2], ["sh", "-c"])
        self.assertIn("--include-aemet true", command[2])

    def test_maplibre_config_includes_sanitized_hover_zoom(self) -> None:
        previous_values = {
            name: os.environ.get(name)
            for name in (
                "RAINMAPPER_MAPLIBRE_HOVER_ZOOM",
                "RAINMAPPER_MAPLIBRE_HEATMAP_WEIGHT_CURVE",
                "RAINMAPPER_MAPLIBRE_HEATMAP_OPACITY",
                "RAINMAPPER_MAPLIBRE_HEATMAP_RADIUS",
                "RAINMAPPER_MAPLIBRE_HEATMAP_INTENSITY",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ENABLED",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_OPACITY",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_QUALITY",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ALTITUDE_CORRECTION",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_SMALL_KM",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_MEDIUM_KM",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_LARGE_KM",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_MAX_RADIUS_KM",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_LOW_CELL_KM",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_MEDIUM_CELL_KM",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_HIGH_CELL_KM",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_SMOOTH_POWER",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_BALANCED_POWER",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_LOCAL_POWER",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_TEMPERATURE_LAPSE_RATE_C_PER_100M",
            )
        }
        os.environ.update(
            {
                "RAINMAPPER_MAPLIBRE_HOVER_ZOOM": "6.5",
                "RAINMAPPER_MAPLIBRE_HEATMAP_WEIGHT_CURVE": "soft",
                "RAINMAPPER_MAPLIBRE_HEATMAP_OPACITY": "65",
                "RAINMAPPER_MAPLIBRE_HEATMAP_RADIUS": "90",
                "RAINMAPPER_MAPLIBRE_HEATMAP_INTENSITY": "70",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ENABLED": "true",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_OPACITY": "55",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS": "large",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_QUALITY": "high",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING": "local",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ALTITUDE_CORRECTION": "true",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_SMALL_KM": "8.5",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_MEDIUM_KM": "20",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_LARGE_KM": "45.5",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_MAX_RADIUS_KM": "85.5",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_LOW_CELL_KM": "12",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_MEDIUM_CELL_KM": "6.5",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_HIGH_CELL_KM": "3.25",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_SMOOTH_POWER": "1.2",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_BALANCED_POWER": "2.2",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_LOCAL_POWER": "3.2",
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_TEMPERATURE_LAPSE_RATE_C_PER_100M": "0.6",
            }
        )
        try:
            config_js = self.web_server.auth_required_config_js()
            payload = json.loads(config_js.removeprefix("window.RAINMAPPER_CONFIG = ").removesuffix(";\n"))

            self.assertEqual(payload["hoverPopupMinZoom"], 6.5)
            self.assertEqual(
                payload["heatmapDefaults"],
                {
                    "weightCurve": "soft",
                    "opacity": 0.65,
                    "radiusScale": 0.9,
                    "intensityScale": 0.7,
                },
            )
            self.assertEqual(
                payload["estimatedField"],
                {
                    "defaults": {
                        "enabled": True,
                        "opacity": 0.55,
                        "radius": "large",
                        "quality": "high",
                        "smoothing": "local",
                        "altitudeCorrection": True,
                    },
                    "radiusKm": {"small": 8.5, "medium": 20.0, "large": 45.5},
                    "maxRadiusKm": 85.5,
                    "grid": {"low": 12.0, "medium": 6.5, "high": 3.25},
                    "smoothingPower": {"smooth": 1.2, "balanced": 2.2, "local": 3.2},
                    "temperatureLapseRateCPer100m": 0.6,
                },
            )

            os.environ["RAINMAPPER_MAPLIBRE_HOVER_ZOOM"] = "999"
            self.assertEqual(self.web_server.maplibre_hover_zoom(), 22)

            os.environ["RAINMAPPER_MAPLIBRE_HOVER_ZOOM"] = "4.5"
            self.assertEqual(self.web_server.maplibre_hover_zoom(), 4.5)

            os.environ["RAINMAPPER_MAPLIBRE_HOVER_ZOOM"] = "invalid"
            self.assertEqual(self.web_server.maplibre_hover_zoom(), 6)

            os.environ["RAINMAPPER_MAPLIBRE_HEATMAP_WEIGHT_CURVE"] = "invalid"
            os.environ["RAINMAPPER_MAPLIBRE_HEATMAP_OPACITY"] = "200"
            os.environ["RAINMAPPER_MAPLIBRE_HEATMAP_RADIUS"] = "10"
            os.environ["RAINMAPPER_MAPLIBRE_HEATMAP_INTENSITY"] = "invalid"
            self.assertEqual(
                self.web_server.maplibre_heatmap_defaults(),
                {
                    "weightCurve": "soft",
                    "opacity": 1.0,
                    "radiusScale": 0.5,
                    "intensityScale": 0.7,
                },
            )
        finally:
            for name, previous in previous_values.items():
                if previous is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = previous

    def test_protected_maplibre_config_is_not_cached(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured: dict[str, object] = {"headers": []}

        class MemoryWriter:
            def __init__(self) -> None:
                self.content = b""

            def write(self, content: bytes) -> None:
                self.content += content

        writer = MemoryWriter()
        handler.wfile = writer
        handler.send_response = lambda status: captured.update({"status": status})
        handler.send_header = lambda name, value: captured["headers"].append((name, value))
        handler.end_headers = lambda: None

        handler.serve_protected_maplibre("/config.js")

        self.assertEqual(captured["status"], 200)
        self.assertIn(("Cache-Control", "no-store, max-age=0"), captured["headers"])
        self.assertIn(b"window.RAINMAPPER_CONFIG", writer.content)


if __name__ == "__main__":
    unittest.main()
