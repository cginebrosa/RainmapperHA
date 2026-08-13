#!/usr/bin/env python3
"""Read-only Biology V3 IDW smoke test over a bounded weather snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--stations-file", type=Path, required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--days", type=int, default=7)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog = weather_context.load_stations_catalog(args.data_dir)
    station_filter = set(
        weather_context.nearest_station_codes(
            catalog,
            args.lat,
            args.lon,
            max_km=mushroom_weather_idw.RAINFALL_IDW_RADIUS_KM,
            top_n=len(catalog),
        )
    )
    stations = weather_context.load_daily_weather_parquet(
        args.data_dir,
        station_filter=station_filter,
        start_date=args.end_date - timedelta(days=args.days),
        end_date=args.end_date,
    )
    excluded = mushroom_weather_idw.disabled_wunderground_station_keys(args.stations_file)
    series = mushroom_weather_idw.build_daily_rain_idw_series(
        stations,
        target_lat=args.lat,
        target_lon=args.lon,
        end_day=args.end_date,
        days=args.days,
        excluded_station_keys=excluded,
    )
    rows = [
        {
            "date": day,
            "rain_idw_mm": value,
            "stations": count,
        }
        for day, value, count in zip(
            series["daily_dates"],
            series["daily_rain_idw_mm"],
            series["daily_rain_station_count"],
        )
    ]
    payload = {
        "contract": mushroom_weather_idw.rainfall_idw_contract_metadata(),
        "catalog_stations": len(catalog),
        "stations_within_radius": len(station_filter),
        "loaded_stations": len(stations),
        "disabled_wunderground_stations": len(excluded),
        "days": rows,
        "observed_days": series["rain_observed_days"],
        "rain_sum_of_daily_idw_mm": sum(
            value for value in series["daily_rain_idw_mm"] if value is not None
        ),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
