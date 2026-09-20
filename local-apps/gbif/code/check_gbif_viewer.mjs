import {spawn} from 'node:child_process';
import {createServer} from 'node:http';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const root=path.resolve(process.argv[2]);
// Temporary loopback origin only for testing genuine OPFS handles (OPFS excludes file://).
const server=createServer(async(req,res)=>{try{const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json'};res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(await fs.readFile(file));}catch{res.writeHead(404);res.end();}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const testURL=`http://127.0.0.1:${server.address().port}/index.html`;
const profile=await fs.mkdtemp(path.join(os.tmpdir(),'rainmapper-gbif-browser-'));
const chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
  '--headless','--no-first-run','--disable-background-networking','--use-angle=swiftshader','--enable-unsafe-swiftshader',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore'});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let pageLoaded=null;
async function navigate(method,params={}){const ready=new Promise(resolve=>{pageLoaded=resolve;});await send(method,params);await ready;}
let ws,serial=0;const waiting=new Map(),requests=[],exceptions=[];
const timeout=setTimeout(()=>{chrome.kill();process.exit(2)},100000);
function send(method,params={}){const id=++serial;return new Promise((resolve,reject)=>{waiting.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function until(expression){for(let i=0;i<150;i++){try{if(await evaluate(expression))return;}catch(error){if(!/navigated|context|closed/.test(String(error.message||error)))throw error;}await pause(100);}throw Error(`Timed out: ${expression}`);}
try{
  let port;for(let i=0;i<120;i++){try{port=(await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await pause(100);}}
  assert(port,'Chrome did not start');
  const pages=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
  await new Promise(r=>ws.addEventListener('open',r,{once:true}));
  ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const t=waiting.get(m.id);waiting.delete(m.id);m.error?t.reject(m.error):t.resolve(m.result);}else if(m.method==='Page.loadEventFired'){pageLoaded?.();pageLoaded=null;}else if(m.method==='Network.requestWillBeSent')requests.push(m.params.request.url);else if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails);});
  await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1500,height:980,deviceScaleFactor:1,mobile:false});
  await navigate('Page.navigate',{url:testURL});
  await until('!!window.gbifViewer && !!gbifViewer.map.getSource("gbif") && gbifViewer.map.isSourceLoaded("gbif")');
  assert.equal(await evaluate('gbifViewer.filtered.length'),1928);
  await until('window.gbifReviewFile?.ready');
  // Use a genuine browser FileSystemFileHandle and IndexedDB; only the native picker is substituted.
  // Pre-existing valid review must be merged, never truncated by choosing its folder.
  await evaluate('(async()=>{const dir=await navigator.storage.getDirectory(),h=await dir.getFileHandle("gbif-revision-autoguardado.json",{create:true}),doc=gbifViewer.reviewDocument();const row=doc.records.find(r=>r.gbif_id==="4459994467");row.status="doubtful";row.reviewed_at=new Date().toISOString();const stream=await h.createWritable();await stream.write(JSON.stringify(doc));await stream.close()})()');
  await evaluate('(async()=>{const dir=await navigator.storage.getDirectory();window.testReviewHandle=await dir.getFileHandle("gbif-revision-autoguardado.json",{create:true});window.showDirectoryPicker=async()=>dir;document.getElementById("connect-review-file").click()})()');
  await until('!document.getElementById("connect-review-file").disabled && document.getElementById("review-file-status").textContent.startsWith("Guardado en archivo:")');
  assert.equal(await evaluate('gbifViewer.reviewStatus("4459994467")'),"doubtful");
  await evaluate('gbifViewer.selectObservation("4978365738",false);document.getElementById("observation-review").value="approved";document.getElementById("observation-review").dispatchEvent(new Event("change"))');
  await until('!gbifReviewFile.pending');
  assert.equal(await evaluate('(async()=>{const h=await(await navigator.storage.getDirectory()).getFileHandle("gbif-revision-autoguardado.json");return JSON.parse(await(await h.getFile()).text()).records.find(r=>r.gbif_id==="4978365738").status})()'),'approved');
  // Simulate losing browser localStorage: remembered file independently restores the decision.
  await evaluate('localStorage.clear()');await navigate('Page.reload');
  await until('window.gbifReviewFile?.ready && !gbifReviewFile.pending && !!window.gbifViewer');
  assert.equal(await evaluate('gbifViewer.reviewStatus("4978365738")'),'approved');
  // All four statuses are saved to disk, including the newly added rejection.
  await evaluate('gbifViewer.selectObservation("4978365738",false);document.getElementById("observation-review").value="rejected";document.getElementById("observation-review").dispatchEvent(new Event("change"))');
  await until('!gbifReviewFile.pending');
  assert.equal(await evaluate('(async()=>{const h=await(await navigator.storage.getDirectory()).getFileHandle("gbif-revision-autoguardado.json");return JSON.parse(await(await h.getFile()).text()).records.find(r=>r.gbif_id==="4978365738").status})()'),'rejected');
  await navigate('Page.reload');
  await until('window.gbifReviewFile?.ready && !!window.gbifViewer');
  assert.equal(await evaluate('gbifViewer.reviewStatus("4978365738")'),'rejected');
  assert.match(await evaluate('document.getElementById("review-file-status").textContent'),/Guardado en archivo:/);
  // Rapid edits are serialized and the last one reaches the file.
  await evaluate('gbifViewer.selectObservation("4978365738",false);for(const state of ["doubtful","approved","pending"]){document.getElementById("observation-review").value=state;document.getElementById("observation-review").dispatchEvent(new Event("change"))}');
  await until('!gbifReviewFile.pending');
  assert.equal(await evaluate('(async()=>{const h=await(await navigator.storage.getDirectory()).getFileHandle("gbif-revision-autoguardado.json");return JSON.parse(await(await h.getFile()).text()).records.find(r=>r.gbif_id==="4978365738").status})()'),'pending');
  // Test write failure: previously committed JSON must remain complete and unchanged.
  const previousFile=await evaluate('(async()=>{const h=await(await navigator.storage.getDirectory()).getFileHandle("gbif-revision-autoguardado.json");return await(await h.getFile()).text()})()');
  await evaluate('window.originalCreateWritable=FileSystemFileHandle.prototype.createWritable;FileSystemFileHandle.prototype.createWritable=async function(){const stream=await originalCreateWritable.call(this);return {write:async text=>{await stream.write(text);throw Error("Test disk failure")},close:()=>stream.close(),abort:()=>stream.abort()}};document.getElementById("observation-review").value="approved";document.getElementById("observation-review").dispatchEvent(new Event("change"))');
  await until('document.getElementById("review-file-status").textContent.includes("Test disk failure")');
  assert.equal(await evaluate('(async()=>{const h=await(await navigator.storage.getDirectory()).getFileHandle("gbif-revision-autoguardado.json");return await(await h.getFile()).text()})()'),previousFile);
  assert.equal(await evaluate('gbifViewer.reviewStatus("4978365738")'),'approved');
  await evaluate('FileSystemFileHandle.prototype.createWritable=originalCreateWritable;document.getElementById("connect-review-file").click()');
  await until('!gbifReviewFile.pending && !document.getElementById("connect-review-file").disabled');
  // Clean only this isolated test profile before the existing browser-only checks.
  await evaluate('(async()=>{const db=await new Promise((resolve,reject)=>{const r=indexedDB.open("rainmapper-gbif-review-files",1);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});await new Promise((resolve,reject)=>{const t=db.transaction("handles","readwrite");t.objectStore("handles").clear();t.oncomplete=resolve;t.onerror=reject});db.close();localStorage.clear()})()');
  await navigate('Page.navigate',{url:pathToFileURL(path.join(root,'index.html')).href});await until('window.gbifReviewFile?.ready && !!window.gbifViewer && !!gbifViewer.map.getSource("gbif")');
  // Independent browser profile: no existing user review is ever touched.
  assert(await evaluate('gbifViewer.reviewDocument().records.every(r=>r.status==="pending"&&r.reviewed_at===null)'));
  await evaluate('gbifViewer.selectObservation("4978365738",false);document.getElementById("observation-review").value="approved";document.getElementById("observation-review").dispatchEvent(new Event("change"))');
  await navigate('Page.reload');
  await until('!!window.gbifViewer && !!gbifViewer.map.getSource("gbif")');
  assert.equal(await evaluate('gbifViewer.reviewStatus("4978365738")'),'approved');
  await evaluate('document.getElementById("review-filter").value="approved";document.getElementById("review-filter").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),1);
  assert.equal(await evaluate('gbifViewer.map.getSource("gbif-uncertainty")._data.features.length'),1);
  await evaluate('gbifViewer.selectObservation("4978365738",false);document.getElementById("observation-review").value="doubtful";document.getElementById("observation-review").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),0);
  assert.equal(await evaluate('document.getElementById("side").hidden'),true);
  await evaluate('document.getElementById("review-filter").value="doubtful";document.getElementById("review-filter").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),1);
  const exported=await evaluate('gbifViewer.reviewDocument()');
  assert.deepEqual(await evaluate('Array.from(document.getElementById("review-filter").options).slice(1).map(o=>o.textContent)'),['Pendiente','Dudosa','Aceptada','Rechazada']);
  await evaluate('document.getElementById("review-filter").value="all";document.getElementById("review-filter").dispatchEvent(new Event("change"));gbifViewer.selectObservation("4459994467",false);document.getElementById("observation-review").value="rejected";document.getElementById("observation-review").dispatchEvent(new Event("change"));document.getElementById("review-filter").value="rejected";document.getElementById("review-filter").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),1);
  assert.match(await evaluate('document.getElementById("count").textContent'),/Rechazada: 1/);
  const rejectedExport=await evaluate('gbifViewer.reviewDocument()');
  await evaluate('localStorage.clear()');
  await navigate('Page.reload');await until('!!window.gbifViewer && !!gbifViewer.map.getSource("gbif")');
  await evaluate(`gbifViewer.importReview(${JSON.stringify(rejectedExport)})`);
  assert.equal(await evaluate('gbifViewer.reviewStatus("4459994467")'),'rejected');
  assert.equal(exported.records.find(r=>r.gbif_id==='4978365738').status,'doubtful');
  assert.equal(exported.records.length,1928);
  // Invalid imports fail atomically; different snapshot, duplicate IDs and unknown states.
  for(const mutation of ['d.snapshot_sha256="wrong"','d.records[0].status="invalid"','d.records[1]=d.records[0]']){
    assert(await evaluate(`(()=>{const before=JSON.stringify(gbifViewer.reviewDocument().records),d=gbifViewer.reviewDocument();${mutation};try{gbifViewer.importReview(d);return false;}catch{return before===JSON.stringify(gbifViewer.reviewDocument().records)}})()`));
  }
  // Simulate another browser's empty review, then import the exported decisions.
  await evaluate('localStorage.clear()');
  await navigate('Page.reload');await until('!!window.gbifViewer && !!gbifViewer.map.getSource("gbif")');
  await evaluate(`gbifViewer.importReview(${JSON.stringify(exported)})`);
  assert.equal(await evaluate('gbifViewer.reviewStatus("4978365738")'),'doubtful');
  await evaluate('document.getElementById("review-filter").value="all";document.getElementById("review-filter").dispatchEvent(new Event("change"));gbifViewer.selectObservation("4978365738",false);document.getElementById("observation-review").value="pending";document.getElementById("observation-review").dispatchEvent(new Event("change"))');
  await evaluate(`gbifViewer.importReview(${JSON.stringify(exported)})`);
  assert.equal(await evaluate('gbifViewer.reviewStatus("4978365738")'),'pending','older import must not overwrite a newer decision');
  // Failed writes must neither display success nor change the state in memory.
  assert(await evaluate('(()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=()=>{throw Error("Test quota")};document.getElementById("observation-review").value="approved";document.getElementById("observation-review").dispatchEvent(new Event("change"));Storage.prototype.setItem=original;return gbifViewer.reviewStatus("4978365738")==="pending"&&document.getElementById("review-message").textContent.includes("No se ha guardado")})()'));
  await evaluate('document.getElementById("close-detail").click()');
  assert.equal(await evaluate('document.getElementById("list")'),null);
  assert.equal(await evaluate('document.getElementById("side").hidden'),true);
  const mapLayout=await evaluate('(()=>{const r=document.getElementById("map").getBoundingClientRect();return {width:r.width,height:r.height,top:r.top}})()');
  assert(mapLayout.width>=1490 && mapLayout.height>=750 && mapLayout.top<170,JSON.stringify(mapLayout));
  assert(await evaluate('document.documentElement.scrollHeight<=innerHeight+1 && document.querySelector(".legend").getBoundingClientRect().bottom<=innerHeight+1'));
  assert.equal(await evaluate('gbifViewer.map.getSource("gbif-uncertainty")._data.features.length'),1928);
  await evaluate('document.getElementById("show-uncertainty").click()');
  assert.equal(await evaluate('gbifViewer.map.getLayoutProperty("gbif-uncertainty-fill","visibility")'),'none');
  await evaluate('document.getElementById("show-uncertainty").click()');
  assert.equal(await evaluate('gbifViewer.map.getLayoutProperty("gbif-uncertainty-fill","visibility")'),'visible');
  assert.equal(await evaluate('document.getElementById("species").options.length'),22);
  assert.deepEqual(await evaluate('[...document.getElementById("basemap").options].map(o=>o.text)'),['Satélite+','Híbrido','Topográfico','Liberty']);
  await evaluate('document.getElementById("precision").value="precise_or_unknown";document.getElementById("precision").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),1774);
  assert.equal(await evaluate('gbifViewer.map.getSource("gbif-uncertainty")._data.features.length'),1774);
  assert.match(await evaluate('document.getElementById("count").textContent'),/1774/);
  assert(await evaluate('gbifViewer.filtered.every(r=>r.coordinateUncertaintyInMeters==null||r.coordinateUncertaintyInMeters<=1000)'));
  await evaluate('document.getElementById("precision").value="all";document.getElementById("precision").dispatchEvent(new Event("change"))');
  await evaluate('gbifViewer.selectObservation(gbifViewer.filtered.find(r=>r.geography.municipality.status!=="available").key,false)');
  assert.match(await evaluate('document.getElementById("detail").textContent'),/No disponible en la cartografía local/);
  await evaluate('document.getElementById("species").value="boletus_edulis";document.getElementById("species").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),84);
  await evaluate('document.getElementById("precision").value="precise_or_unknown";document.getElementById("precision").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),77);
  await evaluate('document.getElementById("precision").value="precise";document.getElementById("precision").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),34);
  assert.deepEqual(await evaluate('gbifViewer.map.getPaintProperty("gbif-uncertainty-fill","fill-color")'),['case',['get','visual_only'],'#ed7777','#78c9ef']);
  assert.equal(await evaluate('gbifViewer.map.getSource("gbif-uncertainty")._data.features.length'),34);
  assert(await evaluate('(()=>{const f=gbifViewer.map.getSource("gbif-uncertainty")._data.features[0],r=gbifViewer.filtered.find(r=>String(r.key)===f.properties.id);const north=f.geometry.coordinates[0][0];const distance=Math.abs(north[1]-r.decimalLatitude)*Math.PI/180*6371008.8;return Math.abs(distance-r.coordinateUncertaintyInMeters)<0.01;})()'));
  await evaluate('gbifViewer.selectObservation(gbifViewer.filtered.find(r=>r.photos.some(p=>p.localPath)).key)');
  await until('!!document.querySelector("#detail img") && [...document.querySelectorAll("#detail img")].every(i=>i.complete&&i.naturalWidth>0)');
  const selected=await evaluate('gbifViewer.selected');
  assert.match(await evaluate('document.getElementById("detail").textContent'),/Boletus edulis/);
  assert.deepEqual(await evaluate('[...document.querySelectorAll("#detail dt")].slice(3,6).map(e=>e.textContent)'),['Coordenadas','Altitud','Municipio']);
  assert(await evaluate('(()=>{const r=gbifViewer.filtered.find(r=>String(r.key)===gbifViewer.selected),d=[...document.querySelectorAll("#detail dd")];return d[4].textContent.includes(new Intl.NumberFormat("es-ES").format(Math.round(r.geography.elevation.value_m)))&&d[5].textContent===r.geography.municipality.name;})()'));
  assert.equal(await evaluate('[...document.querySelectorAll("#detail img")].every(i=>i.src.startsWith("file:"))'),true);
  assert.equal(await evaluate('document.getElementById("side").hidden'),false);
  await evaluate('document.getElementById("close-detail").click()');
  assert.equal(await evaluate('document.getElementById("side").hidden'),true);
  await pause(600);
  await until('gbifViewer.map.queryRenderedFeatures({layers:["gbif-points"]}).length>0');
  // Real click on a projected unclustered point, not just a call to the selection handler.
  const point=await evaluate('(()=>{const f=gbifViewer.map.queryRenderedFeatures({layers:["gbif-points"]})[0];const p=gbifViewer.map.project(f.geometry.coordinates),r=gbifViewer.map.getCanvas().getBoundingClientRect();return {x:r.x+p.x,y:r.y+p.y};})()');
  await send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
  assert(await evaluate('!!gbifViewer.selected'));
  const clicked=await evaluate('gbifViewer.selected');
  await evaluate('document.getElementById("basemap").value="esri-hybrid";document.getElementById("basemap").dispatchEvent(new Event("change"))');
  await until('!!gbifViewer.map.getSource("gbif") && gbifViewer.map.isSourceLoaded("gbif")');
  assert.equal(await evaluate('gbifViewer.selected'),clicked);
  assert.equal(await evaluate('gbifViewer.filtered.length'),34);
  // Prove that filtering and local photographs remain available with all remote requests blocked.
  await send('Network.setBlockedURLs',{urls:['https://*','http://*']});
  await evaluate('document.getElementById("species").value="all";document.getElementById("precision").value="unknown";document.getElementById("precision").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),1181);
  assert.equal(await evaluate('gbifViewer.map.getSource("gbif-uncertainty")._data.features.length'),1181);
  assert(await evaluate('gbifViewer.map.getSource("gbif-uncertainty")._data.features.every(f=>f.properties.visual_only===true&&f.properties.radius_m===500)'));
  assert(await evaluate('gbifViewer.filtered.every(r=>r.coordinateUncertaintyInMeters===null)'));
  await evaluate('gbifViewer.selectObservation(gbifViewer.filtered.find(r=>r.photos.some(p=>p.localPath)).key)');
  await until('[...document.querySelectorAll("#detail img")].every(i=>i.complete&&i.naturalWidth>0)');
  assert.equal(await evaluate('gbifViewer.map.getSource("gbif-selected")._data.features.filter(f=>f.geometry.type==="Polygon").length'),0);
  await evaluate('document.getElementById("search").value="zzzz-nunca-coincide";document.getElementById("search").dispatchEvent(new Event("input"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),0);
  await evaluate('document.getElementById("search").value="";document.getElementById("precision").value="wide";document.getElementById("precision").dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('gbifViewer.filtered.length'),154);
  assert.equal(await evaluate('gbifViewer.map.getSource("gbif-uncertainty")._data.features.length'),154);
  // Reproduce browser-restored controls without a change event.
  await evaluate('document.getElementById("precision").value="precise_or_unknown";window.dispatchEvent(new Event("pageshow"))');
  await until('gbifViewer.filtered.length===1774');
  assert.match(await evaluate('document.getElementById("count").textContent'),/1774/);
  // The user's two overlapping Boletus aereus records must both remain reachable.
  await evaluate('document.getElementById("species").value="boletus_aereus";document.getElementById("species").dispatchEvent(new Event("change"));gbifViewer.map.jumpTo({center:[1.097946,41.229605],zoom:12});void 0');
  await until('gbifViewer.map.isSourceLoaded("gbif") && gbifViewer.map.queryRenderedFeatures({layers:["gbif-clusters"]}).some(f=>f.properties.point_count===2 && Math.abs(f.geometry.coordinates[0]-1.097946)<0.00001 && Math.abs(f.geometry.coordinates[1]-41.229605)<0.00001)');
  const pairPoint=await evaluate('(()=>{const p=gbifViewer.map.project([1.097946,41.229605]),r=gbifViewer.map.getCanvas().getBoundingClientRect();return {x:r.x+p.x,y:r.y+p.y}})()');
  await send('Input.dispatchMouseEvent',{type:'mousePressed',...pairPoint,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',...pairPoint,button:'left',clickCount:1});
  await until('document.querySelectorAll("#overlap button").length===2');
  assert.deepEqual(await evaluate('[...document.querySelectorAll("#overlap button")].map(b=>b.dataset.id).sort()'),['4459994467','4460004405']);
  await evaluate('document.querySelectorAll("#overlap button")[1].click()');
  assert.equal(await evaluate('gbifViewer.selected'),await evaluate('document.querySelectorAll("#overlap button")[1].dataset.id'));
  await evaluate('document.querySelector("#detail details").open=true');
  assert(await evaluate('document.getElementById("side").getBoundingClientRect().bottom<=innerHeight && document.getElementById("side").scrollHeight>document.getElementById("side").clientHeight'));
  await evaluate('document.getElementById("close-detail").click();document.getElementById("species").value="all";document.getElementById("species").dispatchEvent(new Event("change"))');
  await evaluate('document.getElementById("search").value="";document.getElementById("precision").value="all";document.getElementById("search").dispatchEvent(new Event("input"));gbifViewer.fitObservations()');
  assert.equal(await evaluate('gbifViewer.filtered.length'),1928);
  await send('Network.setBlockedURLs',{urls:[]});
  await evaluate('document.getElementById("basemap").value="esri-satellite-vector";document.getElementById("basemap").dispatchEvent(new Event("change"))');
  await until('!!gbifViewer.map.getSource("gbif")');await pause(1500);
  let shot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(root,'viewer/desktop.png'),Buffer.from(shot.data,'base64'));
  await evaluate('gbifViewer.map.jumpTo({center:[1.7,42.1],zoom:10,bearing:65});document.getElementById("terrain-toggle").click()');
  await until('gbifViewer.map.getTerrain()?.source==="gbif-terrain-dem" && Math.abs(gbifViewer.map.getPitch()-55)<0.1');
  assert.equal(await evaluate('gbifViewer.map.getSource("gbif-terrain-dem").encoding'),'terrarium');
  assert.equal(await evaluate('document.getElementById("terrain-toggle").getAttribute("aria-pressed")'),'true');
  const northView=await evaluate('({center:gbifViewer.map.getCenter().toArray(),zoom:gbifViewer.map.getZoom(),pitch:gbifViewer.map.getPitch()})');
  await evaluate('document.getElementById("north-toggle").click()');await until('Math.abs(gbifViewer.map.getBearing())<0.01');
  const afterNorth=await evaluate('({center:gbifViewer.map.getCenter().toArray(),zoom:gbifViewer.map.getZoom(),pitch:gbifViewer.map.getPitch()})');
  assert(Math.abs(afterNorth.zoom-northView.zoom)<0.001 && Math.abs(afterNorth.pitch-northView.pitch)<0.001);
  assert(afterNorth.center.every((v,i)=>Math.abs(v-northView.center[i])<0.000001));
  await evaluate('document.getElementById("basemap").value="esri-hybrid";document.getElementById("basemap").dispatchEvent(new Event("change"))');
  await until('!document.getElementById("terrain-toggle").disabled && !!gbifViewer.map.getSource("esri-roads") && !!gbifViewer.map.getSource("gbif-terrain-dem") && gbifViewer.map.getTerrain()?.source==="gbif-terrain-dem"');
  await evaluate('document.getElementById("terrain-toggle").click()');await until('!gbifViewer.map.getTerrain() && gbifViewer.map.getPitch()<0.1');
  assert.equal(await evaluate('document.getElementById("terrain-toggle").textContent'),'2D');
  assert(await evaluate('document.getElementById("north-toggle").getBoundingClientRect().top>document.getElementById("terrain-toggle").getBoundingClientRect().top && document.getElementById("terrain-toggle").getBoundingClientRect().top>document.querySelector(".maplibregl-ctrl-zoom-out").getBoundingClientRect().top'));
  // Reproduce the reported photograph clipping with the user's actual occurrence.
  const photoVisibility=[];
  for(const size of [{width:1500,height:980,mobile:false},{width:1280,height:720,mobile:false},{width:390,height:844,mobile:true}]){
    await send('Emulation.setDeviceMetricsOverride',{...size,deviceScaleFactor:1});await pause(150);
    await evaluate('gbifViewer.selectObservation("4978365738",false)');
    await until('!!document.querySelector("#detail img") && document.querySelector("#detail img").complete && document.querySelector("#detail img").naturalWidth>0');
    const visible=await evaluate('(()=>{const p=document.getElementById("side"),r=p.getBoundingClientRect(),i=document.querySelector("#detail img").getBoundingClientRect(),h=document.querySelector(".panel-header").getBoundingClientRect();return {scroll:p.scrollTop,top:i.top,bottom:i.bottom,panelBottom:r.bottom,viewport:innerHeight,fullyVisible:i.top>=h.bottom && i.bottom<=r.bottom && i.bottom<=innerHeight,collapsed:!document.querySelector("#detail details").open}})()');
    assert(visible.fullyVisible&&visible.collapsed&&visible.scroll===0,JSON.stringify({size,visible}));
    photoVisibility.push({size,...visible});
    shot=await send('Page.captureScreenshot',{format:'png'});
    await fs.writeFile(path.join(root,`viewer/photo-${size.width}x${size.height}.png`),Buffer.from(shot.data,'base64'));
  }
  await evaluate('document.querySelector("#detail details").open=true');
  assert.match(await evaluate('document.querySelector("#detail details").textContent'),/Licencia del registro/);
  await evaluate('document.getElementById("close-detail").click()');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await pause(300);
  assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true);
  assert(await evaluate('document.documentElement.scrollHeight<=innerHeight+1 && document.querySelector(".legend").getBoundingClientRect().bottom<=innerHeight+1'));
  shot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(root,'viewer/mobile.png'),Buffer.from(shot.data,'base64'));
  const gbifRequests=requests.filter(u=>/^https?:\/\/([^/]*\.)?gbif\.org\//.test(u));
  assert.deepEqual(gbifRequests,[]);assert.deepEqual(exceptions,[]);
  const hashes={};for(const file of ['index.html','viewer/gbif-viewer.js','viewer/gbif-viewer.css','viewer/gbif-review-file.js','viewer/data.js','viewer/base-styles.js'])hashes[file]=createHash('sha256').update(await fs.readFile(path.join(root,file))).digest('hex');
  const report={checked_at:new Date().toISOString(),status:'passed',records:1928,sha256:hashes,photo_visibility:photoVisibility,
    tests:['3D real terrarium source and pitch; terrain survives basemap switch; north preserves center, zoom and pitch; 2D removes terrain; controls below zoom','file autosave: real FileSystemFileHandle writes, existing file merged without truncation, remembered handle in IndexedDB, recovery after localStorage loss, rapid changes, failed disk write preserves committed file, retry','review defaults pending; approved (Aceptada)/doubtful/pending/rejected changes and filters; rejected disk autosave and import roundtrip; legacy approved preserved; reload persistence; export/import roundtrip; invalid imports rejected atomically; newest decisions preserved; failed storage write preserves state','21 profiles plus all','all four existing basemap configurations','species and uncertainty filters',
      'real marker click','local photos render','selection survives basemap switch','unknown uncertainty remains null with illustrative red 500m circles',
      'filters/photos work with external requests blocked','empty results','mobile no horizontal overflow',
      '1928 circles initially visible: 747 published and 1181 illustrative','uncertainty toggle hides and restores circles',
      'circle radius in meters matches published value','circle counts follow precision filters: 34, 154, 1181',
      'combined <=1km and unknown: 1774 all species, 77 edulis; counter and circles agree',
      'local DEM altitude and municipality rendered immediately after coordinates',
      'missing municipality shown explicitly','full-width map and compact header; observation browser removed',
      'closable detail overlay','restored form controls and counter synchronized on pageshow',
      'coincident cluster exposes the two verified GBIF records independently',
      'map and legend fit viewport vertically on desktop/mobile; detail panel scrolls internally',
      'reported occurrence photo fully visible without scrolling at 1500x980, 1280x720, 390x844',
      'secondary fields remain available in expandable section'],
    gbif_network_requests:gbifRequests,remote_hosts:[...new Set(requests.filter(u=>/^https?:/.test(u)).map(u=>new URL(u).hostname))],
    runtime_exceptions:exceptions};
  await fs.writeFile(path.join(root,'viewer/browser-validation.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
}catch(error){
  if(ws){
    const state=await evaluate('({pitch:window.gbifViewer?.map.getPitch(),terrain:window.gbifViewer?.map.getTerrain(),sources:Object.keys(window.gbifViewer?.map.getStyle()?.sources||{}),layers:window.gbifViewer?.map.getStyle()?.layers?.map(l=>l.id),count:document.getElementById("count")?.textContent})').catch(()=>null);
    console.error(JSON.stringify({error:String(error),exceptions,state}));
    const shot=await send('Page.captureScreenshot',{format:'png'}).catch(()=>null);
    if(shot)await fs.writeFile(path.join(root,'viewer/failure.png'),Buffer.from(shot.data,'base64'));
  }
  throw error;
}finally{clearTimeout(timeout);if(ws)ws.close();chrome.kill();server.closeAllConnections();server.close();}
