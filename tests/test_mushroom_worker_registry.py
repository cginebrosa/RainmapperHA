import json
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_worker_registry


class MushroomWorkerRegistryTests(unittest.TestCase):
    def heartbeat(self, worker_id: str = "worker_12345678") -> dict[str, object]:
        return {
            "schema_version": "0.1",
            "kind": "rainmapper_worker_heartbeat",
            "worker_id": worker_id,
            "display_name": "M1 personal",
            "host_name": "macbook-m1-test",
            "architecture": "arm64",
            "platform": "Darwin",
            "worker_version": "local",
            "status": "idle",
            "job_api": "not_implemented",
            "capabilities": ["rebuild_v0"],
            "dataset_cache": {"status": "valid"},
        }

    def test_normalize_rejects_invalid_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "Worker ID"):
            mushroom_worker_registry.normalize_heartbeat({**self.heartbeat(), "worker_id": "short"})

    def test_normalize_accepts_bounded_discard_acknowledgements(self) -> None:
        job_id = "worker_job_discard123"
        heartbeat = mushroom_worker_registry.normalize_heartbeat(
            {**self.heartbeat(), "discarded_job_ids": [job_id, job_id]}
        )
        self.assertEqual(heartbeat["discarded_job_ids"], [job_id])
        with self.assertRaisesRegex(ValueError, "acknowledgement"):
            mushroom_worker_registry.normalize_heartbeat(
                {**self.heartbeat(), "discarded_job_ids": ["../private"]}
            )
        cleaned = mushroom_worker_registry.normalize_heartbeat(
            {**self.heartbeat(), "cleaned_job_ids": [job_id, job_id]}
        )
        self.assertEqual(cleaned["cleaned_job_ids"], [job_id])

    def test_remember_worker_does_not_rewrite_unchanged_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "workers.json"
            heartbeat = mushroom_worker_registry.normalize_heartbeat(self.heartbeat())

            self.assertTrue(mushroom_worker_registry.remember_worker(path, heartbeat))
            first = path.read_bytes()
            self.assertFalse(mushroom_worker_registry.remember_worker(path, heartbeat))
            self.assertEqual(path.read_bytes(), first)

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["workers"][0]["display_name"], "M1 personal")

    def test_registry_keeps_multiple_worker_identities(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "workers.json"
            mushroom_worker_registry.remember_worker(
                path,
                mushroom_worker_registry.normalize_heartbeat(self.heartbeat("worker_12345678")),
            )
            mushroom_worker_registry.remember_worker(
                path,
                mushroom_worker_registry.normalize_heartbeat(
                    {
                        **self.heartbeat("worker_abcdefgh"),
                        "display_name": "Mac del trabajo",
                        "host_name": "Mac-Work",
                    }
                ),
            )

            payload = mushroom_worker_registry.load_registry(path)

        self.assertEqual(len(payload["workers"]), 2)
        self.assertEqual(
            [worker["display_name"] for worker in payload["workers"]],
            ["M1 personal", "Mac del trabajo"],
        )

    def test_default_executor_is_persistent_and_old_registry_defaults_to_ha(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "workers.json"
            mushroom_worker_registry.remember_worker(
                path,
                mushroom_worker_registry.normalize_heartbeat(self.heartbeat()),
            )

            self.assertEqual(
                mushroom_worker_registry.load_registry(path)["default_executor"],
                "home_assistant",
            )
            self.assertTrue(
                mushroom_worker_registry.set_default_executor(
                    path,
                    "worker:worker_12345678",
                )
            )
            self.assertFalse(
                mushroom_worker_registry.set_default_executor(
                    path,
                    "worker:worker_12345678",
                )
            )
            self.assertEqual(
                mushroom_worker_registry.load_registry(path)["default_executor"],
                "worker:worker_12345678",
            )

        with self.assertRaisesRegex(ValueError, "executor"):
            mushroom_worker_registry.normalize_executor("automatic")

    def test_forget_worker_removes_identity_and_resets_default_to_ha(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "workers.json"
            for worker_id in ("worker_12345678", "worker_abcdefgh"):
                mushroom_worker_registry.remember_worker(
                    path,
                    mushroom_worker_registry.normalize_heartbeat(
                        self.heartbeat(worker_id)
                    ),
                )
            mushroom_worker_registry.set_default_executor(
                path,
                "worker:worker_12345678",
            )

            self.assertTrue(
                mushroom_worker_registry.forget_worker(path, "worker_12345678")
            )
            self.assertFalse(
                mushroom_worker_registry.forget_worker(path, "worker_12345678")
            )
            registry = mushroom_worker_registry.load_registry(path)

        self.assertEqual(registry["default_executor"], "home_assistant")
        self.assertEqual(
            [row["worker_id"] for row in registry["workers"]],
            ["worker_abcdefgh"],
        )

        with self.assertRaisesRegex(ValueError, "Worker ID"):
            mushroom_worker_registry.forget_worker(Path("unused"), "short")


if __name__ == "__main__":
    unittest.main()
