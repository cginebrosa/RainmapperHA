#!/usr/bin/env python3
"""Compare area-centroid rainfall with mean micro-area IDW rainfall.

The audit is read-only. It uses every weather day in the 120-day evidence
window of every canonical observation belonging to an area with more than one
configured micro-area.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_known_sites
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--known-sites", type=Path, required=True)
    parser.add_argument("--stations-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def parse_day(value: object) -> date | None:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def location_from_geometry(row: dict[str, object]) -> tuple[float, float] | None:
    representative = row.get("representative_location")
    if isinstance(representative, dict):
        try:
            return float(representative["lat"]), float(representative["lon"])
        except (KeyError, TypeError, ValueError):
            pass
    derived = mushroom_known_sites.derive_geometry_context(row.get("geometry"))
    centroid = derived.get("geometry", {}).get("centroid")
    if not isinstance(centroid, dict):
        return None
    try:
        return float(centroid["lat"]), float(centroid["lon"])
    except (KeyError, TypeError, ValueError):
        return None


def main() -> int:
    args = parse_args()
    observation_payload = json.loads(args.observations.read_text(encoding="utf-8"))
    sites_payload = json.loads(args.known_sites.read_text(encoding="utf-8"))
    observations = observation_payload.get("observations", [])
    canonical = biology_v3.canonicalize_microarea_observations(observations)
    contexts = biology_v3.load_micro_area_contexts(args.known_sites)

    contexts_by_area: dict[str, list[biology_v3.MicroAreaContext]] = defaultdict(list)
    for context in contexts.values():
        contexts_by_area[context.area_id].append(context)
    contexts_by_area = {
        area_id: sorted(rows, key=lambda item: item.micro_area_id)
        for area_id, rows in contexts_by_area.items()
        if len(rows) > 1
    }

    area_locations = {
        str(row.get("area_id") or ""): location_from_geometry(row)
        for row in sites_payload.get("areas", [])
        if isinstance(row, dict) and not row.get("archived")
    }
    relevant_days_by_area: dict[str, set[date]] = defaultdict(set)
    for row in canonical:
        context = contexts.get(str(row.get("micro_area_id") or ""))
        observed_day = parse_day(row.get("observed_at"))
        if context is None or observed_day is None or context.area_id not in contexts_by_area:
            continue
        relevant_days_by_area[context.area_id].update(
            observed_day - timedelta(days=offset)
            for offset in range(weather_context.DAILY_SERIES_DAYS)
        )
    if not relevant_days_by_area:
        raise SystemExit("No multi-micro-area observation windows found")

    min_day = min(min(days) for days in relevant_days_by_area.values())
    max_day = max(max(days) for days in relevant_days_by_area.values())
    catalog = weather_context.load_stations_catalog(args.data_dir)
    all_points = [
        context
        for area_id in relevant_days_by_area
        for context in contexts_by_area[area_id]
    ]
    station_filter: set[tuple[str, str]] = set()
    for row in catalog.itertuples(index=False):
        source = str(getattr(row, "source", "") or "").strip()
        station_code = str(getattr(row, "station_code", "") or "").strip()
        lat = weather_context.parse_float(getattr(row, "lat", None))
        lon = weather_context.parse_float(getattr(row, "lon", None))
        if not source or not station_code or lat is None or lon is None:
            continue
        if any(
            weather_context.haversine_km(point.lat, point.lon, lat, lon)
            <= mushroom_weather_idw.RAINFALL_IDW_RADIUS_KM
            for point in all_points
        ):
            station_filter.add((source, station_code))

    disabled = mushroom_weather_idw.disabled_wunderground_station_keys(
        args.stations_file
    )
    station_filter -= set(disabled)
    stations = weather_context.load_daily_weather_parquet(
        args.data_dir,
        station_filter=station_filter,
        start_date=min_day,
        end_date=max_day,
    )
    duplicate_dates = {
        key: mushroom_weather_idw.suppressed_rain_dates(station)
        for key, station in stations.items()
    }

    area_reports: list[dict[str, object]] = []
    all_abs_diff: list[float] = []
    all_relative_diff: list[float] = []
    all_micro_spread: list[float] = []
    exact_or_tenth = 0
    compared_days = 0
    missing_mean_days = 0
    missing_centroid_days = 0
    for area_id, days in sorted(relevant_days_by_area.items()):
        area_point = area_locations.get(area_id)
        if area_point is None:
            continue
        area_abs_diff: list[float] = []
        area_relative_diff: list[float] = []
        area_spread: list[float] = []
        area_compared = 0
        area_missing_mean = 0
        area_missing_centroid = 0
        max_case: dict[str, object] | None = None
        for day in sorted(days):
            micro_values = []
            for context in contexts_by_area[area_id]:
                result = mushroom_weather_idw.estimate_daily_rain_idw(
                    stations,
                    target_lat=context.lat,
                    target_lon=context.lon,
                    day=day,
                    excluded_station_keys=disabled,
                    duplicate_dates_by_station=duplicate_dates,
                )
                if result.rain_mm is not None:
                    micro_values.append(result.rain_mm)
            micro_mean = statistics.fmean(micro_values) if micro_values else None
            centroid = mushroom_weather_idw.estimate_daily_rain_idw(
                stations,
                target_lat=area_point[0],
                target_lon=area_point[1],
                day=day,
                excluded_station_keys=disabled,
                duplicate_dates_by_station=duplicate_dates,
            ).rain_mm
            if micro_mean is None:
                area_missing_mean += 1
                missing_mean_days += 1
            if centroid is None:
                area_missing_centroid += 1
                missing_centroid_days += 1
            if micro_mean is None or centroid is None:
                continue
            absolute = abs(micro_mean - centroid)
            relative = absolute / max(abs(micro_mean), 1.0)
            spread = max(micro_values) - min(micro_values)
            area_abs_diff.append(absolute)
            area_relative_diff.append(relative)
            area_spread.append(spread)
            all_abs_diff.append(absolute)
            all_relative_diff.append(relative)
            all_micro_spread.append(spread)
            area_compared += 1
            compared_days += 1
            if absolute <= 0.1:
                exact_or_tenth += 1
            if max_case is None or absolute > float(max_case["absolute_difference_mm"]):
                max_case = {
                    "date": day.isoformat(),
                    "microarea_mean_mm": micro_mean,
                    "area_centroid_mm": centroid,
                    "absolute_difference_mm": absolute,
                    "microarea_min_mm": min(micro_values),
                    "microarea_max_mm": max(micro_values),
                    "microareas_with_value": len(micro_values),
                }
        area_reports.append(
            {
                "area_id": area_id,
                "configured_microareas": len(contexts_by_area[area_id]),
                "relevant_weather_days": len(days),
                "compared_days": area_compared,
                "missing_microarea_mean_days": area_missing_mean,
                "missing_area_centroid_days": area_missing_centroid,
                "absolute_difference_mm": {
                    "median": percentile(area_abs_diff, 0.5),
                    "p95": percentile(area_abs_diff, 0.95),
                    "maximum": max(area_abs_diff) if area_abs_diff else None,
                },
                "relative_difference": {
                    "median": percentile(area_relative_diff, 0.5),
                    "p95": percentile(area_relative_diff, 0.95),
                },
                "microarea_spread_mm": {
                    "median": percentile(area_spread, 0.5),
                    "p95": percentile(area_spread, 0.95),
                    "maximum": max(area_spread) if area_spread else None,
                },
                "maximum_difference_case": max_case,
            }
        )

    payload = {
        "audit_contract": "biology_v3_area_idw_comparison_v1",
        "rainfall_contract": mushroom_weather_idw.rainfall_idw_contract_metadata(),
        "comparison": {
            "microarea_value": "unweighted arithmetic mean of available daily micro-area IDWs",
            "alternative": "daily IDW at the calculated area geometry centroid",
            "weather_days": "all 120-day evidence windows of canonical observations",
        },
        "inputs": {
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
        },
        "scope": {
            "source_observations": len(observations),
            "canonical_microarea_observations": len(canonical),
            "multi_microarea_areas_with_observations": len(relevant_days_by_area),
            "selected_weather_stations": len(station_filter),
            "loaded_weather_stations": len(stations),
            "date_from": min_day.isoformat(),
            "date_to": max_day.isoformat(),
        },
        "summary": {
            "compared_area_days": compared_days,
            "difference_at_most_0_1_mm_days": exact_or_tenth,
            "difference_at_most_0_1_mm_fraction": (
                exact_or_tenth / compared_days if compared_days else None
            ),
            "missing_microarea_mean_days": missing_mean_days,
            "missing_area_centroid_days": missing_centroid_days,
            "absolute_difference_mm": {
                "median": percentile(all_abs_diff, 0.5),
                "p95": percentile(all_abs_diff, 0.95),
                "p99": percentile(all_abs_diff, 0.99),
                "maximum": max(all_abs_diff) if all_abs_diff else None,
            },
            "relative_difference": {
                "median": percentile(all_relative_diff, 0.5),
                "p95": percentile(all_relative_diff, 0.95),
                "p99": percentile(all_relative_diff, 0.99),
            },
            "microarea_spread_mm": {
                "median": percentile(all_micro_spread, 0.5),
                "p95": percentile(all_micro_spread, 0.95),
                "p99": percentile(all_micro_spread, 0.99),
                "maximum": max(all_micro_spread) if all_micro_spread else None,
            },
        },
        "areas": area_reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["scope"], ensure_ascii=False))
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
