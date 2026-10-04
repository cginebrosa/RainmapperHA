"""Small, read-only projection of saved private areas for the map overlay."""
from __future__ import annotations

import json
import math
import threading

from rainmapper_core import mushroom_known_sites

PERMISSION = 'can_use_observations_map'
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_FEATURES = 2000
MAX_VERTICES = 50000
MAX_RESPONSE_BYTES = 3 * 1024 * 1024
_lock = threading.Lock()
_cache = None


class SitesError(ValueError):
    def __init__(self, code, status=503):
        super().__init__(code)
        self.status = status


def _point(value):
    return (isinstance(value, list) and len(value) == 2
            and all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= limit
                    for v, limit in zip(value, (180, 90))))


def _shape(row, budget):
    geometry = row.get('geometry')
    location = row.get('representative_location') or {}
    label = [location.get('lon'), location.get('lat')] if isinstance(location, dict) else None
    if geometry is None:
        return ({'type': 'Point', 'coordinates': label}, label) if _point(label) else (None, None)
    if not isinstance(geometry, dict) or geometry.get('type') not in ('Polygon', 'MultiPolygon'):
        raise SitesError('known_sites_invalid_geometry')
    coords = geometry.get('coordinates')
    polygons = [coords] if geometry['type'] == 'Polygon' else coords
    if not isinstance(polygons, list) or not polygons or len(polygons) > MAX_VERTICES:
        raise SitesError('known_sites_invalid_geometry')
    west, south, east, north = 180., 90., -180., -90.
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon or len(polygon) > MAX_VERTICES:
            raise SitesError('known_sites_invalid_geometry')
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4:
                raise SitesError('known_sites_invalid_geometry')
            budget[0] += len(ring)
            if budget[0] > MAX_VERTICES:
                raise SitesError('known_sites_source_limit', 413)
            for point in ring:
                if not _point(point):
                    raise SitesError('known_sites_invalid_geometry')
                west, south = min(west, point[0]), min(south, point[1])
                east, north = max(east, point[0]), max(north, point[1])
            if ring[0] != ring[-1]:
                raise SitesError('known_sites_invalid_geometry')
    # This fallback positions only the label; it never creates a saved location.
    return {'type': geometry['type'], 'coordinates': coords}, label if _point(label) else [(west+east)/2, (south+north)/2]


def _encode(payload):
    output = bytearray()
    for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(',', ':')).iterencode(payload):
        raw = chunk.encode('utf-8')
        if len(output) + len(raw) > MAX_RESPONSE_BYTES:
            raise SitesError('known_sites_response_limit', 413)
        output.extend(raw)
    return bytes(output)


def response():
    """Return cached GeoJSON bytes, never notes, observations, photos or GIS data."""
    global _cache
    path = mushroom_known_sites.persistent_path()
    with _lock:
        if not path.exists():
            _cache = None
            return _encode({'type': 'FeatureCollection', 'features': []})
        stat = path.stat()
        signature = (str(path), stat.st_mtime_ns, stat.st_size)
        if stat.st_size > MAX_FILE_BYTES:
            raise SitesError('known_sites_source_limit', 413)
        if _cache and _cache[0] == signature:
            return _cache[1]
        with path.open('rb') as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise SitesError('known_sites_source_limit', 413)
        source = json.loads(raw)
        if not isinstance(source, dict):
            raise SitesError('known_sites_invalid_source')
        areas, micros = source.get('areas', []), source.get('micro_areas', [])
        if not isinstance(areas, list) or not isinstance(micros, list):
            raise SitesError('known_sites_invalid_source')
        if len(areas) + len(micros) > MAX_FEATURES:
            raise SitesError('known_sites_source_limit', 413)
        # Preflight every geometry before materializing the response feature list.
        budget, prepared, archived = [0], [], set()
        for kind, rows, key in (('area', areas, 'area_id'), ('micro_area', micros, 'micro_area_id')):
            for row in rows:
                if not isinstance(row, dict):
                    raise SitesError('known_sites_invalid_source')
                identifier, name = row.get(key), row.get('name')
                if not isinstance(identifier, str) or not isinstance(name, str) or len(identifier) > 128 or len(name) > 256:
                    raise SitesError('known_sites_invalid_source')
                if row.get('archived') is True:
                    if kind == 'area':
                        archived.add(identifier)
                    continue
                if kind == 'micro_area' and row.get('area_id') in archived:
                    continue
                shape, label = _shape(row, budget)
                if shape:
                    prepared.append((kind, identifier, name, shape, label))
        payload = {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'id': kind+':'+identifier, 'geometry': shape,
             'properties': {'kind': kind, 'name': name, 'label_point': label}}
            for kind, identifier, name, shape, label in prepared]}
        encoded = _encode(payload)
        current = path.stat()
        if (current.st_mtime_ns, current.st_size) != signature[1:]:
            raise SitesError('known_sites_changed', 409)
        _cache = signature, encoded
        return encoded
