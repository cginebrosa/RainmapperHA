import unittest

import pandas as pd

from rainmapper_core.meteocat_daily import combine_meteocat_daily_rows


class MeteocatDailyTests(unittest.TestCase):
    def test_condition_only_day_is_preserved_without_fabricating_zero_rain(self):
        rain = pd.DataFrame(
            [
                {
                    "Codi Estació": "CR",
                    "Data Lectura": pd.Timestamp("2020-08-12 02:00:01"),
                    "Data Local": "20200812",
                    "Total": 14.9,
                    "Variable": "Precipitació",
                    "Unitat": "mm",
                }
            ]
        )
        conditions = pd.DataFrame(
            [
                {
                    "Codi Estació": "CR",
                    "Data Lectura": pd.Timestamp("2020-08-11 02:00:01"),
                    "max_temp_celsius": 33.8,
                    "min_temp_celsius": 18.4,
                    "max_humidity_percent": 70.0,
                    "min_humidity_percent": 29.0,
                },
                {
                    "Codi Estació": "CR",
                    "Data Lectura": pd.Timestamp("2020-08-12 02:00:01"),
                    "max_temp_celsius": 29.0,
                    "min_temp_celsius": 15.0,
                    "max_humidity_percent": 100.0,
                    "min_humidity_percent": 41.0,
                },
            ]
        )

        result = combine_meteocat_daily_rows(rain, conditions)

        self.assertEqual(result["Data Local"].tolist(), ["20200812", "20200811"])
        dry_unknown = result[result["Data Local"] == "20200811"].iloc[0]
        self.assertTrue(pd.isna(dry_unknown["Total"]))
        self.assertEqual(dry_unknown["max_humidity_percent"], 70.0)
        rainy = result[result["Data Local"] == "20200812"].iloc[0]
        self.assertEqual(rainy["Total"], 14.9)
        self.assertEqual(rainy["min_humidity_percent"], 41.0)

    def test_observed_zero_rain_is_preserved(self):
        rain = pd.DataFrame(
            [{"Codi Estació": "CR", "Data Lectura": "2020-08-13", "Total": 0.0}]
        )
        conditions = pd.DataFrame(
            [{"Codi Estació": "CR", "Data Lectura": "2020-08-13", "max_humidity_percent": 100.0}]
        )

        result = combine_meteocat_daily_rows(rain, conditions)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Total"], 0.0)


class MeteocatQueryBoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Importing the legacy runner would execute jobs. Compile its actual
        # query functions alone, as the existing runner tests do.
        import ast
        from pathlib import Path
        from rainmapper_core.meteocat_daily import meteocat_daily_query_bounds
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'rainmapper_core/rainmapper.py').read_text())
        names = {'get_myquery', 'get_myquery_rain_all', 'get_myquery_conditions_all', 'get_myquery_daily_wind_all'}
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        assert len(functions) == 4
        cls.namespace = {'meteocat_daily_query_bounds': meteocat_daily_query_bounds}
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<runner-query-functions>', 'exec'), cls.namespace)

    def query(self, start, end, name='get_myquery_rain_all'):
        args = ['YB', "'35'", "'35'", start, end] if name in ('get_myquery', 'get_myquery_rain_all') else ['YB', start, end]
        return self.namespace[name](*args)

    def test_all_runner_queries_use_whole_utc_days_for_requested_dates(self):
        for name in ('get_myquery', 'get_myquery_rain_all', 'get_myquery_conditions_all', 'get_myquery_daily_wind_all'):
            with self.subTest(name=name):
                query = self.query('2026-09-18T22:00:00', '2026-09-26T21:59:00', name)
                self.assertIn("BETWEEN '2026-09-19T00:00:00' AND '2026-09-26T23:59:59.999'", query)
                self.assertNotIn('2026-09-18', query)

    def test_winter_dst_changes_and_year_boundary_keep_calendar_labels(self):
        from rainmapper_core.meteocat_daily import meteocat_daily_query_bounds
        cases = [
            ('2026-01-01T23:00:00', '2026-01-02T22:59:00', '2026-01-02', '2026-01-02'),
            ('2026-03-28T23:00:00', '2026-03-29T21:59:00', '2026-03-29', '2026-03-29'),
            ('2026-10-24T22:00:00', '2026-10-25T22:59:00', '2026-10-25', '2026-10-25'),
            ('2025-12-31T23:00:00', '2026-01-01T22:59:00', '2026-01-01', '2026-01-01'),
        ]
        for start, end, first, last in cases:
            with self.subTest(start=start):
                self.assertEqual(meteocat_daily_query_bounds(start, end), (first+'T00:00:00', last+'T23:59:59.999'))
        with self.assertRaises(ValueError):
            meteocat_daily_query_bounds('2026-09-20T00:00:00', '2026-09-18T00:00:00')

    def test_partial_first_day_cannot_overwrite_existing_rain_or_conditions(self):
        import re
        from rainmapper_core.incremental_upsert import upsert_incremental
        # The old query starting 09/09 22:00 would overwrite 54.8 with zero.
        # Exercise the actual query predicate and station/day upsert together.
        old = pd.DataFrame([{'Codi Estació': 'YB', 'Data Local': '20260909', 'Total': 54.8,
                             'max_temp_celsius': 20.9}])
        samples = pd.DataFrame([
            {'time': '2026-09-09T14:00:00', 'rain': 54.8, 'temp': 20.9},
            {'time': '2026-09-09T22:00:00', 'rain': 0., 'temp': 13.6},
            {'time': '2026-09-10T12:00:00', 'rain': 2., 'temp': 25.8},
        ])
        query = self.query('2026-09-09T22:00:00', '2026-09-10T21:59:00')
        start, end = re.search(r"BETWEEN '([^']+)' AND '([^']+)'", query).groups()
        selected = samples[(samples.time >= start) & (samples.time <= end)].copy()
        selected['Data Local'] = selected.time.str[:10].str.replace('-', '')
        fresh = selected.groupby('Data Local').agg(Total=('rain', 'sum'), max_temp_celsius=('temp', 'max')).reset_index()
        fresh['Codi Estació'] = 'YB'
        saved = upsert_incremental(fresh, old).set_index('Data Local')
        self.assertEqual(saved.loc['20260909', 'Total'], 54.8)
        self.assertEqual(saved.loc['20260909', 'max_temp_celsius'], 20.9)
        self.assertEqual(saved.loc['20260910', 'Total'], 2.)

    def test_full_day_correction_can_reduce_rain_to_zero(self):
        from rainmapper_core.incremental_upsert import upsert_incremental
        old = pd.DataFrame([{'Codi Estació': 'YB', 'Data Local': '20260909', 'Total': 54.8}])
        corrected = old.copy(); corrected['Total'] = 0.
        self.assertEqual(upsert_incremental(corrected, old).iloc[0]['Total'], 0.)


if __name__ == "__main__":
    unittest.main()
