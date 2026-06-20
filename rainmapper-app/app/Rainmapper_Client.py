#!/usr/bin/env python

"""Compatibility entrypoint for classic Bokeh map generation."""

from rainmapper_core.bokeh_maps import main


if __name__ == '__main__':
    raise SystemExit(main())
