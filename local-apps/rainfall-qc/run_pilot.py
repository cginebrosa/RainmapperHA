"""Offline exploratory IDW quality experiment. Never writes operational inputs."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import argparse
import hashlib
import json
import time
import warnings
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from rainmapper_core import mushroom_weather_idw as idw
from rainmapper_core.mushroom_observation_context import DailyWeatherRecord,WeatherStation

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--history',type=Path,default=Path('docker-data/Data/weather-history'))
    ap.add_argument('--output',type=Path,default=Path('docker-data/diagnostics/rainfall-qc/pilot'))
    ap.add_argument('--stations',type=Path,default=Path('docker-data/diagnostics/rainfall-qc/stations.txt'))
    args=ap.parse_args();started=time.perf_counter();args.output.mkdir(parents=True,exist_ok=True)
    current=json.loads((args.history/'CURRENT.json').read_text());mp=args.history/current['manifest_path']
    assert hashlib.sha256(mp.read_bytes()).hexdigest()==current['manifest_sha256']
    manifest=json.loads(mp.read_text())
    cat=pq.ParquetFile(args.history/manifest['catalog']['path']).read().to_pandas()
    cat=cat[cat.lat.between(40.2,43.3)&cat.lon.between(-.5,3.8)].copy()
    disabled=idw.disabled_wunderground_station_keys(args.stations)
    cat=cat[[ (s,str(c).upper()) not in disabled for s,c in zip(cat.source,cat.station_code)]]
    cat['key']=cat.source+':'+cat.station_code;cat=cat.drop_duplicates('key').sort_values('key').reset_index(drop=True)
    keys=cat.key.tolist();needed=set(keys);frames=[]
    for p in manifest['partitions']:
        if p['year'] not in (2023,2024,2025,2026):continue
        path=args.history/p['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256']
        f=pq.ParquetFile(path).read(columns=['station_code','local_date','rain_mm']).to_pandas()
        f['key']=p['source']+':'+f.station_code
        f=f[f.key.isin(needed)&f.local_date.between('20231229','20260925')];frames.append(f)
    f=pd.concat(frames,ignore_index=True);assert not f.duplicated(['key','local_date']).any()
    dates=pd.date_range('2023-12-29','2026-09-25');datestring=dates.strftime('%Y%m%d')
    raw=f.pivot(index='local_date',columns='key',values='rain_mm').reindex(index=datestring,columns=keys).to_numpy(float)
    # Preserve the existing exact positive duplicate-to-zero rule, including
    # duplicates above the sanity limit (canonical rule checks duplicates first).
    repeated=np.zeros(raw.shape,bool);repeated[1:]=(raw[1:]>0)&(raw[1:]==raw[:-1])
    values=np.where((raw>=0)&(raw<=300),raw,np.nan);values[repeated]=0
    ll=np.radians(cat[['lat','lon']].to_numpy());lat=ll[:,0];lon=ll[:,1]
    dist=6371*2*np.arcsin(np.minimum(1,np.sqrt(np.sin((lat[:,None]-lat[None,:])/2)**2+np.cos(lat[:,None])*np.cos(lat[None,:])*np.sin((lon[:,None]-lon[None,:])/2)**2)))
    altitude=cat.altitude.to_numpy(float)
    # Independent-site approximation: connected clusters within 250 m. No claim
    # that coordinates alone establish ownership or physical-sensor identity.
    parent=np.arange(len(cat))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,j in zip(*np.where(np.triu(dist<.25,1))):parent[find(j)]=find(i)
    cluster=np.array([find(i) for i in range(len(cat))])
    fixed=['meteocat:'+x for x in ('DF','YP','UO','YB','W9','X5','CG','YA')]
    targets=[keys.index(k) for k in fixed if k in needed]
    rng=np.random.default_rng(20260926)
    for source,count in [('meteocat',4),('aemet',12)]:
        eligible=[i for i in range(len(cat)) if cat.iloc[i].source==source and i not in targets and np.isfinite(raw[:,i]).sum()>=180 and len(set(cluster[(dist[i]<=15)&(cluster!=cluster[i])]))>=4 and 40.5<=cat.iloc[i].lat<=42.9 and 0<=cat.iloc[i].lon<=3.4]
        targets+=rng.choice(eligible,size=min(count,len(eligible)),replace=False).tolist()
    config={'generation_id':current['generation_id'],'baseline_contract':idw.RAINFALL_IDW_CONTRACT_ID,'period':['2024-01-01','2026-09-25'],'target_count':len(targets),'target_keys':[keys[i] for i in targets],'spatial_qc_radius_km':5,'qc_altitude_difference_m':300,'cluster_distance_m':250,'minimum_peer_sites':3,'minimum_peer_sources':2,'wet_peer_min_mm':5,'wet_peer_median_min_mm':10,'wet_peer_fraction_min':.8,'low_observation_max_mm':.2,'soft_quality_weight':.25,'high_min_mm':20,'high_ratio_min':4,'high_peer_median_max_mm':1,'high_persistence':'today and at least one previous two days','tuned_on_results':False,'reference_status':'official-network values, not individually certified truth; known incomplete DF 2025-07-06 excluded','production_policy_changed':False}
    (args.output/'config.json').write_text(json.dumps(config,indent=2))
    cat.iloc[targets].to_csv(args.output/'targets.csv',index=False)
    rows=[];audit=[];parity=[]
    for target in targets:
        keep=cluster!=cluster[target]
        candidates=np.flatnonzero(keep&(dist[target]<=15))
        x=values[:,candidates];w=1/np.maximum(dist[target,candidates],.1)**2
        qlow=np.ones_like(x);qboth=np.ones_like(x);lowflags=np.zeros_like(x,bool);highflags=np.zeros_like(x,bool);qc_support=np.zeros_like(x,bool)
        for j,i in enumerate(candidates):
            peers=np.flatnonzero(keep&(cluster!=cluster[i])&(dist[i]<=5)&(np.abs(altitude-altitude[i])<=300))
            groups=[peers[cluster[peers]==g] for g in sorted(set(cluster[peers]))]
            if len(groups)<3:continue
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning)
                grouped=np.column_stack([np.nanmedian(values[:,g],axis=1) for g in groups])
                n=np.isfinite(grouped).sum(axis=1);median=np.nanmedian(grouped,axis=1)
            sources=sum(np.isfinite(values[:,peers[cat.source.to_numpy()[peers]==s]]).any(axis=1) for s in sorted(set(cat.source.to_numpy()[peers])))
            qc_support[:,j]=(n>=3)&(sources>=2)
            wet=(grouped>=5).sum(axis=1)/np.maximum(n,1)
            low=(n>=3)&(sources>=2)&(median>=10)&(wet>=.8)&(x[:,j]<=.2)
            high=(n>=3)&(sources>=2)&(median<=1)&(x[:,j]>=20)&(x[:,j]>4*np.maximum(median,1))
            prior=np.zeros(len(dates),bool);prior[1:]|=high[:-1];prior[2:]|=high[:-2]
            high &= prior
            qlow[low,j]=.25;qboth[low|high,j]=.25;lowflags[:,j]=low;highflags[:,j]=high
        finite=np.isfinite(x)
        predictions={}
        for name,q in [('baseline',np.ones_like(x)),('soft_low',qlow),('soft_both_persistent',qboth),('exclude_low',np.where(lowflags,0.,1.))]:
            weights=finite*w*q;denom=weights.sum(axis=1)
            predictions[name]=np.divide((np.nan_to_num(x)*weights).sum(axis=1),denom,out=np.full(len(dates),np.nan),where=denom>0)
        # Check vectorized baseline against the real canonical function on two
        # observed wet dates per target. No model or worker execution involved.
        wetdates=np.flatnonzero((raw[:,target]>=5)&(dates.year>=2024))[:2]
        for t in wetdates:
            day=dates[t].date();stations={};duplicates={};distances={}
            for i in candidates:
                if not np.isfinite(raw[t,i]):continue
                c=cat.iloc[i];key=(c.source,c.station_code)
                record=DailyWeatherRecord(c.source,c.station_code,c.station_name,day,c.lat,c.lon,float(raw[t,i]),None,None,None,None,None,None,None)
                stations[key]=WeatherStation(c.source,c.station_code,c.station_name,c.lat,c.lon,{day:record})
                duplicates[key]={day} if repeated[t,i] else set();distances[key]=float(dist[target,i])
            answer=idw.estimate_daily_rain_idw(stations,target_lat=cat.iloc[target].lat,target_lon=cat.iloc[target].lon,day=day,duplicate_dates_by_station=duplicates,station_distances_km=distances).rain_mm
            assert answer is None and np.isnan(predictions['baseline'][t]) or answer is not None and np.isclose(answer,predictions['baseline'][t],atol=1e-10)
            parity.append({'target':keys[target],'date':str(day),'canonical':answer,'pilot':float(predictions['baseline'][t])})
        truth=np.where((raw[:,target]>=0)&(raw[:,target]<=300),raw[:,target],np.nan)
        valid=(dates.year>=2024)&np.isfinite(truth)&np.isfinite(predictions['baseline'])
        if keys[target]=='meteocat:DF':valid &= dates!=pd.Timestamp('2025-07-06')
        for t in np.flatnonzero(valid):
            rows.append({'target':keys[target],'date':str(dates[t].date()),'reference_mm':truth[t],'input_stations':int(finite[t].sum()),'qc_supported_inputs':int((qc_support[t]&finite[t]).sum()),'low_flags':int(lowflags[t].sum()),'high_flags':int(highflags[t].sum()),**{k:float(v[t]) for k,v in predictions.items()}})
            for j in np.flatnonzero(lowflags[t]|highflags[t]):
                audit.append({'reference_target':keys[target],'date':str(dates[t].date()),'flagged_station':keys[candidates[j]],'rain_mm':float(x[t,j]),'reason':'low_spatial' if lowflags[t,j] else 'high_persistent','distance_to_target_km':round(float(dist[target,candidates[j]]),3)})
        print(keys[target],int(valid.sum()),'days',int(lowflags[valid].sum()),'low flags',int(highflags[valid].sum()),'high flags',flush=True)
    results=pd.DataFrame(rows);results.to_csv(args.output/'predictions.csv.gz',index=False,compression='gzip')
    pd.DataFrame(audit).to_csv(args.output/'flagged.csv.gz',index=False,compression='gzip')
    (args.output/'baseline-parity.json').write_text(json.dumps(parity,indent=2))
    metrics=[]
    variants=['baseline','soft_low','soft_both_persistent','exclude_low']
    for period,subset in [('all',results),('2024',results[results.date.str.startswith('2024')]),('2025',results[results.date.str.startswith('2025')]),('2026',results[results.date.str.startswith('2026')])]:
        for band,mask in [('all',np.ones(len(subset),bool)),('dry',subset.reference_mm<=.2),('wet_ge5',subset.reference_mm>=5),('heavy_ge20',subset.reference_mm>=20)]:
            part=subset[mask]
            for variant in variants:
                good=part.dropna(subset=[variant]);err=good[variant]-good.reference_mm
                metrics.append({'period':period,'band':band,'variant':variant,'n':len(good),'mae_mm':float(err.abs().mean()),'rmse_mm':float(np.sqrt((err**2).mean())),'bias_mm':float(err.mean()),'changed_days':int((good[variant]-good.baseline).abs().gt(1e-8).sum()),'worse_gt1mm':int(((err.abs()-(good.baseline-good.reference_mm).abs())>1).sum()),'better_gt1mm':int((((good.baseline-good.reference_mm).abs()-err.abs())>1).sum())})
    pd.DataFrame(metrics).to_csv(args.output/'metrics.csv',index=False)
    # Calendar-aligned nonoverlapping 7-day blocks, with complete common support,
    # reduce (but cannot eliminate) daily source reporting-boundary differences.
    results['block']=(pd.to_datetime(results.date)-pd.Timestamp('2024-01-01')).dt.days//7
    agg=results.groupby(['target','block']).agg(n=('date','size'),reference_mm=('reference_mm','sum'),**{v:(v,'sum') for v in variants})
    agg=agg[agg.n==7];agg.to_csv(args.output/'weekly.csv.gz',compression='gzip')
    summary={'elapsed_seconds':round(time.perf_counter()-started,3),'station_days_evaluated':len(results),'reference_stations':len(targets),'baseline_parity_checks':len(parity),'weekly_blocks':len(agg),'distinct_flagged_station_days':len(pd.DataFrame(audit)[['flagged_station','date']].drop_duplicates()) if audit else 0,'weekly_metrics':{v:{'mae_mm':float((agg[v]-agg.reference_mm).abs().mean()),'bias_mm':float((agg[v]-agg.reference_mm).mean())} for v in variants},'operational_jobs_started':0}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
