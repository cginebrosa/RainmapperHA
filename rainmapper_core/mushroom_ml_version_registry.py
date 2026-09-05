"""Persistent per-version installation registry for mushroom ML generations."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from rainmapper_core import mushroom_paths


SCHEMA_VERSION = "2.0"
LEGACY_SCHEMA_VERSION = "1.0"
REGISTRY_KIND = "mushroom_ml_version_registry"
VERSION_STATUSES = frozenset({"candidate", "reference", "proposed"})
GENERATION_KINDS = frozenset({"benchmark", "trained_model"})
PROMOTION_GATE_STATUSES = frozenset({"not_evaluated", "passed", "failed"})
REVISION_VECTOR_KEYS = (
    "observations_revision",
    "weather_generation_id",
    "weather_manifest_sha256",
    "sites_revision",
    "stations_revision",
    "catalogs_revision",
    "gis_revision",
    "training_contract_version",
)


def _non_empty_string(value: object, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{label} must be a non-empty string.")
    return normalized


def _version_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("versions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("ML version registry must contain versions.")
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(value: str) -> Path:
    relative = Path(_non_empty_string(value, "artifact path"))
    if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
        raise ValueError(f"Unsafe generation artifact path: {value}")
    return relative


def validate_revision_vector(value: object) -> dict[str, str]:
    """Validate the metadata-only identity used by quick freshness checks."""
    if not isinstance(value, dict):
        raise ValueError("input_revisions must be an object.")
    missing = [key for key in REVISION_VECTOR_KEYS if key not in value]
    if missing:
        raise ValueError("input_revisions are incomplete.")
    return {
        key: _non_empty_string(value[key], f"input_revisions.{key}")
        for key in REVISION_VECTOR_KEYS
    }


def training_contract_revision(payload: object) -> str:
    """Hash code-owned training definitions without installation lifecycle state."""
    checked = validate_registry(payload)
    contract = copy.deepcopy(checked)
    contract.pop("preferred_version_id", None)
    contract.pop("retention_policy", None)
    for version in contract["versions"]:
        for key in (
            "status",
            "installed_generation_id",
            "generations",
            "installation",
        ):
            version.pop(key, None)
    encoded = json.dumps(
        contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return f"registry-{SCHEMA_VERSION}:sha256:{hashlib.sha256(encoded).hexdigest()}"


def validate_registry(payload: object) -> dict[str, Any]:
    """Validate and normalize one registry without changing lifecycle state."""
    if not isinstance(payload, dict):
        raise ValueError("ML version registry must be an object.")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported ML version registry schema.")
    if payload.get("kind") != REGISTRY_KIND:
        raise ValueError("Unsupported ML version registry kind.")
    normalized = copy.deepcopy(payload)
    rows = _version_rows(normalized)
    seen_versions: set[str] = set()
    seen_generations: set[str] = set()
    installed: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("ML version registry entries must be objects.")
        version_id = _non_empty_string(row.get("version_id"), "version_id")
        if version_id in seen_versions:
            raise ValueError(f"Duplicate ML version_id: {version_id}")
        seen_versions.add(version_id)
        status = _non_empty_string(row.get("status"), f"{version_id}.status")
        if status not in VERSION_STATUSES:
            raise ValueError(f"Unsupported status for {version_id}: {status}")
        installed_generation_id = row.get("installed_generation_id")
        if installed_generation_id is not None:
            installed_generation_id = _non_empty_string(
                installed_generation_id, f"{version_id}.installed_generation_id"
            )
        row["installed_generation_id"] = installed_generation_id
        contracts = row.get("temporal_contract_ids")
        if not isinstance(contracts, list) or not contracts:
            raise ValueError(f"{version_id} must declare temporal_contract_ids.")
        normalized_contracts = [
            _non_empty_string(value, f"{version_id}.temporal_contract_ids")
            for value in contracts
        ]
        if len(set(normalized_contracts)) != len(normalized_contracts):
            raise ValueError(f"{version_id} declares duplicate temporal contracts.")
        row["temporal_contract_ids"] = normalized_contracts
        generations = row.get("generations", [])
        if not isinstance(generations, list):
            raise ValueError(f"{version_id}.generations must be a list.")
        for generation in generations:
            if not isinstance(generation, dict):
                raise ValueError(f"{version_id} generation must be an object.")
            generation_id = _non_empty_string(
                generation.get("generation_id"), f"{version_id}.generation_id"
            )
            if generation_id in seen_generations:
                raise ValueError(f"Duplicate generation_id: {generation_id}")
            seen_generations.add(generation_id)
            if generation.get("version_id") != version_id:
                raise ValueError(f"Generation {generation_id} has the wrong version_id.")
            if generation.get("kind") not in GENERATION_KINDS:
                raise ValueError(f"Generation {generation_id} has an unsupported kind.")
            if generation.get("retention") != "permanent":
                raise ValueError(f"Generation {generation_id} must use permanent retention.")
            gate_status = generation.get("promotion_gate_status", "not_evaluated")
            if gate_status not in PROMOTION_GATE_STATUSES:
                raise ValueError(
                    f"Generation {generation_id} has an unsupported promotion gate status."
                )
            if gate_status == "passed" and generation.get("kind") != "trained_model":
                raise ValueError(
                    f"Only a trained_model generation can pass promotion gates: {generation_id}."
                )
            revision_vector = generation.get("input_revisions")
            if revision_vector is not None:
                generation["input_revisions"] = validate_revision_vector(
                    revision_vector
                )
        if installed_generation_id is not None:
            generation = next(
                (
                    candidate
                    for candidate in generations
                    if candidate.get("generation_id") == installed_generation_id
                ),
                None,
            )
            if generation is None or generation.get("kind") != "trained_model":
                raise ValueError(
                    f"Installed generation {installed_generation_id} is not registered for {version_id}."
                )
            if generation.get("promotion_gate_status") != "passed":
                raise ValueError(
                    f"Installed generation {installed_generation_id} has not passed its gates."
                )
            _non_empty_string(generation.get("batch_id"), f"{installed_generation_id}.batch_id")
            installed[version_id] = installed_generation_id

    from rainmapper_core import mushroom_ml_model_catalog  # noqa: PLC0415

    catalog = mushroom_ml_model_catalog.catalog_entries(normalized)
    for version_id, generation_id in installed.items():
        generation = next(
            generation
            for version in rows
            if version["version_id"] == version_id
            for generation in version.get("generations", [])
            if generation.get("generation_id") == generation_id
        )
        required_profiles = {
            row["profile_id"]
            for row in catalog
            if row["version_id"] == version_id and row["operational_eligible"] is True
        }
        if not required_profiles or set(generation.get("profile_ids") or []) != required_profiles:
            raise ValueError(
                f"Installed generation {generation_id} does not contain the full version."
            )
    preferred = normalized.get("preferred_version_id")
    if preferred is not None:
        preferred = _non_empty_string(preferred, "preferred_version_id")
        if preferred not in installed:
            raise ValueError("preferred_version_id must identify an installed version.")
    normalized["preferred_version_id"] = preferred
    for obsolete in ("active_version_id", "active_operational_target", "activation_history"):
        if obsolete in normalized:
            raise ValueError(f"Obsolete monoversion field is not supported: {obsolete}")
    return normalized


def _read_registry_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load ML version registry: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("ML version registry must be an object.")
    return payload


def load_registry(path: Path) -> dict[str, Any]:
    return validate_registry(_read_registry_payload(path))


def _migrate_legacy_registry_v1(
    payload: object,
    packaged: object,
) -> dict[str, Any]:
    """Convert the single-active-version registry without guessing installations."""
    if not isinstance(payload, dict):
        raise ValueError("ML version registry must be an object.")
    if payload.get("schema_version") != LEGACY_SCHEMA_VERSION:
        raise ValueError("Unsupported ML version registry schema.")
    if payload.get("kind") != REGISTRY_KIND:
        raise ValueError("Unsupported ML version registry kind.")

    defaults = validate_registry(packaged)
    default_by_id = {row["version_id"]: row for row in defaults["versions"]}
    legacy_rows = payload.get("versions")
    if not isinstance(legacy_rows, list) or not legacy_rows:
        raise ValueError("ML version registry must contain versions.")

    legacy_by_id: dict[str, dict[str, Any]] = {}
    active_versions: list[str] = []
    seen_generations: set[str] = set()
    for row in legacy_rows:
        if not isinstance(row, dict):
            raise ValueError("ML version registry entries must be objects.")
        version_id = _non_empty_string(row.get("version_id"), "version_id")
        if version_id in legacy_by_id:
            raise ValueError(f"Duplicate ML version_id: {version_id}")
        if version_id not in default_by_id:
            raise ValueError(
                f"Cannot safely migrate unknown legacy ML version: {version_id}"
            )
        status = _non_empty_string(row.get("status"), f"{version_id}.status")
        if status not in VERSION_STATUSES | {"active"}:
            raise ValueError(f"Unsupported status for {version_id}: {status}")
        if status == "active":
            active_versions.append(version_id)
        generations = row.get("generations", [])
        if not isinstance(generations, list):
            raise ValueError(f"{version_id}.generations must be a list.")
        for generation in generations:
            if not isinstance(generation, dict):
                raise ValueError(f"{version_id} generation must be an object.")
            generation_id = _non_empty_string(
                generation.get("generation_id"), f"{version_id}.generation_id"
            )
            if generation_id in seen_generations:
                raise ValueError(f"Duplicate generation_id: {generation_id}")
            seen_generations.add(generation_id)
            if generation.get("version_id") != version_id:
                raise ValueError(
                    f"Generation {generation_id} has the wrong version_id."
                )
            if generation.get("kind") not in GENERATION_KINDS:
                raise ValueError(
                    f"Generation {generation_id} has an unsupported kind."
                )
            if generation.get("retention") != "permanent":
                raise ValueError(
                    f"Generation {generation_id} must use permanent retention."
                )
        legacy_by_id[version_id] = copy.deepcopy(row)

    active_version_id = _non_empty_string(
        payload.get("active_version_id"), "active_version_id"
    )
    if active_versions != [active_version_id]:
        raise ValueError("active_version_id does not match the active version entry.")
    raw_target = payload.get("active_operational_target")
    if raw_target is None:
        raw_target = {
            "version_id": active_version_id,
            "generation_id": "",
        }
    if not isinstance(raw_target, dict):
        raise ValueError("active_operational_target must be an object.")
    target_version_id = _non_empty_string(
        raw_target.get("version_id"), "active_operational_target.version_id"
    )
    if target_version_id != active_version_id:
        raise ValueError("The operational target must belong to the active version.")
    target_generation_id = str(raw_target.get("generation_id") or "").strip()
    if target_generation_id:
        active_generation = next(
            (
                generation
                for generation in legacy_by_id[active_version_id].get(
                    "generations", []
                )
                if generation.get("generation_id") == target_generation_id
            ),
            None,
        )
        if active_generation is None or active_generation.get("kind") != "trained_model":
            raise ValueError("The operational target generation is not registered.")

    migrated = copy.deepcopy(defaults)
    for definition in migrated["versions"]:
        existing = legacy_by_id.get(definition["version_id"])
        if existing is None:
            continue
        existing_status = existing["status"]
        if existing_status != "active" and not (
            existing_status == "proposed" and definition["status"] == "candidate"
        ):
            definition["status"] = existing_status
        definition["generations"] = copy.deepcopy(existing.get("generations", []))
        definition["installed_generation_id"] = (
            target_generation_id
            if definition["version_id"] == active_version_id
            and target_generation_id
            else None
        )
    migrated["preferred_version_id"] = (
        active_version_id if target_generation_id else None
    )
    return validate_registry(migrated)


def _preserve_legacy_registry_backup(path: Path) -> Path:
    source = Path(path)
    backup = source.with_name(
        f"{source.stem}.schema-{LEGACY_SCHEMA_VERSION}.backup{source.suffix}"
    )
    original = source.read_bytes()
    if backup.is_file():
        if backup.read_bytes() != original:
            raise ValueError(
                f"Legacy ML registry backup already exists with different contents: {backup}"
            )
        return backup
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{backup.name}.", suffix=".tmp", dir=backup.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, backup)
    finally:
        temporary.unlink(missing_ok=True)
    return backup


def training_version_ids(
    payload: object,
    *,
    job_purpose: str,
    requested_version_ids: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Resolve operational or benchmark scope from the validated registry."""
    checked = validate_registry(payload)
    purpose = str(job_purpose or "").strip()
    if purpose == "operational":
        eligible = {
            row["version_id"]
            for row in operational_profile_options(checked)
        }
        if requested_version_ids is None:
            version_ids = [
                str(row["version_id"])
                for row in checked["versions"]
                if row.get("installed_generation_id") is not None
            ]
        else:
            version_ids = [str(value or "").strip() for value in requested_version_ids]
        if not version_ids or any(not value for value in version_ids):
            raise ValueError("Select at least one operational ML version.")
        if len(version_ids) != len(set(version_ids)):
            raise ValueError("Operational ML version selection contains duplicates.")
        unknown = [value for value in version_ids if value not in eligible]
        if unknown:
            raise ValueError(f"ML version is not operationally eligible: {unknown[0]}")
        requested = set(version_ids)
        return [
            str(row["version_id"])
            for row in checked["versions"]
            if row["version_id"] in requested
        ]
    if purpose == "benchmark":
        version_ids = [
            str(row["version_id"])
            for row in checked["versions"]
            if row.get("benchmark_available") is True
        ]
        if not version_ids:
            raise ValueError("The ML registry has no benchmark versions.")
        return version_ids
    raise ValueError("ML training job purpose is invalid.")


def operational_profile_options(payload: object) -> list[dict[str, str]]:
    """Return profiles that the runtime can execute; metrics do not gate this list."""
    checked = validate_registry(payload)
    from rainmapper_core import mushroom_ml_model_catalog  # noqa: PLC0415

    return [
        {
            "profile_key": f"{row['version_id']}/{row['profile_id']}",
            "version_id": str(row["version_id"]),
            "version_name": str(row["version_display_name"]),
            "profile_id": str(row["profile_id"]),
            "profile_name": str(row["profile_display_name"]),
        }
        for row in mushroom_ml_model_catalog.catalog_entries(checked)
        if row["operational_eligible"] is True
    ]


def operational_version_options(payload: object) -> list[dict[str, Any]]:
    """Group executable operational profiles by their registry version."""
    checked = validate_registry(payload)
    version_state = {
        str(row["version_id"]): row
        for row in checked["versions"]
    }
    grouped: dict[str, dict[str, Any]] = {}
    for profile in operational_profile_options(checked):
        version_id = profile["version_id"]
        option = grouped.setdefault(
            version_id,
            {
                "version_id": version_id,
                "version_name": profile["version_name"],
                "profile_keys": [],
                "profile_names": [],
                "installed": bool(
                    version_state[version_id].get("installed_generation_id")
                ),
            },
        )
        option["profile_keys"].append(profile["profile_key"])
        option["profile_names"].append(profile["profile_name"])
    return list(grouped.values())


def resolve_operational_profile(payload: object, profile_key: str) -> dict[str, str]:
    """Resolve one human-selected technically executable operational profile."""
    resolved_key = _non_empty_string(profile_key, "profile_key")
    match = next(
        (
            row
            for row in operational_profile_options(payload)
            if row["profile_key"] == resolved_key
        ),
        None,
    )
    if match is None:
        raise ValueError(f"Profile is not technically promotable: {resolved_key}")
    return match


def training_profile_keys(
    payload: object,
    *,
    job_purpose: str,
    version_ids: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Resolve every profile belonging to selected operational versions."""
    if str(job_purpose or "").strip() != "operational":
        raise ValueError("Profile scope is only defined for operational training.")
    checked = validate_registry(payload)
    selected_versions = training_version_ids(
        checked,
        job_purpose="operational",
        requested_version_ids=version_ids,
    )
    selected = set(selected_versions)
    return [
        row["profile_key"]
        for row in operational_profile_options(checked)
        if row["version_id"] in selected
    ]


def benchmark_profile_options(payload: object) -> list[dict[str, str]]:
    """Return selectable benchmark profiles in stable registry order."""
    checked = validate_registry(payload)
    options: list[dict[str, str]] = []
    for version in checked["versions"]:
        if version.get("benchmark_available") is not True:
            continue
        runtime = version.get("runtime")
        profiles = runtime.get("profiles") if isinstance(runtime, dict) else []
        for profile in profiles if isinstance(profiles, list) else []:
            if (
                not isinstance(profile, dict)
                or profile.get("comparison_eligible_when_trained") is not True
            ):
                continue
            version_id = str(version["version_id"])
            profile_id = str(profile.get("profile_id") or "")
            if not profile_id:
                continue
            options.append(
                {
                    "profile_key": f"{version_id}/{profile_id}",
                    "version_id": version_id,
                    "version_name": str(version.get("display_name") or version_id),
                    "profile_id": profile_id,
                    "profile_name": str(profile.get("display_name") or profile_id),
                    "profile_label_key": str(
                        profile.get("display_label_key") or ""
                    ),
                }
            )
    if not options:
        raise ValueError("The ML registry has no selectable benchmark profiles.")
    return options


def resolve_benchmark_profiles(
    payload: object,
    requested_profile_keys: list[str] | tuple[str, ...] | None,
) -> list[dict[str, str]]:
    """Validate a benchmark selection; an omitted selection means every profile."""
    options = benchmark_profile_options(payload)
    if requested_profile_keys is None:
        return options
    requested = [str(value or "").strip() for value in requested_profile_keys]
    if not requested or any(not value for value in requested):
        raise ValueError("Select at least one benchmark profile.")
    if len(set(requested)) != len(requested):
        raise ValueError("Benchmark profile selection contains duplicates.")
    by_key = {row["profile_key"]: row for row in options}
    unknown = [value for value in requested if value not in by_key]
    if unknown:
        raise ValueError("Unknown benchmark profile: " + unknown[0])
    requested_set = set(requested)
    return [row for row in options if row["profile_key"] in requested_set]


def merge_packaged_definitions(
    packaged: object,
    persistent: object,
) -> dict[str, Any]:
    """Refresh code-owned contracts while retaining persistent lifecycle state."""
    defaults = validate_registry(packaged)
    current = validate_registry(persistent)
    current_by_id = {row["version_id"]: row for row in current["versions"]}
    merged = copy.deepcopy(defaults)
    merged_versions: list[dict[str, Any]] = []
    packaged_ids: set[str] = set()
    for definition in defaults["versions"]:
        version_id = definition["version_id"]
        packaged_ids.add(version_id)
        row = copy.deepcopy(definition)
        existing = current_by_id.get(version_id)
        if existing is not None:
            # A packaged proposed->candidate change is a forward-only technical
            # capability migration. Preserve every user-driven lifecycle state,
            # but do not leave an existing installation unable to use a newly
            # implemented candidate forever.
            if not (
                existing["status"] == "proposed"
                and definition["status"] == "candidate"
            ):
                row["status"] = existing["status"]
            row["generations"] = copy.deepcopy(existing.get("generations", []))
            row["installed_generation_id"] = existing.get(
                "installed_generation_id"
            )
        merged_versions.append(row)
    merged_versions.extend(
        copy.deepcopy(row)
        for row in current["versions"]
        if row["version_id"] not in packaged_ids
    )
    merged["versions"] = merged_versions
    merged["preferred_version_id"] = current.get("preferred_version_id")
    return validate_registry(merged)


def ensure_seeded(
    *,
    default_path: Path | None = None,
    persistent_path: Path | None = None,
) -> Path:
    """Create the persistent registry once without replacing later lifecycle state."""
    source = Path(
        default_path
        or mushroom_paths.app_mushroom_defaults_dir()
        / "mushroom_ml_version_registry.json"
    )
    destination = Path(
        persistent_path
        or mushroom_paths.mushroom_data_file("mushroom_ml_version_registry.json")
    )
    packaged = load_registry(source)
    if destination.is_file():
        raw_persistent = _read_registry_payload(destination)
        legacy_migration = (
            raw_persistent.get("schema_version") == LEGACY_SCHEMA_VERSION
        )
        persistent = (
            _migrate_legacy_registry_v1(raw_persistent, packaged)
            if legacy_migration
            else validate_registry(raw_persistent)
        )
        merged = merge_packaged_definitions(packaged, persistent)
        if legacy_migration:
            _preserve_legacy_registry_backup(destination)
        if legacy_migration or merged != persistent:
            save_registry(destination, merged)
        return destination
    save_registry(destination, packaged)
    return destination


def save_registry(path: Path, payload: object) -> None:
    """Atomically write a validated registry. Existing generations are retained."""
    destination = Path(path)
    checked = validate_registry(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(checked, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def register_version(payload: object, definition: dict[str, Any]) -> dict[str, Any]:
    """Append an arbitrary future version without adding version-specific code."""
    checked = validate_registry(payload)
    if not isinstance(definition, dict):
        raise ValueError("ML version definition must be an object.")
    candidate = copy.deepcopy(definition)
    version_id = _non_empty_string(candidate.get("version_id"), "version_id")
    if any(row["version_id"] == version_id for row in checked["versions"]):
        raise ValueError(f"Duplicate ML version_id: {version_id}")
    if candidate.get("status") not in VERSION_STATUSES:
        raise ValueError("Register a new version as proposed, candidate, or reference.")
    candidate.setdefault("installed_generation_id", None)
    candidate.setdefault("generations", [])
    checked["versions"].append(candidate)
    return validate_registry(checked)


def transition_non_active_status(
    payload: object,
    version_id: str,
    status: str,
) -> dict[str, Any]:
    """Move a non-active version between proposed, candidate, and reference."""
    checked = validate_registry(payload)
    target_id = _non_empty_string(version_id, "version_id")
    resolved_status = _non_empty_string(status, "status")
    if resolved_status not in VERSION_STATUSES:
        raise ValueError("Unsupported ML version lifecycle status.")
    target = next(
        (row for row in checked["versions"] if row["version_id"] == target_id), None
    )
    if target is None:
        raise ValueError(f"Unknown ML version: {target_id}")
    target["status"] = resolved_status
    return validate_registry(checked)


def transition_active_generation(
    payload: object,
    version_id: str,
    *,
    generation_id: str,
    approved_by: str = "local_user",
) -> dict[str, Any]:
    """Install a complete trained generation without affecting other versions."""
    checked = validate_registry(payload)
    target_id = _non_empty_string(version_id, "version_id")
    target_profiles = [
        row
        for row in operational_profile_options(checked)
        if row["version_id"] == target_id
    ]
    if not target_profiles:
        raise ValueError("The selected version has no technically promotable profiles.")
    resolved_generation_id = _non_empty_string(generation_id, "generation_id")
    version = next(
        (row for row in checked["versions"] if row["version_id"] == target_id), None
    )
    if version is None:
        raise ValueError(f"Unknown ML version: {target_id}")
    if version.get("status") == "proposed":
        raise ValueError("A proposed version cannot be installed before implementation.")
    generation = next(
        (
            row
            for row in version.get("generations", [])
            if row.get("generation_id") == resolved_generation_id
        ),
        None,
    )
    if generation is None or generation.get("kind") != "trained_model":
        raise ValueError("Only a registered trained_model generation can be installed.")
    if generation.get("promotion_gate_status") != "passed":
        raise ValueError("The candidate has not passed its technical promotion gates.")
    if set(generation.get("profile_ids") or []) != {
        row["profile_id"] for row in target_profiles
    }:
        raise ValueError("The candidate does not contain every operational profile.")
    _non_empty_string(generation.get("batch_id"), "batch_id")
    previous_generation_id = version.get("installed_generation_id")
    version["generations"] = [
        row
        for row in version.get("generations", [])
        if row.get("kind") != "trained_model"
        or row.get("generation_id") == resolved_generation_id
    ]
    version["installed_generation_id"] = resolved_generation_id
    if checked.get("preferred_version_id") is None:
        checked["preferred_version_id"] = target_id
    version["installation"] = {
        "approved_by": _non_empty_string(approved_by, "approved_by"),
        "previous_generation_id": previous_generation_id,
    }
    return validate_registry(checked)


def set_preferred_version(payload: object, version_id: str | None) -> dict[str, Any]:
    """Move the default Predictor pointer without touching installed generations."""
    checked = validate_registry(payload)
    if version_id is None:
        checked["preferred_version_id"] = None
        return validate_registry(checked)
    target_id = _non_empty_string(version_id, "version_id")
    target = next(
        (row for row in checked["versions"] if row["version_id"] == target_id), None
    )
    if target is None or target.get("installed_generation_id") is None:
        raise ValueError("Only an installed ML version can be preferred.")
    checked["preferred_version_id"] = target_id
    return validate_registry(checked)


def uninstall_version(payload: object, version_id: str) -> dict[str, Any]:
    """Hide one version by clearing only its installed pointer."""
    checked = validate_registry(payload)
    target_id = _non_empty_string(version_id, "version_id")
    target = next(
        (row for row in checked["versions"] if row["version_id"] == target_id), None
    )
    if target is None:
        raise ValueError(f"Unknown ML version: {target_id}")
    target["installed_generation_id"] = None
    if checked.get("preferred_version_id") == target_id:
        checked["preferred_version_id"] = None
    return validate_registry(checked)


def installed_generation(payload: object, version_id: str) -> dict[str, Any] | None:
    """Return the single installed generation for a version, when present."""
    checked = validate_registry(payload)
    target_id = _non_empty_string(version_id, "version_id")
    version = next(
        (row for row in checked["versions"] if row["version_id"] == target_id), None
    )
    if version is None:
        raise ValueError(f"Unknown ML version: {target_id}")
    generation_id = version.get("installed_generation_id")
    if generation_id is None:
        return None
    return copy.deepcopy(
        next(
            row
            for row in version.get("generations", [])
            if row.get("generation_id") == generation_id
        )
    )


def installed_manifest_path(
    payload: object,
    version_id: str,
    *,
    models_root: Path,
) -> Path | None:
    """Resolve one installed version directly through generation.batch_id."""
    generation = installed_generation(payload, version_id)
    if generation is None:
        return None
    return Path(models_root) / "batches" / str(generation["batch_id"]) / "manifest.json"


def operational_manifest_path(
    payload: object,
    *,
    models_root: Path,
) -> Path | None:
    """Resolve the one batch shared by every installed operational version."""
    checked = validate_registry(payload)
    batch_ids = {
        str(generation["batch_id"])
        for version in checked["versions"]
        if (generation := installed_generation(checked, version["version_id"]))
        is not None
    }
    if not batch_ids:
        return None
    if len(batch_ids) != 1:
        raise ValueError("Installed ML versions do not share one operational batch.")
    return Path(models_root) / "batches" / next(iter(batch_ids)) / "manifest.json"


def preferred_manifest_path(
    payload: object,
    *,
    models_root: Path,
) -> Path | None:
    checked = validate_registry(payload)
    preferred = checked.get("preferred_version_id")
    if preferred is None:
        return None
    return installed_manifest_path(checked, preferred, models_root=models_root)


def install_batch_generations(
    payload: object,
    manifest: dict[str, Any],
    *,
    approved_by: str = "local_user",
) -> dict[str, Any]:
    """Register and install every complete version contained in one batch."""
    checked = validate_registry(payload)
    batch_id = _non_empty_string(manifest.get("batch_id"), "batch_id")
    artifacts = manifest.get("artifacts")
    profile_keys = [str(value) for value in manifest.get("profile_keys", [])]
    if not isinstance(artifacts, list) or not artifacts or not profile_keys:
        raise ValueError("Operational batch has no installable artifacts or profiles.")
    generation_ids: dict[str, str] = {}
    for artifact in artifacts:
        reference = artifact.get("artifact_ref") if isinstance(artifact, dict) else None
        if not isinstance(reference, dict):
            raise ValueError("Operational batch artifact identity is invalid.")
        version_id = _non_empty_string(reference.get("version_id"), "version_id")
        generation_id = _non_empty_string(
            reference.get("generation_id"), "generation_id"
        )
        previous = generation_ids.setdefault(version_id, generation_id)
        if previous != generation_id:
            raise ValueError(f"Operational batch mixes generations for {version_id}.")
    result = checked
    for version_id, generation_id in generation_ids.items():
        profile_ids = [
            key.split("/", 1)[1]
            for key in profile_keys
            if key.startswith(version_id + "/")
        ]
        version = next(
            row for row in result["versions"] if row["version_id"] == version_id
        )
        if not any(
            row.get("generation_id") == generation_id
            for row in version.get("generations", [])
        ):
            result = append_generation(
                result,
                version_id=version_id,
                generation={
                    "generation_id": generation_id,
                    "kind": "trained_model",
                    "profile_ids": profile_ids,
                    "batch_id": batch_id,
                    "snapshot_id": str(manifest.get("snapshot_id") or ""),
                    "input_revisions": manifest.get("input_revisions"),
                    "promotion_gate_status": "passed",
                    "promotion_gate_kind": "verified_operational_batch",
                },
            )
        result = transition_active_generation(
            result,
            version_id,
            generation_id=generation_id,
            approved_by=approved_by,
        )
    return validate_registry(result)


def append_generation(
    payload: object,
    *,
    version_id: str,
    generation: dict[str, Any],
) -> dict[str, Any]:
    """Append an immutable benchmark/model generation; never replace an older one."""
    checked = validate_registry(payload)
    resolved_version_id = _non_empty_string(version_id, "version_id")
    row = next(
        (
            candidate
            for candidate in checked["versions"]
            if candidate["version_id"] == resolved_version_id
        ),
        None,
    )
    if row is None:
        raise ValueError(f"Unknown ML version: {resolved_version_id}")
    normalized_generation = copy.deepcopy(generation)
    normalized_generation["version_id"] = resolved_version_id
    normalized_generation["retention"] = "permanent"
    row.setdefault("generations", []).append(normalized_generation)
    return validate_registry(checked)


def persist_generation(
    registry_path: Path,
    archive_root: Path,
    *,
    version_id: str,
    kind: str,
    artifacts: dict[str, Path],
    input_identities: dict[str, str],
    metadata: dict[str, Any] | None = None,
    promotion_gate_status: str = "not_evaluated",
) -> dict[str, Any]:
    """Copy one generation into a permanent content-addressed local archive."""
    if kind not in GENERATION_KINDS:
        raise ValueError(f"Unsupported generation kind: {kind}")
    if promotion_gate_status not in PROMOTION_GATE_STATUSES:
        raise ValueError("Unsupported promotion_gate_status.")
    if kind != "trained_model" and promotion_gate_status == "passed":
        raise ValueError("Only a trained_model generation can pass promotion gates.")
    if not artifacts:
        raise ValueError("A generation must contain at least one artifact.")
    checked = load_registry(registry_path)
    resolved_version_id = _non_empty_string(version_id, "version_id")
    if Path(resolved_version_id).name != resolved_version_id:
        raise ValueError("version_id is unsafe for an archive path.")
    if not any(
        row["version_id"] == resolved_version_id for row in checked["versions"]
    ):
        raise ValueError(f"Unknown ML version: {resolved_version_id}")
    artifact_rows: list[dict[str, Any]] = []
    resolved_sources: dict[str, Path] = {}
    for logical_name, source_value in sorted(artifacts.items()):
        relative = _safe_relative_path(logical_name)
        logical_path = relative.as_posix()
        source = Path(source_value)
        if not source.is_file():
            raise FileNotFoundError(f"Generation artifact is missing: {source}")
        if logical_path in resolved_sources:
            raise ValueError(f"Duplicate generation artifact path: {logical_path}")
        resolved_sources[logical_path] = source
        artifact_rows.append(
            {
                "path": logical_path,
                "size_bytes": source.stat().st_size,
                "sha256": _sha256(source),
            }
        )
    identity = {
        "version_id": resolved_version_id,
        "kind": kind,
        "promotion_gate_status": promotion_gate_status,
        "artifacts": artifact_rows,
        "input_identities": {
            _non_empty_string(key, "input identity name"): _non_empty_string(
                value, f"input identity {key}"
            )
            for key, value in sorted(input_identities.items())
        },
        "metadata": copy.deepcopy(metadata or {}),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    generation_id = f"{resolved_version_id}-{hashlib.sha256(encoded).hexdigest()[:20]}"
    version_root = Path(archive_root) / resolved_version_id
    destination = version_root / generation_id
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "kind": "mushroom_ml_preserved_generation",
        "generation_id": generation_id,
        "retention": "permanent",
        **identity,
    }
    existing_generation = next(
        (
            generation
            for row in checked["versions"]
            if row["version_id"] == resolved_version_id
            for generation in row.get("generations", [])
            if generation.get("generation_id") == generation_id
        ),
        None,
    )
    if existing_generation is not None:
        stored_manifest = destination / "generation_manifest.json"
        if not stored_manifest.is_file() or json.loads(
            stored_manifest.read_text(encoding="utf-8")
        ) != manifest:
            raise ValueError("Registered ML generation archive is missing or changed.")
        return {"registry": checked, "generation": existing_generation, "status": "reused"}

    version_root.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{generation_id}.", suffix=".tmp", dir=version_root)
    )
    try:
        for artifact in artifact_rows:
            source = resolved_sources[artifact["path"]]
            target = staging / artifact["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if target.stat().st_size != artifact["size_bytes"] or _sha256(target) != artifact["sha256"]:
                raise ValueError(f"Archived generation artifact changed: {artifact['path']}")
        (staging / "generation_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if destination.exists():
            raise FileExistsError(f"Generation archive already exists: {destination}")
        os.replace(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    generation = {
        "generation_id": generation_id,
        "kind": kind,
        "retention": "permanent",
        "version_id": resolved_version_id,
        "manifest_path": str(
            (Path(resolved_version_id) / generation_id / "generation_manifest.json")
        ),
        "artifact_count": len(artifact_rows),
        "input_identities": identity["input_identities"],
        "promotion_gate_status": identity["promotion_gate_status"],
    }
    updated = append_generation(
        checked, version_id=resolved_version_id, generation=generation
    )
    save_registry(registry_path, updated)
    return {"registry": updated, "generation": generation, "status": "created"}


def benchmark_version_metadata(
    payload: object, version_ids: list[str]
) -> dict[str, Any]:
    """Return stable version metadata suitable for embedding in a report."""
    checked = validate_registry(payload)
    requested = set(version_ids)
    found = {
        row["version_id"]: {
            "version_id": row["version_id"],
            "status": row["status"],
            "temporal_contract_ids": list(row["temporal_contract_ids"]),
            "contract_document": row.get("contract_document"),
            "generation_count": len(row.get("generations", [])),
            "retention": "permanent",
        }
        for row in checked["versions"]
        if row["version_id"] in requested
    }
    missing = sorted(requested - set(found))
    if missing:
        raise ValueError(f"Unknown ML benchmark version: {missing[0]}")
    return {version_id: found[version_id] for version_id in version_ids}


def version_for_temporal_contract(
    payload: object, temporal_contract_id: str
) -> dict[str, Any]:
    """Resolve a contract through registry data, independent of version names."""
    checked = validate_registry(payload)
    contract_id = _non_empty_string(temporal_contract_id, "temporal_contract_id")
    matches = [
        row
        for row in checked["versions"]
        if contract_id in row["temporal_contract_ids"]
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Temporal contract {contract_id} must belong to exactly one ML version."
        )
    return copy.deepcopy(matches[0])
