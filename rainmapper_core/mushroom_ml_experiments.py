"""Build frozen, leakage-free datasets for mushroom ML experiments.

This module does not train or promote an operational model.  It turns the
joined observation artifact into a versioned benchmark whose target date,
information cutoff and horizon are explicit.  Every later estimator must use
the samples and partitions written here unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

from rainmapper_core import mushroom_observation_context as ctx
from rainmapper_core.mushroom_ml_trainer import (
    TRAIN_RATIO,
    aggregate_to_area_episodes,
    filter_eligible,
    load_area_representative_altitudes,
    load_features,
    load_micro_area_to_area,
)


DEFAULT_HORIZONS = tuple(range(1, 8))
RAIN_EVENT_THRESHOLD_MM = 2.0
SIGNIFICANT_RAIN_THRESHOLD_MM = 5.0
HEAT_STRESS_THRESHOLD_C = 28.0
EVENT_LOOKBACK_DAYS = 90
TEMPERATURE_LAPSE_RATE_C_PER_100M = 0.65


@dataclass(frozen=True)
class FeatureSetSpec:
    feature_set_id: str
    description: str
    feature_cols: tuple[str, ...]
    max_lookback_days: int


LAG_EVENT_V1 = FeatureSetSpec(
    feature_set_id="lag_event_v1",
    description=(
        "Compact daily-weather representation available at the issue date: "
        "disjoint rain lags, age of known rain events and observed post-rain conditions."
    ),
    feature_cols=(
        "horizon_days",
        "target_month_sin",
        "target_month_cos",
        "gis_altitude_m",
        "rain_cutoff_0_3d_mm",
        "rain_cutoff_4_7d_mm",
        "rain_cutoff_8_14d_mm",
        "rain_cutoff_15_21d_mm",
        "days_since_rain_gt_2_at_target",
        "days_since_significant_rain_at_target",
        "significant_rain_found_90d",
        "rain_observed_days_21",
        "rain_missing_days_21",
        "rain_suppressed_days_21",
        "rain_observed_days_90",
        "rain_missing_days_90",
        "rain_suppressed_days_90",
        "dry_spell_observed_at_cutoff",
        "dry_spell_is_censored",
        "heat_stress_observed_at_cutoff",
        "heat_stress_is_censored",
        "temp_mean_after_significant_rain_c",
        "humidity_mean_after_significant_rain_pct",
        "temp_observed_days_after_significant_rain",
        "humidity_observed_days_after_significant_rain",
    ),
    max_lookback_days=EVENT_LOOKBACK_DAYS,
)

FIXED_GAP_7D_V1 = FeatureSetSpec(
    feature_set_id="fixed_gap_7d_v1",
    description=(
        "One sample per episode using only weather observed through target date minus "
        "seven days. The hidden week is never interpreted as zero weather."
    ),
    feature_cols=tuple(
        column for column in LAG_EVENT_V1.feature_cols if column != "horizon_days"
    ),
    max_lookback_days=LAG_EVENT_V1.max_lookback_days,
)

LAG_EVENT_ALTITUDE_V2 = FeatureSetSpec(
    feature_set_id="lag_event_altitude_v2",
    description=(
        "Issue-date lag/event representation with station temperatures adjusted to "
        "the representative DEM altitude of the complete area. It replaces the global "
        "28 C heat-stress threshold with continuous thermal variables."
    ),
    feature_cols=tuple(
        column
        for column in LAG_EVENT_V1.feature_cols
        if column not in {"heat_stress_observed_at_cutoff", "heat_stress_is_censored"}
    )
    + (
        "temp_max_mean_cutoff_7d_c",
        "temp_mean_cutoff_7d_c",
    ),
    max_lookback_days=EVENT_LOOKBACK_DAYS,
)

FIXED_GAP_7D_ALTITUDE_V2 = FeatureSetSpec(
    feature_set_id="fixed_gap_7d_altitude_v2",
    description=(
        "Fixed seven-day blind gap with station temperatures adjusted to the "
        "representative DEM altitude of the complete area and continuous thermal variables."
    ),
    feature_cols=tuple(
        column for column in LAG_EVENT_ALTITUDE_V2.feature_cols if column != "horizon_days"
    ),
    max_lookback_days=EVENT_LOOKBACK_DAYS,
)

FEATURE_SETS = {
    LAG_EVENT_V1.feature_set_id: LAG_EVENT_V1,
    FIXED_GAP_7D_V1.feature_set_id: FIXED_GAP_7D_V1,
    LAG_EVENT_ALTITUDE_V2.feature_set_id: LAG_EVENT_ALTITUDE_V2,
    FIXED_GAP_7D_ALTITUDE_V2.feature_set_id: FIXED_GAP_7D_ALTITUDE_V2,
}


def _float_or_none(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _series(row: dict[str, Any], field: str) -> list[float | None]:
    values = row.get(field)
    if not isinstance(values, list):
        return []
    return [_float_or_none(value) for value in values]


def _window(values: Sequence[float | None], start_age: int, end_age: int) -> list[float | None] | None:
    """Return one cutoff-relative age window, inclusive at both ends."""
    width = end_age - start_age + 1
    end = len(values) - start_age
    start = end - width
    if start < 0 or end > len(values):
        return None
    window = values[start:end]
    if len(window) != width:
        return None
    return list(window)


def _effective_sum(values: Sequence[float | None], start_age: int, end_age: int) -> float | None:
    window = _window(values, start_age, end_age)
    return round(sum(float(value or 0.0) for value in window), 3) if window is not None else None


def _last_event_age(values: Sequence[float | None], threshold: float) -> int | None:
    """Return cutoff-relative event age from the effective-rain series."""
    for age, value in enumerate(reversed(values)):
        effective = float(value or 0.0)
        if effective > threshold or (
            threshold == SIGNIFICANT_RAIN_THRESHOLD_MM and effective >= threshold
        ):
            return age
    return None


def _continuous_run(
    values: Sequence[float | None],
    predicate: Any,
) -> tuple[int | None, bool]:
    """Return observed run length and whether its older boundary is censored."""
    run = 0
    for value in reversed(values):
        if value is None:
            return run, True
        if not predicate(value):
            return run, False
        run += 1
    return run, True


def _available_mean(values: Sequence[float | None]) -> tuple[float | None, int]:
    available = [float(value) for value in values if value is not None]
    if not available:
        return None, 0
    return round(sum(available) / len(available), 3), len(available)


def altitude_temperature_correction_c(
    station_altitude_m: object,
    area_altitude_m: object,
) -> float | None:
    """Return the additive station-to-area temperature correction.

    Positive values warm a lower target area; negative values cool a higher
    target area. The rate matches MapLibre's current configurable default.
    """
    station_altitude = _float_or_none(station_altitude_m)
    area_altitude = _float_or_none(area_altitude_m)
    if station_altitude is None or area_altitude is None:
        return None
    return round(
        ((station_altitude - area_altitude) / 100.0)
        * TEMPERATURE_LAPSE_RATE_C_PER_100M,
        6,
    )


def _corrected_temperature_series(
    values: Sequence[float | None], correction_c: float | None
) -> list[float | None]:
    if correction_c is None:
        return [None for _value in values]
    return [
        round(float(value) + correction_c, 3) if value is not None else None
        for value in values
    ]


def build_lag_event_features(
    episode: dict[str, Any],
    horizon_days: int,
    *,
    altitude_corrected: bool = False,
) -> tuple[dict[str, float | None], dict[str, Any]]:
    """Build features known at target_date - horizon_days, never beyond it."""
    if horizon_days < 0:
        raise ValueError("horizon_days must be >= 0")
    target_date = date.fromisoformat(str(episode["observed_at"]))
    cutoff_date = target_date - timedelta(days=horizon_days)

    raw = {
        field: _series(episode, field)
        for field in (
            "daily_rain_mm",
            "daily_rain_observed",
            "daily_rain_suppressed",
            "daily_temp_max_c",
            "daily_temp_mean_c",
            "daily_humidity_mean_pct",
        )
    }
    rain_source = raw["daily_rain_mm"]
    if not raw["daily_rain_observed"] and rain_source:
        raw["daily_rain_observed"] = [
            1.0 if value is not None else 0.0 for value in rain_source
        ]
    if not raw["daily_rain_suppressed"] and rain_source:
        raw["daily_rain_suppressed"] = [0.0] * len(rain_source)
    raw["daily_rain_mm"] = [float(value or 0.0) for value in rain_source]
    quality_temp_mean = list(raw["daily_temp_mean_c"])
    quality_humidity_mean = list(raw["daily_humidity_mean_pct"])
    temperature_correction_c = None
    if altitude_corrected:
        temperature_correction_c = altitude_temperature_correction_c(
            episode.get("weather_station_altitude_m"),
            episode.get("gis_altitude_m"),
        )
        for field in ("daily_temp_max_c", "daily_temp_mean_c"):
            raw[field] = _corrected_temperature_series(
                raw[field], temperature_correction_c
            )
    lengths = {len(values) for values in raw.values() if values}
    aligned = len(lengths) <= 1
    source_days = max(lengths, default=0)
    cutoff_end = source_days - horizon_days
    enough_history = aligned and cutoff_end >= LAG_EVENT_V1.max_lookback_days

    if not enough_history:
        known = {field: [] for field in raw}
    else:
        known = {field: values[:cutoff_end] for field, values in raw.items()}

    rain = known["daily_rain_mm"]
    rain_observed = known["daily_rain_observed"]
    rain_suppressed = known["daily_rain_suppressed"]
    temp_max = known["daily_temp_max_c"]
    temp_mean = known["daily_temp_mean_c"]
    humidity_mean = known["daily_humidity_mean_pct"]
    rain_search = rain[-EVENT_LOOKBACK_DAYS:]
    rain_observed_search = rain_observed[-EVENT_LOOKBACK_DAYS:]
    rain_suppressed_search = rain_suppressed[-EVENT_LOOKBACK_DAYS:]
    temp_max_search = temp_max[-EVENT_LOOKBACK_DAYS:]

    rain_age = _last_event_age(rain_search, RAIN_EVENT_THRESHOLD_MM)
    significant_age = _last_event_age(
        rain_search, SIGNIFICANT_RAIN_THRESHOLD_MM
    )
    dry_run, dry_censored = _continuous_run(rain_search, lambda value: value <= 0.0)
    heat_run, heat_censored = _continuous_run(
        temp_max_search, lambda value: value > HEAT_STRESS_THRESHOLD_C
    )
    temp_max_mean_7d, _temp_max_days_7d = _available_mean(temp_max[-7:])
    temp_mean_7d, _temp_mean_days_7d = _available_mean(temp_mean[-7:])

    significant_found = significant_age is not None
    context_days = significant_age + 1 if significant_age is not None else EVENT_LOOKBACK_DAYS
    after_rain_temp, after_rain_temp_days = _available_mean(temp_mean[-context_days:])
    after_rain_humidity, after_rain_humidity_days = _available_mean(
        humidity_mean[-context_days:]
    )

    rain_observed_21 = int(sum(rain_observed[-21:]))
    rain_suppressed_21 = int(sum(rain_suppressed[-21:]))
    rain_missing_21 = max(0, 21 - rain_observed_21 - rain_suppressed_21)
    rain_observed_90 = int(sum(rain_observed_search))
    rain_suppressed_90 = int(sum(rain_suppressed_search))
    rain_missing_90 = max(0, EVENT_LOOKBACK_DAYS - rain_observed_90 - rain_suppressed_90)
    quality_temp_known = quality_temp_mean[:cutoff_end] if enough_history else []
    quality_humidity_known = quality_humidity_mean[:cutoff_end] if enough_history else []
    temperature_observed_21 = sum(value is not None for value in quality_temp_known[-21:])
    humidity_observed_21 = sum(value is not None for value in quality_humidity_known[-21:])

    angle = 2.0 * math.pi * (target_date.month - 1) / 12.0
    features: dict[str, float | None] = {
        "horizon_days": float(horizon_days),
        "target_month_sin": round(math.sin(angle), 6),
        "target_month_cos": round(math.cos(angle), 6),
        "gis_altitude_m": _float_or_none(episode.get("gis_altitude_m")),
        "rain_cutoff_0_3d_mm": _effective_sum(rain, 0, 2),
        "rain_cutoff_4_7d_mm": _effective_sum(rain, 3, 6),
        "rain_cutoff_8_14d_mm": _effective_sum(rain, 7, 13),
        "rain_cutoff_15_21d_mm": _effective_sum(rain, 14, 20),
        "days_since_rain_gt_2_at_target": (
            float(min(EVENT_LOOKBACK_DAYS, rain_age + horizon_days))
            if rain_age is not None
            else float(EVENT_LOOKBACK_DAYS)
        ),
        "days_since_significant_rain_at_target": (
            float(min(EVENT_LOOKBACK_DAYS, significant_age + horizon_days))
            if significant_age is not None
            else float(EVENT_LOOKBACK_DAYS)
        ),
        "significant_rain_found_90d": float(significant_found),
        "rain_observed_days_21": float(rain_observed_21),
        "rain_missing_days_21": float(rain_missing_21),
        "rain_suppressed_days_21": float(rain_suppressed_21),
        "rain_observed_days_90": float(rain_observed_90),
        "rain_missing_days_90": float(rain_missing_90),
        "rain_suppressed_days_90": float(rain_suppressed_90),
        "dry_spell_observed_at_cutoff": float(dry_run) if dry_run is not None else None,
        "dry_spell_is_censored": float(dry_censored) if dry_run is not None else None,
        "heat_stress_observed_at_cutoff": float(heat_run) if heat_run is not None else None,
        "heat_stress_is_censored": float(heat_censored) if heat_run is not None else None,
        "temp_mean_after_significant_rain_c": after_rain_temp,
        "humidity_mean_after_significant_rain_pct": after_rain_humidity,
        "temp_observed_days_after_significant_rain": float(after_rain_temp_days),
        "humidity_observed_days_after_significant_rain": float(after_rain_humidity_days),
    }
    if altitude_corrected:
        features.pop("heat_stress_observed_at_cutoff", None)
        features.pop("heat_stress_is_censored", None)
        features["temp_max_mean_cutoff_7d_c"] = temp_max_mean_7d
        features["temp_mean_cutoff_7d_c"] = temp_mean_7d
    metadata = {
        "target_date": target_date.isoformat(),
        "cutoff_date": cutoff_date.isoformat(),
        "horizon_days": horizon_days,
        "source_daily_days": source_days,
        "daily_series_aligned": aligned,
        "enough_history": enough_history,
        "rain_lookback_observed_days": rain_observed_90,
        "rain_lookback_missing_days": rain_missing_90,
        "rain_lookback_suppressed_days": rain_suppressed_90,
        "rain_lookback_expected_days": EVENT_LOOKBACK_DAYS,
        "temperature_observed_days_21": temperature_observed_21,
        "humidity_observed_days_21": humidity_observed_21,
        "rain_event_search_complete": enough_history,
        "significant_rain_search_complete": enough_history,
        "temperature_contract": (
            "station_temperature_adjusted_to_area_representative_dem_altitude_v1"
            if altitude_corrected
            else "raw_station_temperature_v1"
        ),
        "weather_station_altitude_m": _float_or_none(
            episode.get("weather_station_altitude_m")
        ),
        "area_representative_altitude_m": _float_or_none(
            episode.get("gis_altitude_m")
        ),
        "temperature_lapse_rate_c_per_100m": (
            TEMPERATURE_LAPSE_RATE_C_PER_100M if altitude_corrected else None
        ),
        "temperature_altitude_correction_c": temperature_correction_c,
        "temperature_altitude_correction_available": (
            temperature_correction_c is not None if altitude_corrected else None
        ),
    }
    eligibility_reasons = []
    if not enough_history:
        eligibility_reasons.append("insufficient_or_unaligned_daily_history")
    if rain_observed_21 < ctx.STATION_RAIN_MIN_DAYS_21:
        eligibility_reasons.append("rain_coverage_below_19_of_21")
    if rain_observed_90 < ctx.STATION_RAIN_MIN_DAYS_90:
        eligibility_reasons.append("rain_coverage_below_81_of_90")
    if temperature_observed_21 < ctx.STATION_TEMP_MIN_DAYS_21:
        eligibility_reasons.append("temperature_coverage_below_19_of_21")
    if humidity_observed_21 < ctx.STATION_HUMIDITY_MIN_DAYS_21:
        eligibility_reasons.append("humidity_coverage_below_19_of_21")
    if altitude_corrected and temperature_correction_c is None:
        eligibility_reasons.append("station_or_area_altitude_missing")
    metadata["training_eligible"] = not eligibility_reasons
    metadata["training_ineligibility_reasons"] = eligibility_reasons
    return features, metadata


def build_fixed_gap_7d_features(
    episode: dict[str, Any],
) -> tuple[dict[str, float | None], dict[str, Any]]:
    """Build the fixed seven-day blind-gap feature contract."""
    features, metadata = build_lag_event_features(episode, horizon_days=7)
    features.pop("horizon_days", None)
    metadata["feature_set_id"] = FIXED_GAP_7D_V1.feature_set_id
    metadata["hidden_interval"] = "target_minus_6_days_through_target_inclusive"
    return features, metadata


def build_lag_event_altitude_features(
    episode: dict[str, Any], horizon_days: int
) -> tuple[dict[str, float | None], dict[str, Any]]:
    features, metadata = build_lag_event_features(
        episode, horizon_days, altitude_corrected=True
    )
    metadata["feature_set_id"] = LAG_EVENT_ALTITUDE_V2.feature_set_id
    return features, metadata


def build_fixed_gap_7d_altitude_features(
    episode: dict[str, Any],
) -> tuple[dict[str, float | None], dict[str, Any]]:
    features, metadata = build_lag_event_altitude_features(episode, horizon_days=7)
    features.pop("horizon_days", None)
    metadata["feature_set_id"] = FIXED_GAP_7D_ALTITUDE_V2.feature_set_id
    metadata["hidden_interval"] = "target_minus_6_days_through_target_inclusive"
    return features, metadata


PARTITION_SEED = 42


def _episode_id(episode: dict[str, Any]) -> str:
    return (
        f"{episode.get('species_id')}|{episode.get('area_id')}|"
        f"{episode.get('observed_at')}"
    )


def _chronological_partitions(episodes: Sequence[dict[str, Any]]) -> dict[str, str]:
    """Assign whole target dates per species to a chronological diagnostic split."""
    species_ids = sorted(
        {str(episode.get("species_id") or "") for episode in episodes}
    )
    partitions: dict[str, str] = {}
    for species_id in species_ids:
        species_episodes = [
            episode
            for episode in episodes
            if str(episode.get("species_id") or "") == species_id
        ]
        dates = sorted(
            {str(episode.get("observed_at") or "") for episode in species_episodes}
        )
        if not dates:
            continue
        n_train_dates = max(1, int(len(dates) * TRAIN_RATIO))
        train_dates = set(dates[:n_train_dates])
        for episode in species_episodes:
            partitions[_episode_id(episode)] = (
                "train"
                if str(episode.get("observed_at") or "") in train_dates
                else "test"
            )
    return partitions


def _partition_episodes(episodes: Sequence[dict[str, Any]]) -> dict[str, str]:
    """Return deterministic 70/30 class-stratified partitions grouped by date."""
    chronological = _chronological_partitions(episodes)
    partitions: dict[str, str] = {}
    species_ids = sorted(
        {str(episode.get("species_id") or "") for episode in episodes}
    )
    for species_id in species_ids:
        species_episodes = [
            episode
            for episode in episodes
            if str(episode.get("species_id") or "") == species_id
        ]
        by_date: dict[str, list[dict[str, Any]]] = {}
        for episode in species_episodes:
            by_date.setdefault(str(episode.get("observed_at") or ""), []).append(episode)
        groups: list[tuple[str, int, int]] = []
        for target_date, group in by_date.items():
            favorable = sum(
                episode.get("prediction_target") == "favorable" for episode in group
            )
            groups.append((target_date, favorable, len(group) - favorable))
        groups.sort(
            key=lambda item: hashlib.sha256(
                f"{PARTITION_SEED}|{species_id}|{item[0]}".encode("utf-8")
            ).hexdigest()
        )
        total_favorable = sum(group[1] for group in groups)
        total_unfavorable = sum(group[2] for group in groups)
        target_fraction = 1.0 - TRAIN_RATIO
        target_favorable = round(total_favorable * target_fraction)
        target_unfavorable = round(total_unfavorable * target_fraction)
        target_total = round(len(species_episodes) * target_fraction)

        states: dict[tuple[int, int], tuple[str, ...]] = {(0, 0): ()}
        for target_date, favorable, unfavorable in groups:
            expanded = dict(states)
            for (current_favorable, current_unfavorable), selected_dates in states.items():
                key = (
                    current_favorable + favorable,
                    current_unfavorable + unfavorable,
                )
                expanded.setdefault(key, selected_dates + (target_date,))
            states = expanded
        candidates = [
            (counts, selected_dates)
            for counts, selected_dates in states.items()
            if 0 < counts[0] < total_favorable
            and 0 < counts[1] < total_unfavorable
        ]
        if candidates:
            (_counts, selected_test_dates) = min(
                candidates,
                key=lambda item: (
                    abs(item[0][0] - target_favorable)
                    + abs(item[0][1] - target_unfavorable),
                    abs(sum(item[0]) - target_total),
                    len(item[1]),
                    item[1],
                ),
            )
            test_dates = set(selected_test_dates)
            for episode in species_episodes:
                partitions[_episode_id(episode)] = (
                    "test"
                    if str(episode.get("observed_at") or "") in test_dates
                    else "train"
                )
        else:
            for episode in species_episodes:
                episode_id = _episode_id(episode)
                partitions[episode_id] = chronological[episode_id]
    return partitions


def build_benchmark(
    rows: list[dict[str, Any]],
    micro_area_to_area: dict[str, str],
    horizons: Iterable[int] = DEFAULT_HORIZONS,
    feature_set_id: str = LAG_EVENT_V1.feature_set_id,
    area_representative_altitudes: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return a frozen benchmark payload; no estimator is fitted here."""
    if feature_set_id not in FEATURE_SETS:
        raise ValueError(f"Unknown feature_set_id: {feature_set_id}")
    feature_set = FEATURE_SETS[feature_set_id]
    horizon_values = tuple(sorted(set(int(value) for value in horizons)))
    if not horizon_values or horizon_values[0] < 1:
        raise ValueError("At least one horizon >= 1 day is required")

    species_ids = sorted({str(row.get("species_id")) for row in rows if row.get("species_id")})
    all_episodes: list[dict[str, Any]] = []
    for species_id in species_ids:
        all_episodes.extend(
            aggregate_to_area_episodes(
                filter_eligible(rows, species_id),
                micro_area_to_area,
                area_representative_altitudes,
            )
        )
    partitions = _partition_episodes(all_episodes)
    chronological_partitions = _chronological_partitions(all_episodes)

    samples: list[dict[str, Any]] = []
    for episode in all_episodes:
        episode_id = (
            f"{episode.get('species_id')}|{episode.get('area_id')}|{episode.get('observed_at')}"
        )
        fixed_gap_ids = {
            FIXED_GAP_7D_V1.feature_set_id,
            FIXED_GAP_7D_ALTITUDE_V2.feature_set_id,
        }
        sample_horizons = (7,) if feature_set_id in fixed_gap_ids else horizon_values
        for horizon_days in sample_horizons:
            if feature_set_id == FIXED_GAP_7D_V1.feature_set_id:
                features, metadata = build_fixed_gap_7d_features(episode)
                sample_suffix = "fixed_gap_7d"
            elif feature_set_id == FIXED_GAP_7D_ALTITUDE_V2.feature_set_id:
                features, metadata = build_fixed_gap_7d_altitude_features(episode)
                sample_suffix = "fixed_gap_7d_altitude_v2"
            elif feature_set_id == LAG_EVENT_ALTITUDE_V2.feature_set_id:
                features, metadata = build_lag_event_altitude_features(
                    episode, horizon_days
                )
                sample_suffix = f"altitude_v2_h{horizon_days}"
            else:
                features, metadata = build_lag_event_features(episode, horizon_days)
                metadata["feature_set_id"] = LAG_EVENT_V1.feature_set_id
                sample_suffix = f"h{horizon_days}"
            samples.append(
                {
                    "sample_id": f"{episode_id}|{sample_suffix}",
                    "episode_id": episode_id,
                    "species_id": episode.get("species_id"),
                    "area_id": episode.get("area_id"),
                    "prediction_target": episode.get("prediction_target"),
                    "partition": partitions[episode_id],
                    "chronological_partition": chronological_partitions[episode_id],
                    "features": features,
                    "metadata": metadata,
                }
            )

    eligible_episode_ids = {
        str(sample["episode_id"])
        for sample in samples
        if bool(sample.get("metadata", {}).get("training_eligible"))
    }
    eligible_episodes = [
        episode
        for episode in all_episodes
        if _episode_id(episode) in eligible_episode_ids
    ]
    eligible_partitions = _partition_episodes(eligible_episodes)
    eligible_chronological = _chronological_partitions(eligible_episodes)
    for sample in samples:
        episode_id = str(sample["episode_id"])
        if not bool(sample.get("metadata", {}).get("training_eligible")):
            sample["partition"] = "excluded"
            sample["chronological_partition"] = "excluded"
            continue
        sample["partition"] = eligible_partitions[episode_id]
        sample["chronological_partition"] = eligible_chronological[episode_id]

    return {
        "schema_version": "1.0",
        "kind": "mushroom_ml_benchmark",
        "generated_at": datetime.now(UTC).isoformat(),
        "temporal_contract": "P(target_at_T | observed_weather_through_T_minus_horizon)",
        "partition_contract": (
            "deterministic_stratified_70_30_grouped_by_species_and_target_date_seed_42"
        ),
        "chronological_diagnostic_contract": (
            "chronological_target_dates_70_30_grouped_by_species_and_target_date"
        ),
        "weather_contract": ctx.weather_contract_metadata(),
        "feature_set": {
            "id": feature_set.feature_set_id,
            "description": feature_set.description,
            "feature_cols": list(feature_set.feature_cols),
            "max_lookback_days": feature_set.max_lookback_days,
            "thresholds_inherited_from_v0": {
                "rain_event_mm": RAIN_EVENT_THRESHOLD_MM,
                "significant_rain_mm": SIGNIFICANT_RAIN_THRESHOLD_MM,
                **(
                    {}
                    if feature_set_id
                    in {
                        FIXED_GAP_7D_ALTITUDE_V2.feature_set_id,
                        LAG_EVENT_ALTITUDE_V2.feature_set_id,
                    }
                    else {"heat_stress_c": HEAT_STRESS_THRESHOLD_C}
                ),
            },
            "temperature_contract": (
                {
                    "id": "station_to_area_representative_altitude_v1",
                    "lapse_rate_c_per_100m": TEMPERATURE_LAPSE_RATE_C_PER_100M,
                    "area_altitude_method": "mean_of_all_materialized_micro_area_dem_means",
                    "global_heat_stress_threshold_removed": True,
                }
                if feature_set_id
                in {
                    FIXED_GAP_7D_ALTITUDE_V2.feature_set_id,
                    LAG_EVENT_ALTITUDE_V2.feature_set_id,
                }
                else {"id": "raw_station_temperature_v1"}
            ),
        },
        "horizons": (
            [7]
            if feature_set_id
            in {
                FIXED_GAP_7D_V1.feature_set_id,
                FIXED_GAP_7D_ALTITUDE_V2.feature_set_id,
            }
            else list(horizon_values)
        ),
        "episode_count": len(all_episodes),
        "sample_count": len(samples),
        "training_eligible_sample_count": sum(
            bool(sample.get("metadata", {}).get("training_eligible"))
            for sample in samples
        ),
        "samples": samples,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a frozen mushroom ML benchmark dataset.")
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--known-sites", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizons", nargs="+", type=int, default=list(DEFAULT_HORIZONS))
    parser.add_argument(
        "--feature-set",
        choices=sorted(FEATURE_SETS),
        default=LAG_EVENT_ALTITUDE_V2.feature_set_id,
    )
    args = parser.parse_args()

    payload = build_benchmark(
        load_features(args.features),
        load_micro_area_to_area(args.known_sites),
        args.horizons,
        args.feature_set,
        load_area_representative_altitudes(args.known_sites),
    )
    payload["source"] = {
        "features_path": str(args.features),
        "features_sha256": _sha256(args.features),
        "known_sites_path": str(args.known_sites),
        "known_sites_sha256": _sha256(args.known_sites),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Benchmark saved to: {args.output}")


if __name__ == "__main__":
    main()
