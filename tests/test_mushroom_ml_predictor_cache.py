"""Tests for mushroom_ml_predictor: cache invalidation, label function, predict() contract."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from threading import Barrier, Thread
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
    predictor_mod._shared_weather_station_filter = None
    predictor_mod._shared_weather_window_start = None
    predictor_mod._shared_weather_window_end = None
    predictor_mod._shared_stations_catalog = None
    predictor_mod._shared_catalog_data_dir = None
    predictor_mod._shared_catalog_mtime = None


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
                mock_load.assert_called_once_with(Path(d), station_filter=None)
                self.assertEqual(result, self._fake_load())

    def test_physical_load_records_metrics_and_retention_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parquet = Path(d) / _PARQUET_FILENAME
            parquet.write_bytes(b"fake")
            monitor = MagicMock()
            monitor.enabled = True
            monitor.operation_id = "predictor-load-test"
            with (
                patch.object(
                    predictor_mod.ctx,
                    "load_daily_weather_parquet",
                    return_value=self._fake_load(),
                ),
                patch.object(
                    predictor_mod.runtime_diagnostics,
                    "OperationMonitor",
                    return_value=monitor,
                ) as monitor_factory,
                patch.object(
                    predictor_mod.runtime_diagnostics,
                    "schedule_snapshot",
                ) as schedule_snapshot,
            ):
                predictor_mod._get_shared_weather_stations(
                    Path(d),
                    station_filter={("meteocat", "ST1")},
                )

        monitor_factory.assert_called_once()
        self.assertEqual(
            monitor_factory.call_args.kwargs["details"]["filter_station_count"],
            1,
        )
        monitor.finish.assert_called_once_with(
            "ok",
            {
                "loaded_station_count": 1,
                "loaded_record_count": 0,
                "window_start": None,
                "window_end": None,
            },
        )
        self.assertEqual(schedule_snapshot.call_count, 2)
        self.assertEqual(
            [call.args[2] for call in schedule_snapshot.call_args_list],
            ["retained_60s", "retained_600s"],
        )

    def test_lazy_model_load_is_correlated_without_species_in_diagnostics(self) -> None:
        import joblib

        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            species_id = "private-species"
            model_path = data_dir / f"mushroom_ml_v0_{species_id}.joblib"
            joblib.dump({"feature_cols": []}, model_path)
            metrics_path = data_dir / "runtime_metrics.jsonl"
            predictor = predictor_mod.MushroomMLPredictor(
                species_id,
                models_dir=data_dir,
            )
            with (
                patch.dict(
                    predictor_mod.runtime_diagnostics.os.environ,
                    {"RAINMAPPER_RUNTIME_DIAGNOSTICS_PATH": str(metrics_path)},
                ),
                predictor_mod.runtime_diagnostics.operation_context(
                    "parent-predictor-request"
                ),
            ):
                predictor._ensure_model()

            records = [
                json.loads(line)
                for line in metrics_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(records[0]["operation"], "predictor_model_load")
        self.assertEqual(
            records[0]["details"]["parent_operation_id"],
            "parent-predictor-request",
        )
        self.assertNotIn(species_id, json.dumps(records))

    def test_cache_not_reloaded_when_mtime_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parquet = Path(d) / _PARQUET_FILENAME
            parquet.write_bytes(b"fake")
            with patch.object(predictor_mod.ctx, "load_daily_weather_parquet", return_value=self._fake_load()) as mock_load:
                predictor_mod._get_shared_weather_stations(Path(d))
                predictor_mod._get_shared_weather_stations(Path(d))
                self.assertEqual(mock_load.call_count, 1)

    def test_concurrent_cold_cache_performs_one_physical_load(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            (data_dir / _PARQUET_FILENAME).write_bytes(b"fake")
            start = Barrier(3)
            results: list[dict] = []

            def worker() -> None:
                start.wait()
                results.append(
                    predictor_mod._get_shared_weather_stations(
                        data_dir,
                        station_filter={("meteocat", "ST1")},
                    )
                )

            with patch.object(
                predictor_mod.ctx,
                "load_daily_weather_parquet",
                return_value=self._fake_load(),
            ) as mock_load:
                threads = [Thread(target=worker), Thread(target=worker)]
                for thread in threads:
                    thread.start()
                start.wait()
                for thread in threads:
                    thread.join(timeout=2)

            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(mock_load.call_count, 1)
            self.assertEqual(results, [self._fake_load(), self._fake_load()])

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

    def test_predictor_instance_rebinds_when_parquet_mtime_changes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            import os

            data_dir = Path(d)
            parquet = data_dir / _PARQUET_FILENAME
            parquet.write_bytes(b"fake_v1")
            (data_dir / predictor_mod._CATALOG_FILENAME).write_bytes(b"fake")
            predictor = predictor_mod.MushroomMLPredictor(
                "test",
                weather_data_dir=data_dir,
            )
            predictor._micro_area_profiles = {
                "ma": MagicMock(lat=42.0, lon=2.0)
            }
            loads = [
                {("meteocat", "ST1"): "first"},
                {("meteocat", "ST1"): "second"},
            ]

            with patch.object(
                predictor_mod.ctx,
                "load_stations_catalog",
                return_value=MagicMock(empty=False),
            ), patch.object(
                predictor_mod,
                "_compute_station_filter",
                return_value={("meteocat", "ST1")},
            ), patch.object(
                predictor_mod.ctx,
                "load_daily_weather_parquet",
                side_effect=loads,
            ) as weather_load:
                predictor._ensure_weather_stations()
                first = predictor._weather_stations
                new_mtime = parquet.stat().st_mtime + 1.0
                os.utime(parquet, (new_mtime, new_mtime))
                predictor._ensure_weather_stations()

            # Replaced windows are explicitly emptied so predictor instances do
            # not retain stale weather histories through old dict references.
            self.assertEqual(first, {})
            self.assertEqual(
                predictor._weather_stations,
                {("meteocat", "ST1"): "second"},
            )
            self.assertEqual(weather_load.call_count, 2)

    def test_cache_reloaded_when_station_filter_changes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            parquet = Path(d) / _PARQUET_FILENAME
            parquet.write_bytes(b"fake")
            with patch.object(
                predictor_mod.ctx,
                "load_daily_weather_parquet",
                return_value=self._fake_load(),
            ) as mock_load:
                predictor_mod._get_shared_weather_stations(
                    Path(d), station_filter={("meteocat", "ST1")}
                )
                predictor_mod._get_shared_weather_stations(
                    Path(d), station_filter={("meteocat", "ST2")}
                )

                self.assertEqual(mock_load.call_count, 2)
                self.assertEqual(
                    predictor_mod._shared_weather_station_filter,
                    frozenset({("meteocat", "ST2")}),
                )

    def test_target_date_loads_bounded_lookback_and_week_prefetch(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            (data_dir / _PARQUET_FILENAME).write_bytes(b"fake")
            target = date(2026, 8, 8)
            loaded = self._fake_load()
            with patch.object(
                predictor_mod.ctx,
                "load_daily_weather_parquet",
                return_value=loaded,
            ) as mock_load:
                result = predictor_mod._get_shared_weather_stations(
                    data_dir,
                    station_filter={("meteocat", "ST1")},
                    target_date=target,
                )

            self.assertIs(result, loaded)
            mock_load.assert_called_once_with(
                data_dir,
                station_filter={("meteocat", "ST1")},
                start_date=date(2026, 5, 11),
                end_date=date(2026, 8, 14),
            )
            self.assertEqual(
                predictor_mod._shared_weather_window_start,
                date(2026, 5, 11),
            )
            self.assertEqual(
                predictor_mod._shared_weather_window_end,
                date(2026, 8, 14),
            )

    def test_prefetched_week_reuses_one_physical_read(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            (data_dir / _PARQUET_FILENAME).write_bytes(b"fake")
            with patch.object(
                predictor_mod.ctx,
                "load_daily_weather_parquet",
                return_value=self._fake_load(),
            ) as mock_load:
                for offset in range(7):
                    predictor_mod._get_shared_weather_stations(
                        data_dir,
                        station_filter={("meteocat", "ST1")},
                        target_date=date(2026, 8, 8) + timedelta(days=offset),
                    )

            self.assertEqual(mock_load.call_count, 1)

    def test_distant_date_replaces_window_and_releases_old_records(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            (data_dir / _PARQUET_FILENAME).write_bytes(b"fake")
            first_load = {("meteocat", "ST1"): "present"}
            second_load = {("meteocat", "ST1"): "historical"}
            with patch.object(
                predictor_mod.ctx,
                "load_daily_weather_parquet",
                side_effect=[first_load, second_load],
            ) as mock_load:
                first_result = predictor_mod._get_shared_weather_stations(
                    data_dir,
                    station_filter={("meteocat", "ST1")},
                    target_date=date(2026, 8, 8),
                )
                second_result = predictor_mod._get_shared_weather_stations(
                    data_dir,
                    station_filter={("meteocat", "ST1")},
                    target_date=date(2024, 7, 10),
                )

            self.assertEqual(mock_load.call_count, 2)
            self.assertEqual(first_result, {})
            self.assertIs(second_result, second_load)
            self.assertEqual(
                predictor_mod._shared_weather_window_start,
                date(2024, 4, 12),
            )
            self.assertEqual(
                predictor_mod._shared_weather_window_end,
                date(2024, 7, 16),
            )

    def test_explicit_history_range_is_loaded_once_and_reused_by_episodes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            (data_dir / _PARQUET_FILENAME).write_bytes(b"fake")
            with patch.object(
                predictor_mod.ctx,
                "load_daily_weather_parquet",
                return_value=self._fake_load(),
            ) as mock_load:
                predictor_mod._get_shared_weather_stations(
                    data_dir,
                    station_filter={("meteocat", "ST1")},
                    target_date=date(2020, 10, 1),
                    target_end_date=date(2026, 5, 20),
                )
                for episode_date in (
                    date(2020, 10, 1),
                    date(2023, 11, 15),
                    date(2026, 5, 20),
                ):
                    predictor_mod._get_shared_weather_stations(
                        data_dir,
                        station_filter={("meteocat", "ST1")},
                        target_date=episode_date,
                    )

            mock_load.assert_called_once_with(
                data_dir,
                station_filter={("meteocat", "ST1")},
                start_date=date(2020, 7, 4),
                end_date=date(2026, 5, 26),
            )

    def test_invalid_explicit_target_range_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires target_date"):
            predictor_mod._get_shared_weather_stations(
                Path("unused"),
                target_end_date=date(2026, 1, 1),
            )
        with self.assertRaisesRegex(ValueError, "must not be after"):
            predictor_mod._get_shared_weather_stations(
                Path("unused"),
                target_date=date(2026, 1, 2),
                target_end_date=date(2026, 1, 1),
            )

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
            self.assertIsNone(predictor_mod._shared_weather_station_filter)
            self.assertIsNone(predictor_mod._shared_weather_window_start)
            self.assertIsNone(predictor_mod._shared_weather_window_end)

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


class PredictorFeatureParityTests(unittest.TestCase):
    @staticmethod
    def _record(
        station_code: str,
        day: date,
        lat: float,
        lon: float,
        rain_mm: float,
    ) -> predictor_mod.ctx.DailyWeatherRecord:
        return predictor_mod.ctx.DailyWeatherRecord(
            source="meteocat",
            station_code=station_code,
            station_name=station_code,
            day=day,
            lat=lat,
            lon=lon,
            rain_mm=rain_mm,
            temp_max_c=20.0,
            temp_min_c=10.0,
            humidity_max_pct=90.0,
            humidity_min_pct=60.0,
            wind_avg_kmh=None,
            wind_gust_kmh=None,
            wind_direction_deg=None,
        )

    def test_feature_builder_uses_best_covered_nearby_station_and_duplicate_filter(self) -> None:
        target_date = date(2026, 1, 10)
        nearest_record = self._record(
            "LOW_COVERAGE", target_date - timedelta(days=1), 42.0, 2.0, 1.0
        )
        covered_records = {
            day: self._record("COVERED", day, 42.05, 2.05, 5.0)
            for day in (target_date - timedelta(days=2), target_date - timedelta(days=1))
        }
        nearest = predictor_mod.ctx.WeatherStation(
            source="meteocat",
            station_code="LOW_COVERAGE",
            station_name="LOW_COVERAGE",
            lat=42.0,
            lon=2.0,
            records_by_day={nearest_record.day: nearest_record},
        )
        covered = predictor_mod.ctx.WeatherStation(
            source="meteocat",
            station_code="COVERED",
            station_name="COVERED",
            lat=42.05,
            lon=2.05,
            records_by_day=covered_records,
        )
        predictor = predictor_mod.MushroomMLPredictor("test")
        predictor._weather_stations = {
            (nearest.source, nearest.station_code): nearest,
            (covered.source, covered.station_code): covered,
        }
        profile = predictor_mod.AreaProfile(
            area_id="area",
            lat=42.0,
            lon=2.0,
            gis_altitude_m=900.0,
        )

        values, gaps, station_code, _distance, coverage = predictor._build_feature_row(
            target_date, profile
        )

        self.assertEqual(station_code, "COVERED")
        self.assertEqual(coverage, 2)
        self.assertEqual(values[FEATURE_COLS.index("rain_7d_mm")], 5.0)
        self.assertTrue(
            any("rain_suspect_consecutive_20260109" in gap for gap in gaps)
        )


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
        self.assertEqual(list(result.features_used), FEATURE_COLS)
        self.assertEqual(result.features_used["rain_14d_mm"], 0.0)
        self.assertEqual(result.features_used["temp_max_7d_c"], 0.0)
        self.assertNotIn("rain_15d_mm", result.features_used)

    def test_predict_features_used_converts_nan_to_none(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = self._make_predictor(Path(d))
            p._model_bundle = self._mock_bundle(0.30)
            p._weather_stations = {}
            p._micro_area_profiles = {}
            p._area_profiles = {}
            values = [0.0] * len(FEATURE_COLS)
            values[FEATURE_COLS.index("rain_1d_mm")] = float("nan")
            with patch.object(
                p,
                "_build_feature_row",
                return_value=(values, [], "ST1", 5.0, 30),
            ):
                result = p.predict("area_a", date(2024, 10, 15))

        self.assertIsNone(result.features_used["rain_1d_mm"])


if __name__ == "__main__":
    unittest.main()
