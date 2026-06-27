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
from datetime import UTC, datetime, timedelta
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
PUBLIC_MAPLIBRE_HEATMAP_PATH = Path("/config/www/rainmapper-maplibre-heatmap")
PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH = Path("/config/www/.rainmapper-maplibre-heatmap-tmp")
PUBLIC_MAPLIBRE_AEMET_PATH = Path("/config/www/rainmapper-maplibre-aemet")
PUBLIC_MAPLIBRE_AEMET_TMP_PATH = Path("/config/www/.rainmapper-maplibre-aemet-tmp")
AEMET_EXPERIMENT_TOMAP_PATH = Path("/tmp/rainmapper-aemet-tomap")
AEMET_EXPERIMENT_DATA_PATH = Path("/tmp/rainmapper-aemet-publicdata")
# Temporary rollback hook while production AEMET is validated. Set this to True
# only if the old public AEMET test viewer must be re-enabled.
PUBLISH_AEMET_EXPERIMENTAL_MAPLIBRE = False
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
DEVICE_SETTING_LAYER_METRICS = {"rain", "max_temp", "min_temp", "max_humidity", "min_humidity", "wind"}
DEVICE_SETTING_HEATMAP_WEIGHT_CURVES = {"linear", "soft", "strong"}
DEVICE_SETTING_ESTIMATED_FIELD_RADII = {"small", "medium", "large"}
DEVICE_SETTING_ESTIMATED_FIELD_QUALITIES = {"low", "medium", "high"}
DEVICE_SETTING_ESTIMATED_FIELD_SMOOTHING = {"smooth", "balanced", "local"}
UPDATE_SOURCE_FLAGS = {
    "Meteoclimatic": "create_meteoclimatic",
    "Meteocat": "create_meteocat",
    "Wunderground": "create_wunderground",
    "AEMET": "create_aemet",
}

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
    "users_flash": "",
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


def maplibre_hover_zoom() -> float:
    try:
        configured = float(env("RAINMAPPER_MAPLIBRE_HOVER_ZOOM", "6"))
    except ValueError:
        configured = 6.0
    return max(0, min(22, configured))


def percent_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        configured = int(env(name, str(default)))
    except ValueError:
        configured = default
    return max(minimum, min(maximum, configured))


def maplibre_heatmap_defaults() -> dict:
    weight_curve = env("RAINMAPPER_MAPLIBRE_HEATMAP_WEIGHT_CURVE", "soft").strip()
    if weight_curve not in DEVICE_SETTING_HEATMAP_WEIGHT_CURVES:
        weight_curve = "soft"
    return {
        "weightCurve": weight_curve,
        "opacity": percent_env("RAINMAPPER_MAPLIBRE_HEATMAP_OPACITY", 65, 0, 100) / 100,
        "radiusScale": percent_env("RAINMAPPER_MAPLIBRE_HEATMAP_RADIUS", 90, 50, 300) / 100,
        "intensityScale": percent_env("RAINMAPPER_MAPLIBRE_HEATMAP_INTENSITY", 70, 20, 200) / 100,
    }


def number_env(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        configured = float(env(name, str(default)))
    except ValueError:
        configured = default
    return max(minimum, min(maximum, configured))


def int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        configured = int(float(env(name, str(default))))
    except ValueError:
        configured = default
    return max(minimum, min(maximum, configured))


def option_env(name: str, default: str, valid_values: set[str]) -> str:
    value = env(name, default).strip().lower()
    return value if value in valid_values else default


def maplibre_estimated_field_defaults() -> dict:
    return {
        "enabled": bool_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ENABLED", False),
        "opacity": percent_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_OPACITY", 65, 0, 100) / 100,
        "radius": option_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS", "medium", DEVICE_SETTING_ESTIMATED_FIELD_RADII),
        "quality": option_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_QUALITY", "medium", DEVICE_SETTING_ESTIMATED_FIELD_QUALITIES),
        "smoothing": option_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING", "balanced", DEVICE_SETTING_ESTIMATED_FIELD_SMOOTHING),
        "altitudeCorrection": bool_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ALTITUDE_CORRECTION", False),
    }


def maplibre_estimated_field_config() -> dict:
    return {
        "defaults": maplibre_estimated_field_defaults(),
        "radiusKm": {
            "small": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_SMALL_KM", 10, 1, 1000),
            "medium": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_MEDIUM_KM", 25, 1, 1000),
            "large": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_LARGE_KM", 50, 1, 1000),
        },
        "maxRadiusKm": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_MAX_RADIUS_KM", 100, 1, 1000),
        "grid": {
            "low": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_LOW_CELL_KM", 10, 0.1, 100),
            "medium": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_MEDIUM_CELL_KM", 5, 0.1, 100),
            "high": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_HIGH_CELL_KM", 2.5, 0.1, 100),
        },
        "smoothingPower": {
            "smooth": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_SMOOTH_POWER", 1, 0.1, 8),
            "balanced": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_BALANCED_POWER", 2, 0.1, 8),
            "local": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_LOCAL_POWER", 3, 0.1, 8),
        },
        "temperatureLapseRateCPer100m": number_env(
            "RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_TEMPERATURE_LAPSE_RATE_C_PER_100M",
            0.65,
            0,
            2,
        ),
    }


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
    .source-card form {{
      margin-top: 10px;
    }}
    .source-alerts {{
      display: grid;
      gap: 6px;
      margin: 10px 0 8px;
    }}
    .source-alert {{
      border: 1px solid rgba(255, 107, 107, 0.55);
      border-radius: 8px;
      color: var(--danger);
      font-size: 13px;
      font-weight: 800;
      padding: 7px 9px;
    }}
    .control-head {{
      align-items: start;
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 16px;
      justify-content: space-between;
      margin: 0 0 14px;
      padding-bottom: 14px;
    }}
    .control-head p {{
      margin: 0;
    }}
    .control-head-actions {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: flex-end;
    }}
    .control-head-actions form,
    .quick-actions form,
    .source-action-form {{
      margin: 0;
    }}
    .quick-actions {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 0 0 14px;
    }}
    .control-tabs {{
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 18px;
      margin: 0 0 18px;
      overflow-x: auto;
    }}
    .control-tab {{
      background: transparent;
      border: 0;
      border-bottom: 2px solid transparent;
      border-radius: 0;
      color: var(--muted);
      margin: 0;
      min-height: 42px;
      padding: 0 2px;
      white-space: nowrap;
    }}
    .control-tab.active {{
      border-bottom-color: var(--accent);
      color: var(--accent);
    }}
    .control-tab-panel[hidden] {{
      display: none;
    }}
    .control-section {{
      margin: 0 0 18px;
    }}
    .control-section h2 {{
      margin-top: 0;
    }}
    .summary-grid {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      margin: 0 0 14px;
    }}
    .panel-grid {{
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(0, .9fr) minmax(0, .9fr) minmax(0, 1.2fr);
      margin: 12px 0 0;
    }}
    .control-table-wrap {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow-x: auto;
    }}
    .control-table {{
      border-collapse: collapse;
      min-width: 820px;
      width: 100%;
    }}
    .control-table th,
    .control-table td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    .control-table th {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}
    .control-table tr:last-child td {{
      border-bottom: 0;
    }}
    .status-pill {{
      align-items: center;
      display: inline-flex;
      gap: 6px;
      white-space: nowrap;
    }}
    .status-pill::before {{
      background: currentColor;
      border-radius: 50%;
      content: "";
      height: 8px;
      width: 8px;
    }}
    .compact-card-list {{
      display: grid;
      gap: 8px;
    }}
    .compact-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
    }}
    .quick-viewer-list,
    .recent-map-list {{
      display: grid;
      gap: 8px;
    }}
    .quick-viewer-list .button-link,
    .recent-map-link {{
      justify-content: space-between;
      margin: 0;
      width: 100%;
    }}
    .recent-map-link {{
      align-items: center;
      color: var(--fg);
      display: flex;
      gap: 12px;
      min-height: 46px;
      text-decoration: none;
    }}
    .log-preview {{
      max-height: 260px;
    }}
    @media (max-width: 760px) {{
      .source-status-grid {{
        grid-template-columns: 1fr;
      }}
      .control-head {{
        display: block;
      }}
      .control-head-actions {{
        justify-content: flex-start;
        margin-top: 12px;
      }}
      .summary-grid,
      .panel-grid {{
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
      grid-template-columns: auto auto minmax(220px, 1fr) auto auto;
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
    .users-page-head {{
      align-items: start;
      display: flex;
      gap: 18px;
      justify-content: space-between;
      margin: 0 0 14px;
    }}
    .users-page-head h1 {{
      margin-bottom: 4px;
    }}
    .users-page-head p {{
      color: var(--muted);
      margin: 0;
    }}
    .users-list {{
      display: grid;
      gap: 8px;
    }}
    .user-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
    }}
    .user-card.filtered-out {{
      display: none;
    }}
    .user-summary {{
      align-items: center;
      appearance: none;
      background: transparent;
      border: 0;
      color: var(--fg);
      cursor: pointer;
      display: grid;
      gap: 14px;
      grid-template-columns: minmax(220px, 1.6fr) minmax(72px, .5fr) minmax(88px, .6fr) minmax(72px, .5fr) minmax(180px, 1fr) minmax(120px, .7fr) 24px;
      min-height: 62px;
      padding: 10px 14px;
      text-align: left;
      width: 100%;
    }}
    .user-summary:hover {{
      background: color-mix(in srgb, var(--fg) 4%, transparent);
    }}
    .user-summary-main {{
      align-items: center;
      display: flex;
      gap: 12px;
      min-width: 0;
    }}
    .user-avatar {{
      align-items: center;
      background: linear-gradient(135deg, #0ea5e9, #22c55e);
      border-radius: 50%;
      color: #eaf7ff;
      display: inline-flex;
      flex: 0 0 auto;
      font-size: 14px;
      font-weight: 800;
      height: 38px;
      justify-content: center;
      width: 38px;
    }}
    .user-title {{
      min-width: 0;
    }}
    .user-title strong,
    .truncate {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .user-title strong {{
      display: block;
    }}
    .summary-label {{
      color: var(--muted);
      display: block;
      font-size: 12px;
      line-height: 1.2;
    }}
    .badge,
    .permission-chip {{
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      display: inline-flex;
      font-size: 12px;
      font-weight: 700;
      gap: 6px;
      line-height: 1;
      padding: 5px 8px;
      white-space: nowrap;
    }}
    .role-admin {{
      border-color: #0284c7;
      color: #7dd3fc;
    }}
    .role-pro {{
      border-color: #7c3aed;
      color: #c4b5fd;
    }}
    .role-basic,
    .role-free {{
      color: var(--muted);
    }}
    .status-dot {{
      background: #94a3b8;
      border-radius: 50%;
      display: inline-block;
      height: 8px;
      width: 8px;
    }}
    .status-enabled .status-dot {{
      background: #22c55e;
    }}
    .permission-chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .permission-heatmap {{
      border-color: #16a34a;
      color: #86efac;
    }}
    .permission-metrics {{
      border-color: #0284c7;
      color: #7dd3fc;
    }}
    .permission-estimated {{
      border-color: #7c3aed;
      color: #c4b5fd;
    }}
    .user-chevron {{
      color: var(--muted);
      font-size: 18px;
      justify-self: end;
      transform: rotate(0deg);
      transition: transform .15s ease;
    }}
    .user-summary[aria-expanded="true"] .user-chevron {{
      transform: rotate(180deg);
    }}
    .user-panel {{
      border-top: 1px solid var(--line);
      display: grid;
      gap: 10px;
      padding: 14px;
    }}
    .user-panel-card {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
    }}
    .user-panel-card h3 {{
      font-size: 15px;
      margin: 0 0 12px;
    }}
    .user-details-card {{
      padding-bottom: 10px;
    }}
    .user-details-row {{
      align-items: center;
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(160px, 1.2fr) minmax(180px, 1.2fr) minmax(130px, .8fr) minmax(130px, .8fr) minmax(100px, .55fr) auto;
    }}
    .user-details-row .primary {{
      align-self: end;
      margin: 0;
      min-height: 38px;
      white-space: nowrap;
    }}
    .permissions-card-head {{
      align-items: start;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      margin-bottom: 12px;
    }}
    .permissions-card-head h3 {{
      margin-bottom: 3px;
    }}
    .permissions-grid {{
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
    }}
    .permission-card {{
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 9px;
      cursor: pointer;
      display: grid;
      gap: 10px;
      grid-template-columns: auto minmax(0, 1fr) auto;
      min-height: 72px;
      padding: 10px;
    }}
    .permission-card:hover {{
      background: color-mix(in srgb, var(--fg) 4%, transparent);
    }}
    .permission-icon {{
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--fg);
      display: inline-flex;
      font-size: 12px;
      font-weight: 800;
      height: 36px;
      justify-content: center;
      width: 36px;
    }}
    .permission-card-heatmap .permission-icon {{
      background: rgba(22, 163, 74, .18);
      border-color: rgba(134, 239, 172, .28);
      color: #86efac;
    }}
    .permission-card-metrics .permission-icon {{
      background: rgba(2, 132, 199, .18);
      border-color: rgba(125, 211, 252, .28);
      color: #7dd3fc;
    }}
    .permission-card-estimated .permission-icon {{
      background: rgba(124, 58, 237, .18);
      border-color: rgba(196, 181, 253, .28);
      color: #c4b5fd;
    }}
    .permission-copy {{
      min-width: 0;
    }}
    .permission-copy strong {{
      display: block;
      font-size: 13px;
      margin-bottom: 3px;
    }}
    .permission-copy .meta {{
      line-height: 1.25;
    }}
    .switch-control {{
      display: inline-flex;
      position: relative;
    }}
    .switch-control input {{
      height: 1px;
      opacity: 0;
      position: absolute;
      width: 1px;
    }}
    .switch-track {{
      background: #64748b;
      border: 1px solid rgba(255, 255, 255, .18);
      border-radius: 999px;
      display: inline-block;
      height: 22px;
      position: relative;
      transition: background .15s ease;
      width: 40px;
    }}
    .switch-track::after {{
      background: #e2e8f0;
      border-radius: 50%;
      content: "";
      height: 16px;
      left: 2px;
      position: absolute;
      top: 2px;
      transition: transform .15s ease;
      width: 16px;
    }}
    .switch-control input:checked + .switch-track {{
      background: #0ea5e9;
    }}
    .switch-control input:checked + .switch-track::after {{
      transform: translateX(18px);
    }}
    .switch-control input:focus-visible + .switch-track {{
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }}
    .audit-strip {{
      align-items: center;
      display: grid;
      gap: 12px;
      grid-template-columns: auto repeat(3, minmax(160px, 1fr));
      padding: 10px 12px;
    }}
    .audit-strip h3 {{
      margin: 0;
    }}
    .security-actions {{
      align-items: end;
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(260px, 1.5fr) auto auto auto;
    }}
    .security-actions form,
    .devices-head form,
    .device-row form,
    .modal-panel form {{
      margin: 0;
    }}
    .user-update-form {{
      display: grid;
      gap: 10px;
      margin: 0;
      min-width: 0;
    }}
    .security-password-form {{
      align-items: end;
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(180px, 1fr) auto auto;
    }}
    .security-password-form input[type="password"],
    .security-password-form input[type="text"] {{
      min-width: 0;
    }}
    .security-actions button {{
      margin: 0;
      min-height: 38px;
      white-space: nowrap;
    }}
    .danger-zone {{
      border-left: 1px solid var(--line);
      margin-left: 2px;
      padding-left: 12px;
    }}
    .button-danger {{
      border-color: #ef4444;
      color: #fecaca;
    }}
    .button-danger:hover {{
      background: rgba(239, 68, 68, .12);
    }}
    .devices-card {{
      grid-column: 1 / -1;
    }}
    .devices-head {{
      align-items: center;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      margin-bottom: 10px;
    }}
    .devices-list {{
      display: grid;
      gap: 8px;
    }}
    .device-row {{
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(120px, .8fr) minmax(220px, 1.6fr) minmax(120px, .8fr) auto;
      padding: 9px 10px;
    }}
    .modal-backdrop {{
      align-items: center;
      background: rgba(2, 6, 23, .72);
      bottom: 0;
      display: flex;
      justify-content: center;
      left: 0;
      padding: 20px;
      position: fixed;
      right: 0;
      top: 0;
      z-index: 100;
    }}
    .modal-backdrop[hidden] {{
      display: none;
    }}
    .modal-panel {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: 0 24px 80px rgba(0, 0, 0, .45);
      max-height: min(760px, calc(100vh - 40px));
      max-width: 820px;
      overflow: auto;
      padding: 18px;
      width: min(820px, 100%);
    }}
    .modal-head {{
      align-items: center;
      display: flex;
      justify-content: space-between;
      margin-bottom: 12px;
    }}
    .modal-head h2 {{
      margin: 0;
    }}
    @media (max-width: 1320px) {{
      .permissions-grid {{
        grid-template-columns: repeat(3, minmax(180px, 1fr));
      }}
    }}
    @media (max-width: 1080px) {{
      .user-details-row {{
        grid-template-columns: repeat(2, minmax(160px, 1fr));
      }}
      .permissions-grid {{
        grid-template-columns: repeat(2, minmax(180px, 1fr));
      }}
      .security-actions {{
        grid-template-columns: 1fr 1fr;
      }}
      .security-password-form {{
        grid-column: 1 / -1;
      }}
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
      .users-page-head {{
        display: block;
      }}
      .user-summary {{
        grid-template-columns: 1fr auto;
      }}
      .user-summary > :not(.user-summary-main):not(.user-chevron) {{
        display: none;
      }}
      .user-panel-grid {{
        grid-template-columns: 1fr;
      }}
      .user-details-row,
      .permissions-grid,
      .audit-strip,
      .security-actions,
      .security-password-form {{
        grid-template-columns: 1fr;
      }}
      .danger-zone {{
        border-left: 0;
        border-top: 1px solid var(--line);
        margin-left: 0;
        padding-left: 0;
        padding-top: 10px;
      }}
      .device-row {{
        grid-template-columns: 1fr;
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
    .section-header {{
      align-items: center;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      margin: 28px 0 12px;
    }}
    .section-header h2 {{
      margin: 0;
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
    function confirmUserAdminAction(form) {{
      var message = form.getAttribute("data-confirm");
      if (!message) {{
        return true;
      }}
      return window.confirm(message);
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
    function setExpandedUser(username) {{
      var cards = Array.prototype.slice.call(document.querySelectorAll(".user-card"));
      cards.forEach(function(card) {{
        var isOpen = username && card.getAttribute("data-username") === username;
        var button = card.querySelector(".user-summary");
        var panel = card.querySelector(".user-panel");
        if (button) {{
          button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        }}
        if (panel) {{
          panel.hidden = !isOpen;
        }}
      }});
      if (username) {{
        try {{
          window.sessionStorage.setItem("rainmapperUsersExpanded", username);
        }} catch (error) {{}}
      }}
    }}
    function toggleUserCard(button) {{
      var card = button.closest(".user-card");
      if (!card) {{
        return;
      }}
      var username = card.getAttribute("data-username");
      var isOpen = button.getAttribute("aria-expanded") === "true";
      setExpandedUser(isOpen ? "" : username);
    }}
    function restoreExpandedUser() {{
      var username = "";
      try {{
        username = window.sessionStorage.getItem("rainmapperUsersExpanded") || "";
      }} catch (error) {{}}
      if (username) {{
        var cards = Array.prototype.slice.call(document.querySelectorAll(".user-card"));
        var exists = cards.some(function(card) {{
          return card.getAttribute("data-username") === username;
        }});
        if (exists) {{
          setExpandedUser(username);
          return;
        }}
      }}
      var first = document.querySelector(".user-card");
      if (first) {{
        setExpandedUser(first.getAttribute("data-username"));
      }}
    }}
    function openCreateUserModal() {{
      var modal = document.getElementById("create-user-modal");
      if (!modal) {{
        return;
      }}
      modal.hidden = false;
      var firstInput = modal.querySelector("input[name='username']");
      if (firstInput) {{
        firstInput.focus();
      }}
    }}
    function closeCreateUserModal() {{
      var modal = document.getElementById("create-user-modal");
      if (modal) {{
        modal.hidden = true;
      }}
    }}
    function setControlTab(tabName) {{
      var panels = Array.prototype.slice.call(document.querySelectorAll("[data-control-panel]"));
      if (!panels.length) {{
        return;
      }}
      var targetExists = panels.some(function(panel) {{
        return panel.getAttribute("data-control-panel") === tabName;
      }});
      var activeTab = targetExists ? tabName : "summary";
      panels.forEach(function(panel) {{
        panel.hidden = panel.getAttribute("data-control-panel") !== activeTab;
      }});
      Array.prototype.slice.call(document.querySelectorAll(".control-tabs [data-control-tab]")).forEach(function(button) {{
        var isActive = button.getAttribute("data-control-tab") === activeTab;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-selected", isActive ? "true" : "false");
      }});
      try {{
        window.sessionStorage.setItem("rainmapperControlTab", activeTab);
      }} catch (error) {{}}
    }}
    function restoreControlTab() {{
      var tabName = "";
      if (window.location.hash && window.location.hash.indexOf("#tab-") === 0) {{
        tabName = window.location.hash.slice(5);
      }}
      if (!tabName) {{
        try {{
          tabName = window.sessionStorage.getItem("rainmapperControlTab") || "";
        }} catch (error) {{}}
      }}
      setControlTab(tabName || "summary");
    }}
    function applyUsersFilter() {{
      var input = document.getElementById("users-filter");
      var list = document.getElementById("users-list");
      if (!input || !list) {{
        return;
      }}
      var tokens = usersTokens(input.value);
      var rows = Array.prototype.slice.call(list.querySelectorAll(".user-card"));
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
        restoreExpandedUser();
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
    document.addEventListener("click", function(event) {{
      var toggle = event.target.closest("[data-user-toggle]");
      if (toggle) {{
        toggleUserCard(toggle);
        return;
      }}
      if (event.target.closest("[data-create-user-open]")) {{
        openCreateUserModal();
        return;
      }}
      if (event.target.closest("[data-create-user-close]")) {{
        closeCreateUserModal();
        return;
      }}
      var controlTab = event.target.closest("[data-control-tab]");
      if (controlTab) {{
        var tabName = controlTab.getAttribute("data-control-tab");
        setControlTab(tabName);
        if (history.replaceState) {{
          history.replaceState(null, "", "#tab-" + tabName);
        }}
        return;
      }}
      var modal = document.getElementById("create-user-modal");
      if (modal && event.target === modal) {{
        closeCreateUserModal();
      }}
    }});
    document.addEventListener("keydown", function(event) {{
      if (event.key === "Escape") {{
        closeCreateUserModal();
      }}
    }});
    document.addEventListener("DOMContentLoaded", function() {{
      applyUsersFilter();
      restoreExpandedUser();
      restoreControlTab();
    }});
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


def source_flag_value(flag_name: str, only_source: str | None) -> str:
    """Return temporary source enablement for one run without changing HA settings."""
    if only_source:
        return "true" if UPDATE_SOURCE_FLAGS.get(only_source) == flag_name else "false"
    env_names = {
        "create_meteoclimatic": ("RAINMAPPER_CREATE_METEOCLIMATIC", "true"),
        "create_meteocat": ("RAINMAPPER_CREATE_METEOCAT", "true"),
        "create_wunderground": ("RAINMAPPER_CREATE_WUNDERGROUND", "true"),
        "create_aemet": ("RAINMAPPER_CREATE_AEMET", "false"),
    }
    env_name, default = env_names[flag_name]
    return env(env_name, default)


def command_for(action: str, only_source: str | None = None) -> list[str]:
    if only_source and only_source not in UPDATE_SOURCE_FLAGS:
        raise ValueError(f"Invalid source: {only_source}")
    update_command = [
        "python",
        "-m",
        "rainmapper_core.rainmapper",
        "--create_meteoclimatic",
        source_flag_value("create_meteoclimatic", only_source),
        "--create_meteocat",
        source_flag_value("create_meteocat", only_source),
        "--create_wunderground",
        source_flag_value("create_wunderground", only_source),
        "--create_aemet",
        source_flag_value("create_aemet", only_source),
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
            "--include-aemet true "
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


def source_status_card(source: str, payload: dict, disabled: str = "") -> str:
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
    alerts_text = ""
    if source == "AEMET":
        try:
            rate_limit_24h = int(payload.get("rate_limit_24h") or 0)
        except (TypeError, ValueError):
            rate_limit_24h = 0
        try:
            consecutive_429 = int(payload.get("consecutive_429_runs") or 0)
        except (TypeError, ValueError):
            consecutive_429 = 0
        alert_parts = []
        if rate_limit_24h > 0:
            alert_parts.append(f"AEMET 429 in last 24h: {rate_limit_24h}")
        if consecutive_429 > 0:
            alert_parts.append(f"Consecutive AEMET 429 runs: {consecutive_429}")
        if alert_parts:
            alerts_text = (
                '<div class="source-alerts">'
                + "".join(f'<div class="source-alert">{html.escape(part)}</div>' for part in alert_parts)
                + "</div>"
            )
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
        {alerts_text}
        {timing_text}
        <div class="source-message">{html.escape(message)}</div>
        <form method="post" action="">
          <input type="hidden" name="source_update" value="{html.escape(source)}">
          <button {disabled}>Update only</button>
        </form>
      </div>
    """


def source_status_cards(disabled: str = "") -> str:
    payload = read_source_status()
    sources = payload.get("sources", {}) if isinstance(payload, dict) else {}
    cards = []
    for source in ("Meteoclimatic", "Meteocat", "Wunderground", "AEMET"):
        source_payload = sources.get(source, {}) if isinstance(sources, dict) else {}
        cards.append(source_status_card(source, source_payload, disabled=disabled))
    return '<div class="source-status-grid">' + "".join(cards) + "</div>"


# Render the HA Control Panel as server-side fragments so the tabbed dashboard
# stays dependency-free inside Home Assistant ingress.
def source_status_payloads() -> list[tuple[str, dict]]:
    payload = read_source_status()
    sources = payload.get("sources", {}) if isinstance(payload, dict) else {}
    if not isinstance(sources, dict):
        sources = {}
    return [
        (source, sources.get(source, {}) if isinstance(sources.get(source, {}), dict) else {})
        for source in ("Meteoclimatic", "Meteocat", "Wunderground", "AEMET")
    ]


def source_status_counts(payloads: list[tuple[str, dict]]) -> tuple[int, int]:
    total = len(payloads)
    ok_count = sum(1 for _source, payload in payloads if str(payload.get("status") or "").upper() == "OK")
    return ok_count, total


def source_status_table(payloads: list[tuple[str, dict]], disabled: str = "") -> str:
    rows = []
    for source, payload in payloads:
        status = str(payload.get("status") or "Unknown")
        status_class = source_status_class(status)
        exit_code = payload.get("exit_code")
        exit_text = "-" if exit_code is None else str(exit_code)
        rows_text = "-" if payload.get("rows") is None else str(payload.get("rows"))
        stations_text = "-" if payload.get("stations") is None else str(payload.get("stations"))
        duration_text = format_seconds_duration(payload.get("duration_seconds"))
        updated_at = str(payload.get("updated_at") or "-")
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(source)}</strong></td>"
            f'<td><span class="status-pill {status_class}">{html.escape(status)}</span><span class="meta">exit {html.escape(exit_text)}</span></td>'
            f"<td>{html.escape(rows_text)}</td>"
            f"<td>{html.escape(stations_text)}</td>"
            f"<td>{html.escape(duration_text)}</td>"
            f"<td>{html.escape(updated_at)}</td>"
            '<td>'
            f'<form class="source-action-form" method="post" action=""><input type="hidden" name="source_update" value="{html.escape(source)}"><button {disabled}>Update only</button></form>'
            "</td>"
            "</tr>"
        )
    return (
        '<div class="control-table-wrap">'
        '<table class="control-table">'
        "<thead><tr><th>Source</th><th>Status</th><th>Rows</th><th>Stations</th><th>Duration</th><th>Updated</th><th>Action</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


def station_group_summary_card(title: str, group_name: str, station_ids: list[str], disabled_ids: list[str]) -> str:
    return (
        '<div class="compact-card">'
        f"<strong>{html.escape(title)}</strong>"
        f'<span class="meta">{len(station_ids)} current / {len(disabled_ids)} disabled</span>'
        '<button type="button" class="button-link" data-control-tab="errors">View details</button>'
        "</div>"
    )


def quick_viewer_links(links: list[tuple[str, str, bool]]) -> str:
    items = [
        f'<a class="button-link{" primary" if primary else ""}" href="{html.escape(url, quote=True)}" target="_top">{html.escape(label)}</a>'
        for label, url, primary in links
        if url
    ]
    return '<div class="quick-viewer-list">' + "".join(items) + "</div>"


def map_file_records(limit: int | None = None) -> list[dict[str, str]]:
    files = sorted(PLOTS_PATH.glob("*.html"))
    if limit is not None:
        files = files[:limit]
    records = []
    for file_path in files:
        stat = file_path.stat()
        name = file_path.name
        records.append(
            {
                "name": name,
                "title": name.removesuffix(".html").replace("_", " "),
                "generated_at": format_datetime_from_timestamp(stat.st_mtime),
                "size": format_size(stat.st_size),
            }
        )
    return records


def render_recent_map_links(limit: int = 3) -> str:
    records = map_file_records(limit=limit)
    if not records:
        return '<div class="empty">No HTML maps found in <code>/share/rainmapper/Plots</code>.</div>'
    links = []
    for record in records:
        links.append(
            f'<a class="recent-map-link" href="file/{html.escape(record["name"])}">'
            f'<span><strong>{html.escape(record["title"])}</strong>'
            f'<span class="meta">{html.escape(record["name"])} - {html.escape(record["size"])} - {html.escape(record["generated_at"])}</span></span>'
            "<span aria-hidden=\"true\">↗</span>"
            "</a>"
        )
    return '<div class="recent-map-list">' + "".join(links) + "</div>"


def render_log_preview(max_lines: int = 12) -> str:
    lines = read_log().splitlines()
    preview_lines = lines[-max_lines:] if len(lines) > max_lines else lines
    return "<pre class=\"log-preview\">" + html.escape("\n".join(preview_lines)) + "</pre>"


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

    heatmap_message = publish_heatmap_experimental_maplibre()

    aemet_message = ""
    if PUBLISH_AEMET_EXPERIMENTAL_MAPLIBRE:
        aemet_message = publish_aemet_experimental_maplibre(log_file, config_js)
    else:
        shutil.rmtree(PUBLIC_MAPLIBRE_AEMET_PATH, ignore_errors=True)

    published_at = datetime.now(get_timezone()).isoformat(timespec="seconds")
    message = (
        f"Published mobile viewers with {copied} GeoJSON file(s) to "
        f"/local/rainmapper-leaflet/index.html and protected /protected/maplibre/index.html at {published_at}."
    )
    if heatmap_message:
        message = f"{message} {heatmap_message}"
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


def experimental_heatmap_config_js() -> str:
    """Enable the public MapLibre heatmap experiment without changing defaults."""
    return "window.RAINMAPPER_CONFIG = " + json.dumps({
        "experimentalHeatmap": True,
        "hoverPopupMinZoom": maplibre_hover_zoom(),
        "heatmapDefaults": maplibre_heatmap_defaults(),
        "estimatedField": maplibre_estimated_field_config(),
    }) + ";\n"


def publish_heatmap_experimental_maplibre() -> str:
    """Publish a public MapLibre variant with the experimental rain heatmap on.

    The protected viewer remains the canonical production route. This separate
    /local/rainmapper-maplibre-heatmap route lets us validate heatmap rendering
    with the same GeoJSON data without changing the experience for current
    protected users.
    """
    PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH, ignore_errors=True)
    PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH.mkdir(parents=True, exist_ok=True)

    for asset_name in ("index.html", "app.js", "style.css", "translations.json"):
        shutil.copy2(MAPLIBRE_VIEWER_ASSETS_PATH / asset_name, PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH / asset_name)
    (PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH / "config.js").write_text(experimental_heatmap_config_js())

    data_path = PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH / "data"
    data_path.mkdir()
    copied = 0
    for source_path in sorted(PUBLIC_DATA_PATH.glob("*.geojson")):
        shutil.copy2(source_path, data_path / source_path.name)
        copied += 1
    if SOURCE_STATUS_PATH.exists():
        shutil.copy2(SOURCE_STATUS_PATH, data_path / SOURCE_STATUS_PATH.name)

    shutil.rmtree(PUBLIC_MAPLIBRE_HEATMAP_PATH, ignore_errors=True)
    PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH.rename(PUBLIC_MAPLIBRE_HEATMAP_PATH)
    return f"Published experimental rain heatmap MapLibre viewer with {copied} GeoJSON file(s) to /local/rainmapper-maplibre-heatmap/index.html."


def publish_aemet_experimental_maplibre(log_file, config_js: str) -> str:
    """Publish the disabled-by-default public MapLibre AEMET test variant.

    AEMET is now included in the standard protected viewer. This function is
    kept temporarily as a rollback hook for the previous
    /local/rainmapper-maplibre-aemet test route and should be removed once the
    production AEMET path has been validated for long enough.
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


def run_action(action: str, source: str, only_source: str | None = None) -> bool:
    if action not in {"update", "maps", "all"}:
        return False
    if only_source and (action != "update" or only_source not in UPDATE_SOURCE_FLAGS):
        return False

    with RUN_LOCK:
        if RUN_STATE["running"]:
            return False
        action_label = f"{action} ({only_source} only)" if only_source else action
        RUN_STATE.update(
            {
                "running": True,
                "action": action_label,
                "started_at": datetime.now(get_timezone()).isoformat(timespec="seconds"),
                "finished_at": "",
                "duration": "",
                "exit_code": "",
                "last_message": f"Running {action_label} from {source}.",
                "current_step": f"Queued {action_label}",
                "progress_current": "",
                "progress_total": "",
                "progress_percent": "",
            }
        )

    thread = threading.Thread(target=_run_action_thread, args=(action, source, only_source), daemon=True)
    thread.start()
    return True


def _run_action_thread(action: str, source: str, only_source: str | None = None) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    final_exit_code = 0
    started = datetime.now(get_timezone())
    action_label = f"{action} ({only_source} only)" if only_source else action
    print(f"Starting Rainmapper action '{action_label}' from {source}.", flush=True)

    with LOG_PATH.open("w", encoding="utf-8") as log_file:
        log_file.write(f"=== {started.isoformat(timespec='seconds')} - {action_label} ({source}) ===\n")
        log_file.flush()

        actions = ["update", "maps"] if action == "all" else [action]
        for current_action in actions:
            print(f"Running Rainmapper step '{current_action}'.", flush=True)
            with RUN_LOCK:
                RUN_STATE.update({"current_step": f"Running {current_action}", **clear_progress()})
            log_file.write(f"=== running step {current_action} ===\n")
            log_file.flush()
            command = command_for(current_action, only_source=only_source if current_action == "update" else None)
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
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
USER_PERMISSION_FIELDS = ("can_use_heatmap", "can_use_layer_metrics", "can_use_estimated_field")
USER_PERMISSION_UI = (
    {
        "field": "can_use_heatmap",
        "label": "Heatmap access",
        "description": "Allow the Heatmap button and Heatmap settings.",
        "chip": "Heatmap",
        "chip_class": "permission-heatmap",
        "card_class": "permission-card-heatmap",
        "icon": "HM",
    },
    {
        "field": "can_use_layer_metrics",
        "label": "Metric selector access",
        "description": "Allow the metric selector button and layer metric settings.",
        "chip": "Metrics",
        "chip_class": "permission-metrics",
        "card_class": "permission-card-metrics",
        "icon": "MX",
    },
    {
        "field": "can_use_estimated_field",
        "label": "Estimated field access",
        "description": "Allow the IDW button and estimated field settings.",
        "chip": "IDW",
        "chip_class": "permission-estimated",
        "card_class": "permission-card-estimated",
        "icon": "IDW",
    },
)


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


def default_user_permission(role: str, field: str) -> str:
    if field not in USER_PERMISSION_FIELDS:
        return "false"
    return "true" if normalize_role(role) == "admin" else "false"


def normalize_user_permission(raw_user: dict[str, object], role: str, field: str) -> str:
    if field not in raw_user:
        return default_user_permission(role, field)
    return normalize_bool_flag(raw_user.get(field))


def user_permission_enabled(user: dict[str, str], field: str) -> bool:
    return normalize_user_permission(user, normalize_role(user.get("role", "free")), field) == "true"


def user_auth_payload(user: dict[str, str]) -> dict[str, object]:
    role = normalize_role(user.get("role", "free"))
    return {
        "username": user["username"],
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": role,
        "can_use_heatmap": user_permission_enabled(user, "can_use_heatmap"),
        "can_use_layer_metrics": user_permission_enabled(user, "can_use_layer_metrics"),
        "can_use_estimated_field": user_permission_enabled(user, "can_use_estimated_field"),
    }


def normalize_user_record(raw_user: dict[str, object], fallback_username: str = "") -> dict[str, str] | None:
    username = normalize_user_id(str(raw_user.get("username") or fallback_username))
    if not username:
        return None
    role = normalize_role(str(raw_user.get("role", "free")))
    user = {
        "username": username,
        "name": str(raw_user.get("name", "")).strip(),
        "email": normalize_user_id(str(raw_user.get("email", username))),
        "password": str(raw_user.get("password", "")),
        "role": role,
        "enabled": normalize_enabled(raw_user.get("enabled", True)),
        "max_devices": str(parse_max_devices(str(raw_user.get("max_devices", "")), role)),
        "must_change_password": normalize_bool_flag(raw_user.get("must_change_password", False)),
        "created_at": str(raw_user.get("created_at", "")).strip(),
        "updated_at": str(raw_user.get("updated_at", "")).strip(),
        "last_change": str(raw_user.get("last_change", "")).strip(),
    }
    for field in USER_PERMISSION_FIELDS:
        user[field] = normalize_user_permission(raw_user, role, field)
    return user


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
                "created_at": user.get("created_at", ""),
                "updated_at": user.get("updated_at", ""),
                "last_change": user.get("last_change", ""),
                "can_use_heatmap": user_permission_enabled(user, "can_use_heatmap"),
                "can_use_layer_metrics": user_permission_enabled(user, "can_use_layer_metrics"),
                "can_use_estimated_field": user_permission_enabled(user, "can_use_estimated_field"),
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

    layer_metric = str(raw_settings.get("layer_metric", "")).strip()
    if layer_metric in DEVICE_SETTING_LAYER_METRICS:
        settings["layer_metric"] = layer_metric

    if "heatmap_enabled" in raw_settings:
        settings["heatmap_enabled"] = normalize_bool_flag(raw_settings.get("heatmap_enabled")) == "true"

    if "heatmap_opacity" in raw_settings:
        heatmap_opacity = finite_number(raw_settings.get("heatmap_opacity"), 0.65)
        settings["heatmap_opacity"] = max(0.0, min(1.0, heatmap_opacity))

    if "heatmap_radius_scale" in raw_settings:
        heatmap_radius_scale = finite_number(raw_settings.get("heatmap_radius_scale"), 1.0)
        settings["heatmap_radius_scale"] = max(0.5, min(3.0, heatmap_radius_scale))

    if "heatmap_intensity_scale" in raw_settings:
        heatmap_intensity_scale = finite_number(raw_settings.get("heatmap_intensity_scale"), 1.0)
        settings["heatmap_intensity_scale"] = max(0.2, min(2.0, heatmap_intensity_scale))

    heatmap_weight_curve = str(raw_settings.get("heatmap_weight_curve", "")).strip()
    if heatmap_weight_curve in DEVICE_SETTING_HEATMAP_WEIGHT_CURVES:
        settings["heatmap_weight_curve"] = heatmap_weight_curve

    if "estimated_field_enabled" in raw_settings:
        settings["estimated_field_enabled"] = normalize_bool_flag(raw_settings.get("estimated_field_enabled")) == "true"

    if "estimated_field_opacity" in raw_settings:
        estimated_field_opacity = finite_number(raw_settings.get("estimated_field_opacity"), 0.65)
        settings["estimated_field_opacity"] = max(0.0, min(1.0, estimated_field_opacity))

    estimated_field_radius = str(raw_settings.get("estimated_field_radius", "")).strip()
    if estimated_field_radius in DEVICE_SETTING_ESTIMATED_FIELD_RADII:
        settings["estimated_field_radius"] = estimated_field_radius

    estimated_field_quality = str(raw_settings.get("estimated_field_quality", "")).strip()
    if estimated_field_quality in DEVICE_SETTING_ESTIMATED_FIELD_QUALITIES:
        settings["estimated_field_quality"] = estimated_field_quality

    estimated_field_smoothing = str(raw_settings.get("estimated_field_smoothing", "")).strip()
    if estimated_field_smoothing in DEVICE_SETTING_ESTIMATED_FIELD_SMOOTHING:
        settings["estimated_field_smoothing"] = estimated_field_smoothing

    if "estimated_field_altitude_correction" in raw_settings:
        settings["estimated_field_altitude_correction"] = (
            normalize_bool_flag(raw_settings.get("estimated_field_altitude_correction")) == "true"
        )

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


def mark_user_change(user: dict[str, str], change: str, now: str | None = None, is_creation: bool = False) -> None:
    timestamp = now or utc_now()
    if is_creation or not user.get("created_at"):
        user["created_at"] = timestamp
    user["updated_at"] = timestamp
    user["last_change"] = change


def mark_existing_user_change(username: str, change: str) -> None:
    user_id = normalize_user_id(username)
    users = read_users()
    user = users.get(user_id)
    if not user:
        return
    mark_user_change(user, change)
    write_users(users)


def create_user(
    username: str,
    name: str,
    email: str,
    password: str,
    role: str,
    enabled: str,
    max_devices: str,
    can_use_heatmap: str = "",
    can_use_layer_metrics: str = "",
    can_use_estimated_field: str = "",
) -> str:
    user_id = normalize_user_id(username)
    if not user_id:
        return "Username is required."
    if not password:
        return "Password is required for new users."

    users = read_users()
    if user_id in users:
        return f"User {user_id} already exists."

    normalized_role = normalize_role(role)
    now = utc_now()
    users[user_id] = {
        "username": user_id,
        "name": name.strip(),
        "email": normalize_user_id(email) if email.strip() else "",
        "password": hash_password(password),
        "role": normalized_role,
        "enabled": normalize_enabled(enabled),
        "max_devices": str(parse_max_devices(max_devices, normalized_role)),
        "must_change_password": "false",
        "can_use_heatmap": (
            normalize_bool_flag(can_use_heatmap)
            if can_use_heatmap
            else default_user_permission(normalized_role, "can_use_heatmap")
        ),
        "can_use_layer_metrics": (
            normalize_bool_flag(can_use_layer_metrics)
            if can_use_layer_metrics
            else default_user_permission(normalized_role, "can_use_layer_metrics")
        ),
        "can_use_estimated_field": (
            normalize_bool_flag(can_use_estimated_field)
            if can_use_estimated_field
            else default_user_permission(normalized_role, "can_use_estimated_field")
        ),
    }
    mark_user_change(users[user_id], "created user", now, is_creation=True)
    write_users(users)
    return f"Created user {user_id}."


def update_user(
    username: str,
    name: str,
    email: str,
    role: str,
    enabled: str,
    max_devices: str,
    can_use_heatmap: str,
    can_use_layer_metrics: str,
    can_use_estimated_field: str,
) -> str:
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
            "can_use_heatmap": normalize_bool_flag(can_use_heatmap),
            "can_use_layer_metrics": normalize_bool_flag(can_use_layer_metrics),
            "can_use_estimated_field": normalize_bool_flag(can_use_estimated_field),
        }
    )
    mark_user_change(user, "updated user settings")
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
    deleted_count = delete_devices_for_user(user_id)
    set_user_password(user, password)
    mark_user_change(user, f"set password; deleted {deleted_count} device(s)")
    write_users(users)
    return f"Set password for {user_id} and deleted {deleted_count} device(s)."


def require_user_password_change(username: str) -> str:
    user_id = normalize_user_id(username)
    users = read_users()
    user = users.get(user_id)
    if not user:
        return f"User {user_id or '-'} was not found."
    user["must_change_password"] = "true"
    deleted_count = delete_devices_for_user(user_id)
    mark_user_change(user, f"reset password; deleted {deleted_count} device(s)")
    write_users(users)
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

    delete_devices_for_user(user_id)
    set_user_password(user, new_password)
    mark_user_change(user, "completed required password change")
    write_users(users)
    return login_user(user_id, new_password, device_id, user_agent)


def delete_device(device_id: str) -> str:
    device_key = device_id.strip()
    devices = read_devices()
    if device_key not in devices:
        return "Device was not found."
    device = devices.pop(device_key)
    write_devices(devices)
    username = device_username(device) or "-"
    if username != "-":
        mark_existing_user_change(username, f"deleted device {device_key}")
    return f"Deleted device for {username}."


def delete_user_devices(username: str) -> str:
    user_id = normalize_user_id(username)
    deleted_count = delete_devices_for_user(user_id)
    if user_id:
        mark_existing_user_change(user_id, f"deleted all devices ({deleted_count})")
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


def checked_attr(enabled: bool) -> str:
    return " checked" if enabled else ""


# Keep the HA Users page as small server-side HTML fragments. This avoids a
# frontend build step while keeping the accordion layout maintainable.
def user_initials(user: dict[str, str]) -> str:
    label = user_display_name(user) or user.get("username", "")
    parts = [part for part in label.replace("-", " ").replace("_", " ").split() if part]
    if not parts:
        return "U"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[1][:1]).upper()


def short_text(value: str, limit: int = 24) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: max(0, limit - 3)] + "..."


def permission_chips(can_use_heatmap: bool, can_use_layer_metrics: bool, can_use_estimated_field: bool) -> str:
    states = {
        "can_use_heatmap": can_use_heatmap,
        "can_use_layer_metrics": can_use_layer_metrics,
        "can_use_estimated_field": can_use_estimated_field,
    }
    chips = []
    for permission in USER_PERMISSION_UI:
        if states.get(permission["field"], False):
            chip_class = html.escape(permission["chip_class"], quote=True)
            chip_label = html.escape(permission["chip"])
            chips.append(f'<span class="permission-chip {chip_class}">{chip_label}</span>')
    return "".join(chips) or '<span class="meta">No feature access</span>'


def latest_seen_for_devices(user_devices: list[tuple[str, dict[str, str]]]) -> str:
    for _device_id, device in user_devices:
        last_seen = str(device.get("last_seen_at", "")).strip()
        if last_seen:
            return last_seen
    return "-"


def user_search_text(
    username: str,
    user: dict[str, str],
    role: str,
    enabled: str,
    max_devices: str,
    user_devices: list[tuple[str, dict[str, str]]],
    can_use_heatmap: bool,
    can_use_layer_metrics: bool,
    can_use_estimated_field: bool,
) -> str:
    return " ".join(
        [
            username,
            user_display_name(user),
            user.get("email", ""),
            role,
            "enabled" if enabled == "true" else "disabled",
            "heatmap" if can_use_heatmap else "no heatmap",
            "metrics" if can_use_layer_metrics else "no metrics",
            "estimated field" if can_use_estimated_field else "no estimated field",
            "change required" if user.get("must_change_password", "false").lower() == "true" else "current",
            max_devices,
            str(len(user_devices)),
            user.get("created_at", ""),
            user.get("updated_at", ""),
            user.get("last_change", ""),
        ]
    )


def render_user_details_card(username: str, user: dict[str, str], role: str, enabled: str, max_devices: str) -> str:
    return (
        '<section class="user-panel-card user-details-card">'
        "<h3>User details</h3>"
        f'<input type="hidden" name="admin_action" value="update_user">'
        f'<input type="hidden" name="username" value="{html.escape(username, quote=True)}">'
        '<div class="user-details-row">'
        f'<div class="admin-field"><label>Name</label><input name="name" value="{html.escape(user.get("name", ""), quote=True)}"></div>'
        f'<div class="admin-field"><label>Email</label><input name="email" value="{html.escape(user.get("email", ""), quote=True)}"></div>'
        f'<div class="admin-field"><label>Role</label><select name="role">{role_options(role)}</select></div>'
        f'<div class="admin-field"><label>Status</label><select name="enabled">{enabled_options(enabled)}</select></div>'
        f'<div class="admin-field"><label>Max devices</label><input name="max_devices" type="number" min="0" value="{html.escape(max_devices, quote=True)}"></div>'
        '<button class="primary">Save user</button>'
        "</div>"
        "</section>"
    )


def render_permissions_card(
    can_use_heatmap: bool,
    can_use_layer_metrics: bool,
    can_use_estimated_field: bool,
) -> str:
    states = {
        "can_use_heatmap": can_use_heatmap,
        "can_use_layer_metrics": can_use_layer_metrics,
        "can_use_estimated_field": can_use_estimated_field,
    }
    cards = []
    for permission in USER_PERMISSION_UI:
        field = permission["field"]
        label = html.escape(permission["label"])
        description = html.escape(permission["description"])
        icon = html.escape(permission["icon"])
        card_class = html.escape(permission["card_class"], quote=True)
        cards.append(
            f'<label class="permission-card {card_class}">'
            f'<span class="permission-icon">{icon}</span>'
            f'<span class="permission-copy"><strong>{label}</strong><span class="meta">{description}</span></span>'
            '<span class="switch-control">'
            f'<input name="{html.escape(field, quote=True)}" type="checkbox" value="true"{checked_attr(states.get(field, False))}>'
            '<span class="switch-track" aria-hidden="true"></span>'
            "</span>"
            "</label>"
        )
    return (
        '<section class="user-panel-card permissions-card">'
        '<div class="permissions-card-head">'
        '<div><h3>Permissions</h3><span class="meta">Toggle feature access for this user.</span></div>'
        "</div>"
        f'<div class="permissions-grid">{"".join(cards)}</div>'
        "</section>"
    )


def render_security_card(username: str) -> str:
    escaped_username = html.escape(username, quote=True)
    password_id = "reset-password-" + "".join(char if char.isalnum() else "-" for char in username)
    return (
        '<section class="user-panel-card security-compact-card">'
        "<h3>Security</h3>"
        '<div class="security-actions">'
        f'<form class="security-password-form" method="post" action="" onsubmit="return confirmUserAdminAction(this)" data-confirm="{html.escape(f"Set a new password for user {username} and delete all registered devices?", quote=True)}">'
        '<input type="hidden" name="admin_action" value="set_password">'
        f'<input type="hidden" name="username" value="{escaped_username}">'
        f'<input id="{password_id}" name="password" type="password" placeholder="New password" autocomplete="new-password">'
        '<label class="password-tools">'
        f'<input type="checkbox" data-target="{password_id}" onchange="togglePasswordVisibility(this)">'
        '<span>Show typed password</span>'
        '</label>'
        '<button>Set password</button>'
        "</form>"
        f'<form method="post" action="" onsubmit="return confirmUserAdminAction(this)" data-confirm="{html.escape(f"Reset password for user {username}, force password change and delete all registered devices?", quote=True)}">'
        '<input type="hidden" name="admin_action" value="reset_password">'
        f'<input type="hidden" name="username" value="{escaped_username}">'
        '<button>Reset password</button>'
        "</form>"
        '<div class="danger-zone">'
        f'<form method="post" action="" onsubmit="return confirmUserAdminAction(this)" data-confirm="{html.escape(f"Delete user {username} and all registered devices?", quote=True)}">'
        '<input type="hidden" name="admin_action" value="delete_user">'
        f'<input type="hidden" name="username" value="{escaped_username}">'
        '<button class="button-danger">Delete user</button>'
        "</form>"
        "</div>"
        "</div>"
        "</section>"
    )


def render_audit_card(user: dict[str, str]) -> str:
    audit_rows = []
    for label, field in (("Created", "created_at"), ("Updated", "updated_at"), ("Last change", "last_change")):
        value = str(user.get(field, "")).strip() or "-"
        audit_rows.append(f'<span class="meta"><strong>{label}:</strong> {html.escape(value)}</span>')
    return '<section class="user-panel-card audit-strip"><h3>Audit</h3>' + "".join(audit_rows) + "</section>"


def render_device_row(username: str, device_id: str, device: dict[str, str]) -> str:
    device_label = short_text(device_id, 14)
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
    return (
        f'<div class="device-row" data-device-search="{html.escape(device_search_text, quote=True)}">'
        f'<div><strong title="{html.escape(device_id, quote=True)}">{html.escape(device_label)}</strong></div>'
        f'<div class="truncate" title="{html.escape(user_agent, quote=True)}">{html.escape(short_text(user_agent, 92))}</div>'
        f'<div><span class="meta">Created {html.escape(created_at)}</span><span class="meta">Last seen {html.escape(last_seen_at)}</span></div>'
        f'<form method="post" action="" onsubmit="return confirmUserAdminAction(this)" data-confirm="{html.escape(f"Delete device {device_label} for user {username}?", quote=True)}">'
        '<input type="hidden" name="admin_action" value="delete_device">'
        f'<input type="hidden" name="device_id" value="{html.escape(device_id, quote=True)}">'
        '<button class="button-danger">Delete device</button>'
        "</form>"
        "</div>"
    )


def render_devices_card(username: str, user_devices: list[tuple[str, dict[str, str]]]) -> str:
    devices_html = "".join(render_device_row(username, device_id, device) for device_id, device in user_devices)
    if not devices_html:
        devices_html = '<span class="meta">No registered devices</span>'
    note = '<span class="device-filter-note">Showing matching devices only.</span>' if user_devices else ""
    return (
        '<section class="user-panel-card devices-card">'
        '<div class="devices-head">'
        f"<h3>Devices ({len(user_devices)})</h3>"
        f'<form method="post" action="" onsubmit="return confirmUserAdminAction(this)" data-confirm="{html.escape(f"Delete all registered devices for user {username}?", quote=True)}">'
        '<input type="hidden" name="admin_action" value="delete_user_devices">'
        f'<input type="hidden" name="username" value="{html.escape(username, quote=True)}">'
        '<button class="button-danger">Delete all devices</button>'
        "</form>"
        "</div>"
        f'<div class="devices-list">{devices_html}</div>'
        f"{note}"
        "</section>"
    )


def render_user_card(username: str, user: dict[str, str], user_devices: list[tuple[str, dict[str, str]]]) -> str:
    enabled = normalize_enabled(user.get("enabled", "true"))
    role = normalize_role(user.get("role", "free"))
    max_devices = str(user_max_devices(user))
    can_use_heatmap = user_permission_enabled(user, "can_use_heatmap")
    can_use_layer_metrics = user_permission_enabled(user, "can_use_layer_metrics")
    can_use_estimated_field = user_permission_enabled(user, "can_use_estimated_field")
    status_label = "Enabled" if enabled == "true" else "Disabled"
    status_class = "status-enabled" if enabled == "true" else "status-disabled"
    search_text = user_search_text(
        username,
        user,
        role,
        enabled,
        max_devices,
        user_devices,
        can_use_heatmap,
        can_use_layer_metrics,
        can_use_estimated_field,
    )
    panel_id = "user-panel-" + "".join(char if char.isalnum() else "-" for char in username)
    chips = permission_chips(can_use_heatmap, can_use_layer_metrics, can_use_estimated_field)
    latest_seen = latest_seen_for_devices(user_devices)
    password_state = "Change required" if user.get("must_change_password", "false").lower() == "true" else "Current"
    update_form = (
        f'<form class="user-update-form" method="post" action="" onsubmit="return confirmUserAdminAction(this)" data-confirm="{html.escape(f"Save changes for user {username}?", quote=True)}">'
        + render_user_details_card(username, user, role, enabled, max_devices)
        + render_permissions_card(can_use_heatmap, can_use_layer_metrics, can_use_estimated_field)
        + render_audit_card(user)
        + "</form>"
    )
    expanded_html = (
        '<div class="user-panel" hidden '
        f'id="{html.escape(panel_id, quote=True)}">'
        f"{update_form}"
        f"{render_security_card(username)}"
        f"{render_devices_card(username, user_devices)}"
        "</div>"
    )
    return (
        f'<section class="user-card" data-username="{html.escape(username, quote=True)}" data-user-search="{html.escape(search_text, quote=True)}">'
        f'<button class="user-summary" type="button" data-user-toggle aria-expanded="false" aria-controls="{html.escape(panel_id, quote=True)}">'
        '<span class="user-summary-main">'
        f'<span class="user-avatar">{html.escape(user_initials(user))}</span>'
        '<span class="user-title">'
        f'<strong>{html.escape(user_display_name(user))}</strong>'
        f'<span class="meta">{html.escape(username)}</span>'
        '</span>'
        '</span>'
        f'<span><span class="summary-label">Role</span><span class="badge role-{html.escape(role)}">{html.escape(role)}</span></span>'
        f'<span><span class="summary-label">Status</span><span class="badge {status_class}"><span class="status-dot"></span>{status_label}</span></span>'
        f'<span><span class="summary-label">Devices</span>{len(user_devices)}/{html.escape(max_devices)}</span>'
        f'<span><span class="summary-label">Permissions</span><span class="permission-chips">{chips}</span></span>'
        f'<span><span class="summary-label">Last seen</span><span class="truncate" title="{html.escape(latest_seen, quote=True)}">{html.escape(short_text(latest_seen, 20))}</span><span class="meta">{html.escape(password_state)}</span></span>'
        '<span class="user-chevron" aria-hidden="true">⌄</span>'
        "</button>"
        f"{expanded_html}"
        "</section>"
    )


def render_create_user_modal() -> str:
    return f"""
    <div id="create-user-modal" class="modal-backdrop" hidden>
      <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="create-user-title">
        <div class="modal-head">
          <h2 id="create-user-title">Create user</h2>
          <button type="button" data-create-user-close>Close</button>
        </div>
        <p class="help-text">Create a protected MapLibre user. Admin users receive all experimental feature permissions by default unless changed here.</p>
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
            <div class="admin-field"><label><input name="can_use_heatmap" type="checkbox" value="true"> Heatmap access</label></div>
            <div class="admin-field"><label><input name="can_use_layer_metrics" type="checkbox" value="true"> Metric selector access</label></div>
            <div class="admin-field"><label><input name="can_use_estimated_field" type="checkbox" value="true"> Estimated field access</label></div>
          </div>
          <button class="primary">Create user</button>
        </form>
      </div>
    </div>
    """


def new_device_id() -> str:
    return secrets.token_urlsafe(24)


def new_session_token() -> str:
    return secrets.token_urlsafe(AUTH_TOKEN_BYTES)


def authenticate_session(token: str, device_id: str) -> tuple[bool, dict[str, object] | None]:
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
    return True, user_auth_payload(user)


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
    payload = user_auth_payload(user)
    payload.update({
        "ok": True,
        "max_devices": max_devices,
        "device_id": requested_device_id,
        "session_token": session_token,
    })
    return 200, payload


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
                "hoverPopupMinZoom": maplibre_hover_zoom(),
                "heatmapDefaults": maplibre_heatmap_defaults(),
                "estimatedField": maplibre_estimated_field_config(),
            }
        )
        + ";\n"
    )


def public_viewer_config_js() -> str:
    return "window.RAINMAPPER_CONFIG = " + json.dumps({
        "hoverPopupMinZoom": maplibre_hover_zoom(),
        "heatmapDefaults": maplibre_heatmap_defaults(),
        "estimatedField": maplibre_estimated_field_config(),
    }) + ";\n"


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

    def send_bytes(
        self,
        status: int,
        content: bytes,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        for header_name, header_value in (headers or {}).items():
            self.send_header(header_name, header_value)
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

    def authenticated_user(self) -> dict[str, object] | None:
        token, device_id = self.auth_credentials()
        ok, user = authenticate_session(token, device_id)
        return user if ok else None

    def require_authentication(self) -> dict[str, object] | None:
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
        with RUN_LOCK:
            users_flash = str(RUN_STATE.get("users_flash", ""))
            RUN_STATE["users_flash"] = ""

        cards = []
        for username, user in sorted(users.items()):
            user_devices = devices_for_user(devices, username)
            cards.append(render_user_card(username, user, user_devices))

        users_list = "".join(cards) if cards else '<div class="users-empty-filter visible">No users configured.</div>'
        users_flash_script = ""
        if users_flash:
            users_flash_script = f"<script>window.alert({json.dumps(users_flash)});</script>"
        body = f"""
        <div class="users-toolbar">
          <a class="button-link" href="./">Back</a>
          <button id="users-refresh" type="button" onclick="refreshUsersPage()">Refresh</button>
          <input id="users-filter" class="users-filter" type="search" placeholder="Search users or devices">
          <button type="button" class="primary" data-create-user-open>Create user</button>
          <span class="users-toolbar-status"><span id="users-filter-status">{len(users)} users</span> · <span id="users-refresh-status">Manual refresh</span></span>
        </div>
        <div class="users-page-head">
          <div>
            <h1>Users</h1>
            <p>Manage MapLibre protected viewer users, roles, permissions and devices.</p>
          </div>
        </div>
        <div id="users-content">
          <div id="users-empty-filter" class="users-empty-filter">No users or devices match the current search.</div>
          <div id="users-list" class="users-list">
            {users_list}
          </div>
          {render_create_user_modal()}
        </div>
        {users_flash_script}
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

        if path == "/log":
            self.render_log()
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

        source_update = self.form_value(form, "source_update")
        if source_update:
            run_action("update", "web", only_source=source_update)
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
            username = self.form_value(form, "username")
            message = create_user(
                username,
                self.form_value(form, "name"),
                self.form_value(form, "email"),
                self.form_value(form, "password"),
                self.form_value(form, "role"),
                self.form_value(form, "enabled"),
                self.form_value(form, "max_devices"),
                self.form_value(form, "can_use_heatmap"),
                self.form_value(form, "can_use_layer_metrics"),
                self.form_value(form, "can_use_estimated_field"),
            )
            if message.startswith("Created user "):
                created_username = normalize_user_id(username)
                with RUN_LOCK:
                    RUN_STATE["users_flash"] = f"Created user: {created_username}"
        elif admin_action == "update_user":
            message = update_user(
                self.form_value(form, "username"),
                self.form_value(form, "name"),
                self.form_value(form, "email"),
                self.form_value(form, "role"),
                self.form_value(form, "enabled"),
                self.form_value(form, "max_devices"),
                self.form_value(form, "can_use_heatmap"),
                self.form_value(form, "can_use_layer_metrics"),
                self.form_value(form, "can_use_estimated_field"),
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
        <div class="quick-actions">
          <form method="post" action=""><input type="hidden" name="run_action" value="all"><button class="primary" {disabled}>Run all</button></form>
          <form method="post" action=""><input type="hidden" name="run_action" value="update"><button {disabled}>Run update</button></form>
          <form method="post" action=""><input type="hidden" name="run_action" value="maps"><button {disabled}>Generate maps</button></form>
          <a class="button-link" href="./settings">App settings</a>
          <a class="button-link" href="./users">Users</a>
        </div>
        """
        head_controls = f"""
        <div class="control-head-actions">
          <span class="meta">Last update: {html.escape(finished_at)}</span>
        </div>
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

        source_payloads = source_status_payloads()
        ok_sources, total_sources = source_status_counts(source_payloads)
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
        station_summary = (
            station_group_summary_card("Wunderground 404", "404", active_station_groups["404"], disabled_groups["404"])
            + station_group_summary_card("Wunderground parse errors", "parse", active_station_groups["parse"], disabled_groups["parse"])
        )
        source_table = source_status_table(source_payloads, disabled)
        source_cards = source_status_cards(disabled)
        leaflet_url = cache_busted_url("/local/rainmapper-leaflet/index.html")
        maplibre_url = cache_busted_url("/protected/maplibre/index.html")
        heatmap_maplibre_url = cache_busted_url("/local/rainmapper-maplibre-heatmap/index.html") if PUBLIC_MAPLIBRE_HEATMAP_PATH.exists() else ""
        aemet_maplibre_url = cache_busted_url("/local/rainmapper-maplibre-aemet/index.html") if PUBLIC_MAPLIBRE_AEMET_PATH.exists() else ""
        bokeh_21d_url = cache_busted_url("/local/Plots/rain_21d.html")
        heatmap_card = (
            f'<div class="card"><span class="label">MapLibre heatmap experiment</span><span class="value">{html.escape(heatmap_maplibre_url)}</span></div>'
            if heatmap_maplibre_url
            else ""
        )
        aemet_card = (
            f'<div class="card"><span class="label">AEMET test viewer</span><span class="value">{html.escape(aemet_maplibre_url)}</span></div>'
            if aemet_maplibre_url
            else ""
        )
        viewer_links = [
            ("Open Leaflet viewer", leaflet_url, True),
            ("Open MapLibre viewer", maplibre_url, True),
            ("Open heatmap experiment", heatmap_maplibre_url, False),
            ("Open AEMET test viewer", aemet_maplibre_url, False),
            ("Open Bokeh 21 days", bokeh_21d_url, False),
        ]
        visible_viewer_count = len([_label for _label, url, _primary in viewer_links if url])
        maps_count = len(list(PLOTS_PATH.glob("*.html")))

        summary_cards = f"""
        <div class="summary-grid">
          <div class="card"><span class="label">Status</span><span class="value {status_class}">{status_text}</span></div>
          <div class="card"><span class="label">Version</span><span class="value">{html.escape(app_version())}</span></div>
          <div class="card"><span class="label">Next schedule</span><span class="value">{html.escape(next_schedule_text())}</span></div>
          <div class="card"><span class="label">Sources OK</span><span class="value ok">{ok_sources}/{total_sources}</span></div>
          <div class="card"><span class="label">Viewers</span><span class="value">{visible_viewer_count}</span></div>
          <div class="card"><span class="label">Generated maps</span><span class="value">{maps_count}</span></div>
        </div>
        """

        run_status_cards = f"""
        <div class="summary-grid">
          <div class="card"><span class="label">Action</span><span class="value">{html.escape(action)}</span></div>
          <div class="card"><span class="label">Current step</span><span class="value">{html.escape(current_step)}</span></div>
          <div class="card"><span class="label">Progress</span>{progress_html}</div>
          <div class="card"><span class="label">Started</span><span class="value">{html.escape(started_at)}</span></div>
          <div class="card"><span class="label">Finished</span><span class="value">{html.escape(finished_at)}</span></div>
          <div class="card"><span class="label">Duration</span><span class="value">{html.escape(duration)}</span></div>
          <div class="card"><span class="label">Exit code</span><span class="value">{html.escape(exit_code)}</span></div>
          <div class="card"><span class="label">Last published</span><span class="value">{html.escape(last_published_at)}</span></div>
          <div class="card"><span class="label">Bokeh maps</span><span class="value">/local/Plots</span></div>
          <div class="card"><span class="label">Leaflet viewer</span><span class="value">{html.escape(leaflet_url)}</span></div>
          <div class="card"><span class="label">MapLibre viewer</span><span class="value">{html.escape(maplibre_url)}</span></div>
          {heatmap_card}
          {aemet_card}
        </div>
        <p>{html.escape(message)}</p>
        <p>{html.escape(last_publish_message)}</p>
        """

        tabs = """
        <div class="control-tabs" role="tablist" aria-label="Rainmapper control panel sections">
          <button type="button" class="control-tab active" data-control-tab="summary" role="tab" aria-selected="true">Summary</button>
          <button type="button" class="control-tab" data-control-tab="sources" role="tab" aria-selected="false">Data sources</button>
          <button type="button" class="control-tab" data-control-tab="viewers" role="tab" aria-selected="false">Viewers</button>
          <button type="button" class="control-tab" data-control-tab="maps" role="tab" aria-selected="false">Maps</button>
          <button type="button" class="control-tab" data-control-tab="logs" role="tab" aria-selected="false">Logs</button>
          <button type="button" class="control-tab" data-control-tab="errors" role="tab" aria-selected="false">Errors</button>
        </div>
        """

        body = (
            '<div class="control-head">'
            "<div>"
            "<h1>Rainmapper</h1>"
            "<p>Control Panel</p>"
            "</div>"
            f"{head_controls}"
            "</div>"
            f"{controls}"
            f"{tabs}"
            '<section class="control-tab-panel" data-control-panel="summary">'
            '<div class="control-section"><h2>Summary</h2>'
            f"{summary_cards}"
            f"{run_status_cards}"
            "</div>"
            '<div class="control-section"><h2>Data sources</h2>'
            f"{source_table}"
            "</div>"
            '<div class="panel-grid">'
            '<div class="card"><h2>Current errors</h2><div class="compact-card-list">'
            f"{station_summary}"
            "</div></div>"
            '<div class="card"><h2>Quick viewers</h2>'
            f"{quick_viewer_links(viewer_links)}"
            "</div>"
            '<div class="card"><h2>Recent maps</h2>'
            f"{render_recent_map_links(limit=3)}"
            '<button type="button" class="button-link" data-control-tab="maps">View all maps</button>'
            "</div>"
            "</div>"
            '<div class="section-header">'
            "<h2>Last log</h2>"
            '<a class="button-link" href="./log" target="_blank" rel="noopener">Open full log</a>'
            "</div>"
            f"{render_log_preview()}"
            "</section>"
            '<section class="control-tab-panel" data-control-panel="sources" hidden>'
            '<div class="control-section"><h2>Data sources</h2>'
            f"{source_table}"
            f"{source_cards}"
            "</div></section>"
            '<section class="control-tab-panel" data-control-panel="viewers" hidden>'
            '<div class="control-section"><h2>Viewers</h2>'
            f"{quick_viewer_links(viewer_links)}"
            '<div class="status-grid"><div class="status-row status-row-publication">'
            f'<div class="card"><span class="label">Leaflet viewer</span><span class="value">{html.escape(leaflet_url)}</span></div>'
            f'<div class="card"><span class="label">MapLibre viewer</span><span class="value">{html.escape(maplibre_url)}</span></div>'
            f"{heatmap_card}"
            f"{aemet_card}"
            "</div></div>"
            "</div></section>"
            '<section class="control-tab-panel" data-control-panel="maps" hidden>'
            '<div class="control-section"><h2>Maps</h2>'
            f"{self.render_map_list()}"
            "</div></section>"
            '<section class="control-tab-panel" data-control-panel="logs" hidden>'
            '<div class="section-header">'
            "<h2>Logs</h2>"
            '<a class="button-link" href="./log" target="_blank" rel="noopener">Open full log</a>'
            "</div>"
            f"<pre>{html.escape(read_log())}</pre>"
            "</section>"
            '<section class="control-tab-panel" data-control-panel="errors" hidden>'
            '<div class="control-section"><h2>Errors</h2>'
            '<div class="station-grid">'
            f"{station_controls}"
            "</div></div></section>"
        )
        self.send_bytes(200, html_page("Rainmapper", body), "text/html; charset=utf-8")

    def render_log(self) -> None:
        body = (
            "<h1>Rainmapper log</h1>"
            '<p><a class="button-link" href="./">Back</a></p>'
            f"<pre>{html.escape(read_log())}</pre>"
        )
        self.send_bytes(200, html_page("Rainmapper log", body, auto_refresh=False), "text/html; charset=utf-8")

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
            self.send_bytes(
                200,
                auth_required_config_js().encode("utf-8"),
                "application/javascript",
                {"Cache-Control": "no-store, max-age=0"},
            )
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
