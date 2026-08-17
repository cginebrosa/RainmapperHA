"""Non-operational Biology V5 daily-lag feature contract."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any


LOOKBACK_DAYS = 365
VERSION_ID = "biology_v5_raw_weather_discovery"
FIXED_CONTRACT_ID = "fixed_gap_7d_biology_v5_raw365_v1"
LAG_CONTRACT_ID = "lag_event_biology_v5_raw365_v1"
RAW_CHANNELS = (
    "rain_mm",
    "temp_min_c",
    "temp_max_c",
    "humidity_min_pct",
    "humidity_max_pct",
)
PHYSICAL_CHANNELS = ("eto0_mm", "climatic_balance_mm")
AREA_SERIES_KEYS = {
    "rain_mm": "daily_rain_idw_mean_mm",
    "temp_min_c": "daily_temp_min_idw_mean_c",
    "temp_max_c": "daily_temp_max_idw_mean_c",
    "humidity_min_pct": "daily_humidity_min_idw_mean_pct",
    "humidity_max_pct": "daily_humidity_max_idw_mean_pct",
    "eto0_mm": "daily_eto0_mean_mm",
    "climatic_balance_mm": "daily_climatic_balance_mean_mm",
}


def lag_feature_name(channel: str, lag: int) -> str:
    if channel not in RAW_CHANNELS + PHYSICAL_CHANNELS:
        raise ValueError(f"unknown raw-weather channel: {channel}")
    if not 0 <= lag < LOOKBACK_DAYS:
        raise ValueError(f"lag must be in [0, {LOOKBACK_DAYS - 1}]")
    return f"{channel}__lag_{lag:03d}"


def feature_columns(*, include_physical: bool, include_phenology: bool = True) -> list[str]:
    channels = RAW_CHANNELS + (PHYSICAL_CHANNELS if include_physical else ())
    columns = [lag_feature_name(channel, lag) for channel in channels for lag in range(LOOKBACK_DAYS)]
    if include_phenology:
        columns.extend(("target_day_sin", "target_day_cos"))
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
    for channel in RAW_CHANNELS + PHYSICAL_CHANNELS:
        values = list(area_series.get(AREA_SERIES_KEYS[channel]) or [])
        if len(values) != LOOKBACK_DAYS:
            values = [None] * LOOKBACK_DAYS
        for lag, value in enumerate(reversed(values)):
            features[lag_feature_name(channel, lag)] = _as_float(value)
    angle = 2.0 * math.pi * ((target_date.timetuple().tm_yday - 1) / 365.2425)
    features["target_day_sin"] = math.sin(angle)
    features["target_day_cos"] = math.cos(angle)
    if temporal_contract_id == LAG_CONTRACT_ID:
        features["horizon_days"] = float(horizon_days)
    return features


def coverage_by_channel(area_series: Mapping[str, object]) -> dict[str, dict[str, int]]:
    bands = ((0, 7), (7, 30), (30, 90), (90, 180), (180, 365))
    result: dict[str, dict[str, int]] = {}
    for channel in RAW_CHANNELS + PHYSICAL_CHANNELS:
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
        for channel in RAW_CHANNELS + PHYSICAL_CHANNELS:
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
            "raw_weather_contract_id": "area_daily_raw365_common_idw_v1",
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
    raw_no_calendar = feature_columns(include_physical=False, include_phenology=False)
    physical_no_calendar = feature_columns(include_physical=True, include_phenology=False)
    if temporal_contract_id == LAG_CONTRACT_ID:
        raw.append("horizon_days")
        physical.append("horizon_days")
        raw_no_calendar.append("horizon_days")
        physical_no_calendar.append("horizon_days")
    return {
        "id": temporal_contract_id,
        "description": "Non-operational 365-day common-IDW raw weather discovery contract.",
        "max_lookback_days": LOOKBACK_DAYS,
        "profiles": {
            "raw_primary_no_calendar": raw_no_calendar,
            "raw_primary": raw,
            "raw_primary_plus_physical_no_calendar": physical_no_calendar,
            "raw_primary_plus_physical": physical,
        },
        "raw_channels": list(RAW_CHANNELS),
        "physical_channels": list(PHYSICAL_CHANNELS),
        "quality_never_enters_x": True,
        "model_artifact_written": False,
    }
