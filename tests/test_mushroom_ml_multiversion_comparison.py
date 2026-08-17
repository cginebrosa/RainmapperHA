from datetime import date, timedelta
from pathlib import Path
from unittest import TestCase
from unittest import mock

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLMultiversionComparisonTests(TestCase):
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
                    "supported_horizons": [1, 2, 3, 7],
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
        with mock.patch.object(
            comparison.catalog,
            "validate_batch_manifest",
            wraps=comparison.catalog.validate_batch_manifest,
        ) as validate_manifest, mock.patch.object(
            comparison, "prepare_area_weather", return_value=prepared
        ) as prepare, mock.patch.object(
            comparison, "compare_prepared", return_value={"members": []}
        ):
            for _ in range(2):
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

        self.assertEqual(prepare.call_count, 1)
        self.assertEqual(validate_manifest.call_count, 1)

    def test_v2_reference_uses_installed_common_idw_members_only(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        artifacts = []
        for contract_id, horizons in (
            (comparison.V2_FIXED_CONTRACT_ID, [7]),
            (comparison.V2_LAG_CONTRACT_ID, [1, 2, 3, 7]),
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
                    "supported_horizons": [1, 2, 3, 7],
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
                    "supported_horizons": [1, 2, 3, 7],
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
                    "supported_horizons": [1, 2, 3, 7],
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
