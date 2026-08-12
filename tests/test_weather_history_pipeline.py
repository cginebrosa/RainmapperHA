import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core.weather_history_pipeline import (
    WeatherDiskPreflightError,
    check_download_disk_preflight,
    combine_update_exit_codes,
)


class WeatherHistoryPipelineTests(unittest.TestCase):
    def test_exit_code_matrix(self):
        expected = {
            (0, 0): 0,
            (2, 0): 2,
            (1, 0): 1,
            (3, 0): 1,
            (0, 1): 1,
            (2, 1): 1,
            (1, 1): 1,
            (0, 2): 1,
        }
        for pair, result in expected.items():
            with self.subTest(pair=pair):
                self.assertEqual(combine_update_exit_codes(*pair), result)

    def test_disk_preflight_passes_with_budget_and_reports_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            usage = mock.Mock(free=1_000)
            with mock.patch(
                "rainmapper_core.weather_history_pipeline.shutil.disk_usage",
                return_value=usage,
            ):
                report = check_download_disk_preflight(
                    Path(temporary), required_bytes=200, reserve_bytes=700
                )
        self.assertEqual(report.free_bytes, 1_000)

    def test_disk_preflight_fails_before_work_when_reserve_would_be_used(self):
        with tempfile.TemporaryDirectory() as temporary:
            usage = mock.Mock(free=899)
            with mock.patch(
                "rainmapper_core.weather_history_pipeline.shutil.disk_usage",
                return_value=usage,
            ):
                with self.assertRaises(WeatherDiskPreflightError):
                    check_download_disk_preflight(
                        Path(temporary), required_bytes=200, reserve_bytes=700
                    )
