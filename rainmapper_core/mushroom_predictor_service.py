"""Transport-neutral service facade for mushroom ML inference.

The HTML application and external workers both call this module.  Keeping the
query expansion here prevents the remote predictor from becoming a second,
slightly different implementation of the model behaviour.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any, Callable

from rainmapper_core.mushroom_ml_predictor import MushroomMLPredictor, PredictionResult


SCHEMA_VERSION = "1.0"
REQUEST_KIND = "rainmapper_mushroom_predictor_request"
RESPONSE_KIND = "rainmapper_mushroom_predictor_response"
SUPPORTED_VIEWS = {"recommender", "week", "query", "history"}
ProgressCallback = Callable[[int, str, str], None]


class PredictorContractError(ValueError):
    """Raised when a predictor request or response violates contract v1."""


def _iso_date(value: object, *, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise PredictorContractError(f"{field} must be an ISO date.") from exc


def normalize_request(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PredictorContractError("Predictor request must be an object.")
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("kind") != REQUEST_KIND:
        raise PredictorContractError("Unsupported predictor request contract.")
    view = str(payload.get("view", "recommender") or "recommender").strip()
    if view not in SUPPORTED_VIEWS:
        raise PredictorContractError("Predictor view is invalid.")
    species_ids = sorted(
        {str(value).strip() for value in payload.get("trained_species_ids", []) if str(value).strip()}
    )
    if not species_ids:
        raise PredictorContractError("At least one trained species is required.")
    species_id = str(payload.get("species_id", "") or "").strip()
    if species_id and species_id not in species_ids:
        raise PredictorContractError("Selected species is not trained.")
    species_id = species_id or species_ids[0]
    area_id = str(payload.get("area_id", "") or "").strip()
    target_date = _iso_date(payload.get("target_date"), field="target_date")
    filter_mode = str(payload.get("filter_mode", "") or "").strip()[:40]
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": REQUEST_KIND,
        "view": view,
        "species_id": species_id,
        "area_id": area_id,
        "target_date": target_date.isoformat(),
        "filter_mode": filter_mode,
        "trained_species_ids": species_ids,
    }


def serialize_prediction(result: PredictionResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["target_date"] = result.target_date.isoformat()
    return payload


def deserialize_prediction(payload: object) -> PredictionResult:
    if not isinstance(payload, dict):
        raise PredictorContractError("Serialized prediction must be an object.")
    return PredictionResult(
        species_id=str(payload.get("species_id", "")),
        area_id=str(payload.get("area_id", "")),
        target_date=_iso_date(payload.get("target_date"), field="prediction.target_date"),
        lr_probability=_optional_float(payload.get("lr_probability")),
        rf_probability=_optional_float(payload.get("rf_probability")),
        ensemble_probability=_optional_float(payload.get("ensemble_probability")),
        label=str(payload.get("label", "uncertain")),
        weather_station_code=_optional_string(payload.get("weather_station_code")),
        weather_station_distance_km=_optional_float(payload.get("weather_station_distance_km")),
        weather_coverage_days=_optional_int(payload.get("weather_coverage_days")),
        feature_gaps=[str(value) for value in payload.get("feature_gaps", [])],
        features_used=dict(payload.get("features_used", {})),
    )


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)


class PredictorService:
    """Execute predictor contract v1 against one immutable runtime."""

    def __init__(
        self,
        *,
        models_dir: Path,
        weather_data_dir: Path,
        features_artifact_path: Path,
        known_sites_path: Path,
        runtime_fingerprint: str,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.weather_data_dir = Path(weather_data_dir)
        self.features_artifact_path = Path(features_artifact_path)
        self.known_sites_path = Path(known_sites_path)
        self.runtime_fingerprint = str(runtime_fingerprint)
        self._predictors: dict[str, MushroomMLPredictor] = {}
        self._lock = RLock()

    def predictor(self, species_id: str) -> MushroomMLPredictor:
        with self._lock:
            predictor = self._predictors.get(species_id)
            if predictor is None:
                predictor = MushroomMLPredictor(
                    species_id,
                    models_dir=self.models_dir,
                    weather_data_dir=self.weather_data_dir,
                    features_artifact_path=self.features_artifact_path,
                    known_sites_path=self.known_sites_path,
                )
                self._predictors[species_id] = predictor
            return predictor

    def execute(
        self,
        request: object,
        *,
        progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_request(request)
        started = monotonic()
        report = progress or (lambda _percent, _phase, _message: None)
        report(2, "Preparing predictor", "Validating the prediction request.")
        view = normalized["view"]
        species_ids = normalized["trained_species_ids"]
        selected_species = normalized["species_id"]
        target = date.fromisoformat(normalized["target_date"])
        area_id = normalized["area_id"]
        data: dict[str, Any] = {"species": {}}

        if view == "recommender":
            total = len(species_ids)
            for index, species_id in enumerate(species_ids):
                report(
                    5 + round(index / max(1, total) * 88),
                    "Evaluating species",
                    f"{index + 1}/{total}: {species_id}",
                )
                predictor = self.predictor(species_id)
                data["species"][species_id] = {
                    "rankings": {
                        target.isoformat(): [
                            serialize_prediction(row)
                            for row in predictor.rank_areas(target, only_observed=True)
                        ]
                    }
                }
        elif view == "week":
            predictor = self.predictor(selected_species)
            areas = predictor.areas_with_species_observations()
            days = [date.today() + timedelta(days=offset) for offset in range(7)]
            predictions: dict[str, dict[str, Any]] = {}
            total = max(1, len(areas) * len(days))
            completed = 0
            for current_area in areas:
                predictions[current_area] = {}
                for current_date in days:
                    predictions[current_area][current_date.isoformat()] = serialize_prediction(
                        predictor.predict(current_area, current_date)
                    )
                    completed += 1
                    report(
                        5 + round(completed / total * 88),
                        "Building weekly matrix",
                        f"{completed}/{total} area-days",
                    )
            data["species"][selected_species] = {"areas": areas, "predictions": predictions}
        elif view == "history":
            report(10, "Loading history", f"Backtesting {selected_species}.")
            predictor = self.predictor(selected_species)
            data["species"][selected_species] = {
                "backtest": predictor.backtest(),
                "areas": predictor.areas_with_species_observations(),
            }
        else:
            predictor = self.predictor(selected_species)
            areas = predictor.areas_with_species_observations()
            species_data: dict[str, Any] = {"areas": areas}
            if area_id:
                today = date.today()
                current_week = {today + timedelta(days=offset) for offset in range(7)}
                week_start = today if target in current_week else target
                report(20, "Evaluating area", f"Predicting {area_id}.")
                week = predictor.week_window(area_id, week_start)
                species_data["predictions"] = {
                    area_id: {row.target_date.isoformat(): serialize_prediction(row) for row in week}
                }
                if target.isoformat() not in species_data["predictions"][area_id]:
                    row = predictor.predict(area_id, target)
                    species_data["predictions"][area_id][target.isoformat()] = serialize_prediction(row)
            else:
                report(20, "Ranking areas", f"Evaluating {selected_species}.")
                species_data["rankings"] = {
                    target.isoformat(): [
                        serialize_prediction(row)
                        for row in predictor.rank_areas(target, only_observed=True)
                    ]
                }
            data["species"][selected_species] = species_data

        elapsed = round(monotonic() - started, 4)
        report(100, "Prediction complete", "Results are ready.")
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": RESPONSE_KIND,
            "runtime_fingerprint": self.runtime_fingerprint,
            "request": normalized,
            "data": data,
            "metrics": {
                "backend_seconds": elapsed,
                "loaded_predictor_count": len(self._predictors),
            },
        }


class PreparedPredictor:
    """Read-only MushroomMLPredictor-compatible adapter for server rendering."""

    def __init__(self, species_id: str, response: dict[str, Any]) -> None:
        self.species_id = species_id
        self._data = dict(response.get("data", {}).get("species", {}).get(species_id, {}))

    def areas_with_species_observations(self) -> list[str]:
        return [str(value) for value in self._data.get("areas", [])]

    def predict(self, area_id: str, target_date: date) -> PredictionResult:
        payload = self._data.get("predictions", {}).get(area_id, {}).get(target_date.isoformat())
        if payload is None:
            for row in self._data.get("rankings", {}).get(target_date.isoformat(), []):
                if row.get("area_id") == area_id:
                    payload = row
                    break
        if payload is None:
            raise PredictorContractError(f"Prepared result is missing {area_id} on {target_date}.")
        return deserialize_prediction(payload)

    def rank_areas(
        self,
        target_date: date,
        area_ids: list[str] | None = None,
        only_observed: bool = True,
    ) -> list[PredictionResult]:
        del only_observed
        rows = [
            deserialize_prediction(row)
            for row in self._data.get("rankings", {}).get(target_date.isoformat(), [])
        ]
        return rows if area_ids is None else [row for row in rows if row.area_id in area_ids]

    def week_window(self, area_id: str, start_date: date) -> list[PredictionResult]:
        return [self.predict(area_id, start_date + timedelta(days=offset)) for offset in range(7)]

    def backtest(self, *_args: object, **_kwargs: object) -> list[dict[str, Any]]:
        return [dict(row) for row in self._data.get("backtest", [])]


def validate_response(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PredictorContractError("Predictor response must be an object.")
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("kind") != RESPONSE_KIND:
        raise PredictorContractError("Unsupported predictor response contract.")
    normalize_request(payload.get("request"))
    if not isinstance(payload.get("data"), dict) or not isinstance(payload.get("metrics"), dict):
        raise PredictorContractError("Predictor response payload is incomplete.")
    return dict(payload)
