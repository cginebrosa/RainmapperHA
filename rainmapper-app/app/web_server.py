from __future__ import annotations

import argparse
import csv
import html
import json
import mimetypes
import os
import re
import shutil
import signal
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
PUBLIC_DATA_PATH = Path("/app/PublicData")
PUBLIC_PLOTS_PATH = Path("/config/www/Plots")
PUBLIC_PLOTS_TMP_PATH = Path("/config/www/.rainmapper-plots-tmp")
LEAFLET_VIEWER_ASSETS_PATH = Path("/app/leaflet-viewer")
PUBLIC_LEAFLET_PATH = Path("/config/www/rainmapper-leaflet")
PUBLIC_LEAFLET_TMP_PATH = Path("/config/www/.rainmapper-leaflet-tmp")
REMOVED_LEGACY_MOBILE_PATH = Path("/config/www/rainmapper-mobile")
MAPLIBRE_VIEWER_ASSETS_PATH = Path("/app/maplibre-viewer")
PUBLIC_MAPLIBRE_PATH = Path("/config/www/rainmapper-maplibre")
PUBLIC_MAPLIBRE_TMP_PATH = Path("/config/www/.rainmapper-maplibre-tmp")
LOG_PATH = Path("/share/rainmapper/last_run.log")
STATUS_PATH = Path("/share/rainmapper/status.txt")
STATIONS_PATH = Path("/app/stations.txt")
WUNDERGROUND_STATIONS_DB_PATH = Path("/app/Data/estacions_wunderground.csv")

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


def html_page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="5">
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
        "Rainmapper.py",
        "--create_meteoclimatic",
        env("RAINMAPPER_CREATE_METEOCLIMATIC", "true"),
        "--create_meteocat",
        env("RAINMAPPER_CREATE_METEOCAT", "true"),
        "--create_wunderground",
        env("RAINMAPPER_CREATE_WUNDERGROUND", "true"),
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
        env("RAINMAPPER_MAX_THREADS", "1"),
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
        return ["python", "Rainmapper_Client.py"]
    if action == "all":
        return update_command + ["&&", "python", "Rainmapper_Client.py"]
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
        return True, "Publishing viewers to /local/rainmapper-leaflet/index.html and /local/rainmapper-maplibre/index.html is disabled."

    if not Path("/config").exists():
        return False, "Cannot publish viewers: /config is not available in this container."

    if not LEAFLET_VIEWER_ASSETS_PATH.exists():
        return False, "Cannot publish Leaflet viewer: Leaflet viewer assets are missing."

    PUBLIC_DATA_PATH.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        [
            "python",
            "tomap_to_geojson.py",
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

    viewer_config = {}
    config_js = "window.RAINMAPPER_CONFIG = " + json.dumps(viewer_config) + ";\n"
    (PUBLIC_LEAFLET_TMP_PATH / "config.js").write_text(config_js)

    data_path = PUBLIC_LEAFLET_TMP_PATH / "data"
    data_path.mkdir()
    copied = 0
    for source_path in sorted(PUBLIC_DATA_PATH.glob("*.geojson")):
        shutil.copy2(source_path, data_path / source_path.name)
        copied += 1

    shutil.rmtree(PUBLIC_LEAFLET_PATH, ignore_errors=True)
    PUBLIC_LEAFLET_TMP_PATH.rename(PUBLIC_LEAFLET_PATH)
    shutil.rmtree(REMOVED_LEGACY_MOBILE_PATH, ignore_errors=True)

    if not MAPLIBRE_VIEWER_ASSETS_PATH.exists():
        return False, "Cannot publish MapLibre viewer: MapLibre viewer assets are missing."

    PUBLIC_MAPLIBRE_TMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PUBLIC_MAPLIBRE_TMP_PATH, ignore_errors=True)
    PUBLIC_MAPLIBRE_TMP_PATH.mkdir(parents=True, exist_ok=True)

    for asset_name in ("index.html", "app.js", "style.css"):
        shutil.copy2(MAPLIBRE_VIEWER_ASSETS_PATH / asset_name, PUBLIC_MAPLIBRE_TMP_PATH / asset_name)
    (PUBLIC_MAPLIBRE_TMP_PATH / "config.js").write_text(config_js)

    maplibre_data_path = PUBLIC_MAPLIBRE_TMP_PATH / "data"
    maplibre_data_path.mkdir()
    for source_path in sorted(PUBLIC_DATA_PATH.glob("*.geojson")):
        shutil.copy2(source_path, maplibre_data_path / source_path.name)

    shutil.rmtree(PUBLIC_MAPLIBRE_PATH, ignore_errors=True)
    PUBLIC_MAPLIBRE_TMP_PATH.rename(PUBLIC_MAPLIBRE_PATH)

    published_at = datetime.now(get_timezone()).isoformat(timespec="seconds")
    message = (
        f"Published mobile viewers with {copied} GeoJSON file(s) to "
        f"/local/rainmapper-leaflet/index.html and /local/rainmapper-maplibre/index.html at {published_at}."
    )
    log_file.write(f"=== {message} ===\n")
    log_file.flush()
    with RUN_LOCK:
        previous_message = RUN_STATE["last_publish_message"]
        RUN_STATE["last_published_at"] = published_at
        RUN_STATE["last_publish_message"] = f"{previous_message} {message}".strip()
    print(message, flush=True)
    return True, message


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
            finally:
                set_current_process(None)
            print(f"Rainmapper step '{current_action}' finished with exit code {exit_code}.", flush=True)
            if exit_code != 0:
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
        log_file.write(f"=== finished with exit code {exit_code} at {finished.isoformat(timespec='seconds')} ===\n")
        log_file.write(f"=== duration {duration} ===\n")

    message = "Finished successfully." if exit_code == 0 else f"Finished with exit code {exit_code}."
    print(f"Rainmapper action '{action}' finished with exit code {exit_code} in {duration}.", flush=True)
    with RUN_LOCK:
        RUN_STATE.update(
            {
                "running": False,
                "finished_at": datetime.now(get_timezone()).isoformat(timespec="seconds"),
                "duration": format_duration(RUN_STATE["started_at"], datetime.now(get_timezone()).isoformat(timespec="seconds")),
                "exit_code": str(exit_code),
                "last_message": message,
                "current_step": "Idle" if exit_code == 0 else "Finished with error",
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

    def redirect_home(self) -> None:
        self.send_response(303)
        self.send_header("Location", "./")
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
        self.send_bytes(200, html_page("App settings", body), "text/html; charset=utf-8")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            self.render_index()
            return

        if path == "/settings":
            self.render_settings()
            return

        if path.startswith("/file/"):
            self.serve_plot(path.removeprefix("/file/"))
            return

        self.send_bytes(
            404,
            html_page("Not found", "<h1>Not found</h1><p>This Rainmapper page does not exist.</p>"),
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
        form = self.read_form()
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
        leaflet_url = cache_busted_url("/local/rainmapper-leaflet/index.html")
        maplibre_url = cache_busted_url("/local/rainmapper-maplibre/index.html")
        bokeh_21d_url = cache_busted_url("/local/Plots/rain_21d.html")

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
            <div class="card"><span class="label">Last published</span><span class="value">{html.escape(last_published_at)}</span></div>
          </div>
        </div>
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
            f'<a class="button-link" href="{html.escape(bokeh_21d_url, quote=True)}" target="_top">Open Bokeh 21 days</a>'
            "</div>"
            '<h2 id="maps">Maps</h2>'
            f"{self.render_map_list()}"
            "<h2>Last log</h2>"
            f"<pre>{html.escape(read_log())}</pre>"
        )
        self.send_bytes(200, html_page("Rainmapper", body), "text/html; charset=utf-8")

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
