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
from contextlib import contextmanager

FIELDS = {
    'host_ids': 'host_taxa', 'forest_type_ids': 'forest_types',
    'soil_tendency_ids': 'soil_types', 'habitat_feature_ids': 'habitat_features',
}
MAX_BYTES = 60000
_lock = threading.Lock()


@contextmanager
def territorial_session(gis_payload, catalogs_payload):
    """Administrative reads use the current publication; rebuilds never call this."""
    from .mushroom_map_execution import load_config
    from .mushroom_map_geography_runtime import GeographyPublication, config_for_geography
    from .mushroom_territorial_reader import TerritorialSession, PATH_FLAGS
    configured = os.environ.get('RAINMAPPER_PREDICTION_MAP_CONFIG')
    paths = [Path(configured)] if configured else [
        Path('/share/rainmapper/prediction-map/config.json'),
        Path('/media/rainmapper/geography/map-config.json')]
    path = next((p for p in paths if p.is_file()), None)
    if path is None:
        yield None
        return
    config, root = load_config(path)
    publication = None
    try:
        if config.get('geography_publication_root'):
            publication = GeographyPublication(root/config['geography_publication_root'], start=False)
            reference = publication.reference()
            snap = publication.lookup(reference['fingerprint'])
            config = config_for_geography(config, snap['root'], snap['manifest'], snap['identities'])
        for key in (*PATH_FLAGS, 'geography_sources'):
            if config.get(key): config[key] = str(root/config[key])
        with TerritorialSession(config, gis_payload, catalogs_payload) as session:
            yield session
        if publication and publication.reference() != reference:
            raise ValueError('geography_changed_during_recovery')
    finally:
        if publication: publication.close()


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
        if not any(config.get(key) for key in ('forest_index', 'mvc50_index', 'land_cover', 'geology')):
            return {'source_id': 'mfe25', 'status': 'not_connected'}
        args = ['--catalogs', str(mushroom_paths.mushroom_reference_catalogs_path())]
        for key, flag in (('forest_index', '--index'), ('mvc50_index', '--mvc50-index'),
                          ('land_cover', '--land-cover'), ('geology', '--geology'),
                          ('land_cover_parts', '--land-cover-parts'), ('geology_parts', '--geology-parts')):
            if config.get(key):
                args += [flag, str(root / config[key])]
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
    with territorial_session(gis_payload, catalogs_payload) as session:
        if session is not None:
            result = session.lookup(**location)
            resolution = result['resolution']
            dem = gis.sample_dem(location['lon'], location['lat'], None)
            report = {'version': 1, 'location': location,
                      'recovered_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                      'values': {k: resolution['values'][k] for k in FIELDS},
                      'sources': {k: resolution['sources'][k] for k in FIELDS},
                      'forest': dict(result['land_context']['trees'], land_context=result['land_context']),
                      'territorial_policy': resolution['policy'], 'conflicts': resolution['conflicts'],
                      'gaps': [k for k,v in result['land_context'].items() if v.get('status') != 'available']}
            if dem.get('status') == 'ok':
                report.update(altitude_m=dem['elevation_m'], altitude_source=dem.get('source_id', 'dem_5m'))
            if len(json.dumps(report, allow_nan=False).encode()) > MAX_BYTES:
                raise ValueError('gis_recovery_result_limit')
            return report
    result = gis.reconstruct_observation({'location': location}, gis_payload, catalogs_payload)
    context = result.get('gis_context_v0', {})
    trees = forest_lookup(**location)
    from .mushroom_territorial_context import resolve_context, layer_candidates
    from .mushroom_map_ecology import compile_exact_mappings, resolve_land_context
    if 'land_context' in trees:
        ids = gis.catalog_ids_by_group(catalogs_payload)
        mapped = compile_exact_mappings(gis_payload, ids)
        land = dict(trees['land_context'], trees=trees)
        resolution, _ = resolve_land_context(land, mapped, ids.get('host_taxa', set()))
    else:
        candidates = layer_candidates(result.get('layers', {}))
        if trees.get('status') == 'available' and trees.get('catalog_status') != 'unavailable':
            candidates['mfe25'] = {'host_ids': [item['host_id'] for item in trees.get('items', []) if item.get('host_id')]}
        resolution = resolve_context(candidates)
    values = {key: resolution['values'][key] for key in FIELDS}
    sources = {key: resolution['sources'][key] for key in FIELDS}
    report = {'version': 1, 'location': location,
              'recovered_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'values': values, 'sources': sources, 'forest': trees,
              'territorial_policy': resolution['policy'], 'conflicts': resolution['conflicts'],
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
