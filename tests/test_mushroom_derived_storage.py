import os
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_derived_storage
from rainmapper_core import mushroom_paths


class MushroomDerivedStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.old_env = {
            key: os.environ.get(key)
            for key in (
                "RAINMAPPER_SHARE_ROOT",
                "RAINMAPPER_MEDIA_ROOT",
                "RAINMAPPER_MUSHROOM_DATA_DIR",
                "RAINMAPPER_MUSHROOM_DERIVED_DATA_DIR",
                "RAINMAPPER_MUSHROOM_REBUILD_ARTIFACTS_DIR",
                "RAINMAPPER_MUSHROOM_WORKER_STORAGE_DIR",
                "RAINMAPPER_MUSHROOM_ML_MODELS_DIR",
            )
        }
        self.addCleanup(self.restore_env)
        for key in self.old_env:
            os.environ.pop(key, None)
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(self.root / "share")
        os.environ["RAINMAPPER_MEDIA_ROOT"] = str(self.root / "media")

    def restore_env(self) -> None:
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def write_legacy(self, relative: str, content: bytes = b"legacy") -> Path:
        path = mushroom_paths.mushroom_data_dir() / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_transition_copies_only_derived_data_and_preserves_legacy_sources(self) -> None:
        observation = self.write_legacy("mushroom_observations.json", b"source")
        artifact = self.write_legacy("mushroom_observation_features_v0.json")
        model = self.write_legacy("ml_models/batches/current/model.joblib", b"model")
        excluded = self.write_legacy(
            "ml_models/.predictor-runtime-archives/legacy.tar", b"archive"
        )
        bundle = self.write_legacy(
            ".worker-input-bundles/worker_job_abcdefgh/job_spec.json", b"{}"
        )
        predictor = self.write_legacy(
            ".worker-predictor-results/worker_job_abcdefgh.json", b"{}"
        )

        report = mushroom_derived_storage.prepare_derived_storage_transition()

        self.assertTrue(report["enabled"])
        self.assertFalse(report["errors"])
        self.assertTrue(observation.is_file())
        self.assertFalse(
            (mushroom_paths.mushroom_derived_data_dir() / "mushroom_observations.json").exists()
        )
        self.assertEqual(
            (mushroom_paths.mushroom_observation_features_json_path()).read_bytes(),
            artifact.read_bytes(),
        )
        self.assertEqual(
            (mushroom_paths.mushroom_ml_models_dir() / "batches/current/model.joblib").read_bytes(),
            model.read_bytes(),
        )
        self.assertFalse(
            (
                mushroom_paths.mushroom_ml_models_dir()
                / ".predictor-runtime-archives/legacy.tar"
            ).exists()
        )
        self.assertIn(str(excluded.parent), report["excluded"])
        self.assertEqual(
            (mushroom_paths.mushroom_worker_input_bundles_dir() / bundle.parent.name / bundle.name).read_bytes(),
            bundle.read_bytes(),
        )
        self.assertEqual(
            (mushroom_paths.mushroom_worker_predictor_results_dir() / predictor.name).read_bytes(),
            predictor.read_bytes(),
        )
        for legacy_path in (artifact, model, excluded, bundle, predictor):
            self.assertTrue(legacy_path.is_file())

        repeated = mushroom_derived_storage.prepare_derived_storage_transition()
        self.assertTrue(repeated["already_complete"])
        self.assertFalse(repeated["copied_files"])

    def test_transition_does_not_overwrite_a_different_media_artifact(self) -> None:
        self.write_legacy("mushroom_model_v0.json", b"legacy")
        target = mushroom_paths.mushroom_learned_model_json_path()
        target.parent.mkdir(parents=True)
        target.write_bytes(b"newer")

        report = mushroom_derived_storage.prepare_derived_storage_transition()

        self.assertEqual(target.read_bytes(), b"newer")
        self.assertEqual(report["conflicts"], [str(target)])

    def test_empty_media_and_share_are_a_valid_recoverable_state(self) -> None:
        report = mushroom_derived_storage.prepare_derived_storage_transition()

        self.assertTrue(report["enabled"])
        self.assertFalse(report["copied_files"])
        self.assertFalse(report["errors"])


if __name__ == "__main__":
    unittest.main()
