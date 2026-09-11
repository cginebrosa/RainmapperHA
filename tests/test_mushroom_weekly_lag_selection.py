"""Weekly time consistency without loading models or live weather."""

import copy
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_runtime_features as features
from rainmapper_core import mushroom_predictor_precompute as precompute
from rainmapper_core.mushroom_predictor_service import PredictorService


class WeeklyLagSelectionTests(TestCase):
    def resolutions(self, *, species="species-a", area="area-a"):
        rows = {}
        for day in range(1, 8):
            chain = []
            for contract, score in (("fixed_gap_7d_biology_v6", .99), ("lag_event_biology_v6", .65)):
                candidate = {
                    "version_id": "biology_v6_windowed_smooth_hierarchical",
                    "temporal_contract_id": contract,
                    "profile_id": "smooth_window_30d_plus_physical_state",
                    "estimator_id": "smooth_shared_logistic_v1",
                    "horizon_days": 7 if contract.startswith("fixed") else day,
                }
                chain.append({"candidate": candidate, "evidence": {"wilson_lower_95_observations": score}})
            rows[(species, area, day)] = {
                "selection_status": "winner", "candidate": copy.deepcopy(chain[0]["candidate"]),
                "candidate_chain": chain, "evidence": copy.deepcopy(chain[0]["evidence"]),
            }
        return rows

    def test_fixed_model_cannot_win_even_with_better_evidence(self):
        original = self.resolutions()
        before = copy.deepcopy(original)
        result = precompute.weekly_aggregate_resolution_index(original, issue_date=date(2026, 9, 10))
        self.assertEqual(original, before)
        for (_, _, day), row in result.items():
            self.assertTrue(row["candidate"]["temporal_contract_id"].startswith("lag_event"))
            self.assertEqual(row["candidate"]["horizon_days"], day)
            self.assertEqual(len(row["candidate_chain"]), 1)
            self.assertEqual(row["weekly_model_selection"]["common_weather_cutoff"], "2026-09-09")

    def test_incomplete_or_wrong_horizon_keeps_original_daily_choices(self):
        for defect in ("missing_lag", "wrong_horizon", "missing_winner", "unknown_contract", "uninstalled"):
            with self.subTest(defect=defect):
                original = self.resolutions()
                row = original[("species-a", "area-a", 4)]
                if defect == "missing_lag":
                    row["candidate_chain"] = row["candidate_chain"][:1]
                elif defect == "wrong_horizon":
                    row["candidate_chain"][1]["candidate"]["horizon_days"] = 7
                elif defect == "missing_winner":
                    row.update(selection_status="abstain", candidate=None, candidate_chain=[])
                elif defect == "unknown_contract":
                    for r in original.values():
                        r["candidate_chain"][1]["candidate"]["temporal_contract_id"] = "unknown_future_contract"
                result = precompute.weekly_aggregate_resolution_index(
                    original, installed_version_ids=[] if defect == "uninstalled" else None
                )
                for key, selected in result.items():
                    self.assertEqual(selected["candidate"], original[key]["candidate"])
                    self.assertEqual(selected["candidate_chain"], original[key]["candidate_chain"])
                    self.assertEqual(selected["selection_status"], original[key]["selection_status"])
                    audit = selected["weekly_model_selection"]
                    self.assertEqual(audit["status"], "daily_fallback")
                    self.assertNotIn("common_weather_cutoff", audit)

    def test_species_and_areas_are_independent_and_existing_abstentions_stay(self):
        rows = self.resolutions()
        partial = self.resolutions(species="species-b", area="area-b")
        partial[("species-b", "area-b", 7)]["candidate_chain"] = partial[("species-b", "area-b", 7)]["candidate_chain"][:1]
        abstentions = {("species-c", "area-c", day): {"selection_status": "abstain", "candidate": None} for day in range(1, 8)}
        rows.update(partial)
        rows.update(abstentions)
        result = precompute.weekly_aggregate_resolution_index(rows)
        for day in range(1, 8):
            self.assertTrue(result[("species-a", "area-a", day)]["candidate"]["temporal_contract_id"].startswith("lag_event"))
            self.assertEqual(result[("species-b", "area-b", day)]["weekly_model_selection"]["status"], "daily_fallback")
            self.assertEqual(result[("species-c", "area-c", day)], abstentions[("species-c", "area-c", day)])

    def test_runtime_guard_rejects_fixed_partial_and_wrong_horizon_weeks(self):
        rows = precompute.weekly_aggregate_resolution_index(self.resolutions())
        for defect in ("fixed", "horizon", "missing_day"):
            with self.subTest(defect=defect):
                by_day = {key[2]: copy.deepcopy(row) for key, row in rows.items()}
                if defect == "missing_day":
                    del by_day[7]
                elif defect == "fixed":
                    by_day[4]["candidate_chain"][0]["candidate"]["temporal_contract_id"] = "fixed_gap_7d_biology_v6"
                else:
                    by_day[4]["candidate_chain"][0]["candidate"]["horizon_days"] = 7
                with self.assertRaises(ValueError):
                    comparison.prioritize_weekly_resolutions_by_applicability(by_day, {})

    def test_service_rejects_wrong_horizon_before_weather_or_inference(self):
        rows = precompute.weekly_aggregate_resolution_index(self.resolutions())
        rows[("species-a", "area-a", 3)]["candidate_chain"][0]["candidate"]["horizon_days"] = 7
        service = object.__new__(PredictorService)
        with self.assertRaisesRegex(ValueError, "exact lag_event"):
            service.prewarm_multiversion_week(
                species_id="species-a", area_id="area-a", issue_date=date(2026, 9, 10),
                target_dates=[date(2026, 9, 10) + timedelta(days=n) for n in range(7)],
                selections=[], prepared_weather_cache={}, comparison_cache={}, operational_resolution_index=rows,
            )

    def test_all_seven_days_use_known_rain_in_actual_model_inputs_across_calendar_boundaries(self):
        for issue in (date(2026, 9, 10), date(2026, 12, 29), date(2024, 2, 27)):
            for version, profile, estimator in (
                ("biology_v5_windowed_raw_weather", "raw_window_30d_plus_physical_state", "test-estimator"),
                ("biology_v6_windowed_smooth_hierarchical", "smooth_window_30d_plus_physical_state", "smooth_shared_logistic_v1"),
            ):
                with self.subTest(issue=issue, version=version):
                    cutoff = issue - timedelta(days=1)
                    def materialize(**kwargs):
                        end = kwargs["end_day"]
                        days = [end - timedelta(days=n) for n in reversed(range(kwargs["days"]))]
                        series = {key: [0.] * len(days) for key in raw.AREA_SERIES_KEYS.values()}
                        series["daily_dates"] = [d.isoformat() for d in days]
                        series[raw.AREA_SERIES_KEYS["rain_mm"]] = [56.1 if d == cutoff else 0. for d in days]
                        return series
                    with (
                        mock.patch.object(comparison.mushroom_ml_area_weather_runtime, "area_contexts", return_value=({"area-a": object()}, {"area-a": [object()]})),
                        mock.patch.object(comparison.weather_context, "load_stations_catalog", return_value=SimpleNamespace(itertuples=lambda **kw: iter([]))),
                        mock.patch.object(comparison.weather_context, "load_daily_weather_parquet", return_value={}) as load,
                        mock.patch.object(comparison.mushroom_ml_area_weather_runtime, "materialize_area_series", side_effect=materialize),
                    ):
                        for day in range(1, 8):
                            target = issue + timedelta(days=day - 1)
                            _, prepared, stations = comparison.prepare_area_weather(
                                known_sites_path=Path("unused"), weather_data_dir=Path("unused"),
                                area_id="area-a", target_date=target, horizons=[day],
                            )
                            model = catalog.ModelRef(
                                batch_id="test", generation_id="test", version_id=version,
                                temporal_contract_id="lag_event_biology_v6_smooth_hierarchical_v2" if "v6" in version else raw.LAG_CONTRACT_ID,
                                profile_id=profile, estimator_id=estimator, species_id="species-a", horizon_days=day,
                            )
                            sample = features.build_runtime_features(model, target_date=target, area_id="area-a", area_context=None, area_series=prepared[day], stations=stations)
                            self.assertEqual(load.call_args.kwargs["end_date"], cutoff)
                            self.assertEqual(sample["predictive_features"]["rain_mm__lag_000"], 56.1)
                            self.assertEqual(sample["predictive_features"]["horizon_days"], float(day))
                            self.assertEqual(sample["quality"]["significant_rain_event_date"], cutoff.isoformat())
                            self.assertEqual(sample["quality"]["days_since_significant_rain_at_target"], float(day))
                            self.assertEqual(sample["metadata"]["cutoff_date"], cutoff.isoformat())
