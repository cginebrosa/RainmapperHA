#!/usr/bin/env bash
set -u

# Fast repository health check for local development. It intentionally avoids
# network, Docker runs and Home Assistant access; those are validated manually or
# with dedicated scripts. This script focuses on cheap regressions: syntax,
# version alignment, root/app synchronization and small functional fixtures.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Reuse the same sync manifest used by sync-app-files.sh so smoke checks cover
# every root source copied into the Home Assistant app package.
source "$ROOT_DIR/scripts/sync-manifest.sh"

# Prefer the project virtualenv when available, but keep the script usable on a
# fresh machine with only python3 installed.
if [ -n "${PYTHON_BIN:-}" ]; then
  :
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi

failures=0

# Run one check and keep going so the developer sees all failures at once.
run_check() {
  local label="$1"
  shift

  printf '==> %s\n' "$label"
  if "$@"; then
    printf 'OK: %s\n\n' "$label"
  else
    local status=$?
    printf 'FAIL: %s (exit %s)\n\n' "$label" "$status"
    failures=$((failures + 1))
  fi
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$command_name" >&2
    return 1
  fi
}

# Home Assistant version values are repeated in metadata and Docker labels. If
# they drift, HA updates become confusing and runtime diagnostics are misleading.
check_versions() {
  local config_version docker_label_version app_env_version

  config_version="$(sed -n 's/^version:[[:space:]]*"\([^"]*\)".*/\1/p' rainmapper-app/config.yaml | head -n 1)"
  docker_label_version="$(sed -n 's/^LABEL io\.hass\.version="\([^"]*\)".*/\1/p' rainmapper-app/Dockerfile | head -n 1)"
  app_env_version="$(sed -n 's/^ENV RAINMAPPER_APP_VERSION=\([^[:space:]]*\).*/\1/p' rainmapper-app/Dockerfile | head -n 1)"

  if [ -z "$config_version" ] || [ -z "$docker_label_version" ] || [ -z "$app_env_version" ]; then
    printf 'Could not read all Home Assistant version values.\n' >&2
    printf 'config.yaml=%s Dockerfile label=%s Dockerfile env=%s\n' "$config_version" "$docker_label_version" "$app_env_version" >&2
    return 1
  fi

  if [ "$config_version" != "$docker_label_version" ] || [ "$config_version" != "$app_env_version" ]; then
    printf 'Home Assistant versions are not aligned.\n' >&2
    printf 'config.yaml=%s Dockerfile label=%s Dockerfile env=%s\n' "$config_version" "$docker_label_version" "$app_env_version" >&2
    return 1
  fi

  printf 'Home Assistant version: %s\n' "$config_version"
}

read_ha_version() {
  sed -n 's/^version:[[:space:]]*"\([^"]*\)".*/\1/p' rainmapper-app/config.yaml | head -n 1
}

check_viewer_asset_versions() {
  local config_version stale_refs

  config_version="$(read_ha_version)"
  if [ -z "$config_version" ]; then
    printf 'Could not read Home Assistant version.\n' >&2
    return 1
  fi

  stale_refs="$(
    grep -RInE 'href="[^"]+\\?v=|src="[^"]+\\?v=' \
      leaflet-viewer/index.html \
      maplibre-viewer/index.html \
      rainmapper-app/app/rainmapper_core/viewers/leaflet-viewer/index.html \
      rainmapper-app/app/rainmapper_core/viewers/maplibre-viewer/index.html \
    | grep -v "?v=${config_version}" || true
  )"
  if [ -n "$stale_refs" ]; then
    printf 'Viewer asset cache-busters do not match Home Assistant version %s:\n%s\n' "$config_version" "$stale_refs" >&2
    return 1
  fi
}

# Root scripts are the development source of truth; rainmapper-app/app contains
# the copy that goes into the HA image. The sync script must keep them identical.
check_synced_files() {
  local file

  for file in "${RAINMAPPER_SYNC_FILES[@]}"; do
    if ! cmp -s "$file" "rainmapper-app/app/$file"; then
      printf 'File differs: %s vs rainmapper-app/app/%s\n' "$file" "$file" >&2
      return 1
    fi
  done
}

check_synced_viewers() {
  local dir

  for dir in "${RAINMAPPER_SYNC_DIRS[@]}"; do
    diff -qr -x __pycache__ -x '*.pyc' "$dir" "rainmapper-app/app/$dir"
  done
}

check_python_syntax() {
  local python_files=(
    scripts/check-history.py
    Rainmapper.py
    Rainmapper_Client.py
    tomap_to_geojson.py
    rainmapper-app/app/Rainmapper.py
    rainmapper-app/app/Rainmapper_Client.py
    rainmapper-app/app/tomap_to_geojson.py
    rainmapper-app/app/web_server.py
  )

  # Include the whole shared core package so new source-specific helpers are
  # compiled automatically when added under rainmapper_core/.
  while IFS= read -r core_file; do
    python_files+=("$core_file")
  done < <(find rainmapper_core rainmapper-app/app/rainmapper_core -name '*.py' -type f | sort)

  # Compile from source text instead of writing __pycache__ files. This avoids
  # permission issues in cloud-synced folders and keeps the repo clean.
  "$PYTHON_BIN" - "${python_files[@]}" <<'PY'
import sys
from pathlib import Path

for filename in sys.argv[1:]:
    path = Path(filename)
    source = path.read_text(encoding="utf-8")
    compile(source, filename, "exec")
PY
}

check_js_syntax() {
  node --check leaflet-viewer/app.js
  node --check leaflet-viewer/config.js
  node --check maplibre-viewer/app.js
  node --check maplibre-viewer/config.js
  node --check rainmapper-app/app/rainmapper_core/viewers/leaflet-viewer/app.js
  node --check rainmapper-app/app/rainmapper_core/viewers/leaflet-viewer/config.js
  node --check rainmapper-app/app/rainmapper_core/viewers/maplibre-viewer/app.js
  node --check rainmapper-app/app/rainmapper_core/viewers/maplibre-viewer/config.js
}

check_python_unit_tests() {
  "$PYTHON_BIN" -m unittest discover -s tests
}

check_geojson_conversion() {
  local tmp_dir input_dir output_dir ignore_file convert_log

  # Use a tiny Tomap fixture to validate ignore_stations_tomap and basic GeoJSON
  # shape without relying on real generated data.
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/rainmapper-smoke.XXXXXX")" || return 1
  input_dir="$tmp_dir/Tomap"
  output_dir="$tmp_dir/PublicData"
  ignore_file="$tmp_dir/ignore_stations_tomap.txt"
  convert_log="$tmp_dir/tomap_to_geojson.log"

  mkdir -p "$input_dir" "$output_dir"
  printf 'Codi Estació,Latitud,Longitud,Pluja\nTEST_KEEP,41.100,2.100,3.5\nTEST_DROP,41.200,2.200,9.9\n' > "$input_dir/01_Tomap_Last_day.csv"
  printf 'TEST_DROP\n' > "$ignore_file"

  if ! "$PYTHON_BIN" tomap_to_geojson.py \
    --input-dir "$input_dir" \
    --output-dir "$output_dir" \
    --ignore-stations-file "$ignore_file" > "$convert_log" 2>&1; then
    cat "$convert_log" >&2
    rm -rf "$tmp_dir"
    return 1
  fi

  if ! "$PYTHON_BIN" - "$output_dir/01d.geojson" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

features = data.get("features", [])
if data.get("type") != "FeatureCollection":
    raise SystemExit("GeoJSON root type is not FeatureCollection")
if len(features) != 1:
    raise SystemExit(f"Expected 1 feature after ignore filtering, got {len(features)}")

feature = features[0]
properties = feature.get("properties", {})
geometry = feature.get("geometry", {})
if properties.get("Codi Estació") != "TEST_KEEP":
    raise SystemExit(f"Unexpected station code: {properties.get('Codi Estació')}")
if geometry.get("type") != "Point":
    raise SystemExit(f"Unexpected geometry type: {geometry.get('type')}")
if geometry.get("coordinates") != [2.1, 41.1]:
    raise SystemExit(f"Unexpected coordinates: {geometry.get('coordinates')}")
PY
  then
    rm -rf "$tmp_dir"
    return 1
  fi

  rm -rf "$tmp_dir"
}

check_history_fixture() {
  local tmp_dir before_dir after_dir

  # Simulate a safe before/after history comparison: row counts may grow, but
  # should not shrink unless explicitly allowed.
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/rainmapper-history.XXXXXX")" || return 1
  before_dir="$tmp_dir/before/Data"
  after_dir="$tmp_dir/after/Data"
  mkdir -p "$before_dir" "$after_dir"

  printf 'date,station,rain\n2026-06-16,TEST,1.2\n' > "$before_dir/sample_incremental.csv"
  printf 'date,station,rain\n2026-06-16,TEST,1.2\n2026-06-17,TEST,0.4\n' > "$after_dir/sample_incremental.csv"

  if ! "$PYTHON_BIN" scripts/check-history.py "$after_dir" --compare-before "$before_dir" >/dev/null; then
    rm -rf "$tmp_dir"
    return 1
  fi

  rm -rf "$tmp_dir"
}

check_short_history_rebuild_fixture() {
  local tmp_dir

  # Exercise the active Tomap builder against a short fixture. This protects the
  # popup history columns without running the full downloader.
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/rainmapper-short-history.XXXXXX")" || return 1

  if ! "$PYTHON_BIN" - "$tmp_dir" <<'PY'
import sys
from pathlib import Path

import pandas as pd
import tomap_builder

tmp_dir = Path(sys.argv[1])
maps_path = tmp_dir / "Tomap"
maps_path.mkdir(parents=True, exist_ok=True)

df = pd.DataFrame(
    [
        {
            "Codi Estació": "TEST_SHORT",
            "Data Local": "2026-06-16",
            "Data Lectura": "2026-06-16 08:00:00",
            "Estació": "Short History",
            "Comarca": "Test",
            "Municipi": "Testville",
            "Provincia": "Test",
            "Altitud": 100,
            "Latitud": 41.1,
            "Longitud": 2.1,
            "Ultima Lectura": "2026-06-16 08:00:00",
            "Variable": "Rain",
            "Total": 1.2,
            "Unitat": "mm",
            "max_temp_celsius": 20.0,
            "min_temp_celsius": 12.0,
            "max_humidity_percent": 80.0,
            "min_humidity_percent": 45.0,
            "Hora Local": "08:00:00",
        },
        {
            "Codi Estació": "TEST_SHORT",
            "Data Local": "2026-06-17",
            "Data Lectura": "2026-06-17 08:00:00",
            "Estació": "Short History",
            "Comarca": "Test",
            "Municipi": "Testville",
            "Provincia": "Test",
            "Altitud": 100,
            "Latitud": 41.1,
            "Longitud": 2.1,
            "Ultima Lectura": "2026-06-17 08:00:00",
            "Variable": "Rain",
            "Total": 0.8,
            "Unitat": "mm",
            "max_temp_celsius": 21.0,
            "min_temp_celsius": 13.0,
            "max_humidity_percent": 81.0,
            "min_humidity_percent": 46.0,
            "Hora Local": "08:00:00",
        },
    ]
)

result = tomap_builder.create_last_rains(
    df,
    maps_path,
    nrecords=21,
    minimum_rain_tomap=0,
)

expected_groups = ("Data_Pluja", "Pluja_Diaria", "Hum_Max", "Temp_Max", "Hum_Min", "Temp_Min")
for group in expected_groups:
    columns = [column for column in result.columns if column.startswith(f"{group}_")]
    if len(columns) != 21:
        raise SystemExit(f"Expected 21 {group} columns, got {len(columns)}")

if result.loc[0, "Codi Estació"] != "TEST_SHORT":
    raise SystemExit("Unexpected station code in short-history result")
if result.loc[0, "Data_Pluja_01"] != "17/06/2026":
    raise SystemExit(f"Unexpected latest rain date: {result.loc[0, 'Data_Pluja_01']}")
if result.loc[0, "Pluja_Diaria_01"] != 0.8:
    raise SystemExit(f"Unexpected latest rain amount: {result.loc[0, 'Pluja_Diaria_01']}")
missing_day_21 = result.loc[0, "Data_Pluja_21"]
if not (pd.isna(missing_day_21) or str(missing_day_21).lower() == "nan"):
    raise SystemExit(f"Expected missing day 21 to be empty, got {missing_day_21}")

output_file = maps_path / "Last21_rains.csv"
if not output_file.exists():
    raise SystemExit("create_last_rains did not write Last21_rains.csv")
PY
  then
    rm -rf "$tmp_dir"
    return 1
  fi

  rm -rf "$tmp_dir"
}

check_backup_fixture() {
  local tmp_dir source_dir backup_dir backup_count

  # Verify that the backup script creates exactly one archive for a minimal
  # Rainmapper-like data root.
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/rainmapper-backup.XXXXXX")" || return 1
  source_dir="$tmp_dir/source"
  backup_dir="$tmp_dir/backups"
  mkdir -p "$source_dir/Data"
  printf 'date,station,rain\n2026-06-17,TEST,1.2\n' > "$source_dir/Data/sample_incremental.csv"

  if ! scripts/backup-data.sh "$source_dir" "$backup_dir" >/dev/null; then
    rm -rf "$tmp_dir"
    return 1
  fi

  backup_count="$(find "$backup_dir" -name '*.tar.gz' -type f | wc -l | tr -d ' ')"
  if [ "$backup_count" != "1" ]; then
    printf 'Expected exactly one backup file, found %s\n' "$backup_count" >&2
    rm -rf "$tmp_dir"
    return 1
  fi

  rm -rf "$tmp_dir"
}

check_shell_syntax() {
  bash -n run.sh
  bash -n local_all.sh
  bash -n local_maps.sh
  bash -n local_update.sh
  bash -n rainmapper-local/run.sh
  bash -n rainmapper-local/local_all.sh
  bash -n rainmapper-local/local_maps.sh
  bash -n rainmapper-local/local_update.sh
  bash -n rainmapper-app/run.sh
  bash -n scripts/backup-data.sh
  bash -n scripts/docker-offline-functional-test.sh
  bash -n scripts/smoke-test.sh
  bash -n scripts/sync-manifest.sh
  bash -n scripts/sync-app-files.sh
}

# Keep these checks ordered from cheap/environmental to more functional tests.
run_check "Python interpreter is available ($PYTHON_BIN)" require_command "$PYTHON_BIN"
run_check "node is available" require_command node
run_check "Home Assistant version metadata is aligned" check_versions
run_check "viewer asset cache-busters match Home Assistant version" check_viewer_asset_versions
run_check "root and Home Assistant app files are synchronized" check_synced_files
run_check "Leaflet and MapLibre viewer copies are synchronized" check_synced_viewers
run_check "Python files compile" check_python_syntax
run_check "JavaScript files parse" check_js_syntax
run_check "Python unit tests pass" check_python_unit_tests
run_check "Tomap to GeoJSON conversion works on a minimal fixture" check_geojson_conversion
run_check "Historical CSV check works on a minimal fixture" check_history_fixture
run_check "Short rebuilt histories keep expected last-rain columns" check_short_history_rebuild_fixture
run_check "Data backup script works on a minimal fixture" check_backup_fixture
run_check "shell scripts parse" check_shell_syntax

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  run_check "git diff has no whitespace errors" git diff --check
fi

if [ "$failures" -gt 0 ]; then
  printf 'Smoke test failed with %s failing check(s).\n' "$failures" >&2
  exit 1
fi

printf 'Smoke test passed.\n'
