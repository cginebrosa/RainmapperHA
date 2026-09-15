#!/usr/bin/env python3
"""Adopt already copied geography locally; activation is always explicit."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core import mushroom_geography_import as importer
from rainmapper_core.mushroom_geography_store import read_metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('import-map', 'import-dataset', 'publish-dataset'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--generation')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--auxiliary-manifest', type=Path,
                        help='Sealed inventory of retained local files; not sent with scientific jobs')
    parser.add_argument('--fingerprint')
    parser.add_argument('--sealed-source', action='store_true',
                        help='Reuse hashes only after the imported copy has been verified; no raster hashing on HA')
    args = parser.parse_args()
    if args.action == 'publish-dataset':
        if not args.fingerprint:
            parser.error('--fingerprint required')
        result = importer.publish_dataset(args.root, args.fingerprint)
    else:
        if not args.source:
            parser.error('--source required')
        if args.action == 'import-map':
            if not args.generation:
                parser.error('--generation required')
            result = importer.adopt_map(args.source, args.root, args.generation,
                                        sealed_source=args.sealed_source)
        else:
            if not args.manifest:
                parser.error('--manifest required')
            result = importer.adopt_dataset(args.source, args.root, read_metadata(args.manifest),
                                            sealed_source=args.sealed_source,
                                            auxiliary_manifest=read_metadata(args.auxiliary_manifest) if args.auxiliary_manifest else None)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
