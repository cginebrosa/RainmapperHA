"""Reproducible climatic water-balance contract for Mushroom Biology V4.

This module deliberately keeps the physical calculation separate from model
training.  Its public result separates predictive features, quality evidence
and metadata so incomplete weather can never be silently interpreted as zero
or leak a quality flag into ``X``.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Sequence


CLIMATIC_WATER_BALANCE_CONTRACT_ID = "microarea_climatic_water_balance_v1"
EVAPOTRANSPIRATION_METHOD_ID = "hargreaves_samani_fao56_temperature_v1"
SOLAR_CONSTANT_MJ_M2_MIN = 0.0820
MJ_M2_TO_EQUIVALENT_EVAPORATION_MM = 0.408
HARGREAVES_COEFFICIENT = 0.0023
HARGREAVES_TEMPERATURE_OFFSET_C = 17.8
ROUND_DIGITS = 6

# Visible labels retain the inherited V3 naming, while the age boundaries are
# explicit and zero based: 0_7d means ages 0..6, not eight calendar days.
FEATURE_WINDOWS: tuple[tuple[str, int, int], ...] = (
    ("0_7d", 0, 6),
    ("8_14d", 7, 13),
    ("15_21d", 14, 20),
    ("22_30d", 21, 29),
)


def _finite_float(value: object, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def extraterrestrial_radiation_mj_m2_day(day: date, latitude_deg: float) -> float:
    """Return daily extraterrestrial radiation using FAO-56 equations.

    The implementation accepts polar dates by clamping the sunset-hour-angle
    argument to its physical domain.  The returned unit is MJ m-2 day-1.
    """

    latitude = _finite_float(latitude_deg, field="latitude_deg")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude_deg must be between -90 and 90")

    julian_day = day.timetuple().tm_yday
    latitude_rad = math.radians(latitude)
    inverse_relative_distance = 1.0 + 0.033 * math.cos(2.0 * math.pi * julian_day / 365.0)
    solar_declination = 0.409 * math.sin(2.0 * math.pi * julian_day / 365.0 - 1.39)
    sunset_argument = -math.tan(latitude_rad) * math.tan(solar_declination)
    sunset_hour_angle = math.acos(max(-1.0, min(1.0, sunset_argument)))
    radiation = (
        (24.0 * 60.0 / math.pi)
        * SOLAR_CONSTANT_MJ_M2_MIN
        * inverse_relative_distance
        * (
            sunset_hour_angle * math.sin(latitude_rad) * math.sin(solar_declination)
            + math.cos(latitude_rad)
            * math.cos(solar_declination)
            * math.sin(sunset_hour_angle)
        )
    )
    return max(0.0, radiation)


def hargreaves_reference_evapotranspiration_mm(
    day: date,
    latitude_deg: float,
    temp_min_c: float,
    temp_max_c: float,
) -> float:
    """Estimate reference evapotranspiration in mm/day.

    Extraterrestrial radiation is converted from MJ m-2 day-1 to equivalent
    evaporation millimetres before applying Hargreaves-Samani.  Temperature
    mean is only an internal equation term and is not exposed as a predictor.
    """

    temp_min = _finite_float(temp_min_c, field="temp_min_c")
    temp_max = _finite_float(temp_max_c, field="temp_max_c")
    if temp_max < temp_min:
        raise ValueError("temp_max_c must be greater than or equal to temp_min_c")

    temp_mean = (temp_min + temp_max) / 2.0
    radiation_mj = extraterrestrial_radiation_mj_m2_day(day, latitude_deg)
    radiation_equivalent_mm = radiation_mj * MJ_M2_TO_EQUIVALENT_EVAPORATION_MM
    estimate = (
        HARGREAVES_COEFFICIENT
        * (temp_mean + HARGREAVES_TEMPERATURE_OFFSET_C)
        * math.sqrt(temp_max - temp_min)
        * radiation_equivalent_mm
    )
    return round(max(0.0, estimate), ROUND_DIGITS)


def _optional_finite(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _validate_series(dates: Sequence[date], *series: Sequence[object]) -> None:
    if not dates:
        raise ValueError("At least one daily weather row is required")
    expected = len(dates)
    if any(len(values) != expected for values in series):
        raise ValueError("Daily climatic-balance inputs must have equal lengths")
    if list(dates) != sorted(dates) or len(set(dates)) != expected:
        raise ValueError("Daily dates must be strictly increasing and unique")
    for previous, current in zip(dates, dates[1:]):
        if (current - previous).days != 1:
            raise ValueError("Daily dates must be consecutive")


def build_climatic_water_balance(
    *,
    dates: Sequence[date],
    rain_idw_mm: Sequence[float | None],
    temp_min_corrected_c: Sequence[float | None],
    temp_max_corrected_c: Sequence[float | None],
    latitude_deg: float,
) -> dict[str, object]:
    """Build daily balance plus the four V4 cutoff-window features.

    A window becomes unavailable when any of its daily inputs is unavailable.
    This strict rule prevents partial sums over different temporal support from
    looking comparable.  Missing inputs are reported in ``quality`` and never
    imputed as zero.
    """

    _validate_series(dates, rain_idw_mm, temp_min_corrected_c, temp_max_corrected_c)
    latitude = _finite_float(latitude_deg, field="latitude_deg")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude_deg must be between -90 and 90")

    daily_eto: list[float | None] = []
    daily_balance: list[float | None] = []
    daily_reasons: list[list[str]] = []
    mass_errors: list[float] = []

    for day, rain_value, min_value, max_value in zip(
        dates, rain_idw_mm, temp_min_corrected_c, temp_max_corrected_c
    ):
        rain = _optional_finite(rain_value)
        temp_min = _optional_finite(min_value)
        temp_max = _optional_finite(max_value)
        reasons: list[str] = []
        if rain is None:
            reasons.append("missing_area_idw_rain")
        elif rain < 0.0:
            reasons.append("negative_area_idw_rain")
        if temp_min is None:
            reasons.append("missing_corrected_temp_min")
        if temp_max is None:
            reasons.append("missing_corrected_temp_max")
        if temp_min is not None and temp_max is not None and temp_max < temp_min:
            reasons.append("temp_max_below_temp_min")

        if reasons:
            daily_eto.append(None)
            daily_balance.append(None)
            daily_reasons.append(reasons)
            continue

        assert rain is not None and temp_min is not None and temp_max is not None
        eto = hargreaves_reference_evapotranspiration_mm(
            day, latitude, temp_min, temp_max
        )
        balance = round(rain - eto, ROUND_DIGITS)
        daily_eto.append(eto)
        daily_balance.append(balance)
        daily_reasons.append([])
        mass_errors.append(abs(rain - eto - balance))

    cutoff_day = dates[-1]
    by_age = {(cutoff_day - day).days: value for day, value in zip(dates, daily_balance)}
    predictive_features: dict[str, float | None] = {}
    window_quality: dict[str, dict[str, object]] = {}
    for label, youngest_age, oldest_age in FEATURE_WINDOWS:
        expected_ages = range(youngest_age, oldest_age + 1)
        values = [by_age.get(age) for age in expected_ages]
        observed = sum(value is not None for value in values)
        complete = observed == len(values)
        predictive_features[f"climatic_water_balance_cutoff_{label}_mm"] = (
            round(sum(float(value) for value in values if value is not None), ROUND_DIGITS)
            if complete
            else None
        )
        window_quality[label] = {
            "expected_days": len(values),
            "observed_days": observed,
            "complete": complete,
        }

    reason_counts: dict[str, int] = {}
    for reasons in daily_reasons:
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return {
        "contract_id": CLIMATIC_WATER_BALANCE_CONTRACT_ID,
        "predictive_features": predictive_features,
        "quality": {
            "daily_expected_days": len(dates),
            "daily_complete_days": sum(value is not None for value in daily_balance),
            "evapotranspiration_input_coverage": round(
                sum(value is not None for value in daily_eto) / len(dates), 6
            ),
            "missing_input_reason_counts": reason_counts,
            "window_coverage": window_quality,
            "water_balance_mass_error_max_mm": round(max(mass_errors, default=0.0), 9),
        },
        "metadata": {
            "evapotranspiration_method": EVAPOTRANSPIRATION_METHOD_ID,
            "latitude_deg": latitude,
            "cutoff_day": cutoff_day.isoformat(),
            "daily_dates": [day.isoformat() for day in dates],
            "daily_reference_evapotranspiration_mm": daily_eto,
            "daily_climatic_water_balance_mm": daily_balance,
            "daily_exclusion_reasons": daily_reasons,
            "window_age_bounds_inclusive": {
                label: [youngest, oldest]
                for label, youngest, oldest in FEATURE_WINDOWS
            },
            "constants": {
                "solar_constant_mj_m2_min": SOLAR_CONSTANT_MJ_M2_MIN,
                "mj_m2_to_equivalent_evaporation_mm": MJ_M2_TO_EQUIVALENT_EVAPORATION_MM,
                "hargreaves_coefficient": HARGREAVES_COEFFICIENT,
                "hargreaves_temperature_offset_c": HARGREAVES_TEMPERATURE_OFFSET_C,
            },
        },
    }
