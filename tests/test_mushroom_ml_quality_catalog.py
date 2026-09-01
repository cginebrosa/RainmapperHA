import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core import mushroom_ml_quality_catalog as quality


class MushroomMLQualityCatalogTests(TestCase):
    def test_keeps_species_and_scenarios_separate(self) -> None:
        rows = []
        for species_id, probabilities in (("species_a", [0.1, 0.9] * 4), ("species_b", [0.6, 0.4] * 4)):
            for index, probability in enumerate(probabilities):
                rows.append({
                    "version_id": "altitude_v2", "profile_id": "common_idw",
                    "species_id": species_id, "temporal_contract_id": "lag_event_altitude_v2",
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
        catalog = {"entries": [{
            "version_id": "biology_v3", "profile_id": "core", "temporal_family": "lag",
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
        self.assertEqual(found["evidence"], "better_than_prevalence")
        self.assertEqual(missing["evidence"], "not_evaluated")

    def test_reports_calibration_support_and_estimator_abstentions(self) -> None:
        rows = [
            {
                "version_id": "biology_v3",
                "profile_id": "core",
                "species_id": "species_a",
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
