import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_training_freshness as freshness


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLTrainingFreshnessTests(TestCase):
    def _manifest(self, training_digest: str | None = None) -> dict:
        artifact_ref = catalog.ModelArtifactRef(
            batch_id="batch-freshness",
            generation_id="generation-v3",
            version_id="biology_v3",
            temporal_contract_id="fixed_gap_7d_biology_v3",
            profile_id="core",
            estimator_id="logistic_regression_reduced_v1",
            species_id="boletus_edulis",
        )
        manifest = {
            "schema_version": "1.0",
            "kind": "mushroom_ml_runtime_batch",
            "batch_id": "batch-freshness",
            "snapshot_id": "sha256:" + "a" * 64,
            "artifacts": [
                {
                    "artifact_ref": artifact_ref.as_dict(),
                    "supported_horizons": [7],
                    "path": catalog.model_relative_path(artifact_ref).as_posix(),
                    "sha256": "b" * 64,
                }
            ],
        }
        if training_digest:
            manifest["training_input_manifest"] = {
                "path": "batches/batch-freshness/training-input-manifest.json",
                "sha256": training_digest,
            }
        return manifest

    def _assess(self, root: Path, **changes):
        values = {
            "runtime_manifest_path": root / "runtime-batch.json",
            "registry_path": REGISTRY_PATH,
            "models_root": root,
            "observations_path": root / "observations.json",
            "reference_catalogs_path": root / "references.json",
            "gis_mappings_path": root / "mappings.json",
            "weather_data_dir": root / "weather",
            "gis_root": root / "gis",
            "extra_inputs": {},
            "cache_seconds": 0,
        }
        values.update(changes)
        return freshness.assess(**values)

    def test_old_batch_without_training_identity_is_unknown(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "runtime-batch.json").write_text(json.dumps(self._manifest()))
            result = self._assess(root)
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["reason"], "training_identity_unavailable")

    def test_matching_and_changed_inputs_are_distinguished(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            training_path = root / "batches/batch-freshness/training-input-manifest.json"
            training_path.parent.mkdir(parents=True)
            training_path.write_text(json.dumps({"kind": "mushroom_rebuild_input_manifest"}))
            digest = hashlib.sha256(training_path.read_bytes()).hexdigest()
            (root / "runtime-batch.json").write_text(json.dumps(self._manifest(digest)))
            with patch(
                "rainmapper_core.mushroom_ml_training_freshness.mushroom_rebuild_snapshot.verify_live_inputs",
                return_value={"status": "valid", "current_snapshot_id": "sha256:" + "a" * 64, "errors": []},
            ) as verify:
                self.assertEqual(self._assess(root)["status"], "current")
                self.assertEqual(
                    verify.call_args.kwargs["ignored_extra_inputs"],
                    {"observation-features.json"},
                )
                self.assertFalse(verify.call_args.kwargs["verify_weather_file_hashes"])
            with patch(
                "rainmapper_core.mushroom_ml_training_freshness.mushroom_rebuild_snapshot.verify_live_inputs",
                return_value={"status": "stale", "current_snapshot_id": "sha256:" + "c" * 64, "errors": ["changed"]},
            ):
                self.assertEqual(self._assess(root)["status"], "stale")
