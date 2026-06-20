import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd

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
    }


class TomapBuilderTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
