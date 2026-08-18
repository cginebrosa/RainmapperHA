from pathlib import Path
from unittest import TestCase

from rainmapper_core import mushroom_ml_multiversion_plan as plan
from rainmapper_core import mushroom_ml_version_registry


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


class MushroomMLMultiversionPlanTests(TestCase):
    def test_plan_has_one_lag_fit_and_shared_v6_is_not_duplicated_by_species(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        generation_ids = {
            row["version_id"]: f"generation-{index}"
            for index, row in enumerate(registry["versions"], start=2)
        }
        result = plan.build_plan(
            registry,
            batch_id="batch-a",
            snapshot_id="sha256:" + "a" * 64,
            generation_ids=generation_ids,
            species_ids=["boletus_edulis", "lactarius_deliciosus"],
        )

        keys = ["/".join(row["artifact_ref"].values()) for row in result["fits"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(
            all(
                row["supported_horizons"] == list(range(1, 8))
                for row in result["fits"]
                if row["artifact_ref"]["temporal_contract_id"].startswith("lag_event_")
            )
        )
        shared_v6 = [
            row
            for row in result["fits"]
            if row["artifact_ref"]["version_id"] == "biology_v6_smooth_hierarchical"
            and row["estimator_scope"] == "shared"
        ]
        self.assertEqual(len(shared_v6), 4)
        self.assertTrue(
            all(row["artifact_ref"]["species_id"] == "all_species" for row in shared_v6)
        )
        self.assertTrue(all(len(row["training_species_ids"]) == 2 for row in shared_v6))

    def test_plan_requires_generation_for_every_catalog_version(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        with self.assertRaisesRegex(ValueError, "generation_id"):
            plan.build_plan(
                registry,
                batch_id="batch-a",
                snapshot_id="sha256:" + "a" * 64,
                generation_ids={"altitude_v2": "generation-v2"},
                species_ids=["boletus_edulis"],
            )
