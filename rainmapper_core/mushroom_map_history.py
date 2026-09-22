"""Read-only historical station map, paged before materialization/transport.

Overview rows carry one last-rain record. Full station history is fetched on
opening a popup. All reads use the same immutable weather generation, and stop
before the selected reference date. No runner, CSV output or scientific jobs.
"""
from __future__ import annotations

from datetime import date, timedelta, datetime, timezone
import contextlib
import io
import json
import math
from pathlib import Path
import re
import time

CONTRACT = 'prediction_map_weather_history_v1'
CAPABILITY = 'map_weather_history_v1'
PERMISSION = 'can_use_historical_map'
PAGE_SIZE = 128
MAX_BYTES = 60 * 1024  # inside existing reader and map response limits
PERIODS = {'01d.geojson': 1, '07d.geojson': 7, '14d.geojson': 14,
           '21d.geojson': 21, '30d.geojson': 30, '60d.geojson': 60, '90d.geojson': 90}


def is_request(payload):
    return isinstance(payload, dict) and payload.get('contract') == CONTRACT


def parse(payload):
    from rainmapper_core.mushroom_map_weather import map_today
    required = {'contract', 'request_id', 'start_date', 'period', 'offset', 'execution', 'calendar_timezone', 'bounds'}
    optional = {'station', 'generation', 'settings', 'exclude_bounds'}
    if not isinstance(payload, dict) or not required <= payload.keys() or payload.keys() - required - optional:
        raise ValueError('invalid_history_request')
    if payload['contract'] != CONTRACT or not isinstance(payload['request_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', payload['request_id']):
        raise ValueError('invalid_history_request')
    if payload['execution'] not in ('local', 'worker') or payload['period'] not in PERIODS:
        raise ValueError('invalid_history_request')
    if type(payload['offset']) is not int or not 0 <= payload['offset'] < 10000 or payload['offset'] % PAGE_SIZE:
        raise ValueError('invalid_history_offset')
    bounds = payload['bounds']
    if (not isinstance(bounds, list) or len(bounds) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds)
            or not -180 <= bounds[0] < bounds[2] <= 180 or not -90 <= bounds[1] < bounds[3] <= 90):
        raise ValueError('invalid_history_bounds')
    excluded = payload.get('exclude_bounds', [])
    if not isinstance(excluded, list) or len(excluded) > 32:
        raise ValueError('invalid_history_bounds')
    for b in excluded:
        if (not isinstance(b, list) or len(b)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in b)
                or not -180 <= b[0] < b[2] <= 180 or not -90 <= b[1] < b[3] <= 90):
            raise ValueError('invalid_history_bounds')
    value = payload['start_date']
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('invalid_history_date')
    day = date.fromisoformat(value)
    if day.year < 2000 or day >= map_today(payload['calendar_timezone']):
        raise ValueError('invalid_history_date')
    station = payload.get('station')
    if station is not None and (not isinstance(station, dict) or set(station) != {'source', 'code'} or
            any(not isinstance(v, str) or not 0 < len(v) <= 128 for v in station.values()) or payload['offset'] != 0):
        raise ValueError('invalid_history_station')
    if 'generation' in payload and (not isinstance(payload['generation'], str) or not 0 < len(payload['generation']) <= 256):
        raise ValueError('invalid_history_generation')
    settings = payload.get('settings', {'include_aemet': True, 'minimum_rain': 0, 'history_records': 30, 'ignored': []})
    if (not isinstance(settings, dict) or set(settings) != {'include_aemet', 'minimum_rain', 'history_records', 'ignored'}
            or type(settings['include_aemet']) is not bool or type(settings['history_records']) is not int
            or not 1 <= settings['history_records'] <= 90
            or type(settings['minimum_rain']) not in (float, int) or not math.isfinite(settings['minimum_rain'])
            or not 0 <= settings['minimum_rain'] <= 300
            or not isinstance(settings['ignored'], list) or len(settings['ignored']) > 1000
            or any(not isinstance(v, str) or not 0 < len(v) <= 128 for v in settings['ignored'])):
        raise ValueError('invalid_history_settings')
    return {**payload, 'settings': settings}


def validate_result(result, request):
    if not isinstance(result, dict) or result.get('contract') != CONTRACT:
        raise ValueError('invalid_history_result')
    for key in ('request_id', 'start_date', 'period', 'offset', 'calendar_timezone', 'bounds'):
        if result.get(key) != request[key]:
            raise ValueError('history_result_mismatch')
    if result.get('station') != request.get('station'):
        raise ValueError('history_result_mismatch')
    if request.get('generation') and result.get('generation') != request['generation']:
        raise ValueError('history_generation_changed')
    if not isinstance(result.get('generation'), str) or not 0 < len(result['generation']) <= 256:
        raise ValueError('invalid_history_result')
    columns, rows = result.get('columns'), result.get('rows')
    if (not isinstance(columns, list) or not 2 <= len(columns) <= 1250 or len(set(columns)) != len(columns)
            or any(not isinstance(c, str) or not 0 < len(c) <= 128 for c in columns)
            or not {'Latitud', 'Longitud'} <= set(columns) or not isinstance(rows, list)
            or len(rows) > (1 if request.get('station') else PAGE_SIZE)):
        raise ValueError('invalid_history_rows')
    for row in rows:
        if not isinstance(row, list) or len(row) != len(columns):
            raise ValueError('invalid_history_rows')
        for cell in row:
            if cell is not None and not (type(cell) in (int, float) and math.isfinite(cell) or
                                       isinstance(cell, str) and len(cell) <= 512):
                raise ValueError('invalid_history_cell')
    total = result.get('total_stations')
    expected = None if request.get('station') or request['offset'] + PAGE_SIZE >= (total or 0) else request['offset'] + PAGE_SIZE
    if type(total) is not int or not 0 <= total <= 10000 or result.get('next_offset') != expected:
        raise ValueError('invalid_history_page')
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode()) > MAX_BYTES:
        raise ValueError('history_result_limit')


class HistoryReader:
    def __init__(self, data_root, stations_file):
        from rainmapper_core.mushroom_map_weather import PointWeatherReader
        self.weather = PointWeatherReader(data_root, stations_file)

    def _load(self, selected, start, end):
        import pyarrow.dataset as ds
        import pandas as pd
        from rainmapper_core import tomap
        from rainmapper_core.mushroom_map_weather import fingerprint
        first, last = start.strftime('%Y%m%d'), end.strftime('%Y%m%d')
        generation = self.weather.generation
        count, batches, checks = 0, [], {self.weather._catalog_path: self.weather._catalog_stat}
        limit = len(selected) * 90
        byte_count = 0
        for part in generation.partitions:
            codes = [c for s, c in selected if s == part.source]
            if not codes or part.max_local_date < first or part.min_local_date > last:
                continue
            path = generation.object_path(part.path)
            checks[path] = fingerprint(path)
            if checks[path][0] != part.size_bytes:
                raise ValueError('weather_partition_changed')
            dataset = ds.dataset(path, format='parquet')
            columns = [c for c in ['source', *tomap.PARQUET_TO_INCREMENTAL_COLUMNS] if c in dataset.schema.names]
            scan = dataset.scanner(columns=columns, filter=ds.field('station_code').isin(codes) &
                (ds.field('local_date') >= first) & (ds.field('local_date') <= last),
                batch_size=1024, batch_readahead=0, fragment_readahead=0, use_threads=False)
            for batch in scan.to_batches():
                count += batch.num_rows; byte_count += batch.nbytes
                if count > limit or byte_count > 16 * 1024 * 1024:
                    raise ValueError('history_input_limit')
                batches.append(batch.to_pandas())
        self.weather._check_files(checks)
        if not batches:
            return pd.DataFrame(), count, checks
        df = pd.concat(batches, ignore_index=True)
        if df.duplicated(['source', 'station_code', 'local_date']).any():
            raise ValueError('duplicate_weather_station_day')
        df['history_source'] = df['source']; df['history_code'] = df['station_code']
        df.rename(columns=tomap.PARQUET_TO_INCREMENTAL_COLUMNS, inplace=True)
        df['Data Local'] = pd.to_datetime(df['Data Local'], format='%Y%m%d')
        # Tomap requires stable display IDs; namespace codes across providers.
        df['Codi Estació'] = df['history_source'] + ':' + df['history_code']
        return tomap.ensure_incremental_columns(df), count, checks

    def execute(self, payload):
        import pandas as pd
        from rainmapper_core import tomap
        from rainmapper_core.geojson import clean_value
        started = time.perf_counter(); request = parse(payload)
        self.weather._refresh(); identity = self.weather._identity
        generation = self.weather.generation.generation_id
        if request.get('generation') and request['generation'] != generation:
            raise ValueError('history_generation_changed')
        settings = request['settings']; ignored = set(settings['ignored'])
        sources = {'meteocat', 'meteoclimatic', 'wunderground'} | ({'aemet'} if settings['include_aemet'] else set())
        west, south, east, north = request['bounds']
        catalog = sorted({(r['source'], r['station_code']) for r in self.weather.catalog
            if r['source'] in sources and type(r.get('lat')) in (int, float) and type(r.get('lon')) in (int, float)
            and south <= r['lat'] <= north and west <= r['lon'] <= east
            and not any(b[0] <= r['lon'] <= b[2] and b[1] <= r['lat'] <= b[3] for b in request.get('exclude_bounds', []))
            and str(r['station_code']).upper() not in ignored
            and (str(r['source']).lower(), str(r['station_code']).upper()) not in self.weather.disabled})
        station = request.get('station')
        selected = ([(station['source'], station['code'])] if station and (station['source'], station['code']) in catalog
                    else [] if station else catalog[request['offset']:request['offset'] + PAGE_SIZE])
        selected_keys = set(selected)
        positions = {(r['source'], r['station_code']): (r['lat'], r['lon']) for r in self.weather.catalog
                     if (r['source'], r['station_code']) in selected_keys}
        cutoff = date.fromisoformat(request['start_date']) - timedelta(days=1)
        df, count, checks = self._load(selected, cutoff-timedelta(days=89), cutoff)
        load_ms = (time.perf_counter()-started)*1000
        if df.empty:
            result_frame = pd.DataFrame(columns=['Latitud', 'Longitud'])
        else:
            period_start = cutoff - timedelta(days=PERIODS[request['period']]-1)
            period = df.loc[df['Data Local'] >= pd.Timestamp(period_start)].copy()
            # Existing aggregation semantics, no filesystem side effects.
            with contextlib.redirect_stdout(io.StringIO()):
                summary = tomap.create_grouped(period, settings['minimum_rain'])
                recent = tomap.create_last_rains(df if station else df.loc[pd.to_numeric(df['Total'], errors='coerce') > 0], Path('.'), settings['history_records'] if station else 1,
                    settings['minimum_rain'], save_to_csv=False)
            if summary.empty:
                result_frame = pd.DataFrame(columns=['Latitud', 'Longitud'])
            else:
                result_frame = pd.merge(summary, recent, on='Codi Estació', how='left')
                sources_by_id = df.drop_duplicates('Codi Estació').set_index('Codi Estació')
                for col in ('history_source', 'history_code'):
                    result_frame[col] = result_frame['Codi Estació'].map(sources_by_id[col])
                result_frame['Source'] = result_frame['history_source'].map({'meteocat':'Meteocat', 'meteoclimatic':'Meteoclimatic', 'wunderground':'Wunderground', 'aemet':'AEMET'})
                result_frame['Codi Estació'] = result_frame['history_code']
                result_frame['history_count'] = settings['history_records']
                result_frame['history_loaded'] = int(bool(station))
                # Some retained daily records lack location. The catalog used
                # for spatial selection has verified coordinates for the station.
                result_frame['history_coordinate_source'] = 'daily_record'
                for index, row in result_frame.iterrows():
                    if any(pd.isna(row[c]) or not math.isfinite(float(row[c])) for c in ('Latitud', 'Longitud')):
                        lat, lon = positions[(row['history_source'], row['history_code'])]
                        result_frame.loc[index, ['Latitud', 'Longitud']] = [lat, lon]
                        result_frame.loc[index, 'history_coordinate_source'] = 'station_catalog'
                result_frame['Ultima Lectura'] = pd.to_datetime(result_frame['Ultima Lectura'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
                result_frame['Data Local'] = pd.to_datetime(result_frame['Data Local'], errors='coerce').dt.strftime('%Y-%m-%d')
        columns = list(result_frame.columns)
        rows = []
        size = len(json.dumps(columns).encode()) + 2048
        for record in result_frame.itertuples(index=False, name=None):
            row = [clean_value(v.item() if hasattr(v, 'item') else v) for v in record]
            if any(isinstance(v, str) and len(v) > 512 for v in row):
                raise ValueError('history_text_limit')
            size += len(json.dumps(row, ensure_ascii=False, allow_nan=False).encode())
            if size > MAX_BYTES:
                raise ValueError('history_result_limit')
            rows.append(row)
        self.weather._check_files(checks); self.weather._refresh()
        if self.weather._identity != identity:
            raise ValueError('history_generation_changed')
        result = {**{k:request[k] for k in ('contract','request_id','start_date','period','offset','calendar_timezone','bounds')},
            'station': station, 'generation': generation, 'cutoff_date': cutoff.isoformat(),
            'columns': columns, 'rows': rows, 'total_stations': len(catalog),
            'next_offset': None if station or request['offset']+PAGE_SIZE >= len(catalog) else request['offset']+PAGE_SIZE,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'execution': {'mode': request['execution'], 'compute_ms': round((time.perf_counter()-started)*1000, 3),
                          'read_ms': round(load_ms,3), 'rows_read': count}}
        validate_result(result, request)
        return result
