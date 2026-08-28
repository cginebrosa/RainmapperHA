import json
import io
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest import mock

import pandas as pd

from rainmapper_core import mushroom_observation_context
from rainmapper_core import mushroom_rebuild_snapshot
from rainmapper_core import mushroom_worker_dataset_cache
from rainmapper_core import mushroom_worker_transport


class MushroomWorkerTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.weather = self.source / "Data"
        self.weather.mkdir()
        self.gis = self.source / "mushroom-GIS"
        mvc = self.gis / "MVC50mil/extracted"
        mvc.mkdir(parents=True)
        for extension in ("shp", "dbf", "shx"):
            (mvc / f"MVC50mil_novembre2019.{extension}").write_text(extension, encoding="utf-8")
        geology = self.gis / "geologia-territorial-50000-geologic-v3r0-202412/extracted"
        geology.mkdir(parents=True)
        (geology / "geologia-territorial-50000-geologic-v3r0-202412.gpkg").write_text(
            "geology", encoding="utf-8"
        )
        dem = self.gis / "model-elevacions-terreny-topografic-catalunya-5m-2009-2018/extracted"
        dem.mkdir(parents=True)
        (dem / "model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif").write_text(
            "dem", encoding="utf-8"
        )
        self.observations = self.source / "mushroom_observations.json"
        self.catalogs = self.source / "mushroom_reference_catalogs.json"
        self.mappings = self.source / "mushroom_gis_mappings.json"
        self.observations.write_text(
            json.dumps(
                {
                    "observations": [
                        {
                            "observation_id": "obs_transport_1",
                            "validation_status": "valid",
                            "calibration_use": "include",
                            "location": {"lat": 42.0, "lon": 2.0},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.catalogs.write_text("{}", encoding="utf-8")
        self.mappings.write_text("{}", encoding="utf-8")
        (self.weather / "Meteocat_incremental.csv").write_text("date,value\n2026-07-19,1\n", encoding="utf-8")
        pd.DataFrame(
            [
                {
                    "source": "meteocat",
                    "station_code": "X1",
                    "station_name": "Test station",
                    "local_date": "20260808",
                    "lat": 42.0,
                    "lon": 2.0,
                    "rain_mm": 1.5,
                }
            ]
        ).to_parquet(self.weather / "weather_daily.parquet", index=False)
        self.bundle_root = self.root / "coordinator-bundles"
        self.job_id = "worker_job_transport123"
        self.metadata = mushroom_worker_transport.prepare_coordinator_bundle(
            self.bundle_root,
            job_id=self.job_id,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
        )
        self.worker_data = self.root / "worker-data"
        manifest = mushroom_rebuild_snapshot.load_manifest(
            self.bundle_root / self.job_id / "snapshot"
        )
        mushroom_worker_dataset_cache.sync_local(manifest, self.gis, self.worker_data)

    def test_coordinator_bundle_can_carry_small_hashed_extra_inputs(self) -> None:
        registry = self.source / "registry.json"
        registry.write_text('{"versions": []}\n', encoding="utf-8")
        job_id = "worker_job_transportextra"

        metadata = mushroom_worker_transport.prepare_coordinator_bundle(
            self.bundle_root,
            job_id=job_id,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
            extra_inputs={"registry.json": registry},
        )
        manifest = mushroom_rebuild_snapshot.load_manifest(
            self.bundle_root / job_id / "snapshot"
        )
        record = next(row for row in manifest["files"] if row["role"] == "extra:registry.json")

        self.assertEqual(record["path"], "inputs/extra/registry.json")
        self.assertEqual(
            record["sha256"],
            hashlib.sha256(registry.read_bytes()).hexdigest(),
        )
        self.assertEqual(metadata["input_file_count"], len(manifest["files"]))

    def test_complete_multiversion_bundle_is_discardable(self) -> None:
        self.assertTrue(
            mushroom_worker_transport.coordinator_bundle_is_discardable(
                {"status": "complete", "job_type": "worker_ml_multiversion_v1"}
            )
        )

    def test_worker_downloads_and_verifies_immutable_bundle_over_http(self) -> None:
        seen_headers: list[tuple[str, str, str]] = []

        class Response(io.BytesIO):
            def __init__(self, content: bytes):
                super().__init__(content)
                self.headers = {"Content-Length": str(len(content))}

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                self.close()

        def open_input(request, timeout: float):
            parsed = urlparse(request.full_url)
            query = parse_qs(parsed.query)
            logical_path = (query.get("file") or [""])[0]
            seen_headers.append(
                (
                    request.get_header("Authorization", ""),
                    request.get_header("X-rainmapper-worker", ""),
                    request.get_header("X-rainmapper-claim", ""),
                )
            )
            path = mushroom_worker_transport.resolve_coordinator_file(
                self.bundle_root,
                (query.get("job_id") or [""])[0],
                logical_path,
            )
            return Response(path.read_bytes())

        progress: list[dict[str, object]] = []
        job = {
            "job_id": self.job_id,
            "input_bundle": {
                **self.metadata,
                "endpoint": "/api/mushrooms/workers/jobs/input",
            },
        }

        with mock.patch.object(mushroom_worker_transport, "urlopen", side_effect=open_input):
            result = mushroom_worker_transport.download_input_bundle(
                "http://rainmapper-ha-ui:8099",
                job,
                self.worker_data,
                worker_id="worker_12345678",
                claim_token="claim-secret",
                token="coordinator-secret",
                progress_callback=progress.append,
            )

        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["snapshot_id"], self.metadata["snapshot_id"])
        self.assertEqual(result["input_file_count"], self.metadata["input_file_count"])
        self.assertTrue((self.worker_data / "jobs" / self.job_id / "job_spec.json").is_file())
        downloaded_weather = self.worker_data / "jobs" / self.job_id / "snapshot" / "inputs" / "weather"
        self.assertTrue((downloaded_weather / "weather_daily.parquet").is_file())
        self.assertFalse((downloaded_weather / "Meteocat_incremental.csv").exists())
        stations = mushroom_observation_context.load_daily_weather_parquet(downloaded_weather)
        self.assertIn(("meteocat", "X1"), stations)
        self.assertTrue(progress)
        self.assertTrue(all(row == ("Bearer coordinator-secret", "worker_12345678", "claim-secret") for row in seen_headers))

        reused = mushroom_worker_transport.download_input_bundle(
            "http://rainmapper-ha-ui:8099",
            job,
            self.worker_data,
            worker_id="worker_12345678",
            claim_token="claim-secret",
            token="coordinator-secret",
        )
        self.assertEqual(reused["status"], "reused")

    def test_partitioned_weather_objects_are_reused_by_hash(self) -> None:
        content = b"immutable partition bytes"
        digest = hashlib.sha256(content).hexdigest()

        class Response(io.BytesIO):
            def __init__(self):
                super().__init__(content)
                self.headers = {"Content-Length": str(len(content))}

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                self.close()

        first = self.root / "first.parquet"
        second = self.root / "second.parquet"
        with mock.patch.object(
            mushroom_worker_transport, "urlopen", side_effect=lambda *_args, **_kwargs: Response()
        ) as urlopen:
            first_reused = mushroom_worker_transport._materialize_cached_weather_input(
                "http://rainmapper/input",
                first,
                worker_data_dir=self.worker_data,
                digest=digest,
                size=len(content),
                headers={},
                timeout=1.0,
            )
            second_reused = mushroom_worker_transport._materialize_cached_weather_input(
                "http://rainmapper/input",
                second,
                worker_data_dir=self.worker_data,
                digest=digest,
                size=len(content),
                headers={},
                timeout=1.0,
            )

        self.assertFalse(first_reused)
        self.assertTrue(second_reused)
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(first.read_bytes(), content)
        self.assertEqual(second.read_bytes(), content)

    def test_immutable_input_receipt_reuses_object_without_network_or_rehash(self) -> None:
        content = b"sealed chained input"
        digest = hashlib.sha256(content).hexdigest()

        class Response(io.BytesIO):
            def __init__(self):
                super().__init__(content)
                self.headers = {"Content-Length": str(len(content))}

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                self.close()

        first = self.root / "first-input.json"
        second = self.root / "second-input.json"
        with mock.patch.object(
            mushroom_worker_transport,
            "urlopen",
            side_effect=lambda *_args, **_kwargs: Response(),
        ) as urlopen:
            first_reused = (
                mushroom_worker_transport._materialize_cached_immutable_input(
                    "http://rainmapper/input",
                    first,
                    worker_data_dir=self.worker_data,
                    digest=digest,
                    size=len(content),
                    headers={},
                    timeout=1.0,
                )
            )
            with mock.patch.object(
                mushroom_worker_transport.mushroom_rebuild_snapshot,
                "sha256_file",
                side_effect=AssertionError("sealed objects must not be rehashed"),
            ):
                second_reused = (
                    mushroom_worker_transport._materialize_cached_immutable_input(
                        "http://rainmapper/input",
                        second,
                        worker_data_dir=self.worker_data,
                        digest=digest,
                        size=len(content),
                        headers={},
                        timeout=1.0,
                    )
                )

        self.assertFalse(first_reused)
        self.assertTrue(second_reused)
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(first.read_bytes(), content)
        self.assertEqual(second.read_bytes(), content)

    def test_worker_downloads_missing_gis_dataset_transactionally_over_http(self) -> None:
        seen_dataset_requests: list[tuple[str, str, str]] = []

        class Response(io.BytesIO):
            def __init__(self, content: bytes):
                super().__init__(content)
                self.headers = {"Content-Length": str(len(content))}

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                self.close()

        def open_request(request, timeout: float):
            parsed = urlparse(request.full_url)
            query = parse_qs(parsed.query)
            if parsed.path.endswith("/dataset"):
                seen_dataset_requests.append(
                    (
                        request.get_header("Authorization", ""),
                        request.get_header("X-rainmapper-worker", ""),
                        request.get_header("X-rainmapper-claim", ""),
                    )
                )
                path = mushroom_worker_transport.resolve_coordinator_dataset_file(
                    self.bundle_root,
                    self.gis,
                    job_id=(query.get("job_id") or [""])[0],
                    dataset_id=(query.get("dataset_id") or [""])[0],
                    fingerprint=(query.get("fingerprint") or [""])[0],
                    logical_path=(query.get("file") or [""])[0],
                )
            else:
                path = mushroom_worker_transport.resolve_coordinator_file(
                    self.bundle_root,
                    (query.get("job_id") or [""])[0],
                    (query.get("file") or [""])[0],
                )
            return Response(path.read_bytes())

        empty_worker_data = self.root / "empty-worker-data"
        job = {
            "job_id": self.job_id,
            "input_bundle": {
                **self.metadata,
                "endpoint": "/api/mushrooms/workers/jobs/input",
                "dataset_endpoint": "/api/mushrooms/workers/jobs/dataset",
            },
        }
        progress: list[dict[str, object]] = []
        with mock.patch.object(mushroom_worker_transport, "urlopen", side_effect=open_request):
            result = mushroom_worker_transport.download_input_bundle(
                "http://rainmapper-ha-ui:8099",
                job,
                empty_worker_data,
                worker_id="worker_12345678",
                claim_token="claim-secret",
                token="coordinator-secret",
                progress_callback=progress.append,
            )

        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["dataset_cache_status"], "synchronized")
        self.assertEqual(
            result["dataset_transferred_size_bytes"],
            self.metadata["dataset_size_bytes"],
        )
        self.assertEqual(len(seen_dataset_requests), self.metadata["dataset_file_count"])
        self.assertTrue(
            all(
                row == ("Bearer coordinator-secret", "worker_12345678", "claim-secret")
                for row in seen_dataset_requests
            )
        )
        self.assertTrue(any(row.get("phase") == "Synchronizing GIS dataset" for row in progress))
        self.assertEqual(
            mushroom_worker_dataset_cache.verify_version(empty_worker_data, deep=True)["status"],
            "valid",
        )

    def test_coordinator_only_serves_manifest_declared_paths(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsafe"):
            mushroom_worker_transport.resolve_coordinator_file(
                self.bundle_root,
                self.job_id,
                "../mushroom_observations.json",
            )
        with self.assertRaisesRegex(ValueError, "not part"):
            mushroom_worker_transport.resolve_coordinator_file(
                self.bundle_root,
                self.job_id,
                "snapshot/private.json",
            )
        dataset = mushroom_worker_transport.resolve_coordinator_dataset_file(
            self.bundle_root,
            self.gis,
            job_id=self.job_id,
            dataset_id=str(self.metadata["dataset_id"]),
            fingerprint=str(self.metadata["dataset_fingerprint"]),
            logical_path="MVC50mil/extracted/MVC50mil_novembre2019.shp",
        )
        self.assertEqual(dataset.read_text(encoding="utf-8"), "shp")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            mushroom_worker_transport.resolve_coordinator_dataset_file(
                self.bundle_root,
                self.gis,
                job_id=self.job_id,
                dataset_id=str(self.metadata["dataset_id"]),
                fingerprint="sha256:" + "0" * 64,
                logical_path="MVC50mil/extracted/MVC50mil_novembre2019.shp",
            )
        with self.assertRaisesRegex(ValueError, "not declared"):
            mushroom_worker_transport.resolve_coordinator_dataset_file(
                self.bundle_root,
                self.gis,
                job_id=self.job_id,
                dataset_id=str(self.metadata["dataset_id"]),
                fingerprint=str(self.metadata["dataset_fingerprint"]),
                logical_path="private.dat",
            )

    def test_discard_removes_job_copies_but_preserves_shared_dataset_cache(self) -> None:
        worker_job = self.worker_data / "jobs" / self.job_id
        worker_job.mkdir(parents=True)
        (worker_job / "job_spec.json").write_bytes(
            (self.bundle_root / self.job_id / "job_spec.json").read_bytes()
        )
        (worker_job / "candidate").mkdir()
        (worker_job / "candidate" / "result.json").write_text("{}", encoding="utf-8")
        dataset_before = mushroom_worker_dataset_cache.verify_version(
            self.worker_data,
            deep=True,
        )

        self.assertTrue(
            mushroom_worker_transport.discard_coordinator_bundle(
                self.bundle_root,
                self.job_id,
            )
        )
        self.assertTrue(
            mushroom_worker_transport.discard_worker_job(
                self.worker_data,
                self.job_id,
            )
        )

        self.assertFalse((self.bundle_root / self.job_id).exists())
        self.assertFalse(worker_job.exists())
        self.assertEqual(
            mushroom_worker_dataset_cache.verify_version(self.worker_data, deep=True)["fingerprint"],
            dataset_before["fingerprint"],
        )

    def test_discard_accepts_identity_checked_ml_job_spec(self) -> None:
        ml_job_id = "worker_job_mlcleanup123"
        worker_job = self.worker_data / "jobs" / ml_job_id
        worker_job.mkdir(parents=True)
        (worker_job / "job_spec.json").write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "kind": "mushroom_ml_train_v0_spec",
                    "job_id": ml_job_id,
                }
            ),
            encoding="utf-8",
        )

        removed = mushroom_worker_transport.discard_worker_job(
            self.worker_data,
            ml_job_id,
        )

        self.assertTrue(removed)
        self.assertFalse(worker_job.exists())

    def test_cleanup_reconciles_only_discardable_old_storage(self) -> None:
        def prepare(job_id: str) -> None:
            mushroom_worker_transport.prepare_coordinator_bundle(
                self.bundle_root,
                job_id=job_id,
                observations_path=self.observations,
                reference_catalogs_path=self.catalogs,
                gis_mappings_path=self.mappings,
                weather_data_dir=self.weather,
                gis_root=self.gis,
            )

        retained_candidate = "worker_job_candidate123"
        retained_active = "worker_job_running12345"
        failed = "worker_job_failed123456"
        promoted = "worker_job_promoted1234"
        old_orphan = "worker_job_orphanold123"
        recent_orphan = "worker_job_orphannew123"
        for job_id in (
            retained_candidate,
            retained_active,
            failed,
            promoted,
            old_orphan,
            recent_orphan,
        ):
            prepare(job_id)

        now = 100_000.0
        os.utime(self.bundle_root / old_orphan, (0, 0))
        os.utime(self.bundle_root / recent_orphan, (now, now))
        stale_staging = self.bundle_root / (
            ".worker_job_stale12345.staging-" + "a" * 32
        )
        recent_staging = self.bundle_root / (
            ".worker_job_recent1234.staging-" + "b" * 32
        )
        stale_staging.mkdir()
        recent_staging.mkdir()
        os.utime(stale_staging, (0, 0))
        os.utime(recent_staging, (now, now))
        jobs = [
            {
                "job_id": self.job_id,
                "job_type": "worker_snapshot_transport_probe",
                "status": "complete",
            },
            {
                "job_id": retained_candidate,
                "job_type": "worker_candidate_rebuild",
                "status": "complete",
                "promotion_status": "pending",
            },
            {
                "job_id": retained_active,
                "job_type": "worker_candidate_rebuild",
                "status": "running",
            },
            {
                "job_id": failed,
                "job_type": "worker_candidate_rebuild",
                "status": "failed",
            },
            {
                "job_id": promoted,
                "job_type": "worker_candidate_rebuild",
                "status": "complete",
                "promotion_status": "promoted",
            },
        ]

        dry_run = mushroom_worker_transport.cleanup_coordinator_bundles(
            self.bundle_root,
            jobs,
            now=now,
            staging_grace_seconds=60,
            orphan_grace_seconds=60,
            apply=False,
        )
        self.assertCountEqual(
            dry_run["planned_terminal"],
            [self.job_id, failed, promoted],
        )
        self.assertEqual(dry_run["planned_orphan"], [old_orphan])
        self.assertEqual(dry_run["planned_staging"], [stale_staging.name])
        self.assertEqual(dry_run["discarded_terminal"], [])
        self.assertTrue((self.bundle_root / self.job_id).is_dir())
        self.assertTrue((self.bundle_root / old_orphan).is_dir())
        self.assertTrue(stale_staging.is_dir())

        report = mushroom_worker_transport.cleanup_coordinator_bundles(
            self.bundle_root,
            jobs,
            now=now,
            staging_grace_seconds=60,
            orphan_grace_seconds=60,
        )

        self.assertCountEqual(
            report["discarded_terminal"],
            [self.job_id, failed, promoted],
        )
        self.assertEqual(report["discarded_orphan"], [old_orphan])
        self.assertEqual(report["discarded_staging"], [stale_staging.name])
        self.assertTrue((self.bundle_root / retained_candidate).is_dir())
        self.assertTrue((self.bundle_root / retained_active).is_dir())
        self.assertTrue((self.bundle_root / recent_orphan).is_dir())
        self.assertTrue(recent_staging.is_dir())
        self.assertTrue((self.bundle_root / ".gis-hash-cache.json").is_file())
        self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
