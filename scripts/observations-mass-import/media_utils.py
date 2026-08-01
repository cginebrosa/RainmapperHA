"""
Utilidades de procesado de media para importación masiva de observaciones.
Extraídas de rainmapper-app/app/web_server.py — mantener sincronizadas si cambian allí.
"""

from __future__ import annotations

import io
import mimetypes
import re
import subprocess
from pathlib import Path
from urllib.parse import urlencode

# Constantes (deben coincidir con web_server.py)
IMAGE_MAX_EDGE = 1600
IMAGE_JPEG_QUALITY = 86
VIDEO_MAX_SECONDS = 30
VIDEO_MAX_WIDTH = 854
VIDEO_MAX_HEIGHT = 480
VIDEO_CRF = 30
MEDIA_FILE_MAX_BYTES = 100 * 1024 * 1024
VIDEO_SUFFIXES = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".webm", ".3gp"}


def is_video(filename: str, content_type: str = "") -> bool:
    suffix = Path(str(filename or "")).suffix.lower()
    mime = str(content_type or "").split(";", 1)[0].strip().lower()
    return suffix in VIDEO_SUFFIXES or mime.startswith("video/")


def safe_media_name(filename: str, extension: str = ".jpg") -> str:
    source_name = Path(str(filename or "photo")).name
    source_stem = Path(source_name).stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", source_stem).strip("-") or "photo"
    ext = Path(source_name).suffix.lower() or extension
    ext = ext if ext.startswith(".") else f".{ext}"
    ext = re.sub(r"[^a-z0-9.]+", "", ext.lower()) or ".jpg"
    return f"{stem}{ext}"


def original_image_extension(filename: str, content_type: str = "") -> str:
    suffix = Path(str(filename or "")).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".heic", ".heif"}:
        return suffix
    guessed = mimetypes.guess_extension(str(content_type or "").split(";", 1)[0].strip())
    if guessed in {".jpg", ".jpeg", ".heic", ".heif"}:
        return guessed
    return ".jpg"


def media_url(relative_path: str) -> str:
    return "./observation-media?" + urlencode({"path": relative_path})


def media_year(observed_at: object = None) -> str:
    text = str(observed_at or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text[:4]
    from datetime import datetime, UTC
    return datetime.now(UTC).date().isoformat()[:4]


def unique_media_path(target_dir: Path, filename: str, content: bytes) -> Path:
    candidate = target_dir / filename
    if not candidate.exists() or candidate.read_bytes() == content:
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        next_candidate = target_dir / f"{stem}-{counter}{suffix}"
        if not next_candidate.exists() or next_candidate.read_bytes() == content:
            return next_candidate
        counter += 1


def process_image(
    source_path: Path,
    target_dir: Path,
    observed_at: str | None = None,
) -> dict | None:
    """
    Redimensiona una imagen y la guarda en target_dir.
    Devuelve el dict media entry o None si falla.
    """
    filename = source_path.name
    content = source_path.read_bytes()

    if len(content) > MEDIA_FILE_MAX_BYTES:
        raise ValueError(f"{filename} supera el límite de {MEDIA_FILE_MAX_BYTES // (1024*1024)} MB")

    year = media_year(observed_at)
    target_dir = target_dir / year
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = safe_media_name(filename, ".jpg")
    persisted_content_type = "image/jpeg"
    resized = False
    exif_preserved = False
    output_content = b""

    try:
        from PIL import Image, ImageOps
        with Image.open(io.BytesIO(content)) as image:
            image = ImageOps.exif_transpose(image)
            exif_bytes = image.info.get("exif", b"")
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            image.thumbnail((IMAGE_MAX_EDGE, IMAGE_MAX_EDGE), Image.Resampling.LANCZOS)
            save_kwargs: dict = {"format": "JPEG", "quality": IMAGE_JPEG_QUALITY, "optimize": True}
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
                exif_preserved = True
            output = io.BytesIO()
            image.save(output, **save_kwargs)
            output_content = output.getvalue()
            resized = True
    except Exception:
        ext = original_image_extension(filename)
        stored_filename = safe_media_name(filename, ext)
        output_content = content
        persisted_content_type = "image/" + ext.lstrip(".")

    if resized:
        stored_filename = str(Path(stored_filename).with_suffix(".jpg"))

    target_path = unique_media_path(target_dir, stored_filename, output_content)
    target_path.write_bytes(output_content)
    stored_filename = target_path.name
    relative_path = f"media/observation-photos/{year}/{stored_filename}"

    return {
        "kind": "photo",
        "path": relative_path,
        "url": media_url(relative_path),
        "stored_filename": stored_filename,
        "original_filename": filename,
        "content_type": persisted_content_type,
        "size_bytes": target_path.stat().st_size,
        "resized": resized,
        "exif_preserved": exif_preserved,
        "variant": "display",
    }


def process_video(
    source_path: Path,
    target_dir: Path,
    observed_at: str | None = None,
) -> dict | None:
    """
    Convierte un vídeo con ffmpeg y lo guarda en target_dir.
    Devuelve el dict media entry o None si falla.
    """
    filename = source_path.name
    content = source_path.read_bytes()

    if len(content) > MEDIA_FILE_MAX_BYTES:
        raise ValueError(f"{filename} supera el límite de {MEDIA_FILE_MAX_BYTES // (1024*1024)} MB")

    year = media_year(observed_at)
    target_dir = target_dir / year
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = safe_media_name(filename, ".mp4")
    target_path = unique_media_path(target_dir, stored_filename, b"")

    scale = f"scale={VIDEO_MAX_WIDTH}:{VIDEO_MAX_HEIGHT}:force_original_aspect_ratio=decrease:force_divisible_by=2"
    cmd = [
        "ffmpeg", "-nostdin", "-y",
        "-i", str(source_path),
        "-t", str(VIDEO_MAX_SECONDS),
        "-vf", scale,
        "-c:v", "libx264", "-crf", str(VIDEO_CRF), "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(target_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        msg = (exc.stderr or exc.stdout or b"FFmpeg error").decode(errors="replace").strip()
        raise RuntimeError(f"FFmpeg falló para {filename}: {msg}") from exc

    relative_path = f"media/observation-videos/{year}/{target_path.name}"
    return {
        "kind": "video",
        "path": relative_path,
        "url": media_url(relative_path),
        "stored_filename": target_path.name,
        "original_filename": filename,
        "content_type": "video/mp4",
        "size_bytes": target_path.stat().st_size,
        "max_duration_seconds": VIDEO_MAX_SECONDS,
        "max_resolution": f"{VIDEO_MAX_WIDTH}x{VIDEO_MAX_HEIGHT}",
        "variant": "display",
    }


def process_media_file(
    source_path: Path,
    target_dir: Path,
    observed_at: str | None = None,
) -> dict | None:
    """Procesa imagen o vídeo según la extensión."""
    if is_video(source_path.name):
        return process_video(source_path, target_dir, observed_at)
    return process_image(source_path, target_dir, observed_at)
