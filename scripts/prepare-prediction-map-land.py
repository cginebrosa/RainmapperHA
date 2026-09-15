#!/usr/bin/env python3
"""Prepare a separate indexed file for oversized ICGC polygons. Never a query job."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_land_parts import prepare

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--kind",choices=["vegetation","geology"],required=True)
    args=parser.parse_args()
    prepare(args.source,args.output,args.kind)
