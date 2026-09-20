/* Local observations and media; only the four prediction-viewer basemaps use the network. */
"use strict";
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? "No informado").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const records = GBIF_DATA.records;
const byId = new Map(records.map(r => [String(r.key), r]));
// Review metadata is separate from immutable GBIF occurrences; absent entries are pending.
const reviewLabels={pending:"Pendiente",doubtful:"Dudosa",approved:"Aceptada",rejected:"Rechazada"};
const reviewStorageKey="rainmapper-gbif-review-v1:"+GBIF_DATA.snapshot_sha256;
let reviewEntries={}, reviewWritable=true;
function reviewStatus(id){return reviewEntries[String(id)]?.status||"pending";}
function reviewMessage(text,error=false){$("review-message").textContent=text;$("review-message").classList.toggle("review-error",error);}
function reviewDocument(entries=reviewEntries){return {schema:"rainmapper-gbif-review",version:1,source:"GBIF",snapshot_sha256:GBIF_DATA.snapshot_sha256,exported_at:new Date().toISOString(),records:records.map(r=>({gbif_id:String(r.key),status:entries[String(r.key)]?.status||"pending",reviewed_at:entries[String(r.key)]?.reviewed_at||null}))};}
function parseReview(doc){
  if(doc?.schema!=="rainmapper-gbif-review"||doc.version!==1||doc.source!=="GBIF"||doc.snapshot_sha256!==GBIF_DATA.snapshot_sha256||!Array.isArray(doc.records)||doc.records.length!==records.length)throw Error("El archivo no corresponde a esta copia de GBIF.");
  const seen=new Set(), entries={};
  for(const r of doc.records){
    const id=r?.gbif_id;
    if(typeof id!=="string"||!byId.has(id)||seen.has(id)||!Object.hasOwn(reviewLabels,r.status)||!(r.reviewed_at===null||typeof r.reviewed_at==="string"&&Number.isFinite(Date.parse(r.reviewed_at)))||r.status!=="pending"&&r.reviewed_at===null)throw Error("El archivo contiene estados, fechas o identificadores inválidos.");
    seen.add(id);if(r.reviewed_at!==null)entries[id]={status:r.status,reviewed_at:new Date(r.reviewed_at).toISOString()};
  }
  return entries;
}
function readReview(){const raw=localStorage.getItem(reviewStorageKey);return raw?parseReview(JSON.parse(raw)):{};}
try{reviewEntries=readReview();}catch(error){reviewWritable=false;reviewMessage("No se pudo leer la revisión guardada. No se sobrescribirá. "+error.message,true);}
function persistReview(entries){
  if(!reviewWritable)throw Error("El guardado está bloqueado para proteger la revisión existente.");
  localStorage.setItem(reviewStorageKey,JSON.stringify(reviewDocument(entries)));
  reviewEntries=entries;
  window.gbifReviewFile?.schedule();
}
function changeReview(id,status){
  if(!byId.has(String(id))||!Object.hasOwn(reviewLabels,status))return;
  try{
    // Re-read before writing so another tab's decisions are preserved.
    const entries=readReview();entries[String(id)]={status,reviewed_at:new Date().toISOString()};persistReview(entries);
    applyFilters();if(selected===String(id))selectObservation(id,false,currentOverlaps);
    reviewMessage("Cambio guardado en el navegador. El estado del archivo se muestra al lado.");
  }catch(error){reviewMessage("No se ha guardado el cambio: "+error.message,true);if(selected)selectObservation(selected,false,currentOverlaps);}
}
function importReview(doc){
  const incoming=parseReview(doc), entries=readReview();
  for(const [id,value] of Object.entries(incoming)){
    const old=entries[id];
    if(old&&old.reviewed_at===value.reviewed_at&&old.status!==value.status)throw Error("Hay decisiones contradictorias con la misma fecha. Se conserva la revisión actual.");
    if(!old||value.reviewed_at>old.reviewed_at)entries[id]=value;
  }
  persistReview(entries);applyFilters();if(selected)selectObservation(selected,false,currentOverlaps);
  reviewMessage("Revisión importada. Se ha conservado la decisión más reciente de cada observación.");
}
$("export-review").addEventListener("click",()=>{
  try{
    if(reviewWritable)reviewEntries=readReview();
    else throw Error("No se puede exportar hasta recuperar la revisión guardada.");
    const url=URL.createObjectURL(new Blob([JSON.stringify(reviewDocument(),null,2)+"\n"],{type:"application/json"}));
    const link=document.createElement("a");link.href=url;link.download="gbif-revision-"+new Date().toISOString().replace(/[:.]/g,"-")+".json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    reviewMessage("Exportación solicitada. Conserva el JSON descargado para la futura incorporación de las aceptadas.");
  }catch(error){reviewMessage(error.message,true);}
});
$("import-review").addEventListener("click",()=>$("review-file").click());
$("review-file").addEventListener("change",async event=>{
  const file=event.target.files[0];if(!file)return;
  try{if(file.size>5*1024*1024)throw Error("El archivo de revisión es demasiado grande.");importReview(JSON.parse(await file.text()));}
  catch(error){reviewMessage("No se ha importado: "+error.message,true);}finally{event.target.value="";}
});
window.addEventListener("storage",event=>{if(event.key!==reviewStorageKey)return;try{reviewEntries=readReview();applyFilters();if(selected)selectObservation(selected,false,currentOverlaps);}catch(error){reviewWritable=false;reviewMessage("No se pudo leer el cambio de otra ventana: "+error.message,true);}});
if(reviewWritable)reviewMessage("Revisión guardada automáticamente en este navegador.");
const profileById = new Map(GBIF_DATA.profiles.map(p => [p.species_id, p]));
const es = new Intl.NumberFormat("es-ES");
const dateLabel = value => {
  const text=String(value || "Fecha desconocida");
  return text.replace(/^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/, "$3/$2/$1");
};
const precisionGroup = r => r.coordinateUncertaintyInMeters == null ? "unknown" : r.coordinateUncertaintyInMeters <= 1000 ? "precise" : "wide";
const precisionLabel = r => r.coordinateUncertaintyInMeters == null ? "Desconocida" : `${es.format(r.coordinateUncertaintyInMeters)} m`;
const normalize = value => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const searchText = new Map(records.map(r => [r.key, normalize([r.key,r.species,r.scientificName,r.eventDate,r.recordedBy,r.locality,r.geography?.municipality?.name,r.dataset].join(" "))]));
let currentOverlaps=[];
let filtered = records.slice(), selected = null, mapReady = false;
let activeStyleId = GBIF_BASE_STYLES[0].id;
let clusterMarkers = [], clusterRefresh = 0;
const circleCache = new Map();
for (const profile of GBIF_DATA.profiles) {
  const count = records.filter(r => r.profile_ids.includes(profile.species_id)).length;
  const option = new Option(`${profile.scientific_name} · ${count}`, profile.species_id);
  option.title = (profile.common_names || []).join(" · ");
  $("species").append(option);
}
const labels = {"esri-satellite-vector":"Satélite+", "esri-hybrid":"Híbrido", "opentopomap":"Topográfico", "openfreemap-liberty":"Liberty"};
for (const style of GBIF_BASE_STYLES) $("basemap").append(new Option(labels[style.id] || style.label, style.id));
const styleValue = style => style.url || structuredClone(style.style);
const map = new maplibregl.Map({container:"map", style:styleValue(GBIF_BASE_STYLES[0]),
  center:[1.65,41.85], zoom:7, minZoom:5, maxZoom:18, attributionControl:true});
map.addControl(new maplibregl.NavigationControl({showCompass:false}), "top-left");
let terrainEnabled=false;
const terrainControl={onAdd(){
  this.container=document.createElement("div");this.container.className="maplibregl-ctrl maplibregl-ctrl-group gbif-view-controls";
  this.container.innerHTML='<button id="terrain-toggle" type="button" disabled title="Activar relieve 3D" aria-label="Activar relieve 3D" aria-pressed="false">2D</button><button id="north-toggle" type="button" title="Orientar al norte" aria-label="Orientar al norte"><span aria-hidden="true">↑N</span></button>';
  this.container.querySelector("#terrain-toggle").addEventListener("click",()=>{
    terrainEnabled=!terrainEnabled;applyTerrain();map.easeTo({pitch:terrainEnabled?55:0,duration:350});
  });
  this.container.querySelector("#north-toggle").addEventListener("click",()=>map.easeTo({bearing:0,duration:350}));
  return this.container;
},onRemove(){this.container.remove();}};
map.addControl(terrainControl,"top-left");
function applyTerrain(){
  const button=$("terrain-toggle");button.textContent=terrainEnabled?"3D":"2D";button.setAttribute("aria-pressed",String(terrainEnabled));
  button.title=terrainEnabled?"Volver a 2D":"Activar relieve 3D";button.setAttribute("aria-label",button.title);
  if(!mapReady)return;
  if(!terrainEnabled){map.setTerrain(null);return;}
  if(!map.getSource("gbif-terrain-dem"))map.addSource("gbif-terrain-dem",{type:"raster-dem",tiles:GBIF_TERRAIN_TILES,tileSize:256,maxzoom:15,encoding:"terrarium",attribution:"Elevation tiles &copy; Mapzen"});
  map.setTerrain({source:"gbif-terrain-dem",exaggeration:1});
}
map.addControl(new maplibregl.ScaleControl({unit:"metric"}));
map.addControl(new maplibregl.FullscreenControl());
map.getCanvas().setAttribute("aria-label", "Mapa de observaciones GBIF");
const canvasLabels = {"Zoom in":"Acercar", "Zoom out":"Alejar", "Reset bearing to north":"Orientar al norte", "Enter fullscreen":"Pantalla completa", "Exit fullscreen":"Salir de pantalla completa"};
for (const button of document.querySelectorAll(".maplibregl-ctrl button")) {
  const title=button.getAttribute("title"); if(canvasLabels[title]){button.title=canvasLabels[title];button.setAttribute("aria-label",canvasLabels[title]);}
}
function geojson() {
  return {type:"FeatureCollection",features:filtered.filter(r => Number.isFinite(r.decimalLatitude) && Number.isFinite(r.decimalLongitude)).map(r => ({
    type:"Feature", id:Number(r.key), properties:{id:String(r.key),precision:precisionGroup(r)},
    geometry:{type:"Point",coordinates:[r.decimalLongitude,r.decimalLatitude]}}))};
}
function uncertaintyData(){return {type:"FeatureCollection",features:filtered.map(uncertaintyPolygon).filter(Boolean)};}
function updateUncertainty(){
  if(map.getSource("gbif-uncertainty"))map.getSource("gbif-uncertainty").setData(uncertaintyData());
  const visibility=$("show-uncertainty").checked?"visible":"none";
  for(const layer of ["gbif-uncertainty-fill","gbif-uncertainty-line"])if(map.getLayer(layer))map.setLayoutProperty(layer,"visibility",visibility);
}
function clearClusterMarkers(){for(const marker of clusterMarkers) marker.remove();clusterMarkers=[];}
function refreshClusterLabels(){
  clearTimeout(clusterRefresh);
  clusterRefresh=setTimeout(()=>{
    clearClusterMarkers();
    if(!map.getLayer("gbif-clusters"))return;
    const seen=new Set();
    for(const feature of map.queryRenderedFeatures({layers:["gbif-clusters"]})){
      const id=feature.properties.cluster_id;if(seen.has(id))continue;seen.add(id);
      const element=document.createElement("div");element.className="cluster-count";element.textContent=feature.properties.point_count_abbreviated;
      element.setAttribute("aria-hidden","true");
      clusterMarkers.push(new maplibregl.Marker({element}).setLngLat(feature.geometry.coordinates).addTo(map));
    }
  },60);
}
function installObservationLayers(){
  mapReady=true;
  if(map.getSource("gbif"))return;
  map.addSource("gbif-uncertainty",{type:"geojson",data:uncertaintyData()});
  map.addLayer({id:"gbif-uncertainty-fill",type:"fill",source:"gbif-uncertainty",paint:{"fill-color":["case",["get","visual_only"],"#ed7777","#78c9ef"],"fill-opacity":.19}});
  map.addLayer({id:"gbif-uncertainty-line",type:"line",source:"gbif-uncertainty",paint:{"line-color":["case",["get","visual_only"],"#cd4545","#4daedb"],"line-width":1,"line-opacity":.6}});
  map.addSource("gbif",{type:"geojson",data:geojson(),cluster:true,clusterMaxZoom:12,clusterRadius:38});
  map.addLayer({id:"gbif-clusters",type:"circle",source:"gbif",filter:["has","point_count"],paint:{
    "circle-color":"#203f35","circle-radius":["step",["get","point_count"],17,20,21,100,26],"circle-stroke-color":"#fff","circle-stroke-width":2}});
  map.addLayer({id:"gbif-points",type:"circle",source:"gbif",filter:["!",["has","point_count"]],paint:{
    "circle-color":["match",["get","precision"],"precise","#167d61","wide","#d37920","#74818e"],
    "circle-radius":["interpolate",["linear"],["zoom"],6,5,13,7],"circle-stroke-color":"#fff","circle-stroke-width":1.5}});
  map.addSource("gbif-selected",{type:"geojson",data:{type:"FeatureCollection",features:[]}});
  map.addLayer({id:"gbif-highlight",type:"circle",source:"gbif-selected",filter:["==",["geometry-type"],"Point"],paint:{"circle-radius":10,"circle-color":"#fff","circle-opacity":0,"circle-stroke-color":"#ffd05c","circle-stroke-width":4}});
  updateSelection();updateUncertainty();refreshClusterLabels();applyTerrain();$("terrain-toggle").disabled=false;
}
map.on("style.load",installObservationLayers);
map.on("moveend",refreshClusterLabels);
map.on("sourcedata",e=>{if(e.sourceId==="gbif" && e.isSourceLoaded)refreshClusterLabels();});
map.on("error",()=>{$("map-status").textContent="El fondo no ha podido cargar alguna tesela. Puedes cambiar de fondo; los registros siguen en local.";$("map-status").classList.add("map-error");});
map.on("mouseenter","gbif-points",()=>map.getCanvas().style.cursor="pointer");
map.on("mouseleave","gbif-points",()=>map.getCanvas().style.cursor="");
map.on("mouseenter","gbif-clusters",()=>map.getCanvas().style.cursor="pointer");
map.on("mouseleave","gbif-clusters",()=>map.getCanvas().style.cursor="");
map.on("click","gbif-clusters",async e=>{
  const f=e.features[0],source=map.getSource("gbif");
  if(f.properties.point_count<=20){
    const leaves=await source.getClusterLeaves(f.properties.cluster_id,20,0);
    if(leaves.length===f.properties.point_count&&leaves.every(p=>p.geometry.coordinates[0]===leaves[0].geometry.coordinates[0]&&p.geometry.coordinates[1]===leaves[0].geometry.coordinates[1])){
      const ids=leaves.map(p=>String(p.properties.id));selectObservation(ids[0],false,ids);return;
    }
  }
  const zoom=await source.getClusterExpansionZoom(f.properties.cluster_id);
  map.easeTo({center:f.geometry.coordinates,zoom:Math.min(zoom,16)});
});
map.on("click","gbif-points",e=>{
  const features=map.queryRenderedFeatures([[e.point.x-6,e.point.y-6],[e.point.x+6,e.point.y+6]],{layers:["gbif-points"]});
  const ids=[...new Set(features.map(f=>String(f.properties.id)))];
  if(ids.length)selectObservation(ids[0],false,ids);
});
function uncertaintyPolygon(row){
  if(circleCache.has(row.key))return circleCache.get(row.key);
  const visualOnly=row.coordinateUncertaintyInMeters==null;
  const radius=visualOnly?500:row.coordinateUncertaintyInMeters;
  if(!Number.isFinite(radius)||radius<=0)return null;
  const lat=row.decimalLatitude*Math.PI/180,lon=row.decimalLongitude*Math.PI/180,d=radius/6371008.8,ring=[];
  for(let i=0;i<=96;i++){
    const bearing=i/96*2*Math.PI;
    const y=Math.asin(Math.sin(lat)*Math.cos(d)+Math.cos(lat)*Math.sin(d)*Math.cos(bearing));
    const x=lon+Math.atan2(Math.sin(bearing)*Math.sin(d)*Math.cos(lat),Math.cos(d)-Math.sin(lat)*Math.sin(y));
    ring.push([x*180/Math.PI,y*180/Math.PI]);
  }
  const feature={type:"Feature",properties:{id:String(row.key),radius_m:radius,visual_only:visualOnly},geometry:{type:"Polygon",coordinates:[ring]}};
  circleCache.set(row.key,feature);return feature;
}
function updateSelection(){
  if(!map.getSource("gbif-selected"))return;
  const row=byId.get(String(selected)),features=[];
  if(row)features.push({type:"Feature",properties:{},geometry:{type:"Point",coordinates:[row.decimalLongitude,row.decimalLatitude]}});
  map.getSource("gbif-selected").setData({type:"FeatureCollection",features});
}
function selectObservation(id,pan=true,overlaps=[]){
  const row=byId.get(String(id));if(!row)return;
  selected=String(id);currentOverlaps=overlaps;updateSelection();
  const title=row.species||row.scientificName;
  const elevation=row.geography?.elevation, municipality=row.geography?.municipality;
  const altitudeLabel=elevation?.status==="available"?`${es.format(Math.round(elevation.value_m))} m (DEM local)`:"No disponible en el DEM local";
  const municipalityLabel=municipality?.status==="available"?municipality.name:municipality?.status==="ambiguous"?"No determinado (límite o solapamiento)":"No disponible en la cartografía local";
  const fields=[ ["Fecha",dateLabel(row.eventDate)], ["GBIF ID",row.key], ["Incertidumbre",precisionLabel(row)],
    ["Coordenadas",`${row.decimalLatitude}, ${row.decimalLongitude}`], ["Altitud",altitudeLabel],
    ["Municipio",municipalityLabel], ["Observador",row.recordedBy], ["Proveedor",row.dataset]];
  const secondaryFields=[["Referencia local","Altitud y municipio en las coordenadas publicadas"],
    ["Localidad",row.locality], ["Hábitat",row.habitat],
    ["Nombre publicado",row.originalName], ["Fecha publicada",row.originalDate],
    ["Recuento publicado",row.individualCount], ["Cantidad publicada",row.organismQuantity],
    ["Tipo de cantidad",row.organismQuantityType], ["Licencia del registro",row.license]];
  const photoItems=row.photos.filter(p=>p.localPath);
  const photos=photoItems.map((p,i)=>`<figure><a href="${escapeHTML(p.localPath)}" target="_blank" rel="noopener"><img src="${escapeHTML(p.localPath)}" alt="${escapeHTML(title)} · foto ${i+1} de ${photoItems.length}" loading="${i===0?'eager':'lazy'}"></a><figcaption>${i+1}/${photoItems.length} · ${escapeHTML(p.creator||p.rightsHolder)}<br>${escapeHTML(p.license)}</figcaption></figure>`).join("");
  const definitionList=items=>`<dl>${items.map(([name,value])=>`<dt>${escapeHTML(name)}</dt><dd>${escapeHTML(value)}</dd>`).join("")}</dl>`;
  $("detail").innerHTML=`<h2>${escapeHTML(title)}</h2><span class="badge">${escapeHTML(dateLabel(row.eventDate))} · ${escapeHTML(precisionLabel(row))}</span><label class="review-control">Revisión<select id="observation-review">${Object.entries(reviewLabels).map(([value,label])=>`<option value="${value}" ${reviewStatus(id)===value?"selected":""}>${label}</option>`).join("")}</select></label><section class="photo-section"><div class="photo-heading"><strong>Fotos (${photoItems.length})</strong>${photoItems.length>1?'<span>Desliza para ver todas →</span>':''}</div><div class="photos" tabindex="0" aria-label="Fotos de la observación">${photos||"<p>Sin fotos publicadas.</p>"}</div></section>${definitionList(fields)}<details class="extra-details"><summary>Más datos y procedencia</summary>${definitionList(secondaryFields)}${row.occurrenceRemarks?`<p class="detail-note">${escapeHTML(row.occurrenceRemarks)}</p>`:""}${row.informationWithheld?`<p class="detail-note"><strong>Información retenida por el proveedor:</strong> ${escapeHTML(row.informationWithheld)}</p>`:""}${row.dataGeneralizations?`<p class="detail-note">${escapeHTML(row.dataGeneralizations)}</p>`:""}<div class="detail-links"><a href="raw/verbatim/${row.key}.json" target="_blank" rel="noopener">Todos los campos originales (local)</a><a href="https://www.gbif.org/occurrence/${row.key}" target="_blank" rel="noopener">Abrir GBIF (web)</a></div></details>${row.coordinateUncertaintyInMeters==null?'<p class="detail-note">Incertidumbre desconocida. Círculo rojo de 500 m solo como referencia visual.</p>':'<p class="detail-note">El círculo representa la incertidumbre publicada; no delimita un setal.</p>'}`;
  $("observation-review").addEventListener("change",event=>changeReview(id,event.target.value));
  $("overlap").hidden=overlaps.length<2;
  $("overlap").replaceChildren();
  if(overlaps.length>1){const heading=document.createElement("h2");heading.textContent=`${overlaps.length} citas en este punto o muy próximas`;$("overlap").append(heading);for(const key of overlaps)$("overlap").append(recordButton(byId.get(key),()=>selectObservation(key,false,overlaps)));}
  if(pan && mapReady)map.easeTo({center:[row.decimalLongitude,row.decimalLatitude],zoom:Math.max(map.getZoom(),13)});
  $("side").hidden=false;$("side").scrollTop=0;
}
function recordButton(row,handler){
  const button=document.createElement("button");button.className="record"+(String(row.key)===selected?" selected":"");button.dataset.id=row.key;
  const name=document.createElement("strong");name.textContent=row.species||row.scientificName;
  const detail=document.createElement("span");detail.textContent=`GBIF ${row.key} · ${dateLabel(row.eventDate)} · ${precisionLabel(row)} · ${reviewLabels[reviewStatus(row.key)]} · ${row.locality||row.dataset}`;
  button.append(name,detail);button.addEventListener("click",handler||(()=>selectObservation(row.key)));return button;
}
function closeDetail(){selected=null;currentOverlaps=[];$("side").hidden=true;$("overlap").hidden=true;updateSelection();}
function applyFilters(){
  const species=$("species").value, precision=$("precision").value, query=normalize($("search").value);
  filtered=records.filter(r=>(species==="all"||r.profile_ids.includes(species))&&($("review-filter").value==="all"||reviewStatus(r.key)===$("review-filter").value)&&(precision==="all"||(precision==="precise_or_unknown"?precisionGroup(r)!=="wide":precisionGroup(r)===precision))&&(!query||searchText.get(r.key).includes(query)));
  filtered.sort((a,b)=>String(b.eventDate).localeCompare(String(a.eventDate))||Number(b.key)-Number(a.key));
  if(selected&&!filtered.some(r=>String(r.key)===selected))closeDetail();
  $("count").textContent=`${es.format(filtered.length)} de ${es.format(records.length)} observaciones · ${species==="all"?"Todas las especies":profileById.get(species).scientific_name}`;
  $("count").textContent+=" · "+Object.entries(reviewLabels).map(([state,label])=>`${label}: ${es.format(filtered.filter(r=>reviewStatus(r.key)===state).length)}`).join(" · ");
  if(map.getSource("gbif"))map.getSource("gbif").setData(geojson());updateSelection();updateUncertainty();clearClusterMarkers();
}
function fitObservations(){if(!filtered.length)return;const bounds=new maplibregl.LngLatBounds();for(const r of filtered)bounds.extend([r.decimalLongitude,r.decimalLatitude]);map.fitBounds(bounds,{padding:45,maxZoom:13,duration:350});}
$("species").addEventListener("change",()=>{applyFilters();fitObservations();});
$("review-filter").addEventListener("change",applyFilters);
$("precision").addEventListener("change",applyFilters);
$("search").addEventListener("input",applyFilters);
$("fit").addEventListener("click",fitObservations);
$("close-detail").addEventListener("click",()=>{closeDetail();map.getCanvas().focus();});
document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!$("side").hidden){closeDetail();map.getCanvas().focus();}});
$("show-uncertainty").addEventListener("change",updateUncertainty);
function applyBasemap(){const id=$("basemap").value;if(id===activeStyleId)return;activeStyleId=id;mapReady=false;$("terrain-toggle").disabled=true;clearClusterMarkers();$("map-status").textContent="Cartografía online · observaciones locales";$("map-status").classList.remove("map-error");map.setStyle(styleValue(GBIF_BASE_STYLES.find(s=>s.id===id)),{diff:false});}
$("basemap").addEventListener("change",applyBasemap);
// Browsers can restore form values after scripts initialize (reload/back-forward cache).
window.addEventListener("pageshow",()=>requestAnimationFrame(()=>{applyFilters();applyBasemap();}));
applyFilters();
// Expose the minimal state used by the focused browser check and for local diagnosis.
window.gbifViewer={reviewDocument,importReview,reviewStatus,map,selectObservation,fitObservations,get filtered(){return filtered;},get selected(){return selected;}};
document.body.dataset.viewerReady="true";
