"""Map-only hydrology experiment. Never imported by training or IFF features.

ET0: FAO-56 eqs. 6–8, 11–13, 17, 37–40, 47, 50 (daily G=0).
The storage model is a reference sensitivity model, NOT calibrated forest ET.
Its two loss pathways use a linear evaporation availability proxy and FAO's
transpiration stress response (eq. 84). Their unknown partition is explicit.
See docs/mushrooms/prediction-map-hydrology-es.md for scope and assumptions.
"""
import math

from rainmapper_core.mushroom_climatic_water_balance import extraterrestrial_radiation_mj_m2_day


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def wind_at_two_metres(speed_kmh, height_m):
    if not (finite(speed_kmh) and 0 <= speed_kmh <= 200
            and finite(height_m) and 1 <= height_m <= 30):
        raise ValueError('invalid_wind')
    return speed_kmh / 3.6 * 4.87 / math.log(67.8 * height_m - 5.42)


def penman_monteith(day, latitude, altitude, tmin, tmax, rhmin, rhmax,
                   wind_m_s=2., solar_mj=None):
    """FAO reference grass ET0, mm/day; radiation estimated inland if absent.

The 0.16 inland coefficient is an explicit approximation, not local canopy or
slope radiation. Solar radiation can be supplied for independent validation.
No snow/frozen-ground calculation is attempted by the calling history model.
"""
    if not (all(finite(v) for v in (latitude, altitude, tmin, tmax, rhmin, rhmax, wind_m_s))
            and -90 <= latitude <= 90 and -500 <= altitude <= 6000
            and -80 <= tmin <= tmax <= 60 and 0 <= rhmin <= rhmax <= 100
            and 0 <= wind_m_s <= 60):
        raise ValueError('invalid_penman_inputs')
    if solar_mj is not None and not (finite(solar_mj) and solar_mj >= 0):
        raise ValueError('invalid_radiation')
    tmean = (tmin + tmax) / 2
    saturation = lambda t: .6108 * math.exp(17.27 * t / (t + 237.3))
    es = (saturation(tmin) + saturation(tmax)) / 2
    ea = (saturation(tmin) * rhmax + saturation(tmax) * rhmin) / 200
    delta = 4098 * saturation(tmean) / (tmean + 237.3)**2
    pressure = 101.3 * ((293 - .0065 * altitude) / 293)**5.26
    gamma = .000665 * pressure
    ra = extraterrestrial_radiation_mj_m2_day(day, latitude)
    rso = (.75 + .00002 * altitude) * ra
    if rso <= 0:
        raise ValueError('polar_radiation_unavailable')
    rs = min(rso, .16 * math.sqrt(tmax - tmin) * ra) if solar_mj is None else min(solar_mj, rso)
    # FAO bounded cloudiness factor; do not infer negative outgoing longwave.
    cloudiness = 1.35 * min(1., max(.3, rs / rso)) - .35
    rnl = 4.903e-9 * ((tmax + 273.16)**4 + (tmin + 273.16)**4) / 2
    rnl *= max(0., .34 - .14 * math.sqrt(ea)) * cloudiness
    rn = .77 * rs - rnl
    u2 = max(.5, wind_m_s)  # FAO-56 calm-wind lower limit, not an observation.
    eto = (.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea))
    eto /= delta + gamma * (1 + .34 * u2)
    return max(0., eto)


def simulate_reference_store(rain, demand, capacity, initial, *, evaporation_share=.5,
                             depletion_fraction=.5):
    """Two distinct availability responses in ONE 0–30 cm store.

Unknown evaporation/transpiration split: neutral reference 50/50, sensitivity
0/50/100%. These are scenarios, not estimates of forest cover. Evaporation uses
relative available water as a surface-drying proxy, not FAO's full Ke model.
Transpiration Ks=min(1, S/((1-p)*C)); p=.5 reference, .3/.7 sensitivity (FAO-56).
    Losses integrated analytically to avoid a day-step emptying artefact.
Rain enters at start of day; overflow drains immediately. No root/deep-water,
canopy interception, runoff, snow, or terrain-shading corrections are invented.
"""
    if not (finite(capacity) and capacity > 0 and finite(initial) and 0 <= initial <= capacity
            and finite(evaporation_share) and 0 <= evaporation_share <= 1
            and finite(depletion_fraction) and 0 < depletion_fraction < 1
            and len(rain) == len(demand)):
        raise ValueError('invalid_store_inputs')
    storage = initial
    rows = {key: [] for key in ('storage_mm', 'evaporation_mm', 'transpiration_mm', 'drainage_mm')}
    error = 0.
    for p, et0 in zip(rain, demand):
        if not (finite(p) and p >= 0 and finite(et0) and et0 >= 0):
            raise ValueError('invalid_store_weather')
        previous = storage
        drainage = max(0., storage + p - capacity)
        storage = min(capacity, storage + p)
        evaporation = transpiration = 0.
        a = et0 * evaporation_share / capacity
        b = et0 * (1 - evaporation_share)
        threshold = (1 - depletion_fraction) * capacity
        remaining = 1.
        if storage > threshold and et0 > 0:
            crossing = (math.log((a * storage + b) / (a * threshold + b)) / a
                        if a > 0 else (storage - threshold) / b)
            elapsed = min(1., crossing)
            final = ((storage + b / a) * math.exp(-a * elapsed) - b / a
                     if a > 0 else storage - b * elapsed)
            final = max(threshold, final)
            transpiration = b * elapsed
            evaporation = max(0., storage - final - transpiration)
            storage = final
            remaining -= elapsed
        rate = a + b / threshold
        if remaining > 0 and rate > 0:
            loss = storage * -math.expm1(-rate * remaining)
            evaporation += loss * a / rate
            transpiration += loss * (b / threshold) / rate
            storage -= loss
        error = max(error, abs(previous + p - storage - evaporation - transpiration - drainage))
        for key, value in zip(rows, (storage, evaporation, transpiration, drainage)):
            rows[key].append(value)
    rows['mass_error_max_mm'] = error
    return rows
