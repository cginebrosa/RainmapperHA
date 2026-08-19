"""Execute exact installed V2--V6 members against one prepared weather context."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_raw_weather
from rainmapper_core import mushroom_ml_runtime_features
from rainmapper_core import mushroom_ml_runtime_inference
from rainmapper_core import mushroom_ml_quality_catalog
from rainmapper_core import mushroom_ml_area_weather_runtime
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw
from rainmapper_core.mushroom_ml_predictor import _label
from rainmapper_core.mushroom_prediction_interpretation import build_interpretation


V2_FIXED_CONTRACT_ID = "fixed_gap_7d_altitude_v2"
V2_LAG_CONTRACT_ID = "lag_event_altitude_v2"


def _load_quality_catalog(
    registry: Mapping[str, object],
    checked: Mapping[str, object],
    models_root: Path,
) -> dict[str, Any]:
    """Load declared evidence, with a verified promotion-source fallback."""
    quality_path: Path | None = None
    expected_sha = ""
    quality_ref = checked.get("quality_catalog")
    if isinstance(quality_ref, Mapping):
        quality_path = Path(models_root) / str(quality_ref.get("path") or "")
        expected_sha = str(quality_ref.get("sha256") or "")
    else:
        target = registry.get("active_operational_target")
        target = target if isinstance(target, Mapping) else {}
        generation_id = str(target.get("generation_id") or "")
        source_batch_id = ""
        for version in registry.get("versions", []):
            if not isinstance(version, Mapping):
                continue
            for generation in version.get("generations", []):
                if (
                    isinstance(generation, Mapping)
                    and str(generation.get("generation_id") or "") == generation_id
                ):
                    source_batch_id = str(
                        generation.get("source_benchmark_batch_id") or ""
                    )
                    break
        if source_batch_id:
            benchmark_root = Path(models_root) / "benchmarks" / source_batch_id
            benchmark_manifest_path = benchmark_root / "manifest.json"
            if benchmark_manifest_path.is_file():
                benchmark_manifest = json.loads(
                    benchmark_manifest_path.read_text(encoding="utf-8")
                )
                source_ref = benchmark_manifest.get("quality_catalog")
                if isinstance(source_ref, Mapping):
                    quality_path = benchmark_root / "quality-catalog.json"
                    expected_sha = str(source_ref.get("sha256") or "")
    if quality_path is None or not quality_path.is_file() or not expected_sha:
        return {}
    content = quality_path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha:
        return {}
    loaded = json.loads(content)
    if (
        not isinstance(loaded, dict)
        or loaded.get("kind") != mushroom_ml_quality_catalog.KIND
        or loaded.get("schema_version") != mushroom_ml_quality_catalog.SCHEMA_VERSION
    ):
        return {}
    return loaded


def _interpretation_features(sample: Mapping[str, object]) -> dict[str, object]:
    """Keep model inputs pure while forwarding ecological evidence to interpretation.

    Version adapters may wrap the source quality mapping (for example V4 wraps
    the V3 evidence).  Walk every nested quality mapping so a new profile or
    version cannot silently lose the common ecological contract merely because
    it adds another adapter layer.
    """
    features = dict(sample.get("predictive_features") or {})
    quality = sample.get("quality")
    quality = quality if isinstance(quality, Mapping) else {}
    quality_sources: list[Mapping[str, object]] = []
    pending: list[Mapping[str, object]] = [quality]
    while pending:
        source = pending.pop(0)
        quality_sources.append(source)
        pending.extend(
            value for value in source.values() if isinstance(value, Mapping)
        )
    for key in (
        "days_since_significant_rain_at_target",
        "significant_rain_found_90d",
        "significant_rain_search_complete",
        "rain_event_search_complete",
    ):
        for source in quality_sources:
            if key in source:
                features[key] = source[key]
                break
    return features


def compare_prepared(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    model_refs: Sequence[catalog.ModelRef | Mapping[str, object]],
    *,
    models_root: Path,
    target_date: date,
    area_id: str,
    area_context: Any,
    area_series_by_horizon: Mapping[int, Mapping[str, object]],
    stations: Mapping[tuple[str, str], Any],
    checked_manifest: Mapping[str, object] | None = None,
    comparison_cache: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare individual members; quality precedes output and no mean is made."""
    checked = (
        checked_manifest
        if checked_manifest is not None
        else catalog.validate_batch_manifest(registry, manifest)
    )
    quality_catalog = (
        comparison_cache.get("quality_catalog")
        if comparison_cache is not None
        else None
    )
    if not isinstance(quality_catalog, dict):
        quality_catalog = _load_quality_catalog(registry, checked, models_root)
        if comparison_cache is not None:
            comparison_cache["quality_catalog"] = quality_catalog
    artifact_index = (
        comparison_cache.get("artifact_index")
        if comparison_cache is not None
        else None
    )
    if not isinstance(artifact_index, dict):
        artifact_index = {
            (
                row["artifact_ref"]["version_id"],
                row["artifact_ref"]["temporal_contract_id"],
                row["artifact_ref"]["profile_id"],
                row["artifact_ref"]["estimator_id"],
                row["artifact_ref"]["species_id"],
                horizon,
            ): row
            for row in checked["artifacts"]
            for horizon in row["supported_horizons"]
        }
        if comparison_cache is not None:
            comparison_cache["artifact_index"] = artifact_index
    results: list[dict[str, Any]] = []
    for raw_ref in model_refs:
        model_ref = (
            raw_ref
            if isinstance(raw_ref, catalog.ModelRef)
            else catalog.validate_model_ref(registry, raw_ref)
        )
        base = {"model_ref": model_ref.as_dict(), "model_ref_key": model_ref.key}
        area_series = area_series_by_horizon.get(model_ref.horizon_days)
        if area_series is None:
            results.append(
                {
                    **base,
                    "available": False,
                    "reason": "prepared_weather_horizon_missing",
                }
            )
            continue
        try:
            sample = mushroom_ml_runtime_features.build_runtime_features(
                model_ref,
                target_date=target_date,
                area_id=area_id,
                area_context=area_context,
                area_series=area_series,
                stations=stations,
            )
            quality = dict(sample.get("quality") or {})
            if quality.get("inference_eligible") is False:
                results.append(
                    {
                        **base,
                        "available": False,
                        "reason": "runtime_feature_gates_failed",
                        "quality": quality,
                        "metadata": dict(sample.get("metadata") or {}),
                    }
                )
                continue
            artifact_key = (
                model_ref.version_id,
                model_ref.temporal_contract_id,
                model_ref.profile_id,
                model_ref.estimator_id,
                model_ref.species_id,
                model_ref.horizon_days,
            )
            shared_key = (*artifact_key[:4], "all_species", artifact_key[5])
            artifact_row = artifact_index.get(artifact_key) or artifact_index.get(
                shared_key
            )
            if artifact_row is None:
                raise FileNotFoundError(
                    f"Model is not present in runtime batch: {model_ref.key}"
                )
            bundle = mushroom_ml_runtime_inference.load_exact_artifact(
                registry,
                checked,
                model_ref,
                root=models_root,
                checked_manifest=checked,
                artifact_row=artifact_row,
                validated_model_ref=model_ref,
            )
            prediction = mushroom_ml_runtime_inference.predict_bundle(
                bundle,
                dict(sample.get("predictive_features") or {}),
                species_id=model_ref.species_id,
            )
            results.append(
                {
                    **base,
                    "available": True,
                    "prediction": prediction,
                    "quality": quality,
                    "metadata": dict(sample.get("metadata") or {}),
                    "evaluation": mushroom_ml_quality_catalog.lookup(
                        quality_catalog, model_ref.as_dict()
                    ),
                    "features_used": _interpretation_features(sample),
                }
            )
        except FileNotFoundError as exc:
            results.append(
                {
                    **base,
                    "available": False,
                    "reason": "model_not_installed",
                    "message": str(exc),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            results.append(
                {
                    **base,
                    "available": False,
                    "reason": "runtime_model_incompatible",
                    "message": str(exc),
                }
            )
    return {
        "batch_id": checked["batch_id"],
        "snapshot_id": checked["snapshot_id"],
        "area_id": area_id,
        "target_date": target_date.isoformat(),
        "members": results,
        "quality_before_consensus": True,
        "consensus_computed": False,
        "ensemble_computed": False,
        "version_cautions": dict(quality_catalog.get("version_cautions") or {}),
        "species_metrics_are_never_averaged": True,
    }


def _contract_result(
    contract_id: str,
    members: Sequence[Mapping[str, object]],
    *,
    horizon_days: int,
    profile_id: str | None = None,
) -> dict[str, Any]:
    matching = [
        row
        for row in members
        if str((row.get("model_ref") or {}).get("temporal_contract_id") or "")
        == contract_id
        and (
            profile_id is None
            or str((row.get("model_ref") or {}).get("profile_id") or "")
            == profile_id
        )
    ]
    available = [row for row in matching if row.get("available") is True]
    if not available:
        first = matching[0] if matching else {}
        return {
            "available": False,
            "reason": str(first.get("reason") or "model_not_installed"),
            "horizon_days": horizon_days,
        }
    probabilities: dict[str, float] = {}
    estimators: dict[str, dict[str, object]] = {}
    baseline_scores: list[float] = []
    exclusions: dict[str, dict[str, object]] = {}
    for row in available:
        model_ref = row.get("model_ref") or {}
        estimator_id = str(model_ref.get("estimator_id") or "")
        prediction = row.get("prediction") or {}
        probability = prediction.get("probability")
        if estimator_id and isinstance(probability, (int, float)):
            probabilities[estimator_id] = float(probability)
        evaluation = row.get("evaluation") or {}
        brier = evaluation.get("brier_score")
        baseline = evaluation.get("prevalence_brier_score")
        if isinstance(baseline, (int, float)):
            baseline_scores.append(float(baseline))
        if estimator_id and isinstance(brier, (int, float)):
            estimators[estimator_id] = {
                "brier_score": float(brier),
                "roc_auc": evaluation.get("roc_auc"),
                "n": evaluation.get("n_test"),
            }
        extreme = list((prediction.get("applicability") or {}).get("most_extreme") or [])
        if estimator_id == "logistic_regression_reduced_v1" and any(
            isinstance(item, Mapping)
            and isinstance(item.get("standard_deviations"), (int, float))
            and float(item["standard_deviations"]) >= 6.0
            for item in extreme
        ):
            exclusions[estimator_id] = {"reason": "severe_feature_extrapolation"}
    mean_probability = (
        sum(probabilities.values()) / len(probabilities) if probabilities else None
    )
    first = available[0]
    metadata = dict(first.get("metadata") or {})
    return {
        "available": True,
        "feature_set_id": contract_id,
        "cutoff_date": metadata.get("cutoff_date"),
        "horizon_days": horizon_days,
        "spatial_weather_contract": "common_multisource_idw_by_microarea",
        "estimator_probabilities": probabilities,
        "interpretation_estimator_probabilities": probabilities,
        "ensemble_probability": (
            round(mean_probability, 6) if mean_probability is not None else None
        ),
        "label": _label(mean_probability),
        "features_used": dict(first.get("features_used") or {}),
        "estimator_exclusions": exclusions,
        "evaluation": {
            "available": bool(estimators and baseline_scores),
            "baseline": {
                "brier_score": min(baseline_scores) if baseline_scores else None
            },
            "estimators": estimators,
        },
        "member_count": len(available),
    }


def compare_operational_reference(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    species_id: str,
    area_id: str,
    target_date: date,
    issue_date: date,
    season_phase: str,
    phenology: Mapping[str, object] | None,
    models_root: Path,
    known_sites_path: Path,
    weather_data_dir: Path,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]] = frozenset(),
    prepared_weather_cache: MutableMapping[
        tuple[object, ...], tuple[Any, dict[int, dict[str, object]], dict[tuple[str, str], Any]]
    ]
    | None = None,
    comparison_cache: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the operational card from every profile in the active version."""
    target = registry.get("active_operational_target")
    target = target if isinstance(target, Mapping) else {}
    version_id = str(target.get("version_id") or registry.get("active_version_id") or "")
    profiles = [
        row
        for row in catalog.catalog_entries(registry)
        if row["version_id"] == version_id and row["operational_eligible"] is True
    ]
    if not profiles:
        raise ValueError("The active version has no operational profiles")
    payload: dict[str, Any] = {
        "issue_date": issue_date.isoformat(),
        "target_date": target_date.isoformat(),
        "season_phase": season_phase,
    }
    result_specs: list[tuple[str, dict[str, Any], str, int]] = []
    lag_horizon = (target_date - (issue_date - timedelta(days=1))).days
    single_profile = len(profiles) == 1
    for profile in profiles:
        for contract_id in profile["temporal_contract_ids"]:
            horizon = 7 if str(contract_id).startswith("fixed_") else lag_horizon
            result_key = str(contract_id) if single_profile else f"{profile['profile_id']}:{contract_id}"
            result_specs.append((result_key, profile, str(contract_id), horizon))
    payload["active_version_id"] = version_id
    payload["operational_result_keys"] = [row[0] for row in result_specs]
    payload["operational_profiles"] = [
        {
            "profile_id": row["profile_id"],
            "profile_name": row["profile_display_name"],
            "result_keys": [key for key, profile, _contract, _horizon in result_specs if profile["profile_id"] == row["profile_id"]],
        }
        for row in profiles
    ]
    if season_phase == "out_of_season":
        for result_key, _profile, _contract_id, _horizon in result_specs:
            payload[result_key] = {"available": False, "reason": "out_of_season"}
        payload["interpretation"] = build_interpretation(
            payload,
            season_phase=season_phase,
            phenology=dict(phenology or {}),
            feature_set_ids=payload["operational_result_keys"],
        )
        return payload

    checked = (
        comparison_cache.get("checked_manifest")
        if comparison_cache is not None
        else None
    )
    if not isinstance(checked, Mapping):
        checked = catalog.validate_batch_manifest(registry, manifest)
        if comparison_cache is not None:
            comparison_cache["checked_manifest"] = checked
    selections: list[dict[str, object]] = []
    for _result_key, profile, contract_id, horizon in result_specs:
        for row in checked["artifacts"]:
            artifact_ref = row["artifact_ref"]
            if (
                artifact_ref["version_id"] == version_id
                and artifact_ref["temporal_contract_id"] == contract_id
                and artifact_ref["profile_id"] == profile["profile_id"]
                and artifact_ref["species_id"] == species_id
                and horizon in row["supported_horizons"]
            ):
                selections.append(
                    {
                        "version_id": version_id,
                        "temporal_contract_id": contract_id,
                        "profile_id": profile["profile_id"],
                        "estimator_id": artifact_ref["estimator_id"],
                        "horizon_days": horizon,
                    }
                )
    runtime = (
        compare_selection(
            registry,
            checked,
            selections,
            species_id=species_id,
            area_id=area_id,
            target_date=target_date,
            models_root=models_root,
            known_sites_path=known_sites_path,
            weather_data_dir=weather_data_dir,
            excluded_station_keys=excluded_station_keys,
            prepared_weather_cache=prepared_weather_cache,
            checked_manifest=checked,
            comparison_cache=comparison_cache,
        )
        if selections
        else {"members": []}
    )
    members = list(runtime.get("members") or [])
    for result_key, profile, contract_id, horizon in result_specs:
        payload[result_key] = _contract_result(
            contract_id,
            members,
            horizon_days=horizon,
            profile_id=str(profile["profile_id"]),
        )
        payload[result_key]["profile_id"] = profile["profile_id"]
        payload[result_key]["profile_name"] = profile["profile_display_name"]
        payload[result_key]["temporal_contract_id"] = contract_id
    payload["runtime_batch_id"] = checked["batch_id"]
    payload["spatial_weather_contract"] = "common_multisource_idw_by_microarea"
    payload["interpretation"] = build_interpretation(
        payload,
        season_phase=season_phase,
        phenology=dict(phenology or {}),
        feature_set_ids=payload["operational_result_keys"],
    )
    return payload


def compare_v2_reference(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Backward-compatible name for the now registry-driven operational card."""
    return compare_operational_reference(*args, **kwargs)


def resolve_selection(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    selection: Mapping[str, object],
    *,
    species_id: str,
    checked_manifest: Mapping[str, object] | None = None,
    catalog_profiles: Sequence[Mapping[str, object]] | None = None,
) -> catalog.ModelRef:
    """Resolve UI selection to the exact installed generation and batch."""
    checked = (
        checked_manifest
        if checked_manifest is not None
        else catalog.validate_batch_manifest(registry, manifest)
    )
    version_id = str(selection.get("version_id") or "")
    temporal_contract_id = str(selection.get("temporal_contract_id") or "")
    profile_id = str(selection.get("profile_id") or "")
    estimator_id = str(selection.get("estimator_id") or "")
    try:
        horizon_days = int(selection.get("horizon_days") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Comparison horizon is invalid") from exc
    profile = next(
        (
            row
            for row in (
                catalog_profiles
                if catalog_profiles is not None
                else catalog.catalog_entries(registry)
            )
            if row["version_id"] == version_id and row["profile_id"] == profile_id
        ),
        None,
    )
    if profile is None or estimator_id not in profile["estimator_ids"]:
        raise ValueError("Comparison selection is not in the runtime catalog")
    artifact_species = (
        "all_species"
        if profile["estimator_scopes"][estimator_id] == "shared"
        else species_id
    )
    artifact = next(
        (
            row
            for row in checked["artifacts"]
            if row["artifact_ref"]["version_id"] == version_id
            and row["artifact_ref"]["temporal_contract_id"] == temporal_contract_id
            and row["artifact_ref"]["profile_id"] == profile_id
            and row["artifact_ref"]["estimator_id"] == estimator_id
            and row["artifact_ref"]["species_id"] == artifact_species
            and horizon_days in row["supported_horizons"]
        ),
        None,
    )
    if artifact is None:
        raise FileNotFoundError("Selected comparison model has no installed artifact")
    artifact_ref = catalog.ModelArtifactRef.from_mapping(artifact["artifact_ref"])
    resolved_ref = artifact_ref.as_dict()
    resolved_ref["species_id"] = species_id
    return catalog.ModelRef(**resolved_ref, horizon_days=horizon_days)


def _weather_requirements(
    model_refs: Sequence[catalog.ModelRef],
    *,
    catalog_profiles: Sequence[Mapping[str, object]] | None = None,
) -> tuple[int, bool]:
    """Return only the weather work required by the selected trained profiles."""
    if catalog_profiles is not None:
        by_key = {
            (str(row.get("version_id") or ""), str(row.get("profile_id") or "")): row
            for row in catalog_profiles
        }
        requirements = []
        for ref in model_refs:
            profile = by_key.get((ref.version_id, ref.profile_id))
            raw = profile.get("input_requirements") if isinstance(profile, Mapping) else None
            if not isinstance(raw, Mapping):
                raise ValueError(
                    f"Runtime profile lacks input requirements: {ref.version_id}/{ref.profile_id}"
                )
            requirements.append(raw)
        return (
            max(int(row["weather_lookback_days"]) for row in requirements),
            any(bool(row["include_physical_state"]) for row in requirements),
        )
    long_raw_versions = {
        "biology_v5_raw_weather_discovery",
        "biology_v6_smooth_hierarchical",
    }
    physical_profile_tokens = (
        "physical_state",
        "climatic_balance",
        "soil_water",
        "smi",
    )
    lookback_days = (
        mushroom_ml_raw_weather.LOOKBACK_DAYS
        if any(ref.version_id in long_raw_versions for ref in model_refs)
        else biology_v3.EVENT_LOOKBACK_DAYS
    )
    include_physical_state = any(
        any(token in ref.profile_id.lower() for token in physical_profile_tokens)
        for ref in model_refs
    )
    return lookback_days, include_physical_state


def prepare_area_weather(
    *,
    known_sites_path: Path,
    weather_data_dir: Path,
    area_id: str,
    target_date: date,
    horizons: Sequence[int],
    lookback_days: int = mushroom_ml_raw_weather.LOOKBACK_DAYS,
    include_physical_state: bool = True,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]] = frozenset(),
) -> tuple[
    Any,
    dict[int, dict[str, object]],
    dict[tuple[str, str], Any],
]:
    """Load one bounded station window and reuse it for every V2--V6 member."""
    areas, microareas = mushroom_ml_area_weather_runtime.area_contexts(
        Path(known_sites_path)
    )
    area_context = areas.get(area_id)
    contexts = microareas.get(area_id, [])
    if area_context is None or not contexts:
        raise ValueError(f"Unknown mushroom area: {area_id}")
    resolved_horizons = sorted({int(value) for value in horizons})
    if not resolved_horizons:
        raise ValueError("At least one comparison horizon is required")
    cutoffs = {horizon: target_date - timedelta(days=horizon) for horizon in resolved_horizons}
    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")
    earliest = min(cutoffs.values()) - timedelta(days=lookback_days - 1)
    latest = max(cutoffs.values())
    station_catalog = weather_context.load_stations_catalog(Path(weather_data_dir))
    station_filter: set[tuple[str, str]] = set()
    for row in station_catalog.itertuples(index=False):
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
        Path(weather_data_dir),
        station_filter=station_filter,
        start_date=earliest,
        end_date=latest,
    )
    normalized_excluded = {
        (str(source).lower(), str(code).upper())
        for source, code in excluded_station_keys
    }
    stations = {
        key: station
        for key, station in stations.items()
        if (str(key[0]).lower(), str(key[1]).upper()) not in normalized_excluded
    }
    prepared = {
        horizon: mushroom_ml_area_weather_runtime.materialize_area_series(
            area_id=area_id,
            end_day=cutoff,
            days=lookback_days,
            microareas_by_area=microareas,
            stations=stations,
            excluded_station_keys=normalized_excluded,
            include_physical_state=include_physical_state,
        )
        for horizon, cutoff in cutoffs.items()
    }
    return area_context, prepared, stations


def _prepared_weather_key(
    *,
    known_sites_path: Path,
    weather_data_dir: Path,
    area_id: str,
    target_date: date,
    horizons: Sequence[int],
    lookback_days: int,
    include_physical_state: bool,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]],
) -> tuple[object, ...]:
    normalized_excluded = tuple(
        sorted(
            (str(source).lower(), str(code).upper())
            for source, code in excluded_station_keys
        )
    )
    return (
        str(Path(known_sites_path).resolve()),
        str(Path(weather_data_dir).resolve()),
        area_id,
        target_date.isoformat(),
        tuple(sorted({int(value) for value in horizons})),
        lookback_days,
        include_physical_state,
        normalized_excluded,
    )


def prewarm_v2_week_weather(
    *,
    area_ids: Sequence[str],
    target_issue_dates: Sequence[tuple[date, date]],
    known_sites_path: Path,
    weather_data_dir: Path,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]],
    prepared_weather_cache: MutableMapping[
        tuple[object, ...], tuple[Any, dict[int, dict[str, object]], dict[tuple[str, str], Any]]
    ],
) -> None:
    """Prepare one extended IDW series per area for the complete V2 week grid."""
    lookback_days = biology_v3.EVENT_LOOKBACK_DAYS
    requests: list[tuple[date, tuple[int, ...], dict[int, date]]] = []
    for target_date, issue_date in target_issue_dates:
        lag_horizon = (target_date - (issue_date - timedelta(days=1))).days
        horizons = tuple(sorted({7, lag_horizon}))
        cutoffs = {
            horizon: target_date - timedelta(days=horizon)
            for horizon in horizons
        }
        requests.append((target_date, horizons, cutoffs))
    if not requests:
        return
    all_cutoffs = [cutoff for _target, _horizons, rows in requests for cutoff in rows.values()]
    minimum_cutoff = min(all_cutoffs)
    maximum_cutoff = max(all_cutoffs)
    base_days = lookback_days + (maximum_cutoff - minimum_cutoff).days
    base_start = maximum_cutoff - timedelta(days=base_days - 1)

    for area_id in area_ids:
        area_context, base_by_horizon, stations = prepare_area_weather(
            known_sites_path=known_sites_path,
            weather_data_dir=weather_data_dir,
            area_id=area_id,
            target_date=maximum_cutoff,
            horizons=(0,),
            lookback_days=base_days,
            include_physical_state=False,
            excluded_station_keys=excluded_station_keys,
        )
        base = base_by_horizon[0]
        for target_date, horizons, cutoffs in requests:
            prepared: dict[int, dict[str, object]] = {}
            for horizon, cutoff in cutoffs.items():
                end_index = (cutoff - base_start).days + 1
                start_index = end_index - lookback_days
                if start_index < 0 or end_index > base_days:
                    raise ValueError("Prepared V2 week slice is outside its base series")
                prepared[horizon] = {
                    key: (
                        list(value[start_index:end_index])
                        if isinstance(value, list) and len(value) == base_days
                        else value
                    )
                    for key, value in base.items()
                }
            cache_key = _prepared_weather_key(
                known_sites_path=known_sites_path,
                weather_data_dir=weather_data_dir,
                area_id=area_id,
                target_date=target_date,
                horizons=horizons,
                lookback_days=lookback_days,
                include_physical_state=False,
                excluded_station_keys=excluded_station_keys,
            )
            prepared_weather_cache[cache_key] = (area_context, prepared, stations)


def compare_selection(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    selections: Sequence[Mapping[str, object]],
    *,
    species_id: str,
    area_id: str,
    target_date: date,
    models_root: Path,
    known_sites_path: Path,
    weather_data_dir: Path,
    excluded_station_keys: frozenset[tuple[str, str]] | set[tuple[str, str]] = frozenset(),
    prepared_weather_cache: MutableMapping[
        tuple[object, ...], tuple[Any, dict[int, dict[str, object]], dict[tuple[str, str], Any]]
    ]
    | None = None,
    checked_manifest: Mapping[str, object] | None = None,
    comparison_cache: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = checked_manifest
    if checked is None and comparison_cache is not None:
        cached_checked = comparison_cache.get("checked_manifest")
        if isinstance(cached_checked, Mapping):
            checked = cached_checked
    if checked is None:
        checked = catalog.validate_batch_manifest(registry, manifest)
        if comparison_cache is not None:
            comparison_cache["checked_manifest"] = checked
    catalog_profiles = (
        comparison_cache.get("catalog_profiles")
        if comparison_cache is not None
        else None
    )
    if not isinstance(catalog_profiles, list):
        catalog_profiles = catalog.catalog_entries(registry)
        if comparison_cache is not None:
            comparison_cache["catalog_profiles"] = catalog_profiles
    refs = [
        resolve_selection(
            registry,
            checked,
            selection,
            species_id=species_id,
            checked_manifest=checked,
            catalog_profiles=catalog_profiles,
        )
        for selection in selections
    ]
    horizons = tuple(sorted({model_ref.horizon_days for model_ref in refs}))
    lookback_days, include_physical_state = _weather_requirements(
        refs, catalog_profiles=catalog_profiles
    )
    weather_key = _prepared_weather_key(
        known_sites_path=known_sites_path,
        weather_data_dir=weather_data_dir,
        area_id=area_id,
        target_date=target_date,
        horizons=horizons,
        lookback_days=lookback_days,
        include_physical_state=include_physical_state,
        excluded_station_keys=excluded_station_keys,
    )
    prepared_tuple = (
        prepared_weather_cache.get(weather_key)
        if prepared_weather_cache is not None
        else None
    )
    if prepared_tuple is None:
        prepared_tuple = prepare_area_weather(
            known_sites_path=known_sites_path,
            weather_data_dir=weather_data_dir,
            area_id=area_id,
            target_date=target_date,
            horizons=horizons,
            lookback_days=lookback_days,
            include_physical_state=include_physical_state,
            excluded_station_keys=excluded_station_keys,
        )
        if prepared_weather_cache is not None:
            prepared_weather_cache[weather_key] = prepared_tuple
    area_context, prepared, stations = prepared_tuple
    return compare_prepared(
        registry,
        checked,
        refs,
        models_root=models_root,
        target_date=target_date,
        area_id=area_id,
        area_context=area_context,
        area_series_by_horizon=prepared,
        stations=stations,
        checked_manifest=checked,
        comparison_cache=comparison_cache,
    )
