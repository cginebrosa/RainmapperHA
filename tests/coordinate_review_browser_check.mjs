// Exercise the actual review component in Chrome/MapLibre with an isolated API fixture.
// No operational data or authentication files are used; the temporary profile is removed.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {once} from 'node:events';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const app = await fs.readFile(path.join(root, 'rainmapper_core/viewers/maplibre-viewer/app.js'), 'utf8');
const component = app.slice(app.indexOf('function coordinateNotice('), app.indexOf('function numericProperty('));
const paint = app.slice(app.indexOf('      "circle-radius": ["get", "marker_radius"]'),
  app.indexOf('\n    },\n  });', app.indexOf('      "circle-radius": ["get", "marker_radius"]')));
const style = await fs.readFile(path.join(root, 'rainmapper_core/viewers/maplibre-viewer/style.css'), 'utf8');
const translations = JSON.parse(await fs.readFile(path.join(root, 'rainmapper_core/viewers/maplibre-viewer/translations.json'), 'utf8')).es;
const index = await fs.readFile(path.join(root, 'rainmapper_core/viewers/maplibre-viewer/index.html'), 'utf8');
const header = index.match(/<header class="topbar">[\s\S]*?<\/header>/)[0]
  .replace('Loading map data...', '<span class="summary-main">21 días · 2013 estaciones · 2105 total</span><span class="summary-filter">Mín: 1 mm</span>')
  .replace('<time id="generated-at">-</time>', '<time id="generated-at">07/11/26 - 16:53</time>')
  .replace('id="signed-in-user" hidden', 'id="signed-in-user"')
  .replace('<strong id="signed-in-user-value">-</strong>', '<strong id="signed-in-user-value">carlos (admin)</strong>');
const finderPanel = index.match(/<section id="coordinate-finder"[\s\S]*?<\/section>/)[0];
const entry = {source:'meteoclimatic', station_code:'ESCAT4300000043003B', accepted:{lat:41.12,lon:1.27},
  received:{lat:41.2,lon:1.45}, distance_km:17.499, first_seen:'2026-11-04T05:00:00+00:00', revision:'candidate-1', can_accept:true};
let accepted = [], conflict = false, requests = 0;
const html = `<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">
<style>${style}#notice{position:fixed;top:140px;right:70px;max-width:320px;z-index:2;background:#18212b;color:white;padding:12px}#notice:empty{display:none}</style>
${header}
<main><div id="map"></div>${finderPanel}</main><div id="notice"></div><div id="map-settings" hidden></div><script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script>
const AUTH_REQUIRED=true, currentLanguage='es', labels=${JSON.stringify(translations)};
let authState={role:'admin'}, activeStationPopupProperties={Source:'Meteoclimatic','Codi Estació':'ESCAT4300000043003B',coordinate_exception:true,coordinate_since:${JSON.stringify(entry.first_seen)}};
const t=(key,params={})=>Object.entries(params).reduce((s,[k,v])=>s.replaceAll('{'+k+'}',v),labels[key]||key), authFetch=(url,options)=>fetch(url,options);
let currentPopup=null;
const station=(source,code,name,lon,lat,held=true)=>({type:'Feature',geometry:{type:'Point',coordinates:[lon,lat]},properties:{Source:source,'Codi Estació':code,'Estació':name,coordinate_exception:held,coordinate_since:${JSON.stringify(entry.first_seen)}}});
let currentVisibleFeatures=[station('Meteoclimatic','ESCAT4300000043003B','Tarragona-Fortí St.Jordi',1.27,41.12),station('AEMET','AEMET:123','Estación seca',2,42),station('Meteocat','XEMA1','Sin incidencia',1,41,false)];
// Only the first station is rendered: the finder must also locate filtered-out stations.
function closeSecondaryPanels(){closeCoordinateFinder();}
function openStationPopup(feature){currentPopup?.remove();activeStationPopupProperties=feature.properties;let closed=[];currentPopup={on:(type,callback)=>closed.push(callback),remove:()=>{closed.forEach(fn=>fn());currentPopup=null;document.querySelector('#notice').replaceChildren();}};refreshCurrentStationPopup();}
function refreshCurrentStationPopup(){document.querySelector('#notice').innerHTML=currentPopup || !window.ready ? coordinateNotice(activeStationPopupProperties) : '';}
const map=new maplibregl.Map({container:'map',style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#192a35'}}]},center:[1.27,41.12],zoom:10});
const NativeMarker=maplibregl.Marker;window.fixtureMarkers=[];
maplibregl.Marker=class extends NativeMarker{constructor(options){super(options);window.fixtureMarkers.push({marker:this,anchor:options.anchor});}};
map.on('load',()=>{map.addSource('stations',{type:'geojson',data:{type:'FeatureCollection',features:[{type:'Feature',geometry:{type:'Point',coordinates:[1.27,41.12]},properties:{rain_color:'#aaff00',marker_radius:8,coordinate_exception:true}}]}});map.addLayer({id:'station-circles',type:'circle',source:'stations',paint:{${paint}}});renderCoordinateFinder();updateCoordinateFinder();window.ready=true;});
${component}
refreshCurrentStationPopup();
</script>`;
const server = http.createServer(async (req,res) => {
  if (req.url === '/') {res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html);return;}
  res.setHeader('Content-Type','application/json');
  if (req.url.startsWith('/api/weather/coordinates')) {
    requests++;
    if(req.method==='POST') {
      let body='';for await(const chunk of req)body+=chunk;
      const payload=JSON.parse(body);
      if(conflict){res.statusCode=409;res.end(JSON.stringify({error:'La ubicación propuesta ha cambiado. Revisa de nuevo.'}));return;}
      accepted.push(payload);entry.approval={username:'fixture-admin'};
      res.end(JSON.stringify({ok:true,status:'pending'}));return;
    }
    res.end(JSON.stringify(entry));return;
  }
  res.statusCode=404;res.end('{}');
});
const temporary=await fs.mkdtemp(path.join(os.tmpdir(),'rainmapper-coordinate-browser-'));
let chrome,ws,serial=0;const pending=new Map(),errors=[];
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
async function evaluate(expression){const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
async function until(expression){for(let i=0;i<150;i++){if(await evaluate(expression))return;await pause(200);}throw Error('Timeout '+expression);}
async function screenshot(name){if(process.env.COORDINATE_SCREENSHOT_DIR){const result=await send('Page.captureScreenshot',{format:'png'});await fs.writeFile(path.join(process.env.COORDINATE_SCREENSHOT_DIR,name+'.png'),Buffer.from(result.data,'base64'));}}
async function assertReviewGeometry(){
  await until('!map.isMoving()');
  const geometry=await evaluate(`Array.from(document.querySelectorAll('.coordinate-marker')).map(el=>{
    const r=el.getBoundingClientRect(),m=map.getContainer().getBoundingClientRect();
    const fixture=window.fixtureMarkers.find(({marker})=>marker.getElement()===el),p=map.project(fixture.marker.getLngLat());
    return {dx:Math.abs(r.left+r.width/2-m.left-p.x),dy:Math.abs(r.bottom-m.top-p.y),
      arrow:getComputedStyle(el,'::after').borderTopWidth,anchor:fixture.anchor};})`);
  assert.equal(geometry.length,2);
  for(const point of geometry){assert.equal(point.anchor,'bottom');assert.equal(point.arrow,'18px');assert.ok(point.dx<2 && point.dy<2,JSON.stringify(point));}
  assert.equal(await evaluate("getComputedStyle(document.querySelector('.coordinate-dialog p')).color"),'rgb(240, 244, 248)');
  assert.ok(await evaluate("document.querySelector('.coordinate-dialog p').getBoundingClientRect().height > 50"));
}
try {
  server.listen(0,'127.0.0.1');await once(server,'listening');
  const profile=path.join(temporary,'chrome');
  chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
    '--headless','--no-first-run','--disable-background-networking','--use-angle=swiftshader','--enable-unsafe-swiftshader',
    '--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
  let debug;for(let i=0;i<100;i++){try{debug=(await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await pause(100);}}
  assert.ok(debug,'Chrome started');
  const pages=await(await fetch(`http://127.0.0.1:${debug}/json/list`)).json();
  ws=new WebSocket(pages.find(page=>page.type==='page').webSocketDebuggerUrl);await once(ws,'open');
  ws.addEventListener('message',event=>{const message=JSON.parse(event.data);if(message.id){const task=pending.get(message.id);pending.delete(message.id);message.error?task.reject(message.error):task.resolve(message.result);}else if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails);});
  await send('Runtime.enable');await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:`http://127.0.0.1:${server.address().port}/`});await until('window.ready===true');
  assert.match(await evaluate("document.querySelector('#coordinate-finder-toggle').textContent"),/2$/);
  // The actual header must keep its height, and the finder disappears at the
  // same breakpoint as the narrow header, including an already-open panel.
  for (const width of [1280, 768, 641, 640, 390]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
    const layout = await evaluate(`(() => {
      const button=document.querySelector('#coordinate-finder-toggle'), header=document.querySelector('.topbar');
      const shown=header.getBoundingClientRect().height, b=button.getBoundingClientRect(), h=document.querySelector('h1').getBoundingClientRect();
      const display=getComputedStyle(button).display;
      button.hidden=true;const hidden=header.getBoundingClientRect().height;button.hidden=false;
      return {shown,hidden,display,sameLine:Math.abs((b.top+b.bottom-h.top-h.bottom)/2)<1,
        fits:b.right<=document.querySelector('.generated').getBoundingClientRect().left,
        overflow:document.documentElement.scrollWidth>innerWidth};
    })()`);
    assert.equal(layout.shown,layout.hidden,JSON.stringify({width,layout}));
    assert.equal(layout.overflow,false);
    if (width<=640) assert.equal(layout.display,'none');
    else {assert.notEqual(layout.display,'none');assert.ok(layout.sameLine && layout.fits,JSON.stringify({width,layout}));}
  }
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate('map.resize();void 0');
  await evaluate("document.querySelector('#coordinate-finder-toggle').click()");
  assert.equal(await evaluate("document.querySelectorAll('#coordinate-finder-results button').length"),2);
  assert.equal(await evaluate("document.querySelectorAll('#coordinate-finder-results h3').length"),2);
  await screenshot('finder-desktop');
  await evaluate("document.querySelector('#coordinate-finder-query').value='seca';updateCoordinateFinder();document.querySelector('#coordinate-finder-results button').click()");
  assert.equal(await evaluate("activeStationPopupProperties['Codi Estació']"),'AEMET:123');
  assert.equal(await evaluate("document.querySelectorAll('.coordinate-marker').length"),1);
  assert.equal(await evaluate("map.getSource('stations')._data.features.length"),1);
  await evaluate("document.querySelector('#coordinate-finder-toggle').click();document.querySelector('#coordinate-finder-query').value='forti';updateCoordinateFinder()");
  assert.equal(await evaluate("document.querySelectorAll('#coordinate-finder-results button').length"),1);
  await evaluate("document.querySelector('#coordinate-finder-results button').click()");
  assert.equal(await evaluate("document.querySelectorAll('.coordinate-marker').length"),1);
  await evaluate("document.querySelector('[data-coordinate-review]').click()");
  await until("document.querySelectorAll('.coordinate-marker').length===2 && !document.querySelector('.coordinate-actions button:last-child').disabled");
  assert.match(await evaluate("document.querySelector('.coordinate-dialog').innerText"),/41\.12000, 1\.27000/);
  assert.match(await evaluate("document.querySelector('.coordinate-dialog').innerText"),/17\.499 km/);
  await assertReviewGeometry();await screenshot('review-desktop');
  await evaluate("document.querySelectorAll('.coordinate-navigation button')[1].click()");
  await until('!map.isMoving() && map.getZoom()>14.5');
  await evaluate("document.querySelectorAll('.coordinate-navigation button')[2].click()");
  await assertReviewGeometry();
  assert.deepEqual(await evaluate("map.getPaintProperty('station-circles','circle-stroke-width')"),['case',['==',['get','coordinate_exception'],true],3,1.2]);
  await evaluate("document.querySelector('.coordinate-actions button:last-child').click()");
  await until("document.querySelector('.coordinate-dialog').innerText.includes('pendiente del siguiente runner')");
  assert.equal(accepted.length,1);assert.equal(accepted[0].revision,'candidate-1');
  assert.deepEqual(await evaluate("map.getSource('stations')._data.features[0].geometry.coordinates"),[1.27,41.12]);
  await evaluate("coordinateDialog.close()");await until("document.querySelectorAll('.coordinate-marker').length===0");
  entry.approval=null;conflict=true;
  await evaluate("reviewStationCoordinates(activeStationPopupProperties)");await until("!document.querySelector('.coordinate-actions button:last-child').disabled");
  await evaluate("document.querySelector('.coordinate-actions button:last-child').click()");await until("document.querySelector('.coordinate-dialog').innerText.includes('ha cambiado')");
  assert.equal(accepted.length,1);
  await evaluate("coordinateDialog.close()");
  // Exercise a distant proposal like the user's screenshot, on a narrow screen.
  entry.received={lat:49.98,lon:2.28};entry.distance_km=987;conflict=false;
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
  await evaluate("map.resize();reviewStationCoordinates(activeStationPopupProperties)");
  await until("document.querySelectorAll('.coordinate-marker').length===2 && !document.querySelector('.coordinate-actions button:last-child').disabled");
  await assertReviewGeometry();await screenshot('review-mobile');
  assert.ok(await evaluate("Array.from(document.querySelectorAll('.coordinate-marker')).every(el=>{const r=el.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth;})"));
  await evaluate("coordinateDialog.close()");
  assert.equal(await evaluate("getComputedStyle(document.querySelector('#coordinate-finder-toggle')).display"),'none');
  await screenshot('header-mobile');
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate("map.resize();document.querySelector('#coordinate-finder-toggle').click();document.querySelector('#coordinate-finder-query').value='';updateCoordinateFinder()");
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
  assert.equal(await evaluate("getComputedStyle(document.querySelector('#coordinate-finder')).display"),'none');
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate('map.resize();void 0');
  await evaluate("document.querySelector('#coordinate-finder-query').value='ESCAT4300000043003B';updateCoordinateFinder()");
  assert.equal(await evaluate("document.querySelectorAll('#coordinate-finder-results button').length"),1);
  await evaluate("document.querySelector('#coordinate-finder-query').value='inexistente';updateCoordinateFinder()");
  assert.equal(await evaluate("document.querySelectorAll('#coordinate-finder-results button').length"),0);
  await evaluate("closeCoordinateFinder();authState.role='free';refreshCurrentStationPopup()");
  assert.equal(await evaluate("!!document.querySelector('[data-coordinate-review]')"),false);
  const previous=requests;await evaluate("reviewStationCoordinates(activeStationPopupProperties)");assert.equal(requests,previous);
  await evaluate("currentVisibleFeatures=[];updateCoordinateFinder()");
  assert.equal(await evaluate("document.querySelector('#coordinate-finder-toggle').hidden"),true);
  assert.deepEqual(errors,[]);
  console.log('PASS: header height preserved at 1280/768/641/640/390px, finder hidden on narrow screens, grouped searchable finder including filtered stations, exact arrow tips, readable review, focus controls, queued acceptance, permissions, stale rejection and cleanup.');
} finally {
  ws?.close();
  if(chrome && chrome.exitCode===null){chrome.kill('SIGTERM');await once(chrome,'exit');}
  server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
  await fs.rm(temporary,{recursive:true,force:true});
}
