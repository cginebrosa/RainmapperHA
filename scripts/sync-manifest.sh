#!/usr/bin/env bash

# Shared root-to-Home-Assistant sync manifest.
#
# `scripts/sync-app-files.sh` uses this list to copy development sources into
# `rainmapper-app/app`, and `scripts/smoke-test.sh` uses the same list to verify
# that the copy is still aligned. Keeping the list here avoids the two scripts
# drifting when a new wrapper or shared package is added.

RAINMAPPER_SYNC_FILES=(
  Rainmapper.py
  Rainmapper_Client.py
  const.py
  incremental_upsert.py
  requirements.txt
  stations.example.txt
  tomap_builder.py
  tomap_to_geojson.py
)

RAINMAPPER_SYNC_DIRS=(
  rainmapper_core
  leaflet-viewer
  maplibre-viewer
)
