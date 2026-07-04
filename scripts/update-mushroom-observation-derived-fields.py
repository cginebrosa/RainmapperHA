#!/usr/bin/env python3
"""Populate cheap derived fields in mushroom observations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_observations  # noqa: E402
from rainmapper_core.mushroom_store import default_store  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update mushroom observations with derived.month and derived.season from observed_at.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the number of observations that would change without writing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = default_store()
    payload = store.load("observations")
    if not isinstance(payload, dict):
        print("observations payload must be a JSON object", file=sys.stderr)
        return 2
    rows = payload.get("observations")
    if not isinstance(rows, list):
        print("observations payload must contain an observations list", file=sys.stderr)
        return 2

    updated_rows = []
    changed = 0
    for row in rows:
        if not isinstance(row, dict):
            updated_rows.append(row)
            continue
        updated = mushroom_observations.finalize_observation_payload(row)
        if json.dumps(updated, sort_keys=True, ensure_ascii=True) != json.dumps(row, sort_keys=True, ensure_ascii=True):
            changed += 1
        updated_rows.append(updated)

    print(f"Observations: {len(rows)}")
    print(f"Updated derived fields: {changed}")
    if args.dry_run:
        print("Dry run: no file written.")
        return 0

    if changed == 0:
        print("No changes needed.")
        return 0

    payload["observations"] = updated_rows
    result = store.replace("observations", payload)
    if not result.ok:
        for issue in result.errors:
            print(f"{issue.location}: {issue.message}", file=sys.stderr)
        return 1
    print(f"Wrote observations. Backup: {result.backup_path or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
