import unittest
from audit import daily, episodes, integrate, interval_delta, PROFILES


class StorageAuditTests(unittest.TestCase):
    def test_uniform_profile_and_change(self):
        a = dict(VWC_005=.2, VWC_020=.2, VWC_050=.2)
        b = {k: v+.03 for k, v in a.items()}
        for profile in PROFILES:
            self.assertAlmostEqual(integrate(a, profile), 60)
            self.assertAlmostEqual(integrate(b, profile)-integrate(a, profile), 9)

    def test_linear_depth_integration(self):
        # Constant 0–5 cm (0.1), then theta=2*z (z in metres) to 30 cm.
        self.assertAlmostEqual(integrate(dict(VWC_005=.1, VWC_020=.4, VWC_050=1.), 'linear_5_20_50'), 92.5)
        self.assertIsNone(integrate(dict(VWC_005=.1, VWC_020=.4), 'linear_5_20_50'))

    def test_end_day_does_not_invent_last_measurement(self):
        rows = [dict(TmStamp=f'2026-08-01T{h:02}:{m:02}:00', VWC_005=.2, Pluja_Tot=0)
                for h in range(24) for m in (0, 30)]
        out, _ = daily(rows, ['2026-08-01'])
        self.assertEqual(out[0]['end']['VWC_005'], .2)
        out, _ = daily(rows[:-1], ['2026-08-01'])
        self.assertIsNone(out[0]['end']['VWC_005'])
        self.assertAlmostEqual(out[0]['mean']['VWC_005'], .2)
        self.assertIsNone(out[0]['gauge'])
        with self.assertRaises(ValueError):
            daily(rows+[rows[0]], ['2026-08-01'])

    def test_does_not_bridge_missing_days(self):
        self.assertIsNone(interval_delta([1, None, 3], 0, 2))
        self.assertEqual(interval_delta([1, 2, 3], 0, 2), 2)

    def test_episode_grouping_and_boundaries(self):
        good, _ = episodes([0, 0, 10, 0, 8, 0, 0, 0, 0])
        self.assertEqual(good, [(2, 4, None)])
        good, bad = episodes([10, 0, 0, 0, 0])
        self.assertFalse(good)
        self.assertEqual(bad[0][2], 'window_outside_period')


if __name__ == '__main__':
    unittest.main()
