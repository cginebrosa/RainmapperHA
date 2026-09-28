#!/usr/bin/env python3
"""Reuse published GIS assets for reconstruction; prepare only small metadata."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_geography_portable import territorial_dataset_plan, activate_territorial_dataset

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--activate', action='store_true', help='Activate while no reconstruction is running')
    args = parser.parse_args()
    plan = territorial_dataset_plan(args.root)
    if args.activate:
        activate_territorial_dataset(args.root, plan)
    print(json.dumps({'activated': args.activate, 'files': len(plan['dataset']['files']),
                      'fingerprint': plan['dataset']['fingerprint'],
                      'configuration_bytes': plan['configuration_bytes'],
                      'dataset_metadata_bytes': len(json.dumps(plan['dataset']).encode()),
                      'copied_asset_bytes': 0, 'hashed_asset_bytes': 0}))
