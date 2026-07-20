#!/usr/bin/env python3
"""Manage persistent datasets used by the portable Rainmapper worker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_worker_dataset_cache  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync-local", help="copy a manifest dataset into the cache")
    sync_parser.add_argument("--input-manifest", type=Path, required=True)
    sync_parser.add_argument("--source-root", type=Path, required=True)
    sync_parser.add_argument("--worker-data-dir", type=Path, required=True)
    sync_parser.add_argument("--dataset-id", default=mushroom_worker_dataset_cache.DEFAULT_DATASET_ID)

    verify_parser = subparsers.add_parser("verify", help="verify the active cached dataset")
    verify_parser.add_argument("--worker-data-dir", type=Path, required=True)
    verify_parser.add_argument("--dataset-id", default=mushroom_worker_dataset_cache.DEFAULT_DATASET_ID)
    verify_parser.add_argument("--deep", action="store_true")

    resolve_parser = subparsers.add_parser("resolve", help="resolve the active cached dataset")
    resolve_parser.add_argument("--worker-data-dir", type=Path, required=True)
    resolve_parser.add_argument("--dataset-id", default=mushroom_worker_dataset_cache.DEFAULT_DATASET_ID)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "sync-local":
            manifest = mushroom_worker_dataset_cache.load_input_manifest(args.input_manifest)
            result = mushroom_worker_dataset_cache.sync_local(
                manifest,
                args.source_root,
                args.worker_data_dir,
                dataset_id=args.dataset_id,
            )
        elif args.command == "verify":
            result = mushroom_worker_dataset_cache.verify_version(
                args.worker_data_dir,
                dataset_id=args.dataset_id,
                deep=args.deep,
            )
        else:
            result = mushroom_worker_dataset_cache.resolve_current(
                args.worker_data_dir,
                dataset_id=args.dataset_id,
            )
    except (FileNotFoundError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") != "invalid" else 1


if __name__ == "__main__":
    sys.exit(main())
