/* Offline export. The immutable snapshot and browser review storage are read only. */
"use strict";
(() => {
  const T=GBIF_EXPORT_LABELS, MiB=1024*1024, MAX_MEDIA=120*MiB, MAX_PHOTO=8*MiB;
  const text=key=>T[key]?.es||key;
  const originalKeys=['occurrenceID','datasetKey','datasetName','publishingOrgKey','recordedBy','identifiedBy','dateIdentified','scientificName','acceptedScientificName','taxonKey','acceptedTaxonKey','speciesKey','eventDate','eventTime','year','month','day','verbatimEventDate','locality','verbatimLocality','habitat','occurrenceRemarks','occurrenceStatus','individualCount','organismQuantity','organismQuantityType','basisOfRecord','samplingProtocol','samplingEffort','decimalLatitude','decimalLongitude','coordinateUncertaintyInMeters','geodeticDatum','elevation','elevationAccuracy','minimumElevationInMeters','maximumElevationInMeters','issues','informationWithheld','dataGeneralizations','license','rightsHolder','references'];
  const encoder=new TextEncoder();
  const crcTable=Uint32Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=(n&1)?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
  function crc32(data){let c=0xffffffff;for(const byte of data)c=crcTable[(c^byte)&255]^(c>>>8);return (c^0xffffffff)>>>0;}
  async function sha(data){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(v=>v.toString(16).padStart(2,'0')).join('');}
  function zip(entries){
    const parts=[], central=[];let offset=0,centralSize=0;
    for(const entry of entries){const name=encoder.encode(entry.name),header=new Uint8Array(30+name.length),v=new DataView(header.buffer);v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);v.setUint32(14,entry.crc,true);v.setUint32(18,entry.size,true);v.setUint32(22,entry.size,true);v.setUint16(26,name.length,true);header.set(name,30);parts.push(header,entry.data);
      const dir=new Uint8Array(46+name.length),d=new DataView(dir.buffer);d.setUint32(0,0x02014b50,true);d.setUint16(4,20,true);d.setUint16(6,20,true);d.setUint16(8,0x800,true);d.setUint32(16,entry.crc,true);d.setUint32(20,entry.size,true);d.setUint32(24,entry.size,true);d.setUint16(28,name.length,true);d.setUint32(42,offset,true);dir.set(name,46);central.push(dir);centralSize+=dir.length;offset+=header.length+entry.size;
    }
    const end=new Uint8Array(22),v=new DataView(end.buffer);v.setUint32(0,0x06054b50,true);v.setUint16(8,entries.length,true);v.setUint16(10,entries.length,true);v.setUint32(12,centralSize,true);v.setUint32(16,offset,true);
    const blob=new Blob([...parts,...central,end],{type:'application/zip'});if(blob.size>128*MiB)throw Error(text('error_limit'));return blob;
  }
  async function makePackage(rows, originals, files, context, progress=()=>{}){
    const assets={}, entries=[], output=[];
    for(const [index,row] of rows.entries()){
      const source=originals.get(String(row.key));if(!source||row.profile_ids.length!==1)throw Error(text('error_species'));
      const original=Object.fromEntries(originalKeys.filter(k=>source[k]!==undefined).map(k=>[k,source[k]]));
      original.verbatimScientificName=row.originalName;original.verbatimDate=row.originalDate;
      for(const k of ['habitat','locality','occurrenceRemarks','recordedBy'])if(!original[k]&&row[k])original[k]=row[k];
      const record={gbif_id:String(row.key),species_id:row.profile_ids[0],observed_at:String(row.eventDate||'').slice(0,10),lat:row.decimalLatitude,lon:row.decimalLongitude,coordinate_uncertainty_m:row.coordinateUncertaintyInMeters??null,geography:row.geography??null,original,review:context.reviews[String(row.key)]||{status:'pending',reviewed_at:null},photos:[]};
      for(const photo of row.photos||[]){if(!photo.localPath)continue;const file=files.get(photo.localPath);if(!file||file.size>MAX_PHOTO)throw Error(text('error_photo'));const bytes=new Uint8Array(await file.arrayBuffer()),hash=await sha(bytes);
        if(!assets[hash]){assets[hash]={bytes:file.size};entries.push({name:'media/'+hash,data:file,size:file.size,crc:crc32(bytes)});}
        record.photos.push({asset:hash,...Object.fromEntries(['identifier','references','creator','publisher','license','rightsHolder','created'].map(k=>[k,photo[k]??null]))});
      }
      output.push(record);progress(index+1,rows.length);
    }
    const manifest={schema:'rainmapper-gbif-observations',version:1,export:{batch_id:context.batch_id,exported_at:context.exported_at,snapshot_sha256:context.snapshot_sha256,filters:context.filters,normalization_version:1},records:output,assets};
    const bytes=encoder.encode(JSON.stringify(manifest));if(bytes.length>4*MiB)throw Error(text('error_limit'));
    return zip([{name:'manifest.json',data:bytes,size:bytes.length,crc:crc32(bytes)},...entries]);
  }
  function batches(rows,files){let batch=[],size=0,count=0,result=[];for(const row of rows){const photos=(row.photos||[]).filter(p=>p.localPath),bytes=photos.reduce((sum,p)=>sum+files.get(p.localPath).size,0);if(bytes>MAX_MEDIA||photos.length>50)throw Error(text('error_limit'));if(batch.length&&(batch.length>=100||count+photos.length>1000||size+bytes>MAX_MEDIA)){result.push(batch);batch=[];size=0;count=0;}batch.push(row);size+=bytes;count+=photos.length;}if(batch.length)result.push(batch);return result;}
  async function readPackage(file){
    if(file.size>128*MiB)throw Error(text('export_merge_limit'));
    const tail=new Uint8Array(await file.slice(Math.max(0,file.size-65557)).arrayBuffer());
    const view=new DataView(tail.buffer);let end=-1;
    for(let p=tail.length-22;p>=0;p--)if(view.getUint32(p,true)===0x06054b50&&p+22+view.getUint16(p+20,true)===tail.length){end=p;break;}
    const invalid=()=>{throw Error(text('error_invalid'));};
    if(end<0)invalid();
    const count=view.getUint16(end+10,true),size=view.getUint32(end+12,true),start=view.getUint32(end+16,true);
    if(view.getUint16(end+4,true)||view.getUint16(end+6,true)||view.getUint16(end+8,true)!==count||count>1001||size>256*1024||start+size!==file.size-tail.length+end)invalid();
    const central=new Uint8Array(await file.slice(start,start+size).arrayBuffer()),v=new DataView(central.buffer),entries=new Map();let p=0;
    for(let i=0;i<count;i++){
      if(p+46>central.length||v.getUint32(p,true)!==0x02014b50)invalid();
      const flags=v.getUint16(p+8,true),method=v.getUint16(p+10,true),crc=v.getUint32(p+16,true),bytes=v.getUint32(p+24,true),nl=v.getUint16(p+28,true),extra=v.getUint16(p+30,true),comment=v.getUint16(p+32,true),offset=v.getUint32(p+42,true);
      if(p+46+nl+extra+comment>central.length||flags&9||method||v.getUint32(p+20,true)!==bytes||offset+30>start)invalid();
      const name=new TextDecoder().decode(central.slice(p+46,p+46+nl));
      if(entries.has(name)||!(name==='manifest.json'||/^media\/[0-9a-f]{64}$/.test(name))||bytes>(name==='manifest.json'?4*MiB:MAX_PHOTO))invalid();
      const header=new DataView(await file.slice(offset,offset+30).arrayBuffer());
      if(header.getUint32(0,true)!==0x04034b50||header.getUint16(6,true)!==flags||header.getUint16(8,true)!==method||header.getUint32(14,true)!==crc||header.getUint32(18,true)!==bytes||header.getUint32(22,true)!==bytes||header.getUint16(26,true)!==nl)invalid();
      const dataStart=offset+30+nl+header.getUint16(28,true);
      if(dataStart+bytes>start||new TextDecoder().decode(await file.slice(offset+30,offset+30+nl).arrayBuffer())!==name)invalid();
      entries.set(name,{name,data:file.slice(dataStart,dataStart+bytes),size:bytes,crc});p+=46+nl+extra+comment;
    }
    if(p!==central.length||!entries.has('manifest.json'))invalid();
    const raw=new Uint8Array(await entries.get('manifest.json').data.arrayBuffer());
    if(crc32(raw)!==entries.get('manifest.json').crc)invalid();
    const manifest=JSON.parse(new TextDecoder().decode(raw));
    if(manifest.schema!=='rainmapper-gbif-observations'||manifest.version!==1||!Array.isArray(manifest.records)||!manifest.records.length||manifest.records.length>100||!manifest.assets||typeof manifest.assets!=='object'||!manifest.export||!/^[0-9a-f]{64}$/.test(manifest.export.snapshot_sha256)||!/^[a-zA-Z0-9_-]{1,80}$/.test(manifest.export.batch_id))invalid();
    const ids=new Set();for(const row of manifest.records){if(!/^[0-9]{1,24}$/.test(row.gbif_id)||ids.has(String(row.gbif_id))||!Array.isArray(row.photos)||row.photos.length>50)invalid();ids.add(String(row.gbif_id));for(const photo of row.photos)if(!Object.hasOwn(manifest.assets,photo.asset))invalid();}
    if(entries.size!==Object.keys(manifest.assets).length+1)invalid();
    for(const [hash,asset] of Object.entries(manifest.assets)){
      const entry=entries.get('media/'+hash);if(!entry||!asset||asset.bytes!==entry.size)invalid();
      const bytes=new Uint8Array(await entry.data.arrayBuffer());
      if(crc32(bytes)!==entry.crc||await sha(bytes)!==hash)throw Error(text('error_photo'));
    }
    return {manifest,entries};
  }
  function mergePackages(previous,incoming,replaceIds){
    const records=new Map();
    const remember=(row,source)=>({...row,source_export:row.source_export||{snapshot_sha256:source.export.snapshot_sha256,batch_id:source.export.batch_id}});
    for(const row of previous.manifest.records)records.set(String(row.gbif_id),remember(row,previous.manifest));
    for(const row of incoming.manifest.records)if(!records.has(String(row.gbif_id))||replaceIds.has(String(row.gbif_id)))records.set(String(row.gbif_id),remember(row,incoming.manifest));
    if(records.size>100)throw Error(text('export_merge_limit'));
    const assets={},entries=[];
    for(const row of records.values())for(const photo of row.photos)if(!Object.hasOwn(assets,photo.asset)){
      const entry=incoming.entries.get('media/'+photo.asset)||previous.entries.get('media/'+photo.asset);
      if(!entry)throw Error(text('error_photo'));assets[photo.asset]={bytes:entry.size};entries.push(entry);
    }
    if(entries.length>1000)throw Error(text('export_merge_limit'));
    const manifest={schema:'rainmapper-gbif-observations',version:1,export:incoming.manifest.export,records:[...records.values()],assets};
    const bytes=encoder.encode(JSON.stringify(manifest));
    if(bytes.length>4*MiB)throw Error(text('export_merge_limit'));
    try{return zip([{name:'manifest.json',data:bytes,size:bytes.length,crc:crc32(bytes)},...entries]);}catch(error){throw Error(text('export_merge_limit'));}
  }
  async function duplicateChoices(rows){
    return new Promise(resolve=>{
      const section=document.createElement('section');section.id='gbif-export-duplicates';const help=document.createElement('p');help.textContent=text('export_existing');section.append(help);
      const table=document.createElement('table');table.style.width='100%';
      for(const row of rows){const tr=document.createElement('tr');for(const value of [row.gbif_id,row.original?.acceptedScientificName||row.original?.scientificName||row.species_id]){const cell=document.createElement('td');cell.textContent=value;tr.append(cell);}const td=document.createElement('td'),select=document.createElement('select');select.dataset.gbifId=String(row.gbif_id);for(const value of ['ignore','replace']){const option=document.createElement('option');option.value=value;option.textContent=text(value==='ignore'?'export_ignore':'replace');select.append(option);}td.append(select);tr.append(td);table.append(tr);}section.append(table);
      const confirm=document.createElement('button');confirm.id='gbif-export-merge-confirm';confirm.textContent=text('export_apply');const cancel=document.createElement('button');cancel.id='gbif-export-merge-cancel';cancel.textContent=text('export_abort');
      confirm.onclick=()=>{const choices=new Set([...section.querySelectorAll('select')].filter(el=>el.value==='replace').map(el=>el.dataset.gbifId));section.remove();resolve(choices);};
      cancel.onclick=()=>{section.remove();resolve(null);};section.append(confirm,cancel);dialog.append(section);section.scrollIntoView({block:'nearest'});
    });
  }
  async function saveToDestination(handle,blob){
    destinationSelected.textContent=text('export_destination_selected')+' '+handle.name;
    const previousFile=await handle.getFile();let output=blob;
    if(previousFile.size){
      status.textContent=text('busy');const previous=await readPackage(previousFile),incoming=await readPackage(blob);
      const ids=new Set(previous.manifest.records.map(row=>String(row.gbif_id)));
      const duplicates=incoming.manifest.records.filter(row=>ids.has(String(row.gbif_id)));
      const choices=duplicates.length?await duplicateChoices(duplicates):new Set();
      if(choices===null)return false;
      output=mergePackages(previous,incoming,choices);
    }
    const current=await handle.getFile();
    if(current.size!==previousFile.size||current.lastModified!==previousFile.lastModified)throw Error(text('export_destination_changed'));
    await writeZip(handle,output);return true;
  }
  let rememberedSource=null;
  async function sourceHandle(value){
    const db=await new Promise((resolve,reject)=>{const request=indexedDB.open('rainmapper-gbif-export-sources',1);request.onupgradeneeded=()=>request.result.createObjectStore('handles');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
    try{return await new Promise((resolve,reject)=>{const tx=db.transaction('handles',value?'readwrite':'readonly'),store=tx.objectStore('handles'),request=value?store.put(value,GBIF_DATA.snapshot_sha256):store.get(GBIF_DATA.snapshot_sha256);tx.oncomplete=()=>resolve(request.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}finally{db.close();}
  }
  sourceHandle().then(handle=>{rememberedSource=handle||null;}).catch(()=>{});
  const button=document.createElement('button');button.id='export-rainmapper';button.textContent=text('export_title');document.querySelector('header nav').append(button);
  const dialog=document.createElement('dialog');dialog.id='gbif-export-dialog';dialog.style.cssText='width:min(700px,90vw);max-height:85vh;overflow:auto;padding:24px;border-radius:12px';
  const style=document.createElement('style');style.textContent='#gbif-export-dialog [hidden]{display:none!important}';document.head.append(style);
  const title=document.createElement('h2');title.textContent=text('export_title');
  const help=document.createElement('p');help.textContent=text('export_help');
  const sourceHelp=document.createElement('p');sourceHelp.textContent=text('export_source_help');
  const sourceSelected=document.createElement('p'),destinationSelected=document.createElement('p');
  const originLabel=document.createElement('label');originLabel.textContent=text('export_proposed_source');const originPath=document.createElement('input');originPath.readOnly=true;originPath.style.cssText='display:block;width:100%;box-sizing:border-box';originPath.value=location.protocol==='file:'?decodeURIComponent(new URL('.',location.href).pathname):new URL('.',location.href).href;originLabel.append(originPath);
  const copyOrigin=document.createElement('button');copyOrigin.textContent=text('export_copy_path');copyOrigin.onclick=async()=>{try{await navigator.clipboard.writeText(originPath.value);}catch{originPath.select();}};
  const source=document.createElement('button');source.id='gbif-export-source';source.textContent=text('export_folder');
  const fallback=document.createElement('input');fallback.type='file';fallback.webkitdirectory=true;fallback.multiple=true;fallback.hidden=true;
  const status=document.createElement('p');status.setAttribute('role','status');
  const save=document.createElement('button');save.id='gbif-export-save';save.textContent=text('export_save');save.disabled=true;
  const close=document.createElement('button');close.textContent=text('close');
  const download=document.createElement('button');download.id='gbif-export-again';download.type='button';download.hidden=true;download.textContent=text('export_download');download.style.display='block';
  dialog.append(title,help,sourceHelp,originLabel,copyOrigin,source,sourceSelected,fallback,status,save,destinationSelected,download,close);document.body.append(dialog);
  let frozen=[],context=null,files=new Map(),originals=new Map(),parts=[],part=0,lastBlob=null,lastName=null,busy=false;
  function lock(value){busy=value;source.disabled=value;close.disabled=value;save.disabled=value||part>=parts.length;download.disabled=value;}
  async function prepare(read){
    lock(true);try{status.textContent=text('busy');const safeRead=async path=>{try{return await read(path);}catch(error){if(error.name==='NotFoundError')throw Error(text('export_missing')+' '+path);throw error;}};const occurrenceFile=await safeRead('occurrences.json');if(occurrenceFile.size>32*MiB)throw Error(text('error_limit'));const bytes=await occurrenceFile.arrayBuffer();if(await sha(bytes)!==context.snapshot_sha256)throw Error(text('export_wrong_snapshot'));
      const raw=JSON.parse(new TextDecoder().decode(bytes));if(!Array.isArray(raw)||raw.length>10000)throw Error(text('error_limit'));originals=new Map(raw.map(r=>[String(r.key),r]));files=new Map();
      for(const row of frozen)for(const photo of row.photos||[]){if(!photo.localPath||files.has(photo.localPath))continue;const file=await safeRead(photo.localPath);if(file.size>MAX_PHOTO)throw Error(text('error_photo'));files.set(photo.localPath,file);}
      parts=batches(frozen,files);part=0;const count=frozen.reduce((n,r)=>n+(r.photos||[]).filter(p=>p.localPath).length,0),size=[...files.values()].reduce((n,f)=>n+f.size,0),missing=frozen.filter(r=>!(r.photos||[]).some(p=>p.localPath)).length;
      status.textContent=`${frozen.length} ${text('export_records')} · ${count} ${text('photos')} · ${(size/MiB).toFixed(1)} MiB · ${parts.length} ${text('export_batches')} · ${missing} ${text('export_no_photo')}`;
    }catch(e){parts=[];status.textContent=e.message;}finally{lock(false);}
  }
  button.onclick=()=>{if(!reviewWritable)return;frozen=structuredClone(window.gbifViewer.filtered);context={batch_id:crypto.randomUUID(),exported_at:new Date().toISOString(),snapshot_sha256:GBIF_DATA.snapshot_sha256,reviews:structuredClone(reviewEntries),filters:Object.fromEntries(['species','precision','review-filter','search'].map(id=>[id,document.getElementById(id).value]))};parts=[];part=0;sourceSelected.textContent='';destinationSelected.textContent='';save.disabled=true;save.textContent=text('export_save');source.disabled=!frozen.length;download.hidden=true;status.textContent=frozen.length+' '+text('export_records');dialog.showModal();};
  source.onclick=async()=>{if(window.showDirectoryPicker){try{const dir=await window.showDirectoryPicker({id:'rainmapper-gbif-source',mode:'read',...(rememberedSource?{startIn:rememberedSource}:{})});sourceSelected.textContent=text('export_source_selected')+' '+dir.name;await prepare(async path=>{const segments=path.split('/');if(segments.some(s=>!s||s==='.'||s==='..'))throw Error(text('error_invalid'));let current=dir;for(const s of segments.slice(0,-1))current=await current.getDirectoryHandle(s);return (await current.getFileHandle(segments.at(-1))).getFile();});if(parts.length){rememberedSource=dir;await sourceHandle(dir).catch(()=>{});}}catch(e){if(e.name!=='AbortError')status.textContent=e.message;}}else fallback.click();};
  fallback.onchange=()=>{sourceSelected.textContent=text('export_source_selected')+' '+(fallback.files[0]?.webkitRelativePath.split('/')[0]||'');const map=new Map([...fallback.files].map(f=>[f.webkitRelativePath.split('/').slice(1).join('/'),f]));prepare(async path=>{if(!map.has(path))throw Error(text('error_photo'));return map.get(path);});};
  async function destination(name){
    if(!window.showSaveFilePicker)throw Error(text('export_save_unsupported'));
    return window.showSaveFilePicker({id:'rainmapper-gbif-export',suggestedName:name,types:[{description:'ZIP',accept:{'application/zip':['.zip']}}]});
  }
  async function writeZip(handle,blob){const output=await handle.createWritable();try{await output.write(blob);await output.close();}catch(error){await output.abort().catch(()=>{});throw error;}}
  save.onclick=async()=>{lock(true);try{
    const species=(context.filters.species==='all'?'todas':context.filters.species).replace(/[^a-zA-Z0-9_-]/g,'_');const name=`rainmapper-gbif-${context.exported_at.slice(0,10)}-${species}-${part+1}.zip`;
    // Ask while the click still provides browser user activation, before preparing bytes.
    const handle=await destination(name);destinationSelected.textContent=text('export_destination_selected')+' '+handle.name;
    const blob=await makePackage(parts[part],originals,files,{...context,batch_id:context.batch_id+'_'+(part+1)},(n,total)=>status.textContent=text('busy')+` ${n}/${total}`);
    if(!await saveToDestination(handle,blob))return;lastBlob=blob;lastName=handle.name;download.hidden=false;part++;
    status.textContent=`${text('export_saved')} ${part}/${parts.length}`;save.textContent=part<parts.length?text('export_next'):text('done');
  }catch(e){if(e.name!=='AbortError')status.textContent=e.message;}finally{lock(false);}};
  download.onclick=async()=>{lock(true);try{const handle=await destination(lastName);if(!await saveToDestination(handle,lastBlob))return;status.textContent=text('export_saved');}catch(e){if(e.name!=='AbortError')status.textContent=e.message;}finally{lock(false);}};
  close.onclick=()=>dialog.close();dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});dialog.addEventListener('close',()=>{files.clear();originals.clear();parts=[];frozen=[];lastBlob=null;lastName=null;});
  window.gbifExport={makePackage,batches,crc32,zip,readPackage,mergePackages};
})();
