"""Fetch AEMET OpenData observations and maintain Rainmapper CSV snapshots.

This module is intentionally isolated from the main Rainmapper runner while the
AEMET source is validated. It fetches the global "current observations" endpoint
once, stores the hourly observations, deduplicates the hourly history and builds
a daily incremental CSV compatible with the existing Tomap builder schema.
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from rainmapper_core.config import const as rainmapper_const
from rainmapper_core.atomic_io import write_csv_atomic
from rainmapper_core.geocoding import extract_google_metadata, googlemaps_station_metadata
from rainmapper_core.wind import (
    WIND_COLUMNS,
    aemet_direction_to_degrees,
    first_valid,
    meters_per_second_to_kmh,
    normalize_direction_degrees,
)


AEMET_OBSERVATIONS_URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"
AEMET_STATION_PREFIX = "AEMET:"
AEMET_DATA_URL_DELAY_SECONDS = 1.0
AEMET_TOTAL_TIMEOUT_SECONDS = 90.0
AEMET_RATE_LIMIT_METRICS_FILE = "Aemet_rate_limit_metrics.json"
LOCAL_TIMEZONE = "Europe/Madrid"
AEMET_HOURLY_CLOSED_DAYS = 7

HOURLY_COLUMNS = [
    "aemet_id",
    "station_code",
    "station_name",
    "fint_utc",
    "reading_utc",
    "reading_local",
    "local_date",
    "local_time",
    "rain_mm",
    "temp_celsius",
    "humidity_percent",
    "wind_avg_kmh",
    "wind_min_kmh",
    "wind_max_kmh",
    "wind_gust_kmh",
    "wind_direction_deg",
    "wind_gust_direction_deg",
    "wind_observation_count",
    "wind_source_height_m",
    "lat",
    "lon",
    "alt_m",
]

DAILY_COLUMNS = [
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
    "Data Local",
    "Hora Local",
    "max_temp_celsius",
    "min_temp_celsius",
    "max_humidity_percent",
    "min_humidity_percent",
    *WIND_COLUMNS,
]

STATION_COLUMNS = [
    "Codi Estació",
    "aemet_id",
    "Estació",
    "Comarca",
    "Municipi",
    "Provincia",
    "Altitud",
    "Latitud",
    "Longitud",
]

CSV_TEXT_COLUMNS = {
    "aemet_id",
    "station_code",
    "station_name",
    "fint_utc",
    "reading_utc",
    "reading_local",
    "local_date",
    "local_time",
    "Codi Estació",
    "Data Lectura",
    "Estació",
    "Comarca",
    "Municipi",
    "Provincia",
    "Ultima Lectura",
    "Variable",
    "Unitat",
    "Data Local",
    "Hora Local",
}


class AemetRateLimitError(RuntimeError):
    """Raised when AEMET reports that the client is sending too many requests."""


class AemetTotalTimeoutError(TimeoutError):
    """Raised when the complete indexed AEMET download exceeds its deadline."""


def parse_aemet_timestamp(value):
    """Parse AEMET UTC timestamps such as 2026-06-22T13:00:00+0000."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def aemet_log_timestamp():
    """Return a local timestamp for AEMET request logs."""
    return datetime.now().isoformat(timespec="seconds")


def read_rate_limit_metrics(data_dir):
    """Read persisted AEMET 429 counters, tolerating missing or corrupt files."""
    path = Path(data_dir) / AEMET_RATE_LIMIT_METRICS_FILE
    if not path.exists():
        return {"events": [], "consecutive_429_runs": 0}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"events": [], "consecutive_429_runs": 0}
    events = payload.get("events")
    if not isinstance(events, list):
        events = []
    try:
        consecutive = int(payload.get("consecutive_429_runs", 0) or 0)
    except (TypeError, ValueError):
        consecutive = 0
    return {"events": [str(event) for event in events], "consecutive_429_runs": max(0, consecutive)}


def parse_metric_timestamp(value):
    """Parse metric timestamps written by Rainmapper as local naive datetimes."""
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def prune_recent_rate_limit_events(events, now=None):
    """Return AEMET 429 event timestamps that are inside the last 24 hours."""
    now = now or datetime.now()
    cutoff = now - timedelta(hours=24)
    recent = []
    for event in events:
        parsed = parse_metric_timestamp(event)
        if parsed is not None and parsed >= cutoff:
            recent.append(parsed.isoformat(timespec="seconds"))
    return recent


def write_rate_limit_metrics(data_dir, payload):
    """Persist AEMET 429 metrics atomically."""
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    path = data_path / AEMET_RATE_LIMIT_METRICS_FILE
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def record_rate_limit_result(data_dir, rate_limited, now=None):
    """Update persisted AEMET 429 counters for one completed AEMET run attempt."""
    now = now or datetime.now()
    metrics = read_rate_limit_metrics(data_dir)
    events = prune_recent_rate_limit_events(metrics.get("events", []), now=now)
    consecutive = int(metrics.get("consecutive_429_runs", 0) or 0)
    if rate_limited:
        events.append(now.isoformat(timespec="seconds"))
        consecutive += 1
    else:
        consecutive = 0
    payload = {
        "updated_at": now.isoformat(timespec="seconds"),
        "events": events,
        "rate_limit_24h": len(events),
        "consecutive_429_runs": consecutive,
    }
    write_rate_limit_metrics(data_dir, payload)
    return rate_limit_status(data_dir, now=now)


def rate_limit_status(data_dir, now=None):
    """Return AEMET 429 counters for status payloads and the HA WebUI."""
    now = now or datetime.now()
    metrics = read_rate_limit_metrics(data_dir)
    events = prune_recent_rate_limit_events(metrics.get("events", []), now=now)
    consecutive = int(metrics.get("consecutive_429_runs", 0) or 0)
    if len(events) != len(metrics.get("events", [])):
        payload = {
            "updated_at": now.isoformat(timespec="seconds"),
            "events": events,
            "rate_limit_24h": len(events),
            "consecutive_429_runs": consecutive,
        }
        write_rate_limit_metrics(data_dir, payload)
    return {
        "rate_limit_24h": len(events),
        "consecutive_429_runs": consecutive,
    }


def _aemet_phase(phase_callback, phase, details=None):
    safe_details = details or {}
    suffix = " ".join(f"{key}={value}" for key, value in safe_details.items())
    print(f"AEMET phase {phase}" + (f": {suffix}" if suffix else ""), flush=True)
    if phase_callback is not None:
        try:
            phase_callback(f"aemet_{phase}", safe_details)
        except Exception:
            pass


def _remaining_timeout(deadline, socket_timeout, request_label):
    if deadline is None:
        return float(socket_timeout)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise AemetTotalTimeoutError(
            f"AEMET total download deadline exceeded during {request_label}"
        )
    return max(0.001, min(float(socket_timeout), remaining))


def fetch_json(
    url,
    api_key=None,
    timeout=30,
    request_label="AEMET request",
    *,
    deadline=None,
    phase_callback=None,
):
    """Fetch JSON from AEMET, optionally adding the OpenData API key header."""
    headers = {"Accept": "application/json"}
    if api_key:
        headers["api_key"] = api_key
    request = urllib.request.Request(url, headers=headers)
    _aemet_phase(
        phase_callback,
        "request_start",
        {"request": request_label, "at": aemet_log_timestamp()},
    )
    request_started = time.monotonic()
    try:
        with urllib.request.urlopen(
            request,
            timeout=_remaining_timeout(deadline, timeout, request_label),
        ) as response:
            chunks = []
            while True:
                remaining_timeout = _remaining_timeout(
                    deadline, timeout, request_label
                )
                try:
                    response.fp.raw._sock.settimeout(remaining_timeout)
                except (AttributeError, OSError):
                    pass
                if hasattr(response, "read1"):
                    chunk = response.read1(64 * 1024)
                else:
                    chunk = response.read(64 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            raw_payload = b"".join(chunks)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise AemetRateLimitError(
                f"AEMET returned 429 Too Many Requests while fetching {request_label} "
                f"at {aemet_log_timestamp()}"
            ) from exc
        raise
    _remaining_timeout(deadline, timeout, request_label)
    _aemet_phase(
        phase_callback,
        "download_complete",
        {
            "request": request_label,
            "bytes": len(raw_payload),
            "elapsed_seconds": round(time.monotonic() - request_started, 3),
        },
    )
    _aemet_phase(
        phase_callback,
        "decode_start",
        {"request": request_label, "bytes": len(raw_payload)},
    )
    try:
        payload = raw_payload.decode("utf-8")
    except UnicodeDecodeError:
        payload = raw_payload.decode("latin-1")
    _remaining_timeout(deadline, timeout, request_label)
    _aemet_phase(
        phase_callback,
        "decode_complete",
        {"request": request_label, "characters": len(payload)},
    )
    _aemet_phase(
        phase_callback,
        "parse_start",
        {"request": request_label, "characters": len(payload)},
    )
    parsed = json.loads(payload)
    _remaining_timeout(deadline, timeout, request_label)
    _aemet_phase(
        phase_callback,
        "parse_complete",
        {
            "request": request_label,
            "records": len(parsed) if isinstance(parsed, (list, dict)) else None,
        },
    )
    return parsed


def fetch_observations(
    api_key,
    timeout=30,
    data_url_delay_seconds=AEMET_DATA_URL_DELAY_SECONDS,
    total_timeout=AEMET_TOTAL_TIMEOUT_SECONDS,
    phase_callback=None,
):
    """Fetch the global AEMET observations payload using one indexed API call.

    AEMET first returns a short-lived `datos` URL. The runtime path must keep
    this as a single global request sequence; calling per station would be slow
    and much more likely to hit OpenData rate limits.
    """
    if not api_key:
        raise ValueError("AEMET API key is required")
    deadline = time.monotonic() + max(0.001, float(total_timeout))
    index = fetch_json(
        AEMET_OBSERVATIONS_URL,
        api_key=api_key,
        timeout=timeout,
        request_label="observations index endpoint",
        deadline=deadline,
        phase_callback=phase_callback,
    )
    _remaining_timeout(deadline, timeout, "observations index endpoint")
    if int(index.get("estado", 0)) != 200 or not index.get("datos"):
        raise RuntimeError(f"AEMET did not return an observations URL: {index}")
    if data_url_delay_seconds and data_url_delay_seconds > 0:
        print(
            "AEMET waiting "
            f"{data_url_delay_seconds:.1f}s before fetching observations data URL."
        )
        if time.monotonic() + data_url_delay_seconds >= deadline:
            raise AemetTotalTimeoutError(
                "AEMET total download deadline exceeded before observations data URL"
            )
        time.sleep(data_url_delay_seconds)
    observations = fetch_json(
        index["datos"],
        timeout=timeout,
        request_label="observations data URL",
        deadline=deadline,
        phase_callback=phase_callback,
    )
    _remaining_timeout(deadline, timeout, "observations data URL")
    return observations


def normalize_observations(rows, local_timezone=LOCAL_TIMEZONE):
    """Convert AEMET observation rows into normalized hourly Rainmapper rows.

    AEMET's `fint` value is the UTC end time of the hourly observation. The
    hourly history stores both UTC and local timestamps so later aggregations can
    be explicit about day boundaries instead of treating the API payload as a
    complete local day.
    """
    tz = ZoneInfo(local_timezone)
    normalized = []
    for row in rows:
        station_id = str(row.get("idema") or "").strip()
        fint = str(row.get("fint") or "").strip()
        rain = row.get("prec")
        timestamp_utc = parse_aemet_timestamp(fint)
        if not station_id or timestamp_utc is None or not isinstance(rain, (int, float)):
            continue

        timestamp_local = timestamp_utc.astimezone(tz)
        # Prefix the official AEMET id to avoid collisions with existing source
        # station codes. Viewers may hide the prefix, but CSV identity keeps it.
        normalized_row = {
            "aemet_id": station_id,
            "station_code": f"{AEMET_STATION_PREFIX}{station_id}",
            "station_name": str(row.get("ubi") or "").strip(),
            "fint_utc": fint,
            "reading_utc": timestamp_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "reading_local": timestamp_local.strftime("%Y-%m-%d %H:%M:%S"),
            "local_date": timestamp_local.strftime("%Y%m%d"),
            "local_time": timestamp_local.strftime("%H:%M:%S"),
            "rain_mm": float(rain),
            "temp_celsius": parse_optional_float(row.get("ta")),
            "humidity_percent": parse_optional_float(row.get("hr")),
            "lat": row.get("lat"),
            "lon": row.get("lon"),
            "alt_m": row.get("alt"),
        }
        normalized_row.update(normalize_aemet_wind_fields(row))
        normalized.append(normalized_row)
    return pd.DataFrame(normalized, columns=HOURLY_COLUMNS)


def read_csv_if_exists(path, columns, decimal="."):
    """Read a CSV if it exists, otherwise return an empty dataframe."""
    if not path.exists():
        return pd.DataFrame(columns=columns)
    dtype = {column: "string" for column in columns if column in CSV_TEXT_COLUMNS}
    df = pd.read_csv(path, decimal=decimal, dtype=dtype, low_memory=False)
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA
    return df[columns]


def first_non_empty(*values):
    """Return the first value that is not null and not an empty string."""
    for value in values:
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text.lower() == "nan":
            continue
        if text:
            return value
    return ""


def parse_optional_float(value):
    """Return a float for optional AEMET numeric fields, or NA when unavailable."""
    if value is None or pd.isna(value):
        return pd.NA
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value or value.lower() == "nan":
            return pd.NA
    try:
        return float(value)
    except (TypeError, ValueError):
        return pd.NA


def normalize_aemet_wind_fields(row):
    """Return normalized wind fields from optional AEMET observation keys.

    The conventional observations endpoint may expose wind speed as `vv` and
    maximum gust as `vmax`; daily climatological payloads have also been seen
    with `velmedia`, `racha` and `dir`. Speeds are normalized from m/s to km/h,
    and direction values are decoded through AEMET's tens-of-degrees convention
    when applicable.
    """
    average_speed_ms = first_valid(row.get("vv"), row.get("velmedia"))
    gust_speed_ms = first_valid(row.get("vmax"), row.get("racha"))
    direction = normalize_direction_degrees(row.get("dv"))
    if pd.isna(direction):
        direction = aemet_direction_to_degrees(row.get("dir"))
    gust_direction = normalize_direction_degrees(row.get("dmax"))
    if pd.isna(gust_direction):
        gust_direction = aemet_direction_to_degrees(row.get("dir"))
    wind_avg = meters_per_second_to_kmh(average_speed_ms)
    wind_gust = meters_per_second_to_kmh(gust_speed_ms)
    wind_count = 1 if not pd.isna(first_valid(wind_avg, wind_gust, direction)) else 0
    return {
        "wind_avg_kmh": wind_avg,
        "wind_min_kmh": wind_avg,
        "wind_max_kmh": wind_avg,
        "wind_gust_kmh": wind_gust,
        "wind_direction_deg": direction,
        "wind_gust_direction_deg": gust_direction,
        "wind_observation_count": wind_count,
        "wind_source_height_m": pd.NA,
    }


def aggregate_optional_numeric(series, operation, decimals=1):
    """Aggregate optional numeric values and keep empty output when all are missing."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return pd.NA
    if operation == "max":
        return round(float(values.max()), decimals)
    if operation == "min":
        return round(float(values.min()), decimals)
    raise ValueError(f"Unsupported aggregation operation: {operation}")


def mean_optional_numeric(series, decimals=1):
    """Return the mean of optional numeric values, preserving empty output."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return pd.NA
    return round(float(values.mean()), decimals)


def non_empty_mask(series):
    """Return True for values that should be treated as present metadata."""
    return series.notna() & series.astype("string").str.strip().ne("") & series.astype("string").str.lower().ne("nan")


def coalesce_present(primary, fallback=None, default=""):
    """Return primary values when present, otherwise fallback/default values."""
    result = primary.copy() if isinstance(primary, pd.Series) else pd.Series(primary)
    mask = non_empty_mask(result)
    if fallback is None:
        return result.where(mask, default)
    fallback_values = fallback if isinstance(fallback, pd.Series) else pd.Series(fallback, index=result.index)
    return result.where(mask, fallback_values)


def circular_mean_grouped(df, group_keys, column, decimals=1):
    """Vectorized circular mean for a degree column grouped by station/day."""
    numeric = pd.to_numeric(df[column], errors="coerce")
    grouped = numeric.groupby([df[key] for key in group_keys], sort=False)
    counts = grouped.count()
    radians = np.deg2rad(numeric)
    sin_values = pd.Series(np.sin(radians), index=df.index).where(numeric.notna())
    cos_values = pd.Series(np.cos(radians), index=df.index).where(numeric.notna())
    sin_sum = sin_values.groupby([df[key] for key in group_keys], sort=False).sum()
    cos_sum = cos_values.groupby([df[key] for key in group_keys], sort=False).sum()
    angles = (np.rad2deg(np.arctan2(sin_sum, cos_sum)) % 360.0).round(decimals)
    angles = angles.mask(np.isclose(angles, 360.0), 0.0)
    empty_vectors = np.isclose(sin_sum, 0.0, atol=1e-12) & np.isclose(cos_sum, 0.0, atol=1e-12)
    return angles.mask((counts == 0) | empty_vectors, pd.NA)


def coordinates_match(left_lat, left_lon, right_lat, right_lon):
    """Return True when two station coordinate pairs are effectively the same."""
    try:
        return abs(float(left_lat) - float(right_lat)) < 0.000001 and abs(float(left_lon) - float(right_lon)) < 0.000001
    except (TypeError, ValueError):
        return False


def normalize_hourly_key_columns(df):
    """Normalize text key columns after reading hourly history from CSV.

    Pandas reads date-like columns such as `local_date` as integers when they
    come from disk, while freshly downloaded rows keep them as strings. Without
    this normalization a same visible value like 20260623 can become two groupby
    keys (`int` and `str`) and produce duplicate daily rows.
    """
    normalized = df.copy()
    for column in ("aemet_id", "station_code", "fint_utc", "reading_utc", "reading_local", "local_date", "local_time"):
        if column not in normalized.columns:
            normalized[column] = ""
        normalized[column] = normalized[column].astype("string").fillna("").str.strip()
    return normalized


def retain_hourly_incremental(
    hourly_df,
    *,
    local_timezone=LOCAL_TIMEZONE,
    reference_day=None,
    closed_days=AEMET_HOURLY_CLOSED_DAYS,
):
    """Keep complete local calendar days plus the current local day.

    The cutoff is a local midnight boundary, not a rolling number of hours. A
    seven-day policy therefore retains up to eight distinct dates: the seven
    previous closed dates and the current date in progress. Missing dates or
    stations are left missing; this function never creates zero-rain rows.
    """
    if closed_days < 0:
        raise ValueError("closed_days must be non-negative")

    normalized = normalize_hourly_key_columns(hourly_df)
    if normalized.empty:
        return normalized, {
            "closed_days": int(closed_days),
            "reference_local_date": None,
            "cutoff_local_date": None,
            "input_rows": 0,
            "output_rows": 0,
            "removed_rows": 0,
            "input_dates": 0,
            "output_dates": 0,
            "removed_dates": 0,
        }

    normalized["local_date"] = normalized["local_date"].str.replace(
        r"\.0$", "", regex=True
    )
    parsed_dates = pd.to_datetime(
        normalized["local_date"], format="%Y%m%d", errors="coerce"
    )
    valid_dates = parsed_dates.dropna()

    if reference_day is None:
        reference_day = datetime.now(ZoneInfo(local_timezone)).date()
        if not valid_dates.empty:
            reference_day = max(reference_day, valid_dates.max().date())
    elif isinstance(reference_day, datetime):
        reference_day = reference_day.date()

    cutoff_day = reference_day - timedelta(days=closed_days)
    keep = parsed_dates.ge(pd.Timestamp(cutoff_day))
    retained = normalized.loc[keep].copy()
    retained = retained.sort_values(
        ["station_code", "reading_utc"], ascending=[True, False]
    ).reset_index(drop=True)

    input_date_values = set(normalized.loc[parsed_dates.notna(), "local_date"])
    output_date_values = set(retained["local_date"])
    return retained, {
        "closed_days": int(closed_days),
        "reference_local_date": reference_day.isoformat(),
        "cutoff_local_date": cutoff_day.strftime("%Y%m%d"),
        "input_rows": int(len(normalized)),
        "output_rows": int(len(retained)),
        "removed_rows": int(len(normalized) - len(retained)),
        "input_dates": int(len(input_date_values)),
        "output_dates": int(len(output_date_values)),
        "removed_dates": int(len(input_date_values - output_date_values)),
    }


def update_hourly_incremental(current_hourly, existing_hourly):
    """Append new AEMET hourly observations and deduplicate by station and UTC time.

    The current endpoint only covers recent hours. Keeping a separate hourly
    history lets repeated runs gradually build full-day totals without assuming
    that a late-evening response still includes the morning.
    """
    frames = [df for df in (existing_hourly, current_hourly) if not df.empty]
    if not frames:
        return pd.DataFrame(columns=HOURLY_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    combined = normalize_hourly_key_columns(combined)
    combined = combined.drop_duplicates(subset=["aemet_id", "fint_utc"], keep="last")
    combined = combined.sort_values(["station_code", "reading_utc"], ascending=[True, False])
    return combined.reset_index(drop=True)


def build_station_catalog(hourly_df, existing_stations=None):
    """Build or refresh estacions_aemet.csv while preserving manual metadata.

    AEMET observations include coordinates and station names, but not the
    Rainmapper location fields used in popups and filters. Existing municipality,
    province and comarca values are preserved while coordinates stay unchanged,
    so manual or reverse-geocoded enrichment is not lost on every run.
    """
    if hourly_df.empty:
        return pd.DataFrame(columns=STATION_COLUMNS)

    df = hourly_df.copy()
    df["reading_utc_dt"] = pd.to_datetime(df["reading_utc"], errors="coerce")
    df = df.dropna(subset=["station_code"])
    latest = (
        df.sort_values(["station_code", "reading_utc_dt"], ascending=[True, False])
        .drop_duplicates(subset=["station_code"], keep="first")
    )
    current = pd.DataFrame(
        [
            {
                "Codi Estació": row["station_code"],
                "aemet_id": row["aemet_id"],
                "Estació": row["station_name"],
                "Comarca": "",
                "Municipi": "",
                "Provincia": "",
                "Altitud": row["alt_m"],
                "Latitud": row["lat"],
                "Longitud": row["lon"],
            }
            for row in latest.to_dict(orient="records")
        ],
        columns=STATION_COLUMNS,
    )

    if existing_stations is None or existing_stations.empty:
        return current.sort_values("Codi Estació").reset_index(drop=True)

    existing = existing_stations.copy()
    for column in STATION_COLUMNS:
        if column not in existing.columns:
            existing[column] = ""

    existing_by_code = {
        str(row["Codi Estació"]): row
        for row in existing[STATION_COLUMNS].to_dict(orient="records")
    }
    merged_rows = []
    for row in current.to_dict(orient="records"):
        previous = existing_by_code.get(str(row["Codi Estació"]), {})
        # If AEMET moves a station, old municipality/province may no longer be
        # valid. Preserve enriched metadata only while coordinates still match.
        preserve_location_metadata = coordinates_match(
            row.get("Latitud"),
            row.get("Longitud"),
            previous.get("Latitud"),
            previous.get("Longitud"),
        )
        previous_metadata = previous if preserve_location_metadata else {}
        merged_rows.append(
            {
                "Codi Estació": row["Codi Estació"],
                "aemet_id": first_non_empty(row.get("aemet_id"), previous.get("aemet_id")),
                "Estació": first_non_empty(row.get("Estació"), previous.get("Estació")),
                "Comarca": first_non_empty(previous_metadata.get("Comarca"), row.get("Comarca")),
                "Municipi": first_non_empty(previous_metadata.get("Municipi"), row.get("Municipi")),
                "Provincia": first_non_empty(previous_metadata.get("Provincia"), row.get("Provincia")),
                "Altitud": first_non_empty(row.get("Altitud"), previous.get("Altitud")),
                "Latitud": first_non_empty(row.get("Latitud"), previous.get("Latitud")),
                "Longitud": first_non_empty(row.get("Longitud"), previous.get("Longitud")),
            }
        )

    current_codes = {str(row["Codi Estació"]) for row in merged_rows}
    for code, previous in existing_by_code.items():
        if code not in current_codes:
            merged_rows.append(previous)

    return pd.DataFrame(merged_rows, columns=STATION_COLUMNS).sort_values("Codi Estació").reset_index(drop=True)


def station_lookup(stations_df):
    """Return a lookup dictionary keyed by station code."""
    if stations_df is None or stations_df.empty:
        return {}
    return {
        str(row["Codi Estació"]): row
        for row in stations_df.to_dict(orient="records")
    }


def is_empty_value(value):
    """Return True when a dataframe value should be treated as empty metadata."""
    if value is None or pd.isna(value):
        return True
    return str(value).strip() == "" or str(value).strip().lower() == "nan"


def reverse_geocode_station(lat, lon, gmap_api_key, language="ES"):
    """Return municipality, province and comarca-like metadata from Google Maps."""
    metadata = googlemaps_station_metadata(lat, lon, gmap_api_key, language=language)
    return {
        "Altitud": metadata.get("altitude", ""),
        "Comarca": metadata.get("comarca", ""),
        "Municipi": metadata.get("municipality", ""),
        "Provincia": metadata.get("province", ""),
    }


def enrich_station_catalog(stations_df, gmap_api_key, reverse_geocoder=reverse_geocode_station):
    """Fill missing AEMET station metadata using Google Maps reverse geocoding.

    This follows the same operational rule as the other sources: only call
    Google Maps when location metadata is missing. The function is injectable in
    tests so fixtures can validate behavior without external network calls.
    """
    if stations_df.empty:
        return stations_df.copy(), 0

    enriched = stations_df.copy()
    enriched_count = 0
    for index, station in enriched.iterrows():
        needs_metadata = any(is_empty_value(station.get(column)) for column in ("Municipi", "Provincia"))
        if not needs_metadata:
            continue
        lat = station.get("Latitud")
        lon = station.get("Longitud")
        if is_empty_value(lat) or is_empty_value(lon):
            continue

        metadata = reverse_geocoder(lat, lon, gmap_api_key)
        changed = False
        for column in ("Municipi", "Provincia", "Comarca"):
            if is_empty_value(enriched.at[index, column]) and metadata.get(column):
                enriched.at[index, column] = metadata[column]
                changed = True
        if is_empty_value(enriched.at[index, "Altitud"]) and metadata.get("Altitud"):
            enriched.at[index, "Altitud"] = metadata["Altitud"]
            changed = True
        if changed:
            enriched_count += 1

    return enriched, enriched_count


def build_daily_incremental(hourly_df, stations_df=None):
    """Aggregate hourly AEMET history into daily rows compatible with Tomap.

    Tomap expects one row per station and local date. This function is the
    boundary where the UTC hourly history becomes the existing daily incremental
    schema, including optional max/min weather fields when AEMET provided them.
    """
    if hourly_df.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    df = hourly_df.copy()
    df = normalize_hourly_key_columns(df)
    df["rain_mm"] = pd.to_numeric(df["rain_mm"], errors="coerce").fillna(0.0)
    for column in ("temp_celsius", "humidity_percent", *WIND_COLUMNS):
        if column not in df.columns:
            df[column] = pd.NA
        if column != "wind_source_height_m":
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df["reading_local_dt"] = pd.to_datetime(df["reading_local"], errors="coerce")
    df = df.dropna(subset=["reading_local_dt", "local_date", "station_code"])
    if df.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    group_keys = ["station_code", "local_date"]
    grouped = df.groupby(group_keys, sort=False)
    aggregates = grouped.agg(
        Total=("rain_mm", "sum"),
        max_temp_celsius=("temp_celsius", "max"),
        min_temp_celsius=("temp_celsius", "min"),
        max_humidity_percent=("humidity_percent", "max"),
        min_humidity_percent=("humidity_percent", "min"),
        wind_avg_kmh=("wind_avg_kmh", "mean"),
        wind_min_kmh=("wind_min_kmh", "min"),
        wind_max_kmh=("wind_max_kmh", "max"),
        wind_gust_kmh=("wind_gust_kmh", "max"),
        wind_observation_count=("wind_observation_count", "sum"),
    )
    aggregates["Total"] = aggregates["Total"].round(1)
    for column in (
        "max_temp_celsius",
        "min_temp_celsius",
        "max_humidity_percent",
        "min_humidity_percent",
        "wind_avg_kmh",
        "wind_min_kmh",
        "wind_max_kmh",
        "wind_gust_kmh",
    ):
        aggregates[column] = aggregates[column].round(1)
    aggregates["wind_direction_deg"] = circular_mean_grouped(df, group_keys, "wind_direction_deg")
    aggregates["wind_gust_direction_deg"] = circular_mean_grouped(df, group_keys, "wind_gust_direction_deg")
    aggregates["wind_observation_count"] = aggregates["wind_observation_count"].fillna(0).astype(int)
    aggregates = aggregates.reset_index()

    sorted_df = df.sort_values(["station_code", "local_date", "reading_local_dt"], ascending=[True, True, True])
    last_rows = sorted_df.drop_duplicates(subset=group_keys, keep="last")[
        [
            "station_code",
            "local_date",
            "station_name",
            "reading_local_dt",
            "local_time",
            "alt_m",
            "lat",
            "lon",
        ]
    ]
    result = pd.merge(aggregates, last_rows, on=group_keys, how="left")
    if stations_df is not None and not stations_df.empty:
        stations = stations_df.copy()
        for column in STATION_COLUMNS:
            if column not in stations.columns:
                stations[column] = ""
        stations = stations[STATION_COLUMNS].rename(columns={"Codi Estació": "station_code"})
        result = pd.merge(result, stations, on="station_code", how="left")
    else:
        for column in STATION_COLUMNS:
            if column == "Codi Estació":
                continue
            result[column] = ""

    result["Codi Estació"] = result["station_code"]
    result["Data Lectura"] = result["reading_local_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    result["Estació"] = coalesce_present(result["Estació"], result["station_name"])
    for column in ("Comarca", "Municipi", "Provincia"):
        result[column] = coalesce_present(result[column])
    result["Altitud"] = coalesce_present(result["Altitud"], result["alt_m"])
    result["Latitud"] = coalesce_present(result["Latitud"], result["lat"])
    result["Longitud"] = coalesce_present(result["Longitud"], result["lon"])
    result["Ultima Lectura"] = result["reading_local_dt"].dt.strftime("%Y/%m/%d %H:%M:%S")
    result["Variable"] = "Precipitacion"
    result["Unitat"] = "mm"
    result["Data Local"] = result["local_date"]
    result["Hora Local"] = result["reading_local_dt"].dt.strftime("%H:%M:%S")
    result["wind_source_height_m"] = pd.NA
    result = result[DAILY_COLUMNS]
    result = result.sort_values(["Codi Estació", "Data Local"], ascending=[True, False])
    return result.reset_index(drop=True)


def merge_daily_incremental(current_daily, existing_daily):
    """Merge generated AEMET daily rows with an existing daily CSV.

    Manual daily climatology backfills live only in `Aemet_incremental.csv`, not
    in the hourly history. Runtime updates must therefore preserve existing
    daily rows while replacing any station/day that the current hourly rebuild
    can calculate more recently.
    """
    frames = []
    for df in (existing_daily, current_daily):
        if df is None or df.empty:
            continue
        normalized = df.copy()
        for column in DAILY_COLUMNS:
            if column not in normalized.columns:
                normalized[column] = pd.NA
        normalized = normalized[DAILY_COLUMNS]
        normalized["Codi Estació"] = normalized["Codi Estació"].astype("string").fillna("").str.strip()
        normalized["Data Local"] = normalized["Data Local"].astype("string").fillna("").str.strip()
        frames.append(normalized)
    if not frames:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    merged = pd.concat([frame.dropna(axis=1, how="all") for frame in frames], ignore_index=True)
    for column in DAILY_COLUMNS:
        if column not in merged.columns:
            merged[column] = pd.NA
    merged = merged[DAILY_COLUMNS]
    merged = merged.drop_duplicates(subset=["Codi Estació", "Data Local"], keep="last")
    merged = merged.sort_values(["Codi Estació", "Data Local"], ascending=[True, False])
    return merged.reset_index(drop=True)


def write_outputs(
    data_dir,
    current_hourly,
    hourly_incremental,
    station_catalog,
    daily_incremental,
    *,
    write_daily_incremental=True,
):
    """Write every AEMET CSV artifact expected by local tests, HA and Tomap."""
    data_dir.mkdir(parents=True, exist_ok=True)
    current_daily = build_daily_incremental(current_hourly, station_catalog)
    write_csv_atomic(current_hourly, data_dir / "Aemet.csv")
    write_csv_atomic(current_daily, data_dir / "Aemet_current_daily.csv", decimal=",")
    write_csv_atomic(hourly_incremental, data_dir / "Aemet_hourly_incremental.csv")
    write_csv_atomic(station_catalog, data_dir / "estacions_aemet.csv", decimal=",")
    if write_daily_incremental:
        write_csv_atomic(daily_incremental, data_dir / "Aemet_incremental.csv", decimal=",")


def run_update(
    data_dir,
    api_key,
    local_timezone=LOCAL_TIMEZONE,
    timeout=30,
    enrich_stations=True,
    gmap_api_key=None,
    reverse_geocoder=reverse_geocode_station,
    total_timeout=AEMET_TOTAL_TIMEOUT_SECONDS,
    phase_callback=None,
    retention_reference_day=None,
):
    """Fetch AEMET observations and update all AEMET CSV outputs.

    This is the public entry point used by the standalone CLI and by the main
    Rainmapper runner. It deliberately keeps the operation order explicit:
    download current rows, merge the hourly history, refresh/enrich the station
    catalog, rebuild daily rows, then write all files.
    """
    data_dir = Path(data_dir)
    total_started = time.perf_counter()
    timings = {}
    phase_started = time.perf_counter()
    observations = fetch_observations(
        api_key=api_key,
        timeout=timeout,
        total_timeout=total_timeout,
        phase_callback=phase_callback,
    )
    timings["fetch_seconds"] = time.perf_counter() - phase_started
    _aemet_phase(
        phase_callback,
        "normalize_start",
        {"records": len(observations)},
    )
    phase_started = time.perf_counter()
    current_hourly = normalize_observations(observations, local_timezone=local_timezone)
    timings["normalize_seconds"] = time.perf_counter() - phase_started
    _aemet_phase(
        phase_callback,
        "normalize_complete",
        {
            "input_records": len(observations),
            "hourly_rows": len(current_hourly),
            "elapsed_seconds": round(timings["normalize_seconds"], 3),
        },
    )
    phase_started = time.perf_counter()
    existing_hourly = read_csv_if_exists(data_dir / "Aemet_hourly_incremental.csv", HOURLY_COLUMNS)
    timings["read_hourly_seconds"] = time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    merged_hourly = update_hourly_incremental(current_hourly, existing_hourly)
    timings["merge_hourly_seconds"] = time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    hourly_incremental, hourly_retention = retain_hourly_incremental(
        merged_hourly,
        local_timezone=local_timezone,
        reference_day=retention_reference_day,
    )
    timings["retain_hourly_seconds"] = time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    existing_stations = read_csv_if_exists(data_dir / "estacions_aemet.csv", STATION_COLUMNS, decimal=",")
    timings["read_stations_seconds"] = time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    station_catalog = build_station_catalog(hourly_incremental, existing_stations)
    timings["station_catalog_seconds"] = time.perf_counter() - phase_started
    enriched_station_rows = 0
    if enrich_stations:
        phase_started = time.perf_counter()
        station_catalog, enriched_station_rows = enrich_station_catalog(
            station_catalog,
            gmap_api_key,
            reverse_geocoder=reverse_geocoder,
        )
        timings["station_enrichment_seconds"] = time.perf_counter() - phase_started
    else:
        timings["station_enrichment_seconds"] = 0.0
    phase_started = time.perf_counter()
    rebuilt_daily = build_daily_incremental(hourly_incremental, station_catalog)
    timings["build_daily_seconds"] = time.perf_counter() - phase_started
    from rainmapper_core.weather_history_capture import (
        capture_fresh_weather_rows,
        partitioned_history_enabled,
    )

    partitioned_mode = partitioned_history_enabled()
    if partitioned_mode:
        # The archive/CSV close step owns the bounded 180-day merge.  Avoid
        # loading the former multi-million-row AEMET CSV in this source process.
        timings["read_daily_seconds"] = 0.0
        timings["merge_daily_seconds"] = 0.0
        daily_incremental = rebuilt_daily
    else:
        phase_started = time.perf_counter()
        existing_daily = read_csv_if_exists(data_dir / "Aemet_incremental.csv", DAILY_COLUMNS, decimal=",")
        timings["read_daily_seconds"] = time.perf_counter() - phase_started
        phase_started = time.perf_counter()
        daily_incremental = merge_daily_incremental(rebuilt_daily, existing_daily)
        timings["merge_daily_seconds"] = time.perf_counter() - phase_started
    # The reconstructed recent complete days are the touched AEMET rows.  The
    # pending must be durable before Aemet_incremental.csv is modified.
    capture_fresh_weather_rows(data_dir, "aemet", rebuilt_daily)
    phase_started = time.perf_counter()
    write_outputs(
        data_dir,
        current_hourly,
        hourly_incremental,
        station_catalog,
        daily_incremental,
        write_daily_incremental=not partitioned_mode,
    )
    timings["write_outputs_seconds"] = time.perf_counter() - phase_started
    timings["total_seconds"] = time.perf_counter() - total_started
    return {
        "current_hourly_rows": len(current_hourly),
        "hourly_incremental_rows": len(hourly_incremental),
        "hourly_retention": hourly_retention,
        "station_rows": len(station_catalog),
        "enriched_station_rows": enriched_station_rows,
        "daily_incremental_rows": len(daily_incremental),
        "stations": int(daily_incremental["Codi Estació"].nunique()) if not daily_incremental.empty else 0,
        "partitioned_history": partitioned_mode,
        "daily_updates": rebuilt_daily if partitioned_mode else None,
        "timings": timings,
    }


def default_data_dir():
    """Return the Rainmapper data directory from shared configuration."""
    return Path(rainmapper_const._DATA_PATH)


def parse_args():
    """Parse command-line options for standalone AEMET updates."""
    parser = argparse.ArgumentParser(description="Fetch AEMET OpenData observations into Rainmapper CSV files.")
    parser.add_argument("--data-dir", default=str(default_data_dir()), help="Directory where AEMET CSV files are stored.")
    parser.add_argument("--api-key", default=os.environ.get("AEMET_API_KEY") or os.environ.get("RAINMAPPER_AEMET_API_KEY"))
    parser.add_argument("--gmap-api-key", default=os.environ.get("GMAP_API_KEY") or os.environ.get("RAINMAPPER_GMAP_API_KEY"))
    parser.add_argument("--timezone", default=os.environ.get("RAINMAPPER_TIMEZONE", LOCAL_TIMEZONE))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--enrich-stations",
        action="store_true",
        default=True,
        help="Fill missing AEMET station municipality/province using Google Maps reverse geocoding. Enabled by default.",
    )
    parser.add_argument(
        "--skip-station-enrichment",
        dest="enrich_stations",
        action="store_false",
        help="Skip Google Maps reverse geocoding for AEMET station metadata.",
    )
    return parser.parse_args()


def main():
    """Run the standalone AEMET updater."""
    args = parse_args()
    try:
        summary = run_update(
            data_dir=args.data_dir,
            api_key=args.api_key,
            local_timezone=args.timezone,
            timeout=args.timeout,
            enrich_stations=args.enrich_stations,
            gmap_api_key=args.gmap_api_key,
        )
    except AemetRateLimitError as exc:
        print(f"AEMET skipped: {exc}")
        return 2
    print(
        "AEMET update finished: "
        f"{summary['current_hourly_rows']} current hourly row(s), "
        f"{summary['hourly_incremental_rows']} hourly incremental row(s), "
        f"{summary['station_rows']} station row(s), "
        f"{summary['enriched_station_rows']} enriched station row(s), "
        f"{summary['daily_incremental_rows']} daily row(s), "
        f"{summary['stations']} station(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
