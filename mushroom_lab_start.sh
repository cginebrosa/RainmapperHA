#!/usr/bin/env bash
set -euo pipefail

# Start the local mushroom observation lab WebUI.
#
# This wrapper runs only the Home Assistant-style local UI service and mounts
# `docker-data/` as `/share/rainmapper`. It is intended for entering or
# reviewing mushroom observations without touching the real Home Assistant
# installation.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${REPO_ROOT}/rainmapper-local/docker-compose.yml"
LAB_URL="http://127.0.0.1:8101/mushrooms/profiles?section=observations"

cd "${REPO_ROOT}"

docker compose -f "${COMPOSE_FILE}" up --build -d rainmapper-ha-ui

printf '\nMushroom observation lab is starting.\n'
printf 'URL: %s\n\n' "${LAB_URL}"
printf 'Data directory: %s\n' "${REPO_ROOT}/docker-data/mushroom-data"
printf 'Stop it with: ./mushroom_lab_stop.sh\n'
