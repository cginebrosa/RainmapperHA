#!/usr/bin/env python3
"""Bounded on-demand GDAL adapter; only reads the existing MFE index."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_forest import ForestReader
from rainmapper_core.mushroom_geography_store import SourceIdentities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', required=True)
    parser.add_argument('--catalogs', required=True)
    parser.add_argument('--sources')
    args = parser.parse_args()
    reader = ForestReader(args.index, catalogs=args.catalogs, sources=SourceIdentities(args.sources))
    try:
        while raw := sys.stdin.buffer.readline(65537):
            if len(raw) > 65536:
                raise ValueError('gis_request_limit')
            request = json.loads(raw)
            result = (reader.lookup_polygon(request['geometry']) if 'geometry' in request
                      else reader.lookup(request['lat'], request['lon']))
            encoded = json.dumps({'id': request['id'], **result}, allow_nan=False)
            if len(encoded.encode()) > 65536:
                raise ValueError('gis_result_limit')
            print(encoded, flush=True)
    finally:
        reader.close()


if __name__ == '__main__':
    main()
