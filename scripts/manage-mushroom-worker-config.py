#!/usr/bin/env python3
"""Inspect, validate and persist the Rainmapper coordinator used by a worker."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_worker_config  # noqa: E402
from rainmapper_core import mushroom_worker_service  # noqa: E402


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--worker-data-dir", type=Path, default=Path("/var/lib/rainmapper-worker"))
    subparsers = root.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show", help="Show persisted configuration without revealing its token.")
    subparsers.add_parser("get-url", help="Print only the persisted Rainmapper URL.")
    subparsers.add_parser("clear-token", help="Remove the persisted coordinator token without probing it.")
    check = subparsers.add_parser("check", help="Check that the persisted Rainmapper URL is reachable.")
    check.add_argument("--timeout", type=float, default=5.0)
    configure = subparsers.add_parser("configure", help="Validate and persist a Rainmapper URL.")
    configure.add_argument("--rainmapper-url", required=True)
    configure.add_argument("--token-stdin", action="store_true", help="Read a token from standard input.")
    configure.add_argument("--clear-token", action="store_true", help="Remove the persisted token.")
    configure.add_argument("--timeout", type=float, default=5.0)
    pair = subparsers.add_parser("pair", help="Exchange a one-time pairing code for a persistent worker token.")
    pair.add_argument("--rainmapper-url", required=True)
    pair.add_argument("--pairing-code-stdin", action="store_true", required=True)
    pair.add_argument("--display-name", default="")
    pair.add_argument("--host-name", default="")
    pair.add_argument("--timeout", type=float, default=5.0)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "show":
            print(json.dumps(mushroom_worker_config.load_coordinator_config(args.worker_data_dir), ensure_ascii=False))
            return 0
        if args.command == "get-url":
            print(mushroom_worker_config.load_coordinator_config(args.worker_data_dir)["rainmapper_url"])
            return 0
        if args.command == "clear-token":
            removed = mushroom_worker_config.clear_coordinator_token(args.worker_data_dir)
            print(json.dumps({"ok": True, "token_removed": removed}, ensure_ascii=False))
            return 0
        current = mushroom_worker_config.load_coordinator_config(args.worker_data_dir, include_token=True)
        if args.command == "pair":
            identity = mushroom_worker_service.ensure_worker_identity(
                args.worker_data_dir,
                display_name=str(args.display_name),
                host_name=str(args.host_name),
            )
            result = mushroom_worker_config.pair_coordinator(
                args.rainmapper_url,
                pairing_code=sys.stdin.read().strip(),
                identity=identity,
                timeout=args.timeout,
            )
            mushroom_worker_config.save_coordinator_config(
                args.worker_data_dir,
                rainmapper_url=args.rainmapper_url,
                token=str(result["token"]),
            )
            print(json.dumps({"ok": True, "worker_id": identity["worker_id"], "paired": True}, ensure_ascii=False))
            return 0
        identity = mushroom_worker_service.ensure_worker_identity(
            args.worker_data_dir,
            display_name=os.environ.get("RAINMAPPER_WORKER_DISPLAY_NAME", ""),
            host_name=os.environ.get("RAINMAPPER_WORKER_HOST_NAME", ""),
        )
        if args.command == "check":
            result = mushroom_worker_config.probe_coordinator(
                current["rainmapper_url"],
                token=str(current.get("token", "")),
                worker_id=identity["worker_id"],
                timeout=args.timeout,
            )
            print(json.dumps({"ok": True, "coordinator": result}, ensure_ascii=False))
            return 0
        token: str | None = None
        if args.token_stdin:
            token = sys.stdin.read().strip()
        elif args.clear_token:
            mushroom_worker_config.clear_coordinator_token(args.worker_data_dir)
            current["token"] = ""
            token = ""
        effective_token = str(current.get("token", "")) if token is None else token
        result = mushroom_worker_config.probe_coordinator(
            args.rainmapper_url,
            token=effective_token,
            worker_id=identity["worker_id"],
            timeout=args.timeout,
        )
        saved = mushroom_worker_config.save_coordinator_config(
            args.worker_data_dir,
            rainmapper_url=args.rainmapper_url,
            token=token,
        )
        print(json.dumps({"ok": True, "configuration": saved, "coordinator": result}, ensure_ascii=False))
        return 0
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
