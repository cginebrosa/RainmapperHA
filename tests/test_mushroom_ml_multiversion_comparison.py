from datetime import date, timedelta
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest import mock

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLMultiversionComparisonTests(TestCase):
    def test_operational_selections_keep_only_the_dated_horizon(self) -> None:
        selections = [
            {
                "version_id": "biology_v3",
                "temporal_contract_id": "fixed_gap_7d_biology_v3",
                "profile_id": "core",
                "estimator_id": "random_forest_restricted_v1",
                "horizon_days": 7,
            },
            *[
                {
                    "version_id": "biology_v3",
                    "temporal_contract_id": "lag_event_biology_v3",
                    "profile_id": "core",
                    "estimator_id": "random_forest_restricted_v1",
                    "horizon_days": horizon,
                }
                for horizon in range(1, 8)
            ],
        ]

        selected = comparison.operational_selections(
            selections,
            target_date=date(2026, 8, 22),
            issue_date=date(2026, 8, 22),
        )

        self.assertEqual(
            {(row["temporal_contract_id"], row["horizon_days"]) for row in selected},
            {
                ("fixed_gap_7d_biology_v3", 7),
                ("lag_event_biology_v3", 1),
            },
        )

    def test_retarget_operational_selections_reuses_models_for_each_week_horizon(self) -> None:
        selections = [
            {
                "version_id": "biology_v6_windowed_smooth_hierarchical",
                "temporal_contract_id": "fixed_gap_7d_biology_v6_smooth_hierarchical_v2",
                "profile_id": "smooth_window_60d_plus_physical_state",
                "estimator_id": "smooth_shared_logistic_v1",
                "horizon_days": 7,
            },
            {
                "version_id": "biology_v6_windowed_smooth_hierarchical",
                "temporal_contract_id": "lag_event_biology_v6_smooth_hierarchical_v2",
                "profile_id": "smooth_window_60d_plus_physical_state",
                "estimator_id": "smooth_shared_logistic_v1",
                "horizon_days": 1,
            },
        ]

        retargeted = comparison.retarget_operational_selections(
            selections,
            target_date=date(2026, 8, 24),
            issue_date=date(2026, 8, 22),
        )

        self.assertEqual(
            {
                (row["temporal_contract_id"], row["horizon_days"])
                for row in retargeted
            },
            {
                (
                    "fixed_gap_7d_biology_v6_smooth_hierarchical_v2",
                    7,
                ),
                (
                    "lag_event_biology_v6_smooth_hierarchical_v2",
                    3,
                ),
            },
        )

    def test_selected_operational_comparison_chooses_across_versions(self) -> None:
        def member(
            version_id: str,
            estimator_id: str,
            probability: float,
            *,
            brier: float,
            improvement: float,
            contract: str = "fixed",
            applicability: str = "within_observed_range",
        ) -> dict[str, object]:
            contract_id = (
                f"fixed_gap_7d_{version_id}"
                if contract == "fixed"
                else f"lag_event_{version_id}"
            )
            return {
                "model_ref": {
                    "version_id": version_id,
                    "temporal_contract_id": contract_id,
                    "profile_id": "core",
                    "estimator_id": estimator_id,
                    "horizon_days": 7 if contract == "fixed" else 1,
                },
                "available": True,
                "prediction": {
                    "probability": probability,
                    "applicability": {"status": applicability},
                },
                "evaluation": {
                    "evidence": "better_than_prevalence",
                    "brier_score": brier,
                    "prevalence_brier_score": brier + improvement,
                    "brier_delta_vs_prevalence": improvement,
                    "roc_auc": 0.8,
                    "n_test": 20,
                },
                "features_used": {
                    "significant_rain_found_90d": True,
                    "days_since_significant_rain_at_target": 4,
                },
            }

        result = comparison.build_selected_operational_comparison(
            [
                member("biology_v3", "logistic_regression_reduced_v1", 0.61, brier=0.22, improvement=0.08),
                member("biology_v4", "rbf_svm_calibrated_v1", 0.74, brier=0.18, improvement=0.17),
                member("biology_v3", "random_forest_restricted_v1", 0.66, brier=0.19, improvement=0.14, contract="lag"),
            ],
            season_phase="in_season",
            phenology={
                "fruiting_delay_after_rain_days": {
                    "min": 0,
                    "optimal_min": 2,
                    "optimal_max": 14,
                    "max": 30,
                }
            },
        )

        winners = {
            row["result_key"]: row for row in result["selected_winners"]
        }
        self.assertEqual(
            winners["selected:fixed:h7"]["model_ref"]["version_id"],
            "biology_v4",
        )
        self.assertEqual(
            winners["selected:fixed:h7"]["model_ref"]["estimator_id"],
            "rbf_svm_calibrated_v1",
        )
        self.assertEqual(
            result["interpretation"]["reference_range"],
            {"min": 0.66, "max": 0.74, "midpoint": 0.7},
        )

    def test_selected_operational_comparison_accepts_caution_but_not_outside_domain(self) -> None:
        def member(estimator_id: str, probability: float, applicability: str, improvement: float) -> dict[str, object]:
            return {
                "model_ref": {
                    "version_id": "biology_v4",
                    "temporal_contract_id": "fixed_gap_7d_biology_v4",
                    "profile_id": "climatic_balance",
                    "estimator_id": estimator_id,
                    "horizon_days": 7,
                },
                "available": True,
                "prediction": {
                    "probability": probability,
                    "applicability": {"status": applicability},
                },
                "evaluation": {
                    "evidence": "better_than_prevalence",
                    "brier_score": 0.455 - improvement,
                    "prevalence_brier_score": 0.455,
                    "brier_delta_vs_prevalence": improvement,
                    "roc_auc": 0.7,
                    "n_test": 26,
                },
            }

        result = comparison.build_selected_operational_comparison(
            [
                member("logistic_regression_reduced_v1", 0.78, "caution", 0.147),
                member("random_forest_restricted_v1", 0.91, "outside_domain", 0.2),
            ],
            season_phase="in_season",
        )

        winner = result["selected_winners"][0]
        self.assertEqual(
            winner["model_ref"]["estimator_id"],
            "logistic_regression_reduced_v1",
        )
        self.assertEqual(winner["probability"], 0.78)
        self.assertEqual(winner["applicability_status"], "caution")

    def test_selected_operational_comparison_abstains_when_brier_is_worse_than_prevalence(self) -> None:
        member = {
            "model_ref": {
                "version_id": "biology_v3",
                "temporal_contract_id": "lag_event_biology_v3",
                "profile_id": "core",
                "estimator_id": "rbf_svm_calibrated_v1",
                "horizon_days": 5,
            },
            "available": True,
            "prediction": {
                "probability": 0.41,
                "applicability": {"status": "within_observed_range"},
            },
            "evaluation": {
                "evidence": "worse_than_prevalence",
                "brier_score": 0.252,
                "prevalence_brier_score": 0.250,
                "brier_delta_vs_prevalence": -0.002,
                "roc_auc": 0.541,
                "n_test": 42,
            },
        }

        result = comparison.build_selected_operational_comparison(
            [member],
            season_phase="in_season",
        )

        self.assertEqual(result["selected_winners"], [])
        self.assertFalse(result["selected:lag:h5"]["available"])
        self.assertEqual(
            result["selected:lag:h5"]["reason"],
            "no_eligible_selected_member",
        )

    def test_selected_operational_comparison_rejects_auc_below_055(self) -> None:
        def member(estimator_id: str, *, brier: float, roc_auc: float) -> dict[str, object]:
            return {
                "model_ref": {
                    "version_id": "biology_v3",
                    "temporal_contract_id": "fixed_gap_7d_biology_v3",
                    "profile_id": "core",
                    "estimator_id": estimator_id,
                    "horizon_days": 7,
                },
                "available": True,
                "prediction": {
                    "probability": 0.72,
                    "applicability": {"status": "within_observed_range"},
                },
                "evaluation": {
                    "evidence": "better_than_prevalence",
                    "brier_score": brier,
                    "prevalence_brier_score": 0.30,
                    "brier_delta_vs_prevalence": 0.30 - brier,
                    "roc_auc": roc_auc,
                    "n_test": 24,
                },
            }

        result = comparison.build_selected_operational_comparison(
            [
                member("random_forest_restricted_v1", brier=0.12, roc_auc=0.375),
                member("logistic_regression_reduced_v1", brier=0.18, roc_auc=0.55),
            ],
            season_phase="in_season",
        )

        winner = result["selected_winners"][0]
        self.assertEqual(
            winner["model_ref"]["estimator_id"],
            "logistic_regression_reduced_v1",
        )
        self.assertEqual(winner["roc_auc"], 0.55)
        exclusions = result["selected:fixed:h7"]["candidate_exclusions"]
        self.assertEqual(exclusions[0]["reasons"], ["roc_auc_below_minimum"])

    def test_selected_operational_comparison_measures_consensus_between_eligible_families(self) -> None:
        def member(
            estimator_id: str,
            probability: float,
            *,
            brier: float,
            roc_auc: float,
        ) -> dict[str, object]:
            return {
                "model_ref": {
                    "version_id": "biology_v4",
                    "temporal_contract_id": "fixed_gap_7d_biology_v4",
                    "profile_id": "climatic_balance",
                    "estimator_id": estimator_id,
                    "horizon_days": 7,
                },
                "available": True,
                "prediction": {
                    "probability": probability,
                    "applicability": {"status": "within_observed_range"},
                },
                "evaluation": {
                    "evidence": "better_than_prevalence",
                    "brier_score": brier,
                    "prevalence_brier_score": 0.455,
                    "brier_delta_vs_prevalence": 0.455 - brier,
                    "roc_auc": roc_auc,
                    "n_test": 26,
                },
            }

        result = comparison.build_selected_operational_comparison(
            [
                member("logistic_regression_reduced_v1", 0.63, brier=0.308, roc_auc=0.667),
                member("random_forest_restricted_v1", 0.59, brier=0.360, roc_auc=0.583),
                member("extra_trees_restricted_v1", 0.69, brier=0.439, roc_auc=0.50),
            ],
            season_phase="in_season",
        )

        winner = result["selected_winners"][0]
        self.assertEqual(
            winner["model_ref"]["estimator_id"],
            "logistic_regression_reduced_v1",
        )
        scenario = result["scenario_consensus"][0]
        self.assertEqual(scenario["status"], "high")
        self.assertEqual(scenario["eligible_family_count"], 2)
        self.assertEqual(
            scenario["eligible_estimator_ids"],
            ["logistic_regression_reduced_v1", "random_forest_restricted_v1"],
        )
        self.assertAlmostEqual(scenario["maximum_probability_gap"], 0.04)
        self.assertEqual(len(result["selected:fixed:h7"]["eligible_candidates"]), 2)

    def test_selected_operational_comparison_uses_auc_only_after_equal_brier(self) -> None:
        members = []
        for estimator_id, roc_auc in (
            ("logistic_regression_reduced_v1", 0.61),
            ("random_forest_restricted_v1", 0.72),
        ):
            members.append(
                {
                    "model_ref": {
                        "version_id": "biology_v4",
                        "temporal_contract_id": "fixed_gap_7d_biology_v4",
                        "profile_id": "climatic_balance",
                        "estimator_id": estimator_id,
                        "horizon_days": 7,
                    },
                    "available": True,
                    "prediction": {
                        "probability": 0.61,
                        "applicability": {"status": "within_observed_range"},
                    },
                    "evaluation": {
                        "evidence": "better_than_prevalence",
                        "brier_score": 0.20,
                        "prevalence_brier_score": 0.30,
                        "brier_delta_vs_prevalence": 0.10,
                        "roc_auc": roc_auc,
                        "n_test": 20,
                    },
                }
            )

        result = comparison.build_selected_operational_comparison(
            members,
            season_phase="in_season",
        )

        self.assertEqual(
            result["selected_winners"][0]["model_ref"]["estimator_id"],
            "random_forest_restricted_v1",
        )

    def test_smooth_variants_are_internal_agreement_not_independent_families(self) -> None:
        def member(estimator_id: str, probability: float, brier: float) -> dict[str, object]:
            return {
                "model_ref": {
                    "version_id": "biology_v6_windowed_smooth_hierarchical",
                    "temporal_contract_id": "fixed_gap_7d_windowed_smooth_v1",
                    "profile_id": "window_30d",
                    "estimator_id": estimator_id,
                    "horizon_days": 7,
                },
                "available": True,
                "prediction": {
                    "probability": probability,
                    "applicability": {"status": "within_observed_range"},
                },
                "evaluation": {
                    "evidence": "better_than_prevalence",
                    "brier_score": brier,
                    "prevalence_brier_score": 0.25,
                    "brier_delta_vs_prevalence": 0.25 - brier,
                    "roc_auc": 0.76,
                    "n_test": 71,
                },
            }

        result = comparison.build_selected_operational_comparison(
            [
                member("smooth_partial_pooling_logistic_v1", 0.60, 0.14),
                member("smooth_shared_logistic_v1", 0.63, 0.15),
            ],
            season_phase="in_season",
        )

        scenario = result["scenario_consensus"][0]
        self.assertEqual(scenario["status"], "single_family")
        self.assertEqual(scenario["eligible_family_count"], 1)
        self.assertEqual(
            scenario["eligible_methodological_family_ids"], ["logistic"]
        )
        logistic = scenario["methodological_families"][0]
        self.assertEqual(logistic["internal_agreement_status"], "high")
        self.assertAlmostEqual(
            logistic["internal_maximum_probability_gap"], 0.03
        )
        self.assertEqual(result["selected_winners"][0]["test_samples"], 71)

    def test_glanceable_statistical_verdicts_use_weakest_scenario(self) -> None:
        def member(
            estimator_id: str,
            probability: float,
            *,
            contract_id: str,
            brier: float,
            baseline: float,
            roc_auc: float,
            n_test: int,
            positive: int,
            negative: int,
        ) -> dict[str, object]:
            return {
                "model_ref": {
                    "version_id": "biology_v4",
                    "temporal_contract_id": contract_id,
                    "profile_id": "profile",
                    "estimator_id": estimator_id,
                    "horizon_days": 7 if contract_id.startswith("fixed_") else 3,
                },
                "available": True,
                "prediction": {
                    "probability": probability,
                    "applicability": {"status": "within_observed_range"},
                },
                "evaluation": {
                    "evidence": "better_than_prevalence",
                    "brier_score": brier,
                    "prevalence_brier_score": baseline,
                    "brier_delta_vs_prevalence": baseline - brier,
                    "roc_auc": roc_auc,
                    "n_test": n_test,
                    "test_positive_count": positive,
                    "test_negative_count": negative,
                },
            }

        result = comparison.build_selected_operational_comparison(
            [
                member(
                    "logistic_regression_reduced_v1", 0.60,
                    contract_id="fixed_gap_7d_biology_v4", brier=0.14,
                    baseline=0.25, roc_auc=0.83, n_test=60,
                    positive=20, negative=40,
                ),
                member(
                    "random_forest_restricted_v1", 0.40,
                    contract_id="lag_event_biology_v4", brier=0.20,
                    baseline=0.25, roc_auc=0.75, n_test=40,
                    positive=15, negative=25,
                ),
                member(
                    "logistic_regression_reduced_v1", 0.62,
                    contract_id="lag_event_biology_v4", brier=0.21,
                    baseline=0.25, roc_auc=0.74, n_test=40,
                    positive=15, negative=25,
                ),
            ],
            season_phase="in_season",
        )

        self.assertEqual(
            result["statistical_reliability_summary"]["status"], "moderate"
        )
        self.assertEqual(result["consensus_summary"]["status"], "low")
        self.assertEqual(
            result["consensus_summary"]["measurable_scenario_count"], 1
        )
        self.assertEqual(result["consensus_summary"]["eligible_scenario_count"], 2)

    def test_selected_operational_comparison_abstains_without_eligible_auc(self) -> None:
        members = []
        for estimator_id, roc_auc in (
            ("random_forest_restricted_v1", 0.49),
            ("extra_trees_restricted_v1", None),
        ):
            members.append(
                {
                    "model_ref": {
                        "version_id": "biology_v3",
                        "temporal_contract_id": "lag_event_biology_v3",
                        "profile_id": "core",
                        "estimator_id": estimator_id,
                        "horizon_days": 3,
                    },
                    "available": True,
                    "prediction": {
                        "probability": 0.63,
                        "applicability": {"status": "caution"},
                    },
                    "evaluation": {
                        "evidence": "better_than_prevalence",
                        "brier_score": 0.18,
                        "prevalence_brier_score": 0.25,
                        "brier_delta_vs_prevalence": 0.07,
                        "roc_auc": roc_auc,
                        "n_test": 18,
                    },
                }
            )

        result = comparison.build_selected_operational_comparison(
            members,
            season_phase="in_season",
        )

        scenario = result["selected:lag:h3"]
        self.assertEqual(result["selected_winners"], [])
        self.assertFalse(scenario["available"])
        self.assertEqual(scenario["reason"], "no_eligible_selected_member")
        self.assertEqual(
            {reason for row in scenario["candidate_exclusions"] for reason in row["reasons"]},
            {"roc_auc_below_minimum", "roc_auc_unavailable"},
        )
        self.assertEqual(result["minimum_roc_auc"], 0.55)

    def test_interpretation_features_include_rain_evidence_without_changing_model_inputs(self) -> None:
        predictive = {"rain_sum_21d": 12.0, "days_since_significant_rain_at_target": 4.0}
        sample = {
            "predictive_features": predictive,
            "quality": {
                "significant_rain_found_90d": 1.0,
                "significant_rain_search_complete": True,
            },
        }

        result = comparison._interpretation_features(sample)

        self.assertEqual(result["significant_rain_found_90d"], 1.0)
        self.assertTrue(result["significant_rain_search_complete"])
        self.assertNotIn("significant_rain_found_90d", predictive)

    def test_interpretation_features_inherit_nested_v4_rain_evidence(self) -> None:
        sample = {
            "predictive_features": {"climatic_balance_mm": 4.0},
            "quality": {
                "source_v3_quality": {
                    "significant_rain_found_90d": True,
                    "days_since_significant_rain_at_target": 8.0,
                }
            },
        }

        result = comparison._interpretation_features(sample)

        self.assertTrue(result["significant_rain_found_90d"])
        self.assertEqual(result["days_since_significant_rain_at_target"], 8.0)

    def test_interpretation_features_find_common_evidence_through_any_adapter_depth(self) -> None:
        sample = {
            "predictive_features": {"rain_cutoff_0_3d_mm": 12.0},
            "quality": {
                "adapter_quality": {
                    "source_quality": {
                        "significant_rain_found_90d": True,
                        "significant_rain_search_complete": True,
                        "days_since_significant_rain_at_target": 4.0,
                    }
                }
            },
        }

        result = comparison._interpretation_features(sample)

        self.assertTrue(result["significant_rain_found_90d"])
        self.assertTrue(result["significant_rain_search_complete"])
        self.assertEqual(result["days_since_significant_rain_at_target"], 4.0)

    def test_every_operational_version_preserves_brier_rain_and_final_range(self) -> None:
        base_registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        for version in base_registry["versions"]:
            version_id = str(version["version_id"])
            profiles = [
                row
                for row in catalog.catalog_entries(base_registry)
                if row["version_id"] == version_id
                and row["operational_eligible"] is True
            ]
            if not profiles:
                # Retired versions (status "reference") keep their registry
                # entry for historical archives but no longer declare any
                # operationally-eligible profile; they cannot become the
                # active operational target.
                continue
            registry = copy.deepcopy(base_registry)
            registry["preferred_version_id"] = version_id
            profiles = [
                row
                for row in catalog.catalog_entries(registry)
                if row["version_id"] == version_id
                and row["operational_eligible"] is True
            ]
            artifacts = []
            for profile in profiles:
                estimator_id = str(profile["estimator_ids"][0])
                for contract_id in profile["temporal_contract_ids"]:
                    ref = catalog.ModelArtifactRef(
                        batch_id=f"batch-{version_id}",
                        generation_id=f"generation-{version_id}",
                        version_id=version_id,
                        temporal_contract_id=str(contract_id),
                        profile_id=str(profile["profile_id"]),
                        estimator_id=estimator_id,
                        species_id="boletus_edulis",
                    )
                    artifacts.append(
                        {
                            "artifact_ref": ref.as_dict(),
                            "supported_horizons": (
                                [7]
                                if str(contract_id).startswith("fixed_")
                                else list(range(1, 8))
                            ),
                            "path": catalog.model_relative_path(ref).as_posix(),
                            "sha256": "b" * 64,
                        }
                    )
            manifest = {
                "batch_id": f"batch-{version_id}",
                "snapshot_id": "sha256:" + "a" * 64,
                "artifacts": artifacts,
            }

            def compared(_registry, _manifest, selections, **_kwargs):
                return {
                    "members": [
                        {
                            "model_ref": {
                                **next(
                                    artifact["artifact_ref"]
                                    for artifact in artifacts
                                    if artifact["artifact_ref"]["version_id"]
                                    == selection["version_id"]
                                    and artifact["artifact_ref"]["profile_id"]
                                    == selection["profile_id"]
                                    and artifact["artifact_ref"]["temporal_contract_id"]
                                    == selection["temporal_contract_id"]
                                    and artifact["artifact_ref"]["estimator_id"]
                                    == selection["estimator_id"]
                                ),
                                "horizon_days": selection["horizon_days"],
                            },
                            "available": True,
                            "prediction": {
                                "probability": 0.72,
                                "applicability": {"status": "within_observed_range"},
                            },
                            "evaluation": {
                                "evidence": "better_than_prevalence",
                                "brier_score": 0.18,
                                "prevalence_brier_score": 0.25,
                                "brier_delta_vs_prevalence": 0.07,
                                "roc_auc": 0.71,
                                "n_test": 20,
                            },
                            "features_used": {
                                "significant_rain_found_90d": True,
                                "days_since_significant_rain_at_target": 4.0,
                            },
                            "metadata": {"cutoff_date": "2026-08-18"},
                        }
                        for selection in selections
                    ]
                }

            with self.subTest(version_id=version_id), mock.patch.object(
                comparison.catalog,
                "validate_batch_manifest",
                return_value=manifest,
            ), mock.patch.object(
                comparison, "compare_selection", side_effect=compared
            ):
                result = comparison.compare_operational_reference(
                    registry,
                    manifest,
                    species_id="boletus_edulis",
                    area_id="area-a",
                    target_date=date(2026, 8, 20),
                    issue_date=date(2026, 8, 19),
                    season_phase="in_season",
                    phenology={
                        "fruiting_delay_after_rain_days": {
                            "min": 0,
                            "optimal_min": 2,
                            "optimal_max": 14,
                            "max": 30,
                        }
                    },
                    models_root=Path("/unused/models"),
                    known_sites_path=Path("/unused/sites.json"),
                    weather_data_dir=Path("/unused/weather"),
                )

            self.assertEqual(result["interpretation"]["weather_signal"], "recent_event")
            self.assertEqual(result["interpretation"]["ecological_compatibility"], "compatible")
            self.assertEqual(result["interpretation"]["reference_range"]["min"], 0.72)
            self.assertEqual(result["selection_mode"], "preferred_version")
            self.assertTrue(result["selected_winners"])
            for key in result["comparison_detail_result_keys"]:
                self.assertTrue(result[key]["evaluation"]["available"])
                self.assertEqual(
                    next(iter(result[key]["evaluation"]["estimators"].values()))[
                        "brier_score"
                    ],
                    0.18,
                )

    def test_installed_generation_never_falls_back_to_old_benchmark_quality(self) -> None:
        quality = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_quality_catalog",
            "snapshot_id": "sha256:" + "a" * 64,
            "entries": [],
        }
        content = (json.dumps(quality) + "\n").encode()
        digest = hashlib.sha256(content).hexdigest()
        registry = {
            "versions": [
                {
                    "version_id": "biology_v3",
                    "generations": [
                        {
                            "generation_id": "generation-v3",
                            "source_benchmark_batch_id": "benchmark-v3",
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            benchmark = root / "benchmarks" / "benchmark-v3"
            benchmark.mkdir(parents=True)
            (benchmark / "quality-catalog.json").write_bytes(content)
            (benchmark / "manifest.json").write_text(
                json.dumps(
                    {
                        "quality_catalog": {
                            "path": "batches/benchmark-v3/quality-catalog.json",
                            "sha256": digest,
                        }
                    }
                ),
                encoding="utf-8",
            )

            loaded = comparison._load_quality_catalog(registry, {}, root)

        self.assertEqual(loaded, {})

    def test_preferred_v3_exposes_both_profiles_and_both_temporal_contracts(self) -> None:
        registry = copy.deepcopy(mushroom_ml_version_registry.load_registry(REGISTRY_PATH))
        v3 = next(
            version for version in registry["versions"]
            if version["version_id"] == "biology_v3"
        )
        v3["generations"] = [
            {
                "generation_id": "generation-v3",
                "version_id": "biology_v3",
                "kind": "trained_model",
                "retention": "permanent",
                "promotion_gate_status": "passed",
                "profile_ids": ["core", "common_idw_plus_physical_state"],
                "batch_id": "batch-v3",
            }
        ]
        v3["installed_generation_id"] = "generation-v3"
        registry["preferred_version_id"] = "biology_v3"
        registry = mushroom_ml_version_registry.validate_registry(registry)
        artifacts = []
        members = []
        for profile_id in ("core", "common_idw_plus_physical_state"):
            for contract_id, horizons in (
                ("fixed_gap_7d_biology_v3", [7]),
                ("lag_event_biology_v3", list(range(1, 8))),
            ):
                ref = catalog.ModelArtifactRef(
                    batch_id="batch-v3",
                    generation_id="generation-v3",
                    version_id="biology_v3",
                    temporal_contract_id=contract_id,
                    profile_id=profile_id,
                    estimator_id="logistic_regression_reduced_v1",
                    species_id="boletus_edulis",
                )
                artifacts.append(
                    {
                        "artifact_ref": ref.as_dict(),
                        "supported_horizons": horizons,
                        "path": catalog.model_relative_path(ref).as_posix(),
                        "sha256": "b" * 64,
                    }
                )
                members.append(
                    {
                        "model_ref": {**ref.as_dict(), "horizon_days": horizons[0]},
                        "available": True,
                        "prediction": {
                            "probability": 0.6,
                            "applicability": {"status": "within_observed_range"},
                        },
                        "evaluation": {
                            "evidence": "better_than_prevalence",
                            "brier_score": 0.2,
                            "prevalence_brier_score": 0.25,
                            "brier_delta_vs_prevalence": 0.05,
                            "roc_auc": 0.7,
                        },
                        "metadata": {"cutoff_date": "2026-08-18"},
                    }
                )
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-v3",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": artifacts,
        }
        with mock.patch.object(
            comparison, "compare_selection", return_value={"members": members}
        ) as compare_selection:
            result = comparison.compare_operational_reference(
                registry,
                manifest,
                species_id="boletus_edulis",
                area_id="area-a",
                target_date=date(2026, 8, 18),
                issue_date=date(2026, 8, 18),
                season_phase="in_season",
                phenology={},
                models_root=Path("/unused/models"),
                known_sites_path=Path("/unused/sites.json"),
                weather_data_dir=Path("/unused/weather"),
            )

        self.assertEqual(len(result["operational_result_keys"]), 2)
        self.assertEqual(len(result["comparison_detail_result_keys"]), 4)
        self.assertEqual(
            {row["profile_id"] for row in result["operational_profiles"]},
            {"core", "common_idw_plus_physical_state"},
        )
        selected = compare_selection.call_args.args[2]
        self.assertEqual({row["profile_id"] for row in selected}, {"core", "common_idw_plus_physical_state"})
    def test_v2_week_prewarm_materializes_once_per_area_and_slices_cutoffs(self) -> None:
        cache = {}
        base = {"daily_dates": list(range(96)), "scalar": "kept"}
        with mock.patch.object(
            comparison,
            "prepare_area_weather",
            return_value=("area-context", {0: base}, {("aemet", "x"): object()}),
        ) as prepare:
            comparison.prewarm_v2_week_weather(
                area_ids=["area-a"],
                target_issue_dates=[
                    (date(2026, 8, 18), date(2026, 8, 18)),
                    (date(2026, 8, 19), date(2026, 8, 18)),
                ],
                known_sites_path=Path("/unused/sites.json"),
                weather_data_dir=Path("/unused/weather"),
                excluded_station_keys=frozenset(),
                prepared_weather_cache=cache,
            )

        prepare.assert_called_once()
        first_key = comparison._prepared_weather_key(
            known_sites_path=Path("/unused/sites.json"),
            weather_data_dir=Path("/unused/weather"),
            area_id="area-a",
            target_date=date(2026, 8, 18),
            horizons=(1, 7),
            lookback_days=90,
            include_physical_state=False,
            excluded_station_keys=frozenset(),
        )
        second_key = comparison._prepared_weather_key(
            known_sites_path=Path("/unused/sites.json"),
            weather_data_dir=Path("/unused/weather"),
            area_id="area-a",
            target_date=date(2026, 8, 19),
            horizons=(2, 7),
            lookback_days=90,
            include_physical_state=False,
            excluded_station_keys=frozenset(),
        )
        first = cache[first_key][1]
        second = cache[second_key][1]
        self.assertEqual(first[7]["daily_dates"], list(range(90)))
        self.assertEqual(first[1]["daily_dates"], list(range(6, 96)))
        self.assertEqual(second[7]["daily_dates"], list(range(1, 91)))
        self.assertEqual(second[2]["daily_dates"], list(range(6, 96)))
        self.assertEqual(first[7]["scalar"], "kept")

    def test_v2_v3_physical_profile_remains_an_explicit_supported_experiment(self) -> None:
        raw = catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-v2",
            version_id="altitude_v2",
            temporal_contract_id="fixed_gap_7d_altitude_v2",
            profile_id="common_idw",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
            horizon_days=7,
        )
        physical = catalog.ModelRef(
            **{
                **raw.as_dict(),
                "profile_id": "common_idw_plus_physical_state",
            }
        )

        self.assertEqual(comparison._weather_requirements([raw]), (90, False))
        self.assertEqual(
            comparison._weather_requirements([physical]),
            (90, True),
        )

    def test_365_day_runtime_is_limited_to_v5_v6(self) -> None:
        v4 = catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-v4",
            version_id="biology_v4",
            temporal_contract_id="fixed_gap_7d_biology_v4",
            profile_id="climatic_balance",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
            horizon_days=7,
        )
        v5 = catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-v5",
            version_id="biology_v5_raw_weather_discovery",
            temporal_contract_id="fixed_gap_7d_biology_v5_raw365_v2",
            profile_id="raw_primary_plus_physical_state",
            estimator_id="elastic_net_logistic_raw365_v1",
            species_id="boletus_edulis",
            horizon_days=7,
        )

        self.assertEqual(comparison._weather_requirements([v4]), (90, True))
        self.assertEqual(comparison._weather_requirements([v5]), (365, True))

    def test_registry_requirements_drive_v3_core_and_physical_weather(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        profiles = catalog.catalog_entries(registry)
        core = catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
            horizon_days=7,
        )
        physical = catalog.ModelRef(
            **{**core.as_dict(), "profile_id": "common_idw_plus_physical_state"}
        )

        self.assertEqual(
            comparison._weather_requirements([core], catalog_profiles=profiles),
            (90, False),
        )
        self.assertEqual(
            comparison._weather_requirements([physical], catalog_profiles=profiles),
            (365, True),
        )

    def test_selection_reuses_prepared_area_weather_within_one_request(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        model_ref = catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-v5",
            version_id="biology_v5_raw_weather_discovery",
            temporal_contract_id=raw.LAG_CONTRACT_ID,
            profile_id="raw_primary_plus_physical_state",
            estimator_id="elastic_net_logistic_raw365_v1",
            species_id="boletus_edulis",
            horizon_days=3,
        )
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": [
                {
                    "artifact_ref": model_ref.artifact_ref.as_dict(),
                    "supported_horizons": list(range(1, 8)),
                    "path": catalog.model_relative_path(
                        model_ref.artifact_ref
                    ).as_posix(),
                    "sha256": "b" * 64,
                }
            ],
        }
        selection = {
            "version_id": model_ref.version_id,
            "temporal_contract_id": model_ref.temporal_contract_id,
            "profile_id": model_ref.profile_id,
            "estimator_id": model_ref.estimator_id,
            "horizon_days": model_ref.horizon_days,
        }
        prepared_cache = {}
        comparison_cache = {}
        prepared = (object(), {3: {"daily_dates": []}}, {})
        results = []
        with mock.patch.object(
            comparison.catalog,
            "validate_batch_manifest",
            wraps=comparison.catalog.validate_batch_manifest,
        ) as validate_manifest, mock.patch.object(
            comparison, "prepare_area_weather", return_value=prepared
        ) as prepare, mock.patch.object(
            comparison,
            "compare_prepared",
            side_effect=lambda *_args, **_kwargs: {"members": []},
        ):
            for _ in range(2):
                results.append(
                    comparison.compare_selection(
                        registry,
                        manifest,
                        [selection],
                        species_id="boletus_edulis",
                        area_id="area-a",
                        target_date=date(2026, 8, 18),
                        models_root=Path("/unused/models"),
                        known_sites_path=Path("/unused/sites.json"),
                        weather_data_dir=Path("/unused/weather"),
                        prepared_weather_cache=prepared_cache,
                        comparison_cache=comparison_cache,
                    )
                )

        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(validate_manifest.call_count, 1)
        self.assertEqual(
            [row["runtime_metrics"]["weather_cache_status"] for row in results],
            ["miss", "hit"],
        )
        self.assertIn(
            "weather_context", results[0]["runtime_metrics"]["phase_seconds"]
        )
        self.assertIn(
            "prepared_comparison",
            results[0]["runtime_metrics"]["phase_seconds"],
        )

    def test_v2_reference_uses_installed_common_idw_members_only(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        registry["preferred_version_id"] = "altitude_v2"
        artifacts = []
        for contract_id, horizons in (
            (comparison.V2_FIXED_CONTRACT_ID, [7]),
            (comparison.V2_LAG_CONTRACT_ID, list(range(1, 8))),
        ):
            artifact_ref = catalog.ModelArtifactRef(
                batch_id="batch-a",
                generation_id="generation-v2",
                version_id="altitude_v2",
                temporal_contract_id=contract_id,
                profile_id="common_idw",
                estimator_id="logistic_regression_reduced_v1",
                species_id="boletus_edulis",
            )
            artifacts.append(
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": horizons,
                    "path": catalog.model_relative_path(artifact_ref).as_posix(),
                    "sha256": "b" * 64,
                }
            )
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": artifacts,
        }
        runtime_members = []
        for artifact in artifacts:
            ref = artifact["artifact_ref"]
            runtime_members.append(
                {
                    "model_ref": {**ref, "horizon_days": artifact["supported_horizons"][0]},
                    "available": True,
                    "prediction": {"probability": 0.6, "applicability": {}},
                    "evaluation": {
                        "brier_score": 0.2,
                        "prevalence_brier_score": 0.25,
                        "n_test": 8,
                    },
                    "features_used": {"rain_sum_21d": 12.0},
                    "metadata": {"cutoff_date": "2026-08-16"},
                }
            )
        with mock.patch.object(
            comparison,
            "compare_selection",
            return_value={"members": runtime_members},
        ) as compare_selection:
            result = comparison.compare_v2_reference(
                registry,
                manifest,
                species_id="boletus_edulis",
                area_id="area-a",
                target_date=date(2026, 8, 17),
                issue_date=date(2026, 8, 17),
                season_phase="in_season",
                phenology={},
                models_root=Path("/unused"),
                known_sites_path=Path("/unused/sites.json"),
                weather_data_dir=Path("/unused/weather"),
            )

        selections = compare_selection.call_args.args[2]
        self.assertEqual({row["profile_id"] for row in selections}, {"common_idw"})
        self.assertEqual(
            {row["temporal_contract_id"] for row in selections},
            {comparison.V2_FIXED_CONTRACT_ID, comparison.V2_LAG_CONTRACT_ID},
        )
        self.assertNotIn("fixed_gap_7d_v1", result)
        self.assertEqual(
            result[comparison.V2_FIXED_CONTRACT_ID]["spatial_weather_contract"],
            "common_multisource_idw_by_microarea",
        )

    def test_v2_reference_resolves_intermediate_week_horizons(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        registry["preferred_version_id"] = "altitude_v2"
        artifacts = []
        for contract_id, horizons in (
            (comparison.V2_FIXED_CONTRACT_ID, [7]),
            (comparison.V2_LAG_CONTRACT_ID, list(range(1, 8))),
        ):
            artifact_ref = catalog.ModelArtifactRef(
                batch_id="batch-a",
                generation_id="generation-v2",
                version_id="altitude_v2",
                temporal_contract_id=contract_id,
                profile_id="common_idw",
                estimator_id="logistic_regression_reduced_v1",
                species_id="boletus_edulis",
            )
            artifacts.append(
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": horizons,
                    "path": catalog.model_relative_path(artifact_ref).as_posix(),
                    "sha256": "b" * 64,
                }
            )
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": artifacts,
        }

        def available_members(_registry, _manifest, selections, **_kwargs):
            return {
                "members": [
                    {
                        "model_ref": {
                            **next(
                                artifact["artifact_ref"]
                                for artifact in artifacts
                                if artifact["artifact_ref"]["temporal_contract_id"]
                                == selection["temporal_contract_id"]
                            ),
                            "horizon_days": selection["horizon_days"],
                        },
                        "available": True,
                        "prediction": {"probability": 0.6, "applicability": {}},
                        "evaluation": None,
                        "features_used": {},
                        "metadata": {},
                    }
                    for selection in selections
                ]
            }

        issue_date = date(2026, 8, 18)
        with mock.patch.object(
            comparison, "compare_selection", side_effect=available_members
        ) as compare_selection:
            for horizon_days in (4, 5, 6):
                with self.subTest(horizon_days=horizon_days):
                    result = comparison.compare_v2_reference(
                        registry,
                        manifest,
                        species_id="boletus_edulis",
                        area_id="area-a",
                        target_date=issue_date + timedelta(days=horizon_days - 1),
                        issue_date=issue_date,
                        season_phase="in_season",
                        phenology={},
                        models_root=Path("/unused"),
                        known_sites_path=Path("/unused/sites.json"),
                        weather_data_dir=Path("/unused/weather"),
                    )
                    self.assertTrue(
                        result[comparison.V2_LAG_CONTRACT_ID]["available"]
                    )
                    selections = compare_selection.call_args.args[2]
                    self.assertIn(
                        horizon_days,
                        {
                            row["horizon_days"]
                            for row in selections
                            if row["temporal_contract_id"]
                            == comparison.V2_LAG_CONTRACT_ID
                        },
                    )

    def test_compare_reports_members_individually_and_never_ensembles(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        model_ref = catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-v5",
            version_id="biology_v5_raw_weather_discovery",
            temporal_contract_id=raw.LAG_CONTRACT_ID,
            profile_id="raw_primary_plus_physical_state",
            estimator_id="elastic_net_logistic_raw365_v1",
            species_id="boletus_edulis",
            horizon_days=3,
        )
        artifact_ref = model_ref.artifact_ref
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": [
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": list(range(1, 8)),
                    "path": catalog.model_relative_path(artifact_ref).as_posix(),
                    "sha256": "b" * 64,
                }
            ],
        }
        start = date(2024, 1, 1)
        area_series = {
            "daily_dates": [
                (start + timedelta(days=index)).isoformat()
                for index in range(raw.LOOKBACK_DAYS)
            ],
            **{
                key: [1.0] * raw.LOOKBACK_DAYS
                for key in raw.AREA_SERIES_KEYS.values()
            },
        }
        bundle = {
            "evaluation": {"brier_score": 0.2},
            "artifact_ref": artifact_ref.as_dict(),
        }
        prediction = {"probability": 0.61, "ensemble_used": False}
        with mock.patch.object(
            comparison.mushroom_ml_runtime_inference,
            "load_exact_artifact",
            return_value=bundle,
        ), mock.patch.object(
            comparison.mushroom_ml_runtime_inference,
            "predict_bundle",
            return_value=prediction,
        ):
            result = comparison.compare_prepared(
                registry,
                manifest,
                [model_ref],
                models_root=Path("/unused"),
                target_date=date(2024, 12, 31),
                area_id="area-a",
                area_context=None,
                area_series_by_horizon={3: area_series},
                stations={},
            )

        self.assertEqual(len(result["members"]), 1)
        self.assertTrue(result["members"][0]["available"])
        self.assertEqual(result["members"][0]["prediction"]["probability"], 0.61)
        self.assertFalse(result["ensemble_computed"])
        self.assertFalse(result["consensus_computed"])
        self.assertEqual(result["runtime_metrics"]["member_count"], 1)
        self.assertGreaterEqual(result["runtime_metrics"]["backend_seconds"], 0)
        self.assertIn(
            "runtime_features", result["runtime_metrics"]["phase_seconds"]
        )
        self.assertIn("artifact_load", result["runtime_metrics"]["phase_seconds"])
        self.assertIn("model_inference", result["runtime_metrics"]["phase_seconds"])

    def test_missing_horizon_does_not_fall_back_to_another_model(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        model_ref = catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-v5",
            version_id="biology_v5_raw_weather_discovery",
            temporal_contract_id=raw.LAG_CONTRACT_ID,
            profile_id="raw_primary_plus_physical_state",
            estimator_id="elastic_net_logistic_raw365_v1",
            species_id="boletus_edulis",
            horizon_days=3,
        )
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": [
                {
                    "artifact_ref": model_ref.artifact_ref.as_dict(),
                    "supported_horizons": list(range(1, 8)),
                    "path": catalog.model_relative_path(model_ref).as_posix(),
                    "sha256": "b" * 64,
                }
            ],
        }

        result = comparison.compare_prepared(
            registry,
            manifest,
            [model_ref],
            models_root=Path("/unused"),
            target_date=date(2024, 12, 31),
            area_id="area-a",
            area_context=None,
            area_series_by_horizon={},
            stations={},
        )

        self.assertFalse(result["members"][0]["available"])
        self.assertEqual(
            result["members"][0]["reason"], "prepared_weather_horizon_missing"
        )

    def test_selection_resolves_shared_v6_artifact_for_requested_species(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        artifact_ref = catalog.ModelArtifactRef(
            batch_id="batch-a",
            generation_id="generation-v6",
            version_id="biology_v6_smooth_hierarchical",
            temporal_contract_id="lag_event_biology_v6_smooth_hierarchical_v2",
            profile_id="smooth_weather_physical_state",
            estimator_id="smooth_partial_pooling_logistic_v1",
            species_id="all_species",
        )
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": [
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": list(range(1, 8)),
                    "path": catalog.model_relative_path(artifact_ref).as_posix(),
                    "sha256": "b" * 64,
                }
            ],
        }
        resolved = comparison.resolve_selection(
            registry,
            manifest,
            {
                "version_id": "biology_v6_smooth_hierarchical",
                "temporal_contract_id": "lag_event_biology_v6_smooth_hierarchical_v2",
                "profile_id": "smooth_weather_physical_state",
                "estimator_id": "smooth_partial_pooling_logistic_v1",
                "horizon_days": 3,
            },
            species_id="boletus_edulis",
        )

        self.assertEqual(resolved.species_id, "boletus_edulis")
        self.assertEqual(resolved.generation_id, "generation-v6")
