from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import ANY, Mock

from rainmapper_core.mushroom_ml_predictor import PredictionResult
from rainmapper_core.mushroom_predictor_service import (
    PreparedPredictor,
    PredictorContractError,
    PredictorService,
    REQUEST_KIND,
    SCHEMA_VERSION,
    normalize_request,
    validate_response,
)


def prediction(species: str, area: str, day: date, probability: float = 0.7) -> PredictionResult:
    return PredictionResult(
        species_id=species,
        area_id=area,
        target_date=day,
        lr_probability=probability,
        rf_probability=probability,
        ensemble_probability=probability,
        label="favorable",
        weather_station_code="station",
        weather_station_distance_km=1.2,
        weather_coverage_days=90,
        features_used={"rain_7d_mm": 12.0},
    )


class PredictorServiceTests(TestCase):
    def request(self, **changes: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "kind": REQUEST_KIND,
            "view": "query",
            "species_id": "boletus",
            "area_id": "area_one",
            "target_date": "2026-08-09",
            "trained_species_ids": ["boletus"],
        }
        payload.update(changes)
        return payload

    def test_normalize_request_rejects_unknown_view(self) -> None:
        with self.assertRaises(PredictorContractError):
            normalize_request(self.request(view="unknown"))

    def test_query_response_can_be_rendered_through_prepared_adapter(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9 + offset))
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            comparator = Mock()
            comparator.compare.return_value = {"interpretation": {"verdict": "uncertain"}}
            service.comparator = Mock(return_value=comparator)
            progress: list[int] = []

            response = service.execute(
                self.request(), progress=lambda percent, _phase, _message: progress.append(percent)
            )
            validate_response(response)
            prepared = PreparedPredictor("boletus", response)

            self.assertEqual(prepared.areas_with_species_observations(), ["area_one"])
            self.assertEqual(prepared.predict("area_one", date(2026, 8, 9)).ensemble_probability, 0.7)
            self.assertEqual(len(prepared.week_window("area_one", date(2026, 8, 9))), 7)
            self.assertEqual(progress[-1], 100)

    def test_query_drops_area_that_does_not_belong_to_selected_species(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.rank_areas.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9))
            ]
            service.predictor = Mock(return_value=predictor)
            comparator = Mock()
            comparator.compare.return_value = {"interpretation": {"verdict": "uncertain"}}
            service.comparator = Mock(return_value=comparator)

            response = service.execute(self.request(area_id="area_from_previous_species"))

        self.assertEqual(response["request"]["area_id"], "")
        self.assertEqual(
            response["data"]["species"]["boletus"]["areas"], ["area_one"]
        )
        predictor.week_window.assert_not_called()
        predictor.rank_areas.assert_called_once_with(date(2026, 8, 9), only_observed=True)

    def test_identical_request_reuses_bounded_response_cache(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9 + offset))
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            comparator = Mock()
            comparator.compare.return_value = {"interpretation": {"verdict": "uncertain"}}
            service.comparator = Mock(return_value=comparator)

            first = service.execute(self.request())
            second = service.execute(self.request())

        self.assertEqual(first["metrics"]["response_cache_status"], "miss")
        self.assertEqual(second["metrics"]["response_cache_status"], "hit")
        predictor.week_window.assert_called_once()

    def test_query_attaches_common_idw_v2_reference_comparison(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9 + offset))
                for offset in range(7)
            ]
            v2_compare = Mock(
                return_value={
                "fixed_gap_7d_altitude_v2": {"available": True},
                "interpretation": {"verdict": "uncertain"},
                }
            )
            service.predictor = Mock(return_value=predictor)
            service.v2_reference_compare = v2_compare

            response = service.execute(
                self.request(compare_models=True, issue_date="2026-08-09")
            )

        comparison = response["data"]["species"]["boletus"]["model_comparisons"]
        self.assertTrue(
            comparison["area_one"]["2026-08-09"]["fixed_gap_7d_altitude_v2"][
                "available"
            ]
        )
        self.assertEqual(v2_compare.call_count, 7)
        v2_compare.assert_any_call(
            species_id="boletus",
            area_id="area_one",
            target_date=date(2026, 8, 9),
            issue_date=date(2026, 8, 9),
            prepared_weather_cache=ANY,
            comparison_cache=ANY,
        )

    def test_week_view_batches_all_area_days(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = [
                "area_one",
                "area_two",
            ]
            predictor.predict_many.side_effect = lambda requests: [
                prediction("boletus", area_id, target_date)
                for area_id, target_date in requests
            ]
            service.predictor = Mock(return_value=predictor)
            v2_compare = Mock(
                return_value={"interpretation": {"verdict": "uncertain"}}
            )
            service.v2_reference_compare = v2_compare

            response = service.execute(self.request(view="week", area_id=""))

        validate_response(response)
        predictor.predict_many.assert_called_once()
        self.assertEqual(len(predictor.predict_many.call_args.args[0]), 14)
        self.assertEqual(v2_compare.call_count, 14)

    def test_recommender_skips_species_outside_configured_season(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.season_phase.return_value = "out_of_season"
            service.predictor = Mock(return_value=predictor)

            response = service.execute(
                self.request(
                    view="recommender",
                    area_id="",
                    target_date="2026-08-10",
                )
            )

        species_data = response["data"]["species"]["boletus"]
        self.assertEqual(species_data["season_phase"], "out_of_season")
        self.assertEqual(species_data["rankings"]["2026-08-10"], [])
        predictor.rank_areas.assert_not_called()

    def test_recommender_prepared_adapter_exposes_ranked_areas(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.season_phase.return_value = "in_season"
            predictor.rank_areas.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 10))
            ]
            service.predictor = Mock(return_value=predictor)
            comparator = Mock()
            comparator.compare.return_value = {"interpretation": {"verdict": "favorable"}}
            service.comparator = Mock(return_value=comparator)

            response = service.execute(
                self.request(view="recommender", area_id="", target_date="2026-08-10")
            )
            prepared = PreparedPredictor("boletus", response)

        self.assertEqual(
            response["data"]["species"]["boletus"]["areas"], ["area_one"]
        )
        self.assertEqual(prepared.areas_with_species_observations(), ["area_one"])
