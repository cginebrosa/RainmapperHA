"""Tests for mushroom_ml_trainer: temporal split and backtest stats."""
import tempfile
import unittest
from pathlib import Path

from rainmapper_core.mushroom_ml_trainer import (
    FEATURE_COLS,
    TRAIN_RATIO,
    _LABEL_FAVORABLE_THRESHOLD,
    _LABEL_UNFAVORABLE_THRESHOLD,
    _temporal_split,
    build_X_y,
    train_species,
)


def _make_row(observed_at: str, favorable: int, area_id: str = "area_a") -> dict:
    row: dict = {col: 1.0 for col in FEATURE_COLS}
    row["observed_at"] = observed_at
    row["prediction_target"] = "favorable" if favorable else "unfavorable"
    row["area_id"] = area_id
    return row


def _rows(n: int = 30) -> list:
    rows = []
    for i in range(n):
        date = f"2022-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}"
        rows.append(_make_row(date, favorable=i % 2, area_id="area_a" if i < 20 else "area_b"))
    return rows


class TemporalSplitTests(unittest.TestCase):
    def test_split_ratio_approximate(self) -> None:
        rows = _rows(30)
        train_idx, test_idx = _temporal_split(rows)
        self.assertEqual(len(train_idx) + len(test_idx), len(rows))
        self.assertAlmostEqual(len(train_idx) / len(rows), TRAIN_RATIO, delta=0.05)

    def test_test_set_contains_newest_episodes(self) -> None:
        rows = _rows(10)
        train_idx, test_idx = _temporal_split(rows)
        # All train dates must be <= all test dates (temporal ordering)
        train_dates = [rows[i]["observed_at"] for i in train_idx]
        test_dates = [rows[i]["observed_at"] for i in test_idx]
        self.assertLessEqual(max(train_dates), min(test_dates))

    def test_split_with_single_row(self) -> None:
        rows = [_make_row("2023-01-01", favorable=1)]
        train_idx, test_idx = _temporal_split(rows)
        self.assertEqual(len(train_idx), 1)
        self.assertEqual(len(test_idx), 0)

    def test_split_indices_are_disjoint(self) -> None:
        rows = _rows(20)
        train_idx, test_idx = _temporal_split(rows)
        self.assertEqual(len(set(train_idx) & set(test_idx)), 0)


class BuildXyTests(unittest.TestCase):
    def test_shape(self) -> None:
        rows = _rows(10)
        X, y, cols, _ = build_X_y(rows)
        self.assertEqual(X.shape, (10, len(FEATURE_COLS)))
        self.assertEqual(len(y), 10)
        self.assertEqual(cols, FEATURE_COLS)

    def test_y_is_binary(self) -> None:
        rows = _rows(10)
        _, y, _, _ = build_X_y(rows)
        self.assertTrue(set(y.tolist()).issubset({0, 1}))


class LabelThresholdConsistencyTests(unittest.TestCase):
    def test_thresholds_in_valid_range(self) -> None:
        self.assertGreater(_LABEL_FAVORABLE_THRESHOLD, 0.5)
        self.assertLess(_LABEL_UNFAVORABLE_THRESHOLD, 0.5)
        self.assertLess(_LABEL_UNFAVORABLE_THRESHOLD, _LABEL_FAVORABLE_THRESHOLD)


class TrainSpeciesBacktestTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("scikit-learn not installed")

    def _train(self, rows: list, tmpdir: Path) -> dict:
        return train_species("test_sp", rows, models_dir=tmpdir, cv_folds=2)

    def test_backtest_stats_keys_present(self) -> None:
        rows = _rows(30)
        with tempfile.TemporaryDirectory() as d:
            result = self._train(rows, Path(d))
        bs = result.get("backtest_stats", {})
        self.assertNotIn("error", bs, msg=f"backtest_stats had error: {bs.get('error')}")
        for key in ("total_episodes", "n_test", "holdout_test_accuracy", "favorable_ratio", "by_area"):
            self.assertIn(key, bs)

    def test_total_episodes_matches_input(self) -> None:
        rows = _rows(30)
        with tempfile.TemporaryDirectory() as d:
            result = self._train(rows, Path(d))
        self.assertEqual(result["backtest_stats"]["total_episodes"], 30)

    def test_n_test_consistent_with_train_ratio(self) -> None:
        rows = _rows(30)
        with tempfile.TemporaryDirectory() as d:
            result = self._train(rows, Path(d))
        n_test = result["backtest_stats"]["n_test"]
        expected = 30 - int(30 * TRAIN_RATIO)
        self.assertEqual(n_test, expected)

    def test_holdout_accuracy_in_valid_range(self) -> None:
        rows = _rows(30)
        with tempfile.TemporaryDirectory() as d:
            result = self._train(rows, Path(d))
        acc = result["backtest_stats"]["holdout_test_accuracy"]
        if acc is not None:
            self.assertGreaterEqual(acc, 0.0)
            self.assertLessEqual(acc, 1.0)

    def test_by_area_structure(self) -> None:
        rows = _rows(30)
        with tempfile.TemporaryDirectory() as d:
            result = self._train(rows, Path(d))
        by_area = result["backtest_stats"]["by_area"]
        self.assertIn("area_a", by_area)
        self.assertIn("area_b", by_area)
        for area_stats in by_area.values():
            for key in ("episodes", "backtest_accuracy", "false_negatives", "false_positives"):
                self.assertIn(key, area_stats)

    def test_by_area_episode_counts_sum_to_total(self) -> None:
        rows = _rows(30)
        with tempfile.TemporaryDirectory() as d:
            result = self._train(rows, Path(d))
        bs = result["backtest_stats"]
        area_total = sum(v["episodes"] for v in bs["by_area"].values())
        self.assertEqual(area_total, bs["total_episodes"])

    def test_favorable_ratio_in_valid_range(self) -> None:
        rows = _rows(30)
        with tempfile.TemporaryDirectory() as d:
            result = self._train(rows, Path(d))
        ratio = result["backtest_stats"]["favorable_ratio"]
        if ratio is not None:
            self.assertGreaterEqual(ratio, 0.0)
            self.assertLessEqual(ratio, 1.0)

    def test_joblib_file_written(self) -> None:
        rows = _rows(30)
        with tempfile.TemporaryDirectory() as d:
            result = self._train(rows, Path(d))
            joblib_path = Path(result["joblib_path"])
            self.assertTrue(joblib_path.exists())
            self.assertEqual(joblib_path.name, "mushroom_ml_v0_test_sp.joblib")


if __name__ == "__main__":
    unittest.main()
