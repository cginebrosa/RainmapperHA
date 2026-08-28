import tempfile
import unittest
import json
from datetime import UTC, datetime
from pathlib import Path

from rainmapper_core import mushroom_worker_jobs


class MushroomWorkerJobsTests(unittest.TestCase):
    def predictor_request(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "kind": "rainmapper_mushroom_predictor_request",
            "view": "week",
            "species_id": "boletus",
            "area_id": "",
            "target_date": "2026-08-10",
            "trained_species_ids": ["boletus"],
        }

    def predictor_response(self, *, padding: int = 0) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "kind": "rainmapper_mushroom_predictor_response",
            "request": self.predictor_request(),
            "data": {"padding": "x" * padding},
            "metrics": {},
        }

    def test_predictor_result_is_externalized_from_hot_queue_and_hydrated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            mushroom_worker_jobs.create_predictor_job(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                request=self.predictor_request(),
                runtime_manifest={
                    "schema_version": "1.0",
                    "kind": "rainmapper_mushroom_predictor_runtime",
                    "fingerprint": "sha256:" + "a" * 64,
                    "files": [
                        {
                            "path": "models/model.joblib",
                            "sha256": "sha256:" + "b" * 64,
                            "size_bytes": 0,
                        }
                    ],
                },
                job_id="worker_job_predictresult",
            )
            mushroom_worker_jobs.claim_next(
                path, worker_id="worker_aaaaaaaa", claim_token="claim-secret"
            )
            mushroom_worker_jobs.start_job(
                path,
                job_id="worker_job_predictresult",
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            mushroom_worker_jobs.finish_job(
                path,
                job_id="worker_job_predictresult",
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
                status="complete",
                result={"response": self.predictor_response(padding=2 * 1024 * 1024), "cold": False},
            )

            queue_bytes = path.stat().st_size
            stored = json.loads(path.read_text(encoding="utf-8"))["jobs"][0]
            hydrated = mushroom_worker_jobs.get_job(
                path, job_id="worker_job_predictresult"
            )

        self.assertLess(queue_bytes, 100_000)
        self.assertNotIn("response", stored["result"])
        self.assertIn("predictor_result_ref", stored)
        self.assertEqual(len(hydrated["result"]["response"]["data"]["padding"]), 2 * 1024 * 1024)

    def test_exact_predictor_result_can_be_reused_only_for_same_worker_request_and_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            fingerprint = "sha256:" + "a" * 64
            mushroom_worker_jobs.create_predictor_job(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                request=self.predictor_request(),
                runtime_manifest={
                    "schema_version": "1.0",
                    "kind": "rainmapper_mushroom_predictor_runtime",
                    "fingerprint": fingerprint,
                    "files": [
                        {
                            "path": "models/model.joblib",
                            "sha256": "sha256:" + "b" * 64,
                            "size_bytes": 0,
                        }
                    ],
                },
                job_id="worker_job_reusable123",
            )
            mushroom_worker_jobs.claim_next(
                path, worker_id="worker_aaaaaaaa", claim_token="claim-secret"
            )
            mushroom_worker_jobs.start_job(
                path,
                job_id="worker_job_reusable123",
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            mushroom_worker_jobs.finish_job(
                path,
                job_id="worker_job_reusable123",
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
                status="complete",
                result={"response": self.predictor_response(), "cold": False},
            )

            reusable = mushroom_worker_jobs.find_reusable_predictor_job(
                path,
                worker_id="worker_aaaaaaaa",
                request=self.predictor_request(),
                runtime_fingerprint=fingerprint,
            )
            wrong_worker = mushroom_worker_jobs.find_reusable_predictor_job(
                path,
                worker_id="worker_bbbbbbbb",
                request=self.predictor_request(),
                runtime_fingerprint=fingerprint,
            )
            wrong_runtime = mushroom_worker_jobs.find_reusable_predictor_job(
                path,
                worker_id="worker_aaaaaaaa",
                request=self.predictor_request(),
                runtime_fingerprint="sha256:" + "c" * 64,
            )
            changed_request = {
                **self.predictor_request(),
                "target_date": "2026-08-11",
            }
            wrong_request = mushroom_worker_jobs.find_reusable_predictor_job(
                path,
                worker_id="worker_aaaaaaaa",
                request=changed_request,
                runtime_fingerprint=fingerprint,
            )

        self.assertEqual(reusable["job_id"], "worker_job_reusable123")
        self.assertIsInstance(reusable["result"]["response"], dict)
        self.assertIsNone(wrong_worker)
        self.assertIsNone(wrong_runtime)
        self.assertIsNone(wrong_request)

    def test_corrupt_predictor_result_is_not_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            fingerprint = "sha256:" + "a" * 64
            job = {
                "job_id": "worker_job_corrupt123",
                "job_type": mushroom_worker_jobs.JOB_TYPE_PREDICTOR,
                "target_worker_id": "worker_aaaaaaaa",
                "status": "complete",
                "created_at": "2026-08-28T01:00:00+00:00",
                "finished_at": "2026-08-28T01:01:00+00:00",
                "predictor_request": self.predictor_request(),
                "runtime_manifest": {"fingerprint": fingerprint},
                "result": {"response": self.predictor_response()},
            }
            mushroom_worker_jobs._write_atomic(
                path,
                {"schema_version": mushroom_worker_jobs.SCHEMA_VERSION, "jobs": [job]},
            )
            result_path = (
                path.parent
                / mushroom_worker_jobs.PREDICTOR_RESULTS_DIRNAME
                / "worker_job_corrupt123.json"
            )
            result_path.write_text("{}", encoding="utf-8")

            reusable = mushroom_worker_jobs.find_reusable_predictor_job(
                path,
                worker_id="worker_aaaaaaaa",
                request=self.predictor_request(),
                runtime_fingerprint=fingerprint,
            )

        self.assertIsNone(reusable)

    def test_predictor_result_limit_allows_growth_beyond_one_mib(self) -> None:
        response = self.predictor_response(padding=2 * 1024 * 1024)

        normalized = mushroom_worker_jobs._normalized_result(
            {"job_type": mushroom_worker_jobs.JOB_TYPE_PREDICTOR},
            {"response": response, "cold": False},
        )

        self.assertGreater(len(json.dumps(normalized).encode()), 1024 * 1024)

    def test_predictor_result_preserves_runtime_reuse_telemetry(self) -> None:
        normalized = mushroom_worker_jobs._normalized_result(
            {"job_type": mushroom_worker_jobs.JOB_TYPE_PREDICTOR},
            {
                "response": self.predictor_response(),
                "cold": False,
                "runtime_cache_status": "reused",
                "runtime_transferred_size_bytes": 0,
                "runtime_verification_status": "receipt",
                "runtime_hashed_file_count": 0,
                "runtime_reused_file_count": 713,
                "runtime_fetched_file_count": 0,
                "runtime_sync_seconds": 0.004321,
            },
        )

        self.assertEqual(normalized["runtime_verification_status"], "receipt")
        self.assertEqual(normalized["runtime_hashed_file_count"], 0)
        self.assertEqual(normalized["runtime_reused_file_count"], 713)
        self.assertEqual(normalized["runtime_fetched_file_count"], 0)
        self.assertEqual(normalized["runtime_sync_seconds"], 0.004321)

    def test_predictor_result_limit_is_exactly_sixty_four_mib(self) -> None:
        self.assertEqual(
            mushroom_worker_jobs.PREDICTOR_RESULT_MAX_BYTES,
            64 * 1024 * 1024,
        )
        base = self.predictor_response()
        base_size = len(json.dumps(base, ensure_ascii=False).encode("utf-8"))
        at_limit = self.predictor_response(
            padding=mushroom_worker_jobs.PREDICTOR_RESULT_MAX_BYTES - base_size
        )
        self.assertEqual(
            mushroom_worker_jobs.validate_predictor_result_size(at_limit),
            mushroom_worker_jobs.PREDICTOR_RESULT_MAX_BYTES,
        )
        response = self.predictor_response(
            padding=mushroom_worker_jobs.PREDICTOR_RESULT_MAX_BYTES - base_size + 1
        )

        with self.assertRaisesRegex(ValueError, "exceeds 64 MiB"):
            mushroom_worker_jobs._normalized_result(
                {"job_type": mushroom_worker_jobs.JOB_TYPE_PREDICTOR},
                {"response": response, "cold": False},
            )

    def test_predictor_heavy_result_expiry_keeps_newest_ten_or_last_day(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            jobs = []
            for day in range(1, 13):
                job_id = f"worker_job_expiry{day:02d}"
                jobs.append(
                    {
                        "job_id": job_id,
                        "job_type": mushroom_worker_jobs.JOB_TYPE_PREDICTOR,
                        "status": "complete",
                        "created_at": f"2026-08-{day:02d}T10:00:00+00:00",
                        "finished_at": f"2026-08-{day:02d}T10:01:00+00:00",
                        "result": {"response": self.predictor_response(padding=day)},
                    }
                )
            jobs.append(
                {
                    "job_id": "worker_job_expiryrecent",
                    "job_type": mushroom_worker_jobs.JOB_TYPE_PREDICTOR,
                    "status": "complete",
                    "created_at": "2026-08-23T08:00:00+00:00",
                    "finished_at": "2026-08-23T08:01:00+00:00",
                    "result": {"response": self.predictor_response(padding=20)},
                }
            )
            mushroom_worker_jobs._write_atomic(
                path,
                {"schema_version": mushroom_worker_jobs.SCHEMA_VERSION, "jobs": jobs},
            )
            before_queue = path.read_bytes()
            result_dir = path.parent / mushroom_worker_jobs.PREDICTOR_RESULTS_DIRNAME
            before_files = sorted(child.name for child in result_dir.iterdir())

            plan = mushroom_worker_jobs.plan_predictor_result_expiration(
                path,
                now=datetime(2026, 8, 23, 12, tzinfo=UTC),
            )

            self.assertEqual(
                [entry["job_id"] for entry in plan["planned"]],
                ["worker_job_expiry01", "worker_job_expiry02", "worker_job_expiry03"],
            )
            self.assertEqual(plan["errors"], [])
            self.assertEqual(path.read_bytes(), before_queue)
            self.assertEqual(sorted(child.name for child in result_dir.iterdir()), before_files)

            applied = mushroom_worker_jobs.expire_predictor_results(
                path,
                plan,
                expired_at=datetime(2026, 8, 23, 12, tzinfo=UTC),
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
            expired = {
                job["job_id"]: job
                for job in stored["jobs"]
                if job.get("predictor_result_detail", {}).get("status") == "expired"
            }

        self.assertEqual(applied["errors"], [])
        self.assertEqual(set(applied["expired"]), set(expired))
        self.assertEqual(len(expired), 3)
        self.assertNotIn("predictor_result_ref", expired["worker_job_expiry01"])
        self.assertIn("result", expired["worker_job_expiry01"])

    def test_predictor_claim_uses_interactive_prediction_message(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            mushroom_worker_jobs.create_predictor_job(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                request={
                    "schema_version": "1.0",
                    "kind": "rainmapper_mushroom_predictor_request",
                    "view": "recommender",
                    "species_id": "boletus",
                    "area_id": "",
                    "target_date": "2026-08-09",
                    "trained_species_ids": ["boletus"],
                },
                runtime_manifest={
                    "schema_version": "1.0",
                    "kind": "rainmapper_mushroom_predictor_runtime",
                    "fingerprint": "sha256:" + "a" * 64,
                    "files": [
                        {
                            "path": "models/model.joblib",
                            "sha256": "sha256:" + "b" * 64,
                            "size_bytes": 0,
                        }
                    ],
                },
                job_id="worker_job_predict123",
            )

            claimed = mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            started = mushroom_worker_jobs.start_job(
                path,
                job_id="worker_job_predict123",
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )

        self.assertIsNotNone(claimed)
        self.assertEqual(
            claimed["message"],
            "The assigned worker claimed the interactive prediction.",
        )
        self.assertEqual(started["phase"], "Predictor working")
        self.assertEqual(
            started["message"],
            "The prediction was launched. Please wait for the result.",
        )

    def test_discard_candidate_waits_for_the_assigned_worker_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            job_id = "worker_job_discard123"
            created = mushroom_worker_jobs.create_candidate_rebuild(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle={
                    "job_id": job_id,
                    "job_spec_id": "sha256:" + "a" * 64,
                    "snapshot_id": "sha256:" + "b" * 64,
                    "input_file_count": 7,
                    "input_size_bytes": 1234,
                },
                job_id=job_id,
            )
            with self.assertRaisesRegex(ValueError, "after the job has finished"):
                mushroom_worker_jobs.request_candidate_discard(path, job_id=job_id)
            mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            mushroom_worker_jobs.start_job(
                path,
                job_id=job_id,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            mushroom_worker_jobs.finish_job(
                path,
                job_id=job_id,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
                status="failed",
                error="expected test failure",
            )

            discarded = mushroom_worker_jobs.request_candidate_discard(path, job_id=job_id)

            self.assertEqual(discarded["discard_status"], "requested")
            self.assertEqual(
                mushroom_worker_jobs.pending_candidate_discards(
                    path,
                    worker_id="worker_aaaaaaaa",
                ),
                [job_id],
            )
            self.assertEqual(
                mushroom_worker_jobs.acknowledge_candidate_discards(
                    path,
                    worker_id="worker_bbbbbbbb",
                    job_ids=[job_id],
                ),
                [],
            )
            self.assertEqual(
                mushroom_worker_jobs.acknowledge_candidate_discards(
                    path,
                    worker_id="worker_aaaaaaaa",
                    job_ids=[job_id],
                ),
                [job_id],
            )
            retained = mushroom_worker_jobs.get_job(path, job_id=created["job_id"])
            self.assertEqual(retained["discard_status"], "acknowledged")
            self.assertEqual(retained["phase"], "Candidate discarded")
            self.assertEqual(
                mushroom_worker_jobs.pending_candidate_discards(
                    path,
                    worker_id="worker_aaaaaaaa",
                ),
                [],
            )

    def test_terminal_worker_cleanup_is_acknowledged_without_removing_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            job_id = "worker_job_cleanup123"
            mushroom_worker_jobs.create_snapshot_transport_probe(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle={
                    "job_id": job_id,
                    "job_spec_id": "sha256:" + "a" * 64,
                    "snapshot_id": "sha256:" + "b" * 64,
                    "input_file_count": 4,
                    "input_size_bytes": 1234,
                },
                job_id=job_id,
            )
            mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            mushroom_worker_jobs.start_job(
                path,
                job_id=job_id,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            mushroom_worker_jobs.finish_job(
                path,
                job_id=job_id,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
                status="complete",
            )

            self.assertEqual(
                mushroom_worker_jobs.pending_worker_job_cleanups(
                    path,
                    worker_id="worker_aaaaaaaa",
                ),
                [job_id],
            )
            self.assertEqual(
                mushroom_worker_jobs.acknowledge_worker_job_cleanups(
                    path,
                    worker_id="worker_aaaaaaaa",
                    job_ids=[job_id],
                ),
                [job_id],
            )
            retained = mushroom_worker_jobs.get_job(path, job_id=job_id)
            self.assertEqual(retained["worker_cleanup_status"], "complete")
            self.assertEqual(
                mushroom_worker_jobs.pending_worker_job_cleanups(
                    path,
                    worker_id="worker_aaaaaaaa",
                ),
                [],
            )

    def test_candidate_rebuild_rejects_duplicate_active_full_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"

            def bundle(job_id: str) -> dict[str, object]:
                return {
                    "job_id": job_id,
                    "job_spec_id": "sha256:" + "a" * 64,
                    "snapshot_id": "sha256:" + "b" * 64,
                    "input_file_count": 7,
                    "input_size_bytes": 1234,
                }

            first = mushroom_worker_jobs.create_candidate_rebuild(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle=bundle("worker_job_full_aaaa"),
                job_id="worker_job_full_aaaa",
                profile_keys=["altitude_v2/common_idw", "biology_v4/extended_weather"],
            )
            with self.assertRaises(mushroom_worker_jobs.DuplicateActiveWorkError):
                mushroom_worker_jobs.create_candidate_rebuild(
                    path,
                    worker_id="worker_bbbbbbbb",
                    worker_display_name="Worker B",
                    input_bundle=bundle("worker_job_full_bbbb"),
                    job_id="worker_job_full_bbbb",
                )
            self.assertEqual("all", first["reconstruction_scope"])
            self.assertTrue(first["full_update"])
            self.assertTrue(first["promotion_eligible"])
            self.assertEqual(
                first["profile_keys"],
                ["altitude_v2/common_idw", "biology_v4/extended_weather"],
            )

    def test_candidate_preparation_is_visible_cancelable_and_not_claimable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            job_id = "worker_job_preparing123"
            created = mushroom_worker_jobs.create_candidate_preparation(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                job_id=job_id,
                profile_keys=["biology_v4/extended_weather"],
            )

            self.assertEqual(created["status"], "preparing")
            self.assertEqual(created["phase"], "Reconciling GIS and SoilGrids")
            self.assertIsNone(
                mushroom_worker_jobs.claim_next(
                    path,
                    worker_id="worker_aaaaaaaa",
                    claim_token="claim-secret",
                )
            )
            updated = mushroom_worker_jobs.update_candidate_preparation(
                path,
                job_id=job_id,
                phase="Reconciling GIS and SoilGrids",
                message="2/4 micro-areas",
                overall_percent=5,
                telemetry={"processed_micro_areas": 2},
            )
            self.assertEqual(updated["preparation_telemetry"]["processed_micro_areas"], 2)
            cancelled = mushroom_worker_jobs.request_cancel(path, job_id=job_id)
            self.assertEqual(cancelled["status"], "cancelled")
            self.assertTrue(
                mushroom_worker_jobs.candidate_preparation_cancelled(
                    path, job_id=job_id
                )
            )

    def test_candidate_preparation_becomes_claimable_only_after_bundle_is_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            job_id = "worker_job_prepared1234"
            mushroom_worker_jobs.create_candidate_preparation(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                job_id=job_id,
            )
            queued = mushroom_worker_jobs.finalize_candidate_preparation(
                path,
                job_id=job_id,
                input_bundle={
                    "job_id": job_id,
                    "job_spec_id": "sha256:" + "a" * 64,
                    "snapshot_id": "sha256:" + "b" * 64,
                    "input_file_count": 7,
                    "input_size_bytes": 1234,
                },
                telemetry={"duration_ms": 12, "warnings": []},
            )

            self.assertEqual(queued["status"], "queued")
            self.assertEqual(queued["preparation_telemetry"]["duration_ms"], 12)
            claimed = mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            self.assertEqual(claimed["job_id"], job_id)

    def test_candidate_rebuild_requires_claim_and_trusted_result_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            input_bundle = {
                "schema_version": "0.1",
                "kind": "rainmapper_worker_input_bundle",
                "job_id": "worker_job_candidate123",
                "job_spec_id": "sha256:" + "a" * 64,
                "snapshot_id": "sha256:" + "b" * 64,
                "input_file_count": 7,
                "input_size_bytes": 1234,
            }
            created = mushroom_worker_jobs.create_candidate_rebuild(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle=input_bundle,
                job_id="worker_job_candidate123",
            )
            claimed = mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            mushroom_worker_jobs.start_job(
                path,
                job_id=created["job_id"],
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            authorized = mushroom_worker_jobs.authorize_result_upload(
                path,
                job_id=created["job_id"],
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            finished = mushroom_worker_jobs.finish_job(
                path,
                job_id=created["job_id"],
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
                status="complete",
                result={
                    "verification_status": "verified",
                    "snapshot_id": input_bundle["snapshot_id"],
                    "job_spec_id": input_bundle["job_spec_id"],
                    "input_file_count": 7,
                    "input_size_bytes": 1234,
                    "dataset_fingerprint": "sha256:" + "c" * 64,
                    "result_manifest_id": "sha256:" + "d" * 64,
                    "verified_artifacts": 9,
                    "comparison_status": "equivalent",
                },
            )
            promoting = mushroom_worker_jobs.begin_candidate_promotion(
                path,
                job_id=created["job_id"],
            )
            progressing = mushroom_worker_jobs.update_candidate_promotion_progress(
                path,
                job_id=created["job_id"],
                percent=64,
                phase="Validating live inputs (8/12)",
                message="Checking GIS freshness.",
            )
            promoted = mushroom_worker_jobs.finish_candidate_promotion(
                path,
                job_id=created["job_id"],
                promoted=True,
                result={"artifact_count": 9},
            )

        self.assertEqual(claimed["job_type"], "worker_candidate_rebuild")
        self.assertEqual(authorized["status"], "running")
        self.assertEqual(finished["phase"], "Candidate result verified")
        self.assertEqual(finished["result"]["comparison_status"], "equivalent")
        self.assertEqual(promoting["promotion_status"], "promoting")
        self.assertEqual(progressing["promotion_percent"], 64)
        self.assertEqual(progressing["phase"], "Validating live inputs (8/12)")
        self.assertEqual(promoted["promotion_status"], "promoted")
        self.assertEqual(promoted["promotion_percent"], 100)
        self.assertEqual(promoted["promotion_result"]["artifact_count"], 9)

    def test_snapshot_transport_job_requires_exact_claim_for_input_download(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            input_bundle = {
                "schema_version": "0.1",
                "kind": "rainmapper_worker_input_bundle",
                "job_id": "worker_job_transport123",
                "job_spec_id": "sha256:" + "a" * 64,
                "snapshot_id": "sha256:" + "b" * 64,
                "input_file_count": 4,
                "input_size_bytes": 1234,
            }
            created = mushroom_worker_jobs.create_snapshot_transport_probe(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle=input_bundle,
                job_id="worker_job_transport123",
            )
            claimed = mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )

            authorized = mushroom_worker_jobs.authorize_input_download(
                path,
                job_id=created["job_id"],
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            with self.assertRaisesRegex(ValueError, "no longer valid"):
                mushroom_worker_jobs.authorize_input_download(
                    path,
                    job_id=created["job_id"],
                    worker_id="worker_aaaaaaaa",
                    claim_token="wrong-secret",
                )
            mushroom_worker_jobs.start_job(
                path,
                job_id=created["job_id"],
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
            )
            completed = mushroom_worker_jobs.finish_job(
                path,
                job_id=created["job_id"],
                worker_id="worker_aaaaaaaa",
                claim_token="claim-secret",
                status="complete",
                result={
                    "verification_status": "verified",
                    "snapshot_id": input_bundle["snapshot_id"],
                    "job_spec_id": input_bundle["job_spec_id"],
                    "input_file_count": input_bundle["input_file_count"],
                    "input_size_bytes": input_bundle["input_size_bytes"],
                    "dataset_cache_status": "reused",
                    "dataset_transferred_size_bytes": 0,
                },
            )

        self.assertEqual(claimed["input_bundle"]["endpoint"], "/api/mushrooms/workers/jobs/input")
        self.assertEqual(
            claimed["input_bundle"]["dataset_endpoint"],
            "/api/mushrooms/workers/jobs/dataset",
        )
        self.assertEqual(authorized["job_type"], "worker_snapshot_transport_probe")
        self.assertEqual(completed["result"]["dataset_cache_status"], "reused")
        self.assertEqual(completed["result"]["dataset_transferred_size_bytes"], 0)

    def test_equivalent_active_work_is_globally_unique_but_distinct_work_can_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.json"
            first = mushroom_worker_jobs.create_claim_probe(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                job_id="worker_job_aaaaaaaa",
                work_key="rebuild:v0:snapshot-a:all",
            )
            with self.assertRaisesRegex(
                mushroom_worker_jobs.DuplicateActiveWorkError,
                "already active",
            ):
                mushroom_worker_jobs.create_claim_probe(
                    path,
                    worker_id="worker_bbbbbbbb",
                    worker_display_name="Worker B",
                    job_id="worker_job_bbbbbbbb",
                    work_key="rebuild:v0:snapshot-a:all",
                )
            distinct = mushroom_worker_jobs.create_claim_probe(
                path,
                worker_id="worker_bbbbbbbb",
                worker_display_name="Worker B",
                job_id="worker_job_cccccccc",
                work_key="rebuild:v0:snapshot-a:species:amanita_caesarea",
            )
            mushroom_worker_jobs.request_cancel(path, job_id=first["job_id"])
            replacement = mushroom_worker_jobs.create_claim_probe(
                path,
                worker_id="worker_bbbbbbbb",
                worker_display_name="Worker B",
                job_id="worker_job_dddddddd",
                work_key="rebuild:v0:snapshot-a:all",
            )

        self.assertEqual(distinct["status"], "queued")
        self.assertEqual(replacement["status"], "queued")

    def test_probe_is_persisted_and_only_target_worker_claims_it_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            created = mushroom_worker_jobs.create_claim_probe(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                job_id="worker_job_12345678",
                created_at="2026-07-19T12:00:00+00:00",
            )

            self.assertEqual(created["status"], "queued")
            self.assertIsNone(mushroom_worker_jobs.claim_next(path, worker_id="worker_bbbbbbbb"))
            claimed = mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claimed_at="2026-07-19T12:00:05+00:00",
                claim_token="claim-token-a",
            )
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["job_id"], "worker_job_12345678")
            self.assertEqual(claimed["status"], "claimed")
            self.assertIsNone(
                mushroom_worker_jobs.claim_next(
                    path,
                    worker_id="worker_aaaaaaaa",
                    claimed_at="2026-07-19T12:00:06+00:00",
                )
            )

            recent = mushroom_worker_jobs.recent_jobs(path)

        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["target_display_name"], "Worker A")
        self.assertEqual(recent[0]["overall_percent"], 5)

    def test_claim_can_be_reassigned_before_start_and_old_claim_is_revoked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            mushroom_worker_jobs.create_claim_probe(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                job_id="worker_job_12345678",
            )
            mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claimed_at="2026-07-19T12:00:00+00:00",
                claim_token="old-claim-token",
            )
            reassigned = mushroom_worker_jobs.reassign_job(
                path,
                job_id="worker_job_12345678",
                worker_id="worker_bbbbbbbb",
                worker_display_name="Worker B",
                reassigned_at="2026-07-19T12:00:01+00:00",
            )

            with self.assertRaisesRegex(ValueError, "different worker|no longer valid"):
                mushroom_worker_jobs.start_job(
                    path,
                    job_id="worker_job_12345678",
                    worker_id="worker_aaaaaaaa",
                    claim_token="old-claim-token",
                    started_at="2026-07-19T12:00:02+00:00",
                )
            claimed_by_b = mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_bbbbbbbb",
                claimed_at="2026-07-19T12:00:03+00:00",
                claim_token="new-claim-token",
            )

        self.assertEqual(reassigned["status"], "queued")
        self.assertEqual(reassigned["assignment_revision"], 2)
        self.assertEqual(claimed_by_b["target_display_name"], "Worker B")

    def test_queued_or_claimed_job_cancels_immediately(self) -> None:
        for claim_first in (False, True):
            with self.subTest(claim_first=claim_first), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "worker_jobs.json"
                mushroom_worker_jobs.create_claim_probe(
                    path,
                    worker_id="worker_aaaaaaaa",
                    worker_display_name="Worker A",
                    job_id="worker_job_12345678",
                )
                if claim_first:
                    mushroom_worker_jobs.claim_next(
                        path,
                        worker_id="worker_aaaaaaaa",
                        claim_token="claim-token",
                    )
                cancelled = mushroom_worker_jobs.request_cancel(
                    path,
                    job_id="worker_job_12345678",
                    requested_at="2026-07-19T12:00:05+00:00",
                )

            self.assertEqual(cancelled["status"], "cancelled")
            self.assertEqual(cancelled["claim_token"], "")

    def test_running_job_cooperatively_cancels_and_cannot_be_reassigned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            mushroom_worker_jobs.create_claim_probe(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                job_id="worker_job_12345678",
            )
            mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claimed_at="2026-07-19T12:00:00+00:00",
                claim_token="claim-token",
            )
            started = mushroom_worker_jobs.start_job(
                path,
                job_id="worker_job_12345678",
                worker_id="worker_aaaaaaaa",
                claim_token="claim-token",
                started_at="2026-07-19T12:00:01+00:00",
            )
            requested = mushroom_worker_jobs.request_cancel(
                path,
                job_id="worker_job_12345678",
                requested_at="2026-07-19T12:00:02+00:00",
            )
            forced = mushroom_worker_jobs.request_cancel(
                path,
                job_id="worker_job_12345678",
                requested_at="2026-07-19T12:00:03+00:00",
                force=True,
            )
            control = mushroom_worker_jobs.poll_job(
                path,
                job_id="worker_job_12345678",
                worker_id="worker_aaaaaaaa",
                claim_token="claim-token",
                checked_at="2026-07-19T12:00:03+00:00",
            )
            with self.assertRaisesRegex(ValueError, "not started"):
                mushroom_worker_jobs.reassign_job(
                    path,
                    job_id="worker_job_12345678",
                    worker_id="worker_bbbbbbbb",
                    worker_display_name="Worker B",
                )
            cancelled = mushroom_worker_jobs.finish_job(
                path,
                job_id="worker_job_12345678",
                worker_id="worker_aaaaaaaa",
                claim_token="claim-token",
                status="cancelled",
                finished_at="2026-07-19T12:00:04+00:00",
            )

        self.assertEqual(started["status"], "running")
        self.assertEqual(requested["status"], "cancel_requested")
        self.assertEqual(requested["cancel_mode"], "cooperative")
        self.assertEqual(forced["cancel_mode"], "force")
        self.assertEqual(control["status"], "cancel_requested")
        self.assertEqual(control["cancel_mode"], "force")
        self.assertEqual(cancelled["status"], "cancelled")

    def test_expired_unstarted_claim_returns_to_same_worker_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            mushroom_worker_jobs.create_claim_probe(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                job_id="worker_job_12345678",
            )
            mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claimed_at="2026-07-19T12:00:00+00:00",
                lease_seconds=5,
                claim_token="old-token",
            )
            reclaimed = mushroom_worker_jobs.claim_next(
                path,
                worker_id="worker_aaaaaaaa",
                claimed_at="2026-07-19T12:00:06+00:00",
                lease_seconds=5,
                claim_token="new-token",
            )

        self.assertEqual(reclaimed["claim_token"], "new-token")
        self.assertEqual(reclaimed["assignment_revision"], 2)

    def test_invalid_worker_id_does_not_create_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            with self.assertRaisesRegex(ValueError, "Worker ID"):
                mushroom_worker_jobs.create_claim_probe(
                    path,
                    worker_id="short",
                    worker_display_name="Worker",
                )
            self.assertFalse(path.exists())

    def test_full_update_reserves_linked_rebuild_and_training_together(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            rebuild_id = "worker_job_rebuildfull"
            training_id = "worker_job_trainingfull"
            mushroom_worker_jobs.create_candidate_rebuild(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle={
                    "job_id": rebuild_id,
                    "job_spec_id": "sha256:" + "a" * 64,
                    "snapshot_id": "sha256:" + "b" * 64,
                    "input_file_count": 7,
                    "input_size_bytes": 1234,
                },
                job_id=rebuild_id,
            )
            mushroom_worker_jobs.claim_next(
                path, worker_id="worker_aaaaaaaa", claim_token="rebuild-secret"
            )
            mushroom_worker_jobs.start_job(
                path,
                job_id=rebuild_id,
                worker_id="worker_aaaaaaaa",
                claim_token="rebuild-secret",
            )
            mushroom_worker_jobs.finish_job(
                path,
                job_id=rebuild_id,
                worker_id="worker_aaaaaaaa",
                claim_token="rebuild-secret",
                status="complete",
                result={
                    "verification_status": "verified",
                    "comparison_status": "equivalent",
                    "verified_artifacts": 9,
                },
            )
            mushroom_worker_jobs.create_ml_train_job(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle={
                    "job_id": training_id,
                    "features_digest": "sha256:" + "c" * 64,
                    "job_spec_id": "sha256:" + "d" * 64,
                },
                job_id=training_id,
                triggered_by_job_id=rebuild_id,
            )
            mushroom_worker_jobs.claim_next(
                path, worker_id="worker_aaaaaaaa", claim_token="training-secret"
            )
            mushroom_worker_jobs.start_job(
                path,
                job_id=training_id,
                worker_id="worker_aaaaaaaa",
                claim_token="training-secret",
            )
            mushroom_worker_jobs.finish_job(
                path,
                job_id=training_id,
                worker_id="worker_aaaaaaaa",
                claim_token="training-secret",
                status="complete",
                result={"verification_status": "verified"},
            )

            rebuild, training = mushroom_worker_jobs.begin_full_update_promotion(
                path,
                rebuild_job_id=rebuild_id,
                training_job_id=training_id,
            )

            self.assertEqual(rebuild["promotion_status"], "promoting")
            self.assertEqual(training["promotion_status"], "promoting")

    def test_failed_multiversion_result_can_retry_without_new_job_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            job_id = "worker_job_multiretry"
            mushroom_worker_jobs.create_ml_multiversion_job(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle={
                    "job_id": job_id,
                    "bundle_digest": "sha256:" + "a" * 64,
                    "files": [{"path": "job_spec.json", "size_bytes": 1, "sha256": "b" * 64}],
                },
                job_id=job_id,
                profile_keys=["biology_v3/core"],
            )
            mushroom_worker_jobs.claim_next(
                path, worker_id="worker_aaaaaaaa", claim_token="retry-secret"
            )
            mushroom_worker_jobs.start_job(
                path,
                job_id=job_id,
                worker_id="worker_aaaaaaaa",
                claim_token="retry-secret",
            )
            mushroom_worker_jobs.finish_job(
                path,
                job_id=job_id,
                worker_id="worker_aaaaaaaa",
                claim_token="retry-secret",
                status="failed",
                error="HTTP Error 404: Not Found",
            )

            retried = mushroom_worker_jobs.retry_ml_multiversion_result(
                path, job_id=job_id
            )

            self.assertEqual(retried["status"], "queued")
            self.assertTrue(retried["result_retry"])
            self.assertEqual(retried["overall_percent"], 90)
            self.assertEqual(retried["assignment_revision"], 2)
            self.assertEqual(retried["job_id"], job_id)

    def test_multiversion_job_accepts_standard_snapshot_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            job_id = "worker_job_multisnapshot"
            job = mushroom_worker_jobs.create_ml_multiversion_job(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle={
                    "job_id": job_id,
                    "bundle_digest": "sha256:" + "a" * 64,
                    "snapshot_id": "sha256:" + "b" * 64,
                    "job_spec_id": "sha256:" + "c" * 64,
                    "input_file_count": 4,
                    "multiversion_spec": {
                        "kind": "mushroom_ml_multiversion_job",
                    },
                },
                job_id=job_id,
                profile_keys=["biology_v3/core"],
            )

        self.assertEqual(job["input_bundle"]["snapshot_id"], "sha256:" + "b" * 64)
        self.assertEqual(job["job_purpose"], "benchmark")
        self.assertEqual(job["profile_keys"], ["biology_v3/core"])
        self.assertFalse(job["promotion_eligible"])

    def test_operational_multiversion_result_identity_is_enforced(self) -> None:
        job = {
            "job_type": mushroom_worker_jobs.JOB_TYPE_ML_MULTIVERSION,
            "job_purpose": "operational",
        }
        normalized = mushroom_worker_jobs._normalized_result(
            job,
            {
                "verification_status": "verified",
                "operational_candidate_trained": True,
            },
        )

        self.assertEqual(normalized["job_purpose"], "operational")
        self.assertTrue(normalized["operational_candidate_trained"])
        with self.assertRaisesRegex(ValueError, "does not match"):
            mushroom_worker_jobs._normalized_result(
                job,
                {"operational_candidate_trained": False},
            )

    def test_operational_multiversion_job_keeps_selected_complete_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            job_id = "worker_job_operationalmulti"
            job = mushroom_worker_jobs.create_ml_multiversion_job(
                path,
                worker_id="worker_aaaaaaaa",
                worker_display_name="Worker A",
                input_bundle={
                    "job_id": job_id,
                    "bundle_digest": "sha256:" + "a" * 64,
                    "snapshot_id": "sha256:" + "b" * 64,
                    "job_spec_id": "sha256:" + "c" * 64,
                    "input_file_count": 4,
                    "multiversion_spec": {
                        "kind": "mushroom_ml_multiversion_job",
                    },
                },
                job_id=job_id,
                job_purpose="operational",
                profile_keys=[
                    "biology_v3/core",
                    "biology_v3/common_idw_plus_physical_state",
                ],
                triggered_by_job_id="worker_job_linkedtrain",
            )

        self.assertEqual(job["job_purpose"], "operational")
        self.assertEqual(len(job["profile_keys"]), 2)
        self.assertTrue(job["promotion_eligible"])

    def test_benchmark_job_requires_selection_and_verified_report_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker_jobs.json"
            with self.assertRaisesRegex(ValueError, "selected profiles"):
                mushroom_worker_jobs.create_ml_multiversion_job(
                    path,
                    worker_id="worker_aaaaaaaa",
                    worker_display_name="Worker A",
                    input_bundle={
                        "job_id": "worker_job_noprofiles",
                        "bundle_digest": "sha256:" + "a" * 64,
                    },
                    job_id="worker_job_noprofiles",
                )

        job = {
            "job_type": mushroom_worker_jobs.JOB_TYPE_ML_MULTIVERSION,
            "job_purpose": "benchmark",
        }
        normalized = mushroom_worker_jobs._normalized_result(
            job,
            {
                "verification_status": "verified_and_archived",
                "report_id": "sha256:" + "b" * 64,
                "benchmark_report_available": True,
                "operational_candidate_trained": False,
            },
        )
        self.assertTrue(normalized["benchmark_report_available"])
        self.assertEqual(normalized["report_id"], "sha256:" + "b" * 64)
        with self.assertRaisesRegex(ValueError, "report_id"):
            mushroom_worker_jobs._normalized_result(
                job, {"operational_candidate_trained": False}
            )

    def test_ml_training_result_persists_exact_verified_species_scope(self) -> None:
        normalized = mushroom_worker_jobs._normalized_result(
            {"job_type": mushroom_worker_jobs.JOB_TYPE_ML_TRAIN},
            {
                "verification_status": "verified",
                "trained_species_count": 2,
                "trained_species": ["boletus_edulis", "amanita_caesarea"],
                "result_manifest_id": "sha256:" + "a" * 64,
            },
        )

        self.assertEqual(
            normalized["trained_species"],
            ["boletus_edulis", "amanita_caesarea"],
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            mushroom_worker_jobs._normalized_result(
                {"job_type": mushroom_worker_jobs.JOB_TYPE_ML_TRAIN},
                {
                    "trained_species_count": 1,
                    "trained_species": ["boletus_edulis", "amanita_caesarea"],
                },
            )


if __name__ == "__main__":
    unittest.main()
