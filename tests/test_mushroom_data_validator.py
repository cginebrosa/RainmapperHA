import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-mushroom-data.py"
DATA_DIR = REPO_ROOT / "mushroom-data"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_mushroom_data", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator_module()


def load_json(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def write_dataset(target: Path, profiles, catalogs, gis) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "mushroom_profiles.json").write_text(
        json.dumps(profiles, indent=2), encoding="utf-8"
    )
    (target / "mushroom_reference_catalogs.json").write_text(
        json.dumps(catalogs, indent=2), encoding="utf-8"
    )
    (target / "mushroom_gis_mappings.json").write_text(
        json.dumps(gis, indent=2), encoding="utf-8"
    )


class MushroomDataValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profiles = load_json("mushroom_profiles.json")
        self.catalogs = load_json("mushroom_reference_catalogs.json")
        self.gis = load_json("mushroom_gis_mappings.json")

    def validate_temp_dataset(self, profiles=None, catalogs=None, gis=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            write_dataset(
                target,
                copy.deepcopy(profiles if profiles is not None else self.profiles),
                copy.deepcopy(catalogs if catalogs is not None else self.catalogs),
                copy.deepcopy(gis if gis is not None else self.gis),
            )
            return VALIDATOR.validate_mushroom_data(target)

    def test_current_dataset_has_no_broken_id_references(self) -> None:
        messages = self.validate_temp_dataset()
        id_errors = [
            message
            for message in messages
            if message.severity == "ERROR"
            and ("unknown" in message.message or "missing required field" in message.message)
        ]

        self.assertEqual([], [message.format() for message in id_errors])

    def test_validator_reports_profile_and_gis_unknown_ids_together(self) -> None:
        profiles = copy.deepcopy(self.profiles)
        gis = copy.deepcopy(self.gis)
        profiles["species_profiles"][0]["ecology"]["host_affinities"][0]["id"] = "host_missing"
        gis["vegetation_mappings"][0]["mapped_host_ids"] = ["host_missing_from_gis"]

        messages = self.validate_temp_dataset(profiles=profiles, gis=gis)
        errors = [message.format() for message in messages if message.severity == "ERROR"]

        self.assertTrue(any("host_missing" in message for message in errors))
        self.assertTrue(any("host_missing_from_gis" in message for message in errors))
        self.assertGreaterEqual(len(errors), 2)

    def test_validator_reports_scoring_weight_and_month_errors(self) -> None:
        profiles = copy.deepcopy(self.profiles)
        profile = profiles["species_profiles"][0]
        profile["scoring_weights"]["habitat"] = 0.99
        profile["phenology"]["main_months"] = [0, 13]

        messages = self.validate_temp_dataset(profiles=profiles)
        errors = [message.format() for message in messages if message.severity == "ERROR"]

        self.assertTrue(any("weights sum" in message for message in errors))
        self.assertTrue(any("main_months[0]" in message for message in errors))
        self.assertTrue(any("main_months[1]" in message for message in errors))

    def test_validator_reports_altitude_and_controlled_value_errors(self) -> None:
        profiles = copy.deepcopy(self.profiles)
        profile = profiles["species_profiles"][0]
        profile["taxonomy_status"] = "made_up_status"
        profile["topography"]["altitude_optimal_min_m"] = 2500
        profile["topography"]["altitude_optimal_max_m"] = 1200

        messages = self.validate_temp_dataset(profiles=profiles)
        errors = [message.format() for message in messages if message.severity == "ERROR"]

        self.assertTrue(any("taxonomy_status" in message for message in errors))
        self.assertTrue(any("altitude_optimal_max_m" in message for message in errors))


if __name__ == "__main__":
    unittest.main()
