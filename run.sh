#!/usr/bin/env sh
set -eu

cd /app

MODE="${MODE:-${RAINMAPPER_MODE:-once}}"
SCHEDULE_TIME="${SCHEDULE_TIME:-${RAINMAPPER_SCHEDULE_TIME:-23:50}}"
TIMEZONE="${TIMEZONE:-${RAINMAPPER_TIMEZONE:-${TZ:-Europe/Madrid}}}"

CREATE_METEOCLIMATIC_VALUE="${CREATE_METEOCLIMATIC:-${RAINMAPPER_CREATE_METEOCLIMATIC:-true}}"
CREATE_METEOCAT_VALUE="${CREATE_METEOCAT:-${RAINMAPPER_CREATE_METEOCAT:-true}}"
CREATE_WUNDERGROUND_VALUE="${CREATE_WUNDERGROUND:-${RAINMAPPER_CREATE_WUNDERGROUND:-true}}"
DAYS_INIT_VALUE="${DAYS_INIT:-${RAINMAPPER_DAYS_INIT:--7}}"
DAYS_END_VALUE="${DAYS_END:-${RAINMAPPER_DAYS_END:-0}}"
NOMAPS_VALUE="${NOMAPS:-${RAINMAPPER_NOMAPS:-false}}"
NOTOTALS_VALUE="${NOTOTALS:-${RAINMAPPER_NOTOTALS:-false}}"
DAYS_BUCKET_VALUE="${DAYS_BUCKET:-${RAINMAPPER_DAYS_BUCKET:-10}}"
MAX_THREADS_VALUE="${MAX_THREADS:-${RAINMAPPER_MAX_THREADS:-1}}"
MAX_ATTEMPTS_VALUE="${MAX_ATTEMPTS:-${RAINMAPPER_MAX_ATTEMPTS:-3}}"
METEOCLIMATIC_PATTERN_VALUE="${METEOCLIMATIC_PATTERN:-${RAINMAPPER_METEOCLIMATIC_PATTERN:-ESCAT}}"

export TZ="$TIMEZONE"

run_update() {
  echo "Starting Rainmapper..."

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

  echo "Rainmapper finished."
}

run_maps() {
  echo "Starting Rainmapper maps..."
  python Rainmapper_Client.py
  echo "Rainmapper maps finished."
}

seconds_until_schedule() {
  python - "$SCHEDULE_TIME" "$TIMEZONE" <<'PY'
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

schedule_time = sys.argv[1]
timezone_name = sys.argv[2]

try:
    hour_text, minute_text = schedule_time.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError
except ValueError:
    print(f"Invalid RAINMAPPER_SCHEDULE_TIME: {schedule_time}. Use HH:MM.", file=sys.stderr)
    sys.exit(1)

try:
    tz = ZoneInfo(timezone_name)
except Exception as exc:
    print(f"Invalid RAINMAPPER_TIMEZONE: {timezone_name}: {exc}", file=sys.stderr)
    sys.exit(1)

now = datetime.now(tz)
target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

if target <= now:
    target = target + timedelta(days=1)

print(max(0, int((target - now).total_seconds())))
PY
}

case "$MODE" in
  help)
    python Rainmapper.py --help
    ;;
  once|update)
    run_update
    ;;
  maps)
    run_maps
    ;;
  all)
    run_update
    run_maps
    ;;
  schedule)
    echo "Rainmapper scheduled daily at ${SCHEDULE_TIME} (${TIMEZONE})."
    while true; do
      sleep_seconds="$(seconds_until_schedule)"
      echo "Next run in ${sleep_seconds} seconds."
      sleep "$sleep_seconds"
      run_update
    done
    ;;
  *)
    echo "Invalid MODE/RAINMAPPER_MODE: ${MODE}. Use help, once, update, maps, all or schedule."
    exit 1
    ;;
esac
