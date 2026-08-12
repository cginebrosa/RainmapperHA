"""Rebuild Rainmapper Tomap CSV files from incremental history.

This module is the canonical Tomap entrypoint. Run it with
`python -m rainmapper_core.tomap`. The functions keep the legacy Tomap output
format while making the implementation reusable from tests, Docker local and
the HA app package.
"""

import argparse
import math
import time as time_module
import warnings
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from rainmapper_core.config import const as rainmapper_const
from rainmapper_core.wind import WIND_COLUMNS, circular_mean_degrees


INCREMENTAL_COLUMNS = [
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
    *WIND_COLUMNS,
]

DAILY_RAIN_SANITY_LIMIT_MM = 300.0  # matches mushroom_observation_context value

TOMAP_PERIODS = [
    (90, '07_Tomap_Last_three_months', '90 days'),
    (60, '06_Tomap_Last_two_months', '60 days'),
    (30, '05_Tomap_Last_month', '30 days'),
    (21, '04_Tomap_Last_three_weeks', '21 days'),
    (15, '03_Tomap_Last_two_weeks', '15 days'),
    (7, '02_Tomap_Last_week', '7 days'),
    (0, '01_Tomap_Last_day', '1 day'),
]

PARQUET_TO_INCREMENTAL_COLUMNS = {
    'station_code': 'Codi Estació',
    'reading_datetime': 'Data Lectura',
    'station_name': 'Estació',
    'county': 'Comarca',
    'municipality': 'Municipi',
    'province': 'Provincia',
    'altitude': 'Altitud',
    'lat': 'Latitud',
    'lon': 'Longitud',
    'last_reading': 'Ultima Lectura',
    'variable': 'Variable',
    'rain_mm': 'Total',
    'unit': 'Unitat',
    'local_date': 'Data Local',
    'local_time': 'Hora Local',
    'max_temp_celsius': 'max_temp_celsius',
    'min_temp_celsius': 'min_temp_celsius',
    'max_humidity_percent': 'max_humidity_percent',
    'min_humidity_percent': 'min_humidity_percent',
    **{column: column for column in WIND_COLUMNS},
}


class TomapParquetSchemaError(RuntimeError):
    """Raised when weather_daily.parquet cannot satisfy the Tomap contract."""


def _apply_rain_quality_filters(
    df: pd.DataFrame,
    *,
    copy_input: bool = True,
) -> pd.DataFrame:
    """Nullify daily rain totals that are clearly erroneous before aggregation.

    Two filters applied per station sorted by date:
    1. Outlier: Total > 300 mm/day is physically implausible for a single day.
    2. Consecutive duplicate: identical non-zero rain on adjacent calendar days
       is a Wunderground sensor carry-forward artifact. Keep the first, nullify the rest.
    """
    if df.empty:
        return df
    if copy_input:
        df = df.copy()
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce')

    # 1. Outlier filter
    df.loc[df['Total'] > DAILY_RAIN_SANITY_LIMIT_MM, 'Total'] = pd.NA

    # 2. Consecutive duplicate filter — per station, sorted by date
    dates = pd.to_datetime(df['Data Local'], format='%Y%m%d', errors='coerce')
    # Sort only the three quality columns. Sorting the complete 28-column frame
    # created a second ~130k-row metadata copy for every Tomap period.
    quality = pd.DataFrame(
        {
            '_station': df['Codi Estació'],
            '_date': dates,
            '_total': df['Total'],
        },
        index=df.index,
    ).sort_values(['_station', '_date'])
    grouped = quality.groupby('_station', sort=False, observed=True)
    previous_total = grouped['_total'].shift(1)
    previous_date = grouped['_date'].shift(1)
    duplicate = (
        quality['_total'].notna()
        & quality['_total'].gt(0)
        & quality['_total'].eq(previous_total)
        & quality['_date'].notna()
        & previous_date.notna()
        & quality['_date'].sub(previous_date).eq(pd.Timedelta(days=1))
    )
    df.loc[quality.index[duplicate], 'Total'] = pd.NA

    return df


def create_empty_incremental():
    """Return the empty schema expected by the Tomap aggregation steps."""
    return pd.DataFrame(columns=INCREMENTAL_COLUMNS)


def read_incremental(data_dir: Path, name: str, nrows=None):
    """Read one incremental CSV and normalize the types used by Tomap."""
    csv_path = data_dir / f'{name}.csv'
    if not csv_path.exists():
        return create_empty_incremental()

    read_options = {'decimal': ',', 'low_memory': False}
    if nrows is None:
        df = pd.read_csv(csv_path, **read_options)
    else:
        df = pd.read_csv(csv_path, nrows=nrows, **read_options)

    if 'Data Lectura' in df.columns:
        df['Data Lectura'] = pd.to_datetime(df['Data Lectura'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    if 'Total' in df.columns:
        df['Total'] = df['Total'].astype(float)
    if 'Altitud' in df.columns:
        df['Altitud'] = df['Altitud'].astype(str)
    if 'Latitud' in df.columns:
        df['Latitud'] = df['Latitud'].astype(str)
    if 'Longitud' in df.columns:
        df['Longitud'] = df['Longitud'].astype(str)
    if 'Data Local' in df.columns:
        df['Data Local'] = df['Data Local'].astype(str)
    df = ensure_incremental_columns(df)

    return df


def read_weather_daily_parquet(
    data_dir: Path,
    *,
    include_aemet: bool,
    base_date: datetime,
    days_backward: int = 90,
    days_forward: int = 1,
) -> pd.DataFrame:
    """Read only Tomap's date window from the active canonical weather store."""
    start_date = (base_date - timedelta(days=days_backward)).strftime('%Y%m%d')
    end_date = (base_date + timedelta(days=days_forward)).strftime('%Y%m%d')
    from rainmapper_core.weather_history_capture import partitioned_history_enabled

    if partitioned_history_enabled():
        from rainmapper_core.weather_history_dataset import read_weather_history

        sources = {'meteoclimatic', 'meteocat', 'wunderground'}
        if include_aemet:
            sources.add('aemet')
        df = read_weather_history(
            data_dir,
            columns=['source', *PARQUET_TO_INCREMENTAL_COLUMNS],
            sources=sources,
            start_date=start_date,
            end_date=end_date,
        )
        input_label = 'partitioned weather history'
    else:
        input_label = 'weather_daily.parquet'
        parquet_path = data_dir / 'weather_daily.parquet'
        if not parquet_path.exists():
            raise FileNotFoundError(f'Required Tomap input does not exist: {parquet_path}')

        import pyarrow.parquet as pq

        required_columns = {'source', *PARQUET_TO_INCREMENTAL_COLUMNS}
        available_columns = set(pq.ParquetFile(parquet_path).schema_arrow.names)
        missing_columns = sorted(required_columns - available_columns)
        if missing_columns:
            raise TomapParquetSchemaError(
                'weather_daily.parquet uses an obsolete/incomplete Tomap schema; '
                f'missing columns: {", ".join(missing_columns)}'
            )

        df = pd.read_parquet(
            parquet_path,
            columns=['source', *PARQUET_TO_INCREMENTAL_COLUMNS],
            filters=[('local_date', '>=', start_date), ('local_date', '<=', end_date)],
        )
        if not include_aemet:
            df = df.loc[df['source'] != 'aemet'].copy()

    df.rename(columns=PARQUET_TO_INCREMENTAL_COLUMNS, inplace=True)
    if 'Data Lectura' in df.columns:
        df['Data Lectura'] = pd.to_datetime(df['Data Lectura'], errors='coerce')
    df['Data Local'] = pd.to_datetime(df['Data Local'], format='%Y%m%d', errors='coerce')
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
    for column in ('Altitud', 'Latitud', 'Longitud'):
        df[column] = df[column].astype(str)
    df = ensure_incremental_columns(df, copy_input=False)
    # The partitioned 90-day window contains many repeated station metadata
    # strings. Python-object strings use roughly three times the useful payload
    # on ARM64 and made Tomap touch the 384 MiB container gate. Arrow-backed
    # strings preserve values/CSV formatting while keeping the dataframe
    # compact through all seven period aggregations.
    object_columns = list(df.select_dtypes(include='object').columns)
    if object_columns:
        df[object_columns] = df[object_columns].astype('string[pyarrow]')
    df.attrs['weather_input'] = input_label
    return df


def read_recent_incremental_csvs(
    data_dir: Path,
    *,
    include_aemet: bool,
    base_date: datetime,
    max_threads: int,
) -> pd.DataFrame:
    """Build the former CSV input for migration parity tests only."""
    names = ['Meteoclimatic_incremental', 'Meteocat_incremental', 'Wunderground_incremental']
    if include_aemet:
        names.append('Aemet_incremental')
    with ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix='TomapCSVParity') as executor:
        frames = list(executor.map(
            lambda name: create_filtered(read_incremental(data_dir, name), base_date, 90, 1),
            names,
        ))
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return create_empty_incremental()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', FutureWarning)
        return pd.concat(frames, ignore_index=True).drop_duplicates()


def ensure_incremental_columns(df: pd.DataFrame, *, copy_input: bool = True):
    """Add optional incremental columns missing from older CSV/dataframe callers."""
    result = df.copy() if copy_input else df
    for column in INCREMENTAL_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    return result


def numeric_series(values):
    """Normalize optional numeric CSV values to a pandas float series."""
    return pd.to_numeric(pd.Series(values), errors='coerce')


def optional_max(values):
    """Return the maximum numeric value in a group while preserving missing-only groups."""
    series = numeric_series(values).dropna()
    return pd.NA if series.empty else round(float(series.max()), 1)


def optional_min(values):
    """Return the minimum numeric value in a group while preserving missing-only groups."""
    series = numeric_series(values).dropna()
    return pd.NA if series.empty else round(float(series.min()), 1)


def optional_sum(values):
    """Return the sum of numeric values while preserving missing-only groups."""
    series = numeric_series(values).dropna()
    return pd.NA if series.empty else round(float(series.sum()), 1)


def weighted_wind_average(values, weights=None):
    """Average daily wind speeds, using observation counts when available."""
    speeds = numeric_series(values)
    valid = speeds.notna()
    if not valid.any():
        return pd.NA

    if weights is None:
        return round(float(speeds[valid].mean()), 1)

    weight_values = numeric_series(weights)
    weight_values = weight_values.reindex(speeds.index).where(valid)
    positive_weights = weight_values.fillna(0) > 0
    if positive_weights.any():
        weighted = (speeds[positive_weights] * weight_values[positive_weights]).sum() / weight_values[positive_weights].sum()
        return round(float(weighted), 1)

    return round(float(speeds[valid].mean()), 1)


def circular_mean_series(values):
    """Return a circular mean for grouped direction values."""
    return circular_mean_degrees(values)


def add_circular_mean_column(grouped_df: pd.DataFrame, source_df: pd.DataFrame, source_column, target_column):
    """Add a grouped circular mean column using vectorized sine/cosine sums."""
    directions = pd.to_numeric(source_df[source_column], errors='coerce')
    radians = directions * math.pi / 180.0
    trig_df = pd.DataFrame({
        'Codi Estació': source_df['Codi Estació'],
        '_sin': np.sin(radians),
        '_cos': np.cos(radians),
    })
    grouped_trig = trig_df.groupby('Codi Estació').agg({
        '_sin': 'sum',
        '_cos': 'sum',
    })

    def angle(row):
        sin_sum = row['_sin']
        cos_sum = row['_cos']
        if pd.isna(sin_sum) or pd.isna(cos_sum):
            return pd.NA
        if math.isclose(float(sin_sum), 0.0, abs_tol=1e-12) and math.isclose(float(cos_sum), 0.0, abs_tol=1e-12):
            return pd.NA
        result = round(math.degrees(math.atan2(float(sin_sum), float(cos_sum))) % 360.0, 1)
        return 0.0 if math.isclose(result, 360.0) else result

    grouped_df[target_column] = grouped_trig.apply(angle, axis=1)


def filter_results(df: pd.DataFrame, minimum_rain):
    """Keep only rows whose accumulated rain meets the configured threshold."""
    df = df.copy()
    totals = pd.to_numeric(df['Total'], errors='coerce')
    keep_rows = totals >= minimum_rain
    if minimum_rain <= 0:
        keep_rows = keep_rows | totals.isna()
    return df.loc[keep_rows].copy()


def save_dataframe_tomap(df, maps_dir: Path, file_name, save_to_csv=True, decimal='.'):
    """Write one Tomap dataframe using the legacy CSV naming convention."""
    if save_to_csv:
        maps_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(maps_dir / f'{file_name}.csv', decimal=decimal, index=False)


def merge_dataframes(data_dir: Path, source01_df_param: pd.DataFrame, source02_df_param: pd.DataFrame):
    """Merge two source dataframes preserving the legacy full-row outer merge."""
    source01_df = source01_df_param.copy()
    if source01_df.empty:
        source01_df = read_incremental(data_dir, 'Meteocat_incremental', nrows=0)
    source02_df = source02_df_param.copy()
    if source02_df.empty:
        source02_df = read_incremental(data_dir, 'Meteocat_incremental', nrows=0)

    source01_df.reset_index(drop=True, inplace=True)
    source02_df.reset_index(drop=True, inplace=True)

    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore',
            category=FutureWarning,
            message='The behavior of DataFrame concatenation with empty or all-NA entries is deprecated.*',
        )
        csv_completo = pd.concat([source01_df, source02_df], ignore_index=True).drop_duplicates()
    csv_completo.sort_values(by=['Total', 'Codi Estació'], ascending=[False, True], inplace=True)
    csv_completo.reset_index(drop=True, inplace=True)
    return csv_completo


def create_filtered(df_to_filter_param: pd.DataFrame, base_date, days_backward, days_forward):
    """Filter source history to the requested local date window."""
    thread_name = threading.current_thread().name
    print(f'[{thread_name}] Starting thread for dataframe filtering')

    df_to_filter = df_to_filter_param
    start_date = base_date - timedelta(days=days_backward)
    end_date = base_date + timedelta(days=days_forward)

    if not pd.api.types.is_datetime64_any_dtype(df_to_filter['Data Local']):
        df_to_filter['Data Local'] = pd.to_datetime(df_to_filter['Data Local'], format='%Y%m%d', errors='coerce')

    date_mask = (df_to_filter['Data Local'] >= start_date) & (df_to_filter['Data Local'] <= end_date)
    return df_to_filter.loc[date_mask].copy()


def create_grouped(
    df_to_group_param: pd.DataFrame,
    minimum_rain_tomap,
    *,
    copy_input: bool = True,
):
    """Aggregate one row per station for the selected Tomap period."""
    df_to_group = ensure_incremental_columns(
        df_to_group_param,
        copy_input=copy_input,
    )
    if df_to_group.empty:
        return df_to_group.head(0)
    df_to_group = _apply_rain_quality_filters(df_to_group, copy_input=False)

    for column in [
        'max_temp_celsius',
        'min_temp_celsius',
        'max_humidity_percent',
        'min_humidity_percent',
        'wind_avg_kmh',
        'wind_min_kmh',
        'wind_max_kmh',
        'wind_gust_kmh',
        'wind_observation_count',
    ]:
        df_to_group[column] = pd.to_numeric(df_to_group[column], errors='coerce')

    latest_columns = [
        'Codi Estació',
        'Estació',
        'Comarca',
        'Municipi',
        'Provincia',
        'Altitud',
        'Latitud',
        'Longitud',
        'Variable',
        'Unitat',
        'wind_source_height_m',
    ]
    latest_order = df_to_group['Ultima Lectura'].sort_values().index
    latest = (
        df_to_group.loc[latest_order, latest_columns]
        .groupby('Codi Estació', as_index=True, observed=True)
        .last()
    )

    grouped = df_to_group.groupby('Codi Estació', as_index=True).agg({
        'Ultima Lectura': 'max',
        'Total': optional_sum,
        'Data Local': 'max',
        'max_temp_celsius': 'max',
        'min_temp_celsius': 'min',
        'max_humidity_percent': 'max',
        'min_humidity_percent': 'min',
        'wind_min_kmh': 'min',
        'wind_max_kmh': 'max',
        'wind_gust_kmh': 'max',
        'wind_observation_count': 'sum',
    })

    wind_speed = df_to_group['wind_avg_kmh']
    wind_weight = df_to_group['wind_observation_count'].where(df_to_group['wind_observation_count'] > 0, 0)
    weighted_df = pd.DataFrame({
        'Codi Estació': df_to_group['Codi Estació'],
        '_weighted_speed': wind_speed * wind_weight,
        '_weight': wind_weight.where(wind_speed.notna(), 0),
        '_speed': wind_speed,
    })
    weighted = weighted_df.groupby('Codi Estació').agg({
        '_weighted_speed': 'sum',
        '_weight': 'sum',
        '_speed': 'mean',
    })
    grouped['wind_avg_kmh'] = (weighted['_weighted_speed'] / weighted['_weight']).where(
        weighted['_weight'] > 0,
        weighted['_speed'],
    ).round(1)
    add_circular_mean_column(grouped, df_to_group, 'wind_direction_deg', 'wind_direction_deg')
    add_circular_mean_column(grouped, df_to_group, 'wind_gust_direction_deg', 'wind_gust_direction_deg')

    datos_finales = latest.join(grouped).reset_index(drop=False)
    datos_finales['Total'] = datos_finales['Total'].round(1)
    for column in [
        'max_temp_celsius',
        'min_temp_celsius',
        'max_humidity_percent',
        'min_humidity_percent',
        'wind_min_kmh',
        'wind_max_kmh',
        'wind_gust_kmh',
        'wind_observation_count',
    ]:
        datos_finales[column] = datos_finales[column].round(1)
    datos_finales.sort_values(by=['Total'], ascending=[False], inplace=True)
    datos_finales.reset_index(drop=True, inplace=True)

    return filter_results(datos_finales, minimum_rain_tomap)


def create_last_rains(
    df: pd.DataFrame,
    maps_dir: Path,
    nrecords,
    minimum_rain_tomap,
    *,
    copy_input: bool = True,
):
    """Build the wide LastXX_rains table consumed by station popups."""
    df = ensure_incremental_columns(df, copy_input=copy_input)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
    key_columns = ['Codi Estació', 'Data Local']
    grouped = df.groupby(key_columns, sort=False, dropna=True)

    result_step1 = grouped.agg({
        'Data Lectura': 'first',
        'Estació': 'first',
        'Comarca': 'first',
        'Municipi': 'first',
        'Provincia': 'first',
        'Altitud': 'first',
        'Latitud': 'first',
        'Longitud': 'first',
        'Ultima Lectura': 'first',
        'Variable': 'first',
        'Unitat': 'first',
        'max_temp_celsius': 'first',
        'min_temp_celsius': 'first',
        'max_humidity_percent': 'first',
        'min_humidity_percent': 'first',
        'wind_avg_kmh': 'first',
        'wind_min_kmh': 'first',
        'wind_max_kmh': 'first',
        'wind_gust_kmh': 'first',
        'wind_direction_deg': 'first',
        'wind_gust_direction_deg': 'first',
        'wind_observation_count': 'first',
        'Hora Local': 'first',
    }).reset_index()
    result_step1['Total'] = grouped['Total'].sum(min_count=1).round(1).to_numpy()
    result_step1 = _apply_rain_quality_filters(result_step1)

    result_step1 = filter_results(result_step1, minimum_rain_tomap)
    result_step2 = (
        result_step1
        .sort_values(['Codi Estació', 'Data Local'], ascending=[True, False])
        .groupby('Codi Estació', as_index=False)
        .head(nrecords)
        .reset_index(drop=True)
    )

    result_step2['Data Local'] = pd.to_datetime(result_step2['Data Local']).dt.strftime('%Y/%m/%d')
    result_step3 = result_step2.pivot_table(
        index='Codi Estació',
        columns=result_step2.groupby('Codi Estació').cumcount().add(1),
        values=[
            'Data Local',
            'Total',
            'max_temp_celsius',
            'min_temp_celsius',
            'max_humidity_percent',
            'min_humidity_percent',
            'wind_avg_kmh',
            'wind_min_kmh',
            'wind_max_kmh',
            'wind_gust_kmh',
            'wind_direction_deg',
            'wind_gust_direction_deg',
            'wind_observation_count',
        ],
        aggfunc='first',
    )

    expected_value_columns = [
        'Data Local',
        'Total',
        'max_humidity_percent',
        'max_temp_celsius',
        'min_humidity_percent',
        'min_temp_celsius',
        'wind_avg_kmh',
        'wind_direction_deg',
        'wind_gust_kmh',
        'wind_gust_direction_deg',
        'wind_max_kmh',
        'wind_min_kmh',
        'wind_observation_count',
    ]
    expected_columns = pd.MultiIndex.from_product([expected_value_columns, range(1, nrecords + 1)])
    result_step3 = result_step3.reindex(columns=expected_columns)

    for i in range(1, nrecords + 1):
        result_step3[('Data Local', i)] = pd.to_datetime(
            result_step3[('Data Local', i)],
            errors='coerce',
        ).dt.strftime('%d/%m/%Y')

    result_step3.columns = (
        [f'Data_Pluja_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Pluja_Diaria_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Hum_Max_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Temp_Max_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Hum_Min_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Temp_Min_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Wind_Avg_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Wind_Dir_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Wind_Gust_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Wind_Gust_Dir_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Wind_Max_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Wind_Min_{i:02}' for i in range(1, nrecords + 1)]
        + [f'Wind_Obs_{i:02}' for i in range(1, nrecords + 1)]
    )

    result_step3.reset_index(drop=False, inplace=True)

    for i in range(1, nrecords + 1):
        column_name = f'Data_Pluja_{i:02}'
        result_step3[column_name] = result_step3[column_name].astype(str).str.split('.').str[0]

    for i in range(1, nrecords + 1):
        column_name = f'Pluja_Diaria_{i:02}'
        result_step3[column_name] = result_step3[column_name].round(decimals=1)

    save_dataframe_tomap(result_step3, maps_dir, f'Last{nrecords}_rains', save_to_csv=True, decimal='.')
    return result_step3


def build_tomap_outputs(
    df_total: pd.DataFrame,
    maps_dir: Path,
    *,
    base_date: datetime,
    last_rains_history: int,
    minimum_rain_tomap: float,
) -> int:
    """Write Last rains and the seven Tomap products from a recent dataframe."""
    if df_total.empty:
        print('')
        print('NO RECORDS FOUND IN THE LAST 90 DAYS -- Exiting program')
        print('')
        return 1

    last_rains_started = time_module.perf_counter()
    df_last_rains = create_last_rains(
        df_total,
        maps_dir,
        nrecords=last_rains_history,
        minimum_rain_tomap=minimum_rain_tomap,
        copy_input=False,
    )
    print(f"Tomap last-rains duration: {time_module.perf_counter() - last_rains_started:.1f}s ({len(df_last_rains)} station row(s))")

    for days_backward, file_name, label in TOMAP_PERIODS:
        period_started = time_module.perf_counter()
        print(f'Start processing {label} backward Tomap...')
        if days_backward == 90:
            df_period = df_total
        else:
            df_period = create_filtered(df_total, base_date, days_backward, 1)
        df_toprint = create_grouped(
            df_period,
            minimum_rain_tomap,
            copy_input=days_backward == 90,
        )
        df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
        save_dataframe_tomap(df_tomap, maps_dir, file_name, save_to_csv=True)
        print(
            f'Finished processing {label} backward Tomap'
            f'--> Time elapsed: {time_module.perf_counter() - period_started:.1f}s'
        )

    return 0


def build_tomap(data_dir: Path, maps_dir: Path, last_rains_history, minimum_rain_tomap, max_threads, include_aemet=False):
    """Rebuild Tomap products from the filtered weather_daily.parquet window."""
    total_started = time_module.perf_counter()
    maps_dir.mkdir(parents=True, exist_ok=True)
    base_date = datetime.combine(date.today(), time())

    print('')
    print('Start rebuilding Tomap CSV files from weather_daily.parquet...')
    print(f'Data dir: {data_dir}')
    print(f'Tomap dir: {maps_dir}')
    print(f'Last rains history: {last_rains_history}')
    print(f'Include AEMET: {include_aemet}')

    load_started = time_module.perf_counter()
    try:
        df_total = read_weather_daily_parquet(
            data_dir,
            include_aemet=include_aemet,
            base_date=base_date,
        )
    except (FileNotFoundError, TomapParquetSchemaError, OSError, RuntimeError, ValueError) as exc:
        print(f'Tomap Parquet input error: {exc}')
        return 1

    source_counts = df_total['source'].value_counts().to_dict() if 'source' in df_total else {}
    print(
        f"Tomap filtered Parquet load duration: {time_module.perf_counter() - load_started:.1f}s "
        f"({len(df_total)} row(s), sources={source_counts})"
    )
    exit_code = build_tomap_outputs(
        df_total,
        maps_dir,
        base_date=base_date,
        last_rains_history=last_rains_history,
        minimum_rain_tomap=minimum_rain_tomap,
    )
    print(f'Finished rebuilding Tomap CSV files. Total duration: {time_module.perf_counter() - total_started:.1f}s')
    return exit_code


def positive_int(value):
    """Parse a positive integer for CLI options."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return parsed


def default_settings():
    """Return Tomap defaults from the shared Rainmapper configuration."""
    return {
        'data_dir': rainmapper_const._DATA_PATH,
        'maps_dir': rainmapper_const._MAPS_PATH,
        'last_rains_history': rainmapper_const._last_number_rains,
        'minimum_rain_tomap': rainmapper_const._minimum_rain_tomap,
        'max_threads': rainmapper_const._max_threads,
    }


def parse_args(argv=None, defaults=None):
    """Parse Tomap builder CLI arguments with caller-provided defaults."""
    defaults = default_settings() | (defaults or {})
    parser = argparse.ArgumentParser(description='Rebuild Rainmapper Tomap CSV files from incremental history.')
    parser.add_argument('--data-dir', default=defaults.get('data_dir'), help='Directory containing incremental CSV files.')
    parser.add_argument('--maps-dir', default=defaults.get('maps_dir'), help='Directory where Tomap CSV files will be written.')
    parser.add_argument(
        '--last-rains-history',
        type=positive_int,
        default=defaults.get('last_rains_history'),
        help='Number of recent rain records to generate for station popups.',
    )
    parser.add_argument(
        '--minimum-rain-tomap',
        type=float,
        default=defaults.get('minimum_rain_tomap'),
        help='Minimum daily rain included in Tomap last-rains history.',
    )
    parser.add_argument(
        '--max-threads',
        type=positive_int,
        default=max(1, defaults.get('max_threads', 1)),
        help='Number of worker threads used while filtering source histories.',
    )
    parser.add_argument(
        '--include-aemet',
        nargs='?',
        const=True,
        type=lambda value: str(value).lower() in ['true', '1', 'yes'],
        default=False,
        help='Include Aemet_incremental.csv when rebuilding Tomap files.',
    )
    return parser.parse_args(argv)


def main(argv=None, defaults=None):
    """Run the CLI entrypoint and return the Tomap builder exit code."""
    args = parse_args(argv=argv, defaults=defaults)

    data_dir = Path(args.data_dir).resolve()
    maps_dir = Path(args.maps_dir).resolve()
    return build_tomap(
        data_dir=data_dir,
        maps_dir=maps_dir,
        last_rains_history=args.last_rains_history,
        minimum_rain_tomap=args.minimum_rain_tomap,
        max_threads=args.max_threads,
        include_aemet=args.include_aemet,
    )


if __name__ == '__main__':
    raise SystemExit(main())
