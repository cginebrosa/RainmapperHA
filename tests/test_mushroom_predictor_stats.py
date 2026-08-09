from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core.mushroom_predictor_stats import MAX_SAMPLES_PER_EXECUTOR, rank_available, record, summary


class PredictorStatsTests(TestCase):
    def test_summary_and_ranking_use_bounded_medians(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "stats.json"
            for value in (4.0, 2.0, 3.0):
                record(path, executor_id="worker:fast", cold=False, backend_seconds=value)
            record(path, executor_id="home_assistant", cold=True, backend_seconds=30.0)

            fast = summary(path, "worker:fast")
            ranked = rank_available(path, ["home_assistant", "worker:unknown", "worker:fast"])

            self.assertEqual(fast["median_seconds"], 3.0)
            self.assertEqual(fast["warm_median_seconds"], 3.0)
            self.assertEqual(ranked[0]["executor_id"], "worker:fast")
            self.assertEqual(ranked[-1]["executor_id"], "worker:unknown")

    def test_samples_rotate(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "stats.json"
            for value in range(MAX_SAMPLES_PER_EXECUTOR + 5):
                record(path, executor_id="home_assistant", cold=False, backend_seconds=float(value))
            self.assertEqual(summary(path, "home_assistant")["sample_count"], MAX_SAMPLES_PER_EXECUTOR)

