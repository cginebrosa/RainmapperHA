import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core import mushroom_ml_quality_catalog as quality


class MushroomMLQualityCatalogTests(TestCase):
    def test_bundle_builds_matching_compact_and_extended_catalogs(self) -> None:
        rows = [
            {
                "version_id": "biology_v4",
                "profile_id": "extended_weather",
                "species_id": "species_a",
                "area_id": "area_a",
                "split_id": "fruiting_groups_14d",
                "temporal_contract_id": "fixed_gap_7d_biology_v4",
                "horizon_days": 7,
                "observation_id": f"observation-{index}",
                "validation_group_id": f"group-{index // 2}",
                "y_true": index % 2,
                "train_prevalence_probability": 0.5,
                "estimator_probabilities": {
                    "estimator_a": 0.8 if index % 2 else 0.2
                },
            }
            for index in range(8)
        ]
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "v2-v5.jsonl"
            first.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            second = root / "v6.jsonl"
            second.write_text("", encoding="utf-8")
            compact, audit = quality.build_catalog_bundle(
                first,
                second,
                snapshot_id="sha256:" + "f" * 64,
                profile_keys=["biology_v4/extended_weather"],
                expected_estimators={
                    "biology_v4/extended_weather": ["estimator_a"]
                },
            )

        self.assertEqual(audit["selection_id"], compact["selection_id"])
        self.assertEqual(audit["counts"]["area_evaluations"], 1)
        self.assertEqual(audit["counts"]["area_days"], 7)

    def test_keeps_species_and_scenarios_separate(self) -> None:
        rows = []
        for species_id, probabilities in (("species_a", [0.1, 0.9] * 4), ("species_b", [0.6, 0.4] * 4)):
            for index, probability in enumerate(probabilities):
                rows.append({
                    "version_id": "altitude_v2", "profile_id": "common_idw",
                    "species_id": species_id, "temporal_contract_id": "lag_event_altitude_v2",
                    "split_id": "fruiting_groups_7d",
                    "horizon_days": 1, "y_true": index % 2,
                    "train_prevalence_probability": 0.5,
                    "estimator_probabilities": {"logistic_regression_reduced_v1": probability},
                })
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "v2-v5.jsonl"
            first.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            second = root / "v6.jsonl"
            second.write_text("", encoding="utf-8")
            result = quality.build_catalog(first, second, snapshot_id="sha256:" + "a" * 64)

        self.assertEqual(len(result["entries"]), 2)
        self.assertTrue(result["species_metrics_are_never_averaged"])
        evidence = {row["species_id"]: row["evidence"] for row in result["entries"]}
        self.assertEqual(evidence["species_a"], "better_than_prevalence")
        self.assertEqual(evidence["species_b"], "worse_than_prevalence")
        classification = {
            row["species_id"]: row["operational_classification"]
            for row in result["entries"]
        }
        self.assertEqual(
            classification["species_a"],
            {
                "evaluated_count": 8,
                "true_favorable_count": 4,
                "false_favorable_count": 0,
                "true_unfavorable_count": 4,
                "false_unfavorable_count": 0,
                "uncertain_count": 0,
            },
        )
        self.assertEqual(classification["species_b"]["false_favorable_count"], 4)
        self.assertEqual(classification["species_b"]["false_unfavorable_count"], 4)

    def test_lookup_requires_exact_species_contract_horizon_and_estimator(self) -> None:
        catalog = {"split_id": "fruiting_groups_7d", "entries": [{
            "split_id": "fruiting_groups_7d",
            "version_id": "biology_v3", "profile_id": "core",
            "temporal_contract_id": "lag_event_biology_v3", "temporal_family": "lag",
            "horizon_days": 3, "species_id": "boletus_edulis",
            "estimator_id": "random_forest_restricted_v1", "evidence": "better_than_prevalence",
        }]}
        found = quality.lookup(catalog, {
            "version_id": "biology_v3", "profile_id": "core",
            "temporal_contract_id": "lag_event_biology_v3", "horizon_days": 3,
            "species_id": "boletus_edulis", "estimator_id": "random_forest_restricted_v1",
        })
        missing = quality.lookup(catalog, {
            "version_id": "biology_v3", "profile_id": "core",
            "temporal_contract_id": "lag_event_biology_v3", "horizon_days": 7,
            "species_id": "boletus_edulis", "estimator_id": "random_forest_restricted_v1",
        })
        wrong_contract = quality.lookup(catalog, {
            "version_id": "biology_v3", "profile_id": "core",
            "temporal_contract_id": "lag_event_other_contract", "horizon_days": 3,
            "species_id": "boletus_edulis", "estimator_id": "random_forest_restricted_v1",
        })
        self.assertEqual(found["evidence"], "better_than_prevalence")
        self.assertEqual(missing["evidence"], "not_evaluated")
        self.assertEqual(wrong_contract["evidence"], "not_evaluated")

    def test_reports_calibration_support_and_estimator_abstentions(self) -> None:
        rows = [
            {
                "version_id": "biology_v3",
                "profile_id": "core",
                "species_id": "species_a",
                "split_id": "fruiting_groups_7d",
                "temporal_contract_id": "fixed_gap_7d_biology_v3",
                "horizon_days": 7,
                "y_true": index % 2,
                "train_prevalence_probability": 0.5,
                "estimator_probabilities": (
                    {"estimator_a": 0.8 if index % 2 else 0.2}
                    if index != 3
                    else {}
                ),
            }
            for index in range(10)
        ]
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "v2-v5.jsonl"
            first.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            second = root / "v6.jsonl"
            second.write_text("", encoding="utf-8")
            result = quality.build_catalog(
                first,
                second,
                snapshot_id="sha256:" + "b" * 64,
                profile_keys=["biology_v3/core"],
                expected_estimators={"biology_v3/core": ["estimator_a", "estimator_b"]},
            )

        entries = {row["estimator_id"]: row for row in result["entries"]}
        self.assertEqual(entries["estimator_a"]["n_test_total"], 10)
        self.assertEqual(entries["estimator_a"]["abstention_count"], 1)
        self.assertIsNotNone(entries["estimator_a"]["expected_calibration_error"])
        self.assertTrue(entries["estimator_a"]["calibration_bins"])
        self.assertEqual(entries["estimator_b"]["n_test"], 0)
        self.assertEqual(entries["estimator_b"]["abstention_count"], 10)

    def test_never_aggregates_rows_from_different_splits(self) -> None:
        rows = []
        for split_id, favorable_probability in (
            ("fruiting_groups_7d", 0.8),
            ("fruiting_groups_14d", 0.7),
        ):
            for index in range(8):
                label = index % 2
                rows.append(
                    {
                        "version_id": "biology_v3",
                        "profile_id": "core",
                        "species_id": "species_a",
                        "split_id": split_id,
                        "temporal_contract_id": "lag_event_biology_v3",
                        "horizon_days": 1,
                        "area_id": "area_a",
                        "observation_id": f"{split_id}-observation-{index}",
                        "validation_group_id": f"{split_id}-group-{index // 2}",
                        "y_true": label,
                        "train_prevalence_probability": 0.5,
                        "estimator_probabilities": {
                            "estimator_a": favorable_probability if label else 0.2
                        },
                    }
                )
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "v2-v5.jsonl"
            first.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            second = root / "v6.jsonl"
            second.write_text("", encoding="utf-8")

            result = quality.build_catalog(
                first, second, snapshot_id="sha256:" + "c" * 64
            )

        self.assertEqual(result["split_ids"], ["fruiting_groups_14d", "fruiting_groups_7d"])
        self.assertEqual(result["split_id"], "fruiting_groups_7d")
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(len(result["alternate_split_entries"]), 1)
        all_entries = result["entries"] + result["alternate_split_entries"]
        self.assertEqual({row["n_test"] for row in all_entries}, {8})
        by_split = {row["split_id"]: row for row in all_entries}
        self.assertNotEqual(
            by_split["fruiting_groups_7d"]["brier_score"],
            by_split["fruiting_groups_14d"]["brier_score"],
        )
        model_ref = {
            "version_id": "biology_v3",
            "profile_id": "core",
            "temporal_contract_id": "lag_event_biology_v3",
            "horizon_days": 1,
            "species_id": "species_a",
            "estimator_id": "estimator_a",
        }
        self.assertEqual(
            quality.lookup(result, model_ref)["split_id"], "fruiting_groups_7d"
        )
        self.assertEqual(
            quality.lookup(result, model_ref, split_id="fruiting_groups_14d")["split_id"],
            "fruiting_groups_14d",
        )

    def test_rejects_holdout_rows_without_split_id(self) -> None:
        row = {
            "version_id": "biology_v3",
            "profile_id": "core",
            "species_id": "species_a",
            "temporal_contract_id": "lag_event_biology_v3",
            "horizon_days": 1,
            "y_true": 1,
            "train_prevalence_probability": 0.5,
            "estimator_probabilities": {"estimator_a": 0.8},
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "v2-v5.jsonl"
            first.write_text(json.dumps(row) + "\n", encoding="utf-8")
            second = root / "v6.jsonl"
            second.write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing split_id"):
                quality.build_catalog(
                    first, second, snapshot_id="sha256:" + "d" * 64
                )

    def test_builds_and_validates_sealed_area_and_species_fallbacks(self) -> None:
        rows = []
        for area_id, labels in (
            ("area_with_both_classes", [1, 1, 0, 0]),
            ("area_with_one_class", [1, 1, 1, 1]),
        ):
            for index, label in enumerate(labels):
                rows.append(
                    {
                        "version_id": "biology_v4",
                        "profile_id": "extended_weather",
                        "species_id": "species_a",
                        "area_id": area_id,
                        "split_id": "fruiting_groups_14d",
                        "temporal_contract_id": "fixed_gap_7d_biology_v4",
                        "horizon_days": 7,
                        "observation_id": f"{area_id}-observation-{index}",
                        "validation_group_id": f"{area_id}-group-{index // 2}",
                        "y_true": label,
                        "train_prevalence_probability": 0.5,
                        "estimator_probabilities": {
                            "logistic_regression_reduced_v1": 0.8 if label else 0.2
                        },
                    }
                )
        for index, label in enumerate([1, 1, 0, 0]):
            rows.append(
                {
                    "version_id": "biology_v4",
                    "profile_id": "extended_weather",
                    "species_id": "species_a",
                    "area_id": "area_without_official_split",
                    "split_id": "fruiting_groups_7d",
                    "temporal_contract_id": "fixed_gap_7d_biology_v4",
                    "horizon_days": 7,
                    "observation_id": f"other-split-observation-{index}",
                    "validation_group_id": f"other-split-group-{index // 2}",
                    "y_true": label,
                    "train_prevalence_probability": 0.5,
                    "estimator_probabilities": {
                        "logistic_regression_reduced_v1": 0.8 if label else 0.2
                    },
                }
            )
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "v2-v5.jsonl"
            first.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            second = root / "v6.jsonl"
            second.write_text("", encoding="utf-8")
            first_catalog = quality.build_catalog(
                first,
                second,
                snapshot_id="sha256:" + "e" * 64,
                profile_keys=["biology_v4/extended_weather"],
                expected_estimators={
                    "biology_v4/extended_weather": [
                        "logistic_regression_reduced_v1"
                    ]
                },
            )
            second_catalog = quality.build_catalog(
                first,
                second,
                snapshot_id="sha256:" + "e" * 64,
                profile_keys=["biology_v4/extended_weather"],
                expected_estimators={
                    "biology_v4/extended_weather": [
                        "logistic_regression_reduced_v1"
                    ]
                },
            )

        checked = quality.validate_catalog(first_catalog, require_selections=True)
        self.assertEqual(checked["selection_schema_version"], "1.2")
        self.assertEqual(checked["selection_status"], "complete")
        self.assertEqual(checked["selection_counts"]["species_area_days"], 21)
        self.assertEqual(checked["selection_counts"]["area_winners"], 0)
        self.assertEqual(checked["selection_counts"]["species_fallbacks"], 21)
        self.assertEqual(first_catalog["selection_id"], second_catalog["selection_id"])
        fallback_rows = [
            row
            for row in checked["species_area_selections"]
            if row["area_id"]
            in {"area_with_one_class", "area_without_official_split"}
        ]
        self.assertEqual(
            {row["selection_scope"] for row in fallback_rows},
            {"species_fallback"},
        )
        self.assertTrue(
            all(
                row["evidence"]["observation_count"] == 8
                and row["evidence"]["validation_group_count"] == 4
                and row["evidence_by_scope"]["species"]["observation_count"] == 8
                for row in fallback_rows
            )
        )
        one_class = next(
            row
            for row in fallback_rows
            if row["area_id"] == "area_with_one_class"
        )
        self.assertIsNotNone(one_class["evidence_by_scope"]["area"])
        self.assertFalse(one_class["evidence_by_scope"]["area"]["eligible"])
        no_official_split = next(
            row
            for row in fallback_rows
            if row["area_id"] == "area_without_official_split"
        )
        self.assertIsNone(no_official_split["evidence_by_scope"]["area"])
        direct = next(
            row
            for row in checked["species_area_selections"]
            if row["area_id"] == "area_with_both_classes"
        )
        self.assertEqual(direct["selection_scope"], "species_fallback")
        self.assertTrue(direct["evidence_by_scope"]["area"]["eligible"])
        self.assertIsNotNone(direct["evidence_by_scope"]["species"])

        tampered = json.loads(json.dumps(first_catalog))
        tampered["species_area_selections"][0]["candidate"]["horizon_days"] = 1
        with self.assertRaisesRegex(ValueError, "candidate identity"):
            quality.validate_catalog(tampered, require_selections=True)

        obsolete = json.loads(json.dumps(first_catalog))
        obsolete["selection_schema_version"] = "1.1"
        with self.assertRaisesRegex(ValueError, "selection schema"):
            quality.validate_catalog(obsolete, require_selections=True)

        tampered_evidence = json.loads(json.dumps(first_catalog))
        direct_row = next(
            row
            for row in tampered_evidence["species_area_selections"]
            if row["selection_scope"] == "species_fallback"
        )
        direct_row["evidence_by_scope"]["species"]["observation_count"] += 1
        with self.assertRaisesRegex(ValueError, "scoped evidence is inconsistent"):
            quality.validate_catalog(tampered_evidence, require_selections=True)
