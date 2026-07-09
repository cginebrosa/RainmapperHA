#!/usr/bin/env python3
"""Attach reduced observation photos to existing mushroom observations.

The loader matches images by the observation `source.label` field, writes display
copies under `mushroom-data/media/observation-photos/<year>/`, and stores media
references in `mushroom_observations.json`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "rainmapper-app" / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import web_server  # noqa: E402
from rainmapper_core import mushroom_paths  # noqa: E402
from rainmapper_core.mushroom_store import write_json_atomic  # noqa: E402


def image_files(image_dir: Path) -> dict[str, Path]:
    return {
        path.name: path
        for path in sorted(image_dir.iterdir())
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".heic", ".heif"}
    }


def replace_photo_media(row: dict[str, object], media: dict[str, object]) -> None:
    original_filename = str(media.get("original_filename", "") or "")
    existing = row.get("media")
    kept = []
    if isinstance(existing, list):
        for item in existing:
            if not isinstance(item, dict):
                continue
            if item.get("kind") == "photo" and item.get("original_filename") == original_filename:
                continue
            kept.append(item)
    kept.append(media)
    row["media"] = kept


def load_observation_photos(
    observations_path: Path,
    image_dir: Path,
    dry_run: bool = False,
) -> dict[str, object]:
    payload = json.loads(observations_path.read_text(encoding="utf-8"))
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ValueError("observations payload does not contain an observations list")
    images = image_files(image_dir)
    matched_images: set[str] = set()
    updated_rows = 0
    attached_media = 0
    missing_images: list[str] = []

    for row in observations:
        if not isinstance(row, dict):
            continue
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        label = str(source.get("label", "") if isinstance(source, dict) else "").strip()
        if not label or label == "Manual":
            continue
        image_path = images.get(label)
        if image_path is None:
            missing_images.append(f"{row.get('observation_id', '-')}: {label}")
            continue
        matched_images.add(label)
        if dry_run:
            attached_media += 1
            if not any(
                isinstance(item, dict) and item.get("kind") == "photo" and item.get("original_filename") == label
                for item in (row.get("media") if isinstance(row.get("media"), list) else [])
            ):
                updated_rows += 1
            continue
        media = web_server.save_observation_image_media(
            str(row.get("observation_id", "")),
            {
                "filename": image_path.name,
                "content": image_path.read_bytes(),
                "content_type": "image/jpeg",
            },
            row.get("observed_at"),
        )
        if not media:
            missing_images.append(f"{row.get('observation_id', '-')}: {label} could not be saved")
            continue
        before = json.dumps(row.get("media", []), sort_keys=True)
        replace_photo_media(row, media)
        after = json.dumps(row.get("media", []), sort_keys=True)
        attached_media += 1
        if before != after:
            updated_rows += 1

    unused_images = sorted(set(images) - matched_images)
    if not dry_run:
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            metadata["updated_at"] = datetime.now(UTC).date().isoformat()
            metadata["updated_by"] = "rainmapper_ui_photo_initial_load"
        backup_path = observations_path.with_suffix(
            observations_path.suffix + f".bak-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
        )
        shutil.copy2(observations_path, backup_path)
        write_json_atomic(observations_path, payload)
    else:
        backup_path = None

    return {
        "observations": len([row for row in observations if isinstance(row, dict)]),
        "images": len(images),
        "matched_images": len(matched_images),
        "attached_media": attached_media,
        "updated_rows": updated_rows,
        "missing_images": missing_images,
        "unused_images": unused_images,
        "backup_path": str(backup_path) if backup_path else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--images-dir",
        default=str(ROOT / "tmp" / "observation-images-intial-load"),
        help="Directory containing source observation images.",
    )
    parser.add_argument(
        "--observations-path",
        default=str(mushroom_paths.mushroom_observations_path()),
        help="Path to mushroom_observations.json.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report matches without writing JSON.")
    args = parser.parse_args()
    result = load_observation_photos(Path(args.observations_path), Path(args.images_dir), dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
