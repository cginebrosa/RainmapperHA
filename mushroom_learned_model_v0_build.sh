#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
python3 scripts/build-mushroom-learned-model-v0.py "$@"
