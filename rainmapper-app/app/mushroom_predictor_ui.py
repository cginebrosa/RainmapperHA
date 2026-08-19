"""Server-rendered Predictor UI for the mushroom ML v0 model."""

from __future__ import annotations

import gc
import html
import json
from contextvars import ContextVar
from datetime import date, timedelta
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import urlencode

from rainmapper_core import mushroom_paths
from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_ml_multiversion_comparison
from rainmapper_core import mushroom_weather_idw
from rainmapper_core.mushroom_ml_predictor import (
    MushroomMLPredictor,
    invalidate_weather_stations_cache,
)
from rainmapper_core.mushroom_observation_context import WeatherParquetLayoutError
from rainmapper_core.mushroom_predictor_service import PreparedPredictor, validate_response

import mushroom_profiles_ui


# Module-level predictor cache — lazy-loaded, survives across requests
_predictor_cache: dict[str, MushroomMLPredictor] = {}
_predictor_cache_lock = RLock()
_prepared_response: ContextVar[dict[str, Any] | None] = ContextVar(
    "mushroom_predictor_prepared_response", default=None
)
_prepared_weather_cache: ContextVar[dict[tuple[object, ...], Any] | None] = ContextVar(
    "mushroom_predictor_prepared_weather_cache", default=None
)
_comparison_cache: ContextVar[dict[str, Any] | None] = ContextVar(
    "mushroom_predictor_comparison_cache", default=None
)
_executor_query: ContextVar[str] = ContextVar("mushroom_predictor_executor", default="")
_allow_executor_change: ContextVar[bool] = ContextVar(
    "mushroom_predictor_allow_executor_change", default=True
)
_training_freshness: ContextVar[dict[str, Any] | None] = ContextVar(
    "mushroom_predictor_training_freshness", default=None
)

# ML report cache — loaded once per process, reset if file changes
_ml_report_cache: dict[str, Any] | None = None
_ml_report_mtime: float | None = None

_COMPARISON_ESTIMATORS = (
    ("logistic_regression_reduced_v1", "LR", False),
    ("random_forest_restricted_v1", "RF", False),
    ("extra_trees_restricted_v1", "ET", False),
    ("hist_gradient_boosting_restricted_v1", "HGB", False),
    ("knn_distance_v1", "KNN", False),
    ("rbf_svm_calibrated_v1", "SVM", False),
    ("elastic_net_logistic_raw365_v1", "Elastic Net", False),
    ("sparse_group_logistic_raw365_v1", "Sparse Group", False),
    ("smooth_species_logistic_v1", "Smooth Species", False),
    ("smooth_shared_logistic_v1", "Smooth Shared", False),
    ("smooth_partial_pooling_logistic_v1", "Smooth Partial", False),
)
_ESTIMATOR_HELP_KEYS = {
    "logistic_regression_reduced_v1": "ui.predictor_estimator_help_lr",
    "random_forest_restricted_v1": "ui.predictor_estimator_help_rf",
    "extra_trees_restricted_v1": "ui.predictor_estimator_help_et",
    "hist_gradient_boosting_restricted_v1": "ui.predictor_estimator_help_hgb",
    "knn_distance_v1": "ui.predictor_estimator_help_knn",
    "rbf_svm_calibrated_v1": "ui.predictor_estimator_help_svm",
    "elastic_net_logistic_raw365_v1": "ui.predictor_help_estimator_generic",
    "sparse_group_logistic_raw365_v1": "ui.predictor_help_estimator_generic",
    "smooth_species_logistic_v1": "ui.predictor_help_estimator_generic",
    "smooth_shared_logistic_v1": "ui.predictor_help_estimator_generic",
    "smooth_partial_pooling_logistic_v1": "ui.predictor_help_estimator_generic",
}
_ESTIMATOR_SHORT_NAMES = {
    estimator_id: short_name
    for estimator_id, short_name, _experimental in _COMPARISON_ESTIMATORS
}
_ESTIMATOR_SHORT_NAMES.update(
    {
        "elastic_net_logistic_raw365_v1": "Elastic Net",
        "sparse_group_logistic_raw365_v1": "Sparse Group",
        "smooth_species_logistic_v1": "Smooth Species",
        "smooth_shared_logistic_v1": "Smooth Shared",
        "smooth_partial_pooling_logistic_v1": "Smooth Partial",
    }
)

_OUT_OF_DOMAIN_FEATURE_LABEL_KEYS = {
    "horizon_days": "ui.predictor_feature_horizon_days",
    "target_month_sin": "ui.predictor_feature_target_month_sin",
    "target_month_cos": "ui.predictor_feature_target_month_cos",
    "gis_altitude_m": "ui.predictor_feature_gis_altitude",
    "rain_cutoff_0_3d_mm": "ui.predictor_feature_rain_0_3d",
    "rain_cutoff_4_7d_mm": "ui.predictor_feature_rain_4_7d",
    "rain_cutoff_8_14d_mm": "ui.predictor_feature_rain_8_14d",
    "rain_cutoff_15_21d_mm": "ui.predictor_feature_rain_15_21d",
    "days_since_rain_gt_2_at_target": "ui.predictor_feature_days_since_rain",
    "days_since_significant_rain_at_target": "ui.predictor_feature_days_since_significant_rain",
    "significant_rain_found_90d": "ui.predictor_feature_significant_rain_found",
    "rain_observed_days_21": "ui.predictor_feature_rain_observed_21",
    "rain_missing_days_21": "ui.predictor_feature_rain_missing_21",
    "rain_suppressed_days_21": "ui.predictor_feature_rain_suppressed_21",
    "rain_observed_days_90": "ui.predictor_feature_rain_observed_90",
    "rain_missing_days_90": "ui.predictor_feature_rain_missing_90",
    "rain_suppressed_days_90": "ui.predictor_feature_rain_suppressed_90",
    "dry_spell_observed_at_cutoff": "ui.predictor_feature_dry_spell",
    "dry_spell_is_censored": "ui.predictor_feature_dry_spell_censored",
    "heat_stress_observed_at_cutoff": "ui.predictor_feature_heat_stress",
    "heat_stress_is_censored": "ui.predictor_feature_heat_stress_censored",
    "temp_mean_after_significant_rain_c": "ui.predictor_feature_temp_after_rain",
    "temp_max_mean_cutoff_7d_c": "ui.predictor_feature_temp_max_cutoff_7d",
    "temp_mean_cutoff_7d_c": "ui.predictor_feature_temp_mean_cutoff_7d",
    "humidity_mean_after_significant_rain_pct": "ui.predictor_feature_humidity_after_rain",
    "temp_observed_days_after_significant_rain": "ui.predictor_feature_temp_coverage_after_rain",
    "humidity_observed_days_after_significant_rain": "ui.predictor_feature_humidity_coverage_after_rain",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lbl(key: str) -> str:
    return mushroom_profiles_ui.ui_label(key)


def _tooltip_label(
    label: str,
    help_key: str,
    *,
    strong: bool = True,
) -> str:
    """Render a compact, accessible label with localized browser help."""
    help_text = _lbl(help_key)
    escaped_label = html.escape(label)
    escaped_help = html.escape(help_text, quote=True)
    escaped_aria = html.escape(f"{label}. {help_text}", quote=True)
    label_html = f"<strong>{escaped_label}</strong>" if strong else escaped_label
    return (
        f'<span class="pred-tooltip" tabindex="0" title="{escaped_help}" '
        f'aria-label="{escaped_aria}">{label_html}'
        f'<span class="pred-tooltip-icon" aria-hidden="true">ⓘ</span></span>'
    )


def _tooltip_label_key(
    label_key: str,
    help_key: str,
    *,
    strong: bool = True,
) -> str:
    return _tooltip_label(_lbl(label_key), help_key, strong=strong)


def _predictor_error_text(exc: Exception) -> str:
    if isinstance(exc, WeatherParquetLayoutError):
        return _lbl("ui.predictor_weather_refresh_required")
    return str(exc)


def _get_predictor(species_id: str) -> MushroomMLPredictor:
    prepared = _prepared_response.get()
    if prepared is not None and species_id in prepared.get("data", {}).get("species", {}):
        return PreparedPredictor(species_id, prepared)  # type: ignore[return-value]
    with _predictor_cache_lock:
        if species_id not in _predictor_cache:
            _predictor_cache[species_id] = MushroomMLPredictor(species_id)
        return _predictor_cache[species_id]


def release_predictor_cache() -> int:
    """Release Predictor instances and shared weather data before a runner action."""
    with _predictor_cache_lock:
        released_instances = len(_predictor_cache)
        _predictor_cache.clear()
        invalidate_weather_stations_cache()
    gc.collect()
    return released_instances


def predictor_cache_info(species_id: str = "") -> dict[str, int | bool]:
    """Return non-sensitive cache state for request diagnostics."""
    with _predictor_cache_lock:
        instance_count = len(_predictor_cache)
        cold_request = (
            species_id not in _predictor_cache if species_id else instance_count == 0
        )
    return {
        "predictor_instance_count": instance_count,
        "cold_request": cold_request,
    }


def _rel_badge(ep_n: int, acc: float | None = None) -> str:
    if ep_n >= 10:
        square = "🟩"
    elif ep_n >= 4:
        square = "🟨"
    elif ep_n > 0:
        square = "🟥"
    else:
        return '<span class="pred-rel-badge pred-rel-none">—</span>'
    ep_label = _lbl("ui.predictor_stat_episodes").lower()
    return f'<span class="pred-rel-badge">{ep_n} {html.escape(ep_label)} {square}</span>'


def _rel_legend_html() -> str:
    ep_label = _lbl("ui.predictor_stat_episodes").lower()
    return (
        f'<p class="pred-hint-legend">'
        f'🟩 ≥10 {html.escape(ep_label)} &nbsp;'
        f'🟨 4–9 {html.escape(ep_label)} &nbsp;'
        f'🟥 1–3 {html.escape(ep_label)}'
        f'</p>'
    )


def _load_ml_report() -> dict[str, Any] | None:
    global _ml_report_cache, _ml_report_mtime  # noqa: PLW0603
    try:
        p = mushroom_paths.mushroom_ml_report_json_path()
        if not p.exists():
            return None
        mtime = p.stat().st_mtime
        if _ml_report_cache is None or mtime != _ml_report_mtime:
            _ml_report_cache = json.loads(p.read_text(encoding="utf-8"))
            _ml_report_mtime = mtime
        return _ml_report_cache
    except Exception:
        return None


def _get_species_backtest_stats(species_id: str) -> dict[str, Any] | None:
    report = _load_ml_report()
    if not isinstance(report, dict):
        return None
    for entry in report.get("species_results", []):
        if isinstance(entry, dict) and entry.get("species_id") == species_id:
            stats = entry.get("backtest_stats")
            return stats if isinstance(stats, dict) and "total_episodes" in stats else None
    return None


def trained_species_ids() -> list[str]:
    """Return model IDs that are also declared trained by the live report."""
    models_dir = mushroom_paths.mushroom_ml_models_dir()
    if not models_dir.exists():
        return []
    model_species = {
        p.stem.removeprefix("mushroom_ml_v0_")
        for p in models_dir.glob("mushroom_ml_v0_*.joblib")
    }
    report = _load_ml_report()
    if not isinstance(report, dict):
        return sorted(model_species)
    report_species = {
        str(row.get("species_id"))
        for row in report.get("species_results", [])
        if isinstance(row, dict) and row.get("species_id") and not row.get("skipped")
    }
    return sorted(model_species & report_species)


def _species_name(species_id: str, profiles_payload: dict[str, Any]) -> str:
    profiles = profiles_payload.get("species_profiles", []) if isinstance(profiles_payload, dict) else []
    for p in profiles:
        if not isinstance(p, dict) or p.get("species_id") != species_id:
            continue
        names = p.get("common_names")
        if isinstance(names, dict):
            name = names.get("es") or names.get("en") or names.get("ca")
            if name:
                return name
        if isinstance(names, list) and names:
            return names[0]
        return p.get("scientific_name") or species_id
    return species_id


def _area_name(area_id: str, known_sites_payload: dict[str, Any]) -> str:
    areas = known_sites_payload.get("areas", []) if isinstance(known_sites_payload, dict) else []
    for a in areas:
        if isinstance(a, dict) and a.get("area_id") == area_id:
            return a.get("name") or area_id
    return area_id


def _status_dot(label: str) -> str:
    if label == "abstain":
        return "⚫"
    if label == "out_of_season":
        return "⚪"
    if label == "favorable":
        return "🟢"
    if label == "uncertain":
        return "🟡"
    return "🔴"


def _pct(prob: float | None) -> str:
    if prob is None:
        return "—"
    return f"{round(prob * 100)}%"


def _status_cls(label: str) -> str:
    if label in {"out_of_season", "abstain"}:
        return "pred-muted"
    if label == "favorable":
        return "pred-green"
    if label == "uncertain":
        return "pred-yellow"
    return "pred-red"


def _url(view: str = "recommender", species: str = "", area: str = "", target_date: date | None = None, **extra: str) -> str:
    params: dict[str, str] = {"view": view}
    if species:
        params["species"] = species
    if area:
        params["area"] = area
    if target_date:
        params["date"] = target_date.isoformat()
    if _executor_query.get():
        params["executor"] = _executor_query.get()
    params.update({k: v for k, v in extra.items() if v})
    return "?" + urlencode(params)


def _executor_hidden_input() -> str:
    """Keep the selected executor across GET forms inside the Predictor."""
    executor = _executor_query.get()
    if not executor:
        return ""
    return (
        '<input type="hidden" name="executor" value="'
        f'{html.escape(executor, quote=True)}">'
    )


def _model_comparison(species_id: str, area_id: str, target_date: date) -> dict[str, Any] | None:
    predictor = _get_predictor(species_id)
    if isinstance(predictor, PreparedPredictor):
        return predictor.model_comparison(area_id, target_date)
    manifest_path = mushroom_paths.mushroom_ml_runtime_batch_manifest_path()
    if not manifest_path.is_file():
        return {
            "fixed_gap_7d_altitude_v2": {
                "available": False,
                "reason": "runtime_batch_not_installed",
            },
            "lag_event_altitude_v2": {
                "available": False,
                "reason": "runtime_batch_not_installed",
            },
        }
    request_cache = _comparison_cache.get()
    registry = request_cache.get("registry") if request_cache is not None else None
    if not isinstance(registry, dict):
        registry = mushroom_ml_version_registry.load_registry(
            mushroom_paths.mushroom_ml_version_registry_path()
        )
        if request_cache is not None:
            request_cache["registry"] = registry
    manifest = request_cache.get("manifest") if request_cache is not None else None
    if not isinstance(manifest, dict):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if request_cache is not None:
            request_cache["manifest"] = manifest
    profiles = request_cache.get("profiles") if request_cache is not None else None
    if not isinstance(profiles, dict):
        profiles = json.loads(
            mushroom_paths.mushroom_profiles_path().read_text(encoding="utf-8")
        )
        if request_cache is not None:
            request_cache["profiles"] = profiles
    species_profile = next(
        (
            row
            for row in profiles.get("species_profiles", [])
            if isinstance(row, dict) and row.get("species_id") == species_id
        ),
        {},
    )
    stations_file = Path("/app/stations.txt")
    return mushroom_ml_multiversion_comparison.compare_operational_reference(
        registry,
        manifest,
        species_id=species_id,
        area_id=area_id,
        target_date=target_date,
        issue_date=min(date.today(), target_date),
        season_phase=predictor.season_phase(target_date),
        phenology=dict(species_profile.get("phenology") or {}),
        models_root=mushroom_paths.mushroom_ml_models_dir(),
        known_sites_path=mushroom_paths.mushroom_known_sites_path(),
        weather_data_dir=mushroom_paths.weather_data_dir(),
        excluded_station_keys=(
            mushroom_weather_idw.disabled_wunderground_station_keys(stations_file)
            if stations_file.is_file()
            else frozenset()
        ),
        prepared_weather_cache=_prepared_weather_cache.get(),
        comparison_cache=request_cache,
    )


def _multiversion_catalog_payload() -> dict[str, Any]:
    prepared = _prepared_response.get()
    if prepared is not None:
        payload = prepared.get("data", {}).get("model_catalog")
        if isinstance(payload, dict):
            return dict(payload)
    try:
        registry = mushroom_ml_version_registry.load_registry(
            mushroom_paths.mushroom_ml_version_registry_path()
        )
    except (OSError, ValueError):
        return {"available": False, "entries": [], "installed_artifacts": []}
    result: dict[str, Any] = {
        "available": True,
        "active_version_id": registry["active_version_id"],
        "active_operational_target": dict(registry["active_operational_target"]),
        "entries": mushroom_ml_model_catalog.catalog_entries(registry),
        "runtime_batch_status": "not_installed",
        "installed_artifacts": [],
    }
    manifest_path = mushroom_paths.mushroom_ml_runtime_batch_manifest_path()
    if not manifest_path.is_file():
        return result
    try:
        manifest = mushroom_ml_model_catalog.validate_batch_manifest(
            registry, json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except (OSError, ValueError, json.JSONDecodeError):
        result["runtime_batch_status"] = "invalid"
        return result
    result["runtime_batch_status"] = "installed"
    result["runtime_batch"] = {
        "batch_id": manifest["batch_id"],
        "snapshot_id": manifest["snapshot_id"],
    }
    result["installed_artifacts"] = [
        {
            "artifact_ref": dict(row["artifact_ref"]),
            "supported_horizons": list(row["supported_horizons"]),
        }
        for row in manifest["artifacts"]
    ]
    return result


def multiversion_tokens_for_versions(species_id: str, version_ids: list[str]) -> list[str]:
    """Expand the simple V2--V6 choice to exact installed members."""
    payload = _multiversion_catalog_payload()
    entries = payload.get("entries") if isinstance(payload, dict) else []
    artifacts = payload.get("installed_artifacts") if isinstance(payload, dict) else []
    entries = entries if isinstance(entries, list) else []
    artifacts = artifacts if isinstance(artifacts, list) else []
    wanted = set(version_ids)
    tokens: list[str] = []
    availability_by_profile: dict[tuple[str, str], bool] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("catalog_visible"):
            continue
        version_id = str(entry.get("version_id") or "")
        profile_id = str(entry.get("profile_id") or "")
        matching = [
            row
            for row in artifacts
            if isinstance(row, dict)
            and isinstance(row.get("artifact_ref"), dict)
            and row["artifact_ref"].get("version_id") == version_id
            and row["artifact_ref"].get("profile_id") == profile_id
            and row["artifact_ref"].get("species_id") in {species_id, "all_species"}
        ]
        availability_by_profile[(version_id, profile_id)] = bool(matching)
        for artifact in matching:
            ref = artifact["artifact_ref"]
            for horizon in artifact.get("supported_horizons", []):
                selection = {
                    "version_id": version_id,
                    "temporal_contract_id": ref.get("temporal_contract_id"),
                    "profile_id": profile_id,
                    "estimator_id": ref.get("estimator_id"),
                    "horizon_days": horizon,
                }
                try:
                    token = mushroom_ml_model_catalog.selection_token(selection)
                except ValueError:
                    continue
                temporal = "fixed" if str(ref.get("temporal_contract_id")).startswith("fixed_gap_") else "lag"
                label = " / ".join(
                    (
                        str(entry.get("version_display_name") or version_id),
                        f"{temporal}-h{horizon}",
                        str(entry.get("profile_display_name") or profile_id),
                        _ESTIMATOR_SHORT_NAMES.get(
                            str(ref.get("estimator_id")), str(ref.get("estimator_id"))
                        ),
                    )
                )
                if not wanted or version_id in wanted:
                    tokens.append(token)
    return tokens


def _multiversion_controls(
    species_id: str, selected_tokens: list[str], selected_versions: list[str]
) -> str:
    payload = _multiversion_catalog_payload()
    entries = payload.get("entries") if isinstance(payload, dict) else []
    artifacts = payload.get("installed_artifacts") if isinstance(payload, dict) else []
    entries = entries if isinstance(entries, list) else []
    artifacts = artifacts if isinstance(artifacts, list) else []
    selected_version_set = set(selected_versions)
    if not selected_version_set:
        selected_version_set = {
            str(mushroom_ml_model_catalog.parse_selection_token(token)["version_id"])
            for token in selected_tokens
        }
    version_rows = []
    seen_versions: set[str] = set()
    availability_by_profile: dict[tuple[str, str], bool] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("catalog_visible"):
            continue
        version_id = str(entry.get("version_id") or "")
        profile_id = str(entry.get("profile_id") or "")
        matching = [
            row for row in artifacts
            if isinstance(row, dict) and isinstance(row.get("artifact_ref"), dict)
            and row["artifact_ref"].get("version_id") == version_id
            and row["artifact_ref"].get("profile_id") == profile_id
            and row["artifact_ref"].get("species_id") in {species_id, "all_species"}
        ]
        availability_by_profile[(version_id, profile_id)] = bool(matching)
        if version_id in seen_versions:
            continue
        seen_versions.add(version_id)
        short = {"altitude_v2": "V2", "biology_v3": "V3", "biology_v4": "V4",
                 "biology_v5_raw_weather_discovery": "V5", "biology_v6_smooth_hierarchical": "V6"}.get(version_id, version_id)
        compact_name = {
            "altitude_v2": "Altitud y meteo común",
            "biology_v3": "Biología base",
            "biology_v4": "Biología y balance hídrico",
            "biology_v5_raw_weather_discovery": "Meteo cruda regularizada",
            "biology_v6_smooth_hierarchical": "Curvas suaves y jerarquía",
        }.get(version_id, str(entry.get("version_display_name") or version_id))
        checked = (
            " checked"
            if (not selected_versions and not selected_tokens) or version_id in selected_version_set
            else ""
        )
        disabled = "" if any(
            isinstance(row, dict) and isinstance(row.get("artifact_ref"), dict)
            and row["artifact_ref"].get("version_id") == version_id
            and row["artifact_ref"].get("species_id") in {species_id, "all_species"}
            for row in artifacts
        ) else " disabled"
        version_rows.append(
            f'<label class="pred-version-choice"><input type="checkbox" name="mvv" '
            f'value="{html.escape(version_id, quote=True)}"{checked}{disabled}> '
            f'<strong>{html.escape(short)}</strong> '
            f'<span>{html.escape(compact_name)}</span></label>'
        )
    catalog_rows = "".join(
        f'<li><code>{html.escape(str(entry.get("version_display_name") or entry.get("version_id")))}</code> · '
        f'{html.escape(str(entry.get("profile_display_name") or entry.get("profile_id")))} · '
        f'{html.escape(_lbl("ui.predictor_multiversion_installed") if availability_by_profile.get((str(entry.get("version_id")), str(entry.get("profile_id")))) else _lbl("ui.predictor_multiversion_not_installed"))}</li>'
        for entry in entries
        if isinstance(entry, dict) and entry.get("catalog_visible")
    )
    return f"""
<div class="pred-multiversion-controls">
  <label>Versiones experimentales para comparar</label>
  <div class="pred-version-choices">{''.join(version_rows)}</div>
  <small>Se evaluarán todos los perfiles, contratos, horizontes y algoritmos disponibles de cada versión.</small>
  <details><summary>Detalle técnico y disponibilidad</summary><ul>{catalog_rows}</ul></details>
</div>
"""


def _multiversion_result(
    species_id: str,
    area_id: str,
    target_date: date,
    selected_tokens: list[str],
) -> dict[str, Any] | None:
    if not selected_tokens:
        return None
    prepared = _prepared_response.get()
    if prepared is not None:
        payload = (
            prepared.get("data", {})
            .get("species", {})
            .get(species_id, {})
            .get("multiversion_comparison")
        )
        return dict(payload) if isinstance(payload, dict) else None
    request_cache = _comparison_cache.get()
    registry = request_cache.get("registry") if request_cache is not None else None
    if not isinstance(registry, dict):
        registry = mushroom_ml_version_registry.load_registry(
            mushroom_paths.mushroom_ml_version_registry_path()
        )
        if request_cache is not None:
            request_cache["registry"] = registry
    manifest_path = mushroom_paths.mushroom_ml_runtime_batch_manifest_path()
    if not manifest_path.is_file():
        return {"available": False, "reason": "runtime_batch_not_installed"}
    selections = []
    for token in selected_tokens:
        parsed = mushroom_ml_model_catalog.parse_selection_token(token)
        parsed.pop("token", None)
        selections.append(parsed)
    manifest = request_cache.get("manifest") if request_cache is not None else None
    if not isinstance(manifest, dict):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if request_cache is not None:
            request_cache["manifest"] = manifest
    return {
        "available": True,
        **mushroom_ml_multiversion_comparison.compare_selection(
            registry,
            manifest,
            selections,
            species_id=species_id,
            area_id=area_id,
            target_date=target_date,
            models_root=mushroom_paths.mushroom_ml_models_dir(),
            known_sites_path=mushroom_paths.mushroom_known_sites_path(),
            weather_data_dir=mushroom_paths.weather_data_dir(),
            prepared_weather_cache=_prepared_weather_cache.get(),
            comparison_cache=request_cache,
        ),
    }


def _render_multiversion_result(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    if not payload.get("available"):
        return (
            f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_multiversion_unavailable"))}</div>'
        )
    members = [row for row in payload.get("members", []) if isinstance(row, dict)]
    version_names = {
        "altitude_v2": "V2", "biology_v3": "V3", "biology_v4": "V4",
        "biology_v5_raw_weather_discovery": "V5", "biology_v6_smooth_hierarchical": "V6",
    }
    cautions = payload.get("version_cautions") or {}
    by_version: dict[str, list[dict[str, Any]]] = {}
    for member in members:
        version_id = str((member.get("model_ref") or {}).get("version_id") or "")
        by_version.setdefault(version_id, []).append(member)

    weather_gate_codes = {
        "rain_coverage_below_19_of_21",
        "temperature_coverage_below_19_of_21",
        "humidity_coverage_below_19_of_21",
        "required_predictive_features_missing",
    }

    def unavailable_reason(member: dict[str, Any]) -> str:
        reason = str(member.get("reason") or "")
        quality = member.get("quality") or {}
        exclusions = quality.get("inference_exclusion_reasons") or []
        codes = {
            str(row.get("code") or "")
            for row in exclusions
            if isinstance(row, dict)
        }
        if reason == "runtime_feature_gates_failed" and codes & weather_gate_codes:
            cutoff = str((member.get("metadata") or {}).get("cutoff_date") or "")
            if cutoff:
                return _lbl("ui.predictor_multiversion_weather_pending_cutoff").format(
                    cutoff=cutoff
                )
            return _lbl("ui.predictor_multiversion_weather_pending")
        return reason or _lbl("ui.predictor_multiversion_unavailable")

    def confidence_tier(member: dict[str, Any]) -> str:
        if not member.get("available"):
            if unavailable_reason(member) != str(
                member.get("reason") or _lbl("ui.predictor_multiversion_unavailable")
            ):
                return "weather_pending"
            return "not_usable"
        prediction = member.get("prediction") or {}
        evaluation = member.get("evaluation") or {}
        applicability = str((prediction.get("applicability") or {}).get("status") or "")
        evidence = str(evaluation.get("evidence") or "not_evaluated")
        if applicability == "within_observed_range":
            return "usable" if evidence == "better_than_prevalence" else "weak"
        return "not_usable"

    tier_members: dict[str, list[dict[str, Any]]] = {
        "usable": [],
        "weak": [],
        "not_usable": [],
        "weather_pending": [],
    }
    for member in members:
        tier_members[confidence_tier(member)].append(member)

    summary_cards = []
    for tier, label_key, help_key in (
        ("usable", "ui.predictor_multiversion_summary_usable", "ui.predictor_multiversion_summary_usable_help"),
        ("weak", "ui.predictor_multiversion_summary_weak", "ui.predictor_multiversion_summary_weak_help"),
        ("not_usable", "ui.predictor_multiversion_summary_not_usable", "ui.predictor_multiversion_summary_not_usable_help"),
        ("weather_pending", "ui.predictor_multiversion_summary_weather_pending", "ui.predictor_multiversion_summary_weather_pending_help"),
    ):
        summary_cards.append(
            f'<article class="pred-confidence-card pred-confidence-{tier}">'
            f'<strong>{len(tier_members[tier])}</strong>'
            f'<span>{html.escape(_lbl(label_key))}</span>'
            f'<small>{html.escape(_lbl(help_key))}</small>'
            '</article>'
        )

    cards = []
    for version_id, version_members in by_version.items():
        available = [row for row in version_members if row.get("available")]
        probabilities = [
            float((row.get("prediction") or {}).get("probability"))
            for row in available
            if isinstance((row.get("prediction") or {}).get("probability"), (int, float))
        ]
        probability_range = (
            f"{round(min(probabilities) * 100)}%–{round(max(probabilities) * 100)}%"
            if probabilities else "—"
        )
        evaluations = [row.get("evaluation") or {} for row in available]
        better = sum(row.get("evidence") == "better_than_prevalence" for row in evaluations)
        worse = sum(row.get("evidence") == "worse_than_prevalence" for row in evaluations)
        insufficient = len(evaluations) - better - worse
        applicability = [
            str(((row.get("prediction") or {}).get("applicability") or {}).get("status") or "")
            for row in available
        ]
        outside = sum(value == "outside_domain" for value in applicability)
        role = (
            "Candidata experimental más antigua; no es preferida ni se presupone superior."
            if version_id == "altitude_v2"
            else "Candidata experimental; no promocionada ni descartada."
        )
        cards.append(f"""
<article class="pred-version-card">
  <h4>{html.escape(version_names.get(version_id, version_id))}</h4>
  <p class="pred-version-role">{html.escape(role)}</p>
  <dl><div><dt>Rango calculado</dt><dd>{html.escape(probability_range)}</dd></div>
  <div><dt>Miembros disponibles</dt><dd>{len(available)}/{len(version_members)}</dd></div>
  <div><dt>Hold-out frente a prevalencia</dt><dd>{better} mejores · {worse} peores · {insufficient} sin evidencia suficiente</dd></div>
  <div><dt>Fuera de dominio</dt><dd>{outside} miembros</dd></div></dl>
  <p class="pred-version-caution"><strong>Cautela:</strong> {html.escape(str(cautions.get(version_id) or "Todavía no hay evidencia suficiente para considerarla fiable."))}</p>
</article>""")

    evidence_labels = {
        "better_than_prevalence": "mejora",
        "worse_than_prevalence": "no mejora",
        "insufficient": "muestra insuficiente",
        "not_evaluated": "sin evaluación",
    }
    applicability_labels = {
        "within_observed_range": "en rango",
        "caution": "extrapolación leve",
        "outside_domain": "fuera de dominio",
    }
    breakdowns = []
    for version_id, version_members in by_version.items():
        estimator_ids = []
        grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = {}
        for member in version_members:
            ref = member.get("model_ref") or {}
            estimator_id = str(ref.get("estimator_id") or "")
            if estimator_id and estimator_id not in estimator_ids:
                estimator_ids.append(estimator_id)
            key = (
                str(ref.get("profile_id") or ""),
                str(ref.get("temporal_contract_id") or ""),
                int(ref.get("horizon_days") or 0),
            )
            grouped.setdefault(key, {})[estimator_id] = member
        estimator_ids.sort(
            key=lambda value: (
                list(_ESTIMATOR_SHORT_NAMES).index(value)
                if value in _ESTIMATOR_SHORT_NAMES else len(_ESTIMATOR_SHORT_NAMES),
                value,
            )
        )
        header = "".join(
            f'<th>{html.escape(_ESTIMATOR_SHORT_NAMES.get(estimator_id, estimator_id))}</th>'
            for estimator_id in estimator_ids
        )
        body_rows = []
        for (profile_id, contract_id, horizon), estimators in sorted(grouped.items()):
            contract_name = "Ventana fija" if contract_id.startswith("fixed_gap_") else "Retardo/evento"
            cells = []
            for estimator_id in estimator_ids:
                member = estimators.get(estimator_id)
                if not member or not member.get("available"):
                    reason = unavailable_reason(member or {})
                    cells.append(f'<td class="pred-member-unavailable">—<small>{html.escape(reason)}</small></td>')
                    continue
                prediction = member.get("prediction") or {}
                evaluation = member.get("evaluation") or {}
                evidence = evidence_labels.get(
                    str(evaluation.get("evidence") or "not_evaluated"), "sin evaluación"
                )
                delta = evaluation.get("brier_delta_vs_prevalence")
                delta_text = f" {float(delta):+.3f}" if isinstance(delta, (int, float)) else ""
                applicability = applicability_labels.get(
                    str((prediction.get("applicability") or {}).get("status") or ""), "sin dato de dominio"
                )
                cells.append(
                    '<td class="pred-member-result">'
                    f'<strong>{html.escape(_pct(prediction.get("probability")))}</strong>'
                    f'<small>hold-out: {html.escape(evidence + delta_text)}<br>{html.escape(applicability)}</small>'
                    '</td>'
                )
            body_rows.append(
                f'<tr><td>{html.escape(profile_id)}</td><td>{html.escape(contract_name)}</td>'
                f'<td>h{horizon}</td>{"".join(cells)}</tr>'
            )
        short_version = version_names.get(version_id, version_id)
        breakdowns.append(f"""
<details class="pred-version-breakdown">
  <summary>{html.escape(short_version)} · predicción por algoritmo ({len(version_members)} miembros)</summary>
  <div class="pred-table-scroll"><table class="pred-history-table"><thead><tr>
    <th>Perfil</th><th>Contrato</th><th>Horizonte</th>{header}
  </tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>
</details>""")

    scenario_groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for member in members:
        ref = member.get("model_ref") or {}
        contract = str(ref.get("temporal_contract_id") or "")
        family = "fixed" if contract.startswith("fixed_gap_") else "lag"
        scenario_groups.setdefault((family, int(ref.get("horizon_days") or 0)), []).append(member)
    rankings = []
    evidence_order = {"better_than_prevalence": 0, "worse_than_prevalence": 1,
                      "insufficient": 2, "not_evaluated": 3}
    for (family, horizon), scenario_members in sorted(scenario_groups.items()):
        ordered = sorted(
            scenario_members,
            key=lambda row: (
                evidence_order.get(str((row.get("evaluation") or {}).get("evidence") or "not_evaluated"), 4),
                -float((row.get("evaluation") or {}).get("brier_delta_vs_prevalence") or -999),
                float((row.get("evaluation") or {}).get("brier_score") or 999),
            ),
        )
        rank_rows = []
        for position, member in enumerate(ordered, start=1):
            ref = member.get("model_ref") or {}
            evaluation = member.get("evaluation") or {}
            prediction = member.get("prediction") or {}
            evidence = {
                "better_than_prevalence": "mejora la prevalencia",
                "worse_than_prevalence": "no mejora la prevalencia",
                "insufficient": "muestra insuficiente",
                "not_evaluated": "sin hold-out comparable",
            }.get(str(evaluation.get("evidence") or ""), "sin hold-out comparable")
            delta = evaluation.get("brier_delta_vs_prevalence")
            delta_text = f"{float(delta):+.3f}" if isinstance(delta, (int, float)) else "—"
            applicability = (prediction.get("applicability") or {}).get("status") or "—"
            applicability = {
                "within_observed_range": "dentro del rango observado",
                "caution": "extrapolación leve",
                "outside_domain": "fuera de dominio",
            }.get(str(applicability), str(applicability))
            identity = " / ".join((
                version_names.get(str(ref.get("version_id") or ""), str(ref.get("version_id") or "")),
                str(ref.get("profile_id") or ""),
                _ESTIMATOR_SHORT_NAMES.get(str(ref.get("estimator_id") or ""), str(ref.get("estimator_id") or "")),
            ))
            rank_rows.append(
                f"<tr><td>{position}</td><td>{html.escape(identity)}</td>"
                f"<td>{html.escape(_pct(prediction.get('probability')) if member.get('available') else '—')}</td>"
                f"<td>{html.escape(evidence)}</td><td>{html.escape(delta_text)}</td>"
                f"<td>{html.escape(str(evaluation.get('n_test') or '—'))}</td><td>{html.escape(str(applicability))}</td></tr>"
            )
        scenario_name = "ventana fija" if family == "fixed" else "retardo/evento"
        rankings.append(f"""
<details class="pred-ranking"><summary>Ranking diagnóstico: {scenario_name}, h{horizon}</summary>
<div class="pred-table-scroll"><table class="pred-history-table"><thead><tr>
<th>#</th><th>Miembro</th><th>Predicción actual</th><th>Evidencia hold-out</th>
<th>Mejora Brier vs prevalencia</th><th>n test</th><th>Aplicabilidad actual</th>
</tr></thead><tbody>{''.join(rank_rows)}</tbody></table></div></details>""")

    rows = []
    for member in members:
        if not isinstance(member, dict):
            continue
        ref = member.get("model_ref") or {}
        identity = " / ".join(
            str(ref.get(key) or "")
            for key in ("version_id", "profile_id", "estimator_id")
        )
        if member.get("available"):
            prediction = member.get("prediction") or {}
            probability = _pct(prediction.get("probability"))
            status = html.escape(_lbl("ui.predictor_multiversion_available"))
        else:
            probability = "—"
            status = html.escape(unavailable_reason(member))
        rows.append(
            f'<tr><td>{html.escape(identity)}</td><td>h{html.escape(str(ref.get("horizon_days") or ""))}</td>'
            f'<td>{html.escape(probability)}</td><td>{status}</td></tr>'
        )
    return f"""
<section class="pred-multiversion-result">
  <h3>Comparación experimental V2–V6</h3>
  <p>No hay ninguna versión validada, preferida o ganadora: V2–V6 tienen el mismo rango experimental. V2 aparece en la tarjeta superior únicamente porque fue la primera implementación conectada a ella; ese orden cronológico no le da prioridad estadística. Se ordena la calidad hold-out dentro de cada especie, contrato y horizonte; nunca se promedia el Brier entre especies ni se crea un ensemble.</p>
  <h4>{html.escape(_lbl("ui.predictor_multiversion_summary_title"))}</h4>
  <div class="pred-confidence-grid">{''.join(summary_cards)}</div>
  <div class="pred-version-grid">{''.join(cards)}</div>
  <h4>Predicción actual por versión, contrato y algoritmo</h4>
  <p>Cada celda muestra la predicción individual, su evidencia hold-out frente a la prevalencia de esa especie y si el escenario actual queda dentro del dominio observado.</p>
  <div class="pred-version-breakdowns">{''.join(breakdowns)}</div>
  <div class="pred-rankings">{''.join(rankings)}</div>
  <details><summary>Todos los miembros y sus resultados técnicos</summary>
  <div class="pred-table-scroll"><table class="pred-history-table"><thead><tr>
    <th>{html.escape(_lbl("ui.predictor_multiversion_model"))}</th><th>{html.escape(_lbl("ui.predictor_horizon"))}</th>
    <th>{html.escape(_lbl("ui.predictor_probability"))}</th><th>{html.escape(_lbl("ui.predictor_multiversion_status"))}</th>
  </tr></thead><tbody>{''.join(rows)}</tbody></table></div></details>
</section>
"""


def _interpretation(comparison: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(comparison, dict):
        return {}
    value = comparison.get("interpretation")
    return dict(value) if isinstance(value, dict) else {}


def _interpretation_label(interpretation: dict[str, Any]) -> str:
    verdict = str(interpretation.get("verdict", "abstain"))
    if verdict == "abstain":
        if interpretation.get("ecological_compatibility") == "compatible":
            return _lbl("ui.predictor_conditions_compatible_unconfirmed")
        unvalidated_signal = str(
            interpretation.get("unvalidated_signal", "unavailable")
        )
        return {
            "favorable": _lbl("ui.predictor_unvalidated_favorable_signal"),
            "unfavorable": _lbl("ui.predictor_unvalidated_unfavorable_signal"),
            "mixed": _lbl("ui.predictor_unvalidated_mixed_signal"),
        }.get(unvalidated_signal, _lbl("ui.predictor_interpretation_abstain"))
    return {
        "favorable": _lbl("ui.predictor_favorable"),
        "uncertain": _lbl("ui.predictor_uncertain"),
        "unfavorable": _lbl("ui.predictor_unfavorable"),
        "out_of_season": _lbl("ui.predictor_out_of_season"),
        "abstain": _lbl("ui.predictor_interpretation_abstain"),
    }.get(verdict, _lbl("ui.predictor_interpretation_abstain"))


def _interpretation_status(interpretation: dict[str, Any]) -> str:
    verdict = str(interpretation.get("verdict", "abstain"))
    if verdict == "abstain" and interpretation.get("unvalidated_signal") in {
        "favorable",
        "unfavorable",
        "mixed",
    }:
        return "uncertain"
    return verdict if verdict in {"favorable", "uncertain", "unfavorable", "out_of_season", "abstain"} else "abstain"


def _reference_range(interpretation: dict[str, Any]) -> str:
    value = interpretation.get("reference_range")
    if not isinstance(value, dict):
        return "—"
    minimum = value.get("min")
    maximum = value.get("max")
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        return "—"
    if round(float(minimum) * 100) == round(float(maximum) * 100):
        return _pct(float(minimum))
    return f"{_pct(float(minimum))}–{_pct(float(maximum))}"


def _probability_range(value: object) -> str:
    if not isinstance(value, dict):
        return "—"
    minimum = value.get("min")
    maximum = value.get("max")
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        return "—"
    if round(float(minimum) * 100) == round(float(maximum) * 100):
        return _pct(float(minimum))
    return f"{_pct(float(minimum))}–{_pct(float(maximum))}"


def _compact_interpretation_range(interpretation: dict[str, Any]) -> str:
    return _reference_range(interpretation)


def _interpretation_sort_key(interpretation: dict[str, Any]) -> tuple[int, float]:
    verdict = str(interpretation.get("verdict", "abstain"))
    rank = {"favorable": 5, "uncertain": 4, "unfavorable": 1, "abstain": 0}.get(verdict, 0)
    if verdict == "abstain":
        rank = 3 if interpretation.get("ecological_compatibility") == "compatible" else 0
    value = interpretation.get("reference_range")
    midpoint = value.get("midpoint") if isinstance(value, dict) else None
    return rank, float(midpoint) if isinstance(midpoint, (int, float)) else -1.0


def _render_interpretation_card(
    comparison: dict[str, Any],
    species_name: str,
    area_name: str,
    target_date: date,
) -> str:
    interpretation = _interpretation(comparison)
    status = _interpretation_status(interpretation)
    consensus = str(interpretation.get("statistical_consensus", "unavailable"))
    statistical_support = str(
        interpretation.get("statistical_support", "unavailable")
    )
    ecological_compatibility = str(
        interpretation.get("ecological_compatibility", "unknown")
    )
    ecological_evidence = str(
        interpretation.get("ecological_evidence", "low")
    )
    timing = str(interpretation.get("fruiting_timing", "unknown"))
    weather = str(interpretation.get("weather_signal", "unknown"))
    reason_codes = {
        str(value) for value in interpretation.get("reason_codes", [])
    }
    ecological_detail_keys: list[str] = []
    statistical_detail_keys: list[str] = []
    if weather in {"recent_event", "old_event", "no_event"}:
        ecological_detail_keys.append(f"ui.predictor_interpretation_weather_{weather}")
    ecological_rain_guardrail = "ecological_rain_guardrail" in reason_codes
    if timing != "unknown" and not (
        ecological_rain_guardrail and weather in {"old_event", "no_event"}
    ):
        ecological_detail_keys.append(f"ui.predictor_interpretation_timing_{timing}")
    if ecological_rain_guardrail:
        ecological_detail_keys.append("ui.predictor_interpretation_rain_guardrail")
    if "estimators_disagree" in reason_codes:
        statistical_detail_keys.append("ui.predictor_interpretation_disagreement")
    if "feature_sets_use_different_stations" in reason_codes:
        ecological_detail_keys.append("ui.predictor_interpretation_different_stations")
    if "no_estimator_beats_prevalence" in reason_codes:
        statistical_detail_keys.append("ui.predictor_interpretation_no_trusted_model")
    elif (
        "statistical_support_limited" in reason_codes
        and interpretation.get("validated_estimator_count") == 1
    ):
        statistical_detail_keys.append("ui.predictor_interpretation_limited_support")
    if "logistic_regression_excluded_out_of_domain" in reason_codes:
        statistical_detail_keys.append("ui.predictor_interpretation_lr_ood")
    if "feature_sets_conflict_extremely" in reason_codes:
        statistical_detail_keys.append("ui.predictor_interpretation_extreme_conflict")
    if "unvalidated_favorable_signal" in reason_codes:
        statistical_detail_keys.append("ui.predictor_interpretation_unvalidated_favorable")
    elif "unvalidated_unfavorable_signal" in reason_codes:
        statistical_detail_keys.append("ui.predictor_interpretation_unvalidated_unfavorable")
    elif "unvalidated_signal_not_interpretable" in reason_codes:
        statistical_detail_keys.append("ui.predictor_interpretation_unvalidated_mixed")
    comparison_model_ids = tuple(comparison.get("operational_result_keys") or ()) or (
        ("fixed_gap_7d_altitude_v2", "lag_event_altitude_v2")
        if any(
            model_id in comparison
            for model_id in ("fixed_gap_7d_altitude_v2", "lag_event_altitude_v2")
        )
        else ("fixed_gap_7d_v1", "lag_event_v1")
    )
    historical_rows = [
        result.get("historical_evaluation")
        for model_id in comparison_model_ids
        if isinstance((result := comparison.get(model_id)), dict)
        and isinstance(result.get("historical_evaluation"), dict)
    ]
    if historical_rows and any(row.get("out_of_sample") for row in historical_rows):
        statistical_detail_keys.append("ui.predictor_historical_held_out")
    elif historical_rows:
        statistical_detail_keys.append("ui.predictor_historical_included_in_fit")
    ecological_details = " ".join(
        html.escape(_lbl(key)) for key in ecological_detail_keys
    )
    statistical_details = " ".join(
        html.escape(_lbl(key)) for key in statistical_detail_keys
    )
    details_html = "".join(
        f'<p class="pred-interpretation-detail">{details}</p>'
        for details in (ecological_details, statistical_details)
        if details
    )
    range_html = ""
    if interpretation.get("reference_range"):
        range_html = (
            f'<div class="pred-interpretation-range">'
            f'<span>{html.escape(_lbl("ui.predictor_operational_range"))}</span>'
            f'<strong>{html.escape(_reference_range(interpretation))}</strong>'
            f'</div>'
        )
    consensus_html = ""
    if consensus != "unavailable":
        consensus_html = (
            f'<span>{_tooltip_label_key("ui.predictor_consensus", "ui.predictor_help_consensus")}: '
            f'{html.escape(_lbl(f"ui.predictor_consensus_{consensus}"))}</span>'
        )
    return f"""
<section class="pred-interpretation-card {_status_cls(status)}">
  <div class="pred-result-header">
    <span class="pred-result-dot">{_status_dot(status)}</span>
    <span class="pred-result-species">{html.escape(species_name)}</span>
    <span class="pred-result-area">{html.escape(area_name)}</span>
    <span class="pred-result-date">{html.escape(target_date.strftime("%-d %b %Y"))}</span>
  </div>
  <div class="pred-interpretation-title">{html.escape(_interpretation_label(interpretation))}</div>
  {range_html}
  <p class="pred-version-role">{html.escape(_lbl("ui.predictor_active_version_role"))}</p>
  <div class="pred-interpretation-meta">
    <span>{_tooltip_label_key("ui.predictor_ecological_compatibility", "ui.predictor_help_ecological_compatibility")}: {html.escape(_lbl(f"ui.predictor_ecological_compatibility_{ecological_compatibility}"))}</span>
    <span>{_tooltip_label_key("ui.predictor_ecological_evidence", "ui.predictor_help_ecological_reliability")}: {html.escape(_lbl(f"ui.predictor_ecological_evidence_{ecological_evidence}"))}</span>
    <span>{_tooltip_label_key("ui.predictor_statistical_support", "ui.predictor_help_statistical_support")}: {html.escape(_lbl(f"ui.predictor_statistical_support_{statistical_support}"))}</span>
    {consensus_html}
  </div>
  {details_html}
</section>
"""


# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------

def _render_tabs(
    view: str,
    species: str,
    target_date: date,
) -> str:
    def tab(key: str, v: str, extra_params: str = "") -> str:
        tab_date = date.today() if v in {"recommender", "week"} else target_date
        href = _url(v, species, target_date=tab_date)
        cls = "pred-tab pred-tab-active" if view == v else "pred-tab"
        return (
            f'<a class="{cls}" href="{html.escape(href)}" '
            f'data-predictor-direct-run>{html.escape(_lbl(key))}</a>'
        )

    return f"""
<nav class="pred-tabs">
  {tab("ui.predictor_tab_recommender", "recommender")}
  {tab("ui.predictor_tab_week", "week")}
  {tab("ui.predictor_tab_query", "query")}
  {tab("ui.predictor_tab_history", "history")}
</nav>
"""


def normalize_predictor_target_date(
    view: str,
    target_date: date,
    *,
    today: date | None = None,
) -> date:
    """Keep current-week views inside the dates that they actually display."""
    current = today or date.today()
    if view not in {"recommender", "week"}:
        return target_date
    offset = (target_date - current).days
    return target_date if 0 <= offset <= 6 else current


# ---------------------------------------------------------------------------
# Day strip (shared between recommender and week)
# ---------------------------------------------------------------------------

def _render_day_strip(target_date: date, view: str, species: str) -> str:
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]
    cells = []
    for d in days:
        href = _url(view, species, target_date=d)
        is_active = d == target_date
        cls = "pred-day pred-day-active" if is_active else "pred-day"
        day_name = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][d.weekday()]
        label_text = f"{day_name}<br><strong>{d.day}/{d.month}</strong>"
        cells.append(
            f'<a class="{cls}" href="{html.escape(href)}">'
            f'{label_text}'
            f'</a>'
        )
    return '<div class="pred-day-strip">' + "".join(cells) + "</div>"


# ---------------------------------------------------------------------------
# Recommender view
# ---------------------------------------------------------------------------

def _render_recommender(
    target_date: date,
    trained: list[str],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    today = date.today()
    day_strip = _render_day_strip(target_date, "recommender", "")

    all_results: list[tuple[dict[str, Any], str, str]] = []
    errors = []
    for species_id in trained:
        try:
            predictor = _get_predictor(species_id)
            if predictor.season_phase(target_date) == "out_of_season":
                continue
            for area_id in predictor.areas_with_species_observations():
                comparison = _model_comparison(species_id, area_id, target_date)
                interpretation = _interpretation(comparison)
                if interpretation:
                    all_results.append((interpretation, species_id, area_id))
        except FileNotFoundError:
            pass
        except Exception as exc:
            errors.append(f"{species_id}: {html.escape(_predictor_error_text(exc))}")

    all_results.sort(key=lambda row: _interpretation_sort_key(row[0]), reverse=True)

    date_label = (
        "Hoy" if target_date == today
        else "Mañana" if target_date == today + timedelta(days=1)
        else f"{target_date.day}/{target_date.month}/{target_date.year}"
    )

    if not all_results:
        no_data = f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_no_data"))}</div>'
        error_block = _render_errors(errors)
        return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_recommender"))} — {html.escape(date_label)}</h2>
  {day_strip}
  {error_block}
  {no_data}
</section>
"""

    # Best bet card
    best_interpretation, best_species, best_area = all_results[0]
    best_species_name = _species_name(best_species, profiles_payload)
    best_area_name = _area_name(best_area, known_sites_payload)
    best_status = _interpretation_status(best_interpretation)
    best_badge = (
        _lbl("ui.predictor_best_bet")
        if best_interpretation.get("verdict") == "favorable"
        else _lbl("ui.predictor_best_available_signal")
    )
    best_card = f"""
<div class="pred-best-card {_status_cls(best_status)}">
  <div class="pred-best-badge">{html.escape(best_badge)}</div>
  <div class="pred-best-name">{_status_dot(best_status)} {html.escape(best_species_name)}</div>
  <div class="pred-best-area">{html.escape(best_area_name)}</div>
  <div class="pred-best-prob">{html.escape(_compact_interpretation_range(best_interpretation))}</div>
  <div class="pred-best-hint">{html.escape(_interpretation_label(best_interpretation))}</div>
</div>
"""

    # Ranked list
    rows_html = ""
    for interpretation, sp_id, area_id in all_results[:15]:
        sp_name = _species_name(sp_id, profiles_payload)
        area_n = _area_name(area_id, known_sites_payload)
        href = _url("query", sp_id, area_id, target_date)
        status = _interpretation_status(interpretation)
        rows_html += f"""
<a class="pred-rank-row {_status_cls(status)}" href="{html.escape(href)}">
  <span class="pred-rank-dot">{_status_dot(status)}</span>
  <span class="pred-rank-species">{html.escape(sp_name)}</span>
  <span class="pred-rank-area">{html.escape(area_n)}</span>
  <span class="pred-rank-prob">{html.escape(_compact_interpretation_range(interpretation))}</span>
</a>
"""

    error_block = _render_errors(errors)
    return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_recommender"))} — {html.escape(date_label)}</h2>
  {day_strip}
  {error_block}
  {best_card}
  <h3>{html.escape(_lbl("ui.predictor_all_areas"))}</h3>
  <div class="pred-rank-list">
    <div class="pred-rank-header">
      <span></span>
      <span>{html.escape(_lbl("ui.species"))}</span>
      <span>{html.escape(_lbl("ui.known_site_area"))}</span>
      <span>{html.escape(_lbl("ui.predictor_reference_range"))}</span>
    </div>
    {rows_html}
  </div>
</section>
"""


def _label_hint(label: str) -> str:
    if label == "out_of_season":
        return _lbl("ui.predictor_hint_out_of_season")
    if label == "favorable":
        return _lbl("ui.predictor_hint_favorable")
    if label == "uncertain":
        return _lbl("ui.predictor_hint_uncertain")
    return _lbl("ui.predictor_hint_unfavorable")


# ---------------------------------------------------------------------------
# Week view
# ---------------------------------------------------------------------------

def _render_week(
    species: str,
    target_date: date,
    trained: list[str],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]

    # Species chips
    chips = ""
    for sp_id in trained:
        sp_name = _species_name(sp_id, profiles_payload)
        href = _url("week", sp_id, target_date=target_date)
        cls = "pred-chip pred-chip-active" if sp_id == species else "pred-chip"
        chips += f'<a class="{cls}" href="{html.escape(href)}">{html.escape(sp_name)}</a>'

    try:
        predictor = _get_predictor(species)
        area_ids = predictor.areas_with_species_observations()
    except FileNotFoundError:
        area_ids = []
    except Exception as exc:
        return f'<div class="pred-error"><strong>Error:</strong> {html.escape(_predictor_error_text(exc))}</div>'

    if not area_ids:
        return f"""
<section class="pred-section">
  <div class="pred-chips">{chips}</div>
  <div class="pred-empty">{html.escape(_lbl("ui.predictor_no_data"))}</div>
</section>
"""

    prepared_weather_cache = _prepared_weather_cache.get()
    if _prepared_response.get() is None and prepared_weather_cache is not None:
        stations_file = Path("/app/stations.txt")
        excluded_station_keys = (
            mushroom_weather_idw.disabled_wunderground_station_keys(stations_file)
            if stations_file.is_file()
            else frozenset()
        )
        mushroom_ml_multiversion_comparison.prewarm_v2_week_weather(
            area_ids=area_ids,
            target_issue_dates=[(day, min(today, day)) for day in days],
            known_sites_path=mushroom_paths.mushroom_known_sites_path(),
            weather_data_dir=mushroom_paths.weather_data_dir(),
            excluded_station_keys=excluded_station_keys,
            prepared_weather_cache=prepared_weather_cache,
        )

    sp_name = _species_name(species, profiles_payload)
    bt = _get_species_backtest_stats(species)
    by_area_bt = bt.get("by_area", {}) if bt else {}

    # Species-level reliability strip
    if bt and "total_episodes" in bt:
        total_ep = bt["total_episodes"]
        reliability_html = (
            f'<div class="pred-reliability-strip">'
            f'<span class="pred-rel-label">{html.escape(_lbl("ui.predictor_reliability"))}</span>'
            f'<span class="pred-rel-episodes">{total_ep} {html.escape(_lbl("ui.predictor_stat_episodes")).lower()}</span>'
            f'</div>'
        )
    else:
        reliability_html = ""

    # Day header
    day_headers = ""
    for d in days:
        day_name = ["L", "M", "X", "J", "V", "S", "D"][d.weekday()]
        is_today = d == today
        day_headers += f'<th class="{"pred-today-col" if is_today else ""}">{day_name}<br><small>{d.day}/{d.month}</small></th>'

    # Grid rows
    rows_html = ""
    for area_id in sorted(area_ids):
        area_n = _area_name(area_id, known_sites_payload)
        area_bt = by_area_bt.get(area_id, {})
        ep_n = area_bt.get("episodes", 0) if area_bt else 0
        area_acc = area_bt.get("backtest_accuracy") if area_bt else None
        rel_cell = f'<td class="pred-rel-cell">{_rel_badge(ep_n)}</td>'
        row_cells = f'<td class="pred-area-cell">{html.escape(area_n)}</td>{rel_cell}'
        for d in days:
            try:
                comparison = _model_comparison(species, area_id, d)
                interpretation = _interpretation(comparison)
                status = _interpretation_status(interpretation)
                cell_href = _url("query", species, area_id, d)
                row_cells += (
                    f'<td class="pred-cell {_status_cls(status)}">'
                    f'<a href="{html.escape(cell_href)}">'
                    f'{_status_dot(status)} {html.escape(_compact_interpretation_range(interpretation))}'
                    f'</a></td>'
                )
            except WeatherParquetLayoutError as exc:
                return (
                    '<section class="pred-section">'
                    f'<div class="pred-chips">{chips}</div>'
                    f'<div class="pred-error">{html.escape(_predictor_error_text(exc))}</div>'
                    '</section>'
                )
            except Exception:
                row_cells += '<td class="pred-cell">—</td>'
        rows_html += f"<tr>{row_cells}</tr>"

    return f"""
<section class="pred-section">
  <div class="pred-chips">{chips}</div>
  <h2>{html.escape(sp_name)}</h2>
  {reliability_html}
  <div class="pred-table-scroll">
    <table class="pred-week-table">
      <thead>
        <tr>
          <th>{html.escape(_lbl("ui.known_site_area"))}</th>
          <th class="pred-rel-header">{html.escape(_lbl("ui.predictor_reliability"))}</th>
          {day_headers}
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>
  <div class="pred-legends-row">
    {_rel_legend_html()}
    <p class="pred-hint-legend pred-hint-legend-right">
      🟢 {html.escape(_lbl("ui.predictor_favorable"))} &nbsp;
      🟡 {html.escape(_lbl("ui.predictor_uncertain"))} &nbsp;
      🔴 {html.escape(_lbl("ui.predictor_unfavorable"))} &nbsp;
      ⚪ {html.escape(_lbl("ui.predictor_out_of_season"))}
    </p>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Query view
# ---------------------------------------------------------------------------

def _render_query(
    species: str,
    area: str,
    target_date: date,
    trained: list[str],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
    compare_models: bool = True,
    selected_multiversion: list[str] | None = None,
    selected_versions: list[str] | None = None,
) -> str:
    selected_multiversion = list(selected_multiversion or [])
    selected_versions = list(selected_versions or [])
    # Area options for selected species
    area_options_html = f'<option value="">{html.escape(_lbl("ui.predictor_all_areas_option"))}</option>'
    try:
        predictor = _get_predictor(species)
        area_ids = predictor.areas_with_species_observations()
        areas = known_sites_payload.get("areas", []) if isinstance(known_sites_payload, dict) else []
        for a_id in sorted(area_ids):
            a_name = _area_name(a_id, known_sites_payload)
            sel = ' selected' if a_id == area else ''
            area_options_html += f'<option value="{html.escape(a_id)}"{sel}>{html.escape(a_name)}</option>'
    except Exception:
        pass

    # Species options
    species_options_html = ""
    for sp_id in trained:
        sp_name = _species_name(sp_id, profiles_payload)
        sel = ' selected' if sp_id == species else ''
        species_options_html += f'<option value="{html.escape(sp_id)}"{sel}>{html.escape(sp_name)}</option>'

    comparison_toggle = (
        f'<a class="button-link secondary-link" href="{html.escape(_url("query", species, area, target_date, compare="0" if compare_models else "1"))}">'
        f'{html.escape(_lbl("ui.predictor_hide_model_comparison") if compare_models else _lbl("ui.predictor_compare_models"))}'
        "</a>"
        if area
        else ""
    )
    multiversion_controls = (
        _multiversion_controls(species, selected_multiversion, selected_versions)
        if compare_models and area
        else ""
    )
    form_html = f"""
<form class="pred-form" method="get" action="" data-predictor-direct-form>
  <input type="hidden" name="view" value="query">
  <input type="hidden" name="compare" value="{1 if compare_models else 0}">
  {_executor_hidden_input()}
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.species"))}</label>
    <select name="species" onchange="this.form.elements.area.value='';this.form.requestSubmit()">{species_options_html}</select>
  </div>
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.known_site_area"))}</label>
    <select name="area" onchange="this.form.requestSubmit()">{area_options_html}</select>
  </div>
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.date_short"))}</label>
    <input type="date" name="date" value="{html.escape(target_date.isoformat())}">
  </div>
  {multiversion_controls}
  <button type="submit" class="primary">{html.escape(_lbl("ui.predictor_query_submit"))}</button>
  {comparison_toggle}
</form>
"""

    result_html = ""
    if area:
        result_html = _render_query_result(
            species,
            area,
            target_date,
            profiles_payload,
            known_sites_payload,
            compare_models=compare_models,
            selected_multiversion=selected_multiversion,
        )
    elif species:
        # Show all areas for the species
        result_html = _render_query_all_areas(species, target_date, profiles_payload, known_sites_payload)

    return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_query"))}</h2>
  {form_html}
  {result_html}
</section>
"""


def _render_query_result(
    species: str,
    area: str,
    target_date: date,
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
    *,
    compare_models: bool = False,
    selected_multiversion: list[str] | None = None,
) -> str:
    selected_multiversion = list(selected_multiversion or [])
    try:
        comparison = _model_comparison(species, area, target_date)
    except FileNotFoundError as exc:
        return f'<div class="pred-error">{html.escape(str(exc))}</div>'
    except Exception as exc:
        return f'<div class="pred-error"><strong>Error:</strong> {html.escape(_predictor_error_text(exc))}</div>'
    if not comparison:
        return f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_comparison_unavailable"))}</div>'

    sp_name = _species_name(species, profiles_payload)
    area_n = _area_name(area, known_sites_payload)
    interpretation_card = _render_interpretation_card(
        comparison, sp_name, area_n, target_date
    )

    # 7-day strip for this area
    week_cells = ""
    try:
        today = date.today()
        current_week = {today + timedelta(days=offset) for offset in range(7)}
        week_start = today if target_date in current_week else target_date
        for offset in range(7):
            current_date = week_start + timedelta(days=offset)
            current_comparison = _model_comparison(species, area, current_date)
            current_interpretation = _interpretation(current_comparison)
            status = _interpretation_status(current_interpretation)
            is_active = current_date == target_date
            day_name = ["L", "M", "X", "J", "V", "S", "D"][current_date.weekday()]
            href = _url(
                "query",
                species,
                area,
                current_date,
                compare="1" if compare_models else "",
            )
            cls = "pred-week-cell pred-week-active" if is_active else "pred-week-cell"
            week_cells += f"""
<a class="{cls} {_status_cls(status)}" href="{html.escape(href)}">
  <small>{day_name} {current_date.day}/{current_date.month}</small>
  <span>{_status_dot(status)}</span>
  <small>{html.escape(_compact_interpretation_range(current_interpretation))}</small>
</a>
"""
    except Exception:
        pass

    week_strip = f'<div class="pred-week-strip">{week_cells}</div>' if week_cells else ""

    comparison_html = _render_model_comparison(species, area, target_date) if compare_models else ""
    multiversion_html = ""
    if compare_models and selected_multiversion:
        try:
            multiversion_html = _render_multiversion_result(
                _multiversion_result(
                    species, area, target_date, selected_multiversion
                )
            )
        except Exception as exc:
            multiversion_html = (
                f'<div class="pred-error">{html.escape(_predictor_error_text(exc))}</div>'
            )

    return f"""
{interpretation_card}
{week_strip}
{comparison_html}
{multiversion_html}
"""


def _comparison_value(value: object, suffix: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        rendered = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        rendered = str(value)
    return f"{rendered}{suffix}"


def _out_of_domain_feature_unit(feature: str) -> str:
    if feature.endswith("_mm"):
        return " mm"
    if feature.endswith("_c"):
        return " °C"
    if feature.endswith("_pct"):
        return " %"
    if feature == "gis_altitude_m":
        return " m"
    if "days" in feature or feature in {
        "dry_spell_observed_at_cutoff",
        "heat_stress_observed_at_cutoff",
    }:
        return " d"
    return ""


def _out_of_domain_feature_label(feature: str) -> str:
    label_key = _OUT_OF_DOMAIN_FEATURE_LABEL_KEYS.get(feature)
    if label_key:
        return _lbl(label_key)
    return feature.replace("_", " ").strip().capitalize()


def _out_of_domain_feature_value(
    detail: dict[str, Any], *, severe_features: set[str]
) -> str:
    feature = str(detail.get("feature", "") or "")
    unit = _out_of_domain_feature_unit(feature)
    value = _comparison_value(detail.get("value"), unit)
    minimum = _comparison_value(detail.get("training_min"), unit)
    maximum = _comparison_value(detail.get("training_max"), unit)
    rendered = (
        f"{_out_of_domain_feature_label(feature)}: {value} · "
        f'{_lbl("ui.predictor_training_range")} {minimum}–{maximum}'
    )
    try:
        numeric_value = float(detail.get("value"))
        numeric_minimum = float(detail.get("training_min"))
        numeric_maximum = float(detail.get("training_max"))
    except (TypeError, ValueError):
        delta = None
    else:
        if numeric_value < numeric_minimum:
            delta = numeric_value - numeric_minimum
        elif numeric_value > numeric_maximum:
            delta = numeric_value - numeric_maximum
        else:
            delta = None
    if delta is not None:
        rendered_delta = _comparison_value(delta, unit)
        if delta > 0:
            rendered_delta = f"+{rendered_delta}"
        rendered += f' · {_lbl("ui.predictor_out_of_domain_delta")} {rendered_delta}'
    deviations = detail.get("standard_deviations_from_mean")
    if deviations is not None:
        rendered += f" · {_comparison_value(deviations)} σ"
    if feature in severe_features:
        rendered += f' · {_lbl("ui.predictor_out_of_domain_severe")}'
    return rendered


def _render_model_diagnostics(result: dict[str, Any]) -> str:
    features = result.get("features_used")
    features = features if isinstance(features, dict) else {}
    selection = result.get("station_selection")
    selection = selection if isinstance(selection, dict) else {}
    quality = selection.get("selected_station_quality")
    quality = quality if isinstance(quality, dict) else {}

    facts: list[tuple[str, str]] = []

    probability_source = result.get("probability_source")
    if probability_source:
        facts.append(
            (
                _lbl("ui.predictor_probability_source"),
                _lbl(f"ui.predictor_probability_source_{probability_source}"),
            )
        )
    historical = result.get("historical_evaluation")
    historical = historical if isinstance(historical, dict) else {}
    if historical.get("prediction_target"):
        facts.append(
            (
                _lbl("ui.predictor_observed_result"),
                _lbl(
                    "ui.predictor_favorable"
                    if historical.get("prediction_target") == "favorable"
                    else "ui.predictor_unfavorable"
                ),
            )
        )

    evaluation = result.get("evaluation")
    evaluation = evaluation if isinstance(evaluation, dict) else {}
    baseline = evaluation.get("baseline")
    baseline = baseline if isinstance(baseline, dict) else {}
    estimator_metrics = evaluation.get("estimators")
    estimator_metrics = estimator_metrics if isinstance(estimator_metrics, dict) else {}
    estimator_availability = result.get("estimator_availability")
    estimator_availability = (
        estimator_availability if isinstance(estimator_availability, dict) else {}
    )
    for estimator_id, short_name, _is_shadow in _COMPARISON_ESTIMATORS:
        availability = estimator_availability.get(estimator_id)
        availability = availability if isinstance(availability, dict) else {}
        if availability.get("available") is False and availability.get("reason"):
            reason = str(availability["reason"])
            value = (
                _lbl("ui.predictor_estimator_calibration_insufficient_classes")
                if reason.startswith("calibration requires")
                else reason
            )
            facts.append((short_name, value))
    if baseline.get("brier_score") is not None:
        estimator_briers = " · ".join(
            f'{short_name} {_comparison_value(dict(estimator_metrics.get(estimator_id, {})).get("brier_score"))}'
            for estimator_id, short_name, _is_shadow in _COMPARISON_ESTIMATORS
            if estimator_id in estimator_metrics
        )
        facts.append(
            (
                _lbl("ui.predictor_validation_brier"),
                (
                    f'{_lbl("ui.predictor_validation_baseline")} '
                    f'{_comparison_value(baseline.get("brier_score"))}'
                    f'{" · " + estimator_briers if estimator_briers else ""}'
                ),
            )
        )
    estimator_aucs = " · ".join(
        f'{short_name} {_comparison_value(dict(estimator_metrics.get(estimator_id, {})).get("roc_auc"))}'
        for estimator_id, short_name, _is_shadow in _COMPARISON_ESTIMATORS
        if dict(estimator_metrics.get(estimator_id, {})).get("roc_auc") is not None
    )
    if estimator_aucs:
        facts.append(
            (
                _lbl("ui.predictor_validation_auc"),
                estimator_aucs,
            )
        )

    temporal_validation = result.get("temporal_validation")
    if (
        isinstance(temporal_validation, dict)
        and temporal_validation.get("available") is False
    ):
        facts.append(
            (
                _lbl("ui.predictor_temporal_validation"),
                _lbl("ui.predictor_temporal_validation_unavailable"),
            )
        )

    def add(label_key: str, value: object, suffix: str = "") -> None:
        if value is not None:
            facts.append((_lbl(label_key), _comparison_value(value, suffix)))

    add("ui.station", result.get("weather_station_code"))
    add("ui.predictor_station_distance", result.get("weather_station_distance_km"), " km")
    add(
        "ui.predictor_station_altitude",
        result.get("weather_station_altitude_m"),
        " m",
    )
    add(
        "ui.predictor_area_representative_altitude",
        result.get("area_representative_altitude_m"),
        " m",
    )
    correction = result.get("temperature_altitude_correction_c")
    if correction is not None:
        rendered_correction = _comparison_value(correction, " °C")
        try:
            if float(correction) > 0:
                rendered_correction = f"+{rendered_correction}"
        except (TypeError, ValueError):
            pass
        lapse_rate = result.get("temperature_lapse_rate_c_per_100m")
        if lapse_rate is not None:
            rendered_correction += (
                f" · {_comparison_value(lapse_rate, ' °C/100 m')}"
            )
        facts.append(
            (
                _lbl("ui.predictor_temperature_altitude_correction"),
                rendered_correction,
            )
        )
    add("ui.predictor_horizon", result.get("horizon_days"), " d")
    if quality:
        facts.append(
            (
                _lbl("ui.predictor_station_quality"),
                (
                    f'{quality.get("rain_days_21", "—")}/21 · '
                    f'{quality.get("rain_days_90", "—")}/90 · '
                    f'T {quality.get("temperature_days_21", "—")}/21 · '
                    f'H {quality.get("humidity_days_21", "—")}/21'
                ),
            )
        )
    elif result.get("weather_coverage_days") is not None:
        add("ui.predictor_coverage", result.get("weather_coverage_days"), " d")
    skipped = selection.get("skipped_nearer_station_count")
    if isinstance(skipped, int) and skipped > 0:
        facts.append(
            (
                _lbl("ui.predictor_station_jump"),
                _lbl("ui.predictor_station_jump_value").format(
                    count=skipped,
                    station=selection.get("nearest_station_code") or "—",
                ),
            )
        )

    rain_bands = (
        features.get("rain_cutoff_0_3d_mm"),
        features.get("rain_cutoff_4_7d_mm"),
        features.get("rain_cutoff_8_14d_mm"),
        features.get("rain_cutoff_15_21d_mm"),
    )
    if any(value is not None for value in rain_bands):
        facts.append(
            (
                _lbl("ui.predictor_rain_bands"),
                " · ".join(_comparison_value(value, " mm") for value in rain_bands),
            )
        )
    add(
        "ui.predictor_days_since_rain",
        features.get("days_since_rain_gt_2_at_target"),
        " d",
    )
    add(
        "ui.predictor_days_since_significant_rain",
        features.get("days_since_significant_rain_at_target"),
        " d",
    )
    if features.get("rain_observed_days_21") is not None:
        facts.append(
            (
                _lbl("ui.predictor_rain_coverage_21"),
                f'{_comparison_value(features.get("rain_observed_days_21"))} / '
                f'{_comparison_value(features.get("rain_missing_days_21"))} / '
                f'{_comparison_value(features.get("rain_suppressed_days_21"))}',
            )
        )
    if features.get("rain_observed_days_90") is not None:
        facts.append(
            (
                _lbl("ui.predictor_rain_coverage_90"),
                f'{_comparison_value(features.get("rain_observed_days_90"))} / '
                f'{_comparison_value(features.get("rain_missing_days_90"))} / '
                f'{_comparison_value(features.get("rain_suppressed_days_90"))}',
            )
        )
    temp_days = features.get("temp_observed_days_after_significant_rain")
    humidity_days = features.get("humidity_observed_days_after_significant_rain")
    if temp_days is not None or humidity_days is not None:
        facts.append(
            (
                _lbl("ui.predictor_post_rain_coverage"),
                f'T {_comparison_value(temp_days)} d · H {_comparison_value(humidity_days)} d',
            )
        )
    gaps = result.get("feature_gaps")
    if isinstance(gaps, list) and gaps:
        facts.append((_lbl("ui.weather_gaps"), ", ".join(str(value) for value in gaps)))
    out_of_domain = result.get("out_of_domain_features")
    out_of_domain = out_of_domain if isinstance(out_of_domain, list) else []
    severe_ood = result.get("severe_out_of_domain_features")
    severe_ood = severe_ood if isinstance(severe_ood, list) else []
    severe_features = {
        str(row.get("feature"))
        for row in severe_ood
        if isinstance(row, dict) and row.get("feature")
    }
    visible_ood = out_of_domain or severe_ood
    if visible_ood:
        facts.append(
            (
                _lbl("ui.predictor_out_of_domain_features"),
                "; ".join(
                    _out_of_domain_feature_value(row, severe_features=severe_features)
                    for row in visible_ood
                    if isinstance(row, dict) and row.get("feature")
                ),
            )
        )

    if not facts:
        return ""
    help_by_label = {
        _lbl("ui.predictor_probability_source"): "ui.predictor_help_probability_source",
        _lbl("ui.predictor_observed_result"): "ui.predictor_help_observed_result",
        _lbl("ui.predictor_validation_brier"): "ui.predictor_help_brier",
        _lbl("ui.predictor_validation_auc"): "ui.predictor_help_roc_auc",
        _lbl("ui.predictor_temporal_validation"): "ui.predictor_help_temporal_validation",
        _lbl("ui.station"): "ui.predictor_help_station",
        _lbl("ui.predictor_station_distance"): "ui.predictor_help_station_distance",
        _lbl("ui.predictor_station_altitude"): "ui.predictor_help_station_altitude",
        _lbl("ui.predictor_area_representative_altitude"): "ui.predictor_help_area_representative_altitude",
        _lbl("ui.predictor_temperature_altitude_correction"): "ui.predictor_help_temperature_altitude_correction",
        _lbl("ui.predictor_horizon"): "ui.predictor_help_horizon",
        _lbl("ui.predictor_station_quality"): "ui.predictor_help_station_quality",
        _lbl("ui.predictor_coverage"): "ui.predictor_help_coverage",
        _lbl("ui.predictor_station_jump"): "ui.predictor_help_station_jump",
        _lbl("ui.predictor_rain_bands"): "ui.predictor_help_rain_bands",
        _lbl("ui.predictor_days_since_rain"): "ui.predictor_help_days_since_rain",
        _lbl("ui.predictor_days_since_significant_rain"): "ui.predictor_help_days_since_significant_rain",
        _lbl("ui.predictor_rain_coverage_21"): "ui.predictor_help_rain_coverage",
        _lbl("ui.predictor_rain_coverage_90"): "ui.predictor_help_rain_coverage",
        _lbl("ui.predictor_post_rain_coverage"): "ui.predictor_help_post_rain_coverage",
        _lbl("ui.weather_gaps"): "ui.predictor_help_weather_gaps",
        _lbl("ui.predictor_out_of_domain_features"): "ui.predictor_help_out_of_domain",
        **{
            short_name: _ESTIMATOR_HELP_KEYS[estimator_id]
            for estimator_id, short_name, _is_shadow in _COMPARISON_ESTIMATORS
        },
    }
    items = "".join(
        f'<span>{_tooltip_label(label, help_by_label[label])}: {html.escape(value)}</span>'
        for label, value in facts
    )
    return f'<div class="pred-comparison-diagnostics">{items}</div>'


def _render_model_comparison(species: str, area: str, target_date: date) -> str:
    try:
        comparison = _model_comparison(species, area, target_date)
    except Exception as exc:
        return f'<div class="pred-error">{html.escape(_predictor_error_text(exc))}</div>'
    if not comparison:
        return f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_comparison_unavailable"))}</div>'

    labels = {
        "fixed_gap_7d_v1": _lbl("ui.predictor_model_fixed_gap_7d_v1"),
        "lag_event_v1": _lbl("ui.predictor_model_lag_event_v1"),
        "fixed_gap_7d_altitude_v2": _lbl("ui.predictor_model_fixed_gap_7d_v1"),
        "lag_event_altitude_v2": _lbl("ui.predictor_model_lag_event_v1"),
    }
    rows = ""
    model_ids = tuple(comparison.get("operational_result_keys") or ()) or (
        ("fixed_gap_7d_altitude_v2", "lag_event_altitude_v2")
        if any(
            model_id in comparison
            for model_id in ("fixed_gap_7d_altitude_v2", "lag_event_altitude_v2")
        )
        else ("fixed_gap_7d_v1", "lag_event_v1")
    )
    visible_estimator_ids = {
        str(estimator_id)
        for model_id in model_ids
        if isinstance((result := comparison.get(model_id)), dict)
        for key in (
            "interpretation_estimator_probabilities",
            "estimator_probabilities",
        )
        if isinstance((probabilities := result.get(key)), dict)
        for estimator_id in probabilities
    }
    comparison_estimators = tuple(
        row for row in _COMPARISON_ESTIMATORS if row[0] in visible_estimator_ids
    )
    for model_id in model_ids:
        result = comparison.get(model_id)
        if not isinstance(result, dict):
            continue
        if not result.get("available"):
            outcome = html.escape(_lbl("ui.predictor_comparison_unavailable"))
            details = html.escape(str(result.get("reason", "")))
            estimator_probs: dict[str, Any] = {}
        else:
            estimator_probs = result.get(
                "interpretation_estimator_probabilities",
                result.get("estimator_probabilities", {}),
            )
            probability_values = [
                value
                for value in estimator_probs.values()
                if isinstance(value, (int, float))
            ]
            outcome = _pct(
                sum(probability_values) / len(probability_values)
                if probability_values
                else None
            )
            detail_parts = []
            missing_count = result.get("missing_feature_count")
            feature_count = result.get("feature_count")
            if isinstance(missing_count, int) and missing_count:
                detail_parts.append(
                    _lbl("ui.predictor_missing_features").format(
                        missing=missing_count,
                        total=feature_count,
                    )
                )
            details = html.escape(" ".join(detail_parts))
        cutoff = html.escape(str(result.get("cutoff_date", "—")))
        diagnostics = _render_model_diagnostics(result)
        estimator_cells = "".join(
            f'<td>{_pct(estimator_probs.get(estimator_id))}</td>'
            for estimator_id, _short_name, _is_shadow in comparison_estimators
        )
        column_count = 3 + len(comparison_estimators)
        contract_id = str(result.get("temporal_contract_id") or model_id.split(":")[-1])
        base_label = (
            _lbl("ui.predictor_model_fixed_gap_7d_v1")
            if contract_id.startswith("fixed_")
            else _lbl("ui.predictor_model_lag_event_v1")
        )
        profile_name = str(result.get("profile_name") or "")
        row_label = f"{profile_name} · {base_label}" if profile_name else labels.get(model_id, base_label)
        help_key = (
            "ui.predictor_help_model_fixed_gap_7d_altitude_v2"
            if contract_id.startswith("fixed_")
            else "ui.predictor_help_model_lag_event_altitude_v2"
        )
        rows += f"""
<tr>
  <td>{_tooltip_label(row_label, help_key)}<small>{details}</small></td>
  <td>{cutoff}</td>{estimator_cells}<td>{outcome}</td>
</tr>
<tr class="pred-comparison-diagnostics-row"><td colspan="{column_count}">{diagnostics}</td></tr>"""
    estimator_headers = "".join(
        f'<th>{_tooltip_label(short_name, _ESTIMATOR_HELP_KEYS[estimator_id], strong=False)}</th>'
        for estimator_id, short_name, _is_shadow in comparison_estimators
    )
    return f"""
<section class="pred-model-comparison">
  <h3>{html.escape(_lbl("ui.predictor_model_comparison_title"))}</h3>
  <p>{html.escape(_lbl("ui.predictor_model_comparison_help"))}</p>
  <div class="pred-table-wrap"><table class="pred-comparison-table">
    <thead><tr>
      <th>{_tooltip_label_key("ui.predictor_model", "ui.predictor_help_model", strong=False)}</th>
      <th>{_tooltip_label_key("ui.predictor_weather_cutoff", "ui.predictor_help_weather_cutoff", strong=False)}</th>
      {estimator_headers}
      <th>{_tooltip_label_key("ui.predictor_unweighted_mean", "ui.predictor_help_unweighted_mean", strong=False)}</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</section>"""


def _render_query_all_areas(
    species: str,
    target_date: date,
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    try:
        predictor = _get_predictor(species)
        area_ids = predictor.areas_with_species_observations()
    except FileNotFoundError as exc:
        return f'<div class="pred-error">{html.escape(str(exc))}</div>'
    except Exception as exc:
        return f'<div class="pred-error"><strong>Error:</strong> {html.escape(_predictor_error_text(exc))}</div>'

    if not area_ids:
        return f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_no_data"))}</div>'
    comparisons = [
        (area_id, _model_comparison(species, area_id, target_date))
        for area_id in area_ids
    ]
    interpreted = [
        (area_id, _interpretation(comparison))
        for area_id, comparison in comparisons
    ]
    interpreted.sort(key=lambda row: _interpretation_sort_key(row[1]), reverse=True)
    if interpreted and all(
        value.get("verdict") == "out_of_season" for _area_id, value in interpreted
    ):
        return f'<div class="pred-empty">⚪ {html.escape(_lbl("ui.predictor_out_of_season"))}</div>'

    sp_name = _species_name(species, profiles_payload)
    bt = _get_species_backtest_stats(species)
    by_area_bt = bt.get("by_area", {}) if bt else {}

    # Species-level reliability strip
    if bt and "total_episodes" in bt:
        total_ep = bt["total_episodes"]
        reliability_html = (
            f'<div class="pred-reliability-strip">'
            f'<span class="pred-rel-label">{html.escape(_lbl("ui.predictor_reliability"))}</span>'
            f'<span class="pred-rel-episodes">{total_ep} {html.escape(_lbl("ui.predictor_stat_episodes")).lower()}</span>'
            f'</div>'
        )
    else:
        reliability_html = ""

    rows_html = ""
    for area_id, interpretation in interpreted:
        area_n = _area_name(area_id, known_sites_payload)
        href = _url("query", species, area_id, target_date)
        area_bt = by_area_bt.get(area_id, {})
        ep_n = area_bt.get("episodes", 0) if area_bt else 0
        area_acc = area_bt.get("backtest_accuracy") if area_bt else None
        rel_badge = _rel_badge(ep_n)
        status = _interpretation_status(interpretation)
        rows_html += f"""
<a class="pred-rank-row {_status_cls(status)}" href="{html.escape(href)}">
  <span class="pred-rank-dot">{_status_dot(status)}</span>
  <span class="pred-rank-area">{html.escape(area_n)}</span>
  <span class="pred-rank-prob">{html.escape(_compact_interpretation_range(interpretation))}</span>
  {rel_badge}
</a>
"""

    return f"""
<div class="pred-rank-list pred-rank-compact">
  <h3>{html.escape(sp_name)} — {html.escape(target_date.strftime("%-d %b %Y"))}</h3>
  {reliability_html}
  {rows_html}
</div>
<div class="pred-legends-row">
  <p class="pred-hint-legend">
    🟢 {html.escape(_lbl("ui.predictor_favorable"))} &nbsp;
    🟡 {html.escape(_lbl("ui.predictor_uncertain"))} &nbsp;
    🔴 {html.escape(_lbl("ui.predictor_unfavorable"))} &nbsp;
    ⚪ {html.escape(_lbl("ui.predictor_out_of_season"))}
  </p>
  {_rel_legend_html()}
</div>
"""


def _label_text(label: str) -> str:
    if label == "out_of_season":
        return _lbl("ui.predictor_out_of_season")
    if label == "favorable":
        return _lbl("ui.predictor_favorable")
    if label == "uncertain":
        return _lbl("ui.predictor_uncertain")
    return _lbl("ui.predictor_unfavorable")


def _actual_text(actual: str) -> str:
    if actual == "favorable":
        return _lbl("ui.predictor_favorable")
    if actual == "unfavorable":
        return _lbl("ui.predictor_actual_unfavorable")
    return "—"


# ---------------------------------------------------------------------------
# History view
# ---------------------------------------------------------------------------

def _render_history(
    species: str,
    area: str,
    trained: list[str],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
    filter_mode: str = "",
) -> str:
    species_options_html = ""
    for sp_id in trained:
        sp_name = _species_name(sp_id, profiles_payload)
        sel = ' selected' if sp_id == species else ''
        species_options_html += f'<option value="{html.escape(sp_id)}"{sel}>{html.escape(sp_name)}</option>'

    form_html = f"""
<form class="pred-form" method="get" action="" data-predictor-direct-form>
  <input type="hidden" name="view" value="history">
  {_executor_hidden_input()}
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.species"))}</label>
    <select name="species" onchange="this.form.requestSubmit()">{species_options_html}</select>
  </div>
  <button type="submit" class="primary">{html.escape(_lbl("ui.search"))}</button>
</form>
"""

    try:
        predictor = _get_predictor(species)
        records = predictor.observed_episodes()
    except FileNotFoundError as exc:
        return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_history"))}</h2>
  {form_html}
  <div class="pred-error">{html.escape(str(exc))}</div>
</section>
"""
    except Exception as exc:
        return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_history"))}</h2>
  {form_html}
  <div class="pred-error"><strong>Error:</strong> {html.escape(_predictor_error_text(exc))}</div>
</section>
"""

    sp_name = _species_name(species, profiles_payload)
    interpreted_records: list[dict[str, Any]] = []
    for record in records:
        area_id = str(record.get("area_id", ""))
        observed_at = str(record.get("observed_at", ""))
        if not area_id or not observed_at:
            continue
        try:
            comparison = _model_comparison(
                species, area_id, date.fromisoformat(observed_at)
            )
            interpretation = _interpretation(comparison)
        except Exception:
            interpretation = {}
        verdict = str(interpretation.get("verdict", "abstain"))
        unvalidated_signal = str(
            interpretation.get("unvalidated_signal", "unavailable")
        )
        predicted_label = (
            unvalidated_signal
            if verdict == "abstain"
            and unvalidated_signal in {"favorable", "unfavorable"}
            else verdict
        )
        signal_is_unvalidated = verdict == "abstain" and predicted_label in {
            "favorable",
            "unfavorable",
        }
        actual = str(record.get("actual", ""))
        interpreted_records.append(
            {
                **record,
                "predicted_label": predicted_label,
                "signal_is_unvalidated": signal_is_unvalidated,
                "reference_range": _compact_interpretation_range(interpretation),
                "correct": (
                    predicted_label == actual
                    if predicted_label in {"favorable", "unfavorable"}
                    else None
                ),
            }
        )
    stats_html = _render_backtest_stats(interpreted_records, species, filter_mode)
    table_html = _render_backtest_table(interpreted_records, known_sites_payload, filter_mode)

    return f"""
<section class="pred-section">
  <h2>{html.escape(_lbl("ui.predictor_tab_history"))} — {html.escape(sp_name)}</h2>
  {form_html}
  {stats_html}
  {table_html}
</section>
"""


def _render_backtest_stats(records: list[dict[str, Any]], species: str, filter_mode: str) -> str:
    if not records:
        return f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_no_history"))}</div>'

    total = len(records)
    evaluated = [r for r in records if r.get("correct") is not None]
    correct = sum(1 for r in evaluated if r.get("correct"))
    fn = sum(1 for r in records if r.get("actual") == "favorable" and r.get("predicted_label") != "favorable")
    fp = sum(1 for r in records if r.get("actual") == "unfavorable" and r.get("predicted_label") == "favorable")
    acc = round(correct / len(evaluated) * 100) if evaluated else 0

    def stat_url(flt: str) -> str:
        # Toggle off if already active
        if filter_mode == flt:
            return html.escape(_url("history", species))
        return html.escape(_url("history", species, **{"filter": flt}))

    def stat_card(val: str, lbl_key: str, color_cls: str, flt: str) -> str:
        active_cls = " pred-stat-active" if filter_mode == flt else ""
        return (
            f'<a class="pred-stat-card {color_cls}{active_cls}" href="{stat_url(flt)}">'
            f'<div class="pred-stat-val">{html.escape(val)}</div>'
            f'<div class="pred-stat-label">{html.escape(_lbl(lbl_key))}</div>'
            f'</a>'
        )

    all_card = (
        f'<a class="pred-stat-card{"  pred-stat-active" if not filter_mode else ""}" href="{html.escape(_url("history", species))}">'
        f'<div class="pred-stat-val">{total}</div>'
        f'<div class="pred-stat-label">{html.escape(_lbl("ui.predictor_stat_episodes"))}</div>'
        f'</a>'
    )

    return f"""
<div class="pred-stats-row">
  {all_card}
  {stat_card(f"{acc}%", "ui.predictor_stat_accuracy", "pred-green", "correct")}
  {stat_card(str(fn), "ui.predictor_stat_fn", "pred-red", "fn")}
  {stat_card(str(fp), "ui.predictor_stat_fp", "pred-yellow", "fp")}
</div>
"""


def _render_backtest_table(records: list[dict[str, Any]], known_sites_payload: dict[str, Any], filter_mode: str = "") -> str:
    if not records:
        return ""

    def matches(r: dict[str, Any]) -> bool:
        if not filter_mode:
            return True
        actual = r.get("actual", "")
        predicted = r.get("predicted_label", "")
        if filter_mode == "correct":
            return bool(r.get("correct"))
        if filter_mode == "fn":
            return actual == "favorable" and predicted != "favorable"
        if filter_mode == "fp":
            return actual == "unfavorable" and predicted == "favorable"
        return True

    visible = [r for r in records if matches(r)]

    rows_html = ""
    for r in sorted(visible, key=lambda x: x.get("observed_at", ""), reverse=True):
        actual = r.get("actual", "")
        predicted = r.get("predicted_label", "")
        correct = r.get("correct")
        result_icon = (
            "✅"
            if correct is True
            else "❌"
            if correct is False
            else "⚠️"
        )
        area_n = _area_name(r.get("area_id", ""), known_sites_payload)
        reference_range = str(r.get("reference_range", "—"))
        signal_is_unvalidated = bool(r.get("signal_is_unvalidated"))
        display_interpretation = (
            {"verdict": "abstain", "unvalidated_signal": predicted}
            if signal_is_unvalidated
            else {"verdict": predicted}
        )
        display_prediction = _interpretation_label(display_interpretation)
        display_status = (
            "uncertain"
            if signal_is_unvalidated
            else _interpretation_status(display_interpretation)
        )
        rows_html += f"""
<tr>
  <td>{html.escape(str(r.get("observed_at", "")))}</td>
  <td>{html.escape(area_n)}</td>
  <td>{_status_dot(actual)} {html.escape(_actual_text(actual))}</td>
  <td>{_status_dot(display_status)} {html.escape(display_prediction)} {html.escape(reference_range)}</td>
  <td>{result_icon}</td>
</tr>
"""

    return f"""
<div class="pred-table-scroll">
  <table class="pred-history-table">
    <thead>
      <tr>
        <th>{html.escape(_lbl("ui.date_short"))}</th>
        <th>{html.escape(_lbl("ui.known_site_area"))}</th>
        <th>{html.escape(_lbl("ui.predictor_actual"))}</th>
        <th>{html.escape(_lbl("ui.predictor_predicted"))}</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>
"""


# ---------------------------------------------------------------------------
# Error block
# ---------------------------------------------------------------------------

def _render_errors(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "".join(f"<li>{e}</li>" for e in errors)
    return f'<div class="pred-error"><ul>{items}</ul></div>'


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_page(
    query: dict[str, list[str]],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
    prepared_response: dict[str, Any] | None = None,
    allow_executor_change: bool = True,
    training_freshness: dict[str, Any] | None = None,
) -> str:
    if prepared_response is not None:
        prepared_response = validate_response(prepared_response)
    prepared_token = _prepared_response.set(prepared_response)
    weather_cache_token = _prepared_weather_cache.set({})
    comparison_cache_token = _comparison_cache.set({})
    executor_token = _executor_query.set((query.get("executor") or [""])[0])
    executor_change_token = _allow_executor_change.set(allow_executor_change)
    training_freshness_token = _training_freshness.set(training_freshness)
    try:
        return _render_page_inner(query, profiles_payload, known_sites_payload)
    finally:
        _allow_executor_change.reset(executor_change_token)
        _comparison_cache.reset(comparison_cache_token)
        _prepared_weather_cache.reset(weather_cache_token)
        _prepared_response.reset(prepared_token)
        _executor_query.reset(executor_token)
        _training_freshness.reset(training_freshness_token)


def _render_training_freshness_warning() -> str:
    freshness = _training_freshness.get() or {}
    status = str(freshness.get("status", ""))
    if status == "current" or not status:
        return ""
    if status == "stale":
        help_key = "ui.predictor_training_stale_help"
    elif status == "unknown":
        help_key = "ui.predictor_training_unknown_help"
    else:
        help_key = "ui.predictor_training_invalid_help"
    return (
        '<div class="pred-training-warning">'
        f'<strong>{html.escape(_lbl("ui.predictor_training_warning"))}</strong>'
        f'<span>{html.escape(_lbl(help_key))}</span>'
        "</div>"
    )


def _render_page_inner(
    query: dict[str, list[str]],
    profiles_payload: dict[str, Any],
    known_sites_payload: dict[str, Any],
) -> str:
    view = (query.get("view") or ["recommender"])[0]
    species = (query.get("species") or [""])[0]
    area = (query.get("area") or [""])[0]
    date_str = (query.get("date") or [""])[0]
    filter_mode = (query.get("filter") or [""])[0]
    compare_value = (query.get("compare") or [None])[0]
    compare_models = compare_value != "0"

    trained = trained_species_ids()

    if not trained:
        return f"""
<div class="pred-no-models">
  <p style="font-size:3rem">🤖</p>
  <h2>{html.escape(_lbl("ui.predictor_no_models"))}</h2>
  <p>{html.escape(_lbl("ui.predictor_no_models_help"))}</p>
  <a class="button-link secondary-link" href="?" style="margin-top:1rem">{html.escape(_lbl("ui.back"))}</a>
</div>
"""

    if not species or species not in trained:
        species = trained[0]
    selected_versions = list(query.get("mvv", []))
    selected_multiversion = list(query.get("mv", []))
    if selected_versions:
        selected_multiversion = multiversion_tokens_for_versions(species, selected_versions)

    try:
        target_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        target_date = date.today()
    target_date = normalize_predictor_target_date(view, target_date)

    tabs = _render_tabs(view, species, target_date)

    try:
        if view == "week":
            content = _render_week(species, target_date, trained, profiles_payload, known_sites_payload)
        elif view == "query":
            content = _render_query(
                species,
                area,
                target_date,
                trained,
                profiles_payload,
                known_sites_payload,
                compare_models=compare_models,
                selected_multiversion=selected_multiversion,
                selected_versions=selected_versions,
            )
        elif view == "history":
            content = _render_history(species, area, trained, profiles_payload, known_sites_payload, filter_mode)
        else:
            content = _render_recommender(target_date, trained, profiles_payload, known_sites_payload)
    except Exception as exc:
        content = f'<div class="pred-error"><strong>Error:</strong> {html.escape(_predictor_error_text(exc))}</div>'

    change_executor = (
        '<a href="?" data-predictor-modal-open>'
        f'{html.escape(_lbl("ui.predictor_executor_change"))}</a>'
        if _allow_executor_change.get()
        else ""
    )
    freshness_warning = _render_training_freshness_warning()
    return f"""
<style>
{_CSS}
</style>
<div class="pred-page">
  <div class="pred-back">
    <a href="../">← {html.escape(_lbl("ui.back_to_panel"))}</a>
    {change_executor}
  </div>
  <h1>🍄 {html.escape(_lbl("ui.predictor_title"))}</h1>
  {freshness_warning}
  {tabs}
  {content}
</div>
"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
.pred-page { max-width: 1280px; margin: 0 auto; padding: 0 1.25rem 3rem; }
.pred-page h1 { margin-bottom: 0.65rem; font-size: 2rem; }
.pred-back { display: flex; gap: 1rem; margin-bottom: 0.75rem; }
.pred-back a { color: #9aa8b2; font-size: 0.98rem; text-decoration: none; }
.pred-back a:hover { color: #e8eef2; }
.pred-training-warning {
  display: grid; gap: 0.3rem; margin: 0 0 1rem; padding: 0.85rem 1rem;
  border: 1px solid #d69e2e; border-radius: 8px; background: #2a2418;
  color: #f5d98b;
}
.pred-training-warning span { color: #d6c7a0; }

/* Tabs */
.pred-tabs { display: flex; gap: 0.25rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.pred-tab {
  padding: 0.6rem 1.1rem;
  border-radius: 6px;
  background: #1b2229;
  color: #9aa8b2;
  text-decoration: none;
  font-size: 1rem;
  border: 1px solid #33404a;
  transition: background 0.15s;
}
.pred-tab:hover { background: #243040; color: #e8eef2; }
.pred-tab-active { background: #0d2436; color: #03a9f4; border-color: #03a9f4; }

/* Section */
.pred-section h2 { margin-top: 0; color: #e8eef2; }
.pred-section h3 { color: #9aa8b2; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 1.5rem; }

/* Day strip */
.pred-day-strip {
  display: flex; gap: 0.25rem; margin-bottom: 1.5rem; flex-wrap: wrap;
}
.pred-day {
  flex: 1 1 80px; min-width: 60px;
  padding: 0.5rem 0.25rem;
  text-align: center;
  background: #1b2229;
  border: 1px solid #33404a;
  border-radius: 8px;
  text-decoration: none;
  color: #9aa8b2;
  font-size: 0.98rem;
  line-height: 1.4;
  transition: background 0.15s;
}
.pred-day:hover { background: #243040; color: #e8eef2; }
.pred-day-active { background: #0d2436; border-color: #03a9f4; color: #03a9f4; }

/* Best bet card */
.pred-best-card {
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid #33404a;
  background: #1b2229;
  position: relative;
}
.pred-best-badge {
  font-size: 0.92rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #9aa8b2;
  margin-bottom: 0.5rem;
}
.pred-best-name { font-size: 1.4rem; font-weight: 700; color: #e8eef2; }
.pred-best-area { font-size: 1rem; color: #9aa8b2; margin-top: 0.15rem; }
.pred-best-prob { font-size: 2.5rem; font-weight: 900; margin: 0.5rem 0 0.25rem; }
.pred-best-hint { font-size: 1rem; color: #9aa8b2; }

/* Status colors */
.pred-green { border-color: #51cf66 !important; }
.pred-green .pred-best-prob, .pred-green .pred-result-prob { color: #51cf66; }
.pred-yellow { border-color: #ffd43b !important; }
.pred-yellow .pred-best-prob, .pred-yellow .pred-result-prob { color: #ffd43b; }
.pred-red { border-color: #ff6b6b !important; }
.pred-red .pred-best-prob, .pred-red .pred-result-prob { color: #ff6b6b; }
.pred-muted { border-color: #7f8b94 !important; }
.pred-muted .pred-best-prob, .pred-muted .pred-result-prob { color: #a8b1b8; }

/* Ranked list */
.pred-rank-list { display: flex; flex-direction: column; gap: 0.25rem; }
.pred-rank-header {
  display: grid;
  grid-template-columns: 1.5rem minmax(0, 1fr) minmax(0, 1fr) 13.5rem;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem;
  font-size: 0.92rem;
  text-transform: uppercase;
  color: #9aa8b2;
  letter-spacing: 0.05em;
}
.pred-rank-header > span:last-child {
  text-align: right;
  line-height: 1.25;
}
.pred-rank-row {
  display: grid;
  grid-template-columns: 1.5rem minmax(0, 1fr) minmax(0, 1fr) 13.5rem;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  background: #1b2229;
  border-radius: 8px;
  border: 1px solid #33404a;
  text-decoration: none;
  color: #e8eef2;
  font-size: 1rem;
  align-items: center;
  transition: background 0.1s;
}
.pred-rank-row:hover { background: #243040; }
.pred-rank-area { color: #9aa8b2; }
.pred-rank-prob { text-align: right; font-weight: 600; white-space: nowrap; }
.pred-rank-compact .pred-rank-row {
  grid-template-columns: 1.5rem 1fr 4rem 6rem;
}

/* Reliability strip and per-area badge */
.pred-reliability-strip {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.94rem; color: #7a8a96; margin-bottom: 0.5rem;
  padding: 0.35rem 0.6rem; background: #131b22; border-radius: 6px;
  border-left: 3px solid #2d4a5a;
}
.pred-rel-label { color: #5a7080; font-size: 0.92rem; text-transform: uppercase; letter-spacing: 0.04em; }
.pred-rel-sep { color: #3a4a55; }
.pred-rel-acc { font-weight: 600; color: #a0b8c0; }
.pred-rel-badge {
  font-size: 0.92rem; color: #6a8898; text-align: right; white-space: nowrap;
}
.pred-rel-none { color: #3a4a55; }
.pred-rel-cell { font-size: 0.92rem; color: #6a8898; white-space: nowrap; padding: 0.4rem 0.55rem; }
.pred-rel-header { font-size: 0.92rem; color: #5a7080; font-weight: normal; white-space: nowrap; }
.pred-legends-row { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.25rem; }
.pred-legends-row .pred-hint-legend { margin: 0; }
.pred-hint-legend-right { text-align: right; }

/* Species chips */
.pred-chips { display: flex; gap: 0.4rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.pred-chip {
  padding: 0.4rem 0.9rem;
  border-radius: 20px;
  background: #1b2229;
  border: 1px solid #33404a;
  color: #9aa8b2;
  text-decoration: none;
  font-size: 0.98rem;
  transition: background 0.1s;
}
.pred-chip:hover { background: #243040; color: #e8eef2; }
.pred-chip-active { background: #0d2436; border-color: #03a9f4; color: #03a9f4; }

/* Week grid */
.pred-table-scroll { overflow-x: auto; }
.pred-week-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 1rem;
}
.pred-week-table th {
  background: #1b2229;
  padding: 0.65rem 0.5rem;
  text-align: center;
  color: #9aa8b2;
  border-bottom: 1px solid #33404a;
  white-space: nowrap;
}
.pred-week-table td { padding: 0.55rem 0.5rem; border-bottom: 1px solid #1b2229; }
.pred-area-cell { color: #9aa8b2; white-space: nowrap; padding-right: 0.75rem; }
.pred-cell { text-align: center; }
.pred-cell a { text-decoration: none; color: inherit; }
.pred-today-col { color: #03a9f4; }
.pred-hint-legend { font-size: 0.94rem; color: #9aa8b2; margin-top: 0.75rem; }

/* Form */
.pred-form { display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-end; margin-bottom: 1.5rem; }
.pred-form-row { display: flex; flex-direction: column; gap: 0.3rem; }
.pred-form-row label { font-size: 0.92rem; color: #9aa8b2; text-transform: uppercase; letter-spacing: 0.05em; }
.pred-form select, .pred-form input[type="date"] {
  background: #1b2229;
  border: 1px solid #33404a;
  color: #e8eef2;
  padding: 0.45rem 0.75rem;
  border-radius: 6px;
  font-size: 1rem;
}
.pred-multiversion-controls { flex: 1 1 100%; display: grid; gap: 0.4rem; }
.pred-multiversion-controls > label { color: #9aa8b2; font-size: 0.92rem; text-transform: uppercase; letter-spacing: 0.05em; }
.pred-multiversion-controls select { width: 100%; min-height: 10rem; }
.pred-multiversion-controls small { color: #9aa8b2; }
.pred-multiversion-controls details { color: #b8c4cc; }
.pred-multiversion-result { margin-top: 1.25rem; padding: 1rem; border: 1px solid #34434d; border-radius: 8px; background: #182127; }
.pred-version-choices {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.55rem;
  width: 100%;
}
.pred-version-choice {
  min-width: 0;
  display: grid;
  grid-template-columns: 1.1rem minmax(0, 1fr);
  grid-template-areas: "check title" "check subtitle";
  column-gap: 0.55rem;
  row-gap: 0.08rem;
  align-items: center;
  padding: 0.65rem 0.75rem;
  border: 1px solid #40515d;
  border-radius: 7px;
  background: #202b33;
  cursor: pointer;
}
.pred-version-choice input[type="checkbox"] {
  grid-area: check;
  appearance: auto;
  -webkit-appearance: checkbox;
  box-sizing: border-box;
  width: 1.1rem !important;
  height: 1.1rem !important;
  min-width: 1.1rem;
  margin: 0;
  padding: 0;
  accent-color: #1685dd;
}
.pred-version-choice strong { grid-area: title; line-height: 1.15; }
.pred-version-choice span {
  grid-area: subtitle;
  min-width: 0;
  color: #aebbc4;
  font-size: 0.82rem;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.pred-version-choice:has(input:checked) { border-color: #1685dd; background: #1d303d; }
.pred-version-choice:has(input:disabled) { opacity: 0.55; cursor: not-allowed; }
@media (max-width: 1050px) {
  .pred-version-choices { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 680px) {
  .pred-version-choices { grid-template-columns: 1fr; }
}
.pred-version-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0.8rem; margin: 1rem 0; }
.pred-confidence-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.7rem; margin: 0.7rem 0 1rem; }
.pred-confidence-card { display: grid; grid-template-columns: auto 1fr; column-gap: 0.65rem; align-items: baseline; border: 1px solid #40515d; border-radius: 8px; padding: 0.75rem; background: #202b33; }
.pred-confidence-card > strong { grid-row: 1 / span 2; font-size: 1.7rem; line-height: 1; }
.pred-confidence-card > span { font-weight: 750; }
.pred-confidence-card > small { color: #aebbc4; line-height: 1.3; }
.pred-confidence-usable { border-color: #2f8f5b; }
.pred-confidence-weak { border-color: #8b7a38; }
.pred-confidence-not_usable { border-color: #9b5555; }
.pred-confidence-weather_pending { border-color: #4b7897; }
@media (max-width: 1050px) { .pred-confidence-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 680px) { .pred-confidence-grid { grid-template-columns: 1fr; } }
.pred-version-card { border: 1px solid #40515d; border-radius: 8px; padding: 0.85rem; background: #202b33; }
.pred-version-card h4 { margin: 0 0 0.35rem; font-size: 1.25rem; }
.pred-version-role, .pred-version-caution { color: #b8c4cc; }
.pred-version-card dl { margin: 0.7rem 0; display: grid; gap: 0.4rem; }
.pred-version-card dl div { display: flex; justify-content: space-between; gap: 0.6rem; border-bottom: 1px solid #34434d; }
.pred-version-card dt { color: #9aa8b2; }
.pred-version-card dd { margin: 0; text-align: right; }
.pred-version-breakdowns { display: grid; gap: 0.7rem; margin: 0.8rem 0 1rem; }
.pred-version-breakdown { border: 1px solid #40515d; border-radius: 7px; padding: 0.7rem; background: #182127; }
.pred-version-breakdown summary { cursor: pointer; font-weight: 750; }
.pred-version-breakdown .pred-table-scroll { margin-top: 0.7rem; }
.pred-member-result { min-width: 9rem; vertical-align: top; }
.pred-member-result strong { display: block; font-size: 1.05rem; }
.pred-member-result small, .pred-member-unavailable small {
  display: block;
  margin-top: 0.2rem;
  color: #9aa8b2;
  font-size: 0.74rem;
  line-height: 1.25;
}
.pred-member-unavailable { color: #9aa8b2; vertical-align: top; }
.pred-ranking { margin: 0.7rem 0; border: 1px solid #34434d; border-radius: 7px; padding: 0.65rem; }
.pred-ranking summary { cursor: pointer; font-weight: 700; }

/* Result card */
.pred-result-card {
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  border: 1px solid #33404a;
  background: #1b2229;
  margin-bottom: 1rem;
}
.pred-result-header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
  color: #9aa8b2;
  font-size: 1rem;
}
.pred-result-species { font-weight: 600; color: #e8eef2; }
.pred-result-dot { font-size: 1.25rem; }
.pred-result-prob { font-size: 2.5rem; font-weight: 900; margin: 0.25rem 0; }
.pred-result-label { font-size: 1rem; color: #9aa8b2; margin-bottom: 0.5rem; }
.pred-interpretation-card {
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  border: 1px solid #33404a;
  background: #1b2229;
  margin-bottom: 1rem;
}
.pred-interpretation-title { font-size: 1.8rem; font-weight: 800; color: #e8eef2; }
.pred-interpretation-range { display: flex; align-items: baseline; gap: 0.65rem; margin-top: 0.45rem; color: #9aa8b2; }
.pred-interpretation-range strong { font-size: 1.65rem; color: #e8eef2; }
.pred-interpretation-meta { display: flex; flex-wrap: wrap; gap: 0.55rem 1.25rem; margin-top: 0.65rem; color: #aebbc4; }
.pred-interpretation-meta strong { color: #dfe8ed; }
.pred-tooltip {
  display: inline-flex;
  align-items: baseline;
  gap: 0.22rem;
  cursor: help;
  text-decoration: underline dotted rgba(174, 187, 196, 0.55);
  text-underline-offset: 0.2rem;
}
.pred-tooltip:focus { outline: 1px solid #5f7888; outline-offset: 2px; border-radius: 2px; }
.pred-tooltip-icon { color: #7f919c; font-size: 0.72em; text-decoration: none; }
.pred-interpretation-card p { margin: 0.75rem 0 0; color: #c2ccd2; line-height: 1.45; }
.pred-model-comparison { margin: 1.25rem 0; padding: 1rem; border: 1px solid #344650; border-radius: 10px; background: #172129; }
.pred-model-comparison h3 { margin: 0 0 0.35rem; color: #e8eef2; }
.pred-model-comparison p { margin: 0 0 0.85rem; color: #9aa8b2; }
.pred-comparison-table { width: 100%; border-collapse: collapse; }
.pred-comparison-table th, .pred-comparison-table td { padding: 0.65rem; text-align: left; border-bottom: 1px solid #344650; }
.pred-comparison-table th { color: #9aa8b2; }
.pred-comparison-table td small { display: block; max-width: 25rem; color: #ffcc66; margin-top: 0.2rem; }
.pred-comparison-diagnostics-row td { padding-top: 0; }
.pred-comparison-diagnostics { display: flex; flex-wrap: wrap; gap: 0.45rem 1rem; padding: 0.15rem 0 0.7rem; color: #b7c5ce; font-size: 0.94rem; }
.pred-comparison-diagnostics span { white-space: normal; }
.pred-comparison-diagnostics strong { color: #dfe8ed; }
.pred-prob-detail { font-size: 0.94rem; color: #9aa8b2; display: flex; gap: 1rem; }
.pred-station-info { font-size: 0.94rem; color: #9aa8b2; display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem; }
.pred-gaps { margin-top: 0.5rem; color: #9aa8b2; }

/* Week strip (query view) */
.pred-week-strip {
  display: flex; gap: 0.25rem; margin-bottom: 1rem; flex-wrap: wrap;
}
.pred-week-cell {
  flex: 1 1 80px;
  padding: 0.4rem 0.25rem;
  text-align: center;
  background: #1b2229;
  border: 1px solid #33404a;
  border-radius: 8px;
  text-decoration: none;
  color: #9aa8b2;
  font-size: 0.94rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  transition: background 0.1s;
}
.pred-week-cell:hover { background: #243040; }
.pred-week-active { border-width: 2px; }

/* Stats row */
.pred-stats-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.pred-stat-card {
  flex: 1 1 100px;
  background: #1b2229;
  border: 1px solid #33404a;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  text-align: center;
}
.pred-stat-val { font-size: 1.8rem; font-weight: 900; color: #e8eef2; }
.pred-stat-label { font-size: 0.92rem; color: #9aa8b2; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.25rem; }
.pred-stat-card.pred-green .pred-stat-val { color: #51cf66; }
.pred-stat-card.pred-red .pred-stat-val { color: #ff6b6b; }
.pred-stat-card.pred-yellow .pred-stat-val { color: #ffd43b; }
a.pred-stat-card { text-decoration: none; cursor: pointer; transition: background 0.15s, border-color 0.15s; }
a.pred-stat-card:hover { background: #243040; }
.pred-stat-active { outline: 2px solid #03a9f4; outline-offset: 2px; }

/* History table */
.pred-history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 1rem;
}
.pred-history-table th {
  background: #1b2229;
  padding: 0.5rem 0.75rem;
  text-align: left;
  color: #9aa8b2;
  border-bottom: 1px solid #33404a;
}
.pred-history-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #1b2229;
  color: #e8eef2;
}
.pred-history-table tr:hover td { background: #1e2a34; }

/* Utilities */
.pred-error {
  background: #2d1a1a;
  border: 1px solid #7a3030;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  color: #ff9b9b;
  margin-bottom: 1rem;
  font-size: 1rem;
}
.pred-empty { color: #9aa8b2; font-style: italic; padding: 1rem 0; }
.pred-no-models { text-align: center; padding: 3rem 1rem; color: #9aa8b2; }
.pred-no-models h2 { color: #e8eef2; }

@media (max-width: 700px) {
  .pred-page { padding-inline: 0.5rem; }
  .pred-week-table { min-width: 980px; }
  .pred-history-table { min-width: 720px; }
  .pred-rank-header,
  .pred-rank-row {
    grid-template-columns: 1.25rem minmax(0, 1fr) minmax(0, 1fr) 7.5rem;
  }
  .pred-rank-header { font-size: 0.78rem; }
}
"""
