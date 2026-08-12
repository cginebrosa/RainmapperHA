"""Shared exit-code and disk gates for the partitioned weather pipeline."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_DOWNLOAD_REQUIRED_BYTES = 256 * 1024**2
DEFAULT_FREE_RESERVE_BYTES = 512 * 1024**2


class WeatherDiskPreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class WeatherDiskPreflight:
    path: str
    free_bytes: int
    required_bytes: int
    reserve_bytes: int


def combine_update_exit_codes(source_code: int, archive_code: int) -> int:
    """Persistence failure wins; provider degradation remains exit 2."""
    if archive_code != 0:
        return 1
    if source_code == 0:
        return 0
    if source_code == 2:
        return 2
    return 1


def check_download_disk_preflight(
    data_dir: Path,
    *,
    required_bytes: int = DEFAULT_DOWNLOAD_REQUIRED_BYTES,
    reserve_bytes: int = DEFAULT_FREE_RESERVE_BYTES,
) -> WeatherDiskPreflight:
    """Reject a weather download before network work if disk margin is unsafe."""
    if required_bytes < 0 or reserve_bytes < 0:
        raise ValueError("disk byte budgets cannot be negative")
    path = Path(data_dir)
    probe = path if path.exists() else path.parent
    free = shutil.disk_usage(probe).free
    report = WeatherDiskPreflight(
        path=str(path),
        free_bytes=free,
        required_bytes=required_bytes,
        reserve_bytes=reserve_bytes,
    )
    if free - required_bytes < reserve_bytes:
        raise WeatherDiskPreflightError(
            "Insufficient disk before weather download: "
            f"free={free}, required={required_bytes}, reserve={reserve_bytes}"
        )
    return report


def _env_bytes(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    combine = subparsers.add_parser("combine-exit-codes")
    combine.add_argument("--source", type=int, required=True)
    combine.add_argument("--archive", type=int, required=True)
    preflight = subparsers.add_parser("download-preflight")
    preflight.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "combine-exit-codes":
        return combine_update_exit_codes(args.source, args.archive)
    report = check_download_disk_preflight(
        args.data_dir,
        required_bytes=_env_bytes(
            "RAINMAPPER_WEATHER_DOWNLOAD_REQUIRED_BYTES",
            DEFAULT_DOWNLOAD_REQUIRED_BYTES,
        ),
        reserve_bytes=_env_bytes(
            "RAINMAPPER_WEATHER_FREE_RESERVE_BYTES",
            DEFAULT_FREE_RESERVE_BYTES,
        ),
    )
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
