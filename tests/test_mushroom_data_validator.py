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


def write_dataset(target: Path, profiles, catalogs, gis, observations) -> None:
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
    (target / "mushroom_observations.json").write_text(
        json.dumps(observations, indent=2), encoding="utf-8"
    )


class MushroomDataValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profiles = load_json("mushroom_profiles.json")
        self.catalogs = load_json("mushroom_reference_catalogs.json")
        self.gis = load_json("mushroom_gis_mappings.json")
        self.observations = load_json("mushroom_observations.json")

    def validate_temp_dataset(self, profiles=None, catalogs=None, gis=None, observations=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            write_dataset(
                target,
                copy.deepcopy(profiles if profiles is not None else self.profiles),
                copy.deepcopy(catalogs if catalogs is not None else self.catalogs),
                copy.deepcopy(gis if gis is not None else self.gis),
                copy.deepcopy(observations if observations is not None else self.observations),
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

    def test_validator_reports_duplicate_profile_values_and_month_overlap(self) -> None:
        profiles = copy.deepcopy(self.profiles)
        profile = profiles["species_profiles"][0]
        profile["phenology"]["main_months"] = [8, 9, 9]
        profile["phenology"]["secondary_months"] = [7, 8]
        profile["topography"]["preferred_aspect_ids"] = ["aspect_N", "aspect_N"]
        profile["ecology"]["host_affinities"].append(
            copy.deepcopy(profile["ecology"]["host_affinities"][0])
        )

        messages = self.validate_temp_dataset(profiles=profiles)
        errors = [message.format() for message in messages if message.severity == "ERROR"]

        self.assertTrue(any("main_months and secondary_months overlap: 8" in message for message in errors))
        self.assertTrue(any("phenology.main_months" in message and "duplicate values: 9" in message for message in errors))
        self.assertTrue(any("preferred_aspect_ids" in message and "duplicate values: aspect_N" in message for message in errors))
        self.assertTrue(any("host_affinities" in message and "duplicate IDs" in message for message in errors))

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

    def test_validator_accepts_observation_catalog_references(self) -> None:
        observations = copy.deepcopy(self.observations)
        observations["observations"] = [
            {
                "observation_id": "obs_20260629_0001",
                "species_id": self.profiles["species_profiles"][0]["species_id"],
                "observed_at": "2026-06-29",
                "location": {
                    "input": "41.3874, 2.1686",
                    "lat": 41.3874,
                    "lon": 2.1686,
                    "source": "manual_decimal",
                    "precision_m": 50,
                },
                "altitude": {"meters": 120, "source": "manual"},
                "flush_abundance": "abundant",
                "observer": {"name": "Unit Test", "expertise": "experienced"},
                "source": {"type": "personal_observation", "label": "field note"},
                "source_quality": 0.9,
                "validation_status": "valid",
                "calibration_use": "include",
                "metadata": {
                    "created_at": "2026-06-29",
                    "updated_at": "2026-06-29",
                    "created_by": "unit_test",
                    "updated_by": "unit_test",
                },
            }
        ]

        messages = self.validate_temp_dataset(observations=observations)
        errors = [message.format() for message in messages if message.severity == "ERROR"]

        self.assertEqual([], errors)

    def test_validator_reports_observation_unknown_species_and_catalog_ids(self) -> None:
        observations = copy.deepcopy(self.observations)
        observations["observations"] = [
            {
                "observation_id": "obs_20260629_0001",
                "species_id": "missing_species",
                "observed_at": "2026-06-29",
                "location": {
                    "input": "41.3874, 2.1686",
                    "lat": 41.3874,
                    "lon": 2.1686,
                    "source": "unknown_location_source",
                },
                "flush_abundance": "made_up_abundance",
                "source_quality": 1.2,
                "validation_status": "valid",
                "calibration_use": "include",
                "metadata": {
                    "created_at": "2026-06-29",
                    "updated_at": "2026-06-29",
                    "created_by": "unit_test",
                    "updated_by": "unit_test",
                },
            }
        ]

        messages = self.validate_temp_dataset(observations=observations)
        errors = [message.format() for message in messages if message.severity == "ERROR"]

        self.assertTrue(any("missing_species" in message for message in errors))
        self.assertTrue(any("unknown_location_source" in message for message in errors))
        self.assertTrue(any("made_up_abundance" in message for message in errors))
        self.assertTrue(any("source_quality" in message for message in errors))


if __name__ == "__main__":
    unittest.main()
