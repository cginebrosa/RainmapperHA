from __future__ import annotations

import unittest

import numpy as np

from rainmapper_core.mushroom_ml_reliability_audit import (
    AuditPolicy,
    _binary_roc_auc,
    audit_rows,
    build_quality_audit_catalog,
    build_selection_catalog,
    validate_quality_audit_catalog,
)


def _rows_for_candidate(
    *,
    version: str,
    probabilities: list[float],
    labels: list[int],
    area: str = "olvan",
    split: str = "fruiting_groups_14d",
    micro_areas: list[str] | None = None,
    temporal_contract_id: str = "lag_days_v1",
    horizon_days: int = 3,
) -> list[dict[str, object]]:
    return [
        {
            "version_id": version,
            "profile_id": "profile",
            "temporal_contract_id": temporal_contract_id,
            "horizon_days": horizon_days,
            "species_id": "boletus_aereus",
            "area_id": area,
            "micro_area_id": micro_areas[index] if micro_areas else "ignored",
            "split_id": split,
            "observation_id": f"observation-{index}",
            "validation_group_id": f"group-{index // 2}",
            "y_true": label,
            "train_prevalence_probability": 0.45,
            "estimator_probabilities": {"estimator": probabilities[index]},
        }
        for index, label in enumerate(labels)
    ]


def _day(report: dict[str, object], prediction_day: int = 3) -> dict[str, object]:
    scope = report["scopes"][0]  # type: ignore[index]
    return next(
        row
        for row in scope["operational_days"]  # type: ignore[index]
        if row["prediction_day"] == prediction_day
    )


class MushroomMLReliabilityAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = AuditPolicy()

    def test_binary_roc_auc_preserves_average_ranks_for_ties(self) -> None:
        y = np.asarray([0, 1, 0, 1], dtype=int)
        probabilities = np.asarray([0.1, 0.5, 0.5, 0.9], dtype=float)

        self.assertEqual(_binary_roc_auc(y, probabilities), 0.875)

    def test_wilson_ranking_prefers_broader_favorable_evidence(self) -> None:
        labels = [1] * 9 + [0] * 11
        broad = [0.8] * 8 + [0.5] + [0.7] + [0.5] * 10
        narrow = [0.8] * 4 + [0.5] * 5 + [0.5] * 11
        report = audit_rows(
            _rows_for_candidate(version="broad", probabilities=broad, labels=labels)
            + _rows_for_candidate(version="narrow", probabilities=narrow, labels=labels),
            policy=self.policy,
            include_stability=False,
        )

        winner = _day(report)["provisional_winner"]
        self.assertEqual(winner["candidate"]["version_id"], "broad")
        self.assertEqual(winner["true_favorable_count"], 8)
        self.assertEqual(winner["false_favorable_count"], 1)

    def test_species_winner_replaces_weaker_area_winner(self) -> None:
        """Territorial preference must not preserve weaker evidence."""
        olvan_labels = [1, 0, 0, 0]
        other_labels = [1, 1, 1, 0]
        rows = (
            _rows_for_candidate(
                version="area-specialist",
                probabilities=[0.8, 0.2, 0.2, 0.2],
                labels=olvan_labels,
            )
            + _rows_for_candidate(
                version="species-winner",
                probabilities=[0.8, 0.7, 0.2, 0.2],
                labels=olvan_labels,
            )
            + _rows_for_candidate(
                version="area-specialist",
                probabilities=[0.5, 0.5, 0.5, 0.2],
                labels=other_labels,
                area="other",
            )
            + _rows_for_candidate(
                version="species-winner",
                probabilities=[0.8, 0.8, 0.8, 0.2],
                labels=other_labels,
                area="other",
            )
        )
        report = audit_rows(
            rows,
            policy=self.policy,
            split_ids={"fruiting_groups_14d"},
            include_candidates=True,
            include_stability=False,
        )

        selections = build_selection_catalog(report)
        olvan = next(
            row
            for row in selections["species_area_selections"]
            if row["area_id"] == "olvan" and row["prediction_day"] == 3
        )

        self.assertEqual(olvan["selection_scope"], "species_fallback")
        self.assertEqual(olvan["candidate"]["version_id"], "species-winner")
        self.assertGreater(
            olvan["evidence_by_scope"]["species"][
                "wilson_lower_95_observations"
            ],
            olvan["evidence_by_scope"]["area"][
                "wilson_lower_95_observations"
            ],
        )
        self.assertEqual(
            selections["selection_policy"]["territorial_resolution_rule"],
            "highest_wilson_lower_95_between_area_and_species;ties_prefer_area",
        )
        audit_catalog = build_quality_audit_catalog(
            report,
            selections,
            snapshot_id="sha256:" + "b" * 64,
        )
        self.assertEqual(audit_catalog["selection_id"], selections["selection_id"])

    def test_groups_by_area_but_never_by_micro_area(self) -> None:
        labels = [1, 1, 0, 0, 1, 0, 1, 0]
        micro_areas = ["north", "south"] * 4
        rows = _rows_for_candidate(
            version="candidate",
            probabilities=[0.8, 0.7, 0.2, 0.3, 0.8, 0.2, 0.7, 0.3],
            labels=labels,
            micro_areas=micro_areas,
        )

        report = audit_rows(rows, policy=self.policy, include_stability=False)

        self.assertEqual(report["territorial_granularity"], "area_id")
        self.assertEqual(report["scoring_unit"], "observation_id")
        self.assertEqual(
            report["official_selection_split_id"], "fruiting_groups_14d"
        )
        self.assertEqual(
            report["validation_group_role"], "diagnostic_only_not_ranking_or_gate"
        )
        self.assertEqual(report["scope_count"], 1)
        self.assertEqual(
            _day(report)["provisional_winner"]["observation_count"], 8
        )

    def test_group_stability_is_diagnostic_and_does_not_replace_observations(self) -> None:
        labels = [1, 1, 1, 1, 0, 0, 0, 0]
        rows = _rows_for_candidate(
            version="candidate",
            probabilities=[0.8, 0.8, 0.8, 0.8, 0.2, 0.2, 0.2, 0.2],
            labels=labels,
        )
        for row in rows:
            row["validation_group_id"] = "same-temporal-group"

        report = audit_rows(rows, policy=self.policy)

        day = _day(report)
        self.assertEqual(day["provisional_winner"]["observation_count"], 8)
        self.assertEqual(day["provisional_winner"]["validation_group_count"], 1)
        self.assertIsNotNone(day["provisional_winner"])
        self.assertEqual(day["stability"]["same_winner_rate"], 0.0)

    def test_never_combines_splits(self) -> None:
        labels = [1, 1, 0, 0, 1, 0, 1, 0]
        probabilities = [0.8, 0.7, 0.2, 0.3, 0.8, 0.2, 0.7, 0.3]
        report = audit_rows(
            _rows_for_candidate(
                version="candidate-7d",
                probabilities=probabilities,
                labels=labels,
                split="fruiting_groups_7d",
            )
            + _rows_for_candidate(
                version="candidate-14d",
                probabilities=probabilities,
                labels=labels,
                split="fruiting_groups_14d",
            ),
            policy=self.policy,
            include_stability=False,
        )

        self.assertEqual(report["scope_count"], 2)
        self.assertEqual(
            report["audited_split_ids"], ["fruiting_groups_14d", "fruiting_groups_7d"]
        )
        self.assertTrue(report["warnings"])

    def test_has_no_arbitrary_sample_recall_or_auc_gate(self) -> None:
        rows = _rows_for_candidate(
            version="small-but-valid",
            probabilities=[0.6, 0.6, 0.4, 0.4],
            labels=[1, 0, 1, 0],
        )
        for row in rows:
            row["train_prevalence_probability"] = 0.05

        report = audit_rows(rows, policy=self.policy, include_stability=False)

        winner = _day(report)["provisional_winner"]
        self.assertEqual(winner["observation_count"], 4)
        self.assertEqual(winner["favorable_call_count"], 2)
        self.assertEqual(winner["favorable_recall"], 0.5)
        self.assertEqual(winner["roc_auc"], 0.5)

    def test_requires_a_favorable_call_and_brier_improvement(self) -> None:
        labels = [1, 1, 0, 0]
        rows = _rows_for_candidate(
            version="never-go",
            probabilities=[0.5, 0.5, 0.2, 0.2],
            labels=labels,
        ) + _rows_for_candidate(
            version="worse-than-baseline",
            probabilities=[0.9, 0.9, 0.9, 0.9],
            labels=labels,
        )

        report = audit_rows(
            rows,
            policy=self.policy,
            include_candidates=True,
            include_stability=False,
        )

        scope = _day(report)
        self.assertIsNone(scope["provisional_winner"])
        reasons = {
            candidate["candidate"]["version_id"]: candidate["exclusion_reasons"]
            for candidate in scope["candidates"]
        }
        self.assertIn("no_favorable_calls", reasons["never-go"])
        self.assertIn("not_better_than_prevalence", reasons["worse-than-baseline"])

    def test_selects_the_population_shared_by_most_candidates(self) -> None:
        labels = [1, 1, 0, 0]
        common = _rows_for_candidate(
            version="common-a",
            probabilities=[0.8, 0.7, 0.2, 0.3],
            labels=labels,
        ) + _rows_for_candidate(
            version="common-b",
            probabilities=[0.7, 0.6, 0.3, 0.2],
            labels=labels,
        )
        rogue = _rows_for_candidate(
            version="rogue-larger-population",
            probabilities=[0.9, 0.8, 0.2, 0.1, 0.8],
            labels=labels + [1],
        )

        report = audit_rows(
            common + rogue,
            policy=self.policy,
            include_candidates=True,
            include_stability=False,
        )

        scope = _day(report)
        self.assertEqual(scope["population"]["selected_population_candidate_count"], 2)
        reasons = {
            candidate["candidate"]["version_id"]: candidate["exclusion_reasons"]
            for candidate in scope["candidates"]
        }
        self.assertIn(
            "incomparable_population", reasons["rogue-larger-population"]
        )

    def test_rejects_non_finite_or_out_of_range_probabilities(self) -> None:
        rows = _rows_for_candidate(
            version="invalid",
            probabilities=[float("nan"), 0.2],
            labels=[1, 0],
        )

        with self.assertRaisesRegex(ValueError, "must be finite and between 0 and 1"):
            audit_rows(rows, policy=self.policy)

    def test_rejects_duplicate_observation_for_same_candidate(self) -> None:
        labels = [1, 1, 0, 0, 1, 0, 1, 0]
        rows = _rows_for_candidate(
            version="candidate",
            probabilities=[0.8, 0.7, 0.2, 0.3, 0.8, 0.2, 0.7, 0.3],
            labels=labels,
        )
        rows.append(dict(rows[0]))

        with self.assertRaisesRegex(ValueError, "duplicate candidate/evaluation case"):
            audit_rows(rows, policy=self.policy)

    def test_selects_each_prediction_day_without_retargeting_lag_candidate(self) -> None:
        labels = [1, 1, 1, 1, 0, 0, 0, 0]
        fixed = _rows_for_candidate(
            version="fixed",
            probabilities=[0.8, 0.8, 0.5, 0.5, 0.2, 0.2, 0.5, 0.5],
            labels=labels,
            temporal_contract_id="fixed_gap_7d_test_v1",
            horizon_days=7,
        )
        lag_h1 = _rows_for_candidate(
            version="lag-h1",
            probabilities=[0.8, 0.8, 0.8, 0.8, 0.2, 0.2, 0.2, 0.2],
            labels=labels,
            temporal_contract_id="lag_event_test_v1",
            horizon_days=1,
        )
        lag_h2 = _rows_for_candidate(
            version="lag-h2",
            probabilities=[0.8, 0.8, 0.8, 0.5, 0.2, 0.2, 0.2, 0.5],
            labels=labels,
            temporal_contract_id="lag_event_test_v1",
            horizon_days=2,
        )

        report = audit_rows(
            fixed + lag_h1 + lag_h2,
            policy=self.policy,
            include_candidates=True,
            include_stability=False,
        )

        day_1 = _day(report, 1)
        day_2 = _day(report, 2)
        day_3 = _day(report, 3)
        self.assertEqual(
            day_1["provisional_winner"]["candidate"]["version_id"], "lag-h1"
        )
        self.assertEqual(
            day_2["provisional_winner"]["candidate"]["version_id"], "lag-h2"
        )
        self.assertEqual(
            day_3["provisional_winner"]["candidate"]["version_id"], "fixed"
        )
        self.assertNotIn(
            "lag-h1",
            {
                row["candidate"]["version_id"]
                for row in day_2["candidates"]
            },
        )
        self.assertEqual(report["prediction_days"], list(range(1, 8)))

    def test_preserves_exact_temporal_contract_identity(self) -> None:
        rows = _rows_for_candidate(
            version="candidate",
            probabilities=[0.8, 0.8, 0.2, 0.2],
            labels=[1, 1, 0, 0],
            temporal_contract_id="lag_event_biology_v3_exact",
            horizon_days=4,
        )

        report = audit_rows(rows, policy=self.policy, include_stability=False)

        candidate = _day(report, 4)["provisional_winner"]["candidate"]
        self.assertEqual(
            candidate["temporal_contract_id"], "lag_event_biology_v3_exact"
        )
        self.assertEqual(candidate["temporal_family"], "lag")

    def test_rejects_unknown_or_inconsistent_temporal_contract(self) -> None:
        unknown = _rows_for_candidate(
            version="candidate",
            probabilities=[0.8, 0.2],
            labels=[1, 0],
            temporal_contract_id="other_contract",
        )
        with self.assertRaisesRegex(ValueError, "unsupported temporal_contract_id"):
            audit_rows(unknown, policy=self.policy)

        inconsistent_fixed = _rows_for_candidate(
            version="candidate",
            probabilities=[0.8, 0.2],
            labels=[1, 0],
            temporal_contract_id="fixed_gap_test",
            horizon_days=3,
        )
        with self.assertRaisesRegex(ValueError, "requires horizon_days=7"):
            audit_rows(inconsistent_fixed, policy=self.policy)

    def test_extended_catalog_keeps_all_candidates_and_matches_compact_winner(self) -> None:
        labels = [1, 1, 1, 1, 0, 0, 0, 0]
        rows = _rows_for_candidate(
            version="winner",
            probabilities=[0.8, 0.8, 0.8, 0.8, 0.2, 0.2, 0.2, 0.2],
            labels=labels,
            temporal_contract_id="fixed_gap_7d_test",
            horizon_days=7,
        ) + _rows_for_candidate(
            version="alternative",
            probabilities=[0.8, 0.5, 0.5, 0.5, 0.2, 0.2, 0.2, 0.2],
            labels=labels,
            temporal_contract_id="fixed_gap_7d_test",
            horizon_days=7,
        )
        report = audit_rows(
            rows,
            policy=self.policy,
            split_ids={"fruiting_groups_14d"},
            top=1,
            include_candidates=True,
        )
        selections = build_selection_catalog(report)
        first_resolution = selections["species_area_selections"][0]
        self.assertEqual(first_resolution["selection_scope"], "area")
        self.assertEqual(
            first_resolution["evidence_by_scope"]["area"]["candidate"],
            first_resolution["evidence_by_scope"]["species"]["candidate"],
        )
        self.assertEqual(
            first_resolution["evidence_by_scope"]["area"]["candidate"],
            first_resolution["candidate"],
        )
        self.assertEqual(
            [
                row["candidate"]["version_id"]
                for row in first_resolution["candidate_chain"]
            ],
            ["winner", "alternative"],
        )
        self.assertEqual(
            first_resolution["candidate_chain"][0]["evidence"],
            first_resolution["evidence"],
        )

        catalog = build_quality_audit_catalog(
            report,
            selections,
            snapshot_id="sha256:" + "a" * 64,
        )

        self.assertEqual(catalog["selection_id"], selections["selection_id"])
        self.assertEqual(catalog["counts"]["area_scopes"], 1)
        self.assertEqual(catalog["counts"]["area_evaluations"], 2)
        scope = catalog["area_scopes"][0]
        self.assertEqual(len(scope["evaluations"]), 2)
        self.assertEqual(len(scope["operational_days"]), 7)
        first_day = scope["operational_days"][0]
        selected = next(
            row
            for row in scope["evaluations"]
            if row["candidate_id"] == first_day["selected_candidate_id"]
        )
        self.assertEqual(selected["candidate"]["version_id"], "winner")

        first_day["selected_candidate_id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "rank one"):
            validate_quality_audit_catalog(catalog, selections=selections)


if __name__ == "__main__":
    unittest.main()
