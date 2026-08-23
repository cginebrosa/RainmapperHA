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
    def test_monoversion_schema_and_fields_are_rejected(self) -> None:
        payload = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
        payload["schema_version"] = "1.0"
        with self.assertRaisesRegex(ValueError, "Unsupported.*schema"):
            registry.validate_registry(payload)

        payload["schema_version"] = "2.0"
        payload["active_version_id"] = "altitude_v2"
        with self.assertRaisesRegex(ValueError, "Obsolete monoversion field"):
            registry.validate_registry(payload)

    def test_default_registry_starts_clean_and_experiments_available(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)

        self.assertEqual(payload["schema_version"], "2.0")
        self.assertIsNone(payload["preferred_version_id"])
        self.assertTrue(
            all(row["installed_generation_id"] is None for row in payload["versions"])
        )
        self.assertEqual(
            {row["version_id"]: row["status"] for row in payload["versions"]},
            {
                "altitude_v2": "candidate",
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
            "clear_installed_generation_id",
        )
        v4 = next(
            row for row in payload["versions"] if row["version_id"] == "biology_v4"
        )
        self.assertIn(
            "derived_context.soilgrids_water.context_hash",
            v4["known_sites_identity_contract"]["collections"][0]["fields"],
        )

    def test_operational_training_scope_is_explicit_before_first_install(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)

        with self.assertRaisesRegex(ValueError, "Select at least one"):
            registry.training_version_ids(payload, job_purpose="operational")
        self.assertEqual(
            ["altitude_v2", "biology_v3"],
            registry.training_version_ids(
                payload,
                job_purpose="operational",
                requested_version_ids=["altitude_v2", "biology_v3"],
            ),
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
                "profile_ids": ["core", "common_idw_plus_physical_state"],
                "batch_id": "batch-v3",
            },
        )

        promoted = registry.transition_active_generation(
            payload, "biology_v3", generation_id="v3-approved"
        )

        self.assertEqual(promoted["preferred_version_id"], "biology_v3")
        self.assertEqual(
            next(row for row in promoted["versions"] if row["version_id"] == "biology_v3")["installed_generation_id"],
            "v3-approved",
        )
        self.assertEqual(len(promoted["versions"]), len(payload["versions"]))

    def test_proposed_version_cannot_be_activated(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        next(
            row for row in payload["versions"] if row["version_id"] == "biology_v4"
        )["status"] = "proposed"

        with self.assertRaisesRegex(ValueError, "proposed version"):
            registry.transition_active_generation(
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
        self.assertIsNone(payload["preferred_version_id"])

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
            registry.transition_active_generation(
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
                "batch_id": "batch-v3",
            },
        )

        activated = registry.transition_active_generation(
            payload, "biology_v3", generation_id="v3-complete-candidate"
        )

        self.assertEqual(activated["preferred_version_id"], "biology_v3")
        self.assertEqual(
            registry.training_profile_keys(
                activated, job_purpose="operational", version_ids=["biology_v3"]
            ),
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
                "batch_id": "batch-v3",
            },
        )

        with self.assertRaisesRegex(ValueError, "every operational profile"):
            registry.transition_active_generation(
                payload, "biology_v3", generation_id="v3-core-only"
            )

    def test_installing_v4_does_not_replace_v3_and_preference_is_independent(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        for version_id, generation_id, batch_id, profiles in (
            (
                "biology_v3",
                "generation-v3",
                "batch-v3",
                ["core", "common_idw_plus_physical_state"],
            ),
            (
                "biology_v4",
                "generation-v4",
                "batch-v4",
                ["extended_weather", "climatic_balance"],
            ),
        ):
            payload = registry.append_generation(
                payload,
                version_id=version_id,
                generation={
                    "generation_id": generation_id,
                    "kind": "trained_model",
                    "promotion_gate_status": "passed",
                    "profile_ids": profiles,
                    "batch_id": batch_id,
                },
            )
            payload = registry.transition_active_generation(
                payload, version_id, generation_id=generation_id
            )

        installed = {
            row["version_id"]: row["installed_generation_id"]
            for row in payload["versions"]
        }
        self.assertEqual(installed["biology_v3"], "generation-v3")
        self.assertEqual(installed["biology_v4"], "generation-v4")
        self.assertEqual(payload["preferred_version_id"], "biology_v3")
        preferred_v4 = registry.set_preferred_version(payload, "biology_v4")
        self.assertEqual(preferred_v4["preferred_version_id"], "biology_v4")
        self.assertEqual(
            next(
                row for row in preferred_v4["versions"]
                if row["version_id"] == "biology_v3"
            )["installed_generation_id"],
            "generation-v3",
        )

    def test_joint_batch_installs_v2_v3_v4_v5w_v6w_slots(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)
        version_ids = [
            "altitude_v2",
            "biology_v3",
            "biology_v4",
            "biology_v5_windowed_raw_weather",
            "biology_v6_windowed_smooth_hierarchical",
        ]
        profile_keys = registry.training_profile_keys(
            payload,
            job_purpose="operational",
            version_ids=version_ids,
        )
        manifest = {
            "batch_id": "joint-batch",
            "snapshot_id": "sha256:" + "a" * 64,
            "profile_keys": profile_keys,
            "artifacts": [
                {
                    "artifact_ref": {
                        "version_id": version_id,
                        "generation_id": f"generation-{version_id}",
                    }
                }
                for version_id in version_ids
            ],
        }

        installed = registry.install_batch_generations(payload, manifest)

        rows = {row["version_id"]: row for row in installed["versions"]}
        self.assertEqual(installed["preferred_version_id"], "altitude_v2")
        self.assertEqual(
            {
                version_id: rows[version_id]["installed_generation_id"]
                for version_id in version_ids
            },
            {
                version_id: f"generation-{version_id}"
                for version_id in version_ids
            },
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
                "profile_ids": ["adaptive"],
                "batch_id": "batch-v7",
            },
        )

        activated = registry.transition_active_generation(
            expanded, "biology_v7", generation_id="v7-approved"
        )

        self.assertEqual(activated["preferred_version_id"], "biology_v7")
        self.assertEqual(len(activated["versions"]), len(payload["versions"]) + 1)
        self.assertEqual(
            next(row["installed_generation_id"] for row in activated["versions"] if row["version_id"] == "biology_v7"),
            "v7-approved",
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
            self.assertIsNone(json.loads(destination.read_text())["preferred_version_id"])

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
                    "profile_ids": ["core", "common_idw_plus_physical_state"],
                    "batch_id": "batch-v3",
                },
            )
            promoted = registry.transition_active_generation(
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
                registry.load_registry(destination)["preferred_version_id"],
                "biology_v3",
            )

    def test_seed_migrates_schema_v1_and_preserves_every_generation(self) -> None:
        packaged = registry.load_registry(DEFAULT_REGISTRY)
        legacy = json.loads(json.dumps(packaged))
        legacy["schema_version"] = "1.0"
        legacy["active_version_id"] = "biology_v4"
        legacy["active_operational_target"] = {
            "version_id": "biology_v4",
            "generation_id": "installed-v4",
        }
        legacy["activation_history"] = [{"legacy": "preserved-in-backup"}]
        legacy.pop("preferred_version_id")
        for row in legacy["versions"]:
            row.pop("installed_generation_id")
            row["status"] = (
                "active" if row["version_id"] == "biology_v4" else row["status"]
            )
        v3 = next(
            row for row in legacy["versions"] if row["version_id"] == "biology_v3"
        )
        v3["generations"] = [
            {
                "generation_id": "benchmark-v3",
                "version_id": "biology_v3",
                "kind": "benchmark",
                "retention": "permanent",
                "promotion_gate_status": "not_evaluated",
            }
        ]
        v4 = next(
            row for row in legacy["versions"] if row["version_id"] == "biology_v4"
        )
        v4["generations"] = [
            {
                "generation_id": "installed-v4",
                "version_id": "biology_v4",
                "kind": "trained_model",
                "retention": "permanent",
                "promotion_gate_status": "passed",
                "profile_ids": ["extended_weather", "climatic_balance"],
                "batch_id": "batch-v4",
            }
        ]

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "mushroom_ml_version_registry.json"
            original = json.dumps(legacy, indent=2) + "\n"
            destination.write_text(original, encoding="utf-8")

            registry.ensure_seeded(
                default_path=DEFAULT_REGISTRY,
                persistent_path=destination,
            )

            migrated = registry.load_registry(destination)
            rows = {row["version_id"]: row for row in migrated["versions"]}
            self.assertEqual(migrated["schema_version"], "2.0")
            self.assertEqual(migrated["preferred_version_id"], "biology_v4")
            self.assertEqual(
                rows["biology_v4"]["installed_generation_id"], "installed-v4"
            )
            self.assertIsNone(rows["biology_v3"]["installed_generation_id"])
            self.assertEqual(
                [
                    row["generation_id"]
                    for row in rows["biology_v3"]["generations"]
                ],
                ["benchmark-v3"],
            )
            self.assertNotIn("active_version_id", migrated)
            self.assertNotIn("activation_history", migrated)
            backup = root / "mushroom_ml_version_registry.schema-1.0.backup.json"
            self.assertEqual(backup.read_text(encoding="utf-8"), original)

            registry.ensure_seeded(
                default_path=DEFAULT_REGISTRY,
                persistent_path=destination,
            )
            self.assertEqual(registry.load_registry(destination), migrated)
            self.assertEqual(backup.read_text(encoding="utf-8"), original)

    def test_schema_v1_migration_fails_without_changing_persistent_file(self) -> None:
        packaged = registry.load_registry(DEFAULT_REGISTRY)
        legacy = json.loads(json.dumps(packaged))
        legacy["schema_version"] = "1.0"
        legacy["active_version_id"] = "biology_v4"
        legacy["active_operational_target"] = {
            "version_id": "biology_v4",
            "generation_id": "missing-generation",
        }
        legacy.pop("preferred_version_id")
        for row in legacy["versions"]:
            row.pop("installed_generation_id")
            row["status"] = (
                "active" if row["version_id"] == "biology_v4" else row["status"]
            )

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "mushroom_ml_version_registry.json"
            original = json.dumps(legacy, indent=2) + "\n"
            destination.write_text(original, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "not registered"):
                registry.ensure_seeded(
                    default_path=DEFAULT_REGISTRY,
                    persistent_path=destination,
                )

            self.assertEqual(destination.read_text(encoding="utf-8"), original)
            self.assertFalse(
                (
                    root
                    / "mushroom_ml_version_registry.schema-1.0.backup.json"
                ).exists()
            )

    def test_schema_v1_migration_accepts_legacy_registry_without_target(self) -> None:
        packaged = registry.load_registry(DEFAULT_REGISTRY)
        legacy = json.loads(json.dumps(packaged))
        legacy["schema_version"] = "1.0"
        legacy["active_version_id"] = "altitude_v2"
        legacy.pop("active_operational_target", None)
        legacy.pop("preferred_version_id")
        legacy["versions"] = legacy["versions"][:3]
        for row in legacy["versions"]:
            row.pop("installed_generation_id")
            row["status"] = (
                "active" if row["version_id"] == "altitude_v2" else row["status"]
            )
        legacy["versions"][0]["generations"] = [
            {
                "generation_id": "historical-v2",
                "version_id": "altitude_v2",
                "kind": "trained_model",
                "retention": "permanent",
                "promotion_gate_status": "passed",
            }
        ]

        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "mushroom_ml_version_registry.json"
            destination.write_text(json.dumps(legacy), encoding="utf-8")

            registry.ensure_seeded(
                default_path=DEFAULT_REGISTRY,
                persistent_path=destination,
            )

            migrated = registry.load_registry(destination)
            v2 = next(
                row
                for row in migrated["versions"]
                if row["version_id"] == "altitude_v2"
            )
            self.assertIsNone(migrated["preferred_version_id"])
            self.assertIsNone(v2["installed_generation_id"])
            self.assertEqual(
                [row["generation_id"] for row in v2["generations"]],
                ["historical-v2"],
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
            self.assertEqual(
                migrated["preferred_version_id"],
                persistent["preferred_version_id"],
            )

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
