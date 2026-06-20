#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper for the local maps-only runner.

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/rainmapper-local/local_maps.sh" "$@"
