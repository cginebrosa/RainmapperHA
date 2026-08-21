from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core import mushroom_ml_version_registry as registry


DEFAULT_REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "mushroom-data"
    / "mushroom_ml_version_registry.json"
)


class MushroomMLVersionRegistryTests(TestCase):
    def test_default_registry_keeps_v2_active_and_experiments_available(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)

        self.assertEqual(payload["active_version_id"], "altitude_v2")
        self.assertEqual(
            {row["version_id"]: row["status"] for row in payload["versions"]},
            {
                "altitude_v2": "active",
                "biology_v3": "candidate",
                "biology_v4": "candidate",
                "biology_v5_raw_weather_discovery": "reference",
                "biology_v6_smooth_hierarchical": "reference",
                "biology_v5_windowed_raw_weather": "candidate",
                "biology_v6_windowed_smooth_hierarchical": "candidate",
            },
        )
        self.assertEqual(
            payload["retention_policy"]["deactivation_action"],
            "change_status_to_reference_never_delete",
        )
        v4 = next(
            row for row in payload["versions"] if row["version_id"] == "biology_v4"
        )
        self.assertIn(
            "derived_context.soilgrids_water.context_hash",
            v4["known_sites_identity_contract"]["collections"][0]["fields"],
        )

    def test_training_scope_separates_active_v2_from_scientific_versions(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)

        self.assertEqual(
            ["altitude_v2"],
            registry.training_version_ids(payload, job_purpose="operational"),
        )

    def test_every_implemented_version_exposes_its_complete_operational_profiles(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)

        self.assertEqual(
            [row["profile_key"] for row in registry.operational_profile_options(payload)],
            [
                "altitude_v2/common_idw",
                "biology_v3/core",
                "biology_v3/common_idw_plus_physical_state",
                "biology_v4/extended_weather",
                "biology_v4/climatic_balance",
                "biology_v5_windowed_raw_weather/raw_window_30d_plus_physical_state",
                "biology_v5_windowed_raw_weather/raw_window_60d_plus_physical_state",
                "biology_v5_windowed_raw_weather/raw_window_90d_plus_physical_state",
                "biology_v6_windowed_smooth_hierarchical/smooth_window_30d_plus_physical_state",
                "biology_v6_windowed_smooth_hierarchical/smooth_window_60d_plus_physical_state",
                "biology_v6_windowed_smooth_hierarchical/smooth_window_90d_plus_physical_state",
            ],
        )

    def test_benchmark_profiles_are_selectable_and_resolved_in_registry_order(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        options = registry.benchmark_profile_options(payload)
        keys = [row["profile_key"] for row in options]

        self.assertIn("altitude_v2/common_idw", keys)
        self.assertIn("biology_v3/common_idw_plus_physical_state", keys)
        self.assertIn(
            "biology_v6_windowed_smooth_hierarchical/smooth_window_30d_plus_physical_state",
            keys,
        )
        self.assertNotIn(
            "biology_v6_smooth_hierarchical/smooth_weather_physical_state", keys
        )
        self.assertNotIn(
            "biology_v5_raw_weather_discovery/raw_primary_plus_physical_state", keys
        )
        selected = registry.resolve_benchmark_profiles(
            payload,
            [
                "biology_v6_windowed_smooth_hierarchical/smooth_window_30d_plus_physical_state",
                "biology_v3/core",
            ],
        )
        self.assertEqual(
            [row["profile_key"] for row in selected],
            [
                "biology_v3/core",
                "biology_v6_windowed_smooth_hierarchical/smooth_window_30d_plus_physical_state",
            ],
        )
        with self.assertRaisesRegex(ValueError, "Unknown benchmark profile"):
            registry.resolve_benchmark_profiles(payload, ["biology_v3/missing"])
        self.assertEqual(
            [
                "altitude_v2",
                "biology_v3",
                "biology_v4",
                "biology_v5_windowed_raw_weather",
                "biology_v6_windowed_smooth_hierarchical",
            ],
            registry.training_version_ids(payload, job_purpose="benchmark"),
        )
        v3_physical = next(
            row
            for row in options
            if row["profile_key"] == "biology_v3/common_idw_plus_physical_state"
        )
        self.assertEqual(
            v3_physical["profile_label_key"],
            "ui.worker_benchmark_profile_v3_physical",
        )

    def test_activation_retains_previous_version_as_reference(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        payload = registry.append_generation(
            payload,
            version_id="biology_v3",
            generation={
                "generation_id": "v3-approved",
                "kind": "trained_model",
                "promotion_gate_status": "passed",
            },
        )

        promoted = registry.transition_active(
            payload, "biology_v3", generation_id="v3-approved"
        )

        self.assertEqual(promoted["active_version_id"], "biology_v3")
        self.assertEqual(
            {row["version_id"]: row["status"] for row in promoted["versions"]},
            {
                "altitude_v2": "reference",
                "biology_v3": "active",
                "biology_v4": "candidate",
                "biology_v5_raw_weather_discovery": "reference",
                "biology_v6_smooth_hierarchical": "reference",
                "biology_v5_windowed_raw_weather": "candidate",
                "biology_v6_windowed_smooth_hierarchical": "candidate",
            },
        )
        self.assertEqual(len(promoted["versions"]), len(payload["versions"]))

    def test_proposed_version_cannot_be_activated(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        next(
            row for row in payload["versions"] if row["version_id"] == "biology_v4"
        )["status"] = "proposed"

        with self.assertRaisesRegex(ValueError, "proposed version"):
            registry.transition_active(
                payload, "biology_v4", generation_id="v4-approved"
            )

    def test_proposed_version_can_become_candidate_without_name_specific_code(self) -> None:
        source = registry.load_registry(DEFAULT_REGISTRY)
        next(
            row for row in source["versions"] if row["version_id"] == "biology_v4"
        )["status"] = "proposed"
        payload = registry.transition_non_active_status(source, "biology_v4", "candidate")

        statuses = {row["version_id"]: row["status"] for row in payload["versions"]}
        self.assertEqual(statuses["biology_v4"], "candidate")
        self.assertEqual(payload["active_version_id"], "altitude_v2")

    def test_candidate_without_approved_model_cannot_be_activated(self) -> None:
        payload = registry.append_generation(
            registry.load_registry(DEFAULT_REGISTRY),
            version_id="biology_v3",
            generation={
                "generation_id": "v3-benchmark-only",
                "kind": "benchmark",
            },
        )

        with self.assertRaisesRegex(ValueError, "trained_model"):
            registry.transition_active(
                payload, "biology_v3", generation_id="v3-benchmark-only"
            )

    def test_v3_activation_targets_the_complete_version_not_one_profile(self) -> None:
        payload = registry.append_generation(
            registry.load_registry(DEFAULT_REGISTRY),
            version_id="biology_v3",
            generation={
                "generation_id": "v3-complete-candidate",
                "kind": "trained_model",
                "promotion_gate_status": "passed",
                "profile_ids": ["core", "common_idw_plus_physical_state"],
            },
        )

        activated = registry.transition_active_generation(
            payload, "biology_v3", generation_id="v3-complete-candidate"
        )

        self.assertEqual(activated["active_version_id"], "biology_v3")
        self.assertEqual(
            activated["active_operational_target"],
            {"version_id": "biology_v3", "generation_id": "v3-complete-candidate"},
        )
        self.assertEqual(
            registry.training_profile_keys(activated, job_purpose="operational"),
            [
                "biology_v3/core",
                "biology_v3/common_idw_plus_physical_state",
            ],
        )

    def test_v3_activation_rejects_a_generation_missing_one_profile(self) -> None:
        payload = registry.append_generation(
            registry.load_registry(DEFAULT_REGISTRY),
            version_id="biology_v3",
            generation={
                "generation_id": "v3-core-only",
                "kind": "trained_model",
                "promotion_gate_status": "passed",
                "profile_ids": ["core"],
            },
        )

        with self.assertRaisesRegex(ValueError, "every operational profile"):
            registry.transition_active_generation(
                payload, "biology_v3", generation_id="v3-core-only"
            )

    def test_future_version_is_registered_and_activated_without_code_changes(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        expanded = registry.register_version(
            payload,
            {
                "version_id": "biology_v7",
                "display_name": "Biology V7",
                "status": "candidate",
                "temporal_contract_ids": ["adaptive_event_biology_v7"],
                "contract_document": "docs/future-v7.md",
                "benchmark_available": True,
                "operational_prediction_available": True,
                "runtime": {
                    "adapter_id": "future_v7_runtime",
                    "profiles": [
                        {
                            "profile_id": "adaptive",
                            "temporal_contract_ids": ["adaptive_event_biology_v7"],
                            "estimator_ids": ["logistic_regression_reduced_v1"],
                            "input_requirements": {
                                "weather_lookback_days": 90,
                                "predictive_window_days": 30,
                                "include_physical_state": False,
                                "prepared_input_ids": ["v3_fixed"],
                            },
                            "operational_eligible": True,
                        }
                    ],
                },
            },
        )
        expanded = registry.append_generation(
            expanded,
            version_id="biology_v7",
            generation={
                "generation_id": "v7-approved",
                "kind": "trained_model",
                "promotion_gate_status": "passed",
            },
        )

        activated = registry.transition_active(
            expanded, "biology_v7", generation_id="v7-approved"
        )

        self.assertEqual(activated["active_version_id"], "biology_v7")
        self.assertEqual(len(activated["versions"]), len(payload["versions"]) + 1)
        self.assertEqual(
            next(
                row["status"]
                for row in activated["versions"]
                if row["version_id"] == "altitude_v2"
            ),
            "reference",
        )
        self.assertEqual(
            registry.version_for_temporal_contract(
                activated, "adaptive_event_biology_v7"
            )["version_id"],
            "biology_v7",
        )

    def test_generations_are_appended_with_permanent_retention(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        first = registry.append_generation(
            payload,
            version_id="altitude_v2",
            generation={"generation_id": "v2-benchmark-a", "kind": "benchmark"},
        )
        second = registry.append_generation(
            first,
            version_id="altitude_v2",
            generation={"generation_id": "v2-model-a", "kind": "trained_model"},
        )

        generations = second["versions"][0]["generations"]
        self.assertEqual([row["generation_id"] for row in generations], ["v2-benchmark-a", "v2-model-a"])
        self.assertTrue(all(row["retention"] == "permanent" for row in generations))

    def test_duplicate_generation_is_rejected_instead_of_replaced(self) -> None:
        payload = registry.append_generation(
            registry.load_registry(DEFAULT_REGISTRY),
            version_id="altitude_v2",
            generation={"generation_id": "same", "kind": "benchmark"},
        )

        with self.assertRaisesRegex(ValueError, "Duplicate generation_id"):
            registry.append_generation(
                payload,
                version_id="biology_v3",
                generation={"generation_id": "same", "kind": "benchmark"},
            )

    def test_benchmark_generation_cannot_claim_passed_promotion_gates(self) -> None:
        with self.assertRaisesRegex(ValueError, "trained_model generation"):
            registry.append_generation(
                registry.load_registry(DEFAULT_REGISTRY),
                version_id="biology_v3",
                generation={
                    "generation_id": "invalid-benchmark",
                    "kind": "benchmark",
                    "promotion_gate_status": "passed",
                },
            )

    def test_atomic_round_trip_preserves_all_versions(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "registry.json"
            registry.save_registry(destination, payload)

            self.assertEqual(registry.load_registry(destination), payload)
            self.assertEqual(json.loads(destination.read_text())["active_version_id"], "altitude_v2")

    def test_seed_never_replaces_persistent_lifecycle_state(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "live" / "registry.json"

            seeded = registry.ensure_seeded(
                default_path=DEFAULT_REGISTRY,
                persistent_path=destination,
            )
            with_generation = registry.append_generation(
                registry.load_registry(seeded),
                version_id="biology_v3",
                generation={
                    "generation_id": "v3-approved",
                    "kind": "trained_model",
                    "promotion_gate_status": "passed",
                },
            )
            promoted = registry.transition_active(
                with_generation,
                "biology_v3",
                generation_id="v3-approved",
            )
            registry.save_registry(seeded, promoted)
            registry.ensure_seeded(
                default_path=DEFAULT_REGISTRY,
                persistent_path=destination,
            )

            self.assertEqual(
                registry.load_registry(destination)["active_version_id"],
                "biology_v3",
            )

    def test_seed_migrates_packaged_contracts_and_preserves_lifecycle(self) -> None:
        packaged = registry.load_registry(DEFAULT_REGISTRY)
        persistent = json.loads(json.dumps(packaged))
        packaged_v5 = next(
            row
            for row in packaged["versions"]
            if row["version_id"] == "biology_v5_raw_weather_discovery"
        )
        persistent_v5 = next(
            row
            for row in persistent["versions"]
            if row["version_id"] == "biology_v5_raw_weather_discovery"
        )
        persistent_v5["temporal_contract_ids"] = [
            "fixed_gap_7d_biology_v5_raw365_v1",
            "lag_event_biology_v5_raw365_v1",
        ]
        persistent_v5["runtime"]["profiles"][0]["temporal_contract_ids"] = [
            "fixed_gap_7d_biology_v5_raw365_v1",
            "lag_event_biology_v5_raw365_v1",
        ]
        persistent_v5["generations"] = [
            {
                "generation_id": "legacy-v5-generation",
                "version_id": "biology_v5_raw_weather_discovery",
                "kind": "trained_model",
                "retention": "permanent",
                "promotion_gate_status": "not_evaluated",
            }
        ]
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            packaged_path = root / "packaged.json"
            persistent_path = root / "persistent.json"
            packaged_path.write_text(json.dumps(packaged), encoding="utf-8")
            persistent_path.write_text(json.dumps(persistent), encoding="utf-8")

            registry.ensure_seeded(
                default_path=packaged_path,
                persistent_path=persistent_path,
            )

            migrated = registry.load_registry(persistent_path)
            migrated_v5 = next(
                row
                for row in migrated["versions"]
                if row["version_id"] == "biology_v5_raw_weather_discovery"
            )
            self.assertEqual(
                migrated_v5["temporal_contract_ids"],
                packaged_v5["temporal_contract_ids"],
            )
            self.assertEqual(
                migrated_v5["generations"][0]["generation_id"],
                "legacy-v5-generation",
            )
            self.assertEqual(migrated["active_version_id"], persistent["active_version_id"])

    def test_seed_promotes_newly_implemented_packaged_versions_to_candidate(self) -> None:
        packaged = registry.load_registry(DEFAULT_REGISTRY)
        persistent = json.loads(json.dumps(packaged))
        for row in persistent["versions"]:
            if row["version_id"] in {
                "biology_v4",
                "biology_v5_windowed_raw_weather",
                "biology_v6_windowed_smooth_hierarchical",
            }:
                row["status"] = "proposed"
                row["operational_prediction_available"] = False
                for profile in row["runtime"]["profiles"]:
                    profile["operational_eligible"] = False

        merged = registry.merge_packaged_definitions(packaged, persistent)

        migrated = {
            row["version_id"]: row for row in merged["versions"]
        }
        for version_id in (
            "biology_v4",
            "biology_v5_windowed_raw_weather",
            "biology_v6_windowed_smooth_hierarchical",
        ):
            self.assertEqual(migrated[version_id]["status"], "candidate")
            self.assertTrue(
                migrated[version_id]["operational_prediction_available"]
            )
            self.assertTrue(
                all(
                    profile["operational_eligible"]
                    for profile in migrated[version_id]["runtime"]["profiles"]
                )
            )

    def test_persist_generation_is_immutable_idempotent_and_additive(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry_path = root / "registry.json"
            archive = root / "archive"
            model = root / "model.joblib"
            report = root / "report.json"
            registry.save_registry(registry_path, payload)
            model.write_bytes(b"model-v2-a")
            report.write_text('{"brier": 0.2}\n', encoding="utf-8")

            first = registry.persist_generation(
                registry_path,
                archive,
                version_id="altitude_v2",
                kind="trained_model",
                artifacts={"models/model.joblib": model, "reports/report.json": report},
                input_identities={
                    "known_sites_sha256": "a" * 64,
                    "features_sha256": "b" * 64,
                },
                promotion_gate_status="passed",
            )
            repeated = registry.persist_generation(
                registry_path,
                archive,
                version_id="altitude_v2",
                kind="trained_model",
                artifacts={"models/model.joblib": model, "reports/report.json": report},
                input_identities={
                    "known_sites_sha256": "a" * 64,
                    "features_sha256": "b" * 64,
                },
                promotion_gate_status="passed",
            )
            model.write_bytes(b"model-v2-b")
            second = registry.persist_generation(
                registry_path,
                archive,
                version_id="altitude_v2",
                kind="trained_model",
                artifacts={"models/model.joblib": model, "reports/report.json": report},
                input_identities={
                    "known_sites_sha256": "a" * 64,
                    "features_sha256": "b" * 64,
                },
                promotion_gate_status="passed",
            )

            self.assertEqual(first["status"], "created")
            self.assertEqual(repeated["status"], "reused")
            self.assertEqual(second["status"], "created")
            self.assertNotEqual(
                first["generation"]["generation_id"],
                second["generation"]["generation_id"],
            )
            generations = registry.load_registry(registry_path)["versions"][0]["generations"]
            self.assertEqual(len(generations), 2)
            self.assertTrue(
                all(
                    (archive / row["manifest_path"]).is_file()
                    for row in generations
                )
            )


if __name__ == "__main__":
    from unittest import main

    main()
