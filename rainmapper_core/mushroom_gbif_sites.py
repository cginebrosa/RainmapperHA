"""Batch planning of GBIF sites; metric geometry runs in the installed GDAL Python."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, UTC

MAX_BYTES = 4 * 1024 * 1024
MAX_VERTICES = 60000


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def geometry_plan(sites, records, *, create=True):
    """No writes. One bounded process for the whole batch, not one per observation."""
    request = json.dumps({'sites': sites, 'records': records, 'create': create}, allow_nan=False).encode()
    if len(request) > MAX_BYTES or len(records) > 100:
        raise ValueError('limit')
    executable = os.environ.get('RAINMAPPER_GBIF_GEOMETRY_PYTHON') or (
        '/opt/homebrew/bin/python3.14' if sys.platform == 'darwin' else '/usr/bin/python3')
    result = subprocess.run([executable, str(Path(__file__).resolve())], input=request,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if result.returncode or len(result.stdout) > MAX_BYTES:
        raise ValueError('sites_geometry')
    return json.loads(result.stdout)


def _calculate(sites, records, create=True):
    from osgeo import ogr, osr
    from rainmapper_core import mushroom_known_sites as known
    ogr.UseExceptions()
    osr.UseExceptions()
    sites = copy.deepcopy(sites)
    sites.setdefault('areas', [])
    sites.setdefault('micro_areas', [])
    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    cache = {}
    vertices = 0
    def polygon(row):
        nonlocal vertices
        geometry = row.get('geometry') or {}
        if geometry.get('type') not in ('Polygon', 'MultiPolygon'):
            return None
        key = id(row)
        if key not in cache:
            rings = geometry['coordinates'] if geometry['type'] == 'Polygon' else [r for p in geometry['coordinates'] for r in p]
            vertices += sum(len(r) for r in rings)
            if vertices > MAX_VERTICES:
                raise ValueError('limit')
            shape = ogr.CreateGeometryFromJson(json.dumps(geometry))
            if shape is None or not shape.IsValid() or shape.IsEmpty():
                raise ValueError('sites_geometry')
            cache[key] = shape
        return cache[key]
    def project(shape, transform):
        value = shape.Clone()
        value.Transform(transform)
        return value
    def point(lon, lat):
        value = ogr.Geometry(ogr.wkbPoint)
        value.AddPoint_2D(lon, lat)
        return value
    def centre(row, shape, forward, inverse):
        generated = (row.get('provenance') or {}).get('gbif_creation') or {}
        if generated.get('geometry_sha256') == fingerprint(row.get('geometry')):
            c = generated['centre']
            return point(c['lon'], c['lat'])
        # Metric centroid for manual/edited geometries; representative points may be unrelated.
        return project(project(shape, forward).Centroid(), inverse)
    def choose(rows, location, forward, inverse, key):
        matches = [r for r in rows if polygon(r) is not None and polygon(r).Intersects(location)]
        def distance(row):
            c = project(centre(row, polygon(row), forward, inverse), forward)
            return (round(math.hypot(c.GetX(), c.GetY()), 6), row[key])
        return min(matches, key=distance) if matches else None, sorted(r[key] for r in matches)
    def new_id(prefix, gid, rows, key):
        base = prefix + gid
        occupied = {r[key] for r in rows}
        candidate = base
        index = 2
        while candidate in occupied:
            candidate = f'{base}_{index}'
            index += 1
        return candidate
    changes = {}
    assignments = {}
    stamp = datetime.now(UTC).isoformat(timespec='seconds')
    active_areas = [a for a in sites['areas'] if not a.get('archived')]
    area_ids = {a['area_id'] for a in active_areas}
    micros = [m for m in sites['micro_areas'] if not m.get('archived') and m.get('area_id') in area_ids]
    for record in sorted(records, key=lambda r: int(r['gbif_id'])):
        gid, lat, lon = record['gbif_id'], record['lat'], record['lon']
        local = osr.SpatialReference()
        local.ImportFromProj4(f'+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs')
        local.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        forward = osr.CoordinateTransformation(wgs, local)
        inverse = osr.CoordinateTransformation(local, wgs)
        location = point(lon, lat)
        micro, candidates = choose(micros, location, forward, inverse, 'micro_area_id')
        if micro is None and not create:
            assignments[gid] = {'micro_area_id': None, 'status': 'not_found', 'candidates': [], 'checked_at': stamp}
            continue
        if micro is None:
            area, area_candidates = choose(active_areas, location, forward, inverse, 'area_id')
            origin = point(0, 0)
            micro_shape = origin.Buffer(495, 64)
            # Circumscribed outer polygon: its edges, not just vertices, cover radius 500 m.
            area_shape = origin.Buffer(500 / math.cos(math.pi / 256), 64)
            if area is None:
                aid = new_id('gbif_area_', gid, sites['areas'], 'area_id')
                area = known.empty_area(aid)
                municipality = record.get('municipality') or ''
                area.update(name=f'{municipality} · GBIF {gid}' if municipality else f'GBIF {gid}', representative_location={'lat': lat, 'lon': lon})
                if municipality:
                    area['administrative_location']['municipality'] = municipality
                area['geometry'] = json.loads(project(area_shape, inverse).ExportToJson())
                sites['areas'].append(area)
                active_areas.append(area)
                changes[aid] = {'kind': 'area', 'action': 'created', 'id': aid}
            else:
                aid = area['area_id']
                previous = project(polygon(area), forward)
                if not previous.Contains(micro_shape.Buffer(5, 64)):
                    expanded = previous.Union(area_shape)
                    if expanded is None or not expanded.IsValid() or not expanded.Contains(micro_shape.Buffer(5, 64)):
                        raise ValueError('sites_geometry')
                    area['geometry'] = json.loads(project(expanded, inverse).ExportToJson())
                    cache.pop(id(area), None)
                    changes.setdefault(aid, {'kind': 'area', 'action': 'expanded', 'id': aid})
            mid = new_id('gbif_micro_', gid, sites['micro_areas'], 'micro_area_id')
            micro = known.empty_micro_area(mid, aid)
            micro.update(name=f'GBIF {gid}', representative_location={'lat': lat, 'lon': lon},
                         geometry=json.loads(project(micro_shape, inverse).ExportToJson()))
            # Check the round-tripped geometry including the entire 5 m safety margin.
            if not project(polygon(area), forward).Buffer(0.000001).Contains(project(polygon(micro), forward).Buffer(5, 64)):
                raise ValueError('sites_geometry')
            for row, radius in ((micro, 495), (area, 500)):
                change = changes.get(row.get('area_id')) if row is area else None
                if row is micro or (change and change['action'] == 'created' and not row.get('provenance')):
                    row['provenance'] = {'source': 'gbif_import', 'confidence': 'pending_review',
                        'gbif_creation': {'gbif_id': gid, 'centre': {'lat': lat, 'lon': lon},
                                          'radius_m': radius, 'geometry_sha256': fingerprint(row['geometry'])}}
            if aid in changes:
                area.setdefault('metadata', {})['updated_at'] = stamp
                area.setdefault('provenance', {})['last_gbif_extension'] = {'gbif_id': gid, 'at': stamp}
                # Cached geographic summaries describe the old polygon and must not survive expansion.
                area['derived_context'] = known.derive_geometry_context(area['geometry'])
            micro['derived_context'] = known.derive_geometry_context(micro['geometry'])
            sites['micro_areas'].append(micro)
            micros.append(micro)
            changes[mid] = {'kind': 'micro_area', 'action': 'created', 'id': mid}
            candidates = [mid]
        assignments[gid] = {'micro_area_id': micro['micro_area_id'], 'area_id': micro['area_id'],
                            'status': 'assigned', 'method': 'containing_nearest_centre',
                            'candidates': candidates[:16], 'checked_at': stamp}
    rows = {r.get('micro_area_id') or r.get('area_id'): r for key in ('areas', 'micro_areas') for r in sites[key]}
    for change in changes.values():
        row = rows[change['id']]
        change.update(name=row['name'])
    if create and known.validate_payload(sites):
        raise ValueError('sites_geometry')
    return {'sites': sites, 'assignments': assignments, 'changes': list(changes.values())}


def selection(accepted, replacements):
    if (not isinstance(accepted, list) or not isinstance(replacements, dict)
            or len(accepted) + len(replacements) > 100
            or any(not isinstance(v, str) or not v.isdigit() for v in accepted + list(replacements))
            or len(set(accepted)) != len(accepted) or set(accepted) & set(replacements)):
        raise ValueError('invalid')
    return fingerprint({'accepted': sorted(accepted), 'replacements': replacements})


def plan(store, target, package, accepted, replacements, archived):
    from . import mushroom_gbif_import as gbif
    recover(store, target)
    signature = selection(accepted, replacements)
    existing = store.load('observations')['observations']
    preview = {r['gbif_id']: r for r in gbif.preview(package, existing, archived)}
    wanted = []
    for gid in accepted + list(replacements):
        row = preview.get(gid, {})
        if gid in replacements:
            if not row.get('replaceable') or row.get('existing_revision') != replacements[gid]:
                raise ValueError('changed')
        elif row.get('status') != 'new':
            raise ValueError('changed')
        wanted.append(gid)
    records = []
    for item in package['rows']:
        if item['gbif_id'] in wanted:
            if not item.get('prepared'):
                raise ValueError('preparation')
            loc = item['observation']['location']
            geography = item['observation'].get('external_source', {}).get('geography') or {}
            municipality = geography.get('municipality') or {}
            name = municipality.get('name') if municipality.get('status') == 'available' and geography.get('latitude') == loc['lat'] and geography.get('longitude') == loc['lon'] else ''
            records.append({'gbif_id': item['gbif_id'], 'lat': loc['lat'], 'lon': loc['lon'],
                            'municipality': str(name or '')[:120]})
    if len(records) != len(wanted):
        raise ValueError('invalid')
    before = gbif.known_sites(store)
    result = geometry_plan(before, records)
    token = target.name
    for key in ('areas', 'micro_areas'):
        for row in result['sites'][key]:
            change = next((c for c in result['changes'] if c['id'] == row.get('micro_area_id', row.get('area_id'))), None)
            if change:
                provenance = row.setdefault('provenance', {'source': 'manual'})
                provenance.setdefault('source', 'manual')
                provenance.setdefault('creation_source', 'manual')
                if change['action'] == 'created':
                    founder = provenance.get('gbif_creation', {}).get('gbif_id')
                    external = next((i['observation']['external_source'] for i in package['rows'] if i['gbif_id'] == founder), {})
                    provenance.update(source='gbif_import', creation_source='gbif', import_token=token,
                                      export={k: external.get(k) for k in ('snapshot_sha256', 'batch_id')})
                provenance['last_import_token'] = token
    import uuid
    result.update(id=uuid.uuid4().hex, selection=signature, before_sha256=fingerprint(before))
    gbif.write_json_atomic(target / 'sites-plan.json', result)
    return public_plan(result)


def public_plan(result):
    rows = {r.get('micro_area_id', r.get('area_id')): r
            for key in ('areas', 'micro_areas') for r in result['sites'][key]}
    return {'id': result['id'], 'assignments': result['assignments'],
            'changes': [{**c, 'geometry': rows[c['id']]['geometry']} for c in result['changes']]}


def prepare_site(store, target, plan_id, site_id):
    from . import mushroom_gbif_import as gbif, mushroom_gis_lab as gis, mushroom_soilgrids as soilgrids
    plan = gbif.strict_json((target / 'sites-plan.json').read_bytes())
    if plan['id'] != plan_id:
        raise ValueError('changed')
    change = next((c for c in plan['changes'] if c['id'] == site_id), None)
    if change is None:
        raise ValueError('invalid')
    row = next(r for r in plan['sites']['areas' if change['kind'] == 'area' else 'micro_areas']
               if r.get('micro_area_id', r.get('area_id')) == site_id)
    directory = target / 'sites-prepared'
    directory.mkdir(exist_ok=True)
    path = directory / (site_id + '.json')
    if not path.exists():
        try:
            report = gis.derive_site_gis_dem(row['geometry'], store.load('gis'), store.load('catalogs'))
        except Exception as error:
            report = {'dem_status': 'unavailable', 'gis': {}, 'error_type': type(error).__name__}
        gbif.write_json_atomic(path, {'plan_id': plan_id, 'report': report})
    saved = gbif.strict_json(path.read_bytes())
    if saved['plan_id'] != plan_id:
        path.unlink()
        return prepare_site(store, target, plan_id, site_id)
    if change['kind'] == 'micro_area' and 'soilgrids_water' not in saved:
        # Import uses existing coverage; it never downloads a whole new territory implicitly.
        saved['soilgrids_water'] = soilgrids.resolve_geometry_context(
            soilgrids.default_cache_root(), row['geometry'], ensure_missing=False)
        gbif.write_json_atomic(path, saved)
    return {'site_id': site_id, 'gis_gaps': saved['report'].get('dem_status') != 'ok',
            'soilgrids_status': saved.get('soilgrids_water', {}).get('status')}


def apply_plan(store, target, plan_id, accepted, replacements, writes, names):
    from . import mushroom_gbif_import as gbif, mushroom_gis_lab as gis, mushroom_known_sites as known, mushroom_soilgrids as soilgrids
    plan = gbif.strict_json((target / 'sites-plan.json').read_bytes())
    if plan['id'] != plan_id or plan['selection'] != selection(accepted, replacements):
        raise ValueError('changed')
    if fingerprint(gbif.known_sites(store)) != plan['before_sha256']:
        raise ValueError('changed')
    if {r['external_source']['gbif_id'] for r in writes} != set(plan['assignments']):
        raise ValueError('changed')
    if not isinstance(names, dict) or len(names) > 200:
        raise ValueError('invalid')
    for change in plan['changes']:
        row = next(r for r in plan['sites']['areas' if change['kind'] == 'area' else 'micro_areas']
                   if r.get('micro_area_id', r.get('area_id')) == change['id'])
        if change['action'] == 'created' and change['id'] in names:
            name = names[change['id']]
            if not isinstance(name, str) or not name.strip() or len(name) > 160:
                raise ValueError('invalid')
            row['name'] = name.strip()
        prepared = target / 'sites-prepared' / (change['id'] + '.json')
        if not prepared.exists():
            raise ValueError('preparation')
        saved = gbif.strict_json(prepared.read_bytes())
        if saved['plan_id'] != plan_id:
            raise ValueError('changed')
        report = saved['report']
        row['derived_context']['gis_dem'] = report
        if change['kind'] == 'micro_area':
            context = saved.get('soilgrids_water')
            if not isinstance(context, dict) or context.get('geometry_hash') != soilgrids.geometry_sha256(row['geometry']):
                raise ValueError('preparation')
            soilgrids.apply_micro_area_context(row, context)
            gis.apply_micro_area_dem_altitude_report(row, report)
            row['ecology'].update({k: report.get('gis', {}).get(k, []) for k in
                                   ('host_ids', 'forest_type_ids', 'soil_tendency_ids', 'habitat_feature_ids')})
            row['topography']['aspect_ids'] = report.get('dominant_aspect_ids', [])
    for row in writes:
        assignment = plan['assignments'].get(row['external_source']['gbif_id'])
        if not assignment:
            raise ValueError('changed')
        row['micro_area_id'] = assignment['micro_area_id']
        row['external_source']['site_assignment'] = assignment
    if known.validate_payload(plan['sites']):
        raise ValueError('sites_geometry')
    if len(json.dumps(plan['sites']).encode()) > MAX_BYTES:
        raise ValueError('limit')
    return plan


def install(store, target, plan):
    from . import mushroom_gbif_import as gbif
    path = Path(store.data_dir) / 'mushroom_known_sites.json'
    before = gbif.known_sites(store)
    if fingerprint(before) != plan['before_sha256']:
        raise ValueError('changed')
    journal = {'before': before, 'existed': path.exists(), 'after_sha256': fingerprint(plan['sites']),
               'counts': counts(plan),
               'new_micro_ids': [c['id'] for c in plan['changes'] if c['kind'] == 'micro_area']}
    gbif.write_json_atomic(target / 'sites-journal.json', journal)
    backup(store, target, journal)
    gbif.write_json_atomic(path, plan['sites'])


def counts(plan):
    return {'areas_created': sum(c['kind'] == 'area' and c['action'] == 'created' for c in plan['changes']),
            'areas_expanded': sum(c['kind'] == 'area' and c['action'] == 'expanded' for c in plan['changes']),
            'micro_areas_created': sum(c['kind'] == 'micro_area' for c in plan['changes'])}


def backup(store, target, journal):
    from .mushroom_store import write_json_atomic
    destination = store.backup_dir() / ('gbif-sites-' + target.name + '.json')
    if journal['existed'] and not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(destination, journal['before'])


def recover(store, target):
    """Roll back only our unchanged sites if the observation write never completed."""
    from . import mushroom_gbif_import as gbif
    journal_path = target / 'sites-journal.json'
    if not journal_path.exists():
        return None
    journal = gbif.strict_json(journal_path.read_bytes())
    active = store.load('observations')['observations']
    archive_path = Path(store.data_dir) / 'archived/mushroom_observations_archived.json'
    archived = gbif.strict_json(archive_path.read_bytes())['observations'] if archive_path.exists() else []
    if any((r.get('external_source') or {}).get('import_token') == target.name for r in active + archived):
        backup(store, target, journal)
        return journal['counts']
    if any(r.get('micro_area_id') in journal.get('new_micro_ids', []) for r in active + archived):
        raise ValueError('changed')
    current = fingerprint(gbif.known_sites(store))
    if current not in (journal['after_sha256'], fingerprint(journal['before'])):
        raise ValueError('changed')
    if current == journal['after_sha256']:
        path = Path(store.data_dir) / 'mushroom_known_sites.json'
        if journal['existed']:
            gbif.write_json_atomic(path, journal['before'])
        else:
            path.unlink(missing_ok=True)
    journal_path.unlink()
    return None


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    request = json.loads(sys.stdin.buffer.read(MAX_BYTES + 1))
    answer = _calculate(request['sites'], request['records'], request.get('create', True))
    output = json.dumps(answer, allow_nan=False)
    if len(output.encode()) > MAX_BYTES:
        raise ValueError('limit')
    print(output)
