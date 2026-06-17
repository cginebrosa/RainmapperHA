#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Building local Rainmapper Docker image..."
docker compose build rainmapper

echo "Running Rainmapper locally with MODE=all..."
docker compose run --rm -e MODE=all rainmapper

echo ""
echo "Starting local HTTP server for viewers."
echo "MapLibre: http://${HOST}:${PORT}/maplibre-viewer/"
echo "Leaflet:   http://${HOST}:${PORT}/leaflet-viewer/"
echo "Press Ctrl+C to stop the server."
echo ""

exec "$PYTHON_BIN" -m http.server "$PORT" --bind "$HOST"
