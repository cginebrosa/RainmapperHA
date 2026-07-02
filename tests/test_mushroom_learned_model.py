import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_learned_model


class MushroomLearnedModelTests(unittest.TestCase):
    def test_build_learned_model_summarizes_observation_features(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            features_path = Path(temp_dir) / "observation_features_v0.json"
            features_path.write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "observation_id": "obs_1",
                                "species_id": "boletus_aereus",
                                "analysis_result": "present",
                                "validation_status": "valid",
                                "calibration_use": "include",
                                "host_ids": ["host_quercus_ilex"],
                                "forest_type_ids": ["forest_holm_oak"],
                                "soil_tendency_ids": ["soil_calcareous"],
                                "habitat_feature_ids": ["feature_open_warm_woodland"],
                                "rain_14d_mm": 20.0,
                                "gis_altitude_m": 650.0,
                            },
                            {
                                "observation_id": "obs_2",
                                "species_id": "boletus_aereus",
                                "analysis_result": "absent",
                                "validation_status": "valid",
                                "calibration_use": "include",
                                "host_ids": ["host_quercus_ilex"],
                                "forest_type_ids": ["forest_holm_oak"],
                                "soil_tendency_ids": ["soil_calcareous"],
                                "habitat_feature_ids": ["feature_open_warm_woodland"],
                                "rain_14d_mm": 2.0,
                                "gis_altitude_m": 680.0,
                            },
                            {
                                "observation_id": "obs_3",
                                "species_id": "boletus_aereus",
                                "analysis_result": "present",
                                "validation_status": "valid",
                                "calibration_use": "include",
                                "host_ids": ["host_quercus_suber"],
                                "rain_14d_mm": 30.0,
                                "gis_altitude_m": 700.0,
                                "weather_gaps": ["wind_no_data_7d"],
                            },
                            {
                                "observation_id": "obs_4",
                                "species_id": "boletus_aereus",
                                "analysis_result": "present",
                                "validation_status": "draft",
                                "calibration_use": "include",
                                "host_ids": ["host_pinus_sylvestris"],
                                "rain_14d_mm": 200.0,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payload = mushroom_learned_model.build_learned_model_v0(features_path)
            model = payload["species_models"][0]
            hosts = {item["id"]: item for item in model["categorical_features"]["hosts"]}
            altitude = model["numeric_features"]["altitude_m"]
            rain = model["numeric_features"]["rain_14d_mm"]

            self.assertEqual(payload["summary"]["observations"], 3)
            self.assertEqual(payload["summary"]["source_observations"], 4)
            self.assertEqual(payload["summary"]["excluded_observations"], 1)
            self.assertEqual(model["positive_count"], 2)
            self.assertEqual(model["negative_count"], 1)
            self.assertEqual(model["weather_gap_count"], 1)
            self.assertEqual(hosts["host_quercus_ilex"]["positive_support"], 1)
            self.assertEqual(hosts["host_quercus_ilex"]["negative_support"], 1)
            self.assertNotIn("host_pinus_sylvestris", hosts)
            self.assertEqual(altitude["positive"]["min"], 650.0)
            self.assertEqual(altitude["positive"]["max"], 700.0)
            self.assertEqual(rain["positive"]["mean"], 25.0)

    def test_build_and_write_learned_model_outputs_json_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            features_path = root / "features.json"
            output_json = root / "model.json"
            report = root / "model.md"
            features_path.write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "observation_id": "obs_1",
                                "species_id": "x",
                                "analysis_result": "present",
                                "validation_status": "valid",
                                "calibration_use": "include",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payload = mushroom_learned_model.build_and_write_learned_model_v0(
                features_path=features_path,
                output_json_path=output_json,
                report_path=report,
            )

            self.assertTrue(output_json.exists())
            self.assertTrue(report.exists())
            self.assertEqual(payload["output_paths"]["json"], str(output_json))
            self.assertIn("Mushroom Learned Model v0", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
