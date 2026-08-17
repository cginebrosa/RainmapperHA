"""Feature adapters shared by local and worker multiversion inference."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_biology_v3_evaluation as v3_evaluation
from rainmapper_core import mushroom_ml_biology_v4 as biology_v4
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_raw_weather as raw


def build_runtime_features(
    model_ref: catalog.ModelRef,
    *,
    target_date: date,
    area_id: str,
    area_context: biology_v3.AreaPredictionContext | None,
    area_series: Mapping[str, object],
    stations: Mapping[tuple[str, str], Any],
) -> dict[str, Any]:
    """Build one profile row with the same versioned builders as training."""
    if model_ref.version_id in {
        "altitude_v2",
        "biology_v3",
        "biology_v4",
    }:
        v3_contract = (
            biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
            if model_ref.temporal_contract_id.startswith("fixed_gap_")
            else biology_v3.LAG_EVENT_BIOLOGY_V3_ID
        )
        v3_sample = biology_v3.build_biology_v3_inference_sample(
            species_id=model_ref.species_id,
            area_id=area_id,
            target_date=target_date,
            horizon_days=model_ref.horizon_days,
            temporal_contract_id=v3_contract,
            area_context=area_context,
            area_weather=area_series,
            stations=stations,
        )
        if model_ref.version_id == "altitude_v2":
            sample = v3_evaluation.materialize_altitude_v2_common_idw_inference_sample(
                v3_sample,
                fixed=model_ref.temporal_contract_id.startswith("fixed_gap_"),
            )
        elif model_ref.version_id == "biology_v3":
            sample = v3_sample
        else:
            v4_contract = (
                biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID
                if model_ref.temporal_contract_id.startswith("fixed_gap_")
                else biology_v4.LAG_EVENT_BIOLOGY_V4_ID
            )
            sample = biology_v4.materialize_daily_inference_row(
                v3_sample,
                temporal_contract_id=v4_contract,
                profile_id=model_ref.profile_id,
            )
        return dict(sample)
    if model_ref.version_id in {
        "biology_v5_raw_weather_discovery",
        "biology_v6_smooth_hierarchical",
    }:
        v5_contract = (
            raw.FIXED_CONTRACT_ID
            if model_ref.temporal_contract_id.startswith("fixed_gap_")
            else raw.LAG_CONTRACT_ID
        )
        features = raw.build_raw_features(
            area_series,
            target_date=target_date,
            horizon_days=model_ref.horizon_days,
            temporal_contract_id=v5_contract,
        )
        columns = (
            raw.feature_columns(include_physical=False, include_phenology=False)
            if model_ref.version_id == "biology_v5_raw_weather_discovery"
            else [
                raw.lag_feature_name(channel, lag)
                for channel in raw.RAW_CHANNELS
                for lag in range(raw.LOOKBACK_DAYS)
            ]
        )
        if v5_contract == raw.LAG_CONTRACT_ID and model_ref.version_id.startswith("biology_v5"):
            columns.append("horizon_days")
        return {
            "predictive_features": {column: features.get(column) for column in columns},
            "quality": {
                "inference_eligible": True,
                "raw365_coverage_by_channel": raw.coverage_by_channel(area_series),
            },
            "metadata": {
                "area_id": area_id,
                "target_date": target_date.isoformat(),
                "horizon_days": model_ref.horizon_days,
                "diagnostic_weather_summary": raw.diagnostic_weather_summary(area_series),
            },
        }
    raise ValueError(f"No runtime feature adapter for {model_ref.version_id}")
