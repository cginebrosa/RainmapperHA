import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_local_full_update


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
                mushroom_local_full_update._eligible_training_species(features),
            )

    def test_runtime_batch_rollback_restores_previous_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            models_root = Path(temporary)
            installed = models_root / "batches" / "new_batch"
            installed.mkdir(parents=True)
            descriptor = models_root / "runtime-batch.json"
            descriptor.write_text('{"batch_id":"new_batch"}\n', encoding="utf-8")
            previous = b'{"batch_id":"previous_batch"}\n'

            mushroom_local_full_update._restore_runtime_batch(
                models_root=models_root,
                installed_batch_id="new_batch",
                previous_descriptor=previous,
            )

            self.assertFalse(installed.exists())
            self.assertEqual(previous, descriptor.read_bytes())

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

    def test_operational_candidate_reuses_fresh_benchmark_without_training(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._paths(root, work_root=root / ".local-full-update")
            benchmark_id = "benchmark-v4"
            benchmark_root = paths.ml_models_dir / "benchmarks" / benchmark_id
            benchmark_root.mkdir(parents=True)
            training = benchmark_root / "training-input-manifest.json"
            training.write_text(
                json.dumps({"snapshot_id": "sha256:" + "a" * 64}),
                encoding="utf-8",
            )
            (benchmark_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "snapshot_id": "sha256:" + "a" * 64,
                        "training_input_manifest": {
                            "path": f"batches/{benchmark_id}/training-input-manifest.json"
                        },
                    }
                ),
                encoding="utf-8",
            )
            profiles = [
                {"version_id": "biology_v4", "profile_key": "biology_v4/extended_weather"},
                {"version_id": "biology_v4", "profile_key": "biology_v4/climatic_balance"},
            ]
            report = {
                "snapshot_id": "sha256:" + "a" * 64,
                "selection": {"profiles": profiles},
            }
            archived = {
                "candidate_id": "candidate-v4",
                "artifact_preparation": "verified_benchmark_reuse",
            }

            with mock.patch.object(
                mushroom_local_full_update.mushroom_ml_version_registry,
                "load_registry",
                return_value={},
            ), mock.patch.object(
                mushroom_local_full_update.mushroom_ml_version_registry,
                "operational_profile_options",
                return_value=profiles,
            ), mock.patch.object(
                mushroom_local_full_update.mushroom_ml_benchmark_reports,
                "load_report",
                return_value=report,
            ), mock.patch.object(
                mushroom_local_full_update.mushroom_rebuild_snapshot,
                "verify_live_inputs",
                return_value={"status": "valid"},
            ), mock.patch.object(
                mushroom_local_full_update.mushroom_ml_multiversion_transport,
                "archive_benchmark_as_candidate",
                return_value=archived,
            ) as reuse, mock.patch.object(
                mushroom_local_full_update,
                "_run_command_with_jsonl_progress",
            ) as training_command:
                result = mushroom_local_full_update.run_local_operational_candidate(
                    operation_id="operation-a",
                    benchmark_batch_id=benchmark_id,
                    version_id="biology_v4",
                    paths=paths,
                    progress=lambda *_values: None,
                )

            training_command.assert_not_called()
            reuse.assert_called_once()
            self.assertEqual(result["artifact_preparation"], "verified_benchmark_reuse")
            self.assertFalse(result["runtime_changed"])


if __name__ == "__main__":
    unittest.main()
