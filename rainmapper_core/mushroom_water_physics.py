"""Shared reference hydrology for training, precomputation and point prediction.

ET0: FAO-56 eqs. 6–8, 11–13, 17, 37–40, 47, 50 (daily G=0).
The storage model is the accepted orientative reference, NOT calibrated forest ET.
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


# Version the complete feature semantics, not the estimator name.
WATER_STATE_CONTRACT_ID = "regulated_pm_single_layer_v1"
MAX_HISTORY_DAYS = 365
MIN_SPINUP_DAYS = 90


def reference_et_series(weather, latitude, *, altitude_m=None, wind_u2_m_s=None):
    """Shared daily ET0 selection. Missing observations are never zeros."""
    from datetime import date
    from .mushroom_climatic_water_balance import hargreaves_reference_evapotranspiration_mm

    dates = [date.fromisoformat(str(day)) for day in weather['daily_dates']]
    if any((b-a).days != 1 for a,b in zip(dates, dates[1:])):
        raise ValueError('hydrology_dates_not_consecutive')
    n = len(dates)
    low, high = weather['daily_temp_min_idw_c'], weather['daily_temp_max_idw_c']
    rhmin = weather.get('daily_humidity_min_idw_pct', [None]*n)
    rhmax = weather.get('daily_humidity_max_idw_pct', [None]*n)
    wind = wind_u2_m_s if wind_u2_m_s is not None else [None]*n
    if any(len(values) != n for values in (low,high,rhmin,rhmax,wind)):
        raise ValueError('hydrology_series_mismatch')
    eto, methods = [], []
    for day,lo,hi,hrlo,hrhi,u in zip(dates,low,high,rhmin,rhmax,wind):
        value, method = None, 'unavailable'
        if finite(lo) and finite(hi) and -80 <= lo <= hi <= 60:
            if (finite(altitude_m) and -500 <= altitude_m <= 6000 and finite(hrlo)
                    and finite(hrhi) and 0 <= hrlo <= hrhi <= 100):
                trusted = finite(u) and 0 <= u <= 60
                try:
                    value = penman_monteith(day,latitude,altitude_m,lo,hi,hrlo,hrhi,u if trusted else 2.)
                    method = 'pm_station_wind' if trusted else 'pm_estimated_wind'
                except ValueError:
                    pass
            if value is None:
                value = hargreaves_reference_evapotranspiration_mm(day,latitude,lo,hi)
                method = 'hargreaves'
        eto.append(value)
        methods.append(method)
    return {'et0_mm': eto, 'et0_methods': methods, 'water_state_contract_id': WATER_STATE_CONTRACT_ID}


def regulated_history(rain, demand, capacity):
    """Full <=365-day trajectory, masked until initial conditions converge.

    A gap restarts uncertainty, not a dry soil. Every published day must have
    >=90 preceding contiguous daily inputs. Dry/wet trajectories bracket the
    unknown initial state; their mean is the accepted reference estimate.
    """
    if not finite(capacity) or capacity <= 0:
        raise ValueError("invalid_store_capacity")
    if len(rain) != len(demand) or len(rain) > MAX_HISTORY_DAYS:
        raise ValueError('hydrology_series_mismatch')
    n = len(rain)
    keys = ('storage_mm','actual_evapotranspiration_mm','drainage_mm','unmet_evaporative_demand_mm')
    result = {key: [None]*n for key in keys}
    reasons = ['inputs_incomplete']*n
    ages = [0]*n
    limit = max(1., .01*capacity)
    valid = [finite(p) and p >= 0 and finite(e) and e >= 0 for p,e in zip(rain,demand)]
    start, error = 0, 0.
    while start < n:
        if not valid[start]:
            start += 1
            continue
        end = start
        while end < n and valid[end]:
            end += 1
        args = dict(rain=rain[start:end], demand=demand[start:end], capacity=capacity)
        dry = simulate_reference_store(**args, initial=0.)
        wet = simulate_reference_store(**args, initial=capacity)
        error = max(error, dry['mass_error_max_mm'], wet['mass_error_max_mm'])
        for offset in range(end-start):
            i = start+offset
            ages[i] = offset+1
            if offset+1 < MIN_SPINUP_DAYS:
                reasons[i] = 'spinup_incomplete'
            elif wet['storage_mm'][offset]-dry['storage_mm'][offset] > limit:
                reasons[i] = 'not_converged'
            else:
                reasons[i] = None
                result['storage_mm'][i] = (dry['storage_mm'][offset]+wet['storage_mm'][offset])/2
                actual = sum(run[k][offset] for run in (dry,wet) for k in ('evaporation_mm','transpiration_mm'))/2
                result['actual_evapotranspiration_mm'][i] = actual
                result['drainage_mm'][i] = (dry['drainage_mm'][offset]+wet['drainage_mm'][offset])/2
                result['unmet_evaporative_demand_mm'][i] = max(0., demand[i]-actual)
        start = end
    return {**result, 'reasons': reasons, 'contiguous_days': ages, 'mass_error_max_mm': error}


def reference_wind(stations, lat, lon, dates, altitude_m=None):
    """XEMA daily mean, known height ->2 m; same proxy in training and map."""
    from datetime import date
    from .mushroom_observation_context import haversine_km
    from .mushroom_weather_idw import RAINFALL_IDW_RADIUS_KM
    # Geometry is constant across the whole daily series. Bound the candidates
    # once, especially for training/precompute with the full station catalog.
    nearby = []
    for station in stations.values():
        if station.source != 'meteocat':
            continue
        distance = haversine_km(lat,lon,station.lat,station.lon)
        if distance <= RAINFALL_IDW_RADIUS_KM:
            nearby.append((station,distance))
    ordered = sorted(nearby, key=lambda item: (
        abs(item[0].altitude_m-altitude_m)
        if finite(altitude_m) and finite(item[0].altitude_m) else float('inf'),
        item[1], item[0].station_code))
    values, sources = [], {}
    for day in dates:
        value = None
        for station,distance in ordered:
            record = station.records_by_day.get(date.fromisoformat(str(day)))
            try:
                value = wind_at_two_metres(record.wind_avg_kmh,record.wind_source_height_m)
            except (AttributeError,ValueError):
                continue
            sources[station.station_code] = {'name':station.station_name,'distance_km':round(distance,2),'altitude_m':station.altitude_m}
            break
        values.append(value)
    return values,sources


def point_reference_et(weather, context, stations):
    """IDW weather plus the same admissible station wind as the point map."""
    wind, _ = reference_wind(stations,context.lat,context.lon,weather['daily_dates'],context.altitude_m)
    return reference_et_series(weather,context.lat,altitude_m=context.altitude_m,wind_u2_m_s=wind)


def uses_water_features(columns):
    return any(str(c).startswith(('soil_water_', 'climatic_water_balance_',
                                 'climatic_balance_mm__lag_', 'eto0_mm__lag_')) for c in columns)


def validate_water_contract(payload, columns):
    """Old physical datasets/weights must be rebuilt, never silently relabelled."""
    if uses_water_features(columns) and payload.get('water_state_contract_id') != WATER_STATE_CONTRACT_ID:
        raise ValueError('water_state_contract_mismatch: rebuild inputs and retrain physical models')
