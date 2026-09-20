import json,shutil
from pathlib import Path
O=Path(__file__).resolve().parents[2]/'data'
load=lambda n:json.loads((O/n).read_text())
V=O/'viewer';V.mkdir(exist_ok=True)
assets=Path('local-apps/gbif/data/snapshot-catalunya-20120619-20260916-full/viewer')
for n in ('maplibre-gl.js','maplibre-gl.css'):shutil.copy2(assets/n,V/n)
source=Path('rainmapper_core/viewers/maplibre-viewer/app.js').read_text()
styles=source.split('const baseStyles = ',1)[1].split('\nlet currentStyle',1)[0].strip()
assert styles.startswith('[') and styles.endswith(';')
(V/'base-styles.js').write_text('const COVERAGE_BASE_STYLES = '+styles+'\n')
data={'stations':load('stations.json'),'gaps':[g for g in load('grid.json') if g['nearest_km']>8],'candidates':load('candidates.json'),'searches':load('search-points.json')}
template='''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cobertura meteorológica de Catalunya</title><link rel="stylesheet" href="maplibre-gl.css">
<style>*{box-sizing:border-box}body{margin:0;font:14px system-ui;color:#173145;height:100dvh;display:flex;flex-direction:column}header{padding:10px 16px;background:#f3f7fa}h1{font-size:20px;margin:0 0 4px}p{margin:5px 0}nav{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-top:9px}select,button{padding:6px}main{flex:1;min-height:0;position:relative}#map{position:absolute;inset:0}.maplibregl-popup-content{max-height:65vh;overflow:auto;font:14px system-ui;padding:16px}footer{padding:5px 12px;font-size:12px}a{color:#006fa5}#status{font-weight:600}.legend{line-height:1.7}</style>
<header><h1>Cobertura meteorológica · Catalunya</h1><p>Base local del 17/09/2026 a las 11:31. Exploración de candidatas Wunderground del 18/09. Ninguna está aprobada.</p>
<nav><label>Candidatas <select id="selection"><option value="short">12 prioritarias para revisar</option><option value="new">143 nuevas en Catalunya</option><option value="all">178 identificadas (incluye conocidas y excluidas)</option></select></label><label>Fondo <select id="basemap"></select></label><label><input id="stations" type="checkbox" checked> Estaciones actuales</label><label><input id="gaps" type="checkbox" checked> Huecos &gt;8 km</label><label><input id="searches" type="checkbox"> Puntos consultados</label><button id="fit">Encuadrar Catalunya</button><a href="../candidates.csv">CSV completo</a><span id="status"></span></nav></header>
<main><div id="map"></div><div id="map-error" role="status" hidden style="position:absolute;bottom:35px;left:12px;right:12px;padding:8px;background:#fff3cd;color:#513b00;z-index:2">No se ha podido cargar parte del fondo. Prueba otro fondo.</div></main><footer class="legend">Estaciones: <span style="color:#0072b2">● Meteocat</span> · <span style="color:#009e73">● AEMET</span> · <span style="color:#6d4c9c">● Meteoclimatic</span> · <span style="color:#d55e00">● Wunderground</span> | Amarillo: candidatas prioritarias | Huecos: naranja &gt;8 km; rojo &gt;10 km. Distancias horizontales; sin validar calidad ni relieve. Cartografía por Internet.</footer>
<script src="maplibre-gl.js"></script><script src="base-styles.js"></script><script>const D=__DATA__;
const esc=v=>String(v??'No informado').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={'esri-satellite-vector':'Satélite+','esri-hybrid':'Híbrido','opentopomap':'Topográfico','openfreemap-liberty':'Liberty'};
for(const style of COVERAGE_BASE_STYLES)document.getElementById('basemap').append(new Option(labels[style.id]||style.label,style.id));
const styleValue=style=>style.url||structuredClone(style.style);
const map=new maplibregl.Map({container:'map',bounds:[[0.1,40.5],[3.4,42.9]],fitBoundsOptions:{padding:35},style:styleValue(COVERAGE_BASE_STYLES[0])});
map.on('error',()=>{document.getElementById('map-error').hidden=false});
document.getElementById('basemap').onchange=e=>{document.getElementById('map-error').hidden=true;map.setStyle(styleValue(COVERAGE_BASE_STYLES.find(s=>s.id===e.target.value)),{diff:false})};
map.addControl(new maplibregl.NavigationControl(),'top-left');map.addControl(new maplibregl.ScaleControl());
const fc=(rows,lon='lon',lat='lat')=>({type:'FeatureCollection',features:rows.map(p=>({type:'Feature',geometry:{type:'Point',coordinates:[p[lon],p[lat]]},properties:p}))});
const colors=['match',['get','source'],'Meteocat','#0072b2','AEMET','#009e73','Meteoclimatic','#6d4c9c','#d55e00'];
function chosen(){const v=document.querySelector('#selection').value;return D.candidates.filter(c=>v==='all'||(v==='new'?c.status==='nueva':c.rank!==null))}
function update(){const c=chosen();map.getSource('candidates')?.setData(fc(c,'longitude','latitude'));document.querySelector('#status').textContent=c.length+' candidatas visibles'}
function popup(layer,format){map.on('click',layer,e=>{const f=e.features[0];new maplibregl.Popup({maxWidth:'360px'}).setLngLat(f.geometry.coordinates).setHTML(format(f.properties)).addTo(map)});map.on('mouseenter',layer,()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave',layer,()=>map.getCanvas().style.cursor='')}
map.on('style.load',()=>{
 for(const [id,rows] of [['stations',D.stations],['gaps',D.gaps],['searches',D.searches]])map.addSource(id,{type:'geojson',data:fc(rows)});
 map.addSource('candidates',{type:'geojson',data:fc(chosen(),'longitude','latitude')});
 map.addLayer({id:'gaps',type:'circle',source:'gaps',paint:{'circle-radius':5,'circle-color':['case',['>', ['get','nearest_km'],10],'#d73027','#ffad33'],'circle-opacity':0.45}});
 map.addLayer({id:'stations',type:'circle',source:'stations',paint:{'circle-radius':4,'circle-color':colors,'circle-stroke-color':'white','circle-stroke-width':1}});
 map.addLayer({id:'searches',type:'circle',source:'searches',layout:{visibility:'none'},paint:{'circle-radius':9,'circle-color':'transparent','circle-stroke-color':'black','circle-stroke-width':2}});
 map.addLayer({id:'candidates',type:'circle',source:'candidates',paint:{'circle-radius':8,'circle-color':['case',['!=',['get','rank'],null],'#ffdd38','#9aa3ad'],'circle-stroke-color':'#252525','circle-stroke-width':2}});
 for(const id of ['stations','gaps','searches'])map.setLayoutProperty(id,'visibility',document.getElementById(id).checked?'visible':'none');
 update();
});
 popup('stations',p=>`<b>${esc(p.name)}</b><p>${esc(p.source)} · ${esc(p.id)}</p><p>Altitud publicada: ${esc(p.altitude_m)} m</p><p>Días con dato de lluvia en ventana: ${esc(p.rain_days_7)}/7</p><p>Última lectura publicada: ${esc(p.last_reading)}</p><p>Base local; disponibilidad no equivale a calidad.</p>`);
 popup('gaps',p=>`<b>Hueco de ${esc(p.municipality)}</b><p>Estación más cercana: ${esc(p.nearest_km)} km (${esc(p.nearest_name)}, ${esc(p.nearest_source)})</p><p>Cuarta ubicación distinta: ${esc(p.fourth_location_km)} km</p><p>Punto de malla de 2 km, no límite exacto de una zona.</p>`);
 popup('candidates',p=>`<b>${p.rank?'Prioridad '+esc(p.rank)+' · ':''}${esc(p.stationId)}</b><p>${esc(p.stationName)} · ${esc(p.municipality)}</p><p>Estado: ${esc(p.status)}. Pendiente de revisión.</p><p>QC publicado por WU: ${esc(p.qcStatus)} (1: aprobado por WU; 0: fallido; −1: no comprobado). No es nuestra aprobación.</p><p>Distancia a la red actual: ${esc(p.nearest_existing_km)} km · ${esc(p.nearest_existing_name)} (${esc(p.nearest_existing_source)})</p><p>Mejoraría ≥2 km la distancia en ${esc(p.gap_points_improved_2km)} puntos de malla cuyo hueco inicial supera 8 km.</p><p>Antigüedad de updateTimeUtc: ${esc(p.age_hours)} h. No acredita continuidad del pluviómetro.</p><p><a target="_blank" rel="noopener" href="https://www.wunderground.com/dashboard/pws/${encodeURIComponent(p.stationId)}">Ficha Wunderground</a></p>`);
 for(const id of ['stations','gaps','searches'])document.getElementById(id).onchange=e=>{if(map.getLayer(id))map.setLayoutProperty(id,'visibility',e.target.checked?'visible':'none')};
 document.getElementById('selection').onchange=update;
document.getElementById('fit').onclick=()=>map.fitBounds([[0.1,40.5],[3.4,42.9]],{padding:35});
</script></html>'''
(V/'index.html').write_text(template.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')))
print('viewer',V/'index.html')
