import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from rainmapper_core import weather_history


def canonical_row(source, station, day, rain, *, temperature=20.0):
    return {
        "source": source,
        "station_code": station,
        "station_name": f"Station {station}",
        "local_date": day,
        "lat": 42.0,
        "lon": 2.0,
        "altitude": 700.0,
        "rain_mm": rain,
        "max_temp_celsius": temperature,
        "min_temp_celsius": 10.0,
        "max_humidity_percent": 80.0,
        "min_humidity_percent": 40.0,
        "wind_avg_kmh": 5.0,
        "wind_gust_kmh": 12.0,
    }


class WeatherHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.history = self.root / "weather_daily.parquet"

    def write_history(self, rows):
        frame = weather_history.normalize_weather_history_frame(pd.DataFrame(rows))
        frame.sort_values(weather_history.WEATHER_HISTORY_KEY).to_parquet(
            self.history,
            index=False,
        )

    def read_history(self):
        return pd.read_parquet(self.history).sort_values(
            weather_history.WEATHER_HISTORY_KEY
        ).reset_index(drop=True)

    def test_upsert_updates_non_null_preserves_old_value_and_inserts(self):
        self.write_history([
            canonical_row("meteocat", "A", "20260810", 1.0, temperature=22.0),
            canonical_row("meteocat", "B", "20260810", 2.0),
        ])
        updates = pd.DataFrame([
            {
                **canonical_row("meteocat", "A", "20260810", 4.5),
                "max_temp_celsius": pd.NA,
                "wind_direction_deg": 350.0,
            },
            canonical_row("wunderground", "C", "20260811", 3.0),
        ])

        report = weather_history.upsert_weather_history_parquet(
            self.history,
            updates,
            batch_size=1,
        )

        result = self.read_history().set_index(
            weather_history.WEATHER_HISTORY_KEY
        )
        self.assertEqual(report.old_rows, 2)
        self.assertEqual(report.matched_rows, 1)
        self.assertEqual(report.inserted_rows, 1)
        self.assertEqual(report.output_rows, 3)
        self.assertEqual(result.loc[("meteocat", "A", "20260810"), "rain_mm"], 4.5)
        self.assertEqual(result.loc[("meteocat", "A", "20260810"), "max_temp_celsius"], 22.0)
        self.assertEqual(result.loc[("meteocat", "A", "20260810"), "wind_direction_deg"], 350.0)
        self.assertIn(("wunderground", "C", "20260811"), result.index)

    def test_repeated_updates_are_collapsed_with_later_non_null_values(self):
        self.write_history([canonical_row("meteocat", "A", "20260810", 1.0)])
        first = canonical_row("meteocat", "A", "20260810", 2.0)
        second = canonical_row("meteocat", "A", "20260810", pd.NA)
        second["max_temp_celsius"] = 25.0

        report = weather_history.upsert_weather_history_parquet(
            self.history,
            pd.DataFrame([first, second]),
        )

        result = self.read_history()
        self.assertEqual(report.update_rows, 1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["rain_mm"], 2.0)
        self.assertEqual(result.iloc[0]["max_temp_celsius"], 25.0)

    def test_same_upsert_is_logically_idempotent(self):
        self.write_history([canonical_row("meteocat", "A", "20260810", 1.0)])
        updates = pd.DataFrame([
            canonical_row("meteocat", "A", "20260810", 2.0),
            canonical_row("meteocat", "B", "20260811", 3.0),
        ])
        weather_history.upsert_weather_history_parquet(self.history, updates)
        first = self.read_history()

        report = weather_history.upsert_weather_history_parquet(self.history, updates)
        second = self.read_history()

        self.assertEqual(report.inserted_rows, 0)
        pd.testing.assert_frame_equal(first, second)

    def test_duplicate_history_key_does_not_replace_destination(self):
        output = self.root / "candidate.parquet"
        pd.DataFrame([
            canonical_row("meteocat", "A", "20260810", 1.0),
            canonical_row("meteocat", "A", "20260810", 2.0),
        ]).to_parquet(self.history, index=False)
        output.write_bytes(b"previous-candidate")

        with self.assertRaisesRegex(ValueError, "duplicate key"):
            weather_history.upsert_weather_history_parquet(
                self.history,
                pd.DataFrame([canonical_row("meteocat", "A", "20260810", 3.0)]),
                output_path=output,
                batch_size=1,
            )

        self.assertEqual(output.read_bytes(), b"previous-candidate")
        self.assertEqual(list(self.root.glob(".candidate.parquet.*.tmp")), [])

    def test_output_always_has_complete_canonical_schema(self):
        self.write_history([canonical_row("meteocat", "A", "20260810", 1.0)])
        weather_history.upsert_weather_history_parquet(
            self.history,
            pd.DataFrame(columns=weather_history.WEATHER_HISTORY_COLUMNS),
        )
        self.assertEqual(
            pq.ParquetFile(self.history).schema_arrow.names,
            weather_history.WEATHER_HISTORY_COLUMNS,
        )

    def test_numeric_columns_are_canonical_float_even_for_integer_input(self):
        normalized = weather_history.normalize_weather_history_frame(
            pd.DataFrame(
                [
                    {
                        "source": "meteocat",
                        "station_code": "A",
                        "local_date": "20260810",
                        "altitude": "263",
                        "rain_mm": "4,0",
                    }
                ]
            )
        )

        self.assertEqual(str(normalized["altitude"].dtype), "Float64")
        self.assertEqual(str(normalized["rain_mm"].dtype), "Float64")
        self.assertEqual(normalized.iloc[0]["altitude"], 263.0)

    def test_live_queue_loader_keeps_only_configured_calendar_dates(self):
        rows = [
            {
                "Codi Estació": "A",
                "Data Local": "20260212",
                "Total": "1,0",
            },
            {
                "Codi Estació": "A",
                "Data Local": "20260213",
                "Total": "2,0",
            },
            {
                "Codi Estació": "A",
                "Data Local": "20260811",
                "Total": "3,0",
            },
        ]
        pd.DataFrame(rows).to_csv(
            self.root / "Meteocat_incremental.csv",
            index=False,
        )

        updates = weather_history.load_weather_queue_updates(
            self.root,
            retention_days=180,
            reference_day=date(2026, 8, 11),
        )

        self.assertEqual(updates["local_date"].tolist(), ["20260213", "20260811"])
        self.assertEqual(updates["source"].tolist(), ["meteocat", "meteocat"])

    def test_live_queue_update_changes_canonical_parquet_in_place(self):
        self.write_history([
            canonical_row("meteocat", "A", "20260810", 1.0, temperature=22.0),
        ])
        pd.DataFrame([
            {
                "Codi Estació": "A",
                "Data Local": "20260810",
                "Total": "4,5",
                "max_temp_celsius": pd.NA,
            },
            {
                "Codi Estació": "B",
                "Data Local": "20260811",
                "Total": "2,0",
            },
        ]).to_csv(self.root / "Meteocat_incremental.csv", index=False)

        report = weather_history.update_weather_history_from_live_queues(
            self.root,
            retention_days=180,
            reference_day=date(2026, 8, 11),
        )

        result = self.read_history().set_index(weather_history.WEATHER_HISTORY_KEY)
        self.assertEqual(report.matched_rows, 1)
        self.assertEqual(report.inserted_rows, 1)
        self.assertEqual(result.loc[("meteocat", "A", "20260810"), "rain_mm"], 4.5)
        self.assertEqual(result.loc[("meteocat", "A", "20260810"), "max_temp_celsius"], 22.0)

    def test_live_queue_bootstraps_missing_canonical_parquet_atomically(self):
        pd.DataFrame([
            {
                "Codi Estació": "A",
                "Data Local": "20260810",
                "Total": "4,5",
            },
        ]).to_csv(self.root / "Meteocat_incremental.csv", index=False)

        report = weather_history.update_weather_history_from_live_queues(
            self.root,
            retention_days=180,
            reference_day=date(2026, 8, 11),
        )

        self.assertTrue(self.history.is_file())
        self.assertEqual(report.old_rows, 0)
        self.assertEqual(report.inserted_rows, 1)
        self.assertEqual(self.read_history().iloc[0]["rain_mm"], 4.5)
        self.assertEqual(list(self.root.glob(".weather_daily.parquet.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
