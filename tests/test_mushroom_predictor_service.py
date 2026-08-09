from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

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

