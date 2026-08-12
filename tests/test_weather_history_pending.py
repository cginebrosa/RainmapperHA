import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import pyarrow.parquet as pq

from rainmapper_core.weather_history_pending import (
    PendingBatchError,
    acknowledge_pending_batch,
    build_pending_batch,
    list_pending_batches,
)
from rainmapper_core.weather_history_capture import capture_fresh_weather_rows


class WeatherHistoryPendingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data_dir = Path(self.temporary.name) / "Data"

    @staticmethod
    def row(day, rain, *, station="A", name=None, lat=42.0, source=None):
        row = {
            "station_code": station,
            "local_date": day,
            "rain_mm": rain,
            "station_name": name,
            "lat": lat,
            "lon": 2.0,
            "altitude": 700.0,
        }
        if source is not None:
            row["source"] = source
        return row

    def test_external_runs_preserve_last_non_null_semantics(self):
        pending = build_pending_batch(
            self.data_dir,
            "meteocat",
            [
                [
                    self.row("20260102", 2.0, name="old"),
                    self.row("20260101", 1.0),
                ],
                [
                    self.row("20260102", None, name="new"),
                    self.row("20260103", 3.0),
                ],
            ],
            run_id="test",
            chunk_rows=2,
            row_group_size=2,
            fan_in=2,
        )
        self.assertIsNotNone(pending)
        self.assertEqual(pending.rows, 3)
        self.assertEqual(pending.input_rows, 4)
        self.assertEqual(pending.collapsed_rows, 1)
        rows = pq.read_table(pending.data_path).to_pylist()
        self.assertEqual([row["local_date"] for row in rows], ["20260101", "20260102", "20260103"])
        self.assertEqual(rows[1]["rain_mm"], 2.0)
        self.assertEqual(rows[1]["station_name"], "new")
        sidecar = json.loads(pending.sidecar_path.read_text())
        self.assertEqual(sidecar["batch_id"], pending.batch_id)
        self.assertEqual(sidecar["years"], [2026])

    def test_batch_id_is_independent_of_input_batch_boundaries(self):
        rows = [self.row(f"2026010{day}", float(day)) for day in range(1, 5)]
        first = build_pending_batch(
            self.data_dir,
            "aemet",
            [rows[:2], rows[2:]],
            run_id="one",
            chunk_rows=2,
        )
        expected = first.batch_id
        acknowledge_pending_batch(first)
        second = build_pending_batch(
            self.data_dir,
            "aemet",
            [[rows[0]], rows[1:]],
            run_id="two",
            chunk_rows=3,
        )
        self.assertEqual(second.batch_id, expected)

    def test_multi_pass_merge_preserves_precedence_across_distant_runs(self):
        batches = []
        for index in range(9):
            batches.append(
                [
                    self.row(
                        "20260101",
                        None if index == 8 else float(index),
                        name=f"revision-{index}",
                    ),
                    self.row(f"202602{index + 1:02d}", float(index), station=f"S{index}"),
                ]
            )
        pending = build_pending_batch(
            self.data_dir,
            "aemet",
            batches,
            run_id="multipass",
            chunk_rows=2,
            row_group_size=2,
            fan_in=2,
        )
        rows = pq.read_table(pending.data_path).to_pylist()
        repeated = next(row for row in rows if row["station_code"] == "A")
        self.assertEqual(repeated["rain_mm"], 7.0)
        self.assertEqual(repeated["station_name"], "revision-8")

    def test_rejects_second_pending_for_same_source(self):
        build_pending_batch(
            self.data_dir,
            "wunderground",
            [[self.row("20260101", 1.0)]],
            run_id="one",
        )
        with self.assertRaisesRegex(PendingBatchError, "already has"):
            build_pending_batch(
                self.data_dir,
                "wunderground",
                [[self.row("20260102", 2.0)]],
                run_id="two",
            )

    def test_invalid_source_date_and_infinity_are_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_pending_batch(
                self.data_dir,
                "aemet",
                [[self.row("20260101", 1.0, source="meteocat")]],
                run_id="bad",
            )
        with self.assertRaisesRegex(ValueError, "Invalid canonical weather key"):
            build_pending_batch(
                self.data_dir,
                "aemet",
                [[self.row("2026-01-01", 1.0)]],
                run_id="bad",
            )
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            build_pending_batch(
                self.data_dir,
                "aemet",
                [[self.row("20260101", float("inf"))]],
                run_id="bad",
            )

    def test_nan_becomes_null_and_empty_input_creates_nothing(self):
        self.assertIsNone(
            build_pending_batch(self.data_dir, "meteocat", [], run_id="empty")
        )
        pending = build_pending_batch(
            self.data_dir,
            "meteocat",
            [[self.row("20260101", float("nan"))]],
            run_id="nan",
        )
        self.assertIsNone(pq.read_table(pending.data_path)["rain_mm"][0].as_py())

    def test_integrity_failure_is_detected(self):
        pending = build_pending_batch(
            self.data_dir,
            "meteoclimatic",
            [[self.row("20260101", 1.0)]],
            run_id="one",
        )
        with pending.data_path.open("ab") as handle:
            handle.write(b"corrupt")
        with self.assertRaisesRegex(PendingBatchError, "integrity"):
            list_pending_batches(self.data_dir)

    def test_lightweight_import_does_not_load_pandas(self):
        command = (
            "import sys; "
            "import rainmapper_core.weather_history_pending; "
            "assert 'pandas' not in sys.modules"
        )
        subprocess.run([sys.executable, "-c", command], check=True)

    def test_source_capture_is_feature_gated_and_chunked(self):
        frame = pd.DataFrame([self.row("20260101", 1.0)])
        with mock.patch(
            "rainmapper_core.weather_history_capture.build_pending_batch"
        ) as build:
            self.assertIsNone(
                capture_fresh_weather_rows(self.data_dir, "aemet", frame)
            )
            build.assert_not_called()
        with mock.patch.dict(
            "os.environ",
            {"RAINMAPPER_PARTITIONED_WEATHER_HISTORY": "true", "RAINMAPPER_WEATHER_RUN_ID": "run-1"},
            clear=False,
        ), mock.patch(
            "rainmapper_core.weather_history_capture.build_pending_batch",
            return_value="pending",
        ) as build:
            result = capture_fresh_weather_rows(
                self.data_dir, "aemet", frame, chunk_rows=1
            )
            self.assertEqual(result, "pending")
            self.assertEqual(build.call_args.kwargs["run_id"], "run-1")
            batches = list(build.call_args.args[2])
            self.assertEqual(len(batches), 1)
            self.assertEqual(batches[0].num_rows, 1)


if __name__ == "__main__":
    unittest.main()
