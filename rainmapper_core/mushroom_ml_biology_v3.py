"""Foundational, non-operational contracts for the Biology V3 benchmark.

This module does not alter or promote Altitude V2.  It builds auditable target,
micro-area and rainfall evidence that a later V3 benchmark/trainer can consume.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

from rainmapper_core import mushroom_known_sites
from rainmapper_core import mushroom_ml_experiments as altitude_v2
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


TARGET_CONTRACT_ID = "outing_value_area_v1"
EPISODE_CONTRACT_ID = "area_microarea_evidence_v1"
QUALITY_CONTRACT_ID = "observed_weather_quality_v1"
AREA_RAINFALL_CONTRACT_ID = "area_daily_mean_microarea_idw_duplicate_zero_v2"
AREA_WEATHER_CONTRACT_ID = "area_daily_mean_microarea_weather_idw_v1"
FIXED_GAP_7D_BIOLOGY_V3_ID = "fixed_gap_7d_biology_v3"
LAG_EVENT_BIOLOGY_V3_ID = "lag_event_biology_v3"

RAIN_EVENT_THRESHOLD_MM = 2.0
SIGNIFICANT_RAIN_THRESHOLD_MM = 5.0
EVENT_LOOKBACK_DAYS = 90

FeatureRole = Literal["predictive", "quality", "metadata"]
FeatureStatus = Literal[
    "active", "inactive", "experimental", "quality_only", "metadata_only"
]

ModelingTarget = Literal["favorable", "unfavorable", "unknown"]


@dataclass(frozen=True)
class TargetPolicy:
    contract_id: str = TARGET_CONTRACT_ID
    favorable_abundances: tuple[str, ...] = (
        "scarce",
        "normal",
        "abundant",
        "very_abundant",
        "exceptional",
    )
    unfavorable_abundances: tuple[str, ...] = ("very_scarce", "absent")

    def digest(self) -> str:
        payload = {
            "contract_id": self.contract_id,
            "favorable_abundances": self.favorable_abundances,
            "unfavorable_abundances": self.unfavorable_abundances,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


DEFAULT_TARGET_POLICY = TargetPolicy()

ABUNDANCE_ORDER = {
    "pending": 0,
    "absent": 1,
    "very_scarce": 2,
    "scarce": 3,
    "normal": 4,
    "abundant": 5,
    "very_abundant": 6,
    "exceptional": 7,
}


@dataclass(frozen=True)
class MicroAreaContext:
    micro_area_id: str
    area_id: str
    lat: float
    lon: float
    location_source: str
    altitude_m: float | None = None
    altitude_source: str | None = None
    soilgrids_water: Mapping[str, object] | None = None


@dataclass(frozen=True)
class AreaPredictionContext:
    area_id: str
    lat: float | None
    lon: float | None
    altitude_m: float | None
    location_source: str = "area_prediction_point"
    altitude_source: str = "known_sites_microarea_dem_mean"


@dataclass(frozen=True)
class BenchmarkField:
    name: str
    role: FeatureRole
    status: FeatureStatus
    description: str


@dataclass(frozen=True)
class BiologyV3FeatureSet:
    feature_set_id: str
    description: str
    horizon_mode: Literal["fixed_7d", "variable"]
    fields: tuple[BenchmarkField, ...]
    max_lookback_days: int = EVENT_LOOKBACK_DAYS

    @property
    def predictive_feature_cols(self) -> tuple[str, ...]:
        """Columns admitted to the default prediction matrix."""
        return tuple(
            field.name
            for field in self.fields
            if field.role == "predictive" and field.status == "active"
        )

    @property
    def candidate_predictive_feature_cols(self) -> tuple[str, ...]:
        """All retained predictors, including currently inactive comparisons."""
        return tuple(field.name for field in self.fields if field.role == "predictive")

    @property
    def inactive_predictive_feature_cols(self) -> tuple[str, ...]:
        return tuple(
            field.name
            for field in self.fields
            if field.role == "predictive" and field.status == "inactive"
        )

    @property
    def experimental_predictive_feature_cols(self) -> tuple[str, ...]:
        return tuple(
            field.name
            for field in self.fields
            if field.role == "predictive" and field.status == "experimental"
        )

    @property
    def quality_cols(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields if field.role == "quality")

    @property
    def metadata_cols(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields if field.role == "metadata")


def _field(
    name: str,
    role: FeatureRole,
    status: FeatureStatus,
    description: str,
) -> BenchmarkField:
    return BenchmarkField(name, role, status, description)


_SHARED_FIELDS = (
    _field("target_month_sin", "predictive", "inactive", "Retained cyclic target month sine; initially inactive after matched V2/V3 comparison."),
    _field("target_month_cos", "predictive", "inactive", "Retained cyclic target month cosine; initially inactive after matched V2/V3 comparison."),
    _field("gis_altitude_m", "predictive", "inactive", "Retained representative DEM altitude; correction remains applied to temperature."),
    _field("rain_cutoff_0_3d_mm", "predictive", "active", "Area IDW rain at ages 0-2 days."),
    _field("rain_cutoff_4_7d_mm", "predictive", "active", "Area IDW rain at ages 3-6 days."),
    _field("rain_cutoff_8_14d_mm", "predictive", "active", "Area IDW rain at ages 7-13 days."),
    _field("rain_cutoff_15_21d_mm", "predictive", "active", "Area IDW rain at ages 14-20 days."),
    _field("rain_cutoff_22_30d_mm", "predictive", "experimental", "Area IDW rain at ages 21-29 days."),
    _field("rain_cutoff_31_60d_mm", "predictive", "experimental", "Area IDW rain at ages 30-59 days."),
    _field("rain_cutoff_61_90d_mm", "predictive", "experimental", "Area IDW rain at ages 60-89 days."),
    _field("days_since_rain_gt_2_at_target", "predictive", "inactive", "Retained inherited 2 mm comparison clock; not a biological gate."),
    _field("days_since_significant_rain_at_target", "predictive", "inactive", "Retained inherited 5 mm comparison clock; not a biological gate."),
    _field("dry_spell_observed_at_cutoff", "predictive", "active", "Observed trailing dry run at the cutoff."),
    _field("temp_max_cutoff_7d_c", "predictive", "active", "Highest altitude-corrected daily maximum temperature in the latest seven cutoff days."),
    _field("temp_min_cutoff_7d_c", "predictive", "active", "Lowest altitude-corrected daily minimum temperature in the latest seven cutoff days."),
    _field("temp_max_mean_cutoff_7d_c", "predictive", "inactive", "Retained mean of daily maximum temperatures over seven days."),
    _field("temp_min_mean_cutoff_7d_c", "predictive", "inactive", "Retained mean of daily minimum temperatures over seven days."),
    _field("temp_mean_cutoff_7d_c", "predictive", "inactive", "Retained seven-day mean derived from daily temperature extremes."),
    _field("humidity_max_cutoff_0_3d_pct", "predictive", "active", "Highest daily maximum relative humidity at ages 0-2 days."),
    _field("humidity_min_cutoff_0_3d_pct", "predictive", "active", "Lowest daily minimum relative humidity at ages 0-2 days."),
    _field("humidity_max_cutoff_4_7d_pct", "predictive", "active", "Highest daily maximum relative humidity at ages 3-6 days."),
    _field("humidity_min_cutoff_4_7d_pct", "predictive", "active", "Lowest daily minimum relative humidity at ages 3-6 days."),
    _field("humidity_max_cutoff_8_14d_pct", "predictive", "active", "Highest daily maximum relative humidity at ages 7-13 days."),
    _field("humidity_min_cutoff_8_14d_pct", "predictive", "active", "Lowest daily minimum relative humidity at ages 7-13 days."),
    _field("humidity_max_cutoff_15_21d_pct", "predictive", "active", "Highest daily maximum relative humidity at ages 14-20 days."),
    _field("humidity_min_cutoff_15_21d_pct", "predictive", "active", "Lowest daily minimum relative humidity at ages 14-20 days."),
    _field("humidity_max_mean_cutoff_0_3d_pct", "predictive", "inactive", "Retained mean of daily maximum relative humidity at ages 0-2 days."),
    _field("humidity_min_mean_cutoff_0_3d_pct", "predictive", "inactive", "Retained mean of daily minimum relative humidity at ages 0-2 days."),
    _field("humidity_max_mean_cutoff_4_7d_pct", "predictive", "inactive", "Retained mean of daily maximum relative humidity at ages 3-6 days."),
    _field("humidity_min_mean_cutoff_4_7d_pct", "predictive", "inactive", "Retained mean of daily minimum relative humidity at ages 3-6 days."),
    _field("humidity_max_mean_cutoff_8_14d_pct", "predictive", "inactive", "Retained mean of daily maximum relative humidity at ages 7-13 days."),
    _field("humidity_min_mean_cutoff_8_14d_pct", "predictive", "inactive", "Retained mean of daily minimum relative humidity at ages 7-13 days."),
    _field("humidity_max_mean_cutoff_15_21d_pct", "predictive", "inactive", "Retained mean of daily maximum relative humidity at ages 14-20 days."),
    _field("humidity_min_mean_cutoff_15_21d_pct", "predictive", "inactive", "Retained mean of daily minimum relative humidity at ages 14-20 days."),
    _field("humidity_mean_cutoff_0_3d_pct", "predictive", "inactive", "Retained mean humidity at ages 0-2 days."),
    _field("humidity_mean_cutoff_4_7d_pct", "predictive", "inactive", "Retained mean humidity at ages 3-6 days."),
    _field("humidity_mean_cutoff_8_14d_pct", "predictive", "inactive", "Retained mean humidity at ages 7-13 days."),
    _field("humidity_mean_cutoff_15_21d_pct", "predictive", "inactive", "Retained mean humidity at ages 14-20 days."),
    _field("humidity_mean_cutoff_7d_pct", "predictive", "inactive", "Retained aggregate of the most recent seven cutoff days; superseded by aligned humidity windows."),
    _field("temp_mean_after_significant_rain_c", "predictive", "inactive", "Corrected temperature after a found rain event; not applicable otherwise."),
    _field("humidity_mean_after_significant_rain_pct", "predictive", "inactive", "Humidity after a found rain event; not applicable otherwise."),
    _field("rain_observed_days_21", "quality", "quality_only", "Available area-IDW rain days in 21 days."),
    _field("rain_missing_days_21", "quality", "quality_only", "Missing area-IDW rain days in 21 days."),
    _field("rain_suppressed_days_21", "quality", "quality_only", "Days with at least one suppressed gauge in 21 days."),
    _field("rain_imputed_duplicate_zero_days_21", "quality", "quality_only", "Days using at least one repeated-positive-as-zero gauge in 21 days."),
    _field("rain_observed_days_90", "quality", "quality_only", "Available area-IDW rain days in 90 days."),
    _field("rain_missing_days_90", "quality", "quality_only", "Missing area-IDW rain days in 90 days."),
    _field("rain_suppressed_days_90", "quality", "quality_only", "Days with at least one suppressed gauge in 90 days."),
    _field("rain_imputed_duplicate_zero_days_90", "quality", "quality_only", "Days using at least one repeated-positive-as-zero gauge in 90 days."),
    _field("dry_spell_is_censored", "quality", "quality_only", "Dry run ended at missing data or the lookback boundary."),
    _field("temp_observed_days_after_significant_rain", "quality", "quality_only", "Temperature support after a found event."),
    _field("humidity_observed_days_after_significant_rain", "quality", "quality_only", "Humidity support after a found event."),
    _field("temperature_observed_days_21", "quality", "quality_only", "Complete area-IDW Tmin/Tmax days."),
    _field("humidity_observed_days_21", "quality", "quality_only", "Complete area-IDW RHmin/RHmax days."),
    _field("daily_series_aligned", "quality", "quality_only", "Rain dates and values share one axis."),
    _field("enough_history", "quality", "quality_only", "Ninety cutoff-relative days are materialized."),
    _field("rain_event_search_complete", "quality", "quality_only", "The rain-event search covers the full lookback."),
    _field("significant_rain_search_complete", "quality", "quality_only", "The significant-event search covers the full lookback."),
    _field("significant_rain_found_90d", "quality", "quality_only", "A 5 mm event was found; retained outside X."),
    _field("temperature_altitude_correction_available", "quality", "quality_only", "Both station and area altitude are available."),
    _field("weather_idw_eligible", "quality", "quality_only", "All four area-IDW weather channels satisfy the cutoff contract."),
    _field("training_eligible", "quality", "quality_only", "All data-quality and required-feature gates passed."),
    _field("training_exclusion_reasons", "quality", "quality_only", "Stable human-readable gate failures."),
    _field("observation_id", "metadata", "metadata_only", "Original observation identity."),
    _field("species_id", "metadata", "metadata_only", "Species model identity."),
    _field("area_id", "metadata", "metadata_only", "Weather context and prediction destination; never X."),
    _field("micro_area_id", "metadata", "metadata_only", "Original evidence location; never X."),
    _field("target_date", "metadata", "metadata_only", "Observation target date."),
    _field("cutoff_date", "metadata", "metadata_only", "Last meteorological day visible to the sample."),
    _field("horizon_days", "metadata", "metadata_only", "Prediction horizon retained outside X for fixed-gap samples."),
    _field("weather_idw", "metadata", "metadata_only", "Multisource IDW contract and daily spatial support audit."),
    _field("weather_series", "metadata", "metadata_only", "Aligned daily source series retained for later comparisons."),
    _field("area_altitude_source", "metadata", "metadata_only", "Auditable source of representative area altitude."),
    _field("validation_group_7d", "metadata", "metadata_only", "Short-fruiting validation group; observations remain separate."),
    _field("validation_group_14d", "metadata", "metadata_only", "Long-fruiting validation group; observations remain separate."),
)


FIXED_GAP_7D_BIOLOGY_V3 = BiologyV3FeatureSet(
    feature_set_id=FIXED_GAP_7D_BIOLOGY_V3_ID,
    description="Observation-preserving seven-day blind-gap Biology V3 benchmark.",
    horizon_mode="fixed_7d",
    fields=_SHARED_FIELDS,
)

LAG_EVENT_BIOLOGY_V3 = BiologyV3FeatureSet(
    feature_set_id=LAG_EVENT_BIOLOGY_V3_ID,
    description="Observation-preserving issue-date Biology V3 benchmark for variable horizons.",
    horizon_mode="variable",
    fields=(
        _field("horizon_days", "predictive", "active", "Days between cutoff and target."),
    )
    + tuple(field for field in _SHARED_FIELDS if field.name != "horizon_days"),
)

BIOLOGY_V3_FEATURE_SETS = {
    FIXED_GAP_7D_BIOLOGY_V3.feature_set_id: FIXED_GAP_7D_BIOLOGY_V3,
    LAG_EVENT_BIOLOGY_V3.feature_set_id: LAG_EVENT_BIOLOGY_V3,
}


def resolve_modeling_target(
    *,
    valid: bool,
    calibration_use: str,
    flush_abundance: str | None,
    policy: TargetPolicy = DEFAULT_TARGET_POLICY,
) -> ModelingTarget:
    """Resolve output utility independently from the visual/catalog V2 label."""
    if valid is not True:
        return "unknown"
    if str(calibration_use or "").strip().lower() != "include":
        return "unknown"
    abundance = str(flush_abundance or "").strip().lower()
    if abundance in policy.unfavorable_abundances:
        return "unfavorable"
    if abundance in policy.favorable_abundances:
        return "favorable"
    return "unknown"


def resolve_observation_target(
    observation: Mapping[str, object],
    policy: TargetPolicy = DEFAULT_TARGET_POLICY,
) -> ModelingTarget:
    return resolve_modeling_target(
        valid=str(observation.get("validation_status") or "").strip().lower() == "valid",
        calibration_use=str(observation.get("calibration_use") or ""),
        flush_abundance=(
            str(observation.get("flush_abundance"))
            if observation.get("flush_abundance") is not None
            else None
        ),
        policy=policy,
    )


def _canonical_target(targets: Sequence[ModelingTarget]) -> ModelingTarget:
    known = [target for target in targets if target != "unknown"]
    if "favorable" in known:
        return "favorable"
    if known and all(target == "unfavorable" for target in known):
        return "unfavorable"
    return "unknown"


def _maximum_abundance(values: Sequence[str]) -> str | None:
    recognized = [value for value in values if value in ABUNDANCE_ORDER]
    if not recognized:
        return None
    return max(recognized, key=lambda value: ABUNDANCE_ORDER[value])


def canonicalize_microarea_observations(
    observations: Sequence[Mapping[str, object]],
    *,
    policy: TargetPolicy = DEFAULT_TARGET_POLICY,
) -> list[dict[str, object]]:
    """Build one auditable row per species, micro-area and observation date."""
    groups: dict[tuple[str, str, str], list[Mapping[str, object]]] = {}
    for observation in observations:
        species_id = str(observation.get("species_id") or "").strip()
        micro_area_id = str(observation.get("micro_area_id") or "").strip()
        observed_at = str(observation.get("observed_at") or "").strip()
        if not species_id or not micro_area_id or not observed_at:
            continue
        groups.setdefault((species_id, micro_area_id, observed_at), []).append(observation)

    canonical: list[dict[str, object]] = []
    for (species_id, micro_area_id, observed_at), rows in sorted(groups.items()):
        targets = [resolve_observation_target(row, policy) for row in rows]
        abundances = sorted(
            {
                str(row.get("flush_abundance") or "").strip().lower()
                for row in rows
                if str(row.get("flush_abundance") or "").strip()
            },
            key=lambda value: (ABUNDANCE_ORDER.get(value, -1), value),
        )
        known_targets = sorted({target for target in targets if target != "unknown"})
        canonical.append(
            {
                "species_id": species_id,
                "micro_area_id": micro_area_id,
                "observed_at": observed_at,
                "modeling_target": _canonical_target(targets),
                "canonical_flush_abundance": _maximum_abundance(abundances),
                "n_source_rows": len(rows),
                "source_observation_ids": sorted(
                    str(row.get("observation_id") or "") for row in rows
                ),
                "distinct_flush_abundances": abundances,
                "distinct_known_targets": known_targets,
                "target_conflict": len(known_targets) > 1,
                "target_contract_id": policy.contract_id,
                "target_policy_sha256": policy.digest(),
            }
        )
    return canonical


def aggregate_area_episodes(
    canonical_microareas: Sequence[Mapping[str, object]],
    micro_area_to_area: Mapping[str, str],
) -> list[dict[str, object]]:
    """Aggregate canonical micro-area evidence without selecting a weather row."""
    groups: dict[tuple[str, str, str], list[Mapping[str, object]]] = {}
    for row in canonical_microareas:
        micro_area_id = str(row.get("micro_area_id") or "")
        area_id = str(micro_area_to_area.get(micro_area_id) or "")
        species_id = str(row.get("species_id") or "")
        observed_at = str(row.get("observed_at") or "")
        if not area_id or not species_id or not observed_at:
            continue
        groups.setdefault((species_id, area_id, observed_at), []).append(row)

    episodes: list[dict[str, object]] = []
    for (species_id, area_id, observed_at), rows in sorted(groups.items()):
        targets = [str(row.get("modeling_target") or "unknown") for row in rows]
        favorable = sum(target == "favorable" for target in targets)
        unfavorable = sum(target == "unfavorable" for target in targets)
        unknown = sum(target == "unknown" for target in targets)
        known = favorable + unfavorable
        episode_target: ModelingTarget
        if favorable:
            episode_target = "favorable"
        elif known and unfavorable == known:
            episode_target = "unfavorable"
        else:
            episode_target = "unknown"
        episodes.append(
            {
                "species_id": species_id,
                "area_id": area_id,
                "observed_at": observed_at,
                "modeling_target": episode_target,
                "n_source_rows": sum(int(row.get("n_source_rows") or 0) for row in rows),
                "n_microareas_observed": len(rows),
                "n_microareas_target_known": known,
                "n_microareas_favorable": favorable,
                "n_microareas_unfavorable": unfavorable,
                "n_microareas_unknown": unknown,
                "mixed_target": favorable > 0 and unfavorable > 0,
                "source_micro_area_ids": sorted(
                    str(row.get("micro_area_id") or "") for row in rows
                ),
                "episode_contract_id": EPISODE_CONTRACT_ID,
            }
        )
    return episodes


def _location_from_micro_area(row: Mapping[str, object]) -> tuple[float, float, str] | None:
    representative = row.get("representative_location")
    if isinstance(representative, Mapping):
        try:
            return float(representative["lat"]), float(representative["lon"]), "representative_location"
        except (KeyError, TypeError, ValueError):
            pass
    derived = row.get("derived_context")
    if isinstance(derived, Mapping):
        geometry_context = derived.get("geometry")
        if isinstance(geometry_context, Mapping):
            centroid = geometry_context.get("centroid")
            if isinstance(centroid, Mapping):
                try:
                    return float(centroid["lat"]), float(centroid["lon"]), "stored_geometry_centroid"
                except (KeyError, TypeError, ValueError):
                    pass
    generated = mushroom_known_sites.derive_geometry_context(row.get("geometry"))
    centroid = generated.get("geometry", {}).get("centroid")
    if isinstance(centroid, Mapping):
        try:
            return float(centroid["lat"]), float(centroid["lon"]), "derived_geometry_centroid"
        except (KeyError, TypeError, ValueError):
            pass
    return None


def load_micro_area_contexts(path: Path) -> dict[str, MicroAreaContext]:
    """Load stable points used by both V3 reconstruction and inference."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, MicroAreaContext] = {}
    for row in payload.get("micro_areas", []):
        if not isinstance(row, Mapping) or row.get("archived"):
            continue
        micro_area_id = str(row.get("micro_area_id") or "").strip()
        area_id = str(row.get("area_id") or "").strip()
        location = _location_from_micro_area(row)
        if not micro_area_id or not area_id or location is None:
            continue
        lat, lon, source = location
        derived = row.get("derived_context")
        gis_dem = derived.get("gis_dem") if isinstance(derived, Mapping) else None
        altitude = (
            _float_or_none(gis_dem.get("altitude_mean_m"))
            if isinstance(gis_dem, Mapping)
            else None
        )
        result[micro_area_id] = MicroAreaContext(
            micro_area_id=micro_area_id,
            area_id=area_id,
            lat=lat,
            lon=lon,
            location_source=source,
            altitude_m=altitude,
            altitude_source=("derived_context.gis_dem.altitude_mean_m" if altitude is not None else None),
            soilgrids_water=(
                dict(derived.get("soilgrids_water"))
                if isinstance(derived, Mapping)
                and isinstance(derived.get("soilgrids_water"), Mapping)
                else None
            ),
        )
    return result


def rainfall_weather_read_scope(
    canonical_microareas: Sequence[Mapping[str, object]],
    *,
    micro_area_contexts: Mapping[str, MicroAreaContext],
    station_catalog: object,
    series_days: int = weather_context.DAILY_SERIES_DAYS,
) -> tuple[set[mushroom_weather_idw.StationKey], date | None, date | None]:
    """Bound a V3 rebuild to useful gauges and observation windows."""
    requests: list[tuple[MicroAreaContext, date, date]] = []
    for row in canonical_microareas:
        context = micro_area_contexts.get(str(row.get("micro_area_id") or ""))
        observed_day = _parse_observed_day(row.get("observed_at"))
        if context is None or observed_day is None:
            continue
        requests.append(
            (context, observed_day - timedelta(days=series_days - 1), observed_day)
        )
    if not requests:
        return set(), None, None

    selected: set[mushroom_weather_idw.StationKey] = set()
    for row in station_catalog.itertuples(index=False):
        source = str(getattr(row, "source", "") or "").strip()
        station_code = str(getattr(row, "station_code", "") or "").strip()
        lat = weather_context.parse_float(getattr(row, "lat", None))
        lon = weather_context.parse_float(getattr(row, "lon", None))
        if not source or not station_code or lat is None or lon is None:
            continue
        first_day = weather_context.parse_day(getattr(row, "first_date", None))
        last_day = weather_context.parse_day(getattr(row, "last_date", None))
        for context, window_start, window_end in requests:
            if first_day is not None and first_day > window_end:
                continue
            if last_day is not None and last_day < window_start:
                continue
            if weather_context.haversine_km(context.lat, context.lon, lat, lon) <= (
                mushroom_weather_idw.RAINFALL_IDW_RADIUS_KM
            ):
                selected.add((source, station_code))
                break
    return (
        selected,
        min(request[1] for request in requests),
        max(request[2] for request in requests),
    )


def _parse_observed_day(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def materialize_microarea_rainfall(
    canonical_microareas: Sequence[Mapping[str, object]],
    *,
    micro_area_contexts: Mapping[str, MicroAreaContext],
    stations: Mapping[mushroom_weather_idw.StationKey, weather_context.WeatherStation],
    excluded_station_keys: frozenset[mushroom_weather_idw.StationKey] | set[mushroom_weather_idw.StationKey],
    series_days: int = weather_context.DAILY_SERIES_DAYS,
) -> list[dict[str, object]]:
    """Attach canonical daily IDW rainfall once per micro-area/date.

    It intentionally does not aggregate rainfall across micro-areas into an
    area episode. That aggregation belongs to a separately versioned V3 feature
    contract and must be chosen from benchmark evidence, not hidden here.
    """
    cache: dict[tuple[str, date], dict[str, object]] = {}
    duplicate_dates = {
        key: mushroom_weather_idw.suppressed_rain_dates(station)
        for key, station in stations.items()
    }
    materialized: list[dict[str, object]] = []
    for source_row in canonical_microareas:
        row = dict(source_row)
        micro_area_id = str(row.get("micro_area_id") or "")
        context = micro_area_contexts.get(micro_area_id)
        observed_day = _parse_observed_day(row.get("observed_at"))
        if context is None or observed_day is None:
            row["rainfall"] = None
            row["rainfall_unavailable_reason"] = (
                "micro_area_location_missing" if context is None else "observation_date_invalid"
            )
            materialized.append(row)
            continue
        key = (micro_area_id, observed_day)
        if key not in cache:
            cache[key] = mushroom_weather_idw.build_daily_weather_idw_series(
                stations,
                target_lat=context.lat,
                target_lon=context.lon,
                target_altitude_m=context.altitude_m,
                end_day=observed_day,
                days=series_days,
                excluded_station_keys=excluded_station_keys,
                duplicate_dates_by_station=duplicate_dates,
            )
        row["rainfall"] = cache[key]
        row["rainfall_unavailable_reason"] = None
        row["rainfall_point"] = {
            "lat": context.lat,
            "lon": context.lon,
            "source": context.location_source,
        }
        materialized.append(row)
    return materialized


def aggregate_area_rainfall_series(
    microarea_series: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Average aligned daily IDW values across configured micro-areas.

    Missing micro-area days do not become zero. The daily value is absent only
    when no configured micro-area has an IDW estimate. Coverage and spatial
    spread remain quality metadata so a smoothed mean never hides its support.
    """
    if not microarea_series:
        raise ValueError("At least one configured micro-area series is required")
    configured = len(microarea_series)
    reference_dates: list[str] | None = None
    values_by_microarea: dict[str, list[float | None]] = {}
    suppressed_by_microarea: dict[str, list[int]] = {}
    imputed_duplicate_zero_by_microarea: dict[str, list[int]] = {}
    for micro_area_id, series in sorted(microarea_series.items()):
        dates = [str(value) for value in series.get("daily_dates", [])]
        raw_values = list(series.get("daily_rain_idw_mm", []))
        if len(dates) != len(raw_values):
            raise ValueError(f"Unaligned rainfall series for {micro_area_id}")
        if reference_dates is None:
            reference_dates = dates
        elif dates != reference_dates:
            raise ValueError("Micro-area rainfall series use different date axes")
        values_by_microarea[micro_area_id] = [
            float(value) if value is not None else None for value in raw_values
        ]
        raw_suppressed = list(series.get("daily_rain_suppressed_station_count", []))
        suppressed_by_microarea[micro_area_id] = (
            [int(value or 0) for value in raw_suppressed]
            if len(raw_suppressed) == len(raw_values)
            else [0] * len(raw_values)
        )
        raw_imputed = list(
            series.get("daily_rain_imputed_duplicate_zero_station_count", [])
        )
        imputed_duplicate_zero_by_microarea[micro_area_id] = (
            [int(value or 0) for value in raw_imputed]
            if len(raw_imputed) == len(raw_values)
            else [0] * len(raw_values)
        )

    daily_mean: list[float | None] = []
    daily_available: list[int] = []
    daily_min: list[float | None] = []
    daily_max: list[float | None] = []
    daily_spread: list[float | None] = []
    daily_suppressed_station_count: list[int] = []
    daily_imputed_duplicate_zero_station_count: list[int] = []
    for index in range(len(reference_dates or [])):
        values = [
            row[index] for row in values_by_microarea.values() if row[index] is not None
        ]
        daily_available.append(len(values))
        daily_suppressed_station_count.append(
            sum(row[index] for row in suppressed_by_microarea.values())
        )
        daily_imputed_duplicate_zero_station_count.append(
            sum(row[index] for row in imputed_duplicate_zero_by_microarea.values())
        )
        if not values:
            daily_mean.append(None)
            daily_min.append(None)
            daily_max.append(None)
            daily_spread.append(None)
            continue
        minimum = min(values)
        maximum = max(values)
        daily_mean.append(statistics.fmean(values))
        daily_min.append(minimum)
        daily_max.append(maximum)
        daily_spread.append(maximum - minimum)

    result: dict[str, object] = {
        "area_rainfall_contract_id": AREA_RAINFALL_CONTRACT_ID,
        "area_weather_contract_id": AREA_WEATHER_CONTRACT_ID,
        "source_rainfall_contract_id": mushroom_weather_idw.RAINFALL_IDW_CONTRACT_ID,
        "source_weather_contract_id": mushroom_weather_idw.WEATHER_IDW_CONTRACT_ID,
        "daily_dates": reference_dates or [],
        "daily_rain_idw_mean_mm": daily_mean,
        "daily_microareas_available": daily_available,
        "configured_microareas": configured,
        "daily_microarea_min_mm": daily_min,
        "daily_microarea_max_mm": daily_max,
        "daily_microarea_spread_mm": daily_spread,
        "daily_rain_suppressed_station_count": daily_suppressed_station_count,
        "daily_rain_imputed_duplicate_zero_station_count": (
            daily_imputed_duplicate_zero_station_count
        ),
        "rain_observed_days": sum(value is not None for value in daily_mean),
        "rain_missing_days": sum(value is None for value in daily_mean),
        "full_microarea_coverage_days": sum(
            count == configured for count in daily_available
        ),
        "partial_microarea_coverage_days": sum(
            0 < count < configured for count in daily_available
        ),
    }
    metric_fields = (
        ("temp_min", "c"),
        ("temp_max", "c"),
        ("humidity_min", "pct"),
        ("humidity_max", "pct"),
    )
    for metric, unit in metric_fields:
        source_key = f"daily_{metric}_idw_{unit}"
        area_key = f"daily_{metric}_idw_mean_{unit}"
        rows_by_microarea: dict[str, list[float | None]] = {}
        for micro_area_id, series in sorted(microarea_series.items()):
            raw = list(series.get(source_key, []))
            if len(raw) != len(reference_dates or []):
                raw = [None] * len(reference_dates or [])
            rows_by_microarea[micro_area_id] = [
                float(value) if value is not None else None for value in raw
            ]
        means: list[float | None] = []
        available_counts: list[int] = []
        for index in range(len(reference_dates or [])):
            values = [
                row[index]
                for row in rows_by_microarea.values()
                if row[index] is not None
            ]
            available_counts.append(len(values))
            means.append(statistics.fmean(values) if values else None)
        result[area_key] = means
        result[f"daily_{metric}_microareas_available"] = available_counts
        result[f"{metric}_observed_days"] = sum(value is not None for value in means)
        result[f"{metric}_missing_days"] = sum(value is None for value in means)
    return result


def biology_v3_feature_registry(feature_set_id: str) -> dict[str, object]:
    """Return the explicit field registry stored with a V3 benchmark."""
    try:
        feature_set = BIOLOGY_V3_FEATURE_SETS[feature_set_id]
    except KeyError as exc:
        raise ValueError(f"Unknown Biology V3 feature_set_id: {feature_set_id}") from exc
    return {
        "id": feature_set.feature_set_id,
        "description": feature_set.description,
        "horizon_mode": feature_set.horizon_mode,
        "max_lookback_days": feature_set.max_lookback_days,
        "predictive_feature_cols": list(feature_set.predictive_feature_cols),
        "candidate_predictive_feature_cols": list(
            feature_set.candidate_predictive_feature_cols
        ),
        "inactive_predictive_feature_cols": list(
            feature_set.inactive_predictive_feature_cols
        ),
        "experimental_predictive_feature_cols": list(
            feature_set.experimental_predictive_feature_cols
        ),
        "quality_cols": list(feature_set.quality_cols),
        "metadata_cols": list(feature_set.metadata_cols),
        "fields": [
            {
                "name": field.name,
                "role": field.role,
                "status": field.status,
                "description": field.description,
            }
            for field in feature_set.fields
        ],
    }


def _float_or_none(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _age_window(
    values: Sequence[float | None], start_age: int, end_age: int
) -> list[float | None]:
    width = end_age - start_age + 1
    end = len(values) - start_age
    start = end - width
    if start < 0 or end > len(values):
        return []
    return list(values[start:end])


def _available_sum(values: Sequence[float | None]) -> float | None:
    available = [float(value) for value in values if value is not None]
    return round(sum(available), 3) if available else None


def _available_mean(values: Sequence[float | None]) -> tuple[float | None, int]:
    available = [float(value) for value in values if value is not None]
    if not available:
        return None, 0
    return round(statistics.fmean(available), 3), len(available)


def _available_min(values: Sequence[float | None]) -> float | None:
    available = [float(value) for value in values if value is not None]
    return round(min(available), 3) if available else None


def _available_max(values: Sequence[float | None]) -> float | None:
    available = [float(value) for value in values if value is not None]
    return round(max(available), 3) if available else None


def _last_event_age(
    values: Sequence[float | None], threshold_mm: float
) -> int | None:
    for age, value in enumerate(reversed(values)):
        if value is not None and value > threshold_mm:
            return age
    return None


def _dry_spell(values: Sequence[float | None]) -> tuple[int | None, bool]:
    run = 0
    for value in reversed(values):
        if value is None:
            return (run if run else None), True
        if value > 0:
            return run, False
        run += 1
    return (run if run else None), True


def _rainfall_at_cutoff(
    area_rainfall: Mapping[str, object] | None,
    cutoff_day: date,
) -> tuple[list[float | None], list[int], list[int], bool, bool, str | None]:
    """Return cutoff-relative IDW rain without converting absence to zero."""
    if not isinstance(area_rainfall, Mapping):
        return [], [], [], False, False, "area_rainfall_missing"
    if area_rainfall.get("area_rainfall_contract_id") != AREA_RAINFALL_CONTRACT_ID:
        return [], [], [], False, False, "area_rainfall_contract_mismatch"
    raw_dates = list(area_rainfall.get("daily_dates", []))
    raw_values = list(area_rainfall.get("daily_rain_idw_mean_mm", []))
    aligned = len(raw_dates) == len(raw_values)
    if not aligned:
        return [], [], False, False, "area_rainfall_series_unaligned"
    suppressed = list(area_rainfall.get("daily_rain_suppressed_station_count", []))
    imputed = list(
        area_rainfall.get("daily_rain_imputed_duplicate_zero_station_count", [])
    )
    if len(suppressed) != len(raw_values):
        suppressed = [0] * len(raw_values)
    if len(imputed) != len(raw_values):
        imputed = [0] * len(raw_values)
    parsed: list[tuple[date, float | None, int, int]] = []
    for raw_day, raw_value, raw_suppressed, raw_imputed in zip(
        raw_dates, raw_values, suppressed, imputed, strict=True
    ):
        day = _parse_observed_day(raw_day)
        if day is None:
            return [], [], [], False, False, "area_rainfall_date_invalid"
        parsed.append((day, _float_or_none(raw_value), int(raw_suppressed or 0), int(raw_imputed or 0)))
    ordered = sorted(parsed, key=lambda item: item[0])
    unique_axis = len({item[0] for item in ordered}) == len(ordered)
    cutoff_rows = [item for item in ordered if item[0] <= cutoff_day]
    expected_axis = list(weather_context.date_window(cutoff_day, EVENT_LOOKBACK_DAYS))
    actual_axis = [item[0] for item in cutoff_rows[-EVENT_LOOKBACK_DAYS:]]
    enough_history = unique_axis and actual_axis == expected_axis
    return (
        [item[1] for item in cutoff_rows],
        [item[2] for item in cutoff_rows],
        [item[3] for item in cutoff_rows],
        unique_axis,
        enough_history,
        None,
    )


def _area_weather_metric_at_cutoff(
    area_weather: Mapping[str, object] | None,
    cutoff_day: date,
    *,
    value_key: str,
    availability_key: str,
) -> tuple[list[float | None], list[int], bool, bool, str | None]:
    """Read one area-level IDW metric on the same cutoff-relative axis."""
    if not isinstance(area_weather, Mapping):
        return [], [], False, False, "area_weather_missing"
    if area_weather.get("area_weather_contract_id") != AREA_WEATHER_CONTRACT_ID:
        return [], [], False, False, "area_weather_contract_mismatch"
    raw_dates = list(area_weather.get("daily_dates", []))
    raw_values = list(area_weather.get(value_key, []))
    raw_availability = list(area_weather.get(availability_key, []))
    if len(raw_dates) != len(raw_values):
        return [], [], False, False, "area_weather_series_unaligned"
    if len(raw_availability) != len(raw_values):
        raw_availability = [0] * len(raw_values)
    parsed: list[tuple[date, float | None, int]] = []
    for raw_day, raw_value, raw_count in zip(
        raw_dates, raw_values, raw_availability, strict=True
    ):
        day = _parse_observed_day(raw_day)
        if day is None:
            return [], [], False, False, "area_weather_date_invalid"
        parsed.append((day, _float_or_none(raw_value), int(raw_count or 0)))
    ordered = sorted(parsed, key=lambda item: item[0])
    unique_axis = len({item[0] for item in ordered}) == len(ordered)
    cutoff_rows = [item for item in ordered if item[0] <= cutoff_day]
    expected_axis = list(weather_context.date_window(cutoff_day, EVENT_LOOKBACK_DAYS))
    actual_axis = [item[0] for item in cutoff_rows[-EVENT_LOOKBACK_DAYS:]]
    enough_history = unique_axis and actual_axis == expected_axis
    return (
        [item[1] for item in cutoff_rows],
        [item[2] for item in cutoff_rows],
        unique_axis,
        enough_history,
        None,
    )
def _station_series(
    station: weather_context.WeatherStation | None,
    cutoff_day: date,
    correction_c: float | None,
) -> tuple[
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
]:
    days = weather_context.date_window(cutoff_day, EVENT_LOOKBACK_DAYS)
    temp_max: list[float | None] = []
    temp_min: list[float | None] = []
    temp_mean: list[float | None] = []
    humidity_max: list[float | None] = []
    humidity_min: list[float | None] = []
    humidity_mean: list[float | None] = []
    for day in days:
        record = station.records_by_day.get(day) if station is not None else None
        raw_max = record.temp_max_c if record is not None else None
        raw_min = record.temp_min_c if record is not None else None
        if raw_max is not None and correction_c is not None:
            temp_max.append(round(float(raw_max) + correction_c, 3))
        else:
            temp_max.append(None)
        if raw_min is not None and correction_c is not None:
            temp_min.append(round(float(raw_min) + correction_c, 3))
        else:
            temp_min.append(None)
        if raw_min is not None and raw_max is not None and correction_c is not None:
            temp_mean.append(
                round(((float(raw_min) + float(raw_max)) / 2.0) + correction_c, 3)
            )
        else:
            temp_mean.append(None)
        raw_humidity_min = record.humidity_min_pct if record is not None else None
        raw_humidity_max = record.humidity_max_pct if record is not None else None
        humidity_min.append(
            round(float(raw_humidity_min), 3)
            if raw_humidity_min is not None
            else None
        )
        humidity_max.append(
            round(float(raw_humidity_max), 3)
            if raw_humidity_max is not None
            else None
        )
        if raw_humidity_min is not None and raw_humidity_max is not None:
            humidity_mean.append(
                round((float(raw_humidity_min) + float(raw_humidity_max)) / 2.0, 3)
            )
        else:
            humidity_mean.append(None)
    return temp_max, temp_min, temp_mean, humidity_max, humidity_min, humidity_mean


def _reason(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def select_cutoff_station_biology_v3(
    stations: Mapping[tuple[str, str], weather_context.WeatherStation],
    *,
    lat: float,
    lon: float,
    cutoff_day: date,
    area_altitude_m: float | None,
) -> tuple[
    weather_context.WeatherStation | None,
    float | None,
    dict[str, object],
]:
    """Reuse V2 coverage at the cutoff and continue past unusable altitude.

    Altitude V2 itself remains frozen. Biology V3 applies the same radius and
    ``station_quality`` thresholds, but altitude correction is a required part
    of this new sample contract, so a nearer station without altitude cannot
    block a later eligible candidate.
    """
    candidates: list[tuple[float, str, str, weather_context.WeatherStation]] = []
    for station in stations.values():
        distance = weather_context.haversine_km(lat, lon, station.lat, station.lon)
        if distance <= weather_context.STATION_MAX_DISTANCE_KM:
            candidates.append(
                (distance, station.source, station.station_code, station)
            )
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    candidate_audit: list[dict[str, object]] = []
    selected_station = None
    selected_distance = None
    selected_rank = None
    for index, (distance, _source, _code, station) in enumerate(candidates):
        quality = weather_context.station_quality(station, cutoff_day)
        rejection_reasons: list[str] = []
        if not bool(quality["eligible"]):
            rejection_reasons.append("v2_quality_below_cutoff_threshold")
        if station.altitude_m is None:
            rejection_reasons.append("station_altitude_missing")
        if area_altitude_m is None:
            rejection_reasons.append("area_altitude_missing")
        candidate_audit.append(
            {
                "source": station.source,
                "station_code": station.station_code,
                "distance_km": round(distance, 3),
                "quality": quality,
                "station_altitude_m": station.altitude_m,
                "rejection_reasons": rejection_reasons,
            }
        )
        if not rejection_reasons and selected_station is None:
            selected_station = station
            selected_distance = distance
            selected_rank = index + 1
            break
    return selected_station, selected_distance, {
        "candidate_count_within_radius": len(candidates),
        "selected_candidate_rank": selected_rank,
        "skipped_nearer_station_count": (selected_rank - 1 if selected_rank else len(candidates)),
        "fallback_selected": bool(selected_rank and selected_rank > 1),
        "candidates_considered": candidate_audit,
        "selected_station_quality": (
            weather_context.station_quality(selected_station, cutoff_day)
            if selected_station is not None else None
        ),
    }


def _build_biology_v3_sample(
    observation: Mapping[str, object],
    *,
    feature_set: BiologyV3FeatureSet,
    horizon_days: int,
    area_context: AreaPredictionContext | None,
    area_rainfall: Mapping[str, object] | None,
    stations: Mapping[tuple[str, str], weather_context.WeatherStation],
) -> dict[str, object]:
    if horizon_days < 1:
        raise ValueError("Biology V3 horizon_days must be >= 1")
    target_day = _parse_observed_day(observation.get("observed_at"))
    cutoff_day = target_day - timedelta(days=horizon_days) if target_day else None
    target = resolve_observation_target(observation)
    reasons: list[dict[str, str]] = []
    if target_day is None or cutoff_day is None:
        reasons.append(_reason("observation_date_invalid", "La fecha de observación no es válida."))
    if target == "unknown":
        reasons.append(_reason("modeling_target_unknown", "La observación no tiene un target V3 entrenable."))
    if area_context is None:
        reasons.append(_reason("area_context_missing", "Falta el contexto meteorológico del área."))

    rain: list[float | None] = []
    suppressed: list[int] = []
    imputed_duplicate_zero: list[int] = []
    aligned = False
    enough_history = False
    rainfall_error: str | None = None
    if cutoff_day is not None:
        rain, suppressed, imputed_duplicate_zero, aligned, enough_history, rainfall_error = _rainfall_at_cutoff(
            area_rainfall, cutoff_day
        )
    if rainfall_error:
        reasons.append(_reason(rainfall_error, "La serie IDW de lluvia del área no está disponible o no cumple su contrato."))
    if not aligned and rainfall_error is None:
        reasons.append(_reason("daily_series_unaligned", "La serie diaria de lluvia no está alineada."))
    if not enough_history:
        reasons.append(_reason("insufficient_daily_history", "No hay 90 días diarios completos hasta el corte."))

    rain_21 = rain[-21:]
    rain_90 = rain[-EVENT_LOOKBACK_DAYS:]
    suppressed_21 = suppressed[-21:]
    suppressed_90 = suppressed[-EVENT_LOOKBACK_DAYS:]
    imputed_duplicate_zero_21 = imputed_duplicate_zero[-21:]
    imputed_duplicate_zero_90 = imputed_duplicate_zero[-EVENT_LOOKBACK_DAYS:]
    rain_observed_21 = sum(value is not None for value in rain_21)
    rain_observed_90 = sum(value is not None for value in rain_90)
    rain_missing_21 = max(0, 21 - rain_observed_21)
    rain_missing_90 = max(0, EVENT_LOOKBACK_DAYS - rain_observed_90)
    rain_suppressed_21 = sum(value > 0 for value in suppressed_21)
    rain_suppressed_90 = sum(value > 0 for value in suppressed_90)
    rain_imputed_duplicate_zero_21 = sum(value > 0 for value in imputed_duplicate_zero_21)
    rain_imputed_duplicate_zero_90 = sum(value > 0 for value in imputed_duplicate_zero_90)
    if rain_observed_21 < weather_context.STATION_RAIN_MIN_DAYS_21:
        reasons.append(_reason("rain_coverage_below_19_of_21", f"Cobertura IDW de lluvia insuficiente: {rain_observed_21}/21 días."))
    if rain_observed_90 < weather_context.STATION_RAIN_MIN_DAYS_90:
        reasons.append(_reason("rain_coverage_below_81_of_90", f"Cobertura IDW de lluvia insuficiente: {rain_observed_90}/90 días."))

    area_altitude = area_context.altitude_m if area_context is not None else None
    metric_specs = {
        "temp_max": ("daily_temp_max_idw_mean_c", "daily_temp_max_microareas_available"),
        "temp_min": ("daily_temp_min_idw_mean_c", "daily_temp_min_microareas_available"),
        "humidity_max": ("daily_humidity_max_idw_mean_pct", "daily_humidity_max_microareas_available"),
        "humidity_min": ("daily_humidity_min_idw_mean_pct", "daily_humidity_min_microareas_available"),
    }
    metric_series: dict[str, list[float | None]] = {}
    metric_availability: dict[str, list[int]] = {}
    metric_errors: dict[str, str] = {}
    if cutoff_day is not None:
        for metric_name, (value_key, availability_key) in metric_specs.items():
            values, availability, metric_aligned, metric_history, metric_error = _area_weather_metric_at_cutoff(
                area_rainfall,
                cutoff_day,
                value_key=value_key,
                availability_key=availability_key,
            )
            metric_series[metric_name] = values[-EVENT_LOOKBACK_DAYS:]
            metric_availability[metric_name] = availability[-EVENT_LOOKBACK_DAYS:]
            if metric_error is not None:
                metric_errors[metric_name] = metric_error
            elif not metric_aligned or not metric_history:
                metric_errors[metric_name] = "area_weather_history_incomplete"
    for metric_name, error in sorted(metric_errors.items()):
        reasons.append(_reason(f"{metric_name}_{error}", f"La serie IDW de {metric_name.replace('_', ' ')} no está disponible o no cubre 90 días hasta el corte."))
    temp_max = metric_series.get("temp_max", [])
    temp_min = metric_series.get("temp_min", [])
    humidity_max = metric_series.get("humidity_max", [])
    humidity_min = metric_series.get("humidity_min", [])
    temp_mean = [
        round((float(low) + float(high)) / 2.0, 3)
        if low is not None and high is not None else None
        for low, high in zip(temp_min, temp_max)
    ]
    humidity_mean = [
        round((float(low) + float(high)) / 2.0, 3)
        if low is not None and high is not None else None
        for low, high in zip(humidity_min, humidity_max)
    ]
    correction_available = (
        area_altitude is not None
        and area_rainfall is not None
        and area_rainfall.get("source_weather_contract_id") == mushroom_weather_idw.WEATHER_IDW_CONTRACT_ID
    )
    temperature_observed_21 = sum(value is not None for value in temp_mean[-21:])
    humidity_observed_21 = sum(value is not None for value in humidity_mean[-21:])
    if temperature_observed_21 < weather_context.STATION_TEMP_MIN_DAYS_21:
        reasons.append(_reason("temperature_coverage_below_19_of_21", f"Cobertura IDW de temperatura insuficiente: {temperature_observed_21}/21 días."))
    if humidity_observed_21 < weather_context.STATION_HUMIDITY_MIN_DAYS_21:
        reasons.append(_reason("humidity_coverage_below_19_of_21", f"Cobertura IDW de humedad insuficiente: {humidity_observed_21}/21 días."))

    rain_age = _last_event_age(rain_90, RAIN_EVENT_THRESHOLD_MM)
    significant_age = _last_event_age(rain_90, SIGNIFICANT_RAIN_THRESHOLD_MM)
    dry_run, dry_censored = _dry_spell(rain_90)
    significant_found = significant_age is not None
    if significant_age is None:
        after_temp, after_temp_days = None, 0
        after_humidity, after_humidity_days = None, 0
    else:
        context_days = significant_age + 1
        after_temp, after_temp_days = _available_mean(temp_mean[-context_days:])
        after_humidity, after_humidity_days = _available_mean(
            humidity_mean[-context_days:]
        )
    temp_max_7d, _temp_max_days = _available_mean(temp_max[-7:])
    temp_min_7d, _temp_min_days = _available_mean(temp_min[-7:])
    temp_mean_7d, _temp_mean_days = _available_mean(temp_mean[-7:])
    temp_max_extreme_7d = _available_max(temp_max[-7:])
    temp_min_extreme_7d = _available_min(temp_min[-7:])
    humidity_mean_7d, _humidity_mean_days = _available_mean(humidity_mean[-7:])
    humidity_mean_0_3d, _humidity_days_0_3d = _available_mean(
        _age_window(humidity_mean, 0, 2)
    )
    humidity_mean_4_7d, _humidity_days_4_7d = _available_mean(
        _age_window(humidity_mean, 3, 6)
    )
    humidity_mean_8_14d, _humidity_days_8_14d = _available_mean(
        _age_window(humidity_mean, 7, 13)
    )
    humidity_mean_15_21d, _humidity_days_15_21d = _available_mean(
        _age_window(humidity_mean, 14, 20)
    )
    humidity_extreme_windows = {
        "humidity_max_cutoff_0_3d_pct": _available_max(_age_window(humidity_max, 0, 2)),
        "humidity_min_cutoff_0_3d_pct": _available_min(_age_window(humidity_min, 0, 2)),
        "humidity_max_cutoff_4_7d_pct": _available_max(_age_window(humidity_max, 3, 6)),
        "humidity_min_cutoff_4_7d_pct": _available_min(_age_window(humidity_min, 3, 6)),
        "humidity_max_cutoff_8_14d_pct": _available_max(_age_window(humidity_max, 7, 13)),
        "humidity_min_cutoff_8_14d_pct": _available_min(_age_window(humidity_min, 7, 13)),
        "humidity_max_cutoff_15_21d_pct": _available_max(_age_window(humidity_max, 14, 20)),
        "humidity_min_cutoff_15_21d_pct": _available_min(_age_window(humidity_min, 14, 20)),
        "humidity_max_mean_cutoff_0_3d_pct": _available_mean(_age_window(humidity_max, 0, 2))[0],
        "humidity_min_mean_cutoff_0_3d_pct": _available_mean(_age_window(humidity_min, 0, 2))[0],
        "humidity_max_mean_cutoff_4_7d_pct": _available_mean(_age_window(humidity_max, 3, 6))[0],
        "humidity_min_mean_cutoff_4_7d_pct": _available_mean(_age_window(humidity_min, 3, 6))[0],
        "humidity_max_mean_cutoff_8_14d_pct": _available_mean(_age_window(humidity_max, 7, 13))[0],
        "humidity_min_mean_cutoff_8_14d_pct": _available_mean(_age_window(humidity_min, 7, 13))[0],
        "humidity_max_mean_cutoff_15_21d_pct": _available_mean(_age_window(humidity_max, 14, 20))[0],
        "humidity_min_mean_cutoff_15_21d_pct": _available_mean(_age_window(humidity_min, 14, 20))[0],
    }
    angle = 2.0 * math.pi * ((target_day.month if target_day else 1) - 1) / 12.0
    predictive_features: dict[str, float | None] = {
        "target_month_sin": round(math.sin(angle), 6),
        "target_month_cos": round(math.cos(angle), 6),
        "gis_altitude_m": _float_or_none(area_altitude),
        "rain_cutoff_0_3d_mm": _available_sum(_age_window(rain, 0, 2)),
        "rain_cutoff_4_7d_mm": _available_sum(_age_window(rain, 3, 6)),
        "rain_cutoff_8_14d_mm": _available_sum(_age_window(rain, 7, 13)),
        "rain_cutoff_15_21d_mm": _available_sum(_age_window(rain, 14, 20)),
        "rain_cutoff_22_30d_mm": _available_sum(_age_window(rain, 21, 29)),
        "rain_cutoff_31_60d_mm": _available_sum(_age_window(rain, 30, 59)),
        "rain_cutoff_61_90d_mm": _available_sum(_age_window(rain, 60, 89)),
        "days_since_rain_gt_2_at_target": (
            float(min(EVENT_LOOKBACK_DAYS, rain_age + horizon_days))
            if rain_age is not None else float(EVENT_LOOKBACK_DAYS)
        ),
        "days_since_significant_rain_at_target": (
            float(min(EVENT_LOOKBACK_DAYS, significant_age + horizon_days))
            if significant_age is not None else float(EVENT_LOOKBACK_DAYS)
        ),
        "dry_spell_observed_at_cutoff": float(dry_run) if dry_run is not None else None,
        "temp_max_cutoff_7d_c": temp_max_extreme_7d,
        "temp_min_cutoff_7d_c": temp_min_extreme_7d,
        "temp_max_mean_cutoff_7d_c": temp_max_7d,
        "temp_min_mean_cutoff_7d_c": temp_min_7d,
        "temp_mean_cutoff_7d_c": temp_mean_7d,
        **humidity_extreme_windows,
        "humidity_mean_cutoff_0_3d_pct": humidity_mean_0_3d,
        "humidity_mean_cutoff_4_7d_pct": humidity_mean_4_7d,
        "humidity_mean_cutoff_8_14d_pct": humidity_mean_8_14d,
        "humidity_mean_cutoff_15_21d_pct": humidity_mean_15_21d,
        "humidity_mean_cutoff_7d_pct": humidity_mean_7d,
        "temp_mean_after_significant_rain_c": after_temp,
        "humidity_mean_after_significant_rain_pct": after_humidity,
    }
    if feature_set.horizon_mode == "variable":
        predictive_features["horizon_days"] = float(horizon_days)

    required_missing = [
        column
        for column in feature_set.predictive_feature_cols
        if predictive_features.get(column) is None
    ]
    if required_missing:
        reasons.append(_reason("required_predictive_features_missing", "Faltan variables predictivas activas: " + ", ".join(required_missing) + "."))

    quality: dict[str, object] = {
        "rain_observed_days_21": rain_observed_21,
        "rain_missing_days_21": rain_missing_21,
        "rain_suppressed_days_21": rain_suppressed_21,
        "rain_imputed_duplicate_zero_days_21": rain_imputed_duplicate_zero_21,
        "rain_observed_days_90": rain_observed_90,
        "rain_missing_days_90": rain_missing_90,
        "rain_suppressed_days_90": rain_suppressed_90,
        "rain_imputed_duplicate_zero_days_90": rain_imputed_duplicate_zero_90,
        "dry_spell_is_censored": dry_censored,
        "temp_observed_days_after_significant_rain": after_temp_days,
        "humidity_observed_days_after_significant_rain": after_humidity_days,
        "temperature_observed_days_21": temperature_observed_21,
        "humidity_observed_days_21": humidity_observed_21,
        "daily_series_aligned": aligned,
        "enough_history": enough_history,
        "rain_event_search_complete": enough_history,
        "significant_rain_search_complete": enough_history,
        "significant_rain_found_90d": significant_found,
        "temperature_altitude_correction_available": correction_available,
        "weather_idw_eligible": not metric_errors,
        "training_eligible": not reasons,
        "training_exclusion_reasons": reasons,
    }
    observation_id = str(observation.get("observation_id") or "").strip()
    if not observation_id:
        identity = "|".join(
            str(observation.get(key) or "")
            for key in ("species_id", "micro_area_id", "observed_at")
        )
        observation_id = "anonymous_" + hashlib.sha256(identity.encode()).hexdigest()[:16]
    metadata: dict[str, object] = {
        "observation_id": observation_id,
        "species_id": str(observation.get("species_id") or ""),
        "area_id": area_context.area_id if area_context is not None else str(observation.get("area_id") or ""),
        "micro_area_id": str(observation.get("micro_area_id") or ""),
        "target_date": target_day.isoformat() if target_day else None,
        "cutoff_date": cutoff_day.isoformat() if cutoff_day else None,
        "horizon_days": horizon_days,
        "weather_idw": {
            "contract_id": mushroom_weather_idw.WEATHER_IDW_CONTRACT_ID,
            "area_contract_id": AREA_WEATHER_CONTRACT_ID,
            "metric_microareas_available": metric_availability,
            "errors": metric_errors,
        },
        "weather_series": {
            "daily_dates": (
                [day.isoformat() for day in weather_context.date_window(cutoff_day, EVENT_LOOKBACK_DAYS)]
                if cutoff_day is not None else []
            ),
            "daily_area_rain_idw_mean_mm": rain[-EVENT_LOOKBACK_DAYS:],
            "daily_temp_max_corrected_c": temp_max,
            "daily_temp_min_corrected_c": temp_min,
            "daily_temp_mean_corrected_c": temp_mean,
            "daily_humidity_max_pct": humidity_max,
            "daily_humidity_min_pct": humidity_min,
            "daily_humidity_mean_pct": humidity_mean,
        },
        "area_representative_location": {
            "lat": area_context.lat if area_context is not None else None,
            "lon": area_context.lon if area_context is not None else None,
            "source": area_context.location_source if area_context is not None else None,
        },
        "area_altitude_source": (
            area_context.altitude_source if area_context is not None else None
        ),
        "temperature_contract": mushroom_weather_idw.WEATHER_IDW_CONTRACT_ID,
        "humidity_contract": mushroom_weather_idw.WEATHER_IDW_CONTRACT_ID,
        "rainfall_contract_id": mushroom_weather_idw.RAINFALL_IDW_CONTRACT_ID,
        "area_rainfall_contract_id": AREA_RAINFALL_CONTRACT_ID,
        "weather_idw_contract_id": mushroom_weather_idw.WEATHER_IDW_CONTRACT_ID,
        "area_weather_contract_id": AREA_WEATHER_CONTRACT_ID,
        "target_contract_id": TARGET_CONTRACT_ID,
        "episode_contract_id": EPISODE_CONTRACT_ID,
        "quality_contract_id": QUALITY_CONTRACT_ID,
        "feature_set_id": feature_set.feature_set_id,
    }
    sample = {
        "sample_id": f"{observation_id}|{feature_set.feature_set_id}|h{horizon_days}",
        "prediction_target": target,
        "predictive_features": predictive_features,
        "quality": quality,
        "metadata": metadata,
    }
    validate_biology_v3_sample(sample, feature_set.feature_set_id)
    return sample


def build_lag_event_biology_v3(
    observation: Mapping[str, object],
    *,
    horizon_days: int,
    area_context: AreaPredictionContext | None,
    area_rainfall: Mapping[str, object] | None,
    stations: Mapping[tuple[str, str], weather_context.WeatherStation],
) -> dict[str, object]:
    """Build one observation-preserving variable-horizon Biology V3 sample."""
    return _build_biology_v3_sample(
        observation,
        feature_set=LAG_EVENT_BIOLOGY_V3,
        horizon_days=horizon_days,
        area_context=area_context,
        area_rainfall=area_rainfall,
        stations=stations,
    )


def build_fixed_gap_7d_biology_v3(
    observation: Mapping[str, object],
    *,
    area_context: AreaPredictionContext | None,
    area_rainfall: Mapping[str, object] | None,
    stations: Mapping[tuple[str, str], weather_context.WeatherStation],
) -> dict[str, object]:
    """Build one observation-preserving seven-day blind-gap V3 sample."""
    return _build_biology_v3_sample(
        observation,
        feature_set=FIXED_GAP_7D_BIOLOGY_V3,
        horizon_days=7,
        area_context=area_context,
        area_rainfall=area_rainfall,
        stations=stations,
    )


def build_biology_v3_inference_sample(
    *,
    species_id: str,
    area_id: str,
    target_date: date,
    horizon_days: int,
    temporal_contract_id: str,
    area_context: AreaPredictionContext | None,
    area_weather: Mapping[str, object] | None,
    stations: Mapping[tuple[str, str], weather_context.WeatherStation],
) -> dict[str, object]:
    """Build a target-free runtime row while retaining every weather gate."""
    observation = {
        "observation_id": f"runtime_{species_id}_{area_id}_{target_date.isoformat()}_h{horizon_days}",
        "species_id": species_id,
        "area_id": area_id,
        "observed_at": target_date.isoformat(),
    }
    if temporal_contract_id == FIXED_GAP_7D_BIOLOGY_V3_ID:
        if horizon_days != 7:
            raise ValueError("Biology V3 fixed inference requires horizon 7")
        sample = build_fixed_gap_7d_biology_v3(
            observation,
            area_context=area_context,
            area_rainfall=area_weather,
            stations=stations,
        )
    elif temporal_contract_id == LAG_EVENT_BIOLOGY_V3_ID:
        if horizon_days not in range(1, 8):
            raise ValueError("Biology V3 lag inference horizon must be between 1 and 7")
        sample = build_lag_event_biology_v3(
            observation,
            horizon_days=horizon_days,
            area_context=area_context,
            area_rainfall=area_weather,
            stations=stations,
        )
    else:
        raise ValueError(f"Unknown Biology V3 inference contract: {temporal_contract_id}")
    quality = dict(sample.get("quality") or {})
    reasons = [
        dict(reason)
        for reason in quality.get("training_exclusion_reasons", [])
        if isinstance(reason, Mapping) and reason.get("code") != "modeling_target_unknown"
    ]
    quality.update(
        {
            "inference_eligible": not reasons,
            "inference_exclusion_reasons": reasons,
            "target_gate_ignored_for_inference": True,
        }
    )
    sample["quality"] = quality
    return sample


def validate_biology_v3_sample(
    sample: Mapping[str, object], feature_set_id: str
) -> None:
    """Reject role leakage before a sample can be turned into X."""
    try:
        feature_set = BIOLOGY_V3_FEATURE_SETS[feature_set_id]
    except KeyError as exc:
        raise ValueError(f"Unknown Biology V3 feature_set_id: {feature_set_id}") from exc
    predictive = sample.get("predictive_features")
    quality = sample.get("quality")
    metadata = sample.get("metadata")
    if not isinstance(predictive, Mapping) or not isinstance(quality, Mapping) or not isinstance(metadata, Mapping):
        raise ValueError("Biology V3 samples require predictive_features, quality and metadata mappings")
    predictive_names = set(predictive)
    leaked_quality = predictive_names & set(feature_set.quality_cols)
    leaked_metadata = predictive_names & set(feature_set.metadata_cols)
    unknown_predictive = predictive_names - set(feature_set.candidate_predictive_feature_cols)
    if leaked_quality:
        raise ValueError("Quality fields cannot enter predictive_features: " + ", ".join(sorted(leaked_quality)))
    if leaked_metadata:
        raise ValueError("Metadata fields cannot enter predictive_features: " + ", ".join(sorted(leaked_metadata)))
    if unknown_predictive:
        raise ValueError("Unregistered predictive fields: " + ", ".join(sorted(unknown_predictive)))


def build_biology_v3_X(
    samples: Sequence[Mapping[str, object]],
    feature_set_id: str,
    *,
    requested_cols: Iterable[str] | None = None,
) -> tuple[list[list[float | None]], list[str]]:
    """Build an un-imputed matrix using only explicitly registered predictors."""
    try:
        feature_set = BIOLOGY_V3_FEATURE_SETS[feature_set_id]
    except KeyError as exc:
        raise ValueError(f"Unknown Biology V3 feature_set_id: {feature_set_id}") from exc
    columns = list(requested_cols or feature_set.predictive_feature_cols)
    quality_requested = set(columns) & set(feature_set.quality_cols)
    metadata_requested = set(columns) & set(feature_set.metadata_cols)
    unknown_requested = set(columns) - set(feature_set.candidate_predictive_feature_cols)
    if quality_requested:
        raise ValueError("Quality fields cannot enter X: " + ", ".join(sorted(quality_requested)))
    if metadata_requested:
        raise ValueError("Metadata fields cannot enter X: " + ", ".join(sorted(metadata_requested)))
    if unknown_requested:
        raise ValueError("Only registered predictive fields can enter X: " + ", ".join(sorted(unknown_requested)))
    matrix: list[list[float | None]] = []
    for sample in samples:
        validate_biology_v3_sample(sample, feature_set_id)
        predictive = sample["predictive_features"]
        assert isinstance(predictive, Mapping)
        matrix.append([_float_or_none(predictive.get(column)) for column in columns])
    return matrix, columns


def build_biology_v3_benchmark(
    observations: Sequence[Mapping[str, object]],
    *,
    feature_set_id: str,
    micro_area_to_area: Mapping[str, str],
    area_contexts: Mapping[str, AreaPredictionContext],
    area_rainfall_by_date: Mapping[tuple[str, str], Mapping[str, object]],
    stations: Mapping[tuple[str, str], weather_context.WeatherStation],
    horizons: Iterable[int] = tuple(range(1, 8)),
) -> dict[str, object]:
    """Build an auditable benchmark without aggregating original observations."""
    try:
        feature_set = BIOLOGY_V3_FEATURE_SETS[feature_set_id]
    except KeyError as exc:
        raise ValueError(f"Unknown Biology V3 feature_set_id: {feature_set_id}") from exc
    horizon_values = (7,) if feature_set.horizon_mode == "fixed_7d" else tuple(sorted(set(int(value) for value in horizons)))
    if not horizon_values or min(horizon_values) < 1:
        raise ValueError("At least one Biology V3 horizon >= 1 is required")
    validation_groups_7d = observation_validation_groups(
        observations, micro_area_to_area=micro_area_to_area, max_duration_days=7
    )
    validation_groups_14d = observation_validation_groups(
        observations, micro_area_to_area=micro_area_to_area, max_duration_days=14
    )
    samples: list[dict[str, object]] = []
    for observation_index, observation in enumerate(observations):
        micro_area_id = str(observation.get("micro_area_id") or "")
        area_id = str(observation.get("area_id") or micro_area_to_area.get(micro_area_id) or "")
        observed_day = _parse_observed_day(observation.get("observed_at"))
        area_context = area_contexts.get(area_id)
        rainfall = area_rainfall_by_date.get(
            (area_id, observed_day.isoformat() if observed_day else "")
        )
        for horizon_days in horizon_values:
            builder = (
                build_fixed_gap_7d_biology_v3
                if feature_set.horizon_mode == "fixed_7d"
                else build_lag_event_biology_v3
            )
            kwargs: dict[str, object] = {
                "area_context": area_context,
                "area_rainfall": rainfall,
                "stations": stations,
            }
            if feature_set.horizon_mode == "variable":
                kwargs["horizon_days"] = horizon_days
            sample = builder(observation, **kwargs)
            sample["metadata"]["validation_group_7d"] = validation_groups_7d[
                observation_index
            ]
            sample["metadata"]["validation_group_14d"] = validation_groups_14d[
                observation_index
            ]
            samples.append(sample)
    return {
        "schema_version": "3.0-benchmark",
        "kind": "mushroom_ml_biology_v3_benchmark",
        "target_contract_id": TARGET_CONTRACT_ID,
        "episode_contract_id": EPISODE_CONTRACT_ID,
        "quality_contract_id": QUALITY_CONTRACT_ID,
        "rainfall_contract_id": mushroom_weather_idw.RAINFALL_IDW_CONTRACT_ID,
        "area_rainfall_contract_id": AREA_RAINFALL_CONTRACT_ID,
        "weather_idw_contract_id": mushroom_weather_idw.WEATHER_IDW_CONTRACT_ID,
        "area_weather_contract_id": AREA_WEATHER_CONTRACT_ID,
        "feature_set": biology_v3_feature_registry(feature_set_id),
        "observation_count": len(observations),
        "validation_group_count_7d": len(set(validation_groups_7d)),
        "validation_group_count_14d": len(set(validation_groups_14d)),
        "sample_count": len(samples),
        "training_eligible_sample_count": sum(
            bool(sample["quality"]["training_eligible"]) for sample in samples
        ),
        "samples": samples,
    }


def observation_validation_groups(
    observations: Sequence[Mapping[str, object]],
    *,
    micro_area_to_area: Mapping[str, str],
    max_duration_days: int,
) -> list[str]:
    """Relate observations without aggregating them into one training row.

    The shared 7/14-day contracts represent short and long fruitings.  A group
    never spans more than the configured duration from its first observation;
    this avoids transitive chains silently creating month-long fruitings.
    """
    if max_duration_days not in {7, 14}:
        raise ValueError("Biology V3 validation groups support 7 or 14 days")
    grouped_indices: dict[tuple[str, str], list[tuple[date, int]]] = {}
    result = [""] * len(observations)
    for index, observation in enumerate(observations):
        species_id = str(observation.get("species_id") or "")
        micro_area_id = str(observation.get("micro_area_id") or "")
        area_id = str(
            observation.get("area_id") or micro_area_to_area.get(micro_area_id) or ""
        )
        observed_day = _parse_observed_day(observation.get("observed_at"))
        if not species_id or not area_id or observed_day is None:
            result[index] = f"unassigned_{max_duration_days}d_{index}"
            continue
        grouped_indices.setdefault((species_id, area_id), []).append(
            (observed_day, index)
        )
    for (species_id, area_id), rows in sorted(grouped_indices.items()):
        group_start: date | None = None
        group_id = ""
        for observed_day, index in sorted(rows, key=lambda item: (item[0], item[1])):
            if group_start is None or (observed_day - group_start).days > max_duration_days:
                group_start = observed_day
                raw_identity = (
                    f"{species_id}|{area_id}|{group_start.isoformat()}|{max_duration_days}"
                )
                group_id = (
                    f"fruiting_{max_duration_days}d_"
                    + hashlib.sha256(raw_identity.encode()).hexdigest()[:16]
                )
            result[index] = group_id
    return result
