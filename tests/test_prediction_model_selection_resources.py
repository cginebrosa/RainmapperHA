"""The second research folder must not reset the shared disk allowance."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/prediction_model_selection"))
spec = importlib.util.spec_from_file_location("selection_resource_guard", ROOT / "scripts/prediction_model_selection/bounded.py")
guard = importlib.util.module_from_spec(spec)
# Avoid the legacy scripts' equally named common module in a combined test run.
from scripts.prediction_model_selection import common
from scripts.prediction_model_selection import close
with patch.dict(sys.modules, {"common": common}):
    spec.loader.exec_module(guard)


class ResourceBudgetTests(unittest.TestCase):
    def test_disk_budget_counts_both_studies_without_following_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp) / "old", Path(temp) / "new"
            old.mkdir(); new.mkdir()
            (old / "models").write_bytes(b"x" * 40)
            (new / "predictions").write_bytes(b"x" * 10)
            (new / "reference").symlink_to(old / "models")
            with patch.object(guard, "OLD_OUTPUT", old), patch.object(guard, "OUTPUT", new):
                self.assertEqual(guard.output_bytes(), 50)

    def test_monitor_keeps_orphaned_members_of_the_same_process_group(self):
        with patch.object(guard.subprocess, "check_output", return_value="10 10 100\n11 10 200\n12 12 300\n"):
            self.assertEqual(guard.process_tree(10), {10: 102400, 11: 204800})

    def test_historical_source_requires_its_exact_archive_and_explicit_permission(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "script.py"
            path.write_text("old bytes")
            sha = common.digest(path)
            archive = root / "outputs/source-archive"
            archive.mkdir(parents=True)
            (archive / (sha + ".py")).write_bytes(path.read_bytes())
            path.write_text("corrected bytes")
            record = {"path": "script.py", "sha256": sha}
            with patch.object(close, "ROOT", root), patch.object(close, "OUTPUT", root / "outputs"):
                with self.assertRaises(ValueError):
                    close.verify_record(record)
                close.verify_record(record, allow_archived_source=True)
                (archive / (sha + ".py")).write_text("wrong archive")
                with self.assertRaises(ValueError):
                    close.verify_record(record, allow_archived_source=True)

    def test_source_archive_does_not_permit_changed_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "data.json"
            path.write_text("{}")
            sha = common.digest(path)
            archive = root / "outputs/source-archive"
            archive.mkdir(parents=True)
            (archive / (sha + ".json")).write_bytes(path.read_bytes())
            path.write_text('{"changed":true}')
            with patch.object(close, "ROOT", root), patch.object(close, "OUTPUT", root / "outputs"):
                with self.assertRaises(ValueError):
                    close.verify_record({"path": "data.json", "sha256": sha}, allow_archived_source=True)


if __name__ == "__main__":
    unittest.main()
