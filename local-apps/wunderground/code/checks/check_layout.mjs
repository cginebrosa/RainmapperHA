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
const testURL='http://127.0.0.1:8123/';
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
async function until(expression){for(let i=0;i<150;i++){try{if(await evaluate(expression))return;}catch(error){if(!/navigated|context|closed/.test(String(error.message||error)))throw error;}await pause(100);}throw Error(`Timed out: ${expression}; diagnostics=${JSON.stringify(await evaluate('({investigate,busy,message:document.getElementById("message").textContent,online:document.getElementById("online").open,ids:D.records.filter(r=>r.stationId.startsWith("IBROWSER")).map(r=>r.stationId)})'))}; exceptions=${JSON.stringify(exceptions)}`);}
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
  await until('ready && D.stations.length>0 && !!map.getSource("stations")');
  const candidateCount=await evaluate('chosen().length');
  await evaluate('document.getElementById("source-picker").open=true');
  const sources=['Meteocat','AEMET','Meteoclimatic','Wunderground'];
  for(let mask=0;mask<16;mask++){
    await evaluate(`Array.from(document.querySelectorAll('#station-source input')).forEach((input,i)=>{if(input.checked!==Boolean(${mask}&(1<<i)))input.click()});undefined`);
    const selected=sources.filter((_,i)=>mask&(1<<i));
    const result=await evaluate('({actual:chosenStations().length,sources:[...new Set(map.getSource("stations")._data.features.map(f=>f.properties.source))].sort(),candidates:chosen().length,expected:D.stations.filter(s=>Array.from(document.querySelectorAll("#station-source input:checked"),i=>i.value).includes(s.source)).length})');
    assert.equal(result.actual,result.expected);assert.deepEqual(result.sources,selected.sort());assert.equal(result.candidates,candidateCount);
  }
  await evaluate('Array.from(document.querySelectorAll("#station-source input")).forEach((input,i)=>{input.checked=i<2});update();document.getElementById("stations").click()');
  assert.equal(await evaluate('map.getLayoutProperty("stations","visibility")'),'none');
  assert.equal(await evaluate('document.getElementById("station-source").disabled'),true);
  await evaluate('document.getElementById("stations").click();document.getElementById("basemap").value="esri-hybrid";document.getElementById("basemap").dispatchEvent(new Event("change"))');
  await until('ready && !!map.getSource("stations") && map.isSourceLoaded("stations")');
  assert.deepEqual(await evaluate('[...new Set(map.getSource("stations")._data.features.map(f=>f.properties.source))].sort()'),['AEMET','Meteocat']);
  assert.equal(await evaluate('document.getElementById("source-summary").textContent'),'Fuentes actuales: 2 de 4');
  await evaluate('document.getElementById("source-picker").open=false;document.getElementById("basemap-toggle").click()');
  assert.equal(await evaluate('document.getElementById("basemap-panel").hidden'),false);
  assert(await evaluate('document.getElementById("basemap-toggle").getBoundingClientRect().top<document.getElementById("terrain").getBoundingClientRect().top'));
  assert(await evaluate('document.getElementById("clear-queries").getBoundingClientRect().top<document.getElementById("stations").getBoundingClientRect().top'));
  assert.equal(await evaluate('document.querySelector("header #basemap")'),null);
  assert(await evaluate('document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight+1'));
  const shot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(root,'..','research-layout-verified.png'),Buffer.from(shot.data,'base64'));
  assert.equal(exceptions.length,0,JSON.stringify(exceptions));
  console.log(JSON.stringify({status:'passed',combinations:16,candidatesUnchanged:true,preservedAfterBasemap:true,twoRows:true,basemapButtonBefore3D:true}));

} finally { clearTimeout(timeout);ws?.close();chrome.kill();server.close(); }
