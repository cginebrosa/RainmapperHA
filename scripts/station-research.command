#!/bin/zsh
cd "${0:A:h:h}" || exit 1
exec .venv/bin/python -u scripts/station_research.py "$@"
