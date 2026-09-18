// Exercise HA local with temporary sites; restore the JSON and its backup ring.
// Usage: node tests/known_sites_browser_check.mjs --allow-local-writes
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
if (!process.argv.includes('--allow-local-writes')) throw Error('Pass --allow-local-writes to test HA local with a backup/restore.');
const root=path.resolve('docker-data/mushroom-data');
const file=path.join(root,'mushroom_known_sites.json'), backupDir=path.join(root,'backups');
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'sites-functional-'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const original=await fs.readFile(file), observationPath=path.join(root,'mushroom_observations.json');
const observationHash=hash(await fs.readFile(observationPath));
const originalNames=(await fs.readdir(backupDir)).filter(n=>n.startsWith('mushroom_known_sites.')&&n.endsWith('.json'));
await fs.writeFile(path.join(temp,'original.json'),original);
await fs.mkdir(path.join(temp,'backups'));
for (const name of originalNames) await fs.copyFile(path.join(backupDir,name),path.join(temp,'backups',name));
const profile=path.join(temp,'chrome');
const chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
  '--headless','--no-first-run','--disable-background-networking','--use-angle=swiftshader',
  '--enable-unsafe-swiftshader','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'
],{stdio:'ignore'});
let ws,serial=0,mutated=false;const pending=new Map(),errors=[];
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const send=(method,params={})=>new Promise((resolve,reject)=>{
  const id=++serial;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));
});
async function evaluate(expression) {
  const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
  if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;
}
async function until(expression,timeout=20000) {
  const start=Date.now();
  while(Date.now()-start<timeout){try{if(await evaluate(expression))return;}catch{}await pause(100);}
  throw Error(`Timed out: ${expression}; errors=${JSON.stringify(errors)}; status=${await evaluate("document.getElementById('sites-status-message')?.textContent")}`);
}
async function click(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);}
async function input(selector,value){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));})()`);}
async function screenshot(name){const bytes=Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64');await fs.writeFile(path.join(temp,name),bytes);if(process.argv.includes('--screenshot'))await fs.writeFile(path.join(os.tmpdir(),'sites-check-'+name),bytes);}
try {
  let port;
  for(let i=0;i<100;i++){try{port=(await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await pause(100);}}
  const pages=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
  await new Promise(r=>ws.addEventListener('open',r,{once:true}));
  ws.addEventListener('message',e=>{
    const m=JSON.parse(e.data);
    if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}
    else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);
  });
  await send('Runtime.enable');await send('Page.enable');
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`
    let maplibre;
    Object.defineProperty(window,'maplibregl',{configurable:true,get:()=>maplibre,set:v=>{
      maplibre=v;const Original=v.Map;v.Map=new Proxy(Original,{construct(T,args){
        const m=new T(...args);window.__map=m;window.__mapCount=(window.__mapCount||0)+1;
        const add=m.addControl.bind(m);m.addControl=(control,...rest)=>{const result=add(control,...rest);if(control.getTerraDrawInstance)window.__draw=control;return result;};return m;
      }});
    }});
  `});
  await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:'http://127.0.0.1:8101/mushrooms/known-sites'});
  await until("!!window.__map?.getLayer('sites-fill') && !!window.__draw");
  assert.equal(await evaluate('window.__mapCount'),1);
  console.log('Initial:',await evaluate("({bytes:performance.getEntriesByType('navigation')[0].decodedBodySize,nodes:document.querySelectorAll('*').length,rows:document.querySelectorAll('.site-row').length})"));
  await click('.site-row.micro');
  await until("!!document.querySelector('.site-detail-head')");
  const first=await evaluate("document.querySelector('.site-row.selected').dataset.siteKey");
  await click('[data-tab=observations]');
  await until("document.querySelectorAll('.site-observation').length>0");
  await click('[data-tab=general]');
  // Actual map picking, including nested areas, must synchronize the tree.
  const mapKey=await evaluate(`(()=>{const data=JSON.parse(document.getElementById('sites-bootstrap').textContent);const f=data.geojson.features.find(f=>f.properties.kind==='area');const pts=f.geometry.coordinates.flat(2);return f.properties.key;})()`);
  await evaluate(`(()=>{const f=JSON.parse(document.getElementById('sites-bootstrap').textContent).geojson.features.find(f=>f.properties.key===${JSON.stringify(mapKey)});const coords=f.geometry.type==='Polygon'?f.geometry.coordinates[0]:f.geometry.coordinates[0][0];const center=[coords.reduce((s,p)=>s+p[0],0)/coords.length,coords.reduce((s,p)=>s+p[1],0)/coords.length];__map.jumpTo({center,zoom:13});window.__pick=center;})()`);
  await pause(500);
  await evaluate("void __map.fire('click',{point:__map.project(__pick),lngLat:{lng:__pick[0],lat:__pick[1]}})");
  await pause(500);
  if(await evaluate("!document.getElementById('site-overlaps').hidden"))await click('#site-overlaps button');
  await until("!!document.querySelector('.site-row.selected')");
  console.log('PASS selection and lazy observations');
  // Fresh area starts as an editable draft and is saved without document navigation.
  await click('[data-new=area]');
  await until("!!document.querySelector('[name=known_site_action][value=create_area]')");
  await input('#sites-detail [name=name]','UI Browser Temporary');
  // A click sequence draws a real polygon through TerraDraw, not a form injection.
  await evaluate("void __map.jumpTo({center:[1.443,42.152],zoom:15})");
  await pause(300);
  for(const coordinate of [[1.441,42.151],[1.445,42.151],[1.445,42.153],[1.441,42.153],[1.441,42.151]]) {
    const point=await evaluate(`(()=>{const p=__map.project(${JSON.stringify(coordinate)});const r=__map.getCanvas().getBoundingClientRect();return{x:p.x+r.left,y:p.y+r.top}})()`);
    for(const type of ['mouseMoved','mousePressed','mouseReleased'])await send('Input.dispatchMouseEvent',{type,...point,button:type==='mouseMoved'?'none':'left',clickCount:type==='mouseMoved'?0:1});
    await pause(120);
  }
  await until("!!document.querySelector('[name=geometry_json]').value");
  await click('#site-finish-geometry');
  mutated=true;
  await click('#site-save');
  await until("location.search.includes('id=ui_browser_temporary')&&!document.getElementById('site-busy').open",60000);
  assert.equal(await evaluate('location.hash'),'');
  assert.equal(await evaluate('window.__mapCount'),1);
  assert.equal(await evaluate("document.querySelector('[name=known_site_action]').value"),'save_area');
  console.log('PASS area creation and actual polygon drawing');
  // Parent inheritance, editing and save error retain the draft.
  await click('[data-new=micro_area]');
  await until("!!document.querySelector('[name=known_site_action][value=create_micro_area]')");
  assert.equal(await evaluate("document.querySelector('#sites-detail [name=area_id]').value"),'ui_browser_temporary');
  await input('#sites-detail [name=name]','Micro Test');
  await evaluate(`(()=>{const t=__draw.getTerraDrawInstance();t.addFeatures([{type:'Feature',properties:{mode:'polygon'},geometry:{type:'Polygon',coordinates:[[[1.442,42.1515],[1.443,42.1515],[1.443,42.1525],[1.442,42.1525],[1.442,42.1515]]]}},{type:'Feature',properties:{mode:'polygon'},geometry:{type:'Polygon',coordinates:[[[1.4435,42.1515],[1.444,42.1515],[1.444,42.1525],[1.4435,42.1525],[1.4435,42.1515]]]}}]);})()`);
  await until("!!document.querySelector('[name=geometry_json]').value");
  await click('#site-finish-geometry');
  await evaluate("window.realFetch=window.fetch;window.fetch=(url,options)=>options?.method==='POST'?Promise.resolve(new Response(JSON.stringify({ok:false,error:'Prueba de error conservando borrador'}),{status:422})):realFetch(url,options)");
  await click('#site-save');
  await until("document.getElementById('sites-status-message').textContent.includes('Prueba de error')");
  assert.equal(await evaluate("document.querySelector('#sites-detail [name=name]').value"),'Micro Test');
  await evaluate("window.fetch=window.realFetch");
  await click('#site-save');
  await until("document.getElementById('site-busy').open");
  await screenshot('busy.png');
  await until("location.search.includes('id=ui_browser_temporary_micro_test')&&!document.getElementById('site-busy').open",90000);
  assert.equal(await evaluate('window.__mapCount'),1);
  assert.equal(JSON.parse(await evaluate("document.querySelector('[name=geometry_json]').value")).type,'MultiPolygon');
  console.log('PASS micro-area creation, DEM/SoilGrids and failed-save retention');
  // Existing geometry is not changed simply by opening the editor.
  const before=await evaluate("document.querySelector('[name=geometry_json]').value");
  await click('#site-edit-geometry');await click('#site-finish-geometry');
  assert.deepEqual(JSON.parse(await evaluate("document.querySelector('[name=geometry_json]').value")),JSON.parse(before));
  // Unsaved changes prompt and discard.
  await input('#sites-detail [name=description]','Uncommitted');
  await click('.site-row');await until("document.getElementById('site-unsaved').open");
  await click('#site-unsaved [data-choice=cancel]');
  assert.equal(await evaluate("document.querySelector('#sites-detail [name=description]').value"),'Uncommitted');
  await click('#site-cancel');await until("document.getElementById('site-unsaved').open");
  await click('#site-unsaved [data-choice=discard]');
  await until("document.querySelector('#sites-detail [name=description]').value===''");
  // GIS preview is explicit, with a visible busy state and unsaved apply stage.
  await click('#site-recover-gis');
  await until("!!document.getElementById('gis-dem-review') || document.getElementById('sites-status-message').classList.contains('error')",90000);
  assert.ok(await evaluate("!!document.getElementById('gis-dem-review')"),await evaluate("document.getElementById('sites-status-message').textContent"));
  await click('[data-gis-select=empty]');
  await click('#gis-dem-review form .primary');
  await until("!document.getElementById('gis-dem-review')&&!document.getElementById('site-busy').open");
  assert.equal(await evaluate("document.getElementById('site-save-state').textContent"),'Cambios sin guardar');
  await click('#site-save');
  await until("!document.getElementById('site-busy').open&&document.getElementById('site-save-state').textContent==='Guardado'",90000);
  const persisted=JSON.parse(await fs.readFile(file,'utf8')).micro_areas.find(r=>r.micro_area_id==='ui_browser_temporary_micro_test');
  assert.ok(persisted.derived_context.gis_dem);
  assert.ok(persisted.derived_context.soilgrids_water);
  console.log('PASS GIS preview, apply to draft, save and persisted contexts');
  // Archive, restore, archive and permanent deletion require explicit confirmation.
  for(const action of ['archive','archive','archive','delete']) {
    await click('#site-'+action);await until("document.getElementById('site-confirm').open");
    await click('#site-confirm [data-choice=confirm]');
    await until("!document.getElementById('site-busy').open && !document.getElementById('site-confirm').open");
    await pause(250);
  }
  assert.ok(!JSON.parse(await fs.readFile(file,'utf8')).micro_areas.some(r=>r.micro_area_id==='ui_browser_temporary_micro_test'));
  // Search behavior and mobile sizing are deterministic with a synthetic Photon response.
  await evaluate(`window.fetch=(url,options)=>String(url).startsWith('https://photon.')?Promise.resolve(new Response(JSON.stringify({features:[{geometry:{type:'Point',coordinates:[1.44,42.15]},properties:{name:'Lugar <literal>',city:'Alinyà'}}]}))):realFetch(url,options)`);
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await click('#sites-list-toggle');
  await click('#site-search-toggle');await input('#site-search-input','Alinya');
  assert.equal(await evaluate("getComputedStyle(document.getElementById('site-search-input')).fontSize"),'16px');
  await evaluate("document.getElementById('site-search-form').requestSubmit()");
  await until("document.querySelectorAll('#site-search-results button').length===1");
  await click('#site-search-results button');await until("document.querySelectorAll('.sites-place-marker').length===1");
  await click('#site-search-toggle');await input('#site-search-input','Otro lugar');
  await evaluate("document.getElementById('site-search-form').requestSubmit()");
  await until("!document.querySelector('.sites-place-marker')");
  await until("document.querySelectorAll('#site-search-results button').length===1");
  await click('#site-search-results button');
  assert.equal(await evaluate("document.querySelectorAll('.sites-place-marker').length"),1);
  assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));
  await screenshot('mobile.png');
  assert.equal(errors.length,0,JSON.stringify(errors));
  console.log('PASS: one map; lazy observations; map/list; create/draw/save; parent; failed save; GIS; discard; archive/restore/delete; search POI; mobile.');
} finally {
  ws?.close();chrome.kill('SIGTERM');
  if(mutated){
    await fs.writeFile(file+'.browser-restore',original);await fs.rename(file+'.browser-restore',file);
    const now=(await fs.readdir(backupDir)).filter(n=>n.startsWith('mushroom_known_sites.')&&n.endsWith('.json'));
    for(const name of originalNames)await fs.copyFile(path.join(temp,'backups',name),path.join(backupDir,name));
    for(const name of now)if(!originalNames.includes(name))await fs.unlink(path.join(backupDir,name));
  }
  const restored=hash(await fs.readFile(file))===hash(original);
  const observationsUnchanged=hash(await fs.readFile(observationPath))===observationHash;
  console.log({restored,observationsUnchanged});
  await fetch('http://127.0.0.1:8101/mushrooms/known-sites').catch(()=>{});
  await pause(500);
  if(restored&&observationsUnchanged)await fs.rm(temp,{recursive:true,force:true});
  else console.error('Backup retained:',temp);
}
