#!/usr/bin/env python3
"""Stage and safely apply the established observation-photo normalization."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

MAX_EDGE = 1600
JPEG_QUALITY = 86


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def safe_relative_photo_path(value: str) -> Path:
    prefix = "media/observation-photos/"
    if not value.startswith(prefix):
        raise ValueError(f"Unexpected observation photo path: {value}")
    relative = Path(value.removeprefix(prefix))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe observation photo path: {value}")
    return relative


def normalize_one(source: Path, target: Path) -> dict[str, Any]:
    original_size = source.stat().st_size
    original_sha256 = sha256_file(source)
    with Image.open(source) as opened:
        original_format = opened.format
        original_width, original_height = opened.size
        original_orientation = opened.getexif().get(274)
        image = ImageOps.exif_transpose(opened)
        exif_bytes = image.info.get("exif", b"")
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
        output_width, output_height = image.size
        save_kwargs: dict[str, Any] = {
            "format": "JPEG",
            "quality": JPEG_QUALITY,
            "optimize": True,
        }
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_name(f".{target.name}.tmp")
        try:
            image.save(temp_path, **save_kwargs)
            os.replace(temp_path, target)
        finally:
            temp_path.unlink(missing_ok=True)

    with Image.open(target) as check:
        check.verify()
    with Image.open(target) as check:
        if check.format != "JPEG" or max(check.size) > MAX_EDGE:
            raise ValueError(f"Invalid normalized image: {target}")
        output_exif_bytes = len(check.info.get("exif", b""))

    output_size = target.stat().st_size
    return {
        "original_size_bytes": original_size,
        "output_size_bytes": output_size,
        "saved_bytes": original_size - output_size,
        "original_sha256": original_sha256,
        "output_sha256": sha256_file(target),
        "original_format": original_format,
        "original_width": original_width,
        "original_height": original_height,
        "original_orientation": original_orientation,
        "output_width": output_width,
        "output_height": output_height,
        "exif_preserved": bool(exif_bytes and output_exif_bytes),
    }


def stage(args: argparse.Namespace) -> None:
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    candidates = [row for row in audit.get("files", []) if row.get("candidate")]
    if any(args.output.rglob("*")):
        raise SystemExit(f"Output directory must be empty: {args.output}")
    items = []
    for index, row in enumerate(candidates, start=1):
        media_path = str(row["path"])
        relative = safe_relative_photo_path(media_path)
        source = args.source / relative
        target = args.output / relative
        result = normalize_one(source, target)
        items.append({"path": media_path, **result})
        print(f"[{index}/{len(candidates)}] {media_path}: {result['saved_bytes']} bytes saved", flush=True)
    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "criteria": {"max_edge": MAX_EDGE, "jpeg_quality": JPEG_QUALITY, "optimize": True},
        "item_count": len(items),
        "original_bytes": sum(item["original_size_bytes"] for item in items),
        "output_bytes": sum(item["output_size_bytes"] for item in items),
        "saved_bytes": sum(item["saved_bytes"] for item in items),
        "items": items,
    }
    write_json_atomic(args.manifest, manifest)


def update_media_metadata(payload: dict[str, Any], items: dict[str, dict[str, Any]]) -> int:
    updated = 0
    for observation in payload.get("observations", []):
        for media in observation.get("media", []):
            item = items.get(str(media.get("path", "")))
            if media.get("kind") != "photo" or item is None:
                continue
            media["size_bytes"] = item["output_size_bytes"]
            media["content_type"] = "image/jpeg"
            media["resized"] = True
            media["exif_preserved"] = item["exif_preserved"]
            updated += 1
    return updated


def apply(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = {str(item["path"]): item for item in manifest.get("items", [])}
    if len(items) != manifest.get("item_count"):
        raise SystemExit("Manifest contains duplicate or inconsistent items")

    photos_root = args.data_dir / "media" / "observation-photos"
    for media_path, item in items.items():
        relative = safe_relative_photo_path(media_path)
        current = photos_root / relative
        staged = args.staged / relative
        if sha256_file(current) != item["original_sha256"]:
            raise SystemExit(f"Remote original changed since staging: {media_path}")
        if sha256_file(staged) != item["output_sha256"]:
            raise SystemExit(f"Staged output hash mismatch: {media_path}")

    payload_paths = [
        args.data_dir / "mushroom_observations.json",
        args.data_dir / "archived" / "mushroom_observations_archived.json",
    ]
    payloads = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in payload_paths]
    args.backup.mkdir(parents=True, exist_ok=True)
    for path, _payload in payloads:
        # SMB exposes macOS flags that cannot always be reproduced on a local
        # APFS destination. The recovery copy needs the exact bytes, not the
        # remote filesystem metadata.
        shutil.copyfile(path, args.backup / path.name)

    applied = []
    for index, (media_path, item) in enumerate(items.items(), start=1):
        relative = safe_relative_photo_path(media_path)
        current = photos_root / relative
        staged = args.staged / relative
        temp_path = current.with_name(f".{current.name}.resize.tmp")
        try:
            shutil.copyfile(staged, temp_path)
            if sha256_file(temp_path) != item["output_sha256"]:
                raise OSError(f"Remote temporary copy hash mismatch: {media_path}")
            os.replace(temp_path, current)
        finally:
            temp_path.unlink(missing_ok=True)
        applied.append(media_path)
        print(f"[{index}/{len(items)}] applied {media_path}", flush=True)

    metadata_updates = 0
    for path, payload in payloads:
        metadata_updates += update_media_metadata(payload, items)
        write_json_atomic(path, payload)

    report = {
        "schema_version": "1.0",
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "applied_count": len(applied),
        "metadata_references_updated": metadata_updates,
        "saved_bytes": manifest["saved_bytes"],
        "paths": applied,
    }
    write_json_atomic(args.report, report)


def verify(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = {str(item["path"]): item for item in manifest.get("items", [])}
    photos_root = args.data_dir / "media" / "observation-photos"
    failures: list[str] = []
    for media_path, item in items.items():
        target = photos_root / safe_relative_photo_path(media_path)
        if not target.is_file():
            failures.append(f"missing normalized file: {media_path}")
            continue
        if sha256_file(target) != item["output_sha256"]:
            failures.append(f"output hash mismatch: {media_path}")
            continue
        try:
            with Image.open(target) as image:
                image.verify()
            with Image.open(target) as image:
                if image.format != "JPEG" or max(image.size) > MAX_EDGE:
                    failures.append(f"invalid output format/dimensions: {media_path}")
                if bool(image.info.get("exif", b"")) != bool(item["exif_preserved"]):
                    failures.append(f"EXIF mismatch: {media_path}")
        except Exception as exc:
            failures.append(f"cannot decode {media_path}: {type(exc).__name__}: {exc}")

    payload_paths = [
        args.data_dir / "mushroom_observations.json",
        args.data_dir / "archived" / "mushroom_observations_archived.json",
    ]
    referenced: set[str] = set()
    metadata_references = 0
    for payload_path in payload_paths:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        for observation in payload.get("observations", []):
            for media in observation.get("media", []):
                if media.get("kind") != "photo" or not media.get("path"):
                    continue
                media_path = str(media["path"])
                referenced.add(media_path)
                item = items.get(media_path)
                if item is None:
                    continue
                metadata_references += 1
                if media.get("size_bytes") != item["output_size_bytes"]:
                    failures.append(f"size metadata mismatch: {media_path}")
                if media.get("content_type") != "image/jpeg" or media.get("resized") is not True:
                    failures.append(f"normalization metadata mismatch: {media_path}")
                if bool(media.get("exif_preserved")) != bool(item["exif_preserved"]):
                    failures.append(f"EXIF metadata mismatch: {media_path}")

    disk_paths = {
        f"media/observation-photos/{path.relative_to(photos_root).as_posix()}"
        for path in photos_root.rglob("*")
        if path.is_file() and not path.name.startswith(".")
    }
    missing_references = sorted(referenced - disk_paths)
    unreferenced_files = sorted(disk_paths - referenced)
    temporary_files = sorted(
        path.relative_to(args.data_dir).as_posix()
        for path in photos_root.rglob("*")
        if path.is_file() and path.name.startswith(".")
    )
    if missing_references:
        failures.append(f"{len(missing_references)} referenced files are missing")
    if unreferenced_files:
        failures.append(f"{len(unreferenced_files)} files are unreferenced")
    if temporary_files:
        failures.append(f"{len(temporary_files)} temporary files remain")
    report = {
        "schema_version": "1.0",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest_items_verified": len(items),
        "metadata_references_verified": metadata_references,
        "disk_file_count": len(disk_paths),
        "referenced_file_count": len(referenced),
        "disk_bytes": sum((args.data_dir / path).stat().st_size for path in disk_paths),
        "missing_references": missing_references,
        "unreferenced_files": unreferenced_files,
        "temporary_files": temporary_files,
        "failures": failures,
        "ok": not failures,
    }
    write_json_atomic(args.report, report)
    if failures:
        raise SystemExit("Post-apply verification failed; inspect the verification report")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    stage_parser = commands.add_parser("stage")
    stage_parser.add_argument("--source", type=Path, required=True)
    stage_parser.add_argument("--output", type=Path, required=True)
    stage_parser.add_argument("--audit", type=Path, required=True)
    stage_parser.add_argument("--manifest", type=Path, required=True)
    stage_parser.set_defaults(func=stage)
    apply_parser = commands.add_parser("apply")
    apply_parser.add_argument("--data-dir", type=Path, required=True)
    apply_parser.add_argument("--staged", type=Path, required=True)
    apply_parser.add_argument("--manifest", type=Path, required=True)
    apply_parser.add_argument("--backup", type=Path, required=True)
    apply_parser.add_argument("--report", type=Path, required=True)
    apply_parser.set_defaults(func=apply)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--data-dir", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser.add_argument("--report", type=Path, required=True)
    verify_parser.set_defaults(func=verify)
    return root


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
