"""Private bounded worker cache of complete historical forecast weeks.

No model weights, raw feature matrices, coordinates or panels go to HA. The
same fitted temporal unit serves the observed date and its neighbouring days.
Area weather uses the production runtime adapter, with each candidate's actual
lookback and weather cutoff. No future observed weather fills a forecast day.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import date, timedelta
from dataclasses import replace, asdict, fields
from bisect import bisect_left, bisect_right
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import zlib

from rainmapper_core.mushroom_competing_history import canonical
from rainmapper_core.mushroom_competing_comparison import MissingReplay

MAX_BYTES = 96 * 1024 * 1024
MAX_PACKET = 128 * 1024
MAX_CELLS = 375000
RAIN_FIELDS = ('days_since_significant_rain_at_target', 'significant_rain_found_90d',
               'significant_rain_search_complete', 'rain_event_search_complete',
               'significant_rain_event_date', 'significant_rain_event_amount_mm',
               'significant_rain_threshold_mm')


class Panels:
    def __init__(self, path, *, max_bytes=None):
        self.max_bytes = MAX_BYTES if max_bytes is None else max_bytes
        if not isinstance(self.max_bytes, int) or not 4096 <= self.max_bytes <= MAX_BYTES:
            raise ValueError('comparison_panel_cache_limit')
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > self.max_bytes:
            raise ValueError('comparison_panel_cache_limit')
        self.db = sqlite3.connect(path)
        self.db.execute(f'PRAGMA max_page_count={self.max_bytes // 4096}')
        self.db.execute('CREATE TABLE IF NOT EXISTS panels (unit TEXT, species TEXT, observation TEXT, '
                        'payload BLOB NOT NULL, sha TEXT NOT NULL, PRIMARY KEY(unit,species,observation))')
        self.db.execute('CREATE TABLE IF NOT EXISTS generations (revision TEXT PRIMARY KEY, payload BLOB NOT NULL)')
        from rainmapper_core.mushroom_map_competing import PointCache
        self.memo = PointCache(max_bytes=4*1024*1024, max_entries=256)
        self.materialize_missing = None
        self.db.execute('CREATE TABLE IF NOT EXISTS panel_fits '
                        '(unit TEXT PRIMARY KEY, payload BLOB NOT NULL, sha TEXT NOT NULL)')

    @classmethod
    def readonly(cls, path):
        path = Path(path).resolve()
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('comparison_panel_cache_limit')
        value = cls.__new__(cls)
        value.max_bytes = MAX_BYTES
        value.db = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)
        from rainmapper_core.mushroom_map_competing import PointCache
        value.memo = PointCache(max_bytes=4*1024*1024, max_entries=256)
        value.materialize_missing = None
        return value

    def merge_from(self, path):
        """Import validated derived packets, retaining existing weekly members."""
        source = self.readonly(path)
        try:
            with self.db:
                for unit, sid, oid in source.db.execute('SELECT unit,species,observation FROM panels'):
                    packet = source._packet(unit,sid,oid)
                    rows = [(day,horizon,{'prediction':{'probability':p,'applicability':{'status':status}},
                             'features_used':dict(zip(RAIN_FIELDS,rain,strict=True))})
                            for day,horizon,p,status,rain in packet]
                    self.write(unit,sid,oid,rows,merge=True,commit=False)
        finally:
            source.close()

    def close(self):
        self.db.close()

    def write(self, unit, sid, oid, rows, *, merge=False, commit=True):
        compact = []
        for day, horizon, member in rows:
            prediction = member.get('prediction') or {}
            compact.append([day, horizon, prediction.get('probability'),
                            (prediction.get('applicability') or {}).get('status'),
                            [(member.get('features_used') or {}).get(f) for f in RAIN_FIELDS]])
        if merge:
            saved = self._packet(unit, sid, oid)
            existing = {(r[0], r[1]): r for r in saved or ()}
            existing.update({(r[0], r[1]): r for r in compact})
            compact = [existing[k] for k in sorted(existing)]
        if len(compact) > 49:
            raise ValueError('comparison_panel_cardinality')
        raw = canonical(compact)
        if len(raw) > MAX_PACKET:
            raise ValueError('comparison_panel_packet_limit')
        raw = b'RMP1' + zlib.compress(raw, 1)
        if self.db.execute('PRAGMA page_count').fetchone()[0] * 4096 + len(raw) > self.max_bytes:
            raise ValueError('comparison_panel_cache_limit')
        from contextlib import nullcontext
        with self.db if commit else nullcontext():
            self.db.execute('INSERT OR REPLACE INTO panels VALUES (?,?,?,?,?)',
                            (unit, sid, oid, raw, hashlib.sha256(raw).hexdigest()))
        self.memo.discard((unit, sid, oid))

    def _packet(self, unit, sid, oid):
        record = self.db.execute('SELECT payload,sha FROM panels WHERE unit=? AND species=? AND observation=?',
                                 (unit, sid, oid)).fetchone()
        if record is None:
            return None
        raw, sha = record
        if len(raw) > MAX_PACKET or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('comparison_panel_integrity')
        if raw.startswith(b'RMP1'):
            decoder = zlib.decompressobj()
            raw = decoder.decompress(raw[4:], MAX_PACKET + 1)
            if len(raw) > MAX_PACKET or not decoder.eof or decoder.unused_data:
                raise ValueError('comparison_panel_size_limit')
        rows = json.loads(raw)
        if len(rows) > 49 or len({(r[0], r[1]) for r in rows}) != len(rows):
            raise ValueError('comparison_panel_cardinality')
        return rows

    def save_fit(self, unit, reference, fit_key):
        raw = canonical({'reference': reference.as_dict(), 'fit_key': fit_key})
        if len(raw) > 4096 or self.db.execute('PRAGMA page_count').fetchone()[0] * 4096 + len(raw) > self.max_bytes:
            raise ValueError('comparison_panel_cache_limit')
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO panel_fits VALUES (?,?,?)',
                            (unit, raw, hashlib.sha256(raw).hexdigest()))

    def fit(self, unit):
        row = self.db.execute('SELECT payload,sha FROM panel_fits WHERE unit=?', (unit,)).fetchone()
        if row is None:
            raise MissingReplay('historical_fit_unavailable')
        raw, sha = row
        if len(raw) > 4096 or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('comparison_fit_integrity')
        return json.loads(raw)

    def read(self, unit, sid, oid, target, horizon):
        try:
            return self._read(unit, sid, oid, target, horizon)
        except MissingReplay:
            materialize = getattr(self, 'materialize_missing', None)
            if materialize is None:
                raise
            materialize(unit, sid, oid, target, horizon)
            return self._read(unit, sid, oid, target, horizon)

    def read_week_member(self, unit, sid, oid, target, horizon, *, issue):
        try:
            return self._read(unit, sid, oid, target, horizon)
        except MissingReplay:
            if self.materialize_missing is None:
                raise
            self.materialize_missing(unit, sid, oid, target, horizon, week_issue=issue)
            return self._read(unit, sid, oid, target, horizon)

    def _read(self, unit, sid, oid, target, horizon):
        key = unit, sid, oid
        saved = self.memo.get(key)
        if saved is None:
            rows = self._packet(*key)
            # Negative entries last only until this packet is written. Avoid
            # hitting SQLite again for each paused member of the same week.
            saved = ({(r[0], r[1]): r[2:] for r in rows} if rows is not None else None,)
            self.memo.put(key, saved)
        if saved[0] is None:
            raise MissingReplay('weekly_panel_unavailable')
        member = saved[0].get((target.isoformat(), horizon))
        if member is None:
            raise MissingReplay('weekly_day_unavailable')
        p, status, rain = member
        if p is None:
            return {'available': False, 'reason': 'runtime_feature_gates_failed'}
        return {'available': True, 'prediction': {'probability': p, 'applicability': {'status': status}},
                'features_used': dict(zip(RAIN_FIELDS, rain, strict=True)),
                'metadata': {'cutoff_date': (target - timedelta(days=horizon)).isoformat()}}

    def save_generation(self, revision, value):
        from rainmapper_core.mushroom_competing_evidence import to_wire
        value = {**value, 'evidence': to_wire(value['evidence'])}
        # Prove the JSON size before using the C encoder. The incremental
        # fallback preserves the same limit for unusual unbounded structures.
        from rainmapper_core.mushroom_ml_benchmark_io import _encode
        encoded = _encode(value, 128 * 1024 * 1024, 'comparison_generation_limit')
        raw = b'RMG1' + hashlib.sha256(encoded).digest() + zlib.compress(encoded, 1)
        if (len(raw) > 32 * 1024 * 1024 or
                self.db.execute('PRAGMA page_count').fetchone()[0]*4096 + len(raw) > MAX_BYTES):
            raise ValueError('comparison_generation_limit')
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO generations VALUES (?,?)', (revision, raw))

    def generation(self, revision):
        row = self.db.execute('SELECT payload FROM generations WHERE revision=?', (revision,)).fetchone()
        if row is None:
            return None
        raw = row[0]
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError('comparison_generation_limit')
        if raw.startswith(b'RMG1'):
            decoder = zlib.decompressobj()
            value = decoder.decompress(raw[36:], 128 * 1024 * 1024 + 1)
            if (len(value) > 128 * 1024 * 1024 or not decoder.eof or decoder.unused_data or
                    hashlib.sha256(value).digest() != raw[4:36]):
                raise ValueError('comparison_generation_integrity')
            raw = value
        elif len(raw) > 2 * 1024 * 1024:
            raise ValueError('comparison_generation_limit')
        return json.loads(raw)


def preflight(references, visits, *, deferred=False):
    """Conservative bound before inference or weather materialization."""
    cells = sum((49 if r['temporal_contract_id'].startswith('lag_') else 13)
                for r in references for v in visits
                if r['species_id'] in ('all_species', v['species_id']))
    if deferred:
        # No Cartesian product is allocated or predicted. Each replay request
        # materializes one bounded packet and checks the unchanged store budget.
        if len(visits) > 10000 or len(references) > 4096:
            raise ValueError('comparison_panel_plan_limit')
        return {'potential_cells': cells, 'materialization': 'requested_members_only',
                'max_packet_cells': 49, 'max_bytes': MAX_BYTES}
    if cells > MAX_CELLS or cells * 256 > MAX_BYTES:
        raise ValueError('comparison_panel_plan_limit')
    return {'planned_cells': cells, 'estimated_bytes': cells * 256, 'max_bytes': MAX_BYTES}


class Builder:
    def __init__(self, *, store, known_sites, data_dir, stations_file, profiles, progress,
                 inputs=None, input_revision='runtime-inputs-v1', persist_features=True):
        from rainmapper_core import mushroom_ml_area_weather_runtime as weather
        from rainmapper_core import mushroom_ml_weather_workspace as workspace
        from rainmapper_core.mushroom_competing_features import Inputs
        self.store, self.profiles, self.progress = store, profiles, progress
        # Tests may share the panel connection; production uses the existing
        # 256 MiB unit database, without increasing either database's limit.
        self.inputs = inputs or Inputs(store.db)
        self.input_revision = input_revision
        self.areas, self.microareas = weather.area_contexts(known_sites)
        self.workspace = workspace.active_workspace(data_dir=data_dir, known_sites=known_sites, stations_file=stations_file)
        if self.workspace is None:
            raise ValueError('comparison_weather_workspace_missing')
        self.nearby = {}; self.area_keys = {}; self.signatures = OrderedDict()
        self.indexes = OrderedDict(); self.index_bytes = 0
        self.view = None; self.view_area = None
        self.stats = dict(weather_built=0, weather_reused=0, features_built=0, features_reused=0)
        self.fingerprints = OrderedDict()
        self.input_fingerprints = OrderedDict()
        self.requirements = {}
        self.station_windows = OrderedDict()
        from rainmapper_core.mushroom_map_competing import PointCache
        self.raw_windows = PointCache(max_bytes=16*1024*1024, max_entries=1024)
        self.series_memo = PointCache(max_bytes=16*1024*1024, max_entries=256)
        self.daily_templates = PointCache(max_bytes=8*1024*1024, max_entries=1024)
        from rainmapper_core.mushroom_competing_features import TransientInputs
        self.feature_rows = TransientInputs()
        self.persist_features = persist_features

    def _area(self, area):
        from rainmapper_core import mushroom_observation_context as context
        from rainmapper_core import mushroom_weather_idw as idw
        if area not in self.nearby:
            self.nearby[area] = {key: station for key,station in self.workspace.stations.items()
                if any(context.haversine_km(c.lat,c.lon,station.lat,station.lon) <= idw.RAINFALL_IDW_RADIUS_KM
                       for c in self.microareas[area])}
            self.area_keys[area] = hashlib.sha256(canonical([self.input_revision, asdict(self.areas[area]),
                [asdict(c) for c in self.microareas[area]], sorted(self.workspace.disabled)])).hexdigest()
        return self.nearby[area]

    def _index(self, key, station):
        if key in self.indexes:
            self.indexes.move_to_end(key)
            return self.indexes[key]
        axis = sorted(station.records_by_day)
        names = [f.name for f in fields(next(iter(station.records_by_day.values())))] if axis else []
        hashes = bytearray()
        for day in axis:
            row = station.records_by_day[day]
            values = [getattr(row, name) for name in names]
            hashes.extend(hashlib.sha256(canonical([v.isoformat() if isinstance(v,date) else v for v in values])).digest())
        value = axis, bytes(hashes)
        size = len(axis)*8 + len(hashes)
        while self.indexes and self.index_bytes + size > 16*1024*1024:
            old = self.indexes.popitem(last=False)[1]
            self.index_bytes -= len(old[0])*8 + len(old[1])
        if size <= 16*1024*1024:
            self.indexes[key] = value; self.index_bytes += size
        return value

    def _signature(self, area, start, end):
        key = area, start, end
        if key not in self.signatures:
            h = hashlib.sha256(self.area_keys[area].encode())
            for station_key, station in sorted(self._area(area).items()):
                axis, hashes = self._index(station_key, station)
                left, right = bisect_left(axis,start), bisect_right(axis,end)
                if left == right:
                    continue
                h.update(canonical([station_key, station.station_name, station.lat, station.lon, station.altitude_m]))
                h.update(hashes[left*32:right*32])
            self.signatures[key] = h.hexdigest()
            if len(self.signatures) > 4096:
                self.signatures.popitem(last=False)
        return self.signatures[key]

    def _stations(self, area, start, end):
        from rainmapper_core.mushroom_ml_weather_workspace import _RecordRange
        identity = area, start, end
        if identity in self.station_windows:
            self.station_windows.move_to_end(identity)
            return self.station_windows[identity]
        stations = {}
        for key,station in self._area(area).items():
            axis, _ = self._index(key, station)
            records = _RecordRange(station.records_by_day, axis, start, end)
            if records:
                stations[key] = replace(station, records_by_day=records)
        self.station_windows[identity] = stations
        if len(self.station_windows) > 16:
            self.station_windows.popitem(last=False)
        return stations

    def _workspace(self, area):
        from rainmapper_core.mushroom_competing_features import LastView
        if self.view_area != area:
            self.view = copy.copy(self.workspace)
            self.view.stations = self._area(area)
            self.view._station_views = LastView(); self.view._weather_views = LastView()
            self.view.stations_for_view = lambda start,end: self._stations(area,start,end)
            self.view_area = area
        return self.view

    def _series(self, area, cutoff, days, physical, key):
        cached = self.series_memo.get(key)
        if cached is not None:
            self.stats['weather_reused'] += 1
            self.stats['weather_memory_hits'] = self.stats.get('weather_memory_hits', 0) + 1
            return cached
        value = self._load_series(area, cutoff, days, physical, key)
        from rainmapper_core.mushroom_competing_features import _freeze, _FrozenDict
        if not isinstance(value, _FrozenDict):
            try:
                value, _ = _freeze(value, 16*1024*1024)
            except OverflowError:
                return value
        self.series_memo.put(key, value)
        return value

    def _load_series(self, area, cutoff, days, physical, key):
        from rainmapper_core import mushroom_ml_area_weather_runtime as weather
        cached = self.inputs.read_shared(key)
        if cached is not None:
            self.stats['weather_reused'] += 1
            return cached
        start = cutoff - timedelta(days=days-1)
        view = self._workspace(area)
        micro = view.weather_for_contexts(self.microareas[area], start_day=start, end_day=cutoff)
        eto = {c.micro_area_id: view.eto_for_context(c.micro_area_id, start_day=start, end_day=cutoff)
               for c in self.microareas[area]} if physical else None
        # V4 has already computed these exact 365-day/default-soil windows.
        # Its weather audit annotation is private to that benchmark producer.
        from rainmapper_core.mushroom_ml_weather_workspace import DEFAULT_SOIL_VARIANT_ID, soil_inputs_signature
        soil = self.workspace.soil_bundle(DEFAULT_SOIL_VARIANT_ID, area, cutoff) if physical and days == 365 else None
        prepared_soil = None
        if (soil is not None and soil.input_signature is not None and
                soil.input_signature == soil_inputs_signature(
                    {key: value['daily_rain_idw_mm'] for key, value in micro.items()}, eto)):
            state = {**soil.aggregated, 'metadata': {k:v for k,v in soil.aggregated.get('metadata', {}).items()
                                                   if k != 'microarea_weather_idw_quality'}}
            prepared_soil = state, soil.daily_fraction_mean
            self.stats['soil_states_reused'] = self.stats.get('soil_states_reused', 0) + 1
        series = weather.materialize_area_series(area_id=area, end_day=cutoff, days=days,
            microareas_by_area=self.microareas, stations=self._stations(area,start,cutoff),
            excluded_station_keys=self.workspace.disabled, include_physical_state=physical,
            weather_by_microarea=micro, eto_by_microarea=eto, prepared_soil_state=prepared_soil)
        self.inputs.write(key, series); self.stats['weather_built'] += 1
        return series

    def _requests(self, reference, test, requested=None):
        from rainmapper_core import mushroom_ml_model_catalog as catalog
        from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
        profile = reference.version_id, reference.profile_id
        if profile not in self.requirements:
            ref = catalog.ModelRef.from_mapping({**reference.as_dict(), 'horizon_days':7})
            self.requirements[profile] = comparison._weather_requirements([ref], catalog_profiles=self.profiles)
        days, physical = self.requirements[profile]
        visits = {(s['metadata']['species_id'], s['metadata']['observation_id']): s['metadata'] for s in test}
        for index, ((sid, oid), m) in enumerate(sorted(visits.items())):
            target = date.fromisoformat(m['target_date']); area = m['area_id']
            if area not in self.areas:
                continue
            self._area(area)
            dates = {(target - timedelta(days=h-1) + timedelta(days=d-1),
                      d if reference.temporal_contract_id.startswith('lag_') else 7)
                     for h in range(1,8) for d in range(1,8)}
            for day, horizon in sorted(dates):
                if requested is not None and (sid, oid, day, horizon) not in requested:
                    continue
                ref = catalog.ModelRef.from_mapping({**reference.as_dict(), 'species_id':sid, 'horizon_days':horizon})
                cutoff = day - timedelta(days=horizon); start = cutoff - timedelta(days=days-1)
                weather_key = hashlib.sha256(canonical(['weather',self._signature(area,start,cutoff),
                                                       area,cutoff.isoformat(),days,physical])).hexdigest()
                feature_key = hashlib.sha256(canonical(['features',weather_key,sid,day.isoformat(),horizon,
                    ref.version_id,ref.profile_id,ref.temporal_contract_id])).hexdigest()
                yield sid, oid, day, horizon, ref, area, start, cutoff, days, physical, weather_key, feature_key
            self.progress({'phase':'Preparing historical complete weeks',
                'message':f'{reference.version_id}: {index+1}/{len(visits)}',
                'completed_visits_in_unit':index+1, 'total_visits_in_unit':len(visits),
                'input_cache':dict(self.stats)})

    def samples(self, reference, test, requested=None):
        from rainmapper_core import mushroom_ml_runtime_features as features
        for sid, oid, day, horizon, ref, area, start, cutoff, days, physical, weather_key, feature_key in self._requests(reference, test, requested):
            sample = self._cached_feature(feature_key)
            if sample is None and reference.version_id in ('altitude_v2', 'biology_v3', 'biology_v4') and reference.temporal_contract_id.startswith('lag_'):
                sample = self._daily_sample(ref, sid, day, horizon, area, start, cutoff, days, physical, weather_key)
                self._remember_feature(feature_key, sample)
                self.stats['features_built'] += 1
            elif sample is None:
                raw_key = weather_key, ref.version_id, ref.profile_id, ref.temporal_contract_id
                raw_window = self.raw_windows.get(raw_key)
                prepared = raw_window[0] if raw_window is not None else None
                is_raw = ref.version_id not in ('altitude_v2', 'biology_v3', 'biology_v4')
                series = {} if prepared is not None else self._series(area,cutoff,days,physical,weather_key)
                if prepared is None and is_raw:
                    prepared = features.prepare_raw_runtime(ref, series)
                    # Count the complete slotted object's contents, including
                    # its typed array, without retaining daily weather arrays.
                    self.raw_windows.put(raw_key, (prepared, prepared.columns,
                        prepared.window.columns, prepared.window.values,
                        prepared.window.coverage, prepared.rain))
                    self.stats['raw_windows_built'] = self.stats.get('raw_windows_built', 0) + 1
                elif prepared is not None:
                    self.stats['raw_windows_reused'] = self.stats.get('raw_windows_reused', 0) + 1
                sample = features.build_runtime_features(ref, target_date=day, area_id=area,
                    area_context=self.areas[area], area_series=series, stations=self._stations(area,start,cutoff),
                    include_diagnostics=False, prepared_raw=prepared)
                # Fingerprints and inference consume only X and quality. The
                # identity/cutoff are already carried by the request. Never
                # serialize the diagnostic daily arrays once per forecast row.
                sample = {name: sample.get(name) for name in ('predictive_features', 'quality')}
                self._remember_feature(feature_key,sample); self.stats['features_built'] += 1
            else:
                self.stats['features_reused'] += 1
            yield sid, oid, day, horizon, sample

    def _cached_feature(self, key):
        value = self.feature_rows.get(key)
        if value is None and self.persist_features:
            value = self.inputs.read_shared(key)
            if value is not None:
                self.feature_rows.put(key, value)
        return value

    def _remember_feature(self, key, value):
        self.feature_rows.put(key, value)
        if self.persist_features:
            self.inputs.write(key, value)

    def _daily_sample(self, ref, sid, day, horizon, area, start, cutoff, days, physical, weather_key):
        from rainmapper_core import mushroom_ml_runtime_features as runtime
        from rainmapper_core.mushroom_ml_biology_v3 import EVENT_LOOKBACK_DAYS
        import math
        key = weather_key, sid, ref.version_id, ref.profile_id, ref.temporal_contract_id
        template = self.daily_templates.get(key)
        if template is None:
            base = runtime.build_runtime_features(replace(ref, horizon_days=1),
                target_date=cutoff+timedelta(days=1), area_id=area,
                area_context=self.areas[area], area_series=self._series(area,cutoff,days,physical,weather_key),
                stations=self._stations(area,start,cutoff), include_diagnostics=False)
            template = {name:base[name] for name in ('predictive_features','quality')}
            self.daily_templates.put(key, template)
            self.stats['daily_templates_built'] = self.stats.get('daily_templates_built', 0) + 1
        else:
            self.stats['daily_templates_reused'] = self.stats.get('daily_templates_reused', 0) + 1
        values, quality = dict(template['predictive_features']), copy.deepcopy(dict(template['quality']))
        angle = 2.0*math.pi*(day.month-1)/12.0
        for name, value in (('target_month_sin',round(math.sin(angle),6)),
                ('target_month_cos',round(math.cos(angle),6)), ('horizon_days',float(horizon))):
            if name in values:
                values[name] = value
        for name in ('days_since_rain_gt_2_at_target','days_since_significant_rain_at_target'):
            for block in (values, quality):
                if block.get(name) is not None:
                    block[name] = float(min(EVENT_LOOKBACK_DAYS,block[name]+horizon-1))
        return {'predictive_features':values,'quality':quality}

    def fingerprint(self, reference, test):
        # Estimator/weights do not enter runtime features. Their identity and
        # train/test tensors are already sealed separately by unit_key.
        visits = sorted({(m['species_id'], m['observation_id'], m['target_date'], m['area_id'])
                         for m in (s['metadata'] for s in test)})
        identity = hashlib.sha256(canonical([reference.version_id, reference.profile_id,
                                            reference.temporal_contract_id, visits])).hexdigest()
        if identity in self.fingerprints:
            self.fingerprints.move_to_end(identity)
            self.stats['fingerprints_reused'] = self.stats.get('fingerprints_reused', 0) + 1
            return self.fingerprints[identity]
        # Check the exact consumed station records/context before rebuilding a
        # single feature. This survives eviction of disposable numerical rows.
        # Observation labels/episodes remain protected separately by unit_key.
        inputs = hashlib.sha256(canonical(['week_fingerprint_v1', identity, self.input_revision]))
        for sid, oid, day, horizon, *_, feature_key in self._requests(reference, test):
            inputs.update(canonical([sid, oid, day.isoformat(), horizon, feature_key]))
        input_key = inputs.hexdigest()
        saved = self.inputs.read_fingerprint(input_key)
        if saved is not None:
            self.fingerprints[identity] = saved
            if len(self.fingerprints) > 4096:
                self.fingerprints.popitem(last=False)
            self.stats['fingerprints_restored'] = self.stats.get('fingerprints_restored', 0) + 1
            return saved
        h = hashlib.sha256()
        for sid, oid, day, horizon, sample in self.samples(reference,test):
            h.update(canonical([sid,oid,day.isoformat(),horizon,sample['predictive_features'],sample.get('quality')]))
        result = h.hexdigest()
        self.inputs.write_fingerprint(input_key, result)
        self.inputs.flush()
        self.fingerprints[identity] = result
        if len(self.fingerprints) > 4096:
            self.fingerprints.popitem(last=False)
        return result

    def input_fingerprint(self, reference, test):
        """Seal the union of consumed source windows, without expanding weeks.

        The visit identity determines every target/horizon. All lag members use
        the seven cutoffs before the visit; fixed-gap members use thirteen.
        Their weather intervals overlap, so one union contains the same source
        records. Labels and train/test tensors are sealed by the caller.
        """
        from rainmapper_core import mushroom_ml_model_catalog as catalog
        from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
        visits = sorted({(m['species_id'], m['observation_id'], m['target_date'], m['area_id'])
                         for m in (s['metadata'] for s in test)})
        identity = hashlib.sha256(canonical([reference.version_id, reference.profile_id,
                                             reference.temporal_contract_id, visits])).hexdigest()
        if identity in self.input_fingerprints:
            self.input_fingerprints.move_to_end(identity)
            return self.input_fingerprints[identity]
        profile = reference.version_id, reference.profile_id
        if profile not in self.requirements:
            ref = catalog.ModelRef.from_mapping({**reference.as_dict(), 'horizon_days':7})
            self.requirements[profile] = comparison._weather_requirements([ref], catalog_profiles=self.profiles)
        days, physical = self.requirements[profile]
        h = hashlib.sha256(canonical(['requested_week_sources_v3', self.input_revision, identity, days, physical]))
        cutoffs = 7 if reference.temporal_contract_id.startswith('lag_') else 13
        for area, target in sorted({(m[3], m[2]) for m in visits}):
            if area not in self.areas:
                continue
            self._area(area)
            target = date.fromisoformat(target)
            start, end = target-timedelta(days=cutoffs+days-1), target-timedelta(days=1)
            h.update(canonical([area, target.isoformat(), self._signature(area,start,end)]))
        value = h.hexdigest()
        self.input_fingerprints[identity] = value
        if len(self.input_fingerprints) > 2048:
            self.input_fingerprints.popitem(last=False)
        return value

    def defer(self, reference, key, fit_cache, fit_key):
        if fit_cache is None or not fit_cache.contains(fit_key):
            return False
        self.store.save_fit(key, reference, fit_key)
        return True

    def __call__(self, bundle, reference, test, key, *, requested=None):
        from rainmapper_core import mushroom_ml_runtime_inference as inference
        from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
        def save(identity, samples):
            if identity is None:
                return
            eligible = [s for _,_,s in samples if (s.get('quality') or {}).get('inference_eligible') is not False]
            predicted = iter(inference.predict_bundle_many(bundle,[s['predictive_features'] for s in eligible],
                species_ids=[identity[0]]*len(eligible),applicability_only=True)) if eligible else iter(())
            packet = []
            for day,horizon,sample in samples:
                if (sample.get('quality') or {}).get('inference_eligible') is False:
                    member = {'available':False,'reason':'runtime_feature_gates_failed'}
                else:
                    value = next(predicted)
                    interpreted = comparison._interpretation_features(sample)
                    member = {'available':True, 'prediction':{'probability':value['probability'],
                        'applicability':{'status':value['applicability']['status']}},
                        'features_used':{f:interpreted.get(f) for f in RAIN_FIELDS}}
                packet.append([day.isoformat(),horizon,member])
            self.store.write(key,*identity,packet, merge=requested is not None)
        current = None; packet = []
        for sid,oid,day,horizon,sample in self.samples(reference,test, requested):
            if current != (sid,oid):
                save(current,packet); current,packet = (sid,oid),[]
            packet.append((day,horizon,sample))
        save(current,packet)
        self.inputs.flush()

    def predict_requested(self, bundle, reference, rows, requested):
        """Stream only requested members, with at most 256 rows per inference."""
        from itertools import islice
        from rainmapper_core import mushroom_ml_runtime_inference as inference
        from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
        source = iter(self.samples(reference,rows,requested))
        while batch := list(islice(source,256)):
            eligible = [s for s in batch if (s[-1].get('quality') or {}).get('inference_eligible') is not False]
            values = iter(inference.predict_bundle_many(bundle,[s[-1]['predictive_features'] for s in eligible],
                species_ids=[s[0] for s in eligible],applicability_only=True)) if eligible else iter(())
            for sid,oid,day,h,sample in batch:
                if (sample.get('quality') or {}).get('inference_eligible') is False:
                    member = {'available':False,'reason':'runtime_feature_gates_failed'}
                else:
                    value = next(values)
                    interpreted = comparison._interpretation_features(sample)
                    member = {'available':True,'prediction':value,
                              'features_used':{f:interpreted.get(f) for f in RAIN_FIELDS}}
                yield sid,oid,day,h,member
        self.inputs.flush()


class RequestedPanels:
    """Fill missing members inside a worker replay, using completed fits only.

    The map never creates this object. One loaded model and one runtime builder
    are retained, while durable packets remain in the existing bounded store.
    """
    def __init__(self, store, fits, visits, build):
        self.store, self.fits, self.build = store, fits, build
        self.visits = {(v['species_id'], v['id']): v for v in visits}
        self.builder = None
        self.loaded = None
        self.models = OrderedDict(); self.model_bytes = 0
        from rainmapper_core.mushroom_map_competing import PointCache
        self.members = PointCache(max_bytes=4*1024*1024, max_entries=4096)
        self.stats = {'models_loaded': 0, 'members_built': 0, 'members_reused': 0}

    def _plan(self, unit, sid, oid, target, horizon, *, week_issue=None):
        from rainmapper_core import mushroom_ml_model_catalog as catalog
        visit = self.visits.get((sid, oid))
        if visit is None:
            raise ValueError('comparison_unknown_visit')
        recipe = self.store.fit(unit)
        reference = catalog.ModelArtifactRef.from_mapping(recipe['reference'])
        if reference.species_id not in (sid, 'all_species'):
            raise ValueError('comparison_fit_species_mismatch')
        day = date.fromisoformat(visit['day'])
        lag = reference.temporal_contract_id.startswith('lag_')
        valid = ((1 <= horizon <= 7 and 0 <= (day - (target - timedelta(days=horizon))).days - 1 <= 6)
                 if lag else horizon == 7 and abs((target-day).days) <= 6)
        if not valid:
            raise ValueError('comparison_member_outside_week')
        key = recipe['fit_key']
        requested = {(sid, oid, target, horizon)}
        if week_issue is not None:
            if not (week_issue <= day <= week_issue+timedelta(days=6) and
                    week_issue <= target <= week_issue+timedelta(days=6) and
                    (not lag or horizon == (target-week_issue).days+1)):
                raise ValueError('comparison_member_outside_week')
            requested = {(sid,oid,week_issue+timedelta(days=i),i+1 if lag else 7) for i in range(7)}
        return reference, key, visit, requested

    def _model(self, key):
        if self.loaded is None or self.loaded[0] != key:
            cached = self.models.get(key)
            if cached is not None:
                self.models.move_to_end(key)
                self.loaded = key, cached[0]
            else:
                value = self.fits.read(key)
                if value is None:
                    raise ValueError('comparison_completed_fit_missing')
                self.loaded = key, value['bundle']
                self.stats['models_loaded'] += 1
                # Budget is serialized numerical state plus a conservative
                # factor for live estimator objects; also cap object count.
                weight = 3*getattr(self.fits,'last_model_bytes',32*1024*1024)+65536
                limit = 64*1024*1024
                while self.models and (len(self.models)>=64 or self.model_bytes+weight>limit):
                    self.model_bytes -= self.models.popitem(last=False)[1][1]
                if weight <= limit:
                    self.models[key] = value['bundle'], weight
                    self.model_bytes += weight
        return self.loaded[1]

    def __call__(self, unit, sid, oid, target, horizon, *, week_issue=None):
        self.fill_many([(unit,sid,oid,target,horizon,week_issue)])

    def fill_many(self, requests):
        """Deduplicate at most 112 requested weeks before any model inference."""
        if len(requests)>112:
            raise ValueError('comparison_request_batch_limit')
        groups = OrderedDict()
        packets = {}
        def remember(unit,sid,oid,day,h,member):
            packets.setdefault((unit,sid,oid),[]).append((day.isoformat(),h,member))
        for unit,sid,oid,target,horizon,issue in requests:
            reference,key,visit,requested = self._plan(unit,sid,oid,target,horizon,week_issue=issue)
            for _,_,forecast,h in sorted(requested):
                try:
                    self.store._read(unit,sid,oid,forecast,h)
                    continue
                except MissingReplay:
                    pass
                identity = key,sid,visit['area'],forecast,h
                member = self.members.get(identity)
                if member is not None:
                    remember(unit,sid,oid,forecast,h,member)
                    self.stats['members_reused'] += 1
                else:
                    group = groups.setdefault(key,{'reference':reference,'members':{}})
                    entry = group['members'].setdefault(identity,{'visit':visit,'destinations':set()})
                    entry['destinations'].add((unit,sid,oid,forecast,h))
        for key,group in groups.items():
            bundle = self._model(key)
            if self.builder is None:
                self.builder = self.build()
            rows,lookup = {},{}
            for identity,entry in group['members'].items():
                visit = entry['visit']; _,sid,area,forecast,h = identity
                oid = visit['id']
                rows[sid,oid] = {'metadata':{'species_id':sid,'observation_id':oid,
                    'target_date':visit['day'],'area_id':area}}
                lookup[sid,oid,forecast,h] = identity,entry['destinations']
            for sid,oid,day,h,member in self.builder.predict_requested(
                    bundle,group['reference'],list(rows.values()),set(lookup)):
                identity,destinations = lookup[sid,oid,day,h]
                self.members.put(identity,member)
                self.stats['members_built'] += 1
                self.stats['members_reused'] += len(destinations)-1
                for unit,species,observation,forecast,horizon in destinations:
                    remember(unit,species,observation,forecast,horizon,member)
        with self.store.db:
            for (unit,sid,oid),packet in packets.items():
                # One bounded transaction per inference batch, preserving the
                # previous committed packets if any new packet fails validation.
                unique = {(row[0],row[1]):row for row in packet}
                self.store.write(unit,sid,oid,list(unique.values()),merge=True,commit=False)
