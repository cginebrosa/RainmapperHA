import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rainmapper_core import media_layout as layout, mushroom_paths as paths
from rainmapper_core.mushroom_derived_storage import prepare_derived_storage_transition


class MediaLayoutTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.media = self.root / "media"
        self.media.mkdir()
        self.config = self.media / "map-config.json"
        self.config.write_text(json.dumps({"models_root": "/media/rainmapper/mushroom-derived/ml_models", "other": 7}))
        for relative in ("mushroom-derived/ml_models/batches/a/model", "mushroom-derived/worker/input-bundles/bundle", "mushroom-derived/mushroom-artifacts/feature", "mushroom-derived/unknown/keep", "predictor_precompute/active.sqlite3", "runtime-cache/archives/a"):
            p = self.media / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(relative.encode())
        (self.media / "runtime-cache/archives/link").symlink_to("a")
        (self.media / "mushroom-derived/.legacy-share-transition-v1.json").write_text(json.dumps({"schema_version": "1.0", "status": "complete", "target_root": str(self.media / "mushroom-derived")}))

    def test_migration_preserves_every_file_and_legacy_receipt(self):
        with patch.dict(os.environ, {"RAINMAPPER_MEDIA_ROOT": str(self.media), "RAINMAPPER_SHARE_ROOT": str(self.root / "share")}, clear=True):
            self.assertEqual(paths.mushroom_ml_models_dir(), self.media / "mushroom-derived/ml_models")
            report = layout.migrate(self.media, [self.config], writers_stopped=True)
            self.assertEqual(report["state"], "complete")
            for item in report["moves"]:
                p = Path(item["target"])
                if p.is_dir():
                    self.assertEqual(layout.inventory(p), item["inventory"])
                self.assertFalse(Path(item["source"]).exists())
            self.assertEqual(paths.mushroom_ml_models_dir(), self.media / "results/models")
            self.assertEqual(paths.mushroom_worker_storage_dir(), self.media / "transfers/worker")
            self.assertEqual(paths.mushroom_rebuild_artifacts_dir(), self.media / "results/artifacts")
            self.assertEqual(paths.mushroom_predictor_precompute_dir(), self.media / "results/predictor-precompute")
            self.assertEqual(paths.predictor_runtime_archive_preferred_dir(), self.media / "cache/predictor-runtime-archives")
            self.assertTrue(prepare_derived_storage_transition()["already_complete"])
            self.assertEqual(json.loads(self.config.read_text())["models_root"], "/media/rainmapper/results/models")
            self.assertTrue(layout.migrate(self.media, [self.config], writers_stopped=True)["already_complete"])

    def test_conflict_aborts_before_any_move(self):
        (self.media / "results/models").mkdir(parents=True)
        before = layout.inventory(self.media)
        with self.assertRaisesRegex(ValueError, "conflict"):
            layout.migrate(self.media, [self.config], writers_stopped=True)
        self.assertEqual(before, layout.inventory(self.media))

    def test_publication_references_move_without_changing_scientific_identity(self):
        path = self.media / "runtime-cache/predictor-runtime-archives/published-runtime.json"
        path.parent.mkdir()
        manifest = {"fingerprint": "keep-this", "files": [{"sha256": "scientific-content"}]}
        state = {"models/m": {"size_bytes": 9, "mtime_ns": 123}}
        path.write_text(json.dumps({"manifest": manifest, "source_state": state,
                                   "sources": {"models/m": "/media/rainmapper/mushroom-derived/ml_models/model", "data/registry": "/media/rainmapper/runtime-cache/predictor-runtime-archives/registry.json"}}))
        layout.migrate(self.media, [self.config], writers_stopped=True)
        result = json.loads((self.media / "cache/predictor-runtime-archives/published-runtime.json").read_text())
        self.assertEqual(result["manifest"], manifest)
        self.assertEqual(result["source_state"], state)
        self.assertEqual(result["sources"]["models/m"], "/media/rainmapper/results/models/model")
        self.assertIsNone(layout.publication_update(self.media))

    def test_writers_and_invalid_config_abort_without_mutation(self):
        before = layout.inventory(self.media)
        with self.assertRaisesRegex(ValueError, "writers"):
            layout.migrate(self.media, [self.config], writers_stopped=False)
        self.assertEqual(before, layout.inventory(self.media))
        self.config.write_text("invalid json")
        before = layout.inventory(self.media)
        with self.assertRaises(ValueError):
            layout.migrate(self.media, [self.config], writers_stopped=True)
        self.assertEqual(before, layout.inventory(self.media))

    def test_changed_content_keeps_journal_and_blocks_activation(self):
        original = layout.inventory
        calls = 0
        def corrupt_after_move(p):
            nonlocal calls
            calls += 1
            result = original(p)
            if "results" in p.parts:
                result["unexpected"] = {"bytes": 5}
            return result
        with patch.object(layout, "inventory", side_effect=corrupt_after_move):
            with self.assertRaisesRegex(ValueError, "content changed"):
                layout.migrate(self.media, [self.config], writers_stopped=True)
        self.assertTrue((self.media / ".media-migration-in-progress.json").exists())
        self.assertFalse((self.media / layout.MARKER).exists())

    def test_retirement_checks_contents_and_preserves_unlisted_files(self):
        canonical = self.media / "geography"
        (canonical / "mushroom-GIS").mkdir(parents=True)
        original = self.media / "mushroom-GIS"
        original.mkdir()
        (original / "dem").write_bytes(b"height")
        (original / "evidence.txt").write_text("keep me")
        (canonical / "mushroom-GIS/dem").write_bytes(b"HEIGHT")
        row = {"path": "dem", "bytes": 6, "sha256": layout.sha256(original / "dem")}
        (canonical / "mushroom-GIS/geography-auxiliary.json").write_text(json.dumps({"files": [row]}))
        (canonical / "CURRENT.json").write_text(json.dumps({"generation": "test", "sources_file": "sources.json"}))
        (canonical / "sources.json").write_text('{"files": {}}')
        report = self.root / "retirement.json"
        with self.assertRaisesRegex(ValueError, "content changed"):
            layout.retire_legacy_geography(self.media, writers_stopped=True, consumers_verified=True, report_path=report)
        self.assertEqual((original / "dem").read_bytes(), b"height")
        (canonical / "mushroom-GIS/dem").write_bytes(b"height")
        result = layout.retire_legacy_geography(self.media, writers_stopped=True, consumers_verified=True, report_path=report)
        self.assertEqual(result["retired_bytes"], 6)
        self.assertFalse(original.exists())
        self.assertEqual((canonical / "mushroom-GIS/dem").read_bytes(), b"height")
        self.assertEqual((canonical / "imports/retired-legacy-metadata/mushroom-GIS/evidence.txt").read_text(), "keep me")


if __name__ == "__main__":
    unittest.main()
