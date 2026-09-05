"""Deterministic operational interpretation for mushroom model comparisons.

The predictor deliberately keeps the two observed-weather feature sets and
their estimators visible.  This module turns those raw scores and their
out-of-sample evaluation into a conservative, auditable decision contract.
It does not generate prose and it never reads future weather.
"""

from __future__ import annotations

from typing import Any


LEGACY_FEATURE_SET_IDS = ("fixed_gap_7d_v1", "lag_event_v1")
ALTITUDE_FEATURE_SET_IDS = ("fixed_gap_7d_altitude_v2", "lag_event_altitude_v2")
FEATURE_SET_IDS = ALTITUDE_FEATURE_SET_IDS
FAVORABLE_THRESHOLD = 0.60
UNFAVORABLE_THRESHOLD = 0.40
LOW_AGREEMENT_GAP = 0.20
HIGH_AGREEMENT_GAP = 0.10
FEATURE_SET_CONFLICT_GAP = 0.50
UNVALIDATED_FAVORABLE_THRESHOLD = 0.55
UNVALIDATED_UNFAVORABLE_THRESHOLD = 0.45


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _flag(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    number = _number(value)
    return number == 1.0 if number is not None else None


def _score_label(probability: float) -> str:
    if probability >= FAVORABLE_THRESHOLD:
        return "favorable"
    if probability <= UNFAVORABLE_THRESHOLD:
        return "unfavorable"
    return "uncertain"


def _timing(days: float | None, delay: dict[str, Any]) -> str:
    if days is None:
        return "unknown"
    minimum = _number(delay.get("min"))
    optimal_min = _number(delay.get("optimal_min"))
    optimal_max = _number(delay.get("optimal_max"))
    maximum = _number(delay.get("max"))
    # Zero-filled profiles are schema placeholders, not zero-day contracts.
    configured = [minimum, optimal_min, optimal_max, maximum]
    if not any(value is not None and value > 0 for value in configured):
        return "unknown"
    if minimum is not None and days < minimum:
        return "early"
    if optimal_min is not None and days < optimal_min:
        return "entering"
    if optimal_max is not None and days <= optimal_max:
        return "optimal"
    if maximum is not None and days <= maximum:
        return "late"
    if maximum is not None and days > maximum:
        return "expired"
    return "unknown"


def _combined_timing(values: list[str]) -> str:
    known = {value for value in values if value != "unknown"}
    if not known:
        return "unknown"
    if len(known) == 1:
        return next(iter(known))
    if known <= {"entering", "optimal"}:
        return "entering_optimal"
    return "mixed"


def _trusted_result(feature_set_id: str, result: dict[str, Any]) -> dict[str, Any] | None:
    evaluation = result.get("evaluation")
    if not isinstance(evaluation, dict) or evaluation.get("available") is not True:
        return None
    baseline = evaluation.get("baseline")
    baseline = baseline if isinstance(baseline, dict) else {}
    baseline_brier = _number(baseline.get("brier_score"))
    if baseline_brier is None:
        return None
    estimator_metrics = evaluation.get("estimators")
    estimator_metrics = estimator_metrics if isinstance(estimator_metrics, dict) else {}
    probabilities = result.get("interpretation_estimator_probabilities")
    if not isinstance(probabilities, dict):
        probabilities = result.get("estimator_probabilities")
    probabilities = probabilities if isinstance(probabilities, dict) else {}
    exclusions = result.get("estimator_exclusions")
    exclusions = exclusions if isinstance(exclusions, dict) else {}
    candidates: list[tuple[float, str, float, dict[str, Any]]] = []
    for estimator_id in sorted(set(estimator_metrics) | set(probabilities)):
        if estimator_id in exclusions:
            continue
        metrics = estimator_metrics.get(estimator_id)
        metrics = metrics if isinstance(metrics, dict) else {}
        brier = _number(metrics.get("brier_score"))
        probability = _number(probabilities.get(estimator_id))
        if brier is None or probability is None or brier >= baseline_brier:
            continue
        candidates.append((brier, estimator_id, probability, metrics))
    if not candidates:
        return None
    brier, estimator_id, probability, metrics = min(
        candidates, key=lambda row: (row[0], row[1])
    )
    return {
        "feature_set_id": feature_set_id,
        "estimator_id": estimator_id,
        "probability": round(probability, 4),
        "label": _score_label(probability),
        "brier_score": round(brier, 4),
        "baseline_brier_score": round(baseline_brier, 4),
        "roc_auc": _number(metrics.get("roc_auc")),
        "test_samples": metrics.get("n"),
    }


def _interpretation_probabilities(result: dict[str, Any]) -> dict[str, Any]:
    probabilities = result.get("interpretation_estimator_probabilities")
    if not isinstance(probabilities, dict):
        probabilities = result.get("estimator_probabilities")
    return probabilities if isinstance(probabilities, dict) else {}


def _validated_estimator_ids(
    available_results: list[tuple[str, dict[str, Any]]],
) -> list[str]:
    """Return estimator families that beat prevalence in at least one contract."""
    validated: set[str] = set()
    for _feature_set_id, result in available_results:
        evaluation = result.get("evaluation")
        evaluation = evaluation if isinstance(evaluation, dict) else {}
        baseline = evaluation.get("baseline")
        baseline = baseline if isinstance(baseline, dict) else {}
        baseline_brier = _number(baseline.get("brier_score"))
        metrics_by_estimator = evaluation.get("estimators")
        metrics_by_estimator = (
            metrics_by_estimator if isinstance(metrics_by_estimator, dict) else {}
        )
        exclusions = result.get("estimator_exclusions")
        exclusions = exclusions if isinstance(exclusions, dict) else {}
        probabilities = _interpretation_probabilities(result)
        if baseline_brier is None:
            continue
        for estimator_id in sorted(set(metrics_by_estimator) | set(probabilities)):
            metrics = metrics_by_estimator.get(estimator_id)
            metrics = metrics if isinstance(metrics, dict) else {}
            brier = _number(metrics.get("brier_score"))
            probability = _number(probabilities.get(estimator_id))
            if (
                estimator_id not in exclusions
                and brier is not None
                and probability is not None
                and brier < baseline_brier
            ):
                validated.add(estimator_id)
    return sorted(validated)


def _unvalidated_signal(
    available_results: list[tuple[str, dict[str, Any]]],
) -> tuple[str, dict[str, float] | None]:
    """Summarize applicable raw scores without presenting them as validated."""
    feature_set_scores: list[float] = []
    for _feature_set_id, result in available_results:
        probabilities = _interpretation_probabilities(result)
        exclusions = result.get("estimator_exclusions")
        exclusions = exclusions if isinstance(exclusions, dict) else {}
        values = [
            probability
            for estimator_id in sorted(probabilities)
            if estimator_id not in exclusions
            and (probability := _number(probabilities.get(estimator_id))) is not None
        ]
        if values:
            feature_set_scores.append(sum(values) / len(values))
    if not feature_set_scores:
        return "unavailable", None
    minimum = min(feature_set_scores)
    maximum = max(feature_set_scores)
    value_range = {
        "min": round(minimum, 4),
        "max": round(maximum, 4),
        "midpoint": round(sum(feature_set_scores) / len(feature_set_scores), 4),
    }
    if all(
        value >= UNVALIDATED_FAVORABLE_THRESHOLD
        for value in feature_set_scores
    ):
        return "favorable", value_range
    if all(
        value <= UNVALIDATED_UNFAVORABLE_THRESHOLD
        for value in feature_set_scores
    ):
        return "unfavorable", value_range
    return "mixed", value_range


def build_interpretation(
    comparison: dict[str, Any],
    *,
    season_phase: str,
    phenology: dict[str, Any] | None = None,
    feature_set_ids: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """Build the stable interpretation payload consumed by every UI view."""
    active_feature_set_ids = tuple(feature_set_ids or ()) or (
        ALTITUDE_FEATURE_SET_IDS
        if any(feature_set_id in comparison for feature_set_id in ALTITUDE_FEATURE_SET_IDS)
        else LEGACY_FEATURE_SET_IDS
    )
    available_results: list[tuple[str, dict[str, Any]]] = []
    for feature_set_id in active_feature_set_ids:
        result = comparison.get(feature_set_id)
        if isinstance(result, dict) and result.get("available") is True:
            available_results.append((feature_set_id, result))

    reason_codes: list[str] = []
    if season_phase == "out_of_season":
        return {
            "schema_version": "1.1",
            "verdict": "out_of_season",
            "reference_range": None,
            "statistical_consensus": "unavailable",
            "statistical_support": "unavailable",
            "validated_estimator_ids": [],
            "validated_estimator_count": 0,
            "experimental_signal": "unavailable",
            "experimental_range": None,
            "experimental_results": [],
            "experimental_estimator_ids": [],
            "experimental_out_of_domain_caution": False,
            "ecological_compatibility": "out_of_season",
            "ecological_evidence": "unavailable",
            "confidence": "low",
            "weather_signal": "unknown",
            "fruiting_timing": "unknown",
            "significant_rain_events": [],
            "trusted_results": [],
            "reason_codes": ["out_of_season"],
        }
    if len(available_results) < len(active_feature_set_ids):
        reason_codes.append("partial_model_availability")

    stations_by_feature_set = {
        feature_set_id: str(result.get("weather_station_code"))
        for feature_set_id, result in available_results
        if result.get("weather_station_code")
    }
    if len(set(stations_by_feature_set.values())) > 1:
        reason_codes.append("feature_sets_use_different_stations")

    trusted = [
        trusted_result
        for feature_set_id, result in available_results
        if (trusted_result := _trusted_result(feature_set_id, result)) is not None
    ]
    # Kept in the response schema for older clients. There is no shadow tier now:
    # every estimator is subject to the same Brier-vs-prevalence rule above.
    experimental_results: list[dict[str, Any]] = []
    experimental_signal = "unavailable"
    experimental_range = None
    experimental_estimator_ids: list[str] = []
    validated_estimator_ids = _validated_estimator_ids(available_results)
    if not trusted:
        verdict = "abstain"
        reference_range = None
        reason_codes.append("no_estimator_beats_prevalence")
        unvalidated_signal, unvalidated_range = _unvalidated_signal(
            available_results
        )
        if unvalidated_signal in {"favorable", "unfavorable"}:
            reason_codes.append(f"unvalidated_{unvalidated_signal}_signal")
        else:
            reason_codes.append("unvalidated_signal_not_interpretable")
    else:
        unvalidated_signal = "not_applicable"
        unvalidated_range = None
        probabilities = [float(row["probability"]) for row in trusted]
        reference_range = {
            "min": round(min(probabilities), 4),
            "max": round(max(probabilities), 4),
            "midpoint": round(sum(probabilities) / len(probabilities), 4),
        }
        labels = {str(row["label"]) for row in trusted}
        verdict = next(iter(labels)) if len(labels) == 1 else "uncertain"
        if len(labels) > 1:
            reason_codes.append("trusted_models_disagree")
        if max(probabilities) - min(probabilities) >= FEATURE_SET_CONFLICT_GAP:
            verdict = "abstain"
            reference_range = None
            reason_codes.append("feature_sets_conflict_extremely")

    estimator_gaps: dict[str, float] = {}
    for feature_set_id, result in available_results:
        probabilities = _interpretation_probabilities(result)
        evaluation = result.get("evaluation")
        evaluation = evaluation if isinstance(evaluation, dict) else {}
        baseline = evaluation.get("baseline")
        baseline = baseline if isinstance(baseline, dict) else {}
        baseline_brier = _number(baseline.get("brier_score"))
        metrics_by_estimator = evaluation.get("estimators")
        metrics_by_estimator = (
            metrics_by_estimator if isinstance(metrics_by_estimator, dict) else {}
        )
        exclusions = result.get("estimator_exclusions")
        exclusions = exclusions if isinstance(exclusions, dict) else {}
        validated_probabilities = []
        if baseline_brier is not None:
            for estimator_id in sorted(set(metrics_by_estimator) | set(probabilities)):
                metrics = metrics_by_estimator.get(estimator_id)
                metrics = metrics if isinstance(metrics, dict) else {}
                brier = _number(metrics.get("brier_score"))
                probability = _number(probabilities.get(estimator_id))
                if (
                    estimator_id not in exclusions
                    and brier is not None
                    and brier < baseline_brier
                    and probability is not None
                ):
                    validated_probabilities.append(probability)
        if len(validated_probabilities) >= 2:
            estimator_gaps[feature_set_id] = round(
                max(validated_probabilities) - min(validated_probabilities), 4
            )
    maximum_gap = max(estimator_gaps.values(), default=None)
    if len(validated_estimator_ids) < 2 or maximum_gap is None:
        consensus = "unavailable"
    elif maximum_gap is not None and maximum_gap >= LOW_AGREEMENT_GAP:
        consensus = "low"
        reason_codes.append("estimators_disagree")
    elif maximum_gap is not None and maximum_gap <= HIGH_AGREEMENT_GAP:
        consensus = "high"
    else:
        consensus = "moderate"

    if not validated_estimator_ids:
        statistical_support = "unavailable"
    elif len(validated_estimator_ids) == 1 or consensus in {"low", "unavailable"}:
        statistical_support = "limited"
        reason_codes.append("statistical_support_limited")
    elif consensus == "high":
        statistical_support = "strong"
    else:
        statistical_support = "moderate"

    if not trusted or consensus == "low":
        confidence = "low"
    elif len(trusted) >= 2 and consensus == "high":
        confidence = "high"
    else:
        confidence = "moderate"
    if "feature_sets_conflict_extremely" in reason_codes:
        confidence = "low"

    severe_ood_features = sorted(
        {
            str(detail.get("feature"))
            for _feature_set_id, result in available_results
            for detail in result.get("severe_out_of_domain_features", [])
            if isinstance(detail, dict) and detail.get("feature")
        }
    )
    if severe_ood_features:
        reason_codes.append("logistic_regression_excluded_out_of_domain")
        confidence = "low"
    experimental_out_of_domain_caution = False

    # MOD_0001: keep the former ecological timing calculation as
    # advisory data, but never let it replace the fitted model's verdict.
    # See mushroom-predictor-reliability-selection-spec-es.md.
    delay = dict((phenology or {}).get("fruiting_delay_after_rain_days") or {})
    timing_values: list[str] = []
    event_found = False
    active_event_found = False
    significant_rain_events: dict[tuple[str, float, int, float], dict[str, Any]] = {}
    for _feature_set_id, result in available_results:
        features = result.get("features_used")
        features = features if isinstance(features, dict) else {}
        found = _flag(features.get("significant_rain_found_90d"))
        days = _number(features.get("days_since_significant_rain_at_target"))
        event_date = features.get("significant_rain_event_date")
        event_amount = _number(features.get("significant_rain_event_amount_mm"))
        event_threshold = _number(features.get("significant_rain_threshold_mm"))
        if (
            found is True
            and isinstance(event_date, str)
            and event_date
            and event_amount is not None
            and days is not None
            and event_threshold is not None
        ):
            event_key = (
                event_date,
                round(event_amount, 3),
                int(round(days)),
                round(event_threshold, 3),
            )
            significant_rain_events[event_key] = {
                "date": event_key[0],
                "amount_mm": event_key[1],
                "days_since_target": event_key[2],
                "threshold_mm": event_key[3],
                "source": "area_idw_daily",
            }
        event_found = event_found or found is True
        current_timing = _timing(days, delay)
        timing_values.append(current_timing)
        active_event_found = active_event_found or (
            found is True and current_timing not in {"expired", "unknown"}
        )
    fruiting_timing = _combined_timing(timing_values)
    if active_event_found:
        weather_signal = "recent_event"
        reason_codes.append("significant_rain_event_detected")
    elif event_found and fruiting_timing == "expired":
        weather_signal = "old_event"
        reason_codes.append("significant_rain_event_too_old")
    elif event_found:
        weather_signal = "recent_event"
        reason_codes.append("significant_rain_event_detected")
    elif available_results:
        weather_signal = "no_event"
        reason_codes.append("no_significant_rain_event_90d")
    else:
        weather_signal = "unknown"

    if fruiting_timing != "unknown":
        reason_codes.append(f"fruiting_timing_{fruiting_timing}")
    delay_configured = any(
        (value := _number(delay.get(key))) is not None and value > 0
        for key in ("min", "optimal_min", "optimal_max", "max")
    )
    ecological_rain_mismatch = delay_configured and weather_signal in {
        "no_event",
        "old_event",
    }
    if ecological_rain_mismatch:
        ecological_compatibility = "incompatible"
    elif active_event_found:
        ecological_compatibility = "compatible"
    else:
        ecological_compatibility = "unknown"
    ecological_evidence = (
        "high"
        if len(available_results) == len(active_feature_set_ids)
        else "moderate"
        if available_results
        else "low"
    )
    # MOD_0001: deliberately do not mutate verdict, reference_range
    # or confidence from ecological_compatibility. The calculation above is
    # retained so that the advisory can be audited or reconsidered later.
    return {
        "schema_version": "1.1",
        "verdict": verdict,
        "reference_range": reference_range,
        "statistical_consensus": consensus,
        "statistical_support": statistical_support,
        "validated_estimator_ids": validated_estimator_ids,
        "validated_estimator_count": len(validated_estimator_ids),
        "experimental_signal": experimental_signal,
        "experimental_range": experimental_range,
        "experimental_results": experimental_results,
        "experimental_estimator_ids": experimental_estimator_ids,
        "experimental_out_of_domain_caution": experimental_out_of_domain_caution,
        "ecological_compatibility": ecological_compatibility,
        "ecological_evidence": ecological_evidence,
        "confidence": confidence,
        "weather_signal": weather_signal,
        "fruiting_timing": fruiting_timing,
        "significant_rain_events": sorted(
            significant_rain_events.values(),
            key=lambda row: (row["days_since_target"], row["date"]),
        ),
        "trusted_results": trusted,
        "unvalidated_signal": unvalidated_signal,
        "unvalidated_range": unvalidated_range,
        "severe_out_of_domain_features": severe_ood_features,
        "estimator_probability_gaps": estimator_gaps,
        "weather_stations_by_feature_set": stations_by_feature_set,
        "reason_codes": reason_codes,
    }
