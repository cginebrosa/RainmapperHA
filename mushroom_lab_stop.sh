#!/usr/bin/env bash
set -euo pipefail

# Stop the local mushroom observation lab WebUI.
#
# This intentionally uses `docker compose stop` instead of `down -v` so the
# local `docker-data/` copy, observations, historical data, and lab artifacts
# remain untouched.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${REPO_ROOT}/rainmapper-local/docker-compose.yml"

cd "${REPO_ROOT}"

docker compose -f "${COMPOSE_FILE}" stop rainmapper-ha-ui

printf '\nMushroom observation lab stopped.\n'
printf 'Local data preserved under: %s\n' "${REPO_ROOT}/docker-data"
