import copy
import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core.mushroom_store import MushroomDataStore


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULTS_DIR = REPO_ROOT / "mushroom-data"


class MushroomDataStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name) / "mushroom-data"
        self.store = MushroomDataStore(defaults_dir=DEFAULTS_DIR, data_dir=self.data_dir)

    def test_ensure_seeded_copies_missing_defaults_only(self) -> None:
        copied = self.store.ensure_seeded()

        self.assertEqual(["profiles", "catalogs", "gis", "observations"], copied)
        self.assertTrue((self.data_dir / "mushroom_profiles.json").exists())
        self.assertTrue((self.data_dir / "mushroom_reference_catalogs.json").exists())
        self.assertTrue((self.data_dir / "mushroom_gis_mappings.json").exists())
        self.assertTrue((self.data_dir / "mushroom_observations.json").exists())
        self.assertEqual([], self.store.ensure_seeded())

    def test_validate_current_reports_warnings_but_no_errors_for_seeded_defaults(self) -> None:
        errors, warnings = self.store.validate_current()

        self.assertEqual([], [message.as_dict() for message in errors])
        self.assertGreaterEqual(len(warnings), 1)

    def test_empty_templates_preserve_root_shape_and_clear_editable_arrays(self) -> None:
        profile_template = self.store.empty_template("profiles")["data"]
        catalog_template = self.store.empty_template("catalogs")["data"]
        observation_template = self.store.empty_template("observations")["data"]

        self.assertEqual([], profile_template["species_profiles"])
        self.assertIn("metadata", profile_template)
        self.assertTrue(catalog_template["catalogs"])
        self.assertTrue(all(items == [] for items in catalog_template["catalogs"].values()))
        self.assertEqual([], observation_template["observations"])

    def test_replace_writes_atomically_and_keeps_backup(self) -> None:
        self.store.ensure_seeded()
        profiles = self.store.load("profiles")
        updated = copy.deepcopy(profiles)
        updated["metadata"]["updated_by"] = "unit_test"

        result = self.store.replace("profiles", updated)

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.backup_path)
        assert result.backup_path is not None
        self.assertTrue(result.backup_path.exists())
        persisted = json.loads((self.data_dir / "mushroom_profiles.json").read_text(encoding="utf-8"))
        self.assertEqual("unit_test", persisted["metadata"]["updated_by"])

    def test_manual_keep_backup_uses_keep_marker(self) -> None:
        self.store.ensure_seeded()

        backup_path = self.store.backup_current("profiles", keep=True)

        self.assertIsNotNone(backup_path)
        assert backup_path is not None
        self.assertTrue(backup_path.exists())
        self.assertIn(".keep", backup_path.stem)

    def test_replace_prunes_automatic_backups_but_preserves_keep_backups(self) -> None:
        self.store.ensure_seeded()
        backup_dir = self.store.backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        for index in range(22):
            (backup_dir / f"mushroom_profiles.20260101T0000{index:02d}Z.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
        keep_path = backup_dir / "mushroom_profiles.20260101T999999Z.keep.json"
        keep_path.write_text("{}\n", encoding="utf-8")
        profiles = self.store.load("profiles")
        updated = copy.deepcopy(profiles)
        updated["metadata"]["updated_by"] = "retention_test"

        result = self.store.replace("profiles", updated)

        self.assertTrue(result.ok)
        automatic_backups = [
            path
            for path in backup_dir.glob("mushroom_profiles.*.json")
            if ".keep" not in path.stem
        ]
        self.assertLessEqual(len(automatic_backups), 20)
        self.assertTrue(keep_path.exists())

    def test_replace_invalid_payload_reports_errors_and_preserves_existing_file(self) -> None:
        self.store.ensure_seeded()
        original = (self.data_dir / "mushroom_profiles.json").read_text(encoding="utf-8")
        invalid = self.store.load("profiles")
        invalid.pop("species_profiles")

        result = self.store.replace("profiles", invalid)

        self.assertFalse(result.ok)
        self.assertTrue(any("species_profiles" in message.location for message in result.errors))
        current = (self.data_dir / "mushroom_profiles.json").read_text(encoding="utf-8")
        self.assertEqual(original, current)

    def test_gis_replace_is_blocked_in_current_phase(self) -> None:
        with self.assertRaises(ValueError):
            self.store.replace("gis", self.store.load("gis"))


if __name__ == "__main__":
    unittest.main()
