"""Observed-weather model comparison for the mushroom Predictor."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path
from threading import RLock
from typing import Any

from rainmapper_core import mushroom_observation_context as ctx
from rainmapper_core.mushroom_ml_experiment_trainer import model_filename
from rainmapper_core.mushroom_ml_experiments import (
    FIXED_GAP_7D_V1,
    LAG_EVENT_V1,
    build_fixed_gap_7d_features,
    build_lag_event_features,
)
from rainmapper_core.mushroom_ml_predictor import MushroomMLPredictor, _label
from rainmapper_core.mushroom_prediction_interpretation import build_interpretation


SEVERE_OOD_STANDARD_DEVIATIONS = 6.0


class MushroomModelComparator:
    """Evaluate both observed-weather bundles and build one interpretation."""

    def __init__(self, predictor: MushroomMLPredictor, models_dir: Path) -> None:
        self.predictor = predictor
        self.models_dir = Path(models_dir)
        self._bundles: dict[str, dict[str, Any] | None] = {}
        self._species_profile_cache: dict[str, Any] | None = None
        self._lock = RLock()

    def _bundle(self, feature_set_id: str) -> dict[str, Any] | None:
        with self._lock:
            if feature_set_id in self._bundles:
                return self._bundles[feature_set_id]
            path = self.models_dir / model_filename(
                feature_set_id, self.predictor.species_id
            )
            if not path.is_file():
                self._bundles[feature_set_id] = None
                return None
            import joblib  # noqa: PLC0415

            bundle = joblib.load(path)
            if (
                not isinstance(bundle, dict)
                or bundle.get("kind") != "mushroom_ml_experiment_bundle"
                or bundle.get("feature_set_id") != feature_set_id
            ):
                raise ValueError(f"Invalid shadow model bundle: {path}")
            expected_inputs = {
                "features_sha256": Path(self.predictor._features_artifact_path),
                "known_sites_sha256": Path(self.predictor._known_sites_path),
            }
            for digest_key, source_path in expected_inputs.items():
                expected = bundle.get(digest_key)
                if not isinstance(expected, str) or len(expected) != 64:
                    raise ValueError(f"Shadow model bundle has no input identity: {path}")
                actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
                if actual != expected:
                    raise ValueError(
                        f"Shadow model bundle does not match current {source_path.name}: {path}"
                    )
            self._bundles[feature_set_id] = bundle
            return bundle

    @staticmethod
    def _apply(bundle: dict[str, Any], features: dict[str, float | None]) -> dict[str, Any]:
        import numpy as np  # noqa: PLC0415

        columns = [str(value) for value in bundle.get("feature_cols", [])]
        row = [
            float(features[column]) if features.get(column) is not None else float("nan")
            for column in columns
        ]
        X = np.asarray([row], dtype=float)
        probabilities: dict[str, float] = {}
        for estimator_id, model in dict(bundle.get("models", {})).items():
            probabilities[str(estimator_id)] = round(
                float(model.predict_proba(X)[0][1]), 4
            )
        ensemble = (
            round(sum(probabilities.values()) / len(probabilities), 4)
            if probabilities
            else None
        )
        feature_support = bundle.get("feature_support")
        feature_support = feature_support if isinstance(feature_support, dict) else {}
        out_of_domain: list[dict[str, Any]] = []
        severe_out_of_domain: list[dict[str, Any]] = []
        for column in columns:
            value = features.get(column)
            support = feature_support.get(column)
            if not isinstance(value, (int, float)) or not isinstance(support, dict):
                continue
            minimum = support.get("min")
            maximum = support.get("max")
            mean = support.get("mean")
            std = support.get("std")
            if not isinstance(minimum, (int, float)) or not isinstance(
                maximum, (int, float)
            ):
                continue
            if minimum <= float(value) <= maximum:
                continue
            z_score = None
            if isinstance(mean, (int, float)) and isinstance(std, (int, float)):
                if float(std) > 0:
                    z_score = abs((float(value) - float(mean)) / float(std))
                elif float(value) != float(mean):
                    z_score = float("inf")
            detail = {
                "feature": column,
                "value": round(float(value), 6),
                "training_min": float(minimum),
                "training_max": float(maximum),
                "standard_deviations_from_mean": (
                    round(float(z_score), 3)
                    if z_score is not None and math.isfinite(z_score)
                    else None
                ),
            }
            out_of_domain.append(detail)
            if z_score is not None and z_score >= SEVERE_OOD_STANDARD_DEVIATIONS:
                severe_out_of_domain.append(detail)
        estimator_exclusions: dict[str, dict[str, Any]] = {}
        if severe_out_of_domain:
            estimator_exclusions["logistic_regression_reduced_v1"] = {
                "reason": "severe_feature_extrapolation",
                "features": [row["feature"] for row in severe_out_of_domain],
            }
        return {
            "estimator_probabilities": probabilities,
            "ensemble_probability": ensemble,
            "label": _label(ensemble),
            "missing_feature_count": sum(
                features.get(column) is None for column in columns
            ),
            "feature_count": len(columns),
            "out_of_domain_features": out_of_domain,
            "severe_out_of_domain_features": severe_out_of_domain,
            "estimator_exclusions": estimator_exclusions,
            "features_used": {
                key: value if value is None or math.isfinite(value) else None
                for key, value in features.items()
            },
            "evaluation": dict(bundle.get("evaluation", {})),
            "estimator_availability": dict(
                bundle.get("estimator_availability", {})
            ),
        }

    @staticmethod
    def _historical_evaluation(
        bundle: dict[str, Any],
        *,
        area_id: str,
        target_date: date,
        horizon_days: int,
    ) -> dict[str, Any] | None:
        membership = next(
            (
                dict(row)
                for row in bundle.get("episode_partitions", [])
                if isinstance(row, dict)
                and row.get("area_id") == area_id
                and row.get("target_date") == target_date.isoformat()
            ),
            None,
        )
        if membership is None:
            return None
        held_out = next(
            (
                dict(row)
                for row in bundle.get("held_out_predictions", [])
                if isinstance(row, dict)
                and row.get("area_id") == area_id
                and row.get("target_date") == target_date.isoformat()
                and int(row.get("horizon_days", -1)) == horizon_days
            ),
            None,
        )
        return {
            "known_episode": True,
            "prediction_target": membership.get("prediction_target"),
            "partition": membership.get("partition"),
            "chronological_partition": membership.get(
                "chronological_partition"
            ),
            "out_of_sample": held_out is not None,
            "estimator_probabilities": (
                dict(held_out.get("estimator_probabilities", {}))
                if held_out is not None
                else {}
            ),
        }

    def _species_profile(self) -> dict[str, Any]:
        if self._species_profile_cache is not None:
            return self._species_profile_cache
        profile: dict[str, Any] = {}
        try:
            payload = json.loads(self.predictor._profiles_path.read_text(encoding="utf-8"))
            for row in payload.get("species_profiles", []):
                if isinstance(row, dict) and row.get("species_id") == self.predictor.species_id:
                    profile = dict(row)
                    break
        except (OSError, ValueError, TypeError):
            profile = {}
        self._species_profile_cache = profile
        return profile

    def compare(
        self,
        area_id: str,
        target_date: date,
        *,
        issue_date: date | None = None,
    ) -> dict[str, Any]:
        issue = issue_date or min(date.today(), target_date)
        season_phase = self.predictor.season_phase(target_date)
        payload: dict[str, Any] = {
            "issue_date": issue.isoformat(),
            "target_date": target_date.isoformat(),
            "weather_contract": ctx.weather_contract_metadata(),
            "season_phase": season_phase,
        }
        if season_phase == "out_of_season":
            payload["fixed_gap_7d_v1"] = {"available": False, "reason": "out_of_season"}
            payload["lag_event_v1"] = {"available": False, "reason": "out_of_season"}
            payload["interpretation"] = build_interpretation(
                payload,
                season_phase=season_phase,
                phenology=dict(self._species_profile().get("phenology") or {}),
            )
            return payload

        self.predictor._ensure_micro_area_profiles()
        profile = (self.predictor._area_profiles or {}).get(area_id)
        if profile is None or profile.lat is None or profile.lon is None:
            reason = "missing_area_location"
            payload["fixed_gap_7d_v1"] = {"available": False, "reason": reason}
            payload["lag_event_v1"] = {"available": False, "reason": reason}
            payload["interpretation"] = build_interpretation(
                payload,
                season_phase=season_phase,
                phenology=dict(self._species_profile().get("phenology") or {}),
            )
            return payload
        self.predictor._ensure_weather_stations(target_date, target_date)
        desired_lag_cutoff = issue - timedelta(days=1)
        variants: list[
            tuple[
                str,
                Any,
                int,
                date,
                tuple[ctx.WeatherStation, float | None, int] | None,
            ]
        ] = [
            (
                FIXED_GAP_7D_V1.feature_set_id,
                build_fixed_gap_7d_features,
                7,
                target_date - timedelta(days=7),
                None,
            ),
        ]
        lag_station, lag_distance, lag_coverage = ctx.select_station(
            self.predictor._weather_stations or {},
            profile.lat,
            profile.lon,
            desired_lag_cutoff,
            required_complete_day=desired_lag_cutoff,
        )
        effective_lag_cutoff = (
            ctx.latest_complete_weather_day(lag_station, desired_lag_cutoff)
            if lag_station is not None
            else None
        )
        horizon = (
            (target_date - effective_lag_cutoff).days
            if effective_lag_cutoff is not None
            else None
        )
        if horizon is not None and 1 <= horizon <= 7:
            variants.append(
                (
                    LAG_EVENT_V1.feature_set_id,
                    lambda value: build_lag_event_features(value, horizon),
                    horizon,
                    effective_lag_cutoff,
                    (lag_station, lag_distance, lag_coverage),
                )
            )
        else:
            payload[LAG_EVENT_V1.feature_set_id] = {
                "available": False,
                "reason": (
                    "no_qualified_weather_station"
                    if lag_station is None
                    else "effective_horizon_outside_1_7"
                ),
                "horizon_days": horizon,
            }

        for (
            feature_set_id,
            builder,
            variant_horizon,
            selection_cutoff,
            selected_station,
        ) in variants:
            bundle = self._bundle(feature_set_id)
            if bundle is None:
                payload[feature_set_id] = {
                    "available": False,
                    "reason": "model_not_trained",
                }
                continue
            if selected_station is None:
                station, distance, coverage = ctx.select_station(
                    self.predictor._weather_stations or {},
                    profile.lat,
                    profile.lon,
                    selection_cutoff,
                    required_complete_day=selection_cutoff,
                )
            else:
                station, distance, coverage = selected_station
            if station is None:
                payload[feature_set_id] = {
                    "available": False,
                    "reason": "no_qualified_weather_station_within_15km",
                }
                continue
            records = ctx.records_for_window(
                station, target_date, ctx.DAILY_SERIES_DAYS
            )
            duplicates = ctx._consecutive_duplicate_rain_dates(records)
            episode: dict[str, Any] = {
                "observed_at": target_date.isoformat(),
                "gis_altitude_m": profile.gis_altitude_m,
                **ctx.build_daily_series(station, target_date, duplicates),
            }
            features, metadata = builder(episode)
            prediction = self._apply(bundle, features)
            historical_evaluation = self._historical_evaluation(
                bundle,
                area_id=area_id,
                target_date=target_date,
                horizon_days=variant_horizon,
            )
            interpretation_probabilities = dict(
                prediction.get("estimator_probabilities", {})
            )
            probability_source = "production_fit"
            if historical_evaluation is not None:
                if historical_evaluation.get("out_of_sample"):
                    interpretation_probabilities = dict(
                        historical_evaluation.get("estimator_probabilities", {})
                    )
                    probability_source = "held_out_evaluation"
                else:
                    probability_source = "production_fit_includes_episode"
            prediction["interpretation_estimator_probabilities"] = (
                interpretation_probabilities
            )
            prediction["probability_source"] = probability_source
            if historical_evaluation is not None:
                prediction["historical_evaluation"] = historical_evaluation
            station_audit = ctx.station_selection_audit(
                self.predictor._weather_stations or {},
                profile.lat,
                profile.lon,
                selection_cutoff,
                station,
            )
            payload[feature_set_id] = {
                "available": True,
                "feature_set_id": feature_set_id,
                "cutoff_date": metadata["cutoff_date"],
                "horizon_days": variant_horizon,
                "weather_station_code": station.station_code,
                "weather_station_distance_km": round(distance, 2) if distance is not None else None,
                "weather_coverage_days": coverage,
                "station_selection": station_audit,
                "temporal_validation": bundle.get("temporal_validation"),
                "enough_history": metadata.get("enough_history"),
                **prediction,
            }
        payload["interpretation"] = build_interpretation(
            payload,
            season_phase=season_phase,
            phenology=dict(self._species_profile().get("phenology") or {}),
        )
        return payload
