from __future__ import annotations

import importlib.util
import gzip
import json
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_ml_version_registry


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run-mushroom-ml-multiversion-job.py"
REGISTRY = ROOT / "mushroom-data/mushroom_ml_version_registry.json"


def load_script():
    spec = importlib.util.spec_from_file_location("run_ml_multiversion", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def complete_quality_catalog(module):
    rows = [
        {
            "version_id": "biology_v4",
            "profile_id": "extended_weather",
            "species_id": "species_a",
            "area_id": "area_a",
            "split_id": "fruiting_groups_14d",
            "temporal_contract_id": "fixed_gap_7d_biology_v4",
            "horizon_days": 7,
            "observation_id": f"observation-{index}",
            "validation_group_id": f"group-{index // 2}",
            "y_true": index % 2,
            "train_prevalence_probability": 0.5,
            "estimator_probabilities": {
                "logistic_regression_reduced_v1": 0.8 if index % 2 else 0.2
            },
        }
        for index in range(8)
    ]
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        first = root / "v2-v5.jsonl"
        first.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        second = root / "v6.jsonl"
        second.write_text("", encoding="utf-8")
        return module.mushroom_ml_quality_catalog.build_catalog(
            first,
            second,
            snapshot_id="sha256:" + "a" * 64,
            profile_keys=["biology_v4/extended_weather"],
            expected_estimators={
                "biology_v4/extended_weather": [
                    "logistic_regression_reduced_v1"
                ]
            },
        )


class RunMushroomMLMultiversionJobTests(TestCase):
    def test_main_hashes_manifest_after_batch_is_moved_to_result_staging(self) -> None:
        module = load_script()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            produced_batch = root / "models" / "batches" / "batch-test"
            result_manifest = root / "result" / "multiversion_result.json"
            summary_path = root / "summary.json"
            args = Namespace(
                registry=root / "registry.json",
                generation=[("biology_v3", "generation-test")],
                job_purpose="benchmark",
                profile_key=[],
                version=["biology_v3"],
                batch_id="batch-test",
                snapshot_id="sha256:" + "a" * 64,
                species=[],
                operational_plan=None,
                tuning_catalog=None,
                quality_catalog=root / "unused-quality-catalog.json",
                v3_fixed=root / "v3-fixed.json",
                v3_lag=root / "v3-lag.json",
                v4_fixed=None,
                v4_lag=None,
                v5_fixed=None,
                v5_lag=None,
                v2_v5_heldout=root / "v2-v5.jsonl",
                v6_heldout=root / "v6.jsonl",
                models_root=root / "models",
                progress_jsonl=None,
                job_id="job-test",
                result_manifest=result_manifest,
                summary=summary_path,
                training_input_manifest=None,
            )
            manifest = {
                "batch_id": "batch-test",
                "snapshot_id": args.snapshot_id,
                "artifacts": [],
                "planned_fit_count": 0,
                "successful_fit_count": 0,
                "failed_fit_count": 0,
            }
            args.v3_fixed.write_text("{}\n", encoding="utf-8")
            args.v3_lag.write_text("{}\n", encoding="utf-8")

            def write_batch(*_args, **_kwargs):
                produced_batch.mkdir(parents=True)
                (produced_batch / "manifest.json").write_text(
                    json.dumps(manifest) + "\n", encoding="utf-8"
                )
                return produced_batch, dict(manifest)

            with (
                patch.object(module, "parse_args", return_value=args),
                patch.object(
                    module.mushroom_ml_version_registry,
                    "load_registry",
                    return_value={},
                ),
                patch.object(
                    module,
                    "resolve_training_scope",
                    return_value=([], [], ["biology_v3"]),
                ),
                patch.object(
                    module.mushroom_ml_model_catalog,
                    "catalog_entries",
                    return_value=[],
                ),
                patch.object(
                    module.mushroom_ml_multiversion_plan,
                    "build_plan",
                    return_value={"fit_count": 0, "fits": [], "profile_keys": []},
                ),
                patch.object(
                    module.mushroom_ml_runtime_trainer,
                    "materialize_runtime_benchmarks",
                    return_value={},
                ),
                patch.object(
                    module.mushroom_ml_runtime_trainer,
                    "write_batch",
                    side_effect=write_batch,
                ),
            ):
                self.assertEqual(0, module.main())

            staged_batch = result_manifest.parent / "batch"
            self.assertFalse(produced_batch.exists())
            self.assertTrue((staged_batch / "manifest.json").is_file())
            result = json.loads(result_manifest.read_text(encoding="utf-8"))
            self.assertEqual(
                module._sha256(staged_batch / "manifest.json"),
                result["batch_manifest_sha256"],
            )
            self.assertEqual(
                "batch/manifest.json",
                result["files"][0]["path"],
            )

    def test_operational_archive_helpers_leave_only_compressed_storage(self) -> None:
        module = load_script()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog_path = root / "quality-catalog.json.gz"
            module._write_gzip_json(catalog_path, {"value": "x" * 10000})
            self.assertEqual(
                {"value": "x" * 10000},
                json.loads(gzip.decompress(catalog_path.read_bytes())),
            )

            raw_path = root / "holdout-predictions.jsonl"
            raw_path.write_bytes((b'{"value":1}\n') * 1000)
            compressed_path = module._compress_and_remove(raw_path)
            self.assertFalse(raw_path.exists())
            self.assertEqual(
                (b'{"value":1}\n') * 1000,
                gzip.decompress(compressed_path.read_bytes()),
            )

            produced = root / "produced"
            produced.mkdir()
            manifest = produced / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            inode = manifest.stat().st_ino
            staged = root / "result" / "batch"
            module._move_batch(produced, staged)
            self.assertFalse(produced.exists())
            self.assertEqual(inode, (staged / "manifest.json").stat().st_ino)
            self.assertEqual([], list(root.rglob("*.backup")))
            self.assertEqual([], list(root.rglob("*.install")))

    def test_emitted_tuning_catalog_must_match_new_batch_manifest(self) -> None:
        module = load_script()
        with TemporaryDirectory() as temporary:
            destination = Path(temporary)
            tuning_path = destination / "tuning-catalog.json"
            emitted = {
                "catalog_id": "sha256:" + "a" * 64,
                "source_batch_id": "batch-new",
            }
            tuning_path.write_text(json.dumps(emitted) + "\n", encoding="utf-8")
            manifest = {
                "batch_id": "batch-new",
                "tuning_catalog": {
                    "catalog_id": emitted["catalog_id"],
                    "source_batch_id": "batch-new",
                    "path": "batches/batch-new/tuning-catalog.json",
                    "sha256": module._sha256(tuning_path),
                },
            }

            module._validate_emitted_tuning_catalog(destination, manifest)

            stale = dict(emitted, source_batch_id="batch-old")
            tuning_path.write_text(json.dumps(stale) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                module._validate_emitted_tuning_catalog(destination, manifest)

    def test_operational_quality_catalog_rejects_previous_schema_before_training(self) -> None:
        module = load_script()
        catalog = complete_quality_catalog(module)
        catalog["schema_version"] = "1.1"

        with self.assertRaisesRegex(ValueError, "contract is invalid"):
            module.validate_operational_quality_catalog(
                catalog, ["biology_v4/extended_weather"]
            )

    def test_operational_quality_catalog_rejects_profile_without_holdout_probabilities(self) -> None:
        module = load_script()
        catalog = complete_quality_catalog(module)
        catalog["entries"][0]["n_test"] = 0

        with self.assertRaisesRegex(ValueError, "no hold-out probabilities"):
            module.validate_operational_quality_catalog(
                catalog, ["biology_v4/extended_weather"]
            )

    def test_operational_quality_catalog_accepts_profile_with_holdout_probabilities(self) -> None:
        module = load_script()
        catalog = complete_quality_catalog(module)

        module.validate_operational_quality_catalog(
            catalog,
            ["biology_v4/extended_weather"],
            {
                "fits": [
                    {
                        "artifact_ref": {
                            "version_id": "biology_v4",
                            "profile_id": "extended_weather",
                            "temporal_contract_id": "fixed_gap_7d_biology_v4",
                            "estimator_id": "logistic_regression_reduced_v1",
                            "species_id": "species_a",
                        }
                    }
                ]
            },
        )

    def test_operational_quality_catalog_rejects_unplanned_selected_candidate(self) -> None:
        module = load_script()
        catalog = complete_quality_catalog(module)

        with self.assertRaisesRegex(ValueError, "does not materialize selected"):
            module.validate_operational_quality_catalog(
                catalog,
                ["biology_v4/extended_weather"],
                {
                    "fits": [
                        {
                            "artifact_ref": {
                                "version_id": "biology_v4",
                                "profile_id": "extended_weather",
                                "temporal_contract_id": "fixed_gap_7d_biology_v4",
                                "estimator_id": "different_estimator",
                                "species_id": "species_a",
                            }
                        }
                    ]
                },
            )

    def test_operational_bootstrap_selects_five_complete_versions(self) -> None:
        module = load_script()
        registry = mushroom_ml_version_registry.load_registry(REGISTRY)
        version_ids = [
            "altitude_v2",
            "biology_v3",
            "biology_v4",
            "biology_v5_windowed_raw_weather",
            "biology_v6_windowed_smooth_hierarchical",
        ]

        selected, profile_keys, resolved_versions = module.resolve_training_scope(
            registry,
            job_purpose="operational",
            profile_keys=None,
            version_ids=version_ids,
        )

        self.assertEqual(resolved_versions, version_ids)
        self.assertEqual(len(selected), 11)
        self.assertEqual(len(profile_keys), 11)
        self.assertFalse(
            any("raw_weather_discovery" in key for key in profile_keys)
        )
        self.assertFalse(
            any(
                key.startswith("biology_v6_smooth_hierarchical/")
                for key in profile_keys
            )
        )

        catalog = mushroom_ml_model_catalog.catalog_entries(registry)
        windows = sorted(
            {
                int(row["input_requirements"]["predictive_window_days"])
                for row in catalog
                if row["version_id"] in version_ids[-2:]
            }
        )
        self.assertEqual(windows, [30, 60, 90])
        self.assertTrue(
            all(
                row["input_requirements"]["weather_lookback_days"] == 365
                and row["input_requirements"]["include_physical_state"] is True
                for row in catalog
                if row["version_id"] in version_ids[-2:]
            )
        )

    def test_operational_scope_rejects_partial_version(self) -> None:
        module = load_script()
        registry = mushroom_ml_version_registry.load_registry(REGISTRY)

        with self.assertRaisesRegex(ValueError, "every profile in biology_v3"):
            module.resolve_training_scope(
                registry,
                job_purpose="operational",
                profile_keys=["biology_v3/core"],
                version_ids=["biology_v3"],
            )

    def test_training_manifest_publishes_complete_revision_vector(self) -> None:
        module = load_script()
        training_manifest = {
            "weather_history": {
                "generation_id": "weather-generation",
                "manifest_sha256": "a" * 64,
            },
            "files": [
                {"role": role, "sha256": character * 64}
                for role, character in (
                    ("observations", "b"),
                    ("reference_catalogs", "c"),
                    ("gis_mappings", "d"),
                    ("extra:known-sites.json", "e"),
                    ("extra:stations.txt", "f"),
                )
            ],
            "datasets": [
                {"dataset_id": "mushroom_gis_v0", "fingerprint": "sha256:" + "1" * 64}
            ],
        }
        with TemporaryDirectory() as temporary:
            registry_copy = Path(temporary) / "registry.json"
            registry_copy.write_bytes(REGISTRY.read_bytes())

            vector = module._input_revisions(training_manifest, registry_copy)

        self.assertEqual(
            set(vector), set(mushroom_ml_version_registry.REVISION_VECTOR_KEYS)
        )
        self.assertEqual(vector["weather_generation_id"], "weather-generation")
