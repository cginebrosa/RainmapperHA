#!/usr/bin/env python3
"""Run an isolated V3 hydric-feature ablation on frozen hold-out groups."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
import zlib


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_ml_biology_v3_physical
from rainmapper_core.mushroom_ml_hydric_ablation import (
    DEFAULT_ESTIMATOR_ID,
    audit_split,
    load_holdout_rows,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Retrain non-operational copies after removing feature families, while "
            "preserving the exact archived external hold-out groups."
        )
    )
    parser.add_argument("--v4-benchmark", required=True, type=Path)
    parser.add_argument("--holdout", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--species", default="lactarius_deliciosus")
    parser.add_argument("--estimator", default=DEFAULT_ESTIMATOR_ID)
    parser.add_argument("--runtime-db", type=Path)
    parser.add_argument("--runtime-area", default="riu_de_cerdanya")
    parser.add_argument("--runtime-date", default="2026-09-04")
    return parser


def _runtime_row(
    database: Path,
    *,
    species_id: str,
    area_id: str,
    target_date: str,
    estimator_id: str,
) -> dict[str, object]:
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        row = connection.execute(
            """
            SELECT payload_json
            FROM operational_members
            WHERE species_id = ? AND area_id = ? AND target_date = ?
              AND version_id = 'biology_v3'
              AND profile_id = 'common_idw_plus_physical_state'
              AND estimator_id = ?
            LIMIT 1
            """,
            (species_id, area_id, target_date, estimator_id),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError("Requested operational runtime row was not found")
    return json.loads(zlib.decompress(row[0]))


def main() -> int:
    args = _parser().parse_args()
    v4 = json.loads(args.v4_benchmark.read_text(encoding="utf-8"))
    benchmark = mushroom_ml_biology_v3_physical.materialize_benchmark(v4)
    runtime = None
    runtime_features = None
    runtime_probability = None
    if args.runtime_db:
        runtime = _runtime_row(
            args.runtime_db,
            species_id=args.species,
            area_id=args.runtime_area,
            target_date=args.runtime_date,
            estimator_id=args.estimator,
        )
        runtime_features = dict(runtime["features_used"])
        runtime_probability = float(runtime["prediction"]["probability"])
    results = []
    for group_days in (7, 14):
        archived = load_holdout_rows(
            args.holdout,
            species_id=args.species,
            group_days=group_days,
        )
        results.append(
            audit_split(
                benchmark,
                archived,
                species_id=args.species,
                estimator_id=args.estimator,
                runtime_features=runtime_features,
                runtime_reference_probability=runtime_probability,
            )
        )
    report = {
        "schema_version": "1.0",
        "kind": "mushroom_ml_hydric_ablation_audit",
        "operational": False,
        "source_v4_benchmark": str(args.v4_benchmark.resolve()),
        "source_holdout": str(args.holdout.resolve()),
        "runtime_reference": (
            {
                "database": str(args.runtime_db.resolve()),
                "species_id": args.species,
                "area_id": args.runtime_area,
                "target_date": args.runtime_date,
                "stored_probability": runtime_probability,
                "model_ref": runtime["model_ref"],
            }
            if runtime is not None
            else None
        ),
        "splits": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output.resolve()), "splits": len(results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
