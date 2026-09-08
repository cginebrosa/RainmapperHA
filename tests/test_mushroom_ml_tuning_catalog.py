from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest import mock

import joblib

from rainmapper_core import mushroom_ml_model_catalog as model_catalog
from rainmapper_core import mushroom_ml_tuning_catalog as tuning_catalog
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_ml_multiversion_plan


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLTuningCatalogTests(TestCase):
    def _fixture(self, root: Path):
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        artifact_ref = model_catalog.ModelArtifactRef(
            batch_id="batch-source",
            generation_id="generation-v5",
            version_id="biology_v5_windowed_raw_weather",
            temporal_contract_id="fixed_gap_7d_biology_v5_raw365_v2",
            profile_id="raw_window_30d_plus_physical_state",
            estimator_id="elastic_net_logistic_raw365_v1",
            species_id="boletus_edulis",
        )
        relative = model_catalog.model_relative_path(artifact_ref)
        path = root / Path(*relative.parts[2:])
        path.parent.mkdir(parents=True)
        snapshot_id = "sha256:" + "a" * 64
        joblib.dump(
            {
                "artifact_ref": artifact_ref.as_dict(),
                "snapshot_id": snapshot_id,
                "fit_config": {
                    "C": 0.1,
                    "class_weight": None,
                    "inner_selection_available": True,
                    "l1_ratio": 0.9,
                },
            },
            path,
        )
        digest = tuning_catalog._sha256(path)
        manifest = {
            "schema_version": model_catalog.SCHEMA_VERSION,
            "kind": model_catalog.BATCH_MANIFEST_KIND,
            "batch_id": "batch-source",
            "snapshot_id": snapshot_id,
            "artifacts": [
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": [7],
                    "path": relative.as_posix(),
                    "sha256": digest,
                }
            ],
        }
        plan = {"fits": [{"artifact_ref": artifact_ref.as_dict()}]}
        return registry, artifact_ref, manifest, plan

    def test_build_is_deterministic_complete_and_lookupable(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "batches" / "batch-source"
            registry, artifact_ref, manifest, plan = self._fixture(root)

            first = tuning_catalog.build_from_batch(
                registry, manifest, batch_root=root, training_plan=plan
            )
            second = tuning_catalog.build_from_batch(
                registry, manifest, batch_root=root, training_plan=plan
            )

        self.assertEqual(first, second)
        self.assertEqual(
            tuning_catalog.lookup(first, artifact_ref.as_dict())["fit_config"]["C"],
            0.1,
        )
        self.assertEqual(first["source_batch_id"], "batch-source")
        self.assertEqual(len(first["decisions"]), 1)

    def test_missing_plan_decision_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "batches" / "batch-source"
            registry, _artifact_ref, manifest, _plan = self._fixture(root)
            catalog = tuning_catalog.build_from_batch(
                registry, manifest, batch_root=root
            )
            missing = {
                "fits": [
                    {
                        "artifact_ref": {
                            **catalog["decisions"][0]["scope"],
                            "species_id": "amanita_caesarea",
                        }
                    }
                ]
            }

            with self.assertRaisesRegex(ValueError, "1 missing, 1 unexpected"):
                tuning_catalog.validate_catalog(
                    registry, catalog, training_plan=missing
                )

    def test_wholly_new_species_gets_a_sealed_v5_bootstrap(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        existing_species = "boletus_edulis"
        old_plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id="old-plan",
            snapshot_id="sha256:" + "b" * 64,
            generation_ids={
                "biology_v5_windowed_raw_weather": "old-v5-windowed"
            },
            species_ids=[existing_species],
            version_ids=["biology_v5_windowed_raw_weather"],
            profile_keys=[
                "biology_v5_windowed_raw_weather/raw_window_30d_plus_physical_state"
            ],
        )
        decisions = []
        for fit in old_plan["fits"]:
            scope = tuning_catalog.decision_scope(fit["artifact_ref"])
            decisions.append(
                {
                    "scope": scope,
                    "fit_config": tuning_catalog._bootstrap_fit_config(scope),
                    "source_artifact_sha256": "a" * 64,
                }
            )
        catalog = tuning_catalog.build_from_decisions(
            registry,
            source_batch_id="batch-source",
            source_snapshot_id="sha256:" + "b" * 64,
            decisions=decisions,
            training_plan=old_plan,
        )
        training_plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id="operational_plan",
            snapshot_id="sha256:" + "c" * 64,
            generation_ids={
                "biology_v5_windowed_raw_weather": "plan-v5-windowed"
            },
            species_ids=[existing_species, "cantharellus_cibarius_sl"],
            version_ids=["biology_v5_windowed_raw_weather"],
            profile_keys=[
                "biology_v5_windowed_raw_weather/raw_window_30d_plus_physical_state"
            ],
        )

        extended = tuning_catalog.extend_for_new_species(
            registry, catalog, training_plan=training_plan
        )

        added = [
            row
            for row in extended["decisions"]
            if row["scope"]["species_id"] == "cantharellus_cibarius_sl"
        ]
        self.assertEqual(len(added), 4)
        self.assertTrue(
            all(row["bootstrap"]["mode"] == "train_only_select" for row in added)
        )
        self.assertTrue(all("source_artifact_sha256" not in row for row in added))
        self.assertTrue(
            all(
                row["fit_config"]["inner_selection_available"] is False
                for row in added
            )
        )

    def test_partial_gap_for_existing_species_still_fails_closed(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "batches" / "batch-source"
            registry, artifact_ref, manifest, _plan = self._fixture(root)
            catalog = tuning_catalog.build_from_batch(
                registry, manifest, batch_root=root
            )
        training_plan = {
            "fits": [
                {"artifact_ref": artifact_ref.as_dict()},
                {
                    "artifact_ref": {
                        **artifact_ref.as_dict(),
                        "estimator_id": "sparse_group_logistic_raw365_v1",
                    }
                },
            ]
        }

        with self.assertRaisesRegex(ValueError, "partial or shared-scope"):
            tuning_catalog.extend_for_new_species(
                registry, catalog, training_plan=training_plan
            )

    def test_artifact_tampering_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "batches" / "batch-source"
            registry, _artifact_ref, manifest, plan = self._fixture(root)
            path = next(root.rglob("*.joblib"))
            path.write_bytes(path.read_bytes() + b"tampered")

            with self.assertRaisesRegex(ValueError, "does not match its manifest"):
                tuning_catalog.build_from_batch(
                    registry, manifest, batch_root=root, training_plan=plan
                )

    def test_contract_revision_change_fails_closed(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "batches" / "batch-source"
            registry, _artifact_ref, manifest, plan = self._fixture(root)
            catalog = tuning_catalog.build_from_batch(
                registry, manifest, batch_root=root, training_plan=plan
            )

            with mock.patch.object(
                tuning_catalog,
                "IMPLEMENTATION_REVISION",
                "incompatible-revision",
            ), self.assertRaisesRegex(ValueError, "incompatible"):
                tuning_catalog.validate_catalog(registry, catalog)

    def test_historical_knn_decision_is_rekeyed_to_the_active_successor(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        legacy_scope = {
            "version_id": "altitude_v2",
            "temporal_contract_id": "fixed_gap_7d_altitude_v2",
            "profile_id": "common_idw",
            "estimator_id": "knn_distance_v1",
            "species_id": "boletus_edulis",
        }

        migrated = tuning_catalog.build_from_decisions(
            registry,
            source_batch_id="historical-batch",
            source_snapshot_id="sha256:" + "a" * 64,
            decisions=[
                {
                    "scope": legacy_scope,
                    "fit_config": {},
                    "source_artifact_sha256": "b" * 64,
                }
            ],
        )

        self.assertEqual(
            migrated["decisions"][0]["scope"]["estimator_id"],
            "knn_distance_beta_smoothed_v2",
        )
        self.assertNotIn("knn_distance_v1", migrated["decisions"][0]["key"])

    def test_catalog_round_trips_as_json(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "batches" / "batch-source"
            registry, _artifact_ref, manifest, plan = self._fixture(root)
            catalog = tuning_catalog.build_from_batch(
                registry, manifest, batch_root=root, training_plan=plan
            )

        encoded = json.dumps(catalog, ensure_ascii=False, sort_keys=True)
        self.assertEqual(
            tuning_catalog.validate_catalog(registry, json.loads(encoded)),
            catalog,
        )

    def test_estimator_config_shape_fails_closed(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "batches" / "batch-source"
            registry, _artifact_ref, manifest, plan = self._fixture(root)
            catalog = tuning_catalog.build_from_batch(
                registry, manifest, batch_root=root, training_plan=plan
            )
            catalog["decisions"][0]["fit_config"]["unexpected"] = 1

            with self.assertRaisesRegex(ValueError, "fit_config keys"):
                tuning_catalog.validate_catalog(registry, catalog)

    def test_temporal_contract_is_resolved_by_declared_family(self) -> None:
        payload = {
            "decisions": [
                {
                    "scope": {
                        "version_id": "biology_v6_windowed_smooth_hierarchical",
                        "profile_id": "smooth_window_30d_plus_physical_state",
                        "temporal_contract_id": "fixed_gap_7d_biology_v6_smooth_hierarchical_v2",
                    }
                },
                {
                    "scope": {
                        "version_id": "biology_v6_windowed_smooth_hierarchical",
                        "profile_id": "smooth_window_30d_plus_physical_state",
                        "temporal_contract_id": "lag_event_biology_v6_smooth_hierarchical_v2",
                    }
                },
            ]
        }

        self.assertEqual(
            "fixed_gap_7d_biology_v6_smooth_hierarchical_v2",
            tuning_catalog.resolve_temporal_contract(
                payload,
                version_id="biology_v6_windowed_smooth_hierarchical",
                profile_id="smooth_window_30d_plus_physical_state",
                source_temporal_contract_id="fixed_gap_7d_biology_v5_raw365_v2",
            ),
        )
