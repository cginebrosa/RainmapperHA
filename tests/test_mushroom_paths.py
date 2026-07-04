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

    def test_specific_env_overrides_share_root(self) -> None:
        share_root = self.root / "share"
        data_dir = self.root / "custom-data"
        weather_dir = self.root / "custom-weather"
        os.environ["RAINMAPPER_SHARE_ROOT"] = str(share_root)
        os.environ["RAINMAPPER_MUSHROOM_DATA_DIR"] = str(data_dir)
        os.environ["RAINMAPPER_WEATHER_DATA_DIR"] = str(weather_dir)

        self.assertEqual(mushroom_paths.mushroom_data_dir(), data_dir)
        self.assertEqual(mushroom_paths.weather_data_dir(), weather_dir)

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


if __name__ == "__main__":
    unittest.main()
