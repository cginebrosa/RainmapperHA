#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# This script is intentionally update-only: it refreshes Data/* current downloads and
# incrementals, but it does not rebuild Tomap or generate/publish viewers.
echo "Building local Rainmapper Docker image..."
docker compose -f rainmapper-local/docker-compose.yml build rainmapper

echo "Running Rainmapper locally with MODE=update..."
docker compose -f rainmapper-local/docker-compose.yml run --rm -e MODE=update rainmapper

echo ""
echo "Local update finished. Current downloads and incrementals were refreshed."
