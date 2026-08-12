"""Lightweight contracts shared by partitioned weather readers and writers.

This module intentionally depends only on PyArrow and the Python standard
library.  Operational archive processes must be able to import it without
loading pandas or the legacy monolithic weather pipeline.
"""

from __future__ import annotations

import math
import re
from typing import Any, Mapping

import pyarrow as pa


WEATHER_HISTORY_KEY = ["source", "station_code", "local_date"]
KNOWN_SOURCES = frozenset({"aemet", "meteocat", "meteoclimatic", "wunderground"})

LEGACY_TO_CANONICAL = {
    "Codi Estació": "station_code",
    "Data Lectura": "reading_datetime",
    "Estació": "station_name",
    "Comarca": "county",
    "Municipi": "municipality",
    "Provincia": "province",
    "Data Local": "local_date",
    "Hora Local": "local_time",
    "Latitud": "lat",
    "Longitud": "lon",
    "Altitud": "altitude",
    "Ultima Lectura": "last_reading",
    "Variable": "variable",
    "Total": "rain_mm",
    "Unitat": "unit",
    "max_temp_celsius": "max_temp_celsius",
    "min_temp_celsius": "min_temp_celsius",
    "max_humidity_percent": "max_humidity_percent",
    "min_humidity_percent": "min_humidity_percent",
    "wind_avg_kmh": "wind_avg_kmh",
    "wind_min_kmh": "wind_min_kmh",
    "wind_max_kmh": "wind_max_kmh",
    "wind_gust_kmh": "wind_gust_kmh",
    "wind_direction_deg": "wind_direction_deg",
    "wind_gust_direction_deg": "wind_gust_direction_deg",
    "wind_observation_count": "wind_observation_count",
    "wind_source_height_m": "wind_source_height_m",
}

WEATHER_HISTORY_COLUMNS = [
    "station_code",
    "reading_datetime",
    "station_name",
    "county",
    "municipality",
    "province",
    "local_date",
    "local_time",
    "lat",
    "lon",
    "altitude",
    "last_reading",
    "variable",
    "rain_mm",
    "unit",
    "max_temp_celsius",
    "min_temp_celsius",
    "max_humidity_percent",
    "min_humidity_percent",
    "wind_avg_kmh",
    "wind_min_kmh",
    "wind_max_kmh",
    "wind_gust_kmh",
    "wind_direction_deg",
    "wind_gust_direction_deg",
    "wind_observation_count",
    "wind_source_height_m",
    "source",
]

WEATHER_HISTORY_FLOAT_COLUMNS = frozenset(
    {
        "lat",
        "lon",
        "altitude",
        "rain_mm",
        "max_temp_celsius",
        "min_temp_celsius",
        "max_humidity_percent",
        "min_humidity_percent",
        "wind_avg_kmh",
        "wind_min_kmh",
        "wind_max_kmh",
        "wind_gust_kmh",
        "wind_direction_deg",
        "wind_gust_direction_deg",
        "wind_observation_count",
        "wind_source_height_m",
    }
)
WEATHER_HISTORY_STRING_COLUMNS = frozenset(WEATHER_HISTORY_COLUMNS).difference(
    WEATHER_HISTORY_FLOAT_COLUMNS
)
WEATHER_HISTORY_SCHEMA = pa.schema(
    [
        pa.field(
            column,
            pa.float64() if column in WEATHER_HISTORY_FLOAT_COLUMNS else pa.string(),
        )
        for column in WEATHER_HISTORY_COLUMNS
    ]
)

CATALOG_COLUMNS = (
    "source",
    "station_code",
    "station_name",
    "lat",
    "lon",
    "altitude",
    "first_date",
    "last_date",
    "metadata_date",
)
CATALOG_FLOAT_COLUMNS = frozenset({"lat", "lon", "altitude"})
CATALOG_SCHEMA = pa.schema(
    [
        pa.field(column, pa.float64() if column in CATALOG_FLOAT_COLUMNS else pa.string())
        for column in CATALOG_COLUMNS
    ]
)

DATA_SCHEMA_VERSION = "weather_daily_v1"
PENDING_SCHEMA_VERSION = "weather_history_pending_v1"
CURRENT_SCHEMA_VERSION = "weather_history_current_v1"
MANIFEST_SCHEMA_VERSION = "weather_history_manifest_v1"
DEFAULT_ROW_GROUP_SIZE = 8_192

_LOCAL_DATE_RE = re.compile(r"^[0-9]{8}$")


def normalize_scalar(column: str, value: Any) -> str | float | None:
    """Normalize one canonical value without importing pandas."""
    if value is None:
        return None
    if hasattr(value, "as_py"):
        value = value.as_py()
    if column in WEATHER_HISTORY_FLOAT_COLUMNS:
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
            if not value:
                return None
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric value for {column}: {value!r}") from exc
        if math.isnan(number):
            return None
        if not math.isfinite(number):
            raise ValueError(f"Non-finite numeric value for {column}: {value!r}")
        return number
    text = str(value).strip()
    if not text:
        return None
    if column == "local_date" and text.endswith(".0"):
        text = text[:-2]
    return text


def normalize_mapping(row: Mapping[str, Any], source: str) -> dict[str, Any]:
    """Return one exact-schema canonical row and validate its immutable key."""
    if source not in KNOWN_SOURCES:
        raise ValueError(f"Unknown weather source: {source!r}")
    canonical: dict[str, Any] = {}
    for column in WEATHER_HISTORY_COLUMNS:
        legacy = next(
            (name for name, target in LEGACY_TO_CANONICAL.items() if target == column),
            None,
        )
        raw = row.get(column)
        if raw is None and legacy is not None:
            raw = row.get(legacy)
        canonical[column] = normalize_scalar(column, raw)
    supplied_source = canonical["source"]
    if supplied_source is not None and supplied_source != source:
        raise ValueError(
            f"Row source {supplied_source!r} does not match adapter {source!r}"
        )
    canonical["source"] = source
    station = canonical["station_code"]
    local_date = canonical["local_date"]
    if not station or not local_date or not _LOCAL_DATE_RE.fullmatch(local_date):
        raise ValueError(
            f"Invalid canonical weather key: source={source!r}, "
            f"station_code={station!r}, local_date={local_date!r}"
        )
    return canonical


def weather_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return tuple(str(row[column]) for column in WEATHER_HISTORY_KEY)  # type: ignore[return-value]


def weather_partition_key(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["source"]), int(str(row["local_date"])[:4])
