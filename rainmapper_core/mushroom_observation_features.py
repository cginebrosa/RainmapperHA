"""Join GIS and weather features for mushroom observations.

The joined payload is the first reusable v0 feature contract for local
observation review. It combines previously reconstructed weather and GIS
contexts by observation ID without changing observations, profiles or
historical Rainmapper CSV files.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_gis_lab, mushroom_observation_context, mushroom_paths


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
    "weather_source",
    "weather_station_code",
    "weather_station_distance_km",
    "weather_station_coverage_days_90d",
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
    "host_ids",
    "host_sources",
    "forest_type_ids",
    "forest_type_sources",
    "soil_tendency_ids",
    "soil_tendency_sources",
    "habitat_feature_ids",
    "habitat_feature_sources",
    "aspect_ids",
    "aspect_sources",
    "gis_altitude_m",
    "weather_gaps",
    "gis_gaps",
    "feature_gaps",
)


def emit_progress(progress_callback: Any | None, percent: float, message: str) -> None:
    """Report bounded progress while keeping existing callers callback-free."""
    if progress_callback:
        progress_callback(max(0, min(100, int(percent))), message)


def repo_root() -> Path:
    return mushroom_paths.repo_root()


def default_output_json_path() -> Path:
    return mushroom_paths.mushroom_observation_features_json_path()


def default_output_csv_path() -> Path:
    return mushroom_paths.mushroom_observation_features_csv_path()


def default_report_path() -> Path:
    return mushroom_paths.mushroom_observation_features_report_path()


def load_json_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def load_latest_features(path: Path | None = None) -> dict[str, Any] | None:
    target = path or default_output_json_path()
    if not target.exists():
        return None
    try:
        payload = load_json_payload(target)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return payload


def rows_by_observation_id(payload: dict[str, Any], key: str = "rows") -> dict[str, dict[str, Any]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        return {}
    indexed = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        observation_id = str(row.get("observation_id", "") or "")
        if observation_id:
            indexed[observation_id] = row
    return indexed


def gis_results_by_observation_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    results = payload.get("results")
    if not isinstance(results, list):
        return {}
    indexed = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        observation_id = str(row.get("observation_id", "") or "")
        if observation_id:
            indexed[observation_id] = row
    return indexed


def list_value(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def merged_values_with_sources(
    field_values: list[str] | None = None,
    gis_values: list[str] | None = None,
) -> tuple[list[str], dict[str, list[str]]]:
    values: list[str] = []
    sources: dict[str, list[str]] = {}
    for source, source_values in (("field", field_values or []), ("gis", gis_values or [])):
        for item_id in source_values:
            if item_id not in values:
                values.append(item_id)
            sources.setdefault(item_id, [])
            if source not in sources[item_id]:
                sources[item_id].append(source)
    return values, sources


def build_joined_row(weather_row: dict[str, Any], gis_row: dict[str, Any] | None) -> dict[str, Any]:
    gis_row = gis_row if isinstance(gis_row, dict) else {}
    context = gis_row.get("gis_context_v0")
    context = context if isinstance(context, dict) else {}
    feature_gaps = []
    weather_gaps = list_value(weather_row.get("data_gaps"))
    gis_gaps = list_value(gis_row.get("gaps"))
    host_ids, host_sources = merged_values_with_sources(
        list_value(weather_row.get("observed_host_ids")),
        list_value(context.get("host_ids")),
    )
    forest_type_ids, forest_type_sources = merged_values_with_sources(
        list_value(weather_row.get("observed_forest_type_ids")),
        list_value(context.get("forest_type_ids")),
    )
    soil_tendency_ids, soil_tendency_sources = merged_values_with_sources(
        list_value(weather_row.get("observed_soil_tendency_ids")),
        list_value(context.get("soil_tendency_ids")),
    )
    habitat_feature_ids, habitat_feature_sources = merged_values_with_sources(
        list_value(weather_row.get("observed_habitat_feature_ids")),
        list_value(context.get("habitat_feature_ids")),
    )
    aspect_ids, aspect_sources = merged_values_with_sources(
        field_values=list_value(weather_row.get("observed_aspect_ids")),
    )
    if not gis_row:
        feature_gaps.append("missing_gis_reconstruction")
    if not context:
        feature_gaps.append("missing_gis_context_v0")
    flush_abundance = weather_row.get("flush_abundance")
    target = str(weather_row.get("prediction_target", "") or "").strip()
    if target not in {"favorable", "unfavorable", "unknown"}:
        target = "unknown"
    if target == "unknown":
        # Compatibility only for feature artifacts built before prediction_target
        # was materialized from the catalog. New rebuilds always carry the target.
        legacy_result = str(weather_row.get("analysis_result", "") or "").strip()
        if legacy_result == "present":
            target = "favorable"
        elif legacy_result == "absent":
            target = "unfavorable"
    row = {
        "observation_id": weather_row.get("observation_id"),
        "species_id": weather_row.get("species_id") or gis_row.get("species_id"),
        "observed_at": weather_row.get("observed_at"),
        "analysis_result": weather_row.get("analysis_result"),
        "prediction_target": target,
        "flush_abundance": flush_abundance,
        "month": weather_row.get("month"),
        "season": weather_row.get("season"),
        "validation_status": weather_row.get("validation_status"),
        "calibration_use": weather_row.get("calibration_use"),
        "source_quality": weather_row.get("source_quality"),
        "micro_area_id": weather_row.get("micro_area_id"),
        "latitude": weather_row.get("latitude"),
        "longitude": weather_row.get("longitude"),
        "altitude_m": weather_row.get("altitude_m"),
        "weather_source": weather_row.get("weather_source"),
        "weather_station_code": weather_row.get("weather_station_code"),
        "weather_station_distance_km": weather_row.get("weather_station_distance_km"),
        "weather_station_coverage_days_90d": weather_row.get("weather_station_coverage_days_90d"),
        "rain_1d_mm": weather_row.get("rain_1d_mm"),
        "rain_7d_mm": weather_row.get("rain_7d_mm"),
        "rain_14d_mm": weather_row.get("rain_14d_mm"),
        "rain_21d_mm": weather_row.get("rain_21d_mm"),
        "rain_30d_mm": weather_row.get("rain_30d_mm"),
        "temp_min_7d_c": weather_row.get("temp_min_7d_c"),
        "temp_max_7d_c": weather_row.get("temp_max_7d_c"),
        "temp_mean_7d_c": weather_row.get("temp_mean_7d_c"),
        "temp_min_14d_c": weather_row.get("temp_min_14d_c"),
        "temp_max_14d_c": weather_row.get("temp_max_14d_c"),
        "temp_mean_14d_c": weather_row.get("temp_mean_14d_c"),
        "temp_min_21d_c": weather_row.get("temp_min_21d_c"),
        "temp_max_21d_c": weather_row.get("temp_max_21d_c"),
        "temp_mean_21d_c": weather_row.get("temp_mean_21d_c"),
        "temp_min_30d_c": weather_row.get("temp_min_30d_c"),
        "temp_max_30d_c": weather_row.get("temp_max_30d_c"),
        "temp_mean_30d_c": weather_row.get("temp_mean_30d_c"),
        "temp_min_c": weather_row.get("temp_min_c"),
        "temp_max_c": weather_row.get("temp_max_c"),
        "temp_mean_c": weather_row.get("temp_mean_c"),
        "humidity_min_7d_pct": weather_row.get("humidity_min_7d_pct"),
        "humidity_max_7d_pct": weather_row.get("humidity_max_7d_pct"),
        "humidity_mean_7d_pct": weather_row.get("humidity_mean_7d_pct"),
        "humidity_min_14d_pct": weather_row.get("humidity_min_14d_pct"),
        "humidity_max_14d_pct": weather_row.get("humidity_max_14d_pct"),
        "humidity_mean_14d_pct": weather_row.get("humidity_mean_14d_pct"),
        "humidity_min_21d_pct": weather_row.get("humidity_min_21d_pct"),
        "humidity_max_21d_pct": weather_row.get("humidity_max_21d_pct"),
        "humidity_mean_21d_pct": weather_row.get("humidity_mean_21d_pct"),
        "humidity_min_30d_pct": weather_row.get("humidity_min_30d_pct"),
        "humidity_max_30d_pct": weather_row.get("humidity_max_30d_pct"),
        "humidity_mean_30d_pct": weather_row.get("humidity_mean_30d_pct"),
        "humidity_min_pct": weather_row.get("humidity_min_pct"),
        "humidity_max_pct": weather_row.get("humidity_max_pct"),
        "humidity_mean_pct": weather_row.get("humidity_mean_pct"),
        "wind_avg_kmh": weather_row.get("wind_avg_kmh"),
        "wind_gust_kmh": weather_row.get("wind_gust_kmh"),
        "wind_direction_deg": weather_row.get("wind_direction_deg"),
        "dry_spell_days": weather_row.get("dry_spell_days"),
        "days_since_significant_rain": weather_row.get("days_since_significant_rain"),
        "rainy_days_14d": weather_row.get("rainy_days_14d"),
        "thermal_amplitude_mean_7d": weather_row.get("thermal_amplitude_mean_7d"),
        "thermal_amplitude_mean_14d": weather_row.get("thermal_amplitude_mean_14d"),
        "thermal_trend": weather_row.get("thermal_trend"),
        "heat_stress_days": weather_row.get("heat_stress_days"),
        "high_humidity_days_14d": weather_row.get("high_humidity_days_14d"),
        # Preserve the ordered daily weather series in the reusable JSON
        # feature artifact.  They are intentionally excluded from CSV_FIELDS
        # and from the operational v0 estimator, but are required to build
        # leakage-free horizon experiments without reading mutable source CSVs.
        **{
            field: list(weather_row[field])
            if isinstance(weather_row.get(field), list)
            else []
            for field in mushroom_observation_context.JSON_EXTRA_FIELDS
        },
        "host_ids": host_ids,
        "host_sources": host_sources,
        "forest_type_ids": forest_type_ids,
        "forest_type_sources": forest_type_sources,
        "soil_tendency_ids": soil_tendency_ids,
        "soil_tendency_sources": soil_tendency_sources,
        "habitat_feature_ids": habitat_feature_ids,
        "habitat_feature_sources": habitat_feature_sources,
        "aspect_ids": aspect_ids,
        "aspect_sources": aspect_sources,
        "gis_altitude_m": context.get("altitude_m"),
        "weather_gaps": weather_gaps,
        "gis_gaps": gis_gaps,
        "feature_gaps": feature_gaps,
    }
    return row


def build_observation_features_v0(
    weather_features_path: Path | None = None,
    gis_reconstruction_path: Path | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    weather_features_path = weather_features_path or mushroom_observation_context.default_output_json_path()
    gis_reconstruction_path = gis_reconstruction_path or mushroom_gis_lab.default_output_path()
    emit_progress(progress_callback, 2, "Cargando features meteorologicas.")
    weather_payload = load_json_payload(weather_features_path)
    emit_progress(progress_callback, 10, "Cargando reconstruccion GIS/DEM.")
    gis_payload = load_json_payload(gis_reconstruction_path) if gis_reconstruction_path.exists() else {}
    weather_rows = rows_by_observation_id(weather_payload)
    gis_rows = gis_results_by_observation_id(gis_payload)
    rows = []
    weather_items = list(weather_rows.items())
    weather_total = len(weather_items)
    if not weather_items:
        emit_progress(progress_callback, 78, "No hay observaciones que unir.")
    for index, (observation_id, weather_row) in enumerate(weather_items, start=1):
        rows.append(build_joined_row(weather_row, gis_rows.get(observation_id)))
        emit_progress(
            progress_callback,
            15 + (index / weather_total) * 63,
            f"Uniendo features {index}/{weather_total} observaciones.",
        )
    emit_progress(progress_callback, 82, "Ordenando features v0.")
    rows.sort(key=lambda row: (str(row.get("observed_at", "")), str(row.get("observation_id", ""))))
    emit_progress(progress_callback, 87, "Calculando cobertura GIS.")
    with_gis = sum(1 for row in rows if "missing_gis_reconstruction" not in row["feature_gaps"])
    emit_progress(progress_callback, 91, "Calculando gaps meteorologicos.")
    with_weather_gaps = sum(1 for row in rows if row["weather_gaps"])
    emit_progress(progress_callback, 95, "Calculando gaps GIS y de features.")
    with_gis_gaps = sum(1 for row in rows if row["gis_gaps"] or row["feature_gaps"])
    emit_progress(progress_callback, 100, "Features v0 unidas.")
    return {
        "schema_version": "0.2",
        "kind": "mushroom_observation_features_v0",
        "generated_at": datetime.now(UTC).isoformat(),
        "prediction_target_policy": (
            weather_payload.get("prediction_target_policy")
            if isinstance(weather_payload.get("prediction_target_policy"), dict)
            else {
                "version": "legacy_analysis_result_compatibility",
                "field": "prediction_target",
                "source_field": "analysis_result",
            }
        ),
        "input_paths": {
            "weather_features": str(weather_features_path),
            "gis_reconstruction": str(gis_reconstruction_path),
        },
        "summary": {
            "observations": len(rows),
            "with_weather": len(weather_rows),
            "with_gis": with_gis,
            "with_weather_gaps": with_weather_gaps,
            "with_gis_or_feature_gaps": with_gis_gaps,
        },
        "rows": rows,
    }


def csv_value(value: object) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in CSV_FIELDS})


def report_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    lines = [
        "# Mushroom Observation Features v0",
        "",
        f"- Generated at: {payload.get('generated_at', '-')}",
        f"- Observations: {summary.get('observations', 0)}",
        f"- With weather: {summary.get('with_weather', 0)}",
        f"- With GIS: {summary.get('with_gis', 0)}",
        f"- With weather gaps: {summary.get('with_weather_gaps', 0)}",
        f"- With GIS/feature gaps: {summary.get('with_gis_or_feature_gaps', 0)}",
        "",
        "## Species Summary",
        "",
    ]
    by_species: dict[str, dict[str, int]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        species_id = str(row.get("species_id", "") or "unknown")
        item = by_species.setdefault(species_id, {"rows": 0, "favorable": 0, "unfavorable": 0, "unknown": 0, "weather_gaps": 0, "gis_gaps": 0})
        item["rows"] += 1
        target = str(row.get("prediction_target", "") or "unknown")
        item[target if target in {"favorable", "unfavorable"} else "unknown"] += 1
        if row.get("weather_gaps"):
            item["weather_gaps"] += 1
        if row.get("gis_gaps") or row.get("feature_gaps"):
            item["gis_gaps"] += 1
    for species_id, item in sorted(by_species.items()):
        lines.append(
            f"- {species_id}: {item['rows']} obs, {item['favorable']} favorable, "
            f"{item['unfavorable']} unfavorable, {item['unknown']} unknown target, "
            f"weather gaps {item['weather_gaps']}, GIS gaps {item['gis_gaps']}"
        )
    return "\n".join(lines) + "\n"


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_markdown(payload), encoding="utf-8")


def build_and_write_observation_features_v0(
    weather_features_path: Path | None = None,
    gis_reconstruction_path: Path | None = None,
    output_json_path: Path | None = None,
    output_csv_path: Path | None = None,
    report_path: Path | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    payload = build_observation_features_v0(
        weather_features_path,
        gis_reconstruction_path,
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
    emit_progress(progress_callback, 87, "Escribiendo features JSON.")
    write_json(output_json_path, payload)
    emit_progress(progress_callback, 91, "Escribiendo features CSV.")
    write_csv(output_csv_path, payload["rows"])
    emit_progress(progress_callback, 97, "Escribiendo informe de features.")
    write_report(report_path, payload)
    emit_progress(progress_callback, 100, "Features v0 guardadas.")
    return payload
