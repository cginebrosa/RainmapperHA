"""Shared path resolution for mushroom data and v0 artifacts.

Versioned defaults live in the repository or app image. The live editable copy
uses the Rainmapper share root, which is `/share/rainmapper` inside Home
Assistant and `docker-data/` in local development.
"""

from __future__ import annotations

import os
from pathlib import Path


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
