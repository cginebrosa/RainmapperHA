/* Recovery changes only the open form. The normal Save persists the draft. */
(() => {
  if (window.rainmapperObservationGIS) {window.rainmapperObservationGIS.refresh?.();return;}
  window.rainmapperObservationGIS = true;
  const fields = {host_ids:'Hosts', forest_type_ids:'Tipo de bosque', soil_tendency_ids:'Suelo', habitat_feature_ids:'Hábitat'};
  const node = (tag, text) => { const el=document.createElement(tag); if(text!=null)el.textContent=text; return el; };
  const input = (form,name) => form.elements.namedItem(name);
  const saved = form => JSON.parse(input(form,'gis_recovery_json').value || '{}');
  const manual = (form,key) => [...form.querySelectorAll(`[name="observed_${key}"]:checked`)].map(el=>el.value);
  const labels = (form,key,ids) => ids.map(id => {
    const el=[...form.querySelectorAll(`[name="observed_${key}"]`)].find(el=>el.value===id);
    return el?.closest('label')?.textContent.trim() || id;
  }).join(', ') || '—';
  function sync(form) {
    const value=saved(form);
    for(const key of Object.keys(fields)) {
      const ids=new Set(value.values?.[key]||[]);
      form.querySelectorAll(`[name="observed_${key}"]`).forEach(el=>{
        const gis=ids.has(el.value),label=el.closest('label');
        el.indeterminate=gis&&!el.checked;
        el.dataset.gisSelected=String(gis);
        label?.classList.toggle('gis-selected',gis);
        if(gis)label.title=el.checked?'Campo y GIS. Pulsa para quitar del borrador.':'Recuperado de GIS. Pulsa para quitar del borrador.';
        else label?.removeAttribute('title');
      });
    }
    const panel=form.querySelector('.observation-evidence-panel');
    if(panel&&!panel.querySelector('[data-gis-selection-legend]')) {
      const legend=node('p','Azul: evidencia de campo. Verde con GIS: datos cartográficos aceptados. Puedes pulsar un valor GIS para quitarlo del borrador.');
      legend.dataset.gisSelectionLegend='';legend.className='gis-selection-legend';
      panel.querySelector('h3')?.after(legend);
    }
    // Keep the status outside the non-wrapping action row.
    const status=form.querySelector('[data-observation-gis-status]'),footer=form.querySelector('.observation-form-footer');
    if(status&&footer&&status.parentElement!==footer)footer.append(status);
  }
  const refresh=()=>document.querySelectorAll('form:has([name=gis_recovery_json])').forEach(sync);
  function coordinatesChanged(form) {
    if(!form?.querySelector('[name=gis_recovery_json]'))return;
    const value=saved(form);
    if(!value.location)return;
    const same=['lat','lon'].every(key=>{
      const raw=input(form,'location_'+key)?.value?.trim();
      return raw!=='' && raw!=null && Number.isFinite(Number(raw)) &&
        Number(raw).toFixed(7)===Number(value.location[key]).toFixed(7);
    });
    if(same)return;
    input(form,'gis_recovery_json').value='{}';sync(form);
    if(active?.form===form)dialog.close();
    form.querySelector('[data-observation-gis-status]').textContent='La ubicación ha cambiado. Los datos GIS aceptados correspondían al punto anterior: recupera GIS / DEM para la nueva ubicación antes de guardar.';
  }
  let dialog, active;
  function modal() {
    if(dialog)return dialog;
    dialog=node('dialog');dialog.className='observation-gis-dialog';
    dialog.setAttribute('aria-labelledby','observation-gis-title');
    const header=node('header'),title=node('h2','Recuperar GIS / DEM'),close=node('button','Cerrar');
    title.id='observation-gis-title';close.type='button';close.onclick=()=>dialog.close();header.append(title,close);
    dialog.append(header,node('p','Revisa los datos GIS antes de aplicarlos a la ficha. Se conservan separados de la evidencia de campo. El suelo es una tendencia cartográfica, no una medida de pH.'));
    const status=node('p');status.dataset.gisDialogStatus='';status.setAttribute('role','status');
    const currentBox=node('div');currentBox.dataset.observationGisCurrent='';
    const reviewBox=node('div');reviewBox.dataset.observationGisReview='';
    dialog.append(status,currentBox,reviewBox);document.body.append(dialog);
    dialog.addEventListener('close',()=>{if(!dialog.open){active?.controller.abort();active=null;}});
    return dialog;
  }
  function current(form) {
    const box=modal().querySelector('[data-observation-gis-current]');
    box.replaceChildren(); const value=saved(form);
    Object.entries(value.values||{}).forEach(([key,ids])=>box.append(node('p',`${fields[key]} · GIS: ${labels(form,key,ids)} · ${(value.sources?.[key]||[]).join(', ')}`)));
  }
  function review(form, report, query) {
    const box=modal().querySelector('[data-observation-gis-review]');box.replaceChildren();box.hidden=false;
    const stored=saved(form), old=JSON.stringify(stored.location)===JSON.stringify(report.location)?stored:{}, decisions={};
    const table=node('table');table.className='gis-review-table';
    const head=node('tr');['Campo','Actual (campo + GIS)','Recuperado','Decisión'].forEach(t=>head.append(node('th',t)));table.append(head);
    for(const [key,title] of Object.entries({...fields,altitude_m:'Altitud'})) {
      const scalar=key==='altitude_m', proposed=scalar?report.altitude_m:report.values[key];
      if(proposed==null || Array.isArray(proposed)&&!proposed.length)continue;
      const existing=scalar?input(form,'altitude_m').value:[...new Set([...manual(form,key),...(old.values?.[key]||[])])];
      const tr=node('tr');tr.append(node('th',title));
      tr.append(node('td',scalar?existing:labels(form,key,existing)));
      const proposal=node('td',scalar?`${proposed} m`:labels(form,key,proposed));
      proposal.append(node('small',scalar?report.altitude_source:(report.sources[key]||[]).join(', ')));tr.append(proposal);
      const td=node('td'),select=node('select');select.setAttribute('aria-label',title);
      for(const [mode,label] of [['keep','Mantener'],...(!scalar?[['merge','Fusionar']]:[]),['replace','Reemplazar']]) {
        const option=node('option',label);option.value=mode;select.append(option);
      }
      const proposedIds=scalar?null:new Set(proposed);
      const equal=scalar?existing.trim()!==''&&Number(existing)===Number(proposed):existing.length===proposedIds.size&&existing.every(id=>proposedIds.has(id));
      select.value=equal?'keep':'replace';td.append(select);tr.append(td);table.append(tr);decisions[key]=select;
    }
    const scroll=node('div');scroll.className='gis-review-scroll';scroll.append(table);
    const forestStatus={available:'Árboles registrados en el polígono consultado',no_trees_recorded:'Sin árboles registrados en este polígono MFE25; no confirma ausencia de árboles',not_covered:'Punto fuera de la cobertura MFE25',unavailable:'MFE25 no disponible',not_connected:'MFE25 no configurado',ambiguous:'Punto en un límite o solapamiento cartográfico',resource_limit:'Consulta MFE25 fuera del límite de recursos',busy:'MFE25 ocupado; vuelve a intentarlo'};
    box.append(scroll,node('p',`MFE25: ${forestStatus[report.forest.status]||'Sin resultado disponible'}. Capas pendientes: ${(report.gaps||[]).join(', ')||'ninguna'}.`));
    box.append(node('p','Fusionar conserva los datos actuales y añade GIS. Reemplazar sustituye los valores del campo seleccionado. No se guarda hasta pulsar Guardar.'));
    const apply=node('button','Aplicar al borrador');apply.type='button';apply.className='primary';apply.autofocus=true;
    apply.onclick=()=>{
      if(query!==coordinateQuery(form).toString()) {
        modal().querySelector('[data-gis-dialog-status]').textContent='Las coordenadas han cambiado. Recupera GIS / DEM de nuevo.';return;
      }
      const next=structuredClone(old);let changed=false;
      next.values=next.values||{};next.sources=next.sources||{};
      for(const [key,select] of Object.entries(decisions)) {
        const mode=select.value;if(mode==='keep')continue;
        if(key==='altitude_m') {input(form,key).value=Math.round(report.altitude_m);input(form,'altitude_source').value='dem';continue;}
        changed=true;
        next.values[key]=mode==='merge'?[...new Set([...(next.values[key]||[]),...report.values[key]])]:report.values[key];
        next.sources[key]=mode==='merge'?[...new Set([...(next.sources[key]||[]),...report.sources[key]])]:report.sources[key];
        if(mode==='replace')form.querySelectorAll(`[name="observed_${key}"]`).forEach(el=>{el.checked=false;});
      }
      if(changed) {
        Object.assign(next,{version:1,location:report.location,recovered_at:report.recovered_at});
        next.forest=report.forest;
        input(form,'gis_recovery_json').value=JSON.stringify(next);
      }
      sync(form);
      dialog.close();
      form.querySelector('[data-observation-gis-status]').textContent='Datos aplicados al borrador. Revisa la ficha y pulsa Guardar para conservarlos.';
      form.dispatchEvent(new Event('change',{bubbles:true}));
    };
    const cancel=node('button','Cancelar recuperación');cancel.type='button';cancel.onclick=()=>dialog.close();
    const actions=node('div');actions.className='gis-review-actions';actions.append(apply,cancel);box.append(actions);
    apply.focus({preventScroll:true});
  }
  function coordinateQuery(form) {
    return new URLSearchParams(['location_lat','location_lon','location_input'].map(key=>[key,input(form,key)?.value||'']));
  }
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-observation-gis-recover]');if(!button)return;
    const form=button.closest('form'),view=modal(),status=view.querySelector('[data-gis-dialog-status]');
    active?.controller.abort();
    const request={form,controller:new AbortController()};active=request;
    view.querySelector('[data-observation-gis-review]').replaceChildren();
    view.querySelector('[data-observation-gis-review]').hidden=true;current(form);
    const query=coordinateQuery(form).toString();button.disabled=true;status.textContent='Consultando GIS / DEM…';
    if(!view.open)view.showModal();
    try {
      const url=new URL(location.href);url.pathname=url.pathname.replace(/\/mushrooms\/.*$/,'/api/mushrooms/observation-gis-preview');url.search=query;url.hash='';
      const response=await fetch(url,{credentials:'same-origin',cache:'no-store',signal:request.controller.signal}),data=await response.json();
      if(active!==request||!view.open)return;
      if(!response.ok||!data.ok)throw new Error(data.error||'No se han podido recuperar los datos.');
      review(form,data.report,query);status.textContent='Recuperación lista para revisar.';
    } catch(error) {if(active===request&&error.name!=='AbortError')status.textContent=error.message;} finally {button.disabled=false;}
  });
  document.addEventListener('input',event=>{
    if(!['location_lat','location_lon','location_input'].includes(event.target.name))return;
    const form=event.target.closest('form');if(!form?.querySelector('[name=gis_recovery_json]'))return;
    input(form,'gis_recovery_json').value='{}';sync(form);if(active?.form===form)dialog.close();
    form.querySelector('[data-observation-gis-status]').textContent='Coordenadas modificadas: recupera GIS / DEM para la nueva ubicación.';
  });
  document.addEventListener('change',event=>{
    const el=event.target,form=el.closest('form');
    if(!form?.querySelector('[name=gis_recovery_json]'))return;
    const key=el.name?.replace(/^observed_/,'');
    if(key in fields&&el.dataset.gisSelected==='true') {
      const value=saved(form);
      value.values[key]=(value.values[key]||[]).filter(id=>id!==el.value);
      if(!value.values[key].length){delete value.values[key];delete value.sources[key];}
      input(form,'gis_recovery_json').value=JSON.stringify(value);
      el.checked=false;
    }
    sync(form);
  });
  window.addEventListener('hashchange',()=>{refresh();if(active&&location.hash!=='#'+active.form.closest('.modal-layer')?.id)dialog.close();});
  window.rainmapperObservationGIS={refresh,coordinatesChanged};refresh();
})();
