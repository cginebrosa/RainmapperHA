"use strict";
(() => {
  const $=id=>document.getElementById('gbif-import-'+id), labels=window.gbifImportLabels;
  const endpoint=window.location.pathname.replace(/\/mushrooms\/profiles\/?$/,'')+'/api/mushrooms/gbif-import';
  let token=null, busy=false, changed=false, sitePlan=null;
  function resetPlan(){sitePlan=null;$('sites-plan').hidden=true;$('review').hidden=!token;$('accept').textContent=labels.accept;}
  $('auto-sites').onchange=resetPlan;
  $('rows').addEventListener('change',resetPlan);
  function status(text){$('status').textContent=text;}
  function lock(value){busy=value;$('dialog').querySelectorAll('button,input,select').forEach(el=>el.disabled=value);if(!value)$('rows').querySelectorAll('[data-blocked]').forEach(el=>el.disabled=true);}
  async function request(action, body){
    const response=await fetch(endpoint+'?action='+action,{method:'POST',headers:{'X-Rainmapper-GBIF':'1','Content-Type':'application/json'},body:JSON.stringify(body||{})});
    const result=await response.json();if(!response.ok||!result.ok)throw Error(labels['error_'+result.error]||labels[result.error]||labels.error_network);return result;
  }
  async function run(work){if(busy)return;lock(true);try{await work();}catch(e){status(e.message||labels.error_network);}finally{lock(false);}}
  function show(result){token=result.token;resetPlan();$('rows').replaceChildren();$('review').hidden=false;$('accept').hidden=false;$('pending').replaceChildren();
    for(const row of result.rows){const tr=document.createElement('tr'),td=document.createElement('td'),check=document.createElement('input');check.type='checkbox';check.value=row.gbif_id;check.checked=row.status==='new';check.disabled=row.status!=='new';if(check.disabled)check.dataset.blocked='1';if(row.replaceable){const choice=document.createElement('select');choice.dataset.gbifId=row.gbif_id;choice.dataset.revision=row.existing_revision;for(const value of ['keep','replace']){const option=document.createElement('option');option.value=value;option.textContent=labels[value];choice.append(option);}td.append(choice);}else td.append(check);tr.append(td);
      for(const value of [row.gbif_id,row.species_name||row.species_id||'',row.observed_at?row.observed_at.split('-').reverse().join('/'):'',row.precision_m==null?'':row.precision_m+' m'+(row.assumed?' · '+labels.assigned:''),row.photos??'',(row.archived?labels.archived:(labels[row.status]||row.status))+(row.existing_id?' · '+row.existing_id:'')+(row.error?' · '+(labels['error_'+row.error]||labels.invalid):'')+(row.unlicensed?' · '+labels.unlicensed:'')]){const cell=document.createElement('td');cell.textContent=value;cell.style.padding='8px';tr.append(cell);} $('rows').append(tr);
    }status(result.rows.length+' · '+labels.pending);
  }
  async function pending(){const result=await request('pending');$('pending').replaceChildren();for(const item of result.pending){const box=document.createElement('p');box.textContent=labels.pending+' ';if(item.status==='ready'){const resume=document.createElement('button');resume.textContent=labels.resume;resume.onclick=()=>run(async()=>show(await request('resume',{token:item.token})));box.append(resume);}const cancel=document.createElement('button');cancel.textContent=labels.cancel;cancel.onclick=()=>run(async()=>{await request('cancel',{token:item.token});await pending();});box.append(cancel);$('pending').append(box);}}
  $('open').onclick=()=>{$('dialog').showModal();run(pending);};
  $('close').onclick=()=>{if(!busy){$('dialog').close();if(changed)window.location.reload();}};
  $('dialog').addEventListener('cancel',e=>{if(busy)e.preventDefault();});
  $('dialog').addEventListener('close',()=>{if(changed)window.location.reload();});
  $('all').onclick=()=>{resetPlan();$('rows').querySelectorAll('input:not([data-blocked])').forEach(el=>el.checked=true);};
  $('none').onclick=()=>{resetPlan();$('rows').querySelectorAll('input').forEach(el=>el.checked=false);$('rows').querySelectorAll('select').forEach(el=>el.value='keep');};
  $('preview').onclick=()=>run(async()=>{const file=$('file').files[0];if(!file)throw Error(labels.choose);if(file.size>128*1024*1024)throw Error(labels.error_limit);if(token){await request('cancel',{token});token=null;}
    status(labels.busy);$('progress').hidden=false;$('progress').removeAttribute('value');
    try{const result=await new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST',endpoint+'?action=upload');xhr.setRequestHeader('X-Rainmapper-GBIF','1');xhr.setRequestHeader('Content-Type','application/zip');xhr.upload.onprogress=e=>{if(e.lengthComputable){$('progress').max=e.total;$('progress').value=e.loaded;}};xhr.onerror=()=>reject(Error(labels.error_network));xhr.onload=()=>{try{const result=JSON.parse(xhr.responseText);if(xhr.status!==200||!result.ok)throw Error(labels['error_'+result.error]||labels[result.error]||labels.error_network);resolve(result);}catch(e){reject(e);}};xhr.send(file);});show(result);}finally{$('progress').hidden=true;}
  });
  function renderPlan(plan){
    sitePlan=plan;status(labels.sites_review);const box=$('sites-plan');box.replaceChildren();box.hidden=false;$('review').hidden=true;
    const title=document.createElement('h3');title.textContent=labels.sites_review;box.append(title);
    const summary=document.createElement('p');summary.textContent=[['area','created','sites_area_created'],['area','expanded','sites_area_expanded'],['micro_area','created','sites_micro_created']].map(([kind,action,label])=>labels[label]+': '+plan.changes.filter(c=>c.kind===kind&&c.action===action).length).join(' · ');box.append(summary);
    if(plan.changes.length){
      const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('role','img');svg.setAttribute('aria-label',labels.sites_review);
      const rings=plan.changes.flatMap(c=>c.geometry.type==='Polygon'?c.geometry.coordinates:c.geometry.coordinates.flat());
      const coords=rings.flat();const minX=Math.min(...coords.map(p=>p[0])),maxX=Math.max(...coords.map(p=>p[0])),minY=Math.min(...coords.map(p=>p[1])),maxY=Math.max(...coords.map(p=>p[1]));const scale=Math.cos((minY+maxY)*Math.PI/360),w=Math.max((maxX-minX)*scale,.001),h=Math.max(maxY-minY,.001);svg.setAttribute('viewBox',`${-w*.05} ${-h*.05} ${w*1.1} ${h*1.1}`);
      for(const c of plan.changes){const path=document.createElementNS(ns,'path'),rs=c.geometry.type==='Polygon'?c.geometry.coordinates:c.geometry.coordinates.flat();path.setAttribute('d',rs.map(r=>r.map((p,i)=>`${i?'L':'M'}${(p[0]-minX)*scale},${maxY-p[1]}`).join(' ')+'Z').join(' '));path.setAttribute('fill',c.kind==='area'?'#e6972b33':'#00a6d344');path.setAttribute('stroke',c.kind==='area'?'#e6972b':'#00a6d3');path.setAttribute('stroke-width',Math.max(w,h)/500);path.setAttribute('fill-rule','evenodd');const tip=document.createElementNS(ns,'title');tip.textContent=c.name;path.append(tip);svg.append(path);}box.append(svg);
    }
    const table=document.createElement('table'),head=document.createElement('tr');for(const label of ['sites_action','sites_name']){const cell=document.createElement('th');cell.textContent=labels[label];head.append(cell);}const thead=document.createElement('thead');thead.append(head);table.append(thead);const body=document.createElement('tbody');
    for(const c of plan.changes){const tr=document.createElement('tr'),action=document.createElement('td'),name=document.createElement('td');action.textContent=labels[c.kind==='micro_area'?'sites_micro_created':c.action==='created'?'sites_area_created':'sites_area_expanded'];if(c.action==='created'){const input=document.createElement('input');input.value=c.name;input.maxLength=160;input.dataset.siteName=c.id;name.append(input);}else name.textContent=c.name;tr.append(action,name);body.append(tr);}table.append(body);box.append(table);
    const details=document.createElement('details'),caption=document.createElement('summary');caption.textContent=labels.sites_assignments;details.append(caption);for(const [gid,a] of Object.entries(plan.assignments)){const line=document.createElement('div');line.textContent=`GBIF ${gid} → ${a.area_id} / ${a.micro_area_id}`;details.append(line);}box.append(details);
    const back=document.createElement('button');back.textContent=labels.sites_back;back.onclick=resetPlan;box.append(back);$('accept').textContent=labels.sites_confirm;
  }
  $('accept').onclick=()=>run(async()=>{
    const accepted=[...$('rows').querySelectorAll('input:checked:not([data-blocked])')].map(el=>el.value);
    const replacements=Object.fromEntries([...$('rows').querySelectorAll('select')].filter(el=>el.value==='replace').map(el=>[el.dataset.gbifId,el.dataset.revision]));
    if(!accepted.length&&!Object.keys(replacements).length&&!$('rows').querySelector('select'))throw Error(labels.no_selection);
    const selected=[...accepted,...Object.keys(replacements)];let gaps=0;
    if(sitePlan){
      let soilPending=0;
      const site_names=Object.fromEntries([...$('sites-plan').querySelectorAll('[data-site-name]')].map(el=>[el.dataset.siteName,el.value]));
      $('progress').hidden=false;$('progress').max=Math.max(1,sitePlan.changes.length);$('progress').value=0;
      try{for(const [index,c] of sitePlan.changes.entries()){status(`${labels.sites_prepare} ${index+1} / ${sitePlan.changes.length} · ${c.name}`);const prepared=await request('prepare_site',{token,plan_id:sitePlan.id,site_id:c.id});if(prepared.soilgrids_status==='pending')soilPending++;$('progress').value=index+1;}
        status(labels.saving);$('progress').removeAttribute('value');await finishCommit({token,accepted,replacements,sites_plan_id:sitePlan.id,site_names},sitePlan.observationGaps||0,soilPending);
      }finally{$('progress').hidden=true;}return;
    }
    $('progress').hidden=false;$('progress').max=Math.max(1,selected.length);$('progress').value=0;
    try{
      for(const [index,gbif_id] of selected.entries()){
        status(`${labels.preparing} ${index+1} / ${selected.length} · GBIF ${gbif_id}`);
        const prepared=await request('prepare',{token,gbif_id});if(prepared.gis_gaps)gaps++;
        $('progress').value=index+1;
      }
      if($('auto-sites').checked&&selected.length){status(labels.sites_planning);renderPlan({...await request('plan_sites',{token,accepted,replacements}),observationGaps:gaps});return;}
      status(`${labels.saving} ${selected.length} / ${selected.length}`);$('progress').removeAttribute('value');
      await finishCommit({token,accepted,replacements},gaps);
    }finally{$('progress').hidden=true;}
  });
  async function finishCommit(body,gaps,soilPending=0){
    const result=await request('commit',body);
    status(`${labels.done} · ${labels.created}: ${result.created} · ${labels.replaced}: ${result.replaced||0} · ${labels.skipped}: ${result.skipped} · ${labels.rejected}: ${result.rejected} · ${labels.gis_gaps}: ${gaps}`+(body.sites_plan_id?` · ${labels.sites_area_created}: ${result.areas_created||0} · ${labels.sites_area_expanded}: ${result.areas_expanded||0} · ${labels.sites_micro_created}: ${result.micro_areas_created||0} · ${labels.sites_soil_pending}: ${soilPending}`:''));
    token=null;sitePlan=null;changed=true;$('sites-plan').hidden=true;$('review').hidden=true;$('accept').hidden=true;
  }
  $('cancel').onclick=()=>run(async()=>{if(token){await request('cancel',{token});token=null;}resetPlan();$('review').hidden=true;$('accept').hidden=true;status(labels.cancel);await pending();});
})();
