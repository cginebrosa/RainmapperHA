import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import joblib

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_benchmark_reports as benchmark_reports
from rainmapper_core import mushroom_ml_multiversion_plan
from rainmapper_core import mushroom_ml_multiversion_transport as transport
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLMultiversionTransportTests(TestCase):
    def test_complete_benchmark_is_reused_as_candidate_without_refitting(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        version_id = "altitude_v2"
        profile_key = "altitude_v2/common_idw"
        source_batch_id = "benchmark-reuse-v2"
        candidate_batch_id = "candidate-reuse-v2"
        plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id=source_batch_id,
            snapshot_id="sha256:" + "7" * 64,
            generation_ids={version_id: f"{version_id}_{source_batch_id}"},
            species_ids=["boletus_edulis"],
            version_ids=[version_id],
            profile_keys=[profile_key],
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
                    "target_date": f"2025-03-{index + 1:02d}",
                },
            }
            for index in range(20)
        ]
        benchmark = {
            "feature_set": {"predictive_feature_cols": ["test_feature"]},
            "samples": samples,
        }
        benchmarks = {
            trainer.benchmark_key(version_id, contract, "common_idw"): benchmark
            for contract in ("fixed_gap_7d_altitude_v2", "lag_event_altitude_v2")
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            produced_root = root / "produced"
            batch_dir, manifest = trainer.write_batch(
                registry, plan, benchmarks, models_root=produced_root
            )
            quality = batch_dir / "quality-catalog.json"
            quality.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "kind": "mushroom_ml_quality_catalog",
                        "snapshot_id": plan["snapshot_id"],
                        "entries": [
                            {
                                "version_id": version_id,
                                "profile_id": "common_idw",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            training_inputs = batch_dir / "training-input-manifest.json"
            training_inputs.write_text(
                json.dumps(
                    {
                        "schema_version": "0.2",
                        "kind": "mushroom_rebuild_input_manifest",
                        "snapshot_id": plan["snapshot_id"],
                    }
                ),
                encoding="utf-8",
            )
            manifest.update(
                {
                    "job_purpose": "benchmark",
                    "operational_candidate_trained": False,
                    "quality_catalog": {
                        "path": f"batches/{source_batch_id}/quality-catalog.json",
                        "sha256": trainer.sha256(quality),
                    },
                    "training_input_manifest": {
                        "path": f"batches/{source_batch_id}/training-input-manifest.json",
                        "sha256": trainer.sha256(training_inputs),
                    },
                }
            )
            (batch_dir / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            models = root / "models"
            source_archive = models / "benchmarks" / source_batch_id
            source_archive.parent.mkdir(parents=True)
            shutil.copytree(batch_dir, source_archive)
            report = {
                "batch_id": source_batch_id,
                "snapshot_id": plan["snapshot_id"],
                "selection": {
                    "profiles": [
                        {
                            "profile_key": profile_key,
                            "version_id": version_id,
                            "profile_id": "common_idw",
                        }
                    ]
                },
            }
            with mock.patch.object(
                transport.mushroom_ml_benchmark_reports,
                "load_report",
                return_value=report,
            ):
                archived = transport.archive_benchmark_as_candidate(
                    models_root=models,
                    registry_path=REGISTRY_PATH,
                    benchmark_batch_id=source_batch_id,
                    version_id=version_id,
                    candidate_batch_id=candidate_batch_id,
                    job_id="worker_job_reusev2",
                )

            self.assertEqual("verified_benchmark_reuse", archived["artifact_preparation"])
            self.assertEqual(plan["fit_count"], archived["reused_artifact_count"])
            candidate_root = models / "candidates" / candidate_batch_id / "batch"
            candidate_manifest = json.loads(
                (candidate_root / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertTrue(candidate_manifest["operational_candidate_trained"])
            self.assertEqual(source_batch_id, candidate_manifest["source_benchmark_batch_id"])
            source_artifact = manifest["artifacts"][0]
            candidate_artifact = candidate_manifest["artifacts"][0]
            source_bundle = joblib.load(
                source_archive
                / Path(source_artifact["path"]).relative_to(Path("batches") / source_batch_id)
            )
            candidate_bundle = joblib.load(
                candidate_root
                / Path(candidate_artifact["path"]).relative_to(
                    Path("batches") / candidate_batch_id
                )
            )
            self.assertEqual(
                joblib.hash(source_bundle["model"]), joblib.hash(candidate_bundle["model"])
            )
            self.assertEqual(
                source_bundle["training_row_count"], candidate_bundle["training_row_count"]
            )

    def test_operational_result_stays_staged_until_explicit_install(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        active_version = registry["active_version_id"]
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
            }
            staging = root / "staging"
            transport.receive_result_file(
                staging,
                job_id=job_id,
                logical_path=transport.RESULT_MANIFEST_NAME,
                content=json.dumps(result).encode(),
            )
            for record in declared:
                transport.receive_result_file(
                    staging,
                    job_id=job_id,
                    logical_path=record["path"],
                    content=(upload / record["path"]).read_bytes(),
                )
            models = root / "installed"
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

            installed = transport.install_staged_operational_result(
                staging,
                job_id=job_id,
                registry_path=REGISTRY_PATH,
                models_root=models,
            )
            self.assertEqual("verified_and_installed", installed["status"])
            self.assertTrue((models / "runtime-batch.json").is_file())

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
            self.assertTrue((models_root / "benchmarks" / "batch-transport" / "manifest.json").is_file())
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
