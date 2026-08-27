"""Best-effort SoilGrids reconciliation for immutable model rebuild inputs."""

from __future__ import annotations

import copy
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from rainmapper_core import mushroom_soilgrids


USABLE_STATUSES = frozenset({"complete", "partial", "no_coverage"})
COUNTER_KEYS = (
    "downloaded",
    "reused",
    "requests",
    "downloaded_bytes",
    "files_promoted",
    "files_read",
    "asset_hashes_checked",
    "hash_bytes",
    "raster_windows_read",
    "manifest_writes",
    "fsyncs",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _context(row: dict[str, Any]) -> dict[str, Any]:
    derived = row.get("derived_context")
    value = derived.get("soilgrids_water") if isinstance(derived, dict) else None
    return value if isinstance(value, dict) else {}


def _status(context: object) -> str:
    return str(context.get("status", "missing")) if isinstance(context, dict) else "missing"


def _aggregation_counters(cache_root: Path, context: object) -> dict[str, int]:
    source = context.get("source") if isinstance(context, dict) else None
    assets = source.get("asset_hashes") if isinstance(source, dict) else None
    if not isinstance(assets, list):
        return {}
    try:
        manifest = mushroom_soilgrids.load_manifest(cache_root)
    except mushroom_soilgrids.SoilGridsError:
        return {"raster_windows_read": len(assets)}
    hash_bytes = 0
    counted = 0
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        coverage = str(asset.get("coverage_id", ""))
        tile_id = str(asset.get("tile_id", ""))
        try:
            tile = manifest["coverages"][coverage]["tiles"][tile_id]
            hash_bytes += int(tile.get("raw_size_bytes", 0) or 0)
            hash_bytes += int(tile.get("normalized_size_bytes", 0) or 0)
            counted += 1
        except (KeyError, TypeError, ValueError):
            continue
    return {
        "asset_hashes_checked": counted * 2,
        "hash_bytes": hash_bytes,
        "raster_windows_read": len(assets),
        # Two full-file hash reads plus one normalized raster window per asset.
        "files_read": counted * 3,
    }


def inspect_payload(payload: object) -> dict[str, Any]:
    """Return current per-micro-area health without reading raster assets."""
    rows = payload.get("micro_areas") if isinstance(payload, dict) else None
    micro_areas = rows if isinstance(rows, list) else []
    details: list[dict[str, Any]] = []
    counts = {
        "total": 0,
        "current": 0,
        "complete": 0,
        "partial": 0,
        "no_coverage": 0,
        "pending": 0,
        "missing_geometry": 0,
    }
    for raw in micro_areas:
        if not isinstance(raw, dict) or raw.get("archived"):
            continue
        counts["total"] += 1
        geometry = raw.get("geometry")
        context = _context(raw)
        if not isinstance(geometry, dict):
            counts["missing_geometry"] += 1
            status = "missing_geometry"
            current = False
        else:
            status = _status(context)
            current = mushroom_soilgrids.context_is_current(context, geometry)
            if current:
                counts["current"] += 1
            if status in {"complete", "partial", "no_coverage"}:
                counts[status] += 1
            else:
                counts["pending"] += 1
        if not current or status != "complete":
            quality = context.get("quality") if isinstance(context, dict) else None
            details.append(
                {
                    "micro_area_id": str(raw.get("micro_area_id", "")),
                    "area_id": str(raw.get("area_id", "")),
                    "name": str(raw.get("name", "")),
                    "status": status,
                    "error_type": str(
                        quality.get("error_type", "")
                        if isinstance(quality, dict)
                        else ""
                    ),
                    "error": str(
                        quality.get("error", "")
                        if isinstance(quality, dict)
                        else ""
                    ),
                }
            )
    return {**counts, "unresolved": details}


def reconcile_payload(
    payload: dict[str, Any],
    cache_root: Path,
    *,
    cancel_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    resolver: Callable[..., dict[str, Any]] = mushroom_soilgrids.resolve_geometry_context,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Repair stale contexts in a copy and return monotonic phase telemetry."""
    started_ns = time.monotonic_ns()
    candidate = copy.deepcopy(payload)
    rows = candidate.get("micro_areas")
    micro_areas = rows if isinstance(rows, list) else []
    active = [row for row in micro_areas if isinstance(row, dict) and not row.get("archived")]
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "phase": "soilgrids_reconciliation",
        "started_at": utc_now(),
        "duration_ms": 0,
        "total_micro_areas": len(active),
        "processed_micro_areas": 0,
        "attempted_micro_areas": 0,
        "repaired_micro_areas": 0,
        "current_micro_areas": 0,
        "missing_geometry": 0,
        "warnings": [],
        **{key: 0 for key in COUNTER_KEYS},
    }

    def emit(row: dict[str, Any] | None = None) -> None:
        report["duration_ms"] = (time.monotonic_ns() - started_ns) // 1_000_000
        if progress_callback is not None:
            current = (
                {
                    "micro_area_id": str(row.get("micro_area_id", "")),
                    "area_id": str(row.get("area_id", "")),
                    "name": str(row.get("name", "")),
                }
                if isinstance(row, dict)
                else {}
            )
            progress_callback({**report, "current_micro_area": current})

    for row in active:
        if cancel_check is not None and cancel_check():
            raise mushroom_soilgrids.SoilGridsCancelledError(
                "SoilGrids reconciliation was cancelled."
            )
        geometry = row.get("geometry")
        previous = _context(row)
        if not isinstance(geometry, dict):
            report["missing_geometry"] += 1
            report["processed_micro_areas"] += 1
            emit(row)
            continue
        if mushroom_soilgrids.context_is_current(previous, geometry):
            report["current_micro_areas"] += 1
            report["processed_micro_areas"] += 1
            emit(row)
            continue

        report["attempted_micro_areas"] += 1
        cache_telemetry: dict[str, Any] = {}

        def tile_progress(tile: dict[str, Any]) -> None:
            for key in COUNTER_KEYS:
                cache_telemetry[key] = int(tile.get(key, cache_telemetry.get(key, 0)) or 0)
            emit(row)

        try:
            resolved = resolver(
                Path(cache_root),
                geometry,
                ensure_missing=True,
                cancel_check=cancel_check,
                progress_callback=tile_progress,
                telemetry=cache_telemetry,
            )
        except mushroom_soilgrids.SoilGridsCancelledError:
            raise
        except Exception as exc:
            for key in COUNTER_KEYS:
                report[key] += int(cache_telemetry.get(key, 0) or 0)
            report["warnings"].append(
                {
                    "micro_area_id": str(row.get("micro_area_id", "")),
                    "area_id": str(row.get("area_id", "")),
                    "name": str(row.get("name", "")),
                    "status": "resolution_error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            report["processed_micro_areas"] += 1
            emit(row)
            continue
        aggregation = _aggregation_counters(Path(cache_root), resolved)
        for key, value in aggregation.items():
            cache_telemetry[key] = int(cache_telemetry.get(key, 0) or 0) + value
        for key in COUNTER_KEYS:
            report[key] += int(cache_telemetry.get(key, 0) or 0)
        if mushroom_soilgrids.context_is_current(resolved, geometry):
            mushroom_soilgrids.apply_micro_area_context(row, resolved)
            report["repaired_micro_areas"] += 1
        else:
            mushroom_soilgrids.apply_micro_area_context(row, resolved)
            quality = resolved.get("quality") if isinstance(resolved, dict) else None
            report["warnings"].append(
                {
                    "micro_area_id": str(row.get("micro_area_id", "")),
                    "area_id": str(row.get("area_id", "")),
                    "name": str(row.get("name", "")),
                    "status": _status(resolved),
                    "error_type": str(
                        quality.get("error_type", "")
                        if isinstance(quality, dict)
                        else ""
                    ),
                    "error": str(
                        quality.get("error", "")
                        if isinstance(quality, dict)
                        else ""
                    ),
                }
            )
        report["processed_micro_areas"] += 1
        emit(row)

    report["finished_at"] = utc_now()
    report["duration_ms"] = (time.monotonic_ns() - started_ns) // 1_000_000
    report["health"] = inspect_payload(candidate)
    return candidate, report


def payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
