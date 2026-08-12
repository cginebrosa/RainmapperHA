import csv
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from rainmapper_core.weather_history_pending import build_pending_batch
from rainmapper_core.weather_live_csv import apply_pending_to_live_csv


class WeatherLiveCsvTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data_dir = Path(self.temporary.name) / "Data"
        self.data_dir.mkdir()

    @staticmethod
    def row(day, rain, *, station="A", name=None):
        return {
            "station_code": station,
            "station_name": name or f"Station {station}",
            "local_date": day,
            "rain_mm": rain,
            "lat": 42.0,
            "lon": 2.0,
            "altitude": 700.0,
        }

    def pending(self, rows):
        return build_pending_batch(
            self.data_dir,
            "meteocat",
            [rows],
            run_id="csv-test",
            row_group_size=2,
            chunk_rows=2,
        )

    def write_csv(self, rows):
        path = self.data_dir / "Meteocat_incremental.csv"
        fieldnames = ["station_code", "station_name", "local_date", "rain_mm", "lat", "lon", "altitude"]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def read_csv(self, path):
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_streaming_merge_preserves_old_value_for_null_and_compacts(self):
        path = self.write_csv(
            [
                self.row("20260102", 2.0),
                self.row("20260101", 1.0),
                self.row("20250101", 9.0),
            ]
        )
        path.chmod(0o640)
        pending = self.pending(
            [
                self.row("20260102", None, name="Corrected"),
                self.row("20260103", 3.5),
                self.row("20240101", 7.0, station="OLD"),
            ]
        )
        report = apply_pending_to_live_csv(
            self.data_dir,
            pending,
            reference_day=date(2026, 1, 3),
        )
        rows = self.read_csv(path)
        self.assertEqual(
            [(row["station_code"], row["local_date"]) for row in rows],
            [("A", "20260103"), ("A", "20260102"), ("A", "20260101")],
        )
        self.assertEqual(rows[1]["rain_mm"], "2")
        self.assertEqual(rows[1]["station_name"], "Corrected")
        self.assertEqual(rows[0]["rain_mm"], "3,5")
        self.assertEqual(report.matched_rows, 1)
        self.assertEqual(report.inserted_rows, 2)
        self.assertEqual(report.retained_rows, 3)
        self.assertEqual(report.dropped_rows, 2)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o640)

    def test_missing_csv_is_reconstructed_from_pending(self):
        pending = self.pending([self.row("20260103", 3.0)])
        report = apply_pending_to_live_csv(
            self.data_dir,
            pending,
            reference_day=date(2026, 1, 3),
        )
        self.assertEqual(report.retained_rows, 1)
        path = self.data_dir / "Meteocat_incremental.csv"
        rows = self.read_csv(path)
        self.assertEqual(rows[0]["Codi Estació"], "A")
        self.assertEqual(rows[0]["Data Local"], "20260103")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o644)

    def test_unsorted_existing_csv_is_rejected_without_overwriting(self):
        path = self.write_csv(
            [self.row("20260101", 1.0), self.row("20260102", 2.0)]
        )
        original = path.read_bytes()
        pending = self.pending([self.row("20260103", 3.0)])
        with self.assertRaisesRegex(RuntimeError, "not sorted"):
            apply_pending_to_live_csv(
                self.data_dir,
                pending,
                reference_day=date(2026, 1, 3),
            )
        self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
