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
