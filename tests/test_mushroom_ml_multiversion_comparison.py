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
    def test_compare_reports_members_individually_and_never_ensembles(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        model_ref = catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-v5",
            version_id="biology_v5_raw_weather_discovery",
            temporal_contract_id=raw.LAG_CONTRACT_ID,
            profile_id="raw_primary_no_calendar",
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
            profile_id="raw_primary_no_calendar",
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
            temporal_contract_id="lag_event_biology_v6_smooth_hierarchical_v1",
            profile_id="smooth_raw",
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
                "temporal_contract_id": "lag_event_biology_v6_smooth_hierarchical_v1",
                "profile_id": "smooth_raw",
                "estimator_id": "smooth_partial_pooling_logistic_v1",
                "horizon_days": 3,
            },
            species_id="boletus_edulis",
        )

        self.assertEqual(resolved.species_id, "boletus_edulis")
        self.assertEqual(resolved.generation_id, "generation-v6")
