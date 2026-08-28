import hashlib
import io
import json
import shutil
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_benchmark_reports as benchmark_reports
from rainmapper_core import mushroom_ml_multiversion_plan
from rainmapper_core import mushroom_ml_multiversion_transport as transport
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"
REVISION_VECTOR = {
    "observations_revision": "sha256:observations",
    "weather_generation_id": "weather-generation",
    "weather_manifest_sha256": "sha256:weather",
    "sites_revision": "sha256:sites",
    "stations_revision": "sha256:stations",
    "catalogs_revision": "sha256:catalogs",
    "gis_revision": "sha256:gis",
    "training_contract_version": "registry-2.0",
}


class MushroomMLMultiversionTransportTests(TestCase):

    def test_operational_result_stays_staged_until_explicit_install(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        active_version = "altitude_v2"
        plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id="batch-operational-transport",
            snapshot_id="sha256:" + "d" * 64,
            generation_ids={active_version: "generation-operational"},
            species_ids=["boletus_edulis"],
            version_ids=[active_version],
        )
        samples = [
            {
                "sample_id": f"sample-{index}",
                "prediction_target": "favorable" if index % 2 else "unfavorable",
                "predictive_features": {"test_feature": float(index)},
                "quality": {"training_eligible": True},
                "metadata": {
                    "species_id": "boletus_edulis",
                    "area_id": "area-a",
                    "target_date": f"2025-02-{index + 1:02d}",
                },
            }
            for index in range(20)
        ]
        benchmark = {
            "feature_set": {"predictive_feature_cols": ["test_feature"]},
            "samples": samples,
        }
        benchmarks = {
            trainer.benchmark_key(active_version, contract, "common_idw"): benchmark
            for contract in ("fixed_gap_7d_altitude_v2", "lag_event_altitude_v2")
        }
        job_id = "worker_job_operationaltransport"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch_dir, batch_manifest = trainer.write_batch(
                registry, plan, benchmarks, models_root=root / "produced"
            )
            self.assertEqual(0, batch_manifest["failed_fit_count"])
            batch_manifest["job_purpose"] = "operational"
            batch_manifest["operational_candidate_trained"] = True
            batch_manifest["operational_scope_id"] = "sha256:" + "a" * 64
            batch_manifest["operational_plan_id"] = "sha256:" + "b" * 64
            batch_manifest["input_revisions"] = REVISION_VECTOR
            quality_path = batch_dir / "quality-catalog.json"
            quality_path.write_text("{}", encoding="utf-8")
            batch_manifest["quality_catalog"] = {
                "path": f"batches/{batch_manifest['batch_id']}/quality-catalog.json",
                "sha256": hashlib.sha256(quality_path.read_bytes()).hexdigest(),
            }
            training_input_path = batch_dir / "training-input-manifest.json"
            training_input_path.write_text(
                json.dumps({"snapshot_id": batch_manifest["snapshot_id"]}),
                encoding="utf-8",
            )
            batch_manifest["training_input_manifest"] = {
                "path": (
                    f"batches/{batch_manifest['batch_id']}/"
                    "training-input-manifest.json"
                ),
                "sha256": hashlib.sha256(training_input_path.read_bytes()).hexdigest(),
            }
            (batch_dir / "manifest.json").write_text(
                json.dumps(batch_manifest), encoding="utf-8"
            )
            upload = root / "upload"
            shutil.copytree(batch_dir, upload / "batch")
            declared = []
            for path in sorted((upload / "batch").rglob("*")):
                if path.is_file():
                    content = path.read_bytes()
                    declared.append(
                        {
                            "path": path.relative_to(upload).as_posix(),
                            "size_bytes": len(content),
                            "sha256": hashlib.sha256(content).hexdigest(),
                        }
                    )
            result = {
                "schema_version": "1.0",
                "kind": "mushroom_ml_multiversion_result",
                "job_id": job_id,
                "batch_id": batch_manifest["batch_id"],
                "snapshot_id": batch_manifest["snapshot_id"],
                "files": declared,
                "batch_manifest_sha256": trainer.sha256(upload / "batch" / "manifest.json"),
                "planned_fit_count": batch_manifest["planned_fit_count"],
                "successful_fit_count": batch_manifest["successful_fit_count"],
                "failed_fit_count": 0,
                "job_purpose": "operational",
                "operational_candidate_trained": True,
                "operational_scope_id": batch_manifest["operational_scope_id"],
                "operational_plan_id": batch_manifest["operational_plan_id"],
            }
            staging = root / "staging"
            transport.receive_result_file(
                staging,
                job_id=job_id,
                logical_path=transport.RESULT_MANIFEST_NAME,
                content=json.dumps(result).encode(),
            )
            reused_manifest = transport.receive_result_file(
                staging,
                job_id=job_id,
                logical_path=transport.RESULT_MANIFEST_NAME,
                content=json.dumps(result).encode(),
            )
            self.assertEqual("reused", reused_manifest["status"])
            invalid_stream = io.BytesIO()
            with tarfile.open(fileobj=invalid_stream, mode="w") as archive:
                payload = b"undeclared"
                info = tarfile.TarInfo("batch/undeclared.bin")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
            with self.assertRaisesRegex(ValueError, "invalid member"):
                transport.receive_result_bundle(
                    staging,
                    job_id=job_id,
                    content=invalid_stream.getvalue(),
                )

            wrong_size_stream = io.BytesIO()
            with tarfile.open(fileobj=wrong_size_stream, mode="w") as archive:
                payload = (upload / declared[0]["path"]).read_bytes() + b"extra"
                info = tarfile.TarInfo(declared[0]["path"])
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
            with self.assertRaisesRegex(ValueError, "expanded size"):
                transport.receive_result_bundle(
                    staging,
                    job_id=job_id,
                    content=wrong_size_stream.getvalue(),
                )

            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as archive:
                for record in declared:
                    archive.add(upload / record["path"], arcname=record["path"])
            bundled = transport.receive_result_bundle(
                staging,
                job_id=job_id,
                content=stream.getvalue(),
            )
            self.assertEqual(len(declared), bundled["file_count"])
            reused_bundle = transport.receive_result_bundle(
                staging,
                job_id=job_id,
                content=stream.getvalue(),
            )
            self.assertEqual(len(declared), reused_bundle["file_count"])
            models = root / "installed"
            with mock.patch.object(
                transport,
                "sha256",
                side_effect=AssertionError("received files must not be rehashed"),
            ):
                verified = transport.finalize_result(
                    staging,
                    job_id=job_id,
                    registry_path=REGISTRY_PATH,
                    models_root=models,
                    job_purpose="operational",
                )
            self.assertEqual("verified", verified["status"])
            self.assertFalse((models / "runtime-batch.json").exists())
            self.assertTrue((staging / job_id / "multiversion").is_dir())

            with mock.patch.object(
                transport,
                "sha256",
                side_effect=AssertionError("received files must not be rehashed"),
            ):
                installed = transport.install_staged_operational_result(
                    staging,
                    job_id=job_id,
                    registry_path=REGISTRY_PATH,
                    models_root=models,
                )
            self.assertEqual("verified_batch_installed", installed["status"])
            self.assertFalse((models / "runtime-batch.json").exists())
            self.assertTrue(
                (models / "batches" / batch_manifest["batch_id"] / "manifest.json").is_file()
            )

    def test_benchmark_result_is_archived_without_changing_runtime(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        artifact_ref = catalog.ModelArtifactRef(
            batch_id="batch-transport",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
        )
        plan = {
            "batch_id": "batch-transport",
            "snapshot_id": "sha256:" + "a" * 64,
            "version_ids": ["biology_v3"],
            "profile_keys": ["biology_v3/core"],
            "species_ids": ["boletus_edulis"],
            "fit_count": 1,
            "fits": [{"artifact_ref": artifact_ref.as_dict(), "supported_horizons": [7]}],
        }
        samples = [
            {
                "sample_id": f"sample-{index}",
                "prediction_target": "favorable" if index % 2 else "unfavorable",
                "predictive_features": {"test_feature": float(index)},
                "quality": {"training_eligible": True},
                "metadata": {
                    "species_id": "boletus_edulis",
                    "area_id": "area-a",
                    "target_date": f"2025-01-{index + 1:02d}",
                },
            }
            for index in range(20)
        ]
        benchmark = {
            "feature_set": {"predictive_feature_cols": ["test_feature"]},
            "samples": samples,
        }
        key = trainer.benchmark_key("biology_v3", "fixed_gap_7d_biology_v3", "core")
        job_id = "worker_job_transport1234"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            produced_root = root / "produced"
            batch_dir, batch_manifest = trainer.write_batch(
                registry, plan, {key: benchmark}, models_root=produced_root
            )
            predictions = root / "holdout-source.jsonl"
            predictions.write_text(
                json.dumps(
                    {
                        "version_id": "biology_v3",
                        "profile_id": "core",
                        "species_id": "boletus_edulis",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            empty_predictions = root / "holdout-empty.jsonl"
            empty_predictions.write_text("", encoding="utf-8")
            report_bundle = benchmark_reports.write_report(
                batch_dir,
                job_id=job_id,
                training_plan=plan,
                selected_profiles=[
                    {
                        "profile_key": "biology_v3/core",
                        "version_id": "biology_v3",
                        "profile_id": "core",
                    }
                ],
                quality_catalog={"entries": []},
                fit_results=batch_manifest["fit_results"],
                failed_fits=batch_manifest["failed_fits"],
                v2_v5_predictions_path=predictions,
                v6_predictions_path=empty_predictions,
                created_at="2026-08-18T12:00:00+00:00",
            )
            report = report_bundle["report"]
            quality_path = batch_dir / "quality-catalog.json"
            quality_path.write_text(json.dumps({"entries": []}), encoding="utf-8")
            training_input_path = batch_dir / "training-input-manifest.json"
            training_input_path.write_text(
                json.dumps({"snapshot_id": batch_manifest["snapshot_id"]}),
                encoding="utf-8",
            )
            batch_manifest["job_purpose"] = "benchmark"
            batch_manifest["operational_candidate_trained"] = False
            batch_manifest["benchmark_report"] = {
                "path": f"batches/{batch_manifest['batch_id']}/{benchmark_reports.REPORT_NAME}",
                "sha256": trainer.sha256(report_bundle["report_path"]),
                "report_id": report["report_id"],
            }
            batch_manifest["holdout_predictions"] = {
                **dict(report["holdout_predictions"]),
                "path": (
                    f"batches/{batch_manifest['batch_id']}/"
                    f"{benchmark_reports.PREDICTIONS_NAME}"
                ),
            }
            batch_manifest["quality_catalog"] = {
                "path": f"batches/{batch_manifest['batch_id']}/quality-catalog.json",
                "sha256": trainer.sha256(quality_path),
            }
            batch_manifest["training_input_manifest"] = {
                "path": (
                    f"batches/{batch_manifest['batch_id']}/"
                    "training-input-manifest.json"
                ),
                "sha256": trainer.sha256(training_input_path),
            }
            (batch_dir / "manifest.json").write_text(
                json.dumps(batch_manifest), encoding="utf-8"
            )
            upload_source = root / "upload-source"
            shutil.copytree(batch_dir, upload_source / "batch")
            declared = []
            for path in sorted((upload_source / "batch").rglob("*")):
                if path.is_file():
                    content = path.read_bytes()
                    declared.append(
                        {
                            "path": path.relative_to(upload_source).as_posix(),
                            "size_bytes": len(content),
                            "sha256": hashlib.sha256(content).hexdigest(),
                        }
                    )
            result = {
                "schema_version": "1.0",
                "kind": "mushroom_ml_multiversion_result",
                "job_id": job_id,
                "batch_id": batch_manifest["batch_id"],
                "snapshot_id": batch_manifest["snapshot_id"],
                "files": declared,
                "batch_manifest_sha256": trainer.sha256(upload_source / "batch" / "manifest.json"),
                "planned_fit_count": 1,
                "successful_fit_count": 1,
                "failed_fit_count": 0,
                "job_purpose": "benchmark",
                "operational_candidate_trained": False,
                "report_id": report["report_id"],
            }
            result_bytes = (json.dumps(result) + "\n").encode()
            staging_root = root / "staging"
            transport.receive_result_file(
                staging_root,
                job_id=job_id,
                logical_path=transport.RESULT_MANIFEST_NAME,
                content=result_bytes,
            )
            for record in declared:
                transport.receive_result_file(
                    staging_root,
                    job_id=job_id,
                    logical_path=record["path"],
                    content=(upload_source / record["path"]).read_bytes(),
                )
            models_root = root / "installed"
            verification = transport.finalize_result(
                staging_root,
                job_id=job_id,
                registry_path=REGISTRY_PATH,
                models_root=models_root,
                job_purpose="benchmark",
            )

            self.assertEqual(verification["status"], "verified_and_archived")
            self.assertFalse(verification["operational_candidate_trained"])
            self.assertEqual(1, verification["summary"]["profile_count"])
            self.assertEqual(1, verification["summary"]["successful_fit_count"])
            self.assertEqual(
                ["biology_v3/core"], verification["selection"]["profile_keys"]
            )
            self.assertFalse((models_root / "runtime-batch.json").exists())
            benchmark_root = models_root / "benchmarks" / "batch-transport"
            self.assertFalse((benchmark_root / "manifest.json").exists())
            self.assertTrue(
                (benchmark_root / benchmark_reports.EVIDENCE_MANIFEST_NAME).is_file()
            )
            self.assertEqual("evidence_only", verification["storage_state"])
            self.assertFalse((staging_root / job_id / "multiversion").exists())

    def test_failed_finalization_keeps_staged_result_for_diagnosis(self) -> None:
        job_id = "worker_job_transportfailed"
        result = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_multiversion_result",
            "job_id": job_id,
            "batch_id": "batch-failed",
            "snapshot_id": "sha256:" + "a" * 64,
            "files": [
                {
                    "path": "batch/manifest.json",
                    "size_bytes": 2,
                    "sha256": hashlib.sha256(b"{}").hexdigest(),
                }
            ],
            "batch_manifest_sha256": hashlib.sha256(b"{}").hexdigest(),
            "planned_fit_count": 1,
            "successful_fit_count": 1,
            "failed_fit_count": 0,
            "job_purpose": "benchmark",
            "operational_candidate_trained": False,
            "report_id": "sha256:" + "b" * 64,
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging_root = root / "staging"
            transport.receive_result_file(
                staging_root,
                job_id=job_id,
                logical_path=transport.RESULT_MANIFEST_NAME,
                content=(json.dumps(result) + "\n").encode(),
            )
            with self.assertRaises(ValueError):
                transport.finalize_result(
                    staging_root,
                    job_id=job_id,
                    registry_path=REGISTRY_PATH,
                    models_root=root / "models",
                    job_purpose="benchmark",
                )
            self.assertTrue((staging_root / job_id / "multiversion").is_dir())
