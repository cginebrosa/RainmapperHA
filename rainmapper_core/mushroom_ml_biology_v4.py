"""Declarative Biology V4 benchmark records built from frozen V3 samples.

V4 is local benchmark infrastructure only. It preserves every V3 sample and
adds feature blocks without training, artifact creation or operational use.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Literal, Mapping, Sequence

from rainmapper_core import mushroom_climatic_water_balance as climate
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_experiments as altitude_v2
from rainmapper_core import mushroom_observation_context as weather_context


FIXED_GAP_7D_BIOLOGY_V4_ID = "fixed_gap_7d_biology_v4"
LAG_EVENT_BIOLOGY_V4_ID = "lag_event_biology_v4"
FeatureBlock = Literal["core", "extended_weather", "climatic_balance", "soil_water"]
BLOCK_ORDER: tuple[FeatureBlock, ...] = (
    "core",
    "extended_weather",
    "climatic_balance",
    "soil_water",
)


@dataclass(frozen=True)
class V4PredictiveField:
    name: str
    introduced_in: FeatureBlock
    description: str


CORE_FIELDS = tuple(
    V4PredictiveField(field.name, "core", field.description)
    for field in biology_v3.FIXED_GAP_7D_BIOLOGY_V3.fields
    if field.role == "predictive" and field.status == "active"
)
EXTENDED_WEATHER_FIELDS = (
    V4PredictiveField("rain_cutoff_22_30d_mm", "extended_weather", "Area IDW rain at ages 21-29 days with complete support."),
    V4PredictiveField("rainy_days_cutoff_0_7d", "extended_weather", "Observed rainy days at ages 0-6."),
    V4PredictiveField("rainy_days_cutoff_8_14d", "extended_weather", "Observed rainy days at ages 7-13."),
    V4PredictiveField("rainy_days_cutoff_15_21d", "extended_weather", "Observed rainy days at ages 14-20."),
    V4PredictiveField("rainy_days_cutoff_22_30d", "extended_weather", "Observed rainy days at ages 21-29."),
    V4PredictiveField("temp_max_cutoff_8_14d_c", "extended_weather", "Highest corrected Tmax at ages 7-13."),
    V4PredictiveField("temp_min_cutoff_8_14d_c", "extended_weather", "Lowest corrected Tmin at ages 7-13."),
    V4PredictiveField("temp_max_cutoff_15_21d_c", "extended_weather", "Highest corrected Tmax at ages 14-20."),
    V4PredictiveField("temp_min_cutoff_15_21d_c", "extended_weather", "Lowest corrected Tmin at ages 14-20."),
    V4PredictiveField("temp_max_cutoff_22_30d_c", "extended_weather", "Highest corrected Tmax at ages 21-29."),
    V4PredictiveField("temp_min_cutoff_22_30d_c", "extended_weather", "Lowest corrected Tmin at ages 21-29."),
    V4PredictiveField("humidity_max_cutoff_22_30d_pct", "extended_weather", "Highest RH maximum at ages 21-29."),
    V4PredictiveField("humidity_min_cutoff_22_30d_pct", "extended_weather", "Lowest RH minimum at ages 21-29."),
)
EXTENDED_WEATHER_CONTRIBUTION_GROUPS: dict[str, tuple[str, ...]] = {
    "rain_22_30": ("rain_cutoff_22_30d_mm",),
    "rainy_days": (
        "rainy_days_cutoff_0_7d",
        "rainy_days_cutoff_8_14d",
        "rainy_days_cutoff_15_21d",
        "rainy_days_cutoff_22_30d",
    ),
    "temperature_extremes_8_30": (
        "temp_max_cutoff_8_14d_c",
        "temp_min_cutoff_8_14d_c",
        "temp_max_cutoff_15_21d_c",
        "temp_min_cutoff_15_21d_c",
        "temp_max_cutoff_22_30d_c",
        "temp_min_cutoff_22_30d_c",
    ),
    "humidity_extremes_22_30": (
        "humidity_max_cutoff_22_30d_pct",
        "humidity_min_cutoff_22_30d_pct",
    ),
}
CLIMATIC_BALANCE_FIELDS = tuple(
    V4PredictiveField(
        f"climatic_water_balance_cutoff_{label}_mm",
        "climatic_balance",
        f"Complete daily rain minus reference ET balance for {label}.",
    )
    for label, _youngest, _oldest in climate.FEATURE_WINDOWS
)
SOIL_WATER_FIELDS = tuple(
    V4PredictiveField(name, "soil_water", description)
    for name, description in (
        ("soil_water_area_mean_at_cutoff", "Mean available micro-area soil-water fraction at cutoff."),
        ("soil_water_area_min_at_cutoff", "Minimum available micro-area soil-water fraction at cutoff."),
        ("soil_water_change_7d", "Mean soil-water fraction change over seven days."),
        ("soil_water_change_14d", "Mean soil-water fraction change over fourteen days."),
        ("soil_water_recharge_7d", "Mean cumulative positive daily storage changes over seven days."),
        ("soil_water_deficit_at_cutoff", "One minus mean soil-water fraction at cutoff."),
        ("soil_water_drydown_7d", "Mean cumulative negative daily storage changes over seven days."),
    )
)
PREDICTIVE_FIELDS = CORE_FIELDS + EXTENDED_WEATHER_FIELDS + CLIMATIC_BALANCE_FIELDS + SOIL_WATER_FIELDS
PREDICTIVE_FIELD_BY_NAME = {field.name: field for field in PREDICTIVE_FIELDS}
QUALITY_FIELDS = frozenset(
    {
        "eligibility_by_block",
        "exclusion_reasons_by_block",
        "extended_weather_window_coverage",
        "climatic_balance_quality",
        "soil_water_quality",
        "source_v3_quality",
    }
)
METADATA_FIELDS = frozenset(
    {
        "source_v3_metadata",
        "climatic_balance_metadata",
        "soil_water_metadata",
        "temporal_contract_id",
        "feature_block_order",
    }
)


def build_cutoff_temperature_extremes_with_station_fallback(
    stations: Mapping[tuple[str, str], weather_context.WeatherStation],
    *,
    primary_station: weather_context.WeatherStation | None,
    dates: Sequence[date],
    cutoff_day: date,
    area_lat: float,
    area_lon: float,
    area_altitude_m: float | None,
) -> dict[str, object]:
    """Fill isolated primary-station gaps from real cutoff-eligible gauges.

    This helper never interpolates. Candidate eligibility is evaluated at the
    sample cutoff, then each day uses the nearest candidate with both measured
    Tmin and Tmax and an altitude correction to the same area altitude.
    """

    candidates: list[tuple[float, str, str, weather_context.WeatherStation, float]] = []
    for station in stations.values():
        distance = weather_context.haversine_km(area_lat, area_lon, station.lat, station.lon)
        correction = altitude_v2.altitude_temperature_correction_c(
            station.altitude_m, area_altitude_m
        )
        if (
            distance <= weather_context.STATION_MAX_DISTANCE_KM
            and correction is not None
            and bool(weather_context.station_quality(station, cutoff_day).get("eligible"))
        ):
            candidates.append((distance, station.source, station.station_code, station, correction))
    candidates.sort(key=lambda row: (row[0], row[1], row[2]))
    if primary_station is not None:
        candidates.sort(key=lambda row: 0 if row[3] is primary_station else 1)

    temp_min: list[float | None] = []
    temp_max: list[float | None] = []
    source_codes: list[str | None] = []
    primary_days = 0
    fallback_days = 0
    fallback_counts: dict[str, int] = {}
    for day in dates:
        selected = None
        for _distance, _source, _code, station, correction in candidates:
            record = station.records_by_day.get(day)
            if record is None or record.temp_min_c is None or record.temp_max_c is None:
                continue
            selected = (station, correction, record)
            break
        if selected is None:
            temp_min.append(None)
            temp_max.append(None)
            source_codes.append(None)
            continue
        station, correction, record = selected
        temp_min.append(round(float(record.temp_min_c) + correction, 3))
        temp_max.append(round(float(record.temp_max_c) + correction, 3))
        code = f"{station.source}:{station.station_code}"
        source_codes.append(code)
        if station is primary_station:
            primary_days += 1
        else:
            fallback_days += 1
            fallback_counts[code] = fallback_counts.get(code, 0) + 1
    return {
        "daily_temp_min_corrected_c": temp_min,
        "daily_temp_max_corrected_c": temp_max,
        "quality": {
            "candidate_station_count": len(candidates),
            "primary_station_days": primary_days,
            "fallback_station_days": fallback_days,
            "missing_days": sum(value is None for value in temp_min),
            "fallback_station_day_counts": dict(sorted(fallback_counts.items())),
            "interpolated_days": 0,
        },
        "metadata": {
            "contract_id": "cutoff_eligible_measured_temperature_fallback_v1",
            "primary_station_code": (
                f"{primary_station.source}:{primary_station.station_code}"
                if primary_station is not None
                else None
            ),
            "daily_source_codes": source_codes,
        },
    }


def predictive_columns(
    temporal_contract_id: str,
    block: FeatureBlock,
) -> tuple[str, ...]:
    if temporal_contract_id not in {
        FIXED_GAP_7D_BIOLOGY_V4_ID,
        LAG_EVENT_BIOLOGY_V4_ID,
    }:
        raise ValueError(f"Unknown Biology V4 temporal contract: {temporal_contract_id}")
    if block not in BLOCK_ORDER:
        raise ValueError(f"Unknown Biology V4 feature block: {block}")
    max_index = BLOCK_ORDER.index(block)
    columns = [
        field.name
        for field in PREDICTIVE_FIELDS
        if BLOCK_ORDER.index(field.introduced_in) <= max_index
    ]
    if temporal_contract_id == LAG_EVENT_BIOLOGY_V4_ID:
        columns.insert(0, "horizon_days")
    return tuple(columns)


def extended_weather_contribution_columns(
    temporal_contract_id: str,
    contribution_id: str,
) -> tuple[str, ...]:
    """Return core plus one declared V4 weather contribution family."""

    if contribution_id == "extended_weather_all":
        return predictive_columns(temporal_contract_id, "extended_weather")
    try:
        additions = EXTENDED_WEATHER_CONTRIBUTION_GROUPS[contribution_id]
    except KeyError as exc:
        raise ValueError(f"Unknown extended-weather contribution: {contribution_id}") from exc
    registered_extended = {field.name for field in EXTENDED_WEATHER_FIELDS}
    if not set(additions) <= registered_extended:
        raise ValueError(f"Contribution {contribution_id} contains unregistered fields")
    return predictive_columns(temporal_contract_id, "core") + additions


def materialize_comparison_benchmark(
    payload: Mapping[str, object],
    *,
    profile_id: str,
) -> dict[str, object]:
    """Convert one V4 block/soil profile to the generic version benchmark schema."""

    temporal_contract_id = str(payload.get("temporal_contract_id") or "")
    feature_blocks = payload.get("feature_blocks")
    if not isinstance(feature_blocks, Mapping):
        raise ValueError("Biology V4 benchmark does not declare feature blocks")
    soil_variants = payload.get("soil_variants")
    soil_variants = soil_variants if isinstance(soil_variants, Mapping) else {}
    soil_variant = soil_variants.get(profile_id)
    if profile_id in BLOCK_ORDER:
        block = profile_id
        columns = list(feature_blocks.get(block) or ())
    elif isinstance(soil_variant, Mapping):
        block = "soil_water"
        columns = list(feature_blocks.get(block) or ())
    else:
        raise ValueError(f"Unknown Biology V4 comparison profile: {profile_id}")
    if not columns:
        raise ValueError(f"Biology V4 comparison profile {profile_id} has no columns")

    state_catalog = (
        soil_variant.get("area_state_catalog", {})
        if isinstance(soil_variant, Mapping)
        else {}
    )
    samples: list[dict[str, object]] = []
    for source in payload.get("samples", []):
        if not isinstance(source, Mapping):
            continue
        source_quality = source.get("quality")
        source_quality = source_quality if isinstance(source_quality, Mapping) else {}
        eligibility = source_quality.get("eligibility_by_block")
        eligibility = eligibility if isinstance(eligibility, Mapping) else {}
        predictive = dict(source.get("predictive_features") or {})
        eligible = bool(eligibility.get(block))
        if isinstance(soil_variant, Mapping):
            source_metadata = source.get("metadata")
            source_metadata = source_metadata if isinstance(source_metadata, Mapping) else {}
            state = state_catalog.get(source_metadata.get("soil_state_key"))
            if isinstance(state, Mapping):
                predictive.update(state.get("predictive_features") or {})
                state_quality = state.get("quality")
                eligible = (
                    bool(eligibility.get("climatic_balance"))
                    and isinstance(state_quality, Mapping)
                    and bool(state_quality.get("training_eligible"))
                )
            else:
                eligible = False
        missing = [name for name in columns if predictive.get(name) is None]
        metadata = source.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        v3_metadata = metadata.get("source_v3_metadata")
        samples.append(
            {
                "sample_id": source.get("sample_id"),
                "prediction_target": source.get("prediction_target"),
                "predictive_features": {name: predictive.get(name) for name in columns},
                "quality": {
                    "training_eligible": eligible and not missing,
                    "training_exclusion_reasons": (
                        []
                        if eligible and not missing
                        else [
                            {
                                "code": f"v4_profile_{profile_id}_ineligible",
                                "message": (
                                    f"El perfil V4 {profile_id} no supera su bloque o "
                                    f"carece de variables: {', '.join(missing)}."
                                ),
                            }
                        ]
                    ),
                },
                "metadata": dict(v3_metadata) if isinstance(v3_metadata, Mapping) else {},
            }
        )
    return {
        "schema_version": "1.0-v4-comparison-profile",
        "kind": "mushroom_ml_biology_v4_comparison_benchmark",
        "feature_set": {
            "id": f"{temporal_contract_id}:{profile_id}",
            "predictive_feature_cols": columns,
        },
        "comparison_profile_id": profile_id,
        "sample_count": len(samples),
        "training_eligible_sample_count": sum(
            bool((sample.get("quality") or {}).get("training_eligible"))
            for sample in samples
        ),
        "samples": samples,
        "source": {
            **dict(payload.get("source") or {}),
            "v4_profile_id": profile_id,
        },
    }


def materialize_daily_inference_row(
    source_v3_sample: Mapping[str, object],
    *,
    temporal_contract_id: str,
    profile_id: str,
    area_soil_water_state: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Materialize a target-free daily row with the same V4 feature builder.

    The sole training-only exclusion allowed to disappear is an unknown target;
    every weather, coverage and altitude gate remains active and legible.
    """

    if profile_id not in BLOCK_ORDER:
        raise ValueError(f"Unknown Biology V4 daily profile: {profile_id}")
    sample = build_biology_v4_sample(
        source_v3_sample,
        temporal_contract_id=temporal_contract_id,
        area_soil_water_state=area_soil_water_state,
    )
    source_quality = source_v3_sample.get("quality")
    source_quality = source_quality if isinstance(source_quality, Mapping) else {}
    source_predictive = source_v3_sample.get("predictive_features")
    source_predictive = (
        source_predictive if isinstance(source_predictive, Mapping) else {}
    )
    source_reasons = source_quality.get("training_exclusion_reasons")
    source_reasons = source_reasons if isinstance(source_reasons, Sequence) else []
    inference_reasons = [
        dict(reason)
        for reason in source_reasons
        if isinstance(reason, Mapping) and reason.get("code") != "modeling_target_unknown"
    ]
    columns = predictive_columns(temporal_contract_id, profile_id)
    predictive = sample.get("predictive_features")
    predictive = predictive if isinstance(predictive, Mapping) else {}
    missing = [column for column in columns if predictive.get(column) is None]
    if missing:
        inference_reasons.append(
            _reason(
                "daily_predictive_features_missing",
                "Faltan variables diarias V4: " + ", ".join(missing) + ".",
            )
        )
    source_metadata = source_v3_sample.get("metadata")
    source_metadata = source_metadata if isinstance(source_metadata, Mapping) else {}
    return {
        "predictive_features": {column: predictive.get(column) for column in columns},
        "quality": {
            "training_eligible": not inference_reasons,
            "inference_eligible": not inference_reasons,
            "inference_exclusion_reasons": inference_reasons,
            "target_gate_ignored_for_inference": True,
            # Keep the common ecological evidence outside predictive_features:
            # it must never enter a model, but the operational interpretation
            # needs the exact rain event seen by the source V3 adapter.
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
            "area_id": source_metadata.get("area_id"),
            "target_date": source_metadata.get("target_date"),
            "cutoff_date": source_metadata.get("cutoff_date"),
            "horizon_days": source_metadata.get("horizon_days"),
            "temporal_contract_id": temporal_contract_id,
            "profile_id": profile_id,
        },
    }


def audit_train_inference_parity(
    source_v3_payload: Mapping[str, object],
    v4_payload: Mapping[str, object],
    *,
    profile_id: str,
) -> dict[str, object]:
    """Compare stored benchmark predictors with the shared inference builder."""

    temporal_contract_id = str(v4_payload.get("temporal_contract_id") or "")
    soil_variants = v4_payload.get("soil_variants")
    soil_variants = soil_variants if isinstance(soil_variants, Mapping) else {}
    soil_variant = soil_variants.get(profile_id)
    block = "soil_water" if isinstance(soil_variant, Mapping) else profile_id
    if block not in BLOCK_ORDER:
        raise ValueError(f"Unknown Biology V4 parity profile: {profile_id}")
    comparison = materialize_comparison_benchmark(v4_payload, profile_id=profile_id)
    stored_by_id = {
        str(row.get("sample_id") or ""): row
        for row in comparison.get("samples", [])
        if isinstance(row, Mapping)
    }
    state_catalog = (
        soil_variant.get("area_state_catalog", {})
        if isinstance(soil_variant, Mapping)
        else {}
    )
    columns = list((comparison.get("feature_set") or {}).get("predictive_feature_cols") or [])
    mismatch_examples: list[dict[str, object]] = []
    field_mismatch_counts: dict[str, int] = {}
    missing_stored = 0
    eligibility_mismatches = 0
    compared = 0
    for source in source_v3_payload.get("samples", []):
        if not isinstance(source, Mapping):
            continue
        expected_id = str(source.get("sample_id") or "").replace("biology_v3", "biology_v4")
        stored = stored_by_id.get(expected_id)
        if stored is None:
            missing_stored += 1
            continue
        source_metadata = source.get("metadata")
        source_metadata = source_metadata if isinstance(source_metadata, Mapping) else {}
        state_key = f"{source_metadata.get('area_id') or ''}|{source_metadata.get('cutoff_date') or ''}"
        state = state_catalog.get(state_key) if isinstance(state_catalog, Mapping) else None
        inference = materialize_daily_inference_row(
            source,
            temporal_contract_id=temporal_contract_id,
            profile_id=block,
            area_soil_water_state=state if isinstance(state, Mapping) else None,
        )
        compared += 1
        stored_predictive = stored.get("predictive_features")
        stored_predictive = stored_predictive if isinstance(stored_predictive, Mapping) else {}
        inference_predictive = inference["predictive_features"]
        for column in columns:
            if stored_predictive.get(column) != inference_predictive.get(column):
                field_mismatch_counts[column] = field_mismatch_counts.get(column, 0) + 1
                if len(mismatch_examples) < 20:
                    mismatch_examples.append(
                        {
                            "sample_id": expected_id,
                            "field": column,
                            "benchmark_value": stored_predictive.get(column),
                            "inference_value": inference_predictive.get(column),
                        }
                    )
        stored_eligible = bool((stored.get("quality") or {}).get("training_eligible"))
        inference_eligible = bool(inference["quality"]["inference_eligible"])
        if stored_eligible != inference_eligible:
            eligibility_mismatches += 1
    return {
        "kind": "biology_v4_train_inference_parity_audit",
        "schema_version": "1.0",
        "temporal_contract_id": temporal_contract_id,
        "profile_id": profile_id,
        "predictive_feature_cols": columns,
        "source_sample_count": len(source_v3_payload.get("samples", [])),
        "compared_sample_count": compared,
        "missing_stored_sample_count": missing_stored,
        "predictive_field_mismatch_counts": dict(sorted(field_mismatch_counts.items())),
        "predictive_mismatch_count": sum(field_mismatch_counts.values()),
        "eligibility_mismatch_count": eligibility_mismatches,
        "mismatch_examples": mismatch_examples,
        "parity_passed": (
            missing_stored == 0
            and not field_mismatch_counts
            and eligibility_mismatches == 0
        ),
        "model_artifact_written": False,
    }


def _age_values(values: Sequence[object], youngest: int, oldest: int) -> list[float | None]:
    result: list[float | None] = []
    for age in range(youngest, oldest + 1):
        index = len(values) - 1 - age
        value = values[index] if index >= 0 else None
        try:
            number = float(value) if value is not None else None
        except (TypeError, ValueError):
            number = None
        result.append(number)
    return result


def _complete_sum(values: Sequence[float | None]) -> float | None:
    return round(sum(float(value) for value in values), 6) if values and all(value is not None for value in values) else None


def _complete_extreme(values: Sequence[float | None], *, maximum: bool) -> float | None:
    if not values or any(value is None for value in values):
        return None
    function = max if maximum else min
    return round(function(float(value) for value in values), 6)


def _reason(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def build_biology_v4_sample(
    source_v3_sample: Mapping[str, object],
    *,
    temporal_contract_id: str,
    area_soil_water_state: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Augment one frozen V3 sample while preserving its identity and target."""

    source_feature_set = (
        biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID
        if temporal_contract_id == FIXED_GAP_7D_BIOLOGY_V4_ID
        else biology_v3.LAG_EVENT_BIOLOGY_V3_ID
    )
    biology_v3.validate_biology_v3_sample(source_v3_sample, source_feature_set)
    source_predictive = source_v3_sample["predictive_features"]
    source_quality = source_v3_sample["quality"]
    source_metadata = source_v3_sample["metadata"]
    assert isinstance(source_predictive, Mapping)
    assert isinstance(source_quality, Mapping)
    assert isinstance(source_metadata, Mapping)

    predictive: dict[str, float | None] = {
        field.name: (
            float(source_predictive[field.name])
            if source_predictive.get(field.name) is not None
            else None
        )
        for field in CORE_FIELDS
    }
    if temporal_contract_id == LAG_EVENT_BIOLOGY_V4_ID:
        predictive["horizon_days"] = (
            float(source_predictive["horizon_days"])
            if source_predictive.get("horizon_days") is not None
            else None
        )

    weather = source_metadata.get("weather_series")
    weather = weather if isinstance(weather, Mapping) else {}
    rain = weather.get("daily_area_rain_idw_mean_mm", [])
    temp_max = weather.get("daily_temp_max_corrected_c", [])
    temp_min = weather.get("daily_temp_min_corrected_c", [])
    humidity_max = weather.get("daily_humidity_max_pct", [])
    humidity_min = weather.get("daily_humidity_min_pct", [])
    extended_quality: dict[str, object] = {}
    windows = {
        "0_7d": (0, 6),
        "8_14d": (7, 13),
        "15_21d": (14, 20),
        "22_30d": (21, 29),
    }
    predictive["rain_cutoff_22_30d_mm"] = _complete_sum(_age_values(rain, 21, 29))
    for label, (youngest, oldest) in windows.items():
        rain_values = _age_values(rain, youngest, oldest)
        predictive[f"rainy_days_cutoff_{label}"] = (
            float(sum(float(value) > 0.0 for value in rain_values if value is not None))
            if rain_values and all(value is not None for value in rain_values)
            else None
        )
        extended_quality[label] = {
            "rain_observed_days": sum(value is not None for value in rain_values),
            "expected_days": len(rain_values),
        }
    for label, youngest, oldest in (("8_14d", 7, 13), ("15_21d", 14, 20), ("22_30d", 21, 29)):
        predictive[f"temp_max_cutoff_{label}_c"] = _complete_extreme(
            _age_values(temp_max, youngest, oldest), maximum=True
        )
        predictive[f"temp_min_cutoff_{label}_c"] = _complete_extreme(
            _age_values(temp_min, youngest, oldest), maximum=False
        )
    predictive["humidity_max_cutoff_22_30d_pct"] = _complete_extreme(
        _age_values(humidity_max, 21, 29), maximum=True
    )
    predictive["humidity_min_cutoff_22_30d_pct"] = _complete_extreme(
        _age_values(humidity_min, 21, 29), maximum=False
    )

    climate_result: Mapping[str, object] | None = None
    location = source_metadata.get("area_representative_location")
    try:
        if not isinstance(location, Mapping):
            raise ValueError("area representative location is missing")
        climate_result = climate.build_climatic_water_balance(
            dates=[date.fromisoformat(str(value)) for value in weather.get("daily_dates", [])],
            rain_idw_mm=rain,
            temp_min_corrected_c=temp_min,
            temp_max_corrected_c=temp_max,
            latitude_deg=float(location["lat"]),
        )
        predictive.update(climate_result["predictive_features"])
    except (KeyError, TypeError, ValueError):
        predictive.update({field.name: None for field in CLIMATIC_BALANCE_FIELDS})

    soil_predictive = (
        area_soil_water_state.get("predictive_features")
        if isinstance(area_soil_water_state, Mapping)
        else None
    )
    for field in SOIL_WATER_FIELDS:
        value = soil_predictive.get(field.name) if isinstance(soil_predictive, Mapping) else None
        predictive[field.name] = float(value) if value is not None else None

    eligibility: dict[str, bool] = {}
    exclusions: dict[str, list[dict[str, str]]] = {}
    core_missing = [name for name in predictive_columns(temporal_contract_id, "core") if predictive.get(name) is None]
    eligibility["core"] = bool(source_quality.get("training_eligible")) and not core_missing
    exclusions["core"] = [] if eligibility["core"] else [
        _reason("v3_core_ineligible", "La fila no supera los gates heredados del núcleo V3.")
    ]
    for block in BLOCK_ORDER[1:]:
        missing = [name for name in predictive_columns(temporal_contract_id, block) if predictive.get(name) is None]
        previous = BLOCK_ORDER[BLOCK_ORDER.index(block) - 1]
        eligibility[block] = eligibility[previous] and not missing
        exclusions[block] = [] if eligibility[block] else [
            _reason(
                f"{block}_features_missing",
                f"El bloque {block} no dispone de todas sus variables: {', '.join(missing)}.",
            )
        ]
    if area_soil_water_state is not None:
        soil_quality = area_soil_water_state.get("quality")
        if isinstance(soil_quality, Mapping) and not soil_quality.get("training_eligible"):
            eligibility["soil_water"] = False
            exclusions["soil_water"] = [
                _reason("area_soil_water_unavailable", "El estado hídrico de todas las microáreas del área está ausente.")
            ]

    result = {
        "sample_id": str(source_v3_sample.get("sample_id") or "").replace("biology_v3", "biology_v4"),
        "prediction_target": source_v3_sample.get("prediction_target"),
        "predictive_features": predictive,
        "quality": {
            "eligibility_by_block": eligibility,
            "exclusion_reasons_by_block": exclusions,
            "extended_weather_window_coverage": extended_quality,
            "climatic_balance_quality": climate_result.get("quality") if climate_result else {},
            "soil_water_quality": area_soil_water_state.get("quality") if isinstance(area_soil_water_state, Mapping) else {},
            "source_v3_quality": {
                **dict(source_quality),
                "days_since_significant_rain_at_target": source_predictive.get(
                    "days_since_significant_rain_at_target"
                ),
            },
        },
        "metadata": {
            "temporal_contract_id": temporal_contract_id,
            "feature_block_order": list(BLOCK_ORDER),
            "source_v3_metadata": dict(source_metadata),
            "climatic_balance_metadata": climate_result.get("metadata") if climate_result else {},
            "soil_water_metadata": area_soil_water_state.get("metadata") if isinstance(area_soil_water_state, Mapping) else {},
        },
    }
    validate_biology_v4_sample(result, temporal_contract_id)
    return result


def validate_biology_v4_sample(sample: Mapping[str, object], temporal_contract_id: str) -> None:
    predictive = sample.get("predictive_features")
    quality = sample.get("quality")
    metadata = sample.get("metadata")
    if not isinstance(predictive, Mapping) or not isinstance(quality, Mapping) or not isinstance(metadata, Mapping):
        raise ValueError("Biology V4 samples require predictive_features, quality and metadata mappings")
    allowed = set(PREDICTIVE_FIELD_BY_NAME)
    if temporal_contract_id == LAG_EVENT_BIOLOGY_V4_ID:
        allowed.add("horizon_days")
    unknown = set(predictive) - allowed
    if unknown:
        raise ValueError("Unregistered Biology V4 predictors: " + ", ".join(sorted(unknown)))
    leakage = (set(predictive) & QUALITY_FIELDS) | (set(predictive) & METADATA_FIELDS)
    if leakage:
        raise ValueError("Quality or metadata fields cannot enter predictive_features: " + ", ".join(sorted(leakage)))


def build_biology_v4_X(
    samples: Sequence[Mapping[str, object]],
    *,
    temporal_contract_id: str,
    block: FeatureBlock,
    requested_cols: Iterable[str] | None = None,
) -> tuple[list[list[float | None]], list[str]]:
    registered = set(predictive_columns(temporal_contract_id, "soil_water"))
    columns = list(requested_cols or predictive_columns(temporal_contract_id, block))
    quality_requested = set(columns) & QUALITY_FIELDS
    metadata_requested = set(columns) & METADATA_FIELDS
    unknown = set(columns) - registered
    if quality_requested:
        raise ValueError("Quality fields cannot enter X: " + ", ".join(sorted(quality_requested)))
    if metadata_requested:
        raise ValueError("Metadata fields cannot enter X: " + ", ".join(sorted(metadata_requested)))
    if unknown:
        raise ValueError("Only registered Biology V4 predictors can enter X: " + ", ".join(sorted(unknown)))
    matrix: list[list[float | None]] = []
    for sample in samples:
        validate_biology_v4_sample(sample, temporal_contract_id)
        predictive = sample["predictive_features"]
        assert isinstance(predictive, Mapping)
        matrix.append([
            float(predictive[column]) if predictive.get(column) is not None else None
            for column in columns
        ])
    return matrix, columns
