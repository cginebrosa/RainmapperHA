import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BUILDER_SCRIPT = ROOT_DIR / "scripts" / "build-mushroom-profile-v0-candidate.py"
VALIDATOR_SCRIPT = ROOT_DIR / "scripts" / "validate-mushroom-data.py"
DATA_DIR = ROOT_DIR / "mushroom-data"


def load_script_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = load_script_module("build_mushroom_profile_v0_candidate", BUILDER_SCRIPT)
VALIDATOR = load_script_module("validate_mushroom_data_for_v0_candidate", VALIDATOR_SCRIPT)


def load_json(relative_path: str):
    return json.loads((ROOT_DIR / relative_path).read_text(encoding="utf-8"))


def write_dataset(target: Path, profiles, catalogs, gis, observations) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "mushroom_profiles.json").write_text(
        json.dumps(profiles, indent=2), encoding="utf-8"
    )
    (target / "mushroom_reference_catalogs.json").write_text(
        json.dumps(catalogs, indent=2), encoding="utf-8"
    )
    (target / "mushroom_gis_mappings.json").write_text(json.dumps(gis, indent=2), encoding="utf-8")
    (target / "mushroom_observations.json").write_text(
        json.dumps(observations, indent=2), encoding="utf-8"
    )


class MushroomProfileV0CandidateBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profiles = load_json("mushroom-data/mushroom_profiles.json")
        self.catalogs = load_json("mushroom-data/mushroom_reference_catalogs.json")
        self.gis = load_json("mushroom-data/mushroom_gis_mappings.json")
        self.observations = load_json("mushroom-data/mushroom_observations.json")
        self.source = load_json("docs/mushrooms/literature/marc-estevez-v0-source-normalized.json")

    def test_candidate_builds_21_profiles_with_all_source_species_promoted(self) -> None:
        candidate = BUILDER.build_candidate_profiles(self.profiles, self.source)

        species_ids = {profile["species_id"] for profile in candidate["species_profiles"]}
        original_ids = {profile["species_id"] for profile in self.profiles["species_profiles"]}
        new_ids = species_ids - original_ids

        self.assertEqual(21, len(species_ids))
        self.assertEqual(0, len(new_ids))
        self.assertIn("lactarius_salmonicolor_quieticolor_group", species_ids)
        self.assertNotIn("lactarius_salmonicolor", new_ids)
        self.assertNotIn("lactarius_quieticolor", new_ids)

    def test_candidate_uses_placeholders_only_for_schema_compatibility(self) -> None:
        candidate = BUILDER.build_candidate_profiles(self.profiles, self.source)
        lactarius = next(
            profile
            for profile in candidate["species_profiles"]
            if profile["species_id"] == "lactarius_deliciosus"
        )

        self.assertEqual("updated_existing", lactarius["metadata"]["v0_candidate_kind"])
        self.assertIn("Numeric affinities marked v0_placeholder", lactarius["prediction_confidence"]["notes"])
        host_affinities = lactarius["ecology"]["host_affinities"]
        self.assertTrue(any(item.get("v0_placeholder") for item in host_affinities))
        self.assertTrue(all("affinity" in item for item in host_affinities))

    def test_candidate_profiles_validate_without_errors_against_current_catalogs(self) -> None:
        candidate = BUILDER.build_candidate_profiles(self.profiles, self.source)

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            write_dataset(
                target,
                copy.deepcopy(candidate),
                copy.deepcopy(self.catalogs),
                copy.deepcopy(self.gis),
                copy.deepcopy(self.observations),
            )
            messages = VALIDATOR.validate_mushroom_data(target)

        errors = [message for message in messages if message.severity == "ERROR"]
        self.assertEqual([], [error.format() for error in errors])

    def test_catalog_gaps_are_promoted_into_productive_catalogs(self) -> None:
        overlay = BUILDER.build_catalog_overlay(self.source, self.catalogs)

        habitat_ids = {entry["id"] for entry in self.catalogs["catalogs"]["habitat_features"]}
        host_ids = {entry["id"] for entry in self.catalogs["catalogs"]["host_taxa"]}

        self.assertIn("feature_moist_forest", habitat_ids)
        self.assertIn("feature_shaded_slope", habitat_ids)
        self.assertIn("host_corylus_avellana", host_ids)
        self.assertEqual({}, overlay["catalogs"])
        self.assertEqual([], overlay["unresolved_gap_candidates"])

    def test_promoted_catalog_gaps_are_referenced_by_profiles(self) -> None:
        candidate = BUILDER.build_candidate_profiles(
            self.profiles,
            self.source,
            include_catalog_gaps=True,
        )
        tuber = next(
            profile
            for profile in candidate["species_profiles"]
            if profile["species_id"] == "tuber_melanosporum"
        )

        host_ids = {item["id"] for item in tuber["ecology"]["host_affinities"]}
        habitat_ids = {item["id"] for item in tuber["ecology"]["habitat_feature_affinities"]}

        self.assertIn("host_corylus_avellana", host_ids)
        self.assertIn("host_quercus_faginea", host_ids)
        self.assertIn("feature_calcicolous_shrubland", habitat_ids)
        all_affinities = (
            tuber["ecology"]["host_affinities"]
            + tuber["ecology"]["habitat_feature_affinities"]
        )
        self.assertFalse(any(item.get("v0_catalog_gap_promoted") for item in all_affinities))


if __name__ == "__main__":
    unittest.main()
