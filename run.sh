#!/usr/bin/env sh
set -eu

# Compatibility wrapper for the local Docker entrypoint.
#
# The real local container entrypoint lives in `rainmapper-local/run.sh`.
# This wrapper keeps old direct calls to `./run.sh` working from the repo root.

exec "$(dirname "$0")/rainmapper-local/run.sh" "$@"
