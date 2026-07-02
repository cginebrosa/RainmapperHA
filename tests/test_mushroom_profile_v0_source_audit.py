import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT_DIR / "scripts" / "audit-mushroom-profile-v0-source.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_mushroom_profile_v0_source", AUDIT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AUDIT = load_audit_module()


def load_json(relative_path: str):
    return json.loads((ROOT_DIR / relative_path).read_text(encoding="utf-8"))


class MushroomProfileV0SourceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profiles = load_json("mushroom-data/mushroom_profiles.json")
        self.catalogs = load_json("mushroom-data/mushroom_reference_catalogs.json")
        self.source = load_json("docs/mushrooms/literature/marc-estevez-v0-source-normalized.json")

    def test_every_current_profile_exists_in_normalized_source(self) -> None:
        audit = AUDIT.build_audit(self.profiles, self.catalogs, self.source)

        self.assertEqual([], audit["summary"]["current_profiles_missing_from_source"])
        self.assertEqual(21, audit["summary"]["current_profile_count"])
        self.assertEqual(21, audit["summary"]["source_species_count"])

    def test_normalized_source_uses_existing_catalog_ids_only(self) -> None:
        audit = AUDIT.build_audit(self.profiles, self.catalogs, self.source)

        self.assertEqual([], audit["summary"]["source_catalog_reference_errors"])

    def test_expected_source_species_are_promoted(self) -> None:
        audit = AUDIT.build_audit(self.profiles, self.catalogs, self.source)

        missing = set(audit["summary"]["source_species_missing_from_current_profiles"])
        current_ids = {
            profile["species_id"]
            for profile in self.profiles["species_profiles"]
            if isinstance(profile, dict)
        }
        self.assertEqual(set(), missing)
        self.assertIn("lactarius_deliciosus", current_ids)
        self.assertIn("lactarius_salmonicolor_quieticolor_group", current_ids)
        self.assertIn("craterellus_cornucopioides", current_ids)
        self.assertIn("tuber_melanosporum", current_ids)
        self.assertNotIn("lactarius_salmonicolor", missing)
        self.assertNotIn("lactarius_quieticolor", missing)


if __name__ == "__main__":
    unittest.main()
