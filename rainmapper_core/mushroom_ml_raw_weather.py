"""Biology V5 daily-lag feature contract for benchmark and optional runtime."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any


LOOKBACK_DAYS = 365
VERSION_ID = "biology_v5_raw_weather_discovery"
RAW_WEATHER_CONTRACT_ID = "area_daily_raw365_common_idw_physical_state_v2"
FIXED_CONTRACT_ID = "fixed_gap_7d_biology_v5_raw365_v2"
LAG_CONTRACT_ID = "lag_event_biology_v5_raw365_v2"

WINDOWED_VERSION_ID = "biology_v5_windowed_raw_weather"
WINDOW_DAYS_OPTIONS = (30, 60, 90)
RAW_CHANNELS = (
    "rain_mm",
    "temp_min_c",
    "temp_max_c",
    "humidity_min_pct",
    "humidity_max_pct",
)
PHYSICAL_CHANNELS = ("eto0_mm", "climatic_balance_mm")
STATE_CHANNELS = ("soil_water_fraction",)
DAILY_CHANNELS = RAW_CHANNELS + PHYSICAL_CHANNELS + STATE_CHANNELS
PHYSICAL_STATE_SCALARS = (
    "soil_water_area_mean_at_cutoff",
    "soil_water_area_min_at_cutoff",
    "soil_water_change_7d",
    "soil_water_change_14d",
    "soil_water_recharge_7d",
    "soil_water_deficit_at_cutoff",
    "soil_water_drydown_7d",
)
AREA_SERIES_KEYS = {
    "rain_mm": "daily_rain_idw_mean_mm",
    "temp_min_c": "daily_temp_min_idw_mean_c",
    "temp_max_c": "daily_temp_max_idw_mean_c",
    "humidity_min_pct": "daily_humidity_min_idw_mean_pct",
    "humidity_max_pct": "daily_humidity_max_idw_mean_pct",
    "eto0_mm": "daily_eto0_mean_mm",
    "climatic_balance_mm": "daily_climatic_balance_mean_mm",
    "soil_water_fraction": "daily_soil_water_fraction_mean",
}


def lag_feature_name(channel: str, lag: int) -> str:
    if channel not in DAILY_CHANNELS:
        raise ValueError(f"unknown raw-weather channel: {channel}")
    if not 0 <= lag < LOOKBACK_DAYS:
        raise ValueError(f"lag must be in [0, {LOOKBACK_DAYS - 1}]")
    return f"{channel}__lag_{lag:03d}"


def feature_columns(
    *,
    include_physical: bool,
    include_state: bool = False,
    include_phenology: bool = True,
) -> list[str]:
    channels = RAW_CHANNELS + (PHYSICAL_CHANNELS if include_physical else ())
    if include_state:
        channels += STATE_CHANNELS
    columns = [lag_feature_name(channel, lag) for channel in channels for lag in range(LOOKBACK_DAYS)]
    if include_state:
        columns.extend(PHYSICAL_STATE_SCALARS)
    if include_phenology:
        columns.extend(("target_day_sin", "target_day_cos"))
    return columns


def windowed_profile_id(window_days: int) -> str:
    if window_days not in WINDOW_DAYS_OPTIONS:
        raise ValueError(f"window_days must be one of {WINDOW_DAYS_OPTIONS}")
    return f"raw_window_{window_days}d_plus_physical_state"


def window_days_from_profile_id(profile_id: str) -> int | None:
    for window_days in WINDOW_DAYS_OPTIONS:
        if profile_id == windowed_profile_id(window_days):
            return window_days
    return None


def windowed_feature_columns(window_days: int, *, include_horizon: bool) -> list[str]:
    """Raw weather truncated to the last `window_days`, plus the shared
    (365-day-warmed) physical-state scalars and phenology — never the full
    365 daily physical/state channels."""
    columns = [
        lag_feature_name(channel, lag)
        for channel in RAW_CHANNELS
        for lag in range(window_days)
    ]
    columns.extend(PHYSICAL_STATE_SCALARS)
    columns.extend(("target_day_sin", "target_day_cos"))
    if include_horizon:
        columns.append("horizon_days")
    return columns


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def build_raw_features(
    area_series: Mapping[str, object],
    *,
    target_date: date,
    horizon_days: int,
    temporal_contract_id: str,
) -> dict[str, float | None]:
    """Flatten oldest-to-newest area series onto cutoff-relative daily lags."""
    raw_dates = list(area_series.get("daily_dates") or [])
    if len(raw_dates) != LOOKBACK_DAYS:
        raise ValueError(f"raw daily series must contain exactly {LOOKBACK_DAYS} dates")
    parsed = [date.fromisoformat(str(value)) for value in raw_dates]
    if any((right - left).days != 1 for left, right in zip(parsed, parsed[1:])):
        raise ValueError("raw daily dates must be consecutive")
    features: dict[str, float | None] = {}
    for channel in DAILY_CHANNELS:
        values = list(area_series.get(AREA_SERIES_KEYS[channel]) or [])
        if len(values) != LOOKBACK_DAYS:
            values = [None] * LOOKBACK_DAYS
        for lag, value in enumerate(reversed(values)):
            features[lag_feature_name(channel, lag)] = _as_float(value)
    for name in PHYSICAL_STATE_SCALARS:
        features[name] = _as_float(area_series.get(name))
    angle = 2.0 * math.pi * ((target_date.timetuple().tm_yday - 1) / 365.2425)
    features["target_day_sin"] = math.sin(angle)
    features["target_day_cos"] = math.cos(angle)
    if temporal_contract_id == LAG_CONTRACT_ID:
        features["horizon_days"] = float(horizon_days)
    return features


def coverage_by_channel(area_series: Mapping[str, object]) -> dict[str, dict[str, int]]:
    bands = ((0, 7), (7, 30), (30, 90), (90, 180), (180, 365))
    result: dict[str, dict[str, int]] = {}
    for channel in DAILY_CHANNELS:
        chronological = list(area_series.get(AREA_SERIES_KEYS[channel]) or [])
        recent_first = list(reversed(chronological))
        result[channel] = {
            f"lag_{start:03d}_{end - 1:03d}_observed": sum(
                _as_float(value) is not None for value in recent_first[start:end]
            )
            for start, end in bands
        }
    return result


def diagnostic_weather_summary(area_series: Mapping[str, object]) -> dict[str, dict[str, float | int | None]]:
    bands = ((0, 7), (7, 30), (30, 90), (90, 180), (180, 365))
    result: dict[str, dict[str, float | int | None]] = {}
    for start, end in bands:
        key = f"lag_{start:03d}_{end - 1:03d}"
        row: dict[str, float | int | None] = {}
        for channel in DAILY_CHANNELS:
            recent = [
                _as_float(item)
                for item in reversed(list(area_series.get(AREA_SERIES_KEYS[channel]) or []))
            ]
            values = [value for value in recent[start:end] if value is not None]
            row[f"{channel}_observed_days"] = len(values)
            if channel in {"rain_mm", "eto0_mm", "climatic_balance_mm"}:
                row[f"{channel}_sum"] = round(sum(values), 6) if values else None
            else:
                row[f"{channel}_mean"] = round(sum(values) / len(values), 6) if values else None
        result[key] = row
    return result


def build_v5_sample(
    source: Mapping[str, Any],
    area_series: Mapping[str, object],
    *,
    temporal_contract_id: str,
) -> dict[str, Any]:
    metadata = dict(source.get("metadata") or {})
    target = date.fromisoformat(str(metadata["target_date"]))
    horizon = int(metadata.get("horizon_days") or 7)
    observation_id = str(metadata.get("observation_id") or source.get("sample_id") or "")
    features = build_raw_features(
        area_series,
        target_date=target,
        horizon_days=horizon,
        temporal_contract_id=temporal_contract_id,
    )
    metadata.update(
        {
            "source_sample_id": source.get("sample_id"),
            "temporal_contract_id": temporal_contract_id,
            "feature_set_id": temporal_contract_id,
            "raw_weather_contract_id": RAW_WEATHER_CONTRACT_ID,
            "daily_lag_orientation": "lag_000_is_cutoff_lag_364_is_oldest",
            "raw_daily_dates": list(area_series.get("daily_dates") or []),
            "diagnostic_weather_summary": diagnostic_weather_summary(area_series),
        }
    )
    quality = dict(source.get("quality") or {})
    quality["raw365_coverage_by_channel"] = coverage_by_channel(area_series)
    return {
        "sample_id": f"{observation_id}|{temporal_contract_id}|h{horizon}",
        "prediction_target": source.get("prediction_target"),
        "predictive_features": features,
        "quality": quality,
        "metadata": metadata,
    }


def feature_set_contract(temporal_contract_id: str) -> dict[str, Any]:
    if temporal_contract_id not in {FIXED_CONTRACT_ID, LAG_CONTRACT_ID}:
        raise ValueError(f"unknown V5 temporal contract: {temporal_contract_id}")
    raw = feature_columns(include_physical=False)
    physical = feature_columns(include_physical=True)
    physical_state = feature_columns(include_physical=True, include_state=True)
    raw_no_calendar = feature_columns(include_physical=False, include_phenology=False)
    physical_no_calendar = feature_columns(include_physical=True, include_phenology=False)
    physical_state_no_calendar = feature_columns(
        include_physical=True, include_state=True, include_phenology=False
    )
    include_horizon = temporal_contract_id == LAG_CONTRACT_ID
    if include_horizon:
        raw.append("horizon_days")
        physical.append("horizon_days")
        physical_state.append("horizon_days")
        raw_no_calendar.append("horizon_days")
        physical_no_calendar.append("horizon_days")
        physical_state_no_calendar.append("horizon_days")
    windowed_profiles = {
        windowed_profile_id(window_days): windowed_feature_columns(
            window_days, include_horizon=include_horizon
        )
        for window_days in WINDOW_DAYS_OPTIONS
    }
    return {
        "id": temporal_contract_id,
        "description": (
            "Non-operational 365-day common-IDW weather, physical balance, "
            "and soil-state discovery contract."
        ),
        "derived_feature_contract_id": RAW_WEATHER_CONTRACT_ID,
        "max_lookback_days": LOOKBACK_DAYS,
        "profiles": {
            "raw_primary_no_calendar": raw_no_calendar,
            "raw_primary": raw,
            "raw_primary_plus_physical_no_calendar": physical_no_calendar,
            "raw_primary_plus_physical": physical,
            "raw_primary_plus_physical_state_no_calendar": physical_state_no_calendar,
            "raw_primary_plus_physical_state": physical_state,
            **windowed_profiles,
        },
        "raw_channels": list(RAW_CHANNELS),
        "physical_channels": list(PHYSICAL_CHANNELS),
        "state_channels": list(STATE_CHANNELS),
        "physical_state_scalars": list(PHYSICAL_STATE_SCALARS),
        "quality_never_enters_x": True,
        "model_artifact_written": False,
    }
