import fcntl
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq

from rainmapper_core.weather_history_contract import (
    CATALOG_SCHEMA,
    CURRENT_SCHEMA_VERSION,
    DATA_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    WEATHER_HISTORY_SCHEMA,
    normalize_mapping,
)
from rainmapper_core.weather_history_dataset import (
    resolve_weather_generation,
    sha256_file,
    write_json_atomic,
)
from rainmapper_core.weather_history_pending import build_pending_batch, list_pending_batches
from rainmapper_core.weather_history_writer import (
    InjectedWeatherHistoryFailure,
    WeatherHistoryCoordinateConflict,
    WeatherHistoryWriterBusy,
    acknowledge_archived_pending,
    archive_pending_batches,
    repair_current_after_restore,
)
from rainmapper_core.weather_history_archive import archive_and_close_pending


class WeatherHistoryWriterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data_dir = Path(self.temporary.name) / "Data"
        self.root = self.data_dir / "weather-history"
        self.root.mkdir(parents=True)
        self._write_initial_generation()

    @staticmethod
    def row(source, station, day, rain, *, name=None, lat=42.0, lon=2.0, altitude=700.0):
        return normalize_mapping(
            {
                "station_code": station,
                "station_name": name or f"Station {station}",
                "local_date": day,
                "rain_mm": rain,
                "lat": lat,
                "lon": lon,
                "altitude": altitude,
            },
            source,
        )

    def _immutable_parquet(self, relative_dir, prefix, table):
        directory = self.root / relative_dir
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / "temporary.parquet"
        pq.write_table(table, temporary, compression="snappy", use_dictionary=False)
        digest = sha256_file(temporary)
        immutable = directory / f"{prefix}-{digest}.parquet"
        temporary.replace(immutable)
        return immutable, digest

    def _write_initial_generation(self):
        partitions = []
        for source, year, rows in (
            (
                "meteocat",
                2025,
                [
                    self.row("meteocat", "A", "20251230", 1.0),
                    self.row("meteocat", "A", "20251231", 2.0),
                ],
            ),
            (
                "wunderground",
                2025,
                [self.row("wunderground", "W", "20251231", 4.0)],
            ),
        ):
            table = pa.Table.from_pylist(rows, schema=WEATHER_HISTORY_SCHEMA)
            path, digest = self._immutable_parquet(
                f"parts/source={source}/year={year}", "data", table
            )
            partitions.append(
                {
                    "source": source,
                    "year": year,
                    "path": path.relative_to(self.root).as_posix(),
                    "sha256": digest,
                    "size_bytes": path.stat().st_size,
                    "rows": len(rows),
                    "min_local_date": rows[0]["local_date"],
                    "max_local_date": rows[-1]["local_date"],
                }
            )
        catalog_rows = [
            {
                "source": "meteocat",
                "station_code": "A",
                "station_name": "Station A",
                "lat": 42.0,
                "lon": 2.0,
                "altitude": 700.0,
                "first_date": "20251230",
                "last_date": "20251231",
                "metadata_date": "20251231",
            },
            {
                "source": "wunderground",
                "station_code": "W",
                "station_name": "Station W",
                "lat": 42.0,
                "lon": 2.0,
                "altitude": 700.0,
                "first_date": "20251231",
                "last_date": "20251231",
                "metadata_date": "20251231",
            },
        ]
        catalog_path, catalog_sha = self._immutable_parquet(
            "catalogs", "stations", pa.Table.from_pylist(catalog_rows, schema=CATALOG_SCHEMA)
        )
        generation_id = "20260812T120000000000Z-initial"
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "generation_id": generation_id,
            "previous_generation_id": None,
            "created_at": "2026-08-12T12:00:00+00:00",
            "data_schema_version": DATA_SCHEMA_VERSION,
            "key": ["source", "station_code", "local_date"],
            "partitions": partitions,
            "catalog": {
                "path": catalog_path.relative_to(self.root).as_posix(),
                "sha256": catalog_sha,
                "size_bytes": catalog_path.stat().st_size,
                "rows": len(catalog_rows),
            },
            "totals": {
                "rows": sum(value["rows"] for value in partitions),
                "size_bytes": sum(value["size_bytes"] for value in partitions)
                + catalog_path.stat().st_size,
            },
            "update_report": {"batch_ids": []},
        }
        manifest_path = self.root / "manifests" / f"{generation_id}.json"
        write_json_atomic(manifest_path, manifest)
        write_json_atomic(
            self.root / "CURRENT.json",
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "generation_id": generation_id,
                "manifest_path": manifest_path.relative_to(self.root).as_posix(),
                "manifest_sha256": sha256_file(manifest_path),
            },
        )
        self.initial_generation_id = generation_id

    def _pending(self, rows, source="meteocat"):
        return build_pending_batch(
            self.data_dir,
            source,
            [rows],
            run_id="test",
            chunk_rows=2,
            row_group_size=2,
        )

    def test_merge_updates_inserts_reuses_untouched_partition_and_updates_catalog(self):
        old = resolve_weather_generation(self.data_dir)
        untouched = next(value for value in old.partitions if value.source == "wunderground")
        pending = self._pending(
            [
                self.row("meteocat", "A", "20251231", None, name="Station A corrected"),
                self.row("meteocat", "A", "20260101", 3.0, name="Station A 2026"),
                self.row("meteocat", "B", "20260101", 5.0, name="Station B"),
            ]
        )
        report = archive_pending_batches(
            self.data_dir,
            row_group_size=2,
            batch_size=2,
            reserve_bytes=0,
        )
        self.assertTrue(report.committed)
        self.assertEqual(report.batch_ids, (pending.batch_id,))
        generation = resolve_weather_generation(self.data_dir, verify_hashes=True)
        self.assertEqual(generation.previous_generation_id, self.initial_generation_id)
        untouched_after = next(value for value in generation.partitions if value.source == "wunderground")
        self.assertEqual(untouched_after.sha256, untouched.sha256)
        partitions = {
            (value.source, value.year): pq.read_table(generation.object_path(value.path)).to_pylist()
            for value in generation.partitions
        }
        corrected = partitions[("meteocat", 2025)][1]
        self.assertEqual(corrected["rain_mm"], 2.0)
        self.assertEqual(corrected["station_name"], "Station A corrected")
        self.assertEqual(len(partitions[("meteocat", 2026)]), 2)
        catalog = pq.read_table(generation.object_path(generation.catalog.path)).to_pylist()
        station_a = next(row for row in catalog if row["station_code"] == "A")
        self.assertEqual(station_a["last_date"], "20260101")
        self.assertEqual(station_a["station_name"], "Station A 2026")
        self.assertEqual(len(list_pending_batches(self.data_dir)), 1)

    def test_receipt_makes_retry_idempotent_and_ack_requires_receipt(self):
        pending = self._pending([self.row("meteocat", "A", "20260101", 3.0)])
        first = archive_pending_batches(self.data_dir, reserve_bytes=0)
        second = archive_pending_batches(self.data_dir, reserve_bytes=0)
        self.assertTrue(first.committed)
        self.assertFalse(second.committed)
        self.assertEqual(second.already_applied_batch_ids, (pending.batch_id,))
        self.assertEqual(second.generation_id, first.generation_id)
        acknowledge_archived_pending(self.data_dir, pending.batch_id)
        self.assertEqual(list_pending_batches(self.data_dir), [])

    def test_failure_before_current_keeps_old_generation_and_retry_succeeds(self):
        self._pending([self.row("meteocat", "A", "20260101", 3.0)])
        with self.assertRaises(InjectedWeatherHistoryFailure):
            archive_pending_batches(self.data_dir, reserve_bytes=0, fail_after="manifest")
        self.assertEqual(
            resolve_weather_generation(self.data_dir).generation_id,
            self.initial_generation_id,
        )
        recovered = archive_pending_batches(self.data_dir, reserve_bytes=0)
        self.assertTrue(recovered.committed)

    def test_failures_after_partitions_or_catalog_leave_current_recoverable(self):
        for stage in ("partitions", "catalog"):
            with self.subTest(stage=stage):
                with tempfile.TemporaryDirectory() as temporary:
                    original_data_dir = self.data_dir
                    original_root = self.root
                    self.data_dir = Path(temporary) / "Data"
                    self.root = self.data_dir / "weather-history"
                    self.root.mkdir(parents=True)
                    self._write_initial_generation()
                    self._pending([self.row("meteocat", "A", "20260101", 3.0)])
                    with self.assertRaises(InjectedWeatherHistoryFailure):
                        archive_pending_batches(
                            self.data_dir,
                            reserve_bytes=0,
                            fail_after=stage,
                        )
                    self.assertEqual(
                        resolve_weather_generation(self.data_dir).generation_id,
                        self.initial_generation_id,
                    )
                    self.assertTrue(archive_pending_batches(self.data_dir, reserve_bytes=0).committed)
                    self.data_dir = original_data_dir
                    self.root = original_root

    def test_failure_after_current_is_recovered_from_receipt_without_second_commit(self):
        pending = self._pending([self.row("meteocat", "A", "20260101", 3.0)])
        with self.assertRaises(InjectedWeatherHistoryFailure):
            archive_pending_batches(self.data_dir, reserve_bytes=0, fail_after="current")
        committed_id = resolve_weather_generation(self.data_dir).generation_id
        recovered = archive_pending_batches(self.data_dir, reserve_bytes=0)
        self.assertFalse(recovered.committed)
        self.assertEqual(recovered.generation_id, committed_id)
        self.assertEqual(recovered.already_applied_batch_ids, (pending.batch_id,))

    def test_coordinate_jump_quarantines_batch_before_current_changes(self):
        self._pending(
            [self.row("meteocat", "A", "20260101", 3.0, lat=43.0, lon=3.0)]
        )
        with self.assertRaises(WeatherHistoryCoordinateConflict):
            archive_pending_batches(self.data_dir, reserve_bytes=0)
        self.assertEqual(resolve_weather_generation(self.data_dir).generation_id, self.initial_generation_id)
        self.assertEqual(len(list_pending_batches(self.data_dir)), 1)

    def test_noop_partition_is_reused_but_receipt_is_committed(self):
        old = resolve_weather_generation(self.data_dir)
        old_partition = next(value for value in old.partitions if value.source == "meteocat")
        pending = self._pending([self.row("meteocat", "A", "20251231", 2.0)])
        report = archive_pending_batches(self.data_dir, reserve_bytes=0)
        self.assertTrue(report.committed)
        self.assertTrue(report.partitions[0].reused)
        new = resolve_weather_generation(self.data_dir)
        new_partition = next(value for value in new.partitions if value.source == "meteocat")
        self.assertEqual(new_partition.sha256, old_partition.sha256)
        acknowledge_archived_pending(self.data_dir, pending.batch_id)

    def test_writer_lock_timeout_does_not_touch_current(self):
        self._pending([self.row("meteocat", "A", "20260101", 3.0)])
        lock_path = self.root / "locks" / "writer.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            with self.assertRaises(WeatherHistoryWriterBusy):
                archive_pending_batches(
                    self.data_dir,
                    reserve_bytes=0,
                    lock_timeout_seconds=0.01,
                )
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        self.assertEqual(resolve_weather_generation(self.data_dir).generation_id, self.initial_generation_id)

    def test_writer_import_does_not_load_pandas(self):
        command = (
            "import sys; import rainmapper_core.weather_history_writer; "
            "assert 'pandas' not in sys.modules"
        )
        subprocess.run([sys.executable, "-c", command], check=True)

    def test_restore_repair_rejects_incomplete_newest_generation(self):
        self._pending([self.row("meteocat", "A", "20260101", 3.0)])
        archive_pending_batches(self.data_dir, reserve_bytes=0)
        newest = resolve_weather_generation(self.data_dir)
        new_partition = next(
            value
            for value in newest.partitions
            if value.source == "meteocat" and value.year == 2026
        )
        new_partition_path = newest.object_path(new_partition.path)
        new_partition_path.unlink()
        dry_run = repair_current_after_restore(self.data_dir)
        self.assertFalse(dry_run.applied)
        self.assertEqual(dry_run.selected_generation_id, self.initial_generation_id)
        self.assertEqual(len(dry_run.rejected_manifests), 1)
        with self.assertRaises(Exception):
            resolve_weather_generation(self.data_dir)
        applied = repair_current_after_restore(self.data_dir, apply=True)
        self.assertTrue(applied.applied)
        self.assertEqual(
            resolve_weather_generation(self.data_dir, verify_hashes=True).generation_id,
            self.initial_generation_id,
        )

    def test_archive_cli_contract_acknowledges_only_after_live_csv_matches(self):
        pending = self._pending([self.row("meteocat", "A", "20260101", 3.0)])
        csv_path = self.data_dir / "Meteocat_incremental.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        row = self.row("meteocat", "A", "20260101", 3.0)
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        with mock.patch.dict(
            "os.environ", {"RAINMAPPER_WEATHER_REFERENCE_DAY": "2026-01-02"}, clear=False
        ):
            report = archive_and_close_pending(self.data_dir)
        self.assertEqual(report["acknowledged_batch_ids"], [pending.batch_id])
        self.assertEqual(list_pending_batches(self.data_dir), [])

    def test_archive_cli_contract_repairs_live_csv_before_acknowledging(self):
        pending = self._pending([self.row("meteocat", "A", "20260101", 3.0)])
        csv_path = self.data_dir / "Meteocat_incremental.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        row = self.row("meteocat", "A", "20260101", 9.0)
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        with mock.patch.dict(
            "os.environ", {"RAINMAPPER_WEATHER_REFERENCE_DAY": "2026-01-02"}, clear=False
        ):
            report = archive_and_close_pending(self.data_dir)
        self.assertEqual(report["acknowledged_batch_ids"], [pending.batch_id])
        self.assertEqual(list_pending_batches(self.data_dir), [])
        with csv_path.open(encoding="utf-8", newline="") as handle:
            repaired = next(csv.DictReader(handle))
        self.assertEqual(repaired["rain_mm"], "3")


if __name__ == "__main__":
    unittest.main()
