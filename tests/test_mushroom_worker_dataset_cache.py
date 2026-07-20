import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_worker_dataset_cache


def _record(root: Path, relative: str) -> dict[str, object]:
    content = (root / relative).read_bytes()
    return {
        "role": "gis",
        "path": relative,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _fingerprint(records: list[dict[str, object]]) -> str:
    normalized = [
        {
            "role": record.get("role"),
            "path": record.get("path"),
            "size_bytes": record.get("size_bytes"),
            "sha256": record.get("sha256"),
            "exists": record.get("exists", True),
        }
        for record in records
    ]
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class MushroomWorkerDatasetCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.worker_data = self.root / "worker-data"
        (self.source / "nested").mkdir(parents=True)
        (self.source / "nested/a.dat").write_bytes(b"alpha")
        (self.source / "b.dat").write_bytes(b"bravo")
        self.manifest = self.make_manifest()

    def make_manifest(self) -> dict[str, object]:
        records = [_record(self.source, "nested/a.dat"), _record(self.source, "b.dat")]
        return {
            "schema_version": "0.1",
            "kind": "mushroom_rebuild_input_manifest",
            "datasets": [
                {
                    "dataset_id": "mushroom_gis_v0",
                    "fingerprint": _fingerprint(records),
                    "files": records,
                }
            ],
        }

    def current_fingerprint(self) -> str:
        current = self.worker_data / "datasets/mushroom_gis_v0/current"
        return Path(current.readlink()).name

    def test_first_sync_creates_and_deeply_verifies_version(self) -> None:
        result = mushroom_worker_dataset_cache.sync_local(
            self.manifest, self.source, self.worker_data
        )
        verification = mushroom_worker_dataset_cache.verify_version(
            self.worker_data, deep=True
        )

        self.assertEqual(result["status"], "synchronized")
        self.assertEqual(verification["status"], "valid")
        self.assertEqual(verification["validation"], "deep")
        self.assertEqual(self.current_fingerprint(), self.manifest["datasets"][0]["fingerprint"])

    def test_second_sync_reuses_existing_version_without_copying(self) -> None:
        mushroom_worker_dataset_cache.sync_local(self.manifest, self.source, self.worker_data)

        with mock.patch.object(
            mushroom_worker_dataset_cache,
            "_copy_and_hash",
            side_effect=AssertionError("copy must not run"),
        ):
            result = mushroom_worker_dataset_cache.sync_local(
                self.manifest, self.source, self.worker_data
            )

        self.assertEqual(result["status"], "reused")

    def test_fetcher_sync_writes_directly_to_staging_and_reuses_without_refetch(self) -> None:
        fetched: list[str] = []

        def fetch(record: dict[str, object], destination: Path) -> tuple[int, str]:
            fetched.append(str(record["path"]))
            content = (self.source / str(record["path"])).read_bytes()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            return len(content), hashlib.sha256(content).hexdigest()

        result = mushroom_worker_dataset_cache.sync_from_fetcher(
            self.manifest,
            self.worker_data,
            fetch_file=fetch,
        )
        reused = mushroom_worker_dataset_cache.sync_from_fetcher(
            self.manifest,
            self.worker_data,
            fetch_file=lambda _record, _destination: (_ for _ in ()).throw(
                AssertionError("an existing dataset version must not be fetched")
            ),
        )

        self.assertEqual(result["status"], "synchronized")
        self.assertEqual(result["transferred_file_count"], 2)
        self.assertEqual(result["transferred_size_bytes"], 10)
        self.assertEqual(fetched, ["nested/a.dat", "b.dat"])
        self.assertEqual(reused["status"], "reused")
        self.assertEqual(reused["transferred_size_bytes"], 0)
        self.assertEqual(
            mushroom_worker_dataset_cache.verify_version(self.worker_data, deep=True)["status"],
            "valid",
        )

    def test_fetcher_failure_preserves_previous_version_and_cleans_staging(self) -> None:
        first = mushroom_worker_dataset_cache.sync_local(
            self.manifest,
            self.source,
            self.worker_data,
        )
        (self.source / "b.dat").write_bytes(b"updated")
        updated_manifest = self.make_manifest()
        calls = 0

        def fetch(record: dict[str, object], destination: Path) -> tuple[int, str]:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ConnectionError("injected network interruption")
            content = (self.source / str(record["path"])).read_bytes()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            return len(content), hashlib.sha256(content).hexdigest()

        with self.assertRaisesRegex(ConnectionError, "network interruption"):
            mushroom_worker_dataset_cache.sync_from_fetcher(
                updated_manifest,
                self.worker_data,
                fetch_file=fetch,
            )

        staging = self.worker_data / "datasets/mushroom_gis_v0/staging"
        self.assertEqual(self.current_fingerprint(), first["fingerprint"])
        self.assertEqual(list(staging.iterdir()), [])
        self.assertEqual(
            mushroom_worker_dataset_cache.verify_version(self.worker_data)["status"],
            "valid",
        )

    def test_fetcher_sync_rejects_insufficient_staging_space_before_fetch(self) -> None:
        disk_usage = type("DiskUsage", (), {"free": 1})()
        with mock.patch.object(
            mushroom_worker_dataset_cache.shutil,
            "disk_usage",
            return_value=disk_usage,
        ), self.assertRaisesRegex(RuntimeError, "insufficient free space"):
            mushroom_worker_dataset_cache.sync_from_fetcher(
                self.manifest,
                self.worker_data,
                fetch_file=lambda _record, _destination: (_ for _ in ()).throw(
                    AssertionError("fetch must not start without enough space")
                ),
            )

    def test_new_version_is_activated_and_old_version_is_retained(self) -> None:
        first = mushroom_worker_dataset_cache.sync_local(
            self.manifest, self.source, self.worker_data
        )
        old_fingerprint = first["fingerprint"]
        (self.source / "b.dat").write_bytes(b"updated")
        updated_manifest = self.make_manifest()

        result = mushroom_worker_dataset_cache.sync_local(
            updated_manifest, self.source, self.worker_data
        )

        versions = self.worker_data / "datasets/mushroom_gis_v0/versions"
        self.assertEqual(result["status"], "synchronized")
        self.assertEqual(self.current_fingerprint(), result["fingerprint"])
        self.assertTrue((versions / old_fingerprint).is_dir())
        self.assertTrue((versions / result["fingerprint"]).is_dir())

    def test_copy_failure_preserves_current_and_cleans_staging(self) -> None:
        first = mushroom_worker_dataset_cache.sync_local(
            self.manifest, self.source, self.worker_data
        )
        (self.source / "b.dat").write_bytes(b"updated")
        updated_manifest = self.make_manifest()
        original_copy = mushroom_worker_dataset_cache._copy_and_hash
        calls = 0

        def fail_second_copy(source: Path, destination: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected copy failure")
            return original_copy(source, destination, chunk_size)

        with mock.patch.object(
            mushroom_worker_dataset_cache,
            "_copy_and_hash",
            side_effect=fail_second_copy,
        ):
            with self.assertRaisesRegex(OSError, "injected copy failure"):
                mushroom_worker_dataset_cache.sync_local(
                    updated_manifest, self.source, self.worker_data
                )

        staging = self.worker_data / "datasets/mushroom_gis_v0/staging"
        self.assertEqual(self.current_fingerprint(), first["fingerprint"])
        self.assertEqual(list(staging.iterdir()), [])
        self.assertEqual(
            mushroom_worker_dataset_cache.verify_version(self.worker_data)["status"],
            "valid",
        )

    def test_rejects_unsafe_relative_path(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["datasets"][0]["files"][0]["path"] = "../escape"

        with self.assertRaisesRegex(ValueError, "unsafe dataset relative path"):
            mushroom_worker_dataset_cache.sync_local(manifest, self.source, self.worker_data)


if __name__ == "__main__":
    unittest.main()
