"""Reproduce SMI-04 offline; consumes SMI-01/03 evidence, writes here only."""
import collections
import csv
from datetime import date, datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import unicodedata

import numpy as np
from scipy.stats import pearsonr, spearmanr
from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, CustomJS, Div, HoverTool, Range1d, Select
from bokeh.plotting import figure
from bokeh.resources import INLINE

from model import BASE, SCENARIOS, history, simulate_reference_store
from rainmapper_core.mushroom_map_water_physics import penman_monteith
from rainmapper_core.mushroom_climatic_water_balance import hargreaves_reference_evapotranspiration_mm as hargreaves

ROOT = Path(__file__).resolve().parent
FIRST = BASE.parent/'contrast-2026-09-19'


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normal(name):
    return ''.join(c for c in unicodedata.normalize('NFD', name.lower()) if c.isalnum())


def number(v):
    try:
        v = float(v)
        return v if math.isfinite(v) else math.nan
    except (TypeError, ValueError):
        return math.nan


def corr(a, b, minimum=30):
    a, b = np.array(a, float), np.array(b, float)
    valid = np.isfinite(a)&np.isfinite(b)
    a, b = a[valid], b[valid]
    if len(a)<minimum or np.ptp(a)==0 or np.ptp(b)==0:
        return dict(n=len(a), r=None, rho=None)
    return dict(n=len(a), r=float(pearsonr(a,b).statistic), rho=float(spearmanr(a,b).statistic))


def clean(v):
    if isinstance(v, dict):return {k:clean(x) for k,x in v.items()}
    if isinstance(v, (list, tuple)):return [clean(x) for x in v]
    if isinstance(v, np.generic):return clean(v.item())
    if isinstance(v, float) and not math.isfinite(v):return None
    return v


def csv_write(path, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    opener = gzip.open if path.suffix=='.gz' else open
    with opener(path, 'wt', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader();writer.writerows(clean(rows))


def plot(title, unit, shared=None):
    p = figure(title=title, height=240, sizing_mode='stretch_width', x_axis_type='datetime',
               tools='pan,wheel_zoom,box_zoom,reset,save', **(dict(x_range=shared) if shared else {}))
    p.yaxis.axis_label = unit
    return p


def line(p, dates, values, label, color, dash='solid', visible=True):
    src = ColumnDataSource(dict(day=dates,value=values))
    glyph = p.line('day','value',source=src,color=color,line_width=2,legend_label=label,
                   line_dash=dash,visible=visible)
    p.add_tools(HoverTool(renderers=[glyph],tooltips=[('Serie',label),('Fecha','@day{%F}'),
        ('Valor','@value{0.000}')],formatters={'@day':'datetime'},mode='vline'))
    p.legend.click_policy='hide';p.legend.label_text_font_size='10px'


def episode_rows(code, days, gauge, rain, obs, predictions):
    # Only descriptive measured episodes; do not infer an instrumental detection threshold.
    wet = [i for i,v in enumerate(gauge) if np.isfinite(v) and v>=1.]
    groups=[]
    for i in wet:
        if groups and i-groups[-1][-1]<=2 and all(np.isfinite(gauge[j]) for j in range(groups[-1][-1],i+1)):
            groups[-1].append(i)
        else:groups.append([i])
    result=[]
    for gi, group in enumerate(groups):
        start,end=group[0],group[-1]
        # Require known preceding two dry days and following three days with no new episode.
        if start<2 or end+3>=len(days):continue
        if any(not np.isfinite(v) for v in gauge[start-2:end+4]):continue
        if any(v>=1 for v in gauge[start-2:start]):continue
        if gi+1<len(groups) and groups[gi+1][0]<=end+3:continue
        row=dict(code=code,start=days[start],end=days[end],
            rain_gauge_mm=sum(gauge[start:end+1]),rain_idw_mm=sum(rain[start:end+1]))
        for key, values in obs.items():
            block=np.array(values[start-1:end+4],float)
            if not np.isfinite(block).all():continue
            row[key+'_before']=values[start-1]
            row[key+'_delta_next']=values[end+1]-values[start-1]
            row[key+'_peak3_delta']=max(values[end+1:end+4])-values[start-1]
        for key, values in predictions.items():
            if not (key.endswith('_one_total') or key.endswith('_surface_lower')):continue
            if not np.isfinite(values[start-1:end+4]).all():continue
            row[key+'_before_pct']=values[start-1]
            row[key+'_delta_next_pp']=values[end+1]-values[start-1]
            row[key+'_peak3_delta_pp']=max(values[end+1:end+4])-values[start-1]
        result.append(row)
    return result


def main():
    local=read(BASE/'local-inputs.json.gz')
    frozen=list((BASE/'snapshot'/'rainmapper_core').glob('*.py'))
    for path in frozen:
        if path.name!='__init__.py':assert sha(path)==local['code_sha256'][path.name]
    expanded=read(FIRST/'expanded-stations.json.gz')
    original={p['station']:p for p in read(FIRST/'evidence.json.gz')['icgc']['points']}
    observations={normal(p['name']):p.get('rows', original.get(p['station'],{}).get('rows')) for p in expanded['points']}
    baseline={}
    with (BASE/'series.csv').open() as f:
        for row in csv.DictReader(f):baseline[(row['code'],row['date'])]=row
    metrics=[];daily=[];summaries=[];episodes=[];panels=[]
    for point in local['points']:
        code,name=point['code'],point['name'];capacity=point['capacity_mm']
        inp=point['inputs'];weather=inp['interpolated'];days=weather['daily_dates'];last=days[-60:]
        assert len(days)==365 and len(set(days))==365
        assert all((date.fromisoformat(b)-date.fromisoformat(a)).days==1 for a,b in zip(days,days[1:]))
        by_day=collections.defaultdict(list);seen=set()
        for row in observations[normal(name)]:
            instant=datetime.fromisoformat(row['TmStamp']);assert instant not in seen
            seen.add(instant);by_day[instant.date().isoformat()].append(row)
        obs={};gauge=[]
        for channel in ('VWC_005','VWC_020','VWC_050'):
            vals=[]
            for day in last:
                good=[number(r.get(channel)) for r in by_day[day]]
                good=[v for v in good if 0<v<=1]
                vals.append(float(np.mean(good)) if len(good)>=44 else math.nan)
            obs[channel]=vals
            assert np.allclose(vals,[number(baseline[(code,d)][channel]) for d in last],equal_nan=True)
        for day in last:
            rows=by_day[day];values=[number(r.get('Pluja_Tot')) for r in rows]
            slots={datetime.fromisoformat(r['TmStamp']).time().isoformat() for r in rows}
            expected={f'{h:02}:{m:02}:00' for h in range(24) for m in (0,30)}
            gauge.append(sum(values) if len(rows)==48 and slots==expected and all(v>=0 for v in values) else math.nan)
        rain=weather['daily_rain_idw_mm'];ets={'hg':[],'pm':[]}
        for i,day in enumerate(days):
            lo,hi=weather['daily_temp_min_idw_c'][i],weather['daily_temp_max_idw_c'][i]
            old=new=None
            if all(math.isfinite(number(v)) for v in (lo,hi)) and -80<=lo<=hi<=60:
                old=hargreaves(date.fromisoformat(day),point['lat'],lo,hi)
                rlo,rhi=weather['daily_humidity_min_idw_pct'][i],weather['daily_humidity_max_idw_pct'][i]
                wind=inp['wind_u2_m_s'][i]
                if all(math.isfinite(number(v)) for v in (rlo,rhi)) and 0<=rlo<=rhi<=100:
                    new=penman_monteith(date.fromisoformat(day),point['lat'],point['altitude_m'],lo,hi,rlo,rhi,
                         wind if math.isfinite(number(wind)) and 0<=wind<=60 else 2.)
                else:new=old
            ets['hg'].append(old);ets['pm'].append(new)
        assert np.allclose(np.array(ets['pm'][-60:],float),np.array(point['map_weather']['water_balance']['et0_mm'],float),atol=1e-6,equal_nan=True)
        forcings={'idw':rain}
        if all(np.isfinite(gauge)):forcings['gauge']=rain[:-60]+gauge
        preds={};errors=[];support={};fluxes={};initials={}
        for forcing, rainfall in forcings.items():
            for method, et in ets.items():
                prefix=f'{forcing}_{method}'
                # Saved single-layer baseline already controls gaps and 90-day initial uncertainty.
                baseline_key=f'{"idw" if forcing=="idw" else "gauge_recent"}_regulated_{method}'
                single=np.array([number(baseline[(code,d)].get(baseline_key)) for d in last])
                preds[prefix+'_one_total']=single
                for scenario,cfg in SCENARIOS.items():
                    result=history(rainfall,et,capacity,scenario)
                    errors.append(result['mass_error_max_mm'])
                    assert result['mass_error_max_mm']<1e-7
                    caps={'upper':capacity*cfg['fraction'],'lower':capacity*(1-cfg['fraction']),'total':capacity}
                    for part,c in caps.items():
                        preds[f'{prefix}_{scenario}_{part}']=100*np.array(result[part][-60:])/c
                        for initial in ('dry','wet'):
                            initials[f'{prefix}_{scenario}_{part}_{initial}']=100*np.array(result[part+'_'+initial][-60:])/c
                    support[prefix+'_'+scenario]=int(np.isfinite(preds[f'{prefix}_{scenario}_total']).sum())
                    fluxes[prefix+'_'+scenario] = {k:float(np.nansum(result[k][-60:]))
                        for k in ('transfer','direct_lower','evaporation','transpiration','drainage')}
                    if scenario=='control':
                        values=preds[f'{prefix}_control_total'];valid=np.isfinite(values)&np.isfinite(single)
                        assert np.allclose(values[valid],single[valid],atol=1e-9)
                    for channel,part in (('VWC_005','upper'),('VWC_020','lower'),('VWC_050','total')):
                        for target in dict.fromkeys((part,'total')):
                            values=preds[f'{prefix}_{scenario}_{target}'];y=np.array(obs[channel])
                            ok=np.isfinite(values)&np.isfinite(single)&np.isfinite(y)
                            x=np.where(ok,values,np.nan);ref=np.where(ok,single,np.nan);y=np.where(ok,y,np.nan)
                            r=corr(x,y);rr=corr(ref,y)
                            change=corr(np.diff(x),np.diff(y),29);refchange=corr(np.diff(ref),np.diff(y),29)
                            dry_x=np.where(ok,initials[f'{prefix}_{scenario}_{target}_dry'],np.nan)
                            wet_x=np.where(ok,initials[f'{prefix}_{scenario}_{target}_wet'],np.nan)
                            metrics.append(dict(code=code,name=name,forcing=forcing,et=method,scenario=scenario,
                                channel=channel,target=target,**r,reference_r=rr['r'],
                                delta_r=r['r']-rr['r'] if r['r'] is not None and rr['r'] is not None else None,
                                change_n=change['n'],change_r=change['r'],reference_change_r=refchange['r'],
                                first30_r=corr(x[:30],y[:30],20)['r'],last30_r=corr(x[30:],y[30:],20)['r'],
                                candidate_span_pp=float(np.ptp(x[ok])) if any(ok) else None,
                                reference_span_pp=float(np.ptp(ref[ok])) if any(ok) else None,
                                observed_span_m3_m3=float(np.ptp(y[ok])) if any(ok) else None,
                                initial_dry_r=corr(dry_x,y)['r'],initial_wet_r=corr(wet_x,y)['r'],
                                initial_dry_span_pp=float(np.ptp(dry_x[ok])) if any(ok) else None,
                                initial_wet_span_pp=float(np.ptp(wet_x[ok])) if any(ok) else None))
        summaries.append(dict(code=code,name=name,capacity_mm=capacity,gauge_days=sum(np.isfinite(gauge)),
                              support=support,fluxes_mm=fluxes,mass_error_max_mm=max(errors)))
        for i,day in enumerate(last):
            daily.append(dict(code=code,name=name,date=day,rain_idw=rain[-60+i],rain_gauge=gauge[i],
                              **{c:v[i] for c,v in obs.items()},**{k:v[i] for k,v in preds.items()}))
        episodes.extend(episode_rows(code,last,gauge,rain[-60:],obs,preds))
        calendar=[datetime.fromisoformat(d) for d in last]
        a=plot(name+' · ¿La lluvia recarga solo arriba o también abajo?','Reserva disponible (%)')
        a.y_range=Range1d(0,100)
        line(a,calendar,preds['idw_pm_one_total'],'Una capa · 0–30','#555555','dashed')
        line(a,calendar,preds['idw_pm_surface_upper'],'Dos capas · 0–10','#d97706')
        line(a,calendar,preds['idw_pm_surface_lower'],'Dos capas · 10–30','#007ca8')
        line(a,calendar,preds['idw_pm_surface_total'],'Dos capas · total','#8e44ad',visible=False)
        if 'gauge' in forcings:
            line(a,calendar,preds['gauge_pm_surface_lower'],'10–30 · lluvia medida','#007ca8','dotted',False)
        b=plot('Sondas: comparar fechas de subida y duración del secado, no alturas con el panel anterior','m³/m³',a.x_range)
        for ch,label,color in [('VWC_005','5 cm','#d97706'),('VWC_020','20 cm','#007ca8'),('VWC_050','50 cm · contexto','#78909c')]:
            line(b,calendar,obs[ch],label,color,visible=ch!='VWC_050')
        c=plot('Lluvia: IDW alimenta el cálculo; el pluviómetro ayuda a diagnosticar diferencias','mm/día',a.x_range)
        c.vbar(calendar,top=rain[-60:],width=60000000,color='#3182bd',alpha=.5,legend_label='IDW')
        line(c,calendar,gauge,'Pluviómetro','#c62828')
        m=next(r for r in metrics if r['code']==code and r['forcing']=='idw' and r['et']=='pm' and r['scenario']=='surface' and r['channel']=='VWC_020' and r['target']=='lower')
        def fmt(x):return 'indefinida' if x is None else f'{x:.3f}'
        note=Div(text=f'<p><b>{name}</b>: concordancia temporal con la sonda de 20 cm: '
            f'una capa r={fmt(m["reference_r"])}; capa inferior r={fmt(m["r"])} ({m["n"]} días comunes). '
            f'Cambios diarios: {fmt(m["reference_change_r"])} → {fmt(m["change_r"])}. '
            'Estos números no son porcentajes de acierto. El gráfico usa ET nueva fija; CSV incluye Hargreaves y sensibilidades. '
            f'Sondas con cobertura suficiente: 5 cm, {sum(np.isfinite(obs["VWC_005"]))}/60 días; '
            f'20 cm, {sum(np.isfinite(obs["VWC_020"]))}/60. Sin QC instrumental confirmado.</p>'
            f'<p>Variación de la capa inferior: {m["candidate_span_pp"]:.6f} puntos porcentuales. '
            f'Agua transferida abajo durante los 60 días: {fluxes["idw_pm_surface"]["transfer"]:.2f} mm. '
            + ('<b>No hay recarga calculada abajo en este periodo: un r alto de su residuo casi nulo no demuestra que funcione.</b> '
               if fluxes['idw_pm_surface']['transfer']==0 else '') + '</p>')
        panels.append(column(note,a,b,c,sizing_mode='stretch_width'))
        print(code,'complete',flush=True)
    csv_write(ROOT/'metrics.csv',metrics);csv_write(ROOT/'series.csv.gz',daily);csv_write(ROOT/'episodes.csv',episodes)
    table=['# SMI-04 · Resultado por estación', '',
        'Lluvia IDW, ET nueva fija. Comparación de una capa 0–30 cm contra capa inferior 10–30 cm.',
        'r mide forma temporal, no exactitud de agua. La amplitud y la recarga permiten detectar resultados numéricos engañosos.', '',
        '| Estación | Días comunes | r una capa | r inferior | Amplitud inferior (pp) | Recarga abajo (mm/60 días) |',
        '|---|---:|---:|---:|---:|---:|']
    for s in summaries:
        m=next(r for r in metrics if r['code']==s['code'] and r['forcing']=='idw' and r['et']=='pm'
               and r['scenario']=='surface' and r['target']=='lower')
        table.append(f'| {s["name"]} | {m["n"]} | {fmt(m["reference_r"])} | {fmt(m["r"])} | '
            f'{m["candidate_span_pp"]:.6f} | {s["fluxes_mm"]["idw_pm_surface"]["transfer"]:.2f} |')
    table.extend(['','pp = puntos porcentuales de la reserva disponible estimada. La amplitud usa los días comunes con la sonda;',
                  'el flujo de recarga integra los 60 días de simulación. No convertir esta tabla en un ranking de modelos.'])
    (ROOT/'station-results.md').write_text('\n'.join(table)+'\n')
    groups=[]
    for forcing in ('idw','gauge'):
        for et in ('hg','pm'):
            for scenario in SCENARIOS:
                for channel,target in (('VWC_005','upper'),('VWC_020','lower'),('VWC_020','total')):
                    subset=[r for r in metrics if r['forcing']==forcing and r['et']==et and r['scenario']==scenario and r['channel']==channel and r['target']==target and r['delta_r'] is not None]
                    changes=[r['change_r']-r['reference_change_r'] for r in subset if r['change_r'] is not None and r['reference_change_r'] is not None]
                    groups.append(dict(forcing=forcing,et=et,scenario=scenario,channel=channel,target=target,
                        paired_stations=len(subset),higher=sum(r['delta_r']>1e-9 for r in subset),
                        lower=sum(r['delta_r']< -1e-9 for r in subset),
                        median_delta_r=float(np.median([r['delta_r'] for r in subset])) if subset else None,
                        median_reference_r=float(np.median([r['reference_r'] for r in subset])) if subset else None,
                        median_candidate_r=float(np.median([r['r'] for r in subset])) if subset else None,
                        daily_change_pairs=len(changes),median_delta_change_r=float(np.median(changes)) if changes else None))
    provenance=[BASE/'local-inputs.json.gz',BASE/'series.csv',FIRST/'evidence.json.gz',FIRST/'expanded-stations.json.gz',
                ROOT/'PROTOCOL.md',ROOT/'model.py',ROOT/'analyse.py',ROOT/'test_model.py',*frozen]
    (ROOT/'summary.json').write_text(json.dumps(clean(dict(stations=summaries,comparisons=groups,metric_rows=len(metrics),
        daily_rows=len(daily),episode_rows=len(episodes),sha256={str(p.relative_to(ROOT.parent)):sha(p) for p in provenance})),ensure_ascii=False,indent=2,allow_nan=False))
    head=Div(text='<h1>SMI-04 · Una capa frente a dos</h1><p>Ensayo local, 22 estaciones. 21 julio–18 septiembre 2026. '
        '<b>Entrada principal: lluvia IDW.</b> No se han cambiado el mapa ni el worker.</p>'
        '<p>Busca lluvias pequeñas y grandes abajo; mira si la sonda a 20 cm responde; compara con la curva azul superior. '
        'La división debe evitar recargar abajo demasiado pronto, sin perder las recargas que sí se observan. '
        'No compares los porcentajes de arriba con m³/m³ de abajo. No se validan litros ni bosques.</p>'
        '<p>Capacidad uniforme por espesor, transferencia inmediata por exceso, evaporación superficial. '
        'Es una hipótesis de ensayo, no un cálculo de la velocidad de infiltración. Haz clic en una leyenda para mostrar/ocultar series.</p>')
    default=next(i for i,s in enumerate(summaries) if s['code']=='BDS')
    selector=Select(title='Estación',name='station_selector',value=str(default),options=[(str(i),s['name']) for i,s in enumerate(summaries)],width=350)
    for i,p in enumerate(panels):p.visible=i==default
    selector.js_on_change('value',CustomJS(args=dict(panels=panels),code='panels.forEach((p,i)=>{p.visible=i===Number(cb_obj.value);});'))
    (ROOT/'comparison.html').write_text(file_html(column(head,selector,*panels,sizing_mode='stretch_width'),INLINE,'SMI-04 · dos capas'))
    print(json.dumps(clean(dict(stations=len(summaries),metrics=len(metrics),days=len(daily),episodes=len(episodes),
         primary=[g for g in groups if g['forcing']=='idw' and g['scenario']=='surface'])),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
