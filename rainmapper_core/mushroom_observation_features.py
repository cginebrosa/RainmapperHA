"""Join experimental GIS and weather features for mushroom observations.

The joined payload is the first reusable v0 feature contract for local
observation review. It combines previously reconstructed weather and GIS
contexts by observation ID without changing observations, profiles or
historical Rainmapper CSV files.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_gis_lab, mushroom_observation_context


CSV_FIELDS = (
    "observation_id",
    "species_id",
    "observed_at",
    "analysis_result",
    "flush_abundance",
    "validation_status",
    "calibration_use",
    "source_quality",
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
    "rain_60d_mm",
    "rain_90d_mm",
    "temp_min_c",
    "temp_max_c",
    "temp_mean_c",
    "humidity_min_pct",
    "humidity_max_pct",
    "humidity_mean_pct",
    "wind_avg_kmh",
    "wind_gust_kmh",
    "wind_direction_deg",
    "host_ids",
    "forest_type_ids",
    "soil_tendency_ids",
    "habitat_feature_ids",
    "gis_altitude_m",
    "weather_gaps",
    "gis_gaps",
    "feature_gaps",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_lab_root() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_LAB_DIR", "").strip()
    if configured:
        return Path(configured)
    ha_share_root = Path("/share/rainmapper")
    if ha_share_root.exists():
        return ha_share_root / "mushroom-lab"
    local_share_copy = repo_root() / "docker-data"
    if local_share_copy.exists():
        return local_share_copy / "mushroom-lab"
    return repo_root() / "tmp" / "mushroom-lab"


def default_output_json_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATION_FEATURES_PATH", "").strip()
    if configured:
        return Path(configured)
    return default_lab_root() / "working" / "features" / "observation_features_v0.json"


def default_output_csv_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATION_FEATURES_CSV_PATH", "").strip()
    if configured:
        return Path(configured)
    return default_lab_root() / "working" / "features" / "observation_features_v0.csv"


def default_report_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATION_FEATURES_REPORT_PATH", "").strip()
    if configured:
        return Path(configured)
    return default_lab_root() / "output" / "reports" / "observation_features_v0.md"


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


def build_joined_row(weather_row: dict[str, Any], gis_row: dict[str, Any] | None) -> dict[str, Any]:
    gis_row = gis_row if isinstance(gis_row, dict) else {}
    context = gis_row.get("gis_context_v0")
    context = context if isinstance(context, dict) else {}
    feature_gaps = []
    weather_gaps = list_value(weather_row.get("data_gaps"))
    gis_gaps = list_value(gis_row.get("gaps"))
    if not gis_row:
        feature_gaps.append("missing_gis_reconstruction")
    if not context:
        feature_gaps.append("missing_gis_context_v0")
    row = {
        "observation_id": weather_row.get("observation_id"),
        "species_id": weather_row.get("species_id") or gis_row.get("species_id"),
        "observed_at": weather_row.get("observed_at"),
        "analysis_result": weather_row.get("analysis_result"),
        "flush_abundance": weather_row.get("flush_abundance"),
        "validation_status": weather_row.get("validation_status"),
        "calibration_use": weather_row.get("calibration_use"),
        "source_quality": weather_row.get("source_quality"),
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
        "rain_60d_mm": weather_row.get("rain_60d_mm"),
        "rain_90d_mm": weather_row.get("rain_90d_mm"),
        "temp_min_c": weather_row.get("temp_min_c"),
        "temp_max_c": weather_row.get("temp_max_c"),
        "temp_mean_c": weather_row.get("temp_mean_c"),
        "humidity_min_pct": weather_row.get("humidity_min_pct"),
        "humidity_max_pct": weather_row.get("humidity_max_pct"),
        "humidity_mean_pct": weather_row.get("humidity_mean_pct"),
        "wind_avg_kmh": weather_row.get("wind_avg_kmh"),
        "wind_gust_kmh": weather_row.get("wind_gust_kmh"),
        "wind_direction_deg": weather_row.get("wind_direction_deg"),
        "host_ids": list_value(context.get("host_ids")),
        "forest_type_ids": list_value(context.get("forest_type_ids")),
        "soil_tendency_ids": list_value(context.get("soil_tendency_ids")),
        "habitat_feature_ids": list_value(context.get("habitat_feature_ids")),
        "gis_altitude_m": context.get("altitude_m"),
        "weather_gaps": weather_gaps,
        "gis_gaps": gis_gaps,
        "feature_gaps": feature_gaps,
    }
    return row


def build_observation_features_v0(
    weather_features_path: Path | None = None,
    gis_reconstruction_path: Path | None = None,
) -> dict[str, Any]:
    weather_features_path = weather_features_path or mushroom_observation_context.default_output_json_path()
    gis_reconstruction_path = gis_reconstruction_path or mushroom_gis_lab.default_output_path()
    weather_payload = load_json_payload(weather_features_path)
    gis_payload = load_json_payload(gis_reconstruction_path) if gis_reconstruction_path.exists() else {}
    weather_rows = rows_by_observation_id(weather_payload)
    gis_rows = gis_results_by_observation_id(gis_payload)
    rows = [build_joined_row(weather_row, gis_rows.get(observation_id)) for observation_id, weather_row in weather_rows.items()]
    rows.sort(key=lambda row: (str(row.get("observed_at", "")), str(row.get("observation_id", ""))))
    with_gis = sum(1 for row in rows if "missing_gis_reconstruction" not in row["feature_gaps"])
    with_weather_gaps = sum(1 for row in rows if row["weather_gaps"])
    with_gis_gaps = sum(1 for row in rows if row["gis_gaps"] or row["feature_gaps"])
    return {
        "schema_version": "0.1",
        "kind": "mushroom_observation_features_v0",
        "generated_at": datetime.now(UTC).isoformat(),
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
        item = by_species.setdefault(species_id, {"rows": 0, "present": 0, "absent": 0, "weather_gaps": 0, "gis_gaps": 0})
        item["rows"] += 1
        if row.get("analysis_result") == "absent":
            item["absent"] += 1
        else:
            item["present"] += 1
        if row.get("weather_gaps"):
            item["weather_gaps"] += 1
        if row.get("gis_gaps") or row.get("feature_gaps"):
            item["gis_gaps"] += 1
    for species_id, item in sorted(by_species.items()):
        lines.append(
            f"- {species_id}: {item['rows']} obs, {item['present']} present, "
            f"{item['absent']} absent, weather gaps {item['weather_gaps']}, GIS gaps {item['gis_gaps']}"
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
) -> dict[str, Any]:
    payload = build_observation_features_v0(weather_features_path, gis_reconstruction_path)
    output_json_path = output_json_path or default_output_json_path()
    output_csv_path = output_csv_path or default_output_csv_path()
    report_path = report_path or default_report_path()
    payload["output_paths"] = {
        "json": str(output_json_path),
        "csv": str(output_csv_path),
        "report": str(report_path),
    }
    write_json(output_json_path, payload)
    write_csv(output_csv_path, payload["rows"])
    write_report(report_path, payload)
    return payload
