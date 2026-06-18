const defaultDataBase = window.location.pathname.includes("/maplibre-viewer/")
  ? "../docker-data/PublicData/"
  : "data/";
const DATA_BASE = new URLSearchParams(window.location.search).get("data") || defaultDataBase;

const periods = {
  "01d.geojson": "1 day",
  "07d.geojson": "7 days",
  "14d.geojson": "14 days",
  "21d.geojson": "21 days",
  "30d.geojson": "30 days",
  "60d.geojson": "60 days",
  "90d.geojson": "90 days",
};

const DISPLAY_BOUNDS = [
  [-2.5, 39.0],
  [4.2, 43.7],
];
const INITIAL_CENTER = [2.1, 41.7];
const INITIAL_ZOOM = 7;
const SOURCE_ID = "stations";
const CIRCLE_LAYER_ID = "station-circles";
const TERRAIN_SOURCE_ID = "rainmapper-terrain-dem";
const TERRAIN_TILES = [
  "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
];
const TERRAIN_ELEVATION_ZOOM = 15;
const LONG_PRESS_MS = 650;
const LONG_PRESS_MOVE_TOLERANCE_PX = 12;
const jawgAccessToken = window.RAINMAPPER_CONFIG?.jawgmapsAccessToken || "";
const stationSources = [
  { id: "Meteocat", label: "Meteocat" },
  { id: "Meteoclimatic", label: "Meteoclimatic" },
  { id: "Wunderground", label: "Wunderground" },
  { id: "Unknown", label: "Unknown" },
];

const baseStyles = [
  {
    id: "esri-satellite-vector",
    label: "Satellite+",
    style: {
      version: 8,
      sources: {
        "esri-imagery": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Tiles &copy; Esri",
        },
        "openmaptiles": {
          type: "vector",
          url: "https://tiles.openfreemap.org/planet",
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        },
      },
      glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
      layers: [
        { id: "esri-imagery", type: "raster", source: "esri-imagery" },
        {
          id: "satellite-boundary",
          type: "line",
          source: "openmaptiles",
          "source-layer": "boundary",
          filter: ["all", ["!=", ["get", "maritime"], 1], ["<=", ["get", "admin_level"], 6]],
          paint: {
            "line-color": "rgba(255,255,255,0.78)",
            "line-dasharray": [2, 2],
            "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.7, 10, 1.4, 14, 2.2],
          },
        },
        {
          id: "satellite-road-outline",
          type: "line",
          source: "openmaptiles",
          "source-layer": "transportation",
          filter: ["match", ["get", "class"], ["motorway", "trunk", "primary", "secondary", "tertiary"], true, false],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": "rgba(0,0,0,0.75)",
            "line-width": ["interpolate", ["exponential", 1.2], ["zoom"], 6, 1.4, 10, 2.8, 15, 8],
          },
        },
        {
          id: "satellite-road",
          type: "line",
          source: "openmaptiles",
          "source-layer": "transportation",
          filter: ["match", ["get", "class"], ["motorway", "trunk", "primary", "secondary", "tertiary"], true, false],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": ["match", ["get", "class"], ["motorway", "trunk"], "#f6c453", ["primary"], "#ffd37a", "#ffffff"],
            "line-width": ["interpolate", ["exponential", 1.2], ["zoom"], 6, 0.8, 10, 1.6, 15, 5],
          },
        },
        {
          id: "satellite-minor-road",
          type: "line",
          source: "openmaptiles",
          "source-layer": "transportation",
          minzoom: 12,
          filter: ["match", ["get", "class"], ["minor", "service", "track"], true, false],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": "rgba(255,255,255,0.86)",
            "line-width": ["interpolate", ["exponential", 1.2], ["zoom"], 12, 0.6, 16, 3.2],
          },
        },
        {
          id: "satellite-road-label",
          type: "symbol",
          source: "openmaptiles",
          "source-layer": "transportation_name",
          minzoom: 12,
          filter: ["match", ["geometry-type"], ["LineString", "MultiLineString"], true, false],
          layout: {
            "symbol-placement": "line",
            "text-field": ["coalesce", ["get", "name_en"], ["get", "name"]],
            "text-font": ["Noto Sans Regular"],
            "text-size": ["interpolate", ["linear"], ["zoom"], 12, 11, 15, 13],
          },
          paint: {
            "text-color": "#ffffff",
            "text-halo-color": "rgba(0,0,0,0.8)",
            "text-halo-width": 1.4,
          },
        },
        {
          id: "satellite-place-label",
          type: "symbol",
          source: "openmaptiles",
          "source-layer": "place",
          filter: ["match", ["get", "class"], ["country", "state", "city", "town", "village"], true, false],
          layout: {
            "text-field": ["coalesce", ["get", "name_en"], ["get", "name"]],
            "text-font": ["Noto Sans Bold"],
            "text-size": ["interpolate", ["linear"], ["zoom"], 4, 11, 8, 14, 12, 18],
            "text-max-width": 9,
          },
          paint: {
            "text-color": "#ffffff",
            "text-halo-color": "rgba(0,0,0,0.9)",
            "text-halo-width": 1.8,
          },
        },
      ],
    },
  },
  {
    id: "esri-hybrid",
    label: "Hybrid",
    style: {
      version: 8,
      sources: {
        "esri-imagery": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Tiles &copy; Esri",
        },
        "esri-roads": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Roads &copy; Esri",
        },
        "esri-labels": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Labels &copy; Esri",
        },
      },
      layers: [
        { id: "esri-imagery", type: "raster", source: "esri-imagery" },
        { id: "esri-roads", type: "raster", source: "esri-roads" },
        { id: "esri-labels", type: "raster", source: "esri-labels" },
      ],
    },
  },
  {
    id: "opentopomap",
    label: "Topographic",
    style: {
      version: 8,
      sources: {
        "opentopomap": {
          type: "raster",
          tiles: [
            "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
            "https://b.tile.opentopomap.org/{z}/{x}/{y}.png",
            "https://c.tile.opentopomap.org/{z}/{x}/{y}.png",
          ],
          tileSize: 256,
          maxzoom: 17,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
        },
      },
      layers: [
        { id: "opentopomap", type: "raster", source: "opentopomap" },
      ],
    },
  },
  {
    id: "openfreemap-liberty",
    label: "Liberty",
    url: "https://tiles.openfreemap.org/styles/liberty",
  },
];

if (jawgAccessToken) {
  baseStyles.push(
    {
      id: "jawg-streets",
      label: "Street",
      url: `https://api.jawg.io/styles/jawg-streets.json?access-token=${encodeURIComponent(jawgAccessToken)}`,
    },
    {
      id: "jawg-terrain",
      label: "Terrain",
      url: `https://api.jawg.io/styles/jawg-terrain.json?access-token=${encodeURIComponent(jawgAccessToken)}`,
    },
  );
}

let currentStyle = baseStyles[0];
let currentData = null;
let currentVisibleFeatures = [];
let currentPopup = null;
let activeStationPopupProperties = null;
let hasLoadedInitialMap = false;
let minRainFilter = 0;
let lastRainHistoryLimit = 0;
let enabledStationSources = new Set(stationSources.map((source) => source.id));
let terrainEnabled = false;
let terrainExaggeration = 1;
let longPressTimer = null;
let longPressStartPoint = null;
let didTriggerLongPress = false;
const terrainTileCache = new Map();

function styleDefinition(style) {
  if (!style.style) {
    return style.url;
  }
  return JSON.parse(JSON.stringify(style.style));
}

const map = new maplibregl.Map({
  container: "map",
  style: styleDefinition(currentStyle),
  center: INITIAL_CENTER,
  zoom: INITIAL_ZOOM,
  maxPitch: 85,
  attributionControl: true,
});

map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

function rainColor(total) {
  if (total >= 100) return "#7a001f";
  if (total >= 60) return "#c0002b";
  if (total >= 30) return "#ff4b2f";
  if (total >= 15) return "#ff9f32";
  if (total >= 5) return "#ffd166";
  return "#4ea5ff";
}

function markerRadius(total) {
  if (!Number.isFinite(total)) return 5;
  return Math.max(5, Math.min(24, 5 + Math.sqrt(Math.max(total, 0)) * 1.2));
}

function visibleFeatures(features) {
  return features.filter((feature) => {
    const coordinates = feature.geometry?.coordinates || [];
    const lon = Number(coordinates[0]);
    const lat = Number(coordinates[1]);
    return Number.isFinite(lat)
      && Number.isFinite(lon)
      && lon >= DISPLAY_BOUNDS[0][0]
      && lon <= DISPLAY_BOUNDS[1][0]
      && lat >= DISPLAY_BOUNDS[0][1]
      && lat <= DISPLAY_BOUNDS[1][1];
  });
}

function prepareFeature(feature) {
  const total = Number(feature.properties?.Total || 0);
  const source = feature.properties?.Source || inferStationSource(feature.properties?.["Codi Estació"]);
  return {
    ...feature,
    properties: {
      ...(feature.properties || {}),
      Source: source,
      rain_color: rainColor(total),
      marker_radius: markerRadius(total),
    },
  };
}

function featureRainTotal(feature) {
  const total = Number(feature.properties?.Total || 0);
  return Number.isFinite(total) ? total : 0;
}

function inferStationSource(stationCode) {
  const code = String(stationCode || "").trim().toUpperCase();
  if (code.startsWith("ES") && code.length >= 15) {
    return "Meteoclimatic";
  }
  if (code.startsWith("I")) {
    return "Wunderground";
  }
  if (code.length === 2) {
    return "Meteocat";
  }
  return "Unknown";
}

function featureStationSource(feature) {
  return feature.properties?.Source || inferStationSource(feature.properties?.["Codi Estació"]);
}

function filteredFeatures(features) {
  return features.filter((feature) => (
    featureRainTotal(feature) >= minRainFilter
    && enabledStationSources.has(featureStationSource(feature))
  ));
}

function updateMinRainControl(features) {
  const maxRain = features.reduce((maxValue, feature) => Math.max(maxValue, featureRainTotal(feature)), 0);
  const sliderMax = Math.max(10, Math.ceil(maxRain / 10) * 10);
  const slider = document.getElementById("min-rain-filter");
  slider.max = String(sliderMax);
  if (minRainFilter > sliderMax) {
    minRainFilter = sliderMax;
    slider.value = String(minRainFilter);
  }
  updateMinRainValue();
}

function updateMinRainValue() {
  document.getElementById("min-rain-value").textContent = `${minRainFilter} mm`;
}

function rainHistoryIndexes(properties) {
  return Object.keys(properties || {})
    .map((key) => {
      const match = key.match(/^Data_Pluja_(\d+)$/);
      return match ? Number(match[1]) : null;
    })
    .filter((index) => Number.isInteger(index) && index > 0)
    .sort((a, b) => a - b);
}

function maxRainHistoryRecords(features) {
  return features.reduce((maxValue, feature) => (
    Math.max(maxValue, rainHistoryIndexes(feature.properties || {}).length)
  ), 0);
}

function updateLastRainHistoryValue() {
  const output = document.getElementById("last-rain-history-value");
  output.textContent = lastRainHistoryLimit > 0 ? `${lastRainHistoryLimit} records` : "-";
}

function updateLastRainHistoryControl(features) {
  const maxRecords = maxRainHistoryRecords(features);
  const slider = document.getElementById("last-rain-history-filter");
  if (maxRecords <= 0) {
    lastRainHistoryLimit = 0;
    slider.disabled = true;
    slider.max = "1";
    slider.value = "1";
    updateLastRainHistoryValue();
    return;
  }

  slider.disabled = false;
  slider.max = String(maxRecords);
  if (lastRainHistoryLimit <= 0 || lastRainHistoryLimit > maxRecords) {
    lastRainHistoryLimit = maxRecords;
  }
  slider.value = String(lastRainHistoryLimit);
  updateLastRainHistoryValue();
}

function refreshCurrentStationPopup() {
  if (!currentPopup || !activeStationPopupProperties) {
    return;
  }
  currentPopup.setHTML(popupContent(activeStationPopupProperties));
}

function refreshFilteredData() {
  if (!currentVisibleFeatures.length) {
    return;
  }

  const selectedPeriod = document.getElementById("map-selector").value;
  const features = filteredFeatures(currentVisibleFeatures);
  currentData = {
    type: "FeatureCollection",
    metadata: currentData?.metadata || {},
    features,
  };

  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
    activeStationPopupProperties = null;
  }

  addStationLayer();
  updateSummary(selectedPeriod, features.length, currentVisibleFeatures.length);
}

function ensureTerrainSource() {
  if (map.getSource(TERRAIN_SOURCE_ID)) {
    return;
  }

  map.addSource(TERRAIN_SOURCE_ID, {
    type: "raster-dem",
    tiles: TERRAIN_TILES,
    tileSize: 256,
    maxzoom: 15,
    encoding: "terrarium",
    attribution: "Elevation tiles &copy; Mapzen",
  });
}

function updateTerrainExaggerationValue() {
  document.getElementById("terrain-exaggeration-value").textContent = `${terrainExaggeration.toFixed(1)}x`;
}

function applyTerrain() {
  if (!map.isStyleLoaded()) {
    return;
  }

  if (!terrainEnabled) {
    map.setTerrain(null);
    return;
  }

  try {
    ensureTerrainSource();
    map.setTerrain({
      source: TERRAIN_SOURCE_ID,
      exaggeration: terrainExaggeration,
    });
  } catch (error) {
    terrainEnabled = false;
    const terrainToggle = document.getElementById("terrain-toggle");
    const terrainSlider = document.getElementById("terrain-exaggeration");
    if (terrainToggle) {
      terrainToggle.checked = false;
    }
    if (terrainSlider) {
      terrainSlider.disabled = true;
    }
    console.warn("Cannot enable terrain", error);
  }
}

function addStationLayer() {
  if (!currentData || !map.isStyleLoaded()) {
    return false;
  }

  if (map.getLayer(CIRCLE_LAYER_ID)) {
    map.removeLayer(CIRCLE_LAYER_ID);
  }
  if (map.getSource(SOURCE_ID)) {
    map.removeSource(SOURCE_ID);
  }

  map.addSource(SOURCE_ID, {
    type: "geojson",
    data: currentData,
  });
  map.addLayer({
    id: CIRCLE_LAYER_ID,
    type: "circle",
    source: SOURCE_ID,
    paint: {
      "circle-radius": ["get", "marker_radius"],
      "circle-color": ["get", "rain_color"],
      "circle-opacity": 0.72,
      "circle-stroke-color": "#111923",
      "circle-stroke-width": 1.2,
    },
  });
  applyTerrain();
  return true;
}

function reloadCurrentPeriodAfterStyleChange(center, zoom, attempt = 0) {
  if (!map.isStyleLoaded()) {
    if (attempt < 40) {
      window.setTimeout(() => reloadCurrentPeriodAfterStyleChange(center, zoom, attempt + 1), 100);
    }
    return;
  }

  applyTerrain();
  map.jumpTo({ center, zoom });
  const selectedPeriod = document.getElementById("map-selector").value;
  loadMap(selectedPeriod)
    .then(() => {
      map.jumpTo({ center, zoom });
    })
    .catch((error) => {
      document.getElementById("summary").textContent = error.message;
    });
}

function popupContent(properties) {
  const station = properties["Codi Estació"] || "";
  const name = properties["Estació"] || "Unknown station";
  const source = properties.Source || inferStationSource(station);
  const town = properties["Municipi"] || "Unknown town";
  const province = properties["Provincia"] || "";
  const altitude = properties["Altitud"] || "-";
  const total = Number(properties["Total"] || 0).toFixed(1);
  const lastReading = properties["Ultima Lectura"] || "-";
  const rainHistory = recentRainHistory(properties);

  return `
    <div class="popup-title">${station} · ${name}</div>
    <div class="popup-row"><strong>Source:</strong> ${source}</div>
    <div class="popup-row"><strong>Rain:</strong> ${total} mm</div>
    <div class="popup-row"><strong>Location:</strong> ${town}${province ? `, ${province}` : ""}</div>
    <div class="popup-row"><strong>Altitude:</strong> ${altitude} m</div>
    <div class="popup-row"><strong>Last reading:</strong> ${lastReading}</div>
    ${rainHistory}
  `;
}

function terrainPopupContent(elevation, lngLat, status = "loading") {
  const latitude = lngLat.lat.toFixed(5);
  const longitude = lngLat.lng.toFixed(5);
  if (!Number.isFinite(elevation)) {
    const altitudeText = status === "error" ? "unavailable" : "loading";
    const noteText = status === "error"
      ? "External Terrarium DEM unavailable"
      : "Loading external Terrarium DEM";
    return `
      <div class="popup-title">Terrain</div>
      <div class="popup-row"><strong>Altitude:</strong> ${altitudeText}</div>
      <div class="popup-row terrain-note">${noteText}</div>
      <div class="popup-row terrain-coordinates">${latitude}, ${longitude}</div>
    `;
  }

  return `
    <div class="popup-title">Terrain</div>
    <div class="popup-row"><strong>Altitude:</strong> ${Math.round(elevation).toLocaleString("en-GB")} m</div>
    <div class="popup-row terrain-note">External Terrarium DEM</div>
    <div class="popup-row terrain-coordinates">${latitude}, ${longitude}</div>
  `;
}

function terrariumTileForLngLat(lngLat, zoom) {
  const latitude = Math.max(Math.min(lngLat.lat, 85.05112878), -85.05112878);
  const longitude = ((((lngLat.lng + 180) % 360) + 360) % 360) - 180;
  const latRad = latitude * Math.PI / 180;
  const scale = 2 ** zoom;
  const xFloat = (longitude + 180) / 360 * scale;
  const yFloat = (1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2 * scale;
  const x = Math.min(Math.max(Math.floor(xFloat), 0), scale - 1);
  const y = Math.min(Math.max(Math.floor(yFloat), 0), scale - 1);
  const pixelX = Math.min(Math.floor((xFloat - x) * 256), 255);
  const pixelY = Math.min(Math.floor((yFloat - y) * 256), 255);

  return { x, y, pixelX, pixelY, zoom };
}

function decodeTerrariumPixel(red, green, blue) {
  return (red * 256 + green + blue / 256) - 32768;
}

function loadTerrariumTile(tile) {
  const cacheKey = `${tile.zoom}/${tile.x}/${tile.y}`;
  if (terrainTileCache.has(cacheKey)) {
    return terrainTileCache.get(cacheKey);
  }

  const tileUrl = TERRAIN_TILES[0]
    .replace("{z}", tile.zoom)
    .replace("{x}", tile.x)
    .replace("{y}", tile.y);
  const imagePromise = new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Cannot load terrain tile ${tileUrl}`));
    image.src = tileUrl;
  });

  terrainTileCache.set(cacheKey, imagePromise);
  return imagePromise;
}

async function queryTerrariumElevation(lngLat) {
  const tile = terrariumTileForLngLat(lngLat, TERRAIN_ELEVATION_ZOOM);
  const image = await loadTerrariumTile(tile);
  const canvas = document.createElement("canvas");
  canvas.width = 1;
  canvas.height = 1;
  const context = canvas.getContext("2d");
  context.drawImage(image, tile.pixelX, tile.pixelY, 1, 1, 0, 0, 1, 1);
  const [red, green, blue] = context.getImageData(0, 0, 1, 1).data;
  return decodeTerrariumPixel(red, green, blue);
}

function clearLongPressTimer() {
  if (longPressTimer) {
    window.clearTimeout(longPressTimer);
    longPressTimer = null;
  }
}

function showTerrainPopup(lngLat) {
  if (currentPopup) {
    currentPopup.remove();
  }
  activeStationPopupProperties = null;

  currentPopup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: true,
    maxWidth: "260px",
    offset: 8,
  })
    .setLngLat(lngLat)
    .setHTML(terrainPopupContent(null, lngLat))
    .addTo(map);

  queryTerrariumElevation(lngLat)
    .then((elevation) => {
      if (currentPopup && Number.isFinite(elevation)) {
        currentPopup.setHTML(terrainPopupContent(elevation, lngLat));
      }
    })
    .catch((error) => {
      console.warn("Cannot query terrain elevation", error);
      if (currentPopup) {
        currentPopup.setHTML(terrainPopupContent(null, lngLat, "error"));
      }
    });
}

function setupLongPressElevation() {
  function startLongPress(event) {
    didTriggerLongPress = false;
    longPressStartPoint = event.point;
    clearLongPressTimer();
    longPressTimer = window.setTimeout(() => {
      didTriggerLongPress = true;
      showTerrainPopup(event.lngLat);
    }, LONG_PRESS_MS);
  }

  function cancelLongPress() {
    clearLongPressTimer();
    longPressStartPoint = null;
  }

  function cancelLongPressOnMove(event) {
    if (!longPressStartPoint) {
      return;
    }

    const deltaX = Math.abs(event.point.x - longPressStartPoint.x);
    const deltaY = Math.abs(event.point.y - longPressStartPoint.y);
    if (deltaX > LONG_PRESS_MOVE_TOLERANCE_PX || deltaY > LONG_PRESS_MOVE_TOLERANCE_PX) {
      cancelLongPress();
    }
  }

  map.on("mousedown", startLongPress);
  map.on("touchstart", startLongPress);
  map.on("mousemove", cancelLongPressOnMove);
  map.on("touchmove", cancelLongPressOnMove);
  map.on("mouseup", cancelLongPress);
  map.on("touchend", cancelLongPress);
  map.on("dragstart", cancelLongPress);

  map.on("contextmenu", (event) => {
    if (event.originalEvent?.preventDefault) {
      event.originalEvent.preventDefault();
    }
    didTriggerLongPress = true;
    cancelLongPress();
    showTerrainPopup(event.lngLat);
  });
}

function recentRainHistory(properties) {
  const rows = [];
  const historyIndexes = rainHistoryIndexes(properties).slice(0, lastRainHistoryLimit || undefined);
  for (const index of historyIndexes) {
    const suffix = String(index).padStart(2, "0");
    const date = properties[`Data_Pluja_${suffix}`];
    const rain = properties[`Pluja_Diaria_${suffix}`];
    const tempMax = properties[`Temp_Max_${suffix}`];
    const tempMin = properties[`Temp_Min_${suffix}`];
    if (!date || date === "None" || date === "NaT" || date === "nan") {
      continue;
    }
    const rainValue = Number(rain);
    const tempMaxValue = Number(tempMax);
    const tempMinValue = Number(tempMin);
    rows.push(`
      <tr>
        <td>${date}</td>
        <td>${Number.isFinite(rainValue) ? rainValue.toFixed(1) : rain}</td>
        <td>${Number.isFinite(tempMaxValue) ? tempMaxValue.toFixed(1) : "-"}</td>
        <td>${Number.isFinite(tempMinValue) ? tempMinValue.toFixed(1) : "-"}</td>
      </tr>
    `);
  }

  if (rows.length === 0) {
    return "";
  }

  return `
    <details class="history">
      <summary>Last ${rows.length} records</summary>
      <table class="history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Rain</th>
            <th>Tmax</th>
            <th>Tmin</th>
          </tr>
        </thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </details>
  `;
}

function updateSummary(fileName, count, totalCount = count) {
  const stationText = `${count} station${count === 1 ? "" : "s"}`;
  const sourceFilterText = enabledStationSources.size < stationSources.length
    ? ` · sources ${enabledStationSources.size}/${stationSources.length}`
    : "";
  const filterText = minRainFilter > 0 || sourceFilterText
    ? ` · ${totalCount} total${minRainFilter > 0 ? ` · min ${minRainFilter} mm` : ""}${sourceFilterText}`
    : "";
  document.getElementById("summary").textContent = `${periods[fileName]} · ${stationText}${filterText}`;
}

function updateGeneratedAt(generatedAt) {
  const generatedElement = document.getElementById("generated-at");
  if (!generatedAt) {
    generatedElement.textContent = "-";
    generatedElement.removeAttribute("datetime");
    return;
  }

  const generatedDate = new Date(generatedAt);
  if (Number.isNaN(generatedDate.getTime())) {
    generatedElement.textContent = generatedAt;
    generatedElement.setAttribute("datetime", generatedAt);
    return;
  }

  const datePart = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(generatedDate);
  const timePart = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(generatedDate);
  generatedElement.textContent = `${datePart} - ${timePart}`;
  generatedElement.setAttribute("datetime", generatedAt);
}

function fitToData() {
  const features = currentData?.features || [];
  if (features.length === 0) {
    map.fitBounds(DISPLAY_BOUNDS, { padding: 24 });
    return;
  }

  const bounds = new maplibregl.LngLatBounds();
  features.forEach((feature) => bounds.extend(feature.geometry.coordinates));
  map.fitBounds(bounds, { padding: 24, duration: 0 });
}

async function loadMap(fileName) {
  const url = `${DATA_BASE}${fileName}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Cannot load ${url}: ${response.status}`);
  }
  const data = await response.json();
  const features = visibleFeatures(data.features || []).map(prepareFeature);
  currentVisibleFeatures = features;
  updateMinRainControl(features);
  updateLastRainHistoryControl(features);
  const filtered = filteredFeatures(features);
  currentData = {
    ...data,
    features: filtered,
  };

  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
    activeStationPopupProperties = null;
  }

  addStationLayer();
  updateSummary(fileName, filtered.length, features.length);
  updateGeneratedAt(data.metadata?.generated_at);

  if (!hasLoadedInitialMap) {
    hasLoadedInitialMap = true;
    fitToData();
  }
}

function renderLayerSwitcher() {
  const container = document.getElementById("layer-switcher");
  container.innerHTML = baseStyles.map((style) => `
    <label>
      <input type="radio" name="base-style" value="${style.id}" ${style.id === currentStyle.id ? "checked" : ""}>
      <span>${style.label}</span>
    </label>
  `).join("");

  container.addEventListener("change", (event) => {
    const nextStyle = baseStyles.find((style) => style.id === event.target.value);
    if (!nextStyle) {
      return;
    }

    currentStyle = nextStyle;
    const center = map.getCenter();
    const zoom = map.getZoom();
    let reloadedCurrentPeriod = false;
    const reloadOnce = () => {
      if (reloadedCurrentPeriod) {
        return;
      }
      reloadedCurrentPeriod = true;
      reloadCurrentPeriodAfterStyleChange(center, zoom);
    };

    map.once("idle", reloadOnce);
    map.setStyle(styleDefinition(currentStyle));
    window.setTimeout(reloadOnce, 600);
  });
}

function renderSettingsPanel() {
  const toggle = document.getElementById("settings-toggle");
  const northToggle = document.getElementById("north-toggle");
  const panel = document.getElementById("map-settings");
  const slider = document.getElementById("min-rain-filter");
  const historySlider = document.getElementById("last-rain-history-filter");
  const terrainToggle = document.getElementById("terrain-toggle");
  const terrainSlider = document.getElementById("terrain-exaggeration");
  const sourceInputs = Array.from(panel.querySelectorAll("input[name='station-source']"));

  toggle.addEventListener("click", () => {
    const isOpen = panel.hasAttribute("hidden");
    panel.toggleAttribute("hidden", !isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
  });

  northToggle.addEventListener("click", () => {
    map.easeTo({ bearing: 0, duration: 350 });
  });

  slider.addEventListener("input", (event) => {
    minRainFilter = Number(event.target.value);
    updateMinRainValue();
    refreshFilteredData();
  });

  historySlider.addEventListener("input", (event) => {
    lastRainHistoryLimit = Number(event.target.value);
    updateLastRainHistoryValue();
    refreshCurrentStationPopup();
  });

  sourceInputs.forEach((input) => {
    input.addEventListener("change", () => {
      const selectedSources = sourceInputs.filter((sourceInput) => sourceInput.checked);
      if (selectedSources.length === 0) {
        input.checked = true;
        return;
      }
      enabledStationSources = new Set(selectedSources.map((sourceInput) => sourceInput.value));
      refreshFilteredData();
    });
  });

  updateTerrainExaggerationValue();

  terrainToggle.addEventListener("change", (event) => {
    terrainEnabled = event.target.checked;
    terrainSlider.disabled = !terrainEnabled;
    applyTerrain();
  });

  terrainSlider.addEventListener("input", (event) => {
    terrainExaggeration = Number(event.target.value);
    updateTerrainExaggerationValue();
    applyTerrain();
  });
}

map.on("load", () => {
  renderLayerSwitcher();
  renderSettingsPanel();
  setupLongPressElevation();
  applyTerrain();
  loadMap(document.getElementById("map-selector").value).catch((error) => {
    document.getElementById("summary").textContent = error.message;
  });
});

map.on("click", CIRCLE_LAYER_ID, (event) => {
  if (didTriggerLongPress) {
    didTriggerLongPress = false;
    return;
  }

  const feature = event.features?.[0];
  if (!feature) {
    return;
  }
  const coordinates = feature.geometry.coordinates.slice();
  activeStationPopupProperties = feature.properties || {};
  currentPopup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: true,
    maxWidth: "320px",
    anchor: "left",
    offset: 8,
  })
    .setLngLat(coordinates)
    .setHTML(popupContent(feature.properties || {}))
    .addTo(map);
  currentPopup.on("close", () => {
    activeStationPopupProperties = null;
  });
});

map.on("mouseenter", CIRCLE_LAYER_ID, () => {
  map.getCanvas().style.cursor = "pointer";
});

map.on("mouseleave", CIRCLE_LAYER_ID, () => {
  map.getCanvas().style.cursor = "";
});

document.getElementById("map-selector").addEventListener("change", (event) => {
  loadMap(event.target.value).catch((error) => {
    document.getElementById("summary").textContent = error.message;
  });
});
