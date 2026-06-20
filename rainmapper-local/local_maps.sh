#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Building local Rainmapper Docker image..."
docker compose -f rainmapper-local/docker-compose.yml build rainmapper

echo "Running Rainmapper locally with MODE=maps..."
docker compose -f rainmapper-local/docker-compose.yml run --rm -e MODE=maps rainmapper

echo ""
LAN_HOST="${LAN_HOST:-$(ipconfig getifaddr en0 2>/dev/null || true)}"
if [ -z "$LAN_HOST" ]; then
  LAN_HOST="$HOST"
fi

# Bind to all interfaces by default so phones/tablets on the same LAN can open
# the viewers. HOST can still be overridden, for example HOST=127.0.0.1.
echo "Starting local HTTP server for viewers."
echo "MapLibre local: http://127.0.0.1:${PORT}/rainmapper_core/viewers/maplibre-viewer/"
echo "Leaflet local:   http://127.0.0.1:${PORT}/rainmapper_core/viewers/leaflet-viewer/"
echo "MapLibre LAN:   http://${LAN_HOST}:${PORT}/rainmapper_core/viewers/maplibre-viewer/"
echo "Leaflet LAN:     http://${LAN_HOST}:${PORT}/rainmapper_core/viewers/leaflet-viewer/"
echo "Press Ctrl+C to stop the server."
echo ""

exec "$PYTHON_BIN" -m http.server "$PORT" --bind "$HOST"
