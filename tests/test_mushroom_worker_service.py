import json
import io
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_worker_service


class MushroomWorkerServiceTests(unittest.TestCase):
    def test_job_telemetry_coalesces_progress_and_control_every_two_seconds(self) -> None:
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
        telemetry.publish({"phase": "intermediate", "overall_percent": 20})
        now[0] = 11.9
        telemetry.publish({"phase": "newest pending", "overall_percent": 30})
        now[0] = 12.0
        telemetry.publish({"phase": "two seconds", "overall_percent": 40})

        self.assertEqual([action for action, _ in calls], ["control", "progress", "control", "progress"])
        self.assertEqual(
            [payload["phase"] for action, payload in calls if action == "progress"],
            ["first", "two seconds"],
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
        telemetry.publish({"phase": "latest"})
        telemetry.flush()
        cancel[0] = True

        with self.assertRaisesRegex(InterruptedError, "training cancelled") as raised:
            telemetry.poll_control(force=True)

        self.assertTrue(getattr(raised.exception, "force_cancel_requested"))
        self.assertEqual(
            [payload["phase"] for action, payload in calls if action == "progress"],
            ["first", "latest"],
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
        self.assertIn("terminal_job_cleanup_v1", result["capabilities"])
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

    def test_worker_rejects_unknown_job_lifecycle_action(self) -> None:
        with self.assertRaisesRegex(ValueError, "action is invalid"):
            mushroom_worker_service.update_job(
                "http://rainmapper-ha-ui:8099",
                "delete",
                {},
            )


if __name__ == "__main__":
    unittest.main()
