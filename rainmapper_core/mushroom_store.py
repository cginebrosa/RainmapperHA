"""Persistent storage helpers for Rainmapper mushroom predictor JSON data.

This module keeps the Home Assistant storage rules out of the web UI layer:
versioned defaults are shipped with the app, while the editable live copy lives
under `/share/rainmapper/mushroom-data/`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROFILE_FILE = "mushroom_profiles.json"
CATALOG_FILE = "mushroom_reference_catalogs.json"
GIS_FILE = "mushroom_gis_mappings.json"

MUSHROOM_FILES = {
    "profiles": PROFILE_FILE,
    "catalogs": CATALOG_FILE,
    "gis": GIS_FILE,
}
WRITABLE_MUSHROOM_FILES = {"profiles", "catalogs"}


@dataclass(frozen=True)
class StoreValidationMessage:
    severity: str
    location: str
    message: str
    fix: str | None = None

    def as_dict(self) -> dict[str, str]:
        payload = {
            "severity": self.severity,
            "location": self.location,
            "message": self.message,
        }
        if self.fix:
            payload["fix"] = self.fix
        return payload


@dataclass(frozen=True)
class ReplaceResult:
    ok: bool
    errors: list[StoreValidationMessage]
    warnings: list[StoreValidationMessage]
    backup_path: Path | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_data_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_DEFAULTS_DIR", "").strip()
    if configured:
        return Path(configured)
    app_defaults = Path("/app/mushroom-data")
    if app_defaults.exists():
        return app_defaults
    return repo_root() / "mushroom-data"


def persistent_data_dir() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_DATA_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path("/share/rainmapper/mushroom-data")


def validator_script_path() -> Path:
    configured = os.environ.get("RAINMAPPER_MUSHROOM_VALIDATOR", "").strip()
    if configured:
        return Path(configured)
    app_validator = Path("/app/scripts/validate-mushroom-data.py")
    if app_validator.exists():
        return app_validator
    return repo_root() / "scripts" / "validate-mushroom-data.py"


def load_validator_module():
    path = validator_script_path()
    spec = importlib.util.spec_from_file_location("rainmapper_mushroom_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load mushroom validator from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalize_kind(kind: str) -> str:
    normalized = kind.strip().lower()
    if normalized not in MUSHROOM_FILES:
        raise ValueError(f"Unknown mushroom data file: {kind}")
    return normalized


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(serialized)
    os.replace(tmp_path, path)


def validation_messages(data_dir: Path) -> tuple[list[StoreValidationMessage], list[StoreValidationMessage]]:
    validator = load_validator_module()
    messages = [
        StoreValidationMessage(
            severity=str(message.severity),
            location=str(message.location),
            message=str(message.message),
            fix=str(message.fix) if message.fix else None,
        )
        for message in validator.validate_mushroom_data(data_dir)
    ]
    errors = [message for message in messages if message.severity == "ERROR"]
    warnings = [message for message in messages if message.severity == "WARN"]
    return errors, warnings


class MushroomDataStore:
    def __init__(
        self,
        defaults_dir: Path | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.defaults_dir = defaults_dir or default_data_dir()
        self.data_dir = data_dir or persistent_data_dir()

    def file_name(self, kind: str) -> str:
        return MUSHROOM_FILES[normalize_kind(kind)]

    def default_path(self, kind: str) -> Path:
        return self.defaults_dir / self.file_name(kind)

    def persistent_path(self, kind: str) -> Path:
        return self.data_dir / self.file_name(kind)

    def current_path(self, kind: str) -> Path:
        persistent_path = self.persistent_path(kind)
        return persistent_path if persistent_path.exists() else self.default_path(kind)

    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    def ensure_seeded(self) -> list[str]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        copied: list[str] = []
        for kind, file_name in MUSHROOM_FILES.items():
            target = self.data_dir / file_name
            if target.exists():
                continue
            source = self.defaults_dir / file_name
            if not source.exists():
                raise FileNotFoundError(f"Missing mushroom default file: {source}")
            shutil.copy2(source, target)
            copied.append(kind)
        return copied

    def load(self, kind: str, source: str = "current") -> Any:
        normalized = normalize_kind(kind)
        if source == "default":
            path = self.default_path(normalized)
        elif source == "persistent":
            path = self.persistent_path(normalized)
        elif source == "current":
            path = self.current_path(normalized)
        else:
            raise ValueError(f"Unknown mushroom data source: {source}")
        return read_json(path)

    def export_payload(self, kind: str, source: str = "current") -> dict[str, Any]:
        normalized = normalize_kind(kind)
        return {
            "kind": normalized,
            "file": self.file_name(normalized),
            "source": source,
            "data": self.load(normalized, source=source),
        }

    def empty_template(self, kind: str) -> dict[str, Any]:
        normalized = normalize_kind(kind)
        payload = self.load(normalized, source="default")
        if normalized == "profiles":
            payload["species_profiles"] = []
        elif normalized == "catalogs":
            catalogs = payload.get("catalogs", {})
            if not isinstance(catalogs, dict):
                catalogs = {}
            payload["catalogs"] = {name: [] for name in catalogs}
        else:
            raise ValueError("GIS mappings do not have an editable empty template in this phase")
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            metadata["updated_at"] = datetime.now(UTC).date().isoformat()
        return {
            "kind": normalized,
            "file": self.file_name(normalized),
            "source": "template",
            "data": payload,
        }

    def validate_current(self) -> tuple[list[StoreValidationMessage], list[StoreValidationMessage]]:
        self.ensure_seeded()
        return validation_messages(self.data_dir)

    def validate_candidate(
        self,
        kind: str,
        payload: Any,
    ) -> tuple[list[StoreValidationMessage], list[StoreValidationMessage]]:
        normalized = normalize_kind(kind)
        with tempfile.TemporaryDirectory() as tmp_dir:
            candidate_dir = Path(tmp_dir)
            for candidate_kind, file_name in MUSHROOM_FILES.items():
                source_payload = payload if candidate_kind == normalized else self.load(candidate_kind)
                write_json_atomic(candidate_dir / file_name, source_payload)
            return validation_messages(candidate_dir)

    def replace(self, kind: str, payload: Any) -> ReplaceResult:
        normalized = normalize_kind(kind)
        if normalized not in WRITABLE_MUSHROOM_FILES:
            raise ValueError("GIS mappings are read-only in the current maintenance phase")
        if not isinstance(payload, dict):
            return ReplaceResult(
                ok=False,
                errors=[
                    StoreValidationMessage(
                        severity="ERROR",
                        location=self.file_name(normalized),
                        message="replacement payload must be a JSON object",
                    )
                ],
                warnings=[],
            )

        self.ensure_seeded()
        errors, warnings = self.validate_candidate(normalized, payload)
        if errors:
            return ReplaceResult(ok=False, errors=errors, warnings=warnings)

        target = self.persistent_path(normalized)
        backup_path = None
        if target.exists():
            self.backup_dir().mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir() / f"{target.stem}.{timestamp()}{target.suffix}"
            shutil.copy2(target, backup_path)
        write_json_atomic(target, payload)
        return ReplaceResult(ok=True, errors=[], warnings=warnings, backup_path=backup_path)


def default_store() -> MushroomDataStore:
    return MushroomDataStore()
