import json
import io
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest import mock

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


if __name__ == "__main__":
    unittest.main()
