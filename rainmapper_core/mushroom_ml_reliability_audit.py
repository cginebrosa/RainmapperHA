"""Pure hold-out reliability audit and selection by mushroom species and area.

The same deterministic core serves the read-only audit CLI and materializes the
sealed training catalog. It separates validation splits, scores
observation-level outcomes, and uses ``validation_group_id`` only as a
dependency block for stability diagnostics. It never fits models or runs
inference.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


FAVORABLE_THRESHOLD = 0.60
UNFAVORABLE_THRESHOLD = 0.40
WILSON_Z_95 = 1.959963984540054
OFFICIAL_SELECTION_SPLIT_ID = "fruiting_groups_14d"
SELECTION_SCHEMA_VERSION = "1.2"
SELECTION_KIND = "mushroom_ml_reliability_selections"
AUDIT_CATALOG_SCHEMA_VERSION = "1.0"
AUDIT_CATALOG_KIND = "mushroom_ml_quality_audit_catalog"

CandidateKey = tuple[str, str, str, int, str]
ScopeKey = tuple[str, str, str]
SpeciesScopeKey = tuple[str, str]

EVIDENCE_KEYS = (
    "observation_count",
    "validation_group_count",
    "positive_observation_count",
    "negative_observation_count",
    "favorable_call_count",
    "true_favorable_count",
    "false_favorable_count",
    "favorable_precision",
    "wilson_lower_95_observations",
    "favorable_recall",
    "true_unfavorable_count",
    "false_unfavorable_count",
    "uncertain_count",
    "brier_score",
    "prevalence_brier_score",
    "brier_delta_vs_prevalence",
    "expected_calibration_error",
    "roc_auc",
)


@dataclass(frozen=True)
class AuditPolicy:
    official_split_id: str = OFFICIAL_SELECTION_SPLIT_ID
    require_both_classes: bool = True
    require_brier_improvement: bool = True


def wilson_lower_95(successes: int, total: int) -> float | None:
    if total <= 0:
        return None
    proportion = successes / total
    squared = WILSON_Z_95 * WILSON_Z_95
    denominator = 1 + squared / total
    center = proportion + squared / (2 * total)
    margin = WILSON_Z_95 * math.sqrt(
        proportion * (1 - proportion) / total + squared / (4 * total * total)
    )
    return (center - margin) / denominator


def _temporal_family(temporal_contract_id: object) -> str:
    contract = str(temporal_contract_id or "")
    if contract.startswith("fixed_gap_"):
        return "fixed"
    if contract.startswith("lag_"):
        return "lag"
    return "unknown"


def _candidate_key(row: Mapping[str, Any], estimator_id: str) -> CandidateKey:
    return (
        str(row.get("version_id") or ""),
        str(row.get("profile_id") or ""),
        str(row.get("temporal_contract_id") or ""),
        int(row.get("horizon_days") or 0),
        estimator_id,
    )


def _candidate_payload(key: CandidateKey) -> dict[str, Any]:
    return {
        "version_id": key[0],
        "profile_id": key[1],
        "temporal_contract_id": key[2],
        "temporal_family": _temporal_family(key[2]),
        "horizon_days": key[3],
        "estimator_id": key[4],
    }


def _operational_day_candidates(
    candidates: Mapping[CandidateKey, Mapping[str, Mapping[str, Any]]],
    prediction_day: int,
) -> dict[CandidateKey, Mapping[str, Mapping[str, Any]]]:
    """Return only candidates scientifically applicable to one forecast day."""
    if prediction_day not in range(1, 8):
        raise ValueError("prediction_day must be between 1 and 7")
    selected: dict[CandidateKey, Mapping[str, Mapping[str, Any]]] = {}
    for candidate, cases in candidates.items():
        temporal_family = _temporal_family(candidate[2])
        expected_horizon = 7 if temporal_family == "fixed" else prediction_day
        if candidate[3] == expected_horizon:
            selected[candidate] = cases
    return selected


def _calibration_error(y: np.ndarray, probabilities: np.ndarray) -> float:
    error = 0.0
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        upper = lower + 0.2
        mask = (probabilities >= lower) & (
            probabilities <= upper if upper >= 1.0 else probabilities < upper
        )
        if np.any(mask):
            error += float(np.mean(mask)) * abs(
                float(np.mean(probabilities[mask])) - float(np.mean(y[mask]))
            )
    return error


def _binary_roc_auc(y: np.ndarray, probabilities: np.ndarray) -> float:
    """Compute the exact binary ROC AUC without sklearn's per-call validation cost."""
    order = np.argsort(probabilities, kind="mergesort")
    sorted_probabilities = probabilities[order]
    ranks = np.empty(len(probabilities), dtype=float)
    start = 0
    while start < len(probabilities):
        end = start + 1
        while (
            end < len(probabilities)
            and sorted_probabilities[end] == sorted_probabilities[start]
        ):
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    positive = y == 1
    positive_count = int(np.sum(positive))
    negative_count = len(y) - positive_count
    return float(
        (
            np.sum(ranks[positive])
            - positive_count * (positive_count + 1) / 2.0
        )
        / (positive_count * negative_count)
    )


def _population_id(cases: Mapping[str, Mapping[str, Any]]) -> str:
    population = sorted(
        (case_id, int(value["y"]), str(value["group_id"]))
        for case_id, value in cases.items()
    )
    encoded = json.dumps(population, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _evaluate(
    candidate: CandidateKey,
    cases: Mapping[str, Mapping[str, Any]],
    policy: AuditPolicy,
) -> dict[str, Any]:
    values = [cases[case_id] for case_id in sorted(cases)]
    y = np.asarray([value["y"] for value in values], dtype=int)
    probabilities = np.asarray([value["probability"] for value in values], dtype=float)
    baseline_probabilities = np.asarray(
        [value["baseline_probability"] for value in values], dtype=float
    )
    favorable = probabilities >= FAVORABLE_THRESHOLD
    unfavorable = probabilities <= UNFAVORABLE_THRESHOLD
    positive = y == 1
    negative = y == 0
    true_favorable = int(np.sum(favorable & positive))
    false_favorable = int(np.sum(favorable & negative))
    true_unfavorable = int(np.sum(unfavorable & negative))
    false_unfavorable = int(np.sum(unfavorable & positive))
    favorable_calls = true_favorable + false_favorable
    positive_count = int(np.sum(positive))
    negative_count = int(np.sum(negative))
    brier = float(np.mean(np.square(y - probabilities))) if values else None
    baseline_brier = (
        float(np.mean(np.square(y - baseline_probabilities))) if values else None
    )
    brier_delta = (
        baseline_brier - brier
        if brier is not None and baseline_brier is not None
        else None
    )
    both_classes = positive_count > 0 and negative_count > 0
    auc = _binary_roc_auc(y, probabilities) if both_classes else None
    favorable_precision = true_favorable / favorable_calls if favorable_calls else None
    favorable_recall = true_favorable / positive_count if positive_count else None
    exclusion_reasons: list[str] = []
    if policy.require_both_classes and not both_classes:
        exclusion_reasons.append("single_class")
    if favorable_calls == 0:
        exclusion_reasons.append("no_favorable_calls")
    if policy.require_brier_improvement and (brier_delta is None or brier_delta <= 0):
        exclusion_reasons.append("not_better_than_prevalence")
    return {
        "candidate": _candidate_payload(candidate),
        "candidate_key": list(candidate),
        "population_id": _population_id(cases),
        "observation_count": len(values),
        "validation_group_count": len({value["group_id"] for value in values}),
        "positive_observation_count": positive_count,
        "negative_observation_count": negative_count,
        "favorable_call_count": favorable_calls,
        "true_favorable_count": true_favorable,
        "false_favorable_count": false_favorable,
        "favorable_precision": favorable_precision,
        "wilson_lower_95_observations": wilson_lower_95(true_favorable, favorable_calls),
        "favorable_recall": favorable_recall,
        "true_unfavorable_count": true_unfavorable,
        "false_unfavorable_count": false_unfavorable,
        "uncertain_count": int(np.sum(~favorable & ~unfavorable)),
        "brier_score": brier,
        "prevalence_brier_score": baseline_brier,
        "brier_delta_vs_prevalence": brier_delta,
        "roc_auc": auc,
        "expected_calibration_error": _calibration_error(y, probabilities),
        "eligible": not exclusion_reasons,
        "exclusion_reasons": exclusion_reasons,
    }


def _rank_key(result: Mapping[str, Any]) -> tuple[Any, ...]:
    def descending(value: object, *, missing: float = -1.0) -> float:
        return -float(value) if value is not None else -missing

    def ascending(value: object) -> float:
        return float(value) if value is not None else math.inf

    return (
        descending(result.get("wilson_lower_95_observations")),
        descending(result.get("favorable_precision")),
        -int(result.get("favorable_call_count") or 0),
        descending(result.get("favorable_recall")),
        int(result.get("uncertain_count") or 0),
        ascending(result.get("brier_score")),
        ascending(result.get("expected_calibration_error")),
        descending(result.get("roc_auc")),
        tuple(result.get("candidate_key") or ()),
    )


def _rank_candidates(
    candidates: Mapping[CandidateKey, Mapping[str, Mapping[str, Any]]],
    policy: AuditPolicy,
    *,
    evaluation_cache: dict[tuple[CandidateKey, str | None], dict[str, Any]] | None = None,
    omitted_group_id: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    evaluated = []
    for candidate, cases in candidates.items():
        cache_key = (candidate, omitted_group_id)
        cached = evaluation_cache.get(cache_key) if evaluation_cache is not None else None
        if cached is None:
            evaluated_cases = (
                cases
                if omitted_group_id is None
                else {
                    case_id: value
                    for case_id, value in cases.items()
                    if str(value["group_id"]) != omitted_group_id
                }
            )
            cached = _evaluate(candidate, evaluated_cases, policy)
            if evaluation_cache is not None:
                evaluation_cache[cache_key] = cached
        evaluated.append(
            {**cached, "exclusion_reasons": list(cached["exclusion_reasons"])}
        )
    population_counts = Counter(
        (result["population_id"], result["observation_count"]) for result in evaluated
    )
    if not population_counts:
        return [], {"cohort_count": 0, "selected_population_id": None}, []
    selected_population = max(
        population_counts,
        key=lambda item: (population_counts[item], item[1], item[0]),
    )
    comparable: list[dict[str, Any]] = []
    for result in evaluated:
        if (result["population_id"], result["observation_count"]) == selected_population:
            comparable.append(result)
            continue
        result["eligible"] = False
        result["exclusion_reasons"].append("incomparable_population")
    ranked = sorted((result for result in comparable if result["eligible"]), key=_rank_key)
    audited = sorted(
        evaluated, key=lambda result: (not result["eligible"], _rank_key(result))
    )
    version_ids = sorted({candidate[0] for candidate in candidates})
    return (
        ranked,
        {
            "cohort_count": len(population_counts),
            "selected_population_id": selected_population[0],
            "selected_population_observations": selected_population[1],
            "selected_population_candidate_count": population_counts[
                selected_population
            ],
            "candidate_count": len(evaluated),
            "eligible_candidate_count": len(ranked),
            "version_count": len(version_ids),
            "version_ids": version_ids,
        },
        audited,
    )


def _stability(
    candidates: Mapping[CandidateKey, Mapping[str, Mapping[str, Any]]],
    policy: AuditPolicy,
    winner: Mapping[str, Any],
    evaluation_cache: dict[tuple[CandidateKey, str | None], dict[str, Any]],
) -> dict[str, Any]:
    winner_key = tuple(winner["candidate_key"])
    winner_cases = candidates[winner_key]  # type: ignore[index]
    groups = sorted({str(value["group_id"]) for value in winner_cases.values()})
    alternatives: Counter[tuple[Any, ...] | None] = Counter()
    omissions: list[dict[str, Any]] = []
    for group_id in groups:
        ranked, _, _ = _rank_candidates(
            candidates,
            policy,
            evaluation_cache=evaluation_cache,
            omitted_group_id=group_id,
        )
        omitted_winner = tuple(ranked[0]["candidate_key"]) if ranked else None
        alternatives[omitted_winner] += 1
        omissions.append(
            {
                "omitted_validation_group_id": group_id,
                "winner_candidate_key": list(omitted_winner) if omitted_winner else None,
                "same_as_full_population": omitted_winner == winner_key,
            }
        )
    same_count = alternatives[winner_key]
    return {
        "method": "leave_one_validation_group_out_reranking",
        "omission_count": len(groups),
        "same_winner_count": same_count,
        "same_winner_rate": same_count / len(groups) if groups else None,
        "winner_counts": [
            {
                "candidate_key": list(candidate) if candidate else None,
                "count": count,
            }
            for candidate, count in sorted(
                alternatives.items(), key=lambda item: (-item[1], str(item[0]))
            )
        ],
        "omissions": omissions,
    }


def _operational_days(
    candidates: Mapping[CandidateKey, Mapping[str, Mapping[str, Any]]],
    policy: AuditPolicy,
    *,
    top: int,
    include_candidates: bool,
    include_stability: bool,
) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    evaluation_cache: dict[
        tuple[CandidateKey, str | None], dict[str, Any]
    ] = {}
    for prediction_day in range(1, 8):
        applicable = _operational_day_candidates(candidates, prediction_day)
        ranked, population, audited_candidates = _rank_candidates(
            applicable, policy, evaluation_cache=evaluation_cache
        )
        winner = ranked[0] if ranked else None
        day_payload: dict[str, Any] = {
            "prediction_day": prediction_day,
            "applicable_lag_horizon_days": prediction_day,
            "applicable_fixed_horizon_days": 7,
            "selection_status": "winner" if winner else "abstain",
            "population": population,
            "provisional_winner": winner,
            "alternatives": ranked[1:top] if winner else [],
        }
        if winner and include_stability:
            day_payload["stability"] = _stability(
                applicable, policy, winner, evaluation_cache
            )
        if include_candidates:
            day_payload["eligible_candidates"] = ranked
            day_payload["candidates"] = audited_candidates
        days.append(day_payload)
    return days


def audit_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    policy: AuditPolicy | None = None,
    species_ids: set[str] | None = None,
    area_ids: set[str] | None = None,
    split_ids: set[str] | None = None,
    top: int = 5,
    include_candidates: bool = False,
    include_stability: bool = True,
) -> dict[str, Any]:
    active_policy = policy or AuditPolicy()
    grouped: dict[
        ScopeKey, dict[CandidateKey, dict[str, dict[str, Any]]]
    ] = defaultdict(lambda: defaultdict(dict))
    species_grouped: dict[
        SpeciesScopeKey, dict[CandidateKey, dict[str, dict[str, Any]]]
    ] = defaultdict(lambda: defaultdict(dict))
    source_rows: Counter[ScopeKey] = Counter()
    species_source_rows: Counter[SpeciesScopeKey] = Counter()
    encountered_splits: set[str] = set()
    for line_number, row in enumerate(rows, start=1):
        species_id = str(row.get("species_id") or "")
        area_id = str(row.get("area_id") or "")
        split_id = str(row.get("split_id") or "")
        if not all((species_id, area_id, split_id)):
            raise ValueError(f"row {line_number}: missing species_id, area_id or split_id")
        encountered_splits.add(split_id)
        if species_ids is not None and species_id not in species_ids:
            continue
        if area_ids is not None and area_id not in area_ids:
            continue
        if split_ids is not None and split_id not in split_ids:
            continue
        observation_id = str(row.get("observation_id") or "")
        validation_group_id = str(row.get("validation_group_id") or "")
        if not observation_id or not validation_group_id:
            raise ValueError(
                f"row {line_number}: missing observation_id or validation_group_id"
            )
        try:
            y_true = int(row["y_true"])
            baseline = float(row["train_prevalence_probability"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"row {line_number}: invalid outcome or baseline") from exc
        if y_true not in (0, 1):
            raise ValueError(f"row {line_number}: y_true must be 0 or 1")
        if not math.isfinite(baseline) or not 0.0 <= baseline <= 1.0:
            raise ValueError(
                f"row {line_number}: train_prevalence_probability must be finite "
                "and between 0 and 1"
            )
        scope = (split_id, species_id, area_id)
        species_scope = (split_id, species_id)
        source_rows[scope] += 1
        species_source_rows[species_scope] += 1
        probabilities = row.get("estimator_probabilities")
        if not isinstance(probabilities, Mapping):
            continue
        temporal_contract_id = str(row.get("temporal_contract_id") or "")
        temporal_family = _temporal_family(temporal_contract_id)
        if temporal_family == "unknown":
            raise ValueError(
                f"row {line_number}: unsupported temporal_contract_id "
                f"{temporal_contract_id!r}"
            )
        try:
            horizon_days = int(row.get("horizon_days") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"row {line_number}: invalid horizon_days") from exc
        if horizon_days not in range(1, 8):
            raise ValueError(f"row {line_number}: horizon_days must be between 1 and 7")
        if temporal_family == "fixed" and horizon_days != 7:
            raise ValueError(
                f"row {line_number}: fixed temporal contract requires horizon_days=7"
            )
        for raw_estimator_id, raw_probability in probabilities.items():
            estimator_id = str(raw_estimator_id or "")
            if not estimator_id:
                raise ValueError(f"row {line_number}: missing estimator_id")
            try:
                probability = float(raw_probability)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"row {line_number}: invalid estimator probability for "
                    f"{estimator_id!r}"
                ) from exc
            if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError(
                    f"row {line_number}: estimator probability for {estimator_id!r} "
                    "must be finite and between 0 and 1"
                )
            candidate = _candidate_key(row, estimator_id)
            cases = grouped[scope][candidate]
            if observation_id in cases:
                raise ValueError(
                    "duplicate candidate/evaluation case: "
                    f"scope={scope!r}, candidate={candidate!r}, "
                    f"observation_id={observation_id!r}"
                )
            cases[observation_id] = {
                "y": y_true,
                "probability": probability,
                "baseline_probability": baseline,
                "group_id": validation_group_id,
            }
            species_case_id = json.dumps(
                [area_id, observation_id], separators=(",", ":")
            )
            species_cases = species_grouped[species_scope][candidate]
            if species_case_id in species_cases:
                raise ValueError(
                    "duplicate species fallback evaluation case: "
                    f"scope={species_scope!r}, candidate={candidate!r}, "
                    f"area_id={area_id!r}, observation_id={observation_id!r}"
                )
            species_cases[species_case_id] = {
                "y": y_true,
                "probability": probability,
                "baseline_probability": baseline,
                "group_id": json.dumps(
                    [area_id, validation_group_id], separators=(",", ":")
                ),
            }

    scopes: list[dict[str, Any]] = []
    for scope, candidates in sorted(grouped.items()):
        scope_payload: dict[str, Any] = {
            "split_id": scope[0],
            "species_id": scope[1],
            "area_id": scope[2],
            "source_row_count": source_rows[scope],
            "operational_days": _operational_days(
                candidates,
                active_policy,
                top=top,
                include_candidates=include_candidates,
                include_stability=include_stability,
            ),
        }
        scopes.append(scope_payload)

    species_scopes: list[dict[str, Any]] = []
    for scope, candidates in sorted(species_grouped.items()):
        species_scopes.append(
            {
                "split_id": scope[0],
                "species_id": scope[1],
                "source_row_count": species_source_rows[scope],
                "operational_days": _operational_days(
                    candidates,
                    active_policy,
                    top=top,
                    include_candidates=include_candidates,
                    include_stability=include_stability,
                ),
            }
        )

    selected_splits = sorted({scope["split_id"] for scope in scopes})
    warnings: list[str] = []
    if len(selected_splits) > 1:
        warnings.append(
            "Multiple split_id values were audited separately; no cross-split winner was computed."
        )
    if selected_splits and selected_splits != [active_policy.official_split_id]:
        warnings.append(
            "This diagnostic does not exclusively use the official selection split "
            f"{active_policy.official_split_id!r}."
        )
    return {
        "schema_version": "0.2-audit",
        "kind": "mushroom_ml_reliability_audit",
        "selection_status": "provisional_not_for_runtime",
        "territorial_granularity": "area_id",
        "scoring_unit": "observation_id",
        "validation_group_role": "diagnostic_only_not_ranking_or_gate",
        "selection_unit": "species_id_area_id_prediction_day",
        "prediction_days": list(range(1, 8)),
        "operational_candidate_rule": "lag_hN_or_fixed_h7_for_prediction_day_N",
        "ranking_primary_metric": "wilson_lower_95_observations",
        "official_selection_split_id": active_policy.official_split_id,
        "policy": asdict(active_policy),
        "favorable_threshold": FAVORABLE_THRESHOLD,
        "unfavorable_threshold": UNFAVORABLE_THRESHOLD,
        "encountered_split_ids": sorted(encountered_splits),
        "audited_split_ids": selected_splits,
        "warnings": warnings,
        "scope_count": len(scopes),
        "scopes": scopes,
        "species_scope_count": len(species_scopes),
        "species_scopes": species_scopes,
    }


def audit_jsonl(path: Path, **kwargs: Any) -> dict[str, Any]:
    def rows() -> Iterable[Mapping[str, Any]]:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON on line {line_number}: {exc}") from exc
                if not isinstance(payload, Mapping):
                    raise ValueError(f"line {line_number}: JSON object required")
                yield payload

    report = audit_rows(rows(), **kwargs)
    report["source"] = str(path)
    return report


def _published_resolution(
    day: Mapping[str, Any],
    *,
    selection_scope: str,
) -> dict[str, Any]:
    winner = day.get("provisional_winner")
    if not isinstance(winner, Mapping):
        return {
            "selection_status": "abstain",
            "selection_scope": "none",
            "candidate": None,
            "evidence": None,
        }
    candidate = winner.get("candidate")
    if not isinstance(candidate, Mapping):
        raise ValueError("Reliability winner is missing its candidate identity")
    population = day.get("population")
    population = population if isinstance(population, Mapping) else {}
    stability = day.get("stability")
    stability = stability if isinstance(stability, Mapping) else {}
    return {
        "selection_status": "winner",
        "selection_scope": selection_scope,
        "candidate": dict(candidate),
        "evidence": {
            key: winner.get(key)
            for key in EVIDENCE_KEYS
        },
        "population": {
            "population_id": winner.get("population_id"),
            "selected_population_id": population.get("selected_population_id"),
            "selected_population_observations": population.get(
                "selected_population_observations"
            ),
        },
        "stability": {
            "method": stability.get("method"),
            "omission_count": stability.get("omission_count"),
            "same_winner_count": stability.get("same_winner_count"),
            "same_winner_rate": stability.get("same_winner_rate"),
        },
    }


def _candidate_payload_key(candidate: Mapping[str, Any]) -> CandidateKey:
    return (
        str(candidate.get("version_id") or ""),
        str(candidate.get("profile_id") or ""),
        str(candidate.get("temporal_contract_id") or ""),
        int(candidate.get("horizon_days") or 0),
        str(candidate.get("estimator_id") or ""),
    )


def _scope_evidence_for_candidate(
    day: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return one candidate's evidence in this exact territorial scope."""
    if day is None or candidate is None:
        return None
    wanted = _candidate_payload_key(candidate)
    candidates = list(day.get("candidates") or [])
    winner = day.get("provisional_winner")
    if isinstance(winner, Mapping):
        candidates.append(winner)
    for raw in candidates:
        if not isinstance(raw, Mapping):
            continue
        key = tuple(raw.get("candidate_key") or ())
        if len(key) != 5 or (
            str(key[0]), str(key[1]), str(key[2]), int(key[3]), str(key[4])
        ) != wanted:
            continue
        return {
            "candidate": _candidate_payload(wanted),
            **{name: raw.get(name) for name in EVIDENCE_KEYS},
            "eligible": bool(raw.get("eligible")),
            "exclusion_reasons": list(raw.get("exclusion_reasons") or []),
        }
    return None


def _published_candidate_chain(
    selected_day: Mapping[str, Any] | None,
    *,
    area_day: Mapping[str, Any] | None,
    species_day: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Publish every eligible candidate in the exact audited ranking order."""
    if selected_day is None:
        return []
    chain: list[dict[str, Any]] = []
    for ranked in selected_day.get("eligible_candidates") or []:
        if not isinstance(ranked, Mapping):
            continue
        candidate = ranked.get("candidate")
        if not isinstance(candidate, Mapping):
            continue
        scoped_evidence = _scope_evidence_for_candidate(selected_day, candidate)
        if not isinstance(scoped_evidence, Mapping):
            continue
        chain.append(
            {
                "candidate": dict(candidate),
                "evidence": {
                    key: scoped_evidence.get(key)
                    for key in EVIDENCE_KEYS
                },
                "evidence_by_scope": {
                    "area": _scope_evidence_for_candidate(area_day, candidate),
                    "species": _scope_evidence_for_candidate(
                        species_day, candidate
                    ),
                },
            }
        )
    return chain


def _conservative_score(resolution: Mapping[str, Any]) -> float | None:
    """Return the comparable lower confidence bound of a published winner."""
    if resolution.get("selection_status") != "winner":
        return None
    evidence = resolution.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError("Reliability winner is missing its evidence")
    value = evidence.get("wilson_lower_95_observations")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("Reliability winner has no conservative score")
    score = float(value)
    if not math.isfinite(score):
        raise ValueError("Reliability winner conservative score is not finite")
    return score


def build_selection_catalog(
    report: Mapping[str, Any],
    *,
    operational_species_areas: Iterable[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Materialize deterministic area decisions and same-species fallbacks."""
    official_split_id = str(
        report.get("official_selection_split_id") or OFFICIAL_SELECTION_SPLIT_ID
    )
    audited_splits = list(report.get("audited_split_ids") or [])
    if audited_splits and audited_splits != [official_split_id]:
        raise ValueError("Reliability selections require only the official split")

    species_selections: list[dict[str, Any]] = []
    species_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    species_days_by_key: dict[tuple[str, int], Mapping[str, Any]] = {}
    for scope in report.get("species_scopes") or []:
        if not isinstance(scope, Mapping):
            continue
        species_id = str(scope.get("species_id") or "")
        split_id = str(scope.get("split_id") or "")
        if not species_id or split_id != official_split_id:
            continue
        for day in scope.get("operational_days") or []:
            if not isinstance(day, Mapping):
                continue
            prediction_day = int(day.get("prediction_day") or 0)
            resolution = {
                "species_id": species_id,
                "prediction_day": prediction_day,
                **_published_resolution(day, selection_scope="species"),
            }
            resolution["evidence_by_scope"] = {
                "area": None,
                "species": _scope_evidence_for_candidate(
                    day,
                    resolution.get("candidate"),
                ),
            }
            resolution["candidate_chain"] = _published_candidate_chain(
                day,
                area_day=None,
                species_day=day,
            )
            species_by_key[(species_id, prediction_day)] = resolution
            species_days_by_key[(species_id, prediction_day)] = day
            species_selections.append(resolution)

    area_scopes: dict[tuple[str, str], Mapping[str, Any]] = {}
    for scope in report.get("scopes") or []:
        if not isinstance(scope, Mapping):
            continue
        species_id = str(scope.get("species_id") or "")
        area_id = str(scope.get("area_id") or "")
        split_id = str(scope.get("split_id") or "")
        if not species_id or not area_id or split_id != official_split_id:
            continue
        area_scopes[(species_id, area_id)] = scope

    requested_areas = set(area_scopes)
    requested_areas.update(
        (str(species_id), str(area_id))
        for species_id, area_id in (operational_species_areas or ())
        if str(species_id) and str(area_id)
    )
    species_area_selections: list[dict[str, Any]] = []
    for species_id, area_id in sorted(requested_areas):
        scope = area_scopes.get((species_id, area_id), {})
        days_by_number = {
            int(day.get("prediction_day") or 0): day
            for day in scope.get("operational_days", [])
            if isinstance(day, Mapping)
        }
        for prediction_day in range(1, 8):
            day = days_by_number.get(prediction_day)
            area_resolution = (
                _published_resolution(day, selection_scope="area")
                if day is not None
                else {
                    "selection_status": "abstain",
                    "selection_scope": "none",
                    "candidate": None,
                    "evidence": None,
                }
            )
            species_resolution = species_by_key.get((species_id, prediction_day))
            area_score = _conservative_score(area_resolution)
            species_score = (
                _conservative_score(species_resolution)
                if species_resolution is not None
                else None
            )
            if area_score is not None and (
                species_score is None or area_score >= species_score
            ):
                # Equal evidence stays local; species wins only when it has
                # demonstrated a strictly stronger conservative lower bound.
                resolution = area_resolution
            elif species_score is not None and species_resolution is not None:
                resolution = {
                    key: value
                    for key, value in species_resolution.items()
                    if key not in {"species_id", "prediction_day"}
                }
                resolution["selection_scope"] = "species_fallback"
            else:
                resolution = area_resolution
            candidate = resolution.get("candidate")
            candidate = candidate if isinstance(candidate, Mapping) else None
            resolution["evidence_by_scope"] = {
                "area": _scope_evidence_for_candidate(day, candidate),
                "species": _scope_evidence_for_candidate(
                    species_days_by_key.get((species_id, prediction_day)),
                    candidate,
                ),
            }
            selected_scope = str(resolution.get("selection_scope") or "")
            selected_day = (
                day
                if selected_scope == "area"
                else species_days_by_key.get((species_id, prediction_day))
            )
            resolution["candidate_chain"] = _published_candidate_chain(
                selected_day,
                area_day=day,
                species_day=species_days_by_key.get(
                    (species_id, prediction_day)
                ),
            )
            species_area_selections.append(
                {
                    "species_id": species_id,
                    "area_id": area_id,
                    "prediction_day": prediction_day,
                    **resolution,
                }
            )

    policy = report.get("policy")
    policy = dict(policy) if isinstance(policy, Mapping) else {}
    payload: dict[str, Any] = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "kind": SELECTION_KIND,
        "status": "complete" if species_area_selections else "unavailable",
        "official_split_id": official_split_id,
        "prediction_days": list(range(1, 8)),
        "selection_policy": {
            **policy,
            "operational_candidate_rule": (
                "lag_hN_or_fixed_h7_for_prediction_day_N"
            ),
            "ranking_primary_metric": "wilson_lower_95_observations",
            "territorial_resolution_rule": (
                "highest_wilson_lower_95_between_area_and_species;ties_prefer_area"
            ),
            "ranking_order": [
                "wilson_lower_95_observations_desc",
                "favorable_precision_desc",
                "favorable_call_count_desc",
                "favorable_recall_desc",
                "uncertain_count_asc",
                "brier_score_asc",
                "expected_calibration_error_asc",
                "roc_auc_desc",
                "candidate_key_asc",
            ],
        },
        "species_selections": sorted(
            species_selections,
            key=lambda row: (row["species_id"], row["prediction_day"]),
        ),
        "species_area_selections": sorted(
            species_area_selections,
            key=lambda row: (
                row["species_id"],
                row["area_id"],
                row["prediction_day"],
            ),
        ),
    }
    payload["counts"] = {
        "species": len({row["species_id"] for row in species_selections}),
        "species_days": len(species_selections),
        "species_areas": len(
            {
                (row["species_id"], row["area_id"])
                for row in species_area_selections
            }
        ),
        "species_area_days": len(species_area_selections),
        "area_winners": sum(
            row["selection_scope"] == "area" for row in species_area_selections
        ),
        "species_fallbacks": sum(
            row["selection_scope"] == "species_fallback"
            for row in species_area_selections
        ),
        "abstentions": sum(
            row["selection_status"] == "abstain"
            for row in species_area_selections
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    payload["selection_id"] = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    return payload


def _compact_audit_scope(scope: Mapping[str, Any]) -> dict[str, Any]:
    """Deduplicate metrics while retaining every per-day ranking decision."""
    evaluations_by_key: dict[CandidateKey, dict[str, Any]] = {}
    day_candidates: list[tuple[Mapping[str, Any], list[Mapping[str, Any]]]] = []
    for raw_day in scope.get("operational_days") or []:
        if not isinstance(raw_day, Mapping):
            continue
        candidates = [
            row
            for row in raw_day.get("candidates") or []
            if isinstance(row, Mapping)
        ]
        day_candidates.append((raw_day, candidates))
        for row in candidates:
            key = tuple(row.get("candidate_key") or ())
            if len(key) != 5:
                raise ValueError("Audit candidate identity is invalid")
            candidate_key: CandidateKey = (  # type: ignore[assignment]
                str(key[0]), str(key[1]), str(key[2]), int(key[3]), str(key[4])
            )
            evaluation = {
                name: value
                for name, value in row.items()
                if name not in {"eligible", "exclusion_reasons"}
            }
            previous = evaluations_by_key.get(candidate_key)
            if previous is not None and previous != evaluation:
                raise ValueError("Audit candidate metrics changed between prediction days")
            evaluations_by_key[candidate_key] = evaluation

    candidate_ids = {
        key: f"c{index:04d}"
        for index, key in enumerate(sorted(evaluations_by_key), start=1)
    }
    evaluations = []
    for key in sorted(evaluations_by_key):
        evaluation = dict(evaluations_by_key[key])
        evaluation.pop("candidate_key", None)
        evaluations.append({"candidate_id": candidate_ids[key], **evaluation})

    operational_days = []
    for raw_day, candidates in day_candidates:
        ranked_keys = [
            tuple(row.get("candidate_key") or ())
            for row in raw_day.get("eligible_candidates") or []
            if isinstance(row, Mapping)
        ]
        rank_by_key = {key: index for index, key in enumerate(ranked_keys, start=1)}
        references = []
        for row in candidates:
            raw_key = tuple(row.get("candidate_key") or ())
            key: CandidateKey = (  # type: ignore[assignment]
                str(raw_key[0]),
                str(raw_key[1]),
                str(raw_key[2]),
                int(raw_key[3]),
                str(raw_key[4]),
            )
            references.append(
                {
                    "candidate_id": candidate_ids[key],
                    "eligible": bool(row.get("eligible")),
                    "exclusion_reasons": list(row.get("exclusion_reasons") or []),
                    "rank": rank_by_key.get(raw_key),
                }
            )
        references.sort(
            key=lambda row: (
                row["rank"] is None,
                row["rank"] or 0,
                row["candidate_id"],
            )
        )
        winner = raw_day.get("provisional_winner")
        winner_key = (
            tuple(winner.get("candidate_key") or ())
            if isinstance(winner, Mapping)
            else ()
        )
        stability = raw_day.get("stability")
        stability = stability if isinstance(stability, Mapping) else {}
        operational_days.append(
            {
                "prediction_day": int(raw_day.get("prediction_day") or 0),
                "selection_status": str(raw_day.get("selection_status") or ""),
                "selected_candidate_id": (
                    candidate_ids.get(winner_key) if winner_key else None
                ),
                "population": dict(raw_day.get("population") or {}),
                "stability": {
                    key: stability.get(key)
                    for key in (
                        "method",
                        "omission_count",
                        "same_winner_count",
                        "same_winner_rate",
                    )
                },
                "candidates": references,
            }
        )
    result = {
        key: scope.get(key)
        for key in ("split_id", "species_id", "area_id", "source_row_count")
        if key in scope
    }
    result["evaluations"] = evaluations
    result["operational_days"] = operational_days
    return result


def build_quality_audit_catalog(
    report: Mapping[str, Any],
    selections: Mapping[str, Any],
    *,
    snapshot_id: str,
) -> dict[str, Any]:
    """Build the on-demand History evidence catalog from the selection audit."""
    if report.get("audited_split_ids") != [OFFICIAL_SELECTION_SPLIT_ID]:
        raise ValueError("Quality audit catalog requires only the official split")
    if selections.get("official_split_id") != OFFICIAL_SELECTION_SPLIT_ID:
        raise ValueError("Quality audit catalog selection split is invalid")
    area_scopes = [
        _compact_audit_scope(scope)
        for scope in report.get("scopes") or []
        if isinstance(scope, Mapping)
    ]
    species_scopes = [
        _compact_audit_scope(scope)
        for scope in report.get("species_scopes") or []
        if isinstance(scope, Mapping)
    ]
    payload = {
        "schema_version": AUDIT_CATALOG_SCHEMA_VERSION,
        "kind": AUDIT_CATALOG_KIND,
        "snapshot_id": snapshot_id,
        "selection_id": selections.get("selection_id"),
        "official_split_id": OFFICIAL_SELECTION_SPLIT_ID,
        "territorial_granularity": "area_id",
        "scoring_unit": "observation_id",
        "validation_group_role": "diagnostic_only_not_ranking_or_gate",
        "selection_policy": selections.get("selection_policy"),
        "area_scopes": area_scopes,
        "species_scopes": species_scopes,
        "counts": {
            "area_scopes": len(area_scopes),
            "species_scopes": len(species_scopes),
            "area_evaluations": sum(len(scope["evaluations"]) for scope in area_scopes),
            "species_evaluations": sum(
                len(scope["evaluations"]) for scope in species_scopes
            ),
            "area_days": sum(len(scope["operational_days"]) for scope in area_scopes),
            "species_days": sum(
                len(scope["operational_days"]) for scope in species_scopes
            ),
        },
    }
    return validate_quality_audit_catalog(payload, selections=selections)


def validate_quality_audit_catalog(
    catalog: Mapping[str, Any],
    *,
    selections: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate identities, rankings and agreement with the compact catalog."""
    if (
        catalog.get("kind") != AUDIT_CATALOG_KIND
        or catalog.get("schema_version") != AUDIT_CATALOG_SCHEMA_VERSION
    ):
        raise ValueError("Quality audit catalog contract is invalid")
    if not re.fullmatch(
        r"sha256:[0-9a-f]{64}", str(catalog.get("snapshot_id") or "")
    ):
        raise ValueError("Quality audit catalog snapshot_id is invalid")
    if not re.fullmatch(
        r"sha256:[0-9a-f]{64}", str(catalog.get("selection_id") or "")
    ):
        raise ValueError("Quality audit catalog selection_id is invalid")
    if catalog.get("official_split_id") != OFFICIAL_SELECTION_SPLIT_ID:
        raise ValueError("Quality audit catalog split is invalid")

    expected: dict[tuple[str, str, str, int], Mapping[str, Any]] = {}
    if selections is not None:
        if selections.get("selection_id") != catalog.get("selection_id"):
            raise ValueError("Quality audit and compact selection ids differ")
        for scope_name, rows_name, area_marker in (
            ("area", "species_area_selections", True),
            ("species", "species_selections", False),
        ):
            for row in selections.get(rows_name) or []:
                if not isinstance(row, Mapping):
                    continue
                key = (
                    scope_name,
                    str(row.get("species_id") or ""),
                    str(row.get("area_id") or "") if area_marker else "",
                    int(row.get("prediction_day") or 0),
                )
                expected[key] = row

    actual_counts = {
        "area_scopes": 0,
        "species_scopes": 0,
        "area_evaluations": 0,
        "species_evaluations": 0,
        "area_days": 0,
        "species_days": 0,
    }
    seen_scopes: set[tuple[str, str, str]] = set()
    for collection, scope_name in (
        ("area_scopes", "area"),
        ("species_scopes", "species"),
    ):
        scopes = catalog.get(collection)
        if not isinstance(scopes, list):
            raise ValueError("Quality audit catalog scopes must be lists")
        actual_counts[collection] = len(scopes)
        for scope in scopes:
            if not isinstance(scope, Mapping):
                raise ValueError("Quality audit scope is invalid")
            species_id = str(scope.get("species_id") or "")
            area_id = str(scope.get("area_id") or "") if scope_name == "area" else ""
            scope_key = (scope_name, species_id, area_id)
            if (
                not species_id
                or (scope_name == "area" and not area_id)
                or scope_key in seen_scopes
            ):
                raise ValueError("Quality audit scope identity is invalid")
            seen_scopes.add(scope_key)
            evaluations = scope.get("evaluations")
            days = scope.get("operational_days")
            if not isinstance(evaluations, list) or not isinstance(days, list):
                raise ValueError("Quality audit scope contents are invalid")
            actual_counts[f"{scope_name}_evaluations"] += len(evaluations)
            actual_counts[f"{scope_name}_days"] += len(days)
            candidate_ids = {
                str(row.get("candidate_id") or "")
                for row in evaluations
                if isinstance(row, Mapping)
            }
            if "" in candidate_ids or len(candidate_ids) != len(evaluations):
                raise ValueError("Quality audit candidate ids are invalid")
            if {
                int(day.get("prediction_day") or 0)
                for day in days
                if isinstance(day, Mapping)
            } != set(range(1, 8)):
                raise ValueError("Quality audit prediction days are incomplete")
            evaluation_by_id = {
                str(row["candidate_id"]): row
                for row in evaluations
                if isinstance(row, Mapping)
            }
            for day in days:
                if not isinstance(day, Mapping):
                    raise ValueError("Quality audit day is invalid")
                prediction_day = int(day.get("prediction_day") or 0)
                references = day.get("candidates")
                if not isinstance(references, list):
                    raise ValueError("Quality audit candidate references are invalid")
                reference_ids = [
                    str(ref.get("candidate_id") or "")
                    for ref in references
                    if isinstance(ref, Mapping)
                ]
                if (
                    len(reference_ids) != len(references)
                    or len(set(reference_ids)) != len(reference_ids)
                    or any(candidate_id not in evaluation_by_id for candidate_id in reference_ids)
                ):
                    raise ValueError("Quality audit references an unknown candidate")
                eligible = sorted(
                    (
                        int(ref.get("rank") or 0),
                        str(ref.get("candidate_id") or ""),
                    )
                    for ref in references
                    if isinstance(ref, Mapping) and ref.get("eligible")
                )
                if [rank for rank, _ in eligible] != list(range(1, len(eligible) + 1)):
                    raise ValueError("Quality audit candidate ranking is invalid")
                selected_id = day.get("selected_candidate_id")
                if selected_id != (eligible[0][1] if eligible else None):
                    raise ValueError("Quality audit winner does not match rank one")
                compact = expected.get((scope_name, species_id, area_id, prediction_day))
                if compact is not None:
                    compact_candidate = compact.get("candidate")
                    audited_candidate = (
                        evaluation_by_id[str(selected_id)].get("candidate")
                        if selected_id is not None
                        else None
                    )
                    compact_scope = str(compact.get("selection_scope") or "")
                    if scope_name == "species" or compact_scope == "area":
                        if audited_candidate is not None and (
                            compact_scope != scope_name
                            or compact_candidate != audited_candidate
                        ):
                            raise ValueError("Quality audit winner differs from compact selection")
                        if audited_candidate is None and compact_scope == scope_name:
                            raise ValueError("Quality audit abstention differs from compact selection")
                    elif compact_scope == "none" and audited_candidate is not None:
                        raise ValueError("Quality audit winner differs from compact abstention")
                    elif compact_scope not in {"species_fallback", "none"}:
                        raise ValueError("Quality audit compact selection scope is invalid")
    if dict(catalog.get("counts") or {}) != actual_counts:
        raise ValueError("Quality audit catalog counts are invalid")
    return dict(catalog)
