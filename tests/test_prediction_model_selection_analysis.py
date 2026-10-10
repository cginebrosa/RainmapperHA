"""Synthetic invariants for the paired selector analysis; no research data reads."""
from copy import deepcopy
from datetime import date, timedelta
import json
import unittest

from scripts.prediction_model_selection import analyze


def observation(identity, *, fold=2024, y=1, episode=None, decisions=("favorable",) * 3):
    target = date(fold, 10, 1)
    rows = []
    for horizon in range(1, 8):
        row = {"observation_id": str(identity), "fold": fold, "horizon": horizon, "phase": "external",
               "species_id": "boletus_aereus", "episode_id": str(episode if episode is not None else identity),
               "y": y, "target_date": target.isoformat(), "issue_date": (target - timedelta(days=horizon - 1)).isoformat()}
        for method, decision in zip(analyze.METHODS, decisions):
            row[method] = {"decision": decision, "probability": None if decision == "abstain" else .8 if decision == "favorable" else .2,
                           "winner": None if decision == "abstain" else {"version_id": "synthetic", "profile_id": "p", "temporal_contract_id": "fixed", "estimator_id": "e"}}
        rows.append(row)
    return rows


class PredictionModelSelectionAnalysisTests(unittest.TestCase):
    def test_cluster_tensor_preserves_denominators_and_distinct_decisions(self):
        rows = observation(1, episode="shared", decisions=("favorable", "abstain", "unfavorable"))
        rows += observation(2, episode="shared", y=0, decisions=("favorable", "unfavorable", "abstain"))
        keys, tensor = analyze.episode_tensor(rows)
        self.assertEqual(len(keys), 1)
        self.assertTrue(all(abs(value - 2) < 1e-9 for value in tensor.sum(axis=(0, 2))))
        report = analyze.describe(rows, replicates=20)
        self.assertAlmostEqual(report["A"]["metrics"]["false_favorable"], 1)
        self.assertAlmostEqual(report["B"]["matrix"]["positive_abstain"], 1)
        self.assertAlmostEqual(report["C"]["matrix"]["positive_unfavorable"], 1)
        self.assertAlmostEqual(report["C"]["metrics"]["missed_positive"], 1)
        self.assertAlmostEqual(report["B"]["metrics"]["coverage"], .5)
        for contrast in ("B_minus_A", "C_minus_A"):
            self.assertAlmostEqual(report["bootstrap_95_percentile"][contrast]["false_favorable"]["upper"], -1)

    def test_bootstrap_pairs_three_methods_and_stratifies_complete_episodes(self):
        rows = observation(1, fold=2024) + observation(2, fold=2024, y=0, episode=1) + observation(3, fold=2025, y=0)
        keys, tensor = analyze.episode_tensor(rows)
        result = analyze.bootstrap(keys, tensor, replicates=50)
        for bound in ("lower", "upper"):
            self.assertAlmostEqual(result["A"]["false_favorable"][bound], 2)
            for label in ("B_minus_A", "C_minus_B", "C_minus_A"):
                self.assertEqual(result[label]["precision"][bound], 0)

    def test_all_abstain_has_undefined_precision_and_is_not_useful(self):
        rows = observation(1, decisions=("abstain",) * 3) + observation(2, y=0, decisions=("abstain",) * 3)
        report = analyze.describe(rows, replicates=20)
        self.assertIsNone(report["A"]["metrics"]["precision"])
        self.assertEqual(report["bootstrap_95_percentile"]["A"]["precision"]["finite_replicates"], 0)
        self.assertAlmostEqual(report["A"]["metrics"]["recall"], 0)
        for control in report["controls"].values():
            self.assertAlmostEqual(control["metrics"]["recall"], 0)
            self.assertAlmostEqual(control["metrics"]["missed_positive"], 1)
        json.dumps(report, allow_nan=False)

    def test_validation_rejects_duplicate_missing_horizon_and_future_issue(self):
        rows = observation(1)
        analyze.validate_rows(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate observation/horizon"):
            analyze.validate_rows(rows + [rows[0]])
        with self.assertRaisesRegex(ValueError, "all seven horizons"):
            analyze.validate_rows(rows[:-1])
        invalid = deepcopy(rows)
        invalid[0]["issue_date"] = "2024-10-02"
        with self.assertRaisesRegex(ValueError, "Target/issue"):
            analyze.validate_rows(invalid)

    def test_validation_rejects_changed_cohort_labels_and_ungated_favorable(self):
        rows = observation(1)
        cohort = {"rows": [{"observation_id": "1", "species_id": "boletus_aereus", "episode_id": "1", "y": 0, "date": "2024-10-01"}],
                  "folds": {"2024": {"1": "external"}, "2025": {"1": "fit"}, "2026": {"1": "fit"}}}
        with self.assertRaisesRegex(ValueError, "differs from frozen cohort"):
            analyze.validate_rows(rows, cohort)
        rows[0]["B"]["probability"] = .59
        with self.assertRaisesRegex(ValueError, "below the fixed threshold"):
            analyze.validate_rows(rows)

    def test_rule_accepts_useful_fp_reduction_but_rejects_degenerate_abstention(self):
        rows = []
        for fold in analyze.FOLDS:
            for i in range(10):
                y = int(i < 5)
                # B keeps 3/5 positive opportunities per fold and removes one FP.
                a = "favorable" if i < 3 or i in (5, 6) else "unfavorable"
                b = "favorable" if i < 3 or i == 5 else "unfavorable"
                rows += observation(f"{fold}-{i}", fold=fold, y=y, decisions=(a, b, "abstain"))
        strata = {"pooled": {"average": analyze.describe(rows, replicates=20)}}
        for fold in analyze.FOLDS:
            strata[str(fold)] = {"average": analyze.describe([r for r in rows if r["fold"] == fold], replicates=20)}
        result = analyze.nomination(strata)
        self.assertEqual(result["exploratory_nominee"], "B")
        self.assertTrue(result["comparisons"]["B_minus_A"]["passes"])
        self.assertFalse(result["comparisons"]["C_minus_A"]["passes"])
        self.assertFalse(result["operational_change_authorized"])
        # A global improvement cannot hide >1 additional FP in any fold.
        strata["2024"]["average"]["B"]["metrics"]["false_favorable"] = 3.1
        self.assertFalse(analyze.exploratory_rule(strata, "B")["passes"])

    def test_rule_tie_prefers_weekly_b(self):
        rows = []
        for fold in analyze.FOLDS:
            for i in range(10):
                y = int(i < 5)
                baseline = "favorable" if i < 3 or i in (5, 6) else "unfavorable"
                improved = "favorable" if i < 3 or i == 5 else "unfavorable"
                rows += observation(f"{fold}-{i}", fold=fold, y=y, decisions=(baseline, improved, improved))
        strata = {"pooled": {"average": analyze.describe(rows, replicates=10)}}
        for fold in analyze.FOLDS:
            strata[str(fold)] = {"average": analyze.describe([r for r in rows if r["fold"] == fold], replicates=10)}
        self.assertEqual(analyze.nomination(strata)["exploratory_nominee"], "B")

    def test_control_logs_reject_missing_or_failed_scientific_checks(self):
        cases = observation(1)
        controls = [{"observation_id": row["observation_id"], "horizon": row["horizon"], "status": "passed",
                     "different_fields": [], "actual_sha256": "same", "expected_sha256": "same"} for row in cases]
        inputs = [{"observation_id": row["observation_id"], "horizon": row["horizon"], "status": "passed",
                   "mismatched_materializations": 0, "mismatched_key_hashes": [], "shared_materializations": 2,
                   "only_B_materializations": 1, "only_C_materializations": 3} for row in cases]
        self.assertEqual(analyze.validate_control_logs(cases, controls, inputs)["shared_materializations"], 14)
        with self.assertRaisesRegex(ValueError, "cover exactly"):
            analyze.validate_control_logs(cases, controls[:-1], inputs)
        inputs[0]["mismatched_materializations"] = 1
        with self.assertRaisesRegex(ValueError, "input contracts differ"):
            analyze.validate_control_logs(cases, controls, inputs)

    def test_spatial_inventory_excludes_future_and_purged_rows_and_distinguishes_species(self):
        target, other = "boletus_aereus", "amanita_caesarea"
        rows = [
            {"observation_id": "train-same", "species_id": target, "area_id": "known-same"},
            {"observation_id": "train-other", "species_id": other, "area_id": "known-other"},
            {"observation_id": "purged", "species_id": target, "area_id": "purged-area"},
            {"observation_id": "future", "species_id": target, "area_id": "future-area"},
            {"observation_id": "external-1", "species_id": target, "area_id": "known-same"},
            {"observation_id": "external-2", "species_id": target, "area_id": "known-other"},
            {"observation_id": "external-3", "species_id": target, "area_id": "purged-area"},
            {"observation_id": "external-4", "species_id": target, "area_id": "future-area"},
        ]
        roles = {row["observation_id"]: "external" if row["observation_id"].startswith("external") else
                 {"train-same": "ranking", "train-other": "threshold", "purged": "purged", "future": "future"}[row["observation_id"]]
                 for row in rows}
        cohort = {"rows": rows, "folds": {str(fold): roles if fold == 2024 else
                  {row["observation_id"]: "fit" for row in rows} for fold in analyze.FOLDS}}
        result = analyze.spatial_support(cohort, target)
        counts = result["by_fold"]["2024"]
        self.assertEqual(counts["external_observations"], 4)
        self.assertEqual(counts["external_areas"], 4)
        self.assertEqual(counts["observations_in_areas_seen_in_training_any_species"], 2)
        self.assertEqual(counts["observations_in_areas_seen_in_training_same_species"], 1)
        self.assertFalse(result["new_location_transfer_test"])
        self.assertEqual(result["areas"], 4)

    def test_fallback_correction_is_required_only_for_subsequent_evaluations(self):
        self.assertNotIn(analyze.FALLBACK_PROTOCOL, analyze.required_evaluation_protocols(2024))
        for fold in (2025, 2026):
            self.assertIn(analyze.FALLBACK_PROTOCOL, analyze.required_evaluation_protocols(fold))
        self.assertIn(analyze.INPUT_PROTOCOL, analyze.required_evaluation_protocols(2024))

    def test_reuse_accounting_requires_identical_b_payload_and_presealed_plan(self):
        rows = observation(1, fold=2025)
        fields = ["decision_a", "probability", "winner"]
        plan = {"species_id": "boletus_aereus", "quality_sha256": "quality-b", "mode": analyze.DAILY_REUSE,
                "depends_on_point_probabilities": False, "depends_on_observed_outcome": False,
                "catalog_states": [{"day": day, "weekly_status": "daily_fallback"} for day in range(1, 8)]}
        plan["sha256"] = analyze._json_digest(plan)
        for row in rows:
            payload = {key: row["B"].get("decision" if key == "decision_a" else key) for key in fields}
            row["C"].update(execution_mode=analyze.DAILY_REUSE, execution_plan_sha256=plan["sha256"],
                            reused_from="B", reused_scientific_payload_sha256=analyze._json_digest(payload))
        plans = {"boletus_aereus": plan}
        summary = {"fold": 2025, "C_execution_plans": plans, "quality_sha256": {"B": "quality-b"},
                   "technical_control": {"scientific_fields": fields}, "C_execution_modes": {analyze.DAILY_REUSE: 7},
                   "actual_counts": {"C": {"scored_emissions": 7, "evaluator_calls": 0, "reused_scored_emissions": 7,
                        "trace_members": 0, "materialized_members": 0, "reused_materialized_members": 0, "materialized_available_members": 0}}}
        seal = {"cardinality": {"C_execution_plans": deepcopy(plans)}}
        result = analyze.execution_diagnostics(rows, summary, seal)
        self.assertEqual(result["C_execution_modes"][analyze.DAILY_REUSE], 7)
        rows[0]["C"]["probability"] = .9
        with self.assertRaisesRegex(ValueError, "differs from native daily B"):
            analyze.execution_diagnostics(rows, summary, seal)
        summary["fold"] = 2024
        legacy = analyze.execution_diagnostics([], summary, {})
        self.assertFalse(legacy["execution_modes_recorded"])
        self.assertIsNone(legacy["C_execution_modes"])


if __name__ == "__main__":
    unittest.main()
