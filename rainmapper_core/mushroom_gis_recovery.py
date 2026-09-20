"""Explicit, bounded GIS recovery; values remain distinguishable from field notes."""
from __future__ import annotations

from datetime import datetime, timezone
import atexit
import json
import math
import os
from pathlib import Path
import sys
import threading

FIELDS = {
    'host_ids': 'host_taxa', 'forest_type_ids': 'forest_types',
    'soil_tendency_ids': 'soil_types', 'habitat_feature_ids': 'habitat_features',
}
MAX_BYTES = 60000
_lock = threading.Lock()


def merge_value(current, proposed, mode):
    if mode == 'keep':
        return current
    if mode == 'replace':
        return proposed
    if mode == 'merge' and isinstance(proposed, list):
        return list(dict.fromkeys([*(current or []), *proposed]))
    raise ValueError('invalid_gis_recovery_mode')


def point(lat, lon):
    lat, lon = float(lat), float(lon)
    if not math.isfinite(lat) or not math.isfinite(lon) or abs(lat) > 90 or abs(lon) > 180:
        raise ValueError('invalid_gis_coordinates')
    return {'lat': round(lat, 7), 'lon': round(lon, 7)}


def forest_lookup(*, geometry=None, lat=None, lon=None):
    """Use the same configured MFE publication as the map, without hashing assets."""
    from .mushroom_map_execution import ResidentReader, load_config
    from .mushroom_map_geography_runtime import GeographyPublication, config_for_geography
    from . import mushroom_paths
    configured = os.environ.get('RAINMAPPER_PREDICTION_MAP_CONFIG')
    paths = [Path(configured)] if configured else [
        Path('/share/rainmapper/prediction-map/config.json'),
        Path('/media/rainmapper/geography/map-config.json')]
    config_path = next((p for p in paths if p.is_file()), None)
    if config_path is None:
        return {'source_id': 'mfe25', 'status': 'not_connected'}
    request = {'geometry': geometry} if geometry is not None else point(lat, lon)
    if len(json.dumps(request, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError('gis_recovery_request_limit')
    if not _lock.acquire(blocking=False):
        return {'source_id': 'mfe25', 'status': 'busy'}
    reader = publication = None
    try:
        config, root = load_config(config_path)
        reference = None
        if config.get('geography_publication_root'):
            publication = GeographyPublication(root / config['geography_publication_root'], start=False)
            reference = publication.reference()
            snapshot = publication.lookup(reference['fingerprint'])
            config = config_for_geography(config, snapshot['root'], snapshot['manifest'], snapshot['identities'])
        if not config.get('forest_index'):
            return {'source_id': 'mfe25', 'status': 'not_connected'}
        args = ['--index', str(root / config['forest_index']),
                '--catalogs', str(mushroom_paths.mushroom_reference_catalogs_path())]
        if config.get('geography_sources'):
            args += ['--sources', str(root / config['geography_sources'])]
        reader = ResidentReader(config.get('geography_python', sys.executable),
                                'recover-mushroom-forest.py', args,
                                timeout=30, max_request_bytes=65536)
        result = reader.call(request)
        if reference:
            if publication.reference() != reference:
                raise ValueError('geography_changed_during_recovery')
            result['geography_fingerprint'] = reference['fingerprint']
        return result
    except Exception as error:
        import logging
        logging.getLogger(__name__).exception('MFE recovery unavailable')
        return {'source_id': 'mfe25', 'status': 'unavailable', 'reason': type(error).__name__}
    finally:
        if reader:
            reader.close()
            atexit.unregister(reader.close)
        if publication:
            publication.close()
        _lock.release()


def observation_preview(lat, lon, gis_payload, catalogs_payload):
    from . import mushroom_gis_lab as gis
    location = point(lat, lon)
    result = gis.reconstruct_observation({'location': location}, gis_payload, catalogs_payload)
    context = result.get('gis_context_v0', {})
    trees = forest_lookup(**location)
    hosts = [item['host_id'] for item in trees.get('items', []) if item.get('host_id')]
    values = {key: sorted(set(context.get(key, []))) for key in FIELDS}
    values['host_ids'] = sorted(set(values['host_ids'] + hosts))
    sources = {key: [] for key in FIELDS}
    for source, layer in result.get('layers', {}).items():
        for key in FIELDS:
            if layer.get('mapped', {}).get('mapped_' + key):
                sources[key].append(source)
    if hosts:
        sources['host_ids'].append('mfe25')
    report = {'version': 1, 'location': location,
              'recovered_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'values': values, 'sources': sources, 'forest': trees,
              'gaps': result.get('gaps', [])}
    if 'altitude_m' in context:
        report['altitude_m'] = context['altitude_m']
        report['altitude_source'] = context.get('altitude_source', 'dem_5m')
    if len(json.dumps(report, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError('gis_recovery_result_limit')
    return report


def valid_recovery(value, location):
    """Coordinate-bound evidence is safe to carry in the observation snapshot."""
    if not isinstance(value, dict) or value.get('version') != 1:
        return {}
    if len(json.dumps(value, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError('gis_recovery_result_limit')
    if value.get('location') != point(location.get('lat'), location.get('lon')):
        return {}
    values = value.get('values')
    if not isinstance(values, dict) or any(
        key not in FIELDS or not isinstance(ids, list) or len(ids) > 128 or
        any(not isinstance(i, str) or len(i) > 128 for i in ids)
        for key, ids in values.items()
    ):
        raise ValueError('invalid_gis_recovery_values')
    sources = value.get('sources', {})
    if not isinstance(sources, dict) or any(
        key not in FIELDS or not isinstance(ids, list) or len(ids) > 16 or
        any(not isinstance(i, str) or len(i) > 128 for i in ids)
        for key, ids in sources.items()
    ):
        raise ValueError('invalid_gis_recovery_sources')
    return value


def reviewed_context(context, row):
    """Apply reviewed fields even if unrelated live GIS layers are unavailable."""
    site = row.get('site_context') if isinstance(row.get('site_context'), dict) else {}
    recovery = valid_recovery(site.get('gis_recovery'), row.get('location', {}))
    if recovery:
        context.update({field: list(values) for field, values in recovery['values'].items()})
        context.setdefault('evidence', {})['reviewed_recovery'] = {
            'recovered_at': recovery.get('recovered_at'), 'sources': recovery.get('sources', {}),
        }
    return context
