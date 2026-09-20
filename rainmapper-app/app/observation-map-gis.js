/* Read-only point inspection; never changes observation coordinates or fields. */
(() => {
  if (window.rainmapperObservationMapGIS) return;
  const fields={host_ids:'Hosts',forest_type_ids:'Bosque',soil_tendency_ids:'Suelo',habitat_feature_ids:'Hábitat'};
  const sources={mfe25:'MFE25',mvc50:'MVC50',geology_50000:'Geología 1:50.000',dem_5m:'DEM 5 m'};
  const forestStates={available:'Árboles registrados en el polígono MFE25.',no_trees_recorded:'Sin árboles registrados en este polígono MFE25; no demuestra ausencia de árboles.',not_covered:'Punto fuera de la cobertura MFE25.',unavailable:'MFE25 no disponible.',not_connected:'MFE25 no configurado.',ambiguous:'Punto en un límite o solapamiento cartográfico.',resource_limit:'Consulta fuera del límite de recursos MFE25.',busy:'MFE25 ocupado. Vuelve a consultar el punto.'};
  const element=(tag,text)=>{const el=document.createElement(tag);if(text!=null)el.textContent=text;return el;};
  window.rainmapperObservationMapGIS={attach(map,node,first,canActivate) {
    const card=node.closest('.evidence-map-modal'),modal=node.closest('.modal-layer');
    const button=card?.querySelector('.observation-gis-toggle'),panel=card?.querySelector('.observation-map-gis-panel');
    if(!button||!panel)return null;
    let enabled=false,marker=null,pending=null,busy=false,revision=0,disposed=false;
    const disabled=new Map();
    function heading(point,message) {
      panel.replaceChildren(element('h3','GIS / DEM del punto'));
      if(point)panel.append(element('p',`${point.lat.toFixed(7)}, ${point.lng.toFixed(7)}`));
      panel.append(element('p',message));
    }
    function show(data,point) {
      const r=data.report;heading(point,'Pulsa otro punto del mapa para consultar.');
      const list=element('dl');
      for(const [key,label] of Object.entries(fields)) {
        const ids=r.values?.[key]||[],value=element('dd',ids.length?ids.map(id=>data.labels?.[key]?.[id]||id).join(', '):'Sin datos recuperados');
        if(ids.length)value.append(element('small',(r.sources?.[key]||[]).map(id=>sources[id]||id).join(', ')));
        list.append(element('dt',label),value);
      }
      const altitude=element('dd',r.altitude_m==null?'No disponible':`${r.altitude_m} m`);
      if(r.altitude_source)altitude.append(element('small',sources[r.altitude_source]||r.altitude_source));
      list.append(element('dt','Altitud'),altitude);panel.append(list);
      panel.append(element('small',forestStates[r.forest?.status]||'Sin resultado MFE25 disponible.'));
      if(r.gaps?.length)panel.append(element('small','Capas pendientes: '+r.gaps.join(', ')));
      panel.append(element('small','Suelo: tendencia cartográfica, no medida de pH. Esta consulta no modifica la observación.'));
    }
    async function drain() {
      if(busy||!pending||!enabled||disposed)return;
      const request=pending;pending=null;busy=true;
      // One request at a time. Intermediate clicks are replaced by the latest.
      const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
      try {
        const url=new URL(location.href);url.pathname=url.pathname.replace(/\/mushrooms\/.*$/,'/api/mushrooms/observation-gis-preview');
        url.hash='';url.search=new URLSearchParams({location_lat:request.point.lat,location_lon:request.point.lng});
        const response=await fetch(url,{credentials:'same-origin',cache:'no-store',signal:controller.signal}),data=await response.json();
        if(!enabled||disposed||request.revision!==revision)return;
        if(!response.ok||!data.ok)throw Error(data.error||'No se pudo consultar GIS / DEM.');
        show(data,request.point);
      } catch(error) {
        if(enabled&&!disposed&&request.revision===revision)heading(request.point,error.name==='AbortError'?'La consulta ha tardado demasiado. Pulsa el punto para reintentar.':error.message);
      } finally {clearTimeout(timeout);busy=false;drain();}
    }
    function select(point) {
      if(!enabled||disposed)return;
      point={lat:Number(point.lat),lng:Number(point.lng)};
      if(!Number.isFinite(point.lat)||!Number.isFinite(point.lng))return;
      pending={point,revision:++revision};heading(point,'Consultando GIS / DEM…');
      if(!marker)marker=new maplibregl.Marker({color:'#03a9f4'}).setLngLat(point).addTo(map);
      else marker.setLngLat(point);
      marker.getElement().style.pointerEvents='none';
      marker.getElement().title='Punto de consulta GIS / DEM';drain();
    }
    function close() {
      enabled=false;revision++;pending=null;panel.hidden=true;button.setAttribute('aria-pressed','false');
      card.classList.remove('gis-inspecting');marker?.remove();marker=null;
      disabled.forEach((value,control)=>{control.disabled=value;});disabled.clear();
      if(!disposed)map.resize();
    }
    function toggle() {
      if(enabled){close();return;}
      panel.hidden=false;
      if(!canActivate()) {heading(null,'Termina o cancela la edición de coordenadas o geometría antes de consultar GIS / DEM.');card.classList.add('gis-inspecting');map.resize();return;}
      enabled=true;button.setAttribute('aria-pressed','true');card.classList.add('gis-inspecting');
      card.querySelectorAll('[data-coordinate-toolbar] button,.observation-site-assignment button,.observation-site-assignment input').forEach(control=>{disabled.set(control,control.disabled);control.disabled=true;});
      select({lat:first.lat,lng:first.lon});map.resize();
    }
    const changed=()=>{if(location.hash!=='#'+modal.id)close();};
    button.addEventListener('click',toggle);window.addEventListener('hashchange',changed);
    map.on('remove',()=>{disposed=true;close();button.removeEventListener('click',toggle);window.removeEventListener('hashchange',changed);});
    return {get enabled(){return enabled;},select,close};
  }};
})();
