#!/usr/bin/env sh
set -eu

CONFIG_PATH="/data/options.json"
SHARE_ROOT="/share/rainmapper"
IGNORE_STATIONS_TOMAP_FILE="$SHARE_ROOT/ignore_stations_tomap.txt"
USERS_JSON_FILE="$SHARE_ROOT/users.json"
DEVICES_FILE="$SHARE_ROOT/devices.json"

option() {
  key="$1"
  default="$2"
  python3 - "$CONFIG_PATH" "$key" "$default" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
key = sys.argv[2]
default = sys.argv[3]

try:
    data = json.loads(config_path.read_text()) if config_path.exists() else {}
except Exception:
    data = {}

value = data.get(key, default)
if isinstance(value, bool):
    print("true" if value else "false")
else:
    print(value)
PY
}

print_startup_banner() {
  system_name="unknown"
  system_version="unknown"
  if [ -f /etc/os-release ]; then
    system_name="$(python3 - <<'PY'
from pathlib import Path
data = {}
for line in Path("/etc/os-release").read_text().splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        data[key] = value.strip('"')
print(data.get("PRETTY_NAME") or data.get("NAME") or "unknown")
PY
)"
    system_version="$system_name"
  fi

  python_version="$(python --version 2>&1)"
  architecture="$(uname -m)"

  blue="\033[36m"
  green="\033[32m"
  reset="\033[0m"

  print_blue() {
    printf "%b%s%b\n" "$blue" "$1" "$reset"
  }

  print_green() {
    printf "%b%s%b\n" "$green" "$1" "$reset"
  }

  print_blue "-------------------------------------------------------------------------------"
  print_blue ""
  print_blue "App: Rainmapper"
  print_blue "Home Assistant app for weather data updates and generated rain maps"
  print_blue ""
  print_blue "-------------------------------------------------------------------------------"
  print_blue "App version: ${RAINMAPPER_APP_VERSION:-unknown}"
  print_blue "Mode: ${MODE}"
  print_blue "Schedule enabled: ${SCHEDULE_ENABLED_VALUE}"
  print_blue "Schedule time(s): ${SCHEDULE_TIME_VALUE}"
  print_blue "Schedule days: ${SCHEDULE_DAYS_VALUE}"
  print_blue "Scheduled action: ${SCHEDULED_ACTION_VALUE}"
  print_blue "Timezone: ${TIMEZONE}"
  print_blue "Mushroom UI language: ${UI_LANGUAGE_VALUE}"
  print_blue "Last rains history: ${LAST_RAINS_HISTORY_VALUE}"
  print_blue "Legacy public viewers: ${PUBLISH_TO_WWW_VALUE}"
  print_blue "External worker connections: ${EXTERNAL_WORKER_CONNECTIONS_ENABLED_VALUE}"
  print_blue "External rebuilds and promotion: ${EXTERNAL_WORKER_REBUILDS_ENABLED_VALUE}"
  print_blue "MapLibre hover zoom: ${MAPLIBRE_HOVER_ZOOM_VALUE}"
  print_blue "MapLibre heatmap defaults: ${MAPLIBRE_HEATMAP_WEIGHT_CURVE_VALUE}, opacity ${MAPLIBRE_HEATMAP_OPACITY_VALUE}%, radius ${MAPLIBRE_HEATMAP_RADIUS_VALUE}%, intensity ${MAPLIBRE_HEATMAP_INTENSITY_VALUE}%"
  print_blue "Meteocat request timeout: ${METEOCAT_REQUEST_TIMEOUT_VALUE}s"
  print_blue "Meteocat max attempts: ${METEOCAT_MAX_ATTEMPTS_VALUE}"
  print_blue ""
  print_blue "System: ${system_version} (${architecture})"
  print_blue "Python: ${python_version}"
  print_blue "Data path: ${SHARE_ROOT}"
  print_blue "Maps path: ${SHARE_ROOT}/Plots"
  print_blue "Mobile data path: ${SHARE_ROOT}/PublicData"
  print_blue ""
  print_blue "-------------------------------------------------------------------------------"
  print_green "Please share the above information when looking for help or support,"
  print_green "for example in GitHub issues, forums or chat."
  print_blue "-------------------------------------------------------------------------------"
  printf "%b" "$reset"
}

mkdir -p "$SHARE_ROOT/Data" "$SHARE_ROOT/Tomap" "$SHARE_ROOT/Plots" "$SHARE_ROOT/PublicData"

if [ ! -f "$SHARE_ROOT/stations.txt" ]; then
  cp /app/stations.example.txt "$SHARE_ROOT/stations.txt"
fi

if [ ! -f "$IGNORE_STATIONS_TOMAP_FILE" ]; then
  printf "%s\n" "# Stations ignored when generating GeoJSON / new maps" > "$IGNORE_STATIONS_TOMAP_FILE"
fi

if [ ! -f "$USERS_JSON_FILE" ]; then
  cp /app/users.example.json "$USERS_JSON_FILE"
fi

if [ ! -f "$DEVICES_FILE" ]; then
  printf "%s\n" '{"devices": {}}' > "$DEVICES_FILE"
fi

rm -rf /app/Data /app/Tomap /app/Plots /app/PublicData /app/stations.txt /app/ignore_stations_tomap.txt
ln -s "$SHARE_ROOT/Data" /app/Data
ln -s "$SHARE_ROOT/Tomap" /app/Tomap
ln -s "$SHARE_ROOT/Plots" /app/Plots
ln -s "$SHARE_ROOT/PublicData" /app/PublicData
ln -s "$SHARE_ROOT/stations.txt" /app/stations.txt
ln -s "$IGNORE_STATIONS_TOMAP_FILE" /app/ignore_stations_tomap.txt

MODE="$(option mode serve)"
TIMEZONE="$(option timezone Europe/Madrid)"
UI_LANGUAGE_VALUE="$(option ui_language en)"
SCHEDULE_ENABLED_VALUE="$(option schedule_enabled false)"
SCHEDULE_TIME_VALUE="$(option schedule_time 23:50)"
SCHEDULE_DAYS_VALUE="$(option schedule_days all)"
SCHEDULED_ACTION_VALUE="$(option scheduled_action all)"
CREATE_METEOCLIMATIC_VALUE="$(option create_meteoclimatic true)"
CREATE_METEOCAT_VALUE="$(option create_meteocat true)"
CREATE_WUNDERGROUND_VALUE="$(option create_wunderground true)"
CREATE_AEMET_VALUE="$(option create_aemet false)"
DAYS_INIT_VALUE="$(option days_init -7)"
DAYS_END_VALUE="$(option days_end 0)"
BACKFILL_MONTHS_ENABLED_VALUE="$(option backfill_months_enabled false)"
MONTHS_INIT_VALUE="$(option months_init -48)"
MONTHS_END_VALUE="$(option months_end 0)"
MONTHS_INTERVAL_VALUE="$(option months_interval 3)"
BACKFILL_PAUSE_SECONDS_VALUE="$(option backfill_pause_seconds 5)"
BACKFILL_STATION_FILTER_VALUE="$(option backfill_station_filter '')"
NOMAPS_VALUE="$(option nomaps false)"
NOTOTALS_VALUE="$(option nototals false)"
DAYS_BUCKET_VALUE="$(option days_bucket 10)"
METEOCAT_REQUEST_TIMEOUT_VALUE="$(option meteocat_request_timeout 30)"
METEOCAT_MAX_ATTEMPTS_VALUE="$(option meteocat_max_attempts 3)"
MAX_THREADS_VALUE="$(option max_threads 3)"
MAX_ATTEMPTS_VALUE="$(option max_attempts 3)"
WUNDERGROUND_DAILY_API_VALUE="$(option wunderground_daily_api true)"
WUNDERGROUND_FULL_LOG_VALUE="$(option wunderground_full_log false)"
METEOCLIMATIC_PATTERN_VALUE="$(option meteoclimatic_pattern ESCAT)"
LAST_RAINS_HISTORY_VALUE="$(option last_rains_history 30)"
MAPLIBRE_HOVER_ZOOM_VALUE="$(option maplibre_hover_zoom 6.0)"
MAPLIBRE_HEATMAP_WEIGHT_CURVE_VALUE="$(option maplibre_heatmap_weight_curve soft)"
MAPLIBRE_HEATMAP_OPACITY_VALUE="$(option maplibre_heatmap_opacity 80)"
MAPLIBRE_HEATMAP_RADIUS_VALUE="$(option maplibre_heatmap_radius 90)"
MAPLIBRE_HEATMAP_INTENSITY_VALUE="$(option maplibre_heatmap_intensity 70)"
MAPLIBRE_ESTIMATED_FIELD_ENABLED_VALUE="$(option maplibre_estimated_field_enabled false)"
MAPLIBRE_ESTIMATED_FIELD_OPACITY_VALUE="$(option maplibre_estimated_field_opacity 90)"
MAPLIBRE_ESTIMATED_FIELD_RADIUS_VALUE="$(option maplibre_estimated_field_radius medium)"
MAPLIBRE_ESTIMATED_FIELD_QUALITY_VALUE="$(option maplibre_estimated_field_quality medium)"
MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_VALUE="$(option maplibre_estimated_field_smoothing balanced)"
MAPLIBRE_ESTIMATED_FIELD_ALTITUDE_CORRECTION_VALUE="$(option maplibre_estimated_field_altitude_correction false)"
MAPLIBRE_ESTIMATED_FIELD_DEM_ZOOM_VALUE="$(option maplibre_estimated_field_dem_zoom 9)"
MAPLIBRE_ESTIMATED_FIELD_RADIUS_SMALL_KM_VALUE="$(option maplibre_estimated_field_radius_small_km 10)"
MAPLIBRE_ESTIMATED_FIELD_RADIUS_MEDIUM_KM_VALUE="$(option maplibre_estimated_field_radius_medium_km 15)"
MAPLIBRE_ESTIMATED_FIELD_RADIUS_LARGE_KM_VALUE="$(option maplibre_estimated_field_radius_large_km 25)"
MAPLIBRE_ESTIMATED_FIELD_MAX_RADIUS_KM_VALUE="$(option maplibre_estimated_field_max_radius_km 50)"
MAPLIBRE_ESTIMATED_FIELD_GRID_LOW_CELL_KM_VALUE="$(option maplibre_estimated_field_grid_low_cell_km 2)"
MAPLIBRE_ESTIMATED_FIELD_GRID_MEDIUM_CELL_KM_VALUE="$(option maplibre_estimated_field_grid_medium_cell_km 1)"
MAPLIBRE_ESTIMATED_FIELD_GRID_HIGH_CELL_KM_VALUE="$(option maplibre_estimated_field_grid_high_cell_km 0.5)"
MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_SMOOTH_POWER_VALUE="$(option maplibre_estimated_field_smoothing_smooth_power 1)"
MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_BALANCED_POWER_VALUE="$(option maplibre_estimated_field_smoothing_balanced_power 2)"
MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_LOCAL_POWER_VALUE="$(option maplibre_estimated_field_smoothing_local_power 3)"
MAPLIBRE_ESTIMATED_FIELD_TEMPERATURE_LAPSE_RATE_VALUE="$(option maplibre_estimated_field_temperature_lapse_rate_c_per_100m 0.65)"
PUBLISH_TO_WWW_VALUE="$(option publish_to_www false)"
EXTERNAL_WORKER_CONNECTIONS_ENABLED_VALUE="$(option external_worker_connections_enabled "${RAINMAPPER_WORKER_API_ENABLED:-false}")"
EXTERNAL_WORKER_REBUILDS_ENABLED_VALUE="$(option external_worker_rebuilds_enabled "${RAINMAPPER_WORKER_OPERATIONAL_ENABLED:-false}")"
GMAP_API_KEY_VALUE="$(option gmap_api_key "${GMAP_API_KEY:-}")"
AEMET_API_KEY_VALUE="$(option aemet_api_key "${AEMET_API_KEY:-}")"

export TZ="$TIMEZONE"
export GMAP_API_KEY="$GMAP_API_KEY_VALUE"
export RAINMAPPER_MODE="$MODE"
export RAINMAPPER_IGNORE_STATIONS_TOMAP_FILE="/app/ignore_stations_tomap.txt"
export RAINMAPPER_TIMEZONE="$TIMEZONE"
export RAINMAPPER_MUSHROOM_UI_LANGUAGE="$UI_LANGUAGE_VALUE"
export RAINMAPPER_SCHEDULE_ENABLED="$SCHEDULE_ENABLED_VALUE"
export RAINMAPPER_SCHEDULE_TIME="$SCHEDULE_TIME_VALUE"
export RAINMAPPER_SCHEDULE_DAYS="$SCHEDULE_DAYS_VALUE"
export RAINMAPPER_SCHEDULED_ACTION="$SCHEDULED_ACTION_VALUE"
export RAINMAPPER_CREATE_METEOCLIMATIC="$CREATE_METEOCLIMATIC_VALUE"
export RAINMAPPER_CREATE_METEOCAT="$CREATE_METEOCAT_VALUE"
export RAINMAPPER_CREATE_WUNDERGROUND="$CREATE_WUNDERGROUND_VALUE"
export RAINMAPPER_CREATE_AEMET="$CREATE_AEMET_VALUE"
export RAINMAPPER_DAYS_INIT="$DAYS_INIT_VALUE"
export RAINMAPPER_DAYS_END="$DAYS_END_VALUE"
export RAINMAPPER_BACKFILL_MONTHS_ENABLED="$BACKFILL_MONTHS_ENABLED_VALUE"
export RAINMAPPER_MONTHS_INIT="$MONTHS_INIT_VALUE"
export RAINMAPPER_MONTHS_END="$MONTHS_END_VALUE"
export RAINMAPPER_MONTHS_INTERVAL="$MONTHS_INTERVAL_VALUE"
export RAINMAPPER_BACKFILL_PAUSE_SECONDS="$BACKFILL_PAUSE_SECONDS_VALUE"
export RAINMAPPER_NOMAPS="$NOMAPS_VALUE"
export RAINMAPPER_NOTOTALS="$NOTOTALS_VALUE"
export RAINMAPPER_DAYS_BUCKET="$DAYS_BUCKET_VALUE"
export RAINMAPPER_METEOCAT_REQUEST_TIMEOUT="$METEOCAT_REQUEST_TIMEOUT_VALUE"
export RAINMAPPER_METEOCAT_MAX_ATTEMPTS="$METEOCAT_MAX_ATTEMPTS_VALUE"
export RAINMAPPER_MAX_THREADS="$MAX_THREADS_VALUE"
export RAINMAPPER_MAX_ATTEMPTS="$MAX_ATTEMPTS_VALUE"
export RAINMAPPER_WUNDERGROUND_DAILY_API="$WUNDERGROUND_DAILY_API_VALUE"
export RAINMAPPER_WUNDERGROUND_FULL_LOG="$WUNDERGROUND_FULL_LOG_VALUE"
export RAINMAPPER_METEOCLIMATIC_PATTERN="$METEOCLIMATIC_PATTERN_VALUE"
export RAINMAPPER_LAST_RAINS_HISTORY="$LAST_RAINS_HISTORY_VALUE"
export RAINMAPPER_MAPLIBRE_HOVER_ZOOM="$MAPLIBRE_HOVER_ZOOM_VALUE"
export RAINMAPPER_MAPLIBRE_HEATMAP_WEIGHT_CURVE="$MAPLIBRE_HEATMAP_WEIGHT_CURVE_VALUE"
export RAINMAPPER_MAPLIBRE_HEATMAP_OPACITY="$MAPLIBRE_HEATMAP_OPACITY_VALUE"
export RAINMAPPER_MAPLIBRE_HEATMAP_RADIUS="$MAPLIBRE_HEATMAP_RADIUS_VALUE"
export RAINMAPPER_MAPLIBRE_HEATMAP_INTENSITY="$MAPLIBRE_HEATMAP_INTENSITY_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ENABLED="$MAPLIBRE_ESTIMATED_FIELD_ENABLED_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_OPACITY="$MAPLIBRE_ESTIMATED_FIELD_OPACITY_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS="$MAPLIBRE_ESTIMATED_FIELD_RADIUS_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_QUALITY="$MAPLIBRE_ESTIMATED_FIELD_QUALITY_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING="$MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_ALTITUDE_CORRECTION="$MAPLIBRE_ESTIMATED_FIELD_ALTITUDE_CORRECTION_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_DEM_ZOOM="$MAPLIBRE_ESTIMATED_FIELD_DEM_ZOOM_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_SMALL_KM="$MAPLIBRE_ESTIMATED_FIELD_RADIUS_SMALL_KM_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_MEDIUM_KM="$MAPLIBRE_ESTIMATED_FIELD_RADIUS_MEDIUM_KM_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_RADIUS_LARGE_KM="$MAPLIBRE_ESTIMATED_FIELD_RADIUS_LARGE_KM_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_MAX_RADIUS_KM="$MAPLIBRE_ESTIMATED_FIELD_MAX_RADIUS_KM_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_LOW_CELL_KM="$MAPLIBRE_ESTIMATED_FIELD_GRID_LOW_CELL_KM_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_MEDIUM_CELL_KM="$MAPLIBRE_ESTIMATED_FIELD_GRID_MEDIUM_CELL_KM_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_GRID_HIGH_CELL_KM="$MAPLIBRE_ESTIMATED_FIELD_GRID_HIGH_CELL_KM_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_SMOOTH_POWER="$MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_SMOOTH_POWER_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_BALANCED_POWER="$MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_BALANCED_POWER_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_LOCAL_POWER="$MAPLIBRE_ESTIMATED_FIELD_SMOOTHING_LOCAL_POWER_VALUE"
export RAINMAPPER_MAPLIBRE_ESTIMATED_FIELD_TEMPERATURE_LAPSE_RATE_C_PER_100M="$MAPLIBRE_ESTIMATED_FIELD_TEMPERATURE_LAPSE_RATE_VALUE"
export RAINMAPPER_PUBLISH_TO_WWW="$PUBLISH_TO_WWW_VALUE"
export RAINMAPPER_WORKER_API_ENABLED="$EXTERNAL_WORKER_CONNECTIONS_ENABLED_VALUE"
export RAINMAPPER_WORKER_AUTH_REQUIRED="true"
export RAINMAPPER_WORKER_OPERATIONAL_ENABLED="$EXTERNAL_WORKER_REBUILDS_ENABLED_VALUE"
export RAINMAPPER_AEMET_API_KEY="$AEMET_API_KEY_VALUE"
export RAINMAPPER_BACKFILL_STATION_FILTER="$BACKFILL_STATION_FILTER_VALUE"
cd /app

print_startup_banner

run_update() {
  echo "Starting Rainmapper update..."
  set +e
  local run_days_init="${1:-$DAYS_INIT_VALUE}"
  local run_days_end="${2:-$DAYS_END_VALUE}"
  local run_nototals="${3:-$NOTOTALS_VALUE}"
  local run_wunderground_local_start_date="${4:-}"
  local run_wunderground_local_end_date="${5:-}"
  set -- \
    python -m rainmapper_core.rainmapper \
    --create_meteoclimatic "$CREATE_METEOCLIMATIC_VALUE" \
    --create_meteocat "$CREATE_METEOCAT_VALUE" \
    --create_wunderground "$CREATE_WUNDERGROUND_VALUE" \
    --create_aemet "$CREATE_AEMET_VALUE" \
    --days_init "$run_days_init" \
    --days_end "$run_days_end" \
    --nomaps "$NOMAPS_VALUE" \
    --nototals "$run_nototals" \
    --days_bucket "$DAYS_BUCKET_VALUE" \
    --meteocat_request_timeout "$METEOCAT_REQUEST_TIMEOUT_VALUE" \
    --meteocat_max_attempts "$METEOCAT_MAX_ATTEMPTS_VALUE" \
    --max_threads "$MAX_THREADS_VALUE" \
    --max_attempts "$MAX_ATTEMPTS_VALUE" \
    --wunderground_daily_api "$WUNDERGROUND_DAILY_API_VALUE" \
    --wunderground_full_log "$WUNDERGROUND_FULL_LOG_VALUE" \
    --backfill_station_filter "$BACKFILL_STATION_FILTER_VALUE" \
    --meteoclimatic_pattern "$METEOCLIMATIC_PATTERN_VALUE"
  if [ -n "$run_wunderground_local_start_date" ] && [ -n "$run_wunderground_local_end_date" ]; then
    # Monthly backfill windows are local calendar windows. Pass explicit
    # Wunderground dates so Europe/Madrid midnight is not converted to the
    # previous UTC day. Normal updates intentionally keep days_init/days_end so
    # early-month runs reread the previous month and close late WU totals.
    set -- "$@" \
      --wunderground_local_start_date "$run_wunderground_local_start_date" \
      --wunderground_local_end_date "$run_wunderground_local_end_date"
  fi
  "$@"
  update_exit_code="$?"
  set -e
  echo "Rainmapper update finished with exit code ${update_exit_code}."
  return "$update_exit_code"
}

month_backfill_windows() {
  python -c 'from datetime import date, timedelta
import calendar
import os

def int_env(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default

def add_months(day, offset):
    month_index = day.year * 12 + day.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)

def month_end(day):
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])

today = date.today()
start = int_env("RAINMAPPER_MONTHS_INIT", -48)
end = int_env("RAINMAPPER_MONTHS_END", 0)
interval = max(1, abs(int_env("RAINMAPPER_MONTHS_INTERVAL", 3)))
step = interval if start <= end else -interval
current = start
while (step > 0 and current <= end) or (step < 0 and current >= end):
    window_end = current + step
    if step > 0:
        window_end = min(window_end - 1, end)
    else:
        window_end = max(window_end + 1, end)
    start_date = add_months(today, current)
    end_date = today if window_end == 0 else month_end(add_months(today, window_end))
    days_init = (start_date - today).days
    days_end = (end_date - today).days
    print(f"{days_init} {days_end} {current} {window_end} {start_date.isoformat()} {end_date.isoformat()}")
    current = window_end + (1 if step > 0 else -1)'
}

backup_incrementals_for_backfill() {
  local backup_stamp
  backup_stamp="$(date +%Y%m%d_%H%M%S)"
  local backup_dir="/app/Data/backups/backfill_incrementals_${backup_stamp}"
  mkdir -p "$backup_dir"
  local found=0
  for incremental_file in /app/Data/*_incremental.csv; do
    if [ -f "$incremental_file" ]; then
      cp "$incremental_file" "$backup_dir/"
      found=1
    fi
  done
  if [ "$found" -eq 1 ]; then
    echo "Backed up incremental CSV files to ${backup_dir}."
  else
    echo "No incremental CSV files found to back up before monthly backfill."
  fi
}

run_update_windows() {
  if [ "$BACKFILL_MONTHS_ENABLED_VALUE" != "true" ]; then
    run_update
    return "$?"
  fi

  local final_code=0
  local first_window=1
  echo "Monthly backfill enabled: months_init=${MONTHS_INIT_VALUE}, months_end=${MONTHS_END_VALUE}, months_interval=${MONTHS_INTERVAL_VALUE}, pause=${BACKFILL_PAUSE_SECONDS_VALUE}s."
  backup_incrementals_for_backfill
  while read -r window_days_init window_days_end window_months_init window_months_end window_start_date window_end_date; do
    [ -n "$window_days_init" ] || continue
    if [ "$first_window" -eq 0 ]; then
      echo "Waiting ${BACKFILL_PAUSE_SECONDS_VALUE}s before next monthly backfill window."
      sleep "$BACKFILL_PAUSE_SECONDS_VALUE"
    fi
    first_window=0
    echo "Running monthly backfill window months ${window_months_init}..${window_months_end} as ${window_start_date}..${window_end_date}."
    run_update "$window_days_init" "$window_days_end" true "$window_start_date" "$window_end_date"
    window_code="$?"
    if [ "$window_code" -eq 1 ]; then
      return 1
    fi
    if [ "$window_code" -eq 2 ] && [ "$final_code" -eq 0 ]; then
      final_code=2
    fi
  done <<EOF
$(month_backfill_windows)
EOF
  return "$final_code"
}

run_maps() {
  echo "Starting Rainmapper maps..."
  echo "Rebuilding Rainmapper Tomap..."
  python -m rainmapper_core.tomap \
    --data-dir /app/Data \
    --maps-dir /app/Tomap \
    --last-rains-history "$LAST_RAINS_HISTORY_VALUE" \
    --max-threads "$MAX_THREADS_VALUE" \
    --include-aemet true
  echo "Rainmapper Tomap finished."
  if [ "$PUBLISH_TO_WWW_VALUE" = "true" ]; then
    python -m rainmapper_core.bokeh_maps
  else
    echo "Skipping Rainmapper Bokeh maps."
  fi
  echo "Starting Rainmapper GeoJSON..."
  python -m rainmapper_core.geojson \
    --input-dir /app/Tomap \
    --output-dir /app/PublicData \
    --ignore-stations-file "$IGNORE_STATIONS_TOMAP_FILE"
  if [ -f /app/Data/source_status.json ]; then
    cp /app/Data/source_status.json /app/PublicData/source_status.json
  fi
  echo "Rainmapper GeoJSON finished."
  echo "Rainmapper maps finished."
}

case "$MODE" in
  help)
    python -m rainmapper_core.rainmapper --help
    ;;
  update|once)
    run_update_windows
    ;;
  maps)
    run_maps
    ;;
  serve)
    echo "Starting Rainmapper map server..."
    exec python web_server.py --host 0.0.0.0 --port 8099 --worker-host 0.0.0.0 --worker-port 8100
    ;;
  all)
    update_exit_code=0
    run_update_windows || update_exit_code="$?"
    update_exit_code="${update_exit_code:-0}"
    if [ "$update_exit_code" -eq 1 ]; then
      exit 1
    fi
    run_maps
    if [ "$update_exit_code" -eq 2 ]; then
      exit 2
    fi
    ;;
  *)
    echo "Invalid mode: ${MODE}. Use help, update, maps, all or serve."
    exit 1
    ;;
esac
