"""Run in the existing LOCAL HA container only, as a separate Python process.

Caller prepends POINTS from verified station-metadata.json. Captures the exact
365-day inputs used by the existing map calculation; does not edit runtime code.
"""
import hashlib
import json
from datetime import date
from pathlib import Path
from rainmapper_core.mushroom_map_execution import load_config, PointExecutor
from rainmapper_core.mushroom_map_geography_runtime import GeographyPublication, config_for_geography
from rainmapper_core.mushroom_map_weather import PointWeatherReader
from rainmapper_core import mushroom_map_hydrology as hydrology

config, base = load_config('/share/rainmapper/prediction-map/config.json')
publication = GeographyPublication(base / config['geography_publication_root'], start=False)
reference = publication.lookup(publication.reference()['fingerprint'])
config = config_for_geography(config, reference['root'], reference['manifest'], reference['identities'])
executor = PointExecutor(config, base)
reader = PointWeatherReader(str(base / config['weather_data']), str(base / config['weather_stations']))
original = hydrology.build_history
capture = {}

def captured(interpolated, latitude, days, capacity_mm=None, **kwargs):
    capture.clear()
    capture.update(interpolated=interpolated, latitude=latitude, capacity_mm=capacity_mm, **kwargs)
    return original(interpolated, latitude, days, capacity_mm, **kwargs)

hydrology.build_history = captured  # Only this short-lived audit process.
try:
    for point in POINTS:
        row = dict(point)
        try:
            capture.clear()
            lat, lon = point['lat'], point['lon']
            geo = executor.geography.call({'lat': lat, 'lon': lon, 'start_date': '2026-09-19',
                                           'water_history': True, 'model_inputs': True})
            altitude = geo['terrain']['elevation']['value_m']
            capacity = geo['water_capacity_mm']
            weather = reader.lookup(lat, lon, altitude, end_day=date(2026, 9, 18), days=60,
                                    water_history=True, water_capacity_mm=capacity)
            row.update(altitude_m=altitude, capacity_mm=capacity, inputs=dict(capture),
                       map_weather=weather, terrain=geo['terrain'])
        except Exception as exc:
            row['error'] = type(exc).__name__ + ': ' + str(exc)
        print(json.dumps(row, ensure_ascii=False, allow_nan=False), flush=True)
finally:
    hydrology.build_history = original
    executor.close()
    publication.close()

files = ('mushroom_map_hydrology.py', 'mushroom_map_weather.py', 'mushroom_map_water_physics.py',
         'mushroom_soil_water_state.py', 'mushroom_climatic_water_balance.py')
root = Path(hydrology.__file__).parent
print(json.dumps({'code_sha256': {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files}}))
