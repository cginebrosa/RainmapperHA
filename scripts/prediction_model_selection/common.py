"""Helpers confined to the local prediction study; no operational writes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OLD_OUTPUT = ROOT / "tmp/prediction-research"
OUTPUT = ROOT / "tmp/prediction-model-selection"
TARGETS = ("boletus_aereus", "amanita_caesarea")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def write_new(path: Path, value) -> None:
    path = path.resolve()
    if not path.is_relative_to(OUTPUT.resolve()):
        raise ValueError("Research outputs must stay under the ignored study directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        stream.write("\n")


def verify_inputs(manifest) -> None:
    for entry in manifest["inputs"]:
        path = ROOT / entry["path"]
        if path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            raise ValueError(f"Frozen input changed: {entry['path']}")


def protect_originals() -> None:
    """Reject Python filesystem mutations outside the private research outputs."""
    allowed = OUTPUT.resolve()

    def check(path):
        if isinstance(path, int):
            return  # Existing stdout/stderr descriptors; no new file path.
        if not Path(os.fsdecode(path)).resolve().is_relative_to(allowed):
            raise PermissionError("Research process attempted a write outside its output directory")

    def audit(event, args):
        if event == "open":
            path, mode, flags = args
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                check(path)
        elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.utime", "os.truncate"}:
            check(args[0])
        elif event in {"os.rename", "os.link"}:
            check(args[0]); check(args[1])
        elif event == "os.symlink":
            check(args[1])

    sys.addaudithook(audit)
