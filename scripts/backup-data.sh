#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/backup-data.sh SOURCE_DIR [BACKUP_DIR]

Create a timestamped .tar.gz backup of a Rainmapper data directory.

Examples:
  scripts/backup-data.sh docker-data
  scripts/backup-data.sh Data backups
  scripts/backup-data.sh /share/rainmapper /backup/rainmapper

SOURCE_DIR may be a full Rainmapper data root such as docker-data or
/share/rainmapper, or a direct Data directory.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage >&2
  exit 2
fi

SOURCE_DIR="${1%/}"
BACKUP_DIR="${2:-backups}"

if [ ! -d "$SOURCE_DIR" ]; then
  printf 'Source directory does not exist: %s\n' "$SOURCE_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

timestamp="$(date +%Y%m%d-%H%M%S)"
source_name="$(basename "$SOURCE_DIR")"
backup_file="$BACKUP_DIR/rainmapper-${source_name}-${timestamp}.tar.gz"

entries=()
if [ "$(basename "$SOURCE_DIR")" = "Data" ]; then
  entries+=(".")
else
  for entry in Data Tomap Plots PublicData stations.txt ignore_stations_tomap.txt; do
    if [ -e "$SOURCE_DIR/$entry" ]; then
      entries+=("$entry")
    fi
  done
fi

if [ "${#entries[@]}" -eq 0 ]; then
  printf 'No Rainmapper data entries found in: %s\n' "$SOURCE_DIR" >&2
  exit 1
fi

tar -C "$SOURCE_DIR" -czf "$backup_file" "${entries[@]}"

printf 'Backup created: %s\n' "$backup_file"
