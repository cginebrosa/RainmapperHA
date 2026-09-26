// Real offline ZIP export -> real HTTP importer, using a temporary observation store.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';

const root=process.cwd(),temporary=fs.mkdtempSync(path.join(os.tmpdir(),'rainmapper-gbif-browser-'));
const snapshot=path.join(root,'local-apps/gbif/data/snapshot-catalunya-20120619-20260916-full');
const data=JSON.parse(fs.readFileSync(path.join(snapshot,'viewer/data.js'),'utf8').replace(/^const GBIF_DATA = /,'').trim().replace(/;$/,''));
const eligible=data.records.filter(r=>r.profile_ids.length===1&&/^\d{4}-\d{2}-\d{2}/.test(r.eventDate)&&!r.eventDate.includes('/')&&r.photos?.some(p=>p.localPath));
const size=r=>r.photos.filter(p=>p.localPath).reduce((n,p)=>n+fs.statSync(path.join(snapshot,p.localPath)).size,0);
eligible.sort((a,b)=>size(a)-size(b));
const rows=[eligible.find(r=>r.coordinateUncertaintyInMeters==null),eligible.find(r=>r.coordinateUncertaintyInMeters>0)];
assert.ok(rows.every(Boolean));
const occurrences=fs.readFileSync(path.join(snapshot,'occurrences.json'));
assert.equal(crypto.createHash('sha256').update(occurrences).digest('hex'),data.snapshot_sha256);
const sourceFiles=[path.join(snapshot,'occurrences.json'),...new Set(rows.flatMap(r=>r.photos.filter(p=>p.localPath).map(p=>path.join(snapshot,p.localPath))))];
const script=name=>`<script src="file://${path.join(root,'local-apps/gbif/code',name)}"></script>`;
const escaped=value=>JSON.stringify(value).replaceAll('<','\\u003c');
const fixture=path.join(temporary,'export.html');
fs.writeFileSync(fixture,`<!doctype html><meta charset="utf-8"><header><nav></nav></header><input id="species" value="all"><input id="precision" value="all"><input id="review-filter" value="approved"><input id="search" value=""><input id="fixture-files" type="file" multiple><script>
const GBIF_DATA=${escaped({snapshot_sha256:data.snapshot_sha256})};
const reviewWritable=true,reviewEntries=${escaped(Object.fromEntries(rows.map(r=>[String(r.key),{status:'approved',reviewed_at:'2026-09-25T10:00:00Z'}])))};
window.gbifViewer={filtered:${escaped(rows)}};
window.showSaveFilePicker=async options=>{window.__saveOptions=options;const previous=new File(window.__existingZIP?[window.__existingZIP]:[],options.suggestedName,{lastModified:123});return {name:options.suggestedName,getFile:async()=>previous,createWritable:async()=>{let blob;window.__writeCount=(window.__writeCount||0)+1;return {write:async value=>{blob=value;},close:async()=>{window.__savedBlob=blob;if(!window.__savedZIP){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=options.suggestedName;document.body.append(a);a.click();}window.__savedZIP=options.suggestedName;},abort:async()=>{}};}};};
window.showDirectoryPicker=async()=>{const handle={name:"snapshot-source",getDirectoryHandle:async()=>handle,getFileHandle:async name=>({getFile:async()=>{const f=[...document.getElementById('fixture-files').files].find(f=>f.name===name);if(!f)throw Error(name);return f;}})};return handle;};
</script>${script('gbif-export-labels.js')}${script('gbif-export.js')}`);
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let chrome,server,socket,serverLog='';
try {
  server=spawn('.venv/bin/python',['tests/gbif_import_fixture_server.py',path.join(temporary,'data')],{cwd:root,stdio:['ignore','pipe','pipe']});
  server.stderr.on('data',chunk=>serverLog+=chunk);
  const port=await new Promise((resolve,reject)=>{server.stdout.once('data',chunk=>resolve(JSON.parse(String(chunk)).port));server.once('exit',code=>reject(Error('Fixture failed '+code+' '+serverLog)));});
  const profile=path.join(temporary,'chrome');
  chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless','--no-first-run','--disable-background-networking','--user-data-dir='+profile,'--remote-debugging-port=0','about:blank'],{stdio:'ignore'});
  let debugPort;for(let i=0;i<100;i++){try{debugPort=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0];break;}catch{await pause(100);}}
  assert.ok(debugPort,'Chrome debugging endpoint');
  const pages=await(await fetch('http://127.0.0.1:'+debugPort+'/json/list')).json();
  socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);await new Promise(resolve=>socket.addEventListener('open',resolve,{once:true}));
  let serial=0;const pending=new Map(),errors=[];
  socket.addEventListener('message',event=>{const message=JSON.parse(event.data);if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails);if(message.id){const p=pending.get(message.id);pending.delete(message.id);message.error?p.reject(message.error):p.resolve(message.result);}});
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
  const wait=async(expression,message)=>{for(let i=0;i<150;i++){if(await evaluate(expression))return;await pause(100);}throw Error(message+' '+await evaluate('document.body.innerText'));};
  const setFiles=async(selector,files)=>{const {root}=await send('DOM.getDocument');const {nodeId}=await send('DOM.querySelector',{nodeId:root.nodeId,selector});await send('DOM.setFileInputFiles',{nodeId,files});};
  await send('Page.enable');await send('Runtime.enable');await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:temporary});
  await send('Page.navigate',{url:'file://'+fixture});await wait('!!window.gbifExport','Exporter loads');
  await setFiles('#fixture-files',sourceFiles);
  await evaluate("document.getElementById('export-rainmapper').click();window.gbifViewer.filtered=[];reviewEntries[Object.keys(reviewEntries)[0]].status='rejected';document.getElementById('gbif-export-source').click()");
  await wait("!document.getElementById('gbif-export-save').disabled",'Source verification');
  assert.match(await evaluate("document.querySelector('#gbif-export-dialog [role=status]').textContent"),/2 observaciones/);
  await evaluate("document.getElementById('gbif-export-save').click()");
  await wait("!!window.__savedZIP",'ZIP ready');
  const zipName=await evaluate("window.__savedZIP");
  const zip=path.join(temporary,zipName);for(let i=0;i<100&&!fs.existsSync(zip);i++)await pause(100);assert.ok(fs.existsSync(zip));
  assert.match(await evaluate("document.getElementById('gbif-export-dialog').textContent"),/Origen seleccionado: snapshot-source/);
  assert.match(zipName,/rainmapper-gbif-\d{4}-\d{2}-\d{2}-todas-1\.zip/);
  // Existing ZIP: edit its review metadata, retain an unrelated citation, and test both decisions.
  await evaluate(`(async()=>{const pkg=await gbifExport.readPackage(window.__savedBlob);for(const row of pkg.manifest.records)row.review={status:'rejected'};const extra=structuredClone(pkg.manifest.records[0]);extra.gbif_id='999999999999';pkg.manifest.records.push(extra);const bytes=new TextEncoder().encode(JSON.stringify(pkg.manifest));window.__existingZIP=gbifExport.zip([{name:'manifest.json',data:bytes,size:bytes.length,crc:gbifExport.crc32(bytes)},...[...pkg.entries.values()].filter(e=>e.name!=='manifest.json')]);document.getElementById('gbif-export-again').click();})()`);
  await wait("document.querySelectorAll('#gbif-export-duplicates select').length===2",'Export duplicate list');
  assert.equal(await evaluate("window.__writeCount"),1,'Existing destination not opened for writing before choices');
  await evaluate("document.getElementById('gbif-export-merge-cancel').click()");
  await wait("!document.getElementById('gbif-export-again').disabled",'Export merge cancelled');
  assert.equal(await evaluate("window.__writeCount"),1);
  await evaluate("document.getElementById('gbif-export-again').click()");
  await wait("document.querySelectorAll('#gbif-export-duplicates select').length===2",'Export choices again');
  await evaluate("document.querySelector('#gbif-export-duplicates select').value='replace';document.getElementById('gbif-export-merge-confirm').click()");
  await wait("window.__writeCount===2&&!document.getElementById('gbif-export-again').disabled",'Merged ZIP written');
  assert.deepEqual(await evaluate("(async()=>{const p=await gbifExport.readPackage(window.__savedBlob);return p.manifest.records.map(r=>[r.gbif_id,r.review.status]);})()"),[[String(rows[0].key),'approved'],[String(rows[1].key),'rejected'],['999999999999','rejected']]);
  // Limits and corrupt files must fail before touching the destination.
  assert.equal(await evaluate("(async()=>{try{await gbifExport.readPackage(new Blob(['not a zip']));return false;}catch{return true;}})()"),true);
  assert.equal(await evaluate("(async()=>{const p=await gbifExport.readPackage(window.__savedBlob),q=structuredClone(p.manifest.records[0]);for(let i=0;i<101;i++)p.manifest.records.push({...q,gbif_id:String(100000000+i)});try{gbifExport.mergePackages(p,p,new Set());return false;}catch{return true;}})()"),true);
  const before=fs.readFileSync(path.join(temporary,'data/mushroom_observations.json'));
  await send('Page.navigate',{url:`http://127.0.0.1:${port}/mushrooms/profiles?section=observations`});await wait("!!document.getElementById('gbif-import-open')",'Importer loads');
  await evaluate("document.getElementById('gbif-import-open').click()");await wait("!document.getElementById('gbif-import-preview').disabled",'Pending list');
  await setFiles('#gbif-import-file',[zip]);await evaluate("document.getElementById('gbif-import-preview').click()");await wait("document.querySelectorAll('#gbif-import-rows tr').length===2&&!document.getElementById('gbif-import-accept').disabled",'Upload and validation');
  assert.deepEqual(fs.readFileSync(path.join(temporary,'data/mushroom_observations.json')),before,'Preview never writes observations');
  assert.equal(await evaluate("document.querySelectorAll('#gbif-import-rows input:checked').length"),2);
  await evaluate("window.__importStatuses=[];new MutationObserver(()=>window.__importStatuses.push(document.getElementById('gbif-import-status').textContent)).observe(document.getElementById('gbif-import-status'),{childList:true,subtree:true,characterData:true})");
  await evaluate("document.querySelectorAll('#gbif-import-rows input')[1].checked=false;document.getElementById('gbif-import-accept').click()");await wait("document.getElementById('gbif-import-status').textContent.includes('Creadas: 1')",'Commit');
  assert.ok((await evaluate('window.__importStatuses')).some(text=>text.includes('Preparando GIS/DEM y microárea: 1 / 1')),'Per-record progress');
  assert.ok((await evaluate('window.__importStatuses')).some(text=>text.includes('Guardando observaciones y fotos: 1 / 1')),'Final save phase');
  const saved=JSON.parse(fs.readFileSync(path.join(temporary,'data/mushroom_observations.json'))).observations;
  assert.equal(saved.length,1);assert.equal(saved[0].site_context.gis_recovery.recovery_mode,'gbif_import');assert.equal(saved[0].validation_status,'draft');assert.equal(saved[0].calibration_use,'review');assert.equal(saved[0].flush_abundance,'normal');assert.equal(saved[0].location.precision_m,500);assert.equal(saved[0].external_source.viewer_review.status,'approved','Frozen review');assert.equal(saved[0].external_source.coordinate_uncertainty_m,null);
  for(const p of saved[0].media){assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(temporary,'data',p.path))).digest('hex'),p.sha256);}
  await evaluate("document.getElementById('gbif-import-preview').click()");await wait("!document.getElementById('gbif-import-review').hidden&&!document.getElementById('gbif-import-accept').disabled",'Reimport preview');
  assert.equal(await evaluate("document.querySelectorAll('#gbif-import-rows select').length"),1,'Duplicate decision available');
  assert.equal(await evaluate("document.querySelector('#gbif-import-rows select').value"),'keep');
  assert.match(await evaluate("document.getElementById('gbif-import-rows').textContent"),/Ya existe/);
  const after=fs.readFileSync(path.join(temporary,'data/mushroom_observations.json'));
  await evaluate("document.getElementById('gbif-import-cancel').click()");await wait("document.getElementById('gbif-import-review').hidden&&!document.getElementById('gbif-import-cancel').disabled",'Reject');
  assert.deepEqual(fs.readFileSync(path.join(temporary,'data/mushroom_observations.json')),after);
  await evaluate("document.getElementById('gbif-import-preview').click()");
  await wait("document.querySelectorAll('#gbif-import-rows select').length===1&&!document.getElementById('gbif-import-accept').disabled",'Replacement preview');
  await evaluate("document.querySelector('#gbif-import-rows select').value='replace';document.querySelectorAll('#gbif-import-rows input').forEach(el=>el.checked=false);document.getElementById('gbif-import-accept').click()");
  await wait("document.getElementById('gbif-import-status').textContent.includes('Reemplazadas: 1')",'Explicit replacement');
  const replaced=JSON.parse(fs.readFileSync(path.join(temporary,'data/mushroom_observations.json'))).observations;
  assert.equal(replaced.length,1);assert.equal(replaced[0].observation_id,saved[0].observation_id);assert.equal(replaced[0].validation_status,'draft');
  // Upgrade the existing fixture observation with automatic persistent sites.
  await evaluate("document.getElementById('gbif-import-preview').click()");
  await wait("document.querySelectorAll('#gbif-import-rows select').length===1&&!document.getElementById('gbif-import-accept').disabled",'Site creation preview');
  await evaluate("document.querySelector('#gbif-import-rows select').value='replace';document.querySelectorAll('#gbif-import-rows input').forEach(el=>el.checked=false);document.getElementById('gbif-import-auto-sites').checked=true;document.getElementById('gbif-import-accept').click()");
  await wait("!document.getElementById('gbif-import-sites-plan').hidden&&!document.getElementById('gbif-import-accept').disabled",'Batch site plan');
  assert.equal(fs.existsSync(path.join(temporary,'data/mushroom_known_sites.json')),false,'Planning does not save sites');
  assert.equal(await evaluate("document.querySelectorAll('#gbif-import-sites-plan [data-site-name]').length"),2);
  const siteShot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temporary,'site-plan.png'),Buffer.from(siteShot.data,'base64'));
  await evaluate("document.querySelector('#gbif-import-sites-plan [data-site-name]').value='Municipio de prueba';document.querySelectorAll('#gbif-import-sites-plan [data-site-name]')[1].value='Topónimo de prueba';document.getElementById('gbif-import-accept').click()");
  await wait("document.getElementById('gbif-import-sites-plan').hidden&&document.getElementById('gbif-import-status').textContent.includes('Microáreas nuevas: 1')",'Site confirmation');
  const knownSites=JSON.parse(fs.readFileSync(path.join(temporary,'data/mushroom_known_sites.json')));
  const withSites=JSON.parse(fs.readFileSync(path.join(temporary,'data/mushroom_observations.json'))).observations;
  assert.equal(knownSites.areas.length,1);assert.equal(knownSites.micro_areas.length,1);assert.equal(knownSites.areas[0].name,'Municipio de prueba');assert.equal(knownSites.micro_areas[0].name,'Topónimo de prueba');
  assert.equal(knownSites.areas[0].provenance.creation_source,'gbif');assert.equal(withSites[0].micro_area_id,knownSites.micro_areas[0].micro_area_id);
  assert.deepEqual(errors,[]);
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:'file://'+path.join(root,'docs/mushrooms/GBIF/snapshot-catalunya-20120619-20260916-full/index.html')});
  await wait("!!window.gbifExport&&!!window.gbifViewer",'Active viewer exporter');
  await evaluate("document.getElementById('export-rainmapper').click()");
  await wait("document.getElementById('gbif-export-dialog').open",'Export dialog');
  assert.match(await evaluate("document.querySelector('#gbif-export-dialog input[readonly]').value"),/snapshot-catalunya-20120619-20260916-full\/$/);
  const exportShot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temporary,'export-origin.png'),Buffer.from(exportShot.data,'base64'));
  if(process.argv.includes('--local-preview')) {
    await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
    await send('Page.navigate',{url:'http://127.0.0.1:8101/mushrooms/profiles?section=observations'});
    await wait("!!document.getElementById('gbif-import-open')",'HA local import control');
    assert.equal(await evaluate("!!document.querySelector('[name=location_precision_m]')"),true,'Uncertainty field exists');
    await evaluate("window.__form=document.querySelector('[id^=edit-observation-obs_gbif_]')||document.querySelector('[name=location_precision_m]').closest('.modal-layer');location.hash=window.__form.id");
    await wait("getComputedStyle(window.__form).display!=='none'",'Observation edit form visible');
    const layout=await evaluate("(()=>{const field=window.__form.querySelector('.location-precision'),label=field.querySelector('label');return {width:field.getBoundingClientRect().width,labelHeight:label.getBoundingClientRect().height};})()");
    assert.ok(layout.width>=190&&layout.labelHeight<45,JSON.stringify(layout));
    const formShot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temporary,'uncertainty-form.png'),Buffer.from(formShot.data,'base64'));
    await send('Page.navigate',{url:'http://127.0.0.1:8101/mushrooms/profiles?section=observations'});
    await wait("!!document.getElementById('gbif-import-open')&&!document.getElementById('gbif-import-dialog').open",'Fresh import page after layout check');

    await evaluate("document.getElementById('gbif-import-open').click()");
    await wait("!document.getElementById('gbif-import-preview').disabled",'HA local pending list');
    await setFiles('#gbif-import-file',[zip]);await evaluate("document.getElementById('gbif-import-preview').click()");
    await wait("document.querySelectorAll('#gbif-import-rows tr').length===2&&!document.getElementById('gbif-import-accept').disabled",'HA local real upload preview');
    assert.equal(await evaluate("document.querySelectorAll('#gbif-import-rows input').length"),2);
    assert.equal(await evaluate("getComputedStyle(document.getElementById('gbif-import-progress')).display"),'none','Completed upload progress hidden');
    assert.match(await evaluate("document.querySelector('#gbif-import-rows tr').textContent"),/\d{2}\/\d{2}\/\d{4}/,'Readable date');
    assert.ok(await evaluate("[...document.querySelectorAll('#gbif-import-rows tr')].every(tr=>!tr.children[2].textContent.includes('_'))"),'Scientific species labels');
    // A long batch scrolls only its table; every footer action stays in view.
    await evaluate("(()=>{const rows=document.getElementById('gbif-import-rows'),base=rows.firstElementChild;for(let i=0;i<38;i++){const copy=base.cloneNode(true);copy.dataset.fixtureClone='1';rows.append(copy);}})()");
    for(const size of [{width:1280,height:720},{width:390,height:844}]){
      await send('Emulation.setDeviceMetricsOverride',{...size,deviceScaleFactor:1,mobile:false});
      const bounds=await evaluate("(()=>{const d=document.getElementById('gbif-import-dialog'),scroll=d.querySelector('.gbif-table-scroll');scroll.scrollTop=scroll.scrollHeight;return {bottom:d.getBoundingClientRect().bottom,viewport:innerHeight,scrolls:scroll.scrollHeight>scroll.clientHeight,buttons:['accept','cancel','close'].map(id=>{const b=document.getElementById('gbif-import-'+id).getBoundingClientRect();return {top:b.top,bottom:b.bottom,right:b.right};})};})()");
      assert.ok(bounds.scrolls&&bounds.bottom<=bounds.viewport&&bounds.buttons.every(b=>b.top>=0&&b.bottom<=bounds.viewport&&b.right<=size.width),JSON.stringify(bounds));
    }
    await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
    const screenshot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temporary,'ha-local-import.png'),Buffer.from(screenshot.data,'base64'));
    await evaluate("document.querySelectorAll('[data-fixture-clone]').forEach(el=>el.remove());document.getElementById('gbif-import-auto-sites').checked=true;document.getElementById('gbif-import-accept').click()");
    await wait("!document.getElementById('gbif-import-sites-plan').hidden&&!document.getElementById('gbif-import-accept').disabled",'HA local site plan without commit');
    const localSiteShot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temporary,'ha-local-site-plan.png'),Buffer.from(localSiteShot.data,'base64'));
    await evaluate("document.getElementById('gbif-import-cancel').click()");await wait("document.getElementById('gbif-import-review').hidden&&!document.getElementById('gbif-import-cancel').disabled",'HA local cancel');
    await evaluate("document.getElementById('gbif-import-close').click()");
    assert.deepEqual(errors,[]);
  }
  fs.writeFileSync(path.join(temporary,'result.json'),JSON.stringify({ok:true,zip,photoBytes:saved[0].media.reduce((n,p)=>n+p.size_bytes,0),checks:['frozen_filters_and_review','actual_zip','HTTP_preview','selective_commit','media_SHA256','pending_review','unknown_uncertainty','duplicate','reject','export_duplicate_choices','export_cancel_without_write','export_keeps_unselected_records','explicit_import_replacement','GIS_preparation','per_record_progress','automatic_sites','editable_site_names','site_creation_provenance']},null,2));
  console.log(JSON.stringify({ok:true,evidence:temporary,zip,checks:18}));
} finally {if(serverLog)console.error(serverLog);console.log('Evidence: '+temporary);socket?.close();chrome?.kill('SIGTERM');server?.kill('SIGTERM');}
