"""Shared station location guard and administrator-reviewed relocations.

Only provider metadata can heal an exception. Replayed, rebuilt or already
corrected weather rows never count as evidence that the provider recovered.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import tempfile
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from rainmapper_core.meteoclimatic_fixed_coordinates import (
    FILENAME as LEGACY_FILE, load_fixed_coordinates,
)
from rainmapper_core.weather_coordinate_policy import inside_coordinate_regions, load_coordinate_regions

STATE_FILE = "weather-coordinate-state.json"
LIMIT_KM = 1.0
MAX_ENTRIES = 4096
MAX_BYTES = 2 * 1024 * 1024
MAX_AUDIT = 200
LOCATION = {"lat": "Latitud", "lon": "Longitud", "altitude": "Altitud",
            "municipality": "Municipi", "province": "Provincia", "county": "Comarca"}
REGISTRIES = {"aemet": "estacions_aemet.csv", "meteocat": "estacions_xema.csv",
              "meteoclimatic": "estacions_meteoclimatic.csv", "wunderground": "estacions_wunderground.csv"}
_THREAD_LOCK = threading.RLock()


def number(value):
    try:
        result = float(str(value).replace(",", "."))
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def point(row):
    if not hasattr(row, "get"):
        return None
    lat, lon = number(row.get("lat")), number(row.get("lon"))
    if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
        return {"lat": lat, "lon": lon}
    return None


def distance(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = math.radians(b["lat"] - a["lat"]), math.radians(b["lon"] - a["lon"])
    v = min(1.0, max(0.0, math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
    return 6371.0088 * 2 * math.atan2(math.sqrt(v), math.sqrt(1 - v))


def station_key(source, code):
    source, code = str(source).lower(), str(code)
    if (not source or not code or len(source) > 80 or len(code) > 80 or ":" in source
            or any(ord(c) < 32 for c in source + code)):
        raise ValueError("Invalid station identity")
    return source + ":" + code


def read_state(data_dir):
    path = Path(data_dir) / STATE_FILE
    if not path.exists():
        return {"schema_version": 1, "exceptions": {}, "accepted_moves": {}, "audit": []}
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Coordinate state exceeds size limit")
    state = json.loads(raw)
    if (state.get("schema_version") != 1 or
            any(not isinstance(state.get(k), dict) or len(state[k]) > MAX_ENTRIES
                for k in ("exceptions", "accepted_moves")) or
            not isinstance(state.get("audit"), list) or len(state["audit"]) > MAX_AUDIT):
        raise ValueError("Invalid coordinate state")
    for key, entry in state["exceptions"].items():
        if (not isinstance(entry, dict) or key != station_key(entry.get("source", ""), entry.get("station_code", ""))
                or not isinstance(entry.get("first_seen"), str)
                or (entry.get("accepted") is not None and not point(entry["accepted"]))
                or (entry.get("received") is not None and not point(entry["received"]))):
            raise ValueError("Invalid coordinate exception")
    if any(not isinstance(value, dict) or not point(value) for value in state["accepted_moves"].values()):
        raise ValueError("Invalid accepted station location")
    return state


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".coordinates-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def transaction(data_dir):
    data_dir = Path(data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    with _THREAD_LOCK, (data_dir / ".weather-coordinates.lock").open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            state = read_state(data_dir)
            before = json.dumps(state, sort_keys=True)
            yield state
            if any(len(state[k]) > MAX_ENTRIES for k in ("exceptions", "accepted_moves")):
                raise ValueError("Too many coordinate exceptions")
            state["audit"] = state["audit"][-MAX_AUDIT:]
            # Bound encoding before assembling the payload.
            chunks, size = [], 0
            for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False, sort_keys=True).iterencode(state):
                encoded = chunk.encode("utf-8")
                size += len(encoded)
                if size > MAX_BYTES:
                    raise ValueError("Coordinate state exceeds size limit")
                chunks.append(encoded)
            if json.dumps(state, sort_keys=True) != before:
                _write(data_dir / STATE_FILE, b"".join(chunks))
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _event(state, kind, entry, **extra):
    run_id = os.environ.get("RAINMAPPER_WEATHER_RUN_ID", "")
    if run_id and kind in {"recovered", "applied"}:
        if state.get("counts_run_id") != run_id:
            state.update(counts_run_id=run_id, run_counts={})
        counts = state.setdefault("run_counts", {})
        counts[entry["source"]] = counts.get(entry["source"], 0) + 1
    state["audit"].append({"event": kind, "source": entry["source"], "station_code": entry["station_code"],
        "at": datetime.now(UTC).isoformat(), "run_id": os.environ.get("RAINMAPPER_WEATHER_RUN_ID", ""),
        **extra})
    del state["audit"][:-MAX_AUDIT]


def _anchors(data_dir, *, use_catalog=True):
    """Read only the small catalog and station registries, never history partitions."""
    result = {}
    for source, filename in REGISTRIES.items():
        path = Path(data_dir) / filename
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    loc = {k: number(row.get(v)) if k in {"lat", "lon", "altitude"} else row.get(v) or None
                           for k, v in LOCATION.items()}
                    if point(loc):
                        result[station_key(source, row["Codi Estació"])] = loc
    root = Path(data_dir) / "weather-history"
    if use_catalog and (root / "CURRENT.json").exists():
        import pyarrow.parquet as pq
        from rainmapper_core.weather_history_dataset import resolve_weather_generation
        generation = resolve_weather_generation(root)
        for row in pq.read_table(root / generation.catalog.path).to_pylist():
            key = station_key(row["source"], row["station_code"])
            if point(row):
                previous = result.get(key, {})
                labels = previous if point(previous) == point(row) else {}
                result[key] = {k: row.get(k, labels.get(k)) for k in LOCATION}
    return result


def _retire_legacy(data_dir, codes):
    """Comment recovered lines, retaining operator comments and all other entries."""
    if not codes:
        return
    path = Path(data_dir).resolve().parent / LEGACY_FILE
    lines = path.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    updated = []
    for line in lines:
        fields = line.partition("#")[0].split()
        updated.append("# recovered automatically: " + line if fields and fields[0] in codes else line)
    _write(path, "".join(updated).encode("utf-8"))


class CoordinatePolicy:
    """Frozen corrections reused for Parquet, catalog and crash-safe CSV replay."""
    def __init__(self, targets=None):
        self.targets = targets or {}

    def contains(self, row):
        return station_key(row["source"], row["station_code"]) in self.targets

    def apply(self, row):
        target = self.targets.get(station_key(row["source"], row["station_code"]))
        if target is None:
            return row
        if point(row) == point(target) and point(target) is not None:
            return row
        return {**row, **{k: target.get(k) for k in LOCATION}}


class Guard:
    def __init__(self, data_dir, state, *, limit_km=LIMIT_KM):
        self.data_dir, self.state, self.limit = Path(data_dir), state, limit_km
        self.anchors = _anchors(data_dir)
        self.regions = load_coordinate_regions(Path(data_dir))
        self.legacy = load_fixed_coordinates(Path(data_dir))
        self.now = datetime.now(UTC).isoformat()
        self.retired = set()
        for key, loc in list(state["accepted_moves"].items()):
            if point(self.anchors.get(key, {})) == point(loc):
                del state["accepted_moves"][key]
        for code, loc in self.legacy.items():
            key = station_key("meteoclimatic", code)
            previous = self.anchors.get(key, {})
            self.anchors[key] = {k: loc.get(k, previous.get(k) if point(previous) == point(loc) else None)
                                 for k in LOCATION}
        for key, loc in state["accepted_moves"].items():
            self.anchors[key] = loc
        for key, entry in state["exceptions"].items():
            if key not in state["accepted_moves"] and not (entry["source"] == "meteoclimatic" and entry["station_code"] in self.legacy):
                if entry.get("accepted"):
                    self.anchors[key] = entry["accepted"]

    def observe(self, row, *, fresh=False, record=True):
        key = station_key(row["source"], row["station_code"])
        accepted, received = self.anchors.get(key), point(row)
        entry = self.state["exceptions"].get(key)
        legacy = row["source"] == "meteoclimatic" and row["station_code"] in self.legacy
        km = distance(accepted, received) if accepted and received else None
        valid = received is not None and (km <= self.limit if km is not None else
                inside_coordinate_regions(received["lat"], received["lon"], self.regions))
        if valid:
            if accepted is None:
                self.anchors[key] = {k: row.get(k) for k in LOCATION}
                self.anchors[key].update(received)
            if entry and entry.get("approval", {}).get("activated"):
                # The catalog/CSV transaction must finish before marking a
                # manually accepted relocation as applied.
                return accepted
            if fresh and (entry or legacy):
                if entry:
                    _event(self.state, "recovered", entry)
                    del self.state["exceptions"][key]
                if legacy:
                    if not entry:
                        _event(self.state, "recovered", row, legacy_age_unknown=True)
                    # Keep the operator's anchor through the next durable archive.
                    self.state["accepted_moves"][key] = accepted
                    self.retired.add(row["station_code"])
            if entry and not fresh:
                return accepted or dict.fromkeys(LOCATION)
            return None
        if not entry and not record:
            return accepted or dict.fromkeys(LOCATION)
        if not entry:
            if len(self.state["exceptions"]) >= MAX_ENTRIES:
                raise ValueError("Too many coordinate exceptions")
            entry = {"source": row["source"], "station_code": row["station_code"],
                     "name": " ".join(str(row.get("station_name") or row["station_code"]).split())[:200],
                     "accepted": accepted, "first_seen": self.now, "legacy_age_unknown": legacy}
            self.state["exceptions"][key] = entry
            _event(self.state, "detected", entry)
        # Archive replay cannot overwrite more recent, raw provider evidence.
        if fresh or "received" not in entry:
            if entry.get("received") != received:
                if entry.get("approval", {}).get("activated"):
                    entry["accepted"] = accepted
                entry.pop("approval", None)
            entry.update(received=received, last_seen=self.now, distance_km=km,
                         reason="coordinate_jump" if received and accepted else "unlocated",
                         evidence="provider" if fresh else "pending")
        return accepted or dict.fromkeys(LOCATION)


def protect_frame(data_dir, source, frame, *, fresh=False, columns=None):
    """Protect a provider frame before any registry write or geocoding.

The adapter must opt into fresh=True ONLY for raw provider location metadata.
Frames reconstructed from a cache/pending must use the default.
"""
    if frame is None or frame.empty:
        return frame
    columns = columns or {**LOCATION, "station_code": "Codi Estació", "station_name": "Estació"}
    if any(columns[k] not in frame for k in ("station_code", "lat", "lon")):
        return frame
    # Only location metadata is materialized, once per station, not all weather.
    small = frame[list(dict.fromkeys(v for v in columns.values() if v in frame))]
    order = next((c for c in ("reading_utc", "Data Lectura", "Ultima Lectura") if c in frame), None)
    if order and order not in small:
        small = small.assign(_coordinate_time=frame[order].astype(str)).sort_values("_coordinate_time")
    small = small.drop_duplicates(columns["station_code"], keep="last")
    targets = {}
    with transaction(data_dir) as state:
        guard = Guard(data_dir, state)
        for raw in small.to_dict("records"):
            row = {k: raw.get(v) for k, v in columns.items()}
            row.update(source=source, station_code=str(row["station_code"]))
            target = guard.observe(row, fresh=fresh, record=fresh)
            if target is not None:
                targets[row["station_code"]] = target
        retired = guard.retired
        anchors = {str(raw[columns["station_code"]]): guard.anchors.get(station_key(source, raw[columns["station_code"]]))
                   for raw in small.to_dict("records")}
    _retire_legacy(data_dir, retired)
    # Older rows in a fresh hourly response are not recovery evidence. Correct
    # their outliers too, even when its latest row has already returned home.
    import numpy as np
    import pandas as pd
    codes = frame[columns["station_code"]].astype(str)
    lat = pd.to_numeric(frame[columns["lat"]].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    lon = pd.to_numeric(frame[columns["lon"]].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    base_lat = codes.map({k: v["lat"] for k, v in anchors.items() if v})
    base_lon = codes.map({k: v["lon"] for k, v in anchors.items() if v})
    hav = np.sin(np.radians(lat - base_lat) / 2) ** 2 + np.cos(np.radians(lat)) * np.cos(np.radians(base_lat)) * np.sin(np.radians(lon - base_lon) / 2) ** 2
    km = 12742.0176 * np.arcsin(np.sqrt(hav.clip(0, 1)))
    outliers = base_lat.notna() & ((km > LIMIT_KM) | ~np.isfinite(lat) | ~np.isfinite(lon)
                                   | (lat.abs() > 90) | (lon.abs() > 180))
    numeric_columns = [columns[k] for k in ("lat", "lon", "altitude") if columns.get(k) in frame]
    normalize_types = any(not pd.api.types.is_numeric_dtype(frame[v]) for v in numeric_columns)
    if not targets and not outliers.any() and not normalize_types:
        return frame
    frame = frame.copy()
    # Provider/CSV metadata can be strings. Mixing those with numeric corrected
    # coordinates breaks Arrow capture; normalize also on an unchanged replay.
    # Weather measurements retain their original values and types.
    for v in numeric_columns:
        frame[v] = pd.to_numeric(frame[v].astype(str).str.replace(",", ".", regex=False), errors="coerce").astype(float)
    if targets or outliers.any():
        # All-empty text metadata can arrive from CSV as float columns. Keep
        # them able to hold an accepted place name or None without dtype coercion.
        for k, v in columns.items():
            if k in LOCATION and v in frame and v not in numeric_columns:
                frame[v] = frame[v].astype(object)
    for k, v in columns.items():
        if k in LOCATION and v in frame and outliers.any():
            replacements = codes.map({code: loc.get(k) for code, loc in anchors.items() if loc})
            if v in numeric_columns:
                replacements = pd.to_numeric(replacements, errors="coerce")
            frame.loc[outliers, v] = replacements.loc[outliers]
    for code, target in targets.items():
        mask = frame[columns["station_code"]].astype(str) == code
        for k, v in columns.items():
            if k in LOCATION and v in frame:
                value = target.get(k)
                if v in numeric_columns:
                    value = number(value)
                    value = float("nan") if value is None else value
                frame.loc[mask, v] = value
    return frame


def activate_approvals(data_dir):
    """Called at a runner boundary; never by the map's HTTP request."""
    retired = set()
    with transaction(data_dir) as state:
        for key, entry in list(state["exceptions"].items()):
            approval = entry.get("approval")
            if not approval or approval.get("activated"):
                continue
            target = {**dict.fromkeys(LOCATION), **approval["target"]}
            state["accepted_moves"][key] = target
            approval["activated"] = True
            _event(state, "activated", entry, accepted=entry.get("accepted"), target=target,
                   username=approval["username"])
            if entry["source"] == "meteoclimatic" and entry["station_code"] in load_fixed_coordinates(Path(data_dir)):
                retired.add(entry["station_code"])
    _retire_legacy(data_dir, retired)


def reconcile_approvals(data_dir, *, require_catalog=True):
    """Finish an activated decision only after its catalog location is durable."""
    if not any(e.get("approval", {}).get("activated") for e in read_state(data_dir)["exceptions"].values()):
        return
    with transaction(data_dir) as state:
        anchors = _anchors(data_dir, use_catalog=require_catalog)
        for key, entry in list(state["exceptions"].items()):
            approval = entry.get("approval", {})
            if approval.get("activated") and point(anchors.get(key)) == point(approval["target"]):
                _event(state, "applied", entry, accepted=entry.get("accepted"), target=approval["target"],
                       username=approval["username"])
                del state["exceptions"][key]
                if require_catalog:
                    state["accepted_moves"].pop(key, None)


def prepare_pending_policy(data_dir, pending, *, limit_km=LIMIT_KM):
    import pyarrow.parquet as pq
    targets = {}
    with transaction(data_dir) as state:
        guard = Guard(data_dir, state, limit_km=limit_km)
        for item in pending:
            for batch in pq.ParquetFile(item.data_path).iter_batches(
                    columns=["source", "station_code", "station_name", *LOCATION]):
                for row in batch.to_pylist():
                    key = station_key(row["source"], row["station_code"])
                    if key in state["accepted_moves"]:
                        targets[key] = state["accepted_moves"][key]
                    else:
                        target = guard.observe(row)
                        if target is not None:
                            targets[key] = target
        # Legacy pins still apply to old queues, including already accepted points.
        for code in guard.legacy:
            key = station_key("meteoclimatic", code)
            targets[key] = guard.anchors[key]
    return CoordinatePolicy(targets)


def revision(entry):
    payload = {k: entry.get(k) for k in ("source", "station_code", "first_seen", "accepted", "received")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def review(data_dir, source, code):
    entry = read_state(data_dir)["exceptions"].get(station_key(source, code))
    if not entry:
        raise LookupError("La incidencia ya no está activa. Actualiza el mapa.")
    return {**entry, "revision": revision(entry), "can_accept": point(entry.get("received") or {}) is not None}


def approve(data_dir, source, code, expected_revision, username):
    with transaction(data_dir) as state:
        entry = state["exceptions"].get(station_key(source, code))
        if not entry or not expected_revision or revision(entry) != expected_revision:
            raise LookupError("La ubicación propuesta ha cambiado. Revisa de nuevo la incidencia.")
        if not point(entry.get("received") or {}):
            raise ValueError("No hay coordenadas válidas que aceptar.")
        if not entry.get("approval"):
            entry["approval"] = {"target": entry["received"], "username": str(username)[:100],
                                 "at": datetime.now(UTC).isoformat()}
            _event(state, "approved", entry, **entry["approval"], accepted=entry.get("accepted"))
        return {"ok": True, "status": "pending", "message": "Traslado aceptado, pendiente del siguiente runner."}


def summary(data_dir, run_id=""):
    state = read_state(data_dir)
    sources = sorted(set(REGISTRIES) | {e["source"] for e in state["exceptions"].values()})
    lines = ["=== Coordenadas: resumen por fuente ==="]
    for source in sources:
        active = [e for e in state["exceptions"].values() if e["source"] == source]
        events = [e for e in state["audit"] if run_id and e["run_id"] == run_id and e["source"] == source
                  and e["event"] in {"recovered", "applied"}]
        count = state.get("run_counts", {}).get(source, 0) if state.get("counts_run_id") == run_id else len(events)
        lines.append(f"{source}: {len(active)} excepciones activas; {count} recuperadas/aceptadas en este run")
        if count > len(events):
            lines.append(f"  Detalle limitado a los últimos {MAX_AUDIT} eventos; el contador incluye todas.")
        for e in sorted(active, key=lambda e: e["station_code"]):
            km = f"{e['distance_km']:.3f} km" if e.get("distance_km") is not None else "sin ubicación aceptada"
            pending = "; aceptación pendiente" if e.get("approval") else ""
            age = "; antigüedad previa desconocida" if e.get("legacy_age_unknown") else ""
            elapsed = max(0, int((datetime.now(UTC) - datetime.fromisoformat(e["first_seen"])).total_seconds()))
            duration = f"{elapsed // 86400}d {(elapsed % 86400) // 3600}h {(elapsed % 3600) // 60}m"
            lines.append(f"  {e['station_code']} ({e['name']}): desde {e['first_seen']} ({duration}){age}; "
                         f"aceptada={point(e.get('accepted') or {})}; recibida={e.get('received')}; {km}{pending}")
        for e in events:
            lines.append(f"  {e['station_code']}: {e['event']} ({e['at']})")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["summary", "activate", "reconcile"])
    parser.add_argument("--data-dir", type=Path, default=Path("Data"))
    args = parser.parse_args()
    if args.action == "activate":
        activate_approvals(args.data_dir)
    elif args.action == "reconcile":
        from rainmapper_core.weather_history_capture import partitioned_history_enabled
        reconcile_approvals(args.data_dir, require_catalog=partitioned_history_enabled())
    else:
        print(summary(args.data_dir, os.environ.get("RAINMAPPER_WEATHER_RUN_ID", "")), end="")


if __name__ == "__main__":
    main()
