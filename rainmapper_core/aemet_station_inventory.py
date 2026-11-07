"""Complete missing AEMET locations without replacing accepted station metadata."""

import time
from urllib.parse import urlsplit

import pandas as pd

from rainmapper_core.weather_coordinates import point, protect_frame


INVENTORY_URL = "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones"
MAX_BYTES = 512 * 1024
MAX_STATIONS = 1200
TIMEOUT_SECONDS = 30


def parse_coordinate(value, *, latitude):
    """Parse compact AEMET DMS, rejecting invalid axes, minutes and seconds."""
    text = str(value or "").strip().upper()
    if len(text) not in (7, 8) or text[-1:] not in ("NS" if latitude else "EW"):
        return None
    digits = text[:-1]
    if not digits.isascii() or not digits.isdigit():
        return None
    degrees, minutes, seconds = int(digits[:-4]), int(digits[-4:-2]), int(digits[-2:])
    value = degrees + minutes / 60 + seconds / 3600
    if minutes >= 60 or seconds >= 60 or value > (90 if latitude else 180):
        return None
    return round(-value if text[-1] in "SW" else value, 6)


def fetch_inventory(api_key):
    """One bounded global request sequence, with no station-by-station retries."""
    from rainmapper_core.create_aemet import fetch_json

    deadline = time.monotonic() + TIMEOUT_SECONDS
    index = fetch_json(INVENTORY_URL, api_key=api_key, deadline=deadline,
                       max_response_bytes=64 * 1024, request_label="station inventory index")
    if not isinstance(index, dict) or index.get("estado") != 200 or not index.get("datos"):
        raise ValueError("AEMET inventory unavailable")
    url = urlsplit(index["datos"])
    if url.scheme != "https" or url.netloc != "opendata.aemet.es":
        raise ValueError("AEMET inventory requires an official HTTPS data URL")
    rows = fetch_json(index["datos"], deadline=deadline, max_response_bytes=MAX_BYTES,
                      request_label="station inventory data")
    if not isinstance(rows, list) or len(rows) > MAX_STATIONS or any(not isinstance(r, dict) for r in rows):
        raise ValueError("Invalid AEMET inventory size or shape")
    return rows


def complete_station_catalog(data_dir, catalog, daily_stations, *, api_key):
    """Persist resolved locations through the caller's normal station CSV write.

    Existing valid coordinates are never replaced by the lower-precision
    inventory. Only missing stations/locations are requested and considered.
    The next run reuses the station CSV; unresolved codes retry next run.
    """
    from rainmapper_core import create_aemet as aemet

    entries = {str(r["Codi Estació"]): r for r in catalog.to_dict("records")}
    known = {code for code, row in entries.items()
             if point({"lat": row.get("Latitud"), "lon": row.get("Longitud")})}
    missing = (set(entries) | set(daily_stations)) - known
    report = {"requested_stations": len(missing), "resolved_stations": 0,
              "unresolved_stations": len(missing), "error": None}
    if missing:
        try:
            rows = fetch_inventory(api_key)
        except (OSError, ValueError, RuntimeError) as exc:
            # Avoid logging credential-bearing provider responses/URLs.
            report["error"] = type(exc).__name__
            rows = []
        candidates = []
        for row in rows:
            station_id = str(row.get("indicativo") or "").strip()
            code = aemet.AEMET_STATION_PREFIX + station_id
            if code not in missing:
                continue
            lat = parse_coordinate(row.get("latitud"), latitude=True)
            lon = parse_coordinate(row.get("longitud"), latitude=False)
            if lat is None or lon is None:
                continue
            candidates.append({"Codi Estació": code, "aemet_id": station_id,
                "Estació": row.get("nombre", ""), "Provincia": row.get("provincia", ""),
                "Municipi": "", "Comarca": "", "Altitud": aemet.parse_optional_float(row.get("altitud")),
                "Latitud": lat, "Longitud": lon})
        if candidates:
            fresh = pd.DataFrame(candidates, columns=aemet.STATION_COLUMNS).drop_duplicates("Codi Estació", keep="last")
            fresh = protect_frame(data_dir, "aemet", fresh, fresh=True).dropna(subset=["Latitud", "Longitud"])
            for row in fresh.to_dict("records"):
                code = row["Codi Estació"]
                previous = entries.get(code, {})
                # Without a previous location, retain labels already known
                # for this station. The guard owns any accepted-location hold.
                entries[code] = {k: aemet.first_non_empty(row.get(k), previous.get(k)) for k in aemet.STATION_COLUMNS}
                report["resolved_stations"] += 1
    report["unresolved_stations"] -= report["resolved_stations"]
    report["message"] = (f"AEMET station inventory: {report['resolved_stations']} locations completed; "
                         f"{report['unresolved_stations']} unresolved"
                         + (f" ({report['error']})" if report["error"] else "") + ".")
    result = pd.DataFrame(list(entries.values()), columns=aemet.STATION_COLUMNS)
    return result.dropna(subset=["Latitud", "Longitud"]).sort_values("Codi Estació").reset_index(drop=True), report
