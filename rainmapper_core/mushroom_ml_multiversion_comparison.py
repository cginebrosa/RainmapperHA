"""Execute exact installed V2--V6 members against one prepared weather context."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
from time import monotonic
from typing import Any, Mapping, MutableMapping, Sequence

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_raw_weather
from rainmapper_core import mushroom_ml_smooth_hierarchical
from rainmapper_core import mushroom_ml_runtime_features
from rainmapper_core import mushroom_ml_runtime_inference
from rainmapper_core import mushroom_ml_quality_catalog
from rainmapper_core import mushroom_ml_area_weather_runtime
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw
from rainmapper_core.mushroom_ml_predictor import _label
from rainmapper_core.mushroom_prediction_interpretation import (
    HIGH_AGREEMENT_GAP,
    LOW_AGREEMENT_GAP,
    build_interpretation,
)


V2_FIXED_CONTRACT_ID = "fixed_gap_7d_altitude_v2"
V2_LAG_CONTRACT_ID = "lag_event_altitude_v2"
MIN_OPERATIONAL_ROC_AUC = 0.55
HIGH_RELIABILITY_ROC_AUC = 0.80
HIGH_RELIABILITY_RELATIVE_BRIER_GAIN = 0.20
HIGH_RELIABILITY_TEST_SAMPLES = 50
HIGH_RELIABILITY_MIN_CLASS_SAMPLES = 10
MODERATE_RELIABILITY_ROC_AUC = 0.70
MODERATE_RELIABILITY_RELATIVE_BRIER_GAIN = 0.10
MODERATE_RELIABILITY_TEST_SAMPLES = 30
MODERATE_RELIABILITY_MIN_CLASS_SAMPLES = 5

METHODOLOGICAL_FAMILY_BY_ESTIMATOR = {
    "logistic_regression_reduced_v1": "logistic",
    "elastic_net_logistic_raw365_v1": "logistic",
    "sparse_group_logistic_raw365_v1": "logistic",
    "smooth_partial_pooling_logistic_v1": "logistic",
    "smooth_shared_logistic_v1": "logistic",
    "smooth_species_logistic_v1": "logistic",
    "random_forest_restricted_v1": "bagged_trees",
    "extra_trees_restricted_v1": "bagged_trees",
    "hist_gradient_boosting_restricted_v1": "boosting",
    "knn_distance_v1": "distance",
    "rbf_svm_calibrated_v1": "kernel",
}


def _load_quality_catalog(
    registry: Mapping[str, object],
    checked: Mapping[str, object],
    models_root: Path,
) -> dict[str, Any]:
    """Load declared evidence, with a verified promotion-source fallback."""
    quality_path: Path | None = None
    expected_sha = ""
    quality_ref = checked.get("quality_catalog")
    if isinstance(quality_ref, Mapping):
        quality_path = Path(models_root) / str(quality_ref.get("path") or "")
        expected_sha = str(quality_ref.get("sha256") or "")
    if quality_path is None or not quality_path.is_file() or not expected_sha:
        return {}
    content = quality_path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha:
        return {}
    loaded = json.loads(content)
    if (
        not isinstance(loaded, dict)
        or loaded.get("kind") != mushroom_ml_quality_catalog.KIND
        or loaded.get("schema_version") != mushroom_ml_quality_catalog.SCHEMA_VERSION
    ):
        return {}
    return loaded


def _interpretation_features(sample: Mapping[str, object]) -> dict[str, object]:
    """Keep model inputs pure while forwarding ecological evidence to interpretation.

    Version adapters may wrap the source quality mapping (for example V4 wraps
    the V3 evidence).  Walk every nested quality mapping so a new profile or
    version cannot silently lose the common ecological contract merely because
    it adds another adapter layer.
    """
    features = dict(sample.get("predictive_features") or {})
    quality = sample.get("quality")
    quality = quality if isinstance(quality, Mapping) else {}
    quality_sources: list[Mapping[str, object]] = []
    pending: list[Mapping[str, object]] = [quality]
    while pending:
        source = pending.pop(0)
        quality_sources.append(source)
        pending.extend(
            value for value in source.values() if isinstance(value, Mapping)
        )
    for key in (
        "days_since_significant_rain_at_target",
        "significant_rain_found_90d",
        "significant_rain_search_complete",
        "rain_event_search_complete",
    ):
        for source in quality_sources:
            if key in source:
                features[key] = source[key]
                break
    return features


def compare_prepared(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    model_refs: Sequence[catalog.ModelRef | Mapping[str, object]],
    *,
    models_root: Path,
    target_date: date,
    area_id: str,
    area_context: Any,
    area_series_by_horizon: Mapping[int, Mapping[str, object]],
    stations: Mapping[tuple[str, str], Any],
    checked_manifest: Mapping[str, object] | None = None,
    comparison_cache: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare individual members; quality precedes output and no mean is made."""
    started = monotonic()
    phase_seconds: dict[str, float] = {}

    def record_phase(name: str, phase_started: float) -> None:
        phase_seconds[name] = phase_seconds.get(name, 0.0) + (
            monotonic() - phase_started
        )

    phase_started = monotonic()
    checked = (
        checked_manifest
        if checked_manifest is not None
        else catalog.validate_batch_manifest(registry, manifest)
    )
    record_phase("manifest_validation", phase_started)
    phase_started = monotonic()
    quality_catalog = (
        comparison_cache.get("quality_catalog")
        if comparison_cache is not None
        else None
    )
    if not isinstance(quality_catalog, dict):
        quality_catalog = _load_quality_catalog(registry, checked, models_root)
        if comparison_cache is not None:
            comparison_cache["quality_catalog"] = quality_catalog
    record_phase("quality_catalog", phase_started)
    phase_started = monotonic()
    artifact_index = (
        comparison_cache.get("artifact_index")
        if comparison_cache is not None
        else None
    )
    if not isinstance(artifact_index, dict):
        artifact_index = {
            (
                row["artifact_ref"]["version_id"],
                row["artifact_ref"]["temporal_contract_id"],
                row["artifact_ref"]["profile_id"],
                row["artifact_ref"]["estimator_id"],
                row["artifact_ref"]["species_id"],
                horizon,
            ): row
            for row in checked["artifacts"]
            for horizon in row["supported_horizons"]
        }
        if comparison_cache is not None:
            comparison_cache["artifact_index"] = artifact_index
    record_phase("artifact_index", phase_started)
    results: list[dict[str, Any] | None] = [None] * len(model_refs)
    pending_by_artifact: dict[tuple[str, str], list[dict[str, Any]]] = {}
    prediction_result_cache = (
        comparison_cache.setdefault("prediction_result_cache", {})
        if comparison_cache is not None
        else {}
    )
    runtime_sample_cache = (
        comparison_cache.setdefault("runtime_sample_cache", {})
        if comparison_cache is not None
        else {}
    )
    for result_index, raw_ref in enumerate(model_refs):
        model_ref = (
            raw_ref
            if isinstance(raw_ref, catalog.ModelRef)
            else catalog.validate_model_ref(registry, raw_ref)
        )
        base = {"model_ref": model_ref.as_dict(), "model_ref_key": model_ref.key}
        area_series = area_series_by_horizon.get(model_ref.horizon_days)
        if area_series is None:
            results[result_index] = {
                    **base,
                    "available": False,
                    "reason": "prepared_weather_horizon_missing",
                }
            continue
        try:
            phase_started = monotonic()
            sample_cache_key = (area_id, target_date.isoformat(), model_ref.key)
            sample = runtime_sample_cache.get(sample_cache_key)
            if not isinstance(sample, Mapping):
                sample = mushroom_ml_runtime_features.build_runtime_features(
                    model_ref,
                    target_date=target_date,
                    area_id=area_id,
                    area_context=area_context,
                    area_series=area_series,
                    stations=stations,
                )
                runtime_sample_cache[sample_cache_key] = sample
            record_phase("runtime_features", phase_started)
            quality = dict(sample.get("quality") or {})
            if quality.get("inference_eligible") is False:
                results[result_index] = {
                        **base,
                        "available": False,
                        "reason": "runtime_feature_gates_failed",
                        "quality": quality,
                        "metadata": dict(sample.get("metadata") or {}),
                    }
                continue
            artifact_key = (
                model_ref.version_id,
                model_ref.temporal_contract_id,
                model_ref.profile_id,
                model_ref.estimator_id,
                model_ref.species_id,
                model_ref.horizon_days,
            )
            shared_key = (*artifact_key[:4], "all_species", artifact_key[5])
            artifact_row = artifact_index.get(artifact_key) or artifact_index.get(
                shared_key
            )
            if artifact_row is None:
                raise FileNotFoundError(
                    f"Model is not present in runtime batch: {model_ref.key}"
                )
            artifact_identity = (
                str(artifact_row["path"]),
                str(artifact_row["sha256"]),
            )
            prediction_cache_key = (
                area_id,
                target_date.isoformat(),
                model_ref.key,
            )
            cached_prediction = prediction_result_cache.get(prediction_cache_key)
            if isinstance(cached_prediction, Mapping):
                phase_started = monotonic()
                evaluation = mushroom_ml_quality_catalog.lookup(
                    quality_catalog, model_ref.as_dict()
                )
                record_phase("quality_lookup", phase_started)
                results[result_index] = {
                    **base,
                    "available": True,
                    "prediction": dict(cached_prediction),
                    "quality": quality,
                    "metadata": dict(sample.get("metadata") or {}),
                    "evaluation": evaluation,
                    "features_used": _interpretation_features(sample),
                }
                continue
            pending_by_artifact.setdefault(artifact_identity, []).append(
                {
                    "result_index": result_index,
                    "base": base,
                    "model_ref": model_ref,
                    "artifact_row": artifact_row,
                    "features": dict(sample.get("predictive_features") or {}),
                    "quality": quality,
                    "metadata": dict(sample.get("metadata") or {}),
                    "features_used": _interpretation_features(sample),
                }
            )
        except FileNotFoundError as exc:
            results[result_index] = {
                    **base,
                    "available": False,
                    "reason": "model_not_installed",
                    "message": str(exc),
                }
        except (KeyError, TypeError, ValueError) as exc:
            results[result_index] = {
                    **base,
                    "available": False,
                    "reason": "runtime_model_incompatible",
                    "message": str(exc),
                }

    for pending in pending_by_artifact.values():
        first = pending[0]
        try:
            phase_started = monotonic()
            bundle = mushroom_ml_runtime_inference.load_exact_artifact(
                registry,
                checked,
                first["model_ref"],
                root=models_root,
                checked_manifest=checked,
                artifact_row=first["artifact_row"],
                validated_model_ref=first["model_ref"],
            )
            record_phase("artifact_load", phase_started)
            phase_started = monotonic()
            predictions = mushroom_ml_runtime_inference.predict_bundle_many(
                bundle,
                [row["features"] for row in pending],
                species_ids=[row["model_ref"].species_id for row in pending],
            )
            record_phase("model_inference", phase_started)
            for row, prediction in zip(pending, predictions, strict=True):
                phase_started = monotonic()
                evaluation = mushroom_ml_quality_catalog.lookup(
                    quality_catalog, row["model_ref"].as_dict()
                )
                record_phase("quality_lookup", phase_started)
                results[row["result_index"]] = {
                    **row["base"],
                    "available": True,
                    "prediction": prediction,
                    "quality": row["quality"],
                    "metadata": row["metadata"],
                    "evaluation": evaluation,
                    "features_used": row["features_used"],
                }
                prediction_result_cache[
                    (
                        area_id,
                        target_date.isoformat(),
                        row["model_ref"].key,
                    )
                ] = dict(prediction)
        except FileNotFoundError as exc:
            for row in pending:
                results[row["result_index"]] = {
                    **row["base"],
                    "available": False,
                    "reason": "model_not_installed",
                    "message": str(exc),
                }
        except (KeyError, TypeError, ValueError) as exc:
            for row in pending:
                results[row["result_index"]] = {
                    **row["base"],
                    "available": False,
                    "reason": "runtime_model_incompatible",
                    "message": str(exc),
                }

    completed_results = [row for row in results if row is not None]
    if len(completed_results) != len(model_refs):
        raise RuntimeError("Multiversion comparison did not resolve every member")
    return {
        "batch_id": checked["batch_id"],
        "snapshot_id": checked["snapshot_id"],
        "area_id": area_id,
        "target_date": target_date.isoformat(),
        "members": completed_results,
        "quality_before_consensus": True,
        "consensus_computed": False,
        "ensemble_computed": False,
        "version_cautions": dict(quality_catalog.get("version_cautions") or {}),
        "species_metrics_are_never_averaged": True,
        "runtime_metrics": {
            "backend_seconds": round(monotonic() - started, 6),
            "phase_seconds": {
                key: round(value, 6) for key, value in phase_seconds.items()
            },
            "member_count": len(model_refs),
        },
    }


def operational_selections(
    selections: Sequence[Mapping[str, object]],
    *,
    target_date: date,
    issue_date: date,
) -> list[dict[str, object]]:
    """Keep the single horizon that can contribute to one dated prediction."""
    lag_horizon = (target_date - (issue_date - timedelta(days=1))).days
    selected: list[dict[str, object]] = []
    for row in selections:
        contract_id = str(row.get("temporal_contract_id") or "")
        expected_horizon = 7 if contract_id.startswith("fixed_gap_") else lag_horizon
        try:
            horizon = int(row.get("horizon_days") or 0)
        except (TypeError, ValueError):
            continue
        if horizon == expected_horizon:
            selected.append(dict(row))
    return selected


def retarget_operational_selections(
    selections: Sequence[Mapping[str, object]],
    *,
    target_date: date,
    issue_date: date,
) -> list[dict[str, object]]:
    """Reuse the selected models with the horizon required by another date."""
    lag_horizon = (target_date - (issue_date - timedelta(days=1))).days
    retargeted: list[dict[str, object]] = []
    for row in selections:
        contract_id = str(row.get("temporal_contract_id") or "")
        horizon = 7 if contract_id.startswith("fixed_gap_") else lag_horizon
        if horizon not in range(1, 8):
            continue
        candidate = {**dict(row), "horizon_days": horizon}
        if candidate not in retargeted:
            retargeted.append(candidate)
    return retargeted


def _selected_member_rank(
    member: Mapping[str, object],
) -> tuple[float, float, float, str]:
    evaluation = member.get("evaluation") or {}
    evaluation = evaluation if isinstance(evaluation, Mapping) else {}
    delta = evaluation.get("brier_delta_vs_prevalence")
    brier = evaluation.get("brier_score")
    improvement = float(delta) if isinstance(delta, (int, float)) else -999.0
    score = float(brier) if isinstance(brier, (int, float)) else 999.0
    roc_auc = evaluation.get("roc_auc")
    discrimination = (
        float(roc_auc) if isinstance(roc_auc, (int, float)) else -999.0
    )
    ref = member.get("model_ref") or {}
    identity = json.dumps(ref, sort_keys=True, separators=(",", ":"))
    return (-improvement, score, -discrimination, identity)


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _operational_gate_failures(member: Mapping[str, object]) -> list[str]:
    """Explain why one runtime member cannot enter operational ranking."""
    if member.get("available") is not True:
        return ["member_unavailable"]
    failures: list[str] = []
    prediction = member.get("prediction") or {}
    prediction = prediction if isinstance(prediction, Mapping) else {}
    applicability = prediction.get("applicability") or {}
    applicability = applicability if isinstance(applicability, Mapping) else {}
    if str(applicability.get("status") or "") not in {
        "within_observed_range",
        "caution",
    }:
        failures.append("unacceptable_applicability")
    probability = _finite_number(prediction.get("probability"))
    if probability is None or not 0.0 <= probability <= 1.0:
        failures.append("invalid_probability")

    evaluation = member.get("evaluation") or {}
    evaluation = evaluation if isinstance(evaluation, Mapping) else {}
    brier = _finite_number(evaluation.get("brier_score"))
    baseline = _finite_number(evaluation.get("prevalence_brier_score"))
    if (
        evaluation.get("evidence") != "better_than_prevalence"
        or brier is None
        or baseline is None
        or brier >= baseline
    ):
        failures.append("brier_not_better_than_prevalence")
    roc_auc = _finite_number(evaluation.get("roc_auc"))
    if roc_auc is None:
        failures.append("roc_auc_unavailable")
    elif roc_auc < MIN_OPERATIONAL_ROC_AUC:
        failures.append("roc_auc_below_minimum")
    return failures


def _winner_statistical_reliability(
    evaluation: Mapping[str, object],
    prediction: Mapping[str, object],
) -> dict[str, object]:
    """Grade the selected winner without mixing reliability with consensus."""
    baseline = _finite_number(evaluation.get("prevalence_brier_score"))
    improvement = _finite_number(evaluation.get("brier_delta_vs_prevalence"))
    roc_auc = _finite_number(evaluation.get("roc_auc"))
    relative_gain = (
        improvement / baseline
        if improvement is not None and baseline is not None and baseline > 0.0
        else None
    )
    n_test = evaluation.get("n_test")
    positive_count = evaluation.get("test_positive_count")
    negative_count = evaluation.get("test_negative_count")
    class_minimum = (
        min(int(positive_count), int(negative_count))
        if isinstance(positive_count, int)
        and not isinstance(positive_count, bool)
        and isinstance(negative_count, int)
        and not isinstance(negative_count, bool)
        else None
    )
    applicability = prediction.get("applicability") or {}
    applicability = applicability if isinstance(applicability, Mapping) else {}
    applicability_status = str(applicability.get("status") or "")
    high = (
        roc_auc is not None
        and roc_auc >= HIGH_RELIABILITY_ROC_AUC
        and relative_gain is not None
        and relative_gain >= HIGH_RELIABILITY_RELATIVE_BRIER_GAIN
        and isinstance(n_test, int)
        and not isinstance(n_test, bool)
        and n_test >= HIGH_RELIABILITY_TEST_SAMPLES
        and class_minimum is not None
        and class_minimum >= HIGH_RELIABILITY_MIN_CLASS_SAMPLES
        and applicability_status == "within_observed_range"
    )
    moderate = (
        roc_auc is not None
        and roc_auc >= MODERATE_RELIABILITY_ROC_AUC
        and relative_gain is not None
        and relative_gain >= MODERATE_RELIABILITY_RELATIVE_BRIER_GAIN
        and isinstance(n_test, int)
        and not isinstance(n_test, bool)
        and n_test >= MODERATE_RELIABILITY_TEST_SAMPLES
        and class_minimum is not None
        and class_minimum >= MODERATE_RELIABILITY_MIN_CLASS_SAMPLES
        and applicability_status in {"within_observed_range", "caution"}
    )
    return {
        "status": "high" if high else "moderate" if moderate else "limited",
        "relative_brier_gain": (
            round(relative_gain, 6) if relative_gain is not None else None
        ),
        "test_samples": n_test,
        "test_positive_count": positive_count,
        "test_negative_count": negative_count,
        "applicability_status": applicability_status,
    }


def _build_statistical_summaries(comparison: dict[str, Any]) -> None:
    """Attach glanceable verdicts while retaining all per-scenario evidence."""
    winners = [
        row
        for row in comparison.get("selected_winners") or []
        if isinstance(row, dict)
    ]
    reliability_rank = {"unavailable": 0, "limited": 1, "moderate": 2, "high": 3}
    reliability_statuses = [
        str((row.get("statistical_reliability") or {}).get("status") or "unavailable")
        for row in winners
    ]
    scenario_count = len(comparison.get("operational_result_keys") or [])
    if not reliability_statuses or len(reliability_statuses) < scenario_count:
        reliability_status = "unavailable"
    else:
        reliability_status = min(
            reliability_statuses, key=lambda value: reliability_rank.get(value, 0)
        )
    comparison["statistical_reliability_summary"] = {
        "status": reliability_status,
        "evaluated_scenario_count": len(reliability_statuses),
        "scenario_count": scenario_count,
    }

    winner_result_keys = {str(row.get("result_key") or "") for row in winners}
    consensus_rows = [
        row
        for row in comparison.get("scenario_consensus") or []
        if isinstance(row, dict)
        and str(row.get("result_key") or "") in winner_result_keys
    ]
    measurable = [
        row for row in consensus_rows if row.get("status") in {"high", "moderate", "low"}
    ]
    consensus_rank = {"low": 1, "moderate": 2, "high": 3}
    consensus_status = (
        min(
            (str(row["status"]) for row in measurable),
            key=lambda value: consensus_rank[value],
        )
        if measurable
        else "unavailable"
    )
    comparison["consensus_summary"] = {
        "status": consensus_status,
        "measurable_scenario_count": len(measurable),
        "eligible_scenario_count": len(consensus_rows),
        "coverage": (
            "complete" if consensus_rows and len(measurable) == len(consensus_rows)
            else "partial" if measurable
            else "unavailable"
        ),
    }


def _eligible_family_summary(
    candidates: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Separate within-method variants from independent method families."""
    by_estimator: dict[str, list[Mapping[str, object]]] = {}
    for member in candidates:
        ref = member.get("model_ref") or {}
        if not isinstance(ref, Mapping):
            continue
        estimator_id = str(ref.get("estimator_id") or "")
        if estimator_id:
            by_estimator.setdefault(estimator_id, []).append(member)

    estimator_representatives: list[dict[str, object]] = []
    for estimator_id, family_members in sorted(by_estimator.items()):
        representative = min(family_members, key=_selected_member_rank)
        ref = dict(representative.get("model_ref") or {})
        prediction = representative.get("prediction") or {}
        prediction = prediction if isinstance(prediction, Mapping) else {}
        evaluation = representative.get("evaluation") or {}
        evaluation = evaluation if isinstance(evaluation, Mapping) else {}
        estimator_representatives.append(
            {
                "estimator_id": estimator_id,
                "methodological_family_id": METHODOLOGICAL_FAMILY_BY_ESTIMATOR.get(
                    estimator_id, f"estimator:{estimator_id}"
                ),
                "model_ref": ref,
                "probability": round(float(prediction["probability"]), 6),
                "brier_score": evaluation.get("brier_score"),
                "brier_delta_vs_prevalence": evaluation.get(
                    "brier_delta_vs_prevalence"
                ),
                "roc_auc": evaluation.get("roc_auc"),
                "represented_member_count": len(family_members),
            }
        )

    by_methodological_family: dict[str, list[dict[str, object]]] = {}
    for row in estimator_representatives:
        family_id = str(row["methodological_family_id"])
        by_methodological_family.setdefault(family_id, []).append(row)

    methodological_families: list[dict[str, object]] = []
    family_representatives: list[dict[str, object]] = []
    for family_id, estimator_rows in sorted(by_methodological_family.items()):
        raw_members = [
            member
            for member in candidates
            if METHODOLOGICAL_FAMILY_BY_ESTIMATOR.get(
                str((member.get("model_ref") or {}).get("estimator_id") or ""),
                "estimator:"
                + str((member.get("model_ref") or {}).get("estimator_id") or ""),
            )
            == family_id
        ]
        representative_member = min(raw_members, key=_selected_member_rank)
        representative_ref = dict(representative_member.get("model_ref") or {})
        representative_estimator_id = str(
            representative_ref.get("estimator_id") or ""
        )
        representative = next(
            row
            for row in estimator_rows
            if row["estimator_id"] == representative_estimator_id
        )
        internal_probabilities = [float(row["probability"]) for row in estimator_rows]
        internal_gap = (
            round(max(internal_probabilities) - min(internal_probabilities), 6)
            if len(internal_probabilities) >= 2
            else None
        )
        if internal_gap is None:
            internal_status = "single_variant"
        elif internal_gap >= LOW_AGREEMENT_GAP:
            internal_status = "low"
        elif internal_gap <= HIGH_AGREEMENT_GAP:
            internal_status = "high"
        else:
            internal_status = "moderate"
        methodological_families.append(
            {
                "methodological_family_id": family_id,
                "estimator_ids": [str(row["estimator_id"]) for row in estimator_rows],
                "estimator_count": len(estimator_rows),
                "represented_member_count": len(raw_members),
                "internal_agreement_status": internal_status,
                "internal_maximum_probability_gap": internal_gap,
                "estimator_representatives": estimator_rows,
                "representative": representative,
            }
        )
        family_representatives.append(representative)

    probabilities = [float(row["probability"]) for row in family_representatives]
    maximum_gap = (
        round(max(probabilities) - min(probabilities), 6)
        if len(probabilities) >= 2
        else None
    )
    if not family_representatives:
        status = "no_eligible_family"
    elif len(family_representatives) == 1:
        status = "single_family"
    elif maximum_gap is not None and maximum_gap >= LOW_AGREEMENT_GAP:
        status = "low"
    elif maximum_gap is not None and maximum_gap <= HIGH_AGREEMENT_GAP:
        status = "high"
    else:
        status = "moderate"
    return {
        "status": status,
        "eligible_family_count": len(family_representatives),
        "eligible_methodological_family_ids": [
            str(row["methodological_family_id"])
            for row in methodological_families
        ],
        "eligible_estimator_ids": [
            str(row["estimator_id"]) for row in estimator_representatives
        ],
        "maximum_probability_gap": maximum_gap,
        "family_representatives": family_representatives,
        "methodological_families": methodological_families,
    }


def build_selected_operational_comparison(
    members: Sequence[Mapping[str, object]],
    *,
    season_phase: str,
    phenology: Mapping[str, object] | None = None,
    selection_mode: str = "multiversion",
) -> dict[str, Any]:
    """Choose one auditable member per version and scenario, then across versions."""
    grouped: dict[tuple[str, int], list[Mapping[str, object]]] = {}
    selected_versions: set[str] = set()
    for member in members:
        ref = member.get("model_ref") or {}
        if not isinstance(ref, Mapping):
            continue
        version_id = str(ref.get("version_id") or "")
        if version_id:
            selected_versions.add(version_id)
        contract_id = str(ref.get("temporal_contract_id") or "")
        family = "fixed" if contract_id.startswith("fixed_gap_") else "lag"
        try:
            horizon = int(ref.get("horizon_days") or 0)
        except (TypeError, ValueError):
            continue
        grouped.setdefault((family, horizon), []).append(member)

    comparison: dict[str, Any] = {
        "selection_mode": selection_mode,
        "minimum_roc_auc": MIN_OPERATIONAL_ROC_AUC,
        "consensus_computed": True,
        "selected_version_ids": sorted(selected_versions),
        "operational_result_keys": [],
        "selected_winners": [],
        "scenario_consensus": [],
    }
    for (family, horizon), candidates in sorted(grouped.items()):
        result_key = f"selected:{family}:h{horizon}"
        comparison["operational_result_keys"].append(result_key)
        eligible_by_version: dict[str, list[Mapping[str, object]]] = {}
        candidate_exclusions: list[dict[str, object]] = []
        for member in candidates:
            failures = _operational_gate_failures(member)
            if failures:
                candidate_exclusions.append(
                    {
                        "model_ref": dict(member.get("model_ref") or {}),
                        "reasons": failures,
                    }
                )
                continue
            ref = member.get("model_ref") or {}
            version_id = str(ref.get("version_id") or "")
            eligible_by_version.setdefault(version_id, []).append(member)
        if not eligible_by_version:
            comparison[result_key] = {
                "available": False,
                "reason": "no_eligible_selected_member",
                "horizon_days": horizon,
                "minimum_roc_auc": MIN_OPERATIONAL_ROC_AUC,
                "candidate_exclusions": candidate_exclusions,
            }
            comparison["scenario_consensus"].append(
                {
                    "result_key": result_key,
                    "temporal_family": family,
                    "horizon_days": horizon,
                    **_eligible_family_summary([]),
                }
            )
            continue
        eligible_candidates = [
            member
            for version_candidates in eligible_by_version.values()
            for member in version_candidates
        ]
        family_summary = _eligible_family_summary(eligible_candidates)
        version_winners = {
            version_id: min(version_candidates, key=_selected_member_rank)
            for version_id, version_candidates in eligible_by_version.items()
        }
        winner = min(version_winners.values(), key=_selected_member_rank)
        ref = dict(winner.get("model_ref") or {})
        prediction = dict(winner.get("prediction") or {})
        evaluation = dict(winner.get("evaluation") or {})
        estimator_id = str(ref.get("estimator_id") or "")
        probability = float(prediction["probability"])
        brier = evaluation.get("brier_score")
        baseline = evaluation.get("prevalence_brier_score")
        result = {
            "available": True,
            "feature_set_id": result_key,
            "horizon_days": horizon,
            "temporal_family": family,
            "selected_model_ref": ref,
            "selected_model_validated": True,
            "minimum_roc_auc": MIN_OPERATIONAL_ROC_AUC,
            "candidate_exclusions": candidate_exclusions,
            "eligible_candidates": [
                {
                    "model_ref": dict(member.get("model_ref") or {}),
                    "probability": round(
                        float((member.get("prediction") or {})["probability"]), 6
                    ),
                    "brier_score": (member.get("evaluation") or {}).get(
                        "brier_score"
                    ),
                    "brier_delta_vs_prevalence": (
                        member.get("evaluation") or {}
                    ).get("brier_delta_vs_prevalence"),
                    "roc_auc": (member.get("evaluation") or {}).get("roc_auc"),
                }
                for member in sorted(eligible_candidates, key=_selected_member_rank)
            ],
            "version_winners": {
                version_id: dict(member.get("model_ref") or {})
                for version_id, member in sorted(version_winners.items())
            },
            "estimator_probabilities": {estimator_id: probability},
            "interpretation_estimator_probabilities": {estimator_id: probability},
            "estimator_exclusions": {},
            "features_used": dict(winner.get("features_used") or {}),
            "evaluation": {
                "available": isinstance(brier, (int, float))
                and isinstance(baseline, (int, float)),
                "baseline": {"brier_score": baseline},
                "estimators": {
                    estimator_id: {
                        "brier_score": brier,
                        "roc_auc": evaluation.get("roc_auc"),
                        "n": evaluation.get("n_test"),
                    }
                },
            },
        }
        comparison[result_key] = result
        comparison["scenario_consensus"].append(
            {
                "result_key": result_key,
                "temporal_family": family,
                "horizon_days": horizon,
                **family_summary,
            }
        )
        comparison["selected_winners"].append(
            {
                "result_key": result_key,
                "model_ref": ref,
                "probability": round(probability, 6),
                "validated": True,
                "applicability_status": str(
                    (prediction.get("applicability") or {}).get("status") or ""
                ),
                "brier_score": brier,
                "prevalence_brier_score": baseline,
                "brier_delta_vs_prevalence": evaluation.get(
                    "brier_delta_vs_prevalence"
                ),
                "roc_auc": evaluation.get("roc_auc"),
                "test_samples": evaluation.get("n_test"),
                "test_positive_count": evaluation.get("test_positive_count"),
                "test_negative_count": evaluation.get("test_negative_count"),
                "statistical_reliability": _winner_statistical_reliability(
                    evaluation, prediction
                ),
            }
        )
    _build_statistical_summaries(comparison)
    comparison["interpretation"] = build_interpretation(
        comparison,
        season_phase=season_phase,
        phenology=dict(phenology or {}),
        feature_set_ids=comparison["operational_result_keys"],
    )
    return comparison


def _contract_result(
    contract_id: str,
    members: Sequence[Mapping[str, object]],
    *,
    horizon_days: int,
    profile_id: str | None = None,
) -> dict[str, Any]:
    matching = [
        row
        for row in members
        if str((row.get("model_ref") or {}).get("temporal_contract_id") or "")
        == contract_id
        and (
            profile_id is None
            or str((row.get("model_ref") or {}).get("profile_id") or "")
            == profile_id
        )
    ]
    available = [row for row in matching if row.get("available") is True]
    if not available:
        first = matching[0] if matching else {}
        return {
            "available": False,
            "reason": str(first.get("reason") or "model_not_installed"),
            "horizon_days": horizon_days,
        }
    probabilities: dict[str, float] = {}
    estimators: dict[str, dict[str, object]] = {}
    baseline_scores: list[float] = []
    exclusions: dict[str, dict[str, object]] = {}
    for row in available:
        model_ref = row.get("model_ref") or {}
        estimator_id = str(model_ref.get("estimator_id") or "")
        prediction = row.get("prediction") or {}
        probability = prediction.get("probability")
        if estimator_id and isinstance(probability, (int, float)):
            probabilities[estimator_id] = float(probability)
        evaluation = row.get("evaluation") or {}
        brier = evaluation.get("brier_score")
        baseline = evaluation.get("prevalence_brier_score")
        if isinstance(baseline, (int, float)):
            baseline_scores.append(float(baseline))
        if estimator_id and isinstance(brier, (int, float)):
            estimators[estimator_id] = {
                "brier_score": float(brier),
                "roc_auc": evaluation.get("roc_auc"),
                "n": evaluation.get("n_test"),
            }
        extreme = list((prediction.get("applicability") or {}).get("most_extreme") or [])
        if estimator_id == "logistic_regression_reduced_v1" and any(
            isinstance(item, Mapping)
            and isinstance(item.get("standard_deviations"), (int, float))
            and float(item["standard_deviations"]) >= 6.0
            for item in extreme
        ):
            exclusions[estimator_id] = {"reason": "severe_feature_extrapolation"}
    mean_probability = (
        sum(probabilities.values()) / len(probabilities) if probabilities else None
    )
    first = available[0]
    metadata = dict(first.get("metadata") or {})
    return {
        "available": True,
        "feature_set_id": contract_id,
        "cutoff_date": metadata.get("cutoff_date"),
        "horizon_days": horizon_days,
        "spatial_weather_contract": "common_multisource_idw_by_microarea",
        "estimator_probabilities": probabilities,
        "interpretation_estimator_probabilities": probabilities,
        "ensemble_probability": (
            round(mean_probability, 6) if mean_probability is not None else None
        ),
        "label": _label(mean_probability),
        "features_used": dict(first.get("features_used") or {}),
        "estimator_exclusions": exclusions,
        "evaluation": {
            "available": bool(estimators and baseline_scores),
            "baseline": {
                "brier_score": min(baseline_scores) if baseline_scores else None
            },
            "estimators": estimators,
        },
        "member_count": len(available),
    }


def compare_operational_reference(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    species_id: str,
    area_id: str,
    target_date: date,
    issue_date: date,
    season_phase: str,
    phenology: Mapping[str, object] | None,
    models_root: Path,
    known_sites_path: Path,
    weather_data_dir: Path,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]] = frozenset(),
    prepared_weather_cache: MutableMapping[
        tuple[object, ...], tuple[Any, dict[int, dict[str, object]], dict[tuple[str, str], Any]]
    ]
    | None = None,
    comparison_cache: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the operational card from every profile in the preferred version."""
    version_id = str(registry.get("preferred_version_id") or "")
    profiles = [
        row
        for row in catalog.catalog_entries(registry)
        if row["version_id"] == version_id and row["operational_eligible"] is True
    ]
    if not profiles:
        raise ValueError("The preferred version has no operational profiles")
    payload: dict[str, Any] = {
        "issue_date": issue_date.isoformat(),
        "target_date": target_date.isoformat(),
        "season_phase": season_phase,
    }
    result_specs: list[tuple[str, dict[str, Any], str, int]] = []
    lag_horizon = (target_date - (issue_date - timedelta(days=1))).days
    single_profile = len(profiles) == 1
    for profile in profiles:
        for contract_id in profile["temporal_contract_ids"]:
            horizon = 7 if str(contract_id).startswith("fixed_") else lag_horizon
            result_key = str(contract_id) if single_profile else f"{profile['profile_id']}:{contract_id}"
            result_specs.append((result_key, profile, str(contract_id), horizon))
    payload["preferred_version_id"] = version_id
    payload["operational_result_keys"] = [row[0] for row in result_specs]
    payload["operational_profiles"] = [
        {
            "profile_id": row["profile_id"],
            "profile_name": row["profile_display_name"],
            "result_keys": [key for key, profile, _contract, _horizon in result_specs if profile["profile_id"] == row["profile_id"]],
        }
        for row in profiles
    ]
    if season_phase == "out_of_season":
        for result_key, _profile, _contract_id, _horizon in result_specs:
            payload[result_key] = {"available": False, "reason": "out_of_season"}
        payload["interpretation"] = build_interpretation(
            payload,
            season_phase=season_phase,
            phenology=dict(phenology or {}),
            feature_set_ids=payload["operational_result_keys"],
        )
        payload["selection_mode"] = "preferred_version"
        payload["comparison_detail_result_keys"] = list(
            payload["operational_result_keys"]
        )
        payload["selected_winners"] = []
        payload["minimum_roc_auc"] = MIN_OPERATIONAL_ROC_AUC
        return payload

    checked = (
        comparison_cache.get("checked_manifest")
        if comparison_cache is not None
        else None
    )
    if not isinstance(checked, Mapping):
        checked = catalog.validate_batch_manifest(registry, manifest)
        if comparison_cache is not None:
            comparison_cache["checked_manifest"] = checked
    selections: list[dict[str, object]] = []
    for _result_key, profile, contract_id, horizon in result_specs:
        for row in checked["artifacts"]:
            artifact_ref = row["artifact_ref"]
            if (
                artifact_ref["version_id"] == version_id
                and artifact_ref["temporal_contract_id"] == contract_id
                and artifact_ref["profile_id"] == profile["profile_id"]
                and artifact_ref["species_id"] == species_id
                and horizon in row["supported_horizons"]
            ):
                selections.append(
                    {
                        "version_id": version_id,
                        "temporal_contract_id": contract_id,
                        "profile_id": profile["profile_id"],
                        "estimator_id": artifact_ref["estimator_id"],
                        "horizon_days": horizon,
                    }
                )
    runtime = (
        compare_selection(
            registry,
            checked,
            selections,
            species_id=species_id,
            area_id=area_id,
            target_date=target_date,
            models_root=models_root,
            known_sites_path=known_sites_path,
            weather_data_dir=weather_data_dir,
            excluded_station_keys=excluded_station_keys,
            prepared_weather_cache=prepared_weather_cache,
            checked_manifest=checked,
            comparison_cache=comparison_cache,
        )
        if selections
        else {"members": []}
    )
    members = list(runtime.get("members") or [])
    detail_results: dict[str, dict[str, Any]] = {}
    for result_key, profile, contract_id, horizon in result_specs:
        detail_results[result_key] = _contract_result(
            contract_id,
            members,
            horizon_days=horizon,
            profile_id=str(profile["profile_id"]),
        )
        detail_results[result_key]["profile_id"] = profile["profile_id"]
        detail_results[result_key]["profile_name"] = profile["profile_display_name"]
        detail_results[result_key]["temporal_contract_id"] = contract_id
    selected = build_selected_operational_comparison(
        members,
        season_phase=season_phase,
        phenology=phenology,
        selection_mode="preferred_version",
    )
    selected.update(detail_results)
    selected["comparison_detail_result_keys"] = [row[0] for row in result_specs]
    selected["operational_profiles"] = payload["operational_profiles"]
    selected["preferred_version_id"] = version_id
    selected["issue_date"] = issue_date.isoformat()
    selected["target_date"] = target_date.isoformat()
    selected["season_phase"] = season_phase
    selected["runtime_batch_id"] = checked["batch_id"]
    selected["runtime_metrics"] = dict(runtime.get("runtime_metrics") or {})
    selected["spatial_weather_contract"] = "common_multisource_idw_by_microarea"
    return selected


def compare_v2_reference(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Backward-compatible name for the now registry-driven operational card."""
    return compare_operational_reference(*args, **kwargs)


def resolve_selection(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    selection: Mapping[str, object],
    *,
    species_id: str,
    checked_manifest: Mapping[str, object] | None = None,
    catalog_profiles: Sequence[Mapping[str, object]] | None = None,
) -> catalog.ModelRef:
    """Resolve UI selection to the exact installed generation and batch."""
    checked = (
        checked_manifest
        if checked_manifest is not None
        else catalog.validate_batch_manifest(registry, manifest)
    )
    version_id = str(selection.get("version_id") or "")
    temporal_contract_id = str(selection.get("temporal_contract_id") or "")
    profile_id = str(selection.get("profile_id") or "")
    estimator_id = str(selection.get("estimator_id") or "")
    try:
        horizon_days = int(selection.get("horizon_days") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Comparison horizon is invalid") from exc
    profile = next(
        (
            row
            for row in (
                catalog_profiles
                if catalog_profiles is not None
                else catalog.catalog_entries(registry)
            )
            if row["version_id"] == version_id and row["profile_id"] == profile_id
        ),
        None,
    )
    if profile is None or estimator_id not in profile["estimator_ids"]:
        raise ValueError("Comparison selection is not in the runtime catalog")
    artifact_species = (
        "all_species"
        if profile["estimator_scopes"][estimator_id] == "shared"
        else species_id
    )
    artifact = next(
        (
            row
            for row in checked["artifacts"]
            if row["artifact_ref"]["version_id"] == version_id
            and row["artifact_ref"]["temporal_contract_id"] == temporal_contract_id
            and row["artifact_ref"]["profile_id"] == profile_id
            and row["artifact_ref"]["estimator_id"] == estimator_id
            and row["artifact_ref"]["species_id"] == artifact_species
            and horizon_days in row["supported_horizons"]
        ),
        None,
    )
    if artifact is None:
        raise FileNotFoundError("Selected comparison model has no installed artifact")
    artifact_ref = catalog.ModelArtifactRef.from_mapping(artifact["artifact_ref"])
    resolved_ref = artifact_ref.as_dict()
    resolved_ref["species_id"] = species_id
    return catalog.ModelRef(**resolved_ref, horizon_days=horizon_days)


def _weather_requirements(
    model_refs: Sequence[catalog.ModelRef],
    *,
    catalog_profiles: Sequence[Mapping[str, object]] | None = None,
) -> tuple[int, bool]:
    """Return only the weather work required by the selected trained profiles."""
    if catalog_profiles is not None:
        by_key = {
            (str(row.get("version_id") or ""), str(row.get("profile_id") or "")): row
            for row in catalog_profiles
        }
        requirements = []
        for ref in model_refs:
            profile = by_key.get((ref.version_id, ref.profile_id))
            raw = profile.get("input_requirements") if isinstance(profile, Mapping) else None
            if not isinstance(raw, Mapping):
                raise ValueError(
                    f"Runtime profile lacks input requirements: {ref.version_id}/{ref.profile_id}"
                )
            requirements.append(raw)
        return (
            max(int(row["weather_lookback_days"]) for row in requirements),
            any(bool(row["include_physical_state"]) for row in requirements),
        )
    long_raw_versions = {
        "biology_v5_raw_weather_discovery",
        "biology_v6_smooth_hierarchical",
        mushroom_ml_raw_weather.WINDOWED_VERSION_ID,
        mushroom_ml_smooth_hierarchical.WINDOWED_VERSION_ID,
    }
    physical_profile_tokens = (
        "physical_state",
        "climatic_balance",
        "soil_water",
        "smi",
    )
    lookback_days = (
        mushroom_ml_raw_weather.LOOKBACK_DAYS
        if any(ref.version_id in long_raw_versions for ref in model_refs)
        else biology_v3.EVENT_LOOKBACK_DAYS
    )
    include_physical_state = any(
        any(token in ref.profile_id.lower() for token in physical_profile_tokens)
        for ref in model_refs
    )
    return lookback_days, include_physical_state


def prepare_area_weather(
    *,
    known_sites_path: Path,
    weather_data_dir: Path,
    area_id: str,
    target_date: date,
    horizons: Sequence[int],
    lookback_days: int = mushroom_ml_raw_weather.LOOKBACK_DAYS,
    include_physical_state: bool = True,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]] = frozenset(),
) -> tuple[
    Any,
    dict[int, dict[str, object]],
    dict[tuple[str, str], Any],
]:
    """Load one bounded station window and reuse it for every V2--V6 member."""
    areas, microareas = mushroom_ml_area_weather_runtime.area_contexts(
        Path(known_sites_path)
    )
    area_context = areas.get(area_id)
    contexts = microareas.get(area_id, [])
    if area_context is None or not contexts:
        raise ValueError(f"Unknown mushroom area: {area_id}")
    resolved_horizons = sorted({int(value) for value in horizons})
    if not resolved_horizons:
        raise ValueError("At least one comparison horizon is required")
    cutoffs = {horizon: target_date - timedelta(days=horizon) for horizon in resolved_horizons}
    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")
    earliest = min(cutoffs.values()) - timedelta(days=lookback_days - 1)
    latest = max(cutoffs.values())
    station_catalog = weather_context.load_stations_catalog(Path(weather_data_dir))
    station_filter: set[tuple[str, str]] = set()
    for row in station_catalog.itertuples(index=False):
        source = str(getattr(row, "source", "") or "").strip()
        code = str(getattr(row, "station_code", "") or "").strip()
        lat = weather_context.parse_float(getattr(row, "lat", None))
        lon = weather_context.parse_float(getattr(row, "lon", None))
        if source and code and lat is not None and lon is not None and any(
            weather_context.haversine_km(context.lat, context.lon, lat, lon)
            <= mushroom_weather_idw.RAINFALL_IDW_RADIUS_KM
            for context in contexts
        ):
            station_filter.add((source, code))
    stations = weather_context.load_daily_weather_parquet(
        Path(weather_data_dir),
        station_filter=station_filter,
        start_date=earliest,
        end_date=latest,
    )
    normalized_excluded = {
        (str(source).lower(), str(code).upper())
        for source, code in excluded_station_keys
    }
    stations = {
        key: station
        for key, station in stations.items()
        if (str(key[0]).lower(), str(key[1]).upper()) not in normalized_excluded
    }
    prepared = {
        horizon: mushroom_ml_area_weather_runtime.materialize_area_series(
            area_id=area_id,
            end_day=cutoff,
            days=lookback_days,
            microareas_by_area=microareas,
            stations=stations,
            excluded_station_keys=normalized_excluded,
            include_physical_state=include_physical_state,
        )
        for horizon, cutoff in cutoffs.items()
    }
    return area_context, prepared, stations


def _prepared_weather_key(
    *,
    known_sites_path: Path,
    weather_data_dir: Path,
    area_id: str,
    target_date: date,
    horizons: Sequence[int],
    lookback_days: int,
    include_physical_state: bool,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]],
) -> tuple[object, ...]:
    normalized_excluded = tuple(
        sorted(
            (str(source).lower(), str(code).upper())
            for source, code in excluded_station_keys
        )
    )
    return (
        str(Path(known_sites_path).resolve()),
        str(Path(weather_data_dir).resolve()),
        area_id,
        target_date.isoformat(),
        tuple(sorted({int(value) for value in horizons})),
        lookback_days,
        include_physical_state,
        normalized_excluded,
    )


def prewarm_v2_week_weather(
    *,
    area_ids: Sequence[str],
    target_issue_dates: Sequence[tuple[date, date]],
    known_sites_path: Path,
    weather_data_dir: Path,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]],
    prepared_weather_cache: MutableMapping[
        tuple[object, ...], tuple[Any, dict[int, dict[str, object]], dict[tuple[str, str], Any]]
    ],
    lookback_days: int = biology_v3.EVENT_LOOKBACK_DAYS,
    include_physical_state: bool = False,
) -> None:
    """Prepare one extended IDW series per area for a complete weekly grid."""
    requests: list[tuple[date, tuple[int, ...], dict[int, date]]] = []
    for target_date, issue_date in target_issue_dates:
        lag_horizon = (target_date - (issue_date - timedelta(days=1))).days
        horizons = tuple(sorted({7, lag_horizon}))
        cutoffs = {
            horizon: target_date - timedelta(days=horizon)
            for horizon in horizons
        }
        requests.append((target_date, horizons, cutoffs))
    if not requests:
        return
    all_cutoffs = [cutoff for _target, _horizons, rows in requests for cutoff in rows.values()]
    minimum_cutoff = min(all_cutoffs)
    maximum_cutoff = max(all_cutoffs)
    base_days = lookback_days + (maximum_cutoff - minimum_cutoff).days
    base_start = maximum_cutoff - timedelta(days=base_days - 1)

    for area_id in area_ids:
        area_context, base_by_horizon, stations = prepare_area_weather(
            known_sites_path=known_sites_path,
            weather_data_dir=weather_data_dir,
            area_id=area_id,
            target_date=maximum_cutoff,
            horizons=(0,),
            lookback_days=base_days,
            include_physical_state=include_physical_state,
            excluded_station_keys=excluded_station_keys,
        )
        base = base_by_horizon[0]
        for target_date, horizons, cutoffs in requests:
            prepared: dict[int, dict[str, object]] = {}
            for horizon, cutoff in cutoffs.items():
                end_index = (cutoff - base_start).days + 1
                start_index = end_index - lookback_days
                if start_index < 0 or end_index > base_days:
                    raise ValueError("Prepared V2 week slice is outside its base series")
                prepared[horizon] = {
                    key: (
                        list(value[start_index:end_index])
                        if isinstance(value, list) and len(value) == base_days
                        else value
                    )
                    for key, value in base.items()
                }
            cache_key = _prepared_weather_key(
                known_sites_path=known_sites_path,
                weather_data_dir=weather_data_dir,
                area_id=area_id,
                target_date=target_date,
                horizons=horizons,
                lookback_days=lookback_days,
                include_physical_state=include_physical_state,
                excluded_station_keys=excluded_station_keys,
            )
            prepared_weather_cache[cache_key] = (area_context, prepared, stations)


def prewarm_selection_predictions(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    dated_selections: Sequence[tuple[date, Sequence[Mapping[str, object]]]],
    *,
    species_id: str,
    area_id: str,
    models_root: Path,
    known_sites_path: Path,
    weather_data_dir: Path,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]],
    prepared_weather_cache: MutableMapping[
        tuple[object, ...],
        tuple[Any, dict[int, dict[str, object]], dict[tuple[str, str], Any]],
    ],
    comparison_cache: MutableMapping[str, Any],
) -> int:
    """Batch exact model inference for several dates into one call per artifact."""
    checked = comparison_cache.get("checked_manifest")
    if not isinstance(checked, Mapping):
        checked = catalog.validate_batch_manifest(registry, manifest)
        comparison_cache["checked_manifest"] = checked
    catalog_profiles = comparison_cache.get("catalog_profiles")
    if not isinstance(catalog_profiles, list):
        catalog_profiles = catalog.catalog_entries(registry)
        comparison_cache["catalog_profiles"] = catalog_profiles
    artifact_index = comparison_cache.get("artifact_index")
    if not isinstance(artifact_index, dict):
        artifact_index = {
            (
                row["artifact_ref"]["version_id"],
                row["artifact_ref"]["temporal_contract_id"],
                row["artifact_ref"]["profile_id"],
                row["artifact_ref"]["estimator_id"],
                row["artifact_ref"]["species_id"],
                horizon,
            ): row
            for row in checked["artifacts"]
            for horizon in row["supported_horizons"]
        }
        comparison_cache["artifact_index"] = artifact_index
    prediction_cache = comparison_cache.setdefault("prediction_result_cache", {})
    runtime_sample_cache = comparison_cache.setdefault("runtime_sample_cache", {})
    pending_by_artifact: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for target_date, selections in dated_selections:
        refs = [
            resolve_selection(
                registry,
                checked,
                selection,
                species_id=species_id,
                checked_manifest=checked,
                catalog_profiles=catalog_profiles,
            )
            for selection in selections
        ]
        if not refs:
            continue
        horizons = tuple(sorted({model_ref.horizon_days for model_ref in refs}))
        lookback_days, include_physical_state = _weather_requirements(
            refs, catalog_profiles=catalog_profiles
        )
        weather_key = _prepared_weather_key(
            known_sites_path=known_sites_path,
            weather_data_dir=weather_data_dir,
            area_id=area_id,
            target_date=target_date,
            horizons=horizons,
            lookback_days=lookback_days,
            include_physical_state=include_physical_state,
            excluded_station_keys=excluded_station_keys,
        )
        prepared_tuple = prepared_weather_cache.get(weather_key)
        if prepared_tuple is None:
            prepared_tuple = prepare_area_weather(
                known_sites_path=known_sites_path,
                weather_data_dir=weather_data_dir,
                area_id=area_id,
                target_date=target_date,
                horizons=horizons,
                lookback_days=lookback_days,
                include_physical_state=include_physical_state,
                excluded_station_keys=excluded_station_keys,
            )
            prepared_weather_cache[weather_key] = prepared_tuple
        area_context, prepared, stations = prepared_tuple
        for model_ref in refs:
            cache_key = (area_id, target_date.isoformat(), model_ref.key)
            if cache_key in prediction_cache:
                continue
            area_series = prepared.get(model_ref.horizon_days)
            if area_series is None:
                continue
            sample = mushroom_ml_runtime_features.build_runtime_features(
                model_ref,
                target_date=target_date,
                area_id=area_id,
                area_context=area_context,
                area_series=area_series,
                stations=stations,
            )
            runtime_sample_cache[cache_key] = sample
            quality = dict(sample.get("quality") or {})
            if quality.get("inference_eligible") is False:
                continue
            artifact_key = (
                model_ref.version_id,
                model_ref.temporal_contract_id,
                model_ref.profile_id,
                model_ref.estimator_id,
                model_ref.species_id,
                model_ref.horizon_days,
            )
            artifact_row = artifact_index.get(artifact_key) or artifact_index.get(
                (*artifact_key[:4], "all_species", artifact_key[5])
            )
            if artifact_row is None:
                continue
            identity = (str(artifact_row["path"]), str(artifact_row["sha256"]))
            pending_by_artifact.setdefault(identity, []).append(
                {
                    "cache_key": cache_key,
                    "model_ref": model_ref,
                    "artifact_row": artifact_row,
                    "features": dict(sample.get("predictive_features") or {}),
                }
            )
    predicted = 0
    for pending in pending_by_artifact.values():
        first = pending[0]
        bundle = mushroom_ml_runtime_inference.load_exact_artifact(
            registry,
            checked,
            first["model_ref"],
            root=models_root,
            checked_manifest=checked,
            artifact_row=first["artifact_row"],
            validated_model_ref=first["model_ref"],
        )
        predictions = mushroom_ml_runtime_inference.predict_bundle_many(
            bundle,
            [row["features"] for row in pending],
            species_ids=[row["model_ref"].species_id for row in pending],
        )
        for row, prediction in zip(pending, predictions, strict=True):
            prediction_cache[row["cache_key"]] = dict(prediction)
            predicted += 1
    return predicted


def compare_selection(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    selections: Sequence[Mapping[str, object]],
    *,
    species_id: str,
    area_id: str,
    target_date: date,
    models_root: Path,
    known_sites_path: Path,
    weather_data_dir: Path,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]] = frozenset(),
    prepared_weather_cache: MutableMapping[
        tuple[object, ...], tuple[Any, dict[int, dict[str, object]], dict[tuple[str, str], Any]]
    ]
    | None = None,
    checked_manifest: Mapping[str, object] | None = None,
    comparison_cache: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    started = monotonic()
    phase_seconds: dict[str, float] = {}

    def record_phase(name: str, phase_started: float) -> None:
        phase_seconds[name] = round(monotonic() - phase_started, 6)

    phase_started = monotonic()
    checked = checked_manifest
    if checked is None and comparison_cache is not None:
        cached_checked = comparison_cache.get("checked_manifest")
        if isinstance(cached_checked, Mapping):
            checked = cached_checked
    if checked is None:
        checked = catalog.validate_batch_manifest(registry, manifest)
        if comparison_cache is not None:
            comparison_cache["checked_manifest"] = checked
    record_phase("selection_manifest", phase_started)
    phase_started = monotonic()
    catalog_profiles = (
        comparison_cache.get("catalog_profiles")
        if comparison_cache is not None
        else None
    )
    if not isinstance(catalog_profiles, list):
        catalog_profiles = catalog.catalog_entries(registry)
        if comparison_cache is not None:
            comparison_cache["catalog_profiles"] = catalog_profiles
    record_phase("selection_catalog", phase_started)
    phase_started = monotonic()
    refs = [
        resolve_selection(
            registry,
            checked,
            selection,
            species_id=species_id,
            checked_manifest=checked,
            catalog_profiles=catalog_profiles,
        )
        for selection in selections
    ]
    record_phase("selection_resolution", phase_started)
    horizons = tuple(sorted({model_ref.horizon_days for model_ref in refs}))
    lookback_days, include_physical_state = _weather_requirements(
        refs, catalog_profiles=catalog_profiles
    )
    weather_key = _prepared_weather_key(
        known_sites_path=known_sites_path,
        weather_data_dir=weather_data_dir,
        area_id=area_id,
        target_date=target_date,
        horizons=horizons,
        lookback_days=lookback_days,
        include_physical_state=include_physical_state,
        excluded_station_keys=excluded_station_keys,
    )
    prepared_tuple = (
        prepared_weather_cache.get(weather_key)
        if prepared_weather_cache is not None
        else None
    )
    weather_cache_status = "hit" if prepared_tuple is not None else "miss"
    phase_started = monotonic()
    if prepared_tuple is None:
        prepared_tuple = prepare_area_weather(
            known_sites_path=known_sites_path,
            weather_data_dir=weather_data_dir,
            area_id=area_id,
            target_date=target_date,
            horizons=horizons,
            lookback_days=lookback_days,
            include_physical_state=include_physical_state,
            excluded_station_keys=excluded_station_keys,
        )
        if prepared_weather_cache is not None:
            prepared_weather_cache[weather_key] = prepared_tuple
    record_phase("weather_context", phase_started)
    area_context, prepared, stations = prepared_tuple
    phase_started = monotonic()
    result = compare_prepared(
        registry,
        checked,
        refs,
        models_root=models_root,
        target_date=target_date,
        area_id=area_id,
        area_context=area_context,
        area_series_by_horizon=prepared,
        stations=stations,
        checked_manifest=checked,
        comparison_cache=comparison_cache,
    )
    record_phase("prepared_comparison", phase_started)
    prepared_metrics = result.get("runtime_metrics") or {}
    prepared_phases = prepared_metrics.get("phase_seconds") or {}
    result["runtime_metrics"] = {
        "backend_seconds": round(monotonic() - started, 6),
        "phase_seconds": {
            **phase_seconds,
            **{
                f"prepared_{key}": value
                for key, value in prepared_phases.items()
            },
        },
        "weather_cache_status": weather_cache_status,
        "member_count": len(refs),
    }
    return result
