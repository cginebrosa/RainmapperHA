"""Map-only hydrology invariants; never change the existing ML water contract."""
import json
import unittest
from datetime import date, timedelta

from rainmapper_core import mushroom_map_hydrology as water
from rainmapper_core.mushroom_map_water_physics import simulate_reference_store, penman_monteith, wind_at_two_metres
from rainmapper_core.mushroom_climatic_water_balance import hargreaves_reference_evapotranspiration_mm


class HydrologyTests(unittest.TestCase):
    def series(self, n=365, rain=0., low=10., high=20.):
        return dict(daily_dates=[(date(2025,9,19)+timedelta(days=i)).isoformat() for i in range(n)],
                    daily_rain_idw_mm=[rain]*n, daily_temp_min_idw_c=[low]*n,
                    daily_temp_max_idw_c=[high]*n)

    def test_signed_balance_shared_equation_and_no_soil_still_shows_balance(self):
        source=self.series(7,rain=10)
        result=water.build_history(source,42,7)
        expected=10-hargreaves_reference_evapotranspiration_mm(date(2025,9,19),42,10,20)
        self.assertAlmostEqual(result['balance_mm'][0],expected)
        self.assertEqual(result['smi_pct'],[None]*7)
        self.assertEqual(set(result['smi_reasons']),{'soil_unavailable'})
        self.assertTrue(all(v<0 for v in water.build_history(self.series(7),42,7)['balance_mm']))

    def test_dry_and_wet_limits_and_tiny_rain_continuity(self):
        self.assertTrue(all(v is not None and v < .01 for v in water.build_history(self.series(),42,60,60)['smi_pct']))
        self.assertTrue(all(90 < v <= 100 for v in water.build_history(self.series(rain=20),42,60,60)['smi_pct']))
        source=self.series(rain=20)
        source['daily_rain_idw_mm'][-5:]=[0.]*5
        before=water.build_history(source,42,60,60)
        source['daily_rain_idw_mm'][-1]=.01
        after=water.build_history(source,42,60,60)
        self.assertGreater(after['smi_pct'][-1],before['smi_pct'][-1])
        self.assertLessEqual(after['smi_pct'][-1]-before['smi_pct'][-1],100*.01/60+.001)

    def test_final_convergence_does_not_validate_earlier_days(self):
        source=self.series(120,low=0.,high=0.)  # zero demand, initial state persists
        source['daily_rain_idw_mm'][-1]=100.
        result=water.build_history(source,42,60,60)
        self.assertEqual(result['smi_pct'][:-1],[None]*59)
        self.assertEqual(result['smi_pct'][-1],100.)
        self.assertIn('not_converged',result['smi_reasons'])
        self.assertIn('spinup_incomplete',result['smi_reasons'])

    def test_gap_and_invalid_temperature_reset_unknown_state(self):
        for field,value in [('daily_rain_idw_mm',None),('daily_temp_min_idw_c',None),
                            ('daily_temp_min_idw_c',30.),('daily_rain_idw_mm',-1.)]:
            with self.subTest(field=field,value=value):
                source=self.series(rain=20)
                source[field][-4]=value
                result=water.build_history(source,42,7,60)
                self.assertTrue(all(v is not None for v in result['smi_pct'][:3]))
                self.assertEqual(result['smi_pct'][3:],[None]*4)
                self.assertIsNone(result['balance_mm'][-4])
                self.assertEqual(result['smi_reasons'][-4],'inputs_incomplete')

    def test_display_windows_do_not_reset_storage_and_payload_is_small(self):
        source=self.series(rain=4)
        result=water.build_history(source,42,60,60)
        self.assertLess(len(json.dumps(result).encode()),8192)
        for days in (7,15,30,60):
            short=water.build_history(source,42,days,60)
            for field in ('smi_pct','smi_legacy_pct','balance_mm','smi_low_pct','smi_high_pct'):
                self.assertEqual(short[field],result[field][-days:])
            self.assertEqual(short['history_start'],result['history_start'])

    def test_fifty_mm_eight_days_ago_is_retained_in_seven_day_chart(self):
        source=self.series()
        source['daily_rain_idw_mm'][-9]=50.
        wet=water.build_history(source,42,7,60)
        source['daily_rain_idw_mm'][-9]=0.
        dry=water.build_history(source,42,7,60)
        self.assertGreater(wet['smi_pct'][-1],dry['smi_pct'][-1]+10)
        self.assertTrue(all(v<0 for v in wet['balance_mm']))

    def test_penman_uses_humidity_and_marks_estimated_wind_and_fallback(self):
        source=self.series()
        source.update(daily_humidity_min_idw_pct=[40.]*365,daily_humidity_max_idw_pct=[90.]*365)
        result=water.build_history(source,42,7,60,altitude_m=1750)
        self.assertEqual(result['et0_methods'],['pm_estimated_wind']*7)
        source['daily_humidity_min_idw_pct'][-1]=None
        changed=water.build_history(source,42,7,60,altitude_m=1750,wind_u2_m_s=[1.]*365)
        self.assertEqual(changed['et0_methods'],['pm_station_wind']*6+['hargreaves'])
        for low,mid,high in zip(result['smi_low_pct'],result['smi_pct'],result['smi_high_pct']):
            self.assertLessEqual(low,mid)
            self.assertLessEqual(mid,high)

    def test_fao_published_uccle_daily_example(self):
        # FAO-56 ch.4 example 18: independently published ET0=3.88 mm/day.
        u2=wind_at_two_metres(10,10)
        self.assertAlmostEqual(u2,2.078,delta=.003)
        value=penman_monteith(date(2001,7,6),50.8,100,12.3,21.5,63,84,u2,solar_mj=22.07)
        self.assertAlmostEqual(value,3.88,delta=.02)

    def test_penman_response_to_humidity_and_wind(self):
        args=(date(2026,9,4),42.19974,1754.3,13.1,27.5)
        dry=penman_monteith(*args,32,84.2,1.)
        humid=penman_monteith(*args,70,95,1.)
        windy=penman_monteith(*args,32,84.2,4.)
        self.assertLess(humid,dry)
        self.assertGreater(windy,dry)

    def test_storage_mass_conservation_and_reducing_extraction(self):
        run=simulate_reference_store([0.]*40,[4.]*40,60,20)
        self.assertGreater(run['storage_mm'][4],0) # old constant-loss store empty on day 5
        losses=[e+t for e,t in zip(run['evaporation_mm'],run['transpiration_mm'])]
        self.assertTrue(all(a>b for a,b in zip(losses,losses[1:])))
        self.assertLess(run['mass_error_max_mm'],1e-10)
        for share in (0,.5,1):
            run=simulate_reference_store([200.,0.,.01],[4.,100.,4.],60,30,evaporation_share=share)
            self.assertLess(run['mass_error_max_mm'],1e-10)
            self.assertTrue(all(0<=v<=60 for v in run['storage_mm']))

    def test_analytic_integration_matches_independent_small_time_steps(self):
        # Numerical ODE integration, independent of the analytical solution.
        for share in (0,.5,1):
            s=55.; e_total=t_total=0.; step=1/100000
            for _ in range(100000):
                e=100*share*s/60*step
                t=100*(1-share)*min(1,s/30)*step
                s-=e+t; e_total+=e; t_total+=t
            run=simulate_reference_store([0.],[100.],60,55.,evaporation_share=share)
            self.assertAlmostEqual(run['storage_mm'][0],s,delta=.001)
            self.assertAlmostEqual(run['evaporation_mm'][0],e_total,delta=.001)
            self.assertAlmostEqual(run['transpiration_mm'][0],t_total,delta=.001)

    def test_resource_bounds(self):
        with self.assertRaisesRegex(ValueError,'hydrology_history_limit'):
            water.build_history(self.series(366),42,60,60)
        with self.assertRaisesRegex(ValueError,'hydrology_history_limit'):
            water.build_history(self.series(),42,61,60)
        for value in (True,0,-1,301,float('nan'),float('inf'),'60'):
            self.assertFalse(water.valid_capacity(value))

    def test_comparison_reuses_operational_bucket_with_original_hargreaves(self):
        from rainmapper_core.mushroom_soil_water_state import simulate_bounded_bucket
        source=self.series(rain=2)
        source.update(daily_humidity_min_idw_pct=[40.]*365,daily_humidity_max_idw_pct=[90.]*365)
        result=water.build_history(source,42,60,60,altitude_m=1750)
        eto=[hargreaves_reference_evapotranspiration_mm(date.fromisoformat(day),42,10,20) for day in source['daily_dates']]
        original=simulate_bounded_bucket(rain_mm=source['daily_rain_idw_mm'],reference_evapotranspiration_mm=eto,capacity_mm=60,initial_storage_mm=0)
        self.assertEqual(result['smi_legacy_pct'],[round(100*v/60,3) for v in original['storage_mm'][-60:]])
        self.assertNotEqual(result['smi_pct'],result['smi_legacy_pct'])
        source['daily_rain_idw_mm'][-3]=None
        result=water.build_history(source,42,7,60,altitude_m=1750)
        self.assertEqual(result['smi_legacy_pct'][-3:],[None]*3)
