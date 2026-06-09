#!/usr/bin/env sh
set -eu

cd /app

MODE="${RAINMAPPER_MODE:-once}"
SCHEDULE_TIME="${RAINMAPPER_SCHEDULE_TIME:-23:50}"
TIMEZONE="${RAINMAPPER_TIMEZONE:-${TZ:-Europe/Madrid}}"

export TZ="$TIMEZONE"

run_rainmapper() {
  echo "Starting Rainmapper..."

  python Rainmapper.py \
    --create_meteoclimatic "${RAINMAPPER_CREATE_METEOCLIMATIC:-true}" \
    --create_meteocat "${RAINMAPPER_CREATE_METEOCAT:-true}" \
    --create_wunderground "${RAINMAPPER_CREATE_WUNDERGROUND:-true}" \
    --days_init "${RAINMAPPER_DAYS_INIT:--7}" \
    --days_end "${RAINMAPPER_DAYS_END:-0}" \
    --nomaps "${RAINMAPPER_NOMAPS:-false}" \
    --nototals "${RAINMAPPER_NOTOTALS:-false}" \
    --days_bucket "${RAINMAPPER_DAYS_BUCKET:-10}" \
    --max_threads "${RAINMAPPER_MAX_THREADS:-1}" \
    --max_attempts "${RAINMAPPER_MAX_ATTEMPTS:-3}"

  echo "Rainmapper finished."
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
  once)
    run_rainmapper
    ;;
  schedule)
    echo "Rainmapper scheduled daily at ${SCHEDULE_TIME} (${TIMEZONE})."
    while true; do
      sleep_seconds="$(seconds_until_schedule)"
      echo "Next run in ${sleep_seconds} seconds."
      sleep "$sleep_seconds"
      run_rainmapper
    done
    ;;
  *)
    echo "Invalid RAINMAPPER_MODE: ${MODE}. Use once or schedule."
    exit 1
    ;;
esac