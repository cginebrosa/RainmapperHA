"""Invariants of the isolated research protocol, using only synthetic records."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/prediction_research"))
from freeze import episode_groups, memberships
from common import OUTPUT, write_new
from prepare_windowed import project_windowed
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from train_fold import partition_samples
from recommendation_metrics import decision, select_threshold, validate_rows
from analyze import episode_tensor, bootstrap, describe


class PredictionResearchProtocolTests(unittest.TestCase):
    def test_bootstrap_preserves_fold_strata_and_pairs_identical_methods(self):
        rows = [{"observation_id": str(i), "episode_id": str(fold), "fold": fold,
                 "horizon": h, "y": int(i == 0), "decision_a": "favorable", "probability": .8}
                for i, fold in enumerate((2024, 2024, 2025)) for h in range(1, 8)]
        keys, tensor = episode_tensor(rows, {2024: .60, 2025: .60})
        result = bootstrap(keys, tensor, replicates=50)
        for bound in ("lower", "upper"):
            self.assertAlmostEqual(result["A"]["false_favorable"][bound], 2)
            self.assertEqual(result["B_minus_A"]["precision"][bound], 0)

    def test_report_keeps_seven_emissions_in_one_observation_and_episode(self):
        rows = [{"observation_id": str(i), "episode_id": "same_visit", "fold": 2024,
                 "horizon": h, "y": int(i == 0), "decision_a": "favorable",
                 "probability": .90 if i == 0 else .65}
                for i in range(2) for h in range(1, 8)]
        keys, tensor = episode_tensor(rows, {2024: .70})
        self.assertEqual(len(keys), 1)
        self.assertAlmostEqual(tensor[0, 0].sum(), 2)
        result = describe(rows, {2024: .70})
        self.assertAlmostEqual(result["A"]["metrics"]["false_favorable"], 1)
        self.assertAlmostEqual(result["B"]["matrix"]["negative_abstain"], 1)
        self.assertAlmostEqual(result["B"]["metrics"]["coverage"], .5)
        intervals = bootstrap(keys, tensor, replicates=20)
        for bound in ("lower", "upper"):
            self.assertAlmostEqual(intervals["B_minus_A"]["false_favorable"][bound], -1)
        self.assertEqual(result["groups"], 1)

    def test_report_leaves_precision_undefined_without_favorables(self):
        rows = [{"observation_id": "a", "episode_id": "e", "fold": 2026,
                 "horizon": h, "y": 1, "decision_a": "abstain", "probability": None}
                for h in range(1, 8)]
        result = describe(rows, {2026: .60})
        self.assertIsNone(result["A"]["metrics"]["precision"])
        self.assertAlmostEqual(result["A"]["metrics"]["miss_rate"], 1)
        self.assertEqual(result["bootstrap_95_percentile"]["A"]["precision"]["finite_replicates"], 0)
        self.assertIsNone(result["exploratory_group_bound"]["A"]["one_sided_95_upper_event_rate"])

    def test_threshold_control_and_abstention_are_not_negative_predictions(self):
        for answer, probability in (("favorable", .60), ("unfavorable", .20), ("abstain", .80)):
            row = {"decision_a": answer, "probability": probability}
            self.assertEqual(decision(row, .60), answer)
        row = {"decision_a": "favorable", "probability": .69}
        self.assertEqual(decision(row, .70), "abstain")

    def test_threshold_rule_rejects_suppressing_every_opportunity(self):
        rows = [{"observation_id": str(i), "episode_id": str(i), "horizon": h,
                 "y": int(i < 20), "decision_a": "favorable", "probability": .90 if i < 20 else .62}
                for i in range(40) for h in range(1, 8)]
        selected = select_threshold(rows)
        self.assertEqual(selected["threshold"], .65)
        self.assertFalse(selected["curve"][-1]["admissible"])
        with self.assertRaisesRegex(ValueError, "Duplicate observation/horizon"):
            validate_rows(rows + [rows[0]])

    def test_models_filter_all_species_before_preprocessing(self):
        roles = {"a": "fit", "b": "ranking", "c": "threshold", "d": "external", "e": "future"}
        rows, samples = [], []
        for index, (identity, role) in enumerate(roles.items()):
            sid = "boletus_aereus" if identity in {"a", "d"} else "shared_other_species"
            day = f"{2020+index}-10-01"
            rows.append({"observation_id": identity, "species_id": sid, "episode_id": identity, "date": day})
            samples.append({"sample_id": identity, "prediction_target": "favorable", "quality": {"training_eligible": True},
                            "metadata": {"observation_id": identity, "species_id": sid}})
        cohort = {"rows": rows, "folds": {"2024": roles}}
        train, test = partition_samples({"samples": samples}, cohort, 2024, "external")
        self.assertEqual({r["sample_id"] for r in train}, {"a", "b", "c"})
        self.assertEqual({r["sample_id"] for r in test}, {"d"})
        cohort["rows"][3]["episode_id"] = "b"
        with self.assertRaisesRegex(AssertionError, "Cross-species episode"):
            partition_samples({"samples": samples}, cohort, 2024, "external")

    def test_cross_species_visits_stay_in_one_episode_and_are_purged_together(self):
        rows = [
            {"observation_id": "a", "area_id": "same", "date": "2023-12-10", "species_id": "a"},
            {"observation_id": "b", "area_id": "same", "date": "2023-12-23", "species_id": "b"},
            {"observation_id": "c", "area_id": "same", "date": "2024-01-05", "species_id": "a"},
            {"observation_id": "d", "area_id": "other", "date": "2023-12-10", "species_id": "b"},
        ]
        groups = episode_groups(rows)
        self.assertEqual(groups["a"], groups["c"])
        for row in rows:
            row["episode_id"] = groups[row["observation_id"]]
        parts = memberships(rows, 2024)
        self.assertEqual([parts[key] for key in ("a", "b", "c")], ["purged"] * 3)
        self.assertEqual(parts["d"], "threshold")

    def test_temporal_roles_are_disjoint_and_future_is_not_development(self):
        rows = [{"observation_id": str(year), "area_id": "a", "date": f"{year}-10-01",
                 "episode_id": str(year)} for year in range(2021, 2026)]
        self.assertEqual(memberships(rows, 2024), {
            "2021": "fit", "2022": "ranking", "2023": "threshold",
            "2024": "external", "2025": "future"})

    def test_external_end_cannot_split_an_episode(self):
        rows = [{"observation_id": "before", "area_id": "a", "date": "2024-12-10", "episode_id": "e"},
                {"observation_id": "after", "area_id": "a", "date": "2025-01-05", "episode_id": "e"}]
        self.assertEqual(set(memberships(rows, 2024).values()), {"purged"})

    def test_output_helper_refuses_original_paths(self):
        with self.assertRaises(ValueError):
            write_new(OUTPUT.parent.parent / "docker-data/forbidden.json", {})

    def test_window_projection_preserves_every_installed_raw_and_smooth_input(self):
        import copy
        from datetime import date, timedelta
        area = {key: [float(i % 29) for i in range(365)] for key in raw.AREA_SERIES_KEYS.values()}
        area["daily_dates"] = [(date(2023, 10, 1) - timedelta(days=364-i)).isoformat() for i in range(365)]
        for contract in (raw.FIXED_CONTRACT_ID, raw.LAG_CONTRACT_ID):
            source = {"sample_id": "synthetic", "prediction_target": "favorable", "quality": {},
                      "metadata": {"observation_id": "synthetic", "target_date": "2023-10-08", "horizon_days": 7}}
            full = raw.build_v5_sample(source, area, temporal_contract_id=contract)
            projected = project_windowed(copy.deepcopy(full))
            include_horizon = contract == raw.LAG_CONTRACT_ID
            for window in (30, 60, 90):
                columns = set(raw.windowed_feature_columns(window, include_horizon=include_horizon))
                columns.update(smooth.raw_columns(include_phenology=True, include_horizon=include_horizon,
                                                 channels=raw.RAW_CHANNELS, window_days=window))
                self.assertEqual({c: projected["predictive_features"][c] for c in columns},
                                 {c: full["predictive_features"][c] for c in columns})
            self.assertEqual(projected["quality"], full["quality"])
            self.assertEqual(projected["metadata"], full["metadata"])
            self.assertEqual(len(projected["metadata"]["raw_daily_dates"]), 365)


if __name__ == "__main__":
    unittest.main()
