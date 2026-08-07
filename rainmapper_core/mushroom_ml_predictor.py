"""Mushroom fruiting probability predictor using trained ML models.

Loads a trained species model (joblib) and predicts fruiting probability for
any (micro_area, date) pair using historical weather data.

Usage:
    python -m rainmapper_core.mushroom_ml_predictor \\
        --species boletus_aereus \\
        --micro-area guils_la_feixa \\
        --date 2024-10-10

    python -m rainmapper_core.mushroom_ml_predictor \\
        --species boletus_aereus \\
        --rank-date 2024-10-10

The predictor uses the same feature computation logic as training
(mushroom_observation_context). No weather forecast is required: the 30 days
before any near-future date are already in the historical records.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from rainmapper_core import mushroom_observation_context as ctx
from rainmapper_core import mushroom_paths
from rainmapper_core import runtime_diagnostics


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MicroAreaProfile:
    micro_area_id: str
    area_id: str
    lat: float | None
    lon: float | None
    gis_altitude_m: float | None = None
    observed_species: set[str] = field(default_factory=set)


@dataclass
class AreaProfile:
    area_id: str
    lat: float | None       # centroid of micro_areas
    lon: float | None
    gis_altitude_m: float | None = None   # mean of micro_area altitudes
    observed_species: set[str] = field(default_factory=set)


@dataclass
class PredictionResult:
    species_id: str
    area_id: str
    target_date: date
    lr_probability: float | None
    rf_probability: float | None
    ensemble_probability: float | None
    label: str  # 'favorable', 'unfavorable', 'uncertain'
    weather_station_code: str | None
    weather_station_distance_km: float | None
    weather_coverage_days: int | None
    feature_gaps: list[str] = field(default_factory=list)
    features_used: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Label thresholds (not production thresholds — for display only)
# ---------------------------------------------------------------------------
LABEL_FAVORABLE_THRESHOLD = 0.60
LABEL_UNFAVORABLE_THRESHOLD = 0.40


def _label(prob: float | None) -> str:
    if prob is None:
        return "uncertain"
    if prob >= LABEL_FAVORABLE_THRESHOLD:
        return "favorable"
    if prob <= LABEL_UNFAVORABLE_THRESHOLD:
        return "unfavorable"
    return "uncertain"


# ---------------------------------------------------------------------------
# Module-level weather stations cache (shared across all predictor instances)
# Filtered to ~100 stations nearest to known micro-areas (P0 memory fix).
# ---------------------------------------------------------------------------

_shared_weather_stations: dict[tuple[str, str], Any] | None = None
_shared_weather_data_dir: Path | None = None
_shared_weather_parquet_mtime: float | None = None
_shared_weather_station_filter: frozenset[tuple[str, str]] | None = None
_weather_cache_lock = Lock()

_shared_stations_catalog: Any | None = None   # pd.DataFrame
_shared_catalog_data_dir: Path | None = None
_shared_catalog_mtime: float | None = None
_catalog_cache_lock = Lock()

_PARQUET_FILENAME = "weather_daily.parquet"
_CATALOG_FILENAME = "weather_stations_catalog.parquet"

_STATION_FILTER_MAX_KM = 15.0
_STATION_FILTER_TOP_N = 5


def _get_shared_stations_catalog(weather_data_dir: Path) -> Any:
    """Load and cache the stations catalog; reload if the catalog file has changed."""
    global _shared_stations_catalog, _shared_catalog_data_dir, _shared_catalog_mtime
    with _catalog_cache_lock:
        catalog_path = weather_data_dir / _CATALOG_FILENAME
        current_mtime: float | None = None
        try:
            current_mtime = catalog_path.stat().st_mtime if catalog_path.exists() else None
        except OSError:
            pass
        cache_valid = (
            _shared_stations_catalog is not None
            and _shared_catalog_data_dir == weather_data_dir
            and current_mtime is not None
            and current_mtime == _shared_catalog_mtime
        )
        if cache_valid:
            return _shared_stations_catalog
        _shared_stations_catalog = ctx.load_stations_catalog(weather_data_dir)
        _shared_catalog_data_dir = weather_data_dir
        try:
            _shared_catalog_mtime = (
                catalog_path.stat().st_mtime if catalog_path.exists() else None
            )
        except OSError:
            _shared_catalog_mtime = None
        return _shared_stations_catalog


def _compute_station_filter(
    weather_data_dir: Path,
    micro_area_profiles: dict[str, Any],
) -> set[tuple[str, str]]:
    """Return a set of (source, station_code) tuples covering all micro-areas.

    Uses the stations catalog to find up to _STATION_FILTER_TOP_N stations within
    _STATION_FILTER_MAX_KM for each micro-area. An empty result is fail-safe:
    the interactive Predictor must never fall back to loading every station.
    """
    catalog = _get_shared_stations_catalog(weather_data_dir)
    if catalog is None or catalog.empty:
        return set()
    codes: set[tuple[str, str]] = set()
    for profile in micro_area_profiles.values():
        lat = getattr(profile, "lat", None)
        lon = getattr(profile, "lon", None)
        if lat is None or lon is None:
            continue
        for pair in ctx.nearest_station_codes(catalog, lat, lon, _STATION_FILTER_MAX_KM, _STATION_FILTER_TOP_N):
            codes.add(pair)
    return codes


def _get_shared_weather_stations(
    weather_data_dir: Path,
    station_filter: set[tuple[str, str]] | None = None,
) -> dict[tuple[str, str], Any]:
    """Load and cache weather stations; reload automatically if parquet has changed.

    When station_filter is provided, only the relevant row groups and stations
    are materialized instead of the full historical dataset.
    """
    global _shared_weather_stations, _shared_weather_data_dir, _shared_weather_parquet_mtime
    global _shared_weather_station_filter
    filter_key = frozenset(station_filter) if station_filter is not None else None
    with _weather_cache_lock:
        parquet_path = weather_data_dir / _PARQUET_FILENAME
        current_mtime: float | None = None
        try:
            current_mtime = parquet_path.stat().st_mtime if parquet_path.exists() else None
        except OSError:
            pass
        cache_valid = (
            _shared_weather_stations is not None
            and _shared_weather_data_dir == weather_data_dir
            and current_mtime is not None
            and current_mtime == _shared_weather_parquet_mtime
            and filter_key == _shared_weather_station_filter
        )
        if cache_valid:
            return _shared_weather_stations  # type: ignore[return-value]
        parquet_size_mib = (
            round(parquet_path.stat().st_size / (1024 * 1024), 3)
            if parquet_path.exists()
            else None
        )
        monitor = runtime_diagnostics.OperationMonitor(
            "predictor_weather_load",
            details={
                "filter_station_count": len(filter_key or ()),
                "parquet_size_mib": parquet_size_mib,
            },
        )
        try:
            loaded_stations = ctx.load_daily_weather_parquet(
                weather_data_dir, station_filter=station_filter
            )
        except Exception as exc:
            monitor.finish(
                "error",
                {"error_type": type(exc).__name__},
            )
            raise
        _shared_weather_stations = loaded_stations
        _shared_weather_data_dir = weather_data_dir
        _shared_weather_parquet_mtime = current_mtime
        _shared_weather_station_filter = filter_key
        loaded_records = sum(
            len(station.records_by_day)
            for station in loaded_stations.values()
            if hasattr(station, "records_by_day")
        )
        monitor.finish(
            "ok",
            {
                "loaded_station_count": len(loaded_stations),
                "loaded_record_count": loaded_records,
            },
        )
        if monitor.enabled:
            runtime_diagnostics.schedule_snapshot(
                "predictor_weather_load",
                monitor.operation_id,
                "retained_60s",
                60,
            )
            runtime_diagnostics.schedule_snapshot(
                "predictor_weather_load",
                monitor.operation_id,
                "retained_600s",
                600,
            )
        return _shared_weather_stations


def invalidate_weather_stations_cache() -> None:
    """Invalidate the shared weather stations cache (call after data update)."""
    global _shared_weather_stations, _shared_weather_data_dir, _shared_weather_parquet_mtime
    global _shared_weather_station_filter
    global _shared_stations_catalog, _shared_catalog_data_dir, _shared_catalog_mtime
    with _catalog_cache_lock, _weather_cache_lock:
        _shared_weather_stations = None
        _shared_weather_data_dir = None
        _shared_weather_parquet_mtime = None
        _shared_weather_station_filter = None
        _shared_stations_catalog = None
        _shared_catalog_data_dir = None
        _shared_catalog_mtime = None


# ---------------------------------------------------------------------------
# Predictor
# ---------------------------------------------------------------------------

class MushroomMLPredictor:
    """Load a trained species model and answer prediction queries.

    Parameters
    ----------
    species_id:
        Identifier used when loading the joblib artifact.
    models_dir:
        Directory containing mushroom_ml_v0_{species_id}.joblib files.
        Defaults to mushroom_paths.mushroom_ml_models_dir().
    weather_data_dir:
        Directory containing Rainmapper weather CSVs.
        Defaults to mushroom_paths.weather_data_dir().
    features_artifact_path:
        Path to mushroom_observation_features_v0.json.
        Used to build the static altitude lookup for each micro_area.
        Defaults to mushroom_paths.mushroom_observation_features_json_path().
    known_sites_path:
        Path to mushroom_known_sites.json.
        Used for micro_area lat/lon and altitude.
        Defaults to mushroom_paths.mushroom_known_sites_path().
    """

    def __init__(
        self,
        species_id: str,
        models_dir: Path | None = None,
        weather_data_dir: Path | None = None,
        features_artifact_path: Path | None = None,
        known_sites_path: Path | None = None,
    ) -> None:
        self.species_id = species_id
        self._models_dir = models_dir or mushroom_paths.mushroom_ml_models_dir()
        self._weather_data_dir = weather_data_dir or mushroom_paths.weather_data_dir()
        self._features_artifact_path = (
            features_artifact_path or mushroom_paths.mushroom_observation_features_json_path()
        )
        self._known_sites_path = known_sites_path or mushroom_paths.mushroom_known_sites_path()

        self._model_bundle: dict[str, Any] | None = None
        self._weather_stations: dict[tuple[str, str], Any] | None = None
        self._weather_station_filter: set[tuple[str, str]] | None = None
        self._weather_station_filter_catalog_mtime: float | None = None
        self._micro_area_profiles: dict[str, MicroAreaProfile] | None = None
        self._area_profiles: dict[str, AreaProfile] | None = None

    # ------------------------------------------------------------------
    # Lazy loaders
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        if self._model_bundle is not None:
            return
        try:
            import joblib  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "joblib not installed. Run: pip install scikit-learn"
            ) from exc
        path = self._models_dir / f"mushroom_ml_v0_{self.species_id}.joblib"
        if not path.exists():
            raise FileNotFoundError(
                f"Model not found: {path}\n"
                f"Run: python -m rainmapper_core.mushroom_ml_trainer --species {self.species_id}"
            )
        self._model_bundle = joblib.load(path)

    def _ensure_weather_stations(self) -> None:
        if not self._weather_data_dir.exists():
            self._weather_stations = {}
            return
        self._ensure_micro_area_profiles()
        _get_shared_stations_catalog(self._weather_data_dir)
        catalog_mtime = _shared_catalog_mtime
        if (
            self._weather_station_filter is None
            or catalog_mtime != self._weather_station_filter_catalog_mtime
        ):
            self._weather_station_filter = _compute_station_filter(
                self._weather_data_dir, self._micro_area_profiles or {}
            )
            self._weather_station_filter_catalog_mtime = _shared_catalog_mtime
        self._weather_stations = _get_shared_weather_stations(
            self._weather_data_dir,
            station_filter=self._weather_station_filter,
        )

    def _ensure_micro_area_profiles(self) -> None:
        if self._micro_area_profiles is not None:
            return
        self._micro_area_profiles = {}
        self._load_profiles_from_known_sites()
        self._enrich_altitude_from_feature_artifact()
        self._build_area_profiles()

    def _build_area_profiles(self) -> None:
        """Aggregate micro_area profiles into area-level profiles."""
        from collections import defaultdict  # noqa: PLC0415

        area_lats: dict[str, list[float]] = defaultdict(list)
        area_lons: dict[str, list[float]] = defaultdict(list)
        area_alts: dict[str, list[float]] = defaultdict(list)
        area_species: dict[str, set[str]] = defaultdict(set)

        for ma in (self._micro_area_profiles or {}).values():
            if not ma.area_id:
                continue
            if ma.lat is not None:
                area_lats[ma.area_id].append(ma.lat)
            if ma.lon is not None:
                area_lons[ma.area_id].append(ma.lon)
            if ma.gis_altitude_m is not None:
                area_alts[ma.area_id].append(ma.gis_altitude_m)
            area_species[ma.area_id].update(ma.observed_species)

        self._area_profiles = {
            area_id: AreaProfile(
                area_id=area_id,
                lat=sum(area_lats[area_id]) / len(area_lats[area_id]) if area_lats[area_id] else None,
                lon=sum(area_lons[area_id]) / len(area_lons[area_id]) if area_lons[area_id] else None,
                gis_altitude_m=sum(area_alts[area_id]) / len(area_alts[area_id]) if area_alts[area_id] else None,
                observed_species=area_species[area_id],
            )
            for area_id in set(area_lats) | set(area_lons) | set(area_alts) | set(area_species)
        }

    def _load_profiles_from_known_sites(self) -> None:
        if not self._known_sites_path.exists():
            return
        payload = json.loads(self._known_sites_path.read_text(encoding="utf-8"))
        for ma in payload.get("micro_areas", []):
            ma_id = ma.get("micro_area_id")
            if not ma_id:
                continue
            rep = ma.get("representative_location") or {}
            lat = rep.get("lat")
            lon = rep.get("lon")
            # DEM altitude from derived_context
            alt_m = None
            dc = ma.get("derived_context") or {}
            gis_dem = dc.get("gis_dem") or {}
            alt_m = gis_dem.get("altitude_mean_m")
            self._micro_area_profiles[ma_id] = MicroAreaProfile(
                micro_area_id=ma_id,
                area_id=ma.get("area_id", ""),
                lat=float(lat) if lat is not None else None,
                lon=float(lon) if lon is not None else None,
                gis_altitude_m=float(alt_m) if alt_m is not None else None,
            )

    def _enrich_altitude_from_feature_artifact(self) -> None:
        """Fill missing altitudes and observed_species from the feature artifact."""
        if not self._features_artifact_path.exists():
            return
        payload = json.loads(self._features_artifact_path.read_text(encoding="utf-8"))
        rows = payload.get("rows", [])
        for r in rows:
            ma_id = r.get("micro_area_id")
            if not ma_id:
                continue
            species = r.get("species_id")
            alt = r.get("gis_altitude_m")
            if ma_id not in self._micro_area_profiles:
                lat = r.get("latitude")
                lon = r.get("longitude")
                self._micro_area_profiles[ma_id] = MicroAreaProfile(
                    micro_area_id=ma_id,
                    area_id="",
                    lat=float(lat) if lat is not None else None,
                    lon=float(lon) if lon is not None else None,
                    gis_altitude_m=float(alt) if alt is not None else None,
                )
            else:
                if alt is not None and self._micro_area_profiles[ma_id].gis_altitude_m is None:
                    self._micro_area_profiles[ma_id].gis_altitude_m = float(alt)
            # Only mark a species as "observed" for rows that were actually
            # eligible for training — review/pending obs don't count.
            eligible = (
                species
                and r.get("validation_status") == "valid"
                and r.get("calibration_use") == "include"
                and r.get("prediction_target") in ("favorable", "unfavorable")
            )
            if eligible:
                self._micro_area_profiles[ma_id].observed_species.add(species)

    def micro_areas_with_species_observations(self) -> list[str]:
        """Return micro_area_ids where this species has been observed at least once."""
        self._ensure_micro_area_profiles()
        return [
            ma_id
            for ma_id, profile in (self._micro_area_profiles or {}).items()
            if self.species_id in profile.observed_species
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_feature_row(
        self,
        target_date: date,
        profile: AreaProfile,
    ) -> tuple[list[float], list[str], str | None, float | None, int | None]:
        """Return (feature_values, gaps, station_code, station_dist_km, coverage_days)."""
        from rainmapper_core.mushroom_ml_trainer import FEATURE_COLS  # noqa: PLC0415

        station: Any | None = None
        station_dist: float | None = None
        coverage_days: int | None = None
        gaps: list[str] = []
        weather_row: dict[str, Any] = {}

        if profile.lat is not None and profile.lon is not None:
            station, station_dist, coverage_days = ctx.select_station(
                self._weather_stations or {},
                profile.lat,
                profile.lon,
                target_date,
            )
            if station is not None:
                records = ctx.records_for_window(
                    station, target_date, ctx.DAILY_SERIES_DAYS
                )
                duplicate_dates = ctx._consecutive_duplicate_rain_dates(records)
                w_values, w_gaps = ctx.build_weather_values(
                    station, target_date, duplicate_dates
                )
                derived = ctx.build_derived_features(
                    station, target_date, duplicate_dates
                )
                weather_row.update(w_values)
                weather_row.update(derived)
                gaps.extend(w_gaps)
            else:
                gaps.append("no_weather_station_with_90d_coverage")
        else:
            gaps.append("missing_area_location")

        feature_values: list[float] = []
        for col in FEATURE_COLS:
            if col == "gis_altitude_m":
                feature_values.append(
                    profile.gis_altitude_m if profile.gis_altitude_m is not None else float("nan")
                )
            elif col == "month":
                feature_values.append(float(target_date.month))
            else:
                val = weather_row.get(col)
                feature_values.append(float(val) if val is not None else float("nan"))

        station_code = station.station_code if station else None
        return feature_values, gaps, station_code, station_dist, coverage_days

    def _apply_model(
        self, feature_values: list[float]
    ) -> tuple[float | None, float | None]:
        """Return (lr_prob, rf_prob)."""
        import numpy as np  # noqa: PLC0415

        bundle = self._model_bundle
        X = np.array([feature_values], dtype=float)
        X_imp = bundle["imputer"].transform(X)
        X_scaled = bundle["scaler"].transform(X_imp)

        lr_prob: float | None = None
        rf_prob: float | None = None
        if "lr" in bundle:
            lr_prob = float(bundle["lr"].predict_proba(X_scaled)[0][1])
        if "rf" in bundle:
            rf_prob = float(bundle["rf"].predict_proba(X_scaled)[0][1])
        return lr_prob, rf_prob

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        area_id: str,
        target_date: date,
    ) -> PredictionResult:
        """Predict fruiting probability for a (area, date) pair."""
        from rainmapper_core.mushroom_ml_trainer import FEATURE_COLS  # noqa: PLC0415

        self._ensure_model()
        self._ensure_weather_stations()
        self._ensure_micro_area_profiles()

        profile = (self._area_profiles or {}).get(area_id)
        if profile is None:
            profile = AreaProfile(area_id=area_id, lat=None, lon=None)

        feature_values, gaps, station_code, station_dist, coverage_days = (
            self._build_feature_row(target_date, profile)
        )

        lr_prob, rf_prob = self._apply_model(feature_values)

        probs = [p for p in (lr_prob, rf_prob) if p is not None]
        ensemble_prob = round(sum(probs) / len(probs), 4) if probs else None
        features_used = {
            column: value if math.isfinite(value) else None
            for column, value in zip(FEATURE_COLS, feature_values, strict=True)
        }

        return PredictionResult(
            species_id=self.species_id,
            area_id=area_id,
            target_date=target_date,
            lr_probability=round(lr_prob, 4) if lr_prob is not None else None,
            rf_probability=round(rf_prob, 4) if rf_prob is not None else None,
            ensemble_probability=ensemble_prob,
            label=_label(ensemble_prob),
            weather_station_code=station_code,
            weather_station_distance_km=round(station_dist, 2) if station_dist is not None else None,
            weather_coverage_days=coverage_days,
            feature_gaps=gaps,
            features_used=features_used,
        )

    def areas_with_species_observations(self) -> list[str]:
        """Return area_ids where this species has been observed (eligible obs only)."""
        self._ensure_micro_area_profiles()
        return [
            area_id
            for area_id, profile in (self._area_profiles or {}).items()
            if self.species_id in profile.observed_species
        ]

    def rank_areas(
        self,
        target_date: date,
        area_ids: list[str] | None = None,
        only_observed: bool = True,
    ) -> list[PredictionResult]:
        """Predict for areas and rank by probability.

        Parameters
        ----------
        only_observed:
            If True (default), restrict to areas where this species has been
            observed with eligible data. Prevents ecologically impossible results.
        """
        self._ensure_micro_area_profiles()
        if area_ids is not None:
            ids = area_ids
        elif only_observed:
            ids = self.areas_with_species_observations()
        else:
            ids = list((self._area_profiles or {}).keys())
        results = [self.predict(area_id, target_date) for area_id in ids]
        return sorted(
            results,
            key=lambda r: r.ensemble_probability if r.ensemble_probability is not None else -1,
            reverse=True,
        )

    def week_window(
        self,
        area_id: str,
        start_date: date,
    ) -> list[PredictionResult]:
        """Predict for each day in a 7-day window starting at start_date."""
        return [
            self.predict(area_id, start_date + timedelta(days=i))
            for i in range(7)
        ]

    def backtest(
        self,
        features_artifact_path: Path | None = None,
        known_sites_path: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Predict on area-level episodes and compare with known labels."""
        from rainmapper_core.mushroom_ml_trainer import (  # noqa: PLC0415
            aggregate_to_area_episodes,
            filter_eligible,
            load_micro_area_to_area,
        )

        self._ensure_model()
        self._ensure_weather_stations()
        self._ensure_micro_area_profiles()

        path = features_artifact_path or self._features_artifact_path
        ks_path = known_sites_path or self._known_sites_path
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("rows", [])

        eligible = filter_eligible(rows, self.species_id)
        ma_to_area = load_micro_area_to_area(ks_path)
        episodes = aggregate_to_area_episodes(eligible, ma_to_area)

        results = []
        for ep in episodes:
            area_id = ep.get("area_id", "")
            obs_date_str = ep.get("observed_at", "")
            try:
                obs_date = date.fromisoformat(obs_date_str)
            except ValueError:
                continue
            pred = self.predict(area_id, obs_date)
            actual = ep.get("prediction_target")
            results.append(
                {
                    "area_id": area_id,
                    "observed_at": obs_date_str,
                    "n_micro_areas": ep.get("n_micro_areas_in_episode", 1),
                    "actual": actual,
                    "predicted_label": _label(pred.ensemble_probability),
                    "lr_probability": pred.lr_probability,
                    "rf_probability": pred.rf_probability,
                    "ensemble_probability": pred.ensemble_probability,
                    "correct": _label(pred.ensemble_probability) == actual if pred.ensemble_probability is not None else None,
                }
            )
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predict mushroom fruiting probability using trained ML models."
    )
    parser.add_argument("--species", required=True, metavar="SPECIES_ID")
    parser.add_argument("--area", metavar="AREA_ID")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="Target date for prediction")
    parser.add_argument(
        "--rank-date",
        metavar="YYYY-MM-DD",
        help="Rank all areas for this date",
    )
    parser.add_argument(
        "--week",
        metavar="YYYY-MM-DD",
        help="Show 7-day window starting at this date (requires --area)",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest on area-level episodes",
    )
    args = parser.parse_args()

    predictor = MushroomMLPredictor(args.species)

    if args.backtest:
        results = predictor.backtest()
        correct = [r for r in results if r["correct"] is True]
        incorrect = [r for r in results if r["correct"] is False]
        n = len(results)
        print(f"\nBacktest: {args.species}  ({n} area episodes)")
        print(f"  Correct:   {len(correct)} / {n}  ({100*len(correct)//n if n else 0}%)")
        print(f"  Incorrect: {len(incorrect)} / {n}")
        print()
        for r in results:
            mark = "OK" if r["correct"] else "XX"
            n_ma = r.get("n_micro_areas", 1)
            print(
                f"  {mark}  {r['observed_at']}  {r['area_id']:<28}"
                f"  actual={r['actual']:11s}  ensemble={r['ensemble_probability']}  ({n_ma} micro_areas)"
            )
        return

    if args.rank_date:
        try:
            target_date = date.fromisoformat(args.rank_date)
        except ValueError:
            sys.exit(f"Invalid date: {args.rank_date}")
        print(f"\nRanking areas for {args.species} on {target_date}")
        print(f"{'area':<30}  ensemble   LR     RF   label  coverage")
        print("-" * 75)
        for r in predictor.rank_areas(target_date):
            print(
                f"  {r.area_id:<28}"
                f"  {r.ensemble_probability or 'N/A':>8}  {r.lr_probability or 'N/A':>6}"
                f"  {r.rf_probability or 'N/A':>6}  {r.label}  ({r.weather_coverage_days or 0}d)"
            )
        return

    if args.week:
        if not args.area:
            sys.exit("--week requires --area")
        try:
            start_date = date.fromisoformat(args.week)
        except ValueError:
            sys.exit(f"Invalid date: {args.week}")
        print(f"\n7-day forecast: {args.species} @ {args.area}")
        print(f"{'date':<12}  ensemble   LR     RF   label  coverage")
        print("-" * 60)
        for r in predictor.week_window(args.area, start_date):
            print(
                f"  {r.target_date}  {r.ensemble_probability or 'N/A':>8}"
                f"  {r.lr_probability or 'N/A':>6}  {r.rf_probability or 'N/A':>6}"
                f"  {r.label}  ({r.weather_coverage_days or 0}d)"
            )
        return

    if args.area and args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            sys.exit(f"Invalid date: {args.date}")
        r = predictor.predict(args.area, target_date)
        print(f"\nPrediction: {r.species_id} @ {r.area_id} on {r.target_date}")
        print(f"  Ensemble probability : {r.ensemble_probability}")
        print(f"  LR probability       : {r.lr_probability}")
        print(f"  RF probability       : {r.rf_probability}")
        print(f"  Label                : {r.label}")
        print(f"  Weather station      : {r.weather_station_code} ({r.weather_station_distance_km} km)")
        print(f"  Coverage (90d)       : {r.weather_coverage_days} days")
        if r.feature_gaps:
            print(f"  Gaps                 : {', '.join(r.feature_gaps[:5])}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
