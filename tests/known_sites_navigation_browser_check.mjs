// Real MapLibre/TerraDraw interactions. Writes only to an isolated fixture store.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'sites-navigation-'));
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let chrome,server,ws,serial=0,serverLog='';const pending=new Map(),errors=[];
const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function until(expression,timeout=30000){const start=Date.now();while(Date.now()-start<timeout){try{if(await evaluate(expression))return;}catch{}await pause(100);}throw Error('Timeout: '+expression+' '+await evaluate('document.body.innerText'));}
const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
const input=(selector,value)=>evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));})()`);
async function shot(name){await fs.writeFile(path.join(temp,name),Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));}
try{
 server=spawn('.venv/bin/python',['tests/known_sites_navigation_fixture.py',path.join(temp,'data')],{stdio:['ignore','pipe','pipe']});server.stderr.on('data',c=>serverLog+=c);
 const port=await new Promise((resolve,reject)=>{server.stdout.once('data',c=>resolve(JSON.parse(String(c)).port));server.once('exit',c=>reject(Error('Fixture '+c+' '+serverLog)));});
 const base='http://127.0.0.1:'+port;
 const profile=path.join(temp,'chrome');chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless','--no-first-run','--disable-background-networking','--use-angle=swiftshader','--enable-unsafe-swiftshader','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
 let debug;for(let i=0;i<100;i++){try{debug=(await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await pause(100);}}
 const pages=await(await fetch(`http://127.0.0.1:${debug}/json/list`)).json();ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);});
 await send('Runtime.enable');await send('Page.enable');
 await send('Page.addScriptToEvaluateOnNewDocument',{source:`let lib;Object.defineProperty(window,'maplibregl',{configurable:true,get:()=>lib,set:v=>{lib=v;const Original=v.Map;v.Map=new Proxy(Original,{construct(T,args){const m=new T(...args);window.__map=m;const add=m.addControl.bind(m);m.addControl=(c,...r)=>{const v=add(c,...r);if(c.getTerraDrawInstance)window.__draw=c;return v;};return m;}});}});`});
 await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:base+'/mushrooms/fixture-observation#edit-fixture'});await until("!!document.querySelector('.observation-manage-sites-link')");
 // Prevent opening a second tab in the test; exercise the actual onclick URL construction.
 await input('[name=location_lat]','42.1501');
 const href=await evaluate(`(()=>{const a=document.querySelector('.observation-manage-sites-link');a.addEventListener('click',e=>e.preventDefault());a.click();return a.href;})()`);
 const url=new URL(href);assert.equal(url.searchParams.get('id'),'fixture_micro');assert.equal(url.searchParams.get('observation_id'),'fixture_obs');assert.equal(url.searchParams.get('observation_lat'),'42.1501');
 await send('Page.navigate',{url:href});await until("!!window.__draw && !!document.querySelector('.sites-observation-marker')");await pause(800);
 assert.equal(await evaluate("document.querySelector('.site-row.selected').dataset.siteKey"),'micro_area:fixture_micro');
 const center=await evaluate('({lat:__map.getCenter().lat,lon:__map.getCenter().lng})');assert.ok(Math.abs(center.lat-42.1501)<1e-6&&Math.abs(center.lon-1.44)<1e-6);
 await click('.sites-observation-marker');await until("!!document.querySelector('.maplibregl-popup')");assert.ok((await evaluate("document.querySelector('.maplibregl-popup').textContent")).includes('fixture_obs'));await shot('observation-popup.png');await click('.maplibregl-popup-close-button');
 console.log('PASS observation link, selected micro-area, centred point and popup');
 await evaluate("window.realFetch=fetch;window.photonCalls=0;window.fetch=(url,o)=>{if(String(url).startsWith('https://photon.')){photonCalls++;return Promise.resolve(new Response(JSON.stringify({features:[{geometry:{type:'Point',coordinates:[1.45,42.16]},properties:{name:'Photon fixture'}}]})));}return realFetch(url,o);};");
 for(const query of ['42.15, 1.44','42.15 1.44','42,15; 1,44']){
  await click('#site-search-toggle');await input('#site-search-input',query);await evaluate("document.getElementById('site-search-form').requestSubmit()");await until("document.getElementById('site-search-panel').hidden");
 }
 assert.equal(await evaluate('photonCalls'),0);assert.equal(await evaluate("document.querySelectorAll('.sites-place-marker').length"),1);
 await click('#site-search-toggle');await input('#site-search-input','91, 1.44');await evaluate("document.getElementById('site-search-form').requestSubmit()");assert.ok((await evaluate("document.getElementById('site-search-status').textContent")).includes('no válidas'));assert.equal(await evaluate('photonCalls'),0);
 await input('#site-search-input','Girona');await evaluate("document.getElementById('site-search-form').requestSubmit()");await until("document.querySelector('#site-search-results button')");await click('#site-search-results button');assert.equal(await evaluate('photonCalls'),1);assert.equal(await evaluate("document.querySelectorAll('.sites-observation-marker').length"),1);
 console.log('PASS coordinates without Photon, validation, Photon retained and observation marker retained');
 // Existing micro-area: the centre click must pass through the observation marker.
 const originalMicro=await evaluate("JSON.parse(document.querySelector('[name=geometry_json]').value)");
 async function mapClick(coord){const p=await evaluate(`(()=>{const p=__map.project(${JSON.stringify(coord)}),r=__map.getCanvas().getBoundingClientRect();return{x:p.x+r.left,y:p.y+r.top};})()`);for(const type of ['mouseMoved','mousePressed','mouseReleased'])await send('Input.dispatchMouseEvent',{type,...p,button:type==='mouseMoved'?'none':'left',clickCount:type==='mouseMoved'?0:1});await pause(150);}
 await click('#site-edit-geometry');await click('#site-draw-circle');await until("document.getElementById('site-circle-choice').open");await click('#site-circle-choice [data-choice=replace]');
 await evaluate("void __map.jumpTo({center:[1.44,42.1501],zoom:15,padding:{top:0,bottom:0,left:0,right:0}})");await pause(400);
 assert.equal(await evaluate("document.getElementById('site-draw-circle').getAttribute('aria-pressed')"),'true');
 await mapClick([1.44,42.1501]);
 assert.deepEqual(await evaluate("JSON.parse(document.querySelector('[name=geometry_json]').value)"),originalMicro,'Incomplete circle must not replace the original');
 await click('#site-finish-geometry');assert.deepEqual(await evaluate("JSON.parse(document.querySelector('[name=geometry_json]').value)"),originalMicro,'Finishing with only the centre must discard the unfinished circle');
 await click('#site-edit-geometry');await click('#site-draw-circle');await until("document.getElementById('site-circle-choice').open");await click('#site-circle-choice [data-choice=replace]');
 await mapClick([1.44,42.1501]);await mapClick([1.445,42.1501]);
 const circleInfo=await evaluate("__draw.getFeatures().features.map(f=>({mode:f.properties.mode,radius:f.properties.radiusKilometers,coordinates:f.geometry.coordinates}))");
 await shot('existing-circle-active.png');assert.equal(circleInfo.length,1);assert.ok(circleInfo[0].radius>0.4&&circleInfo[0].radius<0.43,'Radius must be about 412 m, not an unfinished tiny circle');
 assert.ok(Math.abs((Math.min(...circleInfo[0].coordinates[0].map(p=>p[0]))+Math.max(...circleInfo[0].coordinates[0].map(p=>p[0])))/2-1.44)<1e-6,'Centre must be on the observation marker');
 await click('#site-finish-geometry');const replaced=await evaluate("JSON.parse(document.querySelector('[name=geometry_json]').value)");assert.equal(replaced.type,'Polygon');
 await click('#site-save');await until("!document.getElementById('site-busy').open&&document.getElementById('site-save-state').textContent==='Guardado'",60000);
 const persistedMicro=JSON.parse(await fs.readFile(path.join(temp,'data/mushroom_known_sites.json'),'utf8')).micro_areas.find(r=>r.micro_area_id==='fixture_micro');assert.deepEqual(persistedMicro.geometry,replaced);
 await click('#site-edit-geometry');await click('#site-draw-circle');await until("document.getElementById('site-circle-choice').open");await click('#site-circle-choice [data-choice=add]');await mapClick([1.448,42.1501]);await mapClick([1.449,42.1501]);await click('#site-finish-geometry');assert.equal(await evaluate("JSON.parse(document.querySelector('[name=geometry_json]').value).type"),'MultiPolygon');
 await click('#site-cancel');await until("document.getElementById('site-unsaved').open");await click('#site-unsaved [data-choice=discard]');await until("document.querySelector('[name=known_site_action][value=save_micro_area]')");
 await shot('existing-circle.png');console.log('PASS existing micro-area: replace, exact marker centre, complete radius, save, add, discard; incomplete circle preserves original');
 // Draw an actual circle and save through the real handler to temporary storage.
 await click('[data-new=area]');await until("document.querySelector('[name=known_site_action][value=create_area]')");await input('#sites-detail [name=name]','Circle fixture');await click('#site-draw-circle');
 await evaluate("void __map.jumpTo({center:[1.44,42.15],zoom:15,padding:0})");await pause(400);
 for(const coord of [[1.44,42.15],[1.445,42.15]]){
  const p=await evaluate(`(()=>{const p=__map.project(${JSON.stringify(coord)}),r=__map.getCanvas().getBoundingClientRect();return{x:p.x+r.left,y:p.y+r.top};})()`);
  for(const type of ['mouseMoved','mousePressed','mouseReleased'])await send('Input.dispatchMouseEvent',{type,...p,button:type==='mouseMoved'?'none':'left',clickCount:type==='mouseMoved'?0:1});await pause(150);
 }
 await until("JSON.parse(document.querySelector('[name=geometry_json]').value||'null')?.coordinates?.[0]?.length>20");
 await click('#site-finish-geometry');const circle=await evaluate("JSON.parse(document.querySelector('[name=geometry_json]').value)");assert.equal(circle.type,'Polygon');assert.deepEqual(circle.coordinates[0][0],circle.coordinates[0].at(-1));
 await click('#site-save');await until("location.search.includes('id=circle_fixture')&&!document.getElementById('site-busy').open",60000);
 const saved=JSON.parse(await fs.readFile(path.join(temp,'data/mushroom_known_sites.json'),'utf8')).areas.find(r=>r.area_id==='circle_fixture');assert.deepEqual(saved.geometry,circle);
 await click('#site-edit-geometry');await click('#site-edit-polygon');await click('#site-finish-geometry');assert.deepEqual(await evaluate("JSON.parse(document.querySelector('[name=geometry_json]').value)"),circle);
 assert.equal(new URL(await evaluate('location.href')).searchParams.get('observation_id'),'fixture_obs');
 await shot('circle.png');console.log('PASS real circular drawing, save, polygon re-edit and navigation context');

 await click('[data-new=micro_area]');await until("document.querySelector('[name=known_site_action][value=create_micro_area]')");await click('#site-draw-circle');
 await evaluate("void __map.jumpTo({center:[1.44,42.15],zoom:16,padding:0})");await pause(400);
 for(const coord of [[1.441,42.15],[1.4415,42.15]]){const p=await evaluate(`(()=>{const p=__map.project(${JSON.stringify(coord)}),r=__map.getCanvas().getBoundingClientRect();return{x:p.x+r.left,y:p.y+r.top};})()`);for(const type of ['mouseMoved','mousePressed','mouseReleased'])await send('Input.dispatchMouseEvent',{type,...p,button:type==='mouseMoved'?'none':'left',clickCount:type==='mouseMoved'?0:1});await pause(150);}
 await until("JSON.parse(document.querySelector('[name=geometry_json]').value||'null')?.coordinates?.[0]?.length>20");await click('#site-finish-geometry');
 await click('#site-cancel');await until("document.getElementById('site-unsaved').open");await click('#site-unsaved [data-choice=discard]');await until("document.querySelector('[name=known_site_action][value=save_area]')");
 console.log('PASS circle available for micro-area and discard retains saved area');
 // Narrow viewport, then actual HA local read-only preview.
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await click('#site-focus-observation');await pause(700);assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));await until('!__map.isMoving()&&Math.abs(__map.project([1.44,42.1501]).x-__map.getCanvas().clientWidth/2)<2'); await shot('mobile.png');
 if(process.argv.includes('--local-preview')){
  await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:'http://127.0.0.1:8101/mushrooms/known-sites?observation_lat=42.15&observation_lon=1.44'});await until("!!window.__draw && !!document.querySelector('.sites-observation-marker')");await pause(700);await click('.sites-observation-marker');await until("!!document.querySelector('.maplibregl-popup')");await shot('ha-local.png');console.log('PASS rebuilt HA local map and popup, read only');
 }
 assert.equal(errors.length,0,JSON.stringify(errors));console.log('Evidence: '+temp);
}finally{ws?.close();chrome?.kill('SIGTERM');server?.kill('SIGTERM');await fs.writeFile(path.join(temp,'server.log'),serverLog);}
