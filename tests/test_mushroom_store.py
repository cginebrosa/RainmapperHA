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
