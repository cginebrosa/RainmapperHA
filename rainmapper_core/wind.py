"""Helpers for normalized wind fields stored in Rainmapper CSV rows."""

import math

import pandas as pd


WIND_COLUMNS = [
    "wind_avg_kmh",
    "wind_min_kmh",
    "wind_max_kmh",
    "wind_gust_kmh",
    "wind_direction_deg",
    "wind_gust_direction_deg",
    "wind_observation_count",
    "wind_source_height_m",
]


COMPASS_TO_DEGREES = {
    "N": 0.0,
    "NNE": 22.5,
    "NE": 45.0,
    "ENE": 67.5,
    "E": 90.0,
    "ESE": 112.5,
    "SE": 135.0,
    "SSE": 157.5,
    "S": 180.0,
    "SSW": 202.5,
    "SW": 225.0,
    "WSW": 247.5,
    "W": 270.0,
    "WNW": 292.5,
    "NW": 315.0,
    "NNW": 337.5,
}


def optional_float(value):
    """Return a float or pandas NA for empty/non-numeric weather values."""
    if value is None or pd.isna(value):
        return pd.NA
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value or value.lower() in {"nan", "na", "none", "null", "--"}:
            return pd.NA
    try:
        return float(value)
    except (TypeError, ValueError):
        return pd.NA


def optional_round(value, decimals=1):
    """Round a numeric weather value while preserving missing values."""
    numeric = optional_float(value)
    if pd.isna(numeric):
        return pd.NA
    return round(float(numeric), decimals)


def first_valid(*values):
    """Return the first non-empty value from a preference-ordered list."""
    for value in values:
        numeric = optional_float(value)
        if not pd.isna(numeric):
            return numeric
    return pd.NA


def meters_per_second_to_kmh(value, decimals=1):
    """Convert wind speed from m/s to km/h while preserving missing values."""
    numeric = optional_float(value)
    if pd.isna(numeric):
        return pd.NA
    return round(float(numeric) * 3.6, decimals)


def normalize_direction_degrees(value):
    """Normalize numeric wind direction to degrees in the [0, 360) range."""
    numeric = optional_float(value)
    if pd.isna(numeric):
        return pd.NA
    return round(float(numeric) % 360.0, 1)


def aemet_direction_to_degrees(value):
    """Normalize AEMET direction values to degrees.

    AEMET climatological wind directions are commonly encoded as tens of
    degrees, while some observation payloads may already expose degrees. Values
    from 0 to 36 are treated as tens of degrees; larger values are treated as
    degrees directly.
    """
    numeric = optional_float(value)
    if pd.isna(numeric):
        return pd.NA
    direction = float(numeric)
    if 0 <= direction <= 36:
        direction *= 10
    return normalize_direction_degrees(direction)


def compass_to_degrees(value):
    """Convert Weather Underground compass direction labels to degrees."""
    if value is None or pd.isna(value):
        return pd.NA
    direction = str(value).strip().upper()
    if direction in {"", "CALM", "VARIABLE", "VAR", "VRB", "--"}:
        return pd.NA
    return COMPASS_TO_DEGREES.get(direction, pd.NA)


def circular_mean_degrees(values, decimals=1):
    """Return the circular mean for degree values, preserving wraparound."""
    numeric_values = [
        float(value)
        for value in (optional_float(item) for item in values)
        if not pd.isna(value)
    ]
    if not numeric_values:
        return pd.NA

    sin_sum = sum(math.sin(math.radians(value)) for value in numeric_values)
    cos_sum = sum(math.cos(math.radians(value)) for value in numeric_values)
    if math.isclose(sin_sum, 0.0, abs_tol=1e-12) and math.isclose(cos_sum, 0.0, abs_tol=1e-12):
        return pd.NA

    angle = round(math.degrees(math.atan2(sin_sum, cos_sum)) % 360.0, decimals)
    return 0.0 if math.isclose(angle, 360.0) else angle


def xema_daily_wind_fields(row):
    """Build normalized wind fields from Meteocat/XEMA daily variable columns."""
    height_specs = [
        (10, "1503", "1509", "1512", "1515"),
        (6, "1504", "1510", "1513", "1516"),
        (2, "1505", "1511", "1514", "1517"),
    ]

    avg_speed = first_valid(*(row.get(f"max_valor_variable_{speed_code}") for _, speed_code, _, _, _ in height_specs))
    direction = first_valid(*(row.get(f"max_valor_variable_{direction_code}") for _, _, direction_code, _, _ in height_specs))
    gust_speed = first_valid(*(row.get(f"max_valor_variable_{gust_code}") for _, _, _, gust_code, _ in height_specs))
    gust_direction = first_valid(*(row.get(f"max_valor_variable_{gust_direction_code}") for _, _, _, _, gust_direction_code in height_specs))

    source_height = pd.NA
    for height, speed_code, direction_code, gust_code, gust_direction_code in height_specs:
        if not pd.isna(first_valid(
            row.get(f"max_valor_variable_{speed_code}"),
            row.get(f"max_valor_variable_{direction_code}"),
            row.get(f"max_valor_variable_{gust_code}"),
            row.get(f"max_valor_variable_{gust_direction_code}"),
        )):
            source_height = height
            break

    wind_avg = meters_per_second_to_kmh(avg_speed)
    return {
        "wind_avg_kmh": wind_avg,
        "wind_gust_kmh": meters_per_second_to_kmh(gust_speed),
        "wind_direction_deg": normalize_direction_degrees(direction),
        "wind_gust_direction_deg": normalize_direction_degrees(gust_direction),
        "wind_observation_count": 0 if pd.isna(wind_avg) else 1,
        "wind_source_height_m": source_height,
    }
