#!/bin/sh
set -eu

WORKER_DATA_DIR="${RAINMAPPER_WORKER_DATA_DIR:-/var/lib/rainmapper-worker}"

mkdir -p "$WORKER_DATA_DIR"
chown rainmapper-worker:rainmapper-worker "$WORKER_DATA_DIR"

if [ "$#" -eq 0 ]; then
    set -- --help
fi

if [ "$1" = "dataset" ]; then
    shift
    exec gosu rainmapper-worker:rainmapper-worker \
        python /app/scripts/manage-mushroom-worker-datasets.py "$@"
fi

if [ "$1" = "config" ]; then
    shift
    exec gosu rainmapper-worker:rainmapper-worker \
        python /app/scripts/manage-mushroom-worker-config.py "$@"
fi

if [ "$1" = "serve" ]; then
    shift
    exec gosu rainmapper-worker:rainmapper-worker \
        python /app/scripts/run-mushroom-worker-service.py "$@"
fi

exec gosu rainmapper-worker:rainmapper-worker \
    python /app/scripts/run-mushroom-rebuild-job.py "$@"
