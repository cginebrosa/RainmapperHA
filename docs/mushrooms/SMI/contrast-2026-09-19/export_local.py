"""Historical local export for the 2026-09-19 audit.

Runs against the local HA filesystem and executable code. Revalidate container,
configuration, and source hashes before reusing. Does not reconstruct or train.
"""
import json,hashlib
from pathlib import Path
from datetime import date
from rainmapper_core.mushroom_map_execution import load_config,PointExecutor
from rainmapper_core.mushroom_map_geography_runtime import GeographyPublication,config_for_geography
from rainmapper_core.mushroom_map_weather import PointWeatherReader
points=[('Urus',42.31870,1.85001),('Vallcebre',42.22774,1.80512),('Bellver_1572m',42.31107,1.79181),('Bellver_1825m',42.31461,1.79936),('Olvan',42.06237,1.93813),('XMS_Batlliu_de_Sort',42.42852498752392,1.124382019043183),('XMS_Cami_dels_Nerets',42.15551398034558,.925598144527499)]
config,base=load_config('/share/rainmapper/prediction-map/config.json')
pub=GeographyPublication(base/config['geography_publication_root'],start=False)
row=pub.lookup(pub.reference()['fingerprint']);config=config_for_geography(config,row['root'],row['manifest'],row['identities'])
executor=PointExecutor(config,base)
reader=PointWeatherReader(str(base/config['weather_data']),str(base/config['weather_stations']))
reports=[]
try:
 for name,lat,lon in points:
  try:
   geo=executor.geography.call({'lat':lat,'lon':lon,'start_date':'2026-09-19','water_history':True,'model_inputs':True})
   alt=geo['terrain']['elevation']['value_m'];capacity=geo['water_capacity_mm']
   weather=reader.lookup(lat,lon,alt,end_day=date(2026,9,18),days=60,water_history=True,water_capacity_mm=capacity)
   reports.append({'name':name,'lat':lat,'lon':lon,'altitude_m':alt,'capacity_mm':capacity,'soil_source':geo.get('model_soil_water',{}).get('source'),'weather':weather})
  except Exception as exc: reports.append({'name':name,'lat':lat,'lon':lon,'error':type(exc).__name__+': '+str(exc)})
 print(json.dumps({'scope':'local calculation, not yet externally validated','points':reports},allow_nan=False))
finally:executor.close();pub.close()
