#!/usr/bin/env python3
"""Join experimental weather and GIS features for mushroom observations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_gis_lab, mushroom_observation_context, mushroom_observation_features  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mushroom_observation_features_v0_build.sh",
        description="Join local mushroom weather features and GIS v0 context by observation_id.",
    )
    parser.add_argument(
        "--weather-features",
        type=Path,
        default=mushroom_observation_context.default_output_json_path(),
        help="Input observations_weather_features.json path.",
    )
    parser.add_argument(
        "--gis-reconstruction",
        type=Path,
        default=mushroom_gis_lab.default_output_path(),
        help="Input gis_observation_reconstruction.json path.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=mushroom_observation_features.default_output_json_path(),
        help="Output joined JSON path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=mushroom_observation_features.default_output_csv_path(),
        help="Output joined CSV path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=mushroom_observation_features.default_report_path(),
        help="Output markdown report path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = mushroom_observation_features.build_and_write_observation_features_v0(
        weather_features_path=args.weather_features,
        gis_reconstruction_path=args.gis_reconstruction,
        output_json_path=args.output_json,
        output_csv_path=args.output_csv,
        report_path=args.report,
    )
    summary = payload.get("summary", {})
    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote CSV: {args.output_csv}")
    print(f"Wrote report: {args.report}")
    print(f"Observations: {summary.get('observations', 0)}")
    print(f"With weather: {summary.get('with_weather', 0)}")
    print(f"With GIS: {summary.get('with_gis', 0)}")
    print(f"With weather gaps: {summary.get('with_weather_gaps', 0)}")
    print(f"With GIS/feature gaps: {summary.get('with_gis_or_feature_gaps', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
