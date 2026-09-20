// Default: isolated fixture. --local-read-only checks the existing HA local UI
// and opens its GIS preview, without saving, training or persistent writes.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawn} from 'node:child_process';

const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'observation-gis-'));
const form=execFileSync('.venv/bin/python',['-c',`
import sys
from unittest.mock import patch
sys.path.insert(0,'rainmapper-app/app')
import mushroom_profiles_ui as ui
import mushroom_observation_gis_ui as recovery_ui
catalogs={'host_taxa':[{'id':'host_oak','scientific_name':'Oak'},{'id':'host_pine','scientific_name':'Pine'}],
          'soil_types':[{'id':'soil_old','label':'Old soil'},{'id':'soil_new','label':'New soil'}]}
row={'observation_id':'fixture','location':{'lat':42,'lon':2},'altitude':{'meters':900,'source':'manual'},
     'site_context':{'observed_host_ids':['host_oak'],'observed_soil_tendency_ids':['soil_old']}}
with patch.object(ui,'known_site_select_options',return_value='<option value=""></option>'):
    print(ui.render_observation_form_modal([],catalogs,row,modal_id='edit-fixture',action='update_observation',title='Fixture'))
print(recovery_ui.script())
print(recovery_ui.map_assets())
`],{encoding:'utf8'});
const checks=String.raw`
(async()=>{
 const form=document.querySelector('form'),status=document.createElement('pre');status.id='test-result';document.body.append(status);
 const eq=(a,b,message)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error(message+': '+JSON.stringify(a));};
 let submits=0;form.addEventListener('submit',e=>{e.preventDefault();submits++;});
 const report={version:1,location:{lat:42,lon:2},recovered_at:'2026-09-20',
   values:{host_ids:['host_pine'],soil_tendency_ids:['soil_new'],forest_type_ids:[],habitat_feature_ids:[]},
   sources:{host_ids:['mfe25'],soil_tendency_ids:['geology_50000']},forest:{status:'available'},gaps:[],altitude_m:950,altitude_source:'dem_5m'};
 window.fetch=async()=>({ok:true,json:async()=>({ok:true,report})});
 const tick=()=>new Promise(r=>setTimeout(r,0));
 const recover=async()=>{form.querySelector('[data-observation-gis-recover]').click();await tick();};
  const modal=()=>document.querySelector('dialog.observation-gis-dialog');
  const mode=(label,value)=>{modal().querySelector('[aria-label="'+label+'"]').value=value;};
  const apply=()=>[...modal().querySelectorAll('button')].find(e=>e.textContent==='Aplicar al borrador').click();
 const value=()=>JSON.parse(form.elements.gis_recovery_json.value);
 try {
   eq(form.querySelector('[data-observation-gis-recover]').previousElementSibling.hasAttribute('data-observation-draft-map'),true,'button immediately after Map');
   eq(form.querySelector('.observation-evidence-panel [data-observation-gis-recover]'),null,'right column free of GIS controls');
   await recover();eq(modal().open,true,'review is a modal');eq(modal().closest('form'),null,'modal outside observation form');
   eq([...modal().querySelectorAll('select')].map(e=>e.value),['replace','replace','replace'],'different values default to replace');
   eq(document.activeElement.textContent,'Aplicar al borrador','apply has default focus');
   eq(document.activeElement.classList.contains('primary'),true,'apply is primary action');
   modal().querySelectorAll('select').forEach(e=>e.value='keep');
   apply();eq(modal().open,false,'apply closes only the review');eq(value(),{},'keep must preserve all original evidence');
   eq(form.querySelector('[value=host_oak]').checked,true,'keep field');
   await recover();mode('Hosts','merge');mode('Suelo','keep');mode('Altitud','keep');apply();
   eq(value().values.host_ids,['host_pine'],'merge adds GIS');eq(form.querySelector('[value=host_oak]').checked,true,'merge preserves field');
   eq(form.querySelector('[value=host_pine]').indeterminate,true,'GIS host is visibly selected separately from field');
   eq(form.querySelector('[value=host_pine]').closest('label').classList.contains('gis-selected'),true,'GIS chip marked');
   eq(new FormData(form).getAll('observed_host_ids'),['host_oak'],'GIS host is not submitted as field evidence');
   await recover();mode('Hosts','keep');mode('Suelo','replace');mode('Altitud','replace');apply();
   eq(form.querySelector('[value=soil_old]').checked,false,'replace clears previous field soil');
   eq(value().values.soil_tendency_ids,['soil_new'],'replace adds GIS soil');eq(form.elements.altitude_m.value,'950','DEM applied');
   const before=form.elements.gis_recovery_json.value;await recover();
   eq(modal().querySelector('[aria-label=Suelo]').value,'keep','equal lists default to keep');
   eq(modal().querySelector('[aria-label=Altitud]').value,'keep','equal numerical altitude defaults to keep');
   [...modal().querySelectorAll('button')].find(e=>e.textContent==='Cancelar recuperación').click();
   eq(modal().open,false,'cancel closes review');
   eq(form.elements.gis_recovery_json.value,before,'cancel keeps draft');
   eq(submits,0,'apply never submits');eq(location.hash,'#edit-fixture','form remains open');
   await recover();mode('Hosts','replace');apply();
   eq(form.querySelector('[value=host_oak]').checked,false,'replace removes former field hosts');
   eq(form.querySelector('[value=host_pine]').indeterminate,true,'replace marks recovered hosts');
   eq(form.querySelector('[value=soil_new]').indeterminate,true,'replace marks recovered soil');
   eq(new FormData(form).getAll('observed_host_ids'),[],'replaced hosts keep GIS provenance on submit');
   const reopened=form.cloneNode(true);document.body.append(reopened);window.rainmapperObservationGIS.refresh();
   eq(reopened.querySelector('[value=host_pine]').indeterminate,true,'saved GIS rehydrates on reopening form');reopened.remove();
   form.querySelector('[value=host_pine]').closest('label').click();
   eq(value().values.host_ids,undefined,'click removes a GIS host from draft');
   eq(form.querySelector('[value=host_pine]').checked,false,'removal does not invent field evidence');
   eq(form.querySelector('[value=host_pine]').indeterminate,false,'removed GIS selection cleared');
   form.querySelector('[value=host_oak]').checked=true;
   form.elements.location_lat.value='42.1';form.elements.location_lat.dispatchEvent(new Event('input',{bubbles:true}));
   eq(value(),{},'moving point clears GIS');eq(form.querySelector('[value=soil_new]').indeterminate,false,'moving point clears GIS marks');eq(form.querySelector('[value=host_oak]').checked,true,'moving point preserves field');
   const card=document.createElement('div');card.className='evidence-map-modal';
   card.innerHTML='<button class="observation-gis-toggle"></button><aside class="observation-map-gis-panel" hidden></aside><div data-coordinate-toolbar><button>Coordinates</button><button disabled>Confirm</button></div><form class="observation-site-assignment"><input value="original"><button>Assign</button></form><div class="fixture-map"></div>';
   document.getElementById('edit-fixture').append(card);
   window.maplibregl={Marker:class {constructor(){this.el=document.createElement('div');}setLngLat(){return this;}addTo(){return this;}getElement(){return this.el;}remove(){}}};
   const map={resize(){},on(){}};let resolveRequest;const requests=[];
   window.fetch=url=>new Promise(resolve=>{requests.push(String(url));resolveRequest=resolve;});
   const inspector=window.rainmapperObservationMapGIS.attach(map,card.querySelector('.fixture-map'),{lat:42,lon:2},()=>true);
   card.querySelector('button').click();eq(requests.length,1,'initial point queried');
   inspector.select({lat:43,lng:3});inspector.select({lat:44,lng:4});eq(requests.length,1,'no concurrent point requests');
   resolveRequest({ok:true,json:async()=>({ok:true,report})});await tick();
   eq(requests.length,2,'only latest pending point queried');eq(requests[1].includes('location_lat=44'),true,'latest coordinates');
   eq(card.querySelector('dl'),null,'stale response not shown');
   resolveRequest({ok:true,json:async()=>({ok:true,report,labels:{host_ids:{host_pine:'Pine'}}})});await tick();
   eq(card.querySelector('dl').textContent.includes('Pine'),true,'returned labels visible');
   eq(card.querySelector('[data-coordinate-toolbar] button').disabled,true,'coordinate edits disabled while inspecting');
   inspector.select({lat:45,lng:5});card.querySelector('button').click();
   resolveRequest({ok:true,json:async()=>({ok:true,report})});await tick();
   eq(card.querySelector('aside').hidden,true,'late response cannot reopen inspector');
   eq(card.querySelector('[data-coordinate-toolbar] button').disabled,false,'coordinate mode restored');
   eq(card.querySelectorAll('[data-coordinate-toolbar] button')[1].disabled,true,'original disabled state restored');
   eq(card.querySelector('input').value,'original','inspector preserves site assignment');
   eq(submits,0,'inspector never saves');
   status.textContent='PASS footer position, separate modal, keep, merge, replace, cancel, coordinate invalidation, no save and open form';
 } catch(error) {status.textContent='FAIL '+error.stack;}
})();`;
let chrome, socket;
try {
 const fixture=path.join(temporary,'fixture.html');
 fs.writeFileSync(fixture,'<!doctype html><html><body>'+form+'<script>'+checks+'</script></body></html>');
 const profile=path.join(temporary,'chrome');
 chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
   '--headless','--no-first-run','--disable-background-networking','--use-angle=swiftshader','--enable-unsafe-swiftshader',
   '--user-data-dir='+profile,'--remote-debugging-port=0','about:blank'
 ],{stdio:'ignore'});
 const pause=ms=>new Promise(r=>setTimeout(r,ms));
 let port;
 for(let i=0;i<100;i++) {try{port=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0];break;}catch{await pause(100);}}
 assert.ok(port,'Chrome debugging endpoint unavailable');
 const pages=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();
 socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
 await new Promise(resolve=>socket.addEventListener('open',resolve,{once:true}));
 let serial=0;const pending=new Map();const browserErrors=[];
 socket.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Runtime.exceptionThrown')browserErrors.push(m.params.exceptionDetails);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}});
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
 await send('Page.enable');await send('Runtime.enable');
 const local=process.argv.includes('--local-read-only');
 await send('Page.navigate',{url:local?'http://127.0.0.1:8101/mushrooms/profiles?section=observations':'file://'+fixture+'#edit-fixture'});
 if(local) {
   let ready=false;
   for(let i=0;i<100;i++) {
     const r=await send('Runtime.evaluate',{expression:"!!window.rainmapperObservationGIS && !!document.querySelector('[id^=edit-observation-] [data-observation-gis-recover]')",returnByValue:true});
     if(r.result?.value){ready=true;break;}await pause(100);
   }
   assert.ok(ready,'HA local did not serve the recovery controls');
   if(process.argv.includes('--apply-draft'))await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
   await send('Runtime.evaluate',{expression:`(()=>{const modal=document.querySelector('[id^=edit-observation-]');location.hash=modal.id;window.__gisLocalModal=modal;
     if(${process.argv.includes('--apply-draft')}) {
       const f=modal.querySelector('form');f.elements.location_lat.value='42.2548768';f.elements.location_lon.value='2.2451714';f.elements.location_input.value='42.2548768, 2.2451714';
       f.querySelectorAll('[name=observed_host_ids]').forEach(e=>e.checked=['host_abies_alba','host_pinus_nigra','host_pinus_sylvestris'].includes(e.value));
       f.elements.gis_recovery_json.value='{}';window.rainmapperObservationGIS.refresh();
     }
     modal.querySelector('[data-observation-gis-recover]').click();})()`});
   let done=false;
   for(let i=0;i<300;i++) {
     const r=await send('Runtime.evaluate',{expression:"!window.__gisLocalModal.querySelector('[data-observation-gis-recover]').disabled",returnByValue:true});
     if(r.result?.value){done=true;break;}await pause(100);
   }
   assert.ok(done,'HA local recovery preview timed out');
   const primary=await send('Runtime.evaluate',{expression:"document.activeElement?.textContent==='Aplicar al borrador' && document.activeElement.classList.contains('primary')",returnByValue:true});
   assert.ok(primary.result.value,'Apply is the focused primary action in HA local');
   const checked=await send('Runtime.evaluate',{expression:`(()=>{const m=window.__gisLocalModal,d=document.querySelector('dialog.observation-gis-dialog'),b=m.querySelector('[data-observation-gis-recover]');return {open:location.hash==='#'+m.id,preview:d?.open&&!d.querySelector('[data-observation-gis-review]').hidden,status:d?.querySelector('[data-gis-dialog-status]').textContent,fields:d?.querySelectorAll('[data-observation-gis-review] select').length,afterMap:b.previousElementSibling.hasAttribute('data-observation-draft-map'),rightColumnFree:!m.querySelector('.observation-evidence-panel [data-observation-gis-recover]')};})()`,returnByValue:true});
   assert.ok(checked.result?.value.open && checked.result?.value.preview,JSON.stringify(checked.result?.value));
   assert.ok(checked.result.value.afterMap && checked.result.value.rightColumnFree,'Footer layout');
   const contrast=await send('Runtime.evaluate',{expression:`(()=>{
     const d=document.querySelector('dialog.observation-gis-dialog');
     const rgb=s=>s.match(/[0-9.]+/g).slice(0,3).map(Number);
     const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
     const bg=lum(rgb(getComputedStyle(d).backgroundColor));
     return [...d.querySelectorAll('h2,th,td')].filter(e=>e.textContent.trim()).map(e=>{
       const fg=lum(rgb(getComputedStyle(e).color));return {text:e.textContent.trim(),ratio:(Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05)};
     });
   })()`,returnByValue:true});
   assert.ok(contrast.result?.value?.length>5,'Review has visible labels and data');
   assert.ok(contrast.result.value.every(x=>x.ratio>=4.5),'Unreadable GIS text: '+JSON.stringify(contrast.result.value));
   if(process.argv.includes('--screenshot')) {
     const shot=await send('Page.captureScreenshot',{format:'png'});
     fs.mkdirSync('tmp/gis-recovery-20260920',{recursive:true});
     fs.writeFileSync('tmp/gis-recovery-20260920/recovery-readable.png',Buffer.from(shot.data,'base64'));
   }
   await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
   await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
   await pause(100);
   const dismissed=await send('Runtime.evaluate',{expression:"!document.querySelector('dialog.observation-gis-dialog').open && location.hash==='#'+window.__gisLocalModal.id",returnByValue:true});
   assert.ok(dismissed.result.value,'Escape closes only GIS modal');
   console.log('PASS HA local: observation form open, GIS/DEM preview returned, no save',JSON.stringify(checked.result.value));
   if(process.argv.includes('--apply-draft')) {
     await send('Runtime.evaluate',{expression:"window.__gisLocalModal.querySelector('[data-observation-gis-recover]').click()"});
     for(let i=0;i<300;i++) {
       const r=await send('Runtime.evaluate',{expression:"!!document.querySelector('dialog.observation-gis-dialog [aria-label=Hosts]')",returnByValue:true});
       if(r.result?.value)break;await pause(100);
     }
     const applied=await send('Runtime.evaluate',{expression:`(()=>{
       const d=document.querySelector('dialog.observation-gis-dialog'),f=window.__gisLocalModal.querySelector('form');
       d.querySelector('[aria-label=Hosts]').value='replace';d.querySelector('[aria-label=Suelo]').value='replace';d.querySelector('[aria-label=Altitud]').value='keep';
       [...d.querySelectorAll('button')].find(b=>b.textContent==='Aplicar al borrador').click();
       const r=JSON.parse(f.elements.gis_recovery_json.value),marks=[...f.querySelectorAll('label.gis-selected')];
       const status=f.querySelector('[data-observation-gis-status]').getBoundingClientRect(),bar=f.querySelector('.profile-action-bar').getBoundingClientRect();
       return {hosts:r.values.host_ids,soil:r.values.soil_tendency_ids,marked:marks.map(l=>l.querySelector('input').value),colors:marks.map(l=>getComputedStyle(l.querySelector('span')).backgroundColor),manual:new FormData(f).getAll('observed_host_ids'),open:location.hash==='#'+window.__gisLocalModal.id,closed:!d.open,statusBelow:status.top>=bar.bottom,actionsInside:bar.right<=f.getBoundingClientRect().right};
     })()`,returnByValue:true});
     const v=applied.result?.value;assert.ok(v,JSON.stringify(applied));
     assert.deepEqual(v.hosts,['host_corylus_avellana','host_pinus_sylvestris','host_quercus_humilis','host_quercus_spp']);
     assert.deepEqual(v.soil,['soil_calcareous']);assert.ok([...v.hosts,...v.soil].every(id=>v.marked.includes(id)));
     assert.ok(v.colors.every(c=>c==='rgb(22, 107, 98)'),JSON.stringify(v));
     assert.deepEqual(v.manual,[]);assert.ok(v.open&&v.closed&&v.statusBelow&&v.actionsInside,JSON.stringify(v));
     if(process.argv.includes('--screenshot')) {
       const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync('tmp/gis-recovery-20260920/applied-gis-selection.png',Buffer.from(shot.data,'base64'));
     }
     console.log('PASS HA local apply draft: four hosts and calcareous soil visibly marked GIS, separate provenance, footer below buttons, no save');
   }

   if(process.argv.includes('--map')) {
     await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false});
     await send('Runtime.evaluate',{expression:"window.__gisLocalModal.querySelector('[data-observation-draft-map]').click()"});
     let mapReady=false;
     for(let i=0;i<300;i++) {
       const r=await send('Runtime.evaluate',{expression:"(()=>{const m=window.rainmapperObservationMaps?.get(location.hash.slice(1));if(m?.rainmapperObservationMarkers?.size){window.__gisMap=m;return true;}return false;})()",returnByValue:true});
       if(r.result?.value){mapReady=true;break;}await pause(100);
     }
     if(!mapReady) {
       const debug=await send('Runtime.evaluate',{expression:"JSON.stringify({hash:location.hash,library:typeof maplibregl,maps:window.rainmapperObservationMaps?.size,targets:[...document.querySelectorAll('.modal-layer:target .observation-site-map')].map(n=>({id:n.dataset.observationSiteMap,ready:n.dataset.ready})),errors:document.querySelector('.modal-layer:target')?.textContent.slice(0,250)})",returnByValue:true});
       console.log('MAP DEBUG',debug.result?.value,JSON.stringify(browserErrors));
     }
     assert.ok(mapReady,'Observation map failed to load');
     const started=await send('Runtime.evaluate',{expression:`(()=>{
       const card=document.querySelector('.modal-layer:target .evidence-map-modal');window.__gisMapCard=card;
       window.__gisMapBefore=[...card.querySelectorAll('input')].map(e=>e.name+'='+e.value).join('&');
       card.querySelector('.observation-gis-toggle').click();
       return card.querySelector('.observation-gis-toggle').getAttribute('aria-pressed');
     })()`,returnByValue:true});assert.equal(started.result?.value,'true');
     async function waitForGis() {
       for(let i=0;i<300;i++) {
         const r=await send('Runtime.evaluate',{expression:"!!window.__gisMapCard.querySelector('.observation-map-gis-panel dl')",returnByValue:true});
         if(r.result?.value)return;await pause(100);
       }
       throw Error('Map GIS did not return data');
     }
     await waitForGis();
     const layout=await send('Runtime.evaluate',{expression:`(()=>{
       const c=window.__gisMapCard,p=c.querySelector('.observation-map-gis-panel'),photo=c.querySelector('.observation-map-photo-strip');
       const rect=p.getBoundingClientRect(),pr=photo?.getBoundingClientRect();
       return {text:p.textContent,noOverlap:[...c.querySelectorAll('[data-coordinate-toolbar] button')].every(b=>b.getBoundingClientRect().right<=rect.left),rightOfPhoto:!pr||rect.left>=pr.right,inside:rect.right<=innerWidth,coordinateEditingDisabled:c.querySelector('[data-coordinate-start]').disabled};
     })()`,returnByValue:true});
     assert.ok(layout.result.value.noOverlap&&layout.result.value.rightOfPhoto&&layout.result.value.inside,JSON.stringify(layout.result.value));
     assert.ok(layout.result.value.coordinateEditingDisabled);
     // The same map event fired by a user click: point lookup must not select a site or move the observation.
     const clicked=await send('Runtime.evaluate',{expression:"window.__gisMap.fire('click',{lngLat:new maplibregl.LngLat(2.2451714,42.2548768),point:window.__gisMap.project([2.2451714,42.2548768]),originalEvent:new MouseEvent('click')})"});
     assert.ok(!clicked.exceptionDetails,JSON.stringify(clicked.exceptionDetails));
     await waitForGis();
     const point=await send('Runtime.evaluate',{expression:"window.__gisMapCard.querySelector('.observation-map-gis-panel').textContent",returnByValue:true});
     assert.ok(point.result.value.includes('42.2548768, 2.2451714'),point.result.value);
     assert.ok(!point.result.value.includes('host_quercus'),'Host labels should be translated');
     assert.ok(point.result.value.includes('MFE25'));
     if(process.argv.includes('--screenshot')) {
       const shot=await send('Page.captureScreenshot',{format:'png'});
       fs.mkdirSync('tmp/gis-recovery-20260920',{recursive:true});
       fs.writeFileSync('tmp/gis-recovery-20260920/map-inspector.png',Buffer.from(shot.data,'base64'));
     }

     const after=await send('Runtime.evaluate',{expression:`(()=>{const c=window.__gisMapCard;c.querySelector('.observation-gis-toggle').click();return {hidden:c.querySelector('.observation-map-gis-panel').hidden,unchanged:window.__gisMapBefore===[...c.querySelectorAll('input')].map(e=>e.name+'='+e.value).join('&'),enabled:!c.querySelector('[data-coordinate-start]').disabled};})()`,returnByValue:true});
     assert.ok(after.result.value.hidden&&after.result.value.unchanged&&after.result.value.enabled,JSON.stringify(after.result.value));
     console.log('PASS HA local map: point GIS data, readable labels, panel beside photo, toggle and unchanged coordinates/sites');
   }

 } else {
 let result;
 for(let i=0;i<100;i++) {
   const r=await send('Runtime.evaluate',{expression:"document.getElementById('test-result')?.textContent",returnByValue:true});
   result=r.result?.value;if(result)break;await pause(100);
 }
 assert.ok(result?.startsWith('PASS'),result||'Browser did not complete the fixture');
 console.log(result);
 }
} finally {
 socket?.close();chrome?.kill('SIGTERM');
 await new Promise(r=>setTimeout(r,200));
 if(chrome?.exitCode===null)chrome.kill('SIGKILL');
 fs.rmSync(temporary,{recursive:true,force:true,maxRetries:3,retryDelay:100});
}
