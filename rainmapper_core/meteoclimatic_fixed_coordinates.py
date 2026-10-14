"""Operator-managed Meteoclimatic locations, independent of provider metadata."""
from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

FILENAME = "meteoclimatic-fixed-coordinates.txt"
MAX_FILE_BYTES = 64 * 1024
MAX_STATIONS = 512
LOCATION_FIELDS = ("altitude", "municipality", "province", "county")


def _number(value):
    try:
        result = float(str(value).replace(",", "."))
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def load_fixed_coordinates(data_dir: Path) -> dict[str, dict]:
    """Read once per operation, beside the physical Data directory (also symlinks)."""
    path = Path(data_dir).resolve().parent / FILENAME
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        content = handle.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise ValueError(f"{path}: exceeds {MAX_FILE_BYTES} bytes")
    result = {}
    for number, raw in enumerate(content.decode("utf-8-sig").splitlines(), 1):
        fields = raw.partition("#")[0].split()
        if not fields:
            continue
        error = f"{path}:{number}: expected unique station_code latitude longitude (decimal degrees)"
        if len(fields) != 3 or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", fields[0]):
            raise ValueError(error)
        code, lat, lon = fields[0], _number(fields[1]), _number(fields[2])
        if code in result or lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(error)
        if len(result) >= MAX_STATIONS:
            raise ValueError(f"{path}:{number}: exceeds {MAX_STATIONS} stations")
        result[code] = {"lat": lat, "lon": lon}
    return result


def _same_location(row, target, lat="lat", lon="lon"):
    return (_number(row.get(lat)), _number(row.get(lon))) == (target["lat"], target["lon"])


def location_metadata(data_dir: Path, coordinates: dict, catalog_rows=()) -> dict:
    """Reuse metadata only at the pinned location; never relabel a foreign altitude.

    Unknown administrative labels remain null until normal source enrichment.
    No network call or historical partition scan is required to unblock a queue.
    """
    targets = {code: {**value, **dict.fromkeys(LOCATION_FIELDS)} for code, value in coordinates.items()}
    for row in catalog_rows:
        code = row.get("station_code")
        if row.get("source") == "meteoclimatic" and code in targets and _same_location(row, targets[code]):
            targets[code]["altitude"] = row.get("altitude")
    path = Path(data_dir) / "estacions_meteoclimatic.csv"
    if targets and path.exists():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                code = row.get("Codi Estació")
                if code in targets and _same_location(row, targets[code], "Latitud", "Longitud"):
                    targets[code].update(
                        altitude=_number(row.get("Altitud")),
                        municipality=row.get("Municipi") or None,
                        province=row.get("Provincia") or None,
                        county=row.get("Comarca") or None,
                    )
    return targets


class FixedCoordinates:
    """Small immutable-per-operation policy; logging is bounded by station count."""

    def __init__(self, targets=None, *, log=True):
        self.targets = targets or {}
        self.log = log
        self._logged = set()

    def contains(self, row):
        return row.get("source") == "meteoclimatic" and row.get("station_code") in self.targets

    def _report(self, code, old_lat, old_lon, target):
        if self.log and code not in self._logged:
            print(f"Meteoclimatic {code}: coordinates received {old_lat}, {old_lon} -> "
                  f"used {target['lat']}, {target['lon']} ({FILENAME})", file=sys.stderr)
            self._logged.add(code)

    def apply(self, row):
        if not self.contains(row):
            return row
        code = row["station_code"]
        target = self.targets[code]
        if _same_location(row, target):
            return row
        self._report(code, row.get("lat"), row.get("lon"), target)
        corrected = dict(row)
        corrected.update(lat=target["lat"], lon=target["lon"])
        for field in LOCATION_FIELDS:
            corrected[field] = target.get(field)
        return corrected

    def apply_frame(self, frame):
        """Override fresh coordinates BEFORE the existing metadata enrichment."""
        if not self.targets or frame.empty:
            return frame
        frame = frame.copy()
        for code, target in self.targets.items():
            mask = frame["Codi Estació"] == code
            if not mask.any():
                continue
            row = frame.loc[mask].iloc[0]
            if not _same_location(row, target, "Latitud", "Longitud"):
                self._report(code, row["Latitud"], row["Longitud"], target)
            frame.loc[mask, "Latitud"] = target["lat"]
            frame.loc[mask, "Longitud"] = target["lon"]
        return frame
