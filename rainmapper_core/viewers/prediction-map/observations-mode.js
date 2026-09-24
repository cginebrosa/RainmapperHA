/* Independent read-only overlay; historical reference dates never enter requests. */
export function createObservationsMode(bridge) {
  const {map, text} = bridge;
  const button = document.createElement('button');
  button.id='observations-mode-toggle'; button.type='button'; button.className='map-control-button';
  button.setAttribute('aria-pressed','false');
  button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="6" cy="12" rx="5" ry="7"/><ellipse cx="18" cy="12" rx="5" ry="7"/><circle cx="7" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>';
  bridge.after().after(button);
  const panel=document.createElement('section'); panel.id='observations-mode-panel'; panel.className='om-panel';panel.hidden=true;
  const heading=document.createElement('label'), select=document.createElement('select'), status=document.createElement('p');
  select.id='observations-species';heading.htmlFor=select.id; status.className='om-status';status.setAttribute('role','status');
  panel.append(heading,select,status);
  const layer=document.createElement('div');layer.className='om-overlay';
  const legs=document.createElementNS('http://www.w3.org/2000/svg','svg');legs.classList.add('om-legs');legs.setAttribute('aria-hidden','true');
  const markers=document.createElement('div');markers.className='om-markers';layer.append(legs,markers);
  map.getContainer().append(layer,panel);
  // Controls and observation icons consume their own gestures, never prediction clicks.
  for(const type of ['click','dblclick','pointerdown','mousedown','touchstart','wheel']) panel.addEventListener(type,e=>e.stopPropagation());
  let enabled=false, destroyed=false, serial=0, controller=null, popup=null, points=[], species=[], revision='', expanded=null, page=0;
  let detailController=null, currentDetail=null;
  const date=value=>/^\d{4}-\d{2}-\d{2}/.test(value) ? value.slice(0,10).split('-').reverse().join('/') : value;
  const mushroom='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 13C3 1 21 1 21 13Z" fill="#e85d41"/><path d="M9 13h6l2 8H7Z" fill="#fff2d1"/><path d="M3 13C3 1 21 1 21 13ZM9 13l-2 8h10l-2-8" fill="none" stroke="#533321" stroke-width="1.5"/><circle cx="8" cy="9" r="1.5" fill="white"/><circle cx="15" cy="7" r="1.5" fill="white"/></svg>';
  function closeDetail() {detailController?.abort();detailController=null;popup?.remove();popup=null;currentDetail=null;}
  function clear() {markers.replaceChildren();legs.replaceChildren();}
  function deactivate() {
    enabled=false;serial++;controller?.abort();closeDetail();points=[];species=[];revision='';expanded=null;
    button.setAttribute('aria-pressed','false');panel.hidden=true;clear();select.replaceChildren();
  }
  async function get(action, params, signal) {
    const response=await bridge.fetch(`${bridge.config.apiBase}/observations/${action}?${new URLSearchParams(params)}`,{cache:'no-store',signal});
    if(response.status===403 || response.status===401) {deactivate();throw new Error('forbidden');}
    if(!response.ok)throw new Error(response.status===409?'observations_changed':'observations_unavailable');
    return response.json();
  }
  function showError(error) {
    if(error.name==='AbortError' || !enabled)return;
    status.textContent=text(error.message==='observations_changed'?'obs_changed':'obs_error');
  }
  function options() {
    const previous=select.value;select.replaceChildren();
    const empty=document.createElement('option');empty.value='';empty.textContent=text('obs_choose');select.append(empty);
    for(const row of species) {const option=document.createElement('option');option.value=row.id;option.textContent=`${row.name} (${row.count})`;select.append(option);}
    select.value=previous;
  }
  async function activate() {
    enabled=true;button.setAttribute('aria-pressed','true');panel.hidden=false;status.textContent=text('obs_loading');
    const own=++serial;controller?.abort();controller=new AbortController();select.disabled=true;
    try {
      const data=await get('species',{},controller.signal);
      if(own!==serial || !enabled)return;
      species=data.species;revision=data.revision;options();status.textContent=species.length?text('obs_all_dates'):text('obs_empty');
    } catch(error) {showError(error);}
    finally {if(own===serial)select.disabled=false;}
  }
  async function choose() {
    const sid=select.value,own=++serial;controller?.abort();controller=new AbortController();closeDetail();points=[];expanded=null;clear();
    if(!sid){status.textContent=text('obs_all_dates');return;}
    status.textContent=text('obs_loading');
    try {
      let offset=0;const loaded=[];
      do {
        const data=await get('points',{species_id:sid,offset:String(offset),revision},controller.signal);
        if(own!==serial || !enabled)return;
        if(data.revision!==revision || !Array.isArray(data.points) || loaded.length+data.points.length>10000)throw Error('observations_changed');
        loaded.push(...data.points);offset=data.next_offset;
      } while(offset!==null);
      points=loaded;render();summary();
    } catch(error) {showError(error);}
  }
  function summary() {
    if(select.value) {
      const row=species.find(r=>r.id===select.value);
      status.textContent=`${points.length} / ${row?.count||points.length} · ${text('obs_all_dates')}`;
    }
  }
  function marker(x,y,items,spider=false) {
    const node=document.createElement('button');node.type='button';node.className=`om-marker${spider?' om-spider':''}`;
    node.style.left=`${x}px`;node.style.top=`${y}px`;
    if(items.length===1) {
      node.innerHTML=mushroom;
      node.setAttribute('aria-label',`${text('obs_observation')} · ${date(items[0][3])} · ${items[0][0]}`);
      node.title=node.getAttribute('aria-label');node.dataset.observationId=items[0][0];
      if(spider){const caption=document.createElement('span');caption.className='om-date';caption.textContent=date(items[0][3]);node.append(caption);}
    } else {node.textContent=String(items.length);node.classList.add('om-cluster');node.setAttribute('aria-label',`${items.length} ${text('obs_expand')}`);}
    for(const type of ['dblclick','pointerdown','mousedown','touchstart'])node.addEventListener(type,e=>e.stopPropagation());
    node.addEventListener('click',event=>{
      event.stopPropagation();
      if(items.length===1){
        if(popup && currentDetail?.[0]===items[0][0])closeDetail();
        else detail(items[0]);
      }
      else {
        const openIds=new Set((expanded||[]).map(row=>row[0]));
        const sameGroup=openIds.size===items.length && items.every(row=>openIds.has(row[0]));
        closeDetail();
        expanded=sameGroup?null:items.slice().sort((a,b)=>a[3].localeCompare(b[3])||a[0].localeCompare(b[0]));
        page=0;render();
      }
    });
    markers.append(node);return node;
  }
  function line(from,to) {
    const node=document.createElementNS(legs.namespaceURI,'line');
    for(const [key,value] of Object.entries({x1:from.x,y1:from.y,x2:to.x,y2:to.y}))node.setAttribute(key,String(value));
    legs.append(node);
  }
  function render() {
    clear();if(!enabled || destroyed)return;
    const canvas=map.getCanvas(),w=canvas.clientWidth,h=canvas.clientHeight;
    // Pixel grouping combines exact coincidences and overlapping icons at this zoom.
    const groups=new Map();
    for(const row of points){const p=map.project([row[1],row[2]]);if(p.x<-24||p.y<-24||p.x>w+24||p.y>h+24)continue;
      const key=`${Math.floor(p.x/44)}:${Math.floor(p.y/44)}`;
      if(!groups.has(key))groups.set(key,{x:p.x,y:p.y,items:[]});groups.get(key).items.push(row);
    }
    for(const g of groups.values())marker(g.x,g.y,g.items);
    if(!expanded)return;
    const original=map.project([expanded[0][1],expanded[0][2]]);
    const radius=expanded.length<=3?85:125;
    const center={x:Math.max(radius+45,Math.min(w-radius-45,original.x)),y:Math.max(radius+40,Math.min(h-radius-55,original.y))};
    // At most eight dated icons at once; large groups remain fully navigable.
    const batch=expanded.slice(page*8,page*8+8);
    batch.forEach((row,index)=>{
      const angle=-Math.PI/2+2*Math.PI*index/batch.length;
      const p={x:center.x+Math.cos(angle)*radius,y:center.y+Math.sin(angle)*radius};
      line(map.project([row[1],row[2]]),p);marker(p.x,p.y,[row],true);
    });
    if(expanded.length>8){
      const nav=document.createElement('div');nav.className='om-pages';nav.style.left=`${center.x}px`;nav.style.top=`${center.y}px`;
      for(const step of [-1,1]){const b=document.createElement('button');b.type='button';b.textContent=step<0?'‹':'›';b.ariaLabel=text(step<0?'obs_previous':'obs_next');b.disabled=page+step<0||(page+step)*8>=expanded.length;b.onclick=e=>{e.stopPropagation();page+=step;render();};nav.append(b);}
      const count=document.createElement('span');count.textContent=`${page*8+1}–${page*8+batch.length} / ${expanded.length}`;nav.append(count);markers.append(nav);
    }
  }
  function moonBadge(moon) {
    if(!moon || !['waxing','waning','full','new'].includes(moon.category) || !Number.isFinite(moon.illuminated_fraction))return null;
    const badge=document.createElement('figure');badge.className='om-moon';
    const caption=document.createElement('figcaption');caption.textContent=text(`obs_moon_${moon.category}`);
    badge.setAttribute('aria-label',`${text('obs_moon')} · ${caption.textContent}`);
    // Northern-hemisphere illustration: waxing lights the right side. The
    // terminator follows the computed fraction, not a fixed half-moon icon.
    const fraction=Math.max(0,Math.min(1,moon.illuminated_fraction)),curve=2*fraction-1;
    const prefix=`om-moon-${serial}`,terminator=Math.abs(26*curve);
    const path=`M32 6 A26 26 0 0 1 32 58 ${terminator<0.001?'L32 6':`A${terminator} 26 0 0 ${curve>=0?1:0} 32 6`} Z`;
    const craters='<g fill="#7f8c9c" opacity=".3"><ellipse cx="23" cy="22" rx="7" ry="8"/><ellipse cx="39" cy="19" rx="5" ry="6"/><ellipse cx="42" cy="35" rx="8" ry="10"/><circle cx="25" cy="42" r="5"/><circle cx="35" cy="49" r="3"/></g><g fill="none" stroke="#f4f6f7" stroke-opacity=".32"><circle cx="21" cy="34" r="4"/><circle cx="35" cy="26" r="3"/><circle cx="31" cy="50" r="2"/></g>';
    badge.innerHTML=`<svg viewBox="0 0 64 64" aria-hidden="true"><defs>
      <radialGradient id="${prefix}-light" cx="35%" cy="28%" r="75%"><stop stop-color="#fff9e8"/><stop offset=".55" stop-color="#dce3e9"/><stop offset="1" stop-color="#8795a7"/></radialGradient>
      <radialGradient id="${prefix}-dark" cx="35%" cy="28%" r="75%"><stop stop-color="#34455d"/><stop offset="1" stop-color="#101e32"/></radialGradient>
      <clipPath id="${prefix}-lit"><path d="${path}" transform="${moon.waxing?'':'translate(64 0) scale(-1 1)'}"/></clipPath>
      </defs><circle cx="32" cy="32" r="29" fill="#e8eef5"/><circle cx="32" cy="32" r="26" fill="url(#${prefix}-dark)"/>
      <g opacity=".14">${craters}</g><g clip-path="url(#${prefix}-lit)"><circle cx="32" cy="32" r="26" fill="url(#${prefix}-light)"/>${craters}</g>
      <circle cx="32" cy="32" r="26" fill="none" stroke="#8293a7" stroke-opacity=".3"/></svg>`;
    badge.append(caption);return badge;
  }
  async function detail(row) {
    closeDetail();bridge.closePopups();const own=++serial;
    detailController=new AbortController();const body=document.createElement('section');body.className='om-detail';body.textContent=text('obs_loading');
    popup=new maplibregl.Popup({maxWidth:'330px',closeOnClick:false,focusAfterOpen:false,className:'om-popup'}).setLngLat([row[1],row[2]]).setDOMContent(body).addTo(map);
    currentDetail=row; // Also allow toggling closed while the request is pending.
    const current=popup;current.on('close',()=>{if(popup===current){detailController?.abort();popup=null;currentDetail=null;}});
    try {
      const data=await get('detail',{id:row[0],revision,lang:bridge.language()},detailController.signal);
      if(!enabled||own!==serial||popup!==current)return;
      body.replaceChildren();
      const title=document.createElement('h3');title.textContent=data.observation.species;body.append(title);
      const fields=document.createElement('dl'),moon=moonBadge(data.observation.moon);
      if(moon)fields.classList.add('om-fields-with-moon');
      const contextValues=key=>data.observation[key].map((value,index)=>
        data.observation.gis?.[key]?.includes(index)?`${value} (${text('obs_gis_accepted')})`:value).join(', ');
      for(const [key,value] of Object.entries({date:date(data.observation.date),area:data.observation.area,microarea:data.observation.microarea,abundance:data.observation.abundance,hosts:contextValues('hosts'),forest:contextValues('forest'),observer:data.observation.observer,id:data.observation.id})){
        const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=text(`obs_${key}`);dd.textContent=value||text('obs_unknown');
        const group=document.createElement('div');group.className=`om-field om-field-${key}`;group.append(dt,dd);fields.append(group);
      }
      if(moon){const cell=document.createElement('div');cell.className='om-moon-cell';const dt=document.createElement('dt');dt.className='om-visually-hidden';dt.textContent=text('obs_moon');const dd=document.createElement('dd');dd.append(moon);cell.append(dt,dd);fields.append(cell);}
      body.append(fields);
    }catch(error){if(error.name!=='AbortError'&&popup===current)body.textContent=text(error.message==='observations_changed'?'obs_changed':'obs_error');}
  }
  function collapse(){if(expanded){expanded=null;render();}}
  function moving(){expanded=null;clear();}
  function refreshLanguage(){button.title=button.ariaLabel=text('obs_show');heading.textContent=text('obs_species');select.ariaLabel=text('obs_species');options();if(enabled){summary();render();if(currentDetail)detail(currentDetail);}}
  button.onclick=()=>enabled?deactivate():activate();select.onchange=choose;
  map.on('click',collapse);map.on('movestart',moving);map.on('moveend',render);map.on('resize',render);
  const escape=e=>{if(e.key==='Escape'){closeDetail();collapse();}};document.addEventListener('keydown',escape);
  refreshLanguage();
  return {refreshLanguage,destroy(){destroyed=true;deactivate();map.off('click',collapse);map.off('movestart',moving);map.off('moveend',render);map.off('resize',render);document.removeEventListener('keydown',escape);button.remove();panel.remove();layer.remove();}};
}
