import os
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_paths


class MushroomPathsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.old_env = {
            key: os.environ.get(key)
            for key in (
                "RAINMAPPER_SHARE_ROOT",
                "RAINMAPPER_MUSHROOM_DATA_DIR",
                "RAINMAPPER_MUSHROOM_DEFAULTS_DIR",
                "RAINMAPPER_MUSHROOM_OBSERVATIONS_PATH",
                "RAINMAPPER_WEATHER_DATA_DIR",
                "RAINMAPPER_MEDIA_ROOT",
                "RAINMAPPER_MUSHROOM_DERIVED_DATA_DIR",
                "RAINMAPPER_MUSHROOM_REBUILD_ARTIFACTS_DIR",
                "RAINMAPPER_MUSHROOM_WORKER_STORAGE_DIR",
                "RAINMAPPER_MUSHROOM_ML_MODELS_DIR",
                "RAINMAPPER_PREDICTOR_PRECOMPUTE_DIR",
                "RAINMAPPER_PREDICTOR_RUNTIME_ARCHIVE_DIR",
                "RAINMAPPER_PREDICTOR_RUNTIME_ARCHIVE_FALLBACK_DIR",
            )
        }
        self.addCleanup(self.restore_env)
        for key in self.old_env:
            os.environ.pop(key, None)

    def restore_env(self) -> None:
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_share_root_drives_live_data_and_model_paths(self) -> None:
        share_root = self.root / "share"
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(share_root)

        self.assertEqual(mushroom_paths.share_root(), share_root)
        self.assertEqual(mushroom_paths.mushroom_data_dir(), share_root / "mushroom-data")
        self.assertEqual(mushroom_paths.weather_data_dir(), share_root / "Data")
        self.assertEqual(
            mushroom_paths.mushroom_learned_model_json_path(),
            share_root / "mushroom-data" / "mushroom_model_v0.json",
        )
        self.assertEqual(
            mushroom_paths.mushroom_model_state_path(),
            share_root / "mushroom-data" / "mushroom_model_v0_state.json",
        )
        self.assertEqual(
            mushroom_paths.mushroom_ml_version_archive_dir(),
            share_root / "mushroom-data" / "ml_version_archive",
        )

    def test_specific_env_overrides_share_root(self) -> None:
        share_root = self.root / "share"
        data_dir = self.root / "custom-data"
        weather_dir = self.root / "custom-weather"
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(share_root)
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir)
        os.environ["RAINMAPPER_WEATHER_DATA_DIR"] = str(weather_dir)

        self.assertEqual(mushroom_paths.mushroom_data_dir(), data_dir)
        self.assertEqual(mushroom_paths.weather_data_dir(), weather_dir)

    def test_predictor_precompute_prefers_media_outside_share(self) -> None:
        share_root = self.root / "share"
        media_root = self.root / "media" / "rainmapper"
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(share_root)
        os.environ["RAINMAPPER_MEDIA_ROOT"] = str(media_root)

        self.assertEqual(
            mushroom_paths.mushroom_predictor_precompute_dir(),
            media_root / "predictor_precompute",
        )
        self.assertEqual(
            mushroom_paths.mushroom_predictor_precompute_artifact_path(),
            media_root / "predictor_precompute" / "active.sqlite3",
        )

    def test_reconstructible_mushroom_paths_prefer_media(self) -> None:
        share_root = self.root / "share"
        media_root = self.root / "media" / "rainmapper"
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(share_root)
        os.environ["RAINMAPPER_MEDIA_ROOT"] = str(media_root)

        derived = media_root / "mushroom-derived"
        artifacts = derived / "mushroom-artifacts"
        worker = derived / "worker"
        self.assertEqual(mushroom_paths.mushroom_derived_data_dir(), derived)
        self.assertEqual(mushroom_paths.mushroom_rebuild_artifacts_dir(), artifacts)
        self.assertEqual(mushroom_paths.mushroom_ml_models_dir(), derived / "ml_models")
        self.assertEqual(
            mushroom_paths.mushroom_observation_features_json_path(),
            artifacts / "mushroom_observation_features_v0.json",
        )
        self.assertEqual(
            mushroom_paths.mushroom_worker_input_bundles_dir(),
            worker / "input-bundles",
        )
        self.assertEqual(
            mushroom_paths.mushroom_worker_candidate_results_dir(),
            worker / "candidate-results",
        )
        self.assertEqual(
            mushroom_paths.mushroom_worker_predictor_results_dir(),
            worker / "predictor-results",
        )

    def test_predictor_precompute_specific_override_wins(self) -> None:
        override = self.root / "custom-precompute"
        os.environ["RAINMAPPER_MEDIA_ROOT"] = str(self.root / "media" / "rainmapper")
        os.environ["RAINMAPPER_PREDICTOR_PRECOMPUTE_DIR"] = str(override)

        self.assertEqual(mushroom_paths.mushroom_predictor_precompute_dir(), override)

    def test_observations_path_prefers_live_copy_then_defaults(self) -> None:
        share_root = self.root / "share"
        defaults = self.root / "defaults"
        live_observations = share_root / "mushroom-data" / "mushroom_observations.json"
        default_observations = defaults / "mushroom_observations.json"
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(share_root)
        os.environ["RAINMAPPER_MUSHROOM_DEFAULTS_DIR"] = str(defaults)

        self.assertEqual(mushroom_paths.mushroom_observations_path(), default_observations)

        live_observations.parent.mkdir(parents=True)
        live_observations.write_text('{"observations": []}', encoding="utf-8")
        self.assertEqual(mushroom_paths.mushroom_observations_path(), live_observations)

    def test_predictor_runtime_archive_prefers_configured_media_and_is_private(self) -> None:
        share_root = self.root / "share"
        archive_dir = self.root / "media" / "runtime-cache" / "archives"
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(share_root)
        os.environ["RAINMAPPER_PREDICTOR_RUNTIME_ARCHIVE_DIR"] = str(archive_dir)

        location = mushroom_paths.prepare_predictor_runtime_archive_dir()

        self.assertEqual(location.path, archive_dir)
        self.assertFalse(location.fallback_used)
        self.assertEqual(location.path.stat().st_mode & 0o777, 0o700)

    def test_predictor_runtime_archive_rejects_share_and_uses_explicit_fallback(self) -> None:
        share_root = self.root / "share"
        forbidden = share_root / "mushroom-data" / "ml_models" / "archives"
        fallback = self.root / "temporary-cache" / "archives"
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(share_root)
        os.environ["RAINMAPPER_PREDICTOR_RUNTIME_ARCHIVE_DIR"] = str(forbidden)
        os.environ["RAINMAPPER_PREDICTOR_RUNTIME_ARCHIVE_FALLBACK_DIR"] = str(fallback)

        location = mushroom_paths.prepare_predictor_runtime_archive_dir()

        self.assertEqual(location.path, fallback)
        self.assertTrue(location.fallback_used)
        self.assertIn("cannot reside under share", location.diagnostic or "")
        self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    unittest.main()
