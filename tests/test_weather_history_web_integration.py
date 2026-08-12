import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WeatherHistoryWebIntegrationTests(unittest.TestCase):
    def test_addon_option_is_opt_in(self):
        config = (ROOT / "rainmapper-app" / "config.yaml").read_text(encoding="utf-8")
        self.assertIn("partitioned_weather_history: false", config)

    def test_shell_runner_wraps_and_drains_partitioned_updates(self):
        script = (ROOT / "rainmapper-app" / "run.sh").read_text(encoding="utf-8")
        self.assertIn("rainmapper_core.weather_history_run_lock", script)
        self.assertIn("run_update_transaction", script)
        self.assertIn("rainmapper_core.weather_history_archive", script)
        self.assertIn("download-preflight", script)
        self.assertIn("combine-exit-codes", script)
        self.assertIn(
            'run_update_transaction "$window_days_init" "$window_days_end"',
            script,
        )

    def test_web_runner_blocks_maps_after_archive_failure(self):
        source = (ROOT / "rainmapper-app" / "app" / "web_server.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("acquire_weather_run_lock", source)
        self.assertIn("weather_history_archive", source)
        self.assertIn("combine_update_exit_codes", source)
        self.assertIn("if exit_code not in {0, 2}:\n                break", source)


if __name__ == "__main__":
    unittest.main()
