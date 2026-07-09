"""Maintain raw Meteoclimatic observations and derive daily Rainmapper rows.

Meteoclimatic RSS readings are snapshots. Rainmapper's public incremental CSV
is daily, keyed by station and local date, so keeping only that file overwrites
earlier same-day wind observations. This module stores raw observations first
and then rebuilds daily rows with computed wind summaries.
"""

import numpy as np
import pandas as pd


OBSERVATION_KEY = ["Codi Estació", "Data Lectura"]

OBSERVATION_COLUMNS = [
    "Codi Estació",
    "Data Lectura",
    "Estació",
    "Comarca",
    "Municipi",
    "Provincia",
    "Altitud",
    "Latitud",
    "Longitud",
    "Ultima Lectura",
    "Variable",
    "Total",
    "Unitat",
    "max_temp_celsius",
    "min_temp_celsius",
    "max_humidity_percent",
    "min_humidity_percent",
    "Data Local",
    "Hora Local",
    "wind_avg_kmh",
    "wind_min_kmh",
    "wind_max_kmh",
    "wind_gust_kmh",
    "wind_direction_deg",
    "wind_gust_direction_deg",
    "wind_observation_count",
    "wind_source_height_m",
]

OBSERVATION_STRING_COLUMNS = [
    "Codi Estació",
    "Estació",
    "Comarca",
    "Municipi",
    "Provincia",
    "Altitud",
    "Latitud",
    "Longitud",
    "Ultima Lectura",
    "Variable",
    "Unitat",
    "Data Local",
    "Hora Local",
]


def read_meteoclimatic_observations(path):
    """Read raw Meteoclimatic observations without pandas chunk inference."""
    dtype = {column: "string" for column in OBSERVATION_STRING_COLUMNS}
    return pd.read_csv(path, decimal=",", dtype=dtype, low_memory=False)


def normalize_observation_frame(df):
    """Return Meteoclimatic observations with a stable schema and key types."""
    normalized = df.copy()
    for column in OBSERVATION_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    normalized = normalized[OBSERVATION_COLUMNS]
    normalized["Codi Estació"] = normalized["Codi Estació"].astype("string").fillna("").str.strip()
    normalized["Data Lectura"] = pd.to_datetime(normalized["Data Lectura"], errors="coerce")
    normalized["Data Local"] = normalized["Data Local"].astype("string").fillna("").str.strip()
    normalized["Hora Local"] = normalized["Hora Local"].astype("string").fillna("").str.strip()
    return normalized.dropna(subset=["Data Lectura"]).reset_index(drop=True)


def update_meteoclimatic_observations(current_df, existing_df):
    """Append fresh observations and deduplicate by station and timestamp."""
    frames = [
        normalize_observation_frame(frame)
        for frame in (existing_df, current_df)
        if frame is not None and not frame.empty
    ]
    if not frames:
        return pd.DataFrame(columns=OBSERVATION_COLUMNS)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=OBSERVATION_KEY, keep="last")
    combined = combined.sort_values(["Codi Estació", "Data Lectura"], ascending=[True, False])
    return combined.reset_index(drop=True)


def _numeric_series(series):
    return pd.to_numeric(series, errors="coerce")


def build_meteoclimatic_daily_incremental(observations_df):
    """Build one daily Rainmapper row per station from raw Meteoclimatic rows.

    Rain and temperature/humidity fields keep Meteoclimatic's latest same-day
    snapshot semantics. Wind is aggregated from all raw observations available
    for that station/day: average/min/max current speed, maximum reported wind,
    and circular mean direction.
    """
    observations = normalize_observation_frame(observations_df)
    if observations.empty:
        return pd.DataFrame(columns=OBSERVATION_COLUMNS)

    key_columns = ["Codi Estació", "Data Local"]
    observations = observations.sort_values([*key_columns, "Data Lectura"])
    grouped = observations.groupby(key_columns, sort=False, dropna=True)

    last_rows = grouped.tail(1).copy()
    last_rows["Total"] = _numeric_series(last_rows["Total"]).round(1)

    wind_avg = _numeric_series(observations["wind_avg_kmh"])
    wind_gust = _numeric_series(observations["wind_gust_kmh"])
    wind_direction = _numeric_series(observations["wind_direction_deg"])

    wind_stats = pd.DataFrame({
        "wind_avg_kmh": wind_avg,
        "wind_gust_kmh": wind_gust,
    }, index=observations.index).groupby(
        [observations["Codi Estació"], observations["Data Local"]],
        sort=False,
        dropna=True,
    ).agg(
        wind_avg_kmh=("wind_avg_kmh", "mean"),
        wind_min_kmh=("wind_avg_kmh", "min"),
        wind_max_kmh=("wind_avg_kmh", "max"),
        wind_gust_kmh=("wind_gust_kmh", "max"),
        wind_observation_count=("wind_avg_kmh", "count"),
    ).round({
        "wind_avg_kmh": 1,
        "wind_min_kmh": 1,
        "wind_max_kmh": 1,
        "wind_gust_kmh": 1,
    })

    direction_radians = np.deg2rad(wind_direction)
    direction_components = pd.DataFrame({
        "sin": np.sin(direction_radians),
        "cos": np.cos(direction_radians),
    }, index=observations.index)
    direction_stats = direction_components.groupby(
        [observations["Codi Estació"], observations["Data Local"]],
        sort=False,
        dropna=True,
    ).sum(min_count=1)
    direction_angle = (np.degrees(np.arctan2(direction_stats["sin"], direction_stats["cos"])) % 360).round(1)
    zero_vector = np.isclose(direction_stats["sin"].fillna(0.0), 0.0, atol=1e-12) & np.isclose(
        direction_stats["cos"].fillna(0.0),
        0.0,
        atol=1e-12,
    )
    direction_angle = direction_angle.mask(direction_stats.isna().all(axis=1) | zero_vector)
    direction_angle = direction_angle.mask(np.isclose(direction_angle.fillna(0.0), 360.0), 0.0)
    direction_angle.name = "wind_direction_deg"

    result = last_rows.set_index(key_columns, drop=False)
    result.update(wind_stats)
    result["wind_direction_deg"] = direction_angle
    result["wind_gust_direction_deg"] = pd.NA
    result["wind_source_height_m"] = pd.NA
    result = result.reset_index(drop=True)
    result = result.sort_values(["Codi Estació", "Data Local"], ascending=[True, False])
    return result.reset_index(drop=True)
