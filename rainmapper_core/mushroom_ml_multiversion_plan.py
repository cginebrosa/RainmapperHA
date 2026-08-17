"""Deterministic fit plan for one same-snapshot multiversion ML batch."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from rainmapper_core import mushroom_ml_model_catalog as catalog


PLAN_SCHEMA_VERSION = "1.0"
PLAN_KIND = "mushroom_ml_multiversion_training_plan"


def build_plan(
    registry: Mapping[str, object],
    *,
    batch_id: str,
    snapshot_id: str,
    generation_ids: Mapping[str, str],
    species_ids: Sequence[str],
) -> dict[str, Any]:
    """Create one fit per artifact; lag horizons are metadata, never fits."""
    normalized_species = sorted(
        {catalog._identifier(value, "species_id") for value in species_ids}
    )
    if not normalized_species:
        raise ValueError("Multiversion training requires species")
    resolved_batch = catalog._identifier(batch_id, "batch_id")
    if not (
        isinstance(snapshot_id, str)
        and snapshot_id.startswith("sha256:")
        and len(snapshot_id) == 71
    ):
        raise ValueError("Multiversion training requires a SHA-256 snapshot_id")
    fits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for profile in catalog.catalog_entries(registry):
        version_id = str(profile["version_id"])
        generation_id = catalog._identifier(
            generation_ids.get(version_id), f"{version_id}.generation_id"
        )
        for temporal_contract_id in profile["temporal_contract_ids"]:
            for estimator_id in profile["estimator_ids"]:
                scope = profile["estimator_scopes"][estimator_id]
                artifact_species = (
                    normalized_species if scope == "species" else ["all_species"]
                )
                for species_id in artifact_species:
                    artifact_ref = catalog.ModelArtifactRef(
                        batch_id=resolved_batch,
                        generation_id=generation_id,
                        version_id=version_id,
                        temporal_contract_id=str(temporal_contract_id),
                        profile_id=str(profile["profile_id"]),
                        estimator_id=str(estimator_id),
                        species_id=species_id,
                    )
                    catalog.validate_artifact_ref(registry, artifact_ref)
                    if artifact_ref.key in seen:
                        raise ValueError(f"Duplicate multiversion fit: {artifact_ref.key}")
                    seen.add(artifact_ref.key)
                    fits.append(
                        {
                            "artifact_ref": artifact_ref.as_dict(),
                            "estimator_scope": scope,
                            "training_species_ids": (
                                [species_id] if scope == "species" else normalized_species
                            ),
                            "supported_horizons": sorted(
                                catalog.supported_horizons(str(temporal_contract_id))
                            ),
                        }
                    )
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "kind": PLAN_KIND,
        "batch_id": resolved_batch,
        "snapshot_id": snapshot_id,
        "species_ids": normalized_species,
        "fit_count": len(fits),
        "fits": fits,
        "lag_fit_policy": "one_fit_per_species_contract_profile_estimator",
        "horizon_policy": "filter_or_feature_of_same_fit_never_retrain",
    }
