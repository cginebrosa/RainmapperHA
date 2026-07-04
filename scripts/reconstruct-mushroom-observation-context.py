#!/usr/bin/env python3
"""Rebuild weather features for mushroom observations.

This script reads Rainmapper incremental weather history and mushroom
observations, then writes v0 weather features under `mushroom-data`. It does
not modify observations, profiles, catalogs or historical CSV files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_observation_context  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mushroom_observation_context_rebuild.sh",
        description="Rebuild experimental weather features for local mushroom observations.",
        epilog=(
            "Defaults read docker-data/mushroom-data/mushroom_observations.json and "
            "docker-data/Data/ in local labs, or /share/rainmapper paths inside HA. "
            "Outputs go under mushroom-data and mushroom-data/reports."
        ),
    )
    parser.add_argument(
        "--observations",
        type=Path,
        default=mushroom_observation_context.default_observations_path(),
        help="Path to mushroom_observations.json.",
    )
    parser.add_argument(
        "--weather-data-dir",
        type=Path,
        default=mushroom_observation_context.default_weather_data_dir(),
        help="Directory containing Rainmapper *_incremental.csv files.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=mushroom_observation_context.default_output_json_path(),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=mushroom_observation_context.default_output_csv_path(),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=mushroom_observation_context.default_report_path(),
        help="Output markdown report path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = mushroom_observation_context.build_and_write_observation_weather_features(
        observations_path=args.observations,
        weather_data_dir=args.weather_data_dir,
        output_json_path=args.output_json,
        output_csv_path=args.output_csv,
        report_path=args.report,
    )
    summary = payload.get("summary", {})
    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote CSV: {args.output_csv}")
    print(f"Wrote report: {args.report}")
    print(f"Observations: {summary.get('observations', 0)}")
    print(f"Weather stations loaded: {summary.get('weather_stations_loaded', 0)}")
    print(f"Rows with station: {summary.get('with_weather_station', 0)}")
    print(f"Rows with gaps: {summary.get('with_gaps', 0)}")
    print(f"Method: {payload.get('weather_method')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
