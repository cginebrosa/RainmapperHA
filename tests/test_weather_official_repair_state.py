import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from rainmapper_core.weather_official_repair_state import (
    detection_window,
    empty_state,
    enqueue_missing_days,
    load_state,
    next_due,
    record_attempt,
    write_state,
)


NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


class WeatherOfficialRepairStateTests(unittest.TestCase):
    def test_queue_is_bounded_to_fifteen_day_blocks_and_deduplicates(self):
        missing = [date(2026, 1, 1).fromordinal(date(2026, 1, 1).toordinal() + offset) for offset in range(20)]
        state = enqueue_missing_days(empty_state(), "meteocat", missing, detected_at=NOW)
        state = enqueue_missing_days(state, "meteocat", missing, detected_at=NOW)
        self.assertTrue(state["active"])
        self.assertEqual(len(state["pending"]), 2)
        self.assertEqual(state["pending"][0]["start_date"], "2026-01-01")
        self.assertEqual(state["pending"][0]["end_date"], "2026-01-15")
        self.assertEqual(state["pending"][1]["start_date"], "2026-01-16")
        self.assertEqual(state["pending"][1]["end_date"], "2026-01-20")

    def test_partial_recovery_keeps_only_missing_days_with_backoff(self):
        state = enqueue_missing_days(
            empty_state(),
            "aemet",
            [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)],
            detected_at=NOW,
        )
        item = next_due(state, now=NOW)
        repaired = record_attempt(
            state,
            item["id"],
            recovered_days=[date(2026, 1, 1), date(2026, 1, 3)],
            attempted_at=NOW,
        )
        self.assertTrue(repaired["active"])
        self.assertEqual(repaired["pending"][0]["start_date"], "2026-01-02")
        self.assertEqual(repaired["pending"][0]["end_date"], "2026-01-02")
        self.assertIsNone(next_due(repaired, now=NOW))

    def test_full_recovery_clears_active_flag_and_persists(self):
        state = enqueue_missing_days(empty_state(), "meteocat", [date(2026, 2, 2)], detected_at=NOW)
        item = next_due(state, now=NOW)
        repaired = record_attempt(
            state,
            item["id"],
            recovered_days=[date(2026, 2, 2)],
            attempted_at=NOW,
        )
        self.assertFalse(repaired["active"])
        self.assertEqual(repaired["pending"], [])
        self.assertEqual(repaired["last_resolved"][0]["status"], "resolved")
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            write_state(data_dir, repaired)
            loaded = load_state(data_dir)
        self.assertFalse(loaded["active"])
        self.assertEqual(loaded["last_resolved"][0]["id"], item["id"])

    def test_detection_starts_after_cursor_and_excludes_seven_day_overlap(self):
        state = empty_state()
        self.assertEqual(
            detection_window(
                state,
                "meteocat",
                date(2026, 8, 15),
                initial_lookback_days=3,
            ),
            (date(2026, 8, 5), date(2026, 8, 7)),
        )
        state["checked_through"]["meteocat"] = "2026-08-06"
        self.assertEqual(
            detection_window(state, "meteocat", date(2026, 8, 15)),
            (date(2026, 8, 7), date(2026, 8, 7)),
        )


if __name__ == "__main__":
    unittest.main()
