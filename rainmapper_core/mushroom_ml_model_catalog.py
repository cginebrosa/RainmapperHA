"""Runtime catalog and exact identities for mushroom ML models.

The scientific version registry is the source of truth.  This module turns its
declarative runtime profiles into exact model references.  Resolution is
deliberately strict: an unavailable V3--V6 model must never fall back to V2.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "1.0"
BATCH_MANIFEST_KIND = "mushroom_ml_runtime_batch"
FIXED_HORIZONS = frozenset({7})
LAG_HORIZONS = frozenset({1, 2, 3, 7})
_SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,159}$")


def _identifier(value: object, field: str) -> str:
    resolved = str(value or "").strip()
    if not _SAFE_ID.fullmatch(resolved):
        raise ValueError(f"Invalid {field}: {resolved!r}")
    return resolved


@dataclass(frozen=True)
class ModelRef:
    """Identity of one estimator prediction within one immutable batch."""

    batch_id: str
    generation_id: str
    version_id: str
    temporal_contract_id: str
    profile_id: str
    estimator_id: str
    species_id: str
    horizon_days: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "ModelRef":
        try:
            horizon = int(value.get("horizon_days", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid horizon_days") from exc
        return cls(
            batch_id=_identifier(value.get("batch_id"), "batch_id"),
            generation_id=_identifier(value.get("generation_id"), "generation_id"),
            version_id=_identifier(value.get("version_id"), "version_id"),
            temporal_contract_id=_identifier(
                value.get("temporal_contract_id"), "temporal_contract_id"
            ),
            profile_id=_identifier(value.get("profile_id"), "profile_id"),
            estimator_id=_identifier(value.get("estimator_id"), "estimator_id"),
            species_id=_identifier(value.get("species_id"), "species_id"),
            horizon_days=horizon,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def key(self) -> str:
        return "/".join(
            (
                self.batch_id,
                self.generation_id,
                self.version_id,
                self.temporal_contract_id,
                self.profile_id,
                self.estimator_id,
                self.species_id,
                f"h{self.horizon_days}",
            )
        )

    @property
    def artifact_ref(self) -> "ModelArtifactRef":
        return ModelArtifactRef(
            batch_id=self.batch_id,
            generation_id=self.generation_id,
            version_id=self.version_id,
            temporal_contract_id=self.temporal_contract_id,
            profile_id=self.profile_id,
            estimator_id=self.estimator_id,
            species_id=self.species_id,
        )


@dataclass(frozen=True)
class ModelArtifactRef:
    """Identity of one fitted artifact; horizons never appear in this key."""

    batch_id: str
    generation_id: str
    version_id: str
    temporal_contract_id: str
    profile_id: str
    estimator_id: str
    species_id: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "ModelArtifactRef":
        return cls(
            **{
                field: _identifier(value.get(field), field)
                for field in (
                    "batch_id",
                    "generation_id",
                    "version_id",
                    "temporal_contract_id",
                    "profile_id",
                    "estimator_id",
                    "species_id",
                )
            }
        )

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    @property
    def key(self) -> str:
        return "/".join(asdict(self).values())


def _versions(registry: Mapping[str, object]) -> list[dict[str, Any]]:
    rows = registry.get("versions")
    if not isinstance(rows, list):
        raise ValueError("ML registry versions must be a list")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def catalog_entries(registry: Mapping[str, object]) -> list[dict[str, Any]]:
    """Flatten every declared runtime profile in stable display order."""
    entries: list[dict[str, Any]] = []
    for version in _versions(registry):
        version_id = _identifier(version.get("version_id"), "version_id")
        contracts = {
            _identifier(value, "temporal_contract_id")
            for value in version.get("temporal_contract_ids", [])
        }
        runtime = version.get("runtime")
        if runtime is None:
            continue
        if not isinstance(runtime, Mapping):
            raise ValueError(f"{version_id}.runtime must be an object")
        adapter_id = _identifier(runtime.get("adapter_id"), "adapter_id")
        profiles = runtime.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            raise ValueError(f"{version_id}.runtime.profiles must not be empty")
        seen_profiles: set[str] = set()
        for raw_profile in profiles:
            if not isinstance(raw_profile, Mapping):
                raise ValueError(f"{version_id} runtime profile must be an object")
            profile_id = _identifier(raw_profile.get("profile_id"), "profile_id")
            if profile_id in seen_profiles:
                raise ValueError(f"Duplicate runtime profile: {version_id}/{profile_id}")
            seen_profiles.add(profile_id)
            profile_contracts = [
                _identifier(value, "temporal_contract_id")
                for value in raw_profile.get("temporal_contract_ids", [])
            ]
            if not profile_contracts or not set(profile_contracts) <= contracts:
                raise ValueError(
                    f"{version_id}/{profile_id} declares an unknown temporal contract"
                )
            estimators = [
                _identifier(value, "estimator_id")
                for value in raw_profile.get("estimator_ids", [])
            ]
            if not estimators or len(estimators) != len(set(estimators)):
                raise ValueError(
                    f"{version_id}/{profile_id} must declare unique estimators"
                )
            raw_scopes = raw_profile.get("estimator_scopes", {})
            if not isinstance(raw_scopes, Mapping):
                raise ValueError(f"{version_id}/{profile_id} estimator scopes are invalid")
            estimator_scopes = {
                estimator_id: str(raw_scopes.get(estimator_id) or "species")
                for estimator_id in estimators
            }
            if set(estimator_scopes.values()) - {"species", "shared"}:
                raise ValueError(f"{version_id}/{profile_id} has an invalid estimator scope")
            if set(raw_scopes) - set(estimators):
                raise ValueError(f"{version_id}/{profile_id} scopes an unknown estimator")
            entries.append(
                {
                    "version_id": version_id,
                    "version_display_name": str(
                        version.get("display_name") or version_id
                    ),
                    "version_status": str(version.get("status") or ""),
                    "catalog_visible": bool(version.get("catalog_visible", True)),
                    "benchmark_runnable": bool(version.get("benchmark_available")),
                    "operational_eligible": bool(
                        raw_profile.get("operational_eligible", False)
                    ),
                    "comparison_eligible_when_trained": bool(
                        raw_profile.get("comparison_eligible_when_trained", True)
                    ),
                    "adapter_id": adapter_id,
                    "profile_id": profile_id,
                    "profile_display_name": str(
                        raw_profile.get("display_name") or profile_id
                    ),
                    "temporal_contract_ids": profile_contracts,
                    "estimator_ids": estimators,
                    "estimator_scopes": estimator_scopes,
                }
            )
    return entries


def validate_model_ref(
    registry: Mapping[str, object], value: ModelRef | Mapping[str, object]
) -> ModelRef:
    model_ref = value if isinstance(value, ModelRef) else ModelRef.from_mapping(value)
    matches = [
        entry
        for entry in catalog_entries(registry)
        if entry["version_id"] == model_ref.version_id
        and entry["profile_id"] == model_ref.profile_id
    ]
    if not matches:
        raise ValueError(
            f"Unknown runtime profile: {model_ref.version_id}/{model_ref.profile_id}"
        )
    profile = matches[0]
    if model_ref.temporal_contract_id not in profile["temporal_contract_ids"]:
        raise ValueError("Model reference temporal contract does not match its profile")
    if model_ref.estimator_id not in profile["estimator_ids"]:
        raise ValueError("Model reference estimator does not match its profile")
    if model_ref.temporal_contract_id.startswith("fixed_gap_"):
        allowed_horizons = FIXED_HORIZONS
    elif model_ref.temporal_contract_id.startswith("lag_event_"):
        allowed_horizons = LAG_HORIZONS
    else:
        raise ValueError("Unsupported temporal contract family")
    if model_ref.horizon_days not in allowed_horizons:
        raise ValueError("Model reference horizon does not match its temporal contract")
    return model_ref


def artifact_ref_for_model_ref(
    registry: Mapping[str, object], value: ModelRef | Mapping[str, object]
) -> ModelArtifactRef:
    model_ref = validate_model_ref(registry, value)
    profile = next(
        row
        for row in catalog_entries(registry)
        if row["version_id"] == model_ref.version_id
        and row["profile_id"] == model_ref.profile_id
    )
    species_id = (
        "all_species"
        if profile["estimator_scopes"][model_ref.estimator_id] == "shared"
        else model_ref.species_id
    )
    return ModelArtifactRef(
        **{
            **model_ref.artifact_ref.as_dict(),
            "species_id": species_id,
        }
    )


def supported_horizons(temporal_contract_id: str) -> frozenset[int]:
    if temporal_contract_id.startswith("fixed_gap_"):
        return FIXED_HORIZONS
    if temporal_contract_id.startswith("lag_event_"):
        return LAG_HORIZONS
    raise ValueError("Unsupported temporal contract family")


def selection_token(selection: Mapping[str, object]) -> str:
    """Encode one generation-independent UI selection in a stable token."""
    values = [
        _identifier(selection.get(field), field)
        for field in (
            "version_id",
            "temporal_contract_id",
            "profile_id",
            "estimator_id",
        )
    ]
    try:
        horizon = int(selection.get("horizon_days", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid selection horizon") from exc
    if horizon not in LAG_HORIZONS:
        raise ValueError("Invalid selection horizon")
    return "|".join((*values, str(horizon)))


def parse_selection_token(value: object) -> dict[str, Any]:
    parts = str(value or "").split("|")
    if len(parts) != 5:
        raise ValueError("Invalid multiversion selection token")
    selection = {
        "version_id": parts[0],
        "temporal_contract_id": parts[1],
        "profile_id": parts[2],
        "estimator_id": parts[3],
        "horizon_days": parts[4],
    }
    token = selection_token(selection)
    return {
        **{key: str(selection[key]) for key in selection if key != "horizon_days"},
        "horizon_days": int(selection["horizon_days"]),
        "token": token,
    }


def validate_artifact_ref(
    registry: Mapping[str, object],
    value: ModelArtifactRef | Mapping[str, object],
) -> ModelArtifactRef:
    artifact_ref = (
        value if isinstance(value, ModelArtifactRef) else ModelArtifactRef.from_mapping(value)
    )
    validate_model_ref(
        registry,
        {
            **artifact_ref.as_dict(),
            "horizon_days": min(supported_horizons(artifact_ref.temporal_contract_id)),
        },
    )
    return artifact_ref


def model_relative_path(model_ref: ModelRef | ModelArtifactRef) -> Path:
    """Return a deterministic per-estimator artifact path."""
    return Path(
        "batches",
        model_ref.batch_id,
        "generations",
        model_ref.generation_id,
        model_ref.version_id,
        model_ref.temporal_contract_id,
        model_ref.profile_id,
        model_ref.estimator_id,
        f"{model_ref.species_id}.joblib",
    )


def validate_batch_manifest(
    registry: Mapping[str, object], payload: object
) -> dict[str, Any]:
    """Validate an immutable same-snapshot multiversion runtime batch."""
    if not isinstance(payload, Mapping):
        raise ValueError("Runtime batch manifest must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported runtime batch schema")
    if payload.get("kind") != BATCH_MANIFEST_KIND:
        raise ValueError("Unsupported runtime batch kind")
    batch_id = _identifier(payload.get("batch_id"), "batch_id")
    snapshot_id = str(payload.get("snapshot_id") or "").strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", snapshot_id):
        raise ValueError("Runtime batch snapshot_id must be a SHA-256 identity")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Runtime batch must contain artifacts")
    checked_artifacts: list[dict[str, Any]] = []
    seen_refs: set[str] = set()
    seen_paths: set[str] = set()
    for raw_artifact in artifacts:
        if not isinstance(raw_artifact, Mapping):
            raise ValueError("Runtime batch artifact must be an object")
        artifact_ref = validate_artifact_ref(
            registry, raw_artifact.get("artifact_ref") or {}
        )
        if artifact_ref.batch_id != batch_id:
            raise ValueError("Runtime artifact belongs to a different batch")
        horizons = raw_artifact.get("supported_horizons")
        expected_horizons = supported_horizons(artifact_ref.temporal_contract_id)
        if (
            not isinstance(horizons, list)
            or {int(value) for value in horizons} != expected_horizons
        ):
            raise ValueError("Runtime artifact horizons do not match its contract")
        relative = Path(str(raw_artifact.get("path") or ""))
        if (
            relative.is_absolute()
            or not relative.parts
            or ".." in relative.parts
            or relative != model_relative_path(artifact_ref)
        ):
            raise ValueError("Runtime artifact path does not match model_ref")
        digest = str(raw_artifact.get("sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Runtime artifact SHA-256 is invalid")
        if artifact_ref.key in seen_refs or relative.as_posix() in seen_paths:
            raise ValueError("Duplicate runtime artifact")
        seen_refs.add(artifact_ref.key)
        seen_paths.add(relative.as_posix())
        checked_artifacts.append(
            {
                "artifact_ref": artifact_ref.as_dict(),
                "supported_horizons": sorted(expected_horizons),
                "path": relative.as_posix(),
                "sha256": digest,
            }
        )
    quality_catalog = payload.get("quality_catalog")
    checked_quality_catalog = None
    if quality_catalog is not None:
        if not isinstance(quality_catalog, Mapping):
            raise ValueError("Runtime quality catalog reference must be an object")
        quality_path = Path(str(quality_catalog.get("path") or ""))
        expected_quality_path = Path("batches", batch_id, "quality-catalog.json")
        digest = str(quality_catalog.get("sha256") or "")
        if quality_path != expected_quality_path or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Runtime quality catalog reference is invalid")
        checked_quality_catalog = {"path": quality_path.as_posix(), "sha256": digest}
    result = {
        **dict(payload),
        "batch_id": batch_id,
        "snapshot_id": snapshot_id,
        "artifacts": checked_artifacts,
    }
    if checked_quality_catalog is not None:
        result["quality_catalog"] = checked_quality_catalog
    return result


def resolve_artifact(
    registry: Mapping[str, object],
    manifest: Mapping[str, object],
    model_ref: ModelRef | Mapping[str, object],
    *,
    root: Path,
) -> Path:
    """Resolve exactly one declared model or fail; never substitute another."""
    checked = validate_batch_manifest(registry, manifest)
    wanted = validate_model_ref(registry, model_ref)
    match = next(
        (
            row
            for row in checked["artifacts"]
            if ModelArtifactRef.from_mapping(row["artifact_ref"]).key
            == artifact_ref_for_model_ref(registry, wanted).key
            and wanted.horizon_days in row["supported_horizons"]
        ),
        None,
    )
    if match is None:
        raise FileNotFoundError(f"Model is not present in runtime batch: {wanted.key}")
    return Path(root) / str(match["path"])
