"""Offline SMI-03 factorial baseline. No fitting, network, HA or worker access."""
import collections
import csv
from datetime import date, datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

import numpy as np
from scipy.stats import pearsonr, spearmanr
from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, CustomJS, Div, HoverTool, Range1d, Select, TabPanel
from bokeh.plotting import figure
from bokeh.resources import INLINE

ROOT = Path(__file__).resolve().parent
FIRST = ROOT.parent / 'contrast-2026-09-19'
def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))

LOCAL = read(ROOT / 'local-inputs.json.gz')
for filename in ('mushroom_map_water_physics.py', 'mushroom_soil_water_state.py',
                 'mushroom_climatic_water_balance.py'):
    assert hashlib.sha256((ROOT/'snapshot'/'rainmapper_core'/filename).read_bytes()).hexdigest() == LOCAL['code_sha256'][filename]
sys.path.insert(0, str(ROOT/'snapshot'))
from rainmapper_core.mushroom_climatic_water_balance import hargreaves_reference_evapotranspiration_mm as hargreaves
from rainmapper_core.mushroom_map_water_physics import penman_monteith, simulate_reference_store
from rainmapper_core.mushroom_soil_water_state import simulate_bounded_bucket

def normal(name):
    return ''.join(c for c in unicodedata.normalize('NFD',name.lower()) if c.isalnum())

EXPANDED = read(FIRST/'expanded-stations.json.gz')
OLD = {p['station']:p for p in read(FIRST/'evidence.json.gz')['icgc']['points']}
OBS = {normal(p['name']): p if 'rows' in p else dict(p,rows=OLD[p['station']]['rows'])
       for p in EXPANDED['points']}
META = {p['code']:p for p in json.loads((ROOT/'station-metadata.json').read_text())}
METRICS, SERIES, SUMMARY, PANELS = [], [], [], []

def finite(v):
    return isinstance(v,(int,float,np.floating)) and np.isfinite(v)

def sensor(v):
    try:
        v=float(v)
        return v if np.isfinite(v) and 0<v<=1 else np.nan
    except (TypeError,ValueError):
        return np.nan

def rain_value(v):
    try:
        v=float(v)
        return v if np.isfinite(v) and v>=0 else np.nan
    except (TypeError,ValueError):
        return np.nan

def correlation(a,b,minimum=30):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    ok=np.isfinite(a)&np.isfinite(b)
    a,b=a[ok],b[ok]
    if len(a)<minimum or np.ptp(a)==0 or np.ptp(b)==0:
        return {'n':len(a),'pearson':None,'spearman':None}
    return {'n':len(a),'pearson':float(pearsonr(a,b).statistic),
            'spearman':float(spearmanr(a,b).statistic)}

def simulate(rain,et,capacity,rule):
    n=len(rain);values=np.full(n,np.nan);max_error=0.; start=0
    while start<n:
        if not finite(rain[start]) or not finite(et[start]):
            start+=1;continue
        end=start
        while end<n and finite(rain[end]) and finite(et[end]):end+=1
        def run(initial):
            if rule=='simple':
                return simulate_bounded_bucket(rain_mm=rain[start:end],
                    reference_evapotranspiration_mm=et[start:end],capacity_mm=capacity,
                    initial_storage_mm=initial)
            return simulate_reference_store(rain[start:end],et[start:end],capacity,initial)
        dry,wet=run(0),run(capacity)
        max_error=max(max_error,dry['mass_error_max_mm'],wet['mass_error_max_mm'])
        for k,(lo,hi) in enumerate(zip(dry['storage_mm'],wet['storage_mm'])):
            if k+1>=90 and hi-lo<=max(1.,.01*capacity):
                values[start+k]=100*(lo if rule=='simple' else (lo+hi)/2)/capacity
        start=end
    assert max_error<1e-7
    assert all(0<=v<=100 for v in values if np.isfinite(v))
    return values[-60:],max_error

def plot(title,ylabel,x_range=None):
    p=figure(title=title,height=235,sizing_mode='stretch_width',x_axis_type='datetime',
             tools='pan,wheel_zoom,box_zoom,reset,save',**({'x_range':x_range} if x_range else {}))
    p.yaxis.axis_label=ylabel
    return p

def line(p,dates,values,label,color,dash='solid'):
    source=ColumnDataSource(dict(date=dates,value=values))
    r=p.line('date','value',source=source,line_width=2,line_color=color,line_dash=dash,legend_label=label)
    p.add_tools(HoverTool(renderers=[r],tooltips=[('Serie',label),('Fecha','@date{%F}'),('Valor','@value{0.000}')],formatters={'@date':'datetime'},mode='vline'))
    p.legend.click_policy='hide';p.legend.label_text_font_size='10px'

for point in LOCAL['points']:
    code,name=point['code'],point['name'];inputs=point['inputs'];data=inputs['interpolated']
    dates=data['daily_dates'];last=dates[-60:];capacity=point['capacity_mm']
    assert len(dates)==365 and len(set(dates))==365
    assert all((date.fromisoformat(b)-date.fromisoformat(a)).days==1 for a,b in zip(dates,dates[1:]))
    rows=OBS[normal(name)]['rows'];by_day=collections.defaultdict(list);timestamps=set()
    for row in rows:
        instant=datetime.fromisoformat(row['TmStamp'])
        assert instant not in timestamps
        timestamps.add(instant);by_day[instant.date().isoformat()].append(row)
    channels=['VWC_005','VWC_020','VWC_050']
    observed={};zero_counts={};daily_counts={}
    for channel in channels:
        observed[channel]=[];daily_counts[channel]=[];zero_counts[channel]=0
        for day in last:
            vals=[sensor(r.get(channel)) for r in by_day[day]]
            zero_counts[channel]+=sum(r.get(channel) in (0,0.,'0','0.0') for r in by_day[day])
            valid=[v for v in vals if finite(v)]
            daily_counts[channel].append(len(valid))
            observed[channel].append(float(np.mean(valid)) if len(valid)>=44 else np.nan)
    measured=[]
    for day in last:
        rs=by_day[day];values=[rain_value(r.get('Pluja_Tot')) for r in rs]
        expected={f'{h:02}:{m:02}:00' for h in range(24) for m in (0,30)}
        complete=len(rs)==48 and {datetime.fromisoformat(r['TmStamp']).time().isoformat() for r in rs}==expected and all(finite(v) for v in values)
        measured.append(sum(values) if complete else np.nan)
    et_old=[];et_new=[]
    for i,day in enumerate(dates):
        lo,hi=data['daily_temp_min_idw_c'][i],data['daily_temp_max_idw_c'][i]
        old=new=None
        if finite(lo) and finite(hi) and -80<=lo<=hi<=60:
            old=hargreaves(date.fromisoformat(day),point['lat'],lo,hi)
            hrlo,hrhi=data['daily_humidity_min_idw_pct'][i],data['daily_humidity_max_idw_pct'][i]
            wind=inputs['wind_u2_m_s'][i]
            if finite(hrlo) and finite(hrhi) and 0<=hrlo<=hrhi<=100:
                new=penman_monteith(date.fromisoformat(day),point['lat'],point['altitude_m'],lo,hi,hrlo,hrhi,
                                    wind if finite(wind) and 0<=wind<=60 else 2.)
            else:new=old
        et_old.append(old);et_new.append(new)
    # Verify reconstruction of ET and both existing map curves before drawing conclusions.
    stored=point['map_weather']['water_balance']
    assert np.allclose(np.array(et_new[-60:],dtype=float),np.array(stored['et0_mm'],dtype=float),atol=1e-6,equal_nan=True)
    rain_idw=data['daily_rain_idw_mm']
    variants={'idw':rain_idw}
    if all(finite(v) for v in measured):variants['gauge_recent']=rain_idw[:-60]+measured
    predictions={};mass_error=0.
    for forcing,rain in variants.items():
        for rule in ('simple','regulated'):
            for method,et in (('hg',et_old),('pm',et_new)):
                key=f'{forcing}_{rule}_{method}'
                predictions[key],error=simulate(rain,et,capacity,rule)
                mass_error=max(mass_error,error)
    for key,reference in (('idw_simple_hg','smi_legacy_pct'),('idw_regulated_pm','smi_pct')):
        assert np.allclose(predictions[key],np.array(stored[reference],dtype=float),atol=.00051,equal_nan=True),(code,key)
    for channel,obs in observed.items():
        # Common dates for the four model combinations at a fixed rain forcing.
        for forcing in variants:
            keys=[k for k in predictions if k.startswith(forcing+'_')]
            common=np.isfinite(np.asarray(obs))
            for k in keys:common &= np.isfinite(predictions[k])
            y=np.where(common,obs,np.nan)
            for k in keys:
                x=np.where(common,predictions[k],np.nan)
                result=dict(code=code,name=name,channel=channel,model=k,**correlation(x,y))
                result.update(change_r=correlation(np.diff(x),np.diff(y),minimum=29)['pearson'],
                              first30_r=correlation(x[:30],y[:30],minimum=20)['pearson'],
                              last30_r=correlation(x[30:],y[30:],minimum=20)['pearson'])
                METRICS.append(result)
    paired_rain=[i for i,v in enumerate(measured) if finite(v) and finite(rain_idw[-60+i])]
    summary=dict(code=code,name=name,capacity_mm=capacity,altitude_m=point['altitude_m'],
        pdf_altitude_m=META[code]['pdf_utm']['Z'],gauge_complete_days=sum(finite(v) for v in measured),
        rain_common_days=len(paired_rain),rain_gauge_common_mm=sum(measured[i] for i in paired_rain),
        rain_idw_common_mm=sum(rain_idw[-60+i] for i in paired_rain),sensor_zero_counts=zero_counts,
        sensor_valid_days={c:sum(finite(v) for v in vs) for c,vs in observed.items()},
        map_smi_valid_days=int(np.isfinite(predictions['idw_regulated_pm']).sum()),mass_error_max_mm=mass_error,
        model_count=len(predictions))
    SUMMARY.append(summary)
    for i,day in enumerate(last):
        SERIES.append(dict(code=code,name=name,date=day,rain_idw=rain_idw[-60+i],rain_gauge=measured[i],
                           **{c:v[i] for c,v in observed.items()},**{k:v[i] for k,v in predictions.items()}))
    calendar=[datetime.fromisoformat(d) for d in last]
    top=plot(name+' · reserva calculada para 0–30 cm','SMI disponible (%)');top.y_range=Range1d(0,100)
    line(top,calendar,predictions['idw_simple_hg'],'Simple · ET anterior','#d97706')
    line(top,calendar,predictions['idw_regulated_pm'],'Regulada · ET nueva','#007ca8')
    if 'gauge_recent' in variants:
        line(top,calendar,predictions['gauge_recent_regulated_pm'],'Regulada · lluvia medida','#333333','dashed')
    middle=plot('Sondas: observar cuándo suben y cómo se secan; las alturas no equivalen al SMI','m³/m³',top.x_range)
    for c,label,color in [('VWC_005','5 cm','#689f38'),('VWC_020','20 cm','#7b1fa2'),('VWC_050','50 cm · contexto','#78909c')]:
        line(middle,calendar,observed[c],label,color)
    bottom=plot('Entrada: comparar primero la lluvia medida con la estimada','mm/día',top.x_range)
    bottom.vbar(calendar,top=rain_idw[-60:],width=60000000,color='#3182bd',alpha=.5,legend_label='IDW')
    line(bottom,calendar,measured,'Pluviómetro · días completos','#c62828')
    note=Div(text=f'<p><b>{name}</b> · Lluvia medida completa: {summary["gauge_complete_days"]}/60 días. '
                   f'Sondas con cobertura suficiente a 5/20 cm: {summary["sensor_valid_days"]["VWC_005"]}/{summary["sensor_valid_days"]["VWC_020"]} días. '
                   'Huecos y ceros dudosos de sondas no se representan como humedad cero. '
                   'La línea discontinua, cuando existe, cambia solo la lluvia de estos 60 días; la historia anterior sigue siendo IDW.</p>')
    PANELS.append(TabPanel(title=name,child=column(note,top,middle,bottom,sizing_mode='stretch_width')))

def clean(obj):
    if isinstance(obj,np.generic):return clean(obj.item())
    if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj,list):return [clean(v) for v in obj]
    if isinstance(obj,(float,np.floating)) and not np.isfinite(obj):return None
    return obj

for filename,rows in [('metrics.csv',METRICS),('series.csv',SERIES)]:
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/filename).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(clean(rows))
(ROOT/'summary.json').write_text(json.dumps(clean(SUMMARY),ensure_ascii=False,indent=2,allow_nan=False))
head=Div(text='<h1>SMI · comparación ampliada en 22 estaciones</h1><p>21 julio–18 septiembre 2026. '
             'Modelos fijados, sin ajustar parámetros. Red ICGC descrita como emplazamientos de viñedo: no valida el bosque.</p>'
             '<p><b>Cómo leerlo:</b> empieza abajo por la lluvia; después mira si las sondas se humedecen y cuándo; '
             'por último comprueba si el cálculo reproduce esa evolución. Compara fechas y duración, no alturas entre paneles. '
             'Las medias diarias pueden esconder respuestas breves. Los valores absolutos de litros no están validados.</p>')
selector=Select(title='Estación',value='0',options=[(str(i),p.title) for i,p in enumerate(PANELS)],width=350)
children=[p.child for p in PANELS]
for i,p in enumerate(children):p.visible=i==0
selector.js_on_change('value',CustomJS(args=dict(panels=children),code='panels.forEach((p,i) => { p.visible = i === Number(cb_obj.value); });'))
(ROOT/'comparison.html').write_text(file_html(column(head,selector,*children,sizing_mode='stretch_width'),INLINE,'SMI · muestra ampliada'))
print('Completed',len(SUMMARY),'stations;',len(METRICS),'comparisons;',len(SERIES),'daily rows')
for p in SUMMARY:
    values={m['model']:m['pearson'] for m in METRICS if m['code']==p['code'] and m['channel']=='VWC_020'}
    print(p['code'],p['name'],'rain days',p['gauge_complete_days'],{k:round(v,3) if v is not None else None for k,v in values.items()})
