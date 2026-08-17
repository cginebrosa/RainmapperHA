#!/usr/bin/env python3
"""Compare an arbitrary set of mushroom ML version benchmarks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core.mushroom_ml_biology_v3_evaluation import (
    evaluate_matched_version_benchmarks,
)


def _version_benchmark(value: str) -> tuple[str, Path]:
    version_id, separator, path = value.partition("=")
    if not separator or not version_id.strip() or not path.strip():
        raise argparse.ArgumentTypeError("expected VERSION_ID=BENCHMARK_JSON")
    return version_id.strip(), Path(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark",
        action="append",
        type=_version_benchmark,
        required=True,
        metavar="VERSION_ID=BENCHMARK_JSON",
    )
    parser.add_argument("--group-days", type=int, choices=(7, 14), required=True)
    parser.add_argument("--species", nargs="+")
    parser.add_argument(
        "--version-registry",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "mushroom-data"
        / "mushroom_ml_version_registry.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    benchmarks: dict[str, dict[str, object]] = {}
    for version_id, path in args.benchmark:
        if version_id in benchmarks:
            parser.error(f"duplicate benchmark version: {version_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            parser.error(f"benchmark must contain an object: {path}")
        benchmarks[version_id] = payload
    report = evaluate_matched_version_benchmarks(
        benchmarks,
        group_days=args.group_days,
        species_ids=set(args.species) if args.species else None,
        version_registry=mushroom_ml_version_registry.load_registry(
            args.version_registry
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "version_ids": report["version_ids"],
                "split": report["split"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
