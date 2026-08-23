"""Auditable dry-run/apply reconciliation for persistent worker storage."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_worker_jobs
from rainmapper_core import mushroom_ml_storage_reconciler
from rainmapper_core import mushroom_worker_results
from rainmapper_core import mushroom_worker_transport
from rainmapper_core import mushroom_paths


_RESULT_DIR_RE = re.compile(r"^(?:ml\.)?(worker_job_[a-zA-Z0-9_-]{8,80})$")
_RESULT_STAGING_RE = re.compile(
    r"^\.(?:ml\.)?(worker_job_[a-zA-Z0-9_-]{8,80})\.staging(?:-[a-f0-9]{32})?$"
)
OPERATIONAL_RESULT_RETENTION_SECONDS = 24 * 60 * 60


def _tree_size(path: Path) -> int:
    if not path.exists() or path.is_symlink():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.iterdir():
        if child.is_symlink():
            continue
        total += _tree_size(child)
    return total


def _inventory(path: Path) -> dict[str, Any]:
    root = Path(path)
    if not root.is_dir() or root.is_symlink():
        return {"path": str(root), "entries": 0, "bytes": 0}
    entries = [child for child in root.iterdir() if not child.is_symlink()]
    return {
        "path": str(root),
        "entries": len(entries),
        "bytes": sum(_tree_size(child) for child in entries),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _planned_names(report: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    return [
        str(name)
        for key in keys
        for name in report.get(key, [])
        if isinstance(name, str)
    ]


def _validate_result_identity(
    path: Path, job_id: str, *, required: bool = True
) -> None:
    identity_paths = (
        path / "candidate_verification.json",
        path / "promotion_receipt.json",
        path / "multiversion" / "multiversion_result.json",
    )
    seen = False
    for identity_path in identity_paths:
        if not identity_path.is_file():
            continue
        seen = True
        try:
            payload = json.loads(identity_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid result identity {identity_path.name}: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("job_id") != job_id:
            raise ValueError(f"result identity mismatch for {path.name}")
    if required and not seen:
        raise ValueError(f"result identity is missing for {path.name}")


def _plan_orphan_results(
    result_root: Path,
    jobs: list[dict[str, Any]],
    *,
    now: float | None,
    orphan_grace_seconds: int,
    staging_grace_seconds: int,
    terminal_retention_seconds: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "planned_orphan": [],
        "planned_empty": [],
        "planned_staging": [],
        "planned_terminal": [],
        "retained": [],
        "errors": [],
    }
    root = Path(result_root)
    if not root.exists():
        return report
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Worker candidate result root must be a real directory.")
    jobs_by_id = {
        str(job.get("job_id", "")): job
        for job in jobs
        if isinstance(job, dict)
        and mushroom_worker_jobs.JOB_ID_PATTERN.fullmatch(str(job.get("job_id", "")))
    }
    timestamp = time.time() if now is None else float(now)
    for child in root.iterdir():
        name = child.name
        if child.is_symlink():
            report["errors"].append(f"refused symlink: {name}")
            continue
        match = _RESULT_DIR_RE.fullmatch(name)
        staging_match = _RESULT_STAGING_RE.fullmatch(name)
        if match is None and staging_match is None:
            continue
        try:
            age_seconds = max(0.0, timestamp - child.stat().st_mtime)
            if staging_match is not None:
                if child.is_dir() and age_seconds >= max(0, staging_grace_seconds):
                    report["planned_staging"].append(
                        {"name": name, "job_id": staging_match.group(1), "size_bytes": _tree_size(child)}
                    )
                else:
                    report["retained"].append(name)
                continue
            assert match is not None
            job_id = match.group(1)
            job = jobs_by_id.get(job_id)
            if job is not None:
                if (
                    job.get("status") in mushroom_worker_jobs.ACTIVE_STATUSES
                    or job.get("promotion_status") == "promoted"
                    or job.get("status") not in mushroom_worker_jobs.TERMINAL_STATUSES
                ):
                    report["retained"].append(name)
                    continue
                finished_at = str(job.get("finished_at") or "")
                try:
                    finished = datetime.fromisoformat(finished_at).astimezone(UTC)
                except ValueError:
                    report["errors"].append(
                        f"{name}: terminal job has an invalid finished_at timestamp"
                    )
                    report["retained"].append(name)
                    continue
                terminal_age = max(0.0, timestamp - finished.timestamp())
                if terminal_age < max(0, terminal_retention_seconds):
                    report["retained"].append(name)
                    continue
                empty = child.is_dir() and not any(child.iterdir())
                if not empty:
                    _validate_result_identity(child, job_id, required=False)
                report["planned_terminal"].append(
                    {
                        "name": name,
                        "job_id": job_id,
                        "size_bytes": _tree_size(child),
                        "validate_identity": not empty,
                        "reason": "terminal worker result older than 24 h",
                    }
                )
                continue
            if age_seconds < max(0, orphan_grace_seconds):
                report["retained"].append(name)
                continue
            if child.is_dir() and not any(child.iterdir()):
                report["planned_empty"].append(
                    {"name": name, "job_id": job_id, "size_bytes": 0}
                )
                continue
            _validate_result_identity(child, job_id)
            report["planned_orphan"].append(
                {"name": name, "job_id": job_id, "size_bytes": _tree_size(child)}
            )
        except (OSError, ValueError) as exc:
            report["errors"].append(f"{name}: {exc}")
    return report


def _apply_orphan_result_plan(result_root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(result_root).resolve()
    removed: list[str] = []
    errors: list[str] = []
    entries = [
        *plan.get("planned_orphan", []),
        *plan.get("planned_empty", []),
        *plan.get("planned_staging", []),
        *plan.get("planned_terminal", []),
    ]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", ""))
        job_id = str(entry.get("job_id", ""))
        path = root / name
        try:
            if path.parent != root or path.is_symlink() or not path.is_dir():
                raise ValueError("planned result path is no longer a safe directory")
            if entry.get("validate_identity"):
                _validate_result_identity(path, job_id, required=False)
            elif name in {
                str(row.get("name", ""))
                for row in plan.get("planned_orphan", [])
                if isinstance(row, dict)
            }:
                _validate_result_identity(path, job_id)
            shutil.rmtree(path)
            removed.append(name)
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    return {"removed": removed, "errors": errors}


def _plan_promotion_backups(live_root: Path) -> dict[str, Any]:
    """Keep the newest identified legacy promotion backup and plan older ones."""
    backup_root = Path(live_root) / ".worker-promotion-backups"
    report: dict[str, Any] = {"retained": [], "planned": [], "errors": []}
    if not backup_root.exists():
        return report
    if backup_root.is_symlink() or not backup_root.is_dir():
        report["errors"].append("promotion backup root is not a safe directory")
        return report
    known: list[Path] = []
    for child in backup_root.iterdir():
        if child.is_symlink():
            report["errors"].append(f"refused symlink: {child.name}")
            continue
        if not child.is_dir():
            continue
        try:
            mushroom_worker_transport.validate_job_id(child.name)
        except ValueError:
            report["retained"].append(
                {"name": child.name, "reason": "unrecognized_identity", "size_bytes": _tree_size(child)}
            )
            continue
        known.append(child)
    known.sort(key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
    if known:
        report["retained"].append(
            {"name": known[0].name, "reason": "current_rollback", "size_bytes": _tree_size(known[0])}
        )
    report["planned"] = [
        {"name": path.name, "reason": "superseded_rollback", "size_bytes": _tree_size(path)}
        for path in known[1:]
    ]
    return report


def _apply_promotion_backup_plan(live_root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    backup_root = (Path(live_root) / ".worker-promotion-backups").resolve()
    removed: list[str] = []
    errors: list[str] = []
    for entry in plan.get("planned", []):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "")
        path = backup_root / name
        try:
            mushroom_worker_transport.validate_job_id(name)
            if path.parent != backup_root or path.is_symlink() or not path.is_dir():
                raise ValueError("planned rollback path is no longer a safe directory")
            shutil.rmtree(path)
            removed.append(name)
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    return {"removed": removed, "errors": errors}


def reconcile_worker_storage(
    *,
    queue_path: Path,
    bundle_root: Path,
    result_root: Path,
    models_root: Path | None = None,
    registry_path: Path | None = None,
    report_path: Path | None = None,
    apply: bool = False,
    now: float | None = None,
    staging_grace_seconds: int = mushroom_worker_transport.DEFAULT_STAGING_GRACE_SECONDS,
    orphan_grace_seconds: int = mushroom_worker_transport.DEFAULT_ORPHAN_GRACE_SECONDS,
    terminal_result_retention_seconds: int = OPERATIONAL_RESULT_RETENTION_SECONDS,
) -> dict[str, Any]:
    """Plan first, optionally apply the exact conservative lifecycle cleanup."""
    started = time.perf_counter()
    queue = mushroom_worker_jobs.load_queue(Path(queue_path))
    jobs = queue["jobs"]
    bundle_plan = mushroom_worker_transport.cleanup_coordinator_bundles(
        Path(bundle_root),
        jobs,
        now=now,
        staging_grace_seconds=staging_grace_seconds,
        orphan_grace_seconds=orphan_grace_seconds,
        apply=False,
    )
    result_plan = mushroom_worker_results.cleanup_promoted_results(
        Path(result_root),
        jobs,
        apply=False,
    )
    orphan_result_plan = _plan_orphan_results(
        Path(result_root),
        jobs,
        now=now,
        orphan_grace_seconds=orphan_grace_seconds,
        staging_grace_seconds=staging_grace_seconds,
        terminal_retention_seconds=terminal_result_retention_seconds,
    )
    promotion_backup_plan = _plan_promotion_backups(Path(queue_path).parent)
    predictor_result_plan = mushroom_worker_jobs.plan_predictor_result_expiration(
        Path(queue_path),
        now=(datetime.fromtimestamp(now, UTC) if now is not None else None),
    )
    model_plan = (
        mushroom_ml_storage_reconciler.plan_model_storage(
            models_root=Path(models_root),
            registry_path=Path(registry_path),
        )
        if models_root is not None and registry_path is not None
        else None
    )
    bundle_names = _planned_names(
        bundle_plan,
        ("planned_terminal", "planned_orphan", "planned_staging"),
    )
    result_names = _planned_names(result_plan, ("planned",))
    recoverable_bytes = sum(_tree_size(Path(bundle_root) / name) for name in bundle_names)
    result_paths: dict[str, Path] = {}
    jobs_by_id = {str(job.get("job_id", "")): job for job in jobs if isinstance(job, dict)}
    for job_id in result_names:
        job = jobs_by_id.get(job_id, {})
        prefix = "ml." if job.get("job_type") == mushroom_worker_jobs.JOB_TYPE_ML_TRAIN else ""
        result_paths[job_id] = Path(result_root) / f"{prefix}{job_id}"
    recoverable_bytes += sum(_tree_size(path) for path in result_paths.values())
    recoverable_bytes += sum(
        int(entry.get("size_bytes", 0))
        for key in (
            "planned_orphan",
            "planned_empty",
            "planned_staging",
            "planned_terminal",
        )
        for entry in orphan_result_plan.get(key, [])
        if isinstance(entry, dict)
    )
    recoverable_bytes += sum(
        int(entry.get("size_bytes", 0))
        for entry in promotion_backup_plan.get("planned", [])
        if isinstance(entry, dict)
    )
    if model_plan is not None:
        recoverable_bytes += int(model_plan.get("recoverable_bytes", 0))
    recoverable_bytes += sum(
        int(entry.get("size_bytes", 0))
        for entry in predictor_result_plan.get("planned", [])
        if isinstance(entry, dict)
    )
    orphan_result_count = sum(
        len(orphan_result_plan.get(key, []))
        for key in (
            "planned_orphan",
            "planned_empty",
            "planned_staging",
            "planned_terminal",
        )
    )

    execution: dict[str, Any] | None = None
    if apply:
        execution = {
            "bundles": mushroom_worker_transport.cleanup_coordinator_bundles(
                Path(bundle_root),
                jobs,
                now=now,
                staging_grace_seconds=staging_grace_seconds,
                orphan_grace_seconds=orphan_grace_seconds,
                apply=True,
            ),
            "results": mushroom_worker_results.cleanup_promoted_results(
                Path(result_root),
                jobs,
                apply=True,
            ),
            "orphan_results": _apply_orphan_result_plan(
                Path(result_root),
                orphan_result_plan,
            ),
            "promotion_backups": _apply_promotion_backup_plan(
                Path(queue_path).parent,
                promotion_backup_plan,
            ),
            "predictor_results": mushroom_worker_jobs.expire_predictor_results(
                Path(queue_path),
                predictor_result_plan,
                expired_at=(datetime.fromtimestamp(now, UTC) if now is not None else None),
            ),
            "models": (
                mushroom_ml_storage_reconciler.apply_model_storage_plan(
                    models_root=Path(models_root),
                    registry_path=Path(registry_path),
                    plan=model_plan,
                )
                if model_plan is not None
                else None
            ),
        }

    errors = [
        *(str(value) for value in bundle_plan.get("errors", [])),
        *(str(value) for value in result_plan.get("errors", [])),
        *(str(value) for value in orphan_result_plan.get("errors", [])),
        *(str(value) for value in promotion_backup_plan.get("errors", [])),
        *(str(value) for value in predictor_result_plan.get("errors", [])),
        *(
            str(value)
            for value in (model_plan.get("errors", []) if model_plan is not None else [])
        ),
    ]
    model_root = Path(models_root) if models_root is not None else None
    archive_root = mushroom_paths.predictor_runtime_archive_preferred_dir()
    legacy_archive_root = (
        model_root / ".predictor-runtime-archives" if model_root is not None else None
    )
    archives = (
        [
            path
            for path in archive_root.glob("*.tar")
            if path.is_file()
            and not path.is_symlink()
            and re.fullmatch(r"[0-9a-f]{64}", path.stem)
        ]
        if archive_root.is_dir() and not archive_root.is_symlink()
        else []
    )
    removed_entries = 0
    if isinstance(execution, dict):
        for section in execution.values():
            if not isinstance(section, dict):
                continue
            for key in (
                "discarded_terminal",
                "discarded_orphan",
                "discarded_staging",
                "discarded",
                "removed",
                "expired",
                "removed_generations",
                "removed_batches",
                "removed_candidates",
                "removed_promotion_history",
                "compacted_benchmarks",
            ):
                values = section.get(key)
                if isinstance(values, list):
                    removed_entries += len(values)
    report = {
        "schema_version": "1.0",
        "kind": "rainmapper_mushroom_storage_reconciliation",
        "mode": "apply" if apply else "dry-run",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": {
            "planned_entries": (
                len(bundle_names)
                + len(result_names)
                + orphan_result_count
                + len(promotion_backup_plan.get("planned", []))
                + len(predictor_result_plan.get("planned", []))
                + (
                    len(model_plan.get("batch_removals", []))
                    + len(model_plan.get("candidate_removals", []))
                    + len(model_plan.get("promotion_history_removals", []))
                    + len(model_plan.get("generation_removals", []))
                    + len(model_plan.get("benchmark_compactions", []))
                    if model_plan is not None
                    else 0
                )
            ),
            "recoverable_bytes": recoverable_bytes,
            "errors": len(errors),
            "duration_seconds": round(time.perf_counter() - started, 6),
            "removed_entries": removed_entries,
        },
        "inventory": {
            "input_bundles": _inventory(Path(bundle_root)),
            "candidate_results": _inventory(Path(result_root)),
            "predictor_results": _inventory(
                Path(queue_path).parent / mushroom_worker_jobs.PREDICTOR_RESULTS_DIRNAME
            ),
            "model_batches": _inventory(model_root / "batches") if model_root else None,
            "model_candidates": _inventory(model_root / "candidates") if model_root else None,
            "model_benchmarks": _inventory(model_root / "benchmarks") if model_root else None,
            "model_promotion_history": (
                _inventory(model_root / "promotion-history") if model_root else None
            ),
            "legacy_runtime_archives": (
                _inventory(legacy_archive_root) if legacy_archive_root else None
            ),
        },
        "lifecycle": {
            "active_jobs": sum(
                1 for job in jobs if job.get("status") in mushroom_worker_jobs.ACTIVE_STATUSES
            ),
            "orphan_results": orphan_result_count,
            "expiring_predictor_results": len(predictor_result_plan.get("planned", [])),
            "installed_batches": (
                sum(
                    1
                    for row in model_plan.get("protected_batches", [])
                    if any(str(reason).startswith("installed:") for reason in row.get("reasons", []))
                )
                if model_plan is not None
                else 0
            ),
            "retained_rollbacks": (
                len(model_plan.get("retained_rollbacks", [])) if model_plan else 0
            )
            + sum(
                1
                for row in promotion_backup_plan.get("retained", [])
                if isinstance(row, dict) and row.get("reason") == "current_rollback"
            ),
        },
        "predictor_runtime_archive": {
            "location": str(archive_root),
            "entries": len(archives),
            "bytes": sum(path.stat().st_size for path in archives),
            "fingerprints": [f"sha256:{path.stem}" for path in sorted(archives)],
            "legacy_share_location": (
                str(legacy_archive_root) if legacy_archive_root is not None else ""
            ),
            "legacy_share_entries": (
                _inventory(legacy_archive_root)["entries"]
                if legacy_archive_root is not None
                else 0
            ),
            "legacy_share_bytes": (
                _inventory(legacy_archive_root)["bytes"]
                if legacy_archive_root is not None
                else 0
            ),
            "legacy_cleanup_state": (
                "manual_after_verified_media_archive"
                if legacy_archive_root is not None and legacy_archive_root.exists()
                else "absent"
            ),
        },
        "plan": {
            "bundles": bundle_plan,
            "results": result_plan,
            "orphan_results": orphan_result_plan,
            "promotion_backups": promotion_backup_plan,
            "predictor_results": predictor_result_plan,
            "models": model_plan,
        },
        "execution": execution,
        "errors": errors,
    }
    if report_path is not None:
        _write_report(Path(report_path), report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--models-root", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if (args.models_root is None) != (args.registry is None):
        parser.error("--models-root and --registry must be provided together")
    print(
        json.dumps(
            reconcile_worker_storage(
                queue_path=args.queue,
                bundle_root=args.bundle_root,
                result_root=args.result_root,
                models_root=args.models_root,
                registry_path=args.registry,
                report_path=args.report,
                apply=args.apply,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
