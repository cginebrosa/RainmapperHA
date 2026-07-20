"""Semantic comparison of mushroom rebuild artifact directories."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


JSON_ARTIFACTS = (
    "mushroom_gis_observation_reconstruction.json",
    "mushroom_observations_weather_features.json",
    "mushroom_observation_features_v0.json",
    "mushroom_model_v0.json",
)
CSV_ARTIFACTS = (
    "mushroom_observations_weather_features.csv",
    "mushroom_observation_features_v0.csv",
)
REPORT_ARTIFACTS = (
    "reports/mushroom_observations_weather_features.md",
    "reports/mushroom_observation_features_v0.md",
    "reports/mushroom_model_v0.md",
)


def _normalize_common_paths(payload: dict[str, Any]) -> None:
    payload.pop("generated_at", None)
    payload.pop("input_paths", None)
    payload.pop("output_paths", None)
    policy = payload.get("prediction_target_policy")
    if isinstance(policy, dict):
        policy.pop("catalog_path", None)
    source_files = payload.get("source_files")
    if isinstance(source_files, list):
        for item in source_files:
            if isinstance(item, dict):
                item.pop("path", None)


def normalize_json_artifact(name: str, raw_payload: Any) -> Any:
    payload = copy.deepcopy(raw_payload)
    if not isinstance(payload, dict):
        return payload
    _normalize_common_paths(payload)
    if name != "mushroom_gis_observation_reconstruction.json":
        return payload
    payload.pop("qgis_points_path", None)
    payload.pop("qgis_points_host_path", None)
    results = payload.get("results")
    if not isinstance(results, list):
        return payload
    for result in results:
        if not isinstance(result, dict):
            continue
        layers = result.get("layers")
        if not isinstance(layers, dict):
            continue
        for layer in layers.values():
            if isinstance(layer, dict):
                layer.pop("source", None)
        dem = layers.get("dem_5m")
        if (
            isinstance(dem, dict)
            and dem.get("status") in {"no_data", "no_value"}
            and dem.get("raw") in {None, ""}
            and dem.get("elevation_m") in {None, -9999, -9999.0}
        ):
            dem["status"] = "no_data"
            dem.pop("raw", None)
            dem.pop("elevation_m", None)
    return payload


def _difference_paths(reference: Any, candidate: Any, path: tuple[object, ...] = ()) -> list[str]:
    if type(reference) is not type(candidate):
        return ["/" + "/".join(map(str, path))]
    if isinstance(reference, dict):
        differences: list[str] = []
        for key in sorted(set(reference) | set(candidate), key=str):
            if key not in reference or key not in candidate:
                differences.append("/" + "/".join(map(str, (*path, key))))
            else:
                differences.extend(_difference_paths(reference[key], candidate[key], (*path, key)))
            if len(differences) >= 20:
                break
        return differences[:20]
    if isinstance(reference, list):
        if len(reference) != len(candidate):
            return ["/" + "/".join(map(str, (*path, "length")))]
        differences = []
        for index, (left, right) in enumerate(zip(reference, candidate, strict=True)):
            differences.extend(_difference_paths(left, right, (*path, index)))
            if len(differences) >= 20:
                break
        return differences[:20]
    return [] if reference == candidate else ["/" + "/".join(map(str, path))]


def _normalized_report(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.startswith("- Generated at:"))


def compare_artifact_dirs(reference_dir: Path, candidate_dir: Path) -> dict[str, object]:
    reference_root = reference_dir.resolve()
    candidate_root = candidate_dir.resolve()
    artifacts: list[dict[str, object]] = []
    for name in JSON_ARTIFACTS:
        reference_path = reference_root / name
        candidate_path = candidate_root / name
        if not reference_path.is_file() or not candidate_path.is_file():
            artifacts.append(
                {
                    "path": name,
                    "kind": "json",
                    "equivalent": False,
                    "error": "missing artifact",
                }
            )
            continue
        reference = normalize_json_artifact(
            name,
            json.loads(reference_path.read_text(encoding="utf-8")),
        )
        candidate = normalize_json_artifact(
            name,
            json.loads(candidate_path.read_text(encoding="utf-8")),
        )
        differences = _difference_paths(reference, candidate)
        artifacts.append(
            {
                "path": name,
                "kind": "json",
                "equivalent": not differences,
                "difference_paths": differences,
            }
        )
    for name in CSV_ARTIFACTS:
        reference_path = reference_root / name
        candidate_path = candidate_root / name
        equivalent = (
            reference_path.is_file()
            and candidate_path.is_file()
            and reference_path.read_bytes() == candidate_path.read_bytes()
        )
        artifacts.append({"path": name, "kind": "csv", "equivalent": equivalent})
    for name in REPORT_ARTIFACTS:
        reference_path = reference_root / name
        candidate_path = candidate_root / name
        equivalent = (
            reference_path.is_file()
            and candidate_path.is_file()
            and _normalized_report(reference_path) == _normalized_report(candidate_path)
        )
        artifacts.append({"path": name, "kind": "report", "equivalent": equivalent})
    return {
        "schema_version": "0.1",
        "kind": "mushroom_rebuild_comparison",
        "status": "equivalent" if all(item["equivalent"] for item in artifacts) else "different",
        "reference_dir": str(reference_root),
        "candidate_dir": str(candidate_root),
        "artifacts": artifacts,
    }
