"""Persistence and validation for private mushroom areas and micro-areas."""

from __future__ import annotations

import copy
import math
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_paths
from rainmapper_core.mushroom_store import AUTOMATIC_BACKUPS_PER_FILE, write_json_atomic


ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
FILE_NAME = "mushroom_known_sites.json"


def prune_automatic_backups(
    target: Path,
    *,
    keep_latest: int = AUTOMATIC_BACKUPS_PER_FILE,
) -> None:
    """Keep the shared automatic-backup limit while preserving manual keeps."""
    backup_dir = target.parent / "backups"
    if not backup_dir.exists() or keep_latest < 0:
        return
    backups = [
        path
        for path in backup_dir.glob(f"{target.stem}.*{target.suffix}")
        if ".keep" not in path.stem
    ]
    backups.sort(key=lambda path: path.name)
    for obsolete in backups[:-keep_latest]:
        obsolete.unlink(missing_ok=True)


def default_payload() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "areas": [],
        "micro_areas": [],
        "metadata": {"updated_at": datetime.now(UTC).date().isoformat()},
    }


def empty_area(area_id: str = "") -> dict[str, Any]:
    return {
        "area_id": area_id,
        "name": "",
        "description": "",
        "aliases": [],
        "administrative_location": {
            "municipality": "",
            "county": "",
            "province": "",
            "country": "",
        },
        "representative_location": None,
        "geometry": None,
        "derived_context": {},
        "notes": "",
        "archived": False,
        "metadata": {
            "created_at": datetime.now(UTC).date().isoformat(),
            "updated_at": datetime.now(UTC).date().isoformat(),
        },
    }


def empty_micro_area(micro_area_id: str = "", area_id: str = "") -> dict[str, Any]:
    return {
        "micro_area_id": micro_area_id,
        "area_id": area_id,
        "name": "",
        "description": "",
        "aliases": [],
        "representative_location": None,
        "geometry": None,
        "derived_context": {},
        "location_precision_m": None,
        "altitude": {"min_m": None, "max_m": None, "source": ""},
        "topography": {"aspect_ids": [], "slope_notes": "", "exposure_notes": ""},
        "ecology": {
            "host_ids": [],
            "forest_type_ids": [],
            "soil_tendency_ids": [],
            "habitat_feature_ids": [],
            "notes": "",
        },
        "access": {"difficulty": "", "notes": ""},
        "provenance": {"source": "manual", "confidence": "", "notes": ""},
        "notes": "",
        "archived": False,
        "metadata": {
            "created_at": datetime.now(UTC).date().isoformat(),
            "updated_at": datetime.now(UTC).date().isoformat(),
        },
    }


def default_path() -> Path:
    return mushroom_paths.app_mushroom_defaults_dir() / FILE_NAME


def point_in_geometry(lon: float, lat: float, geometry: object) -> bool:
    """Return whether a WGS84 point is inside a Polygon or MultiPolygon."""
    if not isinstance(geometry, dict) or not isinstance(geometry.get("coordinates"), list):
        return False
    coordinates = geometry["coordinates"]
    polygons = [coordinates] if geometry.get("type") == "Polygon" else coordinates if geometry.get("type") == "MultiPolygon" else []
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon or not isinstance(polygon[0], list):
            continue
        ring = polygon[0]
        inside = False
        previous = len(ring) - 1
        for current, point in enumerate(ring):
            prior = ring[previous]
            if isinstance(point, list) and isinstance(prior, list) and len(point) >= 2 and len(prior) >= 2:
                x1, y1, x2, y2 = float(point[0]), float(point[1]), float(prior[0]), float(prior[1])
                if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / ((y2 - y1) or 1e-12) + x1:
                    inside = not inside
            previous = current
        if inside:
            return True
    return False


def persistent_path() -> Path:
    return mushroom_paths.mushroom_data_file(FILE_NAME)


def ensure_seeded() -> Path:
    target = persistent_path()
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    source = default_path()
    if source.exists():
        shutil.copy2(source, target)
    else:
        write_json_atomic(target, default_payload())
    return target


def load_payload() -> dict[str, Any]:
    path = ensure_seeded()
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else default_payload()


def active_rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and not row.get("archived")]


def validate_payload(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["Known sites payload must be an object."]
    errors: list[str] = []
    areas = payload.get("areas")
    micro_areas = payload.get("micro_areas")
    if not isinstance(areas, list):
        errors.append("areas must be a list.")
        areas = []
    if not isinstance(micro_areas, list):
        errors.append("micro_areas must be a list.")
        micro_areas = []

    area_ids: set[str] = set()
    for index, row in enumerate(areas):
        if not isinstance(row, dict):
            errors.append(f"areas[{index}] must be an object.")
            continue
        area_id = str(row.get("area_id", "") or "").strip()
        name = str(row.get("name", "") or "").strip()
        if not ID_PATTERN.fullmatch(area_id):
            errors.append(f"areas[{index}].area_id is invalid.")
        elif area_id in area_ids:
            errors.append(f"Duplicate area_id: {area_id}.")
        area_ids.add(area_id)
        if not name:
            errors.append(f"areas[{index}].name is required.")
        _validate_optional_location(row.get("representative_location"), f"areas[{index}]", errors)
        _validate_optional_geometry(row.get("geometry"), f"areas[{index}]", errors)

    micro_ids: set[str] = set()
    for index, row in enumerate(micro_areas):
        if not isinstance(row, dict):
            errors.append(f"micro_areas[{index}] must be an object.")
            continue
        micro_id = str(row.get("micro_area_id", "") or "").strip()
        area_id = str(row.get("area_id", "") or "").strip()
        name = str(row.get("name", "") or "").strip()
        if not ID_PATTERN.fullmatch(micro_id):
            errors.append(f"micro_areas[{index}].micro_area_id is invalid.")
        elif micro_id in micro_ids:
            errors.append(f"Duplicate micro_area_id: {micro_id}.")
        micro_ids.add(micro_id)
        if area_id not in area_ids:
            errors.append(f"micro_areas[{index}].area_id does not exist: {area_id or '-'}.")
        if not name:
            errors.append(f"micro_areas[{index}].name is required.")
        _validate_optional_location(row.get("representative_location"), f"micro_areas[{index}]", errors)
        _validate_optional_geometry(row.get("geometry"), f"micro_areas[{index}]", errors)
        altitude = row.get("altitude")
        if isinstance(altitude, dict):
            minimum = altitude.get("min_m")
            maximum = altitude.get("max_m")
            try:
                if minimum is not None and maximum is not None and float(minimum) > float(maximum):
                    errors.append(f"micro_areas[{index}].altitude min_m exceeds max_m.")
            except (TypeError, ValueError):
                errors.append(f"micro_areas[{index}].altitude values must be numeric.")
    return errors


def _validate_optional_location(value: object, location: str, errors: list[str]) -> None:
    if value in (None, {}):
        return
    if not isinstance(value, dict):
        errors.append(f"{location}.representative_location must be an object.")
        return
    try:
        lat = float(value.get("lat"))
        lon = float(value.get("lon"))
    except (TypeError, ValueError):
        errors.append(f"{location}.representative_location is invalid.")
        return
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        errors.append(f"{location}.representative_location is out of range.")


def _validate_optional_geometry(value: object, location: str, errors: list[str]) -> None:
    if value in (None, {}):
        return
    if not isinstance(value, dict):
        errors.append(f"{location}.geometry must be a GeoJSON object.")
        return
    if str(value.get("type", "")) not in {"Point", "Polygon", "MultiPolygon"}:
        errors.append(f"{location}.geometry type must be Point, Polygon or MultiPolygon.")
    if "coordinates" not in value:
        errors.append(f"{location}.geometry coordinates are required.")


def derive_geometry_context(geometry: object) -> dict[str, Any]:
    """Derive stable WGS84 polygon metrics without requiring a GIS runtime."""
    if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        return {}
    coordinates = geometry.get("coordinates")
    polygons = coordinates if geometry.get("type") == "MultiPolygon" else [coordinates]
    if not isinstance(polygons, list):
        return {}
    rings = [polygon[0] for polygon in polygons if isinstance(polygon, list) and polygon and isinstance(polygon[0], list)]
    points = [point for ring in rings for point in ring if isinstance(point, list) and len(point) >= 2]
    if len(points) < 3:
        return {}
    mean_lat = sum(float(point[1]) for point in points) / len(points)
    earth_radius = 6_371_008.8
    scale_x = math.pi / 180 * earth_radius * math.cos(math.radians(mean_lat))
    scale_y = math.pi / 180 * earth_radius
    total_cross = 0.0
    centroid_x = 0.0
    centroid_y = 0.0
    perimeter = 0.0
    for ring in rings:
        projected = [(float(point[0]) * scale_x, float(point[1]) * scale_y) for point in ring if len(point) >= 2]
        if len(projected) < 3:
            continue
        if projected[0] != projected[-1]:
            projected.append(projected[0])
        for (x1, y1), (x2, y2) in zip(projected, projected[1:]):
            cross = x1 * y2 - x2 * y1
            total_cross += cross
            centroid_x += (x1 + x2) * cross
            centroid_y += (y1 + y2) * cross
            perimeter += math.hypot(x2 - x1, y2 - y1)
    if math.isclose(total_cross, 0.0):
        return {}
    centroid_x /= 3 * total_cross
    centroid_y /= 3 * total_cross
    lons = [float(point[0]) for point in points]
    lats = [float(point[1]) for point in points]
    return {
        "geometry": {
            "centroid": {"lat": round(centroid_y / scale_y, 7), "lon": round(centroid_x / scale_x, 7)},
            "area_ha": round(abs(total_cross) / 2 / 10_000, 4),
            "perimeter_m": round(perimeter, 1),
            "bbox": [round(min(lons), 7), round(min(lats), 7), round(max(lons), 7), round(max(lats), 7)],
            "source": "saved_geometry",
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    }


def save_payload(payload: dict[str, Any]) -> Path | None:
    errors = validate_payload(payload)
    if errors:
        raise ValueError("; ".join(errors))
    target = ensure_seeded()
    backup_path: Path | None = None
    if target.exists():
        backup_dir = target.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = backup_dir / f"{target.stem}.{stamp}{target.suffix}"
        counter = 1
        while backup_path.exists():
            backup_path = backup_dir / f"{target.stem}.{stamp}-{counter}{target.suffix}"
            counter += 1
        shutil.copy2(target, backup_path)
        prune_automatic_backups(target)
    candidate = copy.deepcopy(payload)
    metadata = candidate.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata["updated_at"] = datetime.now(UTC).date().isoformat()
    write_json_atomic(target, candidate)
    return backup_path


def micro_area_options(payload: dict[str, Any]) -> list[tuple[str, str]]:
    area_names = {
        str(row.get("area_id", "")): str(row.get("name", ""))
        for row in active_rows(payload, "areas")
    }
    options = []
    for row in active_rows(payload, "micro_areas"):
        micro_id = str(row.get("micro_area_id", ""))
        area_name = area_names.get(str(row.get("area_id", "")), str(row.get("area_id", "")))
        options.append((micro_id, f"{area_name} · {row.get('name', micro_id)}"))
    return sorted(options, key=lambda item: item[1].casefold())


def observation_reference_counts(observations_payload: object) -> dict[str, int]:
    rows = observations_payload.get("observations") if isinstance(observations_payload, dict) else []
    counts: dict[str, int] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            micro_id = str(row.get("micro_area_id", "") or "").strip()
            if micro_id:
                counts[micro_id] = counts.get(micro_id, 0) + 1
    return counts
