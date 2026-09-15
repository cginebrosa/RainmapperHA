#!/usr/bin/env python3
"""Explicit, metadata-only MFE spatial index preparation; originals stay read-only."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_forest import prepare_index

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_index(args.source,args.output)))
