"""Explicit, offline migration of HA media; never run from a request handler."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

MARKER = ".media-layout-v1.json"


def organized(root: Path) -> bool:
    if (root / ".media-migration-in-progress.json").exists():
        raise ValueError("media layout migration is incomplete; keep writers stopped")
    marker = root / MARKER
    if not marker.exists():
        return False
    data = json.loads(marker.read_text())
    if data.get("version") != 1 or data.get("state") != "complete":
        raise ValueError("media layout migration is incomplete; keep writers stopped")
    return True


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory(root: Path) -> dict:
    """Preserve file contents, symlink targets and empty directories."""
    result = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(base) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                result[rel] = {"link": os.readlink(p)}
            elif p.is_dir():
                result[rel] = {"directory": True}
            elif p.is_file():
                result[rel] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
            else:
                raise ValueError(f"unsupported media entry: {p}")
    return result


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_name(path.name + ".migration-tmp")
    with temporary.open("x") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)


def migration_plan(root: Path) -> list[tuple[Path, Path]]:
    if organized(root):
        return []
    if (root / ".media-migration-in-progress.json").exists():
        raise ValueError("unfinished migration journal; inspect it before continuing")
    moves = []
    derived = root / "mushroom-derived"
    if derived.exists():
        if derived.is_symlink():
            raise ValueError("derived root must be an ordinary directory")
        for p in sorted(derived.iterdir()):
            if p.name == "worker":
                target = root / "transfers" / "worker"
            else:
                name = {"ml_models": "models", "mushroom-artifacts": "artifacts",
                        "ml_version_archive": "model-archive"}.get(p.name, p.name)
                target = root / "results" / name
            moves.append((p, target))
    for source, target in (("predictor_precompute", "results/predictor-precompute"),
                           ("runtime-cache", "cache")):
        if (root / source).exists():
            moves.append((root / source, root / target))
    for source, target in moves:
        if source.is_symlink() or target.exists() or target.is_symlink():
            raise ValueError(f"unsafe root or destination conflict: {source} -> {target}")
        ancestor = target.parent
        while not ancestor.exists():
            ancestor = ancestor.parent
        if ancestor.is_symlink() or ancestor.stat().st_dev != source.stat().st_dev:
            raise ValueError(f"migration must stay on the same ordinary filesystem: {target}")
    return moves


def publication_update(root: Path) -> dict | None:
    """Relocate operational source references, keeping scientific manifest intact."""
    relative = "predictor-runtime-archives/published-runtime.json"
    source = root / "runtime-cache" / relative
    target = root / "cache" / relative
    if not source.exists():
        source = target
    if not source.exists():
        return None
    raw = source.read_text()
    data = json.loads(raw)
    replacements = {
        "/media/rainmapper/mushroom-derived/ml_models/": "/media/rainmapper/results/models/",
        "/media/rainmapper/mushroom-derived/mushroom-artifacts/": "/media/rainmapper/results/artifacts/",
        "/media/rainmapper/runtime-cache/": "/media/rainmapper/cache/",
    }
    changed = 0
    for key, value in data.get("sources", {}).items():
        for old, new in replacements.items():
            if value.startswith(old):
                data["sources"][key] = new + value[len(old):]
                changed += 1
                break
    return {"path": str(target), "before": raw, "after": data, "references_changed": changed} if changed else None


def migrate(root: Path, config_paths: list[Path], *, writers_stopped: bool) -> dict:
    if not writers_stopped:
        raise ValueError("stop coordinator writers before migration")
    moves = migration_plan(root)
    if organized(root):
        return {"already_complete": True}
    # Preflight every config before moving anything. Keep exact originals in journal.
    configs = []
    old = "/media/rainmapper/mushroom-derived/ml_models"
    for p in config_paths:
        if p.exists():
            raw = p.read_text()
            data = json.loads(raw)
            value = data.get("models_root")
            if value == old:
                data["models_root"] = "/media/rainmapper/results/models"
                configs.append({"path": str(p), "before": raw, "after": data})
            elif isinstance(value, str) and "mushroom-derived" in value:
                raise ValueError(f"unrecognized explicit models_root in {p}")
    publication = publication_update(root)
    if publication:
        configs.append(publication)
    checks = []
    for source, target in moves:
        before = inventory(source) if source.is_dir() else {".": {"bytes": source.stat().st_size, "sha256": sha256(source)}}
        checks.append({"source": str(source), "target": str(target), "inventory": before})
    journal = root / ".media-migration-in-progress.json"
    report = {"version": 1, "state": "prepared", "moves": checks, "configs": configs}
    write_json(journal, report)
    try:
        for source, target in moves:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
        for item in configs:
            write_json(Path(item["path"]), item["after"])
        for item in checks:
            target = Path(item["target"])
            after = inventory(target) if target.is_dir() else {".": {"bytes": target.stat().st_size, "sha256": sha256(target)}}
            expected = dict(item["inventory"])
            for config in configs:
                path = Path(config["path"])
                if path.is_relative_to(target):
                    raw = (json.dumps(config["after"], indent=2, ensure_ascii=False) + "\n").encode()
                    expected[path.relative_to(target).as_posix()] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            if expected != after:
                raise ValueError(f"content changed during migration: {target}")
        derived = root / "mushroom-derived"
        if derived.exists():
            derived.rmdir()  # Never remove unexpected contents.
        report["state"] = "complete"
        write_json(root / MARKER, {"version": 1, "state": "complete"})
        write_json(root / "media-migration-receipt.json", report)
        journal.unlink()
        return report
    except Exception:
        # No automatic deletion or rollback over a potentially changed destination.
        # The journal retains every pre-migration fingerprint and original config.
        raise


def retire_legacy_geography(root: Path, *, writers_stopped: bool,
                            consumers_verified: bool, report_path: Path) -> dict:
    """Delete only files whose surviving canonical copy is fully SHA-verified."""
    if not writers_stopped or not consumers_verified:
        raise ValueError("stop writers and verify canonical consumers before retirement")
    canonical = root / "geography"
    auxiliary = json.loads((canonical / "mushroom-GIS/geography-auxiliary.json").read_text())
    pointer = json.loads((canonical / "CURRENT.json").read_text())
    generation = pointer["generation"]
    table = json.loads((canonical / pointer["sources_file"]).read_text())["files"]
    old_map = root / "prediction-map/generations" / generation
    sets = [(root / "mushroom-GIS", auxiliary["files"], None)]
    if old_map.exists():
        sets.append((old_map, json.loads((old_map / "manifest.json").read_text())["files"], table))
    hashes = {}
    rows = []
    metadata = []
    def contained(base, relative):
        p = base / relative
        if not p.resolve().is_relative_to(base.resolve()) or p.is_symlink():
            raise ValueError(f"unsafe geography path: {p}")
        return p
    def identity(p):
        st = p.stat()
        return (st.st_size, st.st_mtime_ns, st.st_ino)
    for source, files, mappings in sets:
        if not source.exists():
            continue
        allowed = set()
        for row in files:
            old = contained(source, row["path"])
            dest_rel = ("mushroom-GIS/" + row["path"] if mappings is None
                        else mappings[row["path"]]["physical_path"])
            target = contained(canonical, dest_rel)
            if not old.is_file() or not target.is_file():
                raise ValueError(f"missing geography copy: {old} / {target}")
            allowed.add(old)
            old_stat, new_stat = identity(old), identity(target)
            if old_stat[0] != row["bytes"] or new_stat[0] != row["bytes"]:
                raise ValueError(f"geography size mismatch: {old}")
            for p, st in ((target, new_stat), (old, old_stat)):
                if p not in hashes:
                    hashes[p] = sha256(p)
                if hashes[p] != row["sha256"] or identity(p) != st:
                    raise ValueError(f"geography content changed: {p}")
            rows.append({"source": str(old), "canonical": str(target), "bytes": row["bytes"],
                         "sha256": row["sha256"], "source_stat": old_stat, "canonical_stat": new_stat})
            if len(rows) % 200 == 0:
                print(f"Verified {len(rows)} legacy references", flush=True)
        for base, dirs, names in os.walk(source, followlinks=False):
            for name in dirs + names:
                p = Path(base) / name
                if p.is_symlink():
                    raise ValueError(f"unexpected legacy link: {p}")
                if p.is_file() and p not in allowed:
                    # Preserve every extra file, including locks and old manifests.
                    target = canonical / "imports/retired-legacy-metadata" / p.relative_to(root)
                    if target.exists():
                        raise ValueError(f"metadata preservation conflict: {target}")
                    metadata.append((p, target))
    report = {"state": "verified", "files": rows, "retired_bytes": sum(r["bytes"] for r in rows),
              "metadata_preserved": [[str(a), str(b)] for a, b in metadata]}
    write_json(report_path, report)
    # All files passed before the first deletion. Recheck identities immediately.
    for row in rows:
        old, target = Path(row["source"]), Path(row["canonical"])
        if identity(old) != row["source_stat"] or identity(target) != row["canonical_stat"]:
            raise ValueError("geography changed after verification; retirement stopped")
        old.unlink()
    for old, target in metadata:
        target.parent.mkdir(parents=True, exist_ok=True)
        old.rename(target)
    for source, _, _ in sets:
        if source.exists():
            for base, dirs, _ in os.walk(source, topdown=False):
                Path(base).rmdir()
    previous = root / "prediction-map"
    if previous.exists():
        for name in (f"prediction-map-{generation}.tar.gz.json", f"prediction-map-{generation}.tar.gz.sha256"):
            old = previous / name
            if old.is_file() and not old.is_symlink():
                target = canonical / "imports/retired-legacy-metadata/prediction-map" / name
                if target.exists():
                    raise ValueError(f"metadata preservation conflict: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                old.rename(target)
                report["metadata_preserved"].append([str(old), str(target)])
        for directory in (previous / "generations", previous):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
    report["state"] = "complete"
    write_json(report_path, report)
    return report
