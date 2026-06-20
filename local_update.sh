#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper for the local update-only runner.

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/rainmapper-local/local_update.sh" "$@"
