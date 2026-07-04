"""Build an experimental learned v0 model from approved observation features.

This module does not write mushroom profiles and does not choose production
thresholds. It summarizes what the current observation feature table supports
so the UI can compare learned evidence against manual v0 profile data.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_observation_features, mushroom_paths


CATEGORICAL_FEATURES = (
    ("host_ids", "hosts", "host_sources"),
    ("forest_type_ids", "forests", "forest_type_sources"),
    ("soil_tendency_ids", "soils", "soil_tendency_sources"),
    ("habitat_feature_ids", "habitat", "habitat_feature_sources"),
    ("aspect_ids", "aspects", "aspect_sources"),
)

NUMERIC_FEATURES = (
    ("gis_altitude_m", "altitude_m"),
    ("rain_7d_mm", "rain_7d_mm"),
    ("rain_14d_mm", "rain_14d_mm"),
    ("rain_21d_mm", "rain_21d_mm"),
    ("rain_30d_mm", "rain_30d_mm"),
    ("rain_60d_mm", "rain_60d_mm"),
    ("rain_90d_mm", "rain_90d_mm"),
    ("temp_min_7d_c", "temp_min_7d_c"),
    ("temp_max_7d_c", "temp_max_7d_c"),
    ("temp_min_14d_c", "temp_min_14d_c"),
    ("temp_max_14d_c", "temp_max_14d_c"),
    ("temp_min_21d_c", "temp_min_21d_c"),
    ("temp_max_21d_c", "temp_max_21d_c"),
    ("temp_min_30d_c", "temp_min_30d_c"),
    ("temp_max_30d_c", "temp_max_30d_c"),
    ("humidity_min_7d_pct", "humidity_min_7d_pct"),
    ("humidity_max_7d_pct", "humidity_max_7d_pct"),
    ("humidity_min_14d_pct", "humidity_min_14d_pct"),
    ("humidity_max_14d_pct", "humidity_max_14d_pct"),
    ("humidity_min_21d_pct", "humidity_min_21d_pct"),
    ("humidity_max_21d_pct", "humidity_max_21d_pct"),
    ("humidity_min_30d_pct", "humidity_min_30d_pct"),
    ("humidity_max_30d_pct", "humidity_max_30d_pct"),
)


def repo_root() -> Path:
    return mushroom_paths.repo_root()


def default_output_json_path() -> Path:
    return mushroom_paths.mushroom_learned_model_json_path()


def default_report_path() -> Path:
    return mushroom_paths.mushroom_learned_model_report_path()


def load_json_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def load_latest_model(path: Path | None = None) -> dict[str, Any] | None:
    target = path or default_output_json_path()
    if not target.exists():
        return None
    try:
        return load_json_payload(target)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def is_positive(row: dict[str, Any]) -> bool:
    return str(row.get("analysis_result", "") or "").strip() != "absent"


def is_training_row(row: dict[str, Any]) -> bool:
    """Return whether an observation feature row is approved for model learning."""
    return (
        str(row.get("validation_status", "") or "").strip() == "valid"
        and str(row.get("calibration_use", "") or "").strip() == "include"
    )


def numeric_value(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def summarize_numeric(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [value for row in rows if (value := numeric_value(row.get(key))) is not None]
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": len(values),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "mean": round(sum(values) / len(values), 2),
    }


def list_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def source_values(row: dict[str, Any], source_key: str, item_id: str) -> list[str]:
    sources = row.get(source_key)
    if not isinstance(sources, dict):
        return ["v0"]
    values = sources.get(item_id)
    if not isinstance(values, list):
        return ["v0"]
    normalized = [str(value) for value in values if str(value or "").strip()]
    return normalized or ["v0"]


def summarize_categorical(
    positive_rows: list[dict[str, Any]],
    negative_rows: list[dict[str, Any]],
    key: str,
    source_key: str,
) -> list[dict[str, Any]]:
    positive_counts: dict[str, set[str]] = {}
    negative_counts: dict[str, set[str]] = {}
    positive_source_counts: dict[str, dict[str, set[str]]] = {}
    negative_source_counts: dict[str, dict[str, set[str]]] = {}
    for row in positive_rows:
        observation_id = str(row.get("observation_id", "") or "")
        for item_id in list_values(row.get(key)):
            positive_counts.setdefault(item_id, set()).add(observation_id)
            for source in source_values(row, source_key, item_id):
                positive_source_counts.setdefault(item_id, {}).setdefault(source, set()).add(observation_id)
    for row in negative_rows:
        observation_id = str(row.get("observation_id", "") or "")
        for item_id in list_values(row.get(key)):
            negative_counts.setdefault(item_id, set()).add(observation_id)
            for source in source_values(row, source_key, item_id):
                negative_source_counts.setdefault(item_id, {}).setdefault(source, set()).add(observation_id)

    rows = []
    positive_total = len(positive_rows)
    negative_total = len(negative_rows)
    for item_id in sorted(set(positive_counts) | set(negative_counts)):
        positive_support = len(positive_counts.get(item_id, set()))
        negative_support = len(negative_counts.get(item_id, set()))
        positive_ratio = positive_support / positive_total if positive_total else None
        negative_ratio = negative_support / negative_total if negative_total else None
        ratio_delta = (
            round(positive_ratio - negative_ratio, 4)
            if positive_ratio is not None and negative_ratio is not None
            else None
        )
        rows.append(
            {
                "id": item_id,
                "positive_support": positive_support,
                "negative_support": negative_support,
                "positive_source_support": {
                    source: len(observation_ids)
                    for source, observation_ids in sorted(positive_source_counts.get(item_id, {}).items())
                },
                "negative_source_support": {
                    source: len(observation_ids)
                    for source, observation_ids in sorted(negative_source_counts.get(item_id, {}).items())
                },
                "positive_sources": sorted(positive_source_counts.get(item_id, {})),
                "negative_sources": sorted(negative_source_counts.get(item_id, {})),
                "positive_ratio": round(positive_ratio, 4) if positive_ratio is not None else None,
                "negative_ratio": round(negative_ratio, 4) if negative_ratio is not None else None,
                "ratio_delta": ratio_delta,
                "positive_observations": sorted(positive_counts.get(item_id, set())),
                "negative_observations": sorted(negative_counts.get(item_id, set())),
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            -(item["positive_support"] or 0),
            item["negative_support"] or 0,
            str(item["id"]),
        ),
    )


def summarize_species(species_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    positive_rows = [row for row in rows if is_positive(row)]
    negative_rows = [row for row in rows if not is_positive(row)]
    weather_gap_rows = [row for row in rows if list_values(row.get("weather_gaps"))]
    gis_gap_rows = [row for row in rows if list_values(row.get("gis_gaps")) or list_values(row.get("feature_gaps"))]
    categorical = {
        output_key: summarize_categorical(positive_rows, negative_rows, source_key, source_tracking_key)
        for source_key, output_key, source_tracking_key in CATEGORICAL_FEATURES
    }
    numeric = {
        output_key: {
            "positive": summarize_numeric(positive_rows, source_key),
            "negative": summarize_numeric(negative_rows, source_key),
        }
        for source_key, output_key in NUMERIC_FEATURES
    }
    return {
        "species_id": species_id,
        "observation_count": len(rows),
        "positive_count": len(positive_rows),
        "negative_count": len(negative_rows),
        "weather_gap_count": len(weather_gap_rows),
        "gis_gap_count": len(gis_gap_rows),
        "categorical_features": categorical,
        "numeric_features": numeric,
    }


def build_learned_model_v0(features_path: Path | None = None, species_id_filter: str | None = None) -> dict[str, Any]:
    features_path = features_path or mushroom_observation_features.default_output_json_path()
    selected_species_id = str(species_id_filter or "").strip()
    features_payload = load_json_payload(features_path)
    feature_rows = features_payload.get("rows")
    all_rows = [row for row in feature_rows if isinstance(row, dict)] if isinstance(feature_rows, list) else []
    rows = [row for row in all_rows if is_training_row(row)]
    by_species: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        species_id = str(row.get("species_id", "") or "").strip()
        if selected_species_id and species_id != selected_species_id:
            continue
        if species_id:
            by_species.setdefault(species_id, []).append(row)
    species_models = [
        summarize_species(species_id, species_rows)
        for species_id, species_rows in sorted(by_species.items())
    ]
    return {
        "schema_version": "0.1",
        "kind": "mushroom_learned_model_v0",
        "generated_at": datetime.now(UTC).isoformat(),
        "model_status": "experimental_observation_learned",
        "scope": {
            "species_id": selected_species_id or None,
        },
        "model_notes": [
            "This model is recalculated from observation_features_v0.json.",
            "It does not write mushroom_profiles.json and does not define production thresholds.",
            "Support ratios are descriptive evidence from valid observations marked include for calibration.",
        ],
        "input_paths": {"observation_features_v0": str(features_path)},
        "feature_contract": {
            "categorical": [key for _source, key, _source_tracking in CATEGORICAL_FEATURES],
            "numeric": [key for _source, key in NUMERIC_FEATURES],
        },
        "summary": {
            "observations": len(rows),
            "source_observations": len(all_rows),
            "excluded_observations": len(all_rows) - len(rows),
            "species": len(species_models),
            "positive_observations": sum(1 for row in rows if is_positive(row)),
            "negative_observations": sum(1 for row in rows if not is_positive(row)),
        },
        "species_models": species_models,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def report_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Mushroom Learned Model v0",
        "",
        f"- Generated at: {payload.get('generated_at', '-')}",
        f"- Observations: {summary.get('observations', 0)}",
        f"- Source observations: {summary.get('source_observations', 0)}",
        f"- Excluded observations: {summary.get('excluded_observations', 0)}",
        f"- Species: {summary.get('species', 0)}",
        f"- Positive observations: {summary.get('positive_observations', 0)}",
        f"- Negative observations: {summary.get('negative_observations', 0)}",
        "",
        "## Species",
        "",
    ]
    models = payload.get("species_models") if isinstance(payload.get("species_models"), list) else []
    for model in models:
        if not isinstance(model, dict):
            continue
        lines.append(
            "- {species_id}: {positive}/{total} positive, {negative} negative, weather gaps {weather_gaps}, GIS gaps {gis_gaps}".format(
                species_id=model.get("species_id", "-"),
                positive=model.get("positive_count", 0),
                total=model.get("observation_count", 0),
                negative=model.get("negative_count", 0),
                weather_gaps=model.get("weather_gap_count", 0),
                gis_gaps=model.get("gis_gap_count", 0),
            )
        )
    return "\n".join(lines) + "\n"


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_markdown(payload), encoding="utf-8")


def build_and_write_learned_model_v0(
    features_path: Path | None = None,
    output_json_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    payload = build_learned_model_v0(features_path)
    output_json_path = output_json_path or default_output_json_path()
    report_path = report_path or default_report_path()
    payload["output_paths"] = {
        "json": str(output_json_path),
        "report": str(report_path),
    }
    write_json(output_json_path, payload)
    write_report(report_path, payload)
    return payload


def build_and_write_species_learned_model_v0(
    species_id: str,
    features_path: Path | None = None,
    output_json_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Rebuild one species model and merge it into the shared learned model file."""
    selected_species_id = species_id.strip()
    if not selected_species_id:
        raise ValueError("species_id is required")
    output_json_path = output_json_path or default_output_json_path()
    report_path = report_path or default_report_path()
    species_payload = build_learned_model_v0(features_path, species_id_filter=selected_species_id)
    existing_payload = load_latest_model(output_json_path)
    if existing_payload is None:
        existing_payload = build_learned_model_v0(features_path)

    existing_models = existing_payload.get("species_models")
    model_by_species = {
        str(model.get("species_id", "") or ""): model
        for model in existing_models
        if isinstance(model, dict) and str(model.get("species_id", "") or "").strip()
    } if isinstance(existing_models, list) else {}
    replacement_models = species_payload.get("species_models")
    replacement = replacement_models[0] if isinstance(replacement_models, list) and replacement_models else None
    if isinstance(replacement, dict):
        model_by_species[selected_species_id] = replacement
    else:
        model_by_species.pop(selected_species_id, None)

    merged_models = [model_by_species[key] for key in sorted(model_by_species)]
    summary = dict(existing_payload.get("summary") if isinstance(existing_payload.get("summary"), dict) else {})
    summary.update(
        {
            "observations": sum(int(model.get("observation_count", 0) or 0) for model in merged_models),
            "species": len(merged_models),
            "positive_observations": sum(int(model.get("positive_count", 0) or 0) for model in merged_models),
            "negative_observations": sum(int(model.get("negative_count", 0) or 0) for model in merged_models),
        }
    )

    merged_payload = dict(existing_payload)
    merged_payload["generated_at"] = datetime.now(UTC).isoformat()
    merged_payload["scope"] = {"species_id": None}
    merged_payload["summary"] = summary
    merged_payload["species_models"] = merged_models
    merged_payload["last_species_rebuild"] = {
        "species_id": selected_species_id,
        "generated_at": merged_payload["generated_at"],
        "observation_count": int(replacement.get("observation_count", 0) or 0) if isinstance(replacement, dict) else 0,
    }
    merged_payload["output_paths"] = {
        "json": str(output_json_path),
        "report": str(report_path),
    }
    write_json(output_json_path, merged_payload)
    write_report(report_path, merged_payload)
    return merged_payload
