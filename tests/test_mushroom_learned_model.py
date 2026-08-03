import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_learned_model


class MushroomLearnedModelTests(unittest.TestCase):
    def test_scarce_observation_is_learned_as_unfavorable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            features_path = Path(temp_dir) / "observation_features_v0.json"
            features_path.write_text(
                json.dumps(
                    {
                        "prediction_target_policy": {
                            "version": "catalog_prediction_favorable_v1",
                            "mapping": {"normal": 1, "scarce": 0},
                        },
                        "rows": [
                            {
                                "observation_id": "obs_normal",
                                "species_id": "boletus_aereus",
                                "micro_area_id": "area_a",
                                "observed_at": "2023-10-15T10:00:00",
                                "analysis_result": "present",
                                "prediction_target": "favorable",
                                "flush_abundance": "normal",
                                "validation_status": "valid",
                                "calibration_use": "include",
                            },
                            {
                                "observation_id": "obs_scarce",
                                "species_id": "boletus_aereus",
                                "micro_area_id": "area_b",
                                "observed_at": "2023-10-16T10:00:00",
                                "analysis_result": "present",
                                "prediction_target": "unfavorable",
                                "flush_abundance": "scarce",
                                "validation_status": "valid",
                                "calibration_use": "include",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payload = mushroom_learned_model.build_learned_model_v0(features_path)
            model = payload["species_models"][0]

            self.assertEqual(model["favorable_count"], 1)
            self.assertEqual(model["unfavorable_count"], 1)
            self.assertEqual(payload["summary"]["favorable_observations"], 1)
            self.assertEqual(payload["summary"]["unfavorable_observations"], 1)
            self.assertEqual(payload["feature_contract"]["target"], "prediction_target")
            self.assertEqual(payload["prediction_target_policy"]["version"], "catalog_prediction_favorable_v1")
            self.assertEqual(payload["prediction_target_policy"]["mapping"]["scarce"], 0)

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
                                "micro_area_id": "area_a",
                                "observed_at": "2023-10-15T10:00:00",
                                "analysis_result": "present",
                                "validation_status": "valid",
                                "calibration_use": "include",
                                "host_ids": ["host_quercus_ilex"],
                                "host_sources": {"host_quercus_ilex": ["field", "gis"]},
                                "forest_type_ids": ["forest_holm_oak"],
                                "soil_tendency_ids": ["soil_calcareous"],
                                "habitat_feature_ids": ["feature_open_warm_woodland"],
                                "rain_14d_mm": 20.0,
                                "gis_altitude_m": 650.0,
                            },
                            {
                                "observation_id": "obs_2",
                                "species_id": "boletus_aereus",
                                "micro_area_id": "area_b",
                                "observed_at": "2023-10-16T10:00:00",
                                "analysis_result": "absent",
                                "validation_status": "valid",
                                "calibration_use": "include",
                                "host_ids": ["host_quercus_ilex"],
                                "host_sources": {"host_quercus_ilex": ["gis"]},
                                "forest_type_ids": ["forest_holm_oak"],
                                "soil_tendency_ids": ["soil_calcareous"],
                                "habitat_feature_ids": ["feature_open_warm_woodland"],
                                "rain_14d_mm": 2.0,
                                "gis_altitude_m": 680.0,
                            },
                            {
                                "observation_id": "obs_3",
                                "species_id": "boletus_aereus",
                                "micro_area_id": "area_c",
                                "observed_at": "2023-10-17T10:00:00",
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
                                "micro_area_id": "area_d",
                                "observed_at": "2023-10-18T10:00:00",
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

            self.assertEqual(payload["summary"]["episodes"], 3)
            self.assertEqual(payload["summary"]["observations"], 3)
            self.assertEqual(payload["summary"]["source_observations"], 4)
            self.assertEqual(payload["summary"]["excluded_observations"], 1)
            self.assertEqual(model["positive_count"], 2)
            self.assertEqual(model["negative_count"], 1)
            self.assertEqual(model["weather_gap_count"], 1)
            self.assertEqual(hosts["host_quercus_ilex"]["positive_support"], 1)
            self.assertEqual(hosts["host_quercus_ilex"]["negative_support"], 1)
            self.assertEqual(hosts["host_quercus_ilex"]["positive_sources"], ["field", "gis"])
            self.assertEqual(
                hosts["host_quercus_ilex"]["positive_source_support"],
                {"field": 1, "gis": 1},
            )
            self.assertEqual(hosts["host_quercus_ilex"]["negative_sources"], ["gis"])
            self.assertEqual(hosts["host_quercus_ilex"]["negative_source_support"], {"gis": 1})
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
            progress: list[tuple[int, str]] = []
            features_path.write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "observation_id": "obs_1",
                                "species_id": "x",
                                "micro_area_id": "area_a",
                                "observed_at": "2023-10-15T10:00:00",
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
                progress_callback=lambda percent, message: progress.append((percent, message)),
            )

            self.assertTrue(output_json.exists())
            self.assertTrue(report.exists())
            self.assertEqual(payload["output_paths"]["json"], str(output_json))
            self.assertIn("Mushroom Learned Model v0", report.read_text(encoding="utf-8"))
            self.assertEqual(100, progress[-1][0])
            self.assertEqual([item[0] for item in progress], sorted(item[0] for item in progress))
            self.assertTrue(any("variable" in message for _percent, message in progress))
            self.assertTrue(any("JSON" in message for _percent, message in progress))

    def test_build_and_write_species_learned_model_replaces_only_selected_species(self) -> None:
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
                                "species_id": "amanita_caesarea",
                                "micro_area_id": "area_a",
                                "observed_at": "2023-10-15T10:00:00",
                                "analysis_result": "present",
                                "validation_status": "valid",
                                "calibration_use": "include",
                                "host_ids": ["host_quercus_ilex"],
                            },
                            {
                                "observation_id": "obs_2",
                                "species_id": "boletus_aereus",
                                "micro_area_id": "area_b",
                                "observed_at": "2023-10-15T10:00:00",
                                "analysis_result": "present",
                                "validation_status": "valid",
                                "calibration_use": "include",
                                "host_ids": ["host_quercus_suber"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            mushroom_learned_model.build_and_write_learned_model_v0(
                features_path=features_path,
                output_json_path=output_json,
                report_path=report,
            )
            updated_rows = json.loads(features_path.read_text(encoding="utf-8"))["rows"]
            updated_rows[0]["host_ids"] = ["host_castanea_sativa"]
            features_path.write_text(json.dumps({"rows": updated_rows}), encoding="utf-8")

            payload = mushroom_learned_model.build_and_write_species_learned_model_v0(
                "amanita_caesarea",
                features_path=features_path,
                output_json_path=output_json,
                report_path=report,
            )
            models = {model["species_id"]: model for model in payload["species_models"]}
            amanita_hosts = {
                item["id"]
                for item in models["amanita_caesarea"]["categorical_features"]["hosts"]
            }
            boletus_hosts = {
                item["id"]
                for item in models["boletus_aereus"]["categorical_features"]["hosts"]
            }

            self.assertEqual(amanita_hosts, {"host_castanea_sativa"})
            self.assertEqual(boletus_hosts, {"host_quercus_suber"})
            self.assertEqual(payload["last_species_rebuild"]["species_id"], "amanita_caesarea")

    def test_episode_consolidation_same_day_same_area(self) -> None:
        """Two obs same day/area/species → 1 episode; favorable wins."""
        with tempfile.TemporaryDirectory() as temp_dir:
            features_path = Path(temp_dir) / "features.json"
            features_path.write_text(
                json.dumps({
                    "rows": [
                        {
                            "observation_id": "obs_a",
                            "species_id": "boletus_aereus",
                            "micro_area_id": "olvan_north",
                            "observed_at": "2023-10-15T10:00:00",
                            "prediction_target": "unfavorable",
                            "validation_status": "valid",
                            "calibration_use": "include",
                            "host_ids": ["host_quercus_ilex"],
                            "host_sources": {"host_quercus_ilex": ["field"]},
                        },
                        {
                            "observation_id": "obs_b",
                            "species_id": "boletus_aereus",
                            "micro_area_id": "olvan_north",
                            "observed_at": "2023-10-15T16:00:00",
                            "prediction_target": "favorable",
                            "validation_status": "valid",
                            "calibration_use": "include",
                            "host_ids": ["host_quercus_suber"],
                            "host_sources": {"host_quercus_suber": ["gis"]},
                        },
                    ]
                }),
                encoding="utf-8",
            )
            payload = mushroom_learned_model.build_learned_model_v0(features_path)
            model = payload["species_models"][0]
            self.assertEqual(payload["summary"]["episodes"], 1)
            self.assertEqual(payload["summary"]["favorable_observations"], 1)
            self.assertEqual(payload["summary"]["unfavorable_observations"], 0)
            self.assertEqual(model["episode_count"], 1)
            self.assertEqual(model["favorable_count"], 1)
            hosts = {item["id"] for item in model["categorical_features"]["hosts"]}
            self.assertIn("host_quercus_ilex", hosts)
            self.assertIn("host_quercus_suber", hosts)

    def test_episode_consolidation_different_days_are_separate_episodes(self) -> None:
        """Same area/species but different days → 2 independent episodes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            features_path = Path(temp_dir) / "features.json"
            features_path.write_text(
                json.dumps({
                    "rows": [
                        {
                            "observation_id": "obs_a",
                            "species_id": "boletus_aereus",
                            "micro_area_id": "olvan_north",
                            "observed_at": "2023-10-15T10:00:00",
                            "prediction_target": "favorable",
                            "validation_status": "valid",
                            "calibration_use": "include",
                        },
                        {
                            "observation_id": "obs_b",
                            "species_id": "boletus_aereus",
                            "micro_area_id": "olvan_north",
                            "observed_at": "2023-10-22T10:00:00",
                            "prediction_target": "unfavorable",
                            "validation_status": "valid",
                            "calibration_use": "include",
                        },
                    ]
                }),
                encoding="utf-8",
            )
            payload = mushroom_learned_model.build_learned_model_v0(features_path)
            self.assertEqual(payload["summary"]["episodes"], 2)
            self.assertEqual(payload["summary"]["favorable_observations"], 1)
            self.assertEqual(payload["summary"]["unfavorable_observations"], 1)

    def test_episode_consolidation_no_area_excluded(self) -> None:
        """Obs without micro_area_id are excluded from training."""
        with tempfile.TemporaryDirectory() as temp_dir:
            features_path = Path(temp_dir) / "features.json"
            features_path.write_text(
                json.dumps({
                    "rows": [
                        {
                            "observation_id": "obs_with_area",
                            "species_id": "boletus_aereus",
                            "micro_area_id": "olvan_north",
                            "observed_at": "2023-10-15T10:00:00",
                            "prediction_target": "favorable",
                            "validation_status": "valid",
                            "calibration_use": "include",
                        },
                        {
                            "observation_id": "obs_no_area",
                            "species_id": "boletus_aereus",
                            "micro_area_id": None,
                            "observed_at": "2023-10-16T10:00:00",
                            "prediction_target": "favorable",
                            "validation_status": "valid",
                            "calibration_use": "include",
                        },
                    ]
                }),
                encoding="utf-8",
            )
            payload = mushroom_learned_model.build_learned_model_v0(features_path)
            self.assertEqual(payload["summary"]["episodes"], 1)
            self.assertEqual(payload["summary"]["excluded_no_area"], 1)

    def test_episode_consolidation_different_areas_same_day_are_separate(self) -> None:
        """Same species/day but different micro_area_id → 2 episodes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            features_path = Path(temp_dir) / "features.json"
            features_path.write_text(
                json.dumps({
                    "rows": [
                        {
                            "observation_id": "obs_north",
                            "species_id": "boletus_aereus",
                            "micro_area_id": "olvan_north",
                            "observed_at": "2023-10-15T10:00:00",
                            "prediction_target": "favorable",
                            "validation_status": "valid",
                            "calibration_use": "include",
                        },
                        {
                            "observation_id": "obs_south",
                            "species_id": "boletus_aereus",
                            "micro_area_id": "olvan_south",
                            "observed_at": "2023-10-15T10:00:00",
                            "prediction_target": "unfavorable",
                            "validation_status": "valid",
                            "calibration_use": "include",
                        },
                    ]
                }),
                encoding="utf-8",
            )
            payload = mushroom_learned_model.build_learned_model_v0(features_path)
            self.assertEqual(payload["summary"]["episodes"], 2)


if __name__ == "__main__":
    unittest.main()
