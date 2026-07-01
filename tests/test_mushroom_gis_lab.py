import unittest
from pathlib import Path
from unittest.mock import patch

from rainmapper_core import mushroom_gis_lab


class MushroomGisLabTests(unittest.TestCase):
    def test_default_output_path_accepts_explicit_reconstruction_path(self):
        configured_path = "/share/rainmapper/mushroom-lab/custom/reconstruction.json"

        with patch.dict("os.environ", {"RAINMAPPER_MUSHROOM_GIS_RECONSTRUCTION_PATH": configured_path}, clear=False):
            self.assertEqual(mushroom_gis_lab.default_output_path(), Path(configured_path))

    def test_default_output_path_uses_configured_lab_dir(self):
        lab_dir = "/share/rainmapper/mushroom-lab"

        with patch.dict(
            "os.environ",
            {
                "RAINMAPPER_MUSHROOM_LAB_DIR": lab_dir,
                "RAINMAPPER_MUSHROOM_GIS_RECONSTRUCTION_PATH": "",
            },
            clear=False,
        ):
            self.assertEqual(
                mushroom_gis_lab.default_output_path(),
                Path(lab_dir) / "working" / "features" / "gis_observation_reconstruction.json",
            )

    def test_geology_lithology_suggestion_uses_catalog_ids(self):
        gis_payload = {
            "batch_suggestion_rules": [
                {
                    "rule_id": "geology_lithology",
                    "source_id": "geology_50000",
                    "field": "Codi",
                    "match_fields": ["Descripcio"],
                    "source_section": "lithology_mappings",
                    "auto_accept_confidences": ["high"],
                }
            ],
            "lithology_mappings": [
                {
                    "source_patterns": ["calcària", "calcàries", "limestone"],
                    "mapped_lithology_ids": ["lith_limestone"],
                    "mapped_soil_tendency_ids": ["soil_calcareous"],
                    "confidence": "high",
                }
            ]
        }
        catalogs_payload = {
            "catalogs": {
                "lithology_types": [{"id": "lith_limestone"}],
                "soil_types": [{"id": "soil_calcareous"}],
            }
        }
        properties = {
            "Codi": "TCL",
            "Descripcio": "Calcàries bioclàstiques",
            "Descripcio_metamorfisme": "",
            "Codi_protolit": "",
            "Descripcio_protolit": "",
        }

        suggestion = mushroom_gis_lab.suggested_batch_mapping(
            "geology_50000",
            "Codi",
            properties,
            gis_payload,
            catalogs_payload,
        )

        self.assertEqual(suggestion["suggested_mapped_lithology_ids"], ["lith_limestone"])
        self.assertEqual(suggestion["suggested_mapped_soil_tendency_ids"], ["soil_calcareous"])
        self.assertEqual(suggestion["suggested_confidence"], "high")
        self.assertEqual(suggestion["suggested_review_status"], "accepted")
        self.assertEqual(suggestion["suggestion_source"], "lithology_mappings")

    def test_batch_suggestion_medium_confidence_remains_pending_review(self):
        gis_payload = {
            "batch_suggestion_rules": [
                {
                    "rule_id": "mvc50_substrate_alluvial",
                    "source_id": "mvc50",
                    "field": "LLVA_Subst",
                    "raw_values": ["Al·luvial"],
                    "mapped_lithology_ids": ["lith_alluvial"],
                    "confidence": "medium",
                    "auto_accept_confidences": ["high"],
                }
            ]
        }
        catalogs_payload = {"catalogs": {"lithology_types": [{"id": "lith_alluvial"}]}}

        suggestion = mushroom_gis_lab.suggested_batch_mapping(
            "mvc50",
            "LLVA_Subst",
            {"LLVA_Subst": "Al·luvial"},
            gis_payload,
            catalogs_payload,
        )

        self.assertEqual(suggestion["suggested_mapped_lithology_ids"], ["lith_alluvial"])
        self.assertEqual(suggestion["suggested_confidence"], "medium")
        self.assertEqual(suggestion["suggested_review_status"], "pending_review")

    def test_geology_lithology_suggestion_ignores_unknown_catalog_ids(self):
        gis_payload = {
            "batch_suggestion_rules": [
                {
                    "rule_id": "geology_lithology",
                    "source_id": "geology_50000",
                    "field": "Codi",
                    "match_fields": ["Descripcio"],
                    "source_section": "lithology_mappings",
                }
            ],
            "lithology_mappings": [
                {
                    "source_patterns": ["basalt"],
                    "mapped_lithology_ids": ["lith_missing"],
                    "confidence": "high",
                }
            ]
        }
        catalogs_payload = {"catalogs": {"lithology_types": []}}

        suggestion = mushroom_gis_lab.suggested_batch_mapping(
            "geology_50000",
            "Codi",
            {"Descripcio": "Basalts"},
            gis_payload,
            catalogs_payload,
        )

        self.assertEqual(suggestion, {})

    def test_exact_batch_suggestion_rule_uses_raw_value(self):
        gis_payload = {
            "batch_suggestion_rules": [
                {
                    "rule_id": "mvc50_substrate_siliceous",
                    "source_id": "mvc50",
                    "field": "LLVA_Subst",
                    "raw_values": ["Silici"],
                    "mapped_soil_tendency_ids": ["soil_siliceous"],
                    "confidence": "high",
                }
            ]
        }
        catalogs_payload = {"catalogs": {"soil_types": [{"id": "soil_siliceous"}]}}

        suggestion = mushroom_gis_lab.suggested_batch_mapping(
            "mvc50",
            "LLVA_Subst",
            {"LLVA_Subst": "Silici"},
            gis_payload,
            catalogs_payload,
        )

        self.assertEqual(suggestion["suggested_mapped_soil_tendency_ids"], ["soil_siliceous"])
        self.assertEqual(suggestion["suggested_confidence"], "high")


if __name__ == "__main__":
    unittest.main()
