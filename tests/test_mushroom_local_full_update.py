import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_local_full_update
from rainmapper_core import mushroom_performance_telemetry


class MushroomLocalFullUpdateTests(unittest.TestCase):
    @staticmethod
    def _paths(root: Path, *, work_root: Path) -> mushroom_local_full_update.LocalFullUpdatePaths:
        live = root / "mushroom-data"
        return mushroom_local_full_update.LocalFullUpdatePaths(
            observations=live / "mushroom_observations.json",
            reference_catalogs=live / "mushroom_reference_catalogs.json",
            gis_mappings=live / "mushroom_gis_mappings.json",
            weather_data_dir=root / "Data",
            gis_root=root / "mushroom-GIS",
            known_sites=live / "mushroom_known_sites.json",
            stations=root / "stations.txt",
            registry=live / "mushroom_ml_version_registry.json",
            mushroom_data_dir=live,
            ml_models_dir=live / "ml_models",
            ml_report=live / "mushroom_ml_report.json",
            bundle_root=live / ".worker-input-bundles",
            candidate_results_root=live / ".worker-candidate-results",
            work_root=work_root,
        )

    def test_work_root_must_be_outside_live_mushroom_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._paths(
                root,
                work_root=root / "mushroom-data" / ".local-full-update",
            )

            with self.assertRaisesRegex(ValueError, "must not overlap live mushroom data"):
                mushroom_local_full_update._validate_isolated_work_root(paths)

    def test_work_root_accepts_share_root_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._paths(root, work_root=root / ".local-full-update")

            mushroom_local_full_update._validate_isolated_work_root(paths)

    def test_training_species_require_ten_eligible_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            features = Path(temporary) / "features.json"
            rows = []
            for species_id, count in (
                ("eligible", 10),
                ("too_small", 9),
                ("single_class", 10),
            ):
                rows.extend(
                    {
                        "species_id": species_id,
                        "validation_status": "valid",
                        "calibration_use": "include",
                        "prediction_target": (
                            "unfavorable"
                            if species_id == "eligible" and index % 2
                            else "favorable"
                        ),
                        "micro_area_id": "area-1",
                    }
                    for index in range(count)
                )
            rows.append(
                {
                    "species_id": "excluded",
                    "validation_status": "invalid",
                    "calibration_use": "include",
                    "prediction_target": "favorable",
                    "micro_area_id": "area-1",
                }
            )
            features.write_text(json.dumps({"rows": rows}), encoding="utf-8")

            self.assertEqual(
                ["eligible"],
                mushroom_local_full_update.eligible_training_species(features),
            )

    def test_operational_tuning_catalog_comes_from_shared_installed_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "models" / "batches" / "batch-source"
            source.mkdir(parents=True)
            (source / "manifest.json").write_text(
                json.dumps({"batch_id": "batch-source"}), encoding="utf-8"
            )
            destination = root / "operation" / "tuning-catalog.json"
            catalog = {"catalog_id": "sha256:" + "a" * 64}

            with mock.patch.object(
                mushroom_local_full_update.mushroom_ml_tuning_catalog,
                "installed_source_batch_id",
                return_value="batch-source",
            ) as source_batch, mock.patch.object(
                mushroom_local_full_update.mushroom_ml_model_catalog,
                "validate_batch_manifest",
                return_value={"tuning_catalog": None},
            ), mock.patch.object(
                mushroom_local_full_update.mushroom_ml_tuning_catalog,
                "build_from_batch",
                return_value=catalog,
            ) as build, mock.patch.object(
                mushroom_local_full_update.mushroom_ml_tuning_catalog,
                "save",
            ) as save:
                result = mushroom_local_full_update._materialize_operational_tuning_catalog(
                    registry={"schema_version": "test"},
                    version_ids=["biology_v5_windowed_raw_weather"],
                    models_root=root / "models",
                    destination=destination,
                )

            self.assertIs(result, catalog)
            source_batch.assert_called_once()
            self.assertEqual(source, build.call_args.kwargs["batch_root"])
            save.assert_called_once_with(destination, catalog)

    def test_operational_tuning_catalog_reuses_persisted_batch_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "models" / "batches" / "batch-source"
            source.mkdir(parents=True)
            (source / "manifest.json").write_text("{}", encoding="utf-8")
            catalog = {
                "catalog_id": "sha256:" + "a" * 64,
                "source_batch_id": "batch-source",
                "decisions": [{"key": "decision"}],
            }
            content = json.dumps(catalog).encode("utf-8")
            (source / "tuning-catalog.json").write_bytes(content)
            destination = root / "operation" / "tuning-catalog.json"

            with mock.patch.object(
                mushroom_local_full_update.mushroom_ml_tuning_catalog,
                "installed_source_batch_id",
                return_value="batch-source",
            ), mock.patch.object(
                mushroom_local_full_update.mushroom_ml_model_catalog,
                "validate_batch_manifest",
                return_value={
                    "tuning_catalog": {
                        "catalog_id": catalog["catalog_id"],
                        "source_batch_id": "batch-source",
                        "decision_count": 1,
                        "path": "batches/batch-source/tuning-catalog.json",
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                },
            ), mock.patch.object(
                mushroom_local_full_update.mushroom_ml_tuning_catalog,
                "validate_catalog",
                return_value=catalog,
            ), mock.patch.object(
                mushroom_local_full_update.mushroom_ml_tuning_catalog,
                "build_from_batch",
            ) as build, mock.patch.object(
                mushroom_local_full_update.mushroom_ml_tuning_catalog,
                "save",
            ) as save:
                result = mushroom_local_full_update.materialize_operational_tuning_catalog(
                    registry={"schema_version": "test"},
                    version_ids=["biology_v5_windowed_raw_weather"],
                    models_root=root / "models",
                    destination=destination,
                )

            self.assertIs(result, catalog)
            build.assert_not_called()
            save.assert_called_once_with(destination, catalog)

    def test_runtime_batch_rollback_removes_only_new_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            models_root = Path(temporary)
            installed = models_root / "batches" / "new_batch"
            installed.mkdir(parents=True)
            mushroom_local_full_update.mushroom_ml_multiversion_transport.remove_installed_batch(
                models_root=models_root,
                batch_id="new_batch",
            )

            self.assertFalse(installed.exists())
            self.assertFalse((models_root / "runtime-batch.json").exists())

    def test_training_progress_maps_fit_count_inside_training_phase(self) -> None:
        percent, phase, detail = mushroom_local_full_update._training_progress_update(
            {
                "completed_fit_count": 50,
                "planned_fit_count": 100,
                "successful_fit_count": 48,
                "failed_fit_count": 2,
                "version_id": "biology_v4",
                "species_id": "boletus_edulis",
            }
        )

        self.assertEqual(74, percent)
        self.assertEqual("Training active operational generation", phase)
        self.assertIn("50/100", detail)
        self.assertIn("biology_v4", detail)
        self.assertIn("boletus_edulis", detail)
        self.assertIn("✗ 2", detail)

    def test_preparation_progress_maps_steps_inside_preparation_phase(self) -> None:
        percent, phase, detail = mushroom_local_full_update._preparation_progress_update(
            {
                "completed_step_count": 5,
                "planned_step_count": 8,
                "phase": "Built V5 raw-weather inputs",
                "detail": "125/352 area cutoffs materialized.",
            }
        )

        self.assertEqual(55, percent)
        self.assertIn("Built V5 raw-weather inputs", phase)
        self.assertIn("not training", phase)
        self.assertEqual("125/352 area cutoffs materialized.", detail)

    def test_command_forwards_flushed_jsonl_progress_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            progress_path = Path(temporary) / "progress.jsonl"
            received = []
            event = {
                "completed_fit_count": 1,
                "planned_fit_count": 2,
                "successful_fit_count": 1,
                "failed_fit_count": 0,
                "version_id": "biology_v3",
                "species_id": "boletus_edulis",
            }
            child = (
                "import json,sys,time; "
                "p=open(sys.argv[1],'x',encoding='utf-8'); "
                f"p.write(json.dumps({event!r})+'\\n'); p.flush(); "
                "time.sleep(0.35); "
                f"p.write(json.dumps({{**{event!r},'completed_fit_count':2}})+'\\n'); "
                "p.flush(); p.close()"
            )

            mushroom_local_full_update._run_command_with_jsonl_progress(
                [sys.executable, "-c", child, str(progress_path)],
                description="test progress",
                progress_path=progress_path,
                progress=lambda *values: received.append(values),
                event_mapper=mushroom_local_full_update._training_progress_update,
            )

            self.assertEqual([74, 90], [row[0] for row in received])
            self.assertIn("1/2", received[0][2])
            self.assertIn("2/2", received[1][2])

    def test_command_progress_reads_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            progress_path = root / "progress.jsonl"
            telemetry = mushroom_performance_telemetry.PersistentTelemetry(
                root / "telemetry.json",
                operation_id="progress_test",
                workload="test",
            )
            child = (
                "import json,sys; "
                "p=open(sys.argv[1],'x',encoding='utf-8'); "
                "p.write(json.dumps({'completed_fit_count':1,'planned_fit_count':1})+'\\n'); "
                "p.close()"
            )

            with mushroom_performance_telemetry.activate(telemetry):
                mushroom_local_full_update._run_command_with_jsonl_progress(
                    [sys.executable, "-c", child, str(progress_path)],
                    description="counted progress",
                    progress_path=progress_path,
                    progress=lambda *_values: None,
                    event_mapper=lambda _event: (50, "phase", "detail"),
                    telemetry_event_mapper=lambda _event: "test_progress_subphase",
                )
            summary = telemetry.finish("complete")

            self.assertGreaterEqual(summary["counters"]["files_read"], 1)
            self.assertGreaterEqual(
                summary["counters"]["bytes_read"], progress_path.stat().st_size
            )
            self.assertIn(
                "test_progress_subphase",
                [row["name"] for row in summary["phases"]],
            )

    def test_command_stops_when_local_benchmark_cancel_is_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            progress_path = Path(temporary) / "progress.jsonl"

            with self.assertRaises(mushroom_local_full_update.LocalBenchmarkCancelled):
                mushroom_local_full_update._run_command_with_jsonl_progress(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    description="cancel test",
                    progress_path=progress_path,
                    progress=lambda *_values: None,
                    event_mapper=mushroom_local_full_update._training_progress_update,
                    cancel_requested=lambda: True,
                )

if __name__ == "__main__":
    unittest.main()
