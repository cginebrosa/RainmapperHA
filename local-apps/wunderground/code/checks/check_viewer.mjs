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
const testURL=pathToFileURL(path.join(root,"index.html")).href;
const profile=await fs.mkdtemp(path.join(os.tmpdir(),'rainmapper-coverage-check-'));
const chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
  '--headless','--no-first-run','--disable-background-networking','--use-angle=swiftshader','--enable-unsafe-swiftshader',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore'});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let pageLoaded=null;
async function navigate(method,params={}){const ready=new Promise(resolve=>{pageLoaded=resolve;});await send(method,params);await ready;}
let ws,serial=0;const waiting=new Map(),requests=[],responses=[],exceptions=[];
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
  ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const t=waiting.get(m.id);waiting.delete(m.id);m.error?t.reject(m.error):t.resolve(m.result);}else if(m.method==='Page.loadEventFired'){pageLoaded?.();pageLoaded=null;}else if(m.method==='Network.requestWillBeSent')requests.push(m.params.request.url);else if(m.method==='Network.responseReceived')responses.push({url:m.params.response.url,status:m.params.response.status});else if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails);});
  await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1500,height:980,deviceScaleFactor:1,mobile:false});
  await navigate('Page.navigate',{url:testURL});
  await until('typeof map !== "undefined" && map.getSource("candidates") && map.isSourceLoaded("candidates") && map.isSourceLoaded("stations")');
  assert.equal(await evaluate('chosen().length'),12);
  assert((await evaluate('map.queryRenderedFeatures({layers:["stations"]}).length'))>100);
  assert.equal(await evaluate('map.queryRenderedFeatures({layers:["candidates"]}).length'),12);
  await evaluate('document.getElementById("selection").value="new";update()');
  assert.equal(await evaluate('chosen().length'),143);
  await until('map.isSourceLoaded("candidates")');
  assert.deepEqual(await evaluate('Array.from(document.getElementById("basemap").options,o=>o.text)'),['Satélite+','Híbrido','Topográfico','Liberty']);
  await evaluate('document.getElementById("gaps").checked=false;document.getElementById("gaps").dispatchEvent(new Event("change"));document.getElementById("basemap").value="esri-hybrid";document.getElementById("basemap").dispatchEvent(new Event("change"))');
  await until('!!map.getLayer("esri-labels") && !!map.getSource("candidates") && map.isSourceLoaded("candidates") && map.isSourceLoaded("esri-imagery") && map.isSourceLoaded("esri-labels")');
  assert.equal(await evaluate('chosen().length'),143);
  assert.equal(await evaluate('map.getLayoutProperty("gaps","visibility")'),'none');
  await evaluate('document.getElementById("basemap").value="esri-satellite-vector";document.getElementById("basemap").dispatchEvent(new Event("change"));document.getElementById("gaps").checked=true');
  await until('!!map.getLayer("satellite-place-label") && !!map.getSource("candidates") && map.isSourceLoaded("candidates") && map.isSourceLoaded("esri-imagery") && map.isSourceLoaded("openmaptiles")');
  assert(!requests.some(url=>url.includes('tile.openstreetmap.org/')));
  assert(responses.some(r=>r.url.includes('World_Imagery/MapServer/tile/') && r.status===200));
  await evaluate('document.getElementById("selection").value="short";update();document.getElementById("fit").click()');
  await until('!map.isMoving() && map.isSourceLoaded("candidates")');
  const shot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(root,'..','viewer-verified.png'),Buffer.from(shot.data,'base64'));
  assert.equal(exceptions.length,0,JSON.stringify(exceptions));
  console.log(JSON.stringify({status:'passed',basemaps:['Satélite+','Híbrido','Topográfico','Liberty'],testedLive:['Satélite+','Híbrido'],osmTileRequests:0,shortlist:12,newCandidates:143,stationFeatures:await evaluate('map.queryRenderedFeatures({layers:["stations"]}).length')}));
} finally { clearTimeout(timeout);ws?.close();chrome.kill();server.close(); }
