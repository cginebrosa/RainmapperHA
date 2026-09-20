import json,datetime,collections,csv
from pathlib import Path
from osgeo import ogr,osr
import numpy as np
O=Path(__file__).resolve().parents[2]/'data'
load=lambda name:json.loads((O/name).read_text())
b=load('baseline-summary.json');stations=load('stations.json');grid=load('grid.json')
w= osr.SpatialReference();w.ImportFromEPSG(4326);w.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
u=osr.SpatialReference();u.ImportFromEPSG(25831);u.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
transform=osr.CoordinateTransformation(w,u)
ds=ogr.Open('mushroom-map-GIS/ign-municipios/prepared/municipalities-2026-08-10.gpkg',0)
layer=ds.GetLayer(0);layer.SetAttributeFilter("national_code LIKE '3409%'")
municipalities=[(f['name'],f.GetGeometryRef().Clone()) for f in layer]
def locate(lon,lat):
 p=ogr.Geometry(ogr.wkbPoint);p.AddPoint_2D(lon,lat)
 for name,g in municipalities:
  a,c,d,e=g.GetEnvelope()
  if a<=lon<=c and d<=lat<=e and g.Intersects(p):return name
 return None
allc={};conflicts=[];rawcount=0
for path in sorted(O.glob('near-*.json')):
 data=json.loads(path.read_text());locations=data.get('response',{}).get('location',{})
 for i,code in enumerate(locations.get('stationId',[])):
  rawcount+=1
  row={k:v[i] for k,v in locations.items() if isinstance(v,list)}
  if code in allc:
   if any(allc[code][k]!=row[k] for k in ('latitude','longitude')):conflicts.append(code)
   allc[code]['query_ids'].append(data['query']['query_id']);continue
  allc[code]=dict(row,query_ids=[data['query']['query_id']],retrieved_utc=data['retrieved_utc'])
xy=np.array([[s['x'],s['y']] for s in stations]);gx=np.array([[g['x'],g['y']] for g in grid]);base=np.array([g['nearest_km'] for g in grid])
candidates=[];distances={}
for code,c in allc.items():
 x,y,_=transform.TransformPoint(c['longitude'],c['latitude']);d=np.sqrt(((xy-[x,y])**2).sum(axis=1))/1000;idx=int(d.argmin());near=stations[idx]
 age=(datetime.datetime.fromisoformat(c['retrieved_utc']).timestamp()-c['updateTimeUtc'])/3600
 municipality=locate(c['longitude'],c['latitude'])
 state='nueva'
 if code in b['disabled_wu'] or code in b['excluded_codes']:state='excluida/desactivada'
 elif code in b['known_wu']:state='ya conocida'
 elif not municipality:state='fuera de Catalunya'
 dg=np.sqrt(((gx-[x,y])**2).sum(axis=1))/1000
 improve=(base>8)&(base-dg>=2)
 benefit=float(np.maximum(base-dg,0)[base>8].sum())
 c.update(status=state,municipality=municipality,age_hours=round(age,2),nearest_existing_km=round(float(d[idx]),3),nearest_existing_id=near['id'],nearest_existing_source=near['source'],nearest_existing_name=near['name'],gap_points_improved_2km=int(improve.sum()),benefit_km_sum=round(benefit,2),rank=None)
 c['nearby_other_source']=bool(d[idx]<0.3)
 c['eligible_for_shortlist']=bool(state=='nueva' and c['qcStatus']==1 and 0<=age<=48 and not c['nearby_other_source'] and improve.any())
 candidates.append(c);distances[code]=dg
# Greedy geometry-only shortlist. Each next candidate must improve remaining gaps.
current=base.copy();short=[]
pool=[c for c in candidates if c['eligible_for_shortlist']]
while pool and len(short)<12:
 scores=[float(np.maximum(current-distances[c['stationId']],0)[base>8].sum()) for c in pool]
 chosen=pool.pop(int(np.argmax(scores)));delta=current-distances[chosen['stationId']]
 count=int(((base>8)&(delta>=2)).sum())
 if count==0:continue
 chosen['rank']=len(short)+1;chosen['incremental_gap_points_improved_2km']=count;chosen['incremental_benefit_km_sum']=round(max(scores),2)
 current=np.minimum(current,distances[chosen['stationId']]);short.append(chosen)
summary={'raw_results':rawcount,'unique_stations':len(candidates),'categories':dict(collections.Counter(c['status'] for c in candidates)),'new_qc_status':dict(collections.Counter(c['qcStatus'] for c in candidates if c['status']=='nueva')),'coordinate_conflicts':conflicts,'new_within_300m_of_existing':sum(c['status']=='nueva' and c['nearby_other_source'] for c in candidates),'shortlist_count':len(short),'baseline_grid_nearest_over_10km':int((base>10).sum()),'hypothetical_grid_nearest_over_10km':int((current>10).sum()),'baseline_grid_nearest_over_8km':int((base>8).sum()),'hypothetical_grid_nearest_over_8km':int((current>8).sum()),'hypothetical_max_nearest_km':round(float(current.max()),3),'warning':'Hypothetical geometry only. No candidate approved; no weather history or rainfall quality checked. Not an exhaustive WU inventory.'}
candidates.sort(key=lambda c:(c['rank'] or 999,-c['benefit_km_sum']))
for name,data in [('candidates.json',candidates),('shortlist.json',short),('discovery-summary.json',summary)]: (O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
fields=['rank','stationId','stationName','municipality','latitude','longitude','status','qcStatus','age_hours','nearest_existing_km','nearest_existing_id','nearest_existing_source','nearby_other_source','gap_points_improved_2km','incremental_gap_points_improved_2km']
with (O/'candidates.csv').open('w',newline='',encoding='utf-8-sig') as f:
 writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(candidates)
print(json.dumps(summary,ensure_ascii=False,indent=2))
for c in short:print(c['rank'],c['stationId'],c['stationName'],c['municipality'],c['nearest_existing_km'],c['incremental_gap_points_improved_2km'],c['age_hours'])
