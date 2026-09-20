#!/bin/zsh
cd "${0:A:h:h:h}" || exit 1
exec .venv/bin/python -u local-apps/wunderground/code/station_research.py "$@"
