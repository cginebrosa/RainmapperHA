from pathlib import Path
from unittest import TestCase

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / "mushroom-data"
    / "mushroom_ml_version_registry.json"
)


class MushroomMLModelCatalogTests(TestCase):
    def setUp(self) -> None:
        self.registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)

    def ref(self, **changes):
        values = {
            "batch_id": "batch-a",
            "generation_id": "generation-a",
            "version_id": "biology_v5_raw_weather_discovery",
            "temporal_contract_id": "lag_event_biology_v5_raw365_v2",
            "profile_id": "raw_primary_plus_physical_state",
            "estimator_id": "elastic_net_logistic_raw365_v1",
            "species_id": "lactarius_deliciosus",
            "horizon_days": 3,
        }
        values.update(changes)
        return catalog.ModelRef.from_mapping(values)

    def test_catalog_exposes_real_profiles_for_v2_through_v6(self) -> None:
        entries = catalog.catalog_entries(self.registry)
        self.assertEqual(
            {row["version_id"] for row in entries},
            {
                "altitude_v2",
                "biology_v3",
                "biology_v4",
                "biology_v5_raw_weather_discovery",
                "biology_v6_smooth_hierarchical",
            },
        )
        self.assertTrue(all(row["catalog_visible"] for row in entries))
        self.assertEqual(
            {
                row["version_id"]
                for row in entries
                if row["operational_eligible"]
            },
            {"altitude_v2"},
        )

    def test_fixed_and_lag_horizons_are_not_confused(self) -> None:
        catalog.validate_model_ref(self.registry, self.ref())
        for horizon_days in range(1, 8):
            catalog.validate_model_ref(
                self.registry, self.ref(horizon_days=horizon_days)
            )
        with self.assertRaisesRegex(ValueError, "horizon"):
            catalog.validate_model_ref(self.registry, self.ref(horizon_days=8))
        with self.assertRaisesRegex(ValueError, "horizon"):
            catalog.validate_model_ref(
                self.registry,
                self.ref(
                    temporal_contract_id="fixed_gap_7d_biology_v5_raw365_v2",
                    horizon_days=3,
                ),
            )

    def test_estimator_must_belong_to_exact_profile(self) -> None:
        with self.assertRaisesRegex(ValueError, "estimator"):
            catalog.validate_model_ref(
                self.registry,
                self.ref(estimator_id="random_forest_restricted_v1"),
            )

    def test_manifest_resolves_exact_model_without_v2_fallback(self) -> None:
        model_ref = self.ref()
        path = catalog.model_relative_path(model_ref)
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": [
                {
                    "artifact_ref": model_ref.artifact_ref.as_dict(),
                    "supported_horizons": list(range(1, 8)),
                    "path": path.as_posix(),
                    "sha256": "b" * 64,
                }
            ],
        }
        self.assertEqual(
            catalog.resolve_artifact(
                self.registry, manifest, model_ref, root=Path("/models")
            ),
            Path("/models") / path,
        )
        with self.assertRaisesRegex(FileNotFoundError, "not present"):
            catalog.resolve_artifact(
                self.registry,
                manifest,
                self.ref(species_id="boletus_edulis"),
                root=Path("/models"),
            )

    def test_manifest_rejects_path_that_does_not_match_identity(self) -> None:
        model_ref = self.ref()
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": [
                {
                    "artifact_ref": model_ref.artifact_ref.as_dict(),
                    "supported_horizons": list(range(1, 8)),
                    "path": "models/v2.joblib",
                    "sha256": "b" * 64,
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "path"):
            catalog.validate_batch_manifest(self.registry, manifest)

    def test_ui_selection_token_round_trips_without_generation_identity(self) -> None:
        selection = {
            "version_id": "biology_v4",
            "temporal_contract_id": "lag_event_biology_v4",
            "profile_id": "climatic_balance",
            "estimator_id": "random_forest_restricted_v1",
            "horizon_days": 3,
        }
        token = catalog.selection_token(selection)
        parsed = catalog.parse_selection_token(token)
        self.assertEqual(parsed["version_id"], "biology_v4")
        self.assertEqual(parsed["horizon_days"], 3)
        self.assertNotIn("generation_id", parsed)
