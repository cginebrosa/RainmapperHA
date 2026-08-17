#!/usr/bin/env python3
"""Build causal daily V4 rows around hold-outs and measure raw flicker locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_climatic_water_balance as climate
from rainmapper_core import mushroom_known_sites
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_biology_v3_evaluation as evaluation
from rainmapper_core import mushroom_ml_biology_v4 as biology_v4
from rainmapper_core import mushroom_ml_biology_v4_continuity as continuity
from rainmapper_core import mushroom_ml_trainer
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_soil_water_state as soil_water
from rainmapper_core import mushroom_weather_idw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v4-benchmark", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--known-sites", required=True, type=Path)
    parser.add_argument("--stations-file", required=True, type=Path)
    parser.add_argument("--profile", default="climatic_balance")
    parser.add_argument("--eligibility-profile")
    parser.add_argument("--group-days", choices=(7, 14), type=int, required=True)
    parser.add_argument("--horizon-days", choices=(1, 2, 3, 7), type=int)
    parser.add_argument("--padding-days", type=int, default=14)
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
    if args.padding_days < 0:
        raise SystemExit("--padding-days must be >= 0")
    v4_payload = json.loads(args.v4_benchmark.read_text(encoding="utf-8"))
    temporal_id = str(v4_payload.get("temporal_contract_id") or "")
    if temporal_id == biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID:
        horizon_days = 7
        if args.horizon_days not in (None, 7):
            raise SystemExit("fixed_gap requires horizon 7")
    elif temporal_id == biology_v4.LAG_EVENT_BIOLOGY_V4_ID:
        if args.horizon_days is None:
            raise SystemExit("lag_event requires --horizon-days")
        horizon_days = args.horizon_days
    else:
        raise SystemExit(f"Unsupported V4 temporal contract: {temporal_id}")

    soil_variants = v4_payload.get("soil_variants")
    soil_variants = soil_variants if isinstance(soil_variants, dict) else {}
    valid_profiles = set(biology_v4.BLOCK_ORDER) | set(soil_variants)
    eligibility_profile = args.eligibility_profile or args.profile
    unknown_profiles = sorted({args.profile, eligibility_profile} - valid_profiles)
    if unknown_profiles:
        raise SystemExit("Unknown V4 profiles: " + ", ".join(unknown_profiles))
    requested_block = args.profile if args.profile in biology_v4.BLOCK_ORDER else "soil_water"
    eligibility_block = (
        eligibility_profile
        if eligibility_profile in biology_v4.BLOCK_ORDER
        else "soil_water"
    )
    soil_profile_id = next(
        (
            profile_id
            for profile_id in (args.profile, eligibility_profile)
            if profile_id in soil_variants
        ),
        None,
    )
    soil_variant = soil_variants.get(soil_profile_id) if soil_profile_id else None
    benchmark = biology_v4.materialize_comparison_benchmark(
        v4_payload, profile_id=eligibility_profile
    )
    if eligibility_profile != args.profile:
        requested_benchmark = biology_v4.materialize_comparison_benchmark(
            v4_payload, profile_id=args.profile
        )
        requested_by_id = {
            str(row.get("sample_id") or ""): row
            for row in requested_benchmark.get("samples", [])
        }
        for row in benchmark.get("samples", []):
            requested = requested_by_id.get(str(row.get("sample_id") or ""))
            if requested is not None:
                row["predictive_features"] = requested["predictive_features"]
        benchmark["feature_set"] = requested_benchmark["feature_set"]
        benchmark["comparison_profile_id"] = args.profile
        benchmark["eligibility_profile_id"] = eligibility_profile
    eligible = evaluation._eligible_samples(benchmark)
    _train, held_out = evaluation.chronological_group_split(
        eligible, group_days=args.group_days
    )
    target_days_by_area: dict[str, set[date]] = defaultdict(set)
    for sample in held_out:
        metadata = sample.get("metadata") or {}
        if temporal_id == biology_v4.LAG_EVENT_BIOLOGY_V4_ID and int(
            metadata.get("horizon_days") or 0
        ) != horizon_days:
            continue
        area_id = str(metadata.get("area_id") or "")
        raw_day = metadata.get("target_date")
        try:
            observed_day = date.fromisoformat(str(raw_day))
        except ValueError:
            continue
        for offset in range(-args.padding_days, args.padding_days + 1):
            target_days_by_area[area_id].add(observed_day + timedelta(days=offset))
    target_days_by_area = {
        area_id: days for area_id, days in target_days_by_area.items() if area_id and days
    }
    if not target_days_by_area:
        raise SystemExit("No held-out area/date ranges are available")

    sites_payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    micro_rows = {
        str(row.get("micro_area_id") or ""): row
        for row in sites_payload.get("micro_areas", [])
        if isinstance(row, dict) and not row.get("archived")
    }
    micro_contexts = biology_v3.load_micro_area_contexts(args.known_sites)
    micros_by_area: dict[str, list[biology_v3.MicroAreaContext]] = defaultdict(list)
    for context in micro_contexts.values():
        micros_by_area[context.area_id].append(context)
    altitudes = mushroom_ml_trainer.load_area_representative_altitudes(args.known_sites)
    areas: dict[str, biology_v3.AreaPredictionContext] = {}
    for row in sites_payload.get("areas", []):
        if not isinstance(row, dict) or row.get("archived"):
            continue
        area_id = str(row.get("area_id") or "")
        location = row_location(row)
        if area_id and location:
            areas[area_id] = biology_v3.AreaPredictionContext(
                area_id=area_id,
                lat=location[0],
                lon=location[1],
                altitude_m=altitudes.get(area_id),
                location_source=location[2],
                altitude_source="known_sites_microarea_dem_mean",
            )

    all_targets = [day for days in target_days_by_area.values() for day in days]
    earliest_cutoff = min(all_targets) - timedelta(days=horizon_days)
    latest_cutoff = max(all_targets) - timedelta(days=horizon_days)
    daily_lookback = 365 if soil_variant is not None else biology_v3.EVENT_LOOKBACK_DAYS
    weather_start = earliest_cutoff - timedelta(days=daily_lookback - 1)
    catalog = weather_context.load_stations_catalog(args.data_dir)
    points = list(micro_contexts.values()) + [
        area for area_id, area in areas.items() if area_id in target_days_by_area
    ]
    station_filter: set[tuple[str, str]] = set()
    for row in catalog.itertuples(index=False):
        source = str(getattr(row, "source", "") or "").strip()
        code = str(getattr(row, "station_code", "") or "").strip()
        lat = weather_context.parse_float(getattr(row, "lat", None))
        lon = weather_context.parse_float(getattr(row, "lon", None))
        if source and code and lat is not None and lon is not None and any(
            weather_context.haversine_km(point.lat, point.lon, lat, lon)
            <= weather_context.STATION_MAX_DISTANCE_KM
            for point in points
        ):
            station_filter.add((source, code))
    stations = weather_context.load_daily_weather_parquet(
        args.data_dir,
        station_filter=station_filter,
        start_date=weather_start,
        end_date=latest_cutoff,
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

    area_rainfall: dict[str, dict[str, object]] = {}
    micro_rainfall_by_area: dict[str, dict[str, dict[str, object]]] = {}
    for area_id, target_days in sorted(target_days_by_area.items()):
        last_cutoff = max(target_days) - timedelta(days=horizon_days)
        first_cutoff = min(target_days) - timedelta(days=horizon_days)
        series_days = (last_cutoff - first_cutoff).days + daily_lookback
        micro_series = {
            context.micro_area_id: mushroom_weather_idw.build_daily_rain_idw_series(
                stations,
                target_lat=context.lat,
                target_lon=context.lon,
                end_day=last_cutoff,
                days=series_days,
                excluded_station_keys=disabled,
                duplicate_dates_by_station=duplicate_dates,
            )
            for context in sorted(
                micros_by_area.get(area_id, []), key=lambda value: value.micro_area_id
            )
        }
        if micro_series:
            micro_rainfall_by_area[area_id] = micro_series
            area_rainfall[area_id] = biology_v3.aggregate_area_rainfall_series(micro_series)

    daily_rows: list[dict[str, object]] = []
    for area_id, target_days in sorted(target_days_by_area.items()):
        for target_day in sorted(target_days):
            pseudo_observation = {
                "observation_id": f"continuity|{area_id}|{target_day.isoformat()}|h{horizon_days}",
                "area_id": area_id,
                "observed_at": target_day.isoformat(),
            }
            if temporal_id == biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID:
                source = biology_v3.build_fixed_gap_7d_biology_v3(
                    pseudo_observation,
                    area_context=areas.get(area_id),
                    area_rainfall=area_rainfall.get(area_id),
                    stations=stations,
                )
            else:
                source = biology_v3.build_lag_event_biology_v3(
                    pseudo_observation,
                    horizon_days=horizon_days,
                    area_context=areas.get(area_id),
                    area_rainfall=area_rainfall.get(area_id),
                    stations=stations,
                )
            area_soil_state = None
            if soil_variant is not None:
                cutoff_day = target_day - timedelta(days=horizon_days)
                soil_dates = list(weather_context.date_window(cutoff_day, 365))
                area = areas.get(area_id)
                eto: list[float | None] = [None] * len(soil_dates)
                if area is not None:
                    station, _distance, _audit = biology_v3.select_cutoff_station_biology_v3(
                        stations,
                        lat=area.lat,
                        lon=area.lon,
                        cutoff_day=cutoff_day,
                        area_altitude_m=area.altitude_m,
                    )
                    temperatures = biology_v4.build_cutoff_temperature_extremes_with_station_fallback(
                        stations,
                        primary_station=station,
                        dates=soil_dates,
                        cutoff_day=cutoff_day,
                        area_lat=area.lat,
                        area_lon=area.lon,
                        area_altitude_m=area.altitude_m,
                    )
                    eto = [
                        (
                            climate.hargreaves_reference_evapotranspiration_mm(
                                day, area.lat, temp_min, temp_max
                            )
                            if temp_min is not None and temp_max is not None
                            else None
                        )
                        for day, temp_min, temp_max in zip(
                            soil_dates,
                            temperatures["daily_temp_min_corrected_c"],
                            temperatures["daily_temp_max_corrected_c"],
                            strict=True,
                        )
                    ]
                micro_states: dict[str, dict[str, object]] = {}
                for context in micros_by_area.get(area_id, []):
                    rain_series = micro_rainfall_by_area.get(area_id, {}).get(
                        context.micro_area_id, {}
                    )
                    rain_by_day = dict(zip(
                        [str(value) for value in rain_series.get("daily_dates", [])],
                        rain_series.get("daily_rain_idw_mm", []),
                    ))
                    soil_context = (
                        (micro_rows.get(context.micro_area_id, {}).get("derived_context") or {}).get(
                            "soilgrids_water"
                        )
                    )
                    try:
                        micro_states[context.micro_area_id] = soil_water.build_soil_water_state(
                            dates=soil_dates,
                            rain_idw_mm=[rain_by_day.get(day.isoformat()) for day in soil_dates],
                            reference_evapotranspiration_mm=eto,
                            soilgrids_context=soil_context,
                            profile_depth_cm=int(soil_variant["profile_depth_cm"]),
                            field_capacity_property=str(soil_variant["field_capacity_property"]),
                        )
                    except (KeyError, TypeError, ValueError) as exc:
                        micro_states[context.micro_area_id] = {
                            "predictive_features": {},
                            "quality": {
                                "training_eligible": False,
                                "training_exclusion_reasons": [
                                    {"code": "soil_state_build_error", "message": str(exc)}
                                ],
                            },
                            "metadata": {"cutoff_date": cutoff_day.isoformat()},
                        }
                area_soil_state = soil_water.aggregate_area_soil_water_states(micro_states)
            inference_row = biology_v4.materialize_daily_inference_row(
                source,
                temporal_contract_id=temporal_id,
                profile_id=requested_block,
                area_soil_water_state=area_soil_state,
            )
            if eligibility_profile != args.profile:
                gate_row = biology_v4.materialize_daily_inference_row(
                    source,
                    temporal_contract_id=temporal_id,
                    profile_id=eligibility_block,
                    area_soil_water_state=area_soil_state,
                )
                inference_row["quality"] = gate_row["quality"]
                inference_row["metadata"]["eligibility_profile_id"] = eligibility_profile
            daily_rows.append(inference_row)

    report = continuity.evaluate_daily_continuity(
        benchmark,
        daily_rows,
        group_days=args.group_days,
    )
    report["source"] = {
        "v4_benchmark_path": str(args.v4_benchmark),
        "v4_benchmark_sha256": sha256(args.v4_benchmark),
        "known_sites_path": str(args.known_sites),
        "known_sites_sha256": sha256(args.known_sites),
        "stations_file": str(args.stations_file),
        "stations_sha256": sha256(args.stations_file),
        "weather_data_dir": str(args.data_dir),
        "loaded_weather_station_count": len(stations),
        "profile_id": args.profile,
        "eligibility_profile_id": eligibility_profile,
        "horizon_days": horizon_days,
        "padding_days_around_each_held_out_observation": args.padding_days,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "daily_input_row_count": report["daily_input_row_count"],
        "daily_eligible_row_count": report["daily_eligible_row_count"],
        "daily_exclusion_counts": report["daily_exclusion_counts"],
        "species_count": len(report["species"]),
        "model_artifact_written": report["model_artifact_written"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
