import json
import unittest
from pathlib import Path

from rainmapper_core.mushroom_profile_v0 import (
    PARKED_V0_PROFILE_FIELDS,
    project_profile_v0,
    project_profiles_payload_v0,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "mushroom-data"


def load_profiles():
    return json.loads((DATA_DIR / "mushroom_profiles.json").read_text(encoding="utf-8"))


class MushroomProfileV0ProjectionTests(unittest.TestCase):
    def test_projection_keeps_operational_v0_fields(self) -> None:
        payload = load_profiles()
        profile = payload["species_profiles"][0]

        projected = project_profile_v0(profile)

        self.assertEqual(profile["species_id"], projected["species_id"])
        self.assertEqual(
            profile["ecology"]["trophic_mode_id"],
            projected["ecology"]["trophic_mode_id"],
        )
        self.assertEqual(
            profile["phenology"]["main_months"],
            projected["phenology"]["main_months"],
        )
        self.assertEqual(
            profile["topography"]["altitude_min_m"],
            projected["topography"]["altitude_min_m"],
        )
        self.assertEqual(
            profile["topography"]["altitude_max_m"],
            projected["topography"]["altitude_max_m"],
        )

    def test_projection_does_not_promote_rich_numeric_model_fields(self) -> None:
        payload = load_profiles()
        projected = project_profile_v0(payload["species_profiles"][0])

        self.assertNotIn("weather_model", projected)
        self.assertNotIn("scoring_weights", projected)
        self.assertFalse(projected["v0_model_status"]["numeric_weather_model_active"])
        self.assertFalse(projected["v0_model_status"]["scoring_weights_active"])
        self.assertIn("weather_model", projected["parked_profile_fields"])
        self.assertIn("scoring_weights", projected["parked_profile_fields"])

    def test_projection_keeps_affinity_relationships_without_numeric_weights(self) -> None:
        payload = load_profiles()
        projected = project_profile_v0(payload["species_profiles"][0])

        host_affinities = projected["ecology"]["host_affinities"]
        self.assertGreater(len(host_affinities), 0)
        self.assertEqual({"id", "relationship"}, set(host_affinities[0]))
        self.assertNotIn("affinity", host_affinities[0])

    def test_projection_ignores_legacy_inactive_affinities(self) -> None:
        payload = load_profiles()
        profile = next(
            profile
            for profile in payload["species_profiles"]
            if profile["species_id"] == "boletus_pinophilus"
        )

        projected = project_profile_v0(profile)
        projected_host_ids = {
            item["id"] for item in projected["ecology"]["host_affinities"]
        }

        self.assertNotIn("host_picea_spp", projected_host_ids)

    def test_projection_parks_lithology_for_v0(self) -> None:
        payload = load_profiles()
        projected = project_profile_v0(payload["species_profiles"][0])

        self.assertNotIn("lithology_affinities", projected["ecology"])
        self.assertIn("ecology.lithology_affinities", projected["parked_profile_fields"])

    def test_payload_projection_declares_active_and_parked_fields(self) -> None:
        payload = load_profiles()
        projected = project_profiles_payload_v0(payload)

        self.assertEqual("0.1", projected["schema_version"])
        self.assertEqual(payload["schema_version"], projected["source_profile_schema_version"])
        self.assertEqual(len(payload["species_profiles"]), len(projected["species_profiles"]))
        self.assertEqual(list(PARKED_V0_PROFILE_FIELDS), projected["parked_profile_fields"])
        self.assertIn("ecology.host_affinities", projected["active_profile_fields"])
        self.assertIn("weather_model", projected["parked_profile_fields"])


if __name__ == "__main__":
    unittest.main()
