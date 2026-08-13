import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from rainmapper_core.wunderground_metrics import FIELDNAMES, save_metrics


def row(day: str, station: str) -> dict[str, object]:
    return {
        "id_ejecucion": "run",
        "timestamp_lectura": f"{day[:4]}-{day[4:6]}-{day[6:]}T12:00:00",
        "fecha_lectura": day,
        "hora_lectura": "12:00:00",
        "codi_estacio": station,
        "estacion": station,
        "url": "https://example.invalid",
        "tiempo_lectura_s": "0.100",
        "ok": True,
        "filas": 9,
        "ultimo_error": "",
    }


class WundergroundMetricsTests(unittest.TestCase):
    def test_keeps_thirty_calendar_days_and_appends_current_rows(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            path = Path(temporary_dir) / "metricas_wunderground.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows([
                    row("20260713", "TOO_OLD"),
                    row("20260714", "BOUNDARY"),
                    row("20260811", "RECENT"),
                ])

            report = save_metrics(
                path,
                [row("20260812", "NEW")],
                today=date(2026, 8, 12),
            )

            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(
                [value["codi_estacio"] for value in rows],
                ["BOUNDARY", "RECENT", "NEW"],
            )
            self.assertEqual(report["cutoff_date"], "2026-07-14")
            self.assertEqual(report["dropped_rows"], 1)

    def test_malformed_historical_rows_are_removed(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            path = Path(temporary_dir) / "metricas_wunderground.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerow({"fecha_lectura": "invalid", "codi_estacio": "BAD"})

            report = save_metrics(path, [], today=date(2026, 8, 12))

            self.assertEqual(report["malformed_rows_dropped"], 1)
            self.assertEqual(path.read_text(encoding="utf-8").count("\n"), 1)

    def test_failed_atomic_write_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            path = Path(temporary_dir) / "metricas_wunderground.csv"
            original = "header\noriginal\n"
            path.write_text(original, encoding="utf-8")

            with mock.patch("csv.DictWriter.writerows", side_effect=RuntimeError("boom")):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    save_metrics(path, [row("20260812", "NEW")], today=date(2026, 8, 12))

            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual(list(path.parent.glob(".metricas_wunderground.csv.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
