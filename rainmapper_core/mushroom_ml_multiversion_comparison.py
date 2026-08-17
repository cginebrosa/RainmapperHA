"""Execute exact installed V2--V6 members against one prepared weather context."""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_runtime_features
from rainmapper_core import mushroom_ml_runtime_inference
from rainmapper_core import mushroom_ml_quality_catalog
from rainmapper_core import mushroom_ml_area_weather_runtime
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


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
) -> dict[str, Any]:
    """Compare individual members; quality precedes output and no mean is made."""
    checked_manifest = catalog.validate_batch_manifest(registry, manifest)
    quality_catalog: dict[str, Any] = {}
    quality_ref = checked_manifest.get("quality_catalog")
    if isinstance(quality_ref, Mapping):
        quality_path = Path(models_root) / str(quality_ref.get("path") or "")
        if quality_path.is_file() and hashlib.sha256(quality_path.read_bytes()).hexdigest() == str(
            quality_ref.get("sha256") or ""
        ):
            loaded = json.loads(quality_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                quality_catalog = loaded
    results: list[dict[str, Any]] = []
    for raw_ref in model_refs:
        model_ref = catalog.validate_model_ref(registry, raw_ref)
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
            bundle = mushroom_ml_runtime_inference.load_exact_artifact(
                registry,
                checked_manifest,
                model_ref,
                root=models_root,
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
        "batch_id": checked_manifest["batch_id"],
        "snapshot_id": checked_manifest["snapshot_id"],
        "area_id": area_id,
        "target_date": target_date.isoformat(),
        "members": results,
        "quality_before_consensus": True,
        "consensus_computed": False,
        "ensemble_computed": False,
        "version_cautions": dict(quality_catalog.get("version_cautions") or {}),
        "species_metrics_are_never_averaged": True,
    }


def resolve_selection(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    selection: Mapping[str, object],
    *,
    species_id: str,
) -> catalog.ModelRef:
    """Resolve UI selection to the exact installed generation and batch."""
    checked = catalog.validate_batch_manifest(registry, manifest)
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
            for row in catalog.catalog_entries(registry)
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
    return catalog.validate_model_ref(
        registry,
        {
            **artifact_ref.as_dict(),
            "species_id": species_id,
            "horizon_days": horizon_days,
        },
    )


def prepare_area_weather(
    *,
    known_sites_path: Path,
    weather_data_dir: Path,
    area_id: str,
    target_date: date,
    horizons: Sequence[int],
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
    earliest = min(cutoffs.values()) - timedelta(days=364)
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
            days=365,
            microareas_by_area=microareas,
            stations=stations,
            excluded_station_keys=normalized_excluded,
        )
        for horizon, cutoff in cutoffs.items()
    }
    return area_context, prepared, stations


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
) -> dict[str, Any]:
    refs = [
        resolve_selection(registry, manifest, selection, species_id=species_id)
        for selection in selections
    ]
    area_context, prepared, stations = prepare_area_weather(
        known_sites_path=known_sites_path,
        weather_data_dir=weather_data_dir,
        area_id=area_id,
        target_date=target_date,
        horizons=[model_ref.horizon_days for model_ref in refs],
        excluded_station_keys=excluded_station_keys,
    )
    return compare_prepared(
        registry,
        manifest,
        refs,
        models_root=models_root,
        target_date=target_date,
        area_id=area_id,
        area_context=area_context,
        area_series_by_horizon=prepared,
        stations=stations,
    )
