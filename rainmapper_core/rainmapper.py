#!/usr/bin/env python

# make sure to install these packages before running:
#beautifulsoup4==4.12.3
#bokeh==3.2.2
#googlemaps==4.10.0
#lxml==4.9.3
#numpy==1.25.2
#pandas==2.2.2
#pytz==2023.3.post1
#Requests==2.32.3

# CHECK requirements.txt

import pandas as pd
from rainmapper_core.sources.sodapy_local import Socrata
from datetime import datetime, date, timedelta, time
import pytz
import os
import math
import re
import csv
import json
import sys
import time as time_module
import requests
from rainmapper_core.sources.meteoclimatic_local.client import MeteoclimaticClient
from rainmapper_core.config.const import _PYTHON_REQUIRES, _GMAPS_KEY, _DATA_PATH, _MAPS_PATH
from rainmapper_core.geocoding import GeocodingError, googlemaps_station_metadata
from rainmapper_core.incremental_upsert import upsert_incremental
from rainmapper_core.meteoclimatic_history import (
    OBSERVATION_COLUMNS as METEOCLIMATIC_OBSERVATION_COLUMNS,
    build_meteoclimatic_daily_incremental,
    read_meteoclimatic_observations,
    update_meteoclimatic_observations,
)
from rainmapper_core.wind import (
    WIND_COLUMNS,
    compass_to_degrees,
    optional_round,
    xema_daily_wind_fields,
)

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed



# Import parameters from shared constants
from rainmapper_core.config.const import   _codi_estacio,\
                    _qcodi_variable,\
                    _qcodi_variable2,\
                    _create_wunderground,\
                    _create_meteoclimatic,\
                    _create_meteocat,\
                    _create_aemet,\
                    _create_meteocat_conditions,\
                    _incremental_wunderground,\
                    _incremental_meteocat,\
                    _meteoclimatic_pattern,\
                    _incremental_meteoclimatic,\
                    _minima_lectura_meteoclimatic,\
                    _minima_lectura_meteocat,\
                    _minimum_rain_toprint,\
                    _minimum_rain_tomap,\
                    _create_googlemaps_files,\
                    _days_init,\
                    _days_end,\
                    _days_bucket,\
                    _meteocat_request_timeout,\
                    _meteocat_max_attempts,\
                    _print_dataframes,\
                    _print_totals,\
                    _max_threads,\
                    _max_attempts,\
                    _wunderground_full_log,\
                    _wunderground_daily_api,\
                    _backfill_station_filter,\
                    _last_number_rains,\
                    _create_daily_stats,\
                    _create_monthly_stats,\
                    _create_weekly_stats

# Add argument parser
import argparse
# Configure command-line arguments
parser = argparse.ArgumentParser(description='Rainmapper data update and map preparation script')
parser.add_argument('--create_meteoclimatic',
                    dest='_create_meteoclimatic',
                    nargs='?',
                    const=True,
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_create_meteoclimatic,
                    help='Fetch Meteoclimatic data (TRUE/FALSE, 1/0, YES/NO) -> Const=True, Default=True')
parser.add_argument('--create_meteocat',
                    dest='_create_meteocat',
                    nargs='?',
                    const=True,
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_create_meteocat,
                    help='Fetch Meteocat data (TRUE/FALSE, 1/0, YES/NO) -> Const=True, Default=True')
parser.add_argument('--create_wunderground',
                    dest='_create_wunderground',
                    nargs='?',
                    const=True,
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_create_wunderground,
                    help='Fetch Wunderground data (TRUE/FALSE, 1/0, YES/NO) -> Const=True, Default=True')
parser.add_argument('--create_aemet',
                    dest='_create_aemet',
                    nargs='?',
                    const=True,
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_create_aemet,
                    help='Fetch AEMET OpenData observations (TRUE/FALSE, 1/0, YES/NO) -> Const=False, Default=False')
parser.add_argument('--days_init',
                    dest='_days_init',
                    nargs='?',
                    const=_days_init,
                    type=int,
                    default= _days_init,
                    help='Days backward for accumulated rain lookup (negative, 0, or positive) -> Const=Default=-7')
parser.add_argument('--days_end',
                    dest='_days_end',
                    nargs='?',
                    const=_days_end,
                    type=int,
                    default=_days_end,
                    help='Days forward for accumulated rain lookup (negative, 0, or positive) -> Const=Default=0')
parser.add_argument('--nomaps',
                    dest='_create_googlemaps_files',
                    nargs='?',
                    const=False,
                    type=lambda x: not(str(x).lower() in ['true','1','yes']),
                    default=_create_googlemaps_files,
                    help='Do not create Google Maps files (TRUE/FALSE, 1/0, YES/NO) -> Const=False, Default=True')
parser.add_argument('--nototals',
                    dest='_print_totals',
                    nargs='?',
                    const=False,
                    type=lambda x: not((str(x).lower() in ['true','1','yes'])),
                    default=_print_totals,
                    help='Do not print totals (TRUE/FALSE, 1/0, YES/NO) -> Const=False, Default=True')
parser.add_argument('--days_bucket',
                    dest='_days_bucket',
                    nargs='?',
                    const=_days_bucket,
                    type=int,
                    default=_days_bucket,
                    help='Day bucket size for Meteocat reads (positive number) -> Const=Default=10')
parser.add_argument('--meteocat_request_timeout',
                    dest='_meteocat_request_timeout',
                    nargs='?',
                    const=_meteocat_request_timeout,
                    type=int,
                    default=_meteocat_request_timeout,
                    help='Meteocat/Socrata request timeout in seconds -> Const=Default=30')
parser.add_argument('--meteocat_max_attempts',
                    dest='_meteocat_max_attempts',
                    nargs='?',
                    const=_meteocat_max_attempts,
                    type=int,
                    default=_meteocat_max_attempts,
                    help='Meteocat/Socrata request attempts before failing -> Const=Default=3')
parser.add_argument('--max_threads',
                    dest='_max_threads',
                    nargs='?',
                    const=_max_threads,
                    type=int,
                    default=_max_threads,
                    help='Number of Wunderground threads -> Const=Default=3')
parser.add_argument('--max_attempts',
                    dest='_max_attempts',
                    nargs='?',
                    const=_max_attempts,
                    type=int,
                    default=_max_attempts,
                    help='Number of Wunderground scraper retries -> Const=Default=3')
parser.add_argument('--wunderground_full_log',
                    dest='_wunderground_full_log',
                    nargs='?',
                    const=True,
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_wunderground_full_log,
                    help='Print detailed Wunderground log (TRUE/FALSE, 1/0, YES/NO) -> Const=Default=False')
parser.add_argument('--wunderground_daily_api',
                    dest='_wunderground_daily_api',
                    nargs='?',
                    const=True,
                    type=lambda x: (str(x).lower() in ['true','1','yes']),
                    default=_wunderground_daily_api,
                    help='Use Wunderground daily JSON API before HTML fallback (TRUE/FALSE, 1/0, YES/NO) -> Const=Default=True')
parser.add_argument('--wunderground_local_start_date',
                    dest='_wunderground_local_start_date',
                    nargs='?',
                    const='',
                    type=str,
                    default='',
                    help='Optional Wunderground-only local calendar start date YYYY-MM-DD for monthly administrative backfills')
parser.add_argument('--wunderground_local_end_date',
                    dest='_wunderground_local_end_date',
                    nargs='?',
                    const='',
                    type=str,
                    default='',
                    help='Optional Wunderground-only local calendar end date YYYY-MM-DD for monthly administrative backfills')
parser.add_argument('--backfill_station_filter',
                    dest='_backfill_station_filter',
                    nargs='?',
                    const=_backfill_station_filter,
                    type=str,
                    default=_backfill_station_filter,
                    help='Optional administrative station filter, for example "wunderground::IORDIN1,IMERAN22"')
parser.add_argument('--meteoclimatic_pattern',
                    dest='_meteoclimatic_pattern',
                    nargs='?',
                    const=_meteoclimatic_pattern,
                    type=str,
                    default=_meteoclimatic_pattern,
                    help='Meteoclimatic station pattern(s) to read from RSS feed. Separate multiple patterns with comma, semicolon, or " - " -> Const=Default=ESCAT')

# Parse command-line arguments
args = parser.parse_args()

_create_meteoclimatic = args._create_meteoclimatic
_create_meteocat = args._create_meteocat
_create_wunderground = args._create_wunderground
_create_aemet = args._create_aemet
_days_init = args._days_init
_days_end = args._days_end
_days_bucket = args._days_bucket
_meteocat_request_timeout = max(1, args._meteocat_request_timeout)
_meteocat_max_attempts = max(1, args._meteocat_max_attempts)
_max_threads = args._max_threads
_max_attempts = args._max_attempts
_wunderground_full_log = args._wunderground_full_log
_wunderground_daily_api = args._wunderground_daily_api
_wunderground_local_start_date = (args._wunderground_local_start_date or '').strip()
_wunderground_local_end_date = (args._wunderground_local_end_date or '').strip()
_backfill_station_filter = args._backfill_station_filter
_meteoclimatic_pattern = args._meteoclimatic_pattern
_create_googlemaps_files = args._create_googlemaps_files
_print_totals = args._print_totals


def wunderground_log(message=""):
    if _wunderground_full_log:
        print(message)

def parse_meteoclimatic_patterns(pattern_text):
    patterns = [
        pattern.strip()
        for pattern in re.split(r"\s+-\s+|[,;\n]+", str(pattern_text))
        if pattern.strip()
    ]
    return patterns or [_meteoclimatic_pattern]


def parse_backfill_station_filter(filter_text):
    filters = {}
    raw_filter = str(filter_text or "").strip()
    if not raw_filter:
        return filters
    for segment in raw_filter.split(";"):
        segment = segment.strip()
        if not segment:
            continue
        if "::" not in segment:
            print(f'Ignoring invalid backfill station filter segment "{segment}". Use source::id1,id2.')
            continue
        source, ids_text = segment.split("::", 1)
        source = source.strip().lower()
        if not source:
            print(f'Ignoring invalid backfill station filter segment "{segment}". Missing source.')
            continue
        try:
            parsed_rows = list(csv.reader([ids_text], skipinitialspace=True))
            parsed_ids = parsed_rows[0] if parsed_rows else []
        except csv.Error:
            parsed_ids = ids_text.split(",")
        station_ids = {
            station_id.strip().strip("'\"").upper()
            for station_id in parsed_ids
            if station_id.strip().strip("'\"")
        }
        if station_ids:
            filters.setdefault(source, set()).update(station_ids)
    return filters


BACKFILL_STATION_FILTERS = parse_backfill_station_filter(_backfill_station_filter)


def backfill_station_ids_for(source_name):
    return BACKFILL_STATION_FILTERS.get(str(source_name or "").strip().lower(), set())

#print(_create_meteocat)
#print(_days_init)
#print(_days_end)

# Configure pandas to show all rows/columns
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# Runtime root is the directory that contains requirements.txt, stations.txt,
# Data/, Tomap/ and Plots/.  The implementation lives one level deeper in
# rainmapper_core/, so derive the root from the package location.
_script_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_requirements_file = os.path.join(_script_path, 'requirements.txt')

print ('=============')
print ('REQUIREMENTS:')
print ('=============')
print ('Python:'+_PYTHON_REQUIRES)
with open(_requirements_file, 'r') as requirements:
    requirements = requirements.read()
    print()
    print('Install packages:')
    print('-----------------')
    print(requirements)
print()

#In[0] ## GENERIC FUNCTION DEFINITIONS

# Thread-local timer used by the parallel source workers.
timer_state = threading.local()

def start_count(_legend=''):
    timer_state.start_wall = datetime.now()
    timer_state.start_perf = time_module.perf_counter()
    print('')
    print(_legend)

def end_count(_legend=''):
    start_perf = getattr(timer_state, 'start_perf', None)
    if start_perf is None:
        print("Error: start_count() not initialized.")
        return
    elapsed_time = timedelta(seconds=time_module.perf_counter() - start_perf)
    print(_legend+"--> Time elapsed: {}".format(elapsed_time))

def record_timing(timings, key, started_at):
    if isinstance(timings, dict):
        timings[key] = time_module.perf_counter() - started_at

def print_source_timings(source, timings):
    timing_parts = [
        f"{key}={value:.1f}s"
        for key, value in timings.items()
        if isinstance(value, (int, float))
    ]
    if timing_parts:
        print(f"{source} timings: " + ", ".join(timing_parts))

def local_to_utc(_datetime_local):
    # Obtiene la zona horaria local
    local_tz = pytz.timezone('Europe/Madrid')

    # Añade la información del timezone a la hora local
    _datetime_local = local_tz.localize(_datetime_local, is_dst=None)

    # Convierte la hora local a UTC
    _datetime_utc = _datetime_local.astimezone(pytz.utc)

    # Elimina la información de timezone antes de devolver el resultado
    _datetime_utc = _datetime_utc.replace(tzinfo=None)

    # Devuelve la hora en UTC sin información de timezone
    return _datetime_utc

def utc_to_local(_datetime_utc):
    # Obtiene la zona horaria local
    local_tz = pytz.timezone('Europe/Madrid')

    # Añade la información del timezone a la hora UTC
    _datetime_utc = pytz.utc.localize(_datetime_utc)

    # Convierte la hora UTC a la hora local
    _datetime_local = _datetime_utc.astimezone(local_tz)

    # Elimina la información de timezone antes de devolver el resultado
    _datetime_local = _datetime_local.replace(tzinfo=None)

    # Devuelve la hora local sin información de timezone
    return _datetime_local

def get_query_date(base_date,date_timedelta):
    query_date= local_to_utc(base_date + timedelta(days=date_timedelta)).strftime("%Y-%m-%dT%H:%M:00")
    return query_date

def get_data_inici():
    # GET START DATE in d-m-Y H:M:S format for file naming
    _data_inici = datetime.strptime(_start_date, "%Y-%m-%dT%H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
    return _data_inici

def get_data_fi():
    # GET  DATE in d-m-Y H:M:S format for file naming
    _data_fi = datetime.strptime(_end_date, "%Y-%m-%dT%H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
    return _data_fi

def get_googlemaps(lat,long):
    try:
        metadata = googlemaps_station_metadata(lat, long, _GMAPS_KEY, language='ES')
    except GeocodingError:
        print ('Error')
        return (0,'Municipi Not found','Provincia Not Found')

    print('Altitude'+ str(metadata['altitude']))
    return metadata['altitude'], metadata['municipality'], metadata['province']

## END GENERIC FUNCTION DEFINITIONS
#In[5] ## DATA RETRIEVAL functions
_INCREMENTAL_COLUMNS = [
    'Codi Estació',
    'Data Lectura',
    'Estació',
    'Comarca',
    'Municipi',
    'Provincia',
    'Altitud',
    'Latitud',
    'Longitud',
    'Ultima Lectura',
    'Variable',
    'Total',
    'Unitat',
    'Data Local',
    'Hora Local',
    'max_temp_celsius',
    'min_temp_celsius',
    'max_humidity_percent',
    'min_humidity_percent',
]

def create_empty_incremental():
    return pd.DataFrame(columns=_INCREMENTAL_COLUMNS)

def read_incremental(_dataframe, _nrows=None):
    csv_path = _DATA_PATH + _dataframe + '.csv'
    if not os.path.exists(csv_path):
        return create_empty_incremental()

    read_options = {'decimal': ',', 'low_memory': False}
    if _nrows is None:
        df = pd.read_csv(csv_path, **read_options)
    else:
        df = pd.read_csv(csv_path, nrows=_nrows, **read_options)
    #df['Data Lectura'] = pd.to_datetime(df['Ultima Lectura'])       # Construye 'Data Lectura' como datetime64
    if 'Data Lectura' in df.columns:
        df['Data Lectura'] = pd.to_datetime(df['Data Lectura'],format='%Y-%m-%d %H:%M:%S', errors='coerce') # 'Data Lectura' como datetime64
    if 'Total' in df.columns:
        df['Total'] = df['Total'].astype(float)     # Convierte la columna 'Total' a tipo float
    if 'Altitud' in df.columns:
        df['Altitud'] = df['Altitud'].astype(str)  # Convierte la columna 'Altitud' a tipo str
    if 'Latitud' in df.columns:
        df['Latitud'] = df['Latitud'].astype(str)  # Convierte la columna 'Latitud' a tipo str
    if 'Longitud' in df.columns:
        df['Longitud'] = df['Longitud'].astype(str)  # Convierte la columna 'Longitud' a tipo str
    if 'Data Local' in df.columns:
        df['Data Local'] = df['Data Local'].astype(str)  # Convierte la columna 'Data Local' a tipo str

    return df

SOURCE_STATUS_PATH = os.path.join(_DATA_PATH, 'source_status.json')
SOURCE_STATUSES = {}
SOURCE_RUNTIME_METRICS = {}
WUNDERGROUND_API_FALLBACK_ERRORS = 0
WUNDERGROUND_STATION_METADATA_CACHE = None
WUNDERGROUND_STATION_METADATA_LOCK = threading.Lock()

def write_source_statuses():
    payload = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'sources': SOURCE_STATUSES,
    }
    try:
        os.makedirs(_DATA_PATH, exist_ok=True)
        tmp_path = SOURCE_STATUS_PATH + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as status_file:
            json.dump(payload, status_file, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SOURCE_STATUS_PATH)
    except OSError as exc:
        print(f'WARNING: Could not write source status file {SOURCE_STATUS_PATH}: {exc}')

def count_incremental_stations(source_incremental):
    """Return unique station count for an incremental dataframe."""
    if source_incremental is None or source_incremental.empty or 'Codi Estació' not in source_incremental.columns:
        return 0
    return int(source_incremental['Codi Estació'].dropna().astype(str).str.strip().replace('', pd.NA).dropna().nunique())

def record_source_status(
    source,
    status,
    exit_code,
    message,
    rows=0,
    stations=0,
    stale_data_used=False,
    enabled=True,
    duration_seconds=None,
    started_at=None,
    finished_at=None,
    timings=None,
    extra=None,
):
    SOURCE_STATUSES[source] = {
        'status': status,
        'exit_code': exit_code,
        'message': str(message),
        'rows': int(rows) if rows is not None else 0,
        'stations': int(stations) if stations is not None else 0,
        'stale_data_used': bool(stale_data_used),
        'enabled': bool(enabled),
        'updated_at': datetime.now().isoformat(timespec='seconds'),
    }
    if duration_seconds is not None:
        SOURCE_STATUSES[source]['duration_seconds'] = round(float(duration_seconds), 3)
    if started_at is not None:
        SOURCE_STATUSES[source]['started_at'] = str(started_at)
    if finished_at is not None:
        SOURCE_STATUSES[source]['finished_at'] = str(finished_at)
    if timings:
        SOURCE_STATUSES[source]['timings'] = {
            str(key): round(float(value), 3)
            for key, value in timings.items()
            if value is not None
        }
    if isinstance(extra, dict):
        SOURCE_STATUSES[source].update(extra)
    write_source_statuses()

def record_source_runtime_metric(source, duration_seconds, started_at=None, finished_at=None, timings=None):
    SOURCE_RUNTIME_METRICS[source] = {
        'duration_seconds': round(float(duration_seconds), 3),
        'started_at': started_at,
        'finished_at': finished_at,
        'timings': timings or {},
    }

def source_runtime_metric(source):
    return SOURCE_RUNTIME_METRICS.get(source, {})

def source_extra_status(source):
    if source == 'Wunderground':
        return {'api_fallback_errors': WUNDERGROUND_API_FALLBACK_ERRORS}
    if source != 'AEMET':
        return {}
    try:
        from rainmapper_core import create_aemet as aemet_source
        return aemet_source.rate_limit_status(_DATA_PATH)
    except Exception as exc:
        print(f'WARNING: Could not read AEMET rate limit metrics: {exc}')
        return {}

def initialize_source_statuses():
    SOURCE_STATUSES.clear()
    SOURCE_RUNTIME_METRICS.clear()
    record_source_status('Meteoclimatic', 'PENDING', None, 'Waiting to run.', enabled=_create_meteoclimatic)
    record_source_status('Meteocat', 'PENDING', None, 'Waiting to run.', enabled=_create_meteocat)
    record_source_status('Wunderground', 'PENDING', None, 'Waiting to run.', enabled=_create_wunderground)
    record_source_status('AEMET', 'PENDING', None, 'Waiting to run.', enabled=_create_aemet)

def collect_source_result(source, future, incremental_name, enabled):
    try:
        source_df, source_incremental = future.result()
        status = 'OK' if enabled else 'DISABLED'
        message = 'Source processed successfully.' if enabled else 'Source disabled; using existing incremental data.'
        record_source_status(
            source,
            status,
            0,
            message,
            rows=len(source_incremental),
            stations=count_incremental_stations(source_incremental),
            stale_data_used=not enabled,
            enabled=enabled,
            extra=source_extra_status(source),
            **source_runtime_metric(source),
        )
        return source_df, source_incremental
    except Exception as exc:
        print('')
        print(f'{source} failed: {exc}')
        print(f'Trying to continue with existing {incremental_name}.csv data...')
        try:
            source_incremental = read_incremental(incremental_name)
            source_df = read_incremental(incremental_name, _nrows=0)
        except Exception as fallback_exc:
            print(f'Could not read fallback data for {source}: {fallback_exc}')
            source_incremental = create_empty_incremental()
            source_df = create_empty_incremental()

        if len(source_incremental) > 0:
            message = f'Source failed; reused {len(source_incremental)} existing incremental row(s). Error: {exc}'
            print(f'{source} status: STALE - {message}')
            record_source_status(
                source,
                'STALE',
                2,
                message,
                rows=len(source_incremental),
                stations=count_incremental_stations(source_incremental),
                stale_data_used=True,
                enabled=enabled,
                extra=source_extra_status(source),
                **source_runtime_metric(source),
            )
            return source_df, source_incremental

        message = f'Source failed and no existing incremental data was available. Error: {exc}'
        print(f'{source} status: NOK - {message}')
        record_source_status(
            source,
            'NOK',
            1,
            message,
            rows=0,
            stations=0,
            stale_data_used=False,
            enabled=enabled,
            extra=source_extra_status(source),
            **source_runtime_metric(source),
        )
        return source_df, source_incremental

def source_exit_code():
    enabled_sources = [
        payload for payload in SOURCE_STATUSES.values()
        if payload.get('enabled', True)
    ]
    if not enabled_sources:
        return 0

    usable_statuses = {'OK', 'STALE'}
    has_usable_source = any(
        str(payload.get('status', '')).upper() in usable_statuses
        for payload in enabled_sources
    )
    if not has_usable_source:
        return 1

    has_degraded_source = any(
        str(payload.get('status', '')).upper() != 'OK'
        for payload in enabled_sources
    )
    return 2 if has_degraded_source else 0

def get_myquery(_codi_estacio,_qcodi_variable, _qcodi_variable2,_start_date, _end_date): # Create _myquery for sum records
    _qcodi_estacio="'"+_codi_estacio+"'"    # BUILD STRING FOR STATION CODE IN CASE SOMEONE IS SELECTED
    _select_per_codi_variable = ' AND (codi_variable='+_qcodi_variable+' '+'OR codi_variable='+_qcodi_variable2+') '

    if _codi_estacio == ''  or _codi_estacio == 'ALL':
        _select_per_codi_estacio = ''
    else:
        _select_per_codi_estacio = ' AND (codi_estacio='+_qcodi_estacio+' '+'OR codi_estacio='+_qcodi_estacio+') '

    _myquery = "SELECT codi_estacio, max(data_lectura) as ultima_lectura, codi_variable, sum(valor_lectura) as valor_variable, \
            avg(valor_lectura) as valor_avg, median(valor_lectura) as valor_median \
            WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " +_select_per_codi_estacio +_select_per_codi_variable+" \
            AND valor_lectura > 0 \
            GROUP BY codi_estacio, codi_variable \
            ORDER BY valor_variable DESC, codi_estacio ASC LIMIT 1000"   # Limit to 1,000 stations
    return _myquery

def get_myquery_rain_all(_codi_estacio,_qcodi_variable, _qcodi_variable2,_start_date, _end_date): # Create _myquery for all records
    _qcodi_estacio="'"+_codi_estacio+"'"    # BUILD STRING FOR STATION CODE IN CASE SOMEONE IS SELECTED
    _select_per_codi_variable = ' AND (codi_variable='+_qcodi_variable+' '+'OR codi_variable='+_qcodi_variable2+') '

    if _codi_estacio == ''  or _codi_estacio == 'ALL':
        _select_per_codi_estacio = ''
    else:
        _select_per_codi_estacio = ' AND (codi_estacio='+_qcodi_estacio+' '+'OR codi_estacio='+_qcodi_estacio+') '

    #_myquery = "SELECT codi_estacio, data_lectura as ultima_lectura, codi_variable, valor_lectura as valor_variable \
    #        WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " +_select_per_codi_estacio +_select_per_codi_variable+" \
    #        AND valor_lectura > 0 \
    #        GROUP BY codi_estacio, codi_variable, data_lectura,valor_lectura \
    #        ORDER BY ultima_lectura,valor_variable DESC, codi_estacio ASC LIMIT 200000"   # Limit to 200,000 records

    _myquery = "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, codi_variable, sum(valor_lectura) as valor_variable \
            WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " +_select_per_codi_estacio +_select_per_codi_variable+" \
            AND valor_lectura >= 0 \
            GROUP BY codi_estacio, codi_variable, ultima_lectura \
            ORDER BY ultima_lectura,valor_variable DESC, codi_estacio ASC LIMIT 200000"   # Limit to 200,000 records

    #print('myquery_rain_all:',_myquery)
    return _myquery

def get_myquery_conditions_all(_codi_estacio,_start_date, _end_date): # Create _myquery for all records
    _qcodi_estacio="'"+_codi_estacio+"'"    # BUILD STRING FOR STATION CODE IN CASE SOMEONE IS SELECTED
    _select_per_codi_variable = " AND (codi_variable in ('40','42','3','44')) " # temp_max(40),temp_min(42),hum_max(3),hum_min(44)

    if _codi_estacio == ''  or _codi_estacio == 'ALL':
        _select_per_codi_estacio = ''
    else:
        _select_per_codi_estacio = ' AND (codi_estacio='+_qcodi_estacio+' '+'OR codi_estacio='+_qcodi_estacio+') '

    #_myquery = "SELECT codi_estacio, data_lectura as ultima_lectura, codi_variable, valor_lectura as valor_variable \
    #        WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " +_select_per_codi_estacio +_select_per_codi_variable+" \
    #        GROUP BY codi_estacio, codi_variable, data_lectura,valor_lectura \
    #        ORDER BY ultima_lectura,valor_variable DESC, codi_estacio ASC LIMIT 200000"   # Limit to 200,000 records
    _myquery = "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, codi_variable, \
                max(valor_lectura) as max_valor_variable, min(valor_lectura) as min_valor_variable \
            WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " \
                    + _select_per_codi_estacio +_select_per_codi_variable+" \
            GROUP BY codi_estacio, codi_variable, ultima_lectura \
            ORDER BY ultima_lectura, codi_estacio ASC LIMIT 200000"   # Limit to 200,000 records

    #print('myquery_conditions_all:',_myquery)
    return _myquery

def get_myquery_daily_wind_all(_codi_estacio,_start_date, _end_date):
    """Build a SoQL query for XEMA daily wind aggregates.

    Rainmapper's regular XEMA readings dataset (`nzvn-apee`) contains rain and
    current condition variables, but not the daily wind aggregate variables
    1503-1517. Those live in the daily XEMA dataset (`7bvh-jvq2`), so wind must
    be fetched separately and merged back by station/day.
    """
    _qcodi_estacio="'"+_codi_estacio+"'"    # BUILD STRING FOR STATION CODE IN CASE SOMEONE IS SELECTED
    _select_per_codi_variable = (
        " AND (codi_variable in ("
        "'1503','1504','1505',"  # daily scalar average wind speed at 10/6/2 m
        "'1509','1510','1511',"  # daily average wind direction at 10/6/2 m
        "'1512','1513','1514',"  # daily maximum gust speed at 10/6/2 m
        "'1515','1516','1517'"  # daily maximum gust direction at 10/6/2 m
        ")) "
    )

    if _codi_estacio == ''  or _codi_estacio == 'ALL':
        _select_per_codi_estacio = ''
    else:
        _select_per_codi_estacio = ' AND (codi_estacio='+_qcodi_estacio+' '+'OR codi_estacio='+_qcodi_estacio+') '

    _myquery = "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, codi_variable, valor as valor_variable \
            WHERE (data_lectura BETWEEN '"+_start_date+"' AND '"+_end_date+"') " \
                    + _select_per_codi_estacio +_select_per_codi_variable+" \
            ORDER BY ultima_lectura, codi_estacio ASC LIMIT 200000"

    return _myquery

def get_estacions_xema(): # Get estacions data from Meteocat
    estacions = socrata_get(socrata_metadades_estacions_xema, "station metadata", \
                       query="SELECT codi_estacio, nom_estacio, nom_comarca, nom_provincia, \
                       nom_municipi, altitud, latitud, longitud ORDER BY codi_estacio", exclude_system_fields='true')

    # Drop duplicates from 20240306
    estacions_xema = pd.DataFrame.from_records(estacions).drop_duplicates(subset='codi_estacio')

    #save_dataframe(estacions_xema, 'estacions_xema_downloaded', _save_to_csv=True, _save_to_excel=False,_decimal=',')

    estacions_xema.rename(columns={'codi_estacio':'Codi Estació',
                                   'nom_estacio':'Estació',
                                   'nom_comarca':'Comarca',
                                   'nom_provincia':'Provincia',
                                   'nom_municipi':'Municipi',
                                   'altitud':'Altitud',
                                   'latitud':'Latitud',
                                   'longitud':'Longitud',
                                   },inplace=True)
    #estacions_xema['Latitud'] = estacions_xema['Latitud'].astype(float)
    #estacions_xema['Longitud'] = estacions_xema['Longitud'].astype(float)

    ## MODI DE CODEX para pandas ##
    for col in ['Altitud', 'Latitud', 'Longitud']:
        estacions_xema[col] = pd.to_numeric(estacions_xema[col], errors='coerce')
    ## FIN MODI DE CODEX PARA PANDAS ##

    # Retrieve and update local file
    try:
        estacions_old = pd.read_csv(_DATA_PATH+'estacions_xema.csv').drop_duplicates(subset='Codi Estació')
    except FileNotFoundError:
        # If not existing file a new df is created
        estacions_old = pd.DataFrame(columns=estacions_xema.columns)

    ## MODI DE CODEX PARA PANDAS ##
    for col in ['Altitud', 'Latitud', 'Longitud']:
        estacions_old[col] = pd.to_numeric(estacions_old[col], errors='coerce')
    ## FIN MODI DE CODEX PARA PANDAS

    estacions_xema.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    estacions_old.set_index(keys=["Codi Estació"],drop=False,inplace=True)

    # Identify existing stations
    existing_stations = estacions_xema[estacions_xema.index.isin(estacions_old.index)].copy()


    # if changes Latitud/Longitud, or Altitud==0 in xema or in local DB
    #print (existing_stations)
    for index, station in existing_stations.iterrows():
        #print('Indice:',index  + \
        #   " - Altitud:" + station['Altitud'] + " - Altitud existing:" + str(estacions_old.loc[index,'Altitud']) + \
        #   " - Latitud:" + station['Latitud'] + " - Latitud existing:" + estacions_old.loc[index,'Latitud'] +\
        #   " - Longitud:" + station['Longitud']  + " - Longitud existing:" + estacions_old.loc[index,'Longitud'])


        ## MODI CODEX por bug logico ##
        #if  (station['Latitud'] != estacions_xema.loc[index,'Latitud']
        #    or station['Longitud'] != estacions_xema.loc[index,'Longitud']):
        if  (station['Latitud'] != estacions_old.loc[index,'Latitud']
            or station['Longitud'] != estacions_old.loc[index,'Longitud']):
        ## FIN MODI CODEX por bug logico ##
            #or estacions_old.loc[index,'Altitud'] == 0
            #or station['Altitud'] == 0):
            print ('Fetching altitude for station:'+ station['Codi Estació'] + '-->' + station['Estació'])
            _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
            existing_stations.loc[index,'Altitud'] = int(_altitud)
        else:
            existing_stations.loc[index,'Altitud'] = estacions_old.loc[index,'Altitud']

    estacions_old.update(existing_stations)

    # Identify new stations
    new_stations = estacions_xema[~estacions_xema.index.isin(estacions_old.index)].copy()

    for index, station in new_stations.iterrows():
        if index == 0:
            print('Checking Googlemaps data...')

        print ('Fetching altitude/municipality/province for new station:'+ station['Codi Estació'] + '-->' + station['Estació'])

        _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
        new_stations.loc[index,'Altitud'] = int(_altitud)

    estacions_old.reset_index(drop=True,inplace=True)
    new_stations.reset_index(drop=True,inplace=True)
    estacions_incremental = pd.merge(new_stations, estacions_old.drop_duplicates(), on=estacions_old.columns.to_list(),
                how='outer', indicator=False)
    estacions_incremental.sort_values(by=['Codi Estació'], ascending=[True],inplace=True)

    estacions_incremental.to_csv(_DATA_PATH+'estacions_xema.csv',index=False)
    return estacions_incremental

def get_variables_xema(): # Get variables data from Meteocat
    variables = socrata_get(socrata_metadades_variables_xema, "variable metadata", exclude_system_fields = 'true')
    variables_xema = pd.DataFrame.from_records(variables)
    variables_xema.rename(columns={'codi_variable':'Codi Variable',
                                   'nom_variable':'Variable',
                                   'unitat':'Unitat',
                                   'acronim':'Acronim',
                                   'codi_tipus_var':'Codi Tipus Variable',
                                   'decimals':'Decimals',
                                   },inplace=True)
    ###
    variables_xema.to_csv(_DATA_PATH+'variables_xema.csv',decimal=',',index=False)

    return variables_xema

def get_lectures_rain_xema(_myquery):  # Get lectures data from Meteocat
    lectures = socrata_get(socrata_lectures_xema, "rain readings", query=_myquery, exclude_system_fields='true')
    lectures_xema = pd.DataFrame.from_records(lectures)

    # If no records returned, return an empty dataframe
    if len(lectures_xema) == 0:
        return lectures_xema
        print(' ')
        print('NO RECORDS RETURNED FOR SELECTION -- Exiting program')
        print(' ')
        exit()

    if 'data_lectura' not in lectures_xema.columns:
        lectures_xema['data_lectura'] = lectures_xema['ultima_lectura']

    lectures_xema.rename(columns={'codi_estacio':'Codi Estació',
                                'ultima_lectura':'Ultima Lectura',
                                'codi_variable':'Codi Variable',
                                'valor_variable':'Total',
                                'data_lectura':'Data Lectura',
                                },inplace=True)
    return lectures_xema

def get_lectures_conditions_xema(_myquery):  # Get lectures data from Meteocat
    lectures = socrata_get(socrata_lectures_xema, "condition readings", query=_myquery, exclude_system_fields='true')
    lectures_xema = pd.DataFrame.from_records(lectures)

    # If no records returned, return an empty dataframe
    if len(lectures_xema) == 0:
        return lectures_xema
        print(' ')
        print('NO RECORDS RETURNED FOR SELECTION -- Exiting program')
        print(' ')
        exit()

    if 'data_lectura' not in lectures_xema.columns:
        lectures_xema['data_lectura'] = lectures_xema['ultima_lectura']

    lectures_xema.rename(columns={'codi_estacio':'Codi Estació',
                                'ultima_lectura':'Ultima Lectura',
                                'codi_variable':'Codi Variable',
                                'data_lectura':'Data Lectura',
                                },inplace=True)
    #print(lectures_xema.info())

    return lectures_xema

def get_lectures_daily_wind_xema(_myquery):
    """Fetch daily XEMA wind records and normalize them to Rainmapper columns."""
    lectures = socrata_get(socrata_daily_xema, "daily wind readings", query=_myquery, exclude_system_fields='true')
    lectures_xema = pd.DataFrame.from_records(lectures)

    if len(lectures_xema) == 0:
        return lectures_xema

    lectures_xema.rename(columns={'codi_estacio':'Codi Estació',
                                'ultima_lectura':'Ultima Lectura',
                                'codi_variable':'Codi Variable',
                                'valor_variable':'max_valor_variable',
                                },inplace=True)
    lectures_xema['min_valor_variable'] = lectures_xema['max_valor_variable']
    return lectures_xema

def get_results_rain_xema(results_xema:pd.DataFrame, estacions_df, variables_df):    # Create results_df from query to Meteocat data
    _myquery0 = get_myquery(_codi_estacio,_qcodi_variable, _qcodi_variable2,_start_date, _end_date) # Get summarized data (1 record per station)
    _myquery = get_myquery_rain_all(_codi_estacio, _qcodi_variable, _qcodi_variable2,_start_date, _end_date) # Get detailed data (all rain records)
    #print(_myquery)

    # Get lectures_df from Meteocat according to _myquery
    lectures_xema = get_lectures_rain_xema(_myquery)
    '''print('')
    print('RAIN XEMA:')
    print(lectures_xema)'''
    # If not records returned, return empty dataframe
    if lectures_xema.empty:
        return lectures_xema

    # Merge estacions_df data and reject non existing codi_estacio
    results_xema = (pd.merge(lectures_xema, estacions_df, on = 'Codi Estació', how = 'inner'))

    # Merge variables_df data and reject non existing codi_variable
    results_xema = (pd.merge(results_xema, variables_df, on = 'Codi Variable', how = 'inner'))
    results_xema = results_xema[['Codi Estació','Data Lectura','Estació','Comarca','Municipi','Provincia','Altitud',
                             'Latitud','Longitud','Ultima Lectura','Codi Variable',
                             'Variable','Total','Unitat','Decimals'
                            ]]
    results_xema['Total'] = results_xema['Total'].astype(float)
    results_xema['Altitud'] = results_xema['Altitud'].astype(str)
    results_xema['Latitud'] = results_xema['Latitud'].astype(str)
    results_xema['Longitud'] = results_xema['Longitud'].astype(str)

    pd.set_option('mode.chained_assignment', None)            # Reset warning on copy Dataframe
    results_xema.drop('Codi Variable', axis=1, inplace=True)  # Not needed by now
    results_xema.drop('Decimals', axis=1, inplace=True)       # Not needed by now
    '''results_df.rename(columns={'valor_variable':'Total',
                        'data_lectura':'Data Lectura',
                        'ultima_lectura':'Ultima Lectura',
                        'codi_estacio':'Codi Estació',
                        'nom_estacio':'Estació',
                        'nom_comarca':'Comarca',
                        'nom_provincia':'Provincia',
                        'nom_municipi':'Municipi',
                        'altitud':'Altitud',
                        'latitud':'Latitud',
                        'longitud':'Longitud',
                        'nom_variable':'Variable',
                        'unitat':'Unitat'
                        },inplace=True)'''

    # Create New Columns from only Date and only Time from 'ultima_lectura'
    results_xema['Data Local'] = results_xema['Ultima Lectura'].astype(str)
    results_xema['Hora Local'] = results_xema['Ultima Lectura'].astype(str)

    # Convert 'Ultima Lectura' to local time and format 'Data Local' & 'Hora Local'
    for i in range(len(results_xema)):
        results_xema.loc[i, 'Ultima Lectura'] = (datetime.strptime(results_xema.loc[i,'Ultima Lectura'],'%Y-%m-%dT%H:%M:%S.%f')
                                                  + timedelta(hours=2,seconds=1)).strftime("%Y/%m/%d %H:%M:%S")

        results_xema.loc[i,'Data Local'] = datetime.strptime(results_xema.loc[i,'Ultima Lectura']
                                                             ,'%Y/%m/%d %H:%M:%S').strftime("%Y%m%d")   # Set Date as only date from 'Ultima Lectura'
        results_xema.loc[i,'Hora Local'] = datetime.strptime(results_xema.loc[i,'Ultima Lectura']
                                                             ,'%Y/%m/%d %H:%M:%S').strftime("%H:%M:%S")  # Set Time as only time from 'Ultima Lectura'

    ## Convert 'Ultima Lectura' to 'Data Lectura' in datetime for index
    results_xema['Data Lectura'] = pd.to_datetime(results_xema['Ultima Lectura'],format='%Y/%m/%d %H:%M:%S')
    results_xema.sort_values(by=['Codi Estació', 'Data Lectura'], ascending=[True, False],inplace=True)
    return results_xema

def get_results_conditions_xema(results_xema:pd.DataFrame, estacions_df, variables_df):    # Create results_df from query to Meteocat data
    _myquery = get_myquery_conditions_all(_codi_estacio, _start_date, _end_date)    # Get daily data (temp/humidity)
    #print(_myquery)
    # Get lectures_df from Meteocat according to _myquery
    lectures_xema = get_lectures_conditions_xema(_myquery)
    '''print('')
    print('CONDITIONS XEMA:')
    print(lectures_xema)'''
    # If not records returned, return empty dataframe
    if lectures_xema.empty:
        return lectures_xema

    # Merge estacions_df data and reject non existing codi_estacio
    results_xema = (pd.merge(lectures_xema, estacions_df, on = 'Codi Estació', how = 'inner'))

    # Merge variables_df data and reject non existing codi_variable
    results_xema = (pd.merge(results_xema, variables_df, on = 'Codi Variable', how = 'inner'))
    results_xema = results_xema[['Codi Estació','Data Lectura','Estació','Comarca','Municipi','Provincia','Altitud',
                             'Latitud','Longitud','Ultima Lectura','Codi Variable',
                             'Variable','max_valor_variable','min_valor_variable','Unitat','Decimals'
                            ]]
    results_xema['max_valor_variable'] = results_xema['max_valor_variable'].astype(float)
    results_xema['min_valor_variable'] = results_xema['min_valor_variable'].astype(float)

    pd.set_option('mode.chained_assignment', None)            # Reset warning on copy Dataframe
    results_xema.drop('Decimals', axis=1, inplace=True)       # Not needed by now

    for i in range(len(results_xema)):
        results_xema.loc[i, 'Ultima Lectura'] = (datetime.strptime(results_xema.loc[i,'Ultima Lectura'],'%Y-%m-%dT%H:%M:%S.%f')
                                                  + timedelta(hours=2,seconds=1)).strftime("%Y/%m/%d %H:%M:%S")

    ## Convert 'Ultima Lectura' to 'Data Lectura' in datettime for index
    results_xema['Data Lectura'] = pd.to_datetime(results_xema['Ultima Lectura'],format='%Y/%m/%d %H:%M:%S')

# Pivotar el DataFrame para obtener max y min valores para 'Codi Variable' 40 y 42
    pivot_df = results_xema.pivot_table(index=['Codi Estació', 'Data Lectura',
                                               'Estació', 'Comarca','Municipi', 'Provincia',
#                                               'Ultima Lectura', 'Variable',
                                               ],
                            columns='Codi Variable',
                            values=['max_valor_variable', 'min_valor_variable'],
                            aggfunc='first').reset_index()

    pivot_df.columns = [f'{col[0]}_{col[1]}' if col[1] else col[0] for col in pivot_df.columns]

    for codi_variable in ('40', '42', '44', '3'):
        for value_prefix in ('max_valor_variable', 'min_valor_variable'):
            column = f'{value_prefix}_{codi_variable}'
            if column not in pivot_df.columns:
                pivot_df[column] = pd.NA

    # Agrupar por 'Codi Estació' y 'Data Lectura' y obtener los valores correspondientes a 'Codi Variable' 40 y 42
    pivot_df = pivot_df.groupby(['Codi Estació', 'Data Lectura']).agg({
        'Estació': 'first',
        'Comarca': 'first',
        'Municipi': 'first',
        'Provincia': 'first',
#        'Ultima Lectura': 'first',
        'max_valor_variable_40': 'first',
        'max_valor_variable_42': 'first',
        'min_valor_variable_40': 'first',
        'min_valor_variable_42': 'first',
        'max_valor_variable_44': 'first',
        'max_valor_variable_3': 'first',
        'min_valor_variable_44': 'first',
        'min_valor_variable_3': 'first'
    }).reset_index()

    # Crear un nuevo DataFrame con las columnas requeridas
    new_columns = ['Codi Estació', 'Data Lectura',
                   'Estació', 'Comarca', 'Municipi', 'Provincia',
#                   'Ultima Lectura',
                   'max_temp_celsius',
#                   'min_temp_max_celsius',
#                   'max_temp_min_celsius',
                   'min_temp_celsius',
                   'max_humidity_percent',
#                   'min_humidity_max_percent',
#                   'max_humidity_min_percent',
                   'min_humidity_percent'
                   ]
    conditions_xema = pd.DataFrame(columns=new_columns)

    # Llenar el nuevo DataFrame con los valores pivotados
    conditions_xema['Codi Estació'] = pivot_df['Codi Estació']
    conditions_xema['Data Lectura'] = pivot_df['Data Lectura']
    conditions_xema['Estació'] = pivot_df['Estació']
    conditions_xema['Comarca'] = pivot_df['Comarca']
    conditions_xema['Municipi'] = pivot_df['Municipi']
    conditions_xema['Provincia'] = pivot_df['Provincia']
#    conditions_xema['Ultima Lectura'] = pivot_df['Ultima Lectura']
    conditions_xema['max_temp_celsius'] = pivot_df[('max_valor_variable_40')].astype(str)
    conditions_xema['min_temp_celsius'] = pivot_df[('min_valor_variable_42')].astype(str)
    conditions_xema['max_humidity_percent'] = pivot_df[('max_valor_variable_3')].astype(str)
    conditions_xema['min_humidity_percent'] = pivot_df[('min_valor_variable_44')].astype(str)

    conditions_xema.sort_values(by=['Codi Estació', 'Data Lectura'], ascending=[True, False],inplace=True)

    return conditions_xema

def get_results_daily_wind_xema(estacions_df):
    """Return one normalized daily wind row per XEMA station/day.

    Wind speeds are published by Meteocat in m/s and converted later to km/h by
    `xema_daily_wind_fields`. The output intentionally uses the same merge keys
    as the temperature/humidity dataframe so rain rows can receive wind fields
    without changing the existing incremental identity.
    """
    _myquery = get_myquery_daily_wind_all(_codi_estacio, _start_date, _end_date)
    lectures_xema = get_lectures_daily_wind_xema(_myquery)
    if lectures_xema.empty:
        return lectures_xema

    results_xema = pd.merge(lectures_xema, estacions_df, on='Codi Estació', how='inner')
    results_xema = results_xema[[
        'Codi Estació', 'Ultima Lectura', 'Codi Variable', 'max_valor_variable',
        'Estació', 'Comarca', 'Municipi', 'Provincia',
    ]]
    results_xema['max_valor_variable'] = pd.to_numeric(results_xema['max_valor_variable'], errors='coerce')
    results_xema['min_valor_variable'] = results_xema['max_valor_variable']

    for i in range(len(results_xema)):
        results_xema.loc[i, 'Ultima Lectura'] = (datetime.strptime(results_xema.loc[i,'Ultima Lectura'],'%Y-%m-%dT%H:%M:%S.%f')
                                                  + timedelta(hours=2,seconds=1)).strftime("%Y/%m/%d %H:%M:%S")

    results_xema['Data Lectura'] = pd.to_datetime(results_xema['Ultima Lectura'],format='%Y/%m/%d %H:%M:%S')

    pivot_df = results_xema.pivot_table(index=['Codi Estació', 'Data Lectura',
                                               'Estació', 'Comarca','Municipi', 'Provincia',
                                               ],
                            columns='Codi Variable',
                            values=['max_valor_variable', 'min_valor_variable'],
                            aggfunc='first').reset_index()

    pivot_df.columns = [f'{col[0]}_{col[1]}' if col[1] else col[0] for col in pivot_df.columns]

    for codi_variable in (
        '1503', '1504', '1505',
        '1509', '1510', '1511',
        '1512', '1513', '1514',
        '1515', '1516', '1517',
    ):
        column = f'max_valor_variable_{codi_variable}'
        if column not in pivot_df.columns:
            pivot_df[column] = pd.NA

    wind_xema = pivot_df[['Codi Estació', 'Data Lectura', 'Estació', 'Comarca', 'Municipi', 'Provincia']].copy()
    wind_fields = pivot_df.apply(xema_daily_wind_fields, axis=1, result_type='expand')
    for column in wind_fields.columns:
        wind_xema[column] = wind_fields[column]

    wind_xema.sort_values(by=['Codi Estació', 'Data Lectura'], ascending=[True, False],inplace=True)
    return wind_xema

## END DATA RETRIEVAL FUNCTION DEFINITIONS
#In[8]  ##  Dataframes creation functions

def filter_results(df: pd.DataFrame, _minima_pluja):             # Filter data according to parameters
    df=df.copy()
    df = df.query('Total >= @_minima_pluja')
    return df

def save_dataframe(df:pd.DataFrame, _file_name, _save_to_csv=True, _save_to_excel=False, _decimal=','):
    #
    if _save_to_csv:                                                     # Save df to csv
        df.to_csv(_DATA_PATH+_file_name+'.csv', decimal=_decimal, index=False)
    #
    if _save_to_excel:                                                   # Save df to or excel
        df.to_excel(_DATA_PATH+_file_name+'.xlsx', decimal=_decimal, index=False)
    #

def save_dataframe_tomap(df, _file_name, _save_to_csv=True, _save_to_excel=False,_decimal='.'):
    #
    if _save_to_csv:                                                     # Save df to csv
        df.to_csv(_MAPS_PATH+_file_name+'.csv', decimal=_decimal, index=False)
    #
    if _save_to_excel:                                                   # Save df to or excel
        df.to_excel(_MAPS_PATH+_file_name+'.xlsx', decimal=_decimal, index=False)
    #

def save_incremental_meteocat(csv_param:pd.DataFrame, _save_to_excel, timings=None):             # Save incremental Dataframe
    csv=csv_param.copy()
    #
    try:
        # Intentar cargar el archivo CSV
        step_start_time = time_module.perf_counter()
        csv_old = read_incremental('Meteocat_incremental')
        record_timing(timings, 'read_incremental_seconds', step_start_time)
        #print('Meteocat incremental leido:',csv_old.info())
    except FileNotFoundError:
        # Si el archivo no se encuentra, crear un DataFrame vacío con las mismas columnas que csv
        csv_old = pd.DataFrame(columns=csv.columns)
    #
    # Upsert by station/day: fresh non-null values win, but fresh NaN values
    # keep existing non-null fields such as Meteocat temperature/humidity.
    step_start_time = time_module.perf_counter()
    csv_incremental = upsert_incremental(csv, csv_old)
    csv_incremental.sort_values(by=['Codi Estació','Data Local'], ascending=[True,False],inplace=True)
    csv_incremental.reset_index(drop=True, inplace=True)
    record_timing(timings, 'upsert_incremental_seconds', step_start_time)
	#
    # Filter rain > 0
    #csv_incremental = filter_results(csv_incremental,_minima_lectura_meteocat)
    #
	# Save incremental Dataframe to csv
    step_start_time = time_module.perf_counter()
    csv_incremental.to_csv(_DATA_PATH+'Meteocat_incremental.csv', decimal=',', index=False) #  Save to csv All incremental rain readings
    record_timing(timings, 'write_incremental_seconds', step_start_time)
    #print('Meteocat incremental salvado:',csv_incremental.info())
    #
	# Save csv_incremental Dataframe to Excel

    if _save_to_excel:
        csv_incremental['Altitud'] = csv_incremental['Altitud'].astype(float)
        csv_incremental['Latitud'] = csv_incremental['Latitud'].astype(float)
        csv_incremental['Longitud'] = csv_incremental['Longitud'].astype(float)
        csv_incremental.to_excel(_DATA_PATH+'Meteocat_incremental.xlsx', index=False) # Save to excel All incremental rain readings

    return csv_incremental

def save_incremental_meteoclimatic(csv_param:pd.DataFrame, _save_to_excel, timings=None):        # Save incremental Dataframe
    csv=csv_param.copy()
    #
    try:
        # Intentar cargar el archivo CSV
        #csv_old = pd.read_csv(_DATA_PATH+'Meteoclimatic_incremental.csv',decimal=',')
        step_start_time = time_module.perf_counter()
        csv_old = read_incremental('Meteoclimatic_incremental')
        record_timing(timings, 'read_incremental_seconds', step_start_time)

    except FileNotFoundError:
        # Si el archivo no se encuentra, crear un DataFrame vacío con las mismas columnas que csv
        csv_old = pd.DataFrame(columns=csv.columns)

    observations_path = _DATA_PATH+'Meteoclimatic_observations_incremental.csv'
    step_start_time = time_module.perf_counter()
    if os.path.exists(observations_path):
        observations_old = read_meteoclimatic_observations(observations_path)
    else:
        observations_old = pd.DataFrame(columns=METEOCLIMATIC_OBSERVATION_COLUMNS)
    record_timing(timings, 'read_observations_seconds', step_start_time)

    step_start_time = time_module.perf_counter()
    observations_incremental = update_meteoclimatic_observations(csv, observations_old)
    record_timing(timings, 'upsert_observations_seconds', step_start_time)

    step_start_time = time_module.perf_counter()
    observations_incremental.to_csv(observations_path, decimal=',', index=False)
    record_timing(timings, 'write_observations_seconds', step_start_time)

    step_start_time = time_module.perf_counter()
    csv = build_meteoclimatic_daily_incremental(observations_incremental)
    record_timing(timings, 'build_daily_seconds', step_start_time)

    # Upsert by station/day: fresh non-null values win, but fresh NaN values
    # keep existing non-null fields from earlier successful reads.
    step_start_time = time_module.perf_counter()
    csv_incremental = upsert_incremental(csv, csv_old)

    csv_incremental.sort_values(by=['Codi Estació','Data Local'], ascending=[True,False],inplace=True)
    csv_incremental.reset_index(drop=True, inplace=True)
    record_timing(timings, 'upsert_incremental_seconds', step_start_time)
    #print(' ')
	#
    # Refresh Station data on incremental local DB from local DB of Stations
    step_start_time = time_module.perf_counter()
    estacions_meteoclimatic_df = pd.read_csv(_DATA_PATH+'estacions_meteoclimatic.csv',decimal=',')

    estacions_meteoclimatic_df.set_index(keys='Codi Estació',drop=False,inplace=True)
    csv_incremental.set_index(keys='Codi Estació',drop=False,inplace=True)
    csv_incremental.update(estacions_meteoclimatic_df)
    record_timing(timings, 'station_incremental_update_seconds', step_start_time)

    # Filter rain > _minima_lectura_meteoclimatic (Daily rain in Meteoclimatic - Discard minimum readings as are errors)
    #csv_incremental = filter_results(csv_incremental,_minima_lectura_meteoclimatic)

    csv_incremental.reset_index(drop=True, inplace=True)

	# Save incremental Dataframe to csv
    step_start_time = time_module.perf_counter()
    csv_incremental.to_csv(_DATA_PATH+'Meteoclimatic_incremental.csv', decimal=',', index=False) #  Save to csv All incremental rain readings
    record_timing(timings, 'write_incremental_seconds', step_start_time)
	#
	# Save csv_incremental Dataframe to Excel

    if _save_to_excel:
        csv_incremental['Altitud'] = csv_incremental['Altitud'].astype(float)
        csv_incremental['Latitud'] = csv_incremental['Latitud'].astype(float)
        csv_incremental['Longitud'] = csv_incremental['Longitud'].astype(float)
        csv_incremental.to_excel(_DATA_PATH+'Meteoclimatic_incremental.xlsx', index=False) # Save to excel All incremental rain readings

    return csv_incremental

def save_incremental_wunderground(csv_param:pd.DataFrame, _save_to_excel, timings=None):        # Save incremental Dataframe
    csv=csv_param.copy()
    #
    try:
        # Intentar cargar el archivo CSV
        #csv_old = pd.read_csv(_DATA_PATH+'Meteoclimatic_incremental.csv',decimal=',')
        step_start_time = time_module.perf_counter()
        csv_old = read_incremental('Wunderground_incremental')
        record_timing(timings, 'read_incremental_seconds', step_start_time)

    except FileNotFoundError:
        # Si el archivo no se encuentra, crear un DataFrame vacío con las mismas columnas que csv
        csv_old = pd.DataFrame(columns=csv.columns)

    # Upsert by station/day: fresh non-null values win, but fresh NaN values
    # keep existing non-null fields from earlier successful reads.
    step_start_time = time_module.perf_counter()
    csv_incremental = upsert_incremental(csv, csv_old)

    csv_incremental.sort_values(by=['Codi Estació','Data Local'], ascending=[True,False],inplace=True)
    csv_incremental.reset_index(drop=True, inplace=True)
    record_timing(timings, 'upsert_incremental_seconds', step_start_time)
    #print(' ')
	#
    '''
    PENDIENTE DE VER SI HAY QUE AÑADIR
    # Refresh Station data on incremental local DB from local DB of Stations
    estacions_wunderground_df = pd.read_csv(_DATA_PATH+'estacions_wunderground.csv',decimal=',')

    estacions_wunderground_df.set_index(keys='Codi Estació',drop=False,inplace=True)
    csv_incremental.set_index(keys='Codi Estació',drop=False,inplace=True)
    csv_incremental.update(estacions_wunderground_df)
    '''
    # Filter rain > _minima_lectura_meteoclimatic (Daily rain in Meteoclimatic - Discard minimum readings as are errors)
    #csv_incremental = filter_results(csv_incremental,_minima_lectura_meteoclimatic)

    csv_incremental.reset_index(drop=True, inplace=True)

	# Save incremental Dataframe to csv
    step_start_time = time_module.perf_counter()
    csv_incremental.to_csv(_DATA_PATH+'Wunderground_incremental.csv', decimal=',', index=False) #  Save to csv All incremental rain readings
    record_timing(timings, 'write_incremental_seconds', step_start_time)
	#
	# Save csv_incremental Dataframe to Excel

    if _save_to_excel:
        csv_incremental['Altitud'] = csv_incremental['Altitud'].astype(float)
        csv_incremental['Latitud'] = csv_incremental['Latitud'].astype(float)
        csv_incremental['Longitud'] = csv_incremental['Longitud'].astype(float)
        csv_incremental.to_excel(_DATA_PATH+'Wundewrground_incremental.xlsx', index=False) # Save to excel All incremental rain readings

    return csv_incremental

def create_total_dataframe(csv_param:pd.DataFrame, _save_to_excel, _save_to_csv):               # Create Total Dataframe
    csv=csv_param.copy()
    #csv['Data Lectura'] = pd.to_datetime(csv['Ultima Lectura'])
    csv.set_index(keys=['Data Lectura'],drop=False,inplace=True)

    csv_total = csv.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Latitud',
                            'Longitud',
                            'Altitud',
                            'Variable',
                            'Unitat'],dropna=False). \
                    agg({'Codi Estació':'last',
                        'Estació':'last',
                        'Comarca':'last',
                        'Municipi':'last',
                        'Provincia':'last',
                        'Altitud':'last',
                        'Latitud':'last',
                        'Longitud':'last',
                        'Data Lectura':'max',
                        'Variable':'last',
                        'Total':'sum',
                        'Unitat':'last'
                        }). \
                    round(1). \
                    rename(columns={'Data Lectura':'Ultima Lectura'}).\
                    sort_values(by=['Total'], ascending=[False],inplace=False)
    #
    csv_total.reset_index(drop=True,inplace=True)
    #
    # Sort in descending order by Accumulated precipitation
    #
    csv_total.sort_values(by=['Total'], ascending=False,inplace=True)
    csv_total.reset_index(drop=True,inplace=True)

    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    if _save_to_csv:
        csv_total.to_csv(_DATA_PATH+'Plujes_Acumulades_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Total rain
    if _save_to_excel:
        csv_total['Altitud'] = csv_total['Altitud'].astype(float)
        csv_total['Latitud'] = csv_total['Latitud'].astype(float)
        csv_total['Longitud'] = csv_total['Longitud'].astype(float)
        csv_total.to_excel(_DATA_PATH+'Plujes_Acumulades_'+_data_inici+' al '+_data_fi+'.xlsx', index=False) # Save to excel Total rain
    #
    return csv_total

def create_total_meteoclimatic(csv_param:pd.DataFrame, _save_to_excel, _save_to_csv):               # Create Total Dataframe
    csv=csv_param.copy()
    for column in (
        'wind_avg_kmh',
        'wind_min_kmh',
        'wind_max_kmh',
        'wind_gust_kmh',
        'wind_direction_deg',
        'wind_gust_direction_deg',
        'wind_observation_count',
        'wind_source_height_m',
    ):
        if column not in csv.columns:
            csv[column] = pd.NA
    #csv['Data Lectura'] = pd.to_datetime(csv['Ultima Lectura'])
    csv.set_index(keys=['Data Lectura'],drop=False,inplace=True)

    csv_total = csv.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Latitud',
                            'Longitud',
                            'Altitud',
                            'Variable',
                            'Unitat'],dropna=False). \
                    agg({'Codi Estació':'last',
                        'Estació':'last',
                        'Comarca':'last',
                        'Municipi':'last',
                        'Provincia':'last',
                        'Altitud':'last',
                        'Latitud':'last',
                        'Longitud':'last',
                        'Data Lectura':'max',
                        'Variable':'last',
                        'Total':'sum',
                        'Unitat':'last',
                        'max_temp_celsius':'last',
                        'min_temp_celsius':'last',
                        'max_humidity_percent':'last',
                        'min_humidity_percent':'last',
                        'wind_avg_kmh':'last',
                        'wind_min_kmh':'last',
                        'wind_max_kmh':'last',
                        'wind_gust_kmh':'last',
                        'wind_direction_deg':'last',
                        'wind_gust_direction_deg':'last',
                        'wind_observation_count':'last',
                        'wind_source_height_m':'last'
                        }). \
                    round(1). \
                    rename(columns={'Data Lectura':'Ultima Lectura'}).\
                    sort_values(by=['Total'], ascending=[False],inplace=False)
    #
    csv_total.reset_index(drop=True,inplace=True)
    csv_total['max_temp_celsius'] = csv_total['max_temp_celsius'].astype(str)
    csv_total['min_temp_celsius'] = csv_total['min_temp_celsius'].astype(str)
    csv_total['max_humidity_percent'] = csv_total['max_humidity_percent'].astype(str)
    csv_total['min_humidity_percent'] = csv_total['min_humidity_percent'].astype(str)
    #
    # Sort in descending order by Accumulated precipitation
    #
    #csv_total.sort_values(by=['Total'], ascending=False,inplace=True)
    #csv_total.reset_index(drop=True,inplace=True)

    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    if _save_to_csv:
        csv_total.to_csv(_DATA_PATH+'Plujes_Acumulades_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Total rain
    if _save_to_excel:
        csv_total['Altitud'] = csv_total['Altitud'].astype(float)
        csv_total['Latitud'] = csv_total['Latitud'].astype(float)
        csv_total['Longitud'] = csv_total['Longitud'].astype(float)
        csv_total.to_excel(_DATA_PATH+'Plujes_Acumulades_'+_data_inici+' al '+_data_fi+'.xlsx', index=False) # Save to excel Total rain
    #
    return csv_total


def create_daily_dataframe(csv_param:pd.DataFrame, _save_to_excel):               # Create daily Dataframe
    csv_daily = csv_param.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Altitud',
                            'Latitud',
                            'Longitud',
                            'Variable',
                            'Unitat',
                            pd.Grouper(key='Data Lectura',freq='D')])['Total']. \
                            sum().\
                            reset_index().\
                            rename(columns={'Data Lectura':'Data Pluja'}).\
                            round(1)

    csv_daily = csv_daily[['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Altitud',
                            'Latitud',
                            'Longitud',
                            'Variable',
                            'Total',
                            'Unitat',
                            'Data Pluja'
                            ]]

    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    csv_daily.to_csv(_DATA_PATH+'Plujes_Diaries_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Daily rain
    if  _save_to_excel:
        csv_daily.to_excel(_DATA_PATH+'Plujes_Diaries_'+_data_inici+' a '+_data_fi+'.xlsx', index=False)      # Save to excel Daily rain
    return

def create_weekly_dataframe(csv_param:pd.DataFrame, _save_to_excel):                        # Create weekly Dataframe
    csv_weekly = csv_param.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Latitud',
                            'Longitud',
                            'Altitud',
                            'Variable',
                            'Unitat',
                            pd.Grouper(key='Data Lectura',freq='W')])['Total'].sum().reset_index().round(1)
    #
    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    csv_weekly.to_csv(_DATA_PATH+'Plujes_Setmanals_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Weekly rain
    if  _save_to_excel:
        csv_weekly.to_excel(_DATA_PATH+'Plujes_Setmanals_'+_data_inici+' a '+_data_fi+'.xlsx', index=False) # Save to excel Weekly rain
    return

def create_monthly_dataframe(csv_param:pd.DataFrame,_save_to_excel):                       # Create monthly Dataframe
    csv_monthly = csv_param.groupby(['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Latitud',
                            'Longitud',
                            'Altitud',
                            'Variable',
                            'Unitat',
                            pd.Grouper(key='Data Lectura',freq='M')])['Total'].sum().reset_index().round(1)
    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    csv_monthly.to_csv(_DATA_PATH+'Plujes_Mensuals_'+_data_inici+' a '+_data_fi+'.csv', decimal=',', index=False) #  Save to csv Monthly rain
    if _save_to_excel:
        csv_monthly.to_excel(_DATA_PATH+'Plujes_Mensuals_'+_data_inici+' a '+_data_fi+'.xlsx', index=False) # Save to excel Monthly rain

def print_dataframes(df:pd.DataFrame, columns_to_print=None):  # Define a function to print some columns from a Dataframe
    if columns_to_print is None:        # If no columns list supplied, use default
        default_columns = ['Codi Estació',
                           'Data Lectura',
                           'Estació',
                           'Municipi',
                           'Provincia',
                           'Altitud',
                           'Variable',
                           'Total',
                           'Unitat']
        columns_to_print = default_columns

    # Select columns to print
    print(df[columns_to_print].to_string(index=True))

def print_totals_per_station(csv_total:pd.DataFrame): # Print totals per station (csv_total) for selection in Terminal sorted by accumulated precipitation DESC
    #
    _data_inici = get_data_inici()
    _data_fi = get_data_fi()
    print(" ")
    print("Accumulated rain data from XEMA, Meteoclimatic, and Wunderground:",len(csv_total), "stations reporting rain")
    print("Minimum accumulated rain:",_minimum_rain_toprint, "mm")
    print("Start date:", utc_to_local(datetime.strptime(_data_inici,"%d-%m-%Y %H:%M:%S")).strftime("%d-%m-%Y %H:%M:%S"))
    print("End date:", utc_to_local(datetime.strptime(_data_fi,"%d-%m-%Y %H:%M:%S")).strftime("%d-%m-%Y %H:%M:%S"))
    if len(csv_total) != 0:
        print("Station code:"+_codi_estacio+" ("+(csv_total.iloc[-1]["Estació"])+")"
            if _codi_estacio!='' and _codi_estacio!='ALL'
            else "All stations")
        print(" ")
    #
    for i in range(len(csv_total)):
        _this_codi_estacio = csv_total.iloc[i]['Codi Estació']
        _this_nom_estacio = csv_total.iloc[i]['Estació']
        #_this_nom_estacio = re.sub(r'\s*\[.*?\]\s*', '', _this_nom_estacio)
        #_this_nom_estacio = re.sub(r'^\[|\]$', '', _this_nom_estacio)
        _this_nom_municipi = csv_total.iloc[i]['Municipi']
        _this_valor_variable = csv_total.iloc[i]['Total']
        _this_unitat = csv_total.iloc[i]['Unitat']
        _this_ultima_lectura =csv_total.iloc[i]['Ultima Lectura'].strftime("%d/%m/%Y %H:%M:%S CET")
    #
    #   Print records from csv Dataframe in Console
    #
        if False:
            print("RECORD:" + \
                    str(i), \
                    "Station: "+ \
                    _this_codi_estacio+" - " + \
                    _this_nom_estacio+" [" + _this_nom_municipi+ \
                    "] - Accumulated rain:", \
                    _this_valor_variable,\
                    _this_unitat, \
                    "- Last reading: " + \
                    _this_ultima_lectura)
        elif True:
            print(f"REC: {i:<3} Station: {_this_codi_estacio:<19} - {_this_nom_estacio:<40} [{_this_nom_municipi:<30}] - Accumulated rain: {_this_valor_variable:<5} {_this_unitat:3} - Last rain: {_this_ultima_lectura:<20}")

        else:
            print("RECORD:"+str(i),"Station: "+ _codi_estacio+" (UNDEFINED) - Accumulated rain:"\
                    ,_valor_variable,_unitat,"- Last reading: "+\
                    _ultima_lectura)
    print("")

def refresh_estacions_meteoclimatic(meteoclimatic_df:pd.DataFrame):
    csv = meteoclimatic_df[['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Altitud',
                            'Latitud',
                            'Longitud']].copy()

    try:
        # Try to read local DB of stations
        csv_old = pd.read_csv(_DATA_PATH+'estacions_meteoclimatic.csv',decimal=',')
    except FileNotFoundError:
        # If not existing file a new df is created
        csv_old = pd.DataFrame(columns=csv.columns)

    #print(csv_old.info())
    csv_old.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    #
    csv.set_index(keys=["Codi Estació"],drop=False,inplace=True)

    # Utilizamos una expresión regular para encontrar el último par de paréntesis en Estació y lo eliminamos
    # Utilizamos apply y una función lambda para aplicar la operación a cada elemento de la columna
    csv['Estació'] = csv['Estació'].apply(lambda x: re.sub(r'\([^)]*\)(?=[^()]*$)', '', x))

    # Get elevation for existing stations in 'estacions_meteoclimatic.csv' if not set or changed lat or long
    existing_stations = csv[csv.index.isin(csv_old.index )]

    for index, station in existing_stations.iterrows():
        try:
            _check_altitud = float(csv_old['Altitud'][index])
            if math.isnan(_check_altitud) or \
                csv_old.loc[index,'Municipi'] == 'To be set later' or \
                csv_old.loc[index,'Provincia'] == 'To be set later':
                _isvalid = False
            else:
                existing_stations.loc[index,'Altitud'] = csv_old.loc[index,'Altitud']
                existing_stations.loc[index,'Municipi'] = csv_old.loc[index,'Municipi']
                existing_stations.loc[index,'Provincia'] = csv_old.loc[index,'Provincia']
                _isvalid = True
        except ValueError:
            _isvalid = False

        if  station['Latitud'] != csv_old.loc[index,'Latitud'] or \
            station['Longitud'] != csv_old.loc[index,'Longitud'] or \
            not _isvalid:
            print ('Fetching altitude for station:'+ station['Codi Estació'] + '-->' + station['Estació'])
            #print('Estacion a actualizar', existing_stations['Codi Estació'][index])
            _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
            #print(_altitud,_municipi,_provincia)
            #existing_stations['Altitud'][index] = int(get_googlemaps(station['Latitud'], station['Longitud'],'elevation'))
            existing_stations.loc[index,'Altitud'] = int(_altitud)
            existing_stations.loc[index,'Municipi'] = _municipi
            existing_stations.loc[index,'Provincia'] = _provincia

    # Get elevation, municipi & provincia for new stations added to 'estacions_meteoclimatic.csv'
    new_stations = csv[ ~csv.index.isin(csv_old.index) ]
    for index, station in new_stations.iterrows():
        print ('Fetching altitude/municipality/province for new station:'+ station['Codi Estació'] + '-->' + station['Estació'])
        _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
        #new_stations['Altitud'][index] = int(get_googlemaps(station['Latitud'], station['Longitud'],'elevation'))
        new_stations.loc[index,'Altitud'] = int(_altitud)
        new_stations.loc[index,'Municipi'] = _municipi
        new_stations.loc[index,'Provincia'] = _provincia

    csv_old.update(existing_stations)
    csv.update(existing_stations)
    csv.update(new_stations)
    #
    # Merge new records from csv & csv_old into csv_incremental
    csv_old.reset_index(drop=True,inplace=True)
    new_stations.reset_index(drop=True,inplace=True)
    csv_incremental = pd.merge(new_stations, csv_old.drop_duplicates(), on=csv_old.columns.to_list(),
                how='outer', indicator=False)
    csv_incremental.sort_values(by=['Codi Estació'], ascending=[True],inplace=True)

    csv_incremental.reset_index(drop=True, inplace=True)

    # Save local DB of Stations for Meteoclimatic - Each new station read is added to local DB
    csv_incremental.to_csv(_DATA_PATH+'estacions_meteoclimatic.csv',decimal=',',index=False)
    return csv

def create_meteoclimatic(_save_to_csv, timings=None):

    client = MeteoclimaticClient()
    patterns = parse_meteoclimatic_patterns(_meteoclimatic_pattern)
    print("Meteoclimatic patterns:", ", ".join(patterns))

    step_start_time = time_module.perf_counter()
    meteoclimatic_frames = []
    failed_patterns = []
    for pattern_index, pattern in enumerate(patterns):
        if pattern_index > 0:
            time_module.sleep(2)
        try:
            pattern_df = client.weather_sel_stations(pattern)
            print(f"Meteoclimatic pattern {pattern}: {len(pattern_df)} station(s)")
            if not pattern_df.empty:
                meteoclimatic_frames.append(pattern_df)
        except Exception as exc:
            failed_patterns.append((pattern, exc))
            print(f"Meteoclimatic pattern {pattern} failed: {exc}")

    if not meteoclimatic_frames:
        if failed_patterns:
            failed_text = ", ".join(pattern for pattern, _ in failed_patterns)
            raise RuntimeError(f"No Meteoclimatic data recovered. Failed pattern(s): {failed_text}")
        raise RuntimeError("No Meteoclimatic data recovered.")
    record_timing(timings, 'fetch_seconds', step_start_time)

    step_start_time = time_module.perf_counter()
    meteoclimatic_df = pd.concat(meteoclimatic_frames, ignore_index=True)
    meteoclimatic_df.drop_duplicates(subset=["Codi Estació"], keep="first", inplace=True)
    meteoclimatic_df.reset_index(drop=True, inplace=True)
    meteoclimatic_df = create_total_meteoclimatic(meteoclimatic_df, _save_to_excel = False, _save_to_csv=False)
    record_timing(timings, 'build_current_seconds', step_start_time)

    step_start_time = time_module.perf_counter()
    meteoclimatic_df['Data Local'] = meteoclimatic_df['Ultima Lectura']
    meteoclimatic_df['Hora Local'] = meteoclimatic_df['Ultima Lectura']

    meteoclimatic_df['Data Lectura'] = meteoclimatic_df['Ultima Lectura'].dt.tz_localize(tz=None)
    for i in range(len(meteoclimatic_df)):
        meteoclimatic_df.loc[i,'Data Lectura'] = utc_to_local(meteoclimatic_df.loc[i,'Data Lectura'])

    meteoclimatic_df['Ultima Lectura']= meteoclimatic_df['Data Lectura'].dt.strftime("%Y/%m/%d %H:%M:%S")
    meteoclimatic_df['Data Local'] = meteoclimatic_df['Data Lectura'].dt.strftime("%Y%m%d") # Set Date as only date from 'Ultima Lectura'
    meteoclimatic_df['Hora Local'] = meteoclimatic_df['Data Lectura'].dt.strftime("%H:%M:%S")  # Set Time as only time from 'Ultima Lectura'
    record_timing(timings, 'normalize_dates_seconds', step_start_time)

    step_start_time = time_module.perf_counter()
    # Set order of columns to match Meteocat's columns order
    cols = meteoclimatic_df.columns.tolist()
    cols = cols[:1]+cols[-1:]+ cols[1:-1]
    meteoclimatic_df = meteoclimatic_df[cols].reset_index(drop=True)

    # Extract Provincia & Municipi from Station name on meteoclimatic data
    meteoclimatic_df['Provincia'] = meteoclimatic_df['Estació'].str.extract(r'\((.*?)\)')
    meteoclimatic_df['Municipi_temp'] = meteoclimatic_df['Estació'].str.extract(r'^(.*?) -')
    # Old pandas < 3.0 style, now avoided because it triggers chained-assignment FutureWarning:
    # meteoclimatic_df['Municipi_temp'].fillna(meteoclimatic_df['Estació'].str.extract(r'^(.*?) \(')[0], inplace=True)
    meteoclimatic_df['Municipi_temp'] = meteoclimatic_df['Municipi_temp'].fillna(meteoclimatic_df['Estació'].str.extract(r'^(.*?) \(')[0])  # pandas 3.0-compatible: assign the filled Series back to the original column.
    meteoclimatic_df['Municipi'] = meteoclimatic_df['Municipi_temp']
    meteoclimatic_df.drop(columns=['Municipi_temp'], inplace=True)
    record_timing(timings, 'normalize_columns_seconds', step_start_time)

    # Refresh local DB of stations (to not search for elevation in googlemaps all the time)
    step_start_time = time_module.perf_counter()
    refreshed_stations_df = refresh_estacions_meteoclimatic(meteoclimatic_df)
    record_timing(timings, 'station_catalog_seconds', step_start_time)

    # Update Altitud on meteoclimatic_df from local DB stations
    step_start_time = time_module.perf_counter()
    refreshed_stations_df.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    meteoclimatic_df.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    meteoclimatic_df.update(refreshed_stations_df)

    meteoclimatic_df.reset_index(drop=True,inplace=True)
    meteoclimatic_df.sort_values(by=['Codi Estació', 'Data Lectura'], ascending=[True, False],inplace=True)
    record_timing(timings, 'station_update_seconds', step_start_time)

    return meteoclimatic_df                             # Same format than Meteocat and with elevation set

def scrap_wunderground_station(weather_station_url, launchtime):

    thread_name = threading.current_thread().name
    station_started_at = datetime.now()
    station_start_time = time_module.perf_counter()
    wunderground_log(f"[{thread_name}] Starting thread for URL: {weather_station_url} at launch time: {launchtime}")

    session = requests.Session()
    timeout = 5
    global START_DATE
    global END_DATE
    global UNIT_SYSTEM
    global FIND_FIRST_DATE
    global wunderground_header

    global wunderground_file_name

    if FIND_FIRST_DATE:
        # find first date
        first_date_with_data = Utils.find_first_data_entry(weather_station_url=weather_station_url, start_date=START_DATE)
        # if first date found
        if(first_date_with_data != -1):
            START_DATE = first_date_with_data

    url_gen = Utils.date_url_generator(weather_station_url, START_DATE, END_DATE)
    station_name = weather_station_url.split('/')[-1]
    file_prefix = station_name
    summary_station_id = station_name
    summary_station_name = ''
    summary_rows = 0
    summary_errors = []
    summary_api_errors = 0

    if MERGE_DATA:
        file_prefix = 'MERGED'

    wunderground_file_name = os.path.join(_script_path,f'{file_prefix}_{START_DATE}_to_{END_DATE}_at_{launchtime}.csv')

    # Crea un Lock para controlar el acceso al archivo
    file_lock = threading.Lock()

    with open(wunderground_file_name, 'a+', newline='') as csvfile:
        if MONTHLY:
            fieldnames = ['StationID','Date','Time','StationName','Comarca','Municipi',
                          'Provincia','Elevation','Latitude','Longitude',
                          'High','Avg','Low','High_1','Avg_1','Low_1','High_2','Avg_2','Low_2','High_3','Avg_3','Low_3',
                          'High_4','Low_4','Sum']
        else:
            fieldnames = ['StationID','Date', 'Time','StationName','Comarca','Municipi',
                          'Provincia','Elevation','Latitude','Longitude',
                          'Temperature','Dew_Point','Humidity',	'Wind','Speed','Gust','Pressure','Precip_Rate',
                          'Precip_Accum','UV','Solar']
        with file_lock:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if wunderground_header:
            # Write the correct headers to the CSV file
            if UNIT_SYSTEM == "metric":
                if MONTHLY:
                    with file_lock:
                        writer.writerow({'StationID':'Codi Estació','Date': 'Data',
                                    'Time': 'Hora','StationName':'Estació','Comarca':'Comarca','Municipi':'Municipi',
                                    'Provincia':'Provincia','Elevation':'Altitud','Latitude':'Latitud','Longitude':'Longitud',
                                    'High': 'TempHigh_C','Avg': 'TempAvg_C','Low': 'TempLow_C',
                                    'High_1': 'DPHigh_C','Avg_1': 'DPAvg_C', 'Low_1': 'DPLow_C','High_2': 'HumHigh_%',
                                    'Avg_2': 'HumAvg_%','Low_2': 'HumLow_%','High_3': 'SpeedHigh_kmh','Avg_3': 'SpeedAv_kmh',
                                    'Low_3': 'SpeedLow_kmh','High_4': 'PressHigh_hPa','Low_4': 'PressLow_hPa','Sum': 'Rain_mm'})
                else:
                    # 12:04 AM	24.4 C	18.3 C	69 %	SW	0.0 km/h	0.0 km/h	1,013.88 hPa	0.00 mm	0.00 mm	0	0 w/m²
                    with file_lock:
                        writer.writerow({'StationID':'Codi Estació','Date': 'Data', 'Time': 'Hora',
                                    'StationName':'Estació','Comarca':'Comarca','Municipi':'Municipi',
                                    'Provincia':'Provincia','Elevation':'Altitud','Latitude':'Latitud','Longitude':'Longitud',
                                    'Temperature': 'Temperature_C','Dew_Point': 'Dew_Point_C',
                                    'Humidity': 'Humidity_%','Wind': 'Wind','Speed': 'Speed_kmh','Gust': 'Gust_kmh',
                                    'Pressure': 'Pressure_hPa','Precip_Rate': 'Precip_Rate_mm','Precip_Accum': 'Precip_Accum_mm',
                                    'UV': 'UV','Solar': 'Solar_w/m2'})
            elif UNIT_SYSTEM == "imperial":
                # 12:04 AM	75.9 F	65.0 F	69 %	SW	0.0 mph	0.0 mph	29.94 in	0.00 in	0.00 in	0	0 w/m²
                with file_lock:
                   writer.writerow({'StationID':'Codi Estació','Date': 'Data', 'Time': 'Hora',
                                'StationName':'Estació','Comarca':'Comarca','Municipi':'Municipi',
                                'Provincia':'Provincia','Elevation':'Altitud_f','Latitude':'Latitud','Longitude':'Longitud',
                                'Temperature': 'Temperature_F','Dew_Point': 'Dew_Point_F',
                                'Humidity': 'Humidity_%','Wind': 'Wind','Speed': 'Speed_mph','Gust': 'Gust_mph',
                                'Pressure': 'Pressure_in','Precip_Rate': 'Precip_Rate_in','Precip_Accum': 'Precip_Accum_in',
                                'UV': 'UV','Solar': 'Solar_w/m2'})
            else:
                raise Exception("please set 'unit_system' to either \"metric\" or \"imperial\"! ")
            wunderground_header = False

        #print(f'url_gen: {list(url_gen)}')
        for date_string, url in url_gen:
            try:
                wunderground_log('')
                wunderground_log('==================================================================================================')
                wunderground_log(f'Retrieving Station Data for {weather_station_url}')

                #scraper = parseStationData(weather_station_url)
                scraper = None
                html_string = None
                metadata = cached_wunderground_station_metadata(weather_station_url)

                if metadata:
                    station_ID = metadata['station_ID']
                    station_name = metadata['station_name']
                    location_name = metadata['location_name']
                    elevation = metadata['elevation']
                    latitude = metadata['latitude']
                    longitude = metadata['longitude']
                else:
                    scraper = parseStationData(url, max_attempts=_max_attempts, full_log=_wunderground_full_log)
                    try:
                        # html_string se usa mas abajo si la API no esta disponible
                        html_string = scraper.fetch_data()
                        if _wunderground_full_log:
                            end_count(_legend='Fetched data for '+url)

                        # Fetch and log station metadata.
                        #elevation, latitude, longitude, station_name, station_ID, location_name = scraper.get_station_header()
                        station_ID, station_name, location_name, elevation, latitude, longitude = scraper.get_station_header()

                    except Exception as e:
                        summary_errors.append(str(e))
                        wunderground_log(str(e))
                        continue

                summary_station_id = station_ID
                summary_station_name = station_name
                wunderground_log(f'Station code: {station_ID}')
                wunderground_log(f'Station name: {station_name}')
                wunderground_log(f'Municipality: {location_name}')
                wunderground_log(f"Latitude: {latitude}")
                wunderground_log(f"Longitude: {longitude}")
                wunderground_log(f"Altitude: {elevation} m")
# Fin modi
                data_to_write = None
                if _wunderground_daily_api and MONTHLY and UNIT_SYSTEM == "metric":
                    try:
                        data_to_write = fetch_wunderground_api_rows(
                            weather_station_url,
                            date_string,
                            station_ID,
                            station_name,
                            location_name,
                            elevation,
                            latitude,
                            longitude,
                            session,
                            timeout,
                        )
                    except WundergroundDailyApiError as e:
                        summary_api_errors += 1
                        print(f'Wunderground API failed for {station_ID} {date_string}: {e}. Falling back to HTML scraper.')

                if data_to_write is None:
                    wunderground_log(f'Scraping data from {url}')
                    if scraper is None:
                        scraper = parseStationData(url, max_attempts=_max_attempts, full_log=_wunderground_full_log)
                    if html_string is None:
                        html_string = scraper.fetch_data()
                        if _wunderground_full_log:
                            end_count(_legend='Fetched data for '+url)
                    history_table = False
                    max_attempts = _max_attempts  # Número máximo de intentos
                    attempts = 0  # Contador de intentos
                    while not history_table and attempts < max_attempts:
                        attempts += 1
                        #html_string = session.get(url, timeout=timeout)
                        doc = lh.fromstring(html_string.content)
                        history_table = doc.xpath('//*[@id="main-page-content"]/div/div/div/lib-history/div[2]/lib-history-table/div/div/div/table/tbody')
                        if not history_table:
                            wunderground_log("refreshing session")
                            session = requests.Session()
                            html_string = session.get(url, timeout=timeout)


                    # parse html table rows
                    #print(f'Parsing html table rows from {url}')

                    data_rows = Parser.parse_html_table(date_string,
                                                        history_table,
                                                        station_ID,
                                                        station_name,
                                                        location_name,
                                                        elevation,
                                                        latitude,
                                                        longitude)

                    # convert to metric system
                    converter = ConvertToSystem(UNIT_SYSTEM, full_log=_wunderground_full_log)
                    data_to_write = converter.clean_and_convert(data_rows)
                summary_rows += len(data_to_write)

                wunderground_log(f'Saving {len(data_to_write)} rows')
                with file_lock:
                    writer.writerows(data_to_write)
            except Exception as e:
                summary_errors.append(str(e))
                wunderground_log(str(e))

    duration_seconds = time_module.perf_counter() - station_start_time
    wunderground_log(f"[{thread_name}] Finished thread for URL: {weather_station_url} ({duration_seconds:.1f}s)")
    return {
        'url': weather_station_url,
        'id_ejecucion': launchtime,
        'station_id': summary_station_id,
        'station_name': summary_station_name,
        'rows': summary_rows,
        'ok': summary_rows > 0,
        'errors': summary_errors,
        'api_errors': summary_api_errors,
        'duration_seconds': duration_seconds,
        'timestamp_lectura': station_started_at.isoformat(timespec='seconds'),
        'fecha_lectura': station_started_at.strftime('%Y%m%d'),
        'hora_lectura': station_started_at.strftime('%H:%M:%S'),
    }

def refresh_estacions_wunderground(wunderground_df:pd.DataFrame):
    csv = wunderground_df[['Codi Estació',
                            'Estació',
                            'Comarca',
                            'Municipi',
                            'Provincia',
                            'Altitud',
                            'Latitud',
                            'Longitud']].copy().drop_duplicates(subset=['Codi Estació'])

    try:
        # Try to read local DB of stations
        csv_old = pd.read_csv(_DATA_PATH+'estacions_wunderground.csv',decimal=',')
    except FileNotFoundError:
        # If not existing file a new df is created
        csv_old = pd.DataFrame(columns=csv.columns)

    #print(csv_old.info())
    csv_old.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    #
    csv.set_index(keys=["Codi Estació"],drop=False,inplace=True)

    # Utilizamos una expresión regular para encontrar el último par de paréntesis en Estació y lo eliminamos
    # Utilizamos apply y una función lambda para aplicar la operación a cada elemento de la columna
    #csv['Estació'] = csv['Estació'].apply(lambda x: re.sub(r'\([^)]*\)(?=[^()]*$)', '', x))

    # Get elevation for existing stations in 'estacions_wunderground.csv' if not set or changed lat or long
    existing_stations = csv[csv.index.isin(csv_old.index )].copy()

    for index, station in existing_stations.iterrows():
        try:
            _check_altitud = float(csv_old['Altitud'][index])
            if math.isnan(_check_altitud) or \
                csv_old.loc[index,'Municipi'] == 'Not set yet' or \
                csv_old.loc[index,'Provincia'] == 'Not set yet':
                _isvalid = False
            else:
                existing_stations.loc[index,'Altitud'] = csv_old.loc[index,'Altitud']
                existing_stations.loc[index,'Municipi'] = csv_old.loc[index,'Municipi']
                existing_stations.loc[index,'Provincia'] = csv_old.loc[index,'Provincia']
                _isvalid = True
        except ValueError:
            _isvalid = False

        if  station['Latitud'] != csv_old.loc[index,'Latitud'] or \
            station['Longitud'] != csv_old.loc[index,'Longitud'] or \
            not _isvalid:
            print ('Updating altitude/municipality/province for existing station:'+ station['Codi Estació'] + '-->' + station['Estació'])
            #print('Estacion a actualizar', existing_stations['Codi Estació'][index])
            _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
            #print(_altitud,_municipi,_provincia)
            #existing_stations['Altitud'][index] = int(get_googlemaps(station['Latitud'], station['Longitud'],'elevation'))
            existing_stations.loc[index,'Altitud'] = int(_altitud)
            existing_stations.loc[index,'Municipi'] = _municipi
            existing_stations.loc[index,'Provincia'] = _provincia

    # Get elevation, municipi & provincia for new stations added to 'estacions_meteoclimatic.csv'
    new_stations = csv[ ~csv.index.isin(csv_old.index) ].copy()
    for index, station in new_stations.iterrows():
        print ('Fetching altitude/municipality/province for new station:'+ station['Codi Estació'] + '-->' + station['Estació'])
        _altitud, _municipi, _provincia = get_googlemaps(station['Latitud'], station['Longitud'])
        #new_stations['Altitud'][index] = int(get_googlemaps(station['Latitud'], station['Longitud'],'elevation'))
        new_stations.loc[index,'Altitud'] = int(_altitud)
        new_stations.loc[index,'Municipi'] = _municipi
        new_stations.loc[index,'Provincia'] = _provincia

    csv_old.update(existing_stations)
    csv.update(existing_stations)
    csv.update(new_stations)
    #
    # Merge new records from csv & csv_old into csv_incremental
    csv_old.reset_index(drop=True,inplace=True)
    new_stations.reset_index(drop=True,inplace=True)
    csv_incremental = pd.merge(new_stations, csv_old.drop_duplicates(), on=csv_old.columns.to_list(),
                how='outer', indicator=False)
    csv_incremental.sort_values(by=['Codi Estació'], ascending=[True],inplace=True)

    csv_incremental.reset_index(drop=True, inplace=True)

    # Save local DB of Stations for Meteoclimatic - Each new station read is added to local DB
    csv_incremental.to_csv(_DATA_PATH+'estacions_wunderground.csv',decimal=',',index=False)
    return csv



def print_wunderground_progress(completed, total):
    print(f'Processing Wunderground stations {completed} from {total}')

def format_wunderground_duration(seconds):
    if seconds is None:
        return '-'
    return f'{seconds:.1f}s'

def format_wunderground_station(result):
    station = result.get('station_id') or result.get('url')
    station_name = result.get('station_name') or ''
    if station_name:
        return f'{station} ({station_name})'
    return station

def save_wunderground_metrics(results):
    if not results:
        return

    metrics_path = os.path.join(_DATA_PATH, 'metricas_wunderground.csv')
    os.makedirs(_DATA_PATH, exist_ok=True)
    fieldnames = [
        'id_ejecucion',
        'timestamp_lectura',
        'fecha_lectura',
        'hora_lectura',
        'codi_estacio',
        'estacion',
        'url',
        'tiempo_lectura_s',
        'ok',
        'filas',
        'ultimo_error',
    ]
    write_header = not os.path.exists(metrics_path) or os.path.getsize(metrics_path) == 0

    with open(metrics_path, 'a', newline='', encoding='utf-8') as metrics_file:
        writer = csv.DictWriter(metrics_file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        for result in results:
            errors = result.get('errors') or []
            duration_seconds = result.get('duration_seconds')
            writer.writerow({
                'timestamp_lectura': result.get('timestamp_lectura', ''),
                'id_ejecucion': result.get('id_ejecucion', ''),
                'fecha_lectura': result.get('fecha_lectura', ''),
                'hora_lectura': result.get('hora_lectura', ''),
                'codi_estacio': result.get('station_id', ''),
                'estacion': result.get('station_name', ''),
                'url': result.get('url', ''),
                'tiempo_lectura_s': f'{duration_seconds:.3f}' if isinstance(duration_seconds, (int, float)) else '',
                'ok': result.get('ok', False),
                'filas': result.get('rows', 0),
                'ultimo_error': errors[-1] if errors else '',
            })

def print_wunderground_summary(results):
    global WUNDERGROUND_API_FALLBACK_ERRORS
    updated = [result for result in results if result.get('ok')]
    failed = [result for result in results if not result.get('ok')]
    WUNDERGROUND_API_FALLBACK_ERRORS = sum(result.get("api_errors", 0) for result in results)
    timed_results = [
        result for result in results
        if isinstance(result.get('duration_seconds'), (int, float))
    ]

    print('')
    print('Wunderground summary:')
    print('--------------------')
    print(f'Requested stations: {len(results)}')
    print(f'Updated stations: {len(updated)}')
    print(f'Failed stations: {len(failed)}')
    print(f'API fallback errors: {WUNDERGROUND_API_FALLBACK_ERRORS}')

    if timed_results:
        sorted_by_duration = sorted(timed_results, key=lambda result: result['duration_seconds'])
        durations = [result['duration_seconds'] for result in sorted_by_duration]
        duration_count = len(durations)
        duration_middle = duration_count // 2
        if duration_count % 2:
            median_duration = durations[duration_middle]
        else:
            median_duration = (durations[duration_middle - 1] + durations[duration_middle]) / 2
        average_duration = sum(durations) / duration_count
        fastest = sorted_by_duration[0]
        slowest = sorted_by_duration[-1]

        print('')
        print('Wunderground timings:')
        print(f'Average time per station: {format_wunderground_duration(average_duration)}')
        print(f'Median time per station: {format_wunderground_duration(median_duration)}')
        print(f'Fastest station: {format_wunderground_station(fastest)} - {format_wunderground_duration(fastest["duration_seconds"])}')
        print(f'Slowest station: {format_wunderground_station(slowest)} - {format_wunderground_duration(slowest["duration_seconds"])}')
        print('Slowest stations:')
        for result in reversed(sorted_by_duration[-10:]):
            status = 'OK' if result.get('ok') else 'ERROR'
            rows = result.get('rows', 0)
            print(f'- {format_wunderground_station(result)} - {format_wunderground_duration(result["duration_seconds"])} - {status} - {rows} rows')

    if failed:
        print('')
        print('Failed Wunderground stations:')
        for result in failed:
            errors = result.get('errors') or ['No rows returned']
            last_error = errors[-1]
            print(f'- {format_wunderground_station(result)} - {last_error}')

    save_wunderground_metrics(results)
    print('')
    print(f'Wunderground metrics saved to {_DATA_PATH}metricas_wunderground.csv')

def build_wunderground_dataframe(scraper_df:pd.DataFrame):
    """Convert scraped Wunderground rows into Rainmapper's normalized schema.

    Monthly Wunderground tables already expose daily wind high/average/low
    speeds, but not a daily direction column. Direction is therefore populated
    only when a non-monthly scrape provides the `Wind` compass column.
    """
    new_columns = [
        'Codi Estació',
        'Data Lectura',
        'Estació',
        'Comarca',
        'Municipi',
        'Provincia',
        'Altitud',
        'Latitud',
        'Longitud',
        'Ultima Lectura',
        'Variable',
        'Total',
        'Unitat',
        'max_temp_celsius',
        'min_temp_celsius',
        'max_humidity_percent',
        'min_humidity_percent',
        *WIND_COLUMNS,
        'Data Local',
        'Hora Local'
                    ]
    wunderground_df = pd.DataFrame(columns=new_columns)
    # Llenar nuevo dataframe con valores de scrapper
    wunderground_df['Codi Estació'] = scraper_df['Codi Estació']
    wunderground_df['Data Lectura'] = scraper_df['Data'] + ' '+ scraper_df['Hora']
    wunderground_df['Estació'] = scraper_df['Estació']
    wunderground_df['Comarca'] = scraper_df['Comarca']
    wunderground_df['Municipi'] = scraper_df['Municipi']
    wunderground_df['Provincia'] = scraper_df['Provincia']
    wunderground_df['Codi Estació'] = scraper_df['Codi Estació']
    wunderground_df['Altitud'] = scraper_df['Altitud']
    wunderground_df['Latitud'] = scraper_df['Latitud']
    wunderground_df['Longitud'] = scraper_df['Longitud']
    wunderground_df['Ultima Lectura'] = scraper_df['Data']
    wunderground_df['Variable'] = 'Precipitació'
    wunderground_df['Total'] = scraper_df['Rain_mm']
    wunderground_df['Unitat'] = 'mm'
    wunderground_df['max_temp_celsius'] = scraper_df['TempHigh_C']
    wunderground_df['min_temp_celsius'] = scraper_df['TempLow_C']
    wunderground_df['max_humidity_percent'] = scraper_df['HumHigh_%']
    wunderground_df['min_humidity_percent'] = scraper_df['HumLow_%']
    wunderground_df['wind_avg_kmh'] = scraper_df['SpeedAv_kmh'].apply(optional_round) if 'SpeedAv_kmh' in scraper_df else pd.NA
    wunderground_df['wind_min_kmh'] = scraper_df['SpeedLow_kmh'].apply(optional_round) if 'SpeedLow_kmh' in scraper_df else pd.NA
    wunderground_df['wind_max_kmh'] = scraper_df['SpeedHigh_kmh'].apply(optional_round) if 'SpeedHigh_kmh' in scraper_df else pd.NA
    wunderground_df['wind_gust_kmh'] = scraper_df['Gust_kmh'].apply(optional_round) if 'Gust_kmh' in scraper_df else pd.NA
    wunderground_df['wind_direction_deg'] = scraper_df['Wind'].apply(compass_to_degrees) if 'Wind' in scraper_df else pd.NA
    wunderground_df['wind_observation_count'] = wunderground_df['wind_avg_kmh'].notna().astype(int)
    wunderground_df['Data Local'] = scraper_df['Data']
    wunderground_df['Hora Local'] = scraper_df['Hora']
    return wunderground_df

def create_wunderground(timings=None):
    launchtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    '''for url in URLS:
        url = url.strip()
        #print(url)
        # INSERTAR THREADS AQUI
        # VER COMO ABRIR 5 THREADS MAXIMO (PONER EN UNA VARIABLE EL NRO DE THREADS?)
        scrap_wunderground_station(url, launchtime)'''
    # Define el número de threads que deseas
    max_threads = _max_threads
    results = []
    station_urls = [url.strip() for url in URLS if url.strip() and not url.strip().startswith('#')]
    filtered_station_ids = backfill_station_ids_for("wunderground")
    if filtered_station_ids:
        station_urls_by_id = {
            station_id_from_url(url).upper(): url
            for url in station_urls
        }
        unknown_station_ids = sorted(filtered_station_ids - set(station_urls_by_id))
        station_urls = [
            url
            for url in station_urls
            if station_id_from_url(url).upper() in filtered_station_ids
        ]
        print(
            "Wunderground station filter enabled: "
            f"{len(station_urls)} selected from {len(station_urls_by_id)} configured station(s)."
        )
        if unknown_station_ids:
            print(
                "Wunderground station filter unknown station(s): "
                + ", ".join(unknown_station_ids)
            )
        if not station_urls:
            raise ValueError("Wunderground station filter did not match any configured station.")
    total_stations = len(station_urls)
    completed_stations = 0
    progress_step = max(1, math.ceil(total_stations / 10))
    next_progress = progress_step

    print(f'Processing Wunderground stations 0 from {total_stations}')

    def register_wunderground_result(result):
        nonlocal completed_stations, next_progress
        results.append(result)
        completed_stations += 1
        if completed_stations >= next_progress or completed_stations == total_stations:
            print_wunderground_progress(completed_stations, total_stations)
            while next_progress <= completed_stations:
                next_progress += progress_step

    # Usa ThreadPoolExecutor para gestionar los threads
    step_start_time = time_module.perf_counter()
    with ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="UrlScrapping") as executor:
        futures = []
        # Crea una lista de tareas usando executor.submit()
        for index, url in enumerate(station_urls):
            if index == 0:
                # Procesa la primera URL sin threads
                wunderground_log(f"Processing first URL without threads: {url}")
                register_wunderground_result(scrap_wunderground_station(url, launchtime))
            else:
                # Procesa el resto de las URLs usando threads
                futures.append(executor.submit(scrap_wunderground_station, url, launchtime))

        # Procesa los resultados a medida que terminan
        for future in as_completed(futures):
            register_wunderground_result(future.result())
    record_timing(timings, 'scrape_seconds', step_start_time)

    step_start_time = time_module.perf_counter()
    print_wunderground_summary(results)
    record_timing(timings, 'metrics_seconds', step_start_time)



    # Convert to Rainmapper format

    # Move to dataframe and remove temporary created csv file = wunderground_file_name
    step_start_time = time_module.perf_counter()
    scraper_df = pd.read_csv(wunderground_file_name , decimal=',')
    os.remove(wunderground_file_name)
    record_timing(timings, 'read_scrape_csv_seconds', step_start_time)

    #print(scraper_df)
    step_start_time = time_module.perf_counter()
    wunderground_df = build_wunderground_dataframe(scraper_df)

    wunderground_df['Data Lectura'] = pd.to_datetime(wunderground_df['Data Lectura'],format='%Y-%m-%d %H:%M:%S') # 'Data Lectura' como datetime64
    wunderground_df['Ultima Lectura']= wunderground_df['Data Lectura'].dt.strftime("%Y/%m/%d %H:%M:%S")
    wunderground_df['Data Local'] = wunderground_df['Data Lectura'].dt.strftime("%Y%m%d") # Set Date as only date from 'Ultima Lectura'
    wunderground_df['Hora Local'] = wunderground_df['Data Lectura'].dt.strftime("%H:%M:%S")  # Set Time as only time from 'Ultima Lectura'

    wunderground_df['Total'] = wunderground_df['Total'].astype(float)     # Convierte la columna 'Total' a tipo float
    wunderground_df['Altitud'] = wunderground_df['Altitud'].astype(str)  # Convierte la columna 'Altitud' a tipo str
    wunderground_df['Latitud'] = wunderground_df['Latitud'].astype(str)  # Convierte la columna 'Latitud' a tipo str
    wunderground_df['Longitud'] = wunderground_df['Longitud'].astype(str)  # Convierte la columna 'Longitud' a tipo str
    wunderground_df['Data Local'] = wunderground_df['Data Local'].astype(str)  # Convierte la columna 'Data Local' a tipo str
    record_timing(timings, 'normalize_seconds', step_start_time)

    # Refresh local stations DB  (to not search for elevation in googlemaps all times)
    step_start_time = time_module.perf_counter()
    refreshed_stations_df = refresh_estacions_wunderground(wunderground_df)
    record_timing(timings, 'station_catalog_seconds', step_start_time)

    # Refresh Update Altitud/Provincia/Població on wunderground_df from local DB stations
    step_start_time = time_module.perf_counter()
    refreshed_stations_df.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    wunderground_df.set_index(keys=["Codi Estació"],drop=False,inplace=True)
    wunderground_df.update(refreshed_stations_df)

    wunderground_df.reset_index(drop=True,inplace=True)
    wunderground_df.sort_values(by=['Codi Estació', 'Data Lectura'], ascending=[True, False],inplace=True)
    record_timing(timings, 'station_update_seconds', step_start_time)


    #print(wunderground_df)

    # Save wunderground_df to csv
    step_start_time = time_module.perf_counter()
    wunderground_df.to_csv(_DATA_PATH+'Wunderground'+'.csv', decimal='.', index=False)
    record_timing(timings, 'write_current_seconds', step_start_time)
    return wunderground_df


def merge_dataframes(source01_df_param:pd.DataFrame, source02_df_param:pd.DataFrame, printit=False):
    ### Merge data from source01 & source02
    source01_df=source01_df_param.copy()
    if source01_df.empty:
        source01_df = read_incremental('Meteocat_incremental',_nrows=0)
    source02_df=source02_df_param.copy()
    if source02_df.empty:
        source02_df = read_incremental('Meteocat_incremental',_nrows=0)
    source01_df.reset_index(drop=True,inplace=True)
    source02_df.reset_index(drop=True,inplace=True)

    csv_completo = pd.merge(source01_df, source02_df.drop_duplicates(), on=source01_df.columns.to_list(),
					how='outer', indicator=False)

    csv_completo.sort_values(by=['Total','Codi Estació'], ascending=[False,True],inplace=True)
    csv_completo.reset_index(drop=True, inplace=True)
    if printit:
        if len(source02_df) != 0:
            print('------------------------------------------')
            print('Data merged from source01 & source02:')
            print('------------------------------------------')

        else:
            print('-------------------------------------------------')
            print('Data merged from source01 & source02(EMPTY):')
            print('-------------------------------------------------')

        print_dataframes(csv_completo)
    return csv_completo

def create_filtered(df_to_filter_param:pd.DataFrame, _base_date, _days_backward, _days_forward):
    # Identify the current thread and log the start message.
    thread_name = threading.current_thread().name
    print(f"[{thread_name}] Starting thread for dataframe filtering")

    df_to_filter = df_to_filter_param.copy()
    start_date = _base_date - timedelta(days=_days_backward)
    end_date = _base_date + timedelta(days=_days_forward)

    if not pd.api.types.is_datetime64_any_dtype(df_to_filter['Data Local']):
        df_to_filter['Data Local'] = pd.to_datetime(df_to_filter['Data Local'], format='%Y%m%d', errors='coerce')

    date_mask = (df_to_filter['Data Local'] >= start_date) & (df_to_filter['Data Local'] <= end_date)
    return df_to_filter.loc[date_mask].copy()

#In[10] ##  MAIN LOOP ##
#
# DEFINE BASE DATES FROM 00:00:00 TO 23:59:59 IN TODAY'S DATE
_data_inici_base = datetime.combine(date.today(), time())                               # Today at 00:00:00
_data_fi_base = datetime.combine(date.today(), time()) - timedelta(days=-1,seconds=1)   # Today at 23:59:59
#
_current_path = os.getcwd()
print('Current path',_current_path)
#
# GET START AND END DATES FOR QUERY
_start_date = get_query_date(_data_inici_base, _days_init)       # Start date for data selection
_end_date = get_query_date(_data_fi_base, _days_end)             # End date for data selection

## PRINT SET PARAMETERS TO TERMINAL
print('')
print("Set parameters")
print("--------------")
print('Start date:', utc_to_local(datetime.strptime(_start_date,'%Y-%m-%dT%H:%M:%S')).strftime('%d/%m/%Y %H:%M:%S'),' in local time')
print('End   date:',  utc_to_local(datetime.strptime(_end_date,'%Y-%m-%dT%H:%M:%S')).strftime('%d/%m/%Y %H:%M:%S'),' in local time')
print('')
print("Print totals:",_print_totals)
print("Print DataFrames:",_print_dataframes)
print("Create daily stats:",_create_daily_stats)
print("Create weekly stats:",_create_weekly_stats)
print("Create monthly stats:",_create_monthly_stats)
print('')
print("Create Meteocat:",_create_meteocat)
print("Save incremental Meteocat:",_incremental_meteocat)
print('')
print("Create Meteoclimatic:",_create_meteoclimatic)
print("Save incremental Meteoclimatic:",_incremental_meteoclimatic)
print('')
print("Create Wunderground:",_create_wunderground)
print("Save incremental Wunderground:",_incremental_wunderground)
print('')
print("Create AEMET:",_create_aemet)
print('')

def process_meteoclimatic():                                        # FOR MULTITHREAD PURPOSES
    #################################
    ## Process Meteoclimatic data ##
    #################################
    source_started_at = datetime.now().isoformat(timespec='seconds')
    source_start_time = time_module.perf_counter()
    source_timings = {}
    try:
        if _create_meteoclimatic:
            start_count(_legend='Start processing Meteoclimatic...')

            # Identify the current thread and log the start message.
            thread_name = threading.current_thread().name
            print(f"[{thread_name}] Starting thread for Meteoclimatic")

            meteoclimatic_df = create_meteoclimatic(_save_to_csv=True, timings=source_timings)

            if _incremental_meteoclimatic:
                meteoclimatic_incremental = save_incremental_meteoclimatic(meteoclimatic_df, _save_to_excel=False, timings=source_timings) 	# Saves incremental data to csv. Also to excel depending on param
            else:
                step_start_time = time_module.perf_counter()
                meteoclimatic_incremental = read_incremental('Meteoclimatic_incremental')
                record_timing(source_timings, 'read_incremental_seconds', step_start_time)

            # Filter results according to settings in parameters
            #meteoclimatic_df = filter_results(meteoclimatic_df,_minima_lectura_meteoclimatic)
            #print('Meteoclimatic.dtypes')

            # print(meteoclimatic_df.dtypes)
            step_start_time = time_module.perf_counter()
            save_dataframe(meteoclimatic_df, 'Meteoclimatic', _save_to_csv=True, _save_to_excel=False,_decimal=',')
            record_timing(source_timings, 'write_current_seconds', step_start_time)
            print_source_timings('Meteoclimatic', source_timings)
            if _print_dataframes:
                print('------------------------')
                print('Data from Meteoclimatic:')
                print('------------------------')
                print_dataframes(meteoclimatic_df)

            end_count(_legend='Finished processing Meteoclimatic')
        else:
            meteoclimatic_incremental = read_incremental('Meteoclimatic_incremental')
            meteoclimatic_df = read_incremental('Meteoclimatic_incremental',_nrows=0)

            #meteoclimatic_df = pd.read_csv(_DATA_PATH +'Meteoclimatic_incremental.csv',decimal=',',nrows=0)
            #meteoclimatic_df['Data Lectura'] = pd.to_datetime(meteoclimatic_df['Ultima Lectura'])

        return meteoclimatic_df, meteoclimatic_incremental
    finally:
        record_source_runtime_metric(
            'Meteoclimatic',
            time_module.perf_counter() - source_start_time,
            started_at=source_started_at,
            finished_at=datetime.now().isoformat(timespec='seconds'),
            timings=source_timings,
        )

###############################################
# Configuracion previa a process_wunderground #                     # FOR MULTITHREAD PURPOSES
###############################################
from rainmapper_core.config import config_wunderground
import csv
import lxml.html as lh
from rainmapper_core.sources.wunderground.UnitConverter import ConvertToSystem
from rainmapper_core.sources.wunderground.Parser import Parser
from rainmapper_core.sources.wunderground.Utils import Utils
from rainmapper_core.sources.wunderground.daily_api import (
    WundergroundDailyApiError,
    build_monthly_rows,
    fetch_daily_observations,
    station_id_from_url,
)
#inicio modi
from rainmapper_core.sources.wunderground.parseStationData import parseStationData

# configuration
_stations_file = os.path.join(_script_path, 'stations.txt')
#stations_file = open('stations.txt', 'r')

# Sort stations file an save it again
# Paso 1: Abrir el archivo y leer su contenido
with open(_stations_file, 'r') as stations_file:
    lines = stations_file.readlines()  # Leer todas las líneas del archivo

# Paso 2: Filtrar las líneas en blanco y quitar espacios al inicio y al final
lines = [line.strip() for line in lines if line.strip()]  # Eliminar líneas en blanco

# Paso 3: Ordenar las líneas alfabéticamente
lines.sort()

# Paso 4: Abrir el archivo en modo de escritura y guardar el contenido ordenado
with open(_stations_file, 'w') as stations_file:
    stations_file.writelines(f"{line}\n" for line in lines)  # Escribir las líneas ordenadas

stations_file = open(_stations_file, 'r')

URLS = stations_file.readlines()
# Date format: YYYY-MM-DD
#START_DATE = config_wunderground.START_DATE
#END_DATE = config_wunderground.END_DATE
# Normal updates keep the legacy days_init/days_end UTC conversion. In monthly
# Wunderground mode that deliberately rereads the previous month when a normal
# short range crosses a month boundary, so late-arriving month totals are fixed.
#
# Administrative monthly backfills are different: each window is a local
# calendar month and must not shift to the previous UTC day in Europe/Madrid.
# When the wrapper passes explicit local dates, use them only for Wunderground
# URL/API month selection and leave the rest of the run behavior unchanged.
if _wunderground_local_start_date and _wunderground_local_end_date:
    START_DATE = datetime.strptime(_wunderground_local_start_date, '%Y-%m-%d').date()
    END_DATE = datetime.strptime(_wunderground_local_end_date, '%Y-%m-%d').date()
else:
    START_DATE = datetime.strptime(_start_date,'%Y-%m-%dT%H:%M:%S').date()
    END_DATE = datetime.strptime(_end_date,'%Y-%m-%dT%H:%M:%S').date()
#print(START_DATE, END_DATE)

MONTHLY = config_wunderground.MONTHLY
MERGE_DATA = config_wunderground.MERGE_DATA

# set to "metric" or "imperial"
UNIT_SYSTEM = config_wunderground.UNIT_SYSTEM
# find the first data entry automatically
FIND_FIRST_DATE = config_wunderground.FIND_FIRST_DATE

def load_wunderground_station_metadata_cache():
    global WUNDERGROUND_STATION_METADATA_CACHE
    if WUNDERGROUND_STATION_METADATA_CACHE is not None:
        return WUNDERGROUND_STATION_METADATA_CACHE

    with WUNDERGROUND_STATION_METADATA_LOCK:
        if WUNDERGROUND_STATION_METADATA_CACHE is not None:
            return WUNDERGROUND_STATION_METADATA_CACHE

        cache = {}
        metadata_path = os.path.join(_DATA_PATH, 'estacions_wunderground.csv')
        try:
            with open(metadata_path, newline='', encoding='utf-8-sig') as metadata_file:
                for row in csv.DictReader(metadata_file):
                    station_id = str(row.get('Codi Estació') or '').strip().upper()
                    if not station_id:
                        continue
                    metadata = {
                        'station_ID': station_id,
                        'station_name': str(row.get('Estació') or '').strip(),
                        'location_name': str(row.get('Municipi') or '').strip(),
                        'elevation': str(row.get('Altitud') or '').strip(),
                        'latitude': str(row.get('Latitud') or '').strip(),
                        'longitude': str(row.get('Longitud') or '').strip(),
                    }
                    if all(metadata.values()):
                        cache[station_id] = metadata
        except FileNotFoundError:
            cache = {}

        WUNDERGROUND_STATION_METADATA_CACHE = cache
        return WUNDERGROUND_STATION_METADATA_CACHE


def cached_wunderground_station_metadata(weather_station_url):
    station_id = station_id_from_url(weather_station_url)
    return load_wunderground_station_metadata_cache().get(station_id)


def month_api_range(month_date):
    start_date = month_date.replace(day=1)
    if start_date < START_DATE:
        start_date = START_DATE
    end_date = min(month_date, END_DATE)
    return start_date, end_date


def fetch_wunderground_api_rows(
    weather_station_url,
    date_string,
    station_ID,
    station_name,
    location_name,
    elevation,
    latitude,
    longitude,
    session,
    timeout,
):
    if not MONTHLY:
        raise WundergroundDailyApiError("daily API fallback is only implemented for monthly mode")

    month_date = datetime.strptime(date_string, "%Y-%m-%d").date()
    api_start, api_end = month_api_range(month_date)
    observations = fetch_daily_observations(
        station_id_from_url(weather_station_url),
        api_start,
        api_end,
        session=session,
        timeout=timeout,
    )
    return build_monthly_rows(
        observations,
        station_ID,
        station_name,
        location_name,
        elevation,
        latitude,
        longitude,
    )

def process_wunderground():                                         # FOR MULTITHREAD PURPOSES
    ###############################
    ## Process Wunderground data ##
    ###############################
    source_started_at = datetime.now().isoformat(timespec='seconds')
    source_start_time = time_module.perf_counter()
    source_timings = {}
    try:
        if _create_wunderground:
            start_count(_legend='Start processing Wunderground...')
            # run processing
            global wunderground_header
            wunderground_header = True
            wunderground_df = create_wunderground(timings=source_timings)
            if _incremental_wunderground:
                wunderground_incremental = save_incremental_wunderground(wunderground_df, _save_to_excel=False, timings=source_timings) 	# Saves incremental data to csv. Also to excel depending on param
            else:
                step_start_time = time_module.perf_counter()
                wunderground_incremental = read_incremental('Wunderground_incremental')
                record_timing(source_timings, 'read_incremental_seconds', step_start_time)
            print_source_timings('Wunderground', source_timings)
            end_count(_legend='Finished processing Wunderground')
        else:
            wunderground_incremental = read_incremental('Wunderground_incremental')
            wunderground_df = read_incremental('Wunderground_incremental',_nrows=0)

        return wunderground_df,wunderground_incremental
    finally:
        record_source_runtime_metric(
            'Wunderground',
            time_module.perf_counter() - source_start_time,
            started_at=source_started_at,
            finished_at=datetime.now().isoformat(timespec='seconds'),
            timings=source_timings,
        )

def process_aemet():                                                # FOR MULTITHREAD PURPOSES
    """Run the optional AEMET source and return its daily incremental data.

    AEMET owns its own updater because it stores hourly observations first and
    derives the daily incremental CSV from that history. The main runner only
    decides whether the source is enabled, records status metrics and returns an
    empty dataframe shape when AEMET is disabled.
    """
    from rainmapper_core import create_aemet as aemet_source

    source_started_at = datetime.now().isoformat(timespec='seconds')
    source_start_time = time_module.perf_counter()
    source_timings = {}
    try:
        if _create_aemet:
            start_count(_legend='Start processing AEMET...')
            aemet_api_key = os.environ.get('RAINMAPPER_AEMET_API_KEY') or os.environ.get('AEMET_API_KEY')
            # create_aemet.run_update writes all AEMET artifacts atomically for
            # this run: current hourly, hourly history, station catalog and daily
            # incremental rows consumed by Tomap.
            summary = aemet_source.run_update(
                data_dir=_DATA_PATH,
                api_key=aemet_api_key,
                local_timezone=os.environ.get('RAINMAPPER_TIMEZONE', 'Europe/Madrid'),
                enrich_stations=True,
                gmap_api_key=_GMAPS_KEY,
            )
            if isinstance(summary.get('timings'), dict):
                source_timings = summary['timings']
                timing_parts = [
                    f"{key}={value:.1f}s"
                    for key, value in source_timings.items()
                    if isinstance(value, (int, float))
                ]
                if timing_parts:
                    print("AEMET timings: " + ", ".join(timing_parts))
            print(
                "AEMET update finished: "
                f"{summary['current_hourly_rows']} current hourly row(s), "
                f"{summary['hourly_incremental_rows']} hourly incremental row(s), "
                f"{summary['daily_incremental_rows']} daily row(s), "
                f"{summary['stations']} station(s)."
            )
            aemet_incremental = read_incremental('Aemet_incremental')
            aemet_df = read_incremental('Aemet_incremental', _nrows=0)
            aemet_source.record_rate_limit_result(_DATA_PATH, rate_limited=False)
            end_count(_legend='Finished processing AEMET')
        else:
            aemet_incremental = read_incremental('Aemet_incremental')
            aemet_df = read_incremental('Aemet_incremental', _nrows=0)

        return aemet_df, aemet_incremental
    except aemet_source.AemetRateLimitError:
        aemet_source.record_rate_limit_result(_DATA_PATH, rate_limited=True)
        raise
    except Exception:
        if _create_aemet:
            aemet_source.record_rate_limit_result(_DATA_PATH, rate_limited=False)
        raise
    finally:
        record_source_runtime_metric(
            'AEMET',
            time_module.perf_counter() - source_start_time,
            started_at=source_started_at,
            finished_at=datetime.now().isoformat(timespec='seconds'),
            timings=source_timings,
        )

###########################################
# Configuracion previa a process_meteocat #                         # FOR MULTITHREAD PURPOSES
###########################################

# Unauthenticated client only works with public data sets. Note 'None'
# in place of application token, and no username or password:
socrata_domain = "analisi.transparenciacatalunya.cat"
socrata_lectures_xema = "nzvn-apee"
socrata_daily_xema = "7bvh-jvq2"
socrata_metadades_lectures_xema =  "4fb2-n3yi"
socrata_metadades_estacions_xema = "yqwd-vj5e"
socrata_metadades_variables_xema = "4fb2-n3yi"
# If you choose to use a token, run the following command on the terminal (or add it to your .bashrc)
# $ export SODAPY_APPTOKEN=<token>
#socrata_token = os.environ.get("SODAPY_APPTOKEN")
socrata_token = None

client = Socrata(socrata_domain, socrata_token, timeout=_meteocat_request_timeout)

def socrata_get(dataset_identifier, description, **kwargs):
    for attempt in range(1, _meteocat_max_attempts + 1):
        try:
            return client.get(dataset_identifier, **kwargs)
        except requests.exceptions.RequestException as exc:
            if attempt >= _meteocat_max_attempts:
                print(
                    f"Meteocat Socrata {description} failed after "
                    f"{_meteocat_max_attempts} attempt(s): {exc}"
                )
                raise
            wait_seconds = min(5 * attempt, 30)
            print(
                f"Meteocat Socrata {description} attempt {attempt}/"
                f"{_meteocat_max_attempts} failed: {exc}. "
                f"Retrying in {wait_seconds}s..."
            )
            time_module.sleep(wait_seconds)

# Example authenticated client (needed for non-public datasets):
# client = Socrata(analisi.transparenciacatalunya.cat,
#                  MyAppToken,
#                  username="user@example.com",
#                  password="AFakePassword")

def process_meteocat():                                             # FOR MULTITHREAD PURPOSES
    ###########################
    ## Process Meteocat data ##
    ###########################
    source_started_at = datetime.now().isoformat(timespec='seconds')
    source_start_time = time_module.perf_counter()
    source_timings = {}
    try:
        if _create_meteocat:
            start_count(_legend='Start processing Meteocat...')

            # Identify the current thread and log the start message.
            thread_name = threading.current_thread().name
            print(f"[{thread_name}] Starting thread for Meteocat")

            # DEFINE base data for Meteocat connection##
            #

            # Get Metadata for Stations and Variables - Only 1 reading per launch
            step_start_time = time_module.perf_counter()
            estacions_xema = get_estacions_xema()   # Get info data from estacions at Meteocat
            variables_xema = get_variables_xema()   # Get info data from variables at Meteocat
            source_timings['metadata_seconds'] = time_module.perf_counter() - step_start_time
            end_count(_legend='Processed Meteocat estacions&variables reading from Socrata')

            if _create_meteocat_conditions:
                step_start_time = time_module.perf_counter()
                meteocat_conditions_xema=get_results_conditions_xema(pd.DataFrame, estacions_xema, variables_xema)
                # Save current readings from meteocat_conditions_xema to csv
                #save_dataframe(meteocat_conditions_xema, 'Meteocat_conditions_xema.csv',_save_to_csv=True, _save_to_excel=False, _decimal='.')
                if meteocat_conditions_xema.empty:
                    meteocat_conditions_xema = read_incremental('Meteocat_incremental',_nrows=0)
                source_timings['conditions_seconds'] = time_module.perf_counter() - step_start_time
                end_count(_legend='Processed Meteocat reading conditions temperature.max/min -  humidity.max&min from Socrata')

                step_start_time = time_module.perf_counter()
                # Daily wind variables are published in a separate XEMA daily
                # dataset, not in the regular readings dataset used above.
                meteocat_wind_xema = get_results_daily_wind_xema(estacions_xema)
                if not meteocat_wind_xema.empty:
                    meteocat_conditions_xema = pd.merge(
                        meteocat_conditions_xema,
                        meteocat_wind_xema.drop_duplicates(),
                        on=('Codi Estació','Estació','Data Lectura','Comarca','Municipi','Provincia'),
                        how='left',
                        indicator=False,
                    )
                source_timings['wind_seconds'] = time_module.perf_counter() - step_start_time
                end_count(_legend='Processed Meteocat daily wind from Socrata')

            step_start_time = time_module.perf_counter()
            meteocat_rain_xema = get_results_rain_xema(pd.DataFrame, estacions_xema, variables_xema)
            if meteocat_rain_xema.empty:
                    meteocat_rain_xema = read_incremental('Meteocat_incremental',_nrows=0)
            source_timings['precipitation_seconds'] = time_module.perf_counter() - step_start_time

            step_start_time = time_module.perf_counter()
            meteocat_df = pd.merge(meteocat_rain_xema, meteocat_conditions_xema.drop_duplicates(),
                                    on=('Codi Estació','Estació','Data Lectura','Comarca','Municipi','Provincia'),
                            how='left', indicator=False)
            #save_dataframe(meteocat_merge, 'Meteocat_merged_xema.csv',_save_to_csv=True, _save_to_excel=False, _decimal='.')
            #meteocat_df = meteocat_merge
            source_timings['merge_seconds'] = time_module.perf_counter() - step_start_time
            end_count(_legend='Processed Meteocat reading precipitation from Socrata')
            # If no records returned, initialize empty meteocat's dataframes with columns from incremental
            if meteocat_df.empty:
                step_start_time = time_module.perf_counter()
                meteocat_incremental = read_incremental('Meteocat_incremental')
                meteocat_df = read_incremental('Meteocat_incremental',_nrows=0)
                record_timing(source_timings, 'read_incremental_seconds', step_start_time)

            if _incremental_meteocat:
                #print('Meteocat creado:',meteocat_df.info())
                meteocat_incremental = save_incremental_meteocat(meteocat_df, _save_to_excel=False, timings=source_timings) 			 # Saves incremental data to csv. Also to excel depending on param
                #print('Meteocat incremental:',meteocat_incremental.info())
            else:
                step_start_time = time_module.perf_counter()
                meteocat_incremental = read_incremental('Meteocat_incremental')
                record_timing(source_timings, 'read_incremental_seconds', step_start_time)
            # Filter results according to settings in parameters
            #meteocat_df = filter_results(meteocat_df, _minima_lectura_meteocat)
            # Save current readings from meteocat to csv
            step_start_time = time_module.perf_counter()
            save_dataframe(meteocat_df, 'Meteocat', _save_to_csv=True, _save_to_excel=False,_decimal=',')
            record_timing(source_timings, 'write_current_seconds', step_start_time)
            print_source_timings('Meteocat', source_timings)

            if _print_dataframes:
                print('-------------------')
                print('Data from Meteocat:')
                print('-------------------')
                print_dataframes(meteocat_df)

            end_count(_legend='Finished processing Meteocat')
        else:
            meteocat_incremental = read_incremental('Meteocat_incremental')
            meteocat_df = read_incremental('Meteocat_incremental',_nrows=0)

        return meteocat_df, meteocat_incremental
    finally:
        record_source_runtime_metric(
            'Meteocat',
            time_module.perf_counter() - source_start_time,
            started_at=source_started_at,
            finished_at=datetime.now().isoformat(timespec='seconds'),
            timings=source_timings,
        )

#############################################################################
# Usa ThreadPoolExecutor para iniciar los threads de los distintos procesos #
#############################################################################
initialize_source_statuses()

with ThreadPoolExecutor(max_workers=_max_threads, thread_name_prefix="MainProcesses") as executor:
        # Crea las tareas en paralelo y mapea los resultados a variables

        future_aemet = executor.submit(process_aemet)
        future_meteoclimatic = executor.submit(process_meteoclimatic)
        future_meteocat = executor.submit(process_meteocat)
        future_wunderground = executor.submit(process_wunderground)

        # Obtén los resultados
        aemet_df, aemet_incremental = collect_source_result(
            'AEMET',
            future_aemet,
            'Aemet_incremental',
            _create_aemet,
        )
        meteoclimatic_df, meteoclimatic_incremental = collect_source_result(
            'Meteoclimatic',
            future_meteoclimatic,
            'Meteoclimatic_incremental',
            _create_meteoclimatic,
        )
        meteocat_df, meteocat_incremental = collect_source_result(
            'Meteocat',
            future_meteocat,
            'Meteocat_incremental',
            _create_meteocat,
        )
        wunderground_df, wunderground_incremental = collect_source_result(
            'Wunderground',
            future_wunderground,
            'Wunderground_incremental',
            _create_wunderground,
        )


###########################
## Process Print routine ##
###########################

if _print_totals:                                              # Create totals per station sorted by precipitacion DESC
    # Defines base date
    start_count(_legend='Start printing routine')
    _base_date = _data_inici_base
    _days_backward = _days_init * -1
    _days_forward = _days_end

    # Para rutina de impresion filtrar por fechas, y eliminar llluvias < 0.4 (son errores el 95% de los casos)

    meteoclimatic_df= create_filtered(meteoclimatic_incremental,_base_date, _days_backward, _days_forward)
    meteocat_df = create_filtered(meteocat_incremental,_base_date, _days_backward, _days_forward)
    wunderground_df= create_filtered(wunderground_incremental,_base_date, _days_backward, _days_forward)
    aemet_df = create_filtered(aemet_incremental,_base_date, _days_backward, _days_forward)

    meteoclimatic_df=filter_results(meteoclimatic_df,_minima_pluja=0.4)
    meteocat_df=filter_results(meteocat_df,_minima_pluja=0.4)
    wunderground_df=filter_results(wunderground_df,_minima_pluja=0.4)
    aemet_df=filter_results(aemet_df,_minima_pluja=0.4)

    # Merge de meteocat y meteoclimatic
    df_toprint = merge_dataframes(meteocat_df, meteoclimatic_df, _print_dataframes)
    # Añadir al merge wunderground
    df_toprint = merge_dataframes(df_toprint, wunderground_df, _print_dataframes)
    # Add AEMET if available
    df_toprint = merge_dataframes(df_toprint, aemet_df, _print_dataframes)

    csv_total= create_total_dataframe(df_toprint, _save_to_csv=False, _save_to_excel=False)
    csv_total = filter_results(csv_total,_minima_pluja=_minimum_rain_toprint)
    print_totals_per_station(csv_total)
    end_count(_legend='End printing routine')


if _create_daily_stats:                                                  # Create daily summary and save to csv
    create_daily_dataframe(meteocat_df, _save_to_excel=False)

if _create_weekly_stats:                                                 # Create weekly summary and save to csv
    create_weekly_dataframe(meteocat_df, _save_to_excel=False)

if _create_monthly_stats:                                                # Create monthly summary and save to csv
    create_monthly_dataframe(meteocat_df, _save_to_excel=False)
#

## Tomap generation is handled by rainmapper_core.tomap so maps can be rebuilt
## independently from weather-data downloads.
##
## Operational flow:
## - python -m rainmapper_core.rainmapper updates source data and source_status.json.
## - python -m rainmapper_core.tomap rebuilds Tomap/*.csv and LastXX_rains.csv.
## - python -m rainmapper_core.bokeh_maps and python -m rainmapper_core.geojson generate publishable maps.
if _create_googlemaps_files:
    print('')
    print('Inline Tomap generation is disabled; Tomap rebuild is handled by rainmapper_core.tomap.')

print('')
try:
    from pathlib import Path as _Path
    from rainmapper_core import mushroom_observation_context as _moc
    _parquet_path = _moc.generate_weather_daily_parquet(_Path(_DATA_PATH))
    if _parquet_path:
        print(f'weather_daily.parquet generated: {_parquet_path}')
except Exception as _parquet_exc:
    print(f'Warning: could not generate weather_daily.parquet: {_parquet_exc}')

exit_code = source_exit_code()
if exit_code == 2:
    print('Rainmapper finished with degraded source status.')
elif exit_code == 1:
    print('Rainmapper finished with no usable enabled source.')
sys.exit(exit_code)
