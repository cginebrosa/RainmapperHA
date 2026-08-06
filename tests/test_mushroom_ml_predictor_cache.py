"""Tests for mushroom_ml_predictor module-level parquet cache with mtime invalidation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import rainmapper_core.mushroom_ml_predictor as predictor_mod
from rainmapper_core.mushroom_ml_predictor import (
    _PARQUET_FILENAME,
    invalidate_weather_stations_cache,
)


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

                # Simulate runner regenerating the parquet (new mtime)
                import time
                time.sleep(0.05)
                parquet.write_bytes(b"fake_v2")

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


if __name__ == "__main__":
    unittest.main()
