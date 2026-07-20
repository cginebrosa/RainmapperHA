#!/usr/bin/env python3
"""Compare two mushroom V0 rebuild output directories semantically."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_rebuild_comparison  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = mushroom_rebuild_comparison.compare_artifact_dirs(
            args.reference_dir,
            args.candidate_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Comparison failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "equivalent" else 1


if __name__ == "__main__":
    raise SystemExit(main())
