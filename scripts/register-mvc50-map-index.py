#!/usr/bin/env python3
"""Explicitly register a copied, verified MVC50 index in a portable geography publication."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_geography_portable import add_map_asset
from rainmapper_core.mushroom_map_volume import digest, local
from rainmapper_core.mushroom_map_vegetation import FORMAT, SOURCE, EDITION
import sqlite3
from contextlib import closing

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--generation', required=True)
    parser.add_argument('--verified-copy', action='store_true', help='Trust a copy already verified off HA; only read metadata and stats')
    args = parser.parse_args()
    if args.receipt.stat().st_size > 4096:
        parser.error('receipt too large')
    asset = json.loads(args.receipt.read_text())
    path = local(args.root.resolve(), asset['path'])
    if path.stat().st_size != asset['bytes']:
        parser.error('index size differs from receipt')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
        metadata = json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
    if (metadata.get('format'), metadata.get('source_id'), metadata.get('edition')) != (FORMAT, SOURCE, EDITION):
        parser.error('unexpected MVC50 index identity')
    if not args.verified_copy and digest(path) != asset['sha256']:
        parser.error('index checksum differs from receipt')
    print(json.dumps(add_map_asset(args.root, asset, 'mvc50_index', args.generation)))
