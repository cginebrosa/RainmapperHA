import json,math,re,hashlib,csv,collections
from pathlib import Path
from osgeo import ogr,osr
import numpy as np
ROOT=Path.cwd(); OUT=ROOT/'local-apps/wunderground/data'
wgs=osr.SpatialReference();wgs.ImportFromEPSG(4326);wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
utm=osr.SpatialReference();utm.ImportFromEPSG(25831);utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
fwd=osr.CoordinateTransformation(wgs,utm);rev=osr.CoordinateTransformation(utm,wgs)
ds=ogr.Open(str(ROOT/'mushroom-map-GIS/ign-municipios/prepared/municipalities-2026-08-10.gpkg'),0)
layer=ds.GetLayer(0);layer.SetAttributeFilter("national_code LIKE '3409%'")
mun=[]
for f in layer:
 g=f.GetGeometryRef().Clone();g.Transform(fwd);mun.append((f['name'],f['national_code'],g,g.GetEnvelope()))
print('municipalities',len(mun),flush=True)
def locate(x,y):
 p=ogr.Geometry(ogr.wkbPoint);p.AddPoint_2D(float(x),float(y))
 for name,code,g,(x0,x1,y0,y1) in mun:
  if x0<=x<=x1 and y0<=y<=y1 and g.Intersects(p):return name
 return None
ignore_path=ROOT/'docker-data/ignore_stations_tomap.txt';stations_path=ROOT/'docker-data/stations.txt'
ignored={l.split('#')[0].strip().upper() for l in ignore_path.read_text().splitlines() if l.split('#')[0].strip()}
known=set();disabled=set()
for l in stations_path.read_text().splitlines():
 m=re.search(r'/pws/([A-Za-z0-9]+)',l)
 if m:
  known.add(m[1].upper())
  if l.strip().startswith('#'):disabled.add(m[1].upper())
for row in csv.DictReader((ROOT/'docker-data/Data/estacions_wunderground.csv').open()):known.add(row['Codi Estació'].upper())
all_stations={};metadata=[];paths=[ROOT/'docker-data/PublicData'/f'{d}.geojson' for d in ['07d','01d']]
for path in paths:
 raw=path.read_bytes();data=json.loads(raw);metadata.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'metadata':data['metadata']})
 for f in data['features']:
  p=f['properties'];code=str(p['Codi Estació']).upper();lon,lat=f['geometry']['coordinates'];source=p['Source']
  if code in ignored or (source=='Wunderground' and code in disabled):continue
  vals=[p.get(f'Pluja_Diaria_{i:02}') for i in range(1,8)]
  valid=sum(isinstance(v,(float,int)) and math.isfinite(v) and v>=0 for v in vals)
  if not valid:continue
  x,y,_=fwd.TransformPoint(lon,lat)
  all_stations[(source,code)]={'id':code,'source':source,'name':p.get('Estació'),'lat':lat,'lon':lon,'x':x,'y':y,'altitude_m':p.get('Altitud'),'municipality':p.get('Municipi'),'last_reading':p.get('Ultima Lectura'),'rain_days_7':valid}
sta=list(all_stations.values());xy=np.array([[s['x'],s['y']] for s in sta]);unique_xy=np.unique(np.round(xy,2),axis=0)
# Regular 2-km grid in ETRS89 / UTM31; classify against the full municipality geometries.
xmin=min(m[3][0] for m in mun);xmax=max(m[3][1] for m in mun);ymin=min(m[3][2] for m in mun);ymax=max(m[3][3] for m in mun)
xs=np.arange(math.floor(xmin/2000)*2000+1000,xmax,2000);ys=np.arange(math.floor(ymin/2000)*2000+1000,ymax,2000)
xx,yy=np.meshgrid(xs,ys);grid=np.column_stack([xx.ravel(),yy.ravel()]);names=np.full(len(grid),'',dtype=object)
for name,code,g,(x0,x1,y0,y1) in mun:
 idx=np.where((grid[:,0]>=x0)&(grid[:,0]<=x1)&(grid[:,1]>=y0)&(grid[:,1]<=y1)&(names==''))[0]
 for i in idx:
  pt=ogr.Geometry(ogr.wkbPoint);pt.AddPoint_2D(*map(float,grid[i]))
  if g.Intersects(pt):names[i]=name
inside=names!='';grid=grid[inside];names=names[inside];metrics=[]
for i in range(0,len(grid),250):
 q=grid[i:i+250];dist=np.sqrt(((q[:,None,:]-xy[None,:,:])**2).sum(axis=2));nearidx=dist.argmin(axis=1)
 udist=np.sqrt(((q[:,None,:]-unique_xy[None,:,:])**2).sum(axis=2));d4=np.partition(udist,3,axis=1)[:,3]
 for j in range(len(q)):
  k=i+j;lon,lat,_=rev.TransformPoint(*map(float,q[j]));s=sta[int(nearidx[j])]
  metrics.append({'lon':lon,'lat':lat,'x':float(q[j,0]),'y':float(q[j,1]),'municipality':str(names[k]),'nearest_km':round(float(dist[j,nearidx[j]])/1000,3),'fourth_location_km':round(float(d4[j])/1000,3),'nearest_id':s['id'],'nearest_source':s['source'],'nearest_name':s['name']})
# Spread searches spatially so a single large gap does not use all requests.
selected=[]
for g in sorted(metrics,key=lambda g:(g['nearest_km'],g['fourth_location_km']),reverse=True):
 if all(math.hypot(g['x']-h['x'],g['y']-h['y'])>=12000 for h in selected):selected.append(dict(g,query_id=len(selected)+1))
 if len(selected)>=20:break
for s in sta:s['in_catalunya']=locate(s['x'],s['y']) is not None
summary={'basis':'Local map snapshot; not revalidated against HA real','inputs':metadata,'municipalities':len(mun),'grid_spacing_m':2000,'grid_points':len(metrics),'sources_in_catalunya':dict(collections.Counter(s['source'] for s in sta if s['in_catalunya'])),'stations_in_catalunya':sum(s['in_catalunya'] for s in sta),'all_stations_including_neighbors':len(sta),'excluded_codes':sorted(ignored),'disabled_wu':sorted(disabled),'known_wu':sorted(known),'search_separation_m':12000,'query_count':len(selected),'nearest_km_percentiles':dict(zip(['p50','p90','p95','max'],map(float,np.percentile([m['nearest_km'] for m in metrics],[50,90,95,100])))),'grid_nearest_over_10km':sum(m['nearest_km']>10 for m in metrics),'grid_fourth_over_15km':sum(m['fourth_location_km']>15 for m in metrics)}
for name,data in [('baseline-summary.json',summary),('stations.json',sta),('grid.json',metrics),('search-points.json',selected)]: (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False),flush=True)
print('searches',json.dumps(selected,ensure_ascii=False),flush=True)
