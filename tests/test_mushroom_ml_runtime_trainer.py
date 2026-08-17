import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLRuntimeTrainerTests(TestCase):
    def test_batch_is_immutable_verified_and_not_activated(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        artifact_ref = catalog.ModelArtifactRef(
            batch_id="batch-test",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
        )
        training_plan = {
            "batch_id": "batch-test",
            "snapshot_id": "sha256:" + "a" * 64,
            "fits": [
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": [7],
                }
            ],
        }
        samples = []
        for index in range(20):
            samples.append(
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
            )
        benchmark = {
            "feature_set": {"predictive_feature_cols": ["test_feature"]},
            "samples": samples,
        }
        key = trainer.benchmark_key(
            "biology_v3", "fixed_gap_7d_biology_v3", "core"
        )

        with TemporaryDirectory() as temporary:
            models_root = Path(temporary)
            progress_events = []
            destination, manifest = trainer.write_batch(
                registry,
                training_plan,
                {key: benchmark},
                models_root=models_root,
                progress_callback=progress_events.append,
            )

            stored = json.loads((destination / "manifest.json").read_text())
            model_path = models_root / stored["artifacts"][0]["path"]
            self.assertTrue(model_path.is_file())
            self.assertEqual(trainer.sha256(model_path), stored["artifacts"][0]["sha256"])
            self.assertFalse(stored["active"])
            self.assertFalse((models_root / "runtime-batch.json").exists())
            self.assertEqual(manifest["batch_id"], "batch-test")
            self.assertEqual(progress_events[-1]["completed_fit_count"], 1)
            self.assertEqual(progress_events[-1]["planned_fit_count"], 1)
            with self.assertRaises(FileExistsError):
                trainer.write_batch(
                    registry,
                    training_plan,
                    {key: benchmark},
                    models_root=models_root,
                )

    def test_untrainable_members_are_reported_without_discarding_batch(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        trainable = catalog.ModelArtifactRef(
            batch_id="batch-partial",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
        )
        unavailable = catalog.ModelArtifactRef(
            **{
                **trainable.as_dict(),
                "species_id": "amanita_caesarea",
            }
        )
        training_plan = {
            "batch_id": "batch-partial",
            "snapshot_id": "sha256:" + "b" * 64,
            "fits": [
                {"artifact_ref": trainable.as_dict(), "supported_horizons": [7]},
                {"artifact_ref": unavailable.as_dict(), "supported_horizons": [7]},
            ],
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

        with TemporaryDirectory() as temporary:
            _destination, manifest = trainer.write_batch(
                registry,
                training_plan,
                {key: benchmark},
                models_root=Path(temporary),
            )

        self.assertEqual(manifest["planned_fit_count"], 2)
        self.assertEqual(manifest["successful_fit_count"], 1)
        self.assertEqual(manifest["failed_fit_count"], 1)
        self.assertEqual(
            manifest["failed_fits"][0]["artifact_ref"]["species_id"],
            "amanita_caesarea",
        )
