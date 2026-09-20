/* Persistent user-selected JSON, separate from the immutable GBIF snapshot. */
"use strict";
(() => {
  const button=$("connect-review-file"), status=$("review-file-status");
  let handle=null, running=null, desired=0, saved=0, enabled=false, restoring=true;
  const permission={mode:"readwrite"};
  function message(text,error=false){status.textContent=text;status.classList.toggle("review-error",error);}
  function merge(left,right){
    const result={...left};
    for(const [id,value] of Object.entries(right)){
      const old=result[id];
      if(old&&old.reviewed_at===value.reviewed_at&&old.status!==value.status)throw Error("Decisiones contradictorias con la misma fecha; el archivo se conserva.");
      if(!old||value.reviewed_at>old.reviewed_at)result[id]=value;
    }
    return result;
  }
  async function remember(value){
    const db=await new Promise((resolve,reject)=>{
      const request=indexedDB.open("rainmapper-gbif-review-files",1);
      request.onupgradeneeded=()=>request.result.createObjectStore("handles");
      request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
    });
    try{return await new Promise((resolve,reject)=>{
      const tx=db.transaction("handles",value?"readwrite":"readonly"), store=tx.objectStore("handles");
      const request=value?store.put(value,reviewStorageKey):store.get(reviewStorageKey);
      tx.oncomplete=()=>resolve(request.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||Error("No se pudo recordar el archivo."));
    });}finally{db.close();}
  }
  async function fileEntries(target){
    const file=await target.getFile();
    if(file.size>5*1024*1024)throw Error("El archivo es demasiado grande para una revisión.");
    // A newly created empty file is valid; malformed or foreign files are never replaced.
    return file.size?parseReview(JSON.parse(await file.text())):{};
  }
  function refresh(entries){
    // File decisions may be newer than this browser's copy, so refresh only if needed.
    const changed=JSON.stringify(reviewEntries)!==JSON.stringify(entries);
    localStorage.setItem(reviewStorageKey,JSON.stringify(reviewDocument(entries)));
    reviewEntries=entries;
    if(changed){applyFilters();if(selected)selectObservation(selected,false,currentOverlaps);}
  }
  async function writeOnce(){
    if(!reviewWritable)throw Error("La revisión del navegador no se puede leer con seguridad.");
    if(await handle.queryPermission(permission)!=="granted")throw Error("Falta permiso de escritura. Pulsa Reanudar guardado.");
    const disk=await fileEntries(handle), entries=merge(disk,readReview());
    const writable=await handle.createWritable();
    try{
      await writable.write(JSON.stringify(reviewDocument(entries),null,2)+"\n");
      // The original remains intact until close commits the writable stream.
      await writable.close();
    }catch(error){await writable.abort().catch(()=>{});throw error;}
    // Preserve any UI edits made while the write was in flight.
    refresh(merge(entries,readReview()));
  }
  function schedule(){
    if(!handle)return;
    desired++;
    if(!enabled){message("Guardado en archivo pausado. Pulsa Reanudar guardado; los cambios están en el navegador.",true);return;}
    message("Guardando en archivo…");
    if(running)return;
    running=(async()=>{
      try{
        while(saved<desired){
          const version=desired;
          // Serialize read/merge/write across tabs of this viewer.
          await navigator.locks.request(reviewStorageKey+":file",writeOnce);
          saved=version;
        }
        message(`Guardado en archivo: ${handle.name}`);
      }catch(error){enabled=false;button.textContent="Reanudar guardado";message("No se ha guardado en archivo: "+error.message+" Los cambios siguen en el navegador.",true);}
      finally{running=null;}
    })();
  }
  async function connect(){
    button.disabled=true;
    try{
      if(!handle){
        const directory=await window.showDirectoryPicker({mode:"readwrite"});
        const candidate=await directory.getFileHandle("gbif-revision-autoguardado.json",{create:true});
        // Validate and merge before adopting the selected file, without writing to it yet.
        merge(await fileEntries(candidate),readReview());
        handle=candidate;
      }
      if(await handle.requestPermission(permission)!=="granted")throw Error("No se concedió permiso para escribir. El archivo no se ha cambiado.");
      enabled=true;button.textContent="Reanudar guardado";
      let rememberError=false;try{await remember(handle);}catch{rememberError=true;}
      schedule();await running;
      if(enabled){button.textContent="Guardar ahora";if(rememberError)message(`Guardado en archivo: ${handle.name}. Tendrás que elegirlo de nuevo al reabrir.`);}
    }catch(error){if(error.name!=="AbortError")message(error.message,true);}
    finally{button.disabled=false;}
  }
  button.addEventListener("click",connect);
  window.addEventListener("beforeunload",event=>{if(handle&&saved<desired){event.preventDefault();event.returnValue="";}});
  window.gbifReviewFile={schedule,get ready(){return !restoring;},get pending(){return saved<desired;}};
  async function restore(){
    try{
      if(!window.showDirectoryPicker||!navigator.locks){button.disabled=true;message("Este navegador no permite el guardado directo. Usa Chrome o Exportar revisión.");return;}
      handle=await remember();
      if(!handle){message("Activa el guardado y elige una carpeta para gbif-revision-autoguardado.json.");return;}
      button.textContent="Reanudar guardado";
      if(await handle.queryPermission(permission)==="granted"){
        enabled=true;schedule();await running;if(enabled)button.textContent="Guardar ahora";
      }else message(`Archivo recordado: ${handle.name}. Pulsa Reanudar guardado para autorizar el acceso.`,true);
    }catch(error){message("No se pudo recuperar el archivo: "+error.message+" Puedes elegirlo de nuevo.",true);handle=null;}
    finally{restoring=false;button.disabled=!window.showDirectoryPicker||!navigator.locks;}
  }
  button.disabled=true;restore();
})();
