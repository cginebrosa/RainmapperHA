import tempfile
import unittest
from pathlib import Path

import pandas as pd

from rainmapper_core.atomic_io import write_csv_atomic


class AtomicCsvTests(unittest.TestCase):
    def test_success_replaces_target_without_leaving_temporary_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "incremental.csv"
            target.write_text("value\nold\n", encoding="utf-8")

            write_csv_atomic(pd.DataFrame([{"value": "new"}]), target)

            self.assertEqual(target.read_text(encoding="utf-8"), "value\nnew\n")
            self.assertEqual(list(Path(temp_dir).glob(".incremental.csv.*.tmp")), [])

    def test_serialization_failure_preserves_previous_target(self):
        class FailingFrame:
            def to_csv(self, path, **_kwargs):
                Path(path).write_text("partial", encoding="utf-8")
                raise RuntimeError("simulated interrupted serialization")

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "incremental.csv"
            target.write_text("value\nold\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "simulated interrupted"):
                write_csv_atomic(FailingFrame(), target)

            self.assertEqual(target.read_text(encoding="utf-8"), "value\nold\n")
            self.assertEqual(list(Path(temp_dir).glob(".incremental.csv.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
