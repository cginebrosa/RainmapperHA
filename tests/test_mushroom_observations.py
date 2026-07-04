from __future__ import annotations

import unittest

from rainmapper_core import mushroom_observations


class MushroomObservationDerivedFieldsTests(unittest.TestCase):
    def test_derived_fields_from_observed_at_assigns_month_and_simple_season(self) -> None:
        cases = {
            "2026-01-15": {"month": 1, "season": "winter"},
            "2026-04-15": {"month": 4, "season": "spring"},
            "2026-07-15": {"month": 7, "season": "summer"},
            "2026-10-15": {"month": 10, "season": "autumn"},
            "2026-12-15": {"month": 12, "season": "winter"},
        }

        for observed_at, expected in cases.items():
            with self.subTest(observed_at=observed_at):
                self.assertEqual(expected, mushroom_observations.derived_fields_from_observed_at(observed_at))

    def test_finalize_observation_payload_updates_derived_without_mutating_input(self) -> None:
        observation = {
            "observation_id": "obs_20260629_0001",
            "observed_at": "2026-06-29",
            "derived": {"month": 1, "season": "winter", "custom": "kept"},
        }

        finalized = mushroom_observations.finalize_observation_payload(observation)

        self.assertEqual({"month": 6, "season": "summer", "custom": "kept"}, finalized["derived"])
        self.assertEqual({"month": 1, "season": "winter", "custom": "kept"}, observation["derived"])


if __name__ == "__main__":
    unittest.main()
