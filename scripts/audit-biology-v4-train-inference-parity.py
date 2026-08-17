#!/usr/bin/env python3
"""Audit Biology V4 benchmark/inference parity without fitting a model."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_ml_biology_v4 as biology_v4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3-benchmark", required=True, type=Path)
    parser.add_argument("--v4-benchmark", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    v3_payload = json.loads(args.v3_benchmark.read_text(encoding="utf-8"))
    v4_payload = json.loads(args.v4_benchmark.read_text(encoding="utf-8"))
    report = biology_v4.audit_train_inference_parity(
        v3_payload, v4_payload, profile_id=args.profile
    )
    report["source"] = {
        "v3_benchmark_path": str(args.v3_benchmark),
        "v3_benchmark_sha256": sha256(args.v3_benchmark),
        "v4_benchmark_path": str(args.v4_benchmark),
        "v4_benchmark_sha256": sha256(args.v4_benchmark),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "profile_id": args.profile,
        "compared_sample_count": report["compared_sample_count"],
        "predictive_mismatch_count": report["predictive_mismatch_count"],
        "eligibility_mismatch_count": report["eligibility_mismatch_count"],
        "parity_passed": report["parity_passed"],
        "model_artifact_written": report["model_artifact_written"],
    }, ensure_ascii=False))
    return 0 if report["parity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
