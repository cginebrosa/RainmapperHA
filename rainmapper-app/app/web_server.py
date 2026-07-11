from __future__ import annotations

import argparse
import calendar
import csv
import base64
import cgi
import hashlib
import html
import io
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
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import mushroom_catalogs_ui
import mushroom_gis_mappings_ui
import mushroom_profiles_ui
from rainmapper_core import mushroom_gis_lab
from rainmapper_core import mushroom_learned_model
from rainmapper_core import mushroom_model_state
from rainmapper_core import mushroom_observation_context
from rainmapper_core import mushroom_observation_features
from rainmapper_core import mushroom_observations
from rainmapper_core import mushroom_paths
from rainmapper_core.mushroom_store import default_store, write_json_atomic
from rainmapper_core.mushroom_validation import (
    empty_species_profile,
    validate_new_species_id,
    validate_profile_semantics,
    validate_profiles_semantics,
)


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
MUSHROOM_OBSERVATION_IMAGE_MAX_EDGE = 1600
MUSHROOM_OBSERVATION_IMAGE_JPEG_QUALITY = 86
DEVICE_SETTING_PERIODS = {"01d.geojson", "07d.geojson", "14d.geojson", "21d.geojson", "30d.geojson", "60d.geojson", "90d.geojson"}
DEVICE_SETTING_MAP_STYLES = {"esri-satellite-vector", "esri-hybrid", "opentopomap", "openfreemap-liberty"}
DEVICE_SETTING_SOURCES = {"Meteocat", "Meteoclimatic", "Wunderground", "AEMET", "Unknown"}
DEVICE_SETTING_LANGUAGES = {"en", "es", "ca"}
DEVICE_SETTING_LAYER_METRICS = {"rain", "max_temp", "min_temp", "max_humidity", "min_humidity", "wind"}
DEVICE_SETTING_HEATMAP_WEIGHT_CURVES = {"linear", "soft", "strong"}
DEVICE_SETTING_ESTIMATED_FIELD_RADII = {"small", "medium", "large"}
DEVICE_SETTING_ESTIMATED_FIELD_QUALITIES = {"low", "medium", "high"}
DEVICE_SETTING_ESTIMATED_FIELD_SMOOTHING = {"smooth", "balanced", "local"}
DEVICE_SETTING_ESTIMATED_FIELD_DEM_ZOOMS = {8, 9, 10}
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
    "mushroom_profiles_flash": "",
}
MUSHROOM_REBUILD_JOBS: dict[str, dict[str, object]] = {}
MUSHROOM_REBUILD_JOB_TTL_SECONDS = 3600


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


def raw_int_env(name: str, default: int) -> int:
    try:
        return int(env(name, str(default)))
    except ValueError:
        return default


def month_start_for_offset(reference: datetime, offset: int) -> datetime:
    month_index = reference.year * 12 + reference.month - 1 + offset
    return datetime(month_index // 12, month_index % 12 + 1, 1, tzinfo=reference.tzinfo)


def month_end_for_offset(reference: datetime, offset: int) -> datetime:
    month_start = month_start_for_offset(reference, offset)
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    return month_start.replace(day=last_day)


def monthly_backfill_enabled() -> bool:
    return bool_env("RAINMAPPER_BACKFILL_MONTHS_ENABLED", False)


def backfill_pause_seconds() -> int:
    return max(0, raw_int_env("RAINMAPPER_BACKFILL_PAUSE_SECONDS", 5))


def monthly_backfill_windows(reference: datetime | None = None) -> list[dict[str, int | str]]:
    reference = reference or datetime.now(get_timezone())
    months_init = raw_int_env("RAINMAPPER_MONTHS_INIT", -48)
    months_end = raw_int_env("RAINMAPPER_MONTHS_END", 0)
    months_interval = max(1, abs(raw_int_env("RAINMAPPER_MONTHS_INTERVAL", 3)))
    step = months_interval if months_init <= months_end else -months_interval

    windows: list[dict[str, int]] = []
    current = months_init
    while (step > 0 and current <= months_end) or (step < 0 and current >= months_end):
        if step > 0:
            window_end = min(current + step - 1, months_end)
            next_current = window_end + 1
        else:
            window_end = max(current + step + 1, months_end)
            next_current = window_end - 1

        start_date = month_start_for_offset(reference, current).date()
        end_date = reference.date() if window_end == 0 else month_end_for_offset(reference, window_end).date()
        windows.append(
            {
                "months_init": current,
                "months_end": window_end,
                "days_init": (start_date - reference.date()).days,
                "days_end": (end_date - reference.date()).days,
                "local_start_date": start_date.isoformat(),
                "local_end_date": end_date.isoformat(),
            }
        )
        current = next_current
    return windows


def backup_incrementals_for_backfill() -> str:
    backup_dir = DATA_PATH / "backups" / f"backfill_incrementals_{datetime.now(get_timezone()).strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source_path in sorted(DATA_PATH.glob("*_incremental.csv")):
        if source_path.is_file():
            shutil.copy2(source_path, backup_dir / source_path.name)
            copied += 1
    if copied:
        return f"Backed up {copied} incremental CSV file(s) to {backup_dir}."
    return "No incremental CSV files found to back up before monthly backfill."


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
        "opacity": percent_env("RAINMAPPER_MAPLIBRE_HEATMAP_OPACITY", 80, 0, 100) / 100,
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
        "opacity": percent_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_OPACITY", 90, 0, 100) / 100,
        "radius": option_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS", "medium", DEVICE_SETTING_ESTIMATED_FIELD_RADII),
        "quality": option_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_QUALITY", "medium", DEVICE_SETTING_ESTIMATED_FIELD_QUALITIES),
        "smoothing": option_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING", "balanced", DEVICE_SETTING_ESTIMATED_FIELD_SMOOTHING),
        "altitudeCorrection": bool_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ALTITUDE_CORRECTION", False),
        "demZoom": int_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_DEM_ZOOM", 9, 8, 10),
    }


def maplibre_estimated_field_config() -> dict:
    return {
        "defaults": maplibre_estimated_field_defaults(),
        "radiusKm": {
            "small": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_SMALL_KM", 10, 1, 1000),
            "medium": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_MEDIUM_KM", 15, 1, 1000),
            "large": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_LARGE_KM", 25, 1, 1000),
        },
        "maxRadiusKm": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_MAX_RADIUS_KM", 50, 1, 1000),
        "grid": {
            "low": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_LOW_CELL_KM", 2, 0.1, 100),
            "medium": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_MEDIUM_CELL_KM", 1, 0.1, 100),
            "high": number_env("RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_HIGH_CELL_KM", 0.5, 0.1, 100),
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


def html_page(title: str, body: str, auto_refresh: bool = True, page_class: str = "") -> bytes:
    refresh_tag = '<meta http-equiv="refresh" content="5">' if auto_refresh else ""
    main_class = f' class="{html.escape(page_class, quote=True)}"' if page_class else ""
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
      max-width: 1840px;
      margin: 0 auto;
      padding: 24px 20px 40px;
    }}
    main.mushroom-wide-page {{
      max-width: 1840px;
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
    .user-panel[hidden] {{
      display: none;
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
    .catalog-toolbar {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 0 0 14px;
    }}
    .catalog-toolbar form {{
      margin: 0;
    }}
    .catalog-filter {{
      flex: 1 1 280px;
      min-width: min(420px, 100%);
    }}
    .profile-view-switch {{
      align-items: center;
      display: inline-flex;
      gap: 6px;
      margin: 0 0 12px;
    }}
    .profile-view-switch.toolbar-switch {{
      margin: 0;
    }}
    .profile-view-switch .button-link {{
      padding: 7px 12px;
    }}
    .profile-view-switch .button-link.active {{
      background: rgba(3, 169, 244, .16);
      border-color: rgba(3, 169, 244, .8);
      color: var(--accent);
    }}
    .catalog-filter input,
    .catalog-json-editor textarea {{
      width: 100%;
    }}
    .profile-metrics.catalog-metrics {{
      display: grid;
      gap: 5px;
      grid-template-columns: repeat(9, minmax(0, 1fr));
      margin-bottom: 10px;
    }}
    .profile-metrics.catalog-metrics .profile-metric {{
      align-items: center;
      display: flex;
      gap: 6px;
      justify-content: flex-start;
      min-height: 34px;
      padding: 6px 7px;
    }}
    .profile-metrics.catalog-metrics .profile-metric .label {{
      font-size: 11px;
      line-height: 1.1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .profile-metrics.catalog-metrics .profile-metric .label::after {{
      content: ":";
      margin-left: 1px;
    }}
    .profile-metrics.catalog-metrics .profile-metric .value {{
      flex: 0 0 auto;
      font-size: 13px;
      margin: 0;
      white-space: nowrap;
    }}
    .catalog-chip-row {{
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      margin: 0 0 16px;
    }}
    .catalog-chip {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(15, 23, 42, .34);
      color: var(--fg);
      display: grid;
      gap: 5px;
      min-height: 70px;
      padding: 11px 12px;
      text-decoration: none;
    }}
    .catalog-chip.active {{
      background: rgba(3, 169, 244, 0.12);
      border-color: var(--accent);
      color: var(--accent);
    }}
    .catalog-chip strong {{
      font-size: 14px;
      line-height: 1.2;
    }}
    .catalog-chip span {{
      color: var(--muted);
      font-size: 12px;
    }}
    .catalog-domain-impact {{
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }}
    .catalog-domain-impact-grid {{
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .catalog-domain-impact .value {{
      display: block;
      margin-top: 3px;
    }}
    .catalog-domain-examples {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .catalog-domain-examples span {{
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 12px;
      padding: 4px 8px;
    }}
    .catalog-layout {{
      align-items: start;
      display: grid;
      gap: 16px;
      grid-template-columns: minmax(660px, 1fr) minmax(520px, .56fr);
    }}
    .catalog-table-wrap {{
      max-height: calc(100vh - 390px);
      min-height: 320px;
      overflow: auto;
    }}
    .catalog-table thead th {{
      background: var(--card);
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    .catalog-click-row {{
      cursor: pointer;
    }}
    .catalog-click-row:hover td {{
      background: rgba(3, 169, 244, .06);
    }}
    .catalog-detail {{
      font-size: 13px;
      max-height: calc(100vh - 24px);
      overflow-y: auto;
      position: sticky;
      top: 12px;
    }}
    .catalog-detail h2 {{
      font-size: 18px;
      margin: 0 0 8px;
    }}
    .catalog-detail p {{
      margin: 0 0 10px;
    }}
    .catalog-json-editor {{
      display: block;
      margin: 0;
    }}
    .catalog-entry-form {{
      display: grid;
      gap: 8px;
      margin: 0;
    }}
    .catalog-entry-form .admin-form-grid {{
      gap: 8px;
      grid-template-columns: 1fr;
      margin: 8px 0 10px;
    }}
    .catalog-entry-form .admin-field label {{
      font-size: 12px;
      margin-bottom: 3px;
    }}
    .catalog-entry-form .admin-field.compact {{
      align-items: center;
      display: grid;
      gap: 8px;
      grid-template-columns: minmax(112px, .34fr) minmax(0, 1fr);
    }}
    .catalog-entry-form .admin-field.compact label {{
      margin-bottom: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .catalog-entry-form .admin-field.compact label::after {{
      content: ":";
      margin-left: 1px;
    }}
    .catalog-entry-form input,
    .catalog-entry-form select {{
      min-height: 34px;
      padding: 0 9px;
    }}
    .catalog-entry-form textarea {{
      background: var(--bg);
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--fg);
      font: inherit;
      line-height: 1.25;
      min-height: 56px;
      padding: 8px 9px;
      resize: vertical;
      width: 100%;
    }}
    .catalog-entry-actions {{
      background: linear-gradient(180deg, rgba(30, 39, 46, .78), var(--card) 35%);
      bottom: -14px;
      display: flex;
      justify-content: flex-end;
      margin: 0 -14px;
      padding: 10px 14px 14px;
      position: sticky;
      z-index: 2;
    }}
    .catalog-entry-actions .primary {{
      min-width: 180px;
    }}
    .catalog-reference-checks {{
      display: grid;
      gap: 6px;
      margin: 8px 0 12px;
    }}
    .catalog-reference-check {{
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      padding: 8px 9px;
    }}
    .catalog-reference-check.ok {{
      border-color: rgba(52, 211, 153, .35);
      color: var(--ok);
    }}
    .catalog-reference-check.error {{
      border-color: rgba(255, 107, 107, .5);
      color: var(--danger);
    }}
    .catalog-reference-check strong {{
      color: var(--fg);
      display: block;
      margin-bottom: 2px;
    }}
    .catalog-create-form {{
      display: block;
      margin: 0;
    }}
    .catalog-json-editor textarea {{
      background: #0c1116;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--fg);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      line-height: 1.45;
      min-height: 320px;
      padding: 12px;
      resize: vertical;
    }}
    .catalog-row-link {{
      color: var(--fg);
      font-weight: 700;
      text-decoration: none;
    }}
    .catalog-row-link:hover,
    .catalog-row-link:focus {{
      color: var(--accent);
    }}
    .catalog-table .selected-row td {{
      background: rgba(3, 169, 244, .16);
      border-bottom-color: rgba(3, 169, 244, .46);
      border-top: 1px solid rgba(3, 169, 244, .46);
      color: var(--fg);
    }}
    .catalog-table .selected-row td:first-child {{
      border-left: 4px solid var(--accent);
      padding-left: 8px;
    }}
    .catalog-table .selected-row .catalog-row-link {{
      color: var(--accent);
      font-weight: 900;
    }}
    .catalog-table .selected-row td:nth-child(3) {{
      color: #fff;
      font-weight: 800;
    }}
    .catalog-alert-list {{
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }}
    .catalog-alert {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
    }}
    .catalog-alert.error {{
      border-color: rgba(255, 107, 107, 0.55);
      color: var(--danger);
    }}
    .catalog-alert.warn {{
      border-color: rgba(255, 209, 102, 0.55);
      color: #ffd166;
    }}
    .profile-layout {{
      align-items: start;
      display: grid;
      gap: 16px;
      grid-template-columns: minmax(400px, .34fr) minmax(820px, 1fr);
    }}
    .profile-list {{
      background: linear-gradient(180deg, rgba(2, 23, 38, .72), rgba(15, 23, 42, .28));
      border: 1px solid var(--line);
      border-radius: 10px;
      display: grid;
      gap: 0;
      grid-template-rows: auto minmax(0, 1fr);
      max-height: calc(100vh - 24px);
      overflow: hidden;
      position: sticky;
      top: 12px;
    }}
    .profile-list-search-title {{
      align-items: center;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      display: grid;
      font-size: 12px;
      font-weight: 800;
      gap: 10px;
      grid-template-columns: 28px minmax(0, 1fr) 54px 54px 70px;
      letter-spacing: 0;
      padding: 10px 12px 10px 14px;
      text-transform: uppercase;
    }}
    .profile-list-title {{
      grid-column: 1 / 3;
    }}
    .profile-list-chip-legend {{
      align-items: center;
      display: grid;
      gap: 5px;
      grid-column: 3 / 6;
      grid-template-columns: 54px 54px 70px;
      text-transform: none;
    }}
    .profile-list-chip-legend span {{
      border: 1px solid rgba(148, 163, 184, .22);
      border-radius: 999px;
      color: var(--muted);
      font-size: 10px;
      line-height: 1;
      padding: 2px 5px;
      text-align: center;
    }}
    .profile-list-rows {{
      min-height: 0;
      overflow-y: auto;
    }}
    .profile-list-item {{
      align-items: center;
      background: transparent;
      border: 0;
      border-bottom: 1px solid rgba(45, 58, 71, .72);
      border-radius: 0;
      color: var(--fg);
      display: grid;
      gap: 8px 10px;
      grid-template-columns: 28px minmax(0, 1fr) 54px 54px 70px;
      min-height: 60px;
      padding: 9px 12px 9px 14px;
      text-decoration: none;
    }}
    .profile-list-item:last-child {{
      border-bottom: 0;
    }}
    .profile-list-item.active {{
      background: linear-gradient(90deg, rgba(3, 169, 244, .22), rgba(3, 169, 244, .06) 78%, rgba(3, 169, 244, 0));
      box-shadow: inset 3px 0 0 var(--accent);
    }}
    .profile-list-item:hover {{
      background: rgba(3, 169, 244, .07);
    }}
    .profile-list-icon {{
      align-items: center;
      background: rgba(3, 169, 244, .06);
      border: 1px solid rgba(3, 169, 244, .42);
      border-radius: 999px;
      color: var(--accent);
      display: inline-flex;
      font-size: 16px;
      height: 26px;
      justify-content: center;
      width: 26px;
    }}
    .profile-list-icon svg,
    .profile-hero-icon svg,
    .profile-tab-labels svg {{
      fill: none;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.8;
    }}
    .profile-list-icon svg {{
      height: 17px;
      width: 17px;
    }}
    .profile-list-main {{
      display: grid;
      gap: 2px;
      min-width: 0;
    }}
    .profile-list-item strong {{
      font-size: 14px;
      line-height: 1.2;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .profile-chip-line {{
      display: grid;
      gap: 5px;
      grid-column: 3 / 6;
      grid-template-columns: 54px 54px 70px;
    }}
    .profile-chip {{
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 11px;
      overflow: hidden;
      padding: 2px 7px;
      text-align: center;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .profile-chip.high,
    .profile-chip.very_high {{
      border-color: rgba(52, 211, 153, .42);
      color: var(--ok);
    }}
    .profile-chip.medium {{
      border-color: rgba(255, 176, 32, .46);
      color: #ffb020;
    }}
    .profile-chip.low,
    .profile-chip.very_low {{
      border-color: rgba(255, 107, 107, .46);
      color: var(--danger);
    }}
    .profile-metrics {{
      display: grid;
      gap: 6px;
      grid-template-columns: repeat(8, minmax(96px, 1fr));
      margin: 0 0 14px;
    }}
    .profile-new-species {{
      margin: 0 0 14px;
    }}
    .profile-new-species summary {{
      cursor: pointer;
    }}
    .profile-new-species p {{
      margin-bottom: 10px;
    }}
    .profile-metric {{
      align-items: center;
      background: rgba(15, 23, 42, .34);
      border: 1px solid var(--line);
      border-radius: 8px;
      display: flex;
      gap: 6px;
      justify-content: space-between;
      min-width: 0;
      min-height: 34px;
      padding: 5px 7px;
    }}
    .profile-metric .label {{
      font-size: 11px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .profile-metric .value {{
      font-size: 13px;
      white-space: nowrap;
    }}
    .profile-editor {{
      display: grid;
      gap: 12px;
    }}
    .profile-editor-polished {{
      background:
        radial-gradient(circle at 8% 0%, rgba(3, 169, 244, .18), transparent 32%),
        linear-gradient(180deg, rgba(3, 169, 244, .08), rgba(3, 169, 244, 0) 190px),
        rgba(15, 23, 42, .54);
      border-radius: 10px;
    }}
    .profile-editor-head {{
      align-items: start;
      display: flex;
      gap: 12px;
      justify-content: space-between;
    }}
    .profile-hero {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 12px;
    }}
    .profile-title-block {{
      align-items: center;
      display: flex;
      gap: 12px;
      min-width: 0;
    }}
    .profile-title-block h2 {{
      font-size: 20px;
      margin: 0 0 4px;
    }}
    .profile-hero-side {{
      align-items: flex-end;
      display: flex;
      flex-direction: column;
      gap: 10px;
      flex: 1 1 auto;
      min-width: min(760px, 55vw);
    }}
    .profile-header-selector {{
      align-items: center;
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      max-width: 100%;
    }}
    .profile-header-selector label {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .profile-header-selector select {{
      max-width: min(360px, 36vw);
      min-width: 220px;
    }}
    .profile-hero-icon {{
      align-items: center;
      border: 1px solid rgba(148, 163, 184, .35);
      border-radius: 999px;
      color: var(--accent);
      display: inline-flex;
      flex: 0 0 38px;
      font-size: 24px;
      height: 38px;
      justify-content: center;
      width: 38px;
    }}
    .profile-hero-icon svg {{
      height: 25px;
      width: 25px;
    }}
    .profile-hero-chips {{
      display: flex;
      flex-wrap: nowrap;
      gap: 7px;
      justify-content: end;
      min-width: 0;
      width: 100%;
    }}
    .profile-status-chip {{
      align-items: center;
      background: rgba(2, 13, 22, .55);
      border: 1px solid rgba(45, 58, 71, .92);
      border-radius: 8px;
      color: var(--fg);
      display: inline-flex;
      gap: 5px;
      min-height: 30px;
      padding: 5px 8px;
      white-space: nowrap;
    }}
    .profile-status-chip.accepted,
    .profile-status-chip.excellent,
    .profile-status-chip.good,
    .profile-status-chip.high,
    .profile-status-chip.very_high,
    .profile-status-chip.locally_calibrated,
    .profile-status-chip.reviewed,
    .profile-status-chip.published {{
      border-color: rgba(52, 211, 153, .42);
      color: var(--ok);
    }}
    .profile-status-chip.medium,
    .profile-status-chip.draft,
    .profile-status-chip.not_calibrated,
    .profile-status-chip.partially_calibrated,
    .profile-status-chip.needs_review {{
      border-color: rgba(255, 176, 32, .48);
      color: #ffb020;
    }}
    .profile-status-chip.low,
    .profile-status-chip.very_low {{
      border-color: rgba(255, 107, 107, .52);
      color: var(--danger);
    }}
    .profile-chip-label {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
    }}
    .profile-section {{
      border-top: 1px solid var(--line);
      display: grid;
      gap: 10px;
      padding-top: 12px;
    }}
    .profile-section h2 {{
      font-size: 16px;
      margin: 0;
    }}
    .profile-section-head {{
      align-items: end;
      display: grid;
      gap: 14px;
      grid-template-columns: minmax(120px, auto) minmax(360px, 1fr);
    }}
    .profile-section-head .admin-field {{
      max-width: 720px;
    }}
    .profile-section-head .admin-field {{
      align-items: center;
      display: grid;
      gap: 6px;
      grid-template-columns: auto minmax(0, 1fr);
    }}
    .profile-section-head .admin-field label {{
      margin-bottom: 0;
      white-space: nowrap;
    }}
    .profile-section-head .admin-field label::after {{
      content: ":";
      margin-left: 1px;
    }}
    .profile-tabs {{
      display: grid;
      gap: 12px;
    }}
    .profile-tabs input[type="radio"] {{
      height: 1px;
      opacity: 0;
      pointer-events: none;
      position: absolute;
      width: 1px;
    }}
    .profile-tab-labels {{
      border-bottom: 1px solid var(--line);
      display: flex;
      flex-wrap: wrap;
      gap: 22px;
      padding: 0 0 0;
    }}
    .profile-tab-labels label {{
      align-items: center;
      border-bottom: 2px solid transparent;
      color: var(--muted);
      cursor: pointer;
      display: inline-flex;
      font-size: 12px;
      gap: 6px;
      font-weight: 700;
      min-height: 36px;
      padding: 0 0 8px;
    }}
    .profile-tab-labels svg {{
      height: 15px;
      width: 15px;
    }}
    .profile-tab-panel {{
      display: none;
    }}
    #profile-tab-general:checked ~ .profile-tab-labels label[for="profile-tab-general"],
    #profile-tab-ecology:checked ~ .profile-tab-labels label[for="profile-tab-ecology"],
    #profile-tab-phenology:checked ~ .profile-tab-labels label[for="profile-tab-phenology"],
    #profile-tab-weather:checked ~ .profile-tab-labels label[for="profile-tab-weather"],
    #profile-tab-scoring:checked ~ .profile-tab-labels label[for="profile-tab-scoring"],
    #profile-tab-calibration:checked ~ .profile-tab-labels label[for="profile-tab-calibration"],
    #profile-tab-metadata:checked ~ .profile-tab-labels label[for="profile-tab-metadata"],
    #profile-tab-json:checked ~ .profile-tab-labels label[for="profile-tab-json"] {{
      border-bottom-color: var(--accent);
      color: var(--accent);
    }}
    #profile-tab-general:checked ~ .profile-tab-content .profile-tab-panel.general,
    #profile-tab-ecology:checked ~ .profile-tab-content .profile-tab-panel.ecology,
    #profile-tab-phenology:checked ~ .profile-tab-content .profile-tab-panel.phenology,
    #profile-tab-weather:checked ~ .profile-tab-content .profile-tab-panel.weather,
    #profile-tab-scoring:checked ~ .profile-tab-content .profile-tab-panel.scoring,
    #profile-tab-calibration:checked ~ .profile-tab-content .profile-tab-panel.calibration,
    #profile-tab-metadata:checked ~ .profile-tab-content .profile-tab-panel.metadata,
    #profile-tab-json:checked ~ .profile-tab-content .profile-tab-panel.json {{
      display: grid;
    }}
    .profile-overview-grid {{
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(12, minmax(0, 1fr));
    }}
    .profile-overview-card {{
      background:
        linear-gradient(180deg, rgba(15, 23, 42, .56), rgba(2, 13, 22, .3)),
        rgba(2, 13, 22, .32);
      border: 1px solid rgba(45, 58, 71, .82);
      border-radius: 8px;
      display: grid;
      gap: 8px;
      grid-column: span 4;
      padding: 12px;
    }}
    .profile-overview-card.identity {{
      border-color: rgba(3, 169, 244, .26);
    }}
    .profile-overview-card.wide {{
      grid-column: span 4;
    }}
    .profile-overview-card.full {{
      grid-column: 1 / -1;
    }}
    .profile-card-title {{
      align-items: center;
      display: flex;
      gap: 8px;
      font-size: 14px;
      margin: 0 0 2px;
    }}
    .profile-card-icon {{
      align-items: center;
      background: rgba(3, 169, 244, .08);
      border: 1px solid rgba(3, 169, 244, .34);
      border-radius: 999px;
      color: var(--accent);
      display: inline-flex;
      height: 24px;
      justify-content: center;
      width: 24px;
    }}
    .profile-card-icon svg {{
      fill: none;
      height: 15px;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.8;
      width: 15px;
    }}
    .profile-kv {{
      align-items: baseline;
      border-bottom: 1px solid rgba(45, 58, 71, .45);
      display: grid;
      gap: 8px;
      grid-template-columns: minmax(96px, .72fr) minmax(0, 1fr);
      padding: 5px 0;
    }}
    .profile-kv.stacked {{
      align-items: start;
      gap: 6px;
      grid-template-columns: minmax(0, 1fr);
      padding: 7px 0;
    }}
    .profile-kv > span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .profile-kv strong {{
      font-size: 12px;
      font-weight: 700;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .profile-subsection {{
      border: 1px solid rgba(45, 58, 71, .55);
      border-radius: 8px;
      display: grid;
      gap: 10px;
      padding: 10px;
    }}
    .profile-subsection h3 {{
      align-items: center;
      display: flex;
      font-size: 13px;
      gap: 7px;
      margin: 0;
    }}
    .profile-subsection h3 svg {{
      fill: none;
      height: 16px;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.8;
      width: 16px;
    }}
    .month-chip-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }}
    .month-chip {{
      border: 1px solid rgba(45, 58, 71, .9);
      border-radius: 6px;
      box-sizing: border-box;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      width: 34px;
      padding: 4px 6px;
      text-align: center;
    }}
    .month-chip.active {{
      background: rgba(3, 169, 244, .72);
      border-color: rgba(3, 169, 244, .96);
      color: white;
    }}
    .month-chip.secondary-month {{
      background: rgba(3, 169, 244, .72);
      border-color: rgba(3, 169, 244, .96);
      color: white;
    }}
    .month-chip.warn {{
      border-color: rgba(255, 209, 102, .65);
      color: #ffd166;
    }}
    .month-toggle-field {{
      display: block;
    }}
    .month-toggle-field .field-label {{
      color: var(--muted);
      display: block;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .month-toggle-grid {{
      display: grid;
      gap: 6px;
      grid-template-columns: repeat(6, 34px);
    }}
    .month-toggle input {{
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }}
    .month-toggle .month-chip {{
      cursor: pointer;
      display: block;
      user-select: none;
    }}
    .month-toggle input:not(:checked) + .month-chip.active,
    .month-toggle input:not(:checked) + .month-chip.secondary-month {{
      background: transparent;
      border-color: rgba(45, 58, 71, .9);
      color: var(--muted);
    }}
    .month-toggle input:checked + .month-chip.active {{
      background: rgba(3, 169, 244, .72);
      border-color: rgba(3, 169, 244, .96);
      color: white;
    }}
    .month-toggle input:checked + .month-chip.secondary-month {{
      background: rgba(3, 169, 244, .72);
      border-color: rgba(3, 169, 244, .96);
      color: white;
    }}
    .host-toggle-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      grid-template-columns: none;
    }}
    .month-toggle .host-chip {{
      display: inline-flex;
      max-width: 220px;
      min-height: 26px;
      width: auto;
    }}
    .month-toggle input:not(:checked) + .host-chip.active {{
      background: transparent;
      border-color: rgba(45, 58, 71, .9);
      color: var(--muted);
    }}
    .catalog-toggle-field {{
      display: block;
    }}
    .catalog-toggle-field .field-label {{
      color: var(--muted);
      display: block;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .catalog-toggle-grid {{
      align-content: start;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .catalog-toggle input {{
      opacity: 0;
      pointer-events: none;
      position: absolute;
    }}
    .catalog-chip {{
      background: transparent;
      border: 1px solid rgba(45, 58, 71, .9);
      border-radius: 6px;
      color: var(--muted);
      cursor: pointer;
      display: inline-flex;
      font-size: 11px;
      font-weight: 800;
      line-height: 1.15;
      max-width: 210px;
      min-height: 26px;
      padding: 5px 7px;
      user-select: none;
    }}
    .catalog-toggle input:checked + .catalog-chip {{
      background: rgba(3, 169, 244, .72);
      border-color: rgba(3, 169, 244, .96);
      color: white;
    }}
    .catalog-chip.missing {{
      border-color: rgba(255, 209, 102, .65);
      color: #ffd166;
      cursor: default;
    }}
    .profile-weather-grid {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .score-row {{
      align-items: center;
      display: grid;
      gap: 8px;
      grid-template-columns: minmax(96px, .8fr) minmax(80px, 1fr) 42px;
      min-height: 24px;
    }}
    .score-row span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .score-row strong {{
      font-size: 12px;
      text-align: right;
    }}
    .score-track {{
      background: rgba(2, 13, 22, .62);
      border-radius: 999px;
      height: 8px;
      overflow: hidden;
    }}
    .score-track span {{
      background: var(--accent);
      display: block;
      height: 100%;
    }}
    .profile-scoring-total {{
      align-items: center;
      background: rgba(2, 13, 22, .45);
      border: 1px solid rgba(45, 58, 71, .82);
      border-radius: 8px;
      display: inline-grid;
      gap: 8px;
      grid-template-columns: auto auto auto;
      justify-self: start;
      padding: 8px 10px;
    }}
    .profile-scoring-total span,
    .profile-scoring-total em {{
      color: var(--muted);
      font-size: 12px;
      font-style: normal;
      font-weight: 700;
    }}
    .profile-scoring-total strong {{
      color: var(--fg);
      font-size: 15px;
    }}
    .profile-metadata-strip {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }}
    .profile-calibration-summary {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .profile-calibration-summary div {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
    }}
    .profile-grid {{
      display: grid;
      gap: 9px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .profile-grid.three {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .profile-grid.four {{
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .profile-grid.full {{
      grid-template-columns: minmax(0, 1fr);
    }}
    .profile-phenology-layout {{
      display: grid;
      gap: 9px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .profile-phenology-left {{
      display: grid;
      gap: 9px;
    }}
    .profile-month-grid,
    .profile-delay-grid {{
      display: grid;
      gap: 9px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .profile-season-pattern-field,
    .profile-season-pattern-field .admin-field {{
      min-height: 100%;
    }}
    .profile-season-pattern-field textarea {{
      height: 100%;
      min-height: 160px;
    }}
    .profile-topography-layout {{
      display: grid;
      gap: 9px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .profile-altitude-grid {{
      display: grid;
      gap: 9px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .profile-aspect-field,
    .profile-aspect-field .admin-field {{
      min-height: 100%;
    }}
    .profile-aspect-field textarea {{
      height: 100%;
      min-height: 106px;
    }}
    .profile-affinity-block {{
      display: grid;
      gap: 6px;
    }}
    .profile-affinity-rows {{
      display: grid;
      gap: 7px;
      max-height: 352px;
      overflow-y: auto;
      padding-right: 4px;
    }}
    .ecology-subtabs {{
      display: grid;
      gap: 10px;
    }}
    .ecology-subtabs > input[type="radio"] {{
      height: 1px;
      opacity: 0;
      pointer-events: none;
      position: absolute;
      width: 1px;
    }}
    .ecology-subtab-labels {{
      border-bottom: 1px solid var(--line);
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
    }}
    .ecology-subtab-labels label {{
      border-bottom: 2px solid transparent;
      color: var(--muted);
      cursor: pointer;
      font-size: 12px;
      font-weight: 800;
      min-height: 32px;
      padding: 0 0 8px;
    }}
    .ecology-subtab-panel {{
      display: none;
    }}
    #eco-tab-0:checked ~ .ecology-subtab-labels label[for="eco-tab-0"],
    #eco-tab-1:checked ~ .ecology-subtab-labels label[for="eco-tab-1"],
    #eco-tab-2:checked ~ .ecology-subtab-labels label[for="eco-tab-2"],
    #eco-tab-3:checked ~ .ecology-subtab-labels label[for="eco-tab-3"],
    #eco-tab-4:checked ~ .ecology-subtab-labels label[for="eco-tab-4"] {{
      border-bottom-color: var(--accent);
      color: var(--accent);
    }}
    #eco-tab-0:checked ~ .ecology-subtab-content .panel-0,
    #eco-tab-1:checked ~ .ecology-subtab-content .panel-1,
    #eco-tab-2:checked ~ .ecology-subtab-content .panel-2,
    #eco-tab-3:checked ~ .ecology-subtab-content .panel-3,
    #eco-tab-4:checked ~ .ecology-subtab-content .panel-4 {{
      display: grid;
    }}
    .profile-affinity-row {{
      align-items: end;
      display: grid;
      gap: 7px;
      grid-template-columns: minmax(230px, .85fr) minmax(126px, .38fr) minmax(126px, .34fr) minmax(78px, .22fr);
    }}
    .profile-affinity-row .admin-field {{
      align-items: center;
      display: grid;
      gap: 6px;
      grid-template-columns: auto minmax(0, 1fr);
    }}
    .profile-affinity-row .admin-field label {{
      margin-bottom: 0;
      white-space: nowrap;
    }}
    .profile-affinity-row .admin-field label::after {{
      content: ":";
      margin-left: 1px;
    }}
    .profile-affinity-origins > div {{
      min-width: 0;
    }}
    .profile-origin-badges {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      min-height: 26px;
    }}
    .profile-origin-badge {{
      border: 1px solid rgba(3, 169, 244, .48);
      border-radius: 999px;
      color: var(--accent);
      font-size: 11px;
      font-weight: 800;
      line-height: 1;
      padding: 3px 7px;
      white-space: nowrap;
    }}
    .profile-origin-empty {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .profile-editor .admin-field label {{
      font-size: 12px;
      margin-bottom: 3px;
    }}
    .profile-editor input,
    .profile-editor select {{
      font-size: 12px;
      min-height: 34px;
      padding: 0 9px;
    }}
    .profile-editor textarea {{
      background: var(--bg);
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--fg);
      font: inherit;
      font-size: 12px;
      line-height: 1.3;
      min-height: 58px;
      padding: 8px 9px;
      resize: vertical;
      width: 100%;
    }}
    .profile-json-editor textarea {{
      background: #0c1116;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--fg);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      line-height: 1.45;
      min-height: 420px;
      padding: 12px;
      resize: vertical;
      width: 100%;
    }}
    .profile-action-bar {{
      align-items: center;
      background: rgba(2, 13, 22, .28);
      border-top: 1px solid var(--line);
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: flex-end;
      margin-top: 12px;
      padding: 12px 0 0;
    }}
    .profile-primary-action {{
      min-width: 210px;
    }}
    .secondary,
    .danger-button {{
      background: rgba(15, 23, 42, .42);
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--fg);
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      min-height: 36px;
      padding: 0 14px;
    }}
    .danger-button {{
      border-color: rgba(255, 107, 107, .55);
      color: var(--danger);
    }}
    .secondary:disabled,
    .danger-button:disabled {{
      cursor: not-allowed;
      opacity: .48;
    }}
    .planned-action:disabled {{
      border-style: dashed;
      opacity: .62;
    }}
    .profile-maintenance-actions {{
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}
    .profile-lifecycle-grid {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin-top: 10px;
    }}
    .profile-lifecycle-card {{
      border: 1px solid rgba(45, 58, 71, .65);
      border-radius: 8px;
      display: grid;
      gap: 10px;
      padding: 12px;
    }}
    .profile-lifecycle-card h3 {{
      font-size: 14px;
      margin: 0;
    }}
    .archived-species-panel {{
      margin: 16px 0;
    }}
    .archived-species-row {{
      align-items: center;
      border-top: 1px solid rgba(45, 58, 71, .65);
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(0, 1fr) auto;
      padding: 10px 0;
    }}
    .archived-species-row:first-of-type {{
      border-top: 0;
    }}
    .archived-species-row .meta {{
      display: block;
      margin-top: 2px;
    }}
    .archived-species-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .profile-raw-json {{
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}
    .profile-section-screen {{
      background:
        radial-gradient(circle at 8% 0%, rgba(3, 169, 244, .14), transparent 30%),
        linear-gradient(180deg, rgba(3, 169, 244, .07), rgba(3, 169, 244, 0) 180px),
        rgba(15, 23, 42, .54);
      display: grid;
      gap: 14px;
    }}
    .profile-section-banner {{
      align-items: center;
      border: 1px solid rgba(3, 169, 244, .38);
      border-radius: 8px;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      padding: 12px;
    }}
    .parameters-screen .profile-section-banner.compact {{
      align-items: center;
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(260px, .46fr) minmax(620px, .54fr);
      padding: 8px 14px 6px;
    }}
    .parameters-screen .profile-section-banner.compact .profile-title-block h2 {{
      font-size: 19px;
      margin: 0 0 3px;
    }}
    .parameters-screen .profile-section-banner.compact .profile-hero-icon {{
      height: 38px;
      width: 38px;
    }}
    .parameters-screen .profile-section-banner.compact .profile-hero-side {{
      gap: 5px;
      min-width: 0;
    }}
    .parameters-screen .profile-section-banner.compact .profile-hero-chips {{
      flex-wrap: nowrap;
      justify-content: flex-end;
      max-width: none;
      width: 100%;
    }}
    .parameters-screen .profile-section-banner.compact .profile-status-chip {{
      border-radius: 7px;
      font-size: 12px;
      gap: 4px;
      min-height: 26px;
      padding: 3px 7px;
    }}
    .parameters-screen .profile-section-banner.compact .profile-chip-label {{
      font-size: 9px;
    }}
    .parameters-screen .profile-section-banner.compact .profile-header-selector select {{
      min-height: 26px;
    }}
    .profile-section-card {{
      background: rgba(2, 13, 22, .28);
      border: 1px solid rgba(45, 58, 71, .76);
      border-radius: 8px;
      align-content: start;
      display: grid;
      gap: 10px;
      padding: 12px;
    }}
    .profile-section-card h2 {{
      align-items: center;
      display: flex;
      font-size: 15px;
      gap: 8px;
      margin: 0;
    }}
    .profile-section-card h2 svg {{
      fill: none;
      height: 17px;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.8;
      width: 17px;
    }}
    .profile-section-card-grid,
    .profile-parameters-grid,
    .profile-calibration-grid {{
      display: grid;
      gap: 12px;
    }}
    .profile-parameters-grid {{
      align-items: start;
      grid-template-columns: minmax(360px, .76fr) minmax(0, 1.24fr);
    }}
    .profile-parameters-grid.v0 {{
      grid-template-columns: minmax(0, 1fr);
    }}
    .profile-section-card-grid.two,
    .profile-calibration-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .profile-subsection.full,
    .profile-section-card.full {{
      grid-column: 1 / -1;
    }}
    .profile-section-screen .admin-field label {{
      font-size: 12px;
      margin-bottom: 3px;
    }}
    .profile-section-screen input,
    .profile-section-screen select {{
      font-size: 12px;
      min-height: 34px;
      padding: 0 9px;
    }}
    .profile-section-screen textarea {{
      background: var(--bg);
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--fg);
      font: inherit;
      font-size: 12px;
      line-height: 1.3;
      min-height: 58px;
      padding: 8px 9px;
      resize: vertical;
      width: 100%;
    }}
    .parameters-screen {{
      gap: 12px;
    }}
    .parameters-screen .profile-section-card {{
      gap: 8px;
      padding: 10px;
    }}
    .parameters-screen .profile-subsection {{
      gap: 7px;
      padding: 9px;
    }}
    .parameter-section-tabs {{
      align-items: center;
      border-bottom: 1px solid rgba(45, 58, 71, .86);
      display: flex;
      flex-wrap: wrap;
      gap: 0;
      margin: -2px 0 2px;
    }}
    .parameter-section-tabs a {{
      border: 1px solid transparent;
      border-bottom: 0;
      border-radius: 8px 8px 0 0;
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      margin: 0 3px -1px 0;
      padding: 9px 14px 10px;
      position: relative;
      text-decoration: none;
    }}
    .parameter-section-tabs a:hover {{
      background: rgba(148, 163, 184, .08);
      color: var(--text);
    }}
    .parameter-section-tabs a.active {{
      background: rgba(7, 18, 31, .96);
      border-color: var(--accent);
      border-bottom-color: rgba(7, 18, 31, .96);
      color: var(--accent);
    }}
    .parameter-tabbed-grid {{
      grid-template-columns: 1fr;
    }}
    .parameter-tab-panel {{
      min-width: 0;
    }}
    .parameter-tab-panel.inactive {{
      display: none;
    }}
    .parameter-focus-subsection {{
      min-height: min(520px, 46vh);
    }}
    .parameter-comparison-layout {{
      align-items: stretch;
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(360px, 1.1fr) minmax(280px, .85fr) minmax(280px, .85fr);
    }}
    .parameter-learned-comparison {{
      background: rgba(4, 16, 28, .56);
      align-content: start;
      font-size: 12px;
      grid-template-rows: auto auto auto minmax(0, 1fr);
    }}
    .parameter-learned-comparison h3 {{
      align-items: center;
      display: flex;
      font-size: 13px;
      gap: 7px;
      margin: 0;
    }}
    .parameter-ecology-profile,
    .parameter-ecology-learned {{
      display: grid;
      grid-template-rows: auto minmax(66px, auto) minmax(224px, auto) minmax(76px, auto) minmax(88px, auto);
      min-height: 0;
    }}
    .parameter-aligned-column {{
      display: grid;
      grid-template-rows: minmax(66px, auto) minmax(84px, auto) minmax(84px, auto) minmax(84px, auto) auto;
      min-height: 0;
    }}
    .parameter-soils-column {{
      grid-template-rows: 66px 96px 96px auto;
    }}
    .parameter-topography-column {{
      grid-template-rows: 82px 100px 108px auto;
    }}
    .parameter-phenology-column {{
      grid-template-rows: 72px 112px 112px 166px auto;
    }}
    .parameter-ecology-profile .parameter-profile-sections,
    .parameter-ecology-learned .parameter-learned-rows,
    .parameter-aligned-column .parameter-learned-rows {{
      display: contents;
    }}
    .parameter-profile-sections {{
      display: grid;
      gap: 8px;
    }}
    .parameter-comparison-section {{
      align-content: start;
      background: rgba(3, 12, 22, .28);
      border: 1px solid rgba(45, 58, 71, .58);
      border-radius: 8px;
      display: grid;
      gap: 6px;
      padding: 8px;
    }}
    .parameter-profile-section h4,
    .parameter-learned-row h4,
    .parameter-learned-summary h4 {{
      color: var(--text);
      font-size: 12px;
      font-weight: 800;
      line-height: 1.25;
      margin: 0;
    }}
    .parameter-section-values {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }}
    .parameter-section-summary {{
      min-height: 66px;
    }}
    .parameter-profile-section > .admin-field > .field-label,
    .parameter-profile-section > .parameter-text-row > span {{
      display: none;
    }}
    .parameter-topography-notes {{
      align-content: start;
    }}
    .parameter-topography-notes .parameter-text-row textarea {{
      min-height: 44px;
      width: 100%;
    }}
    .parameter-pending-note {{
      align-self: start;
      margin: 0;
      padding: 0 2px;
    }}
    .parameter-section-hosts {{
      min-height: 0;
    }}
    .parameter-section-forests,
    .parameter-section-habitat {{
      min-height: 0;
    }}
    .parameter-learned-metrics {{
      display: grid;
      gap: 6px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .parameter-learned-metrics span {{
      border: 1px solid var(--line);
      border-radius: 7px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      padding: 7px;
    }}
    .parameter-learned-metrics strong {{
      color: var(--text);
      float: right;
    }}
    .parameter-learned-rows {{
      display: grid;
      gap: 8px;
    }}
    .parameter-learned-row {{
      align-content: start;
      grid-template-rows: auto auto;
    }}
    .parameter-learned-values {{
      align-items: flex-start;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .parameter-learned-chip {{
      align-items: center;
      border: 1px solid rgba(0, 174, 255, .45);
      border-radius: 7px;
      display: inline-flex;
      gap: 6px;
      line-height: 1.15;
      max-width: 100%;
      min-height: 24px;
      padding: 4px 7px;
    }}
    .parameter-learned-chip span {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .parameter-learned-chip strong {{
      color: var(--accent);
      font-size: 12px;
    }}
    .parameter-learned-chip em {{
      color: var(--muted);
      font-size: 11px;
      font-style: normal;
    }}
    .parameter-climate-stack {{
      display: grid;
      gap: 12px;
    }}
    .parameter-card-note {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      line-height: 1.3;
      margin: -2px 0 2px;
    }}
    .parameter-card-heading {{
      align-items: baseline;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
    }}
    .parameter-card-heading .parameter-card-note {{
      margin: 0;
    }}
    .parameter-edit-note {{
      background: rgba(4, 16, 28, .58);
      border: 1px solid rgba(45, 58, 71, .72);
      border-radius: 7px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      line-height: 1.25;
      padding: 6px 8px;
    }}
    .parameter-edit-note a {{
      color: var(--accent);
      display: block;
      text-decoration: underline;
      text-underline-offset: 2px;
    }}
    .parameter-edit-note a:hover {{
      color: var(--text);
    }}
    .parameter-climate-grid {{
      display: grid;
      gap: 9px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .parameter-left-stack {{
      align-content: start;
      display: grid;
      gap: 12px;
    }}
    .parameter-habitat-grid {{
      gap: 9px;
    }}
    .parameter-habitat-grid.v0 {{
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .parameter-field-row,
    .parameter-text-row,
    .parameter-switch-row {{
      align-items: center;
      display: grid;
      gap: 8px;
      grid-template-columns: minmax(145px, 1fr) minmax(88px, .52fr);
      min-height: 28px;
    }}
    .parameter-field-row > span:first-child,
    .parameter-text-row > span:first-child,
    .parameter-switch-row > span:first-child {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }}
    .parameter-input-shell {{
      align-items: center;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
    }}
    .parameter-input-shell input,
    .parameters-screen .parameter-field-row input {{
      border-radius: 6px 0 0 6px;
      min-height: 28px;
      padding: 0 8px;
    }}
    .parameter-input-shell input:only-child {{
      border-radius: 6px;
    }}
    .parameter-unit {{
      align-items: center;
      background: rgba(15, 23, 42, .72);
      border: 1px solid var(--line);
      border-left: 0;
      border-radius: 0 6px 6px 0;
      color: var(--muted);
      display: inline-flex;
      font-size: 11px;
      font-weight: 800;
      justify-content: center;
      min-height: 28px;
      min-width: 38px;
      padding: 0 7px;
    }}
    .parameter-text-row {{
      align-items: start;
    }}
    .parameter-text-row textarea {{
      border-radius: 6px;
      line-height: 1.25;
      min-height: 31px;
      padding: 6px 8px;
    }}
    .parameter-switch-row {{
      grid-template-columns: minmax(145px, 1fr) auto auto;
      justify-content: start;
    }}
    .parameter-switch-row input {{
      accent-color: var(--accent);
      height: 18px;
      width: 18px;
    }}
    .parameter-switch-row em {{
      color: var(--muted);
      font-size: 11px;
      font-style: normal;
      font-weight: 800;
    }}
    .parameter-duo-grid {{
      display: grid;
      gap: 7px 10px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .parameter-duo-grid .parameter-field-row {{
      grid-template-columns: minmax(82px, 1fr) minmax(82px, .72fr);
    }}
    .parameter-score-grid {{
      display: grid;
      gap: 7px 10px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .parameter-score-grid .parameter-field-row {{
      grid-template-columns: minmax(92px, 1fr) minmax(76px, .58fr);
    }}
    .parameter-chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }}
    .parameter-affinity-chip {{
      align-items: center;
      background: rgba(3, 169, 244, .08);
      border: 1px solid rgba(3, 169, 244, .35);
      border-radius: 6px;
      color: var(--fg);
      display: inline-flex;
      flex-wrap: nowrap;
      gap: 4px 6px;
      font-size: 11px;
      font-weight: 800;
      justify-content: flex-start;
      line-height: 1.15;
      max-width: 100%;
      min-width: 0;
      padding: 4px 6px;
    }}
    .parameter-affinity-label {{
      min-width: 0;
      overflow-wrap: anywhere;
    }}
    .parameter-affinity-badges {{
      display: inline-flex;
      flex-wrap: nowrap;
      gap: 5px;
    }}
    .parameter-affinity-badge {{
      align-items: center;
      border: 1px solid rgba(148, 163, 184, .32);
      border-radius: 999px;
      color: var(--muted);
      display: inline-flex;
      font-size: 11px;
      font-weight: 800;
      line-height: 1;
      min-height: 16px;
      padding: 0 5px;
      white-space: nowrap;
    }}
    .parameter-affinity-badge.primary,
    .parameter-affinity-badge.preferred {{
      background: rgba(76, 175, 80, .12);
      border-color: rgba(76, 175, 80, .42);
      color: var(--ok);
    }}
    .parameter-affinity-badge.secondary,
    .parameter-affinity-badge.possible {{
      background: rgba(255, 193, 7, .10);
      border-color: rgba(255, 193, 7, .42);
      color: var(--warn);
    }}
    .parameter-affinity-badge.source,
    .parameter-affinity-badge.v0 {{
      background: rgba(3, 169, 244, .12);
      border-color: rgba(3, 169, 244, .46);
      color: var(--accent);
    }}
    .parameter-affinity-badge.catalog {{
      background: rgba(168, 85, 247, .12);
      border-color: rgba(168, 85, 247, .42);
      color: #c4b5fd;
    }}
    .parameter-affinity-badge.avoid,
    .parameter-affinity-badge.parked {{
      background: rgba(239, 83, 80, .10);
      border-color: rgba(239, 83, 80, .42);
      color: var(--bad);
    }}
    .parameter-affinity-chip.muted,
    .parameter-empty {{
      border-color: rgba(45, 58, 71, .7);
      color: var(--muted);
    }}
    .parameter-affinity-chip.parked {{
      background: rgba(148, 163, 184, .08);
      border-color: rgba(148, 163, 184, .38);
      color: var(--muted);
    }}
    .profile-v0-row-flags {{
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      margin-top: 5px;
    }}
    .profile-v0-row-flags span {{
      border: 1px solid rgba(148, 163, 184, .34);
      border-radius: 999px;
      color: var(--muted);
      font-size: 10px;
      font-weight: 800;
      padding: 2px 6px;
      text-transform: uppercase;
    }}
    .profile-calibration-cards {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }}
    .profile-coverage-grid {{
      display: grid;
      gap: 6px;
    }}
    .profile-recommendation-list {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .observations-filters {{
      display: grid;
      background: rgba(2, 13, 22, .25);
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      gap: 8px;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      padding: 10px;
    }}
    .observations-layout {{
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(0, 1fr) minmax(300px, .28fr);
    }}
    .observations-metrics .profile-metric .label {{
      align-items: center;
      display: flex;
      gap: 7px;
    }}
    .observations-metrics svg {{
      fill: none;
      height: 16px;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.8;
      width: 16px;
    }}
    .observations-table-card {{
      min-width: 0;
    }}
    .observations-table-shell {{
      max-height: 460px;
      overflow: auto;
    }}
    .observations-table-shell thead th {{
      background: #111a23;
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    .observations-table-shell tbody tr.observation-row {{
      cursor: pointer;
    }}
    .observations-table-shell tbody tr.observation-row:hover {{
      background: rgba(3, 169, 244, .06);
    }}
    .observations-table-shell tbody tr.observation-row.selected {{
      background: rgba(3, 169, 244, .2);
      box-shadow:
        inset 0 0 0 1px rgba(56, 189, 248, .65),
        inset 5px 0 0 var(--accent),
        0 0 0 1px rgba(3, 169, 244, .16);
      color: #f8fbff;
    }}
    .observations-table-shell tbody tr.observation-row.selected td {{
      border-top-color: rgba(56, 189, 248, .28);
      border-bottom-color: rgba(56, 189, 248, .28);
    }}
    .observations-table-shell tbody tr.observation-row.selected a {{
      color: #b9ecff;
    }}
    .observations-table-shell tbody tr.observation-row:focus-within {{
      outline: 1px solid rgba(3, 169, 244, .45);
      outline-offset: -1px;
    }}
    .observations-table-shell {{
      overflow-x: auto;
    }}
    .observations-table-shell table {{
      border-collapse: collapse;
      min-width: 840px;
      width: 100%;
    }}
    .observations-table-shell th,
    .observations-table-shell td {{
      border-bottom: 1px solid rgba(45, 58, 71, .62);
      font-size: 12px;
      padding: 8px 7px;
      text-align: left;
      white-space: nowrap;
    }}
    .observations-table-shell th {{
      color: var(--muted);
      font-weight: 800;
    }}
    .observation-badge {{
      background: rgba(148, 163, 184, .1);
      border: 1px solid rgba(148, 163, 184, .28);
      border-radius: 6px;
      display: inline-flex;
      font-size: 11px;
      font-weight: 800;
      line-height: 1;
      padding: 5px 7px;
    }}
    .observation-badge.ok {{
      border-color: rgba(76, 175, 80, .5);
      color: var(--ok);
    }}
    .observation-badge.warn {{
      border-color: rgba(255, 193, 7, .55);
      color: var(--warn);
    }}
    .observation-badge.danger {{
      border-color: rgba(255, 82, 82, .5);
      color: var(--danger);
    }}
    .gis-reconstruction-lab {{
      margin-top: 12px;
    }}
    .gis-reconstruction-lab h2 svg {{
      fill: none;
      height: 18px;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.8;
      width: 18px;
    }}
    .gis-lab-form {{
      border-top: 1px solid rgba(45, 58, 71, .62);
      margin-top: 10px;
      padding-top: 10px;
    }}
    .gis-observation-grid {{
      max-height: 104px;
      overflow: auto;
      padding-right: 4px;
    }}
    .gis-observation-toggle .catalog-chip {{
      max-width: none;
      min-height: 28px;
    }}
    .profile-action-bar.inline {{
      background: transparent;
      margin-top: 8px;
      padding-top: 8px;
    }}
    .gis-lab-results {{
      border-top: 1px solid rgba(45, 58, 71, .62);
      margin-top: 12px;
      padding-top: 10px;
    }}
    .mushroom-progress-backdrop {{
      align-items: center;
      background: rgba(0, 0, 0, .62);
      bottom: 0;
      display: flex;
      justify-content: center;
      left: 0;
      padding: 24px;
      position: fixed;
      right: 0;
      top: 0;
      z-index: 1000;
    }}
    .mushroom-progress-dialog {{
      background: #172029;
      border: 1px solid rgba(86, 111, 135, .75);
      border-radius: 8px;
      box-shadow: 0 18px 50px rgba(0, 0, 0, .42);
      color: var(--text);
      max-width: 720px;
      padding: 18px;
      width: min(720px, 100%);
    }}
    .mushroom-progress-header {{
      align-items: flex-start;
      border-bottom: 1px solid rgba(86, 111, 135, .42);
      display: flex;
      gap: 16px;
      justify-content: space-between;
      margin-bottom: 14px;
      padding-bottom: 12px;
    }}
    .mushroom-progress-header h2 {{
      margin: 0 0 4px;
    }}
    .mushroom-progress-grid {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .mushroom-progress-grid progress {{
      width: 100%;
    }}
    .mushroom-progress-grid strong {{
      display: block;
      margin-top: 4px;
    }}
    .mushroom-progress-metrics {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      margin-top: 14px;
    }}
    .mushroom-progress-metrics span {{
      border: 1px solid rgba(86, 111, 135, .42);
      border-radius: 6px;
      padding: 8px;
    }}
    .mushroom-progress-metrics em {{
      color: var(--muted);
      font-style: normal;
    }}
    .mushroom-progress-actions {{
      display: flex;
      gap: 10px;
      justify-content: flex-end;
      margin-top: 14px;
    }}
    @media (max-width: 720px) {{
      .mushroom-progress-grid,
      .mushroom-progress-metrics {{
        grid-template-columns: 1fr;
      }}
    }}
    .gis-results-table {{
      max-height: 340px;
      max-width: 100%;
      overflow-x: auto;
    }}
    .gis-results-table table {{
      min-width: 1320px;
      table-layout: fixed;
    }}
    .gis-results-table th:nth-child(1),
    .gis-results-table td:nth-child(1) {{
      width: 230px;
    }}
    .gis-results-table th:nth-child(2),
    .gis-results-table td:nth-child(2) {{
      width: 300px;
    }}
    .gis-results-table th:nth-child(3),
    .gis-results-table td:nth-child(3) {{
      width: 120px;
    }}
    .gis-results-table th:nth-child(4),
    .gis-results-table td:nth-child(4) {{
      width: 300px;
    }}
    .gis-results-table th:nth-child(5),
    .gis-results-table td:nth-child(5) {{
      width: 160px;
    }}
    .gis-results-table th:nth-child(6),
    .gis-results-table td:nth-child(6) {{
      width: 310px;
    }}
    .gis-results-table th:nth-child(7),
    .gis-results-table td:nth-child(7) {{
      width: 120px;
    }}
    .gis-results-table td {{
      overflow: hidden;
      text-overflow: ellipsis;
      vertical-align: middle;
      white-space: nowrap;
    }}
    .gis-inline {{
      align-items: center;
      display: inline-flex;
      gap: 6px;
      max-width: 100%;
      min-width: 0;
      white-space: normal;
    }}
    .gis-inline .observation-badge {{
      flex: 0 0 auto;
    }}
    .gis-inline-text,
    .gis-inline .meta {{
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      line-clamp: 2;
      line-height: 1.25;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: normal;
    }}
    .gis-v0-summary {{
      display: inline-flex;
      flex-wrap: wrap;
      gap: 4px 8px;
      line-height: 1.25;
      max-width: 100%;
      white-space: normal;
    }}
    .gis-v0-summary span {{
      color: var(--muted);
      font-size: 11px;
    }}
    .gis-v0-summary strong {{
      color: var(--fg);
    }}
    .gis-result-v0-detail {{
      border-bottom: 1px solid rgba(45, 58, 71, .48);
      margin: 8px 0 0;
      padding-bottom: 8px;
    }}
    .gis-result-detail-list {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}
    .gis-result-details {{
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      padding: 8px 10px;
    }}
    .gis-result-details summary {{
      cursor: pointer;
      font-size: 12px;
      font-weight: 800;
    }}
    .gis-result-details ul {{
      color: var(--muted);
      display: grid;
      gap: 6px;
      list-style: none;
      margin: 8px 0 0;
      padding: 0;
    }}
    .gis-result-details li {{
      font-size: 12px;
      line-height: 1.35;
    }}
    .evidence-screen {{
      display: grid;
      gap: 12px;
      grid-template-rows: auto minmax(0, 1fr);
      max-height: calc(100vh - 150px);
      min-height: min(820px, calc(100vh - 150px));
      overflow: hidden;
    }}
    .evidence-sticky-header {{
      background: linear-gradient(135deg, rgba(13, 32, 49, .97), rgba(15, 23, 42, .97));
      border: 1px solid rgba(3, 169, 244, .18);
      border-radius: 8px;
      display: grid;
      gap: 12px;
      padding: 0 0 12px;
      position: sticky;
      top: 0;
      z-index: 8;
    }}
    .evidence-sticky-header .profile-section-banner {{
      margin: 0;
    }}
    .evidence-sticky-header .evidence-view-tabs,
    .evidence-sticky-header .evidence-summary-cards,
    .evidence-sticky-header > .meta {{
      margin-left: 0;
      margin-right: 0;
    }}
    .evidence-summary-cards {{
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .evidence-grid {{
      display: grid;
      gap: 12px;
      grid-auto-rows: minmax(0, 1fr);
      grid-template-columns: repeat(2, minmax(0, 1fr));
      min-height: 0;
      overflow: hidden;
    }}
    .evidence-view-tabs {{
      align-items: center;
      border-bottom: 1px solid rgba(45, 58, 71, .72);
      display: inline-flex;
      gap: 6px;
      justify-self: start;
      margin: 0;
      padding: 0 0 8px;
    }}
    .evidence-view-tabs .mushroom-title-tab {{
      align-items: center;
      background: rgba(17, 26, 35, .88);
      border: 1px solid rgba(148, 163, 184, .24);
      border-radius: 8px;
      color: var(--muted);
      display: inline-flex;
      font-size: 13px;
      font-weight: 800;
      line-height: 1;
      min-height: 34px;
      padding: 0 14px;
      text-decoration: none;
    }}
    .evidence-view-tabs .mushroom-title-tab:hover {{
      border-color: rgba(3, 169, 244, .55);
      color: var(--fg);
    }}
    .evidence-view-tabs .mushroom-title-tab.active {{
      background: rgba(3, 169, 244, .13);
      border-color: rgba(3, 169, 244, .85);
      color: var(--accent);
    }}
    .evidence-group {{
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      min-height: 0;
      min-width: 0;
      overflow: hidden;
    }}
    .evidence-group h3 {{
      margin: 0 0 8px;
    }}
    .evidence-table-shell {{
      max-height: 100%;
      overflow: auto;
    }}
    .evidence-table-shell table {{
      border-collapse: collapse;
      min-width: 660px;
      table-layout: fixed;
      width: 100%;
    }}
    .evidence-table-shell th,
    .evidence-table-shell td {{
      border-bottom: 1px solid rgba(45, 58, 71, .62);
      font-size: 12px;
      padding: 6px 7px;
      text-align: left;
      vertical-align: middle;
    }}
    .evidence-table-shell th {{
      background: #111a23;
      border-bottom: 1px solid rgba(78, 95, 115, .9);
      color: var(--muted);
      font-weight: 800;
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    .evidence-table-shell th:nth-child(1),
    .evidence-table-shell td:nth-child(1) {{
      width: 28%;
    }}
    .evidence-table-shell th:nth-child(2),
    .evidence-table-shell td:nth-child(2) {{
      text-align: center;
      width: 58px;
    }}
    .evidence-table-shell th:nth-child(3),
    .evidence-table-shell td:nth-child(3) {{
      text-align: center;
      width: 44px;
    }}
    .evidence-table-shell th:nth-child(4),
    .evidence-table-shell td:nth-child(4) {{
      width: 160px;
    }}
    .evidence-table-shell th:nth-child(5),
    .evidence-table-shell td:nth-child(5) {{
      width: 96px;
    }}
    .evidence-table-shell th:nth-child(6),
    .evidence-table-shell td:nth-child(6) {{
      width: 152px;
    }}
    .evidence-table-shell td:first-child strong,
    .evidence-table-shell td:first-child span {{
      display: block;
    }}
    .local-evidence-table th:nth-child(1),
    .local-evidence-table td:nth-child(1) {{
      width: 220px;
    }}
    .local-evidence-table th:nth-child(2),
    .local-evidence-table td:nth-child(2) {{
      text-align: left;
      width: 88px;
    }}
    .local-evidence-table th:nth-child(3),
    .local-evidence-table td:nth-child(3) {{
      text-align: left;
      width: 140px;
    }}
    .local-evidence-table td:nth-child(3) .meta {{
      display: block;
      line-height: 1.15;
      margin-top: 2px;
      text-align: left;
    }}
    .local-evidence-table th:nth-child(4),
    .local-evidence-table td:nth-child(4) {{
      width: 124px;
    }}
    .local-evidence-table th:nth-child(5),
    .local-evidence-table td:nth-child(5) {{
      width: 88px;
    }}
    .local-evidence-table th:nth-child(6),
    .local-evidence-table td:nth-child(6) {{
      width: 128px;
    }}
    .local-evidence-table table {{
      min-width: 820px;
    }}
    .local-evidence-table td:first-child strong,
    .local-evidence-table td:first-child span {{
      overflow-wrap: anywhere;
    }}
    .local-evidence-table .evidence-status,
    .local-evidence-table .evidence-decision {{
      box-sizing: border-box;
      justify-content: center;
      line-height: 1.08;
      max-width: 100%;
      text-align: center;
      white-space: normal;
      width: 100%;
    }}
    .evidence-profile-state {{
      border: 1px solid rgba(148, 163, 184, .26);
      border-radius: 6px;
      color: var(--muted);
      display: inline-flex;
      font-size: 11px;
      font-weight: 800;
      line-height: 1;
      justify-content: center;
      max-width: 100%;
      padding: 4px 5px;
      text-align: center;
      white-space: normal;
      width: 100%;
    }}
    .evidence-profile-state.declared {{
      border-color: rgba(76, 175, 80, .42);
      color: var(--ok);
    }}
    .evidence-observation-count {{
      align-items: center;
      display: flex;
      gap: 6px;
      min-height: 24px;
    }}
    .evidence-source-breakdown {{
      display: flex;
      flex-wrap: wrap;
      gap: 3px;
      margin-top: 0;
    }}
    .evidence-source-chip {{
      align-items: center;
      border: 1px solid rgba(148, 163, 184, .22);
      border-radius: 6px;
      color: var(--muted);
      display: inline-flex;
      font-size: 11px;
      gap: 4px;
      line-height: 1;
      padding: 4px 5px;
      text-decoration: none;
    }}
    .evidence-source-chip strong {{
      color: var(--fg);
      font-size: 11px;
    }}
    .evidence-source-chip.active.source-field {{
      border-color: rgba(3, 169, 244, .45);
      color: var(--accent);
    }}
    .evidence-source-chip.active.source-gis {{
      border-color: rgba(76, 175, 80, .42);
      color: var(--ok);
    }}
    .weather-evidence {{
      display: grid;
      gap: 12px;
      grid-template-rows: auto auto auto minmax(0, 1fr);
      min-height: 0;
      overflow: hidden;
    }}
    .weather-evidence h3 {{
      align-items: center;
      display: inline-flex;
      gap: 8px;
      margin: 0;
    }}
    .weather-evidence h3 svg {{
      color: var(--accent);
      flex: 0 0 18px;
      height: 18px;
      stroke: currentColor;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 2;
      width: 18px;
    }}
    .weather-evidence .evidence-summary-cards {{
      display: grid;
      gap: 8px;
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }}
    .weather-evidence .evidence-summary-cards .profile-metric {{
      min-width: 0;
      padding: 7px 9px;
    }}
    .weather-evidence .evidence-summary-cards .label,
    .weather-evidence .evidence-summary-cards .value {{
      white-space: nowrap;
    }}
    .weather-evidence-ranges {{
      background: rgba(8, 17, 27, .42);
      border: 1px solid rgba(45, 58, 71, .65);
      border-radius: 6px;
      min-height: 0;
      overflow: auto;
    }}
    .weather-evidence-ranges table {{
      border-collapse: collapse;
      min-width: 100%;
      table-layout: fixed;
    }}
    .weather-evidence-ranges th,
    .weather-evidence-ranges td {{
      border-bottom: 1px solid rgba(45, 58, 71, .5);
      padding: 5px 8px;
      text-align: left;
      white-space: nowrap;
    }}
    .weather-evidence-ranges thead th {{
      background: rgba(15, 25, 36, .92);
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      position: sticky;
      text-transform: uppercase;
      top: 0;
      z-index: 1;
    }}
    .weather-evidence-ranges tbody th,
    .weather-evidence-ranges td {{
      color: var(--fg);
      font-size: 12px;
      line-height: 1.1;
    }}
    .weather-evidence-ranges tbody th {{
      font-weight: 900;
    }}
    .weather-evidence-ranges th:nth-child(1) {{
      width: 44%;
    }}
    .weather-evidence-ranges th:nth-child(2),
    .weather-evidence-ranges th:nth-child(3),
    .weather-evidence-ranges td:nth-child(2),
    .weather-evidence-ranges td:nth-child(3) {{
      width: 28%;
    }}
    .weather-evidence-table table {{
      table-layout: fixed;
      min-width: 1675px;
    }}
    .weather-evidence-table {{
      min-height: 0;
    }}
    .weather-evidence-table th:nth-child(n),
    .weather-evidence-table td:nth-child(n) {{
      text-align: left;
      width: auto;
    }}
    .weather-evidence-table .weather-metric-heading {{
      line-height: 1;
      text-align: center;
    }}
    .weather-evidence-table .weather-metric-heading span,
    .weather-evidence-table .weather-metric-heading em {{
      display: block;
      font-style: normal;
    }}
    .weather-evidence-table .weather-metric-heading em {{
      color: var(--muted);
      font-size: 10px;
      margin-top: 2px;
    }}
    .weather-evidence-table th:nth-child(1),
    .weather-evidence-table td:nth-child(1) {{
      width: 140px;
    }}
    .weather-evidence-table th:nth-child(2),
    .weather-evidence-table td:nth-child(2) {{
      width: 105px;
    }}
    .weather-evidence-table th:nth-child(3),
    .weather-evidence-table td:nth-child(3) {{
      width: 48px;
    }}
    .weather-evidence-table th:nth-child(n+4):nth-child(-n+9),
    .weather-evidence-table td:nth-child(n+4):nth-child(-n+9) {{
      text-align: center;
      width: 46px;
    }}
    .weather-evidence-table th:nth-child(n+10):nth-child(-n+17),
    .weather-evidence-table td:nth-child(n+10):nth-child(-n+17) {{
      text-align: center;
      white-space: nowrap;
      width: 82px;
    }}
    .weather-evidence-table th:nth-child(18),
    .weather-evidence-table td:nth-child(18) {{
      width: 250px;
    }}
    .weather-evidence-table .weather-station-detail {{
      white-space: nowrap;
    }}
    .weather-evidence-table .weather-gap-help {{
      cursor: help;
      text-decoration: underline dotted;
      text-underline-offset: 3px;
    }}
    .weather-evidence-table th:nth-child(19),
    .weather-evidence-table td:nth-child(19) {{
      width: 200px;
    }}
    .learned-model-panel {{
      display: grid;
      gap: 12px;
      min-height: 0;
      overflow: hidden;
    }}
    .learned-model-panel h3,
    .learned-model-panel h4 {{
      margin: 0;
    }}
    .learned-model-toolbar {{
      align-items: start;
      display: flex;
      gap: 12px;
      justify-content: space-between;
    }}
    .learned-model-toolbar form {{
      flex: 0 0 auto;
    }}
    .learned-model-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .learned-model-summary {{
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }}
    .learned-model-grid {{
      display: grid;
      gap: 12px;
      grid-template-rows: minmax(220px, .8fr) minmax(260px, 1fr);
      min-height: 0;
    }}
    .learned-model-grid > section {{
      display: grid;
      gap: 8px;
      min-height: 0;
    }}
    .learned-model-table {{
      max-height: none;
      min-height: 0;
    }}
    .learned-model-table table {{
      min-width: 980px;
    }}
    .learned-model-table-categorical th:nth-child(1),
    .learned-model-table-categorical td:nth-child(1) {{
      width: 32%;
    }}
    .learned-model-table-categorical th:nth-child(2),
    .learned-model-table-categorical td:nth-child(2) {{
      width: 18%;
    }}
    .learned-model-table-categorical th:nth-child(3),
    .learned-model-table-categorical td:nth-child(3),
    .learned-model-table-categorical th:nth-child(4),
    .learned-model-table-categorical td:nth-child(4),
    .learned-model-table-categorical th:nth-child(5),
    .learned-model-table-categorical td:nth-child(5) {{
      width: 12%;
    }}
    .learned-model-table.numeric table {{
      min-width: 840px;
      table-layout: fixed;
    }}
    .learned-model-table.numeric th:nth-child(1),
    .learned-model-table.numeric td:nth-child(1) {{
      width: 34%;
    }}
    .learned-model-table.numeric th:nth-child(2),
    .learned-model-table.numeric td:nth-child(2),
    .learned-model-table.numeric th:nth-child(3),
    .learned-model-table.numeric td:nth-child(3) {{
      width: 33%;
    }}
    .learned-model-table th,
    .learned-model-table td {{
      white-space: nowrap;
    }}
    .learned-numeric-count {{
      display: inline-block;
      font-weight: 800;
      min-width: 22px;
    }}
    .learned-numeric-range {{
      display: inline-block;
      font-weight: 700;
      margin-left: 10px;
      min-width: 150px;
    }}
    .evidence-status,
    .evidence-decision {{
      border: 1px solid rgba(148, 163, 184, .28);
      border-radius: 6px;
      display: inline-flex;
      font-size: 11px;
      font-weight: 800;
      line-height: 1;
      padding: 5px 6px;
      white-space: nowrap;
    }}
    .evidence-status.ok {{
      border-color: rgba(76, 175, 80, .5);
      color: var(--ok);
    }}
    .evidence-status.warn {{
      border-color: rgba(255, 193, 7, .55);
      color: var(--warn);
    }}
    .evidence-status.muted {{
      color: var(--muted);
    }}
    .evidence-action-form {{
      display: flex;
      flex-wrap: wrap;
      gap: 3px;
    }}
    .evidence-action-button {{
      background: rgba(17, 26, 35, .88);
      border: 1px solid rgba(148, 163, 184, .28);
      border-radius: 5px;
      color: var(--fg);
      cursor: pointer;
      font-size: 11px;
      font-weight: 800;
      line-height: 1;
      padding: 5px 6px;
      white-space: nowrap;
    }}
    .evidence-action-button:hover,
    .evidence-action-button.active {{
      border-color: rgba(3, 169, 244, .75);
      color: var(--accent);
    }}
    .evidence-observation-link {{
      align-items: center;
      border: 1px solid rgba(3, 169, 244, .55);
      border-radius: 999px;
      color: var(--accent);
      display: inline-flex;
      font-size: 11px;
      font-weight: 900;
      justify-content: center;
      line-height: 1;
      min-width: 28px;
      padding: 5px 8px;
      text-decoration: none;
    }}
    .evidence-observation-link:hover {{
      background: rgba(3, 169, 244, .14);
      border-color: rgba(3, 169, 244, .9);
    }}
    .modal-card.evidence-map-modal {{
      max-height: calc(100vh - 32px);
      max-width: min(1680px, calc(100vw - 32px));
      overflow: auto;
      padding: 18px;
      width: min(1680px, 100%);
    }}
    .evidence-observation-layout {{
      display: grid;
      gap: 16px;
      grid-template-columns: minmax(700px, .95fr) minmax(720px, 1.05fr);
      min-height: 0;
    }}
    .evidence-observation-layout h3 {{
      margin: 0 0 10px;
    }}
    .evidence-observation-list {{
      display: grid;
      gap: 8px;
      list-style: none;
      margin: 0;
      max-height: min(700px, calc(100vh - 245px));
      overflow: auto;
      padding: 0;
    }}
    .evidence-observation-item {{
      align-items: center;
      background: rgba(8, 17, 27, .42);
      border: 1px solid rgba(45, 58, 71, .7);
      border-radius: 8px;
      display: grid;
      gap: 8px;
      grid-template-columns: 28px 86px minmax(230px, 1fr) 150px auto auto;
      padding: 9px 10px;
    }}
    .evidence-observation-item.selected {{
      background: rgba(3, 169, 244, .13);
      border-color: rgba(3, 169, 244, .78);
      box-shadow: inset 3px 0 0 rgba(3, 169, 244, .95);
    }}
    .evidence-observation-item.selected .evidence-observation-index {{
      background: rgba(3, 169, 244, .28);
      border-color: rgba(3, 169, 244, .95);
      color: #e8f7ff;
    }}
    .evidence-observation-date {{
      font-size: 13px;
      line-height: 1;
      white-space: nowrap;
    }}
    .evidence-observation-main {{
      min-width: 0;
    }}
    .evidence-observation-main strong,
    .evidence-observation-main .meta {{
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .evidence-observation-main .meta {{
      margin-left: 0;
    }}
    .evidence-observation-coords {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }}
    .evidence-observation-index {{
      align-items: center;
      background: rgba(3, 169, 244, .14);
      border: 1px solid rgba(3, 169, 244, .45);
      border-radius: 999px;
      color: var(--accent);
      display: inline-flex;
      font-size: 12px;
      font-weight: 900;
      height: 28px;
      justify-content: center;
      width: 28px;
    }}
    .evidence-map-viewport {{
      background: radial-gradient(circle at 22% 25%, rgba(3, 169, 244, .1), transparent 35%), #08111b;
      border: 1px solid rgba(45, 58, 71, .78);
      border-radius: 8px;
      min-height: min(700px, calc(100vh - 245px));
      overflow: hidden;
      position: relative;
    }}
    .evidence-google-map {{
      border: 0;
      display: block;
      height: min(700px, calc(100vh - 245px));
      min-height: 560px;
      width: 100%;
    }}
    .evidence-map-toolbar {{
      align-items: center;
      background: rgba(8, 17, 27, .86);
      border: 1px solid rgba(45, 58, 71, .75);
      border-radius: 8px;
      display: flex;
      gap: 10px;
      justify-content: space-between;
      left: 10px;
      max-width: calc(100% - 20px);
      padding: 6px 8px;
      position: absolute;
      right: 10px;
      top: 10px;
    }}
    .evidence-map-toolbar span {{
      color: var(--fg);
      font-size: 12px;
      font-weight: 900;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .evidence-map-select-button {{
      background: rgba(17, 26, 35, .88);
      border: 1px solid rgba(3, 169, 244, .45);
      border-radius: 6px;
      color: var(--accent);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 900;
      line-height: 1;
      min-height: 30px;
      padding: 7px 9px;
      text-decoration: none;
      white-space: nowrap;
    }}
    .evidence-map-select-button:hover {{
      background: rgba(3, 169, 244, .14);
      border-color: rgba(3, 169, 244, .85);
    }}
    .evidence-map-svg {{
      display: block;
      height: 440px;
      width: 100%;
    }}
    .evidence-map-svg rect {{
      fill: rgba(15, 23, 42, .68);
      stroke: rgba(148, 163, 184, .22);
      stroke-width: .8;
    }}
    .evidence-map-svg path {{
      fill: none;
      stroke: rgba(148, 163, 184, .25);
      stroke-linecap: round;
      stroke-width: .8;
    }}
    .evidence-map-point circle {{
      fill: var(--accent);
      stroke: rgba(232, 238, 242, .95);
      stroke-width: .8;
    }}
    .evidence-map-point text {{
      fill: var(--fg);
      font-size: 4px;
      font-weight: 900;
      paint-order: stroke;
      stroke: #08111b;
      stroke-width: .8;
      text-anchor: middle;
    }}
    .evidence-map-controls {{
      display: flex;
      gap: 6px;
      position: absolute;
      right: 10px;
      top: 10px;
    }}
    .evidence-map-controls button {{
      background: rgba(17, 26, 35, .94);
      border: 1px solid rgba(148, 163, 184, .35);
      border-radius: 6px;
      color: var(--fg);
      cursor: pointer;
      font-size: 12px;
      font-weight: 900;
      min-height: 30px;
      min-width: 34px;
    }}
    .evidence-map-controls button:hover {{
      border-color: rgba(3, 169, 244, .75);
      color: var(--accent);
    }}
    .evidence-map-empty {{
      align-items: center;
      color: var(--muted);
      display: flex;
      font-size: 13px;
      font-weight: 800;
      justify-content: center;
      min-height: 440px;
      text-align: center;
    }}
    .gis-mapping-page {{
      display: grid;
      gap: 12px;
    }}
    .gis-mapping-head {{
      margin-bottom: 0;
      padding-bottom: 12px;
    }}
    .gis-mapping-toolbar {{
      border-bottom: 1px solid rgba(45, 58, 71, .72);
      margin-bottom: 0;
      padding-bottom: 10px;
    }}
    .gis-mapping-toolbar .gis-mapping-json-link {{
      margin-left: auto;
    }}
    .gis-mapping-search {{
      flex: 1 1 420px;
      max-width: none;
      min-width: min(420px, 100%);
    }}
    .gis-mapping-search input {{
      min-height: 38px;
      width: 100%;
    }}
    .gis-mapping-metrics {{
      display: grid;
      gap: 6px;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      margin-bottom: 8px;
    }}
    .gis-mapping-metric {{
      align-items: center;
      background: linear-gradient(135deg, rgba(10, 24, 38, .98), rgba(17, 34, 51, .74));
      border: 1px solid rgba(45, 58, 71, .82);
      color: inherit;
      display: flex;
      gap: 8px;
      min-height: 58px;
      padding: 8px;
      text-decoration: none;
    }}
    a.gis-mapping-metric {{
      cursor: pointer;
    }}
    a.gis-mapping-metric:hover,
    .gis-mapping-metric.active {{
      background: linear-gradient(135deg, rgba(3, 169, 244, .18), rgba(17, 34, 51, .82));
      border-color: rgba(3, 169, 244, .72);
    }}
    .gis-mapping-metric-icon {{
      background: rgba(3, 169, 244, .12);
      border: 1px solid rgba(3, 169, 244, .32);
      border-radius: 8px;
      flex: 0 0 28px;
      height: 28px;
      position: relative;
      width: 28px;
    }}
    .gis-mapping-metric-icon::after {{
      color: var(--accent);
      font-size: 16px;
      font-weight: 900;
      left: 50%;
      position: absolute;
      top: 50%;
      transform: translate(-50%, -50%);
    }}
    .gis-mapping-metric-icon.list::after {{ content: "#"; }}
    .gis-mapping-metric-icon.ok::after {{ content: "OK"; font-size: 11px; }}
    .gis-mapping-metric-icon.pending::after {{ content: "!"; }}
    .gis-mapping-metric-icon.source::after {{ content: "S"; }}
    .gis-mapping-metric-icon.field::after {{ content: "F"; }}
    .gis-mapping-metric-icon.check::after {{ content: "V"; }}
    .gis-mapping-metric-body {{
      display: grid;
      gap: 2px;
      min-width: 0;
    }}
    .gis-mapping-metric .label {{
      color: var(--muted);
      font-size: 11px;
      line-height: 1.15;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .gis-mapping-metric .value {{
      font-size: 16px;
      font-weight: 900;
      line-height: 1.1;
      margin: 0;
    }}
    .gis-mapping-metric .meta {{
      color: var(--muted);
      font-size: 10px;
      line-height: 1.15;
    }}
    .gis-mapping-filter-panel {{
      background: rgba(8, 18, 30, .58);
      border: 1px solid rgba(45, 58, 71, .7);
      border-radius: 8px;
      display: grid;
      gap: 7px;
      margin-bottom: 8px;
      padding: 8px;
    }}
    .gis-mapping-filter-row {{
      align-items: center;
      display: grid;
      gap: 8px;
      grid-template-columns: 70px minmax(0, 1fr);
    }}
    .gis-mapping-filter-label {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .gis-mapping-filter-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 0;
    }}
    .gis-mapping-filter-grid .catalog-chip {{
      align-items: center;
      display: flex;
      gap: 6px;
      min-height: 30px;
      padding: 5px 9px;
    }}
    .gis-mapping-filter-grid .catalog-chip strong {{
      font-size: 12px;
      white-space: nowrap;
    }}
    .gis-mapping-filter-grid .catalog-chip span {{
      font-size: 11px;
      white-space: nowrap;
    }}
    .gis-mapping-workbench {{
      gap: 14px;
      grid-template-columns: minmax(720px, 1fr) minmax(480px, .48fr);
    }}
    .gis-mapping-list {{
      min-width: 0;
    }}
    .gis-mapping-list-card {{
      background: rgba(8, 18, 30, .42);
      border: 1px solid rgba(45, 58, 71, .72);
      border-radius: 8px;
      overflow: hidden;
    }}
    .gis-mapping-table-shell {{
      border: 0;
      max-height: min(720px, calc(100vh - 320px));
      min-height: 360px;
    }}
    .gis-mapping-table-shell table {{
      min-width: 980px;
      table-layout: fixed;
    }}
    .gis-mapping-table-shell th,
    .gis-mapping-table-shell td {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .gis-mapping-table-shell tbody tr.catalog-row {{
      cursor: pointer;
    }}
    .gis-mapping-table-shell tbody tr.catalog-row:hover td {{
      background: rgba(3, 169, 244, .06);
    }}
    .gis-mapping-table-shell tbody tr.catalog-row.selected td {{
      background: rgba(3, 169, 244, .16);
      border-bottom-color: rgba(3, 169, 244, .38);
      border-top: 1px solid rgba(3, 169, 244, .38);
    }}
    .gis-mapping-table-shell tbody tr.catalog-row.selected td:first-child {{
      border-left: 3px solid var(--accent);
      color: var(--accent);
    }}
    .gis-mapping-table-shell tbody tr.catalog-row.selected td:last-child {{
      border-right: 1px solid rgba(3, 169, 244, .38);
    }}
    .gis-mapping-table-shell th:nth-child(1),
    .gis-mapping-table-shell td:nth-child(1) {{
      width: 110px;
    }}
    .gis-mapping-table-shell th:nth-child(2),
    .gis-mapping-table-shell td:nth-child(2) {{
      width: 135px;
    }}
    .gis-mapping-table-shell th:nth-child(3),
    .gis-mapping-table-shell td:nth-child(3) {{
      width: 38%;
    }}
    .gis-mapping-table-shell th:nth-child(4),
    .gis-mapping-table-shell td:nth-child(4) {{
      width: 28%;
    }}
    .gis-mapping-table-shell th:nth-child(5),
    .gis-mapping-table-shell td:nth-child(5) {{
      width: 120px;
    }}
    .gis-table-source {{
      color: var(--fg);
      font-weight: 800;
    }}
    .gis-table-raw,
    .gis-table-targets {{
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .gis-mapping-detail {{
      background: linear-gradient(180deg, rgba(15, 30, 45, .96), rgba(11, 22, 34, .96));
      border: 1px solid rgba(45, 58, 71, .86);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      max-height: calc(100vh - 178px);
      padding: 12px;
    }}
    .gis-mapping-detail form {{
      display: flex;
      flex: 1 1 auto;
      flex-direction: column;
      min-height: 0;
    }}
    .gis-mapping-detail-fixed {{
      flex: 0 0 auto;
    }}
    .gis-mapping-detail-head {{
      align-items: start;
      border-bottom: 1px solid rgba(45, 58, 71, .72);
      display: flex;
      gap: 10px;
      justify-content: space-between;
      margin-bottom: 10px;
      padding-bottom: 10px;
    }}
    .gis-mapping-detail-actions {{
      align-items: flex-end;
      display: flex;
      flex: 0 0 auto;
      flex-direction: column;
      gap: 8px;
    }}
    .gis-mapping-save-button {{
      min-height: 34px;
      padding: 7px 12px;
      white-space: nowrap;
    }}
    .gis-mapping-detail-head h2 {{
      font-size: 16px;
      line-height: 1.2;
      margin: 0 0 4px;
      word-break: break-word;
    }}
    .gis-mapping-detail-head .meta {{
      line-height: 1.25;
      max-height: 44px;
      overflow: auto;
    }}
    .gis-mapping-detail .compact-labels {{
      gap: 6px 8px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .gis-mapping-detail .compact-labels label {{
      min-width: 0;
    }}
    .gis-mapping-detail .compact-labels .span-full {{
      grid-column: 1 / -1;
    }}
    .gis-mapping-detail textarea {{
      min-height: 52px;
    }}
    .gis-mapping-context {{
      background: rgba(3, 169, 244, .08);
      border: 1px solid rgba(3, 169, 244, .28);
      border-radius: 8px;
      display: grid;
      gap: 5px;
      margin-top: 8px;
      padding: 8px;
    }}
    .gis-mapping-context strong {{
      color: var(--accent);
      font-size: 12px;
    }}
    .gis-mapping-context span {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.3;
    }}
    .gis-mapping-context code {{
      color: var(--fg);
      font-family: inherit;
      font-weight: 800;
    }}
    .gis-mapping-detail-scroll {{
      display: grid;
      flex: 1 1 auto;
      gap: 8px;
      margin-top: 10px;
      min-height: 0;
      overflow: auto;
      padding-right: 4px;
    }}
    .gis-mapping-targets {{
      display: grid;
      gap: 8px;
    }}
    .gis-mapping-target-section {{
      background: rgba(8, 18, 30, .42);
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      padding: 8px;
    }}
    .gis-mapping-target-section summary {{
      align-items: center;
      background: rgba(8, 18, 30, .46);
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 6px;
      color: var(--fg);
      cursor: pointer;
      display: flex;
      font-size: 13px;
      font-weight: 900;
      justify-content: space-between;
      line-height: 1.2;
      margin: 0 0 8px;
      min-height: 32px;
      padding: 7px 8px;
    }}
    .gis-mapping-target-section summary::marker {{
      color: var(--muted);
    }}
    .gis-mapping-target-section summary:hover {{
      border-color: rgba(3, 169, 244, .38);
      color: var(--accent);
    }}
    .gis-mapping-target-grid {{
      display: grid;
      gap: 6px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      padding-right: 4px;
    }}
    .gis-mapping-target-grid .catalog-chip {{
      min-height: 36px;
      padding: 6px 7px;
    }}
    .gis-mapping-target-grid .catalog-chip span,
    .gis-mapping-target-grid .catalog-chip strong {{
      line-height: 1.15;
    }}
    .gis-mapping-quality-grid {{
      display: grid;
      gap: 7px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin-top: 8px;
    }}
    .gis-mapping-quality-card {{
      background: rgba(8, 18, 30, .46);
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      display: grid;
      gap: 5px;
      padding: 8px;
    }}
    .gis-mapping-quality-card strong {{
      font-size: 13px;
    }}
    .gis-mapping-quality-card span {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.25;
    }}
    .modal-layer.validation-modal-open {{
      display: flex;
    }}
    .modal-card.validation-error-card {{
      border-color: rgba(255, 82, 82, .55);
      max-width: 720px;
    }}
    .observation-detail-shell {{
      align-self: start;
    }}
    .observation-photo-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 12px;
    }}
    .observation-photo-link {{
      border: 1px solid rgba(45, 58, 71, .82);
      border-radius: 6px;
      display: inline-flex;
      height: 92px;
      overflow: hidden;
      width: 122px;
    }}
    .observation-photo-link img {{
      height: 100%;
      object-fit: cover;
      width: 100%;
    }}
    .observation-detail-summary {{
      align-items: stretch;
      display: grid;
      gap: 10px;
      grid-template-columns: auto minmax(0, 1fr);
      margin: 0 0 10px;
    }}
    .observation-detail-photo-strip {{
      margin: 0;
    }}
    .observation-detail-photo-strip .observation-photo-link,
    .observation-detail-photo-placeholder {{
      height: 92px;
      width: 122px;
    }}
    .observation-detail-photo-placeholder {{
      border: 1px dashed rgba(45, 58, 71, .62);
      border-radius: 6px;
    }}
    .observation-detail-summary-fields {{
      align-content: center;
      border-bottom: 1px solid rgba(45, 58, 71, .62);
      display: grid;
      gap: 4px;
      font-size: 13px;
      min-width: 0;
      padding-bottom: 6px;
    }}
    .observation-detail-summary-fields div {{
      line-height: 1.15;
      min-width: 0;
    }}
    .observation-detail-summary-fields span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .observation-detail-summary-fields strong {{
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    .observation-detail-summary-fields a {{
      font-size: 13px;
    }}
    .observation-detail-coordinate {{
      overflow-wrap: anywhere;
    }}
    .observation-map-photo-strip {{
      flex: 1;
      justify-content: center;
      margin: 0;
      min-width: 0;
    }}
    .observation-map-photo-strip .observation-photo-link {{
      height: 82px;
      width: 110px;
    }}
    .observation-photo-modal {{
      grid-template-rows: auto minmax(120px, 28vh) minmax(0, 1fr);
      height: calc(100vh - 48px);
      max-width: calc(100vw - 48px);
      width: calc(100vw - 48px);
    }}
    .observation-photo-exif {{
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      min-height: 0;
      overflow: auto;
    }}
    .observation-photo-exif table {{
      width: 100%;
    }}
    .observation-photo-exif th,
    .observation-photo-exif td {{
      border-bottom: 1px solid rgba(45, 58, 71, .42);
      padding: 6px 8px;
      text-align: left;
      vertical-align: top;
    }}
    .observation-photo-exif th {{
      color: var(--muted);
      width: 190px;
    }}
    .observation-photo-stage {{
      align-items: center;
      background: rgba(0, 0, 0, .28);
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      display: flex;
      justify-content: center;
      min-height: 0;
      overflow: hidden;
    }}
    .observation-photo-stage img {{
      max-height: 100%;
      max-width: 100%;
      object-fit: contain;
    }}
    .observation-raw-exif-modal {{
      grid-template-rows: auto minmax(0, 1fr);
      height: calc(100vh - 48px);
      max-width: calc(100vw - 48px);
      width: calc(100vw - 48px);
    }}
    .observation-raw-exif-modal pre {{
      background: rgba(0, 0, 0, .24);
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      color: var(--fg);
      margin: 0;
      min-height: 0;
      overflow: auto;
      padding: 12px;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .observation-exif-preview-modal[hidden] {{
      display: none;
    }}
    .observation-exif-preview-modal {{
      align-items: center;
      background: rgba(0, 0, 0, .72);
      bottom: 0;
      display: flex;
      justify-content: center;
      left: 0;
      padding: 12px;
      position: fixed;
      right: 0;
      top: 0;
      z-index: 1500;
    }}
    .observation-exif-preview-dialog {{
      background: var(--card);
      border: 1px solid rgba(45, 58, 71, .9);
      border-radius: 8px;
      box-shadow: 0 18px 60px rgba(0, 0, 0, .46);
      display: grid;
      gap: 12px;
      grid-template-rows: auto auto minmax(0, 1fr) auto;
      height: calc(100vh - 24px);
      max-width: calc(100vw - 24px);
      padding: 14px;
      width: min(1500px, calc(100vw - 24px));
    }}
    .observation-exif-preview-dialog .modal-head {{
      padding-bottom: 10px;
    }}
    .observation-exif-preview-close {{
      align-items: center;
      border-radius: 7px;
      display: inline-flex;
      font-size: 20px;
      height: 38px;
      justify-content: center;
      line-height: 1;
      padding: 0;
      width: 38px;
    }}
    .observation-exif-preview-content {{
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(280px, 340px) minmax(360px, 1fr) minmax(270px, 360px);
      grid-template-rows: minmax(190px, .7fr) minmax(330px, 1.3fr);
      min-height: 0;
    }}
    .observation-exif-preview-grid {{
      align-content: start;
      display: grid;
      gap: 8px;
      grid-row: 1 / -1;
      min-height: 0;
      overflow: auto;
    }}
    .observation-exif-preview-card {{
      align-items: center;
      background: rgba(8, 18, 30, .34);
      border: 1px solid rgba(45, 58, 71, .82);
      border-radius: 7px;
      color: var(--fg);
      cursor: pointer;
      display: grid;
      gap: 9px;
      grid-template-columns: 72px minmax(0, 1fr);
      min-height: 76px;
      padding: 7px;
      text-align: left;
    }}
    .observation-exif-preview-card.selected {{
      border-color: rgba(3, 169, 244, .78);
      box-shadow: 0 0 0 1px rgba(3, 169, 244, .35);
    }}
    .observation-exif-preview-card.error {{
      border-color: rgba(255, 180, 0, .42);
    }}
    .observation-exif-preview-card img {{
      border-radius: 5px;
      height: 62px;
      object-fit: cover;
      width: 72px;
    }}
    .observation-exif-preview-photo {{
      align-items: center;
      background: rgba(0, 0, 0, .24);
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      display: flex;
      justify-content: center;
      min-height: 0;
      overflow: hidden;
    }}
    .observation-exif-preview-photo img {{
      max-height: 100%;
      max-width: 100%;
      object-fit: contain;
    }}
    .observation-exif-preview-data {{
      align-content: start;
      background: rgba(8, 18, 30, .3);
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      display: grid;
      min-height: 0;
      overflow: auto;
      padding: 8px;
    }}
    .observation-exif-preview-data h3 {{
      font-size: 13px;
      margin: 0 0 8px;
    }}
    .observation-exif-preview-data-rows {{
      display: grid;
      min-height: 0;
    }}
    .observation-exif-preview-data-row {{
      align-items: center;
      border-top: 1px solid rgba(45, 58, 71, .42);
      display: grid;
      gap: 10px;
      grid-template-columns: 20px 92px minmax(0, 1fr);
      min-height: 32px;
      padding: 6px 0;
    }}
    .observation-exif-preview-data-row .exif-icon {{
      color: var(--muted);
      font-size: 14px;
      text-align: center;
    }}
    .observation-exif-preview-data-row span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .observation-exif-preview-data-row strong {{
      font-size: 12px;
      overflow-wrap: anywhere;
      text-align: right;
    }}
    .observation-exif-preview-body {{
      display: grid;
      gap: 3px;
      min-width: 0;
    }}
    .observation-exif-preview-body strong,
    .observation-exif-preview-body span {{
      overflow-wrap: anywhere;
    }}
    .observation-exif-preview-map {{
      border: 1px solid rgba(45, 58, 71, .62);
      border-radius: 8px;
      grid-column: 2 / -1;
      min-height: 0;
      overflow: hidden;
    }}
    .observation-exif-preview-map iframe {{
      border: 0;
      height: 100%;
      width: 100%;
    }}
    .observation-notes {{
      border-top: 1px solid rgba(45, 58, 71, .62);
      display: grid;
      gap: 6px;
      padding-top: 10px;
    }}
    .observation-notes p {{
      color: var(--muted);
      font-size: 12px;
      margin: 0;
    }}
    .observation-form {{
      gap: 12px;
    }}
    .modal-card.observation-form {{
      gap: 10px;
      max-height: calc(100vh - 36px);
      max-width: min(1480px, calc(100vw - 48px));
      padding: 14px;
      width: min(1480px, calc(100vw - 48px));
    }}
    .observation-form .modal-head {{
      padding-bottom: 10px;
    }}
    .observation-form .admin-field label,
    .observation-form .catalog-toggle-field .field-label {{
      color: var(--fg);
      font-weight: 800;
    }}
    .observation-form .admin-field .meta {{
      color: var(--muted);
      font-weight: 700;
    }}
    .observation-form input,
    .observation-form select {{
      min-height: 30px;
      padding: 0 8px;
    }}
    .observation-form .admin-field label,
    .observation-form .catalog-toggle-field .field-label {{
      margin-bottom: 3px;
    }}
    .observation-field-groups {{
      align-items: stretch;
      display: grid;
      gap: 10px;
      grid-template-columns: minmax(250px, .85fr) minmax(420px, 1.35fr) minmax(260px, .86fr) minmax(350px, 1.05fr);
    }}
    .observation-field-group {{
      align-content: start;
      background: rgba(2, 13, 22, .22);
      border: 1px solid rgba(45, 58, 71, .68);
      border-radius: 8px;
      display: grid;
      gap: 7px;
      padding: 8px;
    }}
    .observation-field-group h3 {{
      color: var(--fg);
      font-size: 12px;
      font-weight: 800;
      line-height: 1.1;
      margin: 0;
    }}
    .observation-group-grid {{
      display: grid;
      gap: 7px 8px;
    }}
    .observation-group-grid.record {{
      grid-template-columns: minmax(0, 1fr) 92px;
    }}
    .observation-group-grid.record .wide {{
      grid-column: 1 / -1;
    }}
    .observation-group-grid.location {{
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 92px;
    }}
    .observation-group-grid.location .location-input,
    .observation-group-grid.location .admin-field:last-child {{
      grid-column: 1 / -1;
    }}
    .observation-group-grid.validation {{
      grid-template-columns: minmax(0, 1fr);
    }}
    .observation-group-grid.source {{
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }}
    .observation-group-grid.source .source-url {{
      grid-column: 1 / -1;
    }}
    .observation-context-grid {{
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .observation-context-grid .catalog-toggle-field {{
      align-content: start;
      min-width: 0;
    }}
    .observation-context-grid .catalog-toggle-grid {{
      align-content: start;
      max-height: 156px;
      overflow: auto;
      padding-right: 2px;
    }}
    .table-sort-link {{
      color: inherit;
      text-decoration: none;
    }}
    .table-sort-link:hover {{
      color: var(--accent);
    }}
    .button-link.compact {{
      min-height: 28px;
      padding: 5px 8px;
    }}
    .observation-map-link {{
      color: var(--text);
      font-weight: 800;
      text-decoration: underline;
      text-decoration-color: rgba(0, 174, 255, .55);
      text-underline-offset: 3px;
    }}
    .observation-map-link:hover {{
      color: var(--accent);
    }}
    .observation-row-actions {{
      align-items: center;
      display: flex;
      gap: 6px;
      height: 100%;
      white-space: nowrap;
    }}
    .observation-row-actions form {{
      margin: 0;
    }}
    .observation-row-actions button.compact {{
      font-size: 12px;
      min-height: 28px;
      padding: 5px 8px;
    }}
    .archived-observations-list {{
      display: grid;
      gap: 8px;
      max-height: 320px;
      overflow: auto;
      padding-top: 10px;
    }}
    .observations-main-actions {{
      border-top: 1px solid var(--line);
      margin-top: -2px;
      padding-top: 12px;
    }}
    .gis-reconstruction-lab summary {{
      cursor: pointer;
      list-style-position: inside;
    }}
    .gis-reconstruction-lab summary strong {{
      align-items: center;
      display: inline-flex;
      gap: 8px;
    }}
    .gis-reconstruction-lab .collapsible-section-body {{
      display: grid;
      gap: 12px;
      padding-top: 12px;
    }}
    .mushroom-section-tabs {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 24px;
      justify-content: flex-end;
      margin: 0;
      padding: 0;
    }}
    .mushroom-section-tabs a,
    .mushroom-section-tabs span {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      padding: 7px 0;
      text-decoration: none;
    }}
    .mushroom-section-tabs .active {{
      border-bottom: 2px solid var(--accent);
      color: var(--accent);
    }}
    .button-link.primary-link {{
      background: linear-gradient(180deg, #0277d4, #015ca7);
      border-color: rgba(3, 169, 244, .78);
      color: #fff;
    }}
    .button-link.secondary-link {{
      background: rgba(15, 23, 42, .42);
      border-color: var(--line);
    }}
    .button-link.danger-link {{
      background: rgba(40, 18, 22, .44);
      border-color: rgba(255, 107, 107, .55);
      color: var(--danger);
    }}
    .modal-layer {{
      align-items: center;
      display: none;
      inset: 0;
      justify-content: center;
      padding: 24px;
      position: fixed;
      z-index: 1000;
    }}
    .modal-layer:target {{
      display: flex;
    }}
    .modal-backdrop {{
      background: rgba(0, 0, 0, .64);
      inset: 0;
      position: absolute;
      z-index: 0;
    }}
    .modal-card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      box-shadow: 0 24px 80px rgba(0, 0, 0, .45);
      display: grid;
      gap: 14px;
      max-height: calc(100vh - 48px);
      max-width: 760px;
      overflow: auto;
      padding: 16px;
      position: relative;
      width: min(760px, 100%);
      z-index: 1;
    }}
    .modal-card-wide {{
      max-width: 980px;
      width: min(980px, 100%);
    }}
    .modal-header {{
      align-items: start;
      display: flex;
      gap: 14px;
      justify-content: space-between;
    }}
    .modal-header > div:first-child {{
      min-width: 0;
    }}
    .modal-header-actions {{
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }}
    .modal-head {{
      align-items: start;
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 14px;
      justify-content: space-between;
      padding-bottom: 12px;
    }}
    .modal-head h2 {{
      margin: 0 0 4px;
    }}
    .modal-head p {{
      margin: 0;
    }}
    .modal-actions {{
      align-items: center;
      display: flex;
      gap: 10px;
      justify-content: flex-end;
      margin-top: 12px;
    }}
    .mushroom-title-tabs {{
      align-items: end;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 8px;
      grid-template-areas:
        "title actions"
        "title tabs";
      grid-template-columns: minmax(300px, 1fr) auto;
      margin: 0 0 14px;
      padding: 0 0 10px;
    }}
    .mushroom-title-copy {{
      grid-area: title;
    }}
    .mushroom-title-row {{
      align-items: center;
      display: flex;
      gap: 14px;
      grid-area: actions;
      justify-content: flex-end;
    }}
    .mushroom-tabs-row {{
      align-items: end;
      display: flex;
      gap: 14px;
      grid-area: tabs;
      justify-content: flex-end;
    }}
    .mushroom-title-tabs h1 {{
      margin-bottom: 4px;
    }}
    .mushroom-title-tabs p {{
      margin: 0;
    }}
    .mushroom-title-status {{
      white-space: nowrap;
    }}
    .mushroom-model-stale-form {{
      margin: 0;
    }}
    .mushroom-model-stale-button {{
      align-items: center;
      background: rgba(127, 29, 29, .88);
      border: 1px solid rgba(255, 107, 107, .95);
      border-radius: 8px;
      color: #fff;
      cursor: pointer;
      display: inline-flex;
      font-size: 13px;
      font-weight: 900;
      gap: 8px;
      line-height: 1;
      min-height: 32px;
      padding: 5px 10px;
      text-align: center;
      white-space: nowrap;
    }}
    .mushroom-model-stale-button span {{
      font-size: 10px;
      font-weight: 800;
      opacity: .86;
    }}
    .mushroom-cross-validation {{
      margin-top: 18px;
    }}
    .mushroom-cross-validation summary {{
      cursor: pointer;
    }}
    @media (max-width: 1320px) {{
      .permissions-grid {{
        grid-template-columns: repeat(3, minmax(180px, 1fr));
      }}
      .profile-metrics {{
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }}
      .gis-mapping-metrics {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}
      .gis-mapping-workbench {{
        grid-template-columns: minmax(620px, 1fr) minmax(420px, .5fr);
      }}
      .profile-overview-card,
      .profile-overview-card.wide {{
        grid-column: span 6;
      }}
      .parameter-habitat-grid.v0 {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .parameter-comparison-layout {{
        grid-template-columns: 1fr;
      }}
      .profile-metadata-strip {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}
      .observation-field-groups {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .observation-context-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 980px) {{
      .catalog-layout {{
        grid-template-columns: 1fr;
      }}
      .catalog-detail {{
        position: static;
      }}
      .gis-mapping-workbench {{
        grid-template-columns: 1fr;
      }}
      .gis-mapping-detail {{
        max-height: none;
        position: static;
      }}
      .profile-layout {{
        grid-template-columns: 1fr;
      }}
      .profile-list {{
        max-height: none;
        position: static;
      }}
      .profile-grid,
      .profile-grid.three,
      .profile-grid.four,
      .profile-phenology-layout,
      .profile-month-grid,
      .profile-delay-grid,
      .profile-topography-layout,
      .profile-altitude-grid,
      .profile-calibration-summary,
      .profile-calibration-cards,
      .profile-calibration-grid,
      .profile-metrics,
      .profile-parameters-grid,
      .parameter-left-stack,
      .parameter-climate-grid,
      .parameter-duo-grid,
      .parameter-score-grid,
      .profile-section-card-grid.two,
      .profile-weather-grid,
      .profile-metadata-strip,
      .profile-affinity-row,
      .profile-section-head,
      .profile-lifecycle-grid,
      .evidence-grid,
      .weather-evidence-ranges,
      .archived-species-row,
      .observations-filters,
      .observations-layout,
      .profile-recommendation-list,
      .mushroom-title-tabs {{
        grid-template-columns: 1fr;
      }}
      .observation-context-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .observation-field-groups {{
        grid-template-columns: 1fr;
      }}
      .evidence-screen {{
        max-height: none;
        min-height: 0;
        overflow: visible;
      }}
      .evidence-grid {{
        grid-auto-rows: auto;
        overflow: visible;
      }}
      .evidence-group,
      .weather-evidence {{
        overflow: visible;
      }}
      .weather-evidence .evidence-summary-cards {{
        grid-template-columns: 1fr;
      }}
      .learned-model-summary {{
        grid-template-columns: 1fr;
      }}
      .learned-model-toolbar {{
        align-items: stretch;
        flex-direction: column;
      }}
      .learned-model-actions {{
        justify-content: flex-start;
      }}
      .learned-model-grid {{
        grid-template-rows: auto;
      }}
      .evidence-table-shell {{
        max-height: min(520px, 70vh);
      }}
      .profile-overview-card,
      .profile-overview-card.wide,
      .profile-overview-card.full {{
        grid-column: 1 / -1;
      }}
      .profile-hero {{
        display: grid;
      }}
      .profile-hero-chips {{
        justify-content: start;
      }}
      .profile-hero-side {{
        align-items: stretch;
        min-width: 0;
        width: 100%;
      }}
      .profile-header-selector {{
        justify-content: start;
      }}
      .profile-header-selector select {{
        max-width: 100%;
        min-width: 0;
        width: 100%;
      }}
      .profile-section-banner {{
        align-items: start;
        flex-direction: column;
      }}
      .parameters-screen .profile-section-banner.compact {{
        grid-template-columns: 1fr;
      }}
      .parameters-screen .profile-section-banner.compact .profile-hero-chips {{
        flex-wrap: wrap;
        justify-content: flex-start;
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
      .gis-mapping-metrics,
      .gis-mapping-detail .compact-labels,
      .gis-mapping-quality-grid {{
        grid-template-columns: 1fr;
      }}
      .gis-mapping-toolbar .gis-mapping-json-link {{
        margin-left: 0;
      }}
      .gis-mapping-filter-row {{
        align-items: stretch;
        grid-template-columns: 1fr;
      }}
      .gis-mapping-target-grid {{
        grid-template-columns: 1fr;
      }}
      .modal-layer {{
        padding: 10px;
      }}
      .modal-card.observation-form {{
        max-height: calc(100vh - 20px);
        max-width: calc(100vw - 20px);
        width: calc(100vw - 20px);
      }}
      .observation-context-grid {{
        grid-template-columns: 1fr;
      }}
      .observation-group-grid.record,
      .observation-group-grid.location,
      .observation-group-grid.source {{
        grid-template-columns: 1fr;
      }}
      .observation-group-grid.location .location-input,
      .observation-group-grid.location .admin-field:last-child,
      .observation-group-grid.source .source-url {{
        grid-column: auto;
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
  <main{main_class}>
    {body}
  </main>
  <div id="observation-exif-preview-modal" class="observation-exif-preview-modal" hidden>
    <section class="observation-exif-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="observation-exif-preview-title">
      <header class="modal-head">
        <div>
          <h2 id="observation-exif-preview-title">Vista previa EXIF</h2>
          <p>Revisa la imagen, la fecha, las coordenadas y la altitud antes de aplicar los datos al formulario.</p>
        </div>
        <button class="secondary observation-exif-preview-close" type="button" data-observation-exif-preview-cancel aria-label="Cancelar">×</button>
      </header>
      <div class="observation-exif-preview-status meta"></div>
      <div class="observation-exif-preview-content">
        <div class="observation-exif-preview-grid"></div>
        <div class="observation-exif-preview-photo"><img alt="EXIF image preview"></div>
        <div class="observation-exif-preview-data">
          <h3>Datos EXIF</h3>
          <div class="observation-exif-preview-data-rows"></div>
        </div>
        <div class="observation-exif-preview-map" hidden>
          <iframe title="EXIF location preview map" loading="lazy"></iframe>
        </div>
      </div>
      <div class="modal-actions">
        <button class="secondary" type="button" data-observation-exif-preview-cancel>Cancelar</button>
        <button class="primary" type="button" data-observation-exif-preview-accept disabled>Aplicar datos EXIF</button>
      </div>
    </section>
  </div>
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
    function selectEvidenceMapPoint(button) {{
      var mapId = button.getAttribute("data-evidence-map-target");
      var src = button.getAttribute("data-map-src");
      if (!mapId || !src) {{
        return;
      }}
      var frame = document.querySelector('[data-evidence-map-frame="' + mapId + '"]');
      if (frame) {{
        frame.setAttribute("src", src);
      }}
      var label = button.getAttribute("data-map-label") || "";
      var toolbarLabel = null;
      if (frame) {{
        var viewport = frame.closest(".evidence-map-viewport");
        toolbarLabel = viewport ? viewport.querySelector(".evidence-map-toolbar span") : null;
      }}
      if (toolbarLabel && label) {{
        toolbarLabel.textContent = label;
      }}
      var external = button.getAttribute("data-map-external") || "";
      var externalLink = document.querySelector('[data-evidence-map-external="' + mapId + '"]');
      if (externalLink && external) {{
        externalLink.setAttribute("href", external);
      }}
      var selectedRow = button.closest(".evidence-observation-item");
      if (selectedRow) {{
        var list = selectedRow.closest(".evidence-observation-list");
        if (list) {{
          list.querySelectorAll(".evidence-observation-item.selected").forEach(function(row) {{
            row.classList.remove("selected");
            row.removeAttribute("aria-current");
          }});
        }}
        selectedRow.classList.add("selected");
        selectedRow.setAttribute("aria-current", "true");
      }}
    }}
    function selectObservationRow(row) {{
      if (!row) {{
        return;
      }}
      if (row.classList && row.classList.contains("selected")) {{
        return;
      }}
      var href = row.getAttribute("data-observation-href");
      if (!href) {{
        return;
      }}
      rememberObservationListScroll();
      rememberSelectedDetailScroll({{ url: href }});
      window.location.href = href;
    }}
    const speciesModalHistoryKey = "rainmapperSpeciesMaintenanceModalHistory";
    const speciesModalScrollRestoreKey = "rainmapperSpeciesMaintenanceScrollRestore";
    const selectedDetailScrollKey = "rainmapperSelectedDetailScrollY";
    const observationListScrollKey = "rainmapperObservationListScroll";
    function currentRelativeUrl() {{
      return window.location.pathname + window.location.search + window.location.hash;
    }}
    function selectedDetailContextFromUrl(urlText) {{
      var url;
      try {{
        url = new URL(urlText || currentRelativeUrl(), window.location.origin);
      }} catch (error) {{
        return "";
      }}
      var params = url.searchParams;
      if (params.get("section") === "observations" && params.get("obs_id")) {{
        return "observations:" + params.get("obs_id");
      }}
      return "";
    }}
    function rememberSelectedDetailScroll(options) {{
      options = options || {{}};
      var context = selectedDetailContextFromUrl(options.url || currentRelativeUrl());
      if (!context) {{
        return;
      }}
      try {{
        if (options.ifMissing) {{
          var existing = JSON.parse(window.sessionStorage.getItem(selectedDetailScrollKey) || "{{}}");
          if (existing && existing.context === context && Number.isFinite(Number(existing.y))) {{
            return;
          }}
        }}
        window.sessionStorage.setItem(selectedDetailScrollKey, JSON.stringify({{
          context: context,
          y: Number.isFinite(Number(options.scrollY)) ? Number(options.scrollY) : (window.scrollY || 0)
        }}));
      }} catch (error) {{}}
    }}
    function modalLayerForHash(hash) {{
      if (!hash || hash === "#") {{
        return null;
      }}
      try {{
        var target = document.getElementById(decodeURIComponent(hash.slice(1)));
        return target && target.classList.contains("modal-layer") ? target : null;
      }} catch (error) {{
        return null;
      }}
    }}
    function readSpeciesModalHistory() {{
      try {{
        var payload = JSON.parse(window.sessionStorage.getItem(speciesModalHistoryKey) || "[]");
        if (!Array.isArray(payload)) {{
          return [];
        }}
        return payload.map(function(entry) {{
          if (typeof entry === "string") {{
            return {{ url: entry, y: null }};
          }}
          if (entry && typeof entry.url === "string") {{
            return {{
              url: entry.url,
              y: Number.isFinite(Number(entry.y)) ? Number(entry.y) : null
            }};
          }}
          return null;
        }}).filter(function(entry) {{ return entry && entry.url; }});
      }} catch (error) {{
        return [];
      }}
    }}
    function writeSpeciesModalHistory(stack) {{
      try {{
        window.sessionStorage.setItem(speciesModalHistoryKey, JSON.stringify(stack.filter(function(entry) {{
          return entry && entry.url;
        }}).slice(-30)));
      }} catch (error) {{}}
    }}
    function rememberScrollRestoreForUrl(url, scrollY) {{
      if (!url) {{
        return;
      }}
      try {{
        window.sessionStorage.setItem(speciesModalScrollRestoreKey, JSON.stringify({{
          url: url,
          y: Number.isFinite(Number(scrollY)) ? Number(scrollY) : (window.scrollY || 0)
        }}));
      }} catch (error) {{}}
    }}
    function restoreModalScrollPosition() {{
      var payload;
      try {{
        payload = JSON.parse(window.sessionStorage.getItem(speciesModalScrollRestoreKey) || "{{}}");
      }} catch (error) {{
        return;
      }}
      if (!payload || payload.url !== currentRelativeUrl() || !Number.isFinite(Number(payload.y))) {{
        return;
      }}
      try {{
        window.sessionStorage.removeItem(speciesModalScrollRestoreKey);
      }} catch (error) {{}}
      window.setTimeout(function() {{
        window.scrollTo({{ top: Number(payload.y) }});
      }}, 0);
    }}
    function sameDocumentRelativeUrl(urlText) {{
      try {{
        var url = new URL(urlText, window.location.origin);
        return url.pathname === window.location.pathname && url.search === window.location.search;
      }} catch (error) {{
        return false;
      }}
    }}
    function rememberSpeciesModalNavigation(event) {{
      var link = event.target.closest ? event.target.closest("a[href^='#']") : null;
      if (!link) {{
        return;
      }}
      var targetHash = link.getAttribute("href") || "";
      if (!modalLayerForHash(targetHash) || targetHash === window.location.hash) {{
        return;
      }}
      rememberSelectedDetailScroll();
      var currentUrl = currentRelativeUrl();
      var stack = readSpeciesModalHistory();
      var last = stack[stack.length - 1];
      if (!last || last.url !== currentUrl) {{
        stack.push({{ url: currentUrl, y: window.scrollY || 0 }});
      }}
      writeSpeciesModalHistory(stack);
    }}
    function closeSpeciesModalWithHistory(event) {{
      var link = event.target.closest ? event.target.closest("a") : null;
      if (!link || !link.closest(".modal-layer")) {{
        return;
      }}
      var isLocalClose = link.matches("[data-modal-history-close], .modal-backdrop") || link.getAttribute("href") === "#";
      if (!isLocalClose) {{
        return;
      }}
      var stack = readSpeciesModalHistory();
      var returnEntry = stack.pop() || null;
      var returnUrl = returnEntry ? returnEntry.url : "";
      if (!returnUrl) {{
        return;
      }}
      event.preventDefault();
      writeSpeciesModalHistory(stack);
      rememberSelectedDetailScroll({{ ifMissing: true }});
      rememberScrollRestoreForUrl(returnUrl, returnEntry.y);
      window.location.href = returnUrl;
      if (sameDocumentRelativeUrl(returnUrl) && Number.isFinite(Number(returnEntry.y))) {{
        window.setTimeout(function() {{
          window.scrollTo({{ top: Number(returnEntry.y) }});
        }}, 0);
      }}
    }}
    function restoreObservationScroll() {{
      var params;
      try {{
        params = new URLSearchParams(window.location.search);
      }} catch (error) {{
        return;
      }}
      if (params.get("section") !== "observations" || !params.get("obs_id")) {{
        return;
      }}
      var scrollY = null;
      try {{
        var currentContext = selectedDetailContextFromUrl(currentRelativeUrl());
        var payload = JSON.parse(window.sessionStorage.getItem(selectedDetailScrollKey) || "{{}}");
        if (payload && payload.context === currentContext && Number.isFinite(Number(payload.y))) {{
          scrollY = parseInt(payload.y, 10);
          window.sessionStorage.removeItem(selectedDetailScrollKey);
        }}
      }} catch (error) {{}}
      if (scrollY === null) {{
        var stored = "";
        try {{
          stored = window.sessionStorage.getItem("rainmapperObservationScrollY") || "";
          window.sessionStorage.removeItem("rainmapperObservationScrollY");
        }} catch (error) {{}}
        if (!stored) {{
          return;
        }}
        scrollY = parseInt(stored, 10);
      }}
      if (!Number.isFinite(scrollY)) {{
        return;
      }}
      window.setTimeout(function() {{
        window.scrollTo({{ top: scrollY }});
      }}, 0);
    }}
    function observationListContextFromUrl(urlText) {{
      var url;
      try {{
        url = new URL(urlText || currentRelativeUrl(), window.location.origin);
      }} catch (error) {{
        return "";
      }}
      if (url.searchParams.get("section") !== "observations") {{
        return "";
      }}
      url.searchParams.delete("obs_id");
      return url.pathname + "?" + url.searchParams.toString() + "#observations-list";
    }}
    function observationListShell() {{
      return document.querySelector("#observations-workspace .observations-table-shell");
    }}
    function rememberObservationListScroll() {{
      var shell = observationListShell();
      var context = observationListContextFromUrl(currentRelativeUrl());
      if (!shell || !context) {{
        return;
      }}
      try {{
        window.sessionStorage.setItem(observationListScrollKey, JSON.stringify({{
          context: context,
          top: shell.scrollTop || 0,
          left: shell.scrollLeft || 0
        }}));
      }} catch (error) {{}}
    }}
    function restoreObservationListScroll() {{
      var shell = observationListShell();
      var context = observationListContextFromUrl(currentRelativeUrl());
      if (!shell || !context) {{
        return;
      }}
      var restored = false;
      try {{
        var payload = JSON.parse(window.sessionStorage.getItem(observationListScrollKey) || "{{}}");
        if (payload && payload.context === context) {{
          if (Number.isFinite(Number(payload.top))) {{
            shell.scrollTop = Number(payload.top);
            restored = true;
          }}
          if (Number.isFinite(Number(payload.left))) {{
            shell.scrollLeft = Number(payload.left);
          }}
        }}
      }} catch (error) {{}}
      if (!restored) {{
        var selected = shell.querySelector("tr.observation-row.selected");
        if (selected) {{
          var target = selected.offsetTop - (shell.clientHeight / 2) + (selected.clientHeight / 2);
          shell.scrollTop = Math.max(0, target);
        }}
      }}
    }}
    function mushroomApiBasePath() {{
      return window.location.pathname.replace(new RegExp("/mushrooms/profiles/?$"), "");
    }}
    function observationExifPreviewEndpoint() {{
      return mushroomApiBasePath() + "/api/mushrooms/observation-exif-preview";
    }}
    var observationExifPreviewState = {{
      input: null,
      form: null,
      payload: null,
      selectedIndex: 0,
      objectUrls: []
    }};
    function formatExifPreviewNumber(value, suffix) {{
      if (value === null || value === undefined || value === "") {{
        return "-";
      }}
      var number = Number(value);
      if (!Number.isFinite(number)) {{
        return String(value);
      }}
      return number.toFixed(suffix === " m" ? 0 : 6) + (suffix || "");
    }}
    function clearObservationExifPreviewObjectUrls() {{
      observationExifPreviewState.objectUrls.forEach(function(url) {{
        try {{
          URL.revokeObjectURL(url);
        }} catch (error) {{}}
      }});
      observationExifPreviewState.objectUrls = [];
    }}
    function selectedObservationExifPreview() {{
      var previews = observationExifPreviewState.payload && Array.isArray(observationExifPreviewState.payload.previews)
        ? observationExifPreviewState.payload.previews
        : [];
      return previews[observationExifPreviewState.selectedIndex] || null;
    }}
    function setObservationExifPreviewMap(preview, modal) {{
      var map = modal.querySelector(".observation-exif-preview-map");
      var frame = map ? map.querySelector("iframe") : null;
      if (!map || !frame) {{
        return;
      }}
      if (preview && preview.map_src) {{
        frame.setAttribute("src", preview.map_src);
        map.hidden = false;
      }} else {{
        frame.removeAttribute("src");
        map.hidden = true;
      }}
    }}
    function formatExifPreviewSize(bytes) {{
      var number = Number(bytes);
      if (!Number.isFinite(number) || number <= 0) {{
        return "-";
      }}
      if (number < 1024 * 1024) {{
        return Math.round(number / 1024) + " KB";
      }}
      return (number / 1024 / 1024).toFixed(1) + " MB";
    }}
    function renderObservationExifPreviewData(preview, modal) {{
      var rows = modal.querySelector(".observation-exif-preview-data-rows");
      if (!rows) {{
        return;
      }}
      rows.innerHTML = "";
      var entries = preview && preview.ok ? [
        ["▣", "Archivo", preview.filename || "-"],
        ["◷", "Fecha/hora", preview.captured_at_display || preview.captured_at || preview.observed_at || "-"],
        ["⌖", "Coordenadas", formatExifPreviewNumber(preview.lat, "") + ", " + formatExifPreviewNumber(preview.lon, "")],
        ["△", "Altitud", formatExifPreviewNumber(preview.altitude_m, " m")],
        ["◉", "Tipo", preview.content_type || "-"],
        ["□", "Tamaño", formatExifPreviewSize(preview.size_bytes)]
      ] : [
        ["▣", "Archivo", preview && preview.filename ? preview.filename : "-"],
        ["!", "Estado", preview && preview.error ? preview.error : "Sin datos EXIF válidos"]
      ];
      entries.forEach(function(entry) {{
        var row = document.createElement("div");
        row.className = "observation-exif-preview-data-row";
        var icon = document.createElement("span");
        icon.className = "exif-icon";
        icon.textContent = entry[0];
        var label = document.createElement("span");
        label.textContent = entry[1];
        var value = document.createElement("strong");
        value.textContent = entry[2];
        row.appendChild(icon);
        row.appendChild(label);
        row.appendChild(value);
        rows.appendChild(row);
      }});
    }}
    function closeObservationExifPreview(options) {{
      options = options || {{}};
      var modal = document.getElementById("observation-exif-preview-modal");
      if (modal) {{
        modal.hidden = true;
        var frame = modal.querySelector(".observation-exif-preview-map iframe");
        if (frame) {{
          frame.removeAttribute("src");
        }}
      }}
      if (options.clearInput && observationExifPreviewState.input) {{
        observationExifPreviewState.input.value = "";
      }}
      clearObservationExifPreviewObjectUrls();
      observationExifPreviewState = {{
        input: null,
        form: null,
        payload: null,
        selectedIndex: 0,
        objectUrls: []
      }};
    }}
    function applyObservationExifPreview() {{
      var preview = selectedObservationExifPreview();
      var form = observationExifPreviewState.form;
      if (!preview || !preview.ok || !form) {{
        return;
      }}
      var field;
      field = form.querySelector("[name='observed_at']");
      if (field && preview.observed_at) {{
        field.value = preview.observed_at;
      }}
      field = form.querySelector("[name='location_lat']");
      if (field && preview.lat !== null && preview.lat !== undefined) {{
        field.value = String(preview.lat);
      }}
      field = form.querySelector("[name='location_lon']");
      if (field && preview.lon !== null && preview.lon !== undefined) {{
        field.value = String(preview.lon);
      }}
      field = form.querySelector("[name='location_input']");
      if (field && preview.lat !== null && preview.lat !== undefined && preview.lon !== null && preview.lon !== undefined) {{
        field.value = String(preview.lat) + ", " + String(preview.lon);
      }}
      field = form.querySelector("[name='location_source']");
      if (field && preview.lat !== null && preview.lat !== undefined && preview.lon !== null && preview.lon !== undefined) {{
        field.value = "photo_exif";
      }}
      field = form.querySelector("[name='altitude_m']");
      if (field && preview.altitude_m !== null && preview.altitude_m !== undefined) {{
        field.value = String(Math.round(Number(preview.altitude_m)));
      }}
      field = form.querySelector("[name='altitude_source']");
      if (field && preview.altitude_m !== null && preview.altitude_m !== undefined) {{
        field.value = "photo_exif";
      }}
      field = form.querySelector("[name='source_type']");
      if (field) {{
        field.value = "photo_exif";
      }}
      field = form.querySelector("[name='source_label']");
      if (field && preview.filename) {{
        field.value = preview.filename;
      }}
      closeObservationExifPreview({{ clearInput: false }});
    }}
    function clearObservationExifInputs(scope) {{
      if (!scope || !scope.querySelectorAll) {{
        return;
      }}
      Array.prototype.slice.call(scope.querySelectorAll("input[name='observation_exif_images']")).forEach(function(input) {{
        input.value = "";
      }});
    }}
    function renderObservationExifPreview(payload) {{
      var modal = document.getElementById("observation-exif-preview-modal");
      if (!modal) {{
        return;
      }}
      var status = modal.querySelector(".observation-exif-preview-status");
      var grid = modal.querySelector(".observation-exif-preview-grid");
      var photo = modal.querySelector(".observation-exif-preview-photo img");
      var acceptButton = modal.querySelector("[data-observation-exif-preview-accept]");
      if (!grid || !status || !photo || !acceptButton) {{
        return;
      }}
      var input = observationExifPreviewState.input;
      var files = input ? Array.prototype.slice.call(input.files || []) : [];
      var previews = payload && Array.isArray(payload.previews) ? payload.previews : [];
      status.textContent = previews.length ? "Vista previa EXIF de " + previews.length + " imagen(es)." : "No se pudo leer EXIF de las imagenes seleccionadas.";
      grid.innerHTML = "";
      clearObservationExifPreviewObjectUrls();
      previews.forEach(function(preview, index) {{
        var file = files[index] || null;
        var card = document.createElement("button");
        card.type = "button";
        card.className = "observation-exif-preview-card" + (index === 0 ? " selected" : "") + (preview.ok ? "" : " error");
        var image = document.createElement("img");
        if (file) {{
          var objectUrl = URL.createObjectURL(file);
          observationExifPreviewState.objectUrls.push(objectUrl);
          image.src = objectUrl;
        }}
        image.alt = preview.filename || "EXIF image";
        var body = document.createElement("span");
        body.className = "observation-exif-preview-body";
        var title = document.createElement("strong");
        title.textContent = preview.filename || "photo";
        body.appendChild(title);
        var lines = document.createElement("span");
        lines.className = "meta";
        if (preview.ok) {{
          lines.textContent = [
            "Fecha/hora: " + (preview.captured_at_display || preview.captured_at || preview.observed_at || "-"),
            "Coord.: " + formatExifPreviewNumber(preview.lat, "") + ", " + formatExifPreviewNumber(preview.lon, ""),
            "Altitud: " + formatExifPreviewNumber(preview.altitude_m, " m")
          ].join(" · ");
        }} else {{
          lines.textContent = "EXIF no valido: " + (preview.error || "sin datos");
        }}
        body.appendChild(lines);
        card.appendChild(image);
        card.appendChild(body);
        card.addEventListener("click", function() {{
          Array.prototype.slice.call(grid.querySelectorAll(".observation-exif-preview-card")).forEach(function(item) {{
            item.classList.remove("selected");
          }});
          card.classList.add("selected");
          observationExifPreviewState.selectedIndex = index;
          photo.src = image.src || "";
          photo.alt = preview.filename || "EXIF image";
          acceptButton.disabled = !preview.ok;
          renderObservationExifPreviewData(preview, modal);
          setObservationExifPreviewMap(preview, modal);
        }});
        grid.appendChild(card);
      }});
      observationExifPreviewState.selectedIndex = previews.findIndex(function(item) {{ return item && item.ok; }});
      if (observationExifPreviewState.selectedIndex < 0) {{
        observationExifPreviewState.selectedIndex = 0;
      }}
      var selectedCard = grid.querySelectorAll(".observation-exif-preview-card")[observationExifPreviewState.selectedIndex];
      if (selectedCard) {{
        selectedCard.click();
      }} else {{
        photo.removeAttribute("src");
        acceptButton.disabled = true;
        renderObservationExifPreviewData(null, modal);
        setObservationExifPreviewMap(null, modal);
      }}
      modal.hidden = false;
    }}
    async function updateObservationExifPreview(input) {{
      if (!input.files || !input.files.length) {{
        closeObservationExifPreview({{ clearInput: false }});
        return;
      }}
      var modal = document.getElementById("observation-exif-preview-modal");
      if (!modal) {{
        return;
      }}
      observationExifPreviewState.input = input;
      observationExifPreviewState.form = input.closest("form");
      observationExifPreviewState.payload = null;
      observationExifPreviewState.selectedIndex = 0;
      var status = modal.querySelector(".observation-exif-preview-status");
      var grid = modal.querySelector(".observation-exif-preview-grid");
      var photo = modal.querySelector(".observation-exif-preview-photo img");
      var acceptButton = modal.querySelector("[data-observation-exif-preview-accept]");
      if (status) {{
        status.textContent = "Leyendo EXIF...";
      }}
      if (grid) {{
        grid.innerHTML = "";
      }}
      if (photo) {{
        photo.removeAttribute("src");
      }}
      if (acceptButton) {{
        acceptButton.disabled = true;
      }}
      modal.hidden = false;
      var formData = new FormData();
      Array.prototype.slice.call(input.files).forEach(function(file) {{
        formData.append("observation_exif_images", file, file.name);
      }});
      try {{
        var response = await fetch(observationExifPreviewEndpoint(), {{
          method: "POST",
          body: formData,
          credentials: "same-origin"
        }});
        var payload = await response.json();
        if (!response.ok || !payload.ok) {{
          throw new Error(payload.error || "preview failed");
        }}
        observationExifPreviewState.payload = payload;
        renderObservationExifPreview(payload);
      }} catch (error) {{
        if (status) {{
          status.textContent = "No se pudo generar el preview EXIF: " + error.message;
        }}
      }}
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
    function collapseUserCards() {{
      setExpandedUser("");
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
    function activeProfileTabId() {{
      var checked = document.querySelector(".profile-tabs input[name='profile_tab']:checked");
      return checked ? checked.id : "profile-tab-general";
    }}
    function activeEcologyTabId() {{
      var checked = document.querySelector(".ecology-subtabs input[name='ecology_tab']:checked");
      return checked ? checked.id : "";
    }}
    function setProfileReturnTabs() {{
      var activeTab = activeProfileTabId();
      Array.prototype.slice.call(document.querySelectorAll("input[name='profile_return_tab']")).forEach(function(input) {{
        if (!input.value || input.value.indexOf("profile-tab-") === 0) {{
          input.value = activeTab;
        }}
      }});
    }}
    function restoreProfileTab() {{
      var tabId = "";
      if (window.location.hash && window.location.hash.indexOf("#profile-tab-") === 0) {{
        tabId = window.location.hash.slice(1);
      }}
      if (!tabId) {{
        try {{
          tabId = new URLSearchParams(window.location.search).get("profile_tab") || "";
        }} catch (error) {{}}
      }}
      if (!tabId || tabId.indexOf("profile-tab-") !== 0) {{
        return;
      }}
      var tab = document.getElementById(tabId);
      if (tab && tab.name === "profile_tab") {{
        tab.checked = true;
        setProfileReturnTabs();
      }}
    }}
    function restoreEcologyTab() {{
      var tabId = "";
      try {{
        tabId = new URLSearchParams(window.location.search).get("ecology_tab") || "";
      }} catch (error) {{}}
      if (!tabId || tabId.indexOf("eco-tab-") !== 0) {{
        return;
      }}
      var tab = document.getElementById(tabId);
      if (tab && tab.name === "ecology_tab") {{
        tab.checked = true;
      }}
    }}
    function fitProfileListToViewport() {{
      var list = document.querySelector(".profile-list");
      if (!list) {{
        return;
      }}
      if (window.matchMedia && window.matchMedia("(max-width: 980px)").matches) {{
        list.style.maxHeight = "";
        return;
      }}
      var rect = list.getBoundingClientRect();
      var available = Math.max(260, window.innerHeight - rect.top - 16);
      list.style.maxHeight = available + "px";
    }}
    function revealActiveProfileListItem() {{
      var rows = document.querySelector(".profile-list-rows");
      var active = rows ? rows.querySelector(".profile-list-item.active") : null;
      if (!rows || !active) {{
        return;
      }}
      var target = active.offsetTop - (rows.clientHeight / 2) + (active.clientHeight / 2);
      rows.scrollTop = Math.max(0, target);
    }}
    function fitCatalogTableToViewport() {{
      var tableWrap = document.querySelector(".catalog-table-wrap");
      if (!tableWrap) {{
        return;
      }}
      if (window.matchMedia && window.matchMedia("(max-width: 980px)").matches) {{
        tableWrap.style.maxHeight = "";
        return;
      }}
      var rect = tableWrap.getBoundingClientRect();
      var available = Math.max(320, window.innerHeight - rect.top - 16);
      tableWrap.style.maxHeight = available + "px";
    }}
    function revealSelectedCatalogRow() {{
      var tableWrap = document.querySelector(".catalog-table-wrap");
      var selected = tableWrap ? tableWrap.querySelector("tr.selected-row") : null;
      if (!tableWrap || !selected) {{
        return;
      }}
      var target = selected.offsetTop - (tableWrap.clientHeight / 2) + (selected.clientHeight / 2);
      tableWrap.scrollTop = Math.max(0, target);
    }}
    function speciesUrlWithActiveProfileState(href) {{
      var url;
      try {{
        url = new URL(href, window.location.href);
      }} catch (error) {{
        return href;
      }}
      var activeTab = activeProfileTabId();
      var ecologyTab = activeEcologyTabId();
      if (activeTab && activeTab !== "profile-tab-general") {{
        url.searchParams.set("profile_tab", activeTab);
      }} else {{
        url.searchParams.delete("profile_tab");
      }}
      if (activeTab === "profile-tab-ecology" && ecologyTab) {{
        url.searchParams.set("ecology_tab", ecologyTab);
      }} else {{
        url.searchParams.delete("ecology_tab");
      }}
      return (url.search || "?") + url.hash;
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
        collapseUserCards();
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
    document.addEventListener("change", function(event) {{
      if (event.target && event.target.name === "profile_tab") {{
        setProfileReturnTabs();
      }}
      if (event.target && event.target.name === "observation_exif_images") {{
        updateObservationExifPreview(event.target);
      }}
    }});
    document.addEventListener("submit", function(event) {{
      if (event.target && event.target.querySelector("input[name='profile_return_tab']")) {{
        setProfileReturnTabs();
      }}
    }});
    document.addEventListener("click", function(event) {{
      rememberSpeciesModalNavigation(event);
    }}, true);
    document.addEventListener("click", function(event) {{
      closeSpeciesModalWithHistory(event);
      if (event.defaultPrevented) {{
        return;
      }}
      var exifPreviewCancel = event.target.closest("[data-observation-exif-preview-cancel]");
      if (exifPreviewCancel) {{
        event.preventDefault();
        closeObservationExifPreview({{ clearInput: true }});
        return;
      }}
      var exifPreviewAccept = event.target.closest("[data-observation-exif-preview-accept]");
      if (exifPreviewAccept) {{
        event.preventDefault();
        applyObservationExifPreview();
        return;
      }}
      var observationModalClose = event.target.closest(".observation-form .modal-head a[href='#'], .modal-layer > .modal-backdrop[href='#']");
      if (observationModalClose) {{
        var observationLayer = observationModalClose.closest(".modal-layer");
        if (observationLayer && observationLayer.querySelector(".observation-form")) {{
          rememberObservationListScroll();
          clearObservationExifInputs(observationLayer);
        }}
      }}
      var speciesLink = event.target.closest(".profile-list-item[href]");
      if (speciesLink) {{
        speciesLink.href = speciesUrlWithActiveProfileState(speciesLink.href);
      }}
      var dateInput = event.target.closest(".observations-filters input[type='date'], .observation-form input[type='date']");
      if (dateInput && typeof dateInput.showPicker === "function") {{
        try {{
          dateInput.showPicker();
        }} catch (error) {{}}
      }}
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
    document.addEventListener("click", function(event) {{
      var mapButton = event.target.closest("[data-evidence-map-target]");
      if (mapButton) {{
        selectEvidenceMapPoint(mapButton);
      }}
    }});
    document.addEventListener("submit", function(event) {{
      if (event.target && event.target.closest && event.target.closest("#observations-workspace")) {{
        rememberObservationListScroll();
      }}
    }});
    window.addEventListener("resize", function() {{
      fitProfileListToViewport();
      revealActiveProfileListItem();
      fitCatalogTableToViewport();
      revealSelectedCatalogRow();
    }});
    document.addEventListener("DOMContentLoaded", function() {{
      applyUsersFilter();
      collapseUserCards();
      restoreControlTab();
      restoreProfileTab();
      restoreEcologyTab();
      fitProfileListToViewport();
      revealActiveProfileListItem();
      fitCatalogTableToViewport();
      revealSelectedCatalogRow();
      setProfileReturnTabs();
      restoreModalScrollPosition();
      restoreObservationScroll();
      restoreObservationListScroll();
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


def publish_legacy_www_enabled() -> bool:
    return bool_env("RAINMAPPER_PUBLISH_TO_WWW", False)


def append_optional_bokeh_maps(command: str) -> str:
    if publish_legacy_www_enabled():
        return f"{command} && python -m rainmapper_core.bokeh_maps"
    return f"{command} && echo 'Skipping Rainmapper Bokeh maps.'"


def command_for(
    action: str,
    only_source: str | None = None,
    days_init: int | str | None = None,
    days_end: int | str | None = None,
    nototals: str | bool | None = None,
    wunderground_local_start_date: str | None = None,
    wunderground_local_end_date: str | None = None,
) -> list[str]:
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
        str(days_init if days_init is not None else env("RAINMAPPER_DAYS_INIT", "-7")),
        "--days_end",
        str(days_end if days_end is not None else env("RAINMAPPER_DAYS_END", "0")),
        "--nomaps",
        env("RAINMAPPER_NOMAPS", "false"),
        "--nototals",
        str(nototals).lower() if nototals is not None else env("RAINMAPPER_NOTOTALS", "false"),
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
        "--wunderground_daily_api",
        env("RAINMAPPER_WUNDERGROUND_DAILY_API", "true"),
        "--wunderground_full_log",
        env("RAINMAPPER_WUNDERGROUND_FULL_LOG", "false"),
        "--backfill_station_filter",
        env("RAINMAPPER_BACKFILL_STATION_FILTER", ""),
        "--meteoclimatic_pattern",
        env("RAINMAPPER_METEOCLIMATIC_PATTERN", "ESCAT"),
    ]
    if wunderground_local_start_date and wunderground_local_end_date:
        # Monthly backfill windows are local calendar windows. Pass explicit
        # Wunderground dates so Europe/Madrid midnight is not converted to the
        # previous UTC day. Normal updates intentionally keep days_init/days_end
        # so early-month runs reread the previous month and close late WU totals.
        update_command.extend(
            [
                "--wunderground_local_start_date",
                wunderground_local_start_date,
                "--wunderground_local_end_date",
                wunderground_local_end_date,
            ]
        )

    if action == "update":
        return update_command
    if action == "maps":
        maps_command = (
            "python -m rainmapper_core.tomap "
            "--data-dir /app/Data "
            "--maps-dir /app/Tomap "
            "--last-rains-history \"$RAINMAPPER_LAST_RAINS_HISTORY\" "
            "--max-threads \"$RAINMAPPER_MAX_THREADS\" "
            "--include-aemet true"
        )
        return [
            "sh",
            "-c",
            append_optional_bokeh_maps(maps_command),
        ]
    if action == "all":
        if publish_legacy_www_enabled():
            return update_command + ["&&", "python", "-m", "rainmapper_core.bokeh_maps"]
        return update_command + ["&&", "echo", "Skipping Rainmapper Bokeh maps."]
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
    elif line.startswith("Start processing AEMET"):
        updates.update({"current_step": "Running AEMET", **clear_progress()})
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
    elif source == "Wunderground":
        try:
            api_fallback_errors = int(payload.get("api_fallback_errors") or 0)
        except (TypeError, ValueError):
            api_fallback_errors = 0
        alerts_text = (
            '<div class="source-alerts">'
            f'<div class="source-alert">API fallback errors: {api_fallback_errors}</div>'
            "</div>"
        )
    if isinstance(timings, dict) and timings:
        if source == "AEMET":
            timing_labels = [
                ("fetch_seconds", "fetch"),
                ("normalize_seconds", "normalize"),
                ("read_hourly_seconds", "read hourly"),
                ("merge_hourly_seconds", "merge hourly"),
                ("read_stations_seconds", "read stations"),
                ("station_catalog_seconds", "stations"),
                ("station_enrichment_seconds", "enrich"),
                ("build_daily_seconds", "build daily"),
                ("read_daily_seconds", "read daily"),
                ("merge_daily_seconds", "merge daily"),
                ("write_outputs_seconds", "write"),
            ]
        elif source == "Meteocat":
            timing_labels = [
                ("metadata_seconds", "metadata"),
                ("conditions_seconds", "conditions"),
                ("wind_seconds", "wind"),
                ("precipitation_seconds", "rain"),
                ("merge_seconds", "merge"),
                ("read_incremental_seconds", "read incr."),
                ("upsert_incremental_seconds", "upsert"),
                ("write_incremental_seconds", "write incr."),
                ("write_current_seconds", "write current"),
            ]
        elif source == "Meteoclimatic":
            timing_labels = [
                ("fetch_seconds", "fetch"),
                ("build_current_seconds", "build current"),
                ("normalize_dates_seconds", "dates"),
                ("normalize_columns_seconds", "columns"),
                ("station_catalog_seconds", "stations"),
                ("station_update_seconds", "station update"),
                ("read_observations_seconds", "read obs."),
                ("upsert_observations_seconds", "upsert obs."),
                ("write_observations_seconds", "write obs."),
                ("build_daily_seconds", "build daily"),
                ("read_incremental_seconds", "read incr."),
                ("upsert_incremental_seconds", "upsert"),
                ("station_incremental_update_seconds", "station incr."),
                ("write_incremental_seconds", "write incr."),
                ("write_current_seconds", "write current"),
            ]
        elif source == "Wunderground":
            timing_labels = [
                ("scrape_seconds", "scrape"),
                ("metrics_seconds", "metrics"),
                ("read_scrape_csv_seconds", "read scrape"),
                ("normalize_seconds", "normalize"),
                ("station_catalog_seconds", "stations"),
                ("station_update_seconds", "station update"),
                ("write_current_seconds", "write current"),
                ("read_incremental_seconds", "read incr."),
                ("upsert_incremental_seconds", "upsert"),
                ("write_incremental_seconds", "write incr."),
            ]
        else:
            timing_labels = []
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
    started = time.perf_counter()
    if not publish_legacy_www_enabled():
        shutil.rmtree(PUBLIC_PLOTS_PATH, ignore_errors=True)
        return True, "Legacy Bokeh/Plots publishing to /local/Plots is disabled."

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
    elapsed = time.perf_counter() - started
    message = f"Published {copied} map file(s) to /local/Plots at {published_at}."
    log_file.write(f"=== {message} ===\n")
    log_file.write(f"=== publish Plots duration {format_seconds_duration(elapsed)} ===\n")
    log_file.flush()
    with RUN_LOCK:
        RUN_STATE["last_published_at"] = published_at
        RUN_STATE["last_publish_message"] = message
    print(message, flush=True)
    return True, message


def publish_mobile_viewer(log_file) -> tuple[bool, str]:
    started = time.perf_counter()
    PUBLIC_DATA_PATH.mkdir(parents=True, exist_ok=True)
    geojson_started = time.perf_counter()
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
    log_file.write(f"=== GeoJSON publish generation duration {format_seconds_duration(time.perf_counter() - geojson_started)} ===\n")
    log_file.flush()
    if process.returncode != 0:
        return False, "Cannot publish viewers: GeoJSON generation failed."

    config_js = public_viewer_config_js()

    if not MAPLIBRE_VIEWER_ASSETS_PATH.exists():
        return False, "Cannot publish MapLibre viewer: MapLibre viewer assets are missing."

    public_geojson_count = len(list(PUBLIC_DATA_PATH.glob("*.geojson")))
    leaflet_message = ""
    heatmap_message = ""
    if publish_legacy_www_enabled():
        if not Path("/config").exists():
            return False, "Cannot publish legacy public viewers: /config is not available in this container."
        if not LEAFLET_VIEWER_ASSETS_PATH.exists():
            return False, "Cannot publish Leaflet viewer: Leaflet viewer assets are missing."

        leaflet_started = time.perf_counter()
        PUBLIC_LEAFLET_TMP_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(PUBLIC_LEAFLET_TMP_PATH, ignore_errors=True)
        PUBLIC_LEAFLET_TMP_PATH.mkdir(parents=True, exist_ok=True)

        for asset_name in ("index.html", "app.js", "style.css"):
            shutil.copy2(LEAFLET_VIEWER_ASSETS_PATH / asset_name, PUBLIC_LEAFLET_TMP_PATH / asset_name)

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
        log_file.write(f"=== Leaflet publish duration {format_seconds_duration(time.perf_counter() - leaflet_started)} ===\n")
        log_file.flush()
        leaflet_message = f" Published legacy Leaflet viewer with {copied} GeoJSON file(s) to /local/rainmapper-leaflet/index.html."

        heatmap_started = time.perf_counter()
        heatmap_message = publish_heatmap_experimental_maplibre()
        log_file.write(f"=== heatmap viewer publish duration {format_seconds_duration(time.perf_counter() - heatmap_started)} ===\n")
        log_file.flush()
    else:
        shutil.rmtree(PUBLIC_LEAFLET_PATH, ignore_errors=True)
        shutil.rmtree(PUBLIC_LEAFLET_TMP_PATH, ignore_errors=True)
        shutil.rmtree(PUBLIC_MAPLIBRE_PATH, ignore_errors=True)
        shutil.rmtree(PUBLIC_MAPLIBRE_TMP_PATH, ignore_errors=True)
        shutil.rmtree(PUBLIC_MAPLIBRE_HEATMAP_PATH, ignore_errors=True)
        shutil.rmtree(PUBLIC_MAPLIBRE_HEATMAP_TMP_PATH, ignore_errors=True)

    aemet_message = ""
    if PUBLISH_AEMET_EXPERIMENTAL_MAPLIBRE:
        aemet_message = publish_aemet_experimental_maplibre(log_file, config_js)
    else:
        shutil.rmtree(PUBLIC_MAPLIBRE_AEMET_PATH, ignore_errors=True)
        shutil.rmtree(PUBLIC_MAPLIBRE_AEMET_TMP_PATH, ignore_errors=True)

    published_at = datetime.now(get_timezone()).isoformat(timespec="seconds")
    message = (
        f"Published protected MapLibre data with {public_geojson_count} GeoJSON file(s) "
        f"for /protected/maplibre/index.html at {published_at}."
    )
    if leaflet_message:
        message = f"{message}{leaflet_message}"
    if heatmap_message:
        message = f"{message} {heatmap_message}"
    if aemet_message:
        message = f"{message} {aemet_message}"
    log_file.write(f"=== {message} ===\n")
    log_file.write(f"=== mobile viewers publish total duration {format_seconds_duration(time.perf_counter() - started)} ===\n")
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

        def execute_command_step(current_action: str, command: list[str], step_label: str) -> tuple[int, float]:
            nonlocal final_exit_code
            step_started = time.perf_counter()
            print(f"Running Rainmapper step '{step_label}'.", flush=True)
            with RUN_LOCK:
                RUN_STATE.update({"current_step": f"Running {step_label}", **clear_progress()})
            log_file.write(f"=== running step {step_label} ===\n")
            log_file.flush()
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
            print(f"Rainmapper step '{step_label}' finished with exit code {exit_code}.", flush=True)
            elapsed = time.perf_counter() - step_started
            step_duration = format_seconds_duration(elapsed)
            log_file.write(f"=== step {step_label} duration {step_duration} ===\n")
            log_file.flush()
            return exit_code, elapsed

        actions = ["update", "maps"] if action == "all" else [action]
        for current_action in actions:
            step_started = time.perf_counter()
            if current_action == "update" and monthly_backfill_enabled():
                backup_message = backup_incrementals_for_backfill()
                print(backup_message, flush=True)
                log_file.write(f"=== {backup_message} ===\n")
                windows = monthly_backfill_windows()
                log_file.write(
                    "=== monthly backfill enabled: "
                    f"months_init={env('RAINMAPPER_MONTHS_INIT', '-48')}, "
                    f"months_end={env('RAINMAPPER_MONTHS_END', '0')}, "
                    f"months_interval={env('RAINMAPPER_MONTHS_INTERVAL', '3')}, "
                    f"pause={backfill_pause_seconds()}s, windows={len(windows)} ===\n"
                )
                log_file.flush()
                for window_index, window in enumerate(windows, start=1):
                    if window_index > 1:
                        pause_seconds = backfill_pause_seconds()
                        wait_label = f"Waiting monthly backfill pause ({pause_seconds}s)"
                        with RUN_LOCK:
                            RUN_STATE.update({"current_step": wait_label, **clear_progress()})
                        log_file.write(f"=== {wait_label} before window {window_index}/{len(windows)} ===\n")
                        log_file.flush()
                        if pause_seconds:
                            time.sleep(pause_seconds)
                    step_label = (
                        f"update backfill {window_index}/{len(windows)} "
                        f"months {window['months_init']}..{window['months_end']} "
                        f"({window['local_start_date']}..{window['local_end_date']})"
                    )
                    command = command_for(
                        "update",
                        only_source=only_source,
                        days_init=window["days_init"],
                        days_end=window["days_end"],
                        nototals=True,
                        wunderground_local_start_date=str(window["local_start_date"]),
                        wunderground_local_end_date=str(window["local_end_date"]),
                    )
                    exit_code, _ = execute_command_step("update", command, step_label)
                    if exit_code not in {0, 2}:
                        break
                step_duration = format_seconds_duration(time.perf_counter() - step_started)
                log_file.write(f"=== step update monthly backfill total duration {step_duration} ===\n")
                log_file.flush()
            else:
                command = command_for(current_action, only_source=only_source if current_action == "update" else None)
                exit_code, _ = execute_command_step(current_action, command, current_action)
            if exit_code not in {0, 2}:
                break
            if current_action == "maps":
                publish_started = time.perf_counter()
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
                log_file.write(f"=== publish phase duration {format_seconds_duration(time.perf_counter() - publish_started)} ===\n")
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
        estimated_field_opacity = finite_number(raw_settings.get("estimated_field_opacity"), 0.9)
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

    if "estimated_field_dem_zoom" in raw_settings:
        estimated_field_dem_zoom = int(finite_number(raw_settings.get("estimated_field_dem_zoom"), 9))
        if estimated_field_dem_zoom in DEVICE_SETTING_ESTIMATED_FIELD_DEM_ZOOMS:
            settings["estimated_field_dem_zoom"] = estimated_field_dem_zoom

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


CATALOG_ID_PREFIXES = mushroom_catalogs_ui.CATALOG_ID_PREFIXES
catalog_label = mushroom_catalogs_ui.catalog_label
catalog_rows = mushroom_catalogs_ui.catalog_rows
selected_catalog_row = mushroom_catalogs_ui.selected_catalog_row
catalog_query_url = mushroom_catalogs_ui.catalog_query_url
render_catalog_metric_cards = mushroom_catalogs_ui.render_catalog_metric_cards
render_catalog_group_chips = mushroom_catalogs_ui.render_catalog_group_chips
render_catalog_domain_impact = mushroom_catalogs_ui.render_catalog_domain_impact
render_catalog_table = mushroom_catalogs_ui.render_catalog_table
render_catalog_alerts = mushroom_catalogs_ui.render_catalog_alerts
catalog_ids_for_group = mushroom_catalogs_ui.catalog_ids_for_group
catalog_cross_reference_checks = mushroom_catalogs_ui.catalog_cross_reference_checks
render_catalog_detail = mushroom_catalogs_ui.render_catalog_detail
render_catalog_full_json_panel = mushroom_catalogs_ui.render_catalog_full_json_panel
render_new_catalog_entry_form = mushroom_catalogs_ui.render_new_catalog_entry_form

def empty_catalog_entry(group: str, item_id: str) -> dict[str, object]:
    label = {"es": "", "ca": "", "en": ""}
    if group == "trophic_modes":
        return {"id": item_id, "label": label, "description": ""}
    if group == "host_taxa":
        return {
            "id": item_id,
            "rank": "",
            "scientific_name": "",
            "genus": None,
            "family": "",
            "common_names": {"es": [], "ca": [], "en": []},
            "parent_id": None,
            "gis_aliases": [],
        }
    if group == "forest_types":
        return {"id": item_id, "label": label, "dominant_host_ids": [], "gis_aliases": []}
    if group == "soil_types":
        return {"id": item_id, "label": label, "ph_min": None, "ph_max": None, "gis_aliases": []}
    if group == "lithology_types":
        return {
            "id": item_id,
            "label": label,
            "general_reaction": "",
            "parent_soil_tendency_ids": [],
            "gis_aliases": [],
        }
    if group == "aspects":
        return {"id": item_id, "label": label, "azimuth_min": None, "azimuth_max": None}
    if group == "season_patterns":
        return {"id": item_id, "label": label}
    if group == "habitat_features":
        return {"id": item_id, "label": label}
    return {"id": item_id, "label": label}


def validate_new_catalog_entry_id(group: str, item_id: str) -> tuple[bool, str]:
    if group not in CATALOG_ID_PREFIXES:
        return False, f"Catalog group {group or '-'} is not editable."
    if not re.fullmatch(r"[a-z][a-z0-9_]*", item_id):
        return False, "ID must use lowercase letters, numbers and underscores, starting with a letter."
    expected_prefix = CATALOG_ID_PREFIXES[group]
    if not item_id.startswith(expected_prefix):
        return False, f"ID for {group} must start with {expected_prefix}."
    return True, ""


def replace_catalog_entry(catalog_payload: dict[str, object], group: str, item_id: str, entry: dict[str, object]) -> tuple[bool, str]:
    if str(entry.get("id", "")) != item_id:
        return False, "Entry ID cannot be changed in the first maintenance UI."
    catalogs = catalog_payload.get("catalogs")
    if not isinstance(catalogs, dict):
        return False, "Catalog payload does not contain a catalogs object."
    items = catalogs.get(group)
    if not isinstance(items, list):
        return False, f"Catalog group {group} was not found."
    for index, existing in enumerate(items):
        if isinstance(existing, dict) and str(existing.get("id", "")) == item_id:
            items[index] = entry
            return True, f"Updated catalog entry {item_id}."
    return False, f"Catalog entry {item_id} was not found."


def catalog_split_list(value: str) -> list[str]:
    normalized = value.replace(",", "\n")
    return [part.strip() for part in normalized.splitlines() if part.strip()]


def catalog_form_string(form: dict[str, list[str]], name: str) -> str:
    values = form.get(name, [])
    return values[0].strip() if values else ""


def catalog_form_list(form: dict[str, list[str]], name: str) -> list[str]:
    """Return a cleaned list from a repeated form field."""
    return [value.strip() for value in form.get(name, []) if value.strip()]


def catalog_form_nullable_string(form: dict[str, list[str]], name: str) -> str | None:
    value = catalog_form_string(form, name)
    return value or None


def catalog_form_optional_number(form: dict[str, list[str]], name: str) -> float | int | None:
    value = catalog_form_string(form, name).replace(",", ".")
    if not value:
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def catalog_form_labels(form: dict[str, list[str]]) -> dict[str, str]:
    return {language: catalog_form_string(form, f"label_{language}") for language in ("es", "ca", "en")}


def catalog_entry_from_form(group: str, item_id: str, existing: dict[str, object], form: dict[str, list[str]]) -> dict[str, object]:
    entry = dict(existing)
    entry["id"] = item_id
    if group == "host_taxa":
        entry["rank"] = catalog_form_string(form, "rank")
        entry["scientific_name"] = catalog_form_string(form, "scientific_name")
        entry["genus"] = catalog_form_nullable_string(form, "genus")
        entry["family"] = catalog_form_string(form, "family")
        entry["parent_id"] = catalog_form_nullable_string(form, "parent_id")
        entry["common_names"] = {
            "es": catalog_split_list(catalog_form_string(form, "common_names_es")),
            "ca": catalog_split_list(catalog_form_string(form, "common_names_ca")),
            "en": catalog_split_list(catalog_form_string(form, "common_names_en")),
        }
        entry["gis_aliases"] = catalog_split_list(catalog_form_string(form, "gis_aliases"))
        return entry

    entry["label"] = catalog_form_labels(form)
    if group == "forest_types":
        entry["parent_id"] = catalog_form_nullable_string(form, "parent_id")
        entry["dominant_host_ids"] = catalog_split_list(catalog_form_string(form, "dominant_host_ids"))
        entry["soil_bias_ids"] = catalog_split_list(catalog_form_string(form, "soil_bias_ids"))
        entry["gis_aliases"] = catalog_split_list(catalog_form_string(form, "gis_aliases"))
    elif group == "soil_types":
        entry["ph_min"] = catalog_form_optional_number(form, "ph_min")
        entry["ph_max"] = catalog_form_optional_number(form, "ph_max")
        for field in ("texture", "organic_matter", "drainage"):
            value = catalog_form_string(form, field)
            if value or field in entry:
                entry[field] = value
        entry["gis_aliases"] = catalog_split_list(catalog_form_string(form, "gis_aliases"))
    elif group == "lithology_types":
        entry["general_reaction"] = catalog_form_string(form, "general_reaction")
        entry["parent_soil_tendency_ids"] = catalog_split_list(catalog_form_string(form, "parent_soil_tendency_ids"))
        entry["gis_aliases"] = catalog_split_list(catalog_form_string(form, "gis_aliases"))
    elif group == "aspects":
        entry["azimuth_min"] = catalog_form_optional_number(form, "azimuth_min")
        entry["azimuth_max"] = catalog_form_optional_number(form, "azimuth_max")
    if "description" in entry or group == "trophic_modes":
        entry["description"] = catalog_form_string(form, "description")
    if "notes" in entry:
        entry["notes"] = catalog_form_string(form, "notes")
    return entry


def update_catalog_entry_from_form(catalog_payload: dict[str, object], group: str, item_id: str, form: dict[str, list[str]]) -> tuple[bool, str]:
    catalogs = catalog_payload.get("catalogs")
    if not isinstance(catalogs, dict):
        return False, "Catalog payload does not contain a catalogs object."
    items = catalogs.get(group)
    if not isinstance(items, list):
        return False, f"Catalog group {group} was not found."
    for index, existing in enumerate(items):
        if isinstance(existing, dict) and str(existing.get("id", "")) == item_id:
            items[index] = catalog_entry_from_form(group, item_id, existing, form)
            return True, f"Updated catalog entry {item_id}."
    return False, f"Catalog entry {item_id} was not found."


def gis_mapping_from_form(form: dict[str, list[str]]) -> tuple[dict[str, object] | None, str]:
    source_id = catalog_form_string(form, "source_id")
    field = catalog_form_string(form, "field")
    raw_value = catalog_form_string(form, "raw_value")
    if not source_id or not field or not raw_value:
        return None, "Source, field and raw value are required."
    confidence = catalog_form_string(form, "confidence") or "medium"
    review_status = catalog_form_string(form, "review_status") or "pending_review"
    mapping: dict[str, object] = {
        "source_id": source_id,
        "field": field,
        "raw_value": raw_value,
        "confidence": confidence,
        "review_status": review_status,
    }
    mapped_count = 0
    for target_field, _catalog_group in mushroom_gis_mappings_ui.TARGET_CATALOG_FIELDS:
        values = [str(value).strip() for value in form.get(target_field, []) if str(value).strip()]
        if values:
            mapping[target_field] = values
            mapped_count += len(values)
    notes = catalog_form_string(form, "notes")
    if notes:
        mapping["notes"] = notes
    if review_status == "accepted" and mapped_count == 0:
        return None, "Accepted GIS mappings must select at least one catalog target. Use ignored if this raw value should not map to the model."
    return mapping, "ok"


def upsert_exact_gis_mapping(gis_payload: dict[str, object], mapping: dict[str, object]) -> tuple[bool, str]:
    mappings = gis_payload.setdefault("exact_value_mappings", [])
    if not isinstance(mappings, list):
        return False, "GIS payload exact_value_mappings must be a list."
    key = mushroom_gis_mappings_ui.mapping_key(
        mapping.get("source_id", ""),
        mapping.get("field", ""),
        mapping.get("raw_value", ""),
    )
    for index, existing in enumerate(mappings):
        if not isinstance(existing, dict):
            continue
        existing_key = mushroom_gis_mappings_ui.mapping_key(
            existing.get("source_id", ""),
            existing.get("field", ""),
            existing.get("raw_value", ""),
        )
        if existing_key == key:
            mappings[index] = mapping
            return True, f"Updated GIS mapping for {mapping.get('source_id')}.{mapping.get('field')}."
    mappings.append(mapping)
    return True, f"Created GIS mapping for {mapping.get('source_id')}.{mapping.get('field')}."


def mushroom_catalogs_flash() -> str:
    with RUN_LOCK:
        message = str(RUN_STATE.get("mushroom_catalogs_flash", ""))
        RUN_STATE["mushroom_catalogs_flash"] = ""
    return message


def set_mushroom_catalogs_flash(message: str) -> None:
    with RUN_LOCK:
        RUN_STATE["mushroom_catalogs_flash"] = message


def mushroom_gis_mappings_flash() -> str:
    with RUN_LOCK:
        message = str(RUN_STATE.get("mushroom_gis_mappings_flash", ""))
        RUN_STATE["mushroom_gis_mappings_flash"] = ""
    return message


def set_mushroom_gis_mappings_flash(message: str) -> None:
    with RUN_LOCK:
        RUN_STATE["mushroom_gis_mappings_flash"] = message


def mushroom_profiles_flash() -> str:
    with RUN_LOCK:
        message = str(RUN_STATE.get("mushroom_profiles_flash", ""))
        RUN_STATE["mushroom_profiles_flash"] = ""
    return message


def set_mushroom_profiles_flash(message: str) -> None:
    with RUN_LOCK:
        RUN_STATE["mushroom_profiles_flash"] = message


def compact_duration(seconds: float | int | None) -> str:
    if seconds is None:
        return ""
    total = max(0, int(seconds))
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def append_query_param(url: str, key: str, value: str) -> str:
    base, sep, anchor = url.partition("#")
    delimiter = "&" if "?" in base else "?"
    updated = f"{base}{delimiter}{urlencode({key: value})}"
    return f"{updated}{sep}{anchor}" if sep else updated


def observation_species_ids(rows: list[dict[str, object]]) -> list[str]:
    return sorted({str(row.get("species_id", "") or "").strip() for row in rows if str(row.get("species_id", "") or "").strip()})


def observation_has_coordinates(row: dict[str, object]) -> bool:
    location = row.get("location")
    if not isinstance(location, dict):
        return False
    try:
        float(location.get("lat"))  # type: ignore[arg-type]
        float(location.get("lon"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return True


def eligible_model_species_ids(observations: list[dict[str, object]]) -> list[str]:
    return observation_species_ids(
        [
            row
            for row in observations
            if str(row.get("validation_status", "") or "").strip() == "valid"
            and str(row.get("calibration_use", "") or "").strip() == "include"
            and observation_has_coordinates(row)
        ]
    )


def pending_model_species_ids(
    state: dict[str, object],
    observations: list[dict[str, object]],
    *,
    learned_model_payload: object = None,
) -> list[str]:
    eligible_species = set(eligible_model_species_ids(observations))
    pending_species = [
        str(value).strip()
        for value in state.get("pending_rebuild_species_ids", [])
        if str(value or "").strip()
    ]
    pending_species = sorted({species_id for species_id in pending_species if species_id in eligible_species})
    if pending_species:
        return pending_species
    if learned_model_payload is None:
        return sorted(eligible_species)
    return []


def eligible_observation_ids_for_species(
    observations: list[dict[str, object]],
    species_ids: list[str] | set[str],
) -> list[str]:
    selected_species = {str(species_id).strip() for species_id in species_ids if str(species_id or "").strip()}
    ids = []
    for row in observations:
        if str(row.get("species_id", "") or "").strip() not in selected_species:
            continue
        if str(row.get("validation_status", "") or "").strip() != "valid":
            continue
        if str(row.get("calibration_use", "") or "").strip() != "include":
            continue
        if not observation_has_coordinates(row):
            continue
        observation_id = str(row.get("observation_id", "") or "").strip()
        if observation_id:
            ids.append(observation_id)
    return ids


def cleanup_mushroom_rebuild_jobs(now: float | None = None) -> None:
    now = now if now is not None else time.time()
    with RUN_LOCK:
        expired = [
            job_id
            for job_id, job in MUSHROOM_REBUILD_JOBS.items()
            if job.get("finished_at_ts") and now - float(job.get("finished_at_ts") or 0) > MUSHROOM_REBUILD_JOB_TTL_SECONDS
        ]
        for job_id in expired:
            MUSHROOM_REBUILD_JOBS.pop(job_id, None)


def mushroom_rebuild_job_payload(job: dict[str, object]) -> dict[str, object]:
    now = time.time()
    started_at_ts = float(job.get("started_at_ts") or now)
    phase_started_at_ts = float(job.get("phase_started_at_ts") or started_at_ts)
    finished_at_ts = job.get("finished_at_ts")
    current_ts = float(finished_at_ts or now)
    total_elapsed = current_ts - started_at_ts
    phase_elapsed = current_ts - phase_started_at_ts
    overall_percent = int(job.get("overall_percent") or 0)
    phase_percent = int(job.get("phase_percent") or 0)

    total_eta = None
    if 0 < overall_percent < 100:
        total_eta = max(0, (total_elapsed / overall_percent) * (100 - overall_percent))
    phase_eta = None
    if 0 < phase_percent < 100:
        phase_eta = max(0, (phase_elapsed / phase_percent) * (100 - phase_percent))

    return {
        "job_id": job.get("job_id", ""),
        "status": job.get("status", "unknown"),
        "phase": job.get("phase", ""),
        "phase_index": job.get("phase_index", 0),
        "phase_count": job.get("phase_count", 0),
        "phase_percent": phase_percent,
        "overall_percent": overall_percent,
        "message": job.get("message", ""),
        "error": job.get("error", ""),
        "result": job.get("result", {}),
        "elapsed": compact_duration(total_elapsed),
        "phase_elapsed": compact_duration(phase_elapsed),
        "eta": compact_duration(total_eta) if total_eta is not None else "",
        "phase_eta": compact_duration(phase_eta) if phase_eta is not None else "",
        "started_at": job.get("started_at", ""),
        "finished_at": job.get("finished_at", ""),
    }


def set_mushroom_rebuild_progress(
    job_id: str,
    *,
    status: str | None = None,
    phase: str | None = None,
    phase_index: int | None = None,
    phase_count: int | None = None,
    phase_percent: int | None = None,
    overall_percent: int | None = None,
    message: str | None = None,
    error: str | None = None,
    result: dict[str, object] | None = None,
    reset_phase_timer: bool = False,
) -> None:
    now = time.time()
    with RUN_LOCK:
        job = MUSHROOM_REBUILD_JOBS.get(job_id)
        if not job:
            return
        if status is not None:
            job["status"] = status
        if phase is not None:
            job["phase"] = phase
        if phase_index is not None:
            job["phase_index"] = phase_index
        if phase_count is not None:
            job["phase_count"] = phase_count
        if phase_percent is not None:
            job["phase_percent"] = max(0, min(100, int(phase_percent)))
        if overall_percent is not None:
            job["overall_percent"] = max(0, min(100, int(overall_percent)))
        if message is not None:
            job["message"] = message
        if error is not None:
            job["error"] = error
        if result is not None:
            job["result"] = result
        if reset_phase_timer:
            job["phase_started_at_ts"] = now
        if status in {"complete", "failed"}:
            job["finished_at_ts"] = now
            job["finished_at"] = datetime.now(get_timezone()).isoformat(timespec="seconds")


def get_mushroom_rebuild_job_status(job_id: str) -> dict[str, object] | None:
    cleanup_mushroom_rebuild_jobs()
    with RUN_LOCK:
        job = MUSHROOM_REBUILD_JOBS.get(job_id)
        if not job:
            return None
        return mushroom_rebuild_job_payload(dict(job))


def render_mushroom_profiles_flash(message: str) -> str:
    text = str(message or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    is_error = (
        "not saved" in lowered
        or "invalid json" in lowered
        or "failed" in lowered
        or "was not found" in lowered
        or "unknown species" in lowered
    )
    if not is_error:
        return f'<div id="mushroom-profile-message" class="catalog-alert"><strong>Status</strong><br>{html.escape(text)}</div>'
    return (
        '<div id="mushroom-profile-message" class="catalog-alert error">'
        f"<strong>Validation error</strong><br>{html.escape(text)}"
        "<br><span class=\"meta\">Nothing was saved. Review the fields and save again.</span>"
        "</div>"
    )


def render_mushroom_rebuild_progress_modal(job_id: str, refresh_url: str) -> str:
    if not job_id:
        return ""
    safe_job_id = html.escape(job_id, quote=True)
    safe_refresh_url = html.escape(refresh_url, quote=True)
    label = mushroom_profiles_ui.ui_label
    title = html.escape(label("ui.rebuild_progress_title"))
    preparing = html.escape(label("ui.rebuild_progress_preparing"))
    total_label = html.escape(label("ui.rebuild_progress_total"))
    current_step_label = html.escape(label("ui.rebuild_progress_current_step"))
    step_label = html.escape(label("ui.rebuild_progress_step"))
    total_elapsed_label = html.escape(label("ui.rebuild_progress_total_elapsed"))
    step_elapsed_label = html.escape(label("ui.rebuild_progress_step_elapsed"))
    total_eta_label = html.escape(label("ui.rebuild_progress_total_eta"))
    step_eta_label = html.escape(label("ui.rebuild_progress_step_eta"))
    calculating = html.escape(label("ui.rebuild_progress_calculating"))
    refresh_screen = html.escape(label("ui.rebuild_progress_refresh_screen"))
    close_label = html.escape(label("ui.close"))
    return f"""
    <div id="mushroom-rebuild-progress-modal" class="mushroom-progress-backdrop" data-job-id="{safe_job_id}" data-refresh-url="{safe_refresh_url}">
      <section class="mushroom-progress-dialog" role="dialog" aria-modal="true" aria-labelledby="mushroom-rebuild-progress-title">
        <header class="mushroom-progress-header">
          <div>
            <h2 id="mushroom-rebuild-progress-title">{title}</h2>
            <p id="mushroom-rebuild-progress-message" class="meta">{preparing}</p>
          </div>
          <span id="mushroom-rebuild-progress-status" class="status-pill">running</span>
        </header>
        <div class="mushroom-progress-grid">
          <div>
            <span class="field-label">{total_label}</span>
            <progress id="mushroom-rebuild-progress-total" max="100" value="0"></progress>
            <strong id="mushroom-rebuild-progress-total-label">0%</strong>
          </div>
          <div>
            <span class="field-label">{current_step_label}</span>
            <progress id="mushroom-rebuild-progress-phase" max="100" value="0"></progress>
            <strong id="mushroom-rebuild-progress-phase-label">0%</strong>
          </div>
        </div>
        <div class="mushroom-progress-metrics">
          <span><strong>{step_label}</strong><br><em id="mushroom-rebuild-progress-phase-name">-</em></span>
          <span><strong>{total_elapsed_label}</strong><br><em id="mushroom-rebuild-progress-elapsed">0s</em></span>
          <span><strong>{step_elapsed_label}</strong><br><em id="mushroom-rebuild-progress-phase-elapsed">0s</em></span>
          <span><strong>{total_eta_label}</strong><br><em id="mushroom-rebuild-progress-eta">{calculating}</em></span>
          <span><strong>{step_eta_label}</strong><br><em id="mushroom-rebuild-progress-phase-eta">{calculating}</em></span>
        </div>
        <p id="mushroom-rebuild-progress-error" class="catalog-alert error" hidden></p>
        <footer class="mushroom-progress-actions">
          <a id="mushroom-rebuild-progress-refresh" class="button-link" href="{safe_refresh_url}" hidden>{refresh_screen}</a>
          <button id="mushroom-rebuild-progress-close" class="button-link" type="button" hidden>{close_label}</button>
        </footer>
      </section>
    </div>
    <script>
    (() => {{
      const modal = document.getElementById("mushroom-rebuild-progress-modal");
      if (!modal) return;
      const jobId = modal.dataset.jobId;
      const refreshUrl = modal.dataset.refreshUrl || "";
      const closeButton = document.getElementById("mushroom-rebuild-progress-close");
      const refreshLink = document.getElementById("mushroom-rebuild-progress-refresh");
      let terminalStatus = "";
      const fields = {{
        status: document.getElementById("mushroom-rebuild-progress-status"),
        message: document.getElementById("mushroom-rebuild-progress-message"),
        total: document.getElementById("mushroom-rebuild-progress-total"),
        totalLabel: document.getElementById("mushroom-rebuild-progress-total-label"),
        phase: document.getElementById("mushroom-rebuild-progress-phase"),
        phaseLabel: document.getElementById("mushroom-rebuild-progress-phase-label"),
        phaseName: document.getElementById("mushroom-rebuild-progress-phase-name"),
        elapsed: document.getElementById("mushroom-rebuild-progress-elapsed"),
        phaseElapsed: document.getElementById("mushroom-rebuild-progress-phase-elapsed"),
        eta: document.getElementById("mushroom-rebuild-progress-eta"),
        phaseEta: document.getElementById("mushroom-rebuild-progress-phase-eta"),
        error: document.getElementById("mushroom-rebuild-progress-error"),
      }};
      const setText = (node, value) => {{ if (node) node.textContent = value || "-"; }};
      const setProgress = (node, label, value) => {{
        const pct = Math.max(0, Math.min(100, Number(value || 0)));
        if (node) node.value = pct;
        setText(label, `${{pct}}%`);
      }};
      const appBasePath = window.location.pathname.replace(new RegExp("/mushrooms/profiles/?$"), "");
      const statusUrl = `${{appBasePath}}/api/mushrooms/rebuild-status`;
      async function poll() {{
        try {{
          const response = await fetch(`${{statusUrl}}?job_id=${{encodeURIComponent(jobId)}}`, {{cache: "no-store"}});
          const payload = await response.json();
          if (!payload.ok) throw new Error(payload.error || "Cannot read rebuild status.");
          const job = payload.job || {{}};
          setText(fields.status, job.status || "running");
          setText(fields.message, job.message || "");
          setProgress(fields.total, fields.totalLabel, job.overall_percent);
          setProgress(fields.phase, fields.phaseLabel, job.phase_percent);
          const phaseIndex = job.phase_index || 0;
          const phaseCount = job.phase_count || 0;
          setText(fields.phaseName, `${{job.phase || "-"}} (${{phaseIndex}}/${{phaseCount}})`);
          setText(fields.elapsed, job.elapsed || "0s");
          setText(fields.phaseElapsed, job.phase_elapsed || "0s");
          setText(fields.eta, job.eta || "{calculating}");
          setText(fields.phaseEta, job.phase_eta || "{calculating}");
          if (job.error) {{
            fields.error.hidden = false;
            fields.error.textContent = job.error;
          }}
          if (job.status === "complete" || job.status === "failed") {{
            terminalStatus = job.status;
            closeButton.hidden = false;
            refreshLink.hidden = false;
            return;
          }}
        }} catch (error) {{
          fields.error.hidden = false;
          fields.error.textContent = error.message || String(error);
          closeButton.hidden = false;
          return;
        }}
        window.setTimeout(poll, 1000);
      }}
      closeButton.addEventListener("click", () => {{
        if (terminalStatus === "complete" && refreshUrl) {{
          window.location.href = refreshUrl;
          return;
        }}
        modal.remove();
      }});
      poll();
    }})();
    </script>
    """


PROFILE_AFFINITY_GROUPS = mushroom_profiles_ui.PROFILE_AFFINITY_GROUPS
profile_query_url = mushroom_profiles_ui.profile_query_url
profile_nested_dict = mushroom_profiles_ui.nested_dict
render_profile_affinity_rows = mushroom_profiles_ui.render_profile_affinity_rows
render_archived_species_panel = mushroom_profiles_ui.render_archived_species_panel


def profile_message_url(species_id: str = "", search: str = "") -> str:
    return profile_query_url(species_id, search) + "#mushroom-profile-message"


EVIDENCE_DECISIONS_FILE = "mushroom_evidence_decisions.json"
EVIDENCE_DECISION_VALUES = {"promote", "ignore", "keep", "doubtful", "unreviewed"}
EVIDENCE_GROUP_VALUES = {
    "host_affinities",
    "forest_type_affinities",
    "soil_affinities",
    "habitat_feature_affinities",
}


def evidence_decisions_path(store: object) -> Path:
    data_dir = getattr(store, "data_dir")
    return Path(data_dir) / EVIDENCE_DECISIONS_FILE


def load_evidence_decisions(store: object) -> dict[str, object]:
    path = evidence_decisions_path(store)
    if not path.exists():
        return {
            "schema_version": "0.1",
            "kind": "mushroom_local_evidence_decisions",
            "decisions": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": "0.1",
            "kind": "mushroom_local_evidence_decisions",
            "decisions": [],
        }
    if not isinstance(payload, dict):
        payload = {}
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        decisions = []
    return {
        "schema_version": str(payload.get("schema_version", "0.1") or "0.1"),
        "kind": "mushroom_local_evidence_decisions",
        "decisions": [item for item in decisions if isinstance(item, dict)],
    }


def save_evidence_decision(
    store: object,
    species_id: str,
    group: str,
    item_id: str,
    decision: str,
) -> tuple[bool, str]:
    species_id = species_id.strip()
    group = group.strip()
    item_id = item_id.strip()
    decision = decision.strip()
    if not species_id or not item_id:
        return False, "Evidence decision was not saved: species and item ID are required."
    if group not in EVIDENCE_GROUP_VALUES:
        return False, "Evidence decision was not saved: invalid evidence group."
    if decision not in EVIDENCE_DECISION_VALUES:
        return False, "Evidence decision was not saved: invalid decision."
    payload = load_evidence_decisions(store)
    decisions = payload.get("decisions")
    decisions = decisions if isinstance(decisions, list) else []
    key = (species_id, group, item_id)
    kept = [
        item
        for item in decisions
        if not (
            isinstance(item, dict)
            and (str(item.get("species_id", "") or ""), str(item.get("group", "") or ""), str(item.get("item_id", "") or "")) == key
        )
    ]
    if decision != "unreviewed":
        kept.append(
            {
                "species_id": species_id,
                "group": group,
                "item_id": item_id,
                "decision": decision,
                "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "updated_by": "rainmapper_local_ui",
            }
        )
    payload["decisions"] = kept
    write_json_atomic(evidence_decisions_path(store), payload)
    if decision == "unreviewed":
        return True, f"Evidence decision reset for {item_id}."
    return True, f"Evidence decision saved for {item_id}: {decision}."


def evidence_return_url(species_id: str, search: str = "", profile_view: str = "", evidence_view: str = "") -> str:
    return profile_query_url(
        species_id,
        search,
        section="evidence",
        profile_view=profile_view,
        evidence_view=evidence_view,
    ) + "#mushroom-profile-message"


PROFILE_RETURN_TABS = {
    "profile-tab-general",
    "profile-tab-ecology",
    "profile-tab-phenology",
    "profile-tab-weather",
    "profile-tab-scoring",
    "profile-tab-calibration",
    "profile-tab-metadata",
    "profile-tab-json",
}


def profile_save_return_url(species_id: str, form: dict[str, list[str]], *, message: bool = False) -> str:
    """Return to the species editor and restore the active internal tab."""
    tab = catalog_form_string(form, "profile_return_tab")
    if tab not in PROFILE_RETURN_TABS:
        tab = "profile-tab-general"
    profile_view = mushroom_profiles_ui.normalize_profile_view(catalog_form_string(form, "view") or "enriched")
    if message:
        return profile_query_url(species_id, section="species", profile_view=profile_view) + f"&profile_tab={tab}#mushroom-profile-message"
    return profile_query_url(species_id, section="species", profile_view=profile_view) + f"#{tab}"


GOOGLE_BANG_COORD_RE = re.compile(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)")
DECIMAL_COORD_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)")


def observations_message_url(species_id: str = "", anchor: str = "mushroom-profile-message") -> str:
    return profile_query_url(species_id, section="observations") + f"#{anchor}"


def observations_form_url(species_id: str = "") -> str:
    return profile_query_url(species_id, section="observations") + "#new-observation"


def observations_return_url(
    form: dict[str, list[str]],
    fallback_species_id: str = "",
    *,
    anchor: str = "observations-workspace",
    obs_id: str = "",
    duplicate_from: str = "",
    archive_open: bool | None = None,
) -> str:
    """Return to the observation workspace preserving visible filters after POST actions."""
    selected_species_id = catalog_form_string(form, "return_selected_species_id") or fallback_species_id
    params = {"section": "observations"}
    if selected_species_id:
        params["id"] = selected_species_id
    for key in ("date_from", "date_to", "result", "validation", "obs_q", "obs_species", "sort", "dir"):
        value = catalog_form_string(form, f"return_{key}")
        if value:
            params[key] = value
    selected_obs_id = obs_id or catalog_form_string(form, "return_obs_id")
    if selected_obs_id:
        params["obs_id"] = selected_obs_id
    if duplicate_from:
        params["duplicate_from"] = duplicate_from
    should_open_archive = archive_open if archive_open is not None else catalog_form_string(form, "return_archive_open") == "1"
    if should_open_archive:
        params["archive_open"] = "1"
    return "?" + urlencode(params) + f"#{anchor}"


def start_mushroom_model_rebuild_job(
    *,
    selected_observation_ids: list[str],
    reconstruction_scope: str,
    return_url: str,
    pending_species_ids: list[str] | None = None,
) -> str:
    cleanup_mushroom_rebuild_jobs()
    job_id = secrets.token_urlsafe(12)
    now = time.time()
    phase_count = 4
    with RUN_LOCK:
        MUSHROOM_REBUILD_JOBS[job_id] = {
            "job_id": job_id,
            "status": "running",
            "phase": "Preparing",
            "phase_index": 0,
            "phase_count": phase_count,
            "phase_percent": 0,
            "overall_percent": 0,
            "message": f"Queued rebuild for {len(selected_observation_ids)} observation(s).",
            "error": "",
            "result": {},
            "started_at_ts": now,
            "phase_started_at_ts": now,
            "finished_at_ts": None,
            "started_at": datetime.now(get_timezone()).isoformat(timespec="seconds"),
            "finished_at": "",
            "return_url": return_url,
        }

    def run_job() -> None:
        try:
            store = default_store()
            observations_payload = store.load("observations")
            if not isinstance(observations_payload, dict):
                raise RuntimeError("observations payload must be an object")
            observations = observation_dicts_from_payload(observations_payload)
            gis_payload = store.load("gis")
            catalogs_payload = store.load("catalogs")
            selected_total = len(selected_observation_ids)
            if reconstruction_scope == "visible":
                scope_label = "visible filtered"
            elif reconstruction_scope == "pending":
                scope_label = "pending-species"
            else:
                scope_label = "selected"
            pending_species = sorted({str(species_id) for species_id in (pending_species_ids or []) if str(species_id or "").strip()})

            set_mushroom_rebuild_progress(
                job_id,
                phase="GIS/DEM",
                phase_index=1,
                phase_count=phase_count,
                phase_percent=0,
                overall_percent=5,
                message=f"Reconstructing GIS/DEM for {selected_total} {scope_label} observation(s).",
                reset_phase_timer=True,
            )

            def gis_progress(current: int, total: int) -> None:
                phase_percent = int((current / total) * 100) if total else 100
                overall_percent = 5 + int(phase_percent * 0.35)
                set_mushroom_rebuild_progress(
                    job_id,
                    phase_percent=phase_percent,
                    overall_percent=overall_percent,
                    message=f"GIS/DEM {current}/{total} observation(s).",
                )

            gis_result = mushroom_gis_lab.reconstruct_observations(
                observations,
                selected_observation_ids,
                gis_payload=gis_payload if isinstance(gis_payload, dict) else None,
                catalogs_payload=catalogs_payload if isinstance(catalogs_payload, dict) else None,
                progress_callback=gis_progress,
            )
            result_count = int(gis_result.get("result_count", 0) or 0)

            set_mushroom_rebuild_progress(
                job_id,
                phase="Meteorologia",
                phase_index=2,
                phase_percent=0,
                overall_percent=42,
                message="Reconstruyendo contexto meteorologico.",
                reset_phase_timer=True,
            )
            weather_payload = mushroom_observation_context.build_and_write_observation_weather_features()
            weather_count = (
                int(weather_payload.get("summary", {}).get("observations", 0) or 0)
                if isinstance(weather_payload, dict) else 0
            )
            set_mushroom_rebuild_progress(
                job_id,
                phase_percent=100,
                overall_percent=60,
                message=f"Contexto meteorologico reconstruido para {weather_count} observacion(es).",
            )

            set_mushroom_rebuild_progress(
                job_id,
                phase="Features v0",
                phase_index=3,
                phase_percent=0,
                overall_percent=62,
                message="Uniendo features meteorologicas y GIS/DEM.",
                reset_phase_timer=True,
            )
            features_payload = mushroom_observation_features.build_and_write_observation_features_v0()
            feature_count = (
                int(features_payload.get("summary", {}).get("observations", 0) or 0)
                if isinstance(features_payload, dict) else 0
            )
            set_mushroom_rebuild_progress(
                job_id,
                phase_percent=100,
                overall_percent=78,
                message=f"Features v0 reconstruidas para {feature_count} observacion(es).",
            )

            set_mushroom_rebuild_progress(
                job_id,
                phase="Modelo aprendido v0",
                phase_index=4,
                phase_percent=0,
                overall_percent=80,
                message="Construyendo modelo aprendido v0.",
                reset_phase_timer=True,
            )
            if pending_species:
                learned_payload = None
                for pending_species_id in pending_species:
                    learned_payload = mushroom_learned_model.build_and_write_species_learned_model_v0(pending_species_id)
            else:
                learned_payload = mushroom_learned_model.build_and_write_learned_model_v0()
            model_species_count = (
                int(learned_payload.get("summary", {}).get("species", 0) or 0)
                if isinstance(learned_payload, dict) else 0
            )
            message = (
                "Modelo v0 rebuilt: "
                f"GIS/DEM {result_count} {scope_label} observation(s), "
                f"weather {weather_count}, features {feature_count}, species models {model_species_count}."
            )
            if pending_species:
                mushroom_model_state.clear_species_pending(pending_species)
            else:
                mushroom_model_state.clear_all_pending(full_rebuild=True)
            set_mushroom_profiles_flash(message)
            set_mushroom_rebuild_progress(
                job_id,
                status="complete",
                phase_percent=100,
                overall_percent=100,
                message=message,
                result={
                    "gis_observations": result_count,
                    "weather_observations": weather_count,
                    "feature_observations": feature_count,
                    "model_species": model_species_count,
                    "return_url": return_url,
                },
            )
        except Exception as exc:
            error = f"Modelo v0 rebuild failed: {exc}"
            set_mushroom_profiles_flash(error)
            set_mushroom_rebuild_progress(job_id, status="failed", error=error, message=error)

    thread = threading.Thread(target=run_job, name=f"mushroom-rebuild-{job_id}", daemon=True)
    thread.start()
    return job_id


def next_observation_id(observations: list[dict[str, object]], observed_at: str) -> str:
    """Return a stable observation ID using the observation date and local sequence."""
    compact_date = observed_at.replace("-", "")
    prefix = f"obs_{compact_date}_"
    highest = 0
    for row in observations:
        value = str(row.get("observation_id", ""))
        if not value.startswith(prefix):
            continue
        try:
            highest = max(highest, int(value.rsplit("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"{prefix}{highest + 1:04d}"


def parse_observation_coordinates(form: dict[str, list[str]]) -> tuple[str, float, float, str]:
    """Parse coordinates from explicit fields, decimal text, or common Google Maps URLs."""
    location_input = catalog_form_string(form, "location_input")
    source_override = catalog_form_string(form, "location_source")
    raw_lat = catalog_form_string(form, "location_lat").replace(",", ".")
    raw_lon = catalog_form_string(form, "location_lon").replace(",", ".")
    if bool(raw_lat) != bool(raw_lon):
        raise ValueError("Latitude and longitude must both be informed when using coordinate fields.")
    if raw_lat and raw_lon:
        lat = float(raw_lat)
        lon = float(raw_lon)
        return location_input or f"{lat}, {lon}", lat, lon, source_override or "manual_decimal"
    if not location_input:
        raise ValueError("Coordinates are required: paste a Google Maps link, decimal coordinates, or inform latitude and longitude.")

    source = source_override or ("google_maps_url" if any(marker in location_input for marker in ("google.", "maps.app.goo.gl", "goo.gl/maps")) else "manual_decimal")
    bang_match = GOOGLE_BANG_COORD_RE.search(location_input)
    if bang_match:
        return location_input, float(bang_match.group(1)), float(bang_match.group(2)), source
    decimal_match = DECIMAL_COORD_RE.search(location_input)
    if decimal_match:
        return location_input, float(decimal_match.group(1)), float(decimal_match.group(2)), source
    raise ValueError("Coordinates could not be parsed from the observation location.")


def archived_observations_path(store: object) -> Path:
    """Return the persistent archive file for mushroom observations."""
    data_dir = getattr(store, "data_dir")
    return Path(data_dir) / "archived" / "mushroom_observations_archived.json"


def empty_archived_observations_payload() -> dict[str, object]:
    """Return the stable archive container used by observation archive/restore actions."""
    return {
        "schema_version": "0.1",
        "observations": [],
        "metadata": {
            "created_at": datetime.now(UTC).date().isoformat(),
            "updated_at": datetime.now(UTC).date().isoformat(),
            "updated_by": "rainmapper_ui",
        },
    }


def load_archived_observations(store: object) -> dict[str, object]:
    path = archived_observations_path(store)
    if not path.exists():
        return empty_archived_observations_payload()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else empty_archived_observations_payload()


def write_archived_observations(store: object, payload: dict[str, object]) -> None:
    from rainmapper_core.mushroom_store import write_json_atomic

    metadata = payload.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata["updated_at"] = datetime.now(UTC).date().isoformat()
        metadata["updated_by"] = "rainmapper_ui"
    write_json_atomic(archived_observations_path(store), payload)


def observation_dicts_from_payload(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = payload.get("observations")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def find_observation_by_id(rows: list[dict[str, object]], observation_id: str) -> dict[str, object] | None:
    for row in rows:
        if str(row.get("observation_id", "")) == observation_id:
            return row
    return None


def observation_payload_from_form(
    form: dict[str, list[str]],
    observations: list[dict[str, object]],
    existing: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a persisted observation from the server-side maintenance form."""
    existing = existing if isinstance(existing, dict) else {}
    species_id = catalog_form_string(form, "observation_species_id")
    observed_at = catalog_form_string(form, "observed_at")
    if not species_id:
        raise ValueError("Species is required.")
    if not observed_at:
        raise ValueError("Observation date is required.")
    location_input, lat, lon, location_source = parse_observation_coordinates(form)
    altitude_m = catalog_form_optional_number(form, "altitude_m")
    source_type = catalog_form_string(form, "source_type")
    observed_host_ids = catalog_form_list(form, "observed_host_ids")
    if len(observed_host_ids) > 3:
        raise ValueError("Select at most 3 observed host trees.")
    observed_forest_type_ids = catalog_form_list(form, "observed_forest_type_ids")
    observed_soil_tendency_ids = catalog_form_list(form, "observed_soil_tendency_ids")
    observed_habitat_feature_ids = catalog_form_list(form, "observed_habitat_feature_ids")
    observed_aspect_ids = catalog_form_list(form, "observed_aspect_ids")
    today = datetime.now(UTC).date().isoformat()
    existing_metadata = existing.get("metadata") if isinstance(existing.get("metadata"), dict) else {}
    observation: dict[str, object] = {
        "observation_id": str(existing.get("observation_id", "") or next_observation_id(observations, observed_at)),
        "species_id": species_id,
        "observed_at": observed_at,
        "location": {
            "input": location_input,
            "lat": lat,
            "lon": lon,
            "source": location_source,
            "precision_m": catalog_form_optional_number(form, "location_precision_m"),
        },
        "flush_abundance": catalog_form_string(form, "flush_abundance"),
        "observer": {
            "name": catalog_form_string(form, "observer_name"),
            "expertise": catalog_form_string(form, "observer_expertise"),
        },
        "source": {
            "type": source_type,
            "label": catalog_form_string(form, "source_label"),
            "url": catalog_form_string(form, "source_url"),
            "notes": catalog_form_string(form, "source_notes"),
        },
        "source_quality": catalog_form_optional_number(form, "source_quality"),
        "validation_status": catalog_form_string(form, "validation_status"),
        "calibration_use": catalog_form_string(form, "calibration_use"),
        "calibration_exclusion_reason": catalog_form_string(form, "calibration_exclusion_reason") or None,
        "site_context": {
            "observed_host_ids": observed_host_ids,
            "observed_forest_type_ids": observed_forest_type_ids,
            "observed_soil_tendency_ids": observed_soil_tendency_ids,
            "observed_habitat_feature_ids": observed_habitat_feature_ids,
            "observed_aspect_ids": observed_aspect_ids,
            "habitat_notes": catalog_form_string(form, "habitat_notes"),
            "host_notes": catalog_form_string(form, "host_notes"),
            "soil_notes": catalog_form_string(form, "soil_notes"),
            "aspect_notes": catalog_form_string(form, "aspect_notes"),
        },
        "metadata": {
            "created_at": str(existing_metadata.get("created_at", today)),
            "updated_at": today,
            "created_by": str(existing_metadata.get("created_by", "rainmapper_ui")),
            "updated_by": "rainmapper_ui",
        },
    }
    if altitude_m is not None or catalog_form_string(form, "altitude_source"):
        observation["altitude"] = {
            "meters": altitude_m,
            "source": catalog_form_string(form, "altitude_source") or "manual",
            "resolved_at": today if altitude_m is not None else None,
        }
    existing_media = existing.get("media")
    if isinstance(existing_media, list):
        observation["media"] = [item for item in existing_media if isinstance(item, dict)]
    return mushroom_observations.finalize_observation_payload(observation)


def clone_observation_payload(
    source: dict[str, object],
    observations: list[dict[str, object]],
) -> dict[str, object]:
    """Return a duplicated observation ready for immediate editing."""
    clone = json.loads(json.dumps(source))
    observed_at = str(clone.get("observed_at", datetime.now(UTC).date().isoformat()))
    clone["observation_id"] = next_observation_id(observations, observed_at)
    metadata = clone.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    today = datetime.now(UTC).date().isoformat()
    metadata["created_at"] = today
    metadata["updated_at"] = today
    metadata["created_by"] = "rainmapper_ui_duplicate"
    metadata["updated_by"] = "rainmapper_ui_duplicate"
    clone["metadata"] = metadata
    return mushroom_observations.finalize_observation_payload(clone)


def exif_ratio_to_float(value: object) -> float:
    """Convert a Pillow EXIF rational-like value to float."""
    numerator = getattr(value, "numerator", None)
    denominator = getattr(value, "denominator", None)
    if numerator is not None and denominator:
        return float(numerator) / float(denominator)
    if isinstance(value, tuple) and len(value) == 2:
        return float(value[0]) / float(value[1])
    return float(value)


def exif_dms_to_decimal(value: object, ref: object) -> float:
    """Convert EXIF GPS degrees/minutes/seconds to signed decimal degrees."""
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError("invalid GPS coordinate format")
    degrees = exif_ratio_to_float(value[0])
    minutes = exif_ratio_to_float(value[1])
    seconds = exif_ratio_to_float(value[2])
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if str(ref).upper() in {"S", "W"}:
        decimal = -decimal
    return decimal


def exif_ref_to_int(value: object) -> int:
    """Convert byte or numeric EXIF reference flags to an integer."""
    if isinstance(value, bytes):
        return int.from_bytes(value[:1], "big") if value else 0
    return int(value or 0)


def extract_photo_exif_observation_fields(filename: str, content: bytes) -> dict[str, object]:
    """Extract observation date, coordinates and altitude from a JPEG EXIF payload."""
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, TAGS
    except ImportError as exc:
        raise ValueError("Pillow is required to import EXIF images.") from exc

    with Image.open(io.BytesIO(content)) as image:
        exif = image.getexif()
        if not exif:
            raise ValueError("image has no EXIF metadata")
        tags = {TAGS.get(tag, tag): value for tag, value in exif.items()}
        raw_date = str(tags.get("DateTimeOriginal") or tags.get("DateTime") or "").strip()
        if not raw_date:
            raise ValueError("image has no EXIF capture date")
        try:
            capture_datetime = datetime.strptime(raw_date[:19], "%Y:%m:%d %H:%M:%S")
            captured_at = capture_datetime.isoformat(sep=" ", timespec="seconds")
            captured_at_display = capture_datetime.strftime("%d/%m/%Y %H:%M")
            observed_at = capture_datetime.date().isoformat()
        except ValueError as exc:
            raise ValueError(f"invalid EXIF capture date {raw_date!r}") from exc

        gps_ifd = {}
        try:
            gps_ifd = exif.get_ifd(34853)
        except Exception:
            raw_gps = tags.get("GPSInfo")
            gps_ifd = raw_gps if isinstance(raw_gps, dict) else {}
        gps = {GPSTAGS.get(tag, tag): value for tag, value in gps_ifd.items()}
        if not gps:
            raise ValueError("image has no GPS metadata")
        lat = exif_dms_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
        lon = exif_dms_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
        altitude = None
        if gps.get("GPSAltitude") is not None:
            altitude = exif_ratio_to_float(gps.get("GPSAltitude"))
            if exif_ref_to_int(gps.get("GPSAltitudeRef")) == 1:
                altitude = -altitude

    return {
        "filename": filename,
        "observed_at": observed_at,
        "captured_at": captured_at,
        "captured_at_display": captured_at_display,
        "lat": lat,
        "lon": lon,
        "altitude_m": altitude,
    }


def preview_photo_exif_uploads(files: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    """Return EXIF preview metadata for uploaded observation images without saving them."""
    uploads = [
        item
        for item in files.get("observation_exif_images", [])
        if isinstance(item, dict) and item.get("filename") and item.get("content")
    ]
    previews: list[dict[str, object]] = []
    for index, item in enumerate(uploads):
        filename = str(item.get("filename", "photo") or "photo")
        content = item.get("content")
        content_type = str(item.get("content_type", "") or "")
        preview: dict[str, object] = {
            "index": index,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(content) if isinstance(content, bytes) else 0,
            "ok": False,
        }
        if not isinstance(content, bytes):
            preview["error"] = "invalid upload payload"
            previews.append(preview)
            continue
        try:
            fields = extract_photo_exif_observation_fields(filename, content)
        except ValueError as exc:
            preview["error"] = str(exc)
            previews.append(preview)
            continue
        lat = fields.get("lat")
        lon = fields.get("lon")
        altitude = fields.get("altitude_m")
        preview.update(
            {
                "ok": True,
                "observed_at": fields.get("observed_at"),
                "captured_at": fields.get("captured_at"),
                "captured_at_display": fields.get("captured_at_display"),
                "lat": lat,
                "lon": lon,
                "altitude_m": altitude,
                "map_src": mushroom_profiles_ui.google_maps_embed_src(float(lat), float(lon)) if lat is not None and lon is not None else "",
            }
        )
        previews.append(preview)
    return {"previews": previews}


def safe_observation_media_name(filename: str, extension: str = ".jpg") -> str:
    """Return a human-readable safe filename for one persisted observation image."""
    source_name = Path(str(filename or "photo")).name
    source_stem = Path(source_name).stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", source_stem).strip("-") or "photo"
    ext = Path(source_name).suffix.lower() or extension
    ext = ext if ext.startswith(".") else f".{ext}"
    ext = re.sub(r"[^a-z0-9.]+", "", ext.lower()) or ".jpg"
    return f"{stem}{ext}"


def original_image_extension(filename: str, content_type: str = "") -> str:
    """Return a conservative image extension for uploads that cannot be resized."""
    suffix = Path(str(filename or "")).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".heic", ".heif"}:
        return suffix
    guessed = mimetypes.guess_extension(str(content_type or "").split(";", 1)[0].strip())
    if guessed in {".jpg", ".jpeg", ".heic", ".heif"}:
        return guessed
    return ".jpg"


def observation_image_media_url(relative_path: str) -> str:
    return "./observation-media?" + urlencode({"path": relative_path})


def observation_media_file_path(relative_path: str) -> Path | None:
    """Return a safe media file path inside the configured mushroom data root."""
    path_text = str(relative_path or "").strip().lstrip("/")
    if not path_text or "\x00" in path_text:
        return None
    root = mushroom_paths.mushroom_data_dir().resolve()
    candidate = (root / path_text).resolve()
    if root != candidate and root not in candidate.parents:
        return None
    return candidate


def legacy_observation_media_file_path(observation_id: str, stored_filename: str) -> Path | None:
    safe_observation_id = re.sub(r"[^a-zA-Z0-9_.-]+", "", str(observation_id or ""))
    safe_name = Path(str(stored_filename or "")).name
    if not safe_observation_id or not safe_name or safe_name in {".", ".."}:
        return None
    root = mushroom_paths.mushroom_observation_images_dir().resolve()
    candidate = (root / safe_observation_id / safe_name).resolve()
    if root != candidate and root not in candidate.parents:
        return None
    return candidate


def observation_media_year(observed_at: object = None) -> str:
    text = str(observed_at or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text[:4]
    return datetime.now(UTC).date().isoformat()[:4]


def unique_media_path(target_dir: Path, filename: str, content: bytes) -> Path:
    candidate = target_dir / filename
    if not candidate.exists() or candidate.read_bytes() == content:
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        next_candidate = target_dir / f"{stem}-{counter}{suffix}"
        if not next_candidate.exists() or next_candidate.read_bytes() == content:
            return next_candidate
        counter += 1


def save_observation_image_media(
    observation_id: str,
    upload: dict[str, object],
    observed_at: object = None,
) -> dict[str, object] | None:
    """Persist one uploaded observation image and return its JSON media entry."""
    filename = str(upload.get("filename", "photo") or "photo")
    content = upload.get("content")
    if not isinstance(content, bytes) or not content:
        return None
    content_type = str(upload.get("content_type", "") or "")
    year = observation_media_year(observed_at)
    target_dir = mushroom_paths.mushroom_observation_photos_dir() / year
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = safe_observation_media_name(filename, ".jpg")
    target_path = target_dir / stored_filename
    persisted_content_type = "image/jpeg"
    resized = False
    exif_preserved = False
    output_content = b""
    try:
        from PIL import Image
        from PIL import ImageOps

        with Image.open(io.BytesIO(content)) as image:
            image = ImageOps.exif_transpose(image)
            exif_bytes = image.info.get("exif", b"")
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            image.thumbnail(
                (MUSHROOM_OBSERVATION_IMAGE_MAX_EDGE, MUSHROOM_OBSERVATION_IMAGE_MAX_EDGE),
                Image.Resampling.LANCZOS,
            )
            save_kwargs: dict[str, object] = {
                "format": "JPEG",
                "quality": MUSHROOM_OBSERVATION_IMAGE_JPEG_QUALITY,
                "optimize": True,
            }
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
                exif_preserved = True
            output = io.BytesIO()
            image.save(output, **save_kwargs)
            output_content = output.getvalue()
            resized = True
    except Exception:
        extension = original_image_extension(filename, content_type)
        stored_filename = safe_observation_media_name(filename, extension)
        output_content = content
        persisted_content_type = content_type.split(";", 1)[0].strip() or content_type_for(target_path)

    target_path = unique_media_path(target_dir, stored_filename, output_content)
    target_path.write_bytes(output_content)
    stored_filename = target_path.name
    relative_path = f"media/observation-photos/{year}/{stored_filename}"
    return {
        "kind": "photo",
        "path": relative_path,
        "url": observation_image_media_url(relative_path),
        "stored_filename": stored_filename,
        "original_filename": filename,
        "content_type": persisted_content_type,
        "size_bytes": target_path.stat().st_size,
        "resized": resized,
        "exif_preserved": exif_preserved,
        "variant": "display",
    }


def append_observation_media(observation: dict[str, object], media: dict[str, object] | None) -> None:
    if not media:
        return
    existing = observation.get("media")
    media_rows = [item for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []
    media_rows.append(media)
    observation["media"] = media_rows


def photo_exif_observation_payload(
    form: dict[str, list[str]],
    observations: list[dict[str, object]],
    fields: dict[str, object],
) -> dict[str, object]:
    """Build one persisted observation from common import fields and image EXIF fields."""
    species_id = catalog_form_string(form, "observation_species_id")
    if not species_id:
        raise ValueError("Species is required.")
    observed_host_ids = catalog_form_list(form, "observed_host_ids")
    if len(observed_host_ids) > 3:
        raise ValueError("Select at most 3 observed host trees.")
    observed_forest_type_ids = catalog_form_list(form, "observed_forest_type_ids")
    observed_soil_tendency_ids = catalog_form_list(form, "observed_soil_tendency_ids")
    observed_habitat_feature_ids = catalog_form_list(form, "observed_habitat_feature_ids")
    observed_aspect_ids = catalog_form_list(form, "observed_aspect_ids")
    filename = str(fields.get("filename", "") or "photo")
    observed_at = str(fields["observed_at"])
    lat = float(fields["lat"])
    lon = float(fields["lon"])
    altitude_m = fields.get("altitude_m")
    today = datetime.now(UTC).date().isoformat()
    observation: dict[str, object] = {
        "observation_id": next_observation_id(observations, observed_at),
        "species_id": species_id,
        "observed_at": observed_at,
        "location": {
            "input": f"{lat:.8f}, {lon:.8f}",
            "lat": lat,
            "lon": lon,
            "source": "photo_exif",
            "precision_m": None,
        },
        "flush_abundance": catalog_form_string(form, "flush_abundance"),
        "observer": {
            "name": catalog_form_string(form, "observer_name"),
            "expertise": catalog_form_string(form, "observer_expertise") or "unknown",
        },
        "source": {
            "type": "photo_exif",
            "label": filename,
            "url": "",
            "notes": catalog_form_string(form, "source_notes"),
        },
        "source_quality": catalog_form_optional_number(form, "source_quality"),
        "validation_status": catalog_form_string(form, "validation_status"),
        "calibration_use": catalog_form_string(form, "calibration_use"),
        "calibration_exclusion_reason": catalog_form_string(form, "calibration_exclusion_reason") or None,
        "site_context": {
            "observed_host_ids": observed_host_ids,
            "observed_forest_type_ids": observed_forest_type_ids,
            "observed_soil_tendency_ids": observed_soil_tendency_ids,
            "observed_habitat_feature_ids": observed_habitat_feature_ids,
            "observed_aspect_ids": observed_aspect_ids,
            "habitat_notes": "",
            "host_notes": "",
            "soil_notes": "",
            "aspect_notes": "",
        },
        "metadata": {
            "created_at": today,
            "updated_at": today,
            "created_by": "rainmapper_ui_exif_import",
            "updated_by": "rainmapper_ui_exif_import",
        },
    }
    if altitude_m is not None:
        observation["altitude"] = {
            "meters": round(float(altitude_m), 1),
            "source": "photo_exif",
            "resolved_at": today,
        }
    return mushroom_observations.finalize_observation_payload(observation)


def observation_form_with_exif_fields(
    form: dict[str, list[str]],
    fields: dict[str, object],
) -> dict[str, list[str]]:
    """Return a form copy with date, location, altitude and source overridden from EXIF."""
    next_form = {key: list(value) for key, value in form.items()}
    lat = float(fields["lat"])
    lon = float(fields["lon"])
    next_form["observed_at"] = [str(fields["observed_at"])]
    next_form["location_input"] = [f"{lat:.8f}, {lon:.8f}"]
    next_form["location_lat"] = [str(lat)]
    next_form["location_lon"] = [str(lon)]
    next_form["location_source"] = ["photo_exif"]
    next_form["source_type"] = ["photo_exif"]
    next_form["source_label"] = [str(fields.get("filename", "") or "photo")]
    if fields.get("altitude_m") is not None:
        next_form["altitude_m"] = [str(round(float(fields["altitude_m"]), 1))]
        next_form["altitude_source"] = ["photo_exif"]
    return next_form


def archived_profiles_path(store: object) -> Path:
    """Return the persistent archive file for deleted mushroom profiles."""
    data_dir = getattr(store, "data_dir")
    return Path(data_dir) / "archived" / "mushroom_profiles_archived.json"


def empty_archived_profiles_payload() -> dict[str, object]:
    """Return the stable archive container used by archive/restore actions."""
    return {
        "schema_version": "1.0",
        "archived_species_profiles": [],
    }


def load_archived_profiles(store: object) -> dict[str, object]:
    """Load archived species profiles, tolerating the file not existing yet."""
    path = archived_profiles_path(store)
    if not path.exists():
        return empty_archived_profiles_payload()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return empty_archived_profiles_payload()
    profiles = payload.get("archived_species_profiles")
    if not isinstance(profiles, list):
        payload["archived_species_profiles"] = []
    return payload


def write_archived_profiles(store: object, payload: dict[str, object]) -> None:
    """Persist archived species profiles with an atomic replace."""
    from rainmapper_core.mushroom_store import write_json_atomic

    path = archived_profiles_path(store)
    write_json_atomic(path, payload)


def archived_profile_dicts(archive_payload: dict[str, object]) -> list[dict[str, object]]:
    """Return archived profile dictionaries only."""
    profiles = archive_payload.get("archived_species_profiles")
    return [profile for profile in profiles if isinstance(profile, dict)] if isinstance(profiles, list) else []


def profile_dicts_from_payload(profiles_payload: dict[str, object]) -> list[dict[str, object]]:
    """Return active profile dictionaries from a profiles payload."""
    profiles = profiles_payload.get("species_profiles")
    return [profile for profile in profiles if isinstance(profile, dict)] if isinstance(profiles, list) else []


def find_profile_by_id(profiles: list[dict[str, object]], species_id: str) -> dict[str, object] | None:
    """Return a profile matching the stable species ID."""
    for profile in profiles:
        if str(profile.get("species_id", "")) == species_id:
            return profile
    return None


def profile_form_number(form: dict[str, list[str]], name: str) -> float | int | None:
    return catalog_form_optional_number(form, name)


def profile_form_int_list(form: dict[str, list[str]], name: str) -> list[int]:
    values = []
    for raw_value in form.get(name, []):
        for part in catalog_split_list(raw_value):
            values.append(int(part))
    return values


def profile_form_string_list(form: dict[str, list[str]], name: str) -> list[str]:
    return [str(value).strip() for value in form.get(name, []) if str(value).strip()]


def profile_form_bool(form: dict[str, list[str]], name: str) -> bool:
    return catalog_form_string(form, name) == "true"


def profile_affinities_from_form(form: dict[str, list[str]], field: str) -> list[dict[str, object]]:
    affinities = []
    index = 0
    while f"{field}_{index}_id" in form:
        item_id = catalog_form_string(form, f"{field}_{index}_id")
        relationship = catalog_form_string(form, f"{field}_{index}_relationship")
        affinity = profile_form_number(form, f"{field}_{index}_affinity")
        if item_id:
            item: dict[str, object] = {"id": item_id}
            if relationship:
                item["relationship"] = relationship
            if affinity is not None:
                item["affinity"] = affinity
            original_id = catalog_form_string(form, f"{field}_{index}_original_id")
            if original_id == item_id:
                source_ids = profile_form_string_list(form, f"{field}_{index}_source_ids")
                if source_ids:
                    item["source_ids"] = source_ids
                if catalog_form_string(form, f"{field}_{index}_v0_placeholder") == "true":
                    item["v0_placeholder"] = True
                if catalog_form_string(form, f"{field}_{index}_v0_active") == "false":
                    item["v0_active"] = False
            affinities.append(item)
        index += 1
    return affinities


def finalize_species_profile_payload(profile: dict[str, object], *, updated_by: str = "rainmapper_ui") -> dict[str, object]:
    """Return a profile copy with shared save-time metadata normalized."""
    finalized = json.loads(json.dumps(profile))
    metadata = finalized.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["updated_at"] = datetime.now(UTC).date().isoformat()
    metadata["updated_by"] = updated_by
    finalized["metadata"] = metadata
    return finalized


def profile_semantic_error_messages(profile: dict[str, object]) -> list[str]:
    return [f"{issue.location}: {issue.message}." for issue in validate_profile_semantics(profile)]


def profiles_payload_semantic_error_messages(payload: dict[str, object]) -> list[str]:
    return [f"{issue.location}: {issue.message}." for issue in validate_profiles_semantics(payload)]


def profile_from_form(existing: dict[str, object], form: dict[str, list[str]]) -> dict[str, object]:
    profile = json.loads(json.dumps(existing))
    if "scientific_name" in form:
        profile["scientific_name"] = catalog_form_string(form, "scientific_name")
    if "common_names" in form:
        profile["common_names"] = catalog_split_list(catalog_form_string(form, "common_names"))
    if "taxonomy_status" in form:
        profile["taxonomy_status"] = catalog_form_string(form, "taxonomy_status")
    if "edibility" in form:
        profile["edibility"] = catalog_form_string(form, "edibility")

    ecology = profile_nested_dict(profile, "ecology").copy()
    if "trophic_mode_id" in form:
        ecology["trophic_mode_id"] = catalog_form_string(form, "trophic_mode_id")
    for field in PROFILE_AFFINITY_GROUPS:
        if any(key.startswith(f"{field}_") for key in form):
            ecology[field] = profile_affinities_from_form(form, field)
    profile["ecology"] = ecology

    phenology = profile_nested_dict(profile, "phenology").copy()
    if "main_months" in form:
        phenology["main_months"] = profile_form_int_list(form, "main_months")
    if "secondary_months" in form:
        phenology["secondary_months"] = profile_form_int_list(form, "secondary_months")
    if "season_pattern_ids" in form:
        phenology["season_pattern_ids"] = profile_form_string_list(form, "season_pattern_ids")
    if any(key in form for key in ("delay_min", "delay_optimal_min", "delay_optimal_max", "delay_max")):
        delay = phenology.get("fruiting_delay_after_rain_days")
        delay = delay.copy() if isinstance(delay, dict) else {}
        for key, form_name in (
            ("min", "delay_min"),
            ("optimal_min", "delay_optimal_min"),
            ("optimal_max", "delay_optimal_max"),
            ("max", "delay_max"),
        ):
            if form_name in form:
                delay[key] = profile_form_number(form, form_name)
        phenology["fruiting_delay_after_rain_days"] = delay
    profile["phenology"] = phenology

    topography = profile_nested_dict(profile, "topography").copy()
    for key in ("altitude_min_m", "altitude_optimal_min_m", "altitude_optimal_max_m", "altitude_max_m"):
        if key in form:
            topography[key] = profile_form_number(form, key)
    if "preferred_aspect_ids" in form:
        topography["preferred_aspect_ids"] = profile_form_string_list(form, "preferred_aspect_ids")
    if "aspect_notes" in form:
        topography["aspect_notes"] = catalog_form_string(form, "aspect_notes")
    profile["topography"] = topography

    weather_model = profile_nested_dict(profile, "weather_model").copy()
    for block_name in ("rainfall", "temperature", "humidity", "wind"):
        block = weather_model.get(block_name)
        block = block.copy() if isinstance(block, dict) else {}
        for key, old_value in list(block.items()):
            form_name = f"{block_name}_{key}"
            if form_name in form:
                block[key] = profile_form_bool(form, form_name) if isinstance(old_value, bool) else profile_form_number(form, form_name)
        weather_model[block_name] = block
    profile["weather_model"] = weather_model

    scoring = profile_nested_dict(profile, "scoring_weights").copy()
    for key in list(scoring):
        form_name = f"score_{key}"
        if form_name in form:
            scoring[key] = profile_form_number(form, form_name)
    profile["scoring_weights"] = scoring

    confidence = profile_nested_dict(profile, "prediction_confidence").copy()
    for key in (
        "overall_confidence",
        "habitat_confidence",
        "topography_confidence",
        "phenology_confidence",
        "weather_threshold_confidence",
        "taxonomy_confidence",
        "local_calibration_status",
        "calibration_priority",
    ):
        if key in form:
            confidence[key] = catalog_form_string(form, key)
    for key in (
        "minimum_observations_for_calibration",
        "minimum_positive_observations",
        "minimum_negative_observations",
    ):
        if key in form:
            value = profile_form_number(form, key)
            confidence[key] = int(value) if value is not None else None
    if "confidence_notes" in form:
        confidence["notes"] = catalog_form_string(form, "confidence_notes")
    profile["prediction_confidence"] = confidence

    metadata = profile_nested_dict(profile, "metadata").copy()
    for key in ("profile_version", "created_at", "updated_at", "created_by", "reviewed_by"):
        if key in form:
            metadata[key] = catalog_form_string(form, key)
    if "review_status" in form:
        metadata["review_status"] = catalog_form_string(form, "review_status")
    if "source_quality" in form:
        metadata["source_quality"] = catalog_form_string(form, "source_quality")
    if "requires_human_validation" in form:
        metadata["requires_human_validation"] = profile_form_bool(form, "requires_human_validation")
    profile["metadata"] = metadata
    return finalize_species_profile_payload(profile)


def profile_parameters_from_form(existing: dict[str, object], form: dict[str, list[str]]) -> dict[str, object]:
    """Return a profile copy updated only with fields exposed by Parameters."""
    profile = json.loads(json.dumps(existing))

    ecology = profile_nested_dict(profile, "ecology").copy()
    if "trophic_mode_id" in form:
        ecology["trophic_mode_id"] = catalog_form_string(form, "trophic_mode_id")
    profile["ecology"] = ecology

    phenology = profile_nested_dict(profile, "phenology").copy()
    if "main_months" in form:
        phenology["main_months"] = profile_form_int_list(form, "main_months")
    if "secondary_months" in form:
        phenology["secondary_months"] = profile_form_int_list(form, "secondary_months")
    if "season_pattern_ids" in form:
        phenology["season_pattern_ids"] = profile_form_string_list(form, "season_pattern_ids")
    delay = phenology.get("fruiting_delay_after_rain_days")
    delay = delay.copy() if isinstance(delay, dict) else {}
    for delay_key, form_name in (
        ("min", "delay_min"),
        ("optimal_min", "delay_optimal_min"),
        ("optimal_max", "delay_optimal_max"),
        ("max", "delay_max"),
    ):
        if form_name in form:
            delay[delay_key] = profile_form_number(form, form_name)
    if any(name in form for name in ("delay_min", "delay_optimal_min", "delay_optimal_max", "delay_max")):
        phenology["fruiting_delay_after_rain_days"] = delay
    profile["phenology"] = phenology

    topography = profile_nested_dict(profile, "topography").copy()
    for key in ("altitude_min_m", "altitude_optimal_min_m", "altitude_optimal_max_m", "altitude_max_m"):
        if key in form:
            topography[key] = profile_form_number(form, key)
    if "preferred_aspect_ids" in form:
        topography["preferred_aspect_ids"] = profile_form_string_list(form, "preferred_aspect_ids")
    if "aspect_notes" in form:
        topography["aspect_notes"] = catalog_form_string(form, "aspect_notes")
    profile["topography"] = topography

    weather_model = profile_nested_dict(profile, "weather_model").copy()
    for block_name in ("rainfall", "temperature", "humidity", "wind"):
        block = weather_model.get(block_name)
        block = block.copy() if isinstance(block, dict) else {}
        block_form_names = [f"{block_name}_{key}" for key in block]
        if not any(name in form for name in block_form_names):
            weather_model[block_name] = block
            continue
        for key, old_value in list(block.items()):
            form_name = f"{block_name}_{key}"
            if isinstance(old_value, bool):
                block[key] = profile_form_bool(form, form_name)
            elif form_name in form:
                block[key] = profile_form_number(form, form_name)
        weather_model[block_name] = block
    profile["weather_model"] = weather_model

    scoring = profile_nested_dict(profile, "scoring_weights").copy()
    for key in list(scoring):
        form_name = f"score_{key}"
        if form_name in form:
            scoring[key] = profile_form_number(form, form_name)
    profile["scoring_weights"] = scoring
    return finalize_species_profile_payload(profile)


def profile_calibration_from_form(existing: dict[str, object], form: dict[str, list[str]]) -> dict[str, object]:
    """Return a profile copy updated only with calibration/confidence fields."""
    profile = json.loads(json.dumps(existing))
    confidence = profile_nested_dict(profile, "prediction_confidence").copy()
    for key in (
        "overall_confidence",
        "habitat_confidence",
        "topography_confidence",
        "phenology_confidence",
        "weather_threshold_confidence",
        "taxonomy_confidence",
        "local_calibration_status",
        "calibration_priority",
    ):
        confidence[key] = catalog_form_string(form, key)
    for key in (
        "minimum_observations_for_calibration",
        "minimum_positive_observations",
        "minimum_negative_observations",
    ):
        value = profile_form_number(form, key)
        confidence[key] = int(value) if value is not None else None
    confidence["notes"] = catalog_form_string(form, "confidence_notes")
    profile["prediction_confidence"] = confidence

    metadata = profile_nested_dict(profile, "metadata").copy()
    metadata["review_status"] = catalog_form_string(form, "review_status")
    metadata["requires_human_validation"] = profile_form_bool(form, "requires_human_validation")
    profile["metadata"] = metadata
    return finalize_species_profile_payload(profile)


def save_profile_entry_from_partial_form(
    store: object,
    species_id: str,
    form: dict[str, list[str]],
    updater: object,
    success_prefix: str,
    section: str,
) -> str:
    """Apply a partial profile form, validate, persist and return a redirect URL."""
    profile_view = mushroom_profiles_ui.normalize_profile_view(catalog_form_string(form, "view") or "v0")
    profiles_payload = store.load("profiles")
    profiles = profiles_payload.get("species_profiles")
    existing = None
    if isinstance(profiles, list):
        existing = next(
            (
                profile
                for profile in profiles
                if isinstance(profile, dict) and str(profile.get("species_id", "")) == species_id
            ),
            None,
        )
    if not isinstance(existing, dict):
        set_mushroom_profiles_flash(f"Species profile {species_id} was not found.")
        return profile_query_url(species_id, section=section, profile_view=profile_view) + "#mushroom-profile-message"
    entry = updater(existing, form)
    semantic_errors = profile_semantic_error_messages(entry)
    if semantic_errors:
        set_mushroom_profiles_flash(f"{success_prefix} were not saved: " + "; ".join(semantic_errors[:3]))
        return profile_query_url(species_id, section=section, profile_view=profile_view) + "#mushroom-profile-message"
    ok, message = replace_profile_entry(profiles_payload, species_id, entry)
    if not ok:
        set_mushroom_profiles_flash(message)
        return profile_query_url(species_id, section=section, profile_view=profile_view) + "#mushroom-profile-message"
    result = store.replace("profiles", profiles_payload)
    if result.ok:
        suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
        set_mushroom_profiles_flash(f"{success_prefix} saved for {species_id}." + suffix)
        return profile_query_url(species_id, section=section, profile_view=profile_view)
    error_text = "; ".join(message.message for message in result.errors[:3])
    set_mushroom_profiles_flash(f"{success_prefix} were not saved: " + error_text)
    return profile_query_url(species_id, section=section, profile_view=profile_view) + "#mushroom-profile-message"


def replace_profile_entry(profiles_payload: dict[str, object], species_id: str, entry: dict[str, object]) -> tuple[bool, str]:
    if str(entry.get("species_id", "")) != species_id:
        return False, "Species ID cannot be changed in the first maintenance UI."
    profiles = profiles_payload.get("species_profiles")
    if not isinstance(profiles, list):
        return False, "Profiles payload does not contain a species_profiles array."
    for index, existing in enumerate(profiles):
        if isinstance(existing, dict) and str(existing.get("species_id", "")) == species_id:
            profiles[index] = entry
            return True, f"Updated species profile {species_id}."
    return False, f"Species profile {species_id} was not found."


def duplicate_profile_entry(source: dict[str, object], new_species_id: str, scientific_name: str, common_name: str) -> dict[str, object]:
    """Clone a profile as a draft that must be reviewed before prediction use."""
    entry = json.loads(json.dumps(source))
    entry["species_id"] = new_species_id
    entry["scientific_name"] = scientific_name
    entry["common_names"] = [common_name] if common_name else [f"{scientific_name} copy"]
    now = datetime.now(UTC).date().isoformat()
    metadata = profile_nested_dict(entry, "metadata").copy()
    metadata["created_at"] = now
    metadata["updated_at"] = now
    metadata["created_by"] = "rainmapper_duplicate"
    metadata["review_status"] = "draft"
    metadata["reviewed_by"] = ""
    metadata["requires_human_validation"] = True
    entry["metadata"] = metadata
    confidence = profile_nested_dict(entry, "prediction_confidence").copy()
    confidence["local_calibration_status"] = "not_calibrated"
    confidence["calibration_priority"] = "high"
    confidence["notes"] = "Duplicated from another profile; review locally before using for prediction."
    entry["prediction_confidence"] = confidence
    return entry


render_profile_full_json_panel = mushroom_profiles_ui.render_profile_full_json_panel

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

    def require_admin_api(self) -> dict[str, object] | None:
        user = self.require_authentication()
        if not user:
            return None
        if normalize_role(str(user.get("role", "free"))) != "admin":
            self.send_json(403, {"ok": False, "error": "Administrator role required."})
            return None
        return user

    def send_mushroom_validation(self) -> None:
        store = default_store()
        seeded = store.ensure_seeded()
        errors, warnings = store.validate_current()
        self.send_json(
            200 if not errors else 422,
            {
                "ok": not errors,
                "seeded": seeded,
                "errors": [message.as_dict() for message in errors],
                "warnings": [message.as_dict() for message in warnings],
            },
        )

    def send_mushroom_export(self, query: dict[str, list[str]]) -> None:
        kind = (query.get("file") or query.get("kind") or [""])[0]
        source = (query.get("source") or ["current"])[0]
        store = default_store()
        store.ensure_seeded()
        try:
            payload = store.export_payload(kind, source=source)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
            return
        self.send_json(200, {"ok": True, **payload})

    def send_mushroom_template(self, query: dict[str, list[str]]) -> None:
        kind = (query.get("file") or query.get("kind") or [""])[0]
        store = default_store()
        store.ensure_seeded()
        try:
            payload = store.empty_template(kind)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
            return
        self.send_json(200, {"ok": True, **payload})

    def handle_mushroom_import(self) -> None:
        payload = self.read_json_payload()
        kind = str(payload.get("file", payload.get("kind", "")))
        data = payload.get("data")
        store = default_store()
        try:
            result = store.replace(kind, data)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
            return
        self.send_json(
            200 if result.ok else 422,
            {
                "ok": result.ok,
                "backup_path": str(result.backup_path) if result.backup_path else "",
                "errors": [message.as_dict() for message in result.errors],
                "warnings": [message.as_dict() for message in result.warnings],
            },
        )

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

    def render_mushroom_catalogs(self, query: dict[str, list[str]] | None = None) -> None:
        query = query or {}
        selected_group = (query.get("group") or [""])[0]
        selected_id = (query.get("id") or [""])[0]
        search = (query.get("q") or [""])[0]
        mode = (query.get("mode") or ["current"])[0]

        store = default_store()
        try:
            seeded = store.ensure_seeded()
            catalogs_payload = store.load("catalogs")
            profiles_payload = store.load("profiles")
            gis_payload = store.load("gis")
            observations_payload = store.load("observations")
            errors, warnings = store.validate_current()
        except Exception as exc:
            body = (
                '<p><a class="button-link" href="../">Back</a></p>'
                "<h1>Reference catalog</h1>"
                f'<div class="catalog-alert error"><strong>Cannot load mushroom data</strong><br>{html.escape(str(exc))}</div>'
            )
            self.send_bytes(500, html_page("Mushroom catalogs", body, auto_refresh=False), "text/html; charset=utf-8")
            return

        catalogs = catalogs_payload.get("catalogs", {}) if isinstance(catalogs_payload, dict) else {}
        catalogs = catalogs if isinstance(catalogs, dict) else {}
        rows, metrics = catalog_rows(catalogs, profiles_payload, gis_payload, observations_payload)
        selected = selected_catalog_row(rows, selected_group, selected_id)
        if selected and selected_group and not selected_id:
            selected_id = str(selected["id"])

        full_payload = catalogs_payload
        if mode == "default":
            full_payload = store.load("catalogs", source="default")
        elif mode == "template":
            full_payload = store.empty_template("catalogs")["data"]
        else:
            mode = "current"

        flash = mushroom_catalogs_flash()
        flash_html = f'<div class="catalog-alert"><strong>Status</strong><br>{html.escape(flash)}</div>' if flash else ""
        seeded_html = (
            f'<div class="catalog-alert"><strong>Seeded defaults</strong><br>{html.escape(", ".join(seeded))}</div>'
            if seeded else ""
        )
        status_label = "Flow validated" if not errors else "Validation errors"
        status_class = "ok" if not errors else "danger"
        body = f"""
        <div class="catalog-toolbar">
          <a class="button-link" href="../">Back</a>
          <a class="button-link" href="?">Refresh</a>
          <a class="button-link" href="./profiles">Mushroom species</a>
          <a class="button-link" href="./gis-mappings">GIS mappings</a>
          <form class="catalog-filter" method="get" action="">
            <input type="hidden" name="group" value="{html.escape(selected_group, quote=True)}">
            <input name="q" type="search" value="{html.escape(search, quote=True)}" placeholder="Search ID, group, label or domain">
          </form>
          <a class="button-link" href="#catalog-full-json">Import/export JSON</a>
        </div>
        <div class="control-head">
          <div>
            <h1>Catálogo maestro de referencia</h1>
            <p>Hub operativo del vocabulario del motor de predicción</p>
          </div>
          <div class="control-head-actions">
            <span class="meta">{len(catalogs)} groups · {metrics["ids"]} IDs · <span class="{status_class}">{status_label}</span></span>
          </div>
        </div>
        {flash_html}
        {seeded_html}
        {render_catalog_metric_cards(metrics, errors, warnings)}
        {render_catalog_group_chips(catalogs, rows, selected_group, search)}
        <div class="catalog-layout">
          <section>
            {render_catalog_table(rows, selected, selected_group, search)}
            {render_catalog_domain_impact(rows, selected_group)}
          </section>
          {render_catalog_detail(selected, errors, warnings, catalogs)}
        </div>
        <h2>Cross validation</h2>
        {render_catalog_alerts(errors, warnings, limit=12)}
        {render_new_catalog_entry_form(catalogs, selected_group)}
        <h2 id="catalog-full-json">JSON maintenance</h2>
        {render_catalog_full_json_panel(full_payload, mode)}
        """
        self.send_bytes(
            200,
            html_page("Mushroom reference catalogs", body, auto_refresh=False, page_class="mushroom-wide-page"),
            "text/html; charset=utf-8",
        )

    def render_mushroom_gis_mappings(self, query: dict[str, list[str]] | None = None) -> None:
        query = query or {}
        selected_key = (query.get("key") or [""])[0]
        selected_source = (query.get("source") or [""])[0]
        selected_field = (query.get("field") or [""])[0]
        search = (query.get("q") or [""])[0]
        selected_status = (query.get("status") or [""])[0]
        if selected_status not in {"mapped", "pending"}:
            selected_status = ""
        sort_by = (query.get("sort") or [""])[0]
        if sort_by not in {"source", "field", "raw_value", "mapped_ids", "status"}:
            sort_by = ""
        sort_dir = (query.get("dir") or [""])[0]
        if sort_dir not in {"asc", "desc"}:
            sort_dir = "asc" if sort_by else ""
        store = default_store()
        try:
            seeded = store.ensure_seeded()
            gis_payload = store.load("gis")
            catalogs_payload = store.load("catalogs")
            errors, warnings = store.validate_current()
        except Exception as exc:
            body = (
                '<p><a class="button-link" href="../">Back</a></p>'
                "<h1>GIS mappings</h1>"
                f'<div class="catalog-alert error"><strong>Cannot load GIS mappings</strong><br>{html.escape(str(exc))}</div>'
            )
            self.send_bytes(500, html_page("GIS mappings", body, auto_refresh=False), "text/html; charset=utf-8")
            return

        gis_payload = gis_payload if isinstance(gis_payload, dict) else {}
        catalogs_payload = catalogs_payload if isinstance(catalogs_payload, dict) else {}
        catalogs = catalogs_payload.get("catalogs", {})
        catalogs = catalogs if isinstance(catalogs, dict) else {}
        reconstruction_payload = mushroom_gis_lab.load_latest_reconstruction()
        rows = mushroom_gis_mappings_ui.mapping_rows(gis_payload, reconstruction_payload)
        filtered_rows = mushroom_gis_mappings_ui.filtered_mapping_rows(rows, selected_source, selected_field, search, selected_status)
        filtered_rows = mushroom_gis_mappings_ui.sorted_mapping_rows(filtered_rows, sort_by, sort_dir)
        selected = mushroom_gis_mappings_ui.selected_mapping_row(filtered_rows, selected_key)
        metrics = mushroom_gis_mappings_ui.mapping_metrics(rows, errors, warnings)
        flash = mushroom_gis_mappings_flash()
        is_error_flash = flash.startswith("ERROR:")
        flash_text = flash.removeprefix("ERROR:").strip() if is_error_flash else flash
        close_url = mushroom_gis_mappings_ui.mappings_query_url(
            selected_key=str(selected.get("key", "")) if isinstance(selected, dict) else "",
            source_id=selected_source,
            field=selected_field,
            search=search,
            status_filter=selected_status,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        flash_html = (
            f'<div class="catalog-alert{" error" if is_error_flash else ""}"><strong>{"Validation error" if is_error_flash else "Status"}</strong><br>{html.escape(flash_text)}</div>'
            if flash
            else ""
        )
        modal_html = (
            '<div class="modal-layer validation-modal-open">'
            '<div class="modal-backdrop"></div>'
            '<div class="modal-card validation-error-card">'
            '<h2>GIS mapping was not saved</h2>'
            f'<p>{html.escape(flash_text)}</p>'
            f'<a class="button-link" href="{html.escape(close_url, quote=True)}">Cerrar</a>'
            '</div>'
            '</div>'
            if is_error_flash
            else ""
        )
        seeded_html = (
            f'<div class="catalog-alert"><strong>Seeded defaults</strong><br>{html.escape(", ".join(seeded))}</div>'
            if seeded else ""
        )
        status_label = "Flow validated" if not errors else "Validation errors"
        status_class = "ok" if not errors else "danger"
        body = f"""
        <div class="gis-mapping-page">
        <div class="catalog-toolbar gis-mapping-toolbar">
          <a class="button-link" href="../">Back</a>
          <a class="button-link" href="?">Refresh</a>
          <a class="button-link" href="./profiles">Mushroom species</a>
          <a class="button-link" href="./catalogs">Reference catalogs</a>
          <form class="catalog-filter gis-mapping-search" method="get" action="">
            <input type="hidden" name="source" value="{html.escape(selected_source, quote=True)}">
            <input type="hidden" name="field" value="{html.escape(selected_field, quote=True)}">
            <input type="hidden" name="status" value="{html.escape(selected_status, quote=True)}">
            <input type="hidden" name="sort" value="{html.escape(sort_by, quote=True)}">
            <input type="hidden" name="dir" value="{html.escape(sort_dir, quote=True)}">
            <input name="q" type="search" value="{html.escape(search, quote=True)}" placeholder="Search source, field, raw value or mapped ID">
          </form>
          <a class="button-link gis-mapping-json-link" href="#gis-mappings-json">View JSON</a>
        </div>
        <div class="control-head gis-mapping-head">
          <div>
            <h1>GIS mappings</h1>
            <p>Conecta valores crudos de capas GIS con IDs internos del catálogo</p>
          </div>
          <div class="control-head-actions">
            <span class="meta">{metrics["mapped"]} mapped · {metrics["pending"]} pending · <span class="{status_class}">{status_label}</span></span>
          </div>
        </div>
        {modal_html}
        {flash_html}
        {seeded_html}
        <div class="catalog-layout gis-mapping-workbench">
          <section class="gis-mapping-list">
            {mushroom_gis_mappings_ui.render_mapping_metric_cards(metrics, selected_status, selected_source, selected_field, search, sort_by, sort_dir)}
            {mushroom_gis_mappings_ui.render_source_field_chips(rows, selected_source, selected_field, search, selected_status, sort_by, sort_dir)}
            {mushroom_gis_mappings_ui.render_mapping_table(filtered_rows, selected, selected_source, selected_field, search, selected_status, sort_by, sort_dir)}
          </section>
          {mushroom_gis_mappings_ui.render_mapping_detail(selected, catalogs)}
        </div>
        <h2>Cross validation</h2>
        {render_catalog_alerts(errors, warnings, limit=12)}
        <h2 id="gis-mappings-json">JSON maintenance</h2>
        {mushroom_gis_mappings_ui.render_full_json_panel(gis_payload)}
        </div>
        """
        self.send_bytes(
            200,
            html_page("GIS mappings", body, auto_refresh=False, page_class="mushroom-wide-page"),
            "text/html; charset=utf-8",
        )

    def render_mushroom_profiles(self, query: dict[str, list[str]] | None = None) -> None:
        query = query or {}
        selected_id = (query.get("id") or [""])[0]
        search = (query.get("q") or [""])[0]
        mode = (query.get("mode") or ["current"])[0]
        section = (query.get("section") or ["species"])[0]
        profile_view = mushroom_profiles_ui.normalize_profile_view((query.get("view") or ["v0"])[0])
        if section not in {"summary", "species", "observations", "evidence", "parameters", "calibration"}:
            section = "species"

        store = default_store()
        try:
            seeded = store.ensure_seeded()
            profiles_payload = store.load("profiles")
            catalogs_payload = store.load("catalogs")
            observations_payload = store.load("observations")
            evidence_decisions_payload = load_evidence_decisions(store)
            archived_payload = load_archived_profiles(store)
            archived_observations_payload = load_archived_observations(store)
            errors, warnings = store.validate_current()
        except Exception as exc:
            body = (
                '<p><a class="button-link" href="../">Back</a></p>'
                "<h1>Mushroom species</h1>"
                f'<div class="catalog-alert error"><strong>Cannot load mushroom data</strong><br>{html.escape(str(exc))}</div>'
            )
            self.send_bytes(500, html_page("Mushroom species", body, auto_refresh=False), "text/html; charset=utf-8")
            return

        profiles = profiles_payload.get("species_profiles", []) if isinstance(profiles_payload, dict) else []
        profiles = [profile for profile in profiles if isinstance(profile, dict)] if isinstance(profiles, list) else []
        archived_profiles = archived_profile_dicts(archived_payload)
        catalogs = catalogs_payload.get("catalogs", {}) if isinstance(catalogs_payload, dict) else {}
        catalogs = catalogs if isinstance(catalogs, dict) else {}
        observations_payload = observations_payload if isinstance(observations_payload, dict) else {}
        selected = mushroom_profiles_ui.selected_profile(profiles, selected_id)
        if selected:
            selected_id = str(selected.get("species_id", ""))

        full_payload = profiles_payload
        if mode == "default":
            full_payload = store.load("profiles", source="default")
        elif mode == "template":
            full_payload = store.empty_template("profiles")["data"]
        else:
            mode = "current"

        flash = mushroom_profiles_flash()
        rebuild_job_id = (query.get("rebuild_job") or [""])[0]
        refresh_query = {key: values for key, values in query.items() if key != "rebuild_job"}
        rebuild_refresh_url = "?" + urlencode(refresh_query, doseq=True) if refresh_query else profile_query_url(selected_id, search, section=section, profile_view=profile_view)
        rebuild_progress_modal = render_mushroom_rebuild_progress_modal(rebuild_job_id, rebuild_refresh_url)
        observation_form_message = flash if section == "observations" and flash.startswith("Observation was not saved: ") else ""
        flash_html = "" if observation_form_message else render_mushroom_profiles_flash(flash)
        seeded_html = (
            f'<div class="catalog-alert"><strong>Seeded defaults</strong><br>{html.escape(", ".join(seeded))}</div>'
            if seeded else ""
        )
        status_label = "Flow validated" if not errors else "Validation errors"
        status_class = "ok" if not errors else "danger"
        section_tabs = mushroom_profiles_ui.render_section_tabs(section, selected_id, search, profile_view)
        learned_model_payload = mushroom_learned_model.load_latest_model()
        model_state = mushroom_model_state.load_state()
        observations = observation_dicts_from_payload(observations_payload)
        pending_species = pending_model_species_ids(model_state, observations, learned_model_payload=learned_model_payload)
        pending_rebuild_button = ""
        if pending_species:
            pending_count = len(pending_species)
            species_count_label = mushroom_profiles_ui.ui_label("ui.species").lower()
            pending_rebuild_button = f"""
          <form class="mushroom-model-stale-form" method="post" action="">
            <input type="hidden" name="profile_action" value="rebuild_pending_model_v0">
            <input type="hidden" name="species_id" value="{html.escape(selected_id, quote=True)}">
            <input type="hidden" name="section" value="{html.escape(section, quote=True)}">
            <input type="hidden" name="view" value="{html.escape(profile_view, quote=True)}">
            <button class="mushroom-model-stale-button" type="submit" title="{html.escape(mushroom_profiles_ui.ui_label("ui.rebuild_pending_model_v0_help"), quote=True)}">
              {html.escape(mushroom_profiles_ui.ui_label("ui.model_v0_outdated"))}
              <span>{pending_count} {html.escape(species_count_label)} · {html.escape(mushroom_profiles_ui.ui_label("ui.rebuild_pending_model_v0"))}</span>
            </button>
          </form>
            """
        if section == "parameters":
            parameter_view = (query.get("parameter_view") or ["habitat"])[0]
            main_content = mushroom_profiles_ui.render_parameters_section(
                selected,
                catalogs,
                profiles,
                search,
                profile_view,
                parameter_view,
                learned_model_payload,
                observations_payload,
            )
        elif section == "calibration":
            main_content = mushroom_profiles_ui.render_calibration_section(selected, profiles, search)
        elif section == "observations":
            observation_filters = {
                "date_from": (query.get("date_from") or [""])[0],
                "date_to": (query.get("date_to") or [""])[0],
                "result": (query.get("result") or [""])[0],
                "validation": (query.get("validation") or [""])[0],
                "obs_q": (query.get("obs_q") or [""])[0],
                "obs_species": (query.get("obs_species") or [""])[0],
                "obs_id": (query.get("obs_id") or [""])[0],
                "duplicate_from": (query.get("duplicate_from") or [""])[0],
                "archive_open": (query.get("archive_open") or [""])[0],
                "sort": (query.get("sort") or ["observed_at"])[0],
                "dir": (query.get("dir") or ["desc"])[0],
            }
            main_content = mushroom_profiles_ui.render_observations_section(
                selected,
                profiles,
                catalogs,
                observations_payload,
                archived_observations_payload,
                search,
                observation_form_message,
                observation_filters,
                mushroom_gis_lab.load_latest_reconstruction(),
            )
        elif section == "evidence":
            evidence_view = (query.get("evidence_view") or ["hosts_forests"])[0]
            main_content = mushroom_profiles_ui.render_local_evidence_section(
                profile=selected,
                catalogs=catalogs,
                reconstruction_payload=mushroom_gis_lab.load_latest_reconstruction(),
                observation_features_payload=mushroom_observation_features.load_latest_features(),
                decisions_payload=evidence_decisions_payload,
                learned_model_payload=learned_model_payload,
                search=search,
                profile_view=profile_view,
                evidence_view=evidence_view,
                observations_payload=observations_payload,
                profiles=profiles,
            )
        elif section == "summary":
            main_content = (
                f"{mushroom_profiles_ui.profile_metric_cards(profiles, errors, warnings)}"
                '<section class="card profile-section-screen">'
                '<h2>Summary</h2>'
                '<p class="meta">Global profile summary remains focused on validation and species health metrics. Use Species, Parameters, Calibration and Observations for detailed maintenance.</p>'
                '</section>'
            )
        else:
            main_content = (
                f"{mushroom_profiles_ui.profile_metric_cards(profiles, errors, warnings)}"
                '<div class="profile-layout">'
                f"{mushroom_profiles_ui.render_profile_list(profiles, selected_id, search, profile_view)}"
                f"{mushroom_profiles_ui.render_profile_editor(selected, catalogs, profile_view, search)}"
                "</div>"
            )
        view_switch = mushroom_profiles_ui.render_profile_view_switch(selected_id, search, section, profile_view)
        hide_technical_panels = section == "evidence"
        full_json_link = "" if mushroom_profiles_ui.is_v0_view(profile_view) or hide_technical_panels else '<a class="button-link" href="#profiles-full-json">Import/export JSON</a>'
        full_json_section = "" if mushroom_profiles_ui.is_v0_view(profile_view) or hide_technical_panels else (
            '<h2 id="profiles-full-json">JSON maintenance</h2>'
            f"{mushroom_profiles_ui.render_profile_full_json_panel(full_payload, mode)}"
        )
        cross_validation_section = "" if hide_technical_panels else f"""
        <details class="mushroom-cross-validation">
          <summary><strong>Cross validation</strong> · {len(errors)} errors · {len(warnings)} warnings</summary>
          {render_catalog_alerts(errors, warnings, limit=12)}
        </details>
        """
        body = f"""
        <div class="catalog-toolbar">
          <a class="button-link" href="../">Back</a>
          <a class="button-link" href="{html.escape(mushroom_profiles_ui.profile_query_url(selected_id, search, section=section, profile_view=profile_view), quote=True)}">Refresh</a>
          <a class="button-link" href="./catalogs">Reference catalogs</a>
          <a class="button-link" href="./gis-mappings">GIS mappings</a>
          {view_switch}
          <form class="catalog-filter" method="get" action="">
            <input type="hidden" name="section" value="{html.escape(section, quote=True)}">
            <input type="hidden" name="id" value="{html.escape(selected_id, quote=True)}">
            <input type="hidden" name="view" value="{html.escape(profile_view, quote=True)}">
            <input name="q" type="search" value="{html.escape(search, quote=True)}" placeholder="Search species, ID, confidence or status">
          </form>
          <a class="button-link primary-link" href="#new-species-modal">New species</a>
          <a class="button-link" href="#restore-species-modal">Restore species</a>
          {full_json_link}
        </div>
        <div class="mushroom-title-tabs">
          <div class="mushroom-title-copy">
            <h1>Mantenimiento de especies</h1>
            <p>Gestiona perfiles de especies para el predictor de floradas</p>
          </div>
          <div class="mushroom-title-row">
            {pending_rebuild_button}
            <span class="meta mushroom-title-status">{len(profiles)} species · <span class="{status_class}">{status_label}</span></span>
          </div>
          <div class="mushroom-tabs-row">
            {section_tabs}
          </div>
        </div>
        {flash_html}
        {seeded_html}
        {mushroom_profiles_ui.render_new_species_form()}
        {main_content}
        {cross_validation_section}
        {render_archived_species_panel(archived_profiles)}
        {full_json_section}
        {rebuild_progress_modal}
        """
        self.send_bytes(
            200,
            html_page("Mushroom species", body, auto_refresh=False, page_class="mushroom-wide-page"),
            "text/html; charset=utf-8",
        )

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

        if path == "/mushrooms/catalogs":
            self.render_mushroom_catalogs(parse_qs(parsed.query))
            return

        if path == "/mushrooms/gis-mappings":
            self.render_mushroom_gis_mappings(parse_qs(parsed.query))
            return

        if path == "/mushrooms/profiles":
            self.render_mushroom_profiles(parse_qs(parsed.query))
            return

        if path == "/mushrooms/observation-media":
            self.serve_mushroom_observation_media(parse_qs(parsed.query))
            return

        if path == "/api/mushrooms/rebuild-status":
            query = parse_qs(parsed.query)
            job_id = (query.get("job_id") or [""])[0]
            status = get_mushroom_rebuild_job_status(job_id)
            if status is None:
                self.send_json(404, {"ok": False, "error": "Rebuild job was not found."})
                return
            self.send_json(200, {"ok": True, "job": status})
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

        if path == "/api/mushrooms/validate":
            if not self.require_admin_api():
                return
            self.send_mushroom_validation()
            return

        if path == "/api/mushrooms/export":
            if not self.require_admin_api():
                return
            self.send_mushroom_export(parse_qs(parsed.query))
            return

        if path == "/api/mushrooms/template":
            if not self.require_admin_api():
                return
            self.send_mushroom_template(parse_qs(parsed.query))
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

    def serve_mushroom_observation_media(self, query: dict[str, list[str]]) -> None:
        relative_path = (query.get("path") or [""])[0]
        file_path = observation_media_file_path(relative_path)
        if file_path is None and (query.get("observation_id") or query.get("file")):
            observation_id = (query.get("observation_id") or [""])[0]
            stored_filename = (query.get("file") or [""])[0]
            file_path = legacy_observation_media_file_path(observation_id, stored_filename)
        if file_path is None or not file_path.exists() or not file_path.is_file():
            self.send_bytes(404, b"Observation image not found.", "text/plain; charset=utf-8")
            return
        self.send_bytes(
            200,
            file_path.read_bytes(),
            content_type_for(file_path),
            headers={"Cache-Control": "private, max-age=3600"},
        )

    def read_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        payload = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
        return parse_qs(payload)

    def read_form_and_files(self) -> tuple[dict[str, list[str]], dict[str, list[dict[str, object]]]]:
        """Read urlencoded or multipart form data for server-side admin actions."""
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data"):
            return self.read_form(), {}

        form: dict[str, list[str]] = {}
        files: dict[str, list[dict[str, object]]] = {}
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
        }
        field_storage = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=environ)
        for key in field_storage.keys():
            values = field_storage[key]
            fields = values if isinstance(values, list) else [values]
            for field in fields:
                filename = getattr(field, "filename", None)
                if filename:
                    content = field.file.read()
                    files.setdefault(key, []).append(
                        {
                            "filename": Path(str(filename)).name,
                            "content": content,
                            "content_type": getattr(field, "type", "") or "",
                        }
                    )
                else:
                    form.setdefault(key, []).append(str(field.value))
        return form, files

    def form_value(self, form: dict[str, list[str]], name: str) -> str:
        values = form.get(name, [])
        return values[0] if values else ""

    def form_action_value(self, form: dict[str, list[str]], name: str) -> str:
        values = form.get(name, [])
        return values[-1] if values else ""

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

        if parsed.path == "/api/mushrooms/validate":
            if not self.require_admin_api():
                return
            self.send_mushroom_validation()
            return

        if parsed.path == "/api/mushrooms/import":
            if not self.require_admin_api():
                return
            self.handle_mushroom_import()
            return

        if parsed.path == "/api/mushrooms/observation-exif-preview":
            # This preview only inspects the uploaded bytes and does not read or
            # mutate stored mushroom data, so it must work from the backend form
            # without MapLibre/admin API credentials.
            _form, preview_files = self.read_form_and_files()
            self.send_json(200, {"ok": True, **preview_photo_exif_uploads(preview_files)})
            return

        form, files = self.read_form_and_files()
        if parsed.path.rstrip("/") == "/users":
            self.handle_user_admin_post(form)
            self.redirect_to("./users")
            return

        if parsed.path.rstrip("/") == "/mushrooms/catalogs":
            redirect_target = self.handle_mushroom_catalogs_post(form)
            query = ("?" + parsed.query) if parsed.query else ""
            self.redirect_to(redirect_target or query or "?")
            return

        if parsed.path.rstrip("/") == "/mushrooms/gis-mappings":
            redirect_target = self.handle_mushroom_gis_mappings_post(form)
            query = ("?" + parsed.query) if parsed.query else ""
            self.redirect_to(redirect_target or query or "?")
            return

        if parsed.path.rstrip("/") == "/mushrooms/profiles":
            redirect_target = self.handle_mushroom_profiles_post(form, files)
            query = ("?" + parsed.query) if parsed.query else ""
            self.redirect_to(redirect_target or query or "?")
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

    def handle_mushroom_catalogs_post(self, form: dict[str, list[str]]) -> str:
        action = self.form_action_value(form, "catalog_action")
        store = default_store()
        try:
            store.ensure_seeded()
            if action == "backup_catalog_keep":
                backup_path = store.backup_current("catalogs", keep=True)
                suffix = f" Backup: {backup_path}" if backup_path else ""
                set_mushroom_catalogs_flash("Manual reference catalog backup created." + suffix)
            elif action == "save_entry":
                group = self.form_value(form, "group")
                item_id = self.form_value(form, "id")
                entry = json.loads(self.form_value(form, "entry_json"))
                if not isinstance(entry, dict):
                    set_mushroom_catalogs_flash("Entry JSON must be an object.")
                    return ""
                catalog_payload = store.load("catalogs")
                ok, message = replace_catalog_entry(catalog_payload, group, item_id, entry)
                if not ok:
                    set_mushroom_catalogs_flash(message)
                    return ""
                result = store.replace("catalogs", catalog_payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_catalogs_flash(message + suffix)
                else:
                    error_text = "; ".join(message.message for message in result.errors[:3])
                    set_mushroom_catalogs_flash("Catalog entry was not saved: " + error_text)
            elif action == "save_entry_form":
                group = self.form_value(form, "group")
                item_id = self.form_value(form, "id")
                catalog_payload = store.load("catalogs")
                ok, message = update_catalog_entry_from_form(catalog_payload, group, item_id, form)
                if not ok:
                    set_mushroom_catalogs_flash(message)
                    return ""
                result = store.replace("catalogs", catalog_payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_catalogs_flash(message + suffix)
                else:
                    error_text = "; ".join(message.message for message in result.errors[:3])
                    set_mushroom_catalogs_flash("Catalog entry was not saved: " + error_text)
            elif action == "create_entry":
                group = self.form_value(form, "group")
                item_id = self.form_value(form, "id").strip()
                ok, message = validate_new_catalog_entry_id(group, item_id)
                if not ok:
                    set_mushroom_catalogs_flash(message)
                    return ""
                catalog_payload = store.load("catalogs")
                catalogs = catalog_payload.get("catalogs")
                if not isinstance(catalogs, dict) or not isinstance(catalogs.get(group), list):
                    set_mushroom_catalogs_flash(f"Catalog group {group} was not found.")
                    return ""
                if any(isinstance(item, dict) and str(item.get("id", "")) == item_id for item in catalogs[group]):
                    set_mushroom_catalogs_flash(f"Catalog entry {item_id} already exists.")
                    return catalog_query_url(group, item_id)
                catalogs[group].append(empty_catalog_entry(group, item_id))
                result = store.replace("catalogs", catalog_payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_catalogs_flash(f"Created catalog entry {item_id}." + suffix)
                    return catalog_query_url(group, item_id)
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_catalogs_flash("Catalog entry was not created: " + error_text)
            elif action == "save_catalog":
                payload = json.loads(self.form_value(form, "catalog_json"))
                if not isinstance(payload, dict):
                    set_mushroom_catalogs_flash("Catalog JSON must be an object.")
                    return ""
                result = store.replace("catalogs", payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_catalogs_flash("Saved full reference catalog." + suffix)
                else:
                    error_text = "; ".join(message.message for message in result.errors[:3])
                    set_mushroom_catalogs_flash("Catalog was not saved: " + error_text)
            else:
                set_mushroom_catalogs_flash("Unknown catalog maintenance action.")
        except json.JSONDecodeError as exc:
            set_mushroom_catalogs_flash(f"Invalid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}")
        except Exception as exc:
            set_mushroom_catalogs_flash(f"Catalog action failed: {exc}")
        return ""

    def handle_mushroom_gis_mappings_post(self, form: dict[str, list[str]]) -> str:
        action = self.form_action_value(form, "gis_mapping_action")
        store = default_store()
        try:
            store.ensure_seeded()
            if action == "save_exact_mapping":
                mapping, message = gis_mapping_from_form(form)
                selected_key = catalog_form_string(form, "mapping_key")
                if mapping is None:
                    set_mushroom_gis_mappings_flash("ERROR: " + message)
                    return mushroom_gis_mappings_ui.mappings_query_url(selected_key=selected_key)
                gis_payload = store.load("gis")
                if not isinstance(gis_payload, dict):
                    set_mushroom_gis_mappings_flash("ERROR: GIS mappings payload must be a JSON object.")
                    return mushroom_gis_mappings_ui.mappings_query_url(selected_key=selected_key)
                ok, upsert_message = upsert_exact_gis_mapping(gis_payload, mapping)
                if not ok:
                    set_mushroom_gis_mappings_flash("ERROR: " + upsert_message)
                    return mushroom_gis_mappings_ui.mappings_query_url(selected_key=selected_key)
                result = store.replace("gis", gis_payload)
                new_key = mushroom_gis_mappings_ui.mapping_key(
                    mapping.get("source_id", ""),
                    mapping.get("field", ""),
                    mapping.get("raw_value", ""),
                )
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_gis_mappings_flash(upsert_message + suffix)
                    return mushroom_gis_mappings_ui.mappings_query_url(selected_key=new_key)
                error_text = "; ".join(message.message for message in result.errors[:4])
                set_mushroom_gis_mappings_flash("ERROR: GIS mapping was not saved: " + error_text)
                return mushroom_gis_mappings_ui.mappings_query_url(selected_key=new_key)
            set_mushroom_gis_mappings_flash("ERROR: Unknown GIS mapping action.")
        except Exception as exc:
            set_mushroom_gis_mappings_flash(f"ERROR: GIS mapping action failed: {exc}")
        return ""

    def handle_mushroom_profiles_post(
        self,
        form: dict[str, list[str]],
        files: dict[str, list[dict[str, object]]] | None = None,
    ) -> str:
        action = self.form_action_value(form, "profile_action")
        species_id = self.form_value(form, "species_id")
        files = files or {}
        store = default_store()
        try:
            store.ensure_seeded()
            if action == "backup_profiles_keep":
                backup_path = store.backup_current("profiles", keep=True)
                suffix = f" Backup: {backup_path}" if backup_path else ""
                set_mushroom_profiles_flash("Manual species profiles backup created." + suffix)
                return profile_message_url(species_id)
            if action == "update_evidence_decision":
                group = catalog_form_string(form, "evidence_group")
                item_id = catalog_form_string(form, "evidence_item_id")
                decision = catalog_form_string(form, "evidence_decision")
                profile_view = mushroom_profiles_ui.normalize_profile_view(catalog_form_string(form, "view"))
                evidence_view = catalog_form_string(form, "evidence_view")
                ok, message = save_evidence_decision(store, species_id, group, item_id, decision)
                set_mushroom_profiles_flash(message)
                return evidence_return_url(species_id, profile_view=profile_view, evidence_view=evidence_view)
            if action == "rebuild_learned_model_v0_species":
                profile_view = mushroom_profiles_ui.normalize_profile_view(catalog_form_string(form, "view"))
                learned_payload = mushroom_learned_model.build_and_write_species_learned_model_v0(species_id)
                selected_model = None
                models = learned_payload.get("species_models")
                if isinstance(models, list):
                    selected_model = next(
                        (
                            model
                            for model in models
                            if isinstance(model, dict) and str(model.get("species_id", "") or "") == species_id
                        ),
                        None,
                    )
                selected_count = selected_model.get("observation_count", 0) if isinstance(selected_model, dict) else 0
                set_mushroom_profiles_flash(
                    "Learned v0 model rebuilt for selected species: "
                    f"{species_id} with {selected_count} used observation(s). "
                    "Weather and observation feature caches were not rebuilt."
                )
                mushroom_model_state.clear_species_pending([species_id])
                return evidence_return_url(species_id, profile_view=profile_view, evidence_view="learned_model")
            if action in {"rebuild_learned_model_v0", "rebuild_learned_model_v0_all"}:
                profile_view = mushroom_profiles_ui.normalize_profile_view(catalog_form_string(form, "view"))
                mushroom_observation_context.build_and_write_observation_weather_features()
                features_payload = mushroom_observation_features.build_and_write_observation_features_v0()
                learned_payload = mushroom_learned_model.build_and_write_learned_model_v0()
                features_summary = features_payload.get("summary") if isinstance(features_payload.get("summary"), dict) else {}
                learned_summary = learned_payload.get("summary") if isinstance(learned_payload.get("summary"), dict) else {}
                set_mushroom_profiles_flash(
                    "Learned v0 model rebuilt: "
                    f"{learned_summary.get('observations', 0)} used observation(s), "
                    f"{learned_summary.get('excluded_observations', 0)} excluded, "
                    f"{learned_summary.get('species', 0)} species. "
                    f"Joined features: {features_summary.get('observations', 0)} observation(s)."
                )
                mushroom_model_state.clear_all_pending(full_rebuild=True)
                return evidence_return_url(species_id, profile_view=profile_view, evidence_view="learned_model")
            if action == "rebuild_pending_model_v0":
                profile_view = mushroom_profiles_ui.normalize_profile_view(catalog_form_string(form, "view"))
                state = mushroom_model_state.load_state()
                observations_payload = store.load("observations")
                observations = observation_dicts_from_payload(observations_payload)
                pending_species = pending_model_species_ids(
                    state,
                    observations,
                    learned_model_payload=mushroom_learned_model.load_latest_model(),
                )
                if not pending_species:
                    set_mushroom_profiles_flash("Modelo v0 is already up to date.")
                    return profile_query_url(species_id, section=catalog_form_string(form, "section") or "parameters", profile_view=profile_view)
                selected_observation_ids = eligible_observation_ids_for_species(observations, pending_species)
                if not selected_observation_ids:
                    mushroom_model_state.clear_species_pending(pending_species)
                    set_mushroom_profiles_flash("Modelo v0 pending state cleared: no eligible observations with coordinates were found.")
                    return profile_query_url(species_id, section=catalog_form_string(form, "section") or "parameters", profile_view=profile_view)
                return_url = profile_query_url(species_id, section=catalog_form_string(form, "section") or "parameters", profile_view=profile_view)
                set_mushroom_profiles_flash(f"Modelo v0 pending rebuild started for {len(pending_species)} species.")
                job_id = start_mushroom_model_rebuild_job(
                    selected_observation_ids=selected_observation_ids,
                    reconstruction_scope="pending",
                    return_url=return_url,
                    pending_species_ids=pending_species,
                )
                return append_query_param(return_url, "rebuild_job", job_id)
            if action == "create_profile":
                new_species_id = catalog_form_string(form, "new_species_id")
                scientific_name = catalog_form_string(form, "new_scientific_name")
                common_name = catalog_form_string(form, "new_common_name")
                profiles_payload = store.load("profiles")
                profiles = profiles_payload.get("species_profiles") if isinstance(profiles_payload, dict) else None
                profiles = profiles if isinstance(profiles, list) else []
                profile_dicts = [profile for profile in profiles if isinstance(profile, dict)]
                ok, message = validate_new_species_id(new_species_id, profile_dicts)
                if not ok:
                    set_mushroom_profiles_flash("Species profile was not saved: " + message)
                    return profile_message_url()
                if not scientific_name:
                    set_mushroom_profiles_flash("Species profile was not saved: Scientific name is required.")
                    return profile_message_url()
                profiles.append(empty_species_profile(new_species_id, scientific_name, common_name))
                profiles_payload["species_profiles"] = profiles
                result = store.replace("profiles", profiles_payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(f"Created draft species profile {new_species_id}." + suffix)
                    return profile_query_url(new_species_id)
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Species profile was not saved: " + error_text)
                return profile_message_url()
            if action == "duplicate_profile":
                new_species_id = catalog_form_string(form, "duplicate_species_id")
                scientific_name = catalog_form_string(form, "duplicate_scientific_name")
                common_name = catalog_form_string(form, "duplicate_common_name")
                profiles_payload = store.load("profiles")
                profiles = profile_dicts_from_payload(profiles_payload)
                source = find_profile_by_id(profiles, species_id)
                if not source:
                    set_mushroom_profiles_flash(f"Species profile {species_id} was not found.")
                    return profile_message_url(species_id)
                ok, message = validate_new_species_id(new_species_id, profiles)
                if not ok:
                    set_mushroom_profiles_flash("Species profile was not duplicated: " + message)
                    return profile_message_url(species_id)
                if not scientific_name:
                    set_mushroom_profiles_flash("Species profile was not duplicated: Scientific name is required.")
                    return profile_message_url(species_id)
                profiles_payload["species_profiles"] = profiles + [
                    duplicate_profile_entry(source, new_species_id, scientific_name, common_name)
                ]
                semantic_errors = profiles_payload_semantic_error_messages(profiles_payload)
                if semantic_errors:
                    set_mushroom_profiles_flash("Species profile was not duplicated: " + "; ".join(semantic_errors[:3]))
                    return profile_message_url(species_id)
                result = store.replace("profiles", profiles_payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(f"Duplicated species profile {species_id} as {new_species_id}." + suffix)
                    return profile_query_url(new_species_id)
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Species profile was not duplicated: " + error_text)
                return profile_message_url(species_id)
            if action == "archive_profile":
                profiles_payload = store.load("profiles")
                profiles = profile_dicts_from_payload(profiles_payload)
                source = find_profile_by_id(profiles, species_id)
                if not source:
                    set_mushroom_profiles_flash(f"Species profile {species_id} was not found.")
                    return profile_message_url(species_id)
                archive_payload = load_archived_profiles(store)
                archived = [profile for profile in archived_profile_dicts(archive_payload) if str(profile.get("species_id", "")) != species_id]
                archived.append(json.loads(json.dumps(source)))
                archive_payload["archived_species_profiles"] = archived
                write_archived_profiles(store, archive_payload)
                profiles_payload["species_profiles"] = [
                    profile for profile in profiles if str(profile.get("species_id", "")) != species_id
                ]
                result = store.replace("profiles", profiles_payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(f"Archived species profile {species_id}." + suffix)
                    return "?"
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Species profile was not archived: " + error_text)
                return profile_message_url(species_id)
            if action == "restore_profile":
                profiles_payload = store.load("profiles")
                profiles = profile_dicts_from_payload(profiles_payload)
                if find_profile_by_id(profiles, species_id):
                    set_mushroom_profiles_flash(f"Archived species profile {species_id} was not restored: active ID already exists.")
                    return profile_message_url(species_id)
                archive_payload = load_archived_profiles(store)
                archived = archived_profile_dicts(archive_payload)
                source = find_profile_by_id(archived, species_id)
                if not source:
                    set_mushroom_profiles_flash(f"Archived species profile {species_id} was not found.")
                    return profile_message_url()
                profiles_payload["species_profiles"] = profiles + [json.loads(json.dumps(source))]
                semantic_errors = profiles_payload_semantic_error_messages(profiles_payload)
                if semantic_errors:
                    set_mushroom_profiles_flash("Archived species profile was not restored: " + "; ".join(semantic_errors[:3]))
                    return profile_message_url()
                result = store.replace("profiles", profiles_payload)
                if result.ok:
                    archive_payload["archived_species_profiles"] = [
                        profile for profile in archived if str(profile.get("species_id", "")) != species_id
                    ]
                    write_archived_profiles(store, archive_payload)
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(f"Restored archived species profile {species_id}." + suffix)
                    return profile_query_url(species_id)
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Archived species profile was not restored: " + error_text)
                return profile_message_url()
            if action == "delete_archived_profile":
                confirm_id = catalog_form_string(form, "delete_confirm_id")
                if confirm_id != species_id:
                    set_mushroom_profiles_flash("Archived species profile was not deleted: confirmation ID does not match.")
                    return profile_message_url()
                archive_payload = load_archived_profiles(store)
                archived = archived_profile_dicts(archive_payload)
                remaining = [profile for profile in archived if str(profile.get("species_id", "")) != species_id]
                if len(remaining) == len(archived):
                    set_mushroom_profiles_flash(f"Archived species profile {species_id} was not found.")
                    return profile_message_url()
                archive_payload["archived_species_profiles"] = remaining
                write_archived_profiles(store, archive_payload)
                set_mushroom_profiles_flash(f"Deleted archived species profile {species_id} permanently.")
                return profile_message_url()
            if action in {"reconstruct_observation_gis", "rebuild_observation_model_v0"}:
                reconstruction_scope = catalog_form_string(form, "gis_reconstruction_scope") or "selected"
                selected_field_name = "gis_visible_observation_ids" if reconstruction_scope == "visible" else "gis_observation_ids"
                selected_observation_ids = [
                    str(value).strip()
                    for value in form.get(selected_field_name, [])
                    if str(value).strip()
                ]
                if not selected_observation_ids:
                    set_mushroom_profiles_flash("Modelo v0 was not rebuilt: no visible observation with coordinates was selected.")
                    return observations_return_url(form, species_id, anchor="gis-reconstruction-lab")
                return_url = observations_return_url(form, species_id, anchor="gis-reconstruction-lab")
                set_mushroom_profiles_flash(f"Modelo v0 rebuild started for {len(selected_observation_ids)} observation(s).")
                job_id = start_mushroom_model_rebuild_job(
                    selected_observation_ids=selected_observation_ids,
                    reconstruction_scope=reconstruction_scope,
                    return_url=return_url,
                )
                return append_query_param(return_url, "rebuild_job", job_id)
            if action == "create_observation":
                observations_payload = store.load("observations")
                if not isinstance(observations_payload, dict):
                    set_mushroom_profiles_flash("Observation was not saved: observations payload must be an object.")
                    return observations_return_url(form, species_id, anchor="new-observation")
                observations = observations_payload.get("observations")
                if not isinstance(observations, list):
                    set_mushroom_profiles_flash("Observation was not saved: observations list is missing.")
                    return observations_return_url(form, species_id, anchor="new-observation")
                existing_rows = [row for row in observations if isinstance(row, dict)]
                uploaded_exif = [
                    item
                    for item in files.get("observation_exif_images", [])
                    if isinstance(item, dict) and item.get("filename") and item.get("content")
                ]
                if uploaded_exif:
                    imported: list[dict[str, object]] = []
                    skipped: list[str] = []
                    working_rows = list(existing_rows)
                    for item in uploaded_exif:
                        filename = str(item.get("filename", "photo"))
                        content = item.get("content")
                        if not isinstance(content, bytes):
                            skipped.append(f"{filename}: invalid upload payload")
                            continue
                        try:
                            fields = extract_photo_exif_observation_fields(filename, content)
                            exif_form = observation_form_with_exif_fields(form, fields)
                            observation = observation_payload_from_form(exif_form, working_rows)
                        except ValueError as exc:
                            skipped.append(f"{filename}: {exc}")
                            continue
                        append_observation_media(
                            observation,
                            save_observation_image_media(
                                str(observation.get("observation_id", "")),
                                item,
                                observation.get("observed_at"),
                            ),
                        )
                        imported.append(observation)
                        working_rows.append(observation)
                    observation_species_id = catalog_form_string(form, "observation_species_id") or species_id
                    if not imported:
                        set_mushroom_profiles_flash("Observation was not saved: " + "; ".join(skipped[:3]))
                        return observations_return_url(form, observation_species_id)
                    observations_payload["observations"] = observations + imported
                    metadata = observations_payload.get("metadata")
                    if isinstance(metadata, dict):
                        metadata["updated_at"] = datetime.now(UTC).date().isoformat()
                        metadata["updated_by"] = "rainmapper_ui"
                    result = store.replace("observations", observations_payload)
                    if result.ok:
                        mushroom_model_state.mark_species_pending(observation_species_ids(imported))
                        suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                        skipped_text = f" Skipped {len(skipped)} file(s): {'; '.join(skipped[:3])}." if skipped else ""
                        set_mushroom_profiles_flash(f"Created {len(imported)} EXIF observation(s).{skipped_text}" + suffix)
                        return observations_return_url(
                            form,
                            str(imported[0].get("species_id", observation_species_id)),
                            obs_id=str(imported[0].get("observation_id", "")),
                        )
                    error_text = "; ".join(message.message for message in result.errors[:3])
                    set_mushroom_profiles_flash("Observation was not saved: " + error_text)
                    return observations_return_url(form, observation_species_id)
                try:
                    observation = observation_payload_from_form(form, existing_rows)
                except ValueError as exc:
                    set_mushroom_profiles_flash("Observation was not saved: " + str(exc))
                    return observations_return_url(form, catalog_form_string(form, "observation_species_id"), anchor="new-observation")
                observations.append(observation)
                observations_payload["observations"] = observations
                metadata = observations_payload.get("metadata")
                if isinstance(metadata, dict):
                    metadata["updated_at"] = datetime.now(UTC).date().isoformat()
                    metadata["updated_by"] = "rainmapper_ui"
                result = store.replace("observations", observations_payload)
                observation_species_id = str(observation.get("species_id", ""))
                if result.ok:
                    mushroom_model_state.mark_species_pending([observation_species_id])
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(f"Created observation {observation.get('observation_id')}." + suffix)
                    return observations_return_url(form, observation_species_id, obs_id=str(observation.get("observation_id", "")))
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Observation was not saved: " + error_text)
                return observations_return_url(form, observation_species_id, anchor="new-observation")
            if action == "update_observation":
                observation_id = catalog_form_string(form, "observation_id")
                observations_payload = store.load("observations")
                if not isinstance(observations_payload, dict):
                    set_mushroom_profiles_flash("Observation was not saved: observations payload must be an object.")
                    return observations_return_url(form, species_id)
                observations = observation_dicts_from_payload(observations_payload)
                existing = find_observation_by_id(observations, observation_id)
                if not existing:
                    set_mushroom_profiles_flash(f"Observation {observation_id} was not found.")
                    return observations_return_url(form, species_id)
                uploaded_exif = [
                    item
                    for item in files.get("observation_exif_images", [])
                    if isinstance(item, dict) and item.get("filename") and item.get("content")
                ]
                exif_uploads: list[tuple[dict[str, object], dict[str, object]]] = []
                skipped: list[str] = []
                for item in uploaded_exif:
                    filename = str(item.get("filename", "photo"))
                    content = item.get("content")
                    if not isinstance(content, bytes):
                        skipped.append(f"{filename}: invalid upload payload")
                        continue
                    try:
                        exif_uploads.append((extract_photo_exif_observation_fields(filename, content), item))
                    except ValueError as exc:
                        skipped.append(f"{filename}: {exc}")
                try:
                    updated_form = observation_form_with_exif_fields(form, exif_uploads[0][0]) if exif_uploads else form
                    updated = observation_payload_from_form(updated_form, observations, existing)
                except ValueError as exc:
                    set_mushroom_profiles_flash("Observation was not saved: " + str(exc))
                    return observations_return_url(form, str(existing.get("species_id", species_id)), obs_id=observation_id)
                if uploaded_exif and not exif_uploads:
                    set_mushroom_profiles_flash("Observation was not saved: " + "; ".join(skipped[:3]))
                    return observations_return_url(form, str(existing.get("species_id", species_id)), obs_id=observation_id)
                if exif_uploads:
                    append_observation_media(
                        updated,
                        save_observation_image_media(
                            str(updated.get("observation_id", observation_id)),
                            exif_uploads[0][1],
                            updated.get("observed_at"),
                        ),
                    )
                updated_rows = [
                    updated if str(row.get("observation_id", "")) == observation_id else row
                    for row in observations
                ]
                created_from_extra_photos: list[dict[str, object]] = []
                working_rows = list(updated_rows)
                for fields, item in exif_uploads[1:]:
                    try:
                        extra_form = observation_form_with_exif_fields(form, fields)
                        extra = observation_payload_from_form(extra_form, working_rows)
                    except ValueError as exc:
                        skipped.append(f"{fields.get('filename', 'photo')}: {exc}")
                        continue
                    append_observation_media(
                        extra,
                        save_observation_image_media(
                            str(extra.get("observation_id", "")),
                            item,
                            extra.get("observed_at"),
                        ),
                    )
                    created_from_extra_photos.append(extra)
                    working_rows.append(extra)
                observations_payload["observations"] = updated_rows + created_from_extra_photos
                metadata = observations_payload.get("metadata")
                if isinstance(metadata, dict):
                    metadata["updated_at"] = datetime.now(UTC).date().isoformat()
                    metadata["updated_by"] = "rainmapper_ui"
                result = store.replace("observations", observations_payload)
                if result.ok:
                    affected_species = observation_species_ids([existing, updated] + created_from_extra_photos)
                    mushroom_model_state.mark_species_pending(affected_species)
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    imported_text = ""
                    if uploaded_exif:
                        imported_text = f" Applied EXIF from {len(exif_uploads)} image(s)."
                    if created_from_extra_photos:
                        imported_text += f" Created {len(created_from_extra_photos)} extra observation(s)."
                    if skipped:
                        imported_text += f" Skipped {len(skipped)} file(s): {'; '.join(skipped[:3])}."
                    set_mushroom_profiles_flash(f"Updated observation {observation_id}." + imported_text + suffix)
                    return observations_return_url(form, str(updated.get("species_id", species_id)), obs_id=observation_id)
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Observation was not saved: " + error_text)
                return observations_return_url(form, str(existing.get("species_id", species_id)), obs_id=observation_id)
            if action == "duplicate_observation":
                observation_id = catalog_form_string(form, "observation_id")
                observations_payload = store.load("observations")
                if not isinstance(observations_payload, dict):
                    set_mushroom_profiles_flash("Observation was not duplicated: observations payload must be an object.")
                    return observations_return_url(form, species_id)
                observations = observation_dicts_from_payload(observations_payload)
                source = find_observation_by_id(observations, observation_id)
                if not source:
                    set_mushroom_profiles_flash(f"Observation {observation_id} was not found.")
                    return observations_return_url(form, species_id)
                set_mushroom_profiles_flash(f"Loaded observation {observation_id} as a new unsaved observation template.")
                return observations_return_url(
                    form,
                    str(source.get("species_id", species_id)),
                    anchor="duplicate-observation",
                    duplicate_from=observation_id,
                )
            if action == "import_observation_exif_images":
                observations_payload = store.load("observations")
                if not isinstance(observations_payload, dict):
                    set_mushroom_profiles_flash("EXIF images were not imported: observations payload must be an object.")
                    return observations_return_url(form, species_id)
                observations = observation_dicts_from_payload(observations_payload)
                uploaded = [
                    item
                    for item in files.get("exif_images", [])
                    if isinstance(item, dict) and item.get("filename") and item.get("content")
                ]
                imported: list[dict[str, object]] = []
                skipped: list[str] = []
                working_rows = list(observations)
                for item in uploaded:
                    filename = str(item.get("filename", "photo"))
                    content = item.get("content")
                    if not isinstance(content, bytes):
                        skipped.append(f"{filename}: invalid upload payload")
                        continue
                    try:
                        fields = extract_photo_exif_observation_fields(filename, content)
                        observation = photo_exif_observation_payload(form, working_rows, fields)
                    except ValueError as exc:
                        skipped.append(f"{filename}: {exc}")
                        continue
                    append_observation_media(
                        observation,
                        save_observation_image_media(
                            str(observation.get("observation_id", "")),
                            item,
                            observation.get("observed_at"),
                        ),
                    )
                    imported.append(observation)
                    working_rows.append(observation)
                import_species_id = catalog_form_string(form, "observation_species_id") or species_id
                if not uploaded:
                    set_mushroom_profiles_flash("EXIF images were not imported: no image files were selected.")
                    return observations_return_url(form, import_species_id)
                if not imported:
                    set_mushroom_profiles_flash("EXIF images were not imported: " + "; ".join(skipped[:3]))
                    return observations_return_url(form, import_species_id)
                observations_payload["observations"] = observations + imported
                metadata = observations_payload.get("metadata")
                if isinstance(metadata, dict):
                    metadata["updated_at"] = datetime.now(UTC).date().isoformat()
                    metadata["updated_by"] = "rainmapper_ui"
                result = store.replace("observations", observations_payload)
                imported_species_id = str(imported[0].get("species_id", import_species_id))
                if result.ok:
                    mushroom_model_state.mark_species_pending(observation_species_ids(imported))
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    skipped_text = f" Skipped {len(skipped)} files: {'; '.join(skipped[:3])}." if skipped else ""
                    set_mushroom_profiles_flash(f"Imported {len(imported)} EXIF observations.{skipped_text}" + suffix)
                    return observations_return_url(form, imported_species_id, obs_id=str(imported[0].get("observation_id", "")))
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("EXIF images were not imported: " + error_text)
                return observations_return_url(form, imported_species_id)
            if action == "archive_observation":
                observation_id = catalog_form_string(form, "observation_id")
                observations_payload = store.load("observations")
                observations = observation_dicts_from_payload(observations_payload)
                source = find_observation_by_id(observations, observation_id)
                if not source:
                    set_mushroom_profiles_flash(f"Observation {observation_id} was not found.")
                    return observations_return_url(form, species_id, archive_open=True, obs_id="")
                archived_payload = load_archived_observations(store)
                archived = [
                    row
                    for row in observation_dicts_from_payload(archived_payload)
                    if str(row.get("observation_id", "")) != observation_id
                ]
                archived.append(json.loads(json.dumps(source)))
                archived_payload["observations"] = archived
                observations_payload["observations"] = [
                    row for row in observations if str(row.get("observation_id", "")) != observation_id
                ]
                result = store.replace("observations", observations_payload)
                if result.ok:
                    write_archived_observations(store, archived_payload)
                    mushroom_model_state.mark_species_pending([str(source.get("species_id", species_id))])
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(f"Archived observation {observation_id}." + suffix)
                    return observations_return_url(form, str(source.get("species_id", species_id)), anchor="archived-observations", archive_open=True, obs_id="")
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Observation was not archived: " + error_text)
                return observations_return_url(form, species_id, archive_open=True, obs_id="")
            if action == "restore_observation":
                observation_id = catalog_form_string(form, "observation_id")
                observations_payload = store.load("observations")
                observations = observation_dicts_from_payload(observations_payload)
                if find_observation_by_id(observations, observation_id):
                    set_mushroom_profiles_flash(f"Archived observation {observation_id} was not restored: active ID already exists.")
                    return observations_return_url(form, species_id, anchor="archived-observations", archive_open=True)
                archived_payload = load_archived_observations(store)
                archived = observation_dicts_from_payload(archived_payload)
                source = find_observation_by_id(archived, observation_id)
                if not source:
                    set_mushroom_profiles_flash(f"Archived observation {observation_id} was not found.")
                    return observations_return_url(form, species_id, anchor="archived-observations", archive_open=True)
                observations_payload["observations"] = observations + [json.loads(json.dumps(source))]
                result = store.replace("observations", observations_payload)
                if result.ok:
                    archived_payload["observations"] = [
                        row for row in archived if str(row.get("observation_id", "")) != observation_id
                    ]
                    write_archived_observations(store, archived_payload)
                    mushroom_model_state.mark_species_pending([str(source.get("species_id", species_id))])
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(f"Restored observation {observation_id}." + suffix)
                    return observations_return_url(form, str(source.get("species_id", species_id)), obs_id=observation_id)
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Observation was not restored: " + error_text)
                return observations_return_url(form, species_id, anchor="archived-observations", archive_open=True)
            if action == "delete_archived_observation":
                observation_id = catalog_form_string(form, "observation_id")
                confirm_id = catalog_form_string(form, "delete_confirm_id")
                if confirm_id != observation_id:
                    set_mushroom_profiles_flash("Archived observation was not deleted: confirmation ID does not match.")
                    return observations_return_url(form, species_id, anchor="archived-observations", archive_open=True)
                archived_payload = load_archived_observations(store)
                archived = observation_dicts_from_payload(archived_payload)
                remaining = [row for row in archived if str(row.get("observation_id", "")) != observation_id]
                if len(remaining) == len(archived):
                    set_mushroom_profiles_flash(f"Archived observation {observation_id} was not found.")
                    return observations_return_url(form, species_id, anchor="archived-observations", archive_open=True)
                archived_payload["observations"] = remaining
                write_archived_observations(store, archived_payload)
                if source := find_observation_by_id(archived, observation_id):
                    mushroom_model_state.mark_species_pending([str(source.get("species_id", species_id))])
                set_mushroom_profiles_flash(f"Deleted archived observation {observation_id} permanently.")
                return observations_return_url(form, species_id, anchor="archived-observations", archive_open=True)
            if action == "save_profile_json":
                entry = json.loads(self.form_value(form, "profile_json"))
                if not isinstance(entry, dict):
                    set_mushroom_profiles_flash("Species profile JSON must be an object.")
                    return profile_save_return_url(species_id, form, message=True)
                entry = finalize_species_profile_payload(entry)
                semantic_errors = profile_semantic_error_messages(entry)
                if semantic_errors:
                    set_mushroom_profiles_flash("Species profile was not saved: " + "; ".join(semantic_errors[:3]))
                    return profile_save_return_url(species_id, form, message=True)
                profiles_payload = store.load("profiles")
                ok, message = replace_profile_entry(profiles_payload, species_id, entry)
                if not ok:
                    set_mushroom_profiles_flash(message)
                    return profile_save_return_url(species_id, form, message=True)
                result = store.replace("profiles", profiles_payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(message + suffix)
                    return profile_save_return_url(species_id, form)
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Species profile was not saved: " + error_text)
                return profile_save_return_url(species_id, form, message=True)
            elif action == "save_profile_form":
                profiles_payload = store.load("profiles")
                profiles = profiles_payload.get("species_profiles")
                existing = None
                if isinstance(profiles, list):
                    existing = next(
                        (
                            profile
                            for profile in profiles
                            if isinstance(profile, dict) and str(profile.get("species_id", "")) == species_id
                        ),
                        None,
                    )
                if not isinstance(existing, dict):
                    set_mushroom_profiles_flash(f"Species profile {species_id} was not found.")
                    return profile_save_return_url(species_id, form, message=True)
                entry = profile_from_form(existing, form)
                semantic_errors = profile_semantic_error_messages(entry)
                if semantic_errors:
                    set_mushroom_profiles_flash("Species profile was not saved: " + "; ".join(semantic_errors[:3]))
                    return profile_save_return_url(species_id, form, message=True)
                ok, message = replace_profile_entry(profiles_payload, species_id, entry)
                if not ok:
                    set_mushroom_profiles_flash(message)
                    return profile_save_return_url(species_id, form, message=True)
                result = store.replace("profiles", profiles_payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash(message + suffix)
                    return profile_save_return_url(species_id, form)
                error_text = "; ".join(message.message for message in result.errors[:3])
                set_mushroom_profiles_flash("Species profile was not saved: " + error_text)
                return profile_save_return_url(species_id, form, message=True)
            elif action == "save_profile_parameters":
                return save_profile_entry_from_partial_form(
                    store,
                    species_id,
                    form,
                    profile_parameters_from_form,
                    "Parameter changes",
                    "parameters",
                )
            elif action == "save_profile_calibration":
                return save_profile_entry_from_partial_form(
                    store,
                    species_id,
                    form,
                    profile_calibration_from_form,
                    "Calibration settings",
                    "calibration",
                )
            elif action == "save_profiles":
                payload = json.loads(self.form_value(form, "profiles_json"))
                if not isinstance(payload, dict):
                    set_mushroom_profiles_flash("Profiles JSON must be an object.")
                    return profile_message_url(species_id)
                semantic_errors = profiles_payload_semantic_error_messages(payload)
                if semantic_errors:
                    set_mushroom_profiles_flash("Profiles were not saved: " + "; ".join(semantic_errors[:3]))
                    return profile_message_url(species_id)
                result = store.replace("profiles", payload)
                if result.ok:
                    suffix = f" Backup: {result.backup_path}" if result.backup_path else ""
                    set_mushroom_profiles_flash("Saved full species profiles." + suffix)
                else:
                    error_text = "; ".join(message.message for message in result.errors[:3])
                    set_mushroom_profiles_flash("Profiles were not saved: " + error_text)
                    return profile_message_url(species_id)
            else:
                set_mushroom_profiles_flash("Unknown species maintenance action.")
                return profile_message_url(species_id)
        except json.JSONDecodeError as exc:
            set_mushroom_profiles_flash(f"Invalid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}")
            return profile_message_url(species_id)
        except Exception as exc:
            set_mushroom_profiles_flash(f"Species action failed: {exc}")
            return profile_message_url(species_id)
        return profile_query_url(species_id) if species_id else "?"

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
          <a class="button-link" href="./mushrooms/catalogs">Mushroom catalogs</a>
          <a class="button-link" href="./mushrooms/profiles">Mushroom species</a>
          <a class="button-link" href="./mushrooms/gis-mappings">GIS mappings</a>
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
        legacy_www_enabled = publish_legacy_www_enabled()
        leaflet_url = cache_busted_url("/local/rainmapper-leaflet/index.html") if legacy_www_enabled else ""
        maplibre_url = cache_busted_url("/protected/maplibre/index.html")
        heatmap_maplibre_url = cache_busted_url("/local/rainmapper-maplibre-heatmap/index.html") if legacy_www_enabled and PUBLIC_MAPLIBRE_HEATMAP_PATH.exists() else ""
        aemet_maplibre_url = cache_busted_url("/local/rainmapper-maplibre-aemet/index.html") if PUBLIC_MAPLIBRE_AEMET_PATH.exists() else ""
        bokeh_21d_url = cache_busted_url("/local/Plots/rain_21d.html") if legacy_www_enabled else ""
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
          <div class="card"><span class="label">Legacy public publishing</span><span class="value">{"Enabled" if legacy_www_enabled else "Disabled"}</span></div>
          <div class="card"><span class="label">Leaflet viewer</span><span class="value">{html.escape(leaflet_url or "Disabled")}</span></div>
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
            f'<div class="card"><span class="label">Leaflet viewer</span><span class="value">{html.escape(leaflet_url or "Disabled")}</span></div>'
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
    try:
        seeded = default_store().ensure_seeded()
        if seeded:
            print(f"Seeded mushroom data defaults: {', '.join(seeded)}", flush=True)
    except Exception as exc:
        print(f"WARNING: could not seed mushroom data defaults: {exc}", flush=True)

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
