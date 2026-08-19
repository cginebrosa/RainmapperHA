"""Immutable scientific benchmark reports and archive discovery."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from rainmapper_core import mushroom_ml_quality_catalog


SCHEMA_VERSION = "1.0"
KIND = "mushroom_ml_benchmark_report"
REPORT_NAME = "benchmark-report.json"
PREDICTIONS_NAME = "holdout-predictions.jsonl"


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
    report_path = root / REPORT_NAME
    return validate_report(
        json.loads(report_path.read_text(encoding="utf-8")),
        root=root,
    )


def list_reports(models_root: Path) -> list[dict[str, Any]]:
    archive_root = Path(models_root).resolve() / "benchmarks"
    if not archive_root.is_dir():
        return []
    reports: list[dict[str, Any]] = []
    for directory in archive_root.iterdir():
        if not directory.is_dir() or not (directory / REPORT_NAME).is_file():
            continue
        try:
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
            }
        )
    return sorted(
        reports,
        key=lambda row: (str(row.get("created_at") or ""), str(row["batch_id"])),
        reverse=True,
    )
