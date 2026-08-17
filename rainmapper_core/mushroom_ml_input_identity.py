"""Data-driven semantic identities for ML inputs such as known sites."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _nested_value(payload: object, dotted_path: str) -> object:
    current = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def known_sites_semantic_identity(
    known_sites: object,
    identity_contract: object,
) -> dict[str, Any]:
    """Hash only declared fields globally and per prediction area."""
    if not isinstance(known_sites, dict):
        raise ValueError("known_sites must contain an object")
    if not isinstance(identity_contract, dict):
        raise ValueError("known_sites identity contract must contain an object")
    contract_id = str(identity_contract.get("id") or "").strip()
    collections = identity_contract.get("collections")
    if not contract_id or not isinstance(collections, list) or not collections:
        raise ValueError("known_sites identity contract is incomplete")
    projected_collections: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    row_count = 0
    for collection in collections:
        if not isinstance(collection, dict):
            raise ValueError("known_sites identity collection must be an object")
        collection_path = str(collection.get("path") or "").strip()
        id_field = str(collection.get("id_field") or "").strip()
        group_field = str(collection.get("group_field") or "").strip()
        fields = collection.get("fields")
        if (
            not collection_path
            or not id_field
            or not isinstance(fields, list)
            or not fields
        ):
            raise ValueError("known_sites identity collection is incomplete")
        source_rows = _nested_value(known_sites, collection_path)
        if not isinstance(source_rows, list):
            raise ValueError(f"known_sites collection is missing: {collection_path}")
        projected_rows: list[dict[str, Any]] = []
        for source in source_rows:
            if not isinstance(source, dict):
                continue
            row_id = str(_nested_value(source, id_field) or "").strip()
            if not row_id:
                raise ValueError(
                    f"known_sites identity row has no {id_field}: {collection_path}"
                )
            projected = {
                "id": row_id,
                "values": {
                    str(field): _nested_value(source, str(field)) for field in fields
                },
            }
            projected_rows.append(projected)
            row_count += 1
            if group_field:
                group_id = str(_nested_value(source, group_field) or "").strip()
                if group_id:
                    groups.setdefault(group_id, []).append(
                        {"collection": collection_path, **projected}
                    )
        projected_rows.sort(key=lambda row: row["id"])
        projected_collections.append(
            {"path": collection_path, "rows": projected_rows}
        )
    projected_collections.sort(key=lambda row: row["path"])
    canonical = {"contract_id": contract_id, "collections": projected_collections}
    return {
        "contract_id": contract_id,
        "sha256": _digest(canonical),
        "area_sha256": {
            group_id: _digest(
                {
                    "contract_id": contract_id,
                    "area_id": group_id,
                    "rows": sorted(
                        rows, key=lambda row: (row["collection"], row["id"])
                    ),
                }
            )
            for group_id, rows in sorted(groups.items())
        },
        "row_count": row_count,
    }


def known_sites_semantic_identity_from_path(
    path: Path,
    identity_contract: object,
) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load known_sites identity input: {exc}") from exc
    return known_sites_semantic_identity(payload, identity_contract)
