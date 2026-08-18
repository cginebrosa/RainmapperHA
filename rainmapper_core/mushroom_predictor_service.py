"""Transport-neutral service facade for mushroom ML inference.

The HTML application and external workers both call this module.  Keeping the
query expansion here prevents the remote predictor from becoming a second,
slightly different implementation of the model behaviour.
"""

from __future__ import annotations

import copy
import json
from collections import OrderedDict
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any, Callable, Mapping, Sequence

from rainmapper_core.mushroom_ml_comparison import MushroomModelComparator
from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_ml_multiversion_comparison
from rainmapper_core import mushroom_weather_idw
from rainmapper_core.mushroom_ml_predictor import MushroomMLPredictor, PredictionResult
from rainmapper_core.mushroom_prediction_interpretation import build_interpretation


SCHEMA_VERSION = "1.0"
REQUEST_KIND = "rainmapper_mushroom_predictor_request"
RESPONSE_KIND = "rainmapper_mushroom_predictor_response"
SUPPORTED_VIEWS = {"recommender", "week", "query", "history"}
ProgressCallback = Callable[[int, str, str], None]
_RESPONSE_CACHE_MAX_ENTRIES = 32


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
    compare_models = payload.get("compare_models") is True
    raw_selection = payload.get("multiversion_selection", [])
    if not isinstance(raw_selection, list) or len(raw_selection) > 256:
        raise PredictorContractError("Multiversion comparison selection is invalid.")
    multiversion_selection: list[dict[str, Any]] = []
    for row in raw_selection:
        if not isinstance(row, dict):
            raise PredictorContractError("Multiversion comparison member is invalid.")
        try:
            horizon_days = int(row.get("horizon_days", 0))
        except (TypeError, ValueError) as exc:
            raise PredictorContractError("Comparison horizon is invalid.") from exc
        normalized_member = {
            key: str(row.get(key, "") or "").strip()
            for key in (
                "version_id",
                "temporal_contract_id",
                "profile_id",
                "estimator_id",
            )
        }
        if not all(normalized_member.values()) or horizon_days not in range(1, 8):
            raise PredictorContractError("Multiversion comparison member is incomplete.")
        normalized_member["horizon_days"] = horizon_days
        if normalized_member not in multiversion_selection:
            multiversion_selection.append(normalized_member)
    issue_date = _iso_date(
        payload.get("issue_date") or min(date.today(), target_date).isoformat(),
        field="issue_date",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": REQUEST_KIND,
        "view": view,
        "species_id": species_id,
        "area_id": area_id,
        "target_date": target_date.isoformat(),
        "filter_mode": filter_mode,
        "compare_models": compare_models,
        "multiversion_selection": multiversion_selection,
        "issue_date": issue_date.isoformat(),
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
        season_phase=str(payload.get("season_phase", "unknown")),
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
        profiles_path: Path | None = None,
        version_registry_path: Path | None = None,
        runtime_batch_manifest_path: Path | None = None,
        stations_file_path: Path | None = None,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.weather_data_dir = Path(weather_data_dir)
        self.features_artifact_path = Path(features_artifact_path)
        self.known_sites_path = Path(known_sites_path)
        self.profiles_path = Path(profiles_path) if profiles_path is not None else None
        self.version_registry_path = (
            Path(version_registry_path) if version_registry_path is not None else None
        )
        self.runtime_batch_manifest_path = (
            Path(runtime_batch_manifest_path)
            if runtime_batch_manifest_path is not None
            else None
        )
        self.stations_file_path = (
            Path(stations_file_path) if stations_file_path is not None else None
        )
        self.runtime_fingerprint = str(runtime_fingerprint)
        self._predictors: dict[str, MushroomMLPredictor] = {}
        self._comparators: dict[str, MushroomModelComparator] = {}
        self._responses: OrderedDict[tuple[object, ...], dict[str, Any]] = (
            OrderedDict()
        )
        self._lock = RLock()

    def model_catalog(self) -> dict[str, Any]:
        """Describe catalog and installed batch without claiming absent models."""
        if self.version_registry_path is None or not self.version_registry_path.is_file():
            return {"available": False, "reason": "version_registry_missing", "entries": []}
        try:
            registry = mushroom_ml_version_registry.load_registry(
                self.version_registry_path
            )
            entries = mushroom_ml_model_catalog.catalog_entries(registry)
        except (OSError, ValueError) as exc:
            return {
                "available": False,
                "reason": "version_registry_invalid",
                "message": str(exc),
                "entries": [],
            }
        result: dict[str, Any] = {
            "available": True,
            "active_version_id": registry["active_version_id"],
            "entries": entries,
            "runtime_batch": None,
            "installed_artifacts": [],
        }
        if (
            self.runtime_batch_manifest_path is None
            or not self.runtime_batch_manifest_path.is_file()
        ):
            result["runtime_batch_status"] = "not_installed"
            return result
        try:
            batch = mushroom_ml_model_catalog.validate_batch_manifest(
                registry,
                json.loads(
                    self.runtime_batch_manifest_path.read_text(encoding="utf-8")
                ),
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            result["runtime_batch_status"] = "invalid"
            result["runtime_batch_error"] = str(exc)
            return result
        result["runtime_batch_status"] = "installed"
        result["runtime_batch"] = {
            "batch_id": batch["batch_id"],
            "snapshot_id": batch["snapshot_id"],
        }
        result["installed_artifacts"] = [
            {
                "artifact_ref": dict(row["artifact_ref"]),
                "supported_horizons": list(row["supported_horizons"]),
            }
            for row in batch["artifacts"]
        ]
        return result

    def multiversion_compare(
        self,
        *,
        species_id: str,
        area_id: str,
        target_date: date,
        selections: Sequence[Mapping[str, object]],
    ) -> dict[str, Any]:
        if not selections:
            return {"available": False, "reason": "no_models_selected"}
        if (
            self.version_registry_path is None
            or self.runtime_batch_manifest_path is None
            or not self.version_registry_path.is_file()
            or not self.runtime_batch_manifest_path.is_file()
        ):
            return {"available": False, "reason": "runtime_batch_not_installed"}
        try:
            registry = mushroom_ml_version_registry.load_registry(
                self.version_registry_path
            )
            manifest = json.loads(
                self.runtime_batch_manifest_path.read_text(encoding="utf-8")
            )
            result = mushroom_ml_multiversion_comparison.compare_selection(
                registry,
                manifest,
                selections,
                species_id=species_id,
                area_id=area_id,
                target_date=target_date,
                models_root=self.models_dir,
                known_sites_path=self.known_sites_path,
                weather_data_dir=self.weather_data_dir,
                excluded_station_keys=(
                    mushroom_weather_idw.disabled_wunderground_station_keys(
                        self.stations_file_path
                    )
                    if self.stations_file_path is not None
                    and self.stations_file_path.is_file()
                    else frozenset()
                ),
            )
            return {"available": True, **result}
        except (OSError, KeyError, TypeError, ValueError) as exc:
            return {
                "available": False,
                "reason": "multiversion_runtime_error",
                "message": str(exc),
            }

    def v2_reference_compare(
        self,
        *,
        species_id: str,
        area_id: str,
        target_date: date,
        issue_date: date,
        prepared_weather_cache: dict[tuple[object, ...], Any] | None = None,
        comparison_cache: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve the card's V2 rows from the installed common-IDW batch only."""
        predictor = self.predictor(species_id)
        season_phase = predictor.season_phase(target_date)
        unavailable = {
            "available": False,
            "reason": "runtime_batch_not_installed",
        }
        if (
            self.version_registry_path is None
            or self.runtime_batch_manifest_path is None
            or not self.version_registry_path.is_file()
            or not self.runtime_batch_manifest_path.is_file()
        ):
            payload: dict[str, Any] = {
                "issue_date": issue_date.isoformat(),
                "target_date": target_date.isoformat(),
                "season_phase": season_phase,
                mushroom_ml_multiversion_comparison.V2_FIXED_CONTRACT_ID: dict(
                    unavailable
                ),
                mushroom_ml_multiversion_comparison.V2_LAG_CONTRACT_ID: dict(
                    unavailable
                ),
            }
            payload["interpretation"] = build_interpretation(
                payload, season_phase=season_phase, phenology={}
            )
            return payload
        phenology: dict[str, Any] = {}
        try:
            if self.profiles_path is None:
                raise FileNotFoundError("Mushroom profiles are unavailable")
            profiles = json.loads(self.profiles_path.read_text(encoding="utf-8"))
            species_profile = next(
                (
                    row
                    for row in profiles.get("species_profiles", [])
                    if isinstance(row, dict) and row.get("species_id") == species_id
                ),
                {},
            )
            phenology = dict(species_profile.get("phenology") or {})
        except (OSError, TypeError, ValueError):
            phenology = {}
        try:
            return mushroom_ml_multiversion_comparison.compare_v2_reference(
                mushroom_ml_version_registry.load_registry(
                    self.version_registry_path
                ),
                json.loads(
                    self.runtime_batch_manifest_path.read_text(encoding="utf-8")
                ),
                species_id=species_id,
                area_id=area_id,
                target_date=target_date,
                issue_date=issue_date,
                season_phase=season_phase,
                phenology=phenology,
                models_root=self.models_dir,
                known_sites_path=self.known_sites_path,
                weather_data_dir=self.weather_data_dir,
                excluded_station_keys=(
                    mushroom_weather_idw.disabled_wunderground_station_keys(
                        self.stations_file_path
                    )
                    if self.stations_file_path is not None
                    and self.stations_file_path.is_file()
                    else frozenset()
                ),
                prepared_weather_cache=prepared_weather_cache,
                comparison_cache=comparison_cache,
            )
        except (OSError, KeyError, TypeError, ValueError) as exc:
            payload = {
                "issue_date": issue_date.isoformat(),
                "target_date": target_date.isoformat(),
                "season_phase": season_phase,
                mushroom_ml_multiversion_comparison.V2_FIXED_CONTRACT_ID: {
                    "available": False,
                    "reason": "v2_runtime_error",
                    "message": str(exc),
                },
                mushroom_ml_multiversion_comparison.V2_LAG_CONTRACT_ID: {
                    "available": False,
                    "reason": "v2_runtime_error",
                    "message": str(exc),
                },
            }
            payload["interpretation"] = build_interpretation(
                payload, season_phase=season_phase, phenology=phenology
            )
            return payload

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
                    profiles_path=self.profiles_path,
                )
                self._predictors[species_id] = predictor
            return predictor

    def comparator(self, species_id: str) -> MushroomModelComparator:
        with self._lock:
            comparator = self._comparators.get(species_id)
            if comparator is None:
                comparator = MushroomModelComparator(
                    self.predictor(species_id), self.models_dir
                )
                self._comparators[species_id] = comparator
            return comparator

    def execute(
        self,
        request: object,
        *,
        progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_request(request)
        started = monotonic()
        report = progress or (lambda _percent, _phase, _message: None)
        if normalized["view"] == "query" and normalized["area_id"]:
            selected_predictor = self.predictor(normalized["species_id"])
            if normalized["area_id"] not in selected_predictor.areas_with_species_observations():
                normalized["area_id"] = ""
        cache_key: tuple[object, ...] = (
            normalized["view"],
            normalized["species_id"],
            normalized["area_id"],
            normalized["target_date"],
            normalized["filter_mode"],
            normalized["compare_models"],
            normalized["issue_date"],
            tuple(normalized["trained_species_ids"]),
            tuple(
                tuple(sorted(row.items()))
                for row in normalized["multiversion_selection"]
            ),
        )
        with self._lock:
            cached = self._responses.get(cache_key)
            if cached is not None:
                self._responses.move_to_end(cache_key)
                response = copy.deepcopy(cached)
                response["metrics"] = {
                    **dict(response.get("metrics", {})),
                    "backend_seconds": round(monotonic() - started, 4),
                    "response_cache_status": "hit",
                    "loaded_predictor_count": len(self._predictors),
                }
                report(100, "Prediction complete", "Cached results are ready.")
                return response
        report(2, "Preparing predictor", "Validating the prediction request.")
        view = normalized["view"]
        species_ids = normalized["trained_species_ids"]
        selected_species = normalized["species_id"]
        target = date.fromisoformat(normalized["target_date"])
        area_id = normalized["area_id"]
        data: dict[str, Any] = {
            "species": {},
            "model_catalog": self.model_catalog(),
        }
        prepared_weather_cache: dict[tuple[object, ...], Any] = {}
        comparison_cache: dict[str, Any] = {}

        def comparison_for(
            species_id: str,
            current_area: str,
            current_date: date,
        ) -> dict[str, Any]:
            return self.v2_reference_compare(
                species_id=species_id,
                area_id=current_area,
                target_date=current_date,
                issue_date=min(date.today(), current_date),
                prepared_weather_cache=prepared_weather_cache,
                comparison_cache=comparison_cache,
            )

        if view == "recommender":
            total = len(species_ids)
            for index, species_id in enumerate(species_ids):
                report(
                    5 + round(index / max(1, total) * 88),
                    "Evaluating species",
                    f"{index + 1}/{total}: {species_id}",
                )
                predictor = self.predictor(species_id)
                season_phase = predictor.season_phase(target)
                rankings = (
                    []
                    if season_phase == "out_of_season"
                    else [
                        serialize_prediction(row)
                        for row in predictor.rank_areas(target, only_observed=True)
                    ]
                )
                data["species"][species_id] = {
                    "season_phase": season_phase,
                    "areas": [str(row["area_id"]) for row in rankings],
                    "rankings": {target.isoformat(): rankings},
                    "model_comparisons": {
                        row["area_id"]: {
                            target.isoformat(): comparison_for(
                                species_id, row["area_id"], target
                            )
                        }
                        for row in rankings
                    }
                }
        elif view == "week":
            predictor = self.predictor(selected_species)
            areas = predictor.areas_with_species_observations()
            days = [date.today() + timedelta(days=offset) for offset in range(7)]
            predictions: dict[str, dict[str, Any]] = {}
            comparisons: dict[str, dict[str, Any]] = {}
            total = max(1, len(areas) * len(days))
            requests = [
                (current_area, current_date)
                for current_area in areas
                for current_date in days
            ]
            report(10, "Building weekly matrix", f"Evaluating {total} area-days.")
            rows = predictor.predict_many(requests)
            for completed, ((current_area, current_date), row) in enumerate(
                zip(requests, rows, strict=True), start=1
            ):
                predictions.setdefault(current_area, {})[current_date.isoformat()] = (
                    serialize_prediction(row)
                )
                comparisons.setdefault(current_area, {})[current_date.isoformat()] = (
                    comparison_for(selected_species, current_area, current_date)
                )
                report(
                    10 + round(completed / total * 83),
                    "Building weekly matrix",
                    f"{completed}/{total} area-days",
                )
            data["species"][selected_species] = {
                "areas": areas,
                "predictions": predictions,
                "model_comparisons": comparisons,
            }
        elif view == "history":
            report(10, "Loading history", f"Backtesting {selected_species}.")
            predictor = self.predictor(selected_species)
            backtest = predictor.observed_episodes()
            history_comparisons: dict[str, dict[str, Any]] = {}
            for row in backtest:
                history_area = str(row.get("area_id", ""))
                history_date = str(row.get("observed_at", ""))
                if not history_area or not history_date:
                    continue
                history_comparisons.setdefault(history_area, {})[history_date] = (
                    comparison_for(
                        selected_species,
                        history_area,
                        date.fromisoformat(history_date),
                    )
                )
            data["species"][selected_species] = {
                "backtest": backtest,
                "areas": predictor.areas_with_species_observations(),
                "model_comparisons": history_comparisons,
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
                report(88, "Comparing models", f"Evaluating operational models for {area_id}.")
                species_data["model_comparisons"] = {
                    area_id: {
                        row.target_date.isoformat(): comparison_for(
                            selected_species, area_id, row.target_date
                        )
                        for row in week
                    }
                }
                if target.isoformat() not in species_data["model_comparisons"][area_id]:
                    species_data["model_comparisons"][area_id][target.isoformat()] = (
                        comparison_for(selected_species, area_id, target)
                    )
                if normalized["compare_models"] and normalized["multiversion_selection"]:
                    species_data["multiversion_comparison"] = self.multiversion_compare(
                        species_id=selected_species,
                        area_id=area_id,
                        target_date=target,
                        selections=normalized["multiversion_selection"],
                    )
            else:
                report(20, "Ranking areas", f"Evaluating {selected_species}.")
                ranking_rows = [
                    serialize_prediction(row)
                    for row in predictor.rank_areas(target, only_observed=True)
                ]
                species_data["rankings"] = {target.isoformat(): ranking_rows}
                species_data["model_comparisons"] = {
                    row["area_id"]: {
                        target.isoformat(): comparison_for(
                            selected_species, row["area_id"], target
                        )
                    }
                    for row in ranking_rows
                }
            data["species"][selected_species] = species_data

        elapsed = round(monotonic() - started, 4)
        report(100, "Prediction complete", "Results are ready.")
        response = {
            "schema_version": SCHEMA_VERSION,
            "kind": RESPONSE_KIND,
            "runtime_fingerprint": self.runtime_fingerprint,
            "request": normalized,
            "data": data,
            "metrics": {
                "backend_seconds": elapsed,
                "response_cache_status": "miss",
                "loaded_predictor_count": len(self._predictors),
            },
        }
        with self._lock:
            self._responses[cache_key] = copy.deepcopy(response)
            self._responses.move_to_end(cache_key)
            while len(self._responses) > _RESPONSE_CACHE_MAX_ENTRIES:
                self._responses.popitem(last=False)
        return response


class PreparedPredictor:
    """Read-only MushroomMLPredictor-compatible adapter for server rendering."""

    def __init__(self, species_id: str, response: dict[str, Any]) -> None:
        self.species_id = species_id
        self._data = dict(response.get("data", {}).get("species", {}).get(species_id, {}))

    def areas_with_species_observations(self) -> list[str]:
        explicit = [str(value) for value in self._data.get("areas", [])]
        if explicit:
            return explicit
        derived: list[str] = []
        for rows in self._data.get("rankings", {}).values():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                area_id = str(row.get("area_id", ""))
                if area_id and area_id not in derived:
                    derived.append(area_id)
        return derived

    def season_phase(self, _target_date: date) -> str:
        return str(self._data.get("season_phase", "unknown"))

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

    def observed_episodes(self, *_args: object, **_kwargs: object) -> list[dict[str, Any]]:
        return [dict(row) for row in self._data.get("backtest", [])]

    def model_comparison(self, area_id: str, target_date: date) -> dict[str, Any] | None:
        payload = (
            self._data.get("model_comparisons", {})
            .get(area_id, {})
            .get(target_date.isoformat())
        )
        return dict(payload) if isinstance(payload, dict) else None


def validate_response(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PredictorContractError("Predictor response must be an object.")
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("kind") != RESPONSE_KIND:
        raise PredictorContractError("Unsupported predictor response contract.")
    normalize_request(payload.get("request"))
    if not isinstance(payload.get("data"), dict) or not isinstance(payload.get("metrics"), dict):
        raise PredictorContractError("Predictor response payload is incomplete.")
    return dict(payload)
