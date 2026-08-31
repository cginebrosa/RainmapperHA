import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core.mushroom_storage_reconciler import reconcile_worker_storage


class MushroomStorageReconcilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.queue_path = self.root / "mushroom_worker_jobs.json"
        self.bundle_root = self.root / ".worker-input-bundles"
        self.result_root = self.root / ".worker-candidate-results"
        self.bundle_root.mkdir()
        self.result_root.mkdir()

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_dry_run_is_read_only_and_apply_executes_the_same_safe_plan(self) -> None:
        bundle_job_id = "worker_job_bundleterminal1"
        result_job_id = "worker_job_resultpromoted1"
        self._write_json(
            self.queue_path,
            {
                "schema_version": "0.1",
                "storage_version": "2.0",
                "jobs": [
                    {
                        "job_id": bundle_job_id,
                        "job_type": "worker_snapshot_transport_probe",
                        "status": "complete",
                    },
                    {
                        "job_id": result_job_id,
                        "job_type": "worker_candidate_rebuild",
                        "status": "complete",
                        "promotion_status": "promoted",
                    },
                ],
            },
        )
        bundle = self.bundle_root / bundle_job_id
        self._write_json(bundle / "job_spec.json", {"job_id": bundle_job_id})
        (bundle / "payload.bin").write_bytes(b"bundle")
        result = self.result_root / result_job_id
        self._write_json(
            result / "promotion_receipt.json",
            {
                "kind": "rainmapper_worker_candidate_promotion",
                "status": "promoted",
                "job_id": result_job_id,
            },
        )
        (result / "payload.bin").write_bytes(b"result")
        orphan_job_id = "worker_job_orphanresult123"
        orphan = self.result_root / orphan_job_id
        self._write_json(
            orphan / "candidate_verification.json",
            {
                "kind": "rainmapper_worker_candidate_verification",
                "status": "verified",
                "job_id": orphan_job_id,
            },
        )
        (orphan / "payload.bin").write_bytes(b"orphan")
        os_time = 0
        import os
        os.utime(orphan, (os_time, os_time))
        empty_job_id = "worker_job_emptyorphan123"
        empty_orphan = self.result_root / empty_job_id
        empty_orphan.mkdir()
        os.utime(empty_orphan, (os_time, os_time))
        backup_root = self.queue_path.parent / ".worker-promotion-backups"
        older_backup = backup_root / "worker_job_rollbackolder1"
        current_backup = backup_root / "worker_job_rollbackcurrent1"
        older_backup.mkdir(parents=True)
        current_backup.mkdir()
        (older_backup / "payload.bin").write_bytes(b"old rollback")
        (current_backup / "payload.bin").write_bytes(b"current rollback")
        os.utime(older_backup, ns=(1, 1))
        os.utime(current_backup, ns=(2, 2))

        dry_run = reconcile_worker_storage(
            queue_path=self.queue_path,
            bundle_root=self.bundle_root,
            result_root=self.result_root,
            apply=False,
            now=100_000.0,
            staging_grace_seconds=0,
            orphan_grace_seconds=0,
        )

        self.assertEqual(dry_run["mode"], "dry-run")
        self.assertEqual(dry_run["summary"]["planned_entries"], 5)
        self.assertGreater(dry_run["summary"]["recoverable_bytes"], 0)
        self.assertIsNone(dry_run["execution"])
        self.assertTrue(bundle.is_dir())
        self.assertTrue(result.is_dir())
        self.assertTrue(orphan.is_dir())
        self.assertTrue(empty_orphan.is_dir())
        self.assertTrue(older_backup.is_dir())
        self.assertTrue(current_backup.is_dir())

        applied = reconcile_worker_storage(
            queue_path=self.queue_path,
            bundle_root=self.bundle_root,
            result_root=self.result_root,
            report_path=self.root / "diagnostics" / "storage_reconciliation.json",
            apply=True,
            now=100_000.0,
            staging_grace_seconds=0,
            orphan_grace_seconds=0,
        )

        self.assertEqual(applied["mode"], "apply")
        self.assertEqual(applied["summary"]["planned_entries"], 5)
        self.assertFalse(bundle.exists())
        self.assertFalse(result.exists())
        self.assertFalse(orphan.exists())
        self.assertFalse(empty_orphan.exists())
        self.assertFalse(older_backup.exists())
        self.assertTrue(current_backup.is_dir())
        persisted = json.loads(
            (self.root / "diagnostics" / "storage_reconciliation.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(persisted["summary"]["removed_entries"], 5)
        self.assertIn("predictor_runtime_archive", persisted)
        self.assertEqual(
            persisted["predictor_runtime_archive"]["legacy_cleanup_state"],
            "absent",
        )
        self.assertEqual(
            applied["execution"]["bundles"]["discarded_terminal"],
            [bundle_job_id],
        )
        self.assertEqual(
            applied["execution"]["results"]["discarded"],
            [result_job_id],
        )
        self.assertEqual(
            applied["execution"]["orphan_results"]["removed"],
            [orphan_job_id, empty_job_id],
        )
        self.assertEqual(
            applied["execution"]["promotion_backups"]["removed"],
            [older_backup.name],
        )

    def test_dry_run_refuses_symlink_without_following_it(self) -> None:
        target = self.root / "outside"
        target.mkdir()
        symlink = self.bundle_root / "worker_job_symlink1234"
        symlink.symlink_to(target, target_is_directory=True)
        self._write_json(
            self.queue_path,
            {"schema_version": "0.1", "storage_version": "2.0", "jobs": []},
        )

        report = reconcile_worker_storage(
            queue_path=self.queue_path,
            bundle_root=self.bundle_root,
            result_root=self.result_root,
            apply=False,
            now=100_000.0,
            orphan_grace_seconds=0,
        )

        self.assertEqual(report["summary"]["planned_entries"], 0)
        self.assertEqual(report["summary"]["errors"], 1)
        self.assertTrue(target.is_dir())
        self.assertTrue(symlink.is_symlink())

    def test_terminal_operational_results_are_retained_for_24_hours(self) -> None:
        old_job_id = "worker_job_failedresult1"
        recent_job_id = "worker_job_failedresult2"
        self._write_json(
            self.queue_path,
            {
                "schema_version": "0.1",
                "storage_version": "2.0",
                "jobs": [
                    {
                        "job_id": old_job_id,
                        "job_type": "worker_candidate_rebuild",
                        "status": "failed",
                        "finished_at": "1970-01-01T03:46:39+00:00",
                    },
                    {
                        "job_id": recent_job_id,
                        "job_type": "worker_ml_multiversion_v1",
                        "job_purpose": "operational",
                        "status": "failed",
                        "finished_at": "1970-01-02T03:46:39+00:00",
                    },
                ],
            },
        )
        old_result = self.result_root / old_job_id
        recent_result = self.result_root / recent_job_id
        (old_result / "partial.bin").parent.mkdir(parents=True)
        (old_result / "partial.bin").write_bytes(b"old")
        (recent_result / "partial.bin").parent.mkdir(parents=True)
        (recent_result / "partial.bin").write_bytes(b"recent")

        report = reconcile_worker_storage(
            queue_path=self.queue_path,
            bundle_root=self.bundle_root,
            result_root=self.result_root,
            apply=True,
            now=100_000.0,
        )

        self.assertFalse(old_result.exists())
        self.assertTrue(recent_result.is_dir())
        self.assertEqual(
            [row["job_id"] for row in report["plan"]["orphan_results"]["planned_terminal"]],
            [old_job_id],
        )


if __name__ == "__main__":
    unittest.main()
