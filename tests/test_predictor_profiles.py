import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "mushroom-data"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-mushroom-data.py"


EXPECTED_SPECIES_IDS = {
    "amanita_caesarea",
    "boletus_aereus",
    "boletus_edulis",
    "boletus_pinophilus",
    "calocybe_gambosa",
    "cantharellus_cibarius_sl",
    "cantharellus_lutescens",
    "craterellus_cornucopioides",
    "hygrophorus_latitabundus",
    "hygrophorus_marzuolus",
    "lactarius_deliciosus",
    "lactarius_salmonicolor_quieticolor_group",
    "lactarius_sanguifluus",
    "lactarius_vinosus",
    "lepista_nuda",
    "macrolepiota_procera",
    "marasmius_oreades",
    "morchella_elata_complex",
    "russula_virescens",
    "tricholoma_terreum",
    "tuber_melanosporum",
}


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_mushroom_data", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator_module()


class PredictorProfileDatasetTests(unittest.TestCase):
    def test_current_mushroom_profile_dataset_has_expected_species(self) -> None:
        profiles_path = DATA_DIR / "mushroom_profiles.json"
        data = json.loads(profiles_path.read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], "0.3")
        self.assertEqual(data["requires_catalog_file"], "mushroom_reference_catalogs.json")
        self.assertEqual(
            {profile["species_id"] for profile in data["species_profiles"]},
            EXPECTED_SPECIES_IDS,
        )

    def test_current_mushroom_dataset_has_no_broken_catalog_references(self) -> None:
        messages = VALIDATOR.validate_mushroom_data(DATA_DIR)
        broken_reference_errors = [
            message.format()
            for message in messages
            if message.severity == "ERROR" and "unknown" in message.message
        ]

        self.assertEqual([], broken_reference_errors)


if __name__ == "__main__":
    unittest.main()
