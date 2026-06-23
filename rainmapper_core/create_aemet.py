"""Fetch AEMET OpenData observations and maintain Rainmapper CSV snapshots.

This module is intentionally isolated from the main Rainmapper runner while the
AEMET source is validated. It fetches the global "current observations" endpoint
once, stores the hourly observations, deduplicates the hourly history and builds
a daily incremental CSV compatible with the existing Tomap builder schema.
"""

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from rainmapper_core.config import const as rainmapper_const
from rainmapper_core.geocoding import GeocodingError, extract_google_metadata, googlemaps_station_metadata


AEMET_OBSERVATIONS_URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"
AEMET_STATION_PREFIX = "AEMET:"
LOCAL_TIMEZONE = "Europe/Madrid"

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


class AemetRateLimitError(RuntimeError):
    """Raised when AEMET reports that the client is sending too many requests."""


def parse_aemet_timestamp(value):
    """Parse AEMET UTC timestamps such as 2026-06-22T13:00:00+0000."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def fetch_json(url, api_key=None, timeout=30):
    """Fetch JSON from AEMET, optionally adding the OpenData API key header."""
    headers = {"Accept": "application/json"}
    if api_key:
        headers["api_key"] = api_key
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_payload = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise AemetRateLimitError("AEMET returned 429 Too Many Requests") from exc
        raise
    try:
        payload = raw_payload.decode("utf-8")
    except UnicodeDecodeError:
        payload = raw_payload.decode("latin-1")
    return json.loads(payload)


def fetch_observations(api_key, timeout=30):
    """Fetch the global AEMET observations payload using a single API call."""
    if not api_key:
        raise ValueError("AEMET API key is required")
    index = fetch_json(AEMET_OBSERVATIONS_URL, api_key=api_key, timeout=timeout)
    if int(index.get("estado", 0)) != 200 or not index.get("datos"):
        raise RuntimeError(f"AEMET did not return an observations URL: {index}")
    return fetch_json(index["datos"], timeout=timeout)


def normalize_observations(rows, local_timezone=LOCAL_TIMEZONE):
    """Convert AEMET observation rows into normalized hourly Rainmapper rows."""
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
        normalized.append(
            {
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
        )
    return pd.DataFrame(normalized, columns=HOURLY_COLUMNS)


def read_csv_if_exists(path, columns, decimal="."):
    """Read a CSV if it exists, otherwise return an empty dataframe."""
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path, decimal=decimal)
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


def coordinates_match(left_lat, left_lon, right_lat, right_lon):
    """Return True when two station coordinate pairs are effectively the same."""
    try:
        return abs(float(left_lat) - float(right_lat)) < 0.000001 and abs(float(left_lon) - float(right_lon)) < 0.000001
    except (TypeError, ValueError):
        return False


def update_hourly_incremental(current_hourly, existing_hourly):
    """Append new AEMET hourly observations and deduplicate by station and UTC time."""
    frames = [df for df in (existing_hourly, current_hourly) if not df.empty]
    if not frames:
        return pd.DataFrame(columns=HOURLY_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["aemet_id", "fint_utc"], keep="last")
    combined = combined.sort_values(["station_code", "reading_utc"], ascending=[True, False])
    return combined.reset_index(drop=True)


def build_station_catalog(hourly_df, existing_stations=None):
    """Build or refresh estacions_aemet.csv while preserving manual metadata."""
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
    """Fill missing AEMET station metadata using Google Maps reverse geocoding."""
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
    """Aggregate hourly AEMET history into daily rows compatible with Tomap."""
    if hourly_df.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    df = hourly_df.copy()
    df["rain_mm"] = pd.to_numeric(df["rain_mm"], errors="coerce").fillna(0.0)
    for column in ("temp_celsius", "humidity_percent"):
        if column not in df.columns:
            df[column] = pd.NA
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["reading_local_dt"] = pd.to_datetime(df["reading_local"], errors="coerce")
    df = df.dropna(subset=["reading_local_dt", "local_date", "station_code"])
    if df.empty:
        return pd.DataFrame(columns=DAILY_COLUMNS)

    grouped_rows = []
    stations = station_lookup(stations_df)
    for (_, local_date), group in df.groupby(["station_code", "local_date"], sort=False):
        group = group.sort_values("reading_local_dt")
        last = group.iloc[-1]
        station = stations.get(str(last["station_code"]), {})
        total = round(float(group["rain_mm"].sum()), 1)
        reading_local = last["reading_local_dt"]
        grouped_rows.append(
            {
                "Codi Estació": last["station_code"],
                "Data Lectura": reading_local.strftime("%Y-%m-%d %H:%M:%S"),
                "Estació": first_non_empty(station.get("Estació"), last.get("station_name", "")),
                "Comarca": first_non_empty(station.get("Comarca")),
                "Municipi": first_non_empty(station.get("Municipi")),
                "Provincia": first_non_empty(station.get("Provincia")),
                "Altitud": first_non_empty(station.get("Altitud"), last.get("alt_m", "")),
                "Latitud": first_non_empty(station.get("Latitud"), last.get("lat", "")),
                "Longitud": first_non_empty(station.get("Longitud"), last.get("lon", "")),
                "Ultima Lectura": reading_local.strftime("%Y/%m/%d %H:%M:%S"),
                "Variable": "Precipitacion",
                "Total": total,
                "Unitat": "mm",
                "Data Local": local_date,
                "Hora Local": reading_local.strftime("%H:%M:%S"),
                "max_temp_celsius": aggregate_optional_numeric(group["temp_celsius"], "max"),
                "min_temp_celsius": aggregate_optional_numeric(group["temp_celsius"], "min"),
                "max_humidity_percent": aggregate_optional_numeric(group["humidity_percent"], "max"),
                "min_humidity_percent": aggregate_optional_numeric(group["humidity_percent"], "min"),
            }
        )

    result = pd.DataFrame(grouped_rows, columns=DAILY_COLUMNS)
    result = result.sort_values(["Codi Estació", "Data Local"], ascending=[True, False])
    return result.reset_index(drop=True)


def write_outputs(data_dir, current_hourly, hourly_incremental, station_catalog, daily_incremental):
    """Write AEMET current, hourly incremental and daily incremental CSV files."""
    data_dir.mkdir(parents=True, exist_ok=True)
    current_daily = build_daily_incremental(current_hourly, station_catalog)
    current_hourly.to_csv(data_dir / "Aemet.csv", index=False)
    current_daily.to_csv(data_dir / "Aemet_current_daily.csv", index=False, decimal=",")
    hourly_incremental.to_csv(data_dir / "Aemet_hourly_incremental.csv", index=False)
    station_catalog.to_csv(data_dir / "estacions_aemet.csv", index=False, decimal=",")
    daily_incremental.to_csv(data_dir / "Aemet_incremental.csv", index=False, decimal=",")


def run_update(
    data_dir,
    api_key,
    local_timezone=LOCAL_TIMEZONE,
    timeout=30,
    enrich_stations=True,
    gmap_api_key=None,
    reverse_geocoder=reverse_geocode_station,
):
    """Fetch AEMET observations and update all AEMET CSV outputs."""
    data_dir = Path(data_dir)
    observations = fetch_observations(api_key=api_key, timeout=timeout)
    current_hourly = normalize_observations(observations, local_timezone=local_timezone)
    existing_hourly = read_csv_if_exists(data_dir / "Aemet_hourly_incremental.csv", HOURLY_COLUMNS)
    hourly_incremental = update_hourly_incremental(current_hourly, existing_hourly)
    existing_stations = read_csv_if_exists(data_dir / "estacions_aemet.csv", STATION_COLUMNS, decimal=",")
    station_catalog = build_station_catalog(hourly_incremental, existing_stations)
    enriched_station_rows = 0
    if enrich_stations:
        station_catalog, enriched_station_rows = enrich_station_catalog(
            station_catalog,
            gmap_api_key,
            reverse_geocoder=reverse_geocoder,
        )
    daily_incremental = build_daily_incremental(hourly_incremental, station_catalog)
    write_outputs(data_dir, current_hourly, hourly_incremental, station_catalog, daily_incremental)
    return {
        "current_hourly_rows": len(current_hourly),
        "hourly_incremental_rows": len(hourly_incremental),
        "station_rows": len(station_catalog),
        "enriched_station_rows": enriched_station_rows,
        "daily_incremental_rows": len(daily_incremental),
        "stations": int(daily_incremental["Codi Estació"].nunique()) if not daily_incremental.empty else 0,
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
