"""Canonical daily rainfall interpolation for Biology V3.

Altitude V2 deliberately keeps its nearest-eligible-station contract.  This
module is a new, versioned contract: it estimates rainfall at a micro-area
representative point from all usable gauges inside a fixed radius.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Mapping

from rainmapper_core import mushroom_observation_context as weather_context


RAINFALL_IDW_CONTRACT_ID = "daily_rain_idw_radius15km_power2_v1"
RAINFALL_IDW_RADIUS_KM = 15.0
RAINFALL_IDW_POWER = 2.0
RAINFALL_IDW_DISTANCE_FLOOR_KM = 0.1

StationKey = tuple[str, str]


@dataclass(frozen=True)
class RainGaugeContribution:
    source: str
    station_code: str
    station_name: str
    distance_km: float
    rain_mm: float
    weight: float


@dataclass(frozen=True)
class DailyRainIDWResult:
    day: date
    rain_mm: float | None
    contributions: tuple[RainGaugeContribution, ...]
    excluded_missing: int
    excluded_suppressed: int
    excluded_retired: int

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
        "suppressed_is_zero": False,
        "minimum_contributing_stations": 1,
    }


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
    """Resolve one station-day without treating absence as zero."""
    record = station.records_by_day.get(day)
    if record is None or record.rain_mm is None:
        return None, "missing"
    if duplicate_dates is None:
        duplicate_dates = suppressed_rain_dates(station)
    if day in duplicate_dates:
        return None, "repeated_positive_value"
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

    A valid observed zero participates in the average. Missing or suppressed
    readings do not. With no usable gauge inside the radius, the result remains
    missing; it is never manufactured as zero.
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
        "daily_rain_excluded_retired_station_count": [
            item.excluded_retired for item in results
        ],
        "rain_observed_days": sum(item.observed for item in results),
        "rain_missing_days": sum(not item.observed for item in results),
        "rain_suppressed_station_days": sum(item.excluded_suppressed for item in results),
    }
