"""Weather context reconstruction for mushroom observations.

This module is intentionally read-only for Rainmapper history and mushroom
observation files. It builds a v0 feature table under `mushroom-data` so
profile calibration work can inspect observed weather without changing species
profiles or observation records.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_observations, mushroom_paths


RAIN_WINDOWS_DAYS = (1, 7, 14, 21, 30, 60, 90)
TEMPERATURE_WINDOWS_DAYS = (7, 14, 21, 30)
HUMIDITY_WINDOWS_DAYS = (7, 14, 21, 30)
SUMMARY_WINDOW_DAYS = 7
# Data-quality guard only. Values above this are kept out of experimental
# weather sums and reported as gaps; this is not a mushroom predictor threshold.
DAILY_RAIN_SANITY_LIMIT_MM = 300.0
DAILY_INCREMENTAL_FILES = (
    ("aemet", "Aemet_incremental.csv"),
    ("meteocat", "Meteocat_incremental.csv"),
    ("meteoclimatic", "Meteoclimatic_incremental.csv"),
    ("wunderground", "Wunderground_incremental.csv"),
)
CSV_FIELDS = (
    "observation_id",
    "species_id",
    "observed_at",
    "analysis_result",
    "prediction_target",
    "flush_abundance",
    "month",
    "season",
    "validation_status",
    "calibration_use",
    "source_quality",
    "latitude",
    "longitude",
    "altitude_m",
    "weather_method",
    "weather_source",
    "weather_station_code",
    "weather_station_name",
    "weather_station_distance_km",
    "weather_station_coverage_days_90d",
    "weather_summary_window_days",
    "rain_1d_mm",
    "rain_7d_mm",
    "rain_14d_mm",
    "rain_21d_mm",
    "rain_30d_mm",
    "rain_60d_mm",
    "rain_90d_mm",
    "temp_min_7d_c",
    "temp_max_7d_c",
    "temp_mean_7d_c",
    "temp_min_14d_c",
    "temp_max_14d_c",
    "temp_mean_14d_c",
    "temp_min_21d_c",
    "temp_max_21d_c",
    "temp_mean_21d_c",
    "temp_min_30d_c",
    "temp_max_30d_c",
    "temp_mean_30d_c",
    "temp_min_c",
    "temp_max_c",
    "temp_mean_c",
    "humidity_min_7d_pct",
    "humidity_max_7d_pct",
    "humidity_mean_7d_pct",
    "humidity_min_14d_pct",
    "humidity_max_14d_pct",
    "humidity_mean_14d_pct",
    "humidity_min_21d_pct",
    "humidity_max_21d_pct",
    "humidity_mean_21d_pct",
    "humidity_min_30d_pct",
    "humidity_max_30d_pct",
    "humidity_mean_30d_pct",
    "humidity_min_pct",
    "humidity_max_pct",
    "humidity_mean_pct",
    "wind_avg_kmh",
    "wind_gust_kmh",
    "wind_direction_deg",
    "data_gaps",
    "observed_host_ids",
    "observed_forest_type_ids",
    "observed_soil_tendency_ids",
    "observed_habitat_feature_ids",
    "observed_aspect_ids",
)

PREDICTION_TARGET_POLICY_VERSION = "catalog_prediction_favorable_v1"


@dataclass(frozen=True)
class DailyWeatherRecord:
    source: str
    station_code: str
    station_name: str
    day: date
    lat: float
    lon: float
    rain_mm: float | None
    temp_max_c: float | None
    temp_min_c: float | None
    humidity_max_pct: float | None
    humidity_min_pct: float | None
    wind_avg_kmh: float | None
    wind_gust_kmh: float | None
    wind_direction_deg: float | None


@dataclass(frozen=True)
class WeatherStation:
    source: str
    station_code: str
    station_name: str
    lat: float
    lon: float
    records_by_day: dict[date, DailyWeatherRecord]


def repo_root() -> Path:
    return mushroom_paths.repo_root()


def default_weather_data_dir() -> Path:
    return mushroom_paths.weather_data_dir()


def default_observations_path() -> Path:
    return mushroom_paths.mushroom_observations_path()


def default_catalogs_path() -> Path:
    return mushroom_paths.mushroom_reference_catalogs_path()


def default_output_json_path() -> Path:
    return mushroom_paths.mushroom_weather_features_json_path()


def default_output_csv_path() -> Path:
    return mushroom_paths.mushroom_weather_features_csv_path()


def default_report_path() -> Path:
    return mushroom_paths.mushroom_weather_report_path()


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number):
        return None
    return number


def parse_day(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def date_window(end_day: date, days: int) -> set[date]:
    start = end_day - timedelta(days=days - 1)
    return {start + timedelta(days=offset) for offset in range(days)}


def haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius_km = 6371.0088
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    delta_phi = math.radians(lat_b - lat_a)
    delta_lambda = math.radians(lon_b - lon_a)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_km * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def normalized_record(source: str, row: dict[str, str]) -> DailyWeatherRecord | None:
    day = parse_day(row.get("Data Local") or row.get("local_date"))
    station_code = str(row.get("Codi Estació") or row.get("station_code") or "").strip()
    lat = parse_float(row.get("Latitud") or row.get("lat"))
    lon = parse_float(row.get("Longitud") or row.get("lon"))
    if day is None or not station_code or lat is None or lon is None:
        return None
    return DailyWeatherRecord(
        source=source,
        station_code=station_code,
        station_name=str(row.get("Estació") or row.get("station_name") or "").strip(),
        day=day,
        lat=lat,
        lon=lon,
        rain_mm=parse_float(row.get("Total") or row.get("rain_mm")),
        temp_max_c=parse_float(row.get("max_temp_celsius")),
        temp_min_c=parse_float(row.get("min_temp_celsius")),
        humidity_max_pct=parse_float(row.get("max_humidity_percent")),
        humidity_min_pct=parse_float(row.get("min_humidity_percent")),
        wind_avg_kmh=parse_float(row.get("wind_avg_kmh")),
        wind_gust_kmh=parse_float(row.get("wind_gust_kmh") or row.get("wind_max_kmh")),
        wind_direction_deg=parse_float(row.get("wind_direction_deg")),
    )


def emit_progress(progress_callback: Any | None, percent: float, message: str) -> None:
    """Report bounded progress without making callbacks mandatory for CLI callers."""
    if progress_callback:
        progress_callback(max(0, min(100, int(percent))), message)


def load_daily_weather_stations(
    data_dir: Path,
    progress_callback: Any | None = None,
) -> dict[tuple[str, str], WeatherStation]:
    records: dict[tuple[str, str], dict[date, DailyWeatherRecord]] = {}
    names: dict[tuple[str, str], str] = {}
    coordinates: dict[tuple[str, str], tuple[float, float]] = {}
    source_paths = [
        (source, data_dir / filename)
        for source, filename in DAILY_INCREMENTAL_FILES
        if (data_dir / filename).exists()
    ]
    total_bytes = sum(path.stat().st_size for _source, path in source_paths)
    completed_bytes = 0
    if not source_paths:
        emit_progress(progress_callback, 100, "No hay fuentes meteorologicas disponibles.")
    for source_index, (source, path) in enumerate(source_paths, start=1):
        file_size = path.stat().st_size
        rows_read = 0
        emit_progress(
            progress_callback,
            (completed_bytes / total_bytes) * 100 if total_bytes else 0,
            f"Leyendo fuente meteorologica {source_index}/{len(source_paths)}: {source}.",
        )
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                rows_read += 1
                record = normalized_record(source, row)
                if record is None:
                    pass
                else:
                    key = (record.source, record.station_code)
                    records.setdefault(key, {})[record.day] = record
                    names[key] = record.station_name
                    coordinates[key] = (record.lat, record.lon)
                if rows_read % 5000 == 0:
                    buffered_position = min(file_size, handle.buffer.tell())
                    emit_progress(
                        progress_callback,
                        ((completed_bytes + buffered_position) / total_bytes) * 100 if total_bytes else 100,
                        f"Leyendo {source}: {rows_read} registros.",
                    )
        completed_bytes += file_size
        emit_progress(
            progress_callback,
            (completed_bytes / total_bytes) * 100 if total_bytes else 100,
            f"Fuente {source} cargada: {rows_read} registros.",
        )
    stations = {}
    for key, station_records in records.items():
        lat, lon = coordinates[key]
        stations[key] = WeatherStation(
            source=key[0],
            station_code=key[1],
            station_name=names.get(key, ""),
            lat=lat,
            lon=lon,
            records_by_day=station_records,
        )
    return stations


def observation_location(observation: dict[str, Any]) -> tuple[float | None, float | None]:
    location = observation.get("location")
    if not isinstance(location, dict):
        return None, None
    return parse_float(location.get("lat")), parse_float(location.get("lon"))


def observation_altitude(observation: dict[str, Any]) -> float | None:
    altitude = observation.get("altitude")
    if not isinstance(altitude, dict):
        return None
    return parse_float(altitude.get("meters"))


def observed_host_ids(observation: dict[str, Any]) -> list[str]:
    return observed_site_context_ids(observation, "observed_host_ids")


def observed_site_context_ids(observation: dict[str, Any], key: str) -> list[str]:
    site_context = observation.get("site_context")
    if not isinstance(site_context, dict):
        return []
    values = site_context.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value or "").strip()]


def observation_derived(observation: dict[str, Any]) -> dict[str, Any]:
    derived = observation.get("derived")
    if not isinstance(derived, dict):
        return mushroom_observations.derived_fields_from_observed_at(observation.get("observed_at"))
    if "month" in derived and "season" in derived:
        return derived
    next_derived = dict(derived)
    next_derived.update(mushroom_observations.derived_fields_from_observed_at(observation.get("observed_at")))
    return next_derived


def analysis_result(flush_abundance: object) -> str:
    return "absent" if str(flush_abundance or "").strip() == "absent" else "present"


def load_prediction_target_policy(catalogs_path: Path | None = None) -> dict[str, object]:
    """Load and validate the operational target mapping from the reference catalog."""
    path = catalogs_path or default_catalogs_path()
    payload = json.loads(path.read_text(encoding="utf-8"))
    catalogs = payload.get("catalogs") if isinstance(payload, dict) else None
    entries = catalogs.get("observation_flush_abundance") if isinstance(catalogs, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{path}: catalogs.observation_flush_abundance must be a non-empty list")
    mapping: dict[str, int] = {}
    for index, entry in enumerate(entries):
        location = f"{path}: catalogs.observation_flush_abundance[{index}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{location} must be an object")
        abundance_id = str(entry.get("id", "") or "").strip()
        if not abundance_id:
            raise ValueError(f"{location}.id must be a non-empty string")
        if abundance_id in mapping:
            raise ValueError(f"{location}.id duplicates {abundance_id!r}")
        favorable = entry.get("prediction_favorable")
        if not isinstance(favorable, int) or isinstance(favorable, bool) or favorable not in {0, 1}:
            raise ValueError(f"{location}.prediction_favorable must be integer 0 or 1")
        mapping[abundance_id] = favorable
    serialized_mapping = json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "field": "prediction_target",
        "version": PREDICTION_TARGET_POLICY_VERSION,
        "source_field": "flush_abundance",
        "catalog_field": "prediction_favorable",
        "catalog_path": str(path),
        "mapping": mapping,
        "mapping_sha256": hashlib.sha256(serialized_mapping.encode("utf-8")).hexdigest(),
        "favorable": sorted(item_id for item_id, value in mapping.items() if value == 1),
        "unfavorable": sorted(item_id for item_id, value in mapping.items() if value == 0),
        "unknown": "Any missing or unrecognized flush_abundance value",
    }


def prediction_target(flush_abundance: object, policy: dict[str, object] | None = None) -> str:
    """Return the catalog-driven operational target for a flush abundance ID."""
    abundance = str(flush_abundance or "").strip()
    resolved_policy = policy or load_prediction_target_policy()
    mapping = resolved_policy.get("mapping") if isinstance(resolved_policy, dict) else None
    value = mapping.get(abundance) if isinstance(mapping, dict) else None
    if value == 1:
        return "favorable"
    if value == 0:
        return "unfavorable"
    return "unknown"


def prediction_target_policy(catalogs_path: Path | None = None) -> dict[str, object]:
    """Compatibility wrapper returning the validated catalog-driven policy."""
    return load_prediction_target_policy(catalogs_path)


def station_coverage_days(station: WeatherStation, observed_day: date, days: int = 90) -> int:
    return len(date_window(observed_day, days) & set(station.records_by_day))


def select_station(
    stations: dict[tuple[str, str], WeatherStation],
    lat: float,
    lon: float,
    observed_day: date,
) -> tuple[WeatherStation | None, float | None, int]:
    candidates = []
    for station in stations.values():
        coverage = station_coverage_days(station, observed_day, 90)
        if coverage <= 0:
            continue
        candidates.append((haversine_km(lat, lon, station.lat, station.lon), station.source, station.station_code, coverage, station))
    if not candidates:
        return None, None, 0
    distance, _source, _code, coverage, station = sorted(candidates, key=lambda item: (item[0], item[1], item[2]))[0]
    return station, distance, coverage


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def round_or_none(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None


def circular_mean_degrees(values: list[float]) -> float | None:
    if not values:
        return None
    sin_sum = sum(math.sin(math.radians(value)) for value in values)
    cos_sum = sum(math.cos(math.radians(value)) for value in values)
    if sin_sum == 0 and cos_sum == 0:
        return None
    angle = math.degrees(math.atan2(sin_sum / len(values), cos_sum / len(values)))
    return angle + 360 if angle < 0 else angle


def records_for_window(station: WeatherStation, observed_day: date, days: int) -> list[DailyWeatherRecord]:
    return [
        station.records_by_day[day]
        for day in sorted(date_window(observed_day, days))
        if day in station.records_by_day
    ]


def usable_rain_value(record: DailyWeatherRecord, gaps: list[str]) -> float | None:
    """Return daily rain unless it is a clear station-history anomaly."""
    value = record.rain_mm
    if value is None:
        return None
    if value > DAILY_RAIN_SANITY_LIMIT_MM:
        gap = f"rain_suspect_daily_{record.day.strftime('%Y%m%d')}_{round_or_none(value)}mm"
        if gap not in gaps:
            gaps.append(gap)
        return None
    return value


def build_weather_values(station: WeatherStation, observed_day: date) -> tuple[dict[str, Any], list[str]]:
    values: dict[str, Any] = {}
    gaps: list[str] = []
    for days in RAIN_WINDOWS_DAYS:
        records = records_for_window(station, observed_day, days)
        rain_values = [
            rain_value
            for record in records
            if (rain_value := usable_rain_value(record, gaps)) is not None
        ]
        values[f"rain_{days}d_mm"] = round_or_none(sum(rain_values), 2) if rain_values else None
        if len(rain_values) < days:
            gaps.append(f"rain_{days}d_coverage_{len(rain_values)}/{days}")

    for days in TEMPERATURE_WINDOWS_DAYS:
        records = records_for_window(station, observed_day, days)
        temp_min_values = [record.temp_min_c for record in records if record.temp_min_c is not None]
        temp_max_values = [record.temp_max_c for record in records if record.temp_max_c is not None]
        values[f"temp_min_{days}d_c"] = round_or_none(min(temp_min_values), 2) if temp_min_values else None
        values[f"temp_max_{days}d_c"] = round_or_none(max(temp_max_values), 2) if temp_max_values else None
        values[f"temp_mean_{days}d_c"] = round_or_none(mean(temp_min_values + temp_max_values), 2)
        if not temp_min_values and not temp_max_values:
            gaps.append(f"temperature_no_data_{days}d")

    for days in HUMIDITY_WINDOWS_DAYS:
        records = records_for_window(station, observed_day, days)
        humidity_min_values = [record.humidity_min_pct for record in records if record.humidity_min_pct is not None]
        humidity_max_values = [record.humidity_max_pct for record in records if record.humidity_max_pct is not None]
        values[f"humidity_min_{days}d_pct"] = round_or_none(min(humidity_min_values), 2) if humidity_min_values else None
        values[f"humidity_max_{days}d_pct"] = round_or_none(max(humidity_max_values), 2) if humidity_max_values else None
        values[f"humidity_mean_{days}d_pct"] = round_or_none(mean(humidity_min_values + humidity_max_values), 2)
        if not humidity_min_values and not humidity_max_values:
            gaps.append(f"humidity_no_data_{days}d")

    summary_records = records_for_window(station, observed_day, SUMMARY_WINDOW_DAYS)
    temp_min_values = [record.temp_min_c for record in summary_records if record.temp_min_c is not None]
    temp_max_values = [record.temp_max_c for record in summary_records if record.temp_max_c is not None]
    humidity_min_values = [record.humidity_min_pct for record in summary_records if record.humidity_min_pct is not None]
    humidity_max_values = [record.humidity_max_pct for record in summary_records if record.humidity_max_pct is not None]
    wind_avg_values = [record.wind_avg_kmh for record in summary_records if record.wind_avg_kmh is not None]
    wind_gust_values = [record.wind_gust_kmh for record in summary_records if record.wind_gust_kmh is not None]
    wind_direction_values = [record.wind_direction_deg for record in summary_records if record.wind_direction_deg is not None]

    values.update(
        {
            "temp_min_c": round_or_none(min(temp_min_values), 2) if temp_min_values else None,
            "temp_max_c": round_or_none(max(temp_max_values), 2) if temp_max_values else None,
            "temp_mean_c": round_or_none(mean(temp_min_values + temp_max_values), 2),
            "humidity_min_pct": round_or_none(min(humidity_min_values), 2) if humidity_min_values else None,
            "humidity_max_pct": round_or_none(max(humidity_max_values), 2) if humidity_max_values else None,
            "humidity_mean_pct": round_or_none(mean(humidity_min_values + humidity_max_values), 2),
            "wind_avg_kmh": round_or_none(mean(wind_avg_values), 2),
            "wind_gust_kmh": round_or_none(max(wind_gust_values), 2) if wind_gust_values else None,
            "wind_direction_deg": round_or_none(circular_mean_degrees(wind_direction_values), 1),
        }
    )
    if not wind_avg_values and not wind_gust_values:
        gaps.append("wind_no_data_7d")
    return values, gaps


def build_observation_weather_row(
    observation: dict[str, Any],
    stations: dict[tuple[str, str], WeatherStation],
    prediction_policy: dict[str, object] | None = None,
) -> dict[str, Any]:
    observed_day = parse_day(observation.get("observed_at"))
    lat, lon = observation_location(observation)
    flush_abundance = str(observation.get("flush_abundance", "") or "")
    derived = observation_derived(observation)
    row: dict[str, Any] = {
        "observation_id": str(observation.get("observation_id", "") or ""),
        "species_id": str(observation.get("species_id", "") or ""),
        "observed_at": str(observation.get("observed_at", "") or ""),
        "analysis_result": analysis_result(flush_abundance),
        "prediction_target": prediction_target(flush_abundance, prediction_policy),
        "flush_abundance": flush_abundance,
        "month": derived.get("month"),
        "season": derived.get("season"),
        "validation_status": str(observation.get("validation_status", "") or ""),
        "calibration_use": str(observation.get("calibration_use", "") or ""),
        "source_quality": observation.get("source_quality"),
        "latitude": lat,
        "longitude": lon,
        "altitude_m": observation_altitude(observation),
        "weather_method": "nearest_station_single_source_daily",
        "weather_source": "",
        "weather_station_code": "",
        "weather_station_name": "",
        "weather_station_distance_km": None,
        "weather_station_coverage_days_90d": 0,
        "weather_summary_window_days": SUMMARY_WINDOW_DAYS,
        "observed_host_ids": observed_host_ids(observation),
        "observed_forest_type_ids": observed_site_context_ids(observation, "observed_forest_type_ids"),
        "observed_soil_tendency_ids": observed_site_context_ids(observation, "observed_soil_tendency_ids"),
        "observed_habitat_feature_ids": observed_site_context_ids(observation, "observed_habitat_feature_ids"),
        "observed_aspect_ids": observed_site_context_ids(observation, "observed_aspect_ids"),
    }
    gaps: list[str] = []
    for days in RAIN_WINDOWS_DAYS:
        row[f"rain_{days}d_mm"] = None
    for days in TEMPERATURE_WINDOWS_DAYS:
        row[f"temp_min_{days}d_c"] = None
        row[f"temp_max_{days}d_c"] = None
        row[f"temp_mean_{days}d_c"] = None
    for days in HUMIDITY_WINDOWS_DAYS:
        row[f"humidity_min_{days}d_pct"] = None
        row[f"humidity_max_{days}d_pct"] = None
        row[f"humidity_mean_{days}d_pct"] = None
    for key in (
        "temp_min_c",
        "temp_max_c",
        "temp_mean_c",
        "humidity_min_pct",
        "humidity_max_pct",
        "humidity_mean_pct",
        "wind_avg_kmh",
        "wind_gust_kmh",
        "wind_direction_deg",
    ):
        row[key] = None

    if observed_day is None:
        gaps.append("invalid_observed_at")
    if lat is None or lon is None:
        gaps.append("missing_coordinates")
    if observed_day is None or lat is None or lon is None:
        row["data_gaps"] = gaps
        return row

    station, distance_km, coverage = select_station(stations, lat, lon, observed_day)
    if station is None:
        gaps.append("no_weather_station_with_90d_coverage")
        row["data_gaps"] = gaps
        return row

    weather_values, weather_gaps = build_weather_values(station, observed_day)
    row.update(weather_values)
    row.update(
        {
            "weather_source": station.source,
            "weather_station_code": station.station_code,
            "weather_station_name": station.station_name,
            "weather_station_distance_km": round_or_none(distance_km, 2),
            "weather_station_coverage_days_90d": coverage,
            "data_gaps": gaps + weather_gaps,
        }
    )
    return row


def load_observations(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ValueError(f"{path} must contain an observations list")
    return [item for item in observations if isinstance(item, dict)]


def json_safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in CSV_FIELDS}


def csv_value(value: object) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in CSV_FIELDS})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def report_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    gap_rows = [row for row in rows if isinstance(row, dict) and row.get("data_gaps")]
    lines = [
        "# Mushroom Observation Weather Features",
        "",
        f"- Generated at: {payload.get('generated_at', '-')}",
        f"- Observations: {summary.get('observations', 0)}",
        f"- With weather station: {summary.get('with_weather_station', 0)}",
        f"- With gaps: {summary.get('with_gaps', 0)}",
        f"- Method: {payload.get('weather_method', '-')}",
        f"- Summary window: {SUMMARY_WINDOW_DAYS} days for temperature, humidity and wind.",
        "",
        "## Gap Summary",
        "",
    ]
    gap_counts: dict[str, int] = {}
    for row in gap_rows:
        for gap in row.get("data_gaps", []):
            gap_counts[str(gap)] = gap_counts.get(str(gap), 0) + 1
    if gap_counts:
        for gap, count in sorted(gap_counts.items()):
            lines.append(f"- {gap}: {count}")
    else:
        lines.append("- No gaps reported.")
    lines.extend(["", "## Rows With Gaps", ""])
    for row in gap_rows[:50]:
        lines.append(
            "- {observation_id} · {species_id} · {observed_at}: {gaps}".format(
                observation_id=row.get("observation_id", "-"),
                species_id=row.get("species_id", "-"),
                observed_at=row.get("observed_at", "-"),
                gaps=", ".join(str(gap) for gap in row.get("data_gaps", [])),
            )
        )
    if len(gap_rows) > 50:
        lines.append(f"- ... {len(gap_rows) - 50} additional rows omitted.")
    return "\n".join(lines) + "\n"


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_markdown(payload), encoding="utf-8")


def build_observation_weather_features(
    observations_path: Path | None = None,
    weather_data_dir: Path | None = None,
    catalogs_path: Path | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    observations_path = observations_path or default_observations_path()
    weather_data_dir = weather_data_dir or default_weather_data_dir()
    emit_progress(progress_callback, 1, "Cargando observaciones.")
    observations = load_observations(observations_path)
    emit_progress(progress_callback, 4, f"Cargadas {len(observations)} observaciones.")
    stations = load_daily_weather_stations(
        weather_data_dir,
        progress_callback=lambda percent, message: emit_progress(
            progress_callback,
            5 + percent * 0.35,
            message,
        ),
    )
    emit_progress(progress_callback, 41, "Cargando politica de prediccion del catalogo.")
    prediction_policy = load_prediction_target_policy(catalogs_path)
    rows = []
    observation_total = len(observations)
    if not observations:
        emit_progress(progress_callback, 90, "No hay observaciones meteorologicas que procesar.")
    for index, observation in enumerate(observations, start=1):
        rows.append(json_safe_row(build_observation_weather_row(observation, stations, prediction_policy)))
        emit_progress(
            progress_callback,
            42 + (index / observation_total) * 48,
            f"Calculando meteorologia {index}/{observation_total} observaciones.",
        )
    emit_progress(progress_callback, 94, "Calculando resumen meteorologico.")
    with_station = sum(1 for row in rows if row.get("weather_station_code"))
    with_gaps = sum(1 for row in rows if row.get("data_gaps"))
    emit_progress(progress_callback, 100, "Contexto meteorologico calculado.")
    return {
        "schema_version": "0.2",
        "kind": "mushroom_observation_weather_features",
        "generated_at": datetime.now(UTC).isoformat(),
        "prediction_target_policy": prediction_policy,
        "weather_method": "nearest_station_single_source_daily",
        "weather_summary_window_days": SUMMARY_WINDOW_DAYS,
        "rain_windows_days": list(RAIN_WINDOWS_DAYS),
        "input_paths": {
            "observations": str(observations_path),
            "weather_data_dir": str(weather_data_dir),
            "reference_catalogs": str(catalogs_path or default_catalogs_path()),
        },
        "source_files": [
            {"source": source, "path": str(weather_data_dir / filename), "exists": (weather_data_dir / filename).exists()}
            for source, filename in DAILY_INCREMENTAL_FILES
        ],
        "summary": {
            "observations": len(rows),
            "weather_stations_loaded": len(stations),
            "with_weather_station": with_station,
            "with_gaps": with_gaps,
        },
        "rows": rows,
    }


def build_and_write_observation_weather_features(
    observations_path: Path | None = None,
    weather_data_dir: Path | None = None,
    catalogs_path: Path | None = None,
    output_json_path: Path | None = None,
    output_csv_path: Path | None = None,
    report_path: Path | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    payload = build_observation_weather_features(
        observations_path,
        weather_data_dir,
        catalogs_path,
        progress_callback=lambda percent, message: emit_progress(
            progress_callback,
            percent * 0.85,
            message,
        ),
    )
    output_json_path = output_json_path or default_output_json_path()
    output_csv_path = output_csv_path or default_output_csv_path()
    report_path = report_path or default_report_path()
    payload["output_paths"] = {
        "json": str(output_json_path),
        "csv": str(output_csv_path),
        "report": str(report_path),
    }
    emit_progress(progress_callback, 87, "Escribiendo meteorologia JSON.")
    write_json(output_json_path, payload)
    emit_progress(progress_callback, 91, "Escribiendo meteorologia CSV.")
    write_csv(output_csv_path, payload["rows"])
    emit_progress(progress_callback, 97, "Escribiendo informe meteorologico.")
    write_report(report_path, payload)
    emit_progress(progress_callback, 100, "Meteorologia guardada.")
    return payload
