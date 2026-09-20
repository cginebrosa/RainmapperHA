"""Bounded read-only discovery: reuse saved responses; never log API credentials."""
import ast,json,os,time,datetime
from pathlib import Path
import requests
OUT=Path(__file__).resolve().parents[2]/'data'
t=ast.parse(Path('rainmapper_core/sources/wunderground/daily_api.py').read_text())
default=next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='DEFAULT_API_KEY' for x in n.targets))
key=os.environ.get('RAINMAPPER_WUNDERGROUND_API_KEY',default)
s=requests.Session()
for p in json.loads((OUT/'search-points.json').read_text()):
 target=OUT/f"near-{p['query_id']:02}.json"
 if target.exists() and json.loads(target.read_text()).get("http_status")==200:continue
 result={'query':p,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'endpoint':'https://api.weather.com/v3/location/near'}
 started=time.monotonic()
 try:
  r=s.get(result['endpoint'],params={'geocode':f"{p['lat']},{p['lon']}",'product':'pws','format':'json','apiKey':key},timeout=(5,10))
  result.update(http_status=r.status_code,elapsed_seconds=round(time.monotonic()-started,3))
  if r.status_code==200:result['response']=r.json()
 except Exception as exc:result['error_type']=type(exc).__name__
 target.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(p['query_id'],p['municipality'],result.get('http_status',result.get('error_type')),len(result.get('response',{}).get('location',{}).get('stationId',[])),flush=True)
 if result.get('error_type') or result.get('http_status') in (401,403,429):break
 time.sleep(1)
