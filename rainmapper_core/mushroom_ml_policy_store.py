"""Portable serving rules, separate from installation/generation state.

Only live registries have a local reference. Loading resolves that reference;
sealed worker snapshots always contain the effective rules, never a live path.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from rainmapper_core import mushroom_ml_prediction_policy as policy

FILENAME = "mushroom_ml_prediction_policy.json"
REFERENCE = "prediction_policy_file"
KIND = "mushroom_ml_prediction_policy"
MAX_BYTES = 256 * 1024


def document(registry: dict) -> dict:
    return {"schema_version": "1.0", "kind": KIND,
            "suspensions": policy.validate_rules(registry.get(policy.FIELD, []))}


def encode(value: dict) -> bytes:
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("Model settings exceed the 256 KiB limit.")
    return raw


def decode(raw: bytes) -> list[dict]:
    if len(raw) > MAX_BYTES:
        raise ValueError("Model settings exceed the 256 KiB limit.")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid model settings JSON.") from exc
    if (not isinstance(value, dict)
            or set(value) != {"schema_version", "kind", "suspensions"}
            or value.get("schema_version") != "1.0" or value.get("kind") != KIND):
        raise ValueError("Expected a model settings export, not a model registry.")
    return policy.validate_rules(value["suspensions"])


def referenced_path(registry_path: Path, raw_registry: dict) -> Path | None:
    if REFERENCE not in raw_registry:
        return None
    if raw_registry[REFERENCE] != FILENAME:
        raise ValueError("Invalid model settings file reference.")
    return Path(registry_path).parent / FILENAME


def resolve(registry_path: Path, raw_registry: dict) -> dict:
    result = dict(raw_registry)
    path = referenced_path(registry_path, result)
    if path is not None:
        # A missing/corrupt file fails closed; never resurrect legacy rules.
        with path.open("rb") as stream:
            rules = decode(stream.read(MAX_BYTES + 1))
        result.pop(REFERENCE)
        result.pop(policy.FIELD, None)
        if rules:
            result[policy.FIELD] = rules
    encode(result)  # effective registry must also fit the runtime contract
    return result


def atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def migrate(registry_path: Path) -> None:
    """One-time live migration. Write rules before switching the registry pointer."""
    from rainmapper_core import mushroom_ml_version_registry as versions
    path = Path(registry_path)
    raw = versions._read_registry_payload(path)
    if referenced_path(path, raw) is not None:
        resolve(path, raw)
        return
    effective = versions.validate_registry(raw)
    target = path.parent / FILENAME
    wanted = encode(document(effective))
    if target.exists():
        # Recover an interrupted migration only when both copies agree.
        with target.open("rb") as stream:
            existing = decode(stream.read(MAX_BYTES + 1))
        if existing != document(effective)["suspensions"]:
            raise ValueError("Unlinked model settings differ from the registry; migration stopped.")
    else:
        atomic_write(target, wanted)
    effective.pop(policy.FIELD, None)
    effective[REFERENCE] = FILENAME
    versions.save_registry(path, effective)


def save(registry_path: Path, updated: dict, *, expected_revision: str) -> None:
    """Caller holds the coordinator promotion lock; never rewrite generations."""
    from rainmapper_core import mushroom_ml_version_registry as versions
    if policy.revision(versions.load_registry(registry_path)) != expected_revision:
        raise ValueError("Model settings changed. Refresh before saving again.")
    raw = encode(document(updated))
    encode(updated)
    migrate(registry_path)
    atomic_write(Path(registry_path).parent / FILENAME, raw)


def import_rules(raw: bytes, registry: dict, species_ids: set[str], *, expected_revision: str) -> dict:
    from rainmapper_core import mushroom_ml_model_catalog as catalog
    if policy.revision(registry) != expected_revision:
        raise ValueError("Model settings changed. Refresh before saving again.")
    rows = decode(raw)
    models = {(r["version_id"], r["profile_id"], estimator)
              for r in catalog.catalog_entries(registry) for estimator in r["estimator_ids"]}
    for row in rows:
        if tuple(row[k] for k in policy.IDENTITY[:3]) not in models:
            raise ValueError("Unknown prediction model: " + "/".join(row[k] for k in policy.IDENTITY[:3]))
        if row["species_id"] != "*" and row["species_id"] not in species_ids:
            raise ValueError("Unknown species: " + row["species_id"])
    result = dict(registry)
    result.pop(policy.FIELD, None)
    if rows:
        result[policy.FIELD] = rows
    encode(result)
    return result
