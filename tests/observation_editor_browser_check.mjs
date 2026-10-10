// Isolated synthetic page and intercepted HTTP: no operational reads or saves.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawn} from 'node:child_process';

const fixture=JSON.parse(execFileSync('.venv/bin/python',['-c',String.raw`
import json
from unittest.mock import patch
from tests.test_web_server_auth import load_web_server_module
w=load_web_server_module(); ui=w.mushroom_profiles_ui
rows=[{'observation_id':f'fixture_{i}','species_id':'fixture','observed_at':'2026-10-01',
       'location':{'lat':42,'lon':2},'flush_abundance':'normal','validation_status':'valid',
       'calibration_use':'include'} for i in range(2)]
profiles=[{'species_id':'fixture','scientific_name':'Fixture species'}]
catalogs={'observation_flush_abundance':[{'id':'normal','label':'Normal'}],
          'observation_validation_statuses':[{'id':'valid','label':'Valid'}],
          'observation_calibration_uses':[{'id':'include','label':'Include'}]}
filters={'page':'1','page_size':'25','obs_species':'__all__','sort':'observed_at','dir':'desc'}
with patch.object(ui.mushroom_known_sites,'load_payload',return_value={}):
    section=ui.render_observations_section(None,profiles,catalogs,{'observations':rows},{},filters=filters)
    editors={r['observation_id']:ui.render_observation_edit_modals([r],profiles,catalogs,'',filters) for r in rows}
print(json.dumps({'page':w.html_page('Fixture',section,auto_refresh=False,page_class='mushroom-wide-page').decode(),'editors':editors}))
`],{encoding:'utf8',maxBuffer:8*1024*1024}));

const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'observation-editor-'));
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let chrome,socket;
try {
  chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
    '--headless','--no-first-run','--disable-background-networking','--user-data-dir='+temporary,
    '--remote-debugging-port=0','about:blank'
  ],{stdio:'ignore'});
  let port;
  for(let i=0;i<100;i++){try{port=fs.readFileSync(path.join(temporary,'DevToolsActivePort'),'utf8').split('\n')[0];break;}catch{await pause(100);}}
  assert.ok(port,'Chrome did not start');
  const pages=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();
  socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
  await new Promise(r=>socket.addEventListener('open',r,{once:true}));
  let serial=0;const pending=new Map(),errors=[],requests=[];
  let failNext=false,delayNext=false,delayed=null;
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
  const fulfill=(id,body,type='application/json',code=200)=>send('Fetch.fulfillRequest',{
    requestId:id,responseCode:code,responseHeaders:[{name:'Content-Type',value:type}],body:Buffer.from(body).toString('base64')
  });
  socket.addEventListener('message',async event=>{
    const m=JSON.parse(event.data);
    if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);return;}
    if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);
    if(m.method!=='Fetch.requestPaused')return;
    const {requestId,request}=m.params,url=new URL(request.url);
    try {
      if(url.pathname.endsWith('/observation-editor')){
        requests.push(request.url);
        const id=url.searchParams.get('obs_id');
        if(failNext){failNext=false;await fulfill(requestId,'{"ok":false}',undefined,503);return;}
        const reply=()=>fulfill(requestId,JSON.stringify({ok:true,observation_id:id,html:fixture.editors[id]}));
        if(delayNext){delayNext=false;delayed=reply;}else await reply();
      }else if(url.pathname.replace(/\/$/,'').endsWith('/mushrooms/profiles'))await fulfill(requestId,fixture.page,'text/html');
      else if(url.pathname.endsWith('/observation-detail'))await fulfill(requestId,'{"ok":true,"observation_id":"fixture_1","html":"<p>Selected fixture</p>"}');
      else await fulfill(requestId,'',url.pathname.endsWith('.css')?'text/css':'application/javascript');
    }catch(e){errors.push(String(e));}
  });
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'*'}]});
  const evaluate=async expression=>{
    const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));
    return result.result?.value;
  };
  const waitFor=async expression=>{
    for(let i=0;i<100;i++){if(await evaluate(expression))return;await pause(50);}
    console.error({errors,requests,state:await evaluate('({url:location.href,ready:document.readyState,forms:document.querySelectorAll("[id^=edit-observation-] form").length,status:[...document.querySelectorAll("[data-editor-status]")].map(e=>e.textContent)})')});
    throw Error('Timeout: '+expression);
  };
  const url='https://fixture.invalid/ingress/test/mushrooms/profiles?section=observations&obs_species=__all__&page=1';
  await send('Page.navigate',{url});
  await waitFor('!!document.querySelector("[data-observation-editor]") && document.readyState === "complete"');
  assert.equal(requests.length,0,'no eager editor requests');
  assert.equal(await evaluate('document.querySelectorAll("[id^=edit-observation-] form").length'),0);
  failNext=true;
  await evaluate(`document.querySelector('a[href="#edit-observation-fixture_0"]').click()`);
  await waitFor('!document.querySelector("#edit-observation-fixture_0 [data-editor-retry]").hidden');
  assert.ok(await evaluate('document.querySelector("#edit-observation-fixture_0 [role=status]").textContent.length>0'));
  await evaluate('document.querySelector("#edit-observation-fixture_0 [data-editor-retry]").click()');
  await waitFor('!!document.querySelector("#edit-observation-fixture_0 form")');
  assert.equal(requests.length,2);
  assert.ok(requests.every(r=>r.startsWith('https://fixture.invalid/ingress/test/api/mushrooms/observation-editor?')),'ingress prefix preserved');
  const fields=await evaluate(`(()=>{const f=document.querySelector('#edit-observation-fixture_0 form');
    f.elements.observer_name.value='Unsaved fixture';const d=new FormData(f);
    return [d.get('profile_action'),d.get('return_page'),d.get('return_obs_species'),f.enctype,
            !!f.querySelector('[data-observation-draft-map]'),!!f.querySelector('[data-observation-gis-recover]'),
            f.action];})()`);
  assert.deepEqual(fields.slice(0,6),['update_observation','1','__all__','multipart/form-data',true,true]);
  assert.ok(fields[6].startsWith(url),'save targets maintenance page');
  await evaluate('document.querySelector("#edit-observation-fixture_0 .modal-head a").click()');
  await waitFor('location.hash!=="#edit-observation-fixture_0"');
  await evaluate('location.hash="#edit-observation-fixture_0"');
  await pause(80);
  assert.equal(await evaluate('document.querySelector("#edit-observation-fixture_0 [name=observer_name]").value'),'Unsaved fixture');
  assert.equal(requests.length,2,'reopening retains draft and reuses loaded form');
  delayNext=true;
  await evaluate('location.hash="#edit-observation-fixture_1"');
  for(let i=0;i<100&&!delayed;i++)await pause(20);
  assert.ok(delayed);
  await evaluate('location.hash="#edit-observation-fixture_0"');
  await delayed();
  await waitFor('!!document.querySelector("#edit-observation-fixture_1 form")');
  assert.equal(await evaluate('location.hash'),'#edit-observation-fixture_0','late reply never reopens closed editor');
  assert.equal(await evaluate('document.querySelector("#edit-observation-fixture_0 [name=observer_name]").value'),'Unsaved fixture');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await pause(100);
  const mobile=await evaluate('(()=>{const r=document.querySelector("#edit-observation-fixture_0 .modal-head a").getBoundingClientRect();return {right:r.right,left:r.left,top:r.top,width:innerWidth,height:innerHeight};})()');
  assert.ok(mobile.right<=mobile.width && mobile.left>=0 && mobile.top>=0 && mobile.top<mobile.height,'mobile close visible: '+JSON.stringify(mobile));
  await send('Page.navigate',{url:url+'#edit-observation-fixture_1'});
  await waitFor('location.hash === "#edit-observation-fixture_1"');
  await send('Page.reload');
  for(let i=0;i<100&&requests.length<4;i++)await pause(20);
  await waitFor('!!document.querySelector("#edit-observation-fixture_1 form")');
  assert.equal(requests.length,4,'direct hash opens one editor after reload');
  await send('Page.navigate',{url:url.replace('/profiles?','/profiles/?')+'#edit-observation-fixture_0'});
  for(let i=0;i<100&&requests.length<5;i++)await pause(20);
  await waitFor('!!document.querySelector("#edit-observation-fixture_0 form")');
  assert.equal(requests.length,5,'trailing slash also loads through ingress');
  assert.ok(requests.at(-1).includes('/ingress/test/api/mushrooms/observation-editor?'));
  assert.equal(errors.length,0,JSON.stringify(errors));
  console.log('PASS lazy request, ingress, error/retry, draft, filters, multipart/GIS/map controls, late response, mobile close and deep link');
}finally{
  socket?.close();chrome?.kill('SIGTERM');
}
