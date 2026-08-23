"""Rebase the active weather-history generation as a standalone root."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from rainmapper_core.weather_history_writer import rebase_current_generation_as_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    report = rebase_current_generation_as_root(args.data_dir)
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
