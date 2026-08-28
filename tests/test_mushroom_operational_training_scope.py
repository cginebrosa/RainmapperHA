import hashlib
import json
from pathlib import Path
from unittest import TestCase

from rainmapper_core import mushroom_ml_multiversion_plan
from rainmapper_core import mushroom_ml_tuning_catalog
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_operational_training_scope as operational


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "mushroom-data/mushroom_ml_version_registry.json"


def _row(species_id: str, day: int, micro_area_id: str, target: str) -> dict:
    return {
        "species_id": species_id,
        "observed_at": f"2026-08-{day:02d}",
        "micro_area_id": micro_area_id,
        "validation_status": "valid",
        "calibration_use": "include",
        "prediction_target": target,
        "weather_gaps": [],
        "gis_altitude_m": 100.0,
    }


def _catalog_for(registry: dict, fit_plan: dict) -> dict:
    decisions = []
    for fit in fit_plan["fits"]:
        scope = mushroom_ml_tuning_catalog.decision_scope(fit["artifact_ref"])
        decisions.append(
            {
                "key": mushroom_ml_tuning_catalog.decision_key(scope),
                "scope": scope,
                "fit_config": {},
                "source_artifact_sha256": "a" * 64,
            }
        )
    decisions.sort(key=lambda row: row["key"])
    identity = {
        "compatibility_fingerprint": mushroom_ml_tuning_catalog.compatibility_fingerprint(registry),
        "source_batch_id": "source-batch",
        "source_snapshot_id": "sha256:" + "b" * 64,
        "decisions": decisions,
    }
    return {
        "schema_version": mushroom_ml_tuning_catalog.SCHEMA_VERSION,
        "kind": mushroom_ml_tuning_catalog.KIND,
        "catalog_id": "sha256:" + hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        **identity,
    }


class OperationalTrainingScopeTests(TestCase):
    def setUp(self) -> None:
        self.known_sites = {
            "micro_areas": [
                {"micro_area_id": "ma-a", "area_id": "area-a"},
                {"micro_area_id": "ma-b", "area_id": "area-a"},
            ]
        }

    def test_ten_rows_aggregated_to_nine_episodes_are_omitted(self) -> None:
        rows = [
            _row("sentinel", day, "ma-a", "favorable" if day == 1 else "unfavorable")
            for day in range(1, 10)
        ]
        rows.append(_row("sentinel", 1, "ma-b", "unfavorable"))
        rows.extend(
            _row("admitted", day, "ma-a", "favorable" if day == 1 else "unfavorable")
            for day in range(1, 11)
        )

        scope = operational.build_scope({"rows": rows}, self.known_sites)

        sentinel = next(row for row in scope["species"] if row["species_id"] == "sentinel")
        self.assertEqual(10, sentinel["eligible_row_count"])
        self.assertEqual(9, sentinel["area_episode_count"])
        self.assertEqual("omitted", sentinel["decision"])
        self.assertEqual("insufficient_area_episodes", sentinel["reason_code"])
        self.assertEqual(["admitted"], scope["admitted_species_ids"])

    def test_equal_serialized_inputs_produce_equal_scope_and_plan(self) -> None:
        rows = [
            _row("admitted", day, "ma-a", "favorable" if day == 1 else "unfavorable")
            for day in range(1, 11)
        ]
        local_scope = operational.build_scope({"rows": rows}, self.known_sites)
        remote_scope = operational.build_scope(
            json.loads(json.dumps({"rows": rows})),
            json.loads(json.dumps(self.known_sites)),
        )
        self.assertEqual(local_scope, remote_scope)

        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        fit_plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id="operational_plan",
            snapshot_id=local_scope["scope_id"],
            generation_ids={"altitude_v2": "plan_altitude_v2"},
            species_ids=local_scope["admitted_species_ids"],
            version_ids=["altitude_v2"],
            profile_keys=["altitude_v2/common_idw"],
        )
        catalog = _catalog_for(registry, fit_plan)
        local_plan = operational.build_plan(
            registry,
            local_scope,
            catalog,
            version_ids=["altitude_v2"],
            profile_keys=["altitude_v2/common_idw"],
        )
        remote_plan = operational.build_plan(
            registry,
            remote_scope,
            json.loads(json.dumps(catalog)),
            version_ids=["altitude_v2"],
            profile_keys=["altitude_v2/common_idw"],
        )
        self.assertEqual(local_plan, remote_plan)
        self.assertEqual(local_plan, operational.validate_plan(json.loads(json.dumps(local_plan))))

    def test_scope_identity_ignores_volatile_features_artifact_metadata(self) -> None:
        rows = [
            _row("admitted", day, "ma-a", "favorable" if day == 1 else "unfavorable")
            for day in range(1, 11)
        ]
        local_scope = operational.build_scope(
            {
                "generated_at": "2026-08-28T10:08:29+00:00",
                "input_paths": {"weather": "/local/weather.json"},
                "output_paths": {"json": "/local/features.json"},
                "rows": rows,
            },
            self.known_sites,
        )
        remote_scope = operational.build_scope(
            {
                "generated_at": "2026-08-28T18:42:36+00:00",
                "input_paths": {"weather": "/share/weather.json"},
                "output_paths": {"json": "/share/features.json"},
                "rows": json.loads(json.dumps(rows)),
            },
            self.known_sites,
        )

        self.assertEqual(local_scope, remote_scope)

    def test_scope_identity_changes_when_a_scientific_feature_changes(self) -> None:
        rows = [
            _row("admitted", day, "ma-a", "favorable" if day == 1 else "unfavorable")
            for day in range(1, 11)
        ]
        changed_rows = json.loads(json.dumps(rows))
        changed_rows[0]["gis_altitude_m"] = 101.0

        original_scope = operational.build_scope({"rows": rows}, self.known_sites)
        changed_scope = operational.build_scope({"rows": changed_rows}, self.known_sites)

        self.assertNotEqual(
            original_scope["source_identity"]["features_sha256"],
            changed_scope["source_identity"]["features_sha256"],
        )
        self.assertNotEqual(original_scope["scope_id"], changed_scope["scope_id"])

    def test_scope_identity_ignores_known_sites_reconciliation_timestamps(self) -> None:
        rows = [
            _row("admitted", day, "ma-a", "favorable" if day == 1 else "unfavorable")
            for day in range(1, 11)
        ]
        local_sites = {
            **self.known_sites,
            "metadata": {"updated_at": "2026-08-27", "source": "field"},
            "areas": [
                {
                    "area_id": "area-a",
                    "altitude_m": 100.0,
                    "soilgrids": {"generated_at": "2026-08-27T22:44:11+00:00"},
                }
            ],
        }
        remote_sites = json.loads(json.dumps(local_sites))
        remote_sites["metadata"]["updated_at"] = "2026-08-28"
        remote_sites["areas"][0]["soilgrids"]["generated_at"] = (
            "2026-08-28T02:44:00+00:00"
        )

        local_scope = operational.build_scope({"rows": rows}, local_sites)
        remote_scope = operational.build_scope({"rows": rows}, remote_sites)
        self.assertEqual(local_scope, remote_scope)

        changed_sites = json.loads(json.dumps(remote_sites))
        changed_sites["areas"][0]["altitude_m"] = 101.0
        changed_scope = operational.build_scope({"rows": rows}, changed_sites)
        self.assertNotEqual(
            local_scope["source_identity"]["known_sites_sha256"],
            changed_scope["source_identity"]["known_sites_sha256"],
        )
        self.assertNotEqual(local_scope["scope_id"], changed_scope["scope_id"])

    def test_missing_tuning_is_rejected_while_building_plan(self) -> None:
        rows = [
            _row("admitted", day, "ma-a", "favorable" if day == 1 else "unfavorable")
            for day in range(1, 11)
        ]
        scope = operational.build_scope({"rows": rows}, self.known_sites)
        registry = mushroom_ml_version_registry.load_registry(REGISTRY_PATH)
        fit_plan = mushroom_ml_multiversion_plan.build_plan(
            registry,
            batch_id="operational_plan",
            snapshot_id=scope["scope_id"],
            generation_ids={"altitude_v2": "plan_altitude_v2"},
            species_ids=scope["admitted_species_ids"],
            version_ids=["altitude_v2"],
            profile_keys=["altitude_v2/common_idw"],
        )
        catalog = _catalog_for(registry, fit_plan)
        catalog["decisions"].pop()
        identity = {
            key: catalog[key]
            for key in (
                "compatibility_fingerprint",
                "source_batch_id",
                "source_snapshot_id",
                "decisions",
            )
        }
        catalog["catalog_id"] = "sha256:" + hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        with self.assertRaisesRegex(ValueError, "does not cover the plan"):
            operational.build_plan(
                registry,
                scope,
                catalog,
                version_ids=["altitude_v2"],
                profile_keys=["altitude_v2/common_idw"],
            )
