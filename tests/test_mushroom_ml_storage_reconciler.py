from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rainmapper_core import mushroom_ml_storage_reconciler as reconciler
from rainmapper_core import mushroom_ml_version_registry


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "mushroom-data" / "mushroom_ml_version_registry.json"


class MushroomMLStorageReconcilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "models"
        self.root.mkdir(parents=True)
        self.registry_path = Path(self.temporary.name) / "registry.json"
        shutil.copy2(DEFAULT_REGISTRY, self.registry_path)
        self.version_id = "altitude_v2"
        registry = mushroom_ml_version_registry.load_registry(self.registry_path)
        self.profile_ids = [
            row["profile_id"]
            for row in mushroom_ml_version_registry.operational_profile_options(registry)
            if row["version_id"] == self.version_id
        ]

    def generation(self, generation_id: str, batch_id: str) -> dict[str, object]:
        return {
            "generation_id": generation_id,
            "kind": "trained_model",
            "profile_ids": self.profile_ids,
            "batch_id": batch_id,
            "snapshot_id": "sha256:" + "a" * 64,
            "promotion_gate_status": "passed",
            "promotion_gate_kind": "technical_execution_only",
        }

    @staticmethod
    def write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def make_batch(self, batch_id: str) -> Path:
        path = self.root / "batches" / batch_id
        self.write_json(
            path / "manifest.json",
            {
                "schema_version": "1.0",
                "kind": "mushroom_ml_runtime_batch",
                "batch_id": batch_id,
            },
        )
        (path / "payload.bin").write_bytes(batch_id.encode())
        return path

    def test_dry_run_and_apply_keep_only_installed_batch_and_remove_legacy_state(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(self.registry_path)
        registry = mushroom_ml_version_registry.append_generation(
            registry,
            version_id=self.version_id,
            generation=self.generation("generation_old", "batch_old"),
        )
        previous = mushroom_ml_version_registry.transition_active_generation(
            registry, self.version_id, generation_id="generation_old"
        )
        registry = mushroom_ml_version_registry.append_generation(
            previous,
            version_id=self.version_id,
            generation=self.generation("generation_current", "batch_current"),
        )
        registry = mushroom_ml_version_registry.transition_active_generation(
            registry, self.version_id, generation_id="generation_current"
        )
        registry = mushroom_ml_version_registry.append_generation(
            registry,
            version_id=self.version_id,
            generation=self.generation("generation_stale", "batch_stale"),
        )
        mushroom_ml_version_registry.save_registry(self.registry_path, registry)
        for batch_id in ("batch_old", "batch_stale", "batch_current", "batch_orphan"):
            self.make_batch(batch_id)
        candidate = self.root / "candidates" / "batch_current"
        self.write_json(
            candidate / "multiversion_result.json",
            {"batch_id": "batch_current", "job_id": "worker_job_candidate123"},
        )
        (candidate / "large.bin").write_bytes(b"candidate")
        promotion_id = "promotion_20260823T120000000000Z"
        promotion_root = self.root / "promotion-history" / promotion_id
        self.write_json(
            promotion_root / "promotion.json",
            {
                "kind": "mushroom_ml_version_promotion",
                "promotion_id": promotion_id,
                "status": "installed",
                "activated_at": "2026-08-23T12:00:00+00:00",
                "generation_ids": {self.version_id: "generation_current"},
                "version_ids": [self.version_id],
                "batch_id": "batch_current",
            },
        )
        mushroom_ml_version_registry.save_registry(
            promotion_root / "previous-registry.json", previous
        )

        registry_before = self.registry_path.read_bytes()
        plan = reconciler.plan_model_storage(
            models_root=self.root, registry_path=self.registry_path
        )

        self.assertEqual(plan["errors"], [])
        self.assertEqual(
            {row["batch_id"] for row in plan["protected_batches"]},
            {"batch_current"},
        )
        self.assertEqual(
            {row["batch_id"] for row in plan["batch_removals"]},
            {"batch_old", "batch_stale", "batch_orphan"},
        )
        self.assertEqual(
            [row["candidate_id"] for row in plan["candidate_removals"]],
            ["batch_current"],
        )
        self.assertEqual(
            [row["promotion_id"] for row in plan["promotion_history_removals"]],
            [promotion_id],
        )
        self.assertEqual(self.registry_path.read_bytes(), registry_before)

        applied = reconciler.apply_model_storage_plan(
            models_root=self.root,
            registry_path=self.registry_path,
            plan=plan,
        )

        self.assertEqual(applied["errors"], [])
        self.assertTrue((self.root / "batches" / "batch_current").is_dir())
        self.assertFalse((self.root / "batches" / "batch_old").exists())
        self.assertFalse((self.root / "batches" / "batch_stale").exists())
        self.assertFalse((self.root / "batches" / "batch_orphan").exists())
        self.assertFalse(candidate.exists())
        self.assertFalse(promotion_root.exists())
        self.assertEqual(applied["removed_promotion_history"], [promotion_id])
        saved = mushroom_ml_version_registry.load_registry(self.registry_path)
        version = next(row for row in saved["versions"] if row["version_id"] == self.version_id)
        self.assertEqual(
            {row["generation_id"] for row in version["generations"]},
            {"generation_current"},
        )


if __name__ == "__main__":
    unittest.main()
