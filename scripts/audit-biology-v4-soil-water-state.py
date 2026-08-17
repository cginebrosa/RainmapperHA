#!/usr/bin/env python3
"""Audit the uncalibrated Biology V4 soil-water bucket on all micro-areas."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_climatic_water_balance as climate
from rainmapper_core import mushroom_known_sites
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_biology_v4 as biology_v4
from rainmapper_core import mushroom_ml_trainer
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_soil_water_state as soil_water
from rainmapper_core import mushroom_weather_idw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--known-sites", required=True, type=Path)
    parser.add_argument("--stations-file", required=True, type=Path)
    parser.add_argument("--cutoff-date", required=True, type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_location(row: dict[str, object]) -> tuple[float, float, str] | None:
    representative = row.get("representative_location")
    if isinstance(representative, dict):
        try:
            return float(representative["lat"]), float(representative["lon"]), "representative_location"
        except (KeyError, TypeError, ValueError):
            pass
    derived = row.get("derived_context")
    centroid = (derived.get("geometry") or {}).get("centroid") if isinstance(derived, dict) else None
    if isinstance(centroid, dict):
        try:
            return float(centroid["lat"]), float(centroid["lon"]), "stored_geometry_centroid"
        except (KeyError, TypeError, ValueError):
            pass
    generated = mushroom_known_sites.derive_geometry_context(row.get("geometry"))
    centroid = generated.get("geometry", {}).get("centroid")
    if isinstance(centroid, dict):
        try:
            return float(centroid["lat"]), float(centroid["lon"]), "derived_geometry_centroid"
        except (KeyError, TypeError, ValueError):
            pass
    return None


def main() -> int:
    args = parse_args()
    payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    micro_contexts = biology_v3.load_micro_area_contexts(args.known_sites)
    area_altitudes = mushroom_ml_trainer.load_area_representative_altitudes(args.known_sites)
    area_contexts: dict[str, biology_v3.AreaPredictionContext] = {}
    for row in payload.get("areas", []):
        if not isinstance(row, dict) or row.get("archived"):
            continue
        area_id = str(row.get("area_id") or "")
        location = row_location(row)
        if area_id and location:
            area_contexts[area_id] = biology_v3.AreaPredictionContext(
                area_id=area_id,
                lat=location[0],
                lon=location[1],
                altitude_m=area_altitudes.get(area_id),
                location_source=location[2],
                altitude_source="known_sites_microarea_dem_mean",
            )

    target_points = list(micro_contexts.values()) + list(area_contexts.values())
    catalog = weather_context.load_stations_catalog(args.data_dir)
    station_filter: set[tuple[str, str]] = set()
    for row in catalog.itertuples(index=False):
        source = str(getattr(row, "source", "") or "").strip()
        code = str(getattr(row, "station_code", "") or "").strip()
        lat = weather_context.parse_float(getattr(row, "lat", None))
        lon = weather_context.parse_float(getattr(row, "lon", None))
        if source and code and lat is not None and lon is not None and any(
            weather_context.haversine_km(point.lat, point.lon, lat, lon)
            <= weather_context.STATION_MAX_DISTANCE_KM
            for point in target_points
        ):
            station_filter.add((source, code))
    start_date = args.cutoff_date - timedelta(days=364)
    stations = weather_context.load_daily_weather_parquet(
        args.data_dir,
        station_filter=station_filter,
        start_date=start_date,
        end_date=args.cutoff_date,
    )
    disabled = mushroom_weather_idw.disabled_wunderground_station_keys(args.stations_file)
    stations = {
        key: station
        for key, station in stations.items()
        if (str(key[0]).lower(), str(key[1]).upper()) not in disabled
    }
    duplicate_dates = {
        key: mushroom_weather_idw.suppressed_rain_dates(station)
        for key, station in stations.items()
    }
    dates = list(weather_context.date_window(args.cutoff_date, 365))

    temperature_by_area: dict[str, tuple[list[float | None], dict[str, object]]] = {}
    for area_id, context in area_contexts.items():
        station, _distance, audit = biology_v3.select_cutoff_station_biology_v3(
            stations,
            lat=context.lat,
            lon=context.lon,
            cutoff_day=args.cutoff_date,
            area_altitude_m=context.altitude_m,
        )
        temperature = biology_v4.build_cutoff_temperature_extremes_with_station_fallback(
            stations,
            primary_station=station,
            dates=dates,
            cutoff_day=args.cutoff_date,
            area_lat=context.lat,
            area_lon=context.lon,
            area_altitude_m=context.altitude_m,
        )
        eto: list[float | None] = [
            (
                climate.hargreaves_reference_evapotranspiration_mm(
                    day, context.lat, temp_min, temp_max
                )
                if temp_min is not None and temp_max is not None
                else None
            )
            for day, temp_min, temp_max in zip(
                dates,
                temperature["daily_temp_min_corrected_c"],
                temperature["daily_temp_max_corrected_c"],
                strict=True,
            )
        ]
        temperature_by_area[area_id] = (
            eto,
            {
                "station_selected": station is not None,
                "station_code": station.station_code if station else None,
                "temperature_fallback_quality": temperature["quality"],
                "observed_eto_days_365": sum(value is not None for value in eto),
                "selection_audit": audit,
            },
        )

    micro_rows = {
        str(row.get("micro_area_id") or ""): row
        for row in payload.get("micro_areas", [])
        if isinstance(row, dict) and not row.get("archived")
    }
    variants = [
        (depth, field_property)
        for depth in soil_water.PROFILE_DEPTH_CANDIDATES_CM
        for field_property in ("wv0033_mm_per_m", "wv0010_mm_per_m")
    ]
    summary: dict[str, Counter] = defaultdict(Counter)
    eligible_areas: dict[str, set[str]] = defaultdict(set)
    states_by_variant_area: dict[str, dict[str, dict[str, dict[str, object]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    results: list[dict[str, object]] = []
    for micro_area_id, context in sorted(micro_contexts.items()):
        row = micro_rows.get(micro_area_id, {})
        soil_context = (row.get("derived_context") or {}).get("soilgrids_water")
        rain = mushroom_weather_idw.build_daily_rain_idw_series(
            stations,
            target_lat=context.lat,
            target_lon=context.lon,
            end_day=args.cutoff_date,
            days=365,
            excluded_station_keys=disabled,
            duplicate_dates_by_station=duplicate_dates,
        )
        eto, area_temperature = temperature_by_area.get(context.area_id, ([], {}))
        variant_rows: list[dict[str, object]] = []
        for depth, field_property in variants:
            variant_id = f"{field_property.split('_', 1)[0]}_0_{depth}cm"
            try:
                state = soil_water.build_soil_water_state(
                    dates=dates,
                    rain_idw_mm=rain["daily_rain_idw_mm"],
                    reference_evapotranspiration_mm=eto,
                    soilgrids_context=soil_context,
                    profile_depth_cm=depth,
                    field_capacity_property=field_property,
                )
                selected = state["metadata"]["selected_spinup_days"]
                eligible = bool(state["quality"]["training_eligible"])
                status_key = f"spinup_{selected}" if selected else str(
                    state["quality"]["training_exclusion_reasons"][0]["code"]
                )
                summary[variant_id][status_key] += 1
                if eligible:
                    eligible_areas[variant_id].add(context.area_id)
                states_by_variant_area[variant_id][context.area_id][micro_area_id] = state
                capacity = state["metadata"]["capacity"]["capacity_mm"]
                variant_rows.append(
                    {
                        "variant_id": variant_id,
                        "capacity_mm": capacity,
                        "selected_spinup_days": selected,
                        "eligible": eligible,
                        "cutoff_fraction": state["predictive_features"]["soil_water_at_cutoff_fraction"],
                        "exclusion_reasons": state["quality"]["training_exclusion_reasons"],
                        "missing_input_reason_counts": state["quality"]["missing_input_reason_counts"],
                        "spinup_convergence": state["quality"]["spinup_convergence"],
                        "mass_error_max_mm": state["quality"]["water_balance_mass_error_max_mm"],
                    }
                )
            except (TypeError, ValueError) as exc:
                summary[variant_id]["error"] += 1
                variant_rows.append({"variant_id": variant_id, "eligible": False, "error": str(exc)})
        results.append(
            {
                "micro_area_id": micro_area_id,
                "area_id": context.area_id,
                "rain_observed_days_365": rain["rain_observed_days"],
                "temperature": area_temperature,
                "variants": variant_rows,
            }
        )

    area_aggregations: dict[str, list[dict[str, object]]] = {}
    for variant_id, _counts in sorted(summary.items()):
        area_aggregations[variant_id] = []
        for area_id in sorted(area_contexts):
            aggregated = soil_water.aggregate_area_soil_water_states(
                states_by_variant_area[variant_id].get(area_id, {})
            )
            area_aggregations[variant_id].append(
                {
                    "area_id": area_id,
                    "predictive_features": aggregated["predictive_features"],
                    "quality": aggregated["quality"],
                    "metadata": aggregated["metadata"],
                }
            )

    report = {
        "kind": "mushroom_biology_v4_soil_water_state_audit",
        "schema_version": 1,
        "status": "pass",
        "contract_id": soil_water.SOIL_WATER_STATE_CONTRACT_ID,
        "validation_state": soil_water.VALIDATION_STATE,
        "input": {
            "known_sites_path": str(args.known_sites),
            "known_sites_sha256": sha256(args.known_sites),
            "weather_data_dir": str(args.data_dir),
            "cutoff_date": args.cutoff_date.isoformat(),
            "loaded_station_count": len(stations),
        },
        "variant_summary": {
            variant: dict(sorted(counts.items())) for variant, counts in sorted(summary.items())
        },
        "variant_area_coverage": {
            variant: {
                "configured_area_count": len(area_contexts),
                "eligible_area_count": len(eligible_areas[variant]),
                "unavailable_area_ids": sorted(set(area_contexts) - eligible_areas[variant]),
            }
            for variant, _counts in sorted(summary.items())
        },
        "area_aggregations": area_aggregations,
        "micro_areas": results,
        "limits": [
            "This is an uncalibrated fine-earth index, not measured volumetric soil moisture.",
            "No coarse-fragment, interception, runoff, vegetation or calibrated root correction is applied.",
            "Variants are retained for comparison; this audit does not select a biological winner.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "variant_summary": report["variant_summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
