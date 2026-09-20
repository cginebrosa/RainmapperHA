"""Map presentation of shared water history, independent of display window."""
from datetime import date
import math

from rainmapper_core.mushroom_climatic_water_balance import hargreaves_reference_evapotranspiration_mm
from rainmapper_core.mushroom_soil_water_state import (
    CONVERGENCE_ABSOLUTE_MM,
    CONVERGENCE_CAPACITY_FRACTION, SPINUP_CANDIDATES_DAYS, simulate_bounded_bucket,
)
from rainmapper_core.mushroom_water_physics import (finite, simulate_reference_store,
    reference_et_series, regulated_history, WATER_STATE_CONTRACT_ID)

MAX_HISTORY_DAYS = 365
MAX_CHART_DAYS = 60


def valid_capacity(value):
    # Retention inputs are <=1000 mm/m and this profile is exactly 0.3 m.
    return (type(value) in (int, float) and math.isfinite(value)
            and 0 < value <= 300)


def build_history(interpolated, latitude, days, capacity_mm=None, *, altitude_m=None, wind_u2_m_s=None):
    dates = interpolated['daily_dates']
    if not 1 <= days <= MAX_CHART_DAYS or not days <= len(dates) <= MAX_HISTORY_DAYS:
        raise ValueError('hydrology_history_limit')
    rain = interpolated['daily_rain_idw_mm']
    low = interpolated['daily_temp_min_idw_c']
    high = interpolated['daily_temp_max_idw_c']
    if any(len(values) != len(dates) for values in (rain, low, high)):
        raise ValueError('hydrology_series_mismatch')
    parsed = [date.fromisoformat(day) for day in dates]
    if any((b-a).days != 1 for a,b in zip(parsed,parsed[1:])):
        raise ValueError('hydrology_dates_not_consecutive')
    reference = reference_et_series(interpolated,latitude,altitude_m=altitude_m,wind_u2_m_s=wind_u2_m_s)
    eto, methods = reference['et0_mm'], reference['et0_methods']
    legacy_eto = [hargreaves_reference_evapotranspiration_mm(day,latitude,lo,hi)
                  if finite(lo) and finite(hi) and -80 <= lo <= hi <= 60 else None
                  for day,lo,hi in zip(parsed,low,high)]
    balance = [round(p-e, 6) if finite(p) and p >= 0 and e is not None else None
               for p, e in zip(rain, eto)]
    smi = [None] * len(dates)
    legacy_smi = [None] * len(dates)
    lower_smi, upper_smi = [None]*len(dates), [None]*len(dates)
    reasons = ['soil_unavailable' if not valid_capacity(capacity_mm) else 'inputs_incomplete'] * len(dates)
    if valid_capacity(capacity_mm):
        shared = regulated_history(rain,eto,capacity_mm)
        smi = [round(100*v/capacity_mm,3) if v is not None else None for v in shared["storage_mm"]]
        reasons = shared["reasons"]
        # Missing weather starts a new unknown initial state; never assume zero.
        start = 0
        while start < len(dates):
            if balance[start] is None:
                start += 1
                continue
            end = start
            while end < len(dates) and balance[end] is not None:
                end += 1
            args = dict(rain=rain[start:end], demand=eto[start:end], capacity=capacity_mm)
            dry = simulate_reference_store(**args, initial=0)['storage_mm']
            wet = simulate_reference_store(**args, initial=capacity_mm)['storage_mm']
            # Retain the former simple bucket, with its original ET0, for comparison.
            # This is a point-method comparison, not a persisted ML feature.
            old_args = dict(rain_mm=rain[start:end], reference_evapotranspiration_mm=legacy_eto[start:end], capacity_mm=capacity_mm)
            old_dry = simulate_bounded_bucket(**old_args, initial_storage_mm=0)['storage_mm']
            old_wet = simulate_bounded_bucket(**old_args, initial_storage_mm=capacity_mm)['storage_mm']
            # Sensitivity, not a confidence interval or an inferred canopy mix.
            scenarios = []
            for share in (0., .5, 1.):
                for depletion in (.3, .5, .7):
                    options = dict(evaporation_share=share, depletion_fraction=depletion)
                    if share == .5 and depletion == .5:
                        scenarios.append((dry,wet))
                    else:
                        scenarios.append((simulate_reference_store(**args,initial=0,**options)['storage_mm'],
                                          simulate_reference_store(**args,initial=capacity_mm,**options)['storage_mm']))
            limit = max(CONVERGENCE_ABSOLUTE_MM, capacity_mm * CONVERGENCE_CAPACITY_FRACTION)
            for offset, (lower, upper) in enumerate(zip(dry, wet)):
                i = start + offset
                if offset + 1 >= min(SPINUP_CANDIDATES_DAYS) and old_wet[offset] - old_dry[offset] <= limit:
                    legacy_smi[i] = round(100 * old_dry[offset] / capacity_mm, 3)
                if offset + 1 < min(SPINUP_CANDIDATES_DAYS):
                    reasons[i] = 'spinup_incomplete'
                elif upper - lower > limit:
                    reasons[i] = 'not_converged'
                else:
                    if all(w[offset]-d[offset] <= limit for d,w in scenarios):
                        lower_smi[i] = round(100*min(d[offset] for d,w in scenarios)/capacity_mm,3)
                        upper_smi[i] = round(100*max(w[offset] for d,w in scenarios)/capacity_mm,3)
            start = end
    return {'data_mode': 'estimated_water_balance', 'method_id': WATER_STATE_CONTRACT_ID, 'profile_depth_cm': 30,
            'soil_resolution_m': 250,
            'capacity_mm': capacity_mm if valid_capacity(capacity_mm) else None,
            'balance_mm': balance[-days:], 'smi_pct': smi[-days:],
            'smi_legacy_pct': legacy_smi[-days:],
            'smi_reasons': reasons[-days:], 'smi_low_pct': lower_smi[-days:], 'smi_high_pct': upper_smi[-days:],
            'et0_mm': [round(v,6) if v is not None else None for v in eto[-days:]],
            'et0_methods': methods[-days:],
            'et0_method_counts': {name:methods.count(name) for name in ('pm_station_wind','pm_estimated_wind','hargreaves','unavailable')},
            'history_start': dates[0], 'history_days':len(dates),
            'reference_parameters': {'evaporation_share':.5,'depletion_fraction':.5},
            'sensitivity_parameters': {'evaporation_share':[0.,.5,1.],'depletion_fraction':[.3,.5,.7]},
            'radiation_method':'temperature_range_inland_0.16',
            'estimated_wind_m_s':2., 'minimum_spinup_days':min(SPINUP_CANDIDATES_DAYS)}
