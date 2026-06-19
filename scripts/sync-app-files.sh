#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

copy_file() {
  local source_file="$1"
  local target_file="rainmapper-app/app/$source_file"

  mkdir -p "$(dirname "$target_file")"
  cp "$source_file" "$target_file"
  printf 'Synced %s -> %s\n' "$source_file" "$target_file"
}

sync_dir() {
  local source_dir="$1"
  local target_dir="rainmapper-app/app/$source_dir"

  if ! command -v rsync >/dev/null 2>&1; then
    printf 'Missing required command: rsync\n' >&2
    return 1
  fi

  mkdir -p "$target_dir"
  rsync -a --delete "$source_dir/" "$target_dir/"
  printf 'Synced %s/ -> %s/\n' "$source_dir" "$target_dir"
}

copy_file Rainmapper.py
copy_file Rainmapper_Client.py
copy_file const.py
copy_file requirements.txt
copy_file stations.example.txt
copy_file tomap_builder.py
copy_file tomap_to_geojson.py

sync_dir leaflet-viewer
sync_dir maplibre-viewer

printf 'Root/app Home Assistant copies are synchronized.\n'
