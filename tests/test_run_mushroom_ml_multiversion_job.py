from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_ml_version_registry


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run-mushroom-ml-multiversion-job.py"
REGISTRY = ROOT / "mushroom-data/mushroom_ml_version_registry.json"


def load_script():
    spec = importlib.util.spec_from_file_location("run_ml_multiversion", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunMushroomMLMultiversionJobTests(TestCase):
    def test_operational_bootstrap_selects_five_complete_versions(self) -> None:
        module = load_script()
        registry = mushroom_ml_version_registry.load_registry(REGISTRY)
        version_ids = [
            "altitude_v2",
            "biology_v3",
            "biology_v4",
            "biology_v5_windowed_raw_weather",
            "biology_v6_windowed_smooth_hierarchical",
        ]

        selected, profile_keys, resolved_versions = module.resolve_training_scope(
            registry,
            job_purpose="operational",
            profile_keys=None,
            version_ids=version_ids,
        )

        self.assertEqual(resolved_versions, version_ids)
        self.assertEqual(len(selected), 11)
        self.assertEqual(len(profile_keys), 11)
        self.assertFalse(
            any("raw_weather_discovery" in key for key in profile_keys)
        )
        self.assertFalse(
            any(
                key.startswith("biology_v6_smooth_hierarchical/")
                for key in profile_keys
            )
        )

        catalog = mushroom_ml_model_catalog.catalog_entries(registry)
        windows = sorted(
            {
                int(row["input_requirements"]["predictive_window_days"])
                for row in catalog
                if row["version_id"] in version_ids[-2:]
            }
        )
        self.assertEqual(windows, [30, 60, 90])
        self.assertTrue(
            all(
                row["input_requirements"]["weather_lookback_days"] == 365
                and row["input_requirements"]["include_physical_state"] is True
                for row in catalog
                if row["version_id"] in version_ids[-2:]
            )
        )

    def test_operational_scope_rejects_partial_version(self) -> None:
        module = load_script()
        registry = mushroom_ml_version_registry.load_registry(REGISTRY)

        with self.assertRaisesRegex(ValueError, "every profile in biology_v3"):
            module.resolve_training_scope(
                registry,
                job_purpose="operational",
                profile_keys=["biology_v3/core"],
                version_ids=["biology_v3"],
            )

    def test_training_manifest_publishes_complete_revision_vector(self) -> None:
        module = load_script()
        training_manifest = {
            "weather_history": {
                "generation_id": "weather-generation",
                "manifest_sha256": "a" * 64,
            },
            "files": [
                {"role": role, "sha256": character * 64}
                for role, character in (
                    ("observations", "b"),
                    ("reference_catalogs", "c"),
                    ("gis_mappings", "d"),
                    ("extra:known-sites.json", "e"),
                    ("extra:stations.txt", "f"),
                )
            ],
            "datasets": [
                {"dataset_id": "mushroom_gis_v0", "fingerprint": "sha256:" + "1" * 64}
            ],
        }
        with TemporaryDirectory() as temporary:
            registry_copy = Path(temporary) / "registry.json"
            registry_copy.write_bytes(REGISTRY.read_bytes())

            vector = module._input_revisions(training_manifest, registry_copy)

        self.assertEqual(
            set(vector), set(mushroom_ml_version_registry.REVISION_VECTOR_KEYS)
        )
        self.assertEqual(vector["weather_generation_id"], "weather-generation")
