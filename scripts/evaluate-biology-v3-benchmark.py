#!/usr/bin/env python3
"""Evaluate a Biology V3 benchmark without writing fitted model artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core.mushroom_ml_biology_v3_evaluation import evaluate_benchmark


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--group-days", type=int, choices=(7, 14), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    report = evaluate_benchmark(benchmark, group_days=args.group_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "split": report["split"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
