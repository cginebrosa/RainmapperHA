"""Editable operational regions for accepting station coordinate corrections."""

import json
import math
from pathlib import Path


def load_coordinate_regions(data_dir: Path) -> tuple[tuple[float, ...], ...]:
    path = Path(data_dir) / "weather_coordinate_policy.json"
    if not path.exists():
        path = Path(__file__).with_suffix(".json")
    if path.stat().st_size > 16384:
        raise ValueError("Weather coordinate policy exceeds 16 KiB")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "weather_coordinate_policy_v1":
        raise ValueError("Unsupported weather coordinate policy")
    regions = payload.get("regions")
    if not isinstance(regions, list) or len(regions) > 32:
        raise ValueError("Expected at most 32 weather coordinate regions")
    result = []
    for region in regions:
        bounds = tuple(float(region[key]) for key in ("south", "north", "west", "east"))
        south, north, west, east = bounds
        if not all(math.isfinite(value) for value in bounds) or not (
            -90 <= south < north <= 90 and -180 <= west < east <= 180
        ):
            raise ValueError("Invalid weather coordinate region bounds")
        result.append(bounds)
    return tuple(result)


def inside_coordinate_regions(lat: float, lon: float, regions: tuple) -> bool:
    return any(south <= lat <= north and west <= lon <= east
               for south, north, west, east in regions)
