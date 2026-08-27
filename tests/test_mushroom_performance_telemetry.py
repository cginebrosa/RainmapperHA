import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_performance_telemetry


class MushroomPerformanceTelemetryTests(unittest.TestCase):
    def test_persists_monotonic_phases_and_bounded_counters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            now = [100.0]
            path = Path(temporary) / "telemetry.json"
            recorder = mushroom_performance_telemetry.PersistentTelemetry(
                path,
                operation_id="local_full_update_test",
                workload="local_operational_full_update",
                monotonic=lambda: now[0],
                wall_clock=lambda: "2026-08-26T12:00:00.000+00:00",
            )
            recorder.add(bytes_read=11, files_read=1, hashes=1, hash_bytes=11)
            now[0] = 102.5
            recorder.phase("training")
            recorder.add(copies=2, copy_bytes=17)
            now[0] = 107.0

            summary = recorder.finish("complete")
            persisted = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(summary, persisted)
            self.assertEqual("monotonic", persisted["clock"])
            self.assertEqual("instrumented_application_io", persisted["counter_scope"])
            self.assertEqual(7.0, persisted["elapsed_seconds"])
            self.assertEqual(
                [("initializing", 2.5), ("training", 4.5)],
                [
                    (row["name"], row["duration_seconds"])
                    for row in persisted["phases"]
                ],
            )
            self.assertEqual(11, persisted["counters"]["bytes_read"])
            self.assertEqual(2, persisted["counters"]["copies"])
            self.assertEqual(3, persisted["counters"]["files_written"])
            self.assertEqual(6, persisted["counters"]["fsyncs"])
            self.assertGreaterEqual(
                persisted["counters"]["bytes_written"],
                path.stat().st_size,
            )

    def test_context_only_counts_the_active_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "telemetry.json"
            recorder = mushroom_performance_telemetry.PersistentTelemetry(
                path,
                operation_id="context_test",
                workload="test",
            )

            mushroom_performance_telemetry.add(requests=7)
            with mushroom_performance_telemetry.activate(recorder):
                mushroom_performance_telemetry.add(requests=2, bytes_read=5)
            mushroom_performance_telemetry.add(requests=11)
            summary = recorder.finish("complete")

            self.assertEqual(2, summary["counters"]["requests"])
            self.assertEqual(5, summary["counters"]["bytes_read"])

    def test_untrusted_summary_must_be_terminal_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "telemetry.json"
            recorder = mushroom_performance_telemetry.PersistentTelemetry(
                path,
                operation_id="validation_test",
                workload="test",
            )
            summary = recorder.finish("complete")

            normalized = mushroom_performance_telemetry.validate_summary(summary)
            self.assertEqual(summary, normalized)

            malformed = dict(summary)
            malformed["status"] = "running"
            with self.assertRaisesRegex(ValueError, "state is invalid"):
                mushroom_performance_telemetry.validate_summary(malformed)


if __name__ == "__main__":
    unittest.main()
