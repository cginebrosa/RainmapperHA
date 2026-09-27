"""Compact, immutable membership index for the rows of final fitted models.

Models sharing a prepared training matrix share one observation set. No feature
vectors or observations are copied; point queries use the composite primary key.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sqlite3

FILENAME = "training-observations.sqlite"
MAX_BYTES = 128 * 1024 * 1024
MAX_MEMBERS = 2_000_000
STATES = frozenset({"used", "not_used", "legacy", "unavailable", "no_model"})


def valid_id(value):
    return isinstance(value, str) and 0 < len(value) <= 256 and not any(ord(c) < 32 for c in value)


def validate_reference(value, batch_id):
    expected = Path("batches", batch_id, FILENAME).as_posix()
    if (not isinstance(value, dict) or value.get("path") != expected
            or not re.fullmatch(r"[0-9a-f]{64}", str(value.get("sha256", "")))
            or type(value.get("size_bytes")) is not int
            or not 0 < value["size_bytes"] <= MAX_BYTES):
        raise ValueError("Invalid training observation index reference")
    return {key: value[key] for key in ("path", "sha256", "size_bytes")}


class Writer:
    """Write once in batch staging, using already filtered fit samples."""
    def __init__(self, path):
        self.path = Path(path)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA cache_size=-256")
        self.db.execute(f"PRAGMA max_page_count={MAX_BYTES // 4096}")
        self.db.executescript("""
            PRAGMA user_version=1;
            CREATE TABLE sets (id INTEGER PRIMARY KEY, complete INTEGER NOT NULL);
            CREATE TABLE members (set_id INTEGER NOT NULL, observation_id TEXT NOT NULL,
                PRIMARY KEY (set_id, observation_id)) WITHOUT ROWID;
            CREATE TABLE models (artifact_key TEXT PRIMARY KEY, set_id INTEGER NOT NULL)
                WITHOUT ROWID;
        """)
        self.groups = {}
        self.input_count = 0

    def add(self, artifact_key, scope, samples):
        group = self.groups.get(tuple(scope))
        if group is None:
            # Check cardinality before iterating/materializing additional data.
            if self.input_count + len(samples) > MAX_MEMBERS:
                raise ValueError("Training observation index exceeds row budget")
            self.input_count += len(samples)
            group = len(self.groups) + 1
            self.groups[tuple(scope)] = group
            complete = True
            for sample in samples:
                observation_id = (sample.get("metadata") or {}).get("observation_id")
                if not valid_id(observation_id):
                    # Legacy/synthetic input lacking the original ID cannot
                    # prove absence. Never treat sample IDs as observation IDs.
                    complete = False
                    continue
                self.db.execute("INSERT OR IGNORE INTO members VALUES (?, ?)", (group, observation_id))
            self.db.execute("INSERT INTO sets VALUES (?, ?)", (group, int(complete)))
        self.db.execute("INSERT INTO models VALUES (?, ?)", (artifact_key, group))

    def finish(self, batch_id):
        self.db.commit()
        self.close()
        size = self.path.stat().st_size
        if size > MAX_BYTES:
            raise ValueError("Training observation index exceeds byte budget")
        with self.path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        return {"path": Path("batches", batch_id, FILENAME).as_posix(),
                "sha256": digest, "size_bytes": size}

    def close(self):
        self.db.close()


def lookup(models_root, manifest, artifact_key, observation_id):
    """Two indexed seeks; missing/corrupt evidence never becomes 'not used'."""
    reference = manifest.get("training_observations")
    if reference is None:
        return "legacy"
    try:
        reference = validate_reference(reference, manifest["batch_id"])
        root = Path(models_root).resolve()
        path = (root / reference["path"]).resolve()
        if not path.is_relative_to(root) or path.stat().st_size != reference["size_bytes"]:
            return "unavailable"
        db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            db.execute("PRAGMA cache_size=-256")
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                return "unavailable"
            row = db.execute("SELECT set_id, complete FROM models JOIN sets ON sets.id=models.set_id "
                             "WHERE artifact_key=?", (artifact_key,)).fetchone()
            if row is None:
                return "unavailable"
            found = db.execute("SELECT 1 FROM members WHERE set_id=? AND observation_id=?",
                               (row[0], observation_id)).fetchone()
            return "used" if found else "not_used" if row[1] else "unavailable"
        finally:
            db.close()
    except (OSError, sqlite3.Error, ValueError, KeyError):
        return "unavailable"
