#!/usr/bin/env python3
"""Build non-operational Biology V5 raw365 benchmarks from frozen V3 rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_climatic_water_balance as climate
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_raw_weather as raw_weather
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_soil_water_state
from rainmapper_core import mushroom_weather_idw


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3-fixed", required=True, type=Path)
    parser.add_argument("--v3-lag", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--known-sites", required=True, type=Path)
    parser.add_argument("--stations-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def _mean_series(rows: list[list[float | None]], length: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(length):
        values = [float(row[index]) for row in rows if index < len(row) and row[index] is not None]
        result.append(statistics.fmean(values) if values else None)
    return result


def main() -> int:
    args = parse_args()
    fixed = json.loads(args.v3_fixed.read_text(encoding="utf-8"))
    lag = json.loads(args.v3_lag.read_text(encoding="utf-8"))
    payloads = (
        (fixed, raw_weather.FIXED_CONTRACT_ID, "biology-v5-fixed.json"),
        (lag, raw_weather.LAG_CONTRACT_ID, "biology-v5-lag.json"),
    )
    all_samples = [sample for payload, _contract, _name in payloads for sample in payload.get("samples", [])]
    requested: set[tuple[str, date]] = set()
    for sample in all_samples:
        metadata = sample.get("metadata") or {}
        try:
            area_id = str(metadata["area_id"])
            cutoff = date.fromisoformat(str(metadata["cutoff_date"]))
            if area_id:
                requested.add((area_id, cutoff))
        except (KeyError, ValueError):
            continue
    if not requested:
        raise SystemExit("source benchmarks contain no area/cutoff pairs")

    micro_contexts = biology_v3.load_micro_area_contexts(args.known_sites)
    micros_by_area: dict[str, list[biology_v3.MicroAreaContext]] = defaultdict(list)
    for context in micro_contexts.values():
        micros_by_area[context.area_id].append(context)
    requested_areas = {area for area, _cutoff in requested}
    contexts = sorted(
        (context for context in micro_contexts.values() if context.area_id in requested_areas),
        key=lambda context: context.micro_area_id,
    )
    earliest = min(cutoff for _area, cutoff in requested) - timedelta(days=raw_weather.LOOKBACK_DAYS - 1)
    latest = max(cutoff for _area, cutoff in requested)
    cache_days = (latest - earliest).days + 1
    cache_dates = list(weather_context.date_window(latest, cache_days))

    catalog = weather_context.load_stations_catalog(args.data_dir)
    station_filter: set[tuple[str, str]] = set()
    for row in catalog.itertuples(index=False):
        source = str(getattr(row, "source", "") or "").strip()
        code = str(getattr(row, "station_code", "") or "").strip()
        lat = weather_context.parse_float(getattr(row, "lat", None))
        lon = weather_context.parse_float(getattr(row, "lon", None))
        if source and code and lat is not None and lon is not None and any(
            weather_context.haversine_km(context.lat, context.lon, lat, lon)
            <= mushroom_weather_idw.RAINFALL_IDW_RADIUS_KM
            for context in contexts
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
    duplicates = {key: mushroom_weather_idw.suppressed_rain_dates(value) for key, value in stations.items()}

    weather_cache: dict[str, dict[str, object]] = {}
    eto_cache: dict[str, list[float | None]] = {}
    for index, context in enumerate(contexts, start=1):
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
        weather_cache[context.micro_area_id] = weather
        eto_cache[context.micro_area_id] = [
            climate.hargreaves_reference_evapotranspiration_mm(day, context.lat, low, high)
            if low is not None and high is not None
            else None
            for day, low, high in zip(
                cache_dates,
                weather["daily_temp_min_idw_c"],
                weather["daily_temp_max_idw_c"],
                strict=True,
            )
        ]
        if index % 5 == 0 or index == len(contexts):
            print(json.dumps({"cached_microareas": index, "total_microareas": len(contexts)}), flush=True)

    area_cache: dict[str, dict[str, object]] = {}
    for index, (area_id, cutoff) in enumerate(sorted(requested), start=1):
        sliced: dict[str, dict[str, object]] = {}
        micro_eto: list[list[float | None]] = []
        micro_balance: list[list[float | None]] = []
        micro_soil_states: dict[str, dict[str, object]] = {}
        axis = list(weather_context.date_window(cutoff, raw_weather.LOOKBACK_DAYS))
        slice_start = (cutoff - timedelta(days=raw_weather.LOOKBACK_DAYS - 1) - earliest).days
        slice_end = slice_start + raw_weather.LOOKBACK_DAYS
        for context in micros_by_area.get(area_id, []):
            cached = weather_cache.get(context.micro_area_id)
            if cached is None:
                continue
            weather = mushroom_weather_idw.slice_daily_weather_idw_series(
                cached, end_day=cutoff, days=raw_weather.LOOKBACK_DAYS
            )
            sliced[context.micro_area_id] = weather
            eto = eto_cache[context.micro_area_id][slice_start:slice_end]
            micro_eto.append(eto)
            micro_balance.append(
                [
                    float(rain) - float(eto_value)
                    if rain is not None and eto_value is not None
                    else None
                    for rain, eto_value in zip(
                        weather["daily_rain_idw_mm"], eto, strict=True
                    )
                ]
            )
            try:
                micro_soil_states[context.micro_area_id] = (
                    mushroom_soil_water_state.build_soil_water_state(
                        dates=axis,
                        rain_idw_mm=weather["daily_rain_idw_mm"],
                        reference_evapotranspiration_mm=eto,
                        soilgrids_context=context.soilgrids_water or {},
                    )
                )
            except (TypeError, ValueError) as exc:
                micro_soil_states[context.micro_area_id] = {
                    "predictive_features": {},
                    "quality": {
                        "training_eligible": False,
                        "training_exclusion_reasons": [
                            {"code": "soil_state_build_error", "message": str(exc)}
                        ],
                    },
                    "metadata": {"cutoff_date": cutoff.isoformat()},
                }
        area = biology_v3.aggregate_area_rainfall_series(sliced)
        area["daily_eto0_mean_mm"] = _mean_series(
            micro_eto, raw_weather.LOOKBACK_DAYS
        )
        area["daily_climatic_balance_mean_mm"] = _mean_series(
            micro_balance, raw_weather.LOOKBACK_DAYS
        )
        soil_state = mushroom_soil_water_state.aggregate_area_soil_water_states(
            micro_soil_states
        )
        daily_soil_by_microarea: list[dict[str, float]] = []
        for state in micro_soil_states.values():
            quality = state.get("quality")
            metadata = state.get("metadata")
            if not isinstance(quality, dict) or not quality.get("training_eligible"):
                continue
            if not isinstance(metadata, dict):
                continue
            dates = list(metadata.get("longest_converged_daily_dates") or [])
            values = list(
                metadata.get("longest_converged_daily_storage_fraction") or []
            )
            if len(dates) == len(values):
                daily_soil_by_microarea.append(
                    {
                        str(day): float(value)
                        for day, value in zip(dates, values, strict=True)
                    }
                )
        area["daily_soil_water_fraction_mean"] = [
            (
                statistics.fmean(
                    row[day.isoformat()]
                    for row in daily_soil_by_microarea
                    if day.isoformat() in row
                )
                if any(day.isoformat() in row for row in daily_soil_by_microarea)
                else None
            )
            for day in axis
        ]
        area.update(dict(soil_state.get("predictive_features") or {}))
        area["soil_water_quality"] = dict(soil_state.get("quality") or {})
        area["soil_water_metadata"] = dict(soil_state.get("metadata") or {})
        area_cache[f"{area_id}|{cutoff.isoformat()}"] = area
        if index % 50 == 0 or index == len(requested):
            print(json.dumps({"materialized_area_cutoffs": index, "total_area_cutoffs": len(requested)}), flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, dict[str, object]] = {}
    for source_payload, contract_id, filename in payloads:
        built = []
        for source in source_payload.get("samples", []):
            metadata = source.get("metadata") or {}
            key = f"{metadata.get('area_id')}|{metadata.get('cutoff_date')}"
            area_series = area_cache.get(key)
            if area_series is None:
                cutoff = date.fromisoformat(str(metadata["cutoff_date"]))
                area_series = {
                    "daily_dates": [
                        day.isoformat()
                        for day in weather_context.date_window(cutoff, raw_weather.LOOKBACK_DAYS)
                    ],
                    **{
                        series_key: [None] * raw_weather.LOOKBACK_DAYS
                        for series_key in raw_weather.AREA_SERIES_KEYS.values()
                    },
                }
            built.append(raw_weather.build_v5_sample(source, area_series, temporal_contract_id=contract_id))
        output = {
            "kind": "mushroom_biology_v5_raw_weather_benchmark",
            "schema_version": 1,
            "version_id": raw_weather.VERSION_ID,
            "feature_set": raw_weather.feature_set_contract(contract_id),
            "sample_count": len(built),
            "samples": built,
            "source": {
                "source_benchmark_sha256": sha256(args.v3_fixed if contract_id == raw_weather.FIXED_CONTRACT_ID else args.v3_lag),
                "known_sites_sha256": sha256(args.known_sites),
                "stations_sha256": sha256(args.stations_file),
                "weather_data_dir": str(args.data_dir),
                "loaded_weather_station_count": len(stations),
                "cache_start_date": earliest.isoformat(),
                "cache_end_date": latest.isoformat(),
                "cached_microarea_count": len(weather_cache),
            },
            "model_artifact_written": False,
            "operational_candidate_trained": False,
        }
        path = args.output_dir / filename
        path.write_text(json.dumps(output, ensure_ascii=False) + "\n", encoding="utf-8")
        outputs[filename] = {"sha256": sha256(path), "sample_count": len(built)}

    inventory = {
        "kind": "biology_v5_raw_channel_inventory",
        "included_raw_channels": list(raw_weather.RAW_CHANNELS),
        "included_canonical_daily_channels": list(raw_weather.DAILY_CHANNELS),
        "included_canonical_state_scalars": list(raw_weather.PHYSICAL_STATE_SCALARS),
        "excluded": {
            "daily_means": "deterministic duplicates of min/max channels",
            "wind": "no common V2/V3/V4 IDW contract with inference parity",
            "quality_and_provenance": "audit-only and forbidden from X",
        },
        "lookback_days": raw_weather.LOOKBACK_DAYS,
    }
    inventory_path = args.output_dir / "raw-channel-inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "kind": "mushroom_ml_v5_raw_discovery_build",
        "schema_version": 1,
        "source_snapshot": "docker-data/audits/mushroom-ml-snapshot-20260816",
        "source_snapshot_manifest_sha256": sha256(args.v3_fixed.parent / "MANIFEST.json"),
        "outputs": outputs,
        "raw_channel_inventory_sha256": sha256(inventory_path),
        "model_artifact_written": False,
        "operational_candidate_trained": False,
    }
    (args.output_dir / "MANIFEST.build.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output_dir": str(args.output_dir), "outputs": outputs}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
