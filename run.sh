#!/usr/bin/env sh
set -eu

cd /app

echo "Starting Rainmapper once..."

python Rainmapper.py \
  --days_init "${RAINMAPPER_DAYS_INIT:--1}" \
  --days_end "${RAINMAPPER_DAYS_END:-0}" \
  --create_wunderground "${RAINMAPPER_CREATE_WUNDERGROUND:-false}"

echo "Rainmapper finished."