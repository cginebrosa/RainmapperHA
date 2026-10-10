"""Synthetic scientific controls for experimental daily model selection."""
import copy
from datetime import date
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prediction_model_selection.daily import resolve_species_days
from scripts.prediction_model_selection.evaluate import (
    cardinality, compare_control, compare_input_contracts, daily_resolver, legacy,
    daily_execution_plan, reuse_native_daily_result, DAILY_INDEPENDENT, DAILY_REUSE,
)


def reference(estimator, day, *, fixed=False):
    return {"version_id": "synthetic_v1", "profile_id": "synthetic_profile",
            "temporal_contract_id": "fixed_gap_7d" if fixed else "lag_event_7d",
            "horizon_days": 7 if fixed else day, "estimator_id": estimator,
            "species_id": "amanita_caesarea"}


def resolutions(*, fixed=False):
    result = {}
    for day in range(1, 8):
        candidates = [reference(estimator, day, fixed=fixed) for estimator in ("preferred", "backup")]
        result[day] = {"selection_status": "winner", "candidate": candidates[0],
                       "candidate_chain": [{"candidate": candidate} for candidate in candidates]}
    return result


def member(ref, *, probability=.65, valid=True):
    return {"model_ref": ref, "available": True,
            "prediction": {"probability": probability, "applicability": {
                "status": "within_observed_range" if valid else "outside_observed_range"}},
            "evaluation": {"evidence": "better_than_prevalence", "brier_score": .10,
                           "prevalence_brier_score": .25, "brier_delta_vs_prevalence": .15,
                           "roc_auc": .8, "n_test": 20,
                           "test_positive_count": 10, "test_negative_count": 10}}


def run_daily(rows, materialize, *, resolver=resolve_species_days, **overrides):
    keywords = dict(species_id="amanita_caesarea", point_id="synthetic_point",
        issue_date=date(2026, 10, 1), resolutions_by_day=rows,
        installed_version_ids=["synthetic_v1"], materialize=materialize,
        season_phase=lambda _: "main", phenology={},
        recommendation_policy={"mode": "shadow", "rule_version": "consensus_v1"})
    keywords.update(overrides)
    return resolver(**keywords)


class PredictionModelSelectionDailyTests(unittest.TestCase):
    def test_daily_fallback_changes_only_on_veto_not_higher_probability(self):
        rows = resolutions()
        original = copy.deepcopy(rows)
        calls = []
        def materialize(*, target_date, selections):
            calls.append((target_date, selections))
            return {"members": [member(ref, probability=.99 if ref["estimator_id"] == "backup" else .65,
                valid=not (target_date.day == 4 and ref["estimator_id"] == "preferred")) for ref in selections]}
        result = run_daily(rows, materialize)
        selected = [row["operational_comparison"]["selected_winners"][0]["model_ref"]["estimator_id"]
                    for row in result["days"]]
        self.assertEqual(selected, ["preferred", "preferred", "preferred", "backup", "preferred", "preferred", "preferred"])
        self.assertEqual(rows, original)
        self.assertTrue(all(len({legacy.comparison._weekly_candidate_family(ref) for ref in selections}) == 1
                            for _, selections in calls))
        for row in result["days"]:
            active = row["reliability_selection"]
            self.assertNotIn("weekly_model_selection", active)
            self.assertEqual(row["operational_comparison"]["recommendation_decision"]["mode"], "shadow")

    def test_daily_fixed_contract_keeps_its_seven_day_weather_gap(self):
        seen = []
        def materialize(*, target_date, selections):
            seen.extend(selections)
            return {"members": [member(ref) for ref in selections]}
        result = run_daily(resolutions(fixed=True), materialize)
        self.assertEqual(len(result["days"]), 7)
        self.assertTrue(all(ref["horizon_days"] == 7 for ref in seen))

    def test_lazy_daily_matches_exhaustive_and_stops_on_uncertain_winner(self):
        calls = {"full": 0, "lazy": 0}
        def run(mode):
            def materialize(*, target_date, selections):
                calls[mode] += len(selections)
                return {"members": [member(ref, probability=.5 if ref["estimator_id"] == "preferred" else .99,
                    valid=not (target_date.day == 4 and ref["estimator_id"] == "preferred")) for ref in selections]}
            return run_daily(resolutions(), materialize, lazy_families=mode == "lazy")
        full, lazy = run("full"), run("lazy")
        for expected, actual in zip(full["days"], lazy["days"], strict=True):
            self.assertEqual(actual["operational_comparison"]["selected_winners"],
                             expected["operational_comparison"]["selected_winners"])
            self.assertEqual(actual["operational_comparison"]["interpretation"],
                             expected["operational_comparison"]["interpretation"])
            for key in ("candidate", "runtime_selection_status", "fallback_rank", "runtime_candidate_exclusions"):
                self.assertEqual(actual["reliability_selection"].get(key), expected["reliability_selection"].get(key))
        self.assertEqual(calls, {"full": 14, "lazy": 8})

    def test_all_vetoed_candidates_remain_abstention(self):
        result = run_daily(resolutions(), lambda **kwargs: {
            "members": [member(ref, valid=False) for ref in kwargs["selections"]]})
        for row in result["days"]:
            self.assertEqual(row["reliability_selection"]["runtime_selection_status"], "abstain")
            self.assertEqual(row["operational_comparison"]["selected_winners"], [])

    def test_rejects_weekly_resolved_or_wrong_horizon_inputs(self):
        rows = resolutions()
        rows[1]["weekly_model_selection"] = {"status": "weekly"}
        with self.assertRaisesRegex(ValueError, "original_candidate_chains"):
            run_daily(rows, lambda **_: self.fail("Must reject before materializing"))
        rows = resolutions()
        rows[1]["candidate_chain"][0]["candidate"]["horizon_days"] = 2
        with self.assertRaisesRegex(ValueError, "horizon_mismatch"):
            run_daily(rows, lambda **_: self.fail("Must reject before materializing"))

    def test_requires_complete_week_and_frozen_shadow_policy(self):
        rows = resolutions()
        rows.pop(7)
        with self.assertRaisesRegex(ValueError, "seven_days"):
            run_daily(rows, lambda **_: {})
        with self.assertRaisesRegex(ValueError, "shadow"):
            run_daily(resolutions(), lambda **_: {},
                      recommendation_policy={"mode": "prudent", "rule_version": "consensus_v1"})

    def test_daily_injection_restores_legacy_resolver_after_error(self):
        before = legacy.resolve_species_week
        with self.assertRaisesRegex(RuntimeError, "deliberate"):
            with daily_resolver():
                self.assertIs(legacy.resolve_species_week, resolve_species_days)
                raise RuntimeError("deliberate")
        self.assertIs(legacy.resolve_species_week, before)

    def test_control_compares_trace_and_weekly_science_not_just_target_class(self):
        old = {"decision_a": "abstain", "probability": None, "winner": None,
               "reason": "uncertain", "trace": [{"probability": .72}],
               "weekly_days": [{"winner": {"estimator_id": "preferred"}, "verdict": "favorable"}]}
        now = copy.deepcopy(old)
        now["runtime_seconds"] = 12
        self.assertEqual(compare_control(now, old)["status"], "passed")
        now["trace"][0]["probability"] = .73
        self.assertEqual(compare_control(now, old)["different_fields"], ["trace"])
        now = copy.deepcopy(old)
        now["weekly_days"][0]["winner"]["estimator_id"] = "backup"
        self.assertEqual(compare_control(now, old)["different_fields"], ["weekly_days"])

    def test_input_parity_refuses_mixed_batch_weather_contract(self):
        base = {"model_ref": reference("preferred", 1), "target_date": "2026-10-01",
                "cutoff_date": "2026-09-30", "weather_lookback_days": 90, "include_physical_state": False}
        self.assertEqual(compare_input_contracts([base], [base])["shared_materializations"], 1)
        changed = {**base, "weather_lookback_days": 365, "include_physical_state": True}
        self.assertEqual(compare_input_contracts([base], [changed])["status"], "failed")
        with self.assertRaisesRegex(ValueError, "unlike weather inputs"):
            compare_input_contracts([base, changed], [base])

    def test_metadata_fallback_plan_reuses_native_daily_result_without_aliases(self):
        rows = resolutions()
        # No family occurs on all seven days, so B's native branch is daily.
        for day, row in rows.items():
            for entry in row["candidate_chain"]:
                entry["candidate"]["profile_id"] = f"day_{day}"
        plan = daily_execution_plan(rows, species_id="amanita_caesarea",
                                    installed_version_ids=["synthetic_v1"], quality_sha256="frozen")
        self.assertEqual(plan["mode"], DAILY_REUSE)
        self.assertFalse(plan["depends_on_point_probabilities"])
        calls = []
        def materialize(*, target_date, selections):
            calls.append(len(selections))
            return {"members": [member(ref, probability=.65 if ref["estimator_id"] == "preferred" else .99,
                valid=not (target_date.day == 4 and ref["estimator_id"] == "preferred")) for ref in selections]}
        native = run_daily(rows, materialize, resolver=legacy.resolve_species_week, lazy_families=True)
        before_reuse = len(calls)
        contracts = [{"lookback": 365, "physical": True}]
        reused, copied_contracts = reuse_native_daily_result(native, contracts, plan)
        self.assertEqual(reused, native)
        self.assertEqual(len(calls), before_reuse)
        self.assertTrue(all(size == 2 for size in calls))  # B's mixed batches are unchanged.
        pure_daily = run_daily(rows, materialize, lazy_families=True)
        for left, right in zip(native["days"], pure_daily["days"], strict=True):
            self.assertEqual(left["operational_comparison"]["selected_winners"],
                             right["operational_comparison"]["selected_winners"])
            self.assertEqual(left["operational_comparison"]["interpretation"],
                             right["operational_comparison"]["interpretation"])
        reused["days"][0]["operational_comparison"]["selected_winners"].clear()
        copied_contracts[0]["lookback"] = 90
        self.assertTrue(native["days"][0]["operational_comparison"]["selected_winners"])
        self.assertEqual(contracts[0]["lookback"], 365)

    def test_common_weekly_family_never_reuses_B_decision_for_C(self):
        rows = resolutions()
        for row in rows.values():
            for entry in row["candidate_chain"]:
                entry["evidence"] = {"wilson_lower_95_observations": .4}
        plan = daily_execution_plan(rows, species_id="amanita_caesarea",
                                    installed_version_ids=["synthetic_v1"], quality_sha256="frozen")
        self.assertEqual(plan["mode"], DAILY_INDEPENDENT)
        with self.assertRaisesRegex(ValueError, "daily-fallback"):
            reuse_native_daily_result({}, [], plan)

    def test_cardinality_counts_separate_weeks_not_seven_independent_visits(self):
        cases = [{"species_id": "amanita_caesarea"}]
        result = cardinality(cases, {method: {"amanita_caesarea": resolutions()}
                                     for method in ("control", "A", "B", "C")})
        self.assertEqual(result["observations"], 1)
        self.assertEqual(result["scored_emissions"], 7)
        self.assertEqual(result["week_targets_per_method"], 49)
        self.assertEqual(result["per_method"]["C"]["amanita_caesarea"]["candidate_requests_upper_bound"], 98)


if __name__ == "__main__":
    unittest.main()
