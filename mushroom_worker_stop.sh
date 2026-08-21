#!/usr/bin/env bash
set -euo pipefail

# Stop the local worker while preserving its image, volume, cache and results.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${REPO_ROOT}/rainmapper-local/docker-compose.worker.yml"

cd "${REPO_ROOT}"

docker compose -f "${COMPOSE_FILE}" stop rainmapper-worker

printf '\nRainmapper worker stopped.\n'
printf 'Persistent data preserved in Docker volume: rainmapper-worker-data\n'
