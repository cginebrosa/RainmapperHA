#!/usr/bin/env python

"""Compatibility wrapper for the shared Tomap-to-GeoJSON implementation."""

from rainmapper_core.geojson import (
    DEFAULT_IGNORE_STATIONS_FILE,
    TOMAP_FILES,
    add_station_sources,
    clean_value,
    convert_all,
    convert_file,
    dataframe_to_geojson,
    filter_ignored_stations,
    infer_station_source,
    load_ignore_station_codes,
    main,
    parse_args,
)


__all__ = [
    'DEFAULT_IGNORE_STATIONS_FILE',
    'TOMAP_FILES',
    'add_station_sources',
    'clean_value',
    'convert_all',
    'convert_file',
    'dataframe_to_geojson',
    'filter_ignored_stations',
    'infer_station_source',
    'load_ignore_station_codes',
    'main',
    'parse_args',
]


if __name__ == "__main__":
    main()
