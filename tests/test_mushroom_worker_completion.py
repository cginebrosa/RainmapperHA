import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_worker_jobs as jobs
from rainmapper_core import mushroom_worker_transport as transport
from rainmapper_core.mushroom_worker_completion import (
    JobUpdateRejected, MAX_NOTICE_BYTES, PrecomputeCompletion,
)


class PrecomputeCompletionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.completion = PrecomputeCompletion(self.root / "predictor_precompute")
        self.payload = {
            "job_id": "worker_job_completion",
            "worker_id": "worker_aaaaaaaa",
            "claim_token": "private-claim",
            "status": "complete",
            "result": {"publication_receipt": {"artifact_id": "sha256:" + "a" * 64}, "worker_activation": "active"},
        }
        self.queue = self.root / "jobs.json"
        self.queue.write_text(json.dumps({**jobs.empty_queue(), "jobs": [{
            **{key: self.payload[key] for key in ("job_id", "worker_id", "claim_token")},
            "job_type": jobs.JOB_TYPE_PREDICTOR_PRECOMPUTE,
            "target_worker_id": self.payload["worker_id"],
            "artifact_id": "sha256:" + "a" * 64,
            "status": "running", "lane": "background",
        }]}))

    def send(self, action, payload):
        try:
            if action == "control":
                job = jobs.poll_job(self.queue, **payload)
                return {"ok": True, "job": job, "cancel_requested": job["status"] == "cancel_requested"}
            return {"ok": True, "job": jobs.finish_job(self.queue, **payload)}
        except ValueError as exc:
            raise JobUpdateRejected(action, 409, str(exc)) from exc

    def test_acknowledgement_lost_after_ha_completed_survives_restart(self):
        self.completion.remember(self.payload)

        def lose_response(action, payload):
            self.send(action, payload)
            raise TimeoutError("response lost after HA committed")

        with self.assertRaises(TimeoutError):
            self.completion.deliver(lose_response)
        restarted = PrecomputeCompletion(self.completion.path.parent)
        kept = restarted.remember({**self.payload, "status": "failed", "error": "timeout"})
        self.assertEqual(kept["status"], "complete")
        result = restarted.deliver(self.send)
        self.assertTrue(result["job"]["finish_reused"])
        self.assertEqual(jobs.load_queue(self.queue)["jobs"][0]["status"], "complete")
        self.assertIsNone(restarted.pending())

    def test_failed_delivery_eventually_finishes_job_without_result(self):
        payload = {key: value for key, value in self.payload.items() if key != "result"}
        payload.update(status="failed", error="Connection refused while uploading")
        self.completion.remember(payload)
        for error in (ConnectionRefusedError(), TimeoutError(), JobUpdateRejected("finish", 503, "offline")):
            with self.assertRaises(type(error)):
                self.completion.deliver(mock.Mock(side_effect=error))
            self.assertEqual(self.completion.pending(), payload)
        result = self.completion.deliver(self.send)
        self.assertEqual(result["job"]["status"], "failed")
        self.assertEqual(result["job"]["error"], payload["error"])

    def test_operator_abandonment_cannot_be_resurrected(self):
        self.completion.remember(self.payload)
        jobs.request_cancel(self.queue, job_id=self.payload["job_id"])
        jobs.abandon_stuck_job(self.queue, job_id=self.payload["job_id"])
        before = self.queue.read_bytes()
        self.assertTrue(self.completion.deliver(self.send)["finish_superseded"])
        self.assertEqual(self.queue.read_bytes(), before)
        self.assertIsNone(self.completion.pending())

    def test_cooperative_cancellation_is_acknowledged_instead_of_success(self):
        self.completion.remember(self.payload)
        jobs.request_cancel(self.queue, job_id=self.payload["job_id"])
        result = self.completion.deliver(self.send)
        self.assertEqual(result["job"]["status"], "cancelled")
        self.assertIsNone(self.completion.pending())

    def test_lost_cancellation_acknowledgement_keeps_cancelled_notice(self):
        self.completion.remember(self.payload)
        jobs.request_cancel(self.queue, job_id=self.payload["job_id"])

        def lose_cancel(action, payload):
            result = self.send(action, payload)
            if action == "finish" and payload["status"] == "cancelled":
                raise TimeoutError()
            return result

        with self.assertRaises(TimeoutError):
            self.completion.deliver(lose_cancel)
        self.assertEqual(self.completion.pending()["status"], "cancelled")
        self.assertEqual(self.completion.deliver(self.send)["job"]["status"], "cancelled")

    def test_stale_claim_does_not_change_new_assignment(self):
        self.completion.remember({**self.payload, "claim_token": "old-claim"})
        before = self.queue.read_bytes()
        self.assertTrue(self.completion.deliver(self.send)["finish_superseded"])
        self.assertEqual(self.queue.read_bytes(), before)

    def test_authentication_and_unknown_rejections_keep_notice(self):
        self.completion.remember(self.payload)
        for code, detail in [(401, "Unauthorized"), (409, "unexpected conflict"), (404, "unknown job")]:
            with self.assertRaises(JobUpdateRejected):
                self.completion.deliver(mock.Mock(side_effect=JobUpdateRejected("finish", code, detail)))
            self.assertEqual(self.completion.pending(), self.payload)

    def test_job_removed_from_ha_history_does_not_block_future_work(self):
        self.completion.remember(self.payload)
        self.queue.write_text(json.dumps(jobs.empty_queue()))
        self.assertTrue(self.completion.deliver(self.send)["finish_superseded"])
        self.assertIsNone(self.completion.pending())

    def test_notice_is_private_bounded_and_not_in_job_cleanup(self):
        with self.assertRaisesRegex(ValueError, "too large"):
            self.completion.remember({**self.payload, "error": "x" * MAX_NOTICE_BYTES})
        self.assertFalse(self.completion.path.exists())
        self.completion.remember(self.payload)
        self.assertEqual(stat.S_IMODE(self.completion.path.stat().st_mode), 0o600)
        self.assertLess(self.completion.path.stat().st_size, 1024)
        transport.discard_worker_job(self.root, self.payload["job_id"])
        self.assertEqual(self.completion.pending(), self.payload)

    def test_cannot_overwrite_pending_job_and_coordinators_are_isolated(self):
        self.completion.remember(self.payload)
        other = {**self.payload, "job_id": "worker_job_other123"}
        with self.assertRaisesRegex(ValueError, "awaiting acknowledgement"):
            self.completion.remember(other)
        secondary = PrecomputeCompletion(self.root / "coordinators/coordinator_secondary/predictor_precompute")
        secondary.remember(other)
        secondary.deliver(lambda *_: {"ok": True, "job": {}})
        self.assertEqual(self.completion.pending(), self.payload)


if __name__ == "__main__":
    unittest.main()
