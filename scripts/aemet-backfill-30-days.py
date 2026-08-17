#!/usr/bin/env python3
"""Build a local AEMET daily backfill CSV for manual Home Assistant upload.

This script is intentionally separate from the normal AEMET updater. The normal
pipeline uses recent hourly observations and maintains an hourly incremental
history. This helper uses AEMET's daily climatology endpoint for closed days, so
it can fill a short historical window without pretending to have hourly data.

Safety rules:
- Output is written to a timestamped directory under tmp/ by default.
- The script never writes to Rainmapper's Data directory unless the operator
  explicitly passes such a directory with --output-dir.
- Existing enriched station metadata can be preserved by passing the current
  estacions_aemet.csv with --station-catalog.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core.create_aemet import (
    AEMET_STATION_PREFIX,
    DAILY_COLUMNS,
    STATION_COLUMNS,
    AemetRateLimitError,
    fetch_json,
    first_non_empty,
    parse_optional_float,
    read_csv_if_exists,
)


AEMET_DAILY_URL_TEMPLATE = (
    "https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/"
    "fechaini/{start}T00:00:00UTC/fechafin/{end}T23:59:59UTC/todasestaciones"
)
AEMET_STATION_INVENTORY_URL = (
    "https://opendata.aemet.es/opendata/api/valores/climatologicos/"
    "inventarioestaciones/todasestaciones"
)
MAX_DAILY_RANGE_DAYS = 15


def fetch_indexed_payload(url, api_key, timeout=30, request_label="AEMET indexed endpoint"):
    """Fetch an AEMET indexed endpoint and then fetch its short-lived data URL."""
    if not api_key:
        raise ValueError("AEMET API key is required")
    index = fetch_json(url, api_key=api_key, timeout=timeout, request_label=f"{request_label} index")
    if int(index.get("estado", 0)) != 200 or not index.get("datos"):
        raise RuntimeError(f"AEMET did not return a data URL: {index}")
    return fetch_json(index["datos"], timeout=timeout, request_label=f"{request_label} data")


def build_daily_url(start_date, end_date):
    """Return the AEMET daily climatology URL for an inclusive date range."""
    return AEMET_DAILY_URL_TEMPLATE.format(
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )


def split_date_ranges(start_date, end_date, max_days=MAX_DAILY_RANGE_DAYS):
    """Split an inclusive date range into AEMET-compatible chunks."""
    ranges = []
    current = start_date
    while current <= end_date:
        chunk_end = min(current + timedelta(days=max_days - 1), end_date)
        ranges.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return ranges


def fetch_daily_climatology_rows(api_key, start_date, end_date, timeout=30):
    """Fetch daily climatology rows, respecting AEMET's maximum date window."""
    rows = []
    for chunk_start, chunk_end in split_date_ranges(start_date, end_date):
        rows.extend(
            fetch_indexed_payload(
                build_daily_url(chunk_start, chunk_end),
                api_key=api_key,
                timeout=timeout,
                request_label=f"AEMET daily climatology {chunk_start.isoformat()} to {chunk_end.isoformat()}",
            )
        )
    return rows


def parse_yyyymmdd(value):
    """Return a date from YYYY-MM-DD text."""
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def default_end_date():
    """Return yesterday because AEMET daily climatology is for closed days."""
    return date.today() - timedelta(days=1)


def default_output_dir():
    """Return a timestamped tmp directory for safe local backfill output."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("tmp") / f"aemet-backfill-{stamp}"


def parse_aemet_dms(value):
    """Convert AEMET compact DMS coordinates to decimal degrees."""
    if value is None or pd.isna(value):
        return pd.NA
    text = str(value).strip().upper()
    if not text:
        return pd.NA
    hemisphere = text[-1]
    digits = text[:-1]
    if hemisphere not in {"N", "S", "E", "W"} or not digits.isdigit():
        return pd.NA
    if len(digits) == 6:
        degrees_digits = 2
    elif len(digits) == 7:
        degrees_digits = 3
    else:
        return pd.NA
    degrees = int(digits[:degrees_digits])
    minutes = int(digits[degrees_digits : degrees_digits + 2])
    seconds = int(digits[degrees_digits + 2 : degrees_digits + 4])
    decimal = degrees + (minutes / 60) + (seconds / 3600)
    if hemisphere in {"S", "W"}:
        decimal *= -1
    return round(decimal, 6)


def parse_aemet_precipitation(value):
    """Return precipitation in mm, treating AEMET trace values as zero."""
    if value is None or pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if not text:
        return pd.NA
    if text.lower() in {"ip", "tr"}:
        return 0.0
    return parse_optional_float(text)


def station_code(aemet_id):
    """Return the Rainmapper AEMET station code for an official station id."""
    return f"{AEMET_STATION_PREFIX}{str(aemet_id).strip()}"


def normalize_station_catalog(stations_df):
    """Normalize an optional existing Rainmapper AEMET station catalog."""
    if stations_df is None or stations_df.empty:
        return pd.DataFrame(columns=STATION_COLUMNS)
    catalog = stations_df.copy()
    for column in STATION_COLUMNS:
        if column not in catalog.columns:
            catalog[column] = ""
    catalog["Codi Estació"] = catalog["Codi Estació"].astype("string").fillna("").str.strip()
    if "aemet_id" not in catalog.columns:
        catalog["aemet_id"] = catalog["Codi Estació"].str.replace(AEMET_STATION_PREFIX, "", regex=False)
    return catalog[STATION_COLUMNS]


def read_station_catalog_if_exists(path):
    """Read an existing station catalog preserving operator-maintained formatting."""
    if not path.exists():
        return pd.DataFrame(columns=STATION_COLUMNS)
    catalog = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in STATION_COLUMNS:
        if column not in catalog.columns:
            catalog[column] = ""
    return catalog[STATION_COLUMNS]


def normalize_inventory(rows):
    """Convert AEMET station inventory rows into Rainmapper station rows."""
    normalized = []
    for row in rows:
        aemet_id = str(row.get("indicativo") or "").strip()
        if not aemet_id:
            continue
        normalized.append(
            {
                "Codi Estació": station_code(aemet_id),
                "aemet_id": aemet_id,
                "Estació": str(row.get("nombre") or "").strip(),
                "Comarca": "",
                "Municipi": "",
                "Provincia": str(row.get("provincia") or "").strip(),
                "Altitud": parse_optional_float(row.get("altitud")),
                "Latitud": parse_aemet_dms(row.get("latitud")),
                "Longitud": parse_aemet_dms(row.get("longitud")),
            }
        )
    return pd.DataFrame(normalized, columns=STATION_COLUMNS).sort_values("Codi Estació").reset_index(drop=True)


def metadata_lookup(stations_df):
    """Return station metadata keyed by Rainmapper station code."""
    if stations_df is None or stations_df.empty:
        return {}
    return {
        str(row["Codi Estació"]): row
        for row in stations_df.to_dict(orient="records")
        if str(row.get("Codi Estació") or "").strip()
    }


def merge_station_catalog(inventory_df, existing_catalog_df):
    """Merge AEMET inventory with existing enriched Rainmapper station metadata."""
    inventory = normalize_station_catalog(inventory_df)
    existing = normalize_station_catalog(existing_catalog_df)
    existing_by_code = metadata_lookup(existing)
    merged = []
    for row in inventory.to_dict(orient="records"):
        previous = existing_by_code.get(str(row["Codi Estació"]), {})
        merged.append(
            {
                "Codi Estació": row["Codi Estació"],
                "aemet_id": first_non_empty(row.get("aemet_id"), previous.get("aemet_id")),
                "Estació": first_non_empty(previous.get("Estació"), row.get("Estació")),
                "Comarca": first_non_empty(previous.get("Comarca"), row.get("Comarca")),
                "Municipi": first_non_empty(previous.get("Municipi"), row.get("Municipi")),
                "Provincia": first_non_empty(previous.get("Provincia"), row.get("Provincia")),
                "Altitud": first_non_empty(previous.get("Altitud"), row.get("Altitud")),
                "Latitud": first_non_empty(previous.get("Latitud"), row.get("Latitud")),
                "Longitud": first_non_empty(previous.get("Longitud"), row.get("Longitud")),
            }
        )

    inventory_codes = {str(row["Codi Estació"]) for row in merged}
    for code, previous in existing_by_code.items():
        if code not in inventory_codes:
            merged.append(previous)

    return pd.DataFrame(merged, columns=STATION_COLUMNS).sort_values("Codi Estació").reset_index(drop=True)


def build_daily_incremental_from_climatology(rows, station_catalog_df):
    """Build Rainmapper daily incremental rows from AEMET daily climatology rows."""
    stations = metadata_lookup(station_catalog_df)
    output = []
    for row in rows:
        aemet_id = str(row.get("indicativo") or "").strip()
        fecha = str(row.get("fecha") or "").strip()
        total = parse_aemet_precipitation(row.get("prec"))
        temp_max = parse_optional_float(row.get("tmax"))
        temp_min = parse_optional_float(row.get("tmin"))
        humidity_max = parse_optional_float(row.get("hrMax"))
        humidity_min = parse_optional_float(row.get("hrMin"))
        if not aemet_id or not fecha:
            continue
        # AEMET can publish temperature and humidity for a station/day while
        # omitting ``prec``.  Rainmapper used to discard the complete day in
        # that situation and also ignored hrMax/hrMin unconditionally.  Keep
        # every day with at least one modeled measurement; missing rain stays
        # missing and is never fabricated as zero.
        if all(
            pd.isna(value)
            for value in (total, temp_max, temp_min, humidity_max, humidity_min)
        ):
            continue
        try:
            reading_date = parse_yyyymmdd(fecha)
        except ValueError:
            continue

        code = station_code(aemet_id)
        station = stations.get(code, {})
        reading_text = f"{reading_date.strftime('%Y-%m-%d')} 23:59:00"
        output.append(
            {
                "Codi Estació": code,
                "Data Lectura": reading_text,
                "Estació": first_non_empty(station.get("Estació"), row.get("nombre")),
                "Comarca": first_non_empty(station.get("Comarca")),
                "Municipi": first_non_empty(station.get("Municipi")),
                "Provincia": first_non_empty(station.get("Provincia"), row.get("provincia")),
                "Altitud": first_non_empty(station.get("Altitud")),
                "Latitud": first_non_empty(station.get("Latitud")),
                "Longitud": first_non_empty(station.get("Longitud")),
                "Ultima Lectura": reading_date.strftime("%Y/%m/%d 23:59:00"),
                "Variable": "Precipitacion",
                "Total": round(float(total), 1) if not pd.isna(total) else pd.NA,
                "Unitat": "mm",
                "Data Local": reading_date.strftime("%Y%m%d"),
                "Hora Local": "23:59:00",
                "max_temp_celsius": temp_max,
                "min_temp_celsius": temp_min,
                "max_humidity_percent": humidity_max,
                "min_humidity_percent": humidity_min,
            }
        )
    if not output:
        return pd.DataFrame(columns=DAILY_COLUMNS)
    df = pd.DataFrame(output, columns=DAILY_COLUMNS)
    df = df.drop_duplicates(subset=["Codi Estació", "Data Local"], keep="last")
    return df.sort_values(["Codi Estació", "Data Local"], ascending=[True, False]).reset_index(drop=True)


def merge_existing_incremental(backfill_df, existing_df):
    """Merge optional existing AEMET daily history with the generated backfill."""
    if existing_df is None or existing_df.empty:
        return backfill_df.copy()
    existing = existing_df.copy()
    for column in DAILY_COLUMNS:
        if column not in existing.columns:
            existing[column] = pd.NA
    frames = [existing[DAILY_COLUMNS], backfill_df[DAILY_COLUMNS]]
    merged = pd.concat(frames, ignore_index=True)
    merged["Codi Estació"] = merged["Codi Estació"].astype("string").fillna("").str.strip()
    merged["Data Local"] = merged["Data Local"].astype("string").fillna("").str.strip()
    merged = merged.drop_duplicates(subset=["Codi Estació", "Data Local"], keep="last")
    return merged.sort_values(["Codi Estació", "Data Local"], ascending=[True, False]).reset_index(drop=True)


def write_backfill_outputs(output_dir, daily_incremental, station_catalog, summary):
    """Write generated CSV artifacts and a small machine-readable summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    daily_incremental.to_csv(output_dir / "Aemet_incremental.csv", index=False, decimal=",")
    station_catalog.to_csv(output_dir / "estacions_aemet.csv", index=False, decimal=",")
    with (output_dir / "aemet_backfill_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")


def run_backfill(
    api_key,
    days=30,
    end_date=None,
    output_dir=None,
    station_catalog_path=None,
    existing_incremental_path=None,
    timeout=30,
    skip_inventory=False,
):
    """Fetch AEMET daily data and write local backfill CSV outputs."""
    if days < 1:
        raise ValueError("--days must be at least 1")
    if skip_inventory and not station_catalog_path:
        raise ValueError("--skip-inventory requires --station-catalog")
    end_date = end_date or default_end_date()
    start_date = end_date - timedelta(days=days - 1)
    output_dir = Path(output_dir or default_output_dir())

    daily_rows = fetch_daily_climatology_rows(api_key, start_date, end_date, timeout=timeout)
    existing_stations = read_station_catalog_if_exists(Path(station_catalog_path)) if station_catalog_path else None
    if skip_inventory:
        station_catalog = normalize_station_catalog(existing_stations)
    else:
        inventory_rows = fetch_indexed_payload(
            AEMET_STATION_INVENTORY_URL,
            api_key=api_key,
            timeout=timeout,
            request_label="AEMET station inventory",
        )
        inventory = normalize_inventory(inventory_rows)
        station_catalog = merge_station_catalog(inventory, existing_stations)
    backfill = build_daily_incremental_from_climatology(daily_rows, station_catalog)
    existing_incremental = (
        read_csv_if_exists(Path(existing_incremental_path), DAILY_COLUMNS, decimal=",")
        if existing_incremental_path
        else None
    )
    daily_incremental = merge_existing_incremental(backfill, existing_incremental)
    summary = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily_api_rows": len(daily_rows),
        "backfill_rows": len(backfill),
        "daily_incremental_rows": len(daily_incremental),
        "station_rows": len(station_catalog),
        "output_dir": str(output_dir),
        "used_existing_incremental": bool(existing_incremental_path),
        "used_existing_station_catalog": bool(station_catalog_path),
        "skipped_inventory": skip_inventory,
    }
    write_backfill_outputs(output_dir, daily_incremental, station_catalog, summary)
    return summary


def parse_args():
    """Parse CLI arguments for local backfill usage."""
    parser = argparse.ArgumentParser(
        description="Download AEMET daily climatology and build Aemet_incremental.csv for manual HA upload."
    )
    parser.add_argument("--api-key", default=os.environ.get("AEMET_API_KEY") or os.environ.get("RAINMAPPER_AEMET_API_KEY"))
    parser.add_argument("--days", type=int, default=30, help="Inclusive number of closed days to fetch. Default: 30.")
    parser.add_argument(
        "--end-date",
        type=parse_yyyymmdd,
        default=None,
        help="Last closed day to fetch as YYYY-MM-DD. Default: yesterday.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated CSV files. Default: tmp/aemet-backfill-<timestamp>.",
    )
    parser.add_argument(
        "--station-catalog",
        type=Path,
        help="Optional existing estacions_aemet.csv to preserve enriched municipality/province metadata.",
    )
    parser.add_argument(
        "--existing-incremental",
        type=Path,
        help="Optional existing Aemet_incremental.csv to merge with the generated 30-day backfill.",
    )
    parser.add_argument(
        "--skip-inventory",
        action="store_true",
        help="Use --station-catalog as the complete station catalog and skip the AEMET inventory request.",
    )
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args()


def main():
    """Run the local AEMET backfill helper."""
    args = parse_args()
    try:
        summary = run_backfill(
            api_key=args.api_key,
            days=args.days,
            end_date=args.end_date,
            output_dir=args.output_dir,
            station_catalog_path=args.station_catalog,
            existing_incremental_path=args.existing_incremental,
            timeout=args.timeout,
            skip_inventory=args.skip_inventory,
        )
    except (AemetRateLimitError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        print(f"AEMET backfill failed: {exc}", file=sys.stderr)
        return 1

    print(
        "AEMET backfill finished: "
        f"{summary['backfill_rows']} generated daily row(s), "
        f"{summary['station_rows']} station row(s), "
        f"output: {summary['output_dir']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
