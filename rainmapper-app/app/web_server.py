from __future__ import annotations

import argparse
import csv
import base64
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import signal
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


PLOTS_PATH = Path("/app/Plots")
TOMAP_PATH = Path("/app/Tomap")
DATA_PATH = Path("/app/Data")
PUBLIC_DATA_PATH = Path("/app/PublicData")
PUBLIC_PLOTS_PATH = Path("/config/www/Plots")
PUBLIC_PLOTS_TMP_PATH = Path("/config/www/.rainmapper-plots-tmp")
LEAFLET_VIEWER_ASSETS_PATH = Path("/app/rainmapper_core/viewers/leaflet-viewer")
PUBLIC_LEAFLET_PATH = Path("/config/www/rainmapper-leaflet")
PUBLIC_LEAFLET_TMP_PATH = Path("/config/www/.rainmapper-leaflet-tmp")
REMOVED_LEGACY_MOBILE_PATH = Path("/config/www/rainmapper-mobile")
MAPLIBRE_VIEWER_ASSETS_PATH = Path("/app/rainmapper_core/viewers/maplibre-viewer")
PUBLIC_MAPLIBRE_PATH = Path("/config/www/rainmapper-maplibre")
PUBLIC_MAPLIBRE_TMP_PATH = Path("/config/www/.rainmapper-maplibre-tmp")
PUBLIC_MAPLIBRE_AEMET_PATH = Path("/config/www/rainmapper-maplibre-aemet")
PUBLIC_MAPLIBRE_AEMET_TMP_PATH = Path("/config/www/.rainmapper-maplibre-aemet-tmp")
AEMET_EXPERIMENT_TOMAP_PATH = Path("/tmp/rainmapper-aemet-tomap")
AEMET_EXPERIMENT_DATA_PATH = Path("/tmp/rainmapper-aemet-publicdata")
LOG_PATH = Path("/share/rainmapper/last_run.log")
STATUS_PATH = Path("/share/rainmapper/status.txt")
USERS_JSON_PATH = Path("/share/rainmapper/users.json")
DEVICES_PATH = Path("/share/rainmapper/devices.json")
SOURCE_STATUS_PATH = Path("/app/Data/source_status.json")
STATIONS_PATH = Path("/app/stations.txt")
WUNDERGROUND_STATIONS_DB_PATH = Path("/app/Data/estacions_wunderground.csv")
AUTH_TOKEN_BYTES = 32
PASSWORD_HASH_ITERATIONS = 260_000
DEVICE_SETTING_PERIODS = {"01d.geojson", "07d.geojson", "14d.geojson", "21d.geojson", "30d.geojson", "60d.geojson", "90d.geojson"}
DEVICE_SETTING_MAP_STYLES = {"esri-satellite-vector", "esri-hybrid", "opentopomap", "openfreemap-liberty"}
DEVICE_SETTING_SOURCES = {"Meteocat", "Meteoclimatic", "Wunderground", "AEMET", "Unknown"}
DEVICE_SETTING_LANGUAGES = {"en", "es", "ca"}

PUBLIC_MAP_NAMES = {
    "01_Tomap_Last_day.html": "rain_01d.html",
    "02_Tomap_Last_week.html": "rain_07d.html",
    "03_Tomap_Last_two_weeks.html": "rain_14d.html",
    "04_Tomap_Last_three_weeks.html": "rain_21d.html",
    "05_Tomap_Last_month.html": "rain_30d.html",
    "06_Tomap_Last_two_months.html": "rain_60d.html",
    "07_Tomap_Last_three_months.html": "rain_90d.html",
}

RUN_LOCK = threading.Lock()
SHUTDOWN_EVENT = threading.Event()
CURRENT_PROCESS_LOCK = threading.Lock()
CURRENT_PROCESS: subprocess.Popen | None = None
RUN_STATE = {
    "running": False,
    "action": "",
    "started_at": "",
    "finished_at": "",
    "duration": "",
    "exit_code": "",
    "last_message": "Ready.",
    "current_step": "Idle",
    "progress_current": "",
    "progress_total": "",
    "progress_percent": "",
    "last_scheduled_key": "",
    "last_published_at": "",
    "last_publish_message": "Not published yet.",
}


def set_current_process(process: subprocess.Popen | None) -> None:
    global CURRENT_PROCESS
    with CURRENT_PROCESS_LOCK:
        CURRENT_PROCESS = process


def terminate_current_process() -> None:
    with CURRENT_PROCESS_LOCK:
        process = CURRENT_PROCESS

    if process is None or process.poll() is not None:
        return

    print(f"Terminating active Rainmapper subprocess {process.pid}.", flush=True)
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print(f"Killing active Rainmapper subprocess {process.pid}.", flush=True)
        process.kill()
        process.wait(timeout=5)


def action_is_running() -> bool:
    with RUN_LOCK:
        return bool(RUN_STATE["running"])


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def cache_busted_url(path: str) -> str:
    version = env("RAINMAPPER_APP_VERSION").strip()
    if not version:
        return path
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}v={version}"


def app_version() -> str:
    return env("RAINMAPPER_APP_VERSION", "unknown").strip() or "unknown"


def bool_env(name: str, default: bool = False) -> bool:
    value = env(name, "true" if default else "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def supervisor_addon_slug() -> str:
    token = env("SUPERVISOR_TOKEN").strip()
    if not token:
        return ""

    try:
        request = Request(
            "http://supervisor/addons/self/info",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return ""

    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    return str(data.get("slug") or "").strip()


def addon_slug_candidates() -> list[str]:
    candidates = [
        supervisor_addon_slug(),
        env("RAINMAPPER_ADDON_SLUG").strip(),
        "d2750097_rainmapper",
        "rainmapper",
    ]
    slugs = []
    for candidate in candidates:
        if candidate and candidate not in slugs:
            slugs.append(candidate)
    return slugs


def addon_settings_links() -> list[tuple[str, str]]:
    links = []
    seen_urls = set()
    for index, addon_slug in enumerate(addon_slug_candidates()):
        routes = [
            ("Configuration route", f"/config/app/{addon_slug}/config"),
            ("Supervisor route", f"/hassio/addon/{addon_slug}/config"),
        ]
        for route_label, url in routes:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            prefix = "Recommended" if index == 0 and route_label == "Configuration route" else route_label
            links.append((f"{prefix}: {addon_slug}", url))
    return links


def html_page(title: str, body: str, auto_refresh: bool = True) -> bytes:
    refresh_tag = '<meta http-equiv="refresh" content="5">' if auto_refresh else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {refresh_tag}
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #101418;
      --fg: #e8eef2;
      --muted: #9aa8b2;
      --card: #1b2229;
      --line: #33404a;
      --accent: #03a9f4;
      --danger: #ff6b6b;
      --ok: #51cf66;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--fg);
    }}
    main {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 20px 40px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 700;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 18px;
    }}
    p {{
      color: var(--muted);
      margin: 0 0 16px;
      line-height: 1.45;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
      margin: 16px 0 8px;
    }}
    .status-grid {{
      margin: 16px 0 8px;
    }}
    .status-row {{
      display: grid;
      gap: 12px;
      margin: 0 0 12px;
    }}
    .status-row:last-child {{
      margin-bottom: 0;
    }}
    .status-row-primary {{
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }}
    .status-row-secondary,
    .status-row-publication {{
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .station-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin: 16px 0 8px;
    }}
    @media (max-width: 760px) {{
      main {{
        padding: 20px 12px 36px;
      }}
      .status-row,
      .station-grid {{
        grid-template-columns: 1fr;
      }}
    }}
    .card,
    .empty,
    pre {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
    }}
    .card {{
      padding: 14px 16px;
    }}
    .label {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 4px;
    }}
    .value {{
      font-size: 16px;
      word-break: break-word;
    }}
    .ok {{ color: var(--ok); }}
    .danger {{ color: var(--danger); }}
    .warn {{ color: #ffd166; }}
    .source-status-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin: 16px 0 8px;
    }}
    .source-card .value {{
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 8px;
    }}
    .source-card .source-message {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
      margin-top: 6px;
    }}
    .source-card .source-timings {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      margin-top: 6px;
    }}
    @media (max-width: 760px) {{
      .source-status-grid {{
        grid-template-columns: 1fr;
      }}
    }}
    form {{
      display: inline-block;
      margin: 0 8px 8px 0;
    }}
    button,
    .button-link {{
      min-height: 40px;
      padding: 0 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      color: var(--fg);
      font: inherit;
    }}
    .button-link {{
      display: inline-flex;
      align-items: center;
      text-decoration: none;
      margin: 0 8px 8px 0;
      box-sizing: border-box;
    }}
    button:hover,
    button:focus,
    .button-link:hover,
    .button-link:focus {{
      border-color: var(--accent);
    }}
    button.primary,
    .button-link.primary {{
      background: #06344a;
      border-color: var(--accent);
    }}
    .viewer-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 0 0 16px;
    }}
    .viewer-actions .button-link {{
      margin: 0;
    }}
    ul {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 10px;
    }}
    a.map-link {{
      display: block;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      color: var(--fg);
      text-decoration: none;
    }}
    a.map-link:focus,
    a.map-link:hover {{
      border-color: var(--accent);
    }}
    .meta {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }}
    .empty {{
      padding: 16px;
      color: var(--muted);
    }}
    progress {{
      display: block;
      width: 100%;
      height: 10px;
      margin-top: 8px;
      accent-color: var(--accent);
    }}
    .progress-text {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }}
    .station-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    .station-list {{
      display: block;
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      word-break: break-word;
    }}
    .station-details {{
      margin: 6px 0 0;
      padding-left: 18px;
      display: block;
      list-style: disc;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .station-details li {{
      margin: 3px 0;
    }}
    .admin-table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      margin: 12px 0 18px;
    }}
    table.admin-table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
    }}
    .admin-table th,
    .admin-table td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    .admin-table th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .admin-table tr:last-child td {{
      border-bottom: 0;
    }}
    .admin-form-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin: 12px 0 16px;
    }}
    .admin-field label {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 5px;
    }}
    input,
    select {{
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--bg);
      color: var(--fg);
      font: inherit;
      padding: 0 10px;
    }}
    .admin-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .admin-actions form {{
      margin: 0;
    }}
    .inline-form {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 8px;
    }}
    .inline-form input {{
      width: 180px;
    }}
    .password-tools {{
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      margin: 4px 0 8px;
    }}
    .password-tools input {{
      width: auto;
      min-height: auto;
    }}
    .help-text {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
      margin: -4px 0 12px;
    }}
    .users-toolbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: grid;
      grid-template-columns: auto auto minmax(220px, 1fr) auto;
      gap: 10px;
      align-items: center;
      margin: -24px -20px 20px;
      padding: 14px 20px 12px;
      border-bottom: 1px solid var(--line);
      background: color-mix(in srgb, var(--bg) 94%, transparent);
      backdrop-filter: blur(8px);
    }}
    .users-toolbar .button-link,
    .users-toolbar button {{
      margin: 0;
    }}
    .users-filter {{
      min-width: 0;
    }}
    .users-toolbar-status {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .users-empty-filter {{
      display: none;
      padding: 12px 0;
      color: var(--muted);
    }}
    .users-empty-filter.visible {{
      display: block;
    }}
    .device-row.filtered-out {{
      display: none;
    }}
    .user-row.filtered-out {{
      display: none;
    }}
    .device-filter-note {{
      display: none;
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }}
    .device-filter-note.visible {{
      display: block;
    }}
    @media (max-width: 760px) {{
      .admin-form-grid {{
        grid-template-columns: 1fr;
      }}
      .users-toolbar {{
        grid-template-columns: 1fr 1fr;
        margin: -20px -12px 18px;
        padding: 12px;
      }}
      .users-filter,
      .users-toolbar-status {{
        grid-column: 1 / -1;
      }}
    }}
    pre {{
      margin: 0;
      padding: 12px;
      max-height: 60vh;
      overflow: auto;
      white-space: pre-wrap;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
  <script>
    function togglePasswordVisibility(checkbox) {{
      var input = document.getElementById(checkbox.getAttribute("data-target"));
      if (!input) {{
        return;
      }}
      input.type = checkbox.checked ? "text" : "password";
    }}
    function usersTokens(value) {{
      return (value || "")
        .toLowerCase()
        .split(/\\s+/)
        .map(function(token) {{ return token.trim(); }})
        .filter(Boolean);
    }}
    function textMatchesTokens(text, tokens) {{
      var haystack = (text || "").toLowerCase();
      return tokens.every(function(token) {{ return haystack.indexOf(token) !== -1; }});
    }}
    function applyUsersFilter() {{
      var input = document.getElementById("users-filter");
      var table = document.getElementById("users-table");
      if (!input || !table) {{
        return;
      }}
      var tokens = usersTokens(input.value);
      var rows = Array.prototype.slice.call(table.querySelectorAll("tbody tr.user-row"));
      var visibleUsers = 0;
      var visibleDevices = 0;
      rows.forEach(function(row) {{
        var userText = row.getAttribute("data-user-search") || "";
        var rowMatches = tokens.length === 0 || textMatchesTokens(userText, tokens);
        var devices = Array.prototype.slice.call(row.querySelectorAll(".device-row"));
        var anyDeviceMatches = false;
        devices.forEach(function(device) {{
          var deviceText = device.getAttribute("data-device-search") || device.textContent || "";
          var deviceMatches = tokens.length === 0 || rowMatches || textMatchesTokens(deviceText, tokens);
          device.classList.toggle("filtered-out", !deviceMatches);
          if (deviceMatches) {{
            anyDeviceMatches = true;
            visibleDevices += 1;
          }}
        }});
        var showRow = tokens.length === 0 || rowMatches || anyDeviceMatches;
        row.classList.toggle("filtered-out", !showRow);
        if (showRow) {{
          visibleUsers += 1;
        }}
        var note = row.querySelector(".device-filter-note");
        if (note) {{
          note.classList.toggle("visible", tokens.length > 0 && showRow && !rowMatches && anyDeviceMatches);
        }}
      }});
      var empty = document.getElementById("users-empty-filter");
      if (empty) {{
        empty.classList.toggle("visible", tokens.length > 0 && visibleUsers === 0);
      }}
      var status = document.getElementById("users-filter-status");
      if (status) {{
        var totalUsers = rows.length;
        status.textContent = tokens.length
          ? visibleUsers + " of " + totalUsers + " users"
          : totalUsers + " users";
      }}
    }}
    async function refreshUsersPage() {{
      var button = document.getElementById("users-refresh");
      var content = document.getElementById("users-content");
      if (!button || !content) {{
        return;
      }}
      var filter = document.getElementById("users-filter");
      var filterValue = filter ? filter.value : "";
      var scrollY = window.scrollY;
      var status = document.getElementById("users-refresh-status");
      button.disabled = true;
      if (status) {{
        status.textContent = "Refreshing...";
      }}
      try {{
        var response = await fetch(window.location.pathname, {{ cache: "no-store" }});
        if (!response.ok) {{
          throw new Error("HTTP " + response.status);
        }}
        var text = await response.text();
        var doc = new DOMParser().parseFromString(text, "text/html");
        var nextContent = doc.getElementById("users-content");
        if (!nextContent) {{
          throw new Error("Missing users content");
        }}
        content.innerHTML = nextContent.innerHTML;
        if (filter) {{
          filter.value = filterValue;
        }}
        applyUsersFilter();
        window.scrollTo({{ top: scrollY }});
        if (status) {{
          status.textContent = "Updated " + new Date().toLocaleTimeString();
        }}
      }} catch (error) {{
        if (status) {{
          status.textContent = "Refresh failed";
        }}
      }} finally {{
        button.disabled = false;
      }}
    }}
    document.addEventListener("input", function(event) {{
      if (event.target && event.target.id === "users-filter") {{
        applyUsersFilter();
      }}
    }});
    document.addEventListener("DOMContentLoaded", applyUsersFilter);
  </script>
</body>
</html>
""".encode("utf-8")


def format_size(size: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def format_duration(start_text: str, finish_text: str) -> str:
    if not start_text:
        return "-"

    try:
        start = datetime.fromisoformat(start_text)
    except ValueError:
        return "-"

    if finish_text:
        try:
            finish = datetime.fromisoformat(finish_text)
        except ValueError:
            return "-"
    else:
        finish = datetime.now(get_timezone())

    total_seconds = max(0, int((finish - start).total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def format_seconds_duration(value) -> str:
    try:
        total_seconds = max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return "-"

    minutes, seconds = divmod(total_seconds, 60)
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_datetime_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=get_timezone()).isoformat(timespec="seconds")


def get_timezone() -> ZoneInfo:
    timezone_name = env("RAINMAPPER_TIMEZONE", env("TZ", "Europe/Madrid"))
    try:
        return ZoneInfo(timezone_name)
    except Exception:
        return ZoneInfo("UTC")


def schedule_times() -> list[str]:
    configured = env("RAINMAPPER_SCHEDULE_TIME", "23:50")
    matches = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", configured)
    normalized = sorted({f"{int(hour):02}:{minute}" for hour, minute in matches})
    return normalized


def schedule_days() -> set[int]:
    configured = env("RAINMAPPER_SCHEDULE_DAYS", "all").strip().lower()
    if not configured or configured == "all":
        return set(range(7))

    aliases = {
        "0": 0,
        "1": 0,
        "mon": 0,
        "monday": 0,
        "lun": 0,
        "lunes": 0,
        "2": 1,
        "tue": 1,
        "tuesday": 1,
        "mar": 1,
        "martes": 1,
        "3": 2,
        "wed": 2,
        "wednesday": 2,
        "mie": 2,
        "miercoles": 2,
        "4": 3,
        "thu": 3,
        "thursday": 3,
        "jue": 3,
        "jueves": 3,
        "5": 4,
        "fri": 4,
        "friday": 4,
        "vie": 4,
        "viernes": 4,
        "6": 5,
        "sat": 5,
        "saturday": 5,
        "sab": 5,
        "sabado": 5,
        "7": 6,
        "sun": 6,
        "sunday": 6,
        "dom": 6,
        "domingo": 6,
    }

    days = set()
    for token in re.split(r"[,;|\s-]+", configured):
        token = token.strip()
        if token in aliases:
            days.add(aliases[token])
    return days


def command_for(action: str) -> list[str]:
    update_command = [
        "python",
        "-m",
        "rainmapper_core.rainmapper",
        "--create_meteoclimatic",
        env("RAINMAPPER_CREATE_METEOCLIMATIC", "true"),
        "--create_meteocat",
        env("RAINMAPPER_CREATE_METEOCAT", "true"),
        "--create_wunderground",
        env("RAINMAPPER_CREATE_WUNDERGROUND", "true"),
        "--create_aemet",
        env("RAINMAPPER_CREATE_AEMET", "false"),
        "--days_init",
        env("RAINMAPPER_DAYS_INIT", "-7"),
        "--days_end",
        env("RAINMAPPER_DAYS_END", "0"),
        "--nomaps",
        env("RAINMAPPER_NOMAPS", "false"),
        "--nototals",
        env("RAINMAPPER_NOTOTALS", "false"),
        "--days_bucket",
        env("RAINMAPPER_DAYS_BUCKET", "10"),
        "--meteocat_request_timeout",
        env("RAINMAPPER_METEOCAT_REQUEST_TIMEOUT", "30"),
        "--meteocat_max_attempts",
        env("RAINMAPPER_METEOCAT_MAX_ATTEMPTS", "3"),
        "--max_threads",
        env("RAINMAPPER_MAX_THREADS", "3"),
        "--max_attempts",
        env("RAINMAPPER_MAX_ATTEMPTS", "3"),
        "--wunderground_full_log",
        env("RAINMAPPER_WUNDERGROUND_FULL_LOG", "false"),
        "--meteoclimatic_pattern",
        env("RAINMAPPER_METEOCLIMATIC_PATTERN", "ESCAT"),
    ]

    if action == "update":
        return update_command
    if action == "maps":
        return [
            "sh",
            "-c",
            "python -m rainmapper_core.tomap "
            "--data-dir /app/Data "
            "--maps-dir /app/Tomap "
            "--last-rains-history \"$RAINMAPPER_LAST_RAINS_HISTORY\" "
            "--max-threads \"$RAINMAPPER_MAX_THREADS\" "
            "&& python -m rainmapper_core.bokeh_maps",
        ]
    if action == "all":
        return update_command + ["&&", "python", "-m", "rainmapper_core.bokeh_maps"]
    raise ValueError(f"Invalid action: {action}")


def public_name_for(file_path: Path) -> str:
    return PUBLIC_MAP_NAMES.get(file_path.name, file_path.name)


def clear_progress() -> dict[str, str]:
    return {
        "progress_current": "",
        "progress_total": "",
        "progress_percent": "",
    }


def update_run_progress(raw_line: str) -> None:
    line = raw_line.strip()
    if not line:
        return

    updates: dict[str, str] = {}
    progress_match = re.search(
        r"(?:Procesando estaciones Wunderground|Processing Wunderground stations)\s+(\d+)\s+(?:de|from)\s+(\d+)",
        line,
        re.IGNORECASE,
    )
    if progress_match:
        current = int(progress_match.group(1))
        total = int(progress_match.group(2))
        percent = int(round((current / total) * 100)) if total else 0
        updates.update(
            {
                "current_step": "Running Wunderground",
                "progress_current": str(current),
                "progress_total": str(total),
                "progress_percent": str(percent),
            }
        )
    elif line.startswith("Start processing Meteoclimatic"):
        updates.update({"current_step": "Running Meteoclimatic", **clear_progress()})
    elif line.startswith("Start processing Meteocat"):
        updates.update({"current_step": "Running Meteocat", **clear_progress()})
    elif line.startswith("Start processing Wunderground"):
        updates.update({"current_step": "Running Wunderground", **clear_progress()})
    elif line.startswith("Start printing routine"):
        updates.update({"current_step": "Printing totals", **clear_progress()})
    elif line.startswith("Start rebuilding Tomap") or (line.startswith("Start processing") and "Tomap" in line):
        updates.update({"current_step": "Rebuilding Tomap", **clear_progress()})
    elif line.startswith("Start processing") and "map" in line.lower():
        updates.update({"current_step": "Generating map files", **clear_progress()})
    elif line.startswith("Starting Rainmapper maps"):
        updates.update({"current_step": "Generating maps", **clear_progress()})
    elif line.startswith("Rainmapper maps finished"):
        updates.update({"current_step": "Maps finished", **clear_progress()})

    if updates:
        with RUN_LOCK:
            RUN_STATE.update(updates)


DISABLED_MARKER_PREFIX = "rainmapper-disabled:"


def station_id_from_failed_line(line: str) -> str:
    match = re.match(r"^-\s+([^\s(]+)", line.strip())
    return match.group(1) if match else ""


def failed_wunderground_groups() -> dict[str, list[str]]:
    groups = {"404": [], "parse": []}
    if not LOG_PATH.exists():
        return groups

    for raw_line in LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue
        station_id = station_id_from_failed_line(line)
        if not station_id:
            continue
        lower_line = line.lower()
        if "status code=404" in lower_line:
            groups["404"].append(station_id)
        elif "list index out of range" in lower_line:
            groups["parse"].append(station_id)

    return {key: sorted(set(value)) for key, value in groups.items()}


def disabled_station_groups() -> dict[str, list[str]]:
    groups = {"404": [], "parse": []}
    if not STATIONS_PATH.exists():
        return groups

    marker = f"# {DISABLED_MARKER_PREFIX}"
    for raw_line in STATIONS_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith(marker):
            continue
        payload = stripped[2:].strip()
        reason, _, station_line = payload.partition(" ")
        group_name = reason.removeprefix(DISABLED_MARKER_PREFIX).strip()
        if group_name not in groups:
            continue
        station_id = station_id_from_station_line(station_line)
        if station_id:
            groups[group_name].append(station_id)

    return {key: sorted(set(value)) for key, value in groups.items()}


def station_id_from_station_line(line: str) -> str:
    match = re.search(r"/pws/([A-Z0-9]+)", line, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    tokens = re.findall(r"[A-Z][A-Z0-9]{2,}", line.upper())
    return tokens[-1] if tokens else ""


def station_line_payload(line: str) -> str:
    stripped = line.lstrip()
    if stripped.startswith("#"):
        stripped = stripped[1:].lstrip()
    for group_name in ("404", "parse"):
        marker = f"{DISABLED_MARKER_PREFIX}{group_name}"
        if stripped.startswith(marker):
            return stripped.removeprefix(marker).lstrip()
    return stripped


def station_line_matches(line: str, station_id: str) -> bool:
    payload = station_line_payload(line)
    return re.search(rf"(?<![A-Z0-9]){re.escape(station_id)}(?![A-Z0-9])", payload, re.IGNORECASE) is not None


def station_ids_for_group(group_name: str) -> list[str]:
    failed_groups = failed_wunderground_groups()
    disabled_groups = disabled_station_groups()
    return sorted(set(failed_groups.get(group_name, [])) | set(disabled_groups.get(group_name, [])))


def wunderground_station_metadata() -> dict[str, dict[str, str]]:
    if not WUNDERGROUND_STATIONS_DB_PATH.exists():
        return {}

    metadata: dict[str, dict[str, str]] = {}
    try:
        with WUNDERGROUND_STATIONS_DB_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                station_id = (row.get("Codi Estació") or "").strip().upper()
                if not station_id:
                    continue
                metadata[station_id] = {
                    "municipality": (row.get("Municipi") or "").strip(),
                    "province": (row.get("Provincia") or "").strip(),
                    "altitude": (row.get("Altitud") or "").strip(),
                }
    except Exception:
        return {}
    return metadata


def station_detail_text(station_id: str, metadata: dict[str, dict[str, str]]) -> str:
    info = metadata.get(station_id.upper(), {})
    municipality = info.get("municipality") or "unknown municipality"
    province = info.get("province") or "unknown province"
    altitude = info.get("altitude") or "unknown altitude"
    altitude_text = f"{altitude} m" if altitude not in {"", "unknown altitude", "Not set yet"} else altitude
    return f"{station_id} - {municipality}, {province} - Altitude: {altitude_text}"


def station_detail_list(station_ids: list[str], metadata: dict[str, dict[str, str]]) -> str:
    if not station_ids:
        return '<span class="station-list">None</span>'
    items = "".join(
        f"<li>{html.escape(station_detail_text(station_id, metadata))}</li>"
        for station_id in station_ids
    )
    return f'<ul class="station-details">{items}</ul>'


def read_source_status() -> dict:
    if not SOURCE_STATUS_PATH.exists():
        return {}
    try:
        return json.loads(SOURCE_STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def source_status_class(status: str) -> str:
    normalized = status.upper()
    if normalized == "OK":
        return "ok"
    if normalized in {"STALE", "PENDING", "DISABLED"}:
        return "warn"
    if normalized == "NOK":
        return "danger"
    return ""


def source_status_card(source: str, payload: dict) -> str:
    status = str(payload.get("status") or "Unknown")
    exit_code = payload.get("exit_code")
    rows = payload.get("rows")
    stations = payload.get("stations")
    duration = payload.get("duration_seconds")
    timings = payload.get("timings")
    message = str(payload.get("message") or "No source status yet.")
    updated_at = str(payload.get("updated_at") or "-")
    exit_text = "-" if exit_code is None else str(exit_code)
    rows_text = "-" if rows is None else str(rows)
    stations_text = "-" if stations is None else str(stations)
    duration_text = format_seconds_duration(duration)
    status_class = source_status_class(status)
    timing_text = ""
    if isinstance(timings, dict) and timings:
        timing_labels = [
            ("metadata_seconds", "metadata"),
            ("conditions_seconds", "conditions"),
            ("precipitation_seconds", "rain"),
            ("merge_seconds", "merge"),
            ("save_seconds", "save"),
        ]
        timing_parts = [
            f"{label} {format_seconds_duration(timings.get(key))}"
            for key, label in timing_labels
            if timings.get(key) is not None
        ]
        if timing_parts:
            timing_text = f'<div class="source-timings">{html.escape(" · ".join(timing_parts))}</div>'
    return f"""
      <div class="card source-card">
        <span class="label">{html.escape(source)}</span>
        <span class="value"><span class="{status_class}">{html.escape(status)}</span><span>exit {html.escape(exit_text)}</span></span>
        <span class="label">Rows</span><span>{html.escape(rows_text)}</span>
        <span class="label">Stations</span><span>{html.escape(stations_text)}</span>
        <span class="label">Duration</span><span>{html.escape(duration_text)}</span>
        <span class="label">Updated</span><span>{html.escape(updated_at)}</span>
        {timing_text}
        <div class="source-message">{html.escape(message)}</div>
      </div>
    """


def source_status_cards() -> str:
    payload = read_source_status()
    sources = payload.get("sources", {}) if isinstance(payload, dict) else {}
    cards = []
    for source in ("Meteoclimatic", "Meteocat", "Wunderground", "AEMET"):
        source_payload = sources.get(source, {}) if isinstance(sources, dict) else {}
        cards.append(source_status_card(source, source_payload))
    return '<div class="source-status-grid">' + "".join(cards) + "</div>"


def update_station_group(group_name: str, enable: bool) -> int:
    station_ids = station_ids_for_group(group_name)
    if not station_ids or not STATIONS_PATH.exists():
        return 0

    changed = 0
    updated_lines = []
    marker = f"# {DISABLED_MARKER_PREFIX}{group_name} "
    for line in STATIONS_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        payload = station_line_payload(line)
        disabled_for_group = stripped.startswith(marker.strip()) or stripped.startswith(marker)
        matches = any(station_line_matches(line, station_id) for station_id in station_ids)

        if matches and enable and disabled_for_group:
            updated_lines.append(indent + payload)
            changed += 1
        elif matches and not enable and not disabled_for_group and not stripped.startswith("#"):
            updated_lines.append(indent + marker + stripped)
            changed += 1
        else:
            updated_lines.append(line)

    STATIONS_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return changed


def station_group_card(title: str, group_name: str, station_ids: list[str], disabled_ids: list[str], disabled: str) -> str:
    active_count = len(station_ids)
    disabled_count = len(disabled_ids)
    metadata = wunderground_station_metadata()
    current_details = station_detail_list(station_ids, metadata)
    disabled_details = station_detail_list(disabled_ids, metadata)
    return f"""
      <div class="card">
        <span class="label">{html.escape(title)}</span>
        <span class="value">{active_count} current / {disabled_count} disabled</span>
        <span class="station-list">Current:</span>
        {current_details}
        <span class="station-list">Disabled:</span>
        {disabled_details}
        <div class="station-actions">
          <form method="post" action=""><input type="hidden" name="station_action" value="disable"><input type="hidden" name="station_group" value="{html.escape(group_name)}"><button {disabled}>Disable all</button></form>
          <form method="post" action=""><input type="hidden" name="station_action" value="enable"><input type="hidden" name="station_group" value="{html.escape(group_name)}"><button {disabled}>Enable all</button></form>
        </div>
      </div>
    """


def publish_maps(log_file) -> tuple[bool, str]:
    if not bool_env("RAINMAPPER_PUBLISH_TO_WWW", True):
        return True, "Publishing to /local/Plots is disabled."

    if not Path("/config").exists():
        return False, "Cannot publish maps: /config is not available in this container."

    html_files = sorted(PLOTS_PATH.glob("*.html"))
    if not html_files:
        return False, "Cannot publish maps: no HTML files found in /share/rainmapper/Plots."

    PUBLIC_PLOTS_TMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PUBLIC_PLOTS_TMP_PATH, ignore_errors=True)
    PUBLIC_PLOTS_TMP_PATH.mkdir(parents=True, exist_ok=True)

    copied = 0
    for source_path in html_files:
        target_name = public_name_for(source_path)
        shutil.copy2(source_path, PUBLIC_PLOTS_TMP_PATH / target_name)
        copied += 1

    shutil.rmtree(PUBLIC_PLOTS_PATH, ignore_errors=True)
    PUBLIC_PLOTS_TMP_PATH.rename(PUBLIC_PLOTS_PATH)

    published_at = datetime.now(get_timezone()).isoformat(timespec="seconds")
    message = f"Published {copied} map file(s) to /local/Plots at {published_at}."
    log_file.write(f"=== {message} ===\n")
    log_file.flush()
    with RUN_LOCK:
        RUN_STATE["last_published_at"] = published_at
        RUN_STATE["last_publish_message"] = message
    print(message, flush=True)
    return True, message


def publish_mobile_viewer(log_file) -> tuple[bool, str]:
    if not bool_env("RAINMAPPER_PUBLISH_TO_WWW", True):
        return True, "Publishing viewers to /local/rainmapper-leaflet/index.html and /protected/maplibre/index.html is disabled."

    if not Path("/config").exists():
        return False, "Cannot publish viewers: /config is not available in this container."

    if not LEAFLET_VIEWER_ASSETS_PATH.exists():
        return False, "Cannot publish Leaflet viewer: Leaflet viewer assets are missing."

    PUBLIC_DATA_PATH.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        [
            "python",
            "-m",
            "rainmapper_core.geojson",
            "--input-dir",
            str(TOMAP_PATH),
            "--output-dir",
            str(PUBLIC_DATA_PATH),
            "--ignore-stations-file",
            "/app/ignore_stations_tomap.txt",
        ],
        cwd="/app",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if process.stdout:
        log_file.write(process.stdout)
        log_file.flush()
    if process.returncode != 0:
        return False, "Cannot publish viewers: GeoJSON generation failed."

    PUBLIC_LEAFLET_TMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PUBLIC_LEAFLET_TMP_PATH, ignore_errors=True)
    PUBLIC_LEAFLET_TMP_PATH.mkdir(parents=True, exist_ok=True)

    for asset_name in ("index.html", "app.js", "style.css"):
        shutil.copy2(LEAFLET_VIEWER_ASSETS_PATH / asset_name, PUBLIC_LEAFLET_TMP_PATH / asset_name)

    config_js = public_viewer_config_js()
    (PUBLIC_LEAFLET_TMP_PATH / "config.js").write_text(config_js)

    data_path = PUBLIC_LEAFLET_TMP_PATH / "data"
    data_path.mkdir()
    copied = 0
    for source_path in sorted(PUBLIC_DATA_PATH.glob("*.geojson")):
        shutil.copy2(source_path, data_path / source_path.name)
        copied += 1
    if SOURCE_STATUS_PATH.exists():
        shutil.copy2(SOURCE_STATUS_PATH, data_path / SOURCE_STATUS_PATH.name)

    shutil.rmtree(PUBLIC_LEAFLET_PATH, ignore_errors=True)
    PUBLIC_LEAFLET_TMP_PATH.rename(PUBLIC_LEAFLET_PATH)
    shutil.rmtree(REMOVED_LEGACY_MOBILE_PATH, ignore_errors=True)

    if not MAPLIBRE_VIEWER_ASSETS_PATH.exists():
        return False, "Cannot publish MapLibre viewer: MapLibre viewer assets are missing."

    preserve_public_maplibre_data_for_transition()
    PUBLIC_MAPLIBRE_TMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PUBLIC_MAPLIBRE_TMP_PATH, ignore_errors=True)
    PUBLIC_MAPLIBRE_TMP_PATH.mkdir(parents=True, exist_ok=True)

    for asset_name in ("index.html", "app.js", "style.css", "translations.json"):
        shutil.copy2(MAPLIBRE_VIEWER_ASSETS_PATH / asset_name, PUBLIC_MAPLIBRE_TMP_PATH / asset_name)
    (PUBLIC_MAPLIBRE_TMP_PATH / "config.js").write_text(config_js)

    # Transitional fallback: keep /local/rainmapper-maplibre/data available until
    # the protected Cloudflared route has been validated in the real HA setup.
    # TODO: restore strict protected-only data by calling
    # remove_legacy_public_maplibre_data() after Cloudflared validation.
    data_path = PUBLIC_MAPLIBRE_TMP_PATH / "data"
    data_path.mkdir()
    for source_path in sorted(PUBLIC_DATA_PATH.glob("*.geojson")):
        shutil.copy2(source_path, data_path / source_path.name)
    if SOURCE_STATUS_PATH.exists():
        shutil.copy2(SOURCE_STATUS_PATH, data_path / SOURCE_STATUS_PATH.name)

    shutil.rmtree(PUBLIC_MAPLIBRE_PATH, ignore_errors=True)
    PUBLIC_MAPLIBRE_TMP_PATH.rename(PUBLIC_MAPLIBRE_PATH)

    aemet_message = publish_aemet_experimental_maplibre(log_file, config_js)

    published_at = datetime.now(get_timezone()).isoformat(timespec="seconds")
    message = (
        f"Published mobile viewers with {copied} GeoJSON file(s) to "
        f"/local/rainmapper-leaflet/index.html and protected /protected/maplibre/index.html at {published_at}."
    )
    if aemet_message:
        message = f"{message} {aemet_message}"
    log_file.write(f"=== {message} ===\n")
    log_file.flush()
    with RUN_LOCK:
        previous_message = RUN_STATE["last_publish_message"]
        RUN_STATE["last_published_at"] = published_at
        RUN_STATE["last_publish_message"] = f"{previous_message} {message}".strip()
    print(message, flush=True)
    return True, message


def publish_aemet_experimental_maplibre(log_file, config_js: str) -> str:
    """Publish an optional public MapLibre variant with AEMET included.

    The standard protected MapLibre route keeps using the normal PublicData
    output. This experimental fallback lets the owner validate AEMET without
    changing what existing protected users see.
    """
    if not (DATA_PATH / "Aemet_incremental.csv").exists():
        shutil.rmtree(PUBLIC_MAPLIBRE_AEMET_PATH, ignore_errors=True)
        return ""

    shutil.rmtree(AEMET_EXPERIMENT_TOMAP_PATH, ignore_errors=True)
    shutil.rmtree(AEMET_EXPERIMENT_DATA_PATH, ignore_errors=True)
    AEMET_EXPERIMENT_TOMAP_PATH.mkdir(parents=True, exist_ok=True)
    AEMET_EXPERIMENT_DATA_PATH.mkdir(parents=True, exist_ok=True)

    tomap_process = subprocess.run(
        [
            "python",
            "-m",
            "rainmapper_core.tomap",
            "--data-dir",
            str(DATA_PATH),
            "--maps-dir",
            str(AEMET_EXPERIMENT_TOMAP_PATH),
            "--last-rains-history",
            os.environ.get("RAINMAPPER_LAST_RAINS_HISTORY", "30"),
            "--include-aemet",
            "true",
        ],
        cwd="/app",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if tomap_process.stdout:
        log_file.write(tomap_process.stdout)
        log_file.flush()
    if tomap_process.returncode != 0:
        return "AEMET experimental MapLibre was not published: Tomap generation failed."

    geojson_process = subprocess.run(
        [
            "python",
            "-m",
            "rainmapper_core.geojson",
            "--input-dir",
            str(AEMET_EXPERIMENT_TOMAP_PATH),
            "--output-dir",
            str(AEMET_EXPERIMENT_DATA_PATH),
            "--ignore-stations-file",
            "/app/ignore_stations_tomap.txt",
        ],
        cwd="/app",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if geojson_process.stdout:
        log_file.write(geojson_process.stdout)
        log_file.flush()
    if geojson_process.returncode != 0:
        return "AEMET experimental MapLibre was not published: GeoJSON generation failed."

    PUBLIC_MAPLIBRE_AEMET_TMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PUBLIC_MAPLIBRE_AEMET_TMP_PATH, ignore_errors=True)
    PUBLIC_MAPLIBRE_AEMET_TMP_PATH.mkdir(parents=True, exist_ok=True)

    for asset_name in ("index.html", "app.js", "style.css", "translations.json"):
        shutil.copy2(MAPLIBRE_VIEWER_ASSETS_PATH / asset_name, PUBLIC_MAPLIBRE_AEMET_TMP_PATH / asset_name)
    (PUBLIC_MAPLIBRE_AEMET_TMP_PATH / "config.js").write_text(config_js)

    data_path = PUBLIC_MAPLIBRE_AEMET_TMP_PATH / "data"
    data_path.mkdir()
    copied = 0
    for source_path in sorted(AEMET_EXPERIMENT_DATA_PATH.glob("*.geojson")):
        shutil.copy2(source_path, data_path / source_path.name)
        copied += 1
    if SOURCE_STATUS_PATH.exists():
        shutil.copy2(SOURCE_STATUS_PATH, data_path / SOURCE_STATUS_PATH.name)

    shutil.rmtree(PUBLIC_MAPLIBRE_AEMET_PATH, ignore_errors=True)
    PUBLIC_MAPLIBRE_AEMET_TMP_PATH.rename(PUBLIC_MAPLIBRE_AEMET_PATH)
    return f"Published experimental AEMET MapLibre fallback with {copied} GeoJSON file(s) to /local/rainmapper-maplibre-aemet/index.html."


def run_action(action: str, source: str) -> bool:
    if action not in {"update", "maps", "all"}:
        return False

    with RUN_LOCK:
        if RUN_STATE["running"]:
            return False
        RUN_STATE.update(
            {
                "running": True,
                "action": action,
                "started_at": datetime.now(get_timezone()).isoformat(timespec="seconds"),
                "finished_at": "",
                "duration": "",
                "exit_code": "",
                "last_message": f"Running {action} from {source}.",
                "current_step": f"Queued {action}",
                "progress_current": "",
                "progress_total": "",
                "progress_percent": "",
            }
        )

    thread = threading.Thread(target=_run_action_thread, args=(action, source), daemon=True)
    thread.start()
    return True


def _run_action_thread(action: str, source: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    final_exit_code = 0
    started = datetime.now(get_timezone())
    print(f"Starting Rainmapper action '{action}' from {source}.", flush=True)

    with LOG_PATH.open("w", encoding="utf-8") as log_file:
        log_file.write(f"=== {started.isoformat(timespec='seconds')} - {action} ({source}) ===\n")
        log_file.flush()

        actions = ["update", "maps"] if action == "all" else [action]
        for current_action in actions:
            print(f"Running Rainmapper step '{current_action}'.", flush=True)
            with RUN_LOCK:
                RUN_STATE.update({"current_step": f"Running {current_action}", **clear_progress()})
            log_file.write(f"=== running step {current_action} ===\n")
            log_file.flush()
            command = command_for(current_action)
            process = subprocess.Popen(
                command,
                cwd="/app",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            set_current_process(process)
            try:
                assert process.stdout is not None
                for line in process.stdout:
                    update_run_progress(line)
                    log_file.write(line)
                    log_file.flush()
                exit_code = process.wait()
                if exit_code == 1:
                    final_exit_code = 1
                elif exit_code == 2 and final_exit_code == 0:
                    final_exit_code = 2
            finally:
                set_current_process(None)
            print(f"Rainmapper step '{current_action}' finished with exit code {exit_code}.", flush=True)
            if exit_code not in {0, 2}:
                break
            if current_action == "maps":
                publish_ok, publish_message = publish_maps(log_file)
                if not publish_ok:
                    print(publish_message, flush=True)
                    log_file.write(f"=== {publish_message} ===\n")
                    log_file.flush()
                publish_ok, publish_message = publish_mobile_viewer(log_file)
                if not publish_ok:
                    print(publish_message, flush=True)
                    log_file.write(f"=== {publish_message} ===\n")
                    log_file.flush()

        finished = datetime.now(get_timezone())
        duration = format_duration(started.isoformat(timespec="seconds"), finished.isoformat(timespec="seconds"))
        if final_exit_code == 0:
            final_exit_code = exit_code
        log_file.write(f"=== finished with exit code {final_exit_code} at {finished.isoformat(timespec='seconds')} ===\n")
        log_file.write(f"=== duration {duration} ===\n")

    if final_exit_code == 0:
        message = "Finished successfully."
        current_step = "Idle"
    elif final_exit_code == 2:
        message = "Finished with degraded source status."
        current_step = "Finished degraded"
    else:
        message = f"Finished with exit code {final_exit_code}."
        current_step = "Finished with error"
    print(f"Rainmapper action '{action}' finished with exit code {final_exit_code} in {duration}.", flush=True)
    with RUN_LOCK:
        RUN_STATE.update(
            {
                "running": False,
                "finished_at": datetime.now(get_timezone()).isoformat(timespec="seconds"),
                "duration": format_duration(RUN_STATE["started_at"], datetime.now(get_timezone()).isoformat(timespec="seconds")),
                "exit_code": str(final_exit_code),
                "last_message": message,
                "current_step": current_step,
                "progress_current": "",
                "progress_total": "",
                "progress_percent": "",
            }
        )
    STATUS_PATH.write_text(message + "\n", encoding="utf-8")


def next_schedule_text() -> str:
    if not bool_env("RAINMAPPER_SCHEDULE_ENABLED"):
        return "Disabled"

    times = schedule_times()
    days = schedule_days()
    if not times:
        return "Invalid schedule time"
    if not days:
        return "Invalid schedule days"

    now = datetime.now(get_timezone())
    candidates = []
    for day_offset in range(8):
        candidate_day = now.date() + timedelta(days=day_offset)
        if candidate_day.weekday() not in days:
            continue
        for schedule_time in times:
            hour_text, minute_text = schedule_time.split(":", 1)
            candidate = datetime.combine(candidate_day, datetime.min.time(), tzinfo=get_timezone())
            candidate = candidate.replace(hour=int(hour_text), minute=int(minute_text))
            if candidate > now:
                candidates.append(candidate)

    if not candidates:
        return "No upcoming schedule"
    return min(candidates).isoformat(timespec="minutes")


def scheduler_loop() -> None:
    while not SHUTDOWN_EVENT.is_set():
        if SHUTDOWN_EVENT.wait(20):
            break
        if not bool_env("RAINMAPPER_SCHEDULE_ENABLED"):
            continue

        times = schedule_times()
        days = schedule_days()
        scheduled_action = env("RAINMAPPER_SCHEDULED_ACTION", "all")
        now = datetime.now(get_timezone())
        current_time = now.strftime("%H:%M")
        scheduled_key = f"{now.date().isoformat()} {current_time}"

        if now.weekday() not in days:
            continue
        if current_time not in times:
            continue
        if RUN_STATE["last_scheduled_key"] == scheduled_key:
            continue
        if run_action(scheduled_action, "schedule"):
            RUN_STATE["last_scheduled_key"] = scheduled_key


def read_log() -> str:
    if not LOG_PATH.exists():
        return "No logs yet."
    return LOG_PATH.read_text(encoding="utf-8", errors="replace")


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def normalize_user_id(value: str) -> str:
    return value.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}$"
        f"{base64.urlsafe_b64encode(salt).decode('ascii')}$"
        f"{base64.urlsafe_b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, stored_value: str) -> bool:
    if stored_value.startswith("pbkdf2_sha256$"):
        try:
            _algorithm, iterations_text, salt_text, digest_text = stored_value.split("$", 3)
            iterations = int(iterations_text)
            salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
            expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        except Exception:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(actual, expected)

    # Bootstrap mode: allow manually-created plaintext passwords, then migrate on login.
    return secrets.compare_digest(password, stored_value)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


ROLE_DEFAULT_MAX_DEVICES = {
    "free": 1,
    "basic": 2,
    "pro": 3,
    "admin": 0,
}


def normalize_role(value: str) -> str:
    role = value.strip().lower()
    return role if role in ROLE_DEFAULT_MAX_DEVICES else "free"


def default_max_devices_for_role(role: str) -> int:
    return ROLE_DEFAULT_MAX_DEVICES.get(normalize_role(role), 1)


def parse_max_devices(value: str, role: str) -> int:
    if not value.strip():
        return default_max_devices_for_role(role)
    try:
        parsed = int(value)
    except ValueError:
        return default_max_devices_for_role(role)
    return max(parsed, 0)


def user_max_devices(user: dict[str, str]) -> int:
    return parse_max_devices(user.get("max_devices", ""), user.get("role", "free"))


def normalize_enabled(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "false" if str(value).strip().lower() == "false" else "true"


def normalize_bool_flag(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "true" if str(value).strip().lower() == "true" else "false"


def normalize_user_record(raw_user: dict[str, object], fallback_username: str = "") -> dict[str, str] | None:
    username = normalize_user_id(str(raw_user.get("username") or fallback_username))
    if not username:
        return None
    role = normalize_role(str(raw_user.get("role", "free")))
    return {
        "username": username,
        "name": str(raw_user.get("name", "")).strip(),
        "email": normalize_user_id(str(raw_user.get("email", username))),
        "password": str(raw_user.get("password", "")),
        "role": role,
        "enabled": normalize_enabled(raw_user.get("enabled", True)),
        "max_devices": str(parse_max_devices(str(raw_user.get("max_devices", "")), role)),
        "must_change_password": normalize_bool_flag(raw_user.get("must_change_password", False)),
    }


def read_users_json() -> dict[str, dict[str, str]]:
    try:
        payload = json.loads(USERS_JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    raw_users = payload.get("users", []) if isinstance(payload, dict) else []
    if isinstance(raw_users, dict):
        iterable = raw_users.items()
    elif isinstance(raw_users, list):
        iterable = [("", item) for item in raw_users]
    else:
        iterable = []

    users: dict[str, dict[str, str]] = {}
    for fallback_username, item in iterable:
        if not isinstance(item, dict):
            continue
        user = normalize_user_record(item, str(fallback_username))
        if user:
            users[user["username"]] = user
    return users


def read_users() -> dict[str, dict[str, str]]:
    if USERS_JSON_PATH.exists():
        return read_users_json()
    return {}


def write_users(users: dict[str, dict[str, str]]) -> None:
    USERS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "users": [
            {
                "username": user["username"],
                "name": user.get("name", ""),
                "email": user.get("email", user["username"]),
                "password": user["password"],
                "role": normalize_role(user.get("role", "free")),
                "enabled": user.get("enabled", "true").lower() == "true",
                "max_devices": user_max_devices(user),
                "must_change_password": user.get("must_change_password", "false").lower() == "true",
            }
            for _username, user in sorted(users.items())
        ]
    }
    USERS_JSON_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_devices() -> dict[str, dict[str, str]]:
    if not DEVICES_PATH.exists():
        return {}
    try:
        payload = json.loads(DEVICES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    devices = payload.get("devices", {})
    return devices if isinstance(devices, dict) else {}


def write_devices(devices: dict[str, dict[str, str]]) -> None:
    DEVICES_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"devices": devices}
    DEVICES_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finite_number(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed == parsed and parsed not in (float("inf"), float("-inf")) else default


def sanitize_device_settings(raw_settings: object) -> dict[str, object]:
    if not isinstance(raw_settings, dict):
        return {}

    settings: dict[str, object] = {}

    period = str(raw_settings.get("period", "")).strip()
    if period in DEVICE_SETTING_PERIODS:
        settings["period"] = period

    map_style = str(raw_settings.get("map_style", "")).strip()
    if map_style in DEVICE_SETTING_MAP_STYLES:
        settings["map_style"] = map_style

    language = str(raw_settings.get("language", "")).strip().lower()
    if language in DEVICE_SETTING_LANGUAGES:
        settings["language"] = language

    min_rain_mm = finite_number(raw_settings.get("min_rain_mm"), 0.0)
    settings["min_rain_mm"] = max(0.0, min(10000.0, min_rain_mm))

    try:
        last_rains_history = int(raw_settings.get("last_rains_history", 0))
    except (TypeError, ValueError):
        last_rains_history = 0
    if last_rains_history > 0:
        settings["last_rains_history"] = min(500, last_rains_history)

    station_sources = raw_settings.get("station_sources")
    if isinstance(station_sources, list):
        selected_sources = [
            str(source)
            for source in station_sources
            if str(source) in DEVICE_SETTING_SOURCES
        ]
        deduplicated_sources = list(dict.fromkeys(selected_sources))
        if deduplicated_sources:
            settings["station_sources"] = deduplicated_sources

    if "terrain_enabled" in raw_settings:
        settings["terrain_enabled"] = normalize_bool_flag(raw_settings.get("terrain_enabled")) == "true"

    terrain_exaggeration = finite_number(raw_settings.get("terrain_exaggeration"), 1.0)
    settings["terrain_exaggeration"] = max(0.5, min(3.0, terrain_exaggeration))

    map_view = raw_settings.get("map_view")
    if isinstance(map_view, dict):
        lng = finite_number(map_view.get("lng"), 999.0)
        lat = finite_number(map_view.get("lat"), 999.0)
        zoom = finite_number(map_view.get("zoom"), -1.0)
        if -180 <= lng <= 180 and -90 <= lat <= 90 and 0 <= zoom <= 22:
            settings["map_view"] = {
                "lng": round(lng, 6),
                "lat": round(lat, 6),
                "zoom": round(zoom, 3),
                "bearing": round(finite_number(map_view.get("bearing"), 0.0), 2),
                "pitch": round(max(0.0, min(85.0, finite_number(map_view.get("pitch"), 0.0))), 2),
            }

    return settings


def settings_for_device(device_id: str) -> dict[str, object]:
    devices = read_devices()
    device = devices.get(device_id.strip(), {})
    return sanitize_device_settings(device.get("settings", {}))


def update_device_settings(device_id: str, raw_settings: object) -> tuple[bool, dict[str, object]]:
    device_key = device_id.strip()
    if not device_key:
        return False, {}
    devices = read_devices()
    device = devices.get(device_key)
    if not device:
        return False, {}
    settings = sanitize_device_settings(raw_settings)
    device["settings"] = settings
    device["last_seen_at"] = utc_now()
    devices[device_key] = device
    write_devices(devices)
    return True, settings


def admin_message(message: str) -> None:
    with RUN_LOCK:
        RUN_STATE["last_message"] = message


def user_display_name(user: dict[str, str]) -> str:
    name = user.get("name", "").strip()
    return name or user.get("username", "")


def device_username(device: dict[str, str]) -> str:
    return normalize_user_id(str(device.get("username", device.get("email", ""))))


def devices_for_user(devices: dict[str, dict[str, str]], username: str) -> list[tuple[str, dict[str, str]]]:
    user_id = normalize_user_id(username)
    user_devices = [
        (device_id, device)
        for device_id, device in devices.items()
        if device_username(device) == user_id
    ]
    return sorted(user_devices, key=lambda item: str(item[1].get("last_seen_at", "")), reverse=True)


def delete_devices_for_user(username: str) -> int:
    user_id = normalize_user_id(username)
    devices = read_devices()
    device_ids = [device_id for device_id, device in devices.items() if device_username(device) == user_id]
    for device_id in device_ids:
        devices.pop(device_id, None)
    write_devices(devices)
    return len(device_ids)


def set_user_password(user: dict[str, str], password: str) -> None:
    if password:
        user["password"] = hash_password(password)
        user["must_change_password"] = "false"


def create_user(username: str, name: str, email: str, password: str, role: str, enabled: str, max_devices: str) -> str:
    user_id = normalize_user_id(username)
    if not user_id:
        return "Username is required."
    if not password:
        return "Password is required for new users."

    users = read_users()
    if user_id in users:
        return f"User {user_id} already exists."

    normalized_role = normalize_role(role)
    users[user_id] = {
        "username": user_id,
        "name": name.strip(),
        "email": normalize_user_id(email) if email.strip() else "",
        "password": hash_password(password),
        "role": normalized_role,
        "enabled": normalize_enabled(enabled),
        "max_devices": str(parse_max_devices(max_devices, normalized_role)),
        "must_change_password": "false",
    }
    write_users(users)
    return f"Created user {user_id}."


def update_user(username: str, name: str, email: str, role: str, enabled: str, max_devices: str) -> str:
    user_id = normalize_user_id(username)
    users = read_users()
    user = users.get(user_id)
    if not user:
        return f"User {user_id or '-'} was not found."

    normalized_role = normalize_role(role)
    user.update(
        {
            "name": name.strip(),
            "email": normalize_user_id(email) if email.strip() else "",
            "role": normalized_role,
            "enabled": normalize_enabled(enabled),
            "max_devices": str(parse_max_devices(max_devices, normalized_role)),
        }
    )
    write_users(users)
    return f"Updated user {user_id}."


def delete_user(username: str) -> str:
    user_id = normalize_user_id(username)
    users = read_users()
    if user_id not in users:
        return f"User {user_id or '-'} was not found."
    users.pop(user_id, None)
    write_users(users)
    deleted_count = delete_devices_for_user(user_id)
    return f"Deleted user {user_id} and {deleted_count} device(s)."


def set_admin_user_password(username: str, password: str) -> str:
    user_id = normalize_user_id(username)
    if not password:
        return "Password is required."
    users = read_users()
    user = users.get(user_id)
    if not user:
        return f"User {user_id or '-'} was not found."
    set_user_password(user, password)
    write_users(users)
    deleted_count = delete_devices_for_user(user_id)
    return f"Set password for {user_id} and deleted {deleted_count} device(s)."


def require_user_password_change(username: str) -> str:
    user_id = normalize_user_id(username)
    users = read_users()
    user = users.get(user_id)
    if not user:
        return f"User {user_id or '-'} was not found."
    user["must_change_password"] = "true"
    write_users(users)
    deleted_count = delete_devices_for_user(user_id)
    return f"Reset password for {user_id}; deleted {deleted_count} device(s). User must choose a new password on next sign-in."


def change_required_password(
    username: str,
    current_password: str,
    new_password: str,
    device_id: str,
    user_agent: str,
) -> tuple[int, dict[str, object]]:
    users = read_users()
    user_id = normalize_user_id(username)
    user = users.get(user_id)
    if not user or user.get("enabled", "true").lower() != "true":
        return 401, {"ok": False, "error": "Invalid user or password."}
    if user.get("must_change_password", "false").lower() != "true":
        return 400, {"ok": False, "error": "Password change is not required for this user."}
    if not verify_password(current_password, user.get("password", "")):
        return 401, {"ok": False, "error": "Invalid user or password."}
    if not new_password:
        return 400, {"ok": False, "error": "New password is required."}
    if verify_password(new_password, user.get("password", "")):
        return 400, {"ok": False, "error": "New password must be different from the current password."}

    set_user_password(user, new_password)
    write_users(users)
    delete_devices_for_user(user_id)
    return login_user(user_id, new_password, device_id, user_agent)


def delete_device(device_id: str) -> str:
    device_key = device_id.strip()
    devices = read_devices()
    if device_key not in devices:
        return "Device was not found."
    device = devices.pop(device_key)
    write_devices(devices)
    username = device_username(device) or "-"
    return f"Deleted device for {username}."


def delete_user_devices(username: str) -> str:
    user_id = normalize_user_id(username)
    deleted_count = delete_devices_for_user(user_id)
    return f"Deleted {deleted_count} device(s) for {user_id or '-'}."


def role_options(selected_role: str) -> str:
    selected = normalize_role(selected_role)
    options = []
    for role in ("free", "basic", "pro", "admin"):
        selected_attr = " selected" if role == selected else ""
        options.append(f'<option value="{role}"{selected_attr}>{role}</option>')
    return "".join(options)


def enabled_options(selected_enabled: str) -> str:
    enabled = normalize_enabled(selected_enabled)
    options = []
    for value, label in (("true", "Enabled"), ("false", "Disabled")):
        selected_attr = " selected" if value == enabled else ""
        options.append(f'<option value="{value}"{selected_attr}>{label}</option>')
    return "".join(options)


def new_device_id() -> str:
    return secrets.token_urlsafe(24)


def new_session_token() -> str:
    return secrets.token_urlsafe(AUTH_TOKEN_BYTES)


def authenticate_session(token: str, device_id: str) -> tuple[bool, dict[str, str] | None]:
    if not token or not device_id:
        return False, None

    devices = read_devices()
    device = devices.get(device_id)
    if not device or str(device.get("enabled", "true")).lower() != "true":
        return False, None
    if not secrets.compare_digest(str(device.get("token_hash", "")), token_hash(token)):
        return False, None

    users = read_users()
    user = users.get(normalize_user_id(str(device.get("username", device.get("email", "")))))
    if not user or user.get("enabled", "true").lower() != "true":
        return False, None
    if user.get("must_change_password", "false").lower() == "true":
        return False, None

    device["last_seen_at"] = utc_now()
    write_devices(devices)
    return True, {
        "username": user["username"],
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "free"),
    }


def login_user(username: str, password: str, device_id: str, user_agent: str) -> tuple[int, dict[str, object]]:
    users = read_users()
    should_rewrite_users = False
    user_id = normalize_user_id(username)
    user = users.get(user_id)
    if not user or user.get("enabled", "true").lower() != "true":
        return 401, {"ok": False, "error": "Invalid user or password."}
    if not verify_password(password, user.get("password", "")):
        return 401, {"ok": False, "error": "Invalid user or password."}

    if not user["password"].startswith("pbkdf2_sha256$"):
        user["password"] = hash_password(password)
        should_rewrite_users = True
    if should_rewrite_users:
        write_users(users)

    if user.get("must_change_password", "false").lower() == "true":
        delete_devices_for_user(user_id)
        return 403, {
            "ok": False,
            "code": "password_change_required",
            "error": "Password change is required.",
            "username": user_id,
        }

    devices = read_devices()
    role = normalize_role(user.get("role", "free"))
    max_devices = user_max_devices(user)
    requested_device_id = device_id.strip() or new_device_id()
    existing_device = devices.get(requested_device_id)

    existing_device_username = normalize_user_id(str(existing_device.get("username", existing_device.get("email", "")))) if existing_device else ""
    if existing_device and existing_device_username != user_id:
        return 403, {"ok": False, "error": "This device is already assigned to another user."}

    active_user_devices = [
        entry
        for entry in devices.values()
        if normalize_user_id(str(entry.get("username", entry.get("email", "")))) == user_id
        and str(entry.get("enabled", "true")).lower() == "true"
    ]
    if max_devices > 0 and not existing_device and len(active_user_devices) >= max_devices:
        return 403, {
            "ok": False,
            "error": f"This user has reached the maximum number of devices ({max_devices}).",
        }

    session_token = new_session_token()
    now = utc_now()
    if not existing_device:
        existing_device = {
            "username": user_id,
            "email": user.get("email", ""),
            "device_id": requested_device_id,
            "role": role,
            "created_at": now,
            "enabled": "true",
        }
    existing_device.update(
        {
            "username": user_id,
            "email": user.get("email", ""),
            "role": role,
            "user_agent": user_agent[:500],
            "last_seen_at": now,
            "token_hash": token_hash(session_token),
        }
    )
    devices[requested_device_id] = existing_device
    write_devices(devices)
    return 200, {
        "ok": True,
        "username": user_id,
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": role,
        "max_devices": max_devices,
        "device_id": requested_device_id,
        "session_token": session_token,
    }


def content_type_for(path: Path) -> str:
    if path.name.endswith(".geojson"):
        return "application/geo+json"
    if path.name.endswith(".js"):
        return "application/javascript"
    if path.name.endswith(".css"):
        return "text/css"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def is_safe_maplibre_data_name(name: str) -> bool:
    return name == "source_status.json" or re.fullmatch(r"\d{2}d\.geojson", name) is not None


def auth_required_config_js() -> str:
    return (
        "window.RAINMAPPER_CONFIG = "
        + json.dumps(
            {
                "authRequired": True,
                "authBase": "/auth",
                "dataBase": "data/",
            }
        )
        + ";\n"
    )


def public_viewer_config_js() -> str:
    return "window.RAINMAPPER_CONFIG = " + json.dumps({}) + ";\n"


def remove_legacy_public_maplibre_data() -> None:
    """Remove public MapLibre data once protected-only access is enforced.

    The protected MapLibre viewer loads GeoJSON through /protected/maplibre/data/*.
    This helper is intentionally kept ready, but not called during the current
    transition, so /local/rainmapper-maplibre remains a working fallback while
    Cloudflared access through port 8099 is validated.
    """
    shutil.rmtree(PUBLIC_MAPLIBRE_PATH / "data", ignore_errors=True)


def preserve_public_maplibre_data_for_transition() -> None:
    """Document the temporary public MapLibre fallback.

    TODO: replace calls to this function with remove_legacy_public_maplibre_data()
    once the protected Cloudflared route is validated in Home Assistant.
    """
    return None


class RainmapperHandler(BaseHTTPRequestHandler):
    server_version = "Rainmapper/0.2"

    def log_message(self, format: str, *args: object) -> None:
        pass

    def send_bytes(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status: int, payload: dict) -> None:
        self.send_bytes(
            status,
            json.dumps(payload).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def read_json_payload(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw_payload = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def auth_credentials(self) -> tuple[str, str]:
        authorization = self.headers.get("Authorization", "").strip()
        token = ""
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        device_id = self.headers.get("X-Rainmapper-Device", "").strip()
        return token, device_id

    def authenticated_user(self) -> dict[str, str] | None:
        token, device_id = self.auth_credentials()
        ok, user = authenticate_session(token, device_id)
        return user if ok else None

    def require_authentication(self) -> dict[str, str] | None:
        user = self.authenticated_user()
        if user:
            return user
        self.send_json(401, {"ok": False, "error": "Authentication required."})
        return None

    def serve_static_file(self, file_path: Path) -> None:
        if not file_path.is_file():
            self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
            return
        self.send_bytes(200, file_path.read_bytes(), content_type_for(file_path))

    def redirect_home(self) -> None:
        self.send_response(303)
        self.send_header("Location", "./")
        self.end_headers()

    def redirect_to(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def render_settings(self) -> None:
        settings_links = addon_settings_links()
        primary_label, primary_url = settings_links[0]
        primary_link = (
            f'<p><a class="button-link primary" target="_top" href="{html.escape(primary_url, quote=True)}">'
            f"{html.escape(primary_label)}</a></p>"
        )
        fallback_links = []
        for label, url in settings_links[1:]:
            fallback_links.append(
                f'<p><a class="button-link" target="_top" href="{html.escape(url, quote=True)}">'
                f"{html.escape(label)}</a></p>"
            )
        fallback_html = ""
        if fallback_links:
            fallback_html = (
                "<details>"
                "<summary>Advanced fallback links</summary>"
                "<p>Use these only if the recommended link does not work in this Home Assistant installation.</p>"
                f"{''.join(fallback_links)}"
                "</details>"
            )
        body = f"""
        <h1>App settings</h1>
        <p>Open the Rainmapper configuration page in Home Assistant.</p>
        {primary_link}
        {fallback_html}
        <p><a class="button-link" href="./">Back to Rainmapper</a></p>
        """
        self.send_bytes(200, html_page("App settings", body, auto_refresh=False), "text/html; charset=utf-8")

    def render_users(self) -> None:
        users = read_users()
        devices = read_devices()

        rows = []
        for username, user in sorted(users.items()):
            user_devices = devices_for_user(devices, username)
            enabled = normalize_enabled(user.get("enabled", "true"))
            max_devices = str(user_max_devices(user))
            role = normalize_role(user.get("role", "free"))
            password_state = (
                '<span class="danger">Change required</span>'
                if user.get("must_change_password", "false").lower() == "true"
                else '<span class="ok">Current</span>'
            )
            device_rows = []
            for device_id, device in user_devices:
                device_label = device_id[:12] + ("..." if len(device_id) > 12 else "")
                user_agent = str(device.get("user_agent", ""))
                last_seen_at = str(device.get("last_seen_at", "-")) or "-"
                created_at = str(device.get("created_at", "-")) or "-"
                device_search_text = " ".join(
                    [
                        device_id,
                        str(device.get("username", "")),
                        str(device.get("email", "")),
                        user_agent,
                        created_at,
                        last_seen_at,
                    ]
                )
                device_rows.append(
                    f'<div class="device-row" data-device-search="{html.escape(device_search_text, quote=True)}">'
                    f"<strong>{html.escape(device_label)}</strong>"
                    f'<span class="meta">Created {html.escape(created_at)} · Last seen {html.escape(last_seen_at)}</span>'
                    f'<span class="meta">{html.escape(user_agent[:120])}</span>'
                    '<form method="post" action="">'
                    '<input type="hidden" name="admin_action" value="delete_device">'
                    f'<input type="hidden" name="device_id" value="{html.escape(device_id, quote=True)}">'
                    '<button>Delete device</button>'
                    "</form>"
                    "</div>"
                )
            devices_html = "".join(device_rows) or '<span class="meta">No registered devices</span>'
            if device_rows:
                devices_html += '<span class="device-filter-note">Showing matching devices only.</span>'
            user_search_text = " ".join(
                [
                    username,
                    user_display_name(user),
                    user.get("email", ""),
                    role,
                    "enabled" if enabled == "true" else "disabled",
                    "change required" if user.get("must_change_password", "false").lower() == "true" else "current",
                    max_devices,
                    str(len(user_devices)),
                ]
            )
            rows.append(
                f'<tr class="user-row" data-user-search="{html.escape(user_search_text, quote=True)}">'
                f"<td><strong>{html.escape(username)}</strong><span class=\"meta\">{html.escape(user_display_name(user))}</span></td>"
                f"<td>{html.escape(user.get('email', ''))}</td>"
                f"<td>{html.escape(role)}</td>"
                f"<td>{'Enabled' if enabled == 'true' else 'Disabled'}</td>"
                f"<td>{password_state}</td>"
                f"<td>{html.escape(max_devices)}</td>"
                f"<td>{len(user_devices)}</td>"
                '<td class="admin-actions">'
                '<form method="post" action="">'
                '<input type="hidden" name="admin_action" value="update_user">'
                f'<input type="hidden" name="username" value="{html.escape(username, quote=True)}">'
                '<div class="admin-form-grid">'
                f'<div class="admin-field"><label>Name</label><input name="name" value="{html.escape(user.get("name", ""), quote=True)}"></div>'
                f'<div class="admin-field"><label>Email</label><input name="email" value="{html.escape(user.get("email", ""), quote=True)}"></div>'
                f'<div class="admin-field"><label>Role</label><select name="role">{role_options(role)}</select></div>'
                f'<div class="admin-field"><label>Status</label><select name="enabled">{enabled_options(enabled)}</select></div>'
                f'<div class="admin-field"><label>Max devices</label><input name="max_devices" type="number" min="0" value="{html.escape(max_devices, quote=True)}"></div>'
                "</div>"
                '<button class="primary">Save user</button>'
                "</form>"
                '<form class="inline-form" method="post" action="">'
                '<input type="hidden" name="admin_action" value="set_password">'
                f'<input type="hidden" name="username" value="{html.escape(username, quote=True)}">'
                f'<input id="reset-password-{html.escape(username, quote=True)}" name="password" type="password" placeholder="New password" autocomplete="new-password">'
                '<label class="password-tools">'
                f'<input type="checkbox" data-target="reset-password-{html.escape(username, quote=True)}" onchange="togglePasswordVisibility(this)">'
                '<span>Show typed password</span>'
                '</label>'
                '<button>Set password</button>'
                "</form>"
                '<form method="post" action="">'
                '<input type="hidden" name="admin_action" value="reset_password">'
                f'<input type="hidden" name="username" value="{html.escape(username, quote=True)}">'
                '<button>Reset password</button>'
                "</form>"
                '<form method="post" action="">'
                '<input type="hidden" name="admin_action" value="delete_user_devices">'
                f'<input type="hidden" name="username" value="{html.escape(username, quote=True)}">'
                '<button>Delete all devices</button>'
                "</form>"
                '<form method="post" action="">'
                '<input type="hidden" name="admin_action" value="delete_user">'
                f'<input type="hidden" name="username" value="{html.escape(username, quote=True)}">'
                '<button>Delete user</button>'
                "</form>"
                "</td>"
                f"<td>{devices_html}</td>"
                "</tr>"
            )

        user_rows_html = "".join(rows) if rows else '<tr><td colspan="9">No users configured.</td></tr>'
        users_table = (
            '<div class="admin-table-wrap"><table id="users-table" class="admin-table">'
            "<thead><tr><th>User</th><th>Email</th><th>Role</th><th>Status</th><th>Password</th><th>Max</th><th>Devices</th><th>Manage user</th><th>Devices</th></tr></thead>"
            f"<tbody>{user_rows_html}</tbody>"
            "</table></div>"
        )
        body = f"""
        <div class="users-toolbar">
          <a class="button-link" href="./">Back</a>
          <button id="users-refresh" type="button" onclick="refreshUsersPage()">Refresh</button>
          <input id="users-filter" class="users-filter" type="search" placeholder="Search users or devices">
          <span class="users-toolbar-status"><span id="users-filter-status">{len(users)} users</span> · <span id="users-refresh-status">Manual refresh</span></span>
        </div>
        <h1>Users</h1>
        <p>Manage MapLibre protected viewer users and registered devices.</p>
        <div id="users-content">
          <h2>Create user</h2>
          <p class="help-text">Stored passwords cannot be viewed because Rainmapper saves password hashes. Set password stores an admin-defined password and deletes registered devices. Reset password forces the user to choose a different password on next sign-in.</p>
          <form method="post" action="">
            <input type="hidden" name="admin_action" value="create_user">
            <div class="admin-form-grid">
              <div class="admin-field"><label>Username</label><input name="username" required autocomplete="username"></div>
              <div class="admin-field"><label>Name</label><input name="name"></div>
              <div class="admin-field"><label>Email</label><input name="email" type="email"></div>
              <div class="admin-field">
                <label>Password</label>
                <input id="create-password" name="password" type="password" required autocomplete="new-password">
                <label class="password-tools"><input type="checkbox" data-target="create-password" onchange="togglePasswordVisibility(this)"><span>Show typed password</span></label>
              </div>
              <div class="admin-field"><label>Role</label><select name="role">{role_options("free")}</select></div>
              <div class="admin-field"><label>Status</label><select name="enabled">{enabled_options("true")}</select></div>
              <div class="admin-field"><label>Max devices</label><input name="max_devices" type="number" min="0" value="1"></div>
            </div>
            <button class="primary">Create user</button>
          </form>
          <h2>Existing users</h2>
          <div id="users-empty-filter" class="users-empty-filter">No users or devices match the current search.</div>
          {users_table}
        </div>
        """
        self.send_bytes(200, html_page("Users", body, auto_refresh=False), "text/html; charset=utf-8")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            self.render_index()
            return

        if path == "/settings":
            self.render_settings()
            return

        if path == "/users":
            self.render_users()
            return

        if path == "/auth/session":
            user = self.authenticated_user()
            if not user:
                self.send_json(401, {"ok": False, "error": "Authentication required."})
                return
            self.send_json(200, {"ok": True, "user": user})
            return

        if path == "/auth/device-settings":
            user = self.authenticated_user()
            if not user:
                self.send_json(401, {"ok": False, "error": "Authentication required."})
                return
            _token, device_id = self.auth_credentials()
            self.send_json(200, {"ok": True, "settings": settings_for_device(device_id)})
            return

        if path.startswith("/protected/maplibre"):
            self.serve_protected_maplibre(path.removeprefix("/protected/maplibre"))
            return

        if path.startswith("/file/"):
            self.serve_plot(path.removeprefix("/file/"))
            return

        self.send_bytes(
            404,
            html_page("Not found", "<h1>Not found</h1><p>This Rainmapper page does not exist.</p>", auto_refresh=False),
            "text/html; charset=utf-8",
        )

    def read_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        payload = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
        return parse_qs(payload)

    def form_value(self, form: dict[str, list[str]], name: str) -> str:
        values = form.get(name, [])
        return values[0] if values else ""

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/auth/login":
            payload = self.read_json_payload()
            status, response = login_user(
                str(payload.get("username", payload.get("email", ""))),
                str(payload.get("password", "")),
                str(payload.get("device_id", "")),
                self.headers.get("User-Agent", ""),
            )
            self.send_json(status, response)
            return

        if parsed.path == "/auth/change-password":
            payload = self.read_json_payload()
            status, response = change_required_password(
                str(payload.get("username", "")),
                str(payload.get("current_password", "")),
                str(payload.get("new_password", "")),
                str(payload.get("device_id", "")),
                self.headers.get("User-Agent", ""),
            )
            self.send_json(status, response)
            return

        if parsed.path == "/auth/session":
            user = self.authenticated_user()
            if not user:
                self.send_json(401, {"ok": False, "error": "Authentication required."})
                return
            self.send_json(200, {"ok": True, "user": user})
            return

        if parsed.path == "/auth/device-settings":
            user = self.authenticated_user()
            if not user:
                self.send_json(401, {"ok": False, "error": "Authentication required."})
                return
            _token, device_id = self.auth_credentials()
            payload = self.read_json_payload()
            ok, settings = update_device_settings(device_id, payload.get("settings", payload))
            if not ok:
                self.send_json(404, {"ok": False, "error": "Device was not found."})
                return
            self.send_json(200, {"ok": True, "settings": settings})
            return

        if parsed.path == "/auth/logout":
            self.logout_current_device()
            return

        form = self.read_form()
        if parsed.path.rstrip("/") == "/users":
            self.handle_user_admin_post(form)
            self.redirect_to("./users")
            return

        action = self.form_value(form, "run_action")
        if action:
            run_action(action, "web")
            self.redirect_home()
            return

        station_action = self.form_value(form, "station_action")
        station_group = self.form_value(form, "station_group")
        if station_action in {"enable", "disable"} and station_group in {"404", "parse"}:
            with RUN_LOCK:
                running = RUN_STATE["running"]
            if not running:
                changed = update_station_group(station_group, enable=station_action == "enable")
                with RUN_LOCK:
                    RUN_STATE["last_message"] = f"Updated {changed} station line(s) in stations.txt."
            self.redirect_home()
            return

        self.redirect_home()

    def handle_user_admin_post(self, form: dict[str, list[str]]) -> None:
        admin_action = self.form_value(form, "admin_action")
        if admin_action == "create_user":
            message = create_user(
                self.form_value(form, "username"),
                self.form_value(form, "name"),
                self.form_value(form, "email"),
                self.form_value(form, "password"),
                self.form_value(form, "role"),
                self.form_value(form, "enabled"),
                self.form_value(form, "max_devices"),
            )
        elif admin_action == "update_user":
            message = update_user(
                self.form_value(form, "username"),
                self.form_value(form, "name"),
                self.form_value(form, "email"),
                self.form_value(form, "role"),
                self.form_value(form, "enabled"),
                self.form_value(form, "max_devices"),
            )
        elif admin_action == "set_password":
            message = set_admin_user_password(
                self.form_value(form, "username"),
                self.form_value(form, "password"),
            )
        elif admin_action == "reset_password":
            message = require_user_password_change(self.form_value(form, "username"))
        elif admin_action == "delete_device":
            message = delete_device(self.form_value(form, "device_id"))
        elif admin_action == "delete_user_devices":
            message = delete_user_devices(self.form_value(form, "username"))
        elif admin_action == "delete_user":
            message = delete_user(self.form_value(form, "username"))
        else:
            message = "Unknown user management action."
        admin_message(message)

    def render_index(self) -> None:
        with RUN_LOCK:
            running = RUN_STATE["running"]
            action = RUN_STATE["action"] or "-"
            message = RUN_STATE["last_message"]
            started_at = RUN_STATE["started_at"] or "-"
            finished_at = RUN_STATE["finished_at"] or "-"
            duration = RUN_STATE["duration"] or format_duration(RUN_STATE["started_at"], RUN_STATE["finished_at"])
            exit_code = RUN_STATE["exit_code"] or "-"
            last_published_at = RUN_STATE["last_published_at"] or "-"
            last_publish_message = RUN_STATE["last_publish_message"]
            current_step = RUN_STATE["current_step"] or "-"
            progress_current = RUN_STATE["progress_current"]
            progress_total = RUN_STATE["progress_total"]
            progress_percent = RUN_STATE["progress_percent"]

        status_class = "ok" if not running else "danger"
        status_text = "Running" if running else "Idle"
        disabled = "disabled" if running else ""

        controls = f"""
        <form method="post" action=""><input type="hidden" name="run_action" value="update"><button {disabled}>Run update</button></form>
        <form method="post" action=""><input type="hidden" name="run_action" value="maps"><button {disabled}>Generate maps</button></form>
        <form method="post" action=""><input type="hidden" name="run_action" value="all"><button class="primary" {disabled}>Run all</button></form>
        <a class="button-link" href="./settings">App settings</a>
        <a class="button-link" href="./users">Users</a>
        """

        if progress_percent and progress_total:
            progress_value = html.escape(progress_percent)
            progress_label = html.escape(f"{progress_percent}% ({progress_current}/{progress_total})")
            progress_html = (
                f'<span class="value">{progress_label}</span>'
                f'<progress max="100" value="{progress_value}"></progress>'
            )
        else:
            progress_html = '<span class="value">-</span><span class="progress-text">No active station progress</span>'

        station_groups = failed_wunderground_groups()
        disabled_groups = disabled_station_groups()
        active_station_groups = {
            group_name: sorted(set(station_groups[group_name]) - set(disabled_groups[group_name]))
            for group_name in ("404", "parse")
        }
        station_controls = (
            station_group_card("Wunderground 404", "404", active_station_groups["404"], disabled_groups["404"], disabled)
            + station_group_card("Wunderground parse errors", "parse", active_station_groups["parse"], disabled_groups["parse"], disabled)
        )
        source_controls = source_status_cards()
        leaflet_url = cache_busted_url("/local/rainmapper-leaflet/index.html")
        maplibre_url = cache_busted_url("/protected/maplibre/index.html")
        aemet_maplibre_url = cache_busted_url("/local/rainmapper-maplibre-aemet/index.html") if PUBLIC_MAPLIBRE_AEMET_PATH.exists() else ""
        bokeh_21d_url = cache_busted_url("/local/Plots/rain_21d.html")
        aemet_card = (
            f'<div class="card"><span class="label">AEMET test viewer</span><span class="value">{html.escape(aemet_maplibre_url)}</span></div>'
            if aemet_maplibre_url
            else ""
        )
        aemet_viewer_link = (
            f'<a class="button-link" href="{html.escape(aemet_maplibre_url, quote=True)}" target="_top">Open AEMET test viewer</a>'
            if aemet_maplibre_url
            else ""
        )

        status = f"""
        <div class="status-grid">
          <div class="status-row status-row-primary">
            <div class="card"><span class="label">Version</span><span class="value">{html.escape(app_version())}</span></div>
            <div class="card"><span class="label">Status</span><span class="value {status_class}">{status_text}</span></div>
            <div class="card"><span class="label">Action</span><span class="value">{html.escape(action)}</span></div>
            <div class="card"><span class="label">Started</span><span class="value">{html.escape(started_at)}</span></div>
            <div class="card"><span class="label">Finished</span><span class="value">{html.escape(finished_at)}</span></div>
            <div class="card"><span class="label">Duration</span><span class="value">{html.escape(duration)}</span></div>
          </div>
          <div class="status-row status-row-secondary">
            <div class="card"><span class="label">Current step</span><span class="value">{html.escape(current_step)}</span></div>
            <div class="card"><span class="label">Progress</span>{progress_html}</div>
            <div class="card"><span class="label">Exit code</span><span class="value">{html.escape(exit_code)}</span></div>
            <div class="card"><span class="label">Next schedule</span><span class="value">{html.escape(next_schedule_text())}</span></div>
          </div>
          <div class="status-row status-row-publication">
            <div class="card"><span class="label">Bokeh maps</span><span class="value">/local/Plots</span></div>
            <div class="card"><span class="label">Leaflet viewer</span><span class="value">{html.escape(leaflet_url)}</span></div>
            <div class="card"><span class="label">MapLibre viewer</span><span class="value">{html.escape(maplibre_url)}</span></div>
            {aemet_card}
            <div class="card"><span class="label">Last published</span><span class="value">{html.escape(last_published_at)}</span></div>
          </div>
        </div>
        {source_controls}
        <div class="station-grid">
          {station_controls}
        </div>
        <p>{html.escape(message)}</p>
        <p>{html.escape(last_publish_message)}</p>
        """

        body = (
            "<h1>Rainmapper</h1>"
            "<p>Update weather data, generate maps, and browse generated HTML maps.</p>"
            "<h2>Actions</h2>"
            f"{controls}"
            "<h2>Status</h2>"
            f"{status}"
            "<h2>Viewers</h2>"
            '<div class="viewer-actions">'
            f'<a class="button-link primary" href="{html.escape(leaflet_url, quote=True)}" target="_top">Open Leaflet viewer</a>'
            f'<a class="button-link primary" href="{html.escape(maplibre_url, quote=True)}" target="_top">Open MapLibre viewer</a>'
            f"{aemet_viewer_link}"
            f'<a class="button-link" href="{html.escape(bokeh_21d_url, quote=True)}" target="_top">Open Bokeh 21 days</a>'
            "</div>"
            '<h2 id="maps">Maps</h2>'
            f"{self.render_map_list()}"
            "<h2>Last log</h2>"
            f"<pre>{html.escape(read_log())}</pre>"
        )
        self.send_bytes(200, html_page("Rainmapper", body), "text/html; charset=utf-8")

    def logout_current_device(self) -> None:
        _token, device_id = self.auth_credentials()
        devices = read_devices()
        device = devices.get(device_id)
        if device:
            device.pop("token_hash", None)
            device["last_seen_at"] = utc_now()
            write_devices(devices)
        self.send_json(200, {"ok": True})

    def serve_protected_maplibre(self, requested_path: str) -> None:
        relative_path = requested_path.lstrip("/") or "index.html"
        if relative_path == "config.js":
            self.send_bytes(200, auth_required_config_js().encode("utf-8"), "application/javascript")
            return

        if relative_path.startswith("data/"):
            if not self.require_authentication():
                return
            data_name = relative_path.removeprefix("data/")
            if "/" in data_name or "\\" in data_name or not is_safe_maplibre_data_name(data_name):
                self.send_json(400, {"ok": False, "error": "Invalid data file."})
                return
            data_path = SOURCE_STATUS_PATH if data_name == "source_status.json" else PUBLIC_DATA_PATH / data_name
            self.serve_static_file(data_path)
            return

        if "/" in relative_path or "\\" in relative_path:
            self.send_bytes(400, b"Invalid file name", "text/plain; charset=utf-8")
            return

        if relative_path not in {"index.html", "app.js", "style.css", "translations.json"}:
            self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
            return
        self.serve_static_file(MAPLIBRE_VIEWER_ASSETS_PATH / relative_path)

    def render_map_list(self) -> str:
        files = sorted(PLOTS_PATH.glob("*.html"))
        if not files:
            return (
                '<div class="empty">No HTML maps found in '
                '<code>/share/rainmapper/Plots</code>.</div>'
            )

        items = []
        for file_path in files:
            stat = file_path.stat()
            name = file_path.name
            title = name.removesuffix(".html").replace("_", " ")
            generated_at = format_datetime_from_timestamp(stat.st_mtime)
            items.append(
                "<li>"
                f'<a class="map-link" href="file/{html.escape(name)}">'
                f"{html.escape(title)}"
                f'<span class="meta">{html.escape(name)} - {format_size(stat.st_size)} - {html.escape(generated_at)}</span>'
                "</a>"
                "</li>"
            )
        return "<ul>" + "".join(items) + "</ul>"

    def serve_plot(self, requested_name: str) -> None:
        name = unquote(requested_name)
        if "/" in name or "\\" in name or not name.endswith(".html"):
            self.send_bytes(400, b"Invalid file name", "text/plain; charset=utf-8")
            return

        file_path = PLOTS_PATH / name
        if not file_path.is_file():
            self.send_bytes(404, b"Map not found", "text/plain; charset=utf-8")
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "text/html"
        self.send_bytes(200, file_path.read_bytes(), content_type)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Rainmapper generated HTML maps.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()

    preserve_public_maplibre_data_for_transition()

    scheduler = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler.start()

    server = ThreadingHTTPServer((args.host, args.port), RainmapperHandler)
    shutdown_requested = False

    def shutdown_after_action_finishes() -> None:
        while action_is_running():
            time.sleep(1)
        server.shutdown()

    def handle_shutdown(signum: int, _frame: object) -> None:
        nonlocal shutdown_requested
        signal_name = signal.Signals(signum).name
        if shutdown_requested:
            print(f"Received {signal_name} again; forcing Rainmapper subprocess termination.", flush=True)
            terminate_current_process()
            threading.Thread(target=server.shutdown, daemon=True).start()
            return

        shutdown_requested = True
        print(f"Received {signal_name}; stopping scheduler and preparing clean shutdown.", flush=True)
        SHUTDOWN_EVENT.set()
        if action_is_running():
            print("Rainmapper action is still running; waiting for it to finish before stopping.", flush=True)
            threading.Thread(target=shutdown_after_action_finishes, daemon=True).start()
            return

        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    print(f"Rainmapper server listening on {args.host}:{args.port}")
    print(f"Schedule enabled: {bool_env('RAINMAPPER_SCHEDULE_ENABLED')}")
    print(f"Next schedule: {next_schedule_text()}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
        print("Rainmapper server stopped cleanly.", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
