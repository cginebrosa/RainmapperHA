"""Cross-process lock for complete weather update pipelines."""

from __future__ import annotations

import argparse
import fcntl
import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, Sequence


class WeatherRunBusy(RuntimeError):
    pass


def acquire_run_lock(path: Path, timeout_seconds: float = 30.0) -> BinaryIO:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if time.monotonic() >= deadline:
                handle.close()
                raise WeatherRunBusy(
                    f"Timed out waiting for weather run lock after {timeout_seconds}s"
                )
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


def release_run_lock(handle: BinaryIO | None) -> None:
    if handle is None or handle.closed:
        return
    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    handle.close()


@contextmanager
def weather_run_lock(path: Path, timeout_seconds: float = 30.0) -> Iterator[None]:
    handle = acquire_run_lock(path, timeout_seconds)
    try:
        yield
    finally:
        release_run_lock(handle)


def run_locked(path: Path, command: Sequence[str], timeout_seconds: float = 30.0) -> int:
    with weather_run_lock(path, timeout_seconds):
        return subprocess.run(list(command), check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    return run_locked(args.lock, command, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
