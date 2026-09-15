"""Point weekly policy: real selectors, isolated materialized model fixtures."""
import copy
from datetime import date, timedelta
import unittest
from unittest.mock import Mock

from rainmapper_core.mushroom_map_prediction import resolve_species_week
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core.mushroom_predictor_precompute import weekly_aggregate_resolution_index


class PointWeekTests(unittest.TestCase):
    issue = date(2026,12,29)

    def resolutions(self):
        rows = {}
        for day in range(1,8):
            chain = []
            for estimator,score in (("quality_first",.8),("coverage_first",.7)):
                ref = {"version_id":"biology_v6","temporal_contract_id":"lag_event_biology_v6",
                       "profile_id":"smooth_window_30d","estimator_id":estimator,"horizon_days":day}
                chain.append({"candidate":ref,"evidence":{"wilson_lower_95_observations":score}})
            rows[day] = {"selection_status":"winner","candidate":copy.deepcopy(chain[0]["candidate"]),
                         "candidate_chain":chain,"evidence":copy.deepcopy(chain[0]["evidence"])}
        return rows

    def materializer(self, veto=None):
        veto = veto or {}
        def calculate(*,target_date,selections):
            day = (target_date-self.issue).days+1
            return {"members":[{"model_ref":dict(ref),"available":True,
                "prediction":{"probability":.6,"applicability":{"status":
                    "outside_domain" if day in veto.get(ref["estimator_id"],()) else "within_observed_range"}},
                "evaluation":{"evidence":"better_than_prevalence","brier_score":.1,
                    "prevalence_brier_score":.25,"brier_delta_vs_prevalence":.15,"roc_auc":.8}}
                for ref in selections]}
        return Mock(side_effect=calculate)

    def run_week(self, rows=None, materialize=None):
        return resolve_species_week(species_id="species-a",point_id="point-a",issue_date=self.issue,
            resolutions_by_day=self.resolutions() if rows is None else rows,
            installed_version_ids=["biology_v6"],
            materialize=materialize or self.materializer(),season_phase=lambda _day:"in_season",phenology={})

    def test_lazy_families_match_eager_probabilities_and_selection(self):
        for veto in ({}, {"quality_first":{7}}, {"quality_first":{7},"coverage_first":{1,2}}):
            eager=self.run_week(materialize=self.materializer(veto))
            calculator=self.materializer(veto)
            lazy=resolve_species_week(species_id="species-a",point_id="point-a",issue_date=self.issue,
                resolutions_by_day=self.resolutions(),installed_version_ids=["biology_v6"],
                materialize=calculator,season_phase=lambda _day:"in_season",phenology={},lazy_families=True)
            self.assertEqual(lazy,eager)
            self.assertEqual(calculator.call_count,7 if not veto else 14)
            self.assertTrue(all(len(c.kwargs['selections'])==1 for c in calculator.call_args_list))

    def test_week_prioritizes_coverage_and_has_one_cutoff_across_year_boundary(self):
        original = self.resolutions()
        before = copy.deepcopy(original)
        materialize = self.materializer({"quality_first":{7}})
        result = self.run_week(original,materialize)
        self.assertEqual(original,before)
        self.assertEqual(materialize.call_count,7)
        for row,call in zip(result["days"],materialize.call_args_list):
            active = row["reliability_selection"]
            self.assertEqual(active["candidate"]["estimator_id"],"coverage_first")
            self.assertEqual(active["weekly_model_selection"]["common_weather_cutoff"],"2026-12-28")
            self.assertEqual(active["weekly_model_selection"]["applicable_prediction_days"],7)
            for ref in call.kwargs["selections"]:
                self.assertEqual(ref["horizon_days"],row["prediction_day"])
                self.assertEqual(call.kwargs["target_date"]-timedelta(days=ref["horizon_days"]),self.issue-timedelta(days=1))
        self.assertEqual(result["days"][-1]["target_date"],"2027-01-04")

    def test_veto_abstains_without_switching_family(self):
        result = self.run_week(materialize=self.materializer({"quality_first":{7},"coverage_first":{1,2}}))
        for row in result["days"]:
            self.assertEqual(row["reliability_selection"]["candidate"]["estimator_id"],"quality_first")
        self.assertEqual(result["days"][-1]["reliability_selection"]["runtime_selection_status"],"abstain")
        self.assertEqual(result["days"][0]["reliability_selection"]["runtime_selection_status"],"winner")

    def test_incomplete_family_preserves_daily_fallback_and_fixed_cutoffs(self):
        rows = self.resolutions()
        for row in rows.values():
            for entry in row["candidate_chain"]:
                entry["candidate"].update(temporal_contract_id="fixed_gap_7d_biology_v6",horizon_days=7)
            row["candidate"] = copy.deepcopy(row["candidate_chain"][0]["candidate"])
        materialize = self.materializer()
        result = self.run_week(rows,materialize)
        cutoffs = set()
        for row,call in zip(result["days"],materialize.call_args_list):
            audit = row["reliability_selection"]["weekly_model_selection"]
            self.assertEqual(audit["status"],"daily_fallback")
            self.assertNotIn("common_weather_cutoff",audit)
            self.assertTrue(all(ref["horizon_days"]==7 for ref in call.kwargs["selections"]))
            cutoffs.add(call.kwargs["target_date"]-timedelta(days=7))
        self.assertEqual(len(cutoffs),7)

    def test_sealed_abstention_never_runs_inference(self):
        rows = {day:{"selection_status":"abstain","candidate":None} for day in range(1,8)}
        materialize = self.materializer()
        result = self.run_week(rows,materialize)
        materialize.assert_not_called()
        self.assertTrue(all(row["operational_comparison"]["available"] is False for row in result["days"]))

    def test_incomplete_or_already_resolved_area_result_rejected_before_inference(self):
        for defect in ("missing_day","resolved","weekly"):
            rows = self.resolutions()
            if defect == "missing_day": del rows[7]
            elif defect == "resolved": rows[1]["runtime_selection_status"] = "winner"
            else: rows[1]["weekly_model_selection"] = {"policy":"weekly_lag_event_v2"}
            materialize = self.materializer()
            with self.assertRaises(ValueError): self.run_week(rows,materialize)
            materialize.assert_not_called()

    def test_same_inputs_equal_existing_predictor_selection_pipeline(self):
        rows = self.resolutions()
        materialize = self.materializer({"quality_first":{7}})
        indexed = weekly_aggregate_resolution_index(
            {("species-a","area-a",day):row for day,row in rows.items()},
            issue_date=self.issue,installed_version_ids=["biology_v6"])
        by_day = {day:indexed[("species-a","area-a",day)] for day in range(1,8)}
        members = {day:materialize(target_date=self.issue+timedelta(days=day-1),
            selections=comparison.reliability_candidate_selections(row))["members"] for day,row in by_day.items()}
        selected = comparison.prioritize_weekly_resolutions_by_applicability(by_day,members)
        result = self.run_week(rows,materialize)
        for row in result["days"]:
            day = row["prediction_day"]
            expected,active = comparison.build_reliability_selected_operational_comparison(
                members[day],selected[day],season_phase="in_season",phenology={})
            self.assertEqual(row["operational_comparison"],expected)
            self.assertEqual(row["reliability_selection"],active)


if __name__ == "__main__": unittest.main()
