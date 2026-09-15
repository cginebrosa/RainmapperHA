"""Offline point inference using installed models and sealed species evidence.

No training, area substitution, artifact publication or learned-model fallback.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import date, timedelta
import gzip
import hashlib
import json
from pathlib import Path

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_version_registry as versions
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_ml_quality_catalog as quality
from rainmapper_core.mushroom_map_prediction import resolve_species_week
from rainmapper_core.mushroom_map_ecology import prediction_candidates
from rainmapper_core.mushroom_phenology import season_phase_for_months
from rainmapper_core.mushroom_map_weather import PointWeatherReader, fingerprint, map_today


def small_json(path, limit):
    with Path(path).open('rb') as f:
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('model_metadata_limit')
    return json.loads(raw)


def projected_quality(path, expected_sha):
    """Read a verified catalog in bounded JSON elements, excluding area evidence.

    Preserves species resolutions verbatim. Does not manufacture a new sealed
    catalog identity; provenance remains the hash of the original full source.
    """
    if Path(path).stat().st_size > 16 * 1024 * 1024:
        raise ValueError('quality_compressed_limit')
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(65536):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha:
        raise ValueError('quality_digest_mismatch')
    opener = gzip.open if Path(path).suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        decoder = json.JSONDecoder()
        buffer = ''; total = 0
        def more():
            nonlocal buffer, total
            chunk = stream.read(65536)
            total += len(chunk)
            if total > 64 * 1024 * 1024 or len(buffer) > 512 * 1024:
                raise ValueError('quality_read_limit')
            buffer += chunk
            return bool(chunk)
        def peek():
            nonlocal buffer
            buffer = buffer.lstrip()
            while not buffer:
                if not more():
                    raise ValueError('quality_truncated')
                buffer = buffer.lstrip()
            return buffer[0]
        def take(char):
            nonlocal buffer
            if peek() != char:
                raise ValueError('invalid_quality_json')
            buffer = buffer[1:]
        def value():
            nonlocal buffer
            peek()
            while True:
                try:
                    obj, end = decoder.raw_decode(buffer)
                    # Values here are objects/strings; ensure delimiter exists.
                    if end == len(buffer) and more():
                        continue
                    buffer = buffer[end:]
                    return obj
                except json.JSONDecodeError:
                    if not more():
                        raise ValueError('invalid_quality_json')
        result = {}; keys = set(); kept_bytes = 0
        take('{')
        while peek() != '}':
            key = value()
            if not isinstance(key,str) or key in keys:
                raise ValueError('invalid_quality_key')
            keys.add(key); take(':')
            if peek() == '[':
                take('['); rows = []; count = 0
                while peek() != ']':
                    row = value(); count += 1
                    if count > 20000:
                        raise ValueError('quality_row_limit')
                    if key in ('entries','species_selections','selection_prediction_days'):
                        kept_bytes += len(json.dumps(row))
                        if kept_bytes > 12 * 1024 * 1024:
                            raise ValueError('quality_projection_limit')
                        rows.append(row)
                    if peek() == ']': break
                    take(',')
                take(']'); result[key] = rows
            else:
                result[key] = value()
            if peek() == '}': break
            take(',')
        take('}')
        if buffer.strip() or stream.read(1):
            raise ValueError('quality_trailing_data')
    if result.get('kind') != quality.KIND or result.get('schema_version') != quality.SCHEMA_VERSION:
        raise ValueError('quality_contract')
    if (result.get('selection_prediction_days') != list(range(1,8)) or
        result.get('selection_split_id') != quality.mushroom_ml_reliability_audit.OFFICIAL_SELECTION_SPLIT_ID):
        raise ValueError('quality_selection_contract')
    resolutions = result.get('species_selections',[])
    if len(resolutions) > 32 * 7:
        raise ValueError('quality_species_limit')
    for row in resolutions:
        quality._validate_resolution(row, prediction_day=row['prediction_day'], allowed_scopes={'species'})
    return result


class PointModelRuntime:
    """Serialized resident adapter. One metadata snapshot, bounded request caches."""
    def __init__(self, *, registry_path, models_root, profiles_path, data_root, stations_file,
                 calendar_timezone="Europe/Madrid"):
        self.registry_path = Path(registry_path)
        self.models_root = Path(models_root).resolve()
        self.profiles_path = Path(profiles_path)
        self.weather = PointWeatherReader(data_root, stations_file, calendar_timezone=calendar_timezone)
        self.signature = None
        self.last_diagnostics = {}

    def _refresh(self):
        registry = small_json(self.registry_path, 256*1024)
        path = versions.operational_manifest_path(registry, models_root=self.models_root)
        if path is None:
            raise ValueError('no_installed_batch')
        manifest = small_json(path, 2*1024*1024)
        qref = manifest['quality_catalog']
        qpath = (self.models_root/qref['path']).resolve()
        if not qpath.is_relative_to(self.models_root):
            raise ValueError('quality_path_outside_root')
        signature = (fingerprint(self.registry_path), str(path), fingerprint(path), fingerprint(qpath))
        if signature == self.signature:
            return
        checked = catalog.validate_batch_manifest(registry,manifest)
        if len(checked['artifacts']) > 2048:
            raise ValueError('model_artifact_count_limit')
        q = projected_quality(qpath,qref['sha256'])
        if q.get('snapshot_id') != checked.get('snapshot_id') or q.get('selection_status') != 'complete':
            raise ValueError('quality_snapshot_mismatch')
        self.registry, self.manifest, self.quality = registry, checked, q
        self.catalog_profiles = catalog.catalog_entries(registry)
        self.installed = [v['version_id'] for v in registry['versions'] if versions.installed_generation(registry,v['version_id'])]
        self.resolutions = {}
        for row in q['species_selections']:
            days = self.resolutions.setdefault(row['species_id'],{})
            if row['prediction_day'] in days:
                raise ValueError('duplicate_species_evidence')
            days[row['prediction_day']] = row
        self.signature = signature
        self.revision = hashlib.sha256(json.dumps({'registry':registry,'batch':checked['batch_id'],'quality':qref['sha256']},sort_keys=True).encode()).hexdigest()[:20]

    def predict(self, request, geography):
        issue = date.fromisoformat(request['start_date']); horizon = request['horizon_days']
        ecology = geography.get('ecology',{})
        self.last_diagnostics = {}
        selected = prediction_candidates(ecology, request.get('species_ids'))
        rows = [{'species_id':s['species_id'],'label_key':s['species_id'],'status':'no_model',
                 'probabilities':[None]*horizon,'reasons':['model_unavailable']*horizon} for s in selected]
        output = {'data_mode':'prediction','species':rows,'provenance':{'engine':'existing_python_predictor',
                  'scientifically_validated':False,'selection_scope':'species','point_validation':'not_established'}}
        if not rows:
            return output
        self._refresh()
        output['provenance'].update(model_revision=self.revision,batch_id=self.manifest['batch_id'])
        if not any(self.resolutions.get(row['species_id']) for row in selected):
            return output
        profiles = small_json(self.profiles_path,2*1024*1024)
        profiles = {p['species_id']:p for p in profiles['species_profiles']}
        lat,lon = request['point']['lat'],request['point']['lon']
        altitude = geography.get('terrain',{}).get('elevation',{}).get('value_m')
        soil = geography.get('model_soil_water')
        self.weather._refresh()
        weather_identity = self.weather._identity
        output['provenance']['weather_generation'] = self.weather.generation.generation_id
        output['provenance']['soil_context_hash'] = (soil or {}).get('context_hash')
        weather_cache = OrderedDict()
        calendar_timezone = request.get('calendar_timezone',self.weather.calendar_timezone)
        today = map_today(calendar_timezone)
        self.last_diagnostics = {}
        def materializer(species_id):
            def materialize(*,target_date,selections):
                phenology = profiles.get(species_id, {}).get('phenology', {})
                if season_phase_for_months(target_date, phenology.get('main_months', []),
                                           phenology.get('secondary_months', [])) not in ('main','secondary'):
                    return {'members':[]}
                refs=[]
                for selection in selections:
                    try:
                        refs.append(comparison.resolve_selection(self.registry,self.manifest,selection,
                            species_id=species_id,checked_manifest=self.manifest,catalog_profiles=self.catalog_profiles))
                    except FileNotFoundError:
                        continue
                if not refs: return {'members':[]}
                if len(refs)>96: raise ValueError('point_candidate_limit')
                days, physical = comparison._weather_requirements(refs,catalog_profiles=self.catalog_profiles)
                series_by_horizon={}; context=None; stations=None
                for h in sorted({r.horizon_days for r in refs}):
                    cutoff=target_date-timedelta(days=h)
                    if cutoff>=today: return {'members':[]}
                    key=(cutoff,days,physical)
                    if key not in weather_cache:
                        prepared=self.weather.prepare_model_inputs(lat,lon,altitude,end_day=cutoff,
                            lookback_days=days,include_physical_state=physical,soilgrids_context=soil,
                            calendar_timezone=calendar_timezone)
                        if self.weather._identity != weather_identity:
                            raise ValueError('point_weather_generation_changed')
                        if len(weather_cache)>=8: weather_cache.popitem(last=False)
                        weather_cache[key]=prepared
                    context,series,stations=weather_cache[key]
                    series_by_horizon[h]=series
                # Cache is per materialization: no inputs survive a point/date.
                return comparison.compare_prepared(self.registry,self.manifest,refs,models_root=self.models_root,
                    target_date=target_date,area_id=context.area_id,area_context=context,
                    area_series_by_horizon=series_by_horizon,stations=stations,checked_manifest=self.manifest,
                    comparison_cache={'quality_catalog':self.quality})
            return materialize
        for source,row in zip(selected,rows):
            sid=row['species_id']; resolutions=self.resolutions.get(sid)
            if not resolutions: continue
            if set(resolutions)!=set(range(1,8)):
                raise ValueError('point_evidence_incomplete')
            # Only the existing predictor evaluates season, using the unchanged profile.
            phenology=profiles.get(sid,{}).get('phenology',{})
            week=resolve_species_week(species_id=sid,point_id='map-query',issue_date=issue,
                resolutions_by_day=resolutions,installed_version_ids=self.installed,
                materialize=materializer(sid),season_phase=lambda day: season_phase_for_months(
                    day,phenology.get('main_months',[]),phenology.get('secondary_months',[])),
                phenology=phenology, lazy_families=True)
            row['status']='available'
            diagnostic=[]
            for i,day in enumerate(week['days'][:horizon]):
                operational=day['operational_comparison']; active=day['reliability_selection']
                candidate=active.get('candidate') or {}
                # A sealed resolution yields at most one operational winner.
                winners=operational.get('selected_winners',[])
                probability=winners[0].get('probability') if len(winners)==1 else None
                if source['daily_season_phases'][i] not in ('main','secondary'):
                    probability=None; reason=source['daily_season_phases'][i]
                elif probability is not None and active.get('runtime_selection_status')!='abstain':
                    reason='calculated'
                else:
                    probability=None; reason=operational.get('reason') or 'model_abstained'
                row['probabilities'][i]=probability;row['reasons'][i]=reason
                diagnostic.append({'day':i+1,'candidate':candidate,'weekly':active.get('weekly_model_selection'),
                    'runtime_status':active.get('runtime_selection_status'),'reason':reason})
            self.last_diagnostics[sid]=diagnostic
        self.weather._refresh()
        if self.weather._identity != weather_identity:
            raise ValueError('point_weather_generation_changed')
        return output
