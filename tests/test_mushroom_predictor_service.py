from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import ANY, Mock, patch

from rainmapper_core import mushroom_predictor_service as service_module
from rainmapper_core.mushroom_ml_predictor import PredictionResult
from rainmapper_core.mushroom_predictor_service import (
    PreparedPredictor,
    PredictorContractError,
    PredictorService,
    REQUEST_KIND,
    SCHEMA_VERSION,
    normalize_request,
    validate_response,
)


def prediction(species: str, area: str, day: date, probability: float = 0.7) -> PredictionResult:
    return PredictionResult(
        species_id=species,
        area_id=area,
        target_date=day,
        lr_probability=probability,
        rf_probability=probability,
        ensemble_probability=probability,
        label="favorable",
        weather_station_code="station",
        weather_station_distance_km=1.2,
        weather_coverage_days=90,
        features_used={"rain_7d_mm": 12.0},
    )


TEST_SELECTION = {
    "version_id": "biology_v3",
    "temporal_contract_id": "fixed_gap_7d_biology_v3",
    "profile_id": "core",
    "estimator_id": "logistic_regression",
    "horizon_days": 7,
}


def operational_comparison(verdict: str = "uncertain") -> dict[str, object]:
    return {
        "available": True,
        "operational_comparison": {
            "selection_mode": "multiversion",
            "interpretation": {"verdict": verdict},
        },
    }


class PredictorServiceTests(TestCase):
    def request(self, **changes: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "kind": REQUEST_KIND,
            "view": "query",
            "species_id": "boletus",
            "area_id": "area_one",
            "target_date": "2026-08-09",
            "trained_species_ids": ["boletus"],
        }
        payload.update(changes)
        return payload

    def test_normalize_request_rejects_unknown_view(self) -> None:
        with self.assertRaises(PredictorContractError):
            normalize_request(self.request(view="unknown"))

    def test_week_uses_sealed_resolution_index_for_each_area_day(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.predict_many.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9) + timedelta(days=offset))
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            service.multiversion_compare = Mock(
                side_effect=lambda **_kwargs: operational_comparison()
            )
            resolutions = {
                ("boletus", "area_one", day): {
                    "species_id": "boletus",
                    "area_id": "area_one",
                    "prediction_day": day,
                    "selection_status": "abstain" if day == 1 else "winner",
                    "selection_scope": "none" if day == 1 else "area",
                    "candidate": None if day == 1 else dict(TEST_SELECTION),
                }
                for day in range(1, 8)
            }

            response = service.execute(
                self.request(
                    view="week",
                    area_id="",
                    issue_date="2026-08-09",
                    multiversion_selection=[],
                ),
                shared_context={"operational_resolution_index": resolutions},
            )

        comparisons = response["data"]["species"]["boletus"]["model_comparisons"][
            "area_one"
        ]
        self.assertFalse(comparisons["2026-08-09"]["available"])
        self.assertEqual(
            comparisons["2026-08-09"]["reason"],
            "reliability_selection_abstained",
        )
        self.assertEqual(service.multiversion_compare.call_count, 6)
        for call in service.multiversion_compare.call_args_list:
            self.assertEqual(call.kwargs["selections"], [TEST_SELECTION])

    def test_area_week_uses_each_sealed_daily_winner_without_broad_comparison(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.return_value = [
                prediction(
                    "boletus", "area_one", date(2026, 8, 9) + timedelta(days=offset)
                )
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            service.prewarm_multiversion_week = Mock(return_value=7)
            predictor.season_phase.return_value = "in_season"

            def compared(**kwargs: object) -> dict[str, object]:
                selections = list(kwargs["selections"])
                members = []
                for index, reference in enumerate(selections):
                    members.append(
                        {
                            "model_ref": dict(reference),
                            "available": True,
                            "prediction": {
                                "probability": 0.9 - index / 10,
                                "applicability": {
                                    "status": "outside_domain"
                                    if index == 0
                                    else "within_observed_range"
                                },
                            },
                            "evaluation": {
                                "evidence": "better_than_prevalence",
                                "brier_score": 0.1,
                                "prevalence_brier_score": 0.25,
                                "brier_delta_vs_prevalence": 0.15,
                                "roc_auc": 0.8,
                            },
                        }
                    )
                return {
                    "available": True,
                    "members": members,
                    "runtime_metrics": {"versions": {}, "phase_seconds": {}},
                }

            service.multiversion_compare = Mock(side_effect=compared)
            resolutions = {}
            for day in range(1, 8):
                candidate = {**TEST_SELECTION, "estimator_id": f"winner_{day}"}
                resolutions[("boletus", "area_one", day)] = {
                    "species_id": "boletus",
                    "area_id": "area_one",
                    "prediction_day": day,
                    "selection_status": "winner",
                    "selection_scope": "area",
                    "candidate": candidate,
                    "candidate_chain": [
                        {"candidate": candidate},
                        {
                            "candidate": {
                                **candidate,
                                "estimator_id": f"fallback_{day}",
                            }
                        },
                    ],
                }

            response = service.execute(
                self.request(
                    area_id="area_one",
                    issue_date="2026-08-09",
                    multiversion_selection=[],
                ),
                shared_context={"operational_resolution_index": resolutions},
            )

        prewarm = service.prewarm_multiversion_week.call_args.kwargs
        self.assertEqual(prewarm["selections"], [])
        self.assertIs(prewarm["operational_resolution_index"], resolutions)
        self.assertEqual(service.multiversion_compare.call_count, 7)
        self.assertEqual(
            [
                [row["estimator_id"] for row in call.kwargs["selections"]]
                for call in service.multiversion_compare.call_args_list
            ],
            [
                [f"winner_{day}", f"fallback_{day}"]
                for day in range(1, 8)
            ],
        )
        comparisons = response["data"]["species"]["boletus"][
            "multiversion_comparisons"
        ]
        self.assertTrue(comparisons)
        for comparison_payload in comparisons.values():
            self.assertEqual(len(comparison_payload["members"]), 1)
            self.assertTrue(
                comparison_payload["members"][0]["model_ref"]["estimator_id"].startswith(
                    "fallback_"
                )
            )

    def test_query_response_can_be_rendered_through_prepared_adapter(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9 + offset))
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            service.multiversion_compare = Mock(return_value=operational_comparison())
            comparator = Mock()
            comparator.compare.return_value = {"interpretation": {"verdict": "uncertain"}}
            service.comparator = Mock(return_value=comparator)
            progress: list[int] = []

            response = service.execute(
                self.request(), progress=lambda percent, _phase, _message: progress.append(percent)
            )
            validate_response(response)
            prepared = PreparedPredictor("boletus", response)

            self.assertEqual(prepared.areas_with_species_observations(), ["area_one"])
            self.assertEqual(prepared.predict("area_one", date(2026, 8, 9)).ensemble_probability, 0.7)
            self.assertEqual(len(prepared.week_window("area_one", date(2026, 8, 9))), 7)
            self.assertEqual(progress[-1], 100)

    def test_query_drops_area_that_does_not_belong_to_selected_species(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.rank_areas.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9))
            ]
            service.predictor = Mock(return_value=predictor)
            service.multiversion_compare = Mock(return_value=operational_comparison())
            comparator = Mock()
            comparator.compare.return_value = {"interpretation": {"verdict": "uncertain"}}
            service.comparator = Mock(return_value=comparator)

            response = service.execute(
                self.request(
                    area_id="area_from_previous_species",
                    multiversion_selection=[TEST_SELECTION],
                )
            )

        self.assertEqual(response["request"]["area_id"], "")
        self.assertEqual(
            response["data"]["species"]["boletus"]["areas"], ["area_one"]
        )
        predictor.week_window.assert_not_called()
        predictor.rank_areas.assert_called_once_with(date(2026, 8, 9), only_observed=True)

    def test_identical_request_reuses_bounded_response_cache(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9 + offset))
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            comparator = Mock()
            comparator.compare.return_value = {"interpretation": {"verdict": "uncertain"}}
            service.comparator = Mock(return_value=comparator)

            first = service.execute(self.request())
            second = service.execute(self.request())

        self.assertEqual(first["metrics"]["response_cache_status"], "miss")
        self.assertEqual(second["metrics"]["response_cache_status"], "hit")
        self.assertIn("prediction_data", first["metrics"]["phase_seconds"])
        self.assertIn(
            "multiversion_model_comparison", first["metrics"]["phase_seconds"]
        )
        self.assertEqual(
            first["metrics"]["phase_call_counts"]["multiversion_model_comparison"],
            7,
        )
        self.assertIn("response_cache_lookup", second["metrics"]["phase_seconds"])
        self.assertEqual(second["metrics"]["detailed_phase_seconds"], {})
        predictor.week_window.assert_called_once()

    def test_recommender_cache_ignores_irrelevant_selected_species(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.season_phase.return_value = "in_season"
            predictor.areas_with_species_observations.return_value = ["area_one"]
            service.predictor = Mock(return_value=predictor)
            service.multiversion_compare = Mock(return_value=operational_comparison())
            request = self.request(
                view="recommender",
                area_id="",
                trained_species_ids=["amanita", "boletus"],
                species_id="amanita",
                multiversion_selection=[TEST_SELECTION],
            )

            first = service.execute(request)
            second = service.execute({**request, "species_id": "boletus"})

        self.assertEqual(first["metrics"]["response_cache_status"], "miss")
        self.assertEqual(second["metrics"]["response_cache_status"], "hit")
        self.assertEqual(second["request"]["species_id"], "boletus")
        predictor.rank_areas.assert_not_called()
        self.assertEqual(service.multiversion_compare.call_count, 2)

    def test_installed_runtime_batches_loads_only_requested_version_once(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = PredictorService(
                models_dir=root,
                weather_data_dir=root,
                features_artifact_path=root / "features.json",
                known_sites_path=root / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            manifest_path = root / "manifest.json"
            manifest_path.write_text("{}", encoding="utf-8")
            registry = {
                "versions": [
                    {
                        "version_id": "altitude_v2",
                        "installed_generation_id": "generation-v2",
                    },
                    {
                        "version_id": "biology_v4",
                        "installed_generation_id": "generation-v4",
                    },
                ]
            }
            validated = {"batch_id": "batch-v4", "artifacts": []}
            comparison_cache: dict[str, object] = {}
            with (
                patch.object(
                    service_module.mushroom_ml_version_registry,
                    "installed_manifest_path",
                    return_value=manifest_path,
                ) as installed_path,
                patch.object(
                    service_module.mushroom_ml_model_catalog,
                    "validate_batch_manifest",
                    return_value=validated,
                ) as validate_manifest,
            ):
                first = service._installed_runtime_batches(
                    registry,
                    version_ids={"biology_v4"},
                    comparison_cache=comparison_cache,
                )
                second = service._installed_runtime_batches(
                    registry,
                    version_ids={"biology_v4"},
                    comparison_cache=comparison_cache,
                )

        self.assertEqual(first, {"biology_v4": validated})
        self.assertEqual(second, first)
        self.assertEqual(installed_path.call_count, 1)
        self.assertEqual(installed_path.call_args.args[1], "biology_v4")
        validate_manifest.assert_called_once()

    def test_non_query_views_request_catalog_without_installed_artifacts(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = []
            predictor.predict_many.return_value = []
            service.predictor = Mock(return_value=predictor)
            service.model_catalog = Mock(
                return_value={"available": True, "preferred_version_id": "biology_v4"}
            )

            service.execute(self.request(view="week", area_id=""))

        service.model_catalog.assert_called_once_with(
            include_installed_artifacts=False,
            comparison_cache=ANY,
        )

    def test_query_attaches_multiversion_operational_comparison(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9 + offset))
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            service.multiversion_compare = Mock(return_value=operational_comparison())

            response = service.execute(
                self.request(
                    compare_models=True,
                    issue_date="2026-08-09",
                    multiversion_selection=[TEST_SELECTION],
                )
            )

        comparison = response["data"]["species"]["boletus"]["model_comparisons"]
        self.assertEqual(
            comparison["area_one"]["2026-08-09"]["selection_mode"],
            "multiversion",
        )
        self.assertEqual(service.multiversion_compare.call_count, 7)

    def test_query_area_anchors_current_week_to_explicit_issue_date(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.side_effect = lambda area_id, week_start: [
                prediction("boletus", area_id, week_start + timedelta(days=offset))
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            service.v2_reference_compare = Mock(
                return_value={"interpretation": {"verdict": "uncertain"}}
            )

            response = service.execute(
                self.request(
                    target_date="2026-08-31",
                    issue_date="2026-08-31",
                )
            )

        predictor.week_window.assert_called_once_with(
            "area_one", date(2026, 8, 31)
        )
        predictions = response["data"]["species"]["boletus"]["predictions"][
            "area_one"
        ]
        self.assertEqual(min(predictions), "2026-08-31")
        self.assertNotIn("2026-08-30", predictions)
        self.assertTrue(
            all(
                call.kwargs["issue_date"] == date(2026, 8, 31)
                for call in service.v2_reference_compare.call_args_list
            )
        )

    def test_query_prepares_multiversion_comparison_for_every_rendered_day(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.week_window.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9 + offset))
                for offset in range(7)
            ]
            service.predictor = Mock(return_value=predictor)
            service.v2_reference_compare = Mock(
                return_value={"interpretation": {"verdict": "uncertain"}}
            )
            service.multiversion_compare = Mock(
                side_effect=lambda **kwargs: {
                    "available": True,
                    "target_date": kwargs["target_date"].isoformat(),
                    "operational_comparison": {
                        "selection_mode": "multiversion",
                        "interpretation": {"verdict": "uncertain"},
                    },
                }
            )
            selection = {
                "version_id": "biology_v3",
                "temporal_contract_id": "fixed_gap_7d_biology_v3",
                "profile_id": "core",
                "estimator_id": "random_forest_restricted_v1",
                "horizon_days": 7,
            }

            response = service.execute(
                self.request(
                    compare_models=True,
                    issue_date="2026-08-09",
                    multiversion_selection=[selection],
                )
            )

        species_data = response["data"]["species"]["boletus"]
        by_date = species_data["multiversion_comparisons"]
        self.assertEqual(
            set(by_date),
            {date(2026, 8, 9 + offset).isoformat() for offset in range(7)},
        )
        self.assertEqual(
            species_data["multiversion_comparison"], by_date["2026-08-09"]
        )
        self.assertEqual(service.multiversion_compare.call_count, 7)

    def test_all_areas_query_uses_the_selected_operational_versions(self) -> None:
        selection = {
            "version_id": "biology_v6_windowed",
            "temporal_contract_id": "fixed_gap_7d_biology_v6_windowed",
            "profile_id": "windowed_smooth_weather",
            "estimator_id": "logistic_regression",
            "horizon_days": 7,
        }
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.rank_areas.return_value = [
                prediction("boletus", "area_one", date(2026, 8, 9))
            ]
            service.predictor = Mock(return_value=predictor)
            service.v2_reference_compare = Mock()
            service.multiversion_compare = Mock(
                return_value={"selection_mode": "multiversion"}
            )

            response = service.execute(
                self.request(
                    view="query",
                    area_id="",
                    target_date="2026-08-09",
                    issue_date="2026-08-09",
                    multiversion_selection=[selection],
                )
            )

        comparison = response["data"]["species"]["boletus"][
            "model_comparisons"
        ]["area_one"]["2026-08-09"]
        self.assertEqual(comparison, {"selection_mode": "multiversion"})
        service.multiversion_compare.assert_called_once()
        service.v2_reference_compare.assert_not_called()

    def test_week_view_batches_all_area_days(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = [
                "area_one",
                "area_two",
            ]
            predictor.predict_many.side_effect = lambda requests: [
                prediction("boletus", area_id, target_date)
                for area_id, target_date in requests
            ]
            service.predictor = Mock(return_value=predictor)
            service.multiversion_compare = Mock(return_value=operational_comparison())

            response = service.execute(
                self.request(
                    view="week",
                    area_id="",
                    target_date="2026-09-02",
                    issue_date="2026-09-02",
                    multiversion_selection=[TEST_SELECTION],
                )
            )

        validate_response(response)
        predictor.predict_many.assert_called_once()
        self.assertEqual(len(predictor.predict_many.call_args.args[0]), 14)
        requested_dates = {
            target_date
            for _area_id, target_date in predictor.predict_many.call_args.args[0]
        }
        self.assertEqual(
            requested_dates,
            {date(2026, 9, 2) + timedelta(days=offset) for offset in range(7)},
        )
        self.assertEqual(service.multiversion_compare.call_count, 14)

    def test_week_view_uses_the_selected_operational_versions(self) -> None:
        selection = {
            "version_id": "biology_v6_windowed",
            "temporal_contract_id": "fixed_gap_7d_biology_v6_windowed",
            "profile_id": "windowed_smooth_weather",
            "estimator_id": "logistic_regression",
            "horizon_days": 7,
        }
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.predict_many.side_effect = lambda requests: [
                prediction("boletus", area_id, target_date)
                for area_id, target_date in requests
            ]
            service.predictor = Mock(return_value=predictor)
            service.v2_reference_compare = Mock()
            service.multiversion_compare = Mock(
                return_value={"selection_mode": "multiversion"}
            )

            response = service.execute(
                self.request(
                    view="week",
                    area_id="",
                    issue_date="2026-09-02",
                    multiversion_selection=[selection],
                )
            )

        comparisons = response["data"]["species"]["boletus"]["model_comparisons"]
        self.assertEqual(len(comparisons["area_one"]), 7)
        self.assertEqual(service.multiversion_compare.call_count, 7)
        service.v2_reference_compare.assert_not_called()

    def test_recommender_skips_species_outside_configured_season(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.season_phase.return_value = "out_of_season"
            predictor.areas_with_species_observations.return_value = ["area_one"]
            service.predictor = Mock(return_value=predictor)

            response = service.execute(
                self.request(
                    view="recommender",
                    area_id="",
                    target_date="2026-08-10",
                )
            )

        species_data = response["data"]["species"]["boletus"]
        self.assertEqual(species_data["season_phase"], "out_of_season")
        self.assertEqual(species_data["areas"], ["area_one"])
        self.assertEqual(species_data["rankings"]["2026-08-10"], [])
        predictor.rank_areas.assert_not_called()

    def test_recommender_compares_every_observed_area_without_base_ranking(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.season_phase.return_value = "in_season"
            predictor.areas_with_species_observations.return_value = [
                "area_one",
                "area_two",
            ]
            service.predictor = Mock(return_value=predictor)
            service.multiversion_compare = Mock(
                return_value=operational_comparison("favorable")
            )

            response = service.execute(
                self.request(
                    view="recommender",
                    area_id="",
                    target_date="2026-08-10",
                    multiversion_selection=[TEST_SELECTION],
                )
            )
            prepared = PreparedPredictor("boletus", response)

        self.assertEqual(
            response["data"]["species"]["boletus"]["areas"],
            ["area_one", "area_two"],
        )
        self.assertEqual(
            prepared.areas_with_species_observations(), ["area_one", "area_two"]
        )
        self.assertEqual(
            set(response["data"]["species"]["boletus"]["model_comparisons"]),
            {"area_one", "area_two"},
        )
        predictor.rank_areas.assert_not_called()
        self.assertEqual(service.multiversion_compare.call_count, 2)

    def test_recommender_uses_the_selected_operational_versions(self) -> None:
        selection = {
            "version_id": "biology_v3",
            "temporal_contract_id": "fixed_gap_7d_biology_v3",
            "profile_id": "core",
            "estimator_id": "logistic_regression",
            "horizon_days": 7,
        }
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.season_phase.return_value = "in_season"
            predictor.areas_with_species_observations.return_value = [
                "area_one",
                "area_two",
            ]
            service.predictor = Mock(return_value=predictor)
            service.v2_reference_compare = Mock()
            service.multiversion_compare = Mock(
                return_value={"selection_mode": "multiversion"}
            )

            response = service.execute(
                self.request(
                    view="recommender",
                    area_id="",
                    target_date="2026-08-10",
                    multiversion_selection=[selection],
                )
            )

        comparisons = response["data"]["species"]["boletus"]["model_comparisons"]
        self.assertEqual(set(comparisons), {"area_one", "area_two"})
        self.assertEqual(service.multiversion_compare.call_count, 2)
        service.v2_reference_compare.assert_not_called()

    def test_history_preserves_multiversion_operational_comparison_in_prepared_adapter(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.observed_episodes.return_value = [
                {
                    "area_id": "area_one",
                    "observed_at": "2026-08-09",
                    "actual": "favorable",
                }
            ]
            predictor.areas_with_species_observations.return_value = ["area_one"]
            service.predictor = Mock(return_value=predictor)
            selected = {
                "selection_mode": "multiversion",
                "selected_winners": [
                    {
                        "model_ref": {
                            "version_id": "biology_v4",
                            "estimator_id": "random_forest_restricted_v1",
                        }
                    }
                ],
                "interpretation": {"verdict": "favorable"},
            }
            service.multiversion_compare = Mock(return_value=selected)

            response = service.execute(
                self.request(
                    view="history",
                    area_id="",
                    multiversion_selection=[TEST_SELECTION],
                )
            )
            prepared = PreparedPredictor("boletus", response)

        self.assertEqual(
            prepared.model_comparison("area_one", date(2026, 8, 9)), selected
        )
        service.multiversion_compare.assert_called_once()

    def test_history_uses_the_selected_operational_version(self) -> None:
        selection = {
            "version_id": "biology_v6_windowed",
            "temporal_contract_id": "fixed_gap_7d_biology_v6_windowed",
            "profile_id": "windowed_smooth_weather",
            "estimator_id": "logistic_regression",
            "horizon_days": 7,
        }
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.observed_episodes.return_value = [
                {
                    "area_id": "area_one",
                    "observed_at": "2026-08-09",
                    "actual": "favorable",
                }
            ]
            predictor.areas_with_species_observations.return_value = ["area_one"]
            service.predictor = Mock(return_value=predictor)
            selected = {
                "selection_mode": "multiversion",
                "interpretation": {"verdict": "favorable"},
            }
            service.multiversion_compare = Mock(return_value=selected)
            service.v2_reference_compare = Mock()

            response = service.execute(
                self.request(
                    view="history",
                    area_id="",
                    multiversion_selection=[selection],
                )
            )

        comparison = response["data"]["species"]["boletus"][
            "model_comparisons"
        ]["area_one"]["2026-08-09"]
        self.assertEqual(comparison, selected)
        service.multiversion_compare.assert_called_once()
        service.v2_reference_compare.assert_not_called()

    def test_shared_context_keeps_multiversion_results_consistent_across_views(self) -> None:
        with TemporaryDirectory() as temporary:
            service = PredictorService(
                models_dir=Path(temporary),
                weather_data_dir=Path(temporary),
                features_artifact_path=Path(temporary) / "features.json",
                known_sites_path=Path(temporary) / "sites.json",
                runtime_fingerprint="sha256:test",
            )
            predictor = Mock()
            predictor.season_phase.return_value = "in_season"
            predictor.areas_with_species_observations.return_value = ["area_one"]
            predictor.observed_episodes.return_value = [
                {"area_id": "area_one", "observed_at": "2026-08-09"}
            ]
            service.predictor = Mock(return_value=predictor)
            service.multiversion_compare = Mock(
                return_value=operational_comparison("favorable")[
                    "operational_comparison"
                ]
            )
            shared_context: dict[str, object] = {}

            recommender = service.execute(
                self.request(
                    view="recommender",
                    area_id="",
                    target_date="2026-08-09",
                    multiversion_selection=[TEST_SELECTION],
                ),
                shared_context=shared_context,
            )
            history = service.execute(
                self.request(
                    view="history",
                    area_id="",
                    multiversion_selection=[TEST_SELECTION],
                ),
                shared_context=shared_context,
            )

        self.assertEqual(service.multiversion_compare.call_count, 2)
        self.assertEqual(
            recommender["data"]["species"]["boletus"]["model_comparisons"]
            ["area_one"]["2026-08-09"],
            history["data"]["species"]["boletus"]["model_comparisons"]
            ["area_one"]["2026-08-09"],
        )
