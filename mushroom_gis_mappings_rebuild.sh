#!/usr/bin/env bash
set -euo pipefail

# Rebuild the local GIS mapping candidate queue used by /mushrooms/gis-mappings.
#
# The Python script scans configured local GIS layers, skips existing exact
# mappings, and writes a temporary reconstruction payload under tmp/. It does
# not modify mushroom_gis_mappings.json, catalogs, observations, or GIS data.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "${REPO_ROOT}"

python3 scripts/reconstruct-mushroom-gis-mappings.py "$@"
