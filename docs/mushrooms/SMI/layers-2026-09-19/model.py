"""SMI-04 audit only. Two available-water stores, not a hydraulic flow solver."""
from pathlib import Path
import math
import sys

BASE = Path(__file__).resolve().parent.parent / 'baseline-2026-09-19'
sys.path.insert(0, str(BASE / 'snapshot'))
from rainmapper_core.mushroom_map_water_physics import simulate_reference_store

SCENARIOS = {
    'control': dict(fraction=1/3, cascade=False, surface=False),
    'cascade': dict(fraction=1/3, cascade=True, surface=False),
    'surface': dict(fraction=1/3, cascade=True, surface=True),
    'surface5': dict(fraction=1/6, cascade=True, surface=True),
    'surface15': dict(fraction=1/2, cascade=True, surface=True),
    'bypass25': dict(fraction=1/3, cascade=True, surface=True, bypass=.25),
}


def finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


def run(rain, demand, capacity, initial_fraction, *, fraction=1/3,
        cascade=True, surface=True, bypass=0.):
    """Return end-of-day stores and fluxes. No missing weather allowed here.

    Separate E and T potentials are integrated using the frozen one-store law.
    Lost uptake in a dry layer is not reassigned to another layer.
    """
    if not (finite(capacity) and capacity > 0 and 0 < fraction < 1
            and 0 <= initial_fraction <= 1 and 0 <= bypass <= 1
            and len(rain) == len(demand)):
        raise ValueError('invalid_layers')
    capacities = [capacity*fraction, capacity*(1-fraction)]
    stores = [c*initial_fraction for c in capacities]
    out = {k: [] for k in ('upper', 'lower', 'total', 'evaporation',
                           'transpiration', 'drainage', 'transfer', 'direct_lower')}
    max_error = 0.
    for p, et in zip(rain, demand):
        if not (finite(p) and p >= 0 and finite(et) and et >= 0):
            raise ValueError('invalid_weather')
        before = sum(stores)
        if cascade:
            direct = p*bypass
            upper_input = p-direct
            transfer = max(0., stores[0]+upper_input-capacities[0])
            stores[0] = min(capacities[0], stores[0]+upper_input)
            bottom_input = direct+transfer
            drainage = max(0., stores[1]+bottom_input-capacities[1])
            stores[1] = min(capacities[1], stores[1]+bottom_input)
        else:
            transfer = direct = drainage = 0.
            for j, c in enumerate(capacities):
                added = p*c/capacity
                drainage += max(0., stores[j]+added-c)
                stores[j] = min(c, stores[j]+added)
        evap = transp = 0.
        for j, c in enumerate(capacities):
            ep = et*.5*((1. if j == 0 else 0.) if surface else c/capacity)
            tp = et*.5*c/capacity
            potential = ep+tp
            result = simulate_reference_store([0.], [potential], c, stores[j],
                       evaporation_share=ep/potential if potential else 0., depletion_fraction=.5)
            stores[j] = result['storage_mm'][0]
            evap += result['evaporation_mm'][0]
            transp += result['transpiration_mm'][0]
            assert -1e-10 <= stores[j] <= c+1e-10
        error = abs(before+p-sum(stores)-evap-transp-drainage)
        max_error = max(max_error, error)
        for key, val in zip(out, (*stores, sum(stores), evap, transp, drainage, transfer, direct)):
            out[key].append(val)
    out['mass_error_max_mm'] = max_error
    out['cumulative_mass_error_mm'] = abs(capacity*initial_fraction+sum(rain)
        -sum(stores)-sum(out['evaporation'])-sum(out['transpiration'])-sum(out['drainage']))
    return out


def history(rain, demand, capacity, scenario):
    """Whole-history simulation; chart slicing must happen AFTER this call."""
    config = SCENARIOS[scenario]
    n = len(rain)
    out = {k: [math.nan]*n for k in ('upper', 'lower', 'total', 'evaporation',
                                    'transpiration', 'drainage', 'transfer', 'direct_lower')}
    state_keys = tuple(out)
    for part in ('upper', 'lower', 'total'):
        out[part+'_dry'] = [math.nan]*n
        out[part+'_wet'] = [math.nan]*n
    errors = []; start = 0
    while start < n:
        if not finite(rain[start]) or not finite(demand[start]):
            start += 1
            continue
        end = start
        while end < n and finite(rain[end]) and finite(demand[end]):
            end += 1
        dry = run(rain[start:end], demand[start:end], capacity, 0., **config)
        wet = run(rain[start:end], demand[start:end], capacity, 1., **config)
        errors.extend([dry['mass_error_max_mm'], wet['mass_error_max_mm'],
                       dry['cumulative_mass_error_mm'], wet['cumulative_mass_error_mm']])
        caps = (capacity*config['fraction'], capacity*(1-config['fraction']))
        for i in range(end-start):
            # Monotone cascade dynamics: dry/full bracket both layers, not just total.
            for k in ('upper', 'lower'):
                assert dry[k][i] <= wet[k][i]+1e-9
            if i+1 >= 90 and all(wet[k][i]-dry[k][i] <= max(.25, .01*c)
                                  for k, c in zip(('upper', 'lower'), caps)):
                for k in state_keys:
                    out[k][start+i] = (dry[k][i]+wet[k][i])/2
                for part in ('upper', 'lower', 'total'):
                    out[part+'_dry'][start+i] = dry[part][i]
                    out[part+'_wet'][start+i] = wet[part][i]
        start = end
    out['mass_error_max_mm'] = max(errors, default=0.)
    return out
