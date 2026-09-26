"""Bounded GBIF packages, explicit GIS preparation and optional site planning."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import stat
import struct
import uuid
import zipfile
from datetime import date, datetime, UTC
from pathlib import Path
from urllib.parse import urlencode

from PIL import Image

from rainmapper_core.mushroom_observations import finalize_observation_payload
from rainmapper_core.mushroom_store import write_json_atomic

MAX_PACKAGE_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 100
MAX_ASSETS = 1000
MAX_OBSERVATIONS_BYTES = 16 * 1024 * 1024
MAX_OBSERVATIONS = 10000
SCHEMA = "rainmapper-gbif-observations"
HASH = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[0-9]{1,24}$")


class ImportError(ValueError):
    """A stable message code for the translated maintenance UI."""


def finite_number(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and low <= value <= high


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ImportError("invalid")
            result[key] = value
        return result
    def constant(_):
        raise ImportError("invalid")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def normalize_record(record, export, assets, species_ids):
    """Construct trusted operational fields; never accept status/paths from a package."""
    if not isinstance(record, dict) or not ID.fullmatch(str(record.get("gbif_id", ""))):
        raise ImportError("invalid")
    gbif_id = str(record["gbif_id"])
    if record.get("species_id") not in species_ids:
        raise ImportError("species")
    observed_at = record.get("observed_at")
    try:
        if not isinstance(observed_at, str) or date.fromisoformat(observed_at).isoformat() != observed_at:
            raise ValueError()
    except (TypeError, ValueError):
        raise ImportError("date") from None
    original = record.get("original")
    if not isinstance(original, dict) or len(json.dumps(original).encode()) > 32768:
        raise ImportError("invalid")
    # Unknown and interval dates must be resolved in the source, never fabricated.
    event_date = original.get("eventDate", "")
    if not isinstance(event_date, str) or "/" in event_date or event_date[:10] != observed_at:
        raise ImportError("date")
    if original.get("occurrenceStatus", "PRESENT") not in (None, "", "PRESENT", "present"):
        raise ImportError("presence")
    lat, lon = record.get("lat"), record.get("lon")
    if not finite_number(lat, -90, 90) or not finite_number(lon, -180, 180):
        raise ImportError("coordinates")
    uncertainty = record.get("coordinate_uncertainty_m")
    if uncertainty is not None and (not finite_number(uncertainty, 0, 40075017) or uncertainty == 0):
        raise ImportError("uncertainty")
    photos = record.get("photos", [])
    if not isinstance(photos, list) or len(photos) > 50:
        raise ImportError("invalid")
    media = []
    for photo in photos:
        if not isinstance(photo, dict) or photo.get("asset") not in assets:
            raise ImportError("photo")
        asset = assets[photo["asset"]]
        attribution = {key: photo.get(key) for key in ("identifier", "references", "creator", "publisher", "license", "rightsHolder", "created")}
        if any(value is not None and (not isinstance(value, str) or len(value) > 4096) for value in attribution.values()):
            raise ImportError("invalid")
        relative = f"media/observation-photos/gbif/{asset['sha256']}.{asset['extension']}"
        media.append({"kind": "photo", "path": relative,
                      "url": "./observation-media?" + urlencode({"path": relative}),
                      "stored_filename": Path(relative).name, "original_filename": Path(relative).name,
                      "content_type": asset["content_type"], "size_bytes": asset["bytes"],
                      "sha256": asset["sha256"], "resized": False, "variant": "original",
                      "attribution": attribution})
    provenance = record.get("source_export", export)
    if (not isinstance(provenance, dict) or not HASH.fullmatch(str(provenance.get("snapshot_sha256", "")))
            or not isinstance(provenance.get("batch_id"), str)
            or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", provenance["batch_id"])):
        raise ImportError("invalid")
    now = datetime.now(UTC).isoformat()
    external = {"provider": "gbif", "gbif_id": gbif_id,
                "coordinate_uncertainty_m": uncertainty, "uncertainty_assumed": uncertainty is None,
                "original": original, "viewer_review": record.get("review"),
                "snapshot_sha256": provenance["snapshot_sha256"], "batch_id": provenance["batch_id"],
                "imported_at": now, "abundance_assigned": "normal", "quality_assigned": 0.75}
    geography = record.get("geography")
    altitude = None
    if geography is not None:
        if not isinstance(geography, dict) or len(json.dumps(geography).encode()) > 8192:
            raise ImportError("invalid")
        if geography.get("latitude") != lat or geography.get("longitude") != lon:
            raise ImportError("coordinates")
        external["geography"] = geography
        elevation = geography.get("elevation") or {}
        if elevation.get("status") == "available":
            if not finite_number(elevation.get("value_m"), -500, 9000):
                raise ImportError("coordinates")
            if elevation.get("source_id") == "dem_5m" and finite_number(elevation.get("resolution_m"), 0.01, 10000):
                altitude = {"meters": elevation["value_m"], "source": "dem", "source_id": "dem_5m",
                            "resolution_m": elevation["resolution_m"], "resolved_at": now[:10]}
    observation = {
        "observation_id": "obs_gbif_" + gbif_id, "species_id": record["species_id"],
        "micro_area_id": None, "observed_at": observed_at,
        "location": {"input": f"{lat}, {lon}", "lat": lat, "lon": lon, "source": "gbif",
                     "precision_m": uncertainty if uncertainty is not None else 500,
                     "precision_origin": "declared" if uncertainty is not None else "assumed_unknown_500m"},
        "observer": {"name": "GBIF", "expertise": "unknown"},
        "source": {"type": "gbif", "label": "GBIF", "url": f"https://www.gbif.org/occurrence/{gbif_id}", "notes": ""},
        "flush_abundance": "normal", "source_quality": 0.75,
        "validation_status": "draft", "calibration_use": "review", "calibration_exclusion_reason": None,
        "site_context": {"observed_host_ids": [], "observed_forest_type_ids": [],
                         "observed_soil_tendency_ids": [], "observed_habitat_feature_ids": [],
                         "observed_aspect_ids": [], "habitat_notes": str(original.get("habitat") or ""),
                         "host_notes": "", "soil_notes": "", "aspect_notes": ""},
        "metadata": {"created_at": now[:10], "updated_at": now[:10], "created_by": "gbif_import", "updated_by": "gbif_import"},
        "external_source": external, "media": media,
    }
    if altitude:
        observation["altitude"] = altitude
    return finalize_observation_payload(observation)


def inspect_package(path, species_ids):
    """Validate stored ZIP and images sequentially, keeping only bounded metadata."""
    if path.stat().st_size > MAX_PACKAGE_BYTES:
        raise ImportError("limit")
    # Bound central-directory allocation before ZipFile materializes its entries.
    with path.open("rb") as source:
        source.seek(max(0, path.stat().st_size - 65557))
        tail = source.read()
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise ImportError("invalid")
    _, disk, central_disk, disk_entries, count, central_bytes, _, comment = struct.unpack_from("<4s4H2IH", tail, offset)
    if disk or central_disk or disk_entries != count or count > MAX_ASSETS + 1 or central_bytes > 256 * 1024 or offset + 22 + comment != len(tail):
        raise ImportError("limit")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ASSETS + 1 or len({i.filename for i in infos}) != len(infos):
            raise ImportError("invalid")
        total = 0
        for info in infos:
            if (info.compress_type != zipfile.ZIP_STORED or info.flag_bits & 1
                    or stat.S_ISLNK(info.external_attr >> 16)
                    or not (info.filename == "manifest.json" or re.fullmatch(r"media/[0-9a-f]{64}", info.filename))):
                raise ImportError("invalid")
            if info.file_size > (MAX_MANIFEST_BYTES if info.filename == "manifest.json" else MAX_PHOTO_BYTES):
                raise ImportError("limit")
            total += info.file_size
        if total > MAX_PACKAGE_BYTES:
            raise ImportError("limit")
        manifest = strict_json(archive.read("manifest.json"))
        if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA or manifest.get("version") != 1:
            raise ImportError("invalid")
        export, records, assets = manifest.get("export"), manifest.get("records"), manifest.get("assets")
        if (not isinstance(export, dict) or not HASH.fullmatch(str(export.get("snapshot_sha256", "")))
                or not isinstance(export.get("batch_id"), str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", export["batch_id"])
                or not isinstance(records, list) or not 1 <= len(records) <= MAX_RECORDS
                or not isinstance(assets, dict) or len(assets) > MAX_ASSETS):
            raise ImportError("invalid")
        if {i.filename for i in infos} != {"manifest.json", *("media/" + key for key in assets)}:
            raise ImportError("invalid")
        for key, asset in assets.items():
            if not HASH.fullmatch(key) or not isinstance(asset, dict) or asset.get("bytes") != archive.getinfo("media/" + key).file_size:
                raise ImportError("photo")
            digest = hashlib.sha256()
            with archive.open("media/" + key) as source:
                while block := source.read(256 * 1024):
                    digest.update(block)
            if digest.hexdigest() != key:
                raise ImportError("photo")
            with archive.open("media/" + key) as source, Image.open(source) as img:
                if img.format not in {"JPEG", "PNG", "WEBP"} or img.width * img.height > 40000000:
                    raise ImportError("photo")
                fmt = img.format
                img.verify()
            asset.update(sha256=key, extension={"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[fmt],
                         content_type={"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[fmt])
        seen, rows = set(), []
        for record in records:
            try:
                row = normalize_record(record, export, assets, species_ids)
                gid = row["external_source"]["gbif_id"]
                if gid in seen:
                    raise ImportError("invalid")
                seen.add(gid)
                rows.append({"gbif_id": gid, "observation": row})
            except ImportError as exc:
                rows.append({"gbif_id": str(record.get("gbif_id", "")) if isinstance(record, dict) else "", "error": str(exc)})
        # Assets belonging to invalid records may remain in the package, but are never installed.
        return {"export": export, "rows": rows, "assets": assets}


def identity_index(rows):
    ids, occurrences = {}, {}
    for row in rows:
        external = row.get("external_source") or {}
        if external.get("is_copy"):
            continue
        source_url = str((row.get("source") or {}).get("url") or "").rstrip("/")
        match = re.fullmatch(r"https?://(?:www\.)?gbif\.org/occurrence/([0-9]+)", source_url)
        gid = str(external.get("gbif_id", "")) if external.get("provider") == "gbif" else (match[1] if match else "")
        if gid:
            ids[gid] = row["observation_id"]
        if source_url:
            occurrences[("url", source_url)] = row["observation_id"]
        original = external.get("original") or {}
        for key in ("occurrenceID", "references"):
            value = original.get(key)
            if value:
                occurrences[("url", str(value).rstrip("/"))] = row["observation_id"]
    return ids, occurrences


def observation_revision(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def preview(package, existing, archived=()):
    active_by_id = {row["observation_id"]: row for row in existing}
    archived_by_id = {row["observation_id"]: row for row in archived}
    archived_ids = set(archived_by_id)
    existing = list(existing) + list(archived)
    ids, occurrences = identity_index(existing)
    observation_ids = {r.get("observation_id") for r in existing}
    identity_counts = {}
    for old in existing:
        for gid in identity_index([old])[0]:
            identity_counts[gid] = identity_counts.get(gid, 0) + 1
    result = []
    for item in package["rows"]:
        entry = {"gbif_id": item["gbif_id"], "status": "invalid", "error": item.get("error", "")}
        row = item.get("observation")
        if row:
            ext = row["external_source"]
            duplicate = ids.get(item["gbif_id"]) or (row["observation_id"] if row["observation_id"] in observation_ids else None)
            conflict = next((occurrences[("url", str(ext["original"][key]).rstrip("/"))] for key in ("occurrenceID", "references")
                             if ext["original"].get(key) and ("url", str(ext["original"][key]).rstrip("/")) in occurrences), None)
            entry.update(status="duplicate" if duplicate else "conflict" if conflict else "new",
                         existing_id=duplicate or conflict, species_id=row["species_id"], observed_at=row["observed_at"],
                         species_name=ext["original"].get("acceptedScientificName") or ext["original"].get("scientificName") or row["species_id"],
                         precision_m=row["location"]["precision_m"], assumed=ext["uncertainty_assumed"],
                         photos=len(row["media"]), unlicensed=sum(not p["attribution"].get("license") for p in row["media"]))
            if duplicate:
                previous = active_by_id.get(duplicate) or archived_by_id.get(duplicate)
                # Ambiguous identities must be resolved before replacing.
                entry["replaceable"] = bool(previous and identity_counts.get(item["gbif_id"]) == 1)
                entry["archived"] = duplicate in archived_ids
                if previous:
                    entry["existing_revision"] = observation_revision(previous)
                    entry["existing_status"] = previous.get("validation_status")
            if entry["status"] == "new":
                for key in ("occurrenceID", "references"):
                    if ext["original"].get(key):
                        occurrences[("url", str(ext["original"][key]).rstrip("/"))] = row["observation_id"]
        result.append(entry)
    return result


def stage_root(store):
    return Path(store.data_dir) / ".gbif-imports"


def stage_path(store, token):
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ImportError("invalid")
    return stage_root(store) / token


def receive(store, chunks, owner):
    root = stage_root(store)
    root.mkdir(parents=True, exist_ok=True)
    # At most two pending uploads; old staging is offered for explicit cancellation.
    if sum(1 for p in root.iterdir() if p.is_dir() and (p / "package.zip").exists()) >= 2:
        raise ImportError("staging")
    if shutil.disk_usage(root).free < MAX_PACKAGE_BYTES * 3:
        raise ImportError("space")
    token = uuid.uuid4().hex
    target = root / token
    target.mkdir()
    try:
        write_json_atomic(target / "state.json", {"owner": owner, "status": "uploading"})
        total = 0
        with (target / "package.zip").open("xb") as output:
            for block in chunks:
                total += len(block)
                if total > MAX_PACKAGE_BYTES:
                    raise ImportError("limit")
                output.write(block)
        species_ids = {r["species_id"] for r in store.load("profiles")["species_profiles"]}
        package = inspect_package(target / "package.zip", species_ids)
        write_json_atomic(target / "preview.json", package)
        write_json_atomic(target / "state.json", {"owner": owner, "status": "ready"})
        return token, package
    except Exception:
        shutil.rmtree(target)
        raise


def load_stage(store, token, owner):
    target = stage_path(store, token)
    state = strict_json((target / "state.json").read_bytes())
    if state.get("owner") != owner:
        raise ImportError("owner")
    return target, state


def assign_known_micro_area(row, sites):
    """Assign only a unique active polygon containing the point (respect holes)."""
    from rainmapper_core.mushroom_known_sites import point_in_geometry
    lat, lon = row["location"]["lat"], row["location"]["lon"]
    active_areas = {a["area_id"] for a in sites.get("areas", []) if not a.get("archived")}
    matches = []
    for site in sites.get("micro_areas", []):
        if site.get("archived") or site.get("area_id") not in active_areas:
            continue
        geometry = site.get("geometry") or {}
        polygons = [geometry.get("coordinates", [])] if geometry.get("type") == "Polygon" else geometry.get("coordinates", []) if geometry.get("type") == "MultiPolygon" else []
        for polygon in polygons:
            if polygon and point_in_geometry(lon, lat, {"type": "Polygon", "coordinates": [polygon[0]]}) and not any(
                    point_in_geometry(lon, lat, {"type": "Polygon", "coordinates": [hole]}) for hole in polygon[1:]):
                matches.append(site["micro_area_id"])
                break
    matches = sorted(set(matches))
    if len(matches) > 1:
        from .mushroom_gbif_sites import geometry_plan
        gid = row["external_source"].get("gbif_id", "0")
        assignment = geometry_plan(sites, [{"gbif_id": gid, "lat": lat, "lon": lon}], create=False)["assignments"][gid]
        row["micro_area_id"] = assignment["micro_area_id"]
        row["external_source"]["site_assignment"] = assignment
        return
    row["micro_area_id"] = matches[0] if len(matches) == 1 else None
    row["external_source"]["site_assignment"] = {
        "status": "assigned" if len(matches) == 1 else "ambiguous" if matches else "not_found",
        "micro_area_id": row["micro_area_id"], "candidates": matches[:16],
        "checked_at": datetime.now(UTC).isoformat(),
    }


def known_sites(store):
    path = Path(store.data_dir) / "mushroom_known_sites.json"
    return strict_json(path.read_bytes()) if path.exists() else {"areas": [], "micro_areas": []}


def staged_package(target):
    package = strict_json((target / "preview.json").read_bytes())
    for item in package["rows"]:
        if "observation" not in item or not ID.fullmatch(item["gbif_id"]):
            continue
        prepared_path = target / "prepared" / (item["gbif_id"] + ".json")
        if not prepared_path.exists():
            continue
        prepared = strict_json(prepared_path.read_bytes())
        row = item["observation"]
        row["site_context"]["gis_recovery"] = prepared["gis_recovery"]
        if prepared.get("altitude"):
            row["altitude"] = prepared["altitude"]
        row["micro_area_id"] = prepared["micro_area_id"]
        row["external_source"]["site_assignment"] = prepared["site_assignment"]
        item.update(prepared=True, gis_gaps=prepared["gis_gaps"])
    return package


def prepare_record(store, token, owner, gbif_id):
    """Recover one selected citation at a time; staged progress survives retries."""
    from rainmapper_core import mushroom_gis_recovery as gis
    target, state = load_stage(store, token, owner)
    if state.get("status") != "ready":
        raise ImportError("invalid")
    if not isinstance(gbif_id, str) or not ID.fullmatch(gbif_id):
        raise ImportError("invalid")
    prepared_path = target / "prepared" / (gbif_id + ".json")
    if prepared_path.exists():
        saved = strict_json(prepared_path.read_bytes())
        return {"gbif_id": gbif_id, "gis_gaps": saved["gis_gaps"],
                "micro_area_id": saved["micro_area_id"], "site_status": saved["site_assignment"]["status"]}
    package = strict_json((target / "preview.json").read_bytes())
    item = next((item for item in package["rows"] if item["gbif_id"] == gbif_id and "observation" in item), None)
    if not item:
        raise ImportError("invalid")
    row = item["observation"]
    if not item.get("prepared"):
        location = row["location"]
        try:
            report = gis.observation_preview(location["lat"], location["lon"], store.load("gis"), store.load("catalogs"))
            report = gis.valid_recovery(report, location)
            if not report:
                raise ValueError("invalid_recovery")
        except Exception as error:
            report = {"version": 1, "location": gis.point(location["lat"], location["lon"]),
                      "recovered_at": datetime.now(UTC).isoformat(), "values": {}, "sources": {},
                      "forest": {"status": "unavailable"}, "gaps": ["gis_recovery_unavailable"],
                      "error_type": type(error).__name__}
        report["recovery_mode"] = "gbif_import"
        row["site_context"]["gis_recovery"] = report
        altitude = report.get("altitude_m")
        if finite_number(altitude, -500, 9000):
            row["altitude"] = {"meters": altitude, "source": "dem", "source_id": report.get("altitude_source", "dem_5m"),
                               "resolved_at": datetime.now(UTC).date().isoformat()}
        assign_known_micro_area(row, known_sites(store))
        item["prepared"] = True
        item["gis_gaps"] = bool(report.get("gaps") or any(not report.get("values", {}).get(field) for field in gis.FIELDS) or report.get("forest", {}).get("status") not in {"available", "no_trees_recorded"})
        # Persist only this citation's small recovery patch, never rewrite the batch per record.
        prepared_path.parent.mkdir(exist_ok=True)
        write_json_atomic(prepared_path, {"gis_recovery": report, "altitude": row.get("altitude"),
                          "micro_area_id": row.get("micro_area_id"),
                          "site_assignment": row["external_source"]["site_assignment"], "gis_gaps": item["gis_gaps"]})
    return {"gbif_id": gbif_id, "gis_gaps": item.get("gis_gaps", False),
            "micro_area_id": row.get("micro_area_id"),
            "site_status": row["external_source"].get("site_assignment", {}).get("status", "not_found")}


def finish_restorations(store, target, token):
    """Remove restored archive rows after active write; safe to retry after a crash."""
    journal_path = target / "restored.json"
    if not journal_path.exists():
        return
    planned = strict_json(journal_path.read_bytes())
    archive_path = Path(store.data_dir) / "archived/mushroom_observations_archived.json"
    if not archive_path.exists():
        return
    payload = strict_json(archive_path.read_bytes())
    active = {row["observation_id"]: row for row in store.load("observations")["observations"]}
    remove = set()
    for row in payload["observations"]:
        oid = row["observation_id"]
        if oid in planned and (active.get(oid, {}).get("external_source") or {}).get("import_token") == token:
            if observation_revision(row) != planned[oid]:
                raise ImportError("changed")
            remove.add(oid)
    if remove:
        backup = target / "archive-before.json"
        if not backup.exists():
            shutil.copyfile(archive_path, backup)
        payload["observations"] = [row for row in payload["observations"] if row["observation_id"] not in remove]
        payload.setdefault("metadata", {})["updated_at"] = datetime.now(UTC).date().isoformat()
        write_json_atomic(archive_path, payload)


def cancel(store, token, owner):
    target, _ = load_stage(store, token, owner)
    from . import mushroom_gbif_sites
    mushroom_gbif_sites.recover(store, target)
    finish_restorations(store, target, token)
    journal = target / "installed.json"
    if journal.exists():
        active = store.load("observations")["observations"]
        archive = Path(store.data_dir) / "archived/mushroom_observations_archived.json"
        archived = strict_json(archive.read_bytes())["observations"] if archive.exists() else []
        references = {p.get("path") for r in active + archived for p in r.get("media", [])}
        for relative, digest in strict_json(journal.read_bytes()).items():
            if relative in references or not re.fullmatch(r"media/observation-photos/gbif/[0-9a-f]{64}\.(jpg|png|webp)", relative):
                continue
            media_path = Path(store.data_dir) / relative
            if media_path.exists():
                with media_path.open("rb") as source:
                    matches = hashlib.file_digest(source, "sha256").hexdigest() == digest
                if matches:
                    media_path.unlink()
    if (target / "archive-before.json").exists():
        backup = store.backup_dir() / ("gbif-archive-" + token + ".json")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target / "archive-before.json", backup)
    shutil.rmtree(target)


def commit(store, token, owner, accepted, archived, replacements=None, *, require_prepared=False, sites_plan_id=None, site_names=None):
    from .mushroom_known_sites import MUTATION_LOCK
    with MUTATION_LOCK:
        return _commit(store, token, owner, accepted, archived, replacements, require_prepared=require_prepared,
                       sites_plan_id=sites_plan_id, site_names=site_names)


def _commit(store, token, owner, accepted, archived, replacements=None, *, require_prepared=False, sites_plan_id=None, site_names=None):
    """Caller holds the same mutation lock as manual observation edits."""
    target, state = load_stage(store, token, owner)
    if state.get("status") == "complete":
        return state["result"]
    from . import mushroom_gbif_sites
    site_counts = mushroom_gbif_sites.recover(store, target)
    package = staged_package(target)
    if not isinstance(accepted, list) or len(accepted) > MAX_RECORDS or any(not isinstance(v, str) for v in accepted) or len(set(accepted)) != len(accepted):
        raise ImportError("invalid")
    replacements = {} if replacements is None else replacements
    if (not isinstance(replacements, dict) or len(replacements) > MAX_RECORDS
            or any(not isinstance(gid, str) or not isinstance(revision, str) or not HASH.fullmatch(revision)
                   for gid, revision in replacements.items()) or set(accepted) & set(replacements)):
        raise ImportError("invalid")
    active_path = store.current_path("observations")
    if active_path.stat().st_size > MAX_OBSERVATIONS_BYTES:
        raise ImportError("limit")
    payload = store.load("observations")
    rows = payload["observations"]
    current = preview(package, rows, archived)
    by_id = {r["gbif_id"]: r for r in current}
    if any(gid not in by_id or by_id[gid]["status"] not in {"new", "duplicate"} for gid in accepted):
        raise ImportError("conflict")
    # A concurrent import or a retry after the atomic write is safely skipped.
    selected = {gid for gid in accepted if by_id[gid]["status"] == "new"}
    additions = [i["observation"] for i in package["rows"] if i["gbif_id"] in selected and "observation" in i]
    active = {row["observation_id"]: row for row in rows}
    incoming = {item["gbif_id"]: item["observation"] for item in package["rows"] if "observation" in item}
    updates = {}
    restored = {}
    archived_by_id = {row["observation_id"]: row for row in archived}
    retried = 0
    for gid, revision in replacements.items():
        match = by_id.get(gid, {})
        previous = active.get(match.get("existing_id")) or archived_by_id.get(match.get("existing_id"))
        if previous and (previous.get("external_source") or {}).get("import_token") == token:
            retried += 1
            continue
        if not match.get("replaceable") or previous is None:
            raise ImportError("conflict")
        if observation_revision(previous) != revision:
            raise ImportError("changed")
        replacement = copy.deepcopy(incoming[gid])
        replacement["observation_id"] = previous["observation_id"]
        for field in ("created_at", "created_by"):
            if field in (previous.get("metadata") or {}):
                replacement["metadata"][field] = previous["metadata"][field]
        replacement["external_source"]["import_token"] = token
        if previous["observation_id"] in archived_by_id:
            restored[previous["observation_id"]] = revision
        updates[previous["observation_id"]] = replacement
    if require_prepared:
        wanted = selected | set(replacements)
        if any(item["gbif_id"] in wanted and not item.get("prepared") for item in package["rows"]):
            raise ImportError("preparation")
    sites = known_sites(store)
    writes = additions + list(updates.values())
    sites_plan = None
    if sites_plan_id and writes:
        sites_plan = mushroom_gbif_sites.apply_plan(store, target, sites_plan_id, accepted, replacements, writes, site_names or {})
    for row in writes:
        row["external_source"]["import_token"] = token
    for row in ([] if sites_plan else writes):
        if (row.get("site_context") or {}).get("gis_recovery"):
            assign_known_micro_area(row, sites)
    payload["observations"] = [updates.get(row["observation_id"], row) for row in rows] + additions + [updates[oid] for oid in restored]
    writes = additions + list(updates.values())
    if len(payload["observations"]) > MAX_OBSERVATIONS:
        raise ImportError("limit")
    # Count via iterencode before store.replace serializes a full candidate.
    size = 1
    for chunk in json.JSONEncoder(ensure_ascii=False, indent=2).iterencode(payload):
        size += len(chunk.encode())
        if size > MAX_OBSERVATIONS_BYTES:
            raise ImportError("limit")
    # Revalidate species and all operational data before writing a single media file.
    errors, _ = store.validate_candidate("observations", payload)
    if errors:
        raise ImportError("validation")
    if shutil.disk_usage(store.data_dir).free < MAX_PACKAGE_BYTES + 3 * size:
        raise ImportError("space")
    installed = set()
    journal_path = target / "installed.json"
    journal = strict_json(journal_path.read_bytes()) if journal_path.exists() else {}
    for row in writes:
        for photo in row["media"]:
            if not (Path(store.data_dir) / photo["path"]).exists():
                journal[photo["path"]] = photo["sha256"]
    # One bounded journal write per batch, not a growing rewrite per photo.
    write_json_atomic(journal_path, journal)
    with zipfile.ZipFile(target / "package.zip") as archive:
        for row in writes:
            for photo in row["media"]:
                relative = photo["path"]
                if relative in installed:
                    continue
                installed.add(relative)
                destination = Path(store.data_dir) / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    with destination.open("rb") as source:
                        actual = hashlib.file_digest(source, "sha256").hexdigest()
                    if actual != photo["sha256"]:
                        raise ImportError("photo")
                    continue
                part = destination.with_name(destination.name + "." + token + ".part")
                digest = hashlib.sha256()
                try:
                    with archive.open("media/" + photo["sha256"]) as source, part.open("wb") as output:
                        while block := source.read(256 * 1024):
                            output.write(block)
                            digest.update(block)
                    if digest.hexdigest() != photo["sha256"]:
                        raise ImportError("photo")
                    os.replace(part, destination)
                finally:
                    part.unlink(missing_ok=True)
    if restored:
        write_json_atomic(target / "restored.json", restored)
    if writes:
        if sites_plan and sites_plan["changes"]:
            mushroom_gbif_sites.install(store, target, sites_plan)
            site_counts = mushroom_gbif_sites.counts(sites_plan)
        try:
            result = store.replace("observations", payload)
            if not result.ok:
                raise ImportError("validation")
        except Exception:
            mushroom_gbif_sites.recover(store, target)
            raise
    finish_restorations(store, target, token)
    kept = sum(row["status"] == "duplicate" and row["gbif_id"] not in replacements for row in current)
    result = {"created": len(additions), "skipped": kept,
              "rejected": len(package["rows"]) - len(additions) - len(replacements) - kept,
              "replaced": len(updates) + retried, **(site_counts or {})}
    write_json_atomic(target / "state.json", {"owner": owner, "status": "complete", "result": result})
    (target / "package.zip").unlink(missing_ok=True)
    (target / "preview.json").unlink(missing_ok=True)
    for directory in ("prepared", "sites-prepared"):
        if (target / directory).exists():
            shutil.rmtree(target / directory)
    for name in ("sites-plan.json", "sites-journal.json"):
        (target / name).unlink(missing_ok=True)
    return result
