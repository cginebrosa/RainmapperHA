"""In-memory weather workspace shared by one operational ML preparation run.

The scientific builders remain independently executable.  The operational
orchestrator activates this workspace while it invokes those builders in the
same Python process, allowing them to share one maximum-range station load,
one IDW series per micro-area, ET0, and default soil-water states.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from collections import OrderedDict
from collections.abc import Mapping as MappingABC
from bisect import bisect_left, bisect_right
from itertools import islice
from datetime import date, timedelta
import json
import hashlib
from pathlib import Path
from typing import Iterable, Mapping

from .mushroom_water_physics import point_reference_et
from . import mushroom_known_sites
from . import mushroom_ml_biology_v3 as biology_v3
from . import mushroom_observation_context as weather_context
from . import mushroom_weather_idw


StationKey = tuple[str, str]
DEFAULT_SOIL_VARIANT_ID = "wv0033_0_30cm"


class _LastWindow(dict):
    """One range view; immutable bases are shared across all builder phases."""
    def __setitem__(self, key, value):
        self.clear()
        super().__setitem__(key, value)


class _RecordRange(MappingABC):
    """Read-only date view over station records; no copy per area/window."""
    __slots__ = ('records', 'axis', 'left', 'right', 'start', 'end')

    def __init__(self, records, axis, start, end):
        self.records, self.axis, self.start, self.end = records, axis, start, end
        self.left, self.right = bisect_left(axis, start), bisect_right(axis, end)

    def __len__(self):
        return self.right - self.left

    def __iter__(self):
        return islice(self.axis, self.left, self.right)

    def __getitem__(self, day):
        if not self.start <= day <= self.end:
            raise KeyError(day)
        return self.records[day]


class AreaWeatherWindows(MappingABC):
    """Lazily aggregate the exact V3 window; do not retain one per observation."""
    def __init__(self, requested, contexts_by_area, series, *, max_entries=16, days=None):
        self.days = weather_context.DAILY_SERIES_DAYS if days is None else days
        if type(self.days) is not int or not 0 < self.days <= 365:
            raise ValueError("area_weather_window_limit")
        available = {area for area, contexts in contexts_by_area.items()
                     if any(c.micro_area_id in series for c in contexts)}
        self.keys_by_day = {(area, day.isoformat()) for area, day in requested if area in available}
        self.contexts, self.series, self.limit = contexts_by_area, series, max_entries
        self.memo = OrderedDict()
        from rainmapper_core.mushroom_map_competing import PointCache
        self.area_series = PointCache(max_bytes=16*1024*1024,max_entries=32)

    def __len__(self):
        return len(self.keys_by_day)

    def __iter__(self):
        return iter(sorted(self.keys_by_day))

    def _from_microareas(self, key):
        if key not in self.keys_by_day:
            raise KeyError(key)
        if key in self.memo:
            self.memo.move_to_end(key)
            return self.memo[key]
        area, day = key
        micro = {context.micro_area_id: mushroom_weather_idw.slice_daily_weather_idw_series(
                     self.series[context.micro_area_id], end_day=date.fromisoformat(day),
                     days=self.days)
                 for context in sorted(self.contexts.get(area, ()), key=lambda c:c.micro_area_id)
                 if context.micro_area_id in self.series}
        if not micro:
            raise KeyError(key)
        value = biology_v3.aggregate_area_rainfall_series(micro)
        self.memo[key] = value
        while len(self.memo) > self.limit:
            self.memo.popitem(last=False)
        return value

    def __getitem__(self, key):
        if key not in self.keys_by_day:
            raise KeyError(key)
        if key in self.memo:
            self.memo.move_to_end(key)
            return self.memo[key]
        area, day = key
        whole = self.area_series.get(area)
        if whole is None:
            micro = {c.micro_area_id: self.series[c.micro_area_id]
                     for c in self.contexts[area] if c.micro_area_id in self.series}
            axes = [v.get('daily_dates', []) for v in micro.values()]
            # Different base axes keep the original slice-before-aggregation path.
            if (not axes or not axes[0] or len(axes[0])*(2048+512*len(micro)) > 16*1024*1024
                    or any(axis != axes[0] for axis in axes[1:])):
                return self._from_microareas(key)
            whole = biology_v3.aggregate_area_rainfall_series(micro)
            self.area_series.put(area, whole)
        axis = whole['daily_dates']
        end = (date.fromisoformat(day) - date.fromisoformat(axis[0])).days + 1
        start = end - self.days
        if start < 0 or end > len(axis):
            return self._from_microareas(key)
        value = {k: (v[start:end] if isinstance(v, list) else v) for k, v in whole.items()}
        rain = value['daily_rain_idw_mean_mm']
        available, configured = value['daily_microareas_available'], value['configured_microareas']
        value.update(rain_observed_days=sum(v is not None for v in rain),
                     rain_missing_days=sum(v is None for v in rain),
                     full_microarea_coverage_days=sum(v == configured for v in available),
                     partial_microarea_coverage_days=sum(0 < v < configured for v in available))
        for metric, unit in (('temp_min', 'c'), ('temp_max', 'c'),
                             ('humidity_min', 'pct'), ('humidity_max', 'pct')):
            values = value[f'daily_{metric}_idw_mean_{unit}']
            value[f'{metric}_observed_days'] = sum(v is not None for v in values)
            value[f'{metric}_missing_days'] = sum(v is None for v in values)
        self.memo[key] = value
        while len(self.memo) > self.limit:
            self.memo.popitem(last=False)
        return value


class AreaPhysicalWindows:
    """Share area ET0/balance means across overlapping raw feature windows."""
    def __init__(self, contexts, weather, eto):
        from rainmapper_core.mushroom_map_competing import PointCache
        self.contexts, self.weather, self.eto = contexts, weather, eto
        self.memo = PointCache(max_bytes=8*1024*1024, max_entries=32)

    def get(self, area, cutoff, *, days=365):
        import statistics
        if type(days) is not int or not 0 < days <= 365:
            raise ValueError('area_weather_window_limit')
        whole = self.memo.get(area)
        if whole is None:
            contexts = [c for c in self.contexts.get(area, []) if c.micro_area_id in self.weather]
            axes = [self.weather[c.micro_area_id]['daily_dates'] for c in contexts]
            if (not axes or not axes[0] or len(axes[0])*256 > 8*1024*1024
                    or any(axis != axes[0] for axis in axes[1:])):
                return None
            n = len(axes[0])
            if n*max(1, len(contexts))*32 > 8*1024*1024:
                return None
            eto = [self.eto[c.micro_area_id] for c in contexts]
            rain = [self.weather[c.micro_area_id]['daily_rain_idw_mm'] for c in contexts]
            if any(len(row) != n for row in (*eto, *rain)):
                return None
            balance = [[float(p)-float(e) if p is not None and e is not None else None
                        for p, e in zip(row, et)] for row, et in zip(rain, eto)]
            def mean(rows):
                result = []
                for i in range(n):
                    values = [float(row[i]) for row in rows if row[i] is not None]
                    result.append(statistics.fmean(values) if values else None)
                return result
            whole = axes[0][0], mean(eto), mean(balance)
            self.memo.put(area, whole)
        end = (cutoff - date.fromisoformat(whole[0])).days + 1
        start = end - days
        if start < 0 or end > len(whole[1]):
            return None
        return whole[1][start:end], whole[2][start:end]


@dataclass(frozen=True)
class AreaSoilBundle:
    aggregated: dict[str, object]
    daily_fraction_mean: list[float | None]
    input_signature: str | None = None


def soil_inputs_signature(rain, eto):
    """Seal actual physical inputs, including the first day's rain policy."""
    value = [(key, rain.get(key), eto.get(key)) for key in sorted(set(rain) | set(eto))]
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


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
        compact_series: bool = False,
        area_ranges: Mapping[str, tuple[date, date]] | None = None,
    ) -> None:
        if end_day < start_day:
            raise ValueError("weather workspace end precedes start")
        self.data_dir = data_dir.resolve()
        self.known_sites = known_sites.resolve()
        self.stations_file = stations_file.resolve()
        self.start_day = start_day
        self.end_day = end_day
        self.days = (end_day - start_day).days + 1
        self.area_ranges = dict(area_ranges or {})
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
            **({'stream_records': True} if compact_series else {}),
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
        self._series_index = None
        if compact_series:
            from .mushroom_weather_series import WeatherSeries
            self._series_index = WeatherSeries(
                self.stations, self.start_day, self.end_day, self.duplicate_dates)
        self._station_axes = ({key: tuple(sorted(station.records_by_day))
                               for key, station in self.stations.items()}
                              if compact_series else None)
        self._station_views: dict[
            tuple[date, date], dict[StationKey, weather_context.WeatherStation]
        ] = {}
        self._weather_base: dict[str, dict[str, object]] = {}
        self._eto_base: dict[str, list[float | None]] = {}
        self._weather_views: dict[
            tuple[date, date, tuple[str, ...]], dict[str, dict[str, object]]
        ] = {}
        if compact_series:
            self._station_views = _LastWindow()
            self._weather_views = _LastWindow()
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
        axes = getattr(self, '_station_axes', None)
        for station_key, station in self.stations.items():
            records = _RecordRange(station.records_by_day, axes[station_key], start_day, end_day) if axes is not None else {
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
        days = (end_day - start_day).days + 1
        result: dict[str, dict[str, object]] = {}
        for context in ordered:
            base = self._weather_base.get(context.micro_area_id)
            if base is None:
                index = getattr(self, '_series_index', None)
                first, last = self.context_range(context, self.start_day, self.end_day)
                base = index.build(context, self.disabled, start=first, end=last) if index is not None else mushroom_weather_idw.build_daily_weather_idw_series(
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
                self._eto_base[context.micro_area_id] = point_reference_et(base,context,self.stations)['et0_mm']
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
                    # Only this first day is recomputed. In the scalar view
                    # it has no predecessor, so it cannot be a carried value.
                    # Do not rescan every station's full history per microarea.
                    duplicate_dates_by_station={key: frozenset() for key in view_stations},
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
        first = date.fromisoformat(self._weather_base[micro_area_id]['daily_dates'][0])
        start_index = (start_day - first).days
        end_index = (end_day - first).days + 1
        if not 0 <= start_index < end_index <= len(values):
            raise ValueError('requested ET0 view is outside its prepared context')
        return values[start_index:end_index]

    def context_range(self, context, start, end):
        """Historical builders only need the union of an area's feature windows."""
        first, last = getattr(self, 'area_ranges', {}).get(context.area_id, (start, end))
        return max(start, first), min(end, last)

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
    compact_series: bool = False,
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
        compact_series=compact_series,
        area_ranges=_area_ranges(rows, known_sites, lookback_days + max_horizon_days - 1)
                    if compact_series else None,
    )
    global _ACTIVE
    _ACTIVE = workspace
    return workspace


def _area_ranges(rows, known_sites, lookback):
    contexts = biology_v3.load_micro_area_contexts(known_sites)
    ranges = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        context = contexts.get(str(row.get('micro_area_id') or ''))
        area = str(row.get('area_id') or (context.area_id if context else ''))
        day = weather_context.parse_day(row.get('observed_at'))
        if not area or day is None:
            continue
        first, last = ranges.get(area, (day, day))
        ranges[area] = min(first, day), max(last, day)
    return {area: (first - timedelta(days=lookback), last) for area, (first, last) in ranges.items()}


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
