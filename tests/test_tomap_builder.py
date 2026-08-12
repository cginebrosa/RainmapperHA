import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd

from rainmapper_core import mushroom_observation_context
from rainmapper_core import tomap as tomap_builder


def make_incremental_row(station_code, reading_date, rain):
    reading_datetime = datetime.combine(reading_date, datetime.min.time()).replace(hour=8)
    return {
        'Codi Estació': station_code,
        'Data Lectura': reading_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        'Estació': f'Station {station_code}',
        'Comarca': 'Test',
        'Municipi': 'Testville',
        'Provincia': 'Test',
        'Altitud': '100',
        'Latitud': '41.1',
        'Longitud': '2.1',
        'Ultima Lectura': reading_datetime.strftime('%Y/%m/%d %H:%M:%S'),
        'Variable': 'Precipitació',
        'Total': rain,
        'Unitat': 'mm',
        'Data Local': reading_date.strftime('%Y%m%d'),
        'Hora Local': '08:00:00',
        'max_temp_celsius': 20.0,
        'min_temp_celsius': 12.0,
        'max_humidity_percent': 80.0,
        'min_humidity_percent': 45.0,
        'wind_avg_kmh': 8.0,
        'wind_min_kmh': 4.0,
        'wind_max_kmh': 12.0,
        'wind_gust_kmh': 18.0,
        'wind_direction_deg': 350.0,
        'wind_gust_direction_deg': 20.0,
        'wind_observation_count': 1,
        'wind_source_height_m': 10,
    }


def generate_parquet(data_dir):
    output = mushroom_observation_context.generate_weather_daily_parquet(data_dir)
    if output is None:
        raise AssertionError('weather_daily.parquet was not generated')


class TomapBuilderTests(unittest.TestCase):
    def test_parquet_and_legacy_csv_inputs_produce_all_eight_equivalent_products(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / 'Data'
            csv_maps_dir = tmp_path / 'TomapCSV'
            parquet_maps_dir = tmp_path / 'TomapParquet'
            data_dir.mkdir()
            today = date.today()

            sources = [
                ('Meteocat_incremental.csv', 'MC', 0, 1.1),
                ('Meteoclimatic_incremental.csv', 'MCL', 8, 2.2),
                ('Wunderground_incremental.csv', 'WU', 25, 3.3),
                ('Aemet_incremental.csv', 'AE', 65, 4.4),
            ]
            for filename, station, age_days, rain in sources:
                rows = [
                    make_incremental_row(station, today - timedelta(days=age_days), rain),
                    make_incremental_row(station, today - timedelta(days=min(age_days + 1, 89)), rain / 2),
                ]
                pd.DataFrame(rows).to_csv(data_dir / filename, decimal=',', index=False)

            base_date = datetime.combine(today, datetime.min.time())
            with redirect_stdout(StringIO()):
                csv_input = tomap_builder.read_recent_incremental_csvs(
                    data_dir,
                    include_aemet=True,
                    base_date=base_date,
                    max_threads=1,
                )
                csv_exit_code = tomap_builder.build_tomap_outputs(
                    csv_input,
                    csv_maps_dir,
                    base_date=base_date,
                    last_rains_history=3,
                    minimum_rain_tomap=0,
                )
                generate_parquet(data_dir)
                parquet_exit_code = tomap_builder.build_tomap(
                    data_dir=data_dir,
                    maps_dir=parquet_maps_dir,
                    last_rains_history=3,
                    minimum_rain_tomap=0,
                    max_threads=1,
                    include_aemet=True,
                )

            self.assertEqual((csv_exit_code, parquet_exit_code), (0, 0))
            expected_files = {f'{file_name}.csv' for _, file_name, _ in tomap_builder.TOMAP_PERIODS}
            expected_files.add('Last3_rains.csv')
            self.assertEqual({path.name for path in parquet_maps_dir.glob('*.csv')}, expected_files)
            for filename in sorted(expected_files):
                csv_product = pd.read_csv(csv_maps_dir / filename).sort_values('Codi Estació').reset_index(drop=True)
                parquet_product = pd.read_csv(parquet_maps_dir / filename).sort_values('Codi Estació').reset_index(drop=True)
                pd.testing.assert_frame_equal(csv_product, parquet_product, check_dtype=False)

    def test_build_tomap_rebuilds_all_periods_and_last_rains_history(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / 'Data'
            maps_dir = tmp_path / 'Tomap'
            data_dir.mkdir()

            today = date.today()
            rows = [
                make_incremental_row('TEST_ONE', today, 1.2),
                make_incremental_row('TEST_ONE', today - timedelta(days=1), 0.8),
                make_incremental_row('TEST_ONE', today - timedelta(days=10), 4.4),
                make_incremental_row('TEST_TWO', today - timedelta(days=2), 2.0),
            ]
            pd.DataFrame(rows).to_csv(data_dir / 'Meteocat_incremental.csv', decimal=',', index=False)
            generate_parquet(data_dir)

            with redirect_stdout(StringIO()):
                exit_code = tomap_builder.build_tomap(
                    data_dir=data_dir,
                    maps_dir=maps_dir,
                    last_rains_history=3,
                    minimum_rain_tomap=0,
                    max_threads=1,
                )

            self.assertEqual(exit_code, 0)
            expected_files = {
                '01_Tomap_Last_day.csv',
                '02_Tomap_Last_week.csv',
                '03_Tomap_Last_two_weeks.csv',
                '04_Tomap_Last_three_weeks.csv',
                '05_Tomap_Last_month.csv',
                '06_Tomap_Last_two_months.csv',
                '07_Tomap_Last_three_months.csv',
                'Last3_rains.csv',
            }
            self.assertEqual({path.name for path in maps_dir.glob('*.csv')}, expected_files)

            last_rains = pd.read_csv(maps_dir / 'Last3_rains.csv')
            self.assertIn('Data_Pluja_03', last_rains.columns)
            self.assertNotIn('Data_Pluja_04', last_rains.columns)

            last_day = pd.read_csv(maps_dir / '01_Tomap_Last_day.csv')
            self.assertEqual(last_day['Codi Estació'].tolist(), ['TEST_ONE'])
            self.assertIn('Pluja_Diaria_03', last_day.columns)
            self.assertNotIn('Pluja_Diaria_04', last_day.columns)
            self.assertIn('Wind_Avg_01', last_day.columns)
            self.assertIn('Hum_Max_01', last_day.columns)

    def test_build_tomap_aggregates_period_weather_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / 'Data'
            maps_dir = tmp_path / 'Tomap'
            data_dir.mkdir()

            today = date.today()
            first = make_incremental_row('TEST_ONE', today, 1.0)
            first['max_humidity_percent'] = 70.0
            first['min_humidity_percent'] = 40.0
            first['wind_avg_kmh'] = 10.0
            first['wind_direction_deg'] = 350.0
            first['wind_observation_count'] = 2
            second = make_incremental_row('TEST_ONE', today - timedelta(days=1), 2.0)
            second['max_humidity_percent'] = 90.0
            second['min_humidity_percent'] = 35.0
            second['wind_avg_kmh'] = 20.0
            second['wind_direction_deg'] = 10.0
            second['wind_gust_kmh'] = 30.0
            second['wind_observation_count'] = 1
            pd.DataFrame([first, second]).to_csv(data_dir / 'Meteocat_incremental.csv', decimal=',', index=False)
            generate_parquet(data_dir)

            with redirect_stdout(StringIO()):
                exit_code = tomap_builder.build_tomap(
                    data_dir=data_dir,
                    maps_dir=maps_dir,
                    last_rains_history=2,
                    minimum_rain_tomap=0,
                    max_threads=1,
                )

            self.assertEqual(exit_code, 0)
            week = pd.read_csv(maps_dir / '02_Tomap_Last_week.csv')
            row = week.iloc[0]
            self.assertEqual(row['Total'], 3.0)
            self.assertEqual(row['max_humidity_percent'], 90.0)
            self.assertEqual(row['min_humidity_percent'], 35.0)
            self.assertEqual(round(row['wind_avg_kmh'], 1), 13.3)
            self.assertEqual(row['wind_gust_kmh'], 30.0)
            self.assertEqual(row['wind_direction_deg'], 0.0)
            self.assertEqual(row['wind_observation_count'], 3)

            last_rains = pd.read_csv(maps_dir / 'Last2_rains.csv')
            self.assertIn('Wind_Avg_01', last_rains.columns)
            self.assertIn('Wind_Dir_01', last_rains.columns)
            self.assertIn('Wind_Gust_01', last_rains.columns)

    def test_build_tomap_includes_optional_aemet_incremental(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / 'Data'
            maps_dir = tmp_path / 'Tomap'
            data_dir.mkdir()

            today = date.today()
            rows = [
                make_incremental_row('AEMET:9632X', today, 6.4),
            ]
            pd.DataFrame(rows).to_csv(data_dir / 'Aemet_incremental.csv', decimal=',', index=False)
            generate_parquet(data_dir)

            with redirect_stdout(StringIO()):
                exit_code = tomap_builder.build_tomap(
                    data_dir=data_dir,
                    maps_dir=maps_dir,
                    last_rains_history=3,
                    minimum_rain_tomap=0,
                    max_threads=1,
                    include_aemet=True,
                )

            self.assertEqual(exit_code, 0)
            last_day = pd.read_csv(maps_dir / '01_Tomap_Last_day.csv')
            self.assertEqual(last_day['Codi Estació'].tolist(), ['AEMET:9632X'])
            self.assertEqual(last_day['Total'].tolist(), [6.4])

    def test_build_tomap_includes_aemet_when_optional_columns_have_mixed_dtypes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / 'Data'
            maps_dir = tmp_path / 'Tomap'
            data_dir.mkdir()

            today = date.today()
            meteocat_row = make_incremental_row('METEO_TEST', today, 1.2)
            meteocat_row['max_temp_celsius'] = ''
            aemet_row = make_incremental_row('AEMET:9632X', today, 6.4)
            aemet_row['max_temp_celsius'] = pd.NA
            aemet_row['min_temp_celsius'] = pd.NA
            aemet_row['max_humidity_percent'] = pd.NA
            aemet_row['min_humidity_percent'] = pd.NA

            pd.DataFrame([meteocat_row]).to_csv(data_dir / 'Meteocat_incremental.csv', decimal=',', index=False)
            pd.DataFrame([aemet_row]).to_csv(data_dir / 'Aemet_incremental.csv', decimal=',', index=False)
            generate_parquet(data_dir)

            with redirect_stdout(StringIO()):
                exit_code = tomap_builder.build_tomap(
                    data_dir=data_dir,
                    maps_dir=maps_dir,
                    last_rains_history=3,
                    minimum_rain_tomap=0,
                    max_threads=1,
                    include_aemet=True,
                )

            self.assertEqual(exit_code, 0)
            last_day = pd.read_csv(maps_dir / '01_Tomap_Last_day.csv')
            self.assertEqual(set(last_day['Codi Estació']), {'METEO_TEST', 'AEMET:9632X'})

    def test_build_tomap_preserves_missing_rain_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / 'Data'
            maps_dir = tmp_path / 'Tomap'
            data_dir.mkdir()

            today = date.today()
            missing_rain = make_incremental_row('NO_RAIN_DATA', today, pd.NA)
            zero_rain = make_incremental_row('ZERO_RAIN', today, 0.0)
            rainy = make_incremental_row('RAINY', today, 2.4)
            pd.DataFrame([missing_rain, zero_rain, rainy]).to_csv(
                data_dir / 'Meteocat_incremental.csv',
                decimal=',',
                index=False,
            )
            generate_parquet(data_dir)

            with redirect_stdout(StringIO()):
                exit_code = tomap_builder.build_tomap(
                    data_dir=data_dir,
                    maps_dir=maps_dir,
                    last_rains_history=3,
                    minimum_rain_tomap=0,
                    max_threads=1,
                )

            self.assertEqual(exit_code, 0)
            last_day = pd.read_csv(maps_dir / '01_Tomap_Last_day.csv')
            by_station = last_day.set_index('Codi Estació')
            self.assertTrue(pd.isna(by_station.loc['NO_RAIN_DATA', 'Total']))
            self.assertEqual(by_station.loc['ZERO_RAIN', 'Total'], 0.0)
            self.assertEqual(by_station.loc['RAINY', 'Total'], 2.4)

    def test_build_tomap_ignores_aemet_by_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / 'Data'
            maps_dir = tmp_path / 'Tomap'
            data_dir.mkdir()

            today = date.today()
            pd.DataFrame([make_incremental_row('AEMET:9632X', today, 6.4)]).to_csv(
                data_dir / 'Aemet_incremental.csv',
                decimal=',',
                index=False,
            )
            generate_parquet(data_dir)

            with redirect_stdout(StringIO()):
                exit_code = tomap_builder.build_tomap(
                    data_dir=data_dir,
                    maps_dir=maps_dir,
                    last_rains_history=3,
                    minimum_rain_tomap=0,
                    max_threads=1,
                )

            self.assertEqual(exit_code, 1)
            self.assertEqual(list(maps_dir.glob('*.csv')), [])


if __name__ == '__main__':
    unittest.main()
