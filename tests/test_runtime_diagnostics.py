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
        self.assertIn("host_boot_id", current)
        self.assertIn("host_uptime_seconds", current)
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
            summaries = [
                json.loads(line)
                for line in runtime_diagnostics.summary_path(metrics_path)
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            state = json.loads(
                runtime_diagnostics.state_path(metrics_path).read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual([record["phase"] for record in records], ["start", "middle", "finish"])
        self.assertEqual(len({record["operation_id"] for record in records}), 1)
        self.assertEqual(records[0]["details"]["path"], "value.csv")
        summary = records[-1]["details"]
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(summary["result"], "done")
        self.assertGreaterEqual(summary["wall_seconds"], 0.05)
        self.assertIn("max_process_peak_rss_mib", summary)
        self.assertEqual(summaries[-1]["status"], "ok")
        self.assertNotIn(monitor.operation_id, state["pending_operations"])

    def test_operation_monitor_persists_running_heartbeats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            monitor = runtime_diagnostics.OperationMonitor(
                "heartbeat_operation",
                path=metrics_path,
                sample_interval_seconds=0.01,
                heartbeat_interval_seconds=0.02,
            )
            time.sleep(0.09)
            monitor.finish("ok")
            records = [
                json.loads(line)
                for line in metrics_path.read_text(encoding="utf-8").splitlines()
            ]

        heartbeats = [record for record in records if record["phase"] == "heartbeat"]
        self.assertGreaterEqual(len(heartbeats), 1)
        self.assertEqual(heartbeats[-1]["details"]["status"], "running")
        self.assertGreater(heartbeats[-1]["details"]["elapsed_seconds"], 0)
        self.assertIn("max_cgroup_memory_current_mib", heartbeats[-1]["details"])

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

    def test_export_bundle_contains_persistent_black_box_and_last_log(self) -> None:
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
                {
                    "manifest.json",
                    "runtime_metrics.jsonl",
                    "runtime_summary.jsonl",
                    "runtime_anomalies.jsonl",
                    "runtime_state.json",
                    "last_run.log",
                },
            )
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["app_version"], "0.2.test")
            exported_log = archive.read("last_run.log")
            self.assertIn(b"apiKey=[REDACTED]&day=1", exported_log)
            self.assertIn(b"Authorization: Bearer [REDACTED]", exported_log)
            self.assertNotIn(b"TOP-SECRET", exported_log)
            self.assertNotIn(b"PRIVATE-TOKEN", exported_log)
            self.assertNotIn(b"DO_NOT_EXPORT", payload)

    def test_initialize_reconciles_pending_operation_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            monitor = runtime_diagnostics.OperationMonitor(
                "unfinished_operation",
                path=metrics_path,
                sample_interval_seconds=60,
            )
            timer = runtime_diagnostics.schedule_snapshot(
                "unfinished_operation",
                monitor.operation_id,
                "recovery_600s",
                600,
                path=metrics_path,
            )
            monitor._stop_event.set()
            if monitor._thread is not None:
                monitor._thread.join(timeout=1)
            timer.cancel()

            runtime_diagnostics.initialize_runtime("test-next-boot", metrics_path)

            records = [
                json.loads(line)
                for line in metrics_path.read_text(encoding="utf-8").splitlines()
            ]
            summaries = [
                json.loads(line)
                for line in runtime_diagnostics.summary_path(metrics_path)
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            state = json.loads(
                runtime_diagnostics.state_path(metrics_path).read_text(
                    encoding="utf-8"
                )
            )

        self.assertIn("interrupted", [record["phase"] for record in records])
        self.assertIn(
            "snapshot_interrupted", [record["phase"] for record in records]
        )
        self.assertEqual(summaries[-1]["status"], "interrupted")
        self.assertEqual(state["pending_operations"], {})
        self.assertEqual(state["pending_snapshots"], {})

    def test_initialize_archives_interrupted_runner_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            metrics_path = data_dir / "runtime_metrics.jsonl"
            last_run_path = data_dir / "last_run.log"
            last_run_path.write_text(
                "partial runner api_key=SECRET\n",
                encoding="utf-8",
            )
            monitor = runtime_diagnostics.OperationMonitor(
                "runner_action",
                path=metrics_path,
                heartbeat_interval_seconds=60,
            )
            monitor._stop_event.set()
            if monitor._thread is not None:
                monitor._thread.join(timeout=1)

            runtime_diagnostics.initialize_runtime(
                "test-next-boot",
                metrics_path,
                last_run_log_path=last_run_path,
            )
            archived_path = (
                runtime_diagnostics.failure_logs_path(metrics_path)
                / f"{monitor.operation_id}.log"
            )
            archived = archived_path.read_text(encoding="utf-8")
            summary = json.loads(
                runtime_diagnostics.summary_path(metrics_path)
                .read_text(encoding="utf-8")
                .splitlines()[-1]
            )

        self.assertIn("api_key=[REDACTED]", archived)
        self.assertNotIn("SECRET", archived)
        self.assertTrue(summary["details"]["interrupted_log_archived"])

    def test_scheduled_snapshot_is_summarized_and_cleared_from_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            timer = runtime_diagnostics.schedule_snapshot(
                "completed_operation",
                "completed-operation-id",
                "recovery_60s",
                0.01,
                path=metrics_path,
            )
            timer.join(timeout=1)
            state = json.loads(
                runtime_diagnostics.state_path(metrics_path).read_text(
                    encoding="utf-8"
                )
            )
            summary = json.loads(
                runtime_diagnostics.summary_path(metrics_path)
                .read_text(encoding="utf-8")
                .splitlines()[-1]
            )

        self.assertFalse(timer.is_alive())
        self.assertEqual(state["pending_snapshots"], {})
        self.assertEqual(summary["status"], "snapshot")
        self.assertEqual(summary["details"]["phase"], "recovery_60s")

    def test_clean_shutdown_is_not_reconciled_as_interrupted_boot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            first_boot = runtime_diagnostics.initialize_runtime("test", metrics_path)
            runtime_diagnostics.shutdown_runtime(metrics_path)
            runtime_diagnostics.initialize_runtime("test", metrics_path)
            records = [
                json.loads(line)
                for line in metrics_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertFalse(
            any(
                record.get("operation") == "runtime_boot"
                and record.get("operation_id") == first_boot
                and record.get("phase") == "interrupted"
                for record in records
            )
        )

    def test_client_timing_accepts_only_allow_listed_non_private_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            operation_id = "20260808T120000Z-predictor_request-1234abcd"
            runtime_diagnostics.record_event(
                "predictor_request",
                operation_id,
                "start",
                path=metrics_path,
            )
            accepted = runtime_diagnostics.record_predictor_client_timing(
                operation_id,
                {
                    "response_start_ms": 123.4,
                    "load_event_ms": 456.7,
                    "navigation_type": "navigate",
                    "species": "private-species",
                    "area": "private-area",
                },
                metrics_path,
            )
            record = json.loads(
                metrics_path.read_text(encoding="utf-8").splitlines()[-1]
            )

        self.assertTrue(accepted)
        self.assertEqual(record["details"]["response_start_ms"], 123.4)
        self.assertNotIn("species", record["details"])
        self.assertNotIn("area", record["details"])

    def test_nested_operation_records_parent_correlation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            with runtime_diagnostics.operation_context("parent-request-12345678"):
                monitor = runtime_diagnostics.OperationMonitor(
                    "child_load",
                    path=metrics_path,
                )
                monitor.finish("ok")
            start = json.loads(
                metrics_path.read_text(encoding="utf-8").splitlines()[0]
            )

        self.assertEqual(
            start["details"]["parent_operation_id"],
            "parent-request-12345678",
        )

    def test_subprocess_parent_environment_records_correlation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            with mock.patch.dict(
                runtime_diagnostics.os.environ,
                {runtime_diagnostics.PARENT_OPERATION_ENV: "parent-runner-12345678"},
            ):
                monitor = runtime_diagnostics.OperationMonitor(
                    "runner_update",
                    path=metrics_path,
                )
                monitor.finish("ok")
            start = json.loads(
                metrics_path.read_text(encoding="utf-8").splitlines()[0]
            )

        self.assertEqual(
            start["details"]["parent_operation_id"],
            "parent-runner-12345678",
        )

    def test_diagnostic_history_joins_child_sources_phases_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            parent = runtime_diagnostics.OperationMonitor(
                "runner_action",
                details={"action": "all", "app_version": "0.2.test"},
                path=metrics_path,
            )
            with runtime_diagnostics.operation_context(parent.operation_id):
                child = runtime_diagnostics.OperationMonitor(
                    "runner_update",
                    details={"app_version": "0.2.test"},
                    path=metrics_path,
                )
                child.mark("source_complete", {"source": "Meteocat"})
                child.finish(
                    "ok",
                    {
                        "sources": {
                            "Meteocat": {
                                "status": "OK",
                                "rows": 100,
                                "stations": 2,
                                "duration_seconds": 1.5,
                                "phase_intervals": [
                                    {
                                        "source": "Meteocat",
                                        "phase": "metadata",
                                        "phase_id": "meteocat-1",
                                        "started_at": "2026-08-08T09:00:00.000Z",
                                        "finished_at": "2026-08-08T09:00:00.500Z",
                                        "duration_seconds": 0.5,
                                    }
                                ],
                            }
                        }
                    },
                )
            parent.finish("ok")
            runtime_diagnostics.record_summary(
                "runner_action",
                parent.operation_id,
                "snapshot",
                {"phase": "recovery_60s", "cgroup_memory_current_mib": 321.0},
                metrics_path,
            )

            history = runtime_diagnostics.diagnostic_history(metrics_path)

        parent_execution = next(
            item for item in history if item["operation"] == "runner_action"
        )
        self.assertEqual(parent_execution["sources"]["Meteocat"]["rows"], 100)
        self.assertEqual(
            parent_execution["snapshots"]["recovery_60s"]["cgroup_memory_current_mib"],
            321.0,
        )
        self.assertIn(
            "source_complete",
            [item["phase"] for item in parent_execution["phases"]],
        )
        self.assertEqual(parent_execution["diagnostic_schema"], "2.2")
        self.assertTrue(parent_execution["capabilities"]["source_phase_intervals"])
        self.assertEqual(
            parent_execution["sources"]["Meteocat"]["phase_intervals"][0]["phase"],
            "metadata",
        )

    def test_diagnostic_history_keeps_legacy_schema_as_limited_detail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            runtime_diagnostics.record_summary(
                "runner_action",
                "legacy-runner",
                "ok",
                {"app_version": "0.2.232", "action": "all", "wall_seconds": 10.0},
                metrics_path,
            )
            summary_path = runtime_diagnostics.summary_path(metrics_path)
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            payload["schema_version"] = "2.1"
            summary_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            history = runtime_diagnostics.diagnostic_history(metrics_path)

        self.assertEqual(history[0]["diagnostic_schema"], "2.1")
        self.assertFalse(history[0]["capabilities"]["source_phase_intervals"])

    def test_version_averages_keep_latest_five_versions_by_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            for index in range(1, 7):
                runtime_diagnostics.record_summary(
                    "runner_action",
                    f"runner-{index}",
                    "ok",
                    {
                        "app_version": f"0.2.{index}",
                        "wall_seconds": float(index * 10),
                        "max_cgroup_memory_current_mib": float(index * 100),
                    },
                    metrics_path,
                )
                time.sleep(0.002)
            runtime_diagnostics.record_summary(
                "runner_action",
                "runner-6-second",
                "degraded",
                {
                    "app_version": "0.2.6",
                    "wall_seconds": 80.0,
                    "max_cgroup_memory_current_mib": 800.0,
                },
                metrics_path,
            )

            averages = runtime_diagnostics.diagnostic_version_averages(metrics_path)

        versions = {item["version"] for item in averages}
        self.assertEqual(versions, {"0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6"})
        latest = next(item for item in averages if item["version"] == "0.2.6")
        self.assertEqual(latest["sample_count"], 2)
        self.assertEqual(latest["ok_count"], 1)
        self.assertEqual(latest["anomaly_count"], 1)
        self.assertEqual(latest["averages"]["wall_seconds"], 70.0)
        self.assertEqual(latest["minimums"]["wall_seconds"], 60.0)
        self.assertEqual(latest["maximums"]["wall_seconds"], 80.0)

    def test_diagnostic_evolution_series_is_compact_and_separates_workloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            metrics_path = Path(temporary_dir) / "runtime_metrics.jsonl"
            runtime_diagnostics.record_summary(
                "runner_action",
                "runner-all",
                "ok",
                {
                    "app_version": "0.2.test",
                    "action": "all",
                    "wall_seconds": 12.5,
                    "max_cgroup_memory_current_mib": 456.0,
                    "sources": {"Meteocat": {"rows": 100}},
                },
                metrics_path,
            )
            runtime_diagnostics.record_summary(
                "predictor_request",
                "predictor-week",
                "ok",
                {
                    "app_version": "0.2.test",
                    "view": "week",
                    "cold_request": True,
                    "wall_seconds": 3.0,
                },
                metrics_path,
            )

            series = runtime_diagnostics.diagnostic_evolution_series(
                metrics_path,
                days=None,
            )

        self.assertEqual(len(series), 2)
        runner = next(item for item in series if item["operation"] == "runner_action")
        predictor = next(item for item in series if item["operation"] == "predictor_request")
        self.assertEqual(runner["workload"], "all")
        self.assertEqual(runner["metrics"]["max_cgroup_memory_current_mib"], 456.0)
        self.assertNotIn("sources", runner)
        self.assertEqual(predictor["workload"], "week · cold")

    def test_failed_operation_archives_redacted_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            metrics_path = data_dir / "runtime_metrics.jsonl"
            source_log = data_dir / "last_run.log"
            source_log.write_text(
                "failed api_key=TOP-SECRET\nAuthorization: Bearer TOKEN\n",
                encoding="utf-8",
            )
            monitor = runtime_diagnostics.OperationMonitor(
                "failed_runner",
                path=metrics_path,
                failure_log_path=source_log,
            )
            monitor.finish("error")
            archived = (
                runtime_diagnostics.failure_logs_path(metrics_path)
                / f"{monitor.operation_id}.log"
            ).read_text(encoding="utf-8")

        self.assertIn("api_key=[REDACTED]", archived)
        self.assertIn("Authorization: Bearer [REDACTED]", archived)
        self.assertNotIn("TOP-SECRET", archived)

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
