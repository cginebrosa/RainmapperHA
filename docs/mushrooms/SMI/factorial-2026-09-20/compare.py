"""Eight fixed combinations, IDW only. Offline, no operational changes."""
import csv
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import pearsonr,spearmanr

from simple_layers import history

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'baseline-2026-09-19'
LAYERS=ROOT.parent/'layers-2026-09-19'
sys.path.insert(0,str(BASE/'snapshot'))
from rainmapper_core.mushroom_map_water_physics import penman_monteith
from rainmapper_core.mushroom_climatic_water_balance import hargreaves_reference_evapotranspiration_mm as hargreaves


def num(v):
    try:return float(v)
    except (ValueError,TypeError):return float('nan')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(v):
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [clean(x) for x in v]
    if isinstance(v,np.generic):return clean(v.item())
    if isinstance(v,float) and not np.isfinite(v):return None
    return v


def correlation(a,b,minimum=30):
    a,b=np.array(a,float),np.array(b,float);ok=np.isfinite(a)&np.isfinite(b)
    a,b=a[ok],b[ok]
    if len(a)<minimum or np.ptp(a)==0 or np.ptp(b)==0:return (None,None,len(a))
    return float(pearsonr(a,b).statistic),float(spearmanr(a,b).statistic),len(a)


def write_csv(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'wt',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(clean(rows))


def label(model):
    rule,et,structure=model.split('_')
    return f'{"Simple" if rule=="simple" else "Regulada"} · {"Hargreaves" if et=="hg" else "ET nueva"} · {"una capa" if structure=="one" else "dos capas"}'


def main():
    local=json.loads(gzip.decompress((BASE/'local-inputs.json.gz').read_bytes()))
    for name,digest in local['code_sha256'].items():
        path=BASE/'snapshot'/'rainmapper_core'/name
        if path.exists():assert sha(path)==digest
    # Verify provenance of reused two-layer outputs before adding missing combinations.
    provenance=json.loads((LAYERS/'summary.json').read_text())
    for name,digest in provenance['sha256'].items():assert sha(ROOT.parent/name)==digest
    old={(r['code'],r['date']):r for r in csv.DictReader((BASE/'series.csv').open())}
    with gzip.open(LAYERS/'series.csv.gz','rt') as f:
        layers={(r['code'],r['date']):r for r in csv.DictReader(f)}
    metrics=[];series=[];diagnostics=[];names={};control_metrics=[]
    modelnames=[f'{r}_{e}_{s}' for r in ('simple','regulated') for e in ('hg','pm') for s in ('one','two')]
    for point in local['points']:
        code=point['code'];names[code]=point['name'];inp=point['inputs'];w=inp['interpolated']
        days=w['daily_dates'];last=days[-60:];capacity=point['capacity_mm'];et={'hg':[],'pm':[]}
        for i,d in enumerate(days):
            lo,hi=w['daily_temp_min_idw_c'][i],w['daily_temp_max_idw_c'][i];a=b=None
            if all(np.isfinite(num(v)) for v in (lo,hi)) and -80<=lo<=hi<=60:
                a=hargreaves(date.fromisoformat(d),point['lat'],lo,hi)
                rlo,rhi=w['daily_humidity_min_idw_pct'][i],w['daily_humidity_max_idw_pct'][i]
                wind=inp['wind_u2_m_s'][i]
                if all(np.isfinite(num(v)) for v in (rlo,rhi)) and 0<=rlo<=rhi<=100:
                    b=penman_monteith(date.fromisoformat(d),point['lat'],point['altitude_m'],lo,hi,rlo,rhi,
                        wind if np.isfinite(num(wind)) and 0<=wind<=60 else 2.)
                else:b=a
            et['hg'].append(a);et['pm'].append(b)
        assert np.allclose(np.array(et['pm'][-60:],float),np.array(point['map_weather']['water_balance']['et0_mm'],float),atol=1e-6,equal_nan=True)
        predictions={};controls={}
        for method in et:
            for rule in ('simple','regulated'):
                arr=np.array([num(old[(code,d)][f'idw_{rule}_{method}']) for d in last])
                predictions[f'{rule}_{method}_one']={k:arr for k in ('upper','lower','total')}
            predictions[f'regulated_{method}_two']={k:np.array([num(layers[(code,d)][f'idw_{method}_surface_{k}']) for d in last]) for k in ('upper','lower','total')}
            result=history(w['daily_rain_idw_mm'],et[method],capacity)
            assert result['mass_error_max_mm']<1e-7
            predictions[f'simple_{method}_two']={k:100*np.array(result[k][-60:])/c for k,c in
                (('upper',capacity/3),('lower',2*capacity/3),('total',capacity))}
            controlled=history(w['daily_rain_idw_mm'],et[method],capacity,two=False)
            controls[method]=100*np.array(controlled['total'][-60:])/capacity
            diagnostics.append(dict(code=code,et=method,mass_error_max_mm=result['mass_error_max_mm'],
                 one_drain_first_error_mm=controlled['mass_error_max_mm'],
                 valid_days=int(np.isfinite(predictions[f'simple_{method}_two']['total']).sum())))
        observations={ch:np.array([num(old[(code,d)][ch]) for d in last]) for ch in ('VWC_005','VWC_020')}
        for target_mode in ('depth','total'):
            for ch,part in (('VWC_005','upper'),('VWC_020','lower')):
                target=part if target_mode=='depth' else 'total'
                y=observations[ch];common=np.isfinite(y)
                for model in modelnames:common&=np.isfinite(predictions[model][target])
                y=np.where(common,y,np.nan)
                for model in modelnames:
                    x=np.where(common,predictions[model][target],np.nan)
                    r,rho,n=correlation(x,y);change,_,change_n=correlation(np.diff(x),np.diff(y),29)
                    metrics.append(dict(code=code,name=point['name'],model=model,target_mode=target_mode,channel=ch,
                        n=n,r=r,rho=rho,change_r=change,change_n=change_n,
                        span_pp=float(np.ptp(x[common])) if any(common) else None,
                        first30_r=correlation(x[:30],y[:30],20)[0],last30_r=correlation(x[30:],y[30:],20)[0]))
                if target_mode=='depth':
                    for method,values in controls.items():
                        r,rho,n=correlation(np.where(common,values,np.nan),y)
                        control_metrics.append(dict(code=code,et=method,channel=ch,n=n,r=r,rho=rho))
        for i,d in enumerate(last):
            series.append(dict(code=code,date=d,**{ch:v[i] for ch,v in observations.items()},
                **{f'{model}_{part}':v[i] for model,parts in predictions.items() for part,v in parts.items()}))
    rankings=[];coverage=[]
    for mode in ('depth','total'):
        for metric in ('r','change_r','rho'):
            lookup={(r['code'],r['model'],r['channel']):r[metric] for r in metrics if r['target_mode']==mode}
            codes=[code for code in names if all(lookup[(code,m,ch)] is not None for m in modelnames for ch in ('VWC_005','VWC_020'))]
            for model in modelnames:
                values=[np.mean([lookup[(c,model,ch)] for ch in ('VWC_005','VWC_020')]) for c in codes]
                rankings.append(dict(target_mode=mode,metric=metric,model=model,n=len(codes),codes=codes,
                    median=float(np.median(values)) if values else None,mean=float(np.mean(values)) if values else None))
                if metric=='r':
                    for ch in ('VWC_005','VWC_020'):
                        vals=[lookup[(code,model,ch)] for code in names if lookup[(code,model,ch)] is not None]
                        coverage.append(dict(target_mode=mode,model=model,channel=ch,defined=len(vals),
                            median=float(np.median(vals)) if vals else None))
    write_csv(ROOT/'metrics.csv',metrics);write_csv(ROOT/'series.csv.gz',series);write_csv(ROOT/'drain_order_control.csv',control_metrics)
    files=[ROOT/'PROTOCOL.md',ROOT/'compare.py',ROOT/'simple_layers.py',ROOT/'test_simple_layers.py',
           BASE/'local-inputs.json.gz',BASE/'series.csv',LAYERS/'series.csv.gz',LAYERS/'summary.json']
    summary=dict(stations=22,models=8,rankings=rankings,coverage=coverage,diagnostics=diagnostics,
                 sha256={str(p.relative_to(ROOT.parent)):sha(p) for p in files})
    (ROOT/'summary.json').write_text(json.dumps(clean(summary),ensure_ascii=False,indent=2,allow_nan=False))
    lines=['# SMI-05 · Comparación de las ocho combinaciones','','Lluvia IDW en todas. Igual peso a 5 y 20 cm por estación; mediana entre estaciones.',
           'Datos y parámetros fijos. Correlación no es porcentaje de acierto ni validación de litros.','']
    for mode,title in [('depth','Comparando cada profundidad con su capa'),('total','Comparando siempre el total 0–30 cm con ambas sondas')]:
        rows=sorted([r for r in rankings if r['target_mode']==mode and r['metric']=='r'],key=lambda x:x['median'],reverse=True)
        lines.extend(['## '+title,'',f'Comparación pareada: **{rows[0]["n"]} estaciones** con las ocho opciones y ambas sondas definidas.',
            'Las otras estaciones no desaparecen: su cobertura y resultados por profundidad figuran en `summary.json` y `metrics.csv`.', '',
            '| Combinación | r conjunto | r cambios diarios | Spearman conjunto |', '|---|---:|---:|---:|'])
        for row in rows:
            other={r['metric']:r['median'] for r in rankings if r['target_mode']==mode and r['model']==row['model']}
            lines.append(f'| {label(row["model"])} | {row["median"]:.3f} | {other["change_r"]:.3f} | {other["rho"]:.3f} |')
        lines.extend(['','Estaciones comunes: '+', '.join(names[c] for c in rows[0]['codes'])+'.',''])
    (ROOT/'ranking.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(clean(dict(rankings=[r for r in rankings if r['metric']=='r'],coverage=[r for r in coverage if r['target_mode']=='depth'],
        max_mass_error=max(d['mass_error_max_mm'] for d in diagnostics))),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
