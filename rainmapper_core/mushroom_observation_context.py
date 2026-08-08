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
from uuid import uuid4

import pandas as pd

from rainmapper_core import mushroom_observations, mushroom_paths


RAIN_WINDOWS_DAYS = (1, 7, 14, 21, 30)
TEMPERATURE_WINDOWS_DAYS = (7, 14, 21, 30)
HUMIDITY_WINDOWS_DAYS = (7, 14, 21, 30)
SUMMARY_WINDOW_DAYS = 7
DAILY_SERIES_DAYS = 30
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
    "micro_area_id",
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
    "dry_spell_days",
    "days_since_significant_rain",
    "rainy_days_14d",
    "thermal_amplitude_mean_7d",
    "thermal_amplitude_mean_14d",
    "thermal_trend",
    "heat_stress_days",
    "high_humidity_days_14d",
    "data_gaps",
    "observed_host_ids",
    "observed_forest_type_ids",
    "observed_soil_tendency_ids",
    "observed_habitat_feature_ids",
    "observed_aspect_ids",
)

PREDICTION_TARGET_POLICY_VERSION = "catalog_prediction_favorable_v1"

JSON_EXTRA_FIELDS = (
    "daily_rain_mm",
    "daily_temp_min_c",
    "daily_temp_max_c",
    "daily_temp_mean_c",
    "daily_humidity_min_pct",
    "daily_humidity_max_pct",
    "daily_humidity_mean_pct",
)


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


def _nan_to_none(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


_PARQUET_FILENAME = "weather_daily.parquet"
_CATALOG_FILENAME = "weather_stations_catalog.parquet"
_PARQUET_ROW_GROUP_SIZE = 512


class WeatherParquetLayoutError(RuntimeError):
    """Raised when filtered reads would scan a legacy monolithic Parquet."""

_PARQUET_COL_MAP = {
    "Codi Estació": "station_code",
    "Estació": "station_name",
    "Data Local": "local_date",
    "Latitud": "lat",
    "Longitud": "lon",
    "Altitud": "altitude",
    "Total": "rain_mm",
    "max_temp_celsius": "max_temp_celsius",
    "min_temp_celsius": "min_temp_celsius",
    "max_humidity_percent": "max_humidity_percent",
    "min_humidity_percent": "min_humidity_percent",
    "wind_avg_kmh": "wind_avg_kmh",
    "wind_gust_kmh": "wind_gust_kmh",
}

_PARQUET_FLOAT_COLS = (
    "lat", "lon", "altitude", "rain_mm",
    "max_temp_celsius", "min_temp_celsius",
    "max_humidity_percent", "min_humidity_percent",
    "wind_avg_kmh", "wind_gust_kmh",
)


def generate_weather_daily_parquet(
    data_dir: Path,
    progress_callback: Any | None = None,
) -> Path | None:
    """Read all incremental CSV sources and write a combined weather_daily.parquet.

    The Parquet is a read-optimised artefact (~15-20 MB vs ~116 MB of raw CSVs).
    It is regenerated from scratch on every runner call; the CSVs remain the
    source of truth. Returns the output path on success, None if no sources exist.
    """
    source_paths = [
        (source, data_dir / filename)
        for source, filename in DAILY_INCREMENTAL_FILES
        if (data_dir / filename).exists()
    ]
    if not source_paths:
        emit_progress(progress_callback, 100, "No hay fuentes meteorologicas disponibles.")
        return None

    dfs = []
    n = len(source_paths)
    for i, (source, path) in enumerate(source_paths, start=1):
        emit_progress(
            progress_callback,
            int((i - 1) / n * 80),
            f"Leyendo {source} para Parquet ({i}/{n})...",
        )
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False, dtype=str)
        available = {col: new for col, new in _PARQUET_COL_MAP.items() if col in df.columns}
        df = df[list(available.keys())].copy()
        df.rename(columns=available, inplace=True)
        for col in _PARQUET_FLOAT_COLS:
            if col in df.columns:
                df[col] = df[col].apply(lambda v: parse_float(v) if pd.notna(v) else None)
        df["source"] = source
        df.sort_values(
            ["station_code", "local_date"],
            kind="stable",
            ignore_index=True,
            inplace=True,
        )
        dfs.append(df)

    emit_progress(progress_callback, 85, "Combinando fuentes y escribiendo Parquet...")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        combined = pd.concat(dfs, ignore_index=True)
    combined = combined.dropna(subset=["station_code", "local_date"])
    output_path = data_dir / _PARQUET_FILENAME
    temporary_path = output_path.with_name(
        f".{output_path.name}.{uuid4().hex}.tmp"
    )
    try:
        combined.to_parquet(
            temporary_path,
            index=False,
            row_group_size=_PARQUET_ROW_GROUP_SIZE,
        )
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    emit_progress(
        progress_callback, 100,
        f"{_PARQUET_FILENAME} generado: {len(combined)} filas, {output_path.stat().st_size // 1024} KB.",
    )
    return output_path


def generate_stations_catalog_parquet(data_dir: Path) -> Path | None:
    """Extract one row per station from weather_daily.parquet and write weather_stations_catalog.parquet.

    The catalog contains only coordinate/metadata columns (~100 KB). It is generated
    immediately after weather_daily.parquet so the predictor can filter the daily parquet
    to relevant stations without loading all rows into Python objects.
    Returns the catalog path on success, None if the daily parquet does not exist.
    """
    parquet_path = data_dir / _PARQUET_FILENAME
    if not parquet_path.exists():
        return None
    import pyarrow.parquet as pq  # noqa: PLC0415

    columns = ["source", "station_code", "station_name", "lat", "lon", "altitude"]
    rows_by_station: dict[tuple[str, str], dict[str, Any]] = {}
    parquet_file = pq.ParquetFile(parquet_path)
    for batch in parquet_file.iter_batches(batch_size=16_384, columns=columns):
        values = batch.to_pydict()
        for source, station_code, station_name, lat, lon, altitude in zip(
            *(values[column] for column in columns)
        ):
            source_text = str(source or "").strip()
            station_code_text = str(station_code or "").strip()
            if not source_text or not station_code_text or lat is None or lon is None:
                continue
            try:
                lat_value = float(lat)
                lon_value = float(lon)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(lat_value) or not math.isfinite(lon_value):
                continue
            altitude_value = _nan_to_none(altitude)
            key = (source_text, station_code_text)
            if key not in rows_by_station:
                rows_by_station[key] = {
                    "source": source_text,
                    "station_code": station_code_text,
                    "station_name": str(station_name or "").strip(),
                    "lat": lat_value,
                    "lon": lon_value,
                    "altitude": altitude_value,
                }
    df = pd.DataFrame(rows_by_station.values(), columns=columns)
    catalog_path = data_dir / _CATALOG_FILENAME
    temporary_path = catalog_path.with_name(
        f".{catalog_path.name}.{uuid4().hex}.tmp"
    )
    try:
        df.to_parquet(temporary_path, index=False)
        temporary_path.replace(catalog_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return catalog_path


def load_stations_catalog(data_dir: Path) -> "pd.DataFrame":
    """Load weather_stations_catalog.parquet as a DataFrame (source, station_code, lat, lon, altitude).

    Creates or refreshes the lightweight catalog from weather_daily.parquet when
    necessary. Returns an empty DataFrame only when neither artifact is available.
    """
    catalog_path = data_dir / _CATALOG_FILENAME
    parquet_path = data_dir / _PARQUET_FILENAME
    catalog_stale = (
        parquet_path.exists()
        and (
            not catalog_path.exists()
            or parquet_path.stat().st_mtime > catalog_path.stat().st_mtime
        )
    )
    if catalog_stale:
        generate_stations_catalog_parquet(data_dir)
    if not catalog_path.exists():
        return pd.DataFrame(columns=["source", "station_code", "station_name", "lat", "lon", "altitude"])
    return pd.read_parquet(catalog_path)


def nearest_station_codes(
    catalog: "pd.DataFrame",
    lat: float,
    lon: float,
    max_km: float = 15.0,
    top_n: int = 5,
) -> list[tuple[str, str]]:
    """Return up to top_n (source, station_code) pairs within max_km of (lat, lon), sorted by distance."""
    if catalog.empty:
        return []
    distances = catalog.apply(
        lambda row: haversine_km(lat, lon, float(row["lat"]), float(row["lon"])),
        axis=1,
    )
    nearby = catalog[distances <= max_km].copy()
    nearby["_dist"] = distances[nearby.index]
    nearby = nearby.sort_values("_dist").head(top_n)
    return [(str(row["source"]), str(row["station_code"])) for _, row in nearby.iterrows()]


def load_daily_weather_parquet(
    data_dir: Path,
    progress_callback: Any | None = None,
    station_filter: set[tuple[str, str]] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[tuple[str, str], WeatherStation]:
    """Load weather stations from Parquet, optionally with read-time filtering.

    ``station_filter=None`` means that the caller explicitly needs every
    station (the rebuild pipeline). An empty set means that no station is safe
    to load and returns an empty result without reading the weather history.
    ``start_date`` and ``end_date`` are inclusive and limit only Predictor
    reads; the rebuild path continues to load the complete history.
    """
    if (start_date is None) != (end_date is None):
        raise ValueError("start_date and end_date must be provided together")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must not be after end_date")
    parquet_path = data_dir / _PARQUET_FILENAME
    if not parquet_path.exists():
        if station_filter is not None:
            return {}
        return _load_daily_weather_from_csv(data_dir, progress_callback)

    emit_progress(progress_callback, 5, "Leyendo weather_daily.parquet...")
    if station_filter is not None:
        normalized_filter = {
            (str(source).strip(), str(station_code).strip())
            for source, station_code in station_filter
            if str(source).strip() and str(station_code).strip()
        }
        if not normalized_filter:
            emit_progress(progress_callback, 100, "No hay estaciones meteorologicas seleccionadas.")
            return {}
        import pyarrow.parquet as pq  # noqa: PLC0415

        metadata = pq.ParquetFile(parquet_path).metadata
        if metadata.num_row_groups == 1 and metadata.num_rows > _PARQUET_ROW_GROUP_SIZE:
            raise WeatherParquetLayoutError(
                "weather_daily.parquet must be regenerated by the current runner "
                "before using filtered Predictor reads"
            )
        date_filters = (
            [
                ("local_date", ">=", start_date.strftime("%Y%m%d")),
                ("local_date", "<=", end_date.strftime("%Y%m%d")),
            ]
            if start_date is not None and end_date is not None
            else []
        )
        parquet_filters = [
            [
                ("source", "==", source),
                ("station_code", "==", station_code),
                *date_filters,
            ]
            for source, station_code in sorted(normalized_filter)
        ]
        df = pd.read_parquet(parquet_path, filters=parquet_filters)
    else:
        df = pd.read_parquet(parquet_path)
    emit_progress(progress_callback, 30, f"Parquet cargado: {len(df)} registros.")

    # Vectorized filtering — drop rows missing required fields before any Python loop
    df = df.copy()
    df["source"] = df["source"].fillna("").str.strip()
    df["station_code"] = df["station_code"].fillna("").str.strip()
    df = df[(df["source"] != "") & (df["station_code"] != "")]
    df = df.dropna(subset=["lat", "lon"])

    # Vectorized date parsing — avoids 600k+ per-row strptime calls
    raw_dates = df["local_date"].astype(str)
    days_dt = pd.to_datetime(raw_dates, format="%Y%m%d", errors="coerce")
    needs_fallback = days_dt.isna()
    if needs_fallback.any():
        days_dt = days_dt.copy()
        days_dt.loc[needs_fallback] = pd.to_datetime(
            raw_dates.loc[needs_fallback], format="%Y-%m-%d", errors="coerce"
        )
    df["_day"] = days_dt
    df = df.dropna(subset=["_day"])

    # Ensure float columns are numeric (parquet may carry object dtype on re-read)
    for col in ["lat", "lon", "rain_mm", "max_temp_celsius", "min_temp_celsius",
                "max_humidity_percent", "min_humidity_percent", "wind_avg_kmh", "wind_gust_kmh"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    emit_progress(progress_callback, 60, "Construyendo indice de estaciones...")

    def _col_list(grp: Any, name: str) -> list:
        return grp[name].tolist() if name in grp.columns else [None] * len(grp)

    def _f(v: Any) -> float | None:
        if v is None:
            return None
        try:
            f = float(v)
            return None if math.isnan(f) else f
        except (TypeError, ValueError):
            return None

    stations: dict[tuple[str, str], WeatherStation] = {}
    for (source, station_code), grp in df.groupby(["source", "station_code"], sort=False):
        lat_s = grp["lat"].iloc[0]
        lon_s = grp["lon"].iloc[0]
        if pd.isna(lat_s) or pd.isna(lon_s):
            continue
        lat_f = float(lat_s)
        lon_f = float(lon_s)

        # Convert whole columns to Python lists once per station (C-level, fast)
        day_dates = grp["_day"].dt.date.tolist()
        names     = grp["station_name"].fillna("").str.strip().tolist()
        rain      = _col_list(grp, "rain_mm")
        t_max     = _col_list(grp, "max_temp_celsius")
        t_min     = _col_list(grp, "min_temp_celsius")
        h_max     = _col_list(grp, "max_humidity_percent")
        h_min     = _col_list(grp, "min_humidity_percent")
        w_avg     = _col_list(grp, "wind_avg_kmh")
        w_gst     = _col_list(grp, "wind_gust_kmh")

        records_by_day = {
            day_dates[i]: DailyWeatherRecord(
                source=source,
                station_code=station_code,
                station_name=names[i],
                day=day_dates[i],
                lat=lat_f,
                lon=lon_f,
                rain_mm=_f(rain[i]),
                temp_max_c=_f(t_max[i]),
                temp_min_c=_f(t_min[i]),
                humidity_max_pct=_f(h_max[i]),
                humidity_min_pct=_f(h_min[i]),
                wind_avg_kmh=_f(w_avg[i]),
                wind_gust_kmh=_f(w_gst[i]),
                wind_direction_deg=None,
            )
            for i in range(len(grp))
        }
        stations[(source, station_code)] = WeatherStation(
            source=source,
            station_code=station_code,
            station_name=names[0] if names else "",
            lat=lat_f,
            lon=lon_f,
            records_by_day=records_by_day,
        )

    emit_progress(progress_callback, 100, f"Estaciones cargadas desde Parquet: {len(stations)}.")
    return stations


def _load_daily_weather_from_csv(
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
    """Choose the best-covered of the five nearest weather stations.

    Coverage quality is measured over the model's existing 30-day feature
    window, so selection does not introduce a new numeric threshold. Distance
    breaks coverage ties. The returned coverage remains the established 90-day
    reporting value used by observation artifacts.
    """
    candidates = []
    for station in stations.values():
        distance = haversine_km(lat, lon, station.lat, station.lon)
        candidates.append((distance, station.source, station.station_code, station))
    nearest_candidates = sorted(
        candidates,
        key=lambda item: (item[0], item[1], item[2]),
    )[:5]
    covered_candidates = []
    for distance, source, station_code, station in nearest_candidates:
        feature_coverage = station_coverage_days(
            station,
            observed_day,
            DAILY_SERIES_DAYS,
        )
        if feature_coverage > 0:
            covered_candidates.append(
                (feature_coverage, distance, source, station_code, station)
            )
    if not covered_candidates:
        return None, None, 0
    _feature_coverage, distance, _source, _code, station = sorted(
        covered_candidates,
        key=lambda item: (-item[0], item[1], item[2], item[3]),
    )[0]
    reporting_coverage = station_coverage_days(station, observed_day, 90)
    return station, distance, reporting_coverage


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


def _consecutive_duplicate_rain_dates(sorted_records: list[DailyWeatherRecord]) -> set[date]:
    """Return dates that repeat the previous calendar day's rain value (value > 0, exact match).

    Wunderground stations sometimes carry forward the last known value when the sensor
    stops reporting. Two or more consecutive days with exactly the same non-zero rain reading
    are almost certainly an artifact, not real weather. Keep the first occurrence; nullify the rest.
    Only applied to truly adjacent calendar days — a gap in the series resets the check.
    """
    duplicate_dates: set[date] = set()
    for i in range(1, len(sorted_records)):
        prev = sorted_records[i - 1]
        curr = sorted_records[i]
        if (
            curr.day == prev.day + timedelta(days=1)
            and prev.rain_mm is not None
            and curr.rain_mm is not None
            and curr.rain_mm > 0
            and curr.rain_mm == prev.rain_mm
        ):
            duplicate_dates.add(curr.day)
    return duplicate_dates


def build_derived_features(
    station: WeatherStation,
    observed_day: date,
    duplicate_dates: set | None = None,
) -> dict[str, Any]:
    """Compute 8 derived scalar features from the 30-day daily series."""
    recs = station.records_by_day
    dup = duplicate_dates or set()

    def rain_of(d: date) -> float | None:
        """Effective rain for a day: None if missing or a consecutive duplicate artifact."""
        if d in dup or d not in recs:
            return None
        return recs[d].rain_mm

    derived: dict[str, Any] = {
        "dry_spell_days": None,
        "days_since_significant_rain": None,
        "rainy_days_14d": None,
        "thermal_amplitude_mean_7d": None,
        "thermal_amplitude_mean_14d": None,
        "thermal_trend": None,
        "heat_stress_days": None,
        "high_humidity_days_14d": None,
    }

    # dry_spell_days: consecutive days without rain immediately before observed_day
    dry_spell = 0
    for delta in range(1, DAILY_SERIES_DAYS + 1):
        check_day = observed_day - timedelta(days=delta)
        v = rain_of(check_day)
        if v is None:
            break
        if v > 0:
            break
        dry_spell += 1
    derived["dry_spell_days"] = dry_spell

    # days_since_significant_rain: days since last rain >= 5mm
    for delta in range(1, DAILY_SERIES_DAYS + 1):
        check_day = observed_day - timedelta(days=delta)
        v = rain_of(check_day)
        if v is not None and v >= 5.0:
            derived["days_since_significant_rain"] = delta
            break

    # rainy_days_14d: count of days with rain > 2mm in last 14 days
    window_14d = date_window(observed_day, 14)
    rain_14d = [v for d in window_14d if (v := rain_of(d)) is not None]
    if rain_14d:
        derived["rainy_days_14d"] = sum(1 for v in rain_14d if v > 2.0)

    # thermal_amplitude_mean_7d and _14d
    for amp_days in (7, 14):
        window = date_window(observed_day, amp_days)
        amplitudes = [
            recs[d].temp_max_c - recs[d].temp_min_c
            for d in window
            if d in recs and recs[d].temp_max_c is not None and recs[d].temp_min_c is not None
        ]
        derived[f"thermal_amplitude_mean_{amp_days}d"] = round_or_none(mean(amplitudes), 2) if amplitudes else None

    # thermal_trend: temp_mean_7d minus temp_mean of days 8-30
    def day_tmean(d: date) -> float | None:
        rec = recs.get(d)
        if rec and rec.temp_max_c is not None and rec.temp_min_c is not None:
            return (rec.temp_max_c + rec.temp_min_c) / 2.0
        return None

    recent_temps = [t for d in date_window(observed_day, 7) if (t := day_tmean(d)) is not None]
    older_temps = [
        t
        for delta in range(8, DAILY_SERIES_DAYS + 1)
        if (t := day_tmean(observed_day - timedelta(days=delta))) is not None
    ]
    if recent_temps and older_temps:
        derived["thermal_trend"] = round_or_none(mean(recent_temps) - mean(older_temps), 2)

    # heat_stress_days: consecutive days with temp_max > 28°C immediately before observed_day
    heat_days = 0
    for delta in range(1, DAILY_SERIES_DAYS + 1):
        check_day = observed_day - timedelta(days=delta)
        if check_day not in recs or recs[check_day].temp_max_c is None:
            break
        if recs[check_day].temp_max_c > 28.0:
            heat_days += 1
        else:
            break
    derived["heat_stress_days"] = heat_days

    # high_humidity_days_14d: days with humidity_mean > 80% in last 14 days
    hum_14d = [
        (recs[d].humidity_min_pct + recs[d].humidity_max_pct) / 2.0
        for d in window_14d
        if d in recs and recs[d].humidity_min_pct is not None and recs[d].humidity_max_pct is not None
    ]
    if hum_14d:
        derived["high_humidity_days_14d"] = sum(1 for v in hum_14d if v > 80.0)

    return derived


def build_daily_series(
    station: WeatherStation,
    observed_day: date,
    duplicate_dates: set | None = None,
) -> dict[str, list]:
    """Build daily series arrays for the last DAILY_SERIES_DAYS days (oldest first)."""
    dup = duplicate_dates or set()
    days = sorted(date_window(observed_day, DAILY_SERIES_DAYS))
    recs = station.records_by_day
    daily: dict[str, list] = {k: [] for k in JSON_EXTRA_FIELDS}
    for d in days:
        rec = recs.get(d)
        daily["daily_rain_mm"].append(rec.rain_mm if (rec and d not in dup) else None)
        daily["daily_temp_min_c"].append(rec.temp_min_c if rec else None)
        daily["daily_temp_max_c"].append(rec.temp_max_c if rec else None)
        if rec and rec.temp_min_c is not None and rec.temp_max_c is not None:
            daily["daily_temp_mean_c"].append(round((rec.temp_min_c + rec.temp_max_c) / 2.0, 2))
        else:
            daily["daily_temp_mean_c"].append(None)
        daily["daily_humidity_min_pct"].append(rec.humidity_min_pct if rec else None)
        daily["daily_humidity_max_pct"].append(rec.humidity_max_pct if rec else None)
        if rec and rec.humidity_min_pct is not None and rec.humidity_max_pct is not None:
            daily["daily_humidity_mean_pct"].append(round((rec.humidity_min_pct + rec.humidity_max_pct) / 2.0, 2))
        else:
            daily["daily_humidity_mean_pct"].append(None)
    return daily


def build_weather_values(
    station: WeatherStation,
    observed_day: date,
    duplicate_dates: set | None = None,
) -> tuple[dict[str, Any], list[str]]:
    dup = duplicate_dates or set()
    values: dict[str, Any] = {}
    gaps: list[str] = []
    if dup:
        for d in sorted(dup):
            gaps.append(f"rain_suspect_consecutive_{d.strftime('%Y%m%d')}")
    for days in RAIN_WINDOWS_DAYS:
        records = records_for_window(station, observed_day, days)
        rain_values = [
            rain_value
            for record in records
            if record.day not in dup
            and (rain_value := usable_rain_value(record, gaps)) is not None
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
        "micro_area_id": str(observation.get("micro_area_id", "") or "") or None,
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
    for key in (
        "dry_spell_days",
        "days_since_significant_rain",
        "rainy_days_14d",
        "thermal_amplitude_mean_7d",
        "thermal_amplitude_mean_14d",
        "thermal_trend",
        "heat_stress_days",
        "high_humidity_days_14d",
    ):
        row[key] = None
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

    all_records_30d = records_for_window(station, observed_day, DAILY_SERIES_DAYS)
    dup_dates = _consecutive_duplicate_rain_dates(all_records_30d)
    weather_values, weather_gaps = build_weather_values(station, observed_day, dup_dates)
    derived_values = build_derived_features(station, observed_day, dup_dates)
    daily_series = build_daily_series(station, observed_day, dup_dates)
    row.update(weather_values)
    row.update(derived_values)
    row.update(daily_series)
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
    result = {key: row.get(key) for key in CSV_FIELDS}
    for key in JSON_EXTRA_FIELDS:
        if key in row:
            result[key] = row[key]
    return result


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
    stations = load_daily_weather_parquet(
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
