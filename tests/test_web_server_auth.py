"""Functional tests for the lightweight MapLibre authentication backend.

These tests keep all state in a temporary directory so they do not touch the
real Home Assistant `/share/rainmapper` files or any developer-local devices.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import threading
import time
import unittest
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin
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

    def reset_run_state(self) -> None:
        with self.web_server.RUN_LOCK:
            self.web_server.RUN_STATE.update(
                {
                    "running": False,
                    "action": "",
                    "started_at": "",
                    "finished_at": "",
                    "duration": "",
                    "exit_code": "",
                }
            )

    def test_runner_releases_predictor_cache_before_starting(self) -> None:
        fake_runner_thread = mock.MagicMock()
        self.addCleanup(self.reset_run_state)

        with (
            mock.patch.object(
                self.web_server.mushroom_predictor_ui,
                "release_predictor_cache",
                return_value=2,
            ) as release_cache,
            mock.patch.object(
                self.web_server.runtime_diagnostics,
                "new_operation_id",
                return_value="coordination-test",
            ),
            mock.patch.object(
                self.web_server.runtime_diagnostics,
                "record_event",
            ) as record_event,
            mock.patch.object(
                self.web_server.threading,
                "Thread",
                return_value=fake_runner_thread,
            ),
        ):
            started = self.web_server.run_action("all", "unit-test")

        self.assertTrue(started)
        release_cache.assert_called_once_with()
        fake_runner_thread.start.assert_called_once_with()
        details = record_event.call_args.args[3]
        self.assertEqual(details["released_predictor_instances"], 2)
        self.assertEqual(details["cache_release_error"], "")

    def test_ml_train_promotion_promotes_report_and_releases_predictor_cache(self) -> None:
        result_root = Path(self.temp_dir.name) / "results"
        models_dir = Path(self.temp_dir.name) / "ml_models"
        report_path = Path(self.temp_dir.name) / "mushroom_ml_v0_report.json"
        promotion = {"status": "promoted", "promoted_files": ["model.joblib"]}
        with (
            mock.patch.object(
                self.web_server,
                "mushroom_worker_candidate_results_path",
                return_value=result_root,
            ),
            mock.patch.object(
                self.web_server.mushroom_paths,
                "mushroom_ml_models_dir",
                return_value=models_dir,
            ),
            mock.patch.object(
                self.web_server.mushroom_paths,
                "mushroom_ml_report_json_path",
                return_value=report_path,
            ),
            mock.patch.object(
                self.web_server.mushroom_worker_results,
                "promote_ml_train_candidate",
                return_value=dict(promotion),
            ) as promote_candidate,
            mock.patch.object(
                self.web_server.mushroom_predictor_ui,
                "release_predictor_cache",
                return_value=3,
            ) as release_cache,
            mock.patch.object(
                self.web_server.mushroom_worker_jobs,
                "update_candidate_promotion_progress",
            ),
            mock.patch.object(
                self.web_server.mushroom_worker_jobs,
                "finish_candidate_promotion",
            ) as finish_promotion,
            mock.patch.object(self.web_server, "set_mushroom_workers_flash"),
        ):
            self.web_server._run_mushroom_worker_ml_train_promotion(
                "worker_job_mltrain1234"
            )

        promote_candidate.assert_called_once_with(
            result_root,
            models_dir,
            job_id="worker_job_mltrain1234",
            report_path=report_path,
        )
        release_cache.assert_called_once_with()
        promoted_result = finish_promotion.call_args.kwargs["result"]
        self.assertEqual(promoted_result["released_predictor_instances"], 3)

    def test_predictor_lists_only_models_declared_trained_by_live_report(self) -> None:
        models_dir = Path(self.temp_dir.name) / "ml_models"
        models_dir.mkdir()
        for species_id in ("boletus_aereus", "stale_species"):
            (models_dir / f"mushroom_ml_v0_{species_id}.joblib").write_bytes(b"model")
        report_path = Path(self.temp_dir.name) / "mushroom_ml_v0_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "species_results": [
                        {"species_id": "boletus_aereus", "skipped": False},
                        {"species_id": "stale_species", "skipped": True},
                    ]
                }
            ),
            encoding="utf-8",
        )
        predictor_ui = self.web_server.mushroom_predictor_ui
        predictor_ui._ml_report_cache = None
        predictor_ui._ml_report_mtime = None
        with (
            mock.patch.object(
                predictor_ui.mushroom_paths,
                "mushroom_ml_models_dir",
                return_value=models_dir,
            ),
            mock.patch.object(
                predictor_ui.mushroom_paths,
                "mushroom_ml_report_json_path",
                return_value=report_path,
            ),
        ):
            self.assertEqual(predictor_ui.trained_species_ids(), ["boletus_aereus"])

    def test_runner_waits_for_an_active_predictor_lock(self) -> None:
        self.addCleanup(self.reset_run_state)
        entered = threading.Event()
        finished = threading.Event()

        def request_runner() -> None:
            entered.set()
            self.web_server.run_action("all", "unit-test")
            finished.set()

        runner_request = threading.Thread(target=request_runner)
        fake_runner_thread = mock.MagicMock()
        with (
            mock.patch.object(
                self.web_server.mushroom_predictor_ui,
                "release_predictor_cache",
                return_value=0,
            ) as release_cache,
            mock.patch.object(
                self.web_server.runtime_diagnostics,
                "record_event",
            ),
            mock.patch.object(
                self.web_server.threading,
                "Thread",
                return_value=fake_runner_thread,
            ),
        ):
            with self.web_server.PREDICTOR_RUN_LOCK:
                runner_request.start()
                self.assertTrue(entered.wait(timeout=1))
                self.assertFalse(finished.wait(timeout=0.05))
                release_cache.assert_not_called()
            runner_request.join(timeout=1)

        self.assertFalse(runner_request.is_alive())
        self.assertTrue(finished.is_set())
        release_cache.assert_called_once_with()

    def test_predictor_shows_a_localized_notice_while_runner_is_active(self) -> None:
        self.addCleanup(self.reset_run_state)
        with self.web_server.RUN_LOCK:
            self.web_server.RUN_STATE["running"] = True
        handler = self.web_server.RainmapperHandler.__new__(
            self.web_server.RainmapperHandler
        )
        captured: dict[str, object] = {}
        handler.send_bytes = lambda status, content, content_type: captured.update(
            status=status,
            content=content,
            content_type=content_type,
        )

        handler.render_mushroom_predictor()

        self.assertEqual(captured["status"], 200)
        content = captured["content"].decode("utf-8")
        self.assertIn("Predictor", content)
        self.assertIn("runner", content)
        self.assertNotIn("Cannot load predictor", content)

    def test_predictor_records_full_server_request_and_embeds_client_timing(self) -> None:
        self.addCleanup(self.reset_run_state)
        handler = self.web_server.RainmapperHandler.__new__(
            self.web_server.RainmapperHandler
        )
        captured: dict[str, object] = {}
        handler.send_bytes = lambda status, content, content_type: captured.update(
            status=status,
            content=content,
            content_type=content_type,
        )
        store = mock.MagicMock()
        store.load.return_value = {"species_profiles": []}

        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            with (
                mock.patch.dict(
                    self.web_server.os.environ,
                    {"RAINMAPPER_RUNTIME_DIAGNOSTICS_PATH": str(metrics_path)},
                ),
                mock.patch.object(
                    self.web_server.mushroom_predictor_ui,
                    "predictor_cache_info",
                    return_value={
                        "predictor_instance_count": 0,
                        "cold_request": True,
                    },
                ),
                mock.patch.object(self.web_server, "default_store", return_value=store),
                mock.patch.object(
                    self.web_server.mushroom_known_sites,
                    "load_payload",
                    return_value={"known_sites": []},
                ),
                mock.patch.object(
                    self.web_server.mushroom_predictor_ui,
                    "render_page",
                    return_value="<div>predictor</div>",
                ),
            ):
                handler.render_mushroom_predictor()

            records = [
                json.loads(line)
                for line in metrics_path.read_text(encoding="utf-8").splitlines()
            ]
            summaries = [
                json.loads(line)
                for line in self.web_server.runtime_diagnostics.summary_path(
                    metrics_path
                )
                .read_text(encoding="utf-8")
                .splitlines()
            ]

        phases = [record["phase"] for record in records]
        self.assertEqual(
            phases,
            [
                "start",
                "lock_acquired",
                "inputs_loaded",
                "predictor_render_started",
                "body_rendered",
                "html_generated",
                "response_sent",
                "finish",
            ],
        )
        self.assertEqual(summaries[-1]["operation"], "predictor_request")
        self.assertTrue(summaries[-1]["details"]["cold_request"])
        content = captured["content"].decode("utf-8")
        endpoint_marker = 'new URL("'
        endpoint_reference = content.split(endpoint_marker, 1)[1].split('"', 1)[0]
        self.assertEqual(endpoint_reference, "../diagnostics/predictor-client")
        self.assertEqual(
            urljoin(
                "https://ha.example/api/hassio_ingress/token/mushrooms/predictor?view=week",
                endpoint_reference,
            ),
            "https://ha.example/api/hassio_ingress/token/diagnostics/predictor-client",
        )
        self.assertEqual(
            urljoin("https://rainmapper.example/mushrooms/predictor", endpoint_reference),
            "https://rainmapper.example/diagnostics/predictor-client",
        )
        self.assertIn(records[0]["operation_id"], content)

    def test_diagnostics_download_returns_a_named_zip(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(
            self.web_server.RainmapperHandler
        )
        captured: dict[str, object] = {}
        handler.send_bytes = (
            lambda status, content, content_type, headers=None: captured.update(
                status=status,
                content=content,
                content_type=content_type,
                headers=headers,
            )
        )

        with mock.patch.object(
            self.web_server.runtime_diagnostics,
            "export_bundle",
            return_value=b"zip-payload",
        ) as export_bundle:
            handler.download_runtime_diagnostics()

        self.assertEqual(captured["status"], 200)
        self.assertEqual(captured["content"], b"zip-payload")
        self.assertEqual(captured["content_type"], "application/zip")
        self.assertIn(
            "rainmapper-diagnostics-",
            captured["headers"]["Content-Disposition"],
        )
        export_bundle.assert_called_once_with(
            last_run_log_path=self.web_server.LOG_PATH,
            app_version=self.web_server.app_version(),
        )

    def test_predictor_cache_release_clears_instances_and_weather_data(self) -> None:
        predictor_ui = self.web_server.mushroom_predictor_ui
        predictor_ui._predictor_cache["species-a"] = mock.MagicMock()
        predictor_ui._predictor_cache["species-b"] = mock.MagicMock()

        with (
            mock.patch.object(
                predictor_ui,
                "invalidate_weather_stations_cache",
            ) as invalidate_weather,
            mock.patch.object(predictor_ui.gc, "collect") as collect,
        ):
            released = predictor_ui.release_predictor_cache()

        self.assertEqual(released, 2)
        self.assertEqual(predictor_ui._predictor_cache, {})
        invalidate_weather.assert_called_once_with()
        collect.assert_called_once_with()

    def test_predictor_feature_bars_use_real_model_features_and_labels(self) -> None:
        predictor_ui = self.web_server.mushroom_predictor_ui
        features = {
            "rain_1d_mm": 3.0,
            "rain_7d_mm": 21.0,
            "rain_14d_mm": 42.0,
            "temp_max_7d_c": 24.0,
            "temp_min_7d_c": -2.0,
            "humidity_max_7d_pct": 91.0,
            "humidity_min_7d_pct": 55.0,
            "rain_15d_mm": 999.0,
            "temp_max_c": 999.0,
        }

        with mock.patch.object(
            predictor_ui,
            "_lbl",
            side_effect=lambda key: key,
        ):
            rendered = predictor_ui._render_feature_bars(features)

        self.assertIn("ui.predictor_feature_rain_14d", rendered)
        self.assertIn("ui.predictor_feature_temp_max_7d", rendered)
        self.assertIn("ui.predictor_feature_temp_min_7d", rendered)
        self.assertIn("42.0mm", rendered)
        self.assertIn("24.0°C", rendered)
        self.assertIn('style="width:0%"', rendered)
        self.assertNotIn("999.0", rendered)

    def seed_empty_mushroom_observations(self, data_dir: Path) -> None:
        self.web_server.default_store().ensure_seeded()
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        payload = json.loads(observations_path.read_text(encoding="utf-8"))
        payload["observations"] = []
        observations_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

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

    def test_aemet_source_card_shows_aemet_timing_breakdown(self) -> None:
        html = self.web_server.source_status_card(
            "AEMET",
            {
                "status": "OK",
                "exit_code": 0,
                "duration_seconds": 6,
                "timings": {
                    "fetch_seconds": 1.2,
                    "read_hourly_seconds": 2.4,
                    "build_daily_seconds": 3.6,
                    "write_outputs_seconds": 4.8,
                    "metadata_seconds": 99,
                },
            },
        )

        self.assertIn("fetch 1s", html)
        self.assertIn("read hourly 2s", html)
        self.assertIn("build daily 4s", html)
        self.assertIn("write 5s", html)
        self.assertNotIn("metadata", html)

    def test_run_progress_detects_aemet_step(self) -> None:
        with self.web_server.RUN_LOCK:
            self.web_server.RUN_STATE.update(
                {
                    "current_step": "Running Wunderground",
                    "progress_current": "10",
                    "progress_total": "99",
                    "progress_percent": "10",
                }
            )

        self.web_server.update_run_progress("Start processing AEMET...\n")

        with self.web_server.RUN_LOCK:
            self.assertEqual(self.web_server.RUN_STATE["current_step"], "Running AEMET")
            self.assertEqual(self.web_server.RUN_STATE["progress_current"], "")
            self.assertEqual(self.web_server.RUN_STATE["progress_total"], "")
            self.assertEqual(self.web_server.RUN_STATE["progress_percent"], "")

    def test_last_publish_summary_replaces_older_runs(self) -> None:
        with self.web_server.RUN_LOCK:
            self.web_server.RUN_STATE["last_publish_message"] = "Older scheduled publication."

        self.web_server.record_last_publish(
            "2026-07-20T20:00:00+02:00",
            "Published protected MapLibre data.",
        )

        with self.web_server.RUN_LOCK:
            self.assertEqual(
                self.web_server.RUN_STATE["last_publish_message"],
                "Published protected MapLibre data.",
            )
            self.assertEqual(
                self.web_server.RUN_STATE["last_published_at"],
                "2026-07-20T20:00:00+02:00",
            )

    def test_last_publish_summary_combines_only_the_same_run(self) -> None:
        self.web_server.record_last_publish(
            "2026-07-20T20:00:00+02:00",
            "Published protected MapLibre data.",
            same_run_publish_message="Published legacy maps.",
        )

        with self.web_server.RUN_LOCK:
            self.assertEqual(
                self.web_server.RUN_STATE["last_publish_message"],
                "Published legacy maps. Published protected MapLibre data.",
            )

    def test_non_aemet_source_cards_show_source_specific_timing_breakdowns(self) -> None:
        meteocat_html = self.web_server.source_status_card(
            "Meteocat",
            {
                "status": "OK",
                "exit_code": 0,
                "duration_seconds": 6,
                "timings": {
                    "metadata_seconds": 1.2,
                    "wind_seconds": 2.4,
                    "read_incremental_seconds": 3.6,
                    "write_current_seconds": 4.8,
                    "build_daily_seconds": 99,
                },
            },
        )
        self.assertIn("metadata 1s", meteocat_html)
        self.assertIn("wind 2s", meteocat_html)
        self.assertIn("read incr. 4s", meteocat_html)
        self.assertIn("write current 5s", meteocat_html)
        self.assertNotIn("build daily", meteocat_html)

        meteoclimatic_html = self.web_server.source_status_card(
            "Meteoclimatic",
            {
                "status": "OK",
                "exit_code": 0,
                "duration_seconds": 6,
                "timings": {
                    "fetch_seconds": 1.2,
                    "build_daily_seconds": 2.4,
                    "write_observations_seconds": 3.6,
                },
            },
        )
        self.assertIn("fetch 1s", meteoclimatic_html)
        self.assertIn("build daily 2s", meteoclimatic_html)
        self.assertIn("write obs. 4s", meteoclimatic_html)

        wunderground_html = self.web_server.source_status_card(
            "Wunderground",
            {
                "status": "OK",
                "exit_code": 0,
                "duration_seconds": 6,
                "timings": {
                    "scrape_seconds": 1.2,
                    "normalize_seconds": 2.4,
                    "upsert_incremental_seconds": 3.6,
                },
            },
        )
        self.assertIn("scrape 1s", wunderground_html)
        self.assertIn("normalize 2s", wunderground_html)
        self.assertIn("upsert 4s", wunderground_html)
        self.assertIn("API fallback errors: 0", wunderground_html)

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
        previous_publish = os.environ.get("RAINMAPPER_PUBLISH_TO_WWW")
        previous_version = os.environ.get("RAINMAPPER_APP_VERSION")
        os.environ.pop("RAINMAPPER_PUBLISH_TO_WWW", None)
        os.environ["RAINMAPPER_APP_VERSION"] = "0.2.204"
        try:
            handler.render_index()
        finally:
            if previous_publish is not None:
                os.environ["RAINMAPPER_PUBLISH_TO_WWW"] = previous_publish
            if previous_version is None:
                os.environ.pop("RAINMAPPER_APP_VERSION", None)
            else:
                os.environ["RAINMAPPER_APP_VERSION"] = previous_version

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        for label in ("Summary", "Data sources", "Viewers", "Maps", "Logs", "Errors"):
            self.assertIn(label, page)
        for action in ("Run update", "Generate maps", "Run all", "App settings", "Users", "Mushroom catalogs", "Mushroom species"):
            self.assertIn(action, page)
        for source in ("Meteoclimatic", "Meteocat", "Wunderground", "AEMET"):
            self.assertIn(f'name="source_update" value="{source}"', page)
        self.assertNotIn("Open Leaflet viewer", page)
        self.assertIn("Open MapLibre viewer", page)
        self.assertIn(
            "https://rainmap.nomentero.com/protected/maplibre/index.html?v=0.2.204",
            page,
        )
        self.assertNotIn("https://ha.nomentero.com/protected/maplibre", page)
        self.assertNotIn("Open heatmap experiment", page)
        self.assertIn("Legacy public publishing", page)
        self.assertIn("Disabled", page)
        self.assertNotIn("Open Bokeh 21 days", page)
        self.assertIn("01 Tomap Last day", page)
        self.assertIn("Open full log", page)
        self.assertIn("Disable all", page)
        self.assertIn("Enable all", page)
        self.assertNotIn('http-equiv="refresh"', page)
        self.assertIn('id="rainmapper-control-panel-live"', page)
        self.assertIn("api/control-panel-fragment", page)
        self.assertIn("window.setTimeout(refreshControlPanel,5000)", page)
        self.assertIn("if(livePanel.dataset.controlSignature!==payload.signature)", page)

    def test_control_panel_fragment_endpoint_returns_live_region(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.render_control_panel_body = lambda: '<section data-control-panel="summary">Updated</section>'
        captured: dict[str, object] = {}
        handler.send_json = lambda status, payload: captured.update(status=status, payload=payload)

        handler.serve_control_panel_fragment()

        self.assertEqual(captured["status"], 200)
        self.assertEqual(
            captured["payload"],
            {
                "ok": True,
                "html": '<section data-control-panel="summary">Updated</section>',
                "signature": self.web_server.hashlib.sha256(
                    b'<section data-control-panel="summary">Updated</section>'
                ).hexdigest(),
            },
        )

    def test_diagnostic_record_timestamp_matches_local_summary_format(self) -> None:
        with mock.patch.dict(
            self.web_server.os.environ,
            {"RAINMAPPER_TIMEZONE": "Europe/Madrid"},
        ):
            rendered = self.web_server.diagnostic_record_text(
                {
                    "operation": "runner_action",
                    "status": "ok",
                    "timestamp": "2026-08-08T04:31:46.811Z",
                }
            )

        self.assertEqual(
            rendered,
            "runner_action · ok · 2026-08-08T06:31:46+02:00",
        )

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
        self.assertLess(page.index('href="./profiles"'), page.index("Catálogo maestro de referencia"))
        self.assertIn('class="catalog-toolbar maintenance-top-toolbar"', page)
        self.assertTrue((data_dir / "mushroom-data" / "mushroom_reference_catalogs.json").exists())

    def test_mushroom_gis_mappings_page_renders_toolbar_before_title(self) -> None:
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
        handler.render_mushroom_gis_mappings({})

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        self.assertIn("<h1>GIS mappings</h1>", page)
        self.assertIn('href="./profiles"', page)
        self.assertIn('href="./catalogs"', page)
        self.assertIn('class="catalog-toolbar gis-mapping-toolbar maintenance-top-toolbar"', page)
        self.assertLess(page.index('href="./profiles"'), page.index("<h1>GIS mappings</h1>"))
        self.assertLess(page.index('href="./catalogs"'), page.index("<h1>GIS mappings</h1>"))

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
        handler.render_mushroom_profiles({"id": ["boletus_pinophilus"], "view": ["enriched"]})

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        self.assertIn("Mantenimiento de especies", page)
        self.assertIn("Boletus pinophilus", page)
        self.assertIn("Host Affinities", page)
        self.assertIn("profile-metrics", page)
        self.assertIn('class="profile-metrics profile-metrics-compact"', page)
        self.assertIn("grid-template-columns: repeat(7, minmax(125px, 1fr)) minmax(210px, 1.45fr)", page)
        self.assertIn("max-width: 1500px", page)
        self.assertIn("flex-direction: column", page)
        self.assertIn("min-height: 40px", page)
        self.assertIn("text-align: center", page)
        self.assertIn("profile-tab-labels", page)
        self.assertIn("profile-list-rows", page)
        self.assertIn('data-profile-species-id="boletus_pinophilus"', page)
        self.assertIn('data-profile-refresh-link', page)
        self.assertIn('/api/mushrooms/profile-detail?', page)
        self.assertIn('selectSpeciesProfile(speciesLink)', page)
        self.assertIn('window.history.pushState({ speciesId: payload.species_id }', page)
        self.assertIn("profile-list-chip-legend", page)
        self.assertIn('<span class="profile-chip-label">Priority</span>', page)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, max-content))", page)
        self.assertIn(".profile-editor-polished .profile-editor-head", page)
        self.assertIn("grid-template-columns: minmax(0, 1fr) auto", page)
        self.assertIn(".profile-editor-polished .profile-title-block > div", page)
        self.assertIn(".profile-editor-polished > form", page)
        self.assertIn("padding: 10px 12px", page)
        self.assertIn(".profile-editor-polished .profile-overview-card", page)
        self.assertIn(".profile-editor-polished .profile-status-chip", page)
        self.assertIn("font-size: 11px", page)
        self.assertIn(".parameters-screen > form", page)
        self.assertIn("height: calc(100vh - 150px)", page)
        self.assertIn(".parameters-screen .parameter-tabbed-grid", page)
        self.assertIn('title="Overall confidence:', page)
        self.assertIn('title="Calibration priority:', page)
        self.assertIn('title="Review status:', page)
        self.assertIn('name="profile_return_tab" value="profile-tab-general"', page)
        self.assertIn("Calibration", page)
        self.assertIn("Local calibration status", page)
        self.assertIn("Full profiles JSON import/export", page)
        self.assertIn('href="./catalogs"', page)
        self.assertIn("New species", page)
        self.assertIn('class="catalog-toolbar maintenance-top-toolbar"', page)
        self.assertIn(".maintenance-top-toolbar > .button-link", page)
        self.assertIn("height:32px", page)
        self.assertIn('name="new_species_id"', page)
        self.assertIn('name="score_habitat"', page)
        self.assertIn('step="0.01"', page)
        self.assertIn("Current total", page)
        self.assertIn("Summary", page)
        self.assertIn("Species", page)
        self.assertIn("Observations", page)
        self.assertTrue((data_dir / "mushroom-data" / "mushroom_profiles.json").exists())

    def test_shared_species_header_shows_all_common_names_without_species_id(self) -> None:
        header = self.web_server.mushroom_profiles_ui.render_selected_species_header(
            {
                "species_id": "amanita_caesarea",
                "scientific_name": "Amanita caesarea",
                "common_names": {
                    "ca": ["Ou de reig"],
                    "es": ["Oronja", "Amanita de los césares"],
                },
            },
            "Calibración",
        )

        self.assertIn("Ou de reig, Oronja, Amanita de los césares", header)
        self.assertNotIn("species_id:", header)
        self.assertNotIn("amanita_caesarea", header)

    def test_mushroom_profile_detail_endpoint_returns_editor_and_current_navigation(self) -> None:
        store = mock.Mock()
        store.load.side_effect = lambda name: {
            "profiles": {
                "species_profiles": [
                    {
                        "species_id": "boletus_pinophilus",
                        "scientific_name": "Boletus pinophilus",
                        "common_names": {"es": ["Pinícola", "Boleto de pino"], "ca": ["Cep de pi"]},
                    },
                    {
                        "species_id": "boletus_aereus",
                        "scientific_name": "Boletus aereus",
                    },
                ]
            },
            "catalogs": {"catalogs": {}},
        }[name]
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured: dict[str, object] = {}
        handler.send_json = lambda status, payload: captured.update(status=status, payload=payload)

        with mock.patch.object(self.web_server, "default_store", return_value=store):
            handler.serve_mushroom_profile_detail(
                {"id": ["boletus_pinophilus"], "view": ["v0"], "q": ["boletus"]}
            )

        self.assertEqual(captured["status"], 200)
        payload = captured["payload"]
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["species_id"], "boletus_pinophilus")
        self.assertIn("Boletus pinophilus", payload["editor_html"])
        self.assertNotIn("Boletus aereus", payload["editor_html"])
        editor_header = payload["editor_html"].split("<form method=", 1)[0]
        self.assertIn("Pinícola, Boleto de pino, Cep de pi", editor_header)
        self.assertNotIn(" · boletus_pinophilus", editor_header)
        self.assertIn("id=boletus_pinophilus", payload["section_tabs_html"])
        self.assertIn("id=boletus_pinophilus", payload["view_switch_html"])
        self.assertIn("id=boletus_pinophilus", payload["refresh_url"])
        self.assertEqual([mock.call("profiles"), mock.call("catalogs")], store.load.call_args_list)

    def test_mushroom_known_site_detail_endpoint_returns_only_selected_panels(self) -> None:
        known_sites = {
            "areas": [
                {
                    "area_id": "bergueda",
                    "name": "Berguedà",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[1.8, 42.0], [1.9, 42.0], [1.8, 42.1], [1.8, 42.0]]],
                    },
                }
            ],
            "micro_areas": [
                {
                    "micro_area_id": "bergueda_obaga",
                    "area_id": "bergueda",
                    "name": "Obaga del Berguedà",
                },
                {
                    "micro_area_id": "bergueda_solans",
                    "area_id": "bergueda",
                    "name": "Solans",
                },
            ],
        }
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured: dict[str, object] = {}
        handler.send_json = lambda status, payload: captured.update(status=status, payload=payload)

        with mock.patch.object(self.web_server.mushroom_known_sites, "load_payload", return_value=known_sites):
            handler.serve_mushroom_known_site_detail(
                {
                    "kind": ["micro_area"],
                    "id": ["bergueda_obaga"],
                    "q": ["bergueda"],
                    "return_to": ["./profiles?section=observations"],
                }
            )

        self.assertEqual(captured["status"], 200)
        payload = captured["payload"]
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["selected_id"], "bergueda_obaga")
        self.assertIn("Obaga del Berguedà", payload["editor_html"])
        self.assertNotIn("Solans", payload["editor_html"])
        self.assertIn('class="known-site-selection-data"', payload["map_html"])
        self.assertIn('"parent_geometry":', payload["map_html"])
        self.assertIn("kind=micro_area", payload["refresh_url"])
        self.assertIn("id=bergueda_obaga", payload["refresh_url"])

    def test_known_sites_page_selects_rows_without_full_navigation(self) -> None:
        known_sites = {
            "areas": [{"area_id": "bergueda", "name": "Berguedà"}],
            "micro_areas": [
                {
                    "micro_area_id": "bergueda_obaga",
                    "area_id": "bergueda",
                    "name": "Obaga del Berguedà",
                }
            ],
        }

        page = self.web_server.mushroom_known_sites_ui.render_page(
            known_sites,
            {"observations": []},
            {"kind": ["micro_area"], "id": ["bergueda_obaga"], "q": ["bergueda"]},
            catalogs_payload={"catalogs": {}},
        )

        self.assertIn('data-known-site-select data-known-site-kind="area"', page)
        self.assertIn('data-known-site-select data-known-site-kind="micro_area"', page)
        self.assertIn('data-known-site-id="bergueda_obaga" aria-current="true"', page)
        self.assertIn('data-known-sites-refresh-link', page)
        self.assertIn('class="catalog-toolbar sites-top-toolbar maintenance-top-toolbar"', page)
        self.assertIn('class="known-site-selection-data"', page)
        self.assertIn('/api/mushrooms/known-site-detail', page)
        self.assertIn("loadSelection(href", page)
        self.assertIn("history.pushState", page)
        self.assertIn("cleanupSelection()", page)
        self.assertIn("mapOptions.bounds=initialBounds", page)
        self.assertIn("duration:0", page)
        self.assertNotIn("center:[1.9,42.05]", page)

    def test_outdated_model_notice_opens_workers_without_starting_rebuild(self) -> None:
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
        captured: dict[str, object] = {}
        handler.send_bytes = lambda status, content, content_type: captured.update(
            status=status,
            content=content.decode("utf-8"),
            content_type=content_type,
        )

        with mock.patch.object(
            self.web_server,
            "pending_model_species_ids",
            return_value=["boletus_pinophilus"],
        ):
            handler.render_mushroom_profiles({"id": ["boletus_pinophilus"]})

        page = str(captured["content"])
        self.assertEqual(captured["status"], 200)
        self.assertIn('./workers?scope=pending&amp;source=outdated', page)
        self.assertNotIn('name="profile_action" value="rebuild_pending_model_v0"', page)

    def test_mushroom_profiles_defaults_to_v0_view(self) -> None:
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
        handler.render_mushroom_profiles({"section": ["observations"]})

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        self.assertIn("Observation records", page)
        self.assertIn('class="button-link active"', page)
        self.assertIn('section=observations&amp;view=v0', page)
        self.assertIn('section=observations&amp;view=enriched', page)
        self.assertIn('name="view" value="v0"', page)

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
        handler.render_mushroom_profiles({"id": ["morchella_elata_complex"], "view": ["v0"]})

        self.assertEqual(captured["status"], 200)
        page = captured["content"]
        self.assertIn("Morchella elata complex", page)
        self.assertIn('name="view" value="v0"', page)
        self.assertIn("Aparcado para v0", page)
        self.assertIn("feature_disturbed_soil", page)
        self.assertNotIn("soil_humus_rich", page)
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
            handler.render_mushroom_profiles({"id": ["boletus_pinophilus"], "section": [section], "view": ["enriched"]})

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

        self.assertEqual("?id=boletus_pinophilus&section=species&view=enriched#profile-tab-phenology", ok_redirect)
        self.assertEqual(
            "?id=boletus_pinophilus&section=species&view=enriched&profile_tab=profile-tab-phenology#mushroom-profile-message",
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
        self.seed_empty_mushroom_observations(data_dir)

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        self.assertEqual(
            "?kind=area&id=olvan",
            handler.handle_mushroom_known_sites_post(
                {
                    "known_site_action": ["create_area"],
                    "name": ["Olvan"],
                    "save_confirmation": ["1"],
                }
            ),
        )
        self.assertEqual(
            "?kind=micro_area&id=olvan_la_pera",
            handler.handle_mushroom_known_sites_post(
                {
                    "known_site_action": ["create_micro_area"],
                    "area_id": ["olvan"],
                    "name": ["La Pera"],
                    "save_confirmation": ["1"],
                }
            ),
        )
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_pinophilus"],
                "micro_area_id": ["olvan_la_pera"],
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
                "observed_forest_type_ids": ["forest_montane_pine"],
                "observed_soil_tendency_ids": ["soil_siliceous"],
                "observed_habitat_feature_ids": ["feature_mature_forest"],
                "observed_aspect_ids": ["aspect_N"],
                "habitat_notes": ["oak woodland"],
            }
        )

        self.assertEqual("?section=observations&id=boletus_pinophilus&obs_id=obs_20260629_0001#observations-workspace", redirect)
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        payload = json.loads(observations_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload["observations"]))
        observation = payload["observations"][0]
        self.assertEqual("boletus_pinophilus", observation["species_id"])
        self.assertEqual("olvan_la_pera", observation["micro_area_id"])
        self.assertEqual("abundant", observation["flush_abundance"])
        self.assertEqual("google_maps_url", observation["location"]["source"])
        self.assertAlmostEqual(41.3874, observation["location"]["lat"])
        self.assertAlmostEqual(2.1686, observation["location"]["lon"])
        self.assertEqual(120, observation["altitude"]["meters"])
        self.assertEqual({"month": 6, "season": "summer"}, observation["derived"])
        self.assertEqual(["forest_montane_pine"], observation["site_context"]["observed_forest_type_ids"])
        self.assertEqual(["soil_siliceous"], observation["site_context"]["observed_soil_tendency_ids"])
        self.assertEqual(["feature_mature_forest"], observation["site_context"]["observed_habitat_feature_ids"])
        self.assertEqual(["aspect_N"], observation["site_context"]["observed_aspect_ids"])
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
        self.seed_empty_mushroom_observations(data_dir)

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
                "observed_forest_type_ids": ["forest_holm_oak"],
                "observed_soil_tendency_ids": ["soil_calcareous"],
                "observed_habitat_feature_ids": ["feature_open_warm_woodland"],
                "observed_aspect_ids": ["aspect_S"],
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
        self.assertEqual({"month": 6, "season": "summer"}, observation["derived"])
        self.assertEqual(["forest_holm_oak"], observation["site_context"]["observed_forest_type_ids"])
        self.assertEqual(["soil_calcareous"], observation["site_context"]["observed_soil_tendency_ids"])
        self.assertEqual(["feature_open_warm_woodland"], observation["site_context"]["observed_habitat_feature_ids"])
        self.assertEqual(["aspect_S"], observation["site_context"]["observed_aspect_ids"])

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
        self.seed_empty_mushroom_observations(data_dir)

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

    def test_mushroom_observations_photo_exif_source_does_not_imply_location_source(self) -> None:
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
        self.seed_empty_mushroom_observations(data_dir)

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        redirect = handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["amanita_caesarea"],
                "observed_at": ["2025-09-30"],
                "location_lat": ["41.99709444"],
                "location_lon": ["1.93571944"],
                "altitude_m": ["596.8"],
                "altitude_source": ["photo_exif"],
                "flush_abundance": ["abundant"],
                "source_quality": ["1"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "observer_expertise": ["experienced"],
                "source_type": ["photo_exif"],
                "source_label": ["IMG_4802.jpeg"],
            }
        )

        self.assertEqual("?section=observations&id=amanita_caesarea&obs_id=obs_20250930_0001#observations-workspace", redirect)
        payload = json.loads((data_dir / "mushroom-data" / "mushroom_observations.json").read_text(encoding="utf-8"))
        observation = payload["observations"][0]
        self.assertEqual("photo_exif", observation["source"]["type"])
        self.assertEqual("manual_decimal", observation["location"]["source"])
        self.assertEqual("photo_exif", observation["altitude"]["source"])

    def test_mushroom_observations_explicit_location_source_is_preserved(self) -> None:
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
        self.seed_empty_mushroom_observations(data_dir)

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["amanita_caesarea"],
                "observed_at": ["2025-09-30"],
                "location_lat": ["41.99709444"],
                "location_lon": ["1.93571944"],
                "location_source": ["photo_exif"],
                "altitude_m": ["596.8"],
                "altitude_source": ["photo_exif"],
                "flush_abundance": ["abundant"],
                "source_quality": ["1"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "observer_expertise": ["experienced"],
                "source_type": ["photo_exif"],
                "source_label": ["IMG_4802.jpeg"],
            }
        )

        payload = json.loads((data_dir / "mushroom-data" / "mushroom_observations.json").read_text(encoding="utf-8"))
        observation = payload["observations"][0]
        self.assertEqual("photo_exif", observation["source"]["type"])
        self.assertEqual("photo_exif", observation["location"]["source"])
        self.assertEqual("photo_exif", observation["altitude"]["source"])

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
        self.seed_empty_mushroom_observations(data_dir)

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
        self.seed_empty_mushroom_observations(data_dir)

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
                "calibration_exclusion_reason": ["other"],
                "observer_name": ["Carlos"],
                "observer_expertise": ["experienced"],
                "source_notes": ["Shared batch source note"],
                "observed_host_ids": ["host_pinus_sylvestris"],
                "observed_forest_type_ids": ["forest_holm_oak"],
                "observed_soil_tendency_ids": ["soil_calcareous"],
                "observed_habitat_feature_ids": ["feature_open_warm_woodland"],
                "observed_aspect_ids": ["aspect_S"],
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
        self.assertEqual("Shared batch source note", observation["source"]["notes"])
        self.assertEqual("Carlos", observation["observer"]["name"])
        self.assertEqual("experienced", observation["observer"]["expertise"])
        self.assertEqual("other", observation["calibration_exclusion_reason"])
        self.assertEqual(["host_pinus_sylvestris"], observation["site_context"]["observed_host_ids"])
        self.assertEqual(["forest_holm_oak"], observation["site_context"]["observed_forest_type_ids"])
        self.assertEqual(["soil_calcareous"], observation["site_context"]["observed_soil_tendency_ids"])
        self.assertEqual(
            ["feature_open_warm_woodland"], observation["site_context"]["observed_habitat_feature_ids"]
        )
        self.assertEqual(["aspect_S"], observation["site_context"]["observed_aspect_ids"])
        self.assertEqual(1, len(observation["media"]))
        media = observation["media"][0]
        self.assertEqual("photo", media["kind"])
        self.assertEqual("IMG_4144.jpeg", media["original_filename"])
        self.assertEqual("media/observation-photos/2025/IMG_4144.jpeg", media["path"])
        self.assertIn("./observation-media?path=", media["url"])
        self.assertEqual("display", media["variant"])
        self.assertTrue((data_dir / "mushroom-data" / media["path"]).exists())
        self.assertEqual({"month": 8, "season": "summer"}, observation["derived"])

    def test_mushroom_observation_exif_preview_reports_photo_position(self) -> None:
        original_extractor = self.web_server.extract_photo_exif_observation_fields

        def restore_extractor() -> None:
            self.web_server.extract_photo_exif_observation_fields = original_extractor

        self.addCleanup(restore_extractor)

        def fake_extractor(filename: str, content: bytes) -> dict[str, object]:
            if filename == "bad.jpeg":
                raise ValueError("image has no GPS metadata")
            return {
                "filename": filename,
                "observed_at": "2025-09-30",
                "captured_at": "2025-09-30 10:42:00",
                "captured_at_display": "30/09/2025 10:42",
                "lat": 41.99709444444444,
                "lon": 1.9357194444444445,
                "altitude_m": 597.2,
            }

        self.web_server.extract_photo_exif_observation_fields = fake_extractor

        payload = self.web_server.preview_photo_exif_uploads(
            {
                "observation_exif_images": [
                    {"filename": "IMG_4802.jpeg", "content": b"jpeg", "content_type": "image/jpeg"},
                    {"filename": "bad.jpeg", "content": b"jpeg", "content_type": "image/jpeg"},
                ]
            }
        )

        self.assertEqual(2, len(payload["previews"]))
        ok_preview = payload["previews"][0]
        self.assertTrue(ok_preview["ok"])
        self.assertEqual("IMG_4802.jpeg", ok_preview["filename"])
        self.assertEqual("2025-09-30", ok_preview["observed_at"])
        self.assertEqual("2025-09-30 10:42:00", ok_preview["captured_at"])
        self.assertEqual("30/09/2025 10:42", ok_preview["captured_at_display"])
        self.assertEqual(41.99709444444444, ok_preview["lat"])
        self.assertEqual(1.9357194444444445, ok_preview["lon"])
        self.assertEqual(597.2, ok_preview["altitude_m"])
        self.assertIn("maps.google.com/maps?", ok_preview["map_src"])
        self.assertFalse(payload["previews"][1]["ok"])
        self.assertEqual("image has no GPS metadata", payload["previews"][1]["error"])

    def test_video_metadata_uses_quicktime_date_gps_and_altitude(self) -> None:
        exiftool_payload = [
            {
                "CreationDate": "2025:09:26 14:38:00+02:00",
                "CreateDate": "2026:07:13 22:35:31+00:00",
                "GPSLatitude": 42.0232,
                "GPSLongitude": 1.9763,
                "GPSAltitude": 713.5,
                "Duration": 28.4,
            }
        ]
        completed = mock.Mock(stdout=json.dumps(exiftool_payload), stderr="", returncode=0)
        with mock.patch.object(self.web_server.subprocess, "run", return_value=completed) as run:
            fields = self.web_server.extract_photo_exif_observation_fields("IMG_4751.mov", b"quicktime-video")

        self.assertEqual("video", fields["media_kind"])
        self.assertEqual("2025-09-26", fields["observed_at"])
        self.assertEqual(42.0232, fields["lat"])
        self.assertEqual(1.9763, fields["lon"])
        self.assertEqual(713.5, fields["altitude_m"])
        self.assertEqual(28.4, fields["duration_seconds"])
        self.assertEqual("exiftool", run.call_args.args[0][0])

    def test_media_preview_proposes_dem_altitude_when_metadata_has_none(self) -> None:
        fields = {
            "filename": "IMG_4751.mov",
            "media_kind": "video",
            "observed_at": "2025-09-26",
            "captured_at": "2025-09-26 14:38:00+02:00",
            "lat": 42.0232,
            "lon": 1.9763,
            "altitude_m": None,
        }
        with mock.patch.object(
            self.web_server.mushroom_gis_lab,
            "sample_dem",
            return_value={"status": "ok", "elevation_m": 625.76},
        ) as sample_dem:
            enriched = self.web_server.enrich_media_fields_with_dem_altitude(fields)

        self.assertEqual(625.8, enriched["altitude_m"])
        self.assertEqual("dem", enriched["altitude_source"])
        sample_dem.assert_called_once_with(1.9763, 42.0232, None)

    def test_video_media_is_transcoded_to_bounded_mp4(self) -> None:
        data_dir = Path(self.temp_dir.name) / "mushroom-data"
        old_data = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR")
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir)

        def restore_env() -> None:
            if old_data is None:
                os.environ.pop("RAINMAPPER_MUSHROOM_DATA_DIR", None)
            else:
                os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = old_data

        self.addCleanup(restore_env)
        commands: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs: object) -> mock.Mock:
            commands.append(command)
            if command[0] == "exiftool":
                return mock.Mock(
                    stdout=json.dumps(
                        [{
                            "CreateDate": "2025:09:26 14:38:00",
                            "GPSLatitude": 42.0232,
                            "GPSLongitude": 1.9763,
                            "GPSAltitude": 713.5,
                            "Duration": 82.0,
                        }]
                    ),
                    stderr="",
                    returncode=0,
                )
            Path(command[-1]).write_bytes(b"small-standard-mp4")
            return mock.Mock(stdout="", stderr="", returncode=0)

        with mock.patch.object(self.web_server.subprocess, "run", side_effect=fake_run):
            media = self.web_server.save_observation_image_media(
                "obs_20250926_0001",
                {"filename": "IMG_4751.mov", "content": b"source-video", "content_type": "video/quicktime"},
                "2025-09-26",
            )

        self.assertIsNotNone(media)
        self.assertEqual("video", media["kind"])
        self.assertEqual("video/mp4", media["content_type"])
        self.assertEqual("IMG_4751.mp4", media["stored_filename"])
        self.assertEqual("media/observation-videos/2025/IMG_4751.mp4", media["path"])
        self.assertEqual(30, media["max_duration_seconds"])
        self.assertEqual("854x480", media["max_resolution"])
        self.assertEqual(42.0232, media["capture_metadata"]["lat"])
        ffmpeg_command = next(command for command in commands if command[0] == "ffmpeg")
        self.assertIn("30", ffmpeg_command)
        self.assertIn("libx264", ffmpeg_command)
        self.assertIn("yuv420p", ffmpeg_command)
        self.assertIn("location=+42.023200+1.976300+713.50/", ffmpeg_command)
        self.assertTrue((data_dir / media["path"]).exists())

    def test_video_media_renders_with_generated_poster(self) -> None:
        row = {
            "observation_id": "obs_20250926_0001",
            "media": [{
                "kind": "video",
                "url": "./observation-media?path=video.mp4",
                "path": "media/observation-videos/2025/video.mp4",
                "original_filename": "IMG_4751.mov",
            }],
        }
        html = self.web_server.mushroom_profiles_ui.render_observation_photo_strip(row)
        self.assertIn("<img", html)
        self.assertIn("poster=1", html)
        self.assertNotIn("<video", html)

    def test_observation_media_http_ranges_support_safari_streaming(self) -> None:
        self.assertEqual((0, 1023), self.web_server.parse_http_byte_range("bytes=0-1023", 4096))
        self.assertEqual((2048, 4095), self.web_server.parse_http_byte_range("bytes=2048-", 4096))
        self.assertEqual((3996, 4095), self.web_server.parse_http_byte_range("bytes=-100", 4096))
        self.assertEqual((4000, 4095), self.web_server.parse_http_byte_range("bytes=4000-9999", 4096))
        with self.assertRaises(ValueError):
            self.web_server.parse_http_byte_range("bytes=4096-", 4096)
        with self.assertRaises(ValueError):
            self.web_server.parse_http_byte_range("bytes=0-1,4-5", 4096)

    def test_video_viewer_declares_mp4_source_and_poster(self) -> None:
        row = {"observation_id": "obs_20250926_0001"}
        media = {
            "kind": "video",
            "url": "./observation-media?path=video.mp4",
            "path": "media/observation-videos/2025/video.mp4",
            "content_type": "video/mp4",
            "original_filename": "IMG_4751.mov",
        }
        html = self.web_server.mushroom_profiles_ui.render_observation_photo_modal(row, media, 0)
        self.assertIn("<video controls", html)
        self.assertIn("poster=1", html)
        self.assertIn('<source src="./observation-media?path=video.mp4" type="video/mp4">', html)
        self.assertNotIn("observation-media-viewer", html)

    def test_photo_viewer_opens_large_view_in_new_tab(self) -> None:
        row = {"observation_id": "obs_20250926_0001"}
        media = {
            "kind": "photo",
            "url": "./observation-media?path=photo.jpeg",
            "path": "media/observation-photos/2025/photo.jpeg",
            "original_filename": "photo.jpeg",
        }
        html = self.web_server.mushroom_profiles_ui.render_observation_photo_modal(row, media, 0)

        self.assertIn("./observation-media-viewer?path=media%2Fobservation-photos%2F2025%2Fphoto.jpeg", html)
        self.assertIn('target="_blank" rel="noopener"', html)
        self.assertIn(self.web_server.mushroom_profiles_ui.ui_label("ui.open_large"), html)
        self.assertIn("data-observation-photo-fullscreen", html)
        self.assertIn(self.web_server.mushroom_profiles_ui.ui_label("ui.fullscreen"), html)
        self.assertIn('class="observation-photo-stage-actions"', html)
        self.assertIn('<svg aria-hidden="true" viewBox="0 0 24 24">', html)
        self.assertNotIn(">Pantalla completa</button>", html)

        viewer = self.web_server.observation_media_viewer_page(media["path"], "photo.jpeg").decode("utf-8")
        self.assertIn('data-zoom-out', viewer)
        self.assertIn('data-zoom-in', viewer)
        self.assertIn('data-actual-size', viewer)
        self.assertIn('data-fit-window', viewer)
        self.assertIn('data-fullscreen', viewer)
        self.assertIn("applyScale(scale * 1.25, true)", viewer)
        self.assertIn("./observation-media?path=media%2Fobservation-photos%2F2025%2Fphoto.jpeg", viewer)
        page = self.web_server.html_page("Viewer", html, auto_refresh=False).decode("utf-8")
        self.assertIn("stage.requestFullscreen || stage.webkitRequestFullscreen", page)
        self.assertIn('window.open(fallbackUrl, "_blank", "noopener")', page)

    def test_mushroom_observations_update_rejects_multiple_exif_images(self) -> None:
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
        self.seed_empty_mushroom_observations(data_dir)

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

        self.assertEqual("?section=observations&id=boletus_aereus&obs_id=obs_20260629_0001#observations-workspace", redirect)
        payload = json.loads(observations_path.read_text(encoding="utf-8"))
        self.assertEqual(1, len(payload["observations"]))
        unchanged = payload["observations"][0]
        self.assertEqual(observation_id, unchanged["observation_id"])
        self.assertEqual("boletus_aereus", unchanged["species_id"])
        self.assertNotIn("media", unchanged)

    def test_mushroom_observation_load_image_does_not_apply_exif(self) -> None:
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
        self.seed_empty_mushroom_observations(data_dir)
        self.web_server.extract_photo_exif_observation_fields = mock.Mock(
            side_effect=AssertionError("image-only import must not read EXIF")
        )

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["create_observation"],
                "observation_species_id": ["boletus_aereus"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.0"],
                "location_lon": ["2.0"],
                "altitude_m": ["500"],
                "altitude_source": ["manual"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "source_type": ["personal_observation"],
                "source_label": ["field notes"],
            }
        )
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        observation_id = json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0][
            "observation_id"
        ]

        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["update_observation"],
                "observation_id": [observation_id],
                "observation_species_id": ["boletus_aereus"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.0"],
                "location_lon": ["2.0"],
                "altitude_m": ["500"],
                "altitude_source": ["manual"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "source_type": ["personal_observation"],
                "source_label": ["field notes"],
                "observation_image_import_mode": ["image_only"],
                "media_replacement_action": ["keep"],
            },
            files={"observation_exif_images": [{"filename": "IMG_3043.jpeg", "content": b"fake-jpeg"}]},
        )

        observation = json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0]
        self.assertEqual("2026-06-29", observation["observed_at"])
        self.assertEqual("41.0, 2.0", observation["location"]["input"])
        self.assertEqual(41.0, observation["location"]["lat"])
        self.assertEqual(2.0, observation["location"]["lon"])
        self.assertEqual("manual_decimal", observation["location"]["source"])
        self.assertEqual(500, observation["altitude"]["meters"])
        self.assertEqual("manual", observation["altitude"]["source"])
        self.assertEqual("personal_observation", observation["source"]["type"])
        self.assertEqual("field notes", observation["source"]["label"])
        self.assertEqual("IMG_3043.jpeg", observation["media"][0]["original_filename"])
        self.web_server.extract_photo_exif_observation_fields.assert_not_called()

    def test_mushroom_observation_load_exif_does_not_attach_image(self) -> None:
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
        self.seed_empty_mushroom_observations(data_dir)

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
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "source_type": ["personal_observation"],
            }
        )
        observations_path = data_dir / "mushroom-data" / "mushroom_observations.json"
        observation_id = json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0][
            "observation_id"
        ]
        self.web_server.extract_photo_exif_observation_fields = mock.Mock(
            return_value={
                "filename": "IMG_3043.jpeg",
                "observed_at": "2025-04-01",
                "lat": 42.369172,
                "lon": 1.321158,
                "altitude_m": 1384.0,
            }
        )

        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["update_observation"],
                "observation_id": [observation_id],
                "observation_species_id": ["boletus_aereus"],
                "observed_at": ["2026-06-29"],
                "location_lat": ["41.0"],
                "location_lon": ["2.0"],
                "flush_abundance": ["normal"],
                "source_quality": ["0.7"],
                "validation_status": ["valid"],
                "calibration_use": ["include"],
                "source_type": ["personal_observation"],
                "observation_image_import_mode": ["exif_only"],
            },
            files={"observation_exif_images": [{"filename": "IMG_3043.jpeg", "content": b"fake-jpeg"}]},
        )

        observation = json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0]
        self.assertEqual("2025-04-01", observation["observed_at"])
        self.assertEqual(42.369172, observation["location"]["lat"])
        self.assertEqual(1.321158, observation["location"]["lon"])
        self.assertEqual("photo_exif", observation["location"]["source"])
        self.assertEqual(1384.0, observation["altitude"]["meters"])
        self.assertEqual("photo_exif", observation["altitude"]["source"])
        self.assertEqual("photo_exif", observation["source"]["type"])
        self.assertEqual("IMG_3043.jpeg", observation["source"]["label"])
        self.assertNotIn("media", observation)

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
        self.seed_empty_mushroom_observations(data_dir)

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
        self.seed_empty_mushroom_observations(data_dir)

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
        observations_payload = json.loads(observations_path.read_text(encoding="utf-8"))
        observation_id = observations_payload["observations"][0]["observation_id"]
        media_relative_path = "media/observation-photos/2026/archive-delete-test.jpg"
        media_path = data_dir / "mushroom-data" / media_relative_path
        media_path.parent.mkdir(parents=True, exist_ok=True)
        media_path.write_bytes(b"test-photo")
        observations_payload["observations"][0]["media"] = [
            {"kind": "photo", "path": media_relative_path, "stored_filename": media_path.name}
        ]
        self.web_server.write_json_atomic(observations_path, observations_payload)

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
        self.assertTrue(media_path.exists(), "archiving must retain observation media")

        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["restore_observation"],
                "species_id": ["boletus_pinophilus"],
                "observation_id": [observation_id],
            }
        )
        self.assertEqual(observation_id, json.loads(observations_path.read_text(encoding="utf-8"))["observations"][0]["observation_id"])
        self.assertEqual([], json.loads(archived_path.read_text(encoding="utf-8"))["observations"])
        self.assertTrue(media_path.exists(), "restoring must retain observation media")

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
        self.assertTrue(media_path.exists(), "failed confirmation must retain observation media")
        handler.handle_mushroom_profiles_post(
            {
                "profile_action": ["delete_archived_observation"],
                "species_id": ["boletus_pinophilus"],
                "observation_id": [observation_id],
                "delete_confirm_id": [observation_id],
            }
        )
        self.assertEqual([], json.loads(archived_path.read_text(encoding="utf-8"))["observations"])
        self.assertFalse(media_path.exists(), "permanent deletion must remove unreferenced media")
        cleanup_queue = json.loads(
            self.web_server.observation_media_cleanup_queue_path(self.web_server.default_store()).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual([], cleanup_queue["jobs"])

    def test_observation_media_cleanup_retries_after_unlink_failure(self) -> None:
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
        self.seed_empty_mushroom_observations(data_dir)
        store = self.web_server.default_store()
        media_relative_path = "media/observation-photos/2026/retry-delete-test.jpg"
        media_path = data_dir / "mushroom-data" / media_relative_path
        media_path.parent.mkdir(parents=True, exist_ok=True)
        media_path.write_bytes(b"test-photo")
        self.web_server.queue_observation_media_cleanup(store, "obs_retry", {media_relative_path})

        with mock.patch.object(Path, "unlink", side_effect=PermissionError("read-only share")):
            deleted, errors = self.web_server.process_observation_media_cleanup_queue(store)

        self.assertEqual([], deleted)
        self.assertEqual(1, len(errors))
        self.assertTrue(media_path.exists())
        queue_payload = self.web_server.load_observation_media_cleanup_queue(store)
        self.assertEqual([media_relative_path], queue_payload["jobs"][0]["paths"])

        deleted, errors = self.web_server.process_observation_media_cleanup_queue(store)
        self.assertEqual([media_path.name], deleted)
        self.assertEqual([], errors)
        self.assertFalse(media_path.exists())
        self.assertEqual([], self.web_server.load_observation_media_cleanup_queue(store)["jobs"])

        shared_relative_path = "media/observation-photos/2026/shared-delete-test.jpg"
        shared_path = data_dir / "mushroom-data" / shared_relative_path
        shared_path.write_bytes(b"shared-photo")
        observations_payload = store.load("observations")
        observations_payload["observations"] = [
            {
                "observation_id": "obs_still_references_media",
                "media": [{"kind": "photo", "path": shared_relative_path}],
            }
        ]
        self.web_server.write_json_atomic(store.persistent_path("observations"), observations_payload)
        self.web_server.queue_observation_media_cleanup(store, "obs_deleted", {shared_relative_path})

        deleted, errors = self.web_server.process_observation_media_cleanup_queue(store)
        self.assertEqual([], deleted)
        self.assertEqual([], errors)
        self.assertTrue(shared_path.exists(), "referenced media must never be deleted")
        self.assertEqual([], self.web_server.load_observation_media_cleanup_queue(store)["jobs"])

    def test_archive_transaction_rolls_back_archive_when_active_replace_fails(self) -> None:
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
        self.seed_empty_mushroom_observations(data_dir)
        store = self.web_server.default_store()
        previous_active = store.load("observations")
        previous_archived = self.web_server.empty_archived_observations_payload()
        next_archived = json.loads(json.dumps(previous_archived))
        next_archived["observations"] = [{"observation_id": "obs_transaction"}]

        with mock.patch.object(store, "replace", return_value=mock.Mock(ok=False)):
            result = self.web_server.replace_observation_archive_transaction(
                store,
                previous_active=previous_active,
                next_active=previous_active,
                previous_archived=previous_archived,
                next_archived=next_archived,
                archive_first=True,
            )

        self.assertFalse(result.ok)
        archived = self.web_server.load_archived_observations(store)
        self.assertEqual([], archived["observations"])

        next_active = json.loads(json.dumps(previous_active))
        next_active["observations"] = [{"observation_id": "obs_restore_transaction"}]

        def write_active(_kind: str, payload: dict[str, object]) -> object:
            self.web_server.write_json_atomic(store.persistent_path("observations"), payload)
            return mock.Mock(ok=True)

        with (
            mock.patch.object(store, "replace", side_effect=write_active),
            mock.patch.object(
                self.web_server,
                "write_archived_observations",
                side_effect=OSError("archive share write failed"),
            ),
            self.assertRaises(OSError),
        ):
            self.web_server.replace_observation_archive_transaction(
                store,
                previous_active=previous_active,
                next_active=next_active,
                previous_archived=previous_archived,
                next_archived=previous_archived,
                archive_first=False,
            )

        self.assertEqual(previous_active, store.load("observations"))

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
        self.assertIn('class="parameter-affinity-badge primary">Principal</span>', html)
        self.assertIn('class="parameter-affinity-badge source">Marc</span>', html)
        self.assertNotIn('class="parameter-affinity-badge catalog">Catalogo</span>', html)

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
                    "media": [
                        {
                            "kind": "photo",
                            "path": "media/observation-photos/2026/IMG_0001.jpeg",
                            "url": "./observation-media?path=media%2Fobservation-photos%2F2026%2FIMG_0001.jpeg",
                            "stored_filename": "IMG_0001.jpeg",
                            "original_filename": "IMG_0001.jpeg",
                            "content_type": "image/jpeg",
                            "size_bytes": 123456,
                        }
                    ],
                    "site_context": {
                        "observed_host_ids": ["host_pinus_sylvestris"],
                        "habitat_notes": "Barranco umbrío muy concreto",
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
        detail_html = self.web_server.mushroom_profiles_ui.render_observation_detail(
            observations["observations"],
            catalogs,
            {"boletus_pinophilus": "Boletus pinophilus"},
            selected_observation_id="obs_20260629_0001",
        )

        filters_html = html[html.index('<form class="observations-filters"') : html.index('<div class="observations-layout">')]
        self.assertIn('name="page" value="1"', filters_html)
        self.assertIn('name="obs_q" type="search"', filters_html)
        self.assertIn('data-observation-search autocomplete="off"', filters_html)
        self.assertIn('name="date_from" type="hidden" value="2026-06-29" data-observation-date-value', filters_html)
        self.assertIn('name="date_to" type="hidden" value="" data-observation-date-value', filters_html)
        self.assertIn('class="observation-date-display" type="text" value="29/06/2026"', filters_html)
        self.assertEqual(filters_html.count('data-observation-date-picker'), 2)
        self.assertNotIn("readonly", filters_html)
        self.assertNotIn("disabled", filters_html)
        self.assertIn("sort=observed_at", html)
        self.assertIn("sort=abundance", html)
        self.assertIn("import-observation-exif", html)
        self.assertIn('name="exif_images"', html)
        batch_start = html.index('<div id="import-observation-exif"')
        batch_end = html.index("</form>", batch_start)
        batch_html = html[batch_start:batch_end]
        self.assertIn("observation-form observation-batch-import", batch_html)
        self.assertIn('name="calibration_exclusion_reason"', batch_html)
        self.assertIn('name="source_notes"', batch_html)
        self.assertIn('class="observation-evidence-panel"', batch_html)
        self.assertIn('class="observation-form-footer"', batch_html)
        self.assertNotIn('name="observed_at"', batch_html)
        self.assertNotIn('name="location_lat"', batch_html)
        self.assertNotIn('name="altitude_m"', batch_html)
        self.assertNotIn('name="source_type"', batch_html)
        self.assertNotIn('name="source_label"', batch_html)
        new_observation_html = html[html.index('id="new-observation"') : html.index('id="import-observation-exif"')]
        self.assertIn('name="observation_exif_images"', new_observation_html)
        self.assertIn('enctype="multipart/form-data"', new_observation_html)
        self.assertNotIn('data-observation-exif-preview', new_observation_html)
        page = self.web_server.html_page("Mushroom species", html, auto_refresh=False).decode("utf-8")
        self.assertIn("/api/mushrooms/observation-exif-preview", page)
        self.assertIn("updateObservationExifPreview(event.target)", page)
        self.assertIn("URL.createObjectURL(file)", page)
        self.assertIn("new XMLHttpRequest()", page)
        self.assertIn('id="observation-save-progress-modal"', page)
        self.assertIn("xhr.upload.onprogress", page)
        self.assertIn('xhr.setRequestHeader("X-Rainmapper-Async", "1")', page)
        self.assertIn('saveFormData.append("rainmapper_async", "1")', page)
        self.assertIn("Cancelar subida", page)
        self.assertIn('id="observation-exif-preview-modal"', page)
        self.assertIn('data-observation-exif-action="image_only"', page)
        self.assertIn('data-observation-exif-action="exif_only"', page)
        self.assertIn('data-observation-exif-action="image_and_exif"', page)
        self.assertIn("applyObservationExifPreview(exifPreviewAction.dataset.observationExifAction)", page)
        self.assertIn('event.target.matches(".observations-filters [data-observation-search]")', page)
        self.assertIn("submitObservationSearch(event.target)", page)
        self.assertIn("observationFilters.requestSubmit()", page)
        self.assertIn(self.web_server.mushroom_profiles_ui.ui_label("ui.image_preview_title"), page)
        self.assertIn(self.web_server.mushroom_profiles_ui.ui_label("ui.load_image_and_exif"), page)
        self.assertIn("grid-template-columns: 180px minmax(0, 1fr)", page)
        self.assertIn("min-height: 165px", page)
        self.assertIn("grid-template-columns: minmax(0, 1fr) minmax(360px, .25fr)", page)
        self.assertIn(".observations-screen{gap:8px;padding:10px 12px}", page)
        self.assertIn(".observations-screen .profile-section-card{gap:6px;padding:8px}", page)
        self.assertIn("max-height: 500px", page)
        self.assertIn("min-width: 800px", page)
        self.assertIn(".observation-row-actions .button-link.compact{margin:0;min-height:26px;padding:4px 6px}", page)
        self.assertIn("air-datepicker@3.6.0/air-datepicker.css", page)
        self.assertIn("air-datepicker@3.6.0/air-datepicker.js", page)
        self.assertIn("initializeObservationDatePickers(document)", page)
        self.assertIn('buttons: ["today", "clear"]', page)
        self.assertIn('months: "yyyy"', page)
        self.assertIn(".observations-filters .admin-field .observation-date-display", page)
        self.assertIn("padding-right:34px", page)
        self.assertNotIn(self.web_server.mushroom_profiles_ui.ui_label("source_quality"), detail_html)
        self.assertNotIn(self.web_server.mushroom_profiles_ui.ui_label("ui.calibration_weight"), detail_html)
        self.assertNotIn(self.web_server.mushroom_profiles_ui.ui_label("ui.micro_area"), detail_html)
        self.assertIn(">Setal<", detail_html)
        self.assertIn("grid-template-columns:minmax(82px,.45fr) minmax(0,1fr)", page)
        for field_key in (
            "site_context.observed_host_ids",
            "site_context.observed_forest_type_ids",
            "site_context.observed_soil_tendency_ids",
            "site_context.observed_habitat_feature_ids",
            "site_context.observed_aspect_ids",
        ):
            self.assertNotIn(self.web_server.mushroom_profiles_ui.ui_label(field_key), detail_html)
            self.assertIn(self.web_server.mushroom_profiles_ui.compact_observation_detail_label(field_key), detail_html)
        self.assertIn("closeObservationExifPreview({ clearInput: true })", page)
        self.assertIn("captured_at_display", page)
        self.assertIn('/api/mushrooms/observation-detail?', page)
        self.assertIn('window.history.pushState({ observationId: payload.observation_id }', page)
        self.assertIn("if (modalLayerForHash(window.location.hash))", page)
        self.assertNotIn("rainmapperMaplibreAuth", page)
        self.assertNotIn("X-Rainmapper-Device", page)
        self.assertIn('name="observed_host_ids"', html)
        self.assertIn('class="profile-action-bar observations-main-actions maintenance-action-bar"', html)
        self.assertNotIn('<details id="gis-reconstruction-lab"', html)
        self.assertNotIn(self.web_server.mushroom_profiles_ui.ui_label("ui.rebuild_managed_in_workers"), html)
        self.assertNotIn('name="profile_action" value="rebuild_observation_model_v0"', html)
        self.assertNotIn('name="gis_reconstruction_scope"', html)
        self.assertLess(html.index('href="#new-observation"'), html.index('id="archived-observations"'))
        self.assertIn('data-observation-select data-observation-id="obs_20260629_0001"', html)
        self.assertIn('data-observation-href=', html)
        self.assertIn('onclick="selectObservationRow(this, event)"', html)
        self.assertIn('class="observation-pagination"', html)
        self.assertIn('class="observation-page-range">1–1 de 1', html)
        self.assertIn('title="Primera página"', html)
        self.assertIn('title="Última página"', html)
        self.assertIn('class="observation-map-link" href="#observation-map-obs-20260629-0001"', html)
        self.assertIn('id="observation-map-obs-20260629-0001"', html)
        self.assertIn('data-modal-history-close', html)
        self.assertIn('data-observation-href="?section=observations&amp;obs_id=obs_20260629_0001&amp;id=boletus_pinophilus&amp;date_from=2026-06-29&amp;result=abundant&amp;page=1&amp;page_size=25"', html)
        self.assertIn('class="observation-site-map"', html)
        self.assertEqual(html.count('id="observation-known-sites-data"'), 1)
        self.assertIn('class="observation-map-control observation-layer-toggle"', html)
        self.assertIn('class="observation-map-control observation-terrain-toggle"', html)
        self.assertIn('class="observation-map-control observation-north-toggle"', html)
        self.assertIn("www.google.com/maps/search/", html)
        self.assertIn('data-observation-draft-map>Map</button>', html)
        self.assertIn('class="observation-photo-link" href="#observation-photo-obs-20260629-0001-', html)
        self.assertNotIn('class="observation-photo-link" href="./observation-media?path=', html)
        self.assertIn('id="observation-photo-raw-exif-obs-20260629-0001-', html)
        self.assertIn('href="#observation-photo-raw-exif-obs-20260629-0001-', html)
        self.assertIn("Raw EXIF metadata", html)
        self.assertIn("Imagen no encontrada en disco", html)
        self.assertIn("Scots pine", html)
        self.assertNotIn("missing label:", html)
        self.assertIn("obs_20260629_0001", html)
        self.assertNotIn("obs_20260620_0001", html)
        self.assertNotIn("obs_20260628_0001", html)

        nested_search_html = self.web_server.mushroom_profiles_ui.render_observations_section(
            profile,
            profiles,
            catalogs,
            observations,
            archived_observations,
            filters={"obs_q": "barranco umbrío"},
        )
        self.assertIn("obs_20260629_0001", nested_search_html)
        self.assertNotIn("obs_20260620_0001", nested_search_html)

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

    def test_observation_table_uses_area_names_without_exposing_site_ids(self) -> None:
        rows = [
            {
                "observation_id": "obs_names_0001",
                "species_id": "boletus_pinophilus",
                "observed_at": "2026-07-17",
                "flush_abundance": "normal",
                "validation_status": "valid",
                "calibration_use": "include",
                "micro_area_id": "micro_internal_id",
                "observer": {"name": "Carlos"},
                "source": {"label": "IMG_6908.jpeg"},
            }
        ]
        known_sites = {
            "areas": [{"area_id": "area_internal_id", "name": "Sant Joan"}],
            "micro_areas": [
                {
                    "micro_area_id": "micro_internal_id",
                    "area_id": "area_internal_id",
                    "name": "Serrat de la Carbassa",
                }
            ],
        }
        with mock.patch.object(
            self.web_server.mushroom_profiles_ui.mushroom_known_sites,
            "load_payload",
            return_value=known_sites,
        ):
            table_html = self.web_server.mushroom_profiles_ui.render_observation_table(
                rows,
                {},
                {"boletus_pinophilus": "Boletus pinophilus"},
            )

        self.assertIn("Sant Joan", table_html)
        self.assertIn("Serrat de la Carbassa", table_html)
        self.assertNotIn("area_internal_id", table_html)
        self.assertNotIn("micro_internal_id", table_html)
        self.assertNotIn("Carlos", table_html)
        self.assertNotIn("IMG_6908.jpeg", table_html)

    def test_observation_pager_renders_compact_svg_navigation(self) -> None:
        pager_html = self.web_server.mushroom_profiles_ui.render_observation_pager(
            126,
            1,
            25,
            6,
            "",
            "",
            {"sort": "observed_at", "dir": "desc", "page_size": "25"},
        )

        self.assertIn("1–25 de 126", pager_html)
        self.assertEqual(pager_html.count('<svg aria-hidden="true"'), 4)
        self.assertIn("page=2", pager_html)
        self.assertIn("page=6", pager_html)
        self.assertIn('title="Primera página"', pager_html)
        self.assertIn('title="Página anterior"', pager_html)
        self.assertIn('aria-disabled="true"', pager_html)

    def test_observation_workspace_only_renders_the_requested_page_rows(self) -> None:
        profile = {"species_id": "boletus_pinophilus", "scientific_name": "Boletus pinophilus"}
        observations = {
            "observations": [
                {
                    "observation_id": f"obs_page_{index:04d}",
                    "species_id": "boletus_pinophilus",
                    "observed_at": f"2026-06-{index:02d}",
                    "flush_abundance": "normal",
                    "validation_status": "valid",
                    "calibration_use": "include",
                }
                for index in range(1, 31)
            ]
        }
        with mock.patch.object(
            self.web_server.mushroom_profiles_ui.mushroom_known_sites,
            "load_payload",
            return_value={"areas": [], "micro_areas": []},
        ):
            first_page = self.web_server.mushroom_profiles_ui.render_observations_section(
                profile,
                [profile],
                {},
                observations,
                {"observations": []},
                filters={"page_size": "25"},
            )
            second_page = self.web_server.mushroom_profiles_ui.render_observations_section(
                profile,
                [profile],
                {},
                observations,
                {"observations": []},
                filters={"page": "2", "page_size": "25"},
            )

        self.assertEqual(first_page.count("data-observation-select"), 25)
        self.assertIn("1–25 de 30", first_page)
        self.assertEqual(second_page.count("data-observation-select"), 5)
        self.assertIn("26–30 de 30", second_page)

    def test_observation_search_filters_all_rows_before_pagination(self) -> None:
        profile = {"species_id": "boletus_pinophilus", "scientific_name": "Boletus pinophilus"}
        observations = {
            "observations": [
                {
                    "observation_id": f"obs_search_{index:04d}",
                    "species_id": "boletus_pinophilus",
                    "observed_at": f"2026-06-{index:02d}",
                    "flush_abundance": "normal",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "micro_area_id": "micro_target_0001" if index == 30 else "micro_other_0001",
                    "source_notes": "unrelated",
                }
                for index in range(1, 31)
            ]
        }
        with mock.patch.object(
            self.web_server.mushroom_profiles_ui.mushroom_known_sites,
            "load_payload",
            return_value={
                "areas": [
                    {"area_id": "area_target_0001", "name": "Guils"},
                    {"area_id": "area_other_0001", "name": "Ordino"},
                ],
                "micro_areas": [
                    {
                        "micro_area_id": "micro_target_0001",
                        "area_id": "area_target_0001",
                        "name": "La Socarrada",
                    },
                    {
                        "micro_area_id": "micro_other_0001",
                        "area_id": "area_other_0001",
                        "name": "Cota 2100",
                    },
                ],
            },
        ):
            filtered = self.web_server.mushroom_profiles_ui.render_observations_section(
                profile,
                [profile],
                {},
                observations,
                {"observations": []},
                filters={"obs_q": "guils", "page": "2", "page_size": "25"},
            )

        self.assertEqual(filtered.count("data-observation-select"), 1)
        self.assertIn("obs_search_0030", filtered)
        self.assertNotIn("obs_search_0001", filtered)
        self.assertIn("1–1 de 1", filtered)

    def test_observation_detail_endpoint_returns_only_selected_fragment(self) -> None:
        store = mock.Mock()
        store.load.side_effect = lambda name: {
            "profiles": {
                "species_profiles": [
                    {"species_id": "boletus_pinophilus", "scientific_name": "Boletus pinophilus"}
                ]
            },
            "catalogs": {"catalogs": {}},
            "observations": {
                "observations": [
                    {
                        "observation_id": "obs_detail_0001",
                        "species_id": "boletus_pinophilus",
                        "observed_at": "2026-07-17",
                        "flush_abundance": "normal",
                        "validation_status": "valid",
                        "calibration_use": "include",
                    },
                    {
                        "observation_id": "obs_detail_0002",
                        "species_id": "boletus_pinophilus",
                        "observed_at": "2026-07-16",
                    },
                ]
            },
        }[name]
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured: dict[str, object] = {}
        handler.send_json = lambda status, payload: captured.update(status=status, payload=payload)

        with (
            mock.patch.object(self.web_server, "default_store", return_value=store),
            mock.patch.object(self.web_server, "load_archived_observations", return_value={"observations": []}),
            mock.patch.object(
                self.web_server.mushroom_profiles_ui.mushroom_known_sites,
                "load_payload",
                return_value={"areas": [], "micro_areas": []},
            ),
        ):
            handler.serve_mushroom_observation_detail(
                {"obs_id": ["obs_detail_0001"], "id": ["boletus_pinophilus"], "page": ["1"]}
            )

        self.assertEqual(captured["status"], 200)
        payload = captured["payload"]
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["observation_id"], "obs_detail_0001")
        self.assertIn("obs_detail_0001", payload["html"])
        self.assertNotIn("obs_detail_0002", payload["html"])

    def test_mushroom_species_page_has_generic_modal_navigation_history(self) -> None:
        page = self.web_server.html_page(
            "Mushroom species",
            '<a href="#edit-observation-1">Edit</a><div id="edit-observation-1" class="modal-layer"></div>',
            auto_refresh=False,
            page_class="mushroom-wide-page",
        ).decode("utf-8")

        self.assertIn("rainmapperSpeciesMaintenanceModalHistory", page)
        self.assertIn("rainmapperSpeciesMaintenanceScrollRestore", page)
        self.assertIn("rememberSpeciesModalNavigation(event)", page)
        self.assertIn("closeSpeciesModalWithHistory(event)", page)
        self.assertIn("modalLayerForHash(targetHash)", page)
        self.assertIn("stack.push({ url: currentUrl, y: window.scrollY || 0 })", page)
        self.assertIn("rememberScrollRestoreForUrl(returnUrl, returnEntry.y)", page)
        self.assertIn("}, true);", page)

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
        self.assertIn("local-evidence-screen", html)
        self.assertIn("Observed, not declared", html)
        self.assertIn("Declared, not observed", html)
        self.assertIn("Promote", html)
        self.assertIn("Doubtful", html)
        self.assertIn("Hosts + forests", html)
        self.assertIn("Soils + habitat", html)
        self.assertIn('name="profile_action" value="update_evidence_decision"', html)
        self.assertIn('name="view" value="v0"', html)
        self.assertIn('name="evidence_view" value="hosts_forests"', html)
        self.assertIn("host_quercus_ilex", html)
        self.assertIn("host_quercus_suber", html)
        self.assertIn("Quercus ilex - Holm oak", html)
        self.assertIn("Quercus suber - Cork oak", html)
        self.assertNotIn('<span class="meta">host_quercus_ilex</span>', html)
        self.assertNotIn('<span class="meta">forest_holm_oak</span>', html)
        self.assertIn("Whether this ID is already declared", html)
        self.assertIn("Evidence observations", html)
        self.assertIn('class="observation-site-map"', html)
        self.assertIn('data-observation-map-target=', html)
        self.assertIn("Microáreas visibles", html)
        self.assertIn(">Open</a>", html)
        self.assertIn('href="?section=observations&amp;obs_id=obs_1&amp;id=boletus_aereus">Open</a>', html)
        self.assertNotIn("Ejemplos", html)

        soils_html = self.web_server.mushroom_profiles_ui.render_local_evidence_section(
            profile,
            catalogs,
            reconstruction,
            None,
            decisions,
            profile_view="v0",
            evidence_view="soils_habitat",
        )
        self.assertIn("Soils", soils_html)
        self.assertIn("Habitat", soils_html)
        self.assertIn('name="view" value="v0"', soils_html)
        self.assertIn('name="evidence_view" value="soils_habitat"', soils_html)
        self.assertNotIn("Quercus ilex - Holm oak", soils_html)

        self.assertEqual(
            "?id=boletus_aereus&section=evidence&view=v0&evidence_view=soils_habitat#mushroom-profile-message",
            self.web_server.evidence_return_url(
                "boletus_aereus",
                profile_view="v0",
                evidence_view="soils_habitat",
            ),
        )

    def test_mushroom_local_evidence_section_counts_field_hosts_from_joined_features(self) -> None:
        profile = {
            "species_id": "boletus_aereus",
            "scientific_name": "Boletus aereus",
            "common_names": ["hongo negro"],
            "ecology": {
                "host_affinities": [{"id": "host_quercus_ilex", "v0_active": True}],
                "forest_type_affinities": [],
                "soil_affinities": [],
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
            ],
            "forest_types": [],
            "soil_types": [],
            "habitat_features": [],
        }
        reconstruction = {
            "generated_at": "2026-07-02T12:00:00",
            "results": [
                {
                    "observation_id": "obs_1",
                    "species_id": "boletus_aereus",
                    "location": {"lat": 41.75, "lon": 2.15, "source": "mushroom_observations"},
                    "gis_context_v0": {"host_ids": []},
                }
            ],
        }
        features = {
            "generated_at": "2026-07-02T14:00:00",
            "rows": [
                {
                    "observation_id": "obs_1",
                    "species_id": "boletus_aereus",
                    "host_ids": ["host_quercus_ilex"],
                    "host_sources": {"host_quercus_ilex": ["field"]},
                }
            ],
        }

        html = self.web_server.mushroom_profiles_ui.render_local_evidence_section(
            profile,
            catalogs,
            reconstruction,
            features,
            None,
            profile_view="v0",
        )

        self.assertIn("Quercus ilex - Holm oak", html)
        self.assertIn(">Declared and observed<", html)
        self.assertIn(">Field<", html)
        self.assertIn('<a class="evidence-source-chip source-field active" href="#evidence-observations-host-affinities-host-quercus-ilex-field"', html)
        self.assertIn('<span class="evidence-source-chip source-gis"><span>GIS/DEM</span><strong>0</strong></span>', html)
        self.assertNotIn("evidence-observation-link", html)
        self.assertIn('<span class="label">Declared, not observed</span><span class="value">0</span>', html)

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
                    "weather_gaps": ["rain_7d_coverage_6/7", "wind_no_data_7d"],
                },
                {
                    "observation_id": "obs_2",
                    "species_id": "boletus_aereus",
                    "observed_at": "2025-10-01",
                    "analysis_result": "present",
                    "prediction_target": "unfavorable",
                    "flush_abundance": "scarce",
                    "rain_7d_mm": 4.0,
                    "weather_source": "meteocat",
                    "weather_station_code": "X1",
                },
            ],
        }

        catalogs = {
            "observation_flush_abundance": [
                {"id": "abundant", "label": {"en": "Abundant", "es": "Abundante", "ca": "Abundant"}, "prediction_favorable": 1},
                {"id": "scarce", "label": {"en": "Scarce", "es": "Escasa", "ca": "Escassa"}, "prediction_favorable": 0},
            ]
        }
        html = self.web_server.mushroom_profiles_ui.render_local_evidence_section(
            profile,
            catalogs,
            {"generated_at": "2026-07-02T12:00:00", "results": []},
            features_payload,
            None,
            evidence_view="weather",
        )

        self.assertIn("Weather evidence", html)
        self.assertIn("Latest v0 features join: 2026-07-02T14:00:00", html)
        self.assertIn('<span class="evidence-status ok">Favorable</span>', html)
        self.assertIn('<span class="evidence-status muted">Unfavorable</span>', html)
        self.assertIn("Scarce", html)
        self.assertNotIn("Positive / present", html)
        self.assertNotIn("Negative / absent", html)
        self.assertIn("Abundant", html)
        self.assertIn('<span>mm</span><em>21d</em>', html)
        self.assertIn('<span>mm</span><em>60d</em>', html)
        self.assertIn('<span>m</span><em>Alt.</em>', html)
        self.assertIn('<span>°C</span><em>30d</em>', html)
        self.assertIn('<span>%</span><em>30d</em>', html)
        self.assertIn("<td>705</td>", html)
        self.assertIn("<td>11</td>", html)
        self.assertIn("meteocat", html)
        self.assertIn("Acumulado de lluvia de 7 dias calculado con 6 dias validos de 7", html)
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
        self.assertIn('./workers?scope=species&amp;species_id=boletus_aereus', html)
        self.assertIn('./workers?scope=all', html)
        self.assertNotIn('name="profile_action" value="rebuild_learned_model_v0_species"', html)
        self.assertNotIn('name="profile_action" value="rebuild_learned_model_v0_all"', html)
        self.assertIn("Rebuild this species", html)
        self.assertIn("Rebuild all species", html)

    def test_mushroom_learned_model_rebuild_all_post_starts_background_job(self) -> None:
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
        with mock.patch.object(
            self.web_server,
            "start_mushroom_model_rebuild_job",
            return_value="job_123",
        ) as start_job:
            redirect = handler.handle_mushroom_profiles_post(
                {
                    "profile_action": ["rebuild_learned_model_v0_all"],
                    "species_id": ["amanita_caesarea"],
                    "view": ["v0"],
                    "evidence_view": ["learned_model"],
                }
            )

        start_job.assert_called_once()
        call_kwargs = start_job.call_args.kwargs
        self.assertTrue(call_kwargs["selected_observation_ids"])
        self.assertEqual("all", call_kwargs["reconstruction_scope"])
        self.assertNotIn("pending_species_ids", call_kwargs)
        self.assertIn(
            "?id=amanita_caesarea&section=evidence&view=v0&evidence_view=learned_model&rebuild_job=job_123",
            redirect,
        )
        self.assertTrue(redirect.endswith("#mushroom-profile-message"))
        self.assertIn("Global Modelo v0 rebuild started", self.web_server.RUN_STATE["mushroom_profiles_flash"])

    def test_mushroom_learned_model_rebuild_selected_species_starts_background_job(self) -> None:
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
        with mock.patch.object(
            self.web_server,
            "start_mushroom_model_rebuild_job",
            return_value="job_456",
        ) as start_job:
            redirect = handler.handle_mushroom_profiles_post(
                {
                    "profile_action": ["rebuild_learned_model_v0_species"],
                    "species_id": ["amanita_caesarea"],
                    "view": ["v0"],
                    "evidence_view": ["learned_model"],
                }
            )

        start_job.assert_called_once()
        call_kwargs = start_job.call_args.kwargs
        self.assertTrue(call_kwargs["selected_observation_ids"])
        self.assertEqual("species", call_kwargs["reconstruction_scope"])
        self.assertEqual(["amanita_caesarea"], call_kwargs["pending_species_ids"])
        self.assertIn(
            "?id=amanita_caesarea&section=evidence&view=v0&evidence_view=learned_model&rebuild_job=job_456",
            redirect,
        )
        self.assertTrue(redirect.endswith("#mushroom-profile-message"))
        self.assertIn("selected species", self.web_server.RUN_STATE["mushroom_profiles_flash"])

    def test_mushroom_observation_model_rebuild_post_runs_full_v0_chain(self) -> None:
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

        class ImmediateThread:
            def __init__(self, target, name=None, daemon=None):
                self.target = target

            def start(self):
                self.target()

        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        with mock.patch.object(self.web_server.mushroom_gis_lab, "reconstruct_observations") as gis_builder, \
            mock.patch.object(self.web_server.mushroom_observation_context, "build_and_write_observation_weather_features") as weather_builder, \
            mock.patch.object(self.web_server.mushroom_observation_features, "build_and_write_observation_features_v0") as features_builder, \
            mock.patch.object(self.web_server.mushroom_learned_model, "build_and_write_learned_model_v0") as model_builder, \
            mock.patch.object(self.web_server.threading, "Thread", ImmediateThread):
            gis_builder.return_value = {"result_count": 1}
            weather_builder.return_value = {"summary": {"observations": 8}}
            features_builder.return_value = {"summary": {"observations": 8}}
            model_builder.return_value = {"summary": {"species": 1}}

            redirect = handler.handle_mushroom_profiles_post(
                {
                    "profile_action": ["rebuild_observation_model_v0"],
                    "species_id": ["amanita_caesarea"],
                    "obs_species": ["amanita_caesarea"],
                    "view": ["v0"],
                    "gis_reconstruction_scope": ["selected"],
                    "gis_observation_ids": ["obs_20250930_0001"],
                }
            )

        gis_builder.assert_called_once()
        self.assertEqual(["obs_20250930_0001"], gis_builder.call_args.args[1])
        self.assertIn("progress_callback", gis_builder.call_args.kwargs)
        weather_builder.assert_called_once()
        self.assertTrue(callable(weather_builder.call_args.kwargs.get("progress_callback")))
        features_builder.assert_called_once()
        self.assertTrue(callable(features_builder.call_args.kwargs.get("progress_callback")))
        model_builder.assert_called_once()
        self.assertTrue(callable(model_builder.call_args.kwargs.get("progress_callback")))
        self.assertIn("?section=observations&id=amanita_caesarea&rebuild_job=", redirect)
        self.assertTrue(redirect.endswith("#gis-reconstruction-lab"))
        job_id = redirect.split("rebuild_job=", 1)[1].split("#", 1)[0]
        status = self.web_server.get_mushroom_rebuild_job_status(job_id)
        self.assertIsNotNone(status)
        self.assertEqual("complete", status["status"])
        self.assertEqual(100, status["overall_percent"])
        self.assertIn("elapsed", status)
        self.assertIn("Modelo v0 rebuilt", self.web_server.RUN_STATE["mushroom_profiles_flash"])

    def test_shared_mushroom_rebuild_pipeline_is_opt_in_and_reports_completion(self) -> None:
        data_dir = Path(self.temp_dir.name)

        class ImmediateThread:
            def __init__(self, target, name=None, daemon=None):
                self.target = target

            def start(self):
                self.target()

        environment = {
            "RAINMAPPER_MUSHROOM_REBUILD_PIPELINE": "shared",
            "RAINMAPPER_MUSHROOM_DEFAULTS_DIR": str(ROOT_DIR / "mushroom-data"),
            "RAINMAPPER_MUSHROOM_DATA_DIR": str(data_dir / "mushroom-data"),
            "RAINMAPPER_SHARE_ROOT": str(data_dir),
            "RAINMAPPER_MUSHROOM_GIS_ROOT": str(data_dir / "mushroom-GIS"),
        }
        with mock.patch.dict(os.environ, environment, clear=False):
            self.web_server.default_store().ensure_seeded()
            with mock.patch.object(
                self.web_server.mushroom_rebuild_pipeline,
                "run_rebuild",
                return_value={
                    "summary": {
                        "gis_observations": 1,
                        "weather_observations": 8,
                        "feature_observations": 8,
                        "model_species": 1,
                    },
                    "phase_durations_seconds": {"gis_dem": 1.25},
                    "duration_seconds": 1.5,
                },
            ) as shared_builder, mock.patch.object(
                self.web_server.mushroom_rebuild_pipeline,
                "promote_qgis_points",
            ), mock.patch.object(
                self.web_server.mushroom_rebuild_pipeline,
                "promote_rebuild_outputs",
                return_value={"status": "promoted", "artifact_count": 9},
            ), mock.patch.object(
                self.web_server.mushroom_gis_lab,
                "reconstruct_observations",
            ) as legacy_gis_builder, mock.patch.object(
                self.web_server.mushroom_model_state,
                "clear_all_pending",
            ) as clear_pending, mock.patch.object(
                self.web_server.threading,
                "Thread",
                ImmediateThread,
            ):
                job_id = self.web_server.start_mushroom_model_rebuild_job(
                    selected_observation_ids=["obs_20250930_0001"],
                    reconstruction_scope="all",
                    return_url="?section=observations",
                )

        shared_builder.assert_called_once()
        call_args = shared_builder.call_args
        self.assertEqual(
            call_args.args[0].observations,
            data_dir / "mushroom-data/mushroom_observations.json",
        )
        self.assertEqual(
            call_args.args[1].root.parent.parent,
            (data_dir / "mushroom-data").resolve(),
        )
        self.assertEqual(
            call_args.kwargs["selected_observation_ids"],
            ["obs_20250930_0001"],
        )
        self.assertFalse(legacy_gis_builder.called)
        clear_pending.assert_called_once_with(full_rebuild=True)
        status = self.web_server.get_mushroom_rebuild_job_status(job_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "complete")
        self.assertEqual(status["result"]["pipeline"], "shared")
        self.assertEqual(status["result"]["phase_durations_seconds"], {"gis_dem": 1.25})
        self.assertEqual(status["result"]["duration_seconds"], 1.5)

    def test_shared_rebuild_failure_keeps_accepted_artifacts_and_pending_state(self) -> None:
        data_dir = Path(self.temp_dir.name)

        class ImmediateThread:
            def __init__(self, target, name=None, daemon=None):
                self.target = target

            def start(self):
                self.target()

        environment = {
            "RAINMAPPER_MUSHROOM_REBUILD_PIPELINE": "shared",
            "RAINMAPPER_MUSHROOM_DEFAULTS_DIR": str(ROOT_DIR / "mushroom-data"),
            "RAINMAPPER_MUSHROOM_DATA_DIR": str(data_dir / "mushroom-data"),
            "RAINMAPPER_SHARE_ROOT": str(data_dir),
            "RAINMAPPER_MUSHROOM_GIS_ROOT": str(data_dir / "mushroom-GIS"),
        }
        with mock.patch.dict(os.environ, environment, clear=False):
            self.web_server.default_store().ensure_seeded()
            accepted_model = data_dir / "mushroom-data/mushroom_model_v0.json"
            accepted_model.write_text("accepted", encoding="utf-8")

            for phase in ("GIS/DEM", "Meteorologia", "Features v0", "Modelo aprendido v0"):
                def fail_in_phase(_inputs, outputs, **_kwargs):
                    outputs.model_json.parent.mkdir(parents=True, exist_ok=True)
                    outputs.model_json.write_text("partial", encoding="utf-8")
                    raise RuntimeError(f"injected {phase} failure")

                with self.subTest(phase=phase), mock.patch.object(
                    self.web_server.mushroom_rebuild_pipeline,
                    "run_rebuild",
                    side_effect=fail_in_phase,
                ), mock.patch.object(
                    self.web_server.mushroom_rebuild_pipeline,
                    "promote_rebuild_outputs",
                ) as promote, mock.patch.object(
                    self.web_server.mushroom_model_state,
                    "clear_all_pending",
                ) as clear_pending, mock.patch.object(
                    self.web_server.threading,
                    "Thread",
                    ImmediateThread,
                ):
                    job_id = self.web_server.start_mushroom_model_rebuild_job(
                        selected_observation_ids=["obs_20250930_0001"],
                        reconstruction_scope="all",
                        return_url="?section=observations",
                    )

                status = self.web_server.get_mushroom_rebuild_job_status(job_id)
                self.assertEqual(status["status"], "failed")
                self.assertIn(phase, status["error"])
                self.assertEqual(accepted_model.read_text(encoding="utf-8"), "accepted")
                self.assertFalse(promote.called)
                self.assertFalse(clear_pending.called)
                staging = data_dir / "mushroom-data/.rebuild-staging"
                self.assertFalse(any(staging.iterdir()) if staging.exists() else False)

    def test_shared_rebuild_can_be_cancelled_without_promotion(self) -> None:
        data_dir = Path(self.temp_dir.name)
        started = threading.Event()
        environment = {
            "RAINMAPPER_MUSHROOM_REBUILD_PIPELINE": "shared",
            "RAINMAPPER_MUSHROOM_DEFAULTS_DIR": str(ROOT_DIR / "mushroom-data"),
            "RAINMAPPER_MUSHROOM_DATA_DIR": str(data_dir / "mushroom-data"),
            "RAINMAPPER_SHARE_ROOT": str(data_dir),
            "RAINMAPPER_MUSHROOM_GIS_ROOT": str(data_dir / "mushroom-GIS"),
        }

        def wait_for_cancel(_inputs, outputs, *, cancel_event, **_kwargs):
            outputs.model_json.parent.mkdir(parents=True, exist_ok=True)
            outputs.model_json.write_text("partial", encoding="utf-8")
            started.set()
            while not cancel_event.is_set():
                time.sleep(0.001)
            raise self.web_server.mushroom_rebuild_pipeline.RebuildCancelled()

        with mock.patch.dict(os.environ, environment, clear=False):
            self.web_server.default_store().ensure_seeded()
            accepted_model = data_dir / "mushroom-data/mushroom_model_v0.json"
            accepted_model.write_text("accepted", encoding="utf-8")
            with mock.patch.object(
                self.web_server.mushroom_rebuild_pipeline,
                "run_rebuild",
                side_effect=wait_for_cancel,
            ), mock.patch.object(
                self.web_server.mushroom_rebuild_pipeline,
                "promote_rebuild_outputs",
            ) as promote, mock.patch.object(
                self.web_server.mushroom_model_state,
                "clear_all_pending",
            ) as clear_pending:
                job_id = self.web_server.start_mushroom_model_rebuild_job(
                    selected_observation_ids=["obs_20250930_0001"],
                    reconstruction_scope="all",
                    return_url="?section=observations",
                )
                self.assertTrue(started.wait(timeout=2))
                response_status, response = self.web_server.request_mushroom_rebuild_cancel(job_id)
                self.assertEqual(response_status, 202)
                self.assertTrue(response["ok"])
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    status = self.web_server.get_mushroom_rebuild_job_status(job_id)
                    if status and status["status"] == "cancelled":
                        break
                    time.sleep(0.01)

        self.assertEqual(status["status"], "cancelled")
        self.assertTrue(status["cancel_requested"])
        self.assertEqual(accepted_model.read_text(encoding="utf-8"), "accepted")
        self.assertFalse(promote.called)
        self.assertFalse(clear_pending.called)
        staging = data_dir / "mushroom-data/.rebuild-staging"
        self.assertFalse(any(staging.iterdir()) if staging.exists() else False)

    def test_mushroom_rebuild_progress_close_refreshes_completed_screen(self) -> None:
        html = self.web_server.render_mushroom_rebuild_progress_modal(
            "job_123",
            "?section=observations&id=amanita_caesarea#gis-reconstruction-lab",
        )

        self.assertIn('data-refresh-url="?section=observations&amp;id=amanita_caesarea#gis-reconstruction-lab"', html)
        self.assertIn('terminalStatus === "complete"', html)
        self.assertIn('job.status === "cancelled"', html)
        self.assertIn('id="mushroom-rebuild-progress-cancel"', html)
        self.assertIn("/api/mushrooms/rebuild-cancel", html)
        self.assertIn("window.location.href = refreshUrl", html)
        self.assertIn('window.location.pathname.replace(new RegExp("/mushrooms/(profiles|workers)/?$"), "")', html)
        self.assertIn('${statusUrl}?job_id=${encodeURIComponent(jobId)}', html)
        self.assertNotIn('fetch(`/api/mushrooms/rebuild-status', html)

    def test_worker_heartbeat_registers_named_physical_worker(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        payload = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": "worker_12345678",
            "display_name": "M1 personal",
            "host_name": "macbook-m1-test",
            "architecture": "arm64",
            "platform": "Darwin",
            "worker_version": "local",
            "status": "idle",
            "job_api": "not_implemented",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid", "file_count": 10, "size_bytes": 6306367027},
        }
        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "false"}), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ):
            status, response = self.web_server.register_mushroom_worker_heartbeat(payload, now=100)
            workers = self.web_server.registered_mushroom_worker_statuses(now=105)

        self.assertEqual(status, 200)
        self.assertEqual(response["worker_id"], "worker_12345678")
        self.assertEqual(response["heartbeat_interval_seconds"], 2)
        self.assertEqual(len(workers), 1)
        self.assertTrue(workers[0]["reachable"])
        self.assertEqual(workers[0]["payload"]["display_name"], "M1 personal")
        self.assertEqual(workers[0]["payload"]["host_name"], "macbook-m1-test")
        self.assertTrue(registry_path.exists())

    def test_worker_heartbeat_api_is_disabled_unless_explicitly_enabled(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "false"}), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ):
            status, response = self.web_server.register_mushroom_worker_heartbeat({})

        self.assertEqual(status, 404)
        self.assertFalse(response["ok"])
        self.assertFalse(registry_path.exists())

    def test_worker_operational_mode_requires_api_and_auth(self) -> None:
        combinations = (
            ("false", "false", False),
            ("false", "true", False),
            ("true", "false", False),
            ("true", "true", True),
        )
        for api_enabled, auth_required, expected in combinations:
            with self.subTest(api_enabled=api_enabled, auth_required=auth_required), mock.patch.dict(
                os.environ,
                {
                    "RAINMAPPER_WORKER_API_ENABLED": api_enabled,
                    "RAINMAPPER_WORKER_AUTH_REQUIRED": auth_required,
                    "RAINMAPPER_WORKER_OPERATIONAL_ENABLED": "true",
                },
            ):
                self.assertEqual(expected, self.web_server.mushroom_worker_operational_enabled())

    def test_worker_pairing_is_one_time_and_authenticates_heartbeats(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        credentials_path = Path(self.temp_dir.name) / "mushroom_worker_credentials.json"
        jobs_path = Path(self.temp_dir.name) / "mushroom_worker_jobs.json"
        heartbeat = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": "worker_12345678",
            "display_name": "M1 personal",
            "host_name": "MacBook Pro",
            "architecture": "arm64",
            "platform": "Linux",
            "worker_version": "local",
            "status": "idle",
            "job_api": "lifecycle_probe_v0",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }
        with self.web_server.RUN_LOCK:
            self.web_server.MUSHROOM_WORKER_PAIRINGS.clear()
        with mock.patch.dict(
            os.environ,
            {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "true"},
        ), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ), mock.patch.object(
            self.web_server, "mushroom_worker_credentials_path", return_value=credentials_path
        ), mock.patch.object(
            self.web_server, "mushroom_worker_jobs_path", return_value=jobs_path
        ):
            pairing = self.web_server.create_mushroom_worker_pairing(
                now=1000,
                pairing_code="ABCD-2345",
            )
            pair_status, paired = self.web_server.pair_mushroom_worker(
                {
                    "pairing_code": pairing["pairing_code"],
                    "worker_id": heartbeat["worker_id"],
                    "display_name": heartbeat["display_name"],
                    "host_name": heartbeat["host_name"],
                },
                now=1001,
            )
            reused_status, _reused = self.web_server.pair_mushroom_worker(
                {
                    "pairing_code": pairing["pairing_code"],
                    "worker_id": heartbeat["worker_id"],
                    "display_name": heartbeat["display_name"],
                    "host_name": heartbeat["host_name"],
                },
                now=1002,
            )
            missing_status, _missing = self.web_server.register_mushroom_worker_heartbeat(heartbeat)
            wrong_status, _wrong = self.web_server.register_mushroom_worker_heartbeat(
                heartbeat,
                auth_token="wrong-token",
            )
            accepted_status, accepted = self.web_server.register_mushroom_worker_heartbeat(
                heartbeat,
                auth_token=str(paired["token"]),
            )
            self.web_server.mushroom_worker_registry.set_default_executor(
                registry_path,
                "worker:worker_12345678",
            )
            create_status, _created = self.web_server.create_mushroom_worker_claim_probe(
                str(heartbeat["worker_id"])
            )
            unauthenticated_claim_status, _unauthenticated_claim = self.web_server.claim_mushroom_worker_job(
                {"worker_id": heartbeat["worker_id"]}
            )
            claim_status, claimed = self.web_server.claim_mushroom_worker_job(
                {"worker_id": heartbeat["worker_id"]},
                auth_token=str(paired["token"]),
            )
            revoke_status, revoked = self.web_server.revoke_mushroom_worker_credential(
                str(heartbeat["worker_id"])
            )
            after_revoke_status, _after_revoke = self.web_server.register_mushroom_worker_heartbeat(
                heartbeat,
                auth_token=str(paired["token"]),
            )
            workers_after_revoke = self.web_server.registered_mushroom_worker_statuses()

        stored_credentials = credentials_path.read_text(encoding="utf-8")
        self.assertEqual(pair_status, 200)
        self.assertEqual(reused_status, 401)
        self.assertEqual(missing_status, 401)
        self.assertEqual(wrong_status, 401)
        self.assertEqual(accepted_status, 200)
        self.assertTrue(accepted["ok"])
        self.assertEqual(create_status, 201)
        self.assertEqual(unauthenticated_claim_status, 401)
        self.assertEqual(claim_status, 200)
        self.assertEqual(claimed["job"]["status"], "claimed")
        self.assertEqual(revoke_status, 200)
        self.assertTrue(revoked["revoked"])
        self.assertTrue(revoked["unregistered"])
        self.assertEqual(after_revoke_status, 401)
        self.assertNotIn(str(paired["token"]), stored_credentials)
        self.assertEqual(workers_after_revoke, [])
        registry = self.web_server.mushroom_worker_registry.load_registry(registry_path)
        self.assertEqual(registry["workers"], [])
        self.assertEqual(registry["default_executor"], "home_assistant")

    def test_expired_worker_pairing_code_is_rejected(self) -> None:
        credentials_path = Path(self.temp_dir.name) / "mushroom_worker_credentials.json"
        with self.web_server.RUN_LOCK:
            self.web_server.MUSHROOM_WORKER_PAIRINGS.clear()
        with mock.patch.dict(
            os.environ,
            {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "true"},
        ), mock.patch.object(
            self.web_server, "mushroom_worker_credentials_path", return_value=credentials_path
        ):
            pairing = self.web_server.create_mushroom_worker_pairing(now=1000, pairing_code="ABCD-2345")
            status, response = self.web_server.pair_mushroom_worker(
                {
                    "pairing_code": pairing["pairing_code"],
                    "worker_id": "worker_12345678",
                    "display_name": "M1 personal",
                    "host_name": "MacBook Pro",
                },
                now=1601,
            )

        self.assertEqual(status, 401)
        self.assertIn("expired", response["error"])
        self.assertFalse(credentials_path.exists())

    def test_new_worker_pairing_code_invalidates_previous_code(self) -> None:
        credentials_path = Path(self.temp_dir.name) / "mushroom_worker_credentials.json"
        with self.web_server.RUN_LOCK:
            self.web_server.MUSHROOM_WORKER_PAIRINGS.clear()
        with mock.patch.dict(
            os.environ,
            {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "true"},
        ), mock.patch.object(
            self.web_server, "mushroom_worker_credentials_path", return_value=credentials_path
        ):
            self.web_server.create_mushroom_worker_pairing(now=1000, pairing_code="ABCD-2345")
            self.web_server.create_mushroom_worker_pairing(now=1001, pairing_code="WXYZ-6789")
            status, _response = self.web_server.pair_mushroom_worker(
                {
                    "pairing_code": "ABCD-2345",
                    "worker_id": "worker_12345678",
                    "display_name": "M1 personal",
                    "host_name": "MacBook Pro",
                },
                now=1002,
            )

        self.assertEqual(status, 401)
        self.assertFalse(credentials_path.exists())

    def test_worker_coordinator_ping_identifies_enabled_local_api(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.server = mock.Mock(rainmapper_listener_role="worker")
        handler.path = "/api/mushrooms/workers/ping"
        handler.headers = {}
        captured: dict[str, object] = {}
        handler.send_json = lambda status, payload: captured.update(status=status, payload=payload)

        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "true"}):
            handler.do_GET()

        self.assertEqual(captured["status"], 200)
        self.assertEqual(captured["payload"]["kind"], "rainmapper_worker_coordinator")
        self.assertTrue(captured["payload"]["auth_required"])

    def test_worker_protocol_is_available_only_on_the_dedicated_listener(self) -> None:
        web_handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        web_handler.server = mock.Mock(rainmapper_listener_role="web")
        web_handler.path = "/api/mushrooms/workers/heartbeat"
        web_handler.headers = {}
        web_response: dict[str, object] = {}
        web_handler.send_json = lambda status, payload: web_response.update(status=status, payload=payload)

        worker_handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        worker_handler.server = mock.Mock(rainmapper_listener_role="worker")
        worker_handler.path = "/mushrooms/workers"
        worker_handler.headers = {}
        worker_response: dict[str, object] = {}
        worker_handler.send_json = lambda status, payload: worker_response.update(status=status, payload=payload)

        web_handler.do_POST()
        worker_handler.do_GET()

        self.assertEqual(web_response["status"], 404)
        self.assertEqual(worker_response["status"], 404)

    def test_worker_web_controls_require_ingress_or_explicit_local_lab_trust(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.headers = {"X-Remote-User-Id": "admin-user-id"}
        handler.client_address = ("192.0.2.10", 12345)

        self.assertFalse(handler.trusted_worker_control_request())

        handler.client_address = (self.web_server.HOME_ASSISTANT_INGRESS_PROXY_IP, 12345)
        self.assertTrue(handler.trusted_worker_control_request())

        with mock.patch.dict(
            os.environ,
            {"RAINMAPPER_WORKER_WEB_CONTROL_TRUST_LOCAL": "true"},
        ):
            handler.headers = {}
            handler.client_address = ("192.0.2.10", 12345)
            self.assertTrue(handler.trusted_worker_control_request())

    def test_workers_post_generates_visible_one_time_pairing_code(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        with mock.patch.object(
            self.web_server,
            "create_mushroom_worker_pairing",
            return_value={"pairing_code": "ABCD-2345", "expires_in_seconds": 600},
        ):
            redirect = handler.handle_mushroom_workers_post(
                {"worker_action": ["create_worker_pairing"]}
            )

        message, is_error = self.web_server.mushroom_workers_flash()
        self.assertEqual(redirect, "./workers")
        self.assertIn("ABCD-2345", message)
        self.assertIn("10", message)
        self.assertFalse(is_error)

    def test_worker_registry_supports_multiple_workers_and_stale_status(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        base = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "architecture": "arm64",
            "platform": "Darwin",
            "worker_version": "local",
            "status": "idle",
            "job_api": "not_implemented",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }
        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "false"}), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ):
            self.web_server.register_mushroom_worker_heartbeat(
                {**base, "worker_id": "worker_bbbbbbbb", "display_name": "Worker B", "host_name": "Mac-B"},
                now=100,
            )
            self.web_server.register_mushroom_worker_heartbeat(
                {**base, "worker_id": "worker_aaaaaaaa", "display_name": "Worker A", "host_name": "Mac-A"},
                now=110,
            )
            workers = self.web_server.registered_mushroom_worker_statuses(now=114)

        self.assertEqual([worker["payload"]["display_name"] for worker in workers], ["Worker A", "Worker B"])
        self.assertTrue(workers[0]["reachable"])
        self.assertFalse(workers[1]["reachable"])
        self.assertEqual(workers[1]["payload"]["status"], "disconnected")

    def test_worker_is_marked_disconnected_after_five_seconds_without_heartbeat(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        payload = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": "worker_12345678",
            "display_name": "Worker",
            "host_name": "Mac",
            "architecture": "arm64",
            "platform": "Linux",
            "worker_version": "local",
            "status": "idle",
            "job_api": "claim_probe_v0",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }
        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "false"}), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ):
            self.web_server.register_mushroom_worker_heartbeat(payload, now=100)
            before_timeout = self.web_server.registered_mushroom_worker_statuses(now=104.9)
            after_timeout = self.web_server.registered_mushroom_worker_statuses(now=105.1)

        self.assertTrue(before_timeout[0]["reachable"])
        self.assertFalse(after_timeout[0]["reachable"])

    def test_workers_page_disables_external_execution_until_job_api_exists(self) -> None:
        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=[{
                "configured": True,
                "reachable": True,
                "checked_at": "2026-07-19T12:00:00",
                "payload": {
                    "kind": "rainmapper_worker_status",
                    "worker_id": "worker_12345678",
                    "display_name": "M1 personal",
                    "host_name": "macbook-m1-test",
                    "architecture": "arm64",
                    "status": "idle",
                    "paired": True,
                    "job_api": "candidate_rebuild_v0",
                    "worker_version": "local",
                    "capabilities": ["rebuild_v0"],
                    "dataset_cache": {"status": "valid", "file_count": 10, "size_bytes": 6306367027},
                },
            }],
            profiles=[{"species_id": "boletus_pinophilus", "scientific_name": "Boletus pinophilus"}],
            eligible_observation_count=126,
            pending_species_count=3,
            jobs=[],
            pipeline="shared",
            pairing_required=True,
        )

        self.assertIn("Workers and jobs", page)
        self.assertIn("5.87 GiB", page)
        self.assertIn('value="worker:worker_12345678" disabled', page)
        self.assertIn("M1 personal", page)
        self.assertIn("macbook-m1-test", page)
        self.assertIn('value="home_assistant" checked', page)
        self.assertIn("Local worker tests available", page)
        self.assertIn('name="worker_action" value="probe_worker_claim"', page)
        self.assertIn('name="worker_action" value="probe_worker_snapshot_transport"', page)
        self.assertIn("Test input delivery", page)
        self.assertIn('name="worker_action" value="run_worker_candidate_rebuild"', page)
        self.assertIn("Run candidate rebuild", page)
        self.assertIn('class="worker-scope-grid"', page)
        self.assertIn('class="worker-species-field" hidden', page)
        self.assertIn('input[type="radio"]{position:absolute!important;width:1px!important', page)
        self.assertIn("window.location.pathname.replace(/\\/mushrooms\\/workers\\/?$/,'')", page)
        self.assertIn("${appBasePath}/api/mushrooms/workers/status", page)
        self.assertIn('href="./workers">Refresh</a>', page)
        self.assertNotIn("../../api/mushrooms/workers/status", page)
        self.assertIn("window.setTimeout(refresh,2000)", page)
        self.assertIn("data-refresh-signature=", page)
        self.assertIn("replaceRegion(cards,payload.worker_cards_html,payload.worker_cards_signature)", page)
        self.assertIn('id="worker-flash-region"', page)
        self.assertIn("payload.worker_activity_active===false", page)
        self.assertIn("flashRegion.replaceChildren()", page)
        self.assertIn("document.addEventListener('pointerdown'", page)
        self.assertIn("requestController?.abort()", page)
        self.assertNotIn("cards.innerHTML=payload.worker_cards_html", page)
        self.assertIn('id="worker-status-cards"', page)
        self.assertIn('id="worker-recent-jobs"', page)
        self.assertIn('value="create_worker_pairing"', page)
        self.assertIn("Generate pairing code", page)
        self.assertIn('class="worker-toolbar-actions"', page)
        self.assertLess(page.index('class="worker-toolbar-actions"'), page.index("<h1>Workers and jobs</h1>"))
        self.assertNotIn('href="#new-worker-rebuild"', page)
        self.assertNotIn('class="workers-head-meta"', page)
        self.assertIn('.workers-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))', page)
        self.assertIn('.worker-destination-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))', page)
        self.assertIn('class="worker-tools"', page)
        self.assertIn("applyJobSort()", page)
        self.assertNotIn('class="workers-panel worker-pairing-panel"', page)
        self.assertNotIn('class="workers-panel worker-default-panel"', page)
        self.assertIn("Paired", page)
        self.assertIn('value="revoke_worker_pairing"', page)

    def test_worker_status_refresh_payload_renders_disconnected_state(self) -> None:
        worker = {
            "configured": True,
            "reachable": False,
            "checked_at": "2026-07-19T21:04:31+02:00",
            "payload": {
                "worker_id": "worker_12345678",
                "display_name": "M1 personal",
                "host_name": "Mac",
                "status": "disconnected",
                "job_api": "claim_probe_v0",
                "capabilities": ["rebuild_v0"],
                "dataset_cache": {"status": "valid"},
            },
        }
        with mock.patch.object(self.web_server, "registered_mushroom_worker_statuses", return_value=[worker]), mock.patch.object(
            self.web_server, "mushroom_workers_recent_jobs", return_value=[]
        ):
            payload = self.web_server.mushroom_workers_status_refresh_payload()

        self.assertEqual(payload["stale_after_seconds"], 5)
        self.assertIn("Disconnected", payload["worker_cards_html"])
        self.assertNotIn("Test assignment", payload["worker_cards_html"])
        self.assertEqual(payload["worker_last_checks"], {"worker_12345678": "2026-07-19 21:04:31"})
        self.assertEqual(len(payload["worker_cards_signature"]), 64)
        self.assertEqual(len(payload["worker_choices_signature"]), 64)
        self.assertEqual(len(payload["recent_jobs_signature"]), 64)
        self.assertFalse(payload["worker_activity_active"])
        self.assertFalse(payload["flash_update"])

    def test_worker_activity_flash_updates_while_active_and_clears_when_idle(self) -> None:
        active_job = {
            "job_id": "worker_job_active",
            "status": "running",
            "created_at": "2026-07-20T19:00:00+02:00",
        }
        terminal_job = {**active_job, "status": "complete"}
        self.web_server.set_mushroom_workers_flash(
            "Worker job queued.",
            clear_when_idle=True,
        )
        with mock.patch.object(
            self.web_server,
            "registered_mushroom_worker_statuses",
            return_value=[],
        ), mock.patch.object(
            self.web_server,
            "mushroom_workers_recent_jobs",
            return_value=[active_job],
        ), mock.patch.object(
            self.web_server.mushroom_worker_registry,
            "load_registry",
            return_value={"default_executor": "home_assistant", "workers": []},
        ):
            active_payload = self.web_server.mushroom_workers_status_refresh_payload()

        self.assertTrue(active_payload["worker_activity_active"])
        self.assertTrue(active_payload["flash_update"])
        self.assertTrue(active_payload["flash_clear_when_idle"])
        self.assertIn("Worker job queued.", active_payload["flash_html"])

        self.web_server.set_mushroom_workers_flash(
            "Stale worker job message.",
            clear_when_idle=True,
        )
        with mock.patch.object(
            self.web_server,
            "registered_mushroom_worker_statuses",
            return_value=[],
        ), mock.patch.object(
            self.web_server,
            "mushroom_workers_recent_jobs",
            return_value=[terminal_job],
        ), mock.patch.object(
            self.web_server.mushroom_worker_registry,
            "load_registry",
            return_value={"default_executor": "home_assistant", "workers": []},
        ):
            idle_payload = self.web_server.mushroom_workers_status_refresh_payload()

        self.assertFalse(idle_payload["worker_activity_active"])
        self.assertFalse(idle_payload["flash_update"])
        self.assertEqual("", idle_payload["flash_html"])

    def test_non_activity_worker_error_remains_available_when_idle(self) -> None:
        self.assertTrue(
            self.web_server.mushroom_worker_error_tracks_activity(
                {"error": "Equivalent worker job is already active: worker_job_x."}
            )
        )
        self.assertFalse(
            self.web_server.mushroom_worker_error_tracks_activity(
                {"error": "The selected worker is not connected."}
            )
        )
        self.web_server.set_mushroom_workers_flash(
            "Worker preparation failed.",
            error=True,
        )
        with mock.patch.object(
            self.web_server,
            "registered_mushroom_worker_statuses",
            return_value=[],
        ), mock.patch.object(
            self.web_server,
            "mushroom_workers_recent_jobs",
            return_value=[],
        ), mock.patch.object(
            self.web_server.mushroom_worker_registry,
            "load_registry",
            return_value={"default_executor": "home_assistant", "workers": []},
        ):
            payload = self.web_server.mushroom_workers_status_refresh_payload()

        self.assertFalse(payload["worker_activity_active"])
        self.assertTrue(payload["flash_update"])
        self.assertFalse(payload["flash_clear_when_idle"])
        self.assertIn('catalog-alert error', payload["flash_html"])
        self.assertIn("Worker preparation failed.", payload["flash_html"])

    def test_worker_card_refresh_signature_ignores_heartbeat_time_only(self) -> None:
        worker = {
            "configured": True,
            "reachable": True,
            "checked_at": "2026-07-20T18:00:00+02:00",
            "payload": {
                "worker_id": "worker_12345678",
                "display_name": "M1 personal",
                "status": "idle",
                "job_api": "candidate_rebuild_v0",
            },
        }
        later = {**worker, "checked_at": "2026-07-20T18:00:02+02:00"}
        busy = {**later, "payload": {**later["payload"], "status": "busy"}}

        initial_signature = self.web_server.mushroom_workers_ui.worker_cards_refresh_signature([worker])
        later_signature = self.web_server.mushroom_workers_ui.worker_cards_refresh_signature([later])
        busy_signature = self.web_server.mushroom_workers_ui.worker_cards_refresh_signature([busy])

        self.assertEqual(initial_signature, later_signature)
        self.assertNotEqual(initial_signature, busy_signature)

    def test_workers_page_disables_empty_pending_scope_but_keeps_species_selectable(self) -> None:
        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=[],
            profiles=[{"species_id": "boletus_pinophilus", "scientific_name": "Boletus pinophilus"}],
            eligible_observation_count=125,
            pending_species_count=0,
            jobs=[],
            pipeline="legacy",
        )

        self.assertIn('name="scope" value="pending" disabled', page)
        self.assertIn('name="scope" value="species"><span>', page)
        self.assertIn('id="worker-species-id" name="species_id" disabled', page)
        self.assertIn('field.hidden=!show', page)

    def test_workers_page_preselects_species_for_home_assistant(self) -> None:
        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=[],
            profiles=[{"species_id": "boletus_pinophilus", "scientific_name": "Boletus pinophilus"}],
            eligible_observation_count=125,
            pending_species_count=2,
            jobs=[],
            pipeline="shared",
            selected_scope="species",
            selected_species_id="boletus_pinophilus",
        )

        self.assertIn('name="scope" value="species" checked', page)
        self.assertIn('class="worker-species-field"><label', page)
        self.assertIn('name="species_id"><option value="boletus_pinophilus" selected', page)
        self.assertIn('value="home_assistant" checked', page)

    def test_workers_page_uses_operational_default_worker_for_partial_rebuild(self) -> None:
        worker = {
            "configured": True,
            "reachable": True,
            "checked_at": "2026-07-20T12:00:00",
            "payload": {
                "worker_id": "worker_12345678",
                "display_name": "M1 personal",
                "host_name": "macbook-m1-test",
                "architecture": "arm64",
                "status": "idle",
                "paired": True,
                "job_api": "candidate_rebuild_v0",
                "worker_version": "local",
                "capabilities": ["rebuild_v0"],
                "dataset_cache": {"status": "valid"},
            },
        }
        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=[worker],
            profiles=[{"species_id": "boletus_pinophilus", "scientific_name": "Boletus pinophilus"}],
            eligible_observation_count=125,
            pending_species_count=2,
            jobs=[],
            pipeline="shared",
            operational_enabled=True,
            default_executor="worker:worker_12345678",
        )

        self.assertIn('name="executor" value="worker:worker_12345678" checked', page)
        self.assertNotIn('value="home_assistant" checked', page)
        self.assertIn("Default rebuild executor", page)
        self.assertIn("Default", page)
        self.assertNotIn('class="catalog-alert error worker-default-issue"', page)

        species_page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=[worker],
            profiles=[{"species_id": "boletus_pinophilus", "scientific_name": "Boletus pinophilus"}],
            eligible_observation_count=125,
            pending_species_count=2,
            jobs=[],
            pipeline="shared",
            operational_enabled=True,
            default_executor="worker:worker_12345678",
            selected_scope="species",
            selected_species_id="boletus_pinophilus",
        )

        self.assertIn('name="scope" value="species" checked', species_page)
        self.assertNotIn("does not yet support this rebuild scope", species_page)
        self.assertIn('name="executor" value="worker:worker_12345678" checked', species_page)
        self.assertNotIn('value="home_assistant" checked', species_page)
        self.assertIn('name="species_id"><option value="boletus_pinophilus" selected', species_page)
        self.assertNotIn('class="primary" type="submit" disabled', species_page)

    def test_workers_page_does_not_fall_back_silently_when_default_worker_is_offline(self) -> None:
        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=[{
                "configured": True,
                "reachable": False,
                "payload": {
                    "worker_id": "worker_12345678",
                    "display_name": "M1 personal",
                    "status": "disconnected",
                    "paired": True,
                    "job_api": "candidate_rebuild_v0",
                },
            }],
            profiles=[],
            eligible_observation_count=125,
            pending_species_count=2,
            jobs=[],
            pipeline="shared",
            operational_enabled=True,
            default_executor="worker:worker_12345678",
        )

        self.assertIn("default worker M1 personal is disconnected", page)
        self.assertNotIn('value="home_assistant" checked', page)
        self.assertIn('class="primary" type="submit" disabled', page)

    def test_workers_page_renders_multiple_named_workers_and_destinations(self) -> None:
        worker_statuses = []
        for worker_id, display_name, host_name in (
            ("worker_aaaaaaaa", "M1 personal", "macbook-m1"),
            ("worker_bbbbbbbb", "Mac del trabajo", "macbook-work"),
        ):
            worker_statuses.append(
                {
                    "configured": True,
                    "reachable": True,
                    "checked_at": "2026-07-19T12:00:00",
                    "payload": {
                        "worker_id": worker_id,
                        "display_name": display_name,
                        "host_name": host_name,
                        "architecture": "arm64",
                        "status": "idle",
                        "job_api": "not_implemented",
                        "worker_version": "local",
                        "capabilities": ["rebuild_v0"],
                        "dataset_cache": {"status": "valid"},
                    },
                }
            )

        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=worker_statuses,
            profiles=[],
            eligible_observation_count=0,
            pending_species_count=0,
            jobs=[],
            pipeline="legacy",
        )

        self.assertIn("M1 personal", page)
        self.assertIn("Mac del trabajo", page)
        self.assertIn('value="worker:worker_aaaaaaaa" disabled', page)
        self.assertIn('value="worker:worker_bbbbbbbb" disabled', page)

    def test_workers_post_reuses_home_assistant_rebuild_action(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured: dict[str, object] = {}

        def handle_profiles(form: dict[str, list[str]]) -> str:
            captured.update(form)
            self.web_server.set_mushroom_profiles_flash("Global Modelo v0 rebuild started for 126 observation(s).")
            return "?section=evidence&rebuild_job=job_123"

        handler.handle_mushroom_profiles_post = handle_profiles
        redirect = handler.handle_mushroom_workers_post(
            {"worker_action": ["start_rebuild"], "executor": ["home_assistant"], "scope": ["all"]}
        )

        self.assertEqual(captured["profile_action"], ["rebuild_learned_model_v0_all"])
        self.assertEqual(redirect, "./workers?rebuild_job=job_123")
        message, is_error = self.web_server.mushroom_workers_flash()
        self.assertIn("rebuild started", message)
        self.assertFalse(is_error)

    def test_workers_post_persists_registered_default_executor(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        worker = {
            "configured": True,
            "reachable": False,
            "payload": {
                "worker_id": "worker_12345678",
                "display_name": "M1 personal",
            },
        }
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        with mock.patch.object(
            self.web_server,
            "mushroom_worker_registry_path",
            return_value=registry_path,
        ), mock.patch.object(
            self.web_server,
            "registered_mushroom_worker_statuses",
            return_value=[worker],
        ):
            redirect = handler.handle_mushroom_workers_post({
                "worker_action": ["set_default_executor"],
                "default_executor": ["worker:worker_12345678"],
            })

        self.assertEqual(redirect, "./workers")
        self.assertEqual(
            self.web_server.mushroom_worker_registry.load_registry(registry_path)["default_executor"],
            "worker:worker_12345678",
        )
        message, is_error = self.web_server.mushroom_workers_flash()
        self.assertIn("M1 personal", message)
        self.assertFalse(is_error)

    def test_workers_post_rejects_missing_executor_without_silent_ha_fallback(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.handle_mushroom_profiles_post = mock.Mock()

        redirect = handler.handle_mushroom_workers_post({
            "worker_action": ["start_rebuild"],
            "scope": ["all"],
        })

        self.assertEqual(redirect, "./workers")
        handler.handle_mushroom_profiles_post.assert_not_called()
        message, is_error = self.web_server.mushroom_workers_flash()
        self.assertIn("Choose Home Assistant or another available compatible destination", message)
        self.assertTrue(is_error)

    def test_worker_probe_is_queued_for_exact_live_worker_and_claimed_once(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        jobs_path = Path(self.temp_dir.name) / "mushroom_worker_jobs.json"
        heartbeat = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": "worker_12345678",
            "display_name": "M1 personal",
            "host_name": "macbook-m1-test",
            "architecture": "arm64",
            "platform": "Linux",
            "worker_version": "local",
            "status": "idle",
            "job_api": "claim_probe_v0",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "false"}), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ), mock.patch.object(self.web_server, "mushroom_worker_jobs_path", return_value=jobs_path):
            self.web_server.register_mushroom_worker_heartbeat(heartbeat)
            redirect = handler.handle_mushroom_workers_post(
                {"worker_action": ["probe_worker_claim"], "worker_id": ["worker_12345678"]}
            )
            wrong_status, wrong = self.web_server.claim_mushroom_worker_job({"worker_id": "worker_abcdefgh"})
            claim_status, claimed = self.web_server.claim_mushroom_worker_job({"worker_id": "worker_12345678"})
            second_status, second = self.web_server.claim_mushroom_worker_job({"worker_id": "worker_12345678"})

        self.assertEqual(redirect, "./workers")
        self.assertEqual(wrong_status, 200)
        self.assertIsNone(wrong["job"])
        self.assertEqual(claim_status, 200)
        self.assertEqual(claimed["job"]["status"], "claimed")
        self.assertEqual(second_status, 200)
        self.assertIsNone(second["job"])
        message, is_error = self.web_server.mushroom_workers_flash()
        self.assertIn("M1 personal", message)
        self.assertFalse(is_error)

    def test_snapshot_transport_probe_is_queued_with_immutable_bundle_contract(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        jobs_path = Path(self.temp_dir.name) / "mushroom_worker_jobs.json"
        bundle_root = Path(self.temp_dir.name) / "bundles"
        heartbeat = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": "worker_12345678",
            "display_name": "M1 personal",
            "host_name": "macbook-m1-test",
            "architecture": "arm64",
            "platform": "Linux",
            "worker_version": "local",
            "status": "idle",
            "job_api": "snapshot_transport_v0",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }

        def bundle_metadata(_root: Path, **kwargs: object) -> dict[str, object]:
            job_id = str(kwargs["job_id"])
            return {
                "schema_version": "0.1",
                "kind": "rainmapper_worker_input_bundle",
                "job_id": job_id,
                "job_spec_id": "sha256:" + "a" * 64,
                "snapshot_id": "sha256:" + "b" * 64,
                "input_file_count": 7,
                "input_size_bytes": 12345,
            }

        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "false"}), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ), mock.patch.object(
            self.web_server, "mushroom_worker_jobs_path", return_value=jobs_path
        ), mock.patch.object(
            self.web_server, "mushroom_worker_input_bundles_path", return_value=bundle_root
        ), mock.patch.object(
            self.web_server.mushroom_worker_transport,
            "prepare_coordinator_bundle",
            side_effect=bundle_metadata,
        ) as prepare_bundle:
            self.web_server.register_mushroom_worker_heartbeat(heartbeat)
            status, response = self.web_server.create_mushroom_worker_snapshot_transport_probe(
                "worker_12345678"
            )
            duplicate_status, duplicate = self.web_server.create_mushroom_worker_snapshot_transport_probe(
                "worker_12345678"
            )
            claim_status, claimed = self.web_server.claim_mushroom_worker_job(
                {"worker_id": "worker_12345678"}
            )
            start_status, _started = self.web_server.start_claimed_mushroom_worker_job(
                {
                    "job_id": claimed["job"]["job_id"],
                    "worker_id": "worker_12345678",
                    "claim_token": claimed["job"]["claim_token"],
                }
            )
            progress_status, progressed = self.web_server.progress_mushroom_worker_job(
                {
                    "job_id": claimed["job"]["job_id"],
                    "worker_id": "worker_12345678",
                    "claim_token": claimed["job"]["claim_token"],
                    "phase": "Downloading immutable inputs",
                    "message": "Verified input file 3/7.",
                    "overall_percent": 55,
                }
            )

        self.assertEqual(status, 201)
        self.assertEqual(duplicate_status, 409)
        self.assertIn("already active", duplicate["error"])
        self.assertEqual(prepare_bundle.call_count, 1)
        self.assertEqual(response["job"]["job_type"], "worker_snapshot_transport_probe")
        self.assertEqual(claim_status, 200)
        self.assertEqual(claimed["job"]["input_bundle"]["endpoint"], "/api/mushrooms/workers/jobs/input")
        self.assertEqual(
            claimed["job"]["input_bundle"]["dataset_endpoint"],
            "/api/mushrooms/workers/jobs/dataset",
        )
        self.assertEqual(start_status, 200)
        self.assertEqual(progress_status, 200)
        self.assertEqual(progressed["job"]["overall_percent"], 55)

    def test_snapshot_transport_start_returns_before_background_preparation(self) -> None:
        callbacks: list[object] = []

        class DeferredThread:
            def __init__(self, *, target: object, **_kwargs: object) -> None:
                self.target = target

            def start(self) -> None:
                callbacks.append(self.target)

        created = {
            "job": {
                "target_display_name": "M1 personal",
            }
        }
        try:
            with mock.patch.object(
                self.web_server.threading,
                "Thread",
                side_effect=lambda **kwargs: DeferredThread(**kwargs),
            ), mock.patch.object(
                self.web_server,
                "create_mushroom_worker_snapshot_transport_probe",
                return_value=(201, created),
            ) as create_probe:
                status, response = self.web_server.start_mushroom_worker_snapshot_transport_probe(
                    "worker_12345678"
                )
                busy_status, busy = self.web_server.start_mushroom_worker_snapshot_transport_probe(
                    "worker_12345678"
                )
                self.assertEqual(status, 202)
                self.assertTrue(response["preparing"])
                self.assertEqual(busy_status, 409)
                self.assertIn("already being prepared", busy["error"])
                self.assertEqual(len(callbacks), 1)
                callbacks[0]()  # type: ignore[operator]
                create_probe.assert_called_once_with(
                    "worker_12345678",
                    _preparation_lock_acquired=True,
                )
        finally:
            if self.web_server.MUSHROOM_WORKER_BUNDLE_PREPARATION_LOCK.locked():
                self.web_server.MUSHROOM_WORKER_BUNDLE_PREPARATION_LOCK.release()

        message, is_error = self.web_server.mushroom_workers_flash()
        self.assertIn("M1 personal", message)
        self.assertFalse(is_error)

    def test_candidate_rebuild_upload_is_claim_bound_and_finished_from_trusted_verification(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        jobs_path = Path(self.temp_dir.name) / "mushroom_worker_jobs.json"
        bundle_root = Path(self.temp_dir.name) / "bundles"
        result_root = Path(self.temp_dir.name) / "results"
        heartbeat = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": "worker_12345678",
            "display_name": "M1 personal",
            "host_name": "macbook-m1-test",
            "architecture": "arm64",
            "platform": "Linux",
            "worker_version": "local",
            "status": "idle",
            "job_api": "candidate_rebuild_v0",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }

        def bundle_metadata(_root: Path, **kwargs: object) -> dict[str, object]:
            job_id = str(kwargs["job_id"])
            return {
                "schema_version": "0.1",
                "kind": "rainmapper_worker_input_bundle",
                "job_id": job_id,
                "job_spec_id": "sha256:" + "a" * 64,
                "snapshot_id": "sha256:" + "b" * 64,
                "input_file_count": 7,
                "input_size_bytes": 12345,
            }

        candidate = {
            "status": "verified",
            "result_manifest_id": "sha256:" + "d" * 64,
            "verified_artifacts": 9,
            "comparison_status": "equivalent",
        }
        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "false"}), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ), mock.patch.object(
            self.web_server, "mushroom_worker_jobs_path", return_value=jobs_path
        ), mock.patch.object(
            self.web_server, "mushroom_worker_input_bundles_path", return_value=bundle_root
        ), mock.patch.object(
            self.web_server, "mushroom_worker_candidate_results_path", return_value=result_root
        ), mock.patch.object(
            self.web_server.mushroom_worker_transport,
            "prepare_coordinator_bundle",
            side_effect=bundle_metadata,
        ), mock.patch.object(
            self.web_server.mushroom_worker_results,
            "receive_result_file",
            return_value={"status": "artifact_received"},
        ), mock.patch.object(
            self.web_server.mushroom_worker_results,
            "finalize_candidate_result",
            return_value=candidate,
        ), mock.patch.object(
            self.web_server.mushroom_worker_results,
            "load_final_candidate",
            return_value=candidate,
        ), mock.patch.object(
            self.web_server.mushroom_rebuild_contracts,
            "load_job_spec",
            return_value={"dataset_requirements": [{"fingerprint": "sha256:" + "c" * 64}]},
        ):
            self.web_server.register_mushroom_worker_heartbeat(heartbeat)
            create_status, created = self.web_server.create_mushroom_worker_candidate_rebuild(
                "worker_12345678"
            )
            claim_status, claimed = self.web_server.claim_mushroom_worker_job(
                {"worker_id": "worker_12345678"}
            )
            claim_token = claimed["job"]["claim_token"]
            job_id = created["job"]["job_id"]
            start_status, _started = self.web_server.start_claimed_mushroom_worker_job(
                {"job_id": job_id, "worker_id": "worker_12345678", "claim_token": claim_token}
            )
            rejected_status, _rejected = self.web_server.receive_mushroom_worker_result_file(
                job_id=job_id,
                logical_path="result_manifest.json",
                content=b"{}",
                worker_id="worker_12345678",
                claim_token="wrong-claim",
                auth_token="",
            )
            upload_status, _uploaded = self.web_server.receive_mushroom_worker_result_file(
                job_id=job_id,
                logical_path="result_manifest.json",
                content=b"{}",
                worker_id="worker_12345678",
                claim_token=claim_token,
                auth_token="",
            )
            complete_status, completed = self.web_server.complete_mushroom_worker_candidate_result(
                {"job_id": job_id, "worker_id": "worker_12345678", "claim_token": claim_token},
                auth_token="",
            )
            finish_status, finished = self.web_server.finish_mushroom_worker_job(
                {
                    "job_id": job_id,
                    "worker_id": "worker_12345678",
                    "claim_token": claim_token,
                    "status": "complete",
                    "result": {"comparison_status": "different"},
                },
                auth_token="",
            )

        self.assertEqual(create_status, 201)
        self.assertEqual(claim_status, 200)
        self.assertEqual(start_status, 200)
        self.assertEqual(rejected_status, 409)
        self.assertEqual(upload_status, 200)
        self.assertEqual(complete_status, 200)
        self.assertEqual(completed["verification"]["comparison_status"], "equivalent")
        self.assertEqual(finish_status, 200)
        self.assertEqual(finished["job"]["phase"], "Candidate result verified")
        self.assertEqual(finished["job"]["result"]["comparison_status"], "equivalent")

    def test_worker_dataset_download_is_authenticated_and_claim_bound(self) -> None:
        dataset_file = Path(self.temp_dir.name) / "dataset.dat"
        dataset_file.write_bytes(b"dataset")
        metadata = {
            "dataset_id": "mushroom_gis_v0",
            "dataset_fingerprint": "sha256:" + "a" * 64,
            "dataset_file_count": 1,
            "dataset_size_bytes": 7,
        }
        job = {"input_bundle": dict(metadata)}
        with mock.patch.dict(
            os.environ,
            {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "true"},
        ), mock.patch.object(
            self.web_server,
            "authenticate_mushroom_worker",
            side_effect=lambda worker_id, token: worker_id == "worker_12345678" and token == "secret",
        ), mock.patch.object(
            self.web_server,
            "mushroom_worker_jobs_path",
            return_value=Path(self.temp_dir.name) / "jobs.json",
        ), mock.patch.object(
            self.web_server.mushroom_worker_jobs,
            "authorize_input_download",
            return_value=job,
        ) as authorize, mock.patch.object(
            self.web_server.mushroom_worker_transport,
            "load_coordinator_bundle",
            return_value=metadata,
        ), mock.patch.object(
            self.web_server.mushroom_worker_transport,
            "resolve_coordinator_dataset_file",
            return_value=dataset_file,
        ):
            rejected_status, _rejected = self.web_server.resolve_mushroom_worker_dataset_download(
                job_id="worker_job_dataset123",
                dataset_id="mushroom_gis_v0",
                fingerprint=metadata["dataset_fingerprint"],
                logical_path="dataset.dat",
                worker_id="worker_12345678",
                claim_token="claim",
                auth_token="wrong",
            )
            accepted_status, accepted = self.web_server.resolve_mushroom_worker_dataset_download(
                job_id="worker_job_dataset123",
                dataset_id="mushroom_gis_v0",
                fingerprint=metadata["dataset_fingerprint"],
                logical_path="dataset.dat",
                worker_id="worker_12345678",
                claim_token="claim",
                auth_token="secret",
            )

        self.assertEqual(rejected_status, 401)
        self.assertEqual(accepted_status, 200)
        self.assertEqual(accepted, dataset_file)
        authorize.assert_called_once_with(
            mock.ANY,
            job_id="worker_job_dataset123",
            worker_id="worker_12345678",
            claim_token="claim",
        )

    def test_worker_probe_lifecycle_reassigns_only_before_start_and_cancels_cooperatively(self) -> None:
        registry_path = Path(self.temp_dir.name) / "mushroom_workers.json"
        jobs_path = Path(self.temp_dir.name) / "mushroom_worker_jobs.json"
        heartbeat = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "host_name": "Mac",
            "architecture": "arm64",
            "platform": "Linux",
            "worker_version": "local",
            "status": "idle",
            "job_api": "lifecycle_probe_v0",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }
        with mock.patch.dict(os.environ, {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "false"}), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ), mock.patch.object(self.web_server, "mushroom_worker_jobs_path", return_value=jobs_path):
            self.web_server.register_mushroom_worker_heartbeat(
                {**heartbeat, "worker_id": "worker_aaaaaaaa", "display_name": "Worker A"}
            )
            self.web_server.register_mushroom_worker_heartbeat(
                {**heartbeat, "worker_id": "worker_bbbbbbbb", "display_name": "Worker B"}
            )
            create_status, created = self.web_server.create_mushroom_worker_claim_probe("worker_aaaaaaaa")
            duplicate_status, duplicate = self.web_server.create_mushroom_worker_claim_probe("worker_bbbbbbbb")
            claim_a_status, claimed_a = self.web_server.claim_mushroom_worker_job(
                {"worker_id": "worker_aaaaaaaa"}
            )
            reassign_status, reassigned = self.web_server.reassign_mushroom_worker_job(
                str(created["job"]["job_id"]), "worker_bbbbbbbb"
            )
            old_start_status, _old_start = self.web_server.start_claimed_mushroom_worker_job(
                {
                    "job_id": created["job"]["job_id"],
                    "worker_id": "worker_aaaaaaaa",
                    "claim_token": claimed_a["job"]["claim_token"],
                }
            )
            claim_b_status, claimed_b = self.web_server.claim_mushroom_worker_job(
                {"worker_id": "worker_bbbbbbbb"}
            )
            start_status, started = self.web_server.start_claimed_mushroom_worker_job(
                {
                    "job_id": created["job"]["job_id"],
                    "worker_id": "worker_bbbbbbbb",
                    "claim_token": claimed_b["job"]["claim_token"],
                }
            )
            late_reassign_status, _late_reassign = self.web_server.reassign_mushroom_worker_job(
                str(created["job"]["job_id"]), "worker_aaaaaaaa"
            )
            cancel_status, cancelled = self.web_server.cancel_mushroom_worker_job(
                str(created["job"]["job_id"])
            )
            force_status, forced = self.web_server.cancel_mushroom_worker_job(
                str(created["job"]["job_id"]), force=True
            )
            control_status, control = self.web_server.control_mushroom_worker_job(
                {
                    "job_id": created["job"]["job_id"],
                    "worker_id": "worker_bbbbbbbb",
                    "claim_token": claimed_b["job"]["claim_token"],
                }
            )
            finish_status, finished = self.web_server.finish_mushroom_worker_job(
                {
                    "job_id": created["job"]["job_id"],
                    "worker_id": "worker_bbbbbbbb",
                    "claim_token": claimed_b["job"]["claim_token"],
                    "status": "cancelled",
                }
            )

        self.assertEqual(create_status, 201)
        self.assertEqual(duplicate_status, 409)
        self.assertIn("already active", duplicate["error"])
        self.assertEqual(claim_a_status, 200)
        self.assertEqual(reassign_status, 200)
        self.assertEqual(reassigned["job"]["target_worker_id"], "worker_bbbbbbbb")
        self.assertEqual(old_start_status, 409)
        self.assertEqual(claim_b_status, 200)
        self.assertEqual(start_status, 200)
        self.assertEqual(started["job"]["status"], "running")
        self.assertEqual(late_reassign_status, 409)
        self.assertEqual(cancel_status, 200)
        self.assertEqual(cancelled["job"]["status"], "cancel_requested")
        self.assertEqual(force_status, 200)
        self.assertEqual(forced["job"]["cancel_mode"], "force")
        self.assertEqual(control_status, 200)
        self.assertTrue(control["cancel_requested"])
        self.assertTrue(control["force_cancel_requested"])
        self.assertEqual(finish_status, 200)
        self.assertEqual(finished["job"]["status"], "cancelled")

    def test_workers_page_offers_cancel_and_safe_reassignment_for_unstarted_probe(self) -> None:
        workers = [
            {
                "configured": True,
                "reachable": True,
                "payload": {
                    "worker_id": worker_id,
                    "display_name": display_name,
                    "host_name": display_name,
                    "job_api": "lifecycle_probe_v0",
                    "status": "idle",
                    "dataset_cache": {"status": "valid"},
                },
            }
            for worker_id, display_name in (
                ("worker_aaaaaaaa", "Worker A"),
                ("worker_bbbbbbbb", "Worker B"),
            )
        ]
        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=workers,
            profiles=[],
            eligible_observation_count=0,
            pending_species_count=0,
            jobs=[{
                "job_id": "worker_job_12345678",
                "job_type": "worker_claim_probe",
                "target_worker_id": "worker_aaaaaaaa",
                "worker_display_name": "Worker A",
                "status": "claimed",
                "started_at": "",
            }],
            pipeline="shared",
        )

        self.assertIn('value="cancel_worker_job"', page)
        self.assertIn('value="reassign_worker_job"', page)
        self.assertIn('<option value="worker_bbbbbbbb">Worker B</option>', page)
        self.assertNotIn('<option value="worker_aaaaaaaa">Worker A</option>', page)

        running_jobs = self.web_server.mushroom_workers_ui.render_recent_jobs([{
            "job_id": "worker_job_abcdefgh",
            "job_type": "worker_claim_probe",
            "target_worker_id": "worker_aaaaaaaa",
            "worker_display_name": "Worker A",
            "status": "running",
            "started_at": "2026-07-19T12:00:00+00:00",
        }], workers)
        self.assertIn('value="force_cancel_worker_job"', running_jobs)
        self.assertIn("Force cancellation", running_jobs)

    def test_workers_recent_jobs_show_local_date_time_and_duration(self) -> None:
        jobs_path = Path(self.temp_dir.name) / "worker-jobs.json"
        with mock.patch.object(self.web_server, "mushroom_worker_jobs_path", return_value=jobs_path):
            self.web_server.mushroom_worker_jobs.create_claim_probe(
                jobs_path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                job_id="worker_job_datetime",
                created_at="2026-07-19T22:20:57+00:00",
            )
            claimed = self.web_server.mushroom_worker_jobs.claim_next(
                jobs_path,
                worker_id="worker_aaaaaaaa",
                claimed_at="2026-07-19T22:20:57+00:00",
                claim_token="claim-token",
            )
            self.web_server.mushroom_worker_jobs.start_job(
                jobs_path,
                job_id="worker_job_datetime",
                worker_id="worker_aaaaaaaa",
                claim_token=str(claimed["claim_token"]),
                started_at="2026-07-19T22:20:58+00:00",
            )
            self.web_server.mushroom_worker_jobs.finish_job(
                jobs_path,
                job_id="worker_job_datetime",
                worker_id="worker_aaaaaaaa",
                claim_token=str(claimed["claim_token"]),
                status="complete",
                finished_at="2026-07-19T22:21:45+00:00",
            )
            with mock.patch.object(
                self.web_server,
                "get_timezone",
                return_value=self.web_server.ZoneInfo("Europe/Madrid"),
            ):
                jobs = self.web_server.mushroom_workers_recent_jobs()

        self.assertEqual(jobs[0]["date_time"], "20/07/2026 00:20:57")
        self.assertEqual(jobs[0]["elapsed"], "47s")
        self.assertEqual(jobs[0]["elapsed_seconds"], 47)
        self.assertGreater(jobs[0]["sort_timestamp"], 0)
        rendered = self.web_server.mushroom_workers_ui.render_recent_jobs(jobs)
        self.assertIn("Date and time", rendered)
        self.assertIn("20/07/2026 00:20:57", rendered)
        self.assertIn("47s", rendered)
        self.assertIn('data-sortable-worker-jobs', rendered)
        self.assertEqual(rendered.count('data-worker-sort-column='), 10)
        self.assertIn('data-worker-sort-column="1" data-worker-sort-type="time"', rendered)
        self.assertIn('aria-sort="descending"', rendered)

    def test_workers_recent_jobs_sort_mixed_timezones_by_instant(self) -> None:
        local_started = "2026-07-20T21:08:09+02:00"
        local_timestamp = self.web_server.datetime.fromisoformat(local_started).timestamp()
        local_job = {
            "job_id": "Ercotzq4lmji",
            "status": "complete",
            "scope": "species",
            "phase": "Model learned v0",
            "overall_percent": 100,
            "started_at": local_started,
            "started_at_ts": local_timestamp,
            "finished_at": "2026-07-20T21:10:39+02:00",
            "finished_at_ts": local_timestamp + 150,
        }
        external_job = {
            "job_id": "worker_job_newer",
            "job_type": "worker_candidate_rebuild",
            "target_display_name": "M1 Personal",
            "status": "cancelled",
            "scope": "species: amanita_caesarea",
            "phase": "Cancelled",
            "overall_percent": 75,
            "created_at": "2026-07-20T19:10:51+00:00",
            "started_at": "2026-07-20T19:10:51+00:00",
            "finished_at": "2026-07-20T19:11:50+00:00",
        }
        with mock.patch.object(
            self.web_server, "cleanup_mushroom_rebuild_jobs"
        ), mock.patch.dict(
            self.web_server.MUSHROOM_REBUILD_JOBS,
            {"Ercotzq4lmji": local_job},
            clear=True,
        ), mock.patch.object(
            self.web_server.mushroom_worker_jobs,
            "recent_jobs",
            return_value=[external_job],
        ):
            jobs = self.web_server.mushroom_workers_recent_jobs()

        self.assertEqual([job["job_id"] for job in jobs], ["worker_job_newer", "Ercotzq4lmji"])
        rendered = self.web_server.mushroom_workers_ui.render_recent_jobs(jobs)
        self.assertIn(">Local HA</strong>", rendered)
        self.assertNotIn(">Ercotzq4lmji</strong>", rendered)

    def test_worker_promotion_runs_in_background_and_persists_progress(self) -> None:
        jobs_path = Path(self.temp_dir.name) / "worker-promotion-jobs.json"
        input_bundle = {
            "job_id": "worker_job_promote123",
            "job_spec_id": "sha256:" + "a" * 64,
            "snapshot_id": "sha256:" + "b" * 64,
            "input_file_count": 7,
            "input_size_bytes": 1234,
        }
        created = self.web_server.mushroom_worker_jobs.create_candidate_rebuild(
            jobs_path,
            worker_id="worker_aaaaaaaa",
            worker_display_name="M1 personal",
            input_bundle=input_bundle,
            job_id="worker_job_promote123",
            promotion_eligible=True,
        )
        claimed = self.web_server.mushroom_worker_jobs.claim_next(
            jobs_path,
            worker_id="worker_aaaaaaaa",
            claim_token="claim-secret",
        )
        self.web_server.mushroom_worker_jobs.start_job(
            jobs_path,
            job_id=created["job_id"],
            worker_id="worker_aaaaaaaa",
            claim_token=str(claimed["claim_token"]),
        )
        self.web_server.mushroom_worker_jobs.finish_job(
            jobs_path,
            job_id=created["job_id"],
            worker_id="worker_aaaaaaaa",
            claim_token=str(claimed["claim_token"]),
            status="complete",
            result={
                "verification_status": "verified",
                "snapshot_id": input_bundle["snapshot_id"],
                "job_spec_id": input_bundle["job_spec_id"],
                "input_file_count": 7,
                "input_size_bytes": 1234,
                "dataset_fingerprint": "sha256:" + "c" * 64,
                "result_manifest_id": "sha256:" + "d" * 64,
                "verified_artifacts": 9,
                "comparison_status": "equivalent",
            },
        )

        def promote(*_args, **kwargs):
            kwargs["progress_callback"](
                58,
                "Validating live inputs (9/17)",
                "Checking authoritative GIS inputs.",
            )
            return {"artifact_count": 9}

        with mock.patch.dict(
            os.environ,
            {
                "RAINMAPPER_WORKER_API_ENABLED": "true",
                "RAINMAPPER_WORKER_AUTH_REQUIRED": "true",
                "RAINMAPPER_WORKER_OPERATIONAL_ENABLED": "true",
            },
        ), mock.patch.object(
            self.web_server, "mushroom_worker_jobs_path", return_value=jobs_path
        ), mock.patch.object(
            self.web_server.threading, "Thread"
        ) as thread_class, mock.patch.object(
            self.web_server.mushroom_worker_results,
            "promote_verified_candidate",
            side_effect=promote,
        ), mock.patch.object(
            self.web_server.mushroom_model_state,
            "clear_all_pending",
        ):
            status, response = self.web_server.promote_mushroom_worker_candidate(
                created["job_id"]
            )
            duplicate_status, duplicate = self.web_server.promote_mushroom_worker_candidate(
                created["job_id"]
            )
            promoting = self.web_server.mushroom_worker_jobs.get_job(
                jobs_path,
                job_id=created["job_id"],
            )
            target = thread_class.call_args.kwargs["target"]
            args = thread_class.call_args.kwargs["args"]
            target(*args)

        promoted = self.web_server.mushroom_worker_jobs.get_job(
            jobs_path,
            job_id=created["job_id"],
        )
        self.assertEqual(status, 202)
        self.assertTrue(response["promoting"])
        self.assertEqual(duplicate_status, 409)
        self.assertIn("already running", duplicate["error"])
        self.assertEqual(promoting["promotion_status"], "promoting")
        self.assertEqual(promoted["promotion_status"], "promoted")
        self.assertEqual(promoted["promotion_percent"], 100)
        thread_class.return_value.start.assert_called_once_with()

    def test_workers_page_shows_promotion_progress_and_hides_duplicate_action(self) -> None:
        rendered = self.web_server.mushroom_workers_ui.render_recent_jobs(
            [{
                "job_id": "worker_job_promoting",
                "job_type": "worker_candidate_rebuild",
                "worker_display_name": "M1 personal",
                "status": "complete",
                "scope": "all eligible (candidate)",
                "phase": "Validating live inputs (9/17)",
                "overall_percent": 100,
                "promotion_eligible": True,
                "promotion_status": "promoting",
                "promotion_percent": 58,
                "elapsed": "49s",
            }],
            operational_enabled=True,
        )

        self.assertIn('value="58"', rendered)
        self.assertIn("58%", rendered)
        self.assertIn("Promoting", rendered)
        self.assertNotIn('value="promote_worker_candidate"', rendered)

    def test_workers_page_discards_terminal_unpromoted_candidate_through_modal(self) -> None:
        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=[],
            profiles=[],
            eligible_observation_count=0,
            pending_species_count=0,
            jobs=[{
                "job_id": "worker_job_discard123",
                "job_type": "worker_candidate_rebuild",
                "worker_display_name": "M1 personal",
                "status": "complete",
                "scope": "Amanita caesarea",
                "phase": "Candidate result verified",
                "overall_percent": 100,
                "promotion_eligible": True,
                "promotion_status": "",
                "elapsed": "49s",
            }],
            pipeline="shared",
            operational_enabled=True,
        )

        self.assertIn("Discard worker candidate?", page)
        self.assertIn("Amanita caesarea", page)
        self.assertIn("data-discard-worker-candidate", page)
        self.assertIn('name="worker_action" value="discard_worker_candidate"', page)
        self.assertIn("showModal", page)

        interrupted = self.web_server.mushroom_workers_ui.render_recent_jobs(
            [{
                "job_id": "worker_job_interrupted",
                "job_type": "worker_candidate_rebuild",
                "worker_display_name": "M1 personal",
                "status": "complete",
                "scope": "Amanita caesarea",
                "promotion_status": "promoting",
                "promotion_active": False,
                "overall_percent": 100,
            }],
            operational_enabled=True,
        )
        self.assertIn("Promotion interrupted", interrupted)
        self.assertIn("data-discard-worker-candidate", interrupted)

    def test_discard_candidate_removes_coordinator_files_then_worker_ack_removes_job(self) -> None:
        jobs_path = Path(self.temp_dir.name) / "discard-worker-jobs.json"
        registry_path = Path(self.temp_dir.name) / "discard-workers.json"
        job_id = "worker_job_discard123"
        created = self.web_server.mushroom_worker_jobs.create_candidate_rebuild(
            jobs_path,
            worker_id="worker_aaaaaaaa",
            worker_display_name="M1 personal",
            input_bundle={
                "job_id": job_id,
                "job_spec_id": "sha256:" + "a" * 64,
                "snapshot_id": "sha256:" + "b" * 64,
                "input_file_count": 7,
                "input_size_bytes": 1234,
            },
            job_id=job_id,
            promotion_eligible=True,
        )
        claimed = self.web_server.mushroom_worker_jobs.claim_next(
            jobs_path,
            worker_id="worker_aaaaaaaa",
            claim_token="claim-secret",
        )
        self.web_server.mushroom_worker_jobs.start_job(
            jobs_path,
            job_id=created["job_id"],
            worker_id="worker_aaaaaaaa",
            claim_token=str(claimed["claim_token"]),
        )
        self.web_server.mushroom_worker_jobs.finish_job(
            jobs_path,
            job_id=created["job_id"],
            worker_id="worker_aaaaaaaa",
            claim_token=str(claimed["claim_token"]),
            status="failed",
            error="expected test failure",
        )
        heartbeat = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": "worker_aaaaaaaa",
            "display_name": "M1 personal",
            "host_name": "macbook-m1-test",
            "architecture": "arm64",
            "platform": "Darwin",
            "worker_version": "local",
            "status": "idle",
            "job_api": "candidate_rebuild_v0",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }
        with mock.patch.dict(
            os.environ,
            {"RAINMAPPER_WORKER_API_ENABLED": "true", "RAINMAPPER_WORKER_AUTH_REQUIRED": "false"},
        ), mock.patch.object(
            self.web_server, "mushroom_worker_jobs_path", return_value=jobs_path
        ), mock.patch.object(
            self.web_server, "mushroom_worker_registry_path", return_value=registry_path
        ), mock.patch.object(
            self.web_server.mushroom_worker_results, "discard_candidate", return_value={"candidate": True}
        ) as discard_result, mock.patch.object(
            self.web_server.mushroom_worker_transport, "discard_coordinator_bundle", return_value=True
        ) as discard_bundle:
            status, response = self.web_server.discard_mushroom_worker_candidate(job_id)
            heartbeat_status, cleanup = self.web_server.register_mushroom_worker_heartbeat(heartbeat)
            ack_status, acknowledged = self.web_server.register_mushroom_worker_heartbeat(
                {**heartbeat, "discarded_job_ids": [job_id]}
            )

        self.assertEqual(status, 202)
        self.assertTrue(response["discarding"])
        self.assertEqual(heartbeat_status, 200)
        self.assertEqual(cleanup["discard_job_ids"], [job_id])
        self.assertEqual(ack_status, 200)
        self.assertEqual(acknowledged["discard_job_ids"], [])
        discard_result.assert_called_once()
        discard_bundle.assert_called_once()
        with self.assertRaisesRegex(ValueError, "not found"):
            self.web_server.mushroom_worker_jobs.get_job(jobs_path, job_id=job_id)

    def test_workers_page_shows_persistent_probe_job_without_rebuild_modal_link(self) -> None:
        page = self.web_server.mushroom_workers_ui.render_page(
            worker_statuses=[],
            profiles=[],
            eligible_observation_count=0,
            pending_species_count=0,
            jobs=[{
                "job_id": "worker_job_12345678",
                "job_type": "worker_claim_probe",
                "worker_display_name": "M1 personal",
                "status": "claimed",
                "scope": "transport test",
                "phase": "Claimed by worker",
                "overall_percent": 100,
                "elapsed": "-",
                "opens_rebuild_modal": False,
            }],
            pipeline="shared",
        )

        self.assertIn("Assignment test", page)
        self.assertIn("M1 personal", page)
        self.assertIn("Claimed", page)
        self.assertNotIn("?rebuild_job=worker_job_12345678", page)

    def test_workers_post_rejects_external_worker_before_job_api(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.handle_mushroom_profiles_post = mock.Mock()

        redirect = handler.handle_mushroom_workers_post(
            {"worker_action": ["start_rebuild"], "executor": ["worker:worker_12345678"], "scope": ["all"]}
        )

        self.assertEqual(redirect, "./workers")
        self.assertFalse(handler.handle_mushroom_profiles_post.called)
        message, is_error = self.web_server.mushroom_workers_flash()
        self.assertIn("cannot receive rebuild jobs yet", message)
        self.assertTrue(is_error)

    def test_workers_post_maps_pending_and_species_scopes_to_existing_actions(self) -> None:
        for scope, expected_action in (
            ("pending", "rebuild_pending_model_v0"),
            ("species", "rebuild_learned_model_v0_species"),
        ):
            with self.subTest(scope=scope):
                handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
                captured: dict[str, object] = {}

                def handle_profiles(form: dict[str, list[str]]) -> str:
                    captured.update(form)
                    self.web_server.set_mushroom_profiles_flash("Rebuild request processed.")
                    return "?rebuild_job=job_scope"

                handler.handle_mushroom_profiles_post = handle_profiles
                redirect = handler.handle_mushroom_workers_post(
                    {
                        "worker_action": ["start_rebuild"],
                        "executor": ["home_assistant"],
                        "scope": [scope],
                        "species_id": ["boletus_pinophilus"],
                    }
                )

                self.assertEqual(captured["profile_action"], [expected_action])
                self.assertEqual(captured["species_id"], ["boletus_pinophilus"])
                self.assertEqual(redirect, "./workers?rebuild_job=job_scope")
                self.web_server.mushroom_workers_flash()

    def test_workers_post_sends_partial_scope_to_operational_external_worker(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        for scope, species_id in (("pending", ""), ("species", "boletus_pinophilus")):
            with self.subTest(scope=scope), mock.patch.dict(
                os.environ,
                {
                    "RAINMAPPER_WORKER_API_ENABLED": "true",
                    "RAINMAPPER_WORKER_OPERATIONAL_ENABLED": "true",
                },
            ), mock.patch.object(
                self.web_server,
                "start_mushroom_worker_candidate_rebuild",
                return_value=(202, {"ok": True, "preparing": True}),
            ) as start:
                redirect = handler.handle_mushroom_workers_post(
                    {
                        "worker_action": ["start_rebuild"],
                        "executor": ["worker:worker_12345678"],
                        "scope": [scope],
                        "species_id": [species_id],
                    }
                )

                self.assertEqual("./workers", redirect)
                start.assert_called_once_with(
                    "worker_12345678",
                    promotion_eligible=True,
                    reconstruction_scope=scope,
                    species_id=species_id,
                )
                message, is_error = self.web_server.mushroom_workers_flash()
                self.assertEqual(message, "")
                self.assertFalse(is_error)

    def test_pending_model_species_uses_current_eligible_observations(self) -> None:
        observations = [
            {
                "species_id": "amanita_caesarea",
                "validation_status": "valid",
                "calibration_use": "include",
                "location": {"lat": 42.0, "lon": 2.0},
            },
            {
                "species_id": "boletus_aereus",
                "validation_status": "pending",
                "calibration_use": "include",
                "location": {"lat": 42.0, "lon": 2.0},
            },
            {
                "species_id": "boletus_pinophilus",
                "validation_status": "valid",
                "calibration_use": "exclude",
                "location": {"lat": 42.0, "lon": 2.0},
            },
            {
                "species_id": "lactarius_sanguifluus",
                "validation_status": "valid",
                "calibration_use": "include",
                "location": {},
            },
        ]
        state = {
            "pending_rebuild_species_ids": [
                "amanita_caesarea",
                "boletus_aereus",
                "boletus_pinophilus",
                "lactarius_sanguifluus",
                "old_ha_species",
            ]
        }

        self.assertEqual(
            ["amanita_caesarea"],
            self.web_server.pending_model_species_ids(state, observations, learned_model_payload={"kind": "model"}),
        )

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

        self.assertEqual(1, html.count('<option value="host_pinus_spp"'))
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

        self.assertEqual("?id=boletus_pinophilus&section=species&view=enriched&profile_tab=profile-tab-json#mushroom-profile-message", redirect)
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

        self.assertEqual("?id=boletus_edulis&section=species&view=enriched&profile_tab=profile-tab-json#mushroom-profile-message", redirect)
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

        self.assertEqual("?id=boletus_pinophilus&section=parameters&view=v0", redirect)
        updated_payload = store.load("profiles")
        updated = next(
            item
            for item in updated_payload["species_profiles"]
            if item["species_id"] == "boletus_pinophilus"
        )
        self.assertEqual(12, updated["weather_model"]["rainfall"]["rain_7d_min_mm"])
        self.assertEqual(original_name, updated["scientific_name"])
        self.assertEqual(original_common_names, updated["common_names"])

    def test_mushroom_profiles_parameters_v0_preserves_unrendered_fields(self) -> None:
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
        original_topography = json.loads(json.dumps(profile["topography"]))
        original_phenology = json.loads(json.dumps(profile["phenology"]))
        original_weather = json.loads(json.dumps(profile["weather_model"]))
        original_scoring = json.loads(json.dumps(profile["scoring_weights"]))

        form = {
            "profile_action": ["save_profile_parameters"],
            "species_id": ["boletus_pinophilus"],
            "view": ["v0"],
            "parameter_view": ["topography"],
            "altitude_min_m": [str(profile["topography"]["altitude_min_m"])],
            "altitude_max_m": ["2300"],
            "aspect_notes": [profile["topography"].get("aspect_notes", "")],
            "preferred_aspect_ids": list(profile["topography"].get("preferred_aspect_ids", [])),
        }

        redirect = handler.handle_mushroom_profiles_post(form)

        self.assertEqual("?id=boletus_pinophilus&section=parameters&view=v0", redirect)
        updated_payload = store.load("profiles")
        updated = next(
            item
            for item in updated_payload["species_profiles"]
            if item["species_id"] == "boletus_pinophilus"
        )
        self.assertEqual(2300, updated["topography"]["altitude_max_m"])
        self.assertEqual(original_topography["altitude_min_m"], updated["topography"]["altitude_min_m"])
        self.assertEqual(original_topography["altitude_optimal_min_m"], updated["topography"]["altitude_optimal_min_m"])
        self.assertEqual(original_topography["altitude_optimal_max_m"], updated["topography"]["altitude_optimal_max_m"])
        self.assertEqual(original_phenology, updated["phenology"])
        self.assertEqual(original_weather, updated["weather_model"])
        self.assertEqual(original_scoring, updated["scoring_weights"])

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

    def test_mushroom_parameters_phenology_uses_observed_evidence(self) -> None:
        profile = {
            "species_id": "amanita_caesarea",
            "scientific_name": "Amanita caesarea",
            "common_names": {"en": ["Caesar mushroom"]},
            "ecology": {},
            "phenology": {
                "main_months": [8, 9],
                "secondary_months": [7],
                "season_pattern_ids": ["season_summer"],
            },
            "topography": {},
            "weather_model": {},
            "scoring_weights": {},
            "metadata": {},
        }
        catalogs = {
            "trophic_modes": [],
            "host_taxa": [],
            "forest_types": [],
            "soil_types": [],
            "lithology_types": [],
            "habitat_features": [],
            "aspects": [],
            "season_patterns": [
                {"id": "season_summer", "label": {"en": "Summer"}},
                {"id": "season_autumn", "label": {"en": "Autumn"}},
            ],
            "observation_flush_abundance": [
                {"id": "normal", "prediction_favorable": 1},
                {"id": "abundant", "prediction_favorable": 1},
                {"id": "scarce", "prediction_favorable": 0},
            ],
        }
        observations = {
            "observations": [
                {
                    "observation_id": "obs_july",
                    "species_id": "amanita_caesarea",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "flush_abundance": "normal",
                    "derived": {"month": 7, "season": "summer"},
                },
                {
                    "observation_id": "obs_august",
                    "species_id": "amanita_caesarea",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "flush_abundance": "abundant",
                    "derived": {"month": 8, "season": "summer"},
                },
                {
                    "observation_id": "obs_september",
                    "species_id": "amanita_caesarea",
                    "validation_status": "valid",
                    "calibration_use": "include",
                    "flush_abundance": "scarce",
                    "derived": {"month": 9, "season": "autumn"},
                },
            ]
        }

        html = self.web_server.mushroom_profiles_ui.render_parameters_section(
            profile,
            catalogs,
            profile_view="v0",
            parameter_view="phenology",
            observations_payload=observations,
        )

        self.assertIn("Total observations used", html)
        self.assertIn("<strong>3</strong>", html)
        self.assertIn("Jul", html)
        self.assertIn("Aug", html)
        self.assertIn("Sep", html)
        self.assertIn("Field", html)
        self.assertIn("Autumn", html)
        self.assertNotIn("No learned model has been generated yet", html)
        self.assertNotIn("mushroom_learned_model_v0_build.sh", html)

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

    def test_catalog_entry_form_updates_prediction_favorable_as_binary_value(self) -> None:
        existing = {
            "id": "scarce",
            "label": {"es": "Escasa", "ca": "Escassa", "en": "Scarce"},
            "prediction_favorable": 1,
        }
        form = {
            "label_es": ["Escasa"],
            "label_ca": ["Escassa"],
            "label_en": ["Scarce"],
            "prediction_favorable": ["0"],
        }

        entry = self.web_server.catalog_entry_from_form(
            "observation_flush_abundance", "scarce", existing, form
        )

        self.assertEqual(0, entry["prediction_favorable"])

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
        self.assertEqual(command[command.index("--wunderground_daily_api") + 1], "true")
        self.assertEqual(command[command.index("--backfill_station_filter") + 1], "")

    def test_webui_update_command_passes_backfill_station_filter(self) -> None:
        previous = os.environ.get("RAINMAPPER_BACKFILL_STATION_FILTER")
        os.environ["RAINMAPPER_BACKFILL_STATION_FILTER"] = "wunderground::IORDIN1,IMERAN22"
        try:
            command = self.web_server.command_for("update")
        finally:
            if previous is None:
                os.environ.pop("RAINMAPPER_BACKFILL_STATION_FILTER", None)
            else:
                os.environ["RAINMAPPER_BACKFILL_STATION_FILTER"] = previous

        self.assertEqual(
            command[command.index("--backfill_station_filter") + 1],
            "wunderground::IORDIN1,IMERAN22",
        )

    def test_webui_update_command_accepts_backfill_day_window_override(self) -> None:
        command = self.web_server.command_for(
            "update",
            days_init=-180,
            days_end=-91,
            nototals=True,
            wunderground_local_start_date="2026-01-01",
            wunderground_local_end_date="2026-03-31",
        )

        self.assertEqual(command[command.index("--days_init") + 1], "-180")
        self.assertEqual(command[command.index("--days_end") + 1], "-91")
        self.assertEqual(command[command.index("--nototals") + 1], "true")
        self.assertEqual(command[command.index("--wunderground_local_start_date") + 1], "2026-01-01")
        self.assertEqual(command[command.index("--wunderground_local_end_date") + 1], "2026-03-31")

    def test_monthly_backfill_windows_convert_month_offsets_to_day_windows(self) -> None:
        previous_values = {
            name: os.environ.get(name)
            for name in (
                "RAINMAPPER_MONTHS_INIT",
                "RAINMAPPER_MONTHS_END",
                "RAINMAPPER_MONTHS_INTERVAL",
            )
        }
        os.environ["RAINMAPPER_MONTHS_INIT"] = "-5"
        os.environ["RAINMAPPER_MONTHS_END"] = "0"
        os.environ["RAINMAPPER_MONTHS_INTERVAL"] = "2"
        try:
            reference = datetime(2026, 7, 11, tzinfo=self.web_server.get_timezone())
            windows = self.web_server.monthly_backfill_windows(reference)
        finally:
            for name, previous in previous_values.items():
                if previous is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = previous

        reference_date = date(2026, 7, 11)
        self.assertEqual(
            [(window["months_init"], window["months_end"]) for window in windows],
            [(-5, -4), (-3, -2), (-1, 0)],
        )
        self.assertEqual(windows[0]["days_init"], (date(2026, 2, 1) - reference_date).days)
        self.assertEqual(windows[0]["days_end"], (date(2026, 3, 31) - reference_date).days)
        self.assertEqual(windows[0]["local_start_date"], "2026-02-01")
        self.assertEqual(windows[0]["local_end_date"], "2026-03-31")
        self.assertEqual(windows[-1]["days_init"], (date(2026, 6, 1) - reference_date).days)
        self.assertEqual(windows[-1]["days_end"], 0)
        self.assertEqual(windows[-1]["local_start_date"], "2026-06-01")
        self.assertEqual(windows[-1]["local_end_date"], "2026-07-11")

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
        previous = os.environ.get("RAINMAPPER_PUBLISH_TO_WWW")
        os.environ.pop("RAINMAPPER_PUBLISH_TO_WWW", None)
        try:
            command = self.web_server.command_for("maps")
        finally:
            if previous is not None:
                os.environ["RAINMAPPER_PUBLISH_TO_WWW"] = previous

        self.assertEqual(command[:2], ["sh", "-c"])
        self.assertIn("--include-aemet true", command[2])
        self.assertNotIn("rainmapper_core.bokeh_maps", command[2])

    def test_webui_legacy_www_enables_bokeh_maps_explicitly(self) -> None:
        previous = os.environ.get("RAINMAPPER_PUBLISH_TO_WWW")
        os.environ["RAINMAPPER_PUBLISH_TO_WWW"] = "true"
        try:
            maps_command = self.web_server.command_for("maps")
            all_command = self.web_server.command_for("all")
        finally:
            if previous is None:
                os.environ.pop("RAINMAPPER_PUBLISH_TO_WWW", None)
            else:
                os.environ["RAINMAPPER_PUBLISH_TO_WWW"] = previous

        self.assertIn("rainmapper_core.bokeh_maps", maps_command[2])
        self.assertIn("rainmapper_core.bokeh_maps", all_command)

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
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_DEM_ZOOM",
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
                "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_DEM_ZOOM": "10",
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
                        "demZoom": 10,
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

    def test_protected_maplibre_index_uses_running_version_for_assets(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        captured: dict[str, object] = {"headers": []}
        previous_version = os.environ.get("RAINMAPPER_APP_VERSION")
        previous_assets_path = self.web_server.MAPLIBRE_VIEWER_ASSETS_PATH

        class MemoryWriter:
            def __init__(self) -> None:
                self.content = b""

            def write(self, content: bytes) -> None:
                self.content += content

        try:
            os.environ["RAINMAPPER_APP_VERSION"] = "9.9.9-test"
            self.web_server.MAPLIBRE_VIEWER_ASSETS_PATH = (
                Path(__file__).resolve().parents[1] / "rainmapper_core" / "viewers" / "maplibre-viewer"
            )
            writer = MemoryWriter()
            handler.wfile = writer
            handler.send_response = lambda status: captured.update({"status": status})
            handler.send_header = lambda name, value: captured["headers"].append((name, value))
            handler.end_headers = lambda: None

            handler.serve_protected_maplibre("/index.html")
        finally:
            self.web_server.MAPLIBRE_VIEWER_ASSETS_PATH = previous_assets_path
            if previous_version is None:
                os.environ.pop("RAINMAPPER_APP_VERSION", None)
            else:
                os.environ["RAINMAPPER_APP_VERSION"] = previous_version

        html = writer.content.decode("utf-8")
        self.assertEqual(captured["status"], 200)
        self.assertIn(("Cache-Control", "no-store, max-age=0"), captured["headers"])
        self.assertIn("app.js?v=9.9.9-test", html)
        self.assertIn("style.css?v=9.9.9-test", html)

    def test_ingress_stream_is_enabled_for_large_media_uploads(self) -> None:
        config = (ROOT_DIR / "rainmapper-app" / "config.yaml").read_text(encoding="utf-8")
        self.assertIn("ingress_stream: true", config)

    def test_chunked_request_body_is_decoded(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.path = "/api/mushrooms/observation-exif-preview"
        handler.headers = {"Transfer-Encoding": "chunked"}
        handler.rfile = io.BytesIO(b"4\r\ntest\r\n8\r\n payload\r\n0\r\n\r\n")

        self.assertEqual(handler.read_request_body(), b"test payload")
        self.assertEqual(handler.read_request_body(), b"test payload")

    def test_worker_protocol_json_has_a_small_independent_body_limit(self) -> None:
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.path = "/api/mushrooms/workers/jobs/claim"
        self.assertEqual(handler.request_body_limit(), 64 * 1024)

        handler.path = "/api/mushrooms/workers/jobs/result-file"
        self.assertEqual(
            handler.request_body_limit(),
            self.web_server.mushroom_worker_results.MAX_RESULT_FILE_BYTES,
        )

    def test_fixed_length_form_body_keeps_existing_behavior(self) -> None:
        body = b"profile_action=create_observation&observation_species_id=boletus_pinophilus"
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.path = "/mushrooms/profiles"
        handler.headers = {
            "Content-Length": str(len(body)),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        handler.rfile = io.BytesIO(body)

        self.assertEqual(handler.read_form()["profile_action"], ["create_observation"])
        self.assertEqual(handler.read_form()["observation_species_id"], ["boletus_pinophilus"])

    def test_chunked_multipart_upload_keeps_form_and_file(self) -> None:
        boundary = "RainmapperBoundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="observation_id"\r\n\r\n'
            "obs_20260716_0001\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="observation_exif_images"; filename="sample.mov"\r\n'
            "Content-Type: video/quicktime\r\n\r\n"
        ).encode("utf-8") + b"video-bytes" + f"\r\n--{boundary}--\r\n".encode("utf-8")
        pieces = (body[:31], body[31:109], body[109:])
        chunked = b"".join(
            f"{len(piece):X}\r\n".encode("ascii") + piece + b"\r\n"
            for piece in pieces
        ) + b"0\r\n\r\n"
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.path = "/api/mushrooms/observation-exif-preview"
        handler.headers = {
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        handler.rfile = io.BytesIO(chunked)

        form, files = handler.read_form_and_files()

        self.assertEqual(form["observation_id"], ["obs_20260716_0001"])
        self.assertEqual(files["observation_exif_images"][0]["filename"], "sample.mov")
        self.assertEqual(files["observation_exif_images"][0]["content"], b"video-bytes")
        self.assertEqual(files["observation_exif_images"][0]["content_type"], "video/quicktime")

    def test_chunked_request_body_rejects_invalid_and_oversized_chunks(self) -> None:
        malformed = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        malformed.path = "/api/mushrooms/observation-exif-preview"
        malformed.headers = {"Transfer-Encoding": "chunked"}
        malformed.rfile = io.BytesIO(b"invalid\r\n")
        with self.assertRaises(self.web_server.RequestBodyError) as invalid_context:
            malformed.read_request_body()
        self.assertEqual(invalid_context.exception.status, 400)

        oversized = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        oversized.rfile = io.BytesIO(b"5\r\nabcde\r\n0\r\n\r\n")
        with self.assertRaises(self.web_server.RequestBodyError) as oversized_context:
            oversized.read_chunked_request_body(4)
        self.assertEqual(oversized_context.exception.status, 413)

    def test_async_observation_save_returns_redirect_as_json(self) -> None:
        body = b"rainmapper_async=1"
        handler = self.web_server.RainmapperHandler.__new__(self.web_server.RainmapperHandler)
        handler.path = "/mushrooms/profiles?section=observations"
        handler.headers = {
            "Content-Length": str(len(body)),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        handler.rfile = io.BytesIO(body)
        handler.handle_mushroom_profiles_post = lambda form, files: "?section=observations#saved"
        captured: dict[str, object] = {}
        handler.send_json = lambda status, payload: captured.update(status=status, payload=payload)

        handler.do_POST()

        self.assertEqual(captured["status"], 200)
        self.assertEqual(captured["payload"], {"ok": True, "redirect": "?section=observations#saved"})


if __name__ == "__main__":
    unittest.main()
