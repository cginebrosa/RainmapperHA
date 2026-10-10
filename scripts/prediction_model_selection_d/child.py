"""Own-process RSS monitor: no process-table privilege or child processes."""
from __future__ import annotations
import json
import os
from pathlib import Path
import resource
import runpy
import sys
import threading
import time


def main():
    heartbeat = Path(sys.argv[1]).resolve()
    command = sys.argv[2:]
    root = Path(__file__).resolve().parents[2]
    allowed = (root / "tmp/prediction-model-selection/D-2026-10-05").resolve()
    if not heartbeat.is_relative_to(allowed):
        raise ValueError("Invalid heartbeat path")
    if command[:3] != [str(root / ".venv/bin/python"), "-B", "-m"] and command[:3] != [".venv/bin/python", "-B", "-m"]:
        raise ValueError("The isolated child only accepts a D study module")
    module = command[3]
    if module not in {"scripts.prediction_model_selection_d.study", "scripts.prediction_model_selection_d.analyze", "scripts.prediction_model_selection_d.common_weather", "scripts.prediction_model_selection_d.verify"}:
        raise ValueError("Unapproved D computation entrypoint")
    def audit(event, args):
        if event in {"subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec"}:
            raise PermissionError("Subprocesses are prohibited inside the isolated D computation")
    sys.addaudithook(audit)
    stopped = threading.Event()
    def sample():
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform != "darwin": rss *= 1024
        value = {"pid": os.getpid(), "peak_rss_bytes": rss, "sample_epoch": time.time()}
        temp = heartbeat.with_suffix(".partial")
        temp.write_text(json.dumps(value)+"\n")
        temp.replace(heartbeat)
        if rss > 8*1024**3:
            os._exit(88)
    def monitor():
        while not stopped.wait(.5): sample()
    sample()
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    sys.path.insert(0, str(root))
    sys.argv = [module, *command[4:]]
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    finally:
        stopped.set(); thread.join(timeout=2); sample()


if __name__ == "__main__": main()
