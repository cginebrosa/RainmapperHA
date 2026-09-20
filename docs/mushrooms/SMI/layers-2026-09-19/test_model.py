"""Physical and history-contract tests for the audit prototype only."""
import math
import random
import unittest
from model import run, history, SCENARIOS, simulate_reference_store


class LayersTests(unittest.TestCase):
    def test_distributed_control_reproduces_single_store(self):
        rng = random.Random(41)
        rain = [rng.choice([0., 0., rng.uniform(0, 100)]) for _ in range(365)]
        demand = [rng.uniform(0, 8) for _ in rain]
        for capacity in (5., 47.1, 150.):
            for initial in (0., .37, 1.):
                ref = simulate_reference_store(rain, demand, capacity, initial*capacity)
                got = run(rain, demand, capacity, initial, **SCENARIOS['control'])
                for a, b in zip(ref['storage_mm'], got['total']):
                    self.assertAlmostEqual(a, b, places=9)

    def test_antecedent_storage_controls_recharge(self):
        # C1=20 mm: 10 mm stays above in dry profile, reaches below when top is full.
        dry = run([10.], [0.], 60., 0.)
        self.assertEqual(dry['upper'], [10.])
        self.assertEqual(dry['lower'], [0.])
        wet = run([10.], [0.], 60., 1.)
        self.assertEqual(wet['transfer'], [10.])
        self.assertEqual(wet['drainage'], [10.])
        big = run([50.], [0.], 60., 0.)
        self.assertEqual(big['lower'], [30.])

    def test_bypass_is_explicit_and_conservative(self):
        got = run([10.], [0.], 60., 0., bypass=.25)
        self.assertEqual(got['upper'], [7.5])
        self.assertEqual(got['lower'], [2.5])
        self.assertEqual(got['total'], [10.])

    def test_mass_bounds_and_no_water_creation(self):
        rng = random.Random(732)
        rain = [rng.uniform(0, 130) if rng.random()<.2 else 0. for _ in range(365)]
        et = [rng.uniform(0, 12) for _ in rain]
        for cfg in SCENARIOS.values():
            got = run(rain, et, 47.1, .42, **cfg)
            self.assertLess(got['mass_error_max_mm'], 1e-8)
            self.assertLess(got['cumulative_mass_error_mm'], 1e-8)
            self.assertTrue(all(0 <= x <= 47.1 for x in got['total']))
            self.assertTrue(all(e+t <= d+1e-9 for e,t,d in zip(got['evaporation'],got['transpiration'],et)))
            empty = run([0.]*3, [10.]*3, 47.1, 0., **cfg)
            self.assertEqual(empty['total'], [0.]*3)

    def test_history_keeps_rain_outside_chart_and_marks_gaps(self):
        rain = [0.]*365
        rain[-9] = 50.
        full = history(rain, [2.]*365, 60., 'surface')
        self.assertGreater(full['total'][-7], 0.)
        no_event = history([0.]*365, [2.]*365, 60., 'surface')
        self.assertGreater(full['total'][-1], no_event['total'][-1]+1.)
        restarted = history(rain[-7:], [2.]*7, 60., 'surface')
        self.assertTrue(all(math.isnan(v) for v in restarted['total']))
        rain[-5] = None
        gap = history(rain, [2.]*365, 60., 'surface')
        self.assertTrue(all(math.isnan(v) for v in gap['total'][-5:]))

    def test_initial_uncertainty_is_not_false_precision(self):
        result = history([0.]*365, [0.]*365, 60., 'surface')
        self.assertTrue(all(math.isnan(v) for v in result['total']))
        with self.assertRaises(ValueError):
            run([-1.], [1.], 60., 0.)

    def test_tiny_rain_perturbation_cannot_create_large_water_jump(self):
        rain = [0., 5., 10., 0., 40., 0., 0., 8.]*15
        perturbed = list(rain);perturbed[17] += .01
        for cfg in SCENARIOS.values():
            a = run(rain, [4.3]*len(rain), 47.1, .4, **cfg)
            b = run(perturbed, [4.3]*len(rain), 47.1, .4, **cfg)
            for x,y in zip(a['total'], b['total']):
                self.assertGreaterEqual(y-x, -1e-9)
                self.assertLessEqual(y-x, .010000001)


if __name__ == '__main__':
    unittest.main()
