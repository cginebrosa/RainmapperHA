"""Small synthetic checks; no study artifacts are deserialized or predicted."""
from copy import deepcopy
from datetime import date, timedelta
import unittest
from unittest.mock import patch

from scripts.prediction_model_selection import ranking as r


KEY = "altitude_v2|fixed_gap_7d_altitude_v2|common_idw"
ESTIMATORS = {"altitude_v2/common_idw": ["first", "second"]}


def fixture():
    specs = [
        ("fit-a", "boletus_aereus", "2020-06-01", 1, "fit"),
        ("fit-other", "other_species", "2020-07-01", 0, "fit"),
        ("rank-a", "boletus_aereus", "2022-06-01", 0, "ranking"),
        ("recent-a", "boletus_aereus", "2023-06-01", 1, "threshold"),
        ("external-a", "boletus_aereus", "2024-06-01", 0, "external"),
    ]
    rows, samples, roles = [], [], {}
    for identity, species, day, y, role in specs:
        rows.append({"observation_id": identity, "species_id": species, "area_id": "area",
            "micro_area_id": None, "date": day, "y": y, "episode_id": identity})
        roles[identity] = role
        samples.append({"sample_id": identity, "prediction_target": "favorable" if y else "unfavorable",
            "predictive_features": {"temperature": 12., "rain": None},
            "quality": {"training_eligible": True, "training_exclusion_reasons": []},
            "metadata": {"observation_id": identity, "species_id": species, "area_id": "area",
                "micro_area_id": None, "target_date": day,
                "cutoff_date": (date.fromisoformat(day) - timedelta(days=7)).isoformat(),
                "horizon_days": 7, "research_episode_id": identity}})
    return {"samples": samples}, {"rows": rows, "folds": {"2024": roles}}


class RankingEvidenceTests(unittest.TestCase):
    def test_same_fold_partition_includes_all_training_species_but_no_recent_or_external(self):
        benchmark, cohort = fixture()
        train, recent = r.old_train.partition_samples(benchmark, cohort, 2024, "threshold")
        self.assertEqual({s["sample_id"] for s in train}, {"fit-a", "fit-other", "rank-a"})
        self.assertEqual([s["sample_id"] for s in recent], ["recent-a"])
        cohort["rows"][1]["episode_id"] = "recent-a"
        with self.assertRaisesRegex(AssertionError, "Cross-species episode"):
            r.old_train.partition_samples(benchmark, cohort, 2024, "threshold")

    def test_prevalence_uses_own_species_fit_and_ranking_not_evaluation_labels(self):
        benchmark, cohort = fixture()
        train, recent = r.old_train.partition_samples(benchmark, cohort, 2024, "threshold")
        row = r.evidence_rows(KEY, train, recent)[0]
        self.assertEqual(row["train_prevalence_probability"], .5)
        recent[0]["prediction_target"] = "unfavorable"
        changed = r.evidence_rows(KEY, train, recent)[0]
        self.assertEqual(changed["train_prevalence_probability"], .5)
        self.assertEqual(changed["y_true"], 0)
        old_train, old_test = r.old_train.partition_samples(benchmark, cohort, 2024, "ranking")
        self.assertEqual(r.evidence_rows(KEY, old_train, old_test)[0]["train_prevalence_probability"], 1.)

    def test_metadata_checks_full_coverage_label_date_group_and_cutoff(self):
        benchmark, cohort = fixture()
        r.validate_samples(benchmark, KEY, cohort)
        for field, value in (("species_id", "wrong"), ("target_date", "2020-06-02"),
                             ("research_episode_id", "wrong"), ("cutoff_date", "2020-06-01")):
            changed = deepcopy(benchmark)
            changed["samples"][0]["metadata"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                r.validate_samples(changed, KEY, cohort)
        for modification in ("label", "duplicate", "missing"):
            changed = deepcopy(benchmark)
            if modification == "label":
                changed["samples"][0]["prediction_target"] = "unfavorable"
            elif modification == "duplicate":
                changed["samples"].append(changed["samples"][0])
            else:
                changed["samples"].pop()
            with self.subTest(modification=modification), self.assertRaises(ValueError):
                r.validate_samples(changed, KEY, cohort)

    def test_predictor_receives_only_features_and_species_and_retains_explicit_null(self):
        samples = fixture()[0]["samples"][:1]
        columns = ["temperature", "rain"]
        bundle = {"feature_cols": columns}
        with patch.object(r.inference, "predict_bundle_many", return_value=[{"probability": .25}]) as predictor:
            self.assertEqual(r.predict_rows(bundle, samples, columns), [{"probability": .25}])
            predictor.assert_called_once_with(bundle, [{"temperature": 12., "rain": None}],
                                               species_ids=["boletus_aereus"])
            del samples[0]["predictive_features"]["rain"]
            with self.assertRaisesRegex(ValueError, "required feature key"):
                r.predict_rows(bundle, samples, columns)
            self.assertEqual(predictor.call_count, 1)

    def test_missing_predictions_or_different_columns_stop(self):
        samples = fixture()[0]["samples"][:1]
        with patch.object(r.inference, "predict_bundle_many", return_value=[]):
            with self.assertRaisesRegex(ValueError, "count mismatch"):
                r.predict_rows({"feature_cols": ["rain"]}, samples, ["rain"])
            with self.assertRaisesRegex(ValueError, "columns differ"):
                r.predict_rows({"feature_cols": ["rain"]}, samples, ["temperature"])

    def test_evidence_requires_every_candidate_and_disallows_duplicates_or_external_rows(self):
        benchmark, cohort = fixture()
        train, test = r.old_train.partition_samples(benchmark, cohort, 2024, "threshold")
        expected = r.evidence_rows(KEY, train, test)
        rows = deepcopy(expected)
        rows[0]["estimator_probabilities"] = {"first": .1, "second": .9}
        r.validate_evidence(rows, expected, ESTIMATORS)
        for mutation in ("missing", "duplicate", "identity", "prevalence", "nan", "boolean"):
            changed = deepcopy(rows)
            if mutation == "missing":
                del changed[0]["estimator_probabilities"]["second"]
            elif mutation == "duplicate":
                changed.append(changed[0])
            elif mutation == "identity":
                changed[0]["row_key"] = "external"
            elif mutation == "prevalence":
                changed[0]["train_prevalence_probability"] = 1.
            else:
                changed[0]["estimator_probabilities"]["first"] = float("nan") if mutation == "nan" else True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                r.validate_evidence(changed, expected, ESTIMATORS)

    def test_only_three_physical_exclusions_are_allowed_in_2025(self):
        exclusions = {}
        for contract, horizons in (("fixed_gap_7d", [7]), ("lag_event", range(1, 8))):
            key = f"biology_v3|{contract}_biology_v3|{r.PHYSICAL_PROFILE}"
            exclusions[key] = [{"metadata": {"observation_id": str(i), "species_id": "amanita_caesarea"},
                "quality": {"training_exclusion_reasons": [
                    {"code": "v3_physical_soil_state_unavailable", "message": "El estado hídrico/SMI declarado para V3+ no está disponible."},
                    {"code": "v3_physical_features_missing", "message": "Faltan variables V3+."},
                ]}} for i in range(3) for _ in horizons]
        r.validate_exclusions(exclusions, 2025)
        for year in (2024, 2026):
            r.validate_exclusions({}, year)
            with self.assertRaises(ValueError):
                r.validate_exclusions(exclusions, year)
        changed = deepcopy(exclusions)
        next(iter(changed.values()))[0]["quality"]["training_exclusion_reasons"][0]["code"] = "new reason"
        with self.assertRaisesRegex(ValueError, "reason"):
            r.validate_exclusions(changed, 2025)

    def test_bundle_requires_fit_plus_ranking_and_initial_tuning(self):
        benchmark, cohort = fixture()
        train, _ = r.old_train.partition_samples(benchmark, cohort, 2024, "threshold")
        reference = r.catalog.ModelArtifactRef.from_mapping({"batch_id": "research_2024_threshold",
            "generation_id": "g", "version_id": "altitude_v2", "temporal_contract_id": "fixed_gap_7d_altitude_v2",
            "profile_id": "common_idw", "estimator_id": "first", "species_id": "all_species"})
        bundle = {"schema_version": "1.0", "kind": "mushroom_ml_runtime_model", "snapshot_id": "snapshot",
            "training_row_count": 3, "training_species_ids": ["boletus_aereus", "other_species"],
            "feature_cols": ["rain"], "fit_config": {"C": .1}}
        event = {"training_rows": 3, "training_observations": 3, "training_species_ids": bundle["training_species_ids"]}
        summary = {"decisions": {r.tuning.decision_key(reference.as_dict()): {"fit_config": {"C": .1}}}}
        with patch.object(r.trainer, "_columns", return_value=["rain"]):
            r.validate_bundle(bundle, reference, benchmark, train, event, summary, summary, "snapshot")
            bundle["training_row_count"] = 4
            with self.assertRaisesRegex(ValueError, "training scope"):
                r.validate_bundle(bundle, reference, benchmark, train, event, summary, summary, "snapshot")
            bundle["training_row_count"] = 3
            bundle["fit_config"] = {"C": 1.}
            with self.assertRaisesRegex(ValueError, "tuning"):
                r.validate_bundle(bundle, reference, benchmark, train, event, summary, summary, "snapshot")


if __name__ == "__main__":
    unittest.main()
