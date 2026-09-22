/* Per-tab reference date. Only bounded historical station queries cross the API. */
export function createHistoricalMode(bridge) {
  const text = bridge.text;
  let referenceDate = null, revision = 0, pending = null, remote = null, busy = false;
  let lastData = null, lastPeriod = null, lastMetrics = null;
  const stationCache=new Map();
  let moveTimer=null;
  let requestSerial=0;
  const requestId=()=>globalThis.crypto?.randomUUID?.() || `history_${Date.now()}_${++requestSerial}`;
  const contains=(outer,inner)=>outer && outer[0]<=inner[0] && outer[1]<=inner[1] && outer[2]>=inner[2] && outer[3]>=inner[3];
  function covered(regions, box) {
    let missing=[box];
    for(const b of regions||[]) {
      missing=missing.flatMap(a=>{
        const w=Math.max(a[0],b[0]),s=Math.max(a[1],b[1]),e=Math.min(a[2],b[2]),n=Math.min(a[3],b[3]);
        if(w>=e || s>=n)return [a];
        return [[a[0],a[1],w,a[3]],[e,a[1],a[2],a[3]],[w,a[1],e,s],[w,n,e,a[3]]].filter(r=>r[0]<r[2]&&r[1]<r[3]);
      });
      if(!missing.length)return true;
    }
    return false;
  }
  const button = document.createElement('button');
  button.id = 'historical-mode-toggle'; button.type = 'button';
  button.className = 'map-control-button'; button.setAttribute('aria-pressed', 'false');
  button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 2v6m10-6v6M3 11h18M7 15h3m4 0h3m-10 3h3"/></svg>';
  bridge.after().after(button);
  const badge = document.createElement('button'); badge.id = 'historical-mode-badge';
  badge.type = 'button'; badge.hidden = true;
  const dialog = document.createElement('dialog'); dialog.id = 'historical-mode-dialog';
  dialog.setAttribute('aria-labelledby', 'hm-title');
  dialog.innerHTML = '<form><h2 id="hm-title"></h2><section class="hm-picker"><div class="hm-date-summary"><span class="hm-date-label"></span><output class="hm-selected-date" aria-live="polite"></output></div><input type="hidden"><div class="hm-calendar"><div class="hm-month-nav"><button type="button" class="hm-prev">‹</button><select class="hm-month"></select><select class="hm-year"></select><button type="button" class="hm-next">›</button></div><div class="hm-weekdays" aria-hidden="true"></div><div class="hm-days" role="group"></div><div class="hm-shortcuts"><button type="button" class="hm-yesterday"></button><button type="button" class="hm-year-ago"></button></div></div><p class="hm-scope"></p><details class="hm-details"><summary></summary><p class="hm-help"></p></details></section><p class="hm-status" role="status" aria-live="polite"></p><div class="hm-actions"><button type="button" class="hm-today"></button><button type="button" class="hm-cancel"></button><button type="submit" class="hm-apply"></button></div></form>';
  bridge.map.getContainer().append(badge); document.body.append(dialog);
  const form = dialog.querySelector('form'), input = dialog.querySelector('input');
  const status = dialog.querySelector('.hm-status'), cancel = dialog.querySelector('.hm-cancel');
  const apply = dialog.querySelector('.hm-apply'), today = dialog.querySelector('.hm-today');
  const monthSelect=dialog.querySelector('.hm-month'),yearSelect=dialog.querySelector('.hm-year');
  const daysGrid=dialog.querySelector('.hm-days');
  let viewedMonth='';
  const isoDate=value=>value.toISOString().slice(0,10);
  const dateObject=value=>new Date(`${value}T12:00:00Z`);
  const displayDate=value=>value.split('-').reverse().join('/');
  function validDay(value) {
    if(!/^\d{4}-\d{2}-\d{2}$/.test(value || '') || value<'2000-01-01' || value>input.max)return false;
    const parsed=dateObject(value);
    return Number.isFinite(parsed.getTime()) && isoDate(parsed)===value;
  }
  function renderCalendar(focusDay=null) {
    if(!viewedMonth || !input.max)return;
    const locale=bridge.language(),[year,month]=viewedMonth.split('-').map(Number);
    const maxYear=Number(input.max.slice(0,4)),maxMonth=Number(input.max.slice(5,7));
    monthSelect.replaceChildren();yearSelect.replaceChildren();
    for(let m=0;m<12;m++) {
      const option=document.createElement('option');option.value=String(m+1);
      option.textContent=new Intl.DateTimeFormat(locale,{month:'long',timeZone:'UTC'}).format(new Date(Date.UTC(2024,m,1)));
      option.disabled=year===maxYear && m+1>maxMonth;monthSelect.append(option);
    }
    for(let y=maxYear;y>=2000;y--){const option=document.createElement('option');option.value=option.textContent=String(y);yearSelect.append(option);}
    monthSelect.value=String(month);yearSelect.value=String(year);
    monthSelect.ariaLabel=text('history_month');yearSelect.ariaLabel=text('history_year');
    for(const [selector,label,disabled] of [['.hm-prev','history_previous_month',viewedMonth==='2000-01'],['.hm-next','history_next_month',viewedMonth===input.max.slice(0,7)]]) {
      const control=dialog.querySelector(selector);control.ariaLabel=control.title=text(label);control.disabled=disabled;
    }
    const weekdays=dialog.querySelector('.hm-weekdays');weekdays.replaceChildren();
    for(let i=0;i<7;i++){const label=document.createElement('span');label.textContent=new Intl.DateTimeFormat(locale,{weekday:'short',timeZone:'UTC'}).format(new Date(Date.UTC(2024,0,1+i)));weekdays.append(label);}
    daysGrid.ariaLabel=text('history_date');daysGrid.replaceChildren();
    const first=new Date(Date.UTC(year,month-1,1,12)),offset=(first.getUTCDay()+6)%7;
    const focus=focusDay || (input.value.startsWith(viewedMonth)?input.value:`${viewedMonth}-01`);
    for(let i=0;i<42;i++) {
      const date=new Date(Date.UTC(year,month-1,1-offset+i,12)),value=isoDate(date);
      const cell=document.createElement('button');cell.type='button';cell.dataset.date=value;
      cell.textContent=String(date.getUTCDate());cell.disabled=!validDay(value);
      cell.className=`hm-day${date.getUTCMonth()!==month-1?' hm-other-month':''}`;
      cell.setAttribute('aria-pressed',String(value===input.value));cell.tabIndex=value===focus?0:-1;
      cell.ariaLabel=new Intl.DateTimeFormat(locale,{dateStyle:'full',timeZone:'UTC'}).format(date);
      daysGrid.append(cell);
    }
    dialog.querySelector('.hm-selected-date').textContent=validDay(input.value)?displayDate(input.value):'';
    if(focusDay)daysGrid.querySelector(`[data-date="${focusDay}"]`)?.focus({preventScroll:true});
  }
  function selectDay(day, focus=false) {
    if(!validDay(day))return;
    input.value=day;viewedMonth=day.slice(0,7);renderCalendar(focus?day:null);
  }
  function moveMonth(delta) {
    const d=dateObject(`${viewedMonth}-01`);d.setUTCMonth(d.getUTCMonth()+delta);
    viewedMonth=isoDate(d).slice(0,7);
    viewedMonth=viewedMonth<'2000-01'?'2000-01':viewedMonth>input.max.slice(0,7)?input.max.slice(0,7):viewedMonth;
    renderCalendar();
  }
  monthSelect.addEventListener('change',()=>{viewedMonth=`${yearSelect.value}-${monthSelect.value.padStart(2,'0')}`;renderCalendar();});
  yearSelect.addEventListener('change',()=>{viewedMonth=`${yearSelect.value}-${monthSelect.value.padStart(2,'0')}`;moveMonth(0);});
  dialog.querySelector('.hm-prev').addEventListener('click',()=>moveMonth(-1));
  dialog.querySelector('.hm-next').addEventListener('click',()=>moveMonth(1));
  daysGrid.addEventListener('click',event=>{const cell=event.target.closest('[data-date]');if(cell&&!cell.disabled)selectDay(cell.dataset.date,true);});
  daysGrid.addEventListener('keydown',event=>{
    const cell=event.target.closest('[data-date]');if(!cell)return;
    const d=dateObject(cell.dataset.date),step={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[event.key];
    if(step)d.setUTCDate(d.getUTCDate()+step);
    else if(event.key==='Home')d.setUTCDate(d.getUTCDate()-(d.getUTCDay()+6)%7);
    else if(event.key==='End')d.setUTCDate(d.getUTCDate()+6-(d.getUTCDay()+6)%7);
    else if(event.key==='PageUp'||event.key==='PageDown') {
      const day=d.getUTCDate();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()+(event.key==='PageUp'?-1:1)*(event.shiftKey?12:1));
      d.setUTCDate(Math.min(day,new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).getUTCDate()));
    } else return;
    event.preventDefault();const next=isoDate(d);selectDay(next<'2000-01-01'?'2000-01-01':next>input.max?input.max:next,true);
  });
  dialog.querySelector('.hm-yesterday').addEventListener('click',()=>selectDay(input.max,true));
  dialog.querySelector('.hm-year-ago').addEventListener('click',()=>{
    const d=dateObject(input.max),month=d.getUTCMonth();d.setUTCFullYear(d.getUTCFullYear()-1);
    if(d.getUTCMonth()!==month)d.setUTCDate(0);selectDay(isoDate(d),true);
  });
  function localToday() {
    const parts = new Intl.DateTimeFormat('en-CA', {timeZone: bridge.calendarTimezone(), year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(new Date());
    return ['year','month','day'].map(key => parts.find(p => p.type === key).value).join('-');
  }
  function refreshLanguage() {
    button.title = button.ariaLabel = text('history_mode');
    dialog.querySelector('h2').textContent = text('history_mode');
    dialog.querySelector('.hm-date-label').textContent = text('history_date');
    dialog.querySelector('.hm-help').textContent = text('history_help');
    dialog.querySelector('.hm-scope').textContent=text('history_scope');
    dialog.querySelector('.hm-details summary').textContent=text('history_how');
    dialog.querySelector('.hm-yesterday').textContent=text('history_yesterday');
    dialog.querySelector('.hm-year-ago').textContent=text('history_year_ago');
    cancel.textContent = text('cancel'); apply.textContent = text('history_apply');
    today.textContent = text('history_today');
    badge.textContent = referenceDate ? `${text('history_mode')} · ${referenceDate.split('-').reverse().join('/')}${lastMetrics ? ` · ${lastMetrics.elapsed_s.toFixed(1)} s` : ''}` : '';
    badge.title = `${text('history_today')}${lastMetrics ? ` · ${text(`execution_${lastMetrics.mode}`)}` : ''}`;
    renderCalendar();
  }
  function setBusy(value) {
    busy = value; input.disabled = apply.disabled = today.disabled = value;
    dialog.classList.toggle('hm-busy', value);
    if(value)status.classList.remove('hm-error');
  }
  function showError(error) {
    status.classList.add('hm-error');
    status.textContent=text('history_error');
    console.warn('Historical weather query failed', error);
  }
  function cancelWork() {
    revision++; pending?.abort(); pending = null;
    if (remote) bridge.fetch(`${bridge.config.apiBase}/queries/${encodeURIComponent(remote)}/cancel`, {method:'POST'}).catch(()=>{});
    remote = null; setBusy(false);
  }
  function show() {
    if (busy) return;
    const max = new Date(`${localToday()}T12:00:00Z`); max.setUTCDate(max.getUTCDate()-1);
    input.max = max.toISOString().slice(0,10); input.value = referenceDate || input.max;
    viewedMonth=input.value.slice(0,7);
    status.textContent = ''; today.hidden = !referenceDate;
    refreshLanguage(); if (!dialog.open) dialog.showModal(); daysGrid.querySelector('[tabindex="0"]')?.focus({preventScroll:true});
  }
  button.addEventListener('click', show); badge.addEventListener('click', show);
  cancel.addEventListener('click',()=>{cancelWork(); dialog.close();});
  dialog.addEventListener('cancel',event=>{event.preventDefault();cancelWork();dialog.close();});

  async function page(request, signal) {
    const controller = new AbortController();
    const abort = () => controller.abort(); signal.addEventListener('abort',abort,{once:true});
    const timer = setTimeout(abort, 60000);
    let id = null;
    try {
      let response = await bridge.fetch(`${bridge.config.apiBase}/queries`, {method:'POST', cache:'no-store', signal:controller.signal,
        headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
      let data = await response.json();
      if (!response.ok) throw Error(data.error || 'history_unavailable');
      id = data.query_id; remote = id;
      if (!id) throw Error('history_invalid_response');
      do {
        await new Promise(resolve=>setTimeout(resolve,150));
        response = await bridge.fetch(`${bridge.config.apiBase}/queries/${encodeURIComponent(id)}`, {cache:'no-store',signal:controller.signal});
        data = await response.json();
        if (!response.ok) throw Error(data.error || 'history_unavailable');
      } while(response.status === 202);
      if (data.contract !== bridge.config.historyContract || data.request_id !== request.request_id || data.start_date !== request.start_date ||
          data.period !== request.period || data.offset !== request.offset || data.calendar_timezone !== request.calendar_timezone ||
          JSON.stringify(data.bounds)!==JSON.stringify(request.bounds) ||
          (request.generation && data.generation !== request.generation) || !Array.isArray(data.rows) || data.rows.length > 128 ||
          !Array.isArray(data.columns) || data.columns.length > 1250 || !Number.isInteger(data.total_stations) || data.total_stations > 10000 ||
          !data.columns.includes('Latitud') || !data.columns.includes('Longitud') || !data.generation ||
          (data.next_offset !== null && data.next_offset !== request.offset+128)) throw Error('history_invalid_response');
      return data;
    } catch (error) {
      if (id) bridge.fetch(`${bridge.config.apiBase}/queries/${encodeURIComponent(id)}/cancel`, {method:'POST'}).catch(()=>{});
      throw error;
    } finally {
      clearTimeout(timer); signal.removeEventListener('abort',abort); if(remote===id) remote=null;
    }
  }
  function features(data) {
    return data.rows.map(row=>{
      if (!Array.isArray(row) || row.length !== data.columns.length) throw Error('history_invalid_response');
      const props = Object.fromEntries(data.columns.map((key,i)=>[key,row[i]]));
      const lat=props.Latitud, lon=props.Longitud;
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat)>90 || Math.abs(lon)>180) throw Error('history_invalid_response');
      delete props.Latitud; delete props.Longitud;
      props.history_generation = data.generation;props.history_lat=lat;props.history_lon=lon;
      return {type:'Feature',geometry:{type:'Point',coordinates:[lon,lat]},properties:props};
    });
  }
  async function calculate(day, period, station=null, reuseExisting=true) {
    cancelWork(); const own=revision, controller=new AbortController(); pending=controller;
    setBusy(true); status.textContent=`${text('history_calculating')} ${day}`;
    if(!station && !dialog.open) dialog.showModal();
    const started=performance.now(); let execution=bridge.execution(), offset=0, generation=station?.generation;
    const reuse=reuseExisting && !station && referenceDate===day && lastPeriod===period ? lastData : null;
    const regions=reuse?.metadata.regions || [];
    if(reuse)generation=reuse.metadata.generation;
    const rows=[]; const bounds=station?.bounds || bridge.bounds(true); let compute=0, read=0, pages=0, result;
    try {
      do {
        const request={contract:bridge.config.historyContract,request_id:requestId(),start_date:day,period,offset,bounds,
          execution,calendar_timezone:bridge.calendarTimezone(),...(regions.length?{exclude_bounds:regions}:{}),...(generation?{generation}:{}),
          ...(station?{station:{source:station.source,code:station.code}}:{})};
        try { result=await page(request,controller.signal); }
        catch(error) {
          if(controller.signal.aborted || execution!=='worker') throw error;
          execution='local'; status.textContent=`${text('execution_fallback')} · ${text('history_calculating')} ${day}`;
          result=await page({...request,execution,request_id:requestId()},controller.signal);
        }
        if(own!==revision || controller.signal.aborted) throw new DOMException('Cancelled','AbortError');
        generation=result.generation; rows.push(...features(result)); pages++;
        compute+=result.execution?.compute_ms||0; read+=result.execution?.rows_read||0;
        offset=result.next_offset;
        status.textContent=`${text('history_calculating')} ${day} · ${Math.min(offset??result.total_stations,result.total_stations)}/${result.total_stations} · ${text(`execution_${execution}`)}`;
      } while(offset!==null);
      const combined=new Map((reuse?.features || []).map(f=>[`${f.properties.history_source}:${f.properties.history_code}`,f]));
      rows.forEach(f=>combined.set(`${f.properties.history_source}:${f.properties.history_code}`,f));
      if(combined.size>10000)throw Error('history_result_limit');
      const nextRegions=[...regions.filter(b=>!contains(bounds,b)),bounds].slice(-32);
      return {data:{type:'FeatureCollection',features:[...combined.values()],metadata:{generated_at:result.generated_at,reference_date:day,generation,bounds,regions:nextRegions}},
        metrics:{elapsed_s:(performance.now()-started)/1000,compute_ms:compute,rows_read:read,pages,stations:rows.length,mode:execution}};
    } finally { if(own===revision) {pending=null;setBusy(false);if(station)queueMicrotask(moved);} }
  }
  async function changeDate(day) {
    try {
      const period=bridge.period();
      const built=await calculate(day,period,null,false);
      bridge.cancelPrediction(); stationCache.clear(); referenceDate=day; lastPeriod=period; lastData=built.data; lastMetrics=built.metrics;
      badge.hidden=false; button.setAttribute('aria-pressed','true'); refreshLanguage();
      dialog.close(); await bridge.apply(period,lastData);
    } catch(error) { if(error.name!=='AbortError') showError(error); }
  }
  form.addEventListener('submit',event=>{event.preventDefault();if(!busy && validDay(input.value)) changeDate(input.value);});
  today.addEventListener('click',async()=>{
    cancelWork(); bridge.cancelPrediction(); const previous={referenceDate,lastData,lastPeriod,lastMetrics};
    referenceDate=null; lastData=null; lastPeriod=null; lastMetrics=null; stationCache.clear(); badge.hidden=true;
    button.setAttribute('aria-pressed','false'); dialog.close(); refreshLanguage();
    try {await bridge.reload();} catch(error) {({referenceDate,lastData,lastPeriod,lastMetrics}=previous); badge.hidden=false; button.setAttribute('aria-pressed','true');refreshLanguage();show();showError(error);}
  });
  function moved() {
    clearTimeout(moveTimer);
    if (!referenceDate || busy || covered(lastData?.metadata.regions,bridge.bounds())) return;
    moveTimer=setTimeout(()=>bridge.reload().catch(()=>{}),400);
  }
  bridge.map.on('moveend',moved);
  bridge.map.on('resize',moved);
  const settings=document.getElementById('map-settings');
  settings?.addEventListener('change',moved);
  refreshLanguage();
  return {
    invalidate(){lastData=null;stationCache.clear();bridge.reload().catch(()=>{});},
    get date(){return referenceDate;},get busy(){return busy;}, get metrics(){return lastMetrics;},
    refreshLanguage, text,
    async load(period) {
      if(period===lastPeriod && lastData && covered(lastData.metadata.regions,bridge.bounds())) return lastData;
      try {
        const built=await calculate(referenceDate,period);lastPeriod=period;lastData=built.data;lastMetrics=built.metrics;
        dialog.close();refreshLanguage();return lastData;
      } catch(error) {if(error.name!=='AbortError')showError(error);throw error;}
    },
    async station(feature) {
      const p=feature.properties;
      if(p.history_loaded===1) return feature;
      const key=[referenceDate,bridge.period(),p.history_generation,p.history_source,p.history_code].join('|');
      if(stationCache.has(key))return stationCache.get(key);
      const built=await calculate(referenceDate,bridge.period(),{source:p.history_source,code:p.history_code,generation:p.history_generation,bounds:[p.history_lon-0.001,p.history_lat-0.001,p.history_lon+0.001,p.history_lat+0.001]});
      if(built.data.features.length!==1) throw Error('history_station_unavailable');
      stationCache.set(key,built.data.features[0]);
      if(stationCache.size>8)stationCache.delete(stationCache.keys().next().value);
      return built.data.features[0];
    },
    destroy(){clearTimeout(moveTimer);bridge.map.off("moveend",moved);bridge.map.off("resize",moved);settings?.removeEventListener("change",moved);cancelWork();referenceDate=null;lastData=null;stationCache.clear();dialog.remove();button.remove();badge.remove();},
  };
}
