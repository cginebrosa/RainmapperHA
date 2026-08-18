import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from rainmapper_core import (
    mushroom_observation_context,
    mushroom_rebuild_comparison,
    mushroom_rebuild_snapshot,
    weather_history_contract,
    weather_history_dataset,
)


class MushroomRebuildSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.weather = self.source / "Data"
        self.weather.mkdir()
        self.gis = self.source / "mushroom-GIS"
        mvc = self.gis / "MVC50mil" / "extracted"
        mvc.mkdir(parents=True)
        for extension in ("shp", "dbf", "shx"):
            (mvc / f"MVC50mil_novembre2019.{extension}").write_text(extension, encoding="utf-8")
        geology = self.gis / "geologia-territorial-50000-geologic-v3r0-202412" / "extracted"
        geology.mkdir(parents=True)
        (geology / "geologia-territorial-50000-geologic-v3r0-202412.gpkg").write_text(
            "geology",
            encoding="utf-8",
        )
        dem = self.gis / "model-elevacions-terreny-topografic-catalunya-5m-2009-2018" / "extracted"
        dem.mkdir(parents=True)
        (dem / "model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif").write_text(
            "dem",
            encoding="utf-8",
        )
        self.observations = self.source / "mushroom_observations.json"
        self.catalogs = self.source / "mushroom_reference_catalogs.json"
        self.mappings = self.source / "mushroom_gis_mappings.json"
        for path in (self.observations, self.catalogs, self.mappings):
            path.write_text("{}", encoding="utf-8")
        (self.weather / "Meteocat_incremental.csv").write_text("header\n", encoding="utf-8")

    def create_snapshot(self) -> Path:
        snapshot = self.root / "snapshot"
        mushroom_rebuild_snapshot.create_snapshot(
            snapshot,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
        )
        return snapshot

    def create_partitioned_weather(self) -> str:
        root = self.weather / "weather-history"
        row = weather_history_contract.normalize_mapping(
            {
                "source": "meteocat",
                "station_code": "X1",
                "station_name": "Test",
                "local_date": "20260808",
                "lat": 42.0,
                "lon": 2.0,
                "altitude": 700.0,
                "rain_mm": 1.0,
            },
            "meteocat",
        )
        frame = pd.DataFrame(
            [row], columns=weather_history_contract.WEATHER_HISTORY_COLUMNS
        )
        part = root / "parts/source=meteocat/year=2026/data.parquet"
        part.parent.mkdir(parents=True)
        pq.write_table(
            pa.Table.from_pandas(
                frame[weather_history_contract.WEATHER_HISTORY_COLUMNS],
                schema=weather_history_contract.WEATHER_HISTORY_SCHEMA,
                preserve_index=False,
            ),
            part,
        )
        part_sha = weather_history_dataset.sha256_file(part)
        immutable_part = part.with_name(f"data-{part_sha}.parquet")
        part.replace(immutable_part)
        catalog = root / "catalogs/catalog.parquet"
        catalog.parent.mkdir(parents=True)
        pd.DataFrame(
            [["meteocat", "X1", "Test", 42.0, 2.0, 700.0, "20260808", "20260808", "20260808"]],
            columns=weather_history_dataset.CATALOG_COLUMNS,
        ).to_parquet(catalog, index=False)
        catalog_sha = weather_history_dataset.sha256_file(catalog)
        immutable_catalog = catalog.with_name(f"stations-{catalog_sha}.parquet")
        catalog.replace(immutable_catalog)
        generation_id = "20260812T120000Z-snapshot"
        manifest = {
            "schema_version": weather_history_dataset.MANIFEST_SCHEMA_VERSION,
            "generation_id": generation_id,
            "previous_generation_id": None,
            "created_at": "2026-08-12T12:00:00+00:00",
            "data_schema_version": weather_history_dataset.DATA_SCHEMA_VERSION,
            "key": ["source", "station_code", "local_date"],
            "partitions": [{
                "source": "meteocat", "year": 2026,
                "path": immutable_part.relative_to(root).as_posix(),
                "sha256": part_sha, "size_bytes": immutable_part.stat().st_size,
                "rows": 1, "min_local_date": "20260808", "max_local_date": "20260808",
            }],
            "catalog": {
                "path": immutable_catalog.relative_to(root).as_posix(),
                "sha256": catalog_sha, "size_bytes": immutable_catalog.stat().st_size,
                "rows": 1,
            },
            "totals": {
                "rows": 1,
                "size_bytes": immutable_part.stat().st_size + immutable_catalog.stat().st_size,
            },
            "update_report": {},
        }
        manifest_path = root / "manifests" / f"{generation_id}.json"
        weather_history_dataset.write_json_atomic(manifest_path, manifest)
        weather_history_dataset.write_json_atomic(
            root / "CURRENT.json",
            {
                "schema_version": weather_history_dataset.CURRENT_SCHEMA_VERSION,
                "generation_id": generation_id,
                "manifest_path": manifest_path.relative_to(root).as_posix(),
                "manifest_sha256": weather_history_dataset.sha256_file(manifest_path),
            },
        )
        return generation_id

    def test_create_and_verify_snapshot(self) -> None:
        snapshot = self.create_snapshot()
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)

        result = mushroom_rebuild_snapshot.verify_snapshot(snapshot)

        self.assertEqual(result["status"], "valid")
        self.assertTrue(str(manifest["snapshot_id"]).startswith("sha256:"))
        self.assertEqual(len(manifest["files"]), 7)
        self.assertEqual((snapshot / manifest["inputs"]["observations"]).read_text(), "{}")
        missing_weather = [row for row in manifest["files"] if row.get("exists") is False]
        self.assertEqual(len(missing_weather), 3)

    def test_snapshot_prefers_weather_parquet_and_live_verification_accepts_it(self) -> None:
        pd.DataFrame(
            [
                {
                    "source": "meteocat",
                    "station_code": "X1",
                    "station_name": "Test",
                    "local_date": "20260808",
                    "lat": 42.0,
                    "lon": 2.0,
                    "rain_mm": 1.0,
                }
            ]
        ).to_parquet(self.weather / "weather_daily.parquet", index=False)

        snapshot = self.create_snapshot()
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)
        weather_records = [
            row for row in manifest["files"] if str(row.get("role", "")).startswith("weather:")
        ]
        live = mushroom_rebuild_snapshot.verify_live_inputs(
            manifest,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
        )

        self.assertEqual(len(manifest["files"]), 4)
        self.assertEqual(len(weather_records), 1)
        self.assertEqual(weather_records[0]["role"], "weather:daily_parquet")
        self.assertEqual(weather_records[0]["path"], "inputs/weather/weather_daily.parquet")
        self.assertFalse(any(str(row.get("path", "")).endswith(".csv") for row in manifest["files"]))
        self.assertEqual(live["status"], "valid")

    def test_snapshot_freezes_and_materializes_partitioned_weather_generation(self) -> None:
        generation_id = self.create_partitioned_weather()
        snapshot = self.create_snapshot()
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)

        self.assertEqual(manifest["weather_history"]["generation_id"], generation_id)
        self.assertEqual(manifest["weather_history"]["partition_count"], 1)
        self.assertFalse(any(
            str(row.get("path", "")).endswith("weather_daily.parquet")
            for row in manifest["files"]
        ))
        self.assertEqual(
            mushroom_rebuild_snapshot.verify_snapshot(snapshot)["status"], "valid"
        )
        live = mushroom_rebuild_snapshot.verify_live_inputs(
            manifest,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
        )
        self.assertEqual(live["status"], "valid")
        runtime = self.root / "partitioned-runtime"
        mushroom_rebuild_snapshot.materialize_ha_test_runtime(snapshot, runtime)
        restored = weather_history_dataset.resolve_weather_generation(
            runtime / "share/Data", verify_hashes=True
        )
        self.assertEqual(restored.generation_id, generation_id)
        with mock.patch.dict("os.environ", {}, clear=True):
            stations = mushroom_observation_context.load_daily_weather_parquet(
                runtime / "share/Data",
                station_filter={("meteocat", "X1")},
                start_date=pd.Timestamp("2026-08-08").date(),
                end_date=pd.Timestamp("2026-08-08").date(),
            )
        self.assertIn(("meteocat", "X1"), stations)

    def test_live_freshness_can_ignore_rebased_derived_extra(self) -> None:
        derived = self.source / "features.json"
        derived.write_text('{"input_paths":{"weather":"/worker/private"}}', encoding="utf-8")
        snapshot = self.root / "snapshot-derived"
        mushroom_rebuild_snapshot.create_snapshot(
            snapshot,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
            extra_inputs={"observation-features.json": derived},
        )
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)
        derived.write_text('{"input_paths":{"weather":"/share/live"}}', encoding="utf-8")

        strict = mushroom_rebuild_snapshot.verify_live_inputs(
            manifest,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
            extra_inputs={"observation-features.json": derived},
        )
        freshness = mushroom_rebuild_snapshot.verify_live_inputs(
            manifest,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
            extra_inputs={"observation-features.json": derived},
            ignored_extra_inputs={"observation-features.json"},
        )

        self.assertEqual(strict["status"], "stale")
        self.assertEqual(freshness["status"], "valid")

    def test_live_freshness_can_use_partitioned_generation_identity(self) -> None:
        self.create_partitioned_weather()
        snapshot = self.create_snapshot()
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)
        original = mushroom_rebuild_snapshot._stable_file_record
        hashed_roles: list[str] = []

        def record_hash(path: Path, *, logical_path: str, role: str):
            hashed_roles.append(role)
            return original(path, logical_path=logical_path, role=role)

        with mock.patch.object(
            mushroom_rebuild_snapshot,
            "_stable_file_record",
            side_effect=record_hash,
        ):
            result = mushroom_rebuild_snapshot.verify_live_inputs(
                manifest,
                observations_path=self.observations,
                reference_catalogs_path=self.catalogs,
                gis_mappings_path=self.mappings,
                weather_data_dir=self.weather,
                gis_root=self.gis,
                verify_weather_file_hashes=False,
            )

        self.assertEqual(result["status"], "valid")
        self.assertFalse(any(role.startswith("weather-history:") for role in hashed_roles))

    def test_snapshot_rejects_partitioned_history_for_incompatible_worker(self) -> None:
        self.create_partitioned_weather()
        snapshot = self.root / "snapshot-incompatible-worker"

        with self.assertRaisesRegex(ValueError, "partitioned_weather_history_v1"):
            mushroom_rebuild_snapshot.create_snapshot(
                snapshot,
                observations_path=self.observations,
                reference_catalogs_path=self.catalogs,
                gis_mappings_path=self.mappings,
                weather_data_dir=self.weather,
                gis_root=self.gis,
                prefer_weather_parquet=True,
                allow_partitioned_weather_history=False,
            )

        self.assertFalse(snapshot.exists())

    def test_snapshot_uses_csv_fallback_for_worker_without_parquet_capability(self) -> None:
        pd.DataFrame(
            [{"source": "meteocat", "station_code": "X1", "local_date": "20260808"}]
        ).to_parquet(self.weather / "weather_daily.parquet", index=False)
        snapshot = self.root / "snapshot-csv-compatibility"

        mushroom_rebuild_snapshot.create_snapshot(
            snapshot,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
            prefer_weather_parquet=False,
        )
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)

        self.assertTrue(any(str(row.get("path", "")).endswith(".csv") for row in manifest["files"]))
        self.assertFalse(
            any(str(row.get("path", "")).endswith("weather_daily.parquet") for row in manifest["files"])
        )

    def test_verify_detects_changed_snapshot_file(self) -> None:
        snapshot = self.create_snapshot()
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)
        (snapshot / manifest["inputs"]["observations"]).write_text("changed", encoding="utf-8")

        result = mushroom_rebuild_snapshot.verify_snapshot(snapshot)

        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("snapshot" in error for error in result["errors"]))

    def test_snapshot_paths_cannot_escape_the_snapshot_or_gis_roots(self) -> None:
        snapshot = self.create_snapshot()
        manifest_path = snapshot / mushroom_rebuild_snapshot.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][0]["path"] = "../outside.json"
        manifest["inputs"]["observations"] = "../outside.json"
        manifest["datasets"][0]["files"][0]["path"] = "../outside.dat"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = mushroom_rebuild_snapshot.verify_snapshot(snapshot)

        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("unsafe snapshot file path" in error for error in result["errors"]))
        self.assertTrue(any("unsafe GIS file path" in error for error in result["errors"]))
        with self.assertRaisesRegex(ValueError, "unsafe snapshot input observations path"):
            mushroom_rebuild_snapshot.resolved_input_paths(snapshot, manifest)

    def test_verify_detects_manifest_identity_tampering(self) -> None:
        snapshot = self.create_snapshot()
        manifest_path = snapshot / mushroom_rebuild_snapshot.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["snapshot_id"] = "sha256:" + "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = mushroom_rebuild_snapshot.verify_snapshot(snapshot)

        self.assertEqual(result["status"], "invalid")
        self.assertIn("snapshot manifest fingerprint mismatch", result["errors"])

    def test_invalid_manifest_records_are_reported_without_reading_outside_roots(self) -> None:
        snapshot = self.create_snapshot()
        manifest_path = snapshot / mushroom_rebuild_snapshot.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"].append("invalid")
        manifest["datasets"][0]["files"][0]["path"] = "../outside.dat"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        snapshot_result = mushroom_rebuild_snapshot.verify_snapshot(snapshot)
        live_result = mushroom_rebuild_snapshot.verify_live_inputs(
            manifest,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
        )

        self.assertEqual(snapshot_result["status"], "invalid")
        self.assertIn("invalid snapshot file record", snapshot_result["errors"])
        self.assertEqual(live_result["status"], "stale")
        self.assertTrue(any("unsafe live GIS file path" in error for error in live_result["errors"]))

    def test_shallow_gis_validation_checks_sizes_without_rehashing(self) -> None:
        snapshot = self.create_snapshot()
        gis_file = mushroom_rebuild_snapshot.gis_dataset_files(self.gis)[0]
        original = gis_file.read_bytes()
        gis_file.write_bytes(b"x" * len(original))

        shallow = mushroom_rebuild_snapshot.verify_snapshot(
            snapshot,
            verify_gis_file_hashes=False,
        )
        deep = mushroom_rebuild_snapshot.verify_snapshot(snapshot)

        self.assertEqual(shallow["status"], "valid")
        self.assertEqual(shallow["gis_validation"], "shallow")
        self.assertEqual(deep["status"], "invalid")

    def test_gis_dataset_files_includes_optional_andorra_dem(self) -> None:
        andorra_dem = (
            self.gis
            / "dem-andorra"
            / "extracted"
            / "rainmapper-dem-andorra-5m-elevation-m-epsg27563.tif"
        )
        andorra_dem.parent.mkdir(parents=True)
        andorra_dem.write_text("andorra-dem", encoding="utf-8")

        paths = mushroom_rebuild_snapshot.gis_dataset_files(self.gis)

        self.assertIn(andorra_dem.resolve(), paths)

    def test_gis_dataset_files_includes_optional_ign_mtn50_592_dem(self) -> None:
        ign_dem = (
            self.gis
            / "dem-ign-mtn50-592"
            / "extracted"
            / "PNOA_MDT25_ETRS89_HU30_0592_LID.tif"
        )
        ign_dem.parent.mkdir(parents=True)
        ign_dem.write_text("ign-dem", encoding="utf-8")

        paths = mushroom_rebuild_snapshot.gis_dataset_files(self.gis)

        self.assertIn(ign_dem.resolve(), paths)

    def test_gis_hash_cache_reuses_unchanged_semi_static_files(self) -> None:
        cache_path = self.root / "private" / ".gis-hash-cache.json"
        original_sha256_file = mushroom_rebuild_snapshot.sha256_file
        hashed_gis_paths: list[Path] = []

        def tracked_sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
            resolved = path.resolve()
            if self.gis.resolve() in resolved.parents:
                hashed_gis_paths.append(resolved)
            return original_sha256_file(path, chunk_size)

        with mock.patch.object(
            mushroom_rebuild_snapshot,
            "sha256_file",
            side_effect=tracked_sha256_file,
        ):
            first = self.root / "snapshot-cached-first"
            mushroom_rebuild_snapshot.create_snapshot(
                first,
                observations_path=self.observations,
                reference_catalogs_path=self.catalogs,
                gis_mappings_path=self.mappings,
                weather_data_dir=self.weather,
                gis_root=self.gis,
                gis_hash_cache_path=cache_path,
            )
            first_hash_count = len(hashed_gis_paths)
            second = self.root / "snapshot-cached-second"
            mushroom_rebuild_snapshot.create_snapshot(
                second,
                observations_path=self.observations,
                reference_catalogs_path=self.catalogs,
                gis_mappings_path=self.mappings,
                weather_data_dir=self.weather,
                gis_root=self.gis,
                gis_hash_cache_path=cache_path,
            )
            self.assertEqual(len(hashed_gis_paths), first_hash_count)
            changed_gis_path = hashed_gis_paths[0]
            original_content = changed_gis_path.read_bytes()
            changed_gis_path.write_bytes(
                bytes([original_content[0] ^ 1]) + original_content[1:]
            )
            third = self.root / "snapshot-cached-after-gis-change"
            mushroom_rebuild_snapshot.create_snapshot(
                third,
                observations_path=self.observations,
                reference_catalogs_path=self.catalogs,
                gis_mappings_path=self.mappings,
                weather_data_dir=self.weather,
                gis_root=self.gis,
                gis_hash_cache_path=cache_path,
            )

        self.assertGreater(first_hash_count, 0)
        self.assertEqual(len(hashed_gis_paths), first_hash_count + 1)
        self.assertTrue(cache_path.is_file())
        cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertNotIn(str(self.gis.resolve()), cache_path.read_text(encoding="utf-8"))
        self.assertEqual(cache_payload["kind"], "rainmapper_gis_hash_cache")

    def test_live_verification_reuses_gis_hash_cache_and_rehashes_changes(self) -> None:
        snapshot = self.root / "snapshot-live-cache"
        cache_path = self.root / "private" / ".gis-hash-cache.json"
        manifest = mushroom_rebuild_snapshot.create_snapshot(
            snapshot,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
            gis_hash_cache_path=cache_path,
        )
        original_sha256_file = mushroom_rebuild_snapshot.sha256_file
        hashed_gis_paths: list[Path] = []

        def tracked_sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
            resolved = path.resolve()
            if self.gis.resolve() in resolved.parents:
                hashed_gis_paths.append(resolved)
            return original_sha256_file(path, chunk_size)

        with mock.patch.object(
            mushroom_rebuild_snapshot,
            "sha256_file",
            side_effect=tracked_sha256_file,
        ):
            unchanged = mushroom_rebuild_snapshot.verify_live_inputs(
                manifest,
                observations_path=self.observations,
                reference_catalogs_path=self.catalogs,
                gis_mappings_path=self.mappings,
                weather_data_dir=self.weather,
                gis_root=self.gis,
                gis_hash_cache_path=cache_path,
            )
            self.assertEqual(hashed_gis_paths, [])

            changed_gis = mushroom_rebuild_snapshot.gis_dataset_files(self.gis)[0]
            original = changed_gis.read_bytes()
            changed_gis.write_bytes(b"x" * len(original))
            changed = mushroom_rebuild_snapshot.verify_live_inputs(
                manifest,
                observations_path=self.observations,
                reference_catalogs_path=self.catalogs,
                gis_mappings_path=self.mappings,
                weather_data_dir=self.weather,
                gis_root=self.gis,
                gis_hash_cache_path=cache_path,
            )

        self.assertEqual(unchanged["status"], "valid")
        self.assertEqual(unchanged["gis_validation"], "identity-cache")
        self.assertIn(changed_gis.resolve(), hashed_gis_paths)
        self.assertEqual(changed["status"], "stale")

    def test_live_inputs_match_frozen_manifest(self) -> None:
        snapshot = self.create_snapshot()
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)
        progress: list[tuple[int, int, str]] = []

        result = mushroom_rebuild_snapshot.verify_live_inputs(
            manifest,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
            progress_callback=lambda completed, total, path: progress.append(
                (completed, total, path)
            ),
        )

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["current_snapshot_id"], manifest["snapshot_id"])
        self.assertTrue(progress)
        self.assertEqual(progress[-1][0], progress[-1][1])
        self.assertGreater(progress[-1][1], 1)

    def test_live_inputs_detect_change_after_snapshot(self) -> None:
        snapshot = self.create_snapshot()
        manifest = mushroom_rebuild_snapshot.load_manifest(snapshot)
        self.observations.write_text('{"changed": true}', encoding="utf-8")

        result = mushroom_rebuild_snapshot.verify_live_inputs(
            manifest,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
        )

        self.assertEqual(result["status"], "stale")
        self.assertTrue(any("observations" in error for error in result["errors"]))

    def test_materialize_ha_test_runtime_uses_only_snapshot_inputs(self) -> None:
        snapshot = self.create_snapshot()
        runtime = self.root / "ha-runtime"

        result = mushroom_rebuild_snapshot.materialize_ha_test_runtime(snapshot, runtime)

        self.assertEqual(result["status"], "materialized")
        self.assertTrue((runtime / ".rainmapper-rebuild-test-runtime.json").is_file())
        self.assertEqual(
            (runtime / "share/mushroom-data/mushroom_observations.json").read_text(),
            "{}",
        )
        self.assertEqual(
            (runtime / "share/Data/Meteocat_incremental.csv").read_text(),
            "header\n",
        )
        self.assertFalse((runtime / "share/Data/Aemet_incremental.csv").exists())
        self.assertTrue((runtime / "share/rebuild_test_input_manifest.json").is_file())


class MushroomRebuildComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.reference = self.root / "reference"
        self.candidate = self.root / "candidate"
        for directory in (self.reference, self.candidate):
            (directory / "reports").mkdir(parents=True)
        self.write_artifacts()

    def write_artifacts(self) -> None:
        gis_reference = {
            "generated_at": "old",
            "qgis_points_path": "/old/qgis.geojson",
            "qgis_points_host_path": "/host/old/qgis.geojson",
            "results": [{"layers": {"dem_5m": {"status": "no_value", "raw": "", "source": "/old/dem"}}}],
        }
        gis_candidate = {
            "generated_at": "new",
            "qgis_points_path": "/new/qgis.geojson",
            "qgis_points_host_path": "/host/new/qgis.geojson",
            "results": [
                {
                    "layers": {
                        "dem_5m": {
                            "status": "no_data",
                            "elevation_m": -9999.0,
                            "source": "/new/dem",
                        }
                    }
                }
            ],
        }
        for name in mushroom_rebuild_comparison.JSON_ARTIFACTS:
            if name == "mushroom_gis_observation_reconstruction.json":
                left, right = gis_reference, gis_candidate
            else:
                left = {
                    "generated_at": "old",
                    "input_paths": {"input": "/old"},
                    "output_paths": {"output": "/old"},
                    "prediction_target_policy": {"catalog_path": "/old", "version": "v1"},
                    "rows": [{"value": 1}],
                }
                right = {
                    "generated_at": "new",
                    "input_paths": {"input": "/new"},
                    "output_paths": {"output": "/new"},
                    "prediction_target_policy": {"catalog_path": "/new", "version": "v1"},
                    "rows": [{"value": 1}],
                }
            (self.reference / name).write_text(json.dumps(left), encoding="utf-8")
            (self.candidate / name).write_text(json.dumps(right), encoding="utf-8")
        for name in mushroom_rebuild_comparison.CSV_ARTIFACTS:
            (self.reference / name).write_text("same\n", encoding="utf-8")
            (self.candidate / name).write_text("same\n", encoding="utf-8")
        for name in mushroom_rebuild_comparison.REPORT_ARTIFACTS:
            (self.reference / name).write_text("# Report\n\n- Generated at: old\n- Count: 1\n", encoding="utf-8")
            (self.candidate / name).write_text("# Report\n\n- Generated at: new\n- Count: 1\n", encoding="utf-8")

    def test_comparison_normalizes_only_expected_metadata(self) -> None:
        result = mushroom_rebuild_comparison.compare_artifact_dirs(self.reference, self.candidate)

        self.assertEqual(result["status"], "equivalent")

    def test_comparison_detects_domain_difference(self) -> None:
        path = self.candidate / "mushroom_model_v0.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["rows"][0]["value"] = 2
        path.write_text(json.dumps(payload), encoding="utf-8")

        result = mushroom_rebuild_comparison.compare_artifact_dirs(self.reference, self.candidate)

        self.assertEqual(result["status"], "different")
        model = next(item for item in result["artifacts"] if item["path"] == path.name)
        self.assertEqual(model["difference_paths"], ["/rows/0/value"])


if __name__ == "__main__":
    unittest.main()
