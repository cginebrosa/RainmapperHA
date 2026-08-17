#!/usr/bin/env python3
"""Build disposable V2--V6 benchmark inputs from one immutable live snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import sys
from pathlib import Path
from typing import Callable, TextIO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts-dir", type=Path, default=Path("/app/scripts"))
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--known-sites", type=Path, required=True)
    parser.add_argument("--observation-features", type=Path, required=True)
    parser.add_argument("--stations-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-snapshot-id", required=True)
    parser.add_argument("--progress-jsonl", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def emit_progress(
    path: Path | None,
    *,
    step: int,
    total: int,
    phase: str,
    detail: str | None = None,
) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        event = {"completed_step_count": step, "planned_step_count": total, "phase": phase}
        if detail:
            event["detail"] = detail
        handle.write(json.dumps(event) + "\n")


class _JsonLineTee:
    def __init__(self, destination: TextIO, callback: Callable[[dict[str, object]], None]):
        self.destination = destination
        self.callback = callback
        self.buffer = ""

    def write(self, value: str) -> int:
        written = self.destination.write(value)
        self.buffer += value
        while "\n" in self.buffer:
            raw, self.buffer = self.buffer.split("\n", 1)
            try:
                event = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(event, dict):
                self.callback(event)
        return written

    def flush(self) -> None:
        self.destination.flush()

    def __getattr__(self, name: str) -> object:
        return getattr(self.destination, name)


def _event_detail(event: dict[str, object]) -> str | None:
    for completed_key, total_key, label in (
        ("cached_microareas", "total_microareas", "microareas cached"),
        ("completed_area_cutoffs", "total_area_cutoffs", "area cutoffs completed"),
        ("materialized_area_cutoffs", "total_area_cutoffs", "area cutoffs materialized"),
    ):
        if completed_key in event and total_key in event:
            return f"{event[completed_key]}/{event[total_key]} {label}."
    if event.get("comparison") and event.get("dataset"):
        return f"{event['comparison']} · {event['dataset']}"
    if event.get("temporal") and event.get("split"):
        return f"{event['temporal']} · {event['split']}"
    return None


def run_script(
    path: Path,
    arguments: list[str],
    *,
    progress_event: Callable[[dict[str, object]], None] | None = None,
) -> None:
    namespace = runpy.run_path(str(path), run_name=f"rainmapper_multiversion_{path.stem}")
    main = namespace.get("main")
    if not callable(main):
        raise RuntimeError(f"benchmark script does not expose main(): {path}")
    previous_argv = sys.argv
    previous_stdout = sys.stdout
    try:
        sys.argv = [str(path), *arguments]
        if progress_event is not None:
            sys.stdout = _JsonLineTee(previous_stdout, progress_event)  # type: ignore[assignment]
        result = main()
    finally:
        sys.argv = previous_argv
        sys.stdout = previous_stdout
    if result not in (None, 0):
        raise RuntimeError(f"benchmark script failed with status {result}: {path}")


def artifact_manifest(kind: str, root: Path, names: list[str], source_snapshot_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "kind": kind,
        "source_snapshot_id": source_snapshot_id,
        "artifacts": {
            name: {"sha256": sha256(root / name), "size_bytes": (root / name).stat().st_size}
            for name in names
        },
        "model_artifact_written": False,
        "operational_candidate_trained": False,
    }


def main() -> int:
    args = parse_args()
    scripts = args.scripts_dir.resolve()
    root = args.output_dir.resolve()
    snapshot = root / "snapshot"
    v5 = root / "v5"
    v6 = root / "v6"
    snapshot.mkdir(parents=True, exist_ok=False)
    v5.mkdir()
    v6.mkdir()
    total = 8

    def stage_progress(step: int, phase: str) -> Callable[[dict[str, object]], None]:
        def publish(event: dict[str, object]) -> None:
            detail = _event_detail(event)
            if detail:
                emit_progress(
                    args.progress_jsonl,
                    step=step - 1,
                    total=total,
                    phase=phase,
                    detail=detail,
                )

        return publish

    v3_fixed = snapshot / "biology-v3-fixed.json"
    v3_lag = snapshot / "biology-v3-lag.json"
    common_v3 = [
        "--data-dir", str(args.data_dir),
        "--observations", str(args.observations),
        "--known-sites", str(args.known_sites),
        "--observation-features", str(args.observation_features),
        "--stations-file", str(args.stations_file),
    ]
    emit_progress(args.progress_jsonl, step=0, total=total, phase="Building V3 fixed-window inputs")
    run_script(
        scripts / "build-biology-v3-benchmark.py",
        [*common_v3, "--feature-set", "fixed_gap_7d_biology_v3", "--output", str(v3_fixed)],
        progress_event=stage_progress(1, "Building V3 fixed-window inputs"),
    )
    emit_progress(args.progress_jsonl, step=1, total=total, phase="Built V3 fixed-window inputs")
    emit_progress(args.progress_jsonl, step=1, total=total, phase="Building V3 lag/event inputs")
    run_script(
        scripts / "build-biology-v3-benchmark.py",
        [*common_v3, "--feature-set", "lag_event_biology_v3", "--output", str(v3_lag)],
        progress_event=stage_progress(2, "Building V3 lag/event inputs"),
    )
    emit_progress(args.progress_jsonl, step=2, total=total, phase="Built V3 lag/event inputs")

    v4_fixed = snapshot / "biology-v4-fixed.json"
    v4_lag = snapshot / "biology-v4-lag.json"
    for step, source, output, phase in (
        (3, v3_fixed, v4_fixed, "Built V4 fixed-window inputs"),
        (4, v3_lag, v4_lag, "Built V4 lag/event inputs"),
    ):
        emit_progress(args.progress_jsonl, step=step - 1, total=total, phase=phase.replace("Built", "Building"))
        run_script(
            scripts / "build-biology-v4-benchmark.py",
            [
                "--v3-benchmark", str(source),
                "--data-dir", str(args.data_dir),
                "--known-sites", str(args.known_sites),
                "--stations-file", str(args.stations_file),
                "--output", str(output),
            ],
            progress_event=stage_progress(step, phase.replace("Built", "Building")),
        )
        emit_progress(args.progress_jsonl, step=step, total=total, phase=phase)

    snapshot_names = [path.name for path in (v3_fixed, v3_lag, v4_fixed, v4_lag)]
    write_json(
        snapshot / "MANIFEST.json",
        artifact_manifest(
            "mushroom_ml_dynamic_v3_v4_snapshot",
            snapshot,
            snapshot_names,
            args.source_snapshot_id,
        ),
    )
    emit_progress(args.progress_jsonl, step=4, total=total, phase="Building V5 raw-weather inputs")
    run_script(
        scripts / "build-biology-v5-raw-benchmark.py",
        [
            "--v3-fixed", str(v3_fixed),
            "--v3-lag", str(v3_lag),
            "--data-dir", str(args.data_dir),
            "--known-sites", str(args.known_sites),
            "--stations-file", str(args.stations_file),
            "--output-dir", str(v5),
        ],
        progress_event=stage_progress(5, "Building V5 raw-weather inputs"),
    )
    emit_progress(args.progress_jsonl, step=5, total=total, phase="Built V5 raw-weather inputs")
    emit_progress(args.progress_jsonl, step=5, total=total, phase="Evaluating V2--V5 hold-out rows")
    run_script(
        scripts / "evaluate-biology-v5-raw-benchmark.py",
        ["--snapshot", str(snapshot), "--v5-dir", str(v5)],
        progress_event=stage_progress(6, "Evaluating V2--V5 hold-out rows"),
    )
    emit_progress(args.progress_jsonl, step=6, total=total, phase="Evaluated V2--V5 hold-out rows")
    v5_names = sorted(path.name for path in v5.iterdir() if path.is_file())
    write_json(
        v5 / "MANIFEST.json",
        artifact_manifest(
            "mushroom_ml_dynamic_v5_evaluation",
            v5,
            v5_names,
            args.source_snapshot_id,
        ),
    )
    emit_progress(args.progress_jsonl, step=6, total=total, phase="Evaluating V6 hold-out rows")
    run_script(
        scripts / "evaluate-biology-v6-smooth-hierarchical.py",
        ["--snapshot", str(snapshot), "--v5-dir", str(v5), "--output-dir", str(v6)],
        progress_event=stage_progress(7, "Evaluating V6 hold-out rows"),
    )
    emit_progress(args.progress_jsonl, step=7, total=total, phase="Evaluated V6 hold-out rows")

    prepared = {
        "schema_version": "1.0",
        "kind": "mushroom_ml_prepared_multiversion_inputs",
        "source_snapshot_id": args.source_snapshot_id,
        "inputs": {
            "v3_fixed": str(v3_fixed),
            "v3_lag": str(v3_lag),
            "v4_fixed": str(v4_fixed),
            "v4_lag": str(v4_lag),
            "v5_fixed": str(v5 / "biology-v5-fixed.json"),
            "v5_lag": str(v5 / "biology-v5-lag.json"),
            "v2_v5_heldout": str(v5 / "heldout-predictions.jsonl"),
            "v6_heldout": str(v6 / "heldout-predictions.jsonl"),
        },
        "operational_candidate_trained": False,
    }
    write_json(root / "prepared-inputs.json", prepared)
    emit_progress(args.progress_jsonl, step=8, total=total, phase="Prepared disposable V2--V6 inputs")
    print(json.dumps({"output": str(root / "prepared-inputs.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
