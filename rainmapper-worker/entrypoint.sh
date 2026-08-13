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

if [ "$1" = "biology-v3" ]; then
    shift
    action="${1:-}"
    if [ -n "$action" ]; then
        shift
    fi
    case "$action" in
        build)
            exec gosu rainmapper-worker:rainmapper-worker \
                python /app/scripts/build-biology-v3-benchmark.py "$@"
            ;;
        evaluate)
            exec gosu rainmapper-worker:rainmapper-worker \
                python /app/scripts/evaluate-biology-v3-benchmark.py "$@"
            ;;
        *)
            printf 'Usage: rainmapper-worker biology-v3 {build|evaluate} [options]\n' >&2
            exit 2
            ;;
    esac
fi

exec gosu rainmapper-worker:rainmapper-worker \
    python /app/scripts/run-mushroom-rebuild-job.py "$@"
