#!/usr/bin/env python3
"""Compare V2, V3 and each selected V4 profile on identical observation rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_biology_v4 as biology_v4
from rainmapper_core import mushroom_ml_trainer
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core.mushroom_ml_biology_v3_evaluation import (
    build_observation_altitude_v2_benchmark,
    build_observation_altitude_v2_common_idw_benchmark,
    evaluate_matched_version_benchmarks,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3-benchmark", required=True, type=Path)
    parser.add_argument("--v4-benchmark", required=True, type=Path)
    parser.add_argument("--v2-features", type=Path)
    parser.add_argument(
        "--v2-weather-basis",
        choices=("common-idw", "production-replay"),
        default="common-idw",
    )
    parser.add_argument("--known-sites", required=True, type=Path)
    parser.add_argument("--group-days", required=True, type=int, choices=(7, 14))
    parser.add_argument(
        "--v4-profile",
        action="append",
        dest="v4_profiles",
        default=[],
    )
    parser.add_argument(
        "--version-registry",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "mushroom-data"
        / "mushroom_ml_version_registry.json",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    v3 = json.loads(args.v3_benchmark.read_text(encoding="utf-8"))
    v4 = json.loads(args.v4_benchmark.read_text(encoding="utf-8"))
    if args.v2_weather_basis == "common-idw":
        v2 = build_observation_altitude_v2_common_idw_benchmark(v3)
        v2["source"] = {
            "weather_basis": "common_multisource_area_idw",
            "v3_benchmark_path": str(args.v3_benchmark),
            "v3_benchmark_sha256": sha256(args.v3_benchmark),
        }
    else:
        if args.v2_features is None:
            parser.error("--v2-features is required for --v2-weather-basis production-replay")
        features = mushroom_ml_trainer.load_features(args.v2_features)
        v2 = build_observation_altitude_v2_benchmark(
            features,
            v3,
            micro_area_to_area=mushroom_ml_trainer.load_micro_area_to_area(
                args.known_sites
            ),
            area_representative_altitudes=(
                mushroom_ml_trainer.load_area_representative_altitudes(args.known_sites)
            ),
        )
        v2["source"] = {
            "weather_basis": "production_single_station_replay",
            "features_path": str(args.v2_features),
            "features_sha256": sha256(args.v2_features),
            "known_sites_path": str(args.known_sites),
            "known_sites_sha256": sha256(args.known_sites),
        }
    profiles = args.v4_profiles or ["core", "extended_weather", "climatic_balance"]
    if len(set(profiles)) != len(profiles):
        parser.error("duplicate --v4-profile")
    registry = mushroom_ml_version_registry.load_registry(args.version_registry)
    reports: dict[str, object] = {}
    evaluation_cache: dict[tuple[object, ...], dict[str, object]] = {}
    for profile_id in profiles:
        v4_profile = biology_v4.materialize_comparison_benchmark(
            v4,
            profile_id=profile_id,
        )
        reports[profile_id] = evaluate_matched_version_benchmarks(
            {
                "altitude_v2": v2,
                "biology_v3": v3,
                "biology_v4": v4_profile,
            },
            group_days=args.group_days,
            version_registry=registry,
            evaluation_cache=evaluation_cache,
        )
        print(
            json.dumps(
                {
                    "completed_v4_profile": profile_id,
                    "jointly_eligible": reports[profile_id]["coverage"][
                        "jointly_eligible"
                    ],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    output = {
        "kind": "mushroom_ml_v2_v3_v4_profile_comparison",
        "schema_version": 1,
        "group_days": args.group_days,
        "v4_profiles": profiles,
        "v2_weather_basis": args.v2_weather_basis,
        "profiles": reports,
        "selection_policy": (
            "compare per species, temporal contract, estimator and V4 profile; "
            "never select from a pooled cross-species score"
        ),
        "model_artifact_written": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
