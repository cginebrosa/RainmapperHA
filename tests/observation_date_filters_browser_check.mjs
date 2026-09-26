// Real calendar and keyboard interactions, using an isolated fixture store.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
const temp=await fs.mkdtemp(path.join(os.tmpdir(),'observation-dates-'));
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


 await send('Page.addScriptToEvaluateOnNewDocument',{source:"window.__submits=[];HTMLFormElement.prototype.submit=function(){__submits.push(Object.fromEntries(new FormData(this)));};"});
 await send('Emulation.setDeviceMetricsOverride',{width:1400,height:1000,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:base+'/mushrooms/fixture-filters'});await until("document.querySelector('[data-observation-date-picker]')?.dataset.observationDateReady==='1'&&typeof AirDatepicker==='function'");
 async function realClick(selector){const p=await evaluate(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);for(const type of ['mouseMoved','mousePressed','mouseReleased'])await send('Input.dispatchMouseEvent',{type,...p,button:type==='mouseMoved'?'none':'left',clickCount:type==='mouseMoved'?0:1});await pause(200);}

 async function choose(name,day){await realClick('#observation-'+name+'-display');const selector='.air-datepicker.-active- .air-datepicker-cell.-day-:not(.-other-month-)[data-date="'+day+'"]';await until(`!!document.querySelector(${JSON.stringify(selector)})`);const iso=await evaluate(`(()=>{const n=document.querySelector(${JSON.stringify(selector)});return n.dataset.year+'-'+String(Number(n.dataset.month)+1).padStart(2,'0')+'-'+String(n.dataset.date).padStart(2,'0');})()`);await realClick(selector);await pause(150);assert.equal(await evaluate(`document.querySelector('[name=${name}]').value`),iso);assert.equal(await evaluate(`document.getElementById('observation-${name}-display').value`),iso.split('-').reverse().join('/'));return iso;}
 const first=await choose('date_from',3);assert.deepEqual(await evaluate('__submits'),[{date_from:first,date_to:''}]);
 const second=await choose('date_from',4);assert.equal(await evaluate('__submits.length'),2);assert.equal(await evaluate('__submits.at(-1).date_from'),second);
 await realClick('#observation-date_from-display');await input('#observation-date_from-display','');for(const char of '05102025')await send('Input.insertText',{text:char});await pause(200);assert.equal(await evaluate("document.getElementById('observation-date_from-display').value"),'05/10/2025');assert.equal(await evaluate('__submits.length'),2);
 await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await pause(200);assert.equal(await evaluate('__submits.at(-1).date_from'),'2025-10-05');assert.equal(await evaluate('__submits.length'),3);await realClick('#outside');assert.equal(await evaluate('__submits.length'),3);
 await realClick('#observation-date_from-display');await input('#observation-date_from-display','31/02/2026');await realClick('#outside');assert.equal(await evaluate('__submits.length'),3);assert.equal(await evaluate("document.getElementById('observation-date_from-display').getAttribute('aria-invalid')"),'true');
 await input('#observation-date_from-display','06/10/2025');await realClick('#observation-date_from-display');await realClick('#outside');assert.equal(await evaluate('__submits.at(-1).date_from'),'2025-10-06');
 const to=await choose('date_to',8);assert.equal(await evaluate('__submits.at(-1).date_to'),to);assert.equal(await evaluate('__submits.at(-1).date_from'),'2025-10-06');
 await realClick('#observation-date_from-display');await until("!!document.querySelector('.air-datepicker.-active- .air-datepicker-button')");const clear=await evaluate("Array.from(document.querySelectorAll('.air-datepicker.-active- .air-datepicker-button')).findIndex(n=>n.textContent==='Limpiar')");assert.ok(clear>=0);await realClick('.air-datepicker.-active- .air-datepicker-button:nth-child('+(clear+1)+')');await pause(200);assert.equal(await evaluate('__submits.at(-1).date_from'),'');assert.equal(await evaluate('__submits.at(-1).date_to'),to);
 await send('Page.navigate',{url:base+'/mushrooms/fixture-filters?date_from=2025-10-05&date_to=2025-10-08'});await until("document.querySelector('[data-observation-date-picker]')?.dataset.observationDateReady==='1'");await pause(500);assert.equal(await evaluate('__submits.length'),0,'Initial selected dates must not resubmit');assert.equal(await evaluate("document.getElementById('observation-date_from-display').value"),'05/10/2025');
 console.log('PASS calendar selection/change/clear; typed digits with separators, Enter/blur, invalid dates; both filters; initial dates without resubmission');
 await shot('date-filters.png');
 assert.equal(errors.length,0,JSON.stringify(errors));console.log('Evidence: '+temp);
}finally{ws?.close();chrome?.kill('SIGTERM');server?.kill('SIGTERM');await fs.writeFile(path.join(temp,'server.log'),serverLog);}
