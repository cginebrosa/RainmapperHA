"""Explicit, guarded catalog-only correction; never rewrites weather readings."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from rainmapper_core.weather_history_contract import CATALOG_SCHEMA, CURRENT_SCHEMA_VERSION
from rainmapper_core.weather_history_dataset import (
    resolve_weather_generation, resolve_weather_manifest, sha256_file,
    weather_history_root, write_json_atomic,
)
from rainmapper_core.weather_history_writer import _writer_lock, _fsync_file, _fsync_directory


def repair_catalog_coordinates(data_dir: Path, plan: dict, *, apply: bool = False) -> dict:
    """Publish one reviewed coordinate correction with immutable objects and backup.

    The plan pins CURRENT and both old and replacement values. Dry run is default.
    Partition descriptors, receipts, station dates and other rows are preserved.
    """
    root = weather_history_root(Path(data_dir))
    with _writer_lock(root, 0):
        current_bytes = (root / "CURRENT.json").read_bytes()
        generation = resolve_weather_generation(root)
        if generation.generation_id != plan["expected_generation_id"]:
            raise ValueError("CURRENT changed: prepare and review a new repair plan")
        catalog_path = generation.object_path(generation.catalog.path)
        if sha256_file(catalog_path) != generation.catalog.sha256:
            raise ValueError("Original catalog hash mismatch")
        original = pq.read_table(catalog_path, schema=CATALOG_SCHEMA).to_pylist()
        rows = [dict(row) for row in original]
        matches = [row for row in rows if (row["source"], row["station_code"]) ==
                   (plan["source"], plan["station_code"])]
        if len(matches) != 1 or len(rows) != generation.catalog.rows:
            raise ValueError("Expected exactly one station and unchanged catalog row count")
        row = matches[0]
        fields = ("lat", "lon", "altitude")
        before = {key: row[key] for key in fields}
        if before != plan["before"]:
            raise ValueError("Station metadata differs from the reviewed before values")
        after = plan["after"]
        if set(after) != set(fields) or not all(math.isfinite(float(after[k])) for k in fields):
            raise ValueError("Expected finite lat, lon and altitude")
        if not (-90 <= float(after["lat"]) <= 90 and -180 <= float(after["lon"]) <= 180):
            raise ValueError("Invalid replacement coordinates")
        if not str(plan.get("reason", "")).strip():
            raise ValueError("A reviewed correction reason is required")
        row.update(after)
        result = {"applied": False, "source_generation_id": generation.generation_id,
                  "source": plan["source"], "station_code": plan["station_code"],
                  "before": before, "after": after, "catalog_rows": len(rows)}
        if not apply or before == after:
            return result

        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup = root.parent / "weather-history-repairs" / stamp
        backup.mkdir(parents=True, exist_ok=False)
        for source in (root / "CURRENT.json", generation.manifest_path, catalog_path):
            target = backup / source.name
            shutil.copyfile(source, target)
            _fsync_file(target)
            if sha256_file(source) != sha256_file(target):
                raise ValueError("Repair backup verification failed")
        write_json_atomic(backup / "plan.json", plan)
        descriptor, temporary_name = tempfile.mkstemp(dir=root / "catalogs", suffix=".parquet")
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            pq.write_table(pa.Table.from_pylist(rows, schema=CATALOG_SCHEMA), temporary,
                           compression="snappy")
            if pq.read_table(temporary, schema=CATALOG_SCHEMA).to_pylist() != rows:
                raise ValueError("Repaired catalog failed readback")
            digest = sha256_file(temporary)
            new_catalog = root / "catalogs" / f"stations-{digest}.parquet"
            if new_catalog.exists():
                if sha256_file(new_catalog) != digest:
                    raise ValueError("Existing immutable catalog hash mismatch")
            else:
                os.replace(temporary, new_catalog)
                _fsync_file(new_catalog)
                _fsync_directory(new_catalog.parent)
        finally:
            temporary.unlink(missing_ok=True)
        manifest = json.loads(generation.manifest_path.read_text())
        generation_id = stamp + "-" + digest[:12]
        manifest.update(generation_id=generation_id,
                        previous_generation_id=generation.generation_id,
                        created_at=datetime.now(UTC).isoformat())
        manifest["catalog"] = {"path": new_catalog.relative_to(root).as_posix(),
                               "sha256": digest, "size_bytes": new_catalog.stat().st_size,
                               "rows": len(rows)}
        manifest["totals"]["size_bytes"] = (
            sum(part["size_bytes"] for part in manifest["partitions"])
            + manifest["catalog"]["size_bytes"]
        )
        manifest.setdefault("update_report", {})["catalog_coordinate_repair"] = plan
        new_manifest = root / "manifests" / f"{generation_id}.json"
        write_json_atomic(new_manifest, manifest)
        resolve_weather_manifest(root, new_manifest, expected_generation_id=generation_id)
        if (root / "CURRENT.json").read_bytes() != current_bytes:
            raise ValueError("CURRENT changed while preparing repair; not activated")
        write_json_atomic(root / "CURRENT.json", {
            "schema_version": CURRENT_SCHEMA_VERSION, "generation_id": generation_id,
            "manifest_path": new_manifest.relative_to(root).as_posix(),
            "manifest_sha256": sha256_file(new_manifest),
        })
        resolved = resolve_weather_generation(root)
        if resolved.generation_id != generation_id:
            raise ValueError("Repaired generation did not become CURRENT")
        result.update(applied=True, generation_id=generation_id,
                      catalog=str(new_catalog), backup=str(backup))
        write_json_atomic(backup / "result.json", result)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(repair_catalog_coordinates(
        args.data_dir, json.loads(args.plan.read_text()), apply=args.apply,
    ), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
