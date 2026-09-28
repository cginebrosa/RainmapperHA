#!/usr/bin/env python3
"""Bounded on-demand reader for the same territorial sources as the map."""
import argparse
import json
import logging
from pathlib import Path
import sys
import sqlite3
from contextlib import ExitStack

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_forest import ForestReader
from rainmapper_core.mushroom_map_land import LandReader
from rainmapper_core.mushroom_map_vegetation import VegetationReader
from rainmapper_core.mushroom_geography_store import SourceIdentities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index')
    for flag in ('--mvc50-index', '--land-cover', '--geology', '--land-cover-parts', '--geology-parts'):
        parser.add_argument(flag)
    parser.add_argument('--catalogs', required=True)
    parser.add_argument('--sources')
    args = parser.parse_args()
    with ExitStack() as cleanup:
        sources = SourceIdentities(args.sources)
        reader = None
        if args.index:
            try:
                reader = ForestReader(args.index, catalogs=args.catalogs, sources=sources)
                cleanup.callback(reader.close)
            except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error):
                logging.exception('Recovery forest reader initialization failed')
        land = {}
        paths = (('mvc50', args.mvc50_index), ('vegetation', args.land_cover), ('geology', args.geology))
        for kind, path in paths:
            if path:
                try:
                    land[kind] = (VegetationReader(path) if kind == 'mvc50' else
                                  LandReader(path, kind, parts=args.land_cover_parts if kind == 'vegetation' else args.geology_parts, sources=sources))
                    cleanup.callback(land[kind].close)
                except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error):
                    logging.exception('Recovery %s reader initialization failed', kind)
        while raw := sys.stdin.buffer.readline(65537):
            if len(raw) > 65536:
                raise ValueError('gis_request_limit')
            request = json.loads(raw)
            try:
                result = ((reader.lookup_polygon(request['geometry']) if 'geometry' in request
                           else reader.lookup(request['lat'], request['lon'])) if reader else
                          {'status': 'unavailable' if args.index else 'not_connected'})
            except (ValueError, RuntimeError, OSError, sqlite3.Error):
                logging.exception('Recovery forest query failed')
                result = {'status': 'unavailable'}
            if 'geometry' not in request:
                result['land_context'] = {}
                for kind, path in paths:
                    try:
                        result['land_context'][kind] = (land[kind].lookup(request['lat'], request['lon']) if kind in land else
                                                       {'status': 'unavailable' if path else 'not_connected'})
                    except (ValueError, RuntimeError, OSError, sqlite3.Error):
                        logging.exception('Recovery %s query failed', kind)
                        result['land_context'][kind] = {'status': 'unavailable'}
            encoded = json.dumps({'id': request['id'], **result}, allow_nan=False)
            if len(encoded.encode()) > 65536:
                raise ValueError('gis_result_limit')
            print(encoded, flush=True)



if __name__ == '__main__':
    main()
