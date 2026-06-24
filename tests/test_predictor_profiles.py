import json
import unittest
from pathlib import Path


PROFILE_PATH = Path(__file__).resolve().parents[1] / "predictor" / "mushroom_profiles.json"

REQUIRED_PROFILE_KEYS = {
    "species_id",
    "scientific_name",
    "common_names",
    "taxonomy_status",
    "edibility",
    "ecology",
    "phenology",
    "topography",
    "weather_model",
    "scoring_weights",
    "prediction_confidence",
    "metadata",
}

REQUIRED_ECOLOGY_KEYS = {
    "trophic_mode",
    "primary_hosts",
    "secondary_hosts",
    "forest_types",
    "soil_preference",
    "soil_avoidance",
    "lithology_preference",
}

REQUIRED_PHENOLOGY_KEYS = {
    "main_months",
    "secondary_months",
    "season_pattern",
    "fruiting_delay_after_rain_days",
}

REQUIRED_TOPOGRAPHY_KEYS = {
    "altitude_min_m",
    "altitude_optimal_min_m",
    "altitude_optimal_max_m",
    "altitude_max_m",
    "preferred_aspects",
    "aspect_notes",
}

REQUIRED_WEATHER_KEYS = {
    "rainfall",
    "temperature",
    "humidity",
    "wind",
}

REQUIRED_PREDICTION_CONFIDENCE_KEYS = {
    "overall_confidence",
    "habitat_confidence",
    "topography_confidence",
    "phenology_confidence",
    "weather_threshold_confidence",
    "taxonomy_confidence",
    "local_calibration_status",
    "calibration_priority",
    "minimum_observations_for_calibration",
    "minimum_positive_observations",
    "minimum_negative_observations",
    "notes",
}

REQUIRED_METADATA_KEYS = {
    "profile_version",
    "created_at",
    "updated_at",
    "created_by",
    "review_status",
    "reviewed_by",
    "source_quality",
    "requires_human_validation",
}


class PredictorProfileTests(unittest.TestCase):
    def load_profiles(self):
        with PROFILE_PATH.open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_profile_file_is_valid_json_with_expected_top_level_shape(self):
        data = self.load_profiles()

        self.assertEqual(data["schema_version"], "0.2")
        self.assertEqual(data["model_purpose"], "mushroom_fruiting_probability_scoring")
        self.assertIsInstance(data["important_note"], str)
        self.assertIsInstance(data["controlled_values"], dict)
        self.assertIsInstance(data["species_profiles"], list)
        self.assertGreater(len(data["species_profiles"]), 0)

    def test_controlled_values_define_expected_enumerations(self):
        data = self.load_profiles()
        controlled = data["controlled_values"]

        for key in ("confidence_values", "local_calibration_status", "calibration_priority", "review_status"):
            self.assertIn(key, controlled)
            self.assertIsInstance(controlled[key], list)
            self.assertGreater(len(controlled[key]), 0)

    def test_species_profiles_have_required_sections_and_unique_ids(self):
        data = self.load_profiles()
        seen_ids = set()
        calibration_priorities = set(data["controlled_values"]["calibration_priority"])

        for profile in data["species_profiles"]:
            with self.subTest(species=profile.get("species_id")):
                self.assertTrue(REQUIRED_PROFILE_KEYS.issubset(profile.keys()))
                species_id = profile["species_id"]
                self.assertNotIn(species_id, seen_ids)
                seen_ids.add(species_id)
                self.assertIsInstance(profile["common_names"], list)
                self.assertGreater(len(profile["common_names"]), 0)
                self.assertIn(profile["prediction_confidence"]["calibration_priority"], calibration_priorities)

    def test_ecology_phenology_topography_and_weather_sections_are_complete(self):
        data = self.load_profiles()
        confidence_values = set(data["controlled_values"]["confidence_values"])

        for profile in data["species_profiles"]:
            with self.subTest(species=profile["species_id"]):
                ecology = profile["ecology"]
                phenology = profile["phenology"]
                topography = profile["topography"]
                weather = profile["weather_model"]

                self.assertTrue(REQUIRED_ECOLOGY_KEYS.issubset(ecology.keys()))
                self.assertTrue(REQUIRED_PHENOLOGY_KEYS.issubset(phenology.keys()))
                self.assertTrue(REQUIRED_TOPOGRAPHY_KEYS.issubset(topography.keys()))
                self.assertTrue(REQUIRED_WEATHER_KEYS.issubset(weather.keys()))
                self.assertTrue(REQUIRED_PREDICTION_CONFIDENCE_KEYS.issubset(profile["prediction_confidence"].keys()))
                self.assertTrue(REQUIRED_METADATA_KEYS.issubset(profile["metadata"].keys()))
                for confidence_key in (
                    "overall_confidence",
                    "habitat_confidence",
                    "topography_confidence",
                    "phenology_confidence",
                    "weather_threshold_confidence",
                    "taxonomy_confidence",
                ):
                    self.assertIn(profile["prediction_confidence"][confidence_key], confidence_values)

    def test_months_altitudes_and_delay_ranges_are_sane(self):
        data = self.load_profiles()

        for profile in data["species_profiles"]:
            with self.subTest(species=profile["species_id"]):
                phenology = profile["phenology"]
                months = phenology["main_months"] + phenology["secondary_months"]
                self.assertTrue(all(isinstance(month, int) for month in months))
                self.assertTrue(all(1 <= month <= 12 for month in months))

                delay = phenology["fruiting_delay_after_rain_days"]
                self.assertLessEqual(delay["min"], delay["optimal_min"])
                self.assertLessEqual(delay["optimal_min"], delay["optimal_max"])
                self.assertLessEqual(delay["optimal_max"], delay["max"])

                topography = profile["topography"]
                self.assertLessEqual(topography["altitude_min_m"], topography["altitude_optimal_min_m"])
                self.assertLessEqual(topography["altitude_optimal_min_m"], topography["altitude_optimal_max_m"])
                self.assertLessEqual(topography["altitude_optimal_max_m"], topography["altitude_max_m"])

    def test_prediction_confidence_and_metadata_values_are_sane(self):
        data = self.load_profiles()
        local_calibration_status = set(data["controlled_values"]["local_calibration_status"])
        review_status = set(data["controlled_values"]["review_status"])

        for profile in data["species_profiles"]:
            with self.subTest(species=profile["species_id"]):
                prediction_confidence = profile["prediction_confidence"]
                metadata = profile["metadata"]

                self.assertIn(prediction_confidence["local_calibration_status"], local_calibration_status)
                self.assertIn(metadata["review_status"], review_status)
                self.assertGreater(prediction_confidence["minimum_observations_for_calibration"], 0)
                self.assertGreater(prediction_confidence["minimum_positive_observations"], 0)
                self.assertGreater(prediction_confidence["minimum_negative_observations"], 0)
                self.assertGreaterEqual(
                    prediction_confidence["minimum_observations_for_calibration"],
                    prediction_confidence["minimum_positive_observations"],
                )
                self.assertGreaterEqual(
                    prediction_confidence["minimum_observations_for_calibration"],
                    prediction_confidence["minimum_negative_observations"],
                )
                self.assertIsInstance(metadata["requires_human_validation"], bool)

    def test_scoring_weights_are_complete_and_normalized(self):
        data = self.load_profiles()

        for profile in data["species_profiles"]:
            with self.subTest(species=profile["species_id"]):
                weights = profile["scoring_weights"]
                self.assertGreater(len(weights), 0)
                self.assertTrue(all(value >= 0 for value in weights.values()))
                self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
