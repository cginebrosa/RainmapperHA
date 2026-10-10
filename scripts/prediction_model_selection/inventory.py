"""Freeze references to the closed study without copying its datasets or models."""
from __future__ import annotations
from collections import Counter
import os
import time
from scripts.prediction_model_selection.common import (
    ROOT, OUTPUT, OLD_OUTPUT, TARGETS, digest, load, write_new, verify_inputs, protect_originals,
)


def main():
    if os.environ.get("RAINMAPPER_MODEL_SELECTION_GUARDED") != "1":
        raise SystemExit("Launch through bounded.py")
    protect_originals()
    cohort = load(OLD_OUTPUT / "cohort-v2.json")
    verify_inputs(cohort)
    closed = load(OLD_OUTPUT / "closure.json")
    for record in closed["delivery_files"]:
        if record["path"].startswith(("scripts/", "tests/")):
            if digest(ROOT / record["path"]) != record["sha256"]:
                raise ValueError("Closed study source changed")
    records = []
    for path in sorted(OLD_OUTPUT.rglob("*")):
        if path.is_file() and not path.is_symlink():
            records.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                            "sha256": digest(path)})
    ledgers = [load(p) for p in (OLD_OUTPUT / "runs").glob("*.json")]
    if any(x.get("status") == "running" for x in ledgers):
        raise ValueError("Prior study has a running stage")
    counts = {}
    for fold, roles in cohort["folds"].items():
        counts[fold] = {}
        for sid in TARGETS:
            counts[fold][sid] = {}
            for role in ("fit", "ranking", "threshold", "external"):
                rows = [r for r in cohort["rows"] if r["species_id"] == sid and roles[r["observation_id"]] == role]
                counts[fold][sid][role] = {"observations": len(rows), "positive": sum(r["y"] for r in rows),
                    "episodes": len({r["episode_id"] for r in rows})}
    protocol = ROOT / "docs/agents/prediction-model-selection/protocolo-ejecucion-2026-10-04.md"
    write_new(OUTPUT / "inventory.json", {"created_at_epoch": time.time(),
        "status": "verified", "cohort_sha256": digest(OLD_OUTPUT / "cohort-v2.json"),
        "protocol": {"path": str(protocol.relative_to(ROOT)), "sha256": digest(protocol)},
        "old_files": records, "old_bytes": sum(r["bytes"] for r in records),
        "old_supervised_seconds": sum(r.get("elapsed_seconds", 0) for r in ledgers),
        "counts": counts, "independent_confirmation": False})
    print({"status": "verified", "old_files": len(records), "old_bytes": sum(r["bytes"] for r in records)})


if __name__ == "__main__":
    main()
