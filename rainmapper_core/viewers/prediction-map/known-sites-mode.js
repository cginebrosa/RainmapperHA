/* Independent overlay: no prediction, weather request or interception of map clicks. */
export function createKnownSitesMode(bridge) {
  const {map, text} = bridge, source = 'known-sites';
  const layers = ['known-sites-fill', 'known-sites-line', 'known-sites-point'];
  const button = document.createElement('button');
  button.id = 'known-sites-mode-toggle'; button.type = 'button'; button.className = 'map-control-button';
  button.setAttribute('aria-pressed', 'false');
  button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 5 14-2 3 14-13 4Z" stroke-dasharray="3 2"/><path d="m9 9 6-1 2 6-6 2Z"/><circle cx="4" cy="5" r="1.5"/><circle cx="21" cy="17" r="1.5"/></svg>';
  bridge.after().after(button);
  const labels = document.createElement('div'); labels.className = 'ks-labels';
  const legend = document.createElement('div'); legend.className = 'ks-legend'; legend.hidden = true;
  const area = document.createElement('span'), micro = document.createElement('span'), status = document.createElement('span');
  area.className = 'ks-area'; micro.className = 'ks-micro'; status.setAttribute('role', 'status');
  legend.append(area, micro, status); map.getContainer().append(labels, legend);
  let enabled = false, destroyed = false, serial = 0, controller = null, data = null, state = '';
  const color = ['match', ['get', 'kind'], 'area', '#7650c2', '#d47a00'];
  function removeLayers() {
    for (const id of layers.slice().reverse()) if (map.getLayer(id)) map.removeLayer(id);
    if (map.getSource(source)) map.removeSource(source);
    labels.replaceChildren();
  }
  function drawLabels() {
    labels.replaceChildren();
    if (!enabled || !data || destroyed) return;
    const canvas = map.getCanvas(), zoom = map.getZoom(), occupied = new Set();
    for (const feature of data.features) {
      const p = feature.properties;
      if (zoom < (p.kind === 'area' ? 9 : 12)) continue;
      const at = map.project(p.label_point);
      if (at.x < 0 || at.y < 0 || at.x > canvas.clientWidth || at.y > canvas.clientHeight) continue;
      // Bound label density while preserving every polygon at every zoom.
      const x = Math.floor(at.x/150), y = Math.floor(at.y/30), cell = `${x}:${y}`;
      if (occupied.has(cell)) continue;
      occupied.add(cell);
      const label = document.createElement('span'); label.className = p.kind === 'area' ? 'ks-area' : 'ks-micro';
      label.textContent = p.name; label.style.left = `${at.x}px`; label.style.top = `${at.y}px`; labels.append(label);
    }
  }
  function install() {
    if (!enabled || destroyed || !data || !map.isStyleLoaded()) return;
    if (!map.getSource(source)) {
      map.addSource(source, {type: 'geojson', data});
      map.addLayer({id: layers[0], type: 'fill', source, filter: ['==', ['geometry-type'], 'Polygon'],
        paint: {'fill-color': color, 'fill-opacity': .07}});
      map.addLayer({id: layers[1], type: 'line', source, filter: ['==', ['geometry-type'], 'Polygon'],
        paint: {'line-color': color, 'line-width': ['match', ['get', 'kind'], 'area', 2.5, 1.8]}});
      map.addLayer({id: layers[2], type: 'circle', source, filter: ['==', ['geometry-type'], 'Point'],
        paint: {'circle-color': color, 'circle-radius': 5, 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5}});
    }
    // Weather layers may be recreated when changing period or heatmap settings.
    const top = map.getStyle().layers.slice(-layers.length).map(layer => layer.id);
    if (layers.some((id, i) => top[i] !== id)) for (const id of layers) map.moveLayer(id);
    drawLabels();
  }
  function deactivate() {
    enabled = false; serial++; controller?.abort(); controller = null; data = null; state = '';
    button.setAttribute('aria-pressed', 'false'); button.removeAttribute('aria-busy'); legend.hidden = true;
    removeLayers();
  }
  function refreshLanguage() {
    button.title = button.ariaLabel = text('sites_mode');
    area.textContent = text('sites_areas'); micro.textContent = text('sites_microareas');
    status.textContent = state ? text(state) : '';
  }
  async function activate() {
    enabled = true; const own = ++serial;
    button.setAttribute('aria-pressed', 'true'); button.setAttribute('aria-busy', 'true');
    legend.hidden = false; state = 'sites_loading'; refreshLanguage(); controller = new AbortController();
    try {
      const response = await bridge.fetch(`${bridge.config.apiBase}/known-sites`, {cache: 'no-store', signal: controller.signal});
      if (own !== serial || !enabled || destroyed) return;
      if (response.status === 401 || response.status === 403) { deactivate(); return; }
      if (!response.ok) throw Error('unavailable');
      const value = await response.json();
      if (own !== serial || !enabled || destroyed) return;
      if (value.type !== 'FeatureCollection' || !Array.isArray(value.features) || value.features.length > 2000) throw Error('invalid');
      data = value; state = data.features.length ? '' : 'sites_empty'; install();
    } catch (error) {
      if (own === serial && enabled && error.name !== 'AbortError') state = 'sites_error';
    } finally {
      if (own === serial) { button.removeAttribute('aria-busy'); refreshLanguage(); }
    }
  }
  button.addEventListener('click', () => enabled ? deactivate() : activate());
  map.on('style.load', install); map.on('idle', install); map.on('move', drawLabels); map.on('resize', drawLabels);
  refreshLanguage();
  return {refreshLanguage, destroy() {
    destroyed = true; deactivate();
    map.off('style.load', install); map.off('idle', install); map.off('move', drawLabels); map.off('resize', drawLabels);
    button.remove(); labels.remove(); legend.remove();
  }};
}
