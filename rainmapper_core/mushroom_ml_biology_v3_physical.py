"""V3+ physical profile built without changing the Biology V3 core contract."""

from __future__ import annotations

from typing import Any, Mapping

from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_biology_v4 as biology_v4


PROFILE_ID = "common_idw_plus_physical_state"
DISPLAY_NAME = "Biology V3+ physical"
SOIL_VARIANT_ID = "wv0033_0_30cm"
FEATURE_CONTRACT_ID = "biology_v3_common_idw_plus_physical_state_v1"


def _v4_contract(temporal_contract_id: str) -> str:
    if temporal_contract_id == biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID:
        return biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID
    if temporal_contract_id == biology_v3.LAG_EVENT_BIOLOGY_V3_ID:
        return biology_v4.LAG_EVENT_BIOLOGY_V4_ID
    raise ValueError(f"Unknown Biology V3+ temporal contract: {temporal_contract_id}")


def _v3_contract(temporal_contract_id: str) -> str:
    if temporal_contract_id == biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID:
        return biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
    if temporal_contract_id == biology_v4.LAG_EVENT_BIOLOGY_V4_ID:
        return biology_v3.LAG_EVENT_BIOLOGY_V3_ID
    raise ValueError(f"Unknown Biology V4 source contract: {temporal_contract_id}")


def predictive_columns(temporal_contract_id: str) -> tuple[str, ...]:
    """Return V3 core plus balance and SMI, excluding V4 weather extensions."""
    v4_contract = _v4_contract(temporal_contract_id)
    core = list(biology_v4.predictive_columns(v4_contract, "core"))
    return tuple(
        core
        + [field.name for field in biology_v4.CLIMATIC_BALANCE_FIELDS]
        + [field.name for field in biology_v4.SOIL_WATER_FIELDS]
    )


def soil_state_from_area_series(area_series: Mapping[str, object]) -> dict[str, object]:
    """Project the shared physical area series to the declared V3+ SMI state."""
    return {
        "predictive_features": {
            field.name: area_series.get(field.name)
            for field in biology_v4.SOIL_WATER_FIELDS
        },
        "quality": dict(area_series.get("soil_water_quality") or {}),
        "metadata": dict(area_series.get("soil_water_metadata") or {}),
    }


def _project_sample(
    source: Mapping[str, object],
    *,
    temporal_contract_id: str,
    state: Mapping[str, object] | None,
    inference: bool,
) -> dict[str, object]:
    v4_contract = _v4_contract(temporal_contract_id)
    physical = biology_v4.build_biology_v4_sample(
        source,
        temporal_contract_id=v4_contract,
        area_soil_water_state=state,
    )
    columns = predictive_columns(temporal_contract_id)
    predictive = dict(physical.get("predictive_features") or {})
    source_predictive = dict(source.get("predictive_features") or {})
    missing = [name for name in columns if predictive.get(name) is None]
    source_quality = source.get("quality")
    source_quality = source_quality if isinstance(source_quality, Mapping) else {}
    state_quality = state.get("quality") if isinstance(state, Mapping) else None
    state_ready = isinstance(state_quality, Mapping) and bool(
        state_quality.get("training_eligible")
    )
    source_ready = bool(
        source_quality.get("inference_eligible")
        if inference
        else source_quality.get("training_eligible")
    )
    reasons = []
    source_reasons_key = (
        "inference_exclusion_reasons" if inference else "training_exclusion_reasons"
    )
    for reason in source_quality.get(source_reasons_key, []):
        if isinstance(reason, Mapping):
            reasons.append(dict(reason))
    if not state_ready:
        reasons.append(
            {
                "code": "v3_physical_soil_state_unavailable",
                "message": "El estado hídrico/SMI declarado para V3+ no está disponible.",
            }
        )
    if missing:
        reasons.append(
            {
                "code": "v3_physical_features_missing",
                "message": "Faltan variables V3+: " + ", ".join(missing) + ".",
            }
        )
    eligible = source_ready and state_ready and not missing
    metadata = source.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    return {
        "sample_id": str(source.get("sample_id") or "").replace(
            "biology_v3", "biology_v3_plus"
        ),
        "prediction_target": source.get("prediction_target"),
        "predictive_features": {name: predictive.get(name) for name in columns},
        "quality": {
            "training_eligible": eligible if not inference else False,
            "training_exclusion_reasons": [] if eligible or inference else reasons,
            "inference_eligible": eligible if inference else False,
            "inference_exclusion_reasons": [] if eligible or not inference else reasons,
            "physical_profile_id": PROFILE_ID,
            "soil_variant_id": SOIL_VARIANT_ID,
            "rain_event_search_complete": source_quality.get(
                "rain_event_search_complete"
            ),
            "significant_rain_search_complete": source_quality.get(
                "significant_rain_search_complete"
            ),
            "significant_rain_found_90d": source_quality.get(
                "significant_rain_found_90d"
            ),
            "significant_rain_event_date": source_quality.get(
                "significant_rain_event_date"
            ),
            "significant_rain_event_amount_mm": source_quality.get(
                "significant_rain_event_amount_mm"
            ),
            "significant_rain_threshold_mm": source_quality.get(
                "significant_rain_threshold_mm"
            ),
            "days_since_significant_rain_at_target": source_predictive.get(
                "days_since_significant_rain_at_target"
            ),
        },
        "metadata": {
            **dict(metadata),
            "temporal_contract_id": temporal_contract_id,
            "profile_id": PROFILE_ID,
            "feature_contract_id": FEATURE_CONTRACT_ID,
            "soil_variant_id": SOIL_VARIANT_ID,
        },
    }


def materialize_benchmark(payload: Mapping[str, object]) -> dict[str, object]:
    """Project one frozen V4 physical payload to the paired V3+ benchmark."""
    source_contract = str(payload.get("temporal_contract_id") or "")
    temporal_contract_id = _v3_contract(source_contract)
    soil_variants = payload.get("soil_variants")
    soil_variants = soil_variants if isinstance(soil_variants, Mapping) else {}
    variant = soil_variants.get(SOIL_VARIANT_ID)
    if not isinstance(variant, Mapping):
        raise ValueError(f"V3+ source lacks soil variant {SOIL_VARIANT_ID}")
    state_catalog = variant.get("area_state_catalog")
    if not isinstance(state_catalog, Mapping):
        raise ValueError("V3+ soil variant lacks its area state catalog")
    samples: list[dict[str, object]] = []
    for source in payload.get("samples", []):
        if not isinstance(source, Mapping):
            continue
        metadata = source.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        state = state_catalog.get(metadata.get("soil_state_key"))
        source_v3_metadata = metadata.get("source_v3_metadata")
        source_v3_metadata = (
            source_v3_metadata if isinstance(source_v3_metadata, Mapping) else {}
        )
        v3_source: dict[str, Any] = {
            "sample_id": str(source.get("sample_id") or "").replace(
                "biology_v4", "biology_v3"
            ),
            "prediction_target": source.get("prediction_target"),
            "predictive_features": {
                name: (source.get("predictive_features") or {}).get(name)
                for name in biology_v4.predictive_columns(source_contract, "core")
            },
            "quality": dict(
                (source.get("quality") or {}).get("source_v3_quality") or {}
            ),
            "metadata": dict(source_v3_metadata),
        }
        samples.append(
            _project_sample(
                v3_source,
                temporal_contract_id=temporal_contract_id,
                state=state if isinstance(state, Mapping) else None,
                inference=False,
            )
        )
    columns = list(predictive_columns(temporal_contract_id))
    return {
        "schema_version": "1.0-v3-physical",
        "kind": "mushroom_ml_biology_v3_physical_benchmark",
        "feature_set": {
            "id": FEATURE_CONTRACT_ID,
            "temporal_contract_id": temporal_contract_id,
            "predictive_feature_cols": columns,
        },
        "comparison_profile_id": PROFILE_ID,
        "sample_count": len(samples),
        "training_eligible_sample_count": sum(
            bool((sample.get("quality") or {}).get("training_eligible"))
            for sample in samples
        ),
        "samples": samples,
        "source": {
            **dict(payload.get("source") or {}),
            "physical_source_contract_id": source_contract,
            "soil_variant_id": SOIL_VARIANT_ID,
        },
    }


def materialize_inference_row(
    source_v3_sample: Mapping[str, object],
    *,
    temporal_contract_id: str,
    area_series: Mapping[str, object],
) -> dict[str, object]:
    """Build one target-free V3+ row through the same physical projection."""
    return _project_sample(
        source_v3_sample,
        temporal_contract_id=temporal_contract_id,
        state=soil_state_from_area_series(area_series),
        inference=True,
    )
