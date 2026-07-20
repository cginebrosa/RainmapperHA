"""Shared, filesystem-explicit orchestration for mushroom rebuild jobs.

This module deliberately has no HTTP, Home Assistant or Docker dependencies.
Callers must provide every input and output path, which allows the same rebuild
to run against HA paths or an isolated snapshot without changing live data.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from rainmapper_core import (
    mushroom_gis_lab,
    mushroom_learned_model,
    mushroom_observation_context,
    mushroom_observation_features,
)


PHASE_COUNT = 4
ProgressCallback = Callable[[dict[str, object]], None]


class CancellationEvent(Protocol):
    def is_set(self) -> bool: ...


class RebuildCancelled(RuntimeError):
    """Raised when cooperative cancellation is requested."""


@dataclass(frozen=True)
class RebuildInputPaths:
    observations: Path
    reference_catalogs: Path
    gis_mappings: Path
    weather_data_dir: Path
    gis_root: Path

    def as_dict(self) -> dict[str, str]:
        return {
            "observations": str(self.observations),
            "reference_catalogs": str(self.reference_catalogs),
            "gis_mappings": str(self.gis_mappings),
            "weather_data_dir": str(self.weather_data_dir),
            "gis_root": str(self.gis_root),
        }


@dataclass(frozen=True)
class RebuildOutputPaths:
    root: Path
    gis_reconstruction: Path
    qgis_points: Path
    weather_json: Path
    weather_csv: Path
    weather_report: Path
    features_json: Path
    features_csv: Path
    features_report: Path
    model_json: Path
    model_report: Path

    @classmethod
    def under(cls, root: Path) -> "RebuildOutputPaths":
        output_root = root.resolve()
        reports = output_root / "reports"
        return cls(
            root=output_root,
            gis_reconstruction=output_root / "mushroom_gis_observation_reconstruction.json",
            qgis_points=output_root / "qgis" / "selected_observations.geojson",
            weather_json=output_root / "mushroom_observations_weather_features.json",
            weather_csv=output_root / "mushroom_observations_weather_features.csv",
            weather_report=reports / "mushroom_observations_weather_features.md",
            features_json=output_root / "mushroom_observation_features_v0.json",
            features_csv=output_root / "mushroom_observation_features_v0.csv",
            features_report=reports / "mushroom_observation_features_v0.md",
            model_json=output_root / "mushroom_model_v0.json",
            model_report=reports / "mushroom_model_v0.md",
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "root": str(self.root),
            "gis_reconstruction": str(self.gis_reconstruction),
            "qgis_points": str(self.qgis_points),
            "weather_json": str(self.weather_json),
            "weather_csv": str(self.weather_csv),
            "weather_report": str(self.weather_report),
            "features_json": str(self.features_json),
            "features_csv": str(self.features_csv),
            "features_report": str(self.features_report),
            "model_json": str(self.model_json),
            "model_report": str(self.model_report),
        }


ACCEPTED_OUTPUT_FIELDS = (
    "gis_reconstruction",
    "weather_json",
    "weather_csv",
    "weather_report",
    "features_json",
    "features_csv",
    "features_report",
    "model_json",
    "model_report",
)


def accepted_output_pairs(
    staged: RebuildOutputPaths,
    final: RebuildOutputPaths,
) -> list[tuple[Path, Path]]:
    return [
        (Path(getattr(staged, field)), Path(getattr(final, field)))
        for field in ACCEPTED_OUTPUT_FIELDS
    ]


def seed_partial_model_outputs(
    staged: RebuildOutputPaths,
    final: RebuildOutputPaths,
) -> None:
    for source, destination in (
        (final.model_json, staged.model_json),
        (final.model_report, staged.model_report),
    ):
        if source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def promote_rebuild_outputs(
    staged: RebuildOutputPaths,
    final: RebuildOutputPaths,
) -> dict[str, object]:
    pairs = accepted_output_pairs(staged, final)
    missing = [str(source) for source, _destination in pairs if not source.is_file()]
    if missing:
        raise FileNotFoundError(f"staged rebuild output is missing: {missing[0]}")
    rollback_root = staged.root / ".rollback"
    backups: dict[Path, Path | None] = {}
    promoted: list[Path] = []
    for _source, destination in pairs:
        relative = destination.relative_to(final.root)
        backup = rollback_root / relative
        if destination.is_file():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
            backups[destination] = backup
        else:
            backups[destination] = None
    try:
        for source, destination in pairs:
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
            promoted.append(destination)
    except BaseException:
        rollback_errors = []
        for destination in reversed(promoted):
            backup = backups[destination]
            try:
                if backup is None:
                    destination.unlink(missing_ok=True)
                else:
                    os.replace(backup, destination)
            except OSError as exc:
                rollback_errors.append(f"{destination}: {exc}")
        if rollback_errors:
            raise RuntimeError(
                "rebuild promotion failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            )
        raise
    return {
        "status": "promoted",
        "artifact_count": len(promoted),
        "artifacts": [str(path.relative_to(final.root)) for path in promoted],
    }


def promote_qgis_points(staged_path: Path, final_path: Path, job_id: str) -> None:
    if not staged_path.is_file():
        raise FileNotFoundError(f"staged QGIS output is missing: {staged_path}")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = final_path.parent / f".{final_path.name}.{job_id}.tmp"
    shutil.copy2(staged_path, temporary)
    os.replace(temporary, final_path)


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"{label} not found: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return payload


def observation_rows(payload: dict[str, Any]) -> list[dict[str, object]]:
    rows = payload.get("observations")
    if not isinstance(rows, list):
        raise ValueError("observations payload must contain an observations list")
    return [dict(row) for row in rows if isinstance(row, dict)]


def observation_has_coordinates(row: dict[str, object]) -> bool:
    location = row.get("location")
    if not isinstance(location, dict):
        return False
    try:
        float(location.get("lat"))
        float(location.get("lon"))
    except (TypeError, ValueError):
        return False
    return True


def eligible_observation_ids(observations: list[dict[str, object]]) -> list[str]:
    result = []
    for row in observations:
        if str(row.get("validation_status", "") or "").strip() != "valid":
            continue
        if str(row.get("calibration_use", "") or "").strip() != "include":
            continue
        if not observation_has_coordinates(row):
            continue
        observation_id = str(row.get("observation_id", "") or "").strip()
        if observation_id:
            result.append(observation_id)
    return result


def _check_cancelled(cancel_event: CancellationEvent | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise RebuildCancelled("mushroom rebuild cancelled")


def _emit_progress(
    callback: ProgressCallback | None,
    *,
    phase: str,
    phase_index: int,
    phase_percent: int,
    overall_percent: int,
    message: str,
) -> None:
    if callback is None:
        return
    callback(
        {
            "phase": phase,
            "phase_index": phase_index,
            "phase_count": PHASE_COUNT,
            "phase_percent": max(0, min(100, int(phase_percent))),
            "overall_percent": max(0, min(100, int(overall_percent))),
            "message": message,
        }
    )


def run_rebuild(
    inputs: RebuildInputPaths,
    outputs: RebuildOutputPaths,
    *,
    selected_observation_ids: list[str] | tuple[str, ...] | None = None,
    pending_species_ids: list[str] | tuple[str, ...] | None = None,
    progress_callback: ProgressCallback | None = None,
    cancel_event: CancellationEvent | None = None,
) -> dict[str, object]:
    """Run the existing four rebuild phases using only the supplied paths."""
    started = time.monotonic()
    observations_payload = load_json_object(inputs.observations, "observations")
    catalogs_payload = load_json_object(inputs.reference_catalogs, "reference catalogs")
    gis_payload = load_json_object(inputs.gis_mappings, "GIS mappings")
    observations = observation_rows(observations_payload)
    selected_ids = list(selected_observation_ids or eligible_observation_ids(observations))
    pending_species = sorted(
        {
            str(species_id).strip()
            for species_id in (pending_species_ids or [])
            if str(species_id or "").strip()
        }
    )
    outputs.root.mkdir(parents=True, exist_ok=True)
    phase_durations: dict[str, float] = {}

    _check_cancelled(cancel_event)
    phase_started = time.monotonic()
    _emit_progress(
        progress_callback,
        phase="GIS/DEM",
        phase_index=1,
        phase_percent=0,
        overall_percent=5,
        message=f"Reconstructing GIS/DEM for {len(selected_ids)} observation(s).",
    )

    def gis_progress(current: int, total: int) -> None:
        _check_cancelled(cancel_event)
        percent = int((current / total) * 100) if total else 100
        _emit_progress(
            progress_callback,
            phase="GIS/DEM",
            phase_index=1,
            phase_percent=percent,
            overall_percent=5 + int(percent * 0.35),
            message=f"GIS/DEM {current}/{total} observation(s).",
        )
        _check_cancelled(cancel_event)

    gis_result = mushroom_gis_lab.reconstruct_observations(
        observations,
        selected_ids,
        output_path=outputs.gis_reconstruction,
        gis_payload=gis_payload,
        catalogs_payload=catalogs_payload,
        progress_callback=gis_progress,
        gis_root_path=inputs.gis_root,
        qgis_points_path=outputs.qgis_points,
    )
    phase_durations["gis_dem"] = round(time.monotonic() - phase_started, 3)

    _check_cancelled(cancel_event)
    phase_started = time.monotonic()
    _emit_progress(
        progress_callback,
        phase="Meteorologia",
        phase_index=2,
        phase_percent=0,
        overall_percent=42,
        message="Reconstruyendo contexto meteorologico.",
    )

    def weather_progress(percent: int, message: str) -> None:
        _check_cancelled(cancel_event)
        _emit_progress(
            progress_callback,
            phase="Meteorologia",
            phase_index=2,
            phase_percent=percent,
            overall_percent=42 + int(percent * 0.18),
            message=message,
        )
        _check_cancelled(cancel_event)

    weather_payload = mushroom_observation_context.build_and_write_observation_weather_features(
        observations_path=inputs.observations,
        weather_data_dir=inputs.weather_data_dir,
        catalogs_path=inputs.reference_catalogs,
        output_json_path=outputs.weather_json,
        output_csv_path=outputs.weather_csv,
        report_path=outputs.weather_report,
        progress_callback=weather_progress,
    )
    phase_durations["weather"] = round(time.monotonic() - phase_started, 3)

    _check_cancelled(cancel_event)
    phase_started = time.monotonic()
    _emit_progress(
        progress_callback,
        phase="Features v0",
        phase_index=3,
        phase_percent=0,
        overall_percent=62,
        message="Uniendo features meteorologicas y GIS/DEM.",
    )

    def features_progress(percent: int, message: str) -> None:
        _check_cancelled(cancel_event)
        _emit_progress(
            progress_callback,
            phase="Features v0",
            phase_index=3,
            phase_percent=percent,
            overall_percent=62 + int(percent * 0.16),
            message=message,
        )
        _check_cancelled(cancel_event)

    features_payload = mushroom_observation_features.build_and_write_observation_features_v0(
        weather_features_path=outputs.weather_json,
        gis_reconstruction_path=outputs.gis_reconstruction,
        output_json_path=outputs.features_json,
        output_csv_path=outputs.features_csv,
        report_path=outputs.features_report,
        progress_callback=features_progress,
    )
    phase_durations["features_v0"] = round(time.monotonic() - phase_started, 3)

    _check_cancelled(cancel_event)
    phase_started = time.monotonic()
    _emit_progress(
        progress_callback,
        phase="Modelo aprendido v0",
        phase_index=4,
        phase_percent=0,
        overall_percent=80,
        message="Construyendo modelo aprendido v0.",
    )

    if pending_species:
        learned_payload: dict[str, Any] | None = None
        pending_total = len(pending_species)
        for index, species_id in enumerate(pending_species, start=1):
            _check_cancelled(cancel_event)

            def species_progress(
                percent: int,
                message: str,
                *,
                species_index: int = index,
            ) -> None:
                _check_cancelled(cancel_event)
                aggregate = int((((species_index - 1) + percent / 100) / pending_total) * 100)
                _emit_progress(
                    progress_callback,
                    phase="Modelo aprendido v0",
                    phase_index=4,
                    phase_percent=aggregate,
                    overall_percent=80 + int(aggregate * 0.2),
                    message=f"Especie {species_index}/{pending_total}. {message}",
                )
                _check_cancelled(cancel_event)

            learned_payload = mushroom_learned_model.build_and_write_species_learned_model_v0(
                species_id,
                features_path=outputs.features_json,
                output_json_path=outputs.model_json,
                report_path=outputs.model_report,
                progress_callback=species_progress,
            )
    else:

        def model_progress(percent: int, message: str) -> None:
            _check_cancelled(cancel_event)
            _emit_progress(
                progress_callback,
                phase="Modelo aprendido v0",
                phase_index=4,
                phase_percent=percent,
                overall_percent=80 + int(percent * 0.2),
                message=message,
            )
            _check_cancelled(cancel_event)

        learned_payload = mushroom_learned_model.build_and_write_learned_model_v0(
            features_path=outputs.features_json,
            output_json_path=outputs.model_json,
            report_path=outputs.model_report,
            progress_callback=model_progress,
        )
    phase_durations["learned_model_v0"] = round(time.monotonic() - phase_started, 3)

    gis_count = int(gis_result.get("result_count", 0) or 0)
    weather_count = int(weather_payload.get("summary", {}).get("observations", 0) or 0)
    feature_count = int(features_payload.get("summary", {}).get("observations", 0) or 0)
    model_species_count = (
        int(learned_payload.get("summary", {}).get("species", 0) or 0)
        if isinstance(learned_payload, dict)
        else 0
    )
    total_duration = round(time.monotonic() - started, 3)
    message = (
        f"Modelo v0 rebuilt: GIS/DEM {gis_count}, weather {weather_count}, "
        f"features {feature_count}, species models {model_species_count}."
    )
    _emit_progress(
        progress_callback,
        phase="Modelo aprendido v0",
        phase_index=4,
        phase_percent=100,
        overall_percent=100,
        message=message,
    )
    return {
        "schema_version": "0.1",
        "kind": "mushroom_rebuild_result",
        "status": "complete",
        "selected_observation_ids": selected_ids,
        "pending_species_ids": pending_species,
        "input_paths": inputs.as_dict(),
        "output_paths": outputs.as_dict(),
        "phase_durations_seconds": phase_durations,
        "duration_seconds": total_duration,
        "summary": {
            "gis_observations": gis_count,
            "weather_observations": weather_count,
            "feature_observations": feature_count,
            "model_species": model_species_count,
        },
        "message": message,
    }
