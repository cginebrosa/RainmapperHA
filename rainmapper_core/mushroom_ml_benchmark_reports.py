"""Immutable scientific benchmark reports and archive discovery."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from rainmapper_core import mushroom_ml_quality_catalog


SCHEMA_VERSION = "1.0"
KIND = "mushroom_ml_benchmark_report"
REPORT_NAME = "benchmark-report.json"
PREDICTIONS_NAME = "holdout-predictions.jsonl"
EVIDENCE_MANIFEST_NAME = "evidence-manifest.json"
EVIDENCE_KIND = "mushroom_ml_benchmark_evidence"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _report_id(payload: Mapping[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "report_id"}
    return "sha256:" + hashlib.sha256(_canonical(unsigned)).hexdigest()


def _family(contract_id: object) -> str:
    value = str(contract_id or "")
    if value.startswith("fixed_gap_"):
        return "fixed"
    if value.startswith("lag_event_"):
        return "lag"
    return "unknown"


def _selected_rows(
    v2_v5_path: Path,
    v6_path: Path,
    profile_keys: set[str],
) -> Iterable[dict[str, Any]]:
    sources = (
        mushroom_ml_quality_catalog._rows(v2_v5_path),
        mushroom_ml_quality_catalog._rows(
            v6_path,
            version_id="biology_v6_smooth_hierarchical",
            profile_id="smooth_weather_physical_state",
        ),
    )
    for source in sources:
        for raw in source:
            row = dict(raw)
            profile_key = f"{row.get('version_id', '')}/{row.get('profile_id', '')}"
            if profile_key in profile_keys:
                yield row


def _duration_summary(fit_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    total = 0.0
    for fit in fit_results:
        artifact_ref = fit.get("artifact_ref")
        if not isinstance(artifact_ref, Mapping):
            continue
        duration = fit.get("duration_seconds")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration < 0:
            continue
        value = float(duration)
        total += value
        grouped[
            (
                str(artifact_ref.get("version_id") or ""),
                str(artifact_ref.get("profile_id") or ""),
                str(artifact_ref.get("estimator_id") or ""),
            )
        ].append(value)
    return {
        "total_fit_seconds": round(total, 6),
        "groups": [
            {
                "version_id": key[0],
                "profile_id": key[1],
                "estimator_id": key[2],
                "fit_count": len(values),
                "total_seconds": round(sum(values), 6),
                "mean_seconds": round(sum(values) / len(values), 6),
            }
            for key, values in sorted(grouped.items())
        ],
    }


def _metrics_with_fit_diagnostics(
    entries: Sequence[Mapping[str, Any]],
    fit_results: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    exact: dict[tuple[str, ...], Mapping[str, Any]] = {}
    shared: dict[tuple[str, ...], Mapping[str, Any]] = {}
    for fit in fit_results:
        ref = fit.get("artifact_ref")
        if not isinstance(ref, Mapping):
            continue
        key = (
            str(ref.get("version_id") or ""),
            str(ref.get("profile_id") or ""),
            _family(ref.get("temporal_contract_id")),
            str(ref.get("species_id") or ""),
            str(ref.get("estimator_id") or ""),
        )
        exact[key] = fit
        if key[3] == "all_species":
            shared[(key[0], key[1], key[2], key[4])] = fit
    result: list[dict[str, Any]] = []
    for raw in entries:
        row = dict(raw)
        key = (
            str(row.get("version_id") or ""),
            str(row.get("profile_id") or ""),
            str(row.get("temporal_family") or ""),
            str(row.get("species_id") or ""),
            str(row.get("estimator_id") or ""),
        )
        fit = exact.get(key) or shared.get((key[0], key[1], key[2], key[4]))
        row["fit_status"] = str(fit.get("status") or "not_planned") if fit else "not_planned"
        row["fit_duration_seconds"] = fit.get("duration_seconds") if fit else None
        row["fit_failure_reason"] = str(fit.get("reason") or "") if fit else ""
        result.append(row)
    return result


def write_report(
    batch_dir: Path,
    *,
    job_id: str,
    training_plan: Mapping[str, Any],
    selected_profiles: Sequence[Mapping[str, str]],
    quality_catalog: Mapping[str, Any],
    fit_results: Sequence[Mapping[str, Any]],
    failed_fits: Sequence[Mapping[str, Any]],
    v2_v5_predictions_path: Path,
    v6_predictions_path: Path,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Persist one self-contained report and filtered row-level hold-out evidence."""
    root = Path(batch_dir)
    profile_keys = {str(row["profile_key"]) for row in selected_profiles}
    predictions_path = root / PREDICTIONS_NAME
    prediction_count = 0
    with predictions_path.open("x", encoding="utf-8") as handle:
        for row in _selected_rows(
            v2_v5_predictions_path,
            v6_predictions_path,
            profile_keys,
        ):
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            prediction_count += 1
    if prediction_count == 0:
        raise ValueError("Scientific benchmark produced no selected hold-out predictions")
    checked_fit_results = [dict(row) for row in fit_results]
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "batch_id": str(training_plan["batch_id"]),
        "job_id": str(job_id),
        "snapshot_id": str(training_plan["snapshot_id"]),
        "created_at": created_at or datetime.now(UTC).isoformat(timespec="seconds"),
        "selection": {
            "version_ids": list(training_plan.get("version_ids") or []),
            "profile_keys": list(training_plan.get("profile_keys") or []),
            "profiles": [dict(row) for row in selected_profiles],
            "species_ids": list(training_plan.get("species_ids") or []),
        },
        "training_plan": dict(training_plan),
        "metrics": _metrics_with_fit_diagnostics(
            [row for row in quality_catalog.get("entries", []) if isinstance(row, Mapping)],
            checked_fit_results,
        ),
        "fit_results": checked_fit_results,
        "fit_failures": [dict(row) for row in failed_fits],
        "duration_summary": _duration_summary(checked_fit_results),
        "holdout_predictions": {
            "path": PREDICTIONS_NAME,
            "sha256": sha256(predictions_path),
            "size_bytes": predictions_path.stat().st_size,
            "row_count": prediction_count,
        },
        "species_metrics_are_never_averaged": True,
        "winner_declared": False,
        "operational_candidate_trained": False,
    }
    report["summary"] = {
        "profile_count": len(report["selection"]["profile_keys"]),
        "species_count": len(report["selection"]["species_ids"]),
        "planned_fit_count": int(training_plan.get("fit_count", 0)),
        "successful_fit_count": sum(
            1 for row in checked_fit_results if row.get("status") == "complete"
        ),
        "failed_fit_count": sum(
            1 for row in checked_fit_results if row.get("status") == "failed"
        ),
        "metric_count": len(report["metrics"]),
        "holdout_prediction_count": prediction_count,
    }
    report["report_id"] = _report_id(report)
    report_path = root / REPORT_NAME
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "report": report,
        "report_path": report_path,
        "predictions_path": predictions_path,
    }


def validate_report(payload: object, *, root: Path | None = None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("Benchmark report must be an object")
    report = dict(payload)
    if report.get("schema_version") != SCHEMA_VERSION or report.get("kind") != KIND:
        raise ValueError("Benchmark report contract is invalid")
    batch_id = str(report.get("batch_id") or "")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", batch_id):
        raise ValueError("Benchmark report batch_id is invalid")
    if report.get("report_id") != _report_id(report):
        raise ValueError("Benchmark report identity is invalid")
    if report.get("species_metrics_are_never_averaged") is not True:
        raise ValueError("Benchmark report must keep species metrics separate")
    predictions = report.get("holdout_predictions")
    if not isinstance(predictions, Mapping) or predictions.get("path") != PREDICTIONS_NAME:
        raise ValueError("Benchmark report hold-out reference is invalid")
    if root is not None:
        path = Path(root) / PREDICTIONS_NAME
        if (
            not path.is_file()
            or path.stat().st_size != predictions.get("size_bytes")
            or sha256(path) != predictions.get("sha256")
        ):
            raise ValueError("Benchmark report hold-out predictions failed integrity checks")
    return report


def load_report(models_root: Path, batch_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", str(batch_id or "")):
        raise ValueError("Benchmark batch identity is invalid")
    root = Path(models_root).resolve() / "benchmarks" / batch_id
    evidence_path = root / EVIDENCE_MANIFEST_NAME
    if evidence_path.is_file():
        _validate_evidence_manifest(root, batch_id)
    report_path = root / REPORT_NAME
    return validate_report(
        json.loads(report_path.read_text(encoding="utf-8")),
        root=root,
    )


def _validate_evidence_manifest(root: Path, batch_id: str) -> dict[str, Any]:
    """Validate evidence identity and every retained file before serving it."""
    evidence = _json_object(root / EVIDENCE_MANIFEST_NAME)
    if (
        evidence.get("schema_version") != SCHEMA_VERSION
        or evidence.get("kind") != EVIDENCE_KIND
        or evidence.get("state") != "evidence_only"
        or evidence.get("batch_id") != batch_id
    ):
        raise ValueError("Benchmark evidence manifest is invalid")
    files = evidence.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Benchmark evidence file inventory is invalid")
    expected_names = {
        REPORT_NAME,
        PREDICTIONS_NAME,
        "quality-catalog.json",
        "training-input-manifest.json",
    }
    seen: set[str] = set()
    for row in files:
        if not isinstance(row, Mapping):
            raise ValueError("Benchmark evidence file entry is invalid")
        name = str(row.get("path") or "")
        if name not in expected_names or name in seen:
            raise ValueError("Benchmark evidence file inventory is invalid")
        path = root / name
        if (
            path.is_symlink()
            or not path.is_file()
            or path.resolve().parent != root.resolve()
            or path.stat().st_size != row.get("size_bytes")
            or sha256(path) != row.get("sha256")
        ):
            raise ValueError(f"Benchmark evidence file failed integrity checks: {name}")
        seen.add(name)
    if seen != expected_names:
        raise ValueError("Benchmark evidence file inventory is incomplete")
    return evidence


def benchmark_evidence_plan(models_root: Path, batch_id: str) -> dict[str, Any]:
    """Validate one benchmark and describe conversion to non-installable evidence."""
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", str(batch_id or "")):
        raise ValueError("Benchmark batch identity is invalid")
    root = Path(models_root).resolve() / "benchmarks" / batch_id
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Archived benchmark batch not found: {batch_id}")
    evidence_path = root / EVIDENCE_MANIFEST_NAME
    if evidence_path.is_file():
        _validate_evidence_manifest(root, batch_id)
        return {"batch_id": batch_id, "status": "evidence_only", "remove": [], "recoverable_bytes": 0}
    report = load_report(models_root, batch_id)
    manifest_path = root / "manifest.json"
    manifest = _json_object(manifest_path)
    if manifest.get("batch_id") != batch_id or manifest.get("job_purpose") != "benchmark":
        raise ValueError("Benchmark installable manifest identity is invalid")
    keep_names = {
        REPORT_NAME,
        PREDICTIONS_NAME,
        "quality-catalog.json",
        "training-input-manifest.json",
    }
    files: list[dict[str, Any]] = []
    for name in sorted(keep_names):
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Benchmark evidence file is missing: {name}")
        files.append(
            {"path": name, "size_bytes": path.stat().st_size, "sha256": sha256(path)}
        )
    remove = [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.relative_to(root).as_posix() not in keep_names
        and path.relative_to(root).as_posix() != EVIDENCE_MANIFEST_NAME
    ]
    return {
        "batch_id": batch_id,
        "status": "installable",
        "report_id": report["report_id"],
        "snapshot_id": report.get("snapshot_id", ""),
        "original_manifest_sha256": sha256(manifest_path),
        "input_revisions": manifest.get("input_revisions"),
        "files": files,
        "remove": remove,
        "recoverable_bytes": sum(int(row["size_bytes"]) for row in remove),
    }


def compact_benchmark_to_evidence(
    models_root: Path, batch_id: str, *, plan: dict[str, Any]
) -> dict[str, Any]:
    """Publish evidence-only identity before removing installable model binaries."""
    fresh = benchmark_evidence_plan(models_root, batch_id)
    if fresh.get("remove") != plan.get("remove") or fresh.get("status") != plan.get("status"):
        raise ValueError("Benchmark archive changed after compaction planning")
    if fresh["status"] == "evidence_only":
        return fresh
    root = Path(models_root).resolve() / "benchmarks" / batch_id
    evidence = {
        "schema_version": "1.0",
        "kind": EVIDENCE_KIND,
        "state": "evidence_only",
        "batch_id": batch_id,
        "report_id": fresh["report_id"],
        "snapshot_id": fresh["snapshot_id"],
        "original_manifest_sha256": fresh["original_manifest_sha256"],
        "input_revisions": fresh.get("input_revisions"),
        "files": fresh["files"],
        "compacted_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{EVIDENCE_MANIFEST_NAME}.", suffix=".tmp", dir=root
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, root / EVIDENCE_MANIFEST_NAME)
    finally:
        temporary.unlink(missing_ok=True)
    removed: list[str] = []
    for entry in fresh["remove"]:
        path = root / str(entry["path"])
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root)
        ):
            raise ValueError("Benchmark compaction path is unsafe")
        path.unlink()
        removed.append(str(entry["path"]))
    for directory in sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    return {
        "batch_id": batch_id,
        "status": "evidence_only",
        "removed": removed,
        "recoverable_bytes": fresh["recoverable_bytes"],
    }


def _json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return payload


def delete_report(models_root: Path, batch_id: str) -> None:
    """Permanently remove one archived benchmark batch from disk.

    Scientific benchmarks are deliberately not covered by the registry's
    permanent-retention policy (that policy applies to registered version
    generations, not to raw benchmark batches on disk): the user wants a
    living, prunable history so only interesting runs are kept.
    """
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", str(batch_id or "")):
        raise ValueError("Benchmark batch identity is invalid")
    archive_root = Path(models_root).resolve() / "benchmarks"
    root = archive_root / batch_id
    if root.resolve().parent != archive_root.resolve() or not root.is_dir():
        raise ValueError(f"Archived benchmark batch not found: {batch_id}")
    manifest_path = root / "manifest.json"
    evidence_path = root / EVIDENCE_MANIFEST_NAME
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("job_purpose") != "benchmark":
            raise ValueError("Only archived scientific benchmarks can be deleted this way")
    elif evidence_path.is_file():
        _validate_evidence_manifest(root, batch_id)
    else:
        raise ValueError(f"Archived benchmark batch has no manifest: {batch_id}")
    shutil.rmtree(root)


def list_reports(models_root: Path) -> list[dict[str, Any]]:
    archive_root = Path(models_root).resolve() / "benchmarks"
    if not archive_root.is_dir():
        return []
    reports: list[dict[str, Any]] = []
    for directory in archive_root.iterdir():
        if not directory.is_dir() or not (directory / REPORT_NAME).is_file():
            continue
        try:
            if (directory / EVIDENCE_MANIFEST_NAME).is_file():
                _validate_evidence_manifest(directory, directory.name)
            report = validate_report(
                json.loads((directory / REPORT_NAME).read_text(encoding="utf-8")),
                root=directory,
            )
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        reports.append(
            {
                "batch_id": report["batch_id"],
                "report_id": report["report_id"],
                "created_at": report.get("created_at", ""),
                "snapshot_id": report.get("snapshot_id", ""),
                "selection": report.get("selection", {}),
                "summary": report.get("summary", {}),
                "storage_state": (
                    "evidence_only"
                    if (directory / EVIDENCE_MANIFEST_NAME).is_file()
                    else "installable"
                ),
            }
        )
    return sorted(
        reports,
        key=lambda row: (str(row.get("created_at") or ""), str(row["batch_id"])),
        reverse=True,
    )
