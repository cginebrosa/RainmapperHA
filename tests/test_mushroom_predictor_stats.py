from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core.mushroom_predictor_stats import MAX_SAMPLES_PER_EXECUTOR, rank_available, record, summary


class PredictorStatsTests(TestCase):
    def test_summary_and_ranking_use_bounded_medians(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "stats.json"
            record(
                path,
                executor_id="worker:fast",
                cold=True,
                backend_seconds=4.0,
                total_seconds=18.0,
                view="recommender",
            )
            for backend, total in ((0.001, 6.0), (0.002, 7.0)):
                record(
                    path,
                    executor_id="worker:fast",
                    cold=False,
                    backend_seconds=backend,
                    total_seconds=total,
                    view="week",
                )
            record(
                path,
                executor_id="home_assistant",
                cold=True,
                backend_seconds=30.0,
                total_seconds=34.0,
                view="recommender",
            )
            record(
                path,
                executor_id="home_assistant",
                cold=False,
                backend_seconds=0.1,
                total_seconds=0.8,
                view="week",
            )

            fast = summary(path, "worker:fast")
            ranked = rank_available(path, ["home_assistant", "worker:unknown", "worker:fast"])

            self.assertEqual(fast["cold_entry_median_seconds"], 18.0)
            self.assertEqual(fast["warm_navigation_median_seconds"], 6.5)
            self.assertEqual(fast["selection_seconds"], 18.0)
            self.assertEqual(fast["total_sample_count"], 3)
            self.assertEqual(ranked[0]["executor_id"], "worker:fast")
            self.assertEqual(ranked[-1]["executor_id"], "worker:unknown")

    def test_ranking_falls_back_to_legacy_backend_samples_until_totals_exist(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "stats.json"
            record(path, executor_id="worker:fast", cold=False, backend_seconds=1.0)
            record(path, executor_id="home_assistant", cold=False, backend_seconds=2.0)

            ranked = rank_available(path, ["home_assistant", "worker:fast"])

            self.assertEqual(ranked[0]["executor_id"], "worker:fast")
            self.assertIsNone(ranked[0]["selection_seconds"])

    def test_warm_totals_do_not_replace_a_cold_entry_measurement(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "stats.json"
            record(
                path,
                executor_id="worker:warm_only",
                cold=False,
                backend_seconds=0.001,
                total_seconds=0.2,
                view="week",
            )
            record(
                path,
                executor_id="home_assistant",
                cold=True,
                backend_seconds=30.0,
                total_seconds=34.0,
                view="recommender",
            )

            ranked = rank_available(path, ["worker:warm_only", "home_assistant"])

            self.assertEqual(ranked[0]["executor_id"], "home_assistant")
            self.assertIsNone(summary(path, "worker:warm_only")["selection_seconds"])

    def test_operation_id_prevents_duplicate_total_samples(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "stats.json"
            first = record(
                path,
                executor_id="worker:fast",
                cold=False,
                backend_seconds=1.0,
                total_seconds=6.0,
                operation_id="predictor-1",
                view="week",
            )
            duplicate = record(
                path,
                executor_id="worker:fast",
                cold=False,
                backend_seconds=0.1,
                total_seconds=0.2,
                operation_id="predictor-1",
                view="week",
            )

            self.assertEqual(duplicate, first)
            self.assertEqual(summary(path, "worker:fast")["total_sample_count"], 1)

    def test_samples_rotate(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "stats.json"
            for value in range(MAX_SAMPLES_PER_EXECUTOR + 5):
                record(path, executor_id="home_assistant", cold=False, backend_seconds=float(value))
            self.assertEqual(summary(path, "home_assistant")["sample_count"], MAX_SAMPLES_PER_EXECUTOR)
