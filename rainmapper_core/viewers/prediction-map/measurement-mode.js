import {horizontalDistance, lineCoordinates, pathDistance, pathCoordinates, pathProfileCoordinates, summarizeProfile, createTerrainSampler, MAX_WAYPOINTS} from './measurement-terrain.js';

export function createMeasurementMode(bridge) {
  const {map, text} = bridge, source = 'map-measurement', layer = 'map-measurement-line';
  const sampler = createTerrainSampler(bridge.terrainTiles);
  const button = document.createElement('button');
  button.id = 'measurement-mode-toggle'; button.type = 'button'; button.className = 'map-control-button';
  button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 16 13-13 5 5L8 21Zm8-8 3 3m-6 0 2 2m4-7 2 2m-11 8 3 3"/></svg>';
  button.setAttribute('aria-pressed', 'false'); bridge.after().after(button);
  const panel = document.createElement('section'); panel.className = 'mm-panel'; panel.hidden = true;
  const heading = document.createElement('strong'), close = document.createElement('button');
  close.type = 'button'; close.className = 'mm-close'; close.textContent = '×';
  const status = document.createElement('p'); status.className = 'mm-status'; status.setAttribute('role', 'status');
  const values = document.createElement('dl'); values.className = 'mm-values';
  const fields = Object.fromEntries(['terrain', 'horizontal', 'change'].map(key => {
    const label = document.createElement('dt'), value = document.createElement('dd'); value.dataset.measure = key;
    values.append(label, value); return [key, {label, value}];
  }));
  const climbs = document.createElement('p'); climbs.className = 'mm-climbs';
  const provisional = document.createElement('p'); provisional.className = 'mm-preview';
  const note = document.createElement('p'); note.className = 'mm-note';
  const help = document.createElement('details'); help.className = 'mm-help';
  const helpTitle = document.createElement('summary'), instructions = document.createElement('p');
  help.append(helpTitle, instructions, note);
  const reset = document.createElement('button'); reset.type = 'button'; reset.className = 'mm-reset';
  const undo = document.createElement('button'); undo.type = 'button'; undo.className = 'mm-undo';
  const actions = document.createElement('div'); actions.className = 'mm-actions'; actions.append(undo, reset);
  panel.append(heading, close, status, values, climbs, provisional, actions, help); map.getContainer().append(panel);
  for (const type of ['click', 'dblclick', 'pointerdown', 'mousedown', 'touchstart', 'wheel']) panel.addEventListener(type, e => e.stopPropagation());
  let enabled = false, destroyed = false, finished = false, points = [], preview = null, markers = [], result = null;
  let state = 'measure_first', serial = 0, controller = null, frame = 0, dragIndex = null, doubleClickWasEnabled = false;
  let suppressMarkerClickUntil = 0;
  let geometry = null;
  let capturing = false;
  const number = (value, digits = 0) => value.toLocaleString(bridge.language(), {maximumFractionDigits: digits});
  const distance = value => Number.isFinite(value) ? (value >= 1000 ? `${number(value / 1000, 2)} km` : `${number(value)} m`) : '—';
  const pointName = index => { let name = ''; for (let n = index + 1; n; n = Math.floor((n - 1) / 26)) name = String.fromCharCode(65 + (n - 1) % 26) + name; return name; };

  function syncInteraction() {
    const next = enabled && (!finished || dragIndex !== null);
    if (next && !capturing) bridge.closePopups();
    capturing = next;
    map.getContainer().classList.toggle('mm-drawing', capturing);
    if (capturing) map.doubleClickZoom.disable();
    else if (doubleClickWasEnabled) map.doubleClickZoom.enable();
  }

  function refreshLanguage() {
    button.title = button.ariaLabel = heading.textContent = text('measure_mode');
    close.ariaLabel = text('measure_close'); reset.textContent = text('measure_reset_short');
    reset.ariaLabel = reset.title = text('measure_reset');
    undo.textContent = text('measure_undo_short'); undo.ariaLabel = undo.title = text('measure_undo');
    helpTitle.textContent = text('measure_help'); instructions.textContent = text('measure_instructions');
    status.textContent = text(state === 'measure_ready' && finished ? 'measure_finished' : state)
      .replace('{point}', pointName(Math.max(0, points.length - 1)));
    note.textContent = text('measure_note');
    for (const [key, row] of Object.entries(fields)) row.label.textContent = text(`measure_${key}`);
    fields.change.label.textContent = text('measure_change_short'); fields.change.label.title = text('measure_change');
    const horizontal = pathDistance(points);
    values.hidden = points.length < 2;
    fields.horizontal.value.textContent = points.length >= 2 ? distance(horizontal) : '—';
    provisional.hidden = !preview || finished;
    provisional.textContent = preview && points.length ? text('measure_preview')
      .replace('{leg}', distance(horizontalDistance(points.at(-1), preview)))
      .replace('{total}', distance(horizontal + horizontalDistance(points.at(-1), preview))) : '';
    fields.terrain.value.textContent = result ? `≈ ${distance(result.terrain)}` : '—';
    fields.change.value.textContent = result ? `${result.change > 0 ? '+' : ''}${number(result.change)} m` : '—';
    climbs.hidden = !result;
    climbs.textContent = result ? `↑ ${distance(result.ascent)} · ↓ ${distance(result.descent)}` : '';
    climbs.ariaLabel = result ? `${text('measure_ascent')} ${distance(result.ascent)}, ${text('measure_descent')} ${distance(result.descent)}` : '';
    reset.disabled = !points.length;
    undo.disabled = !points.length;
    markers.forEach((marker, i) => {
      const element = marker.getElement(), last = i === points.length - 1 && points.length >= 2;
      element.ariaLabel = `${text('measure_point')} ${pointName(i)}${last ? '. ' + text(finished ? 'measure_continue' : 'measure_finish') : ''}`;
      element.title = element.ariaLabel; element.classList.toggle('mm-last', last);
    });
  }
  function install() {
    if (!enabled || !geometry || !map.isStyleLoaded()) return;
    if (!map.getSource(source)) {
      map.addSource(source, {type: 'geojson', data: geometry});
      map.addLayer({id: layer, type: 'line', source,
        filter: ['==', ['get', 'preview'], false],
        layout: {'line-cap': 'round', 'line-join': 'round'},
        paint: {'line-color': '#b2205d', 'line-width': 3, 'line-opacity': .95}});
      map.addLayer({id: layer + '-preview', type: 'line', source,
        filter: ['==', ['get', 'preview'], true], layout: {'line-cap': 'round'},
        paint: {'line-color': '#b2205d', 'line-width': 3, 'line-dasharray': [2, 2], 'line-opacity': .8}});
    }
  }
  function draw() {
    frame = 0;
    syncInteraction();
    const features = [];
    if (points.length >= 2) features.push({type: 'Feature', properties: {preview: false},
      geometry: {type: 'LineString', coordinates: pathCoordinates(points)}});
    if (points.length && preview && !finished) features.push({type: 'Feature', properties: {preview: true},
      geometry: {type: 'LineString', coordinates: lineCoordinates(points.at(-1), preview, Math.min(64, Math.max(1, Math.ceil(horizontalDistance(points.at(-1), preview) / 100))))}});
    geometry = {type: 'FeatureCollection', features};
    install(); map.getSource(source)?.setData(geometry); refreshLanguage();
  }
  function scheduleDraw() { if (!frame) frame = requestAnimationFrame(draw); }
  function cancel() { serial++; controller?.abort(); controller = null; result = null; }
  async function calculate() {
    cancel(); if (points.length < 2) return;
    const own = serial, request = new AbortController(); controller = request;
    state = 'measure_loading'; refreshLanguage();
    const timeout = setTimeout(() => request.abort(), 12000);
    try {
      const coordinates = pathProfileCoordinates(points);
      const elevations = await sampler.sample(coordinates, request.signal);
      if (own !== serial || !enabled || destroyed) return;
      result = summarizeProfile(coordinates, elevations); state = 'measure_ready';
    } catch (error) {
      if (own !== serial || !enabled || destroyed) return;
      state = error.message === 'limit' ? 'measure_limit' : 'measure_unavailable';
      request.abort();
    } finally {
      clearTimeout(timeout);
      if (own === serial) { controller = null; refreshLanguage(); }
    }
  }
  function addMarker(index) {
    const element = document.createElement('div'); element.className = 'mm-point'; element.textContent = pointName(index);
    const marker = bridge.marker(element).setLngLat(points[index]).addTo(map); markers.push(marker);
    const complete = event => {
      event.stopPropagation();
      if (index !== points.length - 1 || points.length < 2 || performance.now() < suppressMarkerClickUntil) return;
      if (finished && points.length >= MAX_WAYPOINTS) { state = 'measure_points_limit'; refreshLanguage(); return; }
      finished = !finished; preview = null; draw();
    };
    element.setAttribute('role', 'button'); element.tabIndex = 0;
    element.addEventListener('click', complete);
    element.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); complete(event); }
    });
    marker.on('dragstart', () => { dragIndex = index; preview = null; syncInteraction(); cancel(); state = 'measure_drag'; refreshLanguage(); });
    marker.on('drag', () => { const p = marker.getLngLat(); points[index] = [p.lng, p.lat]; scheduleDraw(); });
    marker.on('dragend', () => {
      const p = marker.getLngLat(); points[index] = [p.lng, p.lat]; dragIndex = null;
      suppressMarkerClickUntil = performance.now() + 300;
      draw(); if (points.length >= 2) calculate(); else { state = 'measure_second'; refreshLanguage(); }
    });
    refreshLanguage();
  }
  function click(event) {
    if (!enabled || finished || dragIndex !== null || event.originalEvent?.target?.closest('.mm-point')) return;
    if (points.length >= MAX_WAYPOINTS) { state = 'measure_points_limit'; refreshLanguage(); return; }
    const p = event.lngLat;
    if (!p || !Number.isFinite(p.lng) || !Number.isFinite(p.lat)) return;
    points.push([p.lng, p.lat]); preview = null; addMarker(points.length - 1);
    state = points.length === 1 ? 'measure_second' : 'measure_loading'; draw();
    if (points.length >= 2) calculate();
  }
  function move(event) {
    if (!enabled || finished || !points.length || dragIndex !== null || !event.lngLat || event.originalEvent?.target?.closest('.mm-point')) return;
    preview = [event.lngLat.lng, event.lngLat.lat]; scheduleDraw();
  }
  function clear() {
    cancel(); markers.forEach(marker => marker.remove()); markers = []; points = []; preview = null; dragIndex = null; finished = false;
    suppressMarkerClickUntil = 0;
    help.open = false;
    state = 'measure_first'; draw();
  }
  function setEnabled(value) {
    if (value === enabled) return;
    enabled = value; button.setAttribute('aria-pressed', String(enabled)); panel.hidden = !enabled;
    if (enabled) {
      doubleClickWasEnabled = map.doubleClickZoom.isEnabled(); clear();
    } else {
      clear(); if (frame) cancelAnimationFrame(frame); frame = 0;
      for (const id of [layer + '-preview', layer]) if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource(source)) map.removeSource(source);
      if (doubleClickWasEnabled) map.doubleClickZoom.enable();
    }
  }
  function escape(event) {
    if (enabled && event.key === 'Escape' && !event.target?.matches?.('input,textarea,select,[contenteditable="true"]')) {
      event.preventDefault(); setEnabled(false); button.focus();
    }
  }
  button.onclick = () => setEnabled(!enabled); close.onclick = () => setEnabled(false); reset.onclick = clear;
  undo.onclick = () => {
    cancel(); points.pop(); markers.pop()?.remove(); preview = null; finished = false;
    state = points.length ? 'measure_second' : 'measure_first'; draw();
    if (points.length >= 2) calculate();
  };
  map.on('click', click); map.on('mousemove', move); map.on('touchmove', move); map.on('style.load', install); map.on('idle', install);
  document.addEventListener('keydown', escape); refreshLanguage();
  return {get enabled() { return enabled; }, get capturing() { return capturing; }, refreshLanguage, destroy() {
    setEnabled(false); destroyed = true; sampler.clear();
    map.off('click', click); map.off('mousemove', move); map.off('touchmove', move); map.off('style.load', install); map.off('idle', install);
    document.removeEventListener('keydown', escape); button.remove(); panel.remove();
  }};
}
