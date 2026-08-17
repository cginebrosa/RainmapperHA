import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest import mock

import numpy as np
from sklearn.linear_model import LogisticRegression

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_runtime_inference as inference
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / "mushroom-data/mushroom_ml_version_registry.json"
)


class MushroomMLRuntimeInferenceTests(TestCase):
    def setUp(self) -> None:
        inference.clear_artifact_cache()

    def test_predicts_one_estimator_without_ensemble(self) -> None:
        model = LogisticRegression().fit(
            np.asarray([[0.0], [1.0], [2.0], [3.0]]),
            np.asarray([0, 0, 1, 1]),
        )
        bundle = {
            "artifact_ref": catalog.ModelArtifactRef(
                batch_id="batch-a",
                generation_id="generation-a",
                version_id="biology_v3",
                temporal_contract_id="fixed_gap_7d_biology_v3",
                profile_id="core",
                estimator_id="logistic_regression_reduced_v1",
                species_id="boletus_edulis",
            ).as_dict(),
            "feature_cols": ["rain"],
            "model": model,
            "preprocessor": None,
        }

        result = inference.predict_bundle(
            bundle, {"rain": 2.5}, species_id="boletus_edulis"
        )

        self.assertGreater(result["probability"], 0.5)
        self.assertFalse(result["ensemble_used"])
        self.assertEqual(result["estimator_id"], "logistic_regression_reduced_v1")

    def test_missing_features_are_reported_not_silently_zeroed(self) -> None:
        class MissingAwareModel:
            def predict_proba(self, values):
                self.values = values
                return np.asarray([[0.6, 0.4]])

        model = MissingAwareModel()
        bundle = {
            "artifact_ref": catalog.ModelArtifactRef(
                batch_id="batch-a",
                generation_id="generation-a",
                version_id="biology_v3",
                temporal_contract_id="fixed_gap_7d_biology_v3",
                profile_id="core",
                estimator_id="random_forest_restricted_v1",
                species_id="boletus_edulis",
            ).as_dict(),
            "feature_cols": ["rain"],
            "model": model,
            "preprocessor": None,
        }

        result = inference.predict_bundle(
            bundle, {"rain": None}, species_id="boletus_edulis"
        )

        self.assertTrue(np.isnan(model.values[0][0]))
        self.assertEqual(result["missing_features"], ["rain"])

    def test_reports_out_of_training_domain_without_changing_probability(self) -> None:
        class FixedModel:
            def predict_proba(self, values):
                return np.asarray([[0.25, 0.75]])

        bundle = {
            "artifact_ref": catalog.ModelArtifactRef(
                batch_id="batch-a", generation_id="generation-a", version_id="biology_v3",
                temporal_contract_id="fixed_gap_7d_biology_v3", profile_id="core",
                estimator_id="random_forest_restricted_v1", species_id="boletus_edulis",
            ).as_dict(),
            "feature_cols": ["temperature"],
            "feature_support": {
                "temperature": {"min": 5.0, "max": 20.0, "mean": 12.0, "std": 4.0}
            },
            "model": FixedModel(),
            "preprocessor": None,
        }

        result = inference.predict_bundle(
            bundle, {"temperature": 28.0}, species_id="boletus_edulis"
        )

        self.assertEqual(result["probability"], 0.75)
        self.assertEqual(result["applicability"]["status"], "outside_domain")
        self.assertEqual(result["applicability"]["outside_feature_count"], 1)

    def test_exact_artifact_is_deserialized_once_while_file_identity_is_unchanged(
        self,
    ) -> None:
        import joblib

        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        artifact_ref = catalog.ModelArtifactRef(
            batch_id="batch-a",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
        )
        model_ref = catalog.ModelRef(
            **artifact_ref.as_dict(),
            horizon_days=7,
        )
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = catalog.model_relative_path(artifact_ref)
            path = root / relative
            path.parent.mkdir(parents=True)
            joblib.dump({"artifact_ref": artifact_ref.as_dict(), "marker": 1}, path)
            manifest = {
                "schema_version": "1.0",
                "kind": "mushroom_ml_runtime_batch",
                "batch_id": "batch-a",
                "snapshot_id": "sha256:" + "a" * 64,
                "artifacts": [
                    {
                        "artifact_ref": artifact_ref.as_dict(),
                        "supported_horizons": [7],
                        "path": relative.as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                ],
            }

            with mock.patch("joblib.load", wraps=joblib.load) as load:
                first = inference.load_exact_artifact(
                    registry, manifest, model_ref, root=root
                )
                second = inference.load_exact_artifact(
                    registry, manifest, model_ref, root=root
                )

            self.assertIs(first, second)
            self.assertEqual(load.call_count, 1)

    def test_cached_artifact_is_rejected_after_file_changes(self) -> None:
        import joblib

        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        artifact_ref = catalog.ModelArtifactRef(
            batch_id="batch-a",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
        )
        model_ref = catalog.ModelRef(**artifact_ref.as_dict(), horizon_days=7)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = catalog.model_relative_path(artifact_ref)
            path = root / relative
            path.parent.mkdir(parents=True)
            joblib.dump({"artifact_ref": artifact_ref.as_dict()}, path)
            manifest = {
                "schema_version": "1.0",
                "kind": "mushroom_ml_runtime_batch",
                "batch_id": "batch-a",
                "snapshot_id": "sha256:" + "a" * 64,
                "artifacts": [
                    {
                        "artifact_ref": artifact_ref.as_dict(),
                        "supported_horizons": [7],
                        "path": relative.as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                ],
            }
            inference.load_exact_artifact(registry, manifest, model_ref, root=root)
            path.write_bytes(path.read_bytes() + b"changed")

            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                inference.load_exact_artifact(
                    registry, manifest, model_ref, root=root
                )
