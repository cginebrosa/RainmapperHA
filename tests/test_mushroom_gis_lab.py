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

    def test_mvc50_carrascar_exact_mapping_projects_to_v0_context(self):
        gis_payload = {
            "exact_value_mappings": [
                {
                    "source_id": "mvc50",
                    "field": "LLVA_niv2t",
                    "raw_value": "Carrascars",
                    "mapped_host_ids": ["host_quercus_ilex"],
                    "mapped_forest_type_ids": ["forest_holm_oak", "forest_mediterranean_oak"],
                    "mapped_habitat_feature_ids": ["feature_open_warm_woodland"],
                    "confidence": "high",
                    "review_status": "accepted",
                },
                {
                    "source_id": "mvc50",
                    "field": "LLFISCAT_t",
                    "raw_value": "Matollars (inclou bosquines, avellanoses, sargars, canyars…)",
                    "mapped_habitat_feature_ids": ["feature_mediterranean_shrubland"],
                    "confidence": "medium",
                    "review_status": "accepted",
                },
            ]
        }
        catalogs_payload = {
            "catalogs": {
                "host_taxa": [{"id": "host_quercus_ilex"}],
                "forest_types": [{"id": "forest_holm_oak"}, {"id": "forest_mediterranean_oak"}],
                "habitat_features": [{"id": "feature_open_warm_woodland"}, {"id": "feature_mediterranean_shrubland"}],
            }
        }
        layer_result = {
            "status": "ok",
            "properties": {
                "LLVA_niv2t": "Carrascars",
                "LLFISCAT_t": "Matollars (inclou bosquines, avellanoses, sargars, canyars…)",
            },
        }

        mapped = mushroom_gis_lab.apply_exact_layer_mappings("mvc50", layer_result, gis_payload, catalogs_payload)
        context = mushroom_gis_lab.build_gis_context_v0({"layers": {"mvc50": {"status": "ok", "mapped": mapped}}})

        self.assertEqual(context["host_ids"], ["host_quercus_ilex"])
        self.assertEqual(context["forest_type_ids"], ["forest_holm_oak", "forest_mediterranean_oak"])
        self.assertEqual(
            context["habitat_feature_ids"],
            ["feature_mediterranean_shrubland", "feature_open_warm_woodland"],
        )
        self.assertFalse(context["evidence"]["has_unmapped_values"])

    def test_build_gis_context_v0_projects_only_predictor_fields(self):
        reconstruction = {
            "gaps": ["geology_50000"],
            "layers": {
                "mvc50": {
                    "status": "ok",
                    "mapped": {
                        "status": "mapped",
                        "mapped_host_ids": ["host_pinus_sylvestris"],
                        "mapped_forest_type_ids": ["forest_montane_pine"],
                        "mapped_habitat_feature_ids": ["feature_mature_forest"],
                        "mapped_lithology_ids": ["lith_limestone"],
                        "mapped_soil_tendency_ids": ["soil_siliceous"],
                    },
                },
                "geology_50000": {
                    "status": "ok",
                    "mapped": {
                        "status": "partial",
                        "mapped_soil_tendency_ids": ["soil_calcareous", "soil_basic"],
                        "pending_values": [{"raw_value": "TCL"}],
                        "unmapped_values": [{"raw_value": "ABC"}],
                    },
                },
                "dem_5m": {
                    "status": "ok",
                    "elevation_m": 1420.24,
                },
            },
        }

        context = mushroom_gis_lab.build_gis_context_v0(reconstruction)

        self.assertEqual(context["host_ids"], ["host_pinus_sylvestris"])
        self.assertEqual(context["forest_type_ids"], ["forest_montane_pine"])
        self.assertEqual(context["habitat_feature_ids"], ["feature_mature_forest"])
        self.assertEqual(context["soil_tendency_ids"], ["soil_siliceous", "soil_calcareous", "soil_basic"])
        self.assertNotIn("lithology_ids", context)
        self.assertEqual(context["altitude_m"], 1420.24)
        self.assertEqual(context["altitude_source"], "dem_5m")
        self.assertEqual(context["evidence"]["source_layers"], ["mvc50", "geology_50000"])
        self.assertTrue(context["evidence"]["has_pending_values"])
        self.assertTrue(context["evidence"]["has_unmapped_values"])
        self.assertEqual(context["evidence"]["gaps"], ["geology_50000"])

    def test_reconstruct_observation_includes_gis_context_v0(self):
        layer = mushroom_gis_lab.VectorLayer(
            source_id="mvc50",
            label="MVC50",
            path=Path("missing.shp"),
            layer_name="layer",
            fields=("LLFISCAT_t",),
        )
        observation = {
            "observation_id": "obs_1",
            "species_id": "boletus_pinophilus",
            "observed_at": "2026-07-01",
            "location": {"lat": 42.0, "lon": 2.0},
        }
        layer_payload = {"status": "ok", "properties": {"LLFISCAT_t": "Pinedes de pi roig"}}
        mapped_payload = {
            "status": "mapped",
            "mapped_values": [],
            "unmapped_values": [],
            "mapped_host_ids": ["host_pinus_sylvestris"],
            "mapped_forest_type_ids": ["forest_montane_pine"],
        }

        with (
            patch.object(mushroom_gis_lab, "transform_wgs84_to_utm31", return_value=(1.0, 2.0)),
            patch.object(mushroom_gis_lab, "vector_layers", return_value=(layer,)),
            patch.object(mushroom_gis_lab, "first_vector_feature", return_value=layer_payload),
            patch.object(mushroom_gis_lab, "apply_exact_layer_mappings", return_value=mapped_payload),
            patch.object(mushroom_gis_lab, "sample_dem", return_value={"status": "ok", "elevation_m": 1200.0}),
        ):
            result = mushroom_gis_lab.reconstruct_observation(observation)

        self.assertEqual(result["status"], "complete")
        self.assertIn("gis_context_v0", result)
        self.assertEqual(result["gis_context_v0"]["host_ids"], ["host_pinus_sylvestris"])
        self.assertEqual(result["gis_context_v0"]["forest_type_ids"], ["forest_montane_pine"])
        self.assertEqual(result["gis_context_v0"]["altitude_m"], 1200.0)


if __name__ == "__main__":
    unittest.main()
