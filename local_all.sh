#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper.
#
# The real local all-in-one runner lives in `rainmapper-local/local_all.sh`.
# Keeping this file allows the familiar `./local_all.sh` command to continue
# working while local-only files move under `rainmapper-local/`.

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/rainmapper-local/local_all.sh" "$@"
