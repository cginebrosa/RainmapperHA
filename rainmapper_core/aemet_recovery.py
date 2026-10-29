"""Refresh published daily OpenData values independently of hourly coverage.

Recent hourly aggregates are provisional. Published climatology values for the
same AEMET date override them, including downward corrections. The precipitation
period is AEMET's 07-07 UTC day; values are not reinterpreted as local 00-24 totals.
Only official OpenData endpoints are used. No web fallback or refresh cooldown.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import pandas as pd

UTC = timezone.utc
STATE_FILE = "Aemet_official_daily_state.json"
REPORT_FILE = "Aemet_official_daily_report.json"
SCHEMA = "aemet_opendata_daily_v1"
DEFAULT_REFRESH_DAYS = 30
MAX_REFRESH_DAYS = 30
MAX_STATIONS = 1200
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_STATE_BYTES = 8 * 1024 * 1024
REFRESH_TIMEOUT_SECONDS = 60
FIELDS = ("Total", "max_temp_celsius", "min_temp_celsius",
          "max_humidity_percent", "min_humidity_percent")
METADATA_FIELDS = ("Estació", "Provincia", "Altitud")


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def write_json(path, value, limit=MAX_STATE_BYTES):
    # Bound serialized state before allocating a file; avoid keeping hundreds
    # of thousands of tiny encoder chunks as separate Python objects on HA.
    payload = bytearray()
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    for chunk in encoder.iterencode(value):
        chunk = chunk.encode("utf-8")
        if len(payload) + len(chunk) > limit:
            raise ValueError("AEMET official daily state exceeds byte limit")
        payload.extend(chunk)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix="." + path.name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def load_state(data_dir):
    path = Path(data_dir) / STATE_FILE
    if not path.exists():
        return {"schema_version": SCHEMA, "precipitation_period": "07-07 UTC",
                "days": {}, "stations": {}}
    if path.stat().st_size > MAX_STATE_BYTES:
        raise ValueError("AEMET official daily state exceeds byte limit")
    state = json.loads(path.read_text())
    if (state.get("schema_version") != SCHEMA or not isinstance(state.get("days"), dict)
            or not isinstance(state.get("stations"), dict)):
        raise ValueError("Invalid AEMET official daily state")
    if len(state["days"]) > MAX_REFRESH_DAYS or len(state["stations"]) > MAX_STATIONS:
        raise ValueError("AEMET official daily state exceeds cardinality limit")
    for day, rows in state["days"].items():
        datetime.strptime(day, "%Y%m%d")
        if not isinstance(rows, dict) or len(rows) > MAX_STATIONS:
            raise ValueError("Invalid AEMET official day")
        for values in rows.values():
            if not isinstance(values, dict) or any(k not in FIELDS or number(v) is None for k, v in values.items()):
                raise ValueError("Invalid AEMET official values")
            if number(values.get("Total", 0)) < 0:
                raise ValueError("Invalid AEMET official precipitation")
    return state


def recover(data_dir, hourly, station_catalog, *, api_key, local_timezone="Europe/Madrid",
            now=None, refresh_days=None, fetcher=None):
    """Fetch every date in the rolling window, even when local rows are complete.

    Reuse the existing historical OpenData adapter, in sequential blocks of at
    most 15 days. Each runner rechecks the window; missing/failed responses keep
    previously confirmed fields. No hourly rows are changed by daily refresh.
    """
    from rainmapper_core import create_aemet as aemet
    from rainmapper_core.weather_official_backfill import (
        MAX_BACKFILL_DAYS, fetch_aemet_climatology, normalize_aemet_climatology,
    )

    refresh_days = int(refresh_days if refresh_days is not None else os.environ.get(
        "RAINMAPPER_AEMET_DAILY_REFRESH_DAYS", DEFAULT_REFRESH_DAYS))
    if not 7 <= refresh_days <= MAX_REFRESH_DAYS:
        raise ValueError("AEMET daily refresh days must be between 7 and 30")
    now = (now or datetime.now(UTC)).astimezone(UTC)
    today = now.astimezone(ZoneInfo(local_timezone)).date()
    start = today - timedelta(days=refresh_days)
    end = today - timedelta(days=1)
    state = load_state(data_dir)
    state["days"] = {d: rows for d, rows in state["days"].items()
                     if start.strftime("%Y%m%d") <= d <= end.strftime("%Y%m%d")}
    report = {"schema_version": SCHEMA, "checked_at": now.isoformat(),
              "start_date": start.isoformat(), "end_date": end.isoformat(),
              "requests": 0, "download_bytes": 0, "api_rows": 0,
              "blocks": [], "errors": []}
    deadline = time.monotonic() + REFRESH_TIMEOUT_SECONDS
    query = fetcher or fetch_aemet_climatology

    def bounded_fetch(url, **kwargs):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "opendata.aemet.es":
            raise ValueError("AEMET daily refresh requires an official HTTPS OpenData URL")
        report["requests"] += 1
        def record_phase(event, details):
            if event == "aemet_download_complete":
                report["download_bytes"] += details["bytes"]
        return aemet.fetch_json(url, **kwargs, deadline=deadline,
                                max_response_bytes=MAX_RESPONSE_BYTES,
                                phase_callback=record_phase)

    cursor = start
    while cursor <= end:
        block_end = min(end, cursor + timedelta(days=MAX_BACKFILL_DAYS - 1))
        block = {"start_date": cursor.isoformat(), "end_date": block_end.isoformat()}
        try:
            if time.monotonic() >= deadline:
                raise TimeoutError("AEMET daily refresh time budget exhausted")
            raw = query(cursor, block_end, api_key=api_key, timeout=30,
                        fetcher=bounded_fetch, allow_empty=True)
            if len(raw) > MAX_STATIONS * MAX_BACKFILL_DAYS:
                raise ValueError("AEMET daily response exceeds row limit")
            codes = {str(row.get("indicativo", "")) for row in raw}
            if len(codes) > MAX_STATIONS:
                raise ValueError("AEMET daily response exceeds station limit")
            frame = normalize_aemet_climatology(raw, station_catalog)
            frame = frame.loc[frame["Data Local"].between(cursor.strftime("%Y%m%d"), block_end.strftime("%Y%m%d"))]
            report["api_rows"] += len(frame)
            for row in frame[["Codi Estació", "Data Local", *FIELDS, *METADATA_FIELDS]].to_dict("records"):
                code, day = row["Codi Estació"], row["Data Local"]
                values = {field: number(row[field]) for field in FIELDS if number(row[field]) is not None}
                if values.get("Total", 0) < 0:
                    values.pop("Total")
                if not values:
                    continue
                state["days"].setdefault(day, {}).setdefault(code, {}).update(values)
                metadata = {field: str(row[field]) for field in METADATA_FIELDS if not aemet.is_empty_value(row[field])}
                state["stations"].setdefault(code, {}).update(metadata)
            block.update(status="ok", rows=len(frame))
        except (OSError, ValueError, RuntimeError) as exc:
            # Error class only: avoid leaking API keys or temporary data URLs.
            block.update(status="error", error=type(exc).__name__)
            report["errors"].append(dict(block))
            report["blocks"].append(block)
            break  # no retry loop or extra calls after a provider failure
        report["blocks"].append(block)
        cursor = block_end + timedelta(days=1)
    active_codes = {code for rows in state["days"].values() for code in rows}
    state["stations"] = {code: row for code, row in state["stations"].items() if code in active_codes}
    if len(active_codes) > MAX_STATIONS:
        raise ValueError("AEMET official daily cache exceeds station limit")
    state["checked_at"] = now.isoformat()
    report["official_rows"] = sum(len(rows) for rows in state["days"].values())
    report["official_rain_rows"] = sum("Total" in values for rows in state["days"].values() for values in rows.values())
    report["official_dates"] = sorted(state["days"])
    report["awaiting_publication_dates"] = [
        (start + timedelta(days=i)).isoformat() for i in range(refresh_days)
        if (start + timedelta(days=i)).strftime("%Y%m%d") not in state["days"]]
    report["status"] = "pending" if report["errors"] else "complete"
    report["message"] = (f"AEMET OpenData daily refresh: {report['official_rows']} official rows; "
                         f"{len(report['official_dates'])} published dates; "
                         f"{len(report['awaiting_publication_dates'])} dates awaiting publication; "
                         f"{len(report['errors'])} failed blocks.")
    write_json(Path(data_dir) / STATE_FILE, state)
    write_json(Path(data_dir) / REPORT_FILE, report, 64 * 1024)
    return hourly, state, report


def apply_verified(daily, state, catalog):
    """Official nonempty fields win over provisional rows, even if they are lower."""
    from rainmapper_core import create_aemet as aemet

    rows = []
    for day, stations in state.get("days", {}).items():
        stamp = datetime.strptime(day, "%Y%m%d")
        for code, values in stations.items():
            metadata = {**state["stations"].get(code, {}),
                        **{k: v for k, v in catalog.get(code, {}).items() if not aemet.is_empty_value(v)}}
            row = {key: value for key, value in metadata.items() if key in aemet.DAILY_COLUMNS}
            row.update({"Codi Estació": code, "Data Local": day,
                        "Data Lectura": stamp.strftime("%Y-%m-%d 23:59:00"),
                        "Ultima Lectura": stamp.strftime("%Y/%m/%d 23:59:00"),
                        "Hora Local": "23:59:00", "Variable": "Precipitacion", "Unitat": "mm"})
            row.update(values)
            rows.append(row)
    if not rows:
        return daily
    keys = ["Codi Estació", "Data Local"]
    official = pd.DataFrame(rows).set_index(keys)
    combined = official.combine_first(daily.set_index(keys)).reset_index()
    for column in aemet.DAILY_COLUMNS:
        if column not in combined:
            combined[column] = pd.NA
    # Daily-only stations have altitude from API/cache, while hourly stations
    # have floats. Pending Parquet capture requires one numeric dtype.
    for column in ("Altitud", "Latitud", "Longitud"):
        combined[column] = pd.to_numeric(combined[column], errors="coerce")
    return combined[aemet.DAILY_COLUMNS].sort_values(keys, ascending=[True, False]).reset_index(drop=True)


def status(data_dir):
    path = Path(data_dir) / REPORT_FILE
    if not path.exists():
        return {}
    if path.stat().st_size > 64 * 1024:
        return {"recovery_status": "error", "recovery_message": "Daily refresh report exceeds size limit"}
    report = json.loads(path.read_text())
    return {"recovery_status": report["status"], "recovery_message": report["message"],
            "official_daily_rows": report["official_rows"],
            "official_daily_rain_rows": report["official_rain_rows"],
            "official_latest_date": max(report["official_dates"], default=None),
            "official_awaiting_publication_dates": report["awaiting_publication_dates"]}
