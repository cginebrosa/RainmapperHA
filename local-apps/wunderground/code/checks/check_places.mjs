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
  const before=await evaluate('JSON.stringify({records:D.records,searches:D.searches})');
  await evaluate(`document.getElementById('place-query').value='Molló';document.getElementById('place-search').requestSubmit()`);
  await until('!document.getElementById("place-submit").disabled');
  const results=await evaluate('Array.from(document.querySelectorAll("#place-options button"),b=>b.textContent)');
  assert(results.some(x=>x.includes('Ripollès')),JSON.stringify(results));
  assert.equal(await evaluate('getComputedStyle(document.getElementById("place-results")).backgroundColor'),'rgb(255, 255, 255)');
  const shot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(root,'..','place-search-verified.png'),Buffer.from(shot.data,'base64'));
  await evaluate(`document.getElementById('investigate').click();Array.from(document.querySelectorAll('#place-options button')).find(b=>b.textContent.includes('Ripollès')).click()`);
  await until('!map.isMoving()');
  const center=await evaluate('({lat:map.getCenter().lat,lon:map.getCenter().lng})');
  assert(Math.abs(center.lat-42.35)<.05 && Math.abs(center.lon-2.4)<.05,JSON.stringify(center));
  assert.equal(await evaluate('JSON.stringify({records:D.records,searches:D.searches})'),before);
  assert(!requests.some(x=>/api\/(near|availability|review|promote)/.test(x)));
  assert.equal(await evaluate('document.getElementById("place-results").hidden'),true);
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
  assert.equal(await evaluate('document.querySelectorAll(".place-marker").length'),1);
  assert.equal(await evaluate('document.querySelector(".place-marker").textContent'),'Molló');
  await evaluate('document.querySelector(".place-marker").click()');
  assert(!requests.some(x=>/api\/(near|availability)/.test(x)));
  const markerShot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(root,'..','place-marker-verified.png'),Buffer.from(markerShot.data,'base64'));
  // Hold the next request to prove removal happens at submit, before any result.
  await evaluate(`window.realFetch=window.fetch;window.fetch=(...args)=>String(args[0]).endsWith('/api/places')?new Promise(resolve=>{window.finishPlaces=()=>resolve(new Response(JSON.stringify({results:[]}),{status:200}))}):window.realFetch(...args);document.getElementById('place-query').value='No result test';document.getElementById('place-search').requestSubmit()`);
  assert.equal(await evaluate('document.querySelectorAll(".place-marker").length'),0);
  await evaluate('window.finishPlaces();window.fetch=window.realFetch;undefined');
  await until('!document.getElementById("place-submit").disabled');
  assert.equal(await evaluate('document.querySelectorAll(".place-marker").length'),0);
  assert.equal(await evaluate('JSON.stringify({records:D.records,searches:D.searches})'),before);

  assert.equal(exceptions.length,0,JSON.stringify(exceptions));
  console.log(JSON.stringify({status:'passed',results,center,unchangedResearch:true,noWURequests:true}));

} finally { clearTimeout(timeout);ws?.close();chrome.kill();server.close(); }
