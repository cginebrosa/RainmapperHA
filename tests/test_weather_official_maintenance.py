import unittest
from datetime import date, datetime, timezone
from unittest import mock

import pandas as pd

from rainmapper_core.weather_official_maintenance import repair_due_item
from rainmapper_core.weather_official_repair_state import empty_state, enqueue_missing_days, next_due


NOW = datetime(2026, 8, 16, 0, 30, tzinfo=timezone.utc)


class WeatherOfficialMaintenanceTests(unittest.TestCase):
    def _queued(self):
        state = enqueue_missing_days(
            empty_state(),
            "meteocat",
            [date(2026, 8, 1), date(2026, 8, 2)],
            detected_at=NOW,
        )
        return state, next_due(state, now=NOW)

    @mock.patch(
        "rainmapper_core.weather_official_maintenance.observed_network_days",
        return_value={date(2026, 8, 1), date(2026, 8, 2)},
    )
    @mock.patch(
        "rainmapper_core.weather_official_maintenance.list_pending_batches",
        return_value=[],
    )
    def test_already_archived_days_clear_queue_without_fetch(self, pending, observed):
        state, item = self._queued()
        fetcher = mock.Mock()
        updated, report = repair_due_item(
            mock.Mock(),
            state,
            item,
            reference_day=date(2026, 8, 16),
            aemet_api_key=None,
            fetcher=fetcher,
            attempted_at=NOW,
        )
        self.assertFalse(updated["active"])
        self.assertEqual(report["status"], "already_recovered")
        fetcher.assert_not_called()

    @mock.patch(
        "rainmapper_core.weather_official_maintenance.observed_network_days",
        return_value=set(),
    )
    @mock.patch(
        "rainmapper_core.weather_official_maintenance.list_pending_batches",
        return_value=[],
    )
    def test_provider_failure_keeps_queue_with_backoff(self, pending, observed):
        state, item = self._queued()
        updated, report = repair_due_item(
            mock.Mock(),
            state,
            item,
            reference_day=date(2026, 8, 16),
            aemet_api_key=None,
            fetcher=mock.Mock(side_effect=RuntimeError("provider unavailable")),
            attempted_at=NOW,
        )
        self.assertTrue(updated["active"])
        self.assertEqual(report["status"], "retry_wait")
        self.assertIn("provider unavailable", updated["pending"][0]["last_error"])
        self.assertEqual(updated["pending"][0]["attempts"], 1)

    @mock.patch("rainmapper_core.weather_official_maintenance.acknowledge_archived_pending")
    @mock.patch("rainmapper_core.weather_official_maintenance.apply_pending_to_live_csv")
    @mock.patch("rainmapper_core.weather_official_maintenance.archive_pending_batches")
    @mock.patch("rainmapper_core.weather_official_maintenance.list_pending_batches")
    @mock.patch(
        "rainmapper_core.weather_official_maintenance.observed_network_days",
        return_value={date(2026, 8, 1), date(2026, 8, 2)},
    )
    def test_resumes_archived_pending_before_clearing_repair_queue(
        self,
        observed,
        pending_batches,
        archive_pending,
        apply_live,
        acknowledge,
    ):
        state, item = self._queued()
        pending = mock.Mock(batch_id="batch-1")
        pending_batches.return_value = [pending]
        archive_pending.return_value = mock.Mock(
            batch_ids=(),
            already_applied_batch_ids=("batch-1",),
            generation_id="generation-2",
        )
        apply_live.return_value = mock.Mock(to_dict=mock.Mock(return_value={"retained_rows": 0}))
        fetcher = mock.Mock()

        updated, report = repair_due_item(
            mock.Mock(),
            state,
            item,
            reference_day=date(2026, 8, 16),
            aemet_api_key=None,
            fetcher=fetcher,
            attempted_at=NOW,
        )

        self.assertFalse(updated["active"])
        self.assertEqual(report["status"], "already_recovered")
        self.assertEqual(report["resumed_batches"][0]["batch_id"], "batch-1")
        apply_live.assert_called_once_with(
            mock.ANY,
            pending,
            reference_day=date(2026, 8, 16),
        )
        acknowledge.assert_called_once_with(mock.ANY, "batch-1")
        fetcher.assert_not_called()

    @mock.patch("rainmapper_core.weather_official_maintenance.acknowledge_archived_pending")
    @mock.patch("rainmapper_core.weather_official_maintenance.apply_pending_to_live_csv")
    @mock.patch("rainmapper_core.weather_official_maintenance.archive_pending_batches")
    @mock.patch("rainmapper_core.weather_official_maintenance.build_pending_batch")
    @mock.patch("rainmapper_core.weather_official_maintenance.list_pending_batches", return_value=[])
    @mock.patch("rainmapper_core.weather_official_maintenance.observed_network_days")
    def test_success_archives_updates_live_then_acknowledges(
        self,
        observed,
        pending_batches,
        build_pending,
        archive_pending,
        apply_live,
        acknowledge,
    ):
        state, item = self._queued()
        observed.side_effect = [set(), {date(2026, 8, 1), date(2026, 8, 2)}]
        frame = pd.DataFrame(
            [
                {"source": "meteocat", "station_code": "A", "local_date": "20260801"},
                {"source": "meteocat", "station_code": "A", "local_date": "20260802"},
            ]
        )
        pending = mock.Mock(batch_id="batch-1")
        build_pending.return_value = pending
        archive_pending.return_value = mock.Mock(
            committed=True,
            already_applied_batch_ids=(),
            generation_id="generation-2",
        )
        apply_live.return_value = mock.Mock(to_dict=mock.Mock(return_value={"retained_rows": 2}))

        updated, report = repair_due_item(
            mock.Mock(),
            state,
            item,
            reference_day=date(2026, 8, 16),
            aemet_api_key=None,
            fetcher=mock.Mock(return_value=frame),
            attempted_at=NOW,
        )

        self.assertFalse(updated["active"])
        self.assertEqual(report["status"], "resolved")
        self.assertEqual(report["generation_id"], "generation-2")
        apply_live.assert_called_once_with(
            mock.ANY,
            pending,
            reference_day=date(2026, 8, 16),
        )
        acknowledge.assert_called_once_with(mock.ANY, "batch-1")

    @mock.patch("rainmapper_core.weather_official_maintenance.acknowledge_archived_pending")
    @mock.patch(
        "rainmapper_core.weather_official_maintenance.apply_pending_to_live_csv",
        side_effect=RuntimeError("live update interrupted"),
    )
    @mock.patch("rainmapper_core.weather_official_maintenance.archive_pending_batches")
    @mock.patch("rainmapper_core.weather_official_maintenance.build_pending_batch")
    @mock.patch("rainmapper_core.weather_official_maintenance.list_pending_batches", return_value=[])
    @mock.patch("rainmapper_core.weather_official_maintenance.observed_network_days", return_value=set())
    def test_live_failure_does_not_acknowledge_durable_pending(
        self,
        observed,
        pending_batches,
        build_pending,
        archive_pending,
        apply_live,
        acknowledge,
    ):
        state, item = self._queued()
        build_pending.return_value = mock.Mock(batch_id="batch-1")
        archive_pending.return_value = mock.Mock(
            committed=True,
            already_applied_batch_ids=(),
            generation_id="generation-2",
        )
        frame = pd.DataFrame(
            [{"source": "meteocat", "station_code": "A", "local_date": "20260801"}]
        )

        updated, report = repair_due_item(
            mock.Mock(),
            state,
            item,
            reference_day=date(2026, 8, 16),
            aemet_api_key=None,
            fetcher=mock.Mock(return_value=frame),
            attempted_at=NOW,
        )

        self.assertTrue(updated["active"])
        self.assertEqual(report["status"], "retry_wait")
        self.assertIn("live update interrupted", report["error"])
        acknowledge.assert_not_called()


if __name__ == "__main__":
    unittest.main()
