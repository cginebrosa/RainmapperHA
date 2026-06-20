#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load the single source of truth for root files/directories copied into the HA app.
source "$ROOT_DIR/scripts/sync-manifest.sh"

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

for source_file in "${RAINMAPPER_SYNC_FILES[@]}"; do
  copy_file "$source_file"
done

for source_dir in "${RAINMAPPER_SYNC_DIRS[@]}"; do
  sync_dir "$source_dir"
done

printf 'Root/app Home Assistant copies are synchronized.\n'
