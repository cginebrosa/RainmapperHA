import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest import mock

import numpy as np

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLRuntimeTrainerTests(TestCase):
    def test_frozen_v5_config_skips_inner_selection(self) -> None:
        X = np.asarray(
            [[float(index), float(index % 3)] for index in range(20)], dtype=float
        )
        y = np.asarray([index % 2 for index in range(20)], dtype=int)
        samples = [
            {
                "prediction_target": "favorable" if value else "unfavorable",
                "metadata": {"validation_group_14d": f"group-{index}"},
            }
            for index, value in enumerate(y)
        ]
        with mock.patch.object(
            trainer.mushroom_ml_holdout,
            "_select_v5",
            side_effect=AssertionError("inner selection must not run"),
        ):
            fitted = trainer._fit_v5(
                "elastic_net_logistic_raw365_v1",
                samples,
                X,
                y,
                ["feature_a", "feature_b"],
                fit_config={
                    "C": 0.1,
                    "l1_ratio": 0.9,
                    "class_weight": None,
                    "inner_selection_available": True,
                },
            )

        self.assertEqual(fitted["fit_config"]["C"], 0.1)
        self.assertTrue(fitted["fit_config"]["inner_selection_available"])

    def test_invalid_frozen_v5_config_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Frozen V5"):
            trainer._fit_v5(
                "elastic_net_logistic_raw365_v1",
                [],
                np.asarray([[0.0], [1.0]]),
                np.asarray([0, 1]),
                ["feature"],
                fit_config={"C": 0.1},
            )

    def test_operational_materialization_needs_only_v3_fixed_and_lag_inputs(self) -> None:
        fixed = {"source": "fixed"}
        lag = {"source": "lag"}
        with mock.patch.object(
            trainer.mushroom_ml_biology_v3_evaluation,
            "build_observation_altitude_v2_common_idw_benchmark",
            side_effect=lambda payload: {"altitude": payload["source"]},
        ):
            benchmarks = trainer.materialize_runtime_benchmarks(
                v3_fixed=fixed,
                v3_lag=lag,
            )

        self.assertEqual(len(benchmarks), 4)
        self.assertEqual(
            benchmarks[
                trainer.benchmark_key(
                    "altitude_v2", "fixed_gap_7d_altitude_v2", "common_idw"
                )
            ],
            {"altitude": "fixed"},
        )
        self.assertFalse(any("biology_v4" in key for key in benchmarks))
        self.assertFalse(any("biology_v5" in key for key in benchmarks))
        self.assertFalse(any("biology_v6" in key for key in benchmarks))

    def test_v3_physical_materializes_only_when_physical_sources_are_supplied(self) -> None:
        with mock.patch.object(
            trainer.mushroom_ml_biology_v3_physical,
            "materialize_benchmark",
            side_effect=lambda payload: {"physical": payload["source"]},
        ), mock.patch.object(
            trainer.mushroom_ml_biology_v4,
            "materialize_comparison_benchmark",
            side_effect=lambda payload, **_kwargs: {"v4": payload["source"]},
        ):
            benchmarks = trainer.materialize_runtime_benchmarks(
                v3_fixed={"source": "v3-fixed"},
                v3_lag={"source": "v3-lag"},
                v4_fixed={"source": "v4-fixed"},
                v4_lag={"source": "v4-lag"},
            )

        self.assertEqual(
            benchmarks[
                trainer.benchmark_key(
                    "biology_v3",
                    "fixed_gap_7d_biology_v3",
                    "common_idw_plus_physical_state",
                )
            ],
            {"physical": "v4-fixed"},
        )
        self.assertEqual(
            benchmarks[
                trainer.benchmark_key(
                    "biology_v3",
                    "lag_event_biology_v3",
                    "common_idw_plus_physical_state",
                )
            ],
            {"physical": "v4-lag"},
        )

    def test_registry_plan_has_complete_runtime_benchmark_coverage(self) -> None:
        from rainmapper_core import mushroom_ml_multiversion_plan

        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        generation_ids = {
            row["version_id"]: f"generation-{row['version_id']}"
            for row in registry["versions"]
        }
        training_plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id="coverage-test",
            snapshot_id="sha256:" + "c" * 64,
            generation_ids=generation_ids,
            species_ids=["boletus_edulis"],
        )

        trainer.validate_benchmark_coverage(
            training_plan,
            trainer.supported_runtime_benchmark_keys(),
        )

    def test_missing_runtime_benchmark_is_rejected_before_fitting(self) -> None:
        training_plan = {
            "fits": [
                {
                    "artifact_ref": {
                        "version_id": "biology_v5_raw_weather_discovery",
                        "temporal_contract_id": "fixed_gap_7d_biology_v5_raw365_v1",
                        "profile_id": "raw_primary_no_calendar",
                    }
                }
            ]
        }

        with self.assertRaisesRegex(ValueError, "Runtime registry is incompatible"):
            trainer.validate_benchmark_coverage(
                training_plan,
                trainer.supported_runtime_benchmark_keys(),
            )

    def test_batch_is_immutable_verified_and_not_activated(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        artifact_ref = catalog.ModelArtifactRef(
            batch_id="batch-test",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
        )
        training_plan = {
            "batch_id": "batch-test",
            "snapshot_id": "sha256:" + "a" * 64,
            "fits": [
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": [7],
                }
            ],
        }
        samples = []
        for index in range(20):
            samples.append(
                {
                    "sample_id": f"sample-{index}",
                    "prediction_target": "favorable" if index % 2 else "unfavorable",
                    "predictive_features": {"test_feature": float(index)},
                    "quality": {"training_eligible": True},
                    "metadata": {
                        "species_id": "boletus_edulis",
                        "area_id": "area-a",
                        "target_date": f"2025-01-{index + 1:02d}",
                    },
                }
            )
        benchmark = {
            "feature_set": {"predictive_feature_cols": ["test_feature"]},
            "samples": samples,
        }
        key = trainer.benchmark_key(
            "biology_v3", "fixed_gap_7d_biology_v3", "core"
        )

        with TemporaryDirectory() as temporary:
            models_root = Path(temporary)
            progress_events = []
            destination, manifest = trainer.write_batch(
                registry,
                training_plan,
                {key: benchmark},
                models_root=models_root,
                progress_callback=progress_events.append,
            )

            stored = json.loads((destination / "manifest.json").read_text())
            model_path = models_root / stored["artifacts"][0]["path"]
            self.assertTrue(model_path.is_file())
            self.assertEqual(trainer.sha256(model_path), stored["artifacts"][0]["sha256"])
            self.assertFalse(stored["active"])
            self.assertFalse((models_root / "runtime-batch.json").exists())
            self.assertEqual(manifest["batch_id"], "batch-test")
            self.assertEqual(progress_events[-1]["completed_fit_count"], 1)
            self.assertEqual(progress_events[-1]["planned_fit_count"], 1)
            self.assertEqual(stored["fit_results"][0]["status"], "complete")
            self.assertGreaterEqual(stored["fit_results"][0]["duration_seconds"], 0)
            self.assertEqual(
                stored["fit_results"][0]["artifact_ref"], artifact_ref.as_dict()
            )
            with self.assertRaises(FileExistsError):
                trainer.write_batch(
                    registry,
                    training_plan,
                    {key: benchmark},
                    models_root=models_root,
                )

    def test_untrainable_members_are_reported_without_discarding_batch(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        trainable = catalog.ModelArtifactRef(
            batch_id="batch-partial",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
        )
        unavailable = catalog.ModelArtifactRef(
            **{
                **trainable.as_dict(),
                "species_id": "amanita_caesarea",
            }
        )
        training_plan = {
            "batch_id": "batch-partial",
            "snapshot_id": "sha256:" + "b" * 64,
            "fits": [
                {"artifact_ref": trainable.as_dict(), "supported_horizons": [7]},
                {"artifact_ref": unavailable.as_dict(), "supported_horizons": [7]},
            ],
        }
        samples = [
            {
                "sample_id": f"sample-{index}",
                "prediction_target": "favorable" if index % 2 else "unfavorable",
                "predictive_features": {"test_feature": float(index)},
                "quality": {"training_eligible": True},
                "metadata": {
                    "species_id": "boletus_edulis",
                    "area_id": "area-a",
                    "target_date": f"2025-01-{index + 1:02d}",
                },
            }
            for index in range(20)
        ]
        benchmark = {
            "feature_set": {"predictive_feature_cols": ["test_feature"]},
            "samples": samples,
        }
        key = trainer.benchmark_key("biology_v3", "fixed_gap_7d_biology_v3", "core")

        with TemporaryDirectory() as temporary:
            _destination, manifest = trainer.write_batch(
                registry,
                training_plan,
                {key: benchmark},
                models_root=Path(temporary),
            )

        self.assertEqual(manifest["planned_fit_count"], 2)
        self.assertEqual(manifest["successful_fit_count"], 1)
        self.assertEqual(manifest["failed_fit_count"], 1)
        self.assertEqual(
            manifest["failed_fits"][0]["artifact_ref"]["species_id"],
            "amanita_caesarea",
        )
