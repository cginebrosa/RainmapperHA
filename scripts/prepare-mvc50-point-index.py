#!/usr/bin/env python3
"""Prepare the bounded MVC50 reader once, outside map queries and HA runners."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_vegetation import prepare

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination)))
