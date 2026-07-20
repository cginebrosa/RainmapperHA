import copy
import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import (
    mushroom_rebuild_contracts,
    mushroom_rebuild_pipeline,
    mushroom_rebuild_snapshot,
)


class MushroomRebuildContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        source = self.root / "source"
        source.mkdir()
        self.weather = source / "Data"
        self.weather.mkdir()
        self.gis = source / "mushroom-GIS"
        mvc = self.gis / "MVC50mil/extracted"
        mvc.mkdir(parents=True)
        for extension in ("shp", "dbf", "shx"):
            (mvc / f"MVC50mil_novembre2019.{extension}").write_text(extension, encoding="utf-8")
        geology = self.gis / "geologia-territorial-50000-geologic-v3r0-202412/extracted"
        geology.mkdir(parents=True)
        (geology / "geologia-territorial-50000-geologic-v3r0-202412.gpkg").write_text(
            "geology",
            encoding="utf-8",
        )
        dem = self.gis / "model-elevacions-terreny-topografic-catalunya-5m-2009-2018/extracted"
        dem.mkdir(parents=True)
        (dem / "model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif").write_text(
            "dem",
            encoding="utf-8",
        )
        self.observations = source / "mushroom_observations.json"
        self.catalogs = source / "mushroom_reference_catalogs.json"
        self.mappings = source / "mushroom_gis_mappings.json"
        self.observations.write_text(
            json.dumps(
                {
                    "observations": [
                        {
                            "observation_id": "obs_1",
                            "validation_status": "valid",
                            "calibration_use": "include",
                            "location": {"lat": 42.0, "lon": 2.0},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.catalogs.write_text("{}", encoding="utf-8")
        self.mappings.write_text("{}", encoding="utf-8")
        (self.weather / "Meteocat_incremental.csv").write_text("header\n", encoding="utf-8")
        self.snapshot = self.root / "snapshot"
        mushroom_rebuild_snapshot.create_snapshot(
            self.snapshot,
            observations_path=self.observations,
            reference_catalogs_path=self.catalogs,
            gis_mappings_path=self.mappings,
            weather_data_dir=self.weather,
            gis_root=self.gis,
        )

    def create_spec(self) -> dict[str, object]:
        return mushroom_rebuild_contracts.create_job_spec(
            self.snapshot,
            job_id="job-test-1",
            created_at="2026-07-19T00:00:00+00:00",
        )

    def write_artifacts(self, output_dir: Path) -> None:
        outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(output_dir)
        for relative in mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS:
            path = outputs.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative == "mushroom_gis_observation_reconstruction.json":
                payload = {"result_count": 1}
            elif relative in {
                "mushroom_observations_weather_features.json",
                "mushroom_observation_features_v0.json",
            }:
                payload = {"summary": {"observations": 1}}
            elif relative == "mushroom_model_v0.json":
                payload = {"summary": {"species": 1}}
            else:
                payload = None
            content = json.dumps(payload) if payload is not None else relative + "\n"
            path.write_text(content, encoding="utf-8")

    def pipeline_result(self) -> dict[str, object]:
        return {
            "status": "complete",
            "summary": {
                "gis_observations": 1,
                "weather_observations": 1,
                "feature_observations": 1,
                "model_species": 1,
            },
            "phase_durations_seconds": {
                "gis_dem": 1.0,
                "weather": 2.0,
                "features_v0": 0.1,
                "learned_model_v0": 0.1,
            },
            "duration_seconds": 3.2,
        }

    def test_job_spec_matches_snapshot_and_exact_eligible_scope(self) -> None:
        job_spec = self.create_spec()

        result = mushroom_rebuild_contracts.verify_job_spec(job_spec, self.snapshot)

        self.assertEqual(result["status"], "valid")
        self.assertEqual(job_spec["scope"]["selected_observation_ids"], ["obs_1"])
        self.assertEqual(job_spec["expected_artifacts"], list(mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS))
        self.assertTrue(str(job_spec["job_spec_id"]).startswith("sha256:"))

    def test_job_spec_tampering_is_rejected(self) -> None:
        job_spec = self.create_spec()
        tampered = copy.deepcopy(job_spec)
        tampered["scope"]["selected_observation_ids"].append("obs_unknown")

        result = mushroom_rebuild_contracts.verify_job_spec(tampered, self.snapshot)

        self.assertEqual(result["status"], "invalid")
        self.assertIn("job spec hash mismatch", result["errors"])
        self.assertTrue(any("ineligible observation" in error for error in result["errors"]))

    def test_result_manifest_verifies_all_artifacts_and_detects_tampering(self) -> None:
        job_spec = self.create_spec()
        output_dir = self.root / "outputs"
        self.write_artifacts(output_dir)
        result_manifest = mushroom_rebuild_contracts.create_result_manifest(
            job_spec,
            output_dir,
            self.pipeline_result(),
            created_at="2026-07-19T00:01:00+00:00",
        )

        valid = mushroom_rebuild_contracts.verify_result_manifest(
            result_manifest,
            job_spec,
            output_dir,
        )
        self.assertEqual(valid["status"], "valid")
        self.assertEqual(valid["verified_artifacts"], 9)

        (output_dir / "mushroom_model_v0.json").write_text(
            json.dumps({"artifact": "tampered"}),
            encoding="utf-8",
        )
        invalid = mushroom_rebuild_contracts.verify_result_manifest(
            result_manifest,
            job_spec,
            output_dir,
        )
        self.assertEqual(invalid["status"], "invalid")
        self.assertTrue(any("mushroom_model_v0.json" in error for error in invalid["errors"]))

    def test_result_manifest_requires_every_expected_artifact(self) -> None:
        job_spec = self.create_spec()
        output_dir = self.root / "incomplete"
        self.write_artifacts(output_dir)
        (output_dir / "reports/mushroom_model_v0.md").unlink()

        with self.assertRaisesRegex(FileNotFoundError, "mushroom_model_v0.md"):
            mushroom_rebuild_contracts.create_result_manifest(
                job_spec,
                output_dir,
                self.pipeline_result(),
            )

    def test_result_manifest_rejects_incoherent_summary(self) -> None:
        job_spec = self.create_spec()
        output_dir = self.root / "incoherent"
        self.write_artifacts(output_dir)
        pipeline_result = self.pipeline_result()
        pipeline_result["summary"]["model_species"] = 2

        with self.assertRaisesRegex(ValueError, "summary does not match"):
            mushroom_rebuild_contracts.create_result_manifest(
                job_spec,
                output_dir,
                pipeline_result,
            )


if __name__ == "__main__":
    unittest.main()
