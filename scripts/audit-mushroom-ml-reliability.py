#!/usr/bin/env python3
"""Audit provisional hold-out reliability for arbitrary species and areas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core.mushroom_ml_reliability_audit import (
    OFFICIAL_SELECTION_SPLIT_ID,
    AuditPolicy,
    audit_jsonl,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read existing hold-out predictions and rank candidates separately "
            "for each species, area_id, split_id and operational prediction day "
            "from 1 to 7. No models are trained or run."
        )
    )
    parser.add_argument("--holdout", required=True, type=Path)
    parser.add_argument("--species", action="append", dest="species_ids")
    parser.add_argument("--area", action="append", dest="area_ids")
    split_group = parser.add_mutually_exclusive_group()
    split_group.add_argument(
        "--split",
        action="append",
        dest="split_ids",
        help=(
            "Split to audit; repeat for several. Defaults to the official "
            f"selection split ({OFFICIAL_SELECTION_SPLIT_ID})."
        ),
    )
    split_group.add_argument(
        "--all-splits",
        action="store_true",
        help="Audit every split separately for diagnostic comparison.",
    )
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--no-stability", action="store_true")
    parser.add_argument("--include-candidates", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.top < 1:
        raise SystemExit("--top must be at least 1")
    policy = AuditPolicy()
    split_ids = (
        None
        if args.all_splits
        else set(args.split_ids or [OFFICIAL_SELECTION_SPLIT_ID])
    )
    report = audit_jsonl(
        args.holdout,
        policy=policy,
        species_ids=set(args.species_ids) if args.species_ids else None,
        area_ids=set(args.area_ids) if args.area_ids else None,
        split_ids=split_ids,
        top=args.top,
        include_candidates=args.include_candidates,
        include_stability=not args.no_stability,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
