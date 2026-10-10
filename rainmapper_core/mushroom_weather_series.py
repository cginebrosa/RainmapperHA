"""Bounded series materializer for historical ML preparation.

The scalar IDW implementation remains the reference. Reduce one station at a
time, in its exact order, across dates (no parallel or reordered reductions).
Station contributions used only for diagnostics are never materialized here.
"""
from collections import OrderedDict
from datetime import timedelta
import math

import numpy as np

from . import mushroom_weather_idw as idw


class WeatherSeries:
    def __init__(self, stations, start, end, duplicates, *, max_bytes=16 * 1024 * 1024):
        self.stations, self.start, self.end = stations, start, end
        self.duplicates = duplicates
        self.days = (end - start).days + 1
        self.dates = [(start + timedelta(days=i)).isoformat() for i in range(self.days)]
        self.max_bytes, self.bytes = max_bytes, 0
        self.cache = OrderedDict()

    def _station(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        # Rows: rain, Tmin, Tmax, RHmin, RHmax. Validity and missingness differ:
        # an invalid measurement is not counted as a missing measurement.
        shape = (5, self.days)
        values = np.zeros(shape, dtype=np.float64)
        valid = np.zeros(shape, dtype=bool)
        missing = np.ones(shape, dtype=bool)
        imputed = np.zeros(self.days, dtype=bool)
        station = self.stations[key]
        duplicates = self.duplicates.get(key)
        if duplicates is None:
            duplicates = idw.suppressed_rain_dates(station)
        for day, record in station.records_by_day.items():
            i = (day - self.start).days
            if not 0 <= i < self.days:
                continue
            rain, reason = idw.usable_daily_rain(station, day, duplicate_dates=duplicates)
            missing[0, i] = reason == 'missing'
            if rain is not None:
                values[0, i], valid[0, i] = rain, True
                imputed[i] = reason == 'repeated_positive_value_imputed_zero'
            for j, metric in enumerate(idw.WEATHER_IDW_METRICS, 1):
                raw = getattr(record, metric, None)
                if raw is None:
                    continue
                missing[j, i] = False
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value) and (j < 3 or 0 <= value <= 100):
                    values[j, i], valid[j, i] = value, True
        packet = values, valid, missing, imputed
        size = sum(array.nbytes for array in packet)
        while self.cache and self.bytes + size > self.max_bytes:
            self.bytes -= sum(array.nbytes for array in self.cache.popitem(last=False)[1])
        if size <= self.max_bytes:
            self.cache[key] = packet
            self.bytes += size
        return packet

    def build(self, context, excluded, *, start=None, end=None):
        left = ((start or self.start) - self.start).days
        right = ((end or self.end) - self.start).days + 1
        if not 0 <= left < right <= self.days:
            raise ValueError('weather_series_range')
        days = right - left
        normalized = {(str(s).strip().lower(), str(c).strip().upper()) for s, c in excluded}
        nearby = []
        for key, station in sorted(self.stations.items(),
                key=lambda item: (str(item[0][0]).lower(), str(item[0][1]).upper())):
            distance = idw.weather_context.haversine_km(
                context.lat, context.lon, station.lat, station.lon)
            if distance <= idw.RAINFALL_IDW_RADIUS_KM:
                nearby.append((key, station, distance))
        shape = (5, days)
        weighted, weights = np.zeros(shape), np.zeros(shape)
        counts = np.zeros(shape, dtype=np.int32)
        missing, altitude_missing = np.zeros_like(counts), np.zeros_like(counts)
        nearest = np.full(shape, np.inf)
        suppressed, imputed = np.zeros(days, dtype=np.int32), np.zeros(days, dtype=np.int32)
        retired = 0
        for key, station, distance in nearby:
            if (str(key[0]).strip().lower(), str(key[1]).strip().upper()) in normalized:
                retired += 1
                continue
            values, valid, absent, zeros = self._station(key)
            values, valid, absent, zeros = values[:, left:right], valid[:, left:right], absent[:, left:right], zeros[left:right]
            correction = idw.altitude_v2.altitude_temperature_correction_c(
                station.altitude_m, context.altitude_m)
            weight = 1.0 / (max(distance, idw.RAINFALL_IDW_DISTANCE_FLOOR_KM) ** idw.RAINFALL_IDW_POWER)
            missing += absent
            suppressed += ~valid[0] & ~absent[0]
            imputed += zeros
            for j in range(5):
                mask = valid[j]
                if j in (1, 2):
                    if correction is None:
                        altitude_missing[j] += mask
                        continue
                    adjusted = values[j, mask] + correction
                else:
                    adjusted = values[j, mask]
                weighted[j, mask] += adjusted * weight
                weights[j, mask] += weight
                counts[j] += mask
                nearest[j, mask] = np.minimum(nearest[j, mask], distance)
        if context.altitude_m is None:
            # The scalar reference returns before examining any station.
            missing[1:3] = 0
            altitude_missing[1:3] = len(nearby)
        ratios = np.divide(weighted, weights, out=np.zeros(shape), where=weights > 0)
        values = [[float(v) if w > 0 else None for v, w in zip(row, weight_row)]
                  for row, weight_row in zip(ratios, weights)]
        distances = [[float(v) if n else None for v, n in zip(row, count_row)]
                     for row, count_row in zip(nearest, counts)]
        observed = (weights[0] > 0).tolist()
        result = {
            'rainfall_contract_id': idw.RAINFALL_IDW_CONTRACT_ID,
            'weather_idw_contract_id': idw.WEATHER_IDW_CONTRACT_ID,
            'target_altitude_m': context.altitude_m,
            'daily_dates': self.dates[left:right],
            'daily_rain_idw_mm': values[0],
            'daily_rain_observed': observed,
            'daily_rain_station_count': counts[0].tolist(),
            'daily_rain_nearest_station_distance_km': distances[0],
            'daily_rain_excluded_missing_station_count': missing[0].tolist(),
            'daily_rain_suppressed_station_count': suppressed.tolist(),
            'daily_rain_imputed_duplicate_zero_station_count': imputed.tolist(),
            'daily_rain_excluded_retired_station_count': [retired] * days,
            'rain_observed_days': sum(observed),
            'rain_missing_days': days - sum(observed),
            'rain_suppressed_station_days': int(suppressed.sum()),
            'rain_imputed_duplicate_zero_station_days': int(imputed.sum()),
        }
        for j, metric in enumerate(idw.WEATHER_IDW_METRICS, 1):
            prefix = f"daily_{metric.removesuffix('_c').removesuffix('_pct')}_idw"
            unit = 'c' if metric.startswith('temp_') else 'pct'
            result[f'{prefix}_{unit}'] = values[j]
            result[f'{prefix}_station_count'] = counts[j].tolist()
            result[f'{prefix}_nearest_station_distance_km'] = distances[j]
            result[f'{prefix}_excluded_missing_station_count'] = missing[j].tolist()
            result[f'{prefix}_excluded_altitude_missing_station_count'] = altitude_missing[j].tolist()
        return result
