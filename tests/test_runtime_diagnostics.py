"""Tests for the bounded, best-effort runtime diagnostics log."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest import mock

from rainmapper_core import runtime_diagnostics


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_snapshot_exposes_process_cpu_and_memory_fields(self) -> None:
        current = runtime_diagnostics.snapshot()

        self.assertEqual(current["pid"], runtime_diagnostics.os.getpid())
        self.assertIn("process_rss_mib", current)
        self.assertIn("process_peak_rss_mib", current)
        self.assertIn("cgroup_memory_current_mib", current)
        self.assertIn("host_mem_available_mib", current)
        self.assertIsInstance(current["cpu_user_seconds"], float)
        self.assertIsInstance(current["cpu_system_seconds"], float)
        self.assertTrue(current["timestamp"].endswith("Z"))

    def test_operation_monitor_records_phases_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            monitor = runtime_diagnostics.OperationMonitor(
                "unit_operation",
                details={"path": Path("/private/value.csv")},
                path=metrics_path,
                sample_interval_seconds=0.01,
            )
            time.sleep(0.06)
            monitor.mark("middle", {"records": 12})
            monitor.finish("ok", {"result": "done"})
            monitor.finish("duplicate_must_be_ignored")

            records = [
                json.loads(line)
                for line in metrics_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual([record["phase"] for record in records], ["start", "middle", "finish"])
        self.assertEqual(len({record["operation_id"] for record in records}), 1)
        self.assertEqual(records[0]["details"]["path"], "value.csv")
        summary = records[-1]["details"]
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(summary["result"], "done")
        self.assertGreaterEqual(summary["wall_seconds"], 0.05)
        self.assertIn("max_process_peak_rss_mib", summary)

    def test_retention_keeps_only_the_most_recent_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            with mock.patch.object(runtime_diagnostics, "MAX_RECORDS", 3):
                for index in range(5):
                    runtime_diagnostics.record_event(
                        "retention",
                        "same-operation",
                        f"phase-{index}",
                        path=metrics_path,
                    )
            records = [
                json.loads(line)
                for line in metrics_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(
            [record["phase"] for record in records],
            ["phase-2", "phase-3", "phase-4"],
        )

    def test_export_bundle_contains_only_manifest_metrics_and_last_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            metrics_path = data_dir / "runtime_metrics.jsonl"
            last_run_path = data_dir / "last_run.log"
            unrelated_secret = data_dir / "secrets.json"
            metrics_path.write_text('{"phase":"finish"}\n', encoding="utf-8")
            last_run_path.write_text(
                "runner output https://example.test?apiKey=TOP-SECRET&day=1\n"
                "Authorization: Bearer PRIVATE-TOKEN\n",
                encoding="utf-8",
            )
            unrelated_secret.write_text("DO_NOT_EXPORT", encoding="utf-8")

            payload = runtime_diagnostics.export_bundle(
                last_run_log_path=last_run_path,
                app_version="0.2.test",
                path=metrics_path,
            )

        with zipfile.ZipFile(BytesIO(payload)) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {"manifest.json", "runtime_metrics.jsonl", "last_run.log"},
            )
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["app_version"], "0.2.test")
            exported_log = archive.read("last_run.log")
            self.assertIn(b"apiKey=[REDACTED]&day=1", exported_log)
            self.assertIn(b"Authorization: Bearer [REDACTED]", exported_log)
            self.assertNotIn(b"TOP-SECRET", exported_log)
            self.assertNotIn(b"PRIVATE-TOKEN", exported_log)
            self.assertNotIn(b"DO_NOT_EXPORT", payload)

    def test_export_bundle_limits_last_run_log_to_its_recent_tail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            metrics_path = data_dir / "runtime_metrics.jsonl"
            last_run_path = data_dir / "last_run.log"
            metrics_path.write_text("", encoding="utf-8")
            last_run_path.write_bytes(b"old-secret-line\n" + b"recent-line\n" * 4)
            with mock.patch.object(runtime_diagnostics, "MAX_LOG_EXPORT_BYTES", 30):
                payload = runtime_diagnostics.export_bundle(
                    last_run_log_path=last_run_path,
                    app_version="test",
                    path=metrics_path,
                )

        with zipfile.ZipFile(BytesIO(payload)) as archive:
            exported_log = archive.read("last_run.log")
        self.assertIn(b"Earlier log output omitted", exported_log)
        self.assertIn(b"recent-line", exported_log)
        self.assertNotIn(b"old-secret-line", exported_log)

    def test_unwritable_diagnostics_path_never_breaks_the_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            directory_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            directory_path.mkdir()
            result = runtime_diagnostics.record_event(
                "best_effort",
                "test-id",
                "start",
                path=directory_path,
            )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
