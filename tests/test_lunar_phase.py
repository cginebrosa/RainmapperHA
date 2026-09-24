"""Independent event dates, timezone conventions and bad input handling."""
from datetime import date, datetime, timezone
import json
import unittest

from rainmapper_core.lunar_phase import lunar_phase


class LunarPhaseTests(unittest.TestCase):
    def test_usno_primary_phases(self):
        # Independent reference, UT (not outputs copied from this function):
        # https://aa.usno.navy.mil/calculated/moon/phases?date=2025-09-01&format=p&nump=5&submit=Get+Data
        for instant, category, fraction, cycle in (
            ('2025-09-07T18:09:00Z', 'full', 1, .5),
            ('2025-09-14T10:33:00Z', 'waning', .5, .75),
            ('2025-09-21T19:54:00Z', 'new', 0, 0),
            ('2025-09-29T23:54:00Z', 'waxing', .5, .25),
        ):
            with self.subTest(instant=instant):
                result = lunar_phase(instant)
                self.assertEqual(result['category'], category)
                self.assertAlmostEqual(result['illuminated_fraction'], fraction, delta=.02)
                difference = abs(result['phase_cycle'] - cycle)
                self.assertLess(min(difference, 1 - difference), .01)

    def test_date_and_timezone_conventions(self):
        expected = lunar_phase('2025-09-04')
        for value in (date(2025, 9, 4), datetime(2025, 9, 4, 12, tzinfo=timezone.utc),
                      '2025-09-04T14:00:00+02:00', '2025-09-05T02:00:00+14:00'):
            self.assertEqual(lunar_phase(value), expected)
        self.assertEqual(expected['reference_time'], '2025-09-04T12:00:00+00:00')
        self.assertEqual(expected['category'], 'waxing')
        self.assertNotEqual(lunar_phase('2025-09-04T00:00:00Z'), expected)

    def test_bad_dates_never_default_to_today(self):
        for value in ('', 'not-a-date', '2025-02-30', '2025-09-04junk', '20250904',
                      '2025-09-04T12:00:00', datetime(2025, 9, 4)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                lunar_phase(value)
        for value in (None, True, 0, []):
            with self.subTest(value=value), self.assertRaises(TypeError):
                lunar_phase(value)

    def test_numeric_contract_and_distinct_half_cycles(self):
        for year in (1900, 2000, 2025, 2030, 2100):
            for month in (1, 2, 6, 12):
                result = lunar_phase(date(year, month, 15))
                for key in ('illuminated_fraction', 'phase_cycle'):
                    self.assertGreaterEqual(result[key], 0)
                    self.assertLessEqual(result[key], 1)
                self.assertEqual(result['waxing'], result['phase_cycle'] < .5)
                json.dumps(result, allow_nan=False)
        self.assertNotEqual(lunar_phase('2025-09-14')['waxing'], lunar_phase('2025-09-29')['waxing'])
        self.assertEqual(lunar_phase('2000-02-29')['reference_time'][:10], '2000-02-29')
