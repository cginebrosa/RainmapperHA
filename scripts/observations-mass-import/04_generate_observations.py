#!/usr/bin/env python3
"""
Paso 10 del proceso de importación masiva de observaciones.

Genera objetos de observación Rainmapper con media procesada desde review_table.json
y los fusiona con mushroom_observations.json existente.

Reglas de generación:
  - species_mapping_status "no_profile", "unidentified", "multi_none" → se omiten
  - species_mapping_status "mapped" → 1 observación
  - species_mapping_status "multi_full" / "multi_partial" → 1 obs por species_id mapeado
  - micro_area_id null o "pending" → observación sin micro-área (micro_area_id: null)
  - calibration_use → "review" para todas
  - validation_status → del campo "confidence" de review_table.json
  - media → procesado con media_utils.py; idempotente (salta si el fichero ya existe)
  - multi-especie → la misma foto genera N observaciones que comparten la media entry

Uso:
    .venv/bin/python scripts/observations-mass-import/04_generate_observations.py \\
        --review-table "/ruta/a/candidates/review_table.json" \\
        --observations docker-data/mushroom-data/mushroom_observations.json \\
        --photos-dir "/Users/carlosginebrosa/Desktop/Fotos Bolets/candidates" \\
        --media-dir docker-data/mushroom-data \\
        --output "/ruta/a/candidates/mushroom_observations_merged.json"

    # Dry-run (no escribe nada ni procesa media):
    .venv/bin/python scripts/observations-mass-import/04_generate_observations.py \\
        --review-table "/ruta/a/candidates/review_table.json" \\
        --observations docker-data/mushroom-data/mushroom_observations.json \\
        --photos-dir "/Users/carlosginebrosa/Desktop/Fotos Bolets/candidates" \\
        --media-dir docker-data/mushroom-data \\
        --output "/ruta/a/candidates/mushroom_observations_merged.json" \\
        --dry-run
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date as date_type
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from media_utils import (
    IMAGE_MAX_EDGE, VIDEO_MAX_HEIGHT, VIDEO_MAX_SECONDS, VIDEO_MAX_WIDTH,
    is_video, media_url, media_year, process_image, process_video, safe_media_name,
)

SEASON_MAP = {12: "winter", 1: "winter", 2: "winter",
              3: "spring",  4: "spring",  5: "spring",
              6: "summer",  7: "summer",  8: "summer",
              9: "autumn",  10: "autumn", 11: "autumn"}

HEIC_SUFFIXES = {".heic", ".heif"}


def build_live_photo_mov_set(table):
    """
    Devuelve el conjunto de fnames .mov que son companion de una Live Photo HEIC
    (mismo folder + mismo stem). Estos MOVs no aportan nada útil y deben omitirse.
    """
    stems_with_heic = set()
    for row in table:
        fname = row.get("fname", "")
        folder = row.get("folder", "")
        if Path(fname).suffix.lower() in HEIC_SUFFIXES:
            stems_with_heic.add((folder, Path(fname).stem))
    live_movs = set()
    for row in table:
        fname = row.get("fname", "")
        folder = row.get("folder", "")
        if Path(fname).suffix.lower() == ".mov":
            if (folder, Path(fname).stem) in stems_with_heic:
                live_movs.add(fname)
    return live_movs

SKIP_STATUSES = {"no_profile", "unidentified", "multi_none"}

OBSERVER_NAME = "Carlos"
OBSERVER_EXPERTISE = "expert"
CREATED_BY = "mass_import"

REQUIRED_OBS_FIELDS = [
    "observation_id", "species_id", "observed_at", "validation_status",
    "calibration_use", "location", "observer", "source", "metadata",
]


def parse_alt(alt_raw):
    if alt_raw is None:
        return None
    try:
        return float(str(alt_raw).replace("m", "").strip())
    except (ValueError, TypeError):
        return None


def parse_date(date_str):
    if not date_str:
        return None, None, None
    try:
        parts = date_str.split("-")
        year, month = int(parts[0]), int(parts[1])
        return date_str, month, SEASON_MAP.get(month)
    except (IndexError, ValueError):
        return date_str, None, None


def build_existing_id_index(observations):
    existing_ids = set()
    date_seq = defaultdict(int)
    for o in observations:
        oid = o.get("observation_id", "")
        existing_ids.add(oid)
        parts = oid.split("_")
        if len(parts) == 3 and parts[0] == "obs":
            try:
                seq = int(parts[2])
                date_seq[parts[1]] = max(date_seq[parts[1]], seq)
            except ValueError:
                pass
    return existing_ids, date_seq


def next_obs_id(date_str, date_seq, existing_ids):
    date_key = date_str.replace("-", "") if date_str else "00000000"
    date_seq[date_key] += 1
    candidate = f"obs_{date_key}_{date_seq[date_key]:04d}"
    while candidate in existing_ids:
        date_seq[date_key] += 1
        candidate = f"obs_{date_key}_{date_seq[date_key]:04d}"
    existing_ids.add(candidate)
    return candidate


def reconstruct_media_entry(existing_path: Path, fname: str, year: str, vid: bool) -> dict:
    """Reconstruye un media entry desde un fichero ya procesado."""
    rel_type = "observation-videos" if vid else "observation-photos"
    relative = f"media/{rel_type}/{year}/{existing_path.name}"
    if vid:
        return {
            "kind": "video",
            "path": relative,
            "url": media_url(relative),
            "stored_filename": existing_path.name,
            "original_filename": fname,
            "content_type": "video/mp4",
            "size_bytes": existing_path.stat().st_size,
            "max_duration_seconds": VIDEO_MAX_SECONDS,
            "max_resolution": f"{VIDEO_MAX_WIDTH}x{VIDEO_MAX_HEIGHT}",
            "variant": "display",
        }
    return {
        "kind": "photo",
        "path": relative,
        "url": media_url(relative),
        "stored_filename": existing_path.name,
        "original_filename": fname,
        "content_type": "image/jpeg",
        "size_bytes": existing_path.stat().st_size,
        "resized": True,
        "exif_preserved": True,
        "variant": "display",
    }


def get_or_process_media(fname, folder, photos_dir, media_base_dir, observed_at, media_cache, dry_run):
    """
    Idempotente: si el fichero procesado ya existe en media/, reconstruye el entry.
    Si no, lo procesa. En dry-run no hace nada y devuelve None.
    """
    cache_key = (fname, folder)
    if cache_key in media_cache:
        return media_cache[cache_key]

    source_path = Path(photos_dir) / folder / fname
    if not source_path.exists():
        print(f"  [WARN] Fichero fuente no encontrado: {source_path}", file=sys.stderr)
        media_cache[cache_key] = None
        return None

    vid = is_video(fname)
    subdir = "observation-videos" if vid else "observation-photos"
    target_dir = Path(media_base_dir) / "media" / subdir
    ext = ".mp4" if vid else ".jpg"
    year = media_year(observed_at)
    expected_name = safe_media_name(fname, ext)
    existing_path = target_dir / year / expected_name

    if existing_path.exists():
        entry = reconstruct_media_entry(existing_path, fname, year, vid)
        media_cache[cache_key] = entry
        return entry

    if dry_run:
        media_cache[cache_key] = None
        return None

    try:
        if vid:
            entry = process_video(source_path, target_dir, observed_at)
        else:
            entry = process_image(source_path, target_dir, observed_at)
        media_cache[cache_key] = entry
        return entry
    except Exception as exc:
        print(f"  [ERROR] Media fallida para {fname}: {exc}", file=sys.stderr)
        media_cache[cache_key] = None
        return None


def build_observation(row, species_id, obs_id, today_str, media_entry):
    date_str, month, season = parse_date(row.get("date"))
    alt = parse_alt(row.get("alt"))
    lat = row.get("lat")
    lon = row.get("lon")
    mid = row.get("micro_area_id")
    if mid == "pending":
        mid = None

    return {
        "observation_id": obs_id,
        "species_id": species_id,
        "micro_area_id": mid,
        "observed_at": date_str,
        "location": {
            "input": f"{lat}, {lon}" if lat is not None and lon is not None else "",
            "lat": lat,
            "lon": lon,
            "source": "photo_exif",
            "precision_m": None,
        },
        "flush_abundance": None,
        "observer": {
            "name": OBSERVER_NAME,
            "expertise": OBSERVER_EXPERTISE,
        },
        "source": {
            "type": "photo_exif",
            "label": row.get("fname", ""),
            "url": "",
            "notes": row.get("notes", "") or "",
        },
        "source_quality": 1,
        "validation_status": row.get("confidence", "draft"),
        "calibration_use": "review",
        "calibration_exclusion_reason": None,
        "site_context": {
            "observed_host_ids": row.get("observed_host_ids") or [],
            "observed_forest_type_ids": row.get("observed_forest_type_ids") or [],
            "observed_soil_tendency_ids": row.get("observed_soil_tendency_ids") or [],
            "observed_habitat_feature_ids": row.get("observed_habitat_feature_ids") or [],
            "observed_aspect_ids": row.get("observed_aspect_ids") or [],
            "habitat_notes": "",
            "host_notes": "",
            "soil_notes": "",
            "aspect_notes": "",
        },
        "metadata": {
            "created_at": today_str,
            "updated_at": today_str,
            "created_by": CREATED_BY,
            "updated_by": CREATED_BY,
        },
        "altitude": {
            "meters": alt,
            "source": "photo_exif" if alt is not None else None,
            "resolved_at": today_str if alt is not None else None,
        },
        "media": [media_entry] if media_entry else [],
        "derived": {
            "month": month,
            "season": season,
        },
    }


def validate_new_observations(new_observations, existing_ids_before, valid_species_ids):
    errors = []
    seen_new = set()
    for obs in new_observations:
        oid = obs.get("observation_id", "")
        if not oid:
            errors.append(f"Observación sin observation_id: species={obs.get('species_id')}")
            continue
        if oid in existing_ids_before:
            errors.append(f"ID duplicado con existente: {oid}")
        if oid in seen_new:
            errors.append(f"ID duplicado entre nuevas: {oid}")
        seen_new.add(oid)
        for field in REQUIRED_OBS_FIELDS:
            if obs.get(field) is None and field not in {"micro_area_id"}:
                errors.append(f"{oid}: campo requerido ausente: {field}")
        sid = obs.get("species_id", "")
        if valid_species_ids and sid not in valid_species_ids:
            errors.append(f"{oid}: species_id desconocido: {sid}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Genera y fusiona observations desde review_table.json")
    parser.add_argument("--review-table", required=True, help="Ruta a review_table.json")
    parser.add_argument("--observations", required=True, help="Ruta a mushroom_observations.json")
    parser.add_argument("--photos-dir", required=True, help="Directorio raíz de las fotos (contiene <folder>/<fname>)")
    parser.add_argument("--media-dir", required=True, help="Directorio base de mushroom-data (contiene media/)")
    parser.add_argument("--output", required=True, help="Ruta del fichero de salida fusionado")
    parser.add_argument("--profiles", default=None, help="Ruta a mushroom_profiles.json (para validar species_ids)")
    parser.add_argument("--dry-run", action="store_true", help="No escribir fichero ni procesar media")
    args = parser.parse_args()

    with open(args.review_table) as f:
        table = json.load(f)
    with open(args.observations) as f:
        obs_data = json.load(f)

    valid_species_ids = set()
    if args.profiles:
        with open(args.profiles) as f:
            profiles_data = json.load(f)
        for p in profiles_data.get("species_profiles", []):
            sid = p.get("species_id")
            if sid:
                valid_species_ids.add(sid)

    today_str = date_type.today().isoformat()
    existing_obs = obs_data.get("observations", [])
    existing_ids_snapshot = {o.get("observation_id") for o in existing_obs}
    existing_ids, date_seq = build_existing_id_index(existing_obs)

    live_photo_movs = build_live_photo_mov_set(table)
    print(f"MOVs Live Photo companion detectados (se omitirán): {len(live_photo_movs)}")

    new_observations = []
    media_cache = {}
    stats = {
        "generated": 0,
        "skipped_no_profile": 0,
        "skipped_unidentified": 0,
        "skipped_live_photo_mov": 0,
        "multi_expanded": 0,
        "media_ok": 0,
        "media_cached": 0,
        "media_missing": 0,
        "media_error": 0,
    }

    total = len(table)
    for i, row in enumerate(table, 1):
        if i % 100 == 0 or i == total:
            print(f"  Procesando {i}/{total}...", file=sys.stderr)

        status = row.get("species_mapping_status", "")
        species_ids = row.get("species_ids") or []

        if status in SKIP_STATUSES:
            if status == "unidentified":
                stats["skipped_unidentified"] += 1
            else:
                stats["skipped_no_profile"] += 1
            continue

        if row.get("fname", "") in live_photo_movs:
            stats["skipped_live_photo_mov"] += 1
            continue

        if not species_ids:
            stats["skipped_no_profile"] += 1
            continue

        fname = row.get("fname", "")
        folder = row.get("folder", "")
        observed_at = row.get("date")
        cache_key = (fname, folder)

        media_entry = get_or_process_media(
            fname, folder, args.photos_dir, args.media_dir,
            observed_at, media_cache, args.dry_run,
        )

        if cache_key in media_cache:
            if media_entry is not None:
                if media_entry.get("size_bytes") and not args.dry_run:
                    stats["media_ok"] += 1
            else:
                stats["media_missing"] += 1
        else:
            stats["media_error"] += 1

        for species_id in species_ids:
            obs_id = next_obs_id(row.get("date"), date_seq, existing_ids)
            obs = build_observation(row, species_id, obs_id, today_str, media_entry)
            new_observations.append(obs)
            stats["generated"] += 1
            if len(species_ids) > 1:
                stats["multi_expanded"] += 1

    print(f"\nObservaciones generadas:         {stats['generated']}")
    print(f"  de las cuales multi-especie:   {stats['multi_expanded']}")
    print(f"Omitidas sin perfil:             {stats['skipped_no_profile']}")
    print(f"Omitidas no identificadas:       {stats['skipped_unidentified']}")
    print(f"Omitidas MOV Live Photo:         {stats['skipped_live_photo_mov']}")
    if not args.dry_run:
        print(f"Media procesada:                 {stats['media_ok']}")
        print(f"Media ya existente (skip):       {stats['media_cached']}")
        print(f"Media sin fichero fuente:        {stats['media_missing']}")

    print(f"\nValidando {len(new_observations)} observaciones nuevas...")
    errors = validate_new_observations(new_observations, existing_ids_snapshot, valid_species_ids)
    if errors:
        print(f"\n[ERROR] Validación fallida ({len(errors)} errores):")
        for e in errors[:20]:
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  ... y {len(errors) - 20} más.")
        sys.exit(1)
    print("Validación OK.")

    if args.dry_run:
        print("\nDry-run: no se ha escrito nada.")
        return

    merged_obs = existing_obs + new_observations
    merged = dict(obs_data)
    merged["observations"] = merged_obs
    merged.setdefault("metadata", {})
    merged["metadata"]["updated_at"] = today_str
    merged["metadata"]["updated_by"] = CREATED_BY

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    tmp_path.rename(output_path)

    print(f"\nEscrito: {output_path}")
    print(f"  Observaciones existentes: {len(existing_obs)}")
    print(f"  Observaciones nuevas:     {len(new_observations)}")
    print(f"  Total fusionado:          {len(merged_obs)}")


if __name__ == "__main__":
    main()
