from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_ml_version_promotion as promotion
from rainmapper_core import mushroom_ml_version_registry


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "mushroom-data" / "mushroom_ml_version_registry.json"


class MushroomMLVersionPromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.models = self.root / "models"
        self.models.mkdir()
        self.registry = self.root / "registry.json"
        shutil.copy2(DEFAULT_REGISTRY, self.registry)
        (self.models / "runtime-batch.json").write_text(
            json.dumps({"batch_id": "previous-v2"}) + "\n", encoding="utf-8"
        )
        self.extracted = self.root / "candidate-batch"
        self.extracted.mkdir()
        (self.extracted / "training-input-manifest.json").write_text(
            json.dumps({"kind": "mushroom_rebuild_input_manifest", "files": [], "datasets": []}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _verified_candidate(self) -> tuple[dict, dict, Path, str]:
        generation_id = "biology_v3_candidate_generation"
        return (
            {
                "batch_id": "candidate-biology-v3",
                "snapshot_id": "sha256:" + "1" * 64,
            },
            {
                "batch_id": "candidate-biology-v3",
                "version_ids": ["biology_v3"],
                "profile_keys": [
                    "biology_v3/core",
                    "biology_v3/common_idw_plus_physical_state",
                ],
                "training_input_manifest": {"path": "training-input-manifest.json"},
                "artifacts": [
                    {
                        "artifact_ref": {
                            "batch_id": "candidate-biology-v3",
                            "generation_id": generation_id,
                            "version_id": "biology_v3",
                            "temporal_contract_id": "fixed_gap_7d_biology_v3",
                            "profile_id": "core",
                            "estimator_id": "logistic_regression_reduced_v1",
                            "species_id": "boletus_edulis",
                        },
                        "supported_horizons": [7],
                        "path": "batches/candidate-biology-v3/model.joblib",
                        "sha256": "a" * 64,
                    }
                ],
            },
            self.extracted,
            "worker_job_candidate",
        )

    def test_promote_and_rollback_complete_v3_version(self) -> None:
        def install(**kwargs: object) -> dict[str, object]:
            batch = self.models / "batches" / "candidate-biology-v3"
            batch.mkdir(parents=True)
            (self.models / "runtime-batch.json").write_text(
                json.dumps({"batch_id": "candidate-biology-v3"}) + "\n",
                encoding="utf-8",
            )
            return {"batch_id": "candidate-biology-v3", "status": "installed"}

        with (
            mock.patch.object(
                promotion.mushroom_ml_multiversion_transport,
                "verify_archived_candidate",
                return_value=self._verified_candidate(),
            ),
            mock.patch.object(
                promotion.mushroom_rebuild_snapshot,
                "verify_live_inputs",
                return_value={"status": "valid", "errors": []},
            ),
            mock.patch.object(
                promotion.mushroom_ml_multiversion_transport,
                "install_verified_result",
                side_effect=install,
            ),
            mock.patch.object(
                promotion.mushroom_ml_runtime_inference,
                "load_exact_artifact",
                return_value={},
            ),
        ):
            activated = promotion.promote_candidate(
                models_root=self.models,
                registry_path=self.registry,
                candidate_id="candidate-biology-v3",
                observations_path=self.root / "observations.json",
                reference_catalogs_path=self.root / "catalogs.json",
                gis_mappings_path=self.root / "gis.json",
                weather_data_dir=self.root / "weather",
                gis_root=self.root / "gis",
                known_sites_path=self.root / "sites.json",
                stations_path=self.root / "stations.txt",
                observation_features_path=self.root / "features.json",
                source_benchmark_batch_id="benchmark-v3",
            )

        active_registry = mushroom_ml_version_registry.load_registry(self.registry)
        self.assertEqual(active_registry["active_version_id"], "biology_v3")
        self.assertEqual(
            mushroom_ml_version_registry.training_profile_keys(
                active_registry, job_purpose="operational"
            ),
            [
                "biology_v3/core",
                "biology_v3/common_idw_plus_physical_state",
            ],
        )
        self.assertEqual(activated["profile_ids"], ["core", "common_idw_plus_physical_state"])

        rolled_back = promotion.rollback_promotion(
            models_root=self.models,
            registry_path=self.registry,
            promotion_id=activated["promotion_id"],
        )

        restored_registry = mushroom_ml_version_registry.load_registry(self.registry)
        self.assertEqual(restored_registry["active_version_id"], "altitude_v2")
        self.assertEqual(
            json.loads((self.models / "runtime-batch.json").read_text(encoding="utf-8"))["batch_id"],
            "previous-v2",
        )
        self.assertEqual(rolled_back["status"], "rolled_back")


if __name__ == "__main__":
    unittest.main()
