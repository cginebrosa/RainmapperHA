#!/usr/bin/env python3
"""Build the experimental learned v0 mushroom model from observation features."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_learned_model, mushroom_observation_features  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mushroom_learned_model_v0_build.sh",
        description="Build an experimental observation-learned v0 mushroom model.",
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=mushroom_observation_features.default_output_json_path(),
        help="Input observation_features_v0.json path.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=mushroom_learned_model.default_output_json_path(),
        help="Output learned model JSON path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=mushroom_learned_model.default_report_path(),
        help="Output markdown report path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = mushroom_learned_model.build_and_write_learned_model_v0(
        features_path=args.features,
        output_json_path=args.output_json,
        report_path=args.report,
    )
    summary = payload.get("summary", {})
    print(f"Wrote JSON: {args.output_json}")
    print(f"Wrote report: {args.report}")
    print(f"Observations: {summary.get('observations', 0)}")
    print(f"Source observations: {summary.get('source_observations', 0)}")
    print(f"Excluded observations: {summary.get('excluded_observations', 0)}")
    print(f"Species: {summary.get('species', 0)}")
    print(f"Positive observations: {summary.get('positive_observations', 0)}")
    print(f"Negative observations: {summary.get('negative_observations', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
