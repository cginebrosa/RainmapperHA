"""Lossless station/day composition for Meteocat weather variables."""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from rainmapper_core.incremental_upsert import upsert_incremental


KEY_COLUMNS = ["Codi Estació", "Data Local"]


def meteocat_daily_query_bounds(start_utc: str, end_utc: str) -> tuple[str, str]:
    """Query whole UTC buckets for the requested local calendar date labels.

    The runner passes local midnight/end-of-day converted to UTC. XEMA queries
    aggregate by UTC day, so using those instants directly would publish a
    two-hour (one-hour in winter) first bucket as a complete historical day.
    Keep XEMA's existing UTC daily identity, also used by official backfills;
    this is not a conversion of XEMA aggregates into local-day measurements.
    """
    def local_date(value: str):
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        return instant.astimezone(ZoneInfo("Europe/Madrid")).date()

    start, end = local_date(start_utc), local_date(end_utc)
    if start > end:
        raise ValueError("Meteocat start date must not be after end date")
    return f"{start.isoformat()}T00:00:00", f"{end.isoformat()}T23:59:59.999"


def _ensure_local_day(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "Data Local" not in result.columns:
        result["Data Local"] = pd.NA
    if "Hora Local" not in result.columns:
        result["Hora Local"] = pd.NA
    if "Data Lectura" not in result.columns:
        return result
    parsed = pd.to_datetime(result["Data Lectura"], errors="coerce")
    missing_day = result["Data Local"].isna() | result["Data Local"].astype(str).str.strip().isin(("", "nan", "<NA>"))
    missing_time = result["Hora Local"].isna() | result["Hora Local"].astype(str).str.strip().isin(("", "nan", "<NA>"))
    result.loc[missing_day, "Data Local"] = parsed.loc[missing_day].dt.strftime("%Y%m%d")
    result.loc[missing_time, "Hora Local"] = parsed.loc[missing_time].dt.strftime("%H:%M:%S")
    return result


def combine_meteocat_daily_rows(
    rain_rows: pd.DataFrame,
    condition_rows: pd.DataFrame,
) -> pd.DataFrame:
    """Return the union of rain and condition station/days.

    A missing precipitation row must not erase temperature or humidity.  Rain
    remains null on a condition-only day; only an observed numeric zero is a
    dry-day measurement.
    """
    rain = _ensure_local_day(rain_rows)
    conditions = _ensure_local_day(condition_rows)
    if rain.empty and conditions.empty:
        columns = list(dict.fromkeys([*rain.columns, *conditions.columns]))
        return pd.DataFrame(columns=columns)
    if rain.empty:
        combined = conditions.copy()
    elif conditions.empty:
        combined = rain.copy()
    else:
        combined = upsert_incremental(conditions, rain, key_columns=KEY_COLUMNS)
    if "Variable" not in combined.columns:
        combined["Variable"] = pd.NA
    if "Unitat" not in combined.columns:
        combined["Unitat"] = pd.NA
    combined["Variable"] = combined["Variable"].fillna("Precipitació")
    combined["Unitat"] = combined["Unitat"].fillna("mm")
    return combined.sort_values(KEY_COLUMNS, ascending=[True, False]).reset_index(drop=True)
