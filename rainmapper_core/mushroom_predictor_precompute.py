"""Immutable SQLite contract for weekly Predictor precomputation.

This module is deliberately transport- and scheduler-neutral.  It stores the
canonical Predictor response without reproducing scientific rules in SQL, and
keeps explicit normalized coverage beside it so a partial artifact is always a
miss rather than a partially served response.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import queue
import sqlite3
import tempfile
import threading
import zlib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from rainmapper_core import mushroom_ml_multiversion_comparison
from rainmapper_core.mushroom_predictor_service import (
    PredictorContractError,
    SCHEMA_VERSION as PREDICTOR_SCHEMA_VERSION,
    deserialize_prediction,
    normalize_request,
    validate_response,
)


ARTIFACT_SCHEMA_VERSION = "1.5"
ARTIFACT_KIND = "rainmapper_mushroom_predictor_precompute"
SQLITE_USER_VERSION = 6
PRECOMPUTED_VIEWS = {"recommender", "week", "query"}
_EXPECTED_COUNT_KEYS = ("species", "areas", "days", "versions", "members")
_REQUIRED_TABLES = {
    "metadata",
    "species_context",
    "coverage",
    "base_predictions",
    "operational_members",
    "response_coverage",
    "response_payloads",
    "responses",
    "diagnostics",
}


class PrecomputeContractError(ValueError):
    """Raised when scientific identity or stored payloads are inconsistent."""


class PrecomputeArtifactError(OSError):
    """Raised when an artifact cannot be trusted or read."""


class UnsupportedPrecomputeSchema(PrecomputeArtifactError):
    """Raised for a well-formed artifact using an unknown schema."""


class PrecomputeIdentityMismatch(PrecomputeArtifactError):
    """Raised when an artifact belongs to another scientific runtime."""


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _compressed_json(payload: object) -> bytes:
    return zlib.compress(_canonical_json(payload).encode("utf-8"), level=1)


def _canonical_sha256(payload: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _iso_date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise PrecomputeContractError(f"{field} must be an ISO date.") from exc


def _required_text(value: object, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise PrecomputeContractError(f"{field} is required.")
    return normalized


@dataclass(frozen=True, order=True)
class RuntimeVersionIdentity:
    version_id: str
    generation_id: str
    profile_ids: tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        version_id: object,
        generation_id: object,
        profile_ids: Iterable[object],
    ) -> "RuntimeVersionIdentity":
        profiles = tuple(sorted({_required_text(value, "profile_id") for value in profile_ids}))
        if not profiles:
            raise PrecomputeContractError("At least one operational profile is required.")
        return cls(
            _required_text(version_id, "version_id"),
            _required_text(generation_id, "generation_id"),
            profiles,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "version_id": self.version_id,
            "generation_id": self.generation_id,
            "profile_ids": list(self.profile_ids),
        }


@dataclass(frozen=True)
class ArtifactIdentity:
    runtime_fingerprint: str
    issue_date: str
    coverage_start: str
    coverage_end: str
    trained_species_ids: tuple[str, ...]
    installed_versions: tuple[RuntimeVersionIdentity, ...]
    expected_counts: tuple[tuple[str, int], ...]
    predictor_contract_versions: tuple[str, ...] = (PREDICTOR_SCHEMA_VERSION,)
    schema_version: str = ARTIFACT_SCHEMA_VERSION
    kind: str = ARTIFACT_KIND

    @classmethod
    def create(
        cls,
        *,
        runtime_fingerprint: object,
        issue_date: object,
        trained_species_ids: Iterable[object],
        installed_versions: Iterable[RuntimeVersionIdentity],
        expected_counts: Mapping[str, object],
        predictor_contract_versions: Iterable[object] = (PREDICTOR_SCHEMA_VERSION,),
    ) -> "ArtifactIdentity":
        issue = _iso_date(issue_date, "issue_date")
        species = tuple(
            sorted({_required_text(value, "trained_species_id") for value in trained_species_ids})
        )
        if not species:
            raise PrecomputeContractError("At least one trained species is required.")
        versions = tuple(sorted(set(installed_versions)))
        if not versions:
            raise PrecomputeContractError("At least one installed version is required.")
        contracts = tuple(
            sorted({_required_text(value, "predictor_contract_version") for value in predictor_contract_versions})
        )
        if PREDICTOR_SCHEMA_VERSION not in contracts:
            raise PrecomputeContractError("The active Predictor contract must be represented.")
        fingerprint = _required_text(runtime_fingerprint, "runtime_fingerprint")
        if not fingerprint.startswith("sha256:") or len(fingerprint) != 71:
            raise PrecomputeContractError("Runtime fingerprint must be a complete SHA-256.")
        if set(expected_counts) != set(_EXPECTED_COUNT_KEYS):
            raise PrecomputeContractError("Expected counts must define species, areas, days, versions and members.")
        counts: list[tuple[str, int]] = []
        for key in _EXPECTED_COUNT_KEYS:
            value = expected_counts[key]
            if isinstance(value, bool):
                raise PrecomputeContractError(f"Expected {key} count is invalid.")
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                raise PrecomputeContractError(f"Expected {key} count is invalid.") from exc
            if number < 0:
                raise PrecomputeContractError(f"Expected {key} count is invalid.")
            counts.append((key, number))
        if dict(counts)["species"] != len(species):
            raise PrecomputeContractError("Expected species count does not match identity.")
        if dict(counts)["versions"] != len(versions):
            raise PrecomputeContractError("Expected versions count does not match identity.")
        return cls(
            runtime_fingerprint=fingerprint,
            issue_date=issue.isoformat(),
            coverage_start=issue.isoformat(),
            coverage_end=(issue + timedelta(days=6)).isoformat(),
            trained_species_ids=species,
            installed_versions=versions,
            expected_counts=tuple(counts),
            predictor_contract_versions=contracts,
        )

    @classmethod
    def from_dict(cls, payload: object) -> "ArtifactIdentity":
        if not isinstance(payload, dict):
            raise PrecomputeContractError("Artifact identity must be an object.")
        if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION or payload.get("kind") != ARTIFACT_KIND:
            raise UnsupportedPrecomputeSchema("Unsupported Predictor precompute schema.")
        raw_versions = payload.get("installed_versions")
        if not isinstance(raw_versions, list):
            raise PrecomputeContractError("Installed versions identity is invalid.")
        raw_counts = payload.get("expected_counts")
        if not isinstance(raw_counts, dict):
            raise PrecomputeContractError("Expected artifact counters are invalid.")
        versions = [
            RuntimeVersionIdentity.create(
                version_id=row.get("version_id"),
                generation_id=row.get("generation_id"),
                profile_ids=row.get("profile_ids", []),
            )
            for row in raw_versions
            if isinstance(row, dict)
        ]
        if len(versions) != len(raw_versions):
            raise PrecomputeContractError("Installed versions identity is invalid.")
        identity = cls.create(
            runtime_fingerprint=payload.get("runtime_fingerprint"),
            issue_date=payload.get("issue_date"),
            trained_species_ids=payload.get("trained_species_ids", []),
            installed_versions=versions,
            expected_counts=raw_counts,
            predictor_contract_versions=payload.get("predictor_contract_versions", []),
        )
        if payload.get("coverage_start") != identity.coverage_start or payload.get("coverage_end") != identity.coverage_end:
            raise PrecomputeContractError("Artifact coverage window is inconsistent.")
        return identity

    @property
    def artifact_id(self) -> str:
        return _canonical_sha256(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "predictor_contract_versions": list(self.predictor_contract_versions),
            "runtime_fingerprint": self.runtime_fingerprint,
            "issue_date": self.issue_date,
            "coverage_start": self.coverage_start,
            "coverage_end": self.coverage_end,
            "trained_species_ids": list(self.trained_species_ids),
            "installed_versions": [row.as_dict() for row in self.installed_versions],
            "expected_counts": dict(self.expected_counts),
        }


@dataclass(frozen=True, order=True)
class OperationalMemberKey:
    version_id: str
    temporal_contract_id: str
    profile_id: str
    estimator_id: str
    horizon_days: int

    @classmethod
    def create(
        cls,
        *,
        version_id: object,
        temporal_contract_id: object,
        profile_id: object,
        estimator_id: object,
        horizon_days: object,
    ) -> "OperationalMemberKey":
        try:
            horizon = int(horizon_days)
        except (TypeError, ValueError) as exc:
            raise PrecomputeContractError("Operational member horizon is invalid.") from exc
        if horizon not in range(1, 8):
            raise PrecomputeContractError("Operational member horizon is invalid.")
        return cls(
            _required_text(version_id, "version_id"),
            _required_text(temporal_contract_id, "temporal_contract_id"),
            _required_text(profile_id, "profile_id"),
            _required_text(estimator_id, "estimator_id"),
            horizon,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "version_id": self.version_id,
            "temporal_contract_id": self.temporal_contract_id,
            "profile_id": self.profile_id,
            "estimator_id": self.estimator_id,
            "horizon_days": self.horizon_days,
        }


@dataclass(frozen=True, order=True)
class CoverageCell:
    species_id: str
    area_id: str
    target_date: str
    has_base_prediction: bool
    member_keys: tuple[OperationalMemberKey, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        species_id: object,
        area_id: object,
        target_date: object,
        has_base_prediction: bool,
        member_keys: Iterable[OperationalMemberKey] = (),
    ) -> "CoverageCell":
        if not isinstance(has_base_prediction, bool):
            raise PrecomputeContractError("Coverage base-prediction flag must be boolean.")
        return cls(
            _required_text(species_id, "species_id"),
            _required_text(area_id, "area_id"),
            _iso_date(target_date, "target_date").isoformat(),
            has_base_prediction,
            tuple(sorted(set(member_keys))),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "species_id": self.species_id,
            "area_id": self.area_id,
            "target_date": self.target_date,
            "has_base_prediction": self.has_base_prediction,
            "member_keys": [row.as_dict() for row in self.member_keys],
        }


@dataclass(frozen=True)
class BasePredictionRow:
    species_id: str
    area_id: str
    target_date: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class OperationalMemberRow:
    species_id: str
    area_id: str
    target_date: str
    key: OperationalMemberKey
    payload: Mapping[str, object]


@dataclass(frozen=True)
class PrecomputedResponse:
    request: Mapping[str, object]
    response: Mapping[str, object]
    required_coverage: tuple[CoverageCell, ...]


@dataclass(frozen=True)
class ArtifactManifest:
    artifact_id: str
    file_sha256: str
    size_bytes: int
    table_counts: Mapping[str, int]


@dataclass(frozen=True)
class LookupResult:
    hit: bool
    response: dict[str, Any] | None
    reason: str | None
    artifact_id: str | None = None
    rows_read: int = 0


@dataclass(frozen=True)
class ResolvedPredictorResponse:
    response: dict[str, Any]
    source: str
    fallback_reason: str | None
    artifact_id: str | None


@dataclass(frozen=True)
class BatchBuildResult:
    manifest: ArtifactManifest
    request_count: int
    executed_request_count: int
    coverage_count: int
    base_prediction_count: int
    operational_member_count: int


def plan_artifact_identity(
    *,
    runtime_fingerprint: str,
    issue_date: date,
    trained_species_ids: Sequence[str],
    installed_versions: Sequence[RuntimeVersionIdentity],
    area_ids_by_species: Mapping[str, Sequence[str]],
    operational_selections_by_species: Mapping[str, Sequence[Mapping[str, object]]],
) -> ArtifactIdentity:
    """Build the immutable identity without executing a prediction in HA."""
    species = tuple(sorted({str(value) for value in trained_species_ids if str(value)}))
    area_count = sum(
        len({str(value) for value in area_ids_by_species.get(species_id, ()) if str(value)})
        for species_id in species
    )
    member_count = 0
    for species_id in species:
        area_total = len(
            {str(value) for value in area_ids_by_species.get(species_id, ()) if str(value)}
        )
        selections = operational_selections_by_species.get(species_id, ())
        for offset in range(7):
            target = issue_date + timedelta(days=offset)
            member_count += area_total * len(
                mushroom_ml_multiversion_comparison.operational_selections(
                    selections,
                    target_date=target,
                    issue_date=issue_date,
                )
            )
    return ArtifactIdentity.create(
        runtime_fingerprint=runtime_fingerprint,
        issue_date=issue_date,
        trained_species_ids=species,
        installed_versions=installed_versions,
        expected_counts={
            "species": len(species),
            "areas": area_count,
            "days": 7,
            "versions": len(installed_versions),
            "members": member_count,
        },
    )


def _request_key(request: Mapping[str, object]) -> str:
    return _canonical_sha256(request)


def _member_key_from_dict(payload: object) -> OperationalMemberKey:
    if not isinstance(payload, dict):
        raise PrecomputeContractError("Operational member key is invalid.")
    return OperationalMemberKey.create(
        version_id=payload.get("version_id"),
        temporal_contract_id=payload.get("temporal_contract_id"),
        profile_id=payload.get("profile_id"),
        estimator_id=payload.get("estimator_id"),
        horizon_days=payload.get("horizon_days"),
    )


def _coverage_from_dict(payload: object) -> CoverageCell:
    if not isinstance(payload, dict):
        raise PrecomputeContractError("Coverage cell is invalid.")
    raw_members = payload.get("member_keys", [])
    if not isinstance(raw_members, list):
        raise PrecomputeContractError("Coverage member keys are invalid.")
    return CoverageCell.create(
        species_id=payload.get("species_id"),
        area_id=payload.get("area_id"),
        target_date=payload.get("target_date"),
        has_base_prediction=payload.get("has_base_prediction") is True,
        member_keys=(_member_key_from_dict(row) for row in raw_members),
    )


def _validate_identity_coverage(identity: ArtifactIdentity, coverage: Sequence[CoverageCell], members: Sequence[OperationalMemberRow]) -> None:
    if len(set(coverage)) != len(coverage):
        raise PrecomputeContractError("Coverage contains duplicate cells.")
    species = {row.species_id for row in coverage}
    area_pairs = {(row.species_id, row.area_id) for row in coverage}
    days = {row.target_date for row in coverage}
    counts = dict(identity.expected_counts)
    observed = {
        "species": len(species),
        "areas": len(area_pairs),
        "days": len(days),
        "versions": len(identity.installed_versions),
        "members": len(members),
    }
    if observed != counts:
        raise PrecomputeContractError(f"Artifact coverage counters do not match identity: {observed} != {counts}.")
    if species != set(identity.trained_species_ids):
        raise PrecomputeContractError("Coverage species do not match identity.")
    expected_days = {
        (date.fromisoformat(identity.coverage_start) + timedelta(days=offset)).isoformat()
        for offset in range(7)
    }
    if days != expected_days:
        raise PrecomputeContractError("Coverage must represent the complete seven-day window.")


def _validate_rows(
    identity: ArtifactIdentity,
    coverage: Sequence[CoverageCell],
    base_predictions: Sequence[BasePredictionRow],
    members: Sequence[OperationalMemberRow],
    responses: Sequence[PrecomputedResponse],
) -> None:
    _validate_identity_coverage(identity, coverage, members)
    coverage_map = {(row.species_id, row.area_id, row.target_date): row for row in coverage}
    base_keys: set[tuple[str, str, str]] = set()
    for row in base_predictions:
        key = (row.species_id, row.area_id, _iso_date(row.target_date, "base target_date").isoformat())
        if key in base_keys or key not in coverage_map:
            raise PrecomputeContractError("Base prediction is duplicated or outside coverage.")
        prediction = deserialize_prediction(dict(row.payload))
        if (prediction.species_id, prediction.area_id, prediction.target_date.isoformat()) != key:
            raise PrecomputeContractError("Base prediction key does not match its canonical payload.")
        base_keys.add(key)
    member_keys: set[tuple[object, ...]] = set()
    for row in members:
        target_date = _iso_date(row.target_date, "member target_date").isoformat()
        cell_key = (row.species_id, row.area_id, target_date)
        key = cell_key + tuple(row.key.as_dict().values())
        if key in member_keys or cell_key not in coverage_map:
            raise PrecomputeContractError("Operational member is duplicated or outside coverage.")
        member_keys.add(key)
    for cell_key, cell in coverage_map.items():
        if cell.has_base_prediction != (cell_key in base_keys):
            raise PrecomputeContractError("Coverage base-prediction flag is inconsistent.")
        for member in cell.member_keys:
            if cell_key + tuple(member.as_dict().values()) not in member_keys:
                raise PrecomputeContractError("Coverage references a missing operational member.")
    response_keys: set[str] = set()
    for row in responses:
        normalized = normalize_request(dict(row.request))
        if normalized["view"] not in PRECOMPUTED_VIEWS:
            raise PrecomputeContractError("Predictor view is outside precompute scope.")
        response = validate_response(dict(row.response))
        if response.get("runtime_fingerprint") != identity.runtime_fingerprint:
            raise PrecomputeContractError("Response runtime fingerprint does not match artifact identity.")
        if normalize_request(response.get("request")) != normalized:
            raise PrecomputeContractError("Stored response does not echo its normalized request.")
        key = _request_key(normalized)
        if key in response_keys:
            raise PrecomputeContractError("Precomputed response request is duplicated.")
        response_keys.add(key)
        required = tuple(sorted(set(row.required_coverage)))
        if not required:
            raise PrecomputeContractError("Precomputed response must declare required coverage.")
        if any((cell.species_id, cell.area_id, cell.target_date) not in coverage_map for cell in required):
            raise PrecomputeContractError("Precomputed response requires unavailable coverage.")


_SCHEMA_SQL = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE species_context (
    species_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE coverage (
    species_id TEXT NOT NULL,
    area_id TEXT NOT NULL,
    target_date TEXT NOT NULL,
    has_base_prediction INTEGER NOT NULL CHECK (has_base_prediction IN (0, 1)),
    member_keys_json TEXT NOT NULL,
    PRIMARY KEY (species_id, area_id, target_date)
) WITHOUT ROWID;
CREATE INDEX coverage_by_date ON coverage (target_date, species_id, area_id);
CREATE TABLE base_predictions (
    species_id TEXT NOT NULL,
    area_id TEXT NOT NULL,
    target_date TEXT NOT NULL,
    payload_json BLOB NOT NULL,
    PRIMARY KEY (species_id, area_id, target_date),
    FOREIGN KEY (species_id, area_id, target_date)
        REFERENCES coverage (species_id, area_id, target_date)
) WITHOUT ROWID;
CREATE TABLE operational_members (
    species_id TEXT NOT NULL,
    area_id TEXT NOT NULL,
    target_date TEXT NOT NULL,
    version_id TEXT NOT NULL,
    temporal_contract_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    estimator_id TEXT NOT NULL,
    horizon_days INTEGER NOT NULL,
    payload_json BLOB NOT NULL,
    PRIMARY KEY (
        species_id, area_id, target_date, version_id, temporal_contract_id,
        profile_id, estimator_id, horizon_days
    ),
    FOREIGN KEY (species_id, area_id, target_date)
        REFERENCES coverage (species_id, area_id, target_date)
) WITHOUT ROWID;
CREATE INDEX operational_members_by_request ON operational_members (
    species_id, area_id, target_date, version_id
);
CREATE TABLE response_payloads (
    payload_key TEXT PRIMARY KEY,
    payload_json BLOB NOT NULL
) WITHOUT ROWID;
CREATE TABLE response_coverage (
    coverage_key TEXT PRIMARY KEY,
    payload_json BLOB NOT NULL
) WITHOUT ROWID;
CREATE TABLE responses (
    request_key TEXT PRIMARY KEY,
    request_json TEXT NOT NULL,
    coverage_key TEXT NOT NULL,
    payload_key TEXT NOT NULL,
    FOREIGN KEY (coverage_key) REFERENCES response_coverage (coverage_key),
    FOREIGN KEY (payload_key) REFERENCES response_payloads (payload_key)
) WITHOUT ROWID;
CREATE TABLE diagnostics (key TEXT PRIMARY KEY, payload_json TEXT NOT NULL) WITHOUT ROWID;
"""


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in sorted(_REQUIRED_TABLES - {"metadata"})
    }


def _normalized_species_context(
    identity: ArtifactIdentity,
    supplied: Mapping[str, Mapping[str, object]] | None,
    base_predictions: Sequence[BasePredictionRow] = (),
) -> dict[str, dict[str, object]]:
    inferred_phases: dict[tuple[str, str], str] = {}
    for row in base_predictions:
        phase = str(row.payload.get("season_phase") or "").strip()
        if phase:
            inferred_phases[(row.species_id, row.target_date)] = phase
    days = [
        (date.fromisoformat(identity.coverage_start) + timedelta(days=offset)).isoformat()
        for offset in range(7)
    ]
    normalized: dict[str, dict[str, object]] = {}
    for species_id in identity.trained_species_ids:
        raw = dict((supplied or {}).get(species_id, {}))
        phenology = raw.get("phenology") or {}
        raw_phases = raw.get("season_phase_by_date") or {}
        if not isinstance(phenology, Mapping) or not isinstance(raw_phases, Mapping):
            raise PrecomputeContractError("Predictor species context is invalid.")
        phases = {
            target: str(
                raw_phases.get(target)
                or inferred_phases.get((species_id, target))
                or "unknown"
            )
            for target in days
        }
        normalized[species_id] = {
            "phenology": dict(phenology),
            "season_phase_by_date": phases,
        }
    return normalized


def _validate_species_context(
    connection: sqlite3.Connection, identity: ArtifactIdentity
) -> None:
    rows = connection.execute(
        "SELECT species_id, payload_json FROM species_context"
    ).fetchall()
    if {str(row["species_id"]) for row in rows} != set(identity.trained_species_ids):
        raise PrecomputeArtifactError("Predictor species context coverage is invalid.")
    expected_days = {
        (date.fromisoformat(identity.coverage_start) + timedelta(days=offset)).isoformat()
        for offset in range(7)
    }
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
            phenology = payload.get("phenology")
            phases = payload.get("season_phase_by_date")
        except (json.JSONDecodeError, TypeError, AttributeError) as exc:
            raise PrecomputeArtifactError("Predictor species context is corrupt.") from exc
        if (
            not isinstance(phenology, dict)
            or not isinstance(phases, dict)
            or set(phases) != expected_days
            or any(not str(value) for value in phases.values())
        ):
            raise PrecomputeArtifactError("Predictor species context is invalid.")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_artifact(
    path: Path,
    *,
    identity: ArtifactIdentity,
    coverage: Iterable[CoverageCell],
    base_predictions: Iterable[BasePredictionRow],
    operational_members: Iterable[OperationalMemberRow],
    responses: Iterable[PrecomputedResponse],
    species_context: Mapping[str, Mapping[str, object]] | None = None,
    diagnostics: Mapping[str, object] | None = None,
) -> ArtifactManifest:
    """Build, validate and atomically replace one immutable SQLite artifact."""
    target = Path(path)
    coverage_rows = tuple(coverage)
    prediction_rows = tuple(base_predictions)
    member_rows = tuple(operational_members)
    context_rows = _normalized_species_context(
        identity, species_context, prediction_rows
    )
    _validate_rows(identity, coverage_rows, prediction_rows, member_rows, ())
    coverage_map = {
        (row.species_id, row.area_id, row.target_date): row
        for row in coverage_rows
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA user_version={SQLITE_USER_VERSION}")
            connection.executescript(_SCHEMA_SQL)
            with connection:
                for species_id, payload in sorted(context_rows.items()):
                    connection.execute(
                        "INSERT INTO species_context VALUES (?, ?)",
                        (species_id, _canonical_json(payload)),
                    )
                for row in coverage_rows:
                    connection.execute(
                        "INSERT INTO coverage VALUES (?, ?, ?, ?, ?)",
                        (
                            row.species_id,
                            row.area_id,
                            row.target_date,
                            int(row.has_base_prediction),
                            _canonical_json([member.as_dict() for member in row.member_keys]),
                        ),
                    )
                for row in prediction_rows:
                    connection.execute(
                        "INSERT INTO base_predictions VALUES (?, ?, ?, ?)",
                        (
                            row.species_id,
                            row.area_id,
                            row.target_date,
                            _compressed_json(dict(row.payload)),
                        ),
                    )
                for row in member_rows:
                    connection.execute(
                        "INSERT INTO operational_members VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            row.species_id,
                            row.area_id,
                            row.target_date,
                            row.key.version_id,
                            row.key.temporal_contract_id,
                            row.key.profile_id,
                            row.key.estimator_id,
                            row.key.horizon_days,
                            _compressed_json(dict(row.payload)),
                        ),
                    )
                response_keys: set[str] = set()
                coverage_keys: set[str] = set()
                payload_keys: set[str] = set()
                for row in responses:
                    normalized = normalize_request(dict(row.request))
                    response = validate_response(dict(row.response))
                    if response.get("runtime_fingerprint") != identity.runtime_fingerprint:
                        raise PrecomputeContractError(
                            "Response runtime fingerprint does not match artifact identity."
                        )
                    response_request = normalize_request(response.get("request"))
                    if response_request != normalized and (
                        _weekly_execution_key(response_request)
                        != _weekly_execution_key(normalized)
                        or _weekly_execution_key(normalized)[0] == "exact"
                    ):
                        raise PrecomputeContractError(
                            "Stored response cannot be retargeted to its normalized request."
                        )
                    request_key = _request_key(normalized)
                    if request_key in response_keys:
                        raise PrecomputeContractError(
                            "Precomputed response request is duplicated."
                        )
                    response_keys.add(request_key)
                    required = tuple(sorted(set(row.required_coverage)))
                    if not required:
                        raise PrecomputeContractError(
                            "Precomputed response must declare required coverage."
                        )
                    if any(
                        (cell.species_id, cell.area_id, cell.target_date)
                        not in coverage_map
                        for cell in required
                    ):
                        raise PrecomputeContractError(
                            "Precomputed response requires unavailable coverage."
                        )
                    coverage_payload = [cell.as_dict() for cell in required]
                    coverage_key = _canonical_sha256(coverage_payload)
                    if coverage_key not in coverage_keys:
                        connection.execute(
                            "INSERT INTO response_coverage VALUES (?, ?)",
                            (coverage_key, _compressed_json(coverage_payload)),
                        )
                        coverage_keys.add(coverage_key)
                    payload_key = _canonical_sha256(response)
                    if payload_key not in payload_keys:
                        connection.execute(
                            "INSERT INTO response_payloads VALUES (?, ?)",
                            (payload_key, _compressed_json(response)),
                        )
                        payload_keys.add(payload_key)
                    connection.execute(
                        "INSERT INTO responses VALUES (?, ?, ?, ?)",
                        (
                            request_key,
                            _canonical_json(normalized),
                            coverage_key,
                            payload_key,
                        ),
                    )
                for key, payload in sorted((diagnostics or {}).items()):
                    connection.execute(
                        "INSERT INTO diagnostics VALUES (?, ?)",
                        (_required_text(key, "diagnostic key"), _canonical_json(payload)),
                    )
                counts = _table_counts(connection)
                metadata = {
                    "artifact_id": identity.artifact_id,
                    "identity": _canonical_json(identity.as_dict()),
                    "publication_state": "complete",
                    "table_counts": _canonical_json(counts),
                }
                connection.executemany(
                    "INSERT INTO metadata VALUES (?, ?)", sorted(metadata.items())
                )
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
            if quick_check is None or quick_check[0] != "ok":
                raise PrecomputeArtifactError("SQLite quick_check failed during construction.")
        finally:
            connection.close()
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        validated = validate_artifact(temporary, expected_identity=identity, full=True)
        digest = _sha256_file(temporary)
        size = temporary.stat().st_size
        os.replace(temporary, target)
        _fsync_directory(target.parent)
        return ArtifactManifest(identity.artifact_id, digest, size, validated.table_counts)
    except sqlite3.DatabaseError as exc:
        raise PrecomputeArtifactError(f"Cannot build Predictor precompute SQLite: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


class _AsyncBatchArtifactWriter:
    """Single-writer producer/consumer for a batch artifact under construction."""

    _ABORT = object()
    _FINISH = object()

    def __init__(
        self,
        path: Path,
        *,
        identity: ArtifactIdentity,
        all_cell_keys: set[tuple[str, str, str]],
        species_context: Mapping[str, Mapping[str, object]],
    ) -> None:
        self.target = Path(path)
        self.identity = identity
        self.all_cell_keys = set(all_cell_keys)
        self.species_context = _normalized_species_context(
            identity, species_context
        )
        self.target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.target.parent,
            prefix=f".{self.target.name}.",
            suffix=".tmp",
        )
        os.close(descriptor)
        self.temporary = Path(temporary_name)
        self.items: queue.Queue[object] = queue.Queue(maxsize=3)
        self.ready = threading.Event()
        self.error: BaseException | None = None
        self.manifest: ArtifactManifest | None = None
        self.request_count = 0
        self.executed_request_count = 0
        self.base_prediction_count = 0
        self.operational_member_count = 0
        self.thread = threading.Thread(
            target=self._run,
            name="mushroom-precompute-sqlite-writer",
            daemon=True,
        )
        self.thread.start()
        self.ready.wait()
        self._raise_if_failed()

    def _raise_if_failed(self) -> None:
        if self.error is not None:
            raise self.error

    def _put(self, item: object) -> None:
        while True:
            self._raise_if_failed()
            try:
                self.items.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    def submit(
        self,
        response: Mapping[str, object],
        variants: Sequence[
            tuple[dict[str, object], tuple[tuple[str, str, str], ...]]
        ],
    ) -> None:
        self._put((dict(response), tuple(variants)))

    def finish(self, diagnostics: Mapping[str, object]) -> ArtifactManifest:
        self._put((self._FINISH, dict(diagnostics)))
        self.thread.join()
        self._raise_if_failed()
        if self.manifest is None:
            raise PrecomputeArtifactError("Async SQLite writer produced no artifact.")
        return self.manifest

    def abort(self) -> None:
        if self.thread.is_alive():
            try:
                self._put(self._ABORT)
            except BaseException:
                pass
            self.thread.join()
        self.temporary.unlink(missing_ok=True)

    def _run(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.temporary)
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA user_version={SQLITE_USER_VERSION}")
            connection.executescript(_SCHEMA_SQL)
            connection.execute("BEGIN")
            for species_id, payload in sorted(self.species_context.items()):
                connection.execute(
                    "INSERT INTO species_context VALUES (?, ?)",
                    (species_id, _canonical_json(payload)),
                )
            for species_id, area_id, target_date in sorted(self.all_cell_keys):
                connection.execute(
                    "INSERT INTO coverage VALUES (?, ?, ?, 0, '[]')",
                    (species_id, area_id, target_date),
                )
            self.ready.set()

            base_hashes: dict[tuple[str, str, str], str] = {}
            member_hashes: dict[tuple[object, ...], str] = {}
            members_by_cell: dict[
                tuple[str, str, str], set[OperationalMemberKey]
            ] = {}
            response_payload_keys: set[str] = set()
            pending_responses: list[
                tuple[
                    dict[str, object],
                    tuple[tuple[str, str, str], ...],
                    str,
                ]
            ] = []
            diagnostics: dict[str, object] = {}

            while True:
                item = self.items.get()
                if item is self._ABORT:
                    raise InterruptedError("Async Predictor artifact writer was aborted.")
                if (
                    isinstance(item, tuple)
                    and len(item) == 2
                    and item[0] is self._FINISH
                ):
                    diagnostics = dict(item[1])
                    break
                response, variants = item  # type: ignore[misc]
                checked_response = validate_response(response)
                if checked_response.get("runtime_fingerprint") != self.identity.runtime_fingerprint:
                    raise PrecomputeContractError(
                        "Batch response runtime does not match artifact identity."
                    )
                response_request = normalize_request(checked_response.get("request"))
                payload_key = _canonical_sha256(checked_response)
                if payload_key not in response_payload_keys:
                    connection.execute(
                        "INSERT INTO response_payloads VALUES (?, ?)",
                        (payload_key, _compressed_json(checked_response)),
                    )
                    response_payload_keys.add(payload_key)

                species_payloads = checked_response.get("data", {}).get("species", {})
                if isinstance(species_payloads, Mapping):
                    for species_id, raw_species in species_payloads.items():
                        if not isinstance(raw_species, Mapping):
                            continue
                        prediction_groups = raw_species.get("predictions", {})
                        if isinstance(prediction_groups, Mapping):
                            for area_id, raw_dates in prediction_groups.items():
                                if not isinstance(raw_dates, Mapping):
                                    continue
                                for target_date, payload in raw_dates.items():
                                    if not isinstance(payload, Mapping):
                                        continue
                                    self._insert_base_prediction(
                                        connection,
                                        base_hashes,
                                        str(species_id),
                                        str(area_id),
                                        str(target_date),
                                        payload,
                                    )
                        rankings = raw_species.get("rankings", {})
                        if isinstance(rankings, Mapping):
                            for target_date, raw_rows in rankings.items():
                                if not isinstance(raw_rows, list):
                                    continue
                                for payload in raw_rows:
                                    if not isinstance(payload, Mapping):
                                        continue
                                    self._insert_base_prediction(
                                        connection,
                                        base_hashes,
                                        str(species_id),
                                        str(payload.get("area_id", "")),
                                        str(target_date),
                                        payload,
                                    )
                        comparisons = raw_species.get("multiversion_comparisons", {})
                        if not isinstance(comparisons, Mapping):
                            continue
                        request_area = str(
                            checked_response.get("request", {}).get("area_id", "")
                        )
                        for target_date, raw_comparison in comparisons.items():
                            if not isinstance(raw_comparison, Mapping):
                                continue
                            raw_members = raw_comparison.get("members", [])
                            if not isinstance(raw_members, list):
                                continue
                            for payload in raw_members:
                                if not isinstance(payload, Mapping):
                                    continue
                                member_key = _member_key_from_payload(payload)
                                if member_key is None:
                                    continue
                                cell_key = (
                                    str(species_id),
                                    request_area,
                                    str(target_date),
                                )
                                full_key = cell_key + tuple(
                                    member_key.as_dict().values()
                                )
                                payload_hash = _canonical_sha256(payload)
                                previous_hash = member_hashes.get(full_key)
                                if previous_hash is not None:
                                    if previous_hash != payload_hash:
                                        raise PrecomputeContractError(
                                            "Operational member payload changed within one batch."
                                        )
                                    continue
                                if cell_key not in self.all_cell_keys:
                                    raise PrecomputeContractError(
                                        "Operational member is outside planned coverage."
                                    )
                                connection.execute(
                                    "INSERT INTO operational_members VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    (
                                        *cell_key,
                                        member_key.version_id,
                                        member_key.temporal_contract_id,
                                        member_key.profile_id,
                                        member_key.estimator_id,
                                        member_key.horizon_days,
                                        _compressed_json(payload),
                                    ),
                                )
                                member_hashes[full_key] = payload_hash
                                members_by_cell.setdefault(cell_key, set()).add(member_key)

                for variant_request, required_keys in variants:
                    normalized = normalize_request(variant_request)
                    if response_request != normalized and (
                        _weekly_execution_key(response_request)
                        != _weekly_execution_key(normalized)
                        or _weekly_execution_key(normalized)[0] == "exact"
                    ):
                        raise PrecomputeContractError(
                            "Stored response cannot be retargeted to its normalized request."
                        )
                    pending_responses.append(
                        (normalized, tuple(required_keys), payload_key)
                    )
                self.executed_request_count += 1

            coverage_rows = tuple(
                CoverageCell.create(
                    species_id=species_id,
                    area_id=area_id,
                    target_date=target_date,
                    has_base_prediction=(species_id, area_id, target_date)
                    in base_hashes,
                    member_keys=members_by_cell.get(
                        (species_id, area_id, target_date), set()
                    ),
                )
                for species_id, area_id, target_date in sorted(self.all_cell_keys)
            )
            lightweight_members = tuple(
                OperationalMemberRow(
                    str(full_key[0]),
                    str(full_key[1]),
                    str(full_key[2]),
                    OperationalMemberKey.create(
                        version_id=full_key[3],
                        temporal_contract_id=full_key[4],
                        profile_id=full_key[5],
                        estimator_id=full_key[6],
                        horizon_days=full_key[7],
                    ),
                    {},
                )
                for full_key in member_hashes
            )
            _validate_identity_coverage(
                self.identity, coverage_rows, lightweight_members
            )
            coverage_map = {
                (row.species_id, row.area_id, row.target_date): row
                for row in coverage_rows
            }
            for row in coverage_rows:
                connection.execute(
                    """UPDATE coverage
                          SET has_base_prediction=?, member_keys_json=?
                        WHERE species_id=? AND area_id=? AND target_date=?""",
                    (
                        int(row.has_base_prediction),
                        _canonical_json(
                            [member.as_dict() for member in row.member_keys]
                        ),
                        row.species_id,
                        row.area_id,
                        row.target_date,
                    ),
                )

            request_keys: set[str] = set()
            coverage_keys: set[str] = set()
            for normalized, required_keys, payload_key in pending_responses:
                request_key = _request_key(normalized)
                if request_key in request_keys:
                    raise PrecomputeContractError(
                        "Precomputed response request is duplicated."
                    )
                request_keys.add(request_key)
                required = tuple(
                    coverage_map[key] for key in required_keys if key in coverage_map
                )
                if len(required) != len(required_keys) or not required:
                    raise PrecomputeContractError(
                        "Precomputed response requires unavailable coverage."
                    )
                coverage_payload = [cell.as_dict() for cell in required]
                coverage_key = _canonical_sha256(coverage_payload)
                if coverage_key not in coverage_keys:
                    connection.execute(
                        "INSERT INTO response_coverage VALUES (?, ?)",
                        (coverage_key, _compressed_json(coverage_payload)),
                    )
                    coverage_keys.add(coverage_key)
                connection.execute(
                    "INSERT INTO responses VALUES (?, ?, ?, ?)",
                    (
                        request_key,
                        _canonical_json(normalized),
                        coverage_key,
                        payload_key,
                    ),
                )

            for key, payload in sorted(diagnostics.items()):
                connection.execute(
                    "INSERT INTO diagnostics VALUES (?, ?)",
                    (_required_text(key, "diagnostic key"), _canonical_json(payload)),
                )
            counts = _table_counts(connection)
            metadata = {
                "artifact_id": self.identity.artifact_id,
                "identity": _canonical_json(self.identity.as_dict()),
                "publication_state": "complete",
                "table_counts": _canonical_json(counts),
            }
            connection.executemany(
                "INSERT INTO metadata VALUES (?, ?)", sorted(metadata.items())
            )
            connection.commit()
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
            if quick_check is None or quick_check[0] != "ok":
                raise PrecomputeArtifactError(
                    "SQLite quick_check failed during async construction."
                )
            connection.close()
            connection = None
            with self.temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            validated = validate_artifact(
                self.temporary, expected_identity=self.identity, full=True
            )
            digest = _sha256_file(self.temporary)
            size = self.temporary.stat().st_size
            os.replace(self.temporary, self.target)
            _fsync_directory(self.target.parent)
            self.manifest = ArtifactManifest(
                self.identity.artifact_id,
                digest,
                size,
                validated.table_counts,
            )
            self.request_count = len(pending_responses)
            self.base_prediction_count = len(base_hashes)
            self.operational_member_count = len(member_hashes)
        except BaseException as exc:
            self.error = exc
            self.ready.set()
        finally:
            if connection is not None:
                connection.close()
            self.temporary.unlink(missing_ok=True)

    def _insert_base_prediction(
        self,
        connection: sqlite3.Connection,
        hashes: dict[tuple[str, str, str], str],
        species_id: str,
        area_id: str,
        target_date: str,
        payload: Mapping[str, object],
    ) -> None:
        key = (species_id, area_id, target_date)
        if key not in self.all_cell_keys:
            raise PrecomputeContractError(
                "Base prediction is outside planned coverage."
            )
        prediction = deserialize_prediction(dict(payload))
        if (
            prediction.species_id,
            prediction.area_id,
            prediction.target_date.isoformat(),
        ) != key:
            raise PrecomputeContractError(
                "Base prediction key does not match its canonical payload."
            )
        payload_hash = _canonical_sha256(payload)
        previous_hash = hashes.get(key)
        if previous_hash is not None:
            if previous_hash != payload_hash:
                raise PrecomputeContractError(
                    "Base prediction payload changed within one batch."
                )
            return
        connection.execute(
            "INSERT INTO base_predictions VALUES (?, ?, ?, ?)",
            (*key, _compressed_json(payload)),
        )
        hashes[key] = payload_hash


def _open_readonly(path: Path) -> sqlite3.Connection:
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    uri = candidate.resolve().as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _load_metadata(connection: sqlite3.Connection) -> dict[str, str]:
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if not _REQUIRED_TABLES.issubset(tables):
        raise UnsupportedPrecomputeSchema("Predictor precompute SQLite schema is incomplete.")
    if int(connection.execute("PRAGMA user_version").fetchone()[0]) != SQLITE_USER_VERSION:
        raise UnsupportedPrecomputeSchema("Predictor precompute SQLite user_version is unsupported.")
    return {str(row["key"]): str(row["value"]) for row in connection.execute("SELECT key, value FROM metadata")}


def _validated_metadata(
    connection: sqlite3.Connection,
    *,
    expected_identity: ArtifactIdentity | None,
) -> tuple[ArtifactIdentity, dict[str, int]]:
    metadata = _load_metadata(connection)
    if metadata.get("publication_state") != "complete":
        raise PrecomputeArtifactError("Predictor precompute artifact is not published.")
    try:
        identity = ArtifactIdentity.from_dict(json.loads(metadata["identity"]))
        stored_counts = json.loads(metadata["table_counts"])
    except (KeyError, json.JSONDecodeError, TypeError, PrecomputeContractError) as exc:
        raise PrecomputeArtifactError("Predictor precompute metadata is invalid.") from exc
    if metadata.get("artifact_id") != identity.artifact_id:
        raise PrecomputeArtifactError("Predictor precompute artifact identity is invalid.")
    if expected_identity is not None and identity.artifact_id != expected_identity.artifact_id:
        raise PrecomputeIdentityMismatch(
            "Predictor precompute identity does not match the active runtime."
        )
    if not isinstance(stored_counts, dict) or any(
        key not in stored_counts
        or not isinstance(stored_counts[key], int)
        or isinstance(stored_counts[key], bool)
        for key in _REQUIRED_TABLES - {"metadata"}
    ):
        raise PrecomputeArtifactError("Predictor precompute table counters are invalid.")
    return identity, {str(key): int(value) for key, value in stored_counts.items()}


def validate_artifact(
    path: Path,
    *,
    expected_identity: ArtifactIdentity | None = None,
    expected_file_sha256: str | None = None,
    full: bool = True,
) -> ArtifactManifest:
    """Validate schema, identity, optional digest and construction-time coverage."""
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    try:
        connection = _open_readonly(candidate)
        try:
            identity, stored_counts = _validated_metadata(
                connection, expected_identity=expected_identity
            )
            if full:
                quick_check = connection.execute("PRAGMA quick_check").fetchone()
                if quick_check is None or quick_check[0] != "ok":
                    raise PrecomputeArtifactError("Predictor precompute SQLite quick_check failed.")
                actual_counts = _table_counts(connection)
                if actual_counts != stored_counts:
                    raise PrecomputeArtifactError("Predictor precompute table counters do not match.")
                _validate_species_context(connection, identity)
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        raise PrecomputeArtifactError(f"Predictor precompute SQLite is corrupt: {exc}") from exc
    digest = _sha256_file(candidate)
    if expected_file_sha256 is not None and digest != expected_file_sha256:
        raise PrecomputeArtifactError("Predictor precompute SHA-256 does not match.")
    return ArtifactManifest(identity.artifact_id, digest, candidate.stat().st_size, stored_counts)


class ArtifactReader:
    """Short-lived read-only access to one already published artifact."""

    def __init__(self, path: Path, *, expected_identity: ArtifactIdentity) -> None:
        self.path = Path(path)
        self.connection = _open_readonly(self.path)
        try:
            self.identity, self.table_counts = _validated_metadata(
                self.connection, expected_identity=expected_identity
            )
            _validate_species_context(self.connection, self.identity)
        except Exception:
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ArtifactReader":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _multiversion_template_row(
        self, normalized: Mapping[str, object]
    ) -> sqlite3.Row | None:
        fields = (
            "view",
            "species_id",
            "area_id",
            "target_date",
            "filter_mode",
            "issue_date",
            "trained_species_ids",
        )
        rows = self.connection.execute(
            """SELECT responses.request_json,
                      response_coverage.payload_json AS required_coverage_json,
                      response_payloads.payload_json
                 FROM responses
                 JOIN response_coverage USING (coverage_key)
                 JOIN response_payloads USING (payload_key)"""
        )
        for row in rows:
            candidate = json.loads(row["request_json"])
            if (
                candidate.get("compare_models") is True
                and candidate.get("multiversion_selection")
                and all(candidate.get(field) == normalized.get(field) for field in fields)
            ):
                return row
        return None

    def _compose_multiversion_subset(
        self, normalized: dict[str, Any]
    ) -> LookupResult | None:
        if not (
            normalized["view"] == "query"
            and normalized["area_id"]
            and normalized["filter_mode"] == ""
            and normalized["compare_models"]
            and normalized["multiversion_selection"]
        ):
            return None
        template_row = self._multiversion_template_row(normalized)
        if template_row is None:
            return LookupResult(
                False,
                None,
                "selection_not_precomputed",
                self.identity.artifact_id,
            )
        rows_read = 1
        try:
            template_request = normalize_request(
                json.loads(template_row["request_json"])
            )
            response = validate_response(
                json.loads(
                    zlib.decompress(template_row["payload_json"]).decode("utf-8")
                )
            )
            if normalize_request(response.get("request")) != template_request:
                response = _retarget_weekly_response(response, template_request)
            species_payload = (
                response.get("data", {})
                .get("species", {})
                .get(normalized["species_id"], {})
            )
            if not isinstance(species_payload, dict):
                return LookupResult(
                    False, None, "response_invalid", self.identity.artifact_id, rows_read
                )
            comparisons = species_payload.get("multiversion_comparisons", {})
            if not isinstance(comparisons, Mapping):
                return LookupResult(
                    False, None, "response_invalid", self.identity.artifact_id, rows_read
                )
            context_row = self.connection.execute(
                "SELECT payload_json FROM species_context WHERE species_id=?",
                (normalized["species_id"],),
            ).fetchone()
            rows_read += 1
            if context_row is None:
                return LookupResult(
                    False,
                    None,
                    "composition_context_missing",
                    self.identity.artifact_id,
                    rows_read,
                )
            context = json.loads(context_row["payload_json"])
            phenology = context.get("phenology", {})
            phases = context.get("season_phase_by_date", {})
            if not isinstance(phenology, dict) or not isinstance(phases, dict):
                return LookupResult(
                    False, None, "artifact_corrupt", self.identity.artifact_id, rows_read
                )
            artifact_issue_date = date.fromisoformat(self.identity.issue_date)
            composed: dict[str, dict[str, object]] = {}
            for target_text in comparisons:
                target = date.fromisoformat(str(target_text))
                coverage_row = self.connection.execute(
                    """SELECT has_base_prediction, member_keys_json
                         FROM coverage
                        WHERE species_id=? AND area_id=? AND target_date=?""",
                    (
                        normalized["species_id"],
                        normalized["area_id"],
                        target.isoformat(),
                    ),
                ).fetchone()
                rows_read += 1
                if coverage_row is None or not bool(
                    coverage_row["has_base_prediction"]
                ):
                    return LookupResult(
                        False, None, "coverage_partial", self.identity.artifact_id, rows_read
                    )
                base_exists = self.connection.execute(
                    """SELECT 1 FROM base_predictions
                        WHERE species_id=? AND area_id=? AND target_date=?""",
                    (
                        normalized["species_id"],
                        normalized["area_id"],
                        target.isoformat(),
                    ),
                ).fetchone()
                rows_read += 1
                if base_exists is None:
                    return LookupResult(
                        False, None, "coverage_partial", self.identity.artifact_id, rows_read
                    )
                represented_members = {
                    _member_key_from_dict(value)
                    for value in json.loads(coverage_row["member_keys_json"])
                }
                selections = (
                    mushroom_ml_multiversion_comparison.retarget_operational_selections(
                        normalized["multiversion_selection"],
                        target_date=target,
                        issue_date=min(artifact_issue_date, target),
                    )
                )
                if not selections:
                    return LookupResult(
                        False,
                        None,
                        "selection_not_precomputed",
                        self.identity.artifact_id,
                        rows_read,
                    )
                members: list[dict[str, object]] = []
                for selection in selections:
                    selection_key = _member_key_from_dict(selection)
                    if selection_key not in represented_members:
                        return LookupResult(
                            False,
                            None,
                            "selection_not_precomputed",
                            self.identity.artifact_id,
                            rows_read,
                        )
                    member_row = self.connection.execute(
                        """SELECT payload_json FROM operational_members
                             WHERE species_id=? AND area_id=? AND target_date=?
                               AND version_id=? AND temporal_contract_id=?
                               AND profile_id=? AND estimator_id=? AND horizon_days=?""",
                        (
                            normalized["species_id"],
                            normalized["area_id"],
                            target.isoformat(),
                            selection["version_id"],
                            selection["temporal_contract_id"],
                            selection["profile_id"],
                            selection["estimator_id"],
                            selection["horizon_days"],
                        ),
                    ).fetchone()
                    rows_read += 1
                    if member_row is None:
                        return LookupResult(
                            False,
                            None,
                            "coverage_partial",
                            self.identity.artifact_id,
                            rows_read,
                        )
                    member = json.loads(
                        zlib.decompress(member_row["payload_json"]).decode("utf-8")
                    )
                    if not isinstance(member, dict):
                        return LookupResult(
                            False, None, "artifact_corrupt", self.identity.artifact_id, rows_read
                        )
                    members.append(member)
                season_phase = str(phases.get(target.isoformat()) or "")
                if not season_phase:
                    return LookupResult(
                        False, None, "artifact_corrupt", self.identity.artifact_id, rows_read
                    )
                batch_ids = {
                    str((member.get("model_ref") or {}).get("version_id") or ""):
                    str(
                        ((member.get("prediction") or {}).get("artifact_ref") or {}).get(
                            "batch_id"
                        )
                        or ""
                    )
                    for member in members
                }
                composed[target.isoformat()] = {
                    "available": True,
                    "batch_ids": batch_ids,
                    "area_id": normalized["area_id"],
                    "target_date": target.isoformat(),
                    "members": members,
                    "operational_comparison": mushroom_ml_multiversion_comparison.build_selected_operational_comparison(
                        members,
                        season_phase=season_phase,
                        phenology=phenology,
                    ),
                    "consensus_computed": True,
                    "ensemble_computed": False,
                    "runtime_metrics": {"versions": {}, "phase_seconds": {}},
                }
            target_payload = composed.get(normalized["target_date"])
            if target_payload is None:
                return LookupResult(
                    False, None, "coverage_partial", self.identity.artifact_id, rows_read
                )
            species_payload["multiversion_comparisons"] = composed
            species_payload["multiversion_comparison"] = target_payload
            response["request"] = copy.deepcopy(normalized)
            response = validate_response(response)
            return LookupResult(
                True, response, None, self.identity.artifact_id, rows_read
            )
        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            PredictorContractError,
            PrecomputeContractError,
            sqlite3.DatabaseError,
            zlib.error,
        ):
            return LookupResult(
                False, None, "artifact_corrupt", self.identity.artifact_id, rows_read
            )

    def lookup(self, request: object) -> LookupResult:
        normalized = normalize_request(request)
        if normalized["view"] not in PRECOMPUTED_VIEWS:
            return LookupResult(
                False, None, "view_not_precomputed", self.identity.artifact_id
            )
        target = normalized["target_date"]
        if target < self.identity.coverage_start or target > self.identity.coverage_end:
            return LookupResult(False, None, "outside_coverage", self.identity.artifact_id)
        if tuple(normalized["trained_species_ids"]) != self.identity.trained_species_ids:
            return LookupResult(False, None, "identity_mismatch", self.identity.artifact_id)
        row = self.connection.execute(
            """SELECT responses.request_json,
                      response_coverage.payload_json AS required_coverage_json,
                      response_payloads.payload_json
                 FROM responses
                 JOIN response_coverage USING (coverage_key)
                 JOIN response_payloads USING (payload_key)
                WHERE responses.request_key = ?""",
            (_request_key(normalized),),
        ).fetchone()
        if row is None:
            if (
                normalized["view"] == "query"
                and not normalized["area_id"]
                and normalized["filter_mode"] == ""
                and normalized["compare_models"]
            ):
                # The all-areas query ranks the preferred operational result;
                # the live service does not execute the requested comparison
                # selection until one concrete area is opened.  Reuse the
                # canonical all-areas response while preserving the truthful
                # echoed UI request.
                canonical_request = {
                    **normalized,
                    "compare_models": False,
                    "multiversion_selection": [],
                }
                canonical = self.lookup(canonical_request)
                if canonical.hit and canonical.response is not None:
                    response = copy.deepcopy(canonical.response)
                    response["request"] = copy.deepcopy(normalized)
                    try:
                        response = validate_response(response)
                    except PredictorContractError:
                        return LookupResult(
                            False,
                            None,
                            "artifact_corrupt",
                            self.identity.artifact_id,
                            canonical.rows_read,
                        )
                    return LookupResult(
                        True,
                        response,
                        None,
                        self.identity.artifact_id,
                        canonical.rows_read,
                    )
                if canonical.reason in {
                    "artifact_corrupt",
                    "coverage_partial",
                    "response_invalid",
                }:
                    return canonical
            composed = self._compose_multiversion_subset(normalized)
            if composed is not None:
                return composed
            return LookupResult(False, None, "request_not_precomputed", self.identity.artifact_id)
        rows_read = 1
        try:
            stored_request = json.loads(row["request_json"])
            required = [
                _coverage_from_dict(value)
                for value in json.loads(
                    zlib.decompress(row["required_coverage_json"]).decode("utf-8")
                )
            ]
            if stored_request != normalized or not required:
                return LookupResult(False, None, "response_invalid", self.identity.artifact_id, rows_read)
            for cell in required:
                coverage_row = self.connection.execute(
                    "SELECT has_base_prediction, member_keys_json FROM coverage WHERE species_id=? AND area_id=? AND target_date=?",
                    (cell.species_id, cell.area_id, cell.target_date),
                ).fetchone()
                rows_read += 1
                if coverage_row is None:
                    return LookupResult(False, None, "coverage_partial", self.identity.artifact_id, rows_read)
                stored_members = tuple(
                    sorted(_member_key_from_dict(value) for value in json.loads(coverage_row["member_keys_json"]))
                )
                if bool(coverage_row["has_base_prediction"]) != cell.has_base_prediction or stored_members != cell.member_keys:
                    return LookupResult(False, None, "coverage_partial", self.identity.artifact_id, rows_read)
                if cell.has_base_prediction:
                    exists = self.connection.execute(
                        "SELECT 1 FROM base_predictions WHERE species_id=? AND area_id=? AND target_date=?",
                        (cell.species_id, cell.area_id, cell.target_date),
                    ).fetchone()
                    rows_read += 1
                    if exists is None:
                        return LookupResult(False, None, "coverage_partial", self.identity.artifact_id, rows_read)
                for member in cell.member_keys:
                    exists = self.connection.execute(
                        """SELECT 1 FROM operational_members
                           WHERE species_id=? AND area_id=? AND target_date=? AND version_id=?
                             AND temporal_contract_id=? AND profile_id=? AND estimator_id=?
                             AND horizon_days=?""",
                        (
                            cell.species_id,
                            cell.area_id,
                            cell.target_date,
                            member.version_id,
                            member.temporal_contract_id,
                            member.profile_id,
                            member.estimator_id,
                            member.horizon_days,
                        ),
                    ).fetchone()
                    rows_read += 1
                    if exists is None:
                        return LookupResult(False, None, "coverage_partial", self.identity.artifact_id, rows_read)
            response = validate_response(
                json.loads(zlib.decompress(row["payload_json"]).decode("utf-8"))
            )
            if normalize_request(response.get("request")) != normalized:
                response = _retarget_weekly_response(response, normalized)
            if response.get("runtime_fingerprint") != self.identity.runtime_fingerprint:
                return LookupResult(False, None, "identity_mismatch", self.identity.artifact_id, rows_read)
            if normalize_request(response.get("request")) != normalized:
                return LookupResult(False, None, "response_invalid", self.identity.artifact_id, rows_read)
            return LookupResult(True, response, None, self.identity.artifact_id, rows_read)
        except (
            json.JSONDecodeError,
            TypeError,
            PredictorContractError,
            PrecomputeContractError,
            sqlite3.DatabaseError,
            zlib.error,
        ):
            return LookupResult(False, None, "artifact_corrupt", self.identity.artifact_id, rows_read)


def lookup_artifact(
    path: Path,
    *,
    identity: ArtifactIdentity,
    request: object,
) -> LookupResult:
    try:
        with ArtifactReader(path, expected_identity=identity) as reader:
            return reader.lookup(request)
    except FileNotFoundError:
        return LookupResult(False, None, "artifact_missing")
    except UnsupportedPrecomputeSchema:
        return LookupResult(False, None, "schema_unknown")
    except PrecomputeIdentityMismatch:
        return LookupResult(False, None, "identity_mismatch")
    except (PrecomputeArtifactError, sqlite3.DatabaseError, KeyError, json.JSONDecodeError):
        return LookupResult(False, None, "artifact_corrupt")


def lookup_active_artifact(
    path: Path,
    *,
    runtime_fingerprint: str,
    request: object,
) -> LookupResult:
    """Lookup against the published artifact using its own immutable identity."""
    candidate = Path(path)
    if not candidate.is_file():
        return LookupResult(False, None, "artifact_missing")
    try:
        connection = _open_readonly(candidate)
        try:
            identity, _counts = _validated_metadata(connection, expected_identity=None)
        finally:
            connection.close()
        if identity.runtime_fingerprint != runtime_fingerprint:
            return LookupResult(False, None, "identity_mismatch", identity.artifact_id)
        with ArtifactReader(candidate, expected_identity=identity) as reader:
            return reader.lookup(request)
    except UnsupportedPrecomputeSchema:
        return LookupResult(False, None, "schema_unknown")
    except (PrecomputeArtifactError, PrecomputeContractError, sqlite3.DatabaseError, OSError):
        return LookupResult(False, None, "artifact_corrupt")


def resolve_with_fallback(
    path: Path,
    *,
    identity: ArtifactIdentity,
    request: object,
    live_predictor: Callable[[dict[str, Any]], Mapping[str, object]],
) -> ResolvedPredictorResponse:
    """Return one complete artifact response or one complete live response."""
    normalized = normalize_request(request)
    lookup = lookup_artifact(path, identity=identity, request=normalized)
    if lookup.hit and lookup.response is not None:
        return ResolvedPredictorResponse(
            lookup.response, "precompute", None, lookup.artifact_id
        )
    live = validate_response(dict(live_predictor(normalized)))
    if normalize_request(live.get("request")) != normalized:
        raise PredictorContractError("Live fallback did not echo the normalized request.")
    if live.get("runtime_fingerprint") != identity.runtime_fingerprint:
        raise PredictorContractError("Live fallback runtime does not match active identity.")
    return ResolvedPredictorResponse(live, "live", lookup.reason, None)


def scientific_response_payload(response: object) -> dict[str, Any]:
    """Remove execution/cache metrics for scientific equivalence assertions."""
    validated = validate_response(response)

    def scientific(value: object, *, field: str = "") -> object:
        if isinstance(value, Mapping):
            return {
                str(key): scientific(child, field=str(key))
                for key, child in value.items()
                if str(key) not in {"metrics", "runtime_metrics"}
            }
        if isinstance(value, list):
            normalized = [scientific(child) for child in value]
            if field == "areas" and all(isinstance(child, str) for child in normalized):
                return sorted(normalized)
            return normalized
        return value

    return json.loads(_canonical_json(scientific(validated)))


def _batch_request(
    identity: ArtifactIdentity,
    *,
    view: str,
    species_id: str,
    target_date: str,
    area_id: str = "",
    selections: Sequence[Mapping[str, object]] = (),
) -> dict[str, object]:
    return normalize_request(
        {
            "schema_version": PREDICTOR_SCHEMA_VERSION,
            "kind": "rainmapper_mushroom_predictor_request",
            "view": view,
            "species_id": species_id,
            "area_id": area_id,
            "target_date": target_date,
            "filter_mode": "",
            "compare_models": bool(selections),
            "multiversion_selection": [dict(row) for row in selections],
            "issue_date": identity.issue_date,
            "trained_species_ids": list(identity.trained_species_ids),
        }
    )


def _member_key_from_payload(payload: object) -> OperationalMemberKey | None:
    if not isinstance(payload, Mapping):
        return None
    reference = payload.get("model_ref")
    if not isinstance(reference, Mapping):
        return None
    try:
        return OperationalMemberKey.create(
            version_id=reference.get("version_id"),
            temporal_contract_id=reference.get("temporal_contract_id"),
            profile_id=reference.get("profile_id"),
            estimator_id=reference.get("estimator_id"),
            horizon_days=reference.get("horizon_days"),
        )
    except PrecomputeContractError:
        return None


def _weekly_execution_key(request: Mapping[str, object]) -> tuple[object, ...]:
    """Collapse UI variants whose scientific work covers the same seven days."""
    view = str(request.get("view", ""))
    species_id = str(request.get("species_id", ""))
    area_id = str(request.get("area_id", ""))
    if view == "week":
        return (view, species_id)
    if view == "query" and area_id:
        return (view, species_id, area_id)
    return ("exact", _canonical_json(dict(request)))


def _retarget_weekly_response(
    response: Mapping[str, object],
    request: Mapping[str, object],
) -> dict[str, Any]:
    """Materialize one exact UI response from an equivalent weekly execution."""
    retargeted = copy.deepcopy(dict(response))
    retargeted["request"] = copy.deepcopy(dict(request))
    if request.get("view") == "query" and request.get("area_id"):
        species = retargeted.get("data", {}).get("species", {})
        species_payload = (
            species.get(str(request.get("species_id", "")), {})
            if isinstance(species, Mapping)
            else {}
        )
        comparisons = (
            species_payload.get("multiversion_comparisons", {})
            if isinstance(species_payload, dict)
            else {}
        )
        target_date = str(request.get("target_date", ""))
        if isinstance(comparisons, Mapping) and target_date in comparisons:
            species_payload["multiversion_comparison"] = copy.deepcopy(
                comparisons[target_date]
            )
    return validate_response(retargeted)


def build_weekly_artifact(
    path: Path,
    *,
    identity: ArtifactIdentity,
    predictor_service: object,
    operational_selections: (
        Sequence[Mapping[str, object]]
        | Mapping[str, Sequence[Mapping[str, object]]]
    ),
    progress: Callable[[int, int, str], None] | None = None,
    cancel_check: Callable[[], None] | None = None,
) -> BatchBuildResult:
    """Materialize every covered UI request through one PredictorService.

    A single shared context keeps weather workspaces, validated manifests and
    loaded model artifacts reusable across the matrix.  Responses themselves
    always come from ``PredictorService.execute``; this module does not rebuild
    scientific selection or interpretation rules.
    """
    issue = date.fromisoformat(identity.issue_date)
    days = [issue + timedelta(days=offset) for offset in range(7)]
    area_map: dict[str, tuple[str, ...]] = {}
    species_context: dict[str, dict[str, object]] = {}
    for species_id in identity.trained_species_ids:
        predictor = predictor_service.predictor(species_id)
        areas = tuple(
            sorted(
                {
                    _required_text(value, "area_id")
                    for value in predictor.areas_with_species_observations()
                }
            )
        )
        area_map[species_id] = areas
        phenology_loader = getattr(predictor_service, "species_phenology", None)
        phenology = (
            phenology_loader(species_id) if callable(phenology_loader) else {}
        )
        species_context[species_id] = {
            "phenology": dict(phenology or {}),
            "season_phase_by_date": {
                target.isoformat(): str(predictor.season_phase(target))
                for target in days
            },
        }

    request_plan: list[tuple[dict[str, object], tuple[tuple[str, str, str], ...]]] = []
    first_species = identity.trained_species_ids[0]
    for target in days:
        day = target.isoformat()
        recommender_cells = tuple(
            (species_id, area_id, day)
            for species_id in identity.trained_species_ids
            for area_id in area_map[species_id]
        )
        request_plan.append(
            (
                _batch_request(
                    identity,
                    view="recommender",
                    species_id=first_species,
                    target_date=day,
                ),
                recommender_cells,
            )
        )
        for species_id in identity.trained_species_ids:
            species_day_cells = tuple(
                (species_id, area_id, day) for area_id in area_map[species_id]
            )
            request_plan.append(
                (
                    _batch_request(
                        identity,
                        view="week",
                        species_id=species_id,
                        target_date=day,
                    ),
                    tuple(
                        (species_id, area_id, covered.isoformat())
                        for area_id in area_map[species_id]
                        for covered in days
                    ),
                )
            )
            request_plan.append(
                (
                    _batch_request(
                        identity,
                        view="query",
                        species_id=species_id,
                        target_date=day,
                    ),
                    species_day_cells,
                )
            )
            species_selections = (
                operational_selections.get(species_id, ())
                if isinstance(operational_selections, Mapping)
                else operational_selections
            )
            day_selections = mushroom_ml_multiversion_comparison.operational_selections(
                species_selections,
                target_date=target,
                issue_date=issue,
            )
            for area_id in area_map[species_id]:
                request_plan.append(
                    (
                        _batch_request(
                            identity,
                            view="query",
                            species_id=species_id,
                            area_id=area_id,
                            target_date=day,
                            selections=day_selections,
                        ),
                        tuple(
                            (species_id, area_id, covered.isoformat())
                            for covered in days
                        ),
                    )
                )

    execution_groups: dict[
        tuple[object, ...],
        list[tuple[dict[str, object], tuple[tuple[str, str, str], ...]]],
    ] = {}
    for request, required_keys in request_plan:
        execution_groups.setdefault(_weekly_execution_key(request), []).append(
            (request, required_keys)
        )

    all_cell_keys = {
        (species_id, area_id, target.isoformat())
        for species_id in identity.trained_species_ids
        for area_id in area_map[species_id]
        for target in days
    }
    writer = _AsyncBatchArtifactWriter(
        path,
        identity=identity,
        all_cell_keys=all_cell_keys,
        species_context=species_context,
    )
    total = len(execution_groups)
    completed = 0
    shared_context: dict[str, Any] = {"disable_response_cache": True}
    try:
        for variants in execution_groups.values():
            if cancel_check is not None:
                cancel_check()
            request = variants[0][0]

            def request_progress(_percent: int, phase: str, message: str) -> None:
                if progress is not None:
                    scope = f"{request['view']}:{request['species_id']}"
                    if request.get("area_id"):
                        scope += f":{request['area_id']}"
                    progress(completed, total, f"{scope} · {phase}: {message}")

            response = validate_response(
                predictor_service.execute(
                    request,
                    progress=request_progress,
                    shared_context=shared_context,
                )
            )
            if response.get("runtime_fingerprint") != identity.runtime_fingerprint:
                raise PrecomputeContractError(
                    "Batch response runtime does not match artifact identity."
                )
            writer.submit(response, variants)
            completed += 1
            if progress is not None:
                progress(
                    completed,
                    total,
                    f"{request['view']}:{request['species_id']}",
                )

        if progress is not None:
            progress(total, total, "Finalizing and validating SQLite artifact")
        if cancel_check is not None:
            cancel_check()
        manifest = writer.finish(
            {
                "batch": {
                    "request_count": len(request_plan),
                    "executed_request_count": len(execution_groups),
                    "shared_context_keys": sorted(shared_context),
                    "sqlite_write_mode": "async_single_writer",
                }
            }
        )
    except BaseException:
        writer.abort()
        raise
    return BatchBuildResult(
        manifest=manifest,
        request_count=writer.request_count,
        executed_request_count=writer.executed_request_count,
        coverage_count=len(all_cell_keys),
        base_prediction_count=writer.base_prediction_count,
        operational_member_count=writer.operational_member_count,
    )
