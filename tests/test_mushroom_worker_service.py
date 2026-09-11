import json
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

from rainmapper_core import mushroom_worker_service


class MushroomWorkerServiceTests(unittest.TestCase):
    def test_precompute_failed_finish_survives_service_restart_and_blocks_new_background_claims(self):
        failed_delivery = threading.Event()
        delivered = threading.Event()
        allow_delivery = threading.Event()
        requests = []
        claimed = False

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                nonlocal claimed
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
                requests.append((self.path, payload))
                code = 200
                if self.path.endswith("/heartbeat"):
                    response = {"ok": True}
                elif self.path.endswith("/jobs/claim"):
                    job = None
                    if payload.get("lane") == "background" and not claimed:
                        claimed = True
                        # Missing runtime metadata deliberately fails preparation;
                        # only the final notification is under test, no calculation.
                        job = {"job_id": "worker_job_pendingfinish", "job_type": "worker_predictor_precompute_v1", "claim_token": "claim-secret"}
                    response = {"ok": True, "job": job}
                elif self.path.endswith("/jobs/start"):
                    response = {"ok": True, "job": {}}
                elif self.path.endswith("/jobs/finish"):
                    if allow_delivery.is_set():
                        response = {"ok": True, "job": {"status": payload["status"]}}
                        delivered.set()
                    else:
                        code = 503
                        response = {"ok": False, "error": "temporary receiver outage"}
                        failed_delivery.set()
                else:
                    code = 404
                    response = {"ok": False, "error": "test has no runtime"}
                body = json.dumps(response).encode()
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        process = None
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                mushroom_worker_service.mushroom_worker_config.save_coordinator_config(
                    root, rainmapper_url=f"http://127.0.0.1:{server.server_port}", token="p" * 40,
                )
                command = [
                    sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/run-mushroom-worker-service.py"),
                    "--host", "127.0.0.1", "--port", "0", "--worker-data-dir", str(root),
                    "--heartbeat-interval", "1",
                ]

                def launch():
                    return subprocess.Popen(command, env={**os.environ, "RAINMAPPER_WORKER_JOB_RETRY_SECONDS": "0"}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

                process = launch()
                self.assertTrue(failed_delivery.wait(8))
                notice = root / "predictor_precompute/pending-finish.json"
                self.assertEqual(json.loads(notice.read_text())["status"], "failed")
                deadline = time.monotonic() + 5
                while sum(path.endswith("/jobs/finish") for path, _ in requests) < 2 and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertGreaterEqual(sum(path.endswith("/jobs/finish") for path, _ in requests), 2)
                self.assertEqual(sum(path.endswith("/jobs/claim") and p.get("lane") == "background" for path, p in requests), 1)
                process.terminate()
                output, _ = process.communicate(timeout=8)
                self.assertEqual(process.returncode, 0, output)
                process = None
                self.assertTrue(notice.exists())
                allow_delivery.set()
                process = launch()
                self.assertTrue(delivered.wait(8))
                deadline = time.monotonic() + 3
                while notice.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertFalse(notice.exists())
                finishes = [p for path, p in requests if path.endswith("/jobs/finish")]
                self.assertTrue(all(p == finishes[0] for p in finishes))
        finally:
            if process is not None:
                process.terminate()
                output, _ = process.communicate(timeout=8)
                self.assertEqual(process.returncode, 0, output)
            server.shutdown()
            server.server_close()

    def test_quiet_process_drains_stderr_and_keeps_only_a_bounded_tail(self) -> None:
        process, stderr_capture = mushroom_worker_service._start_quiet_process(
            [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "sys.stderr.buffer.write(b'x' * (1024 * 1024)); "
                    "sys.stderr.buffer.write(b'\\nEND-OF-ERROR\\n'); "
                    "sys.stderr.flush()"
                ),
            ]
        )

        self.assertEqual(process.wait(timeout=10), 0)
        stderr_capture.wait()
        tail = stderr_capture.tail_bytes()
        self.assertLessEqual(
            len(tail), mushroom_worker_service.SUBPROCESS_STDERR_TAIL_MAX_BYTES
        )
        self.assertTrue(tail.endswith(b"\nEND-OF-ERROR\n"))

    def test_service_runs_one_job_per_lane_from_different_coordinators(self) -> None:
        def coordinator_server(
            lane: str, job_id: str, *, heartbeat_ok: bool = True
        ) -> tuple[ThreadingHTTPServer, dict[str, object]]:
            state: dict[str, object] = {
                "claimed": False,
                "requests": [],
                "started": threading.Event(),
                "finished": threading.Event(),
                "started_at": 0.0,
            }
            state_lock = threading.Lock()

            class Handler(BaseHTTPRequestHandler):
                def do_POST(self) -> None:  # noqa: N802
                    size = int(self.headers.get("Content-Length", "0"))
                    payload = json.loads(self.rfile.read(size) or b"{}")
                    with state_lock:
                        state["requests"].append(
                            (self.path, payload, self.headers.get("Authorization", ""))
                        )
                    if self.path.endswith("/heartbeat"):
                        if not heartbeat_ok:
                            self.send_error(503)
                            return
                        response = {"ok": True}
                    elif self.path.endswith("/jobs/claim"):
                        with state_lock:
                            should_claim = (
                                payload.get("lane") == lane and not state["claimed"]
                            )
                            if should_claim:
                                state["claimed"] = True
                        response = {
                            "ok": True,
                            "job": {
                                "job_id": job_id,
                                "job_type": "worker_claim_probe",
                                "claim_token": f"claim-{job_id}",
                            }
                            if should_claim
                            else None,
                        }
                    elif self.path.endswith("/jobs/start"):
                        state["started_at"] = time.monotonic()
                        state["started"].set()
                        response = {"ok": True, "job": {}}
                    elif self.path.endswith("/jobs/control"):
                        response = {"ok": True, "job": {}, "cancel_requested": False}
                    elif self.path.endswith("/jobs/finish"):
                        state["finished"].set()
                        response = {"ok": True, "job": {}}
                    else:
                        self.send_error(404)
                        return
                    body = json.dumps(response).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, _format: str, *_args: object) -> None:
                    return

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            return server, state

        primary_server, primary = coordinator_server(
            "foreground", "worker_job_foreground123"
        )
        secondary_server, secondary = coordinator_server(
            "background", "worker_job_background123"
        )
        unavailable_server, unavailable = coordinator_server(
            "foreground",
            "worker_job_unavailable123",
            heartbeat_ok=False,
        )
        process: subprocess.Popen[str] | None = None
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                primary_url = f"http://127.0.0.1:{primary_server.server_port}"
                secondary_url = f"http://127.0.0.1:{secondary_server.server_port}"
                unavailable_url = f"http://127.0.0.1:{unavailable_server.server_port}"
                mushroom_worker_service.mushroom_worker_config.save_coordinator_config(
                    root, rainmapper_url=primary_url, token="p" * 40
                )
                mushroom_worker_service.mushroom_worker_config.add_coordinator(
                    root, rainmapper_url=secondary_url, token="s" * 40
                )
                mushroom_worker_service.mushroom_worker_config.add_coordinator(
                    root, rainmapper_url=unavailable_url, token="u" * 40
                )
                primary_config_before = (
                    root / "config/coordinator.json"
                ).read_bytes()
                primary_token_before = (
                    root / "secrets/coordinator-token"
                ).read_bytes()
                environment = {
                    **os.environ,
                    "RAINMAPPER_WORKER_CLAIM_PROBE_SECONDS": "2",
                    "RAINMAPPER_WORKER_JOB_RETRY_SECONDS": "0",
                }
                process = subprocess.Popen(
                    [
                        sys.executable,
                        str(
                            Path(__file__).resolve().parents[1]
                            / "scripts/run-mushroom-worker-service.py"
                        ),
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "0",
                        "--worker-data-dir",
                        str(root),
                        "--heartbeat-interval",
                        "1",
                    ],
                    cwd=Path(__file__).resolve().parents[1],
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                self.assertTrue(primary["started"].wait(8))
                self.assertTrue(secondary["started"].wait(8))
                self.assertLess(
                    abs(float(primary["started_at"]) - float(secondary["started_at"])),
                    1.0,
                )
                self.assertTrue(primary["finished"].wait(8))
                self.assertTrue(secondary["finished"].wait(8))

                primary_paths = [path for path, _payload, _auth in primary["requests"]]
                secondary_paths = [path for path, _payload, _auth in secondary["requests"]]
                self.assertIn("/api/mushrooms/workers/jobs/finish", primary_paths)
                self.assertIn("/api/mushrooms/workers/jobs/finish", secondary_paths)
                unavailable_paths = [
                    path for path, _payload, _auth in unavailable["requests"]
                ]
                self.assertIn("/api/mushrooms/workers/heartbeat", unavailable_paths)
                self.assertNotIn(
                    "/api/mushrooms/workers/jobs/claim", unavailable_paths
                )
                self.assertTrue(
                    all(auth == f"Bearer {'p' * 40}" for _path, _payload, auth in primary["requests"])
                )
                self.assertTrue(
                    all(auth == f"Bearer {'s' * 40}" for _path, _payload, auth in secondary["requests"])
                )
                primary_busy = [
                    payload
                    for path, payload, _auth in primary["requests"]
                    if path.endswith("/heartbeat")
                    and payload.get("lanes", {}).get("foreground", {}).get("status")
                    == "busy"
                    and payload.get("lanes", {}).get("background", {}).get("status")
                    == "busy"
                ]
                secondary_busy = [
                    payload
                    for path, payload, _auth in secondary["requests"]
                    if path.endswith("/heartbeat")
                    and payload.get("lanes", {}).get("foreground", {}).get("status")
                    == "busy"
                    and payload.get("lanes", {}).get("background", {}).get("status")
                    == "busy"
                ]
                self.assertTrue(primary_busy)
                self.assertTrue(secondary_busy)
                self.assertEqual(
                    primary_busy[0]["lanes"]["foreground"]["active_job_id"],
                    "worker_job_foreground123",
                )
                self.assertEqual(
                    primary_busy[0]["lanes"]["background"]["active_job_id"], ""
                )
                self.assertEqual(
                    secondary_busy[0]["lanes"]["foreground"]["active_job_id"], ""
                )
                self.assertEqual(
                    secondary_busy[0]["lanes"]["background"]["active_job_id"],
                    "worker_job_background123",
                )
                self.assertEqual(
                    (root / "config/coordinator.json").read_bytes(),
                    primary_config_before,
                )
                self.assertEqual(
                    (root / "secrets/coordinator-token").read_bytes(),
                    primary_token_before,
                )
        finally:
            if process is not None:
                process.terminate()
                output, _ = process.communicate(timeout=8)
                self.assertEqual(process.returncode, 0, output)
            primary_server.shutdown()
            primary_server.server_close()
            secondary_server.shutdown()
            secondary_server.server_close()
            unavailable_server.shutdown()
            unavailable_server.server_close()

    def test_configured_coordinators_keeps_primary_and_loads_many_secondaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mushroom_worker_service.mushroom_worker_config.save_coordinator_config(
                root,
                rainmapper_url="https://real-ha.example",
                token="r" * 40,
            )
            for index in range(3):
                mushroom_worker_service.mushroom_worker_config.add_coordinator(
                    root,
                    rainmapper_url=f"https://lab-{index}.example",
                    token=str(index) * 40,
                )

            coordinators = mushroom_worker_service.configured_coordinators(root)

        self.assertEqual(len(coordinators), 4)
        self.assertTrue(coordinators[0]["primary"])
        self.assertEqual(coordinators[0]["rainmapper_url"], "https://real-ha.example")
        self.assertEqual(coordinators[0]["token"], "r" * 40)
        self.assertEqual(
            {row["token"] for row in coordinators[1:]},
            {"0" * 40, "1" * 40, "2" * 40},
        )

    def test_coordinator_lane_view_hides_another_coordinators_job_id(self) -> None:
        lanes = {
            "foreground": {
                "status": "busy",
                "active_job_id": "worker_job_real12345",
                "coordinator_id": "primary",
            },
            "background": {
                "status": "busy",
                "active_job_id": "worker_job_local1234",
                "coordinator_id": "coordinator_local",
            },
        }

        primary = mushroom_worker_service.coordinator_visible_lanes(lanes, "primary")
        local = mushroom_worker_service.coordinator_visible_lanes(
            lanes, "coordinator_local"
        )

        self.assertEqual(primary["foreground"]["active_job_id"], "worker_job_real12345")
        self.assertEqual(primary["background"]["active_job_id"], "")
        self.assertEqual(local["foreground"]["active_job_id"], "")
        self.assertEqual(local["background"]["active_job_id"], "worker_job_local1234")
        self.assertNotIn("coordinator_id", primary["foreground"])
        self.assertNotIn("coordinator_id", local["background"])

    def test_round_robin_supports_more_than_two_coordinators(self) -> None:
        coordinators = [
            {"coordinator_id": f"coordinator_{index}"} for index in range(5)
        ]

        order = mushroom_worker_service.round_robin_coordinators(coordinators, 3)

        self.assertEqual(
            [row["coordinator_id"] for _index, row in order],
            [
                "coordinator_3",
                "coordinator_4",
                "coordinator_0",
                "coordinator_1",
                "coordinator_2",
            ],
        )

    def test_claim_round_robin_skips_unreachable_and_claims_only_one_job(self) -> None:
        coordinators = [
            {
                "coordinator_id": f"coordinator_{index}",
                "rainmapper_url": f"https://coordinator-{index}.example",
                "token": f"token-{index}",
            }
            for index in range(5)
        ]
        calls: list[tuple[str, str]] = []

        def claim(url: str, _worker_id: str, **kwargs: object) -> dict | None:
            calls.append((url, str(kwargs["lane"])))
            if url == "https://coordinator-4.example":
                return {"job_id": "worker_job_selected123"}
            return None

        result = mushroom_worker_service.claim_job_round_robin(
            coordinators,
            reachable_coordinator_ids={
                "coordinator_0",
                "coordinator_2",
                "coordinator_4",
            },
            start_index=1,
            lane="foreground",
            worker_id="worker_12345678",
            claim=claim,
        )

        self.assertEqual(
            calls,
            [
                ("https://coordinator-2.example", "foreground"),
                ("https://coordinator-4.example", "foreground"),
            ],
        )
        self.assertEqual(result["job"]["job_id"], "worker_job_selected123")
        self.assertEqual(result["coordinator"]["coordinator_id"], "coordinator_4")
        self.assertEqual(result["next_index"], 0)

    def test_claim_affinity_and_two_lanes_are_independent(self) -> None:
        coordinators = [
            {
                "coordinator_id": f"coordinator_{index}",
                "rainmapper_url": f"https://coordinator-{index}.example",
                "token": f"token-{index}",
            }
            for index in range(3)
        ]
        calls: list[tuple[str, str]] = []

        def claim(url: str, _worker_id: str, **kwargs: object) -> dict:
            lane = str(kwargs["lane"])
            calls.append((url, lane))
            return {"job_id": f"worker_job_{lane}123"}

        foreground = mushroom_worker_service.claim_job_round_robin(
            coordinators,
            reachable_coordinator_ids={row["coordinator_id"] for row in coordinators},
            start_index=2,
            lane="foreground",
            worker_id="worker_12345678",
            preferred_coordinator_id="coordinator_1",
            claim=claim,
        )
        background = mushroom_worker_service.claim_job_round_robin(
            coordinators,
            reachable_coordinator_ids={row["coordinator_id"] for row in coordinators},
            start_index=2,
            lane="background",
            worker_id="worker_12345678",
            claim=claim,
        )

        self.assertEqual(
            calls,
            [
                ("https://coordinator-1.example", "foreground"),
                ("https://coordinator-2.example", "background"),
            ],
        )
        self.assertEqual(foreground["job"]["job_id"], "worker_job_foreground123")
        self.assertEqual(background["job"]["job_id"], "worker_job_background123")

    def test_primary_and_secondary_precompute_paths_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            primary = mushroom_worker_service.coordinator_precompute_root(
                root, {"coordinator_id": "primary", "primary": True}
            )
            secondary = mushroom_worker_service.coordinator_precompute_root(
                root,
                {"coordinator_id": "coordinator_local", "primary": False},
            )

        self.assertEqual(primary, root.resolve() / "predictor_precompute")
        self.assertEqual(
            secondary,
            root.resolve() / "coordinators/coordinator_local/predictor_precompute",
        )

    def test_precompute_resolves_selections_from_runtime_without_ha_download(self) -> None:
        job = {"area_ids_by_species": {"boletus_edulis": ["area-a"]}}
        expected = [{"species_id": "boletus_edulis", "area_id": "area-a"}]
        with (
            mock.patch.object(
                mushroom_worker_service.mushroom_predictor_runtime,
                "service_paths",
                return_value={
                    "models_dir": Path("/runtime/models"),
                    "version_registry_path": Path("/runtime/registry.json"),
                },
            ),
            mock.patch.object(
                mushroom_worker_service.mushroom_predictor_runtime,
                "operational_reliability_selections",
                return_value=expected,
            ) as resolve,
            mock.patch.object(
                mushroom_worker_service,
                "download_predictor_precompute_operational_selections",
            ) as download,
        ):
            actual = mushroom_worker_service.resolve_predictor_precompute_operational_selections(
                job,
                Path("/runtime"),
                ha_url="http://ha",
                worker_id="worker_12345678",
                claim_token="claim-secret",
                token="coordinator-secret",
            )

        self.assertEqual(expected, actual)
        resolve.assert_called_once()
        download.assert_not_called()

    def test_precompute_selections_are_downloaded_and_verified_outside_claim(self) -> None:
        selections = {"boletus_edulis": [{"profile_key": "biology_v4:model"}]}
        reference = (
            mushroom_worker_service.mushroom_worker_jobs.predictor_precompute_operational_selections_ref(
                selections
            )
        )
        job = {
            "job_id": "worker_job_precompute123",
            "operational_selections_ref": reference,
        }
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(
            {
                "ok": True,
                "operational_selections": selections,
                "operational_selections_ref": reference,
            }
        ).encode()
        with mock.patch.object(
            mushroom_worker_service,
            "urlopen",
            return_value=response,
        ) as urlopen:
            downloaded = (
                mushroom_worker_service.download_predictor_precompute_operational_selections(
                    "http://rainmapper-ha-ui:8099",
                    job,
                    worker_id="worker_12345678",
                    claim_token="claim-secret",
                    token="coordinator-secret",
                )
            )

        self.assertEqual(selections, downloaded)
        self.assertEqual(selections, job["operational_selections"])
        request = urlopen.call_args.args[0]
        self.assertIn(reference["endpoint"], request.full_url)
        self.assertIn("job_id=worker_job_precompute123", request.full_url)

    def test_precompute_selections_reject_digest_mismatch(self) -> None:
        selections = {"boletus_edulis": [{"profile_key": "biology_v4:model"}]}
        reference = (
            mushroom_worker_service.mushroom_worker_jobs.predictor_precompute_operational_selections_ref(
                selections
            )
        )
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(
            {
                "ok": True,
                "operational_selections": {
                    "boletus_edulis": [{"profile_key": "biology_v4:other"}]
                },
            }
        ).encode()
        with mock.patch.object(
            mushroom_worker_service,
            "urlopen",
            return_value=response,
        ):
            with self.assertRaisesRegex(ValueError, "do not match"):
                mushroom_worker_service.download_predictor_precompute_operational_selections(
                    "http://rainmapper-ha-ui:8099",
                    {
                        "job_id": "worker_job_precompute123",
                        "operational_selections_ref": reference,
                    },
                    worker_id="worker_12345678",
                    claim_token="claim-secret",
                    token="coordinator-secret",
                )

    def test_precompute_upload_returns_verified_ha_publication_timings(self) -> None:
        receipt_body = {
            "schema_version": "1.0",
            "desired_revision": 1,
            "artifact_id": "sha256:" + "a" * 64,
            "file_sha256": "sha256:" + "b" * 64,
            "size_bytes": 6,
        }
        receipt = {
            **receipt_body,
            "receipt_id": "sha256:"
            + hashlib.sha256(
                json.dumps(receipt_body, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        response = mock.Mock(
            status=200,
            read=mock.Mock(
                return_value=json.dumps(
                    {
                        "publication_receipt": receipt,
                        "publication_telemetry": {
                            "upload_received_at": "2026-08-30T20:10:25+00:00",
                            "ha_activation_finished_at": "2026-08-30T20:10:28+00:00",
                            "ha_publish_seconds": 3.0,
                            "artifact_size_bytes": 6,
                        },
                    }
                ).encode()
            ),
        )
        connection = mock.Mock(getresponse=mock.Mock(return_value=response))
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "artifact.sqlite3"
            artifact.write_bytes(b"sqlite")
            with mock.patch.object(
                mushroom_worker_service.http.client,
                "HTTPConnection",
                return_value=connection,
            ):
                returned_receipt, telemetry = (
                    mushroom_worker_service.upload_predictor_precompute_artifact(
                        "http://ha:8100",
                        artifact,
                        job_id="worker_job_precompute_upload",
                        worker_id="worker_aaaaaaaa",
                        claim_token="claim-token",
                        token="token",
                        file_sha256=receipt_body["file_sha256"],
                    )
                )

        self.assertEqual(receipt_body["artifact_id"], returned_receipt.artifact_id)
        self.assertEqual(3.0, telemetry["ha_publish_seconds"])
        self.assertEqual(6, telemetry["artifact_size_bytes"])
        connection.send.assert_called_once_with(b"sqlite")

    def test_operational_retry_requires_same_scope_and_plan(self) -> None:
        verified = {
            "operational_scope_id": "sha256:" + "a" * 64,
            "operational_plan_id": "sha256:" + "b" * 64,
        }
        with mock.patch.object(
            mushroom_worker_service.mushroom_ml_multiversion_transport,
            "validate_result_manifest",
            return_value=verified,
        ):
            accepted = mushroom_worker_service.validate_multiversion_retry_identity(
                {},
                job_id="worker_job_retryidentity",
                job_purpose="operational",
                spec=dict(verified),
            )
            self.assertEqual(verified, accepted)
            with self.assertRaisesRegex(ValueError, "sealed operational scope and plan"):
                mushroom_worker_service.validate_multiversion_retry_identity(
                    {},
                    job_id="worker_job_retryidentity",
                    job_purpose="operational",
                    spec={**verified, "operational_plan_id": "sha256:" + "c" * 64},
                )

    def test_operational_multiversion_command_requires_sealed_tuning_catalog(self) -> None:
        root = Path("/worker/jobs/operational")
        command = mushroom_worker_service.multiversion_preparation_command(
            root,
            {
                "weather_data_dir": "snapshot/inputs/weather",
                "observations_path": "snapshot/inputs/observations.json",
                "known_sites_path": "snapshot/inputs/known-sites.json",
                "observation_features_path": "snapshot/inputs/features.json",
                "stations_path": "snapshot/inputs/stations.txt",
                "tuning_catalog_path": "snapshot/inputs/tuning-catalog.json",
                "operational_plan_path": "snapshot/inputs/operational-plan.json",
                "profile_keys": ["biology_v4/climatic_balance"],
            },
            {"snapshot_id": "sha256:snapshot"},
            preparation_root=root / "prepared",
            progress_path=root / "progress.jsonl",
            job_purpose="operational",
        )

        tuning_index = command.index("--tuning-catalog")
        self.assertEqual(
            command[tuning_index + 1],
            str(root / "snapshot/inputs/tuning-catalog.json"),
        )
        self.assertIn("operational", command)
        plan_index = command.index("--operational-plan")
        self.assertEqual(
            command[plan_index + 1],
            str(root / "snapshot/inputs/operational-plan.json"),
        )

    def test_worker_seeds_predictor_cache_from_its_multiversion_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = root / "result"
            batch = result / "batch"
            model = batch / "generations/g/model.joblib"
            quality = batch / "quality-catalog.json"
            quality_audit = batch / "quality-audit-catalog.json"
            model.parent.mkdir(parents=True)
            model.write_bytes(b"trained-here")
            quality.write_bytes(b"quality")
            quality_audit.write_bytes(b"quality-audit")
            batch_id = "batch-local"
            manifest = {
                "batch_id": batch_id,
                "artifacts": [{
                    "path": f"batches/{batch_id}/generations/g/model.joblib",
                    "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                    "size_bytes": model.stat().st_size,
                }],
                "quality_catalog": {
                    "path": f"batches/{batch_id}/quality-catalog.json",
                    "sha256": hashlib.sha256(quality.read_bytes()).hexdigest(),
                },
                "quality_audit_catalog": {
                    "path": f"batches/{batch_id}/quality-audit-catalog.json",
                    "sha256": hashlib.sha256(
                        quality_audit.read_bytes()
                    ).hexdigest(),
                    "selection_id": "sha256:" + "a" * 64,
                },
            }
            (batch / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            cached = mushroom_worker_service.cache_multiversion_predictor_objects(
                root / "worker",
                result,
            )

            self.assertEqual(cached["cached_objects"], 3)
            self.assertEqual(
                len(list((root / "worker/predictor-runtime/objects").iterdir())),
                3,
            )
            self.assertFalse(
                (
                    root
                    / "worker/predictor-runtime/objects"
                    / hashlib.sha256(quality_audit.read_bytes()).hexdigest()
                ).exists()
            )

    def test_job_telemetry_coalesces_progress_and_control_every_ten_seconds(self) -> None:
        now = [10.0]
        calls: list[tuple[str, dict[str, object]]] = []

        def update(action: str, payload: dict[str, object]) -> dict[str, object]:
            calls.append((action, payload))
            return {}

        telemetry = mushroom_worker_service._CoalescedJobTelemetry(
            update,
            base_payload={"job_id": "worker_job_test"},
            cancel_message="cancelled",
            monotonic=lambda: now[0],
        )
        telemetry.publish({"phase": "first", "overall_percent": 10})
        telemetry._wait_for_idle()
        telemetry.publish({"phase": "intermediate", "overall_percent": 20})
        now[0] = 19.9
        telemetry.publish({"phase": "newest pending", "overall_percent": 30})
        now[0] = 20.0
        telemetry.publish({"phase": "ten seconds", "overall_percent": 40})
        telemetry._wait_for_idle()

        self.assertEqual([action for action, _ in calls], ["control", "progress", "control", "progress"])
        self.assertEqual(
            [payload["phase"] for action, payload in calls if action == "progress"],
            ["first", "ten seconds"],
        )

    def test_job_telemetry_flushes_latest_progress_and_honours_force_cancel(self) -> None:
        now = [10.0]
        calls: list[tuple[str, dict[str, object]]] = []
        cancel = [False]

        def update(action: str, payload: dict[str, object]) -> dict[str, object]:
            calls.append((action, payload))
            if action == "control" and cancel[0]:
                return {"cancel_requested": True, "force_cancel_requested": True}
            return {}

        telemetry = mushroom_worker_service._CoalescedJobTelemetry(
            update,
            base_payload={"job_id": "worker_job_test"},
            cancel_message="training cancelled",
            monotonic=lambda: now[0],
        )
        telemetry.publish({"phase": "first"})
        telemetry._wait_for_idle()
        telemetry.publish({"phase": "latest"})
        telemetry.flush()
        cancel[0] = True
        telemetry.poll_control(force=True)
        telemetry._wait_for_idle()

        with self.assertRaisesRegex(InterruptedError, "training cancelled") as raised:
            telemetry.poll_control()

        self.assertTrue(getattr(raised.exception, "force_cancel_requested"))
        self.assertEqual(
            [payload["phase"] for action, payload in calls if action == "progress"],
            ["first", "latest"],
        )

    def test_job_telemetry_network_wait_does_not_block_computation_callback(self) -> None:
        entered = threading.Event()
        release = threading.Event()

        def update(action: str, payload: dict[str, object]) -> dict[str, object]:
            entered.set()
            release.wait(1.0)
            return {}

        telemetry = mushroom_worker_service._CoalescedJobTelemetry(
            update,
            base_payload={"job_id": "worker_job_test"},
            cancel_message="training cancelled",
        )

        started = time.monotonic()
        telemetry.publish({"phase": "local computation continues"})
        elapsed = time.monotonic() - started

        self.assertTrue(entered.wait(0.5))
        self.assertLess(elapsed, 0.2)
        telemetry.publish({"phase": "latest state survives"})
        release.set()
        telemetry._wait_for_idle()
        telemetry.flush()

    def test_transient_telemetry_failure_does_not_abort_and_keeps_latest_progress(self) -> None:
        failing = [True]
        calls: list[tuple[str, dict[str, object]]] = []

        def update(action: str, payload: dict[str, object]) -> dict[str, object]:
            if failing[0]:
                raise URLError("coordinator unavailable")
            calls.append((action, payload))
            return {}

        telemetry = mushroom_worker_service._CoalescedJobTelemetry(
            update,
            base_payload={"job_id": "worker_job_test"},
            cancel_message="training cancelled",
        )

        telemetry.publish({"phase": "computed", "overall_percent": 90})
        telemetry.flush()
        failing[0] = False
        telemetry.flush()

        self.assertEqual(
            [payload["phase"] for action, payload in calls if action == "progress"],
            ["computed"],
        )

    def test_transient_retry_can_wait_without_deadline(self) -> None:
        attempts = [0]

        def operation() -> str:
            attempts[0] += 1
            if attempts[0] < 3:
                raise URLError("coordinator unavailable")
            return "delivered"

        with mock.patch.object(mushroom_worker_service.time, "sleep"):
            result = mushroom_worker_service.retry_transient(
                operation,
                retry_seconds=None,
                retry_interval=0.01,
            )

        self.assertEqual(result, "delivered")
        self.assertEqual(attempts[0], 3)

    def test_unbounded_delivery_retry_still_honours_cancellation(self) -> None:
        def operation() -> None:
            raise URLError("coordinator unavailable")

        def cancel() -> None:
            raise InterruptedError("cancelled from HA")

        with self.assertRaisesRegex(InterruptedError, "cancelled from HA"):
            mushroom_worker_service.retry_transient(
                operation,
                retry_seconds=None,
                on_retry=cancel,
            )

    def test_interactive_prediction_does_not_publish_synchronous_progress(self) -> None:
        service = mock.Mock()
        service.execute.return_value = {"metrics": {"backend_seconds": 2.6}}
        request = {"view": "week", "species_id": "amanita_caesarea"}

        result = mushroom_worker_service.execute_interactive_prediction(service, request)

        self.assertEqual(result["metrics"]["backend_seconds"], 2.6)
        service.execute.assert_called_once_with(request)

    def test_transient_transport_failure_is_retried(self) -> None:
        attempts = 0

        def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionResetError("temporary outage")
            return "recovered"

        result = mushroom_worker_service.retry_transient(
            operation,
            retry_seconds=1,
            retry_interval=0.001,
        )

        self.assertEqual(result, "recovered")
        self.assertEqual(attempts, 3)

    def test_job_update_exposes_coordinator_http_error_detail(self) -> None:
        rejected = mushroom_worker_service.HTTPError(
            "http://rainmapper/api/mushrooms/workers/jobs/finish",
            409,
            "Conflict",
            {},
            io.BytesIO(b'{"ok":false,"error":"exact contract failure"}'),
        )
        with mock.patch.object(
            mushroom_worker_service, "urlopen", side_effect=rejected
        ):
            with self.assertRaisesRegex(
                ValueError, "HTTP 409: exact contract failure"
            ):
                mushroom_worker_service.update_job(
                    "http://rainmapper", "finish", {"job_id": "worker_job_test"}
                )

    def test_transient_transport_retry_stops_at_deadline(self) -> None:
        with self.assertRaises(ConnectionResetError):
            mushroom_worker_service.retry_transient(
                lambda: (_ for _ in ()).throw(ConnectionResetError("offline")),
                retry_seconds=0,
            )

    def test_transient_transport_retry_honours_shutdown(self) -> None:
        stop_event = threading.Event()
        stop_event.set()
        with self.assertRaises(ConnectionResetError):
            mushroom_worker_service.retry_transient(
                lambda: (_ for _ in ()).throw(ConnectionResetError("offline")),
                retry_seconds=10,
                stop_event=stop_event,
            )

    def test_identity_is_generated_named_and_persisted_in_worker_volume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_data_dir = Path(temporary)
            first = mushroom_worker_service.ensure_worker_identity(
                worker_data_dir,
                host_name="macbook-m1-test",
            )
            second = mushroom_worker_service.ensure_worker_identity(
                worker_data_dir,
                host_name="macbook-m1-test",
            )
            renamed = mushroom_worker_service.ensure_worker_identity(
                worker_data_dir,
                display_name="M1 personal",
                host_name="macbook-m1-test",
            )

            identity_path = worker_data_dir / "identity/worker.json"
            stored = json.loads(identity_path.read_text(encoding="utf-8"))

        self.assertTrue(first["worker_id"].startswith("worker_"))
        self.assertEqual(second["worker_id"], first["worker_id"])
        self.assertEqual(first["display_name"], "macbook-m1-test")
        self.assertEqual(renamed["display_name"], "M1 personal")
        self.assertEqual(stored["worker_id"], first["worker_id"])

    def test_status_reports_idle_for_valid_cache(self) -> None:
        cache = {
            "status": "valid",
            "dataset_id": "mushroom_gis_v0",
            "fingerprint": "sha256:" + "a" * 64,
            "validation": "shallow",
            "file_count": 10,
            "size_bytes": 123,
        }
        with mock.patch.object(
            mushroom_worker_service.mushroom_worker_dataset_cache,
            "verify_version",
            return_value=cache,
        ):
            result = mushroom_worker_service.worker_status(
                Path("/unused"),
                worker_version="test",
                identity={
                    "worker_id": "worker_12345678",
                    "display_name": "M1 personal",
                    "host_name": "macbook-m1-test",
                },
            )

        self.assertEqual(result["status"], "idle")
        self.assertEqual(result["worker_version"], "test")
        self.assertEqual(result["worker_id"], "worker_12345678")
        self.assertEqual(result["display_name"], "M1 personal")
        self.assertEqual(result["host_name"], "macbook-m1-test")
        self.assertEqual(result["job_api"], "candidate_rebuild_v0")
        self.assertIn("weather_parquet_v1", result["capabilities"])
        self.assertIn("partitioned_weather_history_v1", result["capabilities"])
        self.assertIn("terminal_job_cleanup_v1", result["capabilities"])
        self.assertIn("predictor_weekly_model_selection_v2", result["capabilities"])
        self.assertIn("predictor_multiversion_v2", result["capabilities"])
        self.assertIn("ml_multiversion_training_v2", result["capabilities"])
        self.assertNotIn("predictor_multiversion_v1", result["capabilities"])
        self.assertNotIn("ml_multiversion_training_v1", result["capabilities"])
        self.assertIn("ml_job_purpose_v1", result["capabilities"])
        self.assertIn("ml_benchmark_report_v1", result["capabilities"])
        self.assertEqual(result["dataset_cache"]["file_count"], 10)

        heartbeat = mushroom_worker_service.heartbeat_payload(
            result,
            discarded_job_ids=["worker_job_discard123"],
            cleaned_job_ids=["worker_job_cleanup123"],
        )
        self.assertEqual(heartbeat["cleaned_job_ids"], ["worker_job_cleanup123"])

    def test_status_reports_missing_dataset_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = mushroom_worker_service.worker_status(Path(temporary))

        self.assertEqual(result["status"], "needs_dataset")
        self.assertEqual(result["dataset_cache"]["status"], "invalid")

    def test_heartbeat_is_sent_outbound_to_ha(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"ok": true, "worker_id": "worker_12345678"}'
        payload = {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": "worker_12345678",
        }
        with mock.patch.object(mushroom_worker_service, "urlopen", return_value=response) as urlopen:
            result = mushroom_worker_service.send_heartbeat(
                "http://rainmapper-ha-ui:8099",
                payload,
                token="secret",
                timeout=0.5,
            )

        request = urlopen.call_args.args[0]
        self.assertTrue(result["ok"])
        self.assertEqual(request.full_url, "http://rainmapper-ha-ui:8099/api/mushrooms/workers/heartbeat")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.headers["Authorization"], "Bearer secret")
        self.assertEqual(json.loads(request.data), payload)

    def test_worker_claims_jobs_outbound_from_ha(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"ok": true, "job": {"job_id": "worker_job_12345678", "job_type": "worker_claim_probe"}}'
        with mock.patch.object(mushroom_worker_service, "urlopen", return_value=response) as urlopen:
            job = mushroom_worker_service.claim_job(
                "http://rainmapper-ha-ui:8099",
                "worker_12345678",
                token="secret",
                timeout=0.5,
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(job["job_id"], "worker_job_12345678")
        self.assertEqual(request.full_url, "http://rainmapper-ha-ui:8099/api/mushrooms/workers/jobs/claim")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data), {"worker_id": "worker_12345678"})

    def test_predictor_runtime_manifest_is_downloaded_separately_from_compact_claim(self) -> None:
        manifest = {
            "schema_version": "1.0",
            "kind": "rainmapper_mushroom_predictor_runtime",
            "fingerprint": "sha256:" + "a" * 64,
            "files": [
                {
                    "path": "models/model.joblib",
                    "sha256": "sha256:" + "b" * 64,
                    "size_bytes": 0,
                }
            ],
        }
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"ok": True, "manifest": manifest}).encode()
        synchronized = (Path("/runtime"), {"status": "valid"})
        compact_job = {
            "job_id": "worker_job_predict123",
            "runtime_endpoint": "/api/mushrooms/workers/jobs/predictor-runtime",
            "runtime_manifest_ref": {"fingerprint": manifest["fingerprint"]},
        }
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.object(
                mushroom_worker_service,
                "urlopen",
                side_effect=[
                    response,
                    HTTPError(
                        "http://rainmapper-ha-ui:8099/api/mushrooms/workers/jobs/predictor-runtime",
                        409,
                        "archive unsupported",
                        {},
                        None,
                    ),
                ],
            ) as urlopen,
            mock.patch.object(
                mushroom_worker_service.mushroom_predictor_runtime,
                "synchronize_runtime",
                return_value=synchronized,
            ) as synchronize,
        ):
            result = mushroom_worker_service.download_predictor_runtime(
                "http://rainmapper-ha-ui:8099",
                compact_job,
                Path(temporary),
                worker_id="worker_12345678",
                claim_token="claim-secret",
                token="coordinator-secret",
            )

        request = urlopen.call_args_list[0].args[0]
        self.assertEqual(result, synchronized)
        self.assertIn("manifest=1", request.full_url)
        self.assertNotIn("file=", request.full_url)
        self.assertIn("archive=1", urlopen.call_args_list[1].args[0].full_url)
        self.assertEqual(synchronize.call_args.args[1], manifest)
        self.assertEqual(compact_job["runtime_manifest"], manifest)

    def test_predictor_runtime_uses_delta_protocol_when_local_objects_exist(self) -> None:
        manifest = {
            "schema_version": "1.0",
            "kind": "rainmapper_mushroom_predictor_runtime",
            "fingerprint": "sha256:" + "a" * 64,
            "files": [
                {
                    "path": "models/model.joblib",
                    "sha256": "sha256:" + "b" * 64,
                    "size_bytes": 0,
                }
            ],
        }
        synchronized = (Path("/runtime"), {"status": "synchronized"})
        job = {
            "job_id": "worker_job_predict123",
            "runtime_endpoint": "/api/mushrooms/workers/jobs/predictor-runtime",
            "runtime_manifest": manifest,
        }
        with tempfile.TemporaryDirectory() as temporary:
            objects = Path(temporary) / "predictor-runtime" / "objects"
            objects.mkdir(parents=True)
            (objects / ("b" * 64)).write_bytes(b"")
            with (
                mock.patch.object(mushroom_worker_service, "urlopen") as urlopen,
                mock.patch.object(
                    mushroom_worker_service.mushroom_predictor_runtime,
                    "synchronize_runtime",
                    return_value=synchronized,
                ) as synchronize,
            ):
                result = mushroom_worker_service.download_predictor_runtime(
                    "http://rainmapper-ha-ui:8099",
                    job,
                    Path(temporary),
                    worker_id="worker_12345678",
                    claim_token="claim-secret",
                    token="coordinator-secret",
                )

        self.assertEqual(result, synchronized)
        urlopen.assert_not_called()
        self.assertEqual(synchronize.call_args.args[1], manifest)

    def test_predictor_runtime_is_namespaced_by_coordinator(self) -> None:
        manifest = {
            "schema_version": "1.0",
            "kind": "rainmapper_mushroom_predictor_runtime",
            "fingerprint": "sha256:" + "a" * 64,
            "files": [
                {
                    "path": "models/model.joblib",
                    "sha256": "sha256:" + "b" * 64,
                    "size_bytes": 0,
                }
            ],
        }
        synchronized = (Path("/runtime"), {"status": "synchronized"})
        job = {
            "job_id": "worker_job_predict123",
            "runtime_endpoint": "/api/mushrooms/workers/jobs/predictor-runtime",
            "runtime_manifest": manifest,
        }
        with tempfile.TemporaryDirectory() as temporary:
            shared_objects = Path(temporary) / "predictor-runtime/objects"
            shared_objects.mkdir(parents=True)
            (shared_objects / ("b" * 64)).write_bytes(b"")
            with (
                mock.patch.object(mushroom_worker_service, "urlopen") as urlopen,
                mock.patch.object(
                    mushroom_worker_service.mushroom_predictor_runtime,
                    "synchronize_runtime",
                    return_value=synchronized,
                ) as synchronize,
            ):
                result = mushroom_worker_service.download_predictor_runtime(
                    "http://rainmapper-ha-ui:8099",
                    job,
                    Path(temporary),
                    worker_id="worker_12345678",
                    claim_token="claim-secret",
                    token="coordinator-secret",
                    coordinator_id="coordinator_1234567890abcdef",
                )

        self.assertEqual(synchronized, result)
        urlopen.assert_not_called()
        self.assertEqual(
            Path(temporary).resolve()
            / "predictor-runtime/coordinators/coordinator_1234567890abcdef",
            synchronize.call_args.args[0],
        )
        self.assertEqual(
            Path(temporary).resolve() / "predictor-runtime/objects",
            synchronize.call_args.kwargs["objects_root"],
        )

    def test_predictor_runtime_uses_delta_protocol_when_current_runtime_exists(self) -> None:
        manifest = {
            "schema_version": "1.0",
            "kind": "rainmapper_mushroom_predictor_runtime",
            "fingerprint": "sha256:" + "a" * 64,
            "files": [
                {
                    "path": "models/model.joblib",
                    "sha256": "sha256:" + "b" * 64,
                    "size_bytes": 0,
                }
            ],
        }
        synchronized = (Path("/runtime"), {"status": "reused"})
        job = {
            "job_id": "worker_job_predict123",
            "runtime_endpoint": "/api/mushrooms/workers/jobs/predictor-runtime",
            "runtime_manifest": manifest,
        }
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.object(mushroom_worker_service, "urlopen") as urlopen,
            mock.patch.object(
                mushroom_worker_service.mushroom_predictor_runtime,
                "current_runtime",
                return_value=Path("/runtime"),
            ),
            mock.patch.object(
                mushroom_worker_service.mushroom_predictor_runtime,
                "synchronize_runtime",
                return_value=synchronized,
            ) as synchronize,
        ):
            result = mushroom_worker_service.download_predictor_runtime(
                "http://rainmapper-ha-ui:8099",
                job,
                Path(temporary),
                worker_id="worker_12345678",
                claim_token="claim-secret",
                token="coordinator-secret",
            )

        self.assertEqual(result, synchronized)
        urlopen.assert_not_called()
        self.assertEqual(synchronize.call_args.args[1], manifest)

    def test_predictor_runtime_falls_back_when_archive_is_invalid(self) -> None:
        manifest = {
            "schema_version": "1.0",
            "kind": "rainmapper_mushroom_predictor_runtime",
            "fingerprint": "sha256:" + "a" * 64,
            "files": [
                {
                    "path": "models/model.joblib",
                    "sha256": "sha256:" + "b" * 64,
                    "size_bytes": 0,
                }
            ],
        }
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = [b"not-a-tar", b""]
        synchronized = (Path("/runtime"), {"status": "synchronized"})
        job = {
            "job_id": "worker_job_predict123",
            "runtime_endpoint": "/api/mushrooms/workers/jobs/predictor-runtime",
            "runtime_manifest": manifest,
        }
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.object(
                mushroom_worker_service, "urlopen", return_value=response
            ) as urlopen,
            mock.patch.object(
                mushroom_worker_service.mushroom_predictor_runtime,
                "synchronize_runtime",
                return_value=synchronized,
            ) as synchronize,
        ):
            result = mushroom_worker_service.download_predictor_runtime(
                "http://rainmapper-ha-ui:8099",
                job,
                Path(temporary),
                worker_id="worker_12345678",
                claim_token="claim-secret",
                token="coordinator-secret",
            )

        self.assertEqual(result, synchronized)
        self.assertIn("archive=1", urlopen.call_args.args[0].full_url)
        self.assertEqual(synchronize.call_args.args[1], manifest)

    def test_worker_updates_job_lifecycle_outbound_to_ha(self) -> None:
        for action in ("start", "progress", "control", "finish"):
            with self.subTest(action=action):
                response = mock.MagicMock()
                response.__enter__.return_value = response
                response.read.return_value = b'{"ok": true, "job": {"job_id": "worker_job_12345678"}}'
                payload = {
                    "job_id": "worker_job_12345678",
                    "worker_id": "worker_12345678",
                    "claim_token": "claim-secret",
                }
                with mock.patch.object(mushroom_worker_service, "urlopen", return_value=response) as urlopen:
                    result = mushroom_worker_service.update_job(
                        "http://rainmapper-ha-ui:8099",
                        action,
                        payload,
                        token="coordinator-secret",
                        timeout=0.5,
                    )

                request = urlopen.call_args.args[0]
                self.assertTrue(result["ok"])
                self.assertEqual(
                    request.full_url,
                    f"http://rainmapper-ha-ui:8099/api/mushrooms/workers/jobs/{action}",
                )
                self.assertEqual(request.headers["Authorization"], "Bearer coordinator-secret")
                self.assertEqual(json.loads(request.data), payload)

    def test_predictor_finish_has_a_longer_bounded_timeout(self) -> None:
        self.assertEqual(
            mushroom_worker_service._job_update_timeout(
                "finish", "worker_predictor_v1"
            ),
            60.0,
        )
        self.assertEqual(
            mushroom_worker_service._job_update_timeout(
                "finish", "worker_ml_multiversion_v1"
            ),
            3.0,
        )
        for action in ("start", "progress", "control"):
            with self.subTest(action=action):
                self.assertEqual(
                    mushroom_worker_service._job_update_timeout(
                        action, "worker_predictor_v1"
                    ),
                    3.0,
                )

    def test_worker_rejects_unknown_job_lifecycle_action(self) -> None:
        with self.assertRaisesRegex(ValueError, "action is invalid"):
            mushroom_worker_service.update_job(
                "http://rainmapper-ha-ui:8099",
                "delete",
                {},
            )


if __name__ == "__main__":
    unittest.main()
