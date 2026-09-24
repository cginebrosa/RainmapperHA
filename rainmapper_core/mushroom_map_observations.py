"""Read-only, bounded observation overlay. Never exports source notes or media."""
from __future__ import annotations

import hashlib
import json
import math
import threading
from pathlib import Path

from rainmapper_core import mushroom_paths, mushroom_known_sites
from rainmapper_core.mushroom_gis_recovery import valid_recovery
from rainmapper_core.lunar_phase import lunar_phase

PERMISSION = 'can_use_observations_map'
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_RECORDS = 10000
MAX_SPECIES = 128
MAX_ABUNDANCES = 64
PAGE_SIZE = 200
MAX_RESPONSE_BYTES = 256 * 1024
_lock = threading.Lock()
_cache = None


class ObservationError(ValueError):
    def __init__(self, code, status=400):
        super().__init__(code)
        self.status = status


def _string(value, limit=256):
    return value[:limit] if isinstance(value, str) else ''


def _read(path):
    if not path.exists():
        return {}
    with path.open('rb') as stream:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ObservationError('observations_source_limit', 413)
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ObservationError('observations_source_limit', 413)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ObservationError('observations_invalid_source', 503)
    return payload


def _signature(paths):
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else (str(p), None, 0) for p in paths)


def _coordinates(row):
    loc = row.get('location') or {}
    lat, lon = loc.get('lat'), loc.get('lon')
    if all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= limit for v, limit in ((lat, 90), (lon, 180))):
        return [lon, lat]
    return None


def _label(row):
    common = row.get('common_names') or {}
    label = row.get('label') or ''
    fallback = row.get('scientific_name') or row.get('name') or (
        label.get('en') if isinstance(label, dict) else label) or row.get('id') or ''
    translated = {}
    for lang in ('es', 'ca', 'en'):
        names = common.get(lang, []) if isinstance(common, dict) else []
        if isinstance(names, str):
            names = [names]
        name = next((v.strip() for v in names if isinstance(v, str) and v.strip()), '') if isinstance(names, list) else ''
        value = label.get(lang) if isinstance(label, dict) else label
        translated[lang] = _string(name or value or fallback)
    return translated


def _reviewed_fields(row):
    """Combine saved field notes and explicitly accepted, coordinate-bound GIS."""
    context = row.get('site_context') or {}
    try:
        recovery = valid_recovery(context.get('gis_recovery'), row.get('location') or {})
    except (ValueError, TypeError, OverflowError):
        recovery = {}
    fields, provenance = {}, {}
    for output, key in (('hosts', 'host_ids'), ('forest', 'forest_type_ids')):
        manual = [_string(v, 128) for v in (context.get('observed_' + key) or [])[:16]]
        accepted = (recovery.get('values') or {}).get(key, [])
        values = list(dict.fromkeys([*manual, *accepted]))[:16]
        fields[output] = values
        provenance[output] = [i for i, value in enumerate(values) if value in accepted and value not in manual]
    return fields, provenance


def snapshot():
    global _cache
    root = mushroom_paths.mushroom_data_dir()
    paths = [root / 'mushroom_observations.json', root / 'mushroom_profiles.json',
             root / 'mushroom_reference_catalogs.json', mushroom_known_sites.persistent_path()]
    with _lock:
        signature = _signature(paths)
        if _cache and _cache['signature'] == signature:
            return _cache
        source = _read(paths[0]).get('observations', [])
        if not isinstance(source, list) or len(source) > MAX_RECORDS:
            raise ObservationError('observations_source_limit', 413)
        profiles = _read(paths[1]).get('species_profiles', [])
        catalogs = _read(paths[2]).get('catalogs', {})
        abundance_catalog = catalogs.get('observation_flush_abundance', [])
        if not isinstance(abundance_catalog, list) or len(abundance_catalog) > MAX_ABUNDANCES:
            raise ObservationError('observations_source_limit', 413)
        abundance_favorable = {
            _string(r['id'], 128): int(type(r.get('prediction_favorable')) in (int, float)
                                      and r['prediction_favorable'] == 1)
            for r in abundance_catalog}
        sites = _read(paths[3])
        species_names = {r['species_id']: _string(r.get('scientific_name') or r['species_id']) for r in profiles if isinstance(r, dict) and r.get('species_id')}
        areas = {r['area_id']: _string(r.get('name')) for r in sites.get('areas', [])}
        micros = {r['micro_area_id']: (_string(r.get('name')), areas.get(r.get('area_id'), '')) for r in sites.get('micro_areas', [])}
        labels = {key: {r['id']: _label(r) for r in catalogs.get(key, [])} for key in ('host_taxa', 'forest_types', 'observation_flush_abundance')}
        records, by_species, counts, favorable_counts = {}, {}, {}, {}
        for row in source:
            if not isinstance(row, dict):
                continue
            sid, oid = _string(row.get('species_id'), 128), _string(row.get('observation_id'), 128)
            if not sid or not oid or oid in records:
                raise ObservationError('observations_invalid_source', 503)
            if sid not in counts and len(counts) >= MAX_SPECIES:
                raise ObservationError('observations_source_limit', 413)
            counts[sid] = counts.get(sid, 0) + 1
            fields, gis = _reviewed_fields(row)
            micro, area = micros.get(row.get('micro_area_id'), ('', ''))
            record = {'id': oid, 'species_id': sid, 'date': _string(row.get('observed_at'), 32),
                      'coordinates': _coordinates(row), 'area': area, 'microarea': micro,
                      'abundance': _string(row.get('flush_abundance'), 128),
                      **fields, 'gis': gis,
                      'observer': _string((row.get('observer') or {}).get('name'))}
            records[oid] = record
            favorable_counts[sid] = favorable_counts.get(sid, 0) + abundance_favorable.get(record['abundance'], 0)
            if record['coordinates']:
                by_species.setdefault(sid, []).append(record)
        if _signature(paths) != signature:
            raise ObservationError('observations_changed', 409)
        _cache = {'signature': signature, 'revision': hashlib.sha256(repr(signature).encode()).hexdigest()[:24],
                  'records': records, 'points': by_species, 'counts': counts, 'names': species_names, 'labels': labels,
                  'abundance_favorable': abundance_favorable, 'favorable_counts': favorable_counts}
        return _cache


def response(action, params):
    data = snapshot()
    lang = params.get('lang', 'es')
    if lang not in ('es', 'ca', 'en'):
        raise ObservationError('invalid_language')
    if params.get('revision') and params['revision'] != data['revision']:
        raise ObservationError('observations_changed', 409)
    def label(group, key):
        value = data['labels'][group].get(key, key)
        return value.get(lang) or value.get('en') or key if isinstance(value, dict) else value
    if action == 'species':
        return {'revision': data['revision'], 'abundance_favorable': data['abundance_favorable'], 'species': [
            {'id': sid, 'name': data['names'].get(sid, sid), 'count': count,
             'favorable_count': data['favorable_counts'][sid],
             'mapped_count': len(data['points'].get(sid, []))}
            for sid, count in sorted(data['counts'].items(), key=lambda item: data['names'].get(item[0], item[0]).casefold())]}
    if action == 'points':
        sid = params.get('species_id', '')
        if sid not in data['counts']:
            raise ObservationError('not_found', 404)
        try:
            offset = int(params.get('offset', '0'))
        except ValueError:
            raise ObservationError('invalid_offset') from None
        points = data['points'].get(sid, [])
        if offset < 0 or offset > len(points):
            raise ObservationError('invalid_offset')
        return {'revision': data['revision'], 'points': [
            [r['id'], *r['coordinates'], r['date'], r['abundance']] for r in points[offset:offset + PAGE_SIZE]],
            'next_offset': offset + PAGE_SIZE if offset + PAGE_SIZE < len(points) else None}
    if action == 'detail':
        row = data['records'].get(params.get('id'))
        if not row:
            raise ObservationError('not_found', 404)
        try:
            moon = lunar_phase(row['date'])
        except (ValueError, TypeError, OverflowError):
            moon = None  # A missing/invalid date must not hide the other fields.
        return {'revision': data['revision'], 'observation': {
            **{k: row[k] for k in ('id', 'date', 'area', 'microarea', 'observer')},
            'species': data['names'].get(row['species_id'], row['species_id']),
            'abundance': label('observation_flush_abundance', row['abundance']),
            'gis': row['gis'],
            'moon': moon,
            'hosts': [label('host_taxa', k) for k in row['hosts']],
            'forest': [label('forest_types', k) for k in row['forest']]}}
    raise ObservationError('not_found', 404)


def encode(payload):
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ObservationError('observations_response_limit', 413)
    return raw
