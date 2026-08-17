import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_transport as transport
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLMultiversionTransportTests(TestCase):
    def test_tiny_result_is_staged_verified_and_installed(self) -> None:
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
                "operational_candidate_trained": False,
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
            )

            self.assertEqual(verification["status"], "verified_and_installed")
            self.assertFalse(verification["operational_candidate_trained"])
            self.assertTrue((models_root / "runtime-batch.json").is_file())
            self.assertTrue((models_root / "batches" / "batch-transport" / "manifest.json").is_file())
