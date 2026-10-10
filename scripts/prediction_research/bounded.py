"""Run a single isolated research stage with hard, recorded resource ceilings."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from common import ROOT, OUTPUT, load, write_new

RSS_LIMIT = 8 * 1024**3
DISK_LIMIT = 2 * 1024**3
BATCH_SECONDS = 45 * 60
TOTAL_SECONDS = 120 * 60


def output_bytes():
    return sum(p.stat().st_size for p in OUTPUT.rglob("*") if p.is_file() and not p.is_symlink())


def process_tree(pid):
    # The child owns a new process group. Track it even if a descendant is orphaned.
    text = subprocess.check_output(["ps", "-axo", "pid=,pgid=,rss="], text=True)
    rows = [tuple(map(int, line.split())) for line in text.splitlines() if line.strip()]
    return {p: rss * 1024 for p, group, rss in rows if group == pid}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command or "/" in args.stage or args.stage in (".", ".."):
        parser.error("stage must be a basename; command is required")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "compute.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = OUTPUT / "runs"
        ledger.mkdir(exist_ok=True)
        previous = [load(p) for p in ledger.glob("*.json")]
        used = sum(float(p.get("elapsed_seconds", 0)) for p in previous)
        if any(p.get("status") == "running" for p in previous):
            raise SystemExit("Unreconciled running stage: inspect its PID and account resources first")
        allowed = min(BATCH_SECONDS, TOTAL_SECONDS - used)
        if allowed <= 0 or output_bytes() >= DISK_LIMIT:
            raise SystemExit("Research resource budget exhausted")
        result_path = ledger / f"{args.stage}.json"
        log_path = ledger / f"{args.stage}.log"
        if result_path.exists() or log_path.exists():
            raise SystemExit("Stage name already used; outputs are immutable")
        env = dict(os.environ)
        env.update({k: "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                     "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS")})
        env.update(PYTHONDONTWRITEBYTECODE="1", GDAL_PAM_ENABLED="NO", PROJ_NETWORK="OFF",
                   RAINMAPPER_PREDICTION_RESEARCH_GUARDED="1")
        start = time.monotonic()
        result = {"stage": args.stage, "command": args.command, "status": "running",
                  "rss_limit_bytes": RSS_LIMIT, "rss_measurement": "sampled_per_process_every_0.5s",
                  "elapsed_seconds": allowed, "budget_reserved_seconds": allowed,
                  "started_at_epoch": time.time(), "max_rss_bytes": 0, "max_output_bytes": output_bytes()}
        write_new(result_path, result)
        reason = None
        with log_path.open("x") as log:
            process = subprocess.Popen(args.command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            result["pid"] = process.pid
            result_path.write_text(json.dumps(result) + "\n")
            try:
                while process.poll() is None:
                    rss = process_tree(process.pid)
                    size = output_bytes()
                    result["max_rss_bytes"] = max(result["max_rss_bytes"], max(rss.values(), default=0))
                    result["max_output_bytes"] = max(result["max_output_bytes"], size)
                    elapsed = time.monotonic() - start
                    if max(rss.values(), default=0) > RSS_LIMIT:
                        reason = "rss_limit"
                    elif size > DISK_LIMIT:
                        reason = "output_limit"
                    elif elapsed > allowed:
                        reason = "time_limit"
                    if reason:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                        break
                    time.sleep(0.5)
            except BaseException:
                reason = "interrupted"
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                raise
            finally:
                process.wait()
                survivors = process_tree(process.pid)
                if survivors:
                    os.killpg(process.pid, signal.SIGTERM)
                    time.sleep(0.1)
                    if process_tree(process.pid):
                        os.killpg(process.pid, signal.SIGKILL)
                    reason = reason or "surviving_descendants"
                size = output_bytes()
                result["max_output_bytes"] = max(size, result["max_output_bytes"])
                if size > DISK_LIMIT:
                    reason = reason or "output_limit"
                if time.monotonic() - start > allowed:
                    reason = reason or "time_limit"
                result.update(elapsed_seconds=time.monotonic()-start, returncode=process.returncode,
                              status="completed" if process.returncode == 0 and reason is None else "stopped",
                              stop_reason=reason)
                result_path.write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps(result), flush=True)
        return process.returncode if process.returncode else (1 if reason else 0)


if __name__ == "__main__":
    raise SystemExit(main())
