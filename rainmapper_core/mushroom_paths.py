"""Shared path resolution for mushroom data and v0 artifacts.

Versioned defaults live in the repository or app image. The live editable copy
uses the Rainmapper share root, which is `/share/rainmapper` inside Home
Assistant and `docker-data/` in local development.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PredictorRuntimeArchiveLocation:
    path: Path
    preferred_path: Path
    fallback_used: bool
    diagnostic: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def app_mushroom_defaults_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", "").strip()
    if configured:
        return Path(configured)
    app_defaults = Path("/app/mushroom-data")
    if app_defaults.exists():
        return app_defaults
    return repo_root() / "mushroom-data"


def share_root() -> Path:
    configured = os.environ.get("RAINMAPPER_SHARE_ROOT", "").strip()
    if configured:
        return Path(configured)
    ha_share_root = Path("/share/rainmapper")
    if ha_share_root.exists():
        return ha_share_root
    local_share_copy = repo_root() / "docker-data"
    if local_share_copy.exists():
        return local_share_copy
    return repo_root() / "tmp" / "rainmapper-share"


def mushroom_data_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR", "").strip()
    if configured:
        return Path(configured)
    return share_root() / "mushroom-data"


def mushroom_data_file(file_name: str) -> Path:
    return mushroom_data_dir() / file_name


def mushroom_data_report_file(file_name: str) -> Path:
    return mushroom_data_dir() / "reports" / file_name


def mushroom_media_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_MEDIA_DIR", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_dir() / "media"


def mushroom_observation_photos_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATION_PHOTOS_DIR", "").strip()
    if configured:
        return Path(configured)
    return mushroom_media_dir() / "observation-photos"


def mushroom_observation_videos_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATION_VIDEOS_DIR", "").strip()
    if configured:
        return Path(configured)
    return mushroom_media_dir() / "observation-videos"


def mushroom_observation_images_dir() -> Path:
    """Backward-compatible alias for observation photo storage."""
    return mushroom_observation_photos_dir()


def mushroom_observations_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATIONS_PATH", "").strip()
    if configured:
        return Path(configured)
    persistent_path = mushroom_data_file("mushroom_observations.json")
    if persistent_path.exists():
        return persistent_path
    return app_mushroom_defaults_dir() / "mushroom_observations.json"


def mushroom_reference_catalogs_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_REFERENCE_CATALOGS_PATH", "").strip()
    if configured:
        return Path(configured)
    persistent_path = mushroom_data_file("mushroom_reference_catalogs.json")
    if persistent_path.exists():
        return persistent_path
    return app_mushroom_defaults_dir() / "mushroom_reference_catalogs.json"


def mushroom_model_state_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_MODEL_STATE_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_model_v0_state.json")


def weather_data_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_WEATHER_DATA_DIR", "").strip()
    if configured:
        return Path(configured)
    return share_root() / "Data"


def mushroom_gis_reconstruction_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_GIS_RECONSTRUCTION_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_gis_observation_reconstruction.json")


def mushroom_weather_features_json_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_WEATHER_FEATURES_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_observations_weather_features.json")


def mushroom_weather_features_csv_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_WEATHER_FEATURES_CSV_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_observations_weather_features.csv")


def mushroom_weather_report_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_WEATHER_REPORT_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_report_file("mushroom_observations_weather_features.md")


def mushroom_observation_features_json_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATION_FEATURES_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_observation_features_v0.json")


def mushroom_observation_features_csv_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATION_FEATURES_CSV_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_observation_features_v0.csv")


def mushroom_observation_features_report_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_OBSERVATION_FEATURES_REPORT_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_report_file("mushroom_observation_features_v0.md")


def mushroom_learned_model_json_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_LEARNED_MODEL_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_model_v0.json")


def mushroom_learned_model_report_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_LEARNED_MODEL_REPORT_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_report_file("mushroom_model_v0.md")


def mushroom_known_sites_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_KNOWN_SITES_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_known_sites.json")


def mushroom_profiles_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_PROFILES_PATH", "").strip()
    if configured:
        return Path(configured)
    persistent_path = mushroom_data_file("mushroom_profiles.json")
    if persistent_path.exists():
        return persistent_path
    return app_mushroom_defaults_dir() / "mushroom_profiles.json"


def mushroom_ml_models_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_ML_MODELS_DIR", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_dir() / "ml_models"


def predictor_runtime_archive_preferred_dir() -> Path:
    """Return the configured/media TAR cache, never a path below /share."""
    configured = os.environ.get(
        "RAINMAPPER_PREDICTOR_RUNTIME_ARCHIVE_DIR", ""
    ).strip()
    if configured:
        return Path(configured)
    media_root = os.environ.get("RAINMAPPER_MEDIA_ROOT", "").strip()
    root = Path(media_root) if media_root else Path("/media/rainmapper")
    return root / "runtime-cache" / "predictor-runtime-archives"


def predictor_runtime_archive_fallback_dir() -> Path:
    configured = os.environ.get(
        "RAINMAPPER_PREDICTOR_RUNTIME_ARCHIVE_FALLBACK_DIR", ""
    ).strip()
    if configured:
        return Path(configured)
    return (
        Path(tempfile.gettempdir())
        / "rainmapper-runtime-cache"
        / "predictor-runtime-archives"
    )


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        Path(path).resolve(strict=False).relative_to(Path(parent).resolve(strict=False))
    except ValueError:
        return False
    return True


def _prepare_private_cache_dir(path: Path) -> Path:
    candidate = Path(path)
    if _path_is_within(candidate, share_root()):
        raise OSError(f"Predictor runtime TAR cache cannot reside under share: {candidate}")
    if candidate.is_symlink():
        raise OSError(f"Predictor runtime TAR cache cannot be a symlink: {candidate}")
    candidate.mkdir(mode=0o700, parents=True, exist_ok=True)
    if candidate.is_symlink() or not candidate.is_dir():
        raise OSError(f"Predictor runtime TAR cache is not a private directory: {candidate}")
    candidate.chmod(0o700)
    return candidate


def prepare_predictor_runtime_archive_dir() -> PredictorRuntimeArchiveLocation:
    """Prepare the media cache, falling back visibly to a non-share temp path."""
    preferred = predictor_runtime_archive_preferred_dir()
    configured = bool(
        os.environ.get("RAINMAPPER_PREDICTOR_RUNTIME_ARCHIVE_DIR", "").strip()
        or os.environ.get("RAINMAPPER_MEDIA_ROOT", "").strip()
    )
    media_root_available = preferred.parents[1].exists()
    preferred_error: OSError | None = None
    if configured or media_root_available:
        try:
            path = _prepare_private_cache_dir(preferred)
            return PredictorRuntimeArchiveLocation(path, preferred, False)
        except OSError as exc:
            preferred_error = exc
    else:
        preferred_error = OSError(
            f"Predictor runtime media root is unavailable: {preferred.parents[1]}"
        )

    fallback = predictor_runtime_archive_fallback_dir()
    try:
        path = _prepare_private_cache_dir(fallback)
    except OSError as exc:
        raise OSError(
            f"Cannot prepare predictor runtime TAR cache at {preferred} or {fallback}: "
            f"{preferred_error}; {exc}"
        ) from exc
    return PredictorRuntimeArchiveLocation(
        path,
        preferred,
        True,
        str(preferred_error),
    )


def mushroom_ml_report_json_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_ML_REPORT_PATH", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_file("mushroom_ml_v0_report.json")


def mushroom_ml_version_registry_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_ML_VERSION_REGISTRY_PATH", "").strip()
    if configured:
        return Path(configured)
    persistent_path = mushroom_data_file("mushroom_ml_version_registry.json")
    if persistent_path.exists():
        return persistent_path
    return app_mushroom_defaults_dir() / "mushroom_ml_version_registry.json"


def mushroom_ml_version_archive_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_ML_VERSION_ARCHIVE_DIR", "").strip()
    if configured:
        return Path(configured)
    return mushroom_data_dir() / "ml_version_archive"
