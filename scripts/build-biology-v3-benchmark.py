#!/usr/bin/env python3
"""Build a local, non-operational Biology V3 benchmark.

The script reads immutable local inputs, preserves every observation as a
sample, materializes area IDW rain, and writes no models or operational files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_known_sites
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_trainer
from rainmapper_core import mushroom_ml_weather_workspace
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--known-sites", type=Path, required=True)
    parser.add_argument("--observation-features", type=Path)
    parser.add_argument("--stations-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--feature-set",
        choices=sorted(biology_v3.BIOLOGY_V3_FEATURE_SETS),
        required=True,
    )
    parser.add_argument(
        "--horizons", nargs="+", type=int, default=list(range(1, 8))
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_location(row: dict[str, object]) -> tuple[float, float, str] | None:
    representative = row.get("representative_location")
    if isinstance(representative, dict):
        try:
            return (
                float(representative["lat"]),
                float(representative["lon"]),
                "representative_location",
            )
        except (KeyError, TypeError, ValueError):
            pass
    derived = row.get("derived_context")
    if isinstance(derived, dict):
        centroid = (derived.get("geometry") or {}).get("centroid")
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
    observations_payload = json.loads(args.observations.read_text(encoding="utf-8"))
    sites_payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    observations = observations_payload.get("observations", [])
    if not isinstance(observations, list):
        raise SystemExit("Observations payload does not contain a list")

    micro_area_to_area = mushroom_ml_trainer.load_micro_area_to_area(args.known_sites)
    area_altitudes = mushroom_ml_trainer.load_area_representative_altitudes(
        args.known_sites
    )
    area_altitude_sources = {
        area_id: "known_sites_microarea_dem_mean" for area_id in area_altitudes
    }
    if args.observation_features is not None:
        feature_payload = json.loads(
            args.observation_features.read_text(encoding="utf-8")
        )
        feature_rows = (
            feature_payload.get("rows", [])
            if isinstance(feature_payload, dict)
            else feature_payload
        )
        altitude_by_microarea: dict[str, list[float]] = defaultdict(list)
        for row in feature_rows if isinstance(feature_rows, list) else []:
            micro_area_id = str(row.get("micro_area_id") or "")
            altitude = row.get("gis_altitude_m")
            try:
                if micro_area_id and altitude is not None:
                    altitude_by_microarea[micro_area_id].append(float(altitude))
            except (TypeError, ValueError):
                continue
        fallback_by_area: dict[str, list[float]] = defaultdict(list)
        for micro_area_id, values in altitude_by_microarea.items():
            area_id = micro_area_to_area.get(micro_area_id)
            if area_id and values:
                fallback_by_area[area_id].append(sum(values) / len(values))
        for area_id, values in fallback_by_area.items():
            if area_id not in area_altitudes and values:
                area_altitudes[area_id] = sum(values) / len(values)
                area_altitude_sources[area_id] = (
                    "observation_features_microarea_dem_mean_fallback"
                )
    micro_contexts = biology_v3.load_micro_area_contexts(args.known_sites)
    micro_contexts_by_area: dict[str, list[biology_v3.MicroAreaContext]] = defaultdict(list)
    for context in micro_contexts.values():
        micro_contexts_by_area[context.area_id].append(context)

    area_contexts: dict[str, biology_v3.AreaPredictionContext] = {}
    for row in sites_payload.get("areas", []):
        if not isinstance(row, dict) or row.get("archived"):
            continue
        area_id = str(row.get("area_id") or "")
        location = row_location(row)
        if not area_id or location is None:
            continue
        lat, lon, location_source = location
        area_contexts[area_id] = biology_v3.AreaPredictionContext(
            area_id=area_id,
            lat=lat,
            lon=lon,
            altitude_m=area_altitudes.get(area_id),
            location_source=location_source,
            altitude_source=area_altitude_sources.get(area_id, "missing"),
        )

    requested_area_days: set[tuple[str, date]] = set()
    for observation in observations:
        micro_area_id = str(observation.get("micro_area_id") or "")
        area_id = str(
            observation.get("area_id") or micro_area_to_area.get(micro_area_id) or ""
        )
        observed_day = weather_context.parse_day(observation.get("observed_at"))
        if area_id and observed_day is not None:
            requested_area_days.add((area_id, observed_day))
    if not requested_area_days:
        raise SystemExit("No observation area/date pairs can be materialized")

    earliest_day = min(day for _area_id, day in requested_area_days) - timedelta(
        days=weather_context.DAILY_SERIES_DAYS - 1
    )
    latest_day = max(day for _area_id, day in requested_area_days)
    workspace = mushroom_ml_weather_workspace.active_workspace(
        data_dir=args.data_dir,
        known_sites=args.known_sites,
        stations_file=args.stations_file,
    )
    disabled = mushroom_weather_idw.disabled_wunderground_station_keys(
        args.stations_file
    )
    if workspace is not None:
        stations = workspace.stations_for_view(earliest_day, latest_day)
        duplicate_dates = {}
    else:
        target_points = list(micro_contexts.values()) + list(area_contexts.values())
        catalog = weather_context.load_stations_catalog(args.data_dir)
        station_filter: set[tuple[str, str]] = set()
        for row in catalog.itertuples(index=False):
            source = str(getattr(row, "source", "") or "").strip()
            station_code = str(getattr(row, "station_code", "") or "").strip()
            lat = weather_context.parse_float(getattr(row, "lat", None))
            lon = weather_context.parse_float(getattr(row, "lon", None))
            if not source or not station_code or lat is None or lon is None:
                continue
            if any(
                point.lat is not None
                and point.lon is not None
                and weather_context.haversine_km(point.lat, point.lon, lat, lon)
                <= weather_context.STATION_MAX_DISTANCE_KM
                for point in target_points
            ):
                station_filter.add((source, station_code))
        stations = weather_context.load_daily_weather_parquet(
            args.data_dir,
            station_filter=station_filter,
            start_date=earliest_day,
            end_date=latest_day,
        )
        stations = {
            key: station
            for key, station in stations.items()
            if (str(key[0]).lower(), str(key[1]).upper()) not in disabled
        }
        duplicate_dates = {
            key: mushroom_weather_idw.suppressed_rain_dates(station)
            for key, station in stations.items()
        }

    requested_area_ids = {area_id for area_id, _day in requested_area_days}
    cache_days = (latest_day - earliest_day).days + 1
    microarea_weather_cache: dict[str, dict[str, object]] = {}
    cached_contexts = sorted(
        (
            context
            for context in micro_contexts.values()
            if context.area_id in requested_area_ids
        ),
        key=lambda item: item.micro_area_id,
    )
    for index, context in enumerate(cached_contexts, start=1):
        if workspace is not None:
            microarea_weather_cache.update(
                workspace.weather_for_contexts(
                    [context], start_day=earliest_day, end_day=latest_day
                )
            )
        else:
            microarea_weather_cache[context.micro_area_id] = (
                mushroom_weather_idw.build_daily_weather_idw_series(
                    stations,
                    target_lat=context.lat,
                    target_lon=context.lon,
                    target_altitude_m=context.altitude_m,
                    end_day=latest_day,
                    days=cache_days,
                    excluded_station_keys=disabled,
                    duplicate_dates_by_station=duplicate_dates,
                )
            )
        if index % 5 == 0 or index == len(cached_contexts):
            print(
                json.dumps(
                    {
                        "cached_microareas": index,
                        "total_microareas": len(cached_contexts),
                        "cached_days_per_microarea": cache_days,
                    }
                ),
                flush=True,
            )

    area_rainfall_by_date: dict[tuple[str, str], dict[str, object]] = {}
    for area_id, observed_day in sorted(requested_area_days):
        microarea_series = {
            context.micro_area_id: mushroom_weather_idw.slice_daily_weather_idw_series(
                microarea_weather_cache[context.micro_area_id],
                end_day=observed_day,
                days=weather_context.DAILY_SERIES_DAYS,
            )
            for context in sorted(
                micro_contexts_by_area.get(area_id, []),
                key=lambda item: item.micro_area_id,
            )
            if context.micro_area_id in microarea_weather_cache
        }
        if microarea_series:
            area_rainfall_by_date[(area_id, observed_day.isoformat())] = (
                biology_v3.aggregate_area_rainfall_series(microarea_series)
            )

    benchmark = biology_v3.build_biology_v3_benchmark(
        observations,
        feature_set_id=args.feature_set,
        micro_area_to_area=micro_area_to_area,
        area_contexts=area_contexts,
        area_rainfall_by_date=area_rainfall_by_date,
        stations=stations,
        horizons=args.horizons,
    )
    benchmark["source"] = {
        "observations_path": str(args.observations),
        "observations_sha256": sha256(args.observations),
        "known_sites_path": str(args.known_sites),
        "known_sites_sha256": sha256(args.known_sites),
        "stations_path": str(args.stations_file),
        "stations_sha256": sha256(args.stations_file),
        "weather_data_dir": str(args.data_dir),
        "weather_cache_identity": weather_context.weather_history_cache_identity(
            args.data_dir
        ),
        "weather_materialization": {
            "mode": (
                "shared_maximum_range_then_exact_window_slice"
                if workspace is not None
                else "full_microarea_series_then_exact_window_slice"
            ),
            "cache_start_date": earliest_day.isoformat(),
            "cache_end_date": latest_day.isoformat(),
            "cache_days_per_microarea": cache_days,
            "cached_microarea_count": len(microarea_weather_cache),
        },
        "loaded_weather_station_count": len(stations),
    }
    if args.observation_features is not None:
        benchmark["source"]["observation_features_path"] = str(
            args.observation_features
        )
        benchmark["source"]["observation_features_sha256"] = sha256(
            args.observation_features
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(benchmark, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "feature_set": args.feature_set,
                "observations": benchmark["observation_count"],
                "samples": benchmark["sample_count"],
                "training_eligible_samples": benchmark[
                    "training_eligible_sample_count"
                ],
                "validation_groups_7d": benchmark["validation_group_count_7d"],
                "validation_groups_14d": benchmark["validation_group_count_14d"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
