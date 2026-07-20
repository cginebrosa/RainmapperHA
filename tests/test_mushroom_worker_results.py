import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_rebuild_contracts
from rainmapper_core import mushroom_rebuild_pipeline
from rainmapper_core import mushroom_worker_results


class MushroomWorkerResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.job_id = "worker_job_candidate123"
        self.input_root = self.root / "inputs"
        job_dir = self.input_root / self.job_id
        job_dir.mkdir(parents=True)
        self.job_spec = {
            "schema_version": "0.1",
            "kind": "mushroom_rebuild_job_spec",
            "job_id": self.job_id,
            "job_spec_id": "sha256:" + "a" * 64,
            "input": {"snapshot_id": "sha256:" + "b" * 64},
        }
        (job_dir / "job_spec.json").write_text(
            json.dumps(self.job_spec), encoding="utf-8"
        )
        self.outputs = self.root / "worker-job" / "candidate"
        self.outputs.mkdir(parents=True)
        (self.outputs.parent / "job_spec.json").write_text(
            json.dumps(self.job_spec), encoding="utf-8"
        )
        self._write_artifacts(self.outputs)
        pipeline_result = {
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
        self.manifest = mushroom_rebuild_contracts.create_result_manifest(
            self.job_spec,
            self.outputs,
            pipeline_result,
            created_at="2026-07-20T00:00:00+00:00",
        )
        (self.outputs / "result_manifest.json").write_text(
            json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
        )
        self.live = self.root / "live"
        self.live.mkdir()
        for relative in mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS:
            destination = self.live / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.outputs / relative, destination)

    def _write_artifacts(self, output_dir: Path) -> None:
        payloads = {
            "mushroom_gis_observation_reconstruction.json": {"result_count": 1},
            "mushroom_observations_weather_features.json": {"summary": {"observations": 1}},
            "mushroom_observation_features_v0.json": {"summary": {"observations": 1}},
            "mushroom_model_v0.json": {"summary": {"species": 1}},
        }
        for relative in mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS:
            path = output_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative in payloads:
                path.write_text(json.dumps(payloads[relative]), encoding="utf-8")
            else:
                path.write_text(relative + "\n", encoding="utf-8")

    def _finalize_candidate(self, result_root: Path) -> None:
        mushroom_worker_results.receive_result_file(
            result_root,
            self.input_root,
            job_id=self.job_id,
            logical_path="result_manifest.json",
            content=(self.outputs / "result_manifest.json").read_bytes(),
        )
        for relative in mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS:
            mushroom_worker_results.receive_result_file(
                result_root,
                self.input_root,
                job_id=self.job_id,
                logical_path=relative,
                content=(self.outputs / relative).read_bytes(),
            )
        mushroom_worker_results.finalize_candidate_result(
            result_root,
            self.input_root,
            self.live,
            job_id=self.job_id,
        )

    def test_coordinator_stages_verifies_compares_and_finalizes_candidate(self) -> None:
        result_root = self.root / "results"
        manifest_content = (self.outputs / "result_manifest.json").read_bytes()
        manifest_result = mushroom_worker_results.receive_result_file(
            result_root,
            self.input_root,
            job_id=self.job_id,
            logical_path="result_manifest.json",
            content=manifest_content,
        )
        for relative in mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS:
            mushroom_worker_results.receive_result_file(
                result_root,
                self.input_root,
                job_id=self.job_id,
                logical_path=relative,
                content=(self.outputs / relative).read_bytes(),
            )

        verification = mushroom_worker_results.finalize_candidate_result(
            result_root,
            self.input_root,
            self.live,
            job_id=self.job_id,
        )
        stored = mushroom_worker_results.load_final_candidate(result_root, self.job_id)

        self.assertEqual(manifest_result["expected_artifacts"], 9)
        self.assertEqual(verification["status"], "verified")
        self.assertEqual(verification["verified_artifacts"], 9)
        self.assertEqual(verification["comparison_status"], "equivalent")
        self.assertEqual(stored["result_manifest_id"], self.manifest["result_manifest_id"])
        self.assertFalse((result_root / f".{self.job_id}.staging").exists())

    def test_discard_candidate_removes_only_unpromoted_private_results(self) -> None:
        result_root = self.root / "discard-results"
        self._finalize_candidate(result_root)

        removed = mushroom_worker_results.discard_candidate(
            result_root,
            self.live,
            job_id=self.job_id,
        )

        self.assertEqual(removed, {"candidate": True, "staging": False})
        self.assertFalse((result_root / self.job_id).exists())
        self.assertTrue(self.live.is_dir())

    def test_discard_candidate_rejects_promoted_or_recovery_artifacts(self) -> None:
        result_root = self.root / "protected-discard-results"
        self._finalize_candidate(result_root)
        receipt = result_root / self.job_id / mushroom_worker_results.PROMOTION_RECEIPT_NAME
        receipt.write_text('{"status":"promoted"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "promoted candidate receipt"):
            mushroom_worker_results.discard_candidate(
                result_root,
                self.live,
                job_id=self.job_id,
            )
        receipt.unlink()
        recovery = self.live / ".worker-promotion-staging" / self.job_id
        recovery.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "recovery artifacts"):
            mushroom_worker_results.discard_candidate(
                result_root,
                self.live,
                job_id=self.job_id,
            )

    def test_coordinator_rejects_tampered_or_undeclared_candidate_file(self) -> None:
        result_root = self.root / "results"
        mushroom_worker_results.receive_result_file(
            result_root,
            self.input_root,
            job_id=self.job_id,
            logical_path="result_manifest.json",
            content=(self.outputs / "result_manifest.json").read_bytes(),
        )
        with self.assertRaisesRegex(ValueError, "hash|size"):
            mushroom_worker_results.receive_result_file(
                result_root,
                self.input_root,
                job_id=self.job_id,
                logical_path="mushroom_model_v0.json",
                content=b"tampered",
            )
        with self.assertRaisesRegex(ValueError, "not allowed"):
            mushroom_worker_results.receive_result_file(
                result_root,
                self.input_root,
                job_id=self.job_id,
                logical_path="private.txt",
                content=b"private",
            )

        self.assertTrue(
            mushroom_worker_results.discard_candidate_staging(result_root, self.job_id)
        )
        self.assertFalse((result_root / f".{self.job_id}.staging").exists())
        self.assertFalse(
            mushroom_worker_results.discard_candidate_staging(result_root, self.job_id)
        )

    def test_worker_uploads_manifest_then_nine_artifacts_and_completes(self) -> None:
        worker_job_dir = self.outputs.parent
        calls: list[tuple[str, bytes, dict[str, str]]] = []

        def post(url: str, content: bytes, *, headers: dict[str, str], timeout: float):
            calls.append((url, content, headers))
            if url.endswith("/result-complete"):
                return {
                    "ok": True,
                    "verification": {
                        "status": "verified",
                        "result_manifest_id": self.manifest["result_manifest_id"],
                        "verified_artifacts": 9,
                        "comparison_status": "equivalent",
                    },
                }
            return {"ok": True, "result": {"status": "received"}}

        progress: list[dict[str, object]] = []
        job = {
            "job_id": self.job_id,
            "result_endpoint": "/api/mushrooms/workers/jobs/result-file",
            "result_complete_endpoint": "/api/mushrooms/workers/jobs/result-complete",
        }
        with mock.patch.object(mushroom_worker_results, "_post_bytes", side_effect=post):
            result = mushroom_worker_results.upload_candidate_result(
                "http://rainmapper-ha-ui:8099",
                job,
                worker_job_dir,
                worker_id="worker_12345678",
                claim_token="claim-secret",
                token="coordinator-secret",
                progress_callback=progress.append,
            )

        self.assertEqual(len(calls), 11)
        self.assertIn("file=result_manifest.json", calls[0][0])
        self.assertTrue(calls[-1][0].endswith("/result-complete"))
        self.assertEqual(calls[0][2]["Authorization"], "Bearer coordinator-secret")
        self.assertEqual(result["comparison_status"], "equivalent")
        self.assertEqual(len(progress), 10)

    def test_verified_fresh_candidate_is_promoted_with_backup(self) -> None:
        result_root = self.root / "promotion-results"
        self._finalize_candidate(result_root)
        for relative in mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS:
            (self.live / relative).write_text("old live value\n", encoding="utf-8")
        valid_freshness = {
            "status": "valid",
            "snapshot_id": "sha256:" + "b" * 64,
            "dataset_fingerprint": "sha256:" + "c" * 64,
        }
        with (
            mock.patch.object(
                mushroom_worker_results.mushroom_rebuild_snapshot,
                "load_manifest",
                return_value={},
            ),
            mock.patch.object(
                mushroom_worker_results.mushroom_rebuild_snapshot,
                "verify_live_inputs",
                return_value=valid_freshness,
            ),
        ):
            promotion = mushroom_worker_results.promote_verified_candidate(
                result_root,
                self.input_root,
                self.live,
                job_id=self.job_id,
                observations_path=self.root / "observations.json",
                reference_catalogs_path=self.root / "catalogs.json",
                gis_mappings_path=self.root / "mappings.json",
                weather_data_dir=self.root / "weather",
                gis_root=self.root / "gis",
            )

        self.assertEqual(promotion["status"], "promoted")
        self.assertEqual(promotion["artifact_count"], 9)
        self.assertEqual(promotion["backup_retention_limit"], 2)
        self.assertTrue((self.live / promotion["backup_path"]).is_dir())
        for relative in mushroom_rebuild_contracts.EXPECTED_ARTIFACT_PATHS:
            self.assertEqual((self.live / relative).read_bytes(), (self.outputs / relative).read_bytes())

    def test_promotion_rebases_worker_private_paths_to_live_coordinator_paths(self) -> None:
        staged = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "rebased-staging")
        live = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "rebased-live")
        worker_root = "/var/lib/rainmapper-worker/jobs/worker_job_example/candidate"
        payloads = {
            staged.gis_reconstruction: {
                "result_count": 1,
                "qgis_points_path": f"{worker_root}/qgis/selected_observations.geojson",
                "qgis_points_host_path": f"{worker_root}/qgis/selected_observations.geojson",
                "results": [{"layers": {"mvc50": {"source": "/var/lib/rainmapper-worker/mvc.shp"}, "dem_5m": {"source": "/var/lib/rainmapper-worker/dem.tif"}}}],
            },
            staged.weather_json: {
                "summary": {"observations": 1},
                "input_paths": {"observations": f"{worker_root}/observations.json"},
                "source_files": [{"source": "aemet", "path": f"{worker_root}/Aemet_incremental.csv"}],
                "prediction_target_policy": {"catalog_path": f"{worker_root}/catalogs.json"},
                "output_paths": {"json": f"{worker_root}/weather.json"},
            },
            staged.features_json: {
                "summary": {"observations": 1},
                "input_paths": {"weather_features": f"{worker_root}/weather.json"},
                "prediction_target_policy": {"catalog_path": f"{worker_root}/catalogs.json"},
                "output_paths": {"json": f"{worker_root}/features.json"},
            },
            staged.model_json: {
                "summary": {"species": 1},
                "input_paths": {"observation_features_v0": f"{worker_root}/features.json"},
                "prediction_target_policy": {"catalog_path": f"{worker_root}/catalogs.json"},
                "output_paths": {"json": f"{worker_root}/model.json"},
            },
        }
        for path, payload in payloads.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")
        observations = self.root / "authoritative/mushroom_observations.json"
        catalogs = self.root / "authoritative/mushroom_reference_catalogs.json"
        weather = self.root / "authoritative/weather"
        gis = self.root / "authoritative/gis"

        changed = mushroom_worker_results._rebase_promoted_metadata(
            staged,
            live,
            observations_path=observations,
            reference_catalogs_path=catalogs,
            weather_data_dir=weather,
            gis_root=gis,
        )

        rebased_gis = json.loads(staged.gis_reconstruction.read_text(encoding="utf-8"))
        rebased_weather = json.loads(staged.weather_json.read_text(encoding="utf-8"))
        rebased_features = json.loads(staged.features_json.read_text(encoding="utf-8"))
        rebased_model = json.loads(staged.model_json.read_text(encoding="utf-8"))
        self.assertEqual(len(changed), 4)
        self.assertNotIn("qgis_points_path", rebased_gis)
        self.assertNotIn("qgis_points_host_path", rebased_gis)
        self.assertEqual(
            rebased_gis["results"][0]["layers"]["mvc50"]["source"],
            str(mushroom_worker_results.mushroom_gis_lab.vector_layers(gis.resolve())[0].path.resolve()),
        )
        self.assertEqual(rebased_weather["input_paths"]["observations"], str(observations.resolve()))
        self.assertEqual(
            rebased_weather["source_files"][0]["path"],
            str((weather / "Aemet_incremental.csv").resolve()),
        )
        self.assertEqual(rebased_features["input_paths"]["weather_features"], str(live.weather_json))
        self.assertEqual(rebased_model["output_paths"]["json"], str(live.model_json))
        for payload in (rebased_weather, rebased_features, rebased_model):
            self.assertNotIn("/var/lib/rainmapper-worker", json.dumps(payload))

    def test_promotion_backup_retention_keeps_only_two_newest_known_jobs(self) -> None:
        backup_root = self.live / ".worker-promotion-backups"
        backup_root.mkdir()
        jobs = [
            "worker_job_retention01",
            "worker_job_retention02",
            "worker_job_retention03",
        ]
        for index, job_id in enumerate(jobs, start=1):
            path = backup_root / job_id
            path.mkdir()
            (path / "marker").write_text(job_id, encoding="utf-8")
            os.utime(path, ns=(index, index))
        unrelated = backup_root / "manual-backup"
        unrelated.mkdir()

        removed = mushroom_worker_results.prune_promotion_backups(
            self.live,
            current_job_id=jobs[-1],
        )

        self.assertEqual(removed, [jobs[0]])
        self.assertFalse((backup_root / jobs[0]).exists())
        self.assertTrue((backup_root / jobs[1]).is_dir())
        self.assertTrue((backup_root / jobs[2]).is_dir())
        self.assertTrue(unrelated.is_dir())

    def test_promotion_rejects_tampered_candidate_and_stale_inputs(self) -> None:
        result_root = self.root / "rejected-promotion-results"
        self._finalize_candidate(result_root)
        candidate_model = result_root / self.job_id / "mushroom_model_v0.json"
        candidate_model.write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed after verification"):
            mushroom_worker_results.promote_verified_candidate(
                result_root,
                self.input_root,
                self.live,
                job_id=self.job_id,
                observations_path=self.root / "observations.json",
                reference_catalogs_path=self.root / "catalogs.json",
                gis_mappings_path=self.root / "mappings.json",
                weather_data_dir=self.root / "weather",
                gis_root=self.root / "gis",
            )

        candidate_model.write_bytes((self.outputs / "mushroom_model_v0.json").read_bytes())
        with (
            mock.patch.object(
                mushroom_worker_results.mushroom_rebuild_snapshot,
                "load_manifest",
                return_value={},
            ),
            mock.patch.object(
                mushroom_worker_results.mushroom_rebuild_snapshot,
                "verify_live_inputs",
                return_value={"status": "stale", "errors": ["observations changed"]},
            ),
        ):
            with self.assertRaisesRegex(ValueError, "inputs are stale"):
                mushroom_worker_results.promote_verified_candidate(
                    result_root,
                    self.input_root,
                    self.live,
                    job_id=self.job_id,
                    observations_path=self.root / "observations.json",
                    reference_catalogs_path=self.root / "catalogs.json",
                    gis_mappings_path=self.root / "mappings.json",
                    weather_data_dir=self.root / "weather",
                    gis_root=self.root / "gis",
                )

    def test_partial_candidate_merge_preserves_out_of_scope_rows_and_models(self) -> None:
        live_outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "partial-live")
        staged_outputs = mushroom_rebuild_pipeline.RebuildOutputPaths.under(self.root / "partial-staged")
        candidate = self.root / "partial-candidate"
        candidate.mkdir()

        def write_json(path: Path, payload: dict[str, object]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")

        live_rows = [
            {"observation_id": "obs_a", "species_id": "species_a", "marker": "old-a"},
            {"observation_id": "obs_b", "species_id": "species_b", "marker": "keep-b"},
        ]
        candidate_rows = [
            {"observation_id": "obs_a", "species_id": "species_a", "marker": "new-a"},
            {"observation_id": "obs_b", "species_id": "species_b", "marker": "wrong-b"},
        ]
        write_json(
            live_outputs.gis_reconstruction,
            {"generated_at": "old", "results": live_rows, "result_count": 2},
        )
        write_json(
            candidate / "mushroom_gis_observation_reconstruction.json",
            {"generated_at": "new", "results": candidate_rows, "result_count": 2},
        )
        weather_live = [
            {**row, "weather_station_code": "ST", "data_gaps": []}
            for row in live_rows
        ]
        weather_candidate = [
            {**row, "weather_station_code": "ST", "data_gaps": []}
            for row in candidate_rows
        ]
        write_json(live_outputs.weather_json, {"rows": weather_live, "summary": {"observations": 2}})
        write_json(
            candidate / "mushroom_observations_weather_features.json",
            {"generated_at": "new", "rows": weather_candidate, "summary": {"observations": 2}},
        )
        feature_live = [
            {**row, "weather_gaps": [], "gis_gaps": [], "feature_gaps": []}
            for row in live_rows
        ]
        feature_candidate = [
            {**row, "weather_gaps": [], "gis_gaps": [], "feature_gaps": []}
            for row in candidate_rows
        ]
        write_json(live_outputs.features_json, {"rows": feature_live, "summary": {"observations": 2}})
        write_json(
            candidate / "mushroom_observation_features_v0.json",
            {"generated_at": "new", "rows": feature_candidate, "summary": {"observations": 2}},
        )
        live_models = [
            {"species_id": "species_a", "marker": "old-a", "observation_count": 1, "favorable_count": 1, "unfavorable_count": 0},
            {"species_id": "species_b", "marker": "keep-b", "observation_count": 1, "favorable_count": 0, "unfavorable_count": 1},
        ]
        candidate_models = [
            {"species_id": "species_a", "marker": "new-a", "observation_count": 1, "favorable_count": 0, "unfavorable_count": 1},
            {"species_id": "species_b", "marker": "wrong-b", "observation_count": 1, "favorable_count": 1, "unfavorable_count": 0},
        ]
        write_json(live_outputs.model_json, {"species_models": live_models, "summary": {"species": 2}})
        write_json(
            candidate / "mushroom_model_v0.json",
            {"generated_at": "new", "species_models": candidate_models, "summary": {"species": 2}},
        )
        for path in (
            live_outputs.weather_csv,
            live_outputs.weather_report,
            live_outputs.features_csv,
            live_outputs.features_report,
            live_outputs.model_report,
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("old\n", encoding="utf-8")

        result = mushroom_worker_results._merge_partial_candidate_outputs(
            candidate,
            live_outputs,
            staged_outputs,
            {
                "scope": {
                    "reconstruction_scope": "species",
                    "selected_observation_ids": ["obs_a"],
                    "pending_species_ids": ["species_a"],
                }
            },
        )

        merged_gis = json.loads(staged_outputs.gis_reconstruction.read_text(encoding="utf-8"))
        merged_features = json.loads(staged_outputs.features_json.read_text(encoding="utf-8"))
        merged_model = json.loads(staged_outputs.model_json.read_text(encoding="utf-8"))
        self.assertEqual([row["marker"] for row in merged_gis["results"]], ["new-a", "keep-b"])
        self.assertEqual([row["marker"] for row in merged_features["rows"]], ["new-a", "keep-b"])
        self.assertEqual(
            [row["marker"] for row in merged_model["species_models"]],
            ["new-a", "keep-b"],
        )
        self.assertEqual(0, merged_model["summary"]["favorable_observations"])
        self.assertEqual(2, merged_model["summary"]["species"])
        self.assertEqual({"selected_observations": 1, "updated_species": 1, "model_species": 2}, result)


if __name__ == "__main__":
    unittest.main()
