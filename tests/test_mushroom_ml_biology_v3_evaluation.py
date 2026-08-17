from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from rainmapper_core import mushroom_ml_biology_v3_evaluation as evaluation
from rainmapper_core import mushroom_ml_experiments
from rainmapper_core import mushroom_ml_version_registry as version_registry


def sample(index: int, target: str, group_7: str, group_14: str) -> dict:
    return {
        "sample_id": str(index),
        "prediction_target": target,
        "predictive_features": {
            "rain_cutoff_0_3d_mm": float(index),
            "temp_mean_cutoff_7d_c": 10.0 + index,
        },
        "quality": {"training_eligible": True},
        "metadata": {
            "species_id": "species",
            "target_date": f"2026-01-{index:02d}",
            "validation_group_7d": group_7,
            "validation_group_14d": group_14,
        },
    }


class BiologyV3EvaluationTests(unittest.TestCase):
    def test_v2_common_idw_reuses_v3_weather_row_instead_of_station_features(self) -> None:
        columns = mushroom_ml_experiments.FIXED_GAP_7D_ALTITUDE_V2.feature_cols
        legacy_quality = {
            "significant_rain_found_90d",
            "rain_observed_days_21",
            "rain_missing_days_21",
            "rain_suppressed_days_21",
            "rain_observed_days_90",
            "rain_missing_days_90",
            "rain_suppressed_days_90",
            "dry_spell_is_censored",
            "temp_observed_days_after_significant_rain",
            "humidity_observed_days_after_significant_rain",
        }
        source = {
            "sample_id": "source",
            "prediction_target": "favorable",
            "predictive_features": {
                name: float(index + 1)
                for index, name in enumerate(columns)
                if name not in legacy_quality
            },
            "quality": {
                "training_eligible": True,
                "training_exclusion_reasons": [],
                **{name: float(index + 1) for index, name in enumerate(sorted(legacy_quality))},
            },
            "metadata": {
                "observation_id": "obs",
                "species_id": "species",
                "area_id": "area",
                "target_date": "2026-01-01",
                "horizon_days": 7,
                "validation_group_7d": "g7",
                "validation_group_14d": "g14",
            },
        }
        benchmark = evaluation.build_observation_altitude_v2_common_idw_benchmark(
            {
                "feature_set": {"id": "fixed_gap_7d_biology_v3"},
                "weather_idw_contract_id": "weather-idw-test",
                "samples": [source],
            }
        )
        self.assertEqual(benchmark["training_eligible_sample_count"], 1)
        self.assertEqual(benchmark["weather_basis"], "common_multisource_area_idw")
        self.assertEqual(
            set(benchmark["samples"][0]["predictive_features"]), set(columns)
        )
        self.assertEqual(
            benchmark["samples"][0]["metadata"]["weather_idw_contract_id"],
            "weather-idw-test",
        )

    def test_chronological_split_never_breaks_fruiting_group(self) -> None:
        rows = [
            sample(1, "favorable", "g7a", "g14a"),
            sample(2, "unfavorable", "g7a", "g14a"),
            sample(3, "favorable", "g7b", "g14a"),
            sample(4, "unfavorable", "g7c", "g14b"),
            sample(5, "favorable", "g7d", "g14c"),
        ]
        train, test = evaluation.chronological_group_split(rows, group_days=14)
        train_groups = {row["metadata"]["validation_group_14d"] for row in train}
        test_groups = {row["metadata"]["validation_group_14d"] for row in test}
        self.assertFalse(train_groups & test_groups)
        self.assertEqual(len(train) + len(test), len(rows))

    def test_quality_fields_are_not_available_to_feature_families(self) -> None:
        benchmark = {
            "feature_set": {
                "id": "fixture",
                "predictive_feature_cols": [
                    "rain_cutoff_0_3d_mm",
                    "temp_mean_cutoff_7d_c",
                ],
            },
            "samples": [
                sample(1, "favorable", "a", "a"),
                sample(2, "unfavorable", "b", "b"),
                sample(3, "favorable", "c", "c"),
                sample(4, "unfavorable", "d", "d"),
                sample(5, "favorable", "e", "e"),
                sample(6, "unfavorable", "f", "f"),
            ],
        }
        report = evaluation.evaluate_benchmark(benchmark, group_days=7)
        for family in report["families"].values():
            self.assertNotIn("training_eligible", family["feature_cols"])
            if family["feature_cols"]:
                self.assertEqual(
                    set(family["estimator_status"]),
                    {
                        "logistic_regression_reduced_v1",
                        "random_forest_restricted_v1",
                        "extra_trees_restricted_v1",
                        "hist_gradient_boosting_restricted_v1",
                        "knn_distance_v1",
                        "rbf_svm_calibrated_v1",
                    },
                )
                self.assertEqual(
                    family["pooled_metrics_policy"],
                    "diagnostic_only_never_select_across_species",
                )
                self.assertEqual(
                    family["pairwise_consensus_contract"]["aggregate_policy"],
                    "report rates; do not invent one species-wide label",
                )
                active_pair = family["pairwise_consensus_by_species"]["species"][
                    "logistic_regression_reduced_v1__random_forest_restricted_v1"
                ]
                self.assertEqual(active_pair["n"], 2)
                self.assertEqual(active_pair["held_out_observation_count"], 2)
                self.assertEqual(
                    sum(
                        active_pair["prediction_consensus"][f"{level}_count"]
                        for level in ("high", "moderate", "low")
                    ),
                    active_pair["n"],
                )
        self.assertEqual(report["split"]["group_overlap_count"], 0)
        self.assertEqual(
            report["evaluation_axes"]["fitted_model_definition"],
            "one species x one temporal contract x one estimator",
        )
        self.assertFalse(report["model_artifact_written"])

    def test_matched_comparison_uses_identical_rows_and_split(self) -> None:
        v3_rows = [
            sample(1, "favorable", "a", "a"),
            sample(2, "unfavorable", "b", "b"),
            sample(3, "favorable", "c", "c"),
            sample(4, "unfavorable", "d", "d"),
            sample(5, "favorable", "e", "e"),
            sample(6, "unfavorable", "f", "f"),
        ]
        for row in v3_rows:
            row["metadata"]["observation_id"] = f"obs_{row['sample_id']}"
            row["metadata"]["horizon_days"] = 7
        v2_rows = []
        for row in v3_rows:
            clone = {
                **row,
                "predictive_features": {
                    "rain_cutoff_0_3d_mm": row["predictive_features"]["rain_cutoff_0_3d_mm"]
                },
            }
            v2_rows.append(clone)
        v2_rows.append(
            {
                **sample(7, "favorable", "g", "g"),
                "metadata": {
                    **sample(7, "favorable", "g", "g")["metadata"],
                    "observation_id": "v2_only",
                    "horizon_days": 7,
                },
            }
        )
        v2 = {
            "feature_set": {"id": "v2", "predictive_feature_cols": ["rain_cutoff_0_3d_mm"]},
            "samples": v2_rows,
        }
        v3 = {
            "feature_set": {
                "id": "v3",
                "predictive_feature_cols": ["rain_cutoff_0_3d_mm", "temp_mean_cutoff_7d_c"],
            },
            "samples": v3_rows,
        }
        report = evaluation.evaluate_matched_benchmarks(v2, v3, group_days=7)
        self.assertEqual(report["coverage"]["jointly_eligible"], 6)
        self.assertEqual(report["coverage"]["v2_only"], 1)
        self.assertEqual(report["altitude_v2"]["split"], report["biology_v3"]["split"])
        self.assertEqual(len(report["split"]["membership_sha256"]), 64)
        self.assertFalse(report["model_artifact_written"])

    def test_matched_comparison_rejects_different_partition_membership(self) -> None:
        rows = [
            sample(1, "favorable", "a", "a"),
            sample(2, "unfavorable", "b", "b"),
            sample(3, "favorable", "c", "c"),
            sample(4, "unfavorable", "d", "d"),
            sample(5, "favorable", "e", "e"),
            sample(6, "unfavorable", "f", "f"),
        ]
        for row in rows:
            row["metadata"]["observation_id"] = f"obs_{row['sample_id']}"
            row["metadata"]["horizon_days"] = 7
        changed = deepcopy(rows)
        changed[4]["metadata"]["validation_group_7d"] = "a"
        benchmark = {
            "feature_set": {
                "id": "fixture",
                "predictive_feature_cols": ["rain_cutoff_0_3d_mm"],
            },
            "samples": rows,
        }
        changed_benchmark = {**benchmark, "samples": changed}

        with self.assertRaisesRegex(AssertionError, "identical partitions"):
            evaluation.evaluate_matched_version_benchmarks(
                {"version_a": benchmark, "version_b": changed_benchmark},
                group_days=7,
            )

    def test_generic_comparison_accepts_future_versions_from_registry(self) -> None:
        rows = [
            sample(1, "favorable", "a", "a"),
            sample(2, "unfavorable", "b", "b"),
            sample(3, "favorable", "c", "c"),
            sample(4, "unfavorable", "d", "d"),
            sample(5, "favorable", "e", "e"),
            sample(6, "unfavorable", "f", "f"),
        ]
        for row in rows:
            row["metadata"]["observation_id"] = f"obs_{row['sample_id']}"
            row["metadata"]["horizon_days"] = 7
        benchmark = {
            "feature_set": {
                "id": "fixture",
                "predictive_feature_cols": [
                    "rain_cutoff_0_3d_mm",
                    "temp_mean_cutoff_7d_c",
                ],
            },
            "samples": rows,
        }
        registry_path = (
            Path(__file__).resolve().parents[1]
            / "mushroom-data"
            / "mushroom_ml_version_registry.json"
        )
        registry = version_registry.register_version(
            version_registry.load_registry(registry_path),
            {
                "version_id": "biology_v5",
                "status": "candidate",
                "temporal_contract_ids": ["fixture_v5"],
                "generations": [],
            },
        )

        report = evaluation.evaluate_matched_version_benchmarks(
            {
                "altitude_v2": deepcopy(benchmark),
                "biology_v3": deepcopy(benchmark),
                "biology_v5": deepcopy(benchmark),
            },
            group_days=7,
            version_registry=registry,
        )

        self.assertEqual(
            report["version_ids"],
            ["altitude_v2", "biology_v3", "biology_v5"],
        )
        self.assertEqual(report["coverage"]["jointly_eligible"], 6)
        self.assertEqual(set(report["versions"]), set(report["version_ids"]))
        self.assertEqual(report["version_registry"]["biology_v5"]["status"], "candidate")
        self.assertEqual(
            report["selection_policy"],
            "select per species, temporal contract and estimator; pooled scores are diagnostic only",
        )

    def test_generic_comparison_reuses_identical_version_evaluations(self) -> None:
        rows = [
            sample(1, "favorable", "a", "a"),
            sample(2, "unfavorable", "b", "b"),
            sample(3, "favorable", "c", "c"),
            sample(4, "unfavorable", "d", "d"),
            sample(5, "favorable", "e", "e"),
            sample(6, "unfavorable", "f", "f"),
        ]
        for row in rows:
            row["metadata"]["observation_id"] = f"obs_{row['sample_id']}"
            row["metadata"]["horizon_days"] = 7
        benchmark = {
            "feature_set": {
                "id": "cached_fixture",
                "predictive_feature_cols": ["rain_cutoff_0_3d_mm"],
            },
            "samples": rows,
        }
        cache: dict[tuple[object, ...], dict] = {}
        fake_report = {"split": {"method": "fixture"}, "families": {}}

        with patch.object(
            evaluation, "evaluate_benchmark", return_value=fake_report
        ) as mocked:
            first = evaluation.evaluate_matched_version_benchmarks(
                {"version_a": benchmark, "version_b": deepcopy(benchmark)},
                group_days=7,
                evaluation_cache=cache,
            )
            second = evaluation.evaluate_matched_version_benchmarks(
                {"version_a": benchmark, "version_b": deepcopy(benchmark)},
                group_days=7,
                evaluation_cache=cache,
            )

        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(first, second)

    def test_lag_horizons_filter_one_full_model_evaluation_without_refit(self) -> None:
        rows = []
        for index in range(1, 7):
            for horizon_days in (1, 2, 3, 7):
                row = sample(
                    index,
                    "favorable" if index % 2 else "unfavorable",
                    f"g7_{index}",
                    f"g14_{index}",
                )
                row["sample_id"] = f"{index}|h{horizon_days}"
                row["metadata"]["observation_id"] = f"obs_{index}"
                row["metadata"]["horizon_days"] = horizon_days
                rows.append(row)
        benchmark = {
            "feature_set": {
                "id": "lag_fixture",
                "predictive_feature_cols": ["rain_cutoff_0_3d_mm"],
            },
            "samples": rows,
        }
        fake_report = {
            "split": {
                "method": "fixture",
                "eligible_samples": len(rows),
            },
            "families": {},
        }

        with patch.object(
            evaluation, "evaluate_benchmark", return_value=fake_report
        ) as mocked:
            report = evaluation.evaluate_matched_version_benchmarks(
                {"version_a": benchmark, "version_b": deepcopy(benchmark)},
                group_days=14,
            )

        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(set(report["by_horizon"]), {"1", "2", "3", "7"})
        for horizon_report in report["by_horizon"].values():
            self.assertEqual(
                horizon_report["evaluation_method"],
                "filter_predictions_from_full_temporal_contract_model_no_refit",
            )

    def test_production_v2_replay_builder_remains_available(self) -> None:
        feature_rows = [
            {
                "observation_id": "obs_1",
                "species_id": "boletus_edulis",
                "micro_area_id": "micro_1",
                "observed_at": "2026-01-10",
                "validation_status": "valid",
                "calibration_use": "include",
                "prediction_target": "favorable",
            }
        ]
        v3 = {
            "feature_set": {"id": "fixed_gap_7d_biology_v3"},
            "samples": [
                {
                    "metadata": {
                        "observation_id": "obs_1",
                        "species_id": "boletus_edulis",
                        "area_id": "area_1",
                        "target_date": "2026-01-10",
                        "horizon_days": 7,
                        "validation_group_7d": "g7",
                        "validation_group_14d": "g14",
                    }
                }
            ],
        }
        fake_features = {
            name: 1.0
            for name in mushroom_ml_experiments.FIXED_GAP_7D_ALTITUDE_V2.feature_cols
        }
        with patch.object(
            mushroom_ml_experiments,
            "build_fixed_gap_7d_altitude_features",
            return_value=(fake_features, {"training_ineligibility_reasons": []}),
        ):
            benchmark = evaluation.build_observation_altitude_v2_benchmark(
                feature_rows,
                v3,
                micro_area_to_area={"micro_1": "area_1"},
                area_representative_altitudes={"area_1": 1000.0},
            )

        self.assertEqual(benchmark["sample_count"], 1)
        self.assertEqual(benchmark["training_eligible_sample_count"], 1)
        self.assertEqual(benchmark["samples"][0]["prediction_target"], "favorable")


if __name__ == "__main__":
    unittest.main()
