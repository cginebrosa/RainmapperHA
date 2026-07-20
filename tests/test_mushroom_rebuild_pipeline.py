import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_rebuild_pipeline


class MushroomRebuildPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.inputs_root = self.root / "inputs"
        self.inputs_root.mkdir()
        self.observations_path = self.inputs_root / "mushroom_observations.json"
        self.catalogs_path = self.inputs_root / "mushroom_reference_catalogs.json"
        self.gis_mappings_path = self.inputs_root / "mushroom_gis_mappings.json"
        self.weather_dir = self.inputs_root / "Data"
        self.weather_dir.mkdir()
        self.gis_root = self.inputs_root / "mushroom-GIS"
        self.gis_root.mkdir()
        self.write_inputs()

    def write_inputs(self) -> None:
        self.observations_path.write_text(
            json.dumps(
                {
                    "observations": [
                        {
                            "observation_id": "obs_1",
                            "species_id": "boletus_test",
                            "observed_at": "2026-07-10",
                            "location": {"lat": 42.0, "lon": 2.0},
                            "altitude": {"meters": 700},
                            "flush_abundance": "normal",
                            "validation_status": "valid",
                            "calibration_use": "include",
                            "source_quality": 1,
                            "site_context": {},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.catalogs_path.write_text(
            json.dumps(
                {
                    "catalogs": {
                        "observation_flush_abundance": [
                            {"id": "normal", "prediction_favorable": 1},
                            {"id": "absent", "prediction_favorable": 0},
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        self.gis_mappings_path.write_text(json.dumps({"exact_value_mappings": []}), encoding="utf-8")
        (self.weather_dir / "Meteocat_incremental.csv").write_text(
            "Codi Estació,Estació,Latitud,Longitud,Data Local,Total\n"
            "ST_NEAR,Near station,42.01,2.01,20260710,2.5\n",
            encoding="utf-8",
        )

    def input_paths(self) -> mushroom_rebuild_pipeline.RebuildInputPaths:
        return mushroom_rebuild_pipeline.RebuildInputPaths(
            observations=self.observations_path,
            reference_catalogs=self.catalogs_path,
            gis_mappings=self.gis_mappings_path,
            weather_data_dir=self.weather_dir,
            gis_root=self.gis_root,
        )

    def test_run_rebuild_writes_complete_chain_only_under_output_root(self) -> None:
        outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "outputs")
        input_contents = {
            path: path.read_bytes()
            for path in (self.observations_path, self.catalogs_path, self.gis_mappings_path)
        }
        progress: list[dict[str, object]] = []

        result = mushroom_rebuild_pipeline.run_rebuild(
            self.input_paths(),
            outputs,
            progress_callback=progress.append,
        )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["selected_observation_ids"], ["obs_1"])
        self.assertEqual(result["summary"]["gis_observations"], 1)
        self.assertEqual(result["summary"]["weather_observations"], 1)
        self.assertEqual(result["summary"]["feature_observations"], 1)
        self.assertEqual(result["summary"]["model_species"], 1)
        self.assertEqual(
            set(result["phase_durations_seconds"]),
            {"gis_dem", "weather", "features_v0", "learned_model_v0"},
        )
        for key, raw_path in outputs.as_dict().items():
            if key == "root":
                continue
            output_path = Path(raw_path)
            self.assertTrue(output_path.exists(), raw_path)
            self.assertIn(outputs.root, output_path.parents)
        for path, contents in input_contents.items():
            self.assertEqual(path.read_bytes(), contents)
        gis_payload = json.loads(outputs.gis_reconstruction.read_text(encoding="utf-8"))
        self.assertTrue(
            gis_payload["results"][0]["layers"]["dem_5m"]["source"].startswith(str(self.gis_root))
        )
        self.assertEqual(progress[-1]["overall_percent"], 100)
        self.assertEqual({event["phase_index"] for event in progress}, {1, 2, 3, 4})

    def test_cancelled_rebuild_does_not_write_artifacts(self) -> None:
        outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "cancelled")
        cancel_event = threading.Event()
        cancel_event.set()

        with self.assertRaises(mushroom_rebuild_pipeline.RebuildCancelled):
            mushroom_rebuild_pipeline.run_rebuild(
                self.input_paths(),
                outputs,
                cancel_event=cancel_event,
            )

        for key, raw_path in outputs.as_dict().items():
            if key != "root":
                self.assertFalse(Path(raw_path).exists())

    def test_cancellation_during_gis_stops_before_writing_artifacts(self) -> None:
        outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "cancelled-during-gis")
        cancel_event = threading.Event()

        def cancel_after_first_gis_result(event: dict[str, object]) -> None:
            if event["phase_index"] == 1 and int(event["phase_percent"]) > 0:
                cancel_event.set()

        with self.assertRaises(mushroom_rebuild_pipeline.RebuildCancelled):
            mushroom_rebuild_pipeline.run_rebuild(
                self.input_paths(),
                outputs,
                progress_callback=cancel_after_first_gis_result,
                cancel_event=cancel_event,
            )

        for key, raw_path in outputs.as_dict().items():
            if key != "root":
                self.assertFalse(Path(raw_path).exists())

    def write_accepted_outputs(
        self,
        outputs: mushroom_rebuild_pipeline.RebuildOutputPaths,
        content: str,
    ) -> None:
        for field in mushroom_rebuild_pipeline.ACCEPTED_OUTPUT_FIELDS:
            path = Path(getattr(outputs, field))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_promote_rebuild_outputs_replaces_all_accepted_artifacts(self) -> None:
        staged = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "staged")
        final = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "final")
        self.write_accepted_outputs(staged, "new")
        self.write_accepted_outputs(final, "old")

        result = mushroom_rebuild_pipeline.promote_rebuild_outputs(staged, final)

        self.assertEqual(result["status"], "promoted")
        self.assertEqual(result["artifact_count"], 9)
        for field in mushroom_rebuild_pipeline.ACCEPTED_OUTPUT_FIELDS:
            self.assertEqual(Path(getattr(final, field)).read_text(encoding="utf-8"), "new")

    def test_promote_rebuild_outputs_rolls_back_if_replace_fails(self) -> None:
        staged = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "staged-failure")
        final = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "final-failure")
        self.write_accepted_outputs(staged, "new")
        self.write_accepted_outputs(final, "old")
        real_replace = os.replace
        replace_count = 0

        def fail_once(source: Path, destination: Path) -> None:
            nonlocal replace_count
            replace_count += 1
            if replace_count == 3:
                raise OSError("injected promotion failure")
            real_replace(source, destination)

        with mock.patch.object(mushroom_rebuild_pipeline.os, "replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "injected promotion failure"):
                mushroom_rebuild_pipeline.promote_rebuild_outputs(staged, final)

        for field in mushroom_rebuild_pipeline.ACCEPTED_OUTPUT_FIELDS:
            self.assertEqual(Path(getattr(final, field)).read_text(encoding="utf-8"), "old")

    def test_seed_partial_model_outputs_preserves_existing_model(self) -> None:
        staged = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "staged-partial")
        final = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "final-partial")
        final.model_json.parent.mkdir(parents=True)
        final.model_json.write_text("existing model", encoding="utf-8")
        final.model_report.parent.mkdir(parents=True)
        final.model_report.write_text("existing report", encoding="utf-8")

        mushroom_rebuild_pipeline.seed_partial_model_outputs(staged, final)

        self.assertEqual(staged.model_json.read_text(encoding="utf-8"), "existing model")
        self.assertEqual(staged.model_report.read_text(encoding="utf-8"), "existing report")


if __name__ == "__main__":
    unittest.main()
