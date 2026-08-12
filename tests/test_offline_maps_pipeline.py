import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd

from rainmapper_core.incremental_upsert import upsert_incremental
from rainmapper_core import geojson as tomap_to_geojson
from rainmapper_core import mushroom_observation_context
from rainmapper_core import tomap as tomap_builder


def make_incremental_row(station_code, reading_date, rain, max_temp=20.0):
    """Create one Rainmapper-like incremental row for offline pipeline tests."""
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
        'max_temp_celsius': max_temp,
        'min_temp_celsius': 12.0,
        'max_humidity_percent': 80.0,
        'min_humidity_percent': 45.0,
    }


class OfflineMapsPipelineTests(unittest.TestCase):
    def test_incremental_upsert_tomap_builder_and_geojson_work_together(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            data_dir = tmp_path / 'Data'
            maps_dir = tmp_path / 'Tomap'
            public_data_dir = tmp_path / 'PublicData'
            ignore_file = tmp_path / 'ignore_stations_tomap.txt'
            data_dir.mkdir()

            today = date.today()
            yesterday = today - timedelta(days=1)

            # Simulate a Meteocat correction for an existing station/day: new rain
            # should win, while a missing new temperature should preserve the old value.
            meteocat_old = pd.DataFrame([
                make_incremental_row('Z1', today, 0.0, max_temp=24.0),
            ])
            meteocat_current = pd.DataFrame([
                make_incremental_row('Z1', today, 5.5, max_temp=pd.NA),
            ])
            meteocat_incremental = upsert_incremental(meteocat_current, meteocat_old)

            self.assertEqual(len(meteocat_incremental), 1)
            self.assertEqual(meteocat_incremental.iloc[0]['Total'], 5.5)
            self.assertEqual(meteocat_incremental.iloc[0]['max_temp_celsius'], 24.0)

            meteocat_incremental.to_csv(
                data_dir / 'Meteocat_incremental.csv',
                decimal=',',
                index=False,
            )
            pd.DataFrame([
                make_incremental_row('ESCAT2500000025720B', today, 8.2, max_temp=18.0),
            ]).to_csv(data_dir / 'Meteoclimatic_incremental.csv', decimal=',', index=False)
            pd.DataFrame([
                make_incremental_row('IGUILS3', yesterday, 1.1, max_temp=16.0),
            ]).to_csv(data_dir / 'Wunderground_incremental.csv', decimal=',', index=False)
            ignore_file.write_text('', encoding='utf-8')
            mushroom_observation_context.generate_weather_daily_parquet(data_dir)

            with redirect_stdout(StringIO()):
                build_exit_code = tomap_builder.build_tomap(
                    data_dir=data_dir,
                    maps_dir=maps_dir,
                    last_rains_history=3,
                    minimum_rain_tomap=0,
                    max_threads=1,
                )
                converted_files = tomap_to_geojson.convert_all(
                    maps_dir,
                    public_data_dir,
                    ignore_file,
                )

            self.assertEqual(build_exit_code, 0)
            self.assertEqual(len(converted_files), 7)

            last_day = pd.read_csv(maps_dir / '01_Tomap_Last_day.csv')
            z1_row = last_day[last_day['Codi Estació'] == 'Z1'].iloc[0]
            self.assertEqual(z1_row['Total'], 5.5)
            self.assertEqual(z1_row['Temp_Max_01'], 24.0)
            self.assertEqual(z1_row['Data_Pluja_01'], today.strftime('%d/%m/%Y'))
            self.assertEqual(z1_row['Pluja_Diaria_01'], 5.5)
            self.assertNotIn('Data_Pluja_04', last_day.columns)

            day_geojson = json.loads((public_data_dir / '01d.geojson').read_text(encoding='utf-8'))
            day_features = {
                feature['properties']['Codi Estació']: feature
                for feature in day_geojson['features']
            }
            self.assertEqual(day_features['Z1']['properties']['Source'], 'Meteocat')
            self.assertEqual(day_features['ESCAT2500000025720B']['properties']['Source'], 'Meteoclimatic')
            self.assertNotIn('IGUILS3', day_features)

            week_geojson = json.loads((public_data_dir / '07d.geojson').read_text(encoding='utf-8'))
            week_features = {
                feature['properties']['Codi Estació']: feature
                for feature in week_geojson['features']
            }
            self.assertEqual(week_features['IGUILS3']['properties']['Source'], 'Wunderground')


if __name__ == '__main__':
    unittest.main()
