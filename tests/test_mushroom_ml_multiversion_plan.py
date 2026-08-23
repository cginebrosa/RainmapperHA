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

    def test_selected_v2_plan_contains_fixed_and_lag(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        version_id = "altitude_v2"
        result = plan.build_plan(
            registry,
            batch_id="batch-operational",
            snapshot_id="sha256:" + "b" * 64,
            generation_ids={version_id: "generation-operational"},
            species_ids=["boletus_edulis"],
            version_ids=[version_id],
        )

        refs = [row["artifact_ref"] for row in result["fits"]]
        self.assertEqual([version_id], result["version_ids"])
        self.assertEqual({version_id}, {row["version_id"] for row in refs})
        self.assertEqual(
            {"fixed_gap_7d_altitude_v2", "lag_event_altitude_v2"},
            {row["temporal_contract_id"] for row in refs},
        )
        self.assertEqual(12, result["fit_count"])

    def test_plan_filters_to_selected_profile(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        result = plan.build_plan(
            registry,
            batch_id="batch-selected",
            snapshot_id="sha256:" + "c" * 64,
            generation_ids={"biology_v4": "generation-v4"},
            species_ids=["boletus_edulis"],
            version_ids=["biology_v4"],
            profile_keys=["biology_v4/climatic_balance"],
        )

        self.assertEqual(result["profile_keys"], ["biology_v4/climatic_balance"])
        self.assertEqual(
            {row["artifact_ref"]["profile_id"] for row in result["fits"]},
            {"climatic_balance"},
        )
        self.assertGreater(result["fit_count"], 0)

    def test_v3_physical_is_a_separate_complete_profile(self) -> None:
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        result = plan.build_plan(
            registry,
            batch_id="batch-v3-physical",
            snapshot_id="sha256:" + "d" * 64,
            generation_ids={"biology_v3": "generation-v3-physical"},
            species_ids=["boletus_edulis"],
            version_ids=["biology_v3"],
            profile_keys=["biology_v3/common_idw_plus_physical_state"],
        )

        self.assertEqual(
            result["profile_keys"],
            ["biology_v3/common_idw_plus_physical_state"],
        )
        self.assertEqual(result["fit_count"], 12)
        self.assertEqual(
            {row["artifact_ref"]["profile_id"] for row in result["fits"]},
            {"common_idw_plus_physical_state"},
        )
