"""Pure, offline lunar illumination for UI and future analytical consumers.

``lunar_phase(date | aware_datetime | ISO_string)`` returns unrounded numeric
values, a stable English category and the calculation convention/version.
Date-only inputs use noon UTC; timestamps must carry an explicit UTC offset.
The low-order SunCalc approximation is not an ephemeris for event timings.
``phase_cycle`` runs from new (0) through full (0.5) to new (1); illumination
alone cannot distinguish waxing from waning. Categories are presentation bins:
new <=1% light, full >=99%, otherwise waxing/waning. They are NOT event dates.
No data writes, clock reads, dependencies, network calls or model integration.

Illumination equations adapted from SunCalc 1.9.0 (getMoonIllumination,
sunCoords, moonCoords): https://github.com/mourner/suncalc/tree/v1.9.0
Copyright (c) 2014, Vladimir Agafonkin. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from datetime import date, datetime, time, timezone
from math import acos, asin, atan2, cos, pi, radians, sin, tan
import re

CALCULATION_VERSION = 'suncalc-1.9.0-noon-utc-v1'
_EPOCH = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
_OBLIQUITY = radians(23.4397)


def _instant(value: date | datetime | str) -> datetime:
    if isinstance(value, str):
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            value = date.fromisoformat(value)
        elif re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', value):
            value = datetime.fromisoformat(value)
        else:
            raise ValueError('Expected ISO date or timezone-aware timestamp')
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Lunar timestamp requires an explicit timezone')
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time(12), tzinfo=timezone.utc)
    raise TypeError('Expected date, aware datetime or ISO string')


def _equatorial(longitude: float, latitude: float) -> tuple[float, float]:
    ra = atan2(sin(longitude) * cos(_OBLIQUITY) - tan(latitude) * sin(_OBLIQUITY), cos(longitude))
    dec = asin(sin(latitude) * cos(_OBLIQUITY) + cos(latitude) * sin(_OBLIQUITY) * sin(longitude))
    return ra, dec


def lunar_phase(value: date | datetime | str) -> dict:
    """Return approximate geocentric phase/illumination; see module contract."""
    instant = _instant(value)
    days = (instant - _EPOCH).total_seconds() / 86400
    solar_anomaly = radians(357.5291 + 0.98560028 * days)
    center = radians(1.9148 * sin(solar_anomaly) + 0.02 * sin(2 * solar_anomaly)
                     + 0.0003 * sin(3 * solar_anomaly))
    sun_ra, sun_dec = _equatorial(solar_anomaly + center + radians(102.9372) + pi, 0)
    lunar_anomaly = radians(134.963 + 13.064993 * days)
    longitude = radians(218.316 + 13.176396 * days) + radians(6.289) * sin(lunar_anomaly)
    latitude = radians(5.128) * sin(radians(93.272 + 13.229350 * days))
    moon_ra, moon_dec = _equatorial(longitude, latitude)
    distance = 385001 - 20905 * cos(lunar_anomaly)
    separation = acos(max(-1, min(1, sin(sun_dec) * sin(moon_dec)
                                 + cos(sun_dec) * cos(moon_dec) * cos(sun_ra - moon_ra))))
    incidence = atan2(149598000 * sin(separation), distance - 149598000 * cos(separation))
    angle = atan2(cos(sun_dec) * sin(sun_ra - moon_ra),
                  sin(sun_dec) * cos(moon_dec) - cos(sun_dec) * sin(moon_dec) * cos(sun_ra - moon_ra))
    fraction = (1 + cos(incidence)) / 2
    cycle = 0.5 + 0.5 * incidence * (-1 if angle < 0 else 1) / pi
    waxing = cycle < 0.5
    category = 'new' if fraction <= 0.01 else 'full' if fraction >= 0.99 else 'waxing' if waxing else 'waning'
    return {'phase_cycle': cycle, 'illuminated_fraction': fraction, 'waxing': waxing,
            'category': category, 'reference_time': instant.isoformat(),
            'calculation_version': CALCULATION_VERSION}
