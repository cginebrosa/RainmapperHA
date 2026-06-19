#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# This script is intentionally update-only: it refreshes Data/* incrementals and lets
# the legacy Rainmapper.py flow rebuild Tomap, but it does not generate/publish viewers.
echo "Building local Rainmapper Docker image..."
docker compose build rainmapper

echo "Running Rainmapper locally with MODE=update..."
docker compose run --rm -e MODE=update rainmapper

echo ""
echo "Local update finished. Tomap files were rebuilt by the legacy Rainmapper.py flow."
