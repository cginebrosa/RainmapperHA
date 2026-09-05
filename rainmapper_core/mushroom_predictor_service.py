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

    def model_catalog(
        self,
        *,
        include_installed_artifacts: bool = True,
        comparison_cache: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Describe catalog and every independently installed version."""
        if self.version_registry_path is None or not self.version_registry_path.is_file():
            return {"available": False, "reason": "version_registry_missing", "entries": []}
        try:
            registry = (
                comparison_cache.get("service_registry")
                if comparison_cache is not None
                else None
            )
            if not isinstance(registry, dict):
                registry = mushroom_ml_version_registry.load_registry(
                    self.version_registry_path
                )
                if comparison_cache is not None:
                    comparison_cache["service_registry"] = registry
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
            "entries": entries,
            "runtime_batches": {},
            "installed_artifacts": [],
        }
        if not include_installed_artifacts:
            result["runtime_batch_status"] = "not_requested"
            return result
        try:
            batches = self._installed_runtime_batches(
                registry,
                comparison_cache=comparison_cache,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            result["runtime_batch_status"] = "invalid"
            result["runtime_batch_error"] = str(exc)
            return result
        result["runtime_batch_status"] = "installed" if batches else "not_installed"
        result["runtime_batches"] = {
            version_id: {
                "batch_id": batch["batch_id"],
                "snapshot_id": batch["snapshot_id"],
            }
            for version_id, batch in batches.items()
        }
        artifacts_by_key = {
            mushroom_ml_model_catalog.ModelArtifactRef.from_mapping(
                row["artifact_ref"]
            ).key: {
                "artifact_ref": dict(row["artifact_ref"]),
                "supported_horizons": list(row["supported_horizons"]),
            }
            for batch in batches.values()
            for row in batch["artifacts"]
        }
        result["installed_artifacts"] = list(artifacts_by_key.values())
        return result

    def _installed_runtime_batches(
        self,
        registry: Mapping[str, object],
        *,
        version_ids: set[str] | None = None,
        comparison_cache: dict[str, Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        cached = (
            comparison_cache.get("service_installed_runtime_batches")
            if comparison_cache is not None
            else None
        )
        if not isinstance(cached, dict):
            cached = {}
            if comparison_cache is not None:
                comparison_cache["service_installed_runtime_batches"] = cached
        batches: dict[str, dict[str, Any]] = {}
        for version in registry.get("versions", []):
            if not isinstance(version, Mapping):
                continue
            version_id = str(version.get("version_id") or "")
            if version_ids is not None and version_id not in version_ids:
                continue
            if version.get("installed_generation_id") is None:
                continue
            cached_batch = cached.get(version_id)
            if isinstance(cached_batch, dict):
                batches[version_id] = cached_batch
                continue
            manifest_path = mushroom_ml_version_registry.installed_manifest_path(
                registry, version_id, models_root=self.models_dir
            )
            if manifest_path is None or not manifest_path.is_file():
                raise FileNotFoundError(
                    f"Installed manifest is missing for {version_id}"
                )
            batch = mushroom_ml_model_catalog.validate_batch_manifest(
                registry, json.loads(manifest_path.read_text(encoding="utf-8"))
            )
            cached[version_id] = batch
            batches[version_id] = batch
        return batches

    def species_phenology(self, species_id: str) -> dict[str, Any]:
        """Return the runtime-scoped phenology used by every interpretation."""
        if self.profiles_path is None or not self.profiles_path.is_file():
            return {}
        try:
            profiles = json.loads(self.profiles_path.read_text(encoding="utf-8"))
            profile = next(
                (
                    row
                    for row in profiles.get("species_profiles", [])
                    if isinstance(row, dict) and row.get("species_id") == species_id
                ),
                {},
            )
            phenology = profile.get("phenology") if isinstance(profile, dict) else {}
            return copy.deepcopy(dict(phenology or {}))
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return {}

    def multiversion_compare(
        self,
        *,
        species_id: str,
        area_id: str,
        target_date: date,
        issue_date: date,
        selections: Sequence[Mapping[str, object]],
        prepared_weather_cache: dict[tuple[object, ...], Any] | None = None,
        comparison_cache: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not selections:
            return {"available": False, "reason": "no_models_selected"}
        if self.version_registry_path is None or not self.version_registry_path.is_file():
            return {"available": False, "reason": "runtime_batch_not_installed"}
        try:
            registry = (
                comparison_cache.get("service_registry")
                if comparison_cache is not None
                else None
            )
            if not isinstance(registry, dict):
                registry = mushroom_ml_version_registry.load_registry(
                    self.version_registry_path
                )
                if comparison_cache is not None:
                    comparison_cache["service_registry"] = registry
            selections = mushroom_ml_multiversion_comparison.operational_selections(
                selections,
                target_date=target_date,
                issue_date=issue_date,
            )
            if not selections:
                return {"available": False, "reason": "no_models_for_target_horizon"}
            selected_version_ids = {
                str(row.get("version_id") or "") for row in selections
            }
            batches = self._installed_runtime_batches(
                registry,
                version_ids=selected_version_ids,
                comparison_cache=comparison_cache,
            )
            shared_weather = (
                prepared_weather_cache
                if prepared_weather_cache is not None
                else {}
            )
            version_caches = (
                comparison_cache.setdefault("service_multiversion_caches", {})
                if comparison_cache is not None
                else {}
            )
            members: list[dict[str, Any]] = []
            batch_ids: dict[str, str] = {}
            version_runtime_metrics: dict[str, dict[str, Any]] = {}
            for version_id in dict.fromkeys(
                str(row.get("version_id") or "") for row in selections
            ):
                batch = batches.get(version_id)
                if batch is None:
                    raise FileNotFoundError(
                        f"No installed generation for {version_id}"
                    )
                selected = [
                    row for row in selections if row.get("version_id") == version_id
                ]
                result = mushroom_ml_multiversion_comparison.compare_selection(
                    registry,
                    batch,
                    selected,
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
                    prepared_weather_cache=shared_weather,
                    comparison_cache=version_caches.setdefault(version_id, {}),
                )
                batch_ids[version_id] = str(result["batch_id"])
                members.extend(result["members"])
                version_runtime_metrics[version_id] = dict(
                    result.get("runtime_metrics") or {}
                )
            phenology = self.species_phenology(species_id)
            operational = (
                mushroom_ml_multiversion_comparison.build_selected_operational_comparison(
                    members,
                    season_phase=self.predictor(species_id).season_phase(target_date),
                    phenology=phenology,
                )
            )
            return {
                "available": True,
                "batch_ids": batch_ids,
                "area_id": area_id,
                "target_date": target_date.isoformat(),
                "members": members,
                "operational_comparison": operational,
                "consensus_computed": True,
                "ensemble_computed": False,
                "runtime_metrics": {
                    "versions": version_runtime_metrics,
                    "phase_seconds": {
                        f"{version_id}_{phase}": round(float(value), 6)
                        for version_id, metrics in version_runtime_metrics.items()
                        for phase, value in (metrics.get("phase_seconds") or {}).items()
                        if isinstance(value, (int, float))
                        and not isinstance(value, bool)
                    },
                },
            }
        except (OSError, KeyError, TypeError, ValueError) as exc:
            return {
                "available": False,
                "reason": "multiversion_runtime_error",
                "message": str(exc),
            }

    def prewarm_multiversion_week(
        self,
        *,
        species_id: str,
        area_id: str,
        target_dates: Sequence[date],
        issue_date: date,
        selections: Sequence[Mapping[str, object]],
        prepared_weather_cache: dict[tuple[object, ...], Any],
        comparison_cache: dict[str, Any],
        operational_resolution_index: Mapping[tuple[str, str, int], object] | None = None,
    ) -> int:
        """Batch weekly inference while retaining the normal response assembly."""
        if self.version_registry_path is None or not self.version_registry_path.is_file():
            return 0
        try:
            registry = comparison_cache.get("service_registry")
            if not isinstance(registry, dict):
                registry = mushroom_ml_version_registry.load_registry(
                    self.version_registry_path
                )
                comparison_cache["service_registry"] = registry
            dated = []
            for current_date in target_dates:
                current_selections = (
                    mushroom_ml_multiversion_comparison.retarget_operational_selections(
                        selections,
                        target_date=current_date,
                        issue_date=min(issue_date, current_date),
                    )
                )
                if not current_selections and isinstance(
                    operational_resolution_index, Mapping
                ):
                    prediction_day = (current_date - issue_date).days + 1
                    resolution = operational_resolution_index.get(
                        (species_id, area_id, prediction_day)
                    )
                    if isinstance(resolution, Mapping):
                        current_selections = (
                            mushroom_ml_multiversion_comparison.reliability_candidate_selections(
                                resolution
                            )
                        )
                dated.append((current_date, current_selections))
            version_ids = {
                str(row.get("version_id") or "")
                for _current_date, rows in dated
                for row in rows
            }
            batches = self._installed_runtime_batches(
                registry,
                version_ids=version_ids,
                comparison_cache=comparison_cache,
            )
            version_caches = comparison_cache.setdefault(
                "service_multiversion_caches", {}
            )
            stations_file = self.stations_file_path
            excluded_station_keys = (
                mushroom_weather_idw.disabled_wunderground_station_keys(
                    stations_file
                )
                if stations_file is not None and stations_file.is_file()
                else frozenset()
            )
            predicted = 0
            for version_id in sorted(version_ids):
                batch = batches.get(version_id)
                if batch is None:
                    continue
                selected_dates = [
                    (
                        current_date,
                        [
                            row
                            for row in rows
                            if row.get("version_id") == version_id
                        ],
                    )
                    for current_date, rows in dated
                ]
                predicted += (
                    mushroom_ml_multiversion_comparison.prewarm_selection_predictions(
                        registry,
                        batch,
                        selected_dates,
                        species_id=species_id,
                        area_id=area_id,
                        models_root=self.models_dir,
                        known_sites_path=self.known_sites_path,
                        weather_data_dir=self.weather_data_dir,
                        excluded_station_keys=excluded_station_keys,
                        prepared_weather_cache=prepared_weather_cache,
                        comparison_cache=version_caches.setdefault(version_id, {}),
                    )
                )
            return predicted
        except (OSError, KeyError, TypeError, ValueError):
            return 0

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
        """Resolve every profile in the preferred installed version."""
        predictor = self.predictor(species_id)
        season_phase = predictor.season_phase(target_date)
        unavailable = {
            "available": False,
            "reason": "runtime_batch_not_installed",
        }
        if self.version_registry_path is None or not self.version_registry_path.is_file():
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
            profiles = (
                comparison_cache.get("service_profiles")
                if comparison_cache is not None
                else None
            )
            if not isinstance(profiles, dict):
                profiles = json.loads(self.profiles_path.read_text(encoding="utf-8"))
                if comparison_cache is not None:
                    comparison_cache["service_profiles"] = profiles
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
            registry = (
                comparison_cache.get("service_registry")
                if comparison_cache is not None
                else None
            )
            if not isinstance(registry, dict):
                registry = mushroom_ml_version_registry.load_registry(
                    self.version_registry_path
                )
                if comparison_cache is not None:
                    comparison_cache["service_registry"] = registry
            preferred = registry.get("preferred_version_id")
            batches = self._installed_runtime_batches(
                registry,
                version_ids={str(preferred)} if preferred is not None else set(),
                comparison_cache=comparison_cache,
            )
            manifest = batches.get(str(preferred)) if preferred is not None else None
            if manifest is None:
                raise FileNotFoundError("Preferred ML version is not installed")
            return mushroom_ml_multiversion_comparison.compare_operational_reference(
                registry,
                manifest,
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
        shared_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = monotonic()
        phase_seconds: dict[str, float] = {}
        phase_call_counts: dict[str, int] = {}
        detailed_phase_seconds: dict[str, float] = {}

        def timed(phase: str, operation: Callable[[], Any]) -> Any:
            phase_started = monotonic()
            try:
                return operation()
            finally:
                phase_seconds[phase] = phase_seconds.get(phase, 0.0) + (
                    monotonic() - phase_started
                )
                phase_call_counts[phase] = phase_call_counts.get(phase, 0) + 1

        def collect_runtime_metrics(prefix: str, payload: object) -> None:
            if not isinstance(payload, Mapping):
                return
            metrics = payload.get("runtime_metrics")
            metrics = metrics if isinstance(metrics, Mapping) else {}
            phases = metrics.get("phase_seconds")
            phases = phases if isinstance(phases, Mapping) else {}
            for name, value in phases.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    key = f"{prefix}_{name}"
                    detailed_phase_seconds[key] = (
                        detailed_phase_seconds.get(key, 0.0) + float(value)
                    )

        normalized = timed("request_normalization", lambda: normalize_request(request))
        report = progress or (lambda _percent, _phase, _message: None)
        if normalized["view"] == "query" and normalized["area_id"]:
            selected_predictor = timed(
                "predictor_access",
                lambda: self.predictor(normalized["species_id"]),
            )
            known_areas = timed(
                "prediction_data",
                selected_predictor.areas_with_species_observations,
            )
            if normalized["area_id"] not in known_areas:
                normalized["area_id"] = ""
        cache_species_id = (
            "__all_trained_species__"
            if normalized["view"] == "recommender"
            else normalized["species_id"]
        )
        cache_key: tuple[object, ...] = (
            normalized["view"],
            cache_species_id,
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
        cache_started = monotonic()
        use_response_cache = not bool(
            shared_context is not None
            and shared_context.get("disable_response_cache") is True
        )
        if use_response_cache:
            with self._lock:
                cached = self._responses.get(cache_key)
                if cached is not None:
                    self._responses.move_to_end(cache_key)
                    response = copy.deepcopy(cached)
                else:
                    response = None
        else:
            response = None
        phase_seconds["response_cache_lookup"] = monotonic() - cache_started
        phase_call_counts["response_cache_lookup"] = 1
        if response is not None:
            # A recommender response is global to every trained species. Keep
            # the echoed request truthful when a navigation URL carried a
            # different, semantically irrelevant species selection.
            response["request"] = copy.deepcopy(normalized)
            response["metrics"] = {
                **dict(response.get("metrics", {})),
                "backend_seconds": round(monotonic() - started, 4),
                "response_cache_status": "hit",
                "loaded_predictor_count": len(self._predictors),
                "phase_seconds": {
                    key: round(value, 6) for key, value in phase_seconds.items()
                },
                "phase_call_counts": dict(phase_call_counts),
                "detailed_phase_seconds": {},
            }
            report(100, "Prediction complete", "Cached results are ready.")
            return response
        report(2, "Preparing predictor", "Validating the prediction request.")
        view = normalized["view"]
        species_ids = normalized["trained_species_ids"]
        selected_species = normalized["species_id"]
        target = date.fromisoformat(normalized["target_date"])
        request_issue_date = date.fromisoformat(normalized["issue_date"])
        area_id = normalized["area_id"]
        context = shared_context if shared_context is not None else {}
        prepared_weather_cache = context.setdefault("prepared_weather_cache", {})
        comparison_cache = context.setdefault("comparison_cache", {})
        if (
            not isinstance(prepared_weather_cache, dict)
            or not isinstance(comparison_cache, dict)
        ):
            raise PredictorContractError("Predictor shared context is invalid.")
        data: dict[str, Any] = {
            "species": {},
            "model_catalog": timed(
                "model_catalog",
                lambda: self.model_catalog(
                    include_installed_artifacts=view == "query",
                    comparison_cache=comparison_cache,
                ),
            ),
        }

        def multiversion_comparison_for(
            *,
            species_id: str,
            current_area: str,
            current_date: date,
            selections: Sequence[Mapping[str, object]],
        ) -> dict[str, Any]:
            result = timed(
                "multiversion_model_comparison",
                lambda: self.multiversion_compare(
                    species_id=species_id,
                    area_id=current_area,
                    target_date=current_date,
                    issue_date=min(request_issue_date, current_date),
                    selections=selections,
                    prepared_weather_cache=prepared_weather_cache,
                    comparison_cache=comparison_cache,
                ),
            )
            collect_runtime_metrics("multiversion", result)
            return result

        def selected_comparison_for(
            species_id: str,
            current_area: str,
            current_date: date,
        ) -> dict[str, Any]:
            selections = normalized["multiversion_selection"]
            sealed_resolution = None
            resolution_index = context.get("operational_resolution_index")
            if not selections and isinstance(resolution_index, Mapping):
                prediction_day = (current_date - request_issue_date).days + 1
                candidate_resolution = resolution_index.get(
                    (species_id, current_area, prediction_day)
                )
                if isinstance(candidate_resolution, Mapping):
                    sealed_resolution = candidate_resolution
                    if candidate_resolution.get("selection_status") == "abstain":
                        return {
                            "available": False,
                            "reason": "reliability_selection_abstained",
                            "reliability_selection": copy.deepcopy(
                                candidate_resolution
                            ),
                        }
                    selections = (
                        mushroom_ml_multiversion_comparison.reliability_candidate_selections(
                            candidate_resolution
                        )
                    )
            if not selections:
                raise PredictorContractError(
                    "Predictor requires the installed operational model selection."
                )
            comparison = multiversion_comparison_for(
                species_id=species_id,
                current_area=current_area,
                current_date=current_date,
                selections=(
                    mushroom_ml_multiversion_comparison.retarget_operational_selections(
                        selections,
                        target_date=current_date,
                        issue_date=min(request_issue_date, current_date),
                    )
                ),
            )
            if sealed_resolution is not None:
                members = comparison.get("members")
                members = members if isinstance(members, list) else []
                operational, active_resolution = (
                    mushroom_ml_multiversion_comparison.build_reliability_selected_operational_comparison(
                        members,
                        sealed_resolution,
                        season_phase=self.predictor(species_id).season_phase(
                            current_date
                        ),
                        phenology=self.species_phenology(species_id),
                    )
                )
                operational["reliability_selection"] = copy.deepcopy(
                    active_resolution
                )
                comparison["members"] = (
                    mushroom_ml_multiversion_comparison.reliability_materialized_members(
                        members,
                        active_resolution,
                    )
                )
                comparison["operational_comparison"] = operational
                comparison["reliability_selection"] = copy.deepcopy(
                    active_resolution
                )
            return comparison

        if view == "recommender":
            total = len(species_ids)
            for index, species_id in enumerate(species_ids):
                report(
                    5 + round(index / max(1, total) * 88),
                    "Evaluating species",
                    f"{index + 1}/{total}: {species_id}",
                )
                predictor = timed(
                    "predictor_access", lambda: self.predictor(species_id)
                )
                season_phase = predictor.season_phase(target)
                observed_areas = timed(
                    "prediction_data", predictor.areas_with_species_observations
                )
                selected_comparisons = (
                    {}
                    if season_phase == "out_of_season"
                    else {
                        current_area: {
                            target.isoformat(): selected_comparison_for(
                                species_id, current_area, target
                            )
                        }
                        for current_area in observed_areas
                    }
                )
                data["species"][species_id] = {
                    "season_phase": season_phase,
                    "areas": [str(area_id) for area_id in observed_areas],
                    # Retain the response field for contract compatibility. The
                    # Recommender ranks preferred-version interpretations, not
                    # legacy base-model probabilities.
                    "rankings": {target.isoformat(): []},
                    "model_comparisons": selected_comparisons,
                }
        elif view == "week":
            predictor = timed(
                "predictor_access", lambda: self.predictor(selected_species)
            )
            areas = timed(
                "prediction_data", predictor.areas_with_species_observations
            )
            week_start = request_issue_date
            days = [week_start + timedelta(days=offset) for offset in range(7)]
            predictions: dict[str, dict[str, Any]] = {}
            comparisons: dict[str, dict[str, Any]] = {}
            total = max(1, len(areas) * len(days))
            requests = [
                (current_area, current_date)
                for current_area in areas
                for current_date in days
            ]
            report(10, "Building weekly matrix", f"Evaluating {total} area-days.")
            rows = timed(
                "prediction_data", lambda: predictor.predict_many(requests)
            )
            for completed, ((current_area, current_date), row) in enumerate(
                zip(requests, rows, strict=True), start=1
            ):
                predictions.setdefault(current_area, {})[current_date.isoformat()] = (
                    serialize_prediction(row)
                )
                comparisons.setdefault(current_area, {})[current_date.isoformat()] = (
                    selected_comparison_for(
                        selected_species, current_area, current_date
                    )
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
            predictor = timed(
                "predictor_access", lambda: self.predictor(selected_species)
            )
            backtest = timed(
                "prediction_data", predictor.observed_episodes
            )
            history_comparisons: dict[str, dict[str, Any]] = {}
            for row in backtest:
                history_area = str(row.get("area_id", ""))
                history_date = str(row.get("observed_at", ""))
                if not history_area or not history_date:
                    continue
                history_comparisons.setdefault(history_area, {})[history_date] = (
                    selected_comparison_for(
                        selected_species,
                        history_area,
                        date.fromisoformat(history_date),
                    )
                )
            data["species"][selected_species] = {
                "backtest": backtest,
                "areas": timed(
                    "prediction_data",
                    predictor.areas_with_species_observations,
                ),
                "model_comparisons": history_comparisons,
            }
        else:
            predictor = timed(
                "predictor_access", lambda: self.predictor(selected_species)
            )
            areas = timed(
                "prediction_data", predictor.areas_with_species_observations
            )
            species_data: dict[str, Any] = {"areas": areas}
            if area_id:
                current_week = {
                    request_issue_date + timedelta(days=offset) for offset in range(7)
                }
                week_start = request_issue_date if target in current_week else target
                report(20, "Evaluating area", f"Predicting {area_id}.")
                week = timed(
                    "prediction_data",
                    lambda: predictor.week_window(area_id, week_start),
                )
                species_data["predictions"] = {
                    area_id: {row.target_date.isoformat(): serialize_prediction(row) for row in week}
                }
                if target.isoformat() not in species_data["predictions"][area_id]:
                    row = timed(
                        "prediction_data",
                        lambda: predictor.predict(area_id, target),
                    )
                    species_data["predictions"][area_id][target.isoformat()] = serialize_prediction(row)
                comparison_dates = list(
                    dict.fromkeys(
                        [row.target_date for row in week]
                        + (
                            [target]
                            if target not in {row.target_date for row in week}
                            else []
                        )
                    )
                )
                report(88, "Comparing models", f"Evaluating operational models for {area_id}.")
                timed(
                    "multiversion_inference_prewarm",
                    lambda: self.prewarm_multiversion_week(
                        species_id=selected_species,
                        area_id=area_id,
                        target_dates=comparison_dates,
                        issue_date=request_issue_date,
                        selections=normalized["multiversion_selection"],
                        prepared_weather_cache=prepared_weather_cache,
                        comparison_cache=comparison_cache,
                        operational_resolution_index=(
                            context.get("operational_resolution_index")
                            if isinstance(
                                context.get("operational_resolution_index"), Mapping
                            )
                            else None
                        ),
                    ),
                )
                multiversion_comparisons = {
                    current_date.isoformat(): (
                        selected_comparison_for(
                            selected_species, area_id, current_date
                        )
                        if normalized["multiversion_selection"]
                        or isinstance(
                            context.get("operational_resolution_index"), Mapping
                        )
                        else multiversion_comparison_for(
                            species_id=selected_species,
                            current_area=area_id,
                            current_date=current_date,
                            selections=[],
                        )
                    )
                    for current_date in comparison_dates
                }
                species_data["model_comparisons"] = {
                    area_id: {
                        current_date: dict(payload.get("operational_comparison") or {})
                        for current_date, payload in multiversion_comparisons.items()
                    }
                }
                species_data["multiversion_comparisons"] = multiversion_comparisons
                species_data["multiversion_comparison"] = (
                    multiversion_comparisons[target.isoformat()]
                )
            else:
                report(20, "Ranking areas", f"Evaluating {selected_species}.")
                ranking_rows = timed(
                    "prediction_data",
                    lambda: [
                        serialize_prediction(row)
                        for row in predictor.rank_areas(
                            target, only_observed=True
                        )
                    ],
                )
                species_data["rankings"] = {target.isoformat(): ranking_rows}
                species_data["model_comparisons"] = {
                    row["area_id"]: {
                        target.isoformat(): selected_comparison_for(
                            selected_species, row["area_id"], target
                        )
                    }
                    for row in ranking_rows
                }
            data["species"][selected_species] = species_data

        report(100, "Prediction complete", "Results are ready.")
        assembly_started = monotonic()
        response = {
            "schema_version": SCHEMA_VERSION,
            "kind": RESPONSE_KIND,
            "runtime_fingerprint": self.runtime_fingerprint,
            "request": normalized,
            "data": data,
            "metrics": {
                "backend_seconds": 0.0,
                "response_cache_status": "miss",
                "loaded_predictor_count": len(self._predictors),
            },
        }
        phase_seconds["response_assembly"] = monotonic() - assembly_started
        phase_call_counts["response_assembly"] = 1
        response["metrics"].update(
            {
                "backend_seconds": round(monotonic() - started, 4),
                "phase_seconds": {
                    key: round(value, 6)
                    for key, value in phase_seconds.items()
                },
                "phase_call_counts": dict(phase_call_counts),
                "detailed_phase_seconds": {
                    key: round(value, 6)
                    for key, value in detailed_phase_seconds.items()
                },
            }
        )
        if use_response_cache:
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
