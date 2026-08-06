"""Tests for mushroom_ml_predictor: cache invalidation, label function, predict() contract."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import rainmapper_core.mushroom_ml_predictor as predictor_mod
from rainmapper_core.mushroom_ml_predictor import (
    LABEL_FAVORABLE_THRESHOLD,
    LABEL_UNFAVORABLE_THRESHOLD,
    _PARQUET_FILENAME,
    _label,
    invalidate_weather_stations_cache,
)
from rainmapper_core.mushroom_ml_trainer import FEATURE_COLS


def _reset_cache() -> None:
    predictor_mod._shared_weather_stations = None
    predictor_mod._shared_weather_data_dir = None
    predictor_mod._shared_weather_parquet_mtime = None


class ParquetCacheMtimeTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_cache()

    def tearDown(self) -> None:
        _reset_cache()

    def _fake_load(self) -> dict:
        return {("ST1", "2024-01-01"): {"rain": 5.0}}

    def test_cache_loaded_on_first_call(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parquet = Path(d) / _PARQUET_FILENAME
            parquet.write_bytes(b"fake")
            with patch.object(predictor_mod.ctx, "load_daily_weather_parquet", return_value=self._fake_load()) as mock_load:
                result = predictor_mod._get_shared_weather_stations(Path(d))
                mock_load.assert_called_once_with(Path(d))
                self.assertEqual(result, self._fake_load())

    def test_cache_not_reloaded_when_mtime_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parquet = Path(d) / _PARQUET_FILENAME
            parquet.write_bytes(b"fake")
            with patch.object(predictor_mod.ctx, "load_daily_weather_parquet", return_value=self._fake_load()) as mock_load:
                predictor_mod._get_shared_weather_stations(Path(d))
                predictor_mod._get_shared_weather_stations(Path(d))
                self.assertEqual(mock_load.call_count, 1)

    def test_cache_reloaded_when_mtime_changes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parquet = Path(d) / _PARQUET_FILENAME
            parquet.write_bytes(b"fake_v1")

            with patch.object(predictor_mod.ctx, "load_daily_weather_parquet", return_value=self._fake_load()) as mock_load:
                predictor_mod._get_shared_weather_stations(Path(d))
                self.assertEqual(mock_load.call_count, 1)

                # Force a different mtime without relying on filesystem resolution
                import os
                new_mtime = parquet.stat().st_mtime + 1.0
                os.utime(parquet, (new_mtime, new_mtime))

                predictor_mod._get_shared_weather_stations(Path(d))
                self.assertEqual(mock_load.call_count, 2)

    def test_invalidate_clears_all_cache_state(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parquet = Path(d) / _PARQUET_FILENAME
            parquet.write_bytes(b"fake")
            with patch.object(predictor_mod.ctx, "load_daily_weather_parquet", return_value=self._fake_load()):
                predictor_mod._get_shared_weather_stations(Path(d))

            invalidate_weather_stations_cache()
            self.assertIsNone(predictor_mod._shared_weather_stations)
            self.assertIsNone(predictor_mod._shared_weather_data_dir)
            self.assertIsNone(predictor_mod._shared_weather_parquet_mtime)

    def test_cache_reloaded_after_invalidate(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parquet = Path(d) / _PARQUET_FILENAME
            parquet.write_bytes(b"fake")
            with patch.object(predictor_mod.ctx, "load_daily_weather_parquet", return_value=self._fake_load()) as mock_load:
                predictor_mod._get_shared_weather_stations(Path(d))
                invalidate_weather_stations_cache()
                predictor_mod._get_shared_weather_stations(Path(d))
                self.assertEqual(mock_load.call_count, 2)

    def test_no_parquet_falls_back_without_caching_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            # No parquet file exists — load_daily_weather_parquet falls back to CSVs
            with patch.object(predictor_mod.ctx, "load_daily_weather_parquet", return_value={}) as mock_load:
                predictor_mod._get_shared_weather_stations(Path(d))
                mock_load.assert_called_once()
                # mtime should be None since file doesn't exist — so next call reloads
                predictor_mod._get_shared_weather_stations(Path(d))
                self.assertEqual(mock_load.call_count, 2)

    def test_cache_isolated_per_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            (Path(d1) / _PARQUET_FILENAME).write_bytes(b"fake1")
            (Path(d2) / _PARQUET_FILENAME).write_bytes(b"fake2")
            with patch.object(predictor_mod.ctx, "load_daily_weather_parquet", return_value=self._fake_load()) as mock_load:
                predictor_mod._get_shared_weather_stations(Path(d1))
                predictor_mod._get_shared_weather_stations(Path(d2))
                self.assertEqual(mock_load.call_count, 2)


class LabelFunctionTests(unittest.TestCase):
    def test_label_favorable_at_exact_threshold(self) -> None:
        self.assertEqual(_label(LABEL_FAVORABLE_THRESHOLD), "favorable")

    def test_label_favorable_above_threshold(self) -> None:
        self.assertEqual(_label(0.99), "favorable")

    def test_label_unfavorable_at_exact_threshold(self) -> None:
        self.assertEqual(_label(LABEL_UNFAVORABLE_THRESHOLD), "unfavorable")

    def test_label_unfavorable_below_threshold(self) -> None:
        self.assertEqual(_label(0.01), "unfavorable")

    def test_label_uncertain_between_thresholds(self) -> None:
        self.assertEqual(_label(0.50), "uncertain")

    def test_label_uncertain_just_above_unfavorable(self) -> None:
        self.assertEqual(_label(LABEL_UNFAVORABLE_THRESHOLD + 0.01), "uncertain")

    def test_label_uncertain_just_below_favorable(self) -> None:
        self.assertEqual(_label(LABEL_FAVORABLE_THRESHOLD - 0.01), "uncertain")

    def test_label_none_returns_uncertain(self) -> None:
        self.assertEqual(_label(None), "uncertain")

    def test_favorable_threshold_is_exactly_0_60(self) -> None:
        self.assertEqual(LABEL_FAVORABLE_THRESHOLD, 0.60)

    def test_unfavorable_threshold_is_exactly_0_40(self) -> None:
        self.assertEqual(LABEL_UNFAVORABLE_THRESHOLD, 0.40)


class PredictContractTests(unittest.TestCase):
    """Test that predict() returns a PredictionResult with the expected public fields."""

    def _make_predictor(self, tmpdir: Path) -> predictor_mod.MushroomMLPredictor:
        p = predictor_mod.MushroomMLPredictor(
            species_id="test_sp",
            models_dir=tmpdir,
            weather_data_dir=tmpdir,
            features_artifact_path=tmpdir / "features.json",
            known_sites_path=tmpdir / "known_sites.json",
        )
        return p

    def _mock_bundle(self, prob: float) -> dict:
        mock_clf = MagicMock()
        mock_clf.predict_proba.return_value = [[1 - prob, prob]]
        import numpy as np
        mock_imputer = MagicMock()
        mock_imputer.transform.side_effect = lambda x: x
        mock_scaler = MagicMock()
        mock_scaler.transform.side_effect = lambda x: x
        return {"lr": mock_clf, "rf": mock_clf, "imputer": mock_imputer, "scaler": mock_scaler}

    def test_predict_returns_label_field(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = self._make_predictor(Path(d))
            p._model_bundle = self._mock_bundle(0.75)
            p._weather_stations = {}
            p._micro_area_profiles = {}
            p._area_profiles = {}
            with patch.object(p, "_build_feature_row", return_value=([0.0] * len(FEATURE_COLS), [], "ST1", 5.0, 30)):
                result = p.predict("area_a", date(2024, 10, 15))
        self.assertIn(result.label, ("favorable", "unfavorable", "uncertain"))

    def test_predict_returns_ensemble_probability(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = self._make_predictor(Path(d))
            p._model_bundle = self._mock_bundle(0.75)
            p._weather_stations = {}
            p._micro_area_profiles = {}
            p._area_profiles = {}
            with patch.object(p, "_build_feature_row", return_value=([0.0] * len(FEATURE_COLS), [], "ST1", 5.0, 30)):
                result = p.predict("area_a", date(2024, 10, 15))
        self.assertIsNotNone(result.ensemble_probability)
        self.assertGreaterEqual(result.ensemble_probability, 0.0)
        self.assertLessEqual(result.ensemble_probability, 1.0)

    def test_predict_label_consistent_with_probability(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = self._make_predictor(Path(d))
            p._model_bundle = self._mock_bundle(0.75)
            p._weather_stations = {}
            p._micro_area_profiles = {}
            p._area_profiles = {}
            with patch.object(p, "_build_feature_row", return_value=([0.0] * len(FEATURE_COLS), [], "ST1", 5.0, 30)):
                result = p.predict("area_a", date(2024, 10, 15))
        # prob 0.75 >= 0.60 → favorable
        self.assertEqual(result.label, "favorable")

    def test_predict_features_used_is_dict(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = self._make_predictor(Path(d))
            p._model_bundle = self._mock_bundle(0.30)
            p._weather_stations = {}
            p._micro_area_profiles = {}
            p._area_profiles = {}
            with patch.object(p, "_build_feature_row", return_value=([0.0] * len(FEATURE_COLS), [], "ST1", 5.0, 30)):
                result = p.predict("area_a", date(2024, 10, 15))
        self.assertIsInstance(result.features_used, dict)


if __name__ == "__main__":
    unittest.main()
