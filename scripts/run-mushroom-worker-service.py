#!/usr/bin/env python3
"""Run the local Rainmapper worker status service."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core import mushroom_worker_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8098)
    parser.add_argument("--worker-data-dir", type=Path, required=True)
    parser.add_argument("--ha-url", default=os.environ.get("RAINMAPPER_HA_URL", ""))
    parser.add_argument("--token", default=os.environ.get("RAINMAPPER_WORKER_TOKEN", ""))
    parser.add_argument("--display-name", default=os.environ.get("RAINMAPPER_WORKER_DISPLAY_NAME", ""))
    parser.add_argument("--host-name", default=os.environ.get("RAINMAPPER_WORKER_HOST_NAME", ""))
    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=float(os.environ.get("RAINMAPPER_WORKER_HEARTBEAT_INTERVAL", "10")),
    )
    args = parser.parse_args()
    mushroom_worker_service.serve(
        args.worker_data_dir,
        host=args.host,
        port=args.port,
        ha_url=args.ha_url,
        token=args.token,
        display_name=args.display_name,
        host_name=args.host_name,
        heartbeat_interval=args.heartbeat_interval,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
