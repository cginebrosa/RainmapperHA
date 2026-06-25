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


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_SERVER_PATH = ROOT_DIR / "rainmapper-app" / "app" / "web_server.py"


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

        status, response = self.login("new-user", "secret", "device-a")
        self.assertEqual(status, 200, response)
        self.assertEqual(response["name"], "New User")
        self.assertEqual(response["max_devices"], 2)
        self.assertFalse(response["can_use_heatmap"])
        self.assertFalse(response["can_use_layer_metrics"])

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

        status, response = self.login("admin2", "secret", "device-a")
        self.assertEqual(status, 200, response)
        self.assertTrue(response["can_use_heatmap"])
        self.assertTrue(response["can_use_layer_metrics"])

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
        )

        self.assertIn("Updated user basic", message)
        users = self.web_server.read_users()
        self.assertEqual(users["basic"]["can_use_heatmap"], "true")
        self.assertEqual(users["basic"]["can_use_layer_metrics"], "false")

        status, response = self.login("basic", "secret", "device-a")
        self.assertEqual(status, 200, response)
        self.assertTrue(response["can_use_heatmap"])
        self.assertFalse(response["can_use_layer_metrics"])

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

        self.web_server.delete_user_devices("pro")
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
        self.assertIn('data-user-search="diego Diego Mobile diego@example.com free enabled no heatmap no metrics current 1 1"', page)
        self.assertIn('data-device-search="device-mobile diego diego@example.com Mobile Safari Test Agent', page)

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

    def test_device_settings_do_not_synthesize_heatmap_tuning_defaults(self) -> None:
        settings = self.web_server.sanitize_device_settings({"terrain_enabled": "false"})

        self.assertFalse(settings["terrain_enabled"])
        self.assertNotIn("heatmap_opacity", settings)
        self.assertNotIn("heatmap_radius_scale", settings)
        self.assertNotIn("heatmap_intensity_scale", settings)

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
            )
        }
        os.environ.update(
            {
                "RAINMAPPER_MAPLIBRE_HOVER_ZOOM": "6.5",
                "RAINMAPPER_MAPLIBRE_HEATMAP_WEIGHT_CURVE": "soft",
                "RAINMAPPER_MAPLIBRE_HEATMAP_OPACITY": "65",
                "RAINMAPPER_MAPLIBRE_HEATMAP_RADIUS": "90",
                "RAINMAPPER_MAPLIBRE_HEATMAP_INTENSITY": "70",
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
