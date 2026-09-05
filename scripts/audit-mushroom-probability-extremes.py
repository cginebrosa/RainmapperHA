#!/usr/bin/env python3
"""Audit extreme mushroom probabilities on archived external hold-out rows.

This command is read-only with respect to models and observations.  It expands
the estimator probabilities stored by the benchmark and reports calibration
for every candidate and for the candidates selected by the sealed reliability
catalog.  Candidate identities are de-duplicated so a fixed-window model used
on several forecast days is counted only once per observation.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rainmapper_core.mushroom_ml_reliability_audit import (
    AuditPolicy,
    audit_rows,
    build_selection_catalog,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", required=True, type=Path)
    parser.add_argument("--quality-catalog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _candidate_key(
    row: Mapping[str, Any], estimator_id: str, *, include_species: bool = True
) -> tuple[object, ...]:
    key: tuple[object, ...] = (
        str(row.get("version_id") or ""),
        str(row.get("profile_id") or ""),
        str(row.get("temporal_contract_id") or ""),
        int(row.get("horizon_days") or 0),
        str(estimator_id),
    )
    return key + (str(row.get("species_id") or ""),) if include_species else key


def _selected_keys(
    selections: Iterable[object],
) -> set[tuple[object, ...]]:
    selected: set[tuple[object, ...]] = set()
    for selection in selections:
        if not isinstance(selection, Mapping):
            continue
        candidate = selection.get("candidate")
        if not isinstance(candidate, Mapping):
            continue
        merged = {**candidate, "species_id": selection.get("species_id")}
        selected.add(_candidate_key(merged, str(candidate.get("estimator_id"))))
    return selected


def _expanded_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            probabilities = row.get("estimator_probabilities") or {}
            if not isinstance(probabilities, Mapping):
                continue
            for estimator_id, probability in probabilities.items():
                try:
                    numeric = float(probability)
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
                    continue
                yield {
                    "split_id": str(row.get("split_id") or ""),
                    "version_id": str(row.get("version_id") or ""),
                    "profile_id": str(row.get("profile_id") or ""),
                    "temporal_contract_id": str(
                        row.get("temporal_contract_id") or ""
                    ),
                    "horizon_days": int(row.get("horizon_days") or 0),
                    "estimator_id": str(estimator_id),
                    "species_id": str(row.get("species_id") or ""),
                    "area_id": str(row.get("area_id") or ""),
                    "observation_id": str(row.get("observation_id") or ""),
                    "target_date": str(row.get("target_date") or ""),
                    "validation_group_id": str(
                        row.get("validation_group_id") or ""
                    ),
                    "probability": numeric,
                    "y_true": int(row.get("y_true") or 0),
                    "baseline_probability": float(
                        row.get("train_prevalence_probability") or 0.0
                    ),
                }


def _ece(rows: list[Mapping[str, Any]]) -> float | None:
    if not rows:
        return None
    total = len(rows)
    error = 0.0
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = lower + 0.2
        selected = [
            row
            for row in rows
            if float(row["probability"]) >= lower
            and (
                float(row["probability"]) <= upper
                if upper >= 1.0
                else float(row["probability"]) < upper
            )
        ]
        if selected:
            predicted = sum(float(row["probability"]) for row in selected) / len(
                selected
            )
            observed = sum(int(row["y_true"]) for row in selected) / len(selected)
            error += len(selected) / total * abs(predicted - observed)
    return error


def _summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"prediction_count": 0}
    probabilities = [float(row["probability"]) for row in rows]
    labels = [int(row["y_true"]) for row in rows]
    baseline = [float(row["baseline_probability"]) for row in rows]

    def band(predicate: Any) -> dict[str, Any]:
        indexes = [index for index, value in enumerate(probabilities) if predicate(value)]
        positives = sum(labels[index] for index in indexes)
        errors = [
            index
            for index in indexes
            if (probabilities[index] >= 0.5) != bool(labels[index])
        ]
        return {
            "count": len(indexes),
            "observed_positive_rate": positives / len(indexes) if indexes else None,
            "error_count": len(errors),
            "error_examples": [
                {
                    key: rows[index].get(key)
                    for key in (
                        "species_id",
                        "area_id",
                        "target_date",
                        "observation_id",
                        "version_id",
                        "profile_id",
                        "temporal_contract_id",
                        "horizon_days",
                        "estimator_id",
                        "probability",
                        "y_true",
                        "prediction_day",
                        "selection_scope",
                    )
                    if rows[index].get(key) is not None
                }
                for index in errors[:20]
            ],
        }

    epsilon = 1e-15
    clipped = [min(max(value, epsilon), 1.0 - epsilon) for value in probabilities]
    return {
        "prediction_count": len(rows),
        "observation_count": len({str(row["observation_id"]) for row in rows}),
        "validation_group_count": len(
            {str(row["validation_group_id"]) for row in rows}
        ),
        "positive_count": sum(labels),
        "brier_score": sum(
            (label - probability) ** 2
            for label, probability in zip(labels, probabilities, strict=True)
        )
        / len(rows),
        "prevalence_brier_score": sum(
            (label - probability) ** 2
            for label, probability in zip(labels, baseline, strict=True)
        )
        / len(rows),
        "log_loss_clipped_for_metric_only": -sum(
            label * math.log(probability)
            + (1 - label) * math.log(1.0 - probability)
            for label, probability in zip(labels, clipped, strict=True)
        )
        / len(rows),
        "expected_calibration_error_5bin": _ece(rows),
        "exact_zero": band(lambda value: value == 0.0),
        "exact_one": band(lambda value: value == 1.0),
        "at_most_0_01": band(lambda value: value <= 0.01),
        "at_least_0_99": band(lambda value: value >= 0.99),
        "at_most_0_05": band(lambda value: value <= 0.05),
        "at_least_0_95": band(lambda value: value >= 0.95),
    }


def _grouped(
    rows: list[dict[str, Any]], fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row[field]) for field in fields)].append(row)
    result = []
    for key, values in sorted(groups.items()):
        result.append({**dict(zip(fields, key, strict=True)), **_summary(values)})
    return result


def _without_knn_catalog(path: Path) -> dict[str, Any]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("split_id") != "fruiting_groups_14d":
                continue
            probabilities = dict(row.get("estimator_probabilities") or {})
            probabilities.pop("knn_distance_v1", None)
            if probabilities:
                rows.append({**row, "estimator_probabilities": probabilities})
    audit = audit_rows(
        rows,
        policy=AuditPolicy(),
        split_ids={"fruiting_groups_14d"},
        include_candidates=False,
        include_stability=False,
    )
    return build_selection_catalog(audit)


def _knn_replacements(
    current: Mapping[str, Any], alternative: Mapping[str, Any]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, identity_fields in (
        ("species_selections", ("species_id", "prediction_day")),
        (
            "species_area_selections",
            ("species_id", "area_id", "prediction_day"),
        ),
    ):
        alternatives = {
            tuple(row.get(key) for key in identity_fields): row
            for row in alternative.get(field) or []
            if isinstance(row, Mapping)
        }
        changed = []
        for row in current.get(field) or []:
            if not isinstance(row, Mapping):
                continue
            candidate = row.get("candidate") or {}
            if not isinstance(candidate, Mapping) or candidate.get("estimator_id") != "knn_distance_v1":
                continue
            identity = tuple(row.get(key) for key in identity_fields)
            replacement = alternatives.get(identity)
            changed.append(
                {
                    **dict(zip(identity_fields, identity, strict=True)),
                    "current_candidate": candidate,
                    "current_evidence": row.get("evidence"),
                    "replacement_status": (
                        replacement.get("selection_status") if replacement else None
                    ),
                    "replacement_scope": (
                        replacement.get("selection_scope") if replacement else None
                    ),
                    "replacement_candidate": (
                        replacement.get("candidate") if replacement else None
                    ),
                    "replacement_evidence": (
                        replacement.get("evidence") if replacement else None
                    ),
                }
            )
        result[field] = changed
    return result


def main() -> int:
    args = _parser().parse_args()
    catalog = json.loads(args.quality_catalog.read_text(encoding="utf-8"))
    no_knn_catalog = _without_knn_catalog(args.holdout)
    species_keys = _selected_keys(catalog.get("species_selections") or [])
    rows = list(_expanded_rows(args.holdout))
    splits: dict[str, Any] = {}
    for split_id in ("fruiting_groups_14d", "fruiting_groups_7d"):
        split_rows = [row for row in rows if row["split_id"] == split_id]
        species_selected = [
            row
            for row in split_rows
            if _candidate_key(row, str(row["estimator_id"])) in species_keys
        ]
        unique: dict[tuple[object, ...], dict[str, Any]] = {}
        for row in species_selected:
            identity = _candidate_key(row, str(row["estimator_id"])) + (
                row["observation_id"],
            )
            unique[identity] = row
        species_selected = list(unique.values())

        row_index: dict[tuple[object, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in split_rows:
            row_index[
                _candidate_key(row, str(row["estimator_id"]))
                + (str(row["area_id"]),)
            ].append(row)
        operational_contexts: list[dict[str, Any]] = []
        for selection in catalog.get("species_area_selections") or []:
            if not isinstance(selection, Mapping):
                continue
            candidate = selection.get("candidate")
            if not isinstance(candidate, Mapping):
                continue
            merged = {**candidate, "species_id": selection.get("species_id")}
            key = _candidate_key(merged, str(candidate.get("estimator_id"))) + (
                str(selection.get("area_id") or ""),
            )
            for row in row_index.get(key, []):
                operational_contexts.append(
                    {
                        **row,
                        "prediction_day": int(selection.get("prediction_day") or 0),
                        "selection_scope": str(selection.get("selection_scope") or ""),
                    }
                )
        splits[split_id] = {
            "all_candidates": _summary(split_rows),
            "species_selected_candidate_identities": len(species_keys),
            "species_selected_candidates": _summary(species_selected),
            "species_selected_by_version": _grouped(
                species_selected, ("version_id",)
            ),
            "species_selected_by_estimator": _grouped(
                species_selected, ("estimator_id",)
            ),
            "species_selected_by_species": _grouped(
                species_selected, ("species_id",)
            ),
            "operational_area_day_contexts": _summary(operational_contexts),
            "operational_contexts_by_version": _grouped(
                operational_contexts, ("version_id",)
            ),
            "operational_contexts_by_estimator": _grouped(
                operational_contexts, ("estimator_id",)
            ),
            "operational_contexts_by_species": _grouped(
                operational_contexts, ("species_id",)
            ),
        }
    report = {
        "schema_version": "1.0",
        "kind": "mushroom_probability_extremes_holdout_audit",
        "operational_artifacts_written": False,
        "source_holdout": str(args.holdout.resolve()),
        "source_quality_catalog": str(args.quality_catalog.resolve()),
        "selection_split_id": catalog.get("selection_split_id"),
        "method": {
            "species_unit": "unique sealed species-candidate-observation prediction",
            "operational_context_unit": (
                "sealed species-area-prediction-day candidate applied to each "
                "matching area hold-out observation"
            ),
            "fixed_window_context_note": (
                "the same fixed-window hold-out probability is counted once for "
                "each forecast day on which that candidate was selected"
            ),
            "exact_endpoints_are_not_rounded_bands": True,
            "log_loss_probability_clip_is_metric_only": 1e-15,
        },
        "splits": splits,
        "knn_exclusion_diagnostic": {
            "operational": False,
            "warning": (
                "replacement candidates are reranked on the same official "
                "hold-out and are therefore diagnostic, not independent proof"
            ),
            "replacements": _knn_replacements(catalog, no_knn_catalog),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output.resolve()), "rows": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
