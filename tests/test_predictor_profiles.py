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
    "calibration_priority",
}

REQUIRED_ECOLOGY_KEYS = {
    "trophic_mode",
    "primary_hosts",
    "secondary_hosts",
    "forest_types",
    "soil_preference",
    "soil_avoidance",
    "lithology_preference",
    "habitat_confidence",
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
    "topography_confidence",
}

REQUIRED_WEATHER_KEYS = {
    "rainfall",
    "temperature",
    "humidity",
    "wind",
}

CONFIDENCE_VALUES = {"low", "medium", "high"}
CALIBRATION_PRIORITIES = {"low", "medium", "high", "very_high"}


class PredictorProfileTests(unittest.TestCase):
    def load_profiles(self):
        with PROFILE_PATH.open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_profile_file_is_valid_json_with_expected_top_level_shape(self):
        data = self.load_profiles()

        self.assertEqual(data["schema_version"], "0.1")
        self.assertEqual(data["model_purpose"], "mushroom_fruiting_probability_scoring")
        self.assertIsInstance(data["important_note"], str)
        self.assertIsInstance(data["species_profiles"], list)
        self.assertGreater(len(data["species_profiles"]), 0)

    def test_species_profiles_have_required_sections_and_unique_ids(self):
        data = self.load_profiles()
        seen_ids = set()

        for profile in data["species_profiles"]:
            with self.subTest(species=profile.get("species_id")):
                self.assertTrue(REQUIRED_PROFILE_KEYS.issubset(profile.keys()))
                species_id = profile["species_id"]
                self.assertNotIn(species_id, seen_ids)
                seen_ids.add(species_id)
                self.assertIsInstance(profile["common_names"], list)
                self.assertGreater(len(profile["common_names"]), 0)
                self.assertIn(profile["calibration_priority"], CALIBRATION_PRIORITIES)

    def test_ecology_phenology_topography_and_weather_sections_are_complete(self):
        data = self.load_profiles()

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
                self.assertIn(ecology["habitat_confidence"], CONFIDENCE_VALUES)
                self.assertIn(topography["topography_confidence"], CONFIDENCE_VALUES)

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
                self.assertIn(delay["confidence"], CONFIDENCE_VALUES)

                topography = profile["topography"]
                self.assertLessEqual(topography["altitude_min_m"], topography["altitude_optimal_min_m"])
                self.assertLessEqual(topography["altitude_optimal_min_m"], topography["altitude_optimal_max_m"])
                self.assertLessEqual(topography["altitude_optimal_max_m"], topography["altitude_max_m"])

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
