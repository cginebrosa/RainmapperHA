"""Server-rendered Predictor UI for the mushroom ML v0 model."""

from __future__ import annotations

import gc
import html
import json
from contextvars import ContextVar
from datetime import date, timedelta
from pathlib import Path
from threading import RLock
from typing import Any, Callable
from urllib.parse import urlencode

from rainmapper_core import mushroom_paths
from rainmapper_core import mushroom_predictor_runtime
from rainmapper_core import mushroom_soilgrids_reconciler
from rainmapper_core import mushroom_ml_model_catalog
from rainmapper_core import mushroom_ml_version_registry
from rainmapper_core import mushroom_ml_multiversion_comparison
from rainmapper_core import mushroom_weather_idw
from rainmapper_core.mushroom_ml_predictor import (
    MushroomMLPredictor,
    invalidate_weather_stations_cache,
)
from rainmapper_core.mushroom_observation_context import WeatherParquetLayoutError
from rainmapper_core.mushroom_predictor_service import (
    PredictorService,
    PreparedPredictor,
    validate_response,
)
from rainmapper_core.mushroom_prediction_interpretation import (
    FAVORABLE_THRESHOLD,
    UNFAVORABLE_THRESHOLD,
)

import mushroom_profiles_ui


# Module-level predictor cache — lazy-loaded, survives across requests
_predictor_cache: dict[str, MushroomMLPredictor] = {}
_predictor_cache_lock = RLock()
_predictor_service: PredictorService | None = None
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
_job_query: ContextVar[str] = ContextVar("mushroom_predictor_job", default="")
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

_VERSION_SHORT_NAMES = {
    "altitude_v2": "V2",
    "biology_v3": "V3",
    "biology_v4": "V4",
    "biology_v5_raw_weather_discovery": "V5",
    "biology_v6_smooth_hierarchical": "V6",
    "biology_v5_windowed_raw_weather": "V5w",
    "biology_v6_windowed_smooth_hierarchical": "V6w",
}

_VERSION_COMPACT_NAMES = {
    "altitude_v2": "Altitud y meteo común",
    "biology_v3": "Biología base",
    "biology_v4": "Biología y balance hídrico",
    "biology_v5_raw_weather_discovery": "Meteo cruda regularizada",
    "biology_v6_smooth_hierarchical": "Curvas suaves y jerarquía",
    "biology_v5_windowed_raw_weather": "Meteo cruda por ventana 30/60/90d",
    "biology_v6_windowed_smooth_hierarchical": "Curvas suaves por ventana 30/60/90d",
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
    global _predictor_service  # noqa: PLW0603
    with _predictor_cache_lock:
        released_instances = len(_predictor_cache)
        _predictor_cache.clear()
        if _predictor_service is not None:
            released_instances += 1
            _predictor_service = None
        invalidate_weather_stations_cache()
    gc.collect()
    return released_instances


def predictor_cache_info(species_id: str = "") -> dict[str, int | bool]:
    """Return non-sensitive cache state for request diagnostics."""
    with _predictor_cache_lock:
        service_loaded = _predictor_service is not None
        instance_count = len(_predictor_cache) + int(service_loaded)
        cold_request = (
            not service_loaded and species_id not in _predictor_cache
            if species_id
            else instance_count == 0
        )
    return {
        "predictor_instance_count": instance_count,
        "cold_request": cold_request,
    }


def execute_predictor_request(request: object) -> dict[str, Any]:
    """Execute one HA request through the same service used by workers."""
    global _predictor_service  # noqa: PLW0603
    with _predictor_cache_lock:
        if _predictor_service is None:
            manifest, _sources, _publication_status = (
                mushroom_predictor_runtime.load_or_publish_manifest()
            )
            _predictor_service = PredictorService(
                models_dir=mushroom_paths.mushroom_ml_models_dir(),
                weather_data_dir=mushroom_paths.weather_data_dir(),
                features_artifact_path=mushroom_paths.mushroom_observation_features_json_path(),
                known_sites_path=mushroom_paths.mushroom_known_sites_path(),
                profiles_path=mushroom_paths.mushroom_profiles_path(),
                version_registry_path=mushroom_paths.mushroom_ml_version_registry_path(),
                stations_file_path=Path("/app/stations.txt"),
                runtime_fingerprint=str(manifest["fingerprint"]),
            )
        service = _predictor_service
    return service.execute(request)


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


def _operational_pct(prob: float | None) -> str:
    """Avoid rounding a score across one of the displayed decision boundaries."""
    if prob is None:
        return "—"
    percentage = float(prob) * 100
    rounded_probability = round(percentage) / 100
    raw_band = (
        "favorable"
        if prob >= FAVORABLE_THRESHOLD
        else "unfavorable"
        if prob <= UNFAVORABLE_THRESHOLD
        else "uncertain"
    )
    rounded_band = (
        "favorable"
        if rounded_probability >= FAVORABLE_THRESHOLD
        else "unfavorable"
        if rounded_probability <= UNFAVORABLE_THRESHOLD
        else "uncertain"
    )
    if raw_band != rounded_band:
        return f"{percentage:.1f}%"
    return f"{round(percentage)}%"


def _status_cls(label: str) -> str:
    if label in {"out_of_season", "abstain"}:
        return "pred-muted"
    if label == "favorable":
        return "pred-green"
    if label == "uncertain":
        return "pred-yellow"
    return "pred-red"


def _url(
    view: str = "recommender",
    species: str = "",
    area: str = "",
    target_date: date | None = None,
    reuse_result: bool = False,
    **extra: str | list[str],
) -> str:
    params: dict[str, str | list[str]] = {"view": view}
    if species:
        params["species"] = species
    if area:
        params["area"] = area
    if target_date:
        params["date"] = target_date.isoformat()
    if _executor_query.get():
        params["executor"] = _executor_query.get()
    if reuse_result and _job_query.get():
        params["job_id"] = _job_query.get()
    params.update({k: v for k, v in extra.items() if v})
    return "?" + urlencode(params, doseq=True)


def _executor_hidden_input() -> str:
    """Keep the selected executor across GET forms inside the Predictor."""
    executor = _executor_query.get()
    if not executor:
        return ""
    return (
        '<input type="hidden" name="executor" value="'
        f'{html.escape(executor, quote=True)}">'
    )


def _installed_manifests(
    registry: dict[str, Any],
    *,
    version_ids: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    request_cache = _comparison_cache.get()
    cached = (
        request_cache.get("installed_manifests")
        if request_cache is not None
        else None
    )
    if not isinstance(cached, dict):
        cached = {}
        if request_cache is not None:
            request_cache["installed_manifests"] = cached
    manifests: dict[str, dict[str, Any]] = {}
    models_root = mushroom_paths.mushroom_ml_models_dir()
    for version in registry["versions"]:
        version_id = str(version["version_id"])
        if version_ids is not None and version_id not in version_ids:
            continue
        if version.get("installed_generation_id") is None:
            continue
        manifest = cached.get(version_id)
        if isinstance(manifest, dict):
            manifests[version_id] = manifest
            continue
        path = mushroom_ml_version_registry.installed_manifest_path(
            registry, version_id, models_root=models_root
        )
        if path is None or not path.is_file():
            raise FileNotFoundError(f"Installed manifest is missing for {version_id}")
        manifest = mushroom_ml_model_catalog.validate_batch_manifest(
            registry, json.loads(path.read_text(encoding="utf-8"))
        )
        cached[version_id] = manifest
        manifests[version_id] = manifest
    return manifests


def _model_comparison(species_id: str, area_id: str, target_date: date) -> dict[str, Any] | None:
    predictor = _get_predictor(species_id)
    if isinstance(predictor, PreparedPredictor):
        return predictor.model_comparison(area_id, target_date)
    request_cache = _comparison_cache.get()
    registry = request_cache.get("registry") if request_cache is not None else None
    if not isinstance(registry, dict):
        registry = mushroom_ml_version_registry.load_registry(
            mushroom_paths.mushroom_ml_version_registry_path()
        )
        if request_cache is not None:
            request_cache["registry"] = registry
    preferred = registry.get("preferred_version_id")
    manifests = _installed_manifests(
        registry,
        version_ids={str(preferred)} if preferred is not None else set(),
    )
    manifest = manifests.get(str(preferred)) if preferred is not None else None
    if manifest is None:
        return {"available": False, "reason": "preferred_version_not_installed"}
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
        "preferred_version_id": registry.get("preferred_version_id"),
        "entries": mushroom_ml_model_catalog.catalog_entries(registry),
        "runtime_batch_status": "not_installed",
        "runtime_batches": {},
        "installed_artifacts": [],
    }
    try:
        manifests = _installed_manifests(registry)
    except (OSError, ValueError, json.JSONDecodeError):
        result["runtime_batch_status"] = "invalid"
        return result
    result["runtime_batch_status"] = "installed" if manifests else "not_installed"
    result["runtime_batches"] = {
        version_id: {
            "batch_id": manifest["batch_id"],
            "snapshot_id": manifest["snapshot_id"],
        }
        for version_id, manifest in manifests.items()
    }
    artifacts_by_key = {
        mushroom_ml_model_catalog.ModelArtifactRef.from_mapping(
            row["artifact_ref"]
        ).key: {
            "artifact_ref": dict(row["artifact_ref"]),
            "supported_horizons": list(row["supported_horizons"]),
        }
        for manifest in manifests.values()
        for row in manifest["artifacts"]
    }
    result["installed_artifacts"] = list(artifacts_by_key.values())
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
    if not selected_version_set:
        preferred = str(payload.get("preferred_version_id") or "")
        if preferred:
            selected_version_set.add(preferred)
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
        short = _VERSION_SHORT_NAMES.get(version_id, version_id)
        compact_name = _VERSION_COMPACT_NAMES.get(
            version_id, str(entry.get("version_display_name") or version_id)
        )
        checked = " checked" if version_id in selected_version_set else ""
        installed = any(
            isinstance(row, dict) and isinstance(row.get("artifact_ref"), dict)
            and row["artifact_ref"].get("version_id") == version_id
            and row["artifact_ref"].get("species_id") in {species_id, "all_species"}
            for row in artifacts
        )
        if not installed:
            continue
        version_rows.append(
            f'<label class="pred-version-choice"><input type="checkbox" name="mvv" '
            f'value="{html.escape(version_id, quote=True)}"{checked}> '
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
  <label>Versiones incluidas en la predicción</label>
  <div class="pred-version-choices">{''.join(version_rows)}</div>
  <small>Las versiones marcadas participan en igualdad. Se evaluarán sus perfiles, contratos y algoritmos disponibles para la fecha solicitada.</small>
  <details><summary>Detalle técnico y disponibilidad</summary><ul>{catalog_rows}</ul></details>
</div>
"""


def _preferred_version_control(
    species_id: str,
    area_id: str,
    target_date: date,
    *,
    compare_models: bool,
    selected_versions: list[str],
) -> str:
    payload = _multiversion_catalog_payload()
    preferred = str(payload.get("preferred_version_id") or "")
    installed_ids = set((payload.get("runtime_batches") or {}).keys())
    entries = payload.get("entries") if isinstance(payload, dict) else []
    entries = entries if isinstance(entries, list) else []
    selected_choice = selected_versions[0] if len(selected_versions) == 1 else preferred
    choices = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        version_id = str(entry.get("version_id") or "")
        if version_id in seen or version_id not in installed_ids:
            continue
        seen.add(version_id)
        selected = " selected" if version_id == selected_choice else ""
        short = _VERSION_SHORT_NAMES.get(version_id, version_id)
        compact_name = _VERSION_COMPACT_NAMES.get(
            version_id, str(entry.get("version_display_name") or version_id)
        )
        choices.append(
            f'<option value="{html.escape(version_id, quote=True)}"{selected}>'
            f'{html.escape(short)} · {html.escape(compact_name)}</option>'
        )
    if not choices:
        return ""
    return f"""
<div class="pred-form-row pred-preferred-field">
  <label for="pred-preferred-version">{html.escape(_lbl("ui.predictor_preferred_short"))}</label>
  <select id="pred-preferred-version" name="preferred_version_id"
          title="{html.escape(_lbl("ui.predictor_preferred_help"), quote=True)}">{''.join(choices)}</select>
</div>
"""


def _preferred_version_id() -> str:
    prepared = _prepared_response.get()
    catalog = (
        prepared.get("data", {}).get("model_catalog")
        if isinstance(prepared, dict)
        else None
    )
    preferred_id = str(
        catalog.get("preferred_version_id") or ""
        if isinstance(catalog, dict)
        else ""
    )
    if not preferred_id:
        request_cache = _comparison_cache.get()
        registry = request_cache.get("registry") if request_cache is not None else None
        if not isinstance(registry, dict):
            try:
                registry = mushroom_ml_version_registry.load_registry(
                    mushroom_paths.mushroom_ml_version_registry_path()
                )
                if request_cache is not None:
                    request_cache["registry"] = registry
            except (OSError, ValueError):
                registry = {}
        preferred_id = str(registry.get("preferred_version_id") or "")
    return preferred_id


def resolved_query_versions(query: dict[str, list[str]]) -> list[str]:
    """Resolve the exact query selection once for queueing and rendering."""
    selected = [str(value) for value in query.get("mvv", []) if str(value)]
    if selected:
        return selected
    form_choice = str((query.get("preferred_version_id") or [""])[0])
    if form_choice:
        return [form_choice]
    preferred = _preferred_version_id()
    return [preferred] if preferred else []


def _preferred_version_badge() -> str:
    preferred_id = _preferred_version_id()
    if not preferred_id:
        return ""
    preferred_name = _VERSION_SHORT_NAMES.get(preferred_id, preferred_id)
    return (
        '<div class="pred-preferred-badge">'
        f'<span>{html.escape(_lbl("ui.predictor_preferred_badge"))}</span>'
        f'<strong>{html.escape(preferred_name)}</strong>'
        '</div>'
    )


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
        data = prepared.get("data", {})
        species_data = data.get("species", {}).get(species_id, {})
        payload = (
            species_data.get("multiversion_comparisons", {}).get(
                target_date.isoformat()
            )
            if isinstance(species_data, dict)
            else None
        )
        if not isinstance(payload, dict) and isinstance(species_data, dict):
            request_target = str(
                prepared.get("request", {}).get("target_date") or ""
            )
            if not request_target or request_target == target_date.isoformat():
                payload = species_data.get("multiversion_comparison")
        if not isinstance(payload, dict):
            return None
        result = dict(payload)
        catalog = data.get("model_catalog")
        if isinstance(catalog, dict):
            result.setdefault("preferred_version_id", catalog.get("preferred_version_id"))
        return result
    request_cache = _comparison_cache.get()
    registry = request_cache.get("registry") if request_cache is not None else None
    if not isinstance(registry, dict):
        registry = mushroom_ml_version_registry.load_registry(
            mushroom_paths.mushroom_ml_version_registry_path()
        )
        if request_cache is not None:
            request_cache["registry"] = registry
    selections = []
    for token in selected_tokens:
        parsed = mushroom_ml_model_catalog.parse_selection_token(token)
        parsed.pop("token", None)
        selections.append(parsed)
    selections = mushroom_ml_multiversion_comparison.operational_selections(
        selections,
        target_date=target_date,
        issue_date=min(date.today(), target_date),
    )
    if not selections:
        return {"available": False, "reason": "no_models_for_target_horizon"}
    selected_version_ids = {
        str(row["version_id"])
        for row in selections
        if row.get("version_id") is not None
    }
    manifests = _installed_manifests(
        registry,
        version_ids=selected_version_ids,
    )
    members: list[dict[str, Any]] = []
    batch_ids: dict[str, str] = {}
    for version_id in dict.fromkeys(row["version_id"] for row in selections):
        manifest = manifests.get(version_id)
        if manifest is None:
            return {"available": False, "reason": "selected_version_not_installed"}
        result = mushroom_ml_multiversion_comparison.compare_selection(
            registry,
            manifest,
            [row for row in selections if row["version_id"] == version_id],
            species_id=species_id,
            area_id=area_id,
            target_date=target_date,
            models_root=mushroom_paths.mushroom_ml_models_dir(),
            known_sites_path=mushroom_paths.mushroom_known_sites_path(),
            weather_data_dir=mushroom_paths.weather_data_dir(),
            prepared_weather_cache=_prepared_weather_cache.get(),
        )
        batch_ids[version_id] = str(result["batch_id"])
        members.extend(result["members"])
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
    operational = (
        mushroom_ml_multiversion_comparison.build_selected_operational_comparison(
            members,
            season_phase=_get_predictor(species_id).season_phase(target_date),
            phenology=dict(species_profile.get("phenology") or {}),
        )
    )
    return {
        "available": True,
        "batch_ids": batch_ids,
        "members": members,
        "operational_comparison": operational,
        "preferred_version_id": registry.get("preferred_version_id"),
    }


def _render_multiversion_result(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    if not payload.get("available"):
        return (
            f'<div class="pred-empty">{html.escape(_lbl("ui.predictor_multiversion_unavailable"))}</div>'
        )
    members = [row for row in payload.get("members", []) if isinstance(row, dict)]
    version_names = _VERSION_SHORT_NAMES
    by_version: dict[str, list[dict[str, Any]]] = {}
    for member in members:
        version_id = str((member.get("model_ref") or {}).get("version_id") or "")
        by_version.setdefault(version_id, []).append(member)
    operational = payload.get("operational_comparison") or {}
    winner_keys = {
        (
            str(ref.get("version_id") or ""),
            str(ref.get("profile_id") or ""),
            str(ref.get("temporal_contract_id") or ""),
            str(ref.get("estimator_id") or ""),
            int(ref.get("horizon_days") or 0),
        )
        for winner in operational.get("selected_winners") or []
        if isinstance(winner, dict)
        and isinstance((ref := winner.get("model_ref")), dict)
    }
    winner_version_ids = {key[0] for key in winner_keys}

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

    def metric(value: object) -> str:
        return f"{float(value):.3f}" if isinstance(value, (int, float)) else "—"

    def signed_metric(value: object) -> str:
        return f"{float(value):+.3f}" if isinstance(value, (int, float)) else "—"

    def scenario_context(estimators: dict[str, dict[str, Any]]) -> str:
        member = next(
            (row for row in estimators.values() if row.get("available")),
            next(iter(estimators.values()), {}),
        )
        metadata = member.get("metadata") or {}
        features = member.get("features_used") or {}
        facts = []
        cutoff = metadata.get("cutoff_date")
        if cutoff:
            facts.append(f"Corte meteorológico: {cutoff}")
        rain_bands = [
            features.get(key)
            for key in (
                "rain_cutoff_0_3d_mm",
                "rain_cutoff_4_7d_mm",
                "rain_cutoff_8_14d_mm",
                "rain_cutoff_15_21d_mm",
            )
        ]
        if any(value is not None for value in rain_bands):
            facts.append(
                "Lluvia 0–3 / 4–7 / 8–14 / 15–21 días: "
                + " · ".join(
                    f"{float(value):.2f} mm" if isinstance(value, (int, float)) else "—"
                    for value in rain_bands
                )
            )
        days_rain = features.get("days_since_rain_gt_2_at_target")
        if days_rain is not None:
            facts.append(f"Días desde lluvia >2 mm: {_comparison_value(days_rain, ' d')}")
        days_significant = features.get("days_since_significant_rain_at_target")
        if days_significant is not None:
            facts.append(
                "Días desde lluvia significativa: "
                f"{_comparison_value(days_significant, ' d')}"
            )
        if features.get("rain_observed_days_21") is not None:
            facts.append(
                "Cobertura lluvia 21d (observados / ausentes / suprimidos): "
                f'{_comparison_value(features.get("rain_observed_days_21"))} / '
                f'{_comparison_value(features.get("rain_missing_days_21"))} / '
                f'{_comparison_value(features.get("rain_suppressed_days_21"))}'
            )
        if features.get("rain_observed_days_90") is not None:
            facts.append(
                "Cobertura lluvia 90d (observados / ausentes / suprimidos): "
                f'{_comparison_value(features.get("rain_observed_days_90"))} / '
                f'{_comparison_value(features.get("rain_missing_days_90"))} / '
                f'{_comparison_value(features.get("rain_suppressed_days_90"))}'
            )
        temp_days = features.get("temp_observed_days_after_significant_rain")
        humidity_days = features.get("humidity_observed_days_after_significant_rain")
        if temp_days is not None or humidity_days is not None:
            facts.append(
                "Cobertura posterior a lluvia: "
                f"T {_comparison_value(temp_days)} d · H {_comparison_value(humidity_days)} d"
            )
        help_by_label = {
            "Corte meteorológico": "ui.predictor_help_weather_cutoff",
            "Lluvia 0–3 / 4–7 / 8–14 / 15–21 días": "ui.predictor_help_rain_bands",
            "Días desde lluvia >2 mm": "ui.predictor_help_days_since_rain",
            "Días desde lluvia significativa": "ui.predictor_help_days_since_significant_rain",
            "Cobertura lluvia 21d (observados / ausentes / suprimidos)": "ui.predictor_help_rain_coverage",
            "Cobertura lluvia 90d (observados / ausentes / suprimidos)": "ui.predictor_help_rain_coverage",
            "Cobertura posterior a lluvia": "ui.predictor_help_post_rain_coverage",
        }
        rendered = []
        for fact in facts:
            if ":" not in fact:
                rendered.append(f"<span>{html.escape(fact)}</span>")
                continue
            label, value = fact.split(":", 1)
            help_key = help_by_label.get(label)
            rendered_label = (
                _tooltip_label(label, help_key)
                if help_key
                else f"<strong>{html.escape(label)}</strong>"
            )
            rendered.append(
                f'<span>{rendered_label}: {html.escape(value.strip())}</span>'
            )
        return "".join(rendered)

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
            f'<th>{_tooltip_label(_ESTIMATOR_SHORT_NAMES.get(estimator_id, estimator_id), _ESTIMATOR_HELP_KEYS.get(estimator_id, "ui.predictor_help_estimator_generic"), strong=False)}</th>'
            for estimator_id in estimator_ids
        )
        body_rows = []
        for (profile_id, contract_id, horizon), estimators in sorted(grouped.items()):
            contract_name = "Ventana fija" if contract_id.startswith("fixed_gap_") else "Retardo/evento"
            cells = []
            available_probabilities = []
            selected_estimator_ids: set[str] = set()
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
                ref = member.get("model_ref") or {}
                is_winner = (
                    str(ref.get("version_id") or ""),
                    str(ref.get("profile_id") or ""),
                    str(ref.get("temporal_contract_id") or ""),
                    str(ref.get("estimator_id") or ""),
                    int(ref.get("horizon_days") or 0),
                ) in winner_keys
                if is_winner:
                    selected_estimator_ids.add(estimator_id)
                probability = prediction.get("probability")
                if isinstance(probability, (int, float)):
                    available_probabilities.append(float(probability))
                cells.append(
                    f'<td class="pred-member-result{" pred-member-selected" if is_winner else ""}">'
                    f'<strong>{html.escape(_pct(probability))}</strong>'
                    f'{"<small>Elegido</small>" if is_winner else ""}'
                    '</td>'
                )
            available = [
                row for row in estimators.values() if row.get("available")
            ]
            representative = available[0] if available else next(iter(estimators.values()), {})
            cutoff = str((representative.get("metadata") or {}).get("cutoff_date") or "—")
            baseline = next(
                (
                    (row.get("evaluation") or {}).get("prevalence_brier_score")
                    for row in available
                    if isinstance(
                        (row.get("evaluation") or {}).get("prevalence_brier_score"),
                        (int, float),
                    )
                ),
                None,
            )
            diagnostics = []

            def diagnostic_values(value_for: Callable[[str], str]) -> str:
                values = []
                for estimator_id in estimator_ids:
                    value = (
                        f'{_ESTIMATOR_SHORT_NAMES.get(estimator_id, estimator_id)} '
                        f'{value_for(estimator_id)}'
                    )
                    escaped = html.escape(value)
                    if estimator_id in selected_estimator_ids:
                        escaped = f'<span class="pred-diagnostic-selected">{escaped}</span>'
                    values.append(escaped)
                return " · ".join(values)

            briers = diagnostic_values(
                lambda estimator_id: metric(
                    (estimators.get(estimator_id, {}).get("evaluation") or {}).get(
                        "brier_score"
                    )
                )
            )
            diagnostics.append(
                f'<span>{_tooltip_label_key("ui.predictor_validation_brier", "ui.predictor_help_brier")}: '
                f'base {metric(baseline)} · {briers}</span>'
            )
            deltas = diagnostic_values(
                lambda estimator_id: signed_metric(
                    (estimators.get(estimator_id, {}).get("evaluation") or {}).get(
                        "brier_delta_vs_prevalence"
                    )
                )
            )
            diagnostics.append(
                f'<span>{_tooltip_label("Δ Brier frente a prevalencia", "ui.predictor_help_brier_delta")}: '
                f'{deltas}</span>'
            )
            aucs = diagnostic_values(
                lambda estimator_id: metric(
                    (estimators.get(estimator_id, {}).get("evaluation") or {}).get(
                        "roc_auc"
                    )
                )
            )
            diagnostics.append(
                f'<span>{_tooltip_label_key("ui.predictor_validation_auc", "ui.predictor_help_roc_auc")}: '
                f'{aucs}</span>'
            )
            samples = " · ".join(
                f'{_ESTIMATOR_SHORT_NAMES.get(estimator_id, estimator_id)} '
                f'{(estimators.get(estimator_id, {}).get("evaluation") or {}).get("n_test", "—")}'
                for estimator_id in estimator_ids
            )
            diagnostics.append(
                f'<span>{_tooltip_label("Muestra hold-out", "ui.predictor_help_holdout_sample")}: '
                f'{html.escape(samples)}</span>'
            )
            validation = diagnostic_values(
                lambda estimator_id: evidence_labels.get(
                    str(
                        (estimators.get(estimator_id, {}).get("evaluation") or {}).get(
                            "evidence"
                        )
                        or "not_evaluated"
                    ),
                    "sin evaluación",
                )
            )
            diagnostics.append(
                f'<span>{_tooltip_label("Evidencia frente a prevalencia", "ui.predictor_help_prevalence_evidence")}: '
                f'{validation}</span>'
            )
            domains = diagnostic_values(
                lambda estimator_id: applicability_labels.get(
                    str(
                        (
                            (estimators.get(estimator_id, {}).get("prediction") or {}).get(
                                "applicability"
                            )
                            or {}
                        ).get("status")
                        or ""
                    ),
                    "sin dato",
                )
            )
            diagnostics.append(
                f'<span>{_tooltip_label("Aplicabilidad actual", "ui.predictor_help_out_of_domain")}: '
                f'{domains}</span>'
            )
            diagnostics.append(
                f'<span>{_tooltip_label_key("ui.predictor_horizon", "ui.predictor_help_horizon")}: '
                f'{horizon} d</span>'
            )
            context = scenario_context(estimators)
            column_count = 3 + len(estimator_ids)
            mean_probability = (
                sum(available_probabilities) / len(available_probabilities)
                if available_probabilities
                else None
            )
            body_rows.append(
                f'<tr><td><strong>{html.escape(profile_id)} · {html.escape(contract_name)}</strong></td>'
                f'<td>{html.escape(cutoff)}</td>{"".join(cells)}<td>{html.escape(_pct(mean_probability))}</td></tr>'
                f'<tr class="pred-comparison-diagnostics-row"><td colspan="{column_count}">'
                f'<div class="pred-comparison-diagnostics">{"".join(diagnostics)}{context}</div></td></tr>'
            )
        short_version = version_names.get(version_id, version_id)
        open_attribute = " open" if version_id in winner_version_ids else ""
        breakdowns.append(f"""
<details class="pred-version-breakdown"{open_attribute}>
  <summary>{html.escape(short_version)} · detalle completo</summary>
  <div class="pred-table-scroll"><table class="pred-comparison-table"><thead><tr>
    <th>{_tooltip_label_key("ui.predictor_model", "ui.predictor_help_model", strong=False)}</th>
    <th>{_tooltip_label_key("ui.predictor_weather_cutoff", "ui.predictor_help_weather_cutoff", strong=False)}</th>
    {header}<th>{_tooltip_label_key("ui.predictor_unweighted_mean", "ui.predictor_help_unweighted_mean", strong=False)}</th>
  </tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>
</details>""")
    return f"""
<section class="pred-multiversion-result">
  <h3>Detalle técnico de la predicción multiversión</h3>
  <p>Las versiones incluidas participan en igualdad. Cada bloque conserva los porcentajes y la auditoría completa de sus perfiles, contratos y algoritmos. La celda resaltada identifica el modelo elegido para cada escenario temporal.</p>
  <div class="pred-version-breakdowns">{''.join(breakdowns)}</div>
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
    minimum_text = _operational_pct(float(minimum))
    maximum_text = _operational_pct(float(maximum))
    if minimum_text == maximum_text:
        return minimum_text
    return f"{minimum_text}–{maximum_text}"


def _probability_range(value: object) -> str:
    if not isinstance(value, dict):
        return "—"
    minimum = value.get("min")
    maximum = value.get("max")
    if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
        return "—"
    minimum_text = _operational_pct(float(minimum))
    maximum_text = _operational_pct(float(maximum))
    if minimum_text == maximum_text:
        return minimum_text
    return f"{minimum_text}–{maximum_text}"


def _compact_interpretation_range(interpretation: dict[str, Any]) -> str:
    return _reference_range(interpretation)


def _selected_model_source(comparison: dict[str, Any] | None) -> str:
    """Return compact, stable provenance for the operational winners."""
    if not isinstance(comparison, dict):
        return ""
    sources: list[str] = []
    for winner in comparison.get("selected_winners") or []:
        if not isinstance(winner, dict):
            continue
        ref = winner.get("model_ref") or {}
        if not isinstance(ref, dict):
            continue
        estimator_id = str(ref.get("estimator_id") or "")
        version_id = str(ref.get("version_id") or "")
        if not estimator_id or not version_id:
            continue
        source = (
            f"{_ESTIMATOR_SHORT_NAMES.get(estimator_id, estimator_id)}–"
            f"{_VERSION_SHORT_NAMES.get(version_id, version_id)}"
        )
        if source not in sources:
            sources.append(source)
    return " · ".join(sources)


_ABSTENTION_REASON_LABELS = {
    "unacceptable_applicability": "ui.predictor_abstention_applicability",
    "brier_not_better_than_prevalence": "ui.predictor_abstention_brier",
    "roc_auc_below_minimum": "ui.predictor_abstention_auc_below_minimum",
    "roc_auc_unavailable": "ui.predictor_abstention_auc_unavailable",
    "member_unavailable": "ui.predictor_abstention_model_unavailable",
    "invalid_probability": "ui.predictor_abstention_invalid_probability",
}


def _operational_abstention_rows(
    comparison: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(comparison, dict):
        return []
    rows: list[dict[str, Any]] = []
    for result_key in comparison.get("operational_result_keys") or []:
        result = comparison.get(result_key)
        if (
            not isinstance(result, dict)
            or result.get("reason") != "no_eligible_selected_member"
        ):
            continue
        reason_codes: list[str] = []
        for exclusion in result.get("candidate_exclusions") or []:
            if not isinstance(exclusion, dict):
                continue
            for reason in exclusion.get("reasons") or []:
                reason = str(reason)
                if reason in _ABSTENTION_REASON_LABELS and reason not in reason_codes:
                    reason_codes.append(reason)
        family = "fixed" if ":fixed:" in str(result_key) else "lag"
        rows.append(
            {
                "temporal_family": family,
                "horizon_days": result.get("horizon_days"),
                "reason_codes": reason_codes,
            }
        )
    return rows


def _abstention_reason_text(reason_codes: list[str]) -> str:
    if not reason_codes:
        return _lbl("ui.predictor_abstention_no_eligible")
    return " · ".join(
        _lbl(_ABSTENTION_REASON_LABELS[reason]) for reason in reason_codes
    )


def _compact_operational_abstention(comparison: dict[str, Any] | None) -> str:
    rows = _operational_abstention_rows(comparison)
    if not rows:
        return ""
    reason_codes: list[str] = []
    for row in rows:
        for reason in row["reason_codes"]:
            if reason not in reason_codes:
                reason_codes.append(reason)
    return _lbl("ui.predictor_abstention_compact").format(
        reasons=_abstention_reason_text(reason_codes)
    )


def _scenario_abstentions_html(comparison: dict[str, Any]) -> str:
    rendered: list[str] = []
    for row in _operational_abstention_rows(comparison):
        family = str(row.get("temporal_family") or "")
        scenario_key = (
            "ui.predictor_consensus_window"
            if family == "fixed"
            else "ui.predictor_consensus_delay"
        )
        scenario = _lbl(scenario_key).format(horizon=row.get("horizon_days"))
        rendered.append(
            '<span class="pred-scenario-abstention">'
            f"<strong>{html.escape(scenario)}</strong>: "
            f"{html.escape(_abstention_reason_text(row['reason_codes']))}"
            "</span>"
        )
    if not rendered:
        return ""
    return (
        '<div class="pred-scenario-abstentions">'
        f'<span>{html.escape(_lbl("ui.predictor_abstention_title"))}</span>'
        f'{"".join(rendered)}</div>'
    )


def _interpretation_sort_key(interpretation: dict[str, Any]) -> tuple[int, float]:
    verdict = str(interpretation.get("verdict", "abstain"))
    rank = {"favorable": 5, "uncertain": 4, "unfavorable": 1, "abstain": 0}.get(verdict, 0)
    if verdict == "abstain":
        rank = 3 if interpretation.get("ecological_compatibility") == "compatible" else 0
    value = interpretation.get("reference_range")
    midpoint = value.get("midpoint") if isinstance(value, dict) else None
    return rank, float(midpoint) if isinstance(midpoint, (int, float)) else -1.0


def _scenario_consensus_html(comparison: dict[str, Any]) -> str:
    rows = [
        row
        for row in comparison.get("scenario_consensus") or []
        if isinstance(row, dict)
        and str(row.get("status") or "") != "no_eligible_family"
    ]
    if not rows:
        return ""
    rendered: list[str] = []
    for row in rows:
        family = str(row.get("temporal_family") or "")
        horizon = row.get("horizon_days")
        scenario_key = (
            "ui.predictor_consensus_window"
            if family == "fixed"
            else "ui.predictor_consensus_delay"
        )
        scenario = _lbl(scenario_key).format(horizon=horizon)
        status = str(row.get("status") or "")
        estimator_names = [
            _ESTIMATOR_SHORT_NAMES.get(str(estimator_id), str(estimator_id))
            for estimator_id in row.get("eligible_estimator_ids") or []
            if estimator_id
        ]
        family_count = row.get("eligible_family_count")
        method_names = [
            _lbl(f"ui.predictor_method_family_{family_id}")
            for family_id in row.get("eligible_methodological_family_ids") or []
        ]
        if status == "single_family":
            detail = _lbl("ui.predictor_consensus_single_family").format(
                count=family_count
            )
        else:
            detail = _lbl(f"ui.predictor_consensus_{status}")
            gap = row.get("maximum_probability_gap")
            if isinstance(gap, (int, float)) and not isinstance(gap, bool):
                detail += " · " + _lbl("ui.predictor_consensus_gap").format(
                    points=round(float(gap) * 100)
                )
        families = "/".join(method_names)
        if families:
            detail += f" · {families}"
        elif estimator_names:
            detail += f" · {'/'.join(estimator_names)}"
        internal_details: list[str] = []
        for method in row.get("methodological_families") or []:
            if not isinstance(method, dict) or method.get("estimator_count", 0) < 2:
                continue
            family_id = str(method.get("methodological_family_id") or "")
            internal_status = str(method.get("internal_agreement_status") or "")
            names = [
                _ESTIMATOR_SHORT_NAMES.get(str(value), str(value))
                for value in method.get("estimator_ids") or []
            ]
            internal = (
                f'{_lbl(f"ui.predictor_method_family_{family_id}")}: '
                f'{_lbl(f"ui.predictor_consensus_{internal_status}")}'
            )
            gap = method.get("internal_maximum_probability_gap")
            if isinstance(gap, (int, float)) and not isinstance(gap, bool):
                internal += " · " + _lbl("ui.predictor_consensus_gap_decimal").format(
                    points=f"{float(gap) * 100:.1f}"
                )
            if names:
                internal += f" · {'/'.join(names)}"
            internal_details.append(internal)
        rendered.append(
            '<div class="pred-scenario-consensus">'
            '<div class="pred-scenario-row-main">'
            f"<strong>{html.escape(scenario)}</strong>: {html.escape(detail)}"
            "</div>"
            + (
                '<div class="pred-scenario-internal">'
                + html.escape(_lbl("ui.predictor_internal_agreement"))
                + ": "
                + html.escape("; ".join(internal_details))
                + "</div>"
                if internal_details
                else ""
            )
            + "</div>"
        )
    return "".join(rendered)


def _scenario_evidence_html(comparison: dict[str, Any]) -> str:
    rows: list[str] = []
    for winner in comparison.get("selected_winners") or []:
        if not isinstance(winner, dict):
            continue
        ref = winner.get("model_ref") or {}
        if not isinstance(ref, dict):
            continue
        contract = str(ref.get("temporal_contract_id") or "")
        scenario_key = (
            "ui.predictor_consensus_window"
            if contract.startswith("fixed_gap_")
            else "ui.predictor_consensus_delay"
        )
        scenario = _lbl(scenario_key).format(horizon=ref.get("horizon_days"))
        evidence: list[str] = []
        brier_gain = winner.get("brier_delta_vs_prevalence")
        if isinstance(brier_gain, (int, float)) and not isinstance(brier_gain, bool):
            evidence.append(
                _lbl("ui.predictor_scenario_brier_gain").format(
                    value=f"{float(brier_gain):.3f}"
                )
            )
        roc_auc = winner.get("roc_auc")
        if isinstance(roc_auc, (int, float)) and not isinstance(roc_auc, bool):
            evidence.append(f"ROC-AUC {float(roc_auc):.3f}")
        test_samples = winner.get("test_samples")
        if isinstance(test_samples, int) and not isinstance(test_samples, bool):
            evidence.append(
                _lbl("ui.predictor_scenario_holdout").format(count=test_samples)
            )
        applicability = str(winner.get("applicability_status") or "")
        if applicability in {"within_observed_range", "caution"}:
            evidence.append(_lbl(f"ui.predictor_scenario_applicability_{applicability}"))
        if evidence:
            rows.append(
                '<div class="pred-scenario-evidence">'
                f"<strong>{html.escape(scenario)}</strong>: "
                f'{html.escape(" · ".join(evidence))}</div>'
            )
    if not rows:
        return ""
    summary = comparison.get("statistical_reliability_summary") or {}
    summary = summary if isinstance(summary, dict) else {}
    summary_status = str(summary.get("status") or "")
    if not summary_status:
        legacy_status = str(
            _interpretation(comparison).get("statistical_support") or ""
        )
        summary_status = {
            "strong": "high",
            "moderate": "moderate",
            "limited": "limited",
        }.get(legacy_status, "unavailable")
    summary_verdict = _lbl(
        f"ui.predictor_statistical_reliability_{summary_status}"
    )
    return (
        '<div class="pred-scenario-evidence-group">'
        f'<div class="pred-scenario-group-title">{_tooltip_label_key("ui.predictor_statistical_support", "ui.predictor_help_statistical_support")}: '
        f'<span class="pred-scenario-verdict pred-scenario-verdict-{html.escape(summary_status)}">{html.escape(summary_verdict)}</span></div>'
        f'{"".join(rows)}</div>'
    )


def _render_interpretation_card(
    comparison: dict[str, Any],
    species_name: str,
    area_name: str,
    target_date: date,
) -> str:
    interpretation = _interpretation(comparison)
    status = _interpretation_status(interpretation)
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
    if "feature_sets_use_different_stations" in reason_codes:
        ecological_detail_keys.append("ui.predictor_interpretation_different_stations")
    if "no_estimator_beats_prevalence" in reason_codes:
        statistical_detail_keys.append("ui.predictor_interpretation_no_trusted_model")
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
    multiversion = comparison.get("selection_mode") == "multiversion"
    selected_winners = [
        row
        for row in comparison.get("selected_winners") or []
        if isinstance(row, dict)
    ]
    display_reference_range = interpretation.get("reference_range")
    if selected_winners:
        selected_probabilities = [
            float(probability)
            for winner in selected_winners
            if not isinstance((probability := winner.get("probability")), bool)
            and isinstance(probability, (int, float))
        ]
        if selected_probabilities:
            display_reference_range = {
                "min": min(selected_probabilities),
                "max": max(selected_probabilities),
            }
    range_html = ""
    if isinstance(display_reference_range, dict):
        range_label_key = (
            "ui.predictor_selected_range"
            if multiversion
            else "ui.predictor_operational_range"
        )
        range_html = (
            f'<div class="pred-interpretation-range">'
            f'<span>{html.escape(_lbl(range_label_key))}</span>'
            f'<strong>{html.escape(_probability_range(display_reference_range))}</strong>'
            f'</div>'
        )
    consensus_rows_html = _scenario_consensus_html(comparison)
    consensus_summary = comparison.get("consensus_summary") or {}
    consensus_summary = (
        consensus_summary if isinstance(consensus_summary, dict) else {}
    )
    consensus_status = str(consensus_summary.get("status") or "")
    if not consensus_status:
        scenario_statuses = [
            str(row.get("status") or "")
            for row in comparison.get("scenario_consensus") or []
            if isinstance(row, dict)
            and row.get("status") in {"high", "moderate", "low"}
        ]
        fallback_rank = {"low": 1, "moderate": 2, "high": 3}
        consensus_status = (
            min(scenario_statuses, key=lambda value: fallback_rank[value])
            if scenario_statuses
            else "unavailable"
        )
    consensus_verdict = _lbl(f"ui.predictor_consensus_{consensus_status}")
    measured_consensus = consensus_summary.get("measurable_scenario_count")
    eligible_consensus = consensus_summary.get("eligible_scenario_count")
    consensus_coverage = ""
    if (
        isinstance(measured_consensus, int)
        and not isinstance(measured_consensus, bool)
        and isinstance(eligible_consensus, int)
        and not isinstance(eligible_consensus, bool)
        and eligible_consensus > 0
    ):
        consensus_coverage = " · " + _lbl(
            "ui.predictor_consensus_contrast_coverage"
        ).format(measured=measured_consensus, total=eligible_consensus)
    consensus_html = (
        '<div class="pred-scenario-consensus-group">'
        f'<div class="pred-scenario-group-title">{_tooltip_label_key("ui.predictor_consensus", "ui.predictor_help_consensus")}: '
        f'<span class="pred-scenario-verdict pred-scenario-verdict-{html.escape(consensus_status)}">{html.escape(consensus_verdict + consensus_coverage)}</span></div>'
        f"{consensus_rows_html}</div>"
        if consensus_rows_html
        else ""
    )
    abstentions_html = _scenario_abstentions_html(comparison)
    scenario_evidence_html = _scenario_evidence_html(comparison)
    winner_rows = []
    if selected_winners:
        for winner in selected_winners:
            if not isinstance(winner, dict):
                continue
            ref = winner.get("model_ref") or {}
            if not isinstance(ref, dict):
                continue
            estimator = _ESTIMATOR_SHORT_NAMES.get(
                str(ref.get("estimator_id") or ""),
                str(ref.get("estimator_id") or ""),
            )
            version = _VERSION_SHORT_NAMES.get(
                str(ref.get("version_id") or ""),
                str(ref.get("version_id") or ""),
            )
            contract = str(ref.get("temporal_contract_id") or "")
            family = "ventana" if contract.startswith("fixed_gap_") else "retardo"
            horizon = str(ref.get("horizon_days") or "")
            validation = "" if winner.get("validated") else (
                f' · {html.escape(_lbl("ui.predictor_selected_model_unvalidated"))}'
            )
            applicability = (
                f' · {html.escape(_lbl("ui.predictor_selected_model_caution"))}'
                if winner.get("applicability_status") == "caution"
                else ""
            )
            winner_rows.append(
                '<span class="pred-selected-model">'
                f'<strong>{html.escape(estimator)}–{html.escape(version)}</strong> '
                f'{html.escape(_operational_pct(winner.get("probability")))}'
                f'<small>{html.escape(family)} h{html.escape(horizon)}{validation}{applicability}</small>'
                '</span>'
            )
    winners_html = (
        '<div class="pred-selected-models">'
        f'<span>{html.escape(_lbl("ui.predictor_selected_models"))}</span>'
        f'{"".join(winner_rows)}</div>'
        if winner_rows
        else ""
    )
    quality_gate_html = ""
    minimum_roc_auc = comparison.get("minimum_roc_auc")
    if isinstance(minimum_roc_auc, (int, float)) and not isinstance(
        minimum_roc_auc, bool
    ):
        quality_gate_html = (
            '<p class="pred-quality-gate">'
            + html.escape(
                _lbl("ui.predictor_auc_gate_rule").format(
                    threshold=f"{float(minimum_roc_auc):.2f}"
                )
            )
            + "</p>"
        )
    role_key = (
        "ui.predictor_multiversion_card_role"
        if multiversion
        else "ui.predictor_active_version_role"
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
  {winners_html}
  {abstentions_html}
  {quality_gate_html}
  <p class="pred-version-role">{html.escape(_lbl(role_key))}</p>
  <div class="pred-interpretation-meta">
    <span>{_tooltip_label_key("ui.predictor_ecological_compatibility", "ui.predictor_help_ecological_compatibility")}: {html.escape(_lbl(f"ui.predictor_ecological_compatibility_{ecological_compatibility}"))}</span>
    <span>{_tooltip_label_key("ui.predictor_ecological_evidence", "ui.predictor_help_ecological_reliability")}: {html.escape(_lbl(f"ui.predictor_ecological_evidence_{ecological_evidence}"))}</span>
    {scenario_evidence_html}
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
            f'<a class="{cls}" href="{html.escape(href)}" data-predictor-direct-run>'
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

    all_results: list[tuple[dict[str, Any], str, str, str, str]] = []
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
                    all_results.append(
                        (
                            interpretation,
                            species_id,
                            area_id,
                            _selected_model_source(comparison),
                            _compact_operational_abstention(comparison),
                        )
                    )
        except FileNotFoundError:
            pass
        except Exception as exc:
            errors.append(f"{species_id}: {html.escape(_predictor_error_text(exc))}")

    all_results.sort(key=lambda row: _interpretation_sort_key(row[0]), reverse=True)
    ranked_results = [
        row for row in all_results if str(row[0].get("verdict") or "abstain") != "abstain"
    ]

    date_label = (
        "Hoy" if target_date == today
        else "Mañana" if target_date == today + timedelta(days=1)
        else f"{target_date.day}/{target_date.month}/{target_date.year}"
    )

    if not ranked_results:
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
    (
        best_interpretation,
        best_species,
        best_area,
        best_source,
        best_abstention,
    ) = ranked_results[0]
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
  <small class="pred-result-source">{html.escape(best_source or best_abstention)}</small>
  <div class="pred-best-hint">{html.escape(_interpretation_label(best_interpretation))}</div>
</div>
"""

    # Ranked list
    rows_html = ""
    area_options_by_species: dict[str, list[dict[str, str]]] = {}
    for interpretation, sp_id, area_id, model_source, abstention in ranked_results[:15]:
        sp_name = _species_name(sp_id, profiles_payload)
        area_n = _area_name(area_id, known_sites_payload)
        href = _url("query", sp_id, area_id, target_date)
        status = _interpretation_status(interpretation)
        rows_html += f"""
<a class="pred-rank-row {_status_cls(status)}" href="{html.escape(href)}" data-predictor-direct-run>
  <span class="pred-rank-dot">{_status_dot(status)}</span>
  <span class="pred-rank-species">{html.escape(sp_name)}</span>
  <span class="pred-rank-area">{html.escape(area_n)}</span>
  <span class="pred-rank-prob">{html.escape(_compact_interpretation_range(interpretation))}<small class="pred-result-source">{html.escape(model_source or abstention)}</small></span>
</a>
"""

    for sp_id in trained:
        try:
            area_ids = _get_predictor(sp_id).areas_with_species_observations()
        except Exception:
            area_ids = []
        area_options_by_species[sp_id] = [
            {"value": area_id, "label": _area_name(area_id, known_sites_payload)}
            for area_id in sorted(area_ids)
        ]
    area_map = html.escape(
        json.dumps(area_options_by_species, ensure_ascii=False, separators=(",", ":")),
        quote=True,
    )

    error_block = _render_errors(errors)
    return f"""
<section class="pred-section" data-predictor-area-map="{area_map}">
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
                model_source = _selected_model_source(comparison)
                abstention = _compact_operational_abstention(comparison)
                status = _interpretation_status(interpretation)
                cell_href = _url("query", species, area_id, d)
                row_cells += (
                    f'<td class="pred-cell {_status_cls(status)}">'
                    f'<a href="{html.escape(cell_href)}" data-predictor-direct-run>'
                    f'{_status_dot(status)} {html.escape(_compact_interpretation_range(interpretation))}'
                    f'<small class="pred-result-source">{html.escape(model_source or abstention)}</small>'
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
    area_options_by_species: dict[str, list[dict[str, str]]] = {species: []}
    try:
        area_options_by_species[species] = [
            {"value": area_id, "label": _area_name(area_id, known_sites_payload)}
            for area_id in sorted(_get_predictor(species).areas_with_species_observations())
        ]
    except Exception:
        pass
    area_options_html = f'<option value="">{html.escape(_lbl("ui.predictor_all_areas_option"))}</option>'
    for option in area_options_by_species.get(species, []):
        a_id = option["value"]
        sel = ' selected' if a_id == area else ''
        area_options_html += (
            f'<option value="{html.escape(a_id, quote=True)}"{sel}>'
            f'{html.escape(option["label"])}</option>'
        )
    area_map = html.escape(
        json.dumps(area_options_by_species, ensure_ascii=False, separators=(",", ":")),
        quote=True,
    )

    # Species options
    species_options_html = ""
    for sp_id in trained:
        sp_name = _species_name(sp_id, profiles_payload)
        sel = ' selected' if sp_id == species else ''
        species_options_html += f'<option value="{html.escape(sp_id)}"{sel}>{html.escape(sp_name)}</option>'

    comparison_toggle = (
        f'<a class="button-link secondary-link" data-predictor-direct-run href="{html.escape(_url("query", species, area, target_date, compare="0" if compare_models else "1", mvv=selected_versions))}">'
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
    preferred_control = _preferred_version_control(
        species,
        area,
        target_date,
        compare_models=compare_models,
        selected_versions=selected_versions,
    )
    form_html = f"""
<form class="pred-form" method="get" action="" data-predictor-direct-form
      data-predictor-area-map="{area_map}">
  <input type="hidden" name="view" value="query">
  <input type="hidden" name="compare" value="{1 if compare_models else 0}">
  {_executor_hidden_input()}
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.species"))}</label>
    <select name="species">{species_options_html}</select>
  </div>
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.known_site_area"))}</label>
    <select name="area">{area_options_html}</select>
  </div>
  <div class="pred-form-row">
    <label>{html.escape(_lbl("ui.date_short"))}</label>
    <input type="date" name="date" value="{html.escape(target_date.isoformat())}">
  </div>
  {preferred_control}
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
            selected_versions=selected_versions,
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
    selected_versions: list[str] | None = None,
) -> str:
    selected_multiversion = list(selected_multiversion or [])
    selected_versions = list(selected_versions or [])
    multiversion_payload: dict[str, Any] | None = None
    if selected_multiversion:
        try:
            multiversion_payload = _multiversion_result(
                species, area, target_date, selected_multiversion
            )
            comparison = (
                multiversion_payload.get("operational_comparison")
                if isinstance(multiversion_payload, dict)
                else None
            )
        except Exception as exc:
            return f'<div class="pred-error"><strong>Error:</strong> {html.escape(_predictor_error_text(exc))}</div>'
    else:
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
            if selected_multiversion:
                current_payload = (
                    multiversion_payload
                    if current_date == target_date
                    else _multiversion_result(
                        species,
                        area,
                        current_date,
                        selected_multiversion,
                    )
                )
                current_comparison = (
                    current_payload.get("operational_comparison")
                    if isinstance(current_payload, dict)
                    else None
                )
            else:
                current_comparison = _model_comparison(
                    species, area, current_date
                )
            current_interpretation = _interpretation(current_comparison)
            current_source = _selected_model_source(current_comparison)
            current_abstention = _compact_operational_abstention(
                current_comparison
            )
            status = _interpretation_status(current_interpretation)
            is_active = current_date == target_date
            day_name = ["L", "M", "X", "J", "V", "S", "D"][current_date.weekday()]
            href = _url(
                "query",
                species,
                area,
                current_date,
                reuse_result=True,
                compare="1" if compare_models else "",
                mvv=selected_versions,
            )
            cls = "pred-week-cell pred-week-active" if is_active else "pred-week-cell"
            week_cells += f"""
<a class="{cls} {_status_cls(status)}" href="{html.escape(href)}">
  <small>{day_name} {current_date.day}/{current_date.month}</small>
  <span>{_status_dot(status)}</span>
  <small>{html.escape(_compact_interpretation_range(current_interpretation))}</small>
  <small class="pred-result-source">{html.escape(current_source or current_abstention)}</small>
</a>
"""
    except Exception:
        pass

    if selected_multiversion:
        week_caption = _lbl("ui.predictor_multiversion_week_context")
    else:
        preferred_id = _preferred_version_id()
        preferred_name = _VERSION_SHORT_NAMES.get(preferred_id, preferred_id)
        week_caption = _lbl("ui.predictor_preferred_week_context").format(
            version=preferred_name
        )
    week_strip = (
        '<div class="pred-week-reference">'
        f'<small>{html.escape(week_caption)}</small>'
        f'<div class="pred-week-strip">{week_cells}</div></div>'
        if week_cells
        else ""
    )

    comparison_html = (
        _render_model_comparison(species, area, target_date)
        if compare_models and not selected_multiversion
        else ""
    )
    multiversion_html = ""
    if compare_models and selected_multiversion:
        multiversion_html = _render_multiversion_result(multiversion_payload)

    return f"""
{interpretation_card}
{week_strip}
{multiversion_html}
{comparison_html}
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
    model_ids = tuple(
        comparison.get("comparison_detail_result_keys")
        or comparison.get("operational_result_keys")
        or ()
    ) or (
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
    catalog = _multiversion_catalog_payload()
    preferred_id = str(catalog.get("preferred_version_id") or "")
    preferred_name = _VERSION_SHORT_NAMES.get(preferred_id, preferred_id or "—")
    return f"""
<section class="pred-model-comparison">
  <h3>{html.escape(_lbl("ui.predictor_preferred_detail_title").format(version=preferred_name))}</h3>
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
        (
            area_id,
            _interpretation(comparison),
            _selected_model_source(comparison),
            _compact_operational_abstention(comparison),
        )
        for area_id, comparison in comparisons
    ]
    interpreted.sort(key=lambda row: _interpretation_sort_key(row[1]), reverse=True)
    if interpreted and all(
        value.get("verdict") == "out_of_season"
        for _area_id, value, _source, _abstention in interpreted
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
    for area_id, interpretation, model_source, abstention in interpreted:
        area_n = _area_name(area_id, known_sites_payload)
        href = _url("query", species, area_id, target_date)
        area_bt = by_area_bt.get(area_id, {})
        ep_n = area_bt.get("episodes", 0) if area_bt else 0
        area_acc = area_bt.get("backtest_accuracy") if area_bt else None
        rel_badge = _rel_badge(ep_n)
        status = _interpretation_status(interpretation)
        rows_html += f"""
<a class="pred-rank-row {_status_cls(status)}" href="{html.escape(href)}" data-predictor-direct-run>
  <span class="pred-rank-dot">{_status_dot(status)}</span>
  <span class="pred-rank-area">{html.escape(area_n)}</span>
  <span class="pred-rank-prob">{html.escape(_compact_interpretation_range(interpretation))}<small class="pred-result-source">{html.escape(model_source or abstention)}</small></span>
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
    <select name="species">{species_options_html}</select>
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
            model_source = _selected_model_source(comparison)
        except Exception:
            interpretation = {}
            model_source = ""
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
                "model_source": model_source,
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
        model_source = str(r.get("model_source", ""))
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
  <td>{_status_dot(display_status)} {html.escape(display_prediction)} {html.escape(reference_range)}<small class="pred-result-source">{html.escape(model_source)}</small></td>
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
    job_token = _job_query.set((query.get("job_id") or [""])[0])
    executor_change_token = _allow_executor_change.set(allow_executor_change)
    training_freshness_token = _training_freshness.set(training_freshness)
    try:
        return _render_page_inner(query, profiles_payload, known_sites_payload)
    finally:
        _allow_executor_change.reset(executor_change_token)
        _comparison_cache.reset(comparison_cache_token)
        _prepared_weather_cache.reset(weather_cache_token)
        _prepared_response.reset(prepared_token)
        _job_query.reset(job_token)
        _executor_query.reset(executor_token)
        _training_freshness.reset(training_freshness_token)


def _render_training_freshness_warning() -> str:
    freshness = _training_freshness.get() or {}
    status = str(freshness.get("status", ""))
    if status == "current" or not status:
        return ""
    if status == "stale":
        warning_key = "ui.predictor_training_stale_warning"
        help_key = "ui.predictor_training_stale_help"
    elif status == "unknown":
        warning_key = "ui.predictor_training_unknown_warning"
        help_key = "ui.predictor_training_unknown_help"
    else:
        warning_key = "ui.predictor_training_invalid_warning"
        help_key = "ui.predictor_training_invalid_help"
    return (
        '<div class="pred-training-warning">'
        f'<strong>{html.escape(_lbl(warning_key))}</strong>'
        f'<span>{html.escape(_lbl(help_key))}</span>'
        "</div>"
    )


def _render_soilgrids_warning(known_sites_payload: dict[str, Any]) -> str:
    health = mushroom_soilgrids_reconciler.inspect_payload(known_sites_payload)
    unresolved = health.get("unresolved")
    count = len(unresolved) if isinstance(unresolved, list) else 0
    if not count:
        return ""
    return (
        '<div class="pred-training-warning">'
        f'<strong>{html.escape(_lbl("ui.soilgrids_warning_title"))}</strong>'
        f'<span>{html.escape(_lbl("ui.soilgrids_warning_help").replace("{count}", str(count)))}</span>'
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
    selected_versions = (
        resolved_query_versions(query) if view == "query" else list(query.get("mvv", []))
    )
    selected_multiversion = list(query.get("mv", []))
    if selected_versions:
        selected_multiversion = multiversion_tokens_for_versions(species, selected_versions)

    try:
        target_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        target_date = date.today()
    target_date = normalize_predictor_target_date(view, target_date)

    tabs = _render_tabs(view, species, target_date)
    preferred_badge = _preferred_version_badge()

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
    soilgrids_warning = _render_soilgrids_warning(known_sites_payload)
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
  {soilgrids_warning}
  {preferred_badge}
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
.pred-preferred-badge { display: inline-flex; align-items: center; gap: 0.45rem; margin: 0 0 0.8rem; padding: 0.35rem 0.65rem; border: 1px solid #526570; border-radius: 999px; background: #182127; color: #aebbc4; }
.pred-preferred-badge strong { color: #e8eef2; }

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
.pred-form-row { display: flex; flex-direction: column; gap: 0.3rem; align-self: flex-start; }
.pred-form-row label { font-size: 0.92rem; color: #9aa8b2; text-transform: uppercase; letter-spacing: 0.05em; }
.pred-form select, .pred-form input[type="date"] {
  background: #1b2229;
  border: 1px solid #33404a;
  color: #e8eef2;
  padding: 0.45rem 0.75rem;
  border-radius: 6px;
  font-size: 1rem;
  height: 2.55rem;
  box-sizing: border-box;
}
.pred-preferred-field select { min-width: 15rem; border-color: #4d6a79; }
.pred-week-reference { margin-top: 0.7rem; }
.pred-week-reference > small { display: block; color: #9aa8b2; margin-bottom: 0.35rem; }
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
.pred-member-selected {
  background: rgba(45, 184, 101, 0.17);
  box-shadow: inset 0 0 0 2px #39c96b;
}
.pred-member-selected strong { color: #63df8a; }
.pred-member-selected small { color: #aaf0bd; font-weight: 750; }
.pred-diagnostic-selected {
  color: #76e59a;
  background: rgba(45, 184, 101, 0.14);
  border-radius: 3px;
  padding: 0.02rem 0.2rem;
  font-weight: 750;
}
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
.pred-selected-models { display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem 0.65rem; margin-top: 0.65rem; color: #aebbc4; }
.pred-selected-model { display: inline-flex; align-items: baseline; gap: 0.3rem; padding: 0.3rem 0.55rem; border: 1px solid #526570; border-radius: 999px; background: #131c22; color: #dfe8ed; }
.pred-selected-model strong { color: #fff; }
.pred-selected-model small { color: #9eacb6; }
.pred-result-source { display: block; margin-top: 0.15rem; color: #8fa0aa; font-size: 0.76rem; font-weight: 500; }
.pred-quality-gate { font-size: 0.86rem; color: #aebbc4 !important; }
.pred-interpretation-meta { display: flex; flex-wrap: wrap; gap: 0.55rem 1.25rem; margin-top: 0.65rem; color: #aebbc4; }
.pred-interpretation-meta strong { color: #dfe8ed; }
.pred-scenario-evidence-group,
.pred-scenario-consensus-group {
  display: grid;
  flex-basis: 100%;
  gap: 0.45rem;
  width: 100%;
  font-size: 0.9rem;
  line-height: 1.4;
}
.pred-scenario-group-title { color: #aebbc4; font-size: inherit; font-weight: 700; }
.pred-scenario-verdict {
  display: inline-block;
  margin-left: 0.2rem;
  padding: 0.12rem 0.42rem;
  border: 1px solid #526570;
  border-radius: 999px;
  color: #dfe8ed;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.025em;
  text-transform: uppercase;
}
.pred-scenario-verdict-high { border-color: #51cf66; color: #7ee394; }
.pred-scenario-verdict-moderate { border-color: #ffd166; color: #ffe08a; }
.pred-scenario-verdict-limited,
.pred-scenario-verdict-low { border-color: #ff7b72; color: #ff9b94; }
.pred-scenario-verdict-unavailable { color: #9eacb6; }
.pred-scenario-evidence,
.pred-scenario-consensus { display: block; color: #c7d2d9; font-size: inherit; }
.pred-scenario-row-main { display: block; }
.pred-scenario-internal {
  display: block;
  margin-top: 0.2rem;
  padding-left: 0.85rem;
  color: #aebbc4;
  font-size: inherit;
}
.pred-scenario-abstentions { display: flex; flex-wrap: wrap; gap: 0.4rem 0.8rem; margin-top: 0.65rem; color: #d8ad69; }
.pred-scenario-abstention strong { color: #efd099; }
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
