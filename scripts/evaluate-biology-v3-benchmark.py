#!/usr/bin/env python3
"""Evaluate a Biology V3 benchmark without writing fitted model artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_trainer
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core.mushroom_ml_biology_v3_evaluation import (
    build_observation_altitude_v2_benchmark,
    evaluate_benchmark,
    evaluate_matched_benchmarks,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--v2-features", type=Path)
    parser.add_argument("--known-sites", type=Path)
    parser.add_argument("--species", nargs="+")
    parser.add_argument(
        "--version-registry",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "mushroom-data"
        / "mushroom_ml_version_registry.json",
    )
    parser.add_argument("--group-days", type=int, choices=(7, 14), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    if bool(args.v2_features) != bool(args.known_sites):
        parser.error("--v2-features and --known-sites must be provided together")
    if args.v2_features:
        feature_rows = mushroom_ml_trainer.load_features(args.v2_features)
        v2_benchmark = build_observation_altitude_v2_benchmark(
            feature_rows,
            benchmark,
            micro_area_to_area=mushroom_ml_trainer.load_micro_area_to_area(args.known_sites),
            area_representative_altitudes=(
                mushroom_ml_trainer.load_area_representative_altitudes(args.known_sites)
            ),
        )
        v2_benchmark["source"] = {
            "features_path": str(args.v2_features),
            "features_sha256": sha256(args.v2_features),
            "known_sites_path": str(args.known_sites),
            "known_sites_sha256": sha256(args.known_sites),
        }
        report = evaluate_matched_benchmarks(
            v2_benchmark,
            benchmark,
            group_days=args.group_days,
            species_ids=set(args.species) if args.species else None,
            version_registry=mushroom_ml_version_registry.load_registry(
                args.version_registry
            ),
        )
    else:
        report = evaluate_benchmark(
            benchmark,
            group_days=args.group_days,
            species_ids=set(args.species) if args.species else None,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "split": report["split"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
