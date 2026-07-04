import importlib.util
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT = ROOT_DIR / "scripts" / "apply-mushroom-literature-source.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("apply_mushroom_literature_source", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


APPLIER = load_script_module()


class MushroomLiteratureSourceApplyTests(unittest.TestCase):
    def test_marc_source_marks_listed_affinities_as_primary(self) -> None:
        profiles = {
            "species_profiles": [
                {
                    "species_id": "boletus_test",
                    "ecology": {
                        "host_affinities": [
                            {
                                "id": "host_pinus_sylvestris",
                                "relationship": "possible",
                                "affinity": 0.0,
                                "v0_placeholder": True,
                            }
                        ],
                        "forest_type_affinities": [],
                        "soil_affinities": [],
                        "habitat_feature_affinities": [],
                    },
                }
            ]
        }
        source = {
            "source_id": "marc_estevez_species_pdf_visual_review",
            "species": [
                {
                    "species_id": "boletus_test",
                    "host_ids": ["host_pinus_sylvestris"],
                    "forest_type_ids": ["forest_montane_pine"],
                    "soil_tendency_ids": [],
                    "habitat_feature_ids": [],
                    "catalog_gap_candidates": [],
                }
            ],
        }

        report = APPLIER.apply_literature_source(profiles, source)
        ecology = profiles["species_profiles"][0]["ecology"]

        self.assertEqual(1, len(report["updated"]))
        self.assertEqual(1, len(report["added"]))
        self.assertEqual("primary", ecology["host_affinities"][0]["relationship"])
        self.assertEqual(["literature_marc_estevez"], ecology["host_affinities"][0]["source_ids"])
        self.assertEqual("primary", ecology["forest_type_affinities"][0]["relationship"])
        self.assertTrue(ecology["forest_type_affinities"][0]["v0_placeholder"])

    def test_source_reactivates_parked_affinity_without_touching_other_fields(self) -> None:
        profiles = {
            "species_profiles": [
                {
                    "species_id": "boletus_test",
                    "ecology": {
                        "host_affinities": [
                            {
                                "id": "host_pinus_sylvestris",
                                "relationship": "secondary",
                                "affinity": 0.4,
                                "v0_active": False,
                                "notes": "manual note",
                            }
                        ],
                    },
                }
            ]
        }
        source = {
            "source_id": "literature_custom",
            "species": [{"species_id": "boletus_test", "host_ids": ["host_pinus_sylvestris"]}],
        }

        APPLIER.apply_literature_source(profiles, source)
        item = profiles["species_profiles"][0]["ecology"]["host_affinities"][0]

        self.assertEqual("primary", item["relationship"])
        self.assertEqual(0.4, item["affinity"])
        self.assertNotIn("v0_active", item)
        self.assertEqual("manual note", item["notes"])
        self.assertEqual(["literature_custom"], item["source_ids"])


if __name__ == "__main__":
    unittest.main()
