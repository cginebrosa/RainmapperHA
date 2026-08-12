import multiprocessing
import tempfile
import time
import unittest
from pathlib import Path

from rainmapper_core.weather_history_run_lock import (
    WeatherRunBusy,
    acquire_run_lock,
    release_run_lock,
)


def hold_lock(path: str, ready, release) -> None:
    handle = acquire_run_lock(Path(path), 1.0)
    ready.set()
    release.wait(5)
    release_run_lock(handle)


class WeatherHistoryRunLockTests(unittest.TestCase):
    def test_cross_process_lock_times_out_and_recovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "run.lock"
            ready = multiprocessing.Event()
            release = multiprocessing.Event()
            process = multiprocessing.Process(
                target=hold_lock,
                args=(str(path), ready, release),
            )
            process.start()
            self.addCleanup(lambda: process.is_alive() and process.terminate())
            self.assertTrue(ready.wait(2))
            started = time.monotonic()
            with self.assertRaises(WeatherRunBusy):
                acquire_run_lock(path, 0.05)
            self.assertGreaterEqual(time.monotonic() - started, 0.04)
            release.set()
            process.join(2)
            self.assertEqual(process.exitcode, 0)
            handle = acquire_run_lock(path, 0.1)
            release_run_lock(handle)


if __name__ == "__main__":
    unittest.main()
