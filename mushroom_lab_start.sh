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
WORKER_COORDINATOR_URL="http://rainmapper-ha-ui:8100"
export RAINMAPPER_LOCAL_REPO_ROOT="${REPO_ROOT}"
RAINMAPPER_LOCAL_DATA_ROOT="${RAINMAPPER_LOCAL_DATA_ROOT:-${REPO_ROOT}/docker-data}"
export RAINMAPPER_LOCAL_DATA_ROOT

cd "${REPO_ROOT}"

docker network create rainmapper-local-compute >/dev/null 2>&1 || true
docker compose -f "${COMPOSE_FILE}" up --build -d rainmapper-ha-ui

printf '\nMushroom observation lab is starting.\n\n'
printf 'UI URL for your browser:\n  %s\n\n' "${LAB_URL}"
printf 'Rainmapper URL for the worker:\n  %s\n' "${WORKER_COORDINATOR_URL}"
printf '  This internal URL is only for containers on rainmapper-local-compute.\n'
printf '  Do not open it in the browser or replace it with 127.0.0.1:8101.\n\n'
printf 'Data directory: %s\n' "${RAINMAPPER_LOCAL_DATA_ROOT}/mushroom-data"
printf 'Stop it with: ./mushroom_lab_stop.sh\n'
