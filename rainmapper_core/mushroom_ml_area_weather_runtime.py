"""Shared common-IDW area weather materialization for V3--V6 inference."""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Mapping

from rainmapper_core import mushroom_climatic_water_balance as climate
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


def area_contexts(
    known_sites_path: Path,
) -> tuple[
    dict[str, biology_v3.AreaPredictionContext],
    dict[str, list[biology_v3.MicroAreaContext]],
]:
    micro = biology_v3.load_micro_area_contexts(Path(known_sites_path))
    grouped: dict[str, list[biology_v3.MicroAreaContext]] = defaultdict(list)
    for row in micro.values():
        grouped[row.area_id].append(row)
    areas: dict[str, biology_v3.AreaPredictionContext] = {}
    for area_id, rows in grouped.items():
        lat = statistics.fmean(row.lat for row in rows)
        lon = statistics.fmean(row.lon for row in rows)
        altitudes = [float(row.altitude_m) for row in rows if row.altitude_m is not None]
        areas[area_id] = biology_v3.AreaPredictionContext(
            area_id=area_id,
            lat=lat,
            lon=lon,
            location_source="mean_of_microarea_representative_points",
            altitude_m=statistics.fmean(altitudes) if altitudes else None,
            altitude_source="mean_of_microarea_dem_means" if altitudes else None,
        )
    return areas, dict(grouped)


def _mean_series(rows: list[list[float | None]], length: int) -> list[float | None]:
    return [
        (
            statistics.fmean(
                float(row[index])
                for row in rows
                if index < len(row) and row[index] is not None
            )
            if any(index < len(row) and row[index] is not None for row in rows)
            else None
        )
        for index in range(length)
    ]


def materialize_area_series(
    *,
    area_id: str,
    end_day: date,
    days: int,
    microareas_by_area: Mapping[str, list[biology_v3.MicroAreaContext]],
    stations: Mapping[tuple[str, str], weather_context.WeatherStation],
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]] = frozenset(),
) -> dict[str, object]:
    """Build one reusable 365-day area series; missing never becomes zero."""
    contexts = list(microareas_by_area.get(area_id, []))
    if not contexts:
        raise ValueError(f"Unknown or empty mushroom area: {area_id}")
    duplicate_dates = {
        key: mushroom_weather_idw.suppressed_rain_dates(station)
        for key, station in stations.items()
    }
    micro_weather: dict[str, dict[str, object]] = {}
    micro_eto: list[list[float | None]] = []
    axis = list(weather_context.date_window(end_day, days))
    for context in contexts:
        weather = mushroom_weather_idw.build_daily_weather_idw_series(
            stations,
            target_lat=context.lat,
            target_lon=context.lon,
            target_altitude_m=context.altitude_m,
            end_day=end_day,
            days=days,
            excluded_station_keys=excluded_station_keys,
            duplicate_dates_by_station=duplicate_dates,
        )
        micro_weather[context.micro_area_id] = weather
        micro_eto.append(
            [
                climate.hargreaves_reference_evapotranspiration_mm(
                    day, context.lat, low, high
                )
                if low is not None and high is not None
                else None
                for day, low, high in zip(
                    axis,
                    weather["daily_temp_min_idw_c"],
                    weather["daily_temp_max_idw_c"],
                    strict=True,
                )
            ]
        )
    area = biology_v3.aggregate_area_rainfall_series(micro_weather)
    eto = _mean_series(micro_eto, days)
    rain = list(area["daily_rain_idw_mean_mm"])
    area["daily_eto0_mean_mm"] = eto
    area["daily_climatic_balance_mean_mm"] = [
        float(rain_value) - float(eto_value)
        if rain_value is not None and eto_value is not None
        else None
        for rain_value, eto_value in zip(rain, eto, strict=True)
    ]
    return area
