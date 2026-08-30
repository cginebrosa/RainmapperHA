"""Persistent desired state and two-phase publication for Predictor precompute."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from rainmapper_core.mushroom_predictor_precompute import (
    ArtifactIdentity,
    ArtifactManifest,
    validate_artifact,
)


DESIRED_SCHEMA_VERSION = "1.0"
RECEIPT_SCHEMA_VERSION = "1.0"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def load_desired_state(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != DESIRED_SCHEMA_VERSION:
        raise ValueError("Predictor precompute desired state is invalid.")
    ArtifactIdentity.from_dict(payload.get("identity"))
    revision = payload.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError("Predictor precompute desired revision is invalid.")
    return payload


def _desired_revision_for_advance(path: Path) -> int:
    """Read the monotonic revision, accepting the immediately previous artifact schema."""
    if not path.is_file():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != DESIRED_SCHEMA_VERSION:
        raise ValueError("Predictor precompute desired state is invalid.")
    revision = payload.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError("Predictor precompute desired revision is invalid.")
    try:
        ArtifactIdentity.from_dict(payload.get("identity"))
    except (OSError, ValueError):
        legacy_identity = payload.get("identity")
        if not (
            isinstance(legacy_identity, dict)
            and legacy_identity.get("kind") == "rainmapper_mushroom_predictor_precompute"
            and legacy_identity.get("schema_version")
            in {"1.0", "1.1", "1.2", "1.3", "1.4"}
        ):
            raise
    return revision


def advance_desired_state(
    path: Path,
    *,
    identity: ArtifactIdentity,
    worker_id: str,
    trigger_origin: str,
    force: bool = False,
) -> dict[str, Any]:
    """Atomically advance the monotonic desired generation."""
    revision = _desired_revision_for_advance(path) + 1
    payload = {
        "schema_version": DESIRED_SCHEMA_VERSION,
        "revision": revision,
        "artifact_id": identity.artifact_id,
        "identity": identity.as_dict(),
        "runtime_fingerprint": identity.runtime_fingerprint,
        "coverage_start": identity.coverage_start,
        "coverage_end": identity.coverage_end,
        "worker_id": str(worker_id),
        "trigger_origin": str(trigger_origin),
        "force": bool(force),
    }
    _atomic_json(path, payload)
    return payload


def assign_desired_worker(
    path: Path,
    *,
    desired_revision: int,
    worker_id: str,
) -> dict[str, Any]:
    """Bind an unassigned desire without changing its scientific revision."""
    current = load_desired_state(path)
    if current is None or current.get("revision") != desired_revision:
        raise ValueError("Predictor precompute desired state changed before assignment.")
    assigned = str(current.get("worker_id", "") or "")
    target = str(worker_id or "").strip()
    if not target:
        raise ValueError("Predictor precompute worker assignment is required.")
    if assigned and assigned != target:
        raise ValueError("Predictor precompute desire belongs to another worker.")
    if assigned == target:
        return current
    current["worker_id"] = target
    _atomic_json(path, current)
    return current


@dataclass(frozen=True)
class PublicationReceipt:
    receipt_id: str
    desired_revision: int
    artifact_id: str
    file_sha256: str
    size_bytes: int

    @classmethod
    def from_dict(cls, payload: object) -> "PublicationReceipt":
        if not isinstance(payload, dict) or payload.get("schema_version") != RECEIPT_SCHEMA_VERSION:
            raise ValueError("Predictor precompute publication receipt is invalid.")
        try:
            desired_revision = int(payload.get("desired_revision", 0))
            size_bytes = int(payload.get("size_bytes", -1))
        except (TypeError, ValueError) as exc:
            raise ValueError("Predictor precompute publication receipt is invalid.") from exc
        body = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "desired_revision": desired_revision,
            "artifact_id": str(payload.get("artifact_id", "")),
            "file_sha256": str(payload.get("file_sha256", "")),
            "size_bytes": size_bytes,
        }
        expected = "sha256:" + hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()
        if (
            desired_revision < 1
            or size_bytes < 1
            or payload.get("receipt_id") != expected
            or not body["artifact_id"].startswith("sha256:")
            or not body["file_sha256"].startswith("sha256:")
        ):
            raise ValueError("Predictor precompute publication receipt is invalid.")
        return cls(expected, desired_revision, body["artifact_id"], body["file_sha256"], size_bytes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "desired_revision": self.desired_revision,
            "artifact_id": self.artifact_id,
            "file_sha256": self.file_sha256,
            "size_bytes": self.size_bytes,
        }


def _receipt(manifest: ArtifactManifest, desired_revision: int) -> PublicationReceipt:
    body = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "desired_revision": desired_revision,
        "artifact_id": manifest.artifact_id,
        "file_sha256": manifest.file_sha256,
        "size_bytes": manifest.size_bytes,
    }
    return PublicationReceipt(
        "sha256:" + hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest(),
        desired_revision,
        manifest.artifact_id,
        manifest.file_sha256,
        manifest.size_bytes,
    )


def publish_received_artifact(
    source: BinaryIO,
    *,
    content_length: int,
    expected_sha256: str,
    identity: ArtifactIdentity,
    desired_state_path: Path,
    destination_path: Path,
    receipt_path: Path,
    desired_revision: int,
    max_bytes: int,
) -> PublicationReceipt:
    """Validate staged bytes and atomically publish only the current desire."""
    if max_bytes < 1 or content_length < 1 or content_length > max_bytes:
        raise ValueError("Predictor precompute artifact size is outside the accepted limit.")
    desired = load_desired_state(desired_state_path)
    if (
        desired is None
        or desired.get("revision") != desired_revision
        or desired.get("artifact_id") != identity.artifact_id
    ):
        raise ValueError("Predictor precompute upload is no longer desired.")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=destination_path.parent, prefix=f".{destination_path.name}.", suffix=".upload"
    )
    staged = Path(name)
    digest = hashlib.sha256()
    received = 0
    try:
        with os.fdopen(descriptor, "wb") as handle:
            while chunk := source.read(min(1024 * 1024, content_length - received)):
                received += len(chunk)
                if received > content_length or received > max_bytes:
                    raise ValueError("Predictor precompute artifact exceeds declared size.")
                digest.update(chunk)
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if received != content_length:
            raise ValueError("Predictor precompute artifact is incomplete.")
        actual_sha256 = "sha256:" + digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError("Predictor precompute artifact digest does not match.")
        manifest = validate_artifact(
            staged,
            expected_identity=identity,
            expected_file_sha256=expected_sha256,
            full=True,
        )
        desired = load_desired_state(desired_state_path)
        if (
            desired is None
            or desired.get("revision") != desired_revision
            or desired.get("artifact_id") != identity.artifact_id
        ):
            raise ValueError("Predictor precompute upload was superseded during validation.")
        os.replace(staged, destination_path)
        directory = os.open(destination_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        receipt = _receipt(manifest, desired_revision)
        _atomic_json(receipt_path, receipt.as_dict())
        return receipt
    finally:
        staged.unlink(missing_ok=True)


def activate_worker_copy(
    source_path: Path,
    *,
    destination_path: Path,
    receipt: PublicationReceipt,
    identity: ArtifactIdentity,
) -> ArtifactManifest:
    """Activate the worker copy only after HA returned a matching receipt."""
    receipt = PublicationReceipt.from_dict(receipt.as_dict())
    if receipt.artifact_id != identity.artifact_id:
        raise ValueError("HA publication receipt belongs to another artifact.")
    manifest = validate_artifact(
        source_path,
        expected_identity=identity,
        expected_file_sha256=receipt.file_sha256,
        full=True,
    )
    if manifest.size_bytes != receipt.size_bytes:
        raise ValueError("Worker artifact size does not match HA publication receipt.")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=destination_path.parent, prefix=f".{destination_path.name}.", suffix=".activate"
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        shutil.copyfile(source_path, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination_path)
        return manifest
    finally:
        temporary.unlink(missing_ok=True)
