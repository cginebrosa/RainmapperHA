#!/usr/bin/env sh
set -eu

CONFIG_PATH="/data/options.json"
SHARE_ROOT="/share/rainmapper"

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

  printf "%b" "$blue"
  cat <<EOF
-------------------------------------------------------------------------------

App: Rainmapper
Home Assistant app for weather data updates and generated rain maps

-------------------------------------------------------------------------------
App version: ${RAINMAPPER_APP_VERSION:-unknown}
Mode: ${MODE}
Schedule enabled: ${SCHEDULE_ENABLED_VALUE}
Schedule time: ${SCHEDULE_TIME_VALUE}
Scheduled action: ${SCHEDULED_ACTION_VALUE}
Timezone: ${TIMEZONE}

System: ${system_version} (${architecture})
Python: ${python_version}
Data path: ${SHARE_ROOT}
Maps path: ${SHARE_ROOT}/Plots

-------------------------------------------------------------------------------
EOF
  printf "%b" "$green"
  cat <<EOF
Please share the above information when looking for help or support,
for example in GitHub issues, forums or chat.
EOF
  printf "%b" "$blue"
  cat <<EOF
-------------------------------------------------------------------------------
EOF
  printf "%b" "$reset"
}

mkdir -p "$SHARE_ROOT/Data" "$SHARE_ROOT/Tomap" "$SHARE_ROOT/Plots"

if [ ! -f "$SHARE_ROOT/stations.txt" ]; then
  cp /app/stations.example.txt "$SHARE_ROOT/stations.txt"
fi

rm -rf /app/Data /app/Tomap /app/Plots /app/stations.txt
ln -s "$SHARE_ROOT/Data" /app/Data
ln -s "$SHARE_ROOT/Tomap" /app/Tomap
ln -s "$SHARE_ROOT/Plots" /app/Plots
ln -s "$SHARE_ROOT/stations.txt" /app/stations.txt

MODE="$(option mode serve)"
TIMEZONE="$(option timezone Europe/Madrid)"
SCHEDULE_ENABLED_VALUE="$(option schedule_enabled false)"
SCHEDULE_TIME_VALUE="$(option schedule_time 23:50)"
SCHEDULED_ACTION_VALUE="$(option scheduled_action all)"
CREATE_METEOCLIMATIC_VALUE="$(option create_meteoclimatic true)"
CREATE_METEOCAT_VALUE="$(option create_meteocat true)"
CREATE_WUNDERGROUND_VALUE="$(option create_wunderground true)"
DAYS_INIT_VALUE="$(option days_init -7)"
DAYS_END_VALUE="$(option days_end 0)"
NOMAPS_VALUE="$(option nomaps false)"
NOTOTALS_VALUE="$(option nototals false)"
DAYS_BUCKET_VALUE="$(option days_bucket 10)"
MAX_THREADS_VALUE="$(option max_threads 1)"
MAX_ATTEMPTS_VALUE="$(option max_attempts 3)"
METEOCLIMATIC_PATTERN_VALUE="$(option meteoclimatic_pattern ESCAT)"
GMAP_API_KEY_VALUE="$(option gmap_api_key '')"

export TZ="$TIMEZONE"
export GMAP_API_KEY="$GMAP_API_KEY_VALUE"
export RAINMAPPER_MODE="$MODE"
export RAINMAPPER_TIMEZONE="$TIMEZONE"
export RAINMAPPER_SCHEDULE_ENABLED="$SCHEDULE_ENABLED_VALUE"
export RAINMAPPER_SCHEDULE_TIME="$SCHEDULE_TIME_VALUE"
export RAINMAPPER_SCHEDULED_ACTION="$SCHEDULED_ACTION_VALUE"
export RAINMAPPER_CREATE_METEOCLIMATIC="$CREATE_METEOCLIMATIC_VALUE"
export RAINMAPPER_CREATE_METEOCAT="$CREATE_METEOCAT_VALUE"
export RAINMAPPER_CREATE_WUNDERGROUND="$CREATE_WUNDERGROUND_VALUE"
export RAINMAPPER_DAYS_INIT="$DAYS_INIT_VALUE"
export RAINMAPPER_DAYS_END="$DAYS_END_VALUE"
export RAINMAPPER_NOMAPS="$NOMAPS_VALUE"
export RAINMAPPER_NOTOTALS="$NOTOTALS_VALUE"
export RAINMAPPER_DAYS_BUCKET="$DAYS_BUCKET_VALUE"
export RAINMAPPER_MAX_THREADS="$MAX_THREADS_VALUE"
export RAINMAPPER_MAX_ATTEMPTS="$MAX_ATTEMPTS_VALUE"
export RAINMAPPER_METEOCLIMATIC_PATTERN="$METEOCLIMATIC_PATTERN_VALUE"
cd /app

print_startup_banner

run_update() {
  echo "Starting Rainmapper update..."
  python Rainmapper.py \
    --create_meteoclimatic "$CREATE_METEOCLIMATIC_VALUE" \
    --create_meteocat "$CREATE_METEOCAT_VALUE" \
    --create_wunderground "$CREATE_WUNDERGROUND_VALUE" \
    --days_init "$DAYS_INIT_VALUE" \
    --days_end "$DAYS_END_VALUE" \
    --nomaps "$NOMAPS_VALUE" \
    --nototals "$NOTOTALS_VALUE" \
    --days_bucket "$DAYS_BUCKET_VALUE" \
    --max_threads "$MAX_THREADS_VALUE" \
    --max_attempts "$MAX_ATTEMPTS_VALUE" \
    --meteoclimatic_pattern "$METEOCLIMATIC_PATTERN_VALUE"
  echo "Rainmapper update finished."
}

run_maps() {
  echo "Starting Rainmapper maps..."
  python Rainmapper_Client.py
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
    python web_server.py --host 0.0.0.0 --port 8099
    ;;
  all)
    run_update
    run_maps
    ;;
  *)
    echo "Invalid mode: ${MODE}. Use help, update, maps, all or serve."
    exit 1
    ;;
esac
