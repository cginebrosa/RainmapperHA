"""Conservative transition of reconstructible mushroom artifacts to HA media."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_paths


LEGACY_REBUILD_FILES = (
    "mushroom_gis_observation_reconstruction.json",
    "mushroom_observations_weather_features.json",
    "mushroom_observations_weather_features.csv",
    "reports/mushroom_observations_weather_features.md",
    "mushroom_observation_features_v0.json",
    "mushroom_observation_features_v0.csv",
    "reports/mushroom_observation_features_v0.md",
    "mushroom_model_v0.json",
    "reports/mushroom_model_v0.md",
)
TRANSITION_SCHEMA_VERSION = "1.0"
TRANSITION_RECEIPT_NAME = ".legacy-share-transition-v1.json"


def _receipt_path() -> Path:
    return mushroom_paths.mushroom_derived_data_dir() / TRANSITION_RECEIPT_NAME


def _load_receipt() -> dict[str, Any] | None:
    path = _receipt_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != TRANSITION_SCHEMA_VERSION
        or payload.get("status") != "complete"
        or payload.get("target_root")
        != str(mushroom_paths.mushroom_derived_data_dir())
    ):
        return None
    return payload


def _write_receipt(report: dict[str, Any]) -> None:
    target = _receipt_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRANSITION_SCHEMA_VERSION,
        "status": "complete",
        "completed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_root": report["source_root"],
        "target_root": report["target_root"],
        "copied_file_count": len(report["copied_files"]),
        "copied_bytes": report["copied_bytes"],
        "conflicts": list(report["conflicts"]),
        "excluded": list(report["excluded"]),
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_missing_file(source: Path, target: Path, report: dict[str, Any]) -> None:
    if source.is_symlink() or not source.is_file():
        report["errors"].append(f"refused non-regular legacy artifact: {source}")
        return
    if target.exists():
        if (
            target.is_file()
            and not target.is_symlink()
            and source.stat().st_size == target.stat().st_size
            and _sha256(source) == _sha256(target)
        ):
            report["already_present"].append(str(target))
        else:
            report["conflicts"].append(str(target))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".migration", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        if source.stat().st_size != temporary.stat().st_size or _sha256(source) != _sha256(
            temporary
        ):
            raise OSError(f"copied artifact failed verification: {source}")
        os.replace(temporary, target)
        report["copied_files"].append(str(target))
        report["copied_bytes"] += target.stat().st_size
    finally:
        temporary.unlink(missing_ok=True)


def _copy_missing_tree(
    source: Path,
    target: Path,
    report: dict[str, Any],
    *,
    excluded_names: frozenset[str] = frozenset(),
) -> None:
    if not source.exists():
        return
    if source.is_symlink() or not source.is_dir():
        report["errors"].append(f"refused non-directory legacy root: {source}")
        return
    for child in source.iterdir():
        if child.name in excluded_names:
            report["excluded"].append(str(child))
            continue
        destination = target / child.name
        try:
            if child.is_symlink():
                report["errors"].append(f"refused legacy symlink: {child}")
            elif child.is_dir():
                _copy_missing_tree(child, destination, report)
            elif child.is_file():
                _copy_missing_file(child, destination, report)
        except OSError as exc:
            report["errors"].append(f"{child}: {exc}")


def prepare_derived_storage_transition() -> dict[str, Any]:
    """Copy legacy derived artifacts to media without overwriting or deleting source."""
    report: dict[str, Any] = {
        "enabled": mushroom_paths.derived_storage_enabled(),
        "source_root": str(mushroom_paths.mushroom_data_dir()),
        "target_root": str(mushroom_paths.mushroom_derived_data_dir()),
        "copied_files": [],
        "copied_bytes": 0,
        "already_present": [],
        "excluded": [],
        "conflicts": [],
        "errors": [],
        "already_complete": False,
    }
    if not report["enabled"]:
        return report
    receipt = _load_receipt()
    if receipt is not None:
        report["already_complete"] = True
        report["receipt"] = receipt
        return report

    legacy = mushroom_paths.mushroom_data_dir()
    artifacts = mushroom_paths.mushroom_rebuild_artifacts_dir()
    for relative in LEGACY_REBUILD_FILES:
        source = legacy / relative
        if source.exists():
            try:
                _copy_missing_file(source, artifacts / relative, report)
            except OSError as exc:
                report["errors"].append(f"{source}: {exc}")

    _copy_missing_tree(
        legacy / "ml_models",
        mushroom_paths.mushroom_ml_models_dir(),
        report,
        excluded_names=frozenset({".predictor-runtime-archives"}),
    )
    _copy_missing_tree(
        legacy / "ml_version_archive",
        mushroom_paths.mushroom_ml_version_archive_dir(),
        report,
    )
    for legacy_name, target in (
        (".worker-input-bundles", mushroom_paths.mushroom_worker_input_bundles_dir()),
        (".worker-candidate-results", mushroom_paths.mushroom_worker_candidate_results_dir()),
        (".worker-predictor-results", mushroom_paths.mushroom_worker_predictor_results_dir()),
        (".worker-promotion-backups", artifacts / ".worker-promotion-backups"),
        (".worker-promotion-staging", artifacts / ".worker-promotion-staging"),
        (".rebuild-staging", artifacts / ".rebuild-staging"),
    ):
        _copy_missing_tree(legacy / legacy_name, target, report)
    if not report["errors"]:
        _write_receipt(report)
    return report
