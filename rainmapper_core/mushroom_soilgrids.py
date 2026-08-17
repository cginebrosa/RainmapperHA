"""Local, manifest-backed SoilGrids cache and micro-area aggregation.

The prediction runtime never calls SoilGrids.  This module is used only while
creating or changing a micro-area (or by an explicit materialization job).
Raster access uses GDAL command-line tools because those are already present in
the HA and worker images; Python GDAL bindings are intentionally not required.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterator

from rainmapper_core.mushroom_store import write_json_atomic
from rainmapper_core import mushroom_paths


MANIFEST_SCHEMA_VERSION = "1.0"
CACHE_CONTRACT_ID = "soilgrids_tile_512px_v1"
CONTEXT_CONTRACT_ID = "microarea_soilgrids_water_context_v1"
LAND_MASK_COVERAGE_ID = "wv0033_0-5cm_Q0.5"
SOURCE_ID = "soilgrids_2_water_retention"
SOURCE_VERSION = "soilgrids_2.0_wcs_snapshot_v1"
SOURCE_LICENSE = "CC-BY-4.0"
NATIVE_CRS_PROJ4 = "+proj=igh +datum=WGS84 +no_defs"
NATIVE_CRS_URI = "http://www.opengis.net/def/crs/EPSG/0/152160"
PIXEL_SIZE_M = 250
TILE_PIXELS = 512
TILE_SIZE_M = PIXEL_SIZE_M * TILE_PIXELS
# Pixel-boundary origin from WCS DescribeCoverage for the SoilGrids 2.0 grid.
GRID_MIN_X_M = -19_949_750
GRID_MIN_Y_M = -6_147_500
TILE_ID_RE = re.compile(r"^x(-?\d+)_y(-?\d+)$")
PROPERTIES = ("wv0010", "wv0033", "wv1500")
DEPTHS = (
    (0, 5, "0-5cm"),
    (5, 15, "5-15cm"),
    (15, 30, "15-30cm"),
    (30, 60, "30-60cm"),
    (60, 100, "60-100cm"),
    (100, 200, "100-200cm"),
)
QUANTILES = (
    ("Q0.05", "Q0.05"),
    ("Q0.50", "Q0.5"),
    ("Q0.95", "Q0.95"),
)
WCS_VERSION = "2.0.1"
WCS_FORMAT = "GEOTIFF_INT16"
MAX_TILE_BYTES = 64 * 1024 * 1024


class SoilGridsError(RuntimeError):
    """Base error for a safe, diagnosable SoilGrids operation."""


class SoilGridsManifestError(SoilGridsError):
    """The cache manifest is absent, invalid, or inconsistent."""


class SoilGridsDownloadError(SoilGridsError):
    """A WCS response was unavailable or was not a valid raster response."""


class SoilGridsRasterError(SoilGridsError):
    """A cached raster does not satisfy the frozen grid contract."""


def default_cache_root(gis_root: Path | None = None) -> Path:
    configured = os.environ.get("RAINMAPPER_SOILGRIDS_CACHE_ROOT", "").strip()
    if configured:
        return Path(configured)
    if gis_root is not None:
        return Path(gis_root) / "soilgrids"
    configured_gis = os.environ.get("RAINMAPPER_MUSHROOM_GIS_ROOT", "").strip()
    if configured_gis:
        return Path(configured_gis) / "soilgrids"
    media_root = Path("/media/rainmapper/mushroom-GIS")
    if media_root.exists():
        return media_root / "soilgrids"
    shared_root = mushroom_paths.share_root() / "mushroom-GIS"
    if shared_root.exists():
        return shared_root / "soilgrids"
    return mushroom_paths.repo_root() / "mushroom-GIS" / "soilgrids"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def geometry_sha256(geometry: object) -> str:
    if not isinstance(geometry, dict):
        raise ValueError("SoilGrids geometry must be a GeoJSON object.")
    return canonical_sha256(geometry)


def coverage_id(property_id: str, depth_label: str, service_quantile: str) -> str:
    if property_id not in PROPERTIES:
        raise ValueError(f"Unsupported SoilGrids property: {property_id}")
    if depth_label not in {row[2] for row in DEPTHS}:
        raise ValueError(f"Unsupported SoilGrids depth: {depth_label}")
    if service_quantile not in {row[1] for row in QUANTILES}:
        raise ValueError(f"Unsupported SoilGrids quantile: {service_quantile}")
    return f"{property_id}_{depth_label}_{service_quantile}"


def required_coverage_ids() -> tuple[str, ...]:
    return tuple(
        coverage_id(property_id, depth_label, service_quantile)
        for _top, _bottom, depth_label in DEPTHS
        for _stored_quantile, service_quantile in QUANTILES
        for property_id in PROPERTIES
    )


def service_url(property_id: str) -> str:
    if property_id not in PROPERTIES:
        raise ValueError(f"Unsupported SoilGrids property: {property_id}")
    return f"https://maps.isric.org/mapserv?map=/map/{property_id}.map"


def capabilities_url(property_id: str) -> str:
    return service_url(property_id) + "&" + urllib.parse.urlencode(
        {
            "SERVICE": "WCS",
            "VERSION": WCS_VERSION,
            "REQUEST": "GetCapabilities",
        }
    )


def empty_manifest() -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "contract_id": CACHE_CONTRACT_ID,
        "source": {
            "source_id": SOURCE_ID,
            "source_version": SOURCE_VERSION,
            "license": SOURCE_LICENSE,
            "native_crs_proj4": NATIVE_CRS_PROJ4,
            "native_crs_uri": NATIVE_CRS_URI,
            "pixel_size_m": PIXEL_SIZE_M,
            "tile_pixels": TILE_PIXELS,
            "grid_origin_lower_left_m": [GRID_MIN_X_M, GRID_MIN_Y_M],
            "service": "WCS",
            "wcs_version": WCS_VERSION,
            "service_urls": {
                property_id: service_url(property_id) for property_id in PROPERTIES
            },
            "capabilities_sha256": {},
        },
        "coverages": {
            coverage: {"tiles": {}} for coverage in required_coverage_ids()
        },
        "updated_at": None,
    }


def _safe_relative_path(value: object) -> Path:
    path = Path(str(value or ""))
    if not str(value or "").strip() or path.is_absolute() or ".." in path.parts:
        raise SoilGridsManifestError(f"Unsafe SoilGrids asset path: {value}")
    return path


def validate_manifest(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SoilGridsManifestError("SoilGrids manifest must be an object.")
    checked = copy.deepcopy(payload)
    if checked.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise SoilGridsManifestError("Unsupported SoilGrids manifest schema.")
    if checked.get("contract_id") != CACHE_CONTRACT_ID:
        raise SoilGridsManifestError("Unsupported SoilGrids cache contract.")
    source = checked.get("source")
    if not isinstance(source, dict):
        raise SoilGridsManifestError("SoilGrids manifest has no source contract.")
    expected_source = empty_manifest()["source"]
    for key in (
        "source_id",
        "source_version",
        "license",
        "native_crs_proj4",
        "native_crs_uri",
        "pixel_size_m",
        "tile_pixels",
        "grid_origin_lower_left_m",
        "service",
        "wcs_version",
        "service_urls",
    ):
        if source.get(key) != expected_source[key]:
            raise SoilGridsManifestError(
                f"SoilGrids manifest source mismatch: {key}."
            )
    capabilities = source.get("capabilities_sha256", {})
    if not isinstance(capabilities, dict):
        raise SoilGridsManifestError("SoilGrids capabilities hashes must be an object.")
    coverages = checked.get("coverages")
    if not isinstance(coverages, dict):
        raise SoilGridsManifestError("SoilGrids coverages must be an object.")
    expected_coverages = set(required_coverage_ids())
    if set(coverages) != expected_coverages:
        raise SoilGridsManifestError("SoilGrids manifest coverage set is incomplete.")
    for coverage, row in coverages.items():
        if not isinstance(row, dict) or not isinstance(row.get("tiles"), dict):
            raise SoilGridsManifestError(f"Invalid SoilGrids coverage: {coverage}")
        for tile_id, tile in row["tiles"].items():
            tile_bbox(tile_id)
            if not isinstance(tile, dict) or tile.get("status") != "valid":
                raise SoilGridsManifestError(
                    f"Invalid SoilGrids tile entry: {coverage}/{tile_id}"
                )
            if tile.get("bbox_native") != list(tile_bbox(tile_id)):
                raise SoilGridsManifestError(
                    f"SoilGrids tile bbox mismatch: {coverage}/{tile_id}"
                )
            for field in ("raw_sha256", "normalized_sha256"):
                value = tile.get(field)
                if not isinstance(value, str) or len(value) != 64:
                    raise SoilGridsManifestError(
                        f"Invalid {field}: {coverage}/{tile_id}"
                    )
            for field in ("raw_path", "normalized_path"):
                _safe_relative_path(tile.get(field))
            if tile.get("width") != TILE_PIXELS or tile.get("height") != TILE_PIXELS:
                raise SoilGridsManifestError(
                    f"SoilGrids tile dimensions mismatch: {coverage}/{tile_id}"
                )
    return checked


def manifest_path(cache_root: Path) -> Path:
    return Path(cache_root) / "manifest.json"


def load_manifest(cache_root: Path, *, create: bool = False) -> dict[str, Any]:
    path = manifest_path(cache_root)
    if not path.is_file():
        if not create:
            raise SoilGridsManifestError(f"SoilGrids manifest is missing: {path}")
        payload = empty_manifest()
        save_manifest(cache_root, payload)
        return load_manifest(cache_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SoilGridsManifestError(f"Cannot load SoilGrids manifest: {exc}") from exc
    return validate_manifest(payload)


def save_manifest(cache_root: Path, payload: object) -> None:
    checked = validate_manifest(payload)
    checked["updated_at"] = utc_now()
    root = Path(cache_root)
    root.mkdir(parents=True, exist_ok=True)
    write_json_atomic(manifest_path(root), checked)


def manifest_sha256(payload: object) -> str:
    checked = validate_manifest(payload)
    return canonical_sha256(checked)


def tile_id(tile_x: int, tile_y: int) -> str:
    return f"x{int(tile_x)}_y{int(tile_y)}"


def tile_indices(value: str) -> tuple[int, int]:
    match = TILE_ID_RE.fullmatch(str(value))
    if match is None:
        raise SoilGridsManifestError(f"Invalid SoilGrids tile ID: {value}")
    return int(match.group(1)), int(match.group(2))


def tile_bbox(value: str) -> tuple[int, int, int, int]:
    tile_x, tile_y = tile_indices(value)
    min_x = GRID_MIN_X_M + tile_x * TILE_SIZE_M
    min_y = GRID_MIN_Y_M + tile_y * TILE_SIZE_M
    return min_x, min_y, min_x + TILE_SIZE_M, min_y + TILE_SIZE_M


def tile_ids_for_bounds(bounds: tuple[float, float, float, float]) -> list[str]:
    min_x, min_y, max_x, max_y = bounds
    if not all(math.isfinite(value) for value in bounds) or max_x < min_x or max_y < min_y:
        raise ValueError("Invalid projected SoilGrids bounds.")
    first_x = math.floor((min_x - GRID_MIN_X_M) / TILE_SIZE_M)
    last_x = math.floor((max_x - GRID_MIN_X_M) / TILE_SIZE_M)
    first_y = math.floor((min_y - GRID_MIN_Y_M) / TILE_SIZE_M)
    last_y = math.floor((max_y - GRID_MIN_Y_M) / TILE_SIZE_M)
    return [
        tile_id(x, y)
        for y in range(first_y, last_y + 1)
        for x in range(first_x, last_x + 1)
    ]


def expand_tile_rectangle(values: list[str], margin_tiles: int = 0) -> list[str]:
    if not values:
        return []
    if margin_tiles < 0:
        raise ValueError("SoilGrids tile margin cannot be negative.")
    indices = [tile_indices(value) for value in values]
    min_x = min(value[0] for value in indices) - margin_tiles
    max_x = max(value[0] for value in indices) + margin_tiles
    min_y = min(value[1] for value in indices) - margin_tiles
    max_y = max(value[1] for value in indices) + margin_tiles
    return [
        tile_id(x, y)
        for y in range(min_y, max_y + 1)
        for x in range(min_x, max_x + 1)
    ]


def land_tile_ids_from_manifest(
    manifest: dict[str, Any], values: list[str]
) -> tuple[list[str], list[str]]:
    """Classify reserve tiles using the topsoil median water layer as land mask."""
    try:
        tiles = manifest["coverages"][LAND_MASK_COVERAGE_ID]["tiles"]
    except (KeyError, TypeError) as exc:
        raise SoilGridsManifestError("SoilGrids land-mask coverage is missing.") from exc
    land: list[str] = []
    empty: list[str] = []
    for value in sorted(set(values), key=tile_indices):
        row = tiles.get(value)
        if not isinstance(row, dict) or row.get("status") != "valid":
            raise SoilGridsManifestError(
                f"Land-mask tile is not cached and valid: {value}"
            )
        maximum = row.get("value_max")
        if not isinstance(maximum, (int, float)):
            raise SoilGridsManifestError(
                f"Land-mask tile has no validated value range: {value}"
            )
        (land if float(maximum) > 0 else empty).append(value)
    return land, empty


def _command(
    args: list[str],
    *,
    input_text: str | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            check=True,
            timeout=timeout,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stderr = getattr(exc, "stderr", "") or ""
        raise SoilGridsError(
            f"SoilGrids command failed ({Path(args[0]).name}): {stderr.strip()}"
        ) from exc


def _geometry_rings(geometry: object) -> list[list[list[tuple[float, float]]]]:
    if not isinstance(geometry, dict) or geometry.get("type") not in {
        "Polygon",
        "MultiPolygon",
    }:
        raise ValueError("SoilGrids requires a Polygon or MultiPolygon geometry.")
    source = geometry.get("coordinates")
    polygons = source if geometry.get("type") == "MultiPolygon" else [source]
    if not isinstance(polygons, list):
        raise ValueError("SoilGrids geometry coordinates are invalid.")
    normalized: list[list[list[tuple[float, float]]]] = []
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            continue
        rings: list[list[tuple[float, float]]] = []
        for ring in polygon:
            if not isinstance(ring, list):
                continue
            points = [
                (float(point[0]), float(point[1]))
                for point in ring
                if isinstance(point, (list, tuple)) and len(point) >= 2
            ]
            if len(points) >= 3:
                if points[0] != points[-1]:
                    points.append(points[0])
                rings.append(points)
        if rings:
            normalized.append(rings)
    if not normalized:
        raise ValueError("SoilGrids geometry has no valid polygon rings.")
    return normalized


def transform_geometry(
    geometry: object,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = _command,
) -> list[list[list[tuple[float, float]]]]:
    rings = _geometry_rings(geometry)
    points = [point for polygon in rings for ring in polygon for point in ring]
    stdin = "".join(f"{lon} {lat}\n" for lon, lat in points)
    result = command_runner(
        [
            "gdaltransform",
            "-s_srs",
            "EPSG:4326",
            "-t_srs",
            NATIVE_CRS_PROJ4,
            "-output_xy",
        ],
        input_text=stdin,
        timeout=60,
    )
    transformed: list[tuple[float, float]] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        transformed.append((float(parts[0]), float(parts[1])))
    if len(transformed) != len(points):
        raise SoilGridsError("GDAL returned an incomplete geometry transformation.")
    iterator = iter(transformed)
    return [
        [[next(iterator) for _point in ring] for ring in polygon]
        for polygon in rings
    ]


def projected_bounds(
    polygons: list[list[list[tuple[float, float]]]],
) -> tuple[float, float, float, float]:
    points = [point for polygon in polygons for ring in polygon for point in ring]
    if not points:
        raise ValueError("Projected SoilGrids geometry is empty.")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _polygon_area(ring: list[tuple[float, float]]) -> float:
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(ring, ring[1:])
        )
        / 2
    )


def _clip_ring(
    ring: list[tuple[float, float]],
    bounds: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    min_x, min_y, max_x, max_y = bounds
    points = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)

    def clip(
        source: list[tuple[float, float]],
        inside: Callable[[tuple[float, float]], bool],
        intersection: Callable[
            [tuple[float, float], tuple[float, float]], tuple[float, float]
        ],
    ) -> list[tuple[float, float]]:
        if not source:
            return []
        output: list[tuple[float, float]] = []
        previous = source[-1]
        previous_inside = inside(previous)
        for current in source:
            current_inside = inside(current)
            if current_inside:
                if not previous_inside:
                    output.append(intersection(previous, current))
                output.append(current)
            elif previous_inside:
                output.append(intersection(previous, current))
            previous = current
            previous_inside = current_inside
        return output

    def vertical(x: float) -> Callable[[tuple[float, float], tuple[float, float]], tuple[float, float]]:
        def intersect(left: tuple[float, float], right: tuple[float, float]) -> tuple[float, float]:
            dx = right[0] - left[0]
            ratio = 0.0 if math.isclose(dx, 0.0) else (x - left[0]) / dx
            return x, left[1] + ratio * (right[1] - left[1])

        return intersect

    def horizontal(y: float) -> Callable[[tuple[float, float], tuple[float, float]], tuple[float, float]]:
        def intersect(left: tuple[float, float], right: tuple[float, float]) -> tuple[float, float]:
            dy = right[1] - left[1]
            ratio = 0.0 if math.isclose(dy, 0.0) else (y - left[1]) / dy
            return left[0] + ratio * (right[0] - left[0]), y

        return intersect

    points = clip(points, lambda point: point[0] >= min_x, vertical(min_x))
    points = clip(points, lambda point: point[0] <= max_x, vertical(max_x))
    points = clip(points, lambda point: point[1] >= min_y, horizontal(min_y))
    points = clip(points, lambda point: point[1] <= max_y, horizontal(max_y))
    if len(points) >= 3 and points[0] != points[-1]:
        points.append(points[0])
    return points


def geometry_area(polygons: list[list[list[tuple[float, float]]]]) -> float:
    total = 0.0
    for polygon in polygons:
        total += _polygon_area(polygon[0])
        total -= sum(_polygon_area(ring) for ring in polygon[1:])
    return max(0.0, total)


def geometry_intersection_area(
    polygons: list[list[list[tuple[float, float]]]],
    bounds: tuple[float, float, float, float],
) -> float:
    total = 0.0
    for polygon in polygons:
        outer = _clip_ring(polygon[0], bounds)
        total += _polygon_area(outer) if outer else 0.0
        for hole in polygon[1:]:
            clipped = _clip_ring(hole, bounds)
            total -= _polygon_area(clipped) if clipped else 0.0
    return max(0.0, total)


def tile_ids_for_geometry(
    polygons: list[list[list[tuple[float, float]]]],
) -> list[str]:
    candidates = tile_ids_for_bounds(projected_bounds(polygons))
    return [
        value
        for value in candidates
        if geometry_intersection_area(polygons, tile_bbox(value)) > 0
    ]


def wcs_get_coverage_url(coverage: str, value: str) -> str:
    return wcs_get_bounds_url(coverage, tile_bbox(value))


def wcs_get_bounds_url(
    coverage: str, bounds: tuple[int, int, int, int]
) -> str:
    property_id = coverage.split("_", 1)[0]
    min_x, min_y, max_x, max_y = bounds
    query = [
        ("map", f"/map/{property_id}.map"),
        ("SERVICE", "WCS"),
        ("VERSION", WCS_VERSION),
        ("REQUEST", "GetCoverage"),
        ("COVERAGEID", coverage),
        ("FORMAT", WCS_FORMAT),
        ("SUBSET", f"X({min_x},{max_x})"),
        ("SUBSET", f"Y({min_y},{max_y})"),
        ("SUBSETTINGCRS", NATIVE_CRS_URI),
        ("OUTPUTCRS", NATIVE_CRS_URI),
    ]
    return "https://maps.isric.org/mapserv?" + urllib.parse.urlencode(query)


def _default_fetcher(url: str, destination: Path, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RainmapperHA-SoilGridsCache/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = str(response.headers.get("Content-Type") or "").lower()
            if "tiff" not in content_type and "octet-stream" not in content_type:
                raise SoilGridsDownloadError(
                    f"SoilGrids returned unexpected content type: {content_type or 'missing'}"
                )
            size = 0
            with Path(destination).open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_TILE_BYTES:
                        raise SoilGridsDownloadError("SoilGrids tile exceeds size limit.")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            return {
                "http_status": int(getattr(response, "status", 200)),
                "content_type": content_type,
                "size_bytes": size,
            }
    except SoilGridsDownloadError:
        raise
    except Exception as exc:
        raise SoilGridsDownloadError(f"Cannot download SoilGrids tile: {exc}") from exc


def _default_capabilities_fetcher(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RainmapperHA-SoilGridsCache/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = str(response.headers.get("Content-Type") or "").lower()
            if "xml" not in content_type:
                raise SoilGridsDownloadError(
                    "SoilGrids GetCapabilities did not return XML."
                )
            payload = response.read(4 * 1024 * 1024 + 1)
            if len(payload) > 4 * 1024 * 1024:
                raise SoilGridsDownloadError("SoilGrids capabilities exceed size limit.")
            return payload
    except SoilGridsDownloadError:
        raise
    except Exception as exc:
        raise SoilGridsDownloadError(
            f"Cannot download SoilGrids capabilities: {exc}"
        ) from exc


def record_capabilities(
    cache_root: Path,
    *,
    fetcher: Callable[[str, int], bytes] = _default_capabilities_fetcher,
    timeout: int = 120,
) -> dict[str, str]:
    """Snapshot and hash the three official WCS capability documents."""
    root = Path(cache_root)
    results: dict[str, str] = {}
    with cache_lock(root):
        manifest = load_manifest(root, create=True)
        reports = root / "reports" / SOURCE_VERSION / "capabilities"
        reports.mkdir(parents=True, exist_ok=True)
        staged: list[tuple[Path, Path]] = []
        try:
            for property_id in PROPERTIES:
                payload = fetcher(capabilities_url(property_id), timeout)
                try:
                    document = ET.fromstring(payload)
                except ET.ParseError as exc:
                    raise SoilGridsDownloadError(
                        f"Invalid SoilGrids capabilities XML: {property_id}"
                    ) from exc
                advertised = {
                    str(node.text or "").strip()
                    for node in document.findall(
                        ".//{http://www.opengis.net/wcs/2.0}CoverageId"
                    )
                }
                expected = {
                    coverage
                    for coverage in required_coverage_ids()
                    if coverage.startswith(f"{property_id}_")
                }
                missing = sorted(expected - advertised)
                if missing:
                    raise SoilGridsDownloadError(
                        f"SoilGrids capabilities omit required coverage: {missing[0]}"
                    )
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{property_id}.", suffix=".xml.tmp", dir=reports
                )
                temporary = Path(temporary_name)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                target = reports / f"{property_id}.xml"
                staged.append((temporary, target))
                results[property_id] = hashlib.sha256(payload).hexdigest()
            for temporary, target in staged:
                os.replace(temporary, target)
            manifest["source"]["capabilities_sha256"] = dict(sorted(results.items()))
            manifest["source"]["capabilities_recorded_at"] = utc_now()
            save_manifest(root, manifest)
        finally:
            for temporary, _target in staged:
                temporary.unlink(missing_ok=True)
    return dict(sorted(results.items()))


def _gdalinfo(path: Path) -> dict[str, Any]:
    result = _command(["gdalinfo", "-json", "-mm", str(path)], timeout=120)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SoilGridsRasterError(f"Invalid gdalinfo output for {path}") from exc
    if not isinstance(payload, dict):
        raise SoilGridsRasterError(f"Invalid raster metadata for {path}")
    return payload


def validate_raster(
    path: Path,
    expected_bbox: tuple[int, int, int, int],
    *,
    require_crs: bool,
    expected_size: tuple[int, int] = (TILE_PIXELS, TILE_PIXELS),
) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file() or source.stat().st_size < 8:
        raise SoilGridsRasterError(f"SoilGrids raster is missing or empty: {source}")
    if source.read_bytes()[:4] not in {b"II*\x00", b"MM\x00*"}:
        raise SoilGridsRasterError(f"SoilGrids response is not a TIFF: {source}")
    payload = _gdalinfo(source)
    if payload.get("driverShortName") != "GTiff":
        raise SoilGridsRasterError(f"SoilGrids raster is not GeoTIFF: {source}")
    if payload.get("size") != list(expected_size):
        raise SoilGridsRasterError(f"SoilGrids raster has invalid dimensions: {source}")
    min_x, min_y, max_x, max_y = expected_bbox
    expected_transform = [
        float(min_x),
        float(PIXEL_SIZE_M),
        0.0,
        float(max_y),
        0.0,
        -float(PIXEL_SIZE_M),
    ]
    transform = payload.get("geoTransform")
    if not isinstance(transform, list) or len(transform) != 6 or any(
        not math.isclose(float(left), right, rel_tol=0.0, abs_tol=1e-6)
        for left, right in zip(transform, expected_transform)
    ):
        raise SoilGridsRasterError(f"SoilGrids raster is not grid-aligned: {source}")
    bands = payload.get("bands")
    band = bands[0] if isinstance(bands, list) and len(bands) == 1 else None
    if not isinstance(band, dict) or band.get("type") != "Int16":
        raise SoilGridsRasterError(f"SoilGrids raster must have one Int16 band: {source}")
    minimum = band.get("computedMin")
    maximum = band.get("computedMax")
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        raise SoilGridsRasterError(f"SoilGrids raster range is unavailable: {source}")
    if float(minimum) < 0 or float(maximum) > 1000:
        raise SoilGridsRasterError(f"SoilGrids raster values are out of range: {source}")
    if require_crs and not isinstance(payload.get("coordinateSystem"), dict):
        raise SoilGridsRasterError(f"Normalized SoilGrids raster has no CRS: {source}")
    return {
        "width": expected_size[0],
        "height": expected_size[1],
        "minimum": float(minimum),
        "maximum": float(maximum),
        "size_bytes": source.stat().st_size,
        "sha256": file_sha256(source),
    }


def _asset_relative_paths(coverage: str, value: str) -> tuple[Path, Path]:
    raw = Path("raw-wcs") / SOURCE_VERSION / coverage / f"{value}.tif"
    normalized = Path("normalized") / SOURCE_VERSION / coverage / f"{value}.tif"
    return raw, normalized


@contextmanager
def cache_lock(cache_root: Path) -> Iterator[None]:
    root = Path(cache_root)
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".cache.lock"
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _registered_tile_is_valid(
    cache_root: Path,
    manifest: dict[str, Any],
    coverage: str,
    value: str,
) -> bool:
    tile = manifest["coverages"][coverage]["tiles"].get(value)
    if not isinstance(tile, dict) or tile.get("status") != "valid":
        return False
    for path_field, hash_field in (
        ("raw_path", "raw_sha256"),
        ("normalized_path", "normalized_sha256"),
    ):
        path = Path(cache_root) / _safe_relative_path(tile.get(path_field))
        if not path.is_file() or file_sha256(path) != tile.get(hash_field):
            return False
    return True


def ensure_tile(
    cache_root: Path,
    coverage: str,
    value: str,
    *,
    fetcher: Callable[[str, Path, int], dict[str, Any]] = _default_fetcher,
    timeout: int = 120,
) -> dict[str, Any]:
    if coverage not in set(required_coverage_ids()):
        raise ValueError(f"Unsupported SoilGrids coverage: {coverage}")
    bbox = tile_bbox(value)
    root = Path(cache_root)
    with cache_lock(root):
        manifest = load_manifest(root, create=True)
        if _registered_tile_is_valid(root, manifest, coverage, value):
            return {"status": "reused", "tile": copy.deepcopy(
                manifest["coverages"][coverage]["tiles"][value]
            )}
        staging_root = root / "staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{coverage}.{value}.", dir=staging_root))
        raw_stage = staging / "raw.tif"
        normalized_stage = staging / "normalized.tif"
        try:
            response = fetcher(wcs_get_coverage_url(coverage, value), raw_stage, timeout)
            raw_metadata = validate_raster(raw_stage, bbox, require_crs=False)
            _command(
                [
                    "gdal_translate",
                    "-q",
                    "-of",
                    "GTiff",
                    "-a_srs",
                    NATIVE_CRS_PROJ4,
                    "-co",
                    "TILED=YES",
                    "-co",
                    "COMPRESS=DEFLATE",
                    "-co",
                    "PREDICTOR=2",
                    str(raw_stage),
                    str(normalized_stage),
                ],
                timeout=120,
            )
            normalized_metadata = validate_raster(
                normalized_stage, bbox, require_crs=True
            )
            raw_relative, normalized_relative = _asset_relative_paths(coverage, value)
            raw_target = root / raw_relative
            normalized_target = root / normalized_relative
            raw_target.parent.mkdir(parents=True, exist_ok=True)
            normalized_target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(raw_stage, raw_target)
            os.replace(normalized_stage, normalized_target)
            tile = {
                "bbox_native": list(bbox),
                "raw_path": raw_relative.as_posix(),
                "normalized_path": normalized_relative.as_posix(),
                "raw_sha256": raw_metadata["sha256"],
                "normalized_sha256": normalized_metadata["sha256"],
                "raw_size_bytes": raw_metadata["size_bytes"],
                "normalized_size_bytes": normalized_metadata["size_bytes"],
                "width": TILE_PIXELS,
                "height": TILE_PIXELS,
                "value_min": normalized_metadata["minimum"],
                "value_max": normalized_metadata["maximum"],
                "status": "valid",
                "download": response,
                "validated_at": utc_now(),
            }
            manifest["coverages"][coverage]["tiles"][value] = tile
            save_manifest(root, manifest)
            return {"status": "downloaded", "tile": copy.deepcopy(tile)}
        finally:
            shutil.rmtree(staging, ignore_errors=True)


def ensure_tiles_bulk(
    cache_root: Path,
    coverage: str,
    values: list[str],
    *,
    fetcher: Callable[[str, Path, int], dict[str, Any]] = _default_fetcher,
    timeout: int = 300,
) -> dict[str, Any]:
    """Download one rectangular WCS clip and split missing cache tiles locally."""
    if coverage not in set(required_coverage_ids()):
        raise ValueError(f"Unsupported SoilGrids coverage: {coverage}")
    selected = sorted(set(values), key=tile_indices)
    if not selected:
        return {"downloaded": 0, "reused": 0, "tile_ids": []}
    root = Path(cache_root)
    with cache_lock(root):
        manifest = load_manifest(root, create=True)
        reusable = [
            value
            for value in selected
            if _registered_tile_is_valid(root, manifest, coverage, value)
        ]
        missing = [value for value in selected if value not in set(reusable)]
        if not missing:
            return {
                "downloaded": 0,
                "reused": len(reusable),
                "tile_ids": selected,
            }
        indices = [tile_indices(value) for value in missing]
        min_tile_x = min(value[0] for value in indices)
        max_tile_x = max(value[0] for value in indices)
        min_tile_y = min(value[1] for value in indices)
        max_tile_y = max(value[1] for value in indices)
        min_x, min_y, _max_x, _max_y = tile_bbox(
            tile_id(min_tile_x, min_tile_y)
        )
        _min_x, _min_y, max_x, max_y = tile_bbox(
            tile_id(max_tile_x, max_tile_y)
        )
        bulk_bounds = (min_x, min_y, max_x, max_y)
        bulk_size = (
            (max_tile_x - min_tile_x + 1) * TILE_PIXELS,
            (max_tile_y - min_tile_y + 1) * TILE_PIXELS,
        )
        batch_id = (
            f"x{min_tile_x}-{max_tile_x}_y{min_tile_y}-{max_tile_y}"
        )
        staging_root = root / "staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(prefix=f".{coverage}.{batch_id}.", dir=staging_root)
        )
        raw_stage = staging / "bulk-raw.tif"
        normalized_bulk = staging / "bulk-normalized.tif"
        try:
            response = fetcher(
                wcs_get_bounds_url(coverage, bulk_bounds), raw_stage, timeout
            )
            raw_metadata = validate_raster(
                raw_stage,
                bulk_bounds,
                require_crs=False,
                expected_size=bulk_size,
            )
            _command(
                [
                    "gdal_translate",
                    "-q",
                    "-of",
                    "GTiff",
                    "-a_srs",
                    NATIVE_CRS_PROJ4,
                    "-co",
                    "TILED=YES",
                    "-co",
                    "COMPRESS=DEFLATE",
                    "-co",
                    "PREDICTOR=2",
                    str(raw_stage),
                    str(normalized_bulk),
                ],
                timeout=300,
            )
            validate_raster(
                normalized_bulk,
                bulk_bounds,
                require_crs=True,
                expected_size=bulk_size,
            )
            bulk_relative = (
                Path("raw-wcs")
                / SOURCE_VERSION
                / "bulk"
                / coverage
                / f"{batch_id}-{raw_metadata['sha256'][:16]}.tif"
            )
            bulk_target = root / bulk_relative
            bulk_target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(raw_stage, bulk_target)
            tile_rows: dict[str, dict[str, Any]] = {}
            for value in missing:
                tile_stage = staging / f"{value}.tif"
                tile_bounds_value = tile_bbox(value)
                tile_min_x, tile_min_y, tile_max_x, tile_max_y = tile_bounds_value
                _command(
                    [
                        "gdal_translate",
                        "-q",
                        "-of",
                        "GTiff",
                        "-projwin",
                        str(tile_min_x),
                        str(tile_max_y),
                        str(tile_max_x),
                        str(tile_min_y),
                        "-co",
                        "TILED=YES",
                        "-co",
                        "COMPRESS=DEFLATE",
                        "-co",
                        "PREDICTOR=2",
                        str(normalized_bulk),
                        str(tile_stage),
                    ],
                    timeout=120,
                )
                tile_metadata = validate_raster(
                    tile_stage, tile_bounds_value, require_crs=True
                )
                _raw_relative, normalized_relative = _asset_relative_paths(
                    coverage, value
                )
                normalized_target = root / normalized_relative
                normalized_target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(tile_stage, normalized_target)
                tile_rows[value] = {
                    "bbox_native": list(tile_bounds_value),
                    "raw_path": bulk_relative.as_posix(),
                    "normalized_path": normalized_relative.as_posix(),
                    "raw_sha256": raw_metadata["sha256"],
                    "normalized_sha256": tile_metadata["sha256"],
                    "raw_size_bytes": raw_metadata["size_bytes"],
                    "normalized_size_bytes": tile_metadata["size_bytes"],
                    "width": TILE_PIXELS,
                    "height": TILE_PIXELS,
                    "value_min": tile_metadata["minimum"],
                    "value_max": tile_metadata["maximum"],
                    "status": "valid",
                    "download": {**response, "batch_id": batch_id},
                    "validated_at": utc_now(),
                }
            manifest["coverages"][coverage]["tiles"].update(tile_rows)
            save_manifest(root, manifest)
            return {
                "downloaded": len(missing),
                "reused": len(reusable),
                "tile_ids": selected,
                "batch_id": batch_id,
            }
        finally:
            shutil.rmtree(staging, ignore_errors=True)


def ensure_geometry_cache(
    cache_root: Path,
    geometry: object,
    *,
    fetcher: Callable[[str, Path, int], dict[str, Any]] = _default_fetcher,
    timeout: int = 120,
) -> dict[str, Any]:
    polygons = transform_geometry(geometry)
    tiles = tile_ids_for_geometry(polygons)
    results = {"downloaded": 0, "reused": 0}
    for coverage in required_coverage_ids():
        for value in tiles:
            outcome = ensure_tile(
                cache_root,
                coverage,
                value,
                fetcher=fetcher,
                timeout=timeout,
            )
            results[outcome["status"]] += 1
    return {
        "coverage_count": len(required_coverage_ids()),
        "tile_ids": tiles,
        **results,
    }


def context_is_current(context: object, geometry: object) -> bool:
    if not isinstance(context, dict):
        return False
    source = context.get("source")
    return (
        context.get("contract_id") == CONTEXT_CONTRACT_ID
        and context.get("geometry_hash") == geometry_sha256(geometry)
        and isinstance(source, dict)
        and source.get("source_id") == SOURCE_ID
        and source.get("source_version") == SOURCE_VERSION
        and source.get("cache_contract_id") == CACHE_CONTRACT_ID
        and context.get("status") in {"complete", "partial", "no_coverage"}
    )


def resolve_geometry_context(
    cache_root: Path,
    geometry: object,
    *,
    ensure_missing: bool,
) -> dict[str, Any]:
    """Resolve a static context, optionally extending the cache first."""
    try:
        context = aggregate_geometry(cache_root, geometry)
        if context.get("status") == "pending" and ensure_missing:
            ensure_geometry_cache(cache_root, geometry)
            context = aggregate_geometry(cache_root, geometry)
        return context
    except Exception as exc:
        try:
            polygons = transform_geometry(geometry)
            tiles = tile_ids_for_geometry(polygons)
        except Exception:
            tiles = []
        context = pending_context(
            geometry,
            tile_ids=tiles,
            reasons=["soilgrids_resolution_error"],
        )
        context["quality"]["error_type"] = type(exc).__name__
        context["quality"]["error"] = str(exc)
        return context


def _read_xyz_window(
    path: Path,
    *,
    col_start: int,
    row_start: int,
    width: int,
    height: int,
) -> dict[tuple[int, int], float]:
    if width <= 0 or height <= 0:
        return {}
    result = _command(
        [
            "gdal_translate",
            "-q",
            "-of",
            "XYZ",
            "-srcwin",
            str(col_start),
            str(row_start),
            str(width),
            str(height),
            str(path),
            "/vsistdout/",
        ],
        timeout=120,
    )
    values: dict[tuple[int, int], float] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        x, y, value = (float(part) for part in parts)
        col = int(math.floor((x - GRID_MIN_X_M) / PIXEL_SIZE_M))
        row = int(math.floor((y - GRID_MIN_Y_M) / PIXEL_SIZE_M))
        values[(col, row)] = value
    return values


def _tile_window(
    geometry_bounds: tuple[float, float, float, float],
    value: str,
) -> tuple[int, int, int, int]:
    geometry_min_x, geometry_min_y, geometry_max_x, geometry_max_y = geometry_bounds
    min_x, min_y, max_x, max_y = tile_bbox(value)
    clipped_min_x = max(min_x, geometry_min_x)
    clipped_max_x = min(max_x, geometry_max_x)
    clipped_min_y = max(min_y, geometry_min_y)
    clipped_max_y = min(max_y, geometry_max_y)
    col_start = max(0, math.floor((clipped_min_x - min_x) / PIXEL_SIZE_M))
    col_end = min(TILE_PIXELS - 1, math.floor((clipped_max_x - min_x) / PIXEL_SIZE_M))
    row_start = max(0, math.floor((max_y - clipped_max_y) / PIXEL_SIZE_M))
    row_end = min(TILE_PIXELS - 1, math.floor((max_y - clipped_min_y) / PIXEL_SIZE_M))
    return col_start, row_start, col_end - col_start + 1, row_end - row_start + 1


def aggregate_geometry(
    cache_root: Path,
    geometry: object,
) -> dict[str, Any]:
    root = Path(cache_root)
    manifest = load_manifest(root)
    polygons = transform_geometry(geometry)
    bounds = projected_bounds(polygons)
    total_area = geometry_area(polygons)
    if total_area <= 0:
        raise ValueError("SoilGrids geometry has no positive projected area.")
    tiles = tile_ids_for_geometry(polygons)
    missing_assets: list[str] = []
    for coverage in required_coverage_ids():
        for value in tiles:
            if not _registered_tile_is_valid(root, manifest, coverage, value):
                missing_assets.append(f"{coverage}/{value}")
    if missing_assets:
        return pending_context(
            geometry,
            tile_ids=tiles,
            reasons=["missing_cache_assets"],
            missing_assets=missing_assets,
        )

    depths: list[dict[str, Any]] = []
    all_coverage_fractions: list[float] = []
    asset_hashes: list[dict[str, str]] = []
    spatial_min: dict[str, float] = {}
    spatial_max: dict[str, float] = {}
    for top_cm, bottom_cm, depth_label in DEPTHS:
        area_weighted: dict[str, dict[str, float | None]] = {}
        quantile_pixel_counts: dict[str, int] = {}
        for stored_quantile, service_quantile in QUANTILES:
            coverages = {
                property_id: coverage_id(property_id, depth_label, service_quantile)
                for property_id in PROPERTIES
            }
            sums = {property_id: 0.0 for property_id in PROPERTIES}
            valid_area = 0.0
            valid_pixels = 0
            for value in tiles:
                window = _tile_window(bounds, value)
                tile_values: dict[str, dict[tuple[int, int], float]] = {}
                for property_id, coverage in coverages.items():
                    tile = manifest["coverages"][coverage]["tiles"][value]
                    normalized_path = root / _safe_relative_path(
                        tile["normalized_path"]
                    )
                    tile_values[property_id] = _read_xyz_window(
                        normalized_path,
                        col_start=window[0],
                        row_start=window[1],
                        width=window[2],
                        height=window[3],
                    )
                    asset_hashes.append(
                        {
                            "coverage_id": coverage,
                            "tile_id": value,
                            "sha256": tile["normalized_sha256"],
                        }
                    )
                common_cells = set.intersection(
                    *(set(values) for values in tile_values.values())
                )
                for col, row in common_cells:
                    values = {
                        property_id: tile_values[property_id][(col, row)]
                        for property_id in PROPERTIES
                    }
                    if any(value <= 0 or value > 1000 for value in values.values()):
                        continue
                    pixel_bounds = (
                        GRID_MIN_X_M + col * PIXEL_SIZE_M,
                        GRID_MIN_Y_M + row * PIXEL_SIZE_M,
                        GRID_MIN_X_M + (col + 1) * PIXEL_SIZE_M,
                        GRID_MIN_Y_M + (row + 1) * PIXEL_SIZE_M,
                    )
                    intersection_area = geometry_intersection_area(
                        polygons, pixel_bounds
                    )
                    if intersection_area <= 0:
                        continue
                    valid_pixels += 1
                    valid_area += intersection_area
                    for property_id, value_number in values.items():
                        sums[property_id] += value_number * intersection_area
                        key = coverage_id(
                            property_id, depth_label, service_quantile
                        )
                        spatial_min[key] = min(
                            spatial_min.get(key, value_number), value_number
                        )
                        spatial_max[key] = max(
                            spatial_max.get(key, value_number), value_number
                        )
            coverage_fraction = min(1.0, max(0.0, valid_area / total_area))
            all_coverage_fractions.append(coverage_fraction)
            quantile_pixel_counts[stored_quantile] = valid_pixels
            area_weighted[stored_quantile] = {
                f"{property_id}_mm_per_m": (
                    round(sums[property_id] / valid_area, 6)
                    if valid_area > 0
                    else None
                )
                for property_id in PROPERTIES
            }
        depths.append(
            {
                "top_cm": top_cm,
                "bottom_cm": bottom_cm,
                "valid_pixel_count": min(quantile_pixel_counts.values()),
                "quantile_valid_pixel_counts": quantile_pixel_counts,
                "area_weighted": area_weighted,
            }
        )
    minimum_coverage = min(all_coverage_fractions) if all_coverage_fractions else 0.0
    if minimum_coverage >= 0.999:
        status = "complete"
        reasons: list[str] = []
    elif minimum_coverage > 0:
        status = "partial"
        reasons = ["partial_soilgrids_coverage"]
    else:
        status = "no_coverage"
        reasons = ["no_soilgrids_coverage"]
    unique_assets = sorted(
        {tuple(sorted(row.items())) for row in asset_hashes}
    )
    context: dict[str, Any] = {
        "contract_id": CONTEXT_CONTRACT_ID,
        "geometry_hash": geometry_sha256(geometry),
        "generated_at": utc_now(),
        "status": status,
        "source": {
            "source_id": SOURCE_ID,
            "source_version": SOURCE_VERSION,
            "cache_contract_id": CACHE_CONTRACT_ID,
            "manifest_hash": manifest_sha256(manifest),
            "tile_ids": tiles,
            "asset_hashes": [dict(row) for row in unique_assets],
        },
        "coverage_fraction": round(minimum_coverage, 6),
        "depths": depths,
        "quality": {
            "spatial_min": dict(sorted(spatial_min.items())),
            "spatial_max": dict(sorted(spatial_max.items())),
            "exclusion_reasons": reasons,
        },
    }
    identity_payload = copy.deepcopy(context)
    identity_payload.pop("generated_at", None)
    context["context_hash"] = canonical_sha256(identity_payload)
    return context


def pending_context(
    geometry: object,
    *,
    tile_ids: list[str],
    reasons: list[str],
    missing_assets: list[str] | None = None,
) -> dict[str, Any]:
    context = {
        "contract_id": CONTEXT_CONTRACT_ID,
        "geometry_hash": geometry_sha256(geometry),
        "generated_at": utc_now(),
        "status": "pending",
        "source": {
            "source_id": SOURCE_ID,
            "source_version": SOURCE_VERSION,
            "cache_contract_id": CACHE_CONTRACT_ID,
            "tile_ids": list(tile_ids),
        },
        "coverage_fraction": 0.0,
        "depths": [],
        "quality": {
            "spatial_min": {},
            "spatial_max": {},
            "exclusion_reasons": sorted(set(reasons)),
            "missing_assets": sorted(missing_assets or []),
        },
    }
    identity_payload = copy.deepcopy(context)
    identity_payload.pop("generated_at", None)
    context["context_hash"] = canonical_sha256(identity_payload)
    return context


def apply_micro_area_context(
    micro_area: dict[str, Any], context: dict[str, Any]
) -> None:
    if context.get("contract_id") != CONTEXT_CONTRACT_ID:
        raise ValueError("Invalid SoilGrids micro-area context contract.")
    derived_context = (
        copy.deepcopy(micro_area.get("derived_context"))
        if isinstance(micro_area.get("derived_context"), dict)
        else {}
    )
    derived_context["soilgrids_water"] = copy.deepcopy(context)
    micro_area["derived_context"] = derived_context
