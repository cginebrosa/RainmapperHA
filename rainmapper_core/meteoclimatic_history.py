"""Maintain raw Meteoclimatic observations and derive daily Rainmapper rows.

Meteoclimatic RSS readings are snapshots. Rainmapper's public incremental CSV
is daily, keyed by station and local date, so keeping only that file overwrites
earlier same-day wind observations. This module stores raw observations first
and then rebuilds daily rows with computed wind summaries.
"""

import pandas as pd

from rainmapper_core.wind import circular_mean_degrees, optional_float, optional_round


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


def _aggregate_optional(series, operation, decimals=1):
    values = _numeric_series(series).dropna()
    if values.empty:
        return pd.NA
    if operation == "max":
        return round(float(values.max()), decimals)
    if operation == "min":
        return round(float(values.min()), decimals)
    if operation == "mean":
        return round(float(values.mean()), decimals)
    raise ValueError(f"Unsupported Meteoclimatic aggregation: {operation}")


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

    grouped_rows = []
    for (_, local_date), group in observations.groupby(["Codi Estació", "Data Local"], sort=False):
        group = group.sort_values("Data Lectura")
        last = group.iloc[-1]
        current_wind = _numeric_series(group["wind_avg_kmh"]).dropna()
        grouped_rows.append(
            {
                "Codi Estació": last["Codi Estació"],
                "Data Lectura": last["Data Lectura"],
                "Estació": last["Estació"],
                "Comarca": last["Comarca"],
                "Municipi": last["Municipi"],
                "Provincia": last["Provincia"],
                "Altitud": last["Altitud"],
                "Latitud": last["Latitud"],
                "Longitud": last["Longitud"],
                "Ultima Lectura": last["Ultima Lectura"],
                "Variable": last["Variable"],
                "Total": optional_round(last["Total"]),
                "Unitat": last["Unitat"],
                "max_temp_celsius": last["max_temp_celsius"],
                "min_temp_celsius": last["min_temp_celsius"],
                "max_humidity_percent": last["max_humidity_percent"],
                "min_humidity_percent": last["min_humidity_percent"],
                "Data Local": local_date,
                "Hora Local": last["Hora Local"],
                "wind_avg_kmh": _aggregate_optional(group["wind_avg_kmh"], "mean"),
                "wind_min_kmh": _aggregate_optional(group["wind_avg_kmh"], "min"),
                "wind_max_kmh": _aggregate_optional(group["wind_avg_kmh"], "max"),
                "wind_gust_kmh": _aggregate_optional(group["wind_gust_kmh"], "max"),
                "wind_direction_deg": circular_mean_degrees(group["wind_direction_deg"]),
                "wind_gust_direction_deg": pd.NA,
                "wind_observation_count": int(current_wind.count()),
                "wind_source_height_m": pd.NA,
            }
        )

    result = pd.DataFrame(grouped_rows, columns=OBSERVATION_COLUMNS)
    result = result.sort_values(["Codi Estació", "Data Local"], ascending=[True, False])
    return result.reset_index(drop=True)
