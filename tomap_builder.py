#!/usr/bin/env python

"""Compatibility wrapper for the shared Tomap builder implementation."""

from rainmapper_core.config.const import _DATA_PATH, _MAPS_PATH, _last_number_rains, _max_threads, _minimum_rain_tomap
from rainmapper_core.tomap import (
    INCREMENTAL_COLUMNS,
    TOMAP_PERIODS,
    build_tomap,
    create_empty_incremental,
    create_filtered,
    create_grouped,
    create_last_rains,
    filter_results,
    main as core_main,
    merge_dataframes,
    parse_args,
    positive_int,
    read_incremental,
    save_dataframe_tomap,
)


__all__ = [
    'INCREMENTAL_COLUMNS',
    'TOMAP_PERIODS',
    'build_tomap',
    'create_empty_incremental',
    'create_filtered',
    'create_grouped',
    'create_last_rains',
    'filter_results',
    'merge_dataframes',
    'parse_args',
    'positive_int',
    'read_incremental',
    'save_dataframe_tomap',
]


def main(argv=None):
    """Run the Tomap builder using the existing local/HA default settings."""
    defaults = {
        'data_dir': _DATA_PATH,
        'maps_dir': _MAPS_PATH,
        'last_rains_history': _last_number_rains,
        'minimum_rain_tomap': _minimum_rain_tomap,
        'max_threads': _max_threads,
    }
    return core_main(argv=argv, defaults=defaults)


if __name__ == '__main__':
    raise SystemExit(main())
