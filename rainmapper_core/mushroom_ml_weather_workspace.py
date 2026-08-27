"""In-memory weather workspace shared by one operational ML preparation run.

The scientific builders remain independently executable.  The operational
orchestrator activates this workspace while it invokes those builders in the
same Python process, allowing them to share one maximum-range station load,
one IDW series per micro-area, ET0, and default soil-water states.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Iterable, Mapping

from . import mushroom_climatic_water_balance as climate
from . import mushroom_known_sites
from . import mushroom_ml_biology_v3 as biology_v3
from . import mushroom_observation_context as weather_context
from . import mushroom_weather_idw


StationKey = tuple[str, str]
DEFAULT_SOIL_VARIANT_ID = "wv0033_0_30cm"


@dataclass(frozen=True)
class AreaSoilBundle:
    aggregated: dict[str, object]
    daily_fraction_mean: list[float | None]


class OperationalWeatherWorkspace:
    """Maximum-range immutable weather base with exact contract-range views."""

    def __init__(
        self,
        *,
        data_dir: Path,
        known_sites: Path,
        stations_file: Path,
        start_day: date,
        end_day: date,
    ) -> None:
        if end_day < start_day:
            raise ValueError("weather workspace end precedes start")
        self.data_dir = data_dir.resolve()
        self.known_sites = known_sites.resolve()
        self.stations_file = stations_file.resolve()
        self.start_day = start_day
        self.end_day = end_day
        self.days = (end_day - start_day).days + 1
        self.disabled = mushroom_weather_idw.disabled_wunderground_station_keys(
            self.stations_file
        )
        contexts = biology_v3.load_micro_area_contexts(self.known_sites)
        target_points = [(item.lat, item.lon) for item in contexts.values()]
        sites_payload = json.loads(self.known_sites.read_text(encoding="utf-8"))
        for row in sites_payload.get("areas", []):
            if not isinstance(row, dict) or row.get("archived"):
                continue
            representative = row.get("representative_location")
            if isinstance(representative, dict):
                try:
                    target_points.append(
                        (float(representative["lat"]), float(representative["lon"]))
                    )
                    continue
                except (KeyError, TypeError, ValueError):
                    pass
            derived = row.get("derived_context")
            centroid = (
                (derived.get("geometry") or {}).get("centroid")
                if isinstance(derived, dict)
                else None
            )
            if not isinstance(centroid, dict):
                centroid = mushroom_known_sites.derive_geometry_context(
                    row.get("geometry")
                ).get("geometry", {}).get("centroid")
            if isinstance(centroid, dict):
                try:
                    target_points.append((float(centroid["lat"]), float(centroid["lon"])))
                except (KeyError, TypeError, ValueError):
                    pass

        catalog = weather_context.load_stations_catalog(self.data_dir)
        station_filter: set[StationKey] = set()
        for row in catalog.itertuples(index=False):
            source = str(getattr(row, "source", "") or "").strip()
            code = str(getattr(row, "station_code", "") or "").strip()
            lat = weather_context.parse_float(getattr(row, "lat", None))
            lon = weather_context.parse_float(getattr(row, "lon", None))
            if (
                source
                and code
                and lat is not None
                and lon is not None
                and any(
                    weather_context.haversine_km(point_lat, point_lon, lat, lon)
                    <= weather_context.STATION_MAX_DISTANCE_KM
                    for point_lat, point_lon in target_points
                )
            ):
                station_filter.add((source, code))
        loaded = weather_context.load_daily_weather_parquet(
            self.data_dir,
            station_filter=station_filter,
            start_date=self.start_day,
            end_date=self.end_day,
        )
        self.stations = {
            key: station
            for key, station in loaded.items()
            if (str(key[0]).lower(), str(key[1]).upper()) not in self.disabled
        }
        self.duplicate_dates = {
            key: mushroom_weather_idw.suppressed_rain_dates(station)
            for key, station in self.stations.items()
        }
        self._station_views: dict[
            tuple[date, date], dict[StationKey, weather_context.WeatherStation]
        ] = {}
        self._weather_base: dict[str, dict[str, object]] = {}
        self._eto_base: dict[str, list[float | None]] = {}
        self._weather_views: dict[
            tuple[date, date, tuple[str, ...]], dict[str, dict[str, object]]
        ] = {}
        self._soil: dict[tuple[str, str, date], AreaSoilBundle] = {}
        self.series_built = 0
        self.series_reused = 0
        self.view_reused = 0

    def stations_for_view(
        self, start_day: date, end_day: date
    ) -> dict[StationKey, weather_context.WeatherStation]:
        self._validate_range(start_day, end_day)
        key = (start_day, end_day)
        cached = self._station_views.get(key)
        if cached is not None:
            return cached
        view: dict[StationKey, weather_context.WeatherStation] = {}
        for station_key, station in self.stations.items():
            records = {
                day: record
                for day, record in station.records_by_day.items()
                if start_day <= day <= end_day
            }
            if records:
                view[station_key] = replace(station, records_by_day=records)
        self._station_views[key] = view
        return view

    def weather_for_contexts(
        self,
        contexts: Iterable[biology_v3.MicroAreaContext],
        *,
        start_day: date,
        end_day: date,
    ) -> dict[str, dict[str, object]]:
        ordered = tuple(sorted(contexts, key=lambda item: item.micro_area_id))
        cache_key = (start_day, end_day, tuple(item.micro_area_id for item in ordered))
        cached_view = self._weather_views.get(cache_key)
        if cached_view is not None:
            self.view_reused += len(ordered)
            return cached_view
        self._validate_range(start_day, end_day)
        view_stations = self.stations_for_view(start_day, end_day)
        view_duplicates = {
            key: mushroom_weather_idw.suppressed_rain_dates(station)
            for key, station in view_stations.items()
        }
        days = (end_day - start_day).days + 1
        result: dict[str, dict[str, object]] = {}
        for context in ordered:
            base = self._weather_base.get(context.micro_area_id)
            if base is None:
                base = mushroom_weather_idw.build_daily_weather_idw_series(
                    self.stations,
                    target_lat=context.lat,
                    target_lon=context.lon,
                    target_altitude_m=context.altitude_m,
                    end_day=self.end_day,
                    days=self.days,
                    excluded_station_keys=self.disabled,
                    duplicate_dates_by_station=self.duplicate_dates,
                )
                self._weather_base[context.micro_area_id] = base
                axis = weather_context.date_window(self.end_day, self.days)
                self._eto_base[context.micro_area_id] = [
                    climate.hargreaves_reference_evapotranspiration_mm(
                        day, context.lat, low, high
                    )
                    if low is not None and high is not None
                    else None
                    for day, low, high in zip(
                        axis,
                        base["daily_temp_min_idw_c"],
                        base["daily_temp_max_idw_c"],
                        strict=True,
                    )
                ]
                self.series_built += 1
            else:
                self.series_reused += 1
            view = mushroom_weather_idw.slice_daily_weather_idw_series(
                base, end_day=end_day, days=days
            )
            self._adjust_absent_station_counts(
                view,
                context=context,
                view_station_keys=set(view_stations),
            )
            if start_day > self.start_day:
                boundary = mushroom_weather_idw.build_daily_rain_idw_series(
                    view_stations,
                    target_lat=context.lat,
                    target_lon=context.lon,
                    end_day=start_day,
                    days=1,
                    excluded_station_keys=self.disabled,
                    duplicate_dates_by_station=view_duplicates,
                )
                for field, values in boundary.items():
                    target = view.get(field)
                    if field.startswith("daily_rain_") and isinstance(target, list):
                        target[0] = values[0]
                self._refresh_rain_totals(view)
            result[context.micro_area_id] = view
        self._weather_views[cache_key] = result
        return result

    def eto_for_context(
        self, micro_area_id: str, *, start_day: date, end_day: date
    ) -> list[float | None]:
        self._validate_range(start_day, end_day)
        values = self._eto_base.get(micro_area_id)
        if values is None:
            raise KeyError(f"weather base not materialized for {micro_area_id}")
        start_index = (start_day - self.start_day).days
        end_index = (end_day - self.start_day).days + 1
        return values[start_index:end_index]

    def soil_bundle(
        self, variant_id: str, area_id: str, cutoff: date
    ) -> AreaSoilBundle | None:
        return self._soil.get((variant_id, area_id, cutoff))

    def store_soil_bundle(
        self,
        variant_id: str,
        area_id: str,
        cutoff: date,
        bundle: AreaSoilBundle,
    ) -> None:
        self._soil[(variant_id, area_id, cutoff)] = bundle

    def stats(self) -> dict[str, int | str]:
        return {
            "mode": "maximum_range_in_memory",
            "start_date": self.start_day.isoformat(),
            "end_date": self.end_day.isoformat(),
            "loaded_station_count": len(self.stations),
            "series_built": self.series_built,
            "series_reused": self.series_reused,
            "view_reused": self.view_reused,
            "soil_states_cached": len(self._soil),
        }

    def _validate_range(self, start_day: date, end_day: date) -> None:
        if start_day < self.start_day or end_day > self.end_day or end_day < start_day:
            raise ValueError("requested weather view is outside the operational workspace")

    def _adjust_absent_station_counts(
        self,
        series: dict[str, object],
        *,
        context: biology_v3.MicroAreaContext,
        view_station_keys: set[StationKey],
    ) -> None:
        absent_nearby = sum(
            1
            for key, station in self.stations.items()
            if key not in view_station_keys
            and weather_context.haversine_km(
                context.lat, context.lon, station.lat, station.lon
            )
            <= mushroom_weather_idw.RAINFALL_IDW_RADIUS_KM
        )
        if not absent_nearby:
            return
        for field, values in series.items():
            if (
                field.endswith("_excluded_missing_station_count")
                and isinstance(values, list)
            ):
                series[field] = [max(0, int(value) - absent_nearby) for value in values]

    @staticmethod
    def _refresh_rain_totals(series: dict[str, object]) -> None:
        observed = list(series.get("daily_rain_observed") or [])
        suppressed = list(series.get("daily_rain_suppressed_station_count") or [])
        imputed = list(
            series.get("daily_rain_imputed_duplicate_zero_station_count") or []
        )
        series["rain_observed_days"] = sum(bool(value) for value in observed)
        series["rain_missing_days"] = sum(not bool(value) for value in observed)
        series["rain_suppressed_station_days"] = sum(int(value) for value in suppressed)
        series["rain_imputed_duplicate_zero_station_days"] = sum(
            int(value) for value in imputed
        )


_ACTIVE: OperationalWeatherWorkspace | None = None


def activate_operational_workspace(
    *,
    data_dir: Path,
    observations: Path,
    known_sites: Path,
    stations_file: Path,
    lookback_days: int = 365,
    max_horizon_days: int = 7,
) -> OperationalWeatherWorkspace:
    payload = json.loads(observations.read_text(encoding="utf-8"))
    rows = payload.get("observations", []) if isinstance(payload, dict) else []
    observed_days = [
        parsed
        for row in rows if isinstance(row, Mapping)
        if (parsed := weather_context.parse_day(row.get("observed_at"))) is not None
    ]
    if not observed_days:
        raise ValueError("operational weather workspace has no observation dates")
    start_day = min(observed_days) - timedelta(
        days=(lookback_days - 1) + max_horizon_days
    )
    workspace = OperationalWeatherWorkspace(
        data_dir=data_dir,
        known_sites=known_sites,
        stations_file=stations_file,
        start_day=start_day,
        end_day=max(observed_days),
    )
    global _ACTIVE
    _ACTIVE = workspace
    return workspace


def active_workspace(
    *, data_dir: Path, known_sites: Path, stations_file: Path
) -> OperationalWeatherWorkspace | None:
    workspace = _ACTIVE
    if workspace is None:
        return None
    if (
        workspace.data_dir != data_dir.resolve()
        or workspace.known_sites != known_sites.resolve()
        or workspace.stations_file != stations_file.resolve()
    ):
        raise ValueError("active operational weather workspace input identity mismatch")
    return workspace


def clear_active_workspace() -> None:
    global _ACTIVE
    _ACTIVE = None
