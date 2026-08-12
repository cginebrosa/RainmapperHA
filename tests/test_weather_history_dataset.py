import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from rainmapper_core import weather_history_contract, weather_history_dataset
from rainmapper_core import mushroom_observation_context, tomap


class WeatherHistoryDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name) / "Data"
        self.root = self.data_dir / "weather-history"
        self.root.mkdir(parents=True)
        self.generation_id = "20260812T120000Z-test"
        self._write_generation()

    def _row(self, source, station, day, rain):
        row = weather_history_contract.normalize_mapping(
            {
                "source": source,
                "station_code": station,
                "station_name": f"Station {station}",
                "local_date": day,
                "lat": 42.0,
                "lon": 2.0,
                "altitude": 700.0,
                "rain_mm": rain,
            },
            source,
        )
        return pd.DataFrame(
            [row], columns=weather_history_contract.WEATHER_HISTORY_COLUMNS
        )

    def _write_generation(self):
        partitions = []
        for source, year, rows in (
            (
                "meteocat",
                2025,
                [
                    self._row("meteocat", "A", "20251231", 1.0),
                    self._row("meteocat", "B", "20251231", 2.0),
                ],
            ),
            ("meteocat", 2026, [self._row("meteocat", "A", "20260101", 3.0)]),
            ("wunderground", 2026, [self._row("wunderground", "W", "20260101", 4.0)]),
        ):
            frame = pd.concat(rows, ignore_index=True)
            path = self.root / f"parts/source={source}/year={year}/data.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pandas(
                frame[weather_history_contract.WEATHER_HISTORY_COLUMNS],
                schema=weather_history_contract.WEATHER_HISTORY_SCHEMA,
                preserve_index=False,
            )
            pq.write_table(table, path, compression="snappy")
            digest = weather_history_dataset.sha256_file(path)
            immutable = path.with_name(f"data-{digest}.parquet")
            path.replace(immutable)
            partitions.append(
                {
                    "source": source,
                    "year": year,
                    "path": immutable.relative_to(self.root).as_posix(),
                    "sha256": digest,
                    "size_bytes": immutable.stat().st_size,
                    "rows": len(frame),
                    "min_local_date": frame["local_date"].min(),
                    "max_local_date": frame["local_date"].max(),
                }
            )
        catalog = pd.DataFrame(
            [
                ["meteocat", "A", "Station A", 42.0, 2.0, 700.0, "20251231", "20260101", "20260101"],
                ["meteocat", "B", "Station B", 42.0, 2.0, 700.0, "20251231", "20251231", "20251231"],
                ["wunderground", "W", "Station W", 42.0, 2.0, 700.0, "20260101", "20260101", "20260101"],
            ],
            columns=weather_history_dataset.CATALOG_COLUMNS,
        )
        catalog_path = self.root / "catalogs/catalog.parquet"
        catalog_path.parent.mkdir(parents=True)
        catalog.to_parquet(catalog_path, index=False)
        catalog_digest = weather_history_dataset.sha256_file(catalog_path)
        immutable_catalog = catalog_path.with_name(f"stations-{catalog_digest}.parquet")
        catalog_path.replace(immutable_catalog)
        manifest = {
            "schema_version": weather_history_dataset.MANIFEST_SCHEMA_VERSION,
            "generation_id": self.generation_id,
            "previous_generation_id": None,
            "created_at": "2026-08-12T12:00:00+00:00",
            "data_schema_version": weather_history_dataset.DATA_SCHEMA_VERSION,
            "key": ["source", "station_code", "local_date"],
            "partitions": partitions,
            "catalog": {
                "path": immutable_catalog.relative_to(self.root).as_posix(),
                "sha256": catalog_digest,
                "size_bytes": immutable_catalog.stat().st_size,
                "rows": len(catalog),
            },
            "totals": {
                "rows": sum(item["rows"] for item in partitions),
                "size_bytes": sum(item["size_bytes"] for item in partitions)
                + immutable_catalog.stat().st_size,
            },
            "update_report": {},
        }
        manifest_path = self.root / "manifests" / f"{self.generation_id}.json"
        weather_history_dataset.write_json_atomic(manifest_path, manifest)
        weather_history_dataset.write_json_atomic(
            self.root / "CURRENT.json",
            {
                "schema_version": weather_history_dataset.CURRENT_SCHEMA_VERSION,
                "generation_id": self.generation_id,
                "manifest_path": manifest_path.relative_to(self.root).as_posix(),
                "manifest_sha256": weather_history_dataset.sha256_file(manifest_path),
            },
        )

    def test_resolve_validates_complete_generation_and_hashes(self):
        generation = weather_history_dataset.resolve_weather_generation(
            self.data_dir,
            verify_hashes=True,
        )
        self.assertEqual(generation.generation_id, self.generation_id)
        self.assertEqual(len(generation.partitions), 3)
        self.assertEqual(generation.cache_identity[0], self.generation_id)

    def test_bounded_reader_crosses_year_and_filters_station(self):
        result = weather_history_dataset.read_weather_history(
            self.data_dir,
            columns=["source", "station_code", "local_date", "rain_mm"],
            station_filter={("meteocat", "A")},
            start_date="20251231",
            end_date="20260101",
        )
        self.assertEqual(result["local_date"].tolist(), ["20251231", "20260101"])
        self.assertEqual(result["rain_mm"].tolist(), [1.0, 3.0])

    def test_tomap_reads_partitioned_generation_across_year_boundary(self):
        with mock.patch.dict(
            "os.environ", {"RAINMAPPER_PARTITIONED_WEATHER_HISTORY": "true"}
        ):
            result = tomap.read_weather_daily_parquet(
                self.data_dir,
                include_aemet=False,
                base_date=datetime(2026, 1, 1),
                days_backward=1,
                days_forward=0,
            )
        self.assertEqual(len(result), 4)
        self.assertEqual(set(result["Data Local"].dt.strftime("%Y%m%d")), {"20251231", "20260101"})
        self.assertEqual(result.attrs["weather_input"], "partitioned weather history")

    def test_predictor_loader_and_catalog_use_generation_identity(self):
        with mock.patch.dict(
            "os.environ", {"RAINMAPPER_PARTITIONED_WEATHER_HISTORY": "true"}
        ):
            catalog = mushroom_observation_context.load_stations_catalog(self.data_dir)
            identity = mushroom_observation_context.weather_history_cache_identity(self.data_dir)
            stations = mushroom_observation_context.load_daily_weather_parquet(
                self.data_dir,
                station_filter={("meteocat", "A")},
                start_date=datetime(2025, 12, 31).date(),
                end_date=datetime(2026, 1, 1).date(),
            )
        self.assertEqual(identity[0], self.generation_id)
        self.assertEqual(len(catalog), 3)
        self.assertEqual(set(stations[("meteocat", "A")].records_by_day), {
            datetime(2025, 12, 31).date(), datetime(2026, 1, 1).date()
        })

    def test_partitioned_predictor_loader_rejects_unbounded_dataframe_read(self):
        with mock.patch.dict(
            "os.environ", {"RAINMAPPER_PARTITIONED_WEATHER_HISTORY": "true"}
        ):
            with self.assertRaisesRegex(
                mushroom_observation_context.WeatherParquetLayoutError,
                "bounded",
            ):
                mushroom_observation_context.load_daily_weather_parquet(self.data_dir)

    def test_dataframe_reader_rejects_unbounded_request(self):
        with self.assertRaisesRegex(ValueError, "Unbounded"):
            weather_history_dataset.read_weather_history(self.data_dir)

    def test_reader_rejects_unknown_source_and_inverted_range(self):
        with self.assertRaisesRegex(ValueError, "Unknown weather sources"):
            weather_history_dataset.read_weather_history(
                self.data_dir,
                sources={"unknown"},
            )
        with self.assertRaisesRegex(ValueError, "must not be after"):
            weather_history_dataset.read_weather_history(
                self.data_dir,
                start_date="20260102",
                end_date="20260101",
            )

    def test_iterator_allows_explicit_unbounded_stream(self):
        rows = sum(
            batch.num_rows
            for batch in weather_history_dataset.iter_weather_history(
                self.data_dir,
                columns=["source", "station_code", "local_date"],
                batch_size=1,
            )
        )
        self.assertEqual(rows, 4)

    def test_pin_creates_and_removes_lease(self):
        with weather_history_dataset.pin_weather_generation(self.data_dir) as generation:
            leases = list((self.root / "leases" / generation.generation_id).glob("*.json"))
            self.assertEqual(len(leases), 1)
        self.assertEqual(list((self.root / "leases").rglob("*.json")), [])

    def test_manifest_path_traversal_is_rejected(self):
        current_path = self.root / "CURRENT.json"
        current = json.loads(current_path.read_text())
        current["manifest_path"] = "../outside.json"
        weather_history_dataset.write_json_atomic(current_path, current)
        with self.assertRaisesRegex(weather_history_dataset.WeatherHistoryManifestError, "Unsafe"):
            weather_history_dataset.resolve_weather_generation(self.data_dir)

    def test_unsorted_partition_manifest_is_rejected(self):
        current = json.loads((self.root / "CURRENT.json").read_text())
        manifest_path = self.root / current["manifest_path"]
        manifest = json.loads(manifest_path.read_text())
        manifest["partitions"] = list(reversed(manifest["partitions"]))
        weather_history_dataset.write_json_atomic(manifest_path, manifest)
        current["manifest_sha256"] = weather_history_dataset.sha256_file(manifest_path)
        weather_history_dataset.write_json_atomic(self.root / "CURRENT.json", current)
        with self.assertRaisesRegex(
            weather_history_dataset.WeatherHistoryManifestError,
            "unique and sorted",
        ):
            weather_history_dataset.resolve_weather_generation(self.data_dir)

    def test_wrong_object_size_is_rejected_without_hash_scan(self):
        current = json.loads((self.root / "CURRENT.json").read_text())
        manifest_path = self.root / current["manifest_path"]
        manifest = json.loads(manifest_path.read_text())
        manifest["partitions"][0]["size_bytes"] += 1
        manifest["totals"]["size_bytes"] += 1
        weather_history_dataset.write_json_atomic(manifest_path, manifest)
        current["manifest_sha256"] = weather_history_dataset.sha256_file(manifest_path)
        weather_history_dataset.write_json_atomic(self.root / "CURRENT.json", current)
        with self.assertRaisesRegex(
            weather_history_dataset.WeatherHistoryIntegrityError,
            "size mismatch",
        ):
            weather_history_dataset.resolve_weather_generation(self.data_dir)

    def test_corrupt_partition_is_rejected_by_exhaustive_validation(self):
        generation = weather_history_dataset.resolve_weather_generation(self.data_dir)
        partition_path = generation.object_path(generation.partitions[0].path)
        data = bytearray(partition_path.read_bytes())
        data[len(data) // 2] ^= 1
        partition_path.write_bytes(data)
        with self.assertRaisesRegex(weather_history_dataset.WeatherHistoryIntegrityError, "SHA"):
            weather_history_dataset.resolve_weather_generation(
                self.data_dir,
                verify_hashes=True,
            )


if __name__ == "__main__":
    unittest.main()
