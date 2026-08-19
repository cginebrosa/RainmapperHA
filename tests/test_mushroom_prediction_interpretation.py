from __future__ import annotations

from unittest import TestCase

from rainmapper_core.mushroom_prediction_interpretation import build_interpretation


def model(lr: float, rf: float, lr_brier: float, rf_brier: float) -> dict:
    return {
        "available": True,
        "estimator_probabilities": {
            "logistic_regression_reduced_v1": lr,
            "random_forest_restricted_v1": rf,
        },
        "evaluation": {
            "available": True,
            "baseline": {"brier_score": 0.23},
            "estimators": {
                "logistic_regression_reduced_v1": {
                    "n": 11,
                    "brier_score": lr_brier,
                    "roc_auc": 0.71,
                },
                "random_forest_restricted_v1": {
                    "n": 11,
                    "brier_score": rf_brier,
                    "roc_auc": 0.86,
                },
            },
        },
        "features_used": {
            "significant_rain_found_90d": 1.0,
            "days_since_significant_rain_at_target": 9.0,
        },
    }


def with_svm(result: dict, probability: float, brier: float = 0.18) -> dict:
    result["estimator_probabilities"]["rbf_svm_calibrated_v1"] = probability
    result["evaluation"]["estimators"]["rbf_svm_calibrated_v1"] = {
        "n": 11,
        "brier_score": brier,
        "roc_auc": 0.82,
    }
    return result


class MushroomPredictionInterpretationTests(TestCase):
    def test_boolean_significant_rain_flag_prevents_false_ecological_veto(self) -> None:
        fixed = model(0.7, 0.65, 0.18, 0.17)
        fixed["features_used"]["significant_rain_found_90d"] = True

        result = build_interpretation(
            {"fixed_gap_7d_v1": fixed},
            season_phase="main",
            phenology={"fruiting_delay_after_rain_days": {"min": 2, "max": 21}},
        )

        self.assertEqual(result["weather_signal"], "recent_event")
        self.assertEqual(result["ecological_compatibility"], "compatible")
        self.assertNotIn("ecological_rain_guardrail", result["reason_codes"])

    def test_uses_best_validated_estimator_per_feature_set(self) -> None:
        result = build_interpretation(
            {
                "fixed_gap_7d_v1": model(0.90, 0.46, 0.21, 0.18),
                "lag_event_v1": model(1.00, 0.53, 0.19, 0.15),
            },
            season_phase="main",
            phenology={
                "fruiting_delay_after_rain_days": {
                    "min": 5,
                    "optimal_min": 7,
                    "optimal_max": 15,
                    "max": 21,
                }
            },
        )

        self.assertEqual(result["verdict"], "uncertain")
        self.assertEqual(result["reference_range"], {
            "min": 0.46,
            "max": 0.53,
            "midpoint": 0.495,
        })
        self.assertEqual(result["statistical_consensus"], "low")
        self.assertEqual(result["statistical_support"], "limited")
        self.assertEqual(result["ecological_compatibility"], "compatible")
        self.assertEqual(result["ecological_evidence"], "high")
        self.assertEqual(
            {row["estimator_id"] for row in result["trusted_results"]},
            {"random_forest_restricted_v1"},
        )

    def test_abstains_when_no_estimator_beats_prevalence(self) -> None:
        weak = model(0.7, 0.6, 0.25, 0.24)
        result = build_interpretation(
            {"fixed_gap_7d_v1": weak, "lag_event_v1": weak},
            season_phase="main",
        )

        self.assertEqual(result["verdict"], "abstain")
        self.assertIsNone(result["reference_range"])
        self.assertEqual(result["statistical_support"], "unavailable")
        self.assertIn("no_estimator_beats_prevalence", result["reason_codes"])
        self.assertEqual(result["unvalidated_signal"], "favorable")
        self.assertEqual(
            result["unvalidated_range"],
            {"min": 0.65, "max": 0.65, "midpoint": 0.65},
        )

    def test_excludes_logistic_regression_on_severe_extrapolation(self) -> None:
        fixed = model(0.0, 0.17, 0.17, 0.19)
        lag = model(1.0, 0.16, 0.17, 0.19)
        for result in (fixed, lag):
            result["estimator_exclusions"] = {
                "logistic_regression_reduced_v1": {
                    "reason": "severe_feature_extrapolation",
                    "features": ["heat_stress_observed_at_cutoff"],
                }
            }
            result["severe_out_of_domain_features"] = [
                {"feature": "heat_stress_observed_at_cutoff"}
            ]

        result = build_interpretation(
            {"fixed_gap_7d_v1": fixed, "lag_event_v1": lag},
            season_phase="main",
        )

        self.assertEqual(result["verdict"], "unfavorable")
        self.assertEqual(
            result["reference_range"],
            {"min": 0.16, "max": 0.17, "midpoint": 0.165},
        )
        self.assertEqual(
            {row["estimator_id"] for row in result["trusted_results"]},
            {"random_forest_restricted_v1"},
        )
        self.assertEqual(result["validated_estimator_count"], 1)
        self.assertEqual(result["statistical_support"], "limited")
        self.assertEqual(result["statistical_consensus"], "unavailable")
        self.assertIn(
            "logistic_regression_excluded_out_of_domain",
            result["reason_codes"],
        )

    def test_extreme_validated_feature_set_conflict_forces_abstention(self) -> None:
        result = build_interpretation(
            {
                "fixed_gap_7d_v1": model(0.0, 0.2, 0.17, 0.19),
                "lag_event_v1": model(1.0, 0.8, 0.17, 0.19),
            },
            season_phase="main",
        )

        self.assertEqual(result["verdict"], "abstain")
        self.assertIsNone(result["reference_range"])
        self.assertIn("feature_sets_conflict_extremely", result["reason_codes"])

    def test_warns_when_feature_sets_use_different_weather_stations(self) -> None:
        fixed = model(0.90, 0.58, 0.21, 0.18)
        fixed["weather_station_code"] = "IGUILS1"
        lag = model(0.24, 0.52, 0.19, 0.15)
        lag["weather_station_code"] = "IMERAN22"

        result = build_interpretation(
            {"fixed_gap_7d_v1": fixed, "lag_event_v1": lag},
            season_phase="main",
        )

        self.assertIn(
            "feature_sets_use_different_stations",
            result["reason_codes"],
        )
        self.assertEqual(
            result["weather_stations_by_feature_set"],
            {
                "fixed_gap_7d_v1": "IGUILS1",
                "lag_event_v1": "IMERAN22",
            },
        )

    def test_old_rain_event_vetoes_favorable_statistical_score_for_any_species(self) -> None:
        strong = model(1.0, 0.64, 0.17, 0.19)
        strong["features_used"].update(
            {
                "significant_rain_found_90d": 0.0,
                "days_since_significant_rain_at_target": 90.0,
            }
        )
        result = build_interpretation(
            {"fixed_gap_7d_v1": strong, "lag_event_v1": strong},
            season_phase="main",
            phenology={
                "fruiting_delay_after_rain_days": {
                    "min": 5,
                    "optimal_min": 7,
                    "optimal_max": 15,
                    "max": 21,
                }
            },
        )

        self.assertEqual(result["verdict"], "unfavorable")
        self.assertIsNone(result["reference_range"])
        self.assertEqual(result["confidence"], "high")
        self.assertEqual(result["ecological_compatibility"], "incompatible")
        self.assertEqual(result["ecological_evidence"], "high")
        self.assertIn("ecological_rain_guardrail", result["reason_codes"])

    def test_any_validated_estimator_can_supply_the_operational_score(self) -> None:
        fixed = with_svm(model(0.0, 0.36, 0.26, 0.28), 0.66, 0.19)
        lag = with_svm(model(0.0, 0.30, 0.30, 0.29), 0.67, 0.18)
        lag["severe_out_of_domain_features"] = [
            {"feature": "heat_stress_observed_at_cutoff"}
        ]

        result = build_interpretation(
            {"fixed_gap_7d_v1": fixed, "lag_event_v1": lag},
            season_phase="main",
            phenology={
                "fruiting_delay_after_rain_days": {
                    "min": 5,
                    "optimal_min": 7,
                    "optimal_max": 15,
                    "max": 21,
                }
            },
        )

        self.assertEqual(result["verdict"], "favorable")
        self.assertEqual(result["statistical_support"], "limited")
        self.assertEqual(
            result["reference_range"],
            {"min": 0.66, "max": 0.67, "midpoint": 0.665},
        )
        self.assertEqual(
            {row["estimator_id"] for row in result["trusted_results"]},
            {"rbf_svm_calibrated_v1"},
        )
        self.assertEqual(result["experimental_signal"], "unavailable")

    def test_generic_validated_estimator_conflict_is_reflected_in_the_verdict(self) -> None:
        fixed = with_svm(model(0.5, 0.5, 0.26, 0.28), 0.70)
        lag = with_svm(model(0.5, 0.5, 0.30, 0.29), 0.30)

        result = build_interpretation(
            {"fixed_gap_7d_v1": fixed, "lag_event_v1": lag},
            season_phase="main",
        )

        self.assertEqual(result["verdict"], "uncertain")
        self.assertEqual(
            result["reference_range"],
            {"min": 0.3, "max": 0.7, "midpoint": 0.5},
        )

    def test_version_specific_estimator_family_is_selected_without_name_changes(self) -> None:
        fixed = model(0.5, 0.5, 0.30, 0.29)
        fixed["estimator_probabilities"]["elastic_net_logistic_raw365_v1"] = 0.73
        fixed["evaluation"]["estimators"]["elastic_net_logistic_raw365_v1"] = {
            "n": 11,
            "brier_score": 0.17,
            "roc_auc": 0.81,
        }

        result = build_interpretation(
            {"fixed_gap_7d_v1": fixed}, season_phase="main"
        )

        self.assertEqual(result["trusted_results"][0]["estimator_id"], "elastic_net_logistic_raw365_v1")
        self.assertEqual(result["reference_range"]["midpoint"], 0.73)
