#!/usr/bin/env sh
set -eu

CONFIG_PATH="/data/options.json"
SHARE_ROOT="/share/rainmapper"
IGNORE_STATIONS_TOMAP_FILE="$SHARE_ROOT/ignore_stations_tomap.txt"

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
  print_blue "Last rains history: ${LAST_RAINS_HISTORY_VALUE}"
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

rm -rf /app/Data /app/Tomap /app/Plots /app/PublicData /app/stations.txt /app/ignore_stations_tomap.txt
ln -s "$SHARE_ROOT/Data" /app/Data
ln -s "$SHARE_ROOT/Tomap" /app/Tomap
ln -s "$SHARE_ROOT/Plots" /app/Plots
ln -s "$SHARE_ROOT/PublicData" /app/PublicData
ln -s "$SHARE_ROOT/stations.txt" /app/stations.txt
ln -s "$IGNORE_STATIONS_TOMAP_FILE" /app/ignore_stations_tomap.txt

MODE="$(option mode serve)"
TIMEZONE="$(option timezone Europe/Madrid)"
SCHEDULE_ENABLED_VALUE="$(option schedule_enabled false)"
SCHEDULE_TIME_VALUE="$(option schedule_time 23:50)"
SCHEDULE_DAYS_VALUE="$(option schedule_days all)"
SCHEDULED_ACTION_VALUE="$(option scheduled_action all)"
CREATE_METEOCLIMATIC_VALUE="$(option create_meteoclimatic true)"
CREATE_METEOCAT_VALUE="$(option create_meteocat true)"
CREATE_WUNDERGROUND_VALUE="$(option create_wunderground true)"
DAYS_INIT_VALUE="$(option days_init -7)"
DAYS_END_VALUE="$(option days_end 0)"
NOMAPS_VALUE="$(option nomaps false)"
NOTOTALS_VALUE="$(option nototals false)"
DAYS_BUCKET_VALUE="$(option days_bucket 10)"
METEOCAT_REQUEST_TIMEOUT_VALUE="$(option meteocat_request_timeout 30)"
METEOCAT_MAX_ATTEMPTS_VALUE="$(option meteocat_max_attempts 3)"
MAX_THREADS_VALUE="$(option max_threads 1)"
MAX_ATTEMPTS_VALUE="$(option max_attempts 3)"
WUNDERGROUND_FULL_LOG_VALUE="$(option wunderground_full_log false)"
METEOCLIMATIC_PATTERN_VALUE="$(option meteoclimatic_pattern ESCAT)"
LAST_RAINS_HISTORY_VALUE="$(option last_rains_history 30)"
PUBLISH_TO_WWW_VALUE="$(option publish_to_www true)"
GMAP_API_KEY_VALUE="$(option gmap_api_key '')"

export TZ="$TIMEZONE"
export GMAP_API_KEY="$GMAP_API_KEY_VALUE"
export RAINMAPPER_MODE="$MODE"
export RAINMAPPER_IGNORE_STATIONS_TOMAP_FILE="/app/ignore_stations_tomap.txt"
export RAINMAPPER_TIMEZONE="$TIMEZONE"
export RAINMAPPER_SCHEDULE_ENABLED="$SCHEDULE_ENABLED_VALUE"
export RAINMAPPER_SCHEDULE_TIME="$SCHEDULE_TIME_VALUE"
export RAINMAPPER_SCHEDULE_DAYS="$SCHEDULE_DAYS_VALUE"
export RAINMAPPER_SCHEDULED_ACTION="$SCHEDULED_ACTION_VALUE"
export RAINMAPPER_CREATE_METEOCLIMATIC="$CREATE_METEOCLIMATIC_VALUE"
export RAINMAPPER_CREATE_METEOCAT="$CREATE_METEOCAT_VALUE"
export RAINMAPPER_CREATE_WUNDERGROUND="$CREATE_WUNDERGROUND_VALUE"
export RAINMAPPER_DAYS_INIT="$DAYS_INIT_VALUE"
export RAINMAPPER_DAYS_END="$DAYS_END_VALUE"
export RAINMAPPER_NOMAPS="$NOMAPS_VALUE"
export RAINMAPPER_NOTOTALS="$NOTOTALS_VALUE"
export RAINMAPPER_DAYS_BUCKET="$DAYS_BUCKET_VALUE"
export RAINMAPPER_METEOCAT_REQUEST_TIMEOUT="$METEOCAT_REQUEST_TIMEOUT_VALUE"
export RAINMAPPER_METEOCAT_MAX_ATTEMPTS="$METEOCAT_MAX_ATTEMPTS_VALUE"
export RAINMAPPER_MAX_THREADS="$MAX_THREADS_VALUE"
export RAINMAPPER_MAX_ATTEMPTS="$MAX_ATTEMPTS_VALUE"
export RAINMAPPER_WUNDERGROUND_FULL_LOG="$WUNDERGROUND_FULL_LOG_VALUE"
export RAINMAPPER_METEOCLIMATIC_PATTERN="$METEOCLIMATIC_PATTERN_VALUE"
export RAINMAPPER_LAST_RAINS_HISTORY="$LAST_RAINS_HISTORY_VALUE"
export RAINMAPPER_PUBLISH_TO_WWW="$PUBLISH_TO_WWW_VALUE"
cd /app

print_startup_banner

run_update() {
  echo "Starting Rainmapper update..."
  set +e
  python Rainmapper.py \
    --create_meteoclimatic "$CREATE_METEOCLIMATIC_VALUE" \
    --create_meteocat "$CREATE_METEOCAT_VALUE" \
    --create_wunderground "$CREATE_WUNDERGROUND_VALUE" \
    --days_init "$DAYS_INIT_VALUE" \
    --days_end "$DAYS_END_VALUE" \
    --nomaps "$NOMAPS_VALUE" \
    --nototals "$NOTOTALS_VALUE" \
    --days_bucket "$DAYS_BUCKET_VALUE" \
    --meteocat_request_timeout "$METEOCAT_REQUEST_TIMEOUT_VALUE" \
    --meteocat_max_attempts "$METEOCAT_MAX_ATTEMPTS_VALUE" \
    --max_threads "$MAX_THREADS_VALUE" \
    --max_attempts "$MAX_ATTEMPTS_VALUE" \
    --wunderground_full_log "$WUNDERGROUND_FULL_LOG_VALUE" \
    --meteoclimatic_pattern "$METEOCLIMATIC_PATTERN_VALUE"
  update_exit_code="$?"
  set -e
  echo "Rainmapper update finished with exit code ${update_exit_code}."
  return "$update_exit_code"
}

run_maps() {
  echo "Starting Rainmapper maps..."
  python Rainmapper_Client.py
  echo "Starting Rainmapper GeoJSON..."
  python tomap_to_geojson.py \
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
    python Rainmapper.py --help
    ;;
  update|once)
    run_update
    ;;
  maps)
    run_maps
    ;;
  serve)
    echo "Starting Rainmapper map server..."
    exec python web_server.py --host 0.0.0.0 --port 8099
    ;;
  all)
    update_exit_code=0
    run_update || update_exit_code="$?"
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
