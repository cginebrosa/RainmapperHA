import math
import random
import unittest
from simple_layers import simulate,history


class SimpleLayersTests(unittest.TestCase):
    def test_demand_consumed_until_empty(self):
        # C1=20, C2=40; E1=3,T1=1,T2=2 with demand 6.
        r=simulate([0.,0.],[6.,6.],60.,1.)
        self.assertEqual(r['upper'],[16.,12.])
        self.assertEqual(r['lower'],[38.,36.])
        self.assertEqual(r['total'],[54.,48.])
        r=simulate([0.],[1000.],60.,1.)
        self.assertEqual(r['total'],[0.])

    def test_fill_and_spill(self):
        r=simulate([10.,40.,100.],[0.]*3,60.,0.)
        self.assertEqual(r['upper'],[10.,20.,20.])
        self.assertEqual(r['lower'],[0.,30.,40.])
        self.assertEqual(r['drainage'],[0.,0.,90.])

    def test_mass_and_tiny_input_change(self):
        rng=random.Random(8)
        rain=[rng.choice([0.,0.,rng.uniform(0,80)]) for _ in range(365)]
        changed=rain.copy();changed[100]+=.01
        et=[rng.uniform(0,8) for _ in rain]
        for two in (False,True):
            a=simulate(rain,et,47.1,.5,two);b=simulate(changed,et,47.1,.5,two)
            self.assertLess(a['mass_error_max_mm'],1e-8)
            self.assertLess(b['mass_error_max_mm'],1e-8)
            for x,y in zip(a['total'],b['total']):
                self.assertGreaterEqual(y-x,-1e-9)
                self.assertLessEqual(y-x,.01000001)

    def test_history_gap_and_initial_uncertainty(self):
        r=history([0.]*365,[0.]*365,60.)
        self.assertTrue(all(math.isnan(v) for v in r['total']))
        rain=[0.]*365;rain[-9]=50.
        r=history(rain,[2.]*365,60.)
        self.assertGreater(r['total'][-1],0.)
        rain[-3]=None;r=history(rain,[2.]*365,60.)
        self.assertTrue(all(math.isnan(v) for v in r['total'][-3:]))


if __name__=='__main__':unittest.main()
