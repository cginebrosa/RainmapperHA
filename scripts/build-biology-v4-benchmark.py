#!/usr/bin/env python3
"""Build a local Biology V4 benchmark from an aligned frozen V3 benchmark."""

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


SOIL_VARIANTS = tuple(
    (f"{field.split('_', 1)[0]}_0_{depth}cm", depth, field)
    for depth in soil_water.PROFILE_DEPTH_CANDIDATES_CM
    for field in ("wv0033_mm_per_m", "wv0010_mm_per_m")
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3-benchmark", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--known-sites", required=True, type=Path)
    parser.add_argument("--stations-file", required=True, type=Path)
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
    v3_payload = json.loads(args.v3_benchmark.read_text(encoding="utf-8"))
    source_samples = v3_payload.get("samples", [])
    source_id = str((v3_payload.get("feature_set") or {}).get("id") or "")
    if source_id == biology_v3.FIXED_GAP_7D_BIOLOGY_V3_ID:
        temporal_id = biology_v4.FIXED_GAP_7D_BIOLOGY_V4_ID
    elif source_id == biology_v3.LAG_EVENT_BIOLOGY_V3_ID:
        temporal_id = biology_v4.LAG_EVENT_BIOLOGY_V4_ID
    else:
        raise SystemExit(f"Unsupported V3 feature set: {source_id}")

    sites_payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    micro_contexts = biology_v3.load_micro_area_contexts(args.known_sites)
    micro_rows = {
        str(row.get("micro_area_id") or ""): row
        for row in sites_payload.get("micro_areas", [])
        if isinstance(row, dict) and not row.get("archived")
    }
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

    requested: set[tuple[str, date]] = set()
    for sample in source_samples:
        metadata = sample.get("metadata", {})
        area_id = str(metadata.get("area_id") or "")
        raw_cutoff = metadata.get("cutoff_date")
        try:
            if area_id and raw_cutoff:
                requested.add((area_id, date.fromisoformat(str(raw_cutoff))))
        except ValueError:
            continue
    if not requested:
        raise SystemExit("V3 benchmark contains no usable area/cutoff pairs")
    earliest = min(day for _area, day in requested) - timedelta(days=364)
    latest = max(day for _area, day in requested)
    points = list(micro_contexts.values()) + list(areas.values())
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
            for point in points
        ):
            station_filter.add((source, code))
    stations = weather_context.load_daily_weather_parquet(
        args.data_dir,
        station_filter=station_filter,
        start_date=earliest,
        end_date=latest,
    )
    disabled = mushroom_weather_idw.disabled_wunderground_station_keys(args.stations_file)
    stations = {
        key: station
        for key, station in stations.items()
        if (str(key[0]).lower(), str(key[1]).upper()) not in disabled
    }
    duplicates = {
        key: mushroom_weather_idw.suppressed_rain_dates(station)
        for key, station in stations.items()
    }

    requested_area_ids = {area_id for area_id, _cutoff in requested}
    cache_days = (latest - earliest).days + 1
    cache_dates = list(weather_context.date_window(latest, cache_days))
    microarea_weather_cache: dict[str, dict[str, object]] = {}
    microarea_eto_cache: dict[str, list[float | None]] = {}
    cached_contexts = sorted(
        (
            context
            for context in micro_contexts.values()
            if context.area_id in requested_area_ids
        ),
        key=lambda item: item.micro_area_id,
    )
    for cache_index, context in enumerate(cached_contexts, start=1):
        weather = mushroom_weather_idw.build_daily_weather_idw_series(
            stations,
            target_lat=context.lat,
            target_lon=context.lon,
            target_altitude_m=context.altitude_m,
            end_day=latest,
            days=cache_days,
            excluded_station_keys=disabled,
            duplicate_dates_by_station=duplicates,
        )
        microarea_weather_cache[context.micro_area_id] = weather
        microarea_eto_cache[context.micro_area_id] = [
            (
                climate.hargreaves_reference_evapotranspiration_mm(
                    day, context.lat, low, high
                )
                if low is not None and high is not None
                else None
            )
            for day, low, high in zip(
                cache_dates,
                weather["daily_temp_min_idw_c"],
                weather["daily_temp_max_idw_c"],
                strict=True,
            )
        ]
        if cache_index % 5 == 0 or cache_index == len(cached_contexts):
            print(
                json.dumps(
                    {
                        "cached_microareas": cache_index,
                        "total_microareas": len(cached_contexts),
                        "cached_days_per_microarea": cache_days,
                    }
                ),
                flush=True,
            )

    state_catalog: dict[str, dict[str, object]] = {variant[0]: {} for variant in SOIL_VARIANTS}
    for index, (area_id, cutoff) in enumerate(sorted(requested), start=1):
        state_key = f"{area_id}|{cutoff.isoformat()}"
        dates = list(weather_context.date_window(cutoff, 365))
        slice_start = (cutoff - timedelta(days=364) - earliest).days
        slice_end = slice_start + 365
        micro_rain: dict[str, list[float | None]] = {}
        micro_eto: dict[str, list[float | None]] = {}
        micro_weather_quality: dict[str, dict[str, object]] = {}
        for context in micros_by_area.get(area_id, []):
            cached_weather = microarea_weather_cache.get(context.micro_area_id)
            if cached_weather is None:
                continue
            weather = mushroom_weather_idw.slice_daily_weather_idw_series(
                cached_weather,
                end_day=cutoff,
                days=365,
            )
            micro_rain[context.micro_area_id] = weather["daily_rain_idw_mm"]
            temp_min = weather["daily_temp_min_idw_c"]
            temp_max = weather["daily_temp_max_idw_c"]
            micro_eto[context.micro_area_id] = microarea_eto_cache[
                context.micro_area_id
            ][slice_start:slice_end]
            micro_weather_quality[context.micro_area_id] = {
                "weather_idw_contract_id": weather["weather_idw_contract_id"],
                "target_altitude_m": context.altitude_m,
                "rain_observed_days": weather["rain_observed_days"],
                "temp_min_observed_days": sum(value is not None for value in temp_min),
                "temp_max_observed_days": sum(value is not None for value in temp_max),
            }
        for variant_id, depth, field_property in SOIL_VARIANTS:
            micro_states: dict[str, dict[str, object]] = {}
            for context in micros_by_area.get(area_id, []):
                soil_context = (
                    (micro_rows.get(context.micro_area_id, {}).get("derived_context") or {}).get("soilgrids_water")
                )
                try:
                    micro_states[context.micro_area_id] = soil_water.build_soil_water_state(
                        dates=dates,
                        rain_idw_mm=micro_rain.get(context.micro_area_id, []),
                        reference_evapotranspiration_mm=micro_eto.get(context.micro_area_id, []),
                        soilgrids_context=soil_context,
                        profile_depth_cm=depth,
                        field_capacity_property=field_property,
                    )
                except (TypeError, ValueError) as exc:
                    micro_states[context.micro_area_id] = {
                        "predictive_features": {},
                        "quality": {
                            "training_eligible": False,
                            "training_exclusion_reasons": [{"code": "soil_state_build_error", "message": str(exc)}],
                        },
                        "metadata": {"cutoff_date": cutoff.isoformat()},
                    }
            aggregated = soil_water.aggregate_area_soil_water_states(micro_states)
            aggregated["metadata"]["microarea_weather_idw_quality"] = micro_weather_quality
            state_catalog[variant_id][state_key] = aggregated
        if index % 25 == 0 or index == len(requested):
            print(json.dumps({"completed_area_cutoffs": index, "total_area_cutoffs": len(requested)}), flush=True)

    base_samples: list[dict[str, object]] = []
    block_counts = Counter()
    variant_counts: dict[str, Counter] = {variant[0]: Counter() for variant in SOIL_VARIANTS}
    for source_sample in source_samples:
        metadata = source_sample.get("metadata", {})
        state_key = f"{metadata.get('area_id') or ''}|{metadata.get('cutoff_date') or ''}"
        base = biology_v4.build_biology_v4_sample(
            source_sample,
            temporal_contract_id=temporal_id,
        )
        base["metadata"]["soil_state_key"] = state_key
        for block, eligible in base["quality"]["eligibility_by_block"].items():
            if eligible:
                block_counts[block] += 1
        base_samples.append(base)
        for variant_id, _depth, _field in SOIL_VARIANTS:
            state = state_catalog[variant_id].get(state_key)
            candidate = biology_v4.build_biology_v4_sample(
                source_sample,
                temporal_contract_id=temporal_id,
                area_soil_water_state=state if isinstance(state, dict) else None,
            )
            for block, eligible in candidate["quality"]["eligibility_by_block"].items():
                if eligible:
                    variant_counts[variant_id][block] += 1

    report = {
        "kind": "mushroom_biology_v4_benchmark",
        "schema_version": 1,
        "temporal_contract_id": temporal_id,
        "feature_blocks": {
            block: list(biology_v4.predictive_columns(temporal_id, block))
            for block in biology_v4.BLOCK_ORDER
        },
        "sample_count": len(base_samples),
        "samples": base_samples,
        "base_block_eligible_sample_counts": dict(sorted(block_counts.items())),
        "soil_variants": {
            variant_id: {
                "profile_depth_cm": depth,
                "field_capacity_property": field,
                "eligible_sample_counts": dict(sorted(variant_counts[variant_id].items())),
                "area_state_catalog": state_catalog[variant_id],
            }
            for variant_id, depth, field in SOIL_VARIANTS
        },
        "source": {
            "v3_benchmark_path": str(args.v3_benchmark),
            "v3_benchmark_sha256": sha256(args.v3_benchmark),
            "known_sites_path": str(args.known_sites),
            "known_sites_sha256": sha256(args.known_sites),
            "stations_file": str(args.stations_file),
            "stations_sha256": sha256(args.stations_file),
            "weather_data_dir": str(args.data_dir),
            "loaded_weather_station_count": len(stations),
            "weather_materialization": {
                "mode": "full_microarea_series_then_exact_window_slice",
                "cache_start_date": earliest.isoformat(),
                "cache_end_date": latest.isoformat(),
                "cache_days_per_microarea": cache_days,
                "cached_microarea_count": len(microarea_weather_cache),
                "eto_cached_with_weather": True,
            },
        },
        "operational_model_written": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "temporal_contract_id": temporal_id,
        "sample_count": len(base_samples),
        "base_block_eligible_sample_counts": report["base_block_eligible_sample_counts"],
        "soil_variant_eligible_sample_counts": {
            key: value["eligible_sample_counts"] for key, value in report["soil_variants"].items()
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
