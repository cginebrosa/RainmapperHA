"""Rebuild Rainmapper Tomap CSV files from incremental history.

This module is the canonical Tomap entrypoint. Run it with
`python -m rainmapper_core.tomap`. The functions keep the legacy Tomap output
format while making the implementation reusable from tests, Docker local and
the HA app package.
"""

import argparse
import math
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

TOMAP_PERIODS = [
    (90, '07_Tomap_Last_three_months', '90 days'),
    (60, '06_Tomap_Last_two_months', '60 days'),
    (30, '05_Tomap_Last_month', '30 days'),
    (21, '04_Tomap_Last_three_weeks', '21 days'),
    (15, '03_Tomap_Last_two_weeks', '15 days'),
    (7, '02_Tomap_Last_week', '7 days'),
    (0, '01_Tomap_Last_day', '1 day'),
]


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


def ensure_incremental_columns(df: pd.DataFrame):
    """Add optional incremental columns missing from older CSV/dataframe callers."""
    result = df.copy()
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
    return df.query('Total >= @minimum_rain')


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

    df_to_filter = df_to_filter_param.copy()
    start_date = base_date - timedelta(days=days_backward)
    end_date = base_date + timedelta(days=days_forward)

    if not pd.api.types.is_datetime64_any_dtype(df_to_filter['Data Local']):
        df_to_filter['Data Local'] = pd.to_datetime(df_to_filter['Data Local'], format='%Y%m%d', errors='coerce')

    date_mask = (df_to_filter['Data Local'] >= start_date) & (df_to_filter['Data Local'] <= end_date)
    return df_to_filter.loc[date_mask].copy()


def create_grouped(df_to_group_param: pd.DataFrame, minimum_rain_tomap):
    """Aggregate one row per station for the selected Tomap period."""
    df_to_group = ensure_incremental_columns(df_to_group_param)
    if df_to_group.empty:
        return df_to_group.head(0)

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

    sorted_df = df_to_group.sort_values('Ultima Lectura')
    latest = sorted_df.groupby('Codi Estació', as_index=True).last()[[
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
    ]]

    grouped = df_to_group.groupby('Codi Estació', as_index=True).agg({
        'Ultima Lectura': 'max',
        'Total': 'sum',
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


def create_last_rains(df: pd.DataFrame, maps_dir: Path, nrecords, minimum_rain_tomap):
    """Build the wide LastXX_rains table consumed by station popups."""
    df = ensure_incremental_columns(df)
    result_step1 = df.groupby(['Codi Estació', 'Data Local'], as_index=False).agg({
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
        'Total': 'sum',
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
    })

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


def build_tomap(data_dir: Path, maps_dir: Path, last_rains_history, minimum_rain_tomap, max_threads, include_aemet=False):
    """Rebuild all Tomap period files from existing incremental CSV history."""
    maps_dir.mkdir(parents=True, exist_ok=True)

    meteoclimatic_incremental = read_incremental(data_dir, 'Meteoclimatic_incremental')
    meteocat_incremental = read_incremental(data_dir, 'Meteocat_incremental')
    wunderground_incremental = read_incremental(data_dir, 'Wunderground_incremental')
    aemet_incremental = read_incremental(data_dir, 'Aemet_incremental') if include_aemet else create_empty_incremental()

    if (
        len(meteoclimatic_incremental) == 0
        and len(meteocat_incremental) == 0
        and len(wunderground_incremental) == 0
        and len(aemet_incremental) == 0
    ):
        print('')
        print('NO RECORDS RETURNED FOR SELECTION -- Exiting program')
        print('')
        return 1

    base_date = datetime.combine(date.today(), time())
    days_forward = 1

    print('')
    print('Start rebuilding Tomap CSV files from incremental history...')
    print(f'Data dir: {data_dir}')
    print(f'Tomap dir: {maps_dir}')
    print(f'Last rains history: {last_rains_history}')
    print(f'Include AEMET: {include_aemet}')

    with ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix='TomapFilterProcesses') as executor:
        future_meteoclimatic_df = executor.submit(
            create_filtered,
            meteoclimatic_incremental,
            base_date,
            90,
            days_forward,
        )
        future_meteocat_df = executor.submit(
            create_filtered,
            meteocat_incremental,
            base_date,
            90,
            days_forward,
        )
        future_wunderground_df = executor.submit(
            create_filtered,
            wunderground_incremental,
            base_date,
            90,
            days_forward,
        )
        future_aemet_df = executor.submit(
            create_filtered,
            aemet_incremental,
            base_date,
            90,
            days_forward,
        )
        meteoclimatic_df = future_meteoclimatic_df.result()
        meteocat_df = future_meteocat_df.result()
        wunderground_df = future_wunderground_df.result()
        aemet_df = future_aemet_df.result()

    df_total = merge_dataframes(data_dir, meteocat_df, wunderground_df)
    df_total = merge_dataframes(data_dir, df_total, meteoclimatic_df)
    df_total = merge_dataframes(data_dir, df_total, aemet_df)

    if df_total.empty:
        print('')
        print('NO RECORDS FOUND IN THE LAST 90 DAYS -- Exiting program')
        print('')
        return 1

    df_last_rains = create_last_rains(
        df_total,
        maps_dir,
        nrecords=last_rains_history,
        minimum_rain_tomap=minimum_rain_tomap,
    )

    for days_backward, file_name, label in TOMAP_PERIODS:
        print(f'Start processing {label} backward Tomap...')
        if days_backward == 90:
            df_period = df_total
        else:
            df_period = create_filtered(df_total, base_date, days_backward, days_forward)
        df_toprint = create_grouped(df_period, minimum_rain_tomap)
        df_tomap = pd.merge(df_toprint, df_last_rains, how='inner')
        save_dataframe_tomap(df_tomap, maps_dir, file_name, save_to_csv=True)
        print(f'Finished processing {label} backward Tomap')

    print('Finished rebuilding Tomap CSV files.')
    return 0


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
