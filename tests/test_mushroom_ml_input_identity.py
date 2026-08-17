from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

from rainmapper_core.mushroom_ml_input_identity import (
    known_sites_semantic_identity,
)


CONTRACT = {
    "id": "fixture_identity_v1",
    "collections": [
        {
            "path": "micro_areas",
            "id_field": "micro_area_id",
            "group_field": "area_id",
            "fields": [
                "micro_area_id",
                "area_id",
                "representative_location.lat",
                "representative_location.lon",
                "derived_context.gis_dem.altitude_mean_m",
            ],
        }
    ],
}


def known_sites() -> dict:
    return {
        "micro_areas": [
            {
                "micro_area_id": "a1",
                "area_id": "a",
                "name": "Name does not affect ML",
                "representative_location": {"lat": 42.0, "lon": 1.0},
                "derived_context": {"gis_dem": {"altitude_mean_m": 700.0}},
            },
            {
                "micro_area_id": "b1",
                "area_id": "b",
                "name": "B",
                "representative_location": {"lat": 43.0, "lon": 2.0},
                "derived_context": {"gis_dem": {"altitude_mean_m": 900.0}},
            },
        ]
    }


class MushroomMLInputIdentityTests(TestCase):
    def test_non_predictive_edit_does_not_change_identity(self) -> None:
        original = known_sites()
        changed = deepcopy(original)
        changed["micro_areas"][0]["name"] = "Renamed"
        changed["micro_areas"][0]["notes"] = "UI-only note"

        self.assertEqual(
            known_sites_semantic_identity(original, CONTRACT),
            known_sites_semantic_identity(changed, CONTRACT),
        )

    def test_altitude_edit_changes_only_affected_area_and_global_identity(self) -> None:
        original = known_sites()
        changed = deepcopy(original)
        changed["micro_areas"][0]["derived_context"]["gis_dem"][
            "altitude_mean_m"
        ] = 710.0
        before = known_sites_semantic_identity(original, CONTRACT)
        after = known_sites_semantic_identity(changed, CONTRACT)

        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertNotEqual(before["area_sha256"]["a"], after["area_sha256"]["a"])
        self.assertEqual(before["area_sha256"]["b"], after["area_sha256"]["b"])

    def test_new_area_does_not_change_existing_area_identities(self) -> None:
        original = known_sites()
        changed = deepcopy(original)
        changed["micro_areas"].append(
            {
                "micro_area_id": "c1",
                "area_id": "c",
                "representative_location": {"lat": 44.0, "lon": 3.0},
                "derived_context": {"gis_dem": {"altitude_mean_m": 500.0}},
            }
        )
        before = known_sites_semantic_identity(original, CONTRACT)
        after = known_sites_semantic_identity(changed, CONTRACT)

        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertEqual(before["area_sha256"]["a"], after["area_sha256"]["a"])
        self.assertEqual(before["area_sha256"]["b"], after["area_sha256"]["b"])
        self.assertIn("c", after["area_sha256"])
