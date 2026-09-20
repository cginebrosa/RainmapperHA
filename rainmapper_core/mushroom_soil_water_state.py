"""Shared SoilGrids regulated water state for physical prediction profiles.

The accepted component is a transparent one-layer reference, not a
replacement for a calibrated forest water-balance model. It uses SoilGrids
fine-earth available-water capacity and publishes every limitation outside X.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Mapping, Sequence


SOIL_WATER_STATE_CONTRACT_ID = "microarea_soil_water_state_v2"
BUCKET_METHOD_ID = "regulated_pm_single_layer_v1"
VALIDATION_STATE = "uncalibrated_physical_index"
DEFAULT_FIELD_CAPACITY_PROPERTY = "wv0033_mm_per_m"
WILTING_POINT_PROPERTY = "wv1500_mm_per_m"
DEFAULT_QUANTILE = "Q0.50"
PROFILE_DEPTH_CANDIDATES_CM = (30, 60, 100)
SPINUP_CANDIDATES_DAYS = (90, 180, 365)
CONVERGENCE_CAPACITY_FRACTION = 0.01
CONVERGENCE_ABSOLUTE_MM = 1.0
ROUND_DIGITS = 6


def _number(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite number")
    return result


def available_water_capacity_mm(
    soilgrids_context: Mapping[str, object],
    *,
    profile_depth_cm: int,
    field_capacity_property: str = DEFAULT_FIELD_CAPACITY_PROPERTY,
    quantile: str = DEFAULT_QUANTILE,
) -> dict[str, object]:
    """Calculate fine-earth available-water capacity for an exact profile.

    SoilGrids water retention is stored as mm/m. The difference between field
    capacity and wilting point is multiplied by layer thickness in metres.
    Coarse-fragment correction is deliberately not fabricated: the result is
    labelled fine-earth capacity until a versioned ``cfvo`` context exists.
    """

    if profile_depth_cm not in PROFILE_DEPTH_CANDIDATES_CM:
        raise ValueError(
            "profile_depth_cm must be one of "
            + ", ".join(str(value) for value in PROFILE_DEPTH_CANDIDATES_CM)
        )
    if soilgrids_context.get("status") != "complete":
        raise ValueError("SoilGrids water context must have status complete")
    depths = soilgrids_context.get("depths")
    if not isinstance(depths, list):
        raise ValueError("SoilGrids water context has no depth list")

    expected_top = 0
    capacity = 0.0
    layers: list[dict[str, object]] = []
    for layer in sorted(depths, key=lambda row: int(row.get("top_cm", -1))):
        top = int(layer.get("top_cm", -1))
        bottom = int(layer.get("bottom_cm", -1))
        if top >= profile_depth_cm:
            break
        if top != expected_top or bottom > profile_depth_cm or bottom <= top:
            raise ValueError("SoilGrids depth layers do not exactly cover the requested profile")
        area_weighted = layer.get("area_weighted")
        values = area_weighted.get(quantile) if isinstance(area_weighted, dict) else None
        if not isinstance(values, dict):
            raise ValueError(f"SoilGrids layer {top}-{bottom} lacks {quantile}")
        field_capacity = _number(
            values.get(field_capacity_property), field=field_capacity_property
        )
        wilting_point = _number(
            values.get(WILTING_POINT_PROPERTY), field=WILTING_POINT_PROPERTY
        )
        if field_capacity < wilting_point:
            raise ValueError(
                f"Field capacity is below wilting point in layer {top}-{bottom} cm"
            )
        layer_capacity = (field_capacity - wilting_point) * ((bottom - top) / 100.0)
        capacity += layer_capacity
        layers.append(
            {
                "top_cm": top,
                "bottom_cm": bottom,
                "field_capacity_mm_per_m": field_capacity,
                "wilting_point_mm_per_m": wilting_point,
                "available_water_mm": round(layer_capacity, ROUND_DIGITS),
            }
        )
        expected_top = bottom
    if expected_top != profile_depth_cm or capacity <= 0.0:
        raise ValueError("SoilGrids layers do not yield a positive complete profile capacity")
    return {
        "capacity_mm": round(capacity, ROUND_DIGITS),
        "profile_depth_cm": profile_depth_cm,
        "field_capacity_property": field_capacity_property,
        "wilting_point_property": WILTING_POINT_PROPERTY,
        "quantile": quantile,
        "coarse_fragment_correction": "not_applied_context_unavailable",
        "layers": layers,
    }


def simulate_bounded_bucket(
    *,
    rain_mm: Sequence[float],
    reference_evapotranspiration_mm: Sequence[float],
    capacity_mm: float,
    initial_storage_mm: float,
) -> dict[str, list[float] | float]:
    """Run a daily mass-conserving bucket with no fitted parameters."""

    if len(rain_mm) != len(reference_evapotranspiration_mm):
        raise ValueError("Bucket rain and evapotranspiration series must align")
    capacity = _number(capacity_mm, field="capacity_mm")
    storage = _number(initial_storage_mm, field="initial_storage_mm")
    if capacity <= 0.0 or not 0.0 <= storage <= capacity:
        raise ValueError("Bucket capacity/storage bounds are invalid")

    storage_series: list[float] = []
    actual_et_series: list[float] = []
    drainage_series: list[float] = []
    unmet_demand_series: list[float] = []
    mass_errors: list[float] = []
    for raw_rain, raw_eto in zip(rain_mm, reference_evapotranspiration_mm):
        rain = _number(raw_rain, field="rain_mm")
        demand = _number(raw_eto, field="reference_evapotranspiration_mm")
        if rain < 0.0 or demand < 0.0:
            raise ValueError("Bucket rain and evapotranspiration cannot be negative")
        available = storage + rain
        actual_et = min(demand, available)
        after_et = available - actual_et
        drainage = max(0.0, after_et - capacity)
        next_storage = min(capacity, after_et)
        unmet = demand - actual_et
        mass_error = abs(storage + rain - next_storage - actual_et - drainage)

        storage = next_storage
        storage_series.append(round(storage, ROUND_DIGITS))
        actual_et_series.append(round(actual_et, ROUND_DIGITS))
        drainage_series.append(round(drainage, ROUND_DIGITS))
        unmet_demand_series.append(round(unmet, ROUND_DIGITS))
        mass_errors.append(mass_error)

    return {
        "storage_mm": storage_series,
        "actual_evapotranspiration_mm": actual_et_series,
        "drainage_mm": drainage_series,
        "unmet_evaporative_demand_mm": unmet_demand_series,
        "mass_error_max_mm": round(max(mass_errors, default=0.0), 9),
    }


def build_soil_water_state(
    *,
    dates: Sequence[date],
    rain_idw_mm: Sequence[float | None],
    reference_evapotranspiration_mm: Sequence[float | None],
    soilgrids_context: Mapping[str, object],
    profile_depth_cm: int = 30,
    field_capacity_property: str = DEFAULT_FIELD_CAPACITY_PROPERTY,
    quantile: str = DEFAULT_QUANTILE,
) -> dict[str, object]:
    """Build a cutoff state only after dry/saturated spin-up convergence."""

    if not dates or len(dates) != len(rain_idw_mm) or len(dates) != len(reference_evapotranspiration_mm):
        raise ValueError("Soil-water daily inputs must be non-empty and aligned")
    if list(dates) != sorted(dates) or len(set(dates)) != len(dates):
        raise ValueError("Soil-water dates must be strictly increasing and unique")
    for previous, current in zip(dates, dates[1:]):
        if (current - previous).days != 1:
            raise ValueError("Soil-water dates must be consecutive")

    capacity_context = available_water_capacity_mm(
        soilgrids_context,
        profile_depth_cm=profile_depth_cm,
        field_capacity_property=field_capacity_property,
        quantile=quantile,
    )
    capacity = float(capacity_context["capacity_mm"])
    from .mushroom_water_physics import regulated_history, WATER_STATE_CONTRACT_ID

    # Use the full bounded history, as the map does. Never start afresh at the
    # display/feature window, and never publish unconverged early daily states.
    dates = list(dates[-365:])
    rain = list(rain_idw_mm[-365:])
    eto = list(reference_evapotranspiration_mm[-365:])
    history = regulated_history(rain, eto, capacity)
    cutoff = history['storage_mm'][-1]
    end_reason = history['reasons'][-1]
    reasons = [] if end_reason is None else [{
        'code': 'soil_water_spinup_not_converged' if end_reason == 'not_converged' else 'soil_water_spinup_inputs_incomplete',
        'message': 'El estado requiere al menos 90 días consecutivos y convergencia de los estados iniciales seco y lleno.',
    }]
    # Consecutive usable tail for area changes; the raw daily ML channel below
    # retains every valid date, including segments preceding an observed gap.
    first = len(dates)
    while first > 0 and history['storage_mm'][first-1] is not None:
        first -= 1
    values = history['storage_mm'][first:]
    def change(age):
        return round((values[-1]-values[-1-age])/capacity,ROUND_DIGITS) if len(values)>age else None
    usable = [(day,value) for day,value in zip(dates,history['storage_mm']) if value is not None]
    convergence = {'full_history': {
        'available': end_reason not in ('inputs_incomplete','spinup_incomplete'),
        'converged': end_reason is None,
        'contiguous_days': history['contiguous_days'][-1],
        'limit_mm': max(CONVERGENCE_ABSOLUTE_MM, capacity*CONVERGENCE_CAPACITY_FRACTION),
    }}
    return {
        'contract_id': SOIL_WATER_STATE_CONTRACT_ID,
        'predictive_features': {
            'soil_water_at_cutoff_fraction': round(cutoff/capacity,ROUND_DIGITS) if cutoff is not None else None,
            'soil_water_change_7d_fraction': change(7),
            'soil_water_change_14d_fraction': change(14),
        },
        'quality': {
            'training_eligible': not reasons,
            'training_exclusion_reasons': reasons,
            'missing_input_reason_counts': {
                'missing_area_idw_rain': sum(v is None for v in rain),
                'missing_reference_evapotranspiration': sum(v is None for v in eto),
            },
            'spinup_convergence': convergence,
            'water_balance_mass_error_max_mm': history['mass_error_max_mm'],
        },
        'metadata': {
            'water_state_contract_id': WATER_STATE_CONTRACT_ID,
            'validation_state': VALIDATION_STATE,
            'bucket_method': BUCKET_METHOD_ID,
            'soilgrids_context_hash': soilgrids_context.get('context_hash'),
            'capacity': capacity_context,
            'selected_spinup_days': history['contiguous_days'][-1] if cutoff is not None else None,
            'cutoff_date': dates[-1].isoformat(),
            'daily_dates': [day.isoformat() for day in dates[first:]],
            'daily_storage_mm': values,
            'daily_storage_fraction': [round(v/capacity,ROUND_DIGITS) for v in values],
            'longest_converged_daily_dates': [day.isoformat() for day,v in usable],
            'longest_converged_daily_storage_fraction': [round(v/capacity,ROUND_DIGITS) for day,v in usable],
            'daily_actual_evapotranspiration_mm': history['actual_evapotranspiration_mm'][first:],
            'daily_drainage_mm': history['drainage_mm'][first:],
            'daily_unmet_evaporative_demand_mm': history['unmet_evaporative_demand_mm'][first:],
            'reference_parameters': {'evaporation_share':.5,'depletion_fraction':.5},
            'limitations': [
                'SoilGrids is a 250 m prediction, not a plot measurement.',
                'Capacity describes fine earth; no coarse-fragment correction.',
                'No calibrated forest interception, runoff, deep roots or canopy demand.',
            ],
        },
    }


def aggregate_area_soil_water_states(
    microarea_states: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Summarize available micro-area buckets without segmenting observations.

    Every configured micro-area remains represented in quality metadata. The
    area feature uses the available states; it is absent only when none are
    eligible. This mirrors the area-IDW availability rule while preserving the
    nonlinear requirement to simulate each soil bucket first.
    """

    available: list[tuple[str, Mapping[str, object]]] = []
    excluded: dict[str, object] = {}
    cutoff_dates: set[str] = set()
    for micro_area_id, state in sorted(microarea_states.items()):
        quality = state.get("quality")
        metadata = state.get("metadata")
        eligible = isinstance(quality, Mapping) and bool(quality.get("training_eligible"))
        fractions = metadata.get("daily_storage_fraction") if isinstance(metadata, Mapping) else None
        cutoff = metadata.get("cutoff_date") if isinstance(metadata, Mapping) else None
        if eligible and isinstance(fractions, list) and len(fractions) >= 15 and cutoff:
            available.append((micro_area_id, state))
            cutoff_dates.add(str(cutoff))
        else:
            excluded[micro_area_id] = {
                "training_exclusion_reasons": (
                    quality.get("training_exclusion_reasons", [])
                    if isinstance(quality, Mapping)
                    else [{"code": "soil_water_state_invalid", "message": "Estado hídrico ausente o inválido."}]
                ),
                "missing_input_reason_counts": (
                    quality.get("missing_input_reason_counts", {})
                    if isinstance(quality, Mapping)
                    else {}
                ),
                "spinup_convergence": (
                    quality.get("spinup_convergence", {})
                    if isinstance(quality, Mapping)
                    else {}
                ),
            }
    if len(cutoff_dates) > 1:
        raise ValueError("Micro-area soil-water cutoff dates do not align")

    def fraction_series(state: Mapping[str, object]) -> list[float]:
        metadata = state["metadata"]
        return [float(value) for value in metadata["daily_storage_fraction"]]

    if available:
        series = [fraction_series(state) for _micro_area_id, state in available]
        cutoff_values = [values[-1] for values in series]
        mean_cutoff = sum(cutoff_values) / len(cutoff_values)
        min_cutoff = min(cutoff_values)

        def mean_change(age: int) -> float:
            return sum(values[-1] - values[-1 - age] for values in series) / len(series)

        recharge_values: list[float] = []
        drydown_values: list[float] = []
        for values in series:
            recent = values[-8:]
            deltas = [current - previous for previous, current in zip(recent, recent[1:])]
            recharge_values.append(sum(max(0.0, delta) for delta in deltas))
            drydown_values.append(sum(max(0.0, -delta) for delta in deltas))
        predictive = {
            "soil_water_area_mean_at_cutoff": round(mean_cutoff, ROUND_DIGITS),
            "soil_water_area_min_at_cutoff": round(min_cutoff, ROUND_DIGITS),
            "soil_water_change_7d": round(mean_change(7), ROUND_DIGITS),
            "soil_water_change_14d": round(mean_change(14), ROUND_DIGITS),
            "soil_water_recharge_7d": round(sum(recharge_values) / len(recharge_values), ROUND_DIGITS),
            "soil_water_deficit_at_cutoff": round(1.0 - mean_cutoff, ROUND_DIGITS),
            "soil_water_drydown_7d": round(sum(drydown_values) / len(drydown_values), ROUND_DIGITS),
        }
    else:
        predictive = {
            "soil_water_area_mean_at_cutoff": None,
            "soil_water_area_min_at_cutoff": None,
            "soil_water_change_7d": None,
            "soil_water_change_14d": None,
            "soil_water_recharge_7d": None,
            "soil_water_deficit_at_cutoff": None,
            "soil_water_drydown_7d": None,
        }

    return {
        "contract_id": SOIL_WATER_STATE_CONTRACT_ID,
        "predictive_features": predictive,
        "quality": {
            "configured_microarea_count": len(microarea_states),
            "available_microarea_count": len(available),
            "excluded_microarea_count": len(excluded),
            "training_eligible": bool(available),
            "training_exclusion_reasons": (
                []
                if available
                else [{
                    "code": "area_soil_water_unavailable",
                    "message": "Ninguna microárea del área tiene estado hídrico disponible.",
                }]
            ),
        },
        "metadata": {
            "cutoff_date": next(iter(cutoff_dates), None),
            "available_microarea_ids": [micro_area_id for micro_area_id, _state in available],
            "excluded_microareas": excluded,
            "aggregation": "mean_and_min_of_available_microarea_buckets_v1",
            "recharge_semantics": "mean cumulative positive daily storage-fraction changes over ages 0..7",
            "drydown_semantics": "mean cumulative negative daily storage-fraction changes over ages 0..7",
        },
    }
