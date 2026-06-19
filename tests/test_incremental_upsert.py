import unittest

import pandas as pd

from incremental_upsert import upsert_incremental


def row(station, local_date, rain, max_temp=None, station_name=None):
    return {
        'Codi Estació': station,
        'Data Local': local_date,
        'Total': rain,
        'max_temp_celsius': max_temp,
        'Estació': station_name or f'Station {station}',
    }


class IncrementalUpsertTests(unittest.TestCase):
    def test_new_non_null_values_win_and_new_nan_keeps_old_value(self):
        old = pd.DataFrame([
            row('AA', '20260619', 0.0, max_temp=18.2, station_name='Old name'),
        ])
        current = pd.DataFrame([
            row('AA', '20260619', 4.6, max_temp=pd.NA, station_name='New name'),
        ])

        result = upsert_incremental(current, old)

        self.assertEqual(len(result), 1)
        result_row = result.iloc[0]
        self.assertEqual(result_row['Total'], 4.6)
        self.assertEqual(result_row['max_temp_celsius'], 18.2)
        self.assertEqual(result_row['Estació'], 'New name')

    def test_new_keys_are_appended(self):
        old = pd.DataFrame([
            row('AA', '20260618', 1.0, max_temp=18.2),
        ])
        current = pd.DataFrame([
            row('BB', '20260619', 2.5, max_temp=20.0),
        ])

        result = upsert_incremental(current, old)

        self.assertEqual(set(zip(result['Codi Estació'], result['Data Local'])), {
            ('AA', '20260618'),
            ('BB', '20260619'),
        })

    def test_existing_duplicate_keys_are_collapsed_with_non_null_fallback(self):
        old = pd.DataFrame([
            row('AA', '20260619', 0.0, max_temp=18.2),
            row('AA', '20260619', 0.0, max_temp=pd.NA),
        ])
        current = pd.DataFrame([
            row('AA', '20260619', 0.0, max_temp=pd.NA),
        ])

        result = upsert_incremental(current, old)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['max_temp_celsius'], 18.2)


if __name__ == '__main__':
    unittest.main()
