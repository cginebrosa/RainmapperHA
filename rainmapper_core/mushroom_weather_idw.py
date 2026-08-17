"""Canonical daily rainfall interpolation for Biology V3.

Altitude V2 deliberately keeps its nearest-eligible-station contract.  This
module is a new, versioned contract: it estimates rainfall at a micro-area
representative point from all usable gauges inside a fixed radius.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Mapping

from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_ml_experiments as altitude_v2


RAINFALL_IDW_CONTRACT_ID = "daily_rain_idw_radius15km_power2_duplicate_zero_v2"
RAINFALL_IDW_RADIUS_KM = 15.0
RAINFALL_IDW_POWER = 2.0
RAINFALL_IDW_DISTANCE_FLOOR_KM = 0.1
WEATHER_IDW_CONTRACT_ID = "daily_weather_idw_radius15km_power2_temp_altitude_v1"
WEATHER_IDW_METRICS = (
    "temp_min_c",
    "temp_max_c",
    "humidity_min_pct",
    "humidity_max_pct",
)

StationKey = tuple[str, str]


@dataclass(frozen=True)
class RainGaugeContribution:
    source: str
    station_code: str
    station_name: str
    distance_km: float
    rain_mm: float
    weight: float
    imputed_repeated_positive_as_zero: bool = False


@dataclass(frozen=True)
class DailyRainIDWResult:
    day: date
    rain_mm: float | None
    contributions: tuple[RainGaugeContribution, ...]
    excluded_missing: int
    excluded_suppressed: int
    excluded_retired: int
    imputed_repeated_positive_zero: int

    @property
    def observed(self) -> bool:
        return self.rain_mm is not None

    @property
    def station_count(self) -> int:
        return len(self.contributions)

    @property
    def nearest_station_distance_km(self) -> float | None:
        if not self.contributions:
            return None
        return min(item.distance_km for item in self.contributions)


@dataclass(frozen=True)
class WeatherGaugeContribution:
    source: str
    station_code: str
    station_name: str
    distance_km: float
    raw_value: float
    adjusted_value: float
    weight: float
    station_altitude_m: float | None


@dataclass(frozen=True)
class DailyWeatherIDWResult:
    day: date
    metric: str
    value: float | None
    contributions: tuple[WeatherGaugeContribution, ...]
    excluded_missing: int
    excluded_invalid: int
    excluded_altitude_missing: int
    excluded_retired: int

    @property
    def observed(self) -> bool:
        return self.value is not None

    @property
    def station_count(self) -> int:
        return len(self.contributions)

    @property
    def nearest_station_distance_km(self) -> float | None:
        if not self.contributions:
            return None
        return min(item.distance_km for item in self.contributions)


def rainfall_idw_contract_metadata() -> dict[str, object]:
    """Return stable metadata that is stored with every Biology V3 benchmark."""
    return {
        "contract_id": RAINFALL_IDW_CONTRACT_ID,
        "method": "inverse_distance_weighted_daily_rainfall",
        "radius_km": RAINFALL_IDW_RADIUS_KM,
        "power": RAINFALL_IDW_POWER,
        "distance_floor_km": RAINFALL_IDW_DISTANCE_FLOOR_KM,
        "target_geometry": "micro_area_representative_point",
        "observed_zero_is_zero": True,
        "missing_is_zero": False,
        "repeated_positive_suppressed_is_zero": True,
        "other_suppressed_is_zero": False,
        "minimum_contributing_stations": 1,
    }


def weather_idw_contract_metadata() -> dict[str, object]:
    """Describe the common multichannel IDW used by Biology V3/V4."""
    return {
        "contract_id": WEATHER_IDW_CONTRACT_ID,
        "sources": ["aemet", "meteocat", "meteoclimatic", "wunderground"],
        "metrics": list(WEATHER_IDW_METRICS),
        "radius_km": RAINFALL_IDW_RADIUS_KM,
        "power": RAINFALL_IDW_POWER,
        "distance_floor_km": RAINFALL_IDW_DISTANCE_FLOOR_KM,
        "target_geometry": "micro_area_representative_point",
        "minimum_contributing_stations": 1,
        "temperature_altitude_correction": {
            "required": True,
            "lapse_rate_c_per_100m": altitude_v2.TEMPERATURE_LAPSE_RATE_C_PER_100M,
            "applied_before_idw": True,
        },
        "humidity_altitude_correction": False,
        "quality_fields_are_predictors": False,
    }


def estimate_daily_weather_idw(
    stations: Mapping[StationKey, weather_context.WeatherStation],
    *,
    metric: str,
    target_lat: float,
    target_lon: float,
    target_altitude_m: float | None,
    day: date,
    excluded_station_keys: frozenset[StationKey] | set[StationKey] = frozenset(),
    radius_km: float = RAINFALL_IDW_RADIUS_KM,
    power: float = RAINFALL_IDW_POWER,
    distance_floor_km: float = RAINFALL_IDW_DISTANCE_FLOOR_KM,
) -> DailyWeatherIDWResult:
    """Interpolate one daily temperature or humidity extreme from every source.

    Temperature readings are first moved from station altitude to micro-area
    altitude. Stations lacking an altitude are excluded for temperature rather
    than silently mixing corrected and uncorrected values.
    """
    if metric not in WEATHER_IDW_METRICS:
        raise ValueError(f"Unsupported weather IDW metric: {metric}")
    if radius_km <= 0 or power <= 0 or distance_floor_km <= 0:
        raise ValueError("IDW radius, power and distance floor must be positive")
    is_temperature = metric.startswith("temp_")
    if is_temperature and target_altitude_m is None:
        return DailyWeatherIDWResult(day, metric, None, (), 0, 0, len(stations), 0)

    normalized_exclusions = {
        (str(source).strip().lower(), str(code).strip().upper())
        for source, code in excluded_station_keys
    }
    weighted_value = 0.0
    total_weight = 0.0
    contributions: list[WeatherGaugeContribution] = []
    excluded_missing = 0
    excluded_invalid = 0
    excluded_altitude_missing = 0
    excluded_retired = 0
    for raw_key, station in sorted(
        stations.items(), key=lambda item: (str(item[0][0]).lower(), str(item[0][1]).upper())
    ):
        distance_km = weather_context.haversine_km(
            target_lat, target_lon, station.lat, station.lon
        )
        if distance_km > radius_km:
            continue
        key = (str(raw_key[0]).strip().lower(), str(raw_key[1]).strip().upper())
        if key in normalized_exclusions:
            excluded_retired += 1
            continue
        record = station.records_by_day.get(day)
        raw_value = getattr(record, metric, None) if record is not None else None
        if raw_value is None:
            excluded_missing += 1
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            excluded_invalid += 1
            continue
        if not math.isfinite(value) or (
            metric.startswith("humidity_") and not 0.0 <= value <= 100.0
        ):
            excluded_invalid += 1
            continue
        adjusted = value
        if is_temperature:
            correction = altitude_v2.altitude_temperature_correction_c(
                station.altitude_m, target_altitude_m
            )
            if correction is None:
                excluded_altitude_missing += 1
                continue
            adjusted += correction
        weight = 1.0 / (max(distance_km, distance_floor_km) ** power)
        weighted_value += adjusted * weight
        total_weight += weight
        contributions.append(
            WeatherGaugeContribution(
                source=station.source,
                station_code=station.station_code,
                station_name=station.station_name,
                distance_km=distance_km,
                raw_value=value,
                adjusted_value=adjusted,
                weight=weight,
                station_altitude_m=station.altitude_m,
            )
        )
    return DailyWeatherIDWResult(
        day=day,
        metric=metric,
        value=(weighted_value / total_weight if total_weight > 0 else None),
        contributions=tuple(contributions),
        excluded_missing=excluded_missing,
        excluded_invalid=excluded_invalid,
        excluded_altitude_missing=excluded_altitude_missing,
        excluded_retired=excluded_retired,
    )


def build_daily_weather_idw_series(
    stations: Mapping[StationKey, weather_context.WeatherStation],
    *,
    target_lat: float,
    target_lon: float,
    target_altitude_m: float | None,
    end_day: date,
    days: int,
    excluded_station_keys: frozenset[StationKey] | set[StationKey] = frozenset(),
    duplicate_dates_by_station: Mapping[StationKey, frozenset[date] | set[date]] | None = None,
) -> dict[str, object]:
    """Build aligned rain, temperature and humidity IDW series at one point."""
    nearby_stations = {
        key: station
        for key, station in stations.items()
        if weather_context.haversine_km(
            target_lat, target_lon, station.lat, station.lon
        )
        <= RAINFALL_IDW_RADIUS_KM
    }
    rainfall = build_daily_rain_idw_series(
        nearby_stations,
        target_lat=target_lat,
        target_lon=target_lon,
        end_day=end_day,
        days=days,
        excluded_station_keys=excluded_station_keys,
        duplicate_dates_by_station=duplicate_dates_by_station,
    )
    start_day = end_day - timedelta(days=days - 1)
    metric_results = {
        metric: [
            estimate_daily_weather_idw(
                nearby_stations,
                metric=metric,
                target_lat=target_lat,
                target_lon=target_lon,
                target_altitude_m=target_altitude_m,
                day=start_day + timedelta(days=offset),
                excluded_station_keys=excluded_station_keys,
            )
            for offset in range(days)
        ]
        for metric in WEATHER_IDW_METRICS
    }
    result = dict(rainfall)
    result["weather_idw_contract_id"] = WEATHER_IDW_CONTRACT_ID
    result["target_altitude_m"] = target_altitude_m
    for metric, rows in metric_results.items():
        prefix = f"daily_{metric.removesuffix('_c').removesuffix('_pct')}_idw"
        unit = "c" if metric.startswith("temp_") else "pct"
        result[f"{prefix}_{unit}"] = [row.value for row in rows]
        result[f"{prefix}_station_count"] = [row.station_count for row in rows]
        result[f"{prefix}_nearest_station_distance_km"] = [
            row.nearest_station_distance_km for row in rows
        ]
        result[f"{prefix}_excluded_missing_station_count"] = [
            row.excluded_missing for row in rows
        ]
        result[f"{prefix}_excluded_altitude_missing_station_count"] = [
            row.excluded_altitude_missing for row in rows
        ]
    return result


def slice_daily_weather_idw_series(
    series: Mapping[str, object],
    *,
    end_day: date,
    days: int,
) -> dict[str, object]:
    """Return an exact window from a previously materialized IDW series.

    Daily IDW values are independent between dates. Building one long series
    per micro-area and slicing it is therefore numerically equivalent to
    rebuilding every overlapping observation window, while avoiding the most
    expensive repeated station scans. The returned shape intentionally matches
    :func:`build_daily_weather_idw_series` so benchmark and future training
    consumers use the same materializer contract.
    """
    if days <= 0:
        raise ValueError("days must be positive")
    raw_dates = series.get("daily_dates")
    if not isinstance(raw_dates, list) or not raw_dates:
        raise ValueError("weather IDW series has no daily_dates")
    try:
        parsed_dates = [date.fromisoformat(str(value)) for value in raw_dates]
    except ValueError as exc:
        raise ValueError("weather IDW series contains an invalid daily date") from exc
    start_day = end_day - timedelta(days=days - 1)
    try:
        start_index = parsed_dates.index(start_day)
        end_index = parsed_dates.index(end_day) + 1
    except ValueError as exc:
        raise ValueError("requested weather IDW window is outside the cached range") from exc
    if end_index - start_index != days:
        raise ValueError("cached weather IDW dates are not consecutive for the requested window")
    expected_dates = [start_day + timedelta(days=offset) for offset in range(days)]
    if parsed_dates[start_index:end_index] != expected_dates:
        raise ValueError("cached weather IDW dates are not consecutive for the requested window")

    total_days = len(raw_dates)
    result: dict[str, object] = {}
    for key, value in series.items():
        if isinstance(value, list) and len(value) == total_days:
            result[key] = value[start_index:end_index]
        else:
            result[key] = value

    observed = result.get("daily_rain_observed")
    if isinstance(observed, list):
        result["rain_observed_days"] = sum(bool(value) for value in observed)
        result["rain_missing_days"] = sum(not bool(value) for value in observed)
    for daily_key, total_key in (
        ("daily_rain_suppressed_station_count", "rain_suppressed_station_days"),
        (
            "daily_rain_imputed_duplicate_zero_station_count",
            "rain_imputed_duplicate_zero_station_days",
        ),
    ):
        values = result.get(daily_key)
        if isinstance(values, list):
            result[total_key] = sum(int(value) for value in values)
    return result


def disabled_wunderground_station_keys(path: Path) -> frozenset[StationKey]:
    """Read every explicitly disabled PWS from ``stations.txt``.

    The reason (404, parser failure or bad data) does not matter to Biology V3:
    disabled stations are not eligible inputs, even if old rows remain in the
    immutable history.
    """
    if not path.is_file():
        return frozenset()
    result: set[StationKey] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "rainmapper-disabled:" not in line.lower():
            continue
        match = re.search(r"/pws/([A-Z0-9]+)", line, re.IGNORECASE)
        if match:
            result.add(("wunderground", match.group(1).upper()))
    return frozenset(result)


def suppressed_rain_dates(
    station: weather_context.WeatherStation,
) -> frozenset[date]:
    """Return carried-forward positive rainfall dates for one station."""
    records = sorted(station.records_by_day.values(), key=lambda item: item.day)
    return frozenset(weather_context._consecutive_duplicate_rain_dates(records))


def usable_daily_rain(
    station: weather_context.WeatherStation,
    day: date,
    *,
    duplicate_dates: frozenset[date] | set[date] | None = None,
) -> tuple[float | None, str | None]:
    """Resolve one station-day under the versioned duplicate-zero policy."""
    record = station.records_by_day.get(day)
    if record is None or record.rain_mm is None:
        return None, "missing"
    if duplicate_dates is None:
        duplicate_dates = suppressed_rain_dates(station)
    if day in duplicate_dates:
        return 0.0, "repeated_positive_value_imputed_zero"
    value = float(record.rain_mm)
    if value < 0:
        return None, "negative_value"
    if value > weather_context.DAILY_RAIN_SANITY_LIMIT_MM:
        return None, "daily_sanity_limit"
    return value, None


def estimate_daily_rain_idw(
    stations: Mapping[StationKey, weather_context.WeatherStation],
    *,
    target_lat: float,
    target_lon: float,
    day: date,
    excluded_station_keys: frozenset[StationKey] | set[StationKey] = frozenset(),
    radius_km: float = RAINFALL_IDW_RADIUS_KM,
    power: float = RAINFALL_IDW_POWER,
    distance_floor_km: float = RAINFALL_IDW_DISTANCE_FLOOR_KM,
    duplicate_dates_by_station: Mapping[StationKey, frozenset[date] | set[date]] | None = None,
) -> DailyRainIDWResult:
    """Estimate daily rain at a point with deterministic inverse-distance weights.

    A valid observed zero participates in the average. A carried-forward
    repeated positive is treated as the most likely zero and participates with
    an imputation flag. Generic missing and other suppressed readings do not.
    """
    if radius_km <= 0 or power <= 0 or distance_floor_km <= 0:
        raise ValueError("IDW radius, power and distance floor must be positive")

    normalized_exclusions = {
        (str(source).strip().lower(), str(code).strip().upper())
        for source, code in excluded_station_keys
    }
    weighted_rain = 0.0
    total_weight = 0.0
    contributions: list[RainGaugeContribution] = []
    excluded_missing = 0
    excluded_suppressed = 0
    excluded_retired = 0
    imputed_repeated_positive_zero = 0

    for raw_key, station in sorted(
        stations.items(), key=lambda item: (str(item[0][0]).lower(), str(item[0][1]).upper())
    ):
        key = (str(raw_key[0]).strip().lower(), str(raw_key[1]).strip().upper())
        distance_km = weather_context.haversine_km(
            target_lat, target_lon, station.lat, station.lon
        )
        if distance_km > radius_km:
            continue
        if key in normalized_exclusions:
            excluded_retired += 1
            continue
        duplicate_dates = (
            duplicate_dates_by_station.get(raw_key)
            if duplicate_dates_by_station is not None
            else None
        )
        value, reason = usable_daily_rain(
            station,
            day,
            duplicate_dates=duplicate_dates,
        )
        if value is None:
            if reason == "missing":
                excluded_missing += 1
            else:
                excluded_suppressed += 1
            continue
        imputed_zero = reason == "repeated_positive_value_imputed_zero"
        if imputed_zero:
            imputed_repeated_positive_zero += 1
        weight = 1.0 / (max(distance_km, distance_floor_km) ** power)
        weighted_rain += value * weight
        total_weight += weight
        contributions.append(
            RainGaugeContribution(
                source=station.source,
                station_code=station.station_code,
                station_name=station.station_name,
                distance_km=distance_km,
                rain_mm=value,
                weight=weight,
                imputed_repeated_positive_as_zero=imputed_zero,
            )
        )

    rain_mm = weighted_rain / total_weight if total_weight > 0 else None
    return DailyRainIDWResult(
        day=day,
        rain_mm=rain_mm,
        contributions=tuple(contributions),
        excluded_missing=excluded_missing,
        excluded_suppressed=excluded_suppressed,
        excluded_retired=excluded_retired,
        imputed_repeated_positive_zero=imputed_repeated_positive_zero,
    )


def build_daily_rain_idw_series(
    stations: Mapping[StationKey, weather_context.WeatherStation],
    *,
    target_lat: float,
    target_lon: float,
    end_day: date,
    days: int,
    excluded_station_keys: frozenset[StationKey] | set[StationKey] = frozenset(),
    duplicate_dates_by_station: Mapping[StationKey, frozenset[date] | set[date]] | None = None,
) -> dict[str, object]:
    """Materialize an aligned Biology V3 rainfall series and its quality data."""
    if days <= 0:
        raise ValueError("days must be positive")
    duplicates = duplicate_dates_by_station or {
        key: suppressed_rain_dates(station) for key, station in stations.items()
    }
    start_day = end_day - timedelta(days=days - 1)
    results = [
        estimate_daily_rain_idw(
            stations,
            target_lat=target_lat,
            target_lon=target_lon,
            day=start_day + timedelta(days=offset),
            excluded_station_keys=excluded_station_keys,
            duplicate_dates_by_station=duplicates,
        )
        for offset in range(days)
    ]
    return {
        "rainfall_contract_id": RAINFALL_IDW_CONTRACT_ID,
        "daily_dates": [item.day.isoformat() for item in results],
        "daily_rain_idw_mm": [item.rain_mm for item in results],
        "daily_rain_observed": [item.observed for item in results],
        "daily_rain_station_count": [item.station_count for item in results],
        "daily_rain_nearest_station_distance_km": [
            item.nearest_station_distance_km for item in results
        ],
        "daily_rain_excluded_missing_station_count": [
            item.excluded_missing for item in results
        ],
        "daily_rain_suppressed_station_count": [
            item.excluded_suppressed for item in results
        ],
        "daily_rain_imputed_duplicate_zero_station_count": [
            item.imputed_repeated_positive_zero for item in results
        ],
        "daily_rain_excluded_retired_station_count": [
            item.excluded_retired for item in results
        ],
        "rain_observed_days": sum(item.observed for item in results),
        "rain_missing_days": sum(not item.observed for item in results),
        "rain_suppressed_station_days": sum(item.excluded_suppressed for item in results),
        "rain_imputed_duplicate_zero_station_days": sum(
            item.imputed_repeated_positive_zero for item in results
        ),
    }
