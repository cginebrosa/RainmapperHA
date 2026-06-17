#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${PYTHON_BIN:-}" ]; then
  :
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi

failures=0

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

check_synced_files() {
  local files=(
    Rainmapper.py
    Rainmapper_Client.py
    const.py
    requirements.txt
    stations.example.txt
    tomap_to_geojson.py
  )
  local file

  for file in "${files[@]}"; do
    if ! cmp -s "$file" "rainmapper-app/app/$file"; then
      printf 'File differs: %s vs rainmapper-app/app/%s\n' "$file" "$file" >&2
      return 1
    fi
  done
}

check_synced_viewers() {
  diff -qr leaflet-viewer rainmapper-app/app/leaflet-viewer
  diff -qr maplibre-viewer rainmapper-app/app/maplibre-viewer
}

check_python_syntax() {
  "$PYTHON_BIN" - \
    scripts/check-history.py \
    Rainmapper.py \
    Rainmapper_Client.py \
    tomap_to_geojson.py \
    rainmapper-app/app/Rainmapper.py \
    rainmapper-app/app/Rainmapper_Client.py \
    rainmapper-app/app/tomap_to_geojson.py \
    rainmapper-app/app/web_server.py <<'PY'
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
  node --check rainmapper-app/app/leaflet-viewer/app.js
  node --check rainmapper-app/app/leaflet-viewer/config.js
  node --check rainmapper-app/app/maplibre-viewer/app.js
  node --check rainmapper-app/app/maplibre-viewer/config.js
}

check_geojson_conversion() {
  local tmp_dir input_dir output_dir ignore_file convert_log

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

check_backup_fixture() {
  local tmp_dir source_dir backup_dir backup_count

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
  bash -n rainmapper-app/run.sh
  bash -n scripts/backup-data.sh
  bash -n scripts/smoke-test.sh
  bash -n scripts/sync-app-files.sh
}

run_check "Python interpreter is available ($PYTHON_BIN)" require_command "$PYTHON_BIN"
run_check "node is available" require_command node
run_check "Home Assistant version metadata is aligned" check_versions
run_check "root and Home Assistant app files are synchronized" check_synced_files
run_check "Leaflet and MapLibre viewer copies are synchronized" check_synced_viewers
run_check "Python files compile" check_python_syntax
run_check "JavaScript files parse" check_js_syntax
run_check "Tomap to GeoJSON conversion works on a minimal fixture" check_geojson_conversion
run_check "Historical CSV check works on a minimal fixture" check_history_fixture
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
