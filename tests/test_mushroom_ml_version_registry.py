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
                "biology_v4": "proposed",
                "biology_v5_raw_weather_discovery": "proposed",
                "biology_v6_smooth_hierarchical": "proposed",
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
                "biology_v4": "proposed",
                "biology_v5_raw_weather_discovery": "proposed",
                "biology_v6_smooth_hierarchical": "proposed",
            },
        )
        self.assertEqual(len(promoted["versions"]), len(payload["versions"]))

    def test_proposed_version_cannot_be_activated(self) -> None:
        payload = registry.load_registry(DEFAULT_REGISTRY)

        with self.assertRaisesRegex(ValueError, "proposed version"):
            registry.transition_active(
                payload, "biology_v4", generation_id="v4-approved"
            )

    def test_proposed_version_can_become_candidate_without_name_specific_code(self) -> None:
        payload = registry.transition_non_active_status(
            registry.load_registry(DEFAULT_REGISTRY), "biology_v4", "candidate"
        )

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
                "operational_prediction_available": False,
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
