#!/usr/bin/env bash
set -euo pipefail

# Docker-based functional check for the offline map pipeline.
#
# This script is intentionally separate from smoke-test.sh because it requires
# Docker and can be slower than pure unit tests. It does not call external
# weather services and it does not mount docker-data, so it is safe to run before
# larger refactors such as unifying the root and Home Assistant app code.
#
# Covered flow:
#   1. Build the local Docker image.
#   2. Create temporary Rainmapper-like incremental CSV files.
#   3. Run rainmapper_core.tomap inside the container.
#   4. Run rainmapper_core.geojson inside the container.
#   5. Validate Tomap and GeoJSON outputs from the host.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${PYTHON_BIN:-}" ]; then
  :
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/rainmapper-docker-offline.XXXXXX")"
KEEP_DOCKER_TEST_IMAGE="${KEEP_DOCKER_TEST_IMAGE:-0}"
cleanup() {
  rm -rf "$TMP_ROOT"
  if [ "$KEEP_DOCKER_TEST_IMAGE" != "1" ]; then
    docker image rm rainmapperha:test >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

DATA_DIR="$TMP_ROOT/Data"
TOMAP_DIR="$TMP_ROOT/Tomap"
PLOTS_DIR="$TMP_ROOT/Plots"
PUBLIC_DATA_DIR="$TMP_ROOT/PublicData"
IGNORE_FILE="$TMP_ROOT/ignore_stations_tomap.txt"

mkdir -p "$DATA_DIR" "$TOMAP_DIR" "$PLOTS_DIR" "$PUBLIC_DATA_DIR"
printf '# No ignored stations in this offline fixture\n' > "$IGNORE_FILE"

echo "Preparing offline fixture in $TMP_ROOT"
"$PYTHON_BIN" - "$DATA_DIR" <<'PY'
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


def row(station_code, reading_date, rain, max_temp, lat="41.1", lon="2.1"):
    reading_datetime = datetime.combine(reading_date, datetime.min.time()).replace(hour=8)
    return {
        "Codi Estació": station_code,
        "Data Lectura": reading_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "Estació": f"Station {station_code}",
        "Comarca": "Test",
        "Municipi": "Testville",
        "Provincia": "Test",
        "Altitud": "100",
        "Latitud": lat,
        "Longitud": lon,
        "Ultima Lectura": reading_datetime.strftime("%Y/%m/%d %H:%M:%S"),
        "Variable": "Precipitació",
        "Total": rain,
        "Unitat": "mm",
        "Data Local": reading_date.strftime("%Y%m%d"),
        "Hora Local": "08:00:00",
        "max_temp_celsius": max_temp,
        "min_temp_celsius": 12.0,
        "max_humidity_percent": 80.0,
        "min_humidity_percent": 45.0,
    }


data_dir = Path(sys.argv[1])
today = date.today()
yesterday = today - timedelta(days=1)

fixtures = {
    "Meteocat_incremental.csv": [
        row("Z1", today, 5.5, 24.0, lat="41.10", lon="2.10"),
    ],
    "Meteoclimatic_incremental.csv": [
        row("ESCAT2500000025720B", today, 8.2, 18.0, lat="41.20", lon="2.20"),
    ],
    "Wunderground_incremental.csv": [
        row("IGUILS3", yesterday, 1.1, 16.0, lat="41.30", lon="2.30"),
    ],
}

for filename, rows in fixtures.items():
    pd.DataFrame(rows).to_csv(data_dir / filename, decimal=",", index=False)
PY

echo "Building local Docker image rainmapperha:test"
docker compose -f rainmapper-local/docker-compose.yml build rainmapper

echo "Running offline Tomap and GeoJSON generation inside Docker"
docker run --rm \
  -v "$DATA_DIR:/app/Data" \
  -v "$TOMAP_DIR:/app/Tomap" \
  -v "$PLOTS_DIR:/app/Plots" \
  -v "$PUBLIC_DATA_DIR:/app/PublicData" \
  -v "$IGNORE_FILE:/app/ignore_stations_tomap.txt" \
  -e RAINMAPPER_IGNORE_STATIONS_TOMAP_FILE=/app/ignore_stations_tomap.txt \
  rainmapperha:test \
  sh -eu -c '
    python -m rainmapper_core.tomap \
      --data-dir /app/Data \
      --maps-dir /app/Tomap \
      --last-rains-history 3 \
      --max-threads 2
    python -m rainmapper_core.geojson \
      --input-dir /app/Tomap \
      --output-dir /app/PublicData \
      --ignore-stations-file /app/ignore_stations_tomap.txt
  '

echo "Validating Docker-generated outputs"
"$PYTHON_BIN" - "$TOMAP_DIR" "$PUBLIC_DATA_DIR" <<'PY'
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd


tomap_dir = Path(sys.argv[1])
public_data_dir = Path(sys.argv[2])
today_text = date.today().strftime("%d/%m/%Y")

expected_tomap = {
    "01_Tomap_Last_day.csv",
    "02_Tomap_Last_week.csv",
    "03_Tomap_Last_two_weeks.csv",
    "04_Tomap_Last_three_weeks.csv",
    "05_Tomap_Last_month.csv",
    "06_Tomap_Last_two_months.csv",
    "07_Tomap_Last_three_months.csv",
    "Last3_rains.csv",
}
actual_tomap = {path.name for path in tomap_dir.glob("*.csv")}
if actual_tomap != expected_tomap:
    raise SystemExit(f"Unexpected Tomap files: {sorted(actual_tomap)}")

last_day = pd.read_csv(tomap_dir / "01_Tomap_Last_day.csv")
if set(last_day["Codi Estació"]) != {"Z1", "ESCAT2500000025720B"}:
    raise SystemExit(f"Unexpected 1-day stations: {last_day['Codi Estació'].tolist()}")
if "Data_Pluja_04" in last_day.columns:
    raise SystemExit("Tomap contains more last-rain columns than requested")

z1 = last_day[last_day["Codi Estació"] == "Z1"].iloc[0]
if z1["Total"] != 5.5:
    raise SystemExit(f"Unexpected Z1 total: {z1['Total']}")
if z1["Data_Pluja_01"] != today_text:
    raise SystemExit(f"Unexpected Z1 latest rain date: {z1['Data_Pluja_01']}")

expected_geojson = {"01d.geojson", "07d.geojson", "14d.geojson", "21d.geojson", "30d.geojson", "60d.geojson", "90d.geojson"}
actual_geojson = {path.name for path in public_data_dir.glob("*.geojson")}
if actual_geojson != expected_geojson:
    raise SystemExit(f"Unexpected GeoJSON files: {sorted(actual_geojson)}")

with open(public_data_dir / "01d.geojson", encoding="utf-8") as handle:
    day_data = json.load(handle)
day_sources = {
    feature["properties"]["Codi Estació"]: feature["properties"]["Source"]
    for feature in day_data["features"]
}
if day_sources != {"Z1": "Meteocat", "ESCAT2500000025720B": "Meteoclimatic"}:
    raise SystemExit(f"Unexpected 1-day sources: {day_sources}")

with open(public_data_dir / "07d.geojson", encoding="utf-8") as handle:
    week_data = json.load(handle)
week_sources = {
    feature["properties"]["Codi Estació"]: feature["properties"]["Source"]
    for feature in week_data["features"]
}
if week_sources.get("IGUILS3") != "Wunderground":
    raise SystemExit(f"Wunderground station missing from 7-day GeoJSON: {week_sources}")
PY

echo "Docker offline functional test passed."
