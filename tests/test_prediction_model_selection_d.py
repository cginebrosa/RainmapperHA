"""Scientific isolation checks for the new historical D study only."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.prediction_model_selection_d import study


class HistoricalIsolationTests(unittest.TestCase):
    def row(self, identity, day, episode, species="boletus_aereus"):
        return {"observation_id": identity, "date": day, "episode_id": episode,
                "species_id": species, "area_id": "synthetic", "y": 1}

    def test_purges_related_species_at_boundary(self):
        rows = [self.row("before", "2019-12-15", "shared"),
                self.row("after", "2020-01-20", "shared", "amanita_caesarea"),
                self.row("fit", "2019-10-20", "old"),
                self.row("test", "2020-10-20", "current"),
                self.row("future", "2021-10-20", "future")]
        roles = study.memberships(rows, 2020)
        self.assertEqual(roles, {"before": "purged", "after": "purged", "fit": "train", "test": "test", "future": "future"})

    def test_purge_fourteen_day_boundary_inclusive(self):
        rows = [self.row("near", "2020-01-15", "near"), self.row("far", "2020-01-16", "far")]
        self.assertEqual(study.memberships(rows, 2020), {"near": "purged", "far": "test"})

    def test_no_previous_species_has_no_fabricated_prevalence(self):
        m = {"species_id": "amanita_caesarea"}
        with self.assertRaisesRegex(ValueError, "No species-specific training prevalence"):
            study.ranking.evidence_rows("a|b|c", [], [{"metadata": m}])

    def test_writer_and_network_guard(self):
        code = '''
import socket
from scripts.prediction_model_selection_d.common import protect_originals
protect_originals()
checks = 0
for action in (lambda: open("tmp/forbidden-D-test", "w"), lambda: socket.socket().connect(("127.0.0.1", 9))):
    try: action()
    except PermissionError: checks += 1
assert checks == 2
'''
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=study.ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((study.ROOT / "tmp/forbidden-D-test").exists())

    def test_same_saved_request_requires_same_weather(self):
        record = {"model_ref": {"id": "x"}, "target_date": "2024-10-01", "cutoff_date": "2024-09-30", "weather_lookback_days": 30, "include_physical_state": False}
        altered = {**record, "weather_lookback_days": 365}
        self.assertEqual(study.evaluate.compare_input_contracts([record], [record])["status"], "passed")
        self.assertEqual(study.evaluate.compare_input_contracts([record], [altered])["status"], "failed")

    def test_i4_matches_user_equivalence_with_same_positives(self):
        from scripts.prediction_model_selection_d.analyze import values
        first = values([9, 11, 0, 1, 9, 0])
        second = values([17, 3, 0, 3, 7, 0])
        self.assertEqual(float(first["I4"]), float(second["I4"]))
        self.assertEqual(float(first["I4"]), 25)

    def test_abstention_not_useful_and_undefined_without_positives(self):
        from scripts.prediction_model_selection_d.analyze import values
        import numpy as np
        self.assertEqual(float(values([0, 0, 10, 0, 0, 10])["I4"]), 0)
        self.assertTrue(np.isnan(values([0, 0, 0, 0, 10, 0])["I4"]))

    def test_route_effect_is_only_declared_for_fallback_to_weekly(self):
        from scripts.prediction_model_selection_d.common_weather import route_check
        failed = {"status": "failed", "mismatched_materializations": 2}
        weekly = {"mode": study.evaluate.DAILY_INDEPENDENT, "catalog_states": [{"weekly_status": "weekly"} for _ in range(7)], "sha256": "weekly"}
        fallback = {"mode": study.evaluate.DAILY_REUSE, "sha256": "fallback"}
        self.assertEqual(route_check(failed, fallback, weekly)["status"], "native_route_effect")
        self.assertEqual(route_check(failed, weekly, weekly)["status"], "failed")
        self.assertEqual(route_check(failed, fallback, {**weekly, "catalog_states": []})["status"], "failed")


if __name__ == "__main__":
    unittest.main()
